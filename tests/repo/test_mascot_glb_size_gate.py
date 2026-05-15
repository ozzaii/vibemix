# SPDX-License-Identifier: Apache-2.0
"""Phase 31 Plan 07 — Mascot GLB total size CI gate.

Pitfall P52 — total mascot GLB size must stay <= 25 MB. Test wraps the
shell script so the same invariant holds in both pytest and CI shell.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CAP_BYTES = 25 * 1024 * 1024  # 25 MB

GLB_ROOTS = [
    REPO_ROOT / "tauri" / "ui" / "assets" / "mascot",
    REPO_ROOT / "tauri" / "ui" / "public" / "mascot",
]


def _total_glb_bytes() -> int:
    total = 0
    for root in GLB_ROOTS:
        if not root.is_dir():
            continue
        for path in root.rglob("*.glb"):
            total += path.stat().st_size
    return total


def test_mascot_glb_total_under_cap() -> None:
    """Sum every .glb under the mascot asset roots; assert <= 25 MB."""
    total = _total_glb_bytes()
    total_mb = total / 1024 / 1024
    cap_mb = CAP_BYTES / 1024 / 1024
    assert total <= CAP_BYTES, (
        f"Mascot GLB total {total_mb:.2f} MB exceeds cap {cap_mb:.2f} MB "
        f"(Pitfall P52). Reduce GLB count or compress with gltf-transform."
    )


def test_shell_gate_script_exits_clean() -> None:
    """The check_mascot_glb_size.sh script must exit 0 against current state."""
    script = REPO_ROOT / "scripts" / "check_mascot_glb_size.sh"
    assert script.is_file(), f"missing {script}"
    assert os.access(script, os.X_OK), f"{script} not executable"
    result = subprocess.run(
        [str(script)],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        check=False,
    )
    assert result.returncode == 0, (
        f"check_mascot_glb_size.sh failed (exit={result.returncode}):\n"
        f"stdout={result.stdout}\nstderr={result.stderr}"
    )
