# SPDX-License-Identifier: Apache-2.0
"""PROXY-01..04 — build_proxy_genai_client + build_proxy_tts_chain."""

from __future__ import annotations

import subprocess
import sys

from livekit.agents import tts as agents_tts

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


def test_proxy_03_tts_chain_is_moss_only(mocker):
    """PROXY-03: proxy TTS is local MOSS, never proxy/OpenAI speech."""
    mocker.patch("vibemix.agent.local_tts.local_tts_enabled", return_value=True)
    fake_moss_cls = mocker.patch("vibemix.agent.local_tts.MossLocalTTS")
    mocker.patch.object(agents_tts.FallbackAdapter, "__init__", return_value=None)

    build_proxy_tts_chain(jwt="jwt-x", proxy_base_url="https://api.altidus.world")

    fa_kwargs = agents_tts.FallbackAdapter.__init__.call_args.kwargs
    assert fa_kwargs["tts"] == [fake_moss_cls.return_value]
    assert fa_kwargs["max_retry_per_tts"] == 1
    fake_moss_cls.return_value.prewarm.assert_called_once()


def test_proxy_03b_tts_chain_uses_local_moss_when_enabled(mocker):
    """Proxy mode should not route voice to paid/proxy TTS when local MOSS is ready."""
    mocker.patch("vibemix.agent.local_tts.local_tts_enabled", return_value=True)
    fake_moss_cls = mocker.patch("vibemix.agent.local_tts.MossLocalTTS")
    mocker.patch.object(agents_tts.FallbackAdapter, "__init__", return_value=None)

    build_proxy_tts_chain(jwt="jwt-x", proxy_base_url="https://api.altidus.world")

    fa_kwargs = agents_tts.FallbackAdapter.__init__.call_args.kwargs
    assert fa_kwargs["tts"] == [fake_moss_cls.return_value]
    assert fa_kwargs["max_retry_per_tts"] == 1
    fake_moss_cls.return_value.prewarm.assert_called_once()


def test_proxy_04_tts_chain_does_not_import_openai_tts_plugin() -> None:
    """PROXY-04: MOSS-only voice does not patch or import OpenAI TTS."""
    proc = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys\n"
                "import vibemix.agent.tts_chain\n"
                "assert 'livekit.plugins.openai.tts' not in sys.modules\n"
                "print('OK')\n"
            ),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert proc.stdout.strip() == "OK"
