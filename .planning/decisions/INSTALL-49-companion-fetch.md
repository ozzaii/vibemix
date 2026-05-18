# ADR INSTALL-49 — Companion driver fetch + signing chain

**Status:** Accepted
**Date:** 2026-05-18
**Phase:** 49 (Win + Mac One-Click Installer Chain)
**REQ-IDs satisfied:** INSTALL-04, INSTALL-05, INSTALL-09, INSTALL-10

## Context

vibemix v3.1 needs a one-click installer on both Mac and Win that lands the
user at session-ready state in ≤ 60 s (per memory
`project_one_click_install_hard_req`). Two virtual-audio drivers are required:

- **BlackHole 2ch** (Mac) — `existential.audio` — GPL-3.0
- **VB-CABLE** (Win) — `vb-audio.com` — freeware with attribution

Three constraints conflict if naively addressed:

1. **License**: VB-Audio's EULA reserves "written agreement for OEM/bundle
   redistribution." BlackHole's licensing similarly requires ExistentialAudio
   sign-off for bundle redistribution. Shipping the driver `.pkg` / `.exe`
   inside the vibemix installer is legally fraught.

2. **Bundle ceiling**: the vibemix app bundle has a 350 MB hard ceiling per
   v3.0 invariants. Bundling drivers eats meaningfully into that envelope.

3. **Trust chain**: even if we bundled the vendor binaries, signing them
   under our certs would be impersonation. The drivers must remain
   vendor-signed; only the fetch script can be Bravoh-signed.

## Decision

Post-install **vendor fetch from official URLs** with **SHA-256 verification
against a pinned manifest** + **vendor-signed installer invocation**.
Companion scripts themselves are Bravoh-codesigned via a new `companion-sign`
release.yml stage placed between BUILD and SIGN.

### Components

| File | Purpose | Signing |
|---|---|---|
| `installer/companion/driver_manifest.json` | Single source-of-truth for vendor URLs + SHA-256 + version + license-ack text | Codesigned by Bravoh (Mac codesign + included in SignPath companion manifest on Win) |
| `installer/companion/fetch_drivers.sh` (Mac) | Fetches BlackHole pkg from `existential.audio`, SHA-256-verifies, runs `installer -pkg` | Bravoh Developer ID |
| `installer/companion/fetch_drivers.ps1` (Win) | Fetches VB-CABLE zip from `vb-audio.com`, SHA-256-verifies, runs `VBCABLE_Setup_x64.exe /S` | Bravoh SignPath Authenticode |
| `installer/companion/audio_config.py` | Routing automation + 48 kHz probe | Bravoh codesign (Mac) + SignPath (Win) |
| `installer/companion/onboarding_copy.json` | Wizard strings (single grep target for anti-slop) | Bravoh codesign (Mac); content-only on Win |
| `installer/companion/README.md` | Contract docs, AIza ban, SHA-256 discharge procedure | Content-only |

### Signing chain

```
release.yml tag push
  ├─ p46-audit (existing)
  ├─ build-{macos,windows} (existing)
  ├─ companion-sign (NEW, parallel to build)        ← codesigns installer/companion/*
  ├─ sign (existing, downstream)
  ├─ verify-signed-publish-gate (existing)
  ├─ verify-companion-signatures (NEW, gates publish on companion attestation)
  └─ release-publish (existing)
```

Verifier: `scripts/audit/check_companion_signing.sh` — codesign-verify on
Mac, sidecar `.sig` check on CI Linux runners. Tag-build = fail-on-unsigned;
branch build = WARNING tagged `§INSTALL-COMPANION-SIGN`.

### Workflow file

`.github/workflows/companion-sign.yml` (new, parallel to existing
`.github/workflows/release.yml`). Tag-gated submission to SignPath only fires
when `SIGNPATH_API_TOKEN` is provisioned — until Kaan-action
§INSTALL-COMPANION-SIGN discharges, the job emits a WARNING and exits 0.

## Consequences

### Positive

- **License-clean**: vibemix never redistributes vendor binaries. The user's
  fetch executes against the vendor's URL; the vendor controls their
  signing + redistribution chain.
