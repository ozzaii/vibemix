---
phase: 55-feedback-mode-citation-integrity
plan: 03
subsystem: coach / citation-telemetry
tags: [citation-integrity, slop-ratio, last-unverified, telemetry, stripped-rate-tracker, live-04]
requirements: [LIVE-04]
req_ids: [LIVE-04]
dependency_graph:
  requires:
    - "StrippedRateTracker (src/vibemix/coach/stripped_rate.py) — extended in place"
    - "DJCoHostAgent.llm_node strip ladder (src/vibemix/agent/dj_cohost.py)"
    - "_citation_telemetry() closure (src/vibemix/__main__.py)"
    - "SessionCitationPayload (src/vibemix/ui_bus/schemas/citation.py) — field set unchanged"
  provides:
    - "StrippedRateTracker.slop_ratio() -> float — real cumulative stripped/total"
    - "StrippedRateTracker.last_unverified() -> str | None — most-recent unverified text"
    - "record(*, unverified_text=None) optional kwarg"
    - "_citation_telemetry() sourced from the two real accessors"
  affects:
    - "ipc.session.citation diagnostics strip (Tauri Settings -> Diagnostics): slop_ratio + last_unverified_response now reflect REAL state"
tech_stack:
  added: []
  patterns:
    - "Append-only accessor extension on a single-threaded telemetry class (no lock, plain ints)"
    - "Optional keyword-only kwarg with None default to keep existing call sites byte-identical"
key_files:
  created:
    - tests/coach/test_slop_ratio_source.py
    - tests/coach/test_last_unverified_source.py
  modified:
    - src/vibemix/coach/stripped_rate.py
    - src/vibemix/agent/dj_cohost.py
    - src/vibemix/__main__.py
    - tests/coach/test_main_anti_slop_wiring.py
decisions:
  - "slop_ratio is cumulative-per-session (lifetime), distinct from the 15s rolling rate() — both off the same record() decisions"
  - "last_unverified set on strip OR bypass (both surface text the user did/did-not hear); clean emit leaves it untouched"
  - "Append-only: two accessors + one optional kwarg; coach/linter/registry-core/matrix machinery NOT rebuilt (CONTEXT decision c)"
metrics:
  duration: "~25 min"
  completed: "2026-05-21"
  tasks: 4
  commits: 4
  files_changed: 6
---

# Phase 55 Plan 03: Close the telemetry leaks — real slop_ratio + last_unverified_response Summary

One-liner: Replaced two self-documented v2.x stubs in the LIVE-04 diagnostics surface — the count-derived `1/(1+mean)` `slop_ratio` placeholder and the hardcoded `last_unverified_response = None` — with REAL signals sourced from a cumulative stripped/total counter and a most-recent-unverified-text holder on `StrippedRateTracker`, fed by the agent's strip/bypass branches.

## What Was Built

The citation strip Kaan watches in Settings -> Diagnostics now reflects reality:

1. **`StrippedRateTracker.slop_ratio()`** (Task 1) — a real cumulative `stripped/total` ratio. Two lifetime ints (`_cum_stripped`, `_cum_total`) bump on the SAME `record()` call that drives the 15s rolling window, so a strip raises both `slop_ratio()` and `rate()`. `0.0` cold-start (guarded divide, never NaN/None). Crucially the counters are NOT windowed/evicted, so `slop_ratio()` survives a window roll that drops `rate()` — proving the two are distinct signals.

2. **`StrippedRateTracker.last_unverified()`** (Task 2) — a `str | None` holder fed by a new keyword-only `record(*, unverified_text=None)` kwarg. Set on a strip OR a bypass when text is provided (most-recent overwrite). The `None` default keeps every existing `record(bool)` call site byte-identical; the rolling-rate + slop counters work whether or not text is passed.

3. **Agent wiring** (Task 3) — `DJCoHostAgent.llm_node` now passes the raw `full_text` into the tracker on the strip branch (`record(True, unverified_text=full_text)`) and the bypass branch (`record(False, unverified_text=full_text)`). `full_text` was already in scope (logged as `raw_text=` on the `citation_strip`/`citation_bypass` events). The valid/emit branch keeps `record(False)` with no text (clean turn). No other `llm_node` behavior changed.

4. **Telemetry rewrite** (Task 4) — `_citation_telemetry()` in `__main__.py` now sources `slop_ratio` from `stripped_rate_tracker.slop_ratio()` and `last_unverified_response` from `stripped_rate_tracker.last_unverified()`. The `1/(1+mean)` placeholder + its `evidence_registry.citation_telemetry()` mean read are removed; the hardcoded `None` is removed. `stripped_rate_15s` (`rate()`) and `bypass_active` (non-destructive `rate > STRIPPED_RATE_THRESHOLD`, NOT `should_bypass()`) are unchanged. The closure still cannot raise when the tracker is None (anti-slop disabled) — safe defaults `slop_ratio 0.0`, `last_unverified None` (T-20-05-03).

