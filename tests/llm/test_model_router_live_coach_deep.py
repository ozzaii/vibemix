# SPDX-License-Identifier: Apache-2.0
"""X4 route reservation for deep live-coach context.

``live_coach_deep`` is a structural seam, not a behavior change: it resolves
to the same Flash model and STANDARD tier as ``live_coach`` today. Future
rich-context work can swap the deep lane in ``_router_config.py`` without
hardcoding a model literal at the call site.
"""

from __future__ import annotations

from vibemix.llm._router_config import _ROUTES
from vibemix.llm.model_router import resolve


def test_live_coach_deep_route_exists_next_to_live_coach() -> None:
    assert "live_coach" in _ROUTES
    assert "live_coach_deep" in _ROUTES


def test_live_coach_deep_matches_live_coach_today() -> None:
    assert resolve("live_coach_deep") == resolve("live_coach")


def test_live_coach_deep_is_a_distinct_router_key() -> None:
    """The deep lane is addressable by name even while it matches today."""
    assert "live_coach_deep" in _ROUTES
    assert "live_coach_deep" != "live_coach"
