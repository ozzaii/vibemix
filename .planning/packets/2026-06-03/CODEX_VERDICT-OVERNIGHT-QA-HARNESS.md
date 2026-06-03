# CODEX VERDICT — OVERNIGHT-QA-HARNESS

## Increment 1 — per-instance websocket ports

- Item: `CODEX_READY-OVERNIGHT-QA-HARNESS.md` step 1 (`VIBEMIX_WS_PORT` / `VIBEMIX_DEBRIEF_PORT` prerequisite).
- SHA: `1aa56cf4` (`feat(runtime): add per-instance websocket ports`).
- User value: an overnight QA runner can now launch multiple headless source engines in parallel without every instance colliding on `8765/8766`.
- By-eye artifact:
  - Launched source engine with `HOME=/tmp/vibemix-qa-home.ztUOZS VIBEMIX_DEV_SIDECAR=1 VIBEMIX_LOCAL_TTS=0 VIBEMIX_OUTPUT_DEVICE='Multi-Output Device' VIBEMIX_WS_PORT=18765 VIBEMIX_DEBRIEF_PORT=18766 uv run python -m vibemix`.
  - Runtime printed `-> mascot bus on ws://127.0.0.1:18765`.
  - `lsof -nP -iTCP:18765 -sTCP:LISTEN` showed `python3.1 ... TCP 127.0.0.1:18765 (LISTEN)`.
  - `lsof -nP -iTCP:8765 -sTCP:LISTEN` returned no listener, proving the default app port stayed free for this instance.
  - `uv run python .claude/skills/drive-vibemix/scripts/ws_probe.py --uri ws://127.0.0.1:18765 --watch ipc.session.snapshot --seconds 2` connected and observed 28 `ipc.session.snapshot` frames.
  - SIGINT shutdown printed `-> stopping...` / `-> bye`; follow-up `lsof` found no listener on `18765` or `18766`.
- Safety notes:
  - Voice was muted for the meeting-safe run (`VIBEMIX_LOCAL_TTS=0`); output target was `Multi-Output Device`.
  - Defaults remain `8765/8766`; invalid env values fall back to defaults.
  - No grounding review required: this increment changes socket configuration and diagnostics only, not what Sven says or when he speaks.
- Checks:
  - `uv run pytest -q tests/runtime/test_runtime_port_env.py tests/test_main_debrief_flag.py tests/runtime/test_ws_bus.py::test_ws_02_server_starts_on_ws_host_port tests/runtime/test_coach.py::test_const_ws_01_ws_host_and_port_in_vibemix_audio tests/runtime/test_drive_vibemix_ws_probe.py` -> `22 passed`.
  - `uv run ruff check src/vibemix/audio/constants.py src/vibemix/__main__.py src/vibemix/runtime/wizard.py src/vibemix/runtime/session_loop.py tests/runtime/test_runtime_port_env.py` -> pass.
  - `git diff --check` -> pass.
- Packet assumptions corrected:
  - `.claude/skills/drive-vibemix/scripts/ws_probe.py` already had `--uri`; no edit needed there.
