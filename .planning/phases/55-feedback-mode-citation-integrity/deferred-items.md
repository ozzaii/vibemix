# Phase 55 — Deferred Items (out-of-scope discoveries)

Logged per the executor scope-boundary rule: pre-existing failures in files NOT
touched by the current plan. Not fixed here.

## 55-03 (LIVE-04 telemetry leaks)

- **`tests/eval/test_corpus_diversity_gate.py::test_each_session_has_events_jsonl_file`**
  — FAILS on the base commit `15fa3fe`, independent of Plan 55-03's changes.
  Cause: `eval/corpus/sessions/hard_tek_01/` ships `genre.txt` + `source.txt`
  but no `events.jsonl`. This is the documented **GATE-03 carryover** ("6 ×
  30-min DJ session WAVs in git-LFS corpus" / corpus population pending — see
  PROJECT.md "Pre-stage discharges" + STATE.md known tech-debt). Real-corpus
  population is a Kaan-action discharge, not engineering. Plan 55-03 touched
  only `src/vibemix/coach/stripped_rate.py`, `src/vibemix/agent/dj_cohost.py`,
  `src/vibemix/__main__.py` + their 3 test files — none under `eval/corpus/`.
  Left untouched.
