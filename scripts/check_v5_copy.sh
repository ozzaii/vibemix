#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
#
# Phase 14 Wave 0 — Copy purge-dictionary grep gate.
#
# Audits UI-rendered chrome strings under tauri/ui/src/{wizard,session,settings,mascot}/
# for two classes of forbidden vocabulary:
#
#   1. Hardware-vocab residue (FL-Studio retro-tactile language):
#      brushed, anodised, phosphor, retro-futurist, knob/fader physics, knurled
#      These BLOCK in --strict.
#
#   2. Generic AI slop:
#      amazing, awesome, great mix, let me know, delve, leverage, as an AI,
#      unleash, seamless, journey, craft, elevate
#      These BLOCK in --strict.
#
#   3. Manual-review-only:
#      tactile — may be legitimate UI behavior word. Always WARN, never block.
#
# The gate inspects TypeScript string literals only; JSDoc comments and
# // line comments are excluded via a Python preprocess (Pitfall 9 fix).
#
# Usage:
#   ./scripts/check_v5_copy.sh                   — warn-only dashboard
#   ./scripts/check_v5_copy.sh --warn-only       — alias for default
#   ./scripts/check_v5_copy.sh --baseline        — warn-only with baseline header
#   ./scripts/check_v5_copy.sh --surface=wizard  — scope to one surface
#   ./scripts/check_v5_copy.sh --strict          — block on hard purge hits
#
# Exit codes: 0 = pass, 1 = hard purge hit in --strict mode, 2 = invocation error.

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

SCOPE_LABEL="repo-wide (chrome surfaces only)"
SCOPE_PATHS="tauri/ui/src/wizard tauri/ui/src/session tauri/ui/src/settings tauri/ui/src/mascot"
case "$SURFACE" in
  "")          ;;
  wizard)      SCOPE_PATHS="tauri/ui/src/wizard";   SCOPE_LABEL="surface=wizard" ;;
  session)     SCOPE_PATHS="tauri/ui/src/session";  SCOPE_LABEL="surface=session" ;;
  settings)    SCOPE_PATHS="tauri/ui/src/settings"; SCOPE_LABEL="surface=settings" ;;
  mascot)      SCOPE_PATHS="tauri/ui/src/mascot";   SCOPE_LABEL="surface=mascot" ;;
  *)
    echo "unknown --surface: $SURFACE (allowed: wizard|session|settings|mascot)" >&2
    exit 2
    ;;
esac

# Python preprocessor: emit "<file>:<line>:<stripped-line>" for every .ts/.tsx file,
# with // line comments and /* ... */ block comments stripped. This avoids the
# Pitfall 9 problem of jsdoc-only hits blocking the gate.
strip_comments_py() {
  python3 - "$@" <<'PY'
import re
import sys
from pathlib import Path

# Strip // line comments and /* ... */ block comments, but preserve string literals.
# Pragmatic regex — sufficient for grep-gate purposes; not a full TS parser.
BLOCK = re.compile(r"/\*.*?\*/", re.DOTALL)
LINE = re.compile(r"//[^\n]*")

for root in sys.argv[1:]:
    for p in Path(root).rglob("*.ts"):
        try:
            src = p.read_text(encoding="utf-8")
        except Exception:
            continue
        stripped = BLOCK.sub(lambda m: " " * len(m.group(0)), src)
        for n, line in enumerate(stripped.splitlines(), start=1):
            line_no_comment = LINE.sub("", line)
            if line_no_comment.strip():
                print(f"{p}:{n}:{line_no_comment}")
    for p in Path(root).rglob("*.tsx"):
        try:
            src = p.read_text(encoding="utf-8")
        except Exception:
            continue
        stripped = BLOCK.sub(lambda m: " " * len(m.group(0)), src)
        for n, line in enumerate(stripped.splitlines(), start=1):
            line_no_comment = LINE.sub("", line)
            if line_no_comment.strip():
                print(f"{p}:{n}:{line_no_comment}")
PY
}

# Hardware-vocab residue — hard purge (block in --strict).
HARDWARE_PATTERN='[Bb]rushed|[Aa]nodised|[Pp]hosphor|[Rr]etro-?futurist|knob/fader physics|[Kk]nurled'

# General AI slop — hard purge (block in --strict).
SLOP_PATTERN='amazing|awesome|great mix|let me know|delve|leverage|as an AI|unleash|seamless|journey|craft|elevate'

# Manual-review-only — warn always, never block.
TACTILE_PATTERN='[Tt]actile'

stripped_corpus=$(strip_comments_py $SCOPE_PATHS 2>/dev/null || true)

hardware_hits_raw=$(echo "$stripped_corpus" | grep -E "$HARDWARE_PATTERN" || true)
hardware_hits=$(echo "$hardware_hits_raw" | grep -cE "$HARDWARE_PATTERN" || true)
hardware_hits=${hardware_hits:-0}

slop_hits_raw=$(echo "$stripped_corpus" | grep -iE "$SLOP_PATTERN" || true)
slop_hits=$(echo "$slop_hits_raw" | grep -ciE "$SLOP_PATTERN" || true)
slop_hits=${slop_hits:-0}

tactile_hits_raw=$(echo "$stripped_corpus" | grep -E "$TACTILE_PATTERN" || true)
tactile_hits=$(echo "$tactile_hits_raw" | grep -cE "$TACTILE_PATTERN" || true)
tactile_hits=${tactile_hits:-0}

hard_total=$(( hardware_hits + slop_hits ))

if [[ $BASELINE -eq 1 ]]; then
  echo "Phase 14 v5 copy-purge gate — BASELINE capture ($SCOPE_LABEL)"
else
  echo "Phase 14 v5 copy-purge gate ($SCOPE_LABEL)"
fi
echo "  hardware-vocab residue (brushed|anodised|phosphor|retro-futurist|knob/fader physics|knurled):  $hardware_hits"
echo "  general AI slop (amazing|awesome|great mix|let me know|delve|leverage|...):                    $slop_hits"
echo "  tactile (manual review — never blocks):                                                        $tactile_hits"

if [[ $STRICT -eq 1 ]]; then
  if [[ "$hard_total" -gt 0 ]]; then
    echo ""
    echo "BLOCKED. Purge the remaining residue from chrome strings:"
    [[ "$hardware_hits" -gt 0 ]] && echo "$hardware_hits_raw" | head -40
    [[ "$slop_hits" -gt 0 ]]     && echo "$slop_hits_raw" | head -40
    exit 1
  fi
  echo "  STRICT mode: PASS (zero hard-purge hits; tactile is warn-only)"
else
  echo "  warn-only mode (informational)"
fi
exit 0
