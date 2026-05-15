# SPDX-License-Identifier: Apache-2.0
"""Phase 35 Plan 35-01 — Tests for scripts/glb_optimize.py.

Pitfall P52: 25 MB total + 600 KB per-clip cap.

Synthetic GLB fixtures only — these tests never touch real animation
files; they generate sized blobs that the script's byte-counter has no
way to distinguish from real GLBs (it doesn't parse the container).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "glb_optimize.py"


def _write_glb(path: Path, size_bytes: int) -> None:
    """Write a sized blob with .glb extension. Content is opaque to the
    script (it byte-counts; it doesn't parse)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\x00" * size_bytes)


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_check_passes_under_budget(tmp_path: Path) -> None:
    _write_glb(tmp_path / "clip_a.glb", 500 * 1024)
    _write_glb(tmp_path / "clip_b.glb", 400 * 1024)
    result = _run("--check", str(tmp_path))
    assert result.returncode == 0, (
        f"stdout={result.stdout!r}\nstderr={result.stderr!r}"
    )
    assert "OK" in result.stdout


def test_check_fails_per_clip_over_600kb(tmp_path: Path) -> None:
    """Per-clip cap fires only for files under an 'animations' dir."""
    anim_dir = tmp_path / "animations"
    _write_glb(anim_dir / "fatso.glb", 700 * 1024)
    _write_glb(anim_dir / "ok.glb", 100 * 1024)
    result = _run("--check", str(tmp_path))
    assert result.returncode == 1
    assert "fatso.glb" in result.stderr
    assert "600 KB" in result.stderr.replace(".0 KB", " KB")


def test_check_excludes_character_mesh_from_per_clip_cap(tmp_path: Path) -> None:
    """character.glb at the root is the rig (~20 MB) and is excluded
    from the 600 KB per-clip cap — it still counts toward the 25 MB total."""
    # Character mesh at the root, well above per-clip cap. Should NOT fail.
    _write_glb(tmp_path / "character.glb", 2 * 1024 * 1024)
    # Animation clip, under per-clip cap. Should pass.
    _write_glb(tmp_path / "animations" / "wave.glb", 100 * 1024)
    result = _run("--check", str(tmp_path))
    assert result.returncode == 0, (
        f"character mesh wrongly counted as animation clip.\n"
        f"stdout={result.stdout}\nstderr={result.stderr}"
    )


def test_check_fails_total_over_25mb(tmp_path: Path) -> None:
    # 60 clips × 500 KB = 30 MB. Each clip under per-clip cap; total over.
    for i in range(60):
        _write_glb(tmp_path / f"clip_{i:02d}.glb", 500 * 1024)
    result = _run("--check", str(tmp_path))
    assert result.returncode == 1
    assert "total" in result.stderr.lower()
    assert "25" in result.stderr  # 25 MB cap appears in message


def test_check_empty_dir_passes(tmp_path: Path) -> None:
    result = _run("--check", str(tmp_path))
    assert result.returncode == 0
    assert "no .glb files" in result.stdout


def test_check_nonexistent_dir_passes_with_note(tmp_path: Path) -> None:
    """Phase 35 intent: missing dir = no GLBs to check = OK. Matches the
    shell-script's permissive behavior so phases that add new asset dirs
    don't break CI on first run."""
    missing = tmp_path / "does_not_exist"
    result = _run("--check", str(missing))
    assert result.returncode == 0


def test_optimize_mode_missing_gltfpack_exits_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When gltfpack is not on PATH, --optimize must exit 2 with a hint."""
    input_dir = tmp_path / "in"
    output_dir = tmp_path / "out"
    _write_glb(input_dir / "x.glb", 100 * 1024)
    # Empty PATH guarantees gltfpack lookup fails.
    env = os.environ.copy()
    env["PATH"] = ""
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--optimize", str(input_dir), str(output_dir)],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert result.returncode == 2
    assert "gltfpack" in result.stderr
    assert "npm install" in result.stderr or "github.com" in result.stderr


def test_repo_mascot_dir_passes_current_budget() -> None:
    """The current mascot asset dir must pass per-clip + total checks."""
    mascot_dir = REPO_ROOT / "tauri" / "ui" / "assets" / "mascot"
    result = _run("--check", str(mascot_dir))
    assert result.returncode == 0, (
        f"current mascot GLBs exceed Phase 35 budget — investigate "
        f"before adding more.\nstdout={result.stdout!r}\nstderr={result.stderr!r}"
    )
