#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
#
# Release wrapper for the cohost/Viber failure-corpus benchmark.
#
# The wrapper always refreshes the corpus from current recordings before
# benchmarking it. Default policy is strict release gating: fail while the
# refreshed corpus still contains captured failures. Operator mode can use
# COHOST_VIBER_CORPUS_FAIL_ON=automation to pass when every repair candidate
# clears the benchmark, while still reporting release_ready=false.
#
# Env:
#   COHOST_VIBER_CORPUS_FAIL_ON   automation|release (default: release)
#   COHOST_VIBER_BACKEND          deterministic|codex (default: deterministic)
#   COHOST_VIBER_CORPUS_OUT_DIR   artifact dir (default: .planning/eval-runs/cohost-viber-corpus)
#   COHOST_VIBER_CORPUS_SESSION_DIR optional explicit recording session
#   COHOST_VIBER_RECORDINGS_ROOT  optional recordings root
#   COHOST_VIBER_GLOBAL_ROOT      optional app-data root for Viber rows
#   COHOST_VIBER_GLOBAL_SINCE_ISO only include Viber rows at/after this ISO timestamp
#   COHOST_VIBER_MAX_SESSIONS     default: 10
#   COHOST_VIBER_MAX_GLOBAL_ROWS  default: 25
#   COHOST_VIBER_NO_VIBER         1 to skip global Viber rows
#   COHOST_VIBER_NO_POLICY_CANARIES 1 to skip built-in policy canaries
#   COHOST_VIBER_REQUIRE_POLICY_CANARIES 0 to allow missing policy canaries (default: 1)
#   COHOST_VIBER_CODEX_PATH       optional Codex CLI override
#   COHOST_VIBER_TIMEOUT_S        optional Codex timeout
#   COHOST_VIBER_ALLOW_SHELL      1 to pass --allow-shell for Codex backend
#   PYTHON                        Python executable (default: python3)

set -euo pipefail

FAIL_ON="${COHOST_VIBER_CORPUS_FAIL_ON:-${COHOST_VIBER_FAIL_ON:-release}}"
BACKEND="${COHOST_VIBER_BACKEND:-deterministic}"
OUT_DIR="${COHOST_VIBER_CORPUS_OUT_DIR:-.planning/eval-runs/cohost-viber-corpus}"
MAX_SESSIONS="${COHOST_VIBER_MAX_SESSIONS:-10}"
MAX_GLOBAL_ROWS="${COHOST_VIBER_MAX_GLOBAL_ROWS:-25}"
REQUIRE_POLICY_CANARIES="${COHOST_VIBER_REQUIRE_POLICY_CANARIES:-1}"
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
    echo "::error::check_cohost_viber_corpus_benchmark: ${msg}" >&2
  else
    echo "FAIL check_cohost_viber_corpus_benchmark: ${msg}" >&2
  fi
}

emit_pass() {
  echo "PASS check_cohost_viber_corpus_benchmark: $*"
}

if ! command -v "${PY_CMD[0]}" >/dev/null 2>&1; then
  emit_err "${PY_CMD[0]} is required but not found on PATH"
  exit 1
fi

mkdir -p "${OUT_DIR}"

CORPUS_DIR="${OUT_DIR}/corpus"
BENCH_DIR="${OUT_DIR}/benchmark"
mkdir -p "${CORPUS_DIR}" "${BENCH_DIR}"

CORPUS_ARGS=(
  -m vibemix eval failure-corpus
  --out-dir "${CORPUS_DIR}"
  --max-sessions "${MAX_SESSIONS}"
  --max-global-rows "${MAX_GLOBAL_ROWS}"
  --json
)

if [ -n "${COHOST_VIBER_RECORDINGS_ROOT:-}" ]; then
  CORPUS_ARGS+=(--recordings-root "${COHOST_VIBER_RECORDINGS_ROOT}")
fi
if [ -n "${COHOST_VIBER_CORPUS_SESSION_DIR:-}" ]; then
  CORPUS_ARGS+=(--session-dir "${COHOST_VIBER_CORPUS_SESSION_DIR}")
fi
if [ -n "${COHOST_VIBER_GLOBAL_ROOT:-}" ]; then
  CORPUS_ARGS+=(--global-root "${COHOST_VIBER_GLOBAL_ROOT}")
fi
if [ -n "${COHOST_VIBER_GLOBAL_SINCE_ISO:-}" ]; then
  CORPUS_ARGS+=(--global-since-iso "${COHOST_VIBER_GLOBAL_SINCE_ISO}")
fi
if [ "${COHOST_VIBER_NO_VIBER:-0}" = "1" ]; then
  CORPUS_ARGS+=(--no-viber)
fi
if [ "${COHOST_VIBER_NO_POLICY_CANARIES:-0}" = "1" ]; then
  CORPUS_ARGS+=(--no-policy-canaries)
fi

CORPUS_STDOUT="${OUT_DIR}/failure_corpus_stdout.json"
CORPUS_STDERR="${OUT_DIR}/failure_corpus_stderr.log"
set +e
"${PY_CMD[@]}" "${CORPUS_ARGS[@]}" >"${CORPUS_STDOUT}" 2>"${CORPUS_STDERR}"
CORPUS_RC=$?
set -e

CORPUS_MANIFEST="${CORPUS_DIR}/manifest.json"
if [ ! -f "${CORPUS_MANIFEST}" ]; then
  if [ -s "${CORPUS_STDERR}" ]; then
    cat "${CORPUS_STDERR}" >&2
  fi
  emit_err "failure-corpus did not write manifest: ${CORPUS_MANIFEST}"
  if [ "${CORPUS_RC}" -ne 0 ]; then
    exit "${CORPUS_RC}"
  fi
  exit 1
