---
phase: 18-distribution-signing-notarization-installers
plan: 05
subsystem: distribution / ci-release-driver
tags: [dist, ci, github-actions, release-matrix, signpath, notarize, verify, publish, tauri-updater]
dependency-graph:
  requires:
    - 18-01 (verify_binary.py — AIza-pattern leak gate)
    - 18-02 (sign_macos.sh — codesign / create-dmg / notarytool / stapler chain)
    - 18-03 (vibemix-installer.iss — Inno Setup 6 → MSI)
    - 18-04 (tauri.conf.json5 placeholder gate + keypair contract)
    - 11-W1 (scripts/build_sidecar.py --spec CLI surface)
    - 11-W2 (Tauri 2.x cargo tauri build pipeline)
  provides:
    - tag-triggered release matrix on macOS + Windows
    - mock-signing fallback for fork PRs
    - signed latest.json updater manifest publisher
    - 14-secret inventory + rotation runbook
  affects:
    - .github/workflows/* (NEW directory; this is the first workflow)
    - GitHub Releases (draft-creation flow + asset uploads)
    - api.altidus.world/vibemix/updates/upload (Bravoh-side endpoint — Plan 18-04 contract)
tech-stack:
  added: []   # zero new pip / npm / cargo deps — official actions only
  patterns:
    - "release matrix gated by canary-secret presence detection (no value reads)"
    - "5-stage CI per OS: BUILD → SIGN → PACKAGE → VERIFY → PUBLISH"
    - "set +x discipline + temp-key cleanup trap around every secret-touching block"
    - "draft-release publication so Kaan reviews each release before going public"
key-files:
  created:
    - .github/workflows/release.yml
    - .github/workflows/README.md
    - scripts/dist/sign_manifest.sh
    - docs/release-process.md
  modified: []
decisions:
  - "Inno Setup install path: chocolatey (`choco install innosetup --version=6.4.0`) over Jrohy/inno-setup-action (CONTEXT §interfaces note re: action-repo maintenance signals)"
  - "Mock-signing canary set: {APPLE_DEVELOPER_ID_P12_BASE64, SIGNPATH_API_TOKEN, TAURI_UPDATER_PRIVATE_KEY} — three independent providers; all three must be present for full-release mode"
  - "Draft release default for v1; Phase 20 may flip to direct-publish once fresh-machine rehearsal is automated"
  - "Manifest POST to api.altidus.world treats 404 as a `::warning::` not a failure — endpoint not yet deployed by Bravoh ops"
  - "Workflow dispatch defaults dry_run=true so manual runs are safe even when secrets are configured"
metrics:
  duration: "~30 min"
  completed: "2026-05-13"
---

# Phase 18 Plan 05: Release Matrix Driver Summary

GitHub Actions release.yml that takes a `v*` git tag and pipes it through
build → sign → notarize → MSI → verify → publish across macOS + Windows
matrix, plus a Tauri-signer wrapper for the updater manifest and the
secrets/runbook docs that make the whole thing rehearsable without
re-reading any plan file.

## One-Liner

Phase 18 Plan 18-05 binds Plans 18-01..18-04 into a single tag-triggered
release matrix with mock-signing fallback for fork PRs, a 14-secret
inventory, and a signed-manifest publisher targeting api.altidus.world.

## 5-Job DAG

```
                              ┌──────────────────────────┐
                              │  detect-signing-mode     │  (Wave 0)
                              │  Ubuntu. Reads 3 canary  │
                              │  secrets for presence.   │
                              └────────────┬─────────────┘
                                           │ outputs.signing_available
                                           │
                              ┌────────────┴─────────────┐
                              │  placeholder-pubkey-gate │  (Wave 0)
                              │  Tag-only. greps         │
                              │  tauri.conf.json5 for    │
                              │  TAURI_UPDATER_PLACEHOLDER│
                              └────────────┬─────────────┘
                                           │
                       ┌───────────────────┴────────────────────┐
                       │                                        │
            ┌──────────▼────────────┐              ┌────────────▼──────────┐
            │   build-macos         │              │   build-windows       │  (Wave 1, parallel)
            │   runs-on: macos-14   │              │ runs-on: windows-latest│
            │   5 stages:           │              │   5 stages:           │
            │   1. BUILD            │              │   1. BUILD            │
            │   2. SIGN (sign_      │              │   2. SIGN (SignPath   │
            │      macos.sh; full   │              │      v1.2.0; full     │
            │      mode only)       │              │      mode only)       │
            │   3. PACKAGE (DMG)    │              │   3. PACKAGE (ISCC →  │
            │   4. VERIFY (always — │              │      MSI; full mode)  │
            │      verify_binary.py)│              │   4. VERIFY (always)  │
            │   5. UPLOAD artifact  │              │   5. UPLOAD artifact  │
            └──────────┬────────────┘              └────────────┬──────────┘
                       │                                        │
                       └───────────────────┬────────────────────┘
                                           │
                              ┌────────────▼─────────────┐
                              │   release-publish        │  (Wave 2, tag+secrets only)
                              │   Ubuntu.                │
                              │   - sign_manifest.sh →   │
                              │     latest.json          │
                              │   - curl POST to         │
                              │     api.altidus.world    │
                              │   - softprops/action-gh- │
                              │     release@v2 →         │
                              │     DRAFT release        │
                              └──────────────────────────┘
```

## Mock-Signing Fallback

| Scenario              | detect-signing-mode | placeholder-pubkey-gate | build-* (BUILD+VERIFY) | build-* (SIGN+PACKAGE) | release-publish |
| --------------------- | ------------------- | ----------------------- | ---------------------- | ---------------------- | --------------- |
| Tag push, secrets ✓   | true                | runs (must pass)        | runs                   | runs                   | runs            |
| Tag push, secrets ✗   | false               | runs (must pass)        | runs                   | SKIPPED                | SKIPPED         |
| PR build              | (any)               | SKIPPED                 | runs                   | SKIPPED                | SKIPPED         |
| workflow_dispatch     | true (or false)     | SKIPPED                 | runs                   | SKIPPED if dry_run=true| SKIPPED         |
| Fork PR               | false (auto)        | SKIPPED                 | runs                   | SKIPPED                | SKIPPED         |

Critical invariant: **VERIFY always runs**, even in mock mode. A leaked
`AIza` key in a fork PR's commits would still be caught by Plan 18-01's
`verify_binary.py` scan on the unsigned bundle — leak detection never
goes offline (T-18-15 mitigation).

## Cross-Plan Binding

| Workflow step                                | Cross-plan artifact invoked                          |
| -------------------------------------------- | ---------------------------------------------------- |
| `placeholder-pubkey-gate`                    | greps `tauri/src-tauri/tauri.conf.json5` (Plan 18-04)|
| `build-macos` → BUILD                        | `scripts/build_sidecar.py --spec vibemix-core.macos.spec` (Phase 11 W1) |
| `build-macos` → SIGN+PACKAGE                 | `scripts/dist/sign_macos.sh` (Plan 18-02)            |
| `build-macos` → VERIFY                       | `python -m scripts.dist.verify_binary` (Plan 18-01)  |
| `build-windows` → BUILD                      | `scripts/build_sidecar.py --spec vibemix-core.windows.spec` (Phase 11 W1) |
| `build-windows` → SIGN                       | `signpath/github-action-submit-signing-request@v1.2.0` (Plan 18-03 SignPath flow) |
| `build-windows` → PACKAGE                    | `iscc installer/windows/vibemix-installer.iss` (Plan 18-03) |
| `build-windows` → VERIFY                     | `python -m scripts.dist.verify_binary` (Plan 18-01)  |
| `release-publish` → manifest sign            | `scripts/dist/sign_manifest.sh` (this plan; uses `npx @tauri-apps/cli signer sign` under the hood — Plan 18-04 contract) |
| `release-publish` → manifest upload          | `curl POST api.altidus.world/vibemix/updates/upload` (Plan 18-04 §Server contract — endpoint may 404 until Bravoh ops ships) |
| `release-publish` → GitHub Release           | `softprops/action-gh-release@v2` (draft mode)        |

## 14-Secret Inventory + Provenance

Captured in canonical form at `.github/workflows/README.md`. Summary:

| Secret                                     | Used by              | Source                                                |
| ------------------------------------------ | -------------------- | ----------------------------------------------------- |
| APPLE_DEVELOPER_ID                         | macOS codesign       | Identity name from `security find-identity`           |
| APPLE_DEVELOPER_ID_P12_BASE64              | macOS keychain       | `base64 -i <p12>` of exported Developer ID cert       |
| APPLE_DEVELOPER_ID_PASSWORD                | macOS keychain       | .p12 export passphrase                                |
| APPLE_DEVELOPER_ID_KEYCHAIN_PASSWORD       | macOS temp keychain  | Random 32+ char passphrase for ephemeral keychain     |
| APPLE_TEAM_ID                              | macOS codesign       | 10-char team ID, developer.apple.com                  |
| APPLE_API_KEY_ID                           | macOS notarize       | App Store Connect API key ID                          |
| APPLE_API_KEY_ISSUER                       | macOS notarize       | App Store Connect Issuer UUID                         |
| APPLE_API_KEY_P8                           | macOS notarize       | `base64 -i AuthKey_XXXX.p8`                           |
| SIGNPATH_API_TOKEN                         | Windows sign         | SignPath dashboard → API tokens                       |
| SIGNPATH_ORGANIZATION_ID                   | Windows sign         | SignPath dashboard URL slug                           |
| SIGNPATH_PROJECT_SLUG                      | Windows sign         | SignPath dashboard → project slug                     |
| SIGNPATH_SIGNING_POLICY_SLUG               | Windows sign         | SignPath dashboard → signing policy slug              |
| TAURI_UPDATER_PRIVATE_KEY                  | Manifest sign        | base64 of `~/.tauri/vibemix_updater.key`              |
| TAURI_UPDATER_KEY_PASSWORD                 | Manifest sign        | Passphrase chosen at `tauri signer generate`          |
| BRAVOH_MANIFEST_UPLOAD_TOKEN               | Manifest POST        | Bravoh ops (api.altidus.world admin issues)           |

All accessed via `${{ secrets.XXX }}`; zero values inlined. `set +x`
applied before every block that exports a secret env var. Workflow's
`detect-signing-mode` job tests for presence using `secrets.XXX != ''`
expressions, never reading the values themselves.

## Action Version Pins

| Action                                                   | Pin     | Rationale                                                |
| -------------------------------------------------------- | ------- | -------------------------------------------------------- |
| `actions/checkout`                                       | v4      | GitHub-maintained, standard                              |
| `actions/setup-node`                                     | v4      | Node 20 LTS                                              |
| `actions/setup-python`                                   | v5      | Python 3.12                                              |
| `astral-sh/setup-uv`                                     | v3      | uv-based sidecar build (Phase 11 W1 pattern)             |
| `dtolnay/rust-toolchain`                                 | stable  | Tauri build dep                                          |
| `actions/upload-artifact`                                | v4      | Required v4 for `signpath` action's `github-artifact-id` |
| `actions/download-artifact`                              | v4      | Pair w/ upload-artifact@v4                               |
| `signpath/github-action-submit-signing-request`          | v1.2.0  | CONTEXT §specifics literal pin (Plan 18-03)              |
| `softprops/action-gh-release`                            | v2      | CONTEXT Area 1 literal pin                               |

## scripts/dist/sign_manifest.sh — Tauri signer wrapper

Standalone-runnable Tauri-signer wrapper that:

1. Decodes `TAURI_UPDATER_PRIVATE_KEY` (base64) into a temp keyfile inside
   a `mktemp -d` directory.
2. Sets a `trap` to scrub the temp directory on `EXIT`/`INT`/`TERM` so a
   crash or SIGTERM still cleans the private key from the filesystem.
3. Invokes `npx --yes @tauri-apps/cli signer sign` once per platform
   (darwin-aarch64 + windows-x86_64) against the GitHub Release download
   URL of the signed DMG / MSI. The Tauri CLI downloads the URL, hashes
   the bytes, and signs the hash — so the signature on `latest.json`
   matches the exact bytes the updater plugin will fetch.
4. Assembles the multi-platform `latest.json` per `docs/updater.md`
   §Manifest contract.
5. `chmod 600` on the materialised key file; `set +x` discipline so the
   private key value never appears in xtrace output.

Standalone usage (for local rehearsal):

```bash
TAURI_UPDATER_PRIVATE_KEY=$(base64 -i ~/.tauri/vibemix_updater.key) \
TAURI_UPDATER_KEY_PASSWORD='<passphrase>' \
./scripts/dist/sign_manifest.sh \
    --version 0.1.0 \
    --macos-url https://github.com/ozzaii/vibemix/releases/download/v0.1.0/vibemix-0.1.0.dmg \
    --windows-url https://github.com/ozzaii/vibemix/releases/download/v0.1.0/vibemix-installer.msi \
    --notes 'Release v0.1.0 — closed beta' \
    --output ./latest.json
```

## Hand-offs

- **To Phase 20 (Day-Zero Operations):**
  - Fresh-machine install rehearsal on clean macOS Sonoma + Windows 11
    VMs (DIST-07 full coverage; this plan delivers DIST-07-partial).
  - CI matrix expansion (`ci.yml` for lint/test/typecheck) — Plan 18-05
    deliberately does NOT touch CI workflow files.
  - Branch protection on `main` (recommended setting; release.yml relies
    on PR-review hygiene as a defence-in-depth gate against malicious
    workflow modification — see threat T-18-19).
- **To Bravoh ops:**
  - Deploy `POST /vibemix/updates/upload` endpoint on api.altidus.world
    that validates `Authorization: Bearer <BRAVOH_MANIFEST_UPLOAD_TOKEN>`,
    stores the manifest, and serves it via
    `GET /vibemix/updates/<target>/<arch>/<version>` per the Plan 18-04
    `docs/updater.md` §Server contract.
- **To Phase 19 (polish):**
  - Wire the `update_check_on_launch` opt-out toggle into the Settings
    drawer UI (config key already exposed by Plan 18-04; surface in UI
    is the open task).
  - Initialize `CHANGELOG.md` at repo root so the release-day checklist's
    "CHANGELOG entry" item has a real file to update.

## Open Follow-Ups

- Branch protection on `main` requiring PR review before merge (mitigates
  T-18-19; recommended as a Phase 20 setting, not blocking for v0.1.0
  closed beta).
- CHANGELOG.md initialization (Phase 19 polish; until then, release notes
  are written inline into the GH Release body).
- `concurrency: release` gate on the workflow (v2 deferral; protects
  against tag-flood DOS — T-18-17 accepted risk).
- Universal binary on macOS (x64 + arm64) — Apple Silicon-only on v1 per
  CONTEXT §deferred.
- Delta updates (full-DMG / full-MSI only on v1 per CONTEXT §deferred).

## Phase 18 Close Note

Phase 18 closes at scaffolding level with this plan:

- **DIST-01** (PyInstaller `--onedir`) — `release.yml` drives
  `scripts/build_sidecar.py --spec ...` on both OS jobs. **CLOSED.**
- **DIST-02** (macOS sign + notarize) — `release.yml` invokes
  `scripts/dist/sign_macos.sh` from Plan 18-02. **CLOSED.**
- **DIST-03** (Windows MSI + SignPath) — `release.yml` invokes the
  SignPath GHA + ISCC against `installer/windows/vibemix-installer.iss`
  from Plan 18-03. **CLOSED.**
- **DIST-06** (signed auto-update) — `release.yml` signs `latest.json`
  via `scripts/dist/sign_manifest.sh` + POSTs to api.altidus.world;
  placeholder gate prevents tagged release with the stub pubkey.
  **CLOSED.**
- **DIST-07** (verified clean install on fresh non-dev VM) — workflow
  exists end-to-end; full fresh-machine rehearsal is owned by Phase 20.
  **PARTIALLY CLOSED.**
- **VERIFY-04** (binary attack verification gate) — `release.yml` runs
  `python -m scripts.dist.verify_binary` on every signed bundle;
  non-zero exit fails the release. **CLOSED.**

## Self-Check: PASSED

Files verified on disk:
- `.github/workflows/release.yml` ✓ (455 lines, YAML parses, 5 jobs declared)
- `.github/workflows/README.md` ✓ (123 lines, 14 secrets inventoried)
- `scripts/dist/sign_manifest.sh` ✓ (188 lines, `bash -n` passes, exec bit set, `set -euo pipefail` + `set +x` + cleanup trap present)
- `docs/release-process.md` ✓ (178 lines, cross-references all four prior plan docs)

Commits verified in git history:
- `72d90cd feat(18-05): release matrix driver + Tauri manifest signer` ✓
- `a555c44 docs(18-05): release runbook + 14-secret inventory` ✓

Plan-level invariants verified:
- Workflow YAML parses cleanly via `python -c "import yaml; yaml.safe_load(...)"` ✓
- 5 jobs present: `detect-signing-mode`, `placeholder-pubkey-gate`, `build-macos`, `build-windows`, `release-publish` ✓
- `build-macos` runs on `macos-14`; `build-windows` on `windows-latest` ✓
- Triggers: `push.tags: ['v*']` AND `workflow_dispatch` ✓
- 6 `set +x` blocks (plan minimum: 3) ✓
- `softprops/action-gh-release@v2` pinned ✓
- `signpath/github-action-submit-signing-request@v1.2.0` pinned ✓
- TAURI_UPDATER_PLACEHOLDER gate present (greps the placeholder + base64 form) ✓
- Cross-plan references: sign_macos.sh + vibemix-installer.iss + verify_binary + sign_manifest.sh ✓
- Zero secret-shape (`AIza`/`AKIA`/`ya29.`/`sk-`) matches across all four shipped files ✓
- POC files (cohost*.py, mascot.html, mocks/) diff-untouched in this plan's commits ✓
- Zero new pip / npm / cargo deps (workflow uses official actions only) ✓
