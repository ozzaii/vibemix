# SPDX-License-Identifier: Apache-2.0
"""GeminiContextCache — Gemini context-caching layer.

Caches the static prompt prefix (system instruction + persona + Phase 18
citation grammar) on Gemini's server side, shaving 500-1500ms TTFT per call
by reusing the cached prefix across the session.

**Plan 41-02 cleanup (v3.0):**

The wall-clock ``refresh_loop`` background task is GONE. Refresh is now
event-driven — ``EvidenceRegistry`` invokes ``cache.refresh()`` through a
debounced callback whenever observations mutate. This eliminates dead-time
refresh churn (the 4-min ticker created new caches even when nothing
changed) and lets the explicit cache surface follow the data, not the wall
clock. TTL bumped 300s → 3600s (60min) to match the lower refresh rate.

**Pitfall 5 — pad invariant survives the cleanup.** ``_CACHE_PAD_BLOCK``
+ ``padded_body()`` are KEPT. Gemini 2026 implicit caching triggers only
on prefix ≥1024 tokens; vibemix's natural prompt prefix sits around
800-1200 tokens depending on persona, and the lean personas fall below
the implicit-cache floor without the pad. The deterministic pad keeps
implicit hit-rate stable even when explicit caching is disabled.

Three contracts this module owns:

  1. **padded_body() never returns under-floor.** Token-proxy is char-len // 4
     (matches Plan 19-02; project has no tiktoken dep). Bodies <1024 token-
     proxy get the deterministic ``_CACHE_PAD_BLOCK`` appended. Determinism
     is REQUIRED — Gemini's implicit cache hashes the prefix, so a varying
     pad would defeat the cache hit. The pad invariant also covers explicit
     caching for sessions where the body is short.

  2. **refresh() is the atomic-swap chokepoint** (replaces refresh_loop).
     ``EvidenceRegistry.write()`` schedules a debounced callback (5-10s
     debounce + 30s min-interval). On fire, refresh() creates a NEW cache,
     swaps ``_current_name`` to the new name, THEN deletes the old name.
     On create failure, the old cache is preserved (graceful degradation —
     ``current_name()`` never returns None mid-session unless explicit
     invalidate fires).

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

import sys
import time
from typing import TYPE_CHECKING

from google.genai import types

from vibemix.agent.config import LLM_MODEL

if TYPE_CHECKING:  # pragma: no cover — type-only
    from google import genai

# ---- Module constants — Plan 41-02 lock ----

# 60-min TTL — explicit cache only refreshes on EvidenceRegistry mutation;
# the longer ceiling avoids needless re-creates during quiet sets where
# observations don't churn.
GEMINI_CACHE_TTL_S = 3600.0

# (Plan 41-02) The wall-clock refresh constant + refresh_loop method were
# removed. Refresh is now triggered by EvidenceRegistry.write() through a
# debounced callback. See state/evidence_registry.py for the schedule logic.

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

    Lifecycle (Plan 41-02):
      1. ``await cache.create()`` — uploads padded body to Gemini, stores name
      2. ``cache.current_name()`` — returns name string (None if uncreated)
      3. ``await cache.refresh()`` — invoked from EvidenceRegistry.write()
         callback (debounced upstream); atomically swaps to a freshly-created
         cache, deletes the old name. NOT a long-running loop — single shot
         per call.
      4. ``await cache.invalidate()`` — clears _current_name + best-effort
         server-side delete (called by CancelGate-side cancel-and-refire)

    All API calls are async — caller drives them on the asyncio event loop.
    Thread safety: caller is responsible for not racing create() / invalidate()
    against refresh(). The EvidenceRegistry debounce guarantees at most one
    refresh() in flight at a time, and the dj_cohost wiring serializes all
    three on the main loop so this is fine in practice.
    """

    def __init__(
        self,
        client: "genai.Client",
        system_instruction_body: str,
        *,
        model: str = LLM_MODEL,
        ttl_s: float = GEMINI_CACHE_TTL_S,
        time_fn=time.monotonic,
        profile_section: str = "",
    ) -> None:
        self._client = client
        self._body = system_instruction_body
        self._model = model
        self._ttl_s = ttl_s
        self._time_fn = time_fn
        self._current_name: str | None = None
        # Plan 32-02 / PROFILE-03 — optional long-term DJ profile section.
        # Concatenated AFTER system_instruction_body but BEFORE the deterministic
        # pad block. Empty string default = byte-identical to the pre-Phase-32
        # path. P60: profile lives in the CACHE body, NEVER in the per-turn
        # llm_node prompt — DJCoHostAgent.llm_node has no reference to it.
        self._profile_section: str = profile_section

    def padded_body(self) -> str:
        """Return system_instruction_body + profile_section, padded above the
        1024-token Gemini cache floor if needed.

        If the combined (body + profile_section) char-length // 4 is already
        ≥ floor, returns the combined body unchanged. Else appends the
        deterministic _CACHE_PAD_BLOCK. The pad block is fixed-content so
        identical inputs (same body + same profile_section) produce identical
        padded outputs (cache-key stability invariant — Pitfall 11 + P60)."""
        combined = self._body + self._profile_section
        if (len(combined) // 4) >= GEMINI_CACHE_TOKEN_FLOOR:
            return combined
        return combined + "\n\n" + _CACHE_PAD_BLOCK

    async def create(self) -> str | None:
        """Upload the padded body to Gemini's cache store; store + return name.

        On exception, re-raises. Callers (e.g. refresh()) restore the OLD
        cache when create raises so the cache never goes None mid-session."""
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
            # Re-raise; caller (refresh()) handles the keep-old-on-failure
            # semantics by capturing old_name before invoking us.
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

        Used by refresh() to delete the OLD cache name AFTER swapping
        _current_name to the NEW one (atomic swap)."""
        try:
            await self._client.aio.caches.delete(name=name)
        except Exception as e:
            print(f"[cache] delete failed for {name}: {e}", file=sys.stderr)

    async def refresh(self) -> None:
        """Atomic-swap re-create — Plan 41-02 replacement for refresh_loop.

        Called from ``EvidenceRegistry.write()`` through a debounced callback
        (5s debounce + 30s min-interval guard — see
        ``state/evidence_registry.py``). Single-shot per call; the registry
        owns the schedule, this method owns the swap.

        Order (atomic-swap correctness):
          1. capture ``old_name = self._current_name``
          2. call ``create()`` → flips ``_current_name`` to the NEW name on
             success; raises on failure (current_name unchanged)
          3. on success, best-effort delete the old name (server-side delete
             may fail — the old cache will TTL-expire anyway, so we swallow)
          4. on failure (create raised): restore ``_current_name = old_name``
             so the OLD cache stays current → graceful degradation; never
             goes None mid-session unless explicit invalidate fires

        Re-raises the create exception so the caller (registry callback) can
        log it. The state mutation (current_name restored to old) happens
        BEFORE the re-raise so the cache is always in a valid state when
        the exception unwinds.
        """
        old_name = self._current_name
        try:
            await self.create()
        except Exception:
            # create() may have cleared _current_name via the re-raise path;
            # restore to old for graceful degradation, then re-raise so the
            # caller can log.
            self._current_name = old_name
            raise
        if old_name and old_name != self._current_name:
            await self._invalidate_name(old_name)
