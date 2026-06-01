#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
#
# One-command cohost/Viber release matrix.
#
# Runs the current deterministic automation gates and keeps their artifacts in
# one directory:
#   1. latest-session autopilot
#   2. refreshed failure-corpus benchmark
#   3. focused runtime canaries for anti-hallucination behavior
#   4. optional/auto/required FLX4 live-context proof
#
# Env:
#   COHOST_VIBER_MATRIX_MODE       automation|release|first-pass|audio-evidence (default: release)
#   COHOST_VIBER_MATRIX_OUT_DIR    artifact dir (default: .planning/eval-runs/cohost-viber-matrix)
#   COHOST_VIBER_MATRIX_FLX4       auto|required|skip (default: auto)
#   COHOST_VIBER_MATRIX_WRAPPER_DIR override wrapper dir for tests
#   COHOST_VIBER_FLX4_PORT_RE      MIDI/audio match text for auto detection (default: DDJ-FLX4)
#   COHOST_VIBER_FLX4_DIRECT_MIDI_PROBE_S optional OS-level MIDI motion probe seconds
#   COHOST_VIBER_FLX4_DIRECT_MIDI_PROBE_MODE poll|callback for direct probe (default: callback)
#   PYTHON                         Python executable; defaults to .venv, uv, then python3

set -euo pipefail

MODE="${COHOST_VIBER_MATRIX_MODE:-release}"
OUT_DIR="${COHOST_VIBER_MATRIX_OUT_DIR:-.planning/eval-runs/cohost-viber-matrix}"
FLX4_MODE="${COHOST_VIBER_MATRIX_FLX4:-auto}"
PORT_RE="${COHOST_VIBER_FLX4_PORT_RE:-DDJ-FLX4}"
WRAPPER_DIR="${COHOST_VIBER_MATRIX_WRAPPER_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
CORPUS_SESSION_DIR="${COHOST_VIBER_CORPUS_SESSION_DIR:-${COHOST_VIBER_SESSION_DIR:-}}"
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
    echo "::error::check_cohost_viber_matrix: ${msg}" >&2
  else
    echo "FAIL check_cohost_viber_matrix: ${msg}" >&2
  fi
}

emit_pass() {
  echo "PASS check_cohost_viber_matrix: $*"
}

if ! command -v "${PY_CMD[0]}" >/dev/null 2>&1; then
  emit_err "${PY_CMD[0]} is required but not found on PATH"
  exit 1
fi

case "${MODE}" in
  automation|release|first-pass|audio-evidence) ;;
  *)
    emit_err "COHOST_VIBER_MATRIX_MODE must be automation, release, first-pass, or audio-evidence, got ${MODE}"
    exit 2
    ;;
esac

AUTOPILOT_FAIL_ON="${MODE}"
CORPUS_FAIL_ON="${MODE}"
if [ "${MODE}" = "first-pass" ] || [ "${MODE}" = "audio-evidence" ]; then
  CORPUS_FAIL_ON="automation"
fi

case "${FLX4_MODE}" in
  auto|required|skip) ;;
  *)
    emit_err "COHOST_VIBER_MATRIX_FLX4 must be auto, required, or skip, got ${FLX4_MODE}"
    exit 2
    ;;
esac

mkdir -p "${OUT_DIR}"

run_check() {
  local name="$1"
  shift
  local stdout_path="${OUT_DIR}/${name}.stdout.log"
  local stderr_path="${OUT_DIR}/${name}.stderr.log"
  set +e
  "$@" >"${stdout_path}" 2>"${stderr_path}"
  local rc=$?
  set -e
  echo "${rc}"
}

first_summary_line() {
  local name="$1"
  local stdout_path="${OUT_DIR}/${name}.stdout.log"
  local stderr_path="${OUT_DIR}/${name}.stderr.log"
  local line=""
  for path in "${stdout_path}" "${stderr_path}"; do
    if [ -s "${path}" ]; then
      line="$(grep -E '^(PASS|FAIL|SKIP) ' "${path}" | head -n 1 || true)"
      if [ -n "${line}" ]; then
        echo "${line}"
        return
      fi
    fi
  done
  for path in "${stdout_path}" "${stderr_path}"; do
    if [ -s "${path}" ]; then
      line="$(grep -Ev '^ACTION ' "${path}" | head -n 1 || true)"
      if [ -n "${line}" ]; then
        echo "${line}"
        return
      fi
    fi
  done
  if [ -s "${stdout_path}" ]; then
    head -n 1 "${stdout_path}"
  elif [ -s "${stderr_path}" ]; then
    head -n 1 "${stderr_path}"
  else
    echo "(no output)"
  fi
}

AUTOPILOT_RC=$(
  run_check autopilot env \
    COHOST_VIBER_OUT_DIR="${OUT_DIR}/autopilot" \
    COHOST_VIBER_FAIL_ON="${AUTOPILOT_FAIL_ON}" \
    bash "${WRAPPER_DIR}/check_cohost_viber_autopilot.sh"
)

EFFECTIVE_GLOBAL_SINCE_ISO="${COHOST_VIBER_GLOBAL_SINCE_ISO:-}"
if [ -z "${EFFECTIVE_GLOBAL_SINCE_ISO}" ]; then
  EFFECTIVE_GLOBAL_SINCE_ISO="$(
    "${PY_CMD[@]}" - "${OUT_DIR}/autopilot/autopilot_summary.json" <<'PY' 2>/dev/null || true
import json
import sys
from pathlib import Path

try:
    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
except Exception:
    data = {}
value = data.get("global_since_iso") if isinstance(data, dict) else None
if value:
    print(value)
PY
  )"
fi

CORPUS_RC=$(
  run_check corpus env \
    COHOST_VIBER_CORPUS_OUT_DIR="${OUT_DIR}/corpus" \
    COHOST_VIBER_CORPUS_FAIL_ON="${CORPUS_FAIL_ON}" \
    COHOST_VIBER_CORPUS_SESSION_DIR="${CORPUS_SESSION_DIR}" \
    COHOST_VIBER_GLOBAL_SINCE_ISO="${EFFECTIVE_GLOBAL_SINCE_ISO}" \
    bash "${WRAPPER_DIR}/check_cohost_viber_corpus_benchmark.sh"
)

RUNTIME_RC=$(
  run_check runtime_canaries env \
    COHOST_VIBER_RUNTIME_CANARY_OUT_DIR="${OUT_DIR}/runtime-canaries" \
    bash "${WRAPPER_DIR}/check_cohost_viber_runtime_canaries.sh"
)

FLX4_RAN="false"
FLX4_REQUIRED="false"
FLX4_RC=0
FLX4_AUTO_REASON="skipped"
if [ "${FLX4_MODE}" = "required" ]; then
  FLX4_RAN="true"
  FLX4_REQUIRED="true"
