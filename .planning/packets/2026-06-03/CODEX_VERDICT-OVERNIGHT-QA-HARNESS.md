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

## Increment 2 — detector-mode replay + keyless findings JSON

- Item: `CODEX_READY-OVERNIGHT-QA-HARNESS.md` step 2/4 partial (`replay_harness` detector lane + layer-A/C findings surface).
- SHA: `62b6162b` (`feat(eval): add overnight replay findings`).
- User value: the overnight runner can now opt into honest detector predictions and receive one structured findings JSON that names detector silence / mute / slop / late flags for the auto-fix loop.
- By-eye artifact:
  - Ran `uv run python -m scripts.eval.replay_harness --corpus tests/eval/fixtures --judges noop --output /tmp/vibemix-overnight-harness.Xsx9Bd/out --use-detector-predictions --findings-json /tmp/vibemix-overnight-harness.Xsx9Bd/findings.json`.
  - Command exited `1` intentionally: `FAIL synthetic_session: ['f1=0.00 < 0.80']`.
  - `findings.json` was still written with schema `vibemix_overnight_qa_findings_v1`, `verdict: fail`, and scenario flags `["no_detector_events", "mute"]`.
  - The checklist recorded `events: 3`, `llm_invokes: 0`, `ground_truth_events: 3`, `detector_events: 0`, `prediction_source: detector`, plus the evidence pointer to `tests/eval/fixtures/synthetic_session/events.jsonl`.
  - This is the desired anti-greenwash behavior: the 440Hz synthetic fixture is not a DJ transition, so detector mode does not fake `predicted_events` from ground truth.
- Safety notes:
  - No sounddevice, Tauri, LiveKit, MOSS, or websocket server is opened by detector-mode replay.
  - Existing scorecard behavior remains default-off; legacy noop runs still use ground-truth predictions unless `--use-detector-predictions` is passed.
  - Respan/Sven blind quality judge is not wired in this increment; `quality` is honest `null`.
- Checks:
  - `uv run pytest -q tests/eval/test_replay_harness.py tests/eval/test_replay_harness_cooldowns.py tests/eval/test_replay_harness_phase_41.py` -> `39 passed`.
  - `uv run ruff check scripts/eval/replay_harness.py tests/eval/test_replay_harness.py` -> pass.
  - `git diff --check` -> pass.
- Remaining packet work:
  - The env-gated live `VIBEMIX_REPLAY_SESSION` capture-source substitute is not implemented yet.
  - Parallel scenario launcher and Respan quality layer remain to be wired on top of the now-available port fan-out + findings JSON.
