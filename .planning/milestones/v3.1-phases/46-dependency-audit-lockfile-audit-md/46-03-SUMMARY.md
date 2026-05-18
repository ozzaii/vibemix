---
phase: 46-dependency-audit-lockfile-audit-md
plan: 03
status: complete
commit: 8e22569
requirements: [DEPS-04, DEPS-05]
---

# Plan 46-03 Summary — docs/AUDIT.md + generator + freshness gate

## What shipped

- `docs/AUDIT.md` — generated single source of truth, 10,549 bytes, 5 H2 sections (Python / Rust / JavaScript / Decisions / GitHub Actions) + rubric preamble (🟢/🟡/🔴 with definitions).
- `scripts/audit/dep_ratings.yaml` — hand-authored ratings + rationale for 38 direct deps (Python 35 / Rust 17 / JS 16 — counts after extending beyond plan's initial 18+5+15 to cover pyproject.toml's full surface).
- `scripts/audit/gen_audit_md.py` — deterministic generator, `--check` mode for CI drift detection. Reads pyproject.toml + uv.lock + Cargo.toml + package.json + dep_ratings.yaml.
- `scripts/audit/check_audit_freshness.sh` — git-log-based staleness comparator (not filesystem mtime); references all 6 lockfiles + both audit artifacts.
- `.github/workflows/dep-audit.yml` — extended to 5 jobs (added `audit-md-freshness` + `audit-md-gen-check`); `audit-md-freshness` uses `fetch-depth: 0` for full git history.
- `.github/workflows/model-literal-check.yml` — extended `paths:` trigger to include `docs/AUDIT.md`, `scripts/audit/**`, `docs/dep-opportunities/**`.
- `scripts/release/check_no_hardcoded_model.sh` — `SCOPE_DIRS` array (4 paths) replaces single `SCOPE_DIR`; scans .py/.md/.yaml/.yml/.sh/.json files.
- `scripts/launch/check_no_ai_slop.py` — new `--audit-md` mode runs blocklist + `\bdeeply\s+\w+` regex against docs/AUDIT.md + scripts/audit/** + docs/dep-opportunities/** + README.md.
- `tests/audit/test_audit_md_generator.py` + `test_audit_freshness_gate.py` — 11 assertions total.

## Verification

- `uv run python scripts/audit/gen_audit_md.py` — wrote 10,549 bytes, 0 MISSING ratings.
- `uv run python scripts/audit/gen_audit_md.py --check` — idempotent (in sync).
- `bash scripts/release/check_no_hardcoded_model.sh` — clean across all 4 scope paths.
- `uv run python scripts/launch/check_no_ai_slop.py --audit-md` — 8 files scanned, 0 slop hits.
- `uv run pytest tests/audit/test_audit_md_generator.py tests/audit/test_audit_freshness_gate.py` — 11/11 passed.

## Deviations from plan

- **dep_ratings.yaml extended beyond plan's initial scope** — pyproject.toml has more deps than the plan's draft anticipated (mss/pillow/pyjwt/jsonschema/websockets/python-dotenv/pyobjc-*/pyaudiowpatch/pywin32/winsdk/sqlite-vec/etc.). All added with ratings + rationale to keep `0 MISSING`. Same for Rust (tauri-plugin-fs/shell/store/process/updater/global-shortcut/positioner, tokio-tungstenite, futures-util, tracing, dirs-next, file-rotate) and JS (vite-plugin-static-copy).
- **Generator runs successfully end-to-end** — no docker dependency for AUDIT.md generation (only the uv.lock regen needs docker, which is Plan 01's deferred CI step).

## Kaan-action surface

None.

## Files touched

```
docs/AUDIT.md                                (new, generated)
scripts/audit/dep_ratings.yaml               (new, 38 deps + decisions slot)
scripts/audit/gen_audit_md.py                (new, 220+ lines)
scripts/audit/check_audit_freshness.sh       (new, executable)
.github/workflows/dep-audit.yml              (+30 lines, 2 new jobs)
.github/workflows/model-literal-check.yml    (+8 lines, paths extended)
scripts/release/check_no_hardcoded_model.sh  (rewrote scan loop, SCOPE_DIRS array)
scripts/launch/check_no_ai_slop.py           (+60 lines, --audit-md mode)
tests/audit/test_audit_md_generator.py       (new, 7 tests)
tests/audit/test_audit_freshness_gate.py     (new, 4 tests)
```

Commit: `8e22569`
