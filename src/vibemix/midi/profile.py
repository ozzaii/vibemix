# SPDX-License-Identifier: Apache-2.0
"""ControllerProfile dataclass + JSON loader + hand-written schema validator.

Phase 9 Wave 1 — declarative controller mapping data layer. Mirrors the
``vibemix.state.genre.profile`` shape (Phase 6) so the codebase stays
consistent: frozen dataclass + ``importlib.resources`` JSON discovery +
hand-written validator (no pydantic per CONTEXT §Locked / Phase 6 §Critical
Constraint 6 — no new heavy deps).

Locked schema (09-CONTEXT.md §Locked Decisions §Mapping format)::

    {
      "id": "pioneer_ddj_flx4",
      "display_name": "Pioneer DDJ-FLX4",
      "port_name_hints": ["DDJ-FLX4", "FLX4"],
      "decks": ["A", "B"],
      "controls": {
        "<binding_name>": {
          "kind": "cc", "channel": 0..15, "cc": 0..127,
          "axis": "unipolar" | "bipolar",
          "deck": "A" | "B" | null, "field": "vol" | "eq_hi" | ...
        },
        ...
      },
      "buttons": {
        "<binding_name>": {
          "kind": "play"|"cue"|"sync"|"jog_touch"|"loop_in"|"loop_out"|...,
          "channel": 0..15, "note": 0..127,
          "deck": "A" | "B" | null
        },
        ...
      }
    }

Frozen-instance contract:
    Top-level dataclass fields cannot be reassigned (raises
    ``dataclasses.FrozenInstanceError``). Inner ``controls`` / ``buttons``
    dicts are read-only by convention — same trade-off Phase 6's
    ``GenreProfile.band_signature: dict[...]`` accepts. Callers must NOT
    mutate them.

No active-singleton: midi profiles have no module-level "active" — each
connected port resolves its own profile via ``vibemix.midi.registry.find_mapping``.
This is the deliberate asymmetry vs. Phase 6 ``set_active_profile``: a single
machine can have multiple controllers plugged in at once.
"""

from __future__ import annotations

import importlib.resources
import json
from dataclasses import dataclass

_PROFILES_PKG = "vibemix.midi.profiles"

# Locked per 09-CONTEXT.md §Magnitude semantics — only two axes Wave 1+2 ship.
_VALID_AXES = frozenset({"unipolar", "bipolar"})

# Superset covering Wave 1 (FLX4) + Wave 2's 9 controllers (DDJ-1000 + DDJ-SX3
# add hotcues; XDJ-RX3 + Hercules add filter_fx and tap_tempo). Adding to this
# set is forward-compat — adding a kind here breaks nothing for FLX4.
_VALID_BUTTON_KINDS = frozenset(
    {
        "play",
        "cue",
        "sync",
        "jog_touch",
        "loop_in",
        "loop_out",
        "hotcue",
        "filter_fx",
        "tap_tempo",
    }
)

# CC binding kind — only `cc` Wave 1+2 (no aftertouch / pitch-bend yet).
_VALID_CONTROL_KINDS = frozenset({"cc"})


@dataclass(frozen=True)
class ControlBinding:
    """A single CC-knob/fader binding from a controller profile.

    Frozen — top-level field reassignment raises FrozenInstanceError.
    """

    name: str  # binding key (e.g. 'eq_hi_a')
    kind: str  # always 'cc' for Wave 1+2
    channel: int  # 0..15 MIDI channel
    cc: int  # 0..127 CC number
    axis: str  # 'unipolar' (knob) | 'bipolar' (tempo/filter/xfader, center=64)
    deck: str | None  # 'A'/'B'/'C'/'D' or None for master-section (xfader)
    field: (
        str  # semantic field name: 'vol', 'eq_hi', 'eq_mid', 'eq_low', 'tempo', 'filter', 'xfader'
    )


@dataclass(frozen=True)
class ButtonBinding:
    """A single Note-on/off button binding from a controller profile.

    Frozen — top-level field reassignment raises FrozenInstanceError.
    """

    name: str  # binding key (e.g. 'play_a')
    kind: str  # 'play'/'cue'/'sync'/'jog_touch'/'loop_in'/'loop_out'/...
    channel: int  # 0..15 MIDI channel
    note: int  # 0..127 note number
    deck: str | None  # 'A'/'B'/... or None


