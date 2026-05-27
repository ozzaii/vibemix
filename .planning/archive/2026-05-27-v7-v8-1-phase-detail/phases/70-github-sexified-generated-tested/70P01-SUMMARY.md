---
phase: 70-github-sexified-generated-tested
plan: 01
wave: 0
subsystem: asset-reproducibility-infra
tags: [github, assets, reproducibility, manifest, ci, bitrot, wave-0, foundational]
requirements:
  - GH-04
provides:
  - "docs/assets/MANIFEST.yaml — asset reproducibility manifest: top-level `assets:` list ({path, source, sha256, generator}) seeded empty + `opt_out:` list of 27 bespoke/foreign-generated paths the bitrot gate must not check"
  - "tests/repo/test_asset_manifest_shape.py — 6-test schema-pin (parse, exact top-level keys, exact asset key set, sha256 PENDING|64-hex format, opt_out path existence, no assets/opt_out overlap); default grid, no opt-in marker"
  - "scripts/regenerate_assets.sh — deterministic bash regenerator (executable, set -euo pipefail) reading MANIFEST.yaml `assets:` via a PyYAML one-liner, dispatching each entry to its generator step + recomputing shasum -a 256; no-op-clean exit 0 at empty-assets wave; Wave 1 og-card slots into the marked case extension point"
  - ".github/workflows/asset-bitrot.yml — CI bitrot gate (ubuntu-latest, one job asset-bitrot) running the regenerator + git diff --exit-code docs/assets/, fork-PR-safe security posture lifted from packaging-audit.yml"
affects:
  - docs/assets/MANIFEST.yaml (NEW: 73 insertions)
  - tests/repo/test_asset_manifest_shape.py (NEW: 104 insertions, 6/6 GREEN default grid)
  - scripts/regenerate_assets.sh (NEW: executable mode 100755, set -euo pipefail)
  - .github/workflows/asset-bitrot.yml (NEW)
tech-stack:
  added: []
  patterns:
    - "MANIFEST.yaml schema (CONTEXT.md Claude's-Discretion lock): `assets: [{path, source, sha256, generator}]` + `opt_out: [paths]`. The gate is SCOPED not global — only `assets:` entries are regenerated; opt_out (bespoke originals) + foreign-generator assets (architecture.svg, screenshots/*.png) are never touched, so the bitrot gate never fails on an asset it does not own."
    - "social-card.png reconciliation option (a) — least destructive: the 380k hand-cut predecessor is retained as a MANIFEST opt_out bespoke asset (grep confirmed zero live refs outside planning docs). Wave 1's og-card.png is its source-generated, hash-pinned successor; social-card.png is not deleted."
    - "CI security posture lifted verbatim from packaging-audit.yml (Phase 69-04) / full-test-matrix.yml (Phase 67P04): on: pull_request (the plain trigger, never the *_target variant), permissions.contents: read, workflow-prefixed concurrency cancel-in-progress, SHA-pinned actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5 (v4.3.1), timeout-minutes: 15."
    - "Schema-pin test idiom (mirrors tests/repo/test_packaging_scaffolds_present.py): REPO_ROOT = parents[2], yaml.safe_load, set-equality on top-level + per-entry key sets (catches typo'd/extra keys), re.fullmatch sha256 format gate, opt_out path-existence catch for stale entries. Each assert message names the originating plan + task."
    - "Regenerator reads YAML via an inline `python3 - <<'PY'` heredoc (PyYAML, a tracked transitive dep — no new dep) printing TSV rows, looped in bash. Wave 0 assets: [] → loop body never runs → clean no-op exit 0, so the bitrot gate is green from this wave forward."
key-files:
  created:
    - docs/assets/MANIFEST.yaml
    - tests/repo/test_asset_manifest_shape.py
    - scripts/regenerate_assets.sh
    - .github/workflows/asset-bitrot.yml
    - .planning/phases/70-github-sexified-generated-tested/70P01-SUMMARY.md
  modified: []
  deleted: []
decisions:
  - "MANIFEST opt_out classification: bespoke hand-cut originals (social-card.png, hero.png, demo-placeholder.gif, readme-hero.png, readme-hero.webm) + foreign-generator assets (architecture.svg via scripts/dist/render_architecture.py; the 5 screenshots/*.png via docs/assets/screenshots/regen.sh; 10 controllers/*.svg + 6 dj-software/*.svg). `assets:` is empty at Wave 0 — Wave 1 (70P02) appends the og-card entry. Every opt_out path is enumerated as a concrete file path (not a glob) so test_asset_manifest_shape.py's existence check is exact."
  - "Plan literal opt_out used directory globs (screenshots/*.png, controllers/*.svg). Rule-1 reconciliation: the schema-pin test asserts each opt_out path is an existing file, which a glob string is not. Expanded all globs to the 27 concrete file paths present on disk today. Functionally identical scope, test-compatible. Documented for Wave 4 (which reads this manifest's OG hash)."
  - "asset-bitrot.yml comment originally read 'NOT pull_request_target', tripping the plan's `grep -c pull_request_target == 0` acceptance gate textually even though the actual `on:` key is the safe `pull_request`. Rule-1 reconciliation: reworded the comment to 'the plain trigger, never the *_target variant' so the literal string appears zero times; YAML re-parse confirms on=push+pull_request, permissions.contents=read, job=asset-bitrot. Same posture decision as Phase 69-04 hit (documented there)."
