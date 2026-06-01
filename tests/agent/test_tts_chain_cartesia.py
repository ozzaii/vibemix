# SPDX-License-Identifier: Apache-2.0
"""Cartesia keys must not change the MOSS-only voice policy."""

from __future__ import annotations

from livekit.agents import tts as agents_tts
from livekit.plugins import cartesia


def test_cartesia_key_is_ignored_by_tts_chain(mocker) -> None:
    mocker.patch("vibemix.agent.local_tts.local_tts_enabled", return_value=True)
    fake_moss_cls = mocker.patch("vibemix.agent.local_tts.MossLocalTTS")
    cartesia_tts = mocker.patch.object(cartesia, "TTS")
    mocker.patch.object(agents_tts.FallbackAdapter, "__init__", return_value=None)

    from vibemix.agent.tts_chain import build_tts_chain

    build_tts_chain(gemini_api_key="g", cartesia_api_key="c", mode="direct")

    kwargs = agents_tts.FallbackAdapter.__init__.call_args.kwargs
    assert kwargs["tts"] == [fake_moss_cls.return_value]
    cartesia_tts.assert_not_called()


def test_cartesia_env_is_ignored_by_tts_chain(mocker, monkeypatch) -> None:
    monkeypatch.setenv("CARTESIA_API_KEY", "env-cartesia-key")
    mocker.patch("vibemix.agent.local_tts.local_tts_enabled", return_value=True)
    fake_moss_cls = mocker.patch("vibemix.agent.local_tts.MossLocalTTS")
    cartesia_tts = mocker.patch.object(cartesia, "TTS")
    mocker.patch.object(agents_tts.FallbackAdapter, "__init__", return_value=None)

    from vibemix.agent.tts_chain import build_tts_chain

    build_tts_chain(mode="direct")

    kwargs = agents_tts.FallbackAdapter.__init__.call_args.kwargs
    assert kwargs["tts"] == [fake_moss_cls.return_value]
    cartesia_tts.assert_not_called()
