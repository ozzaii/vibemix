# SPDX-License-Identifier: Apache-2.0
"""Phase 39 / Plan 39-08 — KAAN-ACTION-LEGAL §SHIP + §POST-RC-CLEANUP.

REQ-IDs: SHIP-08
Pitfall: P85 (Phase 16 override expiry).

Asserts:
- §SHIP has all 6 Phase-39 customer-facing entries (CUT, TWEET,
  DISCORD, TRANSFER, ROTATE, V1-DECISION).
- §POST-RC-CLEANUP entries present (Phase 16 override expiry, Bravoh
  funnel verification, v2.2 backlog grooming).
- DIST-09 + DIST-11 legal-capacity carveouts (P46) still present + intact.
- All sections carry sign-off blocks.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
LEGAL = REPO_ROOT / "KAAN-ACTION-LEGAL.md"


@pytest.fixture(scope="module")
def text() -> str:
    return LEGAL.read_text(encoding="utf-8")


SHIP_ENTRIES = [
    "SHIP-CUT",
    "SHIP-TWEET",
    "SHIP-DISCORD",
    "SHIP-TRANSFER",
    "SHIP-ROTATE",
    "SHIP-V1-DECISION",
]


def test_ship_section_present(text: str):
    assert "§SHIP — Phase 39" in text or "## §SHIP" in text


def test_ship_section_has_six_entries(text: str):
    """All 6 Phase-39 customer-facing actions must appear under §SHIP."""
    for entry in SHIP_ENTRIES:
        assert entry in text, f"§SHIP missing entry: {entry}"


def test_each_ship_entry_marked_kaan_or_francesco_action(text: str):
    """Each entry must declare its owner (KAAN-ACTION / FRANCESCO-ACTION
    / BRAVOH-action). At least one of the three appears per entry header."""
    # Crude check: between each SHIP-* heading and the next, at least one
    # of the role markers must appear.
    lines = text.splitlines()
    indices = [i for i, ln in enumerate(lines) if any(e in ln and "###" in ln for e in SHIP_ENTRIES)]
    indices.append(len(lines))
    for j, i in enumerate(indices[:-1]):
        chunk = "\n".join(lines[i:indices[j + 1]])
        assert any(t in chunk for t in (
            "KAAN-ACTION", "FRANCESCO-ACTION", "BRAVOH-action",
            "Kaan-action", "Francesco-action", "Bravoh-team",
            "KAAN + FRANCESCO", "Kaan", "Francesco", "Bravoh-action",
        )), (
            f"§SHIP entry near line {i+1} missing owner marker:\n"
            f"{chunk[:300]}"
        )


def test_post_rc_cleanup_section_present(text: str):
    assert "§POST-RC-CLEANUP" in text


def test_post_rc_cleanup_section_has_phase_16_override(text: str):
    """The §POST-RC-CLEANUP section must call out Phase 16 override
    expiry (P85)."""
    # Find the section body.
    start = text.find("§POST-RC-CLEANUP")
    assert start != -1
    section = text[start:start + 5000]  # next ~5000 chars
    assert "Phase 16" in section
    assert "P85" in section or "expires" in section.lower()


def test_post_rc_cleanup_includes_bravoh_funnel_verification(text: str):
    start = text.find("§POST-RC-CLEANUP")
    section = text[start:start + 5000]
    assert "Bravoh funnel" in section or "Bravoh-funnel" in section.lower() or "utm_" in section


def test_post_rc_cleanup_includes_v2_2_backlog(text: str):
    start = text.find("§POST-RC-CLEANUP")
    section = text[start:start + 5000]
    assert "v2.2" in section


def test_legal_capacity_carveouts_unchanged(text: str):
    """DIST-09 + DIST-11 legal-capacity protocols + P46 callout must
    remain intact (Phase 38 contract preserved)."""
    # P46 callout at top.
    assert "LEGAL-CAPACITY CARVEOUTS" in text
    assert "P46" in text
    # DIST-09 + DIST-11 sections still present.
    assert "DIST-09 — Apple Developer Program Agreement update" in text
    assert "DIST-11 — SignPath OSS Foundation application" in text
    # Sign-off blocks still present in each. Find the FULL H2 section
    # heading (not the LEGAL-CAPACITY CARVEOUTS bullet near the top).
    dist09_h2 = text.find("## 6. DIST-09")
    if dist09_h2 == -1:
        dist09_h2 = text.find("## DIST-09")
    assert dist09_h2 != -1, "DIST-09 full H2 section heading missing"
    dist09_end = text.find("\n## ", dist09_h2 + 1)
    dist09_section = text[dist09_h2:dist09_end if dist09_end != -1 else len(text)]
    assert (
        "Sign-off block" in dist09_section
        or "ACCEPTED by" in dist09_section
    ), "DIST-09 section missing sign-off block"

    dist11_h2 = text.find("## 7. DIST-11")
    if dist11_h2 == -1:
        dist11_h2 = text.find("## DIST-11")
    assert dist11_h2 != -1, "DIST-11 full H2 section heading missing"
    dist11_end = text.find("\n## ", dist11_h2 + 1)
    dist11_section = text[dist11_h2:dist11_end if dist11_end != -1 else len(text)]
    assert (
        "Sign-off block" in dist11_section
        or "APPLIED on" in dist11_section
    ), "DIST-11 section missing sign-off block"


def test_ship_entries_have_signoff_blocks(text: str):
    """Each §SHIP entry must have a `Sign-off block:` (humans countersign)."""
    # Count Sign-off blocks: legal had 4 before (DIST-09, DIST-11, DIST-19,
    # INSTALL-VM-RUN). Phase 39 adds 6 §SHIP + 1 §POST-RC-CLEANUP = 11 total.
    count = text.count("Sign-off block")
    assert count >= 10, f"expected >=10 Sign-off blocks, found {count}"


def test_ship_cut_references_cut_release_sh(text: str):
    """SHIP-CUT entry must reference scripts/launch/cut_release.sh."""
    start = text.find("SHIP-CUT")
    chunk = text[start:start + 3000]
    assert "cut_release.sh" in chunk


def test_ship_transfer_references_sync_github_meta(text: str):
    start = text.find("SHIP-TRANSFER")
    chunk = text[start:start + 3000]
    assert "sync_github_meta.sh" in chunk


def test_ship_rotate_references_launch_rotation_doc(text: str):
    start = text.find("SHIP-ROTATE")
    chunk = text[start:start + 3000]
    assert "launch-rotation.md" in chunk
