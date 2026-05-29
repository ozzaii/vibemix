# SPDX-License-Identifier: Apache-2.0
"""Contracts for the consolidated Learn package verifier."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts import verify_learn_package as verifier

from vibemix.learn.curriculum_audit import course_pack_contract


def _curriculum_report() -> dict:
    return {
        "passed": True,
        "counts": {"beginner_lessons": 36},
        "beginner_course_ids": [
            "course_1_anatomy",
            "course_2_transitions",
            "course_3_play_mode",
        ],
        "frontend_projection": {"checked": True, "up_to_date": True},
        "flow_contract_summary": {
            "beginner_lessons": 36,
            "beginner_flows_ok": True,
            "failing_lesson_ids": [],
            "total_steps": 76,
            "min_hint_count": 3,
            "prompt_contract": {
                "ok": True,
                "max_chars": 150,
                "max_words": 24,
                "max_sentences": 2,
                "single_line": True,
                "inline_lists_forbidden": True,
                "observed_max_chars": 115,
                "observed_max_words": 23,
                "observed_max_sentences": 2,
                "exempt_step_ids": ["L1.01.beat.3"],
                "failing_lesson_ids": [],
            },
            "teaching_grounding_contract": {
                "ok": True,
                "teaching_turn_count": 76,
                "grounded_teaching_turn_count": 76,
                "cited_teaching_turn_count": 76,
                "failing_lesson_ids": [],
            },
            "hint_grounding_contract": {
                "ok": True,
                "hint_turn_count": 228,
                "grounded_hint_turn_count": 228,
                "cited_hint_turn_count": 228,
                "failing_lesson_ids": [],
            },
            "input_surfaces": ["hardware", "screen"],
            "input_surface_step_counts": {
                "hardware+screen": 32,
                "screen": 44,
            },
            "backstage_lenses": ["evidence_registry"],
            "observable_control_count": 12,
            "verification_kind_counts": {
                "button_press": 51,
                "cc_delta": 25,
            },
        },
        "transcript_inventory": {
            "ok": True,
            "fixture_count": 37,
            "declared_count": 37,
            "duplicate_paths": [],
            "missing_paths": [],
            "orphan_paths": [],
        },
        "course_pack_contract": course_pack_contract(),
        "unlock_gate_contract": {
            "ok": True,
            "supported_unlock_gates": ["course_2_unlocked", "course_3_unlocked"],
            "used_unlock_gates": ["course_2_unlocked", "course_3_unlocked"],
            "unsupported_unlock_gates": [],
            "missing_lock_reason_course_ids": [],
        },
        "copy_truthfulness_contract": {
            "ok": True,
            "unsupported_auto_open_phrases": ["debrief opens"],
            "unsupported_debrief_auto_open_claims": [],
        },
        "new_course_contract": ["add COURSE_REGISTRY metadata"],
        "errors": [],
        "warnings": [],
    }


def _exemplar_report(*, release_ready: bool = False) -> dict:
    return {
        "technical_passed": True,
        "release_ready": release_ready,
        "human_ear_pass_required": not release_ready,
        "human_ear_pass": "approved" if release_ready else None,
        "bank_fingerprint": {
            "algorithm": "sha256-canonical-json-v1",
            "digest": "a" * 64,
            "manifest_sha256": "b" * 64,
            "track_count": 4,
        },
        "diagnosis": {
            "code": (
                "approved"
                if release_ready
                else "technical_audit_passed_ear_pass_pending"
            )
        },
        "technical_failures": [],
        "operator_commands": {
            "list_output_devices": (
                "uv run python scripts/audition_learn_exemplars.py --list-devices"
            ),
            "play": (
                "uv run python scripts/audition_learn_exemplars.py --play "
                "--device-index <output-device-index> --say-prompts "
                "--out /tmp/vibemix-live-learn-proof/learn-exemplar-audition-current.json"
            ),
            "approve": (
                "uv run python scripts/audition_learn_exemplars.py "
                "--approve-ear-pass --approved-by <name> "
                "--audition /tmp/vibemix-live-learn-proof/learn-exemplar-audition-current.json "
                "--approval-out /tmp/vibemix-live-learn-proof/learn-exemplar-ear-pass-current.json"
            ),
        },
        "operator_action": {
            "prompt": "Listen to the four EQ exemplar loops, then approve or replace them.",
            "recommended_output_devices": [],
            "steps": [
                "uv run python scripts/audition_learn_exemplars.py --list-devices",
                "uv run python scripts/audition_learn_exemplars.py --play --device-index <output-device-index> --say-prompts --out /tmp/vibemix-live-learn-proof/learn-exemplar-audition-current.json",
                "uv run python scripts/audition_learn_exemplars.py --approve-ear-pass --approved-by <name> --audition /tmp/vibemix-live-learn-proof/learn-exemplar-audition-current.json --approval-out /tmp/vibemix-live-learn-proof/learn-exemplar-ear-pass-current.json",
            ],
        },
        "tracks": [{"band": "sub"}, {"band": "low"}, {"band": "mid"}, {"band": "high"}],
    }


def _exemplar_audit_for_approval(*, expected_path: Path):
    def audit(*, approval_path=None):
        return _exemplar_report(release_ready=approval_path == expected_path)

    return audit


def _tauri_smoke(path: Path) -> Path:
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "passed": True,
                "completed_lesson_id": "L1.01",
                "l101_completed": True,
                "quality_ok": True,
                "quality_check_count": 17,
                "failures": [],
            }
        ),
        encoding="utf-8",
    )
    return path


def test_launched_tauri_smoke_script_writes_verifier_discoverable_artifact_by_default() -> None:
    script = Path("scripts/e2e/learn_launched_tauri_smoke.mjs")

    result = subprocess.run(
        ["node", str(script), "--help"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "/tmp/vibemix-live-learn-proof/learn-tauri-smoke-current.json" in result.stdout
    assert "unless --out PATH is provided" in result.stdout


def test_exemplar_status_enriches_operator_action_with_output_devices(monkeypatch) -> None:
    monkeypatch.setattr(verifier, "audit_packaged_bank", lambda approval_path=None: _exemplar_report())
    monkeypatch.setattr(
        verifier,
        "list_output_devices",
        lambda: [
            {
                "index": 4,
                "name": "MacBook Pro Speakers",
                "hostapi": "Core Audio",
                "max_output_channels": 2,
                "default_sample_rate": 48000,
                "is_default_output": False,
            },
            {
                "index": 1,
                "name": "BlackHole 16ch",
                "hostapi": "Core Audio",
                "max_output_channels": 16,
                "default_sample_rate": 48000,
                "is_default_output": True,
            },
        ],
    )

    status = verifier._exemplar_status(None)

    assert status["output_devices"][0]["name"] == "MacBook Pro Speakers"
    assert status["operator_action"]["recommended_output_devices"][0]["index"] == 4
    assert "--device-index 4" in status["operator_action"]["steps"][1]
    assert "learn-exemplar-audition-current.json" in status["operator_action"]["steps"][1]


def _frontend_quality(path: Path, *, passed: bool = True) -> Path:
    command_rows = [
        {
            "name": "learn_app_entry_vitest",
            "command": (
                "npm --prefix tauri/ui test -- "
                "tests/learn/test_beginner_path_contract.spec.ts "
                "tests/session/render-loop-actions.spec.ts "
                "tests/shell/shell.spec.ts"
            ),
            "returncode": 0,
            "duration_s": 1.0,
            "passed": True,
        },
        {
            "name": "learn_frontstage_simplicity_vitest",
            "command": (
                "npm --prefix tauri/ui test -- "
                "tests/learn/test_practice_booth_shell.spec.ts "
                "tests/learn/test_tutor_speak_sr_announcement.spec.ts"
            ),
            "returncode": 0,
            "duration_s": 1.0,
            "passed": True,
        },
        {
            "name": "learn_tauri_window_vitest",
            "command": (
                "npm --prefix tauri/ui test -- "
                "tests/learn/test_learn_window_label.spec.ts"
            ),
            "returncode": 0,
            "duration_s": 1.0,
            "passed": True,
        },
        {
            "name": "learn_choice_replay_vitest",
            "command": (
                "npm --prefix tauri/ui test -- "
                "tests/learn/test_progress_list.spec.ts "
                "tests/learn/test_curriculum_meta.spec.ts "
                "tests/learn/test_hud_progress_dots_keyboard.spec.ts"
            ),
            "returncode": 0 if passed else 1,
            "duration_s": 1.0,
            "passed": passed,
        },
        {
            "name": "learn_vitest",
            "command": "npm --prefix tauri/ui test -- tests/learn",
            "returncode": 0,
            "duration_s": 1.0,
            "passed": True,
        },
        {
            "name": "learn_build",
            "command": "npm --prefix tauri/ui run build",
            "returncode": 0,
            "duration_s": 1.0,
            "passed": True,
        },
        {
            "name": "learn_browser_booth_playwright",
            "command": (
                "npm --prefix tauri/ui run test:e2e:learn -- "
                "tests/learn/browser-axe.pw.ts "
                "tests/learn/browser-responsive.pw.ts "
                "tests/learn/browser-contrast.pw.ts "
                "tests/learn/browser-python-beginner-path.pw.ts"
            ),
            "returncode": 0,
            "duration_s": 1.0,
            "passed": True,
        },
        {
            "name": "learn_e2e",
            "command": "npm --prefix tauri/ui run test:e2e:learn",
            "returncode": 0,
            "duration_s": 1.0,
            "passed": True,
        },
    ]
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "generated_at": "2026-05-29T00:00:00Z",
                "passed": all(row["passed"] for row in command_rows),
                "commands": command_rows,
            }
        ),
        encoding="utf-8",
    )
    return path


def _python_quality(path: Path, *, passed: bool = True) -> Path:
    command_rows = [
        {
            "name": "learn_ruff",
            "command": "uv run ruff check src/vibemix/learn tests/learn",
            "returncode": 0 if passed else 1,
            "duration_s": 1.0,
            "passed": passed,
        },
        {
            "name": "learn_codegen_check",
            "command": "uv run python scripts/export_learn_curriculum_meta.py --check",
            "returncode": 0,
            "duration_s": 1.0,
            "passed": True,
        },
        {
            "name": "learn_model_router_guard",
            "command": "bash scripts/release/check_no_hardcoded_model.sh",
            "returncode": 0,
            "duration_s": 1.0,
            "passed": True,
        },
        {
            "name": "learn_all_lessons_runtime_pytest",
            "command": "uv run pytest -q tests/learn/test_all_lessons_runtime_path.py",
            "returncode": 0,
            "duration_s": 1.0,
            "passed": True,
        },
        {
            "name": "learn_teaching_loop_pytest",
            "command": "uv run pytest -q tests/learn/test_teaching_loop.py",
            "returncode": 0,
            "duration_s": 1.0,
            "passed": True,
        },
        {
            "name": "learn_adaptive_coaching_pytest",
            "command": (
                "uv run pytest -q "
                "tests/learn/test_adaptive_coaching_runtime_contract.py"
            ),
            "returncode": 0,
            "duration_s": 1.0,
            "passed": True,
        },
        {
            "name": "learn_auto_master_finder_pytest",
            "command": "uv run pytest -q tests/learn/test_auto_master_finder_contract.py",
            "returncode": 0,
            "duration_s": 1.0,
            "passed": True,
        },
        {
            "name": "learn_course3_mix_anchor_pytest",
            "command": (
                "uv run pytest -q "
                "tests/state/test_refresh.py::test_tick_course3_live_uses_dj_cue_sections_for_phrase_anchor "
                "tests/state/test_refresh.py::test_tick_course3_mix_uses_unambiguous_title_match_for_phrase_anchor "
                "tests/state/test_refresh.py::test_tick_course3_mix_refuses_ambiguous_title_match_for_phrase_anchor"
            ),
            "returncode": 0,
            "duration_s": 1.0,
            "passed": True,
        },
        {
            "name": "learn_course_pack_pytest",
            "command": "uv run pytest -q tests/learn/test_course_pack.py",
            "returncode": 0,
            "duration_s": 1.0,
            "passed": True,
        },
        {
            "name": "learn_pytest",
            "command": "uv run pytest -q tests/learn",
            "returncode": 0,
            "duration_s": 1.0,
            "passed": True,
        },
    ]
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "generated_at": "2026-05-29T00:00:00Z",
                "passed": all(row["passed"] for row in command_rows),
                "commands": command_rows,
            }
        ),
        encoding="utf-8",
    )
    return path


def _desktop_quality(path: Path, *, passed: bool = True) -> Path:
    command_rows = [
        {
            "name": "learn_tauri_frontend_dist_build",
            "command": "npm --prefix tauri/ui run build",
            "returncode": 0,
            "duration_s": 1.0,
            "passed": True,
        },
        {
            "name": "learn_cargo_fmt",
            "command": "cargo fmt --manifest-path tauri/src-tauri/Cargo.toml --all -- --check",
            "returncode": 0 if passed else 1,
            "duration_s": 1.0,
            "passed": passed,
        },
        {
            "name": "learn_cargo_check",
            "command": "cargo check --manifest-path tauri/src-tauri/Cargo.toml",
            "returncode": 0,
            "duration_s": 1.0,
            "passed": True,
        },
        {
            "name": "learn_cargo_learn_window_test",
            "command": (
                "cargo test --manifest-path tauri/src-tauri/Cargo.toml "
                "learn_window"
            ),
            "returncode": 0,
            "duration_s": 1.0,
            "passed": True,
        },
        {
            "name": "learn_cargo_sidecar_audio_test",
            "command": (
                "cargo test --manifest-path tauri/src-tauri/Cargo.toml "
                "sidecar_audio_env_defaults"
            ),
            "returncode": 0,
            "duration_s": 1.0,
            "passed": True,
        },
    ]
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "generated_at": "2026-05-29T00:00:00Z",
                "passed": all(row["passed"] for row in command_rows),
                "commands": command_rows,
            }
        ),
        encoding="utf-8",
    )
    return path


def _live_artifact(
    path: Path,
    *,
    physical: bool = False,
    physical_diagnosis: dict | None = None,
    course3: bool = False,
    course3_diagnosis: dict | None = None,
    course3_route_plan: dict | None = None,
    auto_master_recommendation: dict | None = None,
    playback_nudge: dict | None = None,
) -> Path:
    app_start_result = {}
    if course3_route_plan is not None:
        app_start_result = {
            "audio_env": {
                "auto_master_input": True,
                "auto_master_fallback_candidate": course3_route_plan.get(
                    "candidate"
                ),
                "auto_master_fallback_device": course3_route_plan.get(
                    "fallback_device"
                ),
                "auto_master_fallback_rejected_reason": course3_route_plan.get(
                    "rejected_reason"
                ),
            },
            "audio_runtime": {
                "auto_master_input": course3_route_plan.get("selected_input")
            },
        }
    stages = {
        "app_start": {"status": "passed", "result": app_start_result},
        "app_stop": {"status": "passed"},
        "readiness_before_probes": {
            "status": "passed",
            "result": {
                **(
                    {"auto_master_recommendation": auto_master_recommendation}
                    if auto_master_recommendation is not None
                    else {}
                )
            },
        },
        "screen_probe": {
            "status": "passed",
            "result": {
                "passed": True,
                "acks_sent": 4,
                "advance_count": 4,
                "complete_seen": True,
                "progress_completed": True,
            },
        },
        "progress_file": {
            "status": "passed",
            "result": {
                "snapshot": {
                    "lessons": {
                        "L1.01": {
                            "completed": True,
                            "completed_at": "2026-05-29T00:00:00Z",
                            "strikes_used": 0,
                        }
                    }
                }
            },
        },
        "physical_probe": {
            "status": "skipped",
            "reason": "physical readiness failed",
            "result": {
                "blockers": ["physical controller is not visible as a MIDI input"],
                **({"diagnosis": physical_diagnosis} if physical_diagnosis is not None else {}),
            },
        },
        "course3_probe": {
            "status": "skipped",
            "reason": "course3 readiness failed",
            "result": {
                "blockers": ["live master audio is not audible yet"],
                **(
                    {"course3_audio_diagnosis": course3_diagnosis}
                    if course3_diagnosis is not None
                    else {}
                ),
            },
        },
    }
    if playback_nudge is not None:
        stages["rekordbox_playback_nudge"] = {
            "status": "passed" if playback_nudge.get("ok") else "failed",
            "result": playback_nudge,
        }
    if physical:
        stages["physical_probe"] = {
            "status": "passed",
            "result": {
                "passed": True,
                "lesson_id": "L1.07",
                "control_id": "jog:A",
                "lesson_loaded": True,
                "jog_position_seen": True,
                "ack_sent": True,
                "advance_seen": True,
            },
        }
    if course3:
        stages["course3_probe"] = {
            "status": "passed",
            "result": {
                "passed": True,
                "lens_frames": 2,
                "active_seen": True,
                "count_in_seen": True,
                "last_lens": {
                    "session_active": True,
                    "next_phrase_cue_id": "cue:A:break",
                },
            },
        }
    path.write_text(
        json.dumps({"schema_version": 1, "passed": physical and course3, "stages": stages}),
        encoding="utf-8",
    )
    return path


def _course3_readiness(path: Path) -> Path:
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "passed": False,
                "requirement": "course3",
                "readiness": {
                    "screen_learn": False,
                    "physical_learn": False,
                    "course3_audio": False,
                },
                "blockers": [
                    "port 8765 is occupied by python3.1 pid 85484, not the Vibemix Learn sidecar websocket",
                    "current macOS output route is 'MacBook Pro Speakers', not a loopback capture device",
                    "direct loopback capture is silent",
                    "macOS now-playing app is 'WebKit GPU', not Rekordbox",
                ],
                "course3_audio_diagnosis": {
                    "code": "macos_output_not_loopback",
                    "severity": "fix_route",
                    "next_action": "Route macOS output to the selected loopback device.",
                },
                "course3_route_doctor": {
                    "ok": False,
                    "status": "fix_route",
                    "diagnosis_code": "macos_output_not_loopback",
                    "route": "BlackHole 16ch @ 48000Hz",
                    "next_step": (
                        "Free 127.0.0.1:8765 so the Vibemix Learn sidecar owns "
                        "the app socket."
                    ),
                    "operator_steps": [
                        "Free 127.0.0.1:8765 so the Vibemix Learn sidecar owns the app socket.",
                        "Route macOS/Rekordbox output to BlackHole 16ch or the intended loopback route.",
                        "Play a real Rekordbox library track through the routed master output.",
                        "Stop unrelated browser/system media so Now Playing can point at Rekordbox.",
                    ],
                    "readiness_command": (
                        "uv run python scripts/learn_live_readiness.py --require course3 "
                        "--out /tmp/vibemix-live-learn-proof/learn-course3-readiness-current.json"
                    ),
                    "proof_command": (
                        "uv run python scripts/run_learn_live_proof.py --course3 "
                        "--say-course3-prompts --require-count-in "
                        "--out /tmp/vibemix-live-learn-proof/proof-course3-auto-master-current.json"
                    ),
                    "uses_spoken_prompt": True,
                    "auto_master_recommendation": {
                        "ok": True,
                        "source": "capture_matrix",
                        "reason": "strongest_loopback_candidate",
                        "device_name": "BlackHole 16ch",
                        "sample_rate": 48000,
                        "live_signal": False,
                    },
                },
                "auto_master_recommendation": {
                    "ok": True,
                    "source": "capture_matrix",
                    "reason": "strongest_loopback_candidate",
                    "device_name": "BlackHole 16ch",
                    "sample_rate": 48000,
                    "live_signal": False,
                },
                "checks": {
                    "sidecar_socket": {
                        "ok": False,
                        "listener": {"command": "python3.1", "pid": "85484"},
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    return path


def _physical_readiness(path: Path) -> Path:
    doctor = {
        "ok": False,
        "status": "missing_midi",
        "next_step": (
            "Use a data-capable USB cable or powered adapter, then wait for DDJ-FLX4 in MIDI."
        ),
        "operator_steps": [
            "Use a data-capable USB cable or powered adapter, then wait for DDJ-FLX4 in MIDI.",
            "Confirm macOS sees DDJ-FLX4 in USB or audio devices before starting the proof.",
        ],
        "readiness_command": (
            "uv run python scripts/learn_live_readiness.py --require physical "
            "--out /tmp/vibemix-live-learn-proof/learn-physical-readiness-current.json"
        ),
        "proof_command": (
            "uv run python scripts/run_learn_live_proof.py --start-app --no-screen "
            "--physical --wait-physical-seconds 30 --physical-seconds 40 "
            "--say-physical-prompts --auto-master-input "
            "--out /tmp/vibemix-live-learn-proof/proof-physical-ddj-current.json"
        ),
        "uses_spoken_prompt": True,
    }
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "passed": False,
                "requirement": "physical",
                "readiness": {
                    "screen_learn": True,
                    "physical_learn": False,
                    "course3_audio": True,
                },
                "blockers": [
                    "physical controller is not visible as a MIDI input",
                    "physical controller is not visible on USB or controller audio",
                ],
                "hardware_connection": {
                    "bluetooth_midi_only": False,
                    "bluetooth_midi_matches": [],
                    "controller_hardware_ready": False,
                },
                "physical_connection_doctor": doctor,
            }
        ),
        encoding="utf-8",
    )
    return path


def test_verifier_separates_static_package_pass_from_release_ready(
    monkeypatch,
    tmp_path: Path,
) -> None:
    tauri = _tauri_smoke(tmp_path / "learn-tauri-smoke-current.json")
    python = _python_quality(tmp_path / verifier.PYTHON_QUALITY_NAME)
    frontend = _frontend_quality(tmp_path / verifier.FRONTEND_QUALITY_NAME)
    desktop = _desktop_quality(tmp_path / verifier.DESKTOP_QUALITY_NAME)
    live = _live_artifact(tmp_path / "proof-current.json")
    monkeypatch.setattr(verifier, "audit_curriculum", lambda frontend_path=None: _curriculum_report())
    monkeypatch.setattr(
        verifier,
        "audit_packaged_bank",
        lambda *args, **kwargs: _exemplar_report(),
    )

    report = verifier.verify_package(
        proof_dir=tmp_path,
        tauri_smoke_path=tauri,
        python_quality_path=python,
        frontend_quality_path=frontend,
        desktop_quality_path=desktop,
        live_proof_paths=[live],
    )

    assert report["passed"] is True
    assert report["release_ready"] is False
    assert report["non_external_ready"] is False
    assert report["deferred_external_blocker_ids"] == [
        "packaged_eq_exemplar_ear_pass",
        "course3_live_audio_play_mode",
    ]
    assert report["internal_blocker_ids"] == ["physical_controller_path"]
    assert report["sections"]["curriculum"]["beginner_lessons"] == 36
    assert report["sections"]["curriculum"]["flow_contract_summary"][
        "beginner_flows_ok"
    ] is True
    assert report["sections"]["curriculum"]["transcript_inventory"]["ok"] is True
    assert (
        report["sections"]["curriculum"]["course_pack_contract"]["frontend_contract"][
            "manual_frontend_edits"
        ]
        == "forbidden"
    )
    assert report["sections"]["launched_tauri_smoke"]["passed"] is True
    assert report["sections"]["python_quality"]["passed"] is True
    assert report["sections"]["frontend_quality"]["passed"] is True
    assert report["sections"]["desktop_quality"]["passed"] is True
    matrix = report["completion_matrix"]
    assert matrix["summary"]["release_ready"] is False
    objective_audit = report["objective_audit"]
    assert objective_audit["summary"] == {
        "total": 9,
        "proven": 6,
        "not_proven": 3,
        "release_ready": False,
        "blocking_objective_ids": [
            "physical_or_on_screen_practice_paths",
            "course3_live_play_mode",
            "audible_example_quality",
        ],
    }
    objectives = {
        row["id"]: row
        for row in objective_audit["objectives"]
    }
    assert objectives["full_36_lesson_beginner_module"]["status"] == "proven"
    assert objectives["simple_practice_booth_no_syllabus_wall"]["status"] == "proven"
    assert objectives["grounded_adaptive_teaching_loop"]["status"] == "proven"
    assert objectives["existing_coded_power_reuse"]["status"] == "proven"
    assert objectives["future_course_extensibility"]["status"] == "proven"
    assert objectives["app_wiring_and_quality"]["status"] == "proven"
    assert objectives["physical_or_on_screen_practice_paths"]["blocking_row_ids"] == [
        "physical_controller_path"
    ]
    assert objectives["course3_live_play_mode"]["blocking_row_ids"] == [
        "course3_live_audio_play_mode"
    ]
    assert objectives["audible_example_quality"]["blocking_row_ids"] == [
        "packaged_eq_exemplar_ear_pass"
    ]
    assert {
        row["id"]: row["status"]
        for row in matrix["requirements"]
    }["frontend_quality_suite"] == "proven"
    assert {
        row["id"]: row["status"]
        for row in matrix["requirements"]
    }["frontstage_simplicity_contract"] == "proven"
    frontstage_evidence = {
        row["id"]: row["evidence"]
        for row in matrix["requirements"]
    }["frontstage_simplicity_contract"]
    assert frontstage_evidence["frontstage_default"] == (
        "primary recommended action plus opt-in chooser"
    )
    assert frontstage_evidence["hardware_unavailable"] == (
        "controller disconnect leaves the booth on the on-screen deck, "
        "keeps the lesson map opt-in, and repaints the active lesson "
        "highlight after mid-lesson remounts"
    )
    assert "tests/learn/test_practice_booth_shell.spec.ts" in frontstage_evidence[
        "covered_tests"
    ]
    assert "tests/learn/test_tutor_speak_sr_announcement.spec.ts" in frontstage_evidence[
        "covered_tests"
    ]
    assert frontstage_evidence["action_receipts"] == (
        "matched learner actions render a compact receipt naming the "
        "control gesture, known input source, and action count; the "
        "same receipt is announced through the tutor live region"
    )
    assert frontstage_evidence["completion_reward"] == (
        "completed lessons return to the one-action booth with a "
        "short visible pass reward that distinguishes clean vs "
        "hint-recovered completions, names the matched hardware/screen "
        "source when known, and carries an accessible next-practice "
        "label pointing at the refreshed recommendation"
    )
    assert frontstage_evidence["in_progress_recommendation"] == (
        "started-but-unfinished recommended lessons are labeled "
        "retry on the primary booth action while still restarting "
        "through the deterministic fresh lesson path"
    )
    assert frontstage_evidence["chooser_disclosure_control"] == (
        "the optional lesson chooser is a real disclosure control "
        "with aria-controls and aria-expanded state, closes on "
        "Escape or lesson pick, and restores focus when the user "
        "dismisses it"
    )
    assert frontstage_evidence["screen_fallback_action_label"] == (
        "when a required control is not represented in the active "
        "controller SVG, the one fallback screen-action button "
        "keeps the deterministic ACK path and names the exact "
        "fallback action in aria/title text"
    )
    assert frontstage_evidence["adaptive_retry_primer"] == (
        "unfinished lessons with persisted hint strikes keep the "
        "booth one-action simple while surfacing a compact "
        "hint-ready retry cue and moving exact hint counts into "
        "aria/title text"
    )
    assert frontstage_evidence["practice_source_memory"] == (
        "MIDI/controller and on-screen deck actions are persisted "
        "as backstage hardware/screen practice-source counts in "
        "LearnProgress, giving future coaching/profile logic real "
        "learner data without adding frontstage chrome"
    )
    assert {
        row["id"]: row["status"]
        for row in matrix["requirements"]
    }["lesson_choice_replay_contract"] == "proven"
    choice_evidence = {
        row["id"]: row["evidence"]
        for row in matrix["requirements"]
    }["lesson_choice_replay_contract"]
    assert choice_evidence["hud_replay_affordance"] == (
        "completed HUD progress dots announce press-to-replay, "
        "current dots announce the current step, and pending dots "
        "announce the prerequisite lock"
    )
    assert choice_evidence["progress_list_affordance"] == (
        "completed lesson-map rows announce press-to-replay, "
        "in-progress rows announce retry, and locked rows keep "
        "the exact lock reason in aria/title text"
    )
    assert {
        row["id"]: row["status"]
        for row in matrix["requirements"]
    }["browser_practice_booth_quality_contract"] == "proven"
    browser_evidence = {
        row["id"]: row["evidence"]
        for row in matrix["requirements"]
    }["browser_practice_booth_quality_contract"]
    assert browser_evidence["required_command"] == "learn_browser_booth_playwright"
    assert (
        "recommended L1.01 completes through Tauri forwarder and direct WebSocket fallback"
        in browser_evidence["browser_claims"]
    )
    assert (
        "wrong on-screen EQ move reaches the Python sidecar, renders a grounded citation chip, and recovers to lesson completion"
        in browser_evidence["browser_claims"]
    )
    assert {
        row["id"]: row["status"]
        for row in matrix["requirements"]
    }["app_entry_contract"] == "proven"
    assert {
        row["id"]: row["status"]
        for row in matrix["requirements"]
    }["tauri_learn_window_contract"] == "proven"
    tauri_window_evidence = {
        row["id"]: row["evidence"]
        for row in matrix["requirements"]
    }["tauri_learn_window_contract"]
    assert tauri_window_evidence["required_frontend_command"] == "learn_tauri_window_vitest"
    assert (
        tauri_window_evidence["required_desktop_command"]
        == "learn_cargo_learn_window_test"
    )
    assert tauri_window_evidence["window_label"] == "learn"
    assert tauri_window_evidence["webview_url"] == "learn.html"
    assert {
        row["id"]: row["status"]
        for row in matrix["requirements"]
    }["python_quality_suite"] == "proven"
    assert {
        row["id"]: row["status"]
        for row in matrix["requirements"]
    }["all_lessons_runtime_contract"] == "proven"
    runtime_evidence = {
        row["id"]: row["evidence"]
        for row in matrix["requirements"]
    }["all_lessons_runtime_contract"]
    assert runtime_evidence["required_command"] == "learn_all_lessons_runtime_pytest"
    assert runtime_evidence["lesson_count"] == 36
    assert runtime_evidence["observer_lessons"] == ["L1.14", "L1.16", "L2.14"]
    assert "ipc.learn.start_lesson" in runtime_evidence["runtime_path"]
    assert {
        row["id"]: row["status"]
        for row in matrix["requirements"]
    }["teaching_loop_contract"] == "proven"
    teaching_loop_evidence = {
        row["id"]: row["evidence"]
        for row in matrix["requirements"]
    }["teaching_loop_contract"]
    assert teaching_loop_evidence["teaching_grounding_contract"] == {
        "ok": True,
        "teaching_turn_count": 76,
        "grounded_teaching_turn_count": 76,
        "cited_teaching_turn_count": 76,
        "failing_lesson_ids": [],
    }
    assert teaching_loop_evidence["hint_grounding_contract"] == {
        "ok": True,
        "hint_turn_count": 228,
        "grounded_hint_turn_count": 228,
        "cited_hint_turn_count": 228,
        "failing_lesson_ids": [],
    }
    assert {
        row["id"]: row["status"]
        for row in matrix["requirements"]
    }["adaptive_coaching_runtime_contract"] == "proven"
    adaptive_evidence = {
        row["id"]: row["evidence"]
        for row in matrix["requirements"]
    }["adaptive_coaching_runtime_contract"]
    assert adaptive_evidence["required_command"] == "learn_adaptive_coaching_pytest"
    assert adaptive_evidence["citation_sources"] == ["midi", "screen"]
    assert (
        "wrong screen control emits teaching_loop.turn_kind=adapt without advancing"
        in adaptive_evidence["runtime_behaviors"]
    )
    assert {
        row["id"]: row["status"]
        for row in matrix["requirements"]
    }["course3_auto_master_finder_contract"] == "proven"
    auto_master_evidence = {
        row["id"]: row["evidence"]
        for row in matrix["requirements"]
    }["course3_auto_master_finder_contract"]
    assert auto_master_evidence["required_command"] == "learn_auto_master_finder_pytest"
    assert (
        "rate-mismatched fallbacks are rejected before app startup"
        in auto_master_evidence["finder_claims"]
    )
    assert {
        row["id"]: row["status"]
        for row in matrix["requirements"]
    }["course3_mix_count_in_anchor_contract"] == "proven"
    mix_anchor_evidence = {
        row["id"]: row["evidence"]
        for row in matrix["requirements"]
    }["course3_mix_count_in_anchor_contract"]
    assert mix_anchor_evidence["required_command"] == "learn_course3_mix_anchor_pytest"
    assert (
        "mix-state anchors require an exact unambiguous Now Playing title match"
        in mix_anchor_evidence["anchor_policy"]
    )
    assert {
        row["id"]: row["status"]
        for row in matrix["requirements"]
    }["session_debrief_profile_contract"] == "proven"
    session_evidence = {
        row["id"]: row["evidence"]
        for row in matrix["requirements"]
    }["session_debrief_profile_contract"]
    assert "tests/learn/test_graduation.py" in session_evidence["covered_tests"]
    assert session_evidence["graduation_practice_summary"] == (
        "the L3.06 graduation handoff can fold persisted "
        "hardware/screen practice-source memory into one grounded "
        "status line without adding a dashboard"
    )
    assert {
        row["id"]: row["status"]
        for row in matrix["requirements"]
    }["desktop_shell_quality"] == "proven"
    assert {
        row["id"]: row["status"]
        for row in matrix["requirements"]
    }["future_course_extension_contract"] == "proven"
    extension_evidence = {
        row["id"]: row["evidence"]
        for row in matrix["requirements"]
    }["future_course_extension_contract"]
    assert extension_evidence["frontend_contract"]["manual_frontend_edits"] == "forbidden"
    assert (
        extension_evidence["draft_validator"]["function"]
        == "vibemix.learn.course_pack.validate_course_pack_draft"
    )
    assert (
        extension_evidence["draft_validator"]["cli"]
        == "uv run python scripts/validate_learn_course_pack.py <course-pack.json>"
    )
    assert extension_evidence["draft_validator"]["template_cli"] == (
        "uv run python scripts/validate_learn_course_pack.py "
        "--init-template <dir> --course-number 4 --slug <slug>"
    )
    assert "flow_preview" in extension_evidence["draft_validator"]["result_fields"]
    assert "integration_plan" in extension_evidence["draft_validator"]["result_fields"]
    assert "prompt_contract" in extension_evidence["draft_validator"]["result_fields"]
    assert "teaching_grounding_contract" in extension_evidence["draft_validator"][
        "result_fields"
    ]
    assert "hint_grounding_contract" in extension_evidence["draft_validator"][
        "result_fields"
    ]
    assert "authoring_contract" in extension_evidence["draft_validator"][
        "result_fields"
    ]
    assert "copy_truthfulness" in extension_evidence["draft_validator"]["result_fields"]
    assert extension_evidence["prompt_contract"] == {
        "max_chars": 150,
        "max_words": 24,
        "max_sentences": 2,
        "single_line": True,
        "inline_lists_forbidden": True,
    }
    assert extension_evidence["teaching_loop_contract"] == {
        "teaching_turns": (
            "every compiled step must plan through plan_teaching_turn, "
            "remain grounded, and carry a citation"
        ),
        "hint_turns": (
            "the first three adaptive hints must plan through plan_hint_turn, "
            "remain grounded, and carry citations"
        ),
    }
    assert extension_evidence["canonical_id_contract"] == {
        "course_id_pattern": "course_<number>_<slug>",
        "lesson_id_pattern": "L<number>.<two digits>",
        "rule": (
            "Future course-pack lesson IDs must match the numeric course "
            "prefix and be contiguous from .01."
        ),
        "starter_template": "scripts/validate_learn_course_pack.py --init-template",
    }
    assert extension_evidence["starter_template_contract"] == {
        "writes_manifest_authoring_contract": True,
        "frontstage": "one prompt, one action, one grounded response",
        "default_input_surfaces": ["hardware", "screen"],
        "starter_expected_action": {
            "type": "button",
            "control": "cue",
            "deck": "A",
            "direction": "down",
        },
        "required_hint_count": 3,
        "prompt_limits": {
            "max_chars": 150,
            "max_words": 24,
            "max_sentences": 2,
            "single_line": True,
            "inline_lists_forbidden": True,
        },
        "copy_rules": [
            "cite the observable control on every teaching and hint turn",
            "do not promise automatic debrief opening",
        ],
        "post_merge_commands": [
            "uv run python scripts/export_learn_curriculum_meta.py --check",
            "uv run pytest -q tests/learn/test_course_pack.py",
            (
                "uv run python scripts/run_learn_perfection_package.py --out "
                "/tmp/vibemix-live-learn-proof/learn-perfection-package-current.json"
            ),
        ],
    }
    assert "debrief opens" in extension_evidence["copy_truthfulness_contract"][
        "unsupported_auto_open_phrases"
    ]
    assert (
        "uv run python scripts/export_learn_curriculum_meta.py --check"
        in extension_evidence["verification_commands"]
    )
    assert (
        "uv run pytest -q tests/learn/test_course_pack.py"
        in extension_evidence["verification_commands"]
    )
    assert (
        "uv run python scripts/validate_learn_course_pack.py <course-pack.json>"
        in extension_evidence["verification_commands"]
    )
    assert {
        row["id"]: row["evidence"]
        for row in matrix["requirements"]
    }["curriculum_36_lesson_contract"]["flow_contract_summary"]["min_hint_count"] == 3
    flow_summary = {
        row["id"]: row["evidence"]
        for row in matrix["requirements"]
    }["curriculum_36_lesson_contract"]["flow_contract_summary"]
    assert flow_summary["verification_kind_counts"] == {
        "button_press": 51,
        "cc_delta": 25,
    }
    assert flow_summary["prompt_contract"]["ok"] is True
    assert flow_summary["prompt_contract"]["observed_max_chars"] == 115
    assert flow_summary["teaching_grounding_contract"] == {
        "ok": True,
        "teaching_turn_count": 76,
        "grounded_teaching_turn_count": 76,
        "cited_teaching_turn_count": 76,
        "failing_lesson_ids": [],
    }
    assert flow_summary["hint_grounding_contract"] == {
        "ok": True,
        "hint_turn_count": 228,
        "grounded_hint_turn_count": 228,
        "cited_hint_turn_count": 228,
        "failing_lesson_ids": [],
    }
    assert flow_summary["input_surface_step_counts"] == {
        "hardware+screen": 32,
        "screen": 44,
    }
    assert {
        row["id"]: row["evidence"]
        for row in matrix["requirements"]
    }["curriculum_36_lesson_contract"]["transcript_inventory"]["orphan_paths"] == []
    assert {
        row["id"]: row["evidence"]
        for row in matrix["requirements"]
    }["curriculum_36_lesson_contract"]["unlock_gate_contract"][
        "unsupported_unlock_gates"
    ] == []
    assert {
        row["id"]: row["evidence"]
        for row in matrix["requirements"]
    }["curriculum_36_lesson_contract"]["copy_truthfulness_contract"][
        "unsupported_debrief_auto_open_claims"
    ] == []
    assert "--list-devices" in report["sections"]["exemplars"]["operator_commands"][
        "list_output_devices"
    ]
    assert report["sections"]["live_proofs"]["screen"]["passed"] is True
    assert report["sections"]["live_proofs"]["physical"]["status"] == "unavailable"
    physical_commands = report["sections"]["live_proofs"]["physical"]["operator_commands"]
    assert "sniff_controller.py --list" in physical_commands["list_controller"]
    assert "--require physical" in physical_commands["readiness"]
    assert "--physical" in physical_commands["proof"]
    assert "--say-physical-prompts" in physical_commands["proof"]
    assert "proof-physical-ddj-current.json" in physical_commands["proof"]
    assert report["sections"]["live_proofs"]["course3"]["status"] == "unavailable"
    course3_commands = report["sections"]["live_proofs"]["course3"]["operator_commands"]
    assert "--require course3" in course3_commands["readiness"]
    assert "learn-course3-readiness-current.json" in course3_commands["readiness"]
    assert "--start-app" in course3_commands["proof"]
    assert "--auto-master-input" in course3_commands["proof"]
    assert "--require-count-in" in course3_commands["proof"]
    assert "--say-course3-prompts" in course3_commands["proof"]
    assert "--loopback-self-test-seconds 1" in course3_commands["proof"]
    assert "proof-course3-auto-master-current.json" in course3_commands["proof"]
    assert "verify_learn_package.py" in course3_commands["verify"]
    assert "packaged EQ exemplar human ear-pass is pending" in report["completion_blockers"]
    assert any(
        "--list-devices" in action
        and "--say-prompts" in action
        and "--audition" in action
        and "--approve-ear-pass" in action
        for action in report["next_actions"]
    )
    assert "physical controller lesson proof is not strictly proven" in report[
        "completion_blockers"
    ]
    assert "Course 3 routed-audio count-in proof is not strictly proven" in report[
        "completion_blockers"
    ]
    recipe = {row["id"]: row for row in report["release_blocker_recipe"]}
    assert set(recipe) == {
        "packaged_eq_exemplar_ear_pass",
        "physical_controller_path",
        "course3_live_audio_play_mode",
    }
    assert recipe["packaged_eq_exemplar_ear_pass"]["status"] == (
        "pending_human_ear_pass"
    )
    assert recipe["packaged_eq_exemplar_ear_pass"]["operator_action"]["steps"][0].endswith(
        "--list-devices"
    )
    assert "--device-index" in recipe["packaged_eq_exemplar_ear_pass"][
        "operator_steps"
    ][1]
    assert "--say-prompts" in recipe["packaged_eq_exemplar_ear_pass"][
        "operator_steps"
    ][1]
    assert "--audition" in recipe["packaged_eq_exemplar_ear_pass"]["commands"][
        "approve"
    ]
    assert "--list-devices" in recipe["packaged_eq_exemplar_ear_pass"]["commands"][
        "list_output_devices"
    ]
    assert "sniff_controller.py --list" in recipe["physical_controller_path"][
        "commands"
    ]["list_controller"]
    assert "--physical" in recipe["physical_controller_path"]["commands"]["proof"]
    assert "--say-physical-prompts" in recipe["physical_controller_path"]["commands"][
        "proof"
    ]
    assert "--require course3" in recipe["course3_live_audio_play_mode"]["commands"][
        "readiness"
    ]
    assert "--require-count-in" in recipe["course3_live_audio_play_mode"]["commands"][
        "proof"
    ]
    assert "--say-course3-prompts" in recipe["course3_live_audio_play_mode"]["commands"][
        "proof"
    ]
    assert recipe["course3_live_audio_play_mode"]["operator_action"]["steps"][-1] == (
        "Rerun the Course 3 proof command; it will speak the route/playback moment."
    )


def test_verifier_can_mark_non_external_ready_when_only_deferred_gates_remain(
    monkeypatch,
    tmp_path: Path,
) -> None:
    tauri = _tauri_smoke(tmp_path / "learn-tauri-smoke-current.json")
    python = _python_quality(tmp_path / verifier.PYTHON_QUALITY_NAME)
    frontend = _frontend_quality(tmp_path / verifier.FRONTEND_QUALITY_NAME)
    desktop = _desktop_quality(tmp_path / verifier.DESKTOP_QUALITY_NAME)
    live = _live_artifact(tmp_path / "proof-current.json", physical=True)
    monkeypatch.setattr(verifier, "audit_curriculum", lambda frontend_path=None: _curriculum_report())
    monkeypatch.setattr(
        verifier,
        "audit_packaged_bank",
        lambda *args, **kwargs: _exemplar_report(),
    )

    report = verifier.verify_package(
        proof_dir=tmp_path,
        tauri_smoke_path=tauri,
        python_quality_path=python,
        frontend_quality_path=frontend,
        desktop_quality_path=desktop,
        live_proof_paths=[live],
    )

    assert report["passed"] is True
    assert report["release_ready"] is False
    assert report["non_external_ready"] is True
    assert report["deferred_external_blocker_ids"] == [
        "packaged_eq_exemplar_ear_pass",
        "course3_live_audio_play_mode",
    ]
    assert report["internal_blocker_ids"] == []
    assert report["internal_blockers"] == []
    assert "human ear-pass" in report["non_external_ready_rule"]


def test_verifier_uses_fresh_course3_readiness_for_release_recipe(
    monkeypatch,
    tmp_path: Path,
) -> None:
    tauri = _tauri_smoke(tmp_path / "learn-tauri-smoke-current.json")
    python = _python_quality(tmp_path / verifier.PYTHON_QUALITY_NAME)
    frontend = _frontend_quality(tmp_path / verifier.FRONTEND_QUALITY_NAME)
    desktop = _desktop_quality(tmp_path / verifier.DESKTOP_QUALITY_NAME)
    live = _live_artifact(tmp_path / "proof-current.json", physical=True)
    _course3_readiness(tmp_path / verifier.COURSE3_READINESS_NAME)
    monkeypatch.setattr(verifier, "audit_curriculum", lambda frontend_path=None: _curriculum_report())
    monkeypatch.setattr(
        verifier,
        "audit_packaged_bank",
        lambda *args, **kwargs: _exemplar_report(release_ready=True),
    )

    report = verifier.verify_package(
        proof_dir=tmp_path,
        tauri_smoke_path=tauri,
        python_quality_path=python,
        frontend_quality_path=frontend,
        desktop_quality_path=desktop,
        live_proof_paths=[live],
    )

    course3 = report["sections"]["live_proofs"]["course3"]
    assert course3["readiness_status"]["path"].endswith(verifier.COURSE3_READINESS_NAME)
    assert (
        "port 8765 is occupied by python3.1 pid 85484, not the Vibemix Learn sidecar websocket"
        in course3["blockers"]
    )
    assert course3["operator_commands"]["manual_action"].startswith(
        "Free 127.0.0.1:8765"
    )
    assert course3["operator_commands"]["current_fallback_candidate"] == {
        "name": "BlackHole 16ch",
        "sample_rate": 48000,
        "reason": "strongest_loopback_candidate",
        "source": "capture_matrix",
        "live_signal": False,
    }

    recipe = {row["id"]: row for row in report["release_blocker_recipe"]}
    course3_recipe = recipe["course3_live_audio_play_mode"]
    assert course3_recipe["readiness_status"]["status"] == "fix_route"
    assert course3_recipe["course3_route_doctor"]["route"] == "BlackHole 16ch @ 48000Hz"
    assert course3_recipe["operator_steps"][:4] == [
        "Free 127.0.0.1:8765 so the Vibemix Learn sidecar owns the app socket.",
        "Route macOS/Rekordbox output to BlackHole 16ch or the intended loopback route.",
        "Play a real Rekordbox library track through the routed master output.",
        "Stop unrelated browser/system media so Now Playing can point at Rekordbox.",
    ]
    assert report["next_actions"] == [
        "Free 127.0.0.1:8765 so the Vibemix Learn sidecar owns the app socket."
    ]


def test_verifier_uses_fresh_physical_readiness_for_release_recipe(
    monkeypatch,
    tmp_path: Path,
) -> None:
    tauri = _tauri_smoke(tmp_path / "learn-tauri-smoke-current.json")
    python = _python_quality(tmp_path / verifier.PYTHON_QUALITY_NAME)
    frontend = _frontend_quality(tmp_path / verifier.FRONTEND_QUALITY_NAME)
    desktop = _desktop_quality(tmp_path / verifier.DESKTOP_QUALITY_NAME)
    live = _live_artifact(tmp_path / "proof-current.json")
    readiness_path = _physical_readiness(tmp_path / verifier.PHYSICAL_READINESS_NAME)
    monkeypatch.setattr(verifier, "audit_curriculum", lambda frontend_path=None: _curriculum_report())
    monkeypatch.setattr(
        verifier,
        "audit_packaged_bank",
        lambda *args, **kwargs: _exemplar_report(release_ready=True),
    )

    report = verifier.verify_package(
        proof_dir=tmp_path,
        tauri_smoke_path=tauri,
        python_quality_path=python,
        frontend_quality_path=frontend,
        desktop_quality_path=desktop,
        live_proof_paths=[live],
    )

    physical = report["sections"]["live_proofs"]["physical"]
    assert physical["readiness_status"]["path"] == str(readiness_path)
    assert physical["physical_connection_doctor"]["status"] == "missing_midi"
    assert physical["operator_commands"]["manual_action"] == (
        "Use a data-capable USB cable or powered adapter, then wait for DDJ-FLX4 in MIDI."
    )
    assert "physical controller is not visible on USB or controller audio" in physical[
        "blockers"
    ]

    recipe = {row["id"]: row for row in report["release_blocker_recipe"]}
    physical_recipe = recipe["physical_controller_path"]
    assert physical_recipe["readiness_status"]["status"] == "missing_midi"
    assert physical_recipe["operator_steps"] == [
        "Use a data-capable USB cable or powered adapter, then wait for DDJ-FLX4 in MIDI.",
        "Confirm macOS sees DDJ-FLX4 in USB or audio devices before starting the proof.",
    ]
    assert report["next_actions"][0] == (
        "Use a data-capable USB cable or powered adapter, then wait for DDJ-FLX4 in MIDI."
    )

    matrix = {
        row["id"]: row["evidence"]
        for row in report["completion_matrix"]["requirements"]
    }
    assert matrix["physical_controller_path"]["readiness_status"]["status"] == "missing_midi"


def test_verifier_does_not_downgrade_passed_physical_proof_with_stale_readiness(
    monkeypatch,
    tmp_path: Path,
) -> None:
    tauri = _tauri_smoke(tmp_path / "learn-tauri-smoke-current.json")
    python = _python_quality(tmp_path / verifier.PYTHON_QUALITY_NAME)
    frontend = _frontend_quality(tmp_path / verifier.FRONTEND_QUALITY_NAME)
    desktop = _desktop_quality(tmp_path / verifier.DESKTOP_QUALITY_NAME)
    live = _live_artifact(tmp_path / "proof-current.json", physical=True, course3=True)
    readiness_path = _physical_readiness(tmp_path / verifier.PHYSICAL_READINESS_NAME)
    monkeypatch.setattr(verifier, "audit_curriculum", lambda frontend_path=None: _curriculum_report())
    monkeypatch.setattr(
        verifier,
        "audit_packaged_bank",
        lambda *args, **kwargs: _exemplar_report(release_ready=True),
    )

    report = verifier.verify_package(
        proof_dir=tmp_path,
        tauri_smoke_path=tauri,
        python_quality_path=python,
        frontend_quality_path=frontend,
        desktop_quality_path=desktop,
        live_proof_paths=[live],
    )

    physical = report["sections"]["live_proofs"]["physical"]
    assert physical["passed"] is True
    assert physical["status"] == "passed"
    assert physical["blockers"] == []
    assert physical["readiness_status"]["path"] == str(readiness_path)
    assert physical["readiness_status"]["status"] == "missing_midi"
    assert physical["physical_connection_doctor"] is None
    assert all(row["id"] != "physical_controller_path" for row in report["release_blocker_recipe"])

    matrix = {
        row["id"]: row["evidence"]
        for row in report["completion_matrix"]["requirements"]
    }
    assert matrix["physical_controller_path"]["readiness_status"]["status"] == "missing_midi"
    assert matrix["physical_controller_path"]["physical_connection_doctor"] is None


def test_verifier_surfaces_course3_probe_operator_action(
    monkeypatch,
    tmp_path: Path,
) -> None:
    tauri = _tauri_smoke(tmp_path / "learn-tauri-smoke-current.json")
    live = _live_artifact(tmp_path / "proof-current.json", physical=True)
    operator_action = {
        "prompt": "Open one channel.",
        "route": "live Course 3 socket lens",
        "steps": [
            "Raise the playing channel fader while the deck is audible.",
            "Keep master up until the Course 3 lens sees routed deck audio.",
        ],
    }
    artifact = json.loads(live.read_text(encoding="utf-8"))
    artifact["stages"]["course3_probe"] = {
        "status": "failed",
        "result": {
            "passed": False,
            "lens_frames": 3,
            "active_seen": False,
            "count_in_seen": False,
            "diagnostics": {
                "blockers": ["audible audio stayed unattributed to an open deck"],
                "operator_action": operator_action,
            },
            "last_lens": {
                "session_active": True,
                "audio_active": True,
                "operator_action": {
                    "prompt": "Load a track.",
                    "steps": ["Load a Rekordbox library track."],
                },
            },
        },
    }
    live.write_text(json.dumps(artifact), encoding="utf-8")
    monkeypatch.setattr(verifier, "audit_curriculum", lambda frontend_path=None: _curriculum_report())
    monkeypatch.setattr(
        verifier,
        "audit_packaged_bank",
        lambda *args, **kwargs: _exemplar_report(release_ready=True),
    )

    report = verifier.verify_package(
        proof_dir=tmp_path,
        tauri_smoke_path=tauri,
        live_proof_paths=[live],
    )

    course3 = report["sections"]["live_proofs"]["course3"]
    assert course3["status"] == "failed"
    assert course3["probe_operator_action"] == operator_action
    assert course3["attempts"][0]["probe_operator_action"] == operator_action
    assert course3["operator_commands"]["manual_action"] == "Open one channel."
    assert course3["operator_commands"]["operator_action"] == operator_action
    assert "Open one channel." in report["next_actions"]

    recipe = {row["id"]: row for row in report["release_blocker_recipe"]}
    course3_recipe = recipe["course3_live_audio_play_mode"]
    assert course3_recipe["operator_action"] == operator_action
    assert course3_recipe["operator_steps"] == operator_action["steps"]

    matrix = {
        row["id"]: row["evidence"]
        for row in report["completion_matrix"]["requirements"]
    }
    assert matrix["course3_live_audio_play_mode"]["probe_operator_action"] == operator_action


def test_verifier_reports_release_ready_only_when_all_completion_evidence_exists(
    monkeypatch,
    tmp_path: Path,
) -> None:
    tauri = _tauri_smoke(tmp_path / "learn-tauri-smoke-current.json")
    python = _python_quality(tmp_path / verifier.PYTHON_QUALITY_NAME)
    frontend = _frontend_quality(tmp_path / verifier.FRONTEND_QUALITY_NAME)
    desktop = _desktop_quality(tmp_path / verifier.DESKTOP_QUALITY_NAME)
    live = _live_artifact(tmp_path / "proof-current.json", physical=True, course3=True)
    monkeypatch.setattr(verifier, "audit_curriculum", lambda frontend_path=None: _curriculum_report())
    monkeypatch.setattr(
        verifier,
        "audit_packaged_bank",
        lambda *args, **kwargs: _exemplar_report(release_ready=True),
    )

    report = verifier.verify_package(
        proof_dir=tmp_path,
        tauri_smoke_path=tauri,
        python_quality_path=python,
        frontend_quality_path=frontend,
        desktop_quality_path=desktop,
        live_proof_paths=[live],
    )

    assert report["passed"] is True
    assert report["release_ready"] is True
    assert report["non_external_ready"] is True
    assert report["deferred_external_blocker_ids"] == []
    assert report["internal_blocker_ids"] == []
    assert report["completion_blockers"] == []
    assert report["release_blocker_recipe"] == []
    assert report["completion_matrix"]["summary"] == {
        "total": 22,
        "proven": 22,
        "not_proven": 0,
        "release_gate_total": 22,
        "release_gate_proven": 22,
        "release_ready": True,
    }
    assert report["objective_audit"]["summary"] == {
        "total": 9,
        "proven": 9,
        "not_proven": 0,
        "release_ready": True,
        "blocking_objective_ids": [],
    }


def test_verifier_rejects_incomplete_future_course_extension_contract(
    monkeypatch,
    tmp_path: Path,
) -> None:
    tauri = _tauri_smoke(tmp_path / "learn-tauri-smoke-current.json")
    python = _python_quality(tmp_path / verifier.PYTHON_QUALITY_NAME)
    frontend = _frontend_quality(tmp_path / verifier.FRONTEND_QUALITY_NAME)
    desktop = _desktop_quality(tmp_path / verifier.DESKTOP_QUALITY_NAME)
    live = _live_artifact(tmp_path / "proof-current.json", physical=True, course3=True)
    curriculum = _curriculum_report()
    broken_contract = dict(curriculum["course_pack_contract"])
    broken_frontend = dict(broken_contract["frontend_contract"])
    broken_frontend["manual_frontend_edits"] = "allowed"
    broken_contract["frontend_contract"] = broken_frontend
    broken_contract.pop("canonical_id_contract", None)
    broken_contract.pop("copy_truthfulness_contract", None)
    broken_contract.pop("starter_template_contract", None)
    broken_contract["verification_commands"] = [
        command
        for command in broken_contract["verification_commands"]
        if "export_learn_curriculum_meta.py --check" not in command
    ]
    curriculum["course_pack_contract"] = broken_contract
    monkeypatch.setattr(verifier, "audit_curriculum", lambda frontend_path=None: curriculum)
    monkeypatch.setattr(
        verifier,
        "audit_packaged_bank",
        lambda *args, **kwargs: _exemplar_report(release_ready=True),
    )

    report = verifier.verify_package(
        proof_dir=tmp_path,
        tauri_smoke_path=tauri,
        python_quality_path=python,
        frontend_quality_path=frontend,
        desktop_quality_path=desktop,
        live_proof_paths=[live],
    )

    extension_row = {
        row["id"]: row
        for row in report["completion_matrix"]["requirements"]
    }["future_course_extension_contract"]
    assert report["passed"] is True
    assert report["release_ready"] is False
    assert extension_row["status"] == "not_proven"
    assert "course extension frontend projection is not generated-only" in extension_row[
        "blockers"
    ]
    assert "course extension canonical course_id pattern is missing" in extension_row[
        "blockers"
    ]
    assert "course extension copy truthfulness phrases are missing" in extension_row[
        "blockers"
    ]
    assert "course extension starter template authoring contract is missing" in extension_row[
        "blockers"
    ]
    assert any("verification commands missing" in blocker for blocker in extension_row["blockers"])


def test_verifier_rejects_missing_tauri_smoke(monkeypatch, tmp_path: Path) -> None:
    live = _live_artifact(tmp_path / "proof-current.json", physical=True, course3=True)
    monkeypatch.setattr(verifier, "audit_curriculum", lambda frontend_path=None: _curriculum_report())
    monkeypatch.setattr(
        verifier,
        "audit_packaged_bank",
        lambda *args, **kwargs: _exemplar_report(release_ready=True),
    )

    report = verifier.verify_package(
        proof_dir=tmp_path,
        tauri_smoke_path=tmp_path / "missing.json",
        live_proof_paths=[live],
    )

    assert report["passed"] is False
    assert report["release_ready"] is False
    assert "launched Tauri Learn smoke is missing or failing" in report[
        "completion_blockers"
    ]


def test_verifier_rejects_missing_frontend_quality_artifact(
    monkeypatch,
    tmp_path: Path,
) -> None:
    tauri = _tauri_smoke(tmp_path / "learn-tauri-smoke-current.json")
    live = _live_artifact(tmp_path / "proof-current.json", physical=True, course3=True)
    monkeypatch.setattr(verifier, "audit_curriculum", lambda frontend_path=None: _curriculum_report())
    monkeypatch.setattr(
        verifier,
        "audit_packaged_bank",
        lambda *args, **kwargs: _exemplar_report(release_ready=True),
    )

    report = verifier.verify_package(
        proof_dir=tmp_path,
        tauri_smoke_path=tauri,
        live_proof_paths=[live],
    )

    assert report["passed"] is False
    assert report["release_ready"] is False
    assert report["sections"]["frontend_quality"]["status"] == "missing"
    assert "full Learn frontend quality gate is missing or failing" in report[
        "completion_blockers"
    ]
    assert {
        row["id"]: row["status"]
        for row in report["completion_matrix"]["requirements"]
    }["frontend_quality_suite"] == "not_proven"
    assert {
        row["id"]: row["status"]
        for row in report["completion_matrix"]["requirements"]
    }["frontstage_simplicity_contract"] == "not_proven"
    assert {
        row["id"]: row["status"]
        for row in report["completion_matrix"]["requirements"]
    }["lesson_choice_replay_contract"] == "not_proven"
    assert {
        row["id"]: row["status"]
        for row in report["completion_matrix"]["requirements"]
    }["browser_practice_booth_quality_contract"] == "not_proven"
    assert {
        row["id"]: row["status"]
        for row in report["completion_matrix"]["requirements"]
    }["app_entry_contract"] == "not_proven"
    assert {
        row["id"]: row["status"]
        for row in report["completion_matrix"]["requirements"]
    }["tauri_learn_window_contract"] == "not_proven"


def test_verifier_rejects_missing_python_quality_artifact(
    monkeypatch,
    tmp_path: Path,
) -> None:
    tauri = _tauri_smoke(tmp_path / "learn-tauri-smoke-current.json")
    _frontend_quality(tmp_path / verifier.FRONTEND_QUALITY_NAME)
    live = _live_artifact(tmp_path / "proof-current.json", physical=True, course3=True)
    monkeypatch.setattr(verifier, "audit_curriculum", lambda frontend_path=None: _curriculum_report())
    monkeypatch.setattr(
        verifier,
        "audit_packaged_bank",
        lambda *args, **kwargs: _exemplar_report(release_ready=True),
    )

    report = verifier.verify_package(
        proof_dir=tmp_path,
        tauri_smoke_path=tauri,
        live_proof_paths=[live],
    )

    assert report["passed"] is False
    assert report["release_ready"] is False
    assert report["sections"]["python_quality"]["status"] == "missing"
    assert "full Learn Python quality gate is missing or failing" in report[
        "completion_blockers"
    ]
    assert {
        row["id"]: row["status"]
        for row in report["completion_matrix"]["requirements"]
    }["python_quality_suite"] == "not_proven"
    assert {
        row["id"]: row["status"]
        for row in report["completion_matrix"]["requirements"]
    }["all_lessons_runtime_contract"] == "not_proven"
    assert {
        row["id"]: row["status"]
        for row in report["completion_matrix"]["requirements"]
    }["teaching_loop_contract"] == "not_proven"
    assert {
        row["id"]: row["status"]
        for row in report["completion_matrix"]["requirements"]
    }["adaptive_coaching_runtime_contract"] == "not_proven"
    assert {
        row["id"]: row["status"]
        for row in report["completion_matrix"]["requirements"]
    }["course3_auto_master_finder_contract"] == "not_proven"
    assert {
        row["id"]: row["status"]
        for row in report["completion_matrix"]["requirements"]
    }["course3_mix_count_in_anchor_contract"] == "not_proven"
    assert {
        row["id"]: row["status"]
        for row in report["completion_matrix"]["requirements"]
    }["session_debrief_profile_contract"] == "not_proven"


def test_verifier_rejects_missing_desktop_quality_artifact(
    monkeypatch,
    tmp_path: Path,
) -> None:
    tauri = _tauri_smoke(tmp_path / "learn-tauri-smoke-current.json")
    _python_quality(tmp_path / verifier.PYTHON_QUALITY_NAME)
    _frontend_quality(tmp_path / verifier.FRONTEND_QUALITY_NAME)
    live = _live_artifact(tmp_path / "proof-current.json", physical=True, course3=True)
    monkeypatch.setattr(verifier, "audit_curriculum", lambda frontend_path=None: _curriculum_report())
    monkeypatch.setattr(
        verifier,
        "audit_packaged_bank",
        lambda *args, **kwargs: _exemplar_report(release_ready=True),
    )

    report = verifier.verify_package(
        proof_dir=tmp_path,
        tauri_smoke_path=tauri,
        live_proof_paths=[live],
    )

    assert report["passed"] is False
    assert report["release_ready"] is False
    assert report["sections"]["desktop_quality"]["status"] == "missing"
    assert "Learn desktop shell quality gate is missing or failing" in report[
        "completion_blockers"
    ]
    assert {
        row["id"]: row["status"]
        for row in report["completion_matrix"]["requirements"]
    }["desktop_shell_quality"] == "not_proven"
    assert {
        row["id"]: row["status"]
        for row in report["completion_matrix"]["requirements"]
    }["tauri_learn_window_contract"] == "not_proven"


def test_verifier_discovers_exemplar_approval_under_proof_dir(
    monkeypatch,
    tmp_path: Path,
) -> None:
    tauri = _tauri_smoke(tmp_path / "learn-tauri-smoke-current.json")
    _python_quality(tmp_path / verifier.PYTHON_QUALITY_NAME)
    _frontend_quality(tmp_path / verifier.FRONTEND_QUALITY_NAME)
    _desktop_quality(tmp_path / verifier.DESKTOP_QUALITY_NAME)
    live = _live_artifact(tmp_path / "proof-current.json", physical=True, course3=True)
    approval = tmp_path / verifier.EXEMPLAR_APPROVAL_NAME
    approval.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(verifier, "audit_curriculum", lambda frontend_path=None: _curriculum_report())
    monkeypatch.setattr(
        verifier,
        "audit_packaged_bank",
        _exemplar_audit_for_approval(expected_path=approval),
    )

    report = verifier.verify_package(
        proof_dir=tmp_path,
        tauri_smoke_path=tauri,
        live_proof_paths=[live],
    )

    assert report["release_ready"] is True
    assert report["sections"]["exemplars"]["approval_path"] == str(approval)


def test_verifier_surfaces_exemplar_bank_fingerprint(monkeypatch, tmp_path: Path) -> None:
    tauri = _tauri_smoke(tmp_path / "learn-tauri-smoke-current.json")
    _python_quality(tmp_path / verifier.PYTHON_QUALITY_NAME)
    _frontend_quality(tmp_path / verifier.FRONTEND_QUALITY_NAME)
    _desktop_quality(tmp_path / verifier.DESKTOP_QUALITY_NAME)
    live = _live_artifact(tmp_path / "proof-current.json")
    monkeypatch.setattr(verifier, "audit_curriculum", lambda frontend_path=None: _curriculum_report())
    monkeypatch.setattr(
        verifier,
        "audit_packaged_bank",
        lambda *args, **kwargs: _exemplar_report(),
    )

    report = verifier.verify_package(
        proof_dir=tmp_path,
        tauri_smoke_path=tauri,
        live_proof_paths=[live],
    )

    fingerprint = report["sections"]["exemplars"]["bank_fingerprint"]
    matrix_fingerprint = {
        row["id"]: row["evidence"] for row in report["completion_matrix"]["requirements"]
    }["packaged_eq_exemplar_ear_pass"]["bank_fingerprint"]
    assert fingerprint["digest"] == "a" * 64
    assert matrix_fingerprint == fingerprint


def test_verifier_discovers_rekordbox_nudge_and_auto_master_artifacts(tmp_path: Path) -> None:
    nudge = tmp_path / "proof-course3-rekordbox-nudge-current.json"
    auto_master_current = tmp_path / "proof-course3-auto-master-current.json"
    auto_master_plan = tmp_path / "proof-course3-auto-master-plan-current.json"
    nudge.write_text("{}", encoding="utf-8")
    auto_master_current.write_text("{}", encoding="utf-8")
    auto_master_plan.write_text("{}", encoding="utf-8")

    paths = verifier._discover_live_proofs(tmp_path)

    assert paths[:3] == [nudge, auto_master_current, auto_master_plan]


def test_verifier_prefers_richer_course3_unavailable_attempt(
    monkeypatch,
    tmp_path: Path,
) -> None:
    tauri = _tauri_smoke(tmp_path / "learn-tauri-smoke-current.json")
    nudge = _live_artifact(
        tmp_path / "proof-course3-rekordbox-nudge-current.json",
        course3_diagnosis={
            "code": "rekordbox_route_self_test_inconclusive_external_playback_absent",
            "next_action": "start deck playback",
        },
        course3_route_plan={
            "candidate": {
                "name": "BlackHole 2ch",
                "sample_rate": 48000,
                "source": "rekordbox_audio_settings",
            },
            "fallback_device": "BlackHole 2ch",
            "selected_input": {
                "name": "BlackHole 2ch",
                "sample_rate": 48000,
                "live_signal": False,
                "reason": "preferred_fallback",
            },
        },
        playback_nudge={"ok": True, "action": "rekordbox_spacebar"},
    )
    auto_master_plan = _live_artifact(
        tmp_path / "proof-course3-auto-master-plan-current.json",
        course3_diagnosis={
            "code": "loopback_route_healthy_external_playback_absent",
            "next_action": "use the saved BlackHole 2ch route and start deck playback",
        },
        course3_route_plan={
            "candidate": {
                "name": "BlackHole 2ch",
                "sample_rate": 48000,
                "source": "rekordbox_audio_settings",
                "reason": "saved_loopback_route",
            },
            "fallback_device": "BlackHole 2ch",
            "selected_input": {
                "name": "BlackHole 2ch",
                "sample_rate": 48000,
                "live_signal": False,
                "reason": "preferred_fallback",
            },
        },
        auto_master_recommendation={
            "ok": True,
            "status": "ready",
            "source": "rekordbox_audio_settings",
            "reason": "saved_loopback_route",
            "device_name": "BlackHole 2ch",
            "sample_rate": 48000,
            "live_signal": False,
        },
    )
    auto_master_current = _live_artifact(
        tmp_path / "proof-course3-auto-master-current.json",
        course3_diagnosis={
            "code": "loopback_route_healthy_external_playback_absent",
            "next_action": (
                "current app-start proof selected BlackHole 2ch; start deck playback. "
                "Current macOS now-playing is not a citable Rekordbox deck title; "
                "stop unrelated media or make Rekordbox the active playing source."
            ),
            "nowplaying_hint": (
                "macOS now-playing is 'The Diary Of A CEO - Chase Hughes' "
                "from com.apple.WebKit.GPU (not playing), not Rekordbox; "
                "deck_state needs a Rekordbox-published title that matches the "
                "imported library"
            ),
            "nowplaying": {
                "available": True,
                "ok": True,
                "full_title": "The Diary Of A CEO - Chase Hughes",
                "bundle_identifier": "com.apple.WebKit.GPU",
                "playback_rate": 0,
                "is_playing": False,
                "looks_like_rekordbox": False,
            },
            "operator_action": {
                "prompt": (
                    "Play a real Rekordbox library track through BlackHole 2ch "
                    "@ 48000Hz with channel and master faders up."
                ),
                "route": "BlackHole 2ch @ 48000Hz",
                "nowplaying_blocker": (
                    "macOS now-playing is 'The Diary Of A CEO - Chase Hughes' "
                    "from com.apple.WebKit.GPU (not playing), not Rekordbox; "
                    "deck_state needs a Rekordbox-published title that matches the "
                    "imported library"
                ),
                "steps": [
                    "Stop unrelated media or make Rekordbox the active playing source.",
                    (
                        "In Rekordbox, load and play a real library track through "
                        "BlackHole 2ch @ 48000Hz."
                    ),
                    (
                        "Raise the playing channel fader and master until the "
                        "loopback capture has signal."
                    ),
                    "Rerun the Course 3 live proof with --require-count-in.",
                ],
            },
        },
        course3_route_plan={
            "candidate": {
                "name": "BlackHole 2ch",
                "sample_rate": 48000,
                "source": "rekordbox_audio_settings",
                "reason": "saved_loopback_route",
            },
            "fallback_device": "BlackHole 2ch",
            "selected_input": {
                "name": "BlackHole 2ch",
                "sample_rate": 48000,
                "live_signal": False,
                "reason": "preferred_fallback",
            },
        },
        auto_master_recommendation={
            "ok": True,
            "status": "ready",
            "source": "rekordbox_audio_settings",
            "reason": "saved_loopback_route",
            "device_name": "BlackHole 2ch",
            "sample_rate": 48000,
            "live_signal": False,
        },
        playback_nudge={"ok": True, "action": "rekordbox_spacebar"},
    )
    monkeypatch.setattr(verifier, "audit_curriculum", lambda frontend_path=None: _curriculum_report())
    monkeypatch.setattr(
        verifier,
        "audit_packaged_bank",
        lambda *args, **kwargs: _exemplar_report(),
    )

    report = verifier.verify_package(
        proof_dir=tmp_path,
        tauri_smoke_path=tauri,
        live_proof_paths=[nudge, auto_master_current, auto_master_plan],
    )

    course3 = report["sections"]["live_proofs"]["course3"]
    assert course3["status"] == "unavailable"
    assert course3["path"] == str(auto_master_current)
    assert course3["auto_master_recommendation"]["reason"] == "saved_loopback_route"
    assert (
        course3["route_plan"]["auto_master_fallback_candidate"]["reason"]
        == "saved_loopback_route"
    )
    assert course3["playback_nudge"]["action"] == "rekordbox_spacebar"
    assert course3["operator_commands"]["manual_action"] == (
        "current app-start proof selected BlackHole 2ch; start deck playback. "
        "Current macOS now-playing is not a citable Rekordbox deck title; "
        "stop unrelated media or make Rekordbox the active playing source."
    )
    assert course3["diagnosis"]["nowplaying_hint"] == (
        "macOS now-playing is 'The Diary Of A CEO - Chase Hughes' "
        "from com.apple.WebKit.GPU (not playing), not Rekordbox; "
        "deck_state needs a Rekordbox-published title that matches the "
        "imported library"
    )
    assert course3["operator_commands"]["operator_action"]["route"] == (
        "BlackHole 2ch @ 48000Hz"
    )
    assert course3["operator_commands"]["operator_action"]["steps"][0] == (
        "Stop unrelated media or make Rekordbox the active playing source."
    )
    assert course3["operator_commands"]["current_selected_input"] == {
        "name": "BlackHole 2ch",
        "sample_rate": 48000,
        "reason": "preferred_fallback",
        "live_signal": False,
    }
    assert course3["operator_commands"]["current_fallback_candidate"] == {
        "name": "BlackHole 2ch",
        "sample_rate": 48000,
        "reason": "saved_loopback_route",
        "source": "rekordbox_audio_settings",
        "live_signal": None,
    }
    assert "--nudge-rekordbox-playback" in course3["operator_commands"]["proof"]
    assert "--say-course3-prompts" in course3["operator_commands"]["proof"]


def test_verifier_surfaces_course3_audio_diagnosis(monkeypatch, tmp_path: Path) -> None:
    diagnosis = {
        "code": "loopback_route_healthy_external_playback_absent",
        "severity": "start_playback",
        "next_action": "set Rekordbox Audio preferences to BlackHole",
    }
    tauri = _tauri_smoke(tmp_path / "learn-tauri-smoke-current.json")
    live = _live_artifact(tmp_path / "proof-current.json", course3_diagnosis=diagnosis)
    monkeypatch.setattr(verifier, "audit_curriculum", lambda frontend_path=None: _curriculum_report())
    monkeypatch.setattr(
        verifier,
        "audit_packaged_bank",
        lambda *args, **kwargs: _exemplar_report(),
    )

    report = verifier.verify_package(
        proof_dir=tmp_path,
        tauri_smoke_path=tauri,
        live_proof_paths=[live],
    )

    course3 = report["sections"]["live_proofs"]["course3"]
    assert course3["status"] == "unavailable"
    assert course3["diagnosis"] == diagnosis
    assert course3["attempts"][0]["diagnosis"] == diagnosis
    assert (
        course3["operator_commands"]["manual_action"]
        == "set Rekordbox Audio preferences to BlackHole"
    )
    assert "set Rekordbox Audio preferences to BlackHole" in report["next_actions"]


def test_verifier_surfaces_physical_probe_diagnosis(monkeypatch, tmp_path: Path) -> None:
    diagnosis = {
        "code": "left_jog_not_observed",
        "message": "L1.07 loaded, but no ipc.learn.midi_position frame reached jog:A.",
        "operator_action": {
            "prompt": "Nudge the left jog wheel during the active proof window.",
            "steps": [
                "When the proof prints the connected prompt, rotate the left jog wheel.",
                "Keep the DDJ-FLX4 connected directly over USB.",
            ],
        },
    }
    tauri = _tauri_smoke(tmp_path / "learn-tauri-smoke-current.json")
    live = _live_artifact(tmp_path / "proof-current.json", physical_diagnosis=diagnosis)
    monkeypatch.setattr(verifier, "audit_curriculum", lambda frontend_path=None: _curriculum_report())
    monkeypatch.setattr(
        verifier,
        "audit_packaged_bank",
        lambda *args, **kwargs: _exemplar_report(),
    )

    report = verifier.verify_package(
        proof_dir=tmp_path,
        tauri_smoke_path=tauri,
        live_proof_paths=[live],
    )

    physical = report["sections"]["live_proofs"]["physical"]
    assert physical["status"] == "unavailable"
    assert physical["diagnosis"] == diagnosis
    assert physical["attempts"][0]["diagnosis"] == diagnosis
    assert physical["operator_commands"]["manual_action"] == (
        "Nudge the left jog wheel during the active proof window."
    )
    assert "sniff_controller.py --list" in physical["operator_commands"]["list_controller"]
    assert "--wait-physical-seconds 30" in physical["operator_commands"]["proof"]
    assert "--say-physical-prompts" in physical["operator_commands"]["proof"]
    assert "Nudge the left jog wheel during the active proof window." in report[
        "next_actions"
    ]


def test_verifier_surfaces_physical_connection_doctor(
    monkeypatch,
    tmp_path: Path,
) -> None:
    doctor = {
        "ok": False,
        "status": "missing_midi",
        "next_step": (
            "Use a data-capable USB cable or powered adapter, then wait for DDJ-FLX4 in MIDI."
        ),
        "operator_steps": [
            "Use a data-capable USB cable or powered adapter, then wait for DDJ-FLX4 in MIDI.",
            "Confirm macOS sees DDJ-FLX4 in USB or audio devices before starting the proof.",
        ],
        "readiness_command": (
            "uv run python scripts/learn_live_readiness.py --require physical "
            "--out /tmp/vibemix-live-learn-proof/learn-physical-readiness-current.json"
        ),
        "proof_command": (
            "uv run python scripts/run_learn_live_proof.py --start-app --no-screen "
            "--physical --wait-physical-seconds 30 --physical-seconds 40 "
            "--say-physical-prompts --auto-master-input "
            "--out /tmp/vibemix-live-learn-proof/proof-physical-ddj-current.json"
        ),
        "uses_spoken_prompt": True,
    }
    tauri = _tauri_smoke(tmp_path / "learn-tauri-smoke-current.json")
    live = _live_artifact(tmp_path / "proof-current.json")
    artifact = json.loads(live.read_text(encoding="utf-8"))
    artifact["stages"]["physical_readiness_wait"] = {
        "status": "failed",
        "result": {"last": {"physical_connection_doctor": doctor}},
    }
    live.write_text(json.dumps(artifact), encoding="utf-8")
    monkeypatch.setattr(verifier, "audit_curriculum", lambda frontend_path=None: _curriculum_report())
    monkeypatch.setattr(
        verifier,
        "audit_packaged_bank",
        lambda *args, **kwargs: _exemplar_report(),
    )

    report = verifier.verify_package(
        proof_dir=tmp_path,
        tauri_smoke_path=tauri,
        live_proof_paths=[live],
    )

    physical = report["sections"]["live_proofs"]["physical"]
    assert physical["status"] == "unavailable"
    assert physical["physical_connection_doctor"] == doctor
    assert physical["attempts"][0]["physical_connection_doctor"] == doctor
    assert physical["operator_commands"]["manual_action"] == doctor["next_step"]
    assert physical["operator_commands"]["operator_action"]["steps"] == doctor[
        "operator_steps"
    ]
    assert physical["operator_commands"]["physical_connection_doctor"] == doctor
    assert doctor["next_step"] in report["next_actions"]

    recipe = {row["id"]: row for row in report["release_blocker_recipe"]}
    physical_recipe = recipe["physical_controller_path"]
    assert physical_recipe["operator_steps"] == doctor["operator_steps"]
    assert physical_recipe["physical_connection_doctor"] == doctor

    matrix = {
        row["id"]: row["evidence"]
        for row in report["completion_matrix"]["requirements"]
    }
    assert matrix["physical_controller_path"]["physical_connection_doctor"] == doctor


def test_verifier_surfaces_course3_route_plan(monkeypatch, tmp_path: Path) -> None:
    diagnosis = {
        "code": "loopback_route_healthy_external_playback_absent",
        "severity": "start_playback",
        "next_action": "align Rekordbox with the vibemix capture input",
    }
    route_plan = {
        "candidate": {
            "name": "BlackHole 2ch",
            "sample_rate": 44100,
            "source": "rekordbox_audio_settings",
        },
        "fallback_device": None,
        "rejected_reason": "BlackHole 2ch is 44100Hz; vibemix capture expects 48000Hz",
        "selected_input": {
            "name": "BlackHole 16ch",
            "sample_rate": 48000,
            "live_signal": False,
            "reason": "48k_fallback",
        },
    }
    tauri = _tauri_smoke(tmp_path / "learn-tauri-smoke-current.json")
    live = _live_artifact(
        tmp_path / "proof-current.json",
        course3_diagnosis=diagnosis,
        course3_route_plan=route_plan,
    )
    monkeypatch.setattr(verifier, "audit_curriculum", lambda frontend_path=None: _curriculum_report())
    monkeypatch.setattr(
        verifier,
        "audit_packaged_bank",
        lambda *args, **kwargs: _exemplar_report(),
    )

    report = verifier.verify_package(
        proof_dir=tmp_path,
        tauri_smoke_path=tauri,
        live_proof_paths=[live],
    )

    course3 = report["sections"]["live_proofs"]["course3"]
    assert course3["route_plan"]["auto_master_fallback_candidate"]["name"] == "BlackHole 2ch"
    assert course3["route_plan"]["selected_input"]["name"] == "BlackHole 16ch"
    assert course3["attempts"][0]["route_plan"]["selected_input"]["reason"] == "48k_fallback"
    assert course3["operator_commands"]["current_selected_input"]["name"] == "BlackHole 16ch"
    assert course3["operator_commands"]["current_fallback_candidate"]["name"] == "BlackHole 2ch"
    assert course3["operator_commands"]["operator_action"]["route"] == (
        "BlackHole 16ch @ 48000Hz"
    )
    assert course3["operator_commands"]["operator_action"]["steps"][1] == (
        "Route Rekordbox master/output audio to BlackHole 16ch @ 48000Hz."
    )
    assert any(
        "BlackHole 2ch is 44100Hz" in action
        for action in report["next_actions"]
    )
    assert "align Rekordbox with the vibemix capture input" in report["next_actions"]


def test_verifier_surfaces_course3_playback_nudge(monkeypatch, tmp_path: Path) -> None:
    diagnosis = {
        "code": "loopback_route_healthy_external_playback_absent",
        "severity": "start_playback",
        "next_action": "start real deck playback",
    }
    tauri = _tauri_smoke(tmp_path / "learn-tauri-smoke-current.json")
    live = _live_artifact(
        tmp_path / "proof-current.json",
        course3_diagnosis=diagnosis,
        playback_nudge={
            "ok": True,
            "action": "rekordbox_spacebar",
            "returncode": 0,
            "precheck": {"ok": False, "loopback_ok": False},
        },
    )
    monkeypatch.setattr(verifier, "audit_curriculum", lambda frontend_path=None: _curriculum_report())
    monkeypatch.setattr(
        verifier,
        "audit_packaged_bank",
        lambda *args, **kwargs: _exemplar_report(),
    )

    report = verifier.verify_package(
        proof_dir=tmp_path,
        tauri_smoke_path=tauri,
        live_proof_paths=[live],
    )

    course3 = report["sections"]["live_proofs"]["course3"]
    assert course3["playback_nudge"] == {
        "status": "passed",
        "ok": True,
        "action": "rekordbox_spacebar",
        "returncode": 0,
        "precheck": {"ok": False, "loopback_ok": False},
    }
    assert course3["attempts"][0]["playback_nudge"]["action"] == "rekordbox_spacebar"
    assert course3["attempts"][0]["playback_nudge"]["precheck"]["ok"] is False


def test_verifier_cli_writes_json_and_keeps_release_gate_separate(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    tauri = _tauri_smoke(tmp_path / "learn-tauri-smoke-current.json")
    _python_quality(tmp_path / verifier.PYTHON_QUALITY_NAME)
    _frontend_quality(tmp_path / verifier.FRONTEND_QUALITY_NAME)
    _desktop_quality(tmp_path / verifier.DESKTOP_QUALITY_NAME)
    live = _live_artifact(tmp_path / "proof-current.json")
    out_path = tmp_path / "learn-package-verification.json"

    proc = subprocess.run(
        [
            sys.executable,
            "scripts/verify_learn_package.py",
            "--proof-dir",
            str(tmp_path),
            "--tauri-smoke",
            str(tauri),
            "--live-proof",
            str(live),
            "--out",
            str(out_path),
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert proc.returncode == 0
    stdout_report = json.loads(proc.stdout)
    file_report = json.loads(out_path.read_text(encoding="utf-8"))
    assert stdout_report["passed"] is True
    assert file_report["release_ready"] is False
    assert "packaged EQ exemplar human ear-pass is pending" in file_report[
        "completion_blockers"
    ]

    strict = subprocess.run(
        [
            sys.executable,
            "scripts/verify_learn_package.py",
            "--proof-dir",
            str(tmp_path),
            "--tauri-smoke",
            str(tauri),
            "--live-proof",
            str(live),
            "--require-release-ready",
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert strict.returncode == 4
    strict_report = json.loads(strict.stdout)
    assert strict_report["passed"] is True
    assert strict_report["release_ready"] is False
