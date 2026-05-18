---
phase: 47-mascot-real-glb-land-full-emotion-coverage
status: clean
reviewed_at: 2026-05-18
depth: standard
files_reviewed: 34
findings_critical: 0
findings_warning: 1
findings_info: 2
fixes_applied: 1
---

# Phase 47 Code Review

**Status:** clean (1 Warning auto-fixed, 2 Info findings noted-not-blocked)

## Files Reviewed (34)

### Python (8)
- `scripts/mascot/retarget_to_neon_rebel.py` (327 lines)
- `scripts/mascot/check_manifest_complete.py` (82 lines)
- `scripts/mascot/check_no_ai_slop_phase47.py` (105 lines)
- `scripts/mascot/seed_phase_47_placeholders.py` (105 lines)
- `tests/mascot/test_retarget_cli_slots.py`
- `tests/mascot/test_bundle_gate_families.py`
- `tests/mascot/test_manifest_json_phase_47.py`
- `tests/mascot/test_persona_smoke_shape.py`
- `tests/mascot/test_readme_hero_assets.py`
- `tests/mascot/test_ci_grep_gates.py`
- `tests/mascot/test_bundle_size_cap.py` (Phase 43 update)

### Bash (3)
- `scripts/mascot/check_bundle_size.sh` (98 lines)
- `scripts/mascot/persona_smoke.sh` (95 lines)
- `scripts/mascot/render_readme_hero.sh` (83 lines)

### TypeScript (7)
- `tauri/ui/src/mascot/pools.ts`
- `tauri/ui/src/mascot/types.ts`
- `tauri/ui/src/mascot/event-dispatcher.ts`
- `tauri/ui/src/mascot/layers/anticipation.ts` (80 lines)
- `tauri/ui/src/mascot/layers/phase47-emotion.ts` (67 lines)
- `tauri/ui/src/mascot/layers/phase47-reaction.ts` (68 lines)
- `tauri/ui/src/mascot/persona-smoke-harness.ts` (118 lines)
- `tauri/ui/src/mascot/__tests__/event-coverage-matrix.test.ts`
- `tauri/ui/src/mascot/__tests__/pools-extension.test.ts`
- `tauri/ui/src/mascot/layers/anticipation.test.ts`

### YAML / config (5)
- `.github/workflows/mascot-audit.yml`
- `.github/workflows/mascot-tauri-only.yml`
- `.github/workflows/readme-hero-sync.yml` (extended)
- `assets/mascot/source/MANIFEST.yaml`
- `tauri/ui/assets/mascot/manifest.json`
- `.gitignore` (extended)

### Markdown (3)
- `docs/mascot/README.md`
- `docs/mascot/BUNDLE-DECISION.md`
- `scripts/mascot/MIXAMO-CLIP-SOURCES.md`
- `tauri/ui/assets/mascot/animations/PLACEHOLDER_NOTE.md`

## Findings

### Critical (0)

None.

### Warning (1 — auto-fixed)

**W-01 [Quality / Plan-Contract] retarget_to_neon_rebel.py main() used the legacy 400-1200 KB band for every slot**

- **File:** `scripts/mascot/retarget_to_neon_rebel.py` line 305 (pre-fix)
- **Issue:** The `--really` discharge path called `verify_size_band(size)` which hard-codes the legacy 400-1200 KB band. Plan 47-01 Task 1 truth #2 requires per-family band assertion: "retarget_to_neon_rebel.py asserts the output GLB's per-family size band (Base 200-600 KB / Emotion 300-900 KB / Anticipation+Reaction 400-1200 KB) and exits non-zero if outside the band". As-written, a base_idle.glb retarget of e.g. 800 KB would pass the legacy band check while violating its own family's 600 KB ceiling.
- **Fix applied:** Switched to `verify_size_band_for_slot(args.slot, size)` (already defined at line 152). Error message updated to surface the family name + dynamic band.
- **Verification:** 17 retarget tests still green (test_retarget_cli_slots.py 9 + test_retarget_pipeline.py 8).

### Info (2)

**I-01 [Documentation / Cohesion] Multiple anti-slop scripts coexist**

- **Files:** `scripts/launch/check_no_ai_slop.py`, `scripts/mascot/check_no_ai_slop_phase47.py`
- **Observation:** Phase 47 ships a sibling anti-slop script that re-imports `AI_SLOP_BLOCKLIST` from the canonical launch-side script. This is deliberate per the orchestrator anti-stall discipline (the launch-side script is contractually pinned to `scripts/dayzero/launch_copy/`). The sibling pattern is documented in `tests/mascot/test_ci_grep_gates.py::test_canonical_launch_anti_slop_script_untouched`.
- **Decision:** Not-blocked — single-source-of-truth preserved via runtime re-import. If future phases ship more anti-slop targets, consider a third extraction pass.

**I-02 [Convention / Idiom] Bash stat-portability helpers duplicated**

- **Files:** `scripts/mascot/check_bundle_size.sh`, `scripts/mascot/persona_smoke.sh`, `scripts/mascot/render_readme_hero.sh`
- **Observation:** Three scripts define `stat -f '%z'` (Darwin) / `stat -c '%s'` (Linux) inline. Could be extracted to a shared bash helper.
- **Decision:** Not-blocked — three callsites, each ~3 lines; extraction would add an indirection without meaningful win. Keep inline.

## Project-Convention Checks

- **Anti-slop blocklist (16 tokens + `\bdeeply\s+\w+` regex):** All Phase 47 prose artifacts clean via `scripts/mascot/check_no_ai_slop_phase47.py` (exit 0).
- **POC immutability:** `cohost*.py` + `mascot.html` byte-identical to v2.0 tag — `tests/repo/test_g5_poc_files_untouched.py` + `test_repo_scrub.py` green (15 tests).
- **No hardcoded `gemini-*` model literals:** Phase 47 changes touch zero ModelRouter surfaces — n/a.
- **Pitfall 4 closure:** Grep gate at `.github/workflows/mascot-tauri-only.yml` finds 0 violations (allowlist filters the 6 legitimate POC-immutability references).
- **Privacy rule:** Phase 47 reads/writes within `assets/mascot/`, `tauri/ui/assets/mascot/`, `scripts/mascot/`, `tests/mascot/`, `docs/mascot/`, `docs/assets/`, `.github/workflows/` — all in-bounds.

## Test-Suite Outcome

- **Python pytest tests/mascot/**: 63 / 63 pass
- **TypeScript vitest src/mascot/**: 177 / 177 pass (27 files)
- **POC immutability tests/repo/**: 15 / 15 pass
- **CI gate dry-runs (local):** check_manifest_complete.py exit 0; check_no_ai_slop_phase47.py exit 0; check_bundle_size.sh exit 2 (expected-fail placeholder UX); mascot.html grep gate exit 0 (with allowlist).

## Security

No security findings. Phase 47 changes are pure-build / pure-asset / pure-test surfaces:
- No new IPC handlers
- No new network endpoints
- No new credential paths
- No new file-system writes outside the documented `tauri/ui/assets/mascot/animations/` + `docs/assets/` + `assets/mascot/source/` paths
- All Bash scripts use `set -euo pipefail` (or equivalent variable defaults via `${var:-default}`)
- Python scripts use `pathlib.Path` instead of string concatenation
- No shell injection vectors (subprocess args list, no `shell=True`)

## Sign-off

Phase 47 cleared for verification (already passed) + Phase 48 dispatch.
