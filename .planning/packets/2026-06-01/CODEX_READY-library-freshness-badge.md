# CODEX_READY: Shell Library Freshness Badge

Date: 2026-06-01
Author: Codex
Status: LAND packet, shell readout slice
Package: Package 5G - Shell Library Freshness Badge
Suggested commit: `feat(tauri-ui): show library freshness in shell`

## Decision

LAND this slice as `feat(tauri-ui): show library freshness in shell`.

The library freshness engine is now source-aware and wired through Settings and
Viber guardrails. This package makes that state visible in the main shell footer
as a compact readout: fresh, stale, not indexed, or unknown.

## Files

- `tauri/ui/src/shell/LibraryFreshnessBadge.ts`
- `tauri/ui/src/shell/app.ts`
- `tauri/ui/src/shell/shell.css`
- `tauri/ui/tests/shell/library-freshness-badge.spec.ts`
- `.planning/handoffs/2026-05-31-package-checklist.md`
- `.planning/packets/2026-06-01/CODEX_READY-library-freshness-badge.md`

## What Changed

- Added a small shell footer badge that consumes `libraryStats()` and maps the
  existing freshness contract to truthful display states.
- The badge is read-only and display-only. It does not add a backend command,
  automatic import, watcher, or schema.
- Failures render `library unknown`, not a fake good state.
- The shell app mounts and tears down the badge beside the existing session
  status footer.

## Evidence

```text
npm --prefix tauri/ui test -- tests/shell/library-freshness-badge.spec.ts tests/shell/shell.spec.ts
Test Files  2 passed (2)
Tests       15 passed (15)
```

```text
npm --prefix tauri/ui test -- tests/shell/library-freshness-badge.spec.ts src/library/api.test.ts
Test Files  2 passed (2)
Tests       47 passed (47)
```

```text
npm --prefix tauri/ui run build
✓ built
```

```text
git diff --check -- tauri/ui/src/shell/LibraryFreshnessBadge.ts tauri/ui/src/shell/app.ts tauri/ui/src/shell/shell.css tauri/ui/tests/shell/library-freshness-badge.spec.ts
```

## Boundaries

- No backend behavior changed.
- No claim that a signed packaged artifact contains this UI until rebuild.
- No screenshot or visual-acceptance claim yet; this is code, tests, and build
  proof only.
