# SPDX-License-Identifier: Apache-2.0
"""DEV-03 hot-plug matrix.

Parametrizes the v4.0 P53 single-state callback across 3 distinct profiles
(Pioneer DDJ-FLX4, Pioneer DDJ-400, Hercules DJControl Inpulse 500). The
production callback (``vibemix.platform._midi_common::handle_port_change_single_state``)
is READ-ONLY — this test MUST NOT modify it. The single-state invariant under
test: ``id(holder.controller_state)`` is preserved across every
(dis)connect transition, the moves ring is cleared on disconnect (per the
v4.0 P53 ``mark_disconnected`` ring-clear in
``src/vibemix/midi/state.py``), and decode resumes on a fresh ring on
reconnect.

This file parametrizes the canonical FLX4-only pattern from
``tests/midi/test_disconnect_reconnect.py`` (lines 45-77) across three
profiles. The ``_DummyThread`` + ``_make_holder`` + ``_stub_spawn_listener``
helpers are lifted verbatim per 68-RESEARCH §Pattern 3 / §Pitfall #3 so the
production listener never opens a real ``mido`` port during the test.

Live ear-pass discharge (real FLX4 plug/unplug + real DDJ-400 + real
Inpulse-500) rides KAAN-ACTION §V7-LIVE-10 / Wave 4 (P05).
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from vibemix.midi import load_profile
from vibemix.midi.state import ControllerState
from vibemix.platform import _midi_common
from vibemix.platform._midi_common import ListenerHolder, handle_port_change_single_state

# Three (profile_id, port_name, sample_cc) rows — sample CCs verified against
# the corresponding profile JSON (channel + cc lookup) on 2026-05-23:
#   - Pioneer DDJ-FLX4    : (0, 19, 110)  → vol_a (deck A volume, unipolar)
#   - Pioneer DDJ-400     : (0, 19, 100)  → vol_a (deck A volume, unipolar)
#   - Hercules Inpulse-500: (1,  4,  90)  → eq_low_a (deck A EQ low, unipolar)
#                                          (FLX4-style ch=0, cc=15 is NOT
#                                           valid on Inpulse-500 — the EQ low
#                                           lives on channel 1, cc 4)
_PROFILES = [
    ("pioneer_ddj_flx4", "DDJ-FLX4 USB MIDI", (0, 19, 110)),
    ("pioneer_ddj_400", "DDJ-400", (0, 19, 100)),
    ("hercules_inpulse_500", "DJControl Inpulse 500", (1, 4, 90)),
]


class _DummyThread:
    """Stand-in for the listener thread — supports ``join()`` so the callback's
    teardown path runs without a real thread. Lifted verbatim from
    ``tests/midi/test_disconnect_reconnect.py``.
    """

    def __init__(self) -> None:
        self.joined = False

    def join(self, timeout: float | None = None) -> None:
        self.joined = True


def _make_holder(profile, port_name: str) -> ListenerHolder:
    """A ``ListenerHolder`` seeded with a real ``ControllerState`` (target
    profile) + a fake mido. ``spawn_listener`` is monkeypatched in each test
    so this holder's ``mido_module`` is never actually opened.

    Lifted verbatim from ``tests/midi/test_disconnect_reconnect.py:_make_holder``.
    """
    cs = ControllerState(profile=profile)
    fake_mido = SimpleNamespace(
        get_input_names=lambda: [port_name],
        open_input=lambda name: SimpleNamespace(
            __enter__=lambda self: self, __exit__=lambda *a: False, poll=lambda: None
        ),
    )
    return ListenerHolder(
        controller_state=cs,
        listener_thread=None,
        listener_stop=None,
        mido_module=fake_mido,
    )


def _stub_spawn_listener(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace ``spawn_listener`` with a dummy so no real port opens. MUST be
    called before any ``handle_port_change_single_state(('connected', ...))``
    invocation (68-RESEARCH Pitfall #3).
    """
    monkeypatch.setattr(_midi_common, "spawn_listener", lambda *a, **k: _DummyThread())


@pytest.mark.integration
@pytest.mark.parametrize("profile_id,port_name,sample_cc", _PROFILES)
def test_hotplug_single_state_across_three_profiles(
    monkeypatch: pytest.MonkeyPatch,
    profile_id: str,
    port_name: str,
    sample_cc: tuple[int, int, int],
) -> None:
    """Connect → state mutate → disconnect → reconnect, asserting the v4.0
    P53 single-state invariant holds across 3 distinct profiles.

    Invariants pinned per row:
      1. ``handle_port_change_single_state(('connected', ...))`` flips
         ``is_connected()`` to True without rebuilding the ControllerState
         object (``id`` preserved).
      2. A synthetic CC for one of the profile's real bindings produces at
         least one entry in ``moves_since(0.0)`` (proves the listener-thread
         → ControllerState wiring is intact for the bound profile).
      3. ``handle_port_change_single_state(('disconnected', ...))`` flips
         ``is_connected()`` to False, clears the moves ring (per
         ``mark_disconnected``'s ring-clear from v4.0 P53), and does NOT
         rebuild the ControllerState object.
      4. A subsequent ``('connected', ...)`` flips back to True with the
         same object identity — the single-state callback never swaps the
         ControllerState out from under the live-session consumers.
    """
    _stub_spawn_listener(monkeypatch)
    profile = load_profile(profile_id)
    assert profile is not None, f"load_profile({profile_id!r}) returned None"

    holder = _make_holder(profile, port_name)
    orig_id = id(holder.controller_state)

    # Phase 1 — CONNECT.
    handle_port_change_single_state(holder, ("connected", port_name, profile))
    assert holder.controller_state.is_connected() is True, (
        f"{profile_id}: not connected after ('connected', ...)"
    )
    assert holder.bound_port == port_name, (
        f"{profile_id}: bound_port mismatch after connect"
    )
    assert id(holder.controller_state) == orig_id, (
        f"{profile_id}: ControllerState rebuilt on connect — single-state invariant broken"
    )

    # Push a real binding to prove the decode path is wired.
    channel, control, value = sample_cc
    holder.controller_state.handle_msg(
        SimpleNamespace(type="control_change", channel=channel, control=control, value=value)
    )
    assert len(holder.controller_state.moves_since(0.0)) >= 1, (
        f"{profile_id}: no moves surfaced after connect — handle_msg not wired "
        f"(ch={channel}, cc={control}, v={value} did not match a binding)"
    )

    # Phase 2 — DISCONNECT.
    handle_port_change_single_state(holder, ("disconnected", port_name))
    assert holder.controller_state.is_connected() is False, (
        f"{profile_id}: still connected after ('disconnected', ...)"
    )
    assert holder.controller_state.moves_since(0.0) == [], (
        f"{profile_id}: ring not cleared on disconnect — v4.0 P53 invariant broken"
    )
    assert holder.bound_port is None, (
        f"{profile_id}: bound_port not cleared on disconnect"
    )
    assert id(holder.controller_state) == orig_id, (
        f"{profile_id}: ControllerState rebuilt on disconnect — single-state invariant broken"
    )

    # Phase 3 — RECONNECT.
    handle_port_change_single_state(holder, ("connected", port_name, profile))
    assert holder.controller_state.is_connected() is True, (
        f"{profile_id}: not reconnected"
    )
    assert id(holder.controller_state) == orig_id, (
        f"{profile_id}: ControllerState rebuilt on reconnect — single-state invariant broken"
    )
    assert holder.controller_state.moves_since(0.0) == [], (
        f"{profile_id}: ring not fresh on reconnect"
    )
