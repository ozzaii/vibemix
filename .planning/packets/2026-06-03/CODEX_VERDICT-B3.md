# CODEX VERDICT - B3

Item: B3 - Grade-carrying IPC + lock-meter HUD
Code SHA: fd9a92ee

## User Value

A Pro Learn user on L2.01 now sees the live beatmatch grade the fused judge already
computes, while Sven keeps the rare spoken grade path deduped instead of stuttering.

## By-Ear / By-Eye Artifact

- Launched current source with `VIBEMIX_DEV_SIDECAR=1` and forced output routing to
  `Multi-Output Device`; boot confirmed:
  - `AI voice -> Multi-Output Device @ 24000Hz`
  - `djay passthrough -> Multi-Output Device @ 48000Hz`
  - `mascot bus on ws://127.0.0.1:8765`
- Started Learn `L2.01` after local proof-only Course 2 unlock seeding.
- Fired `ipc.learn.ack` for `tempo:B`; immediate bus reply included:
  `ipc.learn.live_grade` with
  `{"verdict":"tempo_off","phase_error_beats":-0.2576145124716547,"score":0.0,"citation":null}`.
- `ws_observe` saw repeated `ipc.learn.live_grade` ticks for the HUD, while
  `tail_ui_log` confirmed the frontend received the same frames.
- Session `20260603-141106` recorded one deduped authored tutor grade:
  `tempos are off - ease the pitch back.` with `tts_marker=L2.01.grade`.
- BPM guard held during speech: session snapshots reported `bpm:null` and pill frames
  stayed at `bpm:0` while voice/meter activity was present, so Sven audio did not fake
  a deck BPM count.

## Checks

- `npm --prefix tauri/ui run codegen:ipc`
- `uv run python scripts/check_ipc_schema.py`
- `uv run python .claude/skills/ipc-wiring-checker/scripts/check_ipc_wiring.py`
- `uv run pytest -q tests/ui_bus/test_learn_live_grade_message.py tests/ipc/test_learn_envelope_parity_p92.py tests/ui_bus/test_messages_schema.py tests/ui_bus/test_recordings_messages.py tests/ui_bus/test_mood_change_envelope.py tests/learn/test_runtime_evidence_grounding.py`
- `uv run ruff check scripts/check_ipc_schema.py src/vibemix/learn/runtime.py src/vibemix/ui_bus/__init__.py src/vibemix/ui_bus/learn_messages.py tests/ipc/test_learn_envelope_parity_p92.py tests/learn/test_runtime_evidence_grounding.py tests/ui_bus/test_learn_live_grade_message.py tests/ui_bus/test_messages_schema.py tests/ui_bus/test_mood_change_envelope.py tests/ui_bus/test_recordings_messages.py`
- `npm --prefix tauri/ui test -- tests/learn/live-meter.spec.ts tests/learn/test_ws_client_tauri_bridge.spec.ts tests/learn/test_practice_booth_shell.spec.ts`
- `npm --prefix tauri/ui run build`
- `npm --prefix tauri/ui test`
- `uv run pytest -q tests/learn/test_runtime_invariants.py tests/learn/test_no_new_ws_port.py tests/runtime/test_ws_bus.py tests/learn/test_no_speculative_phrase.py tests/prompts/test_negative_dict.py tests/state/test_hype_anti_slop.py tests/state/test_coach_anti_slop.py`
- `uv run pytest -q tests/state/test_evidence_registry.py tests/coach/test_citation_linter.py tests/coach/test_citation_zero_orphan_replay.py tests/agent/test_citation_strip_emit.py tests/agent/test_dj_cohost_grounding.py tests/agent/test_dj_cohost_linter.py`
- `git diff --check`

## Assumptions / Gaps

- The live proof used a local progress-file seed to unlock Course 2; the product
  progression contract was not changed.
- The live physical proof exercised a `tempo_off` grade, not a locked centered grade.
  The HUD wire, score clamping, citation propagation, and centered/phase rendering are
  unit-covered; a hands-on lock proof still needs a tuned deck interaction.
- Local app config had drifted to MacBook speakers before proof. It was corrected
  outside the repo to output device index `12` and reinforced with
  `VIBEMIX_OUTPUT_DEVICE='Multi-Output Device'`.
