# SPDX-License-Identifier: Apache-2.0
"""2026-06-10 audit (E-midi finding 1) — the hot-plug -> MidiMirror hook.

At HEAD the hook was a closure inside _activate_session that called the
keyword-only MidiMirror.queue_controller_detected POSITIONALLY — every
connect/disconnect event died with a TypeError inside the watcher's
_safe_invoke (stderr-only), so the UI never saw controller_detected
envelopes and an unplug never marked the controller disconnected.
"""

from __future__ import annotations

from vibemix.__main__ import _make_midi_mirror_hotplug_hook
from vibemix.learn.midi_mirror import MidiMirror
from vibemix.midi import load_profile
from vibemix.midi.state import ControllerState

_PORT = "DDJ-FLX4 USB MIDI"


def _flx4():
    p = load_profile("pioneer_ddj_flx4")
    assert p is not None
    return p


def _make_hook():
    cs = ControllerState(profile=_flx4())
    mirror = MidiMirror(controller_state=cs)
    return _make_midi_mirror_hotplug_hook(mirror, cs), mirror, cs


def test_connected_event_binds_profile_and_queues_envelope():
    hook, mirror, _cs = _make_hook()

    hook(("connected", _PORT, _flx4()))  # must not raise (TypeError at HEAD)

    bound = mirror.current_profile()
    assert bound is not None and bound.id == "pioneer_ddj_flx4"
    pending = mirror.drain_pending_detected()
    assert len(pending) == 1
    payload = pending[0]["payload"]
    assert payload["connected"] is True
    assert payload["controller_id"] == "pioneer_ddj_flx4"
    assert payload["port_name"] == _PORT


def test_disconnected_event_queues_envelope_marks_disconnected_and_unbinds():
    hook, mirror, cs = _make_hook()
    hook(("connected", _PORT, _flx4()))
    cs.mark_connected(_PORT)
    mirror.drain_pending_detected()  # clear the connect envelope

    hook(("disconnected", _PORT))  # must not raise (TypeError at HEAD)

    pending = mirror.drain_pending_detected()
    assert len(pending) == 1
    payload = pending[0]["payload"]
    assert payload["connected"] is False
    assert payload["controller_id"] == "pioneer_ddj_flx4"
    assert cs.is_connected() is False, "unplug must mark the controller disconnected"
    assert mirror.current_profile() is None, "mirror unbinds after the envelope is queued"
