#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# vibemix SHIP-TWEET launch orchestrator — Phase 45 / Plan 45-02 (SHIP-08).
#
# Single discharge entry point for post-cut publish. Reads the cadence
# matrix at scripts/dayzero/launch_copy/cadence_index.json, picks the row
# for --phase, and shells out to publish_social_posts.py (4 web channels)
# + post_discord_launch.py (Discord). Dry-run by default; --live requires
# triple-env (LAUNCH_REAL=1, GITHUB_TOKEN, DISCORD_WEBHOOK_URL).
#
# Usage:
#   bash scripts/launch/launch_trigger.sh --phase {T-30|T+0|T+5h|T+24h}
#                                         [--live]
#                                         [--cadence-index PATH]
#                                         [--copy-dir PATH]
#                                         [--quiet]
#
# Flags:
#   --phase           REQUIRED. One of T-30, T+0, T+5h, T+24h.
#   --live            Without it, dry-run (prints [plan] lines + writes JSONL).
#                     With it, requires LAUNCH_REAL=1 + GITHUB_TOKEN +
#                     DISCORD_WEBHOOK_URL env, then invokes subordinates
#                     with --real.
#   --cadence-index   Path to cadence_index.json
#                     (default: scripts/dayzero/launch_copy/cadence_index.json).
#   --copy-dir        Path to the per-channel .txt directory
#                     (default: scripts/dayzero/launch_copy).
#   --quiet           Suppress [plan] stdout (still writes JSONL audit).
#   -h, --help        Show this help and exit 0.
#
# Pre-publish gates (run for every invocation before the cadence loop):
#   1. scripts/launch/check_no_ai_slop.py over the 5 copy files.
#   2. Sign-off footer assertion (Kaan signature: + Francesco signature:
#      markers present in each .txt file — Plan 44-05 lock).
#
# Audit log: $VIBEMIX_LAUNCH_RUN_DIR (default dist/launch-runs)/
# <UTC>.jsonl — append-only, one line per channel × stage; Plan 45-04
# SHIP-V1-DECISION reads this for evidence.
#
# Test seam: VIBEMIX_LAUNCH_SHIM_DIR env var, when set, points at a
# directory of stub publish_social_posts.py / post_discord_launch.py /
# check_no_ai_slop.py. Used by tests/launch/test_launch_trigger_orchestration.py
# to assert subordinate argv + zero-network in dry-run.

set -euo pipefail

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
VALID_PHASES=("T-30" "T+0" "T+5h" "T+24h")
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DEFAULT_CADENCE_INDEX="${REPO_ROOT}/scripts/dayzero/launch_copy/cadence_index.json"
DEFAULT_COPY_DIR="${REPO_ROOT}/scripts/dayzero/launch_copy"
DEFAULT_RUN_DIR="${REPO_ROOT}/dist/launch-runs"

# ---------------------------------------------------------------------------
# usage() — sourced from this file's top comment block.
# ---------------------------------------------------------------------------
usage() {
  cat <<'EOF'
vibemix SHIP-TWEET launch orchestrator — Phase 45 / Plan 45-02 (SHIP-08).

Usage:
  bash scripts/launch/launch_trigger.sh --phase {T-30|T+0|T+5h|T+24h}
                                        [--live]
                                        [--cadence-index PATH]
                                        [--copy-dir PATH]
                                        [--quiet]

Flags:
  --phase           REQUIRED. One of T-30, T+0, T+5h, T+24h.
  --live            Triggers --real on subordinates. Requires
                    LAUNCH_REAL=1 + GITHUB_TOKEN + DISCORD_WEBHOOK_URL.
  --cadence-index   Path to cadence_index.json
                    (default: scripts/dayzero/launch_copy/cadence_index.json).
  --copy-dir        Path to the per-channel .txt directory
                    (default: scripts/dayzero/launch_copy).
  --quiet           Suppress [plan] stdout (JSONL audit still written).
  -h, --help        Show this help and exit 0.
EOF
}

