# SPDX-License-Identifier: Apache-2.0
"""tests/launch/test_cut_count.py — ≤8 cut hard gate for hero demo storyboard.

VIS-08 (Phase 43, Plan 43-08): asserts the storyboard mock carries exactly
8 ``data-cut="N"`` frames (the CONTEXT §VIS-08 hard ship gate). Pairs with
``scripts/launch/check_cut_count.py``; rejects under-counts (<8, cut sequence
incomplete) and over-counts (>8, demo length bloat) symmetrically.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from scripts.launch.check_cut_count import (
    MAX_CUTS,
    count_cuts,
    main,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
STORYBOARD = REPO_ROOT / "mocks" / "vibemix-cinematic-storyboard.html"


def test_module_imports_cleanly() -> None:
    """Importing the checker exposes the three public symbols."""
    assert callable(main)
    assert callable(count_cuts)
    assert isinstance(MAX_CUTS, int)


def test_max_cuts_is_eight() -> None:
    """MAX_CUTS == 8 — the CONTEXT §VIS-08 hard ceiling."""
    assert MAX_CUTS == 8


def test_count_cuts_handles_zero_and_n() -> None:
    """count_cuts returns 0 for cleanly empty HTML; returns N for N markers."""
    assert count_cuts("<html><body></body></html>") == 0

    three = (
        '<section data-cut="1"></section>'
        '<section data-cut="2"></section>'
        '<article class="frame" data-cut="3"></article>'
    )
    assert count_cuts(three) == 3


def test_storyboard_has_exactly_eight_cuts() -> None:
    """The re-mocked storyboard (post-Task-2) exits 0 against the checker."""
    rc = main([])
    assert rc == 0, (
        "storyboard cut count drift detected — should be exactly 8 "
        "data-cut frames per CONTEXT §VIS-08 (see stderr from main())"
    )


def test_over_count_is_rejected(tmp_path: Path) -> None:
    """A tmp HTML with 9 data-cut attributes fails with non-zero rc + 'max 8'."""
    bad = tmp_path / "too_many.html"
    parts = "".join(f'<section data-cut="{i}"></section>' for i in range(1, 10))
    bad.write_text(f"<!doctype html><html><body>{parts}</body></html>",
                   encoding="utf-8")
    result = subprocess.run(
        [sys.executable,
         str(REPO_ROOT / "scripts" / "launch" / "check_cut_count.py"),
         "--file", str(bad)],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    assert result.returncode != 0
    assert "9 cuts" in result.stderr
    assert "max 8" in result.stderr


def test_under_count_is_rejected(tmp_path: Path) -> None:
    """A tmp HTML with 7 data-cut attributes fails with non-zero rc + 'need 8'."""
    bad = tmp_path / "too_few.html"
    parts = "".join(f'<section data-cut="{i}"></section>' for i in range(1, 8))
    bad.write_text(f"<!doctype html><html><body>{parts}</body></html>",
                   encoding="utf-8")
    result = subprocess.run(
        [sys.executable,
         str(REPO_ROOT / "scripts" / "launch" / "check_cut_count.py"),
         "--file", str(bad)],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    assert result.returncode != 0
    assert "7 cuts" in result.stderr
    assert "need 8" in result.stderr
