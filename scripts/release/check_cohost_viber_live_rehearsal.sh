#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
#
# Start-or-use-live cohost/Viber rehearsal gate.
#
# This wrapper is for the physical preflight: launch the Vibemix live sidecar
# when needed, wait for ws://127.0.0.1:8765, run the release matrix, and cleanly
# stop the sidecar it started. It preserves the matrix artifacts and the live
# process logs under one directory.
#
# Env:
#   COHOST_VIBER_REHEARSAL_OUT_DIR       default: .planning/eval-runs/cohost-viber-live-rehearsal
#   COHOST_VIBER_REHEARSAL_START_LIVE    auto|required|never (default: auto)
#   COHOST_VIBER_REHEARSAL_KEEP_LIVE     1 to leave a sidecar started by this script running
#   COHOST_VIBER_REHEARSAL_WAIT_SOCKET_S default: 20
#   COHOST_VIBER_REHEARSAL_PROOF_WINDOW_S default: 20; time to play audio + move a control
#   COHOST_VIBER_REHEARSAL_PROOF_TIMEOUT_S per proof sample timeout (default: 2.0)
#   COHOST_VIBER_REHEARSAL_PROOF_FRAMES   max frames per proof sample (default: 120)
#   COHOST_VIBER_REHEARSAL_PROOF_ATTEMPTS default: 1; retry physical proof while live stays up
#   COHOST_VIBER_REHEARSAL_PROOF_RETRY_SLEEP_S default: 2
#   COHOST_VIBER_REHEARSAL_DIRECT_MIDI_PROBE_S default: 3; OS-level MIDI motion probe per attempt
#   COHOST_VIBER_REHEARSAL_DIRECT_MIDI_PROBE_MODE poll|callback (default: callback)
#   COHOST_VIBER_REHEARSAL_MATRIX_MODE   automation|release|first-pass|audio-evidence (default: first-pass)
#   COHOST_VIBER_REHEARSAL_FLX4          auto|required|skip (default: required)
#   COHOST_VIBER_REHEARSAL_WRAPPER_DIR   override release-wrapper dir for tests
#   COHOST_VIBER_REHEARSAL_LIVE_CMD      override live command (shell string)
#   COHOST_VIBER_REHEARSAL_DEV_SIDECAR   child VIBEMIX_DEV_SIDECAR (default: 1)
#   COHOST_VIBER_REHEARSAL_CITATION_LINT child VIBEMIX_CITATION_LINT (default: on)
#   COHOST_VIBER_REHEARSAL_REQUIRE_ACTIVITY 1 to require current cohost+Viber rows (default: 1)
#   COHOST_VIBER_REHEARSAL_STIMULATE     1 to drive cohost+Viber before checks (default: 1)
#   COHOST_VIBER_REHEARSAL_TRIGGER_COHOST send ws manual trigger (default: STIMULATE)
#   COHOST_VIBER_REHEARSAL_TRIGGER_WAIT_S wait for live ai_message after trigger (default: 25)
#   COHOST_VIBER_REHEARSAL_VIBER_GUARD_CHAT run no-context Viber guard chat (default: STIMULATE)
#   COHOST_VIBER_REHEARSAL_VIBER_MESSAGE guard-chat prompt (default: active live-deck question)
#   COHOST_VIBER_REHEARSAL_SOCKET_PORT   test seam; default: 8765
#   COHOST_VIBER_REHEARSAL_SOCKET_PROTOCOL websocket|tcp (default: websocket; tcp for tests)
#   PYTHON                               Python executable; defaults to .venv, uv, then python3

set -euo pipefail

OUT_DIR="${COHOST_VIBER_REHEARSAL_OUT_DIR:-.planning/eval-runs/cohost-viber-live-rehearsal}"
START_LIVE="${COHOST_VIBER_REHEARSAL_START_LIVE:-auto}"
KEEP_LIVE="${COHOST_VIBER_REHEARSAL_KEEP_LIVE:-0}"
WAIT_SOCKET_S="${COHOST_VIBER_REHEARSAL_WAIT_SOCKET_S:-20}"
PROOF_WINDOW_S="${COHOST_VIBER_REHEARSAL_PROOF_WINDOW_S:-20}"
PROOF_TIMEOUT_S="${COHOST_VIBER_REHEARSAL_PROOF_TIMEOUT_S:-2.0}"
PROOF_FRAMES="${COHOST_VIBER_REHEARSAL_PROOF_FRAMES:-120}"
PROOF_ATTEMPTS="${COHOST_VIBER_REHEARSAL_PROOF_ATTEMPTS:-1}"
PROOF_RETRY_SLEEP_S="${COHOST_VIBER_REHEARSAL_PROOF_RETRY_SLEEP_S:-2}"
DIRECT_MIDI_PROBE_S="${COHOST_VIBER_REHEARSAL_DIRECT_MIDI_PROBE_S:-3}"
DIRECT_MIDI_PROBE_MODE="${COHOST_VIBER_REHEARSAL_DIRECT_MIDI_PROBE_MODE:-callback}"
MATRIX_MODE="${COHOST_VIBER_REHEARSAL_MATRIX_MODE:-first-pass}"
MATRIX_FLX4="${COHOST_VIBER_REHEARSAL_FLX4:-required}"
WRAPPER_DIR="${COHOST_VIBER_REHEARSAL_WRAPPER_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
DEV_SIDECAR="${COHOST_VIBER_REHEARSAL_DEV_SIDECAR:-${VIBEMIX_DEV_SIDECAR:-1}}"
CITATION_LINT="${COHOST_VIBER_REHEARSAL_CITATION_LINT:-${VIBEMIX_CITATION_LINT:-on}}"
REQUIRE_ACTIVITY="${COHOST_VIBER_REHEARSAL_REQUIRE_ACTIVITY:-1}"
STIMULATE="${COHOST_VIBER_REHEARSAL_STIMULATE:-1}"
TRIGGER_COHOST="${COHOST_VIBER_REHEARSAL_TRIGGER_COHOST:-${STIMULATE}}"
TRIGGER_WAIT_S="${COHOST_VIBER_REHEARSAL_TRIGGER_WAIT_S:-25}"
VIBER_GUARD_CHAT="${COHOST_VIBER_REHEARSAL_VIBER_GUARD_CHAT:-${STIMULATE}}"
VIBER_MESSAGE="${COHOST_VIBER_REHEARSAL_VIBER_MESSAGE:-What am I doing on the live deck right now?}"
SOCKET_PORT="${COHOST_VIBER_REHEARSAL_SOCKET_PORT:-8765}"
SOCKET_PROTOCOL="${COHOST_VIBER_REHEARSAL_SOCKET_PROTOCOL:-websocket}"
GHA_ANNOT="${GITHUB_ACTIONS:-false}"
REHEARSAL_STARTED_AT_ISO="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

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

LIVE_PID=""
STARTED_LIVE="false"

emit_err() {
  local msg="$1"
  if [ "${GHA_ANNOT}" = "true" ]; then
    echo "::error::check_cohost_viber_live_rehearsal: ${msg}" >&2
  else
    echo "FAIL check_cohost_viber_live_rehearsal: ${msg}" >&2
  fi
}

emit_pass() {
  echo "PASS check_cohost_viber_live_rehearsal: $*"
}

enabled() {
  case "${1:-}" in
    ""|0|false|False|FALSE|no|No|NO|off|Off|OFF) return 1 ;;
    *) return 0 ;;
  esac
}

cleanup() {
  if [ "${STARTED_LIVE}" = "true" ] && [ "${KEEP_LIVE}" != "1" ] && [ -n "${LIVE_PID}" ]; then
    if kill -0 "${LIVE_PID}" >/dev/null 2>&1; then
      kill "${LIVE_PID}" >/dev/null 2>&1 || true
      for _ in 1 2 3 4 5; do
        if ! kill -0 "${LIVE_PID}" >/dev/null 2>&1; then
          break
        fi
        sleep 1
      done
      if kill -0 "${LIVE_PID}" >/dev/null 2>&1; then
        kill -9 "${LIVE_PID}" >/dev/null 2>&1 || true
      fi
      wait "${LIVE_PID}" >/dev/null 2>&1 || true
    fi
  fi
}
trap cleanup EXIT INT TERM

