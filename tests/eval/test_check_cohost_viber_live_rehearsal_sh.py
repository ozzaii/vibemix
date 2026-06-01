# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
from pathlib import Path

SCRIPT = Path("scripts/release/check_cohost_viber_live_rehearsal.sh").resolve()


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _fake_live_script(tmp_path: Path) -> Path:
    path = tmp_path / "fake_live.py"
    path.write_text(
        """from __future__ import annotations

import signal
import socket
import sys
import threading
import time

port = int(sys.argv[1])
stop = threading.Event()

def _stop(*_args):
    stop.set()

signal.signal(signal.SIGTERM, _stop)
signal.signal(signal.SIGINT, _stop)
sock = socket.socket()
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind(("127.0.0.1", port))
sock.listen(8)
sock.settimeout(0.2)
while not stop.is_set():
    try:
        conn, _addr = sock.accept()
    except socket.timeout:
        continue
    with conn:
        pass
sock.close()
time.sleep(0.05)
""",
        encoding="utf-8",
    )
    return path


def _fake_wrapper_dir(tmp_path: Path) -> Path:
    wrapper_dir = tmp_path / "wrappers"
    wrapper_dir.mkdir()
    (wrapper_dir / "check_cohost_viber_matrix.sh").write_text(
        """#!/usr/bin/env bash
set -euo pipefail
mkdir -p "${COHOST_VIBER_MATRIX_OUT_DIR}"
mkdir -p "${COHOST_VIBER_MATRIX_OUT_DIR}/autopilot"
rc="${FAKE_MATRIX_RC:-0}"
if [ -n "${FAKE_MATRIX_PASS_ON_ATTEMPT:-}" ] && [ "${COHOST_VIBER_REHEARSAL_ATTEMPT:-1}" -ge "${FAKE_MATRIX_PASS_ON_ATTEMPT}" ]; then
  rc=0
fi
ai_messages="${FAKE_COHOST_AI_MESSAGES:-1}"
live_coach_messages="${FAKE_LIVE_COACH_MESSAGES:-$ai_messages}"
viber_rows="${FAKE_VIBER_ROWS:-1}"
viber_errored_rows="${FAKE_VIBER_ERRORED_ROWS:-0}"
python3 - "${COHOST_VIBER_MATRIX_OUT_DIR}/autopilot/report.json" "$ai_messages" "$live_coach_messages" "$viber_rows" "$viber_errored_rows" <<'PY'
import json
import sys
from pathlib import Path

payload = {
    "schema": "cohost_viber_automation_report_v1",
    "ok": True,
    "metrics": {
        "session": {
            "ai_messages": int(sys.argv[2]),
            "live_coach_messages": int(sys.argv[3]),
        },
        "viber": {
            "rows_inspected": int(sys.argv[4]),
            "errored_rows": int(sys.argv[5]),
        },
    },
    "issues": [],
}
Path(sys.argv[1]).write_text(json.dumps(payload), encoding="utf-8")
PY
python3 - "${COHOST_VIBER_MATRIX_OUT_DIR}/matrix_summary.json" "$rc" <<'PY'
import json
import os
import sys
from pathlib import Path

rc = int(sys.argv[2])
flx4_ok = rc == 0
autopilot_ok = os.environ.get("FAKE_AUTOPILOT_OK", "1") not in {"0", "false", "False"}
corpus_ok = os.environ.get("FAKE_CORPUS_OK", "1") not in {"0", "false", "False"}
runtime_ok = os.environ.get("FAKE_RUNTIME_OK", "1") not in {"0", "false", "False"}
matrix_mode = os.environ.get("COHOST_VIBER_MATRIX_MODE", "release")
autopilot_fail_on = "first-pass" if matrix_mode == "first-pass" else matrix_mode
corpus_fail_on = "automation" if matrix_mode in {"first-pass", "audio-evidence"} else matrix_mode
attempt = int(os.environ.get("COHOST_VIBER_REHEARSAL_ATTEMPT") or "1")

def value_for_attempt(name: str, default: str) -> str:
    raw = os.environ.get(name)
    if not raw:
        return default
    values = [item.strip() for item in raw.split(",")]
    if not values:
        return default
    return values[min(attempt - 1, len(values) - 1)] or default

direct_midi_s = os.environ.get("COHOST_VIBER_FLX4_DIRECT_MIDI_PROBE_S")
direct_midi_mode = os.environ.get("COHOST_VIBER_FLX4_DIRECT_MIDI_PROBE_MODE")
direct_midi_ran = direct_midi_s not in {None, "", "0", "0.0"}
direct_midi_frames = int(value_for_attempt("FAKE_DIRECT_MIDI_FRAMES", "0"))
recent_moves_seen = (
    value_for_attempt("FAKE_RECENT_MOVES_SEEN", "1" if flx4_ok else "0")
    not in {"0", "false", "False"}
)
audio_observed = (
    value_for_attempt("FAKE_AUDIO_OBSERVED", "1" if flx4_ok else "0")
    not in {"0", "false", "False"}
)
deck_state_resolved = (
    value_for_attempt("FAKE_DECK_STATE_RESOLVED", "1" if flx4_ok else "0")
    not in {"0", "false", "False"}
)
deck_state_pair_resolved = (
    value_for_attempt("FAKE_DECK_STATE_PAIR_RESOLVED", "1" if flx4_ok else "0")
    not in {"0", "false", "False"}
)
deck_pair_capture_configured = (
    value_for_attempt("FAKE_DECK_PAIR_CAPTURE_CONFIGURED", "1" if flx4_ok else "0")
    not in {"0", "false", "False"}
)
deck_audio_capture_both_active = (
    value_for_attempt("FAKE_DECK_AUDIO_CAPTURE_BOTH_ACTIVE", "1" if flx4_ok else "0")
    not in {"0", "false", "False"}
)
next_action = {"code": "ready", "source": "matrix", "detail": "fake ready"}
if not autopilot_ok:
    next_action = {
        "code": "inspect_autopilot",
        "source": "autopilot",
        "detail": "FAIL autopilot",
        "recommended_command": f"COHOST_VIBER_FAIL_ON={autopilot_fail_on} bash scripts/release/check_cohost_viber_autopilot.sh",
    }
elif not corpus_ok:
    next_action = {
        "code": "inspect_corpus",
        "source": "corpus",
        "detail": "FAIL corpus",
        "recommended_command": f"COHOST_VIBER_CORPUS_FAIL_ON={corpus_fail_on} bash scripts/release/check_cohost_viber_corpus_benchmark.sh",
    }
elif not runtime_ok:
    runtime_code = os.environ.get("FAKE_RUNTIME_ACTION_CODE") or "inspect_runtime_canaries"
    next_action = {
        "code": runtime_code,
        "source": "runtime_canaries",
        "detail": "Runtime canary coverage is incomplete." if runtime_code == "restore_runtime_canary_coverage" else "FAIL runtime canaries",
        "recommended_command": "bash scripts/release/check_cohost_viber_runtime_canaries.sh",
        "artifacts": {
            "summary_json": os.environ["COHOST_VIBER_MATRIX_OUT_DIR"] + "/runtime-canaries/runtime_canaries_summary.json",
            "manifest": os.environ["COHOST_VIBER_MATRIX_OUT_DIR"] + "/runtime-canaries/runtime_canaries_manifest.json",
        },
    }
elif not flx4_ok and os.environ.get("FAKE_MATRIX_FLX4_NEXT_ACTION_CODE"):
    flx4_code = os.environ["FAKE_MATRIX_FLX4_NEXT_ACTION_CODE"]
    next_action = {
        "code": flx4_code,
        "source": "flx4",
        "detail": f"FLX4 says {flx4_code}.",
        "diagnostic_commands": [
            "python scripts/sniff_controller.py --port DDJ-FLX4 --seconds 10 --mode callback"
        ],
        "recommended_command": (
            f"COHOST_VIBER_REHEARSAL_MATRIX_MODE={matrix_mode} "
            "COHOST_VIBER_REHEARSAL_START_LIVE=required "
            "COHOST_VIBER_REHEARSAL_FLX4=required "
            "bash scripts/release/check_cohost_viber_live_rehearsal.sh"
        ),
    }
operator_action_queue = [next_action]
if os.environ.get("FAKE_MATRIX_SECONDARY_ACTION", "0") not in {"0", "false", "False"}:
    operator_action_queue.append(
        {
            "code": "review_audio_evidence_debt",
            "source": "autopilot",
            "detail": "Review secondary audio evidence debt.",
            "recommended_command": "COHOST_VIBER_FAIL_ON=audio-evidence bash scripts/release/check_cohost_viber_autopilot.sh",
        }
    )
payload = {
    "schema": "cohost_viber_release_matrix_v1",
    "ok": flx4_ok and autopilot_ok and corpus_ok and runtime_ok,
    "mode": matrix_mode,
    "autopilot_fail_on": autopilot_fail_on,
    "corpus_fail_on": corpus_fail_on,
    "attempt": os.environ.get("COHOST_VIBER_REHEARSAL_ATTEMPT"),
    "session_dir": os.environ.get("COHOST_VIBER_SESSION_DIR"),
    "corpus_session_dir": os.environ.get("COHOST_VIBER_CORPUS_SESSION_DIR"),
    "global_since_iso": os.environ.get("COHOST_VIBER_GLOBAL_SINCE_ISO"),
    "flx4_wait_ready_s": os.environ.get("COHOST_VIBER_FLX4_WAIT_READY_S"),
    "flx4_timeout_s": os.environ.get("COHOST_VIBER_FLX4_TIMEOUT_S"),
    "flx4_frames": os.environ.get("COHOST_VIBER_FLX4_FRAMES"),
    "flx4_direct_midi_probe_s": direct_midi_s,
    "flx4_direct_midi_probe_mode": direct_midi_mode,
    "checks": {
        "autopilot": {
            "ok": autopilot_ok,
            "required": True,
            "rc": 0 if autopilot_ok else 1,
            "summary": "PASS autopilot" if autopilot_ok else "FAIL autopilot",
            "out_dir": os.environ["COHOST_VIBER_MATRIX_OUT_DIR"] + "/autopilot",
            "first_pass_clean": autopilot_ok,
            "reprompt_debt": 0 if autopilot_ok else 1,
            "audio_evidence_debt": 0 if autopilot_ok else 1,
        },
        "corpus": {"ok": corpus_ok, "required": True, "rc": 0 if corpus_ok else 1, "summary": "PASS corpus" if corpus_ok else "FAIL corpus"},
        "runtime_canaries": {
            "ok": runtime_ok,
            "required": True,
            "rc": 0 if runtime_ok else 1,
            "summary": "PASS runtime" if runtime_ok else "FAIL runtime canaries",
            "coverage_ok": runtime_ok,
            "missing_canaries": 0 if runtime_ok else 1,
            "exercised": 8 if runtime_ok else 7,
        },
        "flx4": {
            "ok": flx4_ok,
            "rc": rc,
            "ran": True,
            "required": True,
            "summary": "PASS flx4" if flx4_ok else "FAIL flx4",
            "diagnosis": "ready" if flx4_ok else "missing_physical_proof",
            "action_hint": "none" if flx4_ok else "play_audible_audio" if recent_moves_seen and not audio_observed else "play_audible_deck_audio_and_move_a_fader_or_knob_within_the_proof_window",
            "first_blocker": "none" if flx4_ok else "live master audio was not observed above the audible floor" if recent_moves_seen and not audio_observed else "live master audio was not observed above the audible floor",
            "top_blockers": [] if flx4_ok else ["live master audio was not observed above the audible floor"],
            "operator_actions": [] if flx4_ok else [{"code": "play_audible_audio", "detail": "Play audible DJ app output."}],
            "proof_legs": [
                {"id": "live_socket_frames", "status": "pass"},
                {"id": "controller_connected", "status": "pass"},
                {"id": "audible_audio", "status": "pass" if audio_observed else "missing"},
                {"id": "deck_identity", "status": "pass" if deck_state_pair_resolved else "missing"},
                {"id": "deck_pair_audio_capture", "status": "pass" if deck_pair_capture_configured and deck_audio_capture_both_active else "missing"},
            ],
            "proof_legs_passed": sum(
                1
                for passed in [
                    True,
                    True,
                    audio_observed,
                    deck_state_pair_resolved,
                    deck_pair_capture_configured and deck_audio_capture_both_active,
                ]
                if passed
            ),
            "proof_legs_total": 5,
            "checks": {
                "controller_connected": True,
                "deck_state_resolved": deck_state_resolved,
                "deck_state_pair_resolved": deck_state_pair_resolved,
                "recent_moves_seen": recent_moves_seen,
                "audio_observed": audio_observed,
                "deck_pair_capture_configured": deck_pair_capture_configured,
                "deck_audio_capture_both_active": deck_audio_capture_both_active,
            },
            "direct_midi_probe": {
                "ran": direct_midi_ran,
                "ok": True,
                "rc": 0 if direct_midi_ran else None,
                "seconds": direct_midi_s if direct_midi_ran else None,
                "mode": direct_midi_mode if direct_midi_ran else None,
                "sampling": "concurrent_with_live_context" if direct_midi_ran else "disabled",
                "motion_observed": direct_midi_ran and direct_midi_frames > 0,
                "frames": direct_midi_frames if direct_midi_ran else 0,
                "unique_cc": [74] if direct_midi_ran and direct_midi_frames > 0 else [],
                "unique_notes": [],
                "jsonl": os.environ["COHOST_VIBER_MATRIX_OUT_DIR"] + "/flx4/direct_midi_probe.jsonl" if direct_midi_ran else None,
                "stderr": os.environ["COHOST_VIBER_MATRIX_OUT_DIR"] + "/flx4/direct_midi_probe.stderr.log" if direct_midi_ran else None,
            },
            "midi_motion_diagnosis": (
                "direct_midi_motion_observed"
                if direct_midi_ran and direct_midi_frames > 0
                else "no_direct_midi_motion_observed"
                if direct_midi_ran
                else "not_run"
            ),
            "summary_json": os.environ["COHOST_VIBER_MATRIX_OUT_DIR"] + "/flx4/flx4_live_context_summary.json",
            "setup_hint": {
                "status": "rekordbox_route_hint_found",
                "recommended_env": {"VIBEMIX_DECK_AUDIO_CHANNELS": "auto"},
                "next_action": "Start the live session with VIBEMIX_DECK_AUDIO_CHANNELS=auto, play both decks, move a controller, then rerun proof.",
                "rule": "setup_hint_not_live_audio_proof",
            } if os.environ.get("FAKE_FLX4_SETUP_HINT", "0") not in {"0", "false", "False"} else None,
        },
    },
    "next_operator_action": next_action,
    "operator_action_queue": operator_action_queue,
}
Path(sys.argv[1]).write_text(json.dumps(payload), encoding="utf-8")
PY
if [ "$rc" = "0" ]; then
  echo "PASS check_cohost_viber_matrix: fake"
  exit 0
fi
echo "FAIL check_cohost_viber_matrix: fake" >&2
exit "$rc"
""",
        encoding="utf-8",
    )
    (wrapper_dir / "check_cohost_viber_matrix.sh").chmod(0o755)
    return wrapper_dir


