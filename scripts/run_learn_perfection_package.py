#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Refresh deterministic Learn quality artifacts and the package verifier."""
from __future__ import annotations

import argparse
import json
import subprocess
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROOF_DIR = Path("/tmp/vibemix-live-learn-proof")
DEFAULT_OUT = DEFAULT_PROOF_DIR / "learn-perfection-package-current.json"
DEFAULT_PYTHON_QUALITY = DEFAULT_PROOF_DIR / "learn-python-quality-current.json"
DEFAULT_FRONTEND_QUALITY = DEFAULT_PROOF_DIR / "learn-frontend-quality-current.json"
DEFAULT_DESKTOP_QUALITY = DEFAULT_PROOF_DIR / "learn-desktop-quality-current.json"
DEFAULT_VERIFICATION = DEFAULT_PROOF_DIR / "learn-package-verification-current.json"


@dataclass(frozen=True)
class PackageCommand:
    name: str
    command: tuple[str, ...]
    timeout_s: float


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _tail(value: str, *, limit: int = 6000) -> str:
    if len(value) <= limit:
        return value
    return value[-limit:]


def run_command(spec: PackageCommand) -> dict[str, Any]:
    started = time.monotonic()
    try:
        proc = subprocess.run(
            list(spec.command),
            cwd=_REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=spec.timeout_s,
            check=False,
        )
        duration_s = round(time.monotonic() - started, 3)
        return {
            "name": spec.name,
            "command": " ".join(spec.command),
            "returncode": proc.returncode,
            "duration_s": duration_s,
            "passed": proc.returncode == 0,
            "stdout_tail": _tail(proc.stdout),
            "stderr_tail": _tail(proc.stderr),
        }
    except subprocess.TimeoutExpired as exc:
        duration_s = round(time.monotonic() - started, 3)
        return {
            "name": spec.name,
            "command": " ".join(spec.command),
            "returncode": None,
            "duration_s": duration_s,
            "passed": False,
            "error": f"timed out after {spec.timeout_s:g}s",
            "stdout_tail": _tail((exc.stdout or "") if isinstance(exc.stdout, str) else ""),
            "stderr_tail": _tail((exc.stderr or "") if isinstance(exc.stderr, str) else ""),
        }


def build_commands(
    *,
    python_quality_path: Path,
    frontend_quality_path: Path,
    desktop_quality_path: Path,
    verification_path: Path,
) -> tuple[PackageCommand, ...]:
    return (
        PackageCommand(
            name="python_quality",
            command=(
                "uv",
                "run",
                "python",
                "scripts/run_learn_python_quality.py",
                "--out",
                str(python_quality_path),
            ),
            timeout_s=540.0,
        ),
        PackageCommand(
            name="frontend_quality",
            command=(
                "uv",
                "run",
                "python",
                "scripts/run_learn_frontend_quality.py",
                "--out",
                str(frontend_quality_path),
            ),
            timeout_s=720.0,
        ),
        PackageCommand(
            name="desktop_quality",
            command=(
                "uv",
                "run",
                "python",
                "scripts/run_learn_desktop_quality.py",
                "--out",
                str(desktop_quality_path),
            ),
            timeout_s=540.0,
        ),
        PackageCommand(
            name="package_verifier",
            command=(
                "uv",
                "run",
                "python",
                "scripts/verify_learn_package.py",
                "--python-quality",
                str(python_quality_path),
                "--frontend-quality",
                str(frontend_quality_path),
                "--desktop-quality",
                str(desktop_quality_path),
                "--out",
                str(verification_path),
            ),
            timeout_s=120.0,
        ),
    )


def read_json(path: Path) -> dict[str, Any] | None:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return raw if isinstance(raw, dict) else None


def _section(verification: dict[str, Any] | None, name: str) -> dict[str, Any]:
    sections = verification.get("sections") if isinstance(verification, dict) else None
    if not isinstance(sections, dict):
        return {}
    section = sections.get(name)
    return section if isinstance(section, dict) else {}


def _command_names(section: dict[str, Any]) -> list[str]:
    commands = section.get("commands")
    rows = commands if isinstance(commands, list) else []
    return [
        str(row.get("name"))
        for row in rows
        if isinstance(row, dict) and row.get("name") is not None
    ]


def _quality_contract_summary(verification: dict[str, Any] | None) -> dict[str, Any]:
    python_quality = _section(verification, "python_quality")
    frontend_quality = _section(verification, "frontend_quality")
    desktop_quality = _section(verification, "desktop_quality")
    python_command_names = _command_names(python_quality)
    frontend_command_names = _command_names(frontend_quality)
    desktop_command_names = _command_names(desktop_quality)
    return {
        "python_quality": {
            "path": python_quality.get("path"),
            "passed": python_quality.get("passed") is True,
            "required_commands": python_quality.get("required_commands"),
            "commands": python_command_names,
            "model_router_guard": "learn_model_router_guard" in python_command_names,
            "all_lessons_runtime": (
                "learn_all_lessons_runtime_pytest" in python_command_names
            ),
            "adaptive_coaching": (
                "learn_adaptive_coaching_pytest" in python_command_names
            ),
            "auto_master_finder": (
                "learn_auto_master_finder_pytest" in python_command_names
            ),
            "course3_mix_anchor": (
                "learn_course3_mix_anchor_pytest" in python_command_names
            ),
            "course_pack_preflight": "learn_course_pack_pytest" in python_command_names,
        },
        "frontend_quality": {
            "path": frontend_quality.get("path"),
            "passed": frontend_quality.get("passed") is True,
            "commands": frontend_command_names,
            "browser_booth_quality": (
                "learn_browser_booth_playwright" in frontend_command_names
            ),
            "tauri_window_contract": "learn_tauri_window_vitest" in frontend_command_names,
        },
        "desktop_quality": {
            "path": desktop_quality.get("path"),
            "passed": desktop_quality.get("passed") is True,
            "commands": desktop_command_names,
            "learn_window_test": "learn_cargo_learn_window_test" in desktop_command_names,
        },
    }


