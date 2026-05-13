# Signing vibemix on macOS — Local Re-sign Playbook

> **Audience:** Kaan, when CI's automated signing breaks and a hotfix needs to ship before CI is back up.
> **Authority:** This doc is the manual fallback. Normal releases run `scripts/dist/sign_macos.sh` automatically on `v*` tag push via `.github/workflows/release.yml` (Plan 18-05). Use this playbook only when CI is broken.

## TL;DR — One-liner

```bash
export APPLE_DEVELOPER_ID="Developer ID Application: Bravoh SAGL (TEAMID)"
export APPLE_TEAM_ID="TEAMID"
export APPLE_API_KEY_PATH="$HOME/.appstoreconnect/AuthKey_XXXXXXXX.p8"
export APPLE_API_KEY_ID="XXXXXXXX"
export APPLE_API_KEY_ISSUER="YOUR_ISSUER_UUID"

./scripts/dist/sign_macos.sh dist/vibemix-core/vibemix-core.app
```

Expected final line: `[sign_macos] DONE: vibemix-X.Y.Z.dmg notarized + stapled + verified`. The DMG path is also printed on stdout (alone, for piping).

## Prerequisites (one-time setup)

These steps run **once per machine**. Skip if you've shipped a vibemix release from this Mac before.

### 1. Apple Developer ID Application certificate (keychain)

1. Sign in to <https://developer.apple.com/account/resources/certificates> with the Bravoh team account.
2. **Certificates → "+" → Developer ID Application**.
3. Generate a Certificate Signing Request locally: **Keychain Access → Certificate Assistant → Request a Certificate From a Certificate Authority** → user email = your Apple ID → CA email = leave blank → "Saved to disk" → save the `.certSigningRequest`.
4. Upload the CSR on developer.apple.com → download the issued `.cer`.
5. Double-click the `.cer`. Keychain Access imports it. Verify both the cert AND its private key landed in `login.keychain-db`.
6. Verify:
   ```bash
   security find-identity -p codesigning -v
   ```
   Expected output line:
   ```
   1) <SHA1>  "Developer ID Application: Bravoh SAGL (TEAMID)"
   ```

If the private key is missing (just a cert), the cert was imported on a different Mac. Either generate a fresh cert here, or export `.p12` from the originating Mac and `security import` it.

### 2. ASC API key (for notarytool — preferred over Apple-ID + app-specific password)

1. Sign in to <https://appstoreconnect.apple.com/access/api>.
2. **Keys (Users and Access → Keys → "+")** → **Name** = "vibemix-notarize" → **Access** = Developer → Generate.
3. **Download the `.p8` file**. Apple gives you exactly one chance. If lost, revoke and recreate.
4. Note the **Key ID** (10-char) and **Issuer ID** (UUID).
5. Store credentials with notarytool (one-time, idempotent):
   ```bash
   xcrun notarytool store-credentials vibemix-notarytool \
     --key "$HOME/.appstoreconnect/AuthKey_XXXXXXXX.p8" \
     --key-id XXXXXXXX \
     --issuer YOUR_ISSUER_UUID
   ```
   The keychain profile name `vibemix-notarytool` is what `sign_macos.sh` defaults to via `--keychain-profile`.

> **Security note:** Never echo `$APPLE_API_KEY_P8` or paste the `.p8` contents into logs. The script never echoes them; if you re-run via `set -x` for debugging, restrict the debug window to stages 1-3 only.

### 3. `create-dmg` (Homebrew)

```bash
brew install create-dmg
```

vibemix's DMG is produced via `create-dmg`, not `hdiutil` raw — `create-dmg` handles the icon layout + drag-to-Applications stencil + signed-DMG flow in one call.

### 4. Xcode Command Line Tools

```bash
xcode-select --install
```

This pulls `codesign`, `xcrun`, `notarytool`, `stapler`, `spctl`. If you have full Xcode installed already, skip.

## Local re-sign — Stage-by-stage walkthrough

The script runs 8 stages. If a stage fails, the script exits with a numeric code mapping to the failure mode.

