# CODEX VERDICT - Q8 Voice-Muted Banner

Item: Q8 - show local voice muted/model-missing status in the running app
SHA: 85e3c6d6

## User Value

A Free/Pro user on the live shell now sees when Sven's local MOSS voice is muted for this boot instead of reading a false "voice ready" footer while no speech can play.

## By-Eye / By-Wire Proof

- Launched current source with `VIBEMIX_LOCAL_TTS=0 VIBEMIX_DEV_SIDECAR=1 VIBEMIX_OUTPUT_DEVICE='Multi-Output Device' cargo tauri dev --no-watch --no-dev-server-wait --config '{"build":{"beforeDevCommand":null}}'`.
- Found and killed a stale bundled `/Applications/vibemix.app` sidecar that still owned `127.0.0.1:8765`; after that, `lsof -nP -iTCP:8765 -sTCP:LISTEN` showed current-source `.venv/bin/python3 -m vibemix` owning the socket.
- `ws_observe(seconds=4, type_filter="ipc.status.tick")` saw `payload.voice == "muted"` on live status ticks.
- `ui.log` showed `ipc.status.tick` frames with `"voice":"muted"` and session snapshots with `meters.voice.peak == 0`.
- Window screenshot: `/tmp/vibemix-q8-voice-muted-final.png` shows the visible shell footer reading `voice muted`.

## Checks

- `uv run pytest -q tests/ui_bus/test_status_tick.py tests/runtime/test_ws_bus_status_tick.py tests/wizard/test_wizard_loop_ipc.py::test_status_tick_payload_is_schema_valid` - 27 passed.
- `npm --prefix tauri/ui test -- tests/shell/voice-readiness-badge.spec.ts src/ipc/validator.spec.ts tests/session/components.spec.ts tests/session/state.spec.ts tests/session/render-loop.spec.ts` - 131 passed.
- `npm --prefix tauri/ui test -- tests/shell/voice-readiness-badge.spec.ts tests/session/components.spec.ts` - 56 passed after cleanup.
- `npm --prefix tauri/ui run build` - passed.
- `uv run python scripts/check_ipc_schema.py` - passed, 73 dataclasses / 73 oneOf entries.
- `uv run python .claude/skills/ipc-wiring-checker/scripts/check_ipc_wiring.py` - passed.
- `git diff --check` - passed.

## Notes

The first live probe read stale packaged-app ticks with no `voice` field because the bundled sidecar owned the single websocket. That duplicate process is a credible source of the stutter the user heard; current-source proof only became valid after clearing the stale socket owner.
