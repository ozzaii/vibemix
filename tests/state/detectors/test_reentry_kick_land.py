# SPDX-License-Identifier: Apache-2.0
"""ReentryKickLandDetector — paired with BreakdownKickKillDetector.

Fires when:
  1. The kick comes back (``state.bands["sub"]`` recovers above
     ``KICK_REENTRY_SUB_FLOOR``)
  2. Within ``KICK_REENTRY_MAX_AGE_S`` of the most recent
     ``BreakdownKickKillDetector.last_kill_at``
  3. Near a downbeat (``min(beat_phase, 1 - beat_phase)`` ≤
     ``KICK_REENTRY_BAR_TOLERANCE``)
  4. With a trustworthy BPM lock (``state.bpm_confidence >= 0.5``) — Phase
     17 anti-hallucination guard per threat T-17-03-02; without this,
     ``bpm_confidence == 0`` would force ``beat_phase = 0.0`` (Phase 13's
     "no fabricated lock" contract) and naively pass the downbeat gate.

Each kill pairs with at most ONE re-entry — the detector tracks
``last_consumed_kill_at`` and ignores subsequent ticks that point at the
same kill timestamp.
"""

from __future__ import annotations

from tests.state.detectors.conftest import _state
from vibemix.audio.constants import LOW_RMS
from vibemix.state.detectors.breakdown_kick_kill import BreakdownKickKillDetector
from vibemix.state.detectors.reentry_kick_land import ReentryKickLandDetector


def _kill_detector_with_recent_kill(kill_at: float) -> BreakdownKickKillDetector:
    """Build a kill detector with ``last_kill_at`` pre-stamped, bypassing the
    full kill-detection pipeline. The pair contract is just the public
    attribute — tests can set it directly without driving the kill path."""
    k = BreakdownKickKillDetector()
    k.last_kill_at = kill_at
    return k


def _state_post_reentry(
    *,
    rms: float = 0.10,
    sub: float = 0.25,
    beat_phase: float = 0.05,
    bpm_confidence: float = 0.8,
):
    """MusicState shaped for a 'ready-to-fire' re-entry tick."""
    ms = _state(rms=rms, bands={"sub": sub, "low": 0.3, "mid": 0.25, "high": 0.20})
    ms.beat_phase = beat_phase
    ms.bpm_confidence = bpm_confidence
    return ms


# ---------- Test 1: no fire without prior kill ----------


def test_reentry_no_fire_without_prior_kill():
    """``last_kill_at == 0.0`` (no kill ever) → never fires regardless of
    sub recovery / downbeat alignment."""
    k = BreakdownKickKillDetector()  # last_kill_at = 0.0
    r = ReentryKickLandDetector(k)
    ms = _state_post_reentry()  # everything else aligned
    ev = r.detect(ms, audio_buf=None, now=1000.0)
    assert ev is None


# ---------- Test 2: fires on sub recovery within 30s near downbeat ----------


def test_reentry_fires_on_sub_recovery_within_30s_of_kill_near_downbeat():
    now = 1000.0
    k = _kill_detector_with_recent_kill(kill_at=now - 5.0)
    r = ReentryKickLandDetector(k)
    ms = _state_post_reentry(rms=0.10, sub=0.25, beat_phase=0.05, bpm_confidence=0.8)

    ev = r.detect(ms, audio_buf=None, now=now)
    assert ev is not None
    assert ev.type == "REENTRY_KICK_LAND"
    assert ev.extra == {
        "kill_age_s": 5.0,
        "sub_at_reentry": 0.25,
        "beat_phase": 0.05,
    }


# ---------- Test 3: no fire when kill age exceeds max (30s) ----------


def test_reentry_no_fire_when_kill_age_exceeds_max():
    now = 1000.0
    k = _kill_detector_with_recent_kill(kill_at=now - 35.0)
    r = ReentryKickLandDetector(k)
    ms = _state_post_reentry()
    ev = r.detect(ms, audio_buf=None, now=now)
    assert ev is None


# ---------- Test 4: no fire when sub below reentry floor ----------


def test_reentry_no_fire_when_sub_below_reentry_floor():
    now = 1000.0
    k = _kill_detector_with_recent_kill(kill_at=now - 5.0)
    r = ReentryKickLandDetector(k)
    # KICK_REENTRY_SUB_FLOOR = 0.18; 0.15 is below.
    ms = _state_post_reentry(sub=0.15)
    ev = r.detect(ms, audio_buf=None, now=now)
    assert ev is None


# ---------- Test 5: no fire when beat_phase mid-bar ----------


