---
gsd_plan_summary_version: 1.0
phase: 20
plan: 20
plan_name: Day-Zero Operations
status: completed
requirements: [DIST-08]
---

# Plan 20 — Day-Zero Operations

Single plan covering issue auto-triage workflow + rota + rehearsal
checklist + post-launch playbook + pretag readiness gate + tests.

## Tasks

| # | Task                                  | File                                              | Status |
|---|---------------------------------------|---------------------------------------------------|--------|
| 1 | Issue auto-triage workflow            | `.github/workflows/issue-triage.yml`              | ✅     |
| 2 | Day-zero responder rota doc           | `docs/day-zero-rota.md`                           | ✅     |
| 3 | Fresh-machine install rehearsal       | `docs/install-rehearsal.md`                       | ✅     |
| 4 | 72h post-launch playbook              | `docs/post-launch-playbook.md`                    | ✅     |
| 5 | README Discord link placeholder       | `README.md` (1-line edit, TODO marker)            | ✅     |
| 6 | Pre-tag readiness gate script         | `scripts/dist/pretag_check.sh`                    | ✅     |
| 7 | Tests + this SUMMARY + VERIFICATION   | `tests/repo/test_phase20_docs.py`                 | ✅     |

## Tests

`pytest tests/repo/test_phase20_docs.py -q` → **19 passed in 0.04s**.

`scripts/dist/pretag_check.sh` → returns exit 1 today (6 expected
human-owned blockers + 1 pass = Apple cert in Keychain). Will return
exit 0 once Kaan resolves the 6 items.

## What this phase gave Kaan

- A single script (`pretag_check.sh`) that says PASS/FAIL on whether
  v0.1.0 is ready to tag. No more "did I forget the Tauri pubkey?"
  guesswork.
- A 72h playbook so launch hour-by-hour is scripted.
- A rota so when bugs land at 03:00 CET, the responder knows who's on.
- An auto-labelling workflow so every new issue gets `triage` instantly.
- An install rehearsal checklist that turns the "fresh machine test"
  from a vague intent into a stopwatch-able 11-step protocol.

## What's left for Kaan (resolves the 6 pretag-check failures)

1. DJ a real session with vibemix running → sign off in
   `.planning/phases/16-hallucination-verification-gate/16-VERIFICATION.md`
   with `status: passed`.
2. Run the reaction-reel grading sheet (Phase 17) — 4 raters minimum.
3. Strip the `<!-- TODO(kaan, pre-tag-v0.1.0): ... -->` marker in README
   once the Discord invite lands.
4. Generate Tauri updater keypair, paste pubkey into
   `tauri/src-tauri/tauri.conf.json5`, drop the private half (base64) into
   `TAURI_UPDATER_PRIVATE_KEY` GitHub secret.
5. Configure the 11 GitHub secrets (Apple, SignPath, Tauri, Bravoh).
6. Replace `Discord: **TBD**` with `Discord: https://discord.gg/<code>`.

## Cross-phase integration

- Consumes Phase 18's `release.yml` (CI matrix already exists).
- Consumes Phase 19's `.github/ISSUE_TEMPLATE/*.yml` (auto-triage parses them).
- Gates Phase 16 + Phase 17 by checking their verification artifacts.
- No code changes to runtime — Phase 20 is pure ops surface.