def _run_rehearsal(
    tmp_path: Path,
    *,
    start_live: str,
    port: int,
    live_cmd: str | None = None,
    matrix_rc: int = 0,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(
        {
            "PYTHON": sys.executable,
            "COHOST_VIBER_REHEARSAL_OUT_DIR": str(tmp_path / "out"),
            "COHOST_VIBER_REHEARSAL_START_LIVE": start_live,
            "COHOST_VIBER_REHEARSAL_SOCKET_PORT": str(port),
            "COHOST_VIBER_REHEARSAL_SOCKET_PROTOCOL": "tcp",
            "COHOST_VIBER_REHEARSAL_WRAPPER_DIR": str(_fake_wrapper_dir(tmp_path)),
            "COHOST_VIBER_REHEARSAL_WAIT_SOCKET_S": "4",
            "COHOST_VIBER_REHEARSAL_PROOF_WINDOW_S": "7",
            "COHOST_VIBER_REHEARSAL_PROOF_TIMEOUT_S": "1.5",
            "COHOST_VIBER_REHEARSAL_PROOF_FRAMES": "77",
            "COHOST_VIBER_REHEARSAL_FLX4": "required",
            "COHOST_VIBER_REHEARSAL_STIMULATE": "0",
            "FAKE_MATRIX_RC": str(matrix_rc),
        }
    )
    if live_cmd:
        env["COHOST_VIBER_REHEARSAL_LIVE_CMD"] = live_cmd
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=Path.cwd(),
        env=env,
        text=True,
        capture_output=True,
        check=False,
        timeout=15,
    )


