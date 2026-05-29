# SPDX-License-Identifier: Apache-2.0
"""Contracts for the Learn desktop-shell quality artifact runner."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from scripts import run_learn_desktop_quality as runner


def test_build_report_requires_every_desktop_quality_command_to_pass() -> None:
    report = runner.build_report(
        [
            {"name": "learn_tauri_frontend_dist_build", "passed": True},
            {"name": "learn_cargo_fmt", "passed": True},
            {"name": "learn_cargo_check", "passed": False},
            {"name": "learn_cargo_learn_window_test", "passed": True},
            {"name": "learn_cargo_sidecar_audio_test", "passed": True},
        ]
    )

    assert report["passed"] is False
    assert [row["name"] for row in report["commands"]] == [
        "learn_tauri_frontend_dist_build",
        "learn_cargo_fmt",
        "learn_cargo_check",
        "learn_cargo_learn_window_test",
        "learn_cargo_sidecar_audio_test",
    ]


def test_desktop_quality_builds_frontend_dist_before_cargo() -> None:
    assert runner.QUALITY_COMMANDS[0].name == "learn_tauri_frontend_dist_build"
    assert runner.QUALITY_COMMANDS[0].command == ("npm", "--prefix", "tauri/ui", "run", "build")
    assert [command.name for command in runner.QUALITY_COMMANDS[1:]] == [
        "learn_cargo_fmt",
        "learn_cargo_check",
        "learn_cargo_learn_window_test",
        "learn_cargo_sidecar_audio_test",
    ]


def test_run_command_records_success(monkeypatch) -> None:
    def fake_run(cmd, **kwargs):
        assert cmd == ["cargo", "check", "--manifest-path", "tauri/src-tauri/Cargo.toml"]
        assert kwargs["cwd"] == runner._REPO_ROOT
        return subprocess.CompletedProcess(cmd, 0, stdout="ok", stderr="")

    monkeypatch.setattr(runner.subprocess, "run", fake_run)

    result = runner.run_command(
        runner.QualityCommand(
            name="learn_cargo_check",
            command=("cargo", "check", "--manifest-path", "tauri/src-tauri/Cargo.toml"),
            timeout_s=1.0,
        )
    )

    assert result["passed"] is True
    assert result["returncode"] == 0
    assert result["stdout_tail"] == "ok"


def test_frontend_dist_build_retries_vite_enotempty_after_clean(monkeypatch) -> None:
    calls: list[list[str]] = []
    cleaned: list[Path] = []

    def fake_run(cmd, **kwargs):
        calls.append(list(cmd))
        assert kwargs["cwd"] == runner._REPO_ROOT
        if len(calls) == 1:
            return subprocess.CompletedProcess(
                cmd,
                1,
                stdout="transforming...",
                stderr=(
                    "error during build:\n"
                    "ENOTEMPTY: directory not empty, rmdir "
                    "'/Users/ozai/projects/dj-set-ai/tauri/ui/dist/assets'"
                ),
            )
        return subprocess.CompletedProcess(cmd, 0, stdout="built", stderr="")

    def fake_rmtree(path: Path, *, ignore_errors: bool = False) -> None:
        cleaned.append(path)
        assert ignore_errors is True

    monkeypatch.setattr(runner.subprocess, "run", fake_run)
    monkeypatch.setattr(runner.shutil, "rmtree", fake_rmtree)

    result = runner.run_command(runner.QUALITY_COMMANDS[0])

    assert result["passed"] is True
    assert result["retried_after_dist_cleanup"] is True
    assert calls == [list(runner.QUALITY_COMMANDS[0].command)] * 2
    assert cleaned == [runner._TAURI_UI_DIST]


def test_main_writes_desktop_quality_artifact(monkeypatch, tmp_path: Path) -> None:
    rows = [
        {
            "name": "learn_tauri_frontend_dist_build",
            "passed": True,
            "returncode": 0,
            "duration_s": 0.1,
        },
        {"name": "learn_cargo_fmt", "passed": True, "returncode": 0, "duration_s": 0.1},
        {"name": "learn_cargo_check", "passed": True, "returncode": 0, "duration_s": 0.1},
        {
            "name": "learn_cargo_learn_window_test",
            "passed": True,
            "returncode": 0,
            "duration_s": 0.1,
        },
        {
            "name": "learn_cargo_sidecar_audio_test",
            "passed": True,
            "returncode": 0,
            "duration_s": 0.1,
        },
    ]
    monkeypatch.setattr(runner, "run_command", lambda _spec: rows.pop(0))
    out = tmp_path / "desktop-quality.json"

    assert runner.main(["--out", str(out)]) == 0

    artifact = json.loads(out.read_text(encoding="utf-8"))
    assert artifact["passed"] is True
    assert [row["name"] for row in artifact["commands"]] == [
        "learn_tauri_frontend_dist_build",
        "learn_cargo_fmt",
        "learn_cargo_check",
        "learn_cargo_learn_window_test",
        "learn_cargo_sidecar_audio_test",
    ]
