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
#   5. Bundled sidecar resource tree is real, executable, and not placeholder-only
#   6. Required GitHub secrets are configured (gh secret list)
#   7. README Discord link is no longer the TBD placeholder
#   8. Apple Developer ID cert is installed in local Keychain (macOS only)
#
# Steps 6–8 are skipped gracefully when `gh` / `security` unavailable
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
echo "[1/8] Phase 16 ear-test signed off"
V16=".planning/phases/16-hallucination-verification-gate/16-VERIFICATION.md"
if [[ -f "$V16" ]] && grep -q "^status: passed" "$V16" 2>/dev/null; then
  ok "$V16 exists and status: passed"
else
  no "Phase 16 verification missing or not signed off — Kaan must DJ + sign off in $V16"
fi
echo

# --- 2. Phase 17 grading sheet has 4+ rows --------------------------------
# RC-tag mode (VIBEMIX_PRETAG_RC=1) softens this gate to warn-level: 4-rater
# reaction-reel grading is a stable-release signal, not an rc gate. An rc tag
# IS the "test in the wild" cut; gather rater feedback against the rc binary
# itself, then enforce the gate before promoting to v0.1.0 stable.
echo "[2/8] Phase 17 reaction-reel grading has ≥4 raters"
G17="benchmarks/reaction_reel/grading-sheet.csv"
if [[ -f "$G17" ]]; then
  rows=$(($(wc -l < "$G17") - 1))  # minus header
  if (( rows >= 4 )); then
    ok "$G17 has $rows rater rows"
  elif [[ "${VIBEMIX_PRETAG_RC:-0}" == "1" ]]; then
    warn "$G17 has only $rows rater rows (need ≥4 for stable; deferred for rc tag)"
  else
    no "$G17 has only $rows rater rows (need ≥4)"
  fi
else
  if [[ "${VIBEMIX_PRETAG_RC:-0}" == "1" ]]; then
    warn "$G17 missing — Phase 17 grading deferred for rc tag (required before v0.1.0 stable)"
  else
    no "$G17 missing — Phase 17 grading not run yet"
  fi
fi
echo

# --- 3. README has no unresolved pre-tag TODOs ----------------------------
echo "[3/8] README has no unresolved pre-tag TODOs"
if grep -q "TODO(kaan, pre-tag-v0.1.0)" README.md 2>/dev/null; then
  count=$(grep -c "TODO(kaan, pre-tag-v0.1.0)" README.md)
  no "$count unresolved pre-tag TODO marker(s) in README.md"
else
  ok "README clean"
fi
echo

# --- 4. Tauri pubkey is not the placeholder ------------------------------
echo "[4/8] Tauri updater pubkey is not the placeholder"
T_CONF="tauri/src-tauri/tauri.conf.json5"
if [[ -f "$T_CONF" ]]; then
  # Only inspect the actual pubkey JSON value, not the surrounding comments
  # (the comment block intentionally documents the sentinel string).
  pubkey_line=$(grep -E '^\s*"pubkey":' "$T_CONF" | head -1)
  if echo "$pubkey_line" | grep -q "TAURI_UPDATER_PLACEHOLDER\|dW50cnVzdGVkIGNvbW1lbnQ6IFRBVVJJX1VQREFURVJfUExBQ0VIT0xERVI="; then
    no "$T_CONF pubkey value is still the placeholder sentinel"
  elif [[ -z "$pubkey_line" ]]; then
    no "$T_CONF has no \"pubkey\" line"
  else
    ok "$T_CONF has a real pubkey"
  fi
else
  warn "$T_CONF not found (Tauri shell not yet bootstrapped at this path)"
fi
echo

# --- 5. Bundled sidecar resource tree ready -------------------------------
echo "[5/8] Bundled sidecar resource tree ready"
if command -v uv >/dev/null 2>&1; then
  SIDECAR_CHECK=(uv run python scripts/dist/check_sidecar_bundle_ready.py --quiet)
elif command -v python3 >/dev/null 2>&1; then
  SIDECAR_CHECK=(python3 scripts/dist/check_sidecar_bundle_ready.py --quiet)
elif command -v python >/dev/null 2>&1; then
  SIDECAR_CHECK=(python scripts/dist/check_sidecar_bundle_ready.py --quiet)
else
  SIDECAR_CHECK=()
fi

if (( ${#SIDECAR_CHECK[@]} == 0 )); then
  no "Python not found — cannot verify bundled sidecar resource tree"
elif sidecar_check_out=$("${SIDECAR_CHECK[@]}" 2>&1); then
  ok "bundled sidecar resource tree is ready"
else
  no "bundled sidecar resource tree is not ready"
  printf '%s\n' "$sidecar_check_out" | sed 's/^/    /'
fi
echo

# --- 6. Required GitHub secrets configured -------------------------------
# Mac-only mode (set VIBEMIX_PRETAG_MAC_ONLY=1) skips the SignPath gates so
# the macOS-only rc tag can ship while the SignPath OSS-program approval is
# still in flight. The Windows build job in release.yml already no-ops when
# SignPath secrets are absent — this just suppresses the pretag fail line so
# the macOS rc isn't held hostage by Windows signing infra.
echo "[6/8] Required GitHub secrets configured"
REQUIRED=(
  APPLE_DEVELOPER_ID
  APPLE_DEVELOPER_ID_P12_BASE64
  APPLE_DEVELOPER_ID_PASSWORD
  APPLE_DEVELOPER_ID_KEYCHAIN_PASSWORD
  APPLE_TEAM_ID
  APPLE_API_KEY_ID
  APPLE_API_KEY_ISSUER
  APPLE_API_KEY_P8
  TAURI_UPDATER_PRIVATE_KEY
  TAURI_UPDATER_KEY_PASSWORD
  BRAVOH_MANIFEST_UPLOAD_TOKEN
)
if [[ "${VIBEMIX_PRETAG_MAC_ONLY:-0}" != "1" ]]; then
  REQUIRED+=(
    SIGNPATH_API_TOKEN
    SIGNPATH_ORGANIZATION_ID
    SIGNPATH_PROJECT_SLUG
    SIGNPATH_SIGNING_POLICY_SLUG
    SIGNPATH_SIGNTOOL_CMD
  )
fi
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

# --- 7. Discord invite is no longer TBD ----------------------------------
echo "[7/8] Discord invite link is real"
if grep -qE "^Discord: \*\*TBD\*\*" README.md 2>/dev/null; then
  no "README still has Discord: **TBD** placeholder"
elif grep -qE "discord\.gg/[A-Za-z0-9]+" README.md 2>/dev/null; then
  ok "README has a real discord.gg invite link"
else
  warn "README has no Discord line at all — was the placeholder removed without replacement?"
fi
echo

# --- 8. Apple Dev ID cert in local Keychain (macOS only) -----------------
echo "[8/8] Apple Developer ID cert in local Keychain"
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
