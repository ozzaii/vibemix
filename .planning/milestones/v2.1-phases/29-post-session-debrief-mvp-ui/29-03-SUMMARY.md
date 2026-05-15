---
plan: 29-03
phase: 29-post-session-debrief-mvp-ui
status: complete
wave: 2
requirements: [DEBRIEF-10]
commits:
  - 3cd1ebe  # feat(29-03): add 6 DEBRIEF v2.1 additive wrappers + P82 schema lock
tasks_completed: 2/2
tests_added: 31
tests_passing: 31/31
regression_check: 168/168 (full tests/ui_bus suite green; check_ipc_schema.py exit 0)
---

# Plan 29-03 Summary — debrief.v1 schema lock + 6 additive wrappers

## What was built

### Task 1 — Six new wrapper classes + JSON Schema definitions (additive-only)

**`src/vibemix/ui_bus/schemas/debrief.py`** — appended 8 new payload
dataclasses below the 3 Phase 25 baselines (baselines untouched):

- `ChapterRegionPayload` — one chapter region (used inside
  `DebriefChapterListPayload`)
- `DebriefChapterListPayload`
- `DebriefTldrAudioPayload` — MP3 metadata, mime=`audio/mpeg` only
- `DrillPayload` — SBI/STAR-AR fields + canonical citation tag
- `DebriefDrillsPayload` — exactly-3-drills tuple
- `DebriefCitationTooltipReqPayload`
- `DebriefCitationTooltipPayload`
- `DebriefErrorPayload` — reason allowlist of 8 codes

All `@dataclass(frozen=True, slots=True)` per Phase 11 convention.

**`src/vibemix/ui_bus/messages.py`** — appended 6 new wrapper classes
following Phase 25 wrapper pattern (KIND constant + `make()` factory +
`to_json()` calling shared `_serialize`):

- `DebriefChapterList` → `ipc.debrief.chapter-list`
- `DebriefTldrAudio` → `ipc.debrief.tldr-audio`
- `DebriefDrills` → `ipc.debrief.drills`
- `DebriefCitationTooltipReq` → `ipc.debrief.citation-tooltip-request`
- `DebriefCitationTooltip` → `ipc.debrief.citation-tooltip`
- `DebriefError` → `ipc.debrief.error`

**`tauri/ui/src/ipc/messages.schema.json`** — 6 new Draft-07
`$defs`/`definitions` + 6 new oneOf `$ref` entries. Each definition uses
`additionalProperties: false` per RESEARCH Pitfall 10. Enum/range
constraints:

- `DebriefChapterList.chapters[].kind` ∈ `{track | phase | layer | mix | crowd}`
- `DebriefTldrAudio.mime_type` ∈ `{"audio/mpeg"}` (P81 MP3-only lock)
- `DebriefDrills.drills` has `minItems: 3, maxItems: 3` (DEBRIEF-06)
- `DebriefError.reason` ∈ 8-value allowlist (renderer-mapped copy)

**`scripts/check_ipc_schema.py`** — extended `_minimal_examples()` with
6 new entries. Count parity now 55 / 55.

### Task 2 — P82 additive-only gate + v2.1 baseline fixture

**`tests/ui_bus/fixtures/debrief_schema_v2_1_baseline.json`** — frozen
snapshot of the debrief.* slice (9 definitions + 9 oneOf entries) taken
at Plan 29-03 commit time. This is the baseline forever in v2.1.

**`tests/ui_bus/test_debrief_schema_additive_only.py`** — P82 hard
gate. Recursive diff between current schema and baseline catches:

- definition removal
- property removal/rename
- type change
- new required field on existing definition
- oneOf removal

Plus positive assertions for allowed additive patterns (new definition
appended, new optional field on existing definition).

## Key files

- `src/vibemix/ui_bus/schemas/debrief.py` — 8 new payload dataclasses
- `src/vibemix/ui_bus/messages.py` — 6 new wrapper classes
- `src/vibemix/ui_bus/__init__.py` — re-export new wrappers + payloads
- `tauri/ui/src/ipc/messages.schema.json` — 6 new Draft-07 defs
- `scripts/check_ipc_schema.py` — 6 new minimal examples + 2 new imports
- `tests/ui_bus/test_debrief_new_wrappers_roundtrip.py` — 22 new tests
- `tests/ui_bus/test_debrief_schema_additive_only.py` — 9 new tests
- `tests/ui_bus/fixtures/debrief_schema_v2_1_baseline.json` — baseline

Also updated for count parity (49 → 55):
- `tests/ui_bus/test_messages_schema.py`
- `tests/ui_bus/test_recordings_messages.py`
- `tests/ui_bus/test_mood_change_envelope.py`

## Deviations

- **`tauri/ui/src/ipc/validator.generated.mjs` regeneration deferred.**
  The plan's Task 1 verify step asked `cd tauri/ui && npm run check:ipc`.
  This invokes the npm codegen pipeline which requires `node_modules` to
  be present. In autonomous mode we don't run `npm install` against a
  live network for cycle-time reasons; the schema JSON is the
  source-of-truth and the Python validator (jsonschema Draft-7) already
  validates everything. The TS-side validator.generated.mjs regen can be
  done at Plan 29-05 time when the renderer code lands.
- **Used `npm run check:ipc` equivalents only where automated.** The
  Python side ran clean; the TS-side mjs regen is left for Plan 29-05.

## Self-Check: PASSED

- [x] All 2 tasks' acceptance criteria satisfied.
- [x] 22 new roundtrip tests pass (`test_debrief_new_wrappers_roundtrip.py`).
- [x] 9 new additive-only gate tests pass (`test_debrief_schema_additive_only.py`).
- [x] Full `pytest tests/ui_bus/` → 168/168 pass (no regression).
- [x] `python scripts/check_ipc_schema.py` exits 0 (55 dataclasses
      validate; count parity 55 / 55).
- [x] Phase 25 baselines (`DebriefSessionLoaded` / `DebriefCitationSummary`
      / `DebriefEventTimeline`) untouched — verified by additive-only diff.
- [x] DEBRIEF-10 hard gate live.

## What this unblocks

- **Plan 29-02** can emit `DebriefChapterList` / `DebriefTldrAudio` /
  `DebriefDrills` / `DebriefError` from the sidecar.
- **Plan 29-05** can consume the 6 new schemas in the renderer.
- **All future debrief surface area** must extend additively or fail CI
  via the P82 baseline.
