#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
#
# Physical FLX4 + Viber live-context proof gate.
#
# This is the hardware-in-the-loop companion to the corpus benchmark: it proves
# the controller is visible as MIDI, visible as an audio device, and that the
# running Vibemix socket can emit the grounded live-context packet Viber would
# receive. A plugged controller alone is not enough for release readiness.
#
# Env:
#   COHOST_VIBER_FLX4_OUT_DIR       artifact dir (default: .planning/eval-runs/flx4-live-context)
#   COHOST_VIBER_FLX4_WAIT_READY_S  live-context wait window (default: 0)
#   COHOST_VIBER_FLX4_TIMEOUT_S     per-attempt socket sample seconds (default: 2.0)
#   COHOST_VIBER_FLX4_FRAMES        max frames per attempt (default: 120)
#   COHOST_VIBER_FLX4_PORT_RE       MIDI/audio match text (default: DDJ-FLX4)
#   COHOST_VIBER_FLX4_GOOD_REPLY    listener-read canary expected to pass
#   COHOST_VIBER_FLX4_BAD_REPLY     legacy alias for BAD_CAUSAL_REPLY
#   COHOST_VIBER_FLX4_BAD_CAUSAL_REPLY audio-causality canary expected to fail
#   COHOST_VIBER_FLX4_BAD_SOURCE_REPLY hidden source-detail canary expected to fail
#   COHOST_VIBER_FLX4_DIRECT_MIDI_PROBE_S optional OS-level MIDI motion probe seconds (default: 0)
#   COHOST_VIBER_FLX4_DIRECT_MIDI_PROBE_MODE poll|callback (default: callback)
#   PYTHON                          Python executable; defaults to .venv, uv, then python3

set -euo pipefail

OUT_DIR="${COHOST_VIBER_FLX4_OUT_DIR:-.planning/eval-runs/flx4-live-context}"
WAIT_READY_S="${COHOST_VIBER_FLX4_WAIT_READY_S:-0}"
TIMEOUT_S="${COHOST_VIBER_FLX4_TIMEOUT_S:-2.0}"
FRAMES="${COHOST_VIBER_FLX4_FRAMES:-120}"
PORT_RE="${COHOST_VIBER_FLX4_PORT_RE:-DDJ-FLX4}"
GOOD_REPLY="${COHOST_VIBER_FLX4_GOOD_REPLY:-The low end got hollow for a moment.}"
BAD_CAUSAL_REPLY="${COHOST_VIBER_FLX4_BAD_CAUSAL_REPLY:-${COHOST_VIBER_FLX4_BAD_REPLY:-That EQ move fixed the low end.}}"
BAD_SOURCE_REPLY="${COHOST_VIBER_FLX4_BAD_SOURCE_REPLY:-The vocal opened up and the kick got tighter.}"
DIRECT_MIDI_PROBE_S="${COHOST_VIBER_FLX4_DIRECT_MIDI_PROBE_S:-0}"
DIRECT_MIDI_PROBE_MODE="${COHOST_VIBER_FLX4_DIRECT_MIDI_PROBE_MODE:-callback}"
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
    echo "::error::check_flx4_live_context: ${msg}" >&2
  else
    echo "FAIL check_flx4_live_context: ${msg}" >&2
  fi
}

emit_pass() {
  echo "PASS check_flx4_live_context: $*"
}

if ! command -v "${PY_CMD[0]}" >/dev/null 2>&1; then
  emit_err "${PY_CMD[0]} is required but not found on PATH"
  exit 1
fi
case "${DIRECT_MIDI_PROBE_MODE}" in
  poll|callback) ;;
  *)
    emit_err "COHOST_VIBER_FLX4_DIRECT_MIDI_PROBE_MODE must be poll or callback, got ${DIRECT_MIDI_PROBE_MODE}"
    exit 2
    ;;
esac

mkdir -p "${OUT_DIR}"
SUMMARY_JSON="${OUT_DIR}/flx4_live_context_summary.json"

