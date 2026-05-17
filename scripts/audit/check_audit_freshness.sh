#!/usr/bin/env bash
# Phase 46 / DEPS-05 — AUDIT.md freshness gate.
#
# Fails the PR if any lockfile's last-commit-time is newer than the
# last-commit-time of either docs/AUDIT.md or scripts/audit/dep_ratings.yaml.
#
# Uses `git log -1 --format=%ct <file>` (last-commit unix timestamp)
# instead of filesystem mtime — mtime is unstable on fresh clones
# (every checkout gets `now()`).
#
# If the gate fails:
#   1. Run `python scripts/audit/gen_audit_md.py` locally.
#   2. Update scripts/audit/dep_ratings.yaml with rationale for any
#      new dep + verify rating.
#   3. Commit AUDIT.md + dep_ratings.yaml in the same commit as the
#      lockfile change.

set -euo pipefail

LOCKFILES=(
  "pyproject.toml"
  "uv.lock"
  "tauri/src-tauri/Cargo.toml"
  "tauri/src-tauri/Cargo.lock"
  "tauri/ui/package.json"
  "tauri/ui/package-lock.json"
)

AUDIT_FILES=(
  "docs/AUDIT.md"
  "scripts/audit/dep_ratings.yaml"
)

commit_time() {
  local file="$1"
  git log -1 --format=%ct -- "$file" 2>/dev/null || echo "0"
}

# Find the min commit-time across AUDIT_FILES — AUDIT.md and
# dep_ratings.yaml MUST both be at-or-newer-than every lockfile.
AUDIT_MIN=99999999999
for f in "${AUDIT_FILES[@]}"; do
  t=$(commit_time "$f")
  if [ "$t" = "0" ]; then
    echo "::error::missing audit artifact: $f"
    exit 1
  fi
  if [ "$t" -lt "$AUDIT_MIN" ]; then
    AUDIT_MIN="$t"
  fi
done

STALE=()
for f in "${LOCKFILES[@]}"; do
  t=$(commit_time "$f")
  if [ "$t" = "0" ]; then
    continue  # file does not exist or not tracked — skip
  fi
  if [ "$t" -gt "$AUDIT_MIN" ]; then
    STALE+=("$f")
  fi
done

if [ ${#STALE[@]} -gt 0 ]; then
  echo "::error::audit artifacts are stale relative to these lockfiles:" >&2
  for f in "${STALE[@]}"; do
    echo "::error::  - $f (last-commit-time newer than AUDIT.md + dep_ratings.yaml)" >&2
  done
  echo "::error::Fix: run \`python scripts/audit/gen_audit_md.py\`, update dep_ratings.yaml if needed, and commit." >&2
  exit 1
fi

echo "AUDIT.md + dep_ratings.yaml are at-or-newer-than every lockfile — DEPS-05 OK"
