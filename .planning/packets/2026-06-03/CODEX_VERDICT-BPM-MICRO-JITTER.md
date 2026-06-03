# CODEX VERDICT - BPM micro-jitter

Item: live BPM counter accepted same-title micro-jitter (`107.1 -> 109.1`).
SHA: `2ca3b6ac fix(runtime): tighten live bpm display jitter`

## User Value

A live user watching the session BPM readout now gets a steadier public counter
when the autocorr estimator hops between nearby same-title layers. Sub-1% drift
can still pass; larger same-title hops now hold the last-good value instead of
looking like a broken display.

## Root Cause

The prior BPM stabilizer intentionally allowed "small drift" immediately with a
2% tolerance. The live app showed the same recognized track moving from `107.1`
to `109.1`, which is about 1.87% and therefore passed the old tolerance. That
looked stuttery in the UI even though it was in-range estimator output.

## Change

- Tightened `_BPM_SWITCH_TOLERANCE` in `src/vibemix/state/refresh.py` from 2%
  to 1%.
- Added a regression in `tests/state/test_bpm_stabilize.py` pinning the live
  same-title `107.1 -> 109.1` case.

## By-Eye / Runtime Proof

Relaunched the source app with meeting-safe audio:

```sh
VIBEMIX_LOCAL_TTS=0 VIBEMIX_DEV_SIDECAR=1 \
VIBEMIX_OUTPUT_DEVICE='Multi-Output Device' \
cargo tauri dev --no-watch --no-dev-server-wait \
  --config '{"build":{"beforeDevCommand":null}}'
```

Observed `ipc.status.tick`: `voice:"muted"`.

Compact websocket sample over 12 seconds:

```json
{
  "snapshot_frames": 108,
  "non_null_bpms": [162.2],
  "null_frames": 0,
  "grounded_titles": {
    "Bladee, Thaiboy Digital, & Ecco2k - Victim": [162.2]
  }
}
```

The larger 20s raw sample also showed only `162.2` during grounded title frames;
brief `bpm:null` appeared only during an ungrounded idle dip.

## Checks

- `uv run pytest -q tests/state/test_bpm_stabilize.py tests/state/test_bpm_bus_grounding.py tests/runtime/test_ws_bus_snapshot.py tests/runtime/test_session_loop.py`
  passed: 57 tests.
- `uv run pytest -q tests/state/test_refresh.py tests/state/test_bpm_stabilize.py tests/state/test_bpm_bus_grounding.py tests/runtime/test_ws_bus_snapshot.py tests/runtime/test_session_loop.py tests/runtime/test_ws_bus_deck_state.py`
  passed: 146 tests.
- `uv run ruff check src/vibemix/state/refresh.py tests/state/test_bpm_stabilize.py`
  passed.
- `git diff --check -- src/vibemix/state/refresh.py tests/state/test_bpm_stabilize.py`
  passed.

## Notes

This is a display-stability fix, not a claim that the audio-only BPM estimator is
globally perfect. A bigger estimator upgrade still belongs to the beatgrid /
model-grade analysis lane.
