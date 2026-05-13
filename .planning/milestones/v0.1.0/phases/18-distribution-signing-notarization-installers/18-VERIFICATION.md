---
gsd_verification_version: 1.0
phase: 18
phase_name: Distribution — Signing, Notarization, Installers
status: human_needed
verified_at: 2026-05-13
---

# Phase 18 Verification

## Status

`human_needed` — all CI/infra/docs shipped autonomously. The **actual signed
release** (Apple Dev ID + SignPath signing + notarization + fresh-machine
install rehearsal) requires Kaan's credentials and is post-phase-close work.

## Success Criteria Coverage

| # | ROADMAP Criterion | Status | Evidence |
|---|---|---|---|
| 1 | macOS DMG opens fresh non-dev Sequoia, spctl reports notarized | DEFERRED — bench shipped | `scripts/dist/sign_macos.sh` (8-stage codesign+notarize+staple), `tauri/src-tauri/entitlements.macos.plist` (5 entitlements, NOT app-sandbox), `docs/signing-macos.md` local re-sign recipe. Actual signing requires Apple Dev ID secrets. |
| 2 | Windows MSI installs fresh non-dev Win11, signtool verify chain valid | DEFERRED — bench shipped | `installer/windows/vibemix-installer.iss` (Inno Setup 6 per-machine), `docs/signing-windows.md` SignPath + SmartScreen runbook. Actual signing requires SignPath approval + secrets. |
| 3 | PyInstaller `--onedir` on both OSes; every nested binary signed | SCAFFOLDED | sign_macos.sh `--deep` codesigns recursively; release.yml feeds PyInstaller `--onedir` output into both flows. |
| 4 | Tauri auto-updater signed manifest URL; 0.0.1 → 0.0.2 patches | SCAFFOLDED | `tauri.conf.json5` active:true, endpoint `https://api.altidus.world/vibemix/updates/...`, pubkey `TAURI_UPDATER_PLACEHOLDER` (gate-enforced by release.yml); `scripts/dist/sign_manifest.sh`; `docs/updater.md` contract + rollback. Kaan runs `npx @tauri-apps/cli signer generate` pre-v0.1.0 to replace placeholder. |
| 5 | Binary attack verification: zero AIza-pattern matches | SHIPPED — automated gate | `scripts/dist/verify_binary.py` (stdlib-only, in-house pyinstxtractor) + `tests/dist/test_verify_binary.py` (21 tests green: clean / planted / .msi / report redaction). CI fails on exit 1. |

## Automated Gates (all green)

- pytest tests/dist/: **21 passed**
- pytest tests/runtime/ tests/ui_bus/: **171 passed**
- `plutil -lint tauri/src-tauri/entitlements.macos.plist`: OK
- `bash -n scripts/dist/sign_macos.sh`: OK
- `bash -n scripts/dist/sign_manifest.sh`: OK
- `python -c "import yaml; yaml.safe_load(open('.github/workflows/release.yml'))"`: OK
- `grep -c "TAURI_UPDATER_PLACEHOLDER" tauri/src-tauri/tauri.conf.json5`: 1 (gate-enforced)
- 5 entitlements in plist (audio-input + microphone + network.client + allow-jit + allow-unsigned-executable-memory; explicitly NOT app-sandbox)
- 14 secrets referenced as `${{ secrets.* }}` in release.yml, zero values committed
- Mock-signing fallback present (`SIGNING_AVAILABLE != 'true'` skips sign+package+publish)
- POC files diff-untouched (cohost*.py, mascot.html, mocks/)
- Zero new pip/npm/cargo deps

## Human Verification Pending (post-phase)

1. **Kaan: generate Tauri updater keypair** — `npx @tauri-apps/cli signer generate -w ~/.tauri/vibemix_updater.key`; paste base64 pubkey into `tauri/src-tauri/tauri.conf.json5` replacing `TAURI_UPDATER_PLACEHOLDER`; store private key + passphrase as GitHub secrets `TAURI_UPDATER_PRIVATE_KEY` / `TAURI_UPDATER_KEY_PASSWORD`.
2. **Kaan: configure 12 GitHub Secrets** per `.github/workflows/README.md` inventory — Apple Dev ID p12, App Store Connect API key (P8 + key ID + issuer), Team ID, SignPath token + org + project + policy slug.
3. **Kaan: tag v0.1.0** → CI runs full signed release → verify GitHub Release artifacts.
4. **Phase 20 owns**: fresh non-dev macOS + Windows install rehearsal on clean VMs (Gatekeeper + SmartScreen modal-free test).
5. **Bravoh ops owns**: `/vibemix/updates/upload` + `/vibemix/updates/<target>/<arch>/<version>` endpoints on api.altidus.world (release.yml POSTs the manifest; 404 acceptable until endpoint ships).

## Files Delivered

- `scripts/dist/verify_binary.py` + `scripts/dist/_pyinstxtractor.py` (in-house, Apache-2.0-compatible)
- `scripts/dist/sign_macos.sh` (8 stages, idempotent, retries on transient notarytool errors)
- `scripts/dist/sign_manifest.sh` (Tauri-signer-based manifest signer)
- `installer/windows/vibemix-installer.iss` + `installer/windows/version.txt` + `installer/windows/README.md`
- `tauri/src-tauri/entitlements.macos.plist` (5 entitlements; explicit no-app-sandbox)
- `tauri/src-tauri/src/updater.rs` (boot-time fire-and-forget update check)
- `tauri/src-tauri/tauri.conf.json5` (updater stub → live config with placeholder pubkey gate)
- `tauri/src-tauri/keys/README.md` (key-gen recipe + secrets storage)
- `tauri/src-tauri/keys/.gitkeep` + `.gitignore` block of `*.key` / `*.key.pub`
- `.github/workflows/release.yml` (2-OS × 5-stage release matrix with mock-signing fallback)
- `.github/workflows/README.md` (14-secret inventory + rotation procedure)
- `docs/signing-macos.md`, `docs/signing-windows.md`, `docs/updater.md`, `docs/release-process.md`
- `tests/dist/test_verify_binary.py` (21 tests)
- 5 plan SUMMARYs (18-01 through 18-05)