elif [ "${FLX4_MODE}" = "auto" ]; then
  MIDI_PROBE="${OUT_DIR}/flx4-auto-midi.txt"
  MIDI_PROBE_ERR="${OUT_DIR}/flx4-auto-midi.stderr.log"
  set +e
  "${PY_CMD[@]}" scripts/sniff_controller.py --list >"${MIDI_PROBE}" 2>"${MIDI_PROBE_ERR}"
  MIDI_PROBE_RC=$?
  set -e
  if [ "${MIDI_PROBE_RC}" -eq 0 ] && grep -qi "${PORT_RE}" "${MIDI_PROBE}"; then
    FLX4_RAN="true"
    FLX4_REQUIRED="true"
    FLX4_AUTO_REASON="detected"
  else
    FLX4_AUTO_REASON="not_detected"
  fi
fi

if [ "${FLX4_RAN}" = "true" ]; then
  FLX4_RC=$(
    run_check flx4 env \
      COHOST_VIBER_FLX4_OUT_DIR="${OUT_DIR}/flx4" \
      bash "${WRAPPER_DIR}/check_flx4_live_context.sh"
  )
fi

AUTOPILOT_LINE="$(first_summary_line autopilot)"
CORPUS_LINE="$(first_summary_line corpus)"
RUNTIME_LINE="$(first_summary_line runtime_canaries)"
FLX4_LINE="$(
  if [ "${FLX4_RAN}" = "true" ]; then
    first_summary_line flx4
  else
    echo "SKIP check_flx4_live_context: ${FLX4_AUTO_REASON}"
  fi
)"
FLX4_SUMMARY_JSON="${OUT_DIR}/flx4/flx4_live_context_summary.json"

SUMMARY_JSON="${OUT_DIR}/matrix_summary.json"
MATRIX_MODE="${MODE}" \
MATRIX_AUTOPILOT_FAIL_ON="${AUTOPILOT_FAIL_ON}" \
MATRIX_CORPUS_FAIL_ON="${CORPUS_FAIL_ON}" \
MATRIX_OUT_DIR="${OUT_DIR}" \
MATRIX_AUTOPILOT_RC="${AUTOPILOT_RC}" \
MATRIX_CORPUS_RC="${CORPUS_RC}" \
MATRIX_RUNTIME_RC="${RUNTIME_RC}" \
MATRIX_FLX4_RC="${FLX4_RC}" \
MATRIX_FLX4_RAN="${FLX4_RAN}" \
MATRIX_FLX4_REQUIRED="${FLX4_REQUIRED}" \
MATRIX_FLX4_MODE="${FLX4_MODE}" \
MATRIX_FLX4_AUTO_REASON="${FLX4_AUTO_REASON}" \
MATRIX_SESSION_DIR="${COHOST_VIBER_SESSION_DIR:-}" \
MATRIX_CORPUS_SESSION_DIR="${CORPUS_SESSION_DIR}" \
MATRIX_GLOBAL_SINCE_ISO="${EFFECTIVE_GLOBAL_SINCE_ISO}" \
MATRIX_AUTOPILOT_LINE="${AUTOPILOT_LINE}" \
MATRIX_CORPUS_LINE="${CORPUS_LINE}" \
MATRIX_RUNTIME_LINE="${RUNTIME_LINE}" \
MATRIX_FLX4_LINE="${FLX4_LINE}" \
MATRIX_FLX4_SUMMARY_JSON="${FLX4_SUMMARY_JSON}" \
  "${PY_CMD[@]}" - "${SUMMARY_JSON}" <<'PY'
import json
import os
import shlex
import sys
from pathlib import Path

mode = os.environ["MATRIX_MODE"]
out_dir = os.environ["MATRIX_OUT_DIR"]
autopilot_rc = int(os.environ["MATRIX_AUTOPILOT_RC"])
corpus_rc = int(os.environ["MATRIX_CORPUS_RC"])
runtime_rc = int(os.environ["MATRIX_RUNTIME_RC"])
flx4_rc = int(os.environ["MATRIX_FLX4_RC"])
flx4_ran = os.environ["MATRIX_FLX4_RAN"] == "true"
flx4_required = os.environ["MATRIX_FLX4_REQUIRED"] == "true"
flx4_summary_path = Path(os.environ["MATRIX_FLX4_SUMMARY_JSON"])
def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


autopilot_summary_path = Path(out_dir) / "autopilot" / "autopilot_summary.json"
autopilot_summary = _read_json(autopilot_summary_path)
autopilot_stdout_path = Path(out_dir) / "autopilot.stdout.log"
autopilot_stderr_path = Path(out_dir) / "autopilot.stderr.log"
autopilot_artifacts = (
    autopilot_summary.get("artifacts")
    if isinstance(autopilot_summary.get("artifacts"), dict)
    else {}
)
autopilot_report_path = Path(
    str(autopilot_artifacts.get("report_json") or (Path(out_dir) / "autopilot" / "report.json"))
)
autopilot_report_md_path = Path(
    str(autopilot_artifacts.get("report_md") or (Path(out_dir) / "autopilot" / "report.md"))
)
autopilot_pack_path = Path(
    str(autopilot_artifacts.get("reprompt_pack") or (Path(out_dir) / "autopilot" / "reprompt-pack"))
)
autopilot_repair_path = Path(
    str(autopilot_artifacts.get("repair_run") or (Path(out_dir) / "autopilot" / "repair-run"))
)
autopilot_report = _read_json(autopilot_report_path)
autopilot_pack_manifest_path = autopilot_pack_path / "manifest.json"
autopilot_pack_manifest = _read_json(autopilot_pack_manifest_path)
autopilot_repair_manifest_path = autopilot_repair_path / "repair_manifest.json"
autopilot_repair_manifest = _read_json(autopilot_repair_manifest_path)
corpus_manifest_path = Path(out_dir) / "corpus" / "corpus" / "manifest.json"
corpus_manifest = _read_json(corpus_manifest_path)
corpus_benchmark_path = Path(out_dir) / "corpus" / "benchmark" / "benchmark_manifest.json"
corpus_benchmark = _read_json(corpus_benchmark_path)
corpus_stdout_path = Path(out_dir) / "corpus.stdout.log"
corpus_stderr_path = Path(out_dir) / "corpus.stderr.log"
runtime_summary_path = Path(out_dir) / "runtime-canaries" / "runtime_canaries_summary.json"
runtime_summary = _read_json(runtime_summary_path)
flx4_summary = _read_json(flx4_summary_path)


def _issues_by_severity(report: dict, severity: str) -> list[dict]:
    issues = report.get("issues") if isinstance(report.get("issues"), list) else []
    return [
        issue
        for issue in issues
        if isinstance(issue, dict) and str(issue.get("severity") or "") == severity
    ]


