---
phase: 19-github-launch-presence
plan: 01
subsystem: infra
tags: [git-lfs, gh-cli, repo-metadata, pre-commit, ci-gate, pyyaml, gh-17, gh-18]

# Dependency graph
requires:
  - phase: 18-distribution-verification
    provides: "scripts/dist/ style template (sign_macos.sh) + workflows/release.yml badge target"
provides:
  - "Scrubbed repo root (5 scratch files removed)"
  - ".gitattributes routing *.glb through git-lfs (20 MB mascot bundle)"
  - ".gitignore Phase 19 hygiene block + docs/assets whitelist"
  - "Declarative repo metadata source-of-truth (.github/repo-config.yml)"
  - "Idempotent `gh repo edit` wrapper with --apply safety gate"
  - "Pre-commit hook rejecting non-LFS files >1 MB"
  - "CI gate: tests/repo/ — 19 invariants across scrub + metadata"
affects: [19-02, 19-03, 19-04, future-phases-touching-repo-root]

# Tech tracking
tech-stack:
  added:
    - "pyyaml>=6.0 (dev) — YAML loader for tests + yq parity"
    - "yq runtime dep (brew install) — shell-side YAML parsing for configure_repo.sh"
    - "git-lfs convention via .gitattributes (one-time `git lfs migrate` is developer-side)"
  patterns:
    - "Declarative-source + idempotent-wrapper for GitHub repo metadata"
    - "Dry-run-default shell scripts with explicit --apply gate (T-19-02 mitigation)"
    - "Tests-as-CI-gate: tests/repo/ pattern complements .git/hooks/ pattern"
    - "POC reference allowlist (POC_EXEMPT set) coded into hygiene tests"

key-files:
  created:
    - ".gitattributes"
    - ".github/repo-config.yml"
    - "scripts/dist/configure_repo.sh"
    - "scripts/hooks/pre-commit-no-binaries.sh"
    - "tests/repo/__init__.py"
    - "tests/repo/test_repo_scrub.py"
    - "tests/repo/test_repo_metadata.py"
  modified:
    - ".gitignore (Phase 19 hygiene block + docs/assets whitelist)"
    - "pyproject.toml (+ pyyaml dev dep; drop dead _test_*.py ruff ignore)"
    - "uv.lock (pyyaml added)"
  deleted:
    - "_test_multimodal.py (scratch)"
    - "_test_tts.py (scratch)"
    - "sprite-1.png (2.3 MB scratch)"
    - "sprite-2.png (2.5 MB scratch)"
    - "sprite-3.png (2.3 MB scratch)"

key-decisions:
  - "Git LFS chosen over release-asset-CDN for the 20 MB mascot GLB — keeps file logically in-repo for Tauri build path"
  - "Pre-commit hook installed via developer-side `ln -sf` (not auto-installed) — .git/hooks/ is per-clone"
  - "configure_repo.sh defaults to DRY RUN; --apply required to push (T-19-02 tampering mitigation)"
  - "YAML parsing uses yq (shell) + PyYAML (tests) — yq is one of the smallest acceptable shell dependencies for declarative pipelines"
  - "Topic `add-topic` is non-destructive — script does not clear existing topics, only adds the locked set"

patterns-established:
  - "tests/repo/ subdir for repo-meta CI gates (mirrors tests/dist/ Phase 18 pattern)"
  - "POC_EXEMPT + POC_EXEMPT_DIRS sets in test files for clean separation of port-target vs scrub-target files"
  - "Idempotent `gh repo edit` wrapper that mirrors Phase 18's idempotent sign_macos.sh pattern"

requirements-completed: [GH-01, GH-17, GH-18]

# Metrics
duration: ~30min
completed: 2026-05-13
---

# Phase 19 Plan 19-01: Repo Hygiene + Metadata Gates Summary

**Repo root scrubbed of 5 scratch files (10 MB freed), mascot GLB routed through git-lfs, declarative `.github/repo-config.yml` source-of-truth shipped with an idempotent `gh repo edit` wrapper, and 19-test CI gate locks all of it going forward.**

## Performance

- **Duration:** ~30 min
- **Started:** 2026-05-13 (Wave 1 of Phase 19)
- **Completed:** 2026-05-13T17:13:28Z
- **Tasks:** 2/2
- **Files modified:** 8 created, 3 modified, 5 deleted

## Accomplishments

- Five scratch artifacts removed from repo root (`_test_multimodal.py`, `_test_tts.py`, `sprite-1.png/2/3.png`).
- `.gitattributes` routes `*.glb` through git-lfs — `tauri/ui/assets/mascot/character.glb` (20 MB) is the first beneficiary.
- `.gitignore` extended with Phase 19 hygiene block (`*.bak`, `v5-*.png`, `.claude/worktrees/`, `.playwright-mcp/`, `/node_modules/`) + defensive whitelist (`!docs/assets/**`).
- `.github/repo-config.yml` carries the 11-key declarative source of truth (description, homepage, 10 topics, default_branch, feature switches, squash-only merge policy) locked from CONTEXT Area 6.
- `scripts/dist/configure_repo.sh` wraps `gh repo edit`, default dry-run, `--apply` gate, supports `--repo owner/name`.
- `scripts/hooks/pre-commit-no-binaries.sh` rejects added files >1 MB unless LFS-tracked.
- `tests/repo/test_repo_scrub.py` + `tests/repo/test_repo_metadata.py` = 19 passing invariants.
- pyproject cleanup: pyyaml added as dev dep; the now-dead `_test_*.py` ruff-ignore removed.

