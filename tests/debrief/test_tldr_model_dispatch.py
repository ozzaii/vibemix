# SPDX-License-Identifier: Apache-2.0
"""Plan 41-01 / Task 2 — debrief/tldr.py routes via ModelRouter.

Pins the contract that the migrating constants (DEBRIEF_TLDR_MODEL,
DEBRIEF_TTS_MODEL) come from ``vibemix.llm.model_router.resolve`` so a
future SKU bump is a one-file edit in ``_router_config.py``.
"""

from __future__ import annotations

from vibemix.debrief.tldr import DEBRIEF_TLDR_MODEL, DEBRIEF_TTS_MODEL
from vibemix.llm.model_router import resolve


def test_debrief_tldr_model_matches_router() -> None:
    """DEBRIEF_TLDR_MODEL is router-derived (debrief path)."""
    assert DEBRIEF_TLDR_MODEL == resolve("debrief")[0]


def test_debrief_tts_model_matches_router() -> None:
    """DEBRIEF_TTS_MODEL is router-derived (debrief_tts path)."""
    assert DEBRIEF_TTS_MODEL == resolve("debrief_tts")[0]


def test_debrief_tldr_model_is_3_pro_preview() -> None:
    """Smoke: the resolved id still equals the locked Wave-0-A1 id."""
    assert DEBRIEF_TLDR_MODEL == "gemini-3-pro-preview"


def test_debrief_tts_model_is_3_flash_tts_preview() -> None:
    """Smoke: the resolved TTS id still equals the locked id."""
    assert DEBRIEF_TTS_MODEL == "gemini-3-flash-tts-preview"