# ---------------------------------------------------------------------------
# err() — write to stderr; if GITHUB_ACTIONS=true, also emit ::error::
# annotation line on stdout (matches cut_release.sh / check_gate.sh
# convention so GH Actions surface failure inline on the PR).
# ---------------------------------------------------------------------------
err() {
  local msg="$*"
  echo "${msg}" >&2
  if [[ "${GITHUB_ACTIONS:-}" == "true" ]]; then
    echo "::error::${msg}"
  fi
}

# ---------------------------------------------------------------------------
# Arg parser
# ---------------------------------------------------------------------------
PHASE=""
LIVE=0
QUIET=0
CADENCE_INDEX="${DEFAULT_CADENCE_INDEX}"
COPY_DIR="${DEFAULT_COPY_DIR}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --phase)
      PHASE="${2:-}"
      shift 2
      ;;
    --phase=*)
      PHASE="${1#*=}"
      shift
      ;;
    --live)
      LIVE=1
      shift
      ;;
    --cadence-index)
      CADENCE_INDEX="${2:-}"
      shift 2
      ;;
    --cadence-index=*)
      CADENCE_INDEX="${1#*=}"
      shift
      ;;
    --copy-dir)
      COPY_DIR="${2:-}"
      shift 2
      ;;
    --copy-dir=*)
      COPY_DIR="${1#*=}"
      shift
      ;;
    --quiet)
      QUIET=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      err "[launch_trigger] unknown flag: $1"
      usage >&2
      exit 2
      ;;
  esac
done

# Phase validation — every invocation, even --help-less.
if [[ -z "${PHASE}" ]]; then
  err "[launch_trigger] --phase required (one of: T-30, T+0, T+5h, T+24h)"
  exit 2
fi

phase_ok=0
for valid in "${VALID_PHASES[@]}"; do
  if [[ "${PHASE}" == "${valid}" ]]; then
    phase_ok=1
    break
  fi
done
if [[ "${phase_ok}" -eq 0 ]]; then
  err "[launch_trigger] invalid --phase '${PHASE}' (valid: T-30, T+0, T+5h, T+24h)"
  exit 2
fi

# ---------------------------------------------------------------------------
# --live precondition: triple-env (LAUNCH_REAL=1 + GITHUB_TOKEN +
# DISCORD_WEBHOOK_URL). Failure modes are named per KAAN-ACTION-LEGAL.md
# §SHIP-08 so an autonomous trigger surfaces the missing prerequisite
# clearly instead of partial publish.
# ---------------------------------------------------------------------------
if [[ "${LIVE}" -eq 1 ]]; then
  if [[ "${LAUNCH_REAL:-}" != "1" ]]; then
    err "[launch_trigger] --live requires LAUNCH_REAL=1 env (matches publish_social_posts + post_discord_launch convention)"
    exit 2
  fi
  if [[ -z "${GITHUB_TOKEN:-}" ]]; then
    err "[launch_trigger] --live requires GITHUB_TOKEN env (KAAN-ACTION-LEGAL.md §SHIP-08)"
    exit 2
  fi
  if [[ -z "${DISCORD_WEBHOOK_URL:-}" ]]; then
    err "[launch_trigger] --live requires DISCORD_WEBHOOK_URL env (KAAN-ACTION-LEGAL.md §SHIP-08)"
    exit 2
  fi
fi

# ---------------------------------------------------------------------------
# Resolve subordinate paths — VIBEMIX_LAUNCH_SHIM_DIR overrides for tests.
# ---------------------------------------------------------------------------
if [[ -n "${VIBEMIX_LAUNCH_SHIM_DIR:-}" ]]; then
  SLOP_CHECK="${VIBEMIX_LAUNCH_SHIM_DIR}/check_no_ai_slop.py"
  PUBLISH_SOCIAL="${VIBEMIX_LAUNCH_SHIM_DIR}/publish_social_posts.py"
  POST_DISCORD="${VIBEMIX_LAUNCH_SHIM_DIR}/post_discord_launch.py"
