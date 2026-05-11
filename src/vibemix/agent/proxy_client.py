# SPDX-License-Identifier: Apache-2.0
"""Proxy-mode genai + TTS client builders.

Per RESEARCH Q1 verified: genai.Client(http_options=HttpOptions(base_url=...,
headers={Authorization: Bearer JWT})) is the canonical pattern. The SDK's
generate_content_stream(...) works unchanged once base_url + headers are set.

Per RESEARCH Q1 TTS: livekit-plugins-openai TTS(base_url=...) threads the URL
into AsyncOpenAI client. The proxy emits OpenRouter-compatible PCM at
/v1/audio/speech — the existing OpenRouter monkey-patch (Phase 4 module-load
side effect of vibemix.agent.tts_chain) ALSO applies in proxy mode because
the proxy emits identical PCM body shape.
"""

from __future__ import annotations

# Trigger the OpenRouter monkey-patch — load-bearing module-load side effect.
# build_proxy_tts_chain relies on AUDIO_STREAM_MODELS containing
# "google/gemini-3.1-flash-tts-preview".
import vibemix.agent.tts_chain  # noqa: F401  isort: skip
from google import genai
from google.genai import types
from livekit.agents import tts as agents_tts
from livekit.plugins import openai as openai_plugin

from vibemix.agent.config import OPENROUTER_TTS_MODEL, VOICE

_TTS_INSTRUCTIONS = "Casual studio friend, brief, natural — no theatrics, no announcer voice."


def build_proxy_genai_client(jwt: str, proxy_base_url: str) -> genai.Client:
    """Build a genai.Client pointed at the vibemix proxy.

    The SDK's generate_content_stream(...) works unchanged once base_url and
    Authorization header are set via http_options.
    """
    return genai.Client(
        api_key="vibemix-proxy",  # dummy; proxy ignores x-goog-api-key
        http_options=types.HttpOptions(
            base_url=proxy_base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {jwt}"},
            timeout=120_000,  # ms
        ),
    )


def build_proxy_tts_chain(
    jwt: str, proxy_base_url: str, voice: str = VOICE
) -> agents_tts.FallbackAdapter:
    """Single-entry FallbackAdapter via openai_plugin.TTS pointed at proxy/v1.

    No Gemini-native fallback on the client side — the proxy handles upstream
    fallback internally (circuit breaker + future Gemini-native fallback route).
    """
    return agents_tts.FallbackAdapter(
        tts=[
            openai_plugin.TTS(
                model=OPENROUTER_TTS_MODEL,
                voice=voice,
                api_key=jwt,
                base_url=f"{proxy_base_url.rstrip('/')}/v1",
                response_format="pcm",
                instructions=_TTS_INSTRUCTIONS,
            ),
        ],
        max_retry_per_tts=1,
    )
