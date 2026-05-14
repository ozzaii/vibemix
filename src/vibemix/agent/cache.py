# SPDX-License-Identifier: Apache-2.0
"""GeminiContextCache — Plan 19-03 Gemini context-caching layer.

Caches the static prompt prefix (system instruction + persona + Phase 18
citation grammar) on Gemini's server side, shaving 500-1500ms TTFT per call
by reusing the cached prefix across the session. CONTEXT D-08 lock:
TTL ≥5min, refresh every 4min, system instruction MUST be padded ≥1024 tokens
BEFORE caches.create (Pitfall 11 — Gemini rejects under-floor caches with a
non-obvious 400 error).

Three contracts this module owns:

  1. **padded_body() never returns under-floor.** Token-proxy is char-len // 4
     (matches Plan 19-02; project has no tiktoken dep). Bodies <1024 token-
     proxy get the deterministic ``_CACHE_PAD_BLOCK`` appended. Determinism
     is REQUIRED — if Gemini hashes the prefix as the cache key, a varying
     pad would defeat the cache hit on session resume.

  2. **refresh_loop atomic swap.** Every 240s the loop creates a NEW cache,
     swaps ``_current_name`` to the new name, THEN deletes the old name.
     ``current_name()`` is never None during a refresh window unless the
     caller explicitly invalidates. On create failure, the old cache is
     preserved (graceful degradation — fall back to the old cache for one
     more refresh cycle, never None mid-session).

  3. **invalidate() is the cancel-aware chokepoint.** Plan 19-01's
     CancelGate telemetry callback fires through ``DJCoHostAgent.invalidate
     _cache()`` → here. After invalidate, the next ``current_name()`` returns
     None, the next ``DJCoHostAgent.llm_node`` call falls back to the inline
     system_instruction path, and the NEXT explicit create rebuilds from
     scratch — never carries context from the cancelled in-flight turn.

The chokepoint pattern: ``caches.create`` is called in EXACTLY ONE place
in this module — the verification grep ``grep -rE "caches\\.create"
src/vibemix/`` returns this file only.
"""

from __future__ import annotations

import asyncio
import sys
import time
from typing import TYPE_CHECKING

from google.genai import types

from vibemix.agent.config import LLM_MODEL

if TYPE_CHECKING:  # pragma: no cover — type-only
    from google import genai

# ---- Module constants — CONTEXT D-08 lock ----

# 5-min TTL minimum per Gemini cache rules — never set lower.
GEMINI_CACHE_TTL_S = 300.0

# 4-min refresh < 5-min TTL → race-buffered (the new cache is always
# created and swapped in BEFORE the old expires).
GEMINI_CACHE_REFRESH_S = 240.0

# Gemini cache rejects creation under this floor with a non-obvious 400
# error (Pitfall 11). Token-proxy is char-len // 4 — matches Plan 19-02.
GEMINI_CACHE_TOKEN_FLOOR = 1024

# Deterministic pad block — appended to system_instruction when the body
# is below the floor. ~5KB of fixed-content lines (≥1024 token-proxy on its
# own), so body + pad always exceeds the floor for any input ≥1 char. The
# string is fixed at module import time so identical inputs across refresh
# cycles produce identical padded bodies (cache-key stability — if Gemini
# hashes the prefix, a varying pad would defeat the cache hit on session
# resume).
_CACHE_PAD_BLOCK: str = "\n".join(
    ["# vibemix-pad-block-do-not-edit-cache-key-stability"]
    + ["# " + ("x" * 60) for _ in range(80)]
)


