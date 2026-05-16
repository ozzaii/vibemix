# Phase 43 deferred items

## Pre-existing worktree dirty state (logged 2026-05-16 by 43-07 executor)

The following files appear as `M` (modified) in `git status` at the time of 43-07 execution. They are LFS-pointer artifacts from worktree creation, NOT changes introduced by Plan 43-07. Per SCOPE BOUNDARY rule, they are left untouched. Surface to Phase 43 closing plan or asset-pipeline plan if they persist.

- `tauri/ui/assets/mascot/character.glb` (binary, LFS pointer drift: 20747776 → 133 bytes)
- `tauri/ui/assets/mascot/animations/*.glb` (20 files, same pattern)
- `tests/library/fixtures/synthetic_embeddings.npy`
- `tests/library/fixtures/synthetic_queries.json`

Verification: `git stash list` shows prior worktree-agent sessions stashed similar state ("stale lfs glb pointers"). This is a recurring worktree-creation artifact, not Plan 43-07's responsibility.
