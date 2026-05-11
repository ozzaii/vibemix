# SPDX-License-Identifier: Apache-2.0
"""Phase 9 Wave 2 Task 1 — per-controller golden tests across all 10 profiles.

Pins for every bundled controller JSON:
- `list_profiles()` returns exactly the 10 expected ids (sorted).
- `load_profile(id)` returns a non-None ControllerProfile.
- `port_name_hints` is a non-empty tuple of non-empty strings.
- Deck count matches the controller's physical hardware (2 or 4 decks).
- v1 required controls: vol_<deck>, eq_low/mid/hi_<deck> per deck, plus xfader.
- play_<deck> button per deck.
- `find_mapping(profile.port_name_hints[0])` resolves to that profile.
- No two profiles share an exact port-name-hint string (substring overlap is allowed —
  guarded by alphabetic-id tiebreak in find_mapping).
- Profile id matches the JSON filename stem.
- ControllerState constructs from each profile without exception; deck_snapshot keys
  match `decks + ('xfader', 'connected')`.

These tests are intentionally cross-cutting — one failure indicates the JSON drifted
from CONTEXT or the Wave 1 schema.
"""

from __future__ import annotations

import itertools

import pytest

from vibemix.midi import (
    ControllerState,
    find_mapping,
    list_profiles,
    load_profile,
)

