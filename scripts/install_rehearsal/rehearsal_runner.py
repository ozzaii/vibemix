#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Phase 33 / Plan 33-08 — install rehearsal orchestrator.

Drives the fresh-VM matrix (macOS 12.3 / 14 / 15 + Windows 10 / 11)
through install + first-launch + ≤60s onboarding timing.

HARD GUARDS:

  - Default is ``--dry-run``. Without ``--real`` the orchestrator
    prints the planned VM operations but never invokes tart or
    VBoxManage. CI calls in dry-run mode only.
  - ``--real`` ALSO requires INSTALL_REHEARSAL_REAL=1 in the
    environment (matches the shell + PowerShell guards). This double-
    gate exists so a stray ``--real`` flag in a Kaan-experimentation
    branch can't trigger a multi-GB VM spin-up.

Real VM execution stays Kaan-action — see KAAN-ACTION-LEGAL.md
INSTALL-VM-RUN.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import Sequence


REPO_ROOT = Path(__file__).resolve().parents[2]
MAC_MATRIX = ("macos-12.3", "macos-14", "macos-15")
WIN_MATRIX = ("windows-10", "windows-11")


def build_plan(matrix: str) -> list[str]:
    plan: list[str] = []
    if matrix in ("mac", "all"):
        plan.append(f"mac_vm_setup.sh -> {', '.join(MAC_MATRIX)}")
    if matrix in ("win", "all"):
        plan.append(f"win_vm_setup.ps1 -> {', '.join(WIN_MATRIX)}")
    return plan


def _invoke_tart(_args: Sequence[str]) -> int:
    """Real-run hook. Autonomous agents NEVER reach this branch — the
    --real flag + INSTALL_REHEARSAL_REAL=1 env double-gate keeps it
    Kaan-only."""
    raise NotImplementedError(
        "rehearsal_runner real-run path is Kaan-action — see "
        "KAAN-ACTION-LEGAL.md INSTALL-VM-RUN."
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="rehearsal_runner",
        description="vibemix install rehearsal orchestrator (Phase 33).",
    )
    parser.add_argument(
        "--matrix",
        choices=("mac", "win", "all"),
        default="all",
        help="Which OS matrix to run. Default: all.",
    )
    parser.add_argument(
        "--real",
        action="store_true",
        help="Actually run VMs. Requires INSTALL_REHEARSAL_REAL=1 in env.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="(default) Print plan; never invoke tart / VBoxManage.",
    )
    args = parser.parse_args(argv)

    plan = build_plan(args.matrix)
    print("[rehearsal_runner] plan:")
    for line in plan:
        print(f"  - {line}")

    if not args.real:
        print("[rehearsal_runner] dry-run — exit 0.")
        return 0

    # --real path: require env-var double-gate.
    if os.environ.get("INSTALL_REHEARSAL_REAL") != "1":
        print(
            "[rehearsal_runner] --real passed but INSTALL_REHEARSAL_REAL != 1 — refusing.",
            file=sys.stderr,
        )
        print(
            "[rehearsal_runner] See KAAN-ACTION-LEGAL.md INSTALL-VM-RUN.",
            file=sys.stderr,
        )
        return 2

    # Autonomous agents must never reach the body below — gated by env.
    return _invoke_tart(plan)


if __name__ == "__main__":
    raise SystemExit(main())