def test_live_rehearsal_starts_live_process_runs_matrix_and_cleans_up(
    tmp_path: Path,
) -> None:
    port = _free_port()
    live_script = _fake_live_script(tmp_path)

    proc = _run_rehearsal(
        tmp_path,
        start_live="required",
        port=port,
        live_cmd=f"{sys.executable} {live_script} {port}",
    )

    assert proc.returncode == 0
    assert "PASS check_cohost_viber_live_rehearsal" in proc.stdout
    assert "ACTION check_cohost_viber_live_rehearsal: attempt 1/1; for the next 7s" in proc.stdout
    assert "started_live=True" in proc.stdout
    assert "live_env_applied=True" in proc.stdout
    assert "dev_sidecar=1" in proc.stdout
    assert "citation_lint=on" in proc.stdout
    assert "global_since=" in proc.stdout
    assert "matrix_mode=first-pass" in proc.stdout
    assert "first_pass=True" in proc.stdout
    assert "reprompt_debt=0" in proc.stdout
    assert "audio_evidence_debt=0" in proc.stdout
    summary = json.loads((tmp_path / "out" / "live_rehearsal_summary.json").read_text())
    assert summary["ok"] is True
    assert summary["started_live"] is True
    assert summary["live_state"] == "started"
    assert summary["live_env_applied"] is True
    assert summary["requested_dev_sidecar"] == "1"
    assert summary["requested_citation_lint"] == "on"
    assert summary["global_since_iso"]
    assert summary["matrix_mode"] == "first-pass"
    assert summary["first_pass_clean"] is True
    assert summary["reprompt_debt"] == 0
    assert summary["audio_evidence_debt"] == 0
    assert summary["proof_window_s"] == "7"
    assert summary["matrix"]["mode"] == "first-pass"
    assert summary["matrix"]["autopilot_fail_on"] == "first-pass"
    assert summary["matrix"]["corpus_fail_on"] == "automation"
    assert summary["matrix"]["flx4_wait_ready_s"] == "7"
    assert summary["matrix"]["flx4_timeout_s"] == "1.5"
    assert summary["matrix"]["flx4_frames"] == "77"
    assert summary["direct_midi_probe_s"] == "3"
    assert summary["direct_midi_probe_mode"] == "callback"
    assert summary["matrix"]["flx4_direct_midi_probe_s"] == "3"
    assert summary["matrix"]["flx4_direct_midi_probe_mode"] == "callback"
    assert summary["matrix"]["global_since_iso"] == summary["global_since_iso"]
    assert summary["physical"]["ok"] is True
    assert summary["physical"]["diagnosis"] == "ready"
    assert summary["physical"]["direct_midi_probe"]["ran"] is True
    assert summary["physical"]["direct_midi_probe"]["seconds"] == "3"
    assert summary["physical"]["direct_midi_probe"]["sampling"] == "concurrent_with_live_context"
    assert summary["physical"]["midi_motion_diagnosis"] == "no_direct_midi_motion_observed"
    assert summary["next_operator_action"]["code"] == "ready"
    assert [action["code"] for action in summary["operator_action_queue"]] == ["ready"]
    assert summary["operator_actions_json"] == str(tmp_path / "out" / "operator_actions.json")
    assert summary["operator_runbook_sh"] == str(tmp_path / "out" / "operator_action_runbook.sh")
    actions_payload = json.loads((tmp_path / "out" / "operator_actions.json").read_text())
    assert actions_payload["source"] == "live_rehearsal"
    assert actions_payload["runbook_sh"] == str(
        tmp_path / "out" / "operator_action_runbook.sh"
    )
    assert actions_payload["dry_run_default"] is True
    assert actions_payload["actions"][0]["code"] == "ready"
    runbook = (tmp_path / "out" / "operator_action_runbook.sh").read_text()
    assert "cohost/Viber operator action runbook (live rehearsal)" in runbook
    assert "Set RUN_OPERATOR_COMMANDS=1 to execute" in runbook
    assert f"runbook={tmp_path / 'out' / 'operator_action_runbook.sh'}" in proc.stdout
    assert "next_action=ready" in proc.stdout
    assert "actions=1" in proc.stdout
    assert "recommended_command=none" in proc.stdout
    pid = int((tmp_path / "out" / "live.pid").read_text())
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        pass
    else:  # pragma: no cover - defensive cleanup assertion
        raise AssertionError(f"live process {pid} was not cleaned up")


