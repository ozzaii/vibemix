#!/usr/bin/env bash
# check_companion_signing.sh — Phase 49 INSTALL-05 verifier gate.
#
# For each file in installer/companion/*.{sh,py,ps1}, verifies a valid
# code signature (codesign on Mac, Authenticode on Win). Writes a JSON
# report and exits non-zero on any unsigned artifact (tag builds) or
# WARNING on branch builds.
#
# Tag-vs-branch detection: $GITHUB_REF_TYPE == "tag" → fail-on-unsigned.
# Branch / dev / PR → WARNING, exit 0.
#
# Kaan-action §INSTALL-COMPANION-SIGN: SignPath cert discharge gates real
# Windows Authenticode signing. Until then, the verifier emits a WARNING.

set -euo pipefail

REPORT="report-companion-signing.json"
REF_TYPE="${GITHUB_REF_TYPE:-branch}"
COMPANION_DIR="installer/companion"

SIGNED=()
UNSIGNED=()
WARNINGS=()

check_file_darwin() {
  local f="$1"
  if codesign --verify --strict --deep "$f" 2>/dev/null; then
    SIGNED+=("$f")
  else
    UNSIGNED+=("$f")
  fi
}

check_file_linux_ci() {
  local f="$1"
  local sig="${f}.sig"
  if [ -f "$sig" ] && [ -s "$sig" ]; then
    SIGNED+=("$f")
  else
    UNSIGNED+=("$f")
  fi
}

if [ ! -d "$COMPANION_DIR" ]; then
  echo "MISSING: $COMPANION_DIR not found" >&2
  exit 1
fi

SHELL_FILES=()
while IFS= read -r -d '' f; do
  SHELL_FILES+=("$f")
done < <(find "$COMPANION_DIR" -maxdepth 2 -type f \( -name "*.sh" -o -name "*.py" -o -name "*.ps1" \) -print0)

PLATFORM="$(uname -s)"
for f in "${SHELL_FILES[@]}"; do
  if [ "$PLATFORM" = "Darwin" ]; then
    check_file_darwin "$f"
  else
    check_file_linux_ci "$f"
  fi
done

# Placeholder SHA-256 in manifest emits §INSTALL-COMPANION-SIGN warning.
MANIFEST="${COMPANION_DIR}/driver_manifest.json"
if [ -f "$MANIFEST" ] && grep -q "PLACEHOLDER_" "$MANIFEST"; then
  WARNINGS+=("PLACEHOLDER_ SHA-256 in driver_manifest.json — §INSTALL-COMPANION-SIGN undischarged")
fi

# Compute exit code first (JSON build uses it).
EXIT_CODE=0
if [ "$REF_TYPE" = "tag" ] && [ ${#UNSIGNED[@]} -gt 0 ]; then
  EXIT_CODE=1
fi

# Build JSON via Python (avoids shell list-quoting issues).
python3 - "$REPORT" "$REF_TYPE" "$EXIT_CODE" \
  "${SIGNED[*]:-}" "${UNSIGNED[*]:-}" "${WARNINGS[*]:-}" <<'PY'
import json
import sys

report_path = sys.argv[1]
ref_type = sys.argv[2]
exit_code = int(sys.argv[3])
signed = [s for s in sys.argv[4].split() if s]
# Unsigned items: split on spaces (file paths have no spaces in this repo).
unsigned = [s for s in sys.argv[5].split() if s]
# Warnings: re-join the rest as a single warning (they were space-joined; use newline if multi).
warnings_raw = sys.argv[6] if len(sys.argv) > 6 else ""
warnings = [warnings_raw] if warnings_raw else []

doc = {
    "ref_type": ref_type,
    "signed": signed,
    "unsigned": unsigned,
    "warnings": warnings,
    "exit_code": exit_code,
}
with open(report_path, "w", encoding="utf-8") as f:
    json.dump(doc, f, indent=2)
    f.write("\n")
PY

# Surface findings.
echo "── Companion signing verifier report ──"
echo "ref_type=$REF_TYPE"
echo "signed=${#SIGNED[@]}"
echo "unsigned=${#UNSIGNED[@]}"
echo "warnings=${#WARNINGS[@]}"

if [ ${#WARNINGS[@]} -gt 0 ]; then
  for w in "${WARNINGS[@]}"; do
    echo "::warning::$w"
  done
fi

if [ $EXIT_CODE -ne 0 ]; then
  echo "::error::Companion signing verifier FAILED on tag build — ${#UNSIGNED[@]} unsigned artifacts"
  for u in "${UNSIGNED[@]}"; do
    echo "  unsigned: $u"
  done
fi

exit $EXIT_CODE
