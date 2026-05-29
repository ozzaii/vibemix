# SPDX-License-Identifier: Apache-2.0
"""Contracts for the Learn perfection package runner."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from scripts import run_learn_perfection_package as runner


def test_build_commands_refreshes_quality_before_verifier(tmp_path: Path) -> None:
    commands = runner.build_commands(
        python_quality_path=tmp_path / "python.json",
        frontend_quality_path=tmp_path / "frontend.json",
        desktop_quality_path=tmp_path / "desktop.json",
        verification_path=tmp_path / "verify.json",
    )

    assert [command.name for command in commands] == [
        "python_quality",
        "frontend_quality",
        "desktop_quality",
        "package_verifier",
    ]
    assert "scripts/run_learn_python_quality.py" in commands[0].command
    assert "scripts/run_learn_frontend_quality.py" in commands[1].command
    assert "scripts/run_learn_desktop_quality.py" in commands[2].command
    assert "--python-quality" in commands[3].command
    assert "--frontend-quality" in commands[3].command
    assert "--desktop-quality" in commands[3].command


def test_build_report_summarizes_verifier_release_state(tmp_path: Path) -> None:
    verification = tmp_path / "verification.json"
    verification.write_text(
        json.dumps(
            {
                "passed": True,
                "technical_passed": True,
                "release_ready": False,
                "non_external_ready": True,
                "deferred_external_blocker_ids": ["packaged_eq_exemplar_ear_pass"],
                "internal_blocker_ids": [],
                "completion_blockers": ["human ear-pass"],
                "completion_matrix": {"summary": {"proven": 12, "total": 14}},
                "release_gate_cue_card": {
                    "schema_version": 1,
                    "status": "waiting_on_external_gates",
                    "gate_count": 1,
                    "gates": [{"id": "packaged_eq_exemplar_ear_pass"}],
                },
                "sections": {
                    "python_quality": {
                        "path": str(tmp_path / "python.json"),
                        "passed": True,
                        "required_commands": [
                            "learn_all_lessons_runtime_pytest",
                            "learn_codegen_check",
                            "learn_model_router_guard",
                            "learn_pytest",
                            "learn_ruff",
                            "learn_adaptive_coaching_pytest",
                            "learn_auto_master_finder_pytest",
                            "learn_course3_mix_anchor_pytest",
                            "learn_course_pack_pytest",
                            "learn_teaching_loop_pytest",
                        ],
                        "commands": [
                            {"name": "learn_ruff", "passed": True},
                            {"name": "learn_codegen_check", "passed": True},
                            {"name": "learn_model_router_guard", "passed": True},
                            {
                                "name": "learn_all_lessons_runtime_pytest",
                                "passed": True,
                            },
                            {"name": "learn_teaching_loop_pytest", "passed": True},
                            {"name": "learn_adaptive_coaching_pytest", "passed": True},
                            {"name": "learn_auto_master_finder_pytest", "passed": True},
                            {"name": "learn_course3_mix_anchor_pytest", "passed": True},
                            {"name": "learn_course_pack_pytest", "passed": True},
                            {"name": "learn_pytest", "passed": True},
                        ],
                    },
                    "frontend_quality": {
                        "path": str(tmp_path / "frontend.json"),
                        "passed": True,
                        "commands": [
                            {"name": "learn_frontstage_simplicity_vitest", "passed": True},
                            {"name": "learn_tauri_window_vitest", "passed": True},
                            {"name": "learn_browser_booth_playwright", "passed": True},
                            {"name": "learn_build", "passed": True},
                            {"name": "learn_e2e", "passed": True},
                        ],
                    },
                    "desktop_quality": {
                        "path": str(tmp_path / "desktop.json"),
                        "passed": True,
                        "commands": [
                            {"name": "learn_tauri_frontend_dist_build", "passed": True},
                            {"name": "learn_cargo_fmt", "passed": True},
                            {"name": "learn_cargo_check", "passed": True},
                            {"name": "learn_cargo_learn_window_test", "passed": True},
                            {"name": "learn_cargo_sidecar_audio_test", "passed": True},
                        ],
                    },
                },
                "release_blocker_recipe": [
                    {
                        "id": "packaged_eq_exemplar_ear_pass",
                        "commands": {"play": "play command"},
                    },
                    {"id": "", "commands": {"ignored": "blank id"}},
                    "not a recipe row",
                ],
            }
        ),
        encoding="utf-8",
    )

    report = runner.build_report(
        [{"name": "package_verifier", "passed": True}],
        verification_path=verification,
    )

    assert report["passed"] is True
    assert report["release_ready"] is False
    assert report["non_external_ready"] is True
    assert report["deferred_external_blocker_ids"] == ["packaged_eq_exemplar_ear_pass"]
    assert report["internal_blocker_ids"] == []
    assert report["verification_refreshed"] is True
    assert report["verification_summary"]["technical_passed"] is True
    assert report["verification_summary"]["non_external_ready"] is True
    assert report["verification_summary"]["deferred_external_blocker_ids"] == [
        "packaged_eq_exemplar_ear_pass"
    ]
    assert report["verification_summary"]["internal_blocker_ids"] == []
    assert report["verification_summary"]["completion_blockers"] == ["human ear-pass"]
    assert report["verification_summary"]["completion_matrix"] == {"proven": 12, "total": 14}
    assert report["release_gate_cue_card"] == {
        "schema_version": 1,
        "status": "waiting_on_external_gates",
        "gate_count": 1,
        "gates": [{"id": "packaged_eq_exemplar_ear_pass"}],
    }
    assert report["quality_contract"]["python_quality"]["model_router_guard"] is True
    assert report["quality_contract"]["python_quality"]["all_lessons_runtime"] is True
    assert report["quality_contract"]["python_quality"]["adaptive_coaching"] is True
    assert report["quality_contract"]["python_quality"]["auto_master_finder"] is True
    assert report["quality_contract"]["python_quality"]["course3_mix_anchor"] is True
    assert report["quality_contract"]["python_quality"]["course_pack_preflight"] is True
    assert report["quality_contract"]["python_quality"]["commands"] == [
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
    assert report["release_blocker_recipe"] == [
        {"id": "packaged_eq_exemplar_ear_pass", "commands": {"play": "play command"}},
        {"id": "", "commands": {"ignored": "blank id"}},
    ]
    assert report["release_blocker_recipe_ids"] == ["packaged_eq_exemplar_ear_pass"]
    assert report["quality_contract"]["frontend_quality"]["passed"] is True
    assert report["quality_contract"]["frontend_quality"]["browser_booth_quality"] is True
    assert report["quality_contract"]["frontend_quality"]["tauri_window_contract"] is True
    assert report["quality_contract"]["frontend_quality"]["commands"] == [
        "learn_frontstage_simplicity_vitest",
        "learn_tauri_window_vitest",
        "learn_browser_booth_playwright",
        "learn_build",
        "learn_e2e",
    ]
    assert report["quality_contract"]["desktop_quality"]["passed"] is True
    assert report["quality_contract"]["desktop_quality"]["learn_window_test"] is True
    assert report["quality_contract"]["desktop_quality"]["commands"] == [
        "learn_tauri_frontend_dist_build",
        "learn_cargo_fmt",
        "learn_cargo_check",
        "learn_cargo_learn_window_test",
        "learn_cargo_sidecar_audio_test",
    ]


def test_run_command_records_failure(monkeypatch) -> None:
    def fake_run(cmd, **kwargs):
        assert kwargs["cwd"] == runner._REPO_ROOT
        return subprocess.CompletedProcess(cmd, 4, stdout="", stderr="nope")

    monkeypatch.setattr(runner.subprocess, "run", fake_run)

    result = runner.run_command(
        runner.PackageCommand(
            name="package_verifier",
            command=("uv", "run", "python", "scripts/verify_learn_package.py"),
            timeout_s=1.0,
        )
    )

    assert result["passed"] is False
    assert result["returncode"] == 4
    assert result["stderr_tail"] == "nope"


def test_main_writes_package_artifact_and_keeps_release_gate_separate(
    monkeypatch,
    tmp_path: Path,
) -> None:
    verification = tmp_path / "verification.json"
    out = tmp_path / "package.json"

    def fake_run_command(spec):
        if spec.name == "package_verifier":
            verification.write_text(
                json.dumps(
                    {
                        "passed": True,
                        "technical_passed": True,
                        "release_ready": False,
                        "non_external_ready": True,
                        "deferred_external_blocker_ids": ["course3_live_audio_play_mode"],
                        "internal_blocker_ids": [],
                        "completion_blockers": ["Course 3"],
                        "completion_matrix": {"summary": {"proven": 12, "total": 14}},
                        "release_gate_cue_card": {
                            "schema_version": 1,
                            "status": "waiting_on_external_gates",
                            "gate_count": 1,
                            "gates": [{"id": "course3_live_audio_play_mode"}],
                        },
                        "sections": {
                            "python_quality": {
                                "path": str(tmp_path / "python.json"),
                                "passed": True,
                                "required_commands": [
                                    "learn_model_router_guard",
                                    "learn_all_lessons_runtime_pytest",
                                    "learn_adaptive_coaching_pytest",
                                    "learn_auto_master_finder_pytest",
                                    "learn_course3_mix_anchor_pytest",
                                    "learn_course_pack_pytest",
                                ],
                                "commands": [
                                    {"name": "learn_model_router_guard", "passed": True},
                                    {
                                        "name": "learn_all_lessons_runtime_pytest",
                                        "passed": True,
                                    },
                                    {
                                        "name": "learn_adaptive_coaching_pytest",
                                        "passed": True,
                                    },
                                    {
                                        "name": "learn_auto_master_finder_pytest",
                                        "passed": True,
                                    },
                                    {
                                        "name": "learn_course3_mix_anchor_pytest",
                                        "passed": True,
                                    },
                                    {
                                        "name": "learn_course_pack_pytest",
                                        "passed": True,
                                    },
                                ],
                            },
                            "frontend_quality": {
                                "path": str(tmp_path / "frontend.json"),
                                "passed": True,
                                "commands": [
                                    {
                                        "name": "learn_frontstage_simplicity_vitest",
                                        "passed": True,
                                    },
                                    {
                                        "name": "learn_tauri_window_vitest",
                                        "passed": True,
                                    },
                                    {
                                        "name": "learn_browser_booth_playwright",
                                        "passed": True,
                                    },
                                    {"name": "learn_build", "passed": True},
                                ],
                            },
                            "desktop_quality": {
                                "path": str(tmp_path / "desktop.json"),
                                "passed": True,
                                "commands": [
                                    {
                                        "name": "learn_tauri_frontend_dist_build",
                                        "passed": True,
                                    },
                                    {
                                        "name": "learn_cargo_learn_window_test",
                                        "passed": True,
                                    },
                                ],
                            },
                        },
                        "release_blocker_recipe": [
                            {
                                "id": "course3_live_audio_play_mode",
                                "commands": {"proof": "proof command"},
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
        return {
            "name": spec.name,
            "command": " ".join(spec.command),
            "returncode": 0,
            "duration_s": 0.1,
            "passed": True,
        }

    monkeypatch.setattr(runner, "run_command", fake_run_command)

    code = runner.main(
        [
            "--out",
            str(out),
            "--python-quality-out",
            str(tmp_path / "python.json"),
            "--frontend-quality-out",
            str(tmp_path / "frontend.json"),
            "--desktop-quality-out",
            str(tmp_path / "desktop.json"),
            "--verification-out",
            str(verification),
        ]
    )

    assert code == 0
    artifact = json.loads(out.read_text(encoding="utf-8"))
    assert artifact["passed"] is True
    assert artifact["release_ready"] is False
    assert artifact["non_external_ready"] is True
    assert artifact["deferred_external_blocker_ids"] == ["course3_live_audio_play_mode"]
    assert artifact["internal_blocker_ids"] == []
    assert artifact["verification_refreshed"] is True
    assert artifact["release_gate_cue_card"] == {
        "schema_version": 1,
        "status": "waiting_on_external_gates",
        "gate_count": 1,
        "gates": [{"id": "course3_live_audio_play_mode"}],
    }
    assert artifact["quality_contract"]["python_quality"]["model_router_guard"] is True
    assert artifact["quality_contract"]["python_quality"]["all_lessons_runtime"] is True
    assert artifact["quality_contract"]["python_quality"]["adaptive_coaching"] is True
    assert artifact["quality_contract"]["python_quality"]["auto_master_finder"] is True
    assert artifact["quality_contract"]["python_quality"]["course3_mix_anchor"] is True
    assert artifact["quality_contract"]["python_quality"]["course_pack_preflight"] is True
    assert artifact["quality_contract"]["frontend_quality"]["browser_booth_quality"] is True
    assert artifact["quality_contract"]["frontend_quality"]["tauri_window_contract"] is True
    assert artifact["quality_contract"]["desktop_quality"]["learn_window_test"] is True
    assert artifact["release_blocker_recipe"] == [
        {"id": "course3_live_audio_play_mode", "commands": {"proof": "proof command"}}
    ]
    assert artifact["release_blocker_recipe_ids"] == ["course3_live_audio_play_mode"]
    assert [row["name"] for row in artifact["commands"]] == [
        "python_quality",
        "frontend_quality",
        "desktop_quality",
        "package_verifier",
    ]


def test_main_require_release_ready_fails_when_verifier_has_blockers(
    monkeypatch,
    tmp_path: Path,
) -> None:
    verification = tmp_path / "verification.json"

    def fake_run_command(spec):
        if spec.name == "package_verifier":
            verification.write_text(
                json.dumps({"passed": True, "release_ready": False}),
                encoding="utf-8",
            )
        return {
            "name": spec.name,
            "command": " ".join(spec.command),
            "returncode": 0,
            "duration_s": 0.1,
            "passed": True,
        }

    monkeypatch.setattr(runner, "run_command", fake_run_command)

    assert (
        runner.main(
            [
                "--out",
                str(tmp_path / "package.json"),
                "--verification-out",
                str(verification),
                "--require-release-ready",
            ]
        )
        == 4
    )


def test_build_report_marks_verifier_summary_stale_when_verifier_did_not_run(
    tmp_path: Path,
) -> None:
    verification = tmp_path / "verification.json"
    verification.write_text(
        json.dumps({"passed": True, "release_ready": True}),
        encoding="utf-8",
    )

    report = runner.build_report(
        [{"name": "python_quality", "passed": False}],
        verification_path=verification,
    )

    assert report["passed"] is False
    assert report["verification_refreshed"] is False
