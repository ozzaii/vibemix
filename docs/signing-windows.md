# Windows Code Signing — vibemix

> Operational runbook for the accepted Windows signing pipeline that produces
> `vibemix-installer.exe`. Paired with `installer/windows/README.md` (build
> script reference) and `docs/signpath-application.md` (historical SignPath
> notes plus current signing-route caveats).

## Prerequisites

Before this runbook can produce a signed `vibemix-installer.exe`:

- [ ] **Accepted Windows signing route** for the `vibemix` project — either the
      historical SignPath Foundation path or an approved commercial
      Authenticode path. Confirmation includes the organization/account slug
      and project token required by the release workflow.
- [ ] **GitHub Actions secrets** set on the `ozzaii/vibemix` repo:
      - `SIGNPATH_API_TOKEN` — issued by SignPath after approval.
      - `SIGNPATH_ORGANIZATION_ID` — SignPath organization UUID.
      - `SIGNPATH_PROJECT_SLUG` — defaults to `vibemix`.
      - `SIGNPATH_SIGNING_POLICY_SLUG` — defaults to `release-signing`.
      - `SIGNPATH_SIGNTOOL_CMD` — the Inno Setup `/Ssignpath=...` command
        registered at package time.
- [ ] **Inno Setup 6** installed on the build runner (CI: `windows-latest`
      ships a recent ISCC via `choco install innosetup`; local Kaan box:
      install once via `winget install JRSoftware.InnoSetup`).
- [ ] **Sidecar payload** built by
      `uv run python scripts/build_sidecar.py --spec vibemix-core.windows.spec`.
      The helper runs PyInstaller with `--extra ai-local` and installs the
      onedir sidecar into Tauri's `binaries\vibemix-core-<triple>\` resource
      layout.
- [ ] **Windows app payload** staged after `cargo tauri build --no-bundle` by
      `pwsh scripts\win\stage_app_payload.ps1 -OutputDir dist\windows-app`.
      The staged directory contains `vibemix.exe` plus the sidecar
      `binaries\...` tree that `resource_dir()` resolves at runtime.
      Verify it with `uv run python scripts/dist/check_windows_app_payload_ready.py
      dist/windows-app --triple x86_64-pc-windows-msvc --smoke version`.
- [ ] **`version.txt` populated** with the release tag — CI writes this from
      `${{ github.ref_name }}`; manual release backups must hand-edit
      `installer/windows/version.txt` before invoking ISCC.

## SignPath Flow (production)

This is the path that runs on every tagged GitHub Release (Phase 20 wires
the `.github/workflows/release.yml` driver).

```
GitHub tag push
   │
   ▼
release.yml (windows-latest)
   │
   ├─ uv run python scripts/build_sidecar.py --spec vibemix-core.windows.spec
   │      → tauri\src-tauri\binaries\vibemix-core-<triple>\
   │
   ├─ cargo tauri build --no-bundle
   │      → tauri\src-tauri\target\release\vibemix.exe
   │
   ├─ cargo tauri build --bundles nsis --no-sign
   │      → tauri\src-tauri\target\release\bundle\nsis\*setup*.exe
   │
   ├─ pwsh scripts\win\stage_app_payload.ps1 -OutputDir dist\windows-app
   │      → dist\windows-app\vibemix.exe + binaries\vibemix-core-<triple>\
   │
   ├─ python scripts/dist/check_windows_app_payload_ready.py dist/windows-app --smoke version
   │      → confirms the staged app exe, sidecar exe, and _internal tree
   │
   ├─ Write version.txt from ${{ github.ref_name }}
   │
   ├─ ISCC installer\windows\vibemix-installer.iss
   │      /DSourceDir=..\..\dist\signed-binaries
   │      /DInstallerOutputDir=..\..\output
   │      /Ssignpath="signtool sign /n 'SignPath Foundation' /tr <ts> /fd SHA256 /td SHA256 $f"
   │      → output\vibemix-installer.exe
   │
   ├─ SIGNPATH_SIGNTOOL_CMD over the Tauri NSIS updater installer
   │      → Authenticode-signed *setup*.exe updater payload
   │
   ├─ signtool verify /v /pa vibemix-installer.exe
   │      → must pass before release upload
   │
   └─ gh release upload ${{ github.ref_name }} vibemix-installer.exe
```

The workflow uses SignPath in two places: the GitHub Action signs the staged
app payload before packaging, then Inno Setup registers `SIGNPATH_SIGNTOOL_CMD`
through `/Ssignpath=...` so the final installer and generated uninstaller are
signed during compile. DigiCert timestamping keeps the binary trusted past cert
expiry.

The Tauri auto-updater artifact is built separately as
`tauri\src-tauri\target\release\bundle\nsis\*setup*.exe`. Release CI signs that
NSIS updater installer with the same `SIGNPATH_SIGNTOOL_CMD` before the Tauri
manifest signer adds the updater signature in `latest.json`. Authenticode gives
Windows reputation; the Tauri signature gives update-integrity verification.

## Local Re-Sign

You should **not** re-sign locally for production releases — the SignPath
Foundation cert is locked to SignPath's HSM and cannot be exported to dev
machines. The CI pipeline is the only signing surface.

If you need to **dry-run** the signing flow on a local Windows box (Kaan
debugging a CI breakage), use a self-signed cert for shape validation:

```powershell
# 1. Create a one-off self-signed cert (PowerShell, admin).
$cert = New-SelfSignedCertificate `
    -Subject "CN=vibemix-dev" `
    -CertStoreLocation Cert:\CurrentUser\My `
    -Type CodeSigningCert `
    -KeyUsage DigitalSignature `
    -KeyAlgorithm RSA `
    -KeyLength 2048

# 2. Build the installer with the self-signed cert.
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" `
    /Ssignpath="signtool sign /sha1 $($cert.Thumbprint) /tr http://timestamp.digicert.com /fd SHA256 /td SHA256 `$f" `
    /DSourceDir=..\..\dist\windows-app `
    installer\windows\vibemix-installer.iss

