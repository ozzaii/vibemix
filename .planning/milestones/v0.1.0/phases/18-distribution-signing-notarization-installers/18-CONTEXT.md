# Phase 18: Distribution — Signing, Notarization, Installers - Context

**Gathered:** 2026-05-13
**Status:** Ready for planning
**Mode:** Smart discuss (autonomous fully — recommended answers locked; no user pause)

<domain>
## Phase Boundary

Ship signed, notarized installers on both macOS and Windows that pass
Gatekeeper + SmartScreen on **fresh, non-dev** machines without modal warnings.
Wire Tauri's auto-updater with a signed manifest. Lock the binary-attack
verification gate: the shipped bundle reveals zero `AIza`-pattern API key
strings under `strings` + `pyinstxtractor` analysis. The phase delivers:

1. PyInstaller `--onedir` builds with every nested binary signed (macOS) /
   SignPath-signed (Windows).
2. GitHub Actions release matrix that runs on tag push, produces signed
   artifacts, uploads to GitHub Releases, and updates the signed update
   manifest.
3. The binary-attack verification scripts that gate release.
4. Documentation that explains how Kaan would re-sign locally if CI breaks.

Out of scope for autonomous execution:
- Actually signing on Kaan's machine (requires his Apple Developer ID
  identity + his SignPath account credentials).
- Submitting to Apple Notarization (requires app-specific password on Kaan's
  Apple ID).
- Fresh-machine install rehearsal (owned by Phase 20).

What CAN be shipped autonomously:
- All build scripts, CI workflows, Inno Setup `.iss`, entitlements `.plist`,
  Tauri updater config, manifest publisher script, and verification scripts.
- A mock-signing dry-run path so CI can validate the workflow shape on PRs.

</domain>

<decisions>
## Implementation Decisions

### Area 1 — Release Driver: GitHub Actions Matrix
- Single workflow `.github/workflows/release.yml` triggered on `v*` tag push.
- Matrix: `macos-14` (Apple Silicon — minimum) + `windows-latest`.
- Jobs per OS:
  1. **build** — PyInstaller `--onedir` against `vibemix-core.{macos,windows}.spec` (already on disk from Phase 11 W1).
  2. **sign** — macOS: `codesign --deep --options runtime --entitlements vibemix.entitlements.plist`; Windows: SignPath job submission via `signpath/github-action-submit-signing-request@v1.2.0`.
  3. **package** — macOS: `create-dmg` → DMG, then `xcrun notarytool submit --wait` + `xcrun stapler staple`; Windows: Inno Setup 6 (`iscc vibemix-installer.iss`) → MSI.
  4. **verify** — Run `scripts/dist/verify_binary.py` against the produced bundle (AIza scan + key-pattern grep + nested binary signature check).
  5. **publish** — Upload artifacts to GitHub Releases via `softprops/action-gh-release@v2`; push signed `latest.json` updater manifest to `api.altidus.world/vibemix/updates/`.
- Secrets used (all stored in GitHub repo settings, never in code):
  - `APPLE_DEVELOPER_ID` (Developer ID Application certificate p12 base64-encoded)
  - `APPLE_DEVELOPER_ID_PASSWORD` (p12 password)
  - `APPLE_API_KEY_ID`, `APPLE_API_KEY_ISSUER`, `APPLE_API_KEY_P8` (App Store Connect API key for notarytool — preferred over Apple-ID+app-specific-password)
  - `APPLE_TEAM_ID`
  - `SIGNPATH_API_TOKEN`, `SIGNPATH_ORGANIZATION_ID`, `SIGNPATH_PROJECT_SLUG`, `SIGNPATH_SIGNING_POLICY_SLUG`
  - `TAURI_UPDATER_PRIVATE_KEY` (Tauri updater signing key — generated via `tauri signer generate`)
  - `TAURI_UPDATER_KEY_PASSWORD`
- Mock-signing dry-run on PRs: if any of the required secrets is missing, the workflow skips the sign + notarize + publish steps and only runs build + verify on an unsigned bundle. PR checks stay green without leaking secrets.

### Area 2 — macOS Signing + Notarization
- Spec file: `vibemix-core.macos.spec` (exists). Adjust to emit a `.app` bundle (not just CLI binary) so `codesign --deep` + `notarytool` work on the Tauri-wrapper-produced `.app`.
- Entitlements file: `tauri/src-tauri/entitlements.macos.plist` with:
  - `com.apple.security.device.audio-input` (BlackHole input)
  - `com.apple.security.device.microphone` (for direct mic if user opts in)
  - `com.apple.security.network.client` (Gemini proxy + updater)
  - `com.apple.security.cs.allow-jit` (Python interpreter needs it on macOS 14+)
  - `com.apple.security.cs.allow-unsigned-executable-memory` (PyInstaller bootloader)
  - NOT `com.apple.security.app-sandbox` (BlackHole virtual audio + global hotkeys break inside the sandbox; documented in `docs/signing-macos.md`).
