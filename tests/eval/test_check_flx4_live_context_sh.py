# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

SCRIPT = Path("scripts/release/check_flx4_live_context.sh").resolve()
RECOMMENDED_FLX4_GATE_COMMAND = (
    "COHOST_VIBER_FLX4_WAIT_READY_S=20 "
    "COHOST_VIBER_FLX4_DIRECT_MIDI_PROBE_S=20 "
    "bash scripts/release/check_flx4_live_context.sh"
)


def _fake_bin(
    tmp_path: Path,
    *,
    live_ready: bool,
    physical_missing: bool = False,
    midi_present: bool = True,
    audio_present: bool = True,
    deck_pair_configured: bool = False,
    direct_midi_frames: bool = False,
    accept_bad_audio_causality: bool = False,
    accept_bad_audio_source_detail: bool = False,
) -> tuple[Path, Path]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake_python = bin_dir / "fake-python"
    fake_system_profiler = bin_dir / "system_profiler"
    real_python = sys.executable
    fake_python.write_text(
        f"""#!/usr/bin/env bash
set -euo pipefail
if [ "${{1:-}}" = "-" ]; then
  exec "{real_python}" "$@"
fi
if [ "${{1:-}}" = "scripts/sniff_controller.py" ] && [ "${{2:-}}" = "--list" ]; then
  if [ "{str(midi_present).lower()}" = "true" ]; then
    echo "DDJ-FLX4"
  else
    echo "Built-in MIDI Device"
  fi
  exit 0
fi
if [ "${{1:-}}" = "scripts/sniff_controller.py" ]; then
  if [ "{str(direct_midi_frames).lower()}" = "true" ]; then
    echo '{{"ts": 0.1, "type": "cc", "channel": 0, "data1": 7, "data1_hex": "0x07", "data2": 90}}'
    echo '{{"summary": true, "duration_s": 1.0, "frames": 1, "raw_messages": 1, "unsupported_types": {{}}, "diagnosis": "midi_frames_observed", "next_action": "Use the emitted CC/note rows to map or verify the controller.", "unique_cc": [7], "unique_notes": []}}'
  else
    echo '{{"summary": true, "duration_s": 1.0, "frames": 0, "raw_messages": 0, "unsupported_types": {{}}, "diagnosis": "port_visible_no_supported_midi_frames", "next_action": "Move an EQ knob, fader, jog, or pad while sniffing. If this still shows zero frames, enable controller MIDI output in DJ software or close any app that has exclusive access to the controller port.", "unique_cc": [], "unique_notes": []}}'
  fi
  exit 0
fi
if [ "${{1:-}}" = "-m" ] && [ "${{2:-}}" = "vibemix" ] && [ "${{3:-}}" = "library" ] && [ "${{4:-}}" = "verify-live-reply" ]; then
  reply=""
  for ((i=1; i<=$#; i++)); do
    arg="${{!i}}"
    if [ "$arg" = "--reply" ]; then
      j=$((i+1))
      reply="${{!j}}"
    fi
  done
  "{real_python}" - "$reply" "{str(accept_bad_audio_causality).lower()}" "{str(accept_bad_audio_source_detail).lower()}" <<'PY'
import json
import sys

reply = sys.argv[1]
accept_bad_causal = sys.argv[2] == "true"
accept_bad_source = sys.argv[3] == "true"
if "hollow" in reply:
    payload = {{"ok": True, "violations": [], "reply": reply}}
    print(json.dumps(payload))
    raise SystemExit(0)
if "vocal" in reply or "kick" in reply:
    if accept_bad_source:
        payload = {{"ok": True, "violations": [], "reply": reply}}
        print(json.dumps(payload))
        raise SystemExit(0)
    payload = {{
        "ok": False,
        "violations": ["unsupported_audio_source_detail_claim"],
        "reply": reply,
        "corrected": True,
        "corrected_reply": "I only have a broad listener read from the audio here, not source-level proof.",
    }}
    print(json.dumps(payload))
    raise SystemExit(1)
if accept_bad_causal:
    payload = {{"ok": True, "violations": [], "reply": reply}}
    print(json.dumps(payload))
    raise SystemExit(0)
payload = {{
    "ok": False,
    "violations": ["unsupported_live_outcome_claim"],
    "reply": reply,
    "corrected": True,
    "corrected_reply": "I can't tell from this live proof whether the control caused that.",
}}
print(json.dumps(payload))
raise SystemExit(1)
PY
  exit $?
fi
if [ "${{1:-}}" = "-m" ] && [ "${{2:-}}" = "vibemix" ] && [ "${{3:-}}" = "library" ] && [ "${{4:-}}" = "live-context" ]; then
  out=""
  for ((i=1; i<=$#; i++)); do
    arg="${{!i}}"
    if [ "$arg" = "--out" ]; then
      j=$((i+1))
      out="${{!j}}"
    fi
  done
  if [ -z "$out" ]; then
    echo "missing --out" >&2
    exit 2
  fi
  "{real_python}" - "$out" "{str(live_ready).lower()}" "{str(physical_missing).lower()}" "{str(deck_pair_configured).lower()}" <<'PY'
import json
import sys
from pathlib import Path

out = Path(sys.argv[1])
ready = sys.argv[2] == "true"
physical_missing = sys.argv[3] == "true"
deck_pair_configured = sys.argv[4] == "true"
if physical_missing:
    blockers = [
        "deck_state had no resolved deck row",
        "no recent controller moves were observed",
        "live master audio was not observed above the audible floor",
        "deck_state did not resolve both deck A and deck B",
    ]
    if deck_pair_configured:
        blockers.append("deck_audio_capture did not show active audio on both deck lanes")
    else:
        blockers.append("deck-pair audio capture was not configured in the live packet")
    payload = {{
        "ok": True,
        "frames_seen": 80,
        "readiness": {{
            "ready": False,
            "diagnosis": "missing_physical_proof",
            "checks": {{
                "frames_seen": True,
                "flat_deck_frame_seen": True,
                "controller_connected": True,
                "deck_state_resolved": False,
                "deck_state_pair_resolved": False,
                "recent_moves_seen": False,
                "audio_observed": False,
                "deck_pair_capture_configured": deck_pair_configured,
                "deck_audio_capture_both_active": False,
            }},
            "blockers": blockers,
            "next_action": "Collect the missing live proof legs.",
        }},
    }}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload), encoding="utf-8")
    print(json.dumps(payload))
    raise SystemExit(1)
payload = {{
    "ok": ready,
    "frames_seen": 42 if ready else 0,
    "readiness": {{
        "ready": ready,
        "diagnosis": "ready" if ready else "live_socket_missing",
        "checks": {{
            "controller_connected": ready,
            "recent_moves_seen": ready,
            "audio_observed": ready,
        }},
        "blockers": [] if ready else ["no websocket frames arrived"],
    }},
    "operator_actions": [] if ready else [
        {{
            "code": "start_live_session",
            "detail": "Core proof says start the Vibemix live session.",
        }}
    ],
}}
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(payload), encoding="utf-8")
print(json.dumps(payload))
PY
  if [ "{str(live_ready).lower()}" = "true" ]; then
    exit 0
  fi
  exit 1
fi
exec "{real_python}" "$@"
""",
        encoding="utf-8",
    )
    fake_python.chmod(0o755)
    fake_system_profiler.write_text(
        f"""#!/usr/bin/env bash
cat <<'TXT'
Audio:
  Devices:
    {"DDJ-FLX4" if audio_present else "Built-in Output"}:
      Input Channels: 2
      Manufacturer: AlphaTheta Corporation
      Output Channels: 4
TXT
""",
        encoding="utf-8",
    )
    fake_system_profiler.chmod(0o755)
    return bin_dir, fake_python