care_issues = _issues_by_severity(autopilot_report, "care")
watch_issues = _issues_by_severity(autopilot_report, "watch")
first_care_issue = care_issues[0] if care_issues else {}
all_autopilot_issues = (
    autopilot_report.get("issues") if isinstance(autopilot_report.get("issues"), list) else []
)
audio_debt_codes = {
    str(code)
    for code in (autopilot_summary.get("audio_evidence_debt_by_code") or {}).keys()
}
audio_debt_issues = [
    issue
    for issue in all_autopilot_issues
    if isinstance(issue, dict)
    and str(issue.get("severity") or "") in {"blocker", "care"}
    and str(issue.get("code") or "") in audio_debt_codes
]
first_audio_debt_issue = audio_debt_issues[0] if audio_debt_issues else {}
pack_jobs = (
    autopilot_pack_manifest.get("jobs")
    if isinstance(autopilot_pack_manifest.get("jobs"), list)
    else []
)
first_reprompt_job = next((job for job in pack_jobs if isinstance(job, dict)), {})
first_reprompt_path = None
if first_reprompt_job.get("job_id"):
    first_reprompt_path = autopilot_pack_path / str(first_reprompt_job["job_id"]) / "reprompt.md"
def _job_matches_issue(job: dict, issue: dict) -> bool:
    if not issue:
        return False
    job_issue = job.get("issue") if isinstance(job.get("issue"), dict) else {}
    if job_issue.get("code") != issue.get("code"):
        return False
    response_id = issue.get("response_id")
    if response_id and job_issue.get("response_id") != response_id:
        return False
    artifact = issue.get("artifact")
    if artifact and job_issue.get("artifact") != artifact:
        return False
    return True


first_care_reprompt_job = next(
    (
        job
        for job in pack_jobs
        if isinstance(job, dict) and _job_matches_issue(job, first_care_issue)
    ),
    {},
)
first_care_reprompt_path = None
if first_care_reprompt_job.get("job_id"):
    first_care_reprompt_path = (
        autopilot_pack_path / str(first_care_reprompt_job["job_id"]) / "reprompt.md"
    )
first_audio_debt_reprompt_job = next(
    (
        job
        for job in pack_jobs
        if isinstance(job, dict) and _job_matches_issue(job, first_audio_debt_issue)
    ),
    {},
)
first_audio_debt_reprompt_path = None
if first_audio_debt_reprompt_job.get("job_id"):
    first_audio_debt_reprompt_path = (
        autopilot_pack_path / str(first_audio_debt_reprompt_job["job_id"]) / "reprompt.md"
    )
repair_results = (
    autopilot_repair_manifest.get("results")
    if isinstance(autopilot_repair_manifest.get("results"), list)
    else []
)
def _repair_for_job(job: dict) -> dict:
    job_id = job.get("job_id") if isinstance(job, dict) else None
    if job_id:
        found = next(
            (
                item
                for item in repair_results
                if isinstance(item, dict) and item.get("job_id") == job_id
            ),
            {},
        )
        if found:
            return found
    return next((item for item in repair_results if isinstance(item, dict)), {})


def _repair_projection(result: dict):
    if not result:
        return None
    candidate_path = (
        Path(str(result.get("candidate_path")))
        if isinstance(result.get("candidate_path"), str)
        else None
    )
    score_path = (
        Path(str(result.get("score_path")))
        if isinstance(result.get("score_path"), str)
        else None
    )
    candidate = _read_json(candidate_path) if candidate_path is not None else {}
    reply = str(candidate.get("reply") or "")
    return {
        "job_id": result.get("job_id"),
        "ok": result.get("ok"),
        "candidate_path": str(candidate_path) if candidate_path else None,
        "score_path": str(score_path) if score_path else None,
        "violations": result.get("violations") or [],
        "reply_kind": "silence" if reply == "" else "spoken",
        "reply_preview": reply[:240],
    }


