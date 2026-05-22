---
phase: 65-memory-retrieval-seam
plan: 03
subsystem: memory
tags: [retrieval, recall, grounding, sqlite-vec, gemini-embedding, anti-slop]

# Dependency graph
requires:
  - phase: 63-memory-store
    provides: "MemoryStore.query_topk(query_embedding, k, *, exclude_session=None) + Record dataclass"
  - phase: 64-session-ingest
    provides: "coach_line signature template (build_coach_line_signature prefix) for query↔stored embedding symmetry"
  - phase: 65-memory-retrieval-seam (Plan 01)
    provides: "RED-first tests/memory/test_retrieval.py contract (the 5 MemoryRecall behaviors)"
provides:
  - "MemoryRecall enrichment service — event-gated, similarity-floored, current-session-excluded recall seam (a Grounding clone over MemoryStore)"
  - "RECALL_SIMILARITY_FLOOR=0.7, RECALL_TOP_K=3, RECALL_DEADLINE_S=0.5, RECALL_EVENT_GATE constants (the shared retrieval-policy defaults)"
  - "build_recall_query(ev) — the coach_line context-prefix builder for query embeddings"
affects: [65-04, 66-visible-copilot-move]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Grounding-clone enrichment service: lock-guarded _latest, on_event/get_latest/clear, off-loop friendly, never writes MusicState"
    - "Structural anti-poisoning: cosine floor (drop below 0.7) + current-session exclusion + event gate before embed"
    - "Mirror-not-import: copy CITATION_THRESHOLD value with a citation comment to avoid memory→library coupling"

key-files:
  created:
    - src/vibemix/memory/retrieval.py
  modified: []

key-decisions:
  - "Cosine-only v1 — no time-decay/half-life blend (DEFERRED to KAAN-ACTION Kaan-ear pass)"
  - "RECALL_EVENT_GATE is NARROWER than Grounding's TRACK_AWARE_EVENTS: {TRACK_CHANGE, PHASE, LAYER_ARRIVAL} — excludes MIX_MOVE, never HEARTBEAT"
  - "RECALL_SIMILARITY_FLOOR copied (not imported) from library/grounding.py:39 — avoids a memory→library coupling"
  - "build_recall_query reads ev.state/ev.type via getattr (duck-typed) so the module never imports MusicState (no-live-path invariant)"

patterns-established:
  - "MemoryRecall: the off-hot-path retrieval seam. Plan 65-04 runs on_event off-loop via asyncio.wait_for(..., RECALL_DEADLINE_S) and clears on a deadline miss."

requirements-completed: [RECALL-03, RECALL-04]

# Metrics
duration: 14min
completed: 2026-05-22
---

# Phase 65 Plan 03: Memory Retrieval Seam (MemoryRecall service) Summary

**`MemoryRecall` — an event-gated, 0.7-cosine-floored, current-session-excluded recall service cloned from `library/grounding.py::Grounding`, pointed at `MemoryStore` with a single FLEX `embed_query` per track-aware event and zero live-path coupling.**

## Performance

- **Duration:** ~14 min
- **Started:** 2026-05-22
- **Completed:** 2026-05-22
- **Tasks:** 1 (TDD GREEN — RED contract pre-existed from Plan 65-01)
- **Files modified:** 1 created