if ! command -v "${PY_CMD[0]}" >/dev/null 2>&1; then
  emit_err "${PY_CMD[0]} is required but not found on PATH"
  exit 1
fi

case "${START_LIVE}" in
  auto|required|never) ;;
  *)
    emit_err "COHOST_VIBER_REHEARSAL_START_LIVE must be auto, required, or never, got ${START_LIVE}"
    exit 2
    ;;
esac
case "${PROOF_ATTEMPTS}" in
  ""|*[!0-9]*)
    emit_err "COHOST_VIBER_REHEARSAL_PROOF_ATTEMPTS must be a positive integer, got ${PROOF_ATTEMPTS}"
    exit 2
    ;;
esac
if [ "${PROOF_ATTEMPTS}" -lt 1 ]; then
  emit_err "COHOST_VIBER_REHEARSAL_PROOF_ATTEMPTS must be at least 1, got ${PROOF_ATTEMPTS}"
  exit 2
fi
case "${DIRECT_MIDI_PROBE_MODE}" in
  poll|callback) ;;
  *)
    emit_err "COHOST_VIBER_REHEARSAL_DIRECT_MIDI_PROBE_MODE must be poll or callback, got ${DIRECT_MIDI_PROBE_MODE}"
    exit 2
    ;;
esac
case "${MATRIX_MODE}" in
  automation|release|first-pass|audio-evidence) ;;
  *)
    emit_err "COHOST_VIBER_REHEARSAL_MATRIX_MODE must be automation, release, first-pass, or audio-evidence, got ${MATRIX_MODE}"
    exit 2
    ;;
esac

mkdir -p "${OUT_DIR}"

socket_ready() {
  "${PY_CMD[@]}" - "${SOCKET_PORT}" "${SOCKET_PROTOCOL}" <<'PY' >/dev/null 2>&1
import asyncio
import socket
import sys

port = int(sys.argv[1])
protocol = sys.argv[2]
if protocol == "tcp":
    with socket.create_connection(("127.0.0.1", port), timeout=0.35):
        pass
else:
    import websockets

    async def main() -> None:
        async with websockets.connect(f"ws://127.0.0.1:{port}", open_timeout=0.75):
            pass

    asyncio.run(main())
PY
}

wait_socket() {
  local wait_s="$1"
  "${PY_CMD[@]}" - "${wait_s}" "${SOCKET_PORT}" "${SOCKET_PROTOCOL}" <<'PY' >/dev/null
import asyncio
import socket
import sys
import time

deadline = time.monotonic() + float(sys.argv[1])
port = int(sys.argv[2])
protocol = sys.argv[3]
while time.monotonic() <= deadline:
    try:
        if protocol == "tcp":
            with socket.create_connection(("127.0.0.1", port), timeout=0.35):
                raise SystemExit(0)
        else:
            import websockets

            async def main() -> None:
                async with websockets.connect(f"ws://127.0.0.1:{port}", open_timeout=0.75):
                    pass

            asyncio.run(main())
            raise SystemExit(0)
    except Exception:
        time.sleep(0.5)
raise SystemExit(1)
PY
}

started_session_dir() {
  local stdout_path="$1"
  if [ ! -f "${stdout_path}" ]; then
    return 0
  fi
  "${PY_CMD[@]}" - "${stdout_path}" <<'PY' 2>/dev/null || true
import re
import sys
from pathlib import Path

try:
    from vibemix.runtime.config_store import app_data_dir
except Exception:
    raise SystemExit(0)

try:
    text = Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace")
except OSError:
    raise SystemExit(0)

matches = list(re.finditer(r"recording session ->\s*([^/\s]+)/", text))
if not matches:
    raise SystemExit(0)
print(app_data_dir() / "recordings" / matches[-1].group(1))
PY
}

LIVE_STATE="existing"
if socket_ready; then
  LIVE_STATE="existing"
else
  if [ "${START_LIVE}" = "never" ]; then
    emit_err "live socket missing and COHOST_VIBER_REHEARSAL_START_LIVE=never"
    exit 1
  fi
  LIVE_STATE="started"
  LIVE_STDOUT="${OUT_DIR}/live_stdout.log"
  LIVE_STDERR="${OUT_DIR}/live_stderr.log"
  if [ -n "${COHOST_VIBER_REHEARSAL_LIVE_CMD:-}" ]; then
    env \
      VIBEMIX_DEV_SIDECAR="${DEV_SIDECAR}" \
      VIBEMIX_CITATION_LINT="${CITATION_LINT}" \
      bash -c "${COHOST_VIBER_REHEARSAL_LIVE_CMD}" >"${LIVE_STDOUT}" 2>"${LIVE_STDERR}" &
  else
    env \
      VIBEMIX_DEV_SIDECAR="${DEV_SIDECAR}" \
      VIBEMIX_CITATION_LINT="${CITATION_LINT}" \
      "${PY_CMD[@]}" -m vibemix >"${LIVE_STDOUT}" 2>"${LIVE_STDERR}" &
  fi
  LIVE_PID="$!"
  STARTED_LIVE="true"
  echo "${LIVE_PID}" >"${OUT_DIR}/live.pid"
  if ! wait_socket "${WAIT_SOCKET_S}"; then
    if ! kill -0 "${LIVE_PID}" >/dev/null 2>&1; then
      emit_err "live sidecar exited before socket became ready; see ${LIVE_STDERR}"
    else
      emit_err "live socket did not become ready within ${WAIT_SOCKET_S}s; see ${LIVE_STDERR}"
    fi
    exit 1
  fi
fi

REHEARSAL_SESSION_DIR="${COHOST_VIBER_SESSION_DIR:-}"
if [ -z "${REHEARSAL_SESSION_DIR}" ] && [ "${STARTED_LIVE}" = "true" ]; then
  REHEARSAL_SESSION_DIR="$(started_session_dir "${OUT_DIR}/live_stdout.log")"
fi
REHEARSAL_CORPUS_SESSION_DIR="${COHOST_VIBER_CORPUS_SESSION_DIR:-${REHEARSAL_SESSION_DIR}}"
REHEARSAL_GLOBAL_SINCE_ISO="${COHOST_VIBER_GLOBAL_SINCE_ISO:-${REHEARSAL_STARTED_AT_ISO}}"

STIMULUS_DIR="${OUT_DIR}/stimulus"
mkdir -p "${STIMULUS_DIR}"
COHOST_TRIGGER_JSON="${STIMULUS_DIR}/cohost_trigger.json"
VIBER_GUARD_JSON="${STIMULUS_DIR}/viber_guard_chat.json"
if enabled "${TRIGGER_COHOST}"; then
  "${PY_CMD[@]}" - \
    "${SOCKET_PORT}" \
    "${SOCKET_PROTOCOL}" \
    "${REHEARSAL_SESSION_DIR}" \
    "${REHEARSAL_GLOBAL_SINCE_ISO}" \
    "${TRIGGER_WAIT_S}" \
    "${COHOST_TRIGGER_JSON}" <<'PY'
import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path

port = int(sys.argv[1])
protocol = sys.argv[2]
session_dir = sys.argv[3]
since_iso = sys.argv[4]
wait_s = float(sys.argv[5])
out_path = Path(sys.argv[6])


