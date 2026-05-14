"""MidiMapLoader — schema-validated registry of per-SKU MIDI controller maps.

Replaces hardcoded `_CC_MAP`/`_NOTE_MAP` dicts (cohost_v4.py) with a
JSON-per-SKU file under `src/vibemix/midi/controllers/`. The loader
discovers every file at construction time, validates each against
`schema.json` (Draft-07 via jsonschema), and indexes them for O(1)
event-to-semantic lookup.

Public API:
    loader = MidiMapLoader()                  # auto-discovers controllers/
    cmap = loader.load("ddj-flx4")            # returns dict
    all_maps = loader.all_maps()              # dict[id -> map]
    semantic = loader.lookup(cmap, msg)       # "eq_low_a" or None

`msg` is duck-typed: needs `.type`, `.channel`, plus `.control` (when type
is "control_change") or `.note` (when "note_on" / "note_off"). Note_off
resolves to the same semantic as note_on — semantic events are press, not
press-vs-release. Unsupported msg types and unmapped events return None.

T-23-04 mitigation: any controller JSON that fails schema validation or
JSON parsing raises `MapValidationError` citing the offending filename
during loader construction — the registry never silently swallows bad data.

License: Apache-2.0 (repo).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema


__all__ = [
    "CONTROLLERS_DIR",
    "SCHEMA_PATH",
    "MapValidationError",
    "MidiMapLoader",
]

CONTROLLERS_DIR: Path = Path(__file__).parent / "controllers"
SCHEMA_PATH: Path = Path(__file__).parent / "schema.json"


class MapValidationError(Exception):
    """Raised when a controller JSON fails schema validation or parsing.

    Always includes the offending filename in the message so the operator
    can fix the file directly (T-23-04 mitigation).
    """


class MidiMapLoader:
    """Discovers + validates + indexes per-SKU controller maps."""

    def __init__(self) -> None:
        self._schema: dict = json.loads(SCHEMA_PATH.read_text())
        self._maps: dict[str, dict] = {}
        self._indices: dict[str, dict[tuple[str, int, int], str]] = {}
        self._load_all()

    # -- discovery ----------------------------------------------------------

    def _load_all(self) -> None:
        if not CONTROLLERS_DIR.exists():
            # No controllers/ directory yet — leave registry empty.
            return
        for path in sorted(CONTROLLERS_DIR.glob("*.json")):
            self._load_one(path)

    def _load_one(self, path: Path) -> None:
        try:
            raw = path.read_text()
        except OSError as e:  # pragma: no cover — IO error during read
            raise MapValidationError(
                f"Could not read controller map '{path.name}': {e}"
            ) from e
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            raise MapValidationError(
                f"Invalid JSON in controller map '{path.name}': {e.msg} "
                f"at line {e.lineno} col {e.colno}"
            ) from e
        try:
            jsonschema.validate(data, self._schema)
        except jsonschema.ValidationError as e:
            raise MapValidationError(
                f"Schema validation failed for '{path.name}': {e.message} "
                f"(path: {'/'.join(str(p) for p in e.absolute_path)})"
            ) from e
        controller_id = path.stem
        self._maps[controller_id] = data
        self._indices[controller_id] = self._build_index(data)

    @staticmethod
    def _build_index(cmap: dict) -> dict[tuple[str, int, int], str]:
        """Build a (kind, channel, value) -> semantic lookup index.

        kind is 'cc' or 'note' (note covers both note_on and note_off — semantic
        events are press, not press-vs-release).
        """
        index: dict[tuple[str, int, int], str] = {}
        for control in cmap["controls"].values():
            key = (control["type"], int(control["channel"]), int(control["value"]))
            index[key] = control["semantic"]
        return index

    # -- public API ---------------------------------------------------------

    def all_maps(self) -> dict[str, dict]:
        """Return the full id -> map registry. Copy is shallow — do not mutate."""
        return dict(self._maps)

    def load(self, controller_id: str) -> dict:
        """Return the map for the given controller ID (filename stem).

        Raises KeyError with a discoverable message listing available IDs.
        """
        if controller_id not in self._maps:
            available = ", ".join(sorted(self._maps.keys()))
            raise KeyError(
                f"Unknown controller '{controller_id}'. "
                f"Available: [{available}]"
            )
        return self._maps[controller_id]

    def lookup(self, controller_map: dict, msg: Any) -> str | None:
        """Resolve a mido Message-like object to its semantic event name.

        Returns the semantic string (e.g. 'eq_low_a', 'sync_a') or None if
        the message is unmapped or of an unsupported type.
        """
        msg_type = getattr(msg, "type", None)
        if msg_type == "control_change":
            kind = "cc"
            data1 = getattr(msg, "control", None)
        elif msg_type in ("note_on", "note_off"):
            kind = "note"
            data1 = getattr(msg, "note", None)
        else:
            return None
        if data1 is None:
            return None
        channel = getattr(msg, "channel", None)
        if channel is None:
            return None

        # Resolve controller_id from controller_map by reverse-looking-up.
        # We index by id, but the caller hands us the map dict — find the
        # matching index. For O(1) operation we identify by (vendor, model).
        cid = self._id_for_map(controller_map)
        if cid is None:
            return None
        index = self._indices[cid]
        return index.get((kind, int(channel), int(data1)))

    def _id_for_map(self, controller_map: dict) -> str | None:
        """Find the registry id for a given map dict (identity match by vendor+model)."""
        target = (controller_map.get("vendor"), controller_map.get("model"))
        for cid, m in self._maps.items():
            if (m.get("vendor"), m.get("model")) == target:
                return cid
        return None
