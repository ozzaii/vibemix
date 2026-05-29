#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Verify the Learn package evidence without overclaiming live proof.

This script is the single "what is proven right now?" surface for the rebuilt
beginner module. It separates deterministic package integrity from release
readiness so a green curriculum audit can coexist with honest blockers such as
human ear-pass or missing Course 3 routed-audio proof.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.audition_learn_exemplars import (  # noqa: E402
    audit_packaged_bank,
    ear_pass_operator_action,
    list_output_devices,
)
from scripts.validate_learn_live_proof import (  # noqa: E402
    Requirement,
    load_artifact,
    validate_artifact,
)
from vibemix.learn.curriculum_audit import audit_curriculum  # noqa: E402

DEFAULT_PROOF_DIR = Path("/tmp/vibemix-live-learn-proof")
DEFAULT_FRONTEND = (
    _REPO_ROOT / "tauri" / "ui" / "src" / "learn" / "lesson" / "curriculum-meta.ts"
)
TAURI_SMOKE_CANDIDATES = (
    "learn-tauri-smoke-after-audio-wait.json",
    "learn-tauri-smoke-current.json",
)
FRONTEND_QUALITY_NAME = "learn-frontend-quality-current.json"
FRONTEND_QUALITY_COMMANDS = {
    "learn_app_entry_vitest",
    "learn_frontstage_simplicity_vitest",
    "learn_tauri_window_vitest",
    "learn_choice_replay_vitest",
    "learn_vitest",
    "learn_build",
    "learn_browser_booth_playwright",
    "learn_e2e",
}
PYTHON_QUALITY_NAME = "learn-python-quality-current.json"
PYTHON_QUALITY_COMMANDS = {
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
}
DESKTOP_QUALITY_NAME = "learn-desktop-quality-current.json"
DESKTOP_QUALITY_COMMANDS = {
    "learn_tauri_frontend_dist_build",
    "learn_cargo_fmt",
    "learn_cargo_check",
    "learn_cargo_learn_window_test",
    "learn_cargo_sidecar_audio_test",
}
LIVE_PROOF_GLOBS = (
    "proof-screen-runner.json",
    "proof-physical-ddj-current.json",
    "proof-course3-rekordbox-nudge-current.json",
    "proof-course3-auto-master-current.json",
    "proof-course3-auto-master-plan-current.json",
    "proof-course3-route-settings-runner-current.json",
    "proof-course3-route-hint-runner-current.json",
    "proof-combined-current.json",
)
LIVE_REQUIREMENTS: tuple[Requirement, ...] = ("screen", "physical", "course3")
EXEMPLAR_APPROVAL_NAME = "learn-exemplar-ear-pass-current.json"
PHYSICAL_READINESS_NAME = "learn-physical-readiness-current.json"
COURSE3_READINESS_NAME = "learn-course3-readiness-current.json"
DEFERRED_EXTERNAL_RELEASE_BLOCKER_IDS = frozenset(
    {
        "course3_live_audio_play_mode",
        "packaged_eq_exemplar_ear_pass",
    }
)


def _read_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None, "missing"
    except (OSError, json.JSONDecodeError) as exc:
        return None, repr(exc)
    if not isinstance(raw, dict):
        return None, "artifact root is not an object"
    return raw, None


def _discover_tauri_smoke(proof_dir: Path) -> Path | None:
    for name in TAURI_SMOKE_CANDIDATES:
        path = proof_dir / name
        if path.exists():
            return path
    return None


def _discover_live_proofs(proof_dir: Path) -> list[Path]:
    paths: list[Path] = []
    seen: set[Path] = set()
    for name in LIVE_PROOF_GLOBS:
        path = proof_dir / name
        if path.exists() and path not in seen:
            paths.append(path)
            seen.add(path)
    return paths


def _discover_exemplar_approval(proof_dir: Path) -> Path | None:
    path = proof_dir / EXEMPLAR_APPROVAL_NAME
    return path if path.exists() else None


def _discover_frontend_quality(proof_dir: Path) -> Path | None:
    path = proof_dir / FRONTEND_QUALITY_NAME
    return path if path.exists() else None


def _discover_python_quality(proof_dir: Path) -> Path | None:
    path = proof_dir / PYTHON_QUALITY_NAME
    return path if path.exists() else None


def _discover_desktop_quality(proof_dir: Path) -> Path | None:
    path = proof_dir / DESKTOP_QUALITY_NAME
    return path if path.exists() else None


def _discover_course3_readiness(proof_dir: Path) -> Path | None:
    path = proof_dir / COURSE3_READINESS_NAME
    return path if path.exists() else None


def _discover_physical_readiness(proof_dir: Path) -> Path | None:
    path = proof_dir / PHYSICAL_READINESS_NAME
    return path if path.exists() else None


def _enrich_exemplar_operator_action(exemplars: dict[str, Any]) -> dict[str, Any]:
    """Attach current output-device guidance without making verification depend on it."""
    if exemplars.get("release_ready") is True:
        return exemplars
    enriched = dict(exemplars)
    try:
        devices = list_output_devices()
    except Exception as exc:
        enriched.setdefault("operator_action", ear_pass_operator_action([]))
        enriched["output_devices"] = []
        enriched["output_device_error"] = repr(exc)
        return enriched
    enriched["output_devices"] = devices
    enriched["operator_action"] = ear_pass_operator_action(devices)
    return enriched


