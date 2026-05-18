# vibemix e2e — 50a Kaan-walk discharge

This directory holds engineering scaffolding for the Phase 50 50a subjective pass plus the final screencast artifact that Kaan records at §E2E-50A-WALK discharge.

## §E2E-50A-WALK — discharge procedure

1. Install the SHIPPED `.dmg` to `/Applications` (signed build from §SHIP-CUT).
2. Load real DJ-set audio in djay Pro / rekordbox. ≥ 10 min of mixed tracks.
3. Arm the screencast rig:
   ```bash
   bash scripts/e2e/record_50a_walk.sh --record
   ```
   Screencapture starts; press Esc when done.
4. Open `tests/e2e/macbook/50a_kaan_walk_checklist.md`. Walk through every step. Tick PASS/FAIL inline. Note time-to-react in milliseconds for each mascot reaction.
5. On Step 8, score Tier-1 surfaces against `tests/e2e/macbook/nielsen_10_checklist.json`. Note any MEDIUM finding inline; zero HIGH findings is the bar (REQ E2E-06).
6. Transcode raw `.mov` to `.webm`:
   ```bash
   bash scripts/e2e/record_50a_walk.sh --transcode 50a-raw-<stamp>.mov
   ```
   Output lands at `docs/e2e/2026-05-walk.webm`.
7. If the resulting `.webm` is over 25 MB, track via `git-lfs`:
   ```bash
   git lfs track 'docs/e2e/*.webm'
   git add .gitattributes docs/e2e/2026-05-walk.webm
   ```
8. Commit:
   ```bash
   git commit -m "chore(e2e): land 50a Kaan-walk screencast"
   ```

## Nielsen 10 scoring rubric

For each heuristic × Tier-1 surface combination in `nielsen_10_checklist.json`:

| Severity | Meaning | Action |
|----------|---------|--------|
| **HIGH** | Breaks the walk; users cannot proceed | Phase 50 BLOCKS; fix before v3.1 close |
| **MEDIUM** | Friction; users work around it | Note inline; fold into backlog |
| **LOW** | Cosmetic | Note inline; no follow-up required |

REQ E2E-06: zero HIGH findings on Tier-1 surfaces is the bar.

## File-size budget

| Artifact | Budget |
|----------|--------|
| `docs/e2e/2026-05-walk.webm` | < 25 MB inline OR git-lfs tracked |
| Snapshot diff PNGs | not committed (lives at `dist/e2e-macbook-runs/` ephemerally) |

## What the screencast captures

- Full screen of Kaan's MacBook (no privacy concerns — vibemix UI only)
- System audio routing during the walk
- Time-to-react for each mascot reaction (visible on the live-session HUD)
- Zero off-limits content (LM Studio / OZ / Hermes UI are not opened during the walk per CLAUDE.md privacy rule)

## Scope guardrails

- This is a Kaan-ear pass per memory `project_phase_16_kaan_dj_testing`. **NOT** a formal 30-session replay harness. **NOT** a quantified SUS / NASA-TLX usability study.
- The 50b OS-matrix smoke is the parallel objective pass — see `tests/e2e/macbook/os_matrix_smoke.py`.
- 50a + 50b are BOTH required for v3.1 close per REQ E2E-02.
