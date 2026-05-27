# SPDX-License-Identifier: Apache-2.0
"""Plan 41-01 / Task 2 — debrief/drills.py routes via ModelRouter."""

from __future__ import annotations

from vibemix.debrief.drills import DEBRIEF_DRILLS_MODEL
from vibemix.llm.model_router import resolve


def test_debrief_drills_model_matches_router() -> None:
    """drills shares the debrief router path with tldr."""
    assert DEBRIEF_DRILLS_MODEL == resolve("debrief")[0]


def test_debrief_drills_model_is_3_5_flash() -> None:
    """Smoke: resolved id follows the current debrief router SKU."""
    assert DEBRIEF_DRILLS_MODEL == "gemini-3.5-flash"
