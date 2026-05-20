---
phase: 53
slug: controller-live-graceful-fallback
artifact: REVIEW
status: clean
reviewer: gsd-code-review (Opus 4.7)
date: 2026-05-21
diff_range: 53f871b..50d06ed
scope: src/ tests/ (4 source files, 8 test files)
---

# Phase 53 — Code Review

**Verdict: clean.** No HIGH/MEDIUM/LOW findings requiring code change. The diff is
genuinely additive and minimal (4 source files, +120 lines of production code, the
rest tests). The golden FLX4 decode path, `midi/controllers/` + `map_loader.py`,
and `midi/profiles/` are all byte-untouched.

## Files reviewed

| File | Change | Verdict |
|------|--------|---------|
| `src/vibemix/midi/state.py` | `mark_disconnected` clears moves+events rings | clean |
| `src/vibemix/platform/_midi_common.py` | NEW `handle_port_change_single_state` (option B) | clean |
| `src/vibemix/platform/_midi_macos.py` | default watcher callback → single-state | clean |
| `src/vibemix/__main__.py` | watcher spawned + cleaned up | clean |

---

## 1. `midi/state.py::mark_disconnected` — stale-move-leak fix

```python
def mark_disconnected(self) -> None:
    with self._lock:
        self._connected = False
        self._moves.clear()
        self._events.clear()
```

- **Under the lock:** YES — both `clear()` calls are inside `with self._lock:`,
  same lock that guards `handle_msg` mutations and `moves_since`/`events_since`
  reads. No torn read.
- **Off the decode hot path:** YES — `mark_disconnected` is only called by the
  watcher callback (`handle_port_change` / `handle_port_change_single_state`),
  never from `handle_msg`. The v4-byte-equivalent decode body is untouched
  (confirmed: `tests/midi/test_profile_flx4_golden.py` + `tests/test_midi_common.py`
  still pass, 15/15).