| Stage | What it does | Failure recovery |
|------:|--------------|------------------|
| 1 | Validate env vars, binaries, paths, keychain identity | Exit 2: print the missing var/binary; fix and rerun. Identity-mismatch usually means `APPLE_DEVELOPER_ID` doesn't match the keychain entry's CN exactly — `security find-identity -p codesigning -v` and copy the quoted string verbatim. |
| 2 | Pre-flight `codesign` every nested executable (idempotent — skips already-signed files) | Set 1 fails: a specific binary won't sign. Usually a `.dylib` that has a quarantine xattr — `xattr -dr com.apple.quarantine "$APP"` and retry. |
| 3 | `codesign --deep --options runtime --entitlements ...` on the .app + strict verify | The "requirement satisfied" error means an entitlement was wrong. Re-read `tauri/src-tauri/entitlements.macos.plist` headers — only the 5 listed entitlements ship; any deviation is documented in the file's comment block. |
| 4 | `create-dmg` builds `vibemix-X.Y.Z.dmg` and signs it | Missing icon at `tauri/src-tauri/icons/icon.png` is non-fatal (script proceeds without `--volicon`). If create-dmg fails on "Resource busy", a previous DMG is still mounted — `hdiutil detach /Volumes/vibemix`. |
| 5 | `xcrun notarytool submit --wait` (retry x3 with exponential backoff 30s/60s/120s) | Exit 3 = all 3 attempts failed. Apple's notarization can be down; the script dumps the full submission log to stderr. Most-common cause: a binary in `_internal/` failed Hardened Runtime — fetch the `xcrun notarytool log <submission-id>` JSON and look for the `path` of the rejected binary. |
| 6 | `xcrun stapler staple` (idempotent — skips if already stapled) | `stapler validate` failure usually means the DMG was modified after stapling; re-run from Stage 4. |
| 7 | `spctl --assess --type execute --verbose` — Gatekeeper acceptance gate | Exit 4 = rejected. Run `spctl --assess --verbose=4 "$APP"` manually for the full reason. The most common cause: notarization succeeded but the .app inside the DMG isn't the same one that was notarized (don't repackage post-staple). |
| 8 | `verify_binary.py` AIza-pattern scan (cross-plan integration with Plan 18-01) | Exit 5 = release-blocked. A `AIza...` key string landed inside the bundle. Find the leak source via the JSON report at `dist/verify-report.json`; re-do Phase 5 proxy review before re-bundling. |

## Dry-run (validate env + paths only)

```bash
./scripts/dist/sign_macos.sh --dry-run dist/vibemix-core/vibemix-core.app
```

Stops after Stage 1. Useful for verifying env vars + the keychain identity + create-dmg + Xcode CLT before a full run.

## Sign-only mode (skip DMG + notarize)

```bash
./scripts/dist/sign_macos.sh --skip-dmg dist/vibemix-core/vibemix-core.app
```

Stages 1-3 + 7-8 only. For:

- Re-sign drills after editing entitlements.
- Verifying that a fresh build passes `spctl` before paying for the notarytool round-trip.
- Local smoke testing where the DMG step is irrelevant.

## Entitlements — why these 5

`tauri/src-tauri/entitlements.macos.plist` ships **exactly 5 entitlements**, all `<true/>`:

1. `com.apple.security.device.audio-input` — BlackHole loopback + master capture.
2. `com.apple.security.device.microphone` — Kaan's mic when opted in.
3. `com.apple.security.network.client` — Phase 5 proxy + Tauri updater + Gemini calls.
4. `com.apple.security.cs.allow-jit` — Python interpreter on macOS 14+ rejects launch without this.
5. `com.apple.security.cs.allow-unsigned-executable-memory` — PyInstaller + numpy/scipy native C extensions.

**The sandbox key is deliberately NOT present.** BlackHole virtual-audio + global hotkeys break inside the sandbox; the trade is "no Mac App Store, ship via signed DMG via GitHub Releases".

For the full rationale + the deviation from Phase 11's build-time `entitlements.plist`, read the comment block in `tauri/src-tauri/entitlements.macos.plist` directly — that file is the source of truth.

## Bundle ID is LOCKED

```
world.bravoh.vibemix
```

**DO NOT CHANGE.** macOS TCC permissions (Screen Recording, Microphone, Accessibility) are keyed to the bundle identifier. Any post-launch change invalidates every user's previously-granted permission and force-prompts the system modals again — release-grade regression.

