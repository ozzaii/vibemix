# vibemix — Release Process

> End-to-end runbook for cutting a new release. Owns the `v*` tag push →
> GitHub Release flow. Kaan should be able to ship a release without
> re-reading any Phase 18 plan file.

## Pre-Flight (one-time per project / per major-version cycle)

1. **SignPath OSS Foundation certificate approved.**
   Kaan applied via `.planning/research/signpath-application.md` early in
   Phase 1; the OSS-cert SLA is ~3 weeks. Confirm approval status in the
   SignPath dashboard before cutting `v0.1.0`. If not yet approved, the
   Windows job runs in mock-signing mode and tagged releases are blocked
   from publishing (see "Mock-signing PR validation" below).
   If status is unknown or unresolved, see `.planning/phases/21-sign-notarize-github-release-matrix/21-DEFERRED.md` Blocker B and follow `docs/signpath-application.md` to (re-)file.

2. **Apple Developer ID Application certificate imported.**
   Follow `docs/signing-macos.md` to:
   - Generate the cert in the Apple Developer portal.
   - Export `.p12` with a strong passphrase.
   - base64-encode the `.p12` for the GHA secret.
   If the Apple Developer Program Agreement update is pending (as of v2.0 entry), see `.planning/phases/21-sign-notarize-github-release-matrix/21-DEFERRED.md` Blocker A — Francesco-action.

3. **Tauri updater keypair generated.**
   ```bash
   npx @tauri-apps/cli signer generate -w ~/.tauri/vibemix_updater.key
   ```
   See `tauri/src-tauri/keys/README.md` for the full procedure: base64 the
   private half into `TAURI_UPDATER_PRIVATE_KEY`, paste the public half's
   base64 into `tauri/src-tauri/tauri.conf.json5` → `plugins.updater.pubkey`.

4. **All 16 GitHub secrets configured.**
   See `.github/workflows/README.md` for the canonical inventory + source
   for each value.

5. **`tauri.conf.json5` pubkey is NOT the placeholder.**
   Plan 18-05's `placeholder-pubkey-gate` job refuses to build tagged
   releases while the `TAURI_UPDATER_PLACEHOLDER` sentinel string remains
   in `tauri/src-tauri/tauri.conf.json5`. The gate also catches the
   base64-encoded form `dW50cnVzdGVkIGNvbW1lbnQ6IFRBVVJJX1VQREFURVJfUExBQ0VIT0xERVI=`.

6. **Bravoh proxy `/vibemix/updates/upload` endpoint configured.**
   If the Bravoh-side endpoint is live on `api.altidus.world`, set
   `BRAVOH_MANIFEST_UPLOAD_TOKEN` and the release will POST the signed
   manifest. If not yet deployed, the workflow POSTs to a 404 and emits a
   `::warning::` but does not fail — the signed manifest is also attached
   to the GitHub Release for fallback consumption.

## Cutting a release

0. **Run the hard pre-tag gate.**
   ```bash
   scripts/dist/pretag_check.sh
   ```

   Do not tag unless this exits 0. It checks the human ear-test/grading gates,
   Discord invite, updater key, sidecar bundle, local Developer ID identity,
   and required GitHub release secrets.

1. **Bump version** in two locked locations:
   - `tauri/src-tauri/tauri.conf.json5` — top-level `"version"` field.
   - `tauri/src-tauri/Cargo.toml` — `[package].version`.

   Keep them in lock-step. Tauri build cross-checks these at compile time.

2. **Update `CHANGELOG.md`** (Phase 19 polish — created when the file
   first lands; until then, write the release notes inline into the
   GitHub Release body after the workflow lands the draft).

3. **Commit + tag**:
   ```bash
   git add tauri/src-tauri/tauri.conf.json5 tauri/src-tauri/Cargo.toml
   git commit -m "release: v0.1.0"
   git tag -a v0.1.0 -m "vibemix v0.1.0 — closed beta"
   git push origin main
   git push origin v0.1.0
   ```