first_repair_result = _repair_for_job(first_reprompt_job)
first_repair_projection = _repair_projection(first_repair_result)
first_care_repair_result = _repair_for_job(first_care_reprompt_job)
first_care_repair_projection = _repair_projection(first_care_repair_result)
first_audio_debt_repair_result = _repair_for_job(first_audio_debt_reprompt_job)
first_audio_debt_repair_projection = _repair_projection(first_audio_debt_repair_result)
summary = {
    "schema": "cohost_viber_release_matrix_v1",
    "mode": mode,
    "autopilot_fail_on": os.environ["MATRIX_AUTOPILOT_FAIL_ON"],
    "corpus_fail_on": os.environ["MATRIX_CORPUS_FAIL_ON"],
    "out_dir": out_dir,
    "session_dir": os.environ["MATRIX_SESSION_DIR"] or None,
    "corpus_session_dir": os.environ["MATRIX_CORPUS_SESSION_DIR"] or None,
    "global_since_iso": (
        os.environ["MATRIX_GLOBAL_SINCE_ISO"]
        or autopilot_summary.get("global_since_iso")
        or None
    ),
    "checks": {
        "autopilot": {
            "rc": autopilot_rc,
            "ok": autopilot_rc == 0 and bool(autopilot_summary) and bool(autopilot_report),
            "required": True,
            "summary": os.environ["MATRIX_AUTOPILOT_LINE"],
            "out_dir": out_dir + "/autopilot",
            "summary_json": str(autopilot_summary_path),
            "summary_present": bool(autopilot_summary),
            "status": autopilot_summary.get("status"),
            "release_gate_ok": autopilot_summary.get("release_gate_ok"),
            "first_pass_clean": autopilot_summary.get("first_pass_clean"),
            "reprompt_debt": autopilot_summary.get("reprompt_debt"),
            "audio_evidence_debt": autopilot_summary.get("audio_evidence_debt", 0),
            "audio_evidence_debt_by_code": (
                autopilot_summary.get("audio_evidence_debt_by_code") or {}
            ),
            "global_since_iso": autopilot_summary.get("global_since_iso"),
            "initial_issue_counts": autopilot_summary.get("initial_issue_counts") or {},
            "reprompt_jobs": autopilot_summary.get("reprompt_jobs"),
            "report_json": str(autopilot_report_path),
            "report_present": bool(autopilot_report),
            "report_md": str(autopilot_report_md_path) if autopilot_report_md_path.exists() else None,
            "reprompt_pack": str(autopilot_pack_path) if autopilot_pack_manifest else None,
            "reprompt_pack_manifest": str(autopilot_pack_manifest_path) if autopilot_pack_manifest else None,
            "repair_run": str(autopilot_repair_path) if autopilot_repair_manifest else None,
            "repair_manifest": str(autopilot_repair_manifest_path) if autopilot_repair_manifest else None,
            "stdout": str(autopilot_stdout_path),
            "stderr": str(autopilot_stderr_path),
            "care_issue_codes": [
                str(issue.get("code"))
                for issue in care_issues
                if isinstance(issue.get("code"), str)
            ],
            "watch_issue_codes": [
                str(issue.get("code"))
                for issue in watch_issues
                if isinstance(issue.get("code"), str)
            ],
            "first_care_issue": {
                "code": first_care_issue.get("code"),
                "title": first_care_issue.get("title"),
                "response_id": first_care_issue.get("response_id"),
                "artifact": first_care_issue.get("artifact"),
            }
            if first_care_issue
            else None,
            "first_audio_evidence_debt_issue": {
                "code": first_audio_debt_issue.get("code"),
                "severity": first_audio_debt_issue.get("severity"),
                "title": first_audio_debt_issue.get("title"),
                "response_id": first_audio_debt_issue.get("response_id"),
                "artifact": first_audio_debt_issue.get("artifact"),
            }
            if first_audio_debt_issue
            else None,
            "first_reprompt_job": {
                "job_id": first_reprompt_job.get("job_id"),
                "issue_code": (
                    first_reprompt_job.get("issue", {}).get("code")
                    if isinstance(first_reprompt_job.get("issue"), dict)
                    else None
                ),
                "issue_title": (
                    first_reprompt_job.get("issue", {}).get("title")
                    if isinstance(first_reprompt_job.get("issue"), dict)
                    else None
                ),
                "source_artifact": (
                    first_reprompt_job.get("issue", {}).get("artifact")
                    if isinstance(first_reprompt_job.get("issue"), dict)
                    else None
                ),
                "reprompt": str(first_reprompt_path) if first_reprompt_path else None,
            }
            if first_reprompt_job
            else None,
            "first_repair_result": first_repair_projection,
            "first_care_reprompt_job": {
                "job_id": first_care_reprompt_job.get("job_id"),
                "reprompt": (
                    str(first_care_reprompt_path) if first_care_reprompt_path else None
                ),
            }
            if first_care_reprompt_job
            else None,
            "first_care_repair_result": first_care_repair_projection,
            "first_audio_evidence_debt_reprompt_job": {
                "job_id": first_audio_debt_reprompt_job.get("job_id"),
                "reprompt": (
                    str(first_audio_debt_reprompt_path)
                    if first_audio_debt_reprompt_path
                    else None
                ),
            }
            if first_audio_debt_reprompt_job
            else None,
            "first_audio_evidence_debt_repair_result": first_audio_debt_repair_projection,
        },
        "corpus": {
            "rc": corpus_rc,
            "ok": corpus_rc == 0 and bool(corpus_manifest) and bool(corpus_benchmark),
            "required": True,
            "summary": os.environ["MATRIX_CORPUS_LINE"],
            "out_dir": out_dir + "/corpus",
            "manifest_json": str(corpus_manifest_path),
            "manifest_present": bool(corpus_manifest),
            "benchmark_json": str(corpus_benchmark_path),
            "benchmark_present": bool(corpus_benchmark),
            "release_ready": corpus_manifest.get("release_ready"),
            "captured_case_count": corpus_manifest.get("captured_case_count"),
            "policy_canary_count": corpus_manifest.get("policy_canary_count"),
            "case_count": corpus_benchmark.get("case_count", corpus_manifest.get("case_count")),
            "passed": corpus_benchmark.get("passed"),
            "failed": corpus_benchmark.get("failed"),
            "stdout": str(corpus_stdout_path),
            "stderr": str(corpus_stderr_path),
        },
        "runtime_canaries": {
            "rc": runtime_rc,
            "ok": (
                runtime_rc == 0
                and bool(runtime_summary)
                and runtime_summary.get("ok", runtime_rc == 0) is not False
            ),
            "required": True,
            "summary": os.environ["MATRIX_RUNTIME_LINE"],
            "out_dir": out_dir + "/runtime-canaries",
            "summary_json": str(runtime_summary_path),
            "summary_present": bool(runtime_summary),
            "canary_count": runtime_summary.get("canary_count"),
            "passed": runtime_summary.get("passed"),
            "failed": runtime_summary.get("failed"),
            "exercised": runtime_summary.get("exercised"),
            "coverage_ok": runtime_summary.get("coverage_ok"),
            "missing_canaries": runtime_summary.get("missing_canaries"),
            "canaries": runtime_summary.get("canaries") if runtime_summary else [],
            "artifacts": (
                runtime_summary.get("artifacts")
                if isinstance(runtime_summary.get("artifacts"), dict)
                else {}
            ),
        },
        "flx4": {
            "rc": flx4_rc,
            "ok": flx4_rc == 0,
            "ran": flx4_ran,
            "required": flx4_required,
            "mode": os.environ["MATRIX_FLX4_MODE"],
            "auto_reason": os.environ["MATRIX_FLX4_AUTO_REASON"],
            "summary": os.environ["MATRIX_FLX4_LINE"],
            "out_dir": out_dir + "/flx4",
            "summary_json": str(flx4_summary_path) if flx4_summary else None,
            "diagnosis": flx4_summary.get("diagnosis"),
            "action_hint": flx4_summary.get("action_hint"),
            "first_blocker": flx4_summary.get("first_blocker"),
            "top_blockers": flx4_summary.get("top_blockers") if flx4_summary else [],
            "operator_actions": flx4_summary.get("operator_actions") if flx4_summary else [],
            "setup_hint": (
                flx4_summary.get("setup_hint")
                if isinstance(flx4_summary.get("setup_hint"), dict)
                else {}
            ),
            "proof_legs": flx4_summary.get("proof_legs") if flx4_summary else [],
            "proof_legs_passed": flx4_summary.get("proof_legs_passed"),
            "proof_legs_total": flx4_summary.get("proof_legs_total"),
            "proof_missing_legs": [
                str(leg.get("id"))
                for leg in (flx4_summary.get("proof_legs") if flx4_summary else [])
                if isinstance(leg, dict)
                and str(leg.get("status") or "") != "pass"
                and leg.get("id")
            ],
            "checks": (
                flx4_summary.get("checks")
                if isinstance(flx4_summary.get("checks"), dict)
                else {}
            ),
            "direct_midi_probe": (
                flx4_summary.get("direct_midi_probe") if flx4_summary else {}
            ),
            "midi_motion_diagnosis": flx4_summary.get("midi_motion_diagnosis"),
        },
    },
}
summary["ok"] = all(
    (not check.get("required")) or check.get("ok")
    for check in summary["checks"].values()
)


