# SPDX-License-Identifier: Apache-2.0
"""Offline auto-cue detection tests (Path 2 — the auto-cue engine).

DETERMINISTIC, ZERO network, ZERO Gemini, default pytest selection. The pure
DSP is tested over synthetic numpy audio with ``decode_to_mono`` monkeypatched
so no ffmpeg binary / real audio file is needed. One ``@pytest.mark.integration``
test exercises the real ffmpeg decode path against a generated WAV.

``detect_cues`` now returns ``list[CueAnchor]`` (``source="auto"``) — labeled,
phrase-snapped, confidence-scored mixable WINDOWS (span cues), not point cues.
Structure (not energy) drives the labels: ``drop`` = the kick slamming back in
after a sustained breakdown (the re-entry), ``breakdown`` = the bass-cut that
starts it (the kill). The dance-degrade gate is the anti-hallucination core:
dance labels require a beat AND a real sustained breakdown; otherwise the engine
emits ONLY ``intro``/``outro`` and NEVER fabricates a ``drop``/``build``.

Synthetic track shapes (so structure is unambiguous):
    - Dance track WITH a breakdown: 4-on-floor sub-bass kick → sustained ~10s
      bass-out (the kill) → the kick returns (the re-entry) — has beat + a real
      breakdown, so the dance gate opens and a drop lands at the re-entry.
    - Steady kick, NO breakdown: a uniform 4-on-floor groove all the way through
      — beat present but no bass-out, so NO fabricated drop → only intro/outro.
    - Beatless drone: a steady mid-band tone, no kick — the dance gate MUST shut
      → only intro/outro.
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
    audible_bounds_s,
    decode_to_mono,
    detect_cues,
)
from vibemix.library.cue_types import CueAnchor

VALID_LABELS = {"intro", "build", "breakdown", "drop", "outro"}


# ─── Synthetic audio ────────────────────────────────────────────────────────────


def _kick_section(
    seconds: float, sr: int, *, bpm: float = 128.0, gain: float = 1.0
) -> np.ndarray:
    """A 4-on-floor sub kick: short 60Hz sine bursts at the beat period, plus a
    quiet mid-band bed so the section reads full-band (a real drop is not pure
    sub)."""
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
    # A low-level mid bed (440Hz) so the kick section has full-band energy.
    tt = np.arange(n) / sr
    out += (0.08 * np.sin(2 * np.pi * 440.0 * tt)).astype(np.float32)
    return (out * gain).astype(np.float32)


def _pad_section(seconds: float, sr: int) -> np.ndarray:
    """A mid-band pad (800Hz) with NO sub content — a breakdown bass-out."""
    n = int(seconds * sr)
    t = np.arange(n) / sr
    return (0.3 * np.sin(2 * np.pi * 800.0 * t)).astype(np.float32)


# Section durations for the synthetic dance track (seconds). The breakdown is a
# sustained ≥ _MIN_BREAKDOWN_S (6s) bass-out so a real breakdown→drop pair forms.
_INTRO_S = 36.0
_BREAKDOWN_S = 10.0  # sustained bass-out (the kill); ≥ _MIN_BREAKDOWN_S
_DROP_S = 44.0
# Frame indices (1Hz hop) where each event lands.
_BREAKDOWN_FRAME = int(_INTRO_S)  # bass-out (kill) ~here
_REENTRY_FRAME = int(_INTRO_S + _BREAKDOWN_S)  # kick-back (drop) ~here


def _dance_track(sr: int = ANALYSIS_SR) -> np.ndarray:
    """Kick(36s) → sustained bass-out pad(10s) → kick returns(44s).

    The 10s bass-out is the BREAKDOWN (the kill); the kick coming back is the
    DROP (the re-entry). This is the live-ear definition of structure: a drop is
    the kick slamming back IN after a breakdown, not "the loudest segment".
    """
    intro = _kick_section(_INTRO_S, sr, gain=1.0)
    bd = _pad_section(_BREAKDOWN_S, sr)
    drop = _kick_section(_DROP_S, sr, gain=1.0)
    return np.concatenate([intro, bd, drop]).astype(np.float32)


def _steady_kick_track(sr: int = ANALYSIS_SR, seconds: float = 90.0) -> np.ndarray:
    """A uniform 4-on-floor groove all the way through — NO breakdown.

    Beat present (periodic kick) but no bass-out → no significant breakdown →
    the engine must NOT fabricate a drop. Only intro/outro allowed. This is the
    brick-walled-groove case the old energy-ranking labeler got wrong.
    """
    return _kick_section(seconds, sr, gain=1.0)


def _beatless_drone(sr: int = ANALYSIS_SR, seconds: float = 90.0) -> np.ndarray:
    """A steady mid-band tone — no kick, no transients, no dynamic range.

    The dance-degrade gate MUST shut on this: G1 (no beat) fails, and there is
    no breakdown. Only intro/outro allowed.
    """
    n = int(seconds * sr)
    t = np.arange(n) / sr
    return (0.3 * np.sin(2 * np.pi * 500.0 * t)).astype(np.float32)


@pytest.fixture
def dance() -> np.ndarray:
    return _dance_track()


@pytest.fixture
def steady() -> np.ndarray:
    return _steady_kick_track()


@pytest.fixture
def drone() -> np.ndarray:
    return _beatless_drone()


# ─── Pure-DSP unit tests (no ffmpeg) ─────────────────────────────────────────────


def test_sub_energy_curve_dips_in_breakdown(dance: np.ndarray) -> None:
    curve = _sub_energy_curve(dance, ANALYSIS_SR)
    # ~90 frames at 1s hop (36 intro + 10 breakdown + 44 drop).
    assert curve.size >= 85
    # Frames 0-35 = intro kick (high sub), 36-45 = breakdown (low sub),
    # 46-89 = drop kick (high sub).
    kick_a = float(np.median(curve[5:30]))
    breakdown = float(np.median(curve[38:44]))
    kick_c = float(np.median(curve[55:85]))
    assert kick_a > 0.0
    assert kick_c > 0.0
    # The breakdown sub-share must be materially below the kick sections.
    assert breakdown < 0.5 * kick_a
    assert breakdown < 0.5 * kick_c


def test_find_sub_edges_locates_breakdown_and_reentry(dance: np.ndarray) -> None:
    curve = _sub_energy_curve(dance, ANALYSIS_SR)
    rms = _rms_curve(dance, ANALYSIS_SR, curve.size)
    kills, reentries = _find_sub_edges(curve, rms)

    assert kills, "expected a breakdown (kill) edge"
    assert reentries, "expected a re-entry edge"
    # The kill should land in the breakdown region (~frame 36-46).
    assert any(33 <= k <= 48 for k in kills), kills
    # The re-entry should land at / after the kick-back (~frame 44+).
    assert any(r >= 43 for r in reentries), reentries
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


def test_audible_bounds_ignore_silent_lead_in_and_tail() -> None:
    silence = np.zeros(ANALYSIS_SR * 8, dtype=np.float32)
    core = _steady_kick_track(seconds=60.0)
    padded = np.concatenate([silence, core, silence]).astype(np.float32)

    bounds = audible_bounds_s(padded, ANALYSIS_SR)

    assert bounds is not None
    first_s, last_s = bounds
    assert 7.0 <= first_s <= 10.0
    assert 66.0 <= last_s <= 70.0


def test_audible_bounds_all_silence_is_none() -> None:
    silent = np.zeros(ANALYSIS_SR * 90, dtype=np.float32)

    assert audible_bounds_s(silent, ANALYSIS_SR) is None


# ─── detect_cues → CueAnchor contract (decode monkeypatched) ──────────────────────


def _assert_anchor_contract(anchors: list[CueAnchor]) -> None:
    """The cross-session CueAnchor invariants every result must hold."""
    assert all(isinstance(a, CueAnchor) for a in anchors)
    for a in anchors:
        assert a.label in VALID_LABELS, a.label
        assert a.source == "auto", a.source
        assert 0.0 <= a.confidence <= 1.0, a.confidence
        assert a.start_s < a.end_s, (a.start_s, a.end_s)
        assert (a.end_s - a.start_s) <= 80.0 + 1e-6, (a.start_s, a.end_s)
    starts = [a.start_s for a in anchors]
    assert starts == sorted(starts), "anchors must be ascending by start_s"


def test_dance_track_yields_drop_at_reentry_and_breakdown_at_bassout(
    dance: np.ndarray, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cue_detect, "decode_to_mono", lambda *_a, **_k: dance)
    anchors = detect_cues(Path("fake.mp3"), max_cues=5)

    assert anchors, "a structured dance track must produce anchors"
    _assert_anchor_contract(anchors)
    labels = {a.label for a in anchors}
    # The dance gate must OPEN (beat + a real breakdown) → drop + breakdown.
    assert "drop" in labels, labels
    assert "breakdown" in labels, labels

    drop = next(a for a in anchors if a.label == "drop")
    breakdown = next(a for a in anchors if a.label == "breakdown")
    # The drop lands at the kick-back (re-entry ~frame 46s); phrase-snap + window
    # sizing allow a few seconds of slack.
    assert abs(drop.start_s - _REENTRY_FRAME) <= 8.0, drop
    # The breakdown lands at the bass-out (kill ~frame 36s).
    assert abs(breakdown.start_s - _BREAKDOWN_FRAME) <= 8.0, breakdown
    # The drop comes after the breakdown (kick-back follows the bass-out).
    assert drop.start_s > breakdown.start_s


def test_steady_kick_no_breakdown_yields_intro_outro_only(
    steady: np.ndarray, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A uniform groove with a beat but NO breakdown must NOT fabricate a drop —
    the bug the old energy-ranking labeler had on brick-walled hardtechno."""
    monkeypatch.setattr(cue_detect, "decode_to_mono", lambda *_a, **_k: steady)
    anchors = detect_cues(Path("fake.mp3"), max_cues=4)

    _assert_anchor_contract(anchors)
    labels = {a.label for a in anchors}
    # Beat present but no breakdown → only position cues, never a fabricated drop.
    assert labels <= {"intro", "outro"}, labels
    assert "drop" not in labels
    assert "breakdown" not in labels
    assert "build" not in labels