# Sorted (alphabetic) — must match list_profiles() output exactly.
_ALL_CONTROLLER_IDS = [
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

_TWO_DECK_IDS = {
    "hercules_inpulse_300",
    "hercules_inpulse_500",
    "numark_party_mix_live",
    "pioneer_ddj_400",
    "pioneer_ddj_flx4",
    "pioneer_ddj_flx6",
}

_FOUR_DECK_IDS = {
    "pioneer_ddj_1000",
    "pioneer_ddj_flx10",
    "pioneer_ddj_sx3",
    "pioneer_xdj_rx3",
}


# ---------- Registry-level pins ----------


def test_list_profiles_returns_10_entries():
    """All 10 controllers must ship — Phase 9 Wave 2 closes the controller library."""
    assert list_profiles() == _ALL_CONTROLLER_IDS


# ---------- Per-controller parametric pins ----------


@pytest.mark.parametrize("controller_id", _ALL_CONTROLLER_IDS)
def test_every_profile_loads_without_schema_error(controller_id):
    profile = load_profile(controller_id)
    assert profile is not None, f"load_profile({controller_id!r}) returned None"
    assert profile.id == controller_id


@pytest.mark.parametrize("controller_id", _ALL_CONTROLLER_IDS)
def test_every_profile_id_is_filename_stem(controller_id):
    """JSON `id` field must match the filename stem — guards against typos."""
    profile = load_profile(controller_id)
    assert profile is not None
    assert profile.id == controller_id


@pytest.mark.parametrize("controller_id", _ALL_CONTROLLER_IDS)
def test_every_profile_has_non_empty_port_name_hints(controller_id):
    profile = load_profile(controller_id)
    assert profile is not None
    assert isinstance(profile.port_name_hints, tuple)
    assert len(profile.port_name_hints) >= 1
    for hint in profile.port_name_hints:
        assert isinstance(hint, str)
        assert hint, f"profile {controller_id!r} has empty hint"


@pytest.mark.parametrize("controller_id", _ALL_CONTROLLER_IDS)
def test_every_profile_decks_count_matches_hardware(controller_id):
    profile = load_profile(controller_id)
    assert profile is not None
    if controller_id in _TWO_DECK_IDS:
        assert profile.decks == ("A", "B")
    elif controller_id in _FOUR_DECK_IDS:
        assert profile.decks == ("A", "B", "C", "D")
    else:
        pytest.fail(f"controller {controller_id!r} not in 2-deck or 4-deck partition")


@pytest.mark.parametrize("controller_id", _ALL_CONTROLLER_IDS)
def test_every_profile_has_v1_required_controls(controller_id):
    """Every profile must encode at minimum: vol + 3-band EQ per deck + an xfader."""
    profile = load_profile(controller_id)
    assert profile is not None

    # Look up bindings by (deck, field) so we don't depend on the binding key naming.
    by_field: dict[tuple[str | None, str], list] = {}
    for binding in profile.controls.values():
        key = (binding.deck, binding.field)
        by_field.setdefault(key, []).append(binding)

    for deck in profile.decks:
        for field in ("vol", "eq_low", "eq_mid", "eq_hi"):
            assert (deck, field) in by_field, (
                f"profile {controller_id!r} missing required control deck={deck!r} field={field!r}"
            )

    # At least one xfader (deck=None, field='xfader').
    xfader_bindings = [b for b in profile.controls.values() if b.field == "xfader"]
    assert len(xfader_bindings) >= 1, f"profile {controller_id!r} missing xfader control"


@pytest.mark.parametrize("controller_id", _ALL_CONTROLLER_IDS)
def test_every_profile_has_play_button_per_deck(controller_id):
    """play_<deck> button must exist for every deck — minimum playable controller surface."""
    profile = load_profile(controller_id)
    assert profile is not None

    play_decks = {b.deck for b in profile.buttons.values() if b.kind == "play"}
    for deck in profile.decks:
        assert deck in play_decks, (
            f"profile {controller_id!r} missing play button for deck={deck!r}"
        )


@pytest.mark.parametrize("controller_id", _ALL_CONTROLLER_IDS)
def test_find_mapping_resolves_each_controller_by_first_hint(controller_id):
    """`find_mapping(profile.port_name_hints[0])` must resolve back to this profile.

    No two profiles may share an exact hint (test_no_two_profiles_share_an_exact_port_name_hint
    covers that); substring overlap is resolved by alphabetic-id tiebreak in find_mapping.
    """
    profile = load_profile(controller_id)
    assert profile is not None
    hint = profile.port_name_hints[0]
    matched = find_mapping(hint)
    assert matched is not None, (
        f"find_mapping({hint!r}) returned None for {controller_id!r}'s own first hint"
    )
    # Substring overlap between hints is allowed, but the FLX4 first hint must NOT
    # collide with the FLX6/FLX10 hint (the JSONs are authored so their first hints
    # are mutually exclusive — DDJ-FLX4 vs DDJ-FLX6 vs DDJ-FLX10 differ by digit).
    # Hercules / Numark / DDJ-400 / DDJ-1000 / DDJ-SX3 / XDJ-RX3 hints are mutually
    # exclusive by construction.
    # Allow that find_mapping returns SOME controller whose hint is a substring of
    # this profile's first hint — but it must include this profile's id in its own
    # hint family. We require exact id match here as the cleanest invariant.
    assert matched.id == controller_id, (
        f"find_mapping({hint!r}) → {matched.id!r}, expected {controller_id!r} "
        f"(hint collision — first hints must disambiguate)"
    )


def test_no_two_profiles_share_an_exact_port_name_hint():
    """Exact hint duplication is a bug — alphabetic-id tiebreak would silently win.

    Substring overlap (e.g. 'FLX4' inside 'DDJ-FLX4 USB MIDI') IS allowed and HANDLED
    by find_mapping's first-match-by-sorted-id behavior. Exact-string sharing is not.
    """
    seen: dict[str, str] = {}  # hint -> profile_id
    for controller_id in _ALL_CONTROLLER_IDS:
        profile = load_profile(controller_id)
        assert profile is not None
        for hint in profile.port_name_hints:
            if hint in seen:
                pytest.fail(
                    f"exact hint {hint!r} appears in both {seen[hint]!r} and "
                    f"{controller_id!r}"
                )
            seen[hint] = controller_id


@pytest.mark.parametrize("controller_id", _ALL_CONTROLLER_IDS)
def test_every_profile_passes_through_controller_state_constructor(controller_id):
    profile = load_profile(controller_id)
    assert profile is not None
    cs = ControllerState(profile=profile)
    snap = cs.deck_snapshot()
    expected_keys = set(profile.decks) | {"xfader", "connected"}
    assert set(snap.keys()) == expected_keys


# ---------- Notes field (Wave 2 schema additive) ----------


@pytest.mark.parametrize("controller_id", _ALL_CONTROLLER_IDS)
def test_every_profile_notes_field_is_optional_str_or_none(controller_id):
    """The Wave 2 schema adds optional `notes` to ControllerProfile. The FLX4 JSON
    (Wave 1) has no notes field → loads with notes=None. The 9 Wave 2 JSONs SHOULD
    carry a notes string flagging their "JSON-only verified, hardware verification
    pending Phase 16/20" status."""
    profile = load_profile(controller_id)
    assert profile is not None
    assert hasattr(profile, "notes"), "ControllerProfile must expose a `notes` attribute"
    if profile.id == "pioneer_ddj_flx4":
        # FLX4 is Kaan-owned and live-verified — notes is None.
        assert profile.notes is None
    else:
        # Wave 2 JSONs all carry an "unverified" notes string.
        assert isinstance(profile.notes, str)
        assert profile.notes, f"profile {controller_id!r} notes must be non-empty when set"
        # Sanity check: the notes should mention something about verification status.
        # We don't pin exact wording — Kaan can edit the message later.


# ---------- Pairwise hint disambiguation ----------


def test_first_hints_are_pairwise_distinct():
    """Every profile's FIRST hint must differ from every other profile's first hint
    (case-insensitive). This is a stronger pin than the exact-string check — it guards
    against accidental case collisions like 'DDJ-1000' vs 'ddj-1000'.
    """
    first_hints_lower = {}
    for controller_id in _ALL_CONTROLLER_IDS:
        profile = load_profile(controller_id)
        assert profile is not None
        h = profile.port_name_hints[0].lower()
        if h in first_hints_lower:
            pytest.fail(
                f"first hint {h!r} (case-insensitive) appears in both "
                f"{first_hints_lower[h]!r} and {controller_id!r}"
            )
        first_hints_lower[h] = controller_id


# ---------- Cross-profile combinatorial — substring containment is OK ----------


@pytest.mark.parametrize(
    "id_a,id_b",
    list(itertools.combinations(_ALL_CONTROLLER_IDS, 2)),
)
def test_no_profile_pair_shares_an_exact_hint(id_a, id_b):
    """Parametric form of test_no_two_profiles_share_an_exact_port_name_hint —
    surfaces the exact pair that collides when this test fails."""
    a = load_profile(id_a)
    b = load_profile(id_b)
    assert a is not None and b is not None
    overlap = set(a.port_name_hints) & set(b.port_name_hints)
    assert not overlap, (
        f"profiles {id_a!r} and {id_b!r} share exact hints: {sorted(overlap)}"
    )