write_early_summary() {
  local diagnosis="$1"
  local action_hint="$2"
  local first_blocker="$3"
  local operator_code="$4"
  local operator_detail="$5"
  local midi_ok="$6"
  local audio_ok="$7"
  local midi_stdout="${8:-}"
  local midi_stderr="${9:-}"
  local audio_report="${10:-}"
  local audio_stderr="${11:-}"
  "${PY_CMD[@]}" - \
    "${SUMMARY_JSON}" \
    "${diagnosis}" \
    "${action_hint}" \
    "${first_blocker}" \
    "${operator_code}" \
    "${operator_detail}" \
    "${midi_ok}" \
    "${audio_ok}" \
    "${midi_stdout}" \
    "${midi_stderr}" \
    "${audio_report}" \
    "${audio_stderr}" <<'PY'
import json
import sys
from pathlib import Path

out_path = Path(sys.argv[1])
diagnosis = sys.argv[2]
action_hint = sys.argv[3]
first_blocker = sys.argv[4]
operator_code = sys.argv[5]
operator_detail = sys.argv[6]
midi_ok_raw = sys.argv[7]
audio_ok_raw = sys.argv[8]
midi_stdout = sys.argv[9]
midi_stderr = sys.argv[10]
audio_report = sys.argv[11]
audio_stderr = sys.argv[12]


def tri_bool(value: str):
    if value == "true":
        return True
    if value == "false":
        return False
    return None


def first_line(path_raw: str) -> str | None:
    if not path_raw:
        return None
    try:
        for line in Path(path_raw).read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if line:
                return line
    except OSError:
        return None
    return None


operator_actions = []
if operator_code:
    operator_actions.append({"code": operator_code, "detail": operator_detail})
proof_legs = [
    {
        "id": "controller_midi",
        "status": "pass" if tri_bool(midi_ok_raw) is True else "missing",
        "detail": "DDJ-FLX4 appears in MIDI enumeration.",
    },
    {
        "id": "controller_audio_device",
        "status": "pass" if tri_bool(audio_ok_raw) is True else "missing",
        "detail": "DDJ-FLX4 appears as an audio device.",
    },
    {
        "id": "live_socket",
        "status": "missing",
        "detail": "No usable Vibemix live-context websocket proof was captured.",
    },
]
summary = {
    "schema": "flx4_live_context_summary_v1",
    "ok": False,
    "midi_port": first_line(midi_stdout),
    "audio_device_found": tri_bool(audio_ok_raw),
    "live_ok": False,
    "live_ready": False,
    "diagnosis": diagnosis,
    "action_hint": action_hint,
    "operator_actions": operator_actions,
    "first_blocker": first_blocker,
    "top_blockers": [first_blocker],
    "blocker_count": 1,
    "proof_legs": proof_legs,
    "next_action": operator_detail,
    "checks": {
        "controller_connected": tri_bool(midi_ok_raw),
        "deck_state_resolved": False,
        "deck_state_pair_resolved": False,
        "recent_moves_seen": False,
        "audio_observed": False,
        "deck_pair_capture_configured": False,
        "deck_audio_capture_both_active": False,
    },
    "canaries": {
        "listener_read": "skipped",
        "audio_causality_rejected": "skipped",
        "audio_source_detail_rejected": "skipped",
    },
    "setup_hint": None,
    "artifacts": {
        "midi_ports": midi_stdout or None,
        "midi_stderr": midi_stderr or None,
        "audio_devices": audio_report or None,
        "audio_stderr": audio_stderr or None,
        "proof_json": None,
    },
}
out_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
PY
}

MIDI_STDOUT="${OUT_DIR}/midi_ports.txt"
MIDI_STDERR="${OUT_DIR}/midi_ports.stderr.log"
set +e
"${PY_CMD[@]}" scripts/sniff_controller.py --list >"${MIDI_STDOUT}" 2>"${MIDI_STDERR}"
MIDI_RC=$?
set -e

if [ "${MIDI_RC}" -ne 0 ]; then
  write_early_summary \
    "midi_enumeration_failed" \
    "fix_midi_enumeration_then_connect_ddj_flx4" \
    "MIDI enumeration failed rc=${MIDI_RC}" \
    "fix_midi_enumeration" \
    "Fix MIDI enumeration, connect DDJ-FLX4 over USB, then rerun the FLX4 live-context proof." \
    "false" \
    "unknown" \
    "${MIDI_STDOUT}" \
    "${MIDI_STDERR}"
  if [ -s "${MIDI_STDERR}" ]; then
    cat "${MIDI_STDERR}" >&2
  fi
  emit_err "MIDI enumeration failed rc=${MIDI_RC}"
  exit "${MIDI_RC}"
fi
if ! grep -qi "${PORT_RE}" "${MIDI_STDOUT}"; then
  write_early_summary \
    "midi_port_missing" \
    "connect_ddj_flx4_and_start_live_session" \
    "MIDI port matching ${PORT_RE} was not found" \
    "connect_flx4" \
    "Connect DDJ-FLX4 over USB and confirm it appears in MIDI enumeration, then rerun the proof." \
    "false" \
    "unknown" \
    "${MIDI_STDOUT}" \
    "${MIDI_STDERR}"
  emit_err "MIDI port matching ${PORT_RE} was not found"
  exit 1
fi

AUDIO_REPORT="${OUT_DIR}/audio_devices.txt"
if command -v system_profiler >/dev/null 2>&1; then
  system_profiler SPAudioDataType >"${AUDIO_REPORT}" 2>"${OUT_DIR}/audio_devices.stderr.log" || true