def parse_iso(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


since_dt = parse_iso(since_iso)


def recent_live_coach_rows() -> list[dict]:
    if not session_dir:
        return []
    events_path = Path(session_dir) / "events.jsonl"
    if not events_path.exists():
        return []
    rows: list[dict] = []
    try:
        for line in events_path.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if row.get("kind") != "ai_message" or row.get("engine") != "live_coach":
                continue
            row_dt = parse_iso(str(row.get("ts_iso") or ""))
            if since_dt is not None and (row_dt is None or row_dt < since_dt):
                continue
            rows.append(row)
    except OSError:
        return []
    return rows


async def send_trigger() -> tuple[bool, str | None]:
    if protocol != "websocket":
        return False, f"skipped_for_socket_protocol:{protocol}"
    try:
        import websockets

        async with websockets.connect(f"ws://127.0.0.1:{port}", open_timeout=2.0) as ws:
            await ws.send(json.dumps({"action": "trigger"}))
        return True, None
    except Exception as exc:
        return False, f"{exc.__class__.__name__}: {exc}"


sent, error = asyncio.run(send_trigger())
deadline = time.monotonic() + max(0.0, wait_s)
observed = recent_live_coach_rows()
while sent and not observed and time.monotonic() < deadline:
    time.sleep(0.5)
    observed = recent_live_coach_rows()

payload = {
    "enabled": True,
    "sent": sent,
    "ok": sent and bool(observed),
    "reason": (
        "observed_live_coach_ai_message"
        if sent and observed
        else error
        if error
        else "no_live_coach_ai_message_observed"
    ),
    "wait_s": wait_s,
    "socket_protocol": protocol,
    "session_dir": session_dir or None,
    "global_since_iso": since_iso or None,
    "observed_live_coach_messages": len(observed),
}
out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
PY
else
  "${PY_CMD[@]}" - "${COHOST_TRIGGER_JSON}" <<'PY'
import json
import sys
from pathlib import Path

Path(sys.argv[1]).write_text(
    json.dumps({"enabled": False, "sent": False, "ok": True, "reason": "disabled"}, indent=2)
    + "\n",
    encoding="utf-8",
)
PY
fi

if enabled "${VIBER_GUARD_CHAT}"; then
  VIBER_GUARD_STDOUT="${STIMULUS_DIR}/viber_guard_chat_stdout.json"
  VIBER_GUARD_STDERR="${STIMULUS_DIR}/viber_guard_chat_stderr.log"
  set +e
  "${PY_CMD[@]}" -m vibemix library chat "${VIBER_MESSAGE}" --json \
    >"${VIBER_GUARD_STDOUT}" 2>"${VIBER_GUARD_STDERR}"
  VIBER_GUARD_RC=$?
  set -e
  "${PY_CMD[@]}" - \
    "${VIBER_GUARD_JSON}" \
    "${VIBER_GUARD_RC}" \
    "${VIBER_GUARD_STDOUT}" \
    "${VIBER_GUARD_STDERR}" \
    "${VIBER_MESSAGE}" <<'PY'
import json
import sys
from pathlib import Path

out_path = Path(sys.argv[1])
rc = int(sys.argv[2])
stdout_path = Path(sys.argv[3])
stderr_path = Path(sys.argv[4])
message = sys.argv[5]
payload = None
try:
    payload = json.loads(stdout_path.read_text(encoding="utf-8"))
except (OSError, json.JSONDecodeError):
    payload = None
stop_reason = payload.get("stop_reason") if isinstance(payload, dict) else None
reply = payload.get("reply") if isinstance(payload, dict) else None
stderr_tail = ""
try:
    stderr_tail = "\n".join(stderr_path.read_text(encoding="utf-8").splitlines()[-5:])
except OSError:
    stderr_tail = ""
out = {
    "enabled": True,
    "ok": rc == 0 and stop_reason == "live_context_required",
    "rc": rc,
    "message": message,
    "stop_reason": stop_reason,
    "reply": reply,
    "stdout_json": str(stdout_path),
    "stderr_log": str(stderr_path),
    "stderr_tail": stderr_tail,
}
out_path.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
PY
else
  "${PY_CMD[@]}" - "${VIBER_GUARD_JSON}" <<'PY'
import json
import sys
from pathlib import Path

Path(sys.argv[1]).write_text(
    json.dumps({"enabled": False, "ok": True, "reason": "disabled"}, indent=2) + "\n",
    encoding="utf-8",
)
PY
fi

ATTEMPTS_JSONL="${OUT_DIR}/matrix_attempts.jsonl"
: >"${ATTEMPTS_JSONL}"
MATRIX_RC=1
MATRIX_OUT_DIR=""
MATRIX_STDOUT=""
MATRIX_STDERR=""
MATRIX_SUMMARY=""
ATTEMPT=1
while [ "${ATTEMPT}" -le "${PROOF_ATTEMPTS}" ]; do
  if [ "${PROOF_ATTEMPTS}" -eq 1 ]; then
    MATRIX_OUT_DIR="${OUT_DIR}/matrix"
    MATRIX_STDOUT="${OUT_DIR}/matrix_stdout.log"
    MATRIX_STDERR="${OUT_DIR}/matrix_stderr.log"
  else
    ATTEMPT_PADDED="$(printf "%02d" "${ATTEMPT}")"
    MATRIX_OUT_DIR="${OUT_DIR}/matrix-attempt-${ATTEMPT_PADDED}"
    MATRIX_STDOUT="${OUT_DIR}/matrix_attempt_${ATTEMPT_PADDED}_stdout.log"
    MATRIX_STDERR="${OUT_DIR}/matrix_attempt_${ATTEMPT_PADDED}_stderr.log"
  fi
  if [ "${MATRIX_FLX4}" != "skip" ]; then
    echo "ACTION check_cohost_viber_live_rehearsal: attempt ${ATTEMPT}/${PROOF_ATTEMPTS}; for the next ${PROOF_WINDOW_S}s, play audible deck audio and move a FLX4 fader/knob so Viber gets physical proof."
    if [ "${DIRECT_MIDI_PROBE_S}" != "0" ] && [ "${DIRECT_MIDI_PROBE_S}" != "0.0" ]; then
      echo "ACTION check_cohost_viber_live_rehearsal: attempt ${ATTEMPT}/${PROOF_ATTEMPTS}; this will also run a ${DIRECT_MIDI_PROBE_S}s direct OS-level MIDI probe."
    fi
  fi
  set +e
  COHOST_VIBER_MATRIX_OUT_DIR="${MATRIX_OUT_DIR}" \
  COHOST_VIBER_MATRIX_MODE="${MATRIX_MODE}" \
  COHOST_VIBER_MATRIX_FLX4="${MATRIX_FLX4}" \
  COHOST_VIBER_SESSION_DIR="${REHEARSAL_SESSION_DIR}" \
  COHOST_VIBER_CORPUS_SESSION_DIR="${REHEARSAL_CORPUS_SESSION_DIR}" \
  COHOST_VIBER_GLOBAL_SINCE_ISO="${REHEARSAL_GLOBAL_SINCE_ISO}" \
  COHOST_VIBER_FLX4_WAIT_READY_S="${PROOF_WINDOW_S}" \
  COHOST_VIBER_FLX4_TIMEOUT_S="${PROOF_TIMEOUT_S}" \
  COHOST_VIBER_FLX4_FRAMES="${PROOF_FRAMES}" \
  COHOST_VIBER_FLX4_DIRECT_MIDI_PROBE_S="${DIRECT_MIDI_PROBE_S}" \
  COHOST_VIBER_FLX4_DIRECT_MIDI_PROBE_MODE="${DIRECT_MIDI_PROBE_MODE}" \
  COHOST_VIBER_REHEARSAL_ATTEMPT="${ATTEMPT}" \
    bash "${WRAPPER_DIR}/check_cohost_viber_matrix.sh" >"${MATRIX_STDOUT}" 2>"${MATRIX_STDERR}"
  MATRIX_RC=$?
  set -e

  MATRIX_SUMMARY="${MATRIX_OUT_DIR}/matrix_summary.json"
  if [ ! -f "${MATRIX_SUMMARY}" ]; then
    break
  fi

  RETRY_PHYSICAL="$(
    "${PY_CMD[@]}" - "${ATTEMPT}" "${MATRIX_RC}" "${MATRIX_OUT_DIR}" "${MATRIX_SUMMARY}" "${ATTEMPTS_JSONL}" <<'PY'
import json
import sys
from pathlib import Path

attempt = int(sys.argv[1])
rc = int(sys.argv[2])
out_dir = sys.argv[3]
summary_path = Path(sys.argv[4])
attempts_path = Path(sys.argv[5])
matrix = json.loads(summary_path.read_text(encoding="utf-8"))
checks = matrix.get("checks") if isinstance(matrix.get("checks"), dict) else {}
flx4 = checks.get("flx4") if isinstance(checks.get("flx4"), dict) else {}
autopilot = checks.get("autopilot") if isinstance(checks.get("autopilot"), dict) else {}
corpus = checks.get("corpus") if isinstance(checks.get("corpus"), dict) else {}


def _check_failed(check: dict) -> bool:
    return bool(check.get("required")) and not bool(check.get("ok"))


def _physical_action() -> dict:
    actions = flx4.get("operator_actions")
    if isinstance(actions, list) and actions:
        first = actions[0] if isinstance(actions[0], dict) else {}
        return {
            "code": str(first.get("code") or flx4.get("action_hint") or "fix_physical_proof"),
            "source": "physical",
            "detail": str(first.get("detail") or flx4.get("first_blocker") or "Fix FLX4 live proof."),
        }
    return {
        "code": str(flx4.get("action_hint") or "fix_physical_proof"),
        "source": "physical",
        "detail": str(flx4.get("first_blocker") or "Fix FLX4 live proof."),
    }


matrix_next = matrix.get("next_operator_action")
if not isinstance(matrix_next, dict):
    matrix_next = {"code": "inspect_matrix", "source": "matrix", "detail": "Inspect matrix artifacts."}
blocking_model_eval = _check_failed(autopilot) or _check_failed(corpus)
physical_missing = (
    bool(flx4.get("ran"))
    and bool(flx4.get("required"))
    and not bool(flx4.get("ok"))
    and not blocking_model_eval
)
next_action = _physical_action() if physical_missing else matrix_next
retryable = rc != 0 and physical_missing
flx4_checks = flx4.get("checks") if isinstance(flx4.get("checks"), dict) else {}
flx4_actions = flx4.get("operator_actions") if isinstance(flx4.get("operator_actions"), list) else []
flx4_top_blockers = flx4.get("top_blockers") if isinstance(flx4.get("top_blockers"), list) else []
flx4_proof_legs = flx4.get("proof_legs") if isinstance(flx4.get("proof_legs"), list) else []
flx4_setup_hint = flx4.get("setup_hint") if isinstance(flx4.get("setup_hint"), dict) else {}
direct_midi_probe = (
    flx4.get("direct_midi_probe") if isinstance(flx4.get("direct_midi_probe"), dict) else {}
)
missing_proof_legs = [
    str(leg.get("id"))
    for leg in flx4_proof_legs
    if isinstance(leg, dict) and str(leg.get("status") or "") != "pass" and leg.get("id")
]
record = {
    "attempt": attempt,
    "rc": rc,
    "out_dir": out_dir,
    "summary_json": str(summary_path),
    "ok": bool(matrix.get("ok")),
    "retryable_physical_proof": retryable,
    "next_action": next_action,
    "matrix_next_action": matrix_next,
    "flx4_diagnosis": flx4.get("diagnosis"),
    "flx4_action_hint": flx4.get("action_hint"),
    "flx4_first_blocker": flx4.get("first_blocker"),
    "flx4_top_blockers": flx4_top_blockers,
    "flx4_operator_actions": flx4_actions,
    "flx4_setup_hint": flx4_setup_hint,
    "flx4_checks": flx4_checks,
    "matrix_mode": matrix.get("mode"),
    "autopilot_first_pass_clean": autopilot.get("first_pass_clean"),
    "autopilot_reprompt_debt": autopilot.get("reprompt_debt"),
    "autopilot_audio_evidence_debt": autopilot.get("audio_evidence_debt"),
    "proof_legs_passed": flx4.get("proof_legs_passed"),
    "proof_legs_total": flx4.get("proof_legs_total"),
    "proof_missing_legs": missing_proof_legs,
    "direct_midi_sampling": direct_midi_probe.get("sampling"),
    "direct_midi_motion_observed": direct_midi_probe.get("motion_observed"),
    "direct_midi_frames": direct_midi_probe.get("frames"),
    "midi_motion_diagnosis": flx4.get("midi_motion_diagnosis"),
}
with attempts_path.open("a", encoding="utf-8") as handle:
    handle.write(json.dumps(record, sort_keys=True) + "\n")
print("1" if retryable else "0")
PY
  )"

  if [ "${MATRIX_RC}" -eq 0 ]; then
    break
  fi
  if [ "${ATTEMPT}" -ge "${PROOF_ATTEMPTS}" ]; then
    break
  fi
  if [ "${RETRY_PHYSICAL}" != "1" ]; then
    break
  fi
  echo "ACTION check_cohost_viber_live_rehearsal: physical proof still missing; keeping live sidecar up and retrying in ${PROOF_RETRY_SLEEP_S}s."
  sleep "${PROOF_RETRY_SLEEP_S}"
  ATTEMPT=$((ATTEMPT + 1))