- Hardened Runtime: enabled (`--options runtime`).
- Sign every nested binary in the `.app` recursively via `codesign --deep`. Pre-flight `find ... -type f -perm +111 | xargs codesign -s ... --force` to catch any binary missed by `--deep` on PyInstaller's `_internal/` tree.
- Notarization: `xcrun notarytool submit vibemix.dmg --key-id ... --key ... --issuer ... --wait`. On accept, `xcrun stapler staple vibemix.dmg`.
- Verification: `spctl --assess --type execute --verbose vibemix.app` must report `accepted` and `source=Notarized Developer ID`. CI fails if not.
- DMG layout: `create-dmg` with project hero icon, drag-to-Applications stencil, README link.

### Area 3 — Windows Signing + MSI
- Spec file: `vibemix-core.windows.spec` (exists). Produces `dist/vibemix/vibemix.exe` + `_internal/` tree.
- Inno Setup script: `installer/windows/vibemix-installer.iss`:
  - Compile target: `vibemix-installer.msi` (NOT `.exe` — DIST-03 names MSI).
  - Install destination: `{commonpf}\\vibemix\\`.
  - Per-user shortcuts in Start Menu + optional desktop checkbox.
  - Required components: VC++ runtime redistributable check (PyInstaller bundles need it on stripped Win 11).
- SignPath flow:
  - Sign `vibemix.exe` and every `.dll` in `_internal/` BEFORE bundling into MSI.
  - Sign the final `.msi` with the same OV cert.
  - SignPath GitHub Action handles upload + retrieve in two steps.
- Test: `signtool verify /v vibemix-installer.msi` must report the SignPath OV chain valid; CI fails if not.
- SmartScreen reputation: not fixable on day-1; document in `docs/signing-windows.md` that the first ~few thousand installs will still see a "More info" SmartScreen interstitial until Windows builds reputation on the cert. OV signing prevents the harder "blocked publisher" modal.

### Area 4 — Tauri Auto-Updater
- Updater config in `tauri.conf.json5` plugins.updater:
  - `active: true`
  - `endpoints`: `["https://api.altidus.world/vibemix/updates/{{target}}/{{arch}}/{{current_version}}"]` (Bravoh infra — re-uses existing api.altidus.world infrastructure).
  - `pubkey`: base64 of the public half of `TAURI_UPDATER_PRIVATE_KEY`. Committed to git (public).
  - `dialog: true` — show standard updater prompt; user can opt out via Settings (Phase 12 already has a placeholder; wire it in Plan 18-04 or DEFER).
- Server side: `api.altidus.world/vibemix/updates/{target}/{arch}/{current_version}` returns:
  - `204 No Content` if current_version is latest.
  - `200 OK` with JSON manifest `{ url, version, notes, pub_date, signature }` if update available. `signature` is the Tauri-signed signature of the `.dmg` / `.msi` payload.
- The release.yml workflow publishes a new manifest entry to api.altidus.world on tag push via `curl POST` to a Bravoh proxy endpoint. The Bravoh proxy stores manifests in a Postgres table; the GET endpoint serves from cache.
- Opt-out: Phase 12 settings drawer has a placeholder. Wire `update.check_on_launch: bool` in `ConfigStore`; default `true`. Plan 18-04 includes a 1-task subtask to wire this if Phase 12 didn't already; otherwise marked DEFERRED.

### Area 5 — Binary Attack Verification (VERIFY-04)
- One script: `scripts/dist/verify_binary.py`.
- Inputs: path to the produced bundle (.app on macOS, .msi on Windows).
- Behavior:
  - For .app: walk `Contents/`, run `strings` on every binary + every `.pyc` / `.so` / `.dylib`; for `_internal/base_library.zip` and other PyInstaller archives, extract via `pyinstxtractor.py` (vendored as `scripts/dist/_pyinstxtractor.py`) and re-scan recursively.
  - For .msi: `msiexec /a vibemix-installer.msi /qb TARGETDIR=<temp>` administrative install, then walk the extracted tree same as .app.
  - Regex: `r'^(AIza|AKIA|ya29\.|sk-)[A-Za-z0-9_\-]{20,}$'` — catches Google AI Studio + AWS + OAuth + OpenAI key patterns.
  - Optional dictionary scan: any string matching `r'^[A-Za-z0-9_\-]{39}$'` (Google API key shape) gets flagged even without prefix.
  - Output: `verify-report.json` listing all flagged strings + their source binary; exit code 0 (clean) or 1 (flagged).
  - **CI fails the release on exit 1.**
