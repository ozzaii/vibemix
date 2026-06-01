# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

SCRIPT = Path("scripts/release/check_cohost_viber_corpus_benchmark.sh").resolve()


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, separators=(",", ":")) + "\n" for row in rows),
        encoding="utf-8",
    )


def _fixture(tmp_path: Path) -> tuple[Path, Path]:
    recordings = tmp_path / "recordings"
    session = recordings / "20260531-180000"
    _write_jsonl(
        session / "events.jsonl",
        [
            {
                "t": 1.0,
                "kind": "ai_message",
                "engine": "live_coach",
                "surface": "session",
                "response_id": "0001",
                "message": "Great transition, that blend was clean.",
                "citation": {"count": 0, "action": "emit"},
                "extra": {"deck_audio_parts": 0},
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
                "artifacts": {
                    "prompt_path": str(artifact_dir / "prompt.txt"),
                    "response_path": str(artifact_dir / "response.txt"),
                    "meta_path": str(artifact_dir / "meta.json"),
                },
            }
        ],
    )
    return recordings, global_root


def _run_gate(
    tmp_path: Path,
    *,
    fail_on: str,
    extra_env: dict[str, str] | None = None,
    pin_clean_session: bool = False,
) -> subprocess.CompletedProcess[str]:
    recordings, global_root = _fixture(tmp_path)
    clean_session = recordings / "20260531-230000"
    if pin_clean_session:
        _write_jsonl(clean_session / "events.jsonl", [{"kind": "session_start"}])
    env = os.environ.copy()
    env.update(
        {
            "PYTHON": sys.executable,
            "PYTHONPATH": str(Path("src").resolve()),
            "COHOST_VIBER_RECORDINGS_ROOT": str(recordings),
            "COHOST_VIBER_GLOBAL_ROOT": str(global_root),
            "COHOST_VIBER_CORPUS_OUT_DIR": str(tmp_path / f"out-{fail_on}"),
            "COHOST_VIBER_CORPUS_FAIL_ON": fail_on,
            "COHOST_VIBER_BACKEND": "deterministic",
        }
    )
    if extra_env:
        env.update(extra_env)
    if pin_clean_session:
        env["COHOST_VIBER_CORPUS_SESSION_DIR"] = str(clean_session)
        env["COHOST_VIBER_GLOBAL_SINCE_ISO"] = "2026-05-31T22:00:00+00:00"
    return subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=Path.cwd(),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_check_cohost_viber_corpus_benchmark_fails_when_manifest_is_missing(
    tmp_path: Path,
) -> None:
    env = os.environ.copy()
    env.update(
        {
            "PYTHON": "true",
            "COHOST_VIBER_CORPUS_OUT_DIR": str(tmp_path / "out-missing-manifest"),
            "COHOST_VIBER_CORPUS_FAIL_ON": "automation",
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
    assert "failure-corpus did not write manifest" in proc.stderr


def test_check_cohost_viber_corpus_benchmark_blocks_release_on_saved_failures(
    tmp_path: Path,
) -> None:
    proc = _run_gate(tmp_path, fail_on="release")

    assert proc.returncode == 1
    assert "FAIL check_cohost_viber_corpus_benchmark" in proc.stderr
    assert "release_ready=False" in proc.stderr
    assert "benchmark_ok=True" in proc.stderr
    corpus = json.loads((tmp_path / "out-release" / "corpus" / "manifest.json").read_text())
    bench = json.loads(
        (tmp_path / "out-release" / "benchmark" / "benchmark_manifest.json").read_text()
    )
    assert corpus["release_ready"] is False
    assert corpus["policy_canary_count"] >= 4
    assert corpus["issue_code_counts"]["audio_vibe_listener_read_allowed"] == 1
    assert corpus["issue_code_counts"]["cohost_audio_source_detail_emit"] == 1
    assert corpus["issue_code_counts"]["citation_zero_ack_loop"] == 1
    assert "canaries=" in proc.stderr
    assert "audio_listener=1" in proc.stderr
    assert "audio_causal=1" in proc.stderr
    assert "audio_source=1" in proc.stderr
    assert "cohost_source=1" in proc.stderr
    assert "ack_loop=1" in proc.stderr
    assert bench["ok"] is True


def test_check_cohost_viber_corpus_benchmark_operator_mode_passes_clean_repairs(
    tmp_path: Path,
) -> None:
    proc = _run_gate(tmp_path, fail_on="automation")

    assert proc.returncode == 0
    assert "PASS check_cohost_viber_corpus_benchmark" in proc.stdout
    assert "benchmark_ok=True" in proc.stdout
    assert "release_ready=False" in proc.stdout
    assert "canaries=" in proc.stdout
    assert "audio_listener=1" in proc.stdout
    assert "cohost_source=1" in proc.stdout
    assert "ack_loop=1" in proc.stdout
    bench = json.loads(
        (tmp_path / "out-automation" / "benchmark" / "benchmark_manifest.json").read_text()
    )
    assert bench["passed"] == bench["case_count"]
    assert bench["failed"] == 0


def test_check_cohost_viber_corpus_benchmark_can_pin_current_clean_session(
    tmp_path: Path,
) -> None:
    proc = _run_gate(tmp_path, fail_on="release", pin_clean_session=True)

    assert proc.returncode == 0
    assert "PASS check_cohost_viber_corpus_benchmark" in proc.stdout
    assert "release_ready=True" in proc.stdout
    corpus = json.loads((tmp_path / "out-release" / "corpus" / "manifest.json").read_text())
    assert corpus["captured_case_count"] == 0
    assert corpus["release_ready"] is True
    assert corpus["global_since_iso"] == "2026-05-31T22:00:00+00:00"
    assert corpus["session_dirs"] == [str(tmp_path / "recordings" / "20260531-230000")]


def test_check_cohost_viber_corpus_benchmark_requires_policy_canaries(
    tmp_path: Path,
) -> None:
    proc = _run_gate(
        tmp_path,
        fail_on="automation",
        extra_env={
            "COHOST_VIBER_NO_POLICY_CANARIES": "1",
            "COHOST_VIBER_NO_VIBER": "1",
        },
    )

    assert proc.returncode == 1
    assert "FAIL check_cohost_viber_corpus_benchmark" in proc.stderr
    assert "missing_policy_canaries=" in proc.stderr
    assert "audio_vibe_listener_read_allowed" in proc.stderr
    assert "audio_vibe_control_causality" in proc.stderr
    assert "audio_vibe_hidden_source_detail" in proc.stderr
    assert "cohost_audio_source_detail_emit" in proc.stderr
    assert "citation_zero_ack_loop" in proc.stderr
    assert "viber_library_request_live_leak" in proc.stderr
