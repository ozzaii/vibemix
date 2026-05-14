# SPDX-License-Identifier: Apache-2.0
"""PhraseBoundaryDetector — fires on a downbeat that closes an 8/16/32-bar
phrase (locked via 40-120Hz band-limited autocorrelation in `_phrase_dsp.py`).

Self-corrects when ``BREAKDOWN_KICK_KILL`` fires by resetting the phrase
counter — the breakdown IS where the next phrase starts (per T-17-04-04
accept disposition documented in the module docstring). Same DI idiom as
``ReentryKickLandDetector``: the kill detector is passed in via the
constructor (optional — Plan 05's GenreRouter MAY pass None for genres
where kick-kill self-correction isn't relevant, e.g. disco / pop).

The bpm_confidence ≥ 0.5 anti-hallucination guard (mirrors the
``ReentryKickLandDetector`` T-17-03-02 mitigation, lifted to module-level
``BPM_CONFIDENCE_MIN_FOR_DOWNBEAT`` in Plan 17-04) blocks fires when Phase
13's anti-hallucination contract has fabricated ``beat_phase = 0.0``.
"""

from __future__ import annotations

import numpy as np

from tests.state.detectors.conftest import _state
from vibemix.audio.constants import LOW_RMS, MIN_EVENT_GAP_PER_TYPE
from vibemix.state.detectors.breakdown_kick_kill import BreakdownKickKillDetector
from vibemix.state.detectors.phrase_boundary import PhraseBoundaryDetector


class _FakeAudioBuf:
    """Tiny AudioBuffer surrogate — only ``.snapshot(n)`` and ``._sr`` are
    consumed by ``PhraseBoundaryDetector`` (it calls ``audio_buf.snapshot``
    during the lock-seeding step and hands the samples to
    ``lock_downbeat_phase``)."""

    def __init__(self, samples: np.ndarray, sr: int = 16000) -> None:
        self._samples = samples
        self._sr = sr

    def snapshot(self, n: int) -> np.ndarray:
        if self._samples.size <= n:
            return self._samples
        return self._samples[-n:]


def _synth_kick_buf(bpm: float = 130.0, duration_s: float = 8.0, sr: int = 16000) -> _FakeAudioBuf:
    """Build a 4-on-floor synthetic kick pattern wrapped in a fake AudioBuffer.
    Mirrors the helper used by `test_phrase_dsp.py` so the lock seeds with
    real-shaped kick energy."""
    n = int(sr * duration_s)
    out = np.zeros(n, dtype=np.float32)
    beat_period_s = 60.0 / bpm
    samples_per_beat = int(beat_period_s * sr)
    pulse_n = int(0.110 * sr)  # 10ms attack + 100ms decay
    attack_n = int(0.010 * sr)
    decay_n = pulse_n - attack_n
    t_pulse = np.arange(pulse_n, dtype=np.float32) / float(sr)
    sine = np.sin(2.0 * np.pi * 60.0 * t_pulse)
    env = np.zeros(pulse_n, dtype=np.float32)
    env[:attack_n] = np.linspace(0.0, 1.0, attack_n, dtype=np.float32)
    x = np.arange(decay_n, dtype=np.float32) / float(decay_n)
    env[attack_n:] = np.exp(-5.0 * x)
    pulse = (sine * env).astype(np.float32)
    for beat_idx in range(int(duration_s / beat_period_s)):
        start = beat_idx * samples_per_beat
        end = start + pulse_n
        if end > n:
            break
        out[start:end] += pulse
    peak = float(np.max(np.abs(out)))
    if peak > 0.0:
        out = out / peak * 0.6
    # Convert to int16 PCM to mirror AudioBuffer.snapshot() dtype.
    return _FakeAudioBuf((out * 16384.0).astype(np.int16), sr=sr)


def _state_phrase_ready(*, bpm: float = 130.0, beat_phase: float = 0.0,
                         bpm_confidence: float = 0.8, energy_curve: list | None = None):
    """MusicState shaped for a 'ready-to-fire' phrase-boundary tick — audible,
    BPM locked with confidence, and on a downbeat. ``energy_curve`` defaults
    to a flat list long enough that ``estimate_phrase_length_bars`` picks 16
    (the conservative fallback)."""
    ms = _state(rms=0.10, bpm=bpm)
    ms.beat_phase = beat_phase
    ms.bpm_confidence = bpm_confidence
    ms.energy_curve = energy_curve if energy_curve is not None else [0.10] * 60
    return ms


# ---------- Test 1: first call seeds lock, no fire ----------


def test_phrase_boundary_seeds_lock_on_first_call():
    """No prior lock → first call seeds (calls ``lock_downbeat_phase``),
    returns None even with everything else perfectly aligned."""
    d = PhraseBoundaryDetector()
    ms = _state_phrase_ready()
    buf = _synth_kick_buf(bpm=130.0, duration_s=8.0)
    ev = d.detect(ms, buf, now=1000.0)
    assert ev is None
    # After seeding, internal anchor is set + phrase length latched.
    assert d.lock_anchor_t == 1000.0
    assert d.locked_bpm == 130.0
    assert d.phrase_length_bars in (8, 16, 32)