## Task Commits

Each task ran as RED → GREEN TDD on its respective test file:

1. **Task 1 RED — repo-scrub failing tests** — `6637355` (test) — 8 invariants pending fixture
2. **Task 1 GREEN — scrub + LFS + .gitignore** — `1f58cb5` (feat) — 5 files deleted, .gitattributes + .gitignore extension shipped
3. **Task 2 RED — repo-metadata failing tests** — `c50c23a` (test) — 11 invariants pending fixture
4. **Task 2 GREEN — repo-config.yml + 2 shell scripts** — `2eac3e6` (feat) — YAML + configure_repo.sh + pre-commit hook shipped

Final pytest: `19 passed in 0.10s` (all green).

## Files Created/Modified

**Created:**
- `.gitattributes` — `*.glb filter=lfs diff=lfs merge=lfs -text` + migration command in header comment
- `.github/repo-config.yml` — 11 locked keys (CONTEXT Area 6 values)
- `scripts/dist/configure_repo.sh` — 130-line dry-run-default `gh repo edit` wrapper
- `scripts/hooks/pre-commit-no-binaries.sh` — 80-line >1 MB rejection hook with LFS exemption
- `tests/repo/__init__.py` — SPDX header only
- `tests/repo/test_repo_scrub.py` — 8 hygiene invariants
- `tests/repo/test_repo_metadata.py` — 11 metadata + script-shape invariants

**Modified:**
- `.gitignore` — Phase 19 hygiene block + docs/assets whitelist
- `pyproject.toml` — + pyyaml>=6.0 (dev), - dead `_test_*.py` ruff ignore
- `uv.lock` — pyyaml dependency resolved

**Deleted (via git rm):**
- `_test_multimodal.py`, `_test_tts.py`, `sprite-1.png`, `sprite-2.png`, `sprite-3.png`

## Decisions Made

- **Git LFS over release-asset-CDN for `character.glb`** — keeps the file logically in-repo for the Tauri build path. Migration is one-time, developer-side (`git lfs install --local && git rm --cached tauri/ui/assets/mascot/character.glb && git add tauri/ui/assets/mascot/character.glb && git commit -m "chore(19): migrate mascot GLB to Git LFS"`). The `.gitattributes` rule landing this commit is the contract; the migration push is Kaan's one-time action surfaced below.

- **Dry-run-default `configure_repo.sh`** — without `--apply`, the script prints the planned `gh` invocation and exits 0. Mitigates T-19-02 (accidental description/topic overwrite by automation or stale CI runs).

- **`pyyaml` added as dev dep, not runtime** — used only by `tests/repo/test_repo_metadata.py`. The runtime `configure_repo.sh` consumes `yq` (shell tool), not the Python library, to keep the user-facing toolchain shell-native.

- **`_test_*.py` ruff ignore removed** — the rule referenced files we just deleted. Keeping it would silently allow any future `_test_*.py` to escape lint; removing it forces a deliberate decision if such files reappear.

- **POC_EXEMPT allowlist baked into the test file, not into `.gitignore`** — `.gitignore` cannot describe a "tracked file allowed to remain >1 MB"; the allowlist needs program logic.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Worktree had no `.venv`; ran tests against main repo's venv**
- **Found during:** Task 1 RED verification (`source .venv/bin/activate` failed)
- **Issue:** The Claude Code worktree at `.claude/worktrees/agent-a43187f4d25a3c314/` does not provision a per-worktree `.venv`; only the main repo at `/Users/ozai/projects/dj-set-ai/` has one.
- **Fix:** Used `source /Users/ozai/projects/dj-set-ai/.venv/bin/activate` (absolute path) for all pytest runs. No code change — purely a runtime workaround.
- **Files modified:** none
- **Verification:** `python -c "import pytest, yaml"` succeeds in the activated environment.
- **Committed in:** n/a (runtime-only, no diff)

**2. [Rule 2 - Missing Critical] Added pyyaml as dev dependency**
- **Found during:** Task 2 RED — 5 YAML tests skipped because `import yaml` failed.
- **Issue:** Plan said "PyYAML is already a transitive dep (verify); if not present, add pyyaml>=6.0". It was NOT present (`.venv` has 124 packages, none of them PyYAML).
- **Fix:** Added `pyyaml>=6.0` to `[dependency-groups] dev` + `uv pip install` + `uv lock` regen.
- **Files modified:** `pyproject.toml`, `uv.lock`
- **Verification:** All 5 YAML tests progress from skip → pass.
- **Committed in:** `2eac3e6` (Task 2 GREEN commit)