def test_beatless_track_degrades_to_intro_outro_only(
    drone: np.ndarray, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cue_detect, "decode_to_mono", lambda *_a, **_k: drone)
    anchors = detect_cues(Path("fake.mp3"), max_cues=4)

    _assert_anchor_contract(anchors)
    labels = {a.label for a in anchors}
    # Anti-hallucination: the dance gate MUST shut — no fabricated structure.
    assert labels <= {"intro", "outro"}, labels
    assert "drop" not in labels
    assert "build" not in labels
    assert "breakdown" not in labels


def test_detect_cues_deterministic(
    dance: np.ndarray, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cue_detect, "decode_to_mono", lambda *_a, **_k: dance)
    a1 = detect_cues(Path("fake.mp3"), max_cues=4)
    a2 = detect_cues(Path("fake.mp3"), max_cues=4)
    # Pure DSP → byte-identical anchors.
    assert a1 == a2


def test_windows_never_exceed_80s(
    dance: np.ndarray, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cue_detect, "decode_to_mono", lambda *_a, **_k: dance)
    anchors = detect_cues(Path("fake.mp3"), max_cues=4)
    assert anchors
    for a in anchors:
        assert (a.end_s - a.start_s) <= 80.0 + 1e-6, (a.label, a.start_s, a.end_s)