def test_reentry_no_fire_when_beat_phase_misaligned():
    """``beat_phase == 0.50`` → distance-to-downbeat = min(0.50, 0.50) = 0.50,
    well above KICK_REENTRY_BAR_TOLERANCE (0.20)."""
    now = 1000.0
    k = _kill_detector_with_recent_kill(kill_at=now - 5.0)
    r = ReentryKickLandDetector(k)
    ms = _state_post_reentry(beat_phase=0.50)
    ev = r.detect(ms, audio_buf=None, now=now)
    assert ev is None


# ---------- Test 6: accepts beat_phase near either end of bar ----------


def test_reentry_accepts_beat_phase_near_either_end_of_bar():
    """beat_phase = 0.95 → distance to next downbeat (wrap-around) = 0.05.
    The downbeat is the wrap-around point, not just 0.0."""
    now = 1000.0
    k = _kill_detector_with_recent_kill(kill_at=now - 5.0)
    r = ReentryKickLandDetector(k)
    ms = _state_post_reentry(beat_phase=0.95)
    ev = r.detect(ms, audio_buf=None, now=now)
    assert ev is not None
    assert ev.type == "REENTRY_KICK_LAND"
    assert ev.extra["beat_phase"] == 0.95


# ---------- Test 7: each kill consumed by at most one reentry ----------


def test_reentry_consumes_kill_after_fire():
    """After a successful re-entry fire, the SAME kill timestamp can't
    re-fire — the detector clears its watch via ``last_consumed_kill_at``."""
    now = 1000.0
    k = _kill_detector_with_recent_kill(kill_at=now - 5.0)
    r = ReentryKickLandDetector(k)
    ms = _state_post_reentry()
    ev1 = r.detect(ms, audio_buf=None, now=now)
    assert ev1 is not None

    # Same kill, same matching state, advance past cooldown — must NOT re-fire.
    ev2 = r.detect(ms, audio_buf=None, now=now + 20.0)  # past 12s cooldown
    assert ev2 is None

    # New kill at a later moment — re-arms the detector.
    k.last_kill_at = now + 20.0
    ev3 = r.detect(ms, audio_buf=None, now=now + 21.0)  # 1s after new kill
    assert ev3 is not None


# ---------- Test 8: silence gate ----------


def test_reentry_silence_gate():
    now = 1000.0
    k = _kill_detector_with_recent_kill(kill_at=now - 5.0)
    r = ReentryKickLandDetector(k)
    ms = _state_post_reentry(rms=LOW_RMS - 0.005)
    ev = r.detect(ms, audio_buf=None, now=now)
    assert ev is None


# ---------- Test 9: cooldown blocks repeat fire (12s) ----------


def test_reentry_cooldown_12s():
    """Even when a fresh kill arrives within 12s of a prior re-entry,
    the per-type cooldown blocks the second fire."""
    now = 1000.0
    k = _kill_detector_with_recent_kill(kill_at=now - 5.0)
    r = ReentryKickLandDetector(k)
    ms = _state_post_reentry()

    ev1 = r.detect(ms, audio_buf=None, now=now)
    assert ev1 is not None

    # New kill 8s after the first re-entry — re-arms the detector but
    # cooldown (12s on REENTRY_KICK_LAND) still blocks.
    k.last_kill_at = now + 6.0
    ev2 = r.detect(ms, audio_buf=None, now=now + 8.0)  # 8s < 12s cooldown
    assert ev2 is None


# ---------- Test 10: T-17-03-02 — bpm_confidence guard ----------


def test_reentry_no_fire_when_bpm_confidence_low():
    """Threat T-17-03-02: ``bpm_confidence < 0.5`` short-circuits the gate.
    Without this, Phase 13's anti-hallucination contract (invalid BPM →
    beat_phase forced to 0.0) would naively pass the downbeat alignment
    check, false-firing on every "no BPM lock" frame."""
    now = 1000.0
    k = _kill_detector_with_recent_kill(kill_at=now - 5.0)
    r = ReentryKickLandDetector(k)
    # beat_phase = 0.0 (Phase 13 fabricated default), bpm_confidence below 0.5.
    ms = _state_post_reentry(beat_phase=0.0, bpm_confidence=0.0)
    ev = r.detect(ms, audio_buf=None, now=now)
    assert ev is None


# ---------- Test 11: stores kill_detector reference (DI contract) ----------


def test_reentry_stores_kill_detector_reference():
    k = BreakdownKickKillDetector()
    r = ReentryKickLandDetector(k)
    assert r.kill_detector is k


# ---------- Test 12: re-export ----------


def test_reentry_kick_land_detector_is_re_exported_from_subpackage():
    from vibemix.state.detectors import ReentryKickLandDetector as Re

    assert Re is ReentryKickLandDetector
