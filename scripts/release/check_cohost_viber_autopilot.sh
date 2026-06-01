#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
#
# Release wrapper for the cohost/Viber autopilot.
#
# Default policy is strict release gating: fail unless the captured run itself
# is clean. The command still writes the full report, reprompt pack, and repair
# run so the operator has the repair trail even when the release gate blocks.
#
# Env:
#   COHOST_VIBER_FAIL_ON          automation|release|first-pass|audio-evidence (default: release)
#   COHOST_VIBER_BACKEND          deterministic|codex (default: deterministic)
#   COHOST_VIBER_OUT_DIR          artifact dir (default: .planning/eval-runs/cohost-viber-autopilot)
#   COHOST_VIBER_SESSION_DIR      optional explicit recording session
#   COHOST_VIBER_RECORDINGS_ROOT  optional recordings root when session omitted
#   COHOST_VIBER_GLOBAL_ROOT      optional app-data root for Viber rows
#   COHOST_VIBER_GLOBAL_SINCE_ISO only include Viber rows at/after this ISO timestamp
#   COHOST_VIBER_MAX_GLOBAL_ROWS  default: 25
#   COHOST_VIBER_NO_VIBER         1 to skip global Viber rows
#   COHOST_VIBER_CODEX_PATH       optional Codex CLI override
#   COHOST_VIBER_TIMEOUT_S        optional Codex timeout
#   COHOST_VIBER_ALLOW_SHELL      1 to pass --allow-shell for Codex backend
#   PYTHON                        Python executable (default: python3)

set -euo pipefail

FAIL_ON="${COHOST_VIBER_FAIL_ON:-release}"
BACKEND="${COHOST_VIBER_BACKEND:-deterministic}"
OUT_DIR="${COHOST_VIBER_OUT_DIR:-.planning/eval-runs/cohost-viber-autopilot}"
MAX_GLOBAL_ROWS="${COHOST_VIBER_MAX_GLOBAL_ROWS:-25}"
GHA_ANNOT="${GITHUB_ACTIONS:-false}"

PY_CMD=()
if [ -n "${PYTHON:-}" ]; then
  PY_CMD=("${PYTHON}")
elif [ -x ".venv/bin/python" ]; then
  PY_CMD=(".venv/bin/python")
elif command -v uv >/dev/null 2>&1; then
  PY_CMD=("uv" "run" "python")
else
  PY_CMD=("python3")
fi

emit_err() {
  local msg="$1"
  if [ "${GHA_ANNOT}" = "true" ]; then
    echo "::error::check_cohost_viber_autopilot: ${msg}" >&2
  else
    echo "FAIL check_cohost_viber_autopilot: ${msg}" >&2
  fi
}

emit_pass() {
  echo "PASS check_cohost_viber_autopilot: $*"
}

if ! command -v "${PY_CMD[0]}" >/dev/null 2>&1; then
  emit_err "${PY_CMD[0]} is required but not found on PATH"
  exit 1
fi

mkdir -p "${OUT_DIR}"

ARGS=(
  -m vibemix eval autopilot
  --out-dir "${OUT_DIR}"
  --backend "${BACKEND}"
  --fail-on "${FAIL_ON}"
  --max-global-rows "${MAX_GLOBAL_ROWS}"
  --json
)

if [ -n "${COHOST_VIBER_SESSION_DIR:-}" ]; then
  ARGS+=(--session-dir "${COHOST_VIBER_SESSION_DIR}")
fi
if [ -n "${COHOST_VIBER_RECORDINGS_ROOT:-}" ]; then
  ARGS+=(--recordings-root "${COHOST_VIBER_RECORDINGS_ROOT}")
fi
if [ -n "${COHOST_VIBER_GLOBAL_ROOT:-}" ]; then
  ARGS+=(--global-root "${COHOST_VIBER_GLOBAL_ROOT}")
fi
if [ -n "${COHOST_VIBER_GLOBAL_SINCE_ISO:-}" ]; then
  ARGS+=(--global-since-iso "${COHOST_VIBER_GLOBAL_SINCE_ISO}")
fi
if [ "${COHOST_VIBER_NO_VIBER:-0}" = "1" ]; then
  ARGS+=(--no-viber)
fi
if [ -n "${COHOST_VIBER_CODEX_PATH:-}" ]; then
  ARGS+=(--codex-path "${COHOST_VIBER_CODEX_PATH}")
fi
if [ -n "${COHOST_VIBER_TIMEOUT_S:-}" ]; then
  ARGS+=(--timeout-s "${COHOST_VIBER_TIMEOUT_S}")
fi
if [ "${COHOST_VIBER_ALLOW_SHELL:-0}" = "1" ]; then
  ARGS+=(--allow-shell)
fi

STDOUT_JSON="${OUT_DIR}/autopilot_stdout.json"
STDERR_LOG="${OUT_DIR}/autopilot_stderr.log"
set +e
"${PY_CMD[@]}" "${ARGS[@]}" >"${STDOUT_JSON}" 2>"${STDERR_LOG}"
RC=$?
set -e

SUMMARY="${OUT_DIR}/autopilot_summary.json"
if [ ! -f "${SUMMARY}" ]; then
  if [ -s "${STDERR_LOG}" ]; then
    cat "${STDERR_LOG}" >&2
  fi
  emit_err "autopilot did not write summary: ${SUMMARY}"
  if [ "${RC}" -ne 0 ]; then
    exit "${RC}"
  fi
  exit 1
fi

SUMMARY_LINE=$(
  "${PY_CMD[@]}" - "${SUMMARY}" <<'PY'
import json
import sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
repair = data.get("repair") or {}
counts = data.get("initial_issue_counts") or {}
print(
    "status={status} gate_ok={gate_ok} release_gate_ok={release_gate_ok} "
    "first_pass_clean={first_pass_clean} reprompt_debt={reprompt_debt} "
    "audio_evidence_debt={audio_evidence_debt} "
    "blockers={blockers} care={care} watch={watch} repairs_passed={passed} "
    "repairs_failed={failed} global_since={global_since} out_dir={out_dir}".format(
        status=data.get("status"),
        gate_ok=data.get("gate_ok"),
        release_gate_ok=data.get("release_gate_ok"),
        first_pass_clean=data.get("first_pass_clean"),
        reprompt_debt=data.get("reprompt_debt", 0),
        audio_evidence_debt=data.get("audio_evidence_debt", 0),
        blockers=counts.get("blocker", 0),
        care=counts.get("care", 0),
        watch=counts.get("watch", 0),
        passed=repair.get("passed", 0),
        failed=repair.get("failed", 0),
        global_since=data.get("global_since_iso") or "none",
        out_dir=data.get("out_dir"),
    )
)
PY
)

if [ "${RC}" -eq 0 ]; then
  emit_pass "${SUMMARY_LINE}"
  exit 0
fi

emit_err "${SUMMARY_LINE}"
exit "${RC}"
