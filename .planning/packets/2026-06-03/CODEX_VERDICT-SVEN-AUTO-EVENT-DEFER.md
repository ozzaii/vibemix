# CODEX VERDICT - SVEN-AUTO-EVENT-DEFER

Item: stop risky auto-event text from reaching TTS before live-claim guard verdict.

SHA: `8e91de69 fix(sven): defer risky auto-event speech until guarded`

User value: a live Free/Pro user still gets grounded Sven reactions, but KICK_SWAP /
PHRASE_BOUNDARY-style auto events no longer leak raw transition or mixer advice into
MOSS before the guard can strip it.

By-ear/by-eye artifact:

- Before the fix, the live session `20260603-162215` showed stripped auto-event turns
  with `head_yielded=true`, followed by visible voice energy. Example:
  `live_claim_guard action=strip policy=transition_coaching_not_grounded` and
  `extra.head_yielded=true`.
- The regression now pins that shape with a KICK_SWAP no-move turn:
  `chunks == []`, `streaming_cancel` absent, playback silence-pad absent,
  `ai_message.extra.head_yielded is False`, and `live_claim_defer_stream is True`.
- Current-source app was relaunched after the patch. Boot confirmed:
  - `AI voice -> Multi-Output Device @ 24000Hz`
  - `djay passthrough -> Multi-Output Device @ 48000Hz`
  - `mascot bus on ws://127.0.0.1:8765`
- Fresh session `20260603-163006` was observed over ws for 30s; no KICK_SWAP /
  PHRASE_BOUNDARY event fired in that window, and `voice=0.0` while listening.

Verification:

- `uv run pytest -q tests/agent/test_dj_cohost_linter.py::test_live_claim_guard_defers_no_move_kick_swap_before_tts tests/agent/test_dj_cohost_linter.py::test_live_claim_guard_emits_salvaged_audio_read_before_harmonic_advice tests/agent/test_dj_cohost_linter.py::test_live_claim_guard_blocks_mixer_claim_surviving_harmonic_salvage tests/agent/test_dj_cohost_streaming_pipe.py::test_citation_failure_after_head_emits_cancel tests/agent/test_dj_cohost_streaming_pipe.py::test_citation_pass_no_head_yields_after_stream`
  - `5 passed`
- `uv run pytest -q tests/state/test_deck_context.py::test_live_claim_stream_defers_no_move_auto_audio_events_only tests/state/test_deck_context.py -k "live_claim or defer"`
  - `64 passed, 83 deselected`
- `uv run pytest -q tests/agent/test_dj_cohost_linter.py tests/agent/test_dj_cohost_streaming_pipe.py tests/state/test_deck_context.py`
  - `185 passed`
- `uv run pytest -q tests/state/test_coach_anti_slop.py tests/state/test_hype_anti_slop.py tests/agent/test_citation_strip_emit.py tests/agent/test_dj_cohost_grounding.py tests/agent/test_dj_cohost_linter.py tests/state/test_evidence_registry.py tests/coach/test_citation_linter.py tests/coach/test_citation_zero_orphan_replay.py`
  - `113 passed`
- `uv run pytest -q tests/learn/test_no_speculative_phrase.py tests/prompts/test_negative_dict.py tests/state/test_hype_anti_slop.py tests/state/test_coach_anti_slop.py tests/state/test_event_detector.py`
  - `84 passed`
- `uv run ruff check src/vibemix/state/deck_context.py tests/state/test_deck_context.py tests/agent/test_dj_cohost_linter.py`
  - passed
- `git diff --check -- src/vibemix/state/deck_context.py tests/state/test_deck_context.py tests/agent/test_dj_cohost_linter.py`
  - passed

Assumption correction:

- This does not make Sven quieter globally. HEARTBEAT keeps the old speculative
  streaming path; only no-move auto audio events whose live-claim policy is
  `requires_more_evidence` wait for the full guard pass before TTS.
- The live proof window did not naturally produce a new KICK_SWAP / PHRASE_BOUNDARY,
  so the exact stripped-turn artifact is test-pinned and ready for the next real
  auto-event observation.
