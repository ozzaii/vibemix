#!/usr/bin/env bash
# Phase 46 / DEPS-07 — pinact runner.
#
# Modes:
#   --check  : verify every uses: line is SHA-pinned; exit 1 on violations.
#              (CI gate via .github/workflows/dep-audit.yml::pinact-audit)
#   --apply  : mechanically rewrite tag refs to SHA + version-comment form.
#              (Local re-run after a Dependabot bump.)
#
# Tool:  pinact v3.3.0 (suzuki-shunsuke/pinact)
# Install:
#   - CI: this script installs the binary inline
#   - Local: brew install pinact  OR  go install github.com/suzuki-shunsuke/pinact/cmd/pinact@v3.3.0

set -euo pipefail

MODE="${1:-}"

PINACT_VERSION="3.3.0"

install_pinact() {
  if command -v pinact >/dev/null 2>&1; then
    return 0
  fi
  OS="$(uname -s | tr '[:upper:]' '[:lower:]')"
  ARCH="$(uname -m)"
  case "$ARCH" in
    x86_64) ARCH="amd64" ;;
    aarch64|arm64) ARCH="arm64" ;;
  esac
  TARBALL="pinact_${OS}_${ARCH}.tar.gz"
  URL="https://github.com/suzuki-shunsuke/pinact/releases/download/v${PINACT_VERSION}/${TARBALL}"
  curl -sSL -o /tmp/pinact.tar.gz "$URL"
  tar -xzf /tmp/pinact.tar.gz -C /tmp pinact
  sudo mv /tmp/pinact /usr/local/bin/pinact
  sudo chmod +x /usr/local/bin/pinact
}

case "$MODE" in
  --check)
    install_pinact
    pinact run --check
    ;;
  --apply)
    install_pinact
    pinact run
    echo "pinact applied — review the diff and commit."
    ;;
  *)
    echo "Usage: $0 [--check|--apply]" >&2
    exit 2
    ;;
esac
