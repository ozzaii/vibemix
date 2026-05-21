---
phase: 55-feedback-mode-citation-integrity
reviewed: 2026-05-21T00:00:00Z
depth: deep
files_reviewed: 10
files_reviewed_list:
  - src/vibemix/coach/stripped_rate.py
  - src/vibemix/agent/dj_cohost.py
  - src/vibemix/__main__.py
  - tests/state/test_coach_anti_slop.py
  - tests/agent/test_coach_prompt_grounding.py
  - tests/coach/test_citation_zero_orphan_replay.py
  - tests/coach/test_citation_live_debrief_consistency.py
  - tests/coach/test_slop_ratio_source.py
  - tests/coach/test_last_unverified_source.py
  - tests/coach/test_main_anti_slop_wiring.py
findings:
  critical: 0
  warning: 1
  info: 3
  total: 4
status: issues_found
---

# Phase 55: Code Review Report

**Reviewed:** 2026-05-21
**Depth:** deep (cross-file: tracker → agent → telemetry closure → coach_loop consumer → SessionCitationPayload)
**Files Reviewed:** 10 (3 source, 7 test)
**Status:** issues_found

## Summary

Phase 55 Plan 03 closes two real telemetry leaks in the LIVE-04 citation-integrity surface: the count-derived `1/(1+mean)` placeholder `slop_ratio` and the hardcoded `last_unverified_response = None`. The change is exactly what the CONTEXT decision demanded — **harden, don't rebuild**. The diff is append-only: two read accessors (`slop_ratio()`, `last_unverified()`) plus two cumulative ints and one `str | None` holder on `StrippedRateTracker`, one optional keyword-only `record()` kwarg, two agent call-sites gaining that kwarg, and a rewritten `_citation_telemetry()` closure. No machinery (`coach.py`, `citation_linter.py`, `evidence_registry.py` core, `matrix.py`) was touched — confirmed by `git diff --name-only` (only the 3 declared source files changed).

**What I verified holds:**
- **Cumulative `slop_ratio()` math is correct.** `stripped/total`, the `_cum_total == 0` guard short-circuits the divide (never NaN/None), and the counters bump on the SAME `record()` call that drives the rolling window. The cumulative pair is never evicted, so it correctly diverges from `rate()` under window roll — pinned by `test_slop_ratio_is_cumulative_not_windowed`.
- **No thread-safety regression.** `record()`/`slop_ratio()`/`last_unverified()` all run inside `DJCoHostAgent.llm_node`, which is pure async on the event loop (no `run_in_executor`, no `Thread` around the call). The plain-int + plain-str holder honors the documented single-threaded coach-loop contract — same contract the pre-existing deque already relied on.
- **No cross-session stale leak.** `StrippedRateTracker` is constructed once per `main()` (`__main__.py:695`), and `main()` runs once per process/session. A new session = new process = fresh tracker. The "clear-on-session-boundary = tracker lifecycle" claim is accurate.
- **Telemetry sourcing is wired correctly.** `_citation_telemetry()` dict keys (`slop_ratio`, `stripped_rate_15s`, `last_unverified_response`, `bypass_active`) map 1:1 to `SessionCitation.make(...)` kwargs to `SessionCitationPayload` fields. The `coach_loop` consumer (`runtime/coach.py:132-138`) reads them with defensive `.get()` defaults inside a try/except. `bypass_active` correctly stays the non-destructive `rate > STRIPPED_RATE_THRESHOLD` read — it does NOT call `should_bypass()`, so it cannot race the agent's one-shot latch.
- **All tests green.** Full default suite: **3821 passed, 26 skipped**. The 84 Phase-55 + adjacent tracker/linter tests pass. The existing `test_stripped_rate_tracker.py` rolling-rate/bypass contract is byte-identical (the additive kwarg + cumulative counters do not perturb it).

The findings below are one WARNING about a test whose name oversells the integration it proves, and three INFO items about metric-decay semantics and a duplicated tolerance constant. None block the leak fix.

## Warnings

### WR-01: `test_citation_live_debrief_consistency.py` does not exercise the actual debrief consumption path

**File:** `tests/coach/test_citation_live_debrief_consistency.py:1-135`
**Issue:** The test is named "live/debrief citation consistency" and CONTEXT.md decision (a) / the `<code_context>` debrief note ask to "confirm the citation strip is consistent live vs debrief." But the test proves consistency only of `CitationLinter.check(..., mode="live")` vs `CitationLinter.check(..., mode="debrief")`. Cross-file tracing shows the **only** `CitationLinter.check()` caller in `src/` is the live agent at `dj_cohost.py:969` with `mode="live"`. **Nothing in production calls `CitationLinter.check(mode="debrief")`.** The real debrief surfaces resolve citations through entirely separate code:
- `debrief/stripper.py::strip_uncited_sentences()` — a sentence-level regex grammar filter (`EVIDENCE_CITATION_RE`) that does not resolve against the registry at all.
- `debrief/drills.py::_citation_resolves()` — a hand-rolled snapshot lookup with its own local `_CITATION_RESOLVE_TOL_S = 2.0`.

