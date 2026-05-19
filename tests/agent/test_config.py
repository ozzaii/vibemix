# SPDX-License-Identifier: Apache-2.0
"""Agent-layer config constants — CONFIG-01 + PKG-01."""

from __future__ import annotations

import vibemix.agent as vagent
from vibemix.agent.config import (
    INPUT_DEVICE,
    LLM_MODEL,
    MIC_DEVICE,
    OPENROUTER_TTS_MODEL,
    OUTPUT_DEVICE,
    TTS_FALLBACK_MODEL,
    TTS_MODEL,
    VOICE,
)


def test_config_01_constants_pinned() -> None:
    """CONFIG-01: agent constants are pinned to the current shipped values.

    Originally byte-identity to cohost_v4.py was the contract. v4 was
    retired into ``.planning/research/v3-shipped/`` once its behavior had
    been ported into this package, so the test now pins the
    package-side source of truth directly. Device defaults are settable
    per-machine via the calibration wizard; the strings here are the
    factory values.
    """
    assert LLM_MODEL == "gemini-3-flash-preview"
    assert TTS_MODEL == "gemini-3.1-flash-tts-preview"
    assert TTS_FALLBACK_MODEL == "gemini-2.5-flash-preview-tts"
    assert OPENROUTER_TTS_MODEL == "google/gemini-3.1-flash-tts-preview"
    assert VOICE == "Achird"
    assert INPUT_DEVICE == "BlackHole 2ch"
    assert OUTPUT_DEVICE == "MacBook Pro Speakers"
    assert MIC_DEVICE == "MacBook Pro Microphone"


def test_pkg_01_imports_from_package_root() -> None:
    """PKG-01: all the agent-layer constants + persona + build_llm resolve
    from `vibemix.agent`."""
    from vibemix.agent import (
        INPUT_DEVICE as p_input,
    )
    from vibemix.agent import (
        LLM_MODEL as p_llm,
    )
    from vibemix.agent import (
        MIC_DEVICE as p_mic,
    )
    from vibemix.agent import (
        OPENROUTER_TTS_MODEL as p_or,
    )
    from vibemix.agent import (
        OUTPUT_DEVICE as p_out,
    )
    from vibemix.agent import (
        SYSTEM_INSTRUCTION as p_persona,
    )
    from vibemix.agent import (
        TTS_FALLBACK_MODEL as p_tts_fb,
    )
    from vibemix.agent import (
        TTS_MODEL as p_tts,
    )
    from vibemix.agent import (
        VOICE as p_voice,
    )
    from vibemix.agent import (
        build_llm as p_build_llm,
    )

    assert p_llm == LLM_MODEL
    assert p_tts == TTS_MODEL
    assert p_tts_fb == TTS_FALLBACK_MODEL
    assert p_or == OPENROUTER_TTS_MODEL
    assert p_voice == VOICE
    assert p_input == INPUT_DEVICE
    assert p_out == OUTPUT_DEVICE
    assert p_mic == MIC_DEVICE
    assert isinstance(p_persona, str)
    assert callable(p_build_llm)


def test_pkg_01_all_exports_includes_required_names() -> None:
    """__all__ includes at minimum the PKG-01 names."""
    expected = {
        "SYSTEM_INSTRUCTION",
        "build_llm",
        "LLM_MODEL",
        "TTS_MODEL",
        "TTS_FALLBACK_MODEL",
        "OPENROUTER_TTS_MODEL",
        "VOICE",
        "INPUT_DEVICE",
        "OUTPUT_DEVICE",
        "MIC_DEVICE",
    }
    assert expected.issubset(set(vagent.__all__))


# ---------------------------------------------------------------------------
# Plan 41-01 — ModelRouter dispatch (LAT-01, LAT-07)
# ---------------------------------------------------------------------------


def test_41_01_llm_model_matches_router() -> None:
    """LLM_MODEL is router-derived (live_coach path)."""
    from vibemix.llm.model_router import resolve

    assert LLM_MODEL == resolve("live_coach")[0]


def test_41_01_tts_model_matches_router() -> None:
    """TTS_MODEL is router-derived (live_coach_tts path)."""
    from vibemix.llm.model_router import resolve

    assert TTS_MODEL == resolve("live_coach_tts")[0]


def test_41_01_tts_fallback_model_matches_router() -> None:
    """TTS_FALLBACK_MODEL is router-derived (live_coach_tts_fallback path)."""
    from vibemix.llm.model_router import resolve

    assert TTS_FALLBACK_MODEL == resolve("live_coach_tts_fallback")[0]


def test_41_01_openrouter_tts_model_matches_router() -> None:
    """OPENROUTER_TTS_MODEL is router-derived (live_coach_tts_openrouter path).

    Backward-compat: the existing tts_chain monkey-patch consumes this
    string by reference (via ``OPENROUTER_TTS_MODEL`` import), so the
    AUDIO_STREAM_MODELS set in livekit.plugins.openai.tts still contains
    the same string post-migration.
    """
    from livekit.plugins.openai import tts as openai_tts_mod

    from vibemix.llm.model_router import resolve

    assert OPENROUTER_TTS_MODEL == resolve("live_coach_tts_openrouter")[0]
    # Importing vibemix.agent.tts_chain triggers the monkey-patch at module
    # load. The string must still be in AUDIO_STREAM_MODELS afterwards.
    import vibemix.agent.tts_chain  # noqa: F401 — module-load side effect

    assert OPENROUTER_TTS_MODEL in openai_tts_mod.AUDIO_STREAM_MODELS


def test_41_01_live_coach_service_tier_exposed() -> None:
    """LIVE_COACH_SERVICE_TIER exposes the ServiceTier so callers that
    need tier dispatch don't have to do a second resolve() call.

    Per CONTEXT LAT-07: live_coach lives on the Standard tier.
    """
    from google.genai.types import ServiceTier

    from vibemix.agent.config import LIVE_COACH_SERVICE_TIER

    assert LIVE_COACH_SERVICE_TIER == ServiceTier.STANDARD
