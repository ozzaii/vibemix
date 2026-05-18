"""Behavioral tests for installer/companion/uninstall.sh preserve-default.

Phase 49 Plan 06 — INSTALL-07 (uninstall preserves user library unless --clean).
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
UNINSTALL_SH = ROOT / "installer" / "companion" / "uninstall.sh"


def _setup_fixture(tmp_path: Path) -> Path:
    """Create a fake data root with recordings + debriefs + ghost_calibration."""
    data_root = tmp_path / "vibemix-data"
    (data_root / "recordings").mkdir(parents=True)
    (data_root / "recordings" / "20260518-123456.wav").write_text("fake-wav")
    (data_root / "debriefs").mkdir()
    (data_root / "debriefs" / "session_1.json").write_text("{}")
    (data_root / "ghost_calibration.json").write_text("{}")
    return data_root


def test_uninstall_sh_exists():
    assert UNINSTALL_SH.exists()
    assert os.access(UNINSTALL_SH, os.X_OK)


def test_check_syntax_flag_exits_zero():
    result = subprocess.run(
        ["bash", str(UNINSTALL_SH), "--check-syntax"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0


def test_default_uninstall_preserves_recordings(tmp_path: Path):
    data_root = _setup_fixture(tmp_path)
    cache_root = tmp_path / "cache"
    cache_root.mkdir()
    (cache_root / "x.cache").write_text("cache")

    env = os.environ.copy()
    env.update({
        "VIBEMIX_DATA_ROOT": str(data_root),
        "VIBEMIX_CACHE_ROOT": str(cache_root),
        "VIBEMIX_APP_PATH": str(tmp_path / "fake-vibemix.app"),
    })
    result = subprocess.run(
        ["bash", str(UNINSTALL_SH)],
        env=env, capture_output=True, text=True,
    )
    assert result.returncode == 0, f"uninstall failed: {result.stderr}"

    # Preserved
    assert (data_root / "recordings").exists()
    assert (data_root / "recordings" / "20260518-123456.wav").exists()
    assert (data_root / "debriefs").exists()
    assert (data_root / "ghost_calibration.json").exists()

    # Removed
    assert not cache_root.exists()

    # Log written
    assert (data_root / "uninstall.log").exists()


def test_clean_flag_removes_recordings(tmp_path: Path):
    data_root = _setup_fixture(tmp_path)
    cache_root = tmp_path / "cache"
    cache_root.mkdir()

    env = os.environ.copy()
    env.update({
        "VIBEMIX_DATA_ROOT": str(data_root),
        "VIBEMIX_CACHE_ROOT": str(cache_root),
        "VIBEMIX_APP_PATH": str(tmp_path / "fake-vibemix.app"),
    })
    result = subprocess.run(
        ["bash", str(UNINSTALL_SH), "--clean"],
        env=env, capture_output=True, text=True,
    )
    assert result.returncode == 0

    # Removed (clean mode)
    assert not (data_root / "recordings").exists()
    assert not (data_root / "debriefs").exists()
    assert not (data_root / "ghost_calibration.json").exists()


def test_uninstall_log_jsonl_format(tmp_path: Path):
    data_root = _setup_fixture(tmp_path)
    cache_root = tmp_path / "cache"
    cache_root.mkdir()

    env = os.environ.copy()
    env.update({
        "VIBEMIX_DATA_ROOT": str(data_root),
        "VIBEMIX_CACHE_ROOT": str(cache_root),
        "VIBEMIX_APP_PATH": str(tmp_path / "fake-vibemix.app"),
    })
    subprocess.run(["bash", str(UNINSTALL_SH)], env=env, capture_output=True, text=True)

    log_lines = (data_root / "uninstall.log").read_text().strip().splitlines()
    assert len(log_lines) >= 3
    for line in log_lines:
        record = json.loads(line)
        assert "ts" in record
        assert "action" in record


def test_dry_run_does_not_remove(tmp_path: Path):
    data_root = _setup_fixture(tmp_path)
    cache_root = tmp_path / "cache"
    cache_root.mkdir()
    (cache_root / "x.cache").write_text("cache")

    env = os.environ.copy()
    env.update({
        "VIBEMIX_DATA_ROOT": str(data_root),
        "VIBEMIX_CACHE_ROOT": str(cache_root),
        "VIBEMIX_APP_PATH": str(tmp_path / "fake-vibemix.app"),
    })
    result = subprocess.run(
        ["bash", str(UNINSTALL_SH), "--dry-run", "--clean"],
        env=env, capture_output=True, text=True,
    )
    assert result.returncode == 0
    # Nothing removed
    assert (data_root / "recordings").exists()
    assert cache_root.exists()
