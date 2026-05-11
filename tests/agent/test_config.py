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


def test_config_01_constants_match_v4() -> None:
    """CONFIG-01: byte-identical strings to v4:97-104."""
    assert LLM_MODEL == "gemini-3-flash-preview"
    assert TTS_MODEL == "gemini-3.1-flash-tts-preview"
    assert TTS_FALLBACK_MODEL == "gemini-2.5-flash-preview-tts"
    assert OPENROUTER_TTS_MODEL == "google/gemini-3.1-flash-tts-preview"
    assert VOICE == "Achird"
    assert INPUT_DEVICE == "BlackHole 2ch"
    assert OUTPUT_DEVICE == "AI Capture"
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
