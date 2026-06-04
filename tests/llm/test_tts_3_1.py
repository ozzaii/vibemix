# SPDX-License-Identifier: Apache-2.0
"""Retired Gemini TTS router contract.

The live product voice is local Chatterbox-only. This file used to pin Gemini 3.1
Flash TTS router paths and VCR cassette scaffolding; the Chatterbox-era contract is
the opposite:

- cloud TTS router aliases are invalid;
- paid TTS rows may still exist only as explicit cost-model what-ifs;
- the legacy prompt tag DSL remains an opt-in prompt block, and live Chatterbox
  callers can suppress it.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from vibemix.llm.model_router import RouterPathError, resolve
from vibemix.prompts.matrix import TTS_TAG_DSL_BLOCK, TTS_TAGS, build_system_instruction


@pytest.mark.parametrize(
    "path",
    ["live_coach_tts", "live_coach_tts_fallback", "live_coach_tts_openrouter"],
)
def test_cloud_tts_router_aliases_are_retired(path: str) -> None:
    """Chatterbox is the only product voice; cloud TTS is not a model-router path."""
    with pytest.raises(RouterPathError):
        resolve(path)


def test_tts_tags_canonical_set_stays_documented_for_legacy_prompt_opt_in() -> None:
    """The old tag DSL can still be rendered for compatibility docs/tests."""
    assert TTS_TAGS == (
        "[whisper]",
        "[laugh]",
        "[fast]",
        "[slow]",
        "[excited]",
        "[chill]",
    )
    for tag in TTS_TAGS:
        assert tag in TTS_TAG_DSL_BLOCK


def test_tag_dsl_is_suppressed_for_live_chatterbox_prompt_shape() -> None:
    """Live Chatterbox callers opt out of the DSL, so tags do not reach speech."""
    body = build_system_instruction(include_tag_dsl=False)

    for tag in TTS_TAGS:
        assert tag not in body


def test_legacy_prompt_callers_can_still_opt_into_tag_dsl() -> None:
    """Default rendering keeps the block for byte-compat callers that expect it."""
    body = build_system_instruction(skill="intermediate", mode="hype")

    found = sum(1 for tag in TTS_TAGS if tag in body)
    assert found == len(TTS_TAGS)


def test_tts_tag_doc_matches_chatterbox_only_policy() -> None:
    """Docs must not re-advertise retired Gemini TTS as the live voice path."""
    root = Path(__file__).resolve().parents[2]
    doc = (root / "docs/prompts/tts-tags.md").read_text(encoding="utf-8")

    assert "local Chatterbox-only" in doc
    assert "include_tag_dsl=False" in doc
    assert "live_coach_tts" not in doc
    assert "gemini-3.1-flash-tts-preview" not in doc
    assert "public-facing OSS surface" not in doc
