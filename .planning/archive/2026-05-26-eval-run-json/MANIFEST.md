# Eval Run JSON Archive — 2026-05-26

This archive records cleanup of stale ignored load-test artifacts.

## Archived Locally

- `.planning/archive/2026-05-26-eval-run-json.zip`
- Source pattern: `.planning/eval-runs/loadtest_*.json`
- Count: 215 JSON files
- Name range: `loadtest_1779187981.json` through `loadtest_1779805539.json`
- Size before archive: about 860 KB

## Active Path Preserved

`.planning/eval-runs/.gitkeep` remains in place so tools that default to
`.planning/eval-runs/` still have a valid artifact directory. Fresh load-test
artifacts can be regenerated with `scripts/dayzero/proxy_load_test.py`.

The release gate in `scripts/release/check_gate.sh` evaluates nightly run
directories, not these flat ignored `loadtest_*.json` files. Removing the stale
flat JSONs keeps the active gate input cleaner.
