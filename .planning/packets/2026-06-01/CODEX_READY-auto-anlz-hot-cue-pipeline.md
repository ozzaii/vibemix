# CODEX_READY: Auto And ANLZ Hot-Cue Pipeline

Date: 2026-06-01
Author: Codex
Status: LAND packet, offline cue provenance slice
Package: Package 4 - Auto And ANLZ Hot-Cue Pipeline

## Decision

LAND this slice as `fix(library-cues): preserve hot cue slots through suggestions`.

The package makes offline structure durable enough for the product surfaces that
depend on it: Rekordbox ANLZ phrase matches and auto-detected cue anchors are
materialized into cached `TrackEntry.cues` only when there are no DJ-authored
structural cues. The cached cues preserve source, confidence, semantic hot-cue
slot, and section provenance, so pill suggestions and Viber/set-prep tools can
use the same grounded cue facts after restart.

This is not a live DDJ/Viber proof packet. It proves the ingest-to-cache-to-pill
and toolset path, with auto-cue uncertainty deliberately downgraded to CARE.

## Files

- `src/vibemix/library/ingest.py`
- `src/vibemix/library/folder_ingest.py`
- `src/vibemix/library/smart_cues.py`
- `src/vibemix/intel/move_grade.py`
- `tests/library/test_ingest.py`
- `tests/library/test_setprep_tools.py`
- `tests/library/test_smart_cues.py`
- `tests/library/test_next_suggestion.py`
- `tests/intel/test_move_grade.py`

Review context, not part of this dirty package:

- `src/vibemix/library/setprep.py`
- `src/vibemix/library/tools.py`
- `src/vibemix/agent/next_suggestion.py`

## What Changed

- `ingest.py` now materializes ANLZ cues into cached track cues when a track has
  no human structural cues.
- `ingest.py` now materializes auto-detected cues when a track has neither DJ
  nor ANLZ structural cues, and folds those auto anchors into the content-hash
  strategy tag.
- Semantic cue labels map to stable Rekordbox A-H slots: intro A, build B,
  breakdown C, drop D/E, outro F; unknown labels use G/H before stealing later
  semantic slots.
- Cue-agreement calibration is opt-in telemetry only. It may compare DJ/ANLZ
  cues with auto cues, but it does not mutate cached track cues, vector keys, or
  exported cue data.
- `smart_cues.py` treats only human-authored cue sources as preserved DJ slots.
  Materialized `auto` and `anlz` cues stay reviewable/generated sources.
- `move_grade.py` makes auto-cue review risks block overconfident labels and
  return a mid/CARE result instead of bomb/sexy/clean.

## Source Evidence

- `src/vibemix/library/ingest.py:94` defines the semantic hot-cue slot map, and
  `src/vibemix/library/ingest.py:101`/`:103` reserve E for a second drop and
  make unknown labels consume G/H before semantic slots.
- `src/vibemix/library/ingest.py:268` materializes matched ANLZ phrases only
  when no structural cues already exist.
- `src/vibemix/library/ingest.py:295` materializes auto cues only when no
  structural cues exist.
- `src/vibemix/library/ingest.py:319` records cue-agreement calibration as
  telemetry and `src/vibemix/library/ingest.py:326` documents that it never
  mutates track/cache/export data.
- `src/vibemix/library/ingest.py:365` builds `CuePoint` records that preserve
  `number`, `source`, and `confidence`.
- `src/vibemix/library/ingest.py:827` applies ANLZ materialization first,
  optional agreement telemetry second, and auto materialization only if the
  working track still lacks structural cues.
- `src/vibemix/library/smart_cues.py:169` reads existing cues, but
  `src/vibemix/library/smart_cues.py:173` skips non-human-authored cues, with
  human sources defined at `src/vibemix/library/smart_cues.py:324`.
- `src/vibemix/library/smart_cues.py:401` maps section roles back to A-H slots
  for smart cue proposals.
- `src/vibemix/intel/move_grade.py:56` marks `auto_cue_review` and cue
  confidence risks as CARE risks; `src/vibemix/intel/move_grade.py:180` through
  `:202` prevent CARE risks from earning bomb/sexy/clean.

## Test Evidence

- `tests/library/test_ingest.py:589` proves auto cues materialize into cached
  library entries and sections, preserving source, confidence, slot A/D, and
  `source_detail="auto_cue"`.
- `tests/library/test_ingest.py:656` proves cue-agreement calibration compares
  DJ cues without replacing them.
- `tests/library/test_ingest.py:705` pins semantic materialized slots as
  `[0, 1, 2, 3, 4, 6, 5]` for intro/build/breakdown/drop/drop/bridge/outro.
- `tests/library/test_next_suggestion.py:197` proves next suggestions preserve
  auto cue provenance and carry `auto_cue_review`, a mid move grade, and
  `deserved=false`.
- `tests/library/test_next_suggestion.py:234` proves a semantic auto DROP cue
  becomes hot cue D in suggestions.
- `tests/library/test_setprep_tools.py:338` proves Viber/MCP
  `get_track_sections` preserves auto slots A/D/F and `source_detail=auto_cue`.

## Verification

Focused Python package tests:

```text
uv run pytest -q tests/library/test_ingest.py tests/library/test_setprep_tools.py tests/library/test_smart_cues.py tests/library/test_next_suggestion.py tests/intel/test_move_grade.py
88 passed in 1.45s
```

Cue-agreement calibration pair:

```text
uv run pytest -q tests/library/test_ingest.py tests/library/test_cue_agreement.py
23 passed in 1.27s
```

Pill UI contract:

```text
npm --prefix tauri/ui test -- src/pill/index.test.ts src/pill/next-suggestion.test.ts
167 passed

npm --prefix tauri/ui run test:e2e:pill
16 passed
```

Lint/whitespace:

```text
uv run ruff check tests/library/test_ingest.py src/vibemix/library/ingest.py src/vibemix/library/folder_ingest.py src/vibemix/library/smart_cues.py src/vibemix/intel/move_grade.py tests/library/test_setprep_tools.py tests/library/test_smart_cues.py tests/library/test_next_suggestion.py tests/intel/test_move_grade.py
All checks passed!

git diff --check -- <Package 4 files>
```

## Boundaries

- No broad staging, no commit, and no product-release claim.
- This package does not claim live DDJ/FLX4 proof or spoken Viber proof.
- This package does not make unreviewed auto cues human-authored. Auto and ANLZ
  materializations remain provenance-tagged generated structure.
- This package does not include unrelated Learn, pricing, or live-context work.
- If Package 4 lands without Packages 5 and 6, product copy must still treat
  auto cues as reviewable and surface uncertainty as CARE.

## Next Required Proof

Before release, run a live DDJ/Viber rehearsal with an ingested library that has
materialized ANLZ or auto cues. The proof should show the same cue source,
confidence, and A-H slot in the cached library, pill suggestion, Viber
`get_track_sections`, and any spoken or displayed explanation.
