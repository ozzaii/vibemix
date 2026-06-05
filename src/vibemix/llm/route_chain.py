# SPDX-License-Identifier: Apache-2.0
"""Runtime route-chain descriptor for the live co-host brain.

This module is deliberately read-only: it resolves what the current runtime is
doing, and whether latency/outage telemetry should ask the operator for a
route decision. It never chooses a different provider on its own.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from vibemix.llm.model_router import resolve_model

LIVE_COACH_TTFT_HEDGE_BUDGET_MS = 1500.0

RouteHedgeAction = Literal["observe", "operator_decision_required"]


@dataclass(frozen=True)
class LiveCoachRouteCandidate:
    route: str
    provider: str
    model: str
    active: bool
    available: bool
    reason: str

    def event_fields(self) -> dict[str, object]:
        return {
            "route": self.route,
            "provider": self.provider,
            "model": self.model,
            "active": self.active,
            "available": self.available,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class LiveCoachRouteChain:
    active_route: str
    active_provider: str
    active_model: str
    candidates: tuple[LiveCoachRouteCandidate, ...]
    hedge_action: RouteHedgeAction
    hedge_reason: str
    ttft_ms: float | None
    ttft_budget_ms: float
    switch_policy: str = "manual_only"

    def event_fields(self) -> dict[str, object]:
        return {
            "route_active": self.active_route,
            "route_provider": self.active_provider,
            "route_model": self.active_model,
            "route_chain": [candidate.event_fields() for candidate in self.candidates],
            "route_hedge_action": self.hedge_action,
            "route_hedge_reason": self.hedge_reason,
            "route_switch_policy": self.switch_policy,
            "route_ttft_ms": _round_ms(self.ttft_ms),
            "route_ttft_budget_ms": _round_ms(self.ttft_budget_ms),
        }


def _round_ms(value: float | None) -> float | None:
    if value is None:
        return None
    return round(float(value), 1)


def resolve_live_coach_chain(
    *,
    active_provider: str,
    active_model: str,
    llm_mode: str,
    proxy_configured: bool,
    proxy_unavailable: bool,
    openrouter_configured: bool,
    ttft_ms: float | None,
    ttft_budget_ms: float = LIVE_COACH_TTFT_HEDGE_BUDGET_MS,
) -> LiveCoachRouteChain:
    """Describe the current live-coach route and any manual hedge pressure.

    ``openrouter_configured`` means a live OpenRouter client is wired into the
    agent. It does not mean this function may switch to it. The dispatch path
    remains controlled by ``DJCoHostAgent.llm_node`` and operator settings.
    """
    mode = (llm_mode or "direct").strip().lower()
    provider = (active_provider or "gemini").strip().lower()
    proxy_configured = bool(proxy_configured or mode == "proxy")
    openrouter_configured = bool(openrouter_configured or provider == "openrouter")
    active_route = "openrouter" if provider == "openrouter" else (
        "proxy" if proxy_configured else "direct"
    )
    live_model = resolve_model("live_coach")
    openrouter_model = resolve_model("live_coach_openrouter")

    candidates = (
        LiveCoachRouteCandidate(
            route="proxy",
            provider="gemini",
            model=live_model,
            active=active_route == "proxy",
            available=proxy_configured and not proxy_unavailable,
            reason=(
                "active"
                if active_route == "proxy" and not proxy_unavailable
                else "proxy_unavailable"
                if proxy_configured and proxy_unavailable
                else "not_configured"
            ),
        ),
        LiveCoachRouteCandidate(
            route="direct",
            provider="gemini",
            model=live_model,
            active=active_route == "direct",
            available=active_route == "direct",
            reason="active" if active_route == "direct" else "operator_switch_required",
        ),
        LiveCoachRouteCandidate(
            route="openrouter",
            provider="openrouter",
            model=openrouter_model,
            active=active_route == "openrouter",
            available=openrouter_configured,
            reason=(
                "active"
                if active_route == "openrouter"
                else "configured_operator_switch_required"
                if openrouter_configured
                else "not_configured"
            ),
        ),
    )

    ttft_over_budget = ttft_ms is not None and float(ttft_ms) > float(ttft_budget_ms)
    if active_route == "proxy" and proxy_unavailable:
        hedge_action: RouteHedgeAction = "operator_decision_required"
        hedge_reason = "proxy_unavailable"
    elif ttft_over_budget and active_route != "openrouter" and openrouter_configured:
        hedge_action = "operator_decision_required"
        hedge_reason = "ttft_over_budget_openrouter_configured"
    elif ttft_over_budget:
        hedge_action = "observe"
        hedge_reason = "ttft_over_budget_no_verified_alternate"
    else:
        hedge_action = "observe"
        hedge_reason = "within_budget"

    active_first = tuple(
        sorted(candidates, key=lambda candidate: (not candidate.active, candidate.route))
    )
    return LiveCoachRouteChain(
        active_route=active_route,
        active_provider=provider,
        active_model=active_model,
        candidates=active_first,
        hedge_action=hedge_action,
        hedge_reason=hedge_reason,
        ttft_ms=ttft_ms,
        ttft_budget_ms=ttft_budget_ms,
    )
