#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
#
# Phase 14 Wave 0 — Forbidden font-family declaration gate.
#
# Blocks `font-family:` declarations of FL-Studio-era families and any
# alternate display/mono family the v5 spec rejects. The allowlist is
# `var(--type-display|--type-body|--type-mono)` chains in component CSS —
# all consumer code must source typography through tokens.css, never via a
# raw family name in a component CSS string.
#
# Usage:
#   ./scripts/check_v5_fonts.sh                   — warn-only dashboard
#   ./scripts/check_v5_fonts.sh --warn-only       — alias for default
#   ./scripts/check_v5_fonts.sh --baseline        — warn-only with baseline header
#   ./scripts/check_v5_fonts.sh --surface=wizard  — scope to one surface
#   ./scripts/check_v5_fonts.sh --strict          — block on any hit
#
# Exit codes: 0 = pass, 1 = forbidden font found in --strict mode, 2 = invocation error.

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
      exit 2
      ;;
  esac
done

cd "$(git rev-parse --show-toplevel)"

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

# Forbidden families inside component CSS strings (declared via font-family: "Name").
# tokens.css is the only allowed declaration site for these families' @font-face blocks,
# and even there only Saira + JetBrains Mono survive after Wave 5 deletes the legacy block.
# Per Pitfall 9: scope to `font-family:` declarations (NOT comments / jsdoc).
FORBIDDEN_FONT_PATTERN='font-family:[[:space:]]*["'\''"]?(Workbench|DM Mono|DSEG7|Caveat|Geist|Fraunces|Inter)["'\''"]?'

# system-ui as a primary face (i.e. NOT inside a var(--type-*) fallback chain in tokens.css).
# Heuristic: flag `font-family: system-ui` in consumer files; tokens.css is excluded.
SYSTEM_UI_PATTERN='font-family:[[:space:]]*system-ui'

font_hits_raw=$(grep -rnE "$FORBIDDEN_FONT_PATTERN" "$SCOPE_PATH" \
  --include='*.ts' --include='*.tsx' --include='*.css' \
  2>/dev/null || true)
font_hits=$(echo "$font_hits_raw" | grep -cE "$FORBIDDEN_FONT_PATTERN" || true)
font_hits=${font_hits:-0}

system_ui_hits_raw=$(grep -rnE "$SYSTEM_UI_PATTERN" "$SCOPE_PATH" \
  --include='*.ts' --include='*.tsx' --include='*.css' \
  2>/dev/null | grep -v 'tokens.css' || true)
system_ui_hits=$(echo "$system_ui_hits_raw" | grep -cE "$SYSTEM_UI_PATTERN" || true)
system_ui_hits=${system_ui_hits:-0}

total_hits=$(( font_hits + system_ui_hits ))

if [[ $BASELINE -eq 1 ]]; then
  echo "Phase 14 v5 forbidden-fonts gate — BASELINE capture ($SCOPE_LABEL)"
else
  echo "Phase 14 v5 forbidden-fonts gate ($SCOPE_LABEL)"
fi
echo "  forbidden font-family declarations (Workbench|DM Mono|DSEG7|Caveat|Geist|Fraunces|Inter):  $font_hits"
echo "  consumer-side system-ui as primary (outside tokens.css):                                   $system_ui_hits"

if [[ $STRICT -eq 1 ]]; then
  if [[ "$total_hits" -gt 0 ]]; then
    echo ""
    echo "BLOCKED. Migrate the remaining font-family declarations to var(--type-*):"
    [[ "$font_hits" -gt 0 ]]       && echo "$font_hits_raw" | head -40
    [[ "$system_ui_hits" -gt 0 ]]  && echo "$system_ui_hits_raw" | head -20
    exit 1
  fi
  echo "  STRICT mode: PASS (zero hits)"
else
  echo "  warn-only mode (informational)"
fi
exit 0
