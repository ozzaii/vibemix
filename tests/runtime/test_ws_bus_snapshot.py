# SPDX-License-Identifier: Apache-2.0
"""ws_broadcast now ALSO emits a schema-valid ``ipc.session.snapshot``.

The Tauri shell spawns the sidecar flag-less (``__main__.py:main()`` — the
real cohost), whose only WS emitter is ``ws_broadcast``. Before this fix it
emitted ONLY the flat mascot frame, leaving every session panel
(meters/bpm/track/cohost-status/grounded/midi/transcript) dead.

These tests exercise the pure snapshot builder (``_build_session_snapshot``)
against fake refs — no socket, no port bind — and assert the result passes
the SAME outbound validator (``vibemix.ui_bus.validator.validate_message``)
the WizardBus / SessionLoop use, and carries the expected fields.
"""

from __future__ import annotations

from collections import deque
from types import SimpleNamespace

from vibemix.runtime.ws_bus import _build_session_snapshot
from vibemix.ui_bus.validator import validate_message


class _FakeLevels:
    def __init__(
        self,
        music: float,
        voice: float,
        mic: float,
        *,
        music_peak: float | None = None,
        voice_peak: float | None = None,
        mic_peak: float | None = None,
    ) -> None:
        self._snap = {
            "music": music,
            "voice": voice,
            "mic": mic,
            "music_peak": music if music_peak is None else music_peak,
            "voice_peak": voice if voice_peak is None else voice_peak,
            "mic_peak": mic if mic_peak is None else mic_peak,
        }

    def snapshot(self) -> dict[str, float]:
        return dict(self._snap)


def _fake_state(**kw) -> SimpleNamespace:
    base = dict(
        audible=True,
        bpm=128.0,
        audible_track="Floorplan - Never Grow Old",
        audible_deck="B",
    )
    base.update(kw)
    return SimpleNamespace(**base)


def test_snapshot_is_schema_valid_and_carries_fields():
    msg = _build_session_snapshot(
        _FakeLevels(0.42, 0.0, 0.01),
        _fake_state(),
    )
    # MUST pass the same outbound validator the bus uses.
    validate_message(msg)

    assert msg["type"] == "ipc.session.snapshot"
    p = msg["payload"]
    # Meters
    assert p["meters"]["music"]["rms"] == 0.42
    assert p["meters"]["music"]["peak"] == 0.42
    assert p["meters"]["voice"]["rms"] == 0.0
    assert p["meters"]["mic"]["rms"] == 0.01
    # BPM + track
    assert p["bpm"] == 128.0
    assert p["track"]["title"] == "Floorplan - Never Grow Old"
    assert p["track"]["deck"] == "B"
    # Audible music + no AI voice → LISTENING; grounded mirrors audible.
    assert p["cohost_status"] == "LISTENING"
    assert p["grounded"] is True
    assert p["claim_policy"] == {
        "policy": "requires_more_evidence",
        "level": "yellow",
        "reason": None,
    }


def test_snapshot_carries_real_level_peaks():
    msg = _build_session_snapshot(
        _FakeLevels(0.18, 0.04, 0.02, music_peak=0.61, voice_peak=0.12, mic_peak=0.09),
        _fake_state(),
    )
    validate_message(msg)
    p = msg["payload"]
    assert p["meters"]["music"] == {"rms": 0.18, "peak": 0.61}
    assert p["meters"]["voice"] == {"rms": 0.04, "peak": 0.12}
    assert p["meters"]["mic"] == {"rms": 0.02, "peak": 0.09}


def test_snapshot_carries_drop_prediction_as_bars():
    msg = _build_session_snapshot(
        _FakeLevels(0.42, 0.0, 0.01),
        _fake_state(predicted_drop_in_sec=15.0, bpm=128.0),
    )
    validate_message(msg)
    assert msg["payload"]["drop_pred_bars"] == 8


