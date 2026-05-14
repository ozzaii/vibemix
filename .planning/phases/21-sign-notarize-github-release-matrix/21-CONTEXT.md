# Phase 21: Sign + Notarize + GitHub Release Matrix - Context

**Gathered:** 2026-05-14
**Status:** Ready for planning
**Mode:** Auto-generated (gsd-autonomous fully — auto-accepted recommended decisions)

<domain>
## Phase Boundary

vibemix v2.0 binary becomes downloadable from GitHub Releases. Signed + notarized DMG (mac arm64 + intel) and SignPath OSS-signed MSI (win x86_64 + arm64), with Tauri auto-updater wired to `api.altidus.world/vibemix/updates/upload`. **CRITICAL PATH GATE — binary shippable at phase close.**

**Critical scope boundary:** This is the v2.0 ship gate. Every phase after P21 (P22-P26) is documented as cuttable to v2.0.1 if Bravoh-launch timeline (~early June 2026) slips. Apple Issuer ID `3f60cc6b-df70-4ff8-9ceb-865dac6c1b4b` already supplied 2026-05-14; **Apple Developer Program Agreement update OUTSTANDING — Francesco-action-required** (does NOT block roadmap creation per `feedback_autonomous_no_grey_area_pause`, but DOES block P21 sign step). SignPath OSS application FILED Day-1 of phase entry, ~1-week SLA — block phase entry until approved.

</domain>

<decisions>
## Implementation Decisions

### macOS Sign + Notarize (LOCKED — per STATE + Pitfall 5)
- Apple Developer ID Application certificate via Apple Issuer ID `3f60cc6b-df70-4ff8-9ceb-865dac6c1b4b`.
- Notarization via `notarytool` (modern, replaces deprecated `altool`).
- Stapler step REQUIRED: `xcrun stapler staple vibemix.dmg` then `xcrun stapler validate` in release CI gate (Pitfall 17).
- Gatekeeper assertion: `spctl --assess --type install vibemix.dmg` exits 0 on fresh non-dev macOS.
- Bundle ID `world.bravoh.vibemix` LOCKED — TCC permissions break on any change.
- **Apple Developer Program Agreement update Kaan-action-required surface in plan**: Francesco-action flagged, plan continues with mock-signing path until resolved.

### Windows Sign (LOCKED — per Pitfall 6)
- SignPath Foundation OSS program — application FILED Day-1 of phase entry.
- Re-verify status if v0.1.0 Phase 1 application already filed (per STATE outstanding-todo).
- Windows Defender SmartScreen behavior: hard-block must NOT trigger on first launch on fresh non-dev Win 11 VM. Reputation warning is acceptable (decays over downloads, not blockable Day-1).
- ~1-week SLA assumption baked into phase entry gate.

### Release Matrix (LOCKED — per success criteria)
- 4 binaries, 4 GitHub Actions runners:
  - macos-14 arm64 → DMG
  - macos-14 intel → DMG
  - windows-latest x86_64 → MSI
  - windows-latest arm64 → MSI
- Tag: `v2.0.0` with hand-written changelog (no auto-generation — quality bar requires Kaan voice).
- AIza scan re-runs across all new bundle paths at release time; reports 0 matches (gate fails build on any match).

### Tauri Updater (LOCKED — per Pitfall 7)
- ed25519-signed `latest.json` manifest.
- `@tauri-apps/cli signer verify` runs on synthetic manifest in CI; exits 0 (gate).
- **Secret-name audit gate**: explicit CI step asserts `TAURI_UPDATER_KEY_PASSWORD` vs `TAURI_UPDATER_PRIVATE_KEY_PASSWORD` are aligned across `release.yml` + `tauri.conf.json5`. Mismatch = build fails.
- Updater endpoint: POST to `api.altidus.world/vibemix/updates/upload` (Bravoh-team carry-forward — must be deployed before phase close).
- Synthetic v2.0.0 → v2.0.1 update cycle on a fresh VM end-to-end before release sign-off.

### Day-Zero Rehearsal (LOCKED — overlap with P26, per Pitfall 31)
- Fresh-VM rehearsal artifact (clean macOS 14+ + clean Windows 11) recorded as screencast.
- P21 ships the rehearsal *capability*; P26 records the public-launch artifact.
- No TCC pre-granted, no BlackHole pre-installed, no dev cruft on rehearsal VMs.

### Distribution Channels (Claude's Discretion within constraint)
- GitHub Release primary — direct DMG/MSI download links.
- README install one-liner deferred to P26 (one-liner content: `curl ...` or `winget ...` flavor — TBD at P26).
- Homebrew cask + Scoop manifest deferred to v2.0.1+.
- Auto-update opt-in default ON (single user-visible toggle in Settings).

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `tauri/src-tauri/tauri.conf.json5` — existing config; sign + updater fields added here.
- `tauri/src-tauri/src/sidecar.rs` — Phase 11 sidecar spawn pattern; PyInstaller `--onedir` output bundled into resources.
- `.github/workflows/release.yml` (NEW or extended from existing CI) — 4-target matrix.
- Phase 11 AIza leak gate (`scripts/scan_aiza.py`) — re-runs across new bundle paths.

### Established Patterns
- 3-process architecture preserved: Tauri Rust shell + Python sidecar (PyInstaller `--onedir`) + FastAPI proxy on `api.altidus.world`. v2.0 adds ZERO new processes (per STATE locked decision).
- Bundle ID `world.bravoh.vibemix` LOCKED across every phase — TCC permissions break on change.
- Apache 2.0 + DCO license file shipped at repo root + LICENSE-NOTICE in DMG/MSI.

### Integration Points
- GitHub Actions matrix runs after AIza scan + Phase 18/19/20 test suites pass.
- `api.altidus.world/vibemix/updates/upload` endpoint (Bravoh-team carry-forward — Kaan-action surface in plan).
- SignPath dashboard for MSI artifacts.
- Apple App Store Connect for notarization status polling.

</code_context>

<specifics>
## Specific Ideas

- Wave 0 (Day-1): SignPath OSS application FILE + Apple Developer Program Agreement Francesco-action surface.
- Wave 1: GitHub Actions 4-target release.yml matrix scaffold + AIza scan re-run.
- Wave 2: macOS DMG sign + notarize + stapler + spctl assertion gate.
- Wave 3: Windows MSI SignPath integration + SmartScreen smoke test on fresh VM.
- Wave 4: Tauri updater ed25519 signing + secret-name audit gate.
- Wave 5: synthetic v2.0.0 → v2.0.1 update cycle on fresh VM (end-to-end rehearsal).
- Wave 6: tag `v2.0.0` + hand-written changelog + release publish.

</specifics>

<deferred>
## Deferred Ideas

- Homebrew cask submission (v2.0.1+).
- Scoop manifest (v2.0.1+).
- winget submission (v2.0.1+).
- Linux build matrix (explicitly excluded per STATE — macOS 12.3+ / Windows 10/11 only in v1).
- Delta updates (full-binary updates only in v2.0; delta path = v2.x optimization).
- Crash-reporter integration (deferred to v2.x — `events.jsonl` covers in-app diagnostics for v2.0).
</deferred>

---

*Phase: 21-sign-notarize-github-release-matrix*
*Context gathered: 2026-05-14 (smart discuss, fully autonomous)*
