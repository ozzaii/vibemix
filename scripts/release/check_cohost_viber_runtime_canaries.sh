#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
#
# Focused runtime canaries for cohost/Viber anti-hallucination invariants.
#
# These are intentionally narrower than the full test suite: they pin the live
# cohost behavior that must be true before the release matrix can trust a model
# run or a captured session artifact.
#
# Env:
#   COHOST_VIBER_RUNTIME_CANARY_OUT_DIR artifact dir
#   PYTHON                              Python executable; defaults to .venv, uv, then python3

set -euo pipefail

OUT_DIR="${COHOST_VIBER_RUNTIME_CANARY_OUT_DIR:-.planning/eval-runs/cohost-viber-runtime-canaries}"
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
    echo "::error::check_cohost_viber_runtime_canaries: ${msg}" >&2
  else
    echo "FAIL check_cohost_viber_runtime_canaries: ${msg}" >&2
  fi
}

emit_pass() {
  echo "PASS check_cohost_viber_runtime_canaries: $*"
}

if ! command -v "${PY_CMD[0]}" >/dev/null 2>&1; then
  emit_err "${PY_CMD[0]} is required but not found on PATH"
  exit 1
fi

mkdir -p "${OUT_DIR}"

STDOUT_LOG="${OUT_DIR}/pytest.stdout.log"
STDERR_LOG="${OUT_DIR}/pytest.stderr.log"
SUMMARY="${OUT_DIR}/runtime_canaries_summary.json"
MANIFEST="${OUT_DIR}/runtime_canaries_manifest.json"
CANARY_SPECS=(
  "manual_no_evidence_skips_llm|tests/agent/test_dj_cohost_linter.py::test_manual_silent_trigger_skips_llm_before_tts"
  "manual_audio_signal_reaches_model|tests/agent/test_dj_cohost_linter.py::test_manual_trigger_with_audio_signal_still_reaches_model"
  "audio_causal_guard_strips_before_tts|tests/agent/test_dj_cohost_linter.py::test_live_claim_guard_corrects_move_effect_verdict"
  "audio_source_detail_guard_strips_before_tts|tests/agent/test_dj_cohost_linter.py::test_live_claim_guard_strips_hidden_source_detail_before_tts"
  "audio_listener_read_survives_before_tts|tests/agent/test_dj_cohost_linter.py::test_live_claim_guard_allows_broad_audio_listener_read_before_tts"
  "guard_fallback_stays_silent|tests/eval/test_cohost_viber_session_report.py::test_report_blocks_spoken_live_claim_guard_fallback"
  "uncertain_ack_loop_becomes_silence|tests/eval/test_cohost_viber_session_report.py::test_repeated_ack_only_zero_citation_blocks_uncertain_tts"
  "manual_silence_report_is_not_repair|tests/eval/test_cohost_viber_session_report.py::test_report_accepts_pre_llm_manual_silence_without_repair"
)
CANARY_NODES=()
for spec in "${CANARY_SPECS[@]}"; do
  CANARY_NODES+=("${spec#*|}")
done
RUNTIME_CANARY_MANIFEST="${MANIFEST}" \
RUNTIME_CANARY_SPECS="$(printf '%s\n' "${CANARY_SPECS[@]}")" \
  "${PY_CMD[@]}" - <<'PY'
import json
import os
from pathlib import Path

canaries: list[dict[str, str]] = []
for line in os.environ["RUNTIME_CANARY_SPECS"].splitlines():
    if not line.strip():
        continue
    canary_id, proof = line.split("|", 1)
    canaries.append({"id": canary_id, "proof": proof})
Path(os.environ["RUNTIME_CANARY_MANIFEST"]).write_text(
    json.dumps(
        {
            "schema": "cohost_viber_runtime_canaries_manifest_v1",
            "canaries": canaries,
        },
        indent=2,
    )
    + "\n",
    encoding="utf-8",
)
PY
PYTEST_ARGS=(
  -m pytest
  -q
  "${CANARY_NODES[@]}"
)

set +e
PYTHONPATH="${PYTHONPATH:-src}" "${PY_CMD[@]}" "${PYTEST_ARGS[@]}" \
  >"${STDOUT_LOG}" 2>"${STDERR_LOG}"
RC=$?
set -e

RUNTIME_CANARY_OUT_DIR="${OUT_DIR}" \
RUNTIME_CANARY_RC="${RC}" \
RUNTIME_CANARY_STDOUT="${STDOUT_LOG}" \
RUNTIME_CANARY_STDERR="${STDERR_LOG}" \
RUNTIME_CANARY_SUMMARY="${SUMMARY}" \
RUNTIME_CANARY_MANIFEST="${MANIFEST}" \
  "${PY_CMD[@]}" - <<'PY'
import json
import os
import re
from pathlib import Path

out_dir = os.environ["RUNTIME_CANARY_OUT_DIR"]
rc = int(os.environ["RUNTIME_CANARY_RC"])
stdout_path = Path(os.environ["RUNTIME_CANARY_STDOUT"])
stderr_path = Path(os.environ["RUNTIME_CANARY_STDERR"])
summary_path = Path(os.environ["RUNTIME_CANARY_SUMMARY"])
stdout = stdout_path.read_text(encoding="utf-8") if stdout_path.exists() else ""
stderr = stderr_path.read_text(encoding="utf-8") if stderr_path.exists() else ""
combined = stdout + "\n" + stderr
manifest_path = Path(os.environ["RUNTIME_CANARY_MANIFEST"])
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
canaries = manifest.get("canaries") if isinstance(manifest.get("canaries"), list) else []


def _count(label: str) -> int:
    match = re.search(rf"(\d+)\s+{re.escape(label)}", combined)
    return int(match.group(1)) if match else 0


passed = _count("passed")
failed = _count("failed") + _count("error")
exercised = passed + failed
missing = max(0, len(canaries) - exercised)
coverage_ok = missing == 0
summary = {
    "schema": "cohost_viber_runtime_canaries_v1",
    "ok": rc == 0 and coverage_ok,
    "rc": rc,
    "out_dir": out_dir,
    "canary_count": len(canaries),
    "passed": passed,
    "failed": failed,
    "exercised": exercised,
    "coverage_ok": coverage_ok,
    "missing_canaries": missing,
    "deselected": _count("deselected"),
    "canaries": canaries,
    "artifacts": {
        "stdout": str(stdout_path),
        "stderr": str(stderr_path),
        "manifest": str(manifest_path),
    },
}
summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
PY

SUMMARY_LINE=$(
  "${PY_CMD[@]}" - "${SUMMARY}" <<'PY'
import json
import sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print(
    "ok={ok} canaries={canaries} exercised={exercised} passed={passed} "
    "failed={failed} missing={missing} out_dir={out_dir}".format(
        ok=data.get("ok"),
        canaries=data.get("canary_count", 0),
        exercised=data.get("exercised", 0),
        passed=data.get("passed", 0),
        failed=data.get("failed", 0),
        missing=data.get("missing_canaries", 0),
        out_dir=data.get("out_dir"),
    )
)
PY
)

SUMMARY_OK="$("${PY_CMD[@]}" - "${SUMMARY}" <<'PY'
import json
import sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print("1" if data.get("ok") else "0")
PY
)"

if [ "${SUMMARY_OK}" = "1" ]; then
  emit_pass "${SUMMARY_LINE}"
  exit 0
fi

emit_err "${SUMMARY_LINE}"
if [ "${RC}" -ne 0 ]; then
  exit "${RC}"
fi
exit 1