@dataclass(frozen=True)
class ControllerProfile:
    """Declarative controller mapping — hand-validated, JSON-backed.

    Frozen at the top level: ``profile.id = 'x'`` raises FrozenInstanceError.
    Inner ``controls`` / ``buttons`` dicts are read-only by convention; do
    NOT mutate them (matches Phase 6 ``GenreProfile.band_signature``).

    Phase 9 Wave 2 additive: ``notes`` (optional, default None). The 9 Wave 2
    profiles ship "verified by JSON only" — Kaan only physically owns the
    DDJ-FLX4 (Wave 1). Phase 16 + 20 + community PRs handle live verification.
    The notes field carries this status string per profile.
    """

    id: str
    display_name: str
    port_name_hints: tuple[str, ...]
    decks: tuple[str, ...]
    controls: dict[str, ControlBinding]
    buttons: dict[str, ButtonBinding]
    notes: str | None = None


def _require_str(payload: dict, key: str, *, profile_name: str | None = None) -> str:
    """Validate a required non-empty string field. Raises ValueError."""
    if key not in payload:
        prefix = f"profile {profile_name}: " if profile_name else "profile: "
        raise ValueError(f"{prefix}field {key!r} is required")
    val = payload[key]
    if not isinstance(val, str) or not val:
        prefix = f"profile {profile_name}: " if profile_name else "profile: "
        raise ValueError(f"{prefix}field {key!r} must be a non-empty str, got {val!r}")
    return val


def _require_int_in_range(
    payload: dict,
    key: str,
    lo: int,
    hi: int,
    *,
    profile_name: str,
    binding_name: str,
) -> int:
    """Validate a required int within [lo..hi] inclusive. Raises ValueError."""
    if key not in payload:
        raise ValueError(
            f"profile {profile_name}: binding {binding_name!r} missing required field {key!r}"
        )
    val = payload[key]
    if not isinstance(val, int) or isinstance(val, bool):
        raise ValueError(
            f"profile {profile_name}: binding {binding_name!r} field {key!r} must be int, "
            f"got {val!r}"
        )
    if val < lo or val > hi:
        raise ValueError(
            f"profile {profile_name}: binding {binding_name!r} field {key!r}={val} "
            f"out of range {lo}..{hi}"
        )
    return val


def _parse_control_binding(
    binding_name: str, payload: dict, *, profile_name: str
) -> ControlBinding:
    """Validate a single control-binding dict. Raises ValueError."""
    if not isinstance(payload, dict):
        raise ValueError(
            f"profile {profile_name}: control binding {binding_name!r} must be a dict, "
            f"got {type(payload).__name__}"
        )
    kind = payload.get("kind")
    if kind not in _VALID_CONTROL_KINDS:
        raise ValueError(
            f"profile {profile_name}: control binding {binding_name!r} field 'kind' must be one of "
            f"{sorted(_VALID_CONTROL_KINDS)}, got {kind!r}"
        )
    channel = _require_int_in_range(
        payload, "channel", 0, 15, profile_name=profile_name, binding_name=binding_name
    )
    cc = _require_int_in_range(
        payload, "cc", 0, 127, profile_name=profile_name, binding_name=binding_name
    )
    axis = payload.get("axis")
    if axis not in _VALID_AXES:
        raise ValueError(
            f"profile {profile_name}: control binding {binding_name!r} field 'axis' must be one of "
            f"{sorted(_VALID_AXES)}, got {axis!r}"
        )
    deck = payload.get("deck", None)
    if deck is not None and (not isinstance(deck, str) or not deck):
        raise ValueError(
            f"profile {profile_name}: control binding {binding_name!r} field 'deck' must be "
            f"a non-empty str or null, got {deck!r}"
        )
    if "field" not in payload:
        raise ValueError(
            f"profile {profile_name}: control binding {binding_name!r} missing required "
            f"field 'field'"
        )
    field_val = payload["field"]
    if not isinstance(field_val, str) or not field_val:
        raise ValueError(
            f"profile {profile_name}: control binding {binding_name!r} field 'field' must be "
            f"a non-empty str, got {field_val!r}"
        )
    return ControlBinding(
        name=binding_name,
        kind=kind,
        channel=channel,
        cc=cc,
        axis=axis,
        deck=deck,
        field=field_val,
    )


def _parse_button_binding(binding_name: str, payload: dict, *, profile_name: str) -> ButtonBinding:
    """Validate a single button-binding dict. Raises ValueError."""
    if not isinstance(payload, dict):
        raise ValueError(
            f"profile {profile_name}: button binding {binding_name!r} must be a dict, "
            f"got {type(payload).__name__}"
        )
    kind = payload.get("kind")
    if kind not in _VALID_BUTTON_KINDS:
        raise ValueError(
            f"profile {profile_name}: button binding {binding_name!r} field 'kind' must be one of "
            f"{sorted(_VALID_BUTTON_KINDS)}, got {kind!r}"
        )
    channel = _require_int_in_range(
        payload, "channel", 0, 15, profile_name=profile_name, binding_name=binding_name
    )
    note = _require_int_in_range(
        payload, "note", 0, 127, profile_name=profile_name, binding_name=binding_name
    )
    deck = payload.get("deck", None)
    if deck is not None and (not isinstance(deck, str) or not deck):
        raise ValueError(
            f"profile {profile_name}: button binding {binding_name!r} field 'deck' must be "
            f"a non-empty str or null, got {deck!r}"
        )
    return ButtonBinding(
        name=binding_name,
        kind=kind,
        channel=channel,
        note=note,
        deck=deck,
    )


