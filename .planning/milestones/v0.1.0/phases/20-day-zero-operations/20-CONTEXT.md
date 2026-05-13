# Phase 20: Day-Zero Operations - Context

**Gathered:** 2026-05-13
**Status:** Ready for execution (autonomous portion); fresh-machine rehearsal is human-owned
**Mode:** Smart discuss (autonomous fully)

<domain>
## Phase Boundary

Phase 20 turns "we have signed binaries" (Phase 18) and "we have a
launch-grade GitHub presence" (Phase 19) into "we can survive the first
72 hours after launch without things falling over."

It's the operations-readiness gate. Four success criteria from ROADMAP:

1. `git tag v0.1.0 && git push --tags` triggers the macos-14 +
   windows-latest CI matrix; both produce signed binaries attached to a
   GitHub Release in under 30 minutes.
2. Fresh-machine install rehearsal: a non-dev macOS + a non-dev Windows
   machine both run the signed installer end-to-end, complete the
   calibration wizard, and play one AI reaction within 10 minutes.
3. Second-responder rota documented for first 72h (Kaan + Francesco + Musa)
   plus issue auto-labelling and Discord link in README.
4. Day-zero analytics dashboard on `api.altidus.world` wired with 3σ
   cost-spike + 1% binary-extraction `AIza` log-hit alerts.

## Reuse from Phase 18 + 19

This phase does **not** re-invent CI. Phase 18 Plan 18-05 already shipped
`.github/workflows/release.yml` (2-OS × 5-stage matrix with mock-signing
fallback) and `docs/release-process.md`. Phase 20's contribution is:

- Verifying the matrix triggers correctly on tag push (one rehearsal run).
- Writing the human-side runbook for everything around the matrix:
  who's on rota, what to watch, what to do when the dashboard alerts.
- Issue auto-labelling workflow (`.github/workflows/issue-triage.yml`).
- Day-zero playbook for the first 72h.

## What stays human-owned

- **Fresh-machine rehearsal**: Kaan borrows a non-dev macOS Sequoia + a
  non-dev Windows 11 machine (or spins clean VMs), downloads the signed
  binaries from the GitHub Release, and runs the install → calibrate →
  first-reaction flow. Cannot be automated — the whole point is to test
  on hardware that doesn't have any developer state.
- **Discord server**: Kaan creates a Bravoh Discord (if not yet) and adds
  the invite link to README. Cannot be automated; needs his account.
- **Analytics wiring on api.altidus.world**: Bravoh-side dashboard.
  vibemix doesn't own that surface; Musa wires the alerts.
- **Rota commitments**: Kaan confirms Francesco + Musa coverage windows
  before launch. Doc captures the agreed schedule.

## Tuning Constants

None. Phase 20 is process + docs, not code with tunable thresholds.

## POC Reference

None. POCs (`cohost.py`, `cohost_v4.py`) don't have ops surface.

</domain>

<gray-areas>
## Decisions Resolved Autonomously

| # | Decision | Resolution |
|---|----------|------------|
| 1 | Issue auto-label scope | GitHub Actions workflow `.github/workflows/issue-triage.yml` that reads the issue body's `Severity` / `Component` fields (from our YAML templates) and applies `triage`, `bug`/`feature`/`controller`, `severity:critical/major/minor` labels. No external app dependency. |
| 2 | Rota shape | Doc-based with 3 named owners (Kaan = primary, Francesco = secondary, Musa = backend escalation), 8-hour shift windows in CET for first 72h, fallback to async slack thread after hour 72. |
| 3 | Dashboard owner | Musa on api.altidus.world admin panel. vibemix client emits telemetry to `/v1/telemetry/event` (already exists in `src/vibemix/proxy/client.py`); Musa wires the dashboard against existing tables. No vibemix-side work needed beyond confirming the telemetry events fire. |
| 4 | Discord vs Slack | Discord — public, frictionless, what DJ community uses. Slack is for Bravoh internal. README footer gets the Discord invite. |
| 5 | 3σ cost-spike alert math | Baseline = rolling 7-day median per-DAU Gemini cost. Alert fires when current-hour cost-per-DAU > median + 3 × MAD. Owner: Musa. |
| 6 | Binary-extraction alert | Proxy logs every `verify_binary_failed` event. Alert fires when count > 1% of total install events in any rolling 1h window. Owner: Musa. |
| 7 | "Within 10 minutes of download click" pass-fail | Stopwatch the rehearsal. Failure = >10 min or any blocking error. Log captures: download time, install time, calibration completion time, first-reaction time. |
| 8 | When to tag v0.1.0 | After: (a) all human-owned items in the release runbook are done, (b) Phase 16 ear-gate passed, (c) Phase 17 reaction-reel ≥4.0 ratings landed. Phase 20 ships the tooling; Kaan pulls the trigger. |

