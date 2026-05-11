---
phase: 04-livekit-cascade-agent-pivot
plan: 03
type: summary
status: complete
completed_at: 2026-05-11
requirements_covered:
  - ARCH-03  # partial — runtime loops
wave_commit: 2b7ea9b
---

# Plan 04-03 — Runtime loops (coach event pump + diag meter + WS mascot bus) — Summary

## What Shipped

The asyncio runtime layer of Phase 4's cascade — three pure-asyncio loops
with no audio/sounddevice touchpoints, ready to be spawned as
`asyncio.create_task(...)` by `__main__.py` in Wave 4:

- `src/vibemix/runtime/coach.py` — `coach_loop` (~110 lines) verbatim port
  of `cohost_v4.py:1754-1852`. 2.0s warmup → 10Hz event polling. Single
  in-flight enforcement with 12s stale-clear. KAAN_SPOKE mic detection
  (3-frame active + 0.6s silence ladder, lock-protected
  `state.last_kaan_spoke_at` write). AI-talking guard +
  7s post-AI cooldown. Manual trigger fan-in. Timeout + exception
  handling that NEVER crashes the loop.
- `src/vibemix/runtime/diag.py` — `diag_loop` verbatim port of
  `cohost_v4.py:1859-1869`. 1Hz terminal meter with `\r` carriage-return
  overwrite. Format string preserved byte-for-byte.
- `src/vibemix/runtime/ws_bus.py` — `ws_broadcast` verbatim port of
  `cohost_v4.py:1872-1918` with the `_HAS_WS` feature flag DROPPED.
  Inbound `{"action": "trigger"}` JSON → sets `manual_trigger`. Outbound
  30Hz JSON broadcast (levels + audible/deck/phase). Dead client cleanup
  on `send` failure.
- `src/vibemix/runtime/__init__.py` — package surface exporting all three.
- `WS_HOST` (`"127.0.0.1"`) and `WS_PORT` (`8765`) added to
  `vibemix.audio.constants` (v4:123-124 verbatim) and re-exported via
  `vibemix.audio`. Centralized so Phase 12 Live UI reads from the same
  source of truth.

## Files

Created (8):
- `src/vibemix/runtime/__init__.py`
- `src/vibemix/runtime/coach.py`
- `src/vibemix/runtime/diag.py`
- `src/vibemix/runtime/ws_bus.py`
- `tests/runtime/__init__.py`
- `tests/runtime/conftest.py`
- `tests/runtime/test_coach.py`
- `tests/runtime/test_diag.py`
- `tests/runtime/test_ws_bus.py`

Modified (2):
- `src/vibemix/audio/constants.py` — added `WS_HOST` and `WS_PORT`
  (v4:123-124).
- `src/vibemix/audio/__init__.py` — re-export `WS_HOST` and `WS_PORT`.

## Tests Added

25 new tests under `tests/runtime/`:

- COACH-01..13 (13) — warmup, poll cadence, event fire path, in-flight
  guard, stale-clear at 12s, AI-talking blocks, 7s post-AI cooldown,
  KAAN_SPOKE full sequence (3 frames + 0.6s silence), KAAN_SPOKE
  short-press rejection (<3 frames), manual trigger fan-in,
  TimeoutError handling, exception handling, stop_event clean exit.
- CONST-WS-01 (1) — `WS_HOST`/`WS_PORT` exported from `vibemix.audio` and
  match values in `vibemix.audio.constants`.
- DIAG-01..03 (3) — coroutine function, format string substrings via
  capsys, 1.0s sleep cadence.
- WS-01..09 (9) — async function, server starts on `WS_HOST:WS_PORT`,
  inbound trigger sets `manual_trigger`, non-trigger and invalid JSON
  paths, broadcast payload shape (all 6 keys), 30Hz cadence, dead-client
  cleanup, AST-walked guarantee that `_HAS_WS` is not used in code (only
  docstrings, which is fine) and `websockets` is a direct top-level
  import.
- PKG-05 (1) — `from vibemix.runtime import coach_loop, diag_loop,
  ws_broadcast` resolves, `__all__` matches.

Full suite: **340 pass** (315 baseline + 25 new runtime tests). 0 lint
errors, 0 format diffs.

## Architectural Notes

- **`_HAS_WS` feature flag dropped.** `websockets` is now an explicit
  pyproject dep (Phase 2 declared it; Phase 1 already used it). On
  import failure the program fails loud with `ImportError`, not a silent
  degradation. WS-09 AST-walks the source to enforce: no `_HAS_WS`
  references in code (only in docstrings explaining the drop), no
  `try: import websockets` guard. Phase 2 PATTERNS §AntiPatterns-2.
- **TYPE_CHECKING for `DJCoHostAgent` import in coach.py.** Plan 04-03
  runs in parallel with 04-02 in the same wave — we don't want a hard
  runtime dep on 04-02. coach_loop only uses
  `agent.set_next_event(ev)` (interface-level), so a `TYPE_CHECKING`
  import keeps the runtime dep weak and lets tests pass `MagicMock`
  fakes without importing the real class.
- **`state._lock` write inside coach_loop's mic-detection branch.**
  Phase 3 invariant says `state_refresh_loop` is the only writer to
  `MusicState`; the v4:1800-1801 `with state._lock: state.last_kaan_spoke_at
  = now` is the sole locked exception. Port preserves this exactly so the
  lock acquire/release path is exercised in the COACH-08 test.
- **pytest-asyncio NOT a project dep.** Tests use `asyncio.run` inside
  sync test functions (same pattern as `tests/state/test_refresh.py`).
  `_REAL_SLEEP = asyncio.sleep` captured at module top so the fast-forward
  `fake_sleep` doesn't recurse into its own patch.
- **`WS_HOST` and `WS_PORT` centralized in `vibemix.audio.constants`.**
  Same place as the other v4 tuning constants — Phase 12 Live Session
  UI will read them too.

## Deviations

None. Verbatim port. The one structural change (`_HAS_WS` flag drop)
was specified in the plan's must-have truths and is the explicit Phase 2
PATTERNS anti-pattern fix.

## Carry-Forward

- 04-04: `__main__.py` consumes all three loops via
  `asyncio.create_task(...)`. Cleanup must cancel + await each task with
  `CancelledError` catch in the `finally:` block.
- 04-04: AudioMacOS as audio I/O firewall (replaces v4's free-functions).
- 04-04: AgentSession + PlaybackQueueAudioOutput wiring (must assign
  `session.output.audio` BEFORE `await session.start(agent)`).
- 04-05: 12-gate verification + Phase 4 SUMMARY + STATE/ROADMAP advance.
- Phase 12 Live Session UI: WS bus payload shape pinned by WS-06 test
  (`{music, voice, mic, audible, deck, phase}`).
