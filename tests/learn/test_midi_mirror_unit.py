# SPDX-License-Identifier: Apache-2.0
"""MidiMirror unit regression tests.

Pins the three load-bearing behaviours of ``vibemix.learn.midi_mirror.MidiMirror``
that keep the Learn controller mirror responsive without flooding the bus:

1. ``test_no_emit_when_steady`` — when the live ControllerState hasn't moved
   since the last ``snapshot()`` call, the next ``snapshot()`` returns
   ``None`` (delta-suppression — RESEARCH §Pattern 2). Without this, every
   30 Hz tick would emit a redundant ``ipc.learn.midi_position`` frame and
   flood the ws bus.

2. ``test_first_frame_after_bind`` — immediately after ``bind_profile()`` is
   called (the connect path), the very next ``snapshot()`` MUST emit (the
   delta cache was just cleared, so any current ControllerState reads as a
   change). This is the "fill the freshly-rendered SVG with current state"
   contract.

3. ``test_delta_emit_when_one_field_changes`` — when exactly one tracked
   control's integer LSB advances between snapshots, the emit fires and the
   payload's ``positions`` dict reflects the new value.

REQ-ID: RENDER-02 (MIDI mirror delta-suppression contract).
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest


def _midi_mirror_module():
    """Skip the calling test only in a partial build without MidiMirror."""
    return pytest.importorskip(
        "vibemix.learn.midi_mirror",
        reason="vibemix.learn.midi_mirror unavailable in this partial Learn build",
    )


def _make_steady_controller_state(positions: dict[str, int]) -> SimpleNamespace:
    """Build a fake ``ControllerState`` stub whose ``deck_snapshot()`` returns
    a synthetic dict matching the wire shape that
    ``MidiMirror._read_current_positions`` consumes (per RESEARCH §Code
    Example 1).

    The wire shape is::

        {
          "A": {"vol": 0, "eq_low": 64, "eq_mid": 64, "eq_hi": 64, ...},
          "B": {"vol": 0, "eq_low": 64, ...},
          "xfader": 64,
          "connected": True,
        }

    We translate the test's flat ``positions`` (e.g. ``{"eq_hi:A": 100}``)
    back into this nested shape so the fake stub mimics the real
    ControllerState's read API.
    """
    snap: dict = {"A": {}, "B": {}, "connected": True}
    for key, value in positions.items():
        if ":" in key:
            field, deck = key.split(":", 1)
            snap[deck][field] = value
        elif key == "xfader":
            snap["xfader"] = value
    cs = SimpleNamespace()
    cs.deck_snapshot = lambda: snap
    return cs


def _make_profile() -> SimpleNamespace:
    """Synthetic ControllerProfile stub. MidiMirror only reads ``.id`` and
    ``.display_name`` from the profile (per RESEARCH §Code Example 1)."""
    return SimpleNamespace(
        id="pioneer_ddj_flx4",
        display_name="Pioneer DDJ-FLX4",
    )


def test_no_emit_when_steady() -> None:
    """``snapshot()`` returns None when no tracked position has changed
    since the last successful emit (delta-suppression — RESEARCH §Pattern 2)."""
    midi_mirror_module = _midi_mirror_module()
    positions = {"eq_hi:A": 64, "eq_low:A": 64, "vol:A": 0, "xfader": 64}
    cs = _make_steady_controller_state(positions)
    profile = _make_profile()

    mirror = midi_mirror_module.MidiMirror(controller_state=cs)
    mirror.bind_profile(profile)

    # First snapshot after bind emits (covered by test_first_frame_after_bind);
    # we discard it here to set up the "steady state" precondition.
    first = mirror.snapshot()
    assert first is not None, "first frame after bind must emit"

    # Same ControllerState read → integer LSB delta == 0 → suppression.
    second = mirror.snapshot()
    assert second is None, (
        "delta-suppression broken — no tracked position changed but "
        "snapshot() emitted anyway (would flood ws bus at 30 Hz)"
    )


def test_first_frame_after_bind() -> None:
    """The first ``snapshot()`` after ``bind_profile()`` MUST emit — the
    delta cache was just cleared, so any current ControllerState reads as
    a change.

    This is the "fill the freshly-rendered SVG with current state"
    contract — without it, the SVG would mount but every knob/fader stays
    at its default visual position until the user touches one.
    """
    midi_mirror_module = _midi_mirror_module()
    positions = {"eq_hi:A": 64, "vol:A": 0, "xfader": 64}
    cs = _make_steady_controller_state(positions)
    profile = _make_profile()

    mirror = midi_mirror_module.MidiMirror(controller_state=cs)
    mirror.bind_profile(profile)

    frame = mirror.snapshot()
    assert frame is not None, "first frame after bind must emit (fill render)"
    assert frame["type"] == "ipc.learn.midi_position"
    assert frame["payload"]["controller_id"] == "pioneer_ddj_flx4"


def test_delta_emit_when_one_field_changes() -> None:
    """When exactly one tracked control's integer LSB advances between
    snapshots, the emit fires and the payload's ``positions`` dict
    reflects the new value."""
    midi_mirror_module = _midi_mirror_module()
    positions = {"eq_hi:A": 64, "vol:A": 0, "xfader": 64}
    cs = _make_steady_controller_state(positions)
    profile = _make_profile()

    mirror = midi_mirror_module.MidiMirror(controller_state=cs)
    mirror.bind_profile(profile)

    # Discard first-frame emit to establish steady state.
    _ = mirror.snapshot()
    assert mirror.snapshot() is None, "steady-state precondition broken"

    # Twist a single knob: eq_hi:A → 100.
    new_positions = dict(positions)
    new_positions["eq_hi:A"] = 100
    cs.deck_snapshot = lambda: {
        "A": {"eq_hi": 100, "vol": 0},
        "B": {},
        "xfader": 64,
        "connected": True,
    }

    frame = mirror.snapshot()
    assert frame is not None, "single-field delta must trigger emit"
    assert frame["type"] == "ipc.learn.midi_position"
    assert frame["payload"]["positions"]["eq_hi:A"] == 100


def test_snapshot_projects_one_shot_button_events() -> None:
    """Momentary buttons from ControllerState.events_since become pulses."""
    midi_mirror_module = _midi_mirror_module()
    positions = {"eq_hi:A": 64, "xfader": 64}
    event = SimpleNamespace(
        at=1_700_000_000.0,
        kind="sync",
        deck="B",
        value_raw=127,
    )
    cs = _make_steady_controller_state(positions)
    pending_events = [event]

    def events_since(_t: float) -> list[SimpleNamespace]:
        events = list(pending_events)
        pending_events.clear()
        return events

    cs.events_since = events_since
    profile = _make_profile()

    mirror = midi_mirror_module.MidiMirror(controller_state=cs)
    mirror.bind_profile(profile)

    frame = mirror.snapshot()
    assert frame is not None
    assert frame["payload"]["positions"]["sync:B"] == 127


def test_snapshot_projects_relative_jog_ticks_as_pulse_then_reset() -> None:
    """Relative jog CC ticks become a one-frame jog pulse over the 0 baseline."""
    midi_mirror_module = _midi_mirror_module()
    positions = {"jog:A": 0, "xfader": 64}
    event = SimpleNamespace(
        at=1_700_000_000.0,
        kind="cc",
        deck="A",
        field="jog",
        value_raw=65,
    )
    cs = _make_steady_controller_state(positions)
    pending_events = [event]

    def events_since(_t: float) -> list[SimpleNamespace]:
        events = list(pending_events)
        pending_events.clear()
        return events

    cs.events_since = events_since
    profile = _make_profile()

    mirror = midi_mirror_module.MidiMirror(controller_state=cs)
    mirror.bind_profile(profile)

    frame = mirror.snapshot()
    assert frame is not None
    assert frame["payload"]["positions"]["jog:A"] == 127

    reset = mirror.snapshot()
    assert reset is not None
    assert reset["payload"]["positions"]["jog:A"] == 0
