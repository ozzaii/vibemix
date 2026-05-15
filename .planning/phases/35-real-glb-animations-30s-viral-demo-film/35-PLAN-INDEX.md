# Phase 35 Plan Index

**Mode:** gsd-autonomous fully
**Date:** 2026-05-15

## Plans

| ID | Title | REQ-IDs | File |
|----|-------|---------|------|
| 35-01 | GLB optimization pipeline (gltfpack wrapper + per-clip + total budget) | ASSETS-04 | 35-01-PLAN.md |
| 35-02 | Demo film cut driver (ffmpeg manual cut + cuts.json schema + ≤8 cuts gate) | ASSETS-05 | 35-02-PLAN.md |
| 35-03 | README hero hash sync gate (script + CI workflow + drift test) | ASSETS-07 | 35-03-PLAN.md |
| 35-04 | Doctrine docs (3-beat, recording, VO policy, asset pipeline) + AI-VO grep gate | ASSETS-01, ASSETS-02, ASSETS-06 | 35-04-PLAN.md |
| 35-05 | Manifest comment + Phase 22-02 structural contract test + README hero comment | ASSETS-03 | 35-05-PLAN.md |
| 35-06 | KAAN-ACTION-LEGAL.md entries for 6 deferred items | (deferred) | 35-06-PLAN.md |

## Execution order

Plans are independent — execute sequentially per atomic commit discipline. No cross-plan dependencies.

## Hard gates (all must pass after each plan)

- `pytest tests/repo/ tests/scripts/` — no regressions.
- `./scripts/check_mascot_glb_size.sh` — 25 MB cap holds.
- New tests added per-plan must pass.

