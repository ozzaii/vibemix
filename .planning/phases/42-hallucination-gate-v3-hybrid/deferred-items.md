# Plan 42-01 — Deferred Items

## Pre-existing failure (out of scope)

**Test:** `tests/eval/test_corpus_diversity_gate.py::test_each_session_has_events_jsonl_file`

**Failure:** `eval/corpus/sessions/hard_tek_01/events.jsonl` (and all 6 sibling
session directories) lack the `events.jsonl` file the diversity gate test asserts.

**Pre-existing:** Failing at base commit `5d74d6a` before any Plan 42-01 work
landed. Phase 27-03 (commit `5a7ee8b`) created the test + the 6 session subdirs
but only seeded `genre.txt` + `source.txt` — the labeling pass that writes
`events.jsonl` never ran in CI (deferred to KAAN-ACTION corpus acquisition).

**Disposition:** Out of scope for Plan 42-01 (which ships scaffolding only —
no real corpus bytes). Closure path: GATE-03 Kaan-discharge runbook (this plan's
Task 3) directs Kaan to populate the events.jsonl per session as part of the
corpus acquisition workflow.