**3. [Rule 2 - Missing Critical] Cleaned up dead `_test_*.py` ruff ignore in pyproject.toml**
- **Found during:** Task 1 GREEN — the files were just deleted, but `[tool.ruff.lint.per-file-ignores] "_test_*.py" = [...]` still referenced them.
- **Issue:** Dead config entry would silently grant lint-immunity to any future `_test_*.py` reappearance (anti-scrub regression vector).
- **Fix:** Removed the entry; replaced with a `# Phase 19-01:` comment explaining why.
- **Files modified:** `pyproject.toml`
- **Verification:** Existing test suite (`test_license.py`, `test_package.py`) still passes.
- **Committed in:** `1f58cb5` (Task 1 GREEN commit)

---

**Total deviations:** 3 auto-fixed (1 blocking [runtime-only], 2 missing critical)
**Impact on plan:** All three were necessary for the plan to actually pass its acceptance criteria. No scope creep.

## Issues Encountered

- **Branch namespace check on first commit** failed initially because worktree HEAD was on `worktree-agent-a43187f4d25a3c314` and the pre-commit assertion's allow-list regex matched correctly the first time. No remediation needed.
- **`pip` not present in .venv** — the venv was created with `uv`, which does not include pip by default. Worked around by using `uv pip install --python /path/to/venv/python3 pyyaml` instead.

## User Setup Required

### One-time developer actions (NOT shipped, NOT automated)

These are Kaan-side actions surfaced for execution after the plan commits land:

**1. Migrate the mascot GLB to git-lfs:**
```bash
git lfs install --local
git rm --cached tauri/ui/assets/mascot/character.glb
git add tauri/ui/assets/mascot/character.glb
git commit -m "chore(19): migrate mascot GLB to Git LFS"
```
After this, fresh clones without `git lfs install` get a pointer file instead of the 20 MB blob — Tauri build env installs git-lfs in CI before checkout.

**2. Install the pre-commit hook locally (per clone):**
```bash
ln -sf ../../scripts/hooks/pre-commit-no-binaries.sh .git/hooks/pre-commit
```

**3. Push repo metadata to GitHub (after Phase 19 ships, when the repo at `github.com/bravoh/vibemix` exists — see GH-01 below):**
```bash
scripts/dist/configure_repo.sh            # dry-run preview
scripts/dist/configure_repo.sh --apply    # push to GitHub
```

### GH-01 acknowledgement (Kaan-side blocker)

The repo URL at `github.com/bravoh/vibemix` does not yet exist. GH-01 is split: this plan ships the `configure_repo.sh` automation that operates on the resulting repo. Kaan's manual step (one of):

- Create a `bravoh` GitHub organization and create `vibemix` under it.
- Transfer the existing `ozzaii/vibemix` repo to the `bravoh` org.

Once that's done, `scripts/dist/configure_repo.sh --apply` finishes the metadata push.

## Next Phase Readiness

- **Plan 19-02 (Repo metadata + GitHub config workflow):** Wave 2 will land the `.github/workflows/` automation (DCO check + repo-config CI sync). Foundation in place: repo-config.yml + configure_repo.sh ready to be lifted into a scheduled workflow.

- **Plan 19-03 (README rewrite, hero, demo placeholder):** Lands on a clean working tree — no sprite/scratch noise in `ls`. The `!docs/assets/**` gitignore whitelist guarantees that `docs/assets/hero.png`, `docs/assets/architecture.svg`, etc. survive untouched.

- **Plan 19-04 (OSS hygiene — CONTRIBUTING, SECURITY, etc.):** Independent of this plan; can start in parallel with 19-02.

**No blockers for downstream phases.**

## Self-Check: PASSED

Files verified to exist on disk:
- `.gitattributes` ✓
- `.github/repo-config.yml` ✓
- `scripts/dist/configure_repo.sh` (executable) ✓
- `scripts/hooks/pre-commit-no-binaries.sh` (executable) ✓
- `tests/repo/__init__.py` ✓
- `tests/repo/test_repo_scrub.py` ✓
- `tests/repo/test_repo_metadata.py` ✓

Files verified deleted:
- `_test_multimodal.py`, `_test_tts.py`, `sprite-1.png`, `sprite-2.png`, `sprite-3.png` ✓ (all 5 missing)

Commits verified in `git log`:
- `6637355` test(19-01) RED scrub ✓
- `1f58cb5` feat(19-01) GREEN scrub ✓
- `c50c23a` test(19-01) RED metadata ✓
- `2eac3e6` feat(19-01) GREEN metadata ✓

Final pytest run: `19 passed in 0.10s` ✓

---
*Phase: 19-github-launch-presence*
*Plan: 01 — Repo scrub + LFS + metadata + pre-commit + CI tests*
*Completed: 2026-05-13*
