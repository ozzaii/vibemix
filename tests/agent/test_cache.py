# SPDX-License-Identifier: Apache-2.0
"""GeminiContextCache — Plan 19-03 cache-floor + lifecycle + invalidate.

Pins: Pitfall 11 (cache-floor under-pad) closes here.

CONTEXT D-08 hard rules:
  - GEMINI_CACHE_TTL_S = 300.0  (5-min minimum, never less)
  - GEMINI_CACHE_REFRESH_S = 240.0  (4-min refresh < 5-min TTL → race-buffered)
  - GEMINI_CACHE_TOKEN_FLOOR = 1024  (Gemini rejects cache creation under floor)
  - _CACHE_PAD_BLOCK is deterministic across calls within a session (cache-key
    stability if Gemini hashes the prefix).

These tests mock the google.genai client end-to-end — no real API calls.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from vibemix.agent.cache import (
    GEMINI_CACHE_REFRESH_S,
    GEMINI_CACHE_TOKEN_FLOOR,
    GEMINI_CACHE_TTL_S,
    GeminiContextCache,
    _CACHE_PAD_BLOCK,
)

# ---------- helpers ----------


def _mk_client(create_returns: list, *, delete_raises: bool = False) -> MagicMock:
    """Build a mock genai client with .aio.caches.create / .delete async mocks.

    create_returns: list of (name | Exception) yielded in order on each
    create() call. delete_raises: when True, .delete raises RuntimeError.
    """
    client = MagicMock()
    client.aio = MagicMock()
    client.aio.caches = MagicMock()

    create_iter = iter(create_returns)

    async def _create(*_a, **_kw):
        nxt = next(create_iter)
        if isinstance(nxt, Exception):
            raise nxt
        cache = MagicMock()
        cache.name = nxt
        return cache

    client.aio.caches.create = AsyncMock(side_effect=_create)

    async def _delete(*_a, **_kw):
        if delete_raises:
            raise RuntimeError("simulated delete failure")
        return None

    client.aio.caches.delete = AsyncMock(side_effect=_delete)
    return client


# ---------- module constants ----------


def test_module_constants_locked() -> None:
    """The three numeric constants are the CONTEXT D-08 lock — assert exact values."""
    assert GEMINI_CACHE_TTL_S == 300.0
    assert GEMINI_CACHE_REFRESH_S == 240.0
    assert GEMINI_CACHE_TOKEN_FLOOR == 1024
    # Pad block must be ≥4096 chars (≥1024 token-proxy) so any short body +
    # pad is guaranteed above the floor.
    assert len(_CACHE_PAD_BLOCK) >= 4096


# ---------- padded_body() — the floor-padding contract ----------


def test_pad_block_pushes_short_body_above_floor() -> None:
    """A short body ("hi" → 2 chars / 0.5 token-proxy) gets padded so the
    final padded_body() is ≥1024 token-proxy."""
    cache = GeminiContextCache(client=MagicMock(), system_instruction_body="hi")
    out = cache.padded_body()
    assert (len(out) // 4) >= GEMINI_CACHE_TOKEN_FLOOR


def test_pad_block_skipped_when_body_already_above_floor() -> None:
    """A body that's already ≥1024 token-proxy gets returned unchanged
    (no pad appended)."""
    body = "x" * 5000  # 1250 token-proxy ≥ 1024 floor
    cache = GeminiContextCache(client=MagicMock(), system_instruction_body=body)
    assert cache.padded_body() == body


def test_pad_block_is_deterministic() -> None:
    """padded_body() called twice on the same body returns IDENTICAL strings —
    cache-key stability if Gemini hashes the prefix."""
    cache = GeminiContextCache(client=MagicMock(), system_instruction_body="hi")
    a = cache.padded_body()
    b = cache.padded_body()
    assert a == b


# ---------- create() — the API call ----------


def test_create_calls_caches_create_with_padded_body_and_300s_ttl() -> None:
    """create() builds CreateCachedContentConfig(ttl='300s', system_instruction
    =padded_body) and passes it to client.aio.caches.create."""
    client = _mk_client(["cachedContents/A"])
    cache = GeminiContextCache(client=client, system_instruction_body="hi")
    asyncio.run(cache.create())
    assert client.aio.caches.create.call_args is not None
    cfg = client.aio.caches.create.call_args.kwargs["config"]
    assert cfg.ttl == "300s"
    assert cfg.system_instruction == cache.padded_body()


def test_create_stores_returned_name_into_current_name() -> None:
    """After create(), current_name() returns the cache.name string."""
    client = _mk_client(["cachedContents/A"])
    cache = GeminiContextCache(client=client, system_instruction_body="hi")
    name = asyncio.run(cache.create())
    assert name == "cachedContents/A"
    assert cache.current_name() == "cachedContents/A"


# ---------- invalidate() — the cancel-aware clear ----------


def test_invalidate_clears_current_name_and_calls_delete() -> None:
    """invalidate() sets _current_name=None AND calls client.aio.caches.delete
    with the prior name."""
    client = _mk_client(["cachedContents/A"])
    cache = GeminiContextCache(client=client, system_instruction_body="hi")
    asyncio.run(cache.create())
    assert cache.current_name() == "cachedContents/A"

    asyncio.run(cache.invalidate())
    assert cache.current_name() is None
    client.aio.caches.delete.assert_called_once()
    delete_call = client.aio.caches.delete.call_args
    assert delete_call.kwargs.get("name") == "cachedContents/A"


def test_invalidate_swallows_delete_exception() -> None:
    """delete() raising must not propagate — the cache may already be expired
    server-side. _current_name still cleared."""
    client = _mk_client(["cachedContents/A"], delete_raises=True)
    cache = GeminiContextCache(client=client, system_instruction_body="hi")
    asyncio.run(cache.create())
    # MUST NOT raise.
    asyncio.run(cache.invalidate())
    assert cache.current_name() is None


def test_invalidate_no_op_when_never_created() -> None:
    """invalidate() called before create() is a clean no-op (no delete fired)."""
    client = _mk_client([])
    cache = GeminiContextCache(client=client, system_instruction_body="hi")
    asyncio.run(cache.invalidate())  # must not raise
    assert cache.current_name() is None
    client.aio.caches.delete.assert_not_called()


# ---------- refresh_loop() — atomic swap + graceful degradation ----------


def test_refresh_loop_atomic_swap() -> None:
    """At refresh tick: create() returns a new name; current_name flips A→B
    AFTER create completes; delete called with old name 'A'."""
    client = _mk_client(["cachedContents/A", "cachedContents/B"])
    cache = GeminiContextCache(
        client=client, system_instruction_body="hi", refresh_s=0.05
    )

    async def _drive() -> None:
        await cache.create()  # initial → A
        assert cache.current_name() == "cachedContents/A"
        stop = asyncio.Event()
        loop_task = asyncio.create_task(cache.refresh_loop(stop))
        # wait long enough for one refresh tick (refresh_s=0.05 → ~0.15s safe)
        await asyncio.sleep(0.15)
        stop.set()
        try:
            await asyncio.wait_for(loop_task, timeout=1.0)
        except asyncio.TimeoutError:
            loop_task.cancel()

    asyncio.run(_drive())
    assert cache.current_name() == "cachedContents/B"
    # delete called with the OLD name "A" (atomic swap: new created BEFORE
    # old deleted).
    delete_calls = client.aio.caches.delete.call_args_list
    assert any(c.kwargs.get("name") == "cachedContents/A" for c in delete_calls), (
        f"refresh did not delete old name; delete_calls={delete_calls!r}"
    )


def test_refresh_loop_keeps_old_on_create_failure() -> None:
    """create() raising on refresh keeps the old _current_name AND does NOT
    fire delete for the old name."""
    client = _mk_client(
        ["cachedContents/A", RuntimeError("simulated create failure")]
    )
    cache = GeminiContextCache(
        client=client, system_instruction_body="hi", refresh_s=0.05
    )

    async def _drive() -> None:
        await cache.create()  # → A
        stop = asyncio.Event()
        loop_task = asyncio.create_task(cache.refresh_loop(stop))
        await asyncio.sleep(0.15)
        stop.set()
        try:
            await asyncio.wait_for(loop_task, timeout=1.0)
        except asyncio.TimeoutError:
            loop_task.cancel()

    asyncio.run(_drive())
    # Old cache still current — graceful degradation.
    assert cache.current_name() == "cachedContents/A"
    # delete was NOT called (old name preserved on create failure).
    client.aio.caches.delete.assert_not_called()


def test_refresh_loop_stops_on_stop_event() -> None:
    """stop_event.set() inside the wait → loop exits within 1s."""
    client = _mk_client(["cachedContents/A"])
    cache = GeminiContextCache(
        client=client, system_instruction_body="hi", refresh_s=10.0
    )

    async def _drive() -> bool:
        await cache.create()
        stop = asyncio.Event()
        loop_task = asyncio.create_task(cache.refresh_loop(stop))
        await asyncio.sleep(0.05)  # let loop enter the wait
        stop.set()
        try:
            await asyncio.wait_for(loop_task, timeout=1.0)
            return True
        except asyncio.TimeoutError:
            loop_task.cancel()
            return False

    exited_cleanly = asyncio.run(_drive())
    assert exited_cleanly, "refresh_loop did not exit within 1s of stop_event.set()"
