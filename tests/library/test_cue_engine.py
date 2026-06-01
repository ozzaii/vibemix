# SPDX-License-Identifier: Apache-2.0
"""Tests for the auto-cue engine assembly (``cue_detr`` post-process + ``cue_engine``).

The ONNX model + onnxruntime are NOT present in CI, so the heavy inference path is not
exercised here; we pin the pure-numpy post-process, the guarded ``CueProducerUnavailable``
contract, the position→CueAnchor assembly (decode monkeypatched), and the producer→heuristic
fallback. Synthetic audio, no ffmpeg / real model.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from vibemix.library import cue_detr, cue_engine, cue_refine
from vibemix.library.cue_detect import ANALYSIS_SR
from vibemix.library.cue_detr import (
    _DETR_IMAGE_MEAN,
    _DETR_IMAGE_STD,
    CueProducerUnavailable,
    _detr_preprocess_rgb_batch,
    _positions_from_outputs,
)
from vibemix.library.cue_engine import build_cue_anchors, detect_cues_auto
from vibemix.library.cue_refine import RefinedCue
from vibemix.library.cue_types import CueAnchor

_FAKE = Path("fake.mp3")
_VALID = {"intro", "build", "breakdown", "drop", "outro"}


def _kick_track(bpm: float = 128.0, seconds: float = 90.0, sr: int = ANALYSIS_SR) -> np.ndarray:
    n = int(seconds * sr)
    out = np.zeros(n, dtype=np.float32)
    period = int((60.0 / bpm) * sr)
    klen = int(0.12 * sr)
    t = np.arange(klen) / sr
    thump = (np.sin(2 * np.pi * 60.0 * t) * np.exp(-t * 30.0)).astype(np.float32)
    for start in range(0, n - klen, max(1, period)):
        out[start : start + klen] += thump
    tt = np.arange(n) / sr
    out += (0.05 * np.sin(2 * np.pi * 440.0 * tt)).astype(np.float32)
    return out


@pytest.fixture
def kick(monkeypatch: pytest.MonkeyPatch) -> np.ndarray:
    track = _kick_track()
    # build_cue_anchors decodes (cue_engine) and refine decodes (cue_refine).
    monkeypatch.setattr(cue_engine, "decode_to_mono", lambda *_a, **_k: track)
    monkeypatch.setattr(cue_refine, "decode_to_mono", lambda *_a, **_k: track)
    return track


# ─── cue_detr post-process (pure numpy) ─────────────────────────────────────────


def test_positions_from_outputs_picks_peak() -> None:
    # One window, 5 queries; cue logit shaped so softmax peaks at query 2.
    logits = np.array([[[-2, 0], [-1, 0], [3, 0], [-1, 0], [-2, 0]]], dtype=np.float32)
    cx = np.array([0.0, 0.25, 0.5, 0.75, 0.99], dtype=np.float32)
    boxes = np.zeros((1, 5, 4), dtype=np.float32)
    boxes[0, :, 0] = cx
    pos = _positions_from_outputs(logits, boxes, [0], sensitivity=0.5, radius=4)
    # Peak query is idx 2 → centre = round(0.5 * 355) = 177 frames.
    assert pos == [177]


def test_positions_from_outputs_empty() -> None:
    empty_log = np.zeros((0, 5, 2), dtype=np.float32)
    empty_box = np.zeros((0, 5, 4), dtype=np.float32)
    assert _positions_from_outputs(empty_log, empty_box, [], sensitivity=0.5, radius=4) == []


def test_producer_unavailable_when_model_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("VIBEMIX_CUE_ONNX_PATH", str(tmp_path / "nope.onnx"))
    with pytest.raises(CueProducerUnavailable):
        cue_detr.detect_cue_positions(_FAKE)


def test_detr_preprocess_is_local_config() -> None:
    img = np.full((2, 3, 3), 255, dtype=np.uint8)

    batch = _detr_preprocess_rgb_batch([img])

    assert batch.shape == (1, 3, 2, 3)
    expected = (np.ones(3, dtype=np.float32) - _DETR_IMAGE_MEAN) / _DETR_IMAGE_STD
    np.testing.assert_allclose(batch[0, :, 0, 0], expected, rtol=1e-6)


def test_detr_preprocess_pads_to_largest_image() -> None:
    small = np.zeros((2, 3, 3), dtype=np.uint8)
    large = np.zeros((4, 5, 3), dtype=np.uint8)

    batch = _detr_preprocess_rgb_batch([small, large])

    assert batch.shape == (2, 3, 4, 5)
    np.testing.assert_allclose(batch[0, :, 2:, :], 0.0)


# ─── build_cue_anchors (decode monkeypatched) ───────────────────────────────────


def _assert_anchor_contract(anchors: list[CueAnchor]) -> None:
    assert all(isinstance(a, CueAnchor) for a in anchors)
    for a in anchors:
        assert a.label in _VALID, a.label
        assert a.source == "auto"
        assert 0.0 <= a.confidence <= 1.0
        assert a.start_s < a.end_s
        assert (a.end_s - a.start_s) <= 80.0 + 1e-6
    starts = [a.start_s for a in anchors]
    assert starts == sorted(starts)


def test_build_cue_anchors_contract(kick: np.ndarray) -> None:
    anchors = build_cue_anchors(_FAKE, [10.0, 25.0, 40.0, 55.0, 70.0])
    assert anchors
    _assert_anchor_contract(anchors)


def test_build_cue_anchors_empty_positions(kick: np.ndarray) -> None:
    assert build_cue_anchors(_FAKE, []) == []


def test_build_cue_anchors_short_track(monkeypatch: pytest.MonkeyPatch) -> None:
    short = _kick_track(seconds=10.0)
    monkeypatch.setattr(cue_engine, "decode_to_mono", lambda *_a, **_k: short)
    monkeypatch.setattr(cue_refine, "decode_to_mono", lambda *_a, **_k: short)
    assert build_cue_anchors(_FAKE, [3.0, 5.0]) == []


def test_build_cue_anchors_first_is_intro_last_is_outro(kick: np.ndarray) -> None:
    anchors = build_cue_anchors(_FAKE, [1.0, 30.0, 45.0, 88.0])
    assert anchors[0].label == "intro"
    assert anchors[-1].label == "outro"


def test_build_cue_anchors_clamps_to_audible_bounds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    silence = np.zeros(int(10.0 * ANALYSIS_SR), dtype=np.float32)
    core = _kick_track(seconds=70.0)
    track = np.concatenate([silence, core, silence]).astype(np.float32)
    monkeypatch.setattr(cue_engine, "decode_to_mono", lambda *_a, **_k: track)
    monkeypatch.setattr(
        cue_engine,
        "refine_cue_positions",
        lambda *_a, **_k: [
            RefinedCue(1.0, False, 0.0),
            RefinedCue(20.0, False, 0.0),
            RefinedCue(88.0, False, 0.0),
        ],
    )

    anchors = build_cue_anchors(_FAKE, [1.0, 20.0, 88.0])

    assert anchors
    _assert_anchor_contract(anchors)
    assert all(a.start_s >= 9.0 for a in anchors)
    assert all(a.end_s <= 82.0 for a in anchors)
    assert all(a.start_s < 88.0 for a in anchors)


def test_build_cue_anchors_suppresses_all_silent_audio(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    silent = np.zeros(int(90.0 * ANALYSIS_SR), dtype=np.float32)
    monkeypatch.setattr(cue_engine, "decode_to_mono", lambda *_a, **_k: silent)
    monkeypatch.setattr(
        cue_engine,
        "refine_cue_positions",
        lambda *_a, **_k: [RefinedCue(10.0, False, 0.0)],
    )

    assert build_cue_anchors(_FAKE, [10.0]) == []


# ─── detect_cues_auto orchestration ─────────────────────────────────────────────


def test_auto_falls_back_to_heuristic_when_producer_unavailable(
    kick: np.ndarray, monkeypatch: pytest.MonkeyPatch
) -> None:
    sentinel = [CueAnchor("drop", 10.0, 26.0, 0.9, "auto")]
    monkeypatch.setattr(
        cue_engine, "detect_cue_positions",
        lambda *_a, **_k: (_ for _ in ()).throw(CueProducerUnavailable("no model")),
    )
    monkeypatch.setattr(cue_engine, "detect_cues", lambda *_a, **_k: sentinel)
    assert detect_cues_auto(_FAKE) is sentinel


def test_auto_uses_engine_path_when_producer_available(
    kick: np.ndarray, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cue_engine, "detect_cue_positions", lambda *_a, **_k: [10.0, 30.0, 55.0])
    # heuristic would be a different result; assert we did NOT fall back.
    monkeypatch.setattr(cue_engine, "detect_cues", lambda *_a, **_k: [CueAnchor("drop", 1.0, 2.0, 0.1, "auto")])
    anchors = detect_cues_auto(_FAKE)
    assert anchors
    _assert_anchor_contract(anchors)
    assert not (len(anchors) == 1 and anchors[0].end_s == 2.0), "must not have fallen back"
