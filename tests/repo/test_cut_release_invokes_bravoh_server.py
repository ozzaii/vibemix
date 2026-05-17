# SPDX-License-Identifier: Apache-2.0
"""Plan 45-03 Task 3 — wire-in contract for ``scripts/launch/cut_release.sh``.

Pins the SHIP-06 / OPS-14 Bravoh-server gate plumbing decisions:

  Test 13. ``cut_release.sh`` contains a new ``[Gate 5b] ... check_bravoh_server_ready.sh`` block.
  Test 14. Gate 5b sits AFTER Gate 5 (POC files untouched) and BEFORE Gate 6 (bundle ID locked).
  Test 15. The Gate 5b block invokes ``bash "${REPO_ROOT}/scripts/release/check_bravoh_server_ready.sh"``
           (same shape as Gate 2b's ``check_gate.sh`` invocation).
  Test 16. The ``fail()`` message in the Gate 5b block routes the operator to
           the probe for the structured ``BLOCKED_BY`` line.
  Test 17. ``scripts/release/check_bravoh_server_ready.sh`` exists and is executable.
  Test 18. Tag regex ``^v2\\.1\\.0-rc[0-9]+$`` UNCHANGED — Plan 45-06 (or later)
           owns the bump to ``v3.0``; this plan stays scoped to the Bravoh
           server gate.

Regression baseline preservation is asserted by re-running
``tests/repo/test_cut_release_invokes_check_gate.py`` in the same pytest
invocation (verification step).
"""

from __future__ import annotations

import os
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
CUT_RELEASE = REPO_ROOT / "scripts" / "launch" / "cut_release.sh"
BRAVOH_PROBE = REPO_ROOT / "scripts" / "release" / "check_bravoh_server_ready.sh"


def _read_script() -> str:
    assert CUT_RELEASE.is_file(), f"cut_release.sh missing: {CUT_RELEASE}"
    return CUT_RELEASE.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Test 13 — Gate 5b block present
# ---------------------------------------------------------------------------


def test_cut_release_has_gate_5b_block():
    text = _read_script()
    assert "[Gate 5b]" in text, "Gate 5b block missing from cut_release.sh"
    assert "check_bravoh_server_ready.sh" in text, (
        "Gate 5b block must reference check_bravoh_server_ready.sh"
    )


# ---------------------------------------------------------------------------
# Test 14 — Gate ordering: 5 < 5b < 6
# ---------------------------------------------------------------------------


def test_gate_5b_sits_between_gate_5_and_gate_6():
    text = _read_script()
    idx_5 = text.find("[Gate 5]")
    idx_5b = text.find("[Gate 5b]")
    idx_6 = text.find("[Gate 6]")
    assert idx_5 != -1, "Gate 5 banner missing"
    assert idx_5b != -1, "Gate 5b banner missing"
    assert idx_6 != -1, "Gate 6 banner missing"
    assert idx_5 < idx_5b < idx_6, (
        "Gate 5b must sit between Gate 5 (POC files) and Gate 6 (bundle ID); "
        f"got positions: Gate 5={idx_5}, Gate 5b={idx_5b}, Gate 6={idx_6}"
    )


# ---------------------------------------------------------------------------
# Test 15 — invocation shape mirrors Gate 2b's check_gate.sh
# ---------------------------------------------------------------------------


def test_cut_release_invokes_bravoh_probe_via_bash():
    text = _read_script()
    pattern = re.compile(
        r'bash\s+"\$\{REPO_ROOT\}/scripts/release/check_bravoh_server_ready\.sh"'
    )
    assert pattern.search(text), (
        'cut_release.sh must invoke check_bravoh_server_ready.sh via '
        '`bash "${REPO_ROOT}/scripts/release/check_bravoh_server_ready.sh"` '
        "(same shape as the Gate 2b check_gate.sh invocation)"
    )


# ---------------------------------------------------------------------------
# Test 16 — fail() message routes operator to the probe for BLOCKED_BY
# ---------------------------------------------------------------------------


def test_gate_5b_fail_message_routes_to_probe_for_blocked_by():
    text = _read_script()
    # Scope to the slice between Gate 5b and Gate 6.
    idx_5b = text.find("[Gate 5b]")
    idx_6 = text.find("[Gate 6]")
    assert idx_5b != -1 and idx_6 != -1 and idx_5b < idx_6
    block = text[idx_5b:idx_6]

    # Must call fail(...) with a message that points at the probe.
    assert "fail " in block or 'fail "' in block, (
        f"Gate 5b block must call fail() on failure; got:\n{block}"
    )
    assert "check_bravoh_server_ready.sh" in block, (
        "fail message must reference the probe by name"
    )
    assert "BLOCKED_BY" in block, (
        "fail message must reference BLOCKED_BY (the structured stderr "
        "directive the probe emits, so the operator knows what to grep for)"
    )


# ---------------------------------------------------------------------------
# Test 17 — probe artifact exists + is executable
# ---------------------------------------------------------------------------


def test_check_bravoh_server_ready_exists_and_executable():
    assert BRAVOH_PROBE.is_file(), f"missing: {BRAVOH_PROBE}"
    assert os.access(BRAVOH_PROBE, os.X_OK), f"not +x: {BRAVOH_PROBE}"


# ---------------------------------------------------------------------------
# Test 18 — tag regex untouched (Plan 45-06 owns the v3.0 bump)
# ---------------------------------------------------------------------------


def test_tag_regex_unchanged_in_this_plan():
    text = _read_script()
    # Pin both the variable assignment and the contract that this plan does
    # NOT introduce a v3 regex (that's a future plan's job).
    assert "TAG_REGEX='^v2\\.1\\.0-rc[0-9]+$'" in text, (
        "Tag regex must remain `^v2\\.1\\.0-rc[0-9]+$` in this plan; "
        "Plan 45-06 (or later) owns the v3.0 bump."
    )
    # Negative pin: no v3 regex sneaks in.
    assert "v3\\.0" not in text, (
        "v3 tag regex must not appear in cut_release.sh in this plan"
    )
