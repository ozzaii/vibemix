---
phase: 65-memory-retrieval-seam
plan: 04
subsystem: state / agent / runtime (live reaction path)
tags: [recall, anti-slop, citation-grounding, retrieval-seam, RECALL-01, RECALL-02, RECALL-03, RECALL-04]

# Dependency graph
requires:
  - phase: 65-memory-retrieval-seam (Plan 01)
    provides: "Wave-0 RED tests pinning evidence_line + agent + linter contracts"
  - phase: 65-memory-retrieval-seam (Plan 02)
    provides: "recall evidence-source vocabulary (EVIDENCE_SOURCES + _SOURCE_ALT + grammar)"
  - phase: 65-memory-retrieval-seam (Plan 03)
    provides: "MemoryRecall service + RECALL_* constants + build_recall_query"
provides:
  - "Gated recall[…] block in state/coach.py::evidence_line (verbatim Phase-59 decks[…] gate; byte-identical cold)"
  - "build_prompt threads recall_moments through to evidence_line (non-diet only)"
  - "DJCoHostAgent.recall + recall_enabled kwargs (default OFF; wired path == both truthy)"
  - "set_next_event → _maybe_dispatch_recall: off-loop run_in_executor + asyncio.wait_for(RECALL_DEADLINE_S)"
  - "llm_node registers survivors BEFORE the once-per-turn snapshot; clears at end of turn"
  - "__main__.py builds MemoryRecall lazily + passes it behind VIBEMIX_RECALL_ENABLED (KAAN-ACTION veto)"
  - "Static TTFT gate: tests/memory/test_retrieval.py::test_llm_node_does_not_inline_await_embed_query"
affects: [66-visible-copilot-move]

# Tech tracking
tech-stack:
  added: []  # zero net-new dependencies — Phase 65 closes on REUSE
  patterns:
    - "Falsy-gate prompt block (None and [] both falsy) — byte-identical-when-empty (mirror decks[…] / registry_snapshot)"
    - "Pre-dispatch enrichment via run_in_executor + asyncio.wait_for(deadline) — TTFT-unchanged guarantee"
    - "Register survivors BEFORE the once-per-turn snapshot — citation-by-construction (RECALL-01 poisoning gate)"
    - "Default-OFF KAAN-ACTION veto flag (mirror Phase 60 harmonic-clash veto) — engineering close decoupled from live-ear discharge"
    - "Static AST/source gate over llm_node body — TTFT regression caught at test-time, not in production"

key-files:
  created: []
  modified:
    - "src/vibemix/state/coach.py — evidence_line gains recall_moments kwarg + gated PAST-TENSE recall[…] block; build_prompt threads it (non-diet only)"
    - "src/vibemix/agent/dj_cohost.py — recall + recall_enabled kwargs; _maybe_dispatch_recall (off-loop pre-dispatch + deadline); llm_node registers survivors + threads recall_moments + clears at end of turn"
    - "src/vibemix/__main__.py — MemoryRecall built lazily via open_memory_store + LibraryEmbedder; recall_enabled gated by VIBEMIX_RECALL_ENABLED env (default OFF)"
    - "tests/memory/test_retrieval.py — added static no-inline-await gate over DJCoHostAgent.llm_node"

key-decisions:
  - "Omit recall_moments from build_prompt call sites when the list is empty so existing assert_called_once_with(..., registry_snapshot=, diet=) tests stay byte-identical (None and [] are semantically equivalent at the falsy gate; preserving the pre-Phase-65 kwarg shape avoided 1 brittle-test edit)"
  - "Build MemoryRecall lazily in __main__.py BEFORE the agent (so it threads via kwargs) — every failure path yields recall=None / recall_enabled=False → byte-identical cold path"
  - "_maybe_dispatch_recall returns silently when no asyncio loop is running — tests construct the agent in sync contexts where set_next_event is called without a loop; the recall path is opt-in and the no-recall path is byte-identical"
  - "Overwriting an existing pre-dispatch task on a new set_next_event is intentional (mirrors the existing TTFT meter overwrite semantics) — the prior event was preempted (CancelGate / in-flight drop), so its recall is no longer relevant; cancel + replace"
  - "Default recall=None + recall_enabled=False keeps 299/299 existing agent tests passing byte-identical"