def test_snapshot_hides_drop_prediction_without_bpm_lock():
    msg = _build_session_snapshot(
        _FakeLevels(0.42, 0.0, 0.01),
        _fake_state(predicted_drop_in_sec=15.0, bpm=0.0),
    )
    validate_message(msg)
    assert msg["payload"]["drop_pred_bars"] is None


def test_cohost_status_talking_when_voice_active():
    msg = _build_session_snapshot(_FakeLevels(0.3, 0.2, 0.0), _fake_state())
    validate_message(msg)
    assert msg["payload"]["cohost_status"] == "TALKING"


def test_cohost_status_idle_and_grounded_false_when_silent():
    msg = _build_session_snapshot(
        _FakeLevels(0.0, 0.0, 0.0),
        _fake_state(
            audible=False,
            bpm=111.1,
            audible_track="Stale Cached Track",
            audible_deck="A",
            predicted_drop_in_sec=15.0,
        ),
    )
    validate_message(msg)
    p = msg["payload"]
    assert p["cohost_status"] == "IDLE"
    assert p["grounded"] is False
    assert p["bpm"] is None
    assert p["drop_pred_bars"] is None
    assert p["track"] is None


def test_levels_clamped_to_unit_interval():
    # EMA drift above 1.0 must clamp so the validator's [0,1] bound holds.
    msg = _build_session_snapshot(_FakeLevels(2.5, -0.3, 1.7), _fake_state())
    validate_message(msg)  # would raise if unclamped
    p = msg["payload"]
    assert p["meters"]["music"]["rms"] == 1.0
    assert p["meters"]["voice"]["rms"] == 0.0
    assert p["meters"]["mic"]["rms"] == 1.0


def test_transcript_delta_drains_sink():
    sink: deque = deque(["yo that drop", "keep it rolling"])
    msg = _build_session_snapshot(
        _FakeLevels(0.3, 0.0, 0.0),
        _fake_state(),
        transcript_buf=sink,
    )
    validate_message(msg)
    lines = msg["payload"]["transcript_delta"]
    assert [line["text"] for line in lines] == ["yo that drop", "keep it rolling"]
    assert all(line["role"] == "ai" for line in lines)
    # Sink is drained — a second build yields nothing new.
    assert len(sink) == 0
    msg2 = _build_session_snapshot(
        _FakeLevels(0.3, 0.0, 0.0), _fake_state(), transcript_buf=sink
    )
    validate_message(msg2)
    assert msg2["payload"]["transcript_delta"] == []


def test_midi_ribbon_drains_moves_since():
    class _FakeController:
        def __init__(self) -> None:
            self.calls: list[float] = []

        def moves_since(self, t: float):
            self.calls.append(t)
            # First drain returns two moves; subsequent drains return none.
            if len(self.calls) == 1:
                return [(0.2, "jog A"), (0.1, "xfader")]
            return []

    ctrl = _FakeController()
    hwm = [0.0]
    msg = _build_session_snapshot(
        _FakeLevels(0.3, 0.0, 0.0),
        _fake_state(),
        controller_state=ctrl,
        last_move_ts=hwm,
    )
    validate_message(msg)
    events = msg["payload"]["midi_events"]
    assert [e["control"] for e in events] == ["jog A", "xfader"]
    # High-water mark advanced past 0.0.
    assert hwm[0] > 0.0

    msg2 = _build_session_snapshot(
        _FakeLevels(0.3, 0.0, 0.0),
        _fake_state(),
        controller_state=ctrl,
        last_move_ts=hwm,
    )
    validate_message(msg2)
    assert msg2["payload"]["midi_events"] == []


def test_midi_controller_failure_is_swallowed():
    class _Boom:
        def moves_since(self, t: float):
            raise RuntimeError("midi thread died")

    msg = _build_session_snapshot(
        _FakeLevels(0.3, 0.0, 0.0),
        _fake_state(),
        controller_state=_Boom(),
        last_move_ts=[0.0],
    )
    validate_message(msg)  # must not raise — snapshot still valid
    assert msg["payload"]["midi_events"] == []
