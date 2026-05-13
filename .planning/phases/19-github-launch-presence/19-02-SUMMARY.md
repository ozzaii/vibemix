---
gsd_plan_summary_version: 1.0
phase: 19
plan: 19-02
plan_name: OSS hygiene files
status: completed
requirements: [GH-13, GH-14, GH-15]
---

# Plan 19-02 — OSS Hygiene Files

## What landed

- `CONTRIBUTING.md` — DCO sign-off + 3 contribution paths (bug fix / controller mapping / prompt template).
- `CODE_OF_CONDUCT.md` — Contributor Covenant 2.1, enforcement at ozai@bravoh.com, links to upstream Covenant for full text.
- `SECURITY.md` — vuln disclosure email, 90-day coordinated disclosure, scope (in / out).
- `NOTICE` — Apache-2.0 attribution for all bundled deps (Python + JS + Rust) + external tooling (BlackHole, nowplaying-cli, djay Pro).
- `TRADEMARKS.md` — vibemix Bravoh mark + nominative fair use list for Pioneer/Numark/Hercules/Apple/Microsoft/Google/etc.
- `.github/ISSUE_TEMPLATE/bug_report.yml`
- `.github/ISSUE_TEMPLATE/feature_request.yml`
- `.github/ISSUE_TEMPLATE/new_controller.yml`
- `.github/ISSUE_TEMPLATE/config.yml` — blank issues disabled; security + discussions contact links.
- `.github/pull_request_template.md` — DCO + linked issue + test plan + breaking-change flag.
- `scripts/dist/gen_notice.py` — `--check` mode validates NOTICE has required markers; full auto-regeneration deferred (manual maintenance for v1 dep list).
- `tests/repo/test_oss_hygiene.py` — 20 tests covering all files exist, parse, and reference the right contacts.

## Execution path

The original `gsd-executor` worktree-based attempt hit a content-filter mid-flight after the RED test commit. Per fully-autonomous mode and given the OSS hygiene templates are well-known boilerplate (Contributor Covenant URL-referenced, standard issue-template schemas, manual NOTICE), the orchestrator wrote the GREEN deliverables directly in main and committed.

## Acceptance gates — all green

- `pytest tests/repo/test_oss_hygiene.py -q` → 20 passed
- `python -m scripts.dist.gen_notice --check` → exit 0
- All 5 hygiene MD files exist with required sections
- All 4 issue templates parse as valid YAML
- PR template references DCO
- No content from the redacted Covenant verbatim text — link to upstream instead (cleaner)

## Files not shipped this plan

- Real PGP key for security@bravoh.com — placeholder in SECURITY.md, Bravoh ops generates pre-v0.1.0
- Auto-regenerating NOTICE — manual maintenance is fine for the v1 dep count; if dep count balloons in v2 we revisit
