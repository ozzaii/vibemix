# SPDX-License-Identifier: Apache-2.0
"""Plan 41-01 / Task 1 — ModelRouter unit tests (LAT-01, LAT-07).

These tests pin the router contract:

- ``resolve(path)`` returns a ``(model_id, ServiceTier | None)`` tuple per
  the locked router-paths table in 41-01-PLAN.md.
- Live coach + live-coach TTS dispatch to ``ServiceTier.STANDARD`` (LAT-07).
- Debrief / library / embedding dispatch to ``ServiceTier.FLEX``.
- The OpenRouter TTS path returns the namespaced ``google/gemini-*`` id and
  a ``None`` tier sentinel (it is not a Gemini-API call).
- Unknown paths raise ``RouterPathError`` and the message lists every valid
  path so the caller can self-diagnose.
- ``ROUTER_PATHS`` is a frozen ``tuple`` (defensive against mutation).
- No non-Gemini model ids sneak into ``_ROUTES`` (defensive against
  accidental Anthropic / OpenAI / Ollama entries).
"""

from __future__ import annotations

import pytest
from google.genai.types import ServiceTier

from vibemix.llm.model_router import ROUTER_PATHS, RouterPathError, resolve


# ---------------------------------------------------------------------------
# GA path × tier assertions
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("path", "expected_model", "expected_tier"),
    [
        ("live_coach", "gemini-3-flash-preview", ServiceTier.STANDARD),
        ("debrief", "gemini-3-pro-preview", ServiceTier.FLEX),
        ("library_auto_tag", "gemini-3-flash-preview", ServiceTier.FLEX),
        ("embedding", "gemini-embedding-2", ServiceTier.FLEX),
    ],
)
def test_resolve_ga_paths(
    path: str, expected_model: str, expected_tier: ServiceTier
) -> None:
    """Four canonical GA paths × tier dispatch (CONTEXT.md locked table)."""
    model, tier = resolve(path)
    assert model == expected_model
    assert tier == expected_tier


def test_resolve_live_coach_tts_returns_standard_3_1() -> None:
    """Live-coach TTS rides the live-coach Standard tier (LAT-07)."""
    model, tier = resolve("live_coach_tts")
    assert model == "gemini-3.1-flash-tts-preview"
    assert tier == ServiceTier.STANDARD


def test_resolve_openrouter_tts_returns_namespaced_id_and_none_tier() -> None:
    """OpenRouter TTS is not a Gemini-API call — sentinel None tier."""
    model, tier = resolve("live_coach_tts_openrouter")
    assert model == "google/gemini-3.1-flash-tts-preview"
    assert tier is None


def test_resolve_unknown_path_raises_router_path_error() -> None:
    """Unknown path raises RouterPathError with all valid paths listed."""
    with pytest.raises(RouterPathError) as exc:
        resolve("not_a_path")
    msg = str(exc.value)
    # The error message must list every valid key for caller diagnosability.
    for key in ROUTER_PATHS:
        assert key in msg, f"valid key {key!r} missing from error message"


def test_router_path_error_is_keyerror_subclass() -> None:
    """RouterPathError is a KeyError subclass — callers that catch KeyError
    still work (backward-compat)."""
    assert issubclass(RouterPathError, KeyError)


def test_router_paths_is_frozen_tuple() -> None:
    """ROUTER_PATHS is a tuple (not list) — defensive against mutation."""
    assert isinstance(ROUTER_PATHS, tuple)
    # The router-paths table in 41-01-PLAN.md ships 8 keys.
    assert len(ROUTER_PATHS) == 8
    expected = {
        "live_coach",
        "live_coach_tts",
        "live_coach_tts_fallback",
        "live_coach_tts_openrouter",
        "debrief",
        "debrief_tts",
        "library_auto_tag",
        "embedding",
    }
    assert set(ROUTER_PATHS) == expected


def test_no_non_gemini_models() -> None:
    """Every model_id is gemini-* prefixed or the single google/gemini-* id.

    Defensive: a future PR accidentally adding an Anthropic / OpenAI /
    Ollama model id would trip this assertion before the CI grep gate.
    """
    for path in ROUTER_PATHS:
        model, _ = resolve(path)
        ok = model.startswith("gemini-") or model.startswith("google/gemini-")
        assert ok, f"path {path!r} maps to non-Gemini model {model!r}"


def test_live_coach_tts_fallback_returns_2_5() -> None:
    """The TTS fallback chain still surfaces the 2.5 native fallback id."""
    model, tier = resolve("live_coach_tts_fallback")
    assert model == "gemini-2.5-flash-preview-tts"
    assert tier == ServiceTier.STANDARD


def test_debrief_tts_returns_flex_3_flash_tts() -> None:
    """Debrief TTS shares the debrief Flex tier (cost lane)."""
    model, tier = resolve("debrief_tts")
    assert model == "gemini-3-flash-tts-preview"
    assert tier == ServiceTier.FLEX
