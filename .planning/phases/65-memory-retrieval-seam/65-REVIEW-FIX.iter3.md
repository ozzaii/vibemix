---
phase: 65-memory-retrieval-seam
fixed_at: 2026-05-22T00:00:00Z
review_path: .planning/phases/65-memory-retrieval-seam/65-REVIEW.md
iteration: 1
findings_in_scope: 9
fixed: 8
skipped: 1
status: partial
---

# Phase 65: Code Review Fix Report — Memory Retrieval Seam

**Fixed at:** 2026-05-22
**Source review:** `.planning/phases/65-memory-retrieval-seam/65-REVIEW.md`
**Iteration:** 1

**Summary:**

- Findings in scope (critical + warning): 9
- Fixed: 8
- Skipped: 1 (architectural — pre-existing, not a Phase 65 regression)

The 4 BLOCKER findings (CR-01..CR-04) that gate the anti-slop release are all CLOSED. The recall registration handshake now enforces a strict-subset invariant between the prompt list and the registry, the past-session fence sits AFTER the live-evidence corpus footer, and the deadline race is closed by a per-dispatch generation token in `MemoryRecall`. The full v5.0 cold-memory golden (`tests/state/test_coach.py`) stays GREEN, with a new byte-pinned audible-no-recall test added (WR-05) to catch a future regression that the relative-comparison test would miss.

All Phase 65 reviewed-file tests pass (193/193). Twelve unrelated tests in `tests/repo/`, `tests/scripts/`, `tests/test_main_smoke.py`, `tests/eval/`, `tests/coach/test_main_anti_slop_wiring.py` fail in the same way on the unmodified baseline — pre-existing, unrelated to these fixes.

## Fixed Issues

### CR-01 + CR-02: Strict-subset recall registration with per-turn scoping

**Files modified:** `src/vibemix/agent/dj_cohost.py`, `src/vibemix/state/evidence_registry.py`
**Commit:** `28e8d01`
**Applied fix:** Replaced the in-loop list-comprehension rebind (`recall_moments = [x for x in ... if ...]` inside the iterator) with an explicit `kept: list = []` accumulator that only appends on successful registry write. The agent now calls `self._registry.clear_source("recall")` BEFORE re-registering the current turn's survivors, scoping recall registrations per-turn instead of letting them accumulate across the session as ever-widening "valid" fabrication targets. Added a new `EvidenceRegistry.clear_source(source)` primitive (clears one bucket, leaves telemetry counters untouched). The registered set is now a STRICT SUBSET of what the prompt's recall block contains, closing the headline anti-poisoning hole.

CR-02's iterator/rebind interaction is eliminated structurally by the accumulator pattern — no in-loop rebind means no iterator inconsistency, even if a future maintainer adds a `break` after the rollback. Both CRs share the same code site and the same fix per the reviewer's guidance.

### CR-03: Emit evidence_corpus footer BEFORE past-session recall fence

**Files modified:** `src/vibemix/state/coach.py`, `tests/state/test_coach.py`
**Commit:** `fbb36d2`
**Applied fix:** Swapped the order of the two if-blocks in `AICoach.evidence_line` so the live-evidence corpus footer is appended BEFORE the past-tense recall fence. Recall is now the LAST element of the evidence line — subordinate to both the live block AND the corpus marker, preventing Gemini from reading the corpus counts as describing the past session. Added `test_evidence_line_recall_block_after_corpus_footer` to pin the combined-state ordering; the existing `test_18_02_evidence_line_appends_corpus_footer_when_snapshot_present` `endswith("evidence_corpus[...]")` assertion still passes because it does not populate `recall_moments`. Also folded IN-01's inline-comment about the `" || "` inner separator into the same edit (free correctness/docs lift).

### CR-04: Per-dispatch generation token closes clear-during-inflight race

**Files modified:** `src/vibemix/memory/retrieval.py`, `tests/memory/test_retrieval.py`
**Commit:** `ef97d15`
**Applied fix:** Added `self._inflight_gen: int = 0` to `MemoryRecall`. `on_event` bumps and captures it under the lock at dispatch start; `clear()` also bumps it; the final lock-protected write in `on_event` re-checks the captured token and DROPS the survivors (returns them to the caller but does not latch) if `_inflight_gen` has been bumped in between. This closes the race where `asyncio.wait_for`'s `TimeoutError` fires `recall.clear()` while the executor thread is still mid-`query_topk` — the stale executor write can no longer overwrite the cleared latch. Added `test_clear_during_inflight_on_event_discards_stale_latch` that stages the race deterministically by hooking `embed_query` to call `recall.clear()` between dispatch and the final write.

The reviewer suggested mirroring the pattern in `library/grounding.py` "if applicable"; inspection shows grounding is NOT dispatched off-loop with a `wait_for` wrapper in `dj_cohost.py`, so the race surface does not exist there — no change needed (verified by `grep -n grounding\\|wait_for src/vibemix/agent/dj_cohost.py`).

### WR-01: Clear recall latch when get_latest() raises

