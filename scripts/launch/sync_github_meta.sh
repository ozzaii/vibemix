#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
#
# scripts/launch/sync_github_meta.sh — Phase 39 / SHIP-05.
#
# Syncs the GitHub repo metadata (description, homepage, topics) using
# `gh api`. Source-of-truth lives in `docs/launch/github-meta.md`.
#
# HARD GUARD: by default, prints every `gh api` call the script would
# make WITHOUT executing them. To actually apply, pass `--real` AND
# set `GH_META_REAL=1` in the environment.
#
# Real-apply is Kaan-action — autonomous agents never set GH_META_REAL.

set -u

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
META_DOC="${REPO_ROOT}/docs/launch/github-meta.md"
REPO_SLUG="${REPO_SLUG:-bravoh/vibemix}"

MODE="dry-run"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --real)
      MODE="real"
      shift
      ;;
    --repo)
      REPO_SLUG="$2"
      shift 2
      ;;
    -h|--help)
      sed -n '1,16p' "$0"
      exit 0
      ;;
    *)
      echo "unknown arg: $1" >&2
      exit 1
      ;;
  esac
done

if [[ "${MODE}" == "real" && "${GH_META_REAL:-}" != "1" ]]; then
  echo "::error::sync_github_meta: --real requires GH_META_REAL=1 env." >&2
  echo "  Aborting (Phase 39 SHIP-05 hard guard)." >&2
  exit 2
fi

if [[ ! -f "${META_DOC}" ]]; then
  echo "::error::sync_github_meta: ${META_DOC} missing" >&2
  exit 1
fi

# ── Extract description ────────────────────────────────────────────────
# The first fenced ```...``` block after "## Description" is the description.
DESCRIPTION=$(awk '
  /^## Description/        { in_section=1; next }
  in_section && /^```$/    { in_block = !in_block; next }
  in_block && in_section   { print; }
  /^## /                   { if (in_section && !in_block) in_section=0 }
' "${META_DOC}" | head -c 1000)

if [[ -z "${DESCRIPTION}" ]]; then
  echo "::error::sync_github_meta: could not parse Description from ${META_DOC}" >&2
  exit 1
fi

# Description must be <= 350 chars.
if [[ ${#DESCRIPTION} -gt 350 ]]; then
  echo "::error::sync_github_meta: description is ${#DESCRIPTION} chars (>350)" >&2
  exit 1
fi

# ── Extract homepage URL ───────────────────────────────────────────────
HOMEPAGE=$(awk '
  /^## Homepage URL/       { in_section=1; next }
  in_section && /^```$/    { in_block = !in_block; next }
  in_block && in_section   { print; }
  /^## /                   { if (in_section && !in_block) in_section=0 }
' "${META_DOC}" | head -n 1 | tr -d '[:space:]')

# ── Extract topics ─────────────────────────────────────────────────────
TOPICS=$(awk '
  /^## Topics/             { in_section=1; next }
  in_section && /^```$/    { in_block = !in_block; next }
  in_block && in_section   { print; }
  /^## /                   { if (in_section && !in_block) in_section=0 }
' "${META_DOC}" | tr '\n' ' ')

if [[ -z "${TOPICS}" ]]; then
  echo "::error::sync_github_meta: could not parse Topics from ${META_DOC}" >&2
  exit 1
fi

# Build the topic args as an array.
TOPIC_ARGS=()
for t in ${TOPICS}; do
  TOPIC_ARGS+=("-F" "names[]=${t}")
done

echo "═════════════════════════════════════════════════════════"
echo "  vibemix — sync_github_meta.sh (Phase 39 / SHIP-05)"
echo "  Repo:        ${REPO_SLUG}"
echo "  Mode:        ${MODE}"
echo "  Description: (${#DESCRIPTION} chars)"
echo "               ${DESCRIPTION:0:120}..."
echo "  Homepage:    ${HOMEPAGE}"
echo "  Topics:      ${TOPICS}"
echo "═════════════════════════════════════════════════════════"
echo

# ── Print or run the calls ─────────────────────────────────────────────
if [[ "${MODE}" == "real" ]]; then
  echo "[real] gh api repos/${REPO_SLUG} -X PATCH -f description=... -f homepage=..."
  gh api "repos/${REPO_SLUG}" -X PATCH \
    -f "description=${DESCRIPTION}" \
    -f "homepage=${HOMEPAGE}"
  echo
  echo "[real] gh api repos/${REPO_SLUG}/topics -X PUT ${TOPIC_ARGS[*]}"
  gh api "repos/${REPO_SLUG}/topics" -X PUT \
    -H "Accept: application/vnd.github.mercy-preview+json" \
    "${TOPIC_ARGS[@]}"
else
  echo "[dry-run] would: gh api repos/${REPO_SLUG} -X PATCH \\"
  echo "             -f description=\"${DESCRIPTION:0:80}...\" \\"
  echo "             -f homepage=\"${HOMEPAGE}\""
  echo
  echo "[dry-run] would: gh api repos/${REPO_SLUG}/topics -X PUT \\"
  for arg in "${TOPIC_ARGS[@]}"; do
    echo "             ${arg} \\"
  done
  echo
  echo "  To apply: set GH_META_REAL=1 and pass --real."
fi

exit 0
