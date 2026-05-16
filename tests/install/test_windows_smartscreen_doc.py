# SPDX-License-Identifier: Apache-2.0
"""Phase 33 / Plan 33-04 — Windows SmartScreen doc gate.

The doc at ``docs/install/windows-smartscreen.md`` is the user-facing
explainer for the Defender prompt new Windows users see. Two gates:

1. The doc EXISTS and mentions "SmartScreen" + "More info" + "Run anyway"
   (the three primary keywords a Windows user searches for).
2. The doc DOES NOT promise a warning-free install. Defender reputation
   building is outside our control; promising "no warning" would be
   dishonest and trip the gsd-autonomous quality bar.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DOC_PATH = REPO_ROOT / "docs" / "install" / "windows-smartscreen.md"


def test_doc_exists_and_mentions_smartscreen() -> None:
    assert DOC_PATH.exists(), f"missing: {DOC_PATH}"
    body = DOC_PATH.read_text(encoding="utf-8")
    body_lower = body.lower()
    # Must mention SmartScreen by name.
    assert "smartscreen" in body_lower, (
        "windows-smartscreen.md must mention 'SmartScreen' by name"
    )
    # Must walk the user through the actual UX path.
    assert "more info" in body_lower, (
        "doc must mention the 'More info' link the user has to click"
    )
    assert "run anyway" in body_lower, (
        "doc must mention the 'Run anyway' button after More info expands"
    )


def test_doc_does_not_promise_no_warning() -> None:
    """Honesty gate: we never claim the install is warning-free."""
    body = DOC_PATH.read_text(encoding="utf-8").lower()
    # The three phrasings a marketing-driven rewrite would slip in.
    forbidden_phrases = [
        "no warning",
        "no smartscreen prompt",
        "warning-free",
        "never see a warning",
        "no defender prompt",
    ]
    for phrase in forbidden_phrases:
        # Allow the phrase only if it appears under an explicit negation
        # ("does not promise a warning-free install") — we check that the
        # phrase, if present at all, is on a line that ALSO contains a
        # negation marker.
        if phrase in body:
            lines = [line for line in body.split("\n") if phrase in line]
            for line in lines:
                # If we see "warning-free", the line must explicitly say
                # we DO NOT promise it (honesty marker).
                assert (
                    "not promise" in line
                    or "does not" in line
                    or "do not" in line
                    or "doesn't" in line
                ), (
                    f"doc line contains '{phrase}' without a negation marker: {line!r}"
                )


def test_doc_links_to_phase_38_signing() -> None:
    """Doc should reference Phase 38 / SignPath as the long-term fix so
    users understand the timeline."""
    body = DOC_PATH.read_text(encoding="utf-8").lower()
    assert "signpath" in body or "phase 38" in body, (
        "doc should reference SignPath or Phase 38 — the long-term fix"
    )
