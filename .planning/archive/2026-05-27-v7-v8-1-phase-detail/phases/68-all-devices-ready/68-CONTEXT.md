# Phase 68: All Devices Ready - Context

**Gathered:** 2026-05-23
**Status:** Ready for planning
**Mode:** Auto-generated (autonomous mode — `gsd-autonomous fully`)

<domain>
## Phase Boundary

Bridge engineering-green → third-party-installable for the 10 bundled MIDI controllers. Five deliverables:

1. **Profile contracts** — `tests/midi/test_profile_contracts.py` with 10 GREEN `test_<id>_loads_and_validates` cases (one per bundled profile: FLX4, FLX6, FLX10, 400, 1000, SX3, XDJ-RX3, Party-Mix-Live, Inpulse-300, Inpulse-500), each profile with a synthetic-MIDI smoke that exercises every emitted CC + NOTE through `find_mapping` → `ControllerState` → `MusicState`, plus a non-empty `port_name_hint` field.
2. **Catalog reconciliation** — collapse the duplicated `src/vibemix/midi/controllers/*.json` ↔ `src/vibemix/midi/profiles/*.json` to a single canonical directory with a one-paragraph migration note in `docs/contributing/midi-catalog.md`. A `find ... | uniq -c | awk '$1 > 1'` zero-duplicate check.
3. **Hot-plug matrix** — `tests/integration/test_hotplug_matrix.py` with end-to-end connect → disconnect → reconnect + state-preservation GREEN across ≥3 distinct profiles, exercising the v4.0 P53 `start_port_watcher` + `mark_disconnected` + single-state-callback path without modification.
4. **Audio backend matrix** — `tests/integration/test_audio_backends.py` with mocked CoreAudio + WASAPI coverage of macOS BlackHole 2ch + 16ch + Windows WASAPI loopback + edge no-loopback-driver fallback.
5. **"Add Your Controller" recipe** — `docs/contributing/add-a-controller.md` with bundled template, 4-step contract-test pattern, `scripts/discover_midi_port.py` helper, PR checklist. Smoke discharge: Kaan adds one new profile in <30 min on a controller-of-opportunity (or routes to §V7-LIVE if no controller is available at execution).

**Out of scope:** new reaction-path code (zero `src/vibemix/{coach,llm,memory,recall,decks}/` edits — only `src/vibemix/midi/` catalog reconciliation), new product capabilities, new dependencies, new ws ports, new IPC envelopes. The v7.0 acid test still applies: every plan reads as "verify / wire / discharge / generate / test", never "build a new X".

</domain>

<decisions>
## Implementation Decisions

### Canonical Catalog Directory: `profiles/`
- **Winner:** `src/vibemix/midi/profiles/` — it already houses the 10 success-criterion-mapped JSONs verbatim (FLX4 · FLX6 · FLX10 · 400 · 1000 · SX3 · XDJ-RX3 · Party-Mix-Live · Inpulse-300 · Inpulse-500). Adopting `controllers/` would require renaming all 10.
- **Loser:** `src/vibemix/midi/controllers/` — holds an additional 8 non-bundled controllers (Mixtrack-Pro-FX, Mixtrack-Platinum-FX, Kontrol-S2, Kontrol-S4, MC-6000, MC-7000, DDJ-200, DDJ-Rev1) + 2 overlaps with profiles/ (ddj-400, ddj-flx4).
- **Migration plan:**
  - Move non-overlap controllers → `profiles/` (rename to `<vendor>_<model>.json` schema)
  - For the 2 overlaps (ddj-400 ↔ pioneer_ddj_400 and ddj-flx4 ↔ pioneer_ddj_flx4): keep `profiles/` version; archive controllers/ version under `docs/contributing/legacy-controllers/` ONLY IF the file contents differ meaningfully (otherwise delete)
  - Delete `src/vibemix/midi/controllers/` directory entirely after migration
  - Update `map_loader.py` and `generic.py` (which currently reference `controllers/`) to use `profiles/`
- **Note:** the "10 bundled" still means the 10 in the success-criterion list — non-overlap controllers from the old `controllers/` directory ride along as "additional supported" but are NOT in the contract-test set (their contract tests can be added later if Kaan wants).

### Profile JSON Schema
- Use the existing `src/vibemix/midi/schema.json` as canonical. Extend if missing `port_name_hint` field; otherwise leave alone.
- Every `profiles/*.json` file MUST validate against `schema.json` via `jsonschema` (likely already a dep transitively — verify before adding).
- Required fields: `id`, `vendor`, `model`, `port_name_hint` (NEW — string OR array of strings, non-empty), `cc_mappings`, `note_mappings`.

### Contract Test Shape (per profile)
- `tests/midi/test_profile_contracts.py` — parametrized `test_<id>_loads_and_validates` over the 10 bundled profile IDs.
- Each test: loads JSON via `map_loader`, validates against `schema.json`, asserts non-empty `port_name_hint`, asserts every `cc`/`note` is referenced exactly once (no duplicate mappings).

### Synthetic-MIDI Smoke (per profile)
- `tests/midi/test_profile_smokes.py` — generate a synthetic `mido.Message` for every CC + NOTE in the profile, push through `find_mapping` → `ControllerState.apply` → `MusicState.update`, assert no exceptions + every mapping fires its expected handler.
- Use existing `mock` patterns; no real device required.

