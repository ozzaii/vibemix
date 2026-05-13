# vibemix — Auto-Updater Reference

> Tauri's built-in updater plugin (`tauri-plugin-updater` 2.10) checks a
> signed manifest at every launch (if the user has not opted out) and
> prompts to install if a newer signed binary is available. This doc
> explains the manifest contract, how Kaan publishes a new release, and
> how to roll back a bad release.

The Rust-side dispatcher lives in `tauri/src-tauri/src/updater.rs`; the
endpoint + pubkey configuration lives in
`tauri/src-tauri/tauri.conf.json5` (`plugins.updater.*`). Plan 18-05's
release workflow signs the manifest and POSTs it to the Bravoh proxy on
tag push.

## How it works (user perspective)

1. App launches.
2. Within ~2 seconds of boot, the Tauri shell fires a `GET` against
   `https://api.altidus.world/vibemix/updates/<target>/<arch>/<current_version>`.
   This is the lowest-priority boot task — runs AFTER the sidecar, WS
   client, and tray are already up.
3. Server responds `204 No Content` (you're on the latest) — no UI.
4. Or server responds `200 OK` with a signed manifest — Tauri shows the
   standard dialog: "A new version of vibemix is available: 0.1.4
   (release notes). Install now?".
5. On **Yes**: download → verify signature against the `pubkey` baked
   into the running app → install → restart. On **No**: dismissed for
   this launch; check happens again next launch.
6. Failure modes (network offline, manifest 404, signature mismatch,
   manifest server down): logged at WARN level in `sidecar.log` and
   exited silently. The user keeps the running version. **The updater
   MUST NEVER bail boot.**

## Opt-out

`update_check_on_launch` (bool, default `true`) lives in the OS-standard
config file:

| OS | Path |
|----|------|
| macOS | `~/Library/Application Support/vibemix/config.json` |
| Windows | `%APPDATA%\vibemix\config.json` |

Set the key to `false` to disable boot-time checking. The Phase 19
Settings drawer is expected to surface a toggle for this; meanwhile,
end users can edit the file manually:

```json
{
  "first_run_completed": true,
  "voice": "kore",
  "mode": "coach",
  "update_check_on_launch": false,
  "...": "..."
}
```

Save → restart app → no more update prompts. The Rust shell reads this
key directly via `tauri-plugin-store` (see
`tauri/src-tauri/src/updater.rs::check_on_launch_enabled`). The Python
sidecar's `ConfigStore` preserves the key on round-trip (per
`src/vibemix/runtime/config_store.py` header lines 14-22) — neither side
stomps the other.

## Manifest Contract

`GET /vibemix/updates/{target}/{arch}/{current_version}` on
`api.altidus.world`.

| Path param | Possible values |
|------------|-----------------|
| `target` | `darwin`, `windows` |
| `arch` | `aarch64`, `x86_64` |
| `current_version` | running app's semver, e.g. `0.1.0` |

Server logic:

- Look up the latest signed manifest for `(target, arch)`.
- If `latest.version <= current_version`: respond `204 No Content`.
- Else respond `200 OK` with the signed manifest JSON:
  ```json
  {
    "version": "0.1.4",
    "url": "https://github.com/<owner>/vibemix/releases/download/v0.1.4/vibemix-0.1.4-aarch64-apple-darwin.dmg",
    "signature": "<minisign-signature-base64-of-the-dmg>",
    "notes": "Fixes mic gating regression. Improves Windows DDJ-FLX4 hot-plug.",
    "pub_date": "2026-06-15T18:00:00Z"
  }
  ```

`signature` is the minisign signature of the binary at `url`, signed
with the private half of the keypair documented in
`tauri/src-tauri/keys/README.md`. Tauri verifies the signature against
the `pubkey` baked into the running app (committed to
`tauri.conf.json5` at build time). Mismatched / forged signatures are
rejected silently; the running app keeps its version. The TLS layer
protects manifest delivery in transit, but the signature is the
real trust anchor — even a compromised manifest server cannot push
malicious updates without the private key.

## Key Setup

See `tauri/src-tauri/keys/README.md` for the one-time key-generation
procedure. Summary:

1. `npx @tauri-apps/cli signer generate -w ~/.tauri/vibemix_updater.key`
2. `cat ~/.tauri/vibemix_updater.key.pub | base64 | tr -d '\n'` → paste
   into `tauri.conf.json5` `plugins.updater.pubkey`, replacing the
   `TAURI_UPDATER_PLACEHOLDER` sentinel.
