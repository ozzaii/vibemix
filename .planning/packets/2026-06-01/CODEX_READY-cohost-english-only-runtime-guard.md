# CODEX_READY — Co-host English-Only Runtime Speech Guard

Date: 2026-06-01
Suggested commit: `fix(cohost): enforce english-only spoken output`

## Why

Claude's read-only verifier for `de9a55f5` / `a9cb2193` / `c88d5f56` accepted the
co-host grounding and MOSS tag cleanup, but found one remaining speech gap:
English-only behavior was prompt-enforced only. A non-English model response could
still pass the runtime sanitizer and reach MOSS, transcript, `ai_text`, and
`ai_message.message`.

## Include

- `src/vibemix/agent/language_guard.py`
- `src/vibemix/agent/dj_cohost.py`
- `tests/agent/test_language_guard.py`
- `tests/agent/test_dj_cohost.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`
- `.planning/packets/2026-06-01/CODEX_READY-cohost-english-only-runtime-guard.md`

## Behavior

- Keep raw model output in per-invocation artifacts and `ai_message` response
  artifacts.
- Suppress obvious Turkish/Turkish-flavored DJ chat before it reaches MOSS or
  user-visible transcript rows.
- Log `non_english_suppressed` with matched signals.
- Save the `ai_message` row with `message=""`, `suppression="non_english"`, and
  `extra.language_matches`.
- Allow English DJ language, citations, and Turkish-character artist names when
  the surrounding sentence is English.

## Keep Out

- No DROP-call speech.
- No deck/controller audio inference.
- No Viber/library rewriting.
- No broad prompt/persona rewrite.
- No new dependency or general-purpose language detector.

## Proof

Run before landing:

```bash
uv run pytest -q \
  tests/agent/test_language_guard.py \
  tests/agent/test_dj_cohost.py::test_llm_node_suppresses_non_english_spoken_text_but_keeps_raw_artifact \
  tests/agent/test_dj_cohost.py::test_llm_node_english_only_guard_preserves_grounded_english_response \
  tests/agent/test_dj_cohost.py::test_llm_node_strips_legacy_voice_tags_from_speech_and_ai_message \
  tests/agent/test_dj_cohost.py::test_llm_node_strips_emote_tags_and_sets_mascot_intent \
  tests/agent/test_dj_cohost_streaming_pipe.py

uv run pytest -q \
  tests/prompts/test_matrix.py \
  tests/agent/test_dj_cohost_linter.py \
  tests/state/test_coach_anti_slop.py

uv run ruff check \
  src/vibemix/agent/language_guard.py \
  src/vibemix/agent/dj_cohost.py \
  tests/agent/test_language_guard.py \
  tests/agent/test_dj_cohost.py

uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary
```

## Remaining Gate

This is a runtime backstop, not a full language detector. Future prompt work can
still make the model less likely to try non-English phrasing, but product safety
must not depend on that prompt staying perfect.
