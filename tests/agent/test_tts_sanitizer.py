# SPDX-License-Identifier: Apache-2.0
"""TTS-only model text sanitizer tests."""

from __future__ import annotations

from vibemix.agent.tts_sanitizer import model_text_for_tts, strip_citations_for_tts


def test_strip_citations_for_tts_removes_single_atom() -> None:
    assert strip_citations_for_tts("Low end moved [aud:rms@12.0].") == "Low end moved."


def test_strip_citations_for_tts_keeps_visible_words_around_atom() -> None:
    assert strip_citations_for_tts("nice [ev:KICK_SWAP@45.2] yeah") == "nice yeah"


def test_strip_citations_for_tts_removes_multi_atom_bracket() -> None:
    text = "Proof [ev:A@1,aud:bpm@1] stays out of the voice."

    assert strip_citations_for_tts(text) == "Proof stays out of the voice."


def test_model_text_for_tts_strips_voice_controls_and_citations() -> None:
    text = "[chill] Nice [emote:nod] drop [aud:rms@12.0]."

    assert model_text_for_tts(text) == "Nice drop."


def test_model_text_for_tts_leaves_english_without_citations_unchanged() -> None:
    assert model_text_for_tts("That kick is clean. ") == "That kick is clean. "
