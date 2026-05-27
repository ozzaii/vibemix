# Generated Output Cleanup — 2026-05-26

This cleanup removed ignored generated artifacts from the active workspace.

## Deleted

- `build/` — PyInstaller intermediate output for `vibemix-core.macos`
  (`194M` before removal). It is ignored by `.gitignore` and reproducible from
  the sidecar build flow, so it was deleted instead of archived into another
  large binary bundle.
- `tauri/src-tauri/target/debug/binaries/` — ignored Tauri debug sidecar payload
  (`543M` before removal). It included a stale expanded `vibemix-core` tree and
  polluted source searches with vendored dependency TODOs. The release/dev
  sidecar is reproducible, and `tauri/src-tauri/binaries/.placeholder` keeps the
  resource glob satisfied for checks.
- `tauri/src-tauri/binaries/vibemix-core-aarch64-apple-darwin/` generated
  PyInstaller sidecar payload (`543M` before removal). The real release sidecar
  is reproducible through `scripts/build_sidecar.py` / release matrix artifacts.
  A tiny `.placeholder` now remains in each arch-specific resource directory so
  Tauri resource-glob checks still work without committing a generated bundle.
- `spikes/**/__pycache__/` — ignored Python bytecode caches under the tracked
  spike tree. Removed as reproducible interpreter output.
- `dist/e2e-macbook-runs/` — ignored e2e HTML report pile (`1.3M` before
  removal). These were dated local verification reports, not source artifacts.
- `dist/install-vm-runs/` — ignored empty install-VM run directory.
- `dist/vibemix-0.1.0.dev0-py3-none-any.whl` — ignored Python wheel build
  artifact (`92K`), reproducible from the package build.
- `dist/vibemix-core/` — ignored PyInstaller sidecar output (`493M` before
  removal), reproducible from the sidecar build.
- `dist/vibemix_0.1.0-rc1_aarch64-unsigned.dmg` — ignored old unsigned release
  candidate (`242M`), stale for the current CLAP/Codex/CUE state.
- `recordings/20260515-112139/` — ignored local runtime recording payload
  (`212M` before removal). The test fixture derived from this run is already
  checked in under `tests/fixtures/hype_trace_genre1.jsonl`; mutable runtime
  recordings must not be treated as source.
- Repo-local `__pycache__/`, `.pytest_cache/`, and `.ruff_cache/` directories
  outside virtualenvs, Tauri target, node_modules, and Claude worktrees —
  reproducible interpreter/test/linter caches removed from source, tests,
  scripts, eval, installer, and proxy app/test trees.

## Kept

- `tauri/src-tauri/target/` — Rust build cache kept for now because deleting the
  entire directory would slow near-term verification. Only the stale ignored
  debug sidecar payload under `target/debug/binaries/` was removed.
- `tauri/src-tauri/binaries/vibemix-core-aarch64-apple-darwin/.placeholder`
  and `tauri/src-tauri/binaries/vibemix-core-x86_64-apple-darwin/.placeholder`
  — tiny source placeholders kept so both Tauri resource globs exist in a clean
  checkout while real sidecar bundles stay generated release artifacts.
- `tauri/ui/dist/` — frontend build output kept for now because recent UI
  verification refreshed it and commit splitting will decide whether generated
  dist belongs in the UI patch.
- `dist/launch-runs/.gitkeep` — tracked SHIP-08 audit scaffold kept so a fresh
  clone still has the expected launch-run directory.
- `.claude/`, `.venv/`, `proxy/.venv/`, `tauri/src-tauri/target/`,
  `tauri/ui/node_modules/`, and `tauri/ui/dist/` — large ignored developer
  environments/build caches kept for now. `.claude/` contains shared agent
  worktrees, and `target/` / `dist/` are useful for near-term verification.
- `.planning/eval-runs/loadtest_*.json` — archived later in
  `.planning/archive/2026-05-26-eval-run-json/`; `.gitkeep` remains so the
  artifact directory still exists for fresh runs.
