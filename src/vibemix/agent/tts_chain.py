# SPDX-License-Identifier: Apache-2.0
"""MOSS-only TTS factory for the live co-host.

The product voice has exactly one source: ``MossLocalTTS``. Direct and proxy
sessions both build the same local provider; cloud TTS keys are intentionally
ignored here so a missing or failing local voice cannot silently fall back to a
paid/provider voice.

The legacy OpenRouter audio-stream monkey patch stays at module load for
backward compatibility with older imports/tests, but this module no longer
instantiates OpenAI, Gemini-native, or Cartesia TTS providers.
"""

from __future__ import annotations

from typing import Literal

from livekit.agents import tts as agents_tts
from livekit.plugins.openai import tts as _openai_tts_mod

from vibemix.agent.config import OPENROUTER_TTS_MODEL

_openai_tts_mod.AUDIO_STREAM_MODELS.add(OPENROUTER_TTS_MODEL)


def _build_moss_chain() -> agents_tts.FallbackAdapter:
    """Build the only supported live TTS chain: local MOSS, one provider."""
    from vibemix.agent.local_tts import build_local_tts_adapter

    return build_local_tts_adapter()


def _build_direct_chain(
    gemini_api_key: str | None = None,
    openrouter_api_key: str | None = None,
    *,
    openrouter_enabled: bool = False,
    cartesia_api_key: str | None = None,
) -> agents_tts.FallbackAdapter:
    """Compatibility wrapper: direct TTS still resolves to MOSS only."""
    _ = (gemini_api_key, openrouter_api_key, openrouter_enabled, cartesia_api_key)
    return _build_moss_chain()


def build_tts_chain(
    *,
    gemini_api_key: str | None = None,
    openrouter_api_key: str | None = None,
    openrouter_enabled: bool = False,
    cartesia_api_key: str | None = None,
    mode: Literal["direct", "proxy"] = "direct",
    proxy_base_url: str | None = None,
    jwt: str | None = None,
) -> agents_tts.FallbackAdapter:
    """Build the live voice chain.

    ``mode`` is still accepted for the direct/proxy callers, but it no longer
    selects a provider. MOSS is the single source of TTS in every mode. If the
    local model is unavailable, ``build_local_tts_adapter`` raises a clear
    ``LocalTTSUnavailable`` instead of routing speech to a cloud fallback.
    """
    _ = (
        gemini_api_key,
        openrouter_api_key,
        openrouter_enabled,
        cartesia_api_key,
        proxy_base_url,
        jwt,
    )
    if mode not in {"direct", "proxy"}:
        raise ValueError(f"unknown mode: {mode}")
    return _build_moss_chain()
