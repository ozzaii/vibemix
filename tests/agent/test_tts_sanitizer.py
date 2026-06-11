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


def test_citation_only_line_with_trailing_punct_strips_to_empty() -> None:
    """Measured 2026-06-10 (baseline-cadence-midi-r2): the model answered with a
    bare citation atom plus a period. The old strip left "." — truthy, so the
    runtime spoke a click and recorded the turn as a reaction (judged friend-0).
    A residue with no word characters is not speech: it must strip to "" so the
    existing <empty> (skip TTS) branch treats it as the silence escape."""
    assert strip_citations_for_tts("[energy:master_read=audio_peak_110_f3108ffa].") == ""
    assert model_text_for_tts("[emote:nod] [aud:rms@12.0]...") == ""
    # The wordless rule covers the no-citation path too (auditor L1): a bare
    # "..." reply is not speech either.
    assert strip_citations_for_tts("...") == ""


def test_wordless_check_keeps_real_words_after_strip() -> None:
    """The wordless cut keys on \\w content, not length — a one-word residue
    ("Wait.") is real speech and must survive untouched (edge whitespace is
    preserved, matching the no-citation path's contract above)."""
    assert strip_citations_for_tts("Wait. [aud:rms@12.0]") == "Wait. "
