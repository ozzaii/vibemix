---
phase: 46-dependency-audit-lockfile-audit-md
plan: 05
status: complete-with-deferral
commit: ca7ff4f
requirements: [DEPS-07]
---

# Plan 46-05 Summary — pinact SHA-pin config + deferred rewrite

## What shipped

- `.pinact.yaml` — pinact v3.x config with `is_full_version: true`, `use_major_version_tag: false`, file patterns covering `.github/workflows/*.{yml,yaml}` and `.github/actions/*/action.{yml,yaml}`.
- `scripts/audit/run_pinact.sh` — bash wrapper with `--check` (CI gate) and `--apply` (local mechanical rewrite) modes; inline pinact 3.3.0 install (OS+arch detection + GitHub release tarball fetch).
- `.github/workflows/dep-audit.yml` — appended `pinact-audit` job (now 7 jobs total); runs `bash scripts/audit/run_pinact.sh --check`.
- `tests/audit/test_pinact_pinning.py` — 4 assertions: workflow dir has >=15 files, .pinact.yaml exists, run_pinact.sh exists+executable, every `uses:` SHA-pinned (LAST marked xfail with `strict=False` reason="DEPS-07 mechanical pinact --apply deferred to CI").

## Verification

- `bash -n scripts/audit/run_pinact.sh` — clean syntax.
- `uv run pytest tests/audit/test_pinact_pinning.py -v` — 3 passed + 1 xfailed (the SHA-pinning assertion, expected).
- `.github/workflows/dep-audit.yml` parses with 7 jobs.

## Deviations from plan

- **Mechanical pinact `--apply` rewrite DEFERRED**: pinact binary not available on the local executor (no `pinact` in PATH, no Go toolchain to `go install`). Per Plan 05 Task 3 fallback path + `feedback_autonomous_no_grey_area_pause`: committed .pinact.yaml + run_pinact.sh + audit job + xfail test; CI will run `pinact --check` on the first PR and either pass clean (if SHAs already pinned) or surface remaining tag refs for follow-up `pinact --apply`.
- xfail test uses `strict=False` so a future `pinact --apply` pass that flips it green doesn't surprise-fail in `XPASS` mode.

## Kaan-action surface

- **DEPS-07 mechanical pinact rewrite DEFERRED to CI**. Two paths to close:
  1. Local: `brew install pinact` then `bash scripts/audit/run_pinact.sh --apply` — review the diff (~15+ workflow files, mostly mechanical SHA churn) and commit.
  2. CI-discovery: first PR run of `dep-audit.yml::pinact-audit` either passes clean (if upstream actions have stable SHAs that match) or surfaces the exact tag refs needing rewrite. Use `--apply` locally afterward and amend the failing PR.

## Files touched

```
.pinact.yaml                          (new, 22 lines)
scripts/audit/run_pinact.sh           (new, executable, 50 lines)
.github/workflows/dep-audit.yml       (+11 lines, pinact-audit job)
tests/audit/test_pinact_pinning.py    (new, 4 tests with 1 xfail)
```

Commit: `ca7ff4f`
