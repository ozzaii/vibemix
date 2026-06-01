# CODEX_READY: Cohost/Viber Live Rehearsal Wrapper

Date: 2026-06-01
Author: Codex
Status: LAND packet, live rehearsal lifecycle slice
Package: Package 1F - Cohost/Viber Live Rehearsal Wrapper

## Decision

LAND this slice as `test(release): add cohost viber live rehearsal wrapper`.

This wrapper is the safe lifecycle harness around the cohost/Viber release
matrix. It can use an existing live socket or launch the current source sidecar,
wait for `ws://127.0.0.1:8765`, run the matrix, preserve artifacts, and stop
only the live process it started.

## Files

- `scripts/release/check_cohost_viber_live_rehearsal.sh`
- `tests/eval/test_check_cohost_viber_live_rehearsal_sh.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`
- `.planning/packets/2026-06-01/INDEX.md`
- `.planning/packets/2026-06-01/CODEX_READY-cohost-viber-live-rehearsal-wrapper.md`

## What Changed

- Added a start-or-use-live wrapper for cohost/Viber rehearsal.
- Can start the source sidecar, wait for the websocket, stimulate cohost/Viber
  activity, run the release matrix, and clean up only the process it started.
- Supports no-start smoke mode for coordination sessions where launching the app
  would disturb other agents.
- Emits actionable next steps for missing socket, matrix failures, FLX4 motion,
  and live proof gaps.

## Evidence

Syntax:

```text
bash -n scripts/release/check_cohost_viber_live_rehearsal.sh
```

Wrapper tests:

```text
uv run pytest -q tests/eval/test_check_cohost_viber_live_rehearsal_sh.py
21 passed in 27.35s
```

Lint:

```text
uv run ruff check tests/eval/test_check_cohost_viber_matrix_sh.py tests/eval/test_check_cohost_viber_live_rehearsal_sh.py
All checks passed!
```

No-start smoke on this machine:

```text
COHOST_VIBER_REHEARSAL_START_LIVE=never COHOST_VIBER_REHEARSAL_OUT_DIR=/tmp/vibemix-cohost-viber-live-rehearsal-codex bash scripts/release/check_cohost_viber_live_rehearsal.sh
FAIL check_cohost_viber_live_rehearsal: live socket missing and COHOST_VIBER_REHEARSAL_START_LIVE=never
```

The failure is expected for this safe path. `vibemix_dev.sidecar_status` also
reported `ws_reachable=false` for `ws://127.0.0.1:8765`.

## Boundaries

- No broad staging, no commit, and no product-release claim.
- This package does not run a real live rehearsal in the current turn. It proves
  the wrapper and safe no-start behavior.
- It does not change Viber, Sven, or set-generation runtime semantics.
- `/tmp` run outputs are scratch evidence; this packet and the checklist are the
  durable record.

## Next Required Proof

Run the wrapper for real when the rig is ready:

- DDJ-FLX4 connected.
- BlackHole/audio routing set.
- Current source sidecar running or permission to launch it.
- Then require FLX4 proof and inspect the produced matrix/rehearsal artifacts.
