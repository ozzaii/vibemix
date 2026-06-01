# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

SCRIPT = Path("scripts/release/check_cohost_viber_matrix.sh").resolve()


def _fake_wrapper_dir(tmp_path: Path) -> Path:
    wrapper_dir = tmp_path / "wrappers"
    wrapper_dir.mkdir()
    (wrapper_dir / "check_cohost_viber_autopilot.sh").write_text(
        """#!/usr/bin/env bash
set -euo pipefail
mkdir -p "${COHOST_VIBER_OUT_DIR}/reprompt-pack" "${COHOST_VIBER_OUT_DIR}/repair-run"
python3 - "${COHOST_VIBER_OUT_DIR}/autopilot_summary.json" "${COHOST_VIBER_OUT_DIR}/report.json" "${COHOST_VIBER_OUT_DIR}/reprompt-pack/manifest.json" "${COHOST_VIBER_OUT_DIR}/reprompt-pack" "${COHOST_VIBER_OUT_DIR}/repair-run/repair_manifest.json" "${COHOST_VIBER_OUT_DIR}/repair-run" <<'PY'
import json
import os
import sys
from pathlib import Path

blocker = int(os.environ.get("FAKE_AUTOPILOT_BLOCKER", "0"))
care = int(os.environ.get("FAKE_AUTOPILOT_CARE", "0"))
watch = int(os.environ.get("FAKE_AUTOPILOT_WATCH", "0"))
fail_on = os.environ.get("COHOST_VIBER_FAIL_ON", "release")
status = "repaired_candidate_ready" if blocker else "clean_with_care" if care else "clean"
first_pass_clean = blocker == 0 and care == 0
issues = []
if blocker:
    issues.append(
        {
            "code": "viber_library_request_live_leak",
            "severity": "blocker",
            "surface": "viber_chat",
            "title": "Viber answered a library request with live-move language",
            "response_id": "viber-1",
            "artifact": "/tmp/viber_meta.json",
        }
    )
if care:
    issues.append(
        {
            "code": "citation_strip_silent",
            "severity": "care",
            "surface": "cohost",
            "title": "Cohost stayed silent on an ungrounded reply",
            "response_id": "0001",
            "artifact": "/tmp/meta.json",
        }
    )
if watch:
    issues.append(
        {
            "code": "no_deck_audio_parts",
            "severity": "watch",
            "surface": "cohost",
            "title": "Turn had no isolated deck audio parts",
            "response_id": "0001",
        }
    )
pack_dir = Path(sys.argv[4])
repair_dir = Path(sys.argv[6])
jobs = []
repair_results = []


def add_job(issue, reply):
    idx = len(jobs) + 1
    job_id = f"{idx:02d}_{issue['surface']}_{issue['code']}_{issue['response_id']}"
    job_dir = pack_dir / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    reprompt_path = job_dir / "reprompt.md"
    reprompt_path.write_text("# reprompt", encoding="utf-8")
    jobs.append({"job_id": job_id, "issue": issue})

    repair_job_dir = repair_dir / job_id
    repair_job_dir.mkdir(parents=True, exist_ok=True)
    candidate_path = repair_job_dir / "candidate.json"
    score_path = repair_job_dir / "score.json"
    candidate = {
        "reply": reply,
        "tools_used": [],
        "tool_trace": [],
        "track_ids": [],
        "move_grades": [],
        "playlist": None,
    }
    score = {"ok": True, "violations": [], "reply": reply}
    candidate_path.write_text(json.dumps(candidate), encoding="utf-8")
    score_path.write_text(json.dumps(score), encoding="utf-8")
    repair_results.append(
        {
            "job_id": job_id,
            "ok": True,
            "candidate_path": str(candidate_path),
            "score_path": str(score_path),
            "violations": [],
        }
    )


for issue in issues:
    if issue["severity"] == "blocker":
        add_job(issue, "I do not have grounded results to show yet.")
    elif issue["severity"] == "care":
        add_job(issue, "")
payload = {
    "schema": "cohost_viber_autopilot_v1",
    "ok": True,
    "gate_ok": (
        (fail_on == "automation")
        or (fail_on == "release" and blocker == 0)
        or (fail_on == "first-pass" and first_pass_clean)
        or (fail_on == "audio-evidence" and blocker == 0)
    ),
    "status": status,
    "release_gate_ok": blocker == 0 and fail_on != "release",
    "first_pass_clean": first_pass_clean,
    "reprompt_debt": blocker + care,
    "audio_evidence_debt": blocker,
    "audio_evidence_debt_by_code": (
        {"viber_library_request_live_leak": blocker} if blocker else {}
    ),
    "global_since_iso": os.environ.get("FAKE_AUTOPILOT_GLOBAL_SINCE")
    or os.environ.get("COHOST_VIBER_GLOBAL_SINCE_ISO")
    or None,
    "initial_issue_counts": {"blocker": blocker, "care": care, "watch": watch},
    "reprompt_jobs": len(jobs),
    "artifacts": {
        "report_json": sys.argv[2],
        "report_md": str(Path(sys.argv[2]).with_suffix(".md")),
        "reprompt_pack": sys.argv[4],
        "repair_run": sys.argv[6] if jobs else None,
    },
}
if os.environ.get("FAKE_AUTOPILOT_SKIP_SUMMARY", "0") in {"0", "false", "False"}:
    Path(sys.argv[1]).write_text(json.dumps(payload), encoding="utf-8")
if os.environ.get("FAKE_AUTOPILOT_SKIP_REPORT", "0") in {"0", "false", "False"}:
    Path(sys.argv[2]).write_text(json.dumps({"issues": issues}), encoding="utf-8")
    Path(sys.argv[2]).with_suffix(".md").write_text("# report", encoding="utf-8")
Path(sys.argv[3]).write_text(
    json.dumps(
        {
            "job_count": len(jobs),
            "jobs": jobs,
        }
    ),
    encoding="utf-8",
)
repair = {
    "schema": "cohost_viber_auto_repair_run_v1",
    "ok": True,
    "job_count": len(jobs),
    "candidate_count": len(jobs),
    "passed": len(jobs),
    "failed": 0,
    "skipped": 0,
    "results": repair_results,
}
Path(sys.argv[5]).write_text(json.dumps(repair), encoding="utf-8")
PY
if [ "${COHOST_VIBER_FAIL_ON:-release}" = "release" ]; then
  echo "FAIL check_cohost_viber_autopilot: release_gate_ok=False" >&2
  exit 1
fi
if [ "${COHOST_VIBER_FAIL_ON:-release}" = "first-pass" ] && [ "${FAKE_AUTOPILOT_BLOCKER:-0}${FAKE_AUTOPILOT_CARE:-0}" != "00" ]; then
  echo "FAIL check_cohost_viber_autopilot: first_pass_clean=False" >&2
  exit 1
fi
if [ "${COHOST_VIBER_FAIL_ON:-release}" = "audio-evidence" ] && [ "${FAKE_AUTOPILOT_BLOCKER:-0}" != "0" ]; then
  echo "FAIL check_cohost_viber_autopilot: audio_evidence_debt=${FAKE_AUTOPILOT_BLOCKER}" >&2
  exit 1
fi
echo "PASS check_cohost_viber_autopilot: gate_ok=True release_gate_ok=False"
exit 0
""",
        encoding="utf-8",
    )
    (wrapper_dir / "check_cohost_viber_corpus_benchmark.sh").write_text(
        """#!/usr/bin/env bash
set -euo pipefail
mkdir -p "${COHOST_VIBER_CORPUS_OUT_DIR}/corpus" "${COHOST_VIBER_CORPUS_OUT_DIR}/benchmark"
python3 - "${COHOST_VIBER_CORPUS_OUT_DIR}/corpus/manifest.json" "${COHOST_VIBER_CORPUS_OUT_DIR}/benchmark/benchmark_manifest.json" <<'PY'
import json
import os
import sys
from pathlib import Path

manifest = {
    "schema": "cohost_viber_failure_corpus_v1",
    "release_ready": False,
    "captured_case_count": 1,
    "policy_canary_count": 6,
    "case_count": 7,
}
benchmark = {
    "schema": "cohost_viber_corpus_benchmark_v1",
    "ok": True,
    "case_count": 7,
    "passed": 7,
    "failed": 0,
}
if os.environ.get("FAKE_CORPUS_SKIP_MANIFEST", "0") in {"0", "false", "False"}:
    Path(sys.argv[1]).write_text(json.dumps(manifest), encoding="utf-8")
if os.environ.get("FAKE_CORPUS_SKIP_BENCHMARK", "0") in {"0", "false", "False"}:
    Path(sys.argv[2]).write_text(json.dumps(benchmark), encoding="utf-8")
PY
if [ "${COHOST_VIBER_CORPUS_FAIL_ON:-release}" = "release" ]; then
  echo "FAIL check_cohost_viber_corpus_benchmark: release_ready=False benchmark_ok=True" >&2
  exit 1
fi
echo "PASS check_cohost_viber_corpus_benchmark: release_ready=False benchmark_ok=True"
exit 0
""",
        encoding="utf-8",
    )
    (wrapper_dir / "check_cohost_viber_runtime_canaries.sh").write_text(
        """#!/usr/bin/env bash
set -euo pipefail
mkdir -p "${COHOST_VIBER_RUNTIME_CANARY_OUT_DIR}"
if [ "${FAKE_RUNTIME_SKIP_SUMMARY:-0}" != "0" ]; then
  echo "PASS check_cohost_viber_runtime_canaries: ok=True canaries=6 exercised=6 passed=6 failed=0 missing=0"
  exit 0
fi
python3 - "${COHOST_VIBER_RUNTIME_CANARY_OUT_DIR}/runtime_canaries_summary.json" "${FAKE_RUNTIME_RC:-0}" <<'PY'
import json
import os
import sys
from pathlib import Path

rc = int(sys.argv[2])
missing = int(os.environ.get("FAKE_RUNTIME_MISSING", "0"))
effective_rc = 1 if missing else rc
passed = 6 - missing if missing else (6 if effective_rc == 0 else 5)
failed = 0 if missing or effective_rc == 0 else 1
payload = {
    "schema": "cohost_viber_runtime_canaries_v1",
    "ok": effective_rc == 0,
    "rc": effective_rc,
    "canary_count": 6,
    "passed": passed,
    "failed": failed,
    "exercised": passed + failed,
    "coverage_ok": missing == 0,
    "missing_canaries": missing,
    "canaries": [
        {"id": "manual_no_evidence_skips_llm"},
        {"id": "manual_audio_signal_reaches_model"},
        {"id": "audio_causal_guard_strips_before_tts"},
        {"id": "audio_source_detail_guard_strips_before_tts"},
        {"id": "audio_listener_read_survives_before_tts"},
        {"id": "manual_silence_report_is_not_repair"},
    ],
    "artifacts": {
        "manifest": str(Path(sys.argv[1]).with_name("runtime_canaries_manifest.json")),
        "stdout": str(Path(sys.argv[1]).with_name("pytest.stdout.log")),
        "stderr": str(Path(sys.argv[1]).with_name("pytest.stderr.log")),
    },
}
Path(sys.argv[1]).write_text(json.dumps(payload), encoding="utf-8")
Path(payload["artifacts"]["manifest"]).write_text(json.dumps({"canaries": payload["canaries"]}), encoding="utf-8")
PY
if [ "${FAKE_RUNTIME_MISSING:-0}" != "0" ]; then
  echo "FAIL check_cohost_viber_runtime_canaries: ok=False canaries=6 exercised=5 passed=5 failed=0 missing=${FAKE_RUNTIME_MISSING}" >&2
  exit 1
fi
if [ "${FAKE_RUNTIME_RC:-0}" = "0" ]; then
  echo "PASS check_cohost_viber_runtime_canaries: ok=True canaries=6 exercised=6 passed=6 failed=0 missing=0"
  exit 0
fi
echo "FAIL check_cohost_viber_runtime_canaries: ok=False canaries=6 exercised=6 passed=5 failed=1 missing=0" >&2
exit "${FAKE_RUNTIME_RC}"
""",
        encoding="utf-8",
    )
    (wrapper_dir / "check_flx4_live_context.sh").write_text(
        """#!/usr/bin/env bash
set -euo pipefail
mkdir -p "${COHOST_VIBER_FLX4_OUT_DIR}"
python3 - "${COHOST_VIBER_FLX4_OUT_DIR}/flx4_live_context_summary.json" "${FAKE_FLX4_RC:-0}" <<'PY'
import json
import os
import sys
from pathlib import Path

rc = int(sys.argv[2])
direct_midi_s = os.environ.get("COHOST_VIBER_FLX4_DIRECT_MIDI_PROBE_S")
direct_midi_mode = os.environ.get("COHOST_VIBER_FLX4_DIRECT_MIDI_PROBE_MODE")
direct_midi_ran = direct_midi_s not in {None, "", "0", "0.0"}
direct_midi_frames = int(os.environ.get("FAKE_DIRECT_MIDI_FRAMES", "0"))
recent_moves_seen = os.environ.get("FAKE_RECENT_MOVES_SEEN", "1" if rc == 0 else "0") not in {"0", "false", "False"}
audio_observed = os.environ.get("FAKE_AUDIO_OBSERVED", "1" if rc == 0 else "0") not in {"0", "false", "False"}
deck_state_resolved = os.environ.get("FAKE_DECK_STATE_RESOLVED", "1" if rc == 0 else "0") not in {"0", "false", "False"}
deck_state_pair_resolved = os.environ.get("FAKE_DECK_STATE_PAIR_RESOLVED", "1" if rc == 0 else "0") not in {"0", "false", "False"}
deck_pair_capture_configured = os.environ.get("FAKE_DECK_PAIR_CAPTURE_CONFIGURED", "1" if rc == 0 else "0") not in {"0", "false", "False"}
deck_audio_capture_both_active = os.environ.get("FAKE_DECK_AUDIO_CAPTURE_BOTH_ACTIVE", "1" if rc == 0 else "0") not in {"0", "false", "False"}
payload = {
    "schema": "flx4_live_context_summary_v1",
    "ok": rc == 0,
    "diagnosis": "ready" if rc == 0 else "missing_physical_proof",
    "action_hint": "none" if rc == 0 else "play_audible_deck_audio_and_move_a_fader_or_knob_within_the_proof_window",
    "first_blocker": "none" if rc == 0 else "live master audio was not observed above the audible floor",
    "top_blockers": [] if rc == 0 else ["live master audio was not observed above the audible floor"],
    "operator_actions": [] if rc == 0 else [{"code": "play_audible_audio", "detail": "Play audible DJ app output."}],
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
        "jsonl": os.environ["COHOST_VIBER_FLX4_OUT_DIR"] + "/direct_midi_probe.jsonl" if direct_midi_ran else None,
        "stderr": os.environ["COHOST_VIBER_FLX4_OUT_DIR"] + "/direct_midi_probe.stderr.log" if direct_midi_ran else None,
    },
    "midi_motion_diagnosis": (
        "direct_midi_motion_observed"
        if direct_midi_ran and direct_midi_frames > 0
        else "no_direct_midi_motion_observed"
        if direct_midi_ran
        else "not_run"
    ),
    "setup_hint": {
        "status": "rekordbox_route_hint_found",
        "recommended_env": {"VIBEMIX_DECK_AUDIO_CHANNELS": "auto"},
        "next_action": "Start the live session with VIBEMIX_DECK_AUDIO_CHANNELS=auto, play both decks, move a controller, then rerun proof.",
        "rule": "setup_hint_not_live_audio_proof",
    } if os.environ.get("FAKE_FLX4_SETUP_HINT", "0") not in {"0", "false", "False"} else None,
}
Path(sys.argv[1]).write_text(json.dumps(payload), encoding="utf-8")
PY
if [ "${FAKE_FLX4_RC:-0}" = "0" ]; then
  echo "PASS check_flx4_live_context: midi_port=DDJ-FLX4 live_ready=True"
  exit 0
fi
if [ "${FAKE_FLX4_ACTION_STDOUT:-0}" = "1" ]; then
  echo "ACTION check_flx4_live_context: proof window is sampling."
fi
echo "FAIL check_flx4_live_context: midi_port=DDJ-FLX4 diagnosis=live_socket_missing" >&2
exit "${FAKE_FLX4_RC}"
""",
        encoding="utf-8",
    )
    for path in wrapper_dir.iterdir():
        path.chmod(0o755)
    return wrapper_dir


