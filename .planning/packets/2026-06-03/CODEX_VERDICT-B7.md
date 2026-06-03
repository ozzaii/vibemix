# CODEX VERDICT - B7 section-pairing voice receipt

Item: B7 - voice the grounded section pairing on the next-suggestion receipt.

SHA: `2244c3e7` (`feat(sven): voice section-pairing receipts`)

User value: a Free/Pro live user can now hear Sven name the computed section move
when the next-suggestion payload already has grounded section roles, e.g. "mix
out of this outro into that intro", instead of hearing only a generic candidate
receipt.

What shipped:
- `build_next_suggestion_voice_line()` now registers
  `[mix:next_suggestion_section=<from>_to_<to>]` before exposing the section
  clause to Sven.
- The clause only emits when both roles are present and not `unknown`.
- No new speak trigger, no new model pass, no IPC/schema change, and no new
  citation source.

By-ear / by-eye artifact:
- Current-source app launched meeting-safe:
  `VIBEMIX_DEV_SIDECAR=1 VIBEMIX_LOCAL_TTS=0 VIBEMIX_OUTPUT_DEVICE='Multi-Output Device' uv run python -m vibemix`.
- Boot confirmed `djay passthrough -> Multi-Output Device @ 48000Hz`,
  `voice muted`, `midi=1`, `gemini=ok`, and bus `ws://127.0.0.1:8765`.
- `ws_observe` saw `next_suggestion:null`, `audible:false`, `deck:none`,
  `phase:silent`, and `voice:"muted"` in session `20260603-211553`, so the live
  rig did not produce a real section-rich suggestion during this proof window.
- Runtime builder proof against the production receipt path produced:
  `Section pairing: mix out of this outro into that intro.` plus
  `[mix:next_suggestion_section=outro_to_intro]`, with
  `CitationLinter(..., mode="live") -> valid`.
- Coach-loop integration proof pins the same clause and citation on
  `ev.extra["next_suggestion_voice_line"]` before the event is handed to the
  agent.

Grounding:
- PASS: the new section claim is register-then-cite through existing
  existence-only `mix` evidence.
- PASS: unknown or missing roles abstain from the section clause and do not
  register a section key.
- PASS: the defensive "not a proven transition" tail survived.

Verification:
- `uv run pytest -q tests/runtime/test_suggestion_voice.py` -> 5 passed.
- `uv run pytest -q tests/runtime/test_suggestion_voice.py tests/runtime/test_coach.py::test_coach_hands_grounded_next_suggestion_to_agent` -> 6 passed.
- `uv run pytest -q tests/runtime/test_coach.py tests/runtime/test_suggestion_voice.py` -> 26 passed.
- `uv run pytest -q tests/runtime/test_suggestion_voice.py tests/state/test_evidence_registry.py tests/coach/test_citation_linter.py tests/agent/test_citation_strip_emit.py tests/agent/test_dj_cohost_grounding.py tests/agent/test_dj_cohost_linter.py` -> 91 passed.
- `uv run pytest -q tests/learn/test_runtime_invariants.py tests/learn/test_no_new_ws_port.py tests/runtime/test_ws_bus.py tests/learn/test_no_speculative_phrase.py tests/prompts/test_negative_dict.py tests/state/test_hype_anti_slop.py tests/state/test_coach_anti_slop.py` -> 57 passed.
- `uv run pytest -q tests/state/test_event_detector.py tests/state/test_refresh.py tests/state/test_music_state.py` -> 132 passed.
- `npm --prefix tauri/ui test -- tests/session/grounding-failure.spec.ts` -> 12 passed.
- `uv run ruff check src/vibemix/runtime/suggestion_voice.py tests/runtime/test_suggestion_voice.py tests/runtime/test_coach.py` -> pass.
- `git diff --check -- src/vibemix/runtime/suggestion_voice.py tests/runtime/test_suggestion_voice.py` -> pass.

Packet assumptions / caveats:
- The packet expected a live suggestion with section roles. The current local rig
  was silent and had no deck attribution, so the live app proof confirmed the app
  was up and correctly quiet, but not a spoken section-rich suggestion.
