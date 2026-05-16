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

SCOPE_DIR="src/vibemix"

# Regex matches every banned literal pattern. Escape dots inside the
# bracketed alternation. Use POSIX extended regex (grep -E).
PATTERN='gemini-3-flash|gemini-3-pro|gemini-embedding-|gemini-3\.1-flash|gemini-2\.5-flash|gemini-3\.1-flash-live'

if [ ! -d "${SCOPE_DIR}" ]; then
  echo "::error::Plan 41-01 gate: scope dir ${SCOPE_DIR} missing" >&2
  exit 1
fi

# Build the file list — every *.py under src/vibemix/ except the allowlist.
# Use find + grep so a missing file doesn't abort the pipeline.
violations=0

while IFS= read -r -d '' file; do
  # Normalize path for allowlist comparison — find prints paths starting
  # with ./ when run from the repo root with `find . -path …`, so strip
  # any leading ./ before comparing.
  rel="${file#./}"
  if [ "${rel}" = "${ALLOWLIST_PATH}" ]; then
    continue
  fi
  # grep -n prints "lineno:line" for each match; -E enables extended regex.
  if matches=$(grep -nE "${PATTERN}" "${rel}" 2>/dev/null); then
    while IFS= read -r m; do
      lineno="${m%%:*}"
      line="${m#*:}"
      # GitHub Actions annotation — surfaces inline in the PR diff view.
      printf '::error file=%s,line=%s::Plan 41-01: hardcoded Gemini model literal — route via vibemix.llm.model_router.resolve() instead. Line: %s\n' \
        "${rel}" "${lineno}" "${line}" >&2
      violations=$((violations + 1))
    done <<< "${matches}"
  fi
done < <(find "${SCOPE_DIR}" -type f -name '*.py' -print0)

if [ "${violations}" -ne 0 ]; then
  echo "::error::Plan 41-01 gate: ${violations} hardcoded Gemini model literal(s) found in ${SCOPE_DIR}/ — see annotations above. Allowlist: ${ALLOWLIST_PATH}." >&2
  exit 1
fi

echo "Plan 41-01 gate: clean — no hardcoded Gemini model literals in ${SCOPE_DIR}/ outside ${ALLOWLIST_PATH}."
exit 0
