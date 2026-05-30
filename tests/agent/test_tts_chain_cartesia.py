# SPDX-License-Identifier: Apache-2.0
"""Cartesia (Sonic) is the primary live voice when CARTESIA_API_KEY is present.

Gemini TTS failed live ('No audio content generated' on both primary + fallback)
-> the co-host went mute. Kaan 2026-05-30 picked Cartesia as the new primary.
When a Cartesia key is provided, ``_build_direct_chain`` prepends ``cartesia.TTS``
as the FallbackAdapter primary and keeps the Gemini natives as graceful fallback.
No Cartesia key -> the chain is unchanged (Gemini primary).
"""
from __future__ import annotations

import asyncio

import aiohttp
from livekit.agents import tts as agents_tts
from livekit.plugins import cartesia


def test_live_http_session_is_none_without_running_loop():
    # Construction-time / unit-test path: no running loop -> None, so plugin
    # construction stays loop-free (and the existing Cartesia tests still pass).
    from vibemix.agent.tts_chain import _live_http_session

    assert _live_http_session() is None


def test_live_http_session_returns_clientsession_inside_loop():
    from vibemix.agent.tts_chain import _live_http_session

    async def _run():
        sess = _live_http_session()
        assert isinstance(sess, aiohttp.ClientSession)
        await sess.close()

    asyncio.run(_run())


def test_cartesia_gets_http_session_when_built_in_loop(mocker):
    # The livekit Cartesia plugin falls back to utils.http_context.http_session()
    # when given no session — that REQUIRES a livekit job context, which vibemix
    # (own asyncio loop, not the agent-worker api) lacks, so the connection-pool
    # prewarm raises "http session outside of a job context" and TTS goes MUTE.
    # The fix: build_tts_chain must pass our own aiohttp.ClientSession.
    captured: dict = {}

    def _capture(*args, **kwargs):
        captured.update(kwargs)
        return mocker.MagicMock()

    mocker.patch.object(cartesia, "TTS", side_effect=_capture)
    mocker.patch.object(agents_tts.FallbackAdapter, "__init__", return_value=None)
    from vibemix.agent.tts_chain import build_tts_chain

    async def _run():
        build_tts_chain(gemini_api_key="g", cartesia_api_key="c", mode="direct")
        sess = captured.get("http_session")
        if isinstance(sess, aiohttp.ClientSession):
            await sess.close()

    asyncio.run(_run())

    assert "http_session" in captured, "cartesia.TTS built without an http_session kwarg"
    assert isinstance(captured["http_session"], aiohttp.ClientSession), (
        "cartesia.TTS must receive a real aiohttp.ClientSession when built in a "
        "running loop, else the prewarm crashes outside the job context"
    )


def test_cartesia_is_primary_when_key_present(mocker):
    mocker.patch.object(agents_tts.FallbackAdapter, "__init__", return_value=None)
    from vibemix.agent.tts_chain import build_tts_chain

    build_tts_chain(gemini_api_key="g", cartesia_api_key="c", mode="direct")

    chain = agents_tts.FallbackAdapter.__init__.call_args.kwargs["tts"]
    assert isinstance(chain[0], cartesia.TTS)  # Cartesia leads the chain
    assert len(chain) >= 2  # Gemini natives remain as graceful fallback


def test_no_cartesia_key_keeps_gemini_primary(mocker, monkeypatch):
    monkeypatch.delenv("CARTESIA_API_KEY", raising=False)  # env-fallback off
    mocker.patch.object(agents_tts.FallbackAdapter, "__init__", return_value=None)
    from vibemix.agent.tts_chain import build_tts_chain

    build_tts_chain(gemini_api_key="g", mode="direct")

    chain = agents_tts.FallbackAdapter.__init__.call_args.kwargs["tts"]
    assert not isinstance(chain[0], cartesia.TTS)  # Gemini still primary, untouched


def test_empty_cartesia_key_is_treated_as_absent(mocker, monkeypatch):
    monkeypatch.delenv("CARTESIA_API_KEY", raising=False)  # "" + no env -> Gemini
    mocker.patch.object(agents_tts.FallbackAdapter, "__init__", return_value=None)
    from vibemix.agent.tts_chain import build_tts_chain

    build_tts_chain(gemini_api_key="g", cartesia_api_key="", mode="direct")

    chain = agents_tts.FallbackAdapter.__init__.call_args.kwargs["tts"]
    assert not isinstance(chain[0], cartesia.TTS)  # "" -> no Cartesia, no crash