3. Store the matching private-key base64 + passphrase as GitHub repo
   secrets `TAURI_UPDATER_PRIVATE_KEY` + `TAURI_UPDATER_KEY_PASSWORD`.

Plan 18-05's `.github/workflows/release.yml` refuses to build any
tagged release while the placeholder string `TAURI_UPDATER_PLACEHOLDER`
is still present in `tauri.conf.json5`. PR builds skip the sign + publish
steps silently when the placeholder is present (mock-signing dry-run).

## Publishing a release (Plan 18-05)

The `.github/workflows/release.yml` workflow does the following on `v*`
tag push:

1. Build + sign + notarize + DMG / MSI (Plans 18-01 through 18-03).
2. Upload the signed DMG / MSI to the GitHub Release at the matching
   tag.
3. Sign the manifest with `npx @tauri-apps/cli signer sign` (using
   `TAURI_UPDATER_PRIVATE_KEY` + `TAURI_UPDATER_KEY_PASSWORD` from
   GitHub secrets).
4. `curl POST` the signed manifest to a Bravoh-proxy endpoint on
   `api.altidus.world` (TODO: endpoint not yet implemented on the
   proxy side — out of scope for Phase 18; Bravoh ops adds the
   endpoint in a separate hand-off).

Until the Bravoh proxy endpoint ships, the updater will receive HTTP
`404 Not Found` and silently keep the running version. This is OK for
v0.1.0 — manual `https://github.com/<owner>/vibemix/releases` downloads
are the primary acquisition path.

## Rollback

Per `.planning/phases/18-distribution-signing-notarization-installers/18-CONTEXT.md` §deferred,
full rollback automation is v2. For v1, the manual procedure:

1. Identify the bad tag (e.g. `v0.1.4`).
2. Delete the GitHub Release + tag:
   ```sh
   gh release delete v0.1.4 --yes
   git tag -d v0.1.4
   git push origin :refs/tags/v0.1.4
   ```
3. Republish the previous release's manifest as `latest` on the
   `api.altidus.world` side (procedure owned by Bravoh ops; for now
   this means re-pointing `v0.1.3` after deleting v0.1.4 from the
   proxy's manifest cache).
4. Communicate the rollback in the GitHub Releases page (the old
   release notes for v0.1.4 stay deleted; users who already installed
   0.1.4 keep it until the next published release — there is no
   client-side push to downgrade them).
5. Ship the FIX in `v0.1.5` ASAP so the affected users get a real
   upgrade path.

## Why minisign?

Tauri 2.x updater uses `minisign-verify` for manifest signature
checking (see `Cargo.lock` for the `minisign_verify` crate). Minisign
is a small, audited, OpenBSD-derived signing tool; the keypair is
Ed25519-based. The public key is 32 bytes; the manifest signature is
64 bytes. Both fit comfortably in HTTP JSON.

## Day-1 reputation

SmartScreen + Gatekeeper reputation builds across the first ~few
thousand installs of a new cert (see `docs/signing-windows.md` for the
SmartScreen warm-up note). The updater does NOT need separate reputation
— Tauri verifies the manifest signature locally before download, then
re-checks the installer's OS-level signature (codesign / SignPath) on
install. Two independent verification layers.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| No update prompt ever | `update_check_on_launch: false` in `config.json` | Edit to `true`, restart |
| "Update available" but install fails silently | Signature mismatch (rotated key) | Manual download from GitHub Releases |
| `updater: check failed` line in `sidecar.log` | Manifest server unreachable | Check `https://api.altidus.world/healthz` |
| Update appears too aggressively | Future Phase 19 Settings UI will let you disable | For now edit `config.json` |
| Build refuses with "placeholder still present" | Pre-v0.1.0 key not yet generated | Follow `tauri/src-tauri/keys/README.md` |

## Related Docs

- `docs/signing-macos.md` — codesign + notarize bench (Plan 18-02)
- `docs/signing-windows.md` — SignPath OV signing (Plan 18-03)
- `tauri/src-tauri/keys/README.md` — minisign key generation playbook
- `tauri/src-tauri/src/updater.rs` — Rust dispatcher (boot-time gate)
- `tauri/src-tauri/tauri.conf.json5` — `plugins.updater.*` config
- `.github/workflows/release.yml` — orchestrator (Plan 18-05)