The lock is enforced at:
- `tauri/src-tauri/entitlements.plist` (Phase 11 W1 build-time plist)
- `tauri/src-tauri/entitlements.macos.plist` (Phase 18 distribution plist)
- `tauri/src-tauri/tauri.conf.json5` (bundle identifier)
- `vibemix-core.macos.spec` (PyInstaller spec)
- `scripts/dist/sign_macos.sh` (this script's header)

## CI mode vs Local mode

`sign_macos.sh` detects CI by checking `$CI == "true"`. In CI mode:

- The keychain identity check (Stage 1) is **skipped** — CI imports the certificate inline from `$APPLE_DEVELOPER_ID_P12_BASE64` + `$APPLE_DEVELOPER_ID_PASSWORD` into a temporary keychain (handled by `.github/workflows/release.yml`, Plan 18-05).
- The ASC API key is base64-decoded from `$APPLE_API_KEY_P8` into a temp `.p8` file before invocation.
- The temp keychain is cleaned up on workflow exit (job-level `if: always()`).
- Notarytool retries are the same (3 attempts, exponential backoff).

In Local mode (your Mac):
- The keychain identity is checked via `security find-identity -p codesigning -v` — fails fast if the cert is missing.
- The `.p8` file is read from `$APPLE_API_KEY_PATH` directly; no decoding.

The same script handles both via the `CI` env var gate. **Don't fork into two scripts** — that's the lesson from Phase 11 W1 (one PyInstaller pipeline, two specs).

## Troubleshooting

### "no identity found" but the cert is in Keychain Access

`security find-identity -p codesigning -v` is the source of truth — not Keychain Access's UI. If the UI shows the cert but the CLI doesn't, the **private key** is missing. Re-import from the `.p12` you generated on the originating Mac, or re-generate from a fresh CSR.

### "errSecInternalComponent" during codesign

Keychain isn't unlocked. Run:

```bash
security unlock-keychain ~/Library/Keychains/login.keychain-db
```

In CI: `security unlock-keychain -p "$KEYCHAIN_PASSWORD" build.keychain` (the temp keychain created earlier in the job).

### Notarytool returns "Invalid" status

The submission was accepted but Apple's automated scan rejected the binary. Fetch the log:

```bash
xcrun notarytool log <submission-id> \
  --key "$APPLE_API_KEY_PATH" \
  --key-id "$APPLE_API_KEY_ID" \
  --issuer "$APPLE_API_KEY_ISSUER"
```

Read the `issues` array. Most common: a binary in `_internal/` was signed but doesn't have Hardened Runtime enabled. Stage 2 of `sign_macos.sh` is supposed to catch this — if it slipped through, there's likely a binary with a path containing spaces that `find` mishandled. Quote properly and rerun.

### Gatekeeper modal still shows on first launch

Two possibilities:
1. **Quarantine attribute on the DMG download** — Safari adds `com.apple.quarantine`. Right-click → Open → "Open" once; macOS remembers per-bundle-id.
2. **First-time Gatekeeper reputation** — even notarized apps trigger the first-time modal until macOS has seen the bundle id from several IPs. This is Apple's design; it goes away naturally after the first ~few hundred installs. Don't try to suppress it.

### "Resource busy" on create-dmg

A previous DMG is still mounted. Detach:

```bash
hdiutil detach /Volumes/vibemix
```

Then rerun the script.

## Rolling back a bad signed release

Manual procedure for v1 (auto-rollback is v2 per 18-CONTEXT §deferred):

1. Identify the bad git tag (e.g. `v0.4.2`).
2. Delete the tag locally + remote:
   ```bash
   git tag -d v0.4.2
   git push origin :refs/tags/v0.4.2
   ```
3. Recreate the tag at the previous good SHA + push:
   ```bash
   git tag v0.4.2 <good-sha>
   git push origin v0.4.2
   ```
4. The Tauri auto-updater (Plan 18-04) re-fetches the manifest at `api.altidus.world/vibemix/updates/...` — once the manifest server points back at the previous version, new installs and update checks stop offering the bad build.
5. The bad DMG on GitHub Releases is left in place but the manifest no longer references it. Optional: edit the release notes on GitHub to add a "withdrawn" header.

## SmartScreen / Gatekeeper reputation note (day-1)

Day-one releases may still trigger a Gatekeeper modal on first launch even though the binary is notarized + stapled. OS reputation builds over the first ~few thousand installs.

Document this in the release notes so users don't panic. Parity with `docs/signing-windows.md` (Plan 18-03) — Windows SmartScreen has the same warm-up problem with a different UX flow.

## Reference

- 18-CONTEXT.md §Area 2 — locked decisions for macOS signing
- 18-02-PLAN.md — this script's authoring plan
- Apple Hardened Runtime: <https://developer.apple.com/documentation/security/hardened_runtime>
- Apple Notarization: <https://developer.apple.com/documentation/security/notarizing_macos_software_before_distribution>
- create-dmg: <https://github.com/create-dmg/create-dmg>