**Files modified:** `src/vibemix/agent/dj_cohost.py`
**Commit:** `6408c9d`
**Applied fix:** Wrapped the `get_latest()` exception handler with a best-effort `self._recall.clear()` so a failed pull cannot leave a stale prior-turn latch behind. Defense-in-depth — the next turn's `get_latest()` can no longer return survivors that were never consumed.

### WR-02: Snapshot recall query fields under MusicState lock

**Files modified:** `src/vibemix/memory/retrieval.py`
**Commit:** `14c0610`
**Applied fix:** `build_recall_query` now snapshots the three live state fields (`audible_track`, `phase`, `audible_deck`) under `state._lock` when present, mirroring `state_refresh_loop`'s single-writer / locked-read contract. The duck-typed fallback (no `_lock` attribute) preserves the no-live-path invariant — `MusicState` is still not imported by `memory/retrieval.py`.

### WR-03: try/finally guarantees _pending_event clear on both paths

**Files modified:** `src/vibemix/agent/dj_cohost.py`
**Commit:** `9f4ac75`
**Applied fix:** Moved the `self._pending_event = None` clear from immediately after capture into a `finally:` block that scopes the entire recall pull + registration window. The clear now runs on BOTH the success and the exception path, eliminating the failure mode where an uncaught recall-registration error left the registry in a partial-write state while also clearing the pending-event flag (so the turn could never retry).

### WR-05: Byte-pinned v5.0 cold-memory baseline test

**Files modified:** `tests/state/test_coach.py`
**Commit:** `2e67bbe`
**Applied fix:** Added `test_evidence_line_audible_no_recall_byte_identical_v5_baseline` that pins the ABSOLUTE bytes of the audible+populated no-recall path against the v5.0 baseline. The existing `test_evidence_line_recall_empty_no_block` only checks `None == []` relatively — a future maintainer who shifted whitespace or reordered fields could break the baseline without that test catching it. The new test verifies all three no-recall flavors (default kwarg, explicit `None`, explicit `[]`) against the literal v5.0 string.

### IN-01: Inline-comment the " || " inner separator (folded into CR-03)

**Files modified:** `src/vibemix/state/coach.py`
**Commit:** `fbb36d2` (folded into the CR-03 commit since we were editing the same block)
**Applied fix:** Added an inline comment documenting the `" || "` (double-pipe) inner separator vs the `" | "` outer field separator — a future maintainer running `grep " | "` to count fields will no longer get an off-by-one from the recall moments. Free docs lift bundled with CR-03.

## Skipped Issues

### WR-04: Persona resolution / cache env-var stability window

**File:** `src/vibemix/__main__.py:684-700`
**Reason:** Reviewer explicitly notes "Not a Phase 65 regression — it predates this phase". The recommended fixes are architectural (either thread `cache_system_instruction` explicitly into `DJCoHostAgent.__init__`, which touches the agent constructor signature, OR document the env-var-stability requirement at the top of `main()`). Both require buy-in beyond a Phase 65 review-fix pass, and the failure mode is theoretical (`VIBEMIX_MOOD` swap between two reads inside `main()` startup). Deferring to a milestone-cleanup pass.
**Original issue:** When `cache.create()` raises, `cache_system_instruction = _resolve_prompt_cell()` work is discarded, and `DJCoHostAgent.__init__` later re-reads the same env vars — opening a theoretical inconsistency window if env vars are swapped between the two reads.

## Notes on info-tier findings (out of `critical_warning` scope)

- **IN-01** (separator comment): fixed opportunistically inside CR-03's commit since we were editing the same block — no separate commit.
- **IN-02** (cross-reference comment between `evidence_registry.py` and `memory/ingest.py`): skipped — info-tier, pure documentation polish, out of scope.
- **IN-03** (`__main__.py` blanket-except on recall_svc construction): skipped — info-tier, ergonomic improvement around Kaan-flipped recall-enabled boot path. Worth a follow-up but outside this fix pass.

## Test impact

- All 193 Phase-65-reviewed-file tests pass: `tests/state/test_coach.py` (41), `tests/memory/test_retrieval.py` (7), `tests/state/test_evidence_registry.py` (+1 implicit via `clear_source`), `tests/agent/test_dj_cohost_linter.py` (8), `tests/coach/test_citation_linter.py`, `tests/prompts/test_matrix.py`.
- v5.0 cold-memory golden invariant: GREEN (the hard invariant from the user prompt).
- Wider suite: 4083 passed, 12 pre-existing failures in unrelated source-grep / repo-structure tests (verified by running the same selectors against the unmodified baseline branch — identical failure set, no regression caused by these fixes).
- New regression tests added: 3
  - `test_evidence_line_recall_block_after_corpus_footer` (CR-03)
  - `test_clear_during_inflight_on_event_discards_stale_latch` (CR-04)
  - `test_evidence_line_audible_no_recall_byte_identical_v5_baseline` (WR-05)

---

_Fixed: 2026-05-22_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