- Tests: `tests/dist/test_verify_binary.py` constructs a synthetic bundle with intentional `AIza...` plant + verifies the scan catches it; also a clean bundle that passes.

### Area 6 — Docs + Local Re-sign Path
- `docs/signing-macos.md` — Kaan's local re-sign recipe if CI breaks:
  - How to import Developer ID cert into keychain.
  - `notarytool store-credentials` setup.
  - One-liner: `./scripts/dist/sign_macos.sh vibemix.app` (wraps codesign + create-dmg + notarytool + stapler).
- `docs/signing-windows.md` — Windows alternative paths:
  - SignPath CLI for local re-sign if CI is down.
  - Inno Setup local invocation.
  - Note on SmartScreen warm-up.
- `docs/updater.md` — How the manifest server works + how to roll back a bad release.

### Claude's Discretion
- Exact Inno Setup template choices (visual style, install banner).
- macOS DMG visual design — keep minimal, Pioneer-restraint.
- Exact regex tuning in verify_binary.py beyond the core patterns.
- Whether to use `cargo-tauri` Tauri-CLI helpers for DMG/MSI vs. raw `create-dmg`/`iscc` — pick whichever has cleaner CI integration.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `vibemix-core.macos.spec` + `vibemix-core.windows.spec` — PyInstaller specs already on disk (from Phase 11 Wave 1).
- `tauri/src-tauri/tauri.conf.json5` already has the updater plugin stub with explicit "REPLACED IN PHASE 18" comment.
- `scripts/check_ipc_schema.py` — established pattern for CI verification scripts.
- Phase 11 W1's binary attack verification gate (0 / 482 files) — proven approach; lift the pattern into `verify_binary.py`.
- Phase 5's FastAPI proxy at `api.altidus.world` — already runs Bravoh infra. Adding `/vibemix/updates/...` endpoints is a small extension.
- `tauri/src-tauri/capabilities/default.json` — established capability allowlist pattern; updater needs `tauri-plugin-updater` capability added.

### Established Patterns
- `pyproject.toml` for any new pip dep (none expected — verify_binary.py uses stdlib only).
- All scripts under `scripts/` follow Python module shape with `__main__` block.
- Documentation under `docs/`.
- GitHub Actions workflows under `.github/workflows/`.

### Integration Points
- `.github/workflows/release.yml` — NEW, only release-tagged.
- `.github/workflows/ci.yml` (if exists) stays unchanged. Phase 20 owns CI matrix expansion.
- `scripts/dist/` — new directory.
- `installer/windows/vibemix-installer.iss` — new file.
- `tauri/src-tauri/entitlements.macos.plist` — new file.
- `docs/signing-{macos,windows}.md` + `docs/updater.md` — new docs.
- `tauri/src-tauri/tauri.conf.json5` — updater stanza replaced.

</code_context>

<specifics>
## Specific Ideas

- Match SignPath GitHub Action exactly to https://about.signpath.io/documentation/integrations/github recipe — it's the canonical OSS path.
- Use `notarytool` directly (NOT `gon` or `quill` — Apple is deprecating third-party wrappers).
- Pin Inno Setup 6.4.x; lock the version in CI's installer step.
- Tauri 2.x updater key generation: `npx @tauri-apps/cli signer generate -w ~/.tauri/vibemix_updater.key` — document but DON'T commit the private key.

</specifics>

<deferred>
## Deferred Ideas

- **Auto-rollback on bad release** — manual via "delete tag + republish previous manifest" for v1. Real rollback automation is v2.
- **Universal binary on macOS (x64 + arm64)** — Apple Silicon only on v1 (M-series only, matches Bravoh target market + Apple's own deprecation timeline). Document as a v2 enhancement.
- **Linux build** — explicit OUT in PROJECT.md.
- **Per-user MSI install on Windows** — DIST-03 currently spec'd as per-machine install via `commonpf`. Per-user (`localpf`) is friendlier but loses Start Menu shortcut visibility for non-admin users. Keep per-machine for v1; per-user is a v2 deliberation.
- **Delta updates** — full-DMG / full-MSI updates only for v1. Tauri 2.x supports patch updates but the complexity isn't worth shipping in the launch window.
- **Codecov of signing scripts** — verify_binary.py gets tests; the .sh helper scripts don't. Acceptable for v1.

</deferred>
