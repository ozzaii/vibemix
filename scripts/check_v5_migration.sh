#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
#
# Phase 14 Wave 0 — CDJ Whisper v5 shim-removal gate.
#
# Runs as informational dashboard during Waves 1-4 (default warn-only),
# and as a blocking pre-commit hook on the Wave 5 shim-delete commit
# (--strict). The script never modifies the repo — it only reports.
#
# Usage:
#   ./scripts/check_v5_migration.sh                   — warn-only dashboard
#   ./scripts/check_v5_migration.sh --warn-only       — alias for default
#   ./scripts/check_v5_migration.sh --baseline        — warn-only with baseline header
#   ./scripts/check_v5_migration.sh --surface=wizard  — scope to one surface
#   ./scripts/check_v5_migration.sh --strict          — block on any hit
#
# Surfaces: wizard | session | settings | mascot
#
# Exit codes: 0 = pass, 1 = legacy refs found in --strict mode, 2 = invocation error.

set -euo pipefail

STRICT=0
BASELINE=0
SURFACE=""

for arg in "$@"; do
  case "$arg" in
    --strict)        STRICT=1 ;;
    --warn-only)     STRICT=0 ;;
    --baseline)      BASELINE=1; STRICT=0 ;;
    --surface=*)     SURFACE="${arg#--surface=}" ;;
    -h|--help)
      sed -n '1,30p' "$0"
      exit 0
      ;;
    *)
      echo "unknown arg: $arg" >&2
      echo "  usage: $0 [--strict|--warn-only|--baseline] [--surface=<wizard|session|settings|mascot>]" >&2
      exit 2
      ;;
  esac
done

# Move to repo root regardless of cwd
cd "$(git rev-parse --show-toplevel)"

# Scope path: full tauri/ui/src/ or per-surface subset.
SCOPE_PATH="tauri/ui/src/"
SCOPE_LABEL="repo-wide"
case "$SURFACE" in
  "")          ;;
  wizard)      SCOPE_PATH="tauri/ui/src/wizard/";   SCOPE_LABEL="surface=wizard" ;;
  session)     SCOPE_PATH="tauri/ui/src/session/";  SCOPE_LABEL="surface=session" ;;
  settings)    SCOPE_PATH="tauri/ui/src/settings/"; SCOPE_LABEL="surface=settings" ;;
  mascot)      SCOPE_PATH="tauri/ui/src/mascot/";   SCOPE_LABEL="surface=mascot" ;;
  *)
    echo "unknown --surface: $SURFACE (allowed: wizard|session|settings|mascot)" >&2
    exit 2
    ;;
esac

# Legacy CSS-token refs outside tokens.css (the shim file itself is the deletion target).
# Includes --charcoal (defence in depth even though not in current shim) and --col-mascot.
# Excludes --cue (Phase 11 invariant: declared-forbidden but never consumed — not part of migration).
LEGACY_TOKEN_PATTERN='--(phosphor(-warm|-dim|-soft|-glow|-halo)?|brushed-(hi|lo)|bezel-[123]|panel(-lift|-deep|-hover-top|-pressed-bottom)?|groove|ink(-dim|-deep|-engraved)?|charcoal|col-mascot)\b'

# Run the grep — tolerate "no matches" exit code 1 by adding `|| true` BEFORE pipe.
# Use `-e PATTERN` so BSD grep doesn't try to parse `--` as a flag prefix.
# Note: tokens.css filter applied after grep because the shim itself is the deletion target.
token_hits_raw=$(grep -rnE -e "$LEGACY_TOKEN_PATTERN" "$SCOPE_PATH" \
  --include='*.ts' --include='*.tsx' --include='*.css' --include='*.html' \
  2>/dev/null || true)
# Filter out the shim's own definitions in tokens.css (the migration target), then count.
token_hits=$(echo "$token_hits_raw" | grep -v 'tokens.css' | grep -cE -e "$LEGACY_TOKEN_PATTERN" || true)
token_hits=${token_hits:-0}

if [[ $BASELINE -eq 1 ]]; then
  echo "Phase 14 v5 migration gate — BASELINE capture ($SCOPE_LABEL)"
else
  echo "Phase 14 v5 migration gate ($SCOPE_LABEL)"
fi
echo "  legacy CSS-token refs (outside tokens.css):    $token_hits"

if [[ $STRICT -eq 1 ]]; then
  if [[ "$token_hits" -gt 0 ]]; then
    echo ""
    echo "BLOCKED. Migrate the remaining refs before deleting the shim:"
    echo "$token_hits_raw" | grep -v 'tokens.css' | head -40
    exit 1
  fi
  echo "  STRICT mode: PASS (zero hits)"
else
  if [[ "$token_hits" -gt 0 ]]; then
    echo "  warn-only mode (informational)  — top 5 ref sites:"
    echo "$token_hits_raw" | grep -v 'tokens.css' | head -5 | sed 's/^/    /'
  else
    echo "  warn-only mode (informational)"
  fi
fi
exit 0