# 3. Verify — note: /pa will fail because the self-signed cert is not chain-trusted,
#    so use /v alone for shape inspection.
signtool verify /v installer\windows\output\vibemix-installer.exe
```

The output should show a `SignerCertificate` block with `CN=vibemix-dev` and
a successful timestamp. This proves the signtool wiring works; the
production SignPath signature replaces `CN=vibemix-dev` with the SignPath
Foundation issuer chain.

## SmartScreen Warm-up

Microsoft Defender SmartScreen scores executables based on cumulative
download volume and reputation. Even with a valid SignPath OV cert, a brand
new release artifact will trip the "unrecognized app" gate for the first
few hundred downloads.

**What to expect at v1.0 launch:**

- Download #1–~100: SmartScreen shows "Windows protected your PC — Don't run".
  Users must click "More info" → "Run anyway" to install.
- Download ~100–~1000: warnings transition to a softer prompt with a less
  prominent "Don't run" button.
- Download ~1000+: warnings disappear; SmartScreen trusts the binary.

**Mitigations baked into the v1 launch plan:**

1. **Document the warm-up in the release notes.** A short "Windows
   SmartScreen Warning" callout in the v1.0 GitHub Release body with
   screenshots of the "More info" → "Run anyway" path. Tells users this is
   expected, not a malware indicator. (Phase 19 deliverable — the
   release-notes template lives there.)
2. **Submit each new release to Microsoft's "Submit a file for analysis"
   portal** (<https://www.microsoft.com/en-us/wdsi/filesubmission>) right
   after upload. This shortens the warm-up window. Submit as "I believe
   this file should not be detected as malware".
3. **Avoid re-issuing the cert.** SmartScreen reputation is anchored to the
   cert thumbprint — every cert rotation resets the warm-up clock. SignPath
   Foundation certs auto-renew the same identity, so this is handled.

EV (Extended Validation) certs bypass SmartScreen warm-up entirely but
cost ~$300+/year and require a hardware token. The commercial product path no
longer excludes a paid signing route on open-source-positioning grounds; choose
the Windows signing path that gets the accepted release artifact signed,
verifiable, and supportable.

## Troubleshooting

### `signtool verify` fails with "No signature found"

The signing job didn't complete. Re-check:
- `SIGNPATH_API_TOKEN` secret is present and unrevoked.
- `SIGNPATH_SIGNTOOL_CMD` is present; release mode is intentionally disabled
  unless this secret exists because `vibemix-installer.iss` uses
  `SignTool=signpath`.
- `vibemix-installer.iss` has `SignTool=signpath` (no typos in the slug).
- The `signpath` SignTool config was passed to `ISCC.exe` via the `/Ssignpath=...`
  command-line flag at compile time.
- The SignPath dashboard shows the signing request in "Completed" state, not
  "Failed" or "Awaiting Approval".

### "VCRUNTIME140.dll missing" dialog on first launch

The user is missing the Microsoft Visual C++ 2015-2022 Redistributable.
The `[Code]` section of `vibemix-installer.iss` (`CheckVcppRuntime`)
detects this at install time and prompts the user. If the user clicked
"NO" to skip the redist install, run:

```
https://aka.ms/vs/17/release/vc_redist.x64.exe
```

manually, then re-launch vibemix. This is **not** a signing problem.

### SmartScreen shows "Unknown publisher" instead of "vibemix" / "Bravoh"

The signature exists but isn't trusted. Causes:
- Self-signed cert from a local dry-run — expected, see "Local Re-Sign".
- SignPath returned a signed artifact but the cert chain isn't installed
  on the verifying machine. Run Windows Update; the SignPath Foundation
  intermediate ships via Microsoft's Trusted Root Certificate Program.
- Cert revoked. Check SignPath dashboard for revocation events.

### "This app has been blocked for your protection" (Defender SmartScreen for App Installer)

This is a separate gate from SmartScreen at download time — it fires when
the binary itself runs. Same warm-up + reputation mechanic; same mitigations.

### Installer fails during setup

Generic setup failure. Re-run the installer from an elevated PowerShell window
so the Inno log is written beside the installer:

```powershell
.\vibemix-installer.exe /LOG=install.log
```

Common causes captured by `install.log`:
- VC++ redist not installed (the `[Code]` gate should have caught this — if
  it didn't, the user clicked through the warning).
- `{commonpf}\vibemix` already exists from a prior install and the AppId
  GUID changed between releases. The fixed `MyAppId` GUID in the `.iss`
  guards against this — never edit the GUID without a major-version bump.
- Insufficient privileges — UAC was declined. `PrivilegesRequired=admin`
  forces the prompt.

### `gh release upload` fails after signing

Verify the artifact name matches the release-notes download link. The
artifact is `vibemix-installer.exe` (lowercase, hyphenated, single dot).
Phase 19 README download buttons reference this exact name.

## References

- `installer/windows/vibemix-installer.iss` — the Inno Setup source.
- `installer/windows/README.md` — local-build runbook.
- `docs/signpath-application.md` — historical SignPath notes plus current
  signing-route caveats.
- `.planning/ROADMAP.md` Phase 18 — the distribution phase definition.
- [SignPath docs](https://about.signpath.io/documentation) — pipeline reference.
- [Microsoft signtool](https://learn.microsoft.com/en-us/windows/win32/seccrypto/signtool) — command reference.
- [Inno Setup SignTool directive](https://jrsoftware.org/ishelp/index.php?topic=setup_signtool) — directive reference.
