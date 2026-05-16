# SPDX-License-Identifier: Apache-2.0
"""BreakdownKickKillDetector — fires when ``state.bands["sub"]`` collapses
below ``KICK_KILL_SUB_FLOOR`` while ``state.rms`` is still above ``LOW_RMS``
(the kick disappeared but music is still playing — filter sweep / breakdown /
drop preparation). Pairs with ``ReentryKickLandDetector`` via the public
``last_kill_at`` attribute.

Reads ``state.bands["sub"]`` directly — does not touch ``audio_buf``. Two
silence gates (RMS floor + Phase 6 silent-phase classification) reject before
baseline seeding, mirroring ``KickDensityShiftDetector`` and the v4
"trust the audio" anti-hallucination rule.
"""

from __future__ import annotations

from tests.state.detectors.conftest import _state
from vibemix.audio.constants import LOW_RMS
from vibemix.state.detectors.breakdown_kick_kill import BreakdownKickKillDetector


# ---------- Test 1: fires on sub collapse with audible RMS ----------


def test_breakdown_kick_kill_fires_on_sub_collapse_with_audible_rms():
    """Kick gone (sub 0.30 → 0.05) but music still audible (rms=0.08 > LOW_RMS).
    This is the canonical breakdown / filter-sweep moment."""
    d = BreakdownKickKillDetector()
    ms = _state(rms=0.10, bands={"sub": 0.30, "low": 0.3, "mid": 0.25, "high": 0.15})

    # Seed baseline @ t=1000.
    ev = d.detect(ms, audio_buf=None, now=1000.0)
    assert ev is None, "first call seeds baseline, must not fire"

    # 8.5s later: sub collapses to 0.05 (Δ=0.25 ≥ 0.15 drop_min, new<0.10 floor),
    # rms still audible at 0.08.
    ms.bands = {"sub": 0.05, "low": 0.4, "mid": 0.35, "high": 0.20}
    ms.rms = 0.08
    ev = d.detect(ms, audio_buf=None, now=1008.5)
    assert ev is not None
    assert ev.type == "BREAKDOWN_KICK_KILL"
    assert ev.extra == {
        "prev_sub": 0.30,
        "new_sub": 0.05,
        "sub_drop": 0.25,
        "rms": 0.08,
    }


# ---------- Test 2: no fire when rms also dropped (silence, not kick kill) ----------


def test_breakdown_kick_kill_no_fire_when_rms_also_dropped():
    """Sub at 0.05 BUT rms at 0.02 (< LOW_RMS=0.040). This is silence /
    track-end, not a mid-track kick kill — silence gate must reject."""
    d = BreakdownKickKillDetector()
    ms = _state(rms=0.10, bands={"sub": 0.30, "low": 0.3, "mid": 0.25, "high": 0.15})
    d.detect(ms, audio_buf=None, now=1000.0)

    ms.bands = {"sub": 0.05, "low": 0.05, "mid": 0.05, "high": 0.05}
    ms.rms = 0.02  # below LOW_RMS=0.040
    ev = d.detect(ms, audio_buf=None, now=1008.5)
    assert ev is None


# ---------- Test 3: no fire on small sub drop ----------


def test_breakdown_kick_kill_no_fire_on_small_sub_drop():
    """Sub goes 0.30 → 0.20 (Δ=0.10) — but new value (0.20) is still ABOVE
    KICK_KILL_SUB_FLOOR=0.10. Kick still present, no kill."""
    d = BreakdownKickKillDetector()
    ms = _state(rms=0.10, bands={"sub": 0.30, "low": 0.3, "mid": 0.25, "high": 0.15})
    d.detect(ms, audio_buf=None, now=1000.0)

    ms.bands = {"sub": 0.20, "low": 0.3, "mid": 0.3, "high": 0.2}
    ev = d.detect(ms, audio_buf=None, now=1008.5)
    assert ev is None


# ---------- Test 4: cooldown blocks repeat fire (20s) ----------


