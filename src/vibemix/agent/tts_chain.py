# SPDX-License-Identifier: Apache-2.0
"""Gemini-native TTS chain with optional OpenRouter standby + factory.

Verbatim port of cohost_v4.py:62-66 (monkey-patch) + cohost_v4.py:1991-2017
(factory body). Phase 5 extends build_tts_chain with `mode` dispatch. Direct
mode uses Gemini native TTS first; proxy mode routes to
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

import asyncio
import os
from typing import Literal

from livekit.agents import tts as agents_tts
from livekit.plugins import openai as openai_plugin
from livekit.plugins.openai import tts as _openai_tts_mod

# Plan 41-01: import OPENROUTER_TTS_MODEL FIRST so the monkey-patch below
# uses the router-derived constant rather than an inline literal. The v4
# load-order invariant (monkey-patch before any openai_plugin.TTS init) is
# preserved — `vibemix.agent.config` is import-safe and triggers no plugin
# instantiation.
from vibemix.agent.config import (
    CARTESIA_TTS_MODEL,
    CARTESIA_VOICE,
    OPENROUTER_TTS_MODEL,
    TTS_FALLBACK_MODEL,
    TTS_MODEL,
    VOICE,
)

# OpenRouter's Gemini TTS returns raw audio stream, not SSE. Force the
# plugin's AudioChunkedStream path (used for tts-1) for our model.
# Source string is the router-derived OPENROUTER_TTS_MODEL — never inline.
_openai_tts_mod.AUDIO_STREAM_MODELS.add(OPENROUTER_TTS_MODEL)

from vibemix.agent._livekit_google_slim import gemini_native_tts_class  # noqa: E402

_TTS_INSTRUCTIONS = "Casual studio friend, brief, natural — no theatrics, no announcer voice."


def _live_http_session():
    """Return an aiohttp ClientSession bound to the running loop, else ``None``.

    The livekit Cartesia plugin, given no ``http_session``, falls back to
    ``utils.http_context.http_session()`` — which REQUIRES a livekit agent-worker
    "job context". vibemix runs its OWN asyncio loop (not the worker api), so that
    fallback raises ``RuntimeError: Attempted to use an http session outside of a
    job context`` the moment the plugin's connection pool prewarms — and the
    co-host goes mute (verified 2026-05-30 on the frozen sidecar: boot reached
    ``-> agent started.`` but every Cartesia connect crashed). Passing our own
    ClientSession makes the plugin self-sufficient.

    Returns ``None`` when there is no running loop (unit tests / pure construction)
    so plugin construction stays loop-free there; the live path always builds the
    chain from inside ``async def main()`` so a session is created then.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return None
    import aiohttp

    return aiohttp.ClientSession()


def _build_direct_chain(
    gemini_api_key: str,
    openrouter_api_key: str | None,
    *,
    openrouter_enabled: bool = False,
    cartesia_api_key: str | None = None,
) -> agents_tts.FallbackAdapter:
    """Build the direct TTS chain.

    Returns a FallbackAdapter. When the local voice is explicitly enabled
    (``VIBEMIX_LOCAL_TTS`` truthy plus the model cached), the chain is
    MOSS-TTS-Nano ONLY, no paid fallback: the
    point is zero TTS cost and zero embedded API key (benched 71ms TTFT / 0.18 RTF
    on M4 Max CPU, torch-free ONNX, never-mute once cached). Only when the local
    voice is OFF (``VIBEMIX_LOCAL_TTS=0`` or no cached model) does the paid chain
    build:
        optional (Cartesia Sonic, when ``cartesia_api_key`` is set)
          -> secondary (Gemini native TTS_MODEL)
          -> tertiary (Gemini native TTS_FALLBACK_MODEL)
          -> optional quaternary (OpenRouter standby).

    Cartesia leads that paid chain when keyed (2026-05-30 — Gemini TTS returns
    'No audio content generated' live, muting the co-host); the Gemini natives
    stay as graceful fallback so an outage of the lead voice never silences it.

    OpenRouter is no longer enabled just because ``OPENROUTER_API_KEY`` is
    present. A credit-exhausted OpenRouter account can otherwise block every
    spoken turn before native Gemini TTS gets a chance to run. Keep it as an
    explicit standby via ``openrouter_enabled``.
    """
    chain: list = []
    # Local MOSS-TTS-Nano is THE voice when explicitly enabled
    # (VIBEMIX_LOCAL_TTS truthy) + cached: free, key-free, never-mute (benched
    # 71ms TTFT / 0.18 RTF, M4 Max CPU, torch-free ONNX). When it leads we
    # ship NO paid fallback and return immediately - the whole point is zero TTS
    # cost + zero embedded API key. Set VIBEMIX_LOCAL_TTS=0 to fall through to the
    # Cartesia/Gemini chain below. Lazy-import so numpy/onnxruntime load only when
    # the local voice is actually used — keeps tts_chain import-light.
    from vibemix.agent.local_tts import local_tts_enabled

    if local_tts_enabled():
        from vibemix.agent.local_tts import MossLocalTTS

        _moss = MossLocalTTS()
        _moss.prewarm()  # start the ~728MB load in the background so reaction #1 is warm
        return agents_tts.FallbackAdapter(tts=[_moss], max_retry_per_tts=1)
    # Self-activate from the env when the caller didn't thread a key — dropping
    # CARTESIA_API_KEY in .env is enough to switch the live voice to Cartesia.
    cartesia_api_key = cartesia_api_key or os.environ.get("CARTESIA_API_KEY") or None
    # Cartesia (Sonic) leads when a key is present — the fast, working primary
    # voice. Lazy-import so the plugin is only required when actually used.
    if cartesia_api_key:
        from livekit.plugins import cartesia

        chain.append(
            cartesia.TTS(
                model=CARTESIA_TTS_MODEL,
                voice=CARTESIA_VOICE,
                api_key=cartesia_api_key,
                # Self-supplied session — vibemix has no livekit job context to
                # borrow one from (see _live_http_session). None when built
                # loop-free (tests) keeps the plugin's lazy default.
                http_session=_live_http_session(),
            )
        )
    gemini_tts = gemini_native_tts_class()
    chain.append(
        gemini_tts(
            model=TTS_MODEL,
            voice_name=VOICE,
            api_key=gemini_api_key,
            instructions=_TTS_INSTRUCTIONS,
        )
    )
    chain.append(
        gemini_tts(
            model=TTS_FALLBACK_MODEL,
            voice_name=VOICE,
            api_key=gemini_api_key,
            instructions=_TTS_INSTRUCTIONS,
        )
    )
    if openrouter_enabled and openrouter_api_key:
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
    return agents_tts.FallbackAdapter(tts=chain, max_retry_per_tts=1)


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
    """Factory entry — dispatches on mode.

    direct: requires gemini_api_key (OpenRouter standby is explicit opt-in).
    proxy:  requires proxy_base_url AND jwt.

    Per CONTEXT decision (locked): missing required args raise ValueError
    immediately — NEVER silent fallback proxy → direct.
    """
    if mode == "direct":
        if not gemini_api_key:
            raise ValueError("direct mode requires gemini_api_key")
        return _build_direct_chain(
            gemini_api_key,
            openrouter_api_key,
            openrouter_enabled=openrouter_enabled,
            cartesia_api_key=cartesia_api_key,
        )
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
