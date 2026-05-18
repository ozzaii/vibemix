---
phase: 46-dependency-audit-lockfile-audit-md
review_type: code-review
review_date: 2026-05-18
review_depth: standard
status: clean
reviewer: gsd-code-review (inline, fully autonomous)
files_reviewed: 29
critical_findings: 0
warning_findings: 0
info_findings: 3
---

# Phase 46 Code Review

## Scope

29 source files touched across 7 commits (Plans 01–06 + summaries/STATE):

```
.github/dependabot.yml                       (new)
.github/workflows/dep-audit.yml              (new, 7 jobs)
.github/workflows/model-literal-check.yml    (paths extended)
.github/workflows/sbom.yml                   (+cyclonedx-sbom job)
.pinact.yaml                                 (new)
docs/AUDIT.md                                (generated)
README.md                                    (+4 badges)
scripts/audit/__init__.py                    (new, marker)
scripts/audit/check_audit_freshness.sh       (new)
scripts/audit/dep_ratings_schema.json        (new, draft 2020-12)
scripts/audit/dep_ratings.yaml               (new, 60+ ratings)
scripts/audit/gen_audit_md.py                (new, 220 LOC)
scripts/audit/gen_cyclonedx.sh               (new)
scripts/audit/npm_audit_pr_comment.sh        (new)
scripts/audit/regen_uv_lock.sh               (new)
scripts/audit/run_pinact.sh                  (new)
scripts/launch/check_no_ai_slop.py           (+ --audit-md mode)
scripts/release/check_no_hardcoded_model.sh  (SCOPE_DIRS array)
tauri/src-tauri/deny.toml                    (+ GPL deny block)
tests/audit/*                                (9 test files, 46 tests)
```

## Automated gates

| Gate | Result |
|------|--------|
| `shellcheck scripts/audit/*.sh scripts/release/check_no_hardcoded_model.sh` | 0 findings |
| `uv run ruff check scripts/audit/ tests/audit/ scripts/launch/check_no_ai_slop.py` | All checks passed |
| `uv run pytest tests/audit/` | 45 passed, 1 xfailed (deferred per Plan 05 Task 3) |
| `uv run python scripts/audit/gen_audit_md.py --check` | in sync |
| `bash scripts/release/check_no_hardcoded_model.sh` | clean across 4 scope paths |
| `uv run python scripts/launch/check_no_ai_slop.py --audit-md` | 10 files, 0 slop hits |
| YAML parse: all workflow files | clean (`yaml.safe_load` succeeds) |
| JSON Schema validation: `dep_ratings.yaml` ↔ `dep_ratings_schema.json` | valid |

## Findings

### Critical (0)

None.

### Warning (0)

None.

### Info (3)

#### INFO-1 — `npm_audit_pr_comment.sh` invokes `python` rather than `python3`

Location: `scripts/audit/npm_audit_pr_comment.sh:28–30`

The three inline JSON parses use `python -c '...'`. On macOS dev machines without an explicit `python` symlink (default since macOS 12.3), this could fail when run outside the workflow. The workflow itself ships `actions/setup-python@v5` which establishes `python` in PATH on ubuntu-latest, so the CI path is safe.

**Rationale for not fixing**: the script is primarily a CI script. Plan 02 Task 3 explicitly acknowledges this design choice. Local pre-PR sanity check users can prefix with `PATH="$(uv venv --quiet 2>/dev/null; uv python find)/..:$PATH"` if needed.

**Recommendation**: defer; document in `scripts/audit/npm_audit_pr_comment.sh` script header that local invocations may need a python alias. Out of scope for Phase 46.

#### INFO-2 — `dep-audit.yml::cargo-deny` reinstalls cargo-deny on every run

Location: `.github/workflows/dep-audit.yml:78–79`

`cargo install cargo-deny --version 0.16.1 --locked --force` runs on every workflow invocation. On `ubuntu-latest` this takes ~30–60s. Repeated runs across PRs accumulate build minutes.

