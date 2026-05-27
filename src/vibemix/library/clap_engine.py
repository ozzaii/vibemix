# SPDX-License-Identifier: Apache-2.0
"""ClapEngine — local, on-device CLAP audio/text embedder (512-dim).

WIRED product path. ``ClapEmbedder`` uses this engine on the ``onnx`` backend;
the legacy cloud embedder is no longer selected for library embeddings.

# What it is
============

A deterministic, on-device embedder built on the LAION-CLAP ``HTSAT-tiny``
music checkpoint. It maps both audio and text into ONE 512-dim space, so the
library vibe-search / curator / next-suggestion layer can run with ZERO API
cost and audio that never leaves the device. CLAP is an on-device *embedding*
model, NOT a second LLM provider; it does not change the selected
conversational/co-host brain.

# The proven pipeline (ported byte-for-byte from bravoh-gpu-worker/clap_mix_only.py)
=================================================================================

    load audio → mono (mean across channels) → resample to 48kHz
      ├─ total <= CHUNK_SAMPLES (10s): zero-pad to one CHUNK_SAMPLES chunk
      └─ else: non-overlapping 10s slices; a trailing remainder >= 5s is
               zero-padded and kept as a final chunk
    per chunk: CLAP.get_audio_embedding_from_data(batch, use_tensor=False)
    L2-normalize EACH chunk emb (norm + 1e-8) → mean-pool → re-L2-normalize
    → (512,) float32

WHY the 10s-chunk + mean-pool: it is DETERMINISTIC. CLAP's fusion path applies a
random truncation when fed a clip longer than its native 10s ``clip_samples``;
feeding it exact 10s chunks bypasses that randomness, so re-embedding the same
file yields a bit-identical vector (proven: re-embed cos = 1.000000, max|Δ| = 0).

# Lazy-import contract (the load-bearing acceptance)
==================================================

The heavy deps — ``torch`` / ``torchaudio`` / ``laion_clap`` (torch backend)
and ``onnxruntime`` / ``tokenizers`` / ``av`` (the ONNX ship backend) —
are NEVER imported at module top
level. They are imported INSIDE ``_ensure_model`` / ``_load_and_chunk`` only.
This mirrors ``library/telegram_bridge.py``'s convention for
``python-telegram-bot``: ``import vibemix.library.clap_engine`` succeeds in CI
and in the live co-host bundle where none of those deps are installed. The
module top level pulls only numpy + stdlib + ``__future__``.

# Backends
=========

* ``onnx`` (default) — cross-platform ship path using Xenova/larger_clap_music_and_speech
  via onnxruntime + local Slaney log-mel. ``ClapEmbedder`` uses
  this backend for the product CLAP path.
* ``torch`` — the LAION-CLAP reference path above. Requires
  ``torch`` + ``torchaudio`` + ``laion_clap`` to be installed at call time.

Select via the ``backend=`` arg or the ``VIBEMIX_CLAP_BACKEND`` env var
(default ``"onnx"``).
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import numpy as np

from vibemix.library.cache_paths import (
    CLAP_ONNX_ENV,
    DEFAULT_CLAP_ONNX_DIR,
    clap_onnx_dir,
)

# --------------------------------------------------------------------------- #
# Proven pipeline constants — ported VERBATIM from clap_mix_only.py.           #
# Do not re-tune: these define the determinism + the 512-dim contract.        #
# --------------------------------------------------------------------------- #
CLAP_SR = 48000  # CLAP's native sample rate
CHUNK_SAMPLES = 480000  # 10s @ 48kHz — CLAP's native clip_samples
CHUNK_BATCH = 128  # chunks per CLAP forward pass
CLAP_DIM = 512  # output embedding dimensionality

_ENV_BACKEND = "VIBEMIX_CLAP_BACKEND"
_DEFAULT_BACKEND = "onnx"
_VALID_BACKENDS = ("torch", "onnx")

# ---- onnx backend (Xenova/larger_clap_music_and_speech, non-fusion) ----------
# The ONNX ship path. Model dir holds the HF-format repo snapshot:
#   onnx/audio_model.onnx  (ClapAudioModelWithProjection, input "input_features")
#   onnx/text_model.onnx   (ClapTextModelWithProjection, input "input_ids" ONLY)
#   preprocessor_config.json + tokenizer files (for ClapFeatureExtractor / Roberta)
# Override the dir with VIBEMIX_CLAP_ONNX_DIR; default is the vibemix cache.
_ENV_ONNX_DIR = CLAP_ONNX_ENV
_DEFAULT_ONNX_DIR = DEFAULT_CLAP_ONNX_DIR
_ONNX_AUDIO_REL = "onnx/audio_model.onnx"
_ONNX_TEXT_REL = "onnx/text_model.onnx"
_ONNX_REQUIRED_RELS = (
    _ONNX_AUDIO_REL,
    _ONNX_TEXT_REL,
    "preprocessor_config.json",
    "tokenizer.json",
    "vocab.json",
    "merges.txt",
)
# Non-fusion Xenova mel is 10s @ 48k; one 10s segment per ONNX forward (batch=1
# model). Non-overlapping slices match the validated parity run (techno+psy 100%).
_ONNX_TEXT_MAXLEN = 77  # CLAP text is trained/used at length 77
# Log-mel frontend (Xenova ClapFeatureExtractor config). Computed via local
# numpy primitives: Slaney filterbank, Hann window, frame 1024 / hop 480,
# power 2.0, log_mel="dB". Shape fed to the audio ONNX:
# (1, 1, n_frames=1001, _ONNX_N_MELS=64).
_ONNX_N_FFT = 1024
_ONNX_HOP = 480
_ONNX_N_MELS = 64
_ONNX_FMIN = 50
_ONNX_FMAX = 14000
_ONNX_NB_FREQ_BINS = (_ONNX_N_FFT >> 1) + 1  # 513

# MIME suffix mapping for the bytes path (mirrors embed._mime_for_path's idea,
# inverted: mime → tempfile suffix). Default .mp3.
_MIME_TO_SUFFIX = {
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/flac": ".flac",
    "audio/x-flac": ".flac",
    "audio/mp4": ".m4a",
    "audio/aac": ".aac",
    "audio/mpeg": ".mp3",
    "audio/mp3": ".mp3",
}


def onnx_model_status() -> dict[str, object]:
    """Return lightweight CLAP ONNX asset status without importing heavy deps."""
    root = clap_onnx_dir()
    missing = [rel for rel in _ONNX_REQUIRED_RELS if not (root / rel).is_file()]
    mismatched: list[str] = []
    try:
        from vibemix.library.model_assets import clap_model_files

        specs = {spec.rel_path: spec for spec in clap_model_files()}
        for rel in _ONNX_REQUIRED_RELS:
            path = root / rel
            spec = specs.get(rel)
            if spec is not None and path.is_file() and path.stat().st_size != spec.size:
                mismatched.append(rel)
    except Exception:
        # Status must stay best-effort and import-safe; install_clap_model()
        # performs the authoritative SHA-256 verification when the user repairs
        # the cache.
        mismatched = []
    return {
        "installed": not missing and not mismatched,
        "path": str(root),
        "missing": missing,
        "mismatched": mismatched,
    }


def _l2(vec: np.ndarray) -> np.ndarray:
    """L2-normalize a 1-D vector with the same 1e-8 floor the reference uses."""
    return vec / (np.linalg.norm(vec) + 1e-8)


class ClapEngine:
    """Local on-device CLAP 512-dim embedder (audio + text, one space).

    Import-safe: constructing the engine never imports a heavy dep. The model is
    lazy-loaded ONCE on the first embed call and cached on ``self._model`` (warm
    reuse — never reloaded per call). Public contract mirrors what a future
    ``ClapEmbedder`` will expose 1:1:

        embed_audio_file(path)        -> (512,) float32, L2-normalized
        embed_audio_bytes(data, mime) -> (512,) float32, L2-normalized
        embed_query(text)             -> (512,) float32, L2-normalized
    """

    def __init__(self, backend: str | None = None) -> None:
        resolved = (backend or os.environ.get(_ENV_BACKEND) or _DEFAULT_BACKEND)
        resolved = resolved.lower().strip()
        if resolved not in _VALID_BACKENDS:
            raise ValueError(
                f"ClapEngine backend must be one of {_VALID_BACKENDS}, "
                f"got {resolved!r}"
            )
        self.backend = resolved
        # Lazy: the model object (torch CLAP_Module) is loaded on first use and
        # cached here. Construction stays import-safe — no heavy import here.
        self._model = None

    # ------------------------------------------------------------------ #
    # Model loading (lazy, heavy imports live HERE — never at top level)  #
    # ------------------------------------------------------------------ #
    def _ensure_model(self):
        """Load + cache the CLAP model once for either backend."""
        if self._model is not None:
            return self._model

        if self.backend == "onnx":
            return self._ensure_onnx_model()

        # ----- torch backend (the proven reference path) -----
        # MPS fallback so an unsupported op on Apple silicon falls back to CPU
        # rather than erroring (clap_mix_only sets this before loading).
        os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")

        import torch  # lazy — heavy

        # The two monkeypatches are MANDATORY for newer torch loading the older
        # LAION checkpoint: (1) torch.load defaults to weights_only=True on
        # recent torch and refuses the pickled checkpoint; (2) the checkpoint's
        # state_dict has minor key drift, so load_state_dict must be strict=False.
        # BOTH originals are restored after load so the rest of the process is
        # untouched.
        _real_load = torch.load
        torch.load = lambda *a, **kw: _real_load(  # type: ignore[assignment]
            *a, **{**kw, "weights_only": False}
        )

        import laion_clap  # lazy — heavy (and itself imports torch)

        _orig_lsd = torch.nn.Module.load_state_dict
        torch.nn.Module.load_state_dict = lambda self, sd, **kw: _orig_lsd(  # type: ignore[assignment]
            self, sd, strict=False, **{k: v for k, v in kw.items() if k != "strict"}
        )

        try:
            clap = laion_clap.CLAP_Module(
                enable_fusion=True, amodel="HTSAT-tiny", device="cpu"
            )
            clap.load_ckpt(model_id=3)  # the music checkpoint
        finally:
            # Restore the originals whether or not the load succeeded.
            torch.nn.Module.load_state_dict = _orig_lsd
            torch.load = _real_load

        self._model = clap
        return self._model

    # ------------------------------------------------------------------ #
    # Audio loading + chunking (ported EXACTLY from load_and_chunk)        #
    # ------------------------------------------------------------------ #
    def _load_and_chunk(self, path: str) -> list[np.ndarray]:
        """Load → mono → 48kHz → list of (CHUNK_SAMPLES,) float32 chunks.

        Ported verbatim from clap_mix_only.load_and_chunk: the <=CHUNK_SAMPLES
        zero-pad single-chunk branch, the non-overlapping slice loop, and the
        trailing remainder >= 5s rule.
        """
        import torchaudio  # lazy — heavy

        wav, sr = torchaudio.load(path)

        # Mix to mono (mean across channels), then squeeze to (samples,).
        if wav.shape[0] > 1:
            wav = wav.mean(dim=0, keepdim=True)
        wav = wav[0]

        # Resample to 48kHz.
        if sr != CLAP_SR:
            wav = torchaudio.functional.resample(wav, sr, CLAP_SR)

        samples = wav.numpy()
        total = len(samples)

        if total <= CHUNK_SAMPLES:
            padded = np.zeros(CHUNK_SAMPLES, dtype=np.float32)
            padded[:total] = samples
            return [padded]

        chunks: list[np.ndarray] = []
        for start in range(0, total - CHUNK_SAMPLES + 1, CHUNK_SAMPLES):
            chunks.append(samples[start : start + CHUNK_SAMPLES].astype(np.float32))

        remainder = total % CHUNK_SAMPLES
        if remainder >= CLAP_SR * 5:  # keep a trailing chunk >= 5s
            padded = np.zeros(CHUNK_SAMPLES, dtype=np.float32)
            padded[:remainder] = samples[-remainder:]
            chunks.append(padded)

        return chunks

    # ------------------------------------------------------------------ #
    # Chunk embedding (ported EXACTLY from embed_chunks)                   #
    # ------------------------------------------------------------------ #
    def _embed_chunks(self, chunks: list[np.ndarray]) -> np.ndarray:
        """Batch-embed chunks → per-chunk L2 → mean-pool → re-L2 → (512,) f32."""
        clap = self._ensure_model()
        all_embs: list[np.ndarray] = []
        for i in range(0, len(chunks), CHUNK_BATCH):
            batch = chunks[i : i + CHUNK_BATCH]
            batch_np = np.stack(batch)
            embs = clap.get_audio_embedding_from_data(batch_np, use_tensor=False)
            norms = np.linalg.norm(embs, axis=1, keepdims=True) + 1e-8
            embs = embs / norms
            all_embs.append(embs)

        stacked = np.concatenate(all_embs, axis=0)
        mean_emb = stacked.mean(axis=0)
        mean_emb = mean_emb / (np.linalg.norm(mean_emb) + 1e-8)
        return mean_emb.astype(np.float32)

    # ------------------------------------------------------------------ #
    # ONNX backend (Xenova non-fusion; onnxruntime + local mel/tokenizer)  #
    # Heavy imports (onnxruntime/tokenizers/av) live HERE only.            #
    # ------------------------------------------------------------------ #
    def _ensure_onnx_model(self):
        """Load + cache the Xenova ONNX sessions + feature extractor + tokenizer.

        Cached on ``self._model`` as a dict. The model dir (env
        ``VIBEMIX_CLAP_ONNX_DIR`` or the vibemix cache) must hold the HF-format
        snapshot — see ``_DEFAULT_ONNX_DIR`` doc above. Raises a clear, actionable
        error (NOT a wrong vector) when the model files are absent.
        """
        import onnxruntime as ort  # lazy — ship dep
        from tokenizers import Tokenizer  # lazy — ship dep

        mdir = clap_onnx_dir()
        audio_path = mdir / _ONNX_AUDIO_REL
        text_path = mdir / _ONNX_TEXT_REL
        if not audio_path.exists() or not text_path.exists():
            raise FileNotFoundError(
                f"ClapEngine onnx backend: model files not found under {mdir}. "
                f"Expected {_ONNX_AUDIO_REL} + {_ONNX_TEXT_REL} (+ tokenizer "
                f"config). Download Xenova/larger_clap_music_and_speech "
                f"or set {_ENV_ONNX_DIR}."
            )

        tok = Tokenizer.from_file(str(mdir / "tokenizer.json"))
        tok.enable_truncation(max_length=_ONNX_TEXT_MAXLEN)
        from vibemix.library.audio_features import mel_filter_bank

        mel_slaney = mel_filter_bank(
            num_frequency_bins=_ONNX_NB_FREQ_BINS,
            num_mel_filters=_ONNX_N_MELS,
            min_frequency=_ONNX_FMIN,
            max_frequency=_ONNX_FMAX,
            sampling_rate=CLAP_SR,
            norm="slaney",
        )
        providers = ["CPUExecutionProvider"]
        audio_sess = ort.InferenceSession(str(audio_path), providers=providers)
        text_sess = ort.InferenceSession(str(text_path), providers=providers)
        # The Xenova text ONNX takes ONLY input_ids (no attention_mask). Detect
        # which inputs it accepts so we never feed an unknown tensor.
        text_inputs = {i.name for i in text_sess.get_inputs()}
        self._model = {
            "tok": tok,
            "audio": audio_sess,
            "text": text_sess,
            "text_inputs": text_inputs,
            "mel_slaney": mel_slaney,
        }
        return self._model

    @staticmethod
    def _onnx_logmel(seg: np.ndarray, mel_filters: np.ndarray) -> np.ndarray:
        """Log-mel for one 10s segment → (1, 1, n_frames=1001, N_MELS=64).

        Torch-free (the reason the ONNX path exists): Hann window, frame
        1024 / hop 480, power 2.0, Slaney mel filterbank, log_mel="dB"."""
        from vibemix.library.audio_features import spectrogram, window_function

        log_mel = spectrogram(
            np.asarray(seg, dtype=np.float64),
            window_function(_ONNX_N_FFT, "hann"),
            frame_length=_ONNX_N_FFT,
            hop_length=_ONNX_HOP,
            power=2.0,
            mel_filters=mel_filters,
            log_mel="dB",
        )
        lm = log_mel.T.astype(np.float32)  # (n_frames, n_mels)
        return lm[np.newaxis, np.newaxis, :, :]

    def _onnx_embed_audio_file(self, path: str) -> np.ndarray:
        """ONNX audio embed: non-overlapping 10s segs → HF mel → audio ONNX →
        mean-pool → L2 → (512,). Matches the validated parity pipeline."""
        from vibemix.library.audio_decode import load_audio_mono

        m = self._ensure_onnx_model()
        y = load_audio_mono(path, target_sr=CLAP_SR)
        if len(y) == 0:
            raise ValueError(f"ClapEngine: empty audio from {path!r}")
        if len(y) < CHUNK_SAMPLES:  # repeat-pad short clips to one 10s window
            reps = int(np.ceil(CHUNK_SAMPLES / len(y)))
            y = np.tile(y, reps)[:CHUNK_SAMPLES]
        segs = [
            y[i : i + CHUNK_SAMPLES]
            for i in range(0, len(y) - CHUNK_SAMPLES + 1, CHUNK_SAMPLES)
        ] or [y[:CHUNK_SAMPLES]]

        embs: list[np.ndarray] = []
        for seg in segs:
            inp = self._onnx_logmel(seg, m["mel_slaney"])
            out = m["audio"].run(None, {"input_features": inp})[0]
            embs.append(out[0])
        mean_emb = np.mean(np.stack(embs), axis=0)
        return _l2(mean_emb).astype(np.float32)

    def _onnx_embed_text(self, text: str) -> np.ndarray:
        """ONNX text embed: ONE query, UNPADDED (the text ONNX has no
        attention_mask → padding tokens collapse the output) → (512,) L2."""
        m = self._ensure_onnx_model()
        enc = m["tok"].encode(text)
        feed = {"input_ids": np.asarray(enc.ids, dtype=np.int64)[np.newaxis, :]}
        if "attention_mask" in m["text_inputs"]:
            feed["attention_mask"] = np.asarray(enc.attention_mask, dtype=np.int64)[
                np.newaxis, :
            ]
        out = m["text"].run(None, feed)[0][0]
        return _l2(np.asarray(out)).astype(np.float32)

    # ------------------------------------------------------------------ #
    # Public contract                                                     #
    # ------------------------------------------------------------------ #
    def embed_audio_file(self, path: str) -> np.ndarray:
        """Embed an audio file → (512,) float32, L2-normalized, deterministic."""
        if self.backend == "onnx":
            return self._onnx_embed_audio_file(path)
        self._ensure_model()
        chunks = self._load_and_chunk(path)
        if not chunks:
            # Trust-the-audio / no-slop: never fabricate a zero vector for an
            # unreadable or empty file — surface it honestly.
            raise ValueError(f"ClapEngine: no audio chunks produced from {path!r}")
        return self._embed_chunks(chunks)

    def embed_audio_bytes(self, data: bytes, mime: str) -> np.ndarray:
        """Embed raw audio bytes → (512,) float32 — same pipeline as a file.

        Writes the bytes to a tempfile with a MIME-appropriate suffix (defaults
        to ``.mp3``), routes through the SAME load → chunk → embed path, then
        cleans up the tempfile.
        """
        suffix = _MIME_TO_SUFFIX.get((mime or "").lower().strip(), ".mp3")
        tmp_path: str | None = None
        try:
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as fh:
                fh.write(data)
                tmp_path = fh.name
            return self.embed_audio_file(tmp_path)
        finally:
            if tmp_path is not None:
                try:
                    Path(tmp_path).unlink()
                except OSError:
                    pass

    def embed_query(self, text: str) -> np.ndarray:
        """Embed a text query → (512,) float32, L2-normalized — same space."""
        if self.backend == "onnx":
            return self._onnx_embed_text(text)
        clap = self._ensure_model()
        embs = clap.get_text_embedding([text], use_tensor=False)
        vec = np.asarray(embs)[0]
        return _l2(vec).astype(np.float32)
