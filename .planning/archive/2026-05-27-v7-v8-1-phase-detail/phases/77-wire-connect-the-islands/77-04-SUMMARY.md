---
phase: 77-wire-connect-the-islands
plan: 04
subsystem: agent
tags: [wire, grounding, citation, memory-ingest, off-loop-dispatch, recall-seam, additive-gated]

requires:
  - phase: 77-01
    provides: "tests/agent/test_dj_cohost_grounding.py + tests/memory/test_ingest_wiring.py xfail-strict scaffolds (the Wave-0 RED tiers this plan turns GREEN)"
  - phase: 77-03
    provides: "WIRE-06 env-key override (the funded .env key the live grounding embed would use)"
provides:
  - "WIRE-01: DJCoHostAgent grounding 4-point seam (kwarg + _maybe_dispatch_grounding off-loop + llm_node [track:<id>] injection + turn-end clear)"
  - "WIRE-01 wiring: attach_grounding() setter + main() attaches the armed Grounding engine post-construction"
  - "WIRE-05: gated _session_ipc._fire_ingest boot+close on the live main() path (no double retention)"
affects: [78-perceive, 79-lens, 80-ground, 81-bench, 82-curate]

tech-stack:
  added: []
  patterns:
    - "Mirror the Phase-65 MemoryRecall pre-dispatch seam for a second off-loop service (Grounding) — kwarg gate + run_in_executor + wait_for(deadline) + cancel/replace + turn-end clear"
    - "Post-construction attach_grounding() setter to wire a dependency built AFTER the consumer (deck_library ordering), keeping the cold path byte-identical"
    - "Reuse the already-built _session_ipc SessionLoop handle for ingest-only _fire_ingest (never the combined sweep methods → no double retention)"

key-files:
  created: []
  modified:
    - src/vibemix/agent/dj_cohost.py
    - src/vibemix/__main__.py
    - tests/agent/test_dj_cohost_grounding.py
    - tests/memory/test_ingest_wiring.py

key-decisions:
  - "WIRE-01 wiring approach = attach_grounding() SETTER (not build-reorder): grounding's build depends on deck_library, which is resolved AFTER the agent build in main(); reordering would churn ~30 lines + move suggestion_service wiring. The setter is the smaller, additive diff (grounding=None cold path byte-identical either way)."
  - "Grounding off-loop deadline reuses memory.retrieval.RECALL_DEADLINE_S (both are off-hot-path Gemini embeds with the same TTFT budget) with a 2.0s defensive fallback if the memory module is unavailable in a stripped build."
  - "Audio source for the grounding embed = the SAME self._clean_audio_buf WAV snapshot llm_node feeds Gemini (snapshot taken synchronously in _maybe_dispatch_grounding, bytes handed to the executor) — no second capture path (A3)."
  - "Close-path _fire_ingest is await-ed directly (the finally block is inside async def main(), so await is valid); boot-path uses asyncio.create_task (fire-and-forget at the boot site)."
  - "_session_ipc initialized to None BEFORE the wiring try so it is always bound in the finally close-ingest call; reset to None on the except path; both ingest sites guard `is not None`."

patterns-established:
  - "Two off-loop enrichment services (recall + grounding) now share the same pre-dispatch shape in set_next_event; future track-aware consults follow the same gate."

requirements-completed: [WIRE-01, WIRE-05]

duration: ~12min
completed: 2026-05-26
---

# Phase 77 Plan 04: WIRE-01 grounding→agent + WIRE-05 live-path memory ingest Summary

**The live co-host now grounds reactions on what's actually playing — the armed Grounding engine is wired into DJCoHostAgent via the proven Phase-65 4-point off-loop seam ([track:<id>] injection resolves against register_library, cold path byte-identical) — and memory.db finally fills on the live main() path via gated _fire_ingest boot+close, without doubling retention.**

## Performance

- **Duration:** ~12 min
- **Completed:** 2026-05-26
- **Tasks:** 2 (both `tdd="true"`, scaffolds pre-existed from Plan 77-01 — un-xfailed as each beat landed)
- **Files modified:** 4 (2 src, 2 test)

## Accomplishments

