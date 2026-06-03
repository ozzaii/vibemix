# CODEX VERDICT — BPM voice freeze + anti-whipsaw

Item: Live tuning regression from 2026-06-03 user report ("Sven stuttering",
"BPM counter issue").

SHA: `b3ea4c7d fix(runtime): steady bpm during sven speech`

User value: a Free/Pro user on the live session pill now sees a steady BPM
counter while Sven speaks; Sven's own voice no longer contaminates BPM
estimation or makes the compact readout blink to `0/null`.

What changed:
- `refresh.py` skips autocorr BPM estimation while the voice meter is active,
  preserving the last-good BPM cache.
- The BPM stabilizer now refuses far-away in-range alternate locks until a
  small cluster agrees, preventing visible `166 -> 150 -> 125` whipsaw.
- `ws_bus.py` / `session_loop.py` hold the public BPM readout during Sven
  speech without setting `grounded=true`; stale drop/track remain honest-null
  when music is not grounded.

By-eye / by-ear proof:
- Relaunched source app with `VIBEMIX_DEV_SIDECAR=1` and
  `VIBEMIX_OUTPUT_DEVICE='Multi-Output Device'`.
- Quiet pill frames held BPM instead of blinking to zero:
  `bpm=120` over repeated 2s frames, then one accepted cluster shift to
  `103.4`, held over repeated frames.
- Manual trigger emitted grounded Sven line with `citation_count=1` and
  `citation_strip=[]`.
- During the voice-meter window, pill/session frames held `bpm=103.4` while
  `voice` was non-zero; no `bpm=0` or `bpm=null` flicker was observed.

Verification:
- `uv run pytest -q tests/state/test_bpm_stabilize.py tests/state/test_refresh.py tests/state/test_bpm_bus_grounding.py tests/runtime/test_ws_bus_snapshot.py tests/runtime/test_session_loop.py tests/runtime/test_ws_bus_phase22_fields.py tests/runtime/test_ws_bus_genre_fields.py tests/runtime/test_ws_bus_deck_state.py tests/runtime/test_ws_bus.py`
  → `164 passed`.
- Grounding/invariant batch:
  `uv run pytest -q tests/state/test_coach_anti_slop.py tests/state/test_hype_anti_slop.py tests/agent/test_citation_strip_emit.py tests/agent/test_dj_cohost_grounding.py tests/agent/test_dj_cohost_linter.py tests/state/test_evidence_registry.py tests/coach/test_citation_linter.py tests/coach/test_citation_zero_orphan_replay.py tests/learn/test_no_speculative_phrase.py tests/prompts/test_negative_dict.py tests/state/test_event_detector.py`
  → `175 passed`.
- `uv run ruff check ...` on touched files → pass.
- `git diff --check` on touched files → pass.

Notes / remaining follow-up:
- The app is still running from source with output routed to `Multi-Output
  Device`.
- FLX4/controller attribution remains unresolved in the live frame
  (`connected_no_midi_traffic`, `no_single_attributable_deck`), so next-song
  receipts remain blocked until deck identity/cue attribution is live.
