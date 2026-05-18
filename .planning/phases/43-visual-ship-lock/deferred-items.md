# Phase 43 deferred items

## Pre-existing worktree dirty state (logged 2026-05-16 by 43-07 executor)

The following files appear as `M` (modified) in `git status` at the time of 43-07 execution. They are LFS-pointer artifacts from worktree creation, NOT changes introduced by Plan 43-07. Per SCOPE BOUNDARY rule, they are left untouched. Surface to Phase 43 closing plan or asset-pipeline plan if they persist.

- `tauri/ui/assets/mascot/character.glb` (binary, LFS pointer drift: 20747776 → 133 bytes)
- `tauri/ui/assets/mascot/animations/*.glb` (20 files, same pattern)
- `tests/library/fixtures/synthetic_embeddings.npy`
- `tests/library/fixtures/synthetic_queries.json`

Verification: `git stash list` shows prior worktree-agent sessions stashed similar state ("stale lfs glb pointers"). This is a recurring worktree-creation artifact, not Plan 43-07's responsibility.

## Pre-existing Playwright spec TS errors (logged 2026-05-16 by 43-06 executor)

`npx tsc --noEmit` in `tauri/ui/` surfaces ~50 TS errors in:

- `tests/visual/hover-glow.wizard.spec.ts` (TS7031, TS7006 — implicit any on Playwright callback params)
- `tests/visual/meter-spectrum.spec.ts` (TS2307 — missing `@playwright/test` types; cascading TS7031/TS7006)

These exist on the current `main` HEAD (`7b9fb84`) before Plan 43-06's changes. Root cause: `@playwright/test` is not in `tauri/ui/package.json` devDependencies (Playwright runs via `playwright` only). Per SCOPE BOUNDARY rule, 43-06 does not fix unrelated pre-existing errors. Surface to a future Playwright-tooling plan that audits all `tests/visual/*.spec.ts` files for type-safety.
