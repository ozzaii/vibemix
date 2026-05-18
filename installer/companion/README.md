# installer/companion/

Post-install companion artifacts for the vibemix one-click installer chain
(Phase 49).

## Purpose

After the main installer extracts the app bundle:

1. **`fetch_drivers.sh` (Mac)** / **`fetch_drivers.ps1` (Win)** — downloads
   the appropriate virtual-audio driver (BlackHole 2ch on Mac, VB-CABLE on
   Win) from the official vendor URL, verifies SHA-256 against
   `driver_manifest.json`, and runs the vendor-signed installer.

2. **`audio_config.py`** — post-driver-install routing automation
   (Multi-Output Device on Mac, default-playback-endpoint on Win) and the
   BlackHole 48 kHz format probe (INSTALL-10 per memory
   `project_v4_canonical_baseline`).

3. **`onboarding_copy.json`** — single source-of-truth for every wizard
   user-facing string. The wizard `tauri/ui/src/wizard/copy.ts` loads this
   file and exports a typed `copy` object. Anti-slop sibling-script
   `scripts/audit/check_no_slop_install.py` gates this file (and the
   wizard step files) against the AI-slop blocklist.

4. **`uninstall.sh` / `uninstall.ps1`** — uninstall path that preserves
   user library (recordings, debriefs, ghost calibration) by default;
   `--clean` / `-Clean` flag opts into destructive removal.

## Invariants

### Bundle identity

Scripts spawn under bundle ID `world.bravoh.vibemix` (Tauri capability
scope authorizes — see `tauri/src-tauri/capabilities/default.json`).

### Key custody (Pitfall-7)

**NEVER inline AIza pattern in any companion file.** The Bravoh proxy is
the sole key custodian; companion scripts never see a raw provider key.
Enforced by:

- `tests/install/test_audio_config.py::test_no_aiza_literal_in_source`
- `tests/install/test_audio_config.py::test_no_off_limits_paths_in_companion_dir`
- CI `pitfall-7-scan.yml` workflow (when present)

### Privacy

Scripts write ONLY to:

- Mac: `~/Library/Application Support/vibemix/install.log`
- Win: `%APPDATA%\vibemix\install.log`

They MUST NOT write to:

- `~/.hermes/`
- `~/hermes-rig/logs/`
- `~/.lmstudio/`

per memory `feedback_privacy_scope_narrow`.

### Bundle ceiling

Companion driver fetch is **post-install**, OUT of the 350 MB app bundle
ceiling. The companion scripts themselves (~ a few KB) are bundled inside
the installer; the actual driver `.pkg` / `.exe` is downloaded at install
time from the vendor's URL.

## SHA-256 placeholder discharge

Until SignPath cert lands (Kaan-action **§INSTALL-COMPANION-SIGN**), the
`sha256` values in `driver_manifest.json` may start with the literal
`PLACEHOLDER_`. The fetch scripts treat placeholder values as a WARNING
(not a fail) so development can proceed; the SHA-256 verifier itself
runs but is non-blocking on placeholder.

### To discharge a placeholder

1. Download the official vendor installer (BlackHole or VB-CABLE) to a
   trusted machine.
2. Compute SHA-256:
   ```bash
   # Mac
   shasum -a 256 BlackHole2ch.v0.6.0.pkg
   # Win (PowerShell)
   Get-FileHash -Algorithm SHA256 VBCABLE_Driver_Pack43.zip
   ```
3. Edit `driver_manifest.json`, replacing the `PLACEHOLDER_…` literal with
   the 64-hex-char digest.
4. Re-run `python -m pytest tests/install/test_driver_manifest_schema.py`
   to verify.

The check at `tests/audit/test_companion_signing_gate.py` will then mark
the manifest as **discharged**; the verifier gate stops emitting the
WARNING.

## Offline-installer fallback

When the auto-fetch fails (no network at install time, vendor server
unreachable, etc.), the wizard surfaces the fallback copy from
`onboarding_copy.json § steps.driver_fetch.fallback_body`. The user can:

- Mac: run `brew install blackhole-2ch` and click retry.
- Win: download VB-CABLE manually from
  https://vb-audio.com/Cable/ and re-launch vibemix.

## Signing chain hand-off

Companion scripts themselves are Bravoh-codesigned in the release
pipeline:

- **Mac**: `scripts/dist/sign_macos.sh --companion` codesigns each
  `.sh` / `.py` / `.json` under this directory with the same Developer ID
  Application identity used for the main app bundle.
- **Win**: `scripts/dist/sign_windows.ps1 -Companion` emits a SignPath
  submission manifest for the `.ps1` artifacts.

The CI gate `scripts/audit/check_companion_signing.sh` runs at the
`verify` stage of `.github/workflows/release.yml` after the
`companion-sign` job and before publish. See Plan 49-02 for details.

## Wizard UI hand-off

`tauri/ui/src/wizard/step-driver-fetch.ts` orchestrates the companion
fetch via the Tauri `run_companion_fetch` command (defined in
`tauri/src-tauri/src/wizard_cmds.rs`). See Plan 49-03.

## Uninstall

`uninstall.sh` (Mac) / `uninstall.ps1` (Win) implement the preserve-by-
default uninstall path required by INSTALL-07. See Plan 49-06.

## Related files

- `.planning/decisions/INSTALL-49-companion-fetch.md` — ADR for the
  post-install vendor fetch + signing chain
- `.planning/phases/49-win-mac-one-click-installer-chain/49-UI-SPEC.md` —
  copy contract + visual contract for the wizard surface that consumes
  these scripts
