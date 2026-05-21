# Phase 57 — Deferred Items

Out-of-scope discoveries logged during execution (not fixed in the originating plan).

## From Plan 57-03 (impeccable visual pass)

### tsc errors in `tauri/ui/tests/mascot.chrome.test.ts` (Plan 57-01 file)

- **Found:** 2026-05-21, during Plan 57-03 Task 1 verify (`npx tsc --noEmit`).
- **Errors:**
  - `tests/mascot.chrome.test.ts(156,42)`: `TS2345: Argument of type 'string | undefined' is not assignable to parameter of type 'string'.`
  - `tests/mascot.chrome.test.ts(159,21)`: `TS2532: Object is possibly 'undefined'.`
- **Cause:** The POLISH-02b regression assertion added in Plan 57-01 uses `[...css.matchAll(...)]` and indexes `m[1]`/`m[2]` without narrowing for `undefined` under the project's strict tsconfig. The regex always captures both groups at runtime, so `vitest` passes (721 green) — but `tsc --noEmit` (run by `npm run build`) flags it.
- **Scope decision:** NOT fixed here. The file is owned by Plan 57-01 and is untouched by Plan 57-03's diff (`git diff HEAD -- tests/mascot.chrome.test.ts` is empty; file is byte-identical to HEAD). Fixing it would mean editing a dependency plan's test contract — out of the visual-pass scope boundary.
- **Recommended fix (for a follow-up):** narrow with a non-null assertion or guard, e.g. `m[1] ?? ""` / `m[2] ?? ""` in the `displayNoneRules` map at lines ~155-159.
- **Impact:** `npm test` (vitest) is green; only `npm run build`'s typecheck step is affected. Does not block the visual pass.
