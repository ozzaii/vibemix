#!/usr/bin/env bash
# Plan 41-01 / Task 3 — model-literal grep gate.
#
# Fails the PR if any Gemini model literal appears in src/vibemix/
# outside the single allowlisted file (src/vibemix/llm/_router_config.py).
#
# Scope: src/vibemix/**/*.py ONLY.
#   - tests/ is OUT of scope (tests can pin literals as contract canaries).
#   - scripts/ is OUT of scope (scripts/eval/judge.py keeps its own
#     model dispatch per Open Q 4).
#   - docs / mocks / tauri are OUT of scope.
#
# Patterns banned (kept in sync with tests/repo/test_model_literal_gate.py):
#   - gemini-3-flash        (live coach + library auto-tag + debrief TTS)
#   - gemini-3-pro          (debrief)
#   - gemini-embedding-     (embedding 2 + defensive against legacy 001)
#   - gemini-3.1-flash      (TTS + Live API)
#   - gemini-2.5-flash      (fallback TTS)
#   - gemini-3.1-flash-live (future Live API surface)
#
# Comments containing literals count as violations. A docstring that
# names a model id should reference the router path instead.
#
# Output uses GitHub Actions `::error` annotations so the failure surfaces
# inline in the PR diff.
#
# Exit codes:
#   0 — clean tree (post-Plan-41-01 migration; only _router_config.py
#       carries literals)
#   1 — at least one violation found

set -euo pipefail

# Allowlist: the single file in src/vibemix/ permitted to carry model
# literals. NOTE — model_router.py is NOT on the list; the router itself
# never inlines a model id, only consumes _ROUTES from _router_config.py.
ALLOWLIST_PATH="src/vibemix/llm/_router_config.py"

# Phase 46 / DEPS-04 — scan target expanded to include AUDIT.md +
# scripts/audit/ (where the AUDIT.md generator lives) + the future
# docs/dep-opportunities/ surface (Phase 48 pre-emptive coverage).
SCOPE_DIRS=(
  "src/vibemix"
  "docs/AUDIT.md"
  "scripts/audit"
  "docs/dep-opportunities"
)

# Regex matches every banned literal pattern. Escape dots inside the
# bracketed alternation. Use POSIX extended regex (grep -E).
PATTERN='gemini-3-flash|gemini-3-pro|gemini-embedding-|gemini-3\.1-flash|gemini-2\.5-flash|gemini-3\.1-flash-live'

violations=0

scan_file() {
  local rel="$1"
  if [ "${rel}" = "${ALLOWLIST_PATH}" ]; then
    return 0
  fi
  if matches=$(grep -nE "${PATTERN}" "${rel}" 2>/dev/null); then
    while IFS= read -r m; do
      lineno="${m%%:*}"
      line="${m#*:}"
      printf '::error file=%s,line=%s::DEPS-04 / Plan 41-01: hardcoded Gemini model literal — route via vibemix.llm.model_router.resolve() instead. Line: %s\n' \
        "${rel}" "${lineno}" "${line}" >&2
      violations=$((violations + 1))
    done <<< "${matches}"
  fi
}

for scope in "${SCOPE_DIRS[@]}"; do
  if [ ! -e "${scope}" ]; then
    # docs/dep-opportunities/ may not exist yet — pre-emptive coverage.
    continue
  fi
  if [ -d "${scope}" ]; then
    while IFS= read -r -d '' file; do
      rel="${file#./}"
      scan_file "${rel}"
    done < <(find "${scope}" -type f \( -name '*.py' -o -name '*.md' -o -name '*.yaml' -o -name '*.yml' -o -name '*.sh' -o -name '*.json' \) -print0)
  else
    scan_file "${scope}"
  fi
done

if [ "${violations}" -ne 0 ]; then
  echo "::error::DEPS-04 / Plan 41-01 gate: ${violations} hardcoded Gemini model literal(s) found in scanned paths — see annotations above. Allowlist: ${ALLOWLIST_PATH}." >&2
  exit 1
fi

echo "DEPS-04 / Plan 41-01 gate: clean — no hardcoded Gemini model literals in scanned paths (${SCOPE_DIRS[*]}) outside ${ALLOWLIST_PATH}."
exit 0
