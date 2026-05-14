# SPDX-License-Identifier: Apache-2.0
"""TTFTMeter — Plan 19-05 Task 1.

Rolling-average meter for Gemini Time-To-First-Token (TTFT) measurements.
The coach loop reads ``rolling_avg_ms()`` and feeds it to
``AckBank.should_fire(rolling_ttft_avg_ms=...)`` so an ack only fires when
Gemini is slow enough that the user perceives a gap (LATENCY-04 gate at
800ms).

Design choices:

  * **Default sentinel = 1500.0 ms.** When the meter has never seen a
    sample (cold session), ``rolling_avg_ms()`` returns 1500.0 — strictly
    greater than ``ACK_TTFT_GATE_MS`` (800.0). This means the FIRST event
    after warmup CAN fire an ack while Gemini is still cold and the user
    is waiting on the first response. Without the sentinel, the bank
    would be silent on the very first event because there's no prior
    measurement to gate against.
  * **Window = 8 samples.** Bounded deque so memory is constant and stale
    samples (e.g. from a network hiccup 30 seconds ago) eventually fall
    out of the average.
  * **No lock.** Single-threaded asyncio contract — same as
    ``runtime.cancel.CancelGate``. ``record_event_fired`` runs in
    ``DJCoHostAgent.set_next_event``, ``record_first_chunk`` runs in
    ``llm_node``'s streaming branch, ``rolling_avg_ms`` runs in the
    coach-loop tick. All on the same event loop.
  * **Pending-overwrite semantics.** A second ``record_event_fired``
    without an intervening ``record_first_chunk`` overwrites the pending
    pointer — the previous in-flight event was preempted (CancelGate) or
    failed (TimeoutError). The next ``record_first_chunk`` measures from
    the SECOND event_fired.
  * **No-pending no-op.** ``record_first_chunk`` with no pending event is
    a no-op — defensive against callers that record a chunk before any
    event has fired (legitimate during the cold-start LiveKit handshake
    where the agent may yield internal text outside an event-firing
    flow).
"""

from __future__ import annotations

import time
from collections import deque
from collections.abc import Callable


class TTFTMeter:
    """Rolling average of Gemini TTFT (event_fired → first_chunk) in ms.

    Thread-safety: NOT thread-safe. Single-threaded asyncio invariant.
    """

    def __init__(
        self,
        *,
        window: int = 8,
        default_ms: float = 1500.0,
        time_fn: Callable[[], float] = time.monotonic,
    ) -> None:
        self._window = window
        self._default_ms = default_ms
        self._time_fn = time_fn
        self._samples: deque[float] = deque(maxlen=window)
        self._pending: float | None = None

    def record_event_fired(self, now: float | None = None) -> None:
        """Record the moment an event fired (the start of the TTFT window).

        Called from ``DJCoHostAgent.set_next_event``. Overwriting an existing
        pending pointer is intentional — the previous event was preempted /
        failed and its TTFT is unmeasurable.
        """
        self._pending = self._time_fn() if now is None else now

    def record_first_chunk(self, now: float | None = None) -> None:
        """Record the moment the first non-empty Gemini chunk arrived.

        Called from ``DJCoHostAgent.llm_node`` on the first non-empty stream
        yield. No-op when no event_fired is currently pending (defensive —
        first-chunk arriving with no pending fire means TTFT cannot be
        measured).
        """
        if self._pending is None:
            return
        end = self._time_fn() if now is None else now
        ms = (end - self._pending) * 1000.0
        self._samples.append(ms)
        self._pending = None

    def rolling_avg_ms(self) -> float:
        """Return the rolling-average TTFT in ms, or default_ms when empty."""
        if not self._samples:
            return self._default_ms
        return sum(self._samples) / len(self._samples)

    def samples_count(self) -> int:
        """Return the number of samples currently in the window."""
        return len(self._samples)
