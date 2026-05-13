# vibemix — GitHub Actions Workflows

Inventory of every CI workflow under `.github/workflows/` + the secrets each
one consumes. Bookmark this file when adding a new secret — secrets live in
**Settings → Secrets and variables → Actions → New repository secret**, and
this README is the canonical inventory.

> Phase 18 Plan 18-05 ships `release.yml` and its 14-secret inventory.
> Other workflows (CI, lint, test) are out of scope for Phase 18 — they
> arrive in Phase 20 (CI matrix expansion).

## Workflows

| File          | Trigger                                          | Purpose                                                                | Owner             |
| ------------- | ------------------------------------------------ | ---------------------------------------------------------------------- | ----------------- |
| `release.yml` | `v*` tag push + `workflow_dispatch` (rehearsal)  | Build, sign, notarize, MSI, verify, and publish the release end-to-end | Phase 18 Plan 18-05 |

## Secrets required by `release.yml`

| Secret name                              | Used by                       | Source                                                                                                  |
| ---------------------------------------- | ----------------------------- | ------------------------------------------------------------------------------------------------------- |
| `APPLE_DEVELOPER_ID`                     | macOS codesign identity       | Full identity name as it appears in `security find-identity` — e.g. `Developer ID Application: Bravoh SAGL (TEAMID)` |
| `APPLE_DEVELOPER_ID_P12_BASE64`          | macOS keychain import         | `base64 -i Bravoh-DevID.p12` — the certificate's `.p12` export, base64-encoded                          |
| `APPLE_DEVELOPER_ID_PASSWORD`            | macOS keychain import         | Passphrase chosen when exporting the `.p12`                                                             |
| `APPLE_DEVELOPER_ID_KEYCHAIN_PASSWORD`   | macOS temp keychain           | Freshly-generated passphrase for the ephemeral CI keychain (any 32+ char random string)                 |
| `APPLE_TEAM_ID`                          | macOS codesign                | 10-char team ID from <https://developer.apple.com/account> → Membership                                 |
| `APPLE_API_KEY_ID`                       | macOS notarize (notarytool)   | App Store Connect → Users and Access → Keys → Key ID (8-10 char alphanumeric)                           |
| `APPLE_API_KEY_ISSUER`                   | macOS notarize (notarytool)   | App Store Connect → Issuer ID (UUID, top of the Keys page)                                              |
| `APPLE_API_KEY_P8`                       | macOS notarize (notarytool)   | `base64 -i AuthKey_XXXXXXXX.p8` — the `.p8` ASC API key, base64-encoded                                  |
| `SIGNPATH_API_TOKEN`                     | Windows SignPath signing      | SignPath dashboard → Account → API tokens (give the token write access to the project)                  |
| `SIGNPATH_ORGANIZATION_ID`               | Windows SignPath signing      | SignPath dashboard → Organization URL slug                                                              |
| `SIGNPATH_PROJECT_SLUG`                  | Windows SignPath signing      | SignPath dashboard → Project URL slug (typically `vibemix`)                                             |
| `SIGNPATH_SIGNING_POLICY_SLUG`           | Windows SignPath signing      | SignPath dashboard → Project → Signing Policy slug (typically `release-signing`)                        |
| `TAURI_UPDATER_PRIVATE_KEY`              | Manifest signing              | base64 of `~/.tauri/vibemix_updater.key` — see `tauri/src-tauri/keys/README.md` for generation steps    |
| `TAURI_UPDATER_KEY_PASSWORD`             | Manifest signing              | Passphrase chosen during `npx @tauri-apps/cli signer generate`                                          |
| `BRAVOH_MANIFEST_UPLOAD_TOKEN`           | Manifest POST to api.altidus  | Issued by Bravoh ops once `/vibemix/updates/upload` endpoint ships on `api.altidus.world`               |

Total: **14 secrets** + the workflow-default `GITHUB_TOKEN` (auto-provided
by GitHub Actions; never user-configured).

