# CODEX VERDICT - SVEN KAAN SPOKE FULL EAR

Item: user-directed Sven prompt feed: `KAAN_SPOKE` should not use the tiny heartbeat diet window.

SHA: `8926fcae` (`fix(cohost): give user speech the full live ear`).

User value: when Kaan talks to Sven during a set, the AI now hears the full recent live mix before answering, instead of responding from a 6s acknowledgement slice plus mic audio only.

What changed:
- `KAAN_SPOKE` was removed from `RUNTIME_DIET_EVENTS`.
- `HEARTBEAT` remains the only diet event.
- User-directed speech turns now call `snapshot_wav(..., INVOKE_AUDIO_SECONDS)`, currently 60s per `audio/constants.py`, while the separate mic Part still carries the recent spoken window.

Proof:
- `uv run pytest -q tests/agent/test_dj_cohost_prompt_diet.py` -> 13 passed.
- `uv run pytest -q tests/state/test_coach_anti_slop.py tests/state/test_hype_anti_slop.py tests/agent/test_citation_strip_emit.py tests/agent/test_dj_cohost_grounding.py tests/agent/test_dj_cohost_linter.py tests/state/test_evidence_registry.py tests/coach/test_citation_linter.py tests/coach/test_citation_zero_orphan_replay.py` -> 114 passed.
- `uv run pytest -q tests/learn/test_no_speculative_phrase.py tests/prompts/test_negative_dict.py tests/state/test_hype_anti_slop.py tests/state/test_coach_anti_slop.py tests/state/test_event_detector.py` -> 84 passed.
- `uv run ruff check src/vibemix/agent/dj_cohost.py tests/agent/test_dj_cohost_prompt_diet.py` -> pass.
- `git diff --check -- src/vibemix/agent/dj_cohost.py tests/agent/test_dj_cohost_prompt_diet.py` -> pass.

By-ear/by-eye artifact:
- Meeting-safe only: no app was launched and no speaker/TTS path was opened after the user reported active talking in a meeting.
- Unit-level live-turn artifact: the pinned `KAAN_SPOKE` path now asserts `snapshot_wav` receives `INVOKE_AUDIO_SECONDS` and `diet=False`; the `llm_invoke` log contract remains pinned through the same prompt-diet suite.

Notes:
- This does not add a new speak trigger or loosen citation stripping. It only gives an already-fired user speech turn more live audio evidence.
- Current answer to the 30s vs 8s question: musical/user-directed full turns get 60s of P1 master mix; heartbeat stays 6s; mic speech Part is 8s when recent.
