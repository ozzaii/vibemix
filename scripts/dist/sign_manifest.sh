#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
#
# scripts/dist/sign_manifest.sh — Phase 18 Plan 18-05.
#
# Signs the Tauri updater manifest (`latest.json`) with the minisign-style
# Tauri signer keypair generated per `tauri/src-tauri/keys/README.md`.
# Called by `.github/workflows/release.yml`'s `release-publish` job after
# the macOS DMG + Windows MSI have been signed, notarized, and uploaded to
# the GitHub Release. Also runnable locally for Kaan's `workflow_dispatch`
# rehearsal flow (see `docs/release-process.md` §Manual rehearsal).
#
# Output schema (matches `docs/updater.md` §Manifest contract):
#   {
#     "version": "0.1.0",
#     "notes": "Release v0.1.0",
#     "pub_date": "2026-05-13T17:00:00Z",
#     "platforms": {
#       "darwin-aarch64": { "url": "...", "signature": "..." },
#       "windows-x86_64": { "url": "...", "signature": "..." }
#     }
#   }
#
# Required env vars (FAIL FAST if missing):
#   TAURI_UPDATER_PRIVATE_KEY    — base64-encoded contents of the private
#                                  `.key` file (the secret half of the
#                                  keypair; NEVER commit, NEVER log).
#   TAURI_UPDATER_KEY_PASSWORD   — passphrase chosen during
#                                  `npx @tauri-apps/cli signer generate`.
#
# Flags:
#   --version <semver>           — release version, e.g. 0.1.0
#   --macos-url <url>            — full URL to the signed DMG on the GitHub
#                                  Release (consumed by `tauri signer sign`)
#   --windows-url <url>          — full URL to the signed MSI
#   --notes <text>               — release notes (single-line)
#   --output <path>              — destination for the signed manifest JSON
#
# Hardening:
#   - `set -euo pipefail` + `set +x` so the private key never hits any log.
#   - The base64 private key is decoded into a temp file inside a
#     `mktemp -d` directory; a `trap` cleans the dir on EXIT/INT/TERM so a
#     crash or SIGTERM still scrubs the secret.
#   - `chmod 600` on the materialised key file.
#   - Tauri signer CLI is invoked via `npx --yes @tauri-apps/cli` — no
#     persistent install, no global state leak.
#
# Exit codes:
#   0 = success (manifest written to --output)
#   1 = generic failure (set -e cascade)
#   2 = usage / missing-required-flag / missing-required-env error
#   3 = tauri signer CLI failure on either platform
#
# References:
#   - tauri/src-tauri/keys/README.md (key generation procedure)
#   - docs/updater.md (manifest contract + rollback recipe)
#   - .github/workflows/release.yml `release-publish` job (CI caller)

set -euo pipefail
set +x   # private key value must NEVER appear in any log stream

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

VERSION=""
MACOS_URL=""
WINDOWS_URL=""
NOTES=""
OUTPUT=""

usage() {
    cat <<EOF >&2
sign_manifest.sh — Phase 18-05 Tauri updater manifest signer

Usage:
  sign_manifest.sh --version <semver> \\
                   --macos-url <url> \\
                   --windows-url <url> \\
                   --notes <text> \\
                   --output <path>

Required env: TAURI_UPDATER_PRIVATE_KEY, TAURI_UPDATER_KEY_PASSWORD
EOF
    exit 2
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --version)      VERSION="${2:-}";      shift 2 ;;
        --macos-url)    MACOS_URL="${2:-}";    shift 2 ;;
        --windows-url)  WINDOWS_URL="${2:-}";  shift 2 ;;
        --notes)        NOTES="${2:-}";        shift 2 ;;
        --output)       OUTPUT="${2:-}";       shift 2 ;;
        -h|--help)      usage ;;
        *)              echo "Unknown arg: $1" >&2; usage ;;
    esac
done

: "${TAURI_UPDATER_PRIVATE_KEY:?TAURI_UPDATER_PRIVATE_KEY env var required}"
: "${TAURI_UPDATER_KEY_PASSWORD:?TAURI_UPDATER_KEY_PASSWORD env var required}"
: "${VERSION:?--version required}"
: "${MACOS_URL:?--macos-url required}"
: "${WINDOWS_URL:?--windows-url required}"
: "${OUTPUT:?--output required}"

# ---------------------------------------------------------------------------
# Materialise the private key into a temp file with strict cleanup.
# ---------------------------------------------------------------------------

KEY_DIR=$(mktemp -d -t vibemix-updater-key.XXXXXX)
# shellcheck disable=SC2064
trap "rm -rf '$KEY_DIR'" EXIT INT TERM
KEY_PATH="$KEY_DIR/vibemix_updater.key"

# Decode base64 → key file. `--decode` is GNU/BSD-portable.
echo "$TAURI_UPDATER_PRIVATE_KEY" | base64 --decode > "$KEY_PATH"
chmod 600 "$KEY_PATH"

echo "[sign_manifest] signing manifest for vibemix v${VERSION}" >&2

# ---------------------------------------------------------------------------
# Sign each platform payload.
# ---------------------------------------------------------------------------
#
# `tauri signer sign` consumes a local file path OR a URL. For HTTP URLs the
# CLI downloads to a temp path first then signs the bytes — guaranteeing the
# manifest signature matches the exact bytes the updater plugin will fetch
# from GitHub Releases later.
#
# Output of `tauri signer sign` is the base64 minisign signature on stdout
# (along with diagnostic text on stderr). We capture stdout only.

sign_payload() {
    local label="$1"
    local url="$2"
    echo "[sign_manifest] signing $label payload: $url" >&2
    local sig
    if ! sig=$(npx --yes @tauri-apps/cli signer sign \
                --private-key-path "$KEY_PATH" \
                --password "$TAURI_UPDATER_KEY_PASSWORD" \
                "$url" 2>/dev/null); then
        echo "[sign_manifest] FATAL: tauri signer sign failed for $label ($url)" >&2
        exit 3
    fi
    # Trim whitespace and newlines.
    printf '%s' "$sig" | tr -d '\n\r '
}

MACOS_SIG=$(sign_payload "darwin-aarch64" "$MACOS_URL")
WINDOWS_SIG=$(sign_payload "windows-x86_64" "$WINDOWS_URL")

if [[ -z "$MACOS_SIG" || -z "$WINDOWS_SIG" ]]; then
    echo "[sign_manifest] FATAL: empty signature returned by tauri signer" >&2
    exit 3
fi

# ---------------------------------------------------------------------------
# Assemble the multi-platform manifest.
# ---------------------------------------------------------------------------

PUB_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

mkdir -p "$(dirname "$OUTPUT")"

# Escape JSON-special characters in NOTES (best-effort: backslashes + quotes).
NOTES_ESCAPED=$(printf '%s' "$NOTES" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g')

cat > "$OUTPUT" <<EOF
{
  "version": "$VERSION",
  "notes": "$NOTES_ESCAPED",
  "pub_date": "$PUB_DATE",
  "platforms": {
    "darwin-aarch64": {
      "url": "$MACOS_URL",
      "signature": "$MACOS_SIG"
    },
    "windows-x86_64": {
      "url": "$WINDOWS_URL",
      "signature": "$WINDOWS_SIG"
    }
  }
}
EOF

echo "[sign_manifest] signed manifest written: $OUTPUT" >&2
echo "$OUTPUT"
