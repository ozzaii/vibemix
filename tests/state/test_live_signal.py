# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from vibemix.state.live_signal import LiveSignalFrame, LaneObservation


def test_lane_observation_is_frozen_and_minimal():
    lane = LaneObservation(
        active=True, source_trusted=True, camelot="8A",
        bands={"sub": 0.4, "low": 0.3, "mid": 0.2, "high": 0.1},
        rms=0.2, track_id="t1",
    )
    assert lane.active is True
    assert lane.camelot == "8A"
    try:
        lane.active = False  # type: ignore[misc]
        raised = False
    except AttributeError:
        raised = True
    assert raised


def test_frame_lane_helpers():
    a = LaneObservation(active=True, source_trusted=True, camelot="8A", bands=None, rms=0.2, track_id="t1")
    b = LaneObservation(active=False, source_trusted=True, camelot="9A", bands=None, rms=0.0, track_id="t2")
    frame = LiveSignalFrame(
        t_session=12.5, policy="supported_verdict", routing_enabled=True,
        lanes={"A": a, "B": b},
    )
    assert frame.both_lanes_active() is False  # B inactive
    assert set(frame.lane_sides()) == {"A", "B"}
    assert frame.lane("A") is a


def test_frame_both_active_true_when_both_active():
    a = LaneObservation(active=True, source_trusted=True, camelot="8A", bands=None, rms=0.2, track_id="t1")
    b = LaneObservation(active=True, source_trusted=True, camelot="9A", bands=None, rms=0.18, track_id="t2")
    frame = LiveSignalFrame(t_session=1.0, policy="supported_verdict", routing_enabled=True, lanes={"A": a, "B": b})
    assert frame.both_lanes_active() is True
