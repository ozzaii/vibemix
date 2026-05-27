# SPDX-License-Identifier: Apache-2.0
"""Tests for ``vibemix.library.cue_refine`` — phrase-lock + dedup of producer cues.

Synthetic numpy audio with ``decode_to_mono`` monkeypatched (same idiom as
``test_cue_detect``), so no ffmpeg / real files. The producer (CUE-DETR) is NOT
exercised here — these tests pin the dep-free refine stage that turns noisy
candidate positions into clean, phrase-spaced cues.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from vibemix.library import cue_refine
from vibemix.library.cue_detect import ANALYSIS_SR
from vibemix.library.cue_refine import RefinedCue, refine_cue_positions

_FAKE = Path("fake.mp3")


def _kick_track(bpm: float = 128.0, seconds: float = 90.0, sr: int = ANALYSIS_SR) -> np.ndarray:
    """A 4-on-floor 60Hz kick at ``bpm`` plus a faint mid bed (so BPM locks)."""
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


def _drone(seconds: float = 90.0, sr: int = ANALYSIS_SR) -> np.ndarray:
    """A steady mid tone — no kick → no beat grid (forces the unsnapped path)."""
    t = np.arange(int(seconds * sr)) / sr
    return (0.3 * np.sin(2 * np.pi * 500.0 * t)).astype(np.float32)


@pytest.fixture
def kick(monkeypatch: pytest.MonkeyPatch) -> np.ndarray:
    track = _kick_track()
    monkeypatch.setattr(cue_refine, "decode_to_mono", lambda *_a, **_k: track)
    return track


@pytest.fixture
def drone(monkeypatch: pytest.MonkeyPatch) -> np.ndarray:
    track = _drone()
    monkeypatch.setattr(cue_refine, "decode_to_mono", lambda *_a, **_k: track)
    return track


# ─── core behaviour ───────────────────────────────────────────────────────────


def test_clustered_candidates_collapse_per_phrase(kick: np.ndarray) -> None:
    # Four tight clusters (each spans ~1s) separated by ~15s — the producer's
    # duplicate-spray shape. Each cluster must collapse to a single cue.
    cands = [10.0, 10.2, 10.5, 11.0, 25.0, 25.3, 40.0, 40.1, 40.4, 55.0]
    out = refine_cue_positions(_FAKE, cands)

    assert all(isinstance(c, RefinedCue) for c in out)
    assert 0 < len(out) < len(cands), f"{len(cands)} raw must collapse, got {len(out)}"
    # The four clusters → ~four cues (snapping may merge adjacent phrases).
    assert 3 <= len(out) <= 5, [round(c.position_s, 1) for c in out]
    # Ascending, and kept cues are well separated (dedup happened).
    pos = [c.position_s for c in out]
    assert pos == sorted(pos)
    gaps = np.diff(pos)
    assert all(g >= 5.0 for g in gaps), f"cues too close — dedup failed: {pos}"


def test_empty_candidates_returns_empty(kick: np.ndarray) -> None:
    assert refine_cue_positions(_FAKE, []) == []
    assert refine_cue_positions(_FAKE, None) == []


def test_invalid_candidates_filtered(kick: np.ndarray) -> None:
    # NaN / inf / negative / past-end / non-numeric are dropped, valid survive.
    cands = [float("nan"), float("inf"), -5.0, 1e9, "x", None, 20.0, 50.0]
    out = refine_cue_positions(_FAKE, cands)
    assert out, "the two valid candidates must survive"
    assert all(0.0 <= c.position_s <= 90.0 for c in out)


def test_short_track_returns_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    short = _kick_track(seconds=10.0)  # < MIN_TRACK_S
    monkeypatch.setattr(cue_refine, "decode_to_mono", lambda *_a, **_k: short)
    assert refine_cue_positions(_FAKE, [3.0, 5.0]) == []


def test_no_grid_dedups_unsnapped(drone: np.ndarray) -> None:
    # No beat → no grid: still de-duplicated by the section time floor, but every
    # cue is honestly unsnapped (never snapped onto a fabricated grid).
    cands = [10.0, 11.0, 12.0, 40.0, 41.0, 70.0]
    out = refine_cue_positions(_FAKE, cands)
    assert out
    assert all(c.snapped is False and c.snap_confidence == 0.0 for c in out)
    assert len(out) < len(cands)
    gaps = np.diff([c.position_s for c in out])
    assert all(g >= 15.0 for g in gaps), "no-grid dedup must respect the section floor"


def test_determinism(kick: np.ndarray) -> None:
    cands = [10.0, 10.3, 25.0, 40.0, 55.0]
    a = refine_cue_positions(_FAKE, cands)
    b = refine_cue_positions(_FAKE, cands)
    assert a == b


def test_phrase_bars_must_be_positive(kick: np.ndarray) -> None:
    with pytest.raises(ValueError):
        refine_cue_positions(_FAKE, [10.0, 30.0], phrase_bars=0)


def test_larger_phrase_merges_more(kick: np.ndarray) -> None:
    # A wider phrase window must keep no more cues than a tighter one.
    cands = [10.0, 18.0, 26.0, 34.0, 42.0, 50.0]
    tight = refine_cue_positions(_FAKE, cands, phrase_bars=4)
    wide = refine_cue_positions(_FAKE, cands, phrase_bars=16)
    assert len(wide) <= len(tight)
