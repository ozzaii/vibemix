# Sven inline audio cap proof — 2026-06-04

Problem:
- The live by-bus probe in `sven-live-by-bus-20260604-160156` showed the co-host could launch the bus and select local MOSS TTS, but the first manual Sven turn failed before response generation.
- Authoritative live artifact: `/Users/ozai/Library/Application Support/vibemix/recordings/20260604-160156/ai_messages/artifacts/0001_160316/meta.json`
- Failure: `403 PERMISSION_DENIED` from the direct Gemini call, with `message_chars=0`, `raw_response_chars=0`, and `spoken_response_chars=0`.

Reproduction:
- Reused the exact saved live prompt and WAV:
  - prompt: `/Users/ozai/Library/Application Support/vibemix/recordings/20260604-160156/invocations/0001_160316_MANUAL/prompt.txt`
  - audio: `/Users/ozai/Library/Application Support/vibemix/recordings/20260604-160156/invocations/0001_160316_MANUAL/audio.wav`
- Routed model path: `live_coach`
- Model: router-resolved `gemini-3.5-flash`
- Tier: router-resolved `ServiceTier.STANDARD`
- Stream config shape matched the live path: `thinking_level=minimal`, `temperature=0`, `audio/wav` Part.

Probe result:
- `48.0s` inline WAV (`1536044` bytes): success, `chunks=2`, `text_chars=45`
- `60.0s` inline WAV (`1920044` bytes): failed with `ClientError`, `403 PERMISSION_DENIED`

Code change:
- Added `COACH_AUDIO_SECONDS = min(INVOKE_AUDIO_SECONDS, 48.0)` in `src/vibemix/agent/dj_cohost.py`.
- Non-diet Sven turns now send `COACH_AUDIO_SECONDS` to Gemini instead of the full rolling-buffer `INVOKE_AUDIO_SECONDS`.
- HEARTBEAT diet turns still send `6.0s`.
- The larger rolling capture buffer remains unchanged.

Validation:
- `uv run pytest -q tests/agent/test_dj_cohost_prompt_diet.py tests/agent/test_dj_cohost_scaffold_repair.py tests/eval/test_respan_sven_sim_quality_gate.py tests/eval/test_respan_sven_heartbeat_quality_gate.py tests/runtime/test_suggestion_voice.py tests/prompts/test_matrix.py tests/prompts/test_negative_dict.py`
  - `185 passed`
- `uv run ruff check src/vibemix/agent/dj_cohost.py tests/agent/test_dj_cohost_prompt_diet.py tests/agent/test_dj_cohost_scaffold_repair.py tests/eval/test_respan_sven_sim_quality_gate.py scripts/eval/respan_sven_sim.py src/vibemix/runtime/suggestion_voice.py src/vibemix/prompts/matrix.py`
  - pass
- Grounding-review bundle:
  - `373 passed`

Live note:
- I did not rerun a live by-bus probe after this patch because another `python -m vibemix` process was already bound on `127.0.0.1:8765`.
- The committed proof is the exact saved live prompt/audio replay through the Gemini SDK, which isolates the previous live blocker to the old 60s inline WAV request shape.
