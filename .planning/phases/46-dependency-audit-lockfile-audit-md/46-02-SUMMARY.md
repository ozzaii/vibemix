---
phase: 46-dependency-audit-lockfile-audit-md
plan: 02
status: complete
commit: aaf8612
requirements: [DEPS-02, DEPS-03]
---

# Plan 46-02 Summary — cargo-deny GPL ban + npm-audit PR comment

## What shipped

- `tauri/src-tauri/deny.toml` — added `[licenses].deny` block with full GPL family (GPL-2.0/3.0-only/-or-later, AGPL-3.0-only/-or-later, LGPL-2.1/3.0-only/-or-later). Existing `allow` list preserved byte-identical.
- `.github/workflows/dep-audit.yml` — appended 2 jobs (`cargo-deny` + `npm-audit-pr-comment`); extended `paths:` triggers to include Cargo.toml/Cargo.lock/deny.toml/package.json/package-lock.json.
- `scripts/audit/npm_audit_pr_comment.sh` — runs `npm ci` (frozen-lockfile) + `npm audit --omit dev`, posts formatted PR comment, hard-fails on HIGH/CRITICAL.
- `tests/audit/test_deny_toml_policy.py` — 6 static-policy assertions pinning allowlist/denylist/3-job workflow shape/cargo-deny v0.16.1 pin.

## Verification

- `uv run python -c "import tomllib; ... 'deny.toml'"` — full GPL family present in `[licenses].deny`.
- `uv run pytest tests/audit/test_deny_toml_policy.py` — 6/6 passed.
- `bash -n scripts/audit/npm_audit_pr_comment.sh` — clean syntax.
- `.github/workflows/dep-audit.yml` parses with 3 jobs (uv-regen-diff + cargo-deny + npm-audit-pr-comment); npm-audit job has per-job `pull-requests: write` permission.

## Deviations from plan

None.

## Kaan-action surface

None.

## Files touched

```
.github/workflows/dep-audit.yml          (+101 lines, 2 new jobs)
scripts/audit/npm_audit_pr_comment.sh    (new, executable, 50 lines)
tauri/src-tauri/deny.toml                (+15 lines GPL deny block)
tests/audit/test_deny_toml_policy.py     (new, 78 lines, 6 tests)
```

Commit: `aaf8612`
