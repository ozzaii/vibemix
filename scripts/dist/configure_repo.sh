#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
#
# scripts/dist/configure_repo.sh — Phase 19 Plan 19-01 GH-17 metadata wrapper.
#
# Reads the declarative source of truth at .github/repo-config.yml and runs
# `gh repo edit` to push the values to the GitHub repo (description, homepage,
# topics, default_branch, feature switches, merge policy).
#
# IDEMPOTENT: re-running yields the same end state — `gh repo edit` PUTs the
# fields, so the second invocation is a no-op on the server side.
#
# SAFETY: default mode is DRY-RUN. The script prints the planned `gh repo
# edit` invocation and exits 0 without contacting GitHub. Pass `--apply` to
# actually fire it. This avoids accidental description/topic overwrites
# from cron jobs or stale CI runs.
#
# Usage:
#   scripts/dist/configure_repo.sh            # dry-run print
#   scripts/dist/configure_repo.sh --apply    # push to GitHub
#   scripts/dist/configure_repo.sh --repo owner/name --apply
#
# Requirements:
#   - gh CLI (https://cli.github.com), authenticated against the target org
#   - yq v4+ (https://github.com/mikefarah/yq) — `brew install yq`
#
# Exit codes:
#   0  success (dry-run or applied)
#   1  prerequisite missing or yaml parse error
#   2  invalid usage / unknown flag
#
# Cross-plan ref: tests/repo/test_repo_metadata.py gates the script's syntax +
# `gh repo edit` invocation + `--apply` gate presence. CONTEXT Area 6 locks
# the exact field values.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CONFIG_FILE="${REPO_ROOT}/.github/repo-config.yml"

APPLY=0
REPO=""

while (("$#")); do
  case "$1" in
    --apply)
      APPLY=1
      shift
      ;;
    --repo)
      REPO="${2:?--repo requires an argument like owner/name}"
      shift 2
      ;;
    -h | --help)
      sed -n '2,/^$/p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *)
      echo "ERROR: unknown flag: $1" >&2
      echo "Usage: $0 [--apply] [--repo owner/name]" >&2
      exit 2
      ;;
  esac
done

if [[ ! -f "$CONFIG_FILE" ]]; then
  echo "ERROR: missing $CONFIG_FILE" >&2
  exit 1
fi

if ! command -v gh >/dev/null 2>&1; then
  echo "ERROR: gh CLI not installed. Install: https://cli.github.com" >&2
  exit 1
fi

if ! command -v yq >/dev/null 2>&1; then
  echo "ERROR: yq not installed. Install: brew install yq" >&2
  exit 1
fi

# Parse fields from .github/repo-config.yml. yq v4 syntax.
DESCRIPTION="$(yq -r '.description' "$CONFIG_FILE")"
HOMEPAGE="$(yq -r '.homepage' "$CONFIG_FILE")"
DEFAULT_BRANCH="$(yq -r '.default_branch' "$CONFIG_FILE")"
ENABLE_ISSUES="$(yq -r '.enable_issues' "$CONFIG_FILE")"
ENABLE_PROJECTS="$(yq -r '.enable_projects' "$CONFIG_FILE")"
ENABLE_WIKI="$(yq -r '.enable_wiki' "$CONFIG_FILE")"
DELETE_BRANCH="$(yq -r '.delete_branch_on_merge' "$CONFIG_FILE")"
ALLOW_SQUASH="$(yq -r '.allow_squash_merge' "$CONFIG_FILE")"
ALLOW_MERGE="$(yq -r '.allow_merge_commit' "$CONFIG_FILE")"
ALLOW_REBASE="$(yq -r '.allow_rebase_merge' "$CONFIG_FILE")"

# Topics → comma-joined for `gh repo edit --add-topic`. Each topic is added
# individually so existing topics not in the YAML are preserved. To enforce
# strict set equality, switch to repeated `--add-topic` after a clear-call.
TOPICS_CSV="$(yq -r '.topics | join(",")' "$CONFIG_FILE")"

# Build the gh repo edit argv. gh accepts repeated flags for each switch.
# Args are constructed as an array so quoting survives `set -x` introspection.
ARGS=(
  repo edit
  --description "$DESCRIPTION"
  --homepage "$HOMEPAGE"
  --default-branch "$DEFAULT_BRANCH"
  --enable-issues="$ENABLE_ISSUES"
  --enable-projects="$ENABLE_PROJECTS"
  --enable-wiki="$ENABLE_WIKI"
  --delete-branch-on-merge="$DELETE_BRANCH"
  --allow-update-branch=true
  --enable-squash-merge="$ALLOW_SQUASH"
  --enable-merge-commit="$ALLOW_MERGE"
  --enable-rebase-merge="$ALLOW_REBASE"
  --add-topic "$TOPICS_CSV"
)

if [[ -n "$REPO" ]]; then
  ARGS=("${ARGS[@]:0:2}" "$REPO" "${ARGS[@]:2}")
fi

if [[ "$APPLY" -eq 0 ]]; then
  echo "[configure_repo.sh] DRY RUN — no changes pushed to GitHub."
  echo "[configure_repo.sh] Planned invocation:"
  printf '  gh'
  for a in "${ARGS[@]}"; do
    printf ' %q' "$a"
  done
  printf '\n'
  echo "[configure_repo.sh] Re-run with --apply to push these settings."
  exit 0
fi

echo "[configure_repo.sh] Applying repo settings via gh repo edit..."
gh "${ARGS[@]}"
echo "[configure_repo.sh] Done. Verify at the repo's About panel."