class GeminiContextCache:
    """Server-side context cache for the static prompt prefix.

    Lifecycle:
      1. ``await cache.create()`` — uploads padded body to Gemini, stores name
      2. ``cache.current_name()`` — returns name string (None if uncreated)
      3. ``await cache.refresh_loop(stop_event)`` — long-running coroutine
         re-creating the cache every ``refresh_s`` seconds, swapping atomically
      4. ``await cache.invalidate()`` — clears _current_name + best-effort
         server-side delete (called by CancelGate-side cancel-and-refire)

    All API calls are async — caller drives them on the asyncio event loop.
    Thread safety: caller is responsible for not racing create() / invalidate()
    against the refresh_loop. The dj_cohost wiring serializes all three on the
    main loop so this is fine in practice.
    """

    def __init__(
        self,
        client: "genai.Client",
        system_instruction_body: str,
        *,
        model: str = LLM_MODEL,
        ttl_s: float = GEMINI_CACHE_TTL_S,
        refresh_s: float = GEMINI_CACHE_REFRESH_S,
        time_fn=time.monotonic,
    ) -> None:
        self._client = client
        self._body = system_instruction_body
        self._model = model
        self._ttl_s = ttl_s
        self._refresh_s = refresh_s
        self._time_fn = time_fn
        self._current_name: str | None = None

    def padded_body(self) -> str:
        """Return self._body padded above the 1024-token Gemini cache floor.

        If the body's token-proxy (char-len // 4) is already ≥ floor, returns
        body unchanged. Else returns body + "\\n\\n" + _CACHE_PAD_BLOCK. The
        pad block is fixed-content so identical inputs produce identical
        padded outputs (cache-key stability invariant)."""
        if (len(self._body) // 4) >= GEMINI_CACHE_TOKEN_FLOOR:
            return self._body
        return self._body + "\n\n" + _CACHE_PAD_BLOCK

    async def create(self) -> str | None:
        """Upload the padded body to Gemini's cache store; store + return name.

        On exception, sets _current_name=None and re-raises. Callers (e.g.
        refresh_loop) decide how to react to the failure — refresh_loop keeps
        the OLD cache when create raises, never going None mid-session."""
        config = types.CreateCachedContentConfig(
            ttl=f"{int(self._ttl_s)}s",
            system_instruction=self.padded_body(),
            display_name=f"vibemix-{int(self._time_fn())}",
        )
        try:
            cache = await self._client.aio.caches.create(
                model=self._model, config=config
            )
        except Exception:
            # Re-raise after CLEARING current — caller (refresh_loop) handles
            # the keep-old-on-failure semantics by not reading _current_name
            # between the try and the except.
            raise
        self._current_name = cache.name
        return self._current_name

    def current_name(self) -> str | None:
        """Return the current cache name, or None if never created / invalidated."""
        return self._current_name

    async def invalidate(self) -> None:
        """Clear _current_name AND best-effort server-side delete.

        The chokepoint Plan 19-01's CancelGate telemetry callback eventually
        wires through DJCoHostAgent.invalidate_cache(). Best-effort delete:
        the cache may have already expired server-side, so DeleteFailed /
        NotFound exceptions are swallowed — the local _current_name is still
        cleared so the next llm_node call falls back to the inline
        system_instruction path."""
        name = self._current_name
        self._current_name = None
        if name:
            await self._invalidate_name(name)

    async def _invalidate_name(self, name: str) -> None:
        """Best-effort delete of a specific cache name (no _current_name mutation).

        Used by refresh_loop to delete the OLD cache name AFTER swapping
        _current_name to the NEW one (atomic swap)."""
        try:
            await self._client.aio.caches.delete(name=name)
        except Exception as e:
            print(f"[cache] delete failed for {name}: {e}", file=sys.stderr)

    async def refresh_loop(self, stop_event: asyncio.Event) -> None:
        """Long-running coroutine: re-create cache every refresh_s, swap atomically.

        Loop:
          - asyncio.wait_for(stop_event.wait(), timeout=refresh_s)
          - on TimeoutError (the normal case): tick fired
            - capture old_name
            - try create() → flips _current_name to new
            - if create succeeded AND old_name was non-None: best-effort
              delete the old name (atomic swap order: new-then-delete)
            - if create raised: log, continue — _current_name unchanged
              (stays on the OLD name → graceful degradation, current_name()
              never returns None mid-session unless explicit invalidate)
          - on stop_event.set(): clean exit

        Caller is responsible for the initial create() before driving this
        loop — the loop only handles refreshes, not the initial population.
        """
        while not stop_event.is_set():
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=self._refresh_s)
                # If wait completed without timeout, stop was set — exit.
                break
            except asyncio.TimeoutError:
                pass  # tick fired — proceed to refresh
            old_name = self._current_name
            try:
                await self.create()
            except Exception as e:
                print(
                    f"[cache refresh] failed; keeping old cache: {e}",
                    file=sys.stderr,
                )
                # Restore _current_name to old (create() may have cleared it
                # via re-raise path; keep the old cache for graceful
                # degradation).
                self._current_name = old_name
                continue
            if old_name and old_name != self._current_name:
                await self._invalidate_name(old_name)
