# Windows Installer — Inno Setup 6

This directory ships the Inno Setup script that wraps the PyInstaller
`--onedir` sidecar plus Tauri app into `vibemix-installer.exe`, the signed deliverable that
attaches to every GitHub Release.

## Files

| File | Purpose |
|------|---------|
| `vibemix-installer.iss` | Inno Setup 6 script — entry point for `ISCC.exe`. |
| `version.txt` | One-line version string (e.g. `0.1.0`). CI overwrites it from the release tag before compile; the placeholder lets local dev compile without a tag. |
| `assets/vibemix.ico` | Installer icon (added in Phase 18 wave 2 — placeholder reference now). |

## Build prerequisites

You will need these on the Windows build host (CI uses `windows-latest`):

1. **Inno Setup 6** — install from <https://jrsoftware.org/isdl.php> or via
   `choco install innosetup` / `winget install JRSoftware.InnoSetup`.
   The compiler binary lands at `C:\Program Files (x86)\Inno Setup 6\ISCC.exe`.
2. **A built sidecar payload** produced by the canonical helper:
   `uv run python scripts/build_sidecar.py --spec vibemix-core.windows.spec`.
   The helper runs PyInstaller through `uv run --extra ai-local`, then installs
   the onedir sidecar into `tauri\src-tauri\binaries\vibemix-core-<triple>\`.
3. **A staged Windows app payload** produced after `cargo tauri build --no-bundle` by
   `pwsh scripts\win\stage_app_payload.ps1 -OutputDir dist\windows-app`.
   This is the directory Inno Setup recurses into `{app}`.
4. **Windows SDK signtool** — only needed for local signing dry-runs;
   production signing runs inside the SignPath GitHub Action (see below).

## Local compile (unsigned)

From the repo root:

```powershell
# 1. Build the PyInstaller sidecar with local AI runtime deps included.
uv run python scripts/build_sidecar.py --spec vibemix-core.windows.spec

# 2. Build the Tauri app, then stage vibemix.exe + sidecar resources.
cd tauri
npm ci
npm run build
cd src-tauri
cargo tauri build --no-bundle
cd ..\..
pwsh scripts\win\stage_app_payload.ps1 -OutputDir dist\windows-app

# 3. Compile the installer. The `/Sno=` flag disables signing for local builds
#    (no SignPath cert on dev machines).
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" `
    /Sno="echo skipping local sign for $f" `
    /DSourceDir=..\..\dist\windows-app `
    installer\windows\vibemix-installer.iss
```

Output lands at `installer\windows\output\vibemix-installer.exe` — Inno
Setup's native extension. Do not rename it to `.msi`; Windows would route that
extension to `msiexec` instead of running the Inno installer.

> **Note:** Local unsigned installers trigger SmartScreen "unrecognized app"
> warnings. This is expected behavior — see `docs/signing-windows.md` for the
> production signing path.

## CI signing via SignPath (production)

Production signing runs inside `.github/workflows/release.yml` (Phase 20
deliverable). The high-level flow:

1. CI builds the PyInstaller sidecar on `windows-latest` through
   `scripts/build_sidecar.py`, which installs the local AI runtime extra.
2. CI builds the Tauri app executable with `cargo tauri build --no-bundle`
   because Inno is the Windows package producer, then stages
   `dist\windows-app\` with `vibemix.exe` plus
   `binaries\vibemix-core-x86_64-pc-windows-msvc\`.
3. CI writes the release tag's version into `installer\windows\version.txt`.
4. CI runs ISCC with the SignPath signtool config injected:

   ```powershell
   "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" `
       /Ssignpath="signtool sign /n `"SignPath Foundation`" /tr http://timestamp.digicert.com /fd SHA256 /td SHA256 `$f" `
       /DSourceDir=..\..\dist\signed-binaries `
       /DInstallerOutputDir=..\..\output `
       installer\windows\vibemix-installer.iss
   ```

   The release workflow gets that `/Ssignpath=...` value from the
   `SIGNPATH_SIGNTOOL_CMD` secret; without it, full signing mode stays off.

5. The workflow verifies and uploads the signed `vibemix-installer.exe` to the
   GitHub Release.
6. The signed inner uninstaller (`unins000.exe`) is re-signed in the same
   pass — the `SignedUninstaller=yes` +
   `SignedUninstallerDir={#InstallerOutputDir}\signed-uninstaller` directives
   in the `.iss` point SignPath at the right artifact.

The SignPath project token lives in `SIGNPATH_API_TOKEN` (GitHub Actions
secret) — see `.planning/signpath-application.md` for the full application
record and `docs/signing-windows.md` for the operational runbook.

## Verifying a signed installer

After downloading a release artifact, confirm the signature chain:

```powershell
signtool verify /v /pa installer\windows\output\vibemix-installer.exe
```

Expected output includes:
- `Successfully verified` exit code.
- Issuer name referencing `SignPath Foundation` (the OSS-program CA).
- Timestamp signature attached (DigiCert), so the binary stays trusted past
  cert expiry.

If `signtool verify` rejects the file, the binary was tampered with in
transit or the SignPath job didn't complete — do not distribute.

## Why Inno Setup, not WiX

Per `.planning/signpath-application.md §7` and the Phase 18 plan: Inno Setup
6 is the v1 choice because (a) the script-driven format is friendlier to
quick iteration during launch week, (b) SignPath's docs cover Inno Setup
directly via the `SignTool` directive, and (c) the resulting `.exe` installer
is the native Inno Setup output. WiX migration is a v2 candidate if MSI
semantics (group-policy deployment, silent install matrices) become user-blocking.

[signpath-action]: https://github.com/SignPath/github-action-submit-signing-request