def test_live_rehearsal_forwards_pinned_session_to_matrix(
    tmp_path: Path,
) -> None:
    port = _free_port()
    live_script = _fake_live_script(tmp_path)
    session_dir = tmp_path / "recordings" / "current"

    proc = _run_rehearsal(
        tmp_path,
        start_live="required",
        port=port,
        live_cmd=f"{sys.executable} {live_script} {port}",
        extra_env={
            "COHOST_VIBER_SESSION_DIR": str(session_dir),
            "COHOST_VIBER_GLOBAL_SINCE_ISO": "2026-05-31T20:00:00Z",
        },
    )

    assert proc.returncode == 0
    summary = json.loads((tmp_path / "out" / "live_rehearsal_summary.json").read_text())
    assert summary["rehearsal_session_dir"] == str(session_dir)
    assert summary["corpus_session_dir"] == str(session_dir)
    assert summary["global_since_iso"] == "2026-05-31T20:00:00Z"
    assert summary["matrix"]["session_dir"] == str(session_dir)
    assert summary["matrix"]["corpus_session_dir"] == str(session_dir)
    assert summary["matrix"]["global_since_iso"] == "2026-05-31T20:00:00Z"


def test_live_rehearsal_records_stimulus_summary(
    tmp_path: Path,
) -> None:
    port = _free_port()
    live_script = _fake_live_script(tmp_path)

    proc = _run_rehearsal(
        tmp_path,
        start_live="required",
        port=port,
        live_cmd=f"{sys.executable} {live_script} {port}",
        extra_env={
            "COHOST_VIBER_REHEARSAL_STIMULATE": "1",
            "COHOST_VIBER_REHEARSAL_VIBER_GUARD_CHAT": "0",
        },
    )

    assert proc.returncode == 0
    summary = json.loads((tmp_path / "out" / "live_rehearsal_summary.json").read_text())
    trigger = summary["stimulus"]["cohost_trigger"]
    assert trigger["enabled"] is True
    assert trigger["sent"] is False
    assert trigger["reason"] == "skipped_for_socket_protocol:tcp"
    assert summary["stimulus"]["viber_guard_chat"]["enabled"] is False


def test_live_rehearsal_blocks_when_socket_missing_and_start_disabled(
    tmp_path: Path,
) -> None:
    proc = _run_rehearsal(tmp_path, start_live="never", port=_free_port())

    assert proc.returncode == 1
    assert "live socket missing" in proc.stderr
    assert not (tmp_path / "out" / "live_rehearsal_summary.json").exists()


def test_live_rehearsal_propagates_matrix_failure(
    tmp_path: Path,
) -> None:
    port = _free_port()
    live_script = _fake_live_script(tmp_path)

    proc = _run_rehearsal(
        tmp_path,
        start_live="required",
        port=port,
        live_cmd=f"{sys.executable} {live_script} {port}",
        matrix_rc=1,
    )

    assert proc.returncode == 1
    assert "FAIL check_cohost_viber_live_rehearsal" in proc.stderr
    summary = json.loads((tmp_path / "out" / "live_rehearsal_summary.json").read_text())
    assert summary["ok"] is False
    assert summary["matrix"]["checks"]["flx4"]["ok"] is False
    assert summary["physical"]["diagnosis"] == "missing_physical_proof"
    assert (
        summary["physical"]["action_hint"]
        == "play_audible_deck_audio_and_move_a_fader_or_knob_within_the_proof_window"
    )
    assert summary["physical"]["proof_legs_passed"] == 2
    assert summary["physical"]["proof_legs_total"] == 5
    proof_legs = {leg["id"]: leg["status"] for leg in summary["physical"]["proof_legs"]}
    assert proof_legs["audible_audio"] == "missing"
    assert proof_legs["deck_identity"] == "missing"
    assert proof_legs["deck_pair_audio_capture"] == "missing"
    assert summary["physical"]["checks"] == {
        "controller_connected": True,
        "deck_state_resolved": False,
        "deck_state_pair_resolved": False,
        "recent_moves_seen": False,
        "audio_observed": False,
        "deck_pair_capture_configured": False,
        "deck_audio_capture_both_active": False,
    }
    assert summary["physical"]["operator_actions"][0]["code"] == "play_audible_audio"
    assert summary["next_operator_action"] == {
        "code": "play_audible_audio",
        "source": "physical",
        "detail": "Play audible DJ app output.",
        "recommended_command": (
            "COHOST_VIBER_REHEARSAL_PROOF_ATTEMPTS=3 "
            "COHOST_VIBER_REHEARSAL_MATRIX_MODE=first-pass "
            "COHOST_VIBER_REHEARSAL_DIRECT_MIDI_PROBE_S=3 "
            "COHOST_VIBER_REHEARSAL_START_LIVE=required "
            "COHOST_VIBER_REHEARSAL_FLX4=required "
            "bash scripts/release/check_cohost_viber_live_rehearsal.sh"
        ),
    }
    assert "next_action=play_audible_audio" in proc.stderr
    assert "recommended_command=COHOST_VIBER_REHEARSAL_PROOF_ATTEMPTS=3" in proc.stderr


def test_live_rehearsal_preserves_specific_matrix_flx4_action(
    tmp_path: Path,
) -> None:
    port = _free_port()
    live_script = _fake_live_script(tmp_path)

    proc = _run_rehearsal(
        tmp_path,
        start_live="required",
        port=port,
        live_cmd=f"{sys.executable} {live_script} {port}",
        matrix_rc=1,
        extra_env={"FAKE_MATRIX_FLX4_NEXT_ACTION_CODE": "prove_os_midi_motion"},
    )

    assert proc.returncode == 1
    assert "next_action=prove_os_midi_motion" in proc.stderr
    summary = json.loads((tmp_path / "out" / "live_rehearsal_summary.json").read_text())
    assert summary["next_operator_action"] == {
        "code": "prove_os_midi_motion",
        "source": "flx4",
        "detail": "FLX4 says prove_os_midi_motion.",
        "diagnostic_commands": [
            "python scripts/sniff_controller.py --port DDJ-FLX4 --seconds 10 --mode callback"
        ],
        "recommended_command": (
            "COHOST_VIBER_REHEARSAL_MATRIX_MODE=first-pass "
            "COHOST_VIBER_REHEARSAL_START_LIVE=required "
            "COHOST_VIBER_REHEARSAL_FLX4=required "
            "bash scripts/release/check_cohost_viber_live_rehearsal.sh"
        ),
    }
    assert [action["code"] for action in summary["operator_action_queue"][:2]] == [
        "prove_os_midi_motion",
        "play_audible_audio",
    ]
    runbook = (tmp_path / "out" / "operator_action_runbook.sh").read_text()
    assert "python scripts/sniff_controller.py --port DDJ-FLX4 --seconds 10" in runbook