def _audio_debt_action(autopilot: dict, *, code: str, fail_on: str) -> dict:
    debt = int(autopilot.get("audio_evidence_debt") or 0)
    if debt <= 0:
        return {}
    first_issue = (
        autopilot.get("first_audio_evidence_debt_issue")
        if isinstance(autopilot.get("first_audio_evidence_debt_issue"), dict)
        else {}
    )
    first_job = (
        autopilot.get("first_audio_evidence_debt_reprompt_job")
        if isinstance(autopilot.get("first_audio_evidence_debt_reprompt_job"), dict)
        else {}
    )
    first_repair = (
        autopilot.get("first_audio_evidence_debt_repair_result")
        if isinstance(autopilot.get("first_audio_evidence_debt_repair_result"), dict)
        else {}
    )
    issue_code = str(first_issue.get("code") or "audio_evidence_debt")
    issue_severity = str(first_issue.get("severity") or "unknown")
    repair_kind = str(first_repair.get("reply_kind") or "unknown")
    artifacts = {
        "report_json": autopilot.get("report_json"),
        "report_md": autopilot.get("report_md"),
        "reprompt_pack": autopilot.get("reprompt_pack"),
        "repair_manifest": autopilot.get("repair_manifest"),
        "repair_candidate": first_repair.get("candidate_path"),
        "repair_score": first_repair.get("score_path"),
        "reprompt": first_job.get("reprompt"),
        "source_artifact": first_issue.get("artifact"),
    }
    return {
        "code": code,
        "source": "autopilot",
        "detail": (
            f"Audio/live evidence debt={debt}; first_issue={issue_code}; "
            f"severity={issue_severity}; repair_candidate={repair_kind}; "
            "review the raw prompt/response before claiming the cohost or Viber "
            "can use audio without overclaiming."
        ),
        "artifacts": {key: value for key, value in artifacts.items() if value},
        "recommended_command": (
            f"COHOST_VIBER_FAIL_ON={fail_on} "
            "bash scripts/release/check_cohost_viber_autopilot.sh"
        ),
    }


def _autopilot_action(autopilot: dict, *, fail_on: str) -> dict:
    artifact_refs = {
        "summary_json": autopilot.get("summary_json"),
        "report_json": autopilot.get("report_json"),
        "stdout": autopilot.get("stdout"),
        "stderr": autopilot.get("stderr"),
    }
    recommended_command = (
        f"COHOST_VIBER_FAIL_ON={fail_on} "
        "bash scripts/release/check_cohost_viber_autopilot.sh"
    )
    if not autopilot.get("summary_present"):
        return {
            "code": "restore_autopilot_summary",
            "source": "autopilot",
            "detail": (
                "Autopilot wrapper did not produce a readable summary JSON. "
                "Rerun it and inspect stdout/stderr before trusting cohost/Viber "
                "benchmark automation."
            ),
            "artifacts": {key: value for key, value in artifact_refs.items() if value},
            "recommended_command": recommended_command,
        }
    if not autopilot.get("report_present"):
        return {
            "code": "restore_autopilot_report",
            "source": "autopilot",
            "detail": (
                "Autopilot summary exists, but the issue report JSON is missing or "
                "unreadable. Restore the report artifact before trusting reprompt "
                "or repair automation."
            ),
            "artifacts": {key: value for key, value in artifact_refs.items() if value},
            "recommended_command": recommended_command,
        }
    audio_action = _audio_debt_action(
        autopilot,
        code="inspect_audio_evidence_debt",
        fail_on=fail_on,
    )
    if audio_action:
        return audio_action
    return {
        "code": "inspect_autopilot",
        "source": "autopilot",
        "detail": str(autopilot.get("summary") or "Inspect cohost/Viber autopilot artifacts."),
        "recommended_command": recommended_command,
    }


def _corpus_action(corpus: dict, *, fail_on: str) -> dict:
    artifact_refs = {
        "manifest_json": corpus.get("manifest_json"),
        "benchmark_json": corpus.get("benchmark_json"),
        "stdout": corpus.get("stdout"),
        "stderr": corpus.get("stderr"),
    }
    recommended_command = (
        f"COHOST_VIBER_CORPUS_FAIL_ON={fail_on} "
        "bash scripts/release/check_cohost_viber_corpus_benchmark.sh"
    )
    missing = []
    if not corpus.get("manifest_present"):
        missing.append("manifest_json")
    if not corpus.get("benchmark_present"):
        missing.append("benchmark_json")
    if missing:
        return {
            "code": "restore_corpus_benchmark_artifacts",
            "source": "corpus",
            "detail": (
                "Corpus benchmark wrapper did not produce readable evidence "
                f"artifacts: missing={','.join(missing)}. Rerun it and inspect "
                "stdout/stderr before trusting the captured-failure benchmark."
            ),
            "artifacts": {key: value for key, value in artifact_refs.items() if value},
            "recommended_command": recommended_command,
        }
    return {
        "code": "inspect_corpus",
        "source": "corpus",
        "detail": str(corpus.get("summary") or "Inspect cohost/Viber corpus artifacts."),
        "recommended_command": recommended_command,
    }


def _live_rehearsal_recommended_command(mode: str) -> str:
    return (
        f"COHOST_VIBER_REHEARSAL_MATRIX_MODE={mode} "
        "COHOST_VIBER_REHEARSAL_START_LIVE=required "
        "COHOST_VIBER_REHEARSAL_FLX4=required "
        "bash scripts/release/check_cohost_viber_live_rehearsal.sh"
    )


def _direct_midi_probe_command(*, mode: str, seconds: int = 10) -> str:
    return f"python scripts/sniff_controller.py --port DDJ-FLX4 --seconds {seconds} --mode {mode}"


def _live_context_proof_command(*, out_name: str) -> str:
    return (
        "python -m vibemix library live-context --require-proof --wait-ready 10 "
        f"--interval 1 --timeout 1 --frames 90 --json --out .planning/proofs/{out_name}"
    )


def _audio_probe_commands() -> list[str]:
    return [
        (
            "python -m vibemix library live-context --wait-ready 10 --interval 1 "
            "--timeout 1 --frames 60 --json --out .planning/proofs/live-context-audio-proof.json"
        ),
        "system_profiler SPAudioDataType | grep -i 'BlackHole\\|DDJ-FLX4' -A 8",
    ]


def _deck_capture_probe_commands() -> list[str]:
    return [
        _live_context_proof_command(out_name="live-context-deck-capture-proof.json"),
        "system_profiler SPAudioDataType | grep -i 'BlackHole 16ch\\|DDJ-FLX4' -A 8",
    ]