else
  : >"${AUDIO_REPORT}"
fi
if ! grep -qi "${PORT_RE}" "${AUDIO_REPORT}"; then
  write_early_summary \
    "audio_device_missing" \
    "connect_or_select_flx4_audio_device" \
    "Audio device matching ${PORT_RE} was not found" \
    "connect_flx4_audio" \
    "Confirm DDJ-FLX4 appears as an audio device or choose the capture route that carries the DJ app output, then rerun the proof." \
    "true" \
    "false" \
    "${MIDI_STDOUT}" \
    "${MIDI_STDERR}" \
    "${AUDIO_REPORT}" \
    "${OUT_DIR}/audio_devices.stderr.log"
  emit_err "Audio device matching ${PORT_RE} was not found"
  exit 1
fi

LIVE_JSON="${OUT_DIR}/live_context_stdout.json"
LIVE_ERR="${OUT_DIR}/live_context_stderr.log"
PROOF_JSON="${OUT_DIR}/live_context_proof.json"
LIVE_ARGS=(
  -m vibemix library live-context
  --timeout "${TIMEOUT_S}"
  --frames "${FRAMES}"
  --require-proof
  --out "${PROOF_JSON}"
  --json
)
if [ "${WAIT_READY_S}" != "0" ] && [ "${WAIT_READY_S}" != "0.0" ]; then
  LIVE_ARGS+=(--wait-ready "${WAIT_READY_S}")
fi

DIRECT_MIDI_JSONL="${OUT_DIR}/direct_midi_probe.jsonl"
DIRECT_MIDI_ERR="${OUT_DIR}/direct_midi_probe.stderr.log"
DIRECT_MIDI_RC=0
DIRECT_MIDI_PID=""
if [ "${DIRECT_MIDI_PROBE_S}" != "0" ] && [ "${DIRECT_MIDI_PROBE_S}" != "0.0" ]; then
  echo "ACTION check_flx4_live_context: for the next ${DIRECT_MIDI_PROBE_S}s, play deck audio and move a FLX4 fader/knob; live-context and direct OS MIDI proof are sampling together."
  set +e
  "${PY_CMD[@]}" scripts/sniff_controller.py \
    --port "${PORT_RE}" \
    --seconds "${DIRECT_MIDI_PROBE_S}" \
    --mode "${DIRECT_MIDI_PROBE_MODE}" \
    >"${DIRECT_MIDI_JSONL}" 2>"${DIRECT_MIDI_ERR}" &
  DIRECT_MIDI_PID="$!"
  set -e
else
  : >"${DIRECT_MIDI_JSONL}"
  : >"${DIRECT_MIDI_ERR}"
fi

set +e
"${PY_CMD[@]}" "${LIVE_ARGS[@]}" >"${LIVE_JSON}" 2>"${LIVE_ERR}"
LIVE_RC=$?
set -e
if [ -n "${DIRECT_MIDI_PID}" ]; then
  set +e
  wait "${DIRECT_MIDI_PID}"
  DIRECT_MIDI_RC=$?
  set -e
fi

if [ ! -f "${PROOF_JSON}" ]; then
  if [ -s "${LIVE_ERR}" ]; then
    cat "${LIVE_ERR}" >&2
  fi
  emit_err "live-context did not write proof: ${PROOF_JSON}"
  if [ "${LIVE_RC}" -ne 0 ]; then
    exit "${LIVE_RC}"
  fi
  exit 1
fi

