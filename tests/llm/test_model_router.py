# SPDX-License-Identifier: Apache-2.0
"""Plan 41-01 / Task 1 — ModelRouter unit tests (LAT-01, LAT-07).

These tests pin the router contract:

- ``resolve(path)`` returns a ``(model_id, ServiceTier | None)`` tuple per
  the locked router-paths table in 41-01-PLAN.md.
- Live coach dispatches to ``ServiceTier.STANDARD`` (LAT-07).
- Debrief text / library / legacy embedding dispatch to ``ServiceTier.FLEX``.
- The ``embedding`` route remains only for the old Gemini cache/migration
  helper; product library embeddings are local CLAP ONNX and do not use this
  router path.
- The OpenRouter brain path returns a namespaced ``google/gemini-*`` id and a
  ``None`` tier sentinel (they are not Gemini-API calls).
- Product speech is local MOSS-only; retired Gemini/OpenRouter TTS aliases are
  not valid router paths.
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
        ("live_coach", "gemini-3.5-flash", ServiceTier.STANDARD),
        ("debrief", "gemini-3.5-flash", ServiceTier.FLEX),
        ("library_auto_tag", "gemini-3.5-flash", ServiceTier.FLEX),
        ("embedding", "gemini-embedding-2", ServiceTier.FLEX),
    ],
)
def test_resolve_ga_paths(
    path: str, expected_model: str, expected_tier: ServiceTier
) -> None:
    """Canonical Gemini API paths x tier dispatch (legacy embedding included)."""
    model, tier = resolve(path)
    assert model == expected_model
    assert tier == expected_tier


def test_resolve_openrouter_live_coach_returns_namespaced_id_and_none_tier() -> None:
    """OpenRouter brain is not a Gemini-API call — sentinel None tier."""
    model, tier = resolve("live_coach_openrouter")
    assert model == "google/gemini-3.5-flash"
    assert tier is None


@pytest.mark.parametrize(
    "path",
    ["live_coach_tts", "live_coach_tts_fallback", "live_coach_tts_openrouter"],
)
def test_cloud_tts_router_paths_are_retired(path: str) -> None:
    """MOSS is the product voice; cloud TTS survives only as explicit cost what-ifs."""
    with pytest.raises(RouterPathError):
        resolve(path)


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
    # The Library/Viber agent is local Codex now, so no Gemini `library_agent`
    # route remains. OpenRouter is brain-only. Phase 92 Plan 92-01
    # (LESSON-06, Open Q1) adds ``learn_tutor`` for the Learn module's AI tutor
    # lens — decoupled from ``live_coach`` so future model swaps don't drag both
    # surfaces.
    assert len(ROUTER_PATHS) == 8
    expected = {
        "live_coach",
        "live_coach_openrouter",
        "learn_tutor",
        "debrief",
        "library_auto_tag",
        "embedding",
        # Cost+capability study (2026-05-30): candidate live-brain Gemini tiers
        # the pricing table + bench STUDY_C resolve. Kept Gemini-only and
        # non-Live — the 3.1 Flash Live model remains isolated under spikes/,
        # and Viber/DeepSeek is deliberately NOT a router entry (see
        # _router_config.py), so test_no_non_gemini_models stays intact.
        "live_coach_cand_25flash",
        "live_coach_cand_3flash",
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
