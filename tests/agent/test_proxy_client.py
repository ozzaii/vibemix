# SPDX-License-Identifier: Apache-2.0
"""PROXY-01..04 — build_proxy_genai_client + build_proxy_tts_chain."""

from __future__ import annotations

from livekit.agents import tts as agents_tts
from livekit.plugins import openai as openai_plugin

from vibemix.agent.proxy_client import build_proxy_genai_client, build_proxy_tts_chain


def test_proxy_01_genai_client_carries_base_url_and_bearer():
    """PROXY-01: genai.Client has base_url + Authorization header set."""
    c = build_proxy_genai_client(jwt="jwt-x", proxy_base_url="https://api.altidus.world")
    # The client stashes its http_options on its API client
    ho = c._api_client._http_options
    assert ho.base_url == "https://api.altidus.world"
    assert ho.headers["Authorization"] == "Bearer jwt-x"


def test_proxy_02_trailing_slash_stripped():
    c = build_proxy_genai_client(jwt="jwt-x", proxy_base_url="https://api.altidus.world/")
    ho = c._api_client._http_options
    assert ho.base_url == "https://api.altidus.world"


def test_proxy_03_tts_chain_single_entry(mocker):
    """PROXY-03: build_proxy_tts_chain returns 1-entry FallbackAdapter pointed at proxy/v1."""
    mocker.patch.object(openai_plugin.TTS, "__init__", return_value=None)
    mocker.patch.object(agents_tts.FallbackAdapter, "__init__", return_value=None)

    build_proxy_tts_chain(jwt="jwt-x", proxy_base_url="https://api.altidus.world")

    fa_kwargs = agents_tts.FallbackAdapter.__init__.call_args.kwargs
    chain = fa_kwargs["tts"]
    assert len(chain) == 1
    assert fa_kwargs["max_retry_per_tts"] == 1

    tts_kw = openai_plugin.TTS.__init__.call_args.kwargs
    assert tts_kw["model"] == "google/gemini-3.1-flash-tts-preview"
    assert tts_kw["base_url"] == "https://api.altidus.world/v1"
    assert tts_kw["api_key"] == "jwt-x"
    assert tts_kw["response_format"] == "pcm"


def test_proxy_04_monkey_patch_active_after_proxy_client_import():
    """PROXY-04: importing proxy_client triggers the OpenRouter monkey-patch
    via the explicit `import vibemix.agent.tts_chain` at the top of
    proxy_client.py — so AUDIO_STREAM_MODELS still contains the model after a
    fresh import."""
    from livekit.plugins.openai import tts as t

    import vibemix.agent.proxy_client  # noqa: F401

    assert "google/gemini-3.1-flash-tts-preview" in t.AUDIO_STREAM_MODELS
