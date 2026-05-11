# SPDX-License-Identifier: Apache-2.0
"""OpenRouter-primary TTS chain with module-load monkey-patch + factory.

Verbatim port of cohost_v4.py:62-66 (monkey-patch) + cohost_v4.py:1991-2017
(factory body).

The monkey-patch is LOAD-BEARING — it MUST be applied at module-load time,
BEFORE any ``openai_plugin.TTS`` instantiation. OpenRouter's Gemini TTS
returns raw PCM audio, not SSE; without this patch the LiveKit OpenAI plugin
selects the SSE path and fails to decode.

The v4 import order on lines 62-66 pins this invariant — do NOT reorder.
"""

from __future__ import annotations

from livekit.agents import tts as agents_tts
from livekit.plugins import openai as openai_plugin
from livekit.plugins.openai import tts as _openai_tts_mod

# OpenRouter's Gemini TTS returns raw audio stream, not SSE. Force the
# plugin's AudioChunkedStream path (used for tts-1) for our model.
_openai_tts_mod.AUDIO_STREAM_MODELS.add("google/gemini-3.1-flash-tts-preview")

from livekit.plugins.google.beta import gemini_tts as gemini_native_tts  # noqa: E402

from vibemix.agent.config import (  # noqa: E402
    OPENROUTER_TTS_MODEL,
    TTS_FALLBACK_MODEL,
    TTS_MODEL,
    VOICE,
)

_TTS_INSTRUCTIONS = "Casual studio friend, brief, natural — no theatrics, no announcer voice."


def build_tts_chain(
    *,
    gemini_api_key: str,
    openrouter_api_key: str | None = None,
) -> agents_tts.FallbackAdapter:
    """Verbatim port of v4:1991-2017. Returns a FallbackAdapter:

        primary (OpenRouter)  -> secondary (Gemini native TTS_MODEL)
                              -> tertiary (Gemini native TTS_FALLBACK_MODEL).

    When ``openrouter_api_key`` is None or empty, the OpenRouter entry is
    omitted and the chain starts at the secondary. Empty-string handling is
    explicit so callers can pass ``os.getenv("OPENROUTER_API_KEY")`` directly
    without normalizing.
    """
    chain: list = []
    if openrouter_api_key:
        chain.append(
            openai_plugin.TTS(
                model=OPENROUTER_TTS_MODEL,
                voice=VOICE,
                api_key=openrouter_api_key,
                base_url="https://openrouter.ai/api/v1",
                response_format="pcm",
                instructions=_TTS_INSTRUCTIONS,
            )
        )
    chain.append(
        gemini_native_tts.TTS(
            model=TTS_MODEL,
            voice_name=VOICE,
            api_key=gemini_api_key,
            instructions=_TTS_INSTRUCTIONS,
        )
    )
    chain.append(
        gemini_native_tts.TTS(
            model=TTS_FALLBACK_MODEL,
            voice_name=VOICE,
            api_key=gemini_api_key,
            instructions=_TTS_INSTRUCTIONS,
        )
    )
    return agents_tts.FallbackAdapter(tts=chain, max_retry_per_tts=1)
