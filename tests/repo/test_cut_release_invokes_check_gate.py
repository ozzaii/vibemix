# SPDX-License-Identifier: Apache-2.0
"""Plan 42-04 Task 2 — wire-in contract for ``scripts/launch/cut_release.sh``.

Pins the Phase 42 hybrid-gate plumbing decisions:
    - Gate 2b block exists and invokes ``check_gate.sh`` via bash.
    - The original Gate 2 (signed binaries) is still present
      (additive, not replacement).
    - The v2.1 [P85] reminder lines are removed from the success-path
      echo block (the GATE-06 line takes their place).
    - The success-path reminder block now references ``[GATE-06]`` and
      the hybrid gate.
    - ``scripts/release/check_gate.sh`` exists and is executable.
    - Plan-boundary: ``tests/repo/test_phase_16_override_expiry.py``
      still exists (its retirement is Plan 42-05).
"""

from __future__ import annotations

import os
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
CUT_RELEASE = REPO_ROOT / "scripts" / "launch" / "cut_release.sh"
CHECK_GATE = REPO_ROOT / "scripts" / "release" / "check_gate.sh"
PHASE_16_OVERRIDE_TEST = REPO_ROOT / "tests" / "repo" / "test_phase_16_override_expiry.py"


def _read_script() -> str:
    assert CUT_RELEASE.is_file(), f"cut_release.sh missing: {CUT_RELEASE}"
    return CUT_RELEASE.read_text(encoding="utf-8")


def _echo_lines(text: str) -> list[str]:
    """Return only the lines that start with ``echo "`` or ``echo '``.

    Used to scope assertions to user-visible output (excluding comments
    and shell logic).
    """
    out = []
    for ln in text.splitlines():
        stripped = ln.strip()
        if stripped.startswith('echo "') or stripped.startswith("echo '"):
            out.append(stripped)
    return out


# ---------------------------------------------------------------------------
# Gate 2b plumbing
# ---------------------------------------------------------------------------


def test_cut_release_has_gate_2b_block():
    text = _read_script()
    assert "[Gate 2b]" in text, "Gate 2b block missing from cut_release.sh"
    assert "check_gate.sh" in text, (
        "Gate 2b block must reference check_gate.sh"
    )


def test_cut_release_invokes_check_gate_via_bash():
    text = _read_script()
    # Either a quoted or unquoted REPO_ROOT-prefixed invocation is OK.
    pattern = re.compile(
        r"bash\s+(\"|')?\$\{REPO_ROOT\}/scripts/release/check_gate\.sh(\"|')?"
    )
    assert pattern.search(text), (
        "cut_release.sh must invoke check_gate.sh via "
        '`bash "${REPO_ROOT}/scripts/release/check_gate.sh"`'
    )


def test_cut_release_gate_2b_appears_after_gate_2():
    text = _read_script()
    idx_gate_2 = text.find("[Gate 2]")
    idx_gate_2b = text.find("[Gate 2b]")
    idx_gate_3 = text.find("[Gate 3]")
    assert idx_gate_2 != -1
    assert idx_gate_2b != -1
    assert idx_gate_3 != -1
    assert idx_gate_2 < idx_gate_2b < idx_gate_3, (
        "Gate 2b must sit between Gate 2 (signed binaries) and Gate 3 "
        "(README hero hash sync)"
    )


# ---------------------------------------------------------------------------
# Original Gate 2 (signed binaries) still present — regression guard
# ---------------------------------------------------------------------------


def test_cut_release_still_invokes_verify_signed():
    text = _read_script()
    assert "verify_signed.py --require-signed" in text, (
        "Original Gate 2 (signed binaries) must still be in cut_release.sh "
        "— Gate 2b is ADDITIVE, not a replacement."
    )


# ---------------------------------------------------------------------------
# P85 reminder cleanup
# ---------------------------------------------------------------------------


def test_cut_release_no_longer_mentions_p85_reminder():
    """Scoped to echo lines — the test pins that the *user-visible* P85
    reminder is gone. (Comment headers in the body for traceability are
    acceptable; the regression we guard against is the reminder echo
    surfacing in the cut output.)
    """
    text = _read_script()
    echoes = _echo_lines(text)
    joined = "\n".join(echoes)
    assert "[P85]" not in joined, (
        "[P85] echo reminder must be removed from cut_release.sh "
        "(Phase 42 GATE-08 retires the v2.1 override regime)"
    )
    assert "Phase 16 override cleanup reminder" not in joined, (
        "'Phase 16 override cleanup reminder' echo line must be removed"
    )
    assert "Phase 16 ear-test memory override" not in joined, (
        "'Phase 16 ear-test memory override' echo line must be removed"
    )


def test_cut_release_success_path_references_gate_06():
    text = _read_script()
    echoes = _echo_lines(text)
    joined = "\n".join(echoes)
    assert "[GATE-06]" in joined, (
        "Reminder block must reference [GATE-06] (the hybrid gate label)"
    )
    assert "Hybrid hallucination gate" in joined, (
        "Reminder block must mention 'Hybrid hallucination gate'"
    )


# ---------------------------------------------------------------------------
# check_gate.sh artifact
# ---------------------------------------------------------------------------


def test_check_gate_script_exists_and_executable():
    assert CHECK_GATE.is_file(), f"check_gate.sh missing: {CHECK_GATE}"
    assert os.access(CHECK_GATE, os.X_OK), "check_gate.sh not +x"


# ---------------------------------------------------------------------------
# Plan boundary — Plan 42-05 retires the v2.1 override expiry test
# ---------------------------------------------------------------------------


def test_p85_test_file_not_yet_deleted_in_this_plan():
    """Sanity that Plan 42-04 did NOT delete ``tests/repo/test_phase_16_override_expiry.py``
    — that retirement is Plan 42-05's job. Pins the plan boundary so a
    Plan 04 change cannot creep into Plan 05's scope.
    """
    assert PHASE_16_OVERRIDE_TEST.is_file(), (
        "tests/repo/test_phase_16_override_expiry.py is gone — its "
        "retirement belongs to Plan 42-05, not Plan 42-04. Restore it "
        "and route the deletion through Plan 42-05."
    )
