# CODEX VERDICT — SVEN-SOURCE-DETAIL-SALVAGE

- Item: fix mangled Sven prose when the live-claim guard salvages broad audio reads.
- SHA: `25091e2f fix(sven): keep salvaged audio reads grammatical`
- User value: a Free user hearing Sven gets the useful broad audio read without broken citation debris or shredded comma fragments.

## By-Eye / By-Ear Artifact

Live session `20260603-163837` exposed the failure: an unsupported source-detail clause with `[track:Varg²™, Ecco2k, & Bladee - H2D]` was salvaged into broken text containing `cold. metallic... Ecco2k... ]`.

Pinned reproduction now passes:

```text
Input:
The whole space opened up with that cold, metallic sub-bass drone and those slow, sharp synth plucks cutting through the top [track:Varg²™, Ecco2k, & Bladee - H2D].

Corrected output:
The whole space opened up with that cold, metallic sub-bass drone.
```

Real app proof after relaunch:

- Started Tauri dev with `VIBEMIX_DEV_SIDECAR=1 VIBEMIX_OUTPUT_DEVICE='Multi-Output Device'`.
- `ws://127.0.0.1:8765` reachable; `ipc.status.tick` showed `gemini=ok`, `livekit=ok`, `midi=1`.
- UI log showed music meter moving and voice meter `0`; boot heartbeat stayed silent.

## Gates

- `uv run pytest -q tests/state/test_deck_context.py::test_live_claim_guard_salvages_source_detail_without_comma_shredding tests/state/test_deck_context.py::test_live_claim_guard_suppresses_eq_audio_song_detail_verdict tests/agent/test_dj_cohost_linter.py::test_live_claim_guard_emits_cleaned_audio_read_before_hidden_source_detail tests/agent/test_dj_cohost_linter.py::test_live_claim_guard_strips_hidden_source_detail_before_tts` -> 4 passed.
- `uv run pytest -q tests/state/test_deck_context.py tests/agent/test_dj_cohost_linter.py` -> 173 passed.
- Grounding invariant batch: `uv run pytest -q tests/state/test_coach_anti_slop.py tests/state/test_hype_anti_slop.py tests/agent/test_citation_strip_emit.py tests/agent/test_dj_cohost_grounding.py tests/agent/test_dj_cohost_linter.py tests/state/test_evidence_registry.py tests/coach/test_citation_linter.py tests/coach/test_citation_zero_orphan_replay.py` -> 113 passed.
- Trust-audio/no-spec batch: `uv run pytest -q tests/learn/test_no_speculative_phrase.py tests/prompts/test_negative_dict.py tests/state/test_hype_anti_slop.py tests/state/test_coach_anti_slop.py tests/state/test_event_detector.py` -> 84 passed.
- `uv run ruff check src/vibemix/state/deck_context.py tests/state/test_deck_context.py` -> pass.
- `git diff --check` -> pass.

## Notes

- The guard still strips unsupported source-level nouns such as synth/vocal/kick unless a detector/event supports them.
- The change only removes bare comma splitting from the salvage path; conjunction splits still remove unsupported source-detail clauses.
