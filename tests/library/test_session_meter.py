# SPDX-License-Identifier: Apache-2.0
"""Quick task 260525-fuv — SessionMeter billing-split unit tests.

Covers the fresh/cached/output billing split, cache-savings math, the
untracked-call (OpenRouter) path, the summary() shape, and the
no-ZeroDivision / unknown-path safety contracts described in PLAN.md
<behavior>. All tests run under the DEFAULT pytest selection — no
network/integration/slow markers — and use SessionMeter() instances
directly (not the singleton) to avoid cross-test state.
"""

from __future__ import annotations

import math

from vibemix.library.budget import (
    ROUTE_PRICING,
    USD_TO_EUR,
    SessionMeter,
    get_session_meter,
)


def _eur(usd: float) -> float:
    return usd * USD_TO_EUR


def test_route_pricing_keyed_by_router_path() -> None:
    """Pricing is keyed by router-PATH strings, never raw Gemini model names."""
    for path in ("live_coach", "live_coach_tts", "debrief", "embedding"):
        assert path in ROUTE_PRICING, f"missing pricing for path {path!r}"
        rate = ROUTE_PRICING[path]
        assert "input" in rate and "output" in rate
    # live_coach cache discount is real (cached_input < input).
    assert ROUTE_PRICING["live_coach"]["cached_input"] < ROUTE_PRICING["live_coach"]["input"]


def test_live_coach_billing_split_with_cache() -> None:
    """fresh_input = prompt - cached; each tier billed at its own rate."""
    m = SessionMeter()
    m.record("live_coach", prompt=1000, cached=800, output=200)

    rate = ROUTE_PRICING["live_coach"]
    fresh = 1000 - 800
    expected_usd = (
        fresh * rate["input"] / 1e6
        + 800 * rate["cached_input"] / 1e6
        + 200 * rate["output"] / 1e6
    )
    s = m.summary()
    assert math.isclose(s["total_cost_eur"], _eur(expected_usd), rel_tol=1e-9)

    lc = s["per_path"]["live_coach"]
    assert lc["input_tokens"] == 1000
    assert lc["cached_tokens"] == 800
    assert lc["output_tokens"] == 200
    assert math.isclose(lc["cost_eur"], _eur(expected_usd), rel_tol=1e-9)


def test_cache_savings_math() -> None:
    """Savings = cached tokens × (fresh_rate - cached_rate)."""
    m = SessionMeter()
    m.record("live_coach", prompt=1000, cached=800, output=200)
    rate = ROUTE_PRICING["live_coach"]
    expected_savings_usd = 800 * (rate["input"] - rate["cached_input"]) / 1e6
    s = m.summary()
    assert math.isclose(s["total_savings_eur"], _eur(expected_savings_usd), rel_tol=1e-9)


def test_cold_cache_no_savings_fresh_equals_prompt() -> None:
    """cached=0 → savings 0, all input billed at fresh rate."""
    m = SessionMeter()
    m.record("live_coach", prompt=1000, cached=0, output=200)
    rate = ROUTE_PRICING["live_coach"]
    expected_usd = 1000 * rate["input"] / 1e6 + 200 * rate["output"] / 1e6
    s = m.summary()
    assert s["total_savings_eur"] == 0.0
    assert math.isclose(s["total_cost_eur"], _eur(expected_usd), rel_tol=1e-9)


def test_embedding_only_input_billed() -> None:
    """embedding output rate is 0 → only input contributes."""
    m = SessionMeter()
    m.record("embedding", prompt=1000, cached=0, output=0)
    rate = ROUTE_PRICING["embedding"]
    expected_usd = 1000 * rate["input"] / 1e6
    s = m.summary()
    assert math.isclose(s["total_cost_eur"], _eur(expected_usd), rel_tol=1e-9)
    assert rate["output"] == 0.0


def test_record_untracked_no_cost_increments_counter() -> None:
    """OpenRouter path → untracked_calls++ and no cost added."""
    m = SessionMeter()
    m.record_untracked()
    m.record_untracked()
    s = m.summary()
    assert s["untracked_calls"] == 2
    assert s["total_cost_eur"] == 0.0


def test_cache_hit_rate_over_cache_eligible_paths() -> None:
    """cache_hit_rate = total_cached / total_input across cache-eligible paths."""
    m = SessionMeter()
    m.record("live_coach", prompt=1000, cached=800, output=100)
    m.record("live_coach", prompt=1000, cached=200, output=100)
    s = m.summary()
    # 1000 cached / 2000 input = 0.5
    assert math.isclose(s["cache_hit_rate"], 0.5, rel_tol=1e-9)


def test_cache_hit_rate_zero_when_no_input() -> None:
    """No cache-eligible input → 0.0, no ZeroDivisionError."""
    m = SessionMeter()
    s = m.summary()
    assert s["cache_hit_rate"] == 0.0


def test_cache_hit_rate_clamped_to_unit_interval() -> None:
    """Even with pathological inputs cache_hit_rate stays in [0, 1]."""
    m = SessionMeter()
    # cached > prompt should never happen, but the meter must not exceed 1.0.
    m.record("live_coach", prompt=100, cached=500, output=10)
    s = m.summary()
    assert 0.0 <= s["cache_hit_rate"] <= 1.0


def test_unknown_path_does_not_crash_zero_cost() -> None:
    """Unknown router path → recorded with cost 0, flagged, never raises."""
    m = SessionMeter()
    m.record("totally_made_up_path", prompt=1000, cached=0, output=500)
    s = m.summary()
    assert "totally_made_up_path" in s["per_path"]
    assert s["per_path"]["totally_made_up_path"]["cost_eur"] == 0.0
    # Unknown path contributes no cost to the total.
    assert s["total_cost_eur"] == 0.0


def test_summary_shape() -> None:
    """summary() exposes the documented keys."""
    m = SessionMeter()
    m.record("live_coach", prompt=10, cached=0, output=5)
    s = m.summary()
    for key in (
        "per_path",
        "total_cost_eur",
        "total_savings_eur",
        "cache_hit_rate",
        "untracked_calls",
    ):
        assert key in s
    lc = s["per_path"]["live_coach"]
    for key in ("input_tokens", "cached_tokens", "output_tokens", "cost_eur"):
        assert key in lc


def test_record_never_raises_on_garbage() -> None:
    """The meter must never raise into the LLM stream consumer."""
    m = SessionMeter()
    # Negative / None-ish defaults must be tolerated.
    m.record("live_coach", prompt=0, cached=0, output=0)
    m.record("live_coach", prompt=-5, cached=-2, output=-1)
    # Still produces a usable summary.
    assert isinstance(m.summary(), dict)


def test_get_session_meter_singleton() -> None:
    a = get_session_meter()
    b = get_session_meter()
    assert a is b
    a.reset()


def test_reset_clears_state() -> None:
    m = SessionMeter()
    m.record("live_coach", prompt=1000, cached=500, output=200)
    m.record_untracked()
    m.reset()
    s = m.summary()
    assert s["total_cost_eur"] == 0.0
    assert s["untracked_calls"] == 0
    assert s["per_path"] == {}