## What's deferred to Kaan

| # | Item | Why |
|---|------|-----|
| 1 | Rehearsal-machine sourcing | Needs physical/VM access I don't have. |
| 2 | Discord server creation + invite link | Kaan's GitHub/Bravoh account. |
| 3 | Musa-side dashboard alerts | Bravoh backend, not vibemix repo. |
| 4 | Apple app-specific password for ship | One-time generation at appleid.apple.com (Francesco's account). |

</gray-areas>

<assumptions>
## Verified

- A1: `release.yml` already implements the 2-OS × 5-stage matrix (Phase 18 Plan 18-05). **Confirmed** by inspecting `.github/workflows/release.yml:1-44`.
- A2: `docs/release-process.md` already documents the pre-flight + cutting-a-release flow (Phase 18). **Confirmed** by inspection.
- A3: Issue templates have `Severity` + `Component` dropdowns. **Confirmed** by `.github/ISSUE_TEMPLATE/bug_report.yml` (Phase 19 19-02).
- A4: Telemetry client emits `verify_binary_failed` events. **To verify** during execution.

## Unverified — flagged for execution

- A5: Mock-signing fallback in `release.yml` actually skips publish when secrets absent. **Test during execution.**
- A6: `softprops/action-gh-release@v2` draft-mode flag is set so Kaan can review before publishing. **Verify during execution.**
- A7: The placeholder-pubkey-gate blocks tag pushes when Tauri keypair not generated. **Verify during execution.**

</assumptions>

<integration>
## Cross-Phase Connections

- **Phase 18 (signing/installers)**: Phase 20's CI matrix IS Phase 18's `release.yml`. Phase 20 documents how to USE it; Phase 18 built it.
- **Phase 19 (GitHub presence)**: Phase 20's issue-triage workflow consumes Phase 19's issue templates. README gets one more line (Discord link).
- **Phase 17 (reaction-reel)**: Phase 17's grading is a pre-tag gate. Phase 20 doesn't trigger v0.1.0 until 17 passes.
- **Phase 16 (Kaan's ear-test)**: Same — pre-tag gate. Kaan signs off in `16-VERIFICATION.md` before any tag push.
- **No POC reference** (ops surface didn't exist in cohost_v*.py).

## Threat Model

- **T-20-01**: A breaking change lands on `main` between rota shifts and the next responder doesn't know it's there. *Mitigation*: every commit to main during launch week MUST link a rota-pinned issue in the commit body OR be tagged with `[rota-aware]`. Plan task: pre-commit hook + doc.
- **T-20-02**: Issue auto-labelling drops messages (workflow failure) and the rota responder misses a critical bug. *Mitigation*: rota responder owns the `triage` label sweep every 4h regardless; auto-labelling is a convenience, not a contract.
- **T-20-03**: Day-zero analytics fires false positive 3σ cost-spike alert and Kaan panics-kills the proxy. *Mitigation*: documented "first verify the spike isn't a launch traffic surge" runbook step; baseline doesn't fire alerts in the first 24h of v0.1.0 to let the new baseline stabilize.

</integration>