So the test pins a `CitationLinter` branch (`mode == "debrief"`) that is currently **dormant** in the live↔debrief data flow. The "consistency" guarantee a reader infers from the name (live and debrief strip/accept the same citations against the same data) is not actually established — the two real consumers could diverge from the linter and this test would stay green. This is a genuine adversarial gap, not a style nit: it's the test most likely to be cited as "LIVE-04 debrief integrity is proven" when it isn't.

**Fix:** Either (a) tighten the docstring/name to state it pins the **linter's** two-band behavior (not the debrief consumption path), and add a separate regression that drives `debrief/drills.py::_citation_resolves()` (or `stripper.py`) against the same registry + the same drifted/orphan citations to prove the real debrief path matches the live verdict; or (b) if `mode="debrief"` is intended to become the single debrief resolver, file a follow-up to route `drills.py`/`stripper.py` through `CitationLinter.check(mode="debrief")` so the test guards a live path. Concretely, add:
```python
from vibemix.debrief.drills import _citation_resolves
def test_debrief_consumer_matches_linter_verdict():
    reg = _registry_with_phase_at(120.0); snap = reg.snapshot()
    # orphan: both must reject
    assert _citation_resolves("ev:GHOST@500.0", snap) is False
    assert CitationLinter().check("[ev:GHOST@500.0]", snap, mode="debrief").valid is False
    # 1.5s drift: both must accept at the ±2.0s debrief band
    assert _citation_resolves("ev:PHASE@121.5", snap) is True
    assert CitationLinter().check("[ev:PHASE@121.5]", snap, mode="debrief").valid is True
```

## Info

### IN-01: Debrief tolerance has two independent sources of truth (drift risk)

**File:** `src/vibemix/debrief/drills.py:46` vs `src/vibemix/coach/constants.py:20`
**Issue:** `DEBRIEF_TOLERANCE_S = 2.0` lives in `coach/constants.py`, but `drills.py` hardcodes its own `_CITATION_RESOLVE_TOL_S = 2.0` instead of importing the constant. `test_citation_live_debrief_consistency.py::test_tolerance_constants_are_one_and_two` pins the `coach/constants.py` value, but the real debrief drills resolver would keep using its local `2.0` even if the constant changed — the test would not catch the divergence. (Pre-existing, not Phase-55-introduced, but the new consistency test silently depends on these two numbers staying equal.)
**Fix:** In `drills.py`, replace the local literal with `from vibemix.coach.constants import DEBRIEF_TOLERANCE_S as _CITATION_RESOLVE_TOL_S` so there is one source of truth and the constants-pin test actually guards the debrief path's tolerance.

### IN-02: `last_unverified` and `slop_ratio` are monotonic / never decay — the drawer cannot show "recovered"

**File:** `src/vibemix/coach/stripped_rate.py:141-163`
**Issue:** Both new signals are lifetime-cumulative with no decay or expiry (this is the documented design, not a bug). Consequence for the diagnostics drawer Kaan watches: (1) `last_unverified()` pins the text of a single early strip **forever** — after 5000 subsequent clean turns the drawer still surfaces that 40-minute-old line with no recency signal, indistinguishable from "just stripped". (2) `slop_ratio()` is `stripped/total` over the whole session, so one strip in a 5000-turn session reads `0.0002` permanently and can never return to a clean `0.0`, even though the live behavior is now perfect. The windowed `stripped_rate_15s` does recover, but the two new fields are the ones the plan elevated to "the REAL metric." For a "is the anti-slop contract working *right now*" surface this is a slightly misleading read.
**Fix:** No code change required for v1 (the schema field is `str | None` and the cumulative semantics are intentional + tested). Consider a v2.x follow-up: pair `last_unverified_response` with a `last_unverified_at` timestamp (or session-relative age) so the UI can dim/expire stale text, and surface the windowed `stripped_rate_15s` as the primary "now" indicator with `slop_ratio` as the lifetime context. Worth a note in the SUMMARY so the UI side does not present a stale `last_unverified` as a live alarm.

### IN-03: Bypass path holds the full raw reply in `last_unverified` (no size bound)

**File:** `src/vibemix/coach/stripped_rate.py:116-117`, `src/vibemix/agent/dj_cohost.py:1019-1021,1055-1057`
**Issue:** `record(..., unverified_text=full_text)` stores the **entire** raw model reply (`full_text`, capped only by `max_output_tokens=1024`) verbatim into `_last_unverified`, and that string is published wholesale onto the `ipc.session.citation` wire every 2s until the next unverified emission overwrites it. The agent's other surfaces that handle `full_text` truncate before retention (`_ai_text_history.append(stripped[:140])`, `_push_transcript(stripped[:140])`). The tracker holder keeps the untruncated text. For v1 with a 1024-token cap this is bounded and harmless, but it is an inconsistent retention policy and the only place the full untrimmed reply persists past the turn. (Not a leak across sessions — single holder, per-session tracker.)
**Fix:** Optional. If the diagnostics chip wants only a preview, truncate at the agent call-site to match the history convention: `record(True, unverified_text=full_text[:280])`. If the full text is genuinely wanted in the drawer, leave as-is and note the intent in the SUMMARY so a future reader does not "fix" it.

---

_Reviewed: 2026-05-21_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_