## Why slop_ratio Is Cumulative vs the Windowed rate()

These are two distinct signals off the same `record()` decisions:

- **`slop_ratio()`** = lifetime-of-session `stripped/total` — the "what fraction of model turns got stripped" metric LIVE-04 wants Kaan to watch. Never evicted.
- **`rate()`** = 15s rolling stripped fraction — the bypass-guard signal that drives `should_bypass()`. Evicted per window.

A strip bumps both. A window roll drops `rate()` back toward 0 but leaves `slop_ratio()` reflecting the full session history. `test_slop_ratio_is_cumulative_not_windowed` pins exactly this divergence. The `SessionCitationPayload` docstring + `55-CONTEXT.md` decision (c) both already described `slop_ratio` as "cumulative stripped/total" — this plan makes the implementation match the long-standing contract.

## Append-Only Shape — Why No Machinery Was Rebuilt

Per CONTEXT decision (c) ("Don't rebuild the coach/evidence machinery — validate + harden it; any change is data-driven + test-pinned"), the change is strictly additive: two new public accessors + one optional `record()` kwarg. The agent's strip/emit/bypass decision ladder is unchanged (only the two tracker calls gained a kwarg). `coach.py`, `citation_linter.py`, `evidence_registry.py` core, and `matrix.py` are untouched. The `SessionCitationPayload` field set is unchanged — only the SOURCE of two fields changed. No new dependencies, no new public surface beyond the two accessors + the kwarg.

## Tasks & Commits (4 atomic)

| Task | Name | Commit |
| ---- | ---- | ------ |
| 1 | RED+GREEN — cumulative slop_ratio() on StrippedRateTracker | `0814daa` |
| 2 | RED+GREEN — last_unverified() holder fed from record() | `c24428b` |
| 3 | Wire agent strip/bypass branches to pass full_text | `c3f9316` |
| 4 | Rewrite _citation_telemetry() to source real signals | `d4819a0` |

## TDD Gate Compliance

Tasks 1 & 2 followed RED -> GREEN. Task 1: 7 new tests failed on the missing `slop_ratio` attribute (RED), then passed after the accessor was added (GREEN). Task 2: 8 new tests failed on the unexpected `unverified_text` kwarg / missing accessor (RED), then passed after the kwarg + holder were added (GREEN). No unexpected RED-phase passes. Tasks 3 & 4 are `type="auto"` wiring/source-correctness with their behavior pinned by the existing agent suite + the extended source-grep wiring test.

## Verification

- `tests/coach/` — **79 passed** (24 in the three slop/last-unverified/tracker files + 20 in the wiring file + the rest of the coach suite).
- `tests/agent/test_dj_cohost_linter.py tests/agent/test_dj_cohost.py` — **38 passed** (strip ladder behavior unchanged; exactly 2 `unverified_text=full_text` call sites; valid/emit branch still bare `record(False)`).
- Focused superset (coach + agent + runtime + ui_bus + main smoke) — **741 passed**.
- Full default suite — **3786 passed, 27 skipped, 1 failed** in 153s.
- `git diff --name-only` confirms ONLY the 6 plan-scoped files changed; `tauri/src-tauri/*` (Kaan WIP) NOT staged.

## Deviations from Plan

None for the four tasks — plan executed as written. One mid-task test fix: the Task 4 wiring assertion `should_bypass()` was too literal (matched the docstring's explanatory mention of why it is avoided); tightened to `stripped_rate_tracker.should_bypass()` (the actual invocation form). This is a test-authoring correction within Task 4, not a behavior deviation.

## Deferred Issues (out of scope — pre-existing, not caused by this plan)

The full-suite single failure — `tests/eval/test_corpus_diversity_gate.py::test_each_session_has_events_jsonl_file` — is a missing corpus fixture (`eval/corpus/sessions/hard_tek_01/events.jsonl`). It fails identically on the base commit `15fa3fe` and maps to the documented **GATE-03 carryover** (corpus WAV/label population pending — a Kaan-action discharge per PROJECT.md "Pre-stage discharges" + STATE.md tech-debt). It lives under `eval/corpus/`, which Plan 55-03 did not touch. Logged to `.planning/phases/55-feedback-mode-citation-integrity/deferred-items.md`; left unfixed per the executor scope-boundary rule.

## Self-Check: PENDING
