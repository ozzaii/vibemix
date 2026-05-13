# Windows Code Signing — vibemix

> Operational runbook for the SignPath Foundation OSS signing pipeline that
> produces `vibemix-installer.msi`. Paired with `installer/windows/README.md`
> (build script reference) and `.planning/signpath-application.md` (the
> day-1 application record).

## Prerequisites

Before this runbook can produce a signed `vibemix-installer.msi`:

- [ ] **SignPath Foundation OSS approval** for the `vibemix` project — applied
      on day 1 of Phase 1 per the 3-week buffer in `.planning/signpath-application.md`.
      Approval email arrives at `oozzxaaii@gmail.com`. Confirmation includes
      the SignPath organization slug and a project token.
- [ ] **GitHub Actions secrets** set on the `ozzaii/vibemix` repo:
      - `SIGNPATH_API_TOKEN` — issued by SignPath after approval.
      - `SIGNPATH_ORG_ID` — SignPath organization UUID.
      - `SIGNPATH_PROJECT_SLUG` — defaults to `vibemix`.
      - `SIGNPATH_SIGNING_POLICY_SLUG` — defaults to `release-signing`.
- [ ] **Inno Setup 6** installed on the build runner (CI: `windows-latest`
      ships a recent ISCC via `choco install innosetup`; local Kaan box:
      install once via `winget install JRSoftware.InnoSetup`).
- [ ] **PyInstaller payload** built and present at `dist\vibemix\` — produced
      by `pyinstaller vibemix-core.windows.spec` (Phase 18 wave 0).
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
   ├─ python -m PyInstaller vibemix-core.windows.spec
   │      → dist\vibemix\ (interpreter + site-packages + assets)
   │
   ├─ Write version.txt from ${{ github.ref_name }}
   │
   ├─ ISCC installer\windows\vibemix-installer.iss
   │      /Ssignpath="signtool sign /n 'SignPath Foundation' /tr <ts> /fd SHA256 /td SHA256 $f"
   │      → installer\windows\output\vibemix-installer.exe
   │
   ├─ Rename → vibemix-installer.msi
   │
   ├─ signpath/github-action-submit-signing-request@v1
   │      with: api-token, organization-id, project-slug, signing-policy-slug,
   │            artifact-configuration-slug=msi-installer,
   │            github-artifact-id, parameters: {Version: ${{ github.ref_name }}}
   │      → downloads OV-signed vibemix-installer.msi
   │
   ├─ signtool verify /v /pa vibemix-installer.msi
   │      → must pass before release upload
   │
   └─ gh release upload ${{ github.ref_name }} vibemix-installer.msi
```

The `signpath/github-action-submit-signing-request` Action handles:
- Uploading the unsigned MSI to SignPath.
- Polling SignPath until the signing job completes.
- Downloading the OV-signed artifact back into the workflow workspace.
- Attaching a signed timestamp via DigiCert so the binary stays trusted
  past cert expiry.

The inner uninstaller (`unins000.exe` baked into the MSI) is signed in
the same pass — the `SignedUninstaller=yes` + `SignedUninstallerDir=output\signed-uninstaller`
directives in `vibemix-installer.iss` direct SignPath at the second artifact.

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
cost ~$300+/year and require a hardware token — explicitly out-of-scope
for the OSS launch. SignPath Foundation OV is the right tradeoff for v1.

## Troubleshooting

### `signtool verify` fails with "No signature found"

The signing job didn't complete. Re-check:
- `SIGNPATH_API_TOKEN` secret is present and unrevoked.
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

### MSI install fails with error 1603

Generic Windows Installer failure. Check the verbose log:

```powershell
msiexec /i vibemix-installer.msi /l*v install.log
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
artifact is `vibemix-installer.msi` (lowercase, hyphenated, single dot).
Phase 19 README download buttons reference this exact name.

## References

- `installer/windows/vibemix-installer.iss` — the Inno Setup source.
- `installer/windows/README.md` — local-build runbook.
- `.planning/signpath-application.md` — the SignPath Foundation OSS
  application record (filed day 1 of Phase 1).
- `.planning/ROADMAP.md` Phase 18 — the distribution phase definition.
- [SignPath docs](https://about.signpath.io/documentation) — pipeline reference.
- [Microsoft signtool](https://learn.microsoft.com/en-us/windows/win32/seccrypto/signtool) — command reference.
- [Inno Setup SignTool directive](https://jrsoftware.org/ishelp/index.php?topic=setup_signtool) — directive reference.