done

SUMMARY_JSON="${OUT_DIR}/live_rehearsal_summary.json"
if [ ! -f "${MATRIX_SUMMARY}" ]; then
  if [ -s "${MATRIX_STDERR}" ]; then
    cat "${MATRIX_STDERR}" >&2
  fi
  emit_err "matrix did not write summary: ${MATRIX_SUMMARY}"
  if [ "${MATRIX_RC}" -ne 0 ]; then
    exit "${MATRIX_RC}"
  fi
  exit 1
fi

REHEARSAL_LINE=$(
  REHEARSAL_LIVE_STATE="${LIVE_STATE}" \
  REHEARSAL_STARTED_LIVE="${STARTED_LIVE}" \
  REHEARSAL_KEEP_LIVE="${KEEP_LIVE}" \
  REHEARSAL_LIVE_PID="${LIVE_PID}" \
  REHEARSAL_DEV_SIDECAR="${DEV_SIDECAR}" \
  REHEARSAL_CITATION_LINT="${CITATION_LINT}" \
  REHEARSAL_SESSION_DIR="${REHEARSAL_SESSION_DIR}" \
  REHEARSAL_CORPUS_SESSION_DIR="${REHEARSAL_CORPUS_SESSION_DIR}" \
  REHEARSAL_GLOBAL_SINCE_ISO="${REHEARSAL_GLOBAL_SINCE_ISO}" \
  REHEARSAL_REQUIRE_ACTIVITY="${REQUIRE_ACTIVITY}" \
  REHEARSAL_MATRIX_MODE="${MATRIX_MODE}" \
  REHEARSAL_COHOST_TRIGGER_JSON="${COHOST_TRIGGER_JSON}" \
  REHEARSAL_VIBER_GUARD_JSON="${VIBER_GUARD_JSON}" \
  REHEARSAL_OUT_DIR="${OUT_DIR}" \
  REHEARSAL_PROOF_WINDOW_S="${PROOF_WINDOW_S}" \
  REHEARSAL_PROOF_TIMEOUT_S="${PROOF_TIMEOUT_S}" \
  REHEARSAL_PROOF_FRAMES="${PROOF_FRAMES}" \
  REHEARSAL_PROOF_ATTEMPTS="${PROOF_ATTEMPTS}" \
  REHEARSAL_DIRECT_MIDI_PROBE_S="${DIRECT_MIDI_PROBE_S}" \
  REHEARSAL_DIRECT_MIDI_PROBE_MODE="${DIRECT_MIDI_PROBE_MODE}" \
  REHEARSAL_ATTEMPTS_JSONL="${ATTEMPTS_JSONL}" \
    "${PY_CMD[@]}" - "${SUMMARY_JSON}" "${MATRIX_SUMMARY}" <<'PY'
import json
import os
import shlex
import sys
from pathlib import Path

matrix = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
require_activity = os.environ["REHEARSAL_REQUIRE_ACTIVITY"] not in {"0", "false", "False", ""}
autopilot = matrix.get("checks", {}).get("autopilot", {})
report_path = None
session_ai_messages = 0
live_coach_messages = 0
viber_rows = 0
viber_errored_rows = 0
activity_error = None
try:
    autopilot_out = autopilot.get("out_dir") if isinstance(autopilot, dict) else None
    if autopilot_out:
        report_path = str(Path(str(autopilot_out)) / "report.json")
        report = json.loads(Path(report_path).read_text(encoding="utf-8"))
        metrics = report.get("metrics") if isinstance(report.get("metrics"), dict) else {}
        session_metrics = metrics.get("session") if isinstance(metrics.get("session"), dict) else {}
        viber_metrics = metrics.get("viber") if isinstance(metrics.get("viber"), dict) else {}
        session_ai_messages = int(session_metrics.get("ai_messages") or 0)
        live_coach_raw = session_metrics.get("live_coach_messages")
        live_coach_messages = (
            int(live_coach_raw)
            if live_coach_raw is not None
            else session_ai_messages
        )
        viber_rows = int(viber_metrics.get("rows_inspected") or 0)
        viber_errored_rows = int(viber_metrics.get("errored_rows") or 0)
except Exception as exc:
    activity_error = f"{exc.__class__.__name__}: {exc}"
activity_ok = (not require_activity) or (
    live_coach_messages > 0
    and viber_rows > 0
    and viber_errored_rows == 0
    and activity_error is None
)
activity_reason = None
if require_activity and activity_error is not None:
    activity_reason = "activity_report_unreadable"
elif require_activity and live_coach_messages <= 0 and viber_rows <= 0:
    activity_reason = "no_current_live_coach_or_viber_activity"
elif require_activity and live_coach_messages <= 0:
    activity_reason = "no_current_live_coach_activity"
elif require_activity and viber_rows <= 0:
    activity_reason = "no_current_viber_activity"
elif require_activity and viber_errored_rows > 0:
    activity_reason = "current_viber_activity_errored"
elif not require_activity:
    activity_reason = "activity_requirement_disabled"
rehearsal_ok = bool(matrix.get("ok")) and activity_ok
def _read_json(path: str | None) -> dict:
    if not path:
        return {}
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception as exc:
        return {"enabled": None, "ok": False, "reason": f"unreadable:{exc.__class__.__name__}"}

stimulus = {
    "cohost_trigger": _read_json(os.environ.get("REHEARSAL_COHOST_TRIGGER_JSON")),
    "viber_guard_chat": _read_json(os.environ.get("REHEARSAL_VIBER_GUARD_JSON")),
}


def _read_attempts(path: str | None) -> list[dict]:
    if not path:
        return []
    out: list[dict] = []
    try:
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if isinstance(row, dict):
                out.append(row)
    except OSError:
        return []
    return out


attempts = _read_attempts(os.environ.get("REHEARSAL_ATTEMPTS_JSONL"))
checks = matrix.get("checks") if isinstance(matrix.get("checks"), dict) else {}
flx4_check = checks.get("flx4") if isinstance(checks.get("flx4"), dict) else {}
physical = {
    "ran": bool(flx4_check.get("ran")),
    "required": bool(flx4_check.get("required")),
    "ok": bool(flx4_check.get("ok")),
    "diagnosis": flx4_check.get("diagnosis"),
    "action_hint": flx4_check.get("action_hint"),
    "first_blocker": flx4_check.get("first_blocker"),
    "top_blockers": flx4_check.get("top_blockers") if flx4_check.get("top_blockers") else [],
    "operator_actions": (
        flx4_check.get("operator_actions") if flx4_check.get("operator_actions") else []
    ),
    "setup_hint": (
        flx4_check.get("setup_hint") if isinstance(flx4_check.get("setup_hint"), dict) else {}
    ),
    "proof_legs": flx4_check.get("proof_legs") if flx4_check.get("proof_legs") else [],
    "proof_legs_passed": flx4_check.get("proof_legs_passed"),
    "proof_legs_total": flx4_check.get("proof_legs_total"),
    "checks": flx4_check.get("checks") if isinstance(flx4_check.get("checks"), dict) else {},
    "direct_midi_probe": (
        flx4_check.get("direct_midi_probe")
        if isinstance(flx4_check.get("direct_midi_probe"), dict)
        else {}
    ),
    "midi_motion_diagnosis": flx4_check.get("midi_motion_diagnosis"),
    "summary_json": flx4_check.get("summary_json"),
}
autopilot_check = checks.get("autopilot") if isinstance(checks.get("autopilot"), dict) else {}


def _physical_rehearsal_recommended_command() -> str:
    matrix_mode = os.environ["REHEARSAL_MATRIX_MODE"]
    return (
        "COHOST_VIBER_REHEARSAL_PROOF_ATTEMPTS=3 "
        f"COHOST_VIBER_REHEARSAL_MATRIX_MODE={matrix_mode} "
        "COHOST_VIBER_REHEARSAL_DIRECT_MIDI_PROBE_S=3 "
        "COHOST_VIBER_REHEARSAL_START_LIVE=required "
        "COHOST_VIBER_REHEARSAL_FLX4=required "
        "bash scripts/release/check_cohost_viber_live_rehearsal.sh"
    )


def _direct_midi_probe_command(*, mode: str, seconds: int = 10) -> str:
    return f"python scripts/sniff_controller.py --port DDJ-FLX4 --seconds {seconds} --mode {mode}"


def _audio_probe_commands() -> list[str]:
    return [
        (
            "python -m vibemix library live-context --wait-ready 10 --interval 1 "
            "--timeout 1 --frames 60 --json --out .planning/proofs/live-context-audio-proof.json"
        ),
        "system_profiler SPAudioDataType | grep -i 'BlackHole\\|DDJ-FLX4' -A 8",
    ]


def _live_context_proof_command(*, out_name: str) -> str:
    return (
        "python -m vibemix library live-context --require-proof --wait-ready 10 "
        f"--interval 1 --timeout 1 --frames 90 --json --out .planning/proofs/{out_name}"
    )


def _deck_identity_probe_commands() -> list[str]:
    return [
        _live_context_proof_command(out_name="live-context-deck-identity-proof.json"),
    ]


def _deck_capture_probe_commands() -> list[str]:
    return [
        _live_context_proof_command(out_name="live-context-deck-capture-proof.json"),
        "system_profiler SPAudioDataType | grep -i 'BlackHole 16ch\\|DDJ-FLX4' -A 8",
    ]


def _int_or_zero(value: object) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _truthy(value: object) -> bool:
    if isinstance(value, str):
        return value.strip().lower() not in {"", "0", "false", "none", "no", "off"}
    return bool(value)


def _stable_order(values: list[str]) -> list[str]:
    out: list[str] = []
    for value in values:
        if value and value not in out:
            out.append(value)
    return out


def _bool_trend(values: list[bool], *, positive: str = "seen", negative: str = "missing") -> str:
    if not values:
        return "unknown"
    if all(values):
        return f"stable_{positive}"
    if not any(values):
        return f"stable_{negative}"
    if not values[0] and values[-1]:
        return "improved"
    if values[0] and not values[-1]:
        return "regressed"
    return "mixed"


def _frame_trend(values: list[int]) -> str:
    if not values:
        return "unknown"
    if all(value == 0 for value in values):
        return "stable_zero"
    if all(value > 0 for value in values) and len(set(values)) == 1:
        return "stable_positive"
    if values[-1] > values[0]:
        return "improved"
    if values[-1] < values[0]:
        return "regressed"
    if all(value > 0 for value in values):
        return "stable_positive"
    return "mixed"


def _attempt_check(attempt: dict, name: str) -> bool:
    checks = attempt.get("flx4_checks") if isinstance(attempt.get("flx4_checks"), dict) else {}
    return _truthy(checks.get(name))


def _proof_progress_summary() -> dict:
    failed = [
        attempt
        for attempt in attempts
        if isinstance(attempt, dict) and attempt.get("retryable_physical_proof")
    ]
    progress = {
        "available": bool(attempts),
        "attempts": len(attempts),
        "retryable_physical_attempts": len(failed),
        "diagnosis": "not_enough_attempts",
        "summary": "Fewer than two retryable physical proof attempts were recorded.",
    }
    if not attempts:
        progress["diagnosis"] = "no_attempts_recorded"
        progress["summary"] = "No matrix attempts were recorded."
        return progress
    if len(failed) < 2:
        return progress

    direct_frames = [_int_or_zero(attempt.get("direct_midi_frames")) for attempt in failed]
    recent_values = [_attempt_check(attempt, "recent_moves_seen") for attempt in failed]
    audio_values = [_attempt_check(attempt, "audio_observed") for attempt in failed]
    deck_pair_values = [_attempt_check(attempt, "deck_state_pair_resolved") for attempt in failed]
    capture_values = [_attempt_check(attempt, "deck_pair_capture_configured") for attempt in failed]
    deck_audio_values = [_attempt_check(attempt, "deck_audio_capture_both_active") for attempt in failed]
    first_missing = _stable_order(
        [
            str(value)
            for value in failed[0].get("proof_missing_legs", [])
            if value
        ]
    )
    latest_missing = _stable_order(
        [
            str(value)
            for value in failed[-1].get("proof_missing_legs", [])
            if value
        ]
    )
    first_missing_set = set(first_missing)
    latest_missing_set = set(latest_missing)
    resolved_legs = [value for value in first_missing if value not in latest_missing_set]
    stable_missing_legs = [value for value in latest_missing if value in first_missing_set]
    new_missing_legs = [value for value in latest_missing if value not in first_missing_set]

    direct_midi_trend = _frame_trend(direct_frames)
    recent_moves_trend = _bool_trend(recent_values)
    audio_trend = _bool_trend(audio_values, positive="observed")
    deck_pair_trend = _bool_trend(deck_pair_values, positive="resolved")
    capture_trend = _bool_trend(capture_values, positive="configured")
    deck_audio_trend = _bool_trend(deck_audio_values, positive="active")

    if (
        direct_midi_trend == "stable_zero"
        and recent_moves_trend == "stable_missing"
    ):
        diagnosis = "stable_missing_no_direct_midi"
    elif (
        direct_midi_trend in {"stable_positive", "improved"}
        and recent_moves_trend == "stable_missing"
    ):
        diagnosis = "midi_listener_gap"
    elif (
        direct_midi_trend == "regressed"
        or recent_moves_trend == "regressed"
        or audio_trend == "regressed"
    ):
        diagnosis = "regressed"
    elif direct_frames[-1] > 0 and recent_values[-1] and audio_trend == "stable_missing":
        diagnosis = "audio_route_gap"
    elif not deck_pair_values[-1] and recent_values[-1] and audio_values[-1]:
        diagnosis = "deck_identity_or_capture_gap"
    elif resolved_legs or "improved" in {direct_midi_trend, recent_moves_trend, audio_trend}:
        diagnosis = "improving"
    elif stable_missing_legs:
        diagnosis = "stable_missing"
    else:
        diagnosis = "mixed"

    missing = ", ".join(latest_missing) if latest_missing else "none"
    frames = ",".join(str(value) for value in direct_frames) if direct_frames else "none"
    progress.update(
        {
            "diagnosis": diagnosis,
            "first_missing_legs": first_missing,
            "latest_missing_legs": latest_missing,
            "stable_missing_legs": stable_missing_legs,
            "resolved_legs": resolved_legs,
            "new_missing_legs": new_missing_legs,
            "direct_midi_frames": direct_frames,
            "direct_midi_trend": direct_midi_trend,
            "recent_moves_trend": recent_moves_trend,
            "audio_trend": audio_trend,
            "deck_pair_trend": deck_pair_trend,
            "deck_pair_capture_trend": capture_trend,
            "deck_audio_capture_trend": deck_audio_trend,
            "latest_direct_midi_frames": direct_frames[-1] if direct_frames else 0,
            "latest_recent_moves_seen": recent_values[-1] if recent_values else False,
            "latest_audio_observed": audio_values[-1] if audio_values else False,
            "summary": (
                f"{len(failed)} physical proof attempts: {diagnosis}; "
                f"missing={missing}; direct_midi_frames={frames}; "
                f"recent_moves={recent_moves_trend}; audio={audio_trend}."
            ),
        }
    )
    return progress


proof_progress = _proof_progress_summary()


def _repeated_physical_attempt_action() -> dict | None:
    failed = [
        attempt
        for attempt in attempts
        if isinstance(attempt, dict) and attempt.get("retryable_physical_proof")
    ]
    if len(failed) < 2:
        return None
    checks = [
        attempt.get("flx4_checks") if isinstance(attempt.get("flx4_checks"), dict) else {}
        for attempt in failed
    ]
    latest_check = checks[-1]

    direct_samples = [
        attempt
        for attempt in failed
        if attempt.get("direct_midi_sampling") == "concurrent_with_live_context"
    ]
    all_recent_missing = all(not check.get("recent_moves_seen") for check in checks)
    all_audio_missing = all(not check.get("audio_observed") for check in checks)
    direct_frames = [_int_or_zero(attempt.get("direct_midi_frames")) for attempt in failed]
    if direct_samples and len(direct_samples) == len(failed) and all_recent_missing:
        if all(frames == 0 for frames in direct_frames):
            return {
                "code": "prove_os_midi_motion",
                "source": "physical",
                "detail": (
                    f"Across {len(failed)} proof attempts, the concurrent direct OS MIDI "
                    "probe saw 0 FLX4 frames. Move a fader/knob during the proof window "
                    "or fix USB/MIDI input before trusting live controller moves."
                ),
                "diagnostic_commands": [
                    _direct_midi_probe_command(mode="callback"),
                    _direct_midi_probe_command(mode="poll"),
                ],
                "recommended_command": _physical_rehearsal_recommended_command(),
            }
        if all(frames > 0 for frames in direct_frames):
            return {
                "code": "restart_live_midi_listener",
                "source": "physical",
                "detail": (
                    f"Across {len(failed)} proof attempts, direct OS MIDI saw FLX4 "
                    "frames but live-context still saw no recent moves. Restart the "
                    "live session and inspect MIDI listener binding if it repeats."
                ),
                "diagnostic_commands": [
                    _direct_midi_probe_command(
                        mode=str(os.environ["REHEARSAL_DIRECT_MIDI_PROBE_MODE"] or "callback")
                    )
                ],
                "recommended_command": _physical_rehearsal_recommended_command(),
            }
    if proof_progress.get("diagnosis") == "regressed":
        return {
            "code": "stabilize_physical_proof",
            "source": "physical",
            "detail": (
                f"{proof_progress['summary']} Repeat the proof while moving the FLX4 and "
                "playing audible deck audio in the same window before diagnosing audio or MIDI plumbing."
            ),
            "diagnostic_commands": [
                _direct_midi_probe_command(mode="callback"),
                _direct_midi_probe_command(mode="poll"),
            ],
            "recommended_command": _physical_rehearsal_recommended_command(),
        }
    if (
        all_audio_missing
        and _int_or_zero(failed[-1].get("direct_midi_frames")) > 0
        and checks[-1].get("recent_moves_seen")
    ):
        return {
            "code": "play_audible_audio",
            "source": "physical",
            "detail": (
                f"Across {len(failed)} proof attempts, controller motion was visible "
                "but live audio stayed below the floor. Play audible DJ app output "
                "into the configured capture route during the proof window."
            ),
            "diagnostic_commands": _audio_probe_commands(),
            "recommended_command": _physical_rehearsal_recommended_command(),
        }
    if latest_check.get("recent_moves_seen") and latest_check.get("audio_observed"):
        if not latest_check.get("deck_state_pair_resolved"):
            return {
                "code": "resolve_deck_identity",
                "source": "physical",
                "detail": (
                    f"{proof_progress['summary']} Controller motion and master audio are visible, "
                    "but Deck A/B identity is still not resolved enough to cite. Load identifiable "
                    "tracks on both decks and make the active deck posture obvious before rerunning."
                ),
                "diagnostic_commands": _deck_identity_probe_commands(),
                "recommended_command": _physical_rehearsal_recommended_command(),
            }
        if not latest_check.get("deck_pair_capture_configured"):
            latest_hint = failed[-1].get("flx4_setup_hint")
            if not isinstance(latest_hint, dict):
                latest_hint = {}
            return {
                "code": "configure_deck_pair_capture",
                "source": "physical",
                "detail": (
                    f"{proof_progress['summary']} Deck identity, controller motion, and master "
                    "audio are visible, but per-deck audio capture is not configured. Start the "
                    "live session with deck-pair capture enabled so Viber can hear Deck A and Deck B "
                    "as separate evidence lanes."
                ),
                "diagnostic_commands": _deck_capture_probe_commands(),
                "recommended_env": latest_hint.get("recommended_env") or {
                    "VIBEMIX_DECK_AUDIO_CHANNELS": "auto"
                },
                "setup_hint": latest_hint or None,
                "recommended_command": _physical_rehearsal_recommended_command(),
            }
        if not latest_check.get("deck_audio_capture_both_active"):
            return {
                "code": "feed_both_deck_lanes",
                "source": "physical",
                "detail": (
                    f"{proof_progress['summary']} Per-deck capture is configured, but it has not "
                    "seen active audio on both deck lanes. For a BlackHole 16ch/Rekordbox rig, "
                    "route Deck 1 to BlackHole channels 1/2 and Deck 2 to channels 3/4, or update "
                    "VIBEMIX_DECK_AUDIO_CHANNELS to the actual A/B channel map. Rerun until the "
                    "proof shows deck_audio_capture=A_active+B_active."
                ),
                "diagnostic_commands": _deck_capture_probe_commands(),
                "recommended_command": _physical_rehearsal_recommended_command(),
            }
    return None


def _next_operator_action() -> dict:
    if not activity_ok:
        if activity_reason == "activity_report_unreadable":
            return {
                "code": "inspect_activity_report",
                "source": "activity",
                "detail": "Open the autopilot report artifact; rehearsal could not read current cohost/Viber activity.",
                "recommended_command": "bash scripts/release/check_cohost_viber_live_rehearsal.sh",
            }
        if activity_reason == "no_current_live_coach_or_viber_activity":
            return {
                "code": "stimulate_cohost_and_viber",
                "source": "activity",
                "detail": "Trigger the cohost and run the safe Viber guard chat, then rerun the rehearsal.",
                "recommended_command": (
                    "COHOST_VIBER_REHEARSAL_STIMULATE=1 "
                    "bash scripts/release/check_cohost_viber_live_rehearsal.sh"
                ),
            }
        if activity_reason == "no_current_live_coach_activity":
            return {
                "code": "trigger_cohost",
                "source": "activity",
                "detail": "Trigger the live cohost and wait for a current live_coach ai_message before rerunning.",
                "recommended_command": (
                    "COHOST_VIBER_REHEARSAL_TRIGGER_COHOST=1 "
                    "bash scripts/release/check_cohost_viber_live_rehearsal.sh"
                ),
            }
        if activity_reason == "no_current_viber_activity":
            return {
                "code": "run_viber_guard_chat",
                "source": "activity",
                "detail": "Run the safe Viber guard chat so the rehearsal has a current Viber row.",
                "recommended_command": (
                    "COHOST_VIBER_REHEARSAL_VIBER_GUARD_CHAT=1 "
                    "bash scripts/release/check_cohost_viber_live_rehearsal.sh"
                ),
            }
        if activity_reason == "current_viber_activity_errored":
            return {
                "code": "fix_viber_backend_error",
                "source": "activity",
                "detail": "Inspect the current Viber row error before trusting the rehearsal result.",
                "recommended_command": "bash scripts/release/check_cohost_viber_live_rehearsal.sh",
            }
        return {
            "code": str(activity_reason or "fix_activity"),
            "source": "activity",
            "detail": "Fix the current cohost/Viber activity gate, then rerun the rehearsal.",
            "recommended_command": "bash scripts/release/check_cohost_viber_live_rehearsal.sh",
        }
    matrix_next = matrix.get("next_operator_action")
    if not bool(matrix.get("ok")) and isinstance(matrix_next, dict):
        matrix_next_source = str(matrix_next.get("source") or "")
        if matrix_next_source in {"autopilot", "corpus", "runtime_canaries"}:
            action = dict(matrix_next)
            action["code"] = str(action.get("code") or f"inspect_{matrix_next_source}")
            action["source"] = matrix_next_source
            action["detail"] = str(action.get("detail") or "Inspect release matrix artifacts.")
            action["recommended_command"] = str(
                action.get("recommended_command")
                or "bash scripts/release/check_cohost_viber_matrix.sh"
            )
            return action
    if physical["ran"] and physical["required"] and not physical["ok"]:
        repeated_action = _repeated_physical_attempt_action()
        if repeated_action:
            return repeated_action
        if isinstance(matrix_next, dict) and str(matrix_next.get("source") or "") in {
            "flx4",
            "physical",
        }:
            action = dict(matrix_next)
            action["code"] = str(action.get("code") or physical.get("action_hint") or "fix_physical_proof")
            action["detail"] = str(
                action.get("detail")
                or physical.get("first_blocker")
                or "Fix FLX4 live proof."
            )
            action["recommended_command"] = str(
                action.get("recommended_command")
                or _physical_rehearsal_recommended_command()
            )
            return action
        actions = physical.get("operator_actions")
        if isinstance(actions, list) and actions:
            first = actions[0] if isinstance(actions[0], dict) else {}
            return {
                "code": str(first.get("code") or physical.get("action_hint") or "fix_physical_proof"),
                "source": "physical",
                "detail": str(first.get("detail") or physical.get("first_blocker") or "Fix FLX4 live proof."),
                "recommended_command": _physical_rehearsal_recommended_command(),
            }
        return {
            "code": str(physical.get("action_hint") or "fix_physical_proof"),
            "source": "physical",
            "detail": str(physical.get("first_blocker") or "Fix FLX4 live proof."),
            "recommended_command": _physical_rehearsal_recommended_command(),
        }
    if not bool(matrix.get("ok")):
        for check_name in ("autopilot", "corpus", "runtime_canaries", "flx4"):
            check = checks.get(check_name) if isinstance(checks.get(check_name), dict) else {}
            if check.get("required") and not check.get("ok"):
                return {
                    "code": f"inspect_{check_name}",
                    "source": "matrix",
                    "detail": str(check.get("summary") or f"Inspect {check_name} artifacts."),
                    "recommended_command": "bash scripts/release/check_cohost_viber_matrix.sh",
                }
        return {
            "code": "inspect_matrix",
            "source": "matrix",
            "detail": "Inspect release matrix artifacts for the failing check.",
            "recommended_command": "bash scripts/release/check_cohost_viber_matrix.sh",
        }
    return {
        "code": "ready",
        "source": "rehearsal",
        "detail": "Cohost/Viber rehearsal gates are ready for the captured evidence.",
    }


next_operator_action = _next_operator_action()


def _action_key(action: dict) -> str:
    return str(action.get("code") or "")


def _append_action(queue: list[dict], seen: set[str], action: object) -> None:
    if not isinstance(action, dict):
        return
    code = str(action.get("code") or "")
    if not code:
        return
    item = dict(action)
    key = _action_key(item)
    if key in seen:
        return
    seen.add(key)
    queue.append(item)


def _operator_action_queue() -> list[dict]:
    queue: list[dict] = []
    seen: set[str] = set()
    _append_action(queue, seen, next_operator_action)
    matrix_queue = matrix.get("operator_action_queue")
    if isinstance(matrix_queue, list):
        for action in matrix_queue:
            _append_action(queue, seen, action)
    if physical["ran"] and physical["required"] and not physical["ok"]:
        actions = physical.get("operator_actions")
        if isinstance(actions, list):
            for action in actions:
                if not isinstance(action, dict):
                    continue
                physical_action = dict(action)
                physical_action.setdefault("source", "physical")
                physical_action.setdefault(
                    "recommended_command",
                    _physical_rehearsal_recommended_command(),
                )
                _append_action(queue, seen, physical_action)
    return queue


operator_action_queue = _operator_action_queue()


def _write_operator_action_artifacts(actions: list[dict]) -> tuple[str, str]:
    out_path = Path(os.environ["REHEARSAL_OUT_DIR"])
    out_path.mkdir(parents=True, exist_ok=True)
    actions_path = out_path / "operator_actions.json"
    runbook_path = out_path / "operator_action_runbook.sh"
    actions_payload = {
        "schema": "cohost_viber_operator_actions_v1",
        "source": "live_rehearsal",
        "summary_json": str(Path(sys.argv[1])),
        "matrix_summary": str(Path(sys.argv[2])),
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
        'echo "cohost/Viber operator action runbook (live rehearsal)"',
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


operator_actions_json, operator_runbook_sh = _write_operator_action_artifacts(
    operator_action_queue
)
summary = {
    "schema": "cohost_viber_live_rehearsal_v1",
    "ok": rehearsal_ok,
    "live_state": os.environ["REHEARSAL_LIVE_STATE"],
    "started_live": os.environ["REHEARSAL_STARTED_LIVE"] == "true",
    "kept_live": os.environ["REHEARSAL_KEEP_LIVE"] == "1",
    "live_pid": os.environ["REHEARSAL_LIVE_PID"] or None,
    "live_env_applied": os.environ["REHEARSAL_STARTED_LIVE"] == "true",
    "requested_dev_sidecar": os.environ["REHEARSAL_DEV_SIDECAR"],
    "requested_citation_lint": os.environ["REHEARSAL_CITATION_LINT"],
    "rehearsal_session_dir": os.environ["REHEARSAL_SESSION_DIR"] or None,
    "corpus_session_dir": os.environ["REHEARSAL_CORPUS_SESSION_DIR"] or None,
    "global_since_iso": os.environ["REHEARSAL_GLOBAL_SINCE_ISO"] or None,
    "matrix_mode": os.environ["REHEARSAL_MATRIX_MODE"],
    "first_pass_clean": autopilot_check.get("first_pass_clean"),
    "reprompt_debt": autopilot_check.get("reprompt_debt"),
    "audio_evidence_debt": autopilot_check.get("audio_evidence_debt", 0),
    "activity": {
        "required": require_activity,
        "ok": activity_ok,
        "cohost_ai_messages": session_ai_messages,
        "live_coach_messages": live_coach_messages,
        "viber_rows": viber_rows,
        "viber_errored_rows": viber_errored_rows,
        "report_json": report_path,
        "error": activity_error,
        "reason": activity_reason,
    },
    "physical": physical,
    "next_operator_action": next_operator_action,
    "operator_action_queue": operator_action_queue,
    "operator_actions_json": operator_actions_json,
    "operator_runbook_sh": operator_runbook_sh,
    "stimulus": stimulus,
    "out_dir": os.environ["REHEARSAL_OUT_DIR"],
    "proof_window_s": os.environ["REHEARSAL_PROOF_WINDOW_S"],
    "proof_timeout_s": os.environ["REHEARSAL_PROOF_TIMEOUT_S"],
    "proof_frames": os.environ["REHEARSAL_PROOF_FRAMES"],
    "direct_midi_probe_s": os.environ["REHEARSAL_DIRECT_MIDI_PROBE_S"],
    "direct_midi_probe_mode": os.environ["REHEARSAL_DIRECT_MIDI_PROBE_MODE"],
    "proof_attempts_requested": int(os.environ["REHEARSAL_PROOF_ATTEMPTS"]),
    "attempts_jsonl": os.environ.get("REHEARSAL_ATTEMPTS_JSONL"),
    "attempt_count": len(attempts),
    "final_attempt": attempts[-1]["attempt"] if attempts else None,
    "attempts": attempts,
    "proof_progress": proof_progress,
    "matrix_summary": str(Path(sys.argv[2])),
    "matrix": matrix,
}
Path(sys.argv[1]).write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
print(
    "live_state={live_state} started_live={started_live} matrix_ok={matrix_ok} "
    "live_env_applied={live_env_applied} dev_sidecar={dev_sidecar} "
    "citation_lint={citation_lint} "
    "session_pinned={session_pinned} global_since={global_since} "
    "activity={activity} cohost_ai={cohost_ai} live_coach={live_coach} "
    "viber_rows={viber_rows} viber_errors={viber_errors} "
    "proof_attempts={attempt_count}/{proof_attempts_requested} "
    "matrix_mode={matrix_mode} autopilot={autopilot} corpus={corpus} "
    "first_pass={first_pass} reprompt_debt={reprompt_debt} "
    "audio_evidence_debt={audio_evidence_debt} flx4={flx4} "
    "flx4_diag={flx4_diag} direct_midi={direct_midi} "
    "midi_motion_diag={midi_motion_diag} proof_progress={proof_progress} "
    "proof_missing={proof_missing} proof_frames={proof_frames} action_hint={action_hint} "
    "next_action={next_action} actions={actions} "
    "recommended_command={recommended_command} runbook={runbook} out_dir={out_dir}".format(
        live_state=summary["live_state"],
        started_live=summary["started_live"],
        matrix_ok=matrix.get("ok"),
        live_env_applied=summary["live_env_applied"],
        dev_sidecar=summary["requested_dev_sidecar"],
        citation_lint=summary["requested_citation_lint"],
        session_pinned=bool(summary["rehearsal_session_dir"]),
        global_since=summary["global_since_iso"],
        activity=summary["activity"]["ok"],
        cohost_ai=summary["activity"]["cohost_ai_messages"],
        live_coach=summary["activity"]["live_coach_messages"],
        viber_rows=summary["activity"]["viber_rows"],
        viber_errors=summary["activity"]["viber_errored_rows"],
        attempt_count=summary["attempt_count"],
        proof_attempts_requested=summary["proof_attempts_requested"],
        matrix_mode=summary["matrix_mode"],
        autopilot=matrix["checks"]["autopilot"]["ok"],
        corpus=matrix["checks"]["corpus"]["ok"],
        first_pass=summary["first_pass_clean"],
        reprompt_debt=summary["reprompt_debt"],
        audio_evidence_debt=summary["audio_evidence_debt"],
        flx4="skip" if not matrix["checks"]["flx4"]["ran"] else matrix["checks"]["flx4"]["ok"],
        flx4_diag=physical["diagnosis"] or "none",
        direct_midi=(
            physical["direct_midi_probe"].get("motion_observed")
            if isinstance(physical.get("direct_midi_probe"), dict)
            and physical["direct_midi_probe"].get("ran")
            else "skip"
        ),
        midi_motion_diag=physical.get("midi_motion_diagnosis") or "none",
        proof_progress=proof_progress.get("diagnosis") or "none",
        proof_missing=(
            ",".join(proof_progress.get("latest_missing_legs") or [])
            or "none"
        ),
        proof_frames=(
            ",".join(str(value) for value in proof_progress.get("direct_midi_frames") or [])
            or "none"
        ),
        action_hint=physical["action_hint"] or "none",
        next_action=next_operator_action["code"],
        actions=len(operator_action_queue),
        recommended_command=next_operator_action.get("recommended_command") or "none",
        runbook=summary["operator_runbook_sh"],
        out_dir=summary["out_dir"],
    )
)
PY
)

ACTIVITY_OK="$("${PY_CMD[@]}" - "${SUMMARY_JSON}" <<'PY'
import json
import sys
from pathlib import Path
data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print("1" if data.get("activity", {}).get("ok") else "0")
PY
)"

if [ "${MATRIX_RC}" -eq 0 ] && [ "${ACTIVITY_OK}" = "1" ]; then
  emit_pass "${REHEARSAL_LINE}"
  exit 0
fi

if [ -s "${MATRIX_STDERR}" ]; then
  tail -n 5 "${MATRIX_STDERR}" >&2
fi
emit_err "${REHEARSAL_LINE}"
if [ "${MATRIX_RC}" -eq 0 ]; then
  exit 1
fi
exit "${MATRIX_RC}"
