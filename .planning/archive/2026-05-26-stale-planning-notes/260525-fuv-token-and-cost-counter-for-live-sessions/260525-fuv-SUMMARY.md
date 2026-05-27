---
phase: quick-260525-fuv
plan: 01
subsystem: library/budget + agent + audio
tags: [cost, telemetry, gemini, cache, session]
requires:
  - vibemix.library.budget (BudgetTelemetry/PRICING pattern)
  - vibemix.agent.dj_cohost llm_node usage_metadata capture
  - vibemix.audio.recorder _finalize_session_meta
provides:
  - SessionMeter (router-path-keyed token + cost meter)
  - ROUTE_PRICING (live_coach/live_coach_tts/debrief/debrief_tts/embedding)
  - get_session_meter() singleton
  - session.json "cost" block + stderr cost recap at session end
affects:
  - src/vibemix/library/budget.py
  - src/vibemix/agent/dj_cohost.py
  - src/vibemix/audio/recorder.py
tech-stack:
  added: []
  patterns:
    - "Lock-guarded singleton meter mirroring BudgetTelemetry/get_telemetry"
    - "Once-per-stream record from last-seen usage_metadata (no double-billing)"
key-files:
  created:
    - tests/library/test_session_meter.py
  modified:
    - src/vibemix/library/budget.py
    - src/vibemix/agent/dj_cohost.py
    - src/vibemix/audio/recorder.py
decisions:
  - "Pricing keyed by router-PATH strings only — zero Gemini model literals (CI grep gate holds)."
  - "live_coach billed once per stream from last-seen authoritative usage totals; OpenRouter (usage=None) counts as untracked."
  - "Debrief + embedding live-wiring deliberately deferred (advisory #1)."
metrics:
  duration: ~25m
  completed: 2026-05-25
---

# Quick Task 260525-fuv: Token & Cost Counter for Live Sessions Summary

A router-path-keyed `SessionMeter` that records per-call Gemini token usage with a correct fresh/cached/output billing split, wired into the live-coach brain path so every DJ set's session.json gains a `cost` block (per-path tokens, total €, cache-hit rate, € saved by caching) plus a human-readable stderr recap at session end.

## What Was Built

**Task 1 — `SessionMeter` + `ROUTE_PRICING` (TDD):**
- `ROUTE_PRICING` in `budget.py` keyed by router-path (`live_coach`, `live_coach_tts`, `debrief`, `debrief_tts`, `embedding`) with input/output/cached_input USD-per-1M rates from `<pricing_facts>`. No model literals — the `check_no_hardcoded_model.sh` gate stays clean.
- `SessionMeter` (threading.Lock guarded, mirrors `BudgetTelemetry`): `record(path, prompt, cached, output)` does the billing split (`fresh_input = prompt - cached`, billed at input/cached/output rates), `record_untracked()` for the OpenRouter path, `summary()` returning per-path tokens + cost_eur, total_cost_eur, total_savings_eur, cache_hit_rate (clamped [0,1], 0.0 on no input), untracked_calls. `get_session_meter()` singleton + test-only `reset()`.
- Unknown router paths recorded under their key with cost 0 — never crash the stream consumer. `record()` is fully defensive (try/except, negative/None-token clamping).
- `PRICING`, `project_monthly_cost`, `CostProjection`, `BudgetTelemetry` untouched — the €50 ceiling gate still passes.

**Task 2 — wiring:**
- `dj_cohost.py` `llm_node`: captures last-seen `usage_metadata` inside the existing `if usage is not None:` block, then records `live_coach` **once** in the stream-success `else` branch (advisory #2 — final chunk carries authoritative totals; recording once post-stream prevents double-billing). OpenRouter branch (`self._or_client is not None`, usage stays None) calls `record_untracked()`. Both wrapped in best-effort try/except.
- `recorder.py` `_finalize_session_meta`: reads `get_session_meter().summary()` into `self._session_meta["cost"]` (own try/except) before the atomic write, then prints a concise stderr recap via new `_print_cost_summary` static helper. Added `import sys`.

## Verification

- `pytest tests/library/test_session_meter.py tests/library/test_budget.py::test_monthly_projection_under_50_eur` → 15 passed.
- `pytest tests/ -k "session_meter or budget or recorder"` → 54 passed.
- `pytest tests/library tests/audio` → 232 passed (no regressions).
- `scripts/release/check_no_hardcoded_model.sh` → clean.
- Both modules parse + import cleanly.
- End-to-end smoke: seeded the singleton meter, ran `VoiceRecorder.close()` → session.json gained the `cost` block (`cache_hit_rate: 0.75`, correct savings) and the stderr recap printed.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `sys` not imported in recorder.py**
- **Found during:** Task 2
- **Issue:** `_print_cost_summary` prints to `sys.stderr` but `recorder.py` did not import `sys`.
- **Fix:** Added `import sys` to the stdlib import block.
- **Files modified:** `src/vibemix/audio/recorder.py`
- **Commit:** 4799730

## Advisories Honored

- **Advisory #1 (scope):** Live wiring covers ONLY `live_coach` (brain) + `record_untracked()` on the OpenRouter path. Debrief (`tldr.py`, `drills.py`) and embedding (`embed.py`) Gemini calls are **deliberately NOT** wired to the meter in this task — debrief is a separate post-session window and embedding is index-time, neither part of a single DJ set's live cost. `ROUTE_PRICING` includes those paths forward-looking for when/if they get wired. This deferral is intentional, not an omission.
- **Advisory #2 (no double-billing):** `usage_metadata` repeats across chunks; the meter records **once** after the stream completes using the last-seen authoritative totals (captured in `last_usage`, recorded in the success `else` branch), not inside the per-chunk `if usage is not None:` block. Mirrors the existing `last_cache_hit_emitted` dedup intent.

## Known Stubs

None. The meter is fully wired on the live_coach path; debrief/embedding deferral is documented above (forward-looking pricing keys present, wiring intentionally out of scope).

## Self-Check: PASSED

- `src/vibemix/library/budget.py` — FOUND (SessionMeter, ROUTE_PRICING, get_session_meter present)
- `tests/library/test_session_meter.py` — FOUND
- `src/vibemix/agent/dj_cohost.py` — FOUND (get_session_meter().record + record_untracked wired)
- `src/vibemix/audio/recorder.py` — FOUND (get_session_meter().summary + cost block + stderr recap)
- Commits: 45ab024 (RED test), a52c0f9 (Task 1 GREEN), 4799730 (Task 2) — all in `git log`.