def test_live_rehearsal_preserves_audio_evidence_mode_for_physical_retry(
    tmp_path: Path,
) -> None:
    port = _free_port()
    live_script = _fake_live_script(tmp_path)

    proc = _run_rehearsal(
        tmp_path,
        start_live="required",
        port=port,
        live_cmd=f"{sys.executable} {live_script} {port}",
        matrix_rc=1,
        extra_env={"COHOST_VIBER_REHEARSAL_MATRIX_MODE": "audio-evidence"},
    )

    assert proc.returncode == 1
    assert "matrix_mode=audio-evidence" in proc.stderr
    assert (
        "recommended_command=COHOST_VIBER_REHEARSAL_PROOF_ATTEMPTS=3 "
        "COHOST_VIBER_REHEARSAL_MATRIX_MODE=audio-evidence" in proc.stderr
    )
    summary = json.loads((tmp_path / "out" / "live_rehearsal_summary.json").read_text())
    assert summary["matrix_mode"] == "audio-evidence"
    assert summary["matrix"]["mode"] == "audio-evidence"
    assert summary["next_operator_action"]["recommended_command"] == (
        "COHOST_VIBER_REHEARSAL_PROOF_ATTEMPTS=3 "
        "COHOST_VIBER_REHEARSAL_MATRIX_MODE=audio-evidence "
        "COHOST_VIBER_REHEARSAL_DIRECT_MIDI_PROBE_S=3 "
        "COHOST_VIBER_REHEARSAL_START_LIVE=required "
        "COHOST_VIBER_REHEARSAL_FLX4=required "
        "bash scripts/release/check_cohost_viber_live_rehearsal.sh"
    )


def test_live_rehearsal_retries_physical_proof_until_ready(
    tmp_path: Path,
) -> None:
    port = _free_port()
    live_script = _fake_live_script(tmp_path)

    proc = _run_rehearsal(
        tmp_path,
        start_live="required",
        port=port,
        live_cmd=f"{sys.executable} {live_script} {port}",
        matrix_rc=1,
        extra_env={
            "COHOST_VIBER_REHEARSAL_PROOF_ATTEMPTS": "2",
            "COHOST_VIBER_REHEARSAL_PROOF_RETRY_SLEEP_S": "0",
            "FAKE_MATRIX_PASS_ON_ATTEMPT": "2",
        },
    )

    assert proc.returncode == 0
    assert "attempt 1/2" in proc.stdout
    assert "attempt 2/2" in proc.stdout
    summary = json.loads((tmp_path / "out" / "live_rehearsal_summary.json").read_text())
    assert summary["ok"] is True
    assert summary["attempt_count"] == 2
    assert summary["proof_attempts_requested"] == 2
    assert summary["attempts_jsonl"] == str(tmp_path / "out" / "matrix_attempts.jsonl")
    assert summary["final_attempt"] == 2
    assert summary["attempts"][0]["rc"] == 1
    assert summary["attempts"][0]["retryable_physical_proof"] is True
    assert summary["attempts"][0]["next_action"]["code"] == "play_audible_audio"
    assert summary["attempts"][0]["matrix_mode"] == "first-pass"
    assert summary["attempts"][0]["flx4_checks"] == {
        "controller_connected": True,
        "deck_state_resolved": False,
        "deck_state_pair_resolved": False,
        "recent_moves_seen": False,
        "audio_observed": False,
        "deck_pair_capture_configured": False,
        "deck_audio_capture_both_active": False,
    }
    assert summary["attempts"][0]["flx4_top_blockers"] == [
        "live master audio was not observed above the audible floor"
    ]
    assert summary["attempts"][0]["flx4_operator_actions"][0]["code"] == "play_audible_audio"
    assert summary["attempts"][0]["autopilot_first_pass_clean"] is True
    assert summary["attempts"][0]["autopilot_reprompt_debt"] == 0
    assert summary["attempts"][0]["autopilot_audio_evidence_debt"] == 0
    assert summary["attempts"][0]["proof_missing_legs"] == [
        "audible_audio",
        "deck_identity",
        "deck_pair_audio_capture",
    ]
    assert summary["attempts"][0]["direct_midi_sampling"] == "concurrent_with_live_context"
    assert summary["attempts"][0]["direct_midi_motion_observed"] is False
    assert summary["attempts"][0]["direct_midi_frames"] == 0
    assert summary["attempts"][0]["midi_motion_diagnosis"] == "no_direct_midi_motion_observed"
    assert summary["attempts"][1]["rc"] == 0
    assert summary["matrix"]["attempt"] == "2"
    assert summary["matrix_summary"].endswith("matrix-attempt-02/matrix_summary.json")
    assert summary["physical"]["ok"] is True


def test_live_rehearsal_promotes_repeated_missing_direct_midi_motion(
    tmp_path: Path,
) -> None:
    port = _free_port()
    live_script = _fake_live_script(tmp_path)

    proc = _run_rehearsal(
        tmp_path,
        start_live="required",
        port=port,
        live_cmd=f"{sys.executable} {live_script} {port}",
        matrix_rc=1,
        extra_env={
            "COHOST_VIBER_REHEARSAL_PROOF_ATTEMPTS": "2",
            "COHOST_VIBER_REHEARSAL_PROOF_RETRY_SLEEP_S": "0",
        },
    )

    assert proc.returncode == 1
    assert "proof_attempts=2/2" in proc.stderr
    assert "next_action=prove_os_midi_motion" in proc.stderr
    summary = json.loads((tmp_path / "out" / "live_rehearsal_summary.json").read_text())
    assert summary["attempt_count"] == 2
    assert [attempt["direct_midi_frames"] for attempt in summary["attempts"]] == [0, 0]
    assert {
        attempt["direct_midi_sampling"] for attempt in summary["attempts"]
    } == {"concurrent_with_live_context"}
    assert summary["next_operator_action"]["code"] == "prove_os_midi_motion"
    assert "Across 2 proof attempts" in summary["next_operator_action"]["detail"]
    assert "0 FLX4 frames" in summary["next_operator_action"]["detail"]
    assert summary["next_operator_action"]["diagnostic_commands"] == [
        "python scripts/sniff_controller.py --port DDJ-FLX4 --seconds 10 --mode callback",
        "python scripts/sniff_controller.py --port DDJ-FLX4 --seconds 10 --mode poll",
    ]
    assert summary["operator_action_queue"][0]["code"] == "prove_os_midi_motion"
    assert "play_audible_audio" in [
        action["code"] for action in summary["operator_action_queue"]
    ]
    runbook = (tmp_path / "out" / "operator_action_runbook.sh").read_text()
    assert "python scripts/sniff_controller.py --port DDJ-FLX4 --seconds 10 --mode callback" in runbook
    assert "RUN_OPERATOR_COMMANDS" in runbook
    assert summary["proof_progress"]["diagnosis"] == "stable_missing_no_direct_midi"
    assert summary["proof_progress"]["direct_midi_trend"] == "stable_zero"
    assert summary["proof_progress"]["recent_moves_trend"] == "stable_missing"
    assert summary["proof_progress"]["audio_trend"] == "stable_missing"