else
  SLOP_CHECK="${REPO_ROOT}/scripts/launch/check_no_ai_slop.py"
  PUBLISH_SOCIAL="${REPO_ROOT}/scripts/launch/publish_social_posts.py"
  POST_DISCORD="${REPO_ROOT}/scripts/launch/post_discord_launch.py"
fi

# ---------------------------------------------------------------------------
# Pre-publish gate: AI-slop blocklist (Plan 44-05 lock).
# Test shims are chmod +x with a python shebang; real script lives at
# scripts/launch/check_no_ai_slop.py without a shebang, invoked via python3.
# ---------------------------------------------------------------------------
if [[ ! -f "${SLOP_CHECK}" ]]; then
  err "[launch_trigger] slop check script not found at ${SLOP_CHECK}"
  exit 2
fi

set +e
if [[ -x "${SLOP_CHECK}" ]]; then
  # Test shim — has shebang, executable.
  "${SLOP_CHECK}" --dir "${COPY_DIR}" --quiet >/dev/null 2>&1
  SLOP_EXIT=$?
else
  # Real check_no_ai_slop.py — invoke via python3.
  python3 "${SLOP_CHECK}" --dir "${COPY_DIR}" --quiet >/dev/null 2>&1
  SLOP_EXIT=$?
fi
set -e

if [[ ${SLOP_EXIT} -ne 0 ]]; then
  err "[launch_trigger] AI-slop blocklist check failed — fix copy before publishing"
  exit 2
fi

# ---------------------------------------------------------------------------
# Pre-publish gate: sign-off footer (Plan 44-05 lock).
# Each of the 5 launch_copy/*.txt files MUST carry both
# `Kaan signature:` and `Francesco signature:` markers (the literal
# strings check_no_ai_slop.py enforces as Gate 2 — single source of
# truth). check_no_ai_slop.py already pins this when invoked against
# the canonical scripts/dayzero/launch_copy directory; this gate
# re-asserts when --copy-dir overrides the canonical location so
# downstream test fixtures (or future copy moves) can't bypass the
# lock by pointing at a different dir.
# ---------------------------------------------------------------------------
SIGNOFF_FAILURES=()
for fname in twitter.txt instagram.txt linkedin.txt reddit.txt discord.txt; do
  fpath="${COPY_DIR}/${fname}"
  if [[ ! -f "${fpath}" ]]; then
    SIGNOFF_FAILURES+=("${fname} (file missing)")
    continue
  fi
  if ! grep -q "Kaan signature:" "${fpath}"; then
    SIGNOFF_FAILURES+=("${fname} (missing 'Kaan signature:')")
    continue
  fi
  if ! grep -q "Francesco signature:" "${fpath}"; then
    SIGNOFF_FAILURES+=("${fname} (missing 'Francesco signature:')")
  fi
done

