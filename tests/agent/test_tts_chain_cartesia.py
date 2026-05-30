# SPDX-License-Identifier: Apache-2.0
"""Cartesia (Sonic) is the primary live voice when CARTESIA_API_KEY is present.

Gemini TTS failed live ('No audio content generated' on both primary + fallback)
-> the co-host went mute. Kaan 2026-05-30 picked Cartesia as the new primary.
When a Cartesia key is provided, ``_build_direct_chain`` prepends ``cartesia.TTS``
as the FallbackAdapter primary and keeps the Gemini natives as graceful fallback.
No Cartesia key -> the chain is unchanged (Gemini primary).
"""
from __future__ import annotations

from livekit.agents import tts as agents_tts
from livekit.plugins import cartesia


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