def _flx4_action(data: dict, flx4: dict) -> dict:
    mode = str(data.get("mode") or "automation")
    recommended_command = _live_rehearsal_recommended_command(mode)
    checks = flx4.get("checks") if isinstance(flx4.get("checks"), dict) else {}
    direct_probe = (
        flx4.get("direct_midi_probe")
        if isinstance(flx4.get("direct_midi_probe"), dict)
        else {}
    )
    direct_ran = bool(direct_probe.get("ran"))
    direct_motion = bool(direct_probe.get("motion_observed"))
    setup_hint = flx4.get("setup_hint") if isinstance(flx4.get("setup_hint"), dict) else {}

    if direct_ran and not direct_motion and not checks.get("recent_moves_seen"):
        return {
            "code": "prove_os_midi_motion",
            "source": "flx4",
            "detail": (
                "The direct OS MIDI probe saw no FLX4 frames during the proof window. "
                "Move a fader/knob during the probe or fix USB/MIDI input before "
                "trusting live controller moves."
            ),
            "diagnostic_commands": [
                _direct_midi_probe_command(mode="callback"),
                _direct_midi_probe_command(mode="poll"),
            ],
            "recommended_command": recommended_command,
        }
    if direct_ran and direct_motion and not checks.get("recent_moves_seen"):
        return {
            "code": "restart_live_midi_listener",
            "source": "flx4",
            "detail": (
                "Direct OS MIDI saw FLX4 frames, but live-context did not ingest "
                "recent controller moves. Restart the live session and inspect MIDI listener binding."
            ),
            "diagnostic_commands": [
                _direct_midi_probe_command(
                    mode=str(direct_probe.get("mode") or "callback")
                )
            ],
            "recommended_command": recommended_command,
        }
    if checks.get("recent_moves_seen") and not checks.get("audio_observed"):
        return {
            "code": "play_audible_audio",
            "source": "flx4",
            "detail": (
                "Controller motion is visible, but live audio stayed below the floor. "
                "Play audible DJ app output into the configured capture route during the proof window."
            ),
            "diagnostic_commands": _audio_probe_commands(),
            "recommended_command": recommended_command,
        }
    if checks.get("recent_moves_seen") and checks.get("audio_observed"):
        if not checks.get("deck_state_pair_resolved"):
            return {
                "code": "resolve_deck_identity",
                "source": "flx4",
                "detail": (
                    "Controller motion and master audio are visible, but Deck A/B identity "
                    "is still not resolved enough to cite. Load identifiable tracks on both decks "
                    "and make the active deck posture obvious before rerunning."
                ),
                "diagnostic_commands": [
                    _live_context_proof_command(
                        out_name="live-context-deck-identity-proof.json"
                    )
                ],
                "recommended_command": recommended_command,
            }
        if not checks.get("deck_pair_capture_configured"):
            return {
                "code": "configure_deck_pair_capture",
                "source": "flx4",
                "detail": (
                    "Deck identity, controller motion, and master audio are visible, but "
                    "per-deck audio capture is not configured. Start the live session with "
                    "deck-pair capture enabled so Viber can hear Deck A and Deck B as separate evidence lanes."
                ),
                "diagnostic_commands": _deck_capture_probe_commands(),
                "recommended_env": setup_hint.get("recommended_env") or {
                    "VIBEMIX_DECK_AUDIO_CHANNELS": "auto"
                },
                "setup_hint": setup_hint or None,
                "recommended_command": recommended_command,
            }
        if not checks.get("deck_audio_capture_both_active"):
            return {
                "code": "feed_both_deck_lanes",
                "source": "flx4",
                "detail": (
                    "Per-deck capture is configured, but it has not seen active audio on both deck lanes. "
                    "For a BlackHole 16ch/Rekordbox rig, route Deck 1 to BlackHole channels 1/2 "
                    "and Deck 2 to channels 3/4, or update VIBEMIX_DECK_AUDIO_CHANNELS to the actual "
                    "A/B channel map. Rerun until the proof shows deck_audio_capture=A_active+B_active."
                ),
                "diagnostic_commands": _deck_capture_probe_commands(),
                "recommended_command": recommended_command,
            }

    actions = flx4.get("operator_actions")
    if isinstance(actions, list) and actions:
        first = actions[0] if isinstance(actions[0], dict) else {}
        return {
            "code": str(first.get("code") or flx4.get("action_hint") or "fix_flx4_proof"),
            "source": "flx4",
            "detail": str(first.get("detail") or flx4.get("first_blocker") or "Fix FLX4 proof."),
            "recommended_command": recommended_command,
        }
    return {
        "code": str(flx4.get("action_hint") or "fix_flx4_proof"),
        "source": "flx4",
        "detail": str(flx4.get("first_blocker") or "Fix FLX4 proof."),
        "recommended_command": recommended_command,
    }


def _next_operator_action(data: dict) -> dict:
    checks = data.get("checks") if isinstance(data.get("checks"), dict) else {}
    autopilot = checks.get("autopilot") if isinstance(checks.get("autopilot"), dict) else {}
    corpus = checks.get("corpus") if isinstance(checks.get("corpus"), dict) else {}
    runtime = (
        checks.get("runtime_canaries")
        if isinstance(checks.get("runtime_canaries"), dict)
        else {}
    )
    flx4 = checks.get("flx4") if isinstance(checks.get("flx4"), dict) else {}
    mode = str(data.get("mode") or "automation")
    autopilot_fail_on = str(data.get("autopilot_fail_on") or mode)
    corpus_fail_on = str(data.get("corpus_fail_on") or mode)
    if autopilot.get("required") and not autopilot.get("ok"):
        return _autopilot_action(autopilot, fail_on=autopilot_fail_on)
    if corpus.get("required") and not corpus.get("ok"):
        return _corpus_action(corpus, fail_on=corpus_fail_on)
    if runtime.get("required") and not runtime.get("ok"):
        return _runtime_action(runtime)
    if flx4.get("required") and not flx4.get("ok"):
        return _flx4_action(data, flx4)
    return {
        "code": "ready",
        "source": "matrix",
        "detail": "Cohost/Viber matrix gates are ready for the captured evidence.",
    }


