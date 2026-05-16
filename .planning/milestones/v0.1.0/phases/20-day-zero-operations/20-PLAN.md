---
gsd_plan_version: 1.0
phase: 20
plan: 20
plan_name: Day-Zero Operations — rota, triage workflow, rehearsal checklist, post-launch playbook
status: in_progress
requirements: [DIST-08]
---

# Plan 20 — Day-Zero Operations

Single consolidated plan (no waves needed — all tasks are independent docs/workflows).

## Tasks

### Task 1 — Issue auto-triage workflow

**File:** `.github/workflows/issue-triage.yml`

Reads new issues' YAML form fields (`Severity`, `Component`) and applies
labels. Runs on `issues.opened`. Uses `actions/github-script@v7` to
parse the body and call `gh issue edit --add-label`.

Mapped labels:
- `triage` (always added on new issue)
- `bug` | `feature` | `controller` (from issue template type)
- `severity:critical` | `severity:major` | `severity:minor` (from bug template)

**Acceptance:** workflow file parses; doc dry-run via `act` not required —
the workflow is small enough to review by inspection. Field-name match
verified against the live issue templates from Phase 19.

### Task 2 — Day-zero responder rota doc

**File:** `docs/day-zero-rota.md`

Three named owners, 8-hour shift windows for first 72h CET, escalation
table for the alert types, async-thread fallback after hour 72.

### Task 3 — Fresh-machine install rehearsal checklist

**File:** `docs/install-rehearsal.md`

The checklist Kaan runs on a borrowed non-dev macOS + Windows machine.
Stopwatch-able. Includes:
- Cold-machine prerequisites (clean OS, no dev tools)
- Download → install → first reaction stopwatch
- Each step's pass criteria + failure-class taxonomy
- Where to log results

### Task 4 — 72h post-launch playbook

**File:** `docs/post-launch-playbook.md`

What happens hour-by-hour after `git tag v0.1.0 && git push --tags`:
- T+0:00 — tag, verify matrix dispatched, watch for green
- T+0:30 — matrix completes, signed binaries on Release (draft)
- T+0:45 — manual smoke test on macOS
- T+1:00 — flip Release from draft → published
- T+1:00 to T+8:00 — Kaan primary, watch issue inflow + Discord
- T+8:00 to T+16:00 — Francesco
- T+16:00 to T+24:00 — Kaan
- T+24:00 to T+48:00 — async, all-hands on critical only
- T+48:00 to T+72:00 — daily standups for incoming issues
- T+72:00 — retro doc

### Task 5 — README Discord link placeholder

**File:** `README.md` (one-line edit)

Add `Discord: <TBD — Kaan to drop invite link before tag>` to the footer
right after the Apache 2.0 line. Marked with a `<!-- TODO -->` so we
can grep it before tagging.

### Task 6 — Pre-tag readiness gate script

**File:** `scripts/dist/pretag_check.sh`

Single bash script that prints PASS/FAIL for every condition that must
hold before `git tag v0.1.0`:
- `16-VERIFICATION.md` exists and contains `status: passed`
- `17-VERIFICATION.md` exists and grading sheet has 4+ rater rows
- All `<!-- TODO -->` markers in README are resolved
- `tauri.conf.json5` does not contain the placeholder pubkey sentinel
- 4 required secrets are configured (via `gh secret list` parsing)
- Discord invite link is present in README (not the TBD placeholder)
- Apple Dev Program cert is still valid (`security find-identity` shows
  Francesco Fasanella cert)

Exit code 0 = ready to tag. Non-zero = blockers printed.

### Task 7 — Phase 20 SUMMARY + verification

Update `.planning/STATE.md`, write `20-SUMMARY.md` + `20-VERIFICATION.md`.

## Verification Strategy

Each task above produces a file. Task 1 + Task 6 also need to be
test-runnable (issue-triage parses correctly; pretag_check exits with
expected codes given a controlled fixture state).

Add `tests/repo/test_phase20_docs.py` covering:
- `issue-triage.yml` is valid YAML and has the expected `on: issues`
  trigger.
- `day-zero-rota.md` exists and lists 3 named owners.
- `install-rehearsal.md` exists and has a stopwatch checklist.
- `post-launch-playbook.md` exists and covers T+0 through T+72.
- `pretag_check.sh` exists and is executable.
- README has a Discord placeholder OR a real link.

## Acceptance

`pytest tests/repo/test_phase20_docs.py -q` passes. `pretag_check.sh`
runs in repo root and prints a clear PASS/FAIL block.
