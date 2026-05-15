---
plan: 29-07
phase: 29-post-session-debrief-mvp-ui
status: complete
wave: 4
requirements: [DEBRIEF-07]
commits:
  - <T1+T2>  # feat(29-07): DEBRIEF-07 hard gate e2e + TS-side stripper defense-in-depth
tasks_completed: 2/2
tests_added: 18  # 8 Python + 10 TS
tests_passing: 18/18 (full debrief suite 84/84)
regression_check: pytest tests/debrief/ → 84/84
---

# Plan 29-07 Summary — DEBRIEF-07 hard gate (e2e) + TS stripper

## What was built

### Task 1 — server-side strict per-field gate + e2e hard gate

**`src/vibemix/debrief/drills.py`** — `generate_drills` now ALSO checks
that every drill's `behavior` / `impact` / `action_recommended` text
contains ≥ 1 EVIDENCE_CITATION_RE match (in addition to the canonical
`citation` field resolving against the snapshot). Drills failing any of
those gates are retried; persistent failures surface as
`DrillsGenerationError(reason="drills_generation_failed")`.

**Tests:**

- `tests/debrief/test_stripper_integration_with_tldr.py` (3):
  - 6-sentence input (3 cited + 3 uncited) → 3 cited preserved
  - 0-cited Gemini output → typed `DebriefGenerationError`
  - logger captured `[debrief] stripped uncited` on each drop
- `tests/debrief/test_stripper_integration_with_drills.py` (3):
  - drill with uncited behavior → retry → all-good on attempt 2
  - all-good drills pass on first call
  - persistent bad drills → `DrillsGenerationError` after retries
- `tests/debrief/test_no_uncited_critique_in_debrief_e2e.py` (2):
  - **THE HARD GATE**: full `run(session_dir)` → persisted
    `session_debrief.json` has every advice sentence cited
  - bad-citation-only path raises typed error + writes no partial
    artifacts on disk

### Task 2 — renderer-side defense-in-depth (TS stripper)

**`tauri/ui/src/debrief/stripper-roundtrip.ts`** (new):

- `EVIDENCE_CITATION_RE` (port of Phase 18 regex to TS RegExp).
- `stripUncitedSentences(text): { text, strippedCount }`.
- `stripDrillFields(drill)`: applies stripper to all 3 advice fields;
  falls back to original text when strip produces empty (still shown
  to user but the renderer ErrorBanner flags via ws-client — wired in
  Plan 29-05).

**Tests:** `tauri/ui/src/debrief/__tests__/stripper-roundtrip.spec.ts`
— 10 vitest assertions covering:
- cited / uncited keep-vs-drop
- empty input → `{ text: '', strippedCount: 0 }`
- all 7 EBNF sources pass
- 0-cited input → fully stripped
- `!` / `?` sentence boundaries
- `stripDrillFields` 3-field independence
- regex rejects whitespace inside brackets + empty brackets
- multi-citation comma form accepted

## Key files

- `src/vibemix/debrief/drills.py` — per-field gate added
- `tests/debrief/test_stripper_integration_with_tldr.py` (new)
- `tests/debrief/test_stripper_integration_with_drills.py` (new)
- `tests/debrief/test_no_uncited_critique_in_debrief_e2e.py` (new — THE GATE)
- `tauri/ui/src/debrief/stripper-roundtrip.ts` (new)
- `tauri/ui/src/debrief/__tests__/stripper-roundtrip.spec.ts` (new)

## Deviations

- **`ws-client.ts` integration deferred to Plan 29-05.** The plan's
  Task 2 also asked the renderer's ws-client to apply the stripper to
  every inbound drills frame and surface an ErrorBanner warning. The
  ws-client file is created in Plan 29-05; Plan 29-07 ships the
  building-block module + vitest spec ready to import.
- **Plan 29-01's main.py orchestrator already did the final stripper
  sweep before write_debrief.** No new orchestrator edits needed for
  Plan 29-07 because the defense-in-depth was correctly anticipated in
  Plan 29-01 Task 2's `_serialize` / `write_debrief` step.

## Self-Check: PASSED

- [x] DEBRIEF-07 hard gate (`test_no_uncited_critique_in_debrief_e2e`)
      passes end-to-end.
- [x] 18 new tests (8 Python + 10 TS), all green.
- [x] Full debrief suite: 84/84.
- [x] TS regex parity verified against Python `EVIDENCE_CITATION_RE`.
- [x] Server-side + renderer-side both have stripper — two filters.

## What this unblocks

- **Plan 29-05** can import `stripUncitedSentences` / `stripDrillFields`
  in its `ws-client.ts` for the final defense layer before mounting the
  components.
- **Plan 29-08** e2e smoke includes a synthetic-uncited Gemini mock to
  verify the gate never lets bad data through in real-time UI render.