GOOD_VERIFY_JSON="${OUT_DIR}/listener_read_verification.json"
GOOD_VERIFY_ERR="${OUT_DIR}/listener_read_verification.stderr.log"
BAD_CAUSAL_VERIFY_JSON="${OUT_DIR}/audio_causality_rejection.json"
BAD_CAUSAL_VERIFY_ERR="${OUT_DIR}/audio_causality_rejection.stderr.log"
BAD_SOURCE_VERIFY_JSON="${OUT_DIR}/audio_source_detail_rejection.json"
BAD_SOURCE_VERIFY_ERR="${OUT_DIR}/audio_source_detail_rejection.stderr.log"
GOOD_VERIFY_RC=99
BAD_CAUSAL_VERIFY_RC=99
BAD_SOURCE_VERIFY_RC=99
BAD_CAUSAL_REJECTED="false"
BAD_SOURCE_REJECTED="false"
if [ "${LIVE_RC}" -eq 0 ]; then
  set +e
  "${PY_CMD[@]}" -m vibemix library verify-live-reply \
    --live-context-file "${PROOF_JSON}" \
    --reply "${GOOD_REPLY}" \
    --json >"${GOOD_VERIFY_JSON}" 2>"${GOOD_VERIFY_ERR}"
  GOOD_VERIFY_RC=$?
  "${PY_CMD[@]}" -m vibemix library verify-live-reply \
    --live-context-file "${PROOF_JSON}" \
    --reply "${BAD_CAUSAL_REPLY}" \
    --json >"${BAD_CAUSAL_VERIFY_JSON}" 2>"${BAD_CAUSAL_VERIFY_ERR}"
  BAD_CAUSAL_VERIFY_RC=$?
  "${PY_CMD[@]}" -m vibemix library verify-live-reply \
    --live-context-file "${PROOF_JSON}" \
    --reply "${BAD_SOURCE_REPLY}" \
    --json >"${BAD_SOURCE_VERIFY_JSON}" 2>"${BAD_SOURCE_VERIFY_ERR}"
  BAD_SOURCE_VERIFY_RC=$?
  set -e
  if [ "${BAD_CAUSAL_VERIFY_RC}" -ne 0 ] && grep -q "unsupported_live_outcome_claim" "${BAD_CAUSAL_VERIFY_JSON}" 2>/dev/null; then
    BAD_CAUSAL_REJECTED="true"
  fi
  if [ "${BAD_SOURCE_VERIFY_RC}" -ne 0 ] && grep -q "unsupported_audio_source_detail_claim" "${BAD_SOURCE_VERIFY_JSON}" 2>/dev/null; then
    BAD_SOURCE_REJECTED="true"
  fi
fi
REPLY_CANARIES_OK="false"
if [ "${LIVE_RC}" -eq 0 ] && [ "${GOOD_VERIFY_RC}" -eq 0 ] && [ "${BAD_CAUSAL_REJECTED}" = "true" ] && [ "${BAD_SOURCE_REJECTED}" = "true" ]; then
  REPLY_CANARIES_OK="true"
fi