### Hot-Plug Matrix
- `tests/integration/test_hotplug_matrix.py` marked `@pytest.mark.integration`.
- 3 profiles chosen: FLX4 (Kaan's hardware), 400 (most-shipped DJ controller), Inpulse-500 (different vendor).
- For each: simulate `port_watcher` signaling disconnect → wait 100ms → signal reconnect with same port name → assert `ControllerState` state preserved across reconnect (last-known knob/fader values intact, no spurious re-init events).
- Live FLX4 plug/unplug → `KAAN-ACTION-LEGAL.md §V7-LIVE-NN` (one entry: "live FLX4 hot-plug ear pass").

### Audio Backend Matrix
- `tests/integration/test_audio_backends.py` marked `@pytest.mark.integration`.
- Mocked surfaces:
  - macOS: mock `sounddevice` to report a BlackHole 2ch device, then a BlackHole 16ch device — assert input/output stream opens at correct sample rate (48kHz).
  - Windows: mock WASAPI loopback enumeration — assert the loopback device is found and opens.
  - Edge: mock "no loopback driver available" — assert graceful fallback (the existing `_HAS_LOOPBACK` guard fires correctly with a clear log line).
- Real BlackHole + real WASAPI live capture → `§V7-LIVE-NN` (one entry per OS: §V7-LIVE-08 macOS BlackHole live, §V7-LIVE-09 Windows WASAPI live).

### Contributor Recipe
- `docs/contributing/add-a-controller.md` ≤ 200 lines:
  - Step 1: Use `scripts/discover_midi_port.py` to identify the controller's port name on macOS + Windows.
  - Step 2: Copy `src/vibemix/midi/profiles/_template.json` (NEW — clean template) → `<vendor>_<model>.json`, fill in `id` / `vendor` / `model` / `port_name_hint` / `cc_mappings` / `note_mappings`.
  - Step 3: Add `your-controller-id` to the parametrize list in `tests/midi/test_profile_contracts.py` AND `tests/midi/test_profile_smokes.py`.
  - Step 4: `uv run pytest tests/midi/ -q` → green; submit a PR including: the JSON, the parametrize updates, and one paragraph in the PR body describing your testing setup.
- `scripts/discover_midi_port.py` — uses `mido.get_input_names()` to print attached MIDI port names (≤ 30 lines).

### Smoke Discharge (Kaan / DJ ear)
- Engineering-side: the recipe + template + helper land. The <30-min smoke is **the discharge** — under `gsd-autonomous fully`, route to `KAAN-ACTION-LEGAL.md §V7-LIVE-07 — controller-recipe smoke` as a Kaan-ear item. The phase ships engineering-complete without waiting on the live smoke.
- If a DJ friend in Kaan's network can be reached during execution, the smoke discharge can complete immediately; otherwise it rides forward.

### Claude's Discretion
- File names for the new test files (`test_profile_contracts.py` vs `test_profile_validation.py` — pick `test_profile_contracts.py` per goal text).
- Exact synthetic-MIDI fixture shape — pick one and stay consistent.
- Schema-validator library choice — prefer stdlib `jsonschema` if already in `uv.lock`; otherwise raw `json.load` + manual asserts.
- Whether to ship `_template.json` inside `profiles/` (as `_template.json` — the leading underscore excludes it from glob loaders) or under `docs/contributing/` as a copy-target. Pick whichever feels cleaner during planning.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/vibemix/midi/` package — already structured. `__init__.py` + `registry.py` + `profile.py` + `state.py` + `map_loader.py` + `generic.py` + `watcher.py` + `schema.json`.
- `src/vibemix/midi/profiles/*.json` — 10 files matching the success-criterion list exactly.
- v4.0 P53 closed: `start_port_watcher` + `mark_disconnected` + single-state-callback path (in `watcher.py`).
- `mido` + `python-rtmidi` already deps.
- Existing tests under `tests/` use `pytest` + parametrize patterns.

### Established Patterns
- JSON profile files use `snake_case` field names.
- Test files under `tests/<module>/` named `test_<feature>.py`; parametrize via `@pytest.mark.parametrize("profile_id", [...])`.
- `@pytest.mark.integration` for multi-component tests (registered in `pyproject.toml`).
- Mocked CoreAudio/WASAPI via `unittest.mock.patch` (no real `sounddevice` import in test surface).

### Integration Points
- `src/vibemix/midi/profiles/` — canonical catalog (target state).
- `src/vibemix/midi/controllers/` — to be migrated + deleted.
- `src/vibemix/midi/map_loader.py` — currently references `controllers/`; update to `profiles/`.
- `src/vibemix/midi/generic.py` — same.
- `tests/midi/` — new test files.
- `tests/integration/` — new integration tests.
- `scripts/discover_midi_port.py` — new helper.
- `docs/contributing/add-a-controller.md` — new.
- `docs/contributing/midi-catalog.md` — new (migration note).
- `KAAN-ACTION-LEGAL.md` — extend §V7-LIVE with -07 (controller-recipe smoke), -08 (macOS BlackHole live), -09 (Windows WASAPI live), -10 (live FLX4 hot-plug ear).

</code_context>

<specifics>
## Specific Ideas

- The 10 bundled controllers are exactly the 10 already in `src/vibemix/midi/profiles/`. Don't second-guess the bundle.
- v4.0 P53 hot-plug code is the load-bearing path — DO NOT modify it; test it.
- Schema validation already has `src/vibemix/midi/schema.json` as canonical — extend with `port_name_hint` if absent, don't rewrite.
- Kaan owns one Pioneer DDJ-FLX4 — that's the live-ear hardware. The other 9 are mocked + JSON-validated only.

</specifics>

<deferred>
## Deferred Ideas

- Add contract tests for the 8 non-bundled controllers (Mixtrack, Kontrol, MC-7000, etc.) — defer to a future polish phase.
- Live audio capture parity tests (real BlackHole + real WASAPI) — §V7-LIVE-08/09 Kaan-clock items.
- Controller-specific feature flags (e.g., XDJ-RX3's screen output) — defer.
- Multi-controller simultaneous mode (FLX4 + Inpulse-500 plugged in at once) — defer.

</deferred>