def test_breakdown_kick_kill_cooldown():
    d = BreakdownKickKillDetector()
    ms = _state(rms=0.10, bands={"sub": 0.30, "low": 0.3, "mid": 0.25, "high": 0.15})
    d.detect(ms, audio_buf=None, now=1000.0)

    # First fire at t=1008.5
    ms.bands = {"sub": 0.05, "low": 0.4, "mid": 0.35, "high": 0.20}
    ms.rms = 0.08
    ev1 = d.detect(ms, audio_buf=None, now=1008.5)
    assert ev1 is not None

    # Within cooldown (20s) — even with a fresh baseline rotation in between,
    # a repeat kill within the window must not refire.
    # Rotate baseline back to 0.30 via an audible-tick that doesn't satisfy kill.
    ms.bands = {"sub": 0.30, "low": 0.3, "mid": 0.25, "high": 0.15}
    ms.rms = 0.10
    d.detect(ms, audio_buf=None, now=1018.0)  # rotates baseline (drift hygiene)

    # Now drop again — 19s after fire, < 20s cooldown, must be blocked.
    ms.bands = {"sub": 0.05, "low": 0.4, "mid": 0.35, "high": 0.20}
    ms.rms = 0.08
    ev2 = d.detect(ms, audio_buf=None, now=1027.5)  # 19s after first fire
    assert ev2 is None


# ---------- Test 5: first call seeds baseline, no fire ----------


def test_breakdown_kick_kill_baseline_seeded_on_first_call():
    d = BreakdownKickKillDetector()
    ms = _state(rms=0.10, bands={"sub": 0.30, "low": 0.3, "mid": 0.25, "high": 0.15})
    ev = d.detect(ms, audio_buf=None, now=1000.0)
    assert ev is None
    assert d.baseline_sub == 0.30
    assert d.baseline_at == 1000.0


# ---------- Test 6: exposes last_kill_at for ReentryKickLandDetector ----------


def test_breakdown_kick_kill_exposes_last_kill_at_for_pair_detector():
    """After a fire, ``detector.last_kill_at`` MUST equal the firing timestamp.
    The paired ``ReentryKickLandDetector`` reads this attribute as the
    dependency-injection contract — see Plan 17-03 Task 2."""
    d = BreakdownKickKillDetector()
    assert d.last_kill_at == 0.0  # initial state — no kill yet

    ms = _state(rms=0.10, bands={"sub": 0.30, "low": 0.3, "mid": 0.25, "high": 0.15})
    d.detect(ms, audio_buf=None, now=1000.0)

    ms.bands = {"sub": 0.05, "low": 0.4, "mid": 0.35, "high": 0.20}
    ms.rms = 0.08
    ev = d.detect(ms, audio_buf=None, now=1008.5)
    assert ev is not None
    assert d.last_kill_at == 1008.5


# ---------- Test 7: silent-phase gate ----------


def test_breakdown_kick_kill_phase_silent_gate():
    """``state.phase == "silent"`` rejects even when numbers look right —
    Phase 6's silent classification is authoritative for "music isn't really
    playing" (per the v4 anti-hallucination rule layered on top of LOW_RMS)."""
    d = BreakdownKickKillDetector()
    ms = _state(rms=0.10, bands={"sub": 0.30, "low": 0.3, "mid": 0.25, "high": 0.15})
    d.detect(ms, audio_buf=None, now=1000.0)

    ms.bands = {"sub": 0.05, "low": 0.4, "mid": 0.35, "high": 0.20}
    ms.rms = 0.08  # above LOW_RMS — but...
    ms.phase = "silent"  # ...phase classifier overrides
    ev = d.detect(ms, audio_buf=None, now=1008.5)
    assert ev is None


# ---------- Test 8: re-export ----------


def test_breakdown_kick_kill_detector_is_re_exported_from_subpackage():
    from vibemix.state.detectors import BreakdownKickKillDetector as Re

    assert Re is BreakdownKickKillDetector