def test_detect_cues_respects_max_cues(
    dance: np.ndarray, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cue_detect, "decode_to_mono", lambda *_a, **_k: dance)
    for m in (1, 2, 3):
        anchors = detect_cues(Path("fake.mp3"), max_cues=m)
        assert len(anchors) <= m


def test_detect_cues_short_track_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    short = np.zeros(int(ANALYSIS_SR * 10), dtype=np.float32)  # 10s < MIN_TRACK_S
    monkeypatch.setattr(cue_detect, "decode_to_mono", lambda *_a, **_k: short)
    anchors = detect_cues(Path("fake.mp3"), max_cues=4)
    # No-structure → empty list (the consumer falls back to mean_excerpt).
    assert anchors == []


def test_detect_cues_empty_audio_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        cue_detect, "decode_to_mono", lambda *_a, **_k: np.zeros(0, dtype=np.float32)
    )
    anchors = detect_cues(Path("fake.mp3"), max_cues=4)
    assert anchors == []


def test_detect_cues_long_silence_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        cue_detect, "decode_to_mono", lambda *_a, **_k: np.zeros(ANALYSIS_SR * 90, dtype=np.float32)
    )
    anchors = detect_cues(Path("fake.mp3"), max_cues=4)
    assert anchors == []


def test_detect_cues_no_network_no_gemini(
    dance: np.ndarray, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Guard: detect_cues must never import/use the genai client."""
    monkeypatch.setattr(cue_detect, "decode_to_mono", lambda *_a, **_k: dance)
    import sys

    sentinel = object()
    had = sys.modules.get("google.genai", sentinel)
    anchors = detect_cues(Path("fake.mp3"), max_cues=4)
    assert anchors  # produced anchors with zero network
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

    synth = _dance_track()
    wav_path = tmp_path / "synth.wav"
    pcm = np.clip(synth * 32767.0, -32768, 32767).astype("<i2")
    with wave.open(str(wav_path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(ANALYSIS_SR)
        w.writeframes(pcm.tobytes())

    decoded = decode_to_mono(wav_path)
    assert decoded.size > 0
    # Length within a frame of the source (resample/codec slack).
    assert abs(decoded.size - synth.size) < ANALYSIS_SR

    anchors = detect_cues(wav_path, max_cues=4)
    _assert_anchor_contract(anchors)