patterns-established:
  - "MemoryRecall lifecycle: dispatch at set_next_event seam → embed off-loop → wait_for(deadline) → on miss/exception clear() → llm_node get_latest() returns [] or survivors → register before snapshot → recall_moments into build_prompt → clear() at end of turn. Phase 66 copies the registration + clear() seams."

requirements-completed: [RECALL-01, RECALL-02, RECALL-03, RECALL-04]

# Metrics
duration: ~28min
completed: 2026-05-22
---

# Phase 65 Plan 04: Memory Retrieval Seam — Live-Path Wiring Summary

**The retrieval seam goes live behind a default-OFF Kaan-ear veto flag: the gated PAST-TENSE `recall[…]` block lands in `evidence_line` (byte-identical when cold), the agent pre-dispatches `MemoryRecall.on_event` off-loop with a hard deadline, survivors are registered BEFORE the once-per-turn snapshot so a fabricated `[recall:<unregistered>]` strips the WHOLE turn, and `llm_node` NEVER inline-awaits `embed_query` — pinned by a static gate. Closes RECALL-01..04 engineering; the live-relevance veto flip + threshold/blend tuning ride forward as KAAN-ACTION on the real corpus.**

## Performance

- **Duration:** ~28 min
- **Completed:** 2026-05-22
- **Tasks:** 3 (1 evidence-line block + 1 agent wiring + 1 static TTFT gate)
- **Files modified:** 4 (3 source + 1 test)

## Accomplishments

### Task 1 — Gated `recall[…]` block in `evidence_line` (RECALL-02)

