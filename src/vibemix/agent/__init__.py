# SPDX-License-Identifier: Apache-2.0
"""vibemix.agent — LiveKit cascade agent layer.

Phase 4 ships the DJCoHostAgent (multimodal llm_node override calling
google.genai.aio.models.generate_content_stream with the last
INVOKE_AUDIO_SECONDS of audio attached as a Part), the
PlaybackQueueAudioOutput TTS sink, the SYSTEM_INSTRUCTION persona, the LLM
factory, and the MOSS-only local TTS chain.

Phase 5 adds:
- ``install_uuid.get_or_create_install_uuid()`` — OS keychain (with file
  fallback + null-backend detection per Pitfall 6).
- ``jwt_cache.get_or_refresh_jwt(install_uuid, proxy_base_url, client_version)``
  — keychain-cached JWT, refreshed via /api/vibemix/v1/register when within
  7 days of expiry.
- ``proxy_client.build_proxy_genai_client(jwt, proxy_base_url)`` plus the
  MOSS-only ``build_proxy_tts_chain(jwt, proxy_base_url)`` compatibility shim.
- ``build_llm(api_key, *, mode, proxy_base_url, jwt)`` extended with mode
  dispatch (direct = Phase 4 verbatim; proxy = http_options-pointed at proxy).
- ``build_tts_chain(*, mode, ...)`` accepts old direct/proxy arguments but
  always resolves to the single MOSS provider.
"""

from __future__ import annotations

from vibemix.agent.config import (
    INPUT_DEVICE,
    LLM_MODEL,
    MIC_DEVICE,
    OUTPUT_DEVICE,
    TTS_FALLBACK_MODEL,
    TTS_MODEL,
    VOICE,
)
from vibemix.agent.persona import SYSTEM_INSTRUCTION

__all__ = [
    "INPUT_DEVICE",
    "LLM_MODEL",
    "MIC_DEVICE",
    "OUTPUT_DEVICE",
    "SYSTEM_INSTRUCTION",
    "TTS_FALLBACK_MODEL",
    "TTS_MODEL",
    "VOICE",
    "DJCoHostAgent",
    "PlaybackQueueAudioOutput",
    "ProxyUnavailable",
    "build_llm",
    "build_proxy_genai_client",
    "build_proxy_tts_chain",
    "build_tts_chain",
    "classify_proxy_error",
    "get_or_create_install_uuid",
    "get_or_refresh_jwt",
    "probe_proxy_health",
]

_LAZY_EXPORTS = {
    "DJCoHostAgent": ("vibemix.agent.dj_cohost", "DJCoHostAgent"),
    "PlaybackQueueAudioOutput": ("vibemix.agent.playback_sink", "PlaybackQueueAudioOutput"),
    "ProxyUnavailable": ("vibemix.agent.proxy_client", "ProxyUnavailable"),
    "build_llm": ("vibemix.agent.llm_factory", "build_llm"),
    "build_proxy_genai_client": ("vibemix.agent.proxy_client", "build_proxy_genai_client"),
    "build_proxy_tts_chain": ("vibemix.agent.proxy_client", "build_proxy_tts_chain"),
    "build_tts_chain": ("vibemix.agent.tts_chain", "build_tts_chain"),
    "classify_proxy_error": ("vibemix.agent.proxy_client", "classify_proxy_error"),
    "get_or_create_install_uuid": ("vibemix.agent.install_uuid", "get_or_create_install_uuid"),
    "get_or_refresh_jwt": ("vibemix.agent.jwt_cache", "get_or_refresh_jwt"),
    "probe_proxy_health": ("vibemix.agent.proxy_client", "probe_proxy_health"),
}


def __getattr__(name: str):
    """Lazily expose cohost-only modules without taxing library/model CLIs."""
    try:
        module_name, attr = _LAZY_EXPORTS[name]
    except KeyError as exc:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc
    from importlib import import_module

    value = getattr(import_module(module_name), attr)
    globals()[name] = value
    return value