## Accomplishments
- `src/vibemix/memory/retrieval.py` — the `MemoryRecall` enrichment service: lock-guarded `_latest`, `on_event`/`get_latest`/`clear`, gated to track-aware events, similarity-floored, current-session-excluded; never writes `MusicState`, opens no socket, imports no live-reaction-path module.
- The structural anti-poisoning trio (RECALL-03): below-floor survivors → `[]`; current session excluded via `query_topk(..., exclude_session=current_session_id)`; (the PAST-tense fence is 65-04's coach.py block, not here).
- The off-path/budget controls (RECALL-04): event gate short-circuits BEFORE any embed (HEARTBEAT never embeds), exactly one FLEX `embed_query` per gated event, cosine-only (no time-decay), conservative `RECALL_TOP_K=3`.
- All 5 `tests/memory/test_retrieval.py` tests flipped GREEN; the shipped no-live-path + no-extraction static gates and the model-literal gate stay CLEAN over the new file.

## Task Commits

1. **Task 1: MemoryRecall service + constants + build_recall_query** - `10bcaf0` (feat)

_TDD: the RED contract (`tests/memory/test_retrieval.py`) shipped in Plan 65-01; this plan is the single GREEN commit (no new test commit needed — the test file already existed)._

**Plan metadata:** (this commit — docs)

## Files Created/Modified
- `src/vibemix/memory/retrieval.py` - `MemoryRecall` service + `build_recall_query` + `RECALL_*` constants; ~160 lines (incl. docstrings); a Grounding clone over `MemoryStore`.

## Decisions Made
- **Cosine-only v1, no time-decay blend.** The cosine-vs-time blend / half-life / exact-floor tuning is DEFERRED to the Kaan-ear pass (KAAN-ACTION), per plan. `grep -nE 'decay|half_life|exp\('` finds only docstring/comment prose stating the absence.
- **`RECALL_SIMILARITY_FLOOR = 0.7` copied, not imported.** Mirrors `library/grounding.py:39 CITATION_THRESHOLD` with a citation comment — avoids a `memory→library` coupling (the no-live-path spine stays a leaf).
- **Event gate narrower than Grounding's.** `{TRACK_CHANGE, PHASE, LAYER_ARRIVAL}` (excludes `MIX_MOVE`, never `HEARTBEAT`) — track-aware-only, per the RESEARCH §Open-Q1 trio. Confirmed against the live event taxonomy in `src/vibemix/state/event.py`.
- **`build_recall_query` is duck-typed.** Reads `ev.state`/`ev.type` via `getattr` so the module never imports `MusicState` — keeps the no-live-path static gate clean. Builds the Phase-64 `coach_line` context prefix (`track`/`phase`/`deck`/`event`) and omits `cite=`/`said:` for query↔stored embedding symmetry.

## Deviations from Plan

None - plan executed exactly as written. The RED tests pre-existed (Plan 65-01); this was a clean single-commit GREEN with no auto-fixes required.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Verification

- `tests/memory/test_retrieval.py` — 5/5 GREEN (heartbeat_never_retrieves, below_floor_injects_nothing, current_session_excluded, deadline_miss_injects_nothing, embed_called_once).
- `tests/memory/test_no_live_path_import.py` + `tests/memory/test_no_extraction.py` — CLEAN with `retrieval.py` in scope (static AST + tokenize-stripped scans see the new file).
- `tests/repo/test_model_literal_gate.py` — green (no model literal in `retrieval.py`).
- `grep -nE 'MusicState|ws_bus|coach_loop|websockets|from vibemix.agent|generate'` and `grep -nE 'decay|half_life|exp\('` over `retrieval.py` — only docstring/comment prose (the tokenize-stripped static gates prove no real-code violations).
- Full suite: **4130 passed, 11 failed, 26 skipped**. The 11 failures are the documented pre-existing 8-WIP baseline (release-cut / README feature-matrix / gate-42 / orphan-inventory / main-smoke — none reference `memory/`) **+ the 3 still-RED 65-04 wiring contracts** (`test_coach.py::test_evidence_line_recall_block_present`, `test_coach.py::test_evidence_line_recall_empty_no_block`, `test_main_anti_slop_wiring.py::test_wire13_anti_slop_disabled_path_passes_none_kwargs`). **No new failures introduced by this plan.**

## Next Phase Readiness
- The retrieval service is complete and exposes the exact callable Plan 65-04 needs: `MemoryRecall.on_event(event_type, query_text, current_session_id)` (run off-loop via `asyncio.wait_for(..., RECALL_DEADLINE_S)`), `get_latest()` (prompt-builder pull), `clear()` (per-turn / deadline-miss reset), `build_recall_query(ev)`, and the `RECALL_*` constants.
- 65-04 wires: the gated `recall[…]` block in `coach.py::evidence_line` (copy the Phase-59 `decks[…]` gate → cold-memory byte-identical), the off-loop pre-dispatch + deadline, survivor registration, and `clear()` — behind `recall_enabled`. The 3 still-RED 65-04 tests turn GREEN there.

## Self-Check: PASSED
- `src/vibemix/memory/retrieval.py` — FOUND.
- Commit `10bcaf0` — FOUND in `git log`.

---
*Phase: 65-memory-retrieval-seam*
*Completed: 2026-05-22*
