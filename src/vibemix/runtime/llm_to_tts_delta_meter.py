# SPDX-License-Identifier: Apache-2.0
"""LLMToTTSDeltaMeter — Plan 41-04 Task 1 (LAT-04).

Records the per-turn delta from ``event_fired`` (LLM-invoke start) to
``first_sentence_yielded`` (first head pushed to TTS) in milliseconds.

Why a separate meter from :class:`vibemix.runtime.ttft.TTFTMeter`:

  * ``TTFTMeter`` measures ``event_fired → first_chunk_received`` — the
    raw network-level TTFT. That delta is bounded BELOW by the Gemini
    stream's first-byte latency.
  * ``LLMToTTSDeltaMeter`` measures ``event_fired →
    first_sentence_yielded`` — the perceived-latency boundary. The
    streaming pipe-through refactor targets this delta directly: yield
    earlier (mid-stream sentence boundary) → smaller delta → less time
    between event and first audio chunk playing.

  Subtracting TTFT from this delta gives "stream-duration before first
  sentence boundary" — the actual head accumulator residence time. CI
  threshold in Plan 41-07 locks against the synthetic replay baseline.

Design parity with TTFTMeter:
  * No lock — single-threaded asyncio invariant.
  * Injectable ``time_fn`` for deterministic tests.
  * Pending-pointer + record contract — ``start_turn`` arms,
    ``record_first_sentence`` measures; double-arm overwrites; no-pending
    record is a no-op.

Schema:
  ``recorder.log_event("llm_to_tts_delta_ms", delta_ms=<int>, **extra)``.
  Payload carries the delta and any caller-provided extras (e.g. event
  type, response_id). NEVER carries head content (T-41-04-06).
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any


class LLMToTTSDeltaMeter:
    """Per-turn (event_fired → first_sentence_yielded) delta in ms.

    Thread-safety: NOT thread-safe. Single-threaded asyncio invariant.
    """

    def __init__(
        self,
        *,
        time_fn: Callable[[], float] = time.monotonic,
    ) -> None:
        self._time_fn = time_fn
        self._event_fired_at: float | None = None
        self._first_sentence_at: float | None = None

    def start_turn(self, now: float | None = None) -> None:
        """Arm the meter for a new turn.

        Resets ``_first_sentence_at`` so a previous turn's value doesn't
        leak into the new turn's :meth:`delta_ms` call. Idempotent — a
        second ``start_turn`` without an intervening
        :meth:`record_first_sentence` overwrites the pending timestamp
        (the previous turn was preempted or never yielded a sentence).
        """
        self._event_fired_at = self._time_fn() if now is None else now
        self._first_sentence_at = None

    def record_first_sentence(self, now: float | None = None) -> None:
        """Record the moment the first sentence was yielded to TTS.

        No-op when no ``start_turn`` is pending — defensive against
        callers that yield a sentence outside an event-firing flow.
        """
        if self._event_fired_at is None:
            return
        self._first_sentence_at = self._time_fn() if now is None else now

    def delta_ms(self) -> int | None:
        """Return the int ms delta (nearest int), or ``None`` if no first sentence yet.

        Use ``round`` rather than ``int`` to avoid float-precision truncation
        (``0.2s × 1000 == 199.9999...`` → ``int(...)`` yields 199 but ``round``
        yields 200). The schema's int contract is the surface; the meter
        smooths sub-ms float drift before serialization.
        """
        if self._event_fired_at is None or self._first_sentence_at is None:
            return None
        return round((self._first_sentence_at - self._event_fired_at) * 1000.0)

    def log_turn(self, recorder: Any, extra: dict[str, Any] | None = None) -> None:
        """Emit a ``llm_to_tts_delta_ms`` event when the delta is non-None.

        Skip path (no event written) when :meth:`delta_ms` returns None —
        the suppression/citation-strip path may end a turn without ever
        yielding a head, and emitting a null delta would pollute the
        per-turn metrics with garbage rows.
        """
        delta = self.delta_ms()
        if delta is None:
            return
        payload: dict[str, Any] = {"delta_ms": delta}
        if extra:
            payload.update(extra)
        recorder.log_event("llm_to_tts_delta_ms", **payload)