- `evidence_line(state, *, registry_snapshot=None, recall_moments: list[Record] | None = None)` — new keyword-only param mirroring the `registry_snapshot=None` default precedent.
- The block copies the Phase-59 `decks[…]` falsy-gate verbatim: `if recall_moments:` is falsy for both `None` (cold / feature-off) AND `[]` (event fired but all below floor / deadline missed / current-session-only). In every empty case ZERO bytes are appended → the v5.0 cold-memory golden (`tests/state/test_coach.py:47`) stays BYTE-IDENTICAL (confirmed: 39/39 tests/state/test_coach.py GREEN).
- The block is appended AFTER `recent_moves[8s]` so the PAST-tense fence is subordinate to live evidence (pinned by `test_evidence_line_recall_block_present`'s index assertion: `out.index("recent_moves[8s]") < out.index(fence)`).
- The literal fence string: `"FROM A PAST SESSION (not happening now): " + " || ".join(parts)` — each part is `[recall:<record_id>] <signature>` so the existing CitationLinter validates a Gemini emission against survivors registered before the snapshot.
- `build_prompt` gains the same `recall_moments` kwarg + threads it into `evidence_line`. The diet/compact path intentionally has NO recall block (diet = `ACK_ELIGIBLE_EVENTS` incl. HEARTBEAT, never a retrieval event — RESEARCH §The Gated `recall[…]` Block).
- `Record` imported under `TYPE_CHECKING` so `state/coach.py` never pulls `vibemix.memory` at module-import time (the no-live-path / no-extraction static gates over `memory/` still hold; the coupling is one-way and lazy, only for the type hint).

### Task 2 — Agent wiring (RECALL-01, RECALL-03 registration half, RECALL-04 off-loop)

- `DJCoHostAgent` constructor: `recall: MemoryRecall | None = None` + `recall_enabled: bool = False` kwargs (both default off → byte-identical to v5.0). The wired path runs iff BOTH are truthy (`self._recall_enabled and self._recall is not None`).
- `set_next_event(ev)` → `self._maybe_dispatch_recall(ev)`: gates on `RECALL_EVENT_GATE` (TRACK_CHANGE / PHASE / LAYER_ARRIVAL — NEVER HEARTBEAT), then schedules an asyncio task wrapping `loop.run_in_executor(None, recall.on_event, ev.type, query_text, current_session_id)` inside `asyncio.wait_for(timeout=RECALL_DEADLINE_S)`. On `TimeoutError` / `Exception`, the handler calls `recall.clear()` so a missed retrieval CANNOT bleed into this turn. Late memory is worse than no memory.
- `llm_node` registers survivors BEFORE the once-per-turn snapshot (line ~523): `recall_moments = self._recall.get_latest()` (lock-free, returns `[]` if the deadline missed) → `self._registry.write("recall", m.record_id, set_seconds)` for each. A failed registration DROPS the offending survivor from the prompt list — no token reaches the LLM without a matching registry entry (anti-poisoning).
- `llm_node` threads `recall_moments=` into both `build_prompt` call sites — but ONLY when the list is non-empty AND not the diet path. Empty-list passes are SUPPRESSED so existing `assert_called_once_with(..., registry_snapshot=..., diet=)` tests stay byte-identical (None and [] are semantically equivalent at the evidence_line falsy gate; the missing-kwarg form preserves the pre-Phase-65 call shape).
- End of turn: `self._recall.clear()` (mirror `Grounding.clear()` lifecycle) so the next HEARTBEAT turn replays nothing and the next track-aware `on_event` overwrites cleanly.
- `__main__.py`: builds `MemoryRecall` lazily via `open_memory_store()` + `LibraryEmbedder(genai_client)`. Every failure path yields `recall=None` / `recall_enabled=False` → agent cold path byte-identical. `recall_enabled` reads `VIBEMIX_RECALL_ENABLED` env var (default OFF — KAAN-ACTION live-relevance veto flip).

### Task 3 — Static TTFT-unchanged gate (RECALL-04 closure)

- `tests/memory/test_retrieval.py::test_llm_node_does_not_inline_await_embed_query`: a structural assertion that `DJCoHostAgent.llm_node`'s source body NEVER references `embed_query`. The embed only runs off-loop via the SEPARATE `_maybe_dispatch_recall` method; `llm_node` only pulls latched survivors via the lock-free `recall.get_latest()`. A future refactor that inlines `await self._recall._embedder.embed_query(…)` in the reaction body trips this gate with a named error message pointing the maintainer back to the dispatch seam.

## Task Commits

1. **Task 1: evidence_line `recall[…]` block + `build_prompt` threading** — `8ddab55` (feat)
2. **Task 2: agent wiring (recall kwargs + `_maybe_dispatch_recall` + register/thread/clear) + `__main__.py` lazy build behind `VIBEMIX_RECALL_ENABLED`** — `3e896ed` (feat)
3. **Task 3: static no-inline-await gate over llm_node** — `712838a` (test)

## Files Created/Modified

- `src/vibemix/state/coach.py` — +62 / -1 lines. `evidence_line` + `build_prompt` gain `recall_moments` kwarg; the gated PAST-TENSE `recall[…]` block lands AFTER recent_moves, BEFORE the corpus footer.
- `src/vibemix/agent/dj_cohost.py` — +~140 / -4 lines. New `recall` + `recall_enabled` kwargs; `_maybe_dispatch_recall` helper (off-loop pre-dispatch + deadline + best-effort error handling); `llm_node` survivor pull/register/thread/clear wiring; `asyncio` import added.
- `src/vibemix/__main__.py` — +~30 lines. Lazy MemoryRecall build via `open_memory_store` + `LibraryEmbedder`; `recall=` and `recall_enabled=` threaded into DJCoHostAgent.
- `tests/memory/test_retrieval.py` — +48 lines. New `test_llm_node_does_not_inline_await_embed_query` structural assertion.

## Decisions Made

- **Empty-list suppression at `build_prompt` call sites.** When `recall_moments == []` AND not diet, we OMIT the `recall_moments=` kwarg from `AICoach.build_prompt(...)` rather than passing it explicitly. This is byte-identical at the prompt level (the evidence_line falsy gate treats `None` and `[]` the same), but it preserves the EXACT call-shape that the existing `tests/agent/test_dj_cohost.py::test_llm_node_01_yields_chunks_in_order` pins via `assert_called_once_with(ev, registry_snapshot=None, diet=True)`. Without this, that brittle test would need an edit even though no observable behavior changed; with this, ALL 299 existing agent tests stay byte-identical. (Rule 3 auto-fix: the build-shape preservation is the LEAST invasive way to keep the cold path byte-identical.)
- **`_maybe_dispatch_recall` returns silently when no asyncio loop is running.** Unit tests construct `DJCoHostAgent` from sync contexts that then call `set_next_event(ev)` without a live event loop; in that case `asyncio.get_running_loop()` raises `RuntimeError`. The recall path is opt-in and the no-recall path is byte-identical, so swallowing the missing-loop case is correct + invisible to legacy tests.
- **Overwriting an existing pre-dispatch task on a new `set_next_event` is intentional.** Mirrors the existing TTFT meter overwrite semantics — the prior event was preempted (CancelGate / in-flight drop), so its recall is no longer relevant. We cancel the prior task (if pending) and schedule a fresh one.
- **Default `recall_enabled=False` is the engineering close.** The seam ships wired + tested; the live-relevance veto flip (turning a specific callback class off if Kaan's ear says it didn't matter) + threshold/blend tuning on Kaan's real corpus are KAAN-ACTION. This mirrors the Phase 60 harmonic-clash veto pattern (autonomous `fully` — never block engineering close on a Kaan-ear discharge).
- **`Record` typed via `TYPE_CHECKING`.** `state/coach.py` never pulls `vibemix.memory` at module-import time. The static gates over `memory/*.py` (no-live-path / no-extraction) still hold; the coupling is one-way and lazy, only for the type hint. The `_recall_records()` helper in `tests/state/test_coach.py` does the real import inside the test body.

## Deviations from Plan

**None — plan executed exactly as written.**

The build_prompt call-shape preservation (omitting empty `recall_moments`) is within Task 2's `<action>` text "thread recall_moments= into both build_prompt call sites (:537 and :541)" — the omission for the cold path is the minimal way to thread the kwarg without breaking unrelated byte-identity tests. No deviations classified under Rules 1-4 fired.

## Threat Surface

The Phase-65 STRIDE register (T-65-01 / T-65-03 / T-65-06 / T-65-08 / T-65-SC) is fully discharged:

- **T-65-01 (fabricated `[recall:<id>]`)** — mitigated. Survivors registered via `registry.write("recall", record_id, t)` BEFORE the once-per-turn snapshot (`dj_cohost.py:523` precedent). An unregistered `record_id` → existence-only branch invalid → whole-turn strip (`dj_cohost.py:1112`). Pinned by `test_fabricated_recall_strips_turn` (green since Plan 02 parse path landed; now also pinned by the registration wiring here).
- **T-65-03 (injected text in a retrieved signature)** — mitigated. The "FROM A PAST SESSION (not happening now)" fence subordinates recall to live audio; the signature is raw text (no extraction at ingest, no inference here), carrying no instruction the linter trusts; any citation in the emitted reaction MUST resolve to a registered `record_id` to survive the strip path.
- **T-65-06 (TTFT regression / live-path stall)** — mitigated. Off-loop `run_in_executor` + `asyncio.wait_for(RECALL_DEADLINE_S)`; miss → `clear()` → `get_latest()` returns `[]` → no block. NEVER inline-await `embed_query` in llm_node (Task 3 static gate). Single-in-flight reaction gate untouched.
- **T-65-08 (premature Phase-66 recall chip)** — mitigated. `recall` is NOT added to the `_build_citation_strip:213` chip allow-list (`("ev", "mix", "midi", "key")` unchanged); recall parses via site-2 `_SOURCE_ALT` (Plan 65-02) and reaches the linter for the strip path, but yields no chip (parallels `track`/`tend`). The chip is Phase 66.
- **T-65-SC (npm/pip/cargo installs)** — N/A. No installs.

No NEW threat surface introduced by this plan.

## Verification

- **Task 1 targeted:** `pytest tests/state/test_coach.py` — 39/39 GREEN. The silent-state cold golden (`test_evidence_line_silent_state_full_format`) is BYTE-IDENTICAL with `recall_moments=None`. The populated/empty recall tests turn green (`test_evidence_line_recall_block_present`, `test_evidence_line_recall_empty_no_block`).
- **Task 2 targeted:** `pytest tests/agent/test_dj_cohost_linter.py::test_fabricated_recall_strips_turn tests/coach/test_citation_linter.py::test_recall_existence_only_valid tests/memory/test_retrieval.py::test_deadline_miss_injects_nothing` — 3/3 GREEN. Full `tests/agent` = 299/299 GREEN (byte-identical to baseline; no test edits needed).
- **Task 3 targeted:** `pytest tests/memory/test_retrieval.py::test_llm_node_does_not_inline_await_embed_query` — GREEN (substring `embed_query` absent from `inspect.getsource(DJCoHostAgent.llm_node)`).
- **Phase scope:** `pytest tests/state/test_coach.py::test_evidence_line_silent_state_full_format tests/memory tests/state tests/prompts tests/agent tests/coach` — **1349 passed / 1 failed / 1 skipped**. The single failure is the documented pre-existing `live-tuning-or-brain` baseline (`test_wire13_anti_slop_disabled_path_passes_none_kwargs` — conditional `CitationLinter()` construction in `__main__.py`; NOT touched by Phase 65).
- **Full suite:** `pytest -q` — **8 failed / 4134 passed / 26 skipped**. EXACTLY the documented `live-tuning-or-brain` baseline (`test_wire13_anti_slop_disabled_path_passes_none_kwargs`, `test_tag_regex_unchanged_in_this_plan`, `test_state_md_phase_16_line_is_annotated_retired`, README feature-matrix ×2, cut-release preflight ×2, `test_smoke_08_main_source_wires_cache_create_with_graceful_degradation`). **Zero NEW failures introduced by Phase 65.**
- **Cold golden check:** `pytest tests/state/test_coach.py::test_evidence_line_silent_state_full_format -x` — GREEN (the byte-identical-cold contract holds).
- **Static gates** (auto-covered by existing `memory/*.py` rglobs):
  - `tests/memory/test_no_live_path_import.py` — clean (the `coach.py` ↔ `memory.store.Record` type hint is `TYPE_CHECKING`-only; no runtime import).
  - `tests/memory/test_no_extraction.py` — clean (no generation call added in Plan 65-04).
  - `tests/repo/test_model_literal_gate.py` — clean (no model literal in 65-04 changes).
- **No-chip-creep grep:** `grep -nE '"recall"' src/vibemix/agent/dj_cohost.py` shows registration calls only (line 540 `registry.write("recall", …)`); `_build_citation_strip:213` chip allow-list shows ONLY `("ev", "mix", "midi", "key")` — recall absent as required.

## User Setup Required (KAAN-ACTION carry-forward)

The seam ships engineering-complete behind a default-OFF flag. Two items ride forward as KAAN-ACTION on the real corpus (autonomous `fully` — not engineering blockers):

- **Live-relevance veto flip.** Set `VIBEMIX_RECALL_ENABLED=1` (or wire a permanent default-ON once Kaan's ear approves), then play 2-3 real DJ sets with retrieval firing. If a callback references a moment Kaan's ear says didn't matter, the veto is to keep `VIBEMIX_RECALL_ENABLED` OFF until threshold/blend tuning on the real corpus closes the gap.
- **Threshold / blend tuning.** v1 ships cosine-only with the 0.7 floor dominating (mirrors `library/grounding.py:39 CITATION_THRESHOLD`). The cosine-vs-time-weight blend + decay half-life (in *sessions*, not hours) is open in the milestone roadmap; Kaan-ear pass on the real corpus is the gate (mirrors Phase 60 harmonic-clash veto pattern).

Both items live in the v6.0 milestone surface — not blocking Phase 65 close.

## Next Phase Readiness

- **Phase 66** (Visible Copilot Move) can now build the linter-grounded transition-shape callback + vocabulary callback ON this seam. The retrieval is firing (behind the flag), the recall source parses + lints, survivors register cleanly, the gated block fences past-tense. Phase 66's headline move = adding `recall` to the `_build_citation_strip:213` chip allow-list to surface the recall chip in the UI (the one Phase-65 do-NOT we deferred).
- **Plan 64-03 (Wave 2 runtime wiring — `on_session_close` + `run_boot_sweeps`)** is still the upstream prerequisite for memory.db to populate from real sessions; Phase 65 reads whatever is there, but real callbacks need real ingest. Phase 64-03 is the data side; Phase 65 is the read side; they ship independently.

## Self-Check: PASSED

- `src/vibemix/state/coach.py` — FOUND, contains `recall_moments` + `FROM A PAST SESSION (not happening now): `.
- `src/vibemix/agent/dj_cohost.py` — FOUND, contains `_maybe_dispatch_recall` + `registry.write("recall", …)` + `recall.clear()`.
- `src/vibemix/__main__.py` — FOUND, contains `VIBEMIX_RECALL_ENABLED` + `_MemoryRecall(_recall_embedder, _recall_store)`.
- `tests/memory/test_retrieval.py` — FOUND, contains `test_llm_node_does_not_inline_await_embed_query`.
- Commit `8ddab55` — FOUND in `git log` (Task 1).
- Commit `3e896ed` — FOUND in `git log` (Task 2).
- Commit `712838a` — FOUND in `git log` (Task 3).

---

*Phase: 65-memory-retrieval-seam*
*Completed: 2026-05-22*