- **WIRE-01 — grounding 4-point seam** in `agent/dj_cohost.py`, mirroring `_maybe_dispatch_recall` exactly:
  1. Constructor gains `grounding: "Grounding | None" = None` (cold-path gate — `grounding is None`); stored `self._grounding` + `self._grounding_task`.
  2. `_maybe_dispatch_grounding(ev)` — called from `set_next_event` alongside the recall dispatch; gates on `grounding is not None` + `ev.type in TRACK_AWARE_EVENTS` (imported lazily from `vibemix.library.grounding`) + a running loop; snapshots `self._clean_audio_buf` to WAV bytes and hands `grounding.on_event` to `loop.run_in_executor` inside `asyncio.wait_for(RECALL_DEADLINE_S)`; cancel+replace prior in-flight task; clear-on-timeout/exception.
  3. `llm_node` pulls `self._grounding.get_latest_citation()` after `text_prompt` is built and, when `cit.is_cited`, appends ` [track:{cit.track_id}]` — resolves in `EvidenceRegistry` via the already-seeded `register_library` ids (invariant #2, NO linter change). Strictly read-only (never writes MusicState — invariant #1).
  4. Turn-end `self._grounding.clear()` alongside the recall clear.
- **WIRE-01 wiring** — `attach_grounding()` setter on the agent; `main()` constructs the agent with `grounding=None`, then calls `agent.attach_grounding(grounding)` after the engine is armed (it depends on `deck_library`, resolved after the agent build).
- **WIRE-05 — live-path memory ingest** — `main()` fires `_session_ipc._fire_ingest("boot")` at boot (after `register_handlers()`) and `await _session_ipc._fire_ingest("close", session_dir=recorder.session_dir)` in the async `finally` (after `recorder.close()`), both gated on `recall_enabled` (default OFF → additive no-op) and guarded `_session_ipc is not None`. Uses `_fire_ingest` ONLY — never the combined boot-sweep / session-close methods — so the boot/close retention sweeps `main()` already runs are not doubled.
- Flipped all 5 Wave-0 xfail-strict scaffolds (3 WIRE-01 + 2 WIRE-05) to real passes; full suite green offline (no API key).

## Task Commits

1. **Task 1: WIRE-01 4-point grounding seam in dj_cohost** — `e020a91` (feat) — un-xfailed the 3 WIRE-01 tiers; `test_dj_cohost.py` golden green unchanged.
2. **Task 2: grounding wired into agent + gated _fire_ingest on live path** — `5ac3a9d` (feat) — attach_grounding setter + main() wiring + WIRE-05 boot/close ingest; un-xfailed the 2 WIRE-05 main()-path tiers.

## Files Created/Modified

- `src/vibemix/agent/dj_cohost.py` — grounding kwarg + `self._grounding`/`self._grounding_task`; `attach_grounding()` setter; `_maybe_dispatch_grounding()` off-loop dispatcher; `llm_node` `[track:<id>]` pull/inject; turn-end clear; `Grounding` added to the TYPE_CHECKING block.
- `src/vibemix/__main__.py` — `agent.attach_grounding(grounding)` after the grounding build; `_session_ipc = None` pre-init; gated `_fire_ingest("boot")` after `register_handlers()`; gated `await _fire_ingest("close", session_dir=...)` in the finally after `recorder.close()`.
- `tests/agent/test_dj_cohost_grounding.py` — removed 3 `xfail(strict)` markers (source-text off-loop gate, off-loop dispatch behavioural).
- `tests/memory/test_ingest_wiring.py` — removed 2 `xfail(strict)` markers (main()-path boot+close fire, recall_enabled gate).

## Decisions Made

See frontmatter `key-decisions`. Headline: the WIRE-01 wiring uses the **attach_grounding() setter** rather than reordering the grounding build above the agent, because the grounding build depends on `deck_library` (resolved after the agent) — the setter is the smaller additive diff and preserves the byte-identical cold path. The close-path `_fire_ingest` is correctly `await`-ed (the `finally` lives inside `async def main()`); the boot-path uses `asyncio.create_task` at the boot site.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Reworded two source comments to avoid tripping the anti-double-retention source-text gate**
- **Found during:** Task 2 (WIRE-05 ingest wiring)
- **Issue:** My explanatory comments literally contained `run_boot_sweeps(` and `on_session_close(`, which `test_main_does_not_call_combined_retention_methods` greps for as a forbidden-call substring — the test failed on the comment text even though no such call exists.
- **Fix:** Reworded the comments to "the combined boot-sweep method" / "the combined session-close method" (no parenthesized token); the actual calls remain `_fire_ingest` only.
- **Files modified:** src/vibemix/__main__.py
- **Verification:** `test_main_does_not_call_combined_retention_methods` green; `grep -c "run_boot_sweeps(" / "on_session_close("` = 0.
- **Committed in:** 5ac3a9d (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking). No scope creep — the calls were always correct; only the surrounding prose needed to dodge a substring gate.

## Issues Encountered

None beyond the deviation above. The recall seam was a near-exact template; the grounding contract (`on_event`/`get_latest_citation`/`clear`) mirrors `MemoryRecall` so the mirror was mechanical.

## Threat surface scan

No new network endpoints, auth paths, file access, or schema changes beyond the plan's `<threat_model>`. The injected `[track:<id>]` resolves only against `register_library`-seeded ids (T-77-04-01 mitigated); the embed is off-loop with a deadline (T-77-04-02 mitigated); ingest uses `_fire_ingest` only, no double retention (T-77-04-03 mitigated); both ingest calls gated on `VIBEMIX_RECALL_ENABLED` default-OFF (T-77-04-04 mitigated). No package installs (T-77-04-SC N/A).

## User Setup Required

None - no external service configuration required for the engineering green.

**KAAN-ACTION (live e2e, never faked — soft, rides forward):** On the funded key, run `uv run python -m vibemix`, play a known library track, and confirm a real `[track:<id>]` citation appears in a reaction (WIRE-01 live). Separately, with `VIBEMIX_RECALL_ENABLED=1`, confirm `~/.cache/vibemix/memory.db` fills after a session (WIRE-05 live). Both are unit-fakeable (covered here) but the real-audio/real-store confirmation is a Kaan-ear/Kaan-machine item.

## Next Phase Readiness

- Phase 77 (WIRE) is now complete: WIRE-01..06 all landed (WIRE-02/03 shipped pre-phase; WIRE-04 Plan 02; WIRE-06 Plan 03; WIRE-01 + WIRE-05 this plan).
- The wired grounding evidence surface is ready for **P78 PERCEIVE** to deepen (deltas / confidence / trajectory / embedding-genre) and **P79 LENS** / **P80 GROUND** downstream.
- No blockers. memory.db now fuels the §RECALL-EAR Kaan-ear pass (v6.0 felt-quality, independent clock).

## Self-Check: PASSED

- FOUND: .planning/phases/77-wire-connect-the-islands/77-04-SUMMARY.md
- FOUND: src/vibemix/agent/dj_cohost.py (modified)
- FOUND: src/vibemix/__main__.py (modified)
- FOUND commit e020a91 (Task 1), 5ac3a9d (Task 2)
- Full suite: 4451 passed / 26 skipped / 1 xfailed / 4 xpassed / 0 failed (244s, no API key)

---
*Phase: 77-wire-connect-the-islands*
*Completed: 2026-05-26*