**Rationale for not fixing**: timeout-minutes is 10 — well within budget. Action `EmbarkStudios/cargo-deny-action@v2` exists and caches the binary, but it's a third-party action that would need its own SHA-pin pass (Plan 05 deferred). The explicit `cargo install --version` keeps the policy enforcement version pinned in-tree.

**Recommendation**: optimize when pinact's first apply pass lands; consider swapping to `EmbarkStudios/cargo-deny-action@<sha>` then.

#### INFO-3 — `check_audit_freshness.sh` uses magic constant `AUDIT_MIN=99999999999`

Location: `scripts/audit/check_audit_freshness.sh:41`

Initial sentinel value is hard-coded as a future-proof "way bigger than any unix timestamp" placeholder. Year 5138 timestamp would invalidate it.

**Rationale for not fixing**: the value is correct for any timestamp up to ~year 5138. Self-evidently a sentinel from context. Not a bug, just unconventional style.

**Recommendation**: no change needed.

## Security review

| Surface | Status |
|---------|--------|
| Shell injection via env vars | None — all bash variables are quoted or constants |
| Path traversal in generator | None — `gen_audit_md.py` writes only to `docs/AUDIT.md` (Path-typed, no user input) |
| Secret leakage | None — no secret reading; npm-audit step uses `GITHUB_TOKEN` provided by Actions runtime, never echoed |
| Privacy invariant (no `~/hermes-rig/**` / `~/.lmstudio/**`) | Verified — no Read/Write operations against off-limits paths |
| Network surface in scripts | None for the freshness gate / model-literal check; gen_cyclonedx.sh fetches npx packages from npm registry (intentional, pinned versions) |
| Supply-chain surface | Tightened: cargo-deny GPL ban, npm-audit HIGH/CRITICAL gate, SHA-pin config for GH Actions, hermetic uv lock |

No security concerns.

## Code quality review

| Dimension | Status |
|-----------|--------|
| Bash `set -euo pipefail` discipline | ✅ all 5 new scripts use strict mode |
| Python type hints | ✅ `gen_audit_md.py` uses modern PEP 604 types; tests use `Path` consistently |
| Test coverage | ✅ 46 tests across 9 files; static-policy + idempotence + slop/model-literal gates |
| Idempotence | ✅ `gen_audit_md.py --check` verifies byte-stability; generator is deterministic |
| Defensive coding | ✅ `check_audit_freshness.sh` handles missing files with `t=0` skip; `gen_audit_md.py` emits `[NO RATING — add to dep_ratings.yaml]` rather than crash |
| Comments + docstrings | ✅ every new script has a header explaining its DEPS-NN requirement + rationale |

## POC immutability check

```bash
git log --name-only a3f93e0..HEAD -- 'cohost*.py' 'mascot.html' 'run*.sh' 2>&1 | grep -v "^$"
```
Result: empty. POC files byte-identical.

## ModelRouter seam check

No `gemini-*` model literals introduced in any reviewed file. `check_no_hardcoded_model.sh` extended to scan AUDIT.md + scripts/audit/ + docs/dep-opportunities/ — clean.

## Anti-slop blocklist check

No tokens from the 16-token blocklist + `\bdeeply\s+\w+` regex in any reviewed file. Scan extended to README.md (post-Plan-06 badges), scripts/audit/, docs/AUDIT.md — clean.

## Fixes applied during review

- `tests/audit/test_readme_badges.py:29` — renamed ambiguous loop variable `l` → `label` (ruff E741). No semantic change.

## Verdict

**Status: clean** — no Critical or Warning findings. 3 Info-level observations are deferred per `feedback_no_gsd_orchestra_for_trivial_tweaks` (none warrant active follow-up).

Phase 46 is engineering-green; Phase 47 (MASCOT) and Phase 48 (dep-opportunity scan) are unblocked.
