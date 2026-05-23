# SPDX-License-Identifier: Apache-2.0
"""Phase 68 Wave 1 — bundled-profile contract tests (DEV-01 part a + c).

One parametrized row per bundled controller profile. Each row asserts:

1. ``load_profile(profile_id)`` returns a non-None ``ControllerProfile``.
   ``_parse_profile`` raises ``ValueError`` on schema drift; that surfaces as a
   pytest ERROR (not just FAIL) — the exact behavior we want when a contributor
   pushes a malformed JSON.
2. ``profile.port_name_hints`` is a tuple of length ≥ 1 of non-empty strings.
   This pins the v7.0 Phase 68 success-criterion #1 ("non-empty `port_name_hint`"
   in CONTEXT.md §Profile Contracts — the actual field name is plural in the
   loaded dataclass).
3. No duplicate ``(channel, cc)`` across ``profile.controls.values()``. Duplicate
   CC binding inside one profile is a JSON authoring bug — two knobs claiming
   the same wire would silently shadow each other through ``_cc_lookup``
   (``src/vibemix/midi/state.py:172-174``).
4. No duplicate ``(channel, note)`` across ``profile.buttons.values()``. Same
   shadowing failure mode through ``_note_lookup``.

Anti-pattern (deliberately not used here): ``jsonschema.validate`` against
``schema.json``. Phase 68 Wave 0 deleted the schema file; the canonical schema
authority is ``profile.py::_parse_profile``, invoked by ``load_profile``. The
hand-written validator is the project-wide convention (no pydantic, no
jsonschema — see ``profile.py`` module docstring).

Phase 68 success-criterion mirror: this file MUST stay aligned with
``tests/midi/test_profiles_all_controllers.py``'s ``_ALL_CONTROLLER_IDS``
list — the two files target the same 10 bundled profiles for different
purposes (this = field-level invariants; that = registry-level pins). A
future profile addition or rename touches both.
"""

from __future__ import annotations

import pytest

from vibemix.midi import load_profile


# THE ten. Success-criterion 10 per ROADMAP P68 SC#1. Mirrored from
# test_profiles_all_controllers.py:36-47 — DO NOT auto-discover via glob;
# explicit list catches "a profile silently disappeared" regressions louder
# than a silently-shrinking parametrize list would.
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


@pytest.mark.parametrize("profile_id", _BUNDLED_IDS)
def test_profile_loads_and_validates(profile_id):
    """Every bundled profile loads cleanly and obeys the four field-level
    invariants — see module docstring for the assertion catalogue."""
    profile = load_profile(profile_id)
    assert profile is not None, (
        f"load_profile({profile_id!r}) returned None — bundled JSON missing? "
        f"Wave 0 deletion drift?"
    )

    # Invariant 2: port_name_hints is a non-empty tuple of non-empty strings.
    assert isinstance(profile.port_name_hints, tuple), (
        f"{profile_id}: port_name_hints must be a tuple, "
        f"got {type(profile.port_name_hints).__name__}"
    )
    assert len(profile.port_name_hints) >= 1, (
        f"{profile_id}: port_name_hints is empty — at least one hint required "
        f"so the registry can resolve this controller"
    )
    for hint in profile.port_name_hints:
        assert isinstance(hint, str) and hint, (
            f"{profile_id}: blank or non-str entry in port_name_hints: {hint!r}"
        )

    # Invariant 3: no duplicate (channel, cc) across controls.
    cc_keys = [(b.channel, b.cc) for b in profile.controls.values()]
    assert len(cc_keys) == len(set(cc_keys)), (
        f"{profile_id}: duplicate (channel, cc) pair in profile.controls — "
        f"keys: {cc_keys}"
    )

    # Invariant 4: no duplicate (channel, note) across buttons. Empty buttons
    # dict (a hypothetical deck-only controller) trivially passes.
    note_keys = [(b.channel, b.note) for b in profile.buttons.values()]
    assert len(note_keys) == len(set(note_keys)), (
        f"{profile_id}: duplicate (channel, note) pair in profile.buttons — "
        f"keys: {note_keys}"
    )