def test_live_rehearsal_promotes_live_midi_listener_gap_after_repeated_direct_motion(
    tmp_path: Path,
) -> None:
    port = _free_port()
    live_script = _fake_live_script(tmp_path)

    proc = _run_rehearsal(
        tmp_path,
        start_live="required",
        port=port,
        live_cmd=f"{sys.executable} {live_script} {port}",
        matrix_rc=1,
        extra_env={
            "COHOST_VIBER_REHEARSAL_PROOF_ATTEMPTS": "2",
            "COHOST_VIBER_REHEARSAL_PROOF_RETRY_SLEEP_S": "0",
            "FAKE_DIRECT_MIDI_FRAMES": "2",
        },
    )

    assert proc.returncode == 1
    assert "proof_attempts=2/2" in proc.stderr
    assert "next_action=restart_live_midi_listener" in proc.stderr
    summary = json.loads((tmp_path / "out" / "live_rehearsal_summary.json").read_text())
    assert summary["attempt_count"] == 2
    assert [attempt["direct_midi_frames"] for attempt in summary["attempts"]] == [2, 2]
    assert summary["next_operator_action"]["code"] == "restart_live_midi_listener"
    assert "direct OS MIDI saw FLX4 frames" in summary["next_operator_action"]["detail"]
    assert "live-context still saw no recent moves" in summary["next_operator_action"]["detail"]
    assert summary["next_operator_action"]["diagnostic_commands"] == [
        "python scripts/sniff_controller.py --port DDJ-FLX4 --seconds 10 --mode callback"
    ]
    assert summary["proof_progress"]["diagnosis"] == "midi_listener_gap"
    assert summary["proof_progress"]["direct_midi_trend"] == "stable_positive"
    assert summary["proof_progress"]["recent_moves_trend"] == "stable_missing"


def test_live_rehearsal_promotes_audio_route_diagnostics_after_repeated_audio_gap(
    tmp_path: Path,
) -> None:
    port = _free_port()
    live_script = _fake_live_script(tmp_path)

    proc = _run_rehearsal(
        tmp_path,
        start_live="required",
        port=port,
        live_cmd=f"{sys.executable} {live_script} {port}",
        matrix_rc=1,
        extra_env={
            "COHOST_VIBER_REHEARSAL_PROOF_ATTEMPTS": "2",
            "COHOST_VIBER_REHEARSAL_PROOF_RETRY_SLEEP_S": "0",
            "FAKE_DIRECT_MIDI_FRAMES": "2",
            "FAKE_RECENT_MOVES_SEEN": "1",
            "FAKE_AUDIO_OBSERVED": "0",
        },
    )

    assert proc.returncode == 1
    assert "proof_attempts=2/2" in proc.stderr
    assert "next_action=play_audible_audio" in proc.stderr
    summary = json.loads((tmp_path / "out" / "live_rehearsal_summary.json").read_text())
    assert summary["attempt_count"] == 2
    assert [attempt["direct_midi_frames"] for attempt in summary["attempts"]] == [2, 2]
    assert [attempt["flx4_checks"]["recent_moves_seen"] for attempt in summary["attempts"]] == [
        True,
        True,
    ]
    assert [attempt["flx4_checks"]["audio_observed"] for attempt in summary["attempts"]] == [
        False,
        False,
    ]
    assert summary["next_operator_action"]["code"] == "play_audible_audio"
    assert "controller motion was visible" in summary["next_operator_action"]["detail"]
    assert "live audio stayed below the floor" in summary["next_operator_action"]["detail"]
    assert summary["next_operator_action"]["diagnostic_commands"] == [
        (
            "python -m vibemix library live-context --wait-ready 10 --interval 1 "
            "--timeout 1 --frames 60 --json --out .planning/proofs/live-context-audio-proof.json"
        ),
        "system_profiler SPAudioDataType | grep -i 'BlackHole\\|DDJ-FLX4' -A 8",
    ]
    assert summary["proof_progress"]["diagnosis"] == "audio_route_gap"
    assert summary["proof_progress"]["direct_midi_trend"] == "stable_positive"
    assert summary["proof_progress"]["recent_moves_trend"] == "stable_seen"
    assert summary["proof_progress"]["audio_trend"] == "stable_missing"


def test_live_rehearsal_promotes_stabilize_action_when_physical_proof_regresses(
    tmp_path: Path,
) -> None:
    port = _free_port()
    live_script = _fake_live_script(tmp_path)

    proc = _run_rehearsal(
        tmp_path,
        start_live="required",
        port=port,
        live_cmd=f"{sys.executable} {live_script} {port}",
        matrix_rc=1,
        extra_env={
            "COHOST_VIBER_REHEARSAL_PROOF_ATTEMPTS": "2",
            "COHOST_VIBER_REHEARSAL_PROOF_RETRY_SLEEP_S": "0",
            "FAKE_DIRECT_MIDI_FRAMES": "2,0",
            "FAKE_RECENT_MOVES_SEEN": "1,0",
            "FAKE_AUDIO_OBSERVED": "0,0",
        },
    )

    assert proc.returncode == 1
    assert "proof_progress=regressed" in proc.stderr
    assert "next_action=stabilize_physical_proof" in proc.stderr
    summary = json.loads((tmp_path / "out" / "live_rehearsal_summary.json").read_text())
    assert summary["proof_progress"]["diagnosis"] == "regressed"
    assert summary["proof_progress"]["direct_midi_trend"] == "regressed"
    assert summary["proof_progress"]["recent_moves_trend"] == "regressed"
    assert summary["proof_progress"]["audio_trend"] == "stable_missing"
    assert summary["next_operator_action"]["code"] == "stabilize_physical_proof"
    assert "Repeat the proof" in summary["next_operator_action"]["detail"]
    assert summary["next_operator_action"]["diagnostic_commands"] == [
        "python scripts/sniff_controller.py --port DDJ-FLX4 --seconds 10 --mode callback",
        "python scripts/sniff_controller.py --port DDJ-FLX4 --seconds 10 --mode poll",
    ]


def test_live_rehearsal_promotes_deck_identity_resolution_after_motion_and_audio(
    tmp_path: Path,
) -> None:
    port = _free_port()
    live_script = _fake_live_script(tmp_path)

    proc = _run_rehearsal(
        tmp_path,
        start_live="required",
        port=port,
        live_cmd=f"{sys.executable} {live_script} {port}",
        matrix_rc=1,
        extra_env={
            "COHOST_VIBER_REHEARSAL_PROOF_ATTEMPTS": "2",
            "COHOST_VIBER_REHEARSAL_PROOF_RETRY_SLEEP_S": "0",
            "FAKE_DIRECT_MIDI_FRAMES": "2",
            "FAKE_RECENT_MOVES_SEEN": "1",
            "FAKE_AUDIO_OBSERVED": "1",
            "FAKE_DECK_STATE_RESOLVED": "1",
            "FAKE_DECK_STATE_PAIR_RESOLVED": "0",
            "FAKE_DECK_PAIR_CAPTURE_CONFIGURED": "1",
            "FAKE_DECK_AUDIO_CAPTURE_BOTH_ACTIVE": "1",
        },
    )

    assert proc.returncode == 1
    assert "proof_progress=deck_identity_or_capture_gap" in proc.stderr
    assert "next_action=resolve_deck_identity" in proc.stderr
    summary = json.loads((tmp_path / "out" / "live_rehearsal_summary.json").read_text())
    assert summary["proof_progress"]["diagnosis"] == "deck_identity_or_capture_gap"
    assert summary["next_operator_action"]["code"] == "resolve_deck_identity"
    assert "Deck A/B identity" in summary["next_operator_action"]["detail"]
    assert summary["next_operator_action"]["diagnostic_commands"] == [
        (
            "python -m vibemix library live-context --require-proof --wait-ready 10 "
            "--interval 1 --timeout 1 --frames 90 --json "
            "--out .planning/proofs/live-context-deck-identity-proof.json"
        )
    ]