fi
if [ "${CORPUS_RC}" -ne 0 ]; then
  if [ -s "${CORPUS_STDERR}" ]; then
    cat "${CORPUS_STDERR}" >&2
  fi
  emit_err "failure-corpus command failed rc=${CORPUS_RC}"
  exit "${CORPUS_RC}"
fi

BENCH_ARGS=(
  -m vibemix eval corpus-benchmark
  --corpus-dir "${CORPUS_DIR}"
  --out-dir "${BENCH_DIR}"
  --backend "${BACKEND}"
  --json
)

if [ -n "${COHOST_VIBER_CODEX_PATH:-}" ]; then
  BENCH_ARGS+=(--codex-path "${COHOST_VIBER_CODEX_PATH}")
fi
if [ -n "${COHOST_VIBER_TIMEOUT_S:-}" ]; then
  BENCH_ARGS+=(--timeout-s "${COHOST_VIBER_TIMEOUT_S}")
fi
if [ "${COHOST_VIBER_ALLOW_SHELL:-0}" = "1" ]; then
  BENCH_ARGS+=(--allow-shell)
fi

BENCH_STDOUT="${OUT_DIR}/benchmark_stdout.json"
BENCH_STDERR="${OUT_DIR}/benchmark_stderr.log"
set +e
"${PY_CMD[@]}" "${BENCH_ARGS[@]}" >"${BENCH_STDOUT}" 2>"${BENCH_STDERR}"
BENCH_RC=$?
set -e

BENCH_MANIFEST="${BENCH_DIR}/benchmark_manifest.json"
if [ ! -f "${BENCH_MANIFEST}" ]; then
  if [ -s "${BENCH_STDERR}" ]; then
    cat "${BENCH_STDERR}" >&2
  fi
  emit_err "corpus-benchmark did not write manifest: ${BENCH_MANIFEST}"
  if [ "${BENCH_RC}" -ne 0 ]; then
    exit "${BENCH_RC}"
  fi
  exit 1
fi

SUMMARY_LINE=$(
  "${PY_CMD[@]}" - "${CORPUS_MANIFEST}" "${BENCH_MANIFEST}" <<'PY'
import json
import sys
from pathlib import Path

corpus = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
bench = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
counts = corpus.get("issue_code_counts") or {}
print(
    "release_ready={release_ready} benchmark_ok={benchmark_ok} "
    "cases={cases} passed={passed} failed={failed} skipped={skipped} "
    "captured={captured} canaries={canaries} "
    "audio_listener={audio_listener} audio_causal={audio_causal} audio_source={audio_source} "
    "cohost_source={cohost_source} ack_loop={ack_loop} viber_leaks={viber_leaks} "
    "viber_live={viber_live} out_dir={out_dir}".format(
        release_ready=corpus.get("release_ready"),
        benchmark_ok=bench.get("ok"),
        cases=bench.get("case_count", corpus.get("case_count", 0)),
        passed=bench.get("passed", 0),
        failed=bench.get("failed", 0),
        skipped=bench.get("skipped", 0),
        captured=corpus.get("captured_case_count", 0),
        canaries=corpus.get("policy_canary_count", 0),
        audio_listener=counts.get("audio_vibe_listener_read_allowed", 0),
        audio_causal=counts.get("audio_vibe_control_causality", 0),
        audio_source=counts.get("audio_vibe_hidden_source_detail", 0),
        cohost_source=counts.get("cohost_audio_source_detail_emit", 0),
        ack_loop=counts.get("citation_zero_ack_loop", 0),
        viber_leaks=counts.get("viber_library_request_live_leak", 0),
        viber_live=counts.get("viber_live_verification", 0),
        out_dir=bench.get("out_dir"),
    )
)
PY
)

POLICY_CANARIES_OK=$(
  "${PY_CMD[@]}" - "${CORPUS_MANIFEST}" <<'PY'
import json
import sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
counts = data.get("issue_code_counts") or {}
required = {
    "audio_vibe_listener_read_allowed": 1,
    "audio_vibe_control_causality": 1,
    "audio_vibe_hidden_source_detail": 1,
    "cohost_audio_source_detail_emit": 1,
    "citation_zero_ack_loop": 1,
    "viber_library_request_live_leak": 1,
}
missing = [code for code, minimum in required.items() if int(counts.get(code) or 0) < minimum]
print("1" if not missing else ",".join(missing))
PY
)

if [ "${REQUIRE_POLICY_CANARIES}" != "0" ] && [ "${POLICY_CANARIES_OK}" != "1" ]; then
  emit_err "${SUMMARY_LINE} missing_policy_canaries=${POLICY_CANARIES_OK}"
  exit 1
fi

if [ "${BENCH_RC}" -ne 0 ]; then
  emit_err "${SUMMARY_LINE}"
  exit "${BENCH_RC}"
fi

RELEASE_READY=$(
  "${PY_CMD[@]}" - "${CORPUS_MANIFEST}" <<'PY'
import json
import sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print("1" if data.get("release_ready") else "0")
PY
)

if [ "${FAIL_ON}" = "release" ] && [ "${RELEASE_READY}" != "1" ]; then
  emit_err "${SUMMARY_LINE}"
  exit 1
fi

emit_pass "${SUMMARY_LINE}"
exit 0
