# SPDX-License-Identifier: Apache-2.0
"""Phase 69 Plan 69-05 — anti-rot presence test for §SHIP-V4 + v7.0 OSS-04 sub-section.

OSS-04 invariant: the §SHIP-V4 cluster + the v7.0 OSS-04 autonomous-mode-route
sub-section + the exact pre-staged ``cut_release.sh v0.1.0-rc1`` invocation
+ the post-pre-flight ``gh release create v0.1.0-rc1`` command + the
docs/release-process.md "Autonomous-mode release path" section must not
silently drift between v7.0 milestone close and the eventual real cut.

The existing ``tests/repo/test_kaan_action_v4_surface.py`` covers the
broader §SHIP-V4 surface (open carry-forward tokens, public-tag confirm,
Gate-5b precondition, slop-blocklist). This gate pins specifically the
v7.0 OSS-04 autonomous-mode-route extension Plan 69-05 ships — the two
gates are complementary, not redundant.

When the real cut fires (Apple Dev + SignPath landed, Kaan runs the
invocation), this gate stays green — it pins the documentation contract,
not the cut outcome. Deletion or rename of any pinned string flips CI red
and forces a deliberate update.
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

KAAN_ACTION = REPO_ROOT / "KAAN-ACTION-LEGAL.md"
RELEASE_PROCESS = REPO_ROOT / "docs" / "release-process.md"

_SHIP_V4_HEADER = "## §SHIP-V4 — Consolidated v4.0 Ship Surface"
_V7_OSS_04_SUBSECTION = "### v7.0 OSS-04 autonomous-mode route"
_PRE_STAGED_INVOCATION = "bash scripts/launch/cut_release.sh v0.1.0-rc1"
_GH_RELEASE_CREATE_PREFIX = "gh release create v0.1.0-rc1"
_RELEASE_PROCESS_HEADER = "## Autonomous-mode release path"


def test_ship_v4_section_exists() -> None:
    """KAAN-ACTION-LEGAL.md §SHIP-V4 H2 cluster header appears exactly once."""
    assert KAAN_ACTION.exists(), (
        f"KAAN-ACTION-LEGAL.md missing at {KAAN_ACTION}. "
        "See Plan 69-05 Task 2."
    )
    text = KAAN_ACTION.read_text(encoding="utf-8")
    count = text.count(_SHIP_V4_HEADER)
    assert count == 1, (
        f"KAAN-ACTION-LEGAL.md must contain {_SHIP_V4_HEADER!r} exactly once; "
        f"found {count}. The §SHIP-V4 cluster is the consolidated v4.0 ship "
        "surface (Plan 58-03 / REL-03); deletion or duplication signals rot. "
        "See Plan 69-05 Task 2."
    )


def test_ship_v4_v7_oss_04_subsection_exists() -> None:
    """The v7.0 OSS-04 sub-section exists exactly once AND appears AFTER the §SHIP-V4 header."""
    text = KAAN_ACTION.read_text(encoding="utf-8")
    sub_count = text.count(_V7_OSS_04_SUBSECTION)
    assert sub_count == 1, (
        f"KAAN-ACTION-LEGAL.md must contain {_V7_OSS_04_SUBSECTION!r} exactly "
        f"once; found {sub_count}. This is the Plan 69-05 / Wave 4 deliverable. "
        "See Plan 69-05 Task 2."
    )
    lines = text.splitlines()
    ship_v4_line = next(
        (i for i, line in enumerate(lines) if line.startswith(_SHIP_V4_HEADER)),
        None,
    )
    subsection_line = next(
        (i for i, line in enumerate(lines) if line.startswith(_V7_OSS_04_SUBSECTION)),
        None,
    )
    assert ship_v4_line is not None, "§SHIP-V4 H2 line not found (see test_ship_v4_section_exists)"
    assert subsection_line is not None, (
        "v7.0 OSS-04 sub-section H3 line not found "
        "(see test_ship_v4_v7_oss_04_subsection_exists count assertion)"
    )
    assert subsection_line > ship_v4_line, (
        f"The v7.0 OSS-04 sub-section (line {subsection_line + 1}) must appear "
        f"AFTER the §SHIP-V4 header (line {ship_v4_line + 1}) — it is an "
        "extension of that cluster, not a standalone top-level section. "
        "See Plan 69-05 Task 2."
    )


def test_ship_v4_pre_staged_invocation_pinned() -> None:
    """The exact pre-staged real-cut invocation appears at least once in KAAN-ACTION-LEGAL.md."""
    text = KAAN_ACTION.read_text(encoding="utf-8")
    assert _PRE_STAGED_INVOCATION in text, (
        f"KAAN-ACTION-LEGAL.md must contain the exact pre-staged invocation "
        f"{_PRE_STAGED_INVOCATION!r} (no --dry-run flag — this is the REAL "
        "cut command Kaan runs when signatures land). See Plan 69-05 Task 2 "
        "and KAAN-ACTION-LEGAL.md §SHIP-V4 v7.0 OSS-04 sub-section."
    )


def test_ship_v4_gh_release_create_command_pinned() -> None:
    """The post-pre-flight `gh release create v0.1.0-rc1` command appears at least once."""
    text = KAAN_ACTION.read_text(encoding="utf-8")
    assert _GH_RELEASE_CREATE_PREFIX in text, (
        f"KAAN-ACTION-LEGAL.md must contain the post-pre-flight publish "
        f"command prefix {_GH_RELEASE_CREATE_PREFIX!r} (captured verbatim "
        "from cut_release.sh stdout at Plan 69-05 close). Prefix-only match "
        "tolerates future stdout-block tweaks while pinning the load-bearing "
        "form. See Plan 69-05 Task 2."
    )


def test_release_process_doc_has_autonomous_mode_path() -> None:
    """docs/release-process.md ## Autonomous-mode release path section exists exactly once."""
    assert RELEASE_PROCESS.exists(), (
        f"docs/release-process.md missing at {RELEASE_PROCESS}. "
        "See Plan 69-05 Task 3."
    )
    text = RELEASE_PROCESS.read_text(encoding="utf-8")
    count = text.count(_RELEASE_PROCESS_HEADER)
    assert count == 1, (
        f"docs/release-process.md must contain {_RELEASE_PROCESS_HEADER!r} "
        f"exactly once; found {count}. This is the Plan 69-05 Task 3 "
        "deliverable documenting the §SHIP-V4 autonomous-mode deferral "
        "contract. See Plan 69-05 Task 3."
    )