if [[ ${#SIGNOFF_FAILURES[@]} -gt 0 ]]; then
  for failure in "${SIGNOFF_FAILURES[@]}"; do
    err "[launch_trigger] sign-off footer missing in ${failure} — Plan 44-05 contract broken"
  done
  exit 2
fi

# ---------------------------------------------------------------------------
# Audit log setup — VIBEMIX_LAUNCH_RUN_DIR overrides default for tests.
# ---------------------------------------------------------------------------
RUN_DIR="${VIBEMIX_LAUNCH_RUN_DIR:-${DEFAULT_RUN_DIR}}"
mkdir -p "${RUN_DIR}"
RUN_STAMP="$(date -u +%Y-%m-%dT%H-%M-%SZ)"
RUN_FILE="${RUN_DIR}/${RUN_STAMP}.jsonl"

if [[ "${LIVE}" -eq 1 ]]; then
  MODE="live"
  SUBORD_FLAG="--real"
else
  MODE="dry-run"
  SUBORD_FLAG="--dry-run"
fi

# ---------------------------------------------------------------------------
# Cadence resolution + dispatch loop — Python heredoc parses cadence_index.json,
# emits per-channel rows for the requested phase. Bash then iterates rows and
# shells out to subordinates + appends audit JSONL.
# ---------------------------------------------------------------------------
RESOLVED_ROWS="$(python3 - "${CADENCE_INDEX}" "${PHASE}" <<'PYEOF'
import json, sys

cadence_path, phase = sys.argv[1], sys.argv[2]
with open(cadence_path, "r", encoding="utf-8") as f:
    data = json.load(f)

if phase not in data["stages"]:
    sys.stderr.write(f"[launch_trigger] phase {phase} not in cadence_index.json stages\n")
    sys.exit(2)

# Emit channels in canonical order (matches LAUNCH_COPY_FILES tuple in
# check_no_ai_slop.py so determinism cascades).
order = ["twitter", "instagram", "linkedin", "reddit", "discord"]
for channel in order:
    if channel not in data["channels"]:
        continue
    copy_file = data["channels"][channel].get(phase)
    if copy_file is None:
        continue
    # Tab-separated rows: channel<TAB>copy_file
    print(f"{channel}\t{copy_file}")
PYEOF
)"
PY_EXIT=$?
if [[ ${PY_EXIT} -ne 0 ]]; then
  err "[launch_trigger] cadence resolution failed (exit ${PY_EXIT})"
  exit ${PY_EXIT}
fi

# Each row → [plan] log + subordinate invocation + JSONL audit append.
while IFS=$'\t' read -r CHANNEL COPY_FILE; do
  [[ -z "${CHANNEL}" ]] && continue

  if [[ "${QUIET}" -eq 0 ]]; then
    echo "[plan] phase=${PHASE} channel=${CHANNEL} copy_file=${COPY_FILE} mode=${MODE}"
  fi

  # Route: discord → post_discord_launch.py; everything else → publish_social_posts.py.
  # Shims are executable (shebang present); real scripts need python3.
  STATUS="ok"
  if [[ "${CHANNEL}" == "discord" ]]; then
    if [[ -x "${POST_DISCORD}" ]]; then
      "${POST_DISCORD}" "${SUBORD_FLAG}" --release-url "https://github.com/bravoh/vibemix/releases/latest" >/dev/null 2>&1 || STATUS="error"
    else
      python3 "${POST_DISCORD}" "${SUBORD_FLAG}" --release-url "https://github.com/bravoh/vibemix/releases/latest" >/dev/null 2>&1 || STATUS="error"
    fi
  else
    if [[ -x "${PUBLISH_SOCIAL}" ]]; then
      "${PUBLISH_SOCIAL}" "${SUBORD_FLAG}" --release-url "https://github.com/bravoh/vibemix/releases/latest" >/dev/null 2>&1 || STATUS="error"
    else
      python3 "${PUBLISH_SOCIAL}" "${SUBORD_FLAG}" --release-url "https://github.com/bravoh/vibemix/releases/latest" >/dev/null 2>&1 || STATUS="error"
    fi
  fi

  # Append JSONL audit row — Python for safe escaping.
  python3 - "${RUN_FILE}" "${PHASE}" "${CHANNEL}" "${MODE}" "${COPY_FILE}" "${STATUS}" <<'PYEOF'
import json, sys, os, datetime
run_file, stage, channel, mode, copy_file, status = sys.argv[1:7]
row = {
    "ts": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "stage": stage,
    "channel": channel,
    "mode": mode,
    "copy_file": copy_file,
    "status": status,
}
os.makedirs(os.path.dirname(run_file), exist_ok=True)
with open(run_file, "a", encoding="utf-8") as f:
    f.write(json.dumps(row) + "\n")
PYEOF
done <<< "${RESOLVED_ROWS}"

exit 0
