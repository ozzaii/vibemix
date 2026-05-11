# SPDX-License-Identifier: Apache-2.0
"""vibemix.agent — LiveKit cascade agent layer.

Phase 4 ships the DJCoHostAgent (multimodal llm_node override calling
google.genai.aio.models.generate_content_stream with the last
INVOKE_AUDIO_SECONDS of audio attached as a Part), the
PlaybackQueueAudioOutput TTS sink, the SYSTEM_INSTRUCTION persona, the LLM
factory, and the OpenRouter-primary TTS chain (with a load-bearing module-load
monkey-patch that puts the OpenRouter Gemini TTS model on LiveKit's
AudioChunkedStream path).

Phase 5 adds:
- ``install_uuid.get_or_create_install_uuid()`` — OS keychain (with file
  fallback + null-backend detection per Pitfall 6).
- ``jwt_cache.get_or_refresh_jwt(install_uuid, proxy_base_url, client_version)``
  — keychain-cached JWT, refreshed via /api/vibemix/v1/register when within
  7 days of expiry.
- ``proxy_client.build_proxy_genai_client(jwt, proxy_base_url)`` +
  ``build_proxy_tts_chain(jwt, proxy_base_url)``.
- ``build_llm(api_key, *, mode, proxy_base_url, jwt)`` extended with mode
  dispatch (direct = Phase 4 verbatim; proxy = http_options-pointed at proxy).
- ``build_tts_chain(*, gemini_api_key, openrouter_api_key, mode, ...)`` same.
"""

from __future__ import annotations

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
from vibemix.agent.dj_cohost import DJCoHostAgent
from vibemix.agent.install_uuid import get_or_create_install_uuid
from vibemix.agent.jwt_cache import get_or_refresh_jwt
from vibemix.agent.llm_factory import build_llm
from vibemix.agent.persona import SYSTEM_INSTRUCTION
from vibemix.agent.playback_sink import PlaybackQueueAudioOutput
from vibemix.agent.proxy_client import (
    build_proxy_genai_client,
    build_proxy_tts_chain,
)
from vibemix.agent.tts_chain import build_tts_chain

__all__ = [
    "INPUT_DEVICE",
    "LLM_MODEL",
    "MIC_DEVICE",
    "OPENROUTER_TTS_MODEL",
    "OUTPUT_DEVICE",
    "SYSTEM_INSTRUCTION",
    "TTS_FALLBACK_MODEL",
    "TTS_MODEL",
    "VOICE",
    "DJCoHostAgent",
    "PlaybackQueueAudioOutput",
    "build_llm",
    "build_proxy_genai_client",
    "build_proxy_tts_chain",
    "build_tts_chain",
    "get_or_create_install_uuid",
    "get_or_refresh_jwt",
]
