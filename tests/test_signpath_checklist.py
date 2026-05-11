# SPDX-License-Identifier: Apache-2.0
"""Smoke test that .planning/signpath-application.md has all 9 form sections."""

from __future__ import annotations

from pathlib import Path

CHECKLIST_PATH = Path(__file__).resolve().parent.parent / ".planning" / "signpath-application.md"

REQUIRED_SECTION_MARKERS = [
    "1. Basic",
    "2. Repo",
    "3. Distribution",
    "4. Privacy",
    "5. Wikipedia",
    # Section 6 may be titled "Trust" or "Verification" depending on form rev;
    # check either substring.
    ("6. Trust", "6. Verification"),
    "7. Technical",
    "8. Contact",
    "9. Terms",
]


def test_signpath_checklist_complete():
    assert CHECKLIST_PATH.exists(), f"{CHECKLIST_PATH} missing"
    text = CHECKLIST_PATH.read_text().lower()
    missing: list[str] = []
    for marker in REQUIRED_SECTION_MARKERS:
        if isinstance(marker, tuple):
            if not any(m.lower() in text for m in marker):
                missing.append(" / ".join(marker))
        else:
            if marker.lower() not in text:
                missing.append(marker)
    assert not missing, "Missing SignPath section markers: " + ", ".join(missing)
    assert "ozzaii/vibemix" in CHECKLIST_PATH.read_text(), (
        "Repo URL must be ozzaii/vibemix throughout the checklist"
    )
