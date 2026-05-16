# SPDX-License-Identifier: Apache-2.0
"""Phase 39 / Plan 39-08 — Phase 16 override expiry gate.

REQ-IDs: SHIP-08
Pitfall: P85

Asserts:
- STATE.md still carries the Phase 16 override line (traceability).
- STATE.md has a near-it marker that the override expires post-v2.1.
- `scripts/launch/cut_release.sh` prints a Phase 16 cleanup reminder
  on its success path (load-bearing — every cut reminds Kaan).
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
STATE = REPO_ROOT / ".planning" / "STATE.md"
CUT_RELEASE = REPO_ROOT / "scripts" / "launch" / "cut_release.sh"


def test_state_md_exists():
    assert STATE.exists()


def test_state_md_has_phase_16_override_line():
    body = STATE.read_text(encoding="utf-8")
    # Either the canonical phrase or the decision-list bullet.
    assert "Phase 16 ear-test memory override" in body, (
        "STATE.md missing 'Phase 16 ear-test memory override' line "
        "(traceability for P85 expiry tracking)"
    )


def test_state_md_has_expires_post_v2_1_marker():
    """Near the Phase 16 line, an 'expires post-v2.1' marker must
    appear so the override scope is unambiguous."""
    body = STATE.read_text(encoding="utf-8")
    # Find every Phase 16 line; at least one must have an expiry marker
    # within ~400 chars.
    matches = [m.start() for m in re.finditer(r"Phase 16 ear-test", body)]
    assert matches, "no Phase 16 lines to scan"
    found_marker = False
    for idx in matches:
        chunk = body[idx:idx + 400]
        if (
            "expires post-v2.1" in chunk
            or "expires post v2.1" in chunk
            or "Override expires" in chunk
            or "v2.1 only" in chunk
        ):
            found_marker = True
            break
    assert found_marker, (
        "no 'expires post-v2.1' marker near any Phase 16 line — "
        "P85 tracking is load-bearing"
    )


def test_cut_release_sh_reminds_to_remove_override():
    """cut_release.sh's success path must include a Phase 16 override
    cleanup reminder line so every RC cut prods Kaan to remove the
    override post-bake."""
    body = CUT_RELEASE.read_text(encoding="utf-8")
    assert "Phase 16 override cleanup reminder" in body, (
        "cut_release.sh missing 'Phase 16 override cleanup reminder' — "
        "P85 reminder is load-bearing"
    )
    # The reminder must appear in the success block, not just a comment.
    # Find the ALL GATES PASS marker; reminder must come after it.
    pass_idx = body.find("ALL GATES PASS")
    reminder_idx = body.find("Phase 16 override cleanup reminder")
    assert pass_idx != -1 and reminder_idx != -1
    assert reminder_idx > pass_idx, (
        "Phase 16 reminder must appear after the success block, not before"
    )