def _parse_profile(payload: dict) -> ControllerProfile:
    """Validate a JSON payload, return a frozen ControllerProfile.

    Raises ValueError on any missing or malformed field — silent defaults are
    explicitly prohibited (CONTEXT §Locked).
    """
    if not isinstance(payload, dict):
        raise ValueError(f"profile payload must be a dict, got {type(payload).__name__}")

    # id + display_name first so subsequent errors carry the profile name.
    profile_id = _require_str(payload, "id")
    display_name = _require_str(payload, "display_name", profile_name=profile_id)

    if "port_name_hints" not in payload:
        raise ValueError(f"profile {profile_id}: field 'port_name_hints' is required")
    hints_raw = payload["port_name_hints"]
    if not isinstance(hints_raw, list) or len(hints_raw) == 0:
        raise ValueError(
            f"profile {profile_id}: field 'port_name_hints' must be a non-empty list, "
            f"got {hints_raw!r}"
        )
    for h in hints_raw:
        if not isinstance(h, str) or not h:
            raise ValueError(
                f"profile {profile_id}: every entry in 'port_name_hints' must be a "
                f"non-empty str, got {h!r}"
            )
    port_name_hints = tuple(hints_raw)

    if "decks" not in payload:
        raise ValueError(f"profile {profile_id}: field 'decks' is required")
    decks_raw = payload["decks"]
    if not isinstance(decks_raw, list) or len(decks_raw) == 0:
        raise ValueError(
            f"profile {profile_id}: field 'decks' must be a non-empty list, got {decks_raw!r}"
        )
    for d in decks_raw:
        if not isinstance(d, str) or len(d) != 1:
            raise ValueError(
                f"profile {profile_id}: every entry in 'decks' must be a single-letter "
                f"str, got {d!r}"
            )
    decks = tuple(decks_raw)

    if "controls" not in payload or not isinstance(payload["controls"], dict):
        raise ValueError(f"profile {profile_id}: field 'controls' is required and must be a dict")
    controls: dict[str, ControlBinding] = {}
    for binding_name, binding_payload in payload["controls"].items():
        controls[binding_name] = _parse_control_binding(
            binding_name, binding_payload, profile_name=profile_id
        )

    if "buttons" not in payload or not isinstance(payload["buttons"], dict):
        raise ValueError(f"profile {profile_id}: field 'buttons' is required and must be a dict")
    buttons: dict[str, ButtonBinding] = {}
    for binding_name, binding_payload in payload["buttons"].items():
        buttons[binding_name] = _parse_button_binding(
            binding_name, binding_payload, profile_name=profile_id
        )

    # Optional Wave 2 additive — `notes` carries the unverified-status flag for
    # the 9 Wave 2 profiles. FLX4 (Wave 1) has no notes; loads with notes=None.
    notes_val: str | None = None
    if "notes" in payload:
        raw = payload["notes"]
        if raw is None:
            notes_val = None
        elif isinstance(raw, str):
            notes_val = raw
        else:
            raise ValueError(
                f"profile {profile_id}: field 'notes' must be a str or null, got {raw!r}"
            )

    return ControllerProfile(
        id=profile_id,
        display_name=display_name,
        port_name_hints=port_name_hints,
        decks=decks,
        controls=controls,
        buttons=buttons,
        notes=notes_val,
    )


def list_profiles() -> list[str]:
    """Return sorted list of bundled profile stems (e.g. ['pioneer_ddj_flx4'])."""
    pkg = importlib.resources.files(_PROFILES_PKG)
    names: list[str] = []
    for entry in pkg.iterdir():
        try:
            if not entry.is_file():
                continue
        except Exception:
            continue
        n = entry.name
        if not n.endswith(".json"):
            continue
        names.append(n[: -len(".json")])
    return sorted(names)


def load_profile(name: str) -> ControllerProfile | None:
    """Load a profile by name. Returns None if no JSON file exists.

    Raises ValueError on schema drift in a present file (silent defaults
    explicitly prohibited per CONTEXT §Locked).
    """
    if not isinstance(name, str) or not name:
        return None
    resource = importlib.resources.files(_PROFILES_PKG).joinpath(f"{name}.json")
    try:
        if not resource.is_file():
            return None
    except Exception:
        return None
    with resource.open("rb") as f:
        payload = json.load(f)
    return _parse_profile(payload)
