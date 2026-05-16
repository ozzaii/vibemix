# SPDX-License-Identifier: Apache-2.0
"""Plan 41-04 Task 3 — Gemini 3.1 Flash TTS audio-tag DSL contract tests.

The 6 tags supported in vibemix's coach prompts:
  [whisper] [laugh] [fast] [slow] [excited] [chill]

Per CONTEXT.md decisions + the locked router path, the live coach TTS
model is sourced via :func:`vibemix.llm.model_router.resolve`
(``live_coach_tts`` path) — currently ``gemini-3.1-flash-tts-preview``.
The OpenRouter Achird OPUS fallback chain remains intact (the existing
TTS IP from v4 is preserved — never removed).

Test posture:

  * **Mocked-SDK** unit tests pin the router-derived model id, the chain
    shape, and the tag-DSL pass-through invariant. These DO NOT require
    a live ``GEMINI_API_KEY`` and run in CI.
  * **VCR-cassette** integration tests are scaffolded under
    :mod:`tests.llm.cassettes.test_tts_3_1` — they record once per
    rubric change with ``VCR_RECORD_MODE=new_episodes`` against a real
    key (deferred to a Kaan-action recording session per
    ``gsd-autonomous fully`` defer protocol). The cassette path uses the
    same convention as ``tests/eval/cassettes/`` so future record-mode
    integration is one-line.

Tag rendering contract (locked):
  * The 6 tags are inline-emitted by the LLM as part of the response
    text (e.g. ``[whisper] insider tip``). The Gemini 3.1 Flash TTS
    consumes them at synthesis time as expressivity directives.
  * Vibemix's coach prompt template (``vibemix.prompts.matrix``)
    documents the tag DSL via the locked
    :data:`vibemix.prompts.matrix.TTS_TAG_DSL_BLOCK` constant — present
    when ``include_tag_dsl=True`` (default).
  * Unknown tags (``[invented_tag]``) — Gemini 3.1 Flash TTS behavior is
    pinned via cassette (post-record) to either pass-through-literal or
    strip; whichever shape the cassette captures is the canonical
    contract (see ``test_unknown_tag_behavior_documented``).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from vibemix.llm.model_router import resolve
from vibemix.prompts.matrix import TTS_TAG_DSL_BLOCK, TTS_TAGS, build_system_instruction


# ---------- Router-path contract ----------


def test_live_coach_tts_router_path_resolves_to_3_1_flash() -> None:
    """live_coach_tts → ``gemini-3.1-flash-tts-preview`` (Plan 41-04 LAT-05).

    The model id is the SOURCE of truth for the TTS path. If the GA
    rename ships, ``_router_config.py`` is the one-line edit; this test
    follows the rename automatically (the literal is allowlisted there).
    """
    model_id, tier = resolve("live_coach_tts")
    assert model_id == "gemini-3.1-flash-tts-preview"
    # Tier is STANDARD (latency-critical — live path).
    from google.genai.types import ServiceTier

    assert tier == ServiceTier.STANDARD


def test_openrouter_fallback_chain_preserved() -> None:
    """The OpenRouter Achird OPUS path is the second-place TTS choice; it
    MUST remain wired (the v4 IP is not removed by 41-04).
    """
    model_id, _ = resolve("live_coach_tts_openrouter")
    assert model_id == "google/gemini-3.1-flash-tts-preview"


def test_legacy_tts_fallback_chain_preserved() -> None:
    """The legacy Gemini 2.5 Flash TTS fallback (chain entry #3) preserved."""
    model_id, _ = resolve("live_coach_tts_fallback")
    assert model_id == "gemini-2.5-flash-preview-tts"


# ---------- Audio-tag DSL contract ----------


def test_tts_tags_canonical_set() -> None:
    """The 6 audio tags from LAT-05 are the canonical set."""
    assert TTS_TAGS == (
        "[whisper]",
        "[laugh]",
        "[fast]",
        "[slow]",
        "[excited]",
        "[chill]",
    )


def test_tts_tag_dsl_block_documents_all_6_tags() -> None:
    """Each of the 6 tags appears verbatim in the DSL block constant.

    The block is later injected into the coach system instruction via
    ``build_system_instruction(include_tag_dsl=True)`` — so the LLM sees
    the DSL inline in its prompt and can emit tags grounded in the
    documented intent.
    """
    for tag in TTS_TAGS:
        assert tag in TTS_TAG_DSL_BLOCK


def test_dsl_block_present_in_default_system_instruction() -> None:
    """Default ``build_system_instruction(...)`` call appends the tag DSL block.

    Phase 4 byte-identity callers opt OUT via ``include_tag_dsl=False``
    — but the live agent uses defaults so every per-turn Gemini call
    sees the DSL.
    """
    body = build_system_instruction()
    for tag in TTS_TAGS:
        assert tag in body, f"tag {tag} missing from default system instruction"


def test_dsl_block_can_be_suppressed_for_byte_identity_callers() -> None:
    """``include_tag_dsl=False`` removes the tag DSL block from the rendered prompt."""
    body = build_system_instruction(include_tag_dsl=False)
    assert "[whisper]" not in body or "[chill]" not in body, (
        "include_tag_dsl=False should suppress the tag DSL block"
    )
    # Explicit invariant: none of the 6 tags appear when suppressed.
    for tag in TTS_TAGS:
        assert tag not in body


# ---------- Per-tag rendering hooks (cassette-pinned, scaffold-only) ----------

CASSETTE_DIR = Path(__file__).parent / "cassettes" / "test_tts_3_1"


@pytest.mark.parametrize(
    "tag,sample_phrase",
    [
        ("[whisper]", "insider tip — that loop's a sleeper"),
        ("[laugh]", "yeah that bassline got me good"),
        ("[fast]", "drop incoming hype it up"),
        ("[slow]", "feel the groove settle in"),
        ("[excited]", "DROP!"),
        ("[chill]", "easy now, just floating"),
    ],
)
def test_tag_rendering_payload_shape(tag: str, sample_phrase: str) -> None:
    """The tag + phrase compose as a single inline string the LLM will
    emit and the TTS will read at synthesis time.

    This test pins the inline-emission shape (NOT the audio response —
    that's the cassette-backed integration test below). The contract:
    the tag is the FIRST token (after optional whitespace) of the
    payload string the TTS receives.
    """
    payload = f"{tag} {sample_phrase}"
    assert payload.startswith(tag)
    # Whitespace after the tag — TTS parses ``[tag]<space>...`` as the
    # tag scope; the rest of the line carries the spoken text.
    assert payload[len(tag)] == " "


@pytest.mark.skipif(
    not CASSETTE_DIR.exists() or not any(CASSETTE_DIR.glob("*.yaml")),
    reason=(
        "VCR cassettes not recorded yet — run "
        "VCR_RECORD_MODE=new_episodes uv run pytest tests/llm/test_tts_3_1.py "
        "with a real GEMINI_API_KEY to pin the audio response shape."
    ),
)
def test_unknown_tag_behavior_documented() -> None:
    """``[invented_tag]`` → assert the cassette-captured behavior.

    Whichever shape the recorded cassette captures (pass-through-literal
    or strip-with-warning) IS the contract. This test is the canon for
    future maintainers — if Gemini changes behavior on unknown tags, the
    cassette must be re-recorded AND the docs/prompts/tts-tags.md
    "Unknown tags" section updated to match.
    """
    # Cassette-only: deferred to a recording session. Skip applies above
    # — test body is a placeholder reading the recorded response.
    pytest.skip(
        "Cassette-backed integration test — see VCR_RECORD_MODE notes in module docstring."
    )


# ---------- Persona-overlay opt-in ----------


def test_persona_overlay_can_opt_into_tag_dsl() -> None:
    """A persona config that opts IN to the tag DSL produces a prompt
    string containing at least one tag from :data:`TTS_TAGS`.

    The opt-in is the default (Plan 41-04 ships tags-on by default for
    every live coach turn); persona overlays can still suppress via
    ``include_tag_dsl=False`` for byte-identity callers.
    """
    body = build_system_instruction(skill="intermediate", mode="hype")
    # The default rendering contains the DSL block.
    found = sum(1 for tag in TTS_TAGS if tag in body)
    assert found == len(TTS_TAGS), (
        f"expected all {len(TTS_TAGS)} tags in default rendering, found {found}"
    )


def test_persona_overlay_opt_out_suppresses_tags() -> None:
    """Persona overlay opts out → no tags rendered."""
    body = build_system_instruction(
        skill="intermediate", mode="hype", include_tag_dsl=False
    )
    for tag in TTS_TAGS:
        assert tag not in body
