#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Run the Learn desktop-shell quality gate and persist a verifier artifact."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = Path("/tmp/vibemix-live-learn-proof/learn-desktop-quality-current.json")
_TAURI_UI_DIST = _REPO_ROOT / "tauri" / "ui" / "dist"


@dataclass(frozen=True)
class QualityCommand:
    name: str
    command: tuple[str, ...]
    timeout_s: float


QUALITY_COMMANDS: tuple[QualityCommand, ...] = (
    QualityCommand(
        name="learn_tauri_frontend_dist_build",
        command=("npm", "--prefix", "tauri/ui", "run", "build"),
        timeout_s=180.0,
    ),
    QualityCommand(
        name="learn_cargo_fmt",
        command=(
            "cargo",
            "fmt",
            "--manifest-path",
            "tauri/src-tauri/Cargo.toml",
            "--all",
            "--",
            "--check",
        ),
        timeout_s=120.0,
    ),
    QualityCommand(
        name="learn_cargo_check",
        command=("cargo", "check", "--manifest-path", "tauri/src-tauri/Cargo.toml"),
        timeout_s=360.0,
    ),
    QualityCommand(
        name="learn_cargo_learn_window_test",
        command=(
            "cargo",
            "test",
            "--manifest-path",
            "tauri/src-tauri/Cargo.toml",
            "learn_window",
        ),
        timeout_s=360.0,
    ),
    QualityCommand(
        name="learn_cargo_sidecar_audio_test",
        command=(
            "cargo",
            "test",
            "--manifest-path",
            "tauri/src-tauri/Cargo.toml",
            "sidecar_audio_env_defaults",
        ),
        timeout_s=360.0,
    ),
)


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _tail(value: str, *, limit: int = 6000) -> str:
    if len(value) <= limit:
        return value
    return value[-limit:]


def _is_vite_dist_cleanup_flake(result: subprocess.CompletedProcess[str]) -> bool:
    return (
        result.returncode != 0
        and "ENOTEMPTY" in (result.stderr or "")
        and "tauri/ui/dist" in (result.stderr or "")
    )


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
        retried_after_dist_cleanup = False
        if (
            spec.name == "learn_tauri_frontend_dist_build"
            and _is_vite_dist_cleanup_flake(proc)
        ):
            shutil.rmtree(_TAURI_UI_DIST, ignore_errors=True)
            proc = subprocess.run(
                list(spec.command),
                cwd=_REPO_ROOT,
                capture_output=True,
                text=True,
                timeout=spec.timeout_s,
                check=False,
            )
            retried_after_dist_cleanup = True
        duration_s = round(time.monotonic() - started, 3)
        return {
            "name": spec.name,
            "command": " ".join(spec.command),
            "returncode": proc.returncode,
            "duration_s": duration_s,
            "passed": proc.returncode == 0,
            "retried_after_dist_cleanup": retried_after_dist_cleanup,
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
        prog="run_learn_desktop_quality",
        description=(
            "Build the Tauri frontend dist, then run Learn desktop-shell Rust "
            "format, Cargo check, Learn-window, and sidecar auto-master wiring "
            "quality gates."
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
