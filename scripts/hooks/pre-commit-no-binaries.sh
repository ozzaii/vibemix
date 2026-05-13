#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
#
# scripts/hooks/pre-commit-no-binaries.sh — Phase 19 Plan 19-01 GH-18 gate.
#
# Rejects commits that add files >1 MB which are NOT routed through git-lfs.
# Defense-in-depth complement to tests/repo/test_repo_scrub.py (the CI gate
# fires only on PR; this hook fires on every local commit).
#
# Install (per clone — .git/hooks is not version-controlled):
#   ln -sf ../../scripts/hooks/pre-commit-no-binaries.sh \
#          .git/hooks/pre-commit
#
# To bypass (do NOT do this for binary commits — track via LFS instead):
#   git commit --no-verify
#
# Exit codes:
#   0 = all added files OK
#   1 = at least one offender — commit rejected
#
# Cross-plan ref: tests/repo/test_repo_metadata.py asserts the script exists,
# is executable, syntax-clean, and references both the 1048576 byte threshold
# and `git lfs ls-files` (the LFS exemption).

set -euo pipefail

# 1 MB = 1048576 bytes. Larger files belong in LFS or out-of-tree.
THRESHOLD=1048576

# Files staged for the current commit (added or copied — modified files
# don't grow without a deliberate edit, so we focus on net-new content).
ADDED_FILES="$(git diff --cached --name-only --diff-filter=AC)"

if [[ -z "$ADDED_FILES" ]]; then
  exit 0
fi

# LFS-tracked file list. `git lfs ls-files` prints `<oid> * <path>` per line;
# we keep only the path. If git-lfs is not installed, the call falls back
# gracefully (no LFS exemption) — the threshold then applies to every file.
LFS_FILES=""
if command -v git-lfs >/dev/null 2>&1; then
  LFS_FILES="$(git lfs ls-files -n 2>/dev/null || true)"
fi

OFFENDERS=()

while IFS= read -r file; do
  [[ -z "$file" ]] && continue
  [[ ! -f "$file" ]] && continue

  size="$(wc -c <"$file" | tr -d '[:space:]')"

  if [[ "$size" -le "$THRESHOLD" ]]; then
    continue
  fi

  # Size exceeds 1 MB — exempt only if the path is in git lfs ls-files.
  if [[ -n "$LFS_FILES" ]] && grep -Fxq "$file" <<<"$LFS_FILES"; then
    continue
  fi

  OFFENDERS+=("$file ($size bytes)")
done <<<"$ADDED_FILES"

if [[ "${#OFFENDERS[@]}" -gt 0 ]]; then
  echo "ERROR: pre-commit-no-binaries: ${#OFFENDERS[@]} file(s) exceed 1 MB" >&2
  echo "       and are not tracked by git-lfs. Reject the commit." >&2
  echo "" >&2
  for f in "${OFFENDERS[@]}"; do
    echo "  - $f" >&2
  done
  echo "" >&2
  echo "Fix options:" >&2
  echo "  1. Move the binary out of repo (release asset, CDN, S3)." >&2
  echo "  2. Track via git-lfs: add a pattern to .gitattributes," >&2
  echo "     then 'git lfs install --local && git add <file>'." >&2
  echo "  3. If this is a legitimate non-LFS asset under the threshold," >&2
  echo "     ensure it's actually <= 1048576 bytes." >&2
  exit 1
fi

exit 0