def test_live_rehearsal_promotes_deck_pair_capture_setup_after_identity_resolves(
    tmp_path: Path,
) -> None:
    port = _free_port()
    live_script = _fake_live_script(tmp_path)

    proc = _run_rehearsal(
        tmp_path,
        start_live="required",
        port=port,
        live_cmd=f"{sys.executable} {live_script} {port}",
        matrix_rc=1,
        extra_env={
            "COHOST_VIBER_REHEARSAL_PROOF_ATTEMPTS": "2",
            "COHOST_VIBER_REHEARSAL_PROOF_RETRY_SLEEP_S": "0",
            "FAKE_DIRECT_MIDI_FRAMES": "2",
            "FAKE_RECENT_MOVES_SEEN": "1",
            "FAKE_AUDIO_OBSERVED": "1",
            "FAKE_DECK_STATE_RESOLVED": "1",
            "FAKE_DECK_STATE_PAIR_RESOLVED": "1",
            "FAKE_DECK_PAIR_CAPTURE_CONFIGURED": "0",
            "FAKE_DECK_AUDIO_CAPTURE_BOTH_ACTIVE": "0",
            "FAKE_FLX4_SETUP_HINT": "1",
        },
    )

    assert proc.returncode == 1
    assert "next_action=configure_deck_pair_capture" in proc.stderr
    summary = json.loads((tmp_path / "out" / "live_rehearsal_summary.json").read_text())
    assert summary["next_operator_action"]["code"] == "configure_deck_pair_capture"
    assert "per-deck audio capture is not configured" in summary["next_operator_action"]["detail"]
    assert summary["next_operator_action"]["recommended_env"] == {
        "VIBEMIX_DECK_AUDIO_CHANNELS": "auto"
    }
    assert summary["next_operator_action"]["setup_hint"]["rule"] == "setup_hint_not_live_audio_proof"
    assert summary["next_operator_action"]["diagnostic_commands"] == [
        (
            "python -m vibemix library live-context --require-proof --wait-ready 10 "
            "--interval 1 --timeout 1 --frames 90 --json "
            "--out .planning/proofs/live-context-deck-capture-proof.json"
        ),
        "system_profiler SPAudioDataType | grep -i 'BlackHole 16ch\\|DDJ-FLX4' -A 8",
    ]
    runbook = (tmp_path / "out" / "operator_action_runbook.sh").read_text()
    assert "set_env VIBEMIX_DECK_AUDIO_CHANNELS auto" in runbook
    assert "+ export ${key}=${value}" in runbook


def test_live_rehearsal_promotes_feeding_both_deck_lanes_when_capture_is_configured(
    tmp_path: Path,
) -> None:
    port = _free_port()
    live_script = _fake_live_script(tmp_path)

    proc = _run_rehearsal(
        tmp_path,
        start_live="required",
        port=port,
        live_cmd=f"{sys.executable} {live_script} {port}",
        matrix_rc=1,
        extra_env={
            "COHOST_VIBER_REHEARSAL_PROOF_ATTEMPTS": "2",
            "COHOST_VIBER_REHEARSAL_PROOF_RETRY_SLEEP_S": "0",
            "FAKE_DIRECT_MIDI_FRAMES": "2",
            "FAKE_RECENT_MOVES_SEEN": "1",
            "FAKE_AUDIO_OBSERVED": "1",
            "FAKE_DECK_STATE_RESOLVED": "1",
            "FAKE_DECK_STATE_PAIR_RESOLVED": "1",
            "FAKE_DECK_PAIR_CAPTURE_CONFIGURED": "1",
            "FAKE_DECK_AUDIO_CAPTURE_BOTH_ACTIVE": "0",
        },
    )

    assert proc.returncode == 1
    assert "next_action=feed_both_deck_lanes" in proc.stderr
    summary = json.loads((tmp_path / "out" / "live_rehearsal_summary.json").read_text())
    assert summary["next_operator_action"]["code"] == "feed_both_deck_lanes"
    assert "deck_audio_capture=A_active+B_active" in summary["next_operator_action"]["detail"]
    assert summary["next_operator_action"]["diagnostic_commands"] == [
        (
            "python -m vibemix library live-context --require-proof --wait-ready 10 "
            "--interval 1 --timeout 1 --frames 90 --json "
            "--out .planning/proofs/live-context-deck-capture-proof.json"
        ),
        "system_profiler SPAudioDataType | grep -i 'BlackHole 16ch\\|DDJ-FLX4' -A 8",
    ]


def test_live_rehearsal_forwards_direct_midi_probe_override(
    tmp_path: Path,
) -> None:
    port = _free_port()
    live_script = _fake_live_script(tmp_path)

    proc = _run_rehearsal(
        tmp_path,
        start_live="required",
        port=port,
        live_cmd=f"{sys.executable} {live_script} {port}",
        extra_env={
            "COHOST_VIBER_REHEARSAL_DIRECT_MIDI_PROBE_S": "5",
            "COHOST_VIBER_REHEARSAL_DIRECT_MIDI_PROBE_MODE": "poll",
            "FAKE_DIRECT_MIDI_FRAMES": "2",
        },
    )

    assert proc.returncode == 0
    assert "this will also run a 5s direct OS-level MIDI probe" in proc.stdout
    summary = json.loads((tmp_path / "out" / "live_rehearsal_summary.json").read_text())
    assert summary["direct_midi_probe_s"] == "5"
    assert summary["direct_midi_probe_mode"] == "poll"
    assert summary["matrix"]["flx4_direct_midi_probe_s"] == "5"
    assert summary["matrix"]["flx4_direct_midi_probe_mode"] == "poll"
    assert summary["physical"]["direct_midi_probe"]["motion_observed"] is True
    assert summary["physical"]["direct_midi_probe"]["sampling"] == "concurrent_with_live_context"
    assert summary["physical"]["direct_midi_probe"]["frames"] == 2
    assert summary["physical"]["midi_motion_diagnosis"] == "direct_midi_motion_observed"