def _secondary_operator_actions(data: dict) -> list[dict]:
    checks = data.get("checks") if isinstance(data.get("checks"), dict) else {}
    autopilot = checks.get("autopilot") if isinstance(checks.get("autopilot"), dict) else {}
    mode = str(data.get("mode") or "automation")
    autopilot_fail_on = str(data.get("autopilot_fail_on") or mode)
    corpus_fail_on = str(data.get("corpus_fail_on") or mode)
    actions: list[dict] = []
    issue_counts = (
        autopilot.get("initial_issue_counts")
        if isinstance(autopilot.get("initial_issue_counts"), dict)
        else {}
    )
    blockers = int(issue_counts.get("blocker") or 0)
    care = int(issue_counts.get("care") or 0)
    watch = int(issue_counts.get("watch") or 0)
    if autopilot.get("ok") and blockers > 0 and not autopilot.get("release_gate_ok"):
        first_job = (
            autopilot.get("first_reprompt_job")
            if isinstance(autopilot.get("first_reprompt_job"), dict)
            else {}
        )
        first_repair = (
            autopilot.get("first_repair_result")
            if isinstance(autopilot.get("first_repair_result"), dict)
            else {}
        )
        first_code = str(first_job.get("issue_code") or "blocker")
        repair_kind = str(first_repair.get("reply_kind") or "unknown")
        artifact_refs = {
            "report_json": autopilot.get("report_json"),
            "report_md": autopilot.get("report_md"),
            "reprompt_pack": autopilot.get("reprompt_pack"),
            "repair_manifest": autopilot.get("repair_manifest"),
            "repair_candidate": first_repair.get("candidate_path"),
            "repair_score": first_repair.get("score_path"),
            "reprompt": first_job.get("reprompt"),
            "source_artifact": first_job.get("source_artifact"),
        }
        actions.append(
            {
                "code": "review_autopilot_repair",
                "source": "autopilot",
                "detail": (
                    f"Autopilot produced repair candidates for blockers={blockers}; "
                    f"first_blocker={first_code}; repair_candidate={repair_kind}; "
                    "review the candidate and patch the prompt/guard before claiming release-ready."
                ),
                "artifacts": {key: value for key, value in artifact_refs.items() if value},
                "recommended_command": (
                    f"COHOST_VIBER_FAIL_ON={autopilot_fail_on} "
                    "bash scripts/release/check_cohost_viber_autopilot.sh"
                ),
            }
        )
    audio_action = _audio_debt_action(
        autopilot,
        code="review_audio_evidence_debt",
        fail_on=autopilot_fail_on,
    )
    if audio_action:
        actions.append(audio_action)
    if autopilot.get("ok") and (care > 0 or str(autopilot.get("status") or "") == "clean_with_care"):
        first_issue = autopilot.get("first_care_issue") if isinstance(autopilot.get("first_care_issue"), dict) else {}
        first_job = (
            autopilot.get("first_care_reprompt_job")
            if isinstance(autopilot.get("first_care_reprompt_job"), dict)
            else {}
        )
        first_repair = (
            autopilot.get("first_care_repair_result")
            if isinstance(autopilot.get("first_care_repair_result"), dict)
            else {}
        )
        first_code = str(first_issue.get("code") or "care")
        repair_kind = str(first_repair.get("reply_kind") or "unknown")
        artifact_refs = {
            "report_json": autopilot.get("report_json"),
            "report_md": autopilot.get("report_md"),
            "reprompt_pack": autopilot.get("reprompt_pack"),
            "repair_manifest": autopilot.get("repair_manifest"),
            "repair_candidate": first_repair.get("candidate_path"),
            "repair_score": first_repair.get("score_path"),
            "reprompt": first_job.get("reprompt"),
            "source_artifact": first_issue.get("artifact"),
        }
        actions.append(
            {
                "code": "review_autopilot_care",
                "source": "autopilot",
                "detail": (
                    f"Autopilot passed, but care={care} watch={watch}; first_care={first_code}; "
                    f"repair_candidate={repair_kind}; use the reprompt pack to make the model "
                    "choose the safer behavior before guards intervene."
                ),
                "artifacts": {key: value for key, value in artifact_refs.items() if value},
                "recommended_command": (
                    f"COHOST_VIBER_FAIL_ON={autopilot_fail_on} "
                    "bash scripts/release/check_cohost_viber_autopilot.sh"
                ),
            }
        )
    return actions


def _runtime_action(runtime: dict) -> dict:
    artifacts = runtime.get("artifacts") if isinstance(runtime.get("artifacts"), dict) else {}
    artifact_refs = {
        "summary_json": runtime.get("summary_json"),
        "manifest": artifacts.get("manifest"),
        "stdout": artifacts.get("stdout"),
        "stderr": artifacts.get("stderr"),
    }
    if not runtime.get("summary_present"):
        return {
            "code": "restore_runtime_canary_summary",
            "source": "runtime_canaries",
            "detail": (
                "Runtime canary wrapper did not produce a readable summary JSON. "
                "Rerun the canary wrapper and inspect stdout/stderr before trusting "
                "anti-hallucination automation."
            ),
            "artifacts": {key: value for key, value in artifact_refs.items() if value},
            "recommended_command": "bash scripts/release/check_cohost_viber_runtime_canaries.sh",
        }
    if runtime.get("coverage_ok") is False or int(runtime.get("missing_canaries") or 0) > 0:
        missing = int(runtime.get("missing_canaries") or 0)
        exercised = runtime.get("exercised")
        expected = runtime.get("canary_count")
        return {
            "code": "restore_runtime_canary_coverage",
            "source": "runtime_canaries",
            "detail": (
                f"Runtime canary coverage is incomplete: exercised={exercised} "
                f"expected={expected} missing={missing}. Restore the exact canary "
                "node list before trusting anti-hallucination automation."
            ),
            "artifacts": {key: value for key, value in artifact_refs.items() if value},
            "recommended_command": "bash scripts/release/check_cohost_viber_runtime_canaries.sh",
        }
    return {
        "code": "inspect_runtime_canaries",
        "source": "runtime_canaries",
        "detail": str(
            runtime.get("summary")
            or "Inspect focused cohost/Viber runtime canary artifacts."
        ),
        "artifacts": {key: value for key, value in artifact_refs.items() if value},
        "recommended_command": "bash scripts/release/check_cohost_viber_runtime_canaries.sh",
    }


def _failure_operator_actions(data: dict) -> list[dict]:
    checks = data.get("checks") if isinstance(data.get("checks"), dict) else {}
    autopilot = checks.get("autopilot") if isinstance(checks.get("autopilot"), dict) else {}
    corpus = checks.get("corpus") if isinstance(checks.get("corpus"), dict) else {}
    runtime = (
        checks.get("runtime_canaries")
        if isinstance(checks.get("runtime_canaries"), dict)
        else {}
    )
    flx4 = checks.get("flx4") if isinstance(checks.get("flx4"), dict) else {}
    mode = str(data.get("mode") or "automation")
    autopilot_fail_on = str(data.get("autopilot_fail_on") or mode)
    corpus_fail_on = str(data.get("corpus_fail_on") or mode)
    actions: list[dict] = []
    if autopilot.get("required") and not autopilot.get("ok"):
        actions.append(_autopilot_action(autopilot, fail_on=autopilot_fail_on))
    if corpus.get("required") and not corpus.get("ok"):
        actions.append(_corpus_action(corpus, fail_on=corpus_fail_on))
    if runtime.get("required") and not runtime.get("ok"):
        actions.append(_runtime_action(runtime))
    if flx4.get("required") and not flx4.get("ok"):
        actions.append(_flx4_action(data, flx4))
    return actions


