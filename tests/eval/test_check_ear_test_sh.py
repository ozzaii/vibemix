# SPDX-License-Identifier: Apache-2.0
"""Plan 42-03 Task 3 — contract tests for ``scripts/release/check_ear_test.sh``.

Invokes the bash script via :mod:`subprocess` with ``EAR_TEST_DIR``
pointed at a ``tmp_path`` populated by ``_make_log``. Pins the
14-day-window / ≥ 2 sessions / ≥ 2 genres / zero-slop-flag contract.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest


SCRIPT_PATH = Path("scripts/release/check_ear_test.sh").resolve()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _zero_slop() -> dict[str, bool]:
    return {
        "felt_slop": False,
        "felt_scripted": False,
        "felt_late": False,
        "felt_generic": False,
    }


def _make_log(
    base: Path,
    session_id: str,
    genre: str,
    signed_at: datetime,
    slop_flags: dict[str, bool] | None = None,
    duration_s: int = 1800,
    free_form: str = "",
) -> Path:
    base.mkdir(parents=True, exist_ok=True)
    payload = {
        "session_id": session_id,
        "started_at": (signed_at - timedelta(seconds=duration_s))
        .replace(microsecond=0)
        .isoformat(),
        "duration_s": duration_s,
        "genre": genre,
        "slop_flags": slop_flags or _zero_slop(),
        "free_form": free_form,
        "signed_by": "kaan",
        "signed_at": signed_at.replace(microsecond=0).isoformat(),
    }
    out = base / f"{session_id}.json"
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return out


def _run(
    ear_test_dir: Path,
    window_days: int = 14,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["EAR_TEST_DIR"] = str(ear_test_dir)
    env["WINDOW_DAYS"] = str(window_days)
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        ["bash", str(SCRIPT_PATH)],
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
    )


def _now() -> datetime:
    return datetime.now(UTC)


# ---------------------------------------------------------------------------
# Pre-flight: script + jq present
# ---------------------------------------------------------------------------


def test_script_exists_and_executable():
    assert SCRIPT_PATH.is_file()
    assert os.access(SCRIPT_PATH, os.X_OK), "check_ear_test.sh not +x"


@pytest.fixture(autouse=True)
def _skip_if_no_jq():
    if shutil.which("jq") is None:
        pytest.skip("jq not on PATH — check_ear_test.sh requires it")


# ---------------------------------------------------------------------------
# Reject paths
# ---------------------------------------------------------------------------


def test_empty_dir_fails(tmp_path: Path):
    """No log files at all → reject with 'no ear-test logs' message."""
    result = _run(tmp_path)
    assert result.returncode == 1
    assert "no ear-test logs" in result.stderr.lower()


def test_one_session_fails(tmp_path: Path):
    """Single in-window session — need ≥ 2 sessions."""
    _make_log(tmp_path, "s1", "techno", _now() - timedelta(days=1))
    result = _run(tmp_path)
    assert result.returncode == 1
    assert "fewer than 2 sessions" in result.stderr.lower()


def test_two_same_genre_fails(tmp_path: Path):
    """Two house sessions → still 1 genre."""
    _make_log(tmp_path, "h1", "house", _now() - timedelta(days=1))
    _make_log(tmp_path, "h2", "house", _now() - timedelta(days=2))
    result = _run(tmp_path)
    assert result.returncode == 1
    assert "fewer than 2 genres" in result.stderr.lower()


def test_one_slop_flag_fails(tmp_path: Path):
    """Two genres + 2 sessions, but one has felt_late=true → reject."""
    _make_log(tmp_path, "h1", "house", _now() - timedelta(days=1))
    bad_flags = _zero_slop()
    bad_flags["felt_late"] = True
    _make_log(
        tmp_path,
        "t1",
        "techno",
        _now() - timedelta(days=2),
        slop_flags=bad_flags,
    )
    result = _run(tmp_path)
    assert result.returncode == 1
    assert "slop-flagged" in result.stderr.lower()


def test_session_outside_window_excluded(tmp_path: Path):
    """One in-window + one 20d-old → reject (only 1 session in window)."""
    _make_log(tmp_path, "h1", "house", _now() - timedelta(days=1))
    _make_log(tmp_path, "t_old", "techno", _now() - timedelta(days=20))
    result = _run(tmp_path)
    assert result.returncode == 1
    # Either the "fewer than 2 sessions in window" or "fewer than 2 genres"
    # invariant trips — both name the failure.
    err = result.stderr.lower()
    assert ("fewer than 2 sessions" in err) or ("fewer than 2 genres" in err)


def test_all_slop_flags_set_fails(tmp_path: Path):
    """Even with ≥ 2 genres + ≥ 2 sessions, any slop=true rejects."""
    all_slop = {k: True for k in _zero_slop()}
    _make_log(
        tmp_path,
        "h1",
        "house",
        _now() - timedelta(days=1),
        slop_flags=all_slop,
    )
    _make_log(tmp_path, "t1", "techno", _now() - timedelta(days=2))
    result = _run(tmp_path)
    assert result.returncode == 1
    assert "slop-flagged" in result.stderr.lower()


# ---------------------------------------------------------------------------
# Accept path
# ---------------------------------------------------------------------------


def test_two_different_genres_in_window_passes(tmp_path: Path):
    """Two distinct genres + clean slop_flags + both signed within window."""
    _make_log(tmp_path, "h1", "house", _now() - timedelta(days=1))
    _make_log(tmp_path, "t1", "techno", _now() - timedelta(days=3))
    result = _run(tmp_path)
    assert result.returncode == 0, (
        f"expected PASS; stdout={result.stdout!r}; stderr={result.stderr!r}"
    )
    assert "PASS check_ear_test" in result.stdout


def test_three_genres_extra_passes(tmp_path: Path):
    """3 sessions across 3 distinct genres, all clean → still pass."""
    _make_log(tmp_path, "h1", "house", _now() - timedelta(days=1))
    _make_log(tmp_path, "t1", "techno", _now() - timedelta(days=2))
    _make_log(tmp_path, "hk1", "hard_tek", _now() - timedelta(days=5))
    result = _run(tmp_path)
    assert result.returncode == 0
    assert "PASS" in result.stdout


def test_session_at_window_boundary_passes(tmp_path: Path):
    """A session signed 13 days ago counts as in-window."""
    _make_log(tmp_path, "h1", "house", _now() - timedelta(days=13))
    _make_log(tmp_path, "t1", "techno", _now() - timedelta(days=1))
    result = _run(tmp_path)
    assert result.returncode == 0


# ---------------------------------------------------------------------------
# Tooling absence
# ---------------------------------------------------------------------------


def test_jq_missing_surfaces_clear_error(tmp_path: Path):
    """PATH stripped of jq → exit 1 + clear error mentioning jq."""
    # Build a minimal PATH that excludes /usr/local/bin (the typical jq
    # location). We do leave /bin + /usr/bin so bash itself + coreutils
    # still resolve.
    safe_path = "/bin:/usr/bin:/usr/sbin"
    if shutil.which("jq", path=safe_path) is not None:
        pytest.skip("jq present in minimal PATH; cannot simulate absence")
    result = _run(tmp_path, extra_env={"PATH": safe_path})
    assert result.returncode == 1
    err = result.stderr.lower()
    assert "jq" in err and ("required" in err or "not found" in err)


# ---------------------------------------------------------------------------
# GitHub Actions annotation mode
# ---------------------------------------------------------------------------


def test_github_actions_annotation_on_reject(tmp_path: Path):
    """When GITHUB_ACTIONS=true, rejects use ::error:: prefixes."""
    result = _run(tmp_path, extra_env={"GITHUB_ACTIONS": "true"})
    assert result.returncode == 1
    assert "::error::check_ear_test:" in result.stderr
