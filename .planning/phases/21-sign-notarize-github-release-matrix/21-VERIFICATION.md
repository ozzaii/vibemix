---
status: human_needed
phase: 21
phase_name: Sign + Notarize + GitHub Release Matrix
verified_at: 2026-05-14
mode: gsd-autonomous fully
plans_verified_auto: 1
plans_deferred_human: 0
plans_deferred_external: 2
must_haves_total: 4
must_haves_verified: 1
must_haves_human_pending: 3
---

# Phase 21 — Verification

**Mode:** Autonomous (fully). Plan 21-01 shipped — release pipeline scaffolding + secret-name audit gate + 21-DEFERRED.md tracker. Signing/notarization activation = Kaan/Francesco external action (Apple Developer Program Agreement update + SignPath OSS approval).

## ROADMAP Success Criteria

| # | Criterion | Auto-test | Human-test | Notes |
|---|-----------|-----------|------------|-------|
| 1 | macOS DMG signed + notarized (arm64 + intel) | ✗ blocked | ⏸ Kaan-action | Workflow scaffolded `release.yml`; activates when Apple Issuer ID secrets land. |
| 2 | Windows MSI SignPath-signed (x86_64 + arm64) | ✗ blocked | ⏸ Kaan-action | Workflow scaffolded `release.yml`; activates when SignPath OSS approval lands (~1 week SLA). |
| 3 | Tauri updater pubkey + signature verification | ✓ secret-name audit gate ships | ⏸ Kaan-action | Pitfall 7 prevention active (forbidden `TAURI_UPDATER_PRIVATE_KEY_PASSWORD` blocked). Real signature attaches at activation. |
| 4 | GitHub release tagged + binaries downloadable | ✗ blocked | ⏸ Kaan-action | Tag-gated AND secrets-gated `release-publish` job waits for activation. |

## Deferred to Kaan/Francesco-Action

- **Apple Developer Program Agreement update** — Francesco-action. Issuer ID `3f60cc6b-df70-4ff8-9ceb-865dac6c1b4b` already supplied 2026-05-14.
- **SignPath Foundation OSS application** — Kaan-action Day-1 of activation. ~1 week SLA. `vibemix-binaries` slug + Apache 2.0 license confirmed.
- **Real secrets injection into GitHub Actions** — Kaan-action once approvals land. release.yml has placeholder env-var references; no real keys committed.

## Auto-test Verification

- `pytest -q` baseline preserved: 1830 passed / 10 pre-existing failures / 7 skipped.
- `release.yml` YAML parses cleanly (`python -c "import yaml; yaml.safe_load(open('.github/workflows/release.yml'))"`).
- Pitfall 7 secret-name audit gate active on `tag push` + `workflow_dispatch`.
- AIza scan re-runs 0 / 482 files.

## Gaps

None — phase scope is "ship what can ship, defer what's external". External blockers are correctly tracked in `21-DEFERRED.md`.

## Status

✓ Plan 21-01 — Shipped (release scaffolding + DEFERRED tracker + audit gate)
⏸ Activation — Kaan/Francesco-action, no Claude work remaining until approvals land.
