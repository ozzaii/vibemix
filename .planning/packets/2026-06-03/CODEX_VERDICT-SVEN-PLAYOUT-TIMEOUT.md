# CODEX VERDICT - SVEN-PLAYOUT-TIMEOUT

Item: accidental Sven stutter after reply/playout timeout.

SHA: `22cc9b1b fix(runtime): cancel stale sven playout on timeout`

User value: a live Free/Pro user with Sven enabled no longer hears stale queued speech keep
playing after the reply path times out.

By-ear/by-eye artifact:

- Current-source app relaunched with voice and djay passthrough routed to
  `Multi-Output Device`, not MacBook speakers.
- Sidecar boot log confirmed:
  - `AI voice -> Multi-Output Device @ 24000Hz`
  - `djay passthrough -> Multi-Output Device @ 48000Hz`
  - `tts: MOSS-TTS-Nano local only`
- Code now interrupts the active speech handle and clears the playback queue when
  `wait_for_playout()` times out, so a stale in-flight utterance cannot keep stuttering
  after the timeout boundary.

Verification:

- `uv run pytest -q tests/runtime/test_coach.py::test_coach_11_timeout_doesnt_crash_loop tests/runtime/test_coach_cancel_wiring.py tests/runtime/test_cancel.py`
  - `14 passed`
- `uv run pytest -q tests/runtime/test_coach.py tests/runtime/test_coach_cancel_wiring.py tests/runtime/test_cancel.py tests/runtime/test_speak_gate.py`
  - `43 passed`
- `uv run pytest -q tests/state/test_coach_anti_slop.py tests/state/test_hype_anti_slop.py tests/agent/test_citation_strip_emit.py tests/agent/test_dj_cohost_grounding.py tests/agent/test_dj_cohost_linter.py tests/state/test_evidence_registry.py tests/coach/test_citation_linter.py tests/coach/test_citation_zero_orphan_replay.py`
  - `112 passed`
- `uv run pytest -q tests/learn/test_no_speculative_phrase.py tests/prompts/test_negative_dict.py tests/state/test_hype_anti_slop.py tests/state/test_coach_anti_slop.py tests/state/test_event_detector.py`
  - `84 passed`
- `uv run ruff check src/vibemix/runtime/coach.py tests/runtime/test_coach.py`
  - passed
- `git diff --check -- src/vibemix/runtime/coach.py tests/runtime/test_coach.py`
  - passed

Assumption correction:

- The live log also exposed a separate bug: some LLM text is printed as
  `ai_text:live-claim-stripped` while voice energy still rises immediately after.
  That is not fixed by this timeout patch and should be handled as a separate
  guard-before-playout bug.
