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

---

## Plan 42-03 — TS check unavailable in worktree

**Tool:** `tauri/ui` — `npm run check:ipc` / `tsc --noEmit`

**Issue:** This worktree has no `node_modules/` installed. The TS pipeline
(`codegen:ipc` + `tsc --noEmit`) requires `ajv` (and `typescript`) which are
not present locally. Plan 42-03 ships
`tauri/ui/src/debrief/components/ear-test-toggle.ts` + a `mountEarTestToggle`
wire-in inside `debrief-window.ts` + a `sendEarTestSubmit` method on
`ws-client.ts`.

**Pre-existing:** Not introduced by Plan 42-03 — `node_modules` is not part of
the repo (`.gitignore`'d). CI runs `npm ci` then `npm run check:ipc`; local
worktrees rely on the developer running `npm install` once. None of the Plan
42-03 TS changes import unfamiliar APIs — exports + DOM types only, mirroring
the existing `citation-tooltip.ts` and `chapter-list.ts` patterns.

**Disposition:** Smoke verification per the plan was the grep-check (passed —
`mountEarTestToggle` + `EarTestSubmission` both visible). CI will run the full
`check:ipc` on PR. No follow-up needed in repo.

---

## Plan 42-05 — README feature-matrix pre-existing drift

**Test:** `tests/repo/test_readme_feature_matrix_sync.py::test_readme_feature_matrix_in_sync`

**Failure:** `README.md feature matrix out of sync. Run
`python scripts/launch/sync_feature_matrix.py --write`.`

**Pre-existing:** Drift dates from before Plan 42-05 — verified by
`git stash && pytest && git stash pop` cycle showing the same failure with the
plan's test file removed from disk. Plan 42-05 touches neither `README.md` nor
`scripts/launch/sync_feature_matrix.py` nor anything routed through the feature
matrix code path.

**Disposition:** Out of scope for Plan 42-05 (SCOPE BOUNDARY rule — pre-existing
failures in unrelated files are out of scope). Closure path: a future docs /
chore plan can run `python scripts/launch/sync_feature_matrix.py --write` to
flush the regenerated matrix into README.md.