4. **Watch CI.** GitHub Actions picks up the tag push and runs
   `release.yml`. Expected duration: **~15–25 min** end-to-end. The
   macOS notarize step is the slowest single stage (`xcrun notarytool
   submit --wait` typically takes 5–10 min depending on Apple's queue).
   Tauri's `beforeBuildCommand` also runs `scripts/dist/prepare_tauri_build.py`;
   in CI it should find the sidecar produced by the explicit
   `scripts/build_sidecar.py` step and recheck it before packaging. After the
   macOS `.app` is emitted, CI repairs PyInstaller sidecar dylib symlinks and
   runs `scripts/dist/check_macos_app_bundle_ready.py` before
   codesign/notarization. After the signed DMG is created, CI mounts it,
   drag-copies the app to a clean rehearsal directory, and verifies the copied
   sidecar with `scripts/dist/check_macos_dmg_artifact_ready.py`. After creating
   the updater `.app.tar.gz`, CI extracts it with
   `scripts/dist/check_macos_updater_artifact_ready.py` and verifies the
   app-side sidecar still smokes from the extracted payload. The publish gate
   runs on macOS so `scripts/dist/verify_signed.py` can use `codesign --verify`
   for DMGs while still checking Windows updater/installer PE certificate
   tables offline.

5. **Review the draft release.** On success a DRAFT release exists at
   <https://github.com/{repo}/releases>. Open it and confirm:
   - `verify-report-macos.json` reports `"status": "clean"` (zero key-
     pattern hits — Plan 18-01 invariant).
   - `verify-report-windows.json` reports `"status": "clean"`.
   - DMG size ~250 MB; Windows installer EXE size ~280 MB. ±10% off the prior release is a
     yellow flag worth investigating.
   - Updater artifacts are attached separately from first-install downloads:
     macOS `.app.tar.gz` and Windows Tauri NSIS `*setup*.exe`. The
     Windows updater installer should be Authenticode-signed before
     `latest.json` is generated.
   - `latest.json` exists and has signatures for `darwin-aarch64`,
     `darwin-x86_64`, and `windows-x86_64`.

6. **Edit release notes.** The workflow seeds a minimal body. Replace
   with the user-facing changelog (features, fixes, known issues).

7. **Click Publish release.** This flips draft → public. The auto-updater
   on previously-installed `v0.0.x` builds will start serving the new
   manifest within ~2s of next app launch.

## Rolling back a bad release

See `docs/updater.md` §Rolling back a bad release for the full recipe:

1. Delete the bad tag locally and on GitHub.
2. Re-tag the prior good commit as the new "latest" version
   (e.g., if `v0.1.1` was bad, tag the `v0.1.0` commit as `v0.1.2`
   with a "rollback" note in the changelog).
3. Push the new tag to re-trigger the workflow and re-publish the
   signed manifest pointing at the older binary.

## Mock-signing PR validation

Open any PR. CI runs `release.yml` in mock mode: BUILD + VERIFY on both
OSes; no signing, no publishing. Useful for catching YAML errors or build
regressions before they touch a tagged release. The PR check appears as:

- `Release / detect-signing-mode`
- `Release / build-macos`
- `Release / build-windows`

All should be green. The placeholder-pubkey-gate is skipped on non-tag
events so a fresh worktree without real keys can still validate the
workflow shape.

## Manual rehearsal (workflow_dispatch)

For pre-tag confidence checks:

**Actions tab → Release workflow → Run workflow → branch `main` →
`dry_run: true`** (default).

This runs the matrix end-to-end with secrets available but skips
sign/package/publish. Useful before the v0.1.0 tag push to confirm the
PyInstaller spec, Tauri build, and verify_binary scan all land clean on
the current main with the secret-store in its expected state.

## Hand-offs

- **To Phase 20 (Day-Zero Operations):** fresh-machine install rehearsal
  on a clean macOS Sonoma VM + clean Windows 11 VM. The verify-report
  JSON artifacts from Phase 18 prove the bundle is clean of leaked keys;
  Phase 20 proves the end-user install + first-launch experience. The
  CI matrix expansion (lint/test/typecheck) is also Phase 20.

- **To Bravoh ops:** deploy `/vibemix/updates/upload` (POST) and
  `/vibemix/updates/<target>/<arch>/<version>` (GET) endpoints on
  `api.altidus.world`. The signed `latest.json` schema is pinned in
  `docs/updater.md` §Manifest contract.

- **To Phase 19 (polish):** wire the `update_check_on_launch` opt-out
  toggle into the Settings drawer UI surface (the
  `tauri-plugin-store` key is already exposed by Plan 18-04;
  `tauri/src-tauri/src/updater.rs` honours it on launch).

## Homebrew + Scoop publish — split rationale

The Homebrew Formula and Scoop manifest scaffolds live in
`packaging/homebrew/Formula/vibemix.rb` and `packaging/scoop/vibemix.json`.
`.github/workflows/packaging-audit.yml` validates their syntax with
`brew audit --new` on `macos-14` and `scoop checkver -d` on `windows-latest`.
The scaffolds intentionally use deterministic placeholder SHAs; real SHAs are
filled only after the signed release artifacts exist.

The actual publish to `bravoh-ai/homebrew-tap` and
`bravoh-ai/scoop-bucket` is deferred until after the first signed, notarized,
fresh-machine-verified public release. This is a user-visible install upgrade
over DMG/EXE downloads and should not be mixed into the first-install release
gate.

Sequence at execution time:

1. Ship the signed/notarized macOS DMG and signed Windows Inno EXE from the
   GitHub Release flow.
2. Run `scripts/launch/sync_packaging.sh` against those exact artifacts to fill
   the placeholder SHAs.
3. Commit the synced manifests to the Homebrew tap and Scoop bucket in a
   separate install-channel milestone.

This split keeps the first release focused on the one-click installer path.

## Autonomous-mode release path

This section is now a historical pre-stage contract, not permission to publish.
Automation may prepare release artifacts, run `cut_release.sh --dry-run`, and
print the manual `gh release create ...` command, but the public release remains
blocked until signing, notarization, Windows signing, updater artifacts, and
fresh-machine install rehearsal pass.

Current contract:

1. `scripts/launch/cut_release.sh --dry-run <tag>` must pass immediately before
   any real cut.
2. `cut_release.sh` must never invoke `gh release create` itself; the
   hand-on-trigger remains manual and is regression-pinned by
   `tests/repo/test_cut_release_no_autonomous_publish.py`.
3. The operator may run the printed `gh release create ...` command only after
   the signed/notarized DMG, signed Windows installer, updater artifacts, and
   install rehearsal evidence are present.
4. If any gate drifts, fix the gate or record the external blocker. Do not
   downgrade the release definition to match a partial artifact set.

Interactive release sessions follow the same split: automation prepares and
verifies; a human publishes only after the gates prove the release is
friend-installable.

The test surface pinning the deferral contract is `tests/repo/test_ship_v4_section_exists.py` (Plan 69-05 / Wave 4 anti-rot gate). See `KAAN-ACTION-LEGAL.md §SHIP-V4` for the full SHIP runbook + sign-off block.

## Release-day checklist

- [ ] `scripts/dist/pretag_check.sh` exits 0.
- [ ] `tauri.conf.json5` pubkey is NOT the placeholder.
- [ ] `tauri/src-tauri/Cargo.toml` version matches `tauri.conf.json5`.
- [ ] CHANGELOG entry exists for the new version (or release notes
      drafted for inline use).
- [ ] All 16 GitHub Actions secrets present + valid.
- [ ] Last main-branch CI run is green.
- [ ] `uv run python scripts/dist/prepare_tauri_build.py --skip-frontend --check-only`
      passes on the release machine, or CI has already built the sidecar in the
      current matrix job.
- [ ] Local unsigned macOS first-install rehearsal uses
      `bash scripts/dist/build_macos_local_dmg.sh`; direct
      `cargo tauri build --bundles dmg --no-sign` can package the app before
      sidecar symlink repair.
- [ ] Windows payload verifier passed on `dist/windows-app` before SignPath/Inno.
- [ ] Tag follows `v*` pattern (e.g., `v0.1.0`).
- [ ] On tag push, `release.yml` runs all 5 jobs green.
- [ ] `verify-report-macos.json` is `"status": "clean"`.
- [ ] `verify-report-windows.json` is `"status": "clean"`.
- [ ] DMG + Windows installer EXE sizes within ±10% of the last release (sanity gate).
- [ ] Updater artifacts attached: macOS `.app.tar.gz` and Windows Tauri
      NSIS `*setup*.exe`. The Windows updater installer is
      Authenticode-signed through `SIGNPATH_SIGNTOOL_CMD` and covered by the
      publish-gate signed-artifact verifier. Do not point `latest.json` at the
      DMG or Inno `vibemix-installer.exe`.
- [ ] `latest.json` has `darwin-aarch64`, `darwin-x86_64`, and `windows-x86_64`
      signatures present and non-empty.
- [ ] Manifest POST to `api.altidus.world` returned 200/202/204
      (or expected 404 with `::warning::` if endpoint not yet shipped).
- [ ] Release notes are flesh-and-blood (not the seed text).
- [ ] `Publish release` button clicked.
- [ ] Update prompt verified on a previous install (manual for v1;
      Phase 20 automates this on a fresh VM).

## Cross-references

- `.github/workflows/release.yml` — the workflow itself.
- `.github/workflows/README.md` — secrets inventory + mock-signing semantics.
- `docs/signing-macos.md` — local macOS re-sign playbook (Plan 18-02).
- `docs/signing-windows.md` — local Windows re-sign playbook (Plan 18-03).
- `docs/updater.md` — manifest contract + server semantics + rollback recipe (Plan 18-04).
- `tauri/src-tauri/keys/README.md` — keypair generation procedure (Plan 18-04).
- `scripts/dist/verify_binary.py` — leak-detection gate (Plan 18-01).
- `scripts/dist/sign_macos.sh` — macOS sign chain (Plan 18-02).
- `scripts/dist/sign_manifest.sh` — Tauri manifest signer (Plan 18-05).
- `installer/windows/vibemix-installer.iss` — Inno Setup 6 script (Plan 18-03).