All secrets reach the workflow as `${{ secrets.XXX }}` interpolation; zero
values are inlined into the YAML or any committed file. The
`detect-signing-mode` pre-flight job inspects three "canary" secrets
(`APPLE_DEVELOPER_ID_P12_BASE64`, `SIGNPATH_API_TOKEN`,
`TAURI_UPDATER_PRIVATE_KEY`) to decide between full-release and
mock-signing mode without reading the values themselves.

## Mock-signing fallback

When the three canary secrets are ALL present, `release.yml` runs in **full
release mode**:

```
detect-signing-mode → placeholder-pubkey-gate → build-macos (BUILD/SIGN/PACKAGE/VERIFY)
                                              → build-windows (BUILD/SIGN/PACKAGE/VERIFY)
                                              → release-publish
```

If ANY canary is absent (PR builds, fork PRs, dry-runs against a fresh
repo), the workflow runs in **mock mode**: BUILD + VERIFY only on each OS;
no signing, no MSI, no publishing. The verify step (Plan 18-01
`scripts/dist/verify_binary.py`) STILL runs on the unsigned bundle — leak
detection is the load-bearing invariant and never goes offline.

Threat-model rationale: GitHub Actions automatically denies fork PRs access
to repository secrets, so a malicious fork cannot exfiltrate via the workflow.
The mock-signing path provides a green-CI experience for legitimate fork
contributors without leaking the existence-of-secrets through job names.

## Local dry-run / manual rehearsal

Two options:

1. **Actions tab → Run workflow** → branch `main` → `dry_run: true`
   (default). Runs the matrix on macOS + Windows runners but skips
   sign/package/publish even if the secrets are configured. The placeholder-
   pubkey-gate is skipped on non-tag dispatches so a fresh worktree without
   real keys can still validate the YAML shape.

2. **Tag a pre-release locally** (e.g. `v0.0.1-rc1`) and push it. Runs the
   full pipeline, lands a `draft: true` release that Kaan can review and
   then delete. This is the recommended pre-launch confidence-check.

## Adding a new secret

1. **Settings → Secrets and variables → Actions → New repository secret.**
2. **Update this inventory** with secret name, consumer, and provenance.
3. **Update the workflow** `env:` block to surface the secret to the
   relevant step. Use `${{ secrets.XXX }}` form — never inline.
4. **Apply `set +x` discipline** if the value will be exported as a shell
   env var in a `run:` block. GitHub Actions auto-masks the value in its
   own output stream but the shell's xtrace would still expand it.
5. **Update `docs/release-process.md`** if the secret is user-facing
   (e.g., something Kaan must rotate or regenerate by hand).

## Don't commit secrets

The repo enforces three layers of secret-egress defence:

1. **`.gitignore` blocks** `.env`, `*.key`, `*.key.pub`, `*.p12`, `*.p8`,
   `tauri/src-tauri/keys/*.key*` (Phase 18 Plan 18-04).
2. **Pre-commit hook** (Phase 11 W1 `scripts.build_sidecar.assert_no_aiza_leak`)
   scans the build tree before sign + ship.
3. **`release.yml` verify stage** (Plan 18-01 `verify_binary.py`) scans the
   SIGNED bundle post-codesign / post-MSI and fails the workflow on any
   `AIza`/`AKIA`/`ya29.`/`sk-` pattern hit. Defence in depth: even if a
   developer accidentally bypasses the pre-commit hook, the release gate
   would still catch a leaked key before it ships.

## Rotating a leaked secret

If you suspect any secret in this table has leaked:

1. Revoke the upstream credential immediately (Apple Developer portal,
   SignPath dashboard, regenerate Tauri keypair).
2. Delete the GitHub Actions secret (Settings → Secrets → trash icon).
3. Add the replacement secret.
4. Re-run the last successful release tag's workflow to confirm CI is
   healthy on the new credentials.
5. If a release was published with the leaked secret in scope, follow
   `docs/release-process.md` §Rolling back a bad release — re-sign + re-
   publish that version's artifacts with the new credentials before
   considering the rotation complete.
