# CODEX VERDICT — SVEN-SOURCE-DETAIL-TAIL

Item: live Sven source-detail salvage follow-up

SHA: `ecd4ba83` (`fix(sven): salvage grounded sub-layer reads`)

User value: a Free live co-host user now hears a useful, grounded sub-layer read instead of
either unsupported source-detail slop or a full mute when the model adds an unproven vocal tail.

What changed:

- `deck_context` now strips unsupported source-detail tails like `under that ... vocal line`
  while preserving the cited broad audio read before it.
- `SUB_LAYER_ARRIVAL` broad sub/low-end observations are treated as detector-event audio reads,
  not transition/blend grades, when they do not mention a second deck or transition outcome.
- A transition claim on the same event still blocks.

By-eye / by-ear artifact:

- Relaunched the real Tauri dev app against current source with
  `VIBEMIX_DEV_SIDECAR=1 VIBEMIX_OUTPUT_DEVICE='Multi-Output Device'`.
- `ws_observe(12s)` saw `342` frames, `ipc.status.tick` with `livekit=ok`,
  `gemini=ok`, `midi=1`, `screen=unavailable`, moving music meters, grounded snapshots,
  and `cohost_status=LISTENING`.
- `tail_ui_log` showed the shell connected to `ws://127.0.0.1:8765`, `voice=0`,
  moving music meter, `bpm=176.5` then `120`, and `grounded=true`.
- `sounddevice.query_devices()` verified persisted `output_device_id=14` is
  `Multi-Output Device`, so the relaunch did not route voice to MacBook speakers.

Grounding / tests:

- `uv run pytest -q tests/state/test_deck_context.py tests/agent/test_dj_cohost_linter.py`
  → `176 passed`
- `uv run pytest -q tests/state/test_coach_anti_slop.py tests/state/test_hype_anti_slop.py tests/agent/test_citation_strip_emit.py tests/agent/test_dj_cohost_grounding.py tests/agent/test_dj_cohost_linter.py tests/state/test_evidence_registry.py tests/coach/test_citation_linter.py tests/coach/test_citation_zero_orphan_replay.py`
  → `114 passed`
- `uv run pytest -q tests/learn/test_no_speculative_phrase.py tests/prompts/test_negative_dict.py tests/state/test_hype_anti_slop.py tests/state/test_coach_anti_slop.py tests/state/test_event_detector.py`
  → `84 passed`
- Viber batch/timeout regression slice:
  `tests/library/test_setprep_tools.py::test_inspect_candidates_batches_features_sections_and_energy`,
  `::test_inspect_candidates_parallelizes_rows`,
  `::test_inspect_candidates_rejects_unseen_ids_per_row`,
  `::test_dispatch_gives_batched_candidate_inspection_a_larger_timeout`,
  `tests/library/test_codex_curate.py::test_build_set_prompt_has_set_prep_workflow`,
  `::test_chat_prompt_threads_history_and_rules`,
  `::test_chat_timeout_is_interactive`,
  `::test_codex_mcp_tool_timeout_allows_batched_candidate_inspection`
  → `8 passed`
- `uv run pytest -q tests/library/test_setprep_tools.py tests/library/test_codex_curate.py`
  → `125 passed`
- `uv run ruff check src/vibemix/state/deck_context.py tests/state/test_deck_context.py tests/agent/test_dj_cohost_linter.py`
  → pass
- `git diff --check` → pass

Assumption / note:

- The exact live `SUB_LAYER_ARRIVAL` event did not naturally refire during the short relaunch
  window, so the exact utterance is pinned at the co-host boundary test. The running app proof
  confirms the patched source boots, stays connected, and remains safely routed.
