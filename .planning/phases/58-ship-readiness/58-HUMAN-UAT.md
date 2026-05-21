---
status: partial
phase: 58-ship-readiness
source: [58-VERIFICATION.md]
started: 2026-05-21T11:50:00Z
updated: 2026-05-21T11:50:00Z
---

## Current Test

[awaiting Kaan + external clock — the one-button SHIP-CUT is ready minus these]

## Tests

### 1. Record the §E2E-50A-WALK on the real Mac (REL-02)
expected: Drive the real app end-to-end with real DJ-set audio; record to `docs/e2e/2026-05-walk.webm` (feeds Gate 6b). Run `scripts/e2e/record_50a_walk.sh` (path bug now fixed). Gate-6b is proven green on a rendered report; this is the real recording.
why_human: Real hardware + real audio + screen recording.
result: [pending]

### 2. Gate-2b hallucination ear-pass (REL-01)
expected: Discharge `54-HUMAN-UAT.md` (hype) + `55-HUMAN-UAT.md` (coach) — live ≥2-genre ear-pass confirming grounded, non-slop reactions. Flips Gate 2b green.
why_human: Felt-quality on real hardware (Kaan's ears).
result: [pending]

### 3. External signatures (REL-03) — external clock
expected: Apple Developer Program Agreement update (Francesco) + SignPath OSS Foundation cert (Kaan). The signed/notarized DMG (currently Apple 403) + signed companion. Then run the one-button SHIP-CUT per `KAAN-ACTION-LEGAL.md §SHIP-V4` / §SHIP-CUT.
why_human: Legal-capacity / external-clock; the literal signed publish.
result: [pending]

### 4. Gate-5b Bravoh `/vibemix/healthz` freshness at cut time (REL-01)
expected: The Bravoh prod proxy health endpoint is green at the moment of the real cut (it was down during the dry-run; a real-cut precondition, not an engineering gap).
why_human: Live server state at cut time.
result: [pending]

### 5. (Confirm) Public release tag = `v0.1.0-rc1`
expected: Confirm the public tag is `v0.1.0-rc1` (the autonomous-recommended call: matches pyproject `0.1.0-dev0` + first OSS release). If you prefer `v4.0.0-rc1`, it's a one-line regex flip in `cut_release.sh` (Gate 1) — see §SHIP-V4.
why_human: Public version-identity decision.
result: [pending — recommended v0.1.0-rc1]

## Summary

total: 5
passed: 0
issues: 0
pending: 5
skipped: 0
blocked: 0

## Gaps

None — engineering is green (13/13 must-haves; dry-run GREEN; all gates wired to flip). These are the documented external-clock + Kaan-action discharges. The one-button SHIP-CUT is pre-verified ready: everything but the signature is done.
