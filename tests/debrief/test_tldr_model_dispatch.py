# SPDX-License-Identifier: Apache-2.0
"""Plan 41-01 / MOSS-only update — debrief/tldr.py routing contracts.

Pins the contract that debrief text generation still comes from
``vibemix.llm.model_router.resolve`` while debrief narration audio does not
resolve a Gemini TTS route. MOSS is the single product voice source.
"""

from __future__ import annotations

from vibemix.debrief.tldr import DEBRIEF_TLDR_MODEL, DEBRIEF_TTS_PROVIDER
from vibemix.llm.model_router import resolve


def test_debrief_tldr_model_matches_router() -> None:
    """DEBRIEF_TLDR_MODEL is router-derived (debrief path)."""
    assert DEBRIEF_TLDR_MODEL == resolve("debrief")[0]


def test_debrief_tts_provider_is_moss_local() -> None:
    """Debrief audio uses the local MOSS provider, not a Gemini TTS route."""
    assert DEBRIEF_TTS_PROVIDER == "moss-local"


def test_debrief_tldr_model_is_3_5_flash() -> None:
    """Smoke: the resolved id follows the current debrief router SKU."""
    assert DEBRIEF_TLDR_MODEL == "gemini-3.5-flash"


def test_debrief_module_no_longer_exports_gemini_tts_model() -> None:
    """No debrief-level Gemini TTS model constant should reappear."""
    import vibemix.debrief.tldr as tldr

    assert not hasattr(tldr, "DEBRIEF_TTS_MODEL")
