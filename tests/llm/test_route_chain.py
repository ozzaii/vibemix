# SPDX-License-Identifier: Apache-2.0
"""Live co-host route-chain descriptor tests."""

from __future__ import annotations

from vibemix.llm.model_router import resolve_model
from vibemix.llm.route_chain import resolve_live_coach_chain


def test_proxy_unavailable_requests_manual_decision_without_switching() -> None:
    chain = resolve_live_coach_chain(
        active_provider="gemini",
        active_model=resolve_model("live_coach"),
        llm_mode="proxy",
        proxy_configured=True,
        proxy_unavailable=True,
        openrouter_configured=True,
        ttft_ms=900.0,
    )

    assert chain.active_route == "proxy"
    assert chain.switch_policy == "manual_only"
    assert chain.hedge_action == "operator_decision_required"
    assert chain.hedge_reason == "proxy_unavailable"

    fields = chain.event_fields()
    assert fields["route_active"] == "proxy"
    assert fields["route_hedge_action"] == "operator_decision_required"
    assert fields["route_switch_policy"] == "manual_only"
    assert fields["route_chain"][0]["route"] == "proxy"
    assert fields["route_chain"][0]["active"] is True
    assert fields["route_chain"][0]["available"] is False


def test_ttft_over_budget_with_openrouter_configured_is_manual_hedge() -> None:
    chain = resolve_live_coach_chain(
        active_provider="gemini",
        active_model=resolve_model("live_coach"),
        llm_mode="direct",
        proxy_configured=False,
        proxy_unavailable=False,
        openrouter_configured=True,
        ttft_ms=2400.0,
        ttft_budget_ms=1500.0,
    )

    assert chain.active_route == "direct"
    assert chain.hedge_action == "operator_decision_required"
    assert chain.hedge_reason == "ttft_over_budget_openrouter_configured"
    assert chain.switch_policy == "manual_only"
    assert chain.event_fields()["route_ttft_ms"] == 2400.0


def test_ttft_over_budget_without_verified_alternate_stays_observe_only() -> None:
    chain = resolve_live_coach_chain(
        active_provider="gemini",
        active_model=resolve_model("live_coach"),
        llm_mode="direct",
        proxy_configured=False,
        proxy_unavailable=False,
        openrouter_configured=False,
        ttft_ms=2400.0,
        ttft_budget_ms=1500.0,
    )

    assert chain.active_route == "direct"
    assert chain.hedge_action == "observe"
    assert chain.hedge_reason == "ttft_over_budget_no_verified_alternate"
    assert chain.switch_policy == "manual_only"


def test_active_openrouter_route_is_reported_without_back_switching() -> None:
    chain = resolve_live_coach_chain(
        active_provider="openrouter",
        active_model=resolve_model("live_coach_openrouter"),
        llm_mode="direct",
        proxy_configured=False,
        proxy_unavailable=False,
        openrouter_configured=True,
        ttft_ms=1800.0,
        ttft_budget_ms=1500.0,
    )

    assert chain.active_route == "openrouter"
    assert chain.hedge_action == "observe"
    assert chain.hedge_reason == "ttft_over_budget_no_verified_alternate"
    assert chain.event_fields()["route_chain"][0]["route"] == "openrouter"
