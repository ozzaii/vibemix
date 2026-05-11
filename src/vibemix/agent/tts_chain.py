# SPDX-License-Identifier: Apache-2.0
"""OpenRouter-primary TTS chain with module-load monkey-patch + factory.

Verbatim port of cohost_v4.py:62-66 (monkey-patch) + cohost_v4.py:1991-2017
(factory body). Phase 5 extends build_tts_chain with `mode` dispatch — direct
mode preserves the Phase 4 byte-identical behavior; proxy mode routes to
`build_proxy_tts_chain` (single-entry chain via openai_plugin.TTS pointed at
the proxy's /v1).

The monkey-patch is LOAD-BEARING — it MUST be applied at module-load time,
BEFORE any ``openai_plugin.TTS`` instantiation. OpenRouter's Gemini TTS
returns raw PCM audio, not SSE; without this patch the LiveKit OpenAI plugin
selects the SSE path and fails to decode. The proxy also emits PCM at
/v1/audio/speech, so the same patch covers proxy mode too.

The v4 import order on lines 62-66 pins this invariant — do NOT reorder.
"""

from __future__ import annotations

from typing import Literal

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


def _build_direct_chain(
    gemini_api_key: str, openrouter_api_key: str | None
) -> agents_tts.FallbackAdapter:
    """Phase 4 verbatim — port of v4:1991-2017.

    Returns a FallbackAdapter:
        primary (OpenRouter)  -> secondary (Gemini native TTS_MODEL)
                              -> tertiary (Gemini native TTS_FALLBACK_MODEL).

    When ``openrouter_api_key`` is None or empty, the OpenRouter entry is
    omitted and the chain starts at the secondary.
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


def build_tts_chain(
    *,
    gemini_api_key: str | None = None,
    openrouter_api_key: str | None = None,
    mode: Literal["direct", "proxy"] = "direct",
    proxy_base_url: str | None = None,
    jwt: str | None = None,
) -> agents_tts.FallbackAdapter:
    """Factory entry — dispatches on mode.

    direct: requires gemini_api_key (openrouter_api_key optional).
    proxy:  requires proxy_base_url AND jwt.

    Per CONTEXT decision (locked): missing required args raise ValueError
    immediately — NEVER silent fallback proxy → direct.
    """
    if mode == "direct":
        if not gemini_api_key:
            raise ValueError("direct mode requires gemini_api_key")
        return _build_direct_chain(gemini_api_key, openrouter_api_key)
    if mode == "proxy":
        missing: list[str] = []
        if not proxy_base_url:
            missing.append("proxy_base_url")
        if not jwt:
            missing.append("jwt")
        if missing:
            raise ValueError(f"proxy mode requires {', '.join(missing)}")
        # Local import — avoids a circular import (proxy_client imports tts_chain
        # at module-load to trigger the monkey-patch).
        from vibemix.agent.proxy_client import build_proxy_tts_chain

        return build_proxy_tts_chain(jwt=jwt, proxy_base_url=proxy_base_url)  # type: ignore[arg-type]
    raise ValueError(f"unknown mode: {mode}")
