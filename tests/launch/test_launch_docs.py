# SPDX-License-Identifier: Apache-2.0
"""tests/launch/test_launch_docs.py — structural pinning for the
Phase 44 / LAUNCH-09 + LAUNCH-10 launch-orchestration docs.

Pins ``check_launch_docs.py`` against:
  - OUTREACH-CALENDAR.md exists + has >=7 status-checkbox blocks
    (3 editorial + 3 subreddit + 1 Discord T-3 — CONTEXT §LAUNCH-09)
  - LAUNCH-SEQUENCE.md exists + has exactly 7 ``## T-...`` rows
    (T-7, T-3, T-0, T+24h, T+72h, T+7d, T+30 — CONTEXT §LAUNCH-10)
  - LAUNCH-SEQUENCE.md cross-references >=3 distinct §LAUNCH-0[6-9]
    runbook anchors from KAAN-ACTION-LEGAL.md
  - Both docs are AI-slop-blocklist clean (re-uses the canonical
    blocklist; falls back to inline copy if 44-05's
    scripts/launch/check_no_ai_slop module is not yet on disk)
  - README.md references both new docs by filename

Mirrors the test shape of ``tests/launch/test_cut_count.py`` (Phase 43
VIS-08) and ``tests/launch/test_storyboard_palette.py``: import the
checker module, assert public symbols, run happy-path against real
docs, then 3 negative-case synthetic fixtures.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from scripts.launch.check_launch_docs import (
    AI_SLOP_BLOCKLIST,
    REQUIRED_CHECKBOX_BLOCKS,
    REQUIRED_T_ROWS,
    REQUIRED_LAUNCH_ANCHORS,
    count_checkbox_blocks,
    count_t_rows,
    distinct_launch_anchors,
    main,
    scan_ai_slop,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
LAUNCH_PREP = REPO_ROOT / "docs" / "launch-prep"


def test_module_imports_cleanly() -> None:
    """Importing the checker exposes the documented public symbols."""
    assert callable(main)
    assert callable(count_checkbox_blocks)
    assert callable(count_t_rows)
    assert callable(distinct_launch_anchors)
    assert callable(scan_ai_slop)
    assert isinstance(AI_SLOP_BLOCKLIST, (list, tuple, set, frozenset))
    assert isinstance(REQUIRED_CHECKBOX_BLOCKS, int)
    assert isinstance(REQUIRED_T_ROWS, int)
    assert isinstance(REQUIRED_LAUNCH_ANCHORS, int)


def test_constants_match_context() -> None:
    """The 3 hard-pinned counts match CONTEXT §LAUNCH-09 + §LAUNCH-10."""
    assert REQUIRED_CHECKBOX_BLOCKS == 7  # 3 editorial + 3 subreddit + 1 Discord T-3
    assert REQUIRED_T_ROWS == 7  # T-7, T-3, T-0, T+24h, T+72h, T+7d, T+30
    assert REQUIRED_LAUNCH_ANCHORS == 3  # >=3 distinct §LAUNCH-0[6-9]


def test_ai_slop_blocklist_contains_canonical_tokens() -> None:
    """The blocklist re-uses the canonical CONTEXT §LAUNCH-07 token list."""
    # Spot-check the 5 most load-bearing slop tokens. The list is shared with
    # Plan 44-05's check_no_ai_slop module (which lives in a sibling worktree
    # at write time); the helper falls back to an inline copy when the 44-05
    # module is not yet on disk.
    for canonical in ("leverage", "revolutionize", "game-changer", "seamless", "paradigm"):
        assert canonical in {token.lower() for token in AI_SLOP_BLOCKLIST}, (
            f"canonical slop token missing from blocklist: {canonical!r}"
        )


def test_happy_path_against_real_launch_prep_docs() -> None:
    """OUTREACH-CALENDAR.md + LAUNCH-SEQUENCE.md (post-Tasks-1+2) exit 0."""
    rc = main(["--launch-prep-dir", str(LAUNCH_PREP), "--quiet"])
    assert rc == 0, (
        "real launch-prep docs failed the structural gate — re-run "
        "without --quiet to see which assertion fired"
    )


def test_outreach_calendar_six_blocks_is_rejected(tmp_path: Path) -> None:
    """A synthetic OUTREACH-CALENDAR with 6 (not 7) checkbox blocks fails."""
    fake_prep = tmp_path / "launch-prep"
    fake_prep.mkdir()
    six_blocks = "\n\n".join(
        f"### Entry {i}\n\n- **Status:** ☐ Drafted ☐ Sent ☐ Acknowledged ☐ Published\n"
        for i in range(1, 7)
    )
    (fake_prep / "OUTREACH-CALENDAR.md").write_text(
        "# Fake outreach calendar (6 entries)\n\n" + six_blocks,
        encoding="utf-8",
    )
    (fake_prep / "LAUNCH-SEQUENCE.md").write_text(
        "# Fake launch sequence\n\n"
        + "\n\n".join(f"## T-{i} — Row {i}\n\n§LAUNCH-07 §LAUNCH-08 §LAUNCH-09" for i in range(7)),
        encoding="utf-8",
    )
    (fake_prep / "README.md").write_text(
        "# Fake README\n\n- OUTREACH-CALENDAR.md\n- LAUNCH-SEQUENCE.md\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "launch" / "check_launch_docs.py"),
            "--launch-prep-dir",
            str(fake_prep),
        ],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    assert result.returncode != 0
    assert "checkbox" in result.stderr.lower()


def test_launch_sequence_six_rows_is_rejected(tmp_path: Path) -> None:
    """A synthetic LAUNCH-SEQUENCE with 6 (not 7) T-rows fails."""
    fake_prep = tmp_path / "launch-prep"
    fake_prep.mkdir()
    (fake_prep / "OUTREACH-CALENDAR.md").write_text(
        "# Fake outreach calendar\n\n"
        + "\n\n".join(
            f"### Entry {i}\n\n- **Status:** ☐ Drafted ☐ Sent ☐ Acknowledged ☐ Published\n"
            for i in range(1, 8)
        ),
        encoding="utf-8",
    )
    six_rows = "\n\n".join(
        f"## T-{i} — Row {i}\n\n§LAUNCH-07 §LAUNCH-08 §LAUNCH-09" for i in range(6)
    )
    (fake_prep / "LAUNCH-SEQUENCE.md").write_text(
        "# Fake launch sequence (6 rows)\n\n" + six_rows,
        encoding="utf-8",
    )
    (fake_prep / "README.md").write_text(
        "# Fake README\n\n- OUTREACH-CALENDAR.md\n- LAUNCH-SEQUENCE.md\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "launch" / "check_launch_docs.py"),
            "--launch-prep-dir",
            str(fake_prep),
        ],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    assert result.returncode != 0
    assert "row" in result.stderr.lower() or "t-" in result.stderr.lower()


def test_launch_sequence_with_slop_token_is_rejected(tmp_path: Path) -> None:
    """A LAUNCH-SEQUENCE with a slop token (e.g. 'leverage') fails."""
    fake_prep = tmp_path / "launch-prep"
    fake_prep.mkdir()
    (fake_prep / "OUTREACH-CALENDAR.md").write_text(
        "# Fake outreach calendar\n\n"
        + "\n\n".join(
            f"### Entry {i}\n\n- **Status:** ☐ Drafted ☐ Sent ☐ Acknowledged ☐ Published\n"
            for i in range(1, 8)
        ),
        encoding="utf-8",
    )
    seven_rows = "\n\n".join(
        f"## T-{i} — Row {i}\n\nWe leverage best practices §LAUNCH-07 §LAUNCH-08 §LAUNCH-09"
        for i in range(7)
    )
    (fake_prep / "LAUNCH-SEQUENCE.md").write_text(
        "# Fake launch sequence with slop\n\n" + seven_rows,
        encoding="utf-8",
    )
    (fake_prep / "README.md").write_text(
        "# Fake README\n\n- OUTREACH-CALENDAR.md\n- LAUNCH-SEQUENCE.md\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "launch" / "check_launch_docs.py"),
            "--launch-prep-dir",
            str(fake_prep),
        ],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    assert result.returncode != 0
    assert "slop" in result.stderr.lower() or "leverage" in result.stderr.lower()
