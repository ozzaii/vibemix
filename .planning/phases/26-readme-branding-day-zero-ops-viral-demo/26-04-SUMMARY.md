---
phase: 26
plan: "04"
subsystem: dayzero-ops / launch-tooling
tags: [load-test, healthz, watchdog, launch-ops, dry-run, deterministic-tests]
requires: []
provides:
  - scripts/dayzero/proxy_load_test.py (100 RPS × 5min smoke target)
  - scripts/dayzero/healthz_check.sh (foreground curl watchdog)
  - tests/scripts/test_dayzero.py (5 deterministic tests, no network)
affects: [Day-Zero ops runbook]
tech_stack_added: []
tech_stack_patterns:
  - httpx async client with HTTP/2 + Semaphore-bounded concurrency
  - Bash trap SIGINT/SIGTERM for clean watchdog shutdown
  - Linear-interpolated percentile (no numpy dependency in scripts/)
key_files_created:
  - scripts/dayzero/__init__.py
  - scripts/dayzero/proxy_load_test.py
  - scripts/dayzero/healthz_check.sh
  - tests/scripts/test_dayzero.py
key_files_modified: []
decisions:
  - "Both scripts ship with --dry-run mode for offline test + rehearsal. No real network calls in any test."
  - "proxy_load_test uses gaussian@200ms ± 50ms synthetic generator with 0.5% outliers + 1% errors. --dry-run-seed makes it deterministic for tests."
  - "Default budgets: p99 < 500ms AND error_rate < 1%. PASS exits 0, FAIL exits 1."
  - "healthz_check.sh dry-run schedule: every 3rd iteration returns 503, deterministic by construction (no RNG)."
  - "Stdlib + httpx only (proxy_load_test). No locust, no asyncio framework lock-in beyond what httpx requires."
  - "Discord setup, pre-seeded stars, and launch trigger remain Kaan-action (surfaced in KAAN-ACTION.md)."
metrics:
  duration_minutes: ~25
  completed_date: "2026-05-14"
  tasks_completed: 3
  files_created: 4
  files_modified: 0
  tests_added: 5
---

# Phase 26 Plan 04: Day-Zero Ops Scripts (proxy load test + healthz check)

One-liner: **Two Kaan-invoked Day-Zero ops scripts (`proxy_load_test.py` + `healthz_check.sh`) ship under `scripts/dayzero/` with deterministic `--dry-run` modes; 5 new tests pass, no regression to baseline.**

## What Was Done

### Task 1 — proxy_load_test.py

`scripts/dayzero/proxy_load_test.py` — locust-style load-test target for Bravoh's vibemix proxy.

**CLI surface:**
```
--target URL              (default: https://api.altidus.world/vibemix/healthz)
--rps N                   (default: 100)
--duration SECONDS        (default: 300)
--concurrency N           (default: 20)
--p99-budget-ms FLOAT     (default: 500)
--error-rate-budget FRAC  (default: 0.01)
--dry-run                 (no HTTP — synthesize samples)
--dry-run-seed N          (deterministic synthetic generator)
--json                    (machine-readable summary on stdout)
```

**Runtime path:**
- Live mode: `httpx.AsyncClient(http2=True)` + asyncio.Semaphore(concurrency), sleep-throttle to target RPS.
- Dry-run: gaussian@200ms ± 50ms generator, 0.5% chance of uniform(600-1200ms) outlier, 1% chance of synthetic 599 status.
- Verdict computed in `compute_verdict()`: linear-interpolated percentiles (sorted-list-based, no numpy), PASS if `p99 < budget AND error_rate < budget`, else FAIL.
- Exit code: 0 on PASS, 1 on FAIL.

**Stats reported:** min / median / p95 / p99 / max latency, success/error counts, error rate, total samples, budgets.

### Task 2 — healthz_check.sh

`scripts/dayzero/healthz_check.sh` — foreground curl watchdog.

**CLI surface:**
```
--target URL             (default: https://api.altidus.world/healthz)
--interval SECONDS       (default: 30)
--max-iterations N       (0 = infinite, default: 0)
--dry-run                (synthetic 1-in-3 non-200 schedule)
--alert-cmd CMD          (optional — run shell cmd on non-200)
```

**Output:**
- stdout: `[OK] iso=... target=... status=200 iteration=N`
- stderr: `[ALERT] iso=... target=... status=N iteration=N`
- stderr: `[SUMMARY] iterations=N ok=N alerts=N` on clean shutdown (SIGINT/SIGTERM trap)

Dry-run schedule is deterministic: every 3rd iteration returns synthetic 503. Used by the test for exact-count assertions.

Made executable (`chmod +x`).

### Task 3 — Tests

`tests/scripts/test_dayzero.py` — 5 deterministic tests, all using `subprocess.run` with `--dry-run` modes (no real network):

1. `test_proxy_load_test_dry_run_passes_with_loose_budget` — default p99 budget passes synthetic gaussian@200ms.
2. `test_proxy_load_test_dry_run_forced_fail_on_tight_budget` — p99 budget = 50ms forces FAIL, exit 1.
3. `test_proxy_load_test_json_output_shape` — --json output contains all 15 expected keys.
4. `test_healthz_check_dry_run_alert_schedule` — 6 iterations produce exactly 2 ALERTs + 4 OKs + SUMMARY line.
5. `test_healthz_check_help_exits_clean` — bonus 5th test, --help exits 0 with usage on stdout. (Plan called for 4; 5th is cheap and catches argparse breakage.)

All 5 tests pass in <1s.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Initial bash test reported wrong exit code**
- **Found during:** Task 1 manual verification
- **Issue:** Verification step ran `python3 ... | tail -5; echo $?` — `$?` captures `tail`'s exit, not python's. Initial readout suggested forced-fail case exited 0 (looked like a real script bug).
- **Fix:** Re-tested with explicit `python3 ... > /tmp/out 2>&1; echo $?` (capturing real exit). Script was correct all along — verdict=FAIL, exit=1. Discovered the bash shell-piping trap, not a script bug. Documented in this summary so future reviewers don't get fooled by the same pattern.
- **Files modified:** none (verification artifact only)
- **Commit:** N/A (no code change)

### Scope addition (5th test)

The plan specified 4 tests; I added a 5th (`test_healthz_check_help_exits_clean`) because it's <5 lines and guards against argparse regressions in the watchdog script. Within scope of "deterministic tests" — extending coverage, not feature creep.

## Verification

- `python3 scripts/dayzero/proxy_load_test.py --help` exits 0 with all flags listed ✅
- `python3 scripts/dayzero/proxy_load_test.py --dry-run --dry-run-seed 42 --duration 2 --rps 10` exits 0 with PASS verdict ✅
- Same command with `--p99-budget-ms 50` exits 1 with FAIL verdict ✅
- `--json` output parses, contains 15 expected keys ✅
- `bash scripts/dayzero/healthz_check.sh --help` exits 0 ✅
- `bash scripts/dayzero/healthz_check.sh --dry-run --interval 0 --max-iterations 6` produces 2 ALERTs + 4 OKs + SUMMARY, exits 0 ✅
- `[ -x scripts/dayzero/healthz_check.sh ]` exits 0 ✅
- `PYTHONPATH=src python3 -m pytest -q tests/scripts/test_dayzero.py` — 5 passed in 0.30s ✅
- Full-suite regression: pre-existing 10 failures unchanged. New count: 1961 passed (was 1956) + 5 new tests ✅

## Commits

- `beeb3c6` — feat(26-04): Day-Zero ops scripts (proxy load test + healthz check)

## What Shipped vs Kaan-Action

Plan 26-04 covers the script half of Wave 6. Surfaced loudly in KAAN-ACTION.md (Wave 6 partial + Wave 7):

- ⏳ Discord server setup (channels + roles + invite URL — Bot deferred to v2.1)
- ⏳ 15+ pre-seeded stars before launch (warm the "0 stars looks dead" Day-0 problem)
- ⏳ Launch trigger — Kaan's go/no-go call once all gates green

## Self-Check: PASSED