- **Consumers after disconnect:** SAFE.
  - `runtime/ws_bus.py:159` `controller_state.moves_since(...)` — wrapped in
    `try/except`, only emits when non-empty; cleared ring → `[]` → no MIDI ribbon
    entries (correct: don't surface gone-controller moves).
  - `state/refresh.py:463` `state.recent_moves = controller_state.moves_since(...)`
    — receives `[]`, no break.
  - `state/refresh.py:428` `deck_snapshot()` — NOT cleared by `mark_disconnected`
    (only the rings are). Deck/xfader values persist at last-known position with
    `connected: false`. **Intentional and matches the live recipe** (the bus shows
    `connected:false` as the disconnect signal; deck values reflect last state, but
    no *new moves* flow). Not a finding.

## 2. `_midi_common.py::handle_port_change_single_state` — option B (in-place mutate)

- **Rebuild path unchanged:** YES — `handle_port_change` (the rebuild-on-connect
  callback) is byte-untouched; the new function is appended below it. Both coexist;
  rebuild remains available for the future multi-controller path.
- **Consumers see updates without a stale object:** YES — this is the load-bearing
  difference. `__main__` passes `midi_macos.controller_state` ONCE to both
  `ws_broadcast` (`controller_state=`) and `state_refresh_loop` (positional). The
  single-state callback calls `mark_connected` / `mark_disconnected` on that SAME
  object (never reassigns `holder.controller_state`), so the captured references
  stay live across unplug/replug. Verified by `id()` identity assertions in
  `test_disconnect_reconnect.py` (original_id preserved through connect →
  disconnect → reconnect and a 7-event churn loop).
- **Callback vs decode-thread race:** SAFE. The callback runs on the asyncio event
  loop (watcher task); the decode runs on the daemon listener thread. Shared state
  is `ControllerState`, fully `threading.Lock`-guarded. On reconnect the callback
  does `listener_stop.set()` → `join(timeout=1.0)` → `spawn_listener(same_state)`.
  If the old thread outlives the 1s join, two threads could briefly call
  `handle_msg` on the same state — but every mutation is lock-protected, so no
  corruption (worst case: a couple of interleaved moves, harmless). The
  `bound_port` guard (`if holder.bound_port == port: return`) prevents redundant
  respawns. **Lock discipline holds.** Not a finding.
- **mido_module re-used:** the holder carries `mido_module=mido` and reuses it for
  the respawned listener — correct, no re-import churn.

## 3. `_midi_macos.py::start_port_watcher` — default callback switch

- The only behavioral change is `on_change = functools.partial(
  handle_port_change_single_state, holder)` (was `handle_port_change`). The
  ListenerHolder seeding (`controller_state=self.controller_state`), the watcher
  task creation, and the `on_change`-injection seam for tests are all unchanged.
- **Behavior parity:** the disconnect branch is identical between the two
  callbacks; only the connect branch differs (mark vs rebuild). For the
  single-FLX4 BRINGUP-03 target the profile is stable across replug, so
  `mark_connected` (no rebuild) is the correct choice and is explicitly documented
  as a carveout in the docstring. Tests can still inject any callback via
  `on_change`. Clean.

## 4. `__main__.py` — watcher wiring + lifecycle

- **Spawned under the loop:** YES — line 873-874 inside `async def main()`:
  `midi_watcher_stop = asyncio.Event()` + `midi_watcher_task =
  midi_macos.start_port_watcher(midi_watcher_stop)`. `start_port_watcher` does
  `asyncio.get_event_loop().create_task(port_watcher_task(...))` — runs on the
  live loop.
- **Shares the single controller_state:** YES — `start_port_watcher(on_change=None)`
  seeds the ListenerHolder from `self.controller_state`, which is the SAME object
  passed to `ws_broadcast` (line 884) and `state_refresh_loop` (line 894).
  Single-state ownership holds end-to-end.
- **Cleanly cancelled — no leaked task, no double-stop:** YES.
  - `finally` (line 943-946): `midi_stop.set()` (listener thread) then
    `midi_watcher_stop.set()` (watcher coop-exit within one poll).
  - `midi_watcher_task` added to `cleanup_tasks` (line 955) → `t.cancel()` +
    `await t` with `except (CancelledError, Exception): pass`.
  - **No double-stop bug:** setting the asyncio.Event then cancelling the task is
    safe — the watcher either exits on the event check or is cancelled mid-`_wait`;
    cancel is idempotent and the suppressed `await t` swallows CancelledError. The
    dedicated `midi_watcher_stop` is distinct from the listener's `threading.Event`
    `midi_stop`, so no signal cross-wiring.
- **Enumeration-skip robustness (poisoned mido lazy-rtmidi backend):** the watcher
  loop (`midi/watcher.py:77-82`, pre-existing, NOT modified this phase) wraps ONLY
  `get_input_names()` in `try/except Exception → log + skip-this-sweep → keep
  polling`. Because the try wraps only enumeration (callbacks have their own
  `_safe_invoke` guard), a poisoned/empty backend is *skipped*, not masked into the
  callback path; real callback errors still surface via `_safe_invoke`'s separate
  logger. The opt-in live recipe (`test_midi_macos_live.py:96-99`) mirrors this:
  `list_input_ports()` raising → `pytest.skip`, never fail. Correct: no-device /
  poisoned-backend → skip; it does NOT swallow logic errors. Clean.

---

## Tests — are they REAL?

Confirmed real, not shallow:

- **`test_disconnect_reconnect.py`** — drives the REAL production callback
  (`handle_port_change_single_state`) through connect→disconnect→reconnect + a
  7-event churn loop. Real FLX4 message bytes (`_cc(0,19,110)` = vol_a, `_cc(0,15,2)`
  = eq_low_a). Real `id()` identity assertions (original_id preserved across the
  whole cycle). Ring-clear asserted on disconnect, fresh-ring-then-decode-resumes
  asserted on reconnect. `spawn_listener` stubbed (no real port) — appropriate.
- **`test_watcher_callback_integration.py`** — REAL `port_watcher_task` + REAL
  single-state callback composed over a scripted device timeline `[FLX4]→[]→[FLX4]`,
  run under real `asyncio.run`. Injects a move post-connect, asserts it's cleared by
  the disconnect sweep's `mark_disconnected`. Asserts the exact transition sequence
  `[(connected,True),(disconnected,False),(connected,True)]` and clean completion.
- **`test_flx4_synthetic_decode.py`** — broad live-shaped stream across every
  control class (vol/eq/tempo/filter/xfader CCs + jog/play/cue/sync notes) with the
  EXACT ch/cc/note bytes from `profiles/pioneer_ddj_flx4.json`. Asserts per-deck
  values, move labels, typed-event kind/deck/field/magnitude, monotonic+unique
  event ids, deck-B-independent-from-A, unmapped-CC no-op, malformed-msg no-raise.
- **`test_generic_fallback.py`** — adds the BRINGUP-03 unknown-controller
  bind→decode→no-crash end-to-end flow (`find_mapping_or_generic("Some Random USB
  MIDI Thing")` → generic profile → positional generic_cc/generic_note events).
- **`test_live_binding_profiles_canonical.py`** — pins the dual-map resolution:
  source-level invariant that NO module under `src/vibemix` imports
  `map_loader`/`MidiMapLoader` except `map_loader.py` itself; live binding stays on
  `profiles/`. Strong regression guard.
- **`test_state.py`** (+1 test) — `test_mark_disconnected_clears_moves_and_events_rings`
  records real moves+events, asserts both rings non-empty pre-disconnect and `==[]`
  post-disconnect.
- **`test_main_midi_wiring.py`** — source-level guard (mirrors Phase 52's input-path
  assertion): asserts `start_port_watcher(` is spawned, on a dedicated
  `midi_watcher_stop = asyncio.Event()`, set in finally, and in `cleanup_tasks`.
  Also `ast.parse` no-syntax-error guard. Deliberately does NOT import heavy
  `main()` — appropriate (needs real audio devices).
- **`test_midi_macos_live.py`** — `macos_audio`-marked, darwin-only. Verified it
  SKIPS cleanly with no device (`SKIPPED ... no FLX4 connected`). Carries the full
  7-step Kaan-action live-drive recipe in the docstring.

**Targeted run:** 70 passed in 0.28s (all 8 Phase-53 MIDI/wiring test files +
`test_watcher.py`). `macos_audio` recipe: 1 skipped (clean). Golden + common:
15 passed.

---

## LOW notes (no action needed)

- `handle_port_change_single_state` shares ~90% of its body with
  `handle_port_change` (only connect-branch differs: mark vs rebuild). A future
  refactor could factor the common teardown, but duplication is intentional here —
  the two callbacks are documented as distinct strategies (single-FLX4 vs
  multi-controller) and keeping them separate avoids a shared-helper coupling that
  would make either harder to read. Not worth a change for Phase 53.
- After unplug, `deck_snapshot()` retains last-known deck/xfader values (only the
  moves/events rings clear). This is the documented/intended contract (the
  `connected:false` flag is the disconnect signal). Listed only so a future reader
  doesn't mistake it for a leak.
