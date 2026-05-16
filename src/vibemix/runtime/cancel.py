# SPDX-License-Identifier: Apache-2.0
"""CancelGate — single chokepoint for programmatic SpeechHandle.interrupt.

Plan 19-01 ships the wrapper + caps as one atomic unit so Pitfall 1
(cancel-budget blowout) closes in one shot. Every cancel-and-refire in
src/vibemix/ flows through ``CancelGate.try_cancel`` — Plan 19-04 (ack
throttle) and the coach loop refactor (Plan 19 followup) only ever call
this method; the forced-interrupt call lives nowhere else.

Three gates apply in order, short-circuit on first deny:

  1. **Priority** — incoming.priority MUST be strictly > in_flight.priority.
     Equal priorities do not preempt (DROP can't override another DROP).
  2. **Cooldown** — at most one cancel per ``CANCEL_COOLDOWN_S`` (8.0s).
     The CONTEXT D-04 lock — no per-instance override.
  3. **Soft cap** — at most ``CANCEL_SOFT_CAP`` (30) cancels per session.
     The 31st attempt sets ``_disabled = True``, fires the telemetry
     callback exactly once, and stays disabled for the rest of the session.

Time source is injected so tests drive the clock deterministically; the
default is ``time.monotonic`` which is immune to wall-clock jumps.

The LiveKit ``SpeechHandle`` import is intentionally NOT at module top —
this matches the lazy-typing pattern from runtime/coach.py:30-33 so the
gate can be unit-tested without LiveKit installed.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Callable

from vibemix.state.event import Event

if TYPE_CHECKING:
    from livekit.agents import SpeechHandle


# CONTEXT D-04 lock — these are the only allowed values. Do NOT add a
# constructor knob to override them; subscriber tests in Plan 19-05's burst
# harness assume these exact constants.
CANCEL_COOLDOWN_S = 8.0
CANCEL_SOFT_CAP = 30


class CancelGate:
    """The single chokepoint that decides whether a speech-in-flight gets
    interrupted by an incoming higher-priority Event.

    Thread-safety: NOT thread-safe. The coach loop is single-threaded
    asyncio; every call to ``try_cancel`` happens on the event loop. If a
    future caller wants to invoke this from a sounddevice callback, wrap
    it via ``loop.call_soon_threadsafe`` — do not add a lock here, the
    asyncio invariant is the simpler contract.
    """

    def __init__(
        self,
        time_fn: Callable[[], float] = time.monotonic,
        telemetry_cb: Callable[[dict], None] | None = None,
    ) -> None:
        self._time = time_fn
        self._telemetry_cb = telemetry_cb
        self.cancel_count: int = 0
        self.last_cancel_at: float = 0.0
        self._disabled: bool = False

    @property
    def disabled(self) -> bool:
        return self._disabled

    def try_cancel(
        self,
        handle: SpeechHandle,
        incoming: Event,
        in_flight: Event,
        *,
        reason_out: list[str] | None = None,
    ) -> bool:
        """Attempt a cancel-and-refire. Returns True iff the cancel fired.

        On a False return, ``reason_out`` (if provided) gets a one-word tag
        appended: ``"priority"`` / ``"cooldown"`` / ``"soft_cap_breach"`` /
        ``"disabled"``. Plan 19-04's per-cancel telemetry surface reads
        these to attribute drops.
        """
        # Gate 0: already disabled by a prior soft-cap breach.
        if self._disabled:
            if reason_out is not None:
                reason_out.append("disabled")
            return False

        # Gate 1: priority ladder. Strict greater-than — equal does NOT
        # preempt (a DROP cannot override another DROP).
        if incoming.priority <= in_flight.priority:
            if reason_out is not None:
                reason_out.append("priority")
            return False

        # Gate 2: hard cooldown. ``last_cancel_at == 0.0`` on first call
        # passes through trivially (now - 0 >> 8.0).
        now = self._time()
        if now - self.last_cancel_at < CANCEL_COOLDOWN_S:
            if reason_out is not None:
                reason_out.append("cooldown")
            return False

        # Gate 3: soft cap. The CHECK runs BEFORE the cancel — once
        # ``cancel_count`` has reached the cap, the next attempt trips the
        # auto-disable + telemetry, and the cancel itself does NOT fire.
        if self.cancel_count >= CANCEL_SOFT_CAP:
            self._disabled = True
            if self._telemetry_cb is not None:
                self._telemetry_cb(
                    {"event": "cancel_soft_cap_breach", "count": self.cancel_count}
                )
            if reason_out is not None:
                reason_out.append("soft_cap_breach")
            return False

        # All gates clear → fire the cancel. ``force=True`` bypasses the
        # LiveKit ``allow_interruptions=False`` flag set on the original
        # generate_reply call (see runtime/coach.py:136).
        handle.interrupt(force=True)
        self.cancel_count += 1
        self.last_cancel_at = now
        return True
