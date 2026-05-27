# SPDX-License-Identifier: Apache-2.0
"""vibemix.library.cue_detr — CUE-DETR ONNX cue-POSITION producer (local, no torch).

CUE-DETR (ETH-DISCO, ISMIR 2024, MIT; DETR object-detection on log-Mel spectrograms)
detects mixable cue *positions* from raw audio. The published model was exported to
ONNX (fp32, 167 MB, byte-exact parity with the torch path — verified 2026-05-26 on real
techno/psy/house) so it runs on plain ``onnxruntime`` with **NO torch at inference time**.
The same runtime serves the CLAP embedding model — one ONNX runtime, no server.

This module is the PRODUCER: audio → candidate cue timestamps (seconds). Those candidates
are noisy on purpose (run at a low confidence threshold); ``cue_refine.refine_cue_positions``
snaps them to the downbeat/phrase grid and dedups. Labelling (intro/build/breakdown/drop/
outro) is a separate stage. The full pipeline is assembled in ``cue_engine``.

Heavy deps (``onnxruntime``, the model file, ``av``) are ALL imported lazily inside the call
and guarded: when any is missing the producer raises ``CueProducerUnavailable`` so the caller
falls back to the dep-free heuristic. The DETR image preprocessing is local numpy code — no
``from_pretrained`` network/cache lookup is allowed on the cue path. The ONNX model is not
bundled yet; place it at
``~/.cache/vibemix/cue-detr-onnx/cuedetr.fp32.onnx`` or set ``VIBEMIX_CUE_ONNX_PATH``. The
numpy post-processing (``_positions_from_outputs``) is pure and unit-tested without any heavy
dep.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

import numpy as np

from vibemix.library.cache_paths import CUE_ONNX_ENV, DEFAULT_CUE_ONNX_PATH, cue_onnx_path

# CUE-DETR sliding-window constants (from the published cue_points.py — must match the
# spectrogram windowing the model was trained/exported with, or positions drift).
_OVERLAP = 0.75
_W_WIN = 355  # window width in mel frames (== to_pixel width used in post-process)
_PADDING = 266
_MEL_SR = 22050  # sample rate the exported model expects
_N_FFT = 2048
_HOP = 512
_N_MELS = 128

# Run the producer at a LOW threshold by default — the flood of near-duplicate candidates
# is fine, cue_refine cleans it. (At the published default 0.9 it is too sparse off-EDM.)
DEFAULT_SENSITIVITY = 0.5
DEFAULT_RADIUS = 16  # min find_peaks distance (frames) between raw candidates

_ENV_MODEL = CUE_ONNX_ENV
_ENV_MODEL_SHA256 = "VIBEMIX_CUE_ONNX_SHA256"
_ENV_MODEL_SIZE = "VIBEMIX_CUE_ONNX_SIZE"
_DEFAULT_MODEL = DEFAULT_CUE_ONNX_PATH

__all__ = [
    "DEFAULT_RADIUS",
    "DEFAULT_SENSITIVITY",
    "CueProducerUnavailable",
    "detect_cue_positions",
    "model_path",
    "model_status",
]


class CueProducerUnavailable(RuntimeError):
    """The ONNX producer cannot run (missing onnxruntime / model / preprocessing dep).

    Callers catch this and fall back to the dep-free ``cue_detect`` heuristic — the
    producer is an optional local-model upgrade, never a hard requirement.
    """


def model_path() -> Path:
    """Resolved ONNX model path (``VIBEMIX_CUE_ONNX_PATH`` override, else the cache)."""
    return cue_onnx_path()


def model_status() -> dict[str, object]:
    """Return lightweight CUE-DETR ONNX asset status without heavy imports."""
    path = model_path().expanduser()
    missing = [] if path.is_file() else [path.name]
    mismatched: list[str] = []
    if not missing and _cue_file_mismatched(path):
        mismatched.append(path.name)
    return {
        "installed": not missing and not mismatched,
        "path": str(path),
        "missing": missing,
        "mismatched": mismatched,
    }


def _cue_file_mismatched(path: Path) -> bool:
    """Validate optional env-pinned size/SHA for hosted CUE artifacts."""
    expected_size = _expected_size()
    if expected_size is not None and path.stat().st_size != expected_size:
        return True
    expected_sha = _expected_sha256()
    return expected_sha is not None and _sha256_file(path) != expected_sha


def _expected_size() -> int | None:
    raw = os.environ.get(_ENV_MODEL_SIZE, "").strip()
    if not raw:
        return None
    try:
        value = int(raw)
    except ValueError:
        return None
    return value if value > 0 else None


def _expected_sha256() -> str | None:
    raw = os.environ.get(_ENV_MODEL_SHA256, "").strip().lower()
    return raw if len(raw) == 64 and all(c in "0123456789abcdef" for c in raw) else None


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _softmax(x: np.ndarray, axis: int = -1) -> np.ndarray:
    z = x - np.max(x, axis=axis, keepdims=True)
    e = np.exp(z)
    return e / np.sum(e, axis=axis, keepdims=True)


def _peak_indices(values: np.ndarray, *, height: float, distance: int) -> list[int]:
    """Small scipy.find_peaks replacement for CUE score curves."""
    arr = np.asarray(values, dtype=np.float64)
    if arr.size < 3:
        return []
    min_distance = max(1, int(distance))
    candidates = [
        i
        for i in range(1, arr.size - 1)
        if arr[i] >= height and arr[i] > arr[i - 1] and arr[i] >= arr[i + 1]
    ]
    candidates.sort(key=lambda i: float(arr[i]), reverse=True)
    chosen: list[int] = []
    for idx in candidates:
        if all(abs(idx - existing) >= min_distance for existing in chosen):
            chosen.append(idx)
    chosen.sort()
    return chosen


def _positions_from_outputs(
    logits: np.ndarray,
    boxes: np.ndarray,
    borders: list[int],
    *,
    sensitivity: float,
    radius: int,
) -> list[int]:
    """Pure-numpy CUE-DETR post-process → cue positions in MEL-FRAME units.

    ``logits`` (W, Q, C+1) and ``boxes`` (W, Q, 4 cxcywh-normalized) are the ONNX outputs
    over W sliding windows of Q queries. Per query: cue score = softmax over classes,
    excluding the last (no-object) class; cue x-centre (frames) = ``cx * _W_WIN + border``.
    Scores are min-max scaled across all windows, then a local peak picker with
    the sensitivity height + radius distance picks the cues (mirrors the
    published script's ``find_peaks`` contract without carrying scipy).
    """
    scores: list[float] = []
    positions: list[int] = []
    for w in range(logits.shape[0]):
        prob = _softmax(logits[w].astype(np.float64), axis=-1)
        cue_score = prob[:, :-1].max(axis=1)  # exclude no-object (last) class
        cx = boxes[w][:, 0]  # box-centre x, normalized
        centre = (cx * _W_WIN).astype(np.int64) + int(borders[w])
        scores.extend(cue_score.tolist())
        positions.extend(centre.tolist())

    if not positions:
        return []
    order = np.argsort(positions)
    pos_sorted = np.asarray(positions, dtype=np.int64)[order]
    sc = np.asarray(scores, dtype=np.float64)[order]
    rng = sc.max() - sc.min()
    sc = (sc - sc.min()) / rng if rng > 0 else np.zeros_like(sc)
    peaks = _peak_indices(sc, height=sensitivity, distance=max(1, radius))
    return [int(pos_sorted[i]) for i in peaks]


_VIRIDIS_POS = np.asarray(
    [0.000, 0.125, 0.250, 0.375, 0.500, 0.625, 0.750, 0.875, 1.000],
    dtype=np.float32,
)
_VIRIDIS_RGB = np.asarray(
    [
        (68, 1, 84),
        (71, 44, 122),
        (59, 81, 139),
        (44, 113, 142),
        (33, 144, 141),
        (39, 173, 129),
        (92, 200, 99),
        (170, 220, 50),
        (253, 231, 37),
    ],
    dtype=np.float32,
)


def _viridis_rgb(arr: np.ndarray) -> np.ndarray:
    """Small local viridis approximation, avoiding a matplotlib runtime dep."""
    arr_f = np.asarray(arr, dtype=np.float32)
    mn = float(np.min(arr_f))
    mx = float(np.max(arr_f))
    if mx > mn:
        x = (arr_f - mn) / (mx - mn)
    else:
        x = np.zeros_like(arr_f, dtype=np.float32)
    channels = [np.interp(x, _VIRIDIS_POS, _VIRIDIS_RGB[:, i]) for i in range(3)]
    return np.stack(channels, axis=-1).astype(np.uint8)


_DETR_IMAGE_MEAN = np.asarray((0.485, 0.456, 0.406), dtype=np.float32)
_DETR_IMAGE_STD = np.asarray((0.229, 0.224, 0.225), dtype=np.float32)


def _detr_preprocess_rgb_batch(images: list[np.ndarray]) -> np.ndarray:
    """Local DETR rescale/normalize/pad transform → ``(N, 3, H, W)`` float32."""
    if not images:
        return np.empty((0, 3, 0, 0), dtype=np.float32)

    max_h = max(int(img.shape[0]) for img in images)
    max_w = max(int(img.shape[1]) for img in images)
    batch = np.zeros((len(images), 3, max_h, max_w), dtype=np.float32)
    for idx, img in enumerate(images):
        arr = np.asarray(img, dtype=np.float32)
        if arr.ndim != 3 or arr.shape[2] != 3:
            raise CueProducerUnavailable(f"expected RGB image array, got shape {arr.shape}")
        arr = (arr / 255.0 - _DETR_IMAGE_MEAN) / _DETR_IMAGE_STD
        chw = np.transpose(arr, (2, 0, 1)).astype(np.float32, copy=False)
        batch[idx, :, : chw.shape[1], : chw.shape[2]] = chw
    return batch


def _build_windows(audio_path: Path | str):
    """Decode → viridis log-mel image → DETR-normalized sliding-window tensor + borders.

    Replicates the published CUE-DETR ingestion (mel @ 22050, viridis RGB,
    do_resize=False DETR preprocessing). Heavy deps are imported here (lazy) — any ImportError
    surfaces as CueProducerUnavailable upstream.
    """
    from vibemix.library.audio_decode import (
        cue_log_mel_spectrogram_db,
        load_audio_mono,
    )

    y = load_audio_mono(audio_path, target_sr=_MEL_SR)
    arr = cue_log_mel_spectrogram_db(
        y,
        sr=_MEL_SR,
        n_fft=_N_FFT,
        hop_length=_HOP,
        n_mels=_N_MELS,
    )[::-1]
    rgb = _viridis_rgb(arr)  # (mel_bins, frames, 3)

    image_w = rgb.shape[1] + _PADDING
    n_windows = int(np.floor(image_w / (_W_WIN * (1 - _OVERLAP))))
    segs: list[np.ndarray] = []
    borders: list[int] = []
    for i in range(n_windows):
        left = int(np.floor(i * _W_WIN * (1 - _OVERLAP))) - _PADDING
        right = left + _W_WIN
        borders.append(left)
        if left < 0:
            seg = np.pad(rgb[:, :right], ((0, 0), (-left, 0), (0, 0)), mode="linear_ramp")
        elif right > rgb.shape[1]:
            pad = right - left - (rgb.shape[1] - left)
            seg = np.pad(rgb[:, left:], ((0, 0), (0, pad), (0, 0)), mode="linear_ramp")
        else:
            seg = rgb[:, left:right]
        segs.append(seg)

    return _detr_preprocess_rgb_batch(segs), borders


def detect_cue_positions(
    audio_path: Path | str,
    *,
    sensitivity: float = DEFAULT_SENSITIVITY,
    radius: int = DEFAULT_RADIUS,
) -> list[float]:
    """Detect candidate cue positions (seconds) via the CUE-DETR ONNX model.

    Raises:
        CueProducerUnavailable: onnxruntime / the model file / a preprocessing dep is
            missing — the caller falls back to the heuristic.
    """
    mp = model_path()
    if not mp.exists():
        raise CueProducerUnavailable(f"CUE-DETR ONNX model not found at {mp}")
    try:
        import onnxruntime as ort
    except ImportError as exc:  # pragma: no cover - exercised only without the deps
        raise CueProducerUnavailable(f"missing runtime dependency: {exc}") from exc

    try:
        pixel_values, borders = _build_windows(audio_path)
        sess = ort.InferenceSession(str(mp), providers=["CPUExecutionProvider"])
        outs = sess.run(None, {"pixel_values": pixel_values})
        # Identify outputs by trailing dim: boxes end in 4, logits in classes+1.
        boxes = next(o for o in outs if o.shape[-1] == 4)
        logits = next(o for o in outs if o.shape[-1] != 4)
        frames = _positions_from_outputs(
            logits, boxes, borders, sensitivity=sensitivity, radius=radius
        )
    except CueProducerUnavailable:
        raise
    except Exception as exc:  # pragma: no cover - defensive: a broken model / bad audio
        raise CueProducerUnavailable(f"CUE-DETR inference failed: {exc}") from exc

    from vibemix.library.audio_decode import frames_to_time

    return [float(t) for t in frames_to_time(frames, sr=_MEL_SR, hop_length=_HOP)]
