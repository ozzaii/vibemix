# SPDX-License-Identifier: Apache-2.0
"""Plan 58-04 Task 1 — pin Gate 1 (tag regex) + Gate 4 (milestone audit path)
re-pointed from the stale v2.1 RC scheme to the v0.1.0-rc PUBLIC OSS tag +
the v4.0 INTERNAL milestone audit.

Decision (58-CONTEXT §"Public release tag = v0.1.0-rc1"):
    - PUBLIC release tag  = ``v0.1.0-rc1``  → Gate 1 regex ``^v0\\.1\\.0-rc[0-9]+$``
    - INTERNAL milestone  = ``v4.0``        → Gate 4 audit ``v4.0-MILESTONE-AUDIT.md``

Mirrors the read-script + regex style of
``tests/repo/test_cut_release_invokes_check_gate.py``.
"""

from __future__ import annotations

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
CUT_RELEASE = REPO_ROOT / "scripts" / "launch" / "cut_release.sh"


def _read_script() -> str:
    assert CUT_RELEASE.is_file(), f"cut_release.sh missing: {CUT_RELEASE}"
    return CUT_RELEASE.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Gate 1 — tag regex re-pointed to the v0.1.0-rc public tag
# ---------------------------------------------------------------------------


def test_tag_regex_is_v0_1_0_rc():
    text = _read_script()
    assert r"^v0\.1\.0-rc[0-9]+$" in text, (
        "TAG_REGEX must be re-pointed to the v0.1.0-rc public OSS tag "
        r"(^v0\.1\.0-rc[0-9]+$)"
    )


def test_old_v2_1_tag_regex_is_gone():
    text = _read_script()
    assert r"^v2\.1\.0-rc" not in text, (
        "stale v2.1 tag regex must be removed from cut_release.sh"
    )


def test_tag_regex_accepts_public_rejects_misversioned():
    """Drive the actual TAG_REGEX literal: v0.1.0-rc1 matches; v2.1.0-rc1 +
    bare v1.0.0 do not."""
    text = _read_script()
    m = re.search(r"TAG_REGEX='([^']+)'", text)
    assert m, "TAG_REGEX assignment not found in cut_release.sh"
    regex = re.compile(m.group(1))
    assert regex.match("v0.1.0-rc1"), "Gate 1 must ACCEPT v0.1.0-rc1"
    assert regex.match("v0.1.0-rc12"), "Gate 1 must ACCEPT multi-digit rc"
    assert not regex.match("v2.1.0-rc1"), "Gate 1 must REJECT the old v2.1.0-rc1"
    assert not regex.match("v1.0.0"), "Gate 1 must REJECT bare v1.0.0 (P83)"
    assert not regex.match("v0.1.0"), "Gate 1 must REJECT a non-rc release tag"


# ---------------------------------------------------------------------------
# Gate 4 — milestone audit path re-pointed to the v4.0 internal milestone
# ---------------------------------------------------------------------------


def test_gate4_audit_path_is_v4_0():
    text = _read_script()
    assert "v4.0-MILESTONE-AUDIT.md" in text, (
        "Gate 4 AUDIT path must be re-pointed to .planning/v4.0-MILESTONE-AUDIT.md"
    )


def test_gate4_old_v2_1_audit_path_is_gone():
    text = _read_script()
    assert "v2.1-MILESTONE-AUDIT.md" not in text, (
        "stale v2.1-MILESTONE-AUDIT.md path must be removed from cut_release.sh"
    )


def test_gate4_wired_grep_unchanged():
    """The WIRED/passed frontmatter grep is left verbatim (only the path moved)."""
    text = _read_script()
    assert r"^(overall_verdict|status):\s*(WIRED|passed)\s*$" in text, (
        "Gate 4 frontmatter verdict grep must stay verbatim"
    )
