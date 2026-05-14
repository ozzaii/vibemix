# SPDX-License-Identifier: Apache-2.0
"""CitationIpcShim — Phase 20 in-process buffer satisfying the
``await ipc_bus.emit(dict)`` duck-typed contract in ``coach_loop``.

Plan 20-04 added the ``ipc.session.citation`` publish gate to
``vibemix.runtime.coach.coach_loop`` (the 2s-cadence Tauri Settings →
Diagnostics surface). The gate is duck-typed against any object that
exposes ``async emit(dict) -> None`` — the real wiring path is the
``WizardBus`` / ``IpcBus`` class (``vibemix.runtime.ws_bus``) used by
``--session`` runtime.

The full live runtime (``python -m vibemix`` default — no flag) uses
``ws_broadcast`` for the mascot bus instead. Both classes bind
``127.0.0.1:8765`` and are mutually exclusive at the OS-port level — so
``ws_broadcast`` and ``WizardBus`` cannot run side-by-side. Wiring the
SessionCitation envelopes onto the mascot WS clients is a v2.x follow-up
that requires either:
  1. refactoring ``ws_broadcast`` to expose its ``clients`` set so a
     companion emitter can multiplex onto the same socket, or
  2. introducing a multiplexing bus class that owns one ``websockets.serve``
     and routes both 30Hz mascot snapshots + 0.5Hz citation envelopes.

Until then, ``CitationIpcShim`` is the surgical close to Plan 20-04's
``citation_wired`` gate — it gives ``coach_loop`` a non-None
``ipc_bus`` reference so the publish path FIRES (telemetry callable
invoked every 2s, `last_citation_publish_at` updated, no stderr spam).
The emitted dicts buffer into a bounded deque ready for the v2.x
follow-up to drain.

Thread-safety: NOT thread-safe. Same contract as everything else in the
coach loop — single-threaded asyncio. ``emit`` is async only because
the upstream call site (``coach_loop``) ``await``s it; the body has no
I/O and no real await points.
"""

from __future__ import annotations

from collections import deque


class CitationIpcShim:
    """In-process buffered ``ipc_bus`` shim — bounded ``deque`` of emitted dicts.

    Args:
        maxlen: Buffer capacity. Default 64 — at the Plan 20-04 publish
            cadence (every 2s) that's ~2 minutes of history, plenty for a
            v2.x WS-wiring follow-up to drain before the FIFO eviction
            kicks in.

    Public surface (duck-typed against ``IpcBus`` for ``coach_loop`` callers):
        ``await emit(msg: dict) -> None`` — append ``msg``; oldest evicts
            once buffer is full (``deque(maxlen=...)`` semantics).
        ``snapshot() -> tuple[dict, ...]`` — frozen tuple snapshot for
            tests + future v2.x WS multiplex follow-up.
        ``__len__() -> int`` — buffered count.

    The shim never raises from ``emit`` even if ``msg`` is not a dict —
    the bounded buffer accepts any value (we type-hint dict because that's
    the canonical shape from ``SessionCitation.to_json``).
    """

    DEFAULT_MAXLEN = 64

    def __init__(self, maxlen: int = DEFAULT_MAXLEN) -> None:
        self._buffer: deque[dict] = deque(maxlen=maxlen)

    async def emit(self, msg: dict) -> None:
        """Append ``msg`` to the bounded buffer. No I/O, no actual await
        point — kept ``async`` because callers ``await`` the call."""
        self._buffer.append(msg)

    def snapshot(self) -> tuple[dict, ...]:
        """Return a frozen tuple snapshot of the buffer for introspection.

        Mutating the returned tuple is impossible (tuples are immutable);
        callers cannot leak a buffer reference. Cost is O(N) over the
        bounded buffer (≤ maxlen) — fast.
        """
        return tuple(self._buffer)

    def __len__(self) -> int:
        return len(self._buffer)
