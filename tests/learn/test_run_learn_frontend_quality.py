# SPDX-License-Identifier: Apache-2.0
"""Contracts for the Learn frontend quality artifact runner."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from scripts import run_learn_frontend_quality as runner


def test_quality_commands_name_app_entry_and_choice_replay_before_broad_gate() -> None:
    assert [command.name for command in runner.QUALITY_COMMANDS] == [
        "learn_app_entry_vitest",
        "learn_frontstage_simplicity_vitest",
        "learn_tauri_window_vitest",
        "learn_choice_replay_vitest",
        "learn_vitest",
        "learn_build",
        "learn_browser_booth_playwright",
        "learn_e2e",
    ]
    app_entry = runner.QUALITY_COMMANDS[0]
    assert "tests/learn/test_beginner_path_contract.spec.ts" in app_entry.command
    assert "tests/session/render-loop-actions.spec.ts" in app_entry.command
    assert "tests/shell/shell.spec.ts" in app_entry.command
    frontstage = runner.QUALITY_COMMANDS[1]
    assert "tests/learn/test_practice_booth_shell.spec.ts" in frontstage.command
    assert "tests/learn/test_tutor_speak_sr_announcement.spec.ts" in frontstage.command
    tauri_window = runner.QUALITY_COMMANDS[2]
    assert "tests/learn/test_learn_window_label.spec.ts" in tauri_window.command
    choice = runner.QUALITY_COMMANDS[3]
    assert "tests/learn/test_practice_booth_shell.spec.ts" not in choice.command
    assert "tests/learn/test_progress_list.spec.ts" in choice.command
    assert "tests/learn/test_curriculum_meta.spec.ts" in choice.command
    assert "tests/learn/test_hud_progress_dots_keyboard.spec.ts" in choice.command
    browser = runner.QUALITY_COMMANDS[6]
    assert "test:e2e:learn" in browser.command
    assert "tests/learn/browser-axe.pw.ts" in browser.command
    assert "tests/learn/browser-responsive.pw.ts" in browser.command
    assert "tests/learn/browser-contrast.pw.ts" in browser.command
    assert "tests/learn/browser-python-beginner-path.pw.ts" in browser.command


def test_build_report_requires_every_frontend_quality_command_to_pass() -> None:
    report = runner.build_report(
        [
            {"name": "learn_app_entry_vitest", "passed": True},
            {"name": "learn_frontstage_simplicity_vitest", "passed": True},
            {"name": "learn_tauri_window_vitest", "passed": True},
            {"name": "learn_choice_replay_vitest", "passed": True},
            {"name": "learn_vitest", "passed": True},
            {"name": "learn_build", "passed": True},
            {"name": "learn_browser_booth_playwright", "passed": True},
            {"name": "learn_e2e", "passed": False},
        ]
    )

    assert report["passed"] is False
    assert [row["name"] for row in report["commands"]] == [
        "learn_app_entry_vitest",
        "learn_frontstage_simplicity_vitest",
        "learn_tauri_window_vitest",
        "learn_choice_replay_vitest",
        "learn_vitest",
        "learn_build",
        "learn_browser_booth_playwright",
        "learn_e2e",
    ]


def test_run_command_records_success(monkeypatch) -> None:
    def fake_run(cmd, **kwargs):
        assert cmd == ["npm", "--prefix", "tauri/ui", "run", "build"]
        assert kwargs["cwd"] == runner._REPO_ROOT
        return subprocess.CompletedProcess(cmd, 0, stdout="ok", stderr="")

    monkeypatch.setattr(runner.subprocess, "run", fake_run)

    result = runner.run_command(
        runner.QualityCommand(
            name="learn_build",
            command=("npm", "--prefix", "tauri/ui", "run", "build"),
            timeout_s=1.0,
        )
    )

    assert result["passed"] is True
    assert result["returncode"] == 0
    assert result["stdout_tail"] == "ok"


def test_main_writes_frontend_quality_artifact(monkeypatch, tmp_path: Path) -> None:
    rows = [
        {
            "name": "learn_app_entry_vitest",
            "passed": True,
            "returncode": 0,
            "duration_s": 0.1,
        },
        {
            "name": "learn_frontstage_simplicity_vitest",
            "passed": True,
            "returncode": 0,
            "duration_s": 0.1,
        },
        {
            "name": "learn_tauri_window_vitest",
            "passed": True,
            "returncode": 0,
            "duration_s": 0.1,
        },
        {
            "name": "learn_choice_replay_vitest",
            "passed": True,
            "returncode": 0,
            "duration_s": 0.1,
        },
        {"name": "learn_vitest", "passed": True, "returncode": 0, "duration_s": 0.1},
        {"name": "learn_build", "passed": True, "returncode": 0, "duration_s": 0.1},
        {
            "name": "learn_browser_booth_playwright",
            "passed": True,
            "returncode": 0,
            "duration_s": 0.1,
        },
        {"name": "learn_e2e", "passed": True, "returncode": 0, "duration_s": 0.1},
    ]
    monkeypatch.setattr(runner, "run_command", lambda _spec: rows.pop(0))
    out = tmp_path / "frontend-quality.json"

    assert runner.main(["--out", str(out)]) == 0

    artifact = json.loads(out.read_text(encoding="utf-8"))
    assert artifact["passed"] is True
    assert [row["name"] for row in artifact["commands"]] == [
        "learn_app_entry_vitest",
        "learn_frontstage_simplicity_vitest",
        "learn_tauri_window_vitest",
        "learn_choice_replay_vitest",
        "learn_vitest",
        "learn_build",
        "learn_browser_booth_playwright",
        "learn_e2e",
    ]
