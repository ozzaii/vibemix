# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

SCRIPT = Path("scripts/release/check_cohost_viber_autopilot.sh").resolve()


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, separators=(",", ":")) + "\n" for row in rows),
        encoding="utf-8",
    )


def _fixture(tmp_path: Path) -> tuple[Path, Path]:
    session = tmp_path / "recordings" / "20260531-170000"
    _write_jsonl(
        session / "events.jsonl",
        [
            {
                "t": 0.0,
                "kind": "session_start",
                "wall_clock_iso": "2026-05-31T17:00:00+03:00",
            },
            {
                "t": 1.0,
                "kind": "ai_message",
                "engine": "live_coach",
                "surface": "session",
                "response_id": "0001",
                "message": "I'm listening.",
                "citation": {"count": 0, "action": "emit"},
                "extra": {"deck_audio_parts": 1},
            }
        ],
    )
    global_root = tmp_path / "app"
    artifact_dir = global_root / "ai_messages" / "artifacts" / "viber-1"
    artifact_dir.mkdir(parents=True)
    meta = {
        "response_id": "viber-1",
        "surface": "viber_chat",
        "message": "I caught the live move.",
        "moves": {
            "live_context_schema_version": 2,
            "live_context_deck": "none",
            "live_context_deck_mixer": {"connected": True},
        },
        "extra": {
            "request": "find me dark rolling hypnotic techno",
            "live_verification": {
                "ok": True,
                "violations": [],
                "guard_applied": True,
                "guard_violations": ["unsupported_live_outcome_claim"],
            },
        },
    }
    (artifact_dir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    (artifact_dir / "prompt.txt").write_text("prompt", encoding="utf-8")
    (artifact_dir / "response.txt").write_text(str(meta["message"]), encoding="utf-8")
    _write_jsonl(
        global_root / "ai_messages" / "ai_messages.jsonl",
        [
            {
                **meta,
                "engine": "codex",
                "ts_iso": "2026-05-31T17:00:05+03:00",
                "artifacts": {
                    "prompt_path": str(artifact_dir / "prompt.txt"),
                    "response_path": str(artifact_dir / "response.txt"),
                    "meta_path": str(artifact_dir / "meta.json"),
                },
            }
        ],
    )
    return session, global_root


def _run_gate(
    tmp_path: Path,
    *,
    fail_on: str,
) -> subprocess.CompletedProcess[str]:
    session, global_root = _fixture(tmp_path)
    env = os.environ.copy()
    env.update(
        {
            "PYTHON": sys.executable,
            "PYTHONPATH": str(Path("src").resolve()),
            "COHOST_VIBER_SESSION_DIR": str(session),
            "COHOST_VIBER_GLOBAL_ROOT": str(global_root),
            "COHOST_VIBER_OUT_DIR": str(tmp_path / f"out-{fail_on}"),
            "COHOST_VIBER_FAIL_ON": fail_on,
            "COHOST_VIBER_BACKEND": "deterministic",
        }
    )
    return subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=Path.cwd(),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_check_cohost_viber_autopilot_fails_when_summary_is_missing(
    tmp_path: Path,
) -> None:
    env = os.environ.copy()
    env.update(
        {
            "PYTHON": "true",
            "COHOST_VIBER_OUT_DIR": str(tmp_path / "out-missing-summary"),
            "COHOST_VIBER_FAIL_ON": "automation",
        }
    )
    proc = subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=Path.cwd(),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert proc.returncode == 1
    assert "autopilot did not write summary" in proc.stderr


def test_check_cohost_viber_autopilot_blocks_release_when_original_run_failed(
    tmp_path: Path,
) -> None:
    proc = _run_gate(tmp_path, fail_on="release")

    assert proc.returncode == 1
    assert "FAIL check_cohost_viber_autopilot" in proc.stderr
    assert "release_gate_ok=False" in proc.stderr
    assert "first_pass_clean=False" in proc.stderr
    assert "reprompt_debt=" in proc.stderr
    assert "audio_evidence_debt=2" in proc.stderr
    summary = json.loads((tmp_path / "out-release" / "autopilot_summary.json").read_text())
    assert summary["gate_ok"] is False
    assert summary["ok"] is True
    assert summary["first_pass_clean"] is False
    assert summary["reprompt_debt"] > 0
    assert summary["audio_evidence_debt"] == 2


def test_check_cohost_viber_autopilot_operator_mode_passes_with_repair(
    tmp_path: Path,
) -> None:
    proc = _run_gate(tmp_path, fail_on="automation")

    assert proc.returncode == 0
    assert "PASS check_cohost_viber_autopilot" in proc.stdout
    assert "repairs_passed=2" in proc.stdout
    assert "first_pass_clean=False" in proc.stdout
    assert "audio_evidence_debt=2" in proc.stdout
    summary = json.loads((tmp_path / "out-automation" / "autopilot_summary.json").read_text())
    assert summary["gate_ok"] is True
    assert summary["release_gate_ok"] is False
    assert summary["first_pass_clean"] is False
    assert summary["audio_evidence_debt"] == 2
    assert summary["global_since_iso"] == "2026-05-31T17:00:00+03:00"


def test_check_cohost_viber_autopilot_first_pass_blocks_repair_debt(
    tmp_path: Path,
) -> None:
    proc = _run_gate(tmp_path, fail_on="first-pass")

    assert proc.returncode == 1
    assert "FAIL check_cohost_viber_autopilot" in proc.stderr
    assert "first_pass_clean=False" in proc.stderr
    assert "audio_evidence_debt=2" in proc.stderr
    summary = json.loads((tmp_path / "out-first-pass" / "autopilot_summary.json").read_text())
    assert summary["gate_policy"] == "first-pass"
    assert summary["gate_ok"] is False
    assert summary["ok"] is True
    assert summary["first_pass_clean"] is False
    assert summary["reprompt_debt"] > 0


def test_check_cohost_viber_autopilot_audio_evidence_blocks_audio_debt(
    tmp_path: Path,
) -> None:
    proc = _run_gate(tmp_path, fail_on="audio-evidence")

    assert proc.returncode == 1
    assert "FAIL check_cohost_viber_autopilot" in proc.stderr
    assert "audio_evidence_debt=2" in proc.stderr
    summary = json.loads((tmp_path / "out-audio-evidence" / "autopilot_summary.json").read_text())
    assert summary["gate_policy"] == "audio-evidence"
    assert summary["gate_ok"] is False
    assert summary["ok"] is True
    assert summary["audio_evidence_debt"] == 2


def test_check_cohost_viber_autopilot_defaults_global_window_to_session_start(
    tmp_path: Path,
) -> None:
    session, global_root = _fixture(tmp_path)
    current_artifact_dir = global_root / "ai_messages" / "artifacts" / "current-viber"
    current_artifact_dir.mkdir(parents=True)
    current_meta = current_artifact_dir / "meta.json"
    current_prompt = current_artifact_dir / "prompt.txt"
    current_response = current_artifact_dir / "response.txt"
    current_prompt.write_text("LIVE CONTEXT USE: silent_guard", encoding="utf-8")
    current_response.write_text("I caught the live move.", encoding="utf-8")
    _write_jsonl(
        global_root / "ai_messages" / "ai_messages.jsonl",
        [
            {
                "engine": "codex",
                "surface": "viber_chat",
                "response_id": "old-viber",
                "ts_iso": "2026-05-31T16:59:00+03:00",
                "message": "I caught the live move.",
                "extra": {
                    "request": "find me dark rolling hypnotic techno",
                    "live_verification": {
                        "ok": True,
                        "violations": [],
                        "guard_applied": True,
                        "guard_violations": ["unsupported_live_outcome_claim"],
                    },
                },
            },
            {
                "engine": "codex",
                "surface": "viber_chat",
                "response_id": "current-viber",
                "ts_iso": "2026-05-31T17:00:05+03:00",
                "message": "I caught the live move.",
                "artifacts": {
                    "prompt_path": str(current_prompt),
                    "response_path": str(current_response),
                    "meta_path": str(current_meta),
                },
                "extra": {
                    "request": "find me dark rolling hypnotic techno",
                    "live_verification": {
                        "ok": True,
                        "violations": [],
                        "guard_applied": True,
                        "guard_violations": ["unsupported_live_outcome_claim"],
                    },
                },
            },
        ],
    )
    current_meta.write_text(
        json.dumps(
            {
                "response_id": "current-viber",
                "surface": "viber_chat",
                "message": "I caught the live move.",
                "extra": {
                    "request": "find me dark rolling hypnotic techno",
                    "live_verification": {
                        "ok": True,
                        "violations": [],
                        "guard_applied": True,
                        "guard_violations": ["unsupported_live_outcome_claim"],
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    env = os.environ.copy()
    env.update(
        {
            "PYTHON": sys.executable,
            "PYTHONPATH": str(Path("src").resolve()),
            "COHOST_VIBER_SESSION_DIR": str(session),
            "COHOST_VIBER_GLOBAL_ROOT": str(global_root),
            "COHOST_VIBER_OUT_DIR": str(tmp_path / "out-window"),
            "COHOST_VIBER_FAIL_ON": "automation",
            "COHOST_VIBER_BACKEND": "deterministic",
        }
    )

    proc = subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=Path.cwd(),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert proc.returncode == 0
    report = json.loads((tmp_path / "out-window" / "report.json").read_text())
    assert report["metrics"]["viber"]["rows_inspected"] == 1
    assert report["issues"][0]["response_id"] == "current-viber"
    summary = json.loads((tmp_path / "out-window" / "autopilot_summary.json").read_text())
    assert summary["global_since_iso"] == "2026-05-31T17:00:00+03:00"
