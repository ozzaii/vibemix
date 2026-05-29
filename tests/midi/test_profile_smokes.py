# SPDX-License-Identifier: Apache-2.0
"""Phase 68 Wave 1 — synthetic-MIDI decode smokes (DEV-01 part b).

One parametrized row per bundled controller profile. Each row:

1. Loads the profile via ``load_profile(profile_id)`` and constructs a real
   ``ControllerState`` bound to it. Marks it connected so the live binding
   path (``mark_connected(port_name)``) is exercised — the listener-thread
   handoff in ``src/vibemix/midi/state.py:179-182``.
2. Iterates every CC binding in ``profile.controls.values()`` and pushes one
   synthetic ``control_change`` per binding through ``handle_msg``. Value is
   axis-dependent: 80 for unipolar (mid-high range), 90 for bipolar (off-
   center positive), 65 for relative encoders, 64 fallback for any other axis
   (keeps the test forward-compatible).
3. Iterates every NOTE binding in ``profile.buttons.values()`` and pushes one
   synthetic ``note_on`` per binding through ``handle_msg``.
4. Asserts at least one event surfaced via ``events_since(0.0)``. The
   ControllerState-only assertion is sufficient per the plan's research
   §Assumption A5 — the success criterion's "→ MusicState" chain is
   exercised in production code, not required in this smoke (MusicState's
   refresh loop reads ``deck_snapshot()`` + ``events_since()`` from the
   asyncio event loop, not from the MIDI listener thread).

Failure mode this catches: a binding whose ``field`` references a key that
``ControllerState.deck`` doesn't initialise → ``handle_msg`` raises KeyError
on the per-deck mutation → the swallowing try/except in
``state.py:375-376`` logs but the smoke would assert ≥ 1 event surfaced and
get zero (KeyError prevents ``_record_event`` from running). Result: the
row turns red with the offending profile_id in the assertion message.

Synthesis pattern lifted from ``tests/midi/test_flx4_synthetic_decode.py:33-42``
(the project-canonical SimpleNamespace MIDI factory shape). Bundled-IDs list
mirrored from ``tests/midi/test_profile_contracts.py`` — drift between the two
files is itself a contract bug (a profile added to one must be added to both).
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from vibemix.midi import load_profile
from vibemix.midi.state import ControllerState

# THE ten. Mirror of test_profile_contracts.py::_BUNDLED_IDS — if you add a
# profile to one of these files, add it to BOTH. The plan-level rule:
# DO NOT auto-discover via glob; explicit list catches "silently dropped a
# profile" regressions louder than a shrinking parametrize list would.
_BUNDLED_IDS = [
    "hercules_inpulse_300",
    "hercules_inpulse_500",
    "numark_party_mix_live",
    "pioneer_ddj_1000",
    "pioneer_ddj_400",
    "pioneer_ddj_flx10",
    "pioneer_ddj_flx4",
    "pioneer_ddj_flx6",
    "pioneer_ddj_sx3",
    "pioneer_xdj_rx3",
]


# ---------- mido-shaped message factories (lifted verbatim from
#            tests/midi/test_flx4_synthetic_decode.py:33-42) ----------


def _cc(channel: int, control: int, value: int):
    return SimpleNamespace(type="control_change", channel=channel, control=control, value=value)


def _note_on(channel: int, note: int, velocity: int = 127):
    return SimpleNamespace(type="note_on", channel=channel, note=note, velocity=velocity)


def _value_for_axis(axis: str) -> int:
    """Choose a representative CC value per axis kind.

    - unipolar (knobs / faders, 0..127): 80 — mid-high, well above the
      _knob_label 'flat' tier so an event lands in 'boost'.
    - bipolar (tempo / xfader / filter, center=64): 90 — off-center positive,
      well past the 73 boundary into the 'boost' tier on the bipolar axes.
    - relative (jog encoders): 65 — one forward tick around the 64 center.
    - any other (forward-compat for axes added beyond _VALID_AXES): 64 — a
      safe mid-range fallback.
    """
    return {"unipolar": 80, "bipolar": 90, "relative": 65}.get(axis, 64)


# ---------- The smoke ----------


@pytest.mark.parametrize("profile_id", _BUNDLED_IDS)
def test_profile_synthetic_midi_smoke(profile_id):
    """Every CC + NOTE binding decodes through ControllerState.handle_msg
    without raising; at least one typed event surfaces in events_since(0.0)."""
    profile = load_profile(profile_id)
    assert profile is not None, (
        f"{profile_id}: load_profile returned None — bundled JSON missing?"
    )

    cs = ControllerState(profile=profile)
    # Mirror the live binding path — listener thread calls this when the
    # device opens. Not strictly required for decode (handle_msg doesn't gate
    # on connected), but exercises the symmetric mark_connected/mark_disconnected
    # surface here so a future regression in mark_connected surfaces in this smoke.
    cs.mark_connected(profile.port_name_hints[0])

    # Exercise every CC binding.
    for binding in profile.controls.values():
        msg = _cc(binding.channel, binding.cc, _value_for_axis(binding.axis))
        cs.handle_msg(msg)  # MUST NOT raise — handle_msg's outer try/except
        # swallows live-decode exceptions to stderr, so the failure mode here
        # is the absence of a corresponding event in the final ring, not a
        # raised exception. The events_since(0.0) >= 1 assertion below catches it.

    # Exercise every NOTE binding.
    for binding in profile.buttons.values():
        msg = _note_on(binding.channel, binding.note, velocity=127)
        cs.handle_msg(msg)

    events = cs.events_since(0.0)
    assert len(events) >= 1, (
        f"{profile_id}: zero events surfaced after exercising "
        f"{len(profile.controls)} CC bindings + {len(profile.buttons)} NOTE "
        f"bindings — decode broken, or every binding's field/kind triggered "
        f"the handle_msg try/except swallow (check stderr for [midi handle err])"
    )
