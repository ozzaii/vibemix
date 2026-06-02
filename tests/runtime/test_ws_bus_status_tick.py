# SPDX-License-Identifier: Apache-2.0
"""ws_broadcast now ALSO emits a ~1Hz ``ipc.status.tick``.

Until this existed the live session (``__main__.py:main()`` → ``ws_broadcast``)
emitted mascot + ``ipc.session.snapshot`` but NO status tick, so the status-row
badges (audio/screen/midi) stayed neutral. These tests exercise the pure probe
helpers against fakes (no socket, no port bind) and assert the ``StatusTick``
built from them passes the SAME outbound validator the bus uses.

Honesty + never-fault contract (see STATUS_EVERY_N comment in ws_bus.py):
livekit/gemini are "ok" (the real gemini-down signal is the SessionLayout
grounding-failure timer, not this tick); midi is the connected-controller count
for the compact footer LED, while no-frame/no-move detail stays in the
deck_mixer.midi_activity proof channel; screen is a live non-prompting probe
used ONLY to light the badge — denied or unavailable is NOT a deck fault
(faultInput drops screen; audio-only is valid).
"""

from __future__ import annotations

from types import SimpleNamespace

from vibemix.runtime import ws_bus
from vibemix.runtime.ws_bus import _probe_midi_count, _probe_screen_status
from vibemix.ui_bus.messages import StatusTick
from vibemix.ui_bus.validator import validate_message


def test_probe_midi_count_reflects_active_port():
    # No controller wired → None (neutral badge, not a fabricated zero).
    assert _probe_midi_count(None) is None
    # An open port → 1; no port → 0.
    assert _probe_midi_count(SimpleNamespace(port_name="DDJ-FLX4")) == 1
    assert _probe_midi_count(SimpleNamespace(port_name="")) == 0


def test_probe_midi_count_treats_visible_controller_as_connected():
    controller = SimpleNamespace(port_name="DDJ-FLX4")

    assert (
        _probe_midi_count(
            controller,
            SimpleNamespace(
                controller_connected=True,
                controller_midi_activity="connected_no_midi_traffic",
                controller_midi_messages_seen=0,
            ),
        )
        == 1
    )
    assert (
        _probe_midi_count(
            controller,
            SimpleNamespace(
                controller_connected=True,
                controller_midi_activity="active",
                controller_midi_messages_seen=12,
            ),
        )
        == 1
    )
    assert (
        _probe_midi_count(
            controller,
            SimpleNamespace(
                controller_connected=False,
                controller_midi_activity="disconnected",
                controller_midi_messages_seen=0,
            ),
        )
        == 0
    )


def test_probe_midi_count_is_fail_soft():
    class _Boom:
        @property
        def port_name(self):
            raise RuntimeError("midi thread died")

    # A faulting controller_state must degrade to None, never propagate.
    assert _probe_midi_count(_Boom()) is None


def test_probe_screen_status_maps_authorized_to_ok(monkeypatch):
    monkeypatch.setattr(
        "vibemix.platform.permissions.check_screen_recording_permission",
        lambda: "authorized",
    )
    assert _probe_screen_status() == "ok"


def test_probe_screen_status_maps_unavailable_before_permission_probe(monkeypatch):
    monkeypatch.setattr(
        "vibemix.platform.permissions.check_screen_recording_permission",
        lambda: "authorized",
    )
    assert _probe_screen_status(screen_available=False) == "unavailable"


def test_probe_screen_status_maps_denied(monkeypatch):
    monkeypatch.setattr(
        "vibemix.platform.permissions.check_screen_recording_permission",
        lambda: "denied",
    )
    assert _probe_screen_status() == "denied"


def test_probe_screen_status_fail_soft_to_unavailable(monkeypatch):
    # A raising probe must NOT paint a false green badge.
    def _boom():
        raise RuntimeError("no Quartz")

    monkeypatch.setattr(
        "vibemix.platform.permissions.check_screen_recording_permission", _boom
    )
    assert _probe_screen_status() == "unavailable"


def test_status_tick_built_from_probes_is_schema_valid(monkeypatch):
    monkeypatch.setattr(
        "vibemix.platform.permissions.check_screen_recording_permission",
        lambda: "authorized",
    )
    msg = StatusTick.make(
        livekit="ok",
        gemini="ok",
        midi=_probe_midi_count(SimpleNamespace(port_name="DDJ-FLX4")),
        screen=_probe_screen_status(),  # type: ignore[arg-type]
    )
    import json

    payload = json.loads(msg.to_json())
    validate_message(payload)  # would raise if the wire frame were malformed
    assert payload["type"] == "ipc.status.tick"
    assert payload["payload"] == {
        "livekit": "ok",
        "gemini": "ok",
        "midi": 1,
        "screen": "ok",
    }


def test_status_tick_accepts_screen_unavailable():
    msg = StatusTick.make(
        livekit="ok",
        gemini="ok",
        midi=None,
        screen="unavailable",
    )
    import json

    payload = json.loads(msg.to_json())
    validate_message(payload)
    assert payload["payload"]["screen"] == "unavailable"


def test_status_every_n_is_roughly_one_hz():
    # 30Hz mascot loop / 30 ≈ 1Hz status cadence. Pin it so a future tweak to
    # the loop sleep doesn't silently spam the badges.
    assert ws_bus.STATUS_EVERY_N == 30
