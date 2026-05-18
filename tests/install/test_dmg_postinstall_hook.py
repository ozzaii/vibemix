"""Behavioral tests for installer/macos/firstrun_companion.sh.

Phase 49 Plan 04 — Mac first-launch companion fetch hook.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
FIRSTRUN = ROOT / "installer" / "macos" / "firstrun_companion.sh"


def test_firstrun_exists():
    assert FIRSTRUN.exists()
    assert os.access(FIRSTRUN, os.X_OK), "firstrun_companion.sh must be executable"


def test_check_syntax_flag_exits_zero():
    result = subprocess.run(
        ["bash", str(FIRSTRUN), "--check-syntax"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, f"--check-syntax should exit 0, got {result.returncode}\nstderr={result.stderr}"


def test_dry_run_with_companion_creates_sentinel(tmp_path: Path):
    """Dry-run touches sentinel, logs event, exits 0."""
    # Stage a minimal workspace
    wd = tmp_path / "wd"
    macos_dir = wd / "installer" / "macos"
    companion_dir = wd / "installer" / "companion"
    macos_dir.mkdir(parents=True)
    companion_dir.mkdir(parents=True)
    shutil.copy(FIRSTRUN, macos_dir / "firstrun_companion.sh")
    (macos_dir / "firstrun_companion.sh").chmod(0o755)
    # Stub fetch_drivers.sh so the dry-run path doesn't actually run it.
    (companion_dir / "fetch_drivers.sh").write_text("#!/bin/bash\nexit 0\n")
    (companion_dir / "fetch_drivers.sh").chmod(0o755)

    # Redirect HOME so the sentinel + log land in tmp
    fake_home = wd / "home"
    fake_home.mkdir()
    env = os.environ.copy()
    env["HOME"] = str(fake_home)

    result = subprocess.run(
        ["bash", str(macos_dir / "firstrun_companion.sh"), "--dry-run"],
        env=env, capture_output=True, text=True,
    )
    assert result.returncode == 0, f"dry-run failed: {result.stderr}"
    sentinel = fake_home / "Library" / "Application Support" / "vibemix" / "firstlaunch.done"
    assert sentinel.exists(), "sentinel must be touched on dry-run success"
    log = fake_home / "Library" / "Application Support" / "vibemix" / "install.log"
    assert log.exists()
    assert "firstrun" in log.read_text()


def test_sentinel_present_skips_fetch(tmp_path: Path):
    """If sentinel exists, the script no-ops + exits 0."""
    fake_home = tmp_path / "home"
    sentinel = fake_home / "Library" / "Application Support" / "vibemix" / "firstlaunch.done"
    sentinel.parent.mkdir(parents=True)
    sentinel.touch()
    env = os.environ.copy()
    env["HOME"] = str(fake_home)
    result = subprocess.run(
        ["bash", str(FIRSTRUN)],
        env=env, capture_output=True, text=True,
    )
    assert result.returncode == 0


def test_missing_companion_script_fails(tmp_path: Path):
    """If installer/companion/fetch_drivers.sh is absent, exit 1."""
    wd = tmp_path / "wd"
    macos_dir = wd / "installer" / "macos"
    macos_dir.mkdir(parents=True)
    shutil.copy(FIRSTRUN, macos_dir / "firstrun_companion.sh")
    (macos_dir / "firstrun_companion.sh").chmod(0o755)
    # NO companion dir — script must fail.
    fake_home = wd / "home"
    fake_home.mkdir()
    env = os.environ.copy()
    env["HOME"] = str(fake_home)
    result = subprocess.run(
        ["bash", str(macos_dir / "firstrun_companion.sh")],
        env=env, capture_output=True, text=True,
    )
    assert result.returncode == 1


def test_no_aiza_literal_in_source():
    """Pitfall-7 grep gate."""
    import re
    src = FIRSTRUN.read_text()
    aiza_key = re.compile(r"AIza[0-9A-Za-z_-]{20,}")
    assert not aiza_key.findall(src), "AIza key literal in firstrun_companion.sh"
