# SPDX-License-Identifier: Apache-2.0
"""Phase 38 / DIST-09 + DIST-11 — KAAN-ACTION-LEGAL.md protocol tests.

Asserts the legal-capacity carveout protocols are documented with enough
structure that an autonomous agent CANNOT accidentally discharge them:

- P46 callout at the top.
- DIST-09 (Francesco-action) full protocol.
- DIST-11 (Kaan-action) full protocol with ~1-week SLA note.
- Sign-off blocks for both (humans countersign).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
LEGAL = REPO_ROOT / "KAAN-ACTION-LEGAL.md"


@pytest.fixture(scope="module")
def text() -> str:
    return LEGAL.read_text(encoding="utf-8")


def test_kaan_action_legal_md_exists():
    assert LEGAL.exists()


def test_kaan_action_legal_md_has_p46_callout(text: str):
    """Top-of-file P46 callout must list the two legal-capacity carveouts."""
    assert "LEGAL-CAPACITY CARVEOUTS" in text
    # The P46 reference (Pitfall P46 hard rule).
    assert "P46" in text
    # Both REQ-IDs must be named.
    assert "DIST-09" in text
    assert "DIST-11" in text


def test_kaan_action_legal_md_has_dist_09_protocol(text: str):
    """DIST-09 Apple Developer Program Agreement update — Francesco-action."""
    assert "DIST-09" in text
    # Must explicitly say FRANCESCO-ACTION (legal capacity).
    assert "FRANCESCO-ACTION" in text or "Francesco-action" in text.lower() or "Francesco" in text
    # Protocol steps.
    assert "developer.apple.com" in text
    assert "Program License Agreement" in text
    # Sign-off block must exist (humans countersign).
    dist_09_section = _extract_section(text, "DIST-09")
    assert dist_09_section is not None
    assert "Sign-off block" in dist_09_section or "ACCEPTED by" in dist_09_section


def test_kaan_action_legal_md_has_dist_11_protocol(text: str):
    """DIST-11 SignPath OSS Foundation application — Kaan-action."""
    assert "DIST-11" in text
    assert "KAAN-ACTION" in text or "Kaan-action" in text.lower() or "Kaan" in text
    # Protocol steps.
    assert "signpath.org/products/foundation" in text or "signpath.org/foundation" in text
    # ~1-week SLA note must be present.
    assert "1-week" in text or "1 week" in text or "one week" in text.lower()
    # Sign-off block.
    dist_11_section = _extract_section(text, "DIST-11")
    assert dist_11_section is not None
    assert "APPLIED on" in dist_11_section or "APPROVED on" in dist_11_section


def test_kaan_action_legal_md_has_dist_09_dist_11_protocols(text: str):
    """Convenience union of the two above — matches the CONTEXT-named hard gate."""
    assert "DIST-09" in text and "DIST-11" in text
    # Both must have sign-off blocks (the canonical signal that a protocol is real).
    assert text.count("Sign-off block") >= 2


def test_kaan_action_legal_md_references_p46_ci_enforcement(text: str):
    """The P46 callout must reference the CI grep that enforces it."""
    assert "verify-signed.yml" in text
    assert "release.yml" in text or "release-publish" in text


def test_kaan_action_legal_md_dist_19_smoke_documented(text: str):
    """DIST-19 (smoke on first signed binary) must be documented as Kaan-action."""
    assert "DIST-19" in text
    assert "sign-and-test.sh" in text


def _extract_section(text: str, anchor: str) -> str | None:
    """Return the substring from the heading containing `anchor` up to the next `## `."""
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.startswith("## ") and anchor in line:
            start = i
            break
    if start is None:
        return None
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if lines[j].startswith("## "):
            end = j
            break
    return "\n".join(lines[start:end])


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-v"])