# ---------- Test 2: fires on downbeat at estimated phrase count ----------


def test_phrase_boundary_fires_on_downbeat_at_estimated_phrase_count():
    """With phrase_length_bars=16 (default) and bar_index reaching 16 from
    lock-time downbeats, beat_phase near 0.0 → fires. Extra carries phrase
    metadata."""
    d = PhraseBoundaryDetector()
    ms = _state_phrase_ready(bpm=130.0, beat_phase=0.0, bpm_confidence=0.8)
    buf = _synth_kick_buf(bpm=130.0)

    # Seed at t=1000.
    d.detect(ms, buf, now=1000.0)
    # Force phrase length to 16 (default — explicit for clarity).
    d.phrase_length_bars = 16

    # Compute "16 bars later" in seconds: 16 bars × 4 beats × (60/130) s/beat ≈ 29.54s
    sixteen_bars_s = 16 * 4 * 60.0 / 130.0
    fire_at = 1000.0 + sixteen_bars_s

    ev = d.detect(ms, buf, now=fire_at)
    assert ev is not None
    assert ev.type == "PHRASE_BOUNDARY"
    assert ev.extra["phrase_length_bars"] == 16
    assert ev.extra["bar_index_in_phrase"] == 16
    assert "beat_phase" in ev.extra
    assert "bpm" in ev.extra
    assert ev.extra["bpm"] == 130.0


# ---------- Test 3: no fire mid-phrase ----------


def test_phrase_boundary_no_fire_mid_phrase():
    """bar_index = 8 of 16 (mid-phrase), beat_phase near 0.0 → returns None."""
    d = PhraseBoundaryDetector()
    ms = _state_phrase_ready(bpm=130.0, beat_phase=0.0, bpm_confidence=0.8)
    buf = _synth_kick_buf(bpm=130.0)

    d.detect(ms, buf, now=1000.0)
    d.phrase_length_bars = 16

    # 8 bars later — mid-phrase. Should NOT fire.
    eight_bars_s = 8 * 4 * 60.0 / 130.0
    ev = d.detect(ms, buf, now=1000.0 + eight_bars_s)
    assert ev is None


# ---------- Test 4: self-corrects on BREAKDOWN_KICK_KILL ----------


def test_phrase_boundary_self_corrects_on_breakdown_kick_kill():
    """Given a kill_detector with .last_kill_at = now-2.0, the detector resets
    its bar counter (the breakdown is where the next phrase starts).

    Verified by: pre-kill bar_index = 12, then kill happens, then 16 bars
    later detector fires PHRASE_BOUNDARY (counted from kill, not from
    original lock)."""
    k = BreakdownKickKillDetector()  # last_kill_at = 0.0 initially
    d = PhraseBoundaryDetector(kill_detector=k)
    ms = _state_phrase_ready(bpm=130.0, beat_phase=0.0, bpm_confidence=0.8)
    buf = _synth_kick_buf(bpm=130.0)

    # Seed lock at t=1000.
    d.detect(ms, buf, now=1000.0)
    d.phrase_length_bars = 16

    # Advance to "12 bars later" — pre-kill check, no fire.
    twelve_bars_s = 12 * 4 * 60.0 / 130.0
    pre_kill_now = 1000.0 + twelve_bars_s
    ev_pre = d.detect(ms, buf, now=pre_kill_now)
    assert ev_pre is None

    # Kill happens 2 seconds AFTER the pre-kill check.
    kill_at = pre_kill_now + 2.0
    k.last_kill_at = kill_at

    # Next tick at kill_at — detector should observe the new kill, reset
    # the lock anchor to kill_at, and return None (next-tick is start of
    # the new phrase, not a boundary).
    ev_observe_kill = d.detect(ms, buf, now=kill_at)
    assert ev_observe_kill is None
    assert d.lock_anchor_t == kill_at
    assert d.last_observed_kill_at == kill_at

    # 16 bars after the kill — should fire (counted from kill, not from
    # the original t=1000.0 lock).
    sixteen_bars_s = 16 * 4 * 60.0 / 130.0
    ev_post = d.detect(ms, buf, now=kill_at + sixteen_bars_s)
    assert ev_post is not None
    assert ev_post.type == "PHRASE_BOUNDARY"
    assert ev_post.extra["bar_index_in_phrase"] == 16


# ---------- Test 5: bpm_confidence guard ----------


def test_phrase_boundary_no_fire_on_low_bpm_confidence():
    """state.bpm_confidence = 0.3 (below PHRASE_BOUNDARY_MIN_LOCK_CONFIDENCE=0.5)
    → returns None (anti-hallucination — don't fire structural events on
    a fake lock)."""
    d = PhraseBoundaryDetector()
    ms = _state_phrase_ready(bpm=130.0, beat_phase=0.0, bpm_confidence=0.3)
    buf = _synth_kick_buf(bpm=130.0)
    ev = d.detect(ms, buf, now=1000.0)
    assert ev is None
    # Should NOT have seeded either — low confidence rejects before lock.
    assert d.lock_anchor_t == 0.0


