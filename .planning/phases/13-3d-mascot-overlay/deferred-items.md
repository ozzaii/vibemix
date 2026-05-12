# Phase 13 — Deferred Items (out-of-scope discoveries)

Tracking items surfaced during plan execution that fall outside the
executing plan's scope. Each item names the plan that found it + the
plan that should resolve it.

## From Plan 13-03 + Plan 13-05 (2026-05-12)

### `tauri/ui/src/main.ts:104` → import `./session/mock.js` missing

**Discovered during:** Plan 13-03 build sweep AND Plan 13-05 `npm run check:ipc`.

**Symptom:**
```
src/main.ts(104,49): error TS2307: Cannot find module './session/mock.js'
or its corresponding type declarations.
```

**Root cause:** `tauri/ui/src/main.ts` (committed in `6bb7cb6` — chore: align
REQUIREMENTS MASCOT-01..09 with 3D overlay + dev=session-mock route) references
a `./session/mock.ts` file that was untracked in the main repo at the time
Phase 13 forked, but has never been committed.

**Pre-existing:** YES. This error existed BEFORE 13-03 or 13-05 ran.

**Not fixed here:** Scope-boundary rule — both executors auto-fix only
issues directly caused by current task.

**Suggested fix path:** Either
1. Commit the existing `tauri/ui/src/session/mock.ts` file under a chore commit; or
2. Comment out / dynamic-skip the `main.ts:104` mock-router branch behind a
   build-time flag until the real session UI lands.

**Resolve in:** Plan 13-04 or earlier-phase fix-up — whoever first lands
the session-mock route must commit `src/session/mock.ts` alongside `main.ts`.

---

### `tests/agent/test_persona.py::test_persona_02_byte_identical_to_v4`

**Discovered during:** Plan 13-05 Task 3 test sweep.

**Symptom:** `FileNotFoundError: [Errno 2] No such file or directory: 'cohost_v4.py'`

**Root cause:** `tests/agent/conftest.py::v4_persona_string()` reads
`cohost_v4.py` from CWD (project root). The file is untracked in the
main repo (`?? cohost_v4.py` in git status at spawn time) — and therefore
missing in the worktree, where untracked files are not propagated.

**Pre-existing:** YES. Independent of Plan 13-05 changes.

**Suggested fix path:**
1. Track `cohost_v4.py` in the repo (canonical baseline per
   CLAUDE.md "POC = Reference, Devour It"), OR
2. Update the test to skip gracefully when `cohost_v4.py` is absent
   (the byte-identical check is a load-bearing invariant when run in the main
   repo, but worktree runs are routine).
