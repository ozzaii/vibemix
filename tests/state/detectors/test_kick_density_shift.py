# SPDX-License-Identifier: Apache-2.0
"""KickDensityShiftDetector — fires when ``state.onset_density`` crosses a
threshold band vs the trailing 8s baseline (regime change like half-time →
4-on-floor or 4-on-floor → broken).

Reads ``state.onset_density`` directly — does not touch ``audio_buf``. The
silent-phase gate (``state.phase == "silent"``) is checked alongside the RMS
gate so a Phase 6 silent-classification window cannot leak a phantom density
event during what the rest of the system already considers silence.
"""

from __future__ import annotations

from tests.state.detectors.conftest import _state
from vibemix.audio.constants import LOW_RMS
from vibemix.state.detectors.kick_density_shift import KickDensityShiftDetector


# ---------- Test 1: fires on jump up ----------


def test_kick_density_shift_fires_on_jump_up():
    """Half-time → 4-on-floor: onset_density 1.0 → 3.0 (Δ=2.0 ≥ 1.5)."""
    d = KickDensityShiftDetector()
    ms = _state(rms=0.06, onset_density=1.0)

    # Seed baseline at t=1000 with half-time density.
    ev = d.detect(ms, audio_buf=None, now=1000.0)
    assert ev is None, "first call seeds baseline, must not fire"

    # 8.5s later the kick pattern triples — fires.
    ms.onset_density = 3.0
    ev = d.detect(ms, audio_buf=None, now=1008.5)
    assert ev is not None
    assert ev.type == "KICK_DENSITY_SHIFT"
    assert ev.extra == {"prev_density": 1.0, "new_density": 3.0, "delta": 2.0}


# ---------- Test 2: fires on jump down ----------


def test_kick_density_shift_fires_on_jump_down():
    """4-on-floor → broken: onset_density 5.0 → 2.0 (signed Δ=-3.0, |Δ|=3.0).
    Regime drop is also a moment — extra.delta carries the sign."""
    d = KickDensityShiftDetector()
    ms = _state(rms=0.06, onset_density=5.0)
    d.detect(ms, audio_buf=None, now=1000.0)

    ms.onset_density = 2.0
    ev = d.detect(ms, audio_buf=None, now=1008.5)
    assert ev is not None
    assert ev.type == "KICK_DENSITY_SHIFT"
    assert ev.extra == {"prev_density": 5.0, "new_density": 2.0, "delta": -3.0}


# ---------- Test 3: no fire on small change ----------


def test_kick_density_shift_no_fire_on_small_change():
    d = KickDensityShiftDetector()
    ms = _state(rms=0.06, onset_density=2.0)
    d.detect(ms, audio_buf=None, now=1000.0)

    ms.onset_density = 2.5  # Δ=0.5 < 1.5
    ev = d.detect(ms, audio_buf=None, now=1008.5)
    assert ev is None


# ---------- Test 4: silence gate (low RMS) ----------


def test_kick_density_shift_silence_gate_low_rms():
    d = KickDensityShiftDetector()
    ms = _state(rms=LOW_RMS - 0.005, onset_density=1.0)
    ev = d.detect(ms, audio_buf=None, now=1000.0)
    assert ev is None
    # Silence gate fires BEFORE baseline seeding — baseline stays unset.
    assert d.baseline_density is None


# ---------- Test 5: cooldown blocks repeat fire (18s) ----------


def test_kick_density_shift_cooldown_18s():
    d = KickDensityShiftDetector()
    ms = _state(rms=0.06, onset_density=1.0)
    d.detect(ms, audio_buf=None, now=1000.0)

    ms.onset_density = 3.0
    ev1 = d.detect(ms, audio_buf=None, now=1008.5)
    assert ev1 is not None

    # Within cooldown window (18s) — must not refire even on another big jump.
    ms.onset_density = 5.0
    ev2 = d.detect(ms, audio_buf=None, now=1020.0)  # 11.5s after fire, < 18s cooldown
    assert ev2 is None


# ---------- Test 6: baseline rotation across the 8s window ----------


def test_kick_density_shift_baseline_rotation():
    """First call seeds baseline; a second call >= 8s later with no fire-worthy
    delta still rotates the baseline so a slow drift over minutes can never
    accumulate into a spurious fire."""
    d = KickDensityShiftDetector()
    ms = _state(rms=0.06, onset_density=2.0)

    # Seed
    d.detect(ms, audio_buf=None, now=1000.0)
    assert d.baseline_density == 2.0

    # 8s later, density at 2.5 (Δ=0.5, below threshold). Rotates baseline.
    ms.onset_density = 2.5
    ev = d.detect(ms, audio_buf=None, now=1008.5)
    assert ev is None
    assert d.baseline_density == 2.5
    assert d.baseline_at == 1008.5


# ---------- Test 7: silent-phase gate ----------


def test_kick_density_shift_no_fire_during_phase_silent():
    """When ``state.phase == "silent"`` the detector must return None even with
    a fire-worthy density delta — Phase 6's silent classification is
    authoritative for "music isn't really playing".
    """
    d = KickDensityShiftDetector()
    # Seed with audible groove
    ms = _state(rms=0.06, onset_density=1.0, phase="groove")
    d.detect(ms, audio_buf=None, now=1000.0)

    # Now the phase classifier flips to silent. Even though RMS happens to be
    # above LOW_RMS in this contrived setup AND the density delta would
    # otherwise fire, the silent-phase gate must reject.
    ms.phase = "silent"
    ms.onset_density = 3.0  # Δ=2.0 — would fire otherwise
    ev = d.detect(ms, audio_buf=None, now=1008.5)
    assert ev is None


# ---------- Test 8: re-export ----------


def test_kick_density_shift_detector_is_re_exported_from_subpackage():
    from vibemix.state.detectors import KickDensityShiftDetector as Re

    assert Re is KickDensityShiftDetector
