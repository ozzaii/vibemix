# SPDX-License-Identifier: Apache-2.0
"""Offline auto-cue detection tests (Path 2).

DETERMINISTIC, ZERO network, ZERO Gemini, default pytest selection. The pure
DSP is tested over synthetic numpy audio with ``decode_to_mono`` monkeypatched
so no ffmpeg binary / real audio file is needed. One ``@pytest.mark.integration``
test exercises the real ffmpeg decode path against a generated WAV.

Synthetic track shape (so the breakdown / re-entry edges are unambiguous):
    - A 4-on-the-floor sub-bass kick (60Hz sine pulses) drives the sub band.
    - section A (kick busy)  → high sub-share
    - section B (breakdown)  → kick removed, only a mid-band pad → sub collapses
    - section C (drop / re-entry) → kick back → sub recovers
The detector must find the breakdown edge in B and the re-entry edge in C.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from vibemix.library import cue_detect
from vibemix.library.cue_detect import (
    ANALYSIS_SR,
    _find_sub_edges,
    _rms_curve,
    _sub_energy_curve,
    detect_cues,
)
from vibemix.library.rekordbox import CuePoint


# ─── Synthetic audio ────────────────────────────────────────────────────────────


def _kick_section(seconds: float, sr: int, *, bpm: float = 128.0) -> np.ndarray:
    """A 4-on-floor sub kick: short 60Hz sine bursts at the beat period."""
    n = int(seconds * sr)
    out = np.zeros(n, dtype=np.float32)
    beat_period = int(sr * 60.0 / bpm)
    burst_len = int(0.08 * sr)  # 80ms thump
    t = np.arange(burst_len) / sr
    env = np.exp(-t * 25.0)  # fast decay
    thump = (np.sin(2 * np.pi * 60.0 * t) * env).astype(np.float32)
    pos = 0
    while pos + burst_len < n:
        out[pos : pos + burst_len] += thump
        pos += beat_period
    return out


def _pad_section(seconds: float, sr: int) -> np.ndarray:
    """A mid-band pad (800Hz) with NO sub content — a breakdown."""
    n = int(seconds * sr)
    t = np.arange(n) / sr
    return (0.3 * np.sin(2 * np.pi * 800.0 * t)).astype(np.float32)


def _synthetic_track(sr: int = ANALYSIS_SR) -> np.ndarray:
    """Kick(40s) → breakdown pad(16s) → kick drop(40s). ~96s total."""
    a = _kick_section(40.0, sr)
    b = _pad_section(16.0, sr)
    c = _kick_section(40.0, sr)
    return np.concatenate([a, b, c]).astype(np.float32)


@pytest.fixture
def synth() -> np.ndarray:
    return _synthetic_track()


# ─── Pure-DSP unit tests (no ffmpeg) ─────────────────────────────────────────────


def test_sub_energy_curve_dips_in_breakdown(synth: np.ndarray) -> None:
    curve = _sub_energy_curve(synth, ANALYSIS_SR)
    # ~96 frames at 1s hop.
    assert curve.size >= 90
    # Frames 0-39 = kick A (high sub), 40-55 = breakdown (low sub),
    # 56-95 = kick C (high sub).
    kick_a = float(np.median(curve[5:35]))
    breakdown = float(np.median(curve[42:54]))
    kick_c = float(np.median(curve[60:90]))
    assert kick_a > 0.0
    assert kick_c > 0.0
    # The breakdown sub-share must be materially below the kick sections.
    assert breakdown < 0.5 * kick_a
    assert breakdown < 0.5 * kick_c


def test_find_sub_edges_locates_breakdown_and_reentry(synth: np.ndarray) -> None:
    curve = _sub_energy_curve(synth, ANALYSIS_SR)
    rms = _rms_curve(synth, ANALYSIS_SR, curve.size)
    kills, reentries = _find_sub_edges(curve, rms)

    assert kills, "expected a breakdown (kill) edge"
    assert reentries, "expected a re-entry edge"
    # The kill should land in the breakdown region (~frame 40-55).
    assert any(38 <= k <= 57 for k in kills), kills
    # The re-entry should land at / after the drop (~frame 56+).
    assert any(r >= 54 for r in reentries), reentries
    # Re-entry comes after its paired kill.
    assert reentries[0] > kills[0]


def test_silent_input_yields_no_edges() -> None:
    silent = np.zeros(ANALYSIS_SR * 60, dtype=np.float32)
    curve = _sub_energy_curve(silent, ANALYSIS_SR)
    rms = _rms_curve(silent, ANALYSIS_SR, curve.size)
    kills, reentries = _find_sub_edges(curve, rms)
    # Anti-hallucination: no fabricated structure on silence.
    assert kills == []
    assert reentries == []


# ─── detect_cues (decode monkeypatched) ──────────────────────────────────────────


def test_detect_cues_deterministic_and_grounded(
    synth: np.ndarray, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cue_detect, "decode_to_mono", lambda *_a, **_k: synth)

    cues1 = detect_cues(Path("fake.mp3"), max_cues=4)
    cues2 = detect_cues(Path("fake.mp3"), max_cues=4)

    # Deterministic.
    assert cues1 == cues2
    # Ordered, hot-cue-numbered, valid Rekordbox types.
    assert all(isinstance(c, CuePoint) for c in cues1)
    assert 1 <= len(cues1) <= 4
    assert [c.number for c in cues1] == list(range(1, len(cues1) + 1))
    assert all(c.type in {"cue", "loop", "fadein", "fadeout", "load"} for c in cues1)
    starts = [c.start_s for c in cues1]
    assert starts == sorted(starts), "cues must be time-ordered"
    assert all(0.0 <= c.start_s for c in cues1)
    # A breakdown OR re-entry cue should sit in the structural middle of the
    # track (the synthetic breakdown is ~40-56s), proving the cues are anchored
    # on real audio events, not a fabricated even grid.
    assert any(35.0 <= c.start_s <= 75.0 for c in cues1)


def test_detect_cues_respects_max_cues(
    synth: np.ndarray, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cue_detect, "decode_to_mono", lambda *_a, **_k: synth)
    for m in (1, 2, 3):
        cues = detect_cues(Path("fake.mp3"), max_cues=m)
        assert len(cues) <= m


def test_detect_cues_short_track_single_load_cue(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    short = np.zeros(int(ANALYSIS_SR * 10), dtype=np.float32)  # 10s < MIN_TRACK_S
    monkeypatch.setattr(cue_detect, "decode_to_mono", lambda *_a, **_k: short)
    cues = detect_cues(Path("fake.mp3"), max_cues=4)
    assert len(cues) == 1
    assert cues[0].type == "load"
    assert cues[0].start_s == 0.0
    assert cues[0].number == 1


def test_detect_cues_empty_audio_single_load_cue(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        cue_detect, "decode_to_mono", lambda *_a, **_k: np.zeros(0, dtype=np.float32)
    )
    cues = detect_cues(Path("fake.mp3"), max_cues=4)
    assert len(cues) == 1
    assert cues[0].type == "load"


def test_detect_cues_no_network_no_gemini(
    synth: np.ndarray, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Guard: detect_cues must never import/use the genai client."""
    monkeypatch.setattr(cue_detect, "decode_to_mono", lambda *_a, **_k: synth)
    import sys

    # Poison google.genai so any accidental import/use during detection blows up.
    sentinel = object()
    had = sys.modules.get("google.genai", sentinel)
    # detect_cues should complete without touching genai at all.
    cues = detect_cues(Path("fake.mp3"), max_cues=4)
    assert cues  # produced cues with zero network
    # restore (no-op if it wasn't there)
    if had is sentinel:
        sys.modules.pop("google.genai", None)


# ─── Real ffmpeg decode path (opt-in) ────────────────────────────────────────────


@pytest.mark.integration
def test_decode_to_mono_real_ffmpeg(tmp_path: Path) -> None:
    """Round-trip a generated WAV through the real ffmpeg decode path."""
    import shutil
    import wave

    if shutil.which("ffmpeg") is None:
        pytest.skip("ffmpeg not installed")

    synth = _synthetic_track()
    wav_path = tmp_path / "synth.wav"
    pcm = np.clip(synth * 32767.0, -32768, 32767).astype("<i2")
    with wave.open(str(wav_path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(ANALYSIS_SR)
        w.writeframes(pcm.tobytes())

    decoded = cue_detect.decode_to_mono(wav_path)
    assert decoded.size > 0
    # Length within a frame of the source (resample/codec slack).
    assert abs(decoded.size - synth.size) < ANALYSIS_SR

    cues = detect_cues(wav_path, max_cues=4)
    assert cues
    assert all(c.type in {"cue", "load"} for c in cues)
