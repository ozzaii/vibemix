# SPDX-License-Identifier: Apache-2.0
"""Provider-routing contract for the OpenRouter brain path.

2026-06-11 measured outage: the brain pinned ``{"only": ["google-ai-studio"]}``
and the AI Studio pool 429-saturated at US peak ("temporarily rate-limited
upstream") — every live call died with no fallback and the shipped co-host
went fully silent (FATAL-SOFT). Empirical split the same evening: a
vertex-only call returned 200 with content while an ai-studio-only call
returned 429. These tests pin the resilience contract: first-party Google
providers ONLY (the 2026-05-21 TTFT intent — no slow third-party routes),
but never a single provider as a sole point of failure.
"""
from __future__ import annotations

import asyncio
from types import SimpleNamespace

from vibemix.agent.openrouter_llm import stream_or


class _FakeCompletions:
    def __init__(self) -> None:
        self.kwargs: dict | None = None

    async def create(self, **kwargs):
        self.kwargs = kwargs

        async def _empty():
            delta = SimpleNamespace(content="hold that low end.")
            yield SimpleNamespace(choices=[SimpleNamespace(delta=delta)])

        return _empty()


def _capture_create_kwargs() -> dict:
    completions = _FakeCompletions()
    client = SimpleNamespace(
        chat=SimpleNamespace(completions=completions)
    )

    async def _drain() -> None:
        async for _ in stream_or(
            client,  # type: ignore[arg-type]
            model="google/gemini-test",
            system_instruction="be a friend",
            contents=["packet text"],
        ):
            pass

    asyncio.run(_drain())
    assert completions.kwargs is not None
    return completions.kwargs


def test_provider_routing_has_first_party_fallback() -> None:
    provider = _capture_create_kwargs()["extra_body"]["provider"]
    only = provider["only"]
    # Both first-party Google pools allowed: latency sort still prefers the
    # fast one, but a saturated pool no longer silences the co-host.
    assert "google-ai-studio" in only
    assert "google-vertex" in only
    assert len(only) >= 2
    assert provider["sort"] == "latency"


def test_provider_routing_stays_first_party_only() -> None:
    only = _capture_create_kwargs()["extra_body"]["provider"]["only"]
    # The 2026-05-21 TTFT intent survives: no third-party resellers in the
    # allowed set — first-party Google pools only.
    assert all(p.startswith("google-") for p in only)


def test_reasoning_stays_minimal_and_excluded() -> None:
    reasoning = _capture_create_kwargs()["extra_body"]["reasoning"]
    # The empty-content probe trap fix rides the same extra_body — keep it
    # pinned so a provider edit can't silently drop it.
    assert reasoning == {"effort": "minimal", "exclude": True}
