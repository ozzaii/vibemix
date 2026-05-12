# Phase 13 — Deferred Items

Tracking items surfaced during plan execution that fall outside the
executing plan's scope. Each item names the plan that found it + the
plan that should resolve it.

## From 13-03 execution (2026-05-12)

- **Pre-existing TS error: `src/main.ts(104,49): error TS2307: Cannot
  find module './session/mock.js'`** — Found running `npm run check:ipc`
  at base commit `6bb7cb6` (verified by stash test). The base commit
  added `?dev=session-mock` routing to `main.ts` but the matching
  `session/mock.ts` file is untracked (left in the main repo branch,
  not committed onto the Phase 13 base). Not introduced by 13-03 and
  not within its files_modified scope. **Resolve in 13-04 or
  earlier-phase fix-up** — whoever first lands the session-mock route
  must commit `src/session/mock.ts` alongside `main.ts`.