def test_live_rehearsal_prioritizes_autopilot_failure_over_physical_retry(
    tmp_path: Path,
) -> None:
    port = _free_port()
    live_script = _fake_live_script(tmp_path)

    proc = _run_rehearsal(
        tmp_path,
        start_live="required",
        port=port,
        live_cmd=f"{sys.executable} {live_script} {port}",
        matrix_rc=1,
        extra_env={"FAKE_AUTOPILOT_OK": "0", "FAKE_MATRIX_SECONDARY_ACTION": "1"},
    )

    assert proc.returncode == 1
    assert "FAIL check_cohost_viber_live_rehearsal" in proc.stderr
    summary = json.loads((tmp_path / "out" / "live_rehearsal_summary.json").read_text())
    assert summary["activity"]["ok"] is True
    assert summary["physical"]["ok"] is False
    assert summary["next_operator_action"] == {
        "code": "inspect_autopilot",
        "source": "autopilot",
        "detail": "FAIL autopilot",
        "recommended_command": (
            "COHOST_VIBER_FAIL_ON=first-pass bash scripts/release/check_cohost_viber_autopilot.sh"
        ),
    }
    assert [action["code"] for action in summary["operator_action_queue"][:3]] == [
        "inspect_autopilot",
        "review_audio_evidence_debt",
        "play_audible_audio",
    ]
    assert "next_action=inspect_autopilot" in proc.stderr
    assert "actions=3" in proc.stderr


def test_live_rehearsal_prioritizes_runtime_canary_coverage_gap_over_physical_retry(
    tmp_path: Path,
) -> None:
    port = _free_port()
    live_script = _fake_live_script(tmp_path)

    proc = _run_rehearsal(
        tmp_path,
        start_live="required",
        port=port,
        live_cmd=f"{sys.executable} {live_script} {port}",
        matrix_rc=1,
        extra_env={
            "FAKE_RUNTIME_OK": "0",
            "FAKE_RUNTIME_ACTION_CODE": "restore_runtime_canary_coverage",
        },
    )

    assert proc.returncode == 1
    assert "next_action=restore_runtime_canary_coverage" in proc.stderr
    summary = json.loads((tmp_path / "out" / "live_rehearsal_summary.json").read_text())
    assert summary["activity"]["ok"] is True
    assert summary["physical"]["ok"] is False
    assert summary["next_operator_action"] == {
        "code": "restore_runtime_canary_coverage",
        "source": "runtime_canaries",
        "detail": "Runtime canary coverage is incomplete.",
        "recommended_command": "bash scripts/release/check_cohost_viber_runtime_canaries.sh",
        "artifacts": {
            "summary_json": str(
                tmp_path
                / "out"
                / "matrix"
                / "runtime-canaries"
                / "runtime_canaries_summary.json"
            ),
            "manifest": str(
                tmp_path
                / "out"
                / "matrix"
                / "runtime-canaries"
                / "runtime_canaries_manifest.json"
            ),
        },
    }
    assert [action["code"] for action in summary["operator_action_queue"][:2]] == [
        "restore_runtime_canary_coverage",
        "play_audible_audio",
    ]
    runbook = (tmp_path / "out" / "operator_action_runbook.sh").read_text()
    assert "artifact manifest:" in runbook
    assert "runtime_canaries_manifest.json" in runbook


def test_live_rehearsal_requires_current_cohost_and_viber_activity(
    tmp_path: Path,
) -> None:
    port = _free_port()
    live_script = _fake_live_script(tmp_path)

    proc = _run_rehearsal(
        tmp_path,
        start_live="required",
        port=port,
        live_cmd=f"{sys.executable} {live_script} {port}",
        extra_env={"FAKE_COHOST_AI_MESSAGES": "0", "FAKE_VIBER_ROWS": "0"},
    )

    assert proc.returncode == 1
    assert "FAIL check_cohost_viber_live_rehearsal" in proc.stderr
    assert "activity=False" in proc.stderr
    assert "cohost_ai=0" in proc.stderr
    assert "live_coach=0" in proc.stderr
    assert "viber_rows=0" in proc.stderr
    summary = json.loads((tmp_path / "out" / "live_rehearsal_summary.json").read_text())
    assert summary["ok"] is False
    assert summary["matrix"]["ok"] is True
    assert summary["activity"] == {
        "required": True,
        "ok": False,
        "cohost_ai_messages": 0,
        "live_coach_messages": 0,
        "viber_rows": 0,
        "viber_errored_rows": 0,
        "report_json": str(tmp_path / "out" / "matrix" / "autopilot" / "report.json"),
        "error": None,
        "reason": "no_current_live_coach_or_viber_activity",
    }
    assert summary["next_operator_action"]["code"] == "stimulate_cohost_and_viber"
    assert summary["next_operator_action"]["source"] == "activity"
    assert (
        summary["next_operator_action"]["recommended_command"]
        == "COHOST_VIBER_REHEARSAL_STIMULATE=1 "
        "bash scripts/release/check_cohost_viber_live_rehearsal.sh"
    )
    assert "next_action=stimulate_cohost_and_viber" in proc.stderr
    assert "recommended_command=COHOST_VIBER_REHEARSAL_STIMULATE=1" in proc.stderr


def test_live_rehearsal_rejects_errored_viber_activity(
    tmp_path: Path,
) -> None:
    port = _free_port()
    live_script = _fake_live_script(tmp_path)

    proc = _run_rehearsal(
        tmp_path,
        start_live="required",
        port=port,
        live_cmd=f"{sys.executable} {live_script} {port}",
        extra_env={"FAKE_VIBER_ROWS": "1", "FAKE_VIBER_ERRORED_ROWS": "1"},
    )

    assert proc.returncode == 1
    assert "FAIL check_cohost_viber_live_rehearsal" in proc.stderr
    assert "activity=False" in proc.stderr
    assert "viber_errors=1" in proc.stderr
    summary = json.loads((tmp_path / "out" / "live_rehearsal_summary.json").read_text())
    assert summary["ok"] is False
    assert summary["matrix"]["ok"] is True
    assert summary["activity"]["reason"] == "current_viber_activity_errored"
    assert summary["next_operator_action"]["code"] == "fix_viber_backend_error"
    assert (
        summary["next_operator_action"]["recommended_command"]
        == "bash scripts/release/check_cohost_viber_live_rehearsal.sh"
    )


def test_live_rehearsal_can_disable_activity_requirement_for_diagnostics(
    tmp_path: Path,
) -> None:
    port = _free_port()
    live_script = _fake_live_script(tmp_path)

    proc = _run_rehearsal(
        tmp_path,
        start_live="required",
        port=port,
        live_cmd=f"{sys.executable} {live_script} {port}",
        extra_env={
            "COHOST_VIBER_REHEARSAL_REQUIRE_ACTIVITY": "0",
            "FAKE_COHOST_AI_MESSAGES": "0",
            "FAKE_VIBER_ROWS": "0",
        },
    )

    assert proc.returncode == 0
    assert "PASS check_cohost_viber_live_rehearsal" in proc.stdout
    summary = json.loads((tmp_path / "out" / "live_rehearsal_summary.json").read_text())
    assert summary["ok"] is True
    assert summary["activity"]["required"] is False
    assert summary["activity"]["ok"] is True
    assert summary["activity"]["reason"] == "activity_requirement_disabled"
