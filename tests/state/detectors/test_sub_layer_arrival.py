# SPDX-License-Identifier: Apache-2.0
"""SubLayerArrivalDetector — fires when state.bands["sub"] jumps >=
SUB_JUMP_THRESHOLD vs the trailing 8s baseline AND BPM stayed stable
(|Δbpm| <= 4.0). The BPM-stability gate is the anti-double-fire contract
with TRACK_CHANGE: cross-track sub jumps almost always shift BPM by >4 in
dance music, so TRACK_CHANGE owns those moments.
"""

from __future__ import annotations

from tests.state.detectors.conftest import _state
from vibemix.audio.constants import LOW_RMS
from vibemix.state.detectors.sub_layer_arrival import SubLayerArrivalDetector


# ---------- Test 1: fires on sub jump with stable BPM ----------


def test_sub_layer_arrival_fires_on_sub_jump_with_stable_bpm():
    d = SubLayerArrivalDetector()
    ms = _state(rms=0.06, bpm=130.0, bands={"sub": 0.20, "low": 0.3, "mid": 0.3, "high": 0.2})

    # Seed baseline @ t=1000
    ev = d.detect(ms, audio_buf=None, now=1000.0)
    assert ev is None

    # 8.5s later: sub jumps from 0.20 to 0.35 (Δ=0.15 >= 0.10 threshold), bpm stable.
    ms.bands = {"sub": 0.35, "low": 0.3, "mid": 0.2, "high": 0.15}
    ev = d.detect(ms, audio_buf=None, now=1008.5)
    assert ev is not None
    assert ev.type == "SUB_LAYER_ARRIVAL"
    assert ev.extra == {"prev_sub": 0.20, "new_sub": 0.35, "sub_jump": 0.15}


# ---------- Test 2: no fire on BPM change (track change suspected) ----------


def test_sub_layer_arrival_no_fire_on_bpm_change():
    d = SubLayerArrivalDetector()
    ms = _state(rms=0.06, bpm=130.0, bands={"sub": 0.20, "low": 0.3, "mid": 0.3, "high": 0.2})
    d.detect(ms, audio_buf=None, now=1000.0)
    # 8.5s later sub jumps BUT bpm jumps from 130 to 145 (Δ=15 > 4.0).
    ms.bands = {"sub": 0.35, "low": 0.3, "mid": 0.2, "high": 0.15}
    ms.bpm = 145.0
    ev = d.detect(ms, audio_buf=None, now=1008.5)
    assert ev is None  # TRACK_CHANGE owns this; SubLayerArrival defers


# ---------- Test 3: no fire on small jump ----------


def test_sub_layer_arrival_no_fire_on_small_jump():
    d = SubLayerArrivalDetector()
    ms = _state(rms=0.06, bpm=130.0, bands={"sub": 0.20, "low": 0.3, "mid": 0.3, "high": 0.2})
    d.detect(ms, audio_buf=None, now=1000.0)
    ms.bands = {"sub": 0.25, "low": 0.3, "mid": 0.25, "high": 0.2}  # Δ=0.05 < 0.10
    ev = d.detect(ms, audio_buf=None, now=1008.5)
    assert ev is None


# ---------- Test 4: silence gate ----------


def test_sub_layer_arrival_silence_gate():
    d = SubLayerArrivalDetector()
    ms = _state(rms=LOW_RMS - 0.005, bpm=130.0,
                bands={"sub": 0.20, "low": 0.3, "mid": 0.3, "high": 0.2})
    ev = d.detect(ms, audio_buf=None, now=1000.0)
    assert ev is None
    # Silence gate fires BEFORE baseline rotation — baseline stays unset.
    assert d.baseline_sub is None


# ---------- Test 5: cooldown blocks repeat fire ----------


def test_sub_layer_arrival_cooldown_16s():
    d = SubLayerArrivalDetector()
    ms = _state(rms=0.06, bpm=130.0, bands={"sub": 0.20, "low": 0.3, "mid": 0.3, "high": 0.2})
    d.detect(ms, audio_buf=None, now=1000.0)
    ms.bands = {"sub": 0.35, "low": 0.3, "mid": 0.2, "high": 0.15}
    ev1 = d.detect(ms, audio_buf=None, now=1008.5)
    assert ev1 is not None

    # Within cooldown (16s) — must not refire even on big jump.
    # First trigger another rotate
    d.detect(ms, audio_buf=None, now=1018.0)  # 9.5s after fire, just rotates baseline
    ms.bands = {"sub": 0.55, "low": 0.2, "mid": 0.15, "high": 0.1}
    ev2 = d.detect(ms, audio_buf=None, now=1022.0)  # 13.5s after fire, < 16s cooldown
    assert ev2 is None


# ---------- Test 6: reads state.bands, NOT audio_buf ----------


def test_sub_layer_arrival_uses_state_bands_not_audio_buf():
    """audio_buf=None is fine — detector reads state.bands["sub"] which
    state_refresh_loop already populated. Re-deriving from raw samples would
    duplicate the snapshot_features work the writer just did."""
    d = SubLayerArrivalDetector()
    ms = _state(rms=0.06, bpm=130.0, bands={"sub": 0.20, "low": 0.3, "mid": 0.3, "high": 0.2})
    d.detect(ms, audio_buf=None, now=1000.0)
    ms.bands = {"sub": 0.35, "low": 0.3, "mid": 0.2, "high": 0.15}
    ev = d.detect(ms, audio_buf=None, now=1008.5)
    assert ev is not None and ev.type == "SUB_LAYER_ARRIVAL"


# ---------- Test 7: re-export ----------


def test_sub_layer_arrival_detector_is_re_exported_from_subpackage():
    from vibemix.state.detectors import SubLayerArrivalDetector as Re

    assert Re is SubLayerArrivalDetector
