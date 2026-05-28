# SPDX-License-Identifier: Apache-2.0
"""Phase 93 Plan 06 — ``vibemix learn exemplar <band>`` CLI dispatch (RED-state stub).

Three subprocess tests pin the CLI contract from 93-RESEARCH.md §Pattern 12:

    1. Unknown band → exit 2 + stderr contains "unknown band".
    2. Valid band → exit 0 (real or fallback pick) OR exit 1 (no pick + no bank);
       stdout includes "track:" / "path:" / "score:" / "why:" line block on 0.
    3. Bogus subcommand → stderr surfaces "available: reset, exemplar <sub|low|mid|high>".

CLI dispatch is wired into ``src/vibemix/__main__.py`` lines 3316-3330 — the
extension of the existing P92-04 ``learn reset`` block.

REQ-ID: cross-cutting (CLI test surface for Kaan dev-loop validation).
Downstream plan that flips this skip: **Plan 93-06**.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def _is_cli_wired() -> bool:
    """Probe whether the ``learn exemplar`` CLI branch exists in __main__.py.

    The CLI subcommand lands in Plan 93-06 (extension of the P92-04
    ``learn reset`` dispatch block). Until then the subprocess tests below
    would fail with the existing fallback message (``available: reset``),
    NOT the new message (``available: reset, exemplar ...``).
    """
    main_py = _PROJECT_ROOT / "src" / "vibemix" / "__main__.py"
    if not main_py.exists():
        return False
    return "learn exemplar" in main_py.read_text(encoding="utf-8")


if not _is_cli_wired():
    pytest.skip(
        "tests/learn/test_cli_learn_exemplar.py awaiting Plan 93-06 — "
        "vibemix learn exemplar CLI dispatch in src/vibemix/__main__.py.",
        allow_module_level=True,
    )


@pytest.mark.cli
def test_learn_exemplar_unknown_band_exits_2(tmp_path: Path) -> None:
    """``vibemix learn exemplar ultrasonic`` exits 2 + stderr surfaces
    the "unknown band" message — argparse-style error contract."""
    proc = subprocess.run(
        [sys.executable, "-m", "vibemix", "learn", "exemplar", "ultrasonic"],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
        cwd=str(_PROJECT_ROOT),
        env={"PYTHONPATH": str(_PROJECT_ROOT / "src"), "HOME": str(tmp_path)},
    )
    assert proc.returncode == 2, (
        f"unknown band must exit 2 (argparse-style); got {proc.returncode}\n"
        f"stdout={proc.stdout!r} stderr={proc.stderr!r}"
    )
    assert "unknown band" in proc.stderr, (
        f"stderr must surface 'unknown band'; got {proc.stderr!r}"
    )


@pytest.mark.cli
def test_learn_exemplar_low_returns_zero_or_one(tmp_path: Path) -> None:
    """``vibemix learn exemplar low`` exits 0 (real or fallback pick) OR 1
    (no library + no bank). On 0 the stdout carries the 4-line block:
    ``track:`` / ``path:`` / ``score:`` / ``why:``.
    """
    proc = subprocess.run(
        [sys.executable, "-m", "vibemix", "learn", "exemplar", "low"],
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
        cwd=str(_PROJECT_ROOT),
        env={"PYTHONPATH": str(_PROJECT_ROOT / "src"), "HOME": str(tmp_path)},
    )
    assert proc.returncode in (0, 1), (
        f"learn exemplar low must exit 0 (pick) or 1 (no pick + no bank); "
        f"got {proc.returncode}\nstdout={proc.stdout!r} stderr={proc.stderr!r}"
    )
    if proc.returncode == 0:
        for line_prefix in ("track:", "path:", "score:", "why:"):
            assert line_prefix in proc.stdout, (
                f"successful pick must surface '{line_prefix}' line; "
                f"stdout={proc.stdout!r}"
            )


@pytest.mark.cli
def test_learn_help_advertises_exemplar_subcommand(tmp_path: Path) -> None:
    """``vibemix learn bogus`` exits 2 with the usage line that names BOTH
    ``reset`` and ``exemplar`` subcommands — the help-on-bad-subcommand
    discovery surface per 93-RESEARCH.md §Pattern 12.
    """
    proc = subprocess.run(
        [sys.executable, "-m", "vibemix", "learn", "bogus"],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
        cwd=str(_PROJECT_ROOT),
        env={"PYTHONPATH": str(_PROJECT_ROOT / "src"), "HOME": str(tmp_path)},
    )
    assert proc.returncode == 2, (
        f"unknown subcommand must exit 2; got {proc.returncode}\n"
        f"stderr={proc.stderr!r}"
    )
    assert "exemplar" in proc.stderr and "reset" in proc.stderr, (
        f"unknown-subcommand stderr must advertise BOTH reset and exemplar; "
        f"stderr={proc.stderr!r}"
    )
