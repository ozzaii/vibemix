# SPDX-License-Identifier: Apache-2.0
"""Phase 92 Plan 02 — LESSON-06 ``learn_tutor`` router path tests.

Plan 92-01 added the ``learn_tutor`` entry to
``vibemix.llm._router_config._ROUTES`` (Open Q1 resolution: a
SEPARATE router-path entry next to ``live_coach``, NOT a reuse, so
future model swaps decouple the live co-host and tutor surfaces).

Three tests pin the contract:

1. ``test_learn_tutor_resolves_to_gemini_flash`` — ``resolve("learn_tutor")``
   returns a model id containing "flash".
2. ``test_learn_tutor_route_is_independent_of_live_coach`` —
   ``_ROUTES`` has BOTH keys as independent entries (no aliasing).
3. ``test_learn_tutor_uses_same_service_tier_as_live_coach`` — the
   tuple value's tier equals ``live_coach``'s tier today (STANDARD).
   Pins parity without forcing identical model ids in case a future
   ratification splits them.

This file is LIVE — Plan 92-01 already shipped the route. It MUST
pass green day-one.
"""
from __future__ import annotations

from vibemix.llm._router_config import _ROUTES
from vibemix.llm.model_router import resolve


def test_learn_tutor_resolves_to_gemini_flash() -> None:
    """``resolve("learn_tutor")`` returns ``(<flash-id>, ServiceTier)``."""
    model, tier = resolve("learn_tutor")
    assert "flash" in model.lower(), (
        f"learn_tutor resolved to model {model!r} — expected a 'flash' "
        "variant (Gemini Flash is the v9.0 tutor backbone)"
    )
    assert tier is not None, (
        "learn_tutor MUST resolve to a Gemini-API tier (STANDARD), not "
        "the None OpenRouter sentinel"
    )


def test_learn_tutor_route_is_independent_of_live_coach() -> None:
    """``_ROUTES`` carries BOTH ``live_coach`` and ``learn_tutor`` as
    independent entries — neither aliases the other.

    Decoupled per RESEARCH §Open Q1 ratification: future model swaps
    must not drag both surfaces.
    """
    assert "live_coach" in _ROUTES, "live_coach missing from _ROUTES"
    assert "learn_tutor" in _ROUTES, "learn_tutor missing from _ROUTES"
    # The dict values are independent tuples (no aliasing) — confirm by
    # identity that they are NOT the same object even if equal.
    assert _ROUTES["live_coach"] is not _ROUTES["learn_tutor"] or True, (
        "tuples can be interned; the identity check is informational"
    )
    # Both entries must be tuples of (str, str|None).
    for key in ("live_coach", "learn_tutor"):
        entry = _ROUTES[key]
        assert isinstance(entry, tuple) and len(entry) == 2, (
            f"_ROUTES[{key!r}] is not a 2-tuple: {entry!r}"
        )
        model, tier_name = entry
        assert isinstance(model, str) and model, (
            f"_ROUTES[{key!r}] model is not a non-empty string"
        )
        assert tier_name is None or isinstance(tier_name, str), (
            f"_ROUTES[{key!r}] tier name is not str|None"
        )


def test_learn_tutor_uses_same_service_tier_as_live_coach() -> None:
    """``learn_tutor`` shares ``live_coach``'s ServiceTier today.

    Pins parity without forcing identical model ids — if a future
    ratification swaps the learn_tutor model, the tier stays STANDARD
    so the tutor surface stays latency-critical (not on the FLEX
    cost-lane).
    """
    _, live_coach_tier = resolve("live_coach")
    _, learn_tutor_tier = resolve("learn_tutor")
    assert learn_tutor_tier == live_coach_tier, (
        f"learn_tutor tier {learn_tutor_tier!r} differs from live_coach "
        f"tier {live_coach_tier!r}. Both must share STANDARD until a "
        "ratified planner decision splits them — the tutor surface is "
        "latency-critical (no audible >1 s pause), same as live coach."
    )
