# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

SCRIPT = Path("scripts/release/check_cohost_viber_runtime_canaries.sh").resolve()


def test_check_cohost_viber_runtime_canaries_passes_focused_invariants(
    tmp_path: Path,
) -> None:
    env = os.environ.copy()
    env.update(
        {
            "PYTHON": sys.executable,
            "PYTHONPATH": str(Path("src").resolve()),
            "COHOST_VIBER_RUNTIME_CANARY_OUT_DIR": str(tmp_path / "runtime-canaries"),
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
    assert "PASS check_cohost_viber_runtime_canaries" in proc.stdout
    assert "canaries=8" in proc.stdout
    assert "exercised=8" in proc.stdout
    assert "missing=0" in proc.stdout
    summary = json.loads(
        (tmp_path / "runtime-canaries" / "runtime_canaries_summary.json").read_text(
            encoding="utf-8"
        )
    )
    assert summary["ok"] is True
    assert summary["canary_count"] == 8
    assert summary["exercised"] == 8
    assert summary["coverage_ok"] is True
    assert summary["missing_canaries"] == 0
    assert summary["failed"] == 0
    assert summary["artifacts"]["manifest"] == str(
        tmp_path / "runtime-canaries" / "runtime_canaries_manifest.json"
    )
    manifest = json.loads(
        (tmp_path / "runtime-canaries" / "runtime_canaries_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    assert manifest["schema"] == "cohost_viber_runtime_canaries_manifest_v1"
    assert manifest["canaries"] == summary["canaries"]
    assert {item["id"] for item in summary["canaries"]} == {
        "manual_no_evidence_skips_llm",
        "manual_audio_signal_reaches_model",
        "audio_causal_guard_strips_before_tts",
        "audio_source_detail_guard_strips_before_tts",
        "audio_listener_read_survives_before_tts",
        "guard_fallback_stays_silent",
        "uncertain_ack_loop_becomes_silence",
        "manual_silence_report_is_not_repair",
    }


def test_check_cohost_viber_runtime_canaries_fails_when_canary_is_not_exercised(
    tmp_path: Path,
) -> None:
    fake_python = tmp_path / "fake-python"
    fake_python.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "set -euo pipefail",
                'if [ "${1:-}" = "-m" ] && [ "${2:-}" = "pytest" ]; then',
                '  node_args=0',
                '  for arg in "$@"; do',
                '    if [ "${arg}" = "-k" ]; then',
                '      echo "unexpected substring selector" >&2',
                "      exit 12",
                "    fi",
                '    case "${arg}" in',
                '      *"::test_"*) node_args=$((node_args + 1)) ;;',
                "    esac",
                "  done",
                '  if [ "${node_args}" -lt 8 ]; then',
                '    echo "expected exact pytest node ids, got ${node_args}" >&2',
                "    exit 13",
                "  fi",
                '  echo "7 passed, 120 deselected in 0.10s"',
                "  exit 0",
                "fi",
                f"exec {shlex.quote(sys.executable)} \"$@\"",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    fake_python.chmod(0o755)
    env = os.environ.copy()
    env.update(
        {
            "PYTHON": str(fake_python),
            "PYTHONPATH": str(Path("src").resolve()),
            "COHOST_VIBER_RUNTIME_CANARY_OUT_DIR": str(tmp_path / "runtime-canaries"),
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
    assert "FAIL check_cohost_viber_runtime_canaries" in proc.stderr
    assert "canaries=8" in proc.stderr
    assert "exercised=7" in proc.stderr
    assert "missing=1" in proc.stderr
    summary = json.loads(
        (tmp_path / "runtime-canaries" / "runtime_canaries_summary.json").read_text(
            encoding="utf-8"
        )
    )
    assert summary["rc"] == 0
    assert summary["ok"] is False
    assert summary["coverage_ok"] is False
    assert summary["missing_canaries"] == 1
