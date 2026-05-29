#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Run the full Learn frontend quality gate and persist a verifier artifact."""
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
DEFAULT_OUT = Path("/tmp/vibemix-live-learn-proof/learn-frontend-quality-current.json")


@dataclass(frozen=True)
class QualityCommand:
    name: str
    command: tuple[str, ...]
    timeout_s: float


QUALITY_COMMANDS: tuple[QualityCommand, ...] = (
    QualityCommand(
        name="learn_app_entry_vitest",
        command=(
            "npm",
            "--prefix",
            "tauri/ui",
            "test",
            "--",
            "tests/learn/test_beginner_path_contract.spec.ts",
            "tests/session/render-loop-actions.spec.ts",
            "tests/shell/shell.spec.ts",
        ),
        timeout_s=180.0,
    ),
    QualityCommand(
        name="learn_frontstage_simplicity_vitest",
        command=(
            "npm",
            "--prefix",
            "tauri/ui",
            "test",
            "--",
            "tests/learn/test_practice_booth_shell.spec.ts",
            "tests/learn/test_tutor_speak_sr_announcement.spec.ts",
        ),
        timeout_s=180.0,
    ),
    QualityCommand(
        name="learn_tauri_window_vitest",
        command=(
            "npm",
            "--prefix",
            "tauri/ui",
            "test",
            "--",
            "tests/learn/test_learn_window_label.spec.ts",
        ),
        timeout_s=180.0,
    ),
    QualityCommand(
        name="learn_choice_replay_vitest",
        command=(
            "npm",
            "--prefix",
            "tauri/ui",
            "test",
            "--",
            "tests/learn/test_progress_list.spec.ts",
            "tests/learn/test_curriculum_meta.spec.ts",
            "tests/learn/test_hud_progress_dots_keyboard.spec.ts",
        ),
        timeout_s=180.0,
    ),
    QualityCommand(
        name="learn_vitest",
        command=("npm", "--prefix", "tauri/ui", "test", "--", "tests/learn"),
        timeout_s=180.0,
    ),
    QualityCommand(
        name="learn_build",
        command=("npm", "--prefix", "tauri/ui", "run", "build"),
        timeout_s=180.0,
    ),
    QualityCommand(
        name="learn_browser_booth_playwright",
        command=(
            "npm",
            "--prefix",
            "tauri/ui",
            "run",
            "test:e2e:learn",
            "--",
            "tests/learn/browser-axe.pw.ts",
            "tests/learn/browser-responsive.pw.ts",
            "tests/learn/browser-contrast.pw.ts",
            "tests/learn/browser-python-beginner-path.pw.ts",
        ),
        timeout_s=240.0,
    ),
    QualityCommand(
        name="learn_e2e",
        command=("npm", "--prefix", "tauri/ui", "run", "test:e2e:learn"),
        timeout_s=240.0,
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
        prog="run_learn_frontend_quality",
        description=(
            "Run Learn app-entry, frontstage simplicity, Tauri window, "
            "choice/replay contracts, Vitest, production build, focused "
            "browser booth, and broad browser e2e quality gates."
        ),
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
