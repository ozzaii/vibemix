# CODEX_READY — Co-host TTS Citation Sanitizer

Date: 2026-06-01
Suggested commit: `fix(cohost): keep citation atoms out of tts`

## Why

The co-host uses bracketed citations as grounding receipts. Those atoms must
remain in raw model artifacts, citation telemetry, linter input, `ai_text`, and
`ai_message.message`, but MOSS should not read literal strings like
`[aud:rms@12.0]` aloud.

## Include

- `src/vibemix/agent/tts_sanitizer.py`
- `src/vibemix/agent/dj_cohost.py`
- `tests/agent/test_tts_sanitizer.py`
- `tests/agent/test_dj_cohost.py`
- `tests/agent/test_dj_cohost_streaming_pipe.py`
- `tests/agent/test_dj_cohost_linter.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`
- `.planning/packets/2026-06-01/CODEX_READY-cohost-tts-citation-sanitizer.md`

## Behavior

- Strip internal emote/voice tags and grounding citations only from chunks
  yielded into TTS.
- Preserve citations in visible/logged message text and artifacts so grounding
  receipts and verifier paths continue to work.
- Keep the bracket-balance streaming gate: incomplete citation fragments still
  never reach TTS.

## Keep Out

- No citation linter policy changes.
- No prompt rewrite.
- No Viber/library changes.
- No DROP-call speech or timing changes.

## Proof

Run before landing:

```bash
uv run pytest -q \
  tests/agent/test_tts_sanitizer.py \
  tests/agent/test_dj_cohost.py::test_llm_node_english_only_guard_preserves_grounded_english_response \
  tests/agent/test_dj_cohost.py::test_AE_citation_count_event_written_per_turn \
  tests/agent/test_dj_cohost.py::test_AJ_no_registry_path_writes_recorder_event_only \
  tests/agent/test_dj_cohost_streaming_pipe.py

uv run pytest -q \
  tests/agent/test_dj_cohost_linter.py \
  tests/agent/test_citation_strip_emit.py \
  tests/coach/test_citation_linter.py

uv run ruff check \
  src/vibemix/agent/tts_sanitizer.py \
  src/vibemix/agent/dj_cohost.py \
  tests/agent/test_tts_sanitizer.py \
  tests/agent/test_dj_cohost.py \
  tests/agent/test_dj_cohost_streaming_pipe.py \
  tests/agent/test_dj_cohost_linter.py

uv run python scripts/check_dirty_package_plan.py --strict-assignments --summary
```
