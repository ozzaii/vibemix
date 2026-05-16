# SPDX-License-Identifier: Apache-2.0
"""GeminiContextCache — cache-floor + lifecycle + invalidate + refresh.

Pins: Pitfall 11 (cache-floor under-pad) + Pitfall 5 (implicit-cache floor
invariant — pad preserved post-v3.0 cleanup).

Plan 41-02 lock:
  - GEMINI_CACHE_TTL_S = 3600.0   (60-min — explicit cache refresh is now
                                   event-driven, not wall-clock)
  - GEMINI_CACHE_TOKEN_FLOOR = 1024  (Gemini rejects under-floor creation)
  - GEMINI_CACHE_REFRESH_S constant removed (no wall-clock refresh)
  - GeminiContextCache.refresh_loop() method removed (replaced by
    EvidenceRegistry-driven .refresh() callback — single-shot)
  - _CACHE_PAD_BLOCK deterministic across calls within a session — required
    for BOTH explicit cache-key stability AND Gemini 2026 implicit-cache hits
    on lean personas that fall below the 1024-token implicit floor.

These tests mock the google.genai client end-to-end — no real API calls.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from vibemix.agent.cache import (
    GEMINI_CACHE_TOKEN_FLOOR,
    GEMINI_CACHE_TTL_S,
    GeminiContextCache,
    _CACHE_PAD_BLOCK,
)
import vibemix.agent.cache as cache_module

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


# ---------- module constants — Plan 41-02 lock ----------


def test_ttl_constant_is_3600() -> None:
    """Plan 41-02 explicit TTL bump from 300s → 3600s (60 min)."""
    assert GEMINI_CACHE_TTL_S == 3600.0


def test_refresh_s_constant_removed() -> None:
    """Wall-clock refresh constant deleted — refresh is event-driven now."""
    assert not hasattr(cache_module, "GEMINI_CACHE_REFRESH_S")


def test_token_floor_unchanged() -> None:
    """Implicit-cache floor invariant — Gemini still rejects <1024-token
    caches; the pad block keeps lean personas above it."""
    assert GEMINI_CACHE_TOKEN_FLOOR == 1024
    # Pad block must be ≥4096 chars (≥1024 token-proxy) so any short body +
    # pad is guaranteed above the floor.
    assert len(_CACHE_PAD_BLOCK) >= 4096


# ---------- padded_body() — the floor-padding contract (Pitfall 5) ----------


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


def test_padded_body_invariant_preserved() -> None:
    """padded_body() called twice on the same body returns IDENTICAL strings —
    cache-key stability for both explicit caches AND Gemini 2026 implicit
    caching (Pitfall 5 — pad survives the v3.0 cleanup)."""
    cache = GeminiContextCache(client=MagicMock(), system_instruction_body="hi")
    a = cache.padded_body()
    b = cache.padded_body()
    assert a == b


def test_pad_block_unchanged_golden() -> None:
    """The deterministic pad block string is byte-identical to the pre-cleanup
    shape. Changing it would silently break Gemini implicit-cache hits for
    every existing session — same prefix bytes = same cache key."""
    # Golden invariants: header line + 80 padding lines of 60 'x' chars
    lines = _CACHE_PAD_BLOCK.split("\n")
    assert lines[0] == "# vibemix-pad-block-do-not-edit-cache-key-stability"
    assert len(lines) == 81
    assert all(ln == "# " + ("x" * 60) for ln in lines[1:])


# ---------- __init__ surface — Plan 41-02 cleanup ----------


def test_init_rejects_refresh_s_kwarg() -> None:
    """Pre-cleanup constructor accepted refresh_s=240.0 — that kwarg is gone.
    Passing it now must raise TypeError (unknown keyword argument)."""
    with pytest.raises(TypeError):
        GeminiContextCache(  # type: ignore[call-arg]
            client=MagicMock(),
            system_instruction_body="hi",
            refresh_s=240.0,
        )


def test_refresh_loop_method_removed() -> None:
    """Wall-clock background coroutine deleted — instances must not expose
    refresh_loop. Anything still calling it is a stale wiring bug."""
    cache = GeminiContextCache(client=MagicMock(), system_instruction_body="hi")
    assert not hasattr(cache, "refresh_loop")


def test_refresh_method_exists_and_is_awaitable() -> None:
    """The new event-driven refresh() chokepoint replaces refresh_loop."""
    cache = GeminiContextCache(client=MagicMock(), system_instruction_body="hi")
    assert hasattr(cache, "refresh")
    assert asyncio.iscoroutinefunction(cache.refresh)


# ---------- create() — the API call ----------


def test_create_calls_caches_create_with_padded_body_and_3600s_ttl() -> None:
    """create() builds CreateCachedContentConfig(ttl='3600s',
    system_instruction=padded_body) and passes it to client.aio.caches.create.
    """
    client = _mk_client(["cachedContents/A"])
    cache = GeminiContextCache(client=client, system_instruction_body="hi")
    asyncio.run(cache.create())
    assert client.aio.caches.create.call_args is not None
    cfg = client.aio.caches.create.call_args.kwargs["config"]
    assert cfg.ttl == "3600s"
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


# ---------- refresh() — atomic swap + graceful degradation ----------


def test_refresh_atomic_swap_new_name_then_delete_old() -> None:
    """refresh() creates a new cache, flips current_name A → B, then
    best-effort deletes the OLD name 'A' (atomic-swap order: new-before-old).
    """
    client = _mk_client(["cachedContents/A", "cachedContents/B"])
    cache = GeminiContextCache(client=client, system_instruction_body="hi")

    asyncio.run(cache.create())  # initial → A
    assert cache.current_name() == "cachedContents/A"
    asyncio.run(cache.refresh())  # → B + delete(A)
    assert cache.current_name() == "cachedContents/B"
    delete_calls = client.aio.caches.delete.call_args_list
    assert any(c.kwargs.get("name") == "cachedContents/A" for c in delete_calls), (
        f"refresh did not delete old name; delete_calls={delete_calls!r}"
    )


def test_refresh_handles_create_failure_keeps_old() -> None:
    """refresh() create-failure path: re-raises so the caller can log, BUT
    leaves current_name on the OLD value (graceful degradation — the cache
    never goes None mid-session from a refresh failure)."""
    client = _mk_client(
        ["cachedContents/A", RuntimeError("simulated create failure")]
    )
    cache = GeminiContextCache(client=client, system_instruction_body="hi")
    asyncio.run(cache.create())  # → A
    with pytest.raises(RuntimeError, match="simulated create failure"):
        asyncio.run(cache.refresh())
    # Old cache still current — graceful degradation.
    assert cache.current_name() == "cachedContents/A"
    # delete was NOT called — old preserved on create failure.
    client.aio.caches.delete.assert_not_called()


def test_refresh_with_no_prior_create_creates_first_cache() -> None:
    """refresh() called before any create(): old_name is None, so we just
    create the new cache and skip the delete. current_name flips None → A."""
    client = _mk_client(["cachedContents/A"])
    cache = GeminiContextCache(client=client, system_instruction_body="hi")
    assert cache.current_name() is None
    asyncio.run(cache.refresh())
    assert cache.current_name() == "cachedContents/A"
    # No old name to delete.
    client.aio.caches.delete.assert_not_called()
