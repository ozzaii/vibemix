# vibemix — Tauri Updater Key Generation

> ONE-TIME setup, run on Kaan's local machine before the v0.1.0 release tag.
> The private key NEVER gets committed. Only the PUBLIC half (base64-encoded)
> goes into `tauri/src-tauri/tauri.conf.json5` as `plugins.updater.pubkey`.

## What lives here

NOTHING. The `keys/` directory exists so this README sits next to the
crate root for discoverability. The actual `.key` + `.key.pub` files
live OUTSIDE the repo at `~/.tauri/vibemix_updater.key{,.pub}` (or
Kaan's preferred path). The `.gitkeep` is what holds this empty
directory in git.

`.gitignore` blocks `tauri/src-tauri/keys/*.key` and
`tauri/src-tauri/keys/*.key.pub` as a defense-in-depth measure — if a
keypair is ever accidentally dropped into this directory, git refuses
to track it.

## Generation procedure

```sh
# 1. Generate the keypair (interactive — prompts for a passphrase).
npx @tauri-apps/cli signer generate -w ~/.tauri/vibemix_updater.key

# 2. Verify outputs.
ls -la ~/.tauri/vibemix_updater.key ~/.tauri/vibemix_updater.key.pub

# 3. Extract the public half as base64 for tauri.conf.json5.
cat ~/.tauri/vibemix_updater.key.pub | base64 | tr -d '\n'

# 4. Paste the result into tauri/src-tauri/tauri.conf.json5,
#    replacing the TAURI_UPDATER_PLACEHOLDER sentinel:
#      "pubkey": "dW50cnVzdGVkIGNvbW1lbnQ6IFRBVVJJX1VQREFURVJfUExBQ0VIT0xERVI="
#    becomes
#      "pubkey": "<the base64 string from step 3>"
```

## CI / GitHub secrets to set (Plan 18-05)

| Secret | Value source |
|--------|--------------|
| `TAURI_UPDATER_PRIVATE_KEY` | `cat ~/.tauri/vibemix_updater.key \| base64 \| tr -d '\n'` |
| `TAURI_UPDATER_KEY_PASSWORD` | The passphrase chosen at step 1 |

Plan 18-05's `.github/workflows/release.yml` grep-gates the literal
sentinel `TAURI_UPDATER_PLACEHOLDER` and refuses to build any tagged
release while the placeholder is still in `tauri.conf.json5`. CI also
checks that `TAURI_UPDATER_PRIVATE_KEY` + `TAURI_UPDATER_KEY_PASSWORD`
secrets are non-empty before invoking the signer.

## Rotating the key

If the private key is ever compromised:

  1. Generate a new keypair (same procedure as above).
  2. Update `tauri.conf.json5` `pubkey` to the new public half.
  3. Update GitHub secrets to the new private key + passphrase.
  4. Cut a new release. Existing installs WILL NOT auto-update to it
     — signature verification fails against the OLD pubkey baked into
     their installed binary. Communicate the issue + ask users to
     re-download from GitHub Releases manually.

This is the same trade-off as any signed-updater scheme. Document the
incident in `.planning/STATE.md` Open To-dos when rotating.

## Why minisign

Tauri 2.x updater uses `minisign-verify` for manifest signature
checking (see `Cargo.lock` for the `minisign_verify` crate). Minisign
is a small, audited, OpenBSD-derived signing tool; the `.key` file is
Ed25519-based. The public key is 32 bytes; the manifest signature is
64 bytes. Both fit comfortably in HTTP JSON.

## Cross-references

- `tauri/src-tauri/tauri.conf.json5` — `plugins.updater.pubkey` field
- `docs/updater.md` — manifest endpoint contract + rollback recipe
- `.github/workflows/release.yml` — orchestrator (Plan 18-05)
