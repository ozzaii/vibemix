# 51-01 SUMMARY — Kill ws_bus empty-{} frames + boot-smoke cleanliness gate

**Requirements:** BRINGUP-04, BRINGUP-01
**Status:** complete

## Root cause of the live `{}` frames

RESEARCH §1 hypotheses **H2/H3** confirmed; **H1 ruled out**.

- `Levels.snapshot()` (`src/vibemix/audio/levels.py:65`) **always** returns the
  3 meter keys `{"music","voice","mic"}` under its lock — it can never return
  `{}`. The flat mascot frame additionally carries 11 literal static keys, so
  it is structurally incapable of degrading to `{}`. (H1 ruled out.)
- Greps found **no app-level empty-dict emitter** anywhere: no
  `json.dumps({})`, no `send("{}")`, no keepalive/heartbeat path in
  `src/` or in `mascot.html` (which only ever sends `{action:'trigger'}`).
- Conclusion: the live `{}` in the `:8765` tap was the **tap mis-decoding
  websockets control frames** (ping/pong, opcode 0x9/0xA) as empty text —
  not a frame the app put on the wire. (H2/H3.)

## The emit-boundary guard (additive, no reshape)

`ws_broadcast` now builds the mascot payload into a local dict FIRST, then
gates the send: if the dict is falsy or missing any of `music`/`voice`/`mic`,
it logs `[ws] skipped malformed mascot frame ...` once to stderr and skips the
tick (sleeping `1/30` to preserve cadence) WITHOUT sending. It never reshapes
a valid frame — the key set, ordering, and 30Hz cadence are byte-identical.
The branch is normally **unreachable** (the source is already clean); it makes
the no-`{}` / meter-keys-present contract permanent against any future upstream
regression (a snapshot returning `{}`, a vanished state attr). The additive
`ipc.session.snapshot` block and its isolated try/except are untouched.

## Boot-smoke (BRINGUP-01)

`test_boot_smoke_reaches_phase_silent_cleanly` asserts a default (idle)
`MusicState` boots to a broadcasting state quickly: a mascot frame arrives
within a bounded `2.0s` window of the client connecting, and `phase` on every
mascot frame equals the **idle/silent default read from `MusicState().phase`**
(`'silent'`, not a hard-coded guess — with a sanity pin so a future default
change is loud). Zero empty frames over the window, via the shared helper.

## Test design note

The integration tests bind a **REAL** `ws_broadcast` server + connect a
**REAL** `websockets` client, but on an **ephemeral free port** (monkeypatching
`ws_bus.WS_PORT`), because the production port `8765` was held by a live
`cargo tauri dev` session during execution and would be racy in CI. This
exercises the real server bind on a real socket without colliding with a live
app and without touching production behavior.

## Verification (observed)

- `pytest -m integration tests/runtime/test_ws_bus_empty_frames.py -q` → **2 passed**
- `pytest tests/runtime/test_ws_bus.py tests/runtime/test_ws_bus_snapshot.py -q` → **17 passed** (cadence + shape + snapshot pins intact)
- `grep -c '"reaction_intent"' src/vibemix/runtime/ws_bus.py` → 1 (key set not reduced)

## Commits

- `75500f7` test(51-01): pin ws_bus never emits empty {} frames (integration) — includes the BRINGUP-01 boot-smoke (Task 1 + Task 3 in one file/commit).
- `480bfba` fix(51-01): guard ws_broadcast against empty/meter-less mascot frames + root-cause fix.

## Deviation

Tasks 1 and 3 landed in a single commit (`75500f7`) rather than two, because
the boot-smoke shares the same test file + the same `assert_no_empty_or_meterless`
helper as the empty-frame test (the plan explicitly says "extend it, do not
fork a new file"). Two atomic commits for plan 51-01 instead of three; all
three tasks' acceptance criteria are met.
