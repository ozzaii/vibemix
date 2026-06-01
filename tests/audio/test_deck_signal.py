# SPDX-License-Identifier: Apache-2.0
"""DeckAudioCapture -> LiveSignalFrame adapter + end-to-end through the Judge."""
from __future__ import annotations

import numpy as np

from vibemix.audio.constants import INPUT_SR_TARGET
from vibemix.audio.deck_capture import DeckAudioCapture, DeckAudioRouting
from vibemix.audio.deck_signal import signal_frame_from_capture
from vibemix.intel.transition_judge import judge_transition
from vibemix.state.live_signal import LiveSignalFrame


def _routing(enabled=True):
    return DeckAudioRouting(
        opened_channels=4,
        master_channels=(0, 1),
        deck_channels={"A": (0, 1), "B": (2, 3)} if enabled else {},
        enabled=enabled,
    )


def _auto_routing():
    return DeckAudioRouting(
        opened_channels=4,
        master_channels=(0, 1, 2, 3),
        deck_channels={"A": (0, 1), "B": (2, 3)},
        enabled=True,
        source="rekordbox_settings",
        reason="rekordbox_settings_auto",
    )


def _meta():
    return {
        "A": {"camelot": "8A", "source_trusted": True, "track_id": "t1"},
        "B": {"camelot": "9A", "source_trusted": True, "track_id": "t2"},
    }


def _push_tone(buf, hz):
    sr = INPUT_SR_TARGET
    t = np.arange(sr) / sr
    buf.push((0.5 * np.sin(2 * np.pi * hz * t) * 32767.0).astype(np.int16))


def test_adapter_disabled_routing_marks_disabled():
    cap = DeckAudioCapture(_routing(enabled=False))
    frame = signal_frame_from_capture(cap, t_session=5.0, policy="supported_verdict", lane_meta=_meta())
    assert isinstance(frame, LiveSignalFrame)
    assert frame.routing_enabled is False


def test_adapter_treats_unverified_auto_rekordbox_pairs_as_disabled():
    cap = DeckAudioCapture(_auto_routing())
    indata = np.zeros((480, 4), dtype=np.float32)
    indata[:, 0] = 0.2
    indata[:, 1] = 0.2
    cap.process(indata, source_sr=48000)

    frame = signal_frame_from_capture(
        cap,
        t_session=5.0,
        policy="supported_verdict",
        lane_meta=_meta(),
    )

    assert frame.routing_enabled is False
    assert frame.lane("A").bands is None


def test_adapter_carries_lane_meta_and_bands():
    cap = DeckAudioCapture(_routing(enabled=True))
    _push_tone(cap.buffers["A"], 60.0)
    _push_tone(cap.buffers["B"], 60.0)
    frame = signal_frame_from_capture(cap, t_session=5.0, policy="supported_verdict", lane_meta=_meta())
    assert frame.routing_enabled is True
    a = frame.lane("A")
    assert a is not None
    assert a.camelot == "8A"
    assert a.bands is not None
    assert a.bands["sub"] > a.bands["mid"]


def test_e2e_judged_clean_harmonic_clean_bass():
    cap = DeckAudioCapture(_routing(enabled=True))
    cap.last_rms = {"A": 0.2, "B": 0.2}  # both lanes active
    _push_tone(cap.buffers["A"], 60.0)    # A: sub-heavy (bass up)
    _push_tone(cap.buffers["B"], 6000.0)  # B: high-only (bass killed -> clean swap)
    frame = signal_frame_from_capture(cap, t_session=10.0, policy="supported_verdict", lane_meta=_meta())
    v = judge_transition(frame)
    assert v.verdict_state == "judged"
    assert "harmonic" in v.components and "bass_collision" in v.components
    assert v.components["bass_collision"] == 1.0  # clean
    assert v.score is not None


def test_e2e_master_only_rig_abstains():
    cap = DeckAudioCapture(_routing(enabled=False))  # BlackHole-2ch master-only
    frame = signal_frame_from_capture(cap, t_session=10.0, policy="supported_verdict", lane_meta=_meta())
    v = judge_transition(frame)
    assert v.verdict_state == "abstained"
    assert v.abstain_reason == "routing_disabled"