metrics:
  duration: ~12 min
  completed_date: 2026-05-24
  files_touched: 5
  baseline_before: "~4200 passed / ~26 skipped / 4 xpassed / 2 failed (post-69 @ HEAD)"
  baseline_after_default_grid: "4207 passed / 26 skipped / 4 xpassed / 2 failed (Wave 0 close)"
  baseline_delta: "+6 tests (test_asset_manifest_shape.py: 6/6 GREEN); 2 pre-existing Phase 68 README feature-matrix drift failures unchanged (documented in .planning/phases/69-oss-fully-integrated/deferred-items.md — NOT a Phase 70 regression)"
  wall_clock_full_suite_default_grid: 217.15s
  task_commit_shas:
    - ad9fff3 (Task 1: docs/assets/MANIFEST.yaml + tests/repo/test_asset_manifest_shape.py)
    - 6f82170 (Task 2: scripts/regenerate_assets.sh + .github/workflows/asset-bitrot.yml)
---

# Phase 70 Plan 01: Asset Reproducibility Infra Summary

Foundational GH-04 infra landed: a deterministic bash regenerator
(`scripts/regenerate_assets.sh`), a hash-pinned asset manifest
(`docs/assets/MANIFEST.yaml`), a fork-PR-safe CI bitrot gate
(`.github/workflows/asset-bitrot.yml`), and a 6-test schema pin
(`tests/repo/test_asset_manifest_shape.py`) — all green-at-empty-assets so
Wave 1's og-card registers into the marked extension point.

## What Shipped

| Artifact | Role |
|----------|------|
| `docs/assets/MANIFEST.yaml` | `assets: []` (Wave 1 fills) + `opt_out:` of 27 bespoke/foreign-generated paths |
| `tests/repo/test_asset_manifest_shape.py` | 6 schema-pin tests, default grid |
| `scripts/regenerate_assets.sh` | bash dispatcher, no-op-clean exit 0 today; Wave 1 og-card extension point |
| `.github/workflows/asset-bitrot.yml` | regenerate + `git diff --exit-code docs/assets/`, fails on drift |

## MANIFEST Classification (asset vs opt_out)

- **`assets: []`** — empty at Wave 0 by plan. The only source-derived asset
  this script will own is Wave 1's og-card (`docs/assets/og-card.png` from
  `docs/assets/sources/og-card.html`); `grep -c sources/og-card MANIFEST.yaml`
  returns 0 today, as required.
- **`opt_out:` (27 paths)** — chosen because each is either:
  - **bespoke hand-cut** (no source-derived regenerator): `social-card.png`
    (CONTEXT reconciliation option (a) — retained, not deleted; zero live refs),
    `hero.png`, `demo-placeholder.gif`, `readme-hero.png`, `readme-hero.webm`.
  - **foreign-generated** (has its OWN generator, out of regenerate_assets.sh
    scope): `architecture.svg` (render_architecture.py), the 5 `screenshots/*.png`
    (screenshots/regen.sh), the 10 `controllers/*.svg`, the 6 `dj-software/*.svg`.
  This keeps the bitrot gate scoped — it never fails on an asset it does not own.

## Deviations from Plan

### Rule-1 Auto-fixes

1. **opt_out globs → concrete file paths.** The plan's opt_out listed directory
   globs (`screenshots/*.png`, `controllers/*.svg`, `dj-software/*.svg`). The
   schema-pin test asserts each opt_out path is an *existing file*, which a glob
   string is not. Expanded to the 27 concrete paths on disk today — identical
   scope, test-compatible. Wave 4 (which reads this manifest) sees real paths.
2. **asset-bitrot.yml comment reworded.** The plan's acceptance gate
   `grep -c pull_request_target == 0` tripped on the explanatory comment
   "NOT pull_request_target". Reworded to "the plain trigger, never the
   *_target variant" → literal string count is now 0; YAML re-parse confirms the
   posture (on=push+pull_request, permissions.contents:read). Same hit + same
   resolution as Phase 69-04.

### Authentication Gates

None.

## Cardinal Invariant Confirmation

- `git diff --stat HEAD~2..HEAD -- src/vibemix/` → **EMPTY** (zero reaction-path touch).
- `git diff --stat HEAD~2..HEAD -- pyproject.toml uv.lock` → **EMPTY** (zero new Python deps; PyYAML is a pre-existing transitive dep).
- `asset-bitrot.yml` validates as YAML; the regenerator is a clean no-op at empty-assets wave (`git diff --exit-code docs/assets/` exits 0).

## Baseline

`4207 passed / 26 skipped / 4 xpassed / 2 failed` in 217.15s (default grid,
`PYTHONPATH=src python3 -m pytest -q`). The +6 are `test_asset_manifest_shape.py`.
The 2 failures are the **pre-existing** Phase 68
`test_readme_feature_matrix_sync.py` AUTO-GEN drift (documented in
`.planning/phases/69-oss-fully-integrated/deferred-items.md`) — NOT a Phase 70
regression; I touched neither the test nor its README inputs.

## Self-Check: PASSED

- `docs/assets/MANIFEST.yaml` — FOUND
- `tests/repo/test_asset_manifest_shape.py` — FOUND
- `scripts/regenerate_assets.sh` — FOUND (executable)
- `.github/workflows/asset-bitrot.yml` — FOUND
- Commit `ad9fff3` — FOUND
- Commit `6f82170` — FOUND

## EXECUTION COMPLETE