def _run_matrix(
    tmp_path: Path,
    *,
    mode: str,
    flx4: str,
    fake_flx4_rc: int = 0,
    fake_runtime_rc: int = 0,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(
        {
            "COHOST_VIBER_MATRIX_WRAPPER_DIR": str(_fake_wrapper_dir(tmp_path)),
            "COHOST_VIBER_MATRIX_OUT_DIR": str(tmp_path / "out"),
            "COHOST_VIBER_MATRIX_MODE": mode,
            "COHOST_VIBER_MATRIX_FLX4": flx4,
            "FAKE_FLX4_RC": str(fake_flx4_rc),
            "FAKE_RUNTIME_RC": str(fake_runtime_rc),
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


def test_check_cohost_viber_matrix_passes_operator_mode_without_hardware(
    tmp_path: Path,
) -> None:
    proc = _run_matrix(
        tmp_path,
        mode="automation",
        flx4="skip",
        extra_env={"FAKE_AUTOPILOT_GLOBAL_SINCE": "2026-06-01T00:43:04+03:00"},
    )

    assert proc.returncode == 0
    assert "PASS check_cohost_viber_matrix" in proc.stdout
    assert "autopilot=True" in proc.stdout
    assert "corpus=True" in proc.stdout
    assert "runtime=True" in proc.stdout
    assert "flx4=skip" in proc.stdout
    assert "first_pass=True" in proc.stdout
    assert "reprompt_debt=0" in proc.stdout
    assert "audio_evidence_debt=0" in proc.stdout
    assert "next_action=ready" in proc.stdout
    assert "recommended_command=none" in proc.stdout
    summary = json.loads((tmp_path / "out" / "matrix_summary.json").read_text())
    assert summary["ok"] is True
    assert summary["autopilot_fail_on"] == "automation"
    assert summary["corpus_fail_on"] == "automation"
    assert summary["global_since_iso"] == "2026-06-01T00:43:04+03:00"
    assert summary["checks"]["autopilot"]["global_since_iso"] == "2026-06-01T00:43:04+03:00"
    assert summary["checks"]["autopilot"]["first_pass_clean"] is True
    assert summary["checks"]["autopilot"]["reprompt_debt"] == 0
    assert summary["checks"]["autopilot"]["audio_evidence_debt"] == 0
    assert summary["checks"]["runtime_canaries"]["ok"] is True
    assert summary["checks"]["runtime_canaries"]["canary_count"] == 6
    assert summary["checks"]["flx4"]["ran"] is False
    assert summary["next_operator_action"]["code"] == "ready"
    assert summary["operator_action_queue"][0]["code"] == "ready"


def test_check_cohost_viber_matrix_blocks_when_autopilot_summary_is_missing(
    tmp_path: Path,
) -> None:
    proc = _run_matrix(
        tmp_path,
        mode="automation",
        flx4="skip",
        extra_env={"FAKE_AUTOPILOT_SKIP_SUMMARY": "1"},
    )

    assert proc.returncode == 1
    assert "autopilot=False" in proc.stderr
    assert "next_action=restore_autopilot_summary" in proc.stderr
    summary = json.loads((tmp_path / "out" / "matrix_summary.json").read_text())
    autopilot = summary["checks"]["autopilot"]
    assert autopilot["rc"] == 0
    assert autopilot["summary_present"] is False
    assert autopilot["report_present"] is True
    assert summary["next_operator_action"]["code"] == "restore_autopilot_summary"
    assert "did not produce a readable summary JSON" in summary["next_operator_action"]["detail"]
    assert summary["next_operator_action"]["artifacts"] == {
        "summary_json": str(tmp_path / "out" / "autopilot" / "autopilot_summary.json"),
        "report_json": str(tmp_path / "out" / "autopilot" / "report.json"),
        "stdout": str(tmp_path / "out" / "autopilot.stdout.log"),
        "stderr": str(tmp_path / "out" / "autopilot.stderr.log"),
    }
    runbook = (tmp_path / "out" / "operator_action_runbook.sh").read_text()
    assert "artifact summary_json:" in runbook
    assert "autopilot_summary.json" in runbook


def test_check_cohost_viber_matrix_blocks_when_autopilot_report_is_missing(
    tmp_path: Path,
) -> None:
    proc = _run_matrix(
        tmp_path,
        mode="automation",
        flx4="skip",
        extra_env={"FAKE_AUTOPILOT_SKIP_REPORT": "1"},
    )

    assert proc.returncode == 1
    assert "autopilot=False" in proc.stderr
    assert "next_action=restore_autopilot_report" in proc.stderr
    summary = json.loads((tmp_path / "out" / "matrix_summary.json").read_text())
    autopilot = summary["checks"]["autopilot"]
    assert autopilot["rc"] == 0
    assert autopilot["summary_present"] is True
    assert autopilot["report_present"] is False
    assert summary["next_operator_action"]["code"] == "restore_autopilot_report"
    assert "issue report JSON is missing" in summary["next_operator_action"]["detail"]
    runbook = (tmp_path / "out" / "operator_action_runbook.sh").read_text()
    assert "artifact report_json:" in runbook
    assert "report.json" in runbook


def test_check_cohost_viber_matrix_blocks_when_corpus_artifacts_are_missing(
    tmp_path: Path,
) -> None:
    proc = _run_matrix(
        tmp_path,
        mode="automation",
        flx4="skip",
        extra_env={
            "FAKE_CORPUS_SKIP_MANIFEST": "1",
            "FAKE_CORPUS_SKIP_BENCHMARK": "1",
        },
    )

    assert proc.returncode == 1
    assert "corpus=False" in proc.stderr
    assert "next_action=restore_corpus_benchmark_artifacts" in proc.stderr
    summary = json.loads((tmp_path / "out" / "matrix_summary.json").read_text())
    corpus = summary["checks"]["corpus"]
    assert corpus["rc"] == 0
    assert corpus["manifest_present"] is False
    assert corpus["benchmark_present"] is False
    action = summary["next_operator_action"]
    assert action["code"] == "restore_corpus_benchmark_artifacts"
    assert "missing=manifest_json,benchmark_json" in action["detail"]
    assert action["artifacts"] == {
        "manifest_json": str(tmp_path / "out" / "corpus" / "corpus" / "manifest.json"),
        "benchmark_json": str(
            tmp_path / "out" / "corpus" / "benchmark" / "benchmark_manifest.json"
        ),
        "stdout": str(tmp_path / "out" / "corpus.stdout.log"),
        "stderr": str(tmp_path / "out" / "corpus.stderr.log"),
    }
    runbook = (tmp_path / "out" / "operator_action_runbook.sh").read_text()
    assert "artifact benchmark_json:" in runbook
    assert "benchmark_manifest.json" in runbook


def test_check_cohost_viber_matrix_first_pass_mode_blocks_reprompt_debt(
    tmp_path: Path,
) -> None:
    proc = _run_matrix(
        tmp_path,
        mode="first-pass",
        flx4="skip",
        extra_env={"FAKE_AUTOPILOT_CARE": "1"},
    )

    assert proc.returncode == 1
    assert "FAIL check_cohost_viber_matrix" in proc.stderr
    assert "autopilot=False" in proc.stderr
    assert "corpus=True" in proc.stderr
    assert "first_pass=False" in proc.stderr
    assert "reprompt_debt=1" in proc.stderr
    assert "audio_evidence_debt=0" in proc.stderr
    assert "next_action=inspect_autopilot" in proc.stderr
    assert "recommended_command=COHOST_VIBER_FAIL_ON=first-pass" in proc.stderr
    summary = json.loads((tmp_path / "out" / "matrix_summary.json").read_text())
    assert summary["mode"] == "first-pass"
    assert summary["autopilot_fail_on"] == "first-pass"
    assert summary["corpus_fail_on"] == "automation"
    assert summary["checks"]["autopilot"]["ok"] is False
    assert summary["checks"]["autopilot"]["first_pass_clean"] is False
    assert summary["checks"]["autopilot"]["reprompt_debt"] == 1
    assert summary["checks"]["autopilot"]["audio_evidence_debt"] == 0
    assert summary["checks"]["corpus"]["ok"] is True
    assert summary["next_operator_action"] == {
        "code": "inspect_autopilot",
        "source": "autopilot",
        "detail": "FAIL check_cohost_viber_autopilot: first_pass_clean=False",
        "recommended_command": (
            "COHOST_VIBER_FAIL_ON=first-pass "
            "bash scripts/release/check_cohost_viber_autopilot.sh"
        ),
    }


def test_check_cohost_viber_matrix_audio_evidence_mode_allows_non_audio_care(
    tmp_path: Path,
) -> None:
    proc = _run_matrix(
        tmp_path,
        mode="audio-evidence",
        flx4="skip",
        extra_env={"FAKE_AUTOPILOT_CARE": "1"},
    )

    assert proc.returncode == 0
    assert "PASS check_cohost_viber_matrix" in proc.stdout
    assert "audio_evidence_debt=0" in proc.stdout
    assert "next_action=ready" in proc.stdout
    summary = json.loads((tmp_path / "out" / "matrix_summary.json").read_text())
    assert summary["mode"] == "audio-evidence"
    assert summary["autopilot_fail_on"] == "audio-evidence"
    assert summary["corpus_fail_on"] == "automation"
    assert summary["checks"]["autopilot"]["ok"] is True
    assert summary["checks"]["autopilot"]["first_pass_clean"] is False
    assert summary["checks"]["autopilot"]["audio_evidence_debt"] == 0
    assert summary["next_operator_action"]["code"] == "ready"
    assert [action["code"] for action in summary["operator_action_queue"]] == [
        "ready",
        "review_autopilot_care",
    ]


def test_check_cohost_viber_matrix_prioritizes_audio_debt_failure(
    tmp_path: Path,
) -> None:
    proc = _run_matrix(
        tmp_path,
        mode="first-pass",
        flx4="skip",
        extra_env={"FAKE_AUTOPILOT_BLOCKER": "1"},
    )

    assert proc.returncode == 1
    assert "next_action=inspect_audio_evidence_debt" in proc.stderr
    assert "audio_evidence_debt=1" in proc.stderr
    summary = json.loads((tmp_path / "out" / "matrix_summary.json").read_text())
    assert summary["next_operator_action"]["code"] == "inspect_audio_evidence_debt"
    assert summary["next_operator_action"]["source"] == "autopilot"
    assert "Audio/live evidence debt=1" in summary["next_operator_action"]["detail"]
    assert "first_issue=viber_library_request_live_leak" in summary["next_operator_action"]["detail"]
    assert summary["next_operator_action"]["artifacts"]["source_artifact"] == "/tmp/viber_meta.json"
    assert summary["operator_action_queue"][0]["code"] == "inspect_audio_evidence_debt"


def test_check_cohost_viber_matrix_blocks_release_mode_on_release_gates(
    tmp_path: Path,
) -> None:
    proc = _run_matrix(tmp_path, mode="release", flx4="skip")

    assert proc.returncode == 1
    assert "FAIL check_cohost_viber_matrix" in proc.stderr
    assert "autopilot=False" in proc.stderr
    assert "corpus=False" in proc.stderr
    assert "runtime=True" in proc.stderr
    assert "next_action=inspect_autopilot" in proc.stderr
    assert (
        "recommended_command=COHOST_VIBER_FAIL_ON=release "
        "bash scripts/release/check_cohost_viber_autopilot.sh" in proc.stderr
    )
    summary = json.loads((tmp_path / "out" / "matrix_summary.json").read_text())
    assert summary["ok"] is False
    assert summary["checks"]["autopilot"]["rc"] == 1
    assert summary["checks"]["corpus"]["rc"] == 1
    assert summary["checks"]["runtime_canaries"]["rc"] == 0
    assert summary["next_operator_action"]["code"] == "inspect_autopilot"
    assert summary["next_operator_action"]["source"] == "autopilot"
    assert (
        summary["next_operator_action"]["recommended_command"]
        == "COHOST_VIBER_FAIL_ON=release bash scripts/release/check_cohost_viber_autopilot.sh"
    )
    assert [action["code"] for action in summary["operator_action_queue"][:2]] == [
        "inspect_autopilot",
        "inspect_corpus",
    ]


def test_check_cohost_viber_matrix_blocks_when_required_flx4_fails(
    tmp_path: Path,
) -> None:
    proc = _run_matrix(tmp_path, mode="automation", flx4="required", fake_flx4_rc=1)

    assert proc.returncode == 1
    assert "FAIL check_cohost_viber_matrix" in proc.stderr
    assert "flx4=False" in proc.stderr
    assert "next_action=play_audible_audio" in proc.stderr
    assert (
        "recommended_command=COHOST_VIBER_REHEARSAL_MATRIX_MODE=automation "
        "COHOST_VIBER_REHEARSAL_START_LIVE=required" in proc.stderr
    )
    summary = json.loads((tmp_path / "out" / "matrix_summary.json").read_text())
    assert summary["checks"]["flx4"]["ran"] is True
    assert summary["checks"]["flx4"]["required"] is True
    assert summary["checks"]["flx4"]["rc"] == 1
    assert summary["checks"]["flx4"]["diagnosis"] == "missing_physical_proof"
    assert (
        summary["checks"]["flx4"]["action_hint"]
        == "play_audible_deck_audio_and_move_a_fader_or_knob_within_the_proof_window"
    )
    assert summary["checks"]["flx4"]["first_blocker"] == (
        "live master audio was not observed above the audible floor"
    )
    assert summary["checks"]["flx4"]["proof_legs_passed"] == 2
    assert summary["checks"]["flx4"]["proof_legs_total"] == 5
    proof_legs = {leg["id"]: leg["status"] for leg in summary["checks"]["flx4"]["proof_legs"]}
    assert proof_legs["audible_audio"] == "missing"
    assert proof_legs["deck_identity"] == "missing"
    assert proof_legs["deck_pair_audio_capture"] == "missing"
    assert summary["checks"]["flx4"]["checks"] == {
        "controller_connected": True,
        "deck_state_resolved": False,
        "deck_state_pair_resolved": False,
        "recent_moves_seen": False,
        "audio_observed": False,
        "deck_pair_capture_configured": False,
        "deck_audio_capture_both_active": False,
    }
    assert summary["checks"]["flx4"]["direct_midi_probe"]["ran"] is False
    assert summary["checks"]["flx4"]["midi_motion_diagnosis"] == "not_run"
    assert summary["checks"]["flx4"]["operator_actions"][0]["code"] == "play_audible_audio"
    assert summary["operator_actions_json"] == str(tmp_path / "out" / "operator_actions.json")
    assert summary["operator_runbook_sh"] == str(tmp_path / "out" / "operator_action_runbook.sh")
    actions_payload = json.loads((tmp_path / "out" / "operator_actions.json").read_text())
    assert actions_payload["source"] == "matrix"
    assert actions_payload["runbook_sh"] == str(
        tmp_path / "out" / "operator_action_runbook.sh"
    )
    assert actions_payload["dry_run_default"] is True
    assert actions_payload["actions"][0]["code"] == "play_audible_audio"
    runbook = (tmp_path / "out" / "operator_action_runbook.sh").read_text()
    assert "Set RUN_OPERATOR_COMMANDS=1 to execute" in runbook
    assert "COHOST_VIBER_REHEARSAL_MATRIX_MODE=automation" in runbook
    assert f"runbook={tmp_path / 'out' / 'operator_action_runbook.sh'}" in proc.stderr
    assert summary["next_operator_action"] == {
        "code": "play_audible_audio",
        "source": "flx4",
        "detail": "Play audible DJ app output.",
        "recommended_command": (
            "COHOST_VIBER_REHEARSAL_MATRIX_MODE=automation "
            "COHOST_VIBER_REHEARSAL_START_LIVE=required "
            "COHOST_VIBER_REHEARSAL_FLX4=required "
            "bash scripts/release/check_cohost_viber_live_rehearsal.sh"
        ),
    }
    assert summary["operator_action_queue"][0]["code"] == "play_audible_audio"


def test_check_cohost_viber_matrix_prefers_flx4_summary_over_action_line(
    tmp_path: Path,
) -> None:
    proc = _run_matrix(
        tmp_path,
        mode="automation",
        flx4="required",
        fake_flx4_rc=1,
        extra_env={"FAKE_FLX4_ACTION_STDOUT": "1"},
    )

    assert proc.returncode == 1
    assert "flx4: FAIL check_flx4_live_context" in proc.stderr
    assert "flx4: ACTION check_flx4_live_context" not in proc.stderr
    summary = json.loads((tmp_path / "out" / "matrix_summary.json").read_text())
    assert summary["checks"]["flx4"]["summary"].startswith("FAIL check_flx4_live_context")


def test_check_cohost_viber_matrix_preserves_audio_evidence_mode_for_flx4_retry(
    tmp_path: Path,
) -> None:
    proc = _run_matrix(tmp_path, mode="audio-evidence", flx4="required", fake_flx4_rc=1)

    assert proc.returncode == 1
    assert "next_action=play_audible_audio" in proc.stderr
    assert (
        "recommended_command=COHOST_VIBER_REHEARSAL_MATRIX_MODE=audio-evidence "
        "COHOST_VIBER_REHEARSAL_START_LIVE=required" in proc.stderr
    )
    summary = json.loads((tmp_path / "out" / "matrix_summary.json").read_text())
    assert summary["mode"] == "audio-evidence"
    assert summary["next_operator_action"]["recommended_command"] == (
        "COHOST_VIBER_REHEARSAL_MATRIX_MODE=audio-evidence "
        "COHOST_VIBER_REHEARSAL_START_LIVE=required "
        "COHOST_VIBER_REHEARSAL_FLX4=required "
        "bash scripts/release/check_cohost_viber_live_rehearsal.sh"
    )
    assert summary["operator_action_queue"][0]["recommended_command"] == (
        summary["next_operator_action"]["recommended_command"]
    )


def test_check_cohost_viber_matrix_projects_direct_midi_probe(
    tmp_path: Path,
) -> None:
    proc = _run_matrix(
        tmp_path,
        mode="automation",
        flx4="required",
        fake_flx4_rc=1,
        extra_env={
            "COHOST_VIBER_FLX4_DIRECT_MIDI_PROBE_S": "4",
            "COHOST_VIBER_FLX4_DIRECT_MIDI_PROBE_MODE": "poll",
            "FAKE_DIRECT_MIDI_FRAMES": "2",
        },
    )

    assert proc.returncode == 1
    assert "direct_midi=True" in proc.stderr
    assert "midi_motion_diag=direct_midi_motion_observed" in proc.stderr
    summary = json.loads((tmp_path / "out" / "matrix_summary.json").read_text())
    flx4 = summary["checks"]["flx4"]
    assert flx4["direct_midi_probe"]["ran"] is True
    assert flx4["direct_midi_probe"]["seconds"] == "4"
    assert flx4["direct_midi_probe"]["mode"] == "poll"
    assert flx4["direct_midi_probe"]["sampling"] == "concurrent_with_live_context"
    assert flx4["direct_midi_probe"]["motion_observed"] is True
    assert flx4["direct_midi_probe"]["frames"] == 2
    assert flx4["midi_motion_diagnosis"] == "direct_midi_motion_observed"
    assert summary["next_operator_action"]["code"] == "restart_live_midi_listener"
    assert summary["next_operator_action"]["diagnostic_commands"] == [
        "python scripts/sniff_controller.py --port DDJ-FLX4 --seconds 10 --mode poll"
    ]


def test_check_cohost_viber_matrix_promotes_direct_midi_diagnostic_when_probe_sees_no_motion(
    tmp_path: Path,
) -> None:
    proc = _run_matrix(
        tmp_path,
        mode="automation",
        flx4="required",
        fake_flx4_rc=1,
        extra_env={"COHOST_VIBER_FLX4_DIRECT_MIDI_PROBE_S": "4"},
    )

    assert proc.returncode == 1
    assert "next_action=prove_os_midi_motion" in proc.stderr
    summary = json.loads((tmp_path / "out" / "matrix_summary.json").read_text())
    assert summary["next_operator_action"]["code"] == "prove_os_midi_motion"
    assert summary["operator_action_queue"][0]["code"] == "prove_os_midi_motion"
    assert summary["next_operator_action"]["diagnostic_commands"] == [
        "python scripts/sniff_controller.py --port DDJ-FLX4 --seconds 10 --mode callback",
        "python scripts/sniff_controller.py --port DDJ-FLX4 --seconds 10 --mode poll",
    ]


def test_check_cohost_viber_matrix_promotes_deck_identity_resolution(
    tmp_path: Path,
) -> None:
    proc = _run_matrix(
        tmp_path,
        mode="automation",
        flx4="required",
        fake_flx4_rc=1,
        extra_env={
            "FAKE_RECENT_MOVES_SEEN": "1",
            "FAKE_AUDIO_OBSERVED": "1",
            "FAKE_DECK_STATE_RESOLVED": "1",
            "FAKE_DECK_STATE_PAIR_RESOLVED": "0",
            "FAKE_DECK_PAIR_CAPTURE_CONFIGURED": "1",
            "FAKE_DECK_AUDIO_CAPTURE_BOTH_ACTIVE": "1",
        },
    )

    assert proc.returncode == 1
    assert "next_action=resolve_deck_identity" in proc.stderr
    summary = json.loads((tmp_path / "out" / "matrix_summary.json").read_text())
    assert summary["next_operator_action"]["code"] == "resolve_deck_identity"
    assert "Deck A/B identity" in summary["next_operator_action"]["detail"]
    assert summary["checks"]["flx4"]["proof_missing_legs"] == ["deck_identity"]
    assert summary["next_operator_action"]["diagnostic_commands"] == [
        (
            "python -m vibemix library live-context --require-proof --wait-ready 10 "
            "--interval 1 --timeout 1 --frames 90 --json "
            "--out .planning/proofs/live-context-deck-identity-proof.json"
        )
    ]


def test_check_cohost_viber_matrix_promotes_deck_pair_capture_setup(
    tmp_path: Path,
) -> None:
    proc = _run_matrix(
        tmp_path,
        mode="automation",
        flx4="required",
        fake_flx4_rc=1,
        extra_env={
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
    summary = json.loads((tmp_path / "out" / "matrix_summary.json").read_text())
    assert summary["next_operator_action"]["code"] == "configure_deck_pair_capture"
    assert summary["next_operator_action"]["recommended_env"] == {
        "VIBEMIX_DECK_AUDIO_CHANNELS": "auto"
    }
    assert summary["next_operator_action"]["setup_hint"]["rule"] == "setup_hint_not_live_audio_proof"
    assert summary["checks"]["flx4"]["proof_missing_legs"] == ["deck_pair_audio_capture"]
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


def test_check_cohost_viber_matrix_promotes_feeding_both_deck_lanes(
    tmp_path: Path,
) -> None:
    proc = _run_matrix(
        tmp_path,
        mode="automation",
        flx4="required",
        fake_flx4_rc=1,
        extra_env={
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
    summary = json.loads((tmp_path / "out" / "matrix_summary.json").read_text())
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


def test_check_cohost_viber_matrix_blocks_when_runtime_canary_fails(
    tmp_path: Path,
) -> None:
    proc = _run_matrix(
        tmp_path,
        mode="automation",
        flx4="skip",
        fake_runtime_rc=1,
    )

    assert proc.returncode == 1
    assert "FAIL check_cohost_viber_matrix" in proc.stderr
    assert "runtime=False" in proc.stderr
    assert "next_action=inspect_runtime_canaries" in proc.stderr
    assert (
        "recommended_command=bash scripts/release/check_cohost_viber_runtime_canaries.sh"
        in proc.stderr
    )
    summary = json.loads((tmp_path / "out" / "matrix_summary.json").read_text())
    assert summary["checks"]["runtime_canaries"]["rc"] == 1
    assert summary["checks"]["runtime_canaries"]["failed"] == 1
    assert summary["next_operator_action"] == {
        "code": "inspect_runtime_canaries",
        "source": "runtime_canaries",
        "detail": (
            "FAIL check_cohost_viber_runtime_canaries: "
            "ok=False canaries=6 exercised=6 passed=5 failed=1 missing=0"
        ),
        "artifacts": {
            "summary_json": str(tmp_path / "out" / "runtime-canaries" / "runtime_canaries_summary.json"),
            "manifest": str(tmp_path / "out" / "runtime-canaries" / "runtime_canaries_manifest.json"),
            "stdout": str(tmp_path / "out" / "runtime-canaries" / "pytest.stdout.log"),
            "stderr": str(tmp_path / "out" / "runtime-canaries" / "pytest.stderr.log"),
        },
        "recommended_command": "bash scripts/release/check_cohost_viber_runtime_canaries.sh",
    }
    assert summary["operator_action_queue"][0]["code"] == "inspect_runtime_canaries"


def test_check_cohost_viber_matrix_promotes_runtime_canary_coverage_gap(
    tmp_path: Path,
) -> None:
    proc = _run_matrix(
        tmp_path,
        mode="automation",
        flx4="skip",
        extra_env={"FAKE_RUNTIME_MISSING": "1"},
    )

    assert proc.returncode == 1
    assert "next_action=restore_runtime_canary_coverage" in proc.stderr
    summary = json.loads((tmp_path / "out" / "matrix_summary.json").read_text())
    runtime = summary["checks"]["runtime_canaries"]
    assert runtime["coverage_ok"] is False
    assert runtime["missing_canaries"] == 1
    assert runtime["exercised"] == 5
    assert summary["next_operator_action"]["code"] == "restore_runtime_canary_coverage"
    assert "exercised=5 expected=6 missing=1" in summary["next_operator_action"]["detail"]
    assert summary["next_operator_action"]["artifacts"] == {
        "summary_json": str(tmp_path / "out" / "runtime-canaries" / "runtime_canaries_summary.json"),
        "manifest": str(tmp_path / "out" / "runtime-canaries" / "runtime_canaries_manifest.json"),
        "stdout": str(tmp_path / "out" / "runtime-canaries" / "pytest.stdout.log"),
        "stderr": str(tmp_path / "out" / "runtime-canaries" / "pytest.stderr.log"),
    }
    runbook = (tmp_path / "out" / "operator_action_runbook.sh").read_text()
    assert "artifact manifest:" in runbook
    assert "runtime_canaries_manifest.json" in runbook
    assert summary["operator_action_queue"][0]["code"] == "restore_runtime_canary_coverage"


def test_check_cohost_viber_matrix_blocks_when_runtime_summary_is_missing(
    tmp_path: Path,
) -> None:
    proc = _run_matrix(
        tmp_path,
        mode="automation",
        flx4="skip",
        extra_env={"FAKE_RUNTIME_SKIP_SUMMARY": "1"},
    )

    assert proc.returncode == 1
    assert "runtime=False" in proc.stderr
    assert "next_action=restore_runtime_canary_summary" in proc.stderr
    summary = json.loads((tmp_path / "out" / "matrix_summary.json").read_text())
    runtime = summary["checks"]["runtime_canaries"]
    assert runtime["rc"] == 0
    assert runtime["summary_present"] is False
    assert runtime["summary_json"] == str(
        tmp_path / "out" / "runtime-canaries" / "runtime_canaries_summary.json"
    )
    assert summary["next_operator_action"]["code"] == "restore_runtime_canary_summary"
    assert "did not produce a readable summary JSON" in summary["next_operator_action"]["detail"]
    assert summary["next_operator_action"]["artifacts"] == {
        "summary_json": str(tmp_path / "out" / "runtime-canaries" / "runtime_canaries_summary.json")
    }
    runbook = (tmp_path / "out" / "operator_action_runbook.sh").read_text()
    assert "artifact summary_json:" in runbook
    assert "runtime_canaries_summary.json" in runbook


def test_check_cohost_viber_matrix_preserves_secondary_autopilot_care(
    tmp_path: Path,
) -> None:
    proc = _run_matrix(
        tmp_path,
        mode="automation",
        flx4="required",
        fake_flx4_rc=1,
        extra_env={
            "FAKE_AUTOPILOT_BLOCKER": "1",
            "FAKE_AUTOPILOT_CARE": "1",
            "FAKE_AUTOPILOT_WATCH": "1",
        },
    )

    assert proc.returncode == 1
    assert "FAIL check_cohost_viber_matrix" in proc.stderr
    assert "next_action=play_audible_audio" in proc.stderr
    assert "actions=4" in proc.stderr
    assert "first_pass=False" in proc.stderr
    assert "reprompt_debt=2" in proc.stderr
    assert "audio_evidence_debt=1" in proc.stderr
    summary = json.loads((tmp_path / "out" / "matrix_summary.json").read_text())
    assert summary["next_operator_action"]["code"] == "play_audible_audio"
    assert summary["checks"]["autopilot"]["first_pass_clean"] is False
    assert summary["checks"]["autopilot"]["reprompt_debt"] == 2
    assert summary["checks"]["autopilot"]["audio_evidence_debt"] == 1
    assert summary["checks"]["autopilot"]["audio_evidence_debt_by_code"] == {
        "viber_library_request_live_leak": 1
    }
    assert [action["code"] for action in summary["operator_action_queue"]] == [
        "play_audible_audio",
        "review_autopilot_repair",
        "review_audio_evidence_debt",
        "review_autopilot_care",
    ]
    assert summary["operator_action_queue"][1]["source"] == "autopilot"
    repair_action = summary["operator_action_queue"][1]
    assert "blockers=1" in repair_action["detail"]
    assert "first_blocker=viber_library_request_live_leak" in repair_action["detail"]
    assert "repair_candidate=spoken" in repair_action["detail"]
    assert repair_action["artifacts"]["reprompt"].endswith(
        "/autopilot/reprompt-pack/01_viber_chat_viber_library_request_live_leak_viber-1/reprompt.md"
    )
    assert repair_action["artifacts"]["repair_candidate"].endswith(
        "/autopilot/repair-run/01_viber_chat_viber_library_request_live_leak_viber-1/candidate.json"
    )
    audio_action = summary["operator_action_queue"][2]
    assert audio_action["source"] == "autopilot"
    assert "Audio/live evidence debt=1" in audio_action["detail"]
    assert "first_issue=viber_library_request_live_leak" in audio_action["detail"]
    assert "repair_candidate=spoken" in audio_action["detail"]
    assert audio_action["artifacts"]["source_artifact"] == "/tmp/viber_meta.json"
    assert audio_action["artifacts"]["reprompt"].endswith(
        "/autopilot/reprompt-pack/01_viber_chat_viber_library_request_live_leak_viber-1/reprompt.md"
    )
    action = summary["operator_action_queue"][3]
    assert action["source"] == "autopilot"
    assert "care=1 watch=1" in action["detail"]
    assert "first_care=citation_strip_silent" in action["detail"]
    assert "repair_candidate=silence" in action["detail"]
    assert action["artifacts"]["report_json"].endswith("/autopilot/report.json")
    assert action["artifacts"]["reprompt"].endswith(
        "/autopilot/reprompt-pack/02_cohost_citation_strip_silent_0001/reprompt.md"
    )
    assert action["artifacts"]["repair_candidate"].endswith(
        "/autopilot/repair-run/02_cohost_citation_strip_silent_0001/candidate.json"
    )
    assert action["artifacts"]["repair_score"].endswith(
        "/autopilot/repair-run/02_cohost_citation_strip_silent_0001/score.json"
    )
    assert summary["checks"]["autopilot"]["care_issue_codes"] == ["citation_strip_silent"]
    assert summary["checks"]["autopilot"]["first_care_issue"]["artifact"] == "/tmp/meta.json"
    assert summary["checks"]["autopilot"]["first_audio_evidence_debt_issue"]["code"] == (
        "viber_library_request_live_leak"
    )
    assert summary["checks"]["autopilot"]["first_repair_result"]["reply_kind"] == "spoken"
    assert summary["checks"]["autopilot"]["first_care_repair_result"]["reply_kind"] == "silence"
    assert summary["checks"]["autopilot"]["first_audio_evidence_debt_repair_result"][
        "reply_kind"
    ] == "spoken"
