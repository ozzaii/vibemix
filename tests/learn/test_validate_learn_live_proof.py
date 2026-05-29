# SPDX-License-Identifier: Apache-2.0
"""Contracts for Learn live-proof artifact validation."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts import validate_learn_live_proof as validator


def _artifact() -> dict:
    return {
        "schema_version": 1,
        "passed": False,
        "stages": {
            "app_start": {"status": "passed"},
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
            "physical_probe": {
                "status": "skipped",
                "reason": "physical readiness failed",
                "result": {"blockers": ["physical controller is not visible as a MIDI input"]},
            },
            "course3_probe": {
                "status": "skipped",
                "reason": "course3 readiness failed",
                "result": {"blockers": ["physical controller is not visible on USB"]},
            },
            "app_stop": {"status": "passed"},
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
        },
    }


def _passed_physical_stage() -> dict:
    return {
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


def _passed_course3_stage() -> dict:
    return {
        "status": "passed",
        "result": {
            "passed": True,
            "lens_frames": 2,
            "active_seen": True,
            "count_in_seen": True,
            "last_lens": {
                "session_active": True,
                "phrase_position_confidence": 0.9,
                "next_phrase_at": 32.0,
                "next_phrase_cue_id": "cue:A:break",
            },
        },
    }


def test_screen_validation_passes_for_real_screen_shape() -> None:
    verdict = validator.validate_artifact(
        _artifact(),
        required={"screen"},
        allow_skipped=set(),
    )

    assert verdict["valid"] is True
    assert verdict["errors"] == []


def test_validation_rejects_failed_app_start_even_without_required_probe() -> None:
    artifact = _artifact()
    artifact["stages"]["app_start"] = {
        "status": "failed",
        "result": {"socket": {"ok": False}},
    }
    artifact["stages"]["app_stop"] = {"status": "skipped"}

    verdict = validator.validate_artifact(
        artifact,
        required=set(),
        allow_skipped=set(),
    )

    assert verdict["valid"] is False
    assert "app_start stage failed" in verdict["errors"]


def test_validation_rejects_missing_stop_after_successful_app_start() -> None:
    artifact = _artifact()
    artifact["stages"]["app_start"] = {"status": "passed"}
    artifact["stages"]["app_stop"] = {"status": "skipped"}

    verdict = validator.validate_artifact(
        artifact,
        required=set(),
        allow_skipped=set(),
    )

    assert verdict["valid"] is False
    assert "app was started but app_stop did not pass" in verdict["errors"]


def test_physical_validation_fails_without_explicit_skip_allowance() -> None:
    verdict = validator.validate_artifact(
        _artifact(),
        required={"screen", "physical"},
        allow_skipped=set(),
    )

    assert verdict["valid"] is False
    assert verdict["errors"] == [
        "physical_probe skipped: physical readiness failed",
        "physical readiness: physical controller is not visible as a MIDI input",
    ]


def test_physical_and_course3_skips_can_be_accepted_as_unavailable() -> None:
    verdict = validator.validate_artifact(
        _artifact(),
        required={"screen", "physical", "course3"},
        allow_skipped={"physical", "course3"},
    )

    assert verdict["valid"] is True
    assert verdict["errors"] == []


def test_physical_validation_requires_jog_ack_and_advance() -> None:
    artifact = _artifact()
    artifact["stages"]["physical_probe"] = _passed_physical_stage()

    verdict = validator.validate_artifact(
        artifact,
        required={"physical"},
        allow_skipped=set(),
    )

    assert verdict["valid"] is True

    artifact["stages"]["physical_probe"]["result"]["advance_seen"] = False
    verdict = validator.validate_artifact(
        artifact,
        required={"physical"},
        allow_skipped=set(),
    )
    assert verdict["valid"] is False
    assert "physical proof did not see advance" in verdict["errors"]


def test_course3_validation_requires_count_in_and_citable_cue() -> None:
    artifact = _artifact()
    artifact["stages"]["course3_probe"] = _passed_course3_stage()

    verdict = validator.validate_artifact(
        artifact,
        required={"course3"},
        allow_skipped=set(),
    )

    assert verdict["valid"] is True

    artifact["stages"]["course3_probe"]["result"]["count_in_seen"] = False
    verdict = validator.validate_artifact(
        artifact,
        required={"course3"},
        allow_skipped=set(),
    )
    assert verdict["valid"] is False
    assert "course3 proof did not see count-in evidence" in verdict["errors"]


def test_course3_validation_rejects_weak_lens_only_probe() -> None:
    artifact = _artifact()
    artifact["stages"]["course3_probe"] = {
        "status": "passed",
        "result": {
            "passed": True,
            "lens_frames": 1,
            "active_seen": False,
            "count_in_seen": False,
            "last_lens": {"session_active": False},
        },
    }

    verdict = validator.validate_artifact(
        artifact,
        required={"course3"},
        allow_skipped=set(),
    )

    assert verdict["valid"] is False
    assert "course3 proof did not see active Course 3" in verdict["errors"]
    assert "course3 proof did not see count-in evidence" in verdict["errors"]


def test_course3_validation_surfaces_probe_diagnostics() -> None:
    artifact = _artifact()
    artifact["stages"]["course3_probe"] = {
        "status": "failed",
        "result": {
            "passed": False,
            "lens_frames": 1,
            "active_seen": False,
            "count_in_seen": False,
            "last_lens": {"session_active": False},
            "diagnostics": {
                "blockers": [
                    "audible deck stayed none",
                    "deck_state stayed empty",
                ],
                "operator_action": {
                    "prompt": "Open one channel.",
                    "steps": [
                        "Open one deck channel so the coach can attribute deck A or B."
                    ],
                },
            },
        },
    }

    verdict = validator.validate_artifact(
        artifact,
        required={"course3"},
        allow_skipped=set(),
    )

    assert "course3 diagnostic: audible deck stayed none" in verdict["errors"]
    assert "course3 diagnostic: deck_state stayed empty" in verdict["errors"]
    assert "course3 operator action: Open one channel." in verdict["errors"]


def test_course3_validation_surfaces_readiness_context_blockers() -> None:
    artifact = _artifact()
    artifact["stages"]["course3_probe"] = {
        "status": "skipped",
        "reason": "course3 readiness failed",
        "result": {
            "blockers": ["live audio is not attributed to deck A, B, or mix"],
            "checks": {
                "course3_live_context": {
                    "ok": False,
                    "blockers": [
                        "live deck_state has no citable track_id at confidence floor"
                    ],
                }
            },
        },
    }

    verdict = validator.validate_artifact(
        artifact,
        required={"course3"},
        allow_skipped=set(),
    )

    assert verdict["valid"] is False
    assert "course3_probe skipped: course3 readiness failed" in verdict["errors"]
    assert (
        "course3 readiness: live audio is not attributed to deck A, B, or mix"
        in verdict["errors"]
    )
    assert (
        "course3 readiness: live deck_state has no citable track_id at confidence floor"
        in verdict["errors"]
    )


def test_course3_allow_skipped_accepts_nested_wait_blockers() -> None:
    artifact = _artifact()
    artifact["stages"]["course3_probe"] = {
        "status": "skipped",
        "reason": "course3 readiness failed",
        "result": {
            "last": {
                "blockers": [],
                "checks": {
                    "course3_live_context": {
                        "ok": False,
                        "blockers": ["live master audio is not audible yet"],
                    }
                },
            }
        },
    }

    verdict = validator.validate_artifact(
        artifact,
        required={"course3"},
        allow_skipped={"course3"},
    )

    assert verdict["valid"] is True
    assert verdict["errors"] == []


def test_screen_validation_rejects_stale_progress_only_artifact() -> None:
    artifact = _artifact()
    artifact["stages"]["screen_probe"] = {"status": "skipped", "reason": "--no-screen set"}

    verdict = validator.validate_artifact(
        artifact,
        required={"screen"},
        allow_skipped=set(),
    )

    assert verdict["valid"] is False
    assert "screen_probe did not pass" in verdict["errors"]


def test_cli_validates_artifact_file(tmp_path: Path) -> None:
    artifact_path = tmp_path / "proof.json"
    artifact_path.write_text(json.dumps(_artifact()), encoding="utf-8")
    repo_root = Path(__file__).resolve().parents[2]

    proc = subprocess.run(
        [
            sys.executable,
            "scripts/validate_learn_live_proof.py",
            str(artifact_path),
            "--require",
            "screen",
            "--require",
            "physical",
            "--allow-skipped",
            "physical",
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    assert proc.returncode == 0
    assert json.loads(proc.stdout)["valid"] is True


def test_cli_fails_when_required_physical_is_only_skipped(tmp_path: Path) -> None:
    artifact_path = tmp_path / "proof.json"
    artifact_path.write_text(json.dumps(_artifact()), encoding="utf-8")
    repo_root = Path(__file__).resolve().parents[2]

    proc = subprocess.run(
        [
            sys.executable,
            "scripts/validate_learn_live_proof.py",
            str(artifact_path),
            "--require",
            "physical",
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    assert proc.returncode == 4
    assert "physical_probe skipped" in proc.stdout