- **Bundle ceiling preserved**: companion scripts add ~ 5 KB to the bundle;
  the actual driver binary (a few MB) is downloaded at install time.
- **Vendor-signed driver chain intact**: the OS-level signing modal still
  shows the vendor's identity (ExistentialAudio / VB-Audio), preserving
  user trust + matching what `existential.audio` / `vb-audio.com` users
  expect from vendor docs.
- **Auditable manifest**: SHA-256 in JSON + URL allowlist in
  `tests/install/test_driver_manifest_schema.py` lets us detect a supply-
  chain compromise (vendor URL hijacked → mismatched SHA-256 → fetch
  blocks).
- **Single Kaan-action discharge point**: §INSTALL-COMPANION-SIGN is a
  single OSS-Foundation SignPath cert grant; once it lands, every existing
  scaffolded surface activates.

### Negative

- **Requires network at install time**: offline-installer fallback is
  documented in `installer/companion/onboarding_copy.json §
  driver_fetch.fallback_body`. User can run `brew install blackhole-2ch`
  manually on Mac or download VB-CABLE manually on Win.
- **Apple Silicon Reduced Security path still user-driven**: BlackHole
  system-extension approval requires user click in System Settings →
  Privacy & Security. We cannot bypass this (Apple invariant). The
  forewarning UX surfaces this expectation up-front (INSTALL-03).
- **VB-CABLE NSIS `/S` silent flag**: works for the bare driver, but the
  Windows UAC modal for the kernel-mode driver install is unavoidable
  (Microsoft invariant). Forewarning UX surfaces this (INSTALL-03).

## Integration plan

- **Plan 49-01** → companion scripts (this ADR's surface) — DONE in this phase
- **Plan 49-02** → release.yml `companion-sign` stage + verifier (this plan)
- **Plan 49-03** → wizard UI 3-step surface
- **Plan 49-04** → Inno Setup `[Run]` + DMG firstrun hook
- **Plan 49-05** → fresh-VM matrix `--check-60s` gate
- **Plan 49-06** → anti-slop sibling + uninstall preserve-default

## Rollback path

If the companion-fetch chain breaks at SignPath approval time:

1. Revert `.github/workflows/companion-sign.yml` (drop the new workflow)
2. Revert the `--companion` / `-Companion` switches in
   `scripts/dist/sign_macos.sh` + `scripts/dist/sign_windows.ps1`
3. Remove the `installer/companion/` dir contents
4. Revert wizard Plans 49-03 + 49-04 changes
5. Uninstall reverts to the Phase 33 baseline (manual `brew install` /
   manual VB-CABLE download instructed in the wizard)

The rollback is plan-scoped — every Phase 49 surface can be reverted
independently of every other v3.0 / v3.1 phase. ModelRouter seam, IPC
contract, POC immutability, anti-slop blocklist all stay green either way.

## Kaan-action surface (autonomous mode continues; discharge required before milestone close)

- **§INSTALL-COMPANION-SIGN** — SignPath OSS Foundation cert discharge for
  the companion `.ps1` + `.py` Authenticode submission. Engineering ships
  the workflow + verifier; Kaan discharges the cert at SignPath approval
  time. Until discharge: branch builds run in WARNING mode, tag builds
  fail-on-unsigned (forcing the discharge).
- **§INSTALL-VM-RUN** — fresh-VM matrix real execution on Tart. Engineering
  ships `install_vm_matrix.sh --check-60s` harness; Kaan discharges
  real-VM rehearsal when SignPath cert lands.
- **§SHIP-CONTACT-VBAUDIO** — Kaan emails VB-Audio for explicit OEM
  redistribution permission. Out of scope for v3.1.

## References

- `.planning/phases/49-win-mac-one-click-installer-chain/49-CONTEXT.md` —
  full phase context
- `.planning/research/ARCHITECTURE.md § Feature 1` — architecture-level
  design
- `.planning/research/PITFALLS.md § 1` — installer pitfalls (silent install
  regression, Apple Silicon Reduced Security)
- Memory anchors: `project_one_click_install_hard_req`,
  `project_v4_canonical_baseline`, `feedback_no_scope_creep_clean_utility`
