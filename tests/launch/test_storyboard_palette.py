# SPDX-License-Identifier: Apache-2.0
"""tests/launch/test_storyboard_palette.py — CDJ Whisper palette gate.

VIS-07 (Phase 43, Plan 43-07): asserts the storyboard mock stays inside the
locked CDJ Whisper palette (5 warm blacks + amber + REC pill red + a few
fixed neutrals). Catches drift like cyan/teal/electric-blue chip overlays
before they regress through into the hero demo.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from scripts.launch.check_storyboard_palette import (
    ALLOWED_PALETTE,
    extract_colors,
    main,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
STORYBOARD = REPO_ROOT / "mocks" / "vibemix-cinematic-storyboard.html"


def test_module_imports_cleanly() -> None:
    """Importing the checker exposes the three public symbols."""
    assert callable(main)
    assert callable(extract_colors)
    assert isinstance(ALLOWED_PALETTE, frozenset)


def test_allowed_palette_shape() -> None:
    """ALLOWED_PALETTE has amber phosphor, REC red, and >=4 warm blacks."""
    assert "#ffa12e" in ALLOWED_PALETTE  # phosphor (amber)
    assert "#ff3553" in ALLOWED_PALETTE  # REC pill

    # warm blacks — at least 4 from the CDJ Whisper canonical set
    warm_blacks = {"#0a0b0e", "#15181e", "#1d2128", "#07080a", "#0c0d10"}
    found_blacks = warm_blacks & ALLOWED_PALETTE
    assert len(found_blacks) >= 4, (
        f"expected ≥4 warm blacks in ALLOWED_PALETTE, found: {found_blacks}"
    )


def test_extract_colors_returns_normalized_set() -> None:
    """extract_colors returns a set of lowercase normalized hex strings."""
    colors = extract_colors(STORYBOARD)
    assert isinstance(colors, set)
    assert len(colors) > 0
    for c in colors:
        assert c.startswith("#")
        assert len(c) == 7  # #rrggbb
        assert c == c.lower(), f"color not normalized to lowercase: {c}"


def test_storyboard_is_palette_compliant() -> None:
    """The cleaned storyboard (post-Task-2) exits 0 against the checker."""
    rc = main([])
    assert rc == 0, "storyboard palette drift detected — see stderr from main()"


def test_cyan_injection_is_rejected(tmp_path: Path) -> None:
    """A tmp HTML with a cyan literal must fail the checker with non-zero rc."""
    bad = tmp_path / "bad.html"
    bad.write_text(
        "<!doctype html><html><head><style>.foo { color: #00ffff; }</style>"
        "</head><body></body></html>",
        encoding="utf-8",
    )
    rc = main(["--file", str(bad)])
    assert rc != 0, "checker failed to detect cyan #00ffff drift"


def test_cli_entrypoint_runs(tmp_path: Path) -> None:
    """Smoke: invoking the script via subprocess against the storyboard returns 0."""
    script = REPO_ROOT / "scripts" / "launch" / "check_storyboard_palette.py"
    result = subprocess.run(
        [sys.executable, str(script), "--file", str(STORYBOARD)],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0, (
        f"CLI exit {result.returncode}\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )
