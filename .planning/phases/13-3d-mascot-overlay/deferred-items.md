# Phase 13 — Deferred Items (out-of-scope discoveries)

## From Plan 13-05 (2026-05-12)

### tauri/ui/src/main.ts (104) → import './session/mock.js' missing

**Discovered during:** `npm run check:ipc` after Plan 13-05 schema bump.

**Symptom:**
```
src/main.ts(104,49): error TS2307: Cannot find module './session/mock.js'
or its corresponding type declarations.
```

**Root cause:** `tauri/ui/src/main.ts` (committed in `6bb7cb6` — chore: align
REQUIREMENTS MASCOT-01..09 with 3D overlay + dev=session-mock route) references
a `./session/mock.ts` file that exists only as an untracked file in the main
repo (visible in `git status` at agent spawn time as `?? tauri/ui/src/session/mock.ts`),
but has never been committed.

**Pre-existing:** YES. This error existed BEFORE Plan 13-05 changes — the
schema bump only exposed it because `npm run check:ipc` is now what runs the
TypeScript compile. Plan 13-05's codegen output (`messages.ts`) compiles
cleanly on its own.

**Not fixed here:** Scope-boundary rule from execute-plan.md — auto-fix only
issues directly caused by current task. Surface to a follow-up plan that
either commits `session/mock.ts` or removes the `main.ts` reference until
Plan 13-04 / 13-06 lands the real wiring.

**Suggested fix path:** Either
1. Commit the existing `tauri/ui/src/session/mock.ts` file in the main repo
   under a dedicated chore commit; or
2. Comment out / dynamic-skip the `main.ts:104` mock-router branch behind a
   build-time flag until the real session UI lands.

---

### tests/agent/test_persona.py::test_persona_02_byte_identical_to_v4

**Discovered during:** test sweep after Plan 13-05 Task 3 changes.

**Symptom:** `FileNotFoundError: [Errno 2] No such file or directory: 'cohost_v4.py'`

**Root cause:** `tests/agent/conftest.py::v4_persona_string()` reads
`cohost_v4.py` from CWD (the project root). The file is untracked in the
main repo (`?? cohost_v4.py` in git status at spawn time) — and therefore
missing in the worktree, where untracked files are not propagated.

**Pre-existing:** YES. Independent of Plan 13-05 changes.

**Suggested fix path:**
1. Track `cohost_v4.py` in the repo (it's the canonical baseline per
   CLAUDE.md "POC = Reference, Devour It"), OR
2. Update the test to skip gracefully when `cohost_v4.py` is absent (the
   byte-identical check is a load-bearing invariant when run in the main
   repo, but worktree runs are routine).

