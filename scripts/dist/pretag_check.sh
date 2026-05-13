#!/usr/bin/env bash
# =============================================================================
# vibemix — Pre-Tag Readiness Gate (Phase 20 Plan 20 Task 6)
# =============================================================================
#
# Run this BEFORE `git tag v0.1.0`. Exit code 0 = ready. Non-zero = blockers.
#
# Checks (each prints PASS / FAIL with a reason):
#
#   1. Phase 16 ear-test signed off (`16-VERIFICATION.md` exists + passed)
#   2. Phase 17 grading sheet has ≥4 rater rows in `grading-sheet.csv`
#   3. README has no unresolved `<!-- TODO(kaan, pre-tag-v0.1.0): ... -->`
#   4. `tauri.conf.json5` does NOT contain the placeholder pubkey sentinel
#   5. Required GitHub secrets are configured (gh secret list)
#   6. README Discord link is no longer the TBD placeholder
#   7. Apple Developer ID cert is installed in local Keychain (macOS only)
#
# Steps 5–7 are skipped gracefully when `gh` / `security` unavailable
# (e.g. running in CI sandbox); they emit WARN instead of FAIL.
# =============================================================================

set -u

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

PASS=0
FAIL=0
WARN=0

ok()    { echo "  ✓ $1"; PASS=$((PASS+1)); }
no()    { echo "  ✗ $1"; FAIL=$((FAIL+1)); }
warn()  { echo "  ! $1"; WARN=$((WARN+1)); }

echo
echo "============================================================"
echo " vibemix — Pre-Tag Readiness Check"
echo "============================================================"
echo

# --- 1. Phase 16 ear-test signoff ----------------------------------------
echo "[1/7] Phase 16 ear-test signed off"
V16=".planning/phases/16-hallucination-verification-gate/16-VERIFICATION.md"
if [[ -f "$V16" ]] && grep -q "^status: passed" "$V16" 2>/dev/null; then
  ok "$V16 exists and status: passed"
else
  no "Phase 16 verification missing or not signed off — Kaan must DJ + sign off in $V16"
fi
echo

# --- 2. Phase 17 grading sheet has 4+ rows --------------------------------
echo "[2/7] Phase 17 reaction-reel grading has ≥4 raters"
G17="benchmarks/reaction_reel/grading-sheet.csv"
if [[ -f "$G17" ]]; then
  rows=$(($(wc -l < "$G17") - 1))  # minus header
  if (( rows >= 4 )); then
    ok "$G17 has $rows rater rows"
  else
    no "$G17 has only $rows rater rows (need ≥4)"
  fi
else
  no "$G17 missing — Phase 17 grading not run yet"
fi
echo

# --- 3. README has no unresolved pre-tag TODOs ----------------------------
echo "[3/7] README has no unresolved pre-tag TODOs"
if grep -q "TODO(kaan, pre-tag-v0.1.0)" README.md 2>/dev/null; then
  count=$(grep -c "TODO(kaan, pre-tag-v0.1.0)" README.md)
  no "$count unresolved pre-tag TODO marker(s) in README.md"
else
  ok "README clean"
fi
echo

# --- 4. Tauri pubkey is not the placeholder ------------------------------
echo "[4/7] Tauri updater pubkey is not the placeholder"
T_CONF="tauri/src-tauri/tauri.conf.json5"
if [[ -f "$T_CONF" ]]; then
  if grep -q "TAURI_UPDATER_PLACEHOLDER\|dW50cnVzdGVkIGNvbW1lbnQ6IFRBVVJJX1VQREFURVJfUExBQ0VIT0xERVI=" "$T_CONF"; then
    no "$T_CONF still contains the placeholder pubkey sentinel"
  else
    ok "$T_CONF has a real pubkey"
  fi
else
  warn "$T_CONF not found (Tauri shell not yet bootstrapped at this path)"
fi
echo

# --- 5. Required GitHub secrets configured -------------------------------
echo "[5/7] Required GitHub secrets configured"
REQUIRED=(
  APPLE_DEVELOPER_ID_P12_BASE64
  APPLE_DEVELOPER_ID_P12_PASSWORD
  APPLE_ID
  APPLE_APP_PASSWORD
  APPLE_TEAM_ID
  SIGNPATH_API_TOKEN
  SIGNPATH_ORGANIZATION_ID
  SIGNPATH_PROJECT_SLUG
  TAURI_UPDATER_PRIVATE_KEY
  TAURI_UPDATER_PRIVATE_KEY_PASSWORD
  BRAVOH_MANIFEST_UPLOAD_TOKEN
)
if command -v gh >/dev/null 2>&1; then
  if gh auth status >/dev/null 2>&1; then
    secrets_list=$(gh secret list --json name -q '.[].name' 2>/dev/null || true)
    missing=()
    for s in "${REQUIRED[@]}"; do
      if ! echo "$secrets_list" | grep -qx "$s"; then
        missing+=("$s")
      fi
    done
    if (( ${#missing[@]} == 0 )); then
      ok "all ${#REQUIRED[@]} required secrets configured"
    else
      no "missing secret(s): ${missing[*]}"
    fi
  else
    warn "gh CLI present but not authenticated — run 'gh auth login'"
  fi
else
  warn "gh CLI not installed — cannot verify GitHub secrets remotely"
fi
echo

# --- 6. Discord invite is no longer TBD ----------------------------------
echo "[6/7] Discord invite link is real"
if grep -qE "^Discord: \*\*TBD\*\*" README.md 2>/dev/null; then
  no "README still has Discord: **TBD** placeholder"
elif grep -qE "discord\.gg/[A-Za-z0-9]+" README.md 2>/dev/null; then
  ok "README has a real discord.gg invite link"
else
  warn "README has no Discord line at all — was the placeholder removed without replacement?"
fi
echo

# --- 7. Apple Dev ID cert in local Keychain (macOS only) -----------------
echo "[7/7] Apple Developer ID cert in local Keychain"
if [[ "$(uname -s)" == "Darwin" ]] && command -v security >/dev/null 2>&1; then
  if security find-identity -v -p codesigning 2>/dev/null | grep -q "Developer ID Application:"; then
    ident=$(security find-identity -v -p codesigning 2>/dev/null | grep -m1 "Developer ID Application:" | sed 's/.*"\(.*\)".*/\1/')
    ok "found: $ident"
  else
    no "no 'Developer ID Application' identity found in local Keychain"
  fi
else
  warn "not on macOS or 'security' unavailable — skipping Keychain check"
fi
echo

echo "============================================================"
echo " RESULT: $PASS pass / $FAIL fail / $WARN warn"
echo "============================================================"

if (( FAIL > 0 )); then
  echo
  echo " ✗ NOT READY TO TAG. Resolve failures above first."
  exit 1
fi

if (( WARN > 0 )); then
  echo
  echo " ⚠ READY TO TAG with $WARN warning(s). Review warnings before pushing."
fi

exit 0
