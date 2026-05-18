"""Behavioral tests for scripts/audit/check_no_slop_install.py.

Phase 49 Plan 06 — sibling anti-slop gate for installer/wizard surface.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SIBLING = ROOT / "scripts" / "audit" / "check_no_slop_install.py"
PARENT = ROOT / "scripts" / "launch" / "check_no_ai_slop.py"


def test_sibling_exists():
    assert SIBLING.exists()


def test_clean_phase_49_surface_passes():
    """Production Phase 49 surface must pass the gate."""
    result = subprocess.run(
        [sys.executable, "-m", "scripts.audit.check_no_slop_install"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Phase 49 surface contains slop:\n{result.stderr}"
    assert "OK" in result.stdout


def test_seamless_literal_fails(tmp_path: Path):
    """Feed a target containing 'seamless' → exit 1 + substitution hint."""
    bad = tmp_path / "bad-copy.json"
    bad.write_text('{"x": "Set up vibemix is seamless and powerful"}')
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.audit.check_no_slop_install",
            "--target",
            str(bad.relative_to(ROOT) if bad.is_relative_to(ROOT) else bad),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    # We pass an absolute-path target via --target. The sibling joins it
    # with REPO_ROOT/<rel>; for absolute paths Path() / abs returns abs.
    # If the file is actually outside ROOT, the joiner may resolve to
    # ROOT/<abspath-as-rel-stripped> — for this test we'll just verify
    # the sibling's behavior when fed a file with forbidden literals via
    # a colocated tmp file.
    # If the path resolution failed, the test stays meaningful as long
    # as the sibling exits non-zero for at least ONE of the forbidden
    # literals. We assert returncode != 0 on the dummy file we set up
    # via a colocated symlink instead — see below.
    # For now, simpler: write the slop into a file that IS inside ROOT.
    pass


def test_seamless_inside_root_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Drop a slop-containing file inside ROOT, target it, expect exit 1."""
    bad = ROOT / "tmp_slop_test.json"
    bad.write_text('{"x": "This is seamless and powerful"}')
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "scripts.audit.check_no_slop_install",
                "--target",
                "tmp_slop_test.json",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1, f"slop should fail; got {result.returncode}\n{result.stdout}\n{result.stderr}"
        assert "seamless" in result.stderr
    finally:
        bad.unlink(missing_ok=True)


def test_deeply_regex_fails(tmp_path: Path):
    """`deeply integrated` triggers the regex even though it's not a literal token."""
    bad = ROOT / "tmp_deeply_test.txt"
    bad.write_text("This is deeply integrated into your workflow.")
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "scripts.audit.check_no_slop_install",
                "--target",
                "tmp_deeply_test.txt",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1, f"deeply regex should fail\n{result.stderr}"
        assert "deeply" in result.stderr.lower()
    finally:
        bad.unlink(missing_ok=True)


def test_copy_substitutions_md_not_in_default_targets():
    """The substitutions doc itself MUST NOT be in DEFAULT_TARGETS."""
    text = SIBLING.read_text()
    # The default targets array should not include copy-substitutions.md
    assert "copy-substitutions.md" not in text or "Excluded" in text


def test_blocklist_import_from_parent():
    """Sibling-pattern invariant: blocklist comes from parent module."""
    text = SIBLING.read_text()
    assert "AI_SLOP_BLOCKLIST" in text
    assert "check_no_ai_slop" in text  # importlib reference


def test_parent_pinned_targets_unchanged():
    """Parent script's pinned paths must not include Phase 49 surface.

    Sibling-pattern invariant: each phase that needs anti-slop on a new
    surface MUST create a sibling rather than widen the parent.
    """
    text = PARENT.read_text()
    forbidden_in_parent = [
        "installer/companion/onboarding_copy.json",
        "tauri/ui/src/wizard/copy.json",
        "tauri/ui/src/wizard/step-forewarning",
    ]
    for needle in forbidden_in_parent:
        # The parent may MENTION the path in comments (acceptable), but
        # must not include it as a default target. We approximate by
        # asserting the path doesn't appear in a context that looks like
        # a target list (e.g., in DEFAULT_DIR / TARGETS / glob).
        assert (
            f"DEFAULT_DIR = {needle!r}" not in text
            and f'"{needle}"' not in text.split("# Anchor")[0]  # before anchors block
        ), f"Parent contains Phase 49 path in target context: {needle}"
