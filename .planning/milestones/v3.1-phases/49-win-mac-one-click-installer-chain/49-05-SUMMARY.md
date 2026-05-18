# Phase 49 Plan 05 — Summary

**Status:** complete
**Date:** 2026-05-18

## Files modified

- `scripts/dist/install_vm_matrix.json` — added `onboarding_ms_budget` + `simulated_runs` block
- `scripts/dist/install_vm_matrix.sh` — `--simulate` flag added; `--check-60s` already existed
- `scripts/dist/check_60s_gate.py` (NEW) — median + p95 + budget gate helper
- `.github/workflows/install-rehearsal.yml` — added 60s simulated gate step + companion test suite step
- `tests/dist/test_60s_gate.py` (NEW) — 8 tests pass

## Requirements satisfied

- INSTALL-01 / INSTALL-02 / INSTALL-06 — 60s gate scaffold; real-VM real-run deferred to §INSTALL-VM-RUN

## Verification

`pytest tests/dist/test_60s_gate.py` — 8/8 pass.

`bash scripts/dist/install_vm_matrix.sh --simulate --check-60s` — simulated 5 rows, median 41000ms, exit 0.

`python3 -m scripts.dist.check_60s_gate scripts/dist/install_vm_matrix.json` — median 41000, p95 52000, pass true.

## Median onboarding time across SHIP-04 matrix (simulated)

- macOS 12.3 Intel: 52000 ms
- macOS 14 AS: 38000 ms
- macOS 15 AS: 35000 ms
- Win 10: 48000 ms
- Win 11: 41000 ms

**Median: 41 000 ms** (well within 60 s budget).

Real-VM measurements at §INSTALL-VM-RUN discharge.

## Kaan-action carry-forward

- **§INSTALL-VM-RUN** — Tart VM real execution. Engineering scaffold ready; Kaan walks the 5 rows when SignPath cert lands.
