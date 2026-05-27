#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
#
# scripts/dist/sign_manifest.sh — Phase 18 Plan 18-05.
#
# Signs the Tauri updater manifest (`latest.json`) with the minisign-style
# Tauri signer keypair generated per `tauri/src-tauri/keys/README.md`.
# Called by `.github/workflows/release.yml`'s `release-publish` job after
# the macOS/Windows updater artifacts have been signed/notarized. The signer
# signs the local updater artifact bytes and writes the public release URLs into
# the manifest. Also runnable locally for Kaan's `workflow_dispatch` rehearsal
# flow (see `docs/release-process.md` §Manual rehearsal).
#
# Output schema (matches `docs/updater.md` §Manifest contract):
#   {
#     "version": "0.1.0",
#     "notes": "Release v0.1.0",
#     "pub_date": "2026-05-13T17:00:00Z",
#     "platforms": {
#       "darwin-aarch64": { "url": "...", "signature": "..." },
#       "darwin-x86_64": { "url": "...", "signature": "..." },
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
#                                  May be intentionally empty, but the env var
#                                  must still be present.
#
# Flags:
#   --version <semver>           — release version, e.g. 0.1.0
#   --macos-artifact <path>      — local signed arm64 `.app.tar.gz` artifact
#   --macos-url <url>            — public arm64 URL written into latest.json
#   --macos-x86_64-artifact <path> — local signed x86_64 `.app.tar.gz`
#   --macos-x86_64-url <url>     — public x86_64 URL written into latest.json
#   --windows-artifact <path>    — local signed Tauri NSIS setup EXE
#   --windows-url <url>          — public URL written into latest.json
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
MACOS_ARTIFACT=""
MACOS_X86_64_URL=""
MACOS_X86_64_ARTIFACT=""
WINDOWS_URL=""
WINDOWS_ARTIFACT=""
NOTES=""
OUTPUT=""

usage() {
    cat <<EOF >&2
sign_manifest.sh — Phase 18-05 Tauri updater manifest signer

Usage:
  sign_manifest.sh --version <semver> \\
                   --macos-artifact <path> \\
                   --macos-url <url> \\
                   --macos-x86_64-artifact <path> \\
                   --macos-x86_64-url <url> \\
                   --windows-artifact <path> \\
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
        --macos-artifact)        MACOS_ARTIFACT="${2:-}";        shift 2 ;;
        --macos-url)             MACOS_URL="${2:-}";             shift 2 ;;
        --macos-x86_64-artifact) MACOS_X86_64_ARTIFACT="${2:-}"; shift 2 ;;
        --macos-x86_64-url)      MACOS_X86_64_URL="${2:-}";      shift 2 ;;
        --windows-artifact)      WINDOWS_ARTIFACT="${2:-}";      shift 2 ;;
        --windows-url)           WINDOWS_URL="${2:-}";           shift 2 ;;
        --notes)                 NOTES="${2:-}";                 shift 2 ;;
        --output)                OUTPUT="${2:-}";                shift 2 ;;
        -h|--help)               usage ;;
        *)                       echo "Unknown arg: $1" >&2; usage ;;
    esac
done

: "${TAURI_UPDATER_PRIVATE_KEY:?TAURI_UPDATER_PRIVATE_KEY env var required}"
if [[ -z "${TAURI_UPDATER_KEY_PASSWORD+x}" ]]; then
    echo "[sign_manifest] FATAL: TAURI_UPDATER_KEY_PASSWORD env var required (may be empty)" >&2
    exit 2
fi
: "${VERSION:?--version required}"
: "${MACOS_ARTIFACT:?--macos-artifact required}"
: "${MACOS_URL:?--macos-url required}"
: "${MACOS_X86_64_ARTIFACT:?--macos-x86_64-artifact required}"
: "${MACOS_X86_64_URL:?--macos-x86_64-url required}"
: "${WINDOWS_ARTIFACT:?--windows-artifact required}"
: "${WINDOWS_URL:?--windows-url required}"
: "${OUTPUT:?--output required}"

for artifact in "$MACOS_ARTIFACT" "$MACOS_X86_64_ARTIFACT" "$WINDOWS_ARTIFACT"; do
    if [[ ! -f "$artifact" ]]; then
        echo "[sign_manifest] FATAL: artifact not found: $artifact" >&2
        exit 2
    fi
done

if [[ "$MACOS_ARTIFACT" != *.app.tar.gz ]]; then
    echo "[sign_manifest] FATAL: macOS updater artifact must be Tauri's .app.tar.gz bundle, not a DMG: $MACOS_ARTIFACT" >&2
    exit 2
fi
if [[ "$MACOS_X86_64_ARTIFACT" != *.app.tar.gz ]]; then
    echo "[sign_manifest] FATAL: macOS x86_64 updater artifact must be Tauri's .app.tar.gz bundle, not a DMG: $MACOS_X86_64_ARTIFACT" >&2
    exit 2
fi

WIN_NAME=$(basename "$WINDOWS_ARTIFACT")
if [[ "$WIN_NAME" == "vibemix-installer.exe" ]]; then
    echo "[sign_manifest] FATAL: Windows updater artifact must not be the Inno first-install EXE: $WINDOWS_ARTIFACT" >&2
    exit 2
fi
if [[ "$WIN_NAME" != *setup*.exe ]]; then
    echo "[sign_manifest] FATAL: Windows updater artifact must be a Tauri NSIS setup EXE: $WINDOWS_ARTIFACT" >&2
    exit 2
fi

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
# `tauri signer sign` signs a local artifact file. The manifest stores the
# public URL where the same bytes will be uploaded by the release job.
#
# Output of `tauri signer sign` is the base64 minisign signature on stdout
# (along with diagnostic text on stderr). We capture stdout only.

sign_payload() {
    local label="$1"
    local artifact="$2"
    local url="$3"
    echo "[sign_manifest] signing $label payload bytes: $artifact (manifest URL: $url)" >&2
    local sig
    if ! sig=$(npx --yes @tauri-apps/cli signer sign \
                --private-key-path "$KEY_PATH" \
                --password "$TAURI_UPDATER_KEY_PASSWORD" \
                "$artifact" 2>/dev/null); then
        echo "[sign_manifest] FATAL: tauri signer sign failed for $label ($artifact)" >&2
        exit 3
    fi
    # Trim whitespace and newlines.
    printf '%s' "$sig" | tr -d '\n\r '
}

MACOS_SIG=$(sign_payload "darwin-aarch64" "$MACOS_ARTIFACT" "$MACOS_URL")
MACOS_X86_64_SIG=$(sign_payload "darwin-x86_64" "$MACOS_X86_64_ARTIFACT" "$MACOS_X86_64_URL")
WINDOWS_SIG=$(sign_payload "windows-x86_64" "$WINDOWS_ARTIFACT" "$WINDOWS_URL")

if [[ -z "$MACOS_SIG" || -z "$MACOS_X86_64_SIG" || -z "$WINDOWS_SIG" ]]; then
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
    "darwin-x86_64": {
      "url": "$MACOS_X86_64_URL",
      "signature": "$MACOS_X86_64_SIG"
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
