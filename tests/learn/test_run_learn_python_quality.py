# SPDX-License-Identifier: Apache-2.0
"""Contracts for the Learn Python quality artifact runner."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from scripts import run_learn_python_quality as runner


def test_build_report_requires_every_python_quality_command_to_pass() -> None:
    report = runner.build_report(
        [
            {"name": "learn_ruff", "passed": True},
            {"name": "learn_codegen_check", "passed": True},
            {"name": "learn_model_router_guard", "passed": True},
            {"name": "learn_all_lessons_runtime_pytest", "passed": True},
            {"name": "learn_teaching_loop_pytest", "passed": True},
            {"name": "learn_adaptive_coaching_pytest", "passed": True},
            {"name": "learn_auto_master_finder_pytest", "passed": True},
            {"name": "learn_course3_mix_anchor_pytest", "passed": True},
            {"name": "learn_course_pack_pytest", "passed": True},
            {"name": "learn_pytest", "passed": False},
        ]
    )

    assert report["passed"] is False
    assert [row["name"] for row in report["commands"]] == [
        "learn_ruff",
        "learn_codegen_check",
        "learn_model_router_guard",
        "learn_all_lessons_runtime_pytest",
        "learn_teaching_loop_pytest",
        "learn_adaptive_coaching_pytest",
        "learn_auto_master_finder_pytest",
        "learn_course3_mix_anchor_pytest",
        "learn_course_pack_pytest",
        "learn_pytest",
    ]


def test_run_command_records_success(monkeypatch) -> None:
    def fake_run(cmd, **kwargs):
        assert cmd == ["uv", "run", "pytest", "-q", "tests/learn"]
        assert kwargs["cwd"] == runner._REPO_ROOT
        return subprocess.CompletedProcess(cmd, 0, stdout="ok", stderr="")

    monkeypatch.setattr(runner.subprocess, "run", fake_run)

    result = runner.run_command(
        runner.QualityCommand(
            name="learn_pytest",
            command=("uv", "run", "pytest", "-q", "tests/learn"),
            timeout_s=1.0,
        )
    )

    assert result["passed"] is True
    assert result["returncode"] == 0
    assert result["stdout_tail"] == "ok"


def test_main_writes_python_quality_artifact(monkeypatch, tmp_path: Path) -> None:
    rows = [
        {"name": "learn_ruff", "passed": True, "returncode": 0, "duration_s": 0.1},
        {"name": "learn_codegen_check", "passed": True, "returncode": 0, "duration_s": 0.1},
        {"name": "learn_model_router_guard", "passed": True, "returncode": 0, "duration_s": 0.1},
        {
            "name": "learn_all_lessons_runtime_pytest",
            "passed": True,
            "returncode": 0,
            "duration_s": 0.1,
        },
        {
            "name": "learn_teaching_loop_pytest",
            "passed": True,
            "returncode": 0,
            "duration_s": 0.1,
        },
        {
            "name": "learn_adaptive_coaching_pytest",
            "passed": True,
            "returncode": 0,
            "duration_s": 0.1,
        },
        {
            "name": "learn_auto_master_finder_pytest",
            "passed": True,
            "returncode": 0,
            "duration_s": 0.1,
        },
        {
            "name": "learn_course3_mix_anchor_pytest",
            "passed": True,
            "returncode": 0,
            "duration_s": 0.1,
        },
        {
            "name": "learn_course_pack_pytest",
            "passed": True,
            "returncode": 0,
            "duration_s": 0.1,
        },
        {"name": "learn_pytest", "passed": True, "returncode": 0, "duration_s": 0.1},
    ]
    monkeypatch.setattr(runner, "run_command", lambda _spec: rows.pop(0))
    out = tmp_path / "python-quality.json"

    assert runner.main(["--out", str(out)]) == 0

    artifact = json.loads(out.read_text(encoding="utf-8"))
    assert artifact["passed"] is True
    assert [row["name"] for row in artifact["commands"]] == [
        "learn_ruff",
        "learn_codegen_check",
        "learn_model_router_guard",
        "learn_all_lessons_runtime_pytest",
        "learn_teaching_loop_pytest",
        "learn_adaptive_coaching_pytest",
        "learn_auto_master_finder_pytest",
        "learn_course3_mix_anchor_pytest",
        "learn_course_pack_pytest",
        "learn_pytest",
    ]
