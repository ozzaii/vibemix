---
phase: 27-eval-harness-v2-0-carry-forward-close-out
plan: 06
subsystem: dist
tags:
  - rec-09
  - sidecar
  - target-triple
  - apple-silicon

requires:
  - phase: 11
    provides: scripts/build_sidecar.py + Tauri sidecar resource layout
provides:
  - --target-arch on scripts/build_sidecar.py + lipo single-arch assertion
  - GHA matrix build (arm64 + x86_64) on macos-14 + macos-13 runners
  - Runtime arch resolver in sidecar.rs (replaces const SIDECAR_TRIPLE)
  - tauri.conf.json5 bundle.resources includes BOTH arch dirs
affects:
  - Phase 28+ (DIST-* plans assume both arch sidecars are bundled)
  - Future v2.x universal2 migration path

tech-stack:
  added: []
  patterns:
    - "Per-arch PyInstaller build via --target-arch (NOT lipo-merge — RESEARCH §Critical Correction)"
    - "Runtime sidecar arch selection via std::env::consts::ARCH in Tauri Rust"
    - "GHA matrix.include with named runner + target_triple + rust_target per arch"

key-files:
  created:
    - tests/runtime_closeouts/test_universal2_sidecar.py (190 lines, 8 tests)
  modified:
    - scripts/build_sidecar.py (+111 lines)
    - .github/workflows/release.yml (+55/-16 lines)
    - tauri/src-tauri/tauri.conf.json5 (+10/-1 lines)
    - tauri/src-tauri/src/sidecar.rs (+24/-7 lines)

key-decisions:
  - "Used existing --triple arg as foundation; added --target-arch as friendly alias mapping arm64/x86_64 to canonical triples. CI uses --target-arch."
  - "macos-13 (Intel) for x86_64 builds. Fallback path: macos-14-large via Rosetta if macos-13 deprecates."
  - "tauri.conf.json5 keeps bundle.resources (NOT externalBin) per existing Phase 11 architecture (lines 95-100). externalBin flattens onedir which breaks PyInstaller bootloader."
  - "sidecar.rs runtime fallback: unknown arch returns aarch64-apple-darwin with loud file-not-found error (no silent path failure)."

requirements-completed:
  - REC-09

duration: ~25 min
completed: 2026-05-15
---

# Phase 27 Plan 06: REC-09 Universal2 Sidecar Summary

**Eliminates the Rosetta translation prompt for Apple Silicon users on first install — ships TWO arch-specific PyInstaller bundles per the research-corrected target-triple convention, NOT a lipo-merged universal2 binary.**

## Performance

- **Duration:** ~25 min
- **Tasks:** 3 (atomic commits per task)
- **Files created:** 1 (test file with 8 tests, all passing)
- **Files modified:** 4 (build_sidecar.py, release.yml, tauri.conf.json5, sidecar.rs)

## Accomplishments

- `scripts/build_sidecar.py --target-arch arm64|x86_64|aarch64|intel` accepts a friendly arch alias, maps to the canonical Rust triple, passes `--target-arch <arch>` to PyInstaller for cross-arch build, and asserts single-arch via `lipo -archs` post-build. Mitigates Pitfall P69.
- `.github/workflows/release.yml` matrix build: arm64 on macos-14 + x86_64 on macos-13. Each runner installs the matching Rust target, runs the lipo single-arch verification, and uploads the per-arch artifact.
- `tauri/src-tauri/tauri.conf.json5` `bundle.resources` lists BOTH arch directories. Bundle ID `world.bravoh.vibemix` UNCHANGED (Pitfall P63 lock).
- `tauri/src-tauri/src/sidecar.rs` runtime arch resolver replaces `const SIDECAR_TRIPLE` — a single .app bundle picks the correct binary at runtime via `std::env::consts::ARCH`.

## Task Commits

1. **Task 1: --target-arch + lipo single-arch assertion in build_sidecar.py** — `d5b9ae9`
2. **Task 2: Matrix arm64 + x86_64 build in release.yml** — `27a48da`
3. **Task 3: Runtime arch resolver + tauri resources both archs + tests** — `afff7e8`

## Deviations from Plan

### Auto-fixed Issues (3 Rule 1 — codebase-vs-plan mismatches)

1. **tauri.conf.json5 uses `bundle.resources`, NOT `externalBin`** — adapted plan to actual architecture (resources/ + Rust runtime resolver in sidecar.rs); same end-state delivered.
2. **Existing artifacts are `vibemix-core-*`, plan said `vibemix-sidecar-*`** — used actual `vibemix-core` naming throughout.
3. **`--triple` already does what `--target-arch` was specified to add** — added `--target-arch` as friendly alias on top of existing `--triple` arg (mutually exclusive); plus added the PyInstaller `--target-arch` passthrough that the plan intended.

**Total deviations:** 3 auto-fixed. **Impact:** No architectural redesign; plan intent fully delivered against actual codebase.

## macos-13 Deprecation Risk

GitHub Actions deprecation timeline: macos-13 supported through ~Q3 2026.
- Fallback 1: switch matrix runner to `macos-14-large` (Intel hardware via Rosetta on Apple Silicon). One-line change in release.yml.
- Fallback 2: provision self-hosted Intel Mac runner. Out-of-scope for v2.1.
- Fallback 3 (last resort): drop x86_64 support; re-introduces Rosetta prompt for Intel-Mac users.

## Verification

```bash
grep -q "target-arch" scripts/build_sidecar.py
grep -q "matrix:" .github/workflows/release.yml
! grep -E "lipo -create" .github/workflows/release.yml
grep -q '"identifier": "world.bravoh.vibemix"' tauri/src-tauri/tauri.conf.json5
grep -q "fn sidecar_triple" tauri/src-tauri/src/sidecar.rs
grep -q "std::env::consts::ARCH" tauri/src-tauri/src/sidecar.rs
uv run pytest tests/runtime_closeouts/test_universal2_sidecar.py -x  # 8 passed
```

## Self-Check: PASSED

- [x] All 8 plan-level success criteria met (with 3 documented Rule 1 deviations)
- [x] All `<acceptance_criteria>` from all 3 `<task>` blocks pass
- [x] No `lipo -create` step anywhere in release.yml
- [x] Bundle identifier `world.bravoh.vibemix` UNCHANGED (Pitfall P63)
- [x] sidecar.rs runtime resolver active
- [x] No POC files modified

## Next Plan Readiness

Wave 1 plans 27-07/08/09 are independent. The matrix CI build will exercise the new release.yml on the next tag push.