SUMMARY_LINE=$(
  LIVE_RC="${LIVE_RC}" \
  GOOD_VERIFY_RC="${GOOD_VERIFY_RC}" \
  BAD_CAUSAL_REJECTED="${BAD_CAUSAL_REJECTED}" \
  BAD_SOURCE_REJECTED="${BAD_SOURCE_REJECTED}" \
  REPLY_CANARIES_OK="${REPLY_CANARIES_OK}" \
  GOOD_VERIFY_JSON="${GOOD_VERIFY_JSON}" \
  BAD_CAUSAL_VERIFY_JSON="${BAD_CAUSAL_VERIFY_JSON}" \
  BAD_SOURCE_VERIFY_JSON="${BAD_SOURCE_VERIFY_JSON}" \
  DIRECT_MIDI_PROBE_S="${DIRECT_MIDI_PROBE_S}" \
  DIRECT_MIDI_PROBE_MODE="${DIRECT_MIDI_PROBE_MODE}" \
  DIRECT_MIDI_JSONL="${DIRECT_MIDI_JSONL}" \
  DIRECT_MIDI_ERR="${DIRECT_MIDI_ERR}" \
  DIRECT_MIDI_RC="${DIRECT_MIDI_RC}" \
    "${PY_CMD[@]}" - "${PROOF_JSON}" "${MIDI_STDOUT}" "${SUMMARY_JSON}" <<'PY'
import json
import os
import sys
from pathlib import Path

proof = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
midi_ports = [line.strip() for line in Path(sys.argv[2]).read_text(encoding="utf-8").splitlines() if line.strip()]
summary_path = Path(sys.argv[3])
readiness = proof.get("readiness") if isinstance(proof.get("readiness"), dict) else {}
blockers = readiness.get("blockers") if isinstance(readiness.get("blockers"), list) else []
checks = readiness.get("checks") if isinstance(readiness.get("checks"), dict) else {}
raw_first_blocker = str(blockers[0]) if blockers else "none"
next_action = str(readiness.get("next_action") or "none")
diagnosis = str(readiness.get("diagnosis") or "")
direct_midi_probe_s = str(os.environ.get("DIRECT_MIDI_PROBE_S") or "0")
direct_midi_ran = direct_midi_probe_s not in {"", "0", "0.0"}
direct_midi_rc = int(os.environ["DIRECT_MIDI_RC"])


def _read_direct_midi_probe(path_raw: str, *, ran: bool, rc: int) -> dict:
    summary: dict | None = None
    frames: list[dict] = []
    path = Path(path_raw)
    if path.exists():
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(row, dict):
                continue
            if row.get("summary") is True:
                summary = row
            else:
                frames.append(row)
    frame_count = int((summary or {}).get("frames") or len(frames))
    return {
        "ran": ran,
        "ok": (not ran) or rc == 0,
        "rc": rc if ran else None,
        "seconds": direct_midi_probe_s if ran else None,
        "mode": os.environ.get("DIRECT_MIDI_PROBE_MODE") if ran else None,
        "sampling": "concurrent_with_live_context" if ran else "disabled",
        "motion_observed": bool(ran and rc == 0 and frame_count > 0),
        "frames": frame_count,
        "unique_cc": list((summary or {}).get("unique_cc") or []),
        "unique_notes": list((summary or {}).get("unique_notes") or []),
        "jsonl": str(path) if ran else None,
        "stderr": os.environ.get("DIRECT_MIDI_ERR") if ran else None,
    }


direct_midi_probe = _read_direct_midi_probe(
    os.environ["DIRECT_MIDI_JSONL"],
    ran=direct_midi_ran,
    rc=direct_midi_rc,
)
direct_midi_motion = bool(direct_midi_probe.get("motion_observed"))
if diagnosis == "live_socket_missing":
    action_hint = "start_live_session"
elif diagnosis == "stale_live_runtime":
    action_hint = "restart_live_session"
elif not checks.get("controller_connected"):
    action_hint = "connect_ddj_flx4_and_start_live_session"
elif direct_midi_ran and direct_midi_motion and not checks.get("recent_moves_seen"):
    action_hint = "restart_live_midi_listener"
elif not checks.get("recent_moves_seen") and not checks.get("audio_observed"):
    action_hint = "play_audible_deck_audio_and_move_a_fader_or_knob_within_the_proof_window"
elif not checks.get("recent_moves_seen"):
    action_hint = "move_a_fader_or_knob_within_the_proof_window"
elif not checks.get("audio_observed"):
    action_hint = "play_audible_deck_audio_above_the_floor"
else:
    action_hint = "collect_remaining_blockers"
live_rc = int(os.environ["LIVE_RC"])
good_rc = int(os.environ["GOOD_VERIFY_RC"])
listener_read_canary = "skipped"
audio_causality_rejected = "skipped"
audio_source_detail_rejected = "skipped"
if live_rc == 0:
    listener_read_canary = good_rc == 0
    audio_causality_rejected = os.environ["BAD_CAUSAL_REJECTED"] == "true"
    audio_source_detail_rejected = os.environ["BAD_SOURCE_REJECTED"] == "true"


def add_action(actions: list[dict], code: str, detail: str) -> None:
    if any(action.get("code") == code for action in actions):
        return
    actions.append({"code": code, "detail": detail})


def copy_proof_actions(
    actions: list[dict],
    raw_actions: object,
    *,
    skip_codes: set[str] | None = None,
) -> None:
    """Prefer the core live-context action queue when it is present.

    The release checker still adds hardware-only diagnostics such as the direct
    OS MIDI probe. Those overlays can skip broad core advice like
    ``move_controller`` when we have stronger local evidence.
    """
    skip_codes = skip_codes or set()
    if not isinstance(raw_actions, list):
        return
    for raw in raw_actions:
        if not isinstance(raw, dict):
            continue
        code = str(raw.get("code") or "").strip()
        detail = str(raw.get("detail") or "").strip()
        if not code or not detail or code in skip_codes:
            continue
        if any(action.get("code") == code for action in actions):
            continue
        action = {"code": code, "detail": detail}
        for key in ("recommended_env", "setup_hint", "diagnostic_commands", "artifacts"):
            value = raw.get(key)
            if value is not None:
                action[key] = value
        actions.append(action)


setup_hint = proof.get("setup_hint") if isinstance(proof.get("setup_hint"), dict) else None
operator_actions: list[dict] = []
needs_operator_action = not bool(readiness.get("ready"))
hardware_midi_seen = bool(midi_ports)
physical_diagnosis = diagnosis not in {"live_socket_missing", "stale_live_runtime"}
proof_operator_actions = proof.get("operator_actions")
skip_proof_action_codes: set[str] = set()
if needs_operator_action and physical_diagnosis and direct_midi_ran:
    skip_proof_action_codes.add("move_controller")
if (
    needs_operator_action
    and physical_diagnosis
    and direct_midi_ran
    and direct_midi_motion
    and not checks.get("recent_moves_seen")
):
    add_action(
        operator_actions,
        "restart_live_midi_listener",
        "The direct OS MIDI probe saw FLX4 frames, but live-context did not; restart the live session and inspect MIDI listener binding if it repeats.",
    )
copy_proof_actions(
    operator_actions,
    proof_operator_actions,
    skip_codes=skip_proof_action_codes,
)
if needs_operator_action and diagnosis == "live_socket_missing":
    add_action(
        operator_actions,
        "start_live_session",
        "Start the Vibemix live session on the current source and keep ws://127.0.0.1:8765 open.",
    )
elif needs_operator_action and diagnosis == "stale_live_runtime":
    add_action(
        operator_actions,
        "restart_live_session",
        "Restart the Vibemix live session so it advertises the current live-context schema and capabilities.",
    )
elif needs_operator_action and setup_hint and setup_hint.get("next_action"):
    add_action(operator_actions, "apply_route_hint", str(setup_hint["next_action"]))
if (
    needs_operator_action
    and physical_diagnosis
    and direct_midi_ran
    and direct_midi_motion
    and not checks.get("recent_moves_seen")
):
    add_action(
        operator_actions,
        "restart_live_midi_listener",
        "The direct OS MIDI probe saw FLX4 frames, but live-context did not; restart the live session and inspect MIDI listener binding if it repeats.",
    )
if needs_operator_action and not operator_actions and (
    not checks.get("frames_seen") or not checks.get("flat_deck_frame_seen")
):
    add_action(
        operator_actions,
        "start_live_session",
        "Start the Vibemix live session on the current source and keep ws://127.0.0.1:8765 open.",
    )
if needs_operator_action and physical_diagnosis and not checks.get("controller_connected"):
    if hardware_midi_seen:
        add_action(
            operator_actions,
            "restart_live_with_flx4",
            "DDJ-FLX4 is visible to the checker, but not in the live-context packet; restart the live session with the controller connected.",
        )
    else:
        add_action(
            operator_actions,
            "connect_flx4",
            "Connect DDJ-FLX4 over USB and confirm it appears in MIDI plus audio device enumeration.",
        )
if (
    needs_operator_action
    and physical_diagnosis
    and not checks.get("recent_moves_seen")
    and not checks.get("audio_observed")
    and not (direct_midi_ran and direct_midi_motion)
):
    add_action(
        operator_actions,
        "perform_physical_proof_window",
        "During the proof window, play audible DJ app output and move a FLX4 fader, EQ, filter, or transport control.",
    )
if needs_operator_action and physical_diagnosis and not checks.get("recent_moves_seen"):
    if direct_midi_ran and direct_midi_motion:
        pass
    elif direct_midi_ran:
        add_action(
            operator_actions,
            "prove_os_midi_motion",
            "The direct OS MIDI probe saw no FLX4 frames; move a fader/knob during the probe window or fix USB/MIDI input before trusting live moves.",
        )
    else:
        add_action(
            operator_actions,
            "move_controller",
            "Move a fader, EQ, filter, or transport control during the proof window.",
        )
if needs_operator_action and physical_diagnosis and not checks.get("audio_observed"):
    add_action(
        operator_actions,
        "play_audible_audio",
        "Play audible DJ app output into the configured capture route during the proof window.",
    )
if (
    needs_operator_action
    and physical_diagnosis
    and (not checks.get("deck_state_resolved") or not checks.get("deck_state_pair_resolved"))
):
    add_action(
        operator_actions,
        "resolve_deck_identity",
        "Load identifiable tracks on both decks so live context can cite deck A and deck B instead of guessing.",
    )
if needs_operator_action and physical_diagnosis and not checks.get("deck_pair_capture_configured"):
    add_action(
        operator_actions,
        "configure_deck_pair_capture",
        "Use a multichannel route such as BlackHole 16ch with VIBEMIX_DECK_AUDIO_CHANNELS=auto for per-deck proof.",
    )
if (
    needs_operator_action
    and physical_diagnosis
    and checks.get("deck_pair_capture_configured")
    and not checks.get("deck_audio_capture_both_active")
):
    add_action(
        operator_actions,
        "feed_both_deck_lanes",
        (
            "Deck-pair capture is configured, but live proof still has only one active deck lane. "
            "For a BlackHole 16ch/Rekordbox rig, route Deck 1 to BlackHole channels 1/2 and "
            "Deck 2 to channels 3/4, or update VIBEMIX_DECK_AUDIO_CHANNELS to the actual "
            "A/B channel map; rerun until deck_audio_capture=A_active+B_active."
        ),
    )
if needs_operator_action and not operator_actions and blockers:
    add_action(operator_actions, "inspect_blockers", next_action)


def _first_matching(items: list, *needles: str) -> str | None:
    for item in items:
        text = str(item)
        if any(needle in text for needle in needles):
            return text
    return None


def _append_once(items: list[str], value: str | None) -> None:
    if value and value not in items:
        items.append(value)


def _prioritized_physical_blockers(items: list, checks: dict) -> list[str]:
    out: list[str] = []
    if not checks.get("recent_moves_seen"):
        if direct_midi_ran and direct_midi_motion:
            _append_once(
                out,
                "live context did not ingest controller moves even though the direct OS MIDI probe saw FLX4 frames",
            )
        elif direct_midi_ran:
            _append_once(
                out,
                "direct OS MIDI probe saw no controller frames during the probe window",
            )
        _append_once(out, _first_matching(items, "recent controller moves"))
    if not checks.get("audio_observed"):
        _append_once(
            out,
            _first_matching(items, "live master audio", "bounded audio_delta"),
        )
    if not checks.get("deck_state_resolved") or not checks.get("deck_state_pair_resolved"):
        for needle in (
            "deck_state had no resolved",
            "deck identity source",
            "screen vision",
            "deck_state had no citable",
            "deck_state did not resolve",
            "deck_state did not have citable",
        ):
            _append_once(out, _first_matching(items, needle))
    if not checks.get("deck_pair_capture_configured"):
        _append_once(out, _first_matching(items, "deck-pair audio capture"))
    if not checks.get("deck_audio_capture_both_active"):
        _append_once(out, _first_matching(items, "active audio on both deck lanes"))
    for item in items:
        _append_once(out, str(item))
    return out[:8]


if diagnosis == "live_socket_missing":
    top_blockers = [
        str(item)
        for item in blockers
        if "websocket frames" in str(item) or "flat deck frame" in str(item)
    ][:4]
elif diagnosis == "stale_live_runtime":
    top_blockers = [
        str(item)
        for item in blockers
        if "live socket" in str(item)
        or "schema" in str(item)
        or "capabilities" in str(item)
    ][:4]
else:
    top_blockers = _prioritized_physical_blockers(blockers, checks)
if not top_blockers and blockers:
    top_blockers = [str(blockers[0])]
first_blocker = top_blockers[0] if top_blockers else raw_first_blocker


def _leg(
    leg_id: str,
    status: str,
    detail: str,
    *,
    blocker: str | None = None,
) -> dict:
    out = {"id": leg_id, "status": status, "detail": detail}
    if status != "pass" and blocker:
        out["blocker"] = blocker
    return out


def _status(value: object) -> str:
    return "pass" if bool(value) else "missing"


def _status_or_skipped(value: object, *, enabled: bool) -> str:
    if not enabled:
        return "skipped"
    return _status(value)


reply_canaries_ok = os.environ["REPLY_CANARIES_OK"] == "true"
proof_legs = [
    _leg(
        "live_socket_frames",
        _status(bool(proof.get("frames_seen")) or checks.get("frames_seen")),
        "Live ws:8765 produced bounded context frames.",
        blocker=_first_matching(blockers, "websocket frames", "flat deck frame"),
    ),
    _leg(
        "live_context_schema",
        _status(
            readiness.get("ready")
            or (
                checks.get("live_context_schema_seen")
                and checks.get("live_context_capabilities_seen")
            )
        ),
        "Live socket advertised schema v2 and required live-context capabilities.",
        blocker=_first_matching(blockers, "schema", "capabilities"),
    ),
    _leg(
        "controller_connected",
        _status(readiness.get("ready") or checks.get("controller_connected")),
        "DDJ-FLX4 is visible inside the live context packet.",
        blocker=_first_matching(blockers, "controller", "MIDI"),
    ),
    _leg(
        "recent_controller_move",
        _status(readiness.get("ready") or checks.get("recent_moves_seen")),
        "A FLX4 move was observed inside the proof window.",
        blocker=_first_matching(blockers, "recent controller moves"),
    ),
    _leg(
        "audible_audio",
        _status(readiness.get("ready") or checks.get("audio_observed")),
        "Audible DJ app output crossed the live-context audio floor.",
        blocker=_first_matching(blockers, "live master audio", "bounded audio_delta"),
    ),
    _leg(
        "deck_identity",
        _status(
            readiness.get("ready")
            or (checks.get("deck_state_resolved") and checks.get("deck_state_pair_resolved"))
        ),
        "Deck A and Deck B identities are resolved enough to cite rather than guess.",
        blocker=_first_matching(blockers, "deck_state had no resolved", "deck_state did not resolve"),
    ),
    _leg(
        "deck_pair_audio_capture",
        _status(
            readiness.get("ready")
            or (
                checks.get("deck_pair_capture_configured")
                and checks.get("deck_audio_capture_both_active")
            )
        ),
        "Per-deck audio capture is configured and active on both lanes.",
        blocker=_first_matching(
            blockers,
            "deck-pair audio capture",
            "active audio on both deck lanes",
        ),
    ),
    _leg(
        "reply_safety_canaries",
        _status_or_skipped(reply_canaries_ok, enabled=live_rc == 0),
        "Listener-read canary passes while causal/source-detail hallucination canaries are rejected.",
    ),
]
proof_legs_passed = sum(1 for leg in proof_legs if leg["status"] == "pass")
proof_legs_total = len(proof_legs)
midi_motion_diagnosis = "not_run"
if direct_midi_ran and direct_midi_motion and not checks.get("recent_moves_seen"):
    midi_motion_diagnosis = "live_midi_ingest_missing"
elif direct_midi_ran and not direct_midi_motion and not checks.get("recent_moves_seen"):
    midi_motion_diagnosis = "no_direct_midi_motion_observed"
elif direct_midi_ran and direct_midi_motion:
    midi_motion_diagnosis = "direct_midi_motion_observed"

summary = {
    "schema": "flx4_live_context_summary_v1",
    "ok": live_rc == 0 and os.environ["REPLY_CANARIES_OK"] == "true",
    "midi_port": midi_ports[0] if midi_ports else None,
    "audio_device_found": True,
    "live_ok": bool(proof.get("ok")),
    "live_ready": bool(readiness.get("ready")),
    "diagnosis": readiness.get("diagnosis"),
    "action_hint": action_hint,
    "operator_actions": operator_actions,
    "first_blocker": first_blocker,
    "top_blockers": top_blockers,
    "blocker_count": len(blockers),
    "proof_legs": proof_legs,
    "proof_legs_passed": proof_legs_passed,
    "proof_legs_total": proof_legs_total,
    "direct_midi_probe": direct_midi_probe,
    "midi_motion_diagnosis": midi_motion_diagnosis,
    "next_action": next_action,
    "checks": {
        "controller_connected": bool(checks.get("controller_connected")),
        "deck_state_resolved": bool(checks.get("deck_state_resolved")),
        "deck_state_pair_resolved": bool(checks.get("deck_state_pair_resolved")),
        "recent_moves_seen": bool(checks.get("recent_moves_seen")),
        "audio_observed": bool(checks.get("audio_observed")),
        "deck_pair_capture_configured": bool(checks.get("deck_pair_capture_configured")),
        "deck_audio_capture_both_active": bool(checks.get("deck_audio_capture_both_active")),
    },
    "canaries": {
        "listener_read": listener_read_canary,
        "audio_causality_rejected": audio_causality_rejected,
        "audio_source_detail_rejected": audio_source_detail_rejected,
    },
    "setup_hint": setup_hint,
    "artifacts": {
        "proof_json": sys.argv[1],
        "listener_read_verification": os.environ["GOOD_VERIFY_JSON"],
        "audio_causality_rejection": os.environ["BAD_CAUSAL_VERIFY_JSON"],
        "audio_source_detail_rejection": os.environ["BAD_SOURCE_VERIFY_JSON"],
        "direct_midi_probe": direct_midi_probe.get("jsonl"),
        "direct_midi_probe_stderr": direct_midi_probe.get("stderr"),
    },
}
summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
print(
    "midi_port={midi_port} audio_device=True live_ok={live_ok} live_ready={live_ready} "
    "diagnosis={diagnosis} frames={frames} controller_connected={controller} "
    "recent_moves={moves} audio_observed={audio} blockers={blockers} "
    "direct_midi={direct_midi} direct_midi_frames={direct_midi_frames} "
    "midi_motion_diag={midi_motion_diag} "
    "listener_read_canary={listener_read_canary} "
    "audio_causality_rejected={audio_causality_rejected} "
    "audio_source_detail_rejected={audio_source_detail_rejected} "
    "action_hint={action_hint} first_blocker={first_blocker!r} "
    "next_action={next_action!r} proof={proof}".format(
        midi_port=midi_ports[0] if midi_ports else "none",
        live_ok=proof.get("ok"),
        live_ready=readiness.get("ready"),
        diagnosis=readiness.get("diagnosis"),
        frames=proof.get("frames_seen"),
        controller=checks.get("controller_connected"),
        moves=checks.get("recent_moves_seen"),
        audio=checks.get("audio_observed"),
        blockers=len(blockers),
        direct_midi=direct_midi_probe.get("motion_observed"),
        direct_midi_frames=direct_midi_probe.get("frames"),
        midi_motion_diag=midi_motion_diagnosis,
        listener_read_canary=listener_read_canary,
        audio_causality_rejected=audio_causality_rejected,
        audio_source_detail_rejected=audio_source_detail_rejected,
        action_hint=action_hint,
        first_blocker=first_blocker,
        next_action=next_action,
        proof=sys.argv[1],
    )
)
PY
)

if [ "${LIVE_RC}" -eq 0 ] && [ "${REPLY_CANARIES_OK}" = "true" ]; then
  emit_pass "${SUMMARY_LINE}"
  exit 0
fi

emit_err "${SUMMARY_LINE}"
if [ "${LIVE_RC}" -ne 0 ]; then
  exit "${LIVE_RC}"
fi
if [ "${GOOD_VERIFY_RC}" -ne 0 ]; then
  exit "${GOOD_VERIFY_RC}"
fi
exit 1
