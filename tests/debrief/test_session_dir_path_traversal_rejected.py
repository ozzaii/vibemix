# SPDX-License-Identifier: Apache-2.0
"""Plan 29-02 Task 1: path-traversal session_dir rejected BEFORE any read.

The Rust shell (Plan 29-04) gates first; this is defense-in-depth.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from vibemix.debrief import InvalidSessionDir, validate_session_dir_under_root


def _make_session(root: Path, name: str = "20260515-111111") -> Path:
    """Create a real session-dir under ``root``."""
    s = root / name
    s.mkdir(parents=True, exist_ok=True)
    (s / "events.jsonl").write_text("", encoding="utf-8")
    return s


def test_relative_traversal_rejected(tmp_path: Path):
    root = tmp_path / "recordings"
    root.mkdir()
    _make_session(root)
    with pytest.raises(InvalidSessionDir):
        validate_session_dir_under_root(
            Path("../../etc/passwd"), recordings_root=root
        )


def test_absolute_path_outside_root_rejected(tmp_path: Path):
    root = tmp_path / "recordings"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    with pytest.raises(InvalidSessionDir):
        validate_session_dir_under_root(outside, recordings_root=root)


def test_nonexistent_path_rejected(tmp_path: Path):
    root = tmp_path / "recordings"
    root.mkdir()
    with pytest.raises(InvalidSessionDir):
        validate_session_dir_under_root(
            root / "does-not-exist", recordings_root=root
        )


def test_session_id_resolves_under_root(tmp_path: Path):
    root = tmp_path / "recordings"
    root.mkdir()
    _make_session(root, "20260515-111111")
    out = validate_session_dir_under_root(
        "20260515-111111", recordings_root=root
    )
    assert out.is_dir()
    # Must be a child of root.
    out.relative_to(root.resolve())


def test_absolute_path_inside_root_accepted(tmp_path: Path):
    root = tmp_path / "recordings"
    root.mkdir()
    sess = _make_session(root, "20260515-222222")
    out = validate_session_dir_under_root(sess, recordings_root=root)
    assert out == sess.resolve()
