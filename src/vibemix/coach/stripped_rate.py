# SPDX-License-Identifier: Apache-2.0
"""StrippedRateTracker — Phase 20 telemetry guard against linter-induced silence.

Closes Pitfall 2 (silence-streak DoS) + threat T-20-01-02. The linter alone
would mute the cohost for 30+ seconds during early Gemini grammar drift
("0% citations" cold-start). This tracker watches the rolling rate of
stripped decisions and, when the rate breaches a threshold, fires a
**one-shot bypass** that lets the next response emit verbatim with an
``[unverified]`` audit row — a visible, audit-trailed failure mode that's
strictly preferable to silent dead-air.

The one-shot semantics are LOAD-BEARING. Without them, every response in a
sustained breach window would emit ``[unverified]`` and the strip mechanism
would be functionally disabled (the linter would have no teeth). The bypass
re-arms only after the rate falls back to ``<= threshold`` — so the first
bad-grammar streak triggers exactly one bypass, the next clean run re-arms,
and a new breach can fire again.

Concurrency: NOT thread-safe. The coach loop is single-threaded asyncio;
every ``record`` / ``rate`` / ``should_bypass`` call happens on the event
loop.
"""

from __future__ import annotations

import time
from collections import deque
from collections.abc import Callable

from vibemix.coach.constants import STRIPPED_RATE_THRESHOLD, STRIPPED_RATE_WINDOW_S


class StrippedRateTracker:
    """Rolling-window stripped-rate telemetry + one-shot bypass.

    Args:
        window_s: Rolling-window duration in seconds (default 15.0).
        threshold: Rate above which ``should_bypass`` may fire (default 0.4).
        time_fn: Clock function returning a monotonic float. Injected for
            deterministic unit testing — never call ``time.monotonic()``
            inline because it would defeat the test contract.

    Internal state:
        ``_entries`` — deque of ``(t, stripped_bool)`` tuples. Eviction runs
        on every ``record()`` call so ``rate()`` is O(window-size), not
        O(history-size).
        ``_bypass_consumed`` — one-shot latch. ``True`` after a bypass
        fires; reset to ``False`` on the next ``record()`` where rate
        falls back to ``<= threshold``.
    """

    def __init__(
        self,
        *,
        window_s: float = STRIPPED_RATE_WINDOW_S,
        threshold: float = STRIPPED_RATE_THRESHOLD,
        time_fn: Callable[[], float] = time.monotonic,
    ) -> None:
        self._window_s = window_s
        self._threshold = threshold
        self._time_fn = time_fn
        # Deque > list: eviction is O(1) amortized at the head.
        self._entries: deque[tuple[float, bool]] = deque()
        # One-shot bypass latch — flipped True when bypass fires; flipped
        # False when rate recovers below threshold on a subsequent record.
        self._bypass_consumed: bool = False

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def record(self, stripped: bool) -> None:
        """Append one decision to the rolling window + evict stale entries.

        Also re-arms the one-shot bypass when the post-eviction rate falls
        back to ``<= threshold`` — this is the recovery path.
        """
        now = self._time_fn()
        self._entries.append((now, stripped))
        self._evict(now)

        # Recovery: re-arm the one-shot if the rate has fallen back below
        # threshold. Without this branch the bypass would fire only once
        # per process lifetime — see test_bypass_rearms_after_recovery.
        if self._bypass_consumed and self._rate_unlocked() <= self._threshold:
            self._bypass_consumed = False

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    def rate(self) -> float:
        """Return the stripped fraction over the current window.

        Empty buffer (no records yet) returns 0.0 — never NaN, never None.
        Callers don't have to special-case the cold-start state.
        """
        # Eviction runs on record(); reads do not mutate. The window
        # boundary may drift a tick stale between records — acceptable
        # because should_bypass is the only consumer and it always runs
        # after a record (the agent records THEN polls).
        return self._rate_unlocked()

    def should_bypass(self) -> bool:
        """One-shot bypass decision.

        Returns ``True`` exactly once when ``rate() > threshold`` AND the
        previous bypass has been consumed. The latch flips on the firing
        call; subsequent calls return ``False`` until ``record()`` re-arms
        it (see the recovery branch in ``record``).
        """
        if self._bypass_consumed:
            return False
        if self._rate_unlocked() > self._threshold:
            self._bypass_consumed = True
            return True
        return False

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _evict(self, now: float) -> None:
        """Drop entries older than ``window_s``."""
        cutoff = now - self._window_s
        # popleft is O(1); iterate until the head is inside the window.
        while self._entries and self._entries[0][0] < cutoff:
            self._entries.popleft()

    def _rate_unlocked(self) -> float:
        """Raw rate calculation — no eviction (caller is responsible)."""
        if not self._entries:
            return 0.0
        stripped_count = sum(1 for _t, s in self._entries if s)
        return stripped_count / len(self._entries)