def _tauri_smoke_status(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {
            "status": "missing",
            "path": None,
            "passed": False,
            "errors": ["launched Tauri Learn smoke artifact is missing"],
        }
    artifact, error = _read_json(path)
    if artifact is None:
        return {
            "status": "failed",
            "path": str(path),
            "passed": False,
            "errors": [str(error)],
        }
    errors: list[str] = []
    if artifact.get("passed") is not True:
        errors.append("passed is not true")
    if artifact.get("l101_completed") is not True:
        errors.append("L1.01 completion was not proven")
    if artifact.get("quality_ok") is not True:
        errors.append("quality_ok is not true")
    if int(artifact.get("quality_check_count") or 0) < 15:
        errors.append("quality_check_count is below the Learn quality floor")
    failures = artifact.get("failures")
    if isinstance(failures, list) and failures:
        errors.append("quality failures are present")
    return {
        "status": "passed" if not errors else "failed",
        "path": str(path),
        "passed": not errors,
        "completed_lesson_id": artifact.get("completed_lesson_id"),
        "l101_completed": artifact.get("l101_completed"),
        "quality_ok": artifact.get("quality_ok"),
        "quality_check_count": artifact.get("quality_check_count"),
        "errors": errors,
    }


def _frontend_quality_status(path: Path | None) -> dict[str, Any]:
    operator_commands = {
        "run": (
            "uv run python scripts/run_learn_frontend_quality.py "
            "--out /tmp/vibemix-live-learn-proof/learn-frontend-quality-current.json"
        ),
        "verify": (
            "uv run python scripts/verify_learn_package.py "
            "--out /tmp/vibemix-live-learn-proof/learn-package-verification-current.json"
        ),
    }
    if path is None:
        return {
            "status": "missing",
            "path": None,
            "passed": False,
            "required_commands": sorted(FRONTEND_QUALITY_COMMANDS),
            "operator_commands": operator_commands,
            "errors": ["full Learn frontend quality artifact is missing"],
        }
    artifact, error = _read_json(path)
    if artifact is None:
        return {
            "status": "failed",
            "path": str(path),
            "passed": False,
            "required_commands": sorted(FRONTEND_QUALITY_COMMANDS),
            "operator_commands": operator_commands,
            "errors": [str(error)],
        }

    commands = artifact.get("commands")
    rows = commands if isinstance(commands, list) else []
    seen_names = {
        str(row.get("name"))
        for row in rows
        if isinstance(row, dict) and row.get("name") is not None
    }
    errors: list[str] = []
    missing = sorted(FRONTEND_QUALITY_COMMANDS - seen_names)
    if missing:
        errors.append(f"missing frontend quality command rows: {', '.join(missing)}")
    failed = [
        str(row.get("name"))
        for row in rows
        if isinstance(row, dict)
        and row.get("name") in FRONTEND_QUALITY_COMMANDS
        and row.get("passed") is not True
    ]
    if failed:
        errors.append(f"frontend quality command rows failed: {', '.join(failed)}")
    if artifact.get("passed") is not True:
        errors.append("passed is not true")
    return {
        "status": "passed" if not errors else "failed",
        "path": str(path),
        "passed": not errors,
        "required_commands": sorted(FRONTEND_QUALITY_COMMANDS),
        "operator_commands": operator_commands,
        "generated_at": artifact.get("generated_at"),
        "commands": [
            {
                "name": row.get("name"),
                "command": row.get("command"),
                "returncode": row.get("returncode"),
                "duration_s": row.get("duration_s"),
                "passed": row.get("passed") is True,
            }
            for row in rows
            if isinstance(row, dict)
        ],
        "errors": errors,
    }


def _python_quality_status(path: Path | None) -> dict[str, Any]:
    operator_commands = {
        "run": (
            "uv run python scripts/run_learn_python_quality.py "
            "--out /tmp/vibemix-live-learn-proof/learn-python-quality-current.json"
        ),
        "verify": (
            "uv run python scripts/verify_learn_package.py "
            "--out /tmp/vibemix-live-learn-proof/learn-package-verification-current.json"
        ),
    }
    if path is None:
        return {
            "status": "missing",
            "path": None,
            "passed": False,
            "required_commands": sorted(PYTHON_QUALITY_COMMANDS),
            "operator_commands": operator_commands,
            "errors": ["full Learn Python quality artifact is missing"],
        }
    artifact, error = _read_json(path)
    if artifact is None:
        return {
            "status": "failed",
            "path": str(path),
            "passed": False,
            "required_commands": sorted(PYTHON_QUALITY_COMMANDS),
            "operator_commands": operator_commands,
            "errors": [str(error)],
        }

    commands = artifact.get("commands")
    rows = commands if isinstance(commands, list) else []
    seen_names = {
        str(row.get("name"))
        for row in rows
        if isinstance(row, dict) and row.get("name") is not None
    }
    errors: list[str] = []
    missing = sorted(PYTHON_QUALITY_COMMANDS - seen_names)
    if missing:
        errors.append(f"missing Python quality command rows: {', '.join(missing)}")
    failed = [
        str(row.get("name"))
        for row in rows
        if isinstance(row, dict)
        and row.get("name") in PYTHON_QUALITY_COMMANDS
        and row.get("passed") is not True
    ]
    if failed:
        errors.append(f"Python quality command rows failed: {', '.join(failed)}")
    if artifact.get("passed") is not True:
        errors.append("passed is not true")
    return {
        "status": "passed" if not errors else "failed",
        "path": str(path),
        "passed": not errors,
        "required_commands": sorted(PYTHON_QUALITY_COMMANDS),
        "operator_commands": operator_commands,
        "generated_at": artifact.get("generated_at"),
        "commands": [
            {
                "name": row.get("name"),
                "command": row.get("command"),
                "returncode": row.get("returncode"),
                "duration_s": row.get("duration_s"),
                "passed": row.get("passed") is True,
            }
            for row in rows
            if isinstance(row, dict)
        ],
        "errors": errors,
    }


def _desktop_quality_status(path: Path | None) -> dict[str, Any]:
    operator_commands = {
        "run": (
            "uv run python scripts/run_learn_desktop_quality.py "
            "--out /tmp/vibemix-live-learn-proof/learn-desktop-quality-current.json"
        ),
        "verify": (
            "uv run python scripts/verify_learn_package.py "
            "--out /tmp/vibemix-live-learn-proof/learn-package-verification-current.json"
        ),
    }
    if path is None:
        return {
            "status": "missing",
            "path": None,
            "passed": False,
            "required_commands": sorted(DESKTOP_QUALITY_COMMANDS),
            "operator_commands": operator_commands,
            "errors": ["Learn desktop-shell quality artifact is missing"],
        }
    artifact, error = _read_json(path)
    if artifact is None:
        return {
            "status": "failed",
            "path": str(path),
            "passed": False,
            "required_commands": sorted(DESKTOP_QUALITY_COMMANDS),
            "operator_commands": operator_commands,
            "errors": [str(error)],
        }

    commands = artifact.get("commands")
    rows = commands if isinstance(commands, list) else []
    seen_names = {
        str(row.get("name"))
        for row in rows
        if isinstance(row, dict) and row.get("name") is not None
    }
    errors: list[str] = []
    missing = sorted(DESKTOP_QUALITY_COMMANDS - seen_names)
    if missing:
        errors.append(f"missing desktop quality command rows: {', '.join(missing)}")
    failed = [
        str(row.get("name"))
        for row in rows
        if isinstance(row, dict)
        and row.get("name") in DESKTOP_QUALITY_COMMANDS
        and row.get("passed") is not True
    ]
    if failed:
        errors.append(f"desktop quality command rows failed: {', '.join(failed)}")
    if artifact.get("passed") is not True:
        errors.append("passed is not true")
    return {
        "status": "passed" if not errors else "failed",
        "path": str(path),
        "passed": not errors,
        "required_commands": sorted(DESKTOP_QUALITY_COMMANDS),
        "operator_commands": operator_commands,
        "generated_at": artifact.get("generated_at"),
        "commands": [
            {
                "name": row.get("name"),
                "command": row.get("command"),
                "returncode": row.get("returncode"),
                "duration_s": row.get("duration_s"),
                "passed": row.get("passed") is True,
            }
            for row in rows
            if isinstance(row, dict)
        ],
        "errors": errors,
    }


def _course3_readiness_status(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    artifact, error = _read_json(path)
    if artifact is None:
        return {
            "status": "failed",
            "path": str(path),
            "passed": False,
            "blockers": [str(error)],
            "errors": [str(error)],
        }

    blockers = [
        str(blocker)
        for blocker in artifact.get("blockers", [])
        if str(blocker).strip()
    ] if isinstance(artifact.get("blockers"), list) else []
    diagnosis = artifact.get("course3_audio_diagnosis")
    diagnosis = diagnosis if isinstance(diagnosis, dict) else None
    route_doctor = artifact.get("course3_route_doctor")
    route_doctor = route_doctor if isinstance(route_doctor, dict) else None
    auto_master = artifact.get("auto_master_recommendation")
    auto_master = auto_master if isinstance(auto_master, dict) else None
    checks = artifact.get("checks")
    checks = checks if isinstance(checks, dict) else None
    readiness = artifact.get("readiness")
    readiness = readiness if isinstance(readiness, dict) else None
    passed = artifact.get("passed") is True and (
        not isinstance(readiness, dict) or readiness.get("course3_audio") is True
    )
    status = (
        "passed"
        if passed
        else str(route_doctor.get("status"))
        if isinstance(route_doctor, dict) and route_doctor.get("status")
        else str(diagnosis.get("severity"))
        if isinstance(diagnosis, dict) and diagnosis.get("severity")
        else "failed"
    )
    return {
        "status": status,
        "path": str(path),
        "passed": passed,
        "blockers": blockers,
        "readiness": readiness,
        "diagnosis": diagnosis,
        "course3_route_doctor": route_doctor,
        "auto_master_recommendation": auto_master,
        "checks": checks,
        "errors": [] if artifact.get("passed") is True or blockers else ["passed is not true"],
    }


def _physical_readiness_status(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    artifact, error = _read_json(path)
    if artifact is None:
        return {
            "status": "failed",
            "path": str(path),
            "passed": False,
            "blockers": [str(error)],
            "errors": [str(error)],
        }

    blockers = [
        str(blocker)
        for blocker in artifact.get("blockers", [])
        if str(blocker).strip()
    ] if isinstance(artifact.get("blockers"), list) else []
    doctor = artifact.get("physical_connection_doctor")
    doctor = doctor if isinstance(doctor, dict) else None
    hardware_connection = artifact.get("hardware_connection")
    hardware_connection = hardware_connection if isinstance(hardware_connection, dict) else None
    checks = artifact.get("checks")
    checks = checks if isinstance(checks, dict) else None
    readiness = artifact.get("readiness")
    readiness = readiness if isinstance(readiness, dict) else None
    passed = artifact.get("passed") is True and (
        not isinstance(readiness, dict) or readiness.get("physical_learn") is True
    )
    status = (
        "passed"
        if passed
        else str(doctor.get("status"))
        if isinstance(doctor, dict) and doctor.get("status")
        else "failed"
    )
    return {
        "status": status,
        "path": str(path),
        "passed": passed,
        "blockers": blockers,
        "readiness": readiness,
        "physical_connection_doctor": doctor,
        "hardware_connection": hardware_connection,
        "checks": checks,
        "errors": [] if artifact.get("passed") is True or blockers else ["passed is not true"],
    }


def _merge_physical_readiness(
    physical: dict[str, Any],
    readiness: dict[str, Any] | None,
) -> dict[str, Any]:
    if readiness is None:
        return physical
    merged = dict(physical)
    merged["readiness_status"] = readiness
    if physical.get("passed") is True:
        return merged

    merged["blockers"] = _dedupe(
        list(physical.get("blockers") or []) + list(readiness.get("blockers") or [])
    )
    doctor = readiness.get("physical_connection_doctor")
    if isinstance(doctor, dict):
        merged["physical_connection_doctor"] = doctor
    hardware_connection = readiness.get("hardware_connection")
    if isinstance(hardware_connection, dict):
        merged["hardware_connection"] = hardware_connection
    return merged


def _merge_course3_readiness(
    course3: dict[str, Any],
    readiness: dict[str, Any] | None,
) -> dict[str, Any]:
    if readiness is None:
        return course3
    merged = dict(course3)
    merged["readiness_status"] = readiness
    if course3.get("passed") is True:
        return merged

    merged["blockers"] = _dedupe(
        list(course3.get("blockers") or []) + list(readiness.get("blockers") or [])
    )
    diagnosis = readiness.get("diagnosis")
    if isinstance(diagnosis, dict):
        merged["diagnosis"] = diagnosis
    route_doctor = readiness.get("course3_route_doctor")
    if isinstance(route_doctor, dict):
        merged["course3_route_doctor"] = route_doctor
    auto_master = readiness.get("auto_master_recommendation")
    if isinstance(auto_master, dict):
        merged["auto_master_recommendation"] = auto_master
    return merged


def _live_requirement_status(paths: list[Path], requirement: Requirement) -> dict[str, Any]:
    attempts: list[dict[str, Any]] = []
    for path in paths:
        try:
            artifact = load_artifact(path)
        except Exception as exc:
            attempts.append(
                {
                    "path": str(path),
                    "strict_valid": False,
                    "strict_errors": [repr(exc)],
                    "unavailable_valid": False,
                    "unavailable_errors": [repr(exc)],
                    "diagnosis": None,
                }
            )
            continue
        diagnosis = (
            _course3_audio_diagnosis(artifact)
            if requirement == "course3"
            else _physical_probe_diagnosis(artifact)
            if requirement == "physical"
            else None
        )
        physical_connection_doctor = (
            _physical_connection_doctor(artifact) if requirement == "physical" else None
        )
        route_plan = _course3_route_plan(artifact) if requirement == "course3" else None
        auto_master_recommendation = (
            _course3_auto_master_recommendation(artifact) if requirement == "course3" else None
        )
        playback_nudge = (
            _course3_playback_nudge(artifact) if requirement == "course3" else None
        )
        probe_operator_action = (
            _course3_probe_operator_action(artifact) if requirement == "course3" else None
        )
        strict = validate_artifact(
            artifact,
            required={requirement},
            allow_skipped=set(),
        )
        unavailable = validate_artifact(
            artifact,
            required={requirement},
            allow_skipped={requirement} if requirement in {"physical", "course3"} else set(),
        )
        attempts.append(
            {
                "path": str(path),
                "strict_valid": strict["valid"],
                "strict_errors": strict["errors"],
                "unavailable_valid": unavailable["valid"],
                "unavailable_errors": unavailable["errors"],
                "diagnosis": diagnosis,
                "physical_connection_doctor": physical_connection_doctor,
                "route_plan": route_plan,
                "auto_master_recommendation": auto_master_recommendation,
                "playback_nudge": playback_nudge,
                "probe_operator_action": probe_operator_action,
            }
        )
    passed = _best_live_attempt(
        [attempt for attempt in attempts if attempt["strict_valid"] is True],
        requirement=requirement,
    )
    unavailable = _best_live_attempt(
        [
            attempt
            for attempt in attempts
            if attempt["strict_valid"] is not True
            and attempt["unavailable_valid"] is True
            and requirement in {"physical", "course3"}
        ],
        requirement=requirement,
    )
    if passed is not None:
        return {
            "status": "passed",
            "passed": True,
            "path": passed["path"],
            "blockers": [],
            "diagnosis": passed.get("diagnosis"),
            "physical_connection_doctor": passed.get("physical_connection_doctor"),
            "route_plan": passed.get("route_plan"),
            "auto_master_recommendation": passed.get("auto_master_recommendation"),
            "playback_nudge": passed.get("playback_nudge"),
            "probe_operator_action": passed.get("probe_operator_action"),
            "attempts": attempts,
        }
    if unavailable is not None:
        return {
            "status": "unavailable",
            "passed": False,
            "path": unavailable["path"],
            "blockers": unavailable["strict_errors"],
            "diagnosis": unavailable.get("diagnosis"),
            "physical_connection_doctor": unavailable.get("physical_connection_doctor"),
            "route_plan": unavailable.get("route_plan"),
            "auto_master_recommendation": unavailable.get("auto_master_recommendation"),
            "playback_nudge": unavailable.get("playback_nudge"),
            "probe_operator_action": unavailable.get("probe_operator_action"),
            "attempts": attempts,
        }
    blockers: list[str] = []
    for attempt in attempts:
        blockers.extend(str(error) for error in attempt["strict_errors"])
    if not attempts:
        blockers.append(f"{requirement} proof artifact is missing")
    return {
        "status": "missing" if not attempts else "failed",
        "passed": False,
        "path": None,
        "blockers": _dedupe(blockers),
        "diagnosis": next(
            (attempt.get("diagnosis") for attempt in attempts if attempt.get("diagnosis")),
            None,
        ),
        "physical_connection_doctor": next(
            (
                attempt.get("physical_connection_doctor")
                for attempt in attempts
                if attempt.get("physical_connection_doctor")
            ),
            None,
        ),
        "route_plan": next(
            (attempt.get("route_plan") for attempt in attempts if attempt.get("route_plan")),
            None,
        ),
        "auto_master_recommendation": next(
            (
                attempt.get("auto_master_recommendation")
                for attempt in attempts
                if attempt.get("auto_master_recommendation")
            ),
            None,
        ),
        "playback_nudge": next(
            (attempt.get("playback_nudge") for attempt in attempts if attempt.get("playback_nudge")),
            None,
        ),
        "probe_operator_action": next(
            (
                attempt.get("probe_operator_action")
                for attempt in attempts
                if attempt.get("probe_operator_action")
            ),
            None,
        ),
        "attempts": attempts,
    }


def _best_live_attempt(
    attempts: list[dict[str, Any]],
    *,
    requirement: Requirement,
) -> dict[str, Any] | None:
    if not attempts:
        return None
    if requirement != "course3":
        return attempts[0]
    return max(attempts, key=_course3_attempt_score)


def _course3_attempt_score(attempt: dict[str, Any]) -> int:
    score = 0
    if attempt.get("strict_valid") is True:
        score += 1000
    if attempt.get("unavailable_valid") is True:
        score += 100

    recommendation = attempt.get("auto_master_recommendation")
    if isinstance(recommendation, dict):
        score += 50
        if recommendation.get("ok") is True:
            score += 10
        if recommendation.get("source"):
            score += 5
        if recommendation.get("reason"):
            score += 5

    route_plan = attempt.get("route_plan")
    if isinstance(route_plan, dict):
        score += 20
        candidate = route_plan.get("auto_master_fallback_candidate")
        if isinstance(candidate, dict):
            if candidate.get("source"):
                score += 4
            if candidate.get("reason"):
                score += 6
        selected = route_plan.get("selected_input")
        if isinstance(selected, dict) and selected.get("reason"):
            score += 3

    diagnosis = attempt.get("diagnosis")
    if isinstance(diagnosis, dict):
        score += 10
        if diagnosis.get("next_action"):
            score += 3
        if diagnosis.get("nowplaying_hint"):
            score += 8
        if isinstance(diagnosis.get("nowplaying"), dict):
            score += 3

    playback_nudge = attempt.get("playback_nudge")
    if isinstance(playback_nudge, dict) and playback_nudge.get("ok") is True:
        score += 5

    probe_operator_action = attempt.get("probe_operator_action")
    if isinstance(probe_operator_action, dict):
        score += 12
        if probe_operator_action.get("route"):
            score += 3
        if isinstance(probe_operator_action.get("steps"), list):
            score += min(3, len(probe_operator_action["steps"]))

    strict_errors = attempt.get("strict_errors")
    if isinstance(strict_errors, list):
        score -= len(strict_errors)
    return score


def _course3_audio_diagnosis(artifact: dict[str, Any]) -> dict[str, Any] | None:
    stages = artifact.get("stages")
    if not isinstance(stages, dict):
        return None
    for stage_name in ("course3_probe", "readiness_before_probes", "readiness_before"):
        stage = stages.get(stage_name)
        if not isinstance(stage, dict):
            continue
        result = stage.get("result")
        if not isinstance(result, dict):
            continue
        diagnosis = result.get("course3_audio_diagnosis")
        if isinstance(diagnosis, dict):
            return diagnosis
        last = result.get("last")
        if isinstance(last, dict):
            diagnosis = last.get("course3_audio_diagnosis")
            if isinstance(diagnosis, dict):
                return diagnosis
    return None


def _normalize_operator_action(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    prompt = str(raw.get("prompt") or "").strip()
    if not prompt:
        return None
    action: dict[str, Any] = {"prompt": prompt}
    route = str(raw.get("route") or "").strip()
    if route:
        action["route"] = route
    steps_raw = raw.get("steps")
    if isinstance(steps_raw, list):
        steps = [str(step).strip() for step in steps_raw if str(step).strip()]
        if steps:
            action["steps"] = steps
    for key in ("nowplaying_blocker", "source", "reason"):
        value = raw.get(key)
        if value is not None and str(value).strip():
            action[key] = str(value)
    return action


def _course3_probe_operator_action(artifact: dict[str, Any]) -> dict[str, Any] | None:
    stages = artifact.get("stages")
    if not isinstance(stages, dict):
        return None
    for stage_name in ("course3_probe", "course3_readiness_wait", "readiness_before_probes"):
        stage = stages.get(stage_name)
        if not isinstance(stage, dict):
            continue
        result = stage.get("result")
        if not isinstance(result, dict):
            continue
        candidates = [
            result.get("operator_action"),
            result.get("diagnostics", {}).get("operator_action")
            if isinstance(result.get("diagnostics"), dict)
            else None,
            result.get("last_lens", {}).get("operator_action")
            if isinstance(result.get("last_lens"), dict)
            else None,
            result.get("last", {}).get("operator_action")
            if isinstance(result.get("last"), dict)
            else None,
        ]
        for candidate in candidates:
            operator_action = _normalize_operator_action(candidate)
            if operator_action is not None:
                return operator_action
    return None


def _physical_probe_diagnosis(artifact: dict[str, Any]) -> dict[str, Any] | None:
    stages = artifact.get("stages")
    if not isinstance(stages, dict):
        return None
    for stage_name in ("physical_probe", "physical_readiness_wait", "readiness_before_probes"):
        stage = stages.get(stage_name)
        if not isinstance(stage, dict):
            continue
        result = stage.get("result")
        if not isinstance(result, dict):
            continue
        diagnosis = result.get("diagnosis")
        if isinstance(diagnosis, dict):
            return diagnosis
        last = result.get("last")
        if isinstance(last, dict):
            diagnosis = last.get("physical_probe_diagnosis")
            if isinstance(diagnosis, dict):
                return diagnosis
    return None


def _physical_connection_doctor(artifact: dict[str, Any]) -> dict[str, Any] | None:
    stages = artifact.get("stages")
    if not isinstance(stages, dict):
        return None
    for stage_name in ("physical_probe", "physical_readiness_wait", "readiness_before_probes"):
        stage = stages.get(stage_name)
        if not isinstance(stage, dict):
            continue
        result = stage.get("result")
        if not isinstance(result, dict):
            continue
        doctor = result.get("physical_connection_doctor")
        if isinstance(doctor, dict):
            return doctor
        last = result.get("last")
        if isinstance(last, dict):
            doctor = last.get("physical_connection_doctor")
            if isinstance(doctor, dict):
                return doctor
    return None


def _course3_route_plan(artifact: dict[str, Any]) -> dict[str, Any] | None:
    stages = artifact.get("stages")
    if not isinstance(stages, dict):
        return None
    app_start = stages.get("app_start")
    if not isinstance(app_start, dict):
        return None
    result = app_start.get("result")
    if not isinstance(result, dict):
        return None
    audio_env = result.get("audio_env")
    runtime = result.get("audio_runtime")
    if not isinstance(audio_env, dict) and not isinstance(runtime, dict):
        return None

    plan: dict[str, Any] = {}
    if isinstance(audio_env, dict):
        for key in (
            "input_device",
            "auto_master_input",
            "auto_master_fallback_candidate",
            "auto_master_fallback_device",
            "auto_master_fallback_source",
            "auto_master_fallback_rejected_reason",
        ):
            if key in audio_env:
                plan[key] = audio_env.get(key)
    if isinstance(runtime, dict):
        selected = runtime.get("auto_master_input")
        if isinstance(selected, dict):
            plan["selected_input"] = {
                "name": selected.get("name"),
                "sample_rate": selected.get("sample_rate"),
                "live_signal": selected.get("live_signal"),
                "reason": selected.get("reason"),
            }
    return plan or None


def _course3_auto_master_recommendation(artifact: dict[str, Any]) -> dict[str, Any] | None:
    stages = artifact.get("stages")
    if not isinstance(stages, dict):
        return None
    for stage_name in (
        "readiness_before_probes",
        "readiness_before",
        "course3_readiness_wait",
        "course3_probe",
    ):
        stage = stages.get(stage_name)
        if not isinstance(stage, dict):
            continue
        result = stage.get("result")
        if not isinstance(result, dict):
            continue
        recommendation = result.get("auto_master_recommendation")
        if isinstance(recommendation, dict):
            return recommendation
        last = result.get("last")
        if isinstance(last, dict):
            recommendation = last.get("auto_master_recommendation")
            if isinstance(recommendation, dict):
                return recommendation
    return None


def _course3_playback_nudge(artifact: dict[str, Any]) -> dict[str, Any] | None:
    stages = artifact.get("stages")
    if not isinstance(stages, dict):
        return None
    stage = stages.get("rekordbox_playback_nudge")
    if not isinstance(stage, dict):
        return None
    result = stage.get("result")
    row: dict[str, Any] = {
        "status": stage.get("status"),
        "reason": stage.get("reason"),
    }
    if isinstance(result, dict):
        for key in ("ok", "action", "returncode", "error", "skipped", "precheck"):
            if key in result:
                row[key] = result.get(key)
    return {key: value for key, value in row.items() if value is not None}


def _dedupe(values: list[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return deduped


def _curriculum_status(frontend_path: Path | None) -> dict[str, Any]:
    report = audit_curriculum(frontend_path=frontend_path)
    return {
        "passed": report.get("passed") is True,
        "beginner_lessons": report.get("counts", {}).get("beginner_lessons"),
        "beginner_course_ids": report.get("beginner_course_ids", []),
        "frontend_projection": report.get("frontend_projection"),
        "new_course_contract": report.get("new_course_contract", []),
        "course_pack_contract": report.get("course_pack_contract"),
        "flow_contract_summary": report.get("flow_contract_summary"),
        "unlock_gate_contract": report.get("unlock_gate_contract"),
        "copy_truthfulness_contract": report.get("copy_truthfulness_contract"),
        "transcript_inventory": report.get("transcript_inventory"),
        "errors": report.get("errors", []),
        "warnings": report.get("warnings", []),
    }


def _exemplar_status(approval_path: Path | None) -> dict[str, Any]:
    report = _enrich_exemplar_operator_action(audit_packaged_bank(approval_path=approval_path))
    return {
        "technical_passed": report.get("technical_passed") is True,
        "release_ready": report.get("release_ready") is True,
        "human_ear_pass_required": report.get("human_ear_pass_required") is True,
        "human_ear_pass": report.get("human_ear_pass"),
        "approval_path": str(approval_path) if approval_path is not None else None,
        "bank_fingerprint": report.get("bank_fingerprint"),
        "diagnosis": report.get("diagnosis"),
        "operator_commands": report.get("operator_commands"),
        "operator_action": report.get("operator_action"),
        "output_devices": report.get("output_devices"),
        "output_device_error": report.get("output_device_error"),
        "technical_failures": report.get("technical_failures", []),
        "track_count": len(report.get("tracks", []) if isinstance(report.get("tracks"), list) else []),
    }


def _completion_blockers(
    *,
    curriculum: dict[str, Any],
    exemplars: dict[str, Any],
    python_quality: dict[str, Any],
    frontend_quality: dict[str, Any],
    desktop_quality: dict[str, Any],
    tauri_smoke: dict[str, Any],
    live: dict[str, Any],
) -> list[str]:
    blockers: list[str] = []
    if curriculum["passed"] is not True:
        blockers.append("curriculum audit is not passing")
    if exemplars["technical_passed"] is not True:
        blockers.append("packaged EQ exemplar technical audit is not passing")
    elif exemplars["release_ready"] is not True:
        blockers.append("packaged EQ exemplar human ear-pass is pending")
    if python_quality["passed"] is not True:
        blockers.append("full Learn Python quality gate is missing or failing")
    if frontend_quality["passed"] is not True:
        blockers.append("full Learn frontend quality gate is missing or failing")
    if desktop_quality["passed"] is not True:
        blockers.append("Learn desktop shell quality gate is missing or failing")
    if tauri_smoke["passed"] is not True:
        blockers.append("launched Tauri Learn smoke is missing or failing")
    for requirement, label in (
        ("screen", "screen/on-deck Learn proof"),
        ("physical", "physical controller lesson proof"),
        ("course3", "Course 3 routed-audio count-in proof"),
    ):
        status = live[requirement]
        if status["passed"] is not True:
            blockers.append(f"{label} is not strictly proven")
    return blockers


def _completion_row(
    *,
    row_id: str,
    requirement: str,
    passed: bool,
    evidence: dict[str, Any],
    blockers: list[str] | None = None,
    next_actions: list[str] | None = None,
    release_gate: bool = True,
    category: str = "deterministic",
) -> dict[str, Any]:
    return {
        "id": row_id,
        "requirement": requirement,
        "category": category,
        "release_gate": release_gate,
        "status": "proven" if passed else "not_proven",
        "evidence": evidence,
        "blockers": blockers or [],
        "next_actions": next_actions or [],
    }


def _quality_command_names(quality: dict[str, Any]) -> list[str]:
    commands = quality.get("commands")
    rows = commands if isinstance(commands, list) else []
    return [
        str(row.get("name"))
        for row in rows
        if isinstance(row, dict) and row.get("name") is not None
    ]


def _objective_audit_row(
    *,
    rows_by_id: dict[str, dict[str, Any]],
    objective_id: str,
    objective: str,
    evidence_row_ids: list[str],
) -> dict[str, Any]:
    evidence_rows = [
        rows_by_id[row_id]
        for row_id in evidence_row_ids
        if row_id in rows_by_id
    ]
    missing_row_ids = [
        row_id
        for row_id in evidence_row_ids
        if row_id not in rows_by_id
    ]
    not_proven_rows = [
        row for row in evidence_rows if row.get("status") != "proven"
    ]
    blockers: list[str] = []
    next_actions: list[str] = []
    for row in not_proven_rows:
        blockers.extend(str(value) for value in row.get("blockers") or [])
        next_actions.extend(
            str(value)
            for value in row.get("next_actions") or []
            if isinstance(value, str) and value.strip()
        )
    for row_id in missing_row_ids:
        blockers.append(f"objective evidence row missing: {row_id}")
    return {
        "id": objective_id,
        "objective": objective,
        "status": "proven" if not not_proven_rows and not missing_row_ids else "not_proven",
        "evidence_row_ids": evidence_row_ids,
        "proven_row_ids": [
            str(row.get("id"))
            for row in evidence_rows
            if row.get("status") == "proven"
        ],
        "blocking_row_ids": [
            str(row.get("id"))
            for row in not_proven_rows
            if row.get("id") is not None
        ],
        "missing_row_ids": missing_row_ids,
        "blockers": _dedupe(blockers),
        "next_actions": _dedupe(next_actions),
    }


def _objective_audit(completion_matrix: dict[str, Any]) -> dict[str, Any]:
    """Map the user's Learn objective to concrete verifier rows."""
    requirement_rows = completion_matrix.get("requirements")
    requirement_rows = requirement_rows if isinstance(requirement_rows, list) else []
    rows_by_id = {
        str(row.get("id")): row
        for row in requirement_rows
        if isinstance(row, dict) and row.get("id") is not None
    }
    objectives = [
        _objective_audit_row(
            rows_by_id=rows_by_id,
            objective_id="full_36_lesson_beginner_module",
            objective=(
                "All 36 beginner lessons are real structured flows with "
                "canonical ids, deterministic verification, adaptive hints, "
                "progress, and runtime traversal."
            ),
            evidence_row_ids=[
                "curriculum_36_lesson_contract",
                "all_lessons_runtime_contract",
                "python_quality_suite",
            ],
        ),
        _objective_audit_row(
            rows_by_id=rows_by_id,
            objective_id="simple_practice_booth_no_syllabus_wall",
            objective=(
                "The user sees a calm practice booth with one clear prompt, "
                "one action, opt-in lesson choice, replay support, and no "
                "default syllabus wall."
            ),
            evidence_row_ids=[
                "frontstage_simplicity_contract",
                "lesson_choice_replay_contract",
                "browser_practice_booth_quality_contract",
                "curriculum_36_lesson_contract",
            ],
        ),
        _objective_audit_row(
            rows_by_id=rows_by_id,
            objective_id="physical_or_on_screen_practice_paths",
            objective=(
                "A beginner can practice with either a physical controller or "
                "the on-screen deck, with deterministic proof for both paths."
            ),
            evidence_row_ids=[
                "physical_controller_path",
                "on_screen_deck_path",
                "browser_practice_booth_quality_contract",
            ],
        ),
        _objective_audit_row(
            rows_by_id=rows_by_id,
            objective_id="grounded_adaptive_teaching_loop",
            objective=(
                "The backstage loop observes, decides, teaches, verifies, and "
                "adapts with grounded evidence instead of generic coaching."
            ),
            evidence_row_ids=[
                "teaching_loop_contract",
                "adaptive_coaching_runtime_contract",
                "session_debrief_profile_contract",
            ],
        ),
        _objective_audit_row(
            rows_by_id=rows_by_id,
            objective_id="existing_coded_power_reuse",
            objective=(
                "Learn reuses vibemix controller state, live audio, evidence "
                "registry, library/cue/section intelligence, model routing, "
                "IPC/socket, session, debrief, and profile seams."
            ),
            evidence_row_ids=[
                "capability_reuse_contract",
                "teaching_loop_contract",
                "course3_auto_master_finder_contract",
                "course3_mix_count_in_anchor_contract",
                "session_debrief_profile_contract",
                "tauri_learn_window_contract",
            ],
        ),
        _objective_audit_row(
            rows_by_id=rows_by_id,
            objective_id="course3_live_play_mode",
            objective=(
                "Course 3 live play mode proves routed master audio, citable "
                "deck context, and grounded next-phrase count-ins."
            ),
            evidence_row_ids=[
                "course3_auto_master_finder_contract",
                "course3_mix_count_in_anchor_contract",
                "course3_live_audio_play_mode",
            ],
        ),
        _objective_audit_row(
            rows_by_id=rows_by_id,
            objective_id="future_course_extensibility",
            objective=(
                "New courses can be integrated through a machine-checked "
                "course-pack preflight, generated projection, prompt contract, "
                "truthfulness checks, and merge plan."
            ),
            evidence_row_ids=["future_course_extension_contract"],
        ),
        _objective_audit_row(
            rows_by_id=rows_by_id,
            objective_id="app_wiring_and_quality",
            objective=(
                "The Learn module is wired into the app and passes frontend, "
                "desktop, launched Tauri, and consolidated quality gates."
            ),
            evidence_row_ids=[
                "app_entry_contract",
                "tauri_learn_window_contract",
                "frontend_quality_suite",
                "desktop_shell_quality",
                "launched_tauri_practice_booth",
            ],
        ),
        _objective_audit_row(
            rows_by_id=rows_by_id,
            objective_id="audible_example_quality",
            objective=(
                "Packaged EQ examples are technically valid and human ear-passed "
                "for the beginner teaching experience."
            ),
            evidence_row_ids=["packaged_eq_exemplar_ear_pass"],
        ),
    ]
    proven_objectives = [
        row for row in objectives if row.get("status") == "proven"
    ]
    not_proven_objectives = [
        row for row in objectives if row.get("status") != "proven"
    ]
    return {
        "schema_version": 1,
        "summary": {
            "total": len(objectives),
            "proven": len(proven_objectives),
            "not_proven": len(not_proven_objectives),
            "release_ready": not not_proven_objectives,
            "blocking_objective_ids": [
                str(row.get("id")) for row in not_proven_objectives
            ],
        },
        "objectives": objectives,
    }


def _course_extension_contract_summary(
    curriculum: dict[str, Any],
    contract: dict[str, Any],
) -> dict[str, Any]:
    source_of_truth = contract.get("source_of_truth")
    source_of_truth = source_of_truth if isinstance(source_of_truth, dict) else {}
    python_entries = contract.get("python_entries")
    python_entries = python_entries if isinstance(python_entries, list) else []
    draft_validator = contract.get("draft_validator")
    draft_validator = draft_validator if isinstance(draft_validator, dict) else {}
    python_entry_names = [
        str(entry.get("name"))
        for entry in python_entries
        if isinstance(entry, dict) and entry.get("name") is not None
    ]
    transcript_required_fields = contract.get("transcript_required_fields")
    transcript_required_fields = (
        transcript_required_fields if isinstance(transcript_required_fields, list) else []
    )
    canonical_id_contract = contract.get("canonical_id_contract")
    canonical_id_contract = (
        canonical_id_contract if isinstance(canonical_id_contract, dict) else {}
    )
    starter_template_contract = contract.get("starter_template_contract")
    starter_template_contract = (
        starter_template_contract if isinstance(starter_template_contract, dict) else {}
    )
    frontend_contract = contract.get("frontend_contract")
    frontend_contract = frontend_contract if isinstance(frontend_contract, dict) else {}
    flow_contract = contract.get("flow_contract")
    flow_contract = flow_contract if isinstance(flow_contract, dict) else {}
    capability_contract = contract.get("capability_contract")
    capability_contract = capability_contract if isinstance(capability_contract, dict) else {}
    unlock_gate_contract = contract.get("unlock_gate_contract")
    unlock_gate_contract = unlock_gate_contract if isinstance(unlock_gate_contract, dict) else {}
    verification_commands = contract.get("verification_commands")
    verification_commands = verification_commands if isinstance(verification_commands, list) else []

    blockers: list[str] = []
    required_sources = {
        "python_curriculum": "src/vibemix/learn/curriculum.py",
        "transcript_root": "src/vibemix/learn/transcripts/",
        "frontend_projection": "tauri/ui/src/learn/lesson/curriculum-meta.ts",
        "draft_preflight": "src/vibemix/learn/course_pack.py",
        "draft_preflight_cli": "scripts/validate_learn_course_pack.py",
    }
    missing_sources = sorted(
        key
        for key, expected in required_sources.items()
        if source_of_truth.get(key) != expected
    )
    if missing_sources:
        blockers.append(f"course extension source map missing: {', '.join(missing_sources)}")

    required_entries = {"COURSE_REGISTRY", "COURSE_FRAMES", "CURRICULUM"}
    missing_entries = sorted(required_entries - set(python_entry_names))
    if missing_entries:
        blockers.append(f"course extension registry entries missing: {', '.join(missing_entries)}")

    if (
        draft_validator.get("function")
        != "vibemix.learn.course_pack.validate_course_pack_draft"
    ):
        blockers.append("course extension draft validator is missing")
    if (
        draft_validator.get("cli")
        != "uv run python scripts/validate_learn_course_pack.py <course-pack.json>"
    ):
        blockers.append("course extension draft validator CLI is missing")
    if draft_validator.get("template_cli") != (
        "uv run python scripts/validate_learn_course_pack.py "
        "--init-template <dir> --course-number 4 --slug <slug>"
    ):
        blockers.append("course extension draft template CLI is missing")
    validator_fields = set(str(field) for field in draft_validator.get("result_fields") or [])
    required_validator_fields = {
        "ok",
        "lesson_count",
        "step_count",
        "flow_preview",
        "observed_capabilities",
        "required_progress_fields",
        "integration_plan",
        "prompt_contract",
        "teaching_grounding_contract",
        "hint_grounding_contract",
        "authoring_contract",
        "copy_truthfulness",
        "errors",
    }
    missing_validator_fields = sorted(required_validator_fields - validator_fields)
    if missing_validator_fields:
        blockers.append(
            "course extension draft validator fields missing: "
            + ", ".join(missing_validator_fields)
        )

    required_transcript_fields = {
        "lesson_id",
        "title",
        "system_instruction_addendum",
        "tutor_speak",
        "expected_action",
        "hints",
    }
    missing_transcript_fields = sorted(
        required_transcript_fields - set(str(field) for field in transcript_required_fields)
    )
    if missing_transcript_fields:
        blockers.append(
            "course extension transcript fields missing: "
            + ", ".join(missing_transcript_fields)
        )

    if canonical_id_contract.get("course_id_pattern") != "course_<number>_<slug>":
        blockers.append("course extension canonical course_id pattern is missing")
    if canonical_id_contract.get("lesson_id_pattern") != "L<number>.<two digits>":
        blockers.append("course extension canonical lesson_id pattern is missing")
    if not str(canonical_id_contract.get("rule") or "").strip():
        blockers.append("course extension canonical id rule is missing")
    if (
        canonical_id_contract.get("starter_template")
        != "scripts/validate_learn_course_pack.py --init-template"
    ):
        blockers.append("course extension starter template is missing")
    if starter_template_contract.get("writes_manifest_authoring_contract") is not True:
        blockers.append("course extension starter template authoring contract is missing")
    if (
        starter_template_contract.get("frontstage")
        != "one prompt, one action, one grounded response"
    ):
        blockers.append("course extension starter template frontstage rule is missing")
    if starter_template_contract.get("default_input_surfaces") != ["hardware", "screen"]:
        blockers.append("course extension starter template input surfaces are missing")
    if starter_template_contract.get("starter_expected_action") != {
        "type": "button",
        "control": "cue",
        "deck": "A",
        "direction": "down",
    }:
        blockers.append("course extension starter expected action is missing")
    if starter_template_contract.get("required_hint_count") != 3:
        blockers.append("course extension starter template hint floor is missing")
    starter_prompt_limits = starter_template_contract.get("prompt_limits")
    starter_prompt_limits = (
        starter_prompt_limits if isinstance(starter_prompt_limits, dict) else {}
    )
    if starter_prompt_limits.get("max_chars") != 150:
        blockers.append("course extension starter prompt character cap is missing")
    if starter_prompt_limits.get("max_words") != 24:
        blockers.append("course extension starter prompt word cap is missing")
    if starter_prompt_limits.get("max_sentences") != 2:
        blockers.append("course extension starter prompt sentence cap is missing")
    starter_copy_rules = starter_template_contract.get("copy_rules")
    starter_copy_rules = starter_copy_rules if isinstance(starter_copy_rules, list) else []
    if "do not promise automatic debrief opening" not in starter_copy_rules:
        blockers.append("course extension starter copy truthfulness rule is missing")
    starter_post_merge_commands = starter_template_contract.get("post_merge_commands")
    starter_post_merge_commands = (
        starter_post_merge_commands if isinstance(starter_post_merge_commands, list) else []
    )
    required_starter_commands = {
        "uv run python scripts/export_learn_curriculum_meta.py --check",
        "uv run pytest -q tests/learn/test_course_pack.py",
        (
            "uv run python scripts/run_learn_perfection_package.py --out "
            "/tmp/vibemix-live-learn-proof/learn-perfection-package-current.json"
        ),
    }
    missing_starter_commands = sorted(
        required_starter_commands - set(str(command) for command in starter_post_merge_commands)
    )
    if missing_starter_commands:
        blockers.append(
            "course extension starter post-merge commands missing: "
            + ", ".join(missing_starter_commands)
        )

    copy_truthfulness_contract = contract.get("copy_truthfulness_contract")
    copy_truthfulness_contract = (
        copy_truthfulness_contract
        if isinstance(copy_truthfulness_contract, dict)
        else {}
    )
    phrases = copy_truthfulness_contract.get("unsupported_auto_open_phrases")
    if not isinstance(phrases, list) or "debrief opens" not in phrases:
        blockers.append("course extension copy truthfulness phrases are missing")
    if not str(copy_truthfulness_contract.get("rule") or "").strip():
        blockers.append("course extension copy truthfulness rule is missing")

    if frontend_contract.get("manual_frontend_edits") != "forbidden":
        blockers.append("course extension frontend projection is not generated-only")
    if (
        frontend_contract.get("check_command")
        != "uv run python scripts/export_learn_curriculum_meta.py --check"
    ):
        blockers.append("course extension frontend projection check command is missing")
    if flow_contract.get("compiler") != "vibemix.learn.lesson_flow.build_lesson_flow":
        blockers.append("course extension flow compiler is not pinned")
    if not str(flow_contract.get("beginner_gate") or "").strip():
        blockers.append("course extension beginner flow gate is missing")
    prompt_contract = flow_contract.get("prompt_contract")
    prompt_contract = prompt_contract if isinstance(prompt_contract, dict) else {}
    if prompt_contract.get("max_chars") != 150:
        blockers.append("course extension prompt character cap is missing")
    if prompt_contract.get("max_words") != 24:
        blockers.append("course extension prompt word cap is missing")
    if prompt_contract.get("max_sentences") != 2:
        blockers.append("course extension prompt sentence cap is missing")
    if prompt_contract.get("single_line") is not True:
        blockers.append("course extension prompt single-line rule is missing")
    if prompt_contract.get("inline_lists_forbidden") is not True:
        blockers.append("course extension prompt list ban is missing")
    teaching_loop_contract = flow_contract.get("teaching_loop_contract")
    teaching_loop_contract = (
        teaching_loop_contract if isinstance(teaching_loop_contract, dict) else {}
    )
    if not str(teaching_loop_contract.get("teaching_turns") or "").strip():
        blockers.append("course extension teaching-turn grounding rule is missing")
    if not str(teaching_loop_contract.get("hint_turns") or "").strip():
        blockers.append("course extension hint grounding rule is missing")
    if not str(capability_contract.get("rule") or "").strip():
        blockers.append("course extension capability rule is missing")
    if not unlock_gate_contract.get("supported_unlock_gates"):
        blockers.append("course extension unlock-gate contract is missing")

    required_commands = {
        "uv run python scripts/audit_learn_curriculum.py",
        "uv run python scripts/export_learn_curriculum_meta.py --check",
        "uv run python scripts/validate_learn_course_pack.py <course-pack.json>",
        "uv run pytest -q tests/learn/test_course_pack.py",
        "uv run pytest -q tests/learn/test_lesson_flow_contract.py",
        "npm --prefix tauri/ui test -- tests/learn/test_curriculum_meta.spec.ts",
    }
    missing_commands = sorted(required_commands - set(str(command) for command in verification_commands))
    if missing_commands:
        blockers.append(
            "course extension verification commands missing: "
            + ", ".join(missing_commands)
        )
    if curriculum.get("passed") is not True:
        blockers.append("curriculum audit is not passing")

    return {
        "ok": not blockers,
        "source_of_truth": source_of_truth,
        "draft_validator": draft_validator,
        "python_entry_names": python_entry_names,
        "transcript_required_fields": transcript_required_fields,
        "transcript_inventory_contract": contract.get("transcript_inventory_contract"),
        "canonical_id_contract": canonical_id_contract,
        "starter_template_contract": starter_template_contract,
        "copy_truthfulness_contract": copy_truthfulness_contract,
        "frontend_contract": frontend_contract,
        "flow_contract": flow_contract,
        "prompt_contract": prompt_contract,
        "teaching_loop_contract": teaching_loop_contract,
        "capability_contract": capability_contract,
        "unlock_gate_contract": unlock_gate_contract,
        "verification_commands": verification_commands,
        "new_course_contract": curriculum.get("new_course_contract", []),
        "blockers": blockers,
    }


def _completion_matrix(
    *,
    curriculum: dict[str, Any],
    exemplars: dict[str, Any],
    python_quality: dict[str, Any],
    frontend_quality: dict[str, Any],
    desktop_quality: dict[str, Any],
    tauri_smoke: dict[str, Any],
    live: dict[str, Any],
) -> dict[str, Any]:
    contract = curriculum.get("course_pack_contract")
    contract = contract if isinstance(contract, dict) else {}
    capability_contract = contract.get("capability_contract")
    capability_contract = capability_contract if isinstance(capability_contract, dict) else {}
    declared_capabilities = set(capability_contract.get("capabilities") or [])
    extension_contract = _course_extension_contract_summary(curriculum, contract)
    required_capabilities = {
        "controller_state",
        "cue_section_lookahead",
        "debrief",
        "dj_profile",
        "evidence_registry",
        "library_exemplars",
        "library_suggestions",
        "live_audio",
        "on_screen_deck",
        "prepared_pool",
        "recital_observer",
        "recovery_drill",
        "session_recording",
        "session_state",
    }
    missing_capabilities = sorted(required_capabilities - declared_capabilities)
    flow_contract_summary = curriculum.get("flow_contract_summary")
    flow_contract_summary = (
        flow_contract_summary if isinstance(flow_contract_summary, dict) else {}
    )
    hint_grounding_contract = flow_contract_summary.get("hint_grounding_contract")
    hint_grounding_contract = (
        hint_grounding_contract if isinstance(hint_grounding_contract, dict) else {}
    )
    teaching_grounding_contract = flow_contract_summary.get(
        "teaching_grounding_contract"
    )
    teaching_grounding_contract = (
        teaching_grounding_contract
        if isinstance(teaching_grounding_contract, dict)
        else {}
    )
    teaching_turn_count = int(
        teaching_grounding_contract.get("teaching_turn_count") or 0
    )
    grounded_teaching_turn_count = int(
        teaching_grounding_contract.get("grounded_teaching_turn_count") or 0
    )
    cited_teaching_turn_count = int(
        teaching_grounding_contract.get("cited_teaching_turn_count") or 0
    )
    teaching_grounding_ok = (
        teaching_grounding_contract.get("ok") is True
        and teaching_turn_count >= 76
        and teaching_turn_count == grounded_teaching_turn_count
        and teaching_turn_count == cited_teaching_turn_count
    )
    hint_turn_count = int(hint_grounding_contract.get("hint_turn_count") or 0)
    grounded_hint_turn_count = int(
        hint_grounding_contract.get("grounded_hint_turn_count") or 0
    )
    cited_hint_turn_count = int(
        hint_grounding_contract.get("cited_hint_turn_count") or 0
    )
    hint_grounding_ok = (
        hint_grounding_contract.get("ok") is True
        and hint_turn_count >= 228
        and hint_turn_count == grounded_hint_turn_count
        and hint_turn_count == cited_hint_turn_count
    )
    rows = [
        _completion_row(
            row_id="curriculum_36_lesson_contract",
            requirement=(
                "All 36 beginner lessons are present, canonical, hand-authored, "
                "and compile through the Learn curriculum audit."
            ),
            passed=curriculum.get("passed") is True and curriculum.get("beginner_lessons") == 36,
            evidence={
                "beginner_lessons": curriculum.get("beginner_lessons"),
                "beginner_course_ids": curriculum.get("beginner_course_ids"),
                "frontend_projection": curriculum.get("frontend_projection"),
                "flow_contract_summary": curriculum.get("flow_contract_summary"),
                "unlock_gate_contract": curriculum.get("unlock_gate_contract"),
                "copy_truthfulness_contract": curriculum.get(
                    "copy_truthfulness_contract"
                ),
                "transcript_inventory": curriculum.get("transcript_inventory"),
            },
            blockers=list(curriculum.get("errors") or []),
        ),
        _completion_row(
            row_id="capability_reuse_contract",
            requirement=(
                "Course metadata declares the existing vibemix coded powers used by "
                "compiled lesson flows."
            ),
            passed=curriculum.get("passed") is True and not missing_capabilities,
            evidence={
                "declared_capabilities": sorted(declared_capabilities),
                "frontstage_modes": capability_contract.get("frontstage_modes"),
                "rule": capability_contract.get("rule"),
            },
            blockers=[f"missing declared capabilities: {', '.join(missing_capabilities)}"]
            if missing_capabilities
            else [],
        ),
        _completion_row(
            row_id="future_course_extension_contract",
            requirement=(
                "Adding future Learn courses has a machine-checked source map, "
                "registry/transcript contract, generated frontend projection, "
                "unlock-gate rule, and verification command set."
            ),
            passed=extension_contract["ok"] is True,
            evidence=extension_contract,
            blockers=list(extension_contract.get("blockers") or []),
            category="curriculum",
        ),
        _completion_row(
            row_id="python_quality_suite",
            requirement=(
                "The Learn Python quality pass has run Ruff, curriculum codegen "
                "check, the model-router literal guard, all-lesson runtime "
                "traversal, targeted adaptive coaching proof, auto-master "
                "finder proof, Course 3 mix-anchor proof, and the deterministic "
                "Learn pytest suite."
            ),
            passed=python_quality.get("passed") is True,
            evidence={
                "path": python_quality.get("path"),
                "required_commands": python_quality.get("required_commands"),
                "commands": python_quality.get("commands"),
            },
            blockers=list(python_quality.get("errors") or []),
            next_actions=[python_quality.get("operator_commands", {}).get("run")]
            if isinstance(python_quality.get("operator_commands"), dict)
            else [],
        ),
        _completion_row(
            row_id="all_lessons_runtime_contract",
            requirement=(
                "Every beginner lesson starts through the same IPC runtime path "
                "the UI uses, receives canonical action shapes, reaches "
                "LessonRuntime.completed, and persists completed progress."
            ),
            passed=python_quality.get("passed") is True
            and "learn_all_lessons_runtime_pytest" in _quality_command_names(python_quality),
            evidence={
                "path": python_quality.get("path"),
                "required_command": "learn_all_lessons_runtime_pytest",
                "covered_tests": ["tests/learn/test_all_lessons_runtime_path.py"],
                "lesson_count": 36,
                "runtime_path": [
                    "ipc.learn.start_lesson",
                    "ipc.learn.ack",
                    "ipc.learn.complete_lesson",
                    "LearnProgress persistence",
                ],
                "observer_lessons": ["L1.14", "L1.16", "L2.14"],
                "commands": python_quality.get("commands"),
            },
            blockers=(
                list(python_quality.get("errors") or [])
                + (
                    ["learn_all_lessons_runtime_pytest did not run"]
                    if "learn_all_lessons_runtime_pytest"
                    not in _quality_command_names(python_quality)
                    else []
                )
            ),
            next_actions=[python_quality.get("operator_commands", {}).get("run")]
            if isinstance(python_quality.get("operator_commands"), dict)
            else [],
            category="runtime_path",
        ),
        _completion_row(
            row_id="teaching_loop_contract",
            requirement=(
                "The Learn backstage loop proves observe, decide, teach, "
                "verify, and adapt turns through model_router and deterministic "
                "verification metadata."
            ),
            passed=python_quality.get("passed") is True
            and "learn_teaching_loop_pytest" in _quality_command_names(python_quality)
            and teaching_grounding_ok
            and hint_grounding_ok,
            evidence={
                "path": python_quality.get("path"),
                "required_command": "learn_teaching_loop_pytest",
                "model_router_guard": "learn_model_router_guard"
                in _quality_command_names(python_quality),
                "stages": ["observe", "decide", "teach", "verify", "adapt"],
                "teaching_grounding_contract": teaching_grounding_contract,
                "hint_grounding_contract": hint_grounding_contract,
                "covered_tests": ["tests/learn/test_teaching_loop.py"],
                "commands": python_quality.get("commands"),
            },
            blockers=(
                list(python_quality.get("errors") or [])
                + (
                    ["learn_model_router_guard did not run"]
                    if "learn_model_router_guard" not in _quality_command_names(python_quality)
                    else []
                )
                + (
                    ["all authored beginner teaching turns are not deterministically grounded"]
                    if not teaching_grounding_ok
                    else []
                )
                + (
                    ["all authored beginner hint turns are not deterministically grounded"]
                    if not hint_grounding_ok
                    else []
                )
            ),
            next_actions=[python_quality.get("operator_commands", {}).get("run")]
            if isinstance(python_quality.get("operator_commands"), dict)
            else [],
            category="teaching_loop",
        ),
        _completion_row(
            row_id="adaptive_coaching_runtime_contract",
            requirement=(
                "The Learn runtime emits grounded adaptive coaching for timed "
                "hints and wrong actions: hints stay on the active step, wrong "
                "screen or MIDI actions do not advance, citations point to the "
                "observed and expected controls, and strike counts persist."
            ),
            passed=python_quality.get("passed") is True
            and "learn_adaptive_coaching_pytest" in _quality_command_names(python_quality),
            evidence={
                "path": python_quality.get("path"),
                "required_command": "learn_adaptive_coaching_pytest",
                "covered_tests": [
                    "tests/learn/test_adaptive_coaching_runtime_contract.py",
                ],
                "runtime_behaviors": [
                    "timed hint strike emits teaching_loop.turn_kind=hint",
                    "wrong screen control emits teaching_loop.turn_kind=adapt without advancing",
                    "small MIDI movement writes registry-backed midi/screen citations",
                    "unfinished lesson strike count persists to LearnProgress",
                ],
                "citation_sources": ["midi", "screen"],
                "commands": python_quality.get("commands"),
            },
            blockers=(
                list(python_quality.get("errors") or [])
                + (
                    ["learn_adaptive_coaching_pytest did not run"]
                    if "learn_adaptive_coaching_pytest"
                    not in _quality_command_names(python_quality)
                    else []
                )
            ),
            next_actions=[python_quality.get("operator_commands", {}).get("run")]
            if isinstance(python_quality.get("operator_commands"), dict)
            else [],
            category="teaching_loop",
        ),
        _completion_row(
            row_id="course3_auto_master_finder_contract",
            requirement=(
                "Course 3 auto-master readiness resolves one safe capture input "
                "from live signal, saved Rekordbox route, macOS output route, "
                "and 48 kHz loopback fallbacks while exposing ranked candidate "
                "evidence and rejecting sample-rate mismatches before startup."
            ),
            passed=python_quality.get("passed") is True
            and "learn_auto_master_finder_pytest" in _quality_command_names(python_quality),
            evidence={
                "path": python_quality.get("path"),
                "required_command": "learn_auto_master_finder_pytest",
                "covered_tests": [
                    "tests/learn/test_auto_master_finder_contract.py",
                ],
                "finder_claims": [
                    "live capture candidates include ranked source/reason evidence",
                    "saved Rekordbox routes remain marked when unsampled",
                    "rate-mismatched fallbacks are rejected before app startup",
                ],
                "commands": python_quality.get("commands"),
            },
            blockers=(
                list(python_quality.get("errors") or [])
                + (
                    ["learn_auto_master_finder_pytest did not run"]
                    if "learn_auto_master_finder_pytest"
                    not in _quality_command_names(python_quality)
                    else []
                )
            ),
            next_actions=[python_quality.get("operator_commands", {}).get("run")]
            if isinstance(python_quality.get("operator_commands"), dict)
            else [],
            category="live_proof",
        ),
        _completion_row(
            row_id="course3_mix_count_in_anchor_contract",
            requirement=(
                "Course 3 count-in anchors work during a real two-deck mix only "
                "when Now Playing title identity exactly and unambiguously "
                "matches one citable deck row, preserving abstention for "
                "ambiguous titles."
            ),
            passed=python_quality.get("passed") is True
            and "learn_course3_mix_anchor_pytest" in _quality_command_names(python_quality),
            evidence={
                "path": python_quality.get("path"),
                "required_command": "learn_course3_mix_anchor_pytest",
                "covered_tests": [
                    "tests/state/test_refresh.py::test_tick_course3_live_uses_dj_cue_sections_for_phrase_anchor",
                    "tests/state/test_refresh.py::test_tick_course3_mix_uses_unambiguous_title_match_for_phrase_anchor",
                    "tests/state/test_refresh.py::test_tick_course3_mix_refuses_ambiguous_title_match_for_phrase_anchor",
                ],
                "anchor_policy": [
                    "single-deck Course 3 anchors still require DJ-authored cue sections",
                    "mix-state anchors require an exact unambiguous Now Playing title match",
                    "ambiguous duplicate deck titles keep next_phrase_cue_id null",
                ],
                "commands": python_quality.get("commands"),
            },
            blockers=(
                list(python_quality.get("errors") or [])
                + (
                    ["learn_course3_mix_anchor_pytest did not run"]
                    if "learn_course3_mix_anchor_pytest"
                    not in _quality_command_names(python_quality)
                    else []
                )
            ),
            next_actions=[python_quality.get("operator_commands", {}).get("run")]
            if isinstance(python_quality.get("operator_commands"), dict)
            else [],
            category="live_proof",
        ),
        _completion_row(
            row_id="session_debrief_profile_contract",
            requirement=(
                "Learn reuses the existing session/debrief/profile seams by "
                "logging lesson milestones to events.jsonl and making those "
                "events consumable by debrief critique/profile write-back paths."
            ),
            passed=python_quality.get("passed") is True
            and "learn_pytest" in _quality_command_names(python_quality),
            evidence={
                "path": python_quality.get("path"),
                "required_command": "learn_pytest",
                "session_events": [
                    "learn_lesson_loaded",
                    "learn_tutor_speak",
                    "learn_action_observed",
                    "learn_lesson_completed",
                ],
                "covered_tests": [
                    "tests/learn/test_runtime_evidence_grounding.py",
                    "tests/learn/test_session_debrief_integration.py",
                    "tests/learn/test_graduation.py",
                ],
                "graduation_practice_summary": (
                    "the L3.06 graduation handoff can fold persisted "
                    "hardware/screen practice-source memory into one grounded "
                    "status line without adding a dashboard"
                ),
                "commands": python_quality.get("commands"),
            },
            blockers=list(python_quality.get("errors") or []),
            next_actions=[python_quality.get("operator_commands", {}).get("run")]
            if isinstance(python_quality.get("operator_commands"), dict)
            else [],
            category="session_seams",
        ),
        _completion_row(
            row_id="frontend_quality_suite",
            requirement=(
                "The Learn frontend quality pass has run app-entry, frontstage "
                "simplicity, Tauri-window registration, choice/replay, Vitest "
                "Learn coverage, production build, focused browser booth "
                "quality, and broad browser Learn e2e."
            ),
            passed=frontend_quality.get("passed") is True,
            evidence={
                "path": frontend_quality.get("path"),
                "required_commands": frontend_quality.get("required_commands"),
                "commands": frontend_quality.get("commands"),
            },
            blockers=list(frontend_quality.get("errors") or []),
            next_actions=[frontend_quality.get("operator_commands", {}).get("run")]
            if isinstance(frontend_quality.get("operator_commands"), dict)
            else [],
        ),
        _completion_row(
            row_id="frontstage_simplicity_contract",
            requirement=(
                "The default Learn surface is a calm practice booth: one primary "
                "recommended action, the lesson map hidden by default, and progress "
                "snapshots or controller unplug events do not turn the frontstage "
                "into a syllabus wall."
            ),
            passed=frontend_quality.get("passed") is True
            and "learn_frontstage_simplicity_vitest" in _quality_command_names(frontend_quality),
            evidence={
                "path": frontend_quality.get("path"),
                "required_command": "learn_frontstage_simplicity_vitest",
                "covered_tests": [
                    "tests/learn/test_practice_booth_shell.spec.ts",
                    "tests/learn/test_tutor_speak_sr_announcement.spec.ts",
                ],
                "frontstage_default": "primary recommended action plus opt-in chooser",
                "hardware_unavailable": (
                    "controller disconnect leaves the booth on the on-screen deck, "
                    "keeps the lesson map opt-in, and repaints the active lesson "
                    "highlight after mid-lesson remounts"
                ),
                "action_receipts": (
                    "matched learner actions render a compact receipt naming the "
                    "control gesture, known input source, and action count; the "
                    "same receipt is announced through the tutor live region"
                ),
                "completion_reward": (
                    "completed lessons return to the one-action booth with a "
                    "short visible pass reward that distinguishes clean vs "
                    "hint-recovered completions, names the matched hardware/screen "
                    "source when known, and carries an accessible next-practice "
                    "label pointing at the refreshed recommendation"
                ),
                "in_progress_recommendation": (
                    "started-but-unfinished recommended lessons are labeled "
                    "retry on the primary booth action while still restarting "
                    "through the deterministic fresh lesson path"
                ),
                "chooser_disclosure_control": (
                    "the optional lesson chooser is a real disclosure control "
                    "with aria-controls and aria-expanded state, closes on "
                    "Escape or lesson pick, and restores focus when the user "
                    "dismisses it"
                ),
                "screen_fallback_action_label": (
                    "when a required control is not represented in the active "
                    "controller SVG, the one fallback screen-action button "
                    "keeps the deterministic ACK path and names the exact "
                    "fallback action in aria/title text"
                ),
                "adaptive_retry_primer": (
                    "unfinished lessons with persisted hint strikes keep the "
                    "booth one-action simple while surfacing a compact "
                    "hint-ready retry cue and moving exact hint counts into "
                    "aria/title text"
                ),
                "practice_source_memory": (
                    "MIDI/controller and on-screen deck actions are persisted "
                    "as backstage hardware/screen practice-source counts in "
                    "LearnProgress, giving future coaching/profile logic real "
                    "learner data without adding frontstage chrome"
                ),
                "commands": frontend_quality.get("commands"),
            },
            blockers=(
                list(frontend_quality.get("errors") or [])
                + (
                    ["learn_frontstage_simplicity_vitest did not run"]
                    if "learn_frontstage_simplicity_vitest"
                    not in _quality_command_names(frontend_quality)
                    else []
                )
            ),
            next_actions=[frontend_quality.get("operator_commands", {}).get("run")]
            if isinstance(frontend_quality.get("operator_commands"), dict)
            else [],
            category="practice_booth_ux",
        ),
        _completion_row(
            row_id="lesson_choice_replay_contract",
            requirement=(
                "The optional Learn lesson map proves opt-in lesson choice, "
                "locked-course handling, and completed-lesson replay without "
                "replacing the recommended path."
            ),
            passed=frontend_quality.get("passed") is True
            and "learn_choice_replay_vitest" in _quality_command_names(frontend_quality),
            evidence={
                "path": frontend_quality.get("path"),
                "required_command": "learn_choice_replay_vitest",
                "covered_tests": [
                    "tests/learn/test_progress_list.spec.ts",
                    "tests/learn/test_curriculum_meta.spec.ts",
                    "tests/learn/test_hud_progress_dots_keyboard.spec.ts",
                ],
                "hud_replay_affordance": (
                    "completed HUD progress dots announce press-to-replay, "
                    "current dots announce the current step, and pending dots "
                    "announce the prerequisite lock"
                ),
                "progress_list_affordance": (
                    "completed lesson-map rows announce press-to-replay, "
                    "in-progress rows announce retry, and locked rows keep "
                    "the exact lock reason in aria/title text"
                ),
                "commands": frontend_quality.get("commands"),
            },
            blockers=list(frontend_quality.get("errors") or []),
            next_actions=[frontend_quality.get("operator_commands", {}).get("run")]
            if isinstance(frontend_quality.get("operator_commands"), dict)
            else [],
            category="practice_booth_ux",
        ),
        _completion_row(
            row_id="browser_practice_booth_quality_contract",
            requirement=(
                "The browser-rendered Learn booth proves accessible, responsive, "
                "high-contrast practice UX and completes the recommended L1.01 "
                "path through both the Tauri-style forwarder and direct browser "
                "WebSocket fallback against the Python Learn harness."
            ),
            passed=frontend_quality.get("passed") is True
            and "learn_browser_booth_playwright" in _quality_command_names(frontend_quality),
            evidence={
                "path": frontend_quality.get("path"),
                "required_command": "learn_browser_booth_playwright",
                "covered_tests": [
                    "tauri/ui/tests/learn/browser-axe.pw.ts",
                    "tauri/ui/tests/learn/browser-responsive.pw.ts",
                    "tauri/ui/tests/learn/browser-contrast.pw.ts",
                    "tauri/ui/tests/learn/browser-python-beginner-path.pw.ts",
                ],
                "browser_claims": [
                    "no critical or serious WCAG axe violations",
                    "narrow first paint has no shell overflow and keeps booth controls visible",
                    "tutor dock and cue highlights clear computed contrast thresholds",
                    "recommended L1.01 completes through Tauri forwarder and direct WebSocket fallback",
                    "wrong on-screen EQ move reaches the Python sidecar, renders a grounded citation chip, and recovers to lesson completion",
                ],
                "commands": frontend_quality.get("commands"),
            },
            blockers=(
                list(frontend_quality.get("errors") or [])
                + (
                    ["learn_browser_booth_playwright did not run"]
                    if "learn_browser_booth_playwright"
                    not in _quality_command_names(frontend_quality)
                    else []
                )
            ),
            next_actions=[frontend_quality.get("operator_commands", {}).get("run")]
            if isinstance(frontend_quality.get("operator_commands"), dict)
            else [],
            category="practice_booth_ux",
        ),
        _completion_row(
            row_id="app_entry_contract",
            requirement=(
                "The main app shell exposes Learn as a normal user path: the "
                "mode picker opens the Learn window, the command palette can "
                "jump to Learn, and the first recommended action can start "
                "from that entry."
            ),
            passed=frontend_quality.get("passed") is True
            and "learn_app_entry_vitest" in _quality_command_names(frontend_quality),
            evidence={
                "path": frontend_quality.get("path"),
                "required_command": "learn_app_entry_vitest",
                "covered_tests": [
                    "tests/learn/test_beginner_path_contract.spec.ts",
                    "tests/session/render-loop-actions.spec.ts",
                    "tests/shell/shell.spec.ts",
                ],
                "commands": frontend_quality.get("commands"),
            },
            blockers=list(frontend_quality.get("errors") or []),
            next_actions=[frontend_quality.get("operator_commands", {}).get("run")]
            if isinstance(frontend_quality.get("operator_commands"), dict)
            else [],
            category="app_integration",
        ),
        _completion_row(
            row_id="tauri_learn_window_contract",
            requirement=(
                "The desktop app registers the Learn Tauri command, scopes the "
                "learn window in capabilities, uses the single lowercase "
                "`learn` window label, and loads the bundled `learn.html` "
                "surface without launching a second Python process."
            ),
            passed=(
                frontend_quality.get("passed") is True
                and desktop_quality.get("passed") is True
                and "learn_tauri_window_vitest" in _quality_command_names(frontend_quality)
                and "learn_cargo_learn_window_test" in _quality_command_names(desktop_quality)
            ),
            evidence={
                "frontend_path": frontend_quality.get("path"),
                "desktop_path": desktop_quality.get("path"),
                "required_frontend_command": "learn_tauri_window_vitest",
                "required_desktop_command": "learn_cargo_learn_window_test",
                "covered_tests": [
                    "tauri/ui/tests/learn/test_learn_window_label.spec.ts",
                    "tauri/src-tauri/src/learn_window.rs::tests",
                ],
                "window_label": "learn",
                "webview_url": "learn.html",
                "commands": {
                    "frontend": frontend_quality.get("commands"),
                    "desktop": desktop_quality.get("commands"),
                },
            },
            blockers=(
                list(frontend_quality.get("errors") or [])
                + list(desktop_quality.get("errors") or [])
                + (
                    ["learn_tauri_window_vitest did not run"]
                    if "learn_tauri_window_vitest"
                    not in _quality_command_names(frontend_quality)
                    else []
                )
                + (
                    ["learn_cargo_learn_window_test did not run"]
                    if "learn_cargo_learn_window_test"
                    not in _quality_command_names(desktop_quality)
                    else []
                )
            ),
            next_actions=[
                command
                for command in (
                    frontend_quality.get("operator_commands", {}).get("run")
                    if isinstance(frontend_quality.get("operator_commands"), dict)
                    else None,
                    desktop_quality.get("operator_commands", {}).get("run")
                    if isinstance(desktop_quality.get("operator_commands"), dict)
                    else None,
                )
                if isinstance(command, str)
            ],
            category="app_integration",
        ),
        _completion_row(
            row_id="desktop_shell_quality",
            requirement=(
                "The Learn desktop shell quality pass has run Rust formatting, "
                "Cargo check, and sidecar auto-master wiring tests for the "
                "Tauri app wrapper."
            ),
            passed=desktop_quality.get("passed") is True,
            evidence={
                "path": desktop_quality.get("path"),
                "required_commands": desktop_quality.get("required_commands"),
                "commands": desktop_quality.get("commands"),
            },
            blockers=list(desktop_quality.get("errors") or []),
            next_actions=[desktop_quality.get("operator_commands", {}).get("run")]
            if isinstance(desktop_quality.get("operator_commands"), dict)
            else [],
            category="app_integration",
        ),
        _completion_row(
            row_id="launched_tauri_practice_booth",
            requirement=(
                "The real Tauri Learn webview, Rust bridge, Python socket, and "
                "practice-booth quality checks pass together."
            ),
            passed=tauri_smoke.get("passed") is True,
            evidence={
                "path": tauri_smoke.get("path"),
                "completed_lesson_id": tauri_smoke.get("completed_lesson_id"),
                "quality_ok": tauri_smoke.get("quality_ok"),
                "quality_check_count": tauri_smoke.get("quality_check_count"),
            },
            blockers=list(tauri_smoke.get("errors") or []),
            next_actions=["npm --prefix tauri/ui run test:e2e:learn:tauri"],
            category="app_integration",
        ),
        _completion_row(
            row_id="on_screen_deck_path",
            requirement=(
                "A beginner can use the on-screen deck path and complete a Learn "
                "lesson through deterministic socket/progress evidence."
            ),
            passed=live["screen"].get("passed") is True,
            evidence={"status": live["screen"].get("status"), "path": live["screen"].get("path")},
            blockers=list(live["screen"].get("blockers") or []),
            next_actions=["uv run python scripts/run_learn_live_proof.py --start-app"],
            category="live_proof",
        ),
        _completion_row(
            row_id="physical_controller_path",
            requirement=(
                "A beginner can move a physical controller and complete a mapped "
                "Learn action through deterministic evidence."
            ),
            passed=live["physical"].get("passed") is True,
            evidence={
                "status": live["physical"].get("status"),
                "path": live["physical"].get("path"),
                "diagnosis": live["physical"].get("diagnosis"),
                "readiness_status": live["physical"].get("readiness_status"),
                "physical_connection_doctor": live["physical"].get(
                    "physical_connection_doctor"
                ),
                "operator_commands": live["physical"].get("operator_commands"),
            },
            blockers=list(live["physical"].get("blockers") or []),
            next_actions=[
                live["physical"].get("operator_commands", {}).get("proof")
            ],
            category="live_proof",
        ),
        _completion_row(
            row_id="course3_live_audio_play_mode",
            requirement=(
                "Course 3 live play mode proves routed master audio, citable deck "
                "context, and next-phrase count-in evidence."
            ),
            passed=live["course3"].get("passed") is True,
            evidence={
                "status": live["course3"].get("status"),
                "path": live["course3"].get("path"),
                "diagnosis": live["course3"].get("diagnosis"),
                "readiness_status": live["course3"].get("readiness_status"),
                "course3_route_doctor": live["course3"].get("course3_route_doctor"),
                "route_plan": live["course3"].get("route_plan"),
                "playback_nudge": live["course3"].get("playback_nudge"),
                "probe_operator_action": live["course3"].get("probe_operator_action"),
            },
            blockers=list(live["course3"].get("blockers") or []),
            next_actions=[
                live["course3"].get("operator_commands", {}).get("proof")
            ]
            if isinstance(live["course3"].get("operator_commands"), dict)
            else [],
            category="live_proof",
        ),
        _completion_row(
            row_id="packaged_eq_exemplar_ear_pass",
            requirement=(
                "The packaged EQ exemplar bank passes technical integrity and "
                "human ear-pass for the beginner teaching experience."
            ),
            passed=exemplars.get("release_ready") is True,
            evidence={
                "technical_passed": exemplars.get("technical_passed"),
                "release_ready": exemplars.get("release_ready"),
                "track_count": exemplars.get("track_count"),
                "bank_fingerprint": exemplars.get("bank_fingerprint"),
                "diagnosis": exemplars.get("diagnosis"),
                "operator_action": exemplars.get("operator_action"),
            },
            blockers=(
                list(exemplars.get("technical_failures") or [])
                if exemplars.get("technical_passed") is not True
                else ["packaged EQ exemplar human ear-pass is pending"]
                if exemplars.get("release_ready") is not True
                else []
            ),
            next_actions=[
                exemplars.get("operator_commands", {}).get("play"),
                exemplars.get("operator_commands", {}).get("approve"),
            ]
            if isinstance(exemplars.get("operator_commands"), dict)
            else [],
            category="human_ear_pass",
        ),
    ]
    release_rows = [row for row in rows if row["release_gate"]]
    proven_rows = [row for row in rows if row["status"] == "proven"]
    proven_release_rows = [row for row in release_rows if row["status"] == "proven"]
    return {
        "schema_version": 1,
        "summary": {
            "total": len(rows),
            "proven": len(proven_rows),
            "not_proven": len(rows) - len(proven_rows),
            "release_gate_total": len(release_rows),
            "release_gate_proven": len(proven_release_rows),
            "release_ready": len(proven_release_rows) == len(release_rows),
        },
        "requirements": rows,
    }


def verify_package(
    *,
    proof_dir: Path = DEFAULT_PROOF_DIR,
    frontend_path: Path | None = DEFAULT_FRONTEND,
    python_quality_path: Path | None = None,
    frontend_quality_path: Path | None = None,
    desktop_quality_path: Path | None = None,
    tauri_smoke_path: Path | None = None,
    live_proof_paths: list[Path] | None = None,
    exemplar_approval_path: Path | None = None,
    physical_readiness_path: Path | None = None,
    course3_readiness_path: Path | None = None,
) -> dict[str, Any]:
    if tauri_smoke_path is None:
        tauri_smoke_path = _discover_tauri_smoke(proof_dir)
    if python_quality_path is None:
        python_quality_path = _discover_python_quality(proof_dir)
    if frontend_quality_path is None:
        frontend_quality_path = _discover_frontend_quality(proof_dir)
    if desktop_quality_path is None:
        desktop_quality_path = _discover_desktop_quality(proof_dir)
    if live_proof_paths is None:
        live_proof_paths = _discover_live_proofs(proof_dir)
    if exemplar_approval_path is None:
        exemplar_approval_path = _discover_exemplar_approval(proof_dir)
    if physical_readiness_path is None:
        physical_readiness_path = _discover_physical_readiness(proof_dir)
    if course3_readiness_path is None:
        course3_readiness_path = _discover_course3_readiness(proof_dir)
    curriculum = _curriculum_status(frontend_path)
    exemplars = _exemplar_status(exemplar_approval_path)
    python_quality = _python_quality_status(python_quality_path)
    frontend_quality = _frontend_quality_status(frontend_quality_path)
    desktop_quality = _desktop_quality_status(desktop_quality_path)
    tauri_smoke = _tauri_smoke_status(tauri_smoke_path)
    physical_readiness = _physical_readiness_status(physical_readiness_path)
    course3_readiness = _course3_readiness_status(course3_readiness_path)
    live = {
        requirement: _live_requirement_status(live_proof_paths, requirement)
        for requirement in LIVE_REQUIREMENTS
    }
    live["physical"] = _merge_physical_readiness(live["physical"], physical_readiness)
    live["course3"] = _merge_course3_readiness(live["course3"], course3_readiness)
    live["physical"]["operator_commands"] = _physical_operator_commands(live["physical"])
    live["course3"]["operator_commands"] = _course3_operator_commands(live["course3"])
    deterministic_passed = (
        curriculum["passed"] is True
        and exemplars["technical_passed"] is True
        and python_quality["passed"] is True
        and frontend_quality["passed"] is True
        and desktop_quality["passed"] is True
        and tauri_smoke["passed"] is True
    )
    completion_blockers = _completion_blockers(
        curriculum=curriculum,
        exemplars=exemplars,
        python_quality=python_quality,
        frontend_quality=frontend_quality,
        desktop_quality=desktop_quality,
        tauri_smoke=tauri_smoke,
        live=live,
    )
    completion_matrix = _completion_matrix(
        curriculum=curriculum,
        exemplars=exemplars,
        python_quality=python_quality,
        frontend_quality=frontend_quality,
        desktop_quality=desktop_quality,
        tauri_smoke=tauri_smoke,
        live=live,
    )
    objective_audit = _objective_audit(completion_matrix)
    release_ready = not completion_blockers and completion_matrix["summary"]["release_ready"] is True
    release_blocker_recipe = _release_blocker_recipe(
        completion_blockers=completion_blockers,
        exemplars=exemplars,
        live=live,
    )
    non_external_status = _deferred_external_completion_status(
        deterministic_passed=deterministic_passed,
        completion_blockers=completion_blockers,
        release_blocker_recipe=release_blocker_recipe,
    )
    return {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).isoformat(),
        "passed": deterministic_passed,
        "technical_passed": deterministic_passed,
        "release_ready": release_ready,
        "non_external_ready": non_external_status["ready"],
        "deferred_external_blocker_ids": non_external_status[
            "deferred_external_blocker_ids"
        ],
        "internal_blocker_ids": non_external_status["internal_blocker_ids"],
        "deferred_external_blockers": non_external_status[
            "deferred_external_blockers"
        ],
        "internal_blockers": non_external_status["internal_blockers"],
        "non_external_ready_rule": non_external_status["rule"],
        "proof_dir": str(proof_dir),
        "sections": {
            "curriculum": curriculum,
            "exemplars": exemplars,
            "python_quality": python_quality,
            "frontend_quality": frontend_quality,
            "desktop_quality": desktop_quality,
            "launched_tauri_smoke": tauri_smoke,
            "live_proofs": live,
        },
        "completion_matrix": completion_matrix,
        "objective_audit": objective_audit,
        "completion_blockers": completion_blockers,
        "release_blocker_recipe": release_blocker_recipe,
        "next_actions": _next_actions(
            completion_blockers,
            physical_diagnosis=live["physical"].get("diagnosis"),
            physical_connection_doctor=live["physical"].get("physical_connection_doctor"),
            course3_diagnosis=live["course3"].get("diagnosis"),
            course3_route_plan=live["course3"].get("route_plan"),
            course3_route_doctor=live["course3"].get("course3_route_doctor"),
            course3_probe_operator_action=live["course3"].get("probe_operator_action"),
        ),
    }


def _release_blocker_recipe(
    *,
    completion_blockers: list[str],
    exemplars: dict[str, Any],
    live: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return a compact operator recipe for the current release blockers.

    ``next_actions`` is intentionally one-line and human skimmable. This recipe
    is the structured handoff for the next proof session: blocker id, current
    status/path, manual prompt, and the exact commands to run.
    """
    rows: list[dict[str, Any]] = []
    for blocker in completion_blockers:
        if "ear-pass" in blocker:
            commands = exemplars.get("operator_commands")
            commands = commands if isinstance(commands, dict) else {}
            operator_action = exemplars.get("operator_action")
            operator_action = operator_action if isinstance(operator_action, dict) else None
            rows.append(
                {
                    "id": "packaged_eq_exemplar_ear_pass",
                    "blocker": blocker,
                    "status": "pending_human_ear_pass"
                    if exemplars.get("technical_passed") is True
                    else "technical_audit_failed",
                    "manual_action": (
                        "Listen to every packaged EQ exemplar on a real output, "
                        "then approve the current fingerprint only if it teaches "
                        "the band clearly."
                    ),
                    "operator_action": operator_action,
                    "operator_steps": operator_action.get("steps")
                    if isinstance(operator_action, dict)
                    else None,
                    "commands": {
                        key: commands.get(key)
                        for key in ("list_output_devices", "play", "approve", "verify")
                        if commands.get(key)
                    },
                    "fingerprint": exemplars.get("bank_fingerprint"),
                    "diagnosis": exemplars.get("diagnosis"),
                }
            )
            continue
        if "physical controller" in blocker:
            physical = live.get("physical", {})
            commands = physical.get("operator_commands")
            commands = commands if isinstance(commands, dict) else {}
            operator_action = commands.get("operator_action")
            rows.append(
                {
                    "id": "physical_controller_path",
                    "blocker": blocker,
                    "status": physical.get("status"),
                    "path": physical.get("path"),
                    "manual_action": commands.get("manual_action"),
                    "operator_action": operator_action
                    if isinstance(operator_action, dict)
                    else None,
                    "operator_steps": operator_action.get("steps")
                    if isinstance(operator_action, dict)
                    else None,
                    "commands": {
                        key: commands.get(key)
                        for key in ("list_controller", "readiness", "proof", "verify")
                        if commands.get(key)
                    },
                    "diagnosis": physical.get("diagnosis"),
                    "readiness_status": physical.get("readiness_status"),
                    "physical_connection_doctor": physical.get(
                        "physical_connection_doctor"
                    ),
                }
            )
            continue
        if "Course 3" in blocker:
            course3 = live.get("course3", {})
            commands = course3.get("operator_commands")
            commands = commands if isinstance(commands, dict) else {}
            operator_action = commands.get("operator_action")
            rows.append(
                {
                    "id": "course3_live_audio_play_mode",
                    "blocker": blocker,
                    "status": course3.get("status"),
                    "path": course3.get("path"),
                    "manual_action": commands.get("manual_action"),
                    "operator_action": operator_action
                    if isinstance(operator_action, dict)
                    else None,
                    "operator_steps": operator_action.get("steps")
                    if isinstance(operator_action, dict)
                    else None,
                    "commands": {
                        key: commands.get(key)
                        for key in ("readiness", "proof", "verify")
                        if commands.get(key)
                    },
                    "current_selected_input": commands.get("current_selected_input"),
                    "current_fallback_candidate": commands.get(
                        "current_fallback_candidate"
                    ),
                    "diagnosis": course3.get("diagnosis"),
                    "readiness_status": course3.get("readiness_status"),
                    "course3_route_doctor": course3.get("course3_route_doctor"),
                    "route_plan": course3.get("route_plan"),
                    "playback_nudge": course3.get("playback_nudge"),
                    "probe_operator_action": course3.get("probe_operator_action"),
                }
            )
    return rows


def _deferred_external_completion_status(
    *,
    deterministic_passed: bool,
    completion_blockers: list[str],
    release_blocker_recipe: list[dict[str, Any]],
) -> dict[str, Any]:
    """Classify blockers the user explicitly deferred from blockers we still own."""
    deferred_external_blockers: list[dict[str, Any]] = []
    internal_blockers: list[dict[str, Any]] = []
    mapped_blockers: set[str] = set()
    for row in release_blocker_recipe:
        row_id = str(row.get("id") or "").strip()
        blocker = str(row.get("blocker") or "").strip()
        if blocker:
            mapped_blockers.add(blocker)
        compact = {
            "id": row_id or "unknown_release_blocker",
            "blocker": blocker or None,
            "status": row.get("status"),
        }
        if row_id in DEFERRED_EXTERNAL_RELEASE_BLOCKER_IDS:
            deferred_external_blockers.append(compact)
        else:
            internal_blockers.append(compact)

    for blocker in completion_blockers:
        if blocker in mapped_blockers:
            continue
        internal_blockers.append(
            {
                "id": "unclassified_completion_blocker",
                "blocker": blocker,
                "status": "unclassified",
            }
        )

    internal_blocker_ids = _dedupe(
        [
            str(row.get("id"))
            for row in internal_blockers
            if str(row.get("id") or "").strip()
        ]
    )
    deferred_external_blocker_ids = _dedupe(
        [
            str(row.get("id"))
            for row in deferred_external_blockers
            if str(row.get("id") or "").strip()
        ]
    )
    return {
        "ready": deterministic_passed and not internal_blockers,
        "deferred_external_blocker_ids": deferred_external_blocker_ids,
        "internal_blocker_ids": internal_blocker_ids,
        "deferred_external_blockers": deferred_external_blockers,
        "internal_blockers": internal_blockers,
        "rule": (
            "Non-external readiness ignores only the currently deferred human "
            "ear-pass and Course 3 routed-audio proof; every other blocker "
            "still keeps the package incomplete."
        ),
    }


def _physical_operator_commands(physical: dict[str, Any]) -> dict[str, Any]:
    """Return the exact operator recipe for discharging the physical Learn proof."""
    diagnosis = physical.get("diagnosis")
    connection_doctor = physical.get("physical_connection_doctor")
    connection_doctor = connection_doctor if isinstance(connection_doctor, dict) else None
    operator_action = (
        diagnosis.get("operator_action")
        if isinstance(diagnosis, dict) and isinstance(diagnosis.get("operator_action"), dict)
        else None
    )
    if operator_action is None and isinstance(connection_doctor, dict):
        steps = connection_doctor.get("operator_steps")
        operator_action = {
            "prompt": str(connection_doctor.get("next_step") or ""),
            "steps": [str(step) for step in steps if str(step).strip()]
            if isinstance(steps, list)
            else [],
        }
        if not operator_action["prompt"]:
            operator_action = None
    manual_action = (
        operator_action.get("prompt")
        if isinstance(operator_action, dict) and operator_action.get("prompt")
        else diagnosis.get("message")
        if isinstance(diagnosis, dict) and diagnosis.get("message")
        else (
            "Connect the DDJ, wait for DDJ-FLX4 to appear, then nudge the "
            "left jog wheel during L1.07."
        )
    )
    return {
        "manual_action": str(manual_action),
        "operator_action": operator_action,
        "physical_connection_doctor": connection_doctor,
        "list_controller": "uv run python scripts/sniff_controller.py --list",
        "readiness": (
            str(connection_doctor.get("readiness_command"))
            if isinstance(connection_doctor, dict)
            and connection_doctor.get("readiness_command")
            else (
                "uv run python scripts/learn_live_readiness.py --require physical "
                "--out /tmp/vibemix-live-learn-proof/learn-physical-readiness-current.json"
            )
        ),
        "proof": (
            str(connection_doctor.get("proof_command"))
            if isinstance(connection_doctor, dict)
            and connection_doctor.get("proof_command")
            else (
                "uv run python scripts/run_learn_live_proof.py --start-app --no-screen "
                "--physical --wait-physical-seconds 30 --physical-seconds 40 "
                "--say-physical-prompts --auto-master-input "
                "--out /tmp/vibemix-live-learn-proof/proof-physical-ddj-current.json"
            )
        ),
        "verify": (
            "uv run python scripts/verify_learn_package.py "
            "--out /tmp/vibemix-live-learn-proof/learn-package-verification-current.json"
        ),
    }


def _course3_operator_commands(course3: dict[str, Any]) -> dict[str, Any]:
    """Return the exact operator recipe for discharging Course 3 proof."""
    route_doctor = course3.get("course3_route_doctor")
    route_doctor = route_doctor if isinstance(route_doctor, dict) else None
    route_plan = course3.get("route_plan")
    selected_input = None
    fallback_candidate = None
    if isinstance(route_plan, dict):
        selected = route_plan.get("selected_input")
        if isinstance(selected, dict):
            selected_input = {
                "name": selected.get("name"),
                "sample_rate": selected.get("sample_rate"),
                "reason": selected.get("reason"),
                "live_signal": selected.get("live_signal"),
            }
        candidate = route_plan.get("auto_master_fallback_candidate")
        if isinstance(candidate, dict):
            fallback_candidate = {
                "name": candidate.get("name"),
                "sample_rate": candidate.get("sample_rate"),
                "reason": candidate.get("reason"),
                "source": candidate.get("source"),
                "live_signal": candidate.get("live_signal"),
            }
    auto_master_recommendation = (
        route_doctor.get("auto_master_recommendation")
        if isinstance(route_doctor, dict)
        and isinstance(route_doctor.get("auto_master_recommendation"), dict)
        else course3.get("auto_master_recommendation")
    )
    if fallback_candidate is None and isinstance(auto_master_recommendation, dict):
        fallback_candidate = {
            "name": auto_master_recommendation.get("device_name"),
            "sample_rate": auto_master_recommendation.get("sample_rate"),
            "reason": auto_master_recommendation.get("reason"),
            "source": auto_master_recommendation.get("source"),
            "live_signal": auto_master_recommendation.get("live_signal"),
        }
    diagnosis = course3.get("diagnosis")
    probe_operator_action = course3.get("probe_operator_action")
    probe_operator_action = (
        probe_operator_action if isinstance(probe_operator_action, dict) else None
    )
    doctor_next_step = (
        route_doctor.get("next_step")
        if isinstance(route_doctor, dict) and route_doctor.get("next_step")
        else None
    )
    if doctor_next_step:
        manual_action = doctor_next_step
    elif isinstance(probe_operator_action, dict) and probe_operator_action.get("prompt"):
        manual_action = probe_operator_action.get("prompt")
    elif isinstance(diagnosis, dict) and diagnosis.get("next_action"):
        manual_action = diagnosis.get("next_action")
    else:
        manual_action = "Start a real Rekordbox deck with channel and master faders up."
    operator_action = (
        diagnosis.get("operator_action")
        if isinstance(diagnosis, dict) and isinstance(diagnosis.get("operator_action"), dict)
        else None
    )
    if isinstance(route_doctor, dict) and isinstance(route_doctor.get("operator_steps"), list):
        doctor_steps = [
            str(step)
            for step in route_doctor["operator_steps"]
            if str(step).strip()
        ]
        operator_action = {
            "prompt": str(manual_action),
            "route": route_doctor.get("route"),
            "steps": doctor_steps,
        }
    if operator_action is None and probe_operator_action is not None:
        operator_action = probe_operator_action
    if operator_action is None:
        route_name = (
            selected_input.get("name")
            if isinstance(selected_input, dict) and selected_input.get("name")
            else fallback_candidate.get("name")
            if isinstance(fallback_candidate, dict) and fallback_candidate.get("name")
            else "a 48000Hz BlackHole or loopback input"
        )
        route_rate = (
            selected_input.get("sample_rate")
            if isinstance(selected_input, dict) and selected_input.get("sample_rate")
            else fallback_candidate.get("sample_rate")
            if isinstance(fallback_candidate, dict) and fallback_candidate.get("sample_rate")
            else None
        )
        route_label = f"{route_name} @ {route_rate}Hz" if route_rate else str(route_name)
        operator_action = {
            "prompt": str(manual_action),
            "route": route_label,
            "steps": [
                "Stop unrelated browser/system audio so deck attribution can point at Rekordbox.",
                f"Route Rekordbox master/output audio to {route_label}.",
                "Load and play a real Rekordbox library track.",
                "Raise the playing channel fader and master until loopback capture has signal.",
                "Rerun the Course 3 proof command; it will speak the route/playback moment.",
            ],
        }
    readiness_command = (
        str(route_doctor.get("readiness_command"))
        if isinstance(route_doctor, dict) and route_doctor.get("readiness_command")
        else (
            "uv run python scripts/learn_live_readiness.py --require course3 "
            "--live-context-seconds 5 --loopback-signal-seconds 2 "
            "--loopback-self-test-seconds 1 --capture-matrix-seconds 2 "
            "--out /tmp/vibemix-live-learn-proof/learn-course3-readiness-current.json"
        )
    )
    proof_command = (
        str(route_doctor.get("proof_command"))
        if isinstance(route_doctor, dict) and route_doctor.get("proof_command")
        else (
            "uv run python scripts/run_learn_live_proof.py --start-app --no-screen "
            "--course3 --seed-course3-unlocked --auto-master-input "
            "--nudge-rekordbox-playback --require-count-in "
            "--say-course3-prompts "
            "--wait-loopback-signal-seconds 30 --wait-capture-signal-seconds 30 "
            "--wait-course3-seconds 120 --course3-context-seconds 5 "
            "--loopback-signal-seconds 2 --loopback-self-test-seconds 1 "
            "--capture-matrix-seconds 2 "
            "--out /tmp/vibemix-live-learn-proof/proof-course3-auto-master-current.json"
        )
    )
    return {
        "manual_action": str(manual_action),
        "operator_action": operator_action,
        "current_selected_input": selected_input,
        "current_fallback_candidate": fallback_candidate,
        "readiness": readiness_command,
        "proof": proof_command,
        "verify": (
            "uv run python scripts/verify_learn_package.py "
            "--out /tmp/vibemix-live-learn-proof/learn-package-verification-current.json"
        ),
    }


def _next_actions(
    blockers: list[str],
    *,
    physical_diagnosis: dict[str, Any] | None = None,
    physical_connection_doctor: dict[str, Any] | None = None,
    course3_diagnosis: dict[str, Any] | None = None,
    course3_route_plan: dict[str, Any] | None = None,
    course3_route_doctor: dict[str, Any] | None = None,
    course3_probe_operator_action: dict[str, Any] | None = None,
) -> list[str]:
    actions: list[str] = []
    for blocker in blockers:
        if "ear-pass" in blocker:
            actions.append(
                "run scripts/audition_learn_exemplars.py --list-devices, "
                "then --play --device-index <output-device-index> --say-prompts "
                "--out /tmp/vibemix-live-learn-proof/learn-exemplar-audition-current.json, "
                "then --approve-ear-pass --approved-by <name> --audition "
                "/tmp/vibemix-live-learn-proof/learn-exemplar-audition-current.json"
            )
        elif "physical controller" in blocker:
            operator_action = (
                physical_diagnosis.get("operator_action")
                if isinstance(physical_diagnosis, dict)
                and isinstance(physical_diagnosis.get("operator_action"), dict)
                else None
            )
            prompt = (
                operator_action.get("prompt")
                if isinstance(operator_action, dict) and operator_action.get("prompt")
                else None
            )
            doctor_next_step = (
                physical_connection_doctor.get("next_step")
                if isinstance(physical_connection_doctor, dict)
                and physical_connection_doctor.get("next_step")
                else None
            )
            actions.append(
                str(prompt)
                if prompt
                else str(doctor_next_step)
                if doctor_next_step
                else (
                    "connect the DDJ and run scripts/run_learn_live_proof.py "
                    "with --physical --say-physical-prompts while moving the left jog wheel"
                )
            )
        elif "Course 3" in blocker:
            doctor_next_step = (
                course3_route_doctor.get("next_step")
                if isinstance(course3_route_doctor, dict)
                and course3_route_doctor.get("next_step")
                else None
            )
            rejected_reason = (
                course3_route_plan.get("auto_master_fallback_rejected_reason")
                if isinstance(course3_route_plan, dict)
                else None
            )
            next_action = (
                course3_diagnosis.get("next_action")
                if isinstance(course3_diagnosis, dict)
                else None
            )
            probe_prompt = (
                course3_probe_operator_action.get("prompt")
                if isinstance(course3_probe_operator_action, dict)
                and course3_probe_operator_action.get("prompt")
                else None
            )
            if rejected_reason:
                actions.append(str(rejected_reason))
            actions.append(
                str(doctor_next_step)
                if doctor_next_step
                else str(probe_prompt)
                if probe_prompt
                else str(next_action)
                if next_action
                else "route Rekordbox master into capture, then run the Course 3 live proof"
            )
        elif "Tauri" in blocker:
            actions.append("run npm --prefix tauri/ui run test:e2e:learn:tauri")
        elif "desktop shell quality" in blocker:
            actions.append(
                "run scripts/run_learn_desktop_quality.py, then refresh verify_learn_package.py"
            )
        elif "frontend quality" in blocker:
            actions.append(
                "run scripts/run_learn_frontend_quality.py, then refresh verify_learn_package.py"
            )
        elif "Python quality" in blocker:
            actions.append(
                "run scripts/run_learn_python_quality.py, then refresh verify_learn_package.py"
            )
        elif "curriculum" in blocker:
            actions.append("run scripts/audit_learn_curriculum.py and fix reported drift")
        elif "screen/on-deck" in blocker:
            actions.append("run scripts/run_learn_live_proof.py --start-app for screen proof")
    return _dedupe(actions)


def write_report(report: dict[str, Any], out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return out_path


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="verify_learn_package",
        description="Verify Learn package evidence and separate static pass from release readiness.",
    )
    parser.add_argument("--proof-dir", type=Path, default=DEFAULT_PROOF_DIR)
    parser.add_argument(
        "--frontend-path",
        type=Path,
        default=DEFAULT_FRONTEND,
        help="Generated frontend curriculum projection to verify.",
    )
    parser.add_argument(
        "--no-frontend-check",
        action="store_true",
        help="Skip the generated frontend curriculum projection check.",
    )
    parser.add_argument("--tauri-smoke", type=Path, default=None)
    parser.add_argument(
        "--python-quality",
        type=Path,
        default=None,
        help=(
            "Full Learn Python quality artifact "
            f"(default discovery: proof-dir/{PYTHON_QUALITY_NAME})."
        ),
    )
    parser.add_argument(
        "--frontend-quality",
        type=Path,
        default=None,
        help=(
            "Full Learn frontend quality artifact "
            f"(default discovery: proof-dir/{FRONTEND_QUALITY_NAME})."
        ),
    )
    parser.add_argument(
        "--desktop-quality",
        type=Path,
        default=None,
        help=(
            "Learn desktop-shell quality artifact "
            f"(default discovery: proof-dir/{DESKTOP_QUALITY_NAME})."
        ),
    )
    parser.add_argument(
        "--physical-readiness",
        type=Path,
        default=None,
        help=(
            "Fresh physical-controller readiness artifact used to enrich "
            "release-blocker guidance "
            f"(default discovery: proof-dir/{PHYSICAL_READINESS_NAME})."
        ),
    )
    parser.add_argument(
        "--course3-readiness",
        type=Path,
        default=None,
        help=(
            "Fresh Course 3 readiness artifact used to enrich release-blocker guidance "
            f"(default discovery: proof-dir/{COURSE3_READINESS_NAME})."
        ),
    )
    parser.add_argument(
        "--exemplar-approval",
        type=Path,
        default=None,
        help=(
            "Human ear-pass approval artifact for the current exemplar hashes "
            f"(default discovery: proof-dir/{EXEMPLAR_APPROVAL_NAME})."
        ),
    )
    parser.add_argument(
        "--live-proof",
        action="append",
        type=Path,
        default=[],
        help="Live proof artifact to inspect. Repeat for multiple.",
    )
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument(
        "--require-release-ready",
        action="store_true",
        help="Exit non-zero unless every completion blocker is cleared.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    report = verify_package(
        proof_dir=args.proof_dir,
        frontend_path=None if args.no_frontend_check else args.frontend_path,
        python_quality_path=args.python_quality,
        frontend_quality_path=args.frontend_quality,
        desktop_quality_path=args.desktop_quality,
        tauri_smoke_path=args.tauri_smoke,
        live_proof_paths=list(args.live_proof) if args.live_proof else None,
        exemplar_approval_path=args.exemplar_approval,
        physical_readiness_path=args.physical_readiness,
        course3_readiness_path=args.course3_readiness,
    )
    if args.out is not None:
        write_report(report, args.out)
    print(json.dumps(report, sort_keys=True))
    if args.require_release_ready:
        return 0 if report.get("release_ready") is True else 4
    return 0 if report.get("passed") is True else 4


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
