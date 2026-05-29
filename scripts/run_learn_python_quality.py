#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Run the full Learn Python quality gate and persist a verifier artifact."""
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
DEFAULT_OUT = Path("/tmp/vibemix-live-learn-proof/learn-python-quality-current.json")


@dataclass(frozen=True)
class QualityCommand:
    name: str
    command: tuple[str, ...]
    timeout_s: float


QUALITY_COMMANDS: tuple[QualityCommand, ...] = (
    QualityCommand(
        name="learn_ruff",
        command=(
            "uv",
            "run",
            "ruff",
            "check",
            "src/vibemix/learn",
            "scripts/audit_learn_curriculum.py",
            "scripts/audition_learn_exemplars.py",
            "scripts/export_learn_curriculum_meta.py",
            "scripts/learn_live_readiness.py",
            "scripts/run_learn_desktop_quality.py",
            "scripts/run_learn_frontend_quality.py",
            "scripts/run_learn_live_proof.py",
            "scripts/run_learn_perfection_package.py",
            "scripts/run_learn_python_quality.py",
            "scripts/validate_learn_course_pack.py",
            "scripts/validate_learn_live_proof.py",
            "scripts/verify_learn_package.py",
            "tests/learn",
            "src/vibemix/state/refresh.py",
            "tests/state/test_refresh.py",
        ),
        timeout_s=180.0,
    ),
    QualityCommand(
        name="learn_codegen_check",
        command=("uv", "run", "python", "scripts/export_learn_curriculum_meta.py", "--check"),
        timeout_s=120.0,
    ),
    QualityCommand(
        name="learn_model_router_guard",
        command=("bash", "scripts/release/check_no_hardcoded_model.sh"),
        timeout_s=120.0,
    ),
    QualityCommand(
        name="learn_all_lessons_runtime_pytest",
        command=("uv", "run", "pytest", "-q", "tests/learn/test_all_lessons_runtime_path.py"),
        timeout_s=120.0,
    ),
    QualityCommand(
        name="learn_teaching_loop_pytest",
        command=("uv", "run", "pytest", "-q", "tests/learn/test_teaching_loop.py"),
        timeout_s=120.0,
    ),
    QualityCommand(
        name="learn_adaptive_coaching_pytest",
        command=(
            "uv",
            "run",
            "pytest",
            "-q",
            "tests/learn/test_adaptive_coaching_runtime_contract.py",
        ),
        timeout_s=120.0,
    ),
    QualityCommand(
        name="learn_auto_master_finder_pytest",
        command=(
            "uv",
            "run",
            "pytest",
            "-q",
            "tests/learn/test_auto_master_finder_contract.py",
        ),
        timeout_s=120.0,
    ),
    QualityCommand(
        name="learn_course3_mix_anchor_pytest",
        command=(
            "uv",
            "run",
            "pytest",
            "-q",
            "tests/state/test_refresh.py::test_tick_course3_live_uses_dj_cue_sections_for_phrase_anchor",
            "tests/state/test_refresh.py::test_tick_course3_mix_uses_unambiguous_title_match_for_phrase_anchor",
            "tests/state/test_refresh.py::test_tick_course3_mix_refuses_ambiguous_title_match_for_phrase_anchor",
        ),
        timeout_s=120.0,
    ),
    QualityCommand(
        name="learn_course_pack_pytest",
        command=("uv", "run", "pytest", "-q", "tests/learn/test_course_pack.py"),
        timeout_s=120.0,
    ),
    QualityCommand(
        name="learn_pytest",
        command=("uv", "run", "pytest", "-q", "tests/learn"),
        timeout_s=360.0,
    ),
)


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _tail(value: str, *, limit: int = 6000) -> str:
    if len(value) <= limit:
        return value
    return value[-limit:]


def run_command(spec: QualityCommand) -> dict[str, Any]:
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


def build_report(commands: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "generated_at": now_iso(),
        "repo_root": str(_REPO_ROOT),
        "passed": all(command.get("passed") is True for command in commands),
        "commands": commands,
    }


def write_report(report: dict[str, Any], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run_learn_python_quality",
        description="Run Learn Ruff, curriculum codegen, and Python test quality gates.",
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    commands = [run_command(spec) for spec in QUALITY_COMMANDS]
    report = build_report(commands)
    write_report(report, args.out)
    print(
        json.dumps(
            {
                "artifact": str(args.out),
                "passed": report["passed"],
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
    return 0 if report["passed"] is True else 4


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
