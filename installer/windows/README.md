# Windows Installer — Inno Setup 6

This directory ships the Inno Setup script that wraps the PyInstaller
`--onedir` payload into `vibemix-installer.msi`, the signed deliverable that
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
2. **A built PyInstaller payload** at `dist\vibemix\` (run
   `pyinstaller vibemix-core.windows.spec` from the repo root first).
3. **Windows SDK signtool** — only needed for local signing dry-runs;
   production signing runs inside the SignPath GitHub Action (see below).

## Local compile (unsigned)

From the repo root:

```powershell
# 1. Build the PyInstaller payload (Phase 18 wave 0 deliverable).
python -m PyInstaller vibemix-core.windows.spec

# 2. Compile the installer. The `/Sno=` flag disables signing for local builds
#    (no SignPath cert on dev machines).
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" `
    /Sno="echo skipping local sign for $f" `
    installer\windows\vibemix-installer.iss
```

Output lands at `installer\windows\output\vibemix-installer.exe` — Inno
Setup's native extension. The CI signing job renames this to
`vibemix-installer.msi` before SignPath ingests it. Locally you can skip the
rename; the unsigned `.exe` is functionally identical and lets you smoke-test
the install flow.

> **Note:** Local unsigned installers trigger SmartScreen "unrecognized app"
> warnings. This is expected behavior — see `docs/signing-windows.md` for the
> production signing path.

## CI signing via SignPath (production)

Production signing runs inside `.github/workflows/release.yml` (Phase 20
deliverable). The high-level flow:

1. CI builds the PyInstaller payload on `windows-latest`.
2. CI writes the release tag's version into `installer\windows\version.txt`.
3. CI runs ISCC with the SignPath signtool config injected:

   ```powershell
   "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" `
       /Ssignpath="signtool sign /n `"SignPath Foundation`" /tr http://timestamp.digicert.com /fd SHA256 /td SHA256 `$f" `
       installer\windows\vibemix-installer.iss
   ```

4. The signed `vibemix-installer.exe` is renamed to `vibemix-installer.msi`
   and submitted to SignPath via the
   [`signpath/github-action-submit-signing-request`][signpath-action] Action.
5. SignPath returns the OV-signed artifact; the workflow attaches it to the
   GitHub Release.
6. The signed inner uninstaller (`unins000.exe`) is re-signed in the same
   pass — the `SignedUninstaller=yes` + `SignedUninstallerDir=output\signed-uninstaller`
   directives in the `.iss` point SignPath at the right artifact.

The SignPath project token lives in `SIGNPATH_API_TOKEN` (GitHub Actions
secret) — see `.planning/signpath-application.md` for the full application
record and `docs/signing-windows.md` for the operational runbook.

## Verifying a signed installer

After downloading a release artifact, confirm the signature chain:

```powershell
signtool verify /v /pa installer\windows\output\vibemix-installer.msi
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
directly via the `SignTool` directive, and (c) the resulting installer
still surfaces as a real MSI to Windows (Inno's bundled MSI wrapping).
WiX migration is a v2 candidate if MSI semantics (group-policy deployment,
silent install matrices) become user-blocking.

[signpath-action]: https://github.com/SignPath/github-action-submit-signing-request