def _release_blocker_recipe(verification: dict[str, Any] | None) -> list[dict[str, Any]]:
    recipe = verification.get("release_blocker_recipe") if verification else None
    if not isinstance(recipe, list):
        return []
    return [row for row in recipe if isinstance(row, dict)]


def _release_blocker_recipe_ids(recipe: list[dict[str, Any]]) -> list[str]:
    return [
        str(row["id"])
        for row in recipe
        if isinstance(row.get("id"), str) and row["id"].strip()
    ]


def build_report(
    commands: list[dict[str, Any]],
    *,
    verification_path: Path,
) -> dict[str, Any]:
    verification = read_json(verification_path)
    verification_refreshed = any(
        command.get("name") == "package_verifier" and command.get("passed") is True
        for command in commands
    )
    release_blocker_recipe = _release_blocker_recipe(verification)
    return {
        "schema_version": 1,
        "generated_at": now_iso(),
        "repo_root": str(_REPO_ROOT),
        "passed": all(command.get("passed") is True for command in commands)
        and bool(verification and verification.get("passed") is True),
        "release_ready": bool(verification and verification.get("release_ready") is True),
        "non_external_ready": bool(
            verification and verification.get("non_external_ready") is True
        ),
        "deferred_external_blocker_ids": verification.get(
            "deferred_external_blocker_ids"
        )
        if verification
        else [],
        "internal_blocker_ids": verification.get("internal_blocker_ids")
        if verification
        else [],
        "verification_path": str(verification_path),
        "verification_refreshed": verification_refreshed,
        "verification_summary": {
            "passed": verification.get("passed") if verification else None,
            "technical_passed": verification.get("technical_passed") if verification else None,
            "release_ready": verification.get("release_ready") if verification else None,
            "non_external_ready": verification.get("non_external_ready")
            if verification
            else None,
            "deferred_external_blocker_ids": verification.get(
                "deferred_external_blocker_ids"
            )
            if verification
            else None,
            "internal_blocker_ids": verification.get("internal_blocker_ids")
            if verification
            else None,
            "completion_blockers": verification.get("completion_blockers") if verification else None,
            "completion_matrix": verification.get("completion_matrix", {}).get("summary")
            if verification
            else None,
            "objective_audit": verification.get("objective_audit", {}).get("summary")
            if verification
            else None,
        },
        "release_blocker_recipe": release_blocker_recipe,
        "release_blocker_recipe_ids": _release_blocker_recipe_ids(
            release_blocker_recipe
        ),
        "quality_contract": _quality_contract_summary(verification),
        "commands": commands,
    }


def write_report(report: dict[str, Any], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run_learn_perfection_package",
        description=(
            "Refresh Learn Python, frontend, desktop-shell quality, and the package "
            "verifier as one deterministic package pass."
        ),
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--python-quality-out", type=Path, default=DEFAULT_PYTHON_QUALITY)
    parser.add_argument("--frontend-quality-out", type=Path, default=DEFAULT_FRONTEND_QUALITY)
    parser.add_argument("--desktop-quality-out", type=Path, default=DEFAULT_DESKTOP_QUALITY)
    parser.add_argument("--verification-out", type=Path, default=DEFAULT_VERIFICATION)
    parser.add_argument(
        "--require-release-ready",
        action="store_true",
        help="Exit non-zero unless the refreshed package verifier is release-ready.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    commands: list[dict[str, Any]] = []
    for spec in build_commands(
        python_quality_path=args.python_quality_out,
        frontend_quality_path=args.frontend_quality_out,
        desktop_quality_path=args.desktop_quality_out,
        verification_path=args.verification_out,
    ):
        result = run_command(spec)
        commands.append(result)
        if result.get("passed") is not True:
            break
    report = build_report(commands, verification_path=args.verification_out)
    write_report(report, args.out)
    print(
        json.dumps(
            {
                "artifact": str(args.out),
                "passed": report["passed"],
                "release_ready": report["release_ready"],
                "non_external_ready": report["non_external_ready"],
                "verification_refreshed": report["verification_refreshed"],
                "verification": report["verification_summary"],
                "release_blocker_recipe_ids": report["release_blocker_recipe_ids"],
                "commands": [
                    {
                        "name": command["name"],
                        "passed": command["passed"],
                        "returncode": command["returncode"],
                        "duration_s": command["duration_s"],
                    }
                    for command in commands
                ],
            },
            sort_keys=True,
        )
    )
    if args.require_release_ready:
        return 0 if report["release_ready"] is True else 4
    return 0 if report["passed"] is True else 4


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
