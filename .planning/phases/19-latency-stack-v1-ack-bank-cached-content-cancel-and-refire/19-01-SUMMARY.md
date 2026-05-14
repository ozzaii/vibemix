---
phase: 19-latency-stack-v1-ack-bank-cached-content-cancel-and-refire
plan: 01
subsystem: runtime
tags: [cancel-and-refire, livekit, speech-handle, priority, telemetry, event]

# Dependency graph
requires:
  - phase: 04-event-detection
    provides: Event dataclass + EventDetector._fire call sites
  - phase: 17-state-detectors
    provides: DROP slot reservation (priority pre-wired here, emitter lands later)
provides:
  - Event.priority int field with EVENT_PRIORITY default ladder (8 known types)
  - CancelGate single chokepoint with 8s hard cooldown + 30/session soft cap
  - Telemetry callback fires exactly once on soft-cap auto-disable
  - Module constants CANCEL_COOLDOWN_S / CANCEL_SOFT_CAP for downstream readers
affects:
  - 19-02 (prompt diet — independent, no coupling)
  - 19-03 (context caching — will subscribe to telemetry on cancel for cache invalidate)
  - 19-04 (ack bank — will route every cancel through CancelGate.try_cancel)
  - 19-05 (burst harness — reads cancel_count + telemetry payload)
  - coach loop refactor (replaces direct generate_reply with CancelGate-mediated path)

# Tech tracking
tech-stack:
  added: []  # stdlib + existing livekit dep only
  patterns:
    - "Single-chokepoint contract: handle.interrupt(force=True) lives in exactly one src/vibemix/ file"
    - "Injected time_fn for deterministic cooldown tests (no monkeypatch on time.monotonic)"
    - "Lazy LiveKit typing via TYPE_CHECKING — unit-testable without livekit install"
    - "Optional telemetry_cb sink — caller wires to IPC bus, gate stays decoupled"

key-files:
  created:
    - src/vibemix/runtime/cancel.py
    - tests/runtime/test_cancel.py
    - tests/state/test_event_priority.py
  modified:
    - src/vibemix/state/event.py

key-decisions:
  - "Strict-greater priority gate (incoming > in_flight) — equal does NOT preempt (DROP can't override another DROP)"
  - "Soft-cap CHECK runs BEFORE the cancel — the 31st attempt trips auto-disable + telemetry but does NOT execute the interrupt"
  - "Priority field positioned LAST on Event dataclass — preserves existing positional callers in EventDetector._fire (Event(type, state, extra=...))"
  - "DROP slot pre-wired at priority=10 ahead of Phase 17 — ladder is stable for Plans 19-02..19-04 to read against"
  - "time_fn defaults to time.monotonic (not time.time) — immune to wall-clock jumps that could spuriously clear or extend the 8s cooldown"

patterns-established:
  - "Cancel-and-refire chokepoint: Plans 19-03/19-04 and the coach loop refactor MUST call CancelGate.try_cancel — no second SpeechHandle.interrupt path is permitted in src/vibemix/"
  - "Priority ladder is the deterministic int comparison consumed at the gate — no enum, no string ranking elsewhere"

requirements-completed: [LATENCY-10, LATENCY-11, LATENCY-12, LATENCY-13]

# Metrics
duration: ~12min
completed: 2026-05-14
---

# Phase 19 Plan 01: Cancel-and-refire chokepoint shipped

**Single-instrumented `CancelGate` wrapping `SpeechHandle.interrupt(force=True)` with 8s hard cooldown + 30/session soft-cap auto-disable + telemetry, plus the `Event.priority` ladder (MANUAL=DROP=10 down to HEARTBEAT=1) that gates it.**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-05-14
- **Completed:** 2026-05-14
- **Tasks:** 2 (both TDD: RED→GREEN)
- **Files created:** 3
- **Files modified:** 1
- **Tests added:** 22 (12 priority + 10 cancel-gate)

## Accomplishments

