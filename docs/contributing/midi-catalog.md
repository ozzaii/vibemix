# MIDI controller catalog — migration note

**Filed:** 2026-05-23 (Phase 68 Wave 0 / Plan 68P01)
**REQ-ID:** DEV-02

This is a short migration note explaining a one-time directory consolidation in `src/vibemix/midi/`. Read it once if you are wondering "why are there git deletions of `src/vibemix/midi/controllers/` and `map_loader.py` in the v7.0 history?"; otherwise it is reference material.

## What changed

Until v7.0 Phase 68, `src/vibemix/midi/` carried **two parallel controller-mapping catalogs** with **incompatible schemas**:

| Catalog                          | Loader                               | Live-runtime status |
| -------------------------------- | ------------------------------------ | ------------------- |
| `src/vibemix/midi/controllers/`  | `map_loader.py::MidiMapLoader`       | **orphan** — no live consumer (only its own tests imported it) |
| `src/vibemix/midi/profiles/`     | `profile.py::load_profile`           | **canonical** — what the listener + `ControllerState` decode through |

Phase 68 deleted the orphan side and updated every cross-repo reference to point at `profiles/` only.

**Deleted in this migration (full list — git history preserves the bytes):**

- `src/vibemix/midi/controllers/` (entire directory, 10 JSONs):
  `ddj-200.json`, `ddj-400.json`, `ddj-flx4.json`, `ddj-rev1.json`, `kontrol-s2.json`, `kontrol-s4.json`, `mc-6000.json`, `mc-7000.json`, `mixtrack-platinum-fx.json`, `mixtrack-pro-fx.json`
- `src/vibemix/midi/map_loader.py` (the `MidiMapLoader` registry — no live importer)
- `src/vibemix/midi/schema.json` (Draft-07 jsonschema doc validating the deleted `controllers/` shape only)
- `tests/midi/test_map_loader.py` (unit tests for the deleted module)
- `tests/midi/test_live_binding_profiles_canonical.py` (anti-drift gate that becomes vacuous once its targets are gone)

## Why `profiles/` won

- It is **already canonical at runtime** — the live `ControllerState` is built from `load_profile(...)`; the hot-plug watcher resolves ports via `find_mapping` / `find_mapping_or_generic`; the listener binds + decodes through `ControllerProfile` loaded from this directory. Pinned by `tests/midi/test_live_binding_profiles_canonical.py` (now deleted because the pin is structural rather than test-enforced).
- Its 10 bundled JSONs match the v7.0 Phase 68 success-criterion set verbatim (FLX4 · FLX6 · FLX10 · DDJ-400 · DDJ-1000 · SX3 · XDJ-RX3 · Numark Party Mix Live · Hercules Inpulse 300 · Hercules Inpulse 500).
- Validation is a hand-rolled `profile.py::_parse_profile` — consistent with the project-wide ban on pydantic (Phase 6), no jsonschema on the live decode path.

## Why DELETE-AND-UPDATE-REFERENCES rather than MERGE

The two catalogs encode **different ontologies**, not different IDs of the same shape:

```jsonc
// LEGACY controllers/ddj-flx4.json shape — flat cc+note mixed dict
{
  "vendor": "Pioneer", "model": "DDJ-FLX4",
  "description": "...", "verified": true,
  "controls": {
    "vol_a": {"type": "cc", "channel": 0, "value": 19, "semantic": "vol_a", "status": "verified"}
  }
}

// CANONICAL profiles/pioneer_ddj_flx4.json shape — typed kind/axis/field with deck binding
{
  "id": "pioneer_ddj_flx4", "display_name": "Pioneer DDJ-FLX4",
  "port_name_hints": ["DDJ-FLX4", "FLX4"],
  "decks": ["A", "B"],
  "controls": {
    "vol_a": {"kind": "cc", "channel": 0, "cc": 19, "axis": "unipolar", "deck": "A", "field": "vol"}
  },
  "buttons": { /* separated note-message bindings */ }
}
```

There is **nothing to port in.** The legacy shape's `semantic` + `status` + `verified` fields map to nothing in `ControllerProfile`; the profiles' `kind` / `axis` / `field` / `deck` / `port_name_hints` / `decks` fields didn't exist on the legacy side. A field-by-field merge would produce a Frankenstein with neither catalog's invariants. The deletion is the merge.

## For contributors adding controllers

The "add your controller" recipe with template JSON + `scripts/discover_midi_port.py` + 4-step PR checklist lands in Phase 68 Wave 3 at `docs/contributing/add-a-controller.md`. Until that ships, copy `src/vibemix/midi/profiles/pioneer_ddj_flx4.json` as a starting shape; add the new ID to the parametrize list in `tests/midi/test_profiles_all_controllers.py`; run `uv run pytest tests/midi/ -q` and submit a PR with DCO sign-off.

## Git archaeology

The 10 deleted controller JSONs survive in git history. To recover or audit them:

```bash
# Find the deletion commit (this migration):
git log --diff-filter=D -- src/vibemix/midi/controllers/

# Show one of the deleted files at the SHA just before the deletion:
git show <SHA>^:src/vibemix/midi/controllers/ddj-flx4.json
```

Same for `map_loader.py` and `schema.json` — both deleted in the same atomic commit and recoverable the same way.