# ---------- Test 6: silence gate ----------


def test_phrase_boundary_silence_gate():
    """state.rms below LOW_RMS or state.phase=='silent' → returns None."""
    d = PhraseBoundaryDetector()
    buf = _synth_kick_buf(bpm=130.0)

    # Sub-LOW_RMS
    ms_silent = _state_phrase_ready()
    ms_silent.rms = LOW_RMS - 0.005
    assert d.detect(ms_silent, buf, now=1000.0) is None

    # Phase classified as silent
    ms_phase_silent = _state_phrase_ready()
    ms_phase_silent.phase = "silent"
    assert d.detect(ms_phase_silent, buf, now=1000.0) is None


# ---------- Test 7: cooldown blocks repeat fire (24s) ----------


def test_phrase_boundary_cooldown_prevents_double_fire():
    """Repeat call within MIN_EVENT_GAP_PER_TYPE['PHRASE_BOUNDARY']=24s blocked.
    """
    d = PhraseBoundaryDetector()
    ms = _state_phrase_ready(bpm=130.0, beat_phase=0.0, bpm_confidence=0.8)
    buf = _synth_kick_buf(bpm=130.0)

    d.detect(ms, buf, now=1000.0)
    d.phrase_length_bars = 16
    sixteen_bars_s = 16 * 4 * 60.0 / 130.0
    ev1 = d.detect(ms, buf, now=1000.0 + sixteen_bars_s)
    assert ev1 is not None  # first fire

    # Within cooldown — should NOT fire even at the next 16-bar boundary.
    cooldown = MIN_EVENT_GAP_PER_TYPE["PHRASE_BOUNDARY"]
    assert cooldown == 24.0
    next_boundary = 1000.0 + sixteen_bars_s + sixteen_bars_s
    # next_boundary is ~29.5s after first fire — past 24s cooldown but...
    # we want to test BLOCK within cooldown so use a closer offset:
    inside_cooldown_t = 1000.0 + sixteen_bars_s + 5.0
    ev2 = d.detect(ms, buf, now=inside_cooldown_t)
    assert ev2 is None  # blocked by cooldown


# ---------- Test 8: min-bars-between-fires gate ----------


def test_phrase_boundary_min_bars_between_fires():
    """Even outside the 24s cooldown, two fires must be at least
    PHRASE_BOUNDARY_MIN_BARS_BETWEEN_FIRES=8 bars apart (computed from
    bar_index, not seconds — protects against fast-BPM double-fire)."""
    d = PhraseBoundaryDetector()
    # Use a fast BPM where 8 bars elapses fast.
    fast_bpm = 170.0
    ms = _state_phrase_ready(bpm=fast_bpm, beat_phase=0.0, bpm_confidence=0.8)
    buf = _synth_kick_buf(bpm=fast_bpm)

    d.detect(ms, buf, now=1000.0)
    d.phrase_length_bars = 16  # explicit
    sixteen_bars_s = 16 * 4 * 60.0 / fast_bpm
    ev1 = d.detect(ms, buf, now=1000.0 + sixteen_bars_s)
    assert ev1 is not None
    fired_at_bar_idx = ev1.extra["bar_index_in_phrase"]
    assert fired_at_bar_idx == 16

    # Manually clear the wall-clock cooldown so the bar-count gate is the
    # ONLY thing protecting us. Simulate "many bars later, but still inside
    # the 8-bar floor of bar_index".
    d.last_event_at = 0.0  # clear wall-clock cooldown
    # 4 bars after the first fire (bar_index=20) — 20 - 16 = 4 < 8 → blocked.
    four_bars_later = sixteen_bars_s + 4 * 4 * 60.0 / fast_bpm
    ev2 = d.detect(ms, buf, now=1000.0 + four_bars_later)
    assert ev2 is None


# ---------- Test 9: works with no kill_detector ----------


def test_phrase_boundary_with_no_kill_detector_works():
    """``PhraseBoundaryDetector(kill_detector=None)`` — fires correctly
    without self-correction. Plan 05's GenreRouter MAY pass None for genres
    where kick-kill self-correction isn't relevant (e.g. disco / pop)."""
    d = PhraseBoundaryDetector(kill_detector=None)
    ms = _state_phrase_ready(bpm=130.0, beat_phase=0.0, bpm_confidence=0.8)
    buf = _synth_kick_buf(bpm=130.0)

    d.detect(ms, buf, now=1000.0)
    d.phrase_length_bars = 16
    sixteen_bars_s = 16 * 4 * 60.0 / 130.0
    ev = d.detect(ms, buf, now=1000.0 + sixteen_bars_s)
    assert ev is not None
    assert ev.type == "PHRASE_BOUNDARY"


# ---------- Test 10: re-export sentinel ----------


def test_phrase_boundary_detector_is_re_exported_from_subpackage():
    """Parity with the five sibling Wave-2 detectors — every detector class
    is importable from the `vibemix.state.detectors` package directly."""
    from vibemix.state.detectors import PhraseBoundaryDetector as Re

    assert Re is PhraseBoundaryDetector
