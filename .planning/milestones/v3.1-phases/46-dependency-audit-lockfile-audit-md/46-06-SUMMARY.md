---
phase: 46-dependency-audit-lockfile-audit-md
plan: 06
status: complete
commit: 6f094a8
requirements: [DEPS-09, DEPS-10]
---

# Plan 46-06 Summary — README dep-health badges + 4-ecosystem Dependabot

## What shipped

- `README.md` — 4 new dep-health badges in a centered `<p>` block under the existing badge row:
  - uv lock status (links to dep-audit.yml workflow)
  - cargo-deny (links to dep-audit.yml)
  - npm-audit (links to dep-audit.yml)
  - CycloneDX SBOM (links to sbom.yml)
  - Uses `bravoh/vibemix` org/repo (canonical OSS handle per existing badge block at line 32-36).
- `.github/dependabot.yml` — 4 ecosystem entries (pip / cargo / npm / github-actions), weekly Monday 09:00 Europe/Istanbul, security-only majors (each ecosystem ignores `version-update:semver-major`), no auto-merge, per-ecosystem open-pull-requests-limit: 5 + label + commit-message prefix.
- `.github/workflows/dep-audit.yml` — added top-level `concurrency:` block with `cancel-in-progress: true` group `dep-audit-${{ github.ref }}`.
- `tests/audit/test_readme_badges.py` (4 tests) + `tests/audit/test_dependabot_config.py` (7 tests).

## Verification

- `uv run pytest tests/audit/ --tb=short` — **45 passed, 1 xfailed** (the expected pinact deferral from Plan 05).
- `uv run python scripts/launch/check_no_ai_slop.py --audit-md` — 10 files scanned, 0 slop hits (README + AUDIT.md + dep_ratings.yaml + 4 scripts/audit/ files + 3 other scripts/audit/*.sh files now in scope).
- `.github/workflows/dep-audit.yml` has 7 jobs + `concurrency` block + `workflow_dispatch` trigger.
- `.github/dependabot.yml` parses with 4 ecosystem entries.

## Deviations from plan

None.

## Kaan-action surface

(Inherited from Plan 04 and Plan 05 — see those summaries.)

- **Plan 04**: `livekit-plugins-openai` cull is CULL-BLOCKED (used by `src/vibemix/agent/tts_chain.py`); follow-up refactor phase needed.
- **Plan 05**: Mechanical pinact `--apply` deferred to CI (no pinact binary on the local executor); first PR-triggered run of `dep-audit.yml::pinact-audit` will surface any remaining tag refs.

## Files touched

```
README.md                                (+10 lines, 4 dep-health badges)
.github/dependabot.yml                   (new, 80 lines, 4 ecosystems)
.github/workflows/dep-audit.yml          (+5 lines, concurrency block)
tests/audit/test_readme_badges.py        (new, 4 tests)
tests/audit/test_dependabot_config.py    (new, 7 tests)
```

Commit: `6f094a8`