- `Event.priority: int` with `EVENT_PRIORITY` map — 8 known types covered + reserved DROP slot pre-wired (priority 10) per CONTEXT D-04 ahead of Phase 17.
- `CancelGate` class as the **sole** call site for `handle.interrupt(force=True)` in `src/vibemix/` — verified by grep (`grep -rE "interrupt\(force=True\)" src/vibemix/` returns exactly one line).
- 3-gate decision flow: priority (strict greater-than) → 8s hard cooldown → 30/session soft cap with auto-disable + one-shot telemetry.
- Module constants `CANCEL_COOLDOWN_S = 8.0` / `CANCEL_SOFT_CAP = 30` exported (Plan 19-05's burst harness reads them; D-04 lock — no per-instance override knob).
- Telemetry callback decoupled — gate doesn't import an IPC bus; the optional `telemetry_cb: Callable[[dict], None]` is wired by the caller (Plan 19-04 hooks into the cancel signal here).

## Task Commits

1. **Task 1 RED:** failing tests for `Event.priority` + `EVENT_PRIORITY` — `5037459` (test)
2. **Task 1 GREEN:** add `priority` field + `EVENT_PRIORITY` map to Event — `5f63a2a` (feat)
3. **Task 2 RED:** failing tests for `CancelGate` chokepoint — `120ab79` (test)
4. **Task 2 GREEN:** `CancelGate` chokepoint with cooldown + soft-cap + telemetry — `ce456dc` (feat)

**TDD gate compliance:** Both tasks followed RED → GREEN. No REFACTOR commits needed — implementation landed clean on first GREEN.

## Files Created/Modified

- `src/vibemix/state/event.py` *(modified)* — added `EVENT_PRIORITY` dict + `priority: int = 0` field on Event + `__post_init__` that backfills from the map when priority is unset. Field positioned LAST so existing positional callers in `EventDetector._fire` (Event(type, state, extra=...)) keep working.
- `src/vibemix/runtime/cancel.py` *(created, 127 lines)* — `CancelGate` class + module constants. LiveKit `SpeechHandle` typed via `TYPE_CHECKING` — gate is unit-testable without livekit installed.
- `tests/state/test_event_priority.py` *(created, 12 tests)* — covers all 8 known priorities + unknown=0 + explicit-override-wins + isinstance(int) + EVENT_PRIORITY shape.
- `tests/runtime/test_cancel.py` *(created, 10 tests)* — covers all 3 gates, the 4-cancel-in-2s burst, the 31-cancel breach scenario, telemetry-fires-exactly-once, state accessors, and the chokepoint contract (only `interrupt(force=True)` is touched on the handle).

## CancelGate Public API

```python
from vibemix.runtime.cancel import (
    CancelGate,
    CANCEL_COOLDOWN_S,   # 8.0
    CANCEL_SOFT_CAP,     # 30
)

gate = CancelGate(
    time_fn=time.monotonic,                      # injectable for tests
    telemetry_cb=lambda payload: ipc.emit(payload),  # optional; one-shot on breach
)

# Sole entry point — every programmatic interrupt goes through here.
fired: bool = gate.try_cancel(
    handle,            # livekit.agents.SpeechHandle
    incoming,          # vibemix.state.event.Event (the new arrival)
    in_flight,         # vibemix.state.event.Event (currently speaking)
    *,
    reason_out=None,   # optional list[str]; appended with one of:
                       # "priority" | "cooldown" | "soft_cap_breach" | "disabled"
)

# State accessors:
gate.cancel_count    # int — cumulative successful cancels this session
gate.disabled        # bool — True after soft-cap breach, sticky
gate.last_cancel_at  # float — last successful time_fn() reading
```

### Priority ladder semantics

Strict greater-than. `EVENT_PRIORITY` defines:

| Type            | Priority | Notes                                                       |
| --------------- | -------- | ----------------------------------------------------------- |
| `MANUAL`        | 10       | User-issued ceiling                                         |
| `DROP`          | 10       | Reserved per Phase 17 — emitter lands later, slot is wired  |
| `KAAN_SPOKE`    | 9        | Kaan's voice always wins over passive music events          |
| `TRACK_CHANGE`  | 7        | Strong musical signal                                       |
| `PHASE`         | 6        |                                                             |
| `MIX_MOVE`      | 5        |                                                             |
| `LAYER_ARRIVAL` | 4        |                                                             |
| `HEARTBEAT`     | 1        | Lowest non-zero — never preempts anything else              |
| _(unknown)_     | 0        | Lowest possible — never preempts                            |

Equal priorities do NOT preempt (a DROP cannot override another DROP). An incoming `MANUAL` while another `MANUAL` is in flight will be denied with `reason="priority"`.

### Cap enforcement and auto-disable

- Hard cooldown: 8.0s wall-time (via `time_fn`) between any two successful cancels. The CONTEXT D-04 lock — no per-instance override.
- Soft cap: 30 cancels per session. The 31st attempt that would otherwise pass the priority + cooldown gates instead trips `_disabled = True`, fires the telemetry callback exactly once with `{"event": "cancel_soft_cap_breach", "count": 30}`, and returns False with `reason="soft_cap_breach"`. All subsequent attempts return False with `reason="disabled"` — telemetry does NOT re-fire.
- Auto-disable is sticky for the lifetime of the `CancelGate` instance — there is no `reset()` method (intentional per T-19-02 mitigation). A new session creates a new gate.

### What this does NOT do (preserved for downstream plans)

- **No cache invalidate hook** — Plan 19-03 will subscribe to the cancel signal (likely by extending `telemetry_cb` payload to include per-cancel events, or by adding a separate `on_cancel` callback). Not pre-wired here.
- **No ack throttle hook** — Plan 19-04 will route every ack through `CancelGate.try_cancel` and decide ack-bank playback based on the return value. Not pre-wired here.
- **No coach loop integration** — `runtime/coach.py` line 136 still calls `session.generate_reply(allow_interruptions=False)` directly. The refactor that routes the in-flight handle through `CancelGate` lives in a follow-up plan; this plan is the foundation only.

## Decisions Made

- **Strict greater-than priority** rather than `>=` — equal priorities should not stutter the speech bus. A back-to-back DROP scenario is musically unrealistic and the second DROP would be wasted output anyway.
- **Soft-cap check before the cancel fires** — the 31st attempt does NOT interrupt the in-flight speech. Felt right: by the time we've burned 30 cancels in a session, the gate is already telling us the system is misbehaving; firing one more cancel as part of the auto-disable would be the exact behavior we're trying to suppress.
- **Constants without type annotations** (`CANCEL_COOLDOWN_S = 8.0`, not `CANCEL_COOLDOWN_S: float = 8.0`) — the plan's `done` clause requires `grep -c "CANCEL_COOLDOWN_S = 8.0"` to return 1; honoring the literal grep contract preserves the audit trail Plan 19-05 will use.
- **`time.monotonic` default, not `time.time`** — wall-clock jumps (NTP correction, manual user adjustment) shouldn't spuriously clear or extend the 8s cooldown. This is a small but real correctness improvement over the v4 POC's `time.time()` pattern.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## Verification

- `pytest tests/state/test_event_priority.py tests/runtime/test_cancel.py -x` — 22/22 passed.
- `pytest tests/state/ tests/runtime/ -x` — 532 passed, 1 skipped, no regressions.
- `pytest -q --ignore=tests/dist` (full suite) — **1641 passed** / 9 pre-existing failures / 7 skipped. Baseline was 1619 passed / 9 failed → +22 new passes, zero new failures.
- `grep -rE "interrupt\(force=True\)" src/vibemix/` → exactly 1 line (the chokepoint).
- `grep -c "CANCEL_COOLDOWN_S = 8.0" src/vibemix/runtime/cancel.py` → 1.

## Self-Check: PASSED

- src/vibemix/state/event.py — FOUND
- src/vibemix/runtime/cancel.py — FOUND
- tests/state/test_event_priority.py — FOUND
- tests/runtime/test_cancel.py — FOUND
- Commit 5037459 (test 19-01) — FOUND
- Commit 5f63a2a (feat 19-01 priority) — FOUND
- Commit 120ab79 (test 19-01 cancel) — FOUND
- Commit ce456dc (feat 19-01 cancelgate) — FOUND

## Next Phase Readiness

- **Plan 19-02 (prompt diet):** Independent — no shared surface with this plan, can proceed in parallel.
- **Plan 19-03 (Gemini context caching):** When implementing cache invalidate, hook via `CancelGate.telemetry_cb` payload extension OR add a per-cancel `on_cancel` Callable to `__init__`. Do NOT add a second `interrupt(force=True)` path — route through `try_cancel`.
- **Plan 19-04 (ack bank):** Every ack-driven cancel must call `CancelGate.try_cancel(handle, ack_event, in_flight_event)` and gate the ack-audio playback on the return value. The 8s cooldown means an ack burst on rapid mic activity will only fire one cancel per ~8s window — exactly the throttle behavior the ack bank wants.
- **Coach loop refactor (followup):** `runtime/coach.py:136` still calls `session.generate_reply(allow_interruptions=False)` directly. The refactor needs to (a) hold the returned `SpeechHandle` in shared state, (b) inject a `CancelGate` instance into the loop, (c) on every detected event compare its priority to the current in-flight event and call `gate.try_cancel(handle, ev, in_flight)`. Not in scope for this plan.
- **Plan 19-05 (burst harness):** Can read `gate.cancel_count`, `gate.disabled`, and the `telemetry_cb` payload directly to assert the 4-in-2s and 31-cancel scenarios end-to-end.

---
*Phase: 19-latency-stack-v1-ack-bank-cached-content-cancel-and-refire*
*Completed: 2026-05-14*
