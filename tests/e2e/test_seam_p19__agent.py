# SPDX-License-Identifier: Apache-2.0
"""Phase 37 Plan 37-01 seam test — P19 → agent.

Source: ``src/vibemix/agent/cache.py`` (GeminiContextCache)
Sink:   ``src/vibemix/agent/dj_cohost.py`` (DJCoHostAgent.llm_node)

The agent reads ``cache.current_name()`` per llm_node call and switches
between three states (disabled / cold / warm). The seam is the
``current_name() -> cached_content`` contract.

This test exercises the REAL GeminiContextCache (with a fake Gemini
client — the seam under test is cache→agent, NOT cache→Gemini). The
external Gemini API IS mocked (per CONTEXT decision: external IO is
mockable, the seam is not).

Verifies:
1. Real cache.create() persists ``current_name`` for the agent to read.
2. Real cache.invalidate() clears ``current_name`` (agent falls back).
3. ``padded_body()`` returns ≥1024 token-proxy chars (Pitfall 11 floor —
   the agent's cache wiring depends on this contract).
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.mark.e2e
def test_real_cache_padded_body_passes_token_floor() -> None:
    """Real GeminiContextCache always produces ≥1024 token-proxy body.

    DJCoHostAgent depends on this — sending an under-floor cache body to
    Gemini fails with a non-obvious 400 (Pitfall 11). Real cache class
    must enforce the floor for any input.
    """
    from vibemix.agent.cache import GEMINI_CACHE_TOKEN_FLOOR, GeminiContextCache

    fake_client = MagicMock()
    cache = GeminiContextCache(
        client=fake_client,
        system_instruction_body="tiny body",
    )
    body = cache.padded_body()
    # Token-proxy is char-len // 4.
    assert (len(body) // 4) >= GEMINI_CACHE_TOKEN_FLOOR


@pytest.mark.e2e
def test_real_cache_create_then_current_name_round_trip() -> None:
    """cache.create() persists the server name that the agent reads.

    The agent calls ``self._cache.current_name()`` once per llm_node.
    This seam test pins the create→current_name contract end-to-end on
    the real class (with the Gemini client itself mocked — that's
    external IO, not the seam).
    """
    import asyncio

    from vibemix.agent.cache import GeminiContextCache

    fake_client = MagicMock()
    # Mimic the async caches.create() Gemini SDK call.
    fake_cached = SimpleNamespace(name="cachedContents/abc123")
    fake_client.aio.caches.create = AsyncMock(return_value=fake_cached)

    cache = GeminiContextCache(
        client=fake_client,
        system_instruction_body="x" * 5000,  # well above floor
    )
    assert cache.current_name() is None  # cold

    name = asyncio.run(cache.create())
    assert name == "cachedContents/abc123"
    # The agent reads this same surface per llm_node call.
    assert cache.current_name() == "cachedContents/abc123"


@pytest.mark.e2e
def test_real_cache_invalidate_clears_name_for_agent_fallback() -> None:
    """invalidate() drops the name so agent falls back to cold path.

    CancelGate → DJCoHostAgent.invalidate_cache() → GeminiContextCache.
    invalidate(). After invalidate the agent MUST fall through to the
    cold (system_instruction inline) branch on its next llm_node call.
    """
    import asyncio

    from vibemix.agent.cache import GeminiContextCache

    fake_client = MagicMock()
    fake_cached = SimpleNamespace(name="cachedContents/abc123")
    fake_client.aio.caches.create = AsyncMock(return_value=fake_cached)
    fake_client.aio.caches.delete = AsyncMock(return_value=None)

    cache = GeminiContextCache(
        client=fake_client,
        system_instruction_body="x" * 5000,
    )
    asyncio.run(cache.create())
    assert cache.current_name() == "cachedContents/abc123"

    asyncio.run(cache.invalidate())
    assert cache.current_name() is None, (
        "after invalidate the agent's llm_node branch must fall to cold"
    )