def _run_gate(
    tmp_path: Path,
    *,
    live_ready: bool,
    physical_missing: bool = False,
    midi_present: bool = True,
    audio_present: bool = True,
    deck_pair_configured: bool = False,
    direct_midi_frames: bool = False,
    accept_bad_audio_causality: bool = False,
    accept_bad_audio_source_detail: bool = False,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    bin_dir, fake_python = _fake_bin(
        tmp_path,
        live_ready=live_ready,
        physical_missing=physical_missing,
        midi_present=midi_present,
        audio_present=audio_present,
        deck_pair_configured=deck_pair_configured,
        direct_midi_frames=direct_midi_frames,
        accept_bad_audio_causality=accept_bad_audio_causality,
        accept_bad_audio_source_detail=accept_bad_audio_source_detail,
    )
    env = os.environ.copy()
    env.update(
        {
            "PATH": f"{bin_dir}{os.pathsep}{env.get('PATH', '')}",
            "PYTHON": str(fake_python),
            "PYTHONPATH": str(Path("src").resolve()),
            "COHOST_VIBER_FLX4_OUT_DIR": str(tmp_path / "out"),
        }
    )
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=Path.cwd(),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_check_flx4_live_context_passes_when_hardware_and_live_proof_ready(
    tmp_path: Path,
) -> None:
    proc = _run_gate(tmp_path, live_ready=True)

    assert proc.returncode == 0
    assert "PASS check_flx4_live_context" in proc.stdout
    assert "midi_port=DDJ-FLX4" in proc.stdout
    assert "live_ready=True" in proc.stdout
    assert "listener_read_canary=True" in proc.stdout
    assert "audio_causality_rejected=True" in proc.stdout
    assert "audio_source_detail_rejected=True" in proc.stdout
    proof = json.loads((tmp_path / "out" / "live_context_proof.json").read_text())
    assert proof["readiness"]["ready"] is True
    summary = json.loads((tmp_path / "out" / "flx4_live_context_summary.json").read_text())
    assert summary["schema"] == "flx4_live_context_summary_v1"
    assert summary["ok"] is True
    assert summary["diagnosis"] == "ready"
    assert summary["operator_actions"] == []
    assert summary["operator_action_queue"] == []
    assert summary["next_operator_action"] == {
        "code": "ready",
        "source": "flx4",
        "detail": "FLX4 live-context proof is ready.",
    }
    assert summary["operator_action_runbook_sh"] == str(
        tmp_path / "out" / "operator_action_runbook.sh"
    )
    assert summary["operator_actions_json"] == str(tmp_path / "out" / "operator_actions.json")
    operator_actions = json.loads((tmp_path / "out" / "operator_actions.json").read_text())
    assert operator_actions == {
        "source": "flx4",
        "dry_run_default": True,
        "runbook_sh": str(tmp_path / "out" / "operator_action_runbook.sh"),
        "recommended_command": RECOMMENDED_FLX4_GATE_COMMAND,
        "actions": [],
        "next_operator_action": {
            "code": "ready",
            "source": "flx4",
            "detail": "FLX4 live-context proof is ready.",
        },
    }
    runbook = (tmp_path / "out" / "operator_action_runbook.sh").read_text()
    assert "FLX4 live-context operator action runbook" in runbook
    assert "No operator action required; FLX4 proof is ready." in runbook
    assert summary["canaries"]["listener_read"] is True
    assert summary["canaries"]["audio_causality_rejected"] is True
    assert summary["canaries"]["audio_source_detail_rejected"] is True
    assert summary["proof_legs_passed"] == summary["proof_legs_total"] == 8
    assert {leg["status"] for leg in summary["proof_legs"]} == {"pass"}
    good = json.loads((tmp_path / "out" / "listener_read_verification.json").read_text())
    bad_causal = json.loads((tmp_path / "out" / "audio_causality_rejection.json").read_text())
    bad_source = json.loads(
        (tmp_path / "out" / "audio_source_detail_rejection.json").read_text()
    )
    assert good["ok"] is True
    assert "unsupported_live_outcome_claim" in bad_causal["violations"]
    assert "unsupported_audio_source_detail_claim" in bad_source["violations"]


def test_check_flx4_live_context_fails_when_socket_proof_missing(
    tmp_path: Path,
) -> None:
    proc = _run_gate(tmp_path, live_ready=False)

    assert proc.returncode == 1
    assert "FAIL check_flx4_live_context" in proc.stderr
    assert "midi_port=DDJ-FLX4" in proc.stderr
    assert "diagnosis=live_socket_missing" in proc.stderr
    assert "listener_read_canary=skipped" in proc.stderr
    assert "audio_causality_rejected=skipped" in proc.stderr
    assert "audio_source_detail_rejected=skipped" in proc.stderr
    assert "action_hint=start_live_session" in proc.stderr
    proof = json.loads((tmp_path / "out" / "live_context_proof.json").read_text())
    assert proof["readiness"]["ready"] is False
    summary = json.loads((tmp_path / "out" / "flx4_live_context_summary.json").read_text())
    assert summary["ok"] is False
    assert summary["diagnosis"] == "live_socket_missing"
    assert summary["action_hint"] == "start_live_session"
    assert len(summary["operator_actions"]) == 1
    assert summary["operator_actions"][0]["code"] == "start_live_session"
    assert summary["operator_actions"][0]["detail"] == (
        "Core proof says start the Vibemix live session."
    )
    assert summary["top_blockers"] == ["no websocket frames arrived"]
    assert not any("deck_state" in blocker for blocker in summary["top_blockers"])
    assert summary["canaries"]["listener_read"] == "skipped"
    assert summary["proof_legs"][0]["id"] == "live_socket_frames"
    assert summary["proof_legs"][0]["status"] == "missing"


def test_check_flx4_live_context_prioritizes_proof_window_when_audio_and_moves_missing(
    tmp_path: Path,
) -> None:
    proc = _run_gate(tmp_path, live_ready=False, physical_missing=True)

    assert proc.returncode == 1
    assert "FAIL check_flx4_live_context" in proc.stderr
    assert "diagnosis=missing_physical_proof" in proc.stderr
    assert "action_hint=play_audible_deck_audio_and_move_a_fader_or_knob" in proc.stderr
    assert "first_blocker='no recent controller moves were observed'" in proc.stderr
    summary = json.loads((tmp_path / "out" / "flx4_live_context_summary.json").read_text())
    assert summary["diagnosis"] == "missing_physical_proof"
    assert summary["first_blocker"] == "no recent controller moves were observed"
    assert summary["top_blockers"][:2] == [
        "no recent controller moves were observed",
        "live master audio was not observed above the audible floor",
    ]
    assert summary["operator_actions"][0]["code"] == "perform_physical_proof_window"
    assert [item["code"] for item in summary["operator_actions"][1:3]] == [
        "move_controller",
        "play_audible_audio",
    ]
    legs = {leg["id"]: leg["status"] for leg in summary["proof_legs"]}
    assert legs["live_socket_frames"] == "pass"
    assert legs["controller_connected"] == "pass"
    assert legs["recent_controller_move"] == "missing"
    assert legs["audible_audio"] == "missing"
    assert legs["reply_safety_canaries"] == "skipped"


def test_check_flx4_live_context_prioritizes_silent_capture_route(
    tmp_path: Path,
) -> None:
    proc = _run_gate(
        tmp_path,
        live_ready=False,
        physical_missing=True,
        deck_pair_configured=True,
    )

    assert proc.returncode == 1
    assert "FAIL check_flx4_live_context" in proc.stderr
    assert "action_hint=route_dj_audio_to_capture" in proc.stderr
    assert (
        "first_blocker='live master audio was not observed above the audible floor'"
        in proc.stderr
    )
    summary = json.loads((tmp_path / "out" / "flx4_live_context_summary.json").read_text())
    assert summary["action_hint"] == "route_dj_audio_to_capture"
    assert summary["first_blocker"] == "live master audio was not observed above the audible floor"
    assert summary["top_blockers"][:2] == [
        "live master audio was not observed above the audible floor",
        "no recent controller moves were observed",
    ]
    assert summary["operator_actions"][0]["code"] == "route_dj_audio_to_capture"
    assert "perform_physical_proof_window" not in [
        action["code"] for action in summary["operator_actions"]
    ]
    assert "play_audible_audio" not in [action["code"] for action in summary["operator_actions"]]
    assert "receiving silence" in summary["operator_actions"][0]["detail"]
    assert "speaker sound alone is not capture proof" in summary["operator_actions"][0]["detail"]
    assert summary["next_operator_action"]["code"] == "route_dj_audio_to_capture"
    assert summary["next_operator_action"]["source"] == "flx4"
    assert summary["next_operator_action"]["diagnostic_commands"][0].startswith(
        "system_profiler SPAudioDataType"
    )


def test_check_flx4_live_context_splits_direct_midi_from_live_ingest_gap(
    tmp_path: Path,
) -> None:
    proc = _run_gate(
        tmp_path,
        live_ready=False,
        physical_missing=True,
        direct_midi_frames=True,
        extra_env={"COHOST_VIBER_FLX4_DIRECT_MIDI_PROBE_S": "1"},
    )

    assert proc.returncode == 1
    assert "ACTION check_flx4_live_context: for the next 1s" in proc.stdout
    assert "sampling together" in proc.stdout
    assert "direct_midi=True" in proc.stderr
    assert "direct_midi_frames=1" in proc.stderr
    assert "direct_midi_raw=1" in proc.stderr
    assert "direct_midi_unsupported={}" in proc.stderr
    assert "midi_motion_diag=live_midi_ingest_missing" in proc.stderr
    summary = json.loads((tmp_path / "out" / "flx4_live_context_summary.json").read_text())
    assert summary["action_hint"] == "restart_live_midi_listener"
    assert summary["midi_motion_diagnosis"] == "live_midi_ingest_missing"
    assert summary["direct_midi_probe"]["ran"] is True
    assert summary["direct_midi_probe"]["sampling"] == "concurrent_with_live_context"
    assert summary["direct_midi_probe"]["motion_observed"] is True
    assert summary["direct_midi_probe"]["frames"] == 1
    assert summary["direct_midi_probe"]["raw_messages"] == 1
    assert summary["direct_midi_probe"]["unsupported_types"] == {}
    assert summary["direct_midi_probe"]["diagnosis"] == "midi_frames_observed"
    assert summary["direct_midi_probe"]["unique_cc"] == [7]
    assert summary["top_blockers"][0] == (
        "live context did not ingest controller moves even though the direct OS MIDI "
        "probe saw FLX4 frames"
    )
    assert summary["operator_actions"][0]["code"] == "restart_live_midi_listener"
    assert "move_controller" not in [action["code"] for action in summary["operator_actions"]]


def test_check_flx4_live_context_records_direct_midi_probe_no_motion(
    tmp_path: Path,
) -> None:
    proc = _run_gate(
        tmp_path,
        live_ready=False,
        physical_missing=True,
        extra_env={"COHOST_VIBER_FLX4_DIRECT_MIDI_PROBE_S": "1"},
    )

    assert proc.returncode == 1
    assert "direct_midi=False" in proc.stderr
    assert "direct_midi_frames=0" in proc.stderr
    assert "direct_midi_raw=0" in proc.stderr
    assert "direct_midi_unsupported={}" in proc.stderr
    assert "midi_motion_diag=no_direct_midi_motion_observed" in proc.stderr
    assert "action_hint=prove_os_midi_motion" in proc.stderr
    summary = json.loads((tmp_path / "out" / "flx4_live_context_summary.json").read_text())
    assert summary["action_hint"] == "prove_os_midi_motion"
    assert summary["midi_motion_diagnosis"] == "no_direct_midi_motion_observed"
    assert summary["direct_midi_probe"]["sampling"] == "concurrent_with_live_context"
    assert summary["direct_midi_probe"]["motion_observed"] is False
    assert summary["direct_midi_probe"]["frames"] == 0
    assert summary["direct_midi_probe"]["raw_messages"] == 0
    assert summary["direct_midi_probe"]["unsupported_types"] == {}
    assert summary["direct_midi_probe"]["diagnosis"] == "port_visible_no_supported_midi_frames"
    assert "exclusive access" in summary["direct_midi_probe"]["next_action"]
    assert summary["top_blockers"][0] == (
        "direct OS MIDI probe saw no controller frames during the probe window"
    )
    assert summary["operator_actions"][0]["code"] == "prove_os_midi_motion"
    assert summary["operator_actions"][0]["diagnostic_commands"] == [
        "uv run python scripts/sniff_controller.py --port DDJ-FLX4 --seconds 20 --mode callback",
        "uv run python scripts/sniff_controller.py --port DDJ-FLX4 --seconds 20 --mode poll",
    ]
    assert summary["operator_action_queue"][0]["source"] == "flx4"
    assert summary["next_operator_action"]["code"] == "prove_os_midi_motion"
    assert summary["next_operator_action"]["source"] == "flx4"
    assert summary["next_operator_action"]["recommended_command"] == RECOMMENDED_FLX4_GATE_COMMAND
    assert summary["next_operator_action"]["diagnostic_commands"] == [
        "uv run python scripts/sniff_controller.py --port DDJ-FLX4 --seconds 20 --mode callback",
        "uv run python scripts/sniff_controller.py --port DDJ-FLX4 --seconds 20 --mode poll",
    ]
    assert summary["operator_action_runbook_sh"] == str(
        tmp_path / "out" / "operator_action_runbook.sh"
    )
    assert summary["operator_actions_json"] == str(tmp_path / "out" / "operator_actions.json")
    operator_actions = json.loads((tmp_path / "out" / "operator_actions.json").read_text())
    assert operator_actions["source"] == "flx4"
    assert operator_actions["dry_run_default"] is True
    assert operator_actions["runbook_sh"] == str(tmp_path / "out" / "operator_action_runbook.sh")
    assert operator_actions["recommended_command"] == RECOMMENDED_FLX4_GATE_COMMAND
    assert operator_actions["actions"][0]["code"] == "prove_os_midi_motion"
    assert operator_actions["actions"][0]["source"] == "flx4"
    assert operator_actions["next_operator_action"]["code"] == "prove_os_midi_motion"
    assert (
        operator_actions["next_operator_action"]["recommended_command"]
        == RECOMMENDED_FLX4_GATE_COMMAND
    )
    runbook = (tmp_path / "out" / "operator_action_runbook.sh").read_text()
    assert "Set RUN_OPERATOR_COMMANDS=1 to execute diagnostic commands" in runbook
    assert "uv run python scripts/sniff_controller.py --port DDJ-FLX4 --seconds 20 --mode callback" in runbook


def test_check_flx4_live_context_writes_summary_when_midi_port_missing(
    tmp_path: Path,
) -> None:
    proc = _run_gate(tmp_path, live_ready=True, midi_present=False)

    assert proc.returncode == 1
    assert "MIDI port matching DDJ-FLX4 was not found" in proc.stderr
    summary = json.loads((tmp_path / "out" / "flx4_live_context_summary.json").read_text())
    assert summary["ok"] is False
    assert summary["diagnosis"] == "midi_port_missing"
    assert summary["action_hint"] == "connect_ddj_flx4_and_start_live_session"
    assert summary["checks"]["controller_connected"] is False
    assert summary["operator_actions"][0]["code"] == "connect_flx4"
    assert summary["operator_action_queue"][0]["source"] == "flx4"
    assert summary["next_operator_action"]["code"] == "connect_flx4"
    assert summary["next_operator_action"]["recommended_command"] == RECOMMENDED_FLX4_GATE_COMMAND
    operator_actions = json.loads((tmp_path / "out" / "operator_actions.json").read_text())
    assert operator_actions["actions"][0]["code"] == "connect_flx4"
    assert operator_actions["next_operator_action"]["recommended_command"] == (
        RECOMMENDED_FLX4_GATE_COMMAND
    )
    assert summary["canaries"]["listener_read"] == "skipped"


def test_check_flx4_live_context_writes_summary_when_audio_device_missing(
    tmp_path: Path,
) -> None:
    proc = _run_gate(tmp_path, live_ready=True, audio_present=False)

    assert proc.returncode == 1
    assert "Audio device matching DDJ-FLX4 was not found" in proc.stderr
    summary = json.loads((tmp_path / "out" / "flx4_live_context_summary.json").read_text())
    assert summary["ok"] is False
    assert summary["diagnosis"] == "audio_device_missing"
    assert summary["action_hint"] == "connect_or_select_flx4_audio_device"
    assert summary["checks"]["controller_connected"] is True
    assert summary["audio_device_found"] is False
    assert summary["operator_actions"][0]["code"] == "connect_flx4_audio"
    assert summary["operator_action_queue"][0]["source"] == "flx4"
    assert summary["next_operator_action"]["code"] == "connect_flx4_audio"
    assert summary["next_operator_action"]["recommended_command"] == RECOMMENDED_FLX4_GATE_COMMAND
    operator_actions = json.loads((tmp_path / "out" / "operator_actions.json").read_text())
    assert operator_actions["actions"][0]["code"] == "connect_flx4_audio"


def test_check_flx4_live_context_fails_when_audio_causality_canary_is_accepted(
    tmp_path: Path,
) -> None:
    proc = _run_gate(tmp_path, live_ready=True, accept_bad_audio_causality=True)

    assert proc.returncode == 1
    assert "FAIL check_flx4_live_context" in proc.stderr
    assert "listener_read_canary=True" in proc.stderr
    assert "audio_causality_rejected=False" in proc.stderr
    assert "audio_source_detail_rejected=True" in proc.stderr
    bad = json.loads((tmp_path / "out" / "audio_causality_rejection.json").read_text())
    assert bad["ok"] is True
    summary = json.loads((tmp_path / "out" / "flx4_live_context_summary.json").read_text())
    assert summary["ok"] is False
    assert summary["canaries"]["audio_causality_rejected"] is False


def test_check_flx4_live_context_fails_when_audio_source_detail_canary_is_accepted(
    tmp_path: Path,
) -> None:
    proc = _run_gate(tmp_path, live_ready=True, accept_bad_audio_source_detail=True)

    assert proc.returncode == 1
    assert "FAIL check_flx4_live_context" in proc.stderr
    assert "listener_read_canary=True" in proc.stderr
    assert "audio_causality_rejected=True" in proc.stderr
    assert "audio_source_detail_rejected=False" in proc.stderr
    bad = json.loads((tmp_path / "out" / "audio_source_detail_rejection.json").read_text())
    assert bad["ok"] is True
    summary = json.loads((tmp_path / "out" / "flx4_live_context_summary.json").read_text())
    assert summary["ok"] is False
    assert summary["canaries"]["audio_source_detail_rejected"] is False
