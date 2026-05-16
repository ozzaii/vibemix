# SPDX-License-Identifier: Apache-2.0
"""Plan 41-01 / Task 2 — debrief/drills.py routes via ModelRouter."""

from __future__ import annotations

from vibemix.debrief.drills import DEBRIEF_DRILLS_MODEL
from vibemix.llm.model_router import resolve


def test_debrief_drills_model_matches_router() -> None:
    """drills shares the debrief router path with tldr — both Flex 3-Pro."""
    assert DEBRIEF_DRILLS_MODEL == resolve("debrief")[0]


def test_debrief_drills_model_is_3_pro_preview() -> None:
    """Smoke: resolved id is the locked Wave-0-A1 id."""
    assert DEBRIEF_DRILLS_MODEL == "gemini-3-pro-preview"
