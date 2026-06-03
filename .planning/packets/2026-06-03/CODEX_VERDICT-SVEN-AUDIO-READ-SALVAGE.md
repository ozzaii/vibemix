# CODEX VERDICT - Sven audio-read salvage

Item: live over-strip fix - salvage grounded broad audio reads before hidden source detail.

SHA: `03caf94c fix(sven): salvage grounded audio reads`

User value: a Free/live co-host user is less likely to get dead air when Sven says one
unsupported source-level noun inside an otherwise useful, citable audio read. The guard now
removes the unsupported source-detail clause and emits the cleaned AI line when the remaining
text still passes citation grounding.

By-eye / live artifact:

- Restarted current source through Tauri with `VIBEMIX_DEV_SIDECAR=1` and
  `VIBEMIX_OUTPUT_DEVICE='Multi-Output Device'`; ws bus was reachable on `127.0.0.1:8765`.
- Live session `20260603-154954` emitted a cited `KICK_DENSITY_SHIFT` reaction on the real bus:
  `That kick pattern just locked into a much denser, more rolling groove...`
- UI log showed `ipc.session.cohost-reaction` with `citation_strip: []`, and events.jsonl recorded
  `ai_message stop_reason="emit"` with `citation.count=1`.
- Branch-specific proof is pinned in tests: a response containing
  `The high end got super thin [ev:BAND_SHIFT_HIGH@5.12] and then those vocals and synth layers...`
  now emits `The high end got super thin.` instead of stripping the whole turn.

Checks:

- `uv run pytest -q tests/state/test_deck_context.py tests/agent/test_dj_cohost_linter.py` -> 170 passed.
- `uv run pytest -q tests/library/test_live_context_cli.py::test_cmd_library_verify_live_reply_rejects_audio_source_detail_claim tests/library/test_codex_curate.py::test_verify_live_reply_rejects_audio_source_detail_without_control_claim tests/library/test_codex_curate.py::test_chat_with_codex_blocks_audio_source_detail_without_control_claim tests/eval/test_cohost_viber_session_report.py::test_report_blocks_spoken_live_claim_guard_fallback tests/eval/test_cohost_viber_session_report.py::test_report_blocks_spoken_hidden_audio_source_detail` -> 5 passed.
- Grounding-review citation gate:
  `uv run pytest -q tests/state/test_coach_anti_slop.py tests/state/test_hype_anti_slop.py tests/agent/test_citation_strip_emit.py tests/agent/test_dj_cohost_grounding.py tests/agent/test_dj_cohost_linter.py tests/state/test_evidence_registry.py tests/coach/test_citation_linter.py tests/coach/test_citation_zero_orphan_replay.py` -> 112 passed.
- Trust-audio/no-speculative gate:
  `uv run pytest -q tests/learn/test_no_speculative_phrase.py tests/prompts/test_negative_dict.py tests/state/test_hype_anti_slop.py tests/state/test_coach_anti_slop.py tests/state/test_event_detector.py` -> 84 passed.
- `uv run ruff check src/vibemix/state/deck_context.py tests/state/test_deck_context.py tests/agent/test_dj_cohost_linter.py` -> passed.
- `git diff --check` -> passed.

Assumption / next issue:

- This does not fix the live BPM counter wobbling while Sven is talking. The restarted app showed
  BPM shifting during `cohost_status="TALKING"` while `voice.rms` was non-zero, so the next live bug
  is BPM/voice-loopback contamination.