next_action = _next_operator_action(summary)
secondary_actions = _secondary_operator_actions(summary)
queue = _failure_operator_actions(summary) or [next_action]
for action in secondary_actions:
    if action.get("code") not in {item.get("code") for item in queue}:
        queue.append(action)
summary["next_operator_action"] = next_action
summary["operator_action_queue"] = queue


def _write_operator_action_artifacts(data: dict, actions: list[dict]) -> tuple[str, str]:
    out_path = Path(str(data.get("out_dir") or "."))
    out_path.mkdir(parents=True, exist_ok=True)
    actions_path = out_path / "operator_actions.json"
    runbook_path = out_path / "operator_action_runbook.sh"
    actions_payload = {
        "schema": "cohost_viber_operator_actions_v1",
        "source": "matrix",
        "summary_json": str(Path(sys.argv[1])),
        "runbook_sh": str(runbook_path),
        "dry_run_default": True,
        "actions": actions,
    }
    actions_path.write_text(json.dumps(actions_payload, indent=2) + "\n", encoding="utf-8")

    lines = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        'REPO_ROOT="${REPO_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"',
        'cd "${REPO_ROOT}"',
        'echo "cohost/Viber operator action runbook (matrix)"',
        'echo "Set RUN_OPERATOR_COMMANDS=1 to execute; default is dry-run."',
        "",
        "run_cmd() {",
        '  local cmd="$1"',
        '  echo "+ ${cmd}"',
        '  if [ "${RUN_OPERATOR_COMMANDS:-0}" = "1" ]; then',
        '    bash -lc "${cmd}"',
        "  fi",
        "}",
        "",
        "set_env() {",
        '  local key="$1"',
        '  local value="$2"',
        '  echo "+ export ${key}=${value}"',
        '  if [ "${RUN_OPERATOR_COMMANDS:-0}" = "1" ]; then',
        '    export "${key}=${value}"',
        "  fi",
        "}",
        "",
    ]
    for index, action in enumerate(actions, start=1):
        if not isinstance(action, dict):
            continue
        title = f"[{index}] {action.get('code') or 'unknown'} ({action.get('source') or 'unknown'})"
        detail = str(action.get("detail") or "")
        lines.append(f"echo {shlex.quote(title)}")
        if detail:
            lines.append(f"echo {shlex.quote(detail)}")
        artifacts = action.get("artifacts")
        if isinstance(artifacts, dict):
            for key, value in artifacts.items():
                if value is None:
                    continue
                lines.append(f"echo {shlex.quote(f'artifact {key}: {value}')}")
        env = action.get("recommended_env")
        if isinstance(env, dict):
            for key, value in env.items():
                key_text = str(key)
                if (
                    not key_text
                    or key_text[0].isdigit()
                    or not key_text.replace("_", "").isalnum()
                    or value is None
                ):
                    continue
                lines.append(
                    "set_env "
                    f"{shlex.quote(key_text)} {shlex.quote(str(value))}"
                )
        commands = action.get("diagnostic_commands")
        if isinstance(commands, list):
            for command in commands:
                if command:
                    lines.append(f"run_cmd {shlex.quote(str(command))}")
        recommended = action.get("recommended_command")
        if recommended:
            lines.append(f"run_cmd {shlex.quote(str(recommended))}")
        lines.append("")
    runbook_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    runbook_path.chmod(0o755)
    return str(actions_path), str(runbook_path)


actions_json, runbook_sh = _write_operator_action_artifacts(summary, queue)
summary["operator_actions_json"] = actions_json
summary["operator_runbook_sh"] = runbook_sh
Path(sys.argv[1]).write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
PY

MATRIX_LINE="$("${PY_CMD[@]}" - "${SUMMARY_JSON}" <<'PY'
import json
import sys
from pathlib import Path
data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print(
    "mode={mode} ok={ok} autopilot={autopilot} corpus={corpus} runtime={runtime} flx4={flx4} "
    "first_pass={first_pass} reprompt_debt={reprompt_debt} audio_evidence_debt={audio_evidence_debt} "
    "direct_midi={direct_midi} midi_motion_diag={midi_motion_diag} flx4_missing={flx4_missing} "
    "next_action={next_action} actions={actions} recommended_command={recommended_command} "
    "runbook={runbook} out_dir={out_dir}".format(
        mode=data.get("mode"),
        ok=data.get("ok"),
        autopilot=data["checks"]["autopilot"]["ok"],
        corpus=data["checks"]["corpus"]["ok"],
        runtime=data["checks"]["runtime_canaries"]["ok"],
        flx4="skip" if not data["checks"]["flx4"]["ran"] else data["checks"]["flx4"]["ok"],
        first_pass=data["checks"]["autopilot"].get("first_pass_clean"),
        reprompt_debt=data["checks"]["autopilot"].get("reprompt_debt", 0),
        audio_evidence_debt=data["checks"]["autopilot"].get("audio_evidence_debt", 0),
        direct_midi=(
            data["checks"]["flx4"].get("direct_midi_probe", {}).get("motion_observed")
            if data["checks"]["flx4"]["ran"]
            and isinstance(data["checks"]["flx4"].get("direct_midi_probe"), dict)
            else "skip"
        ),
        midi_motion_diag=(
            data["checks"]["flx4"].get("midi_motion_diagnosis")
            if data["checks"]["flx4"]["ran"]
            else "skip"
        )
        or "none",
        flx4_missing=(
            ",".join(data["checks"]["flx4"].get("proof_missing_legs") or [])
            if data["checks"]["flx4"]["ran"]
            else "skip"
        )
        or "none",
        next_action=(
            data.get("next_operator_action", {}).get("code")
            if isinstance(data.get("next_operator_action"), dict)
            else "unknown"
        ),
        recommended_command=(
            data.get("next_operator_action", {}).get("recommended_command")
            if isinstance(data.get("next_operator_action"), dict)
            else None
        )
        or "none",
        actions=len(data.get("operator_action_queue") or []),
        runbook=data.get("operator_runbook_sh") or "none",
        out_dir=data.get("out_dir"),
    )
)
PY
)"

MATRIX_OK="$("${PY_CMD[@]}" - "${SUMMARY_JSON}" <<'PY'
import json
import sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print("1" if data.get("ok") else "0")
PY
)"

if [ "${MATRIX_OK}" = "1" ]; then
  emit_pass "${MATRIX_LINE}"
  exit 0
fi

emit_err "${MATRIX_LINE}"
echo "autopilot: ${AUTOPILOT_LINE}" >&2
echo "corpus: ${CORPUS_LINE}" >&2
echo "runtime_canaries: ${RUNTIME_LINE}" >&2
echo "flx4: ${FLX4_LINE}" >&2
exit 1
