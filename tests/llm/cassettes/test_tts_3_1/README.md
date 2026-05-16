# VCR cassettes — Gemini 3.1 Flash TTS audio-tag DSL (Plan 41-04 LAT-05)

## Status

**Cassettes not yet recorded.** The
`tests/llm/test_tts_3_1.py::test_unknown_tag_behavior_documented` test is
skipped until a recording session lands.

## Why deferred

Per `gsd-autonomous fully` defer protocol, the live `GEMINI_API_KEY`
recording was deferred to a Kaan-action recording session. The mock-based
unit tests cover the router-derivation contract + tag-DSL injection
shape; the cassette tests would additionally pin the actual audio-
response behavior of each tag.

## Recording instructions

```bash
# From repo root, with a real GEMINI_API_KEY in .env:
VCR_RECORD_MODE=new_episodes uv run pytest tests/llm/test_tts_3_1.py -v
```

The cassette files will land here as `*.yaml` (one per test). Commit
them to git and re-run without `VCR_RECORD_MODE` to verify cassette
playback is deterministic.

After recording, update
[`docs/prompts/tts-tags.md`](../../../../docs/prompts/tts-tags.md)
"Unknown tags" section to document the observed behavior (pass-through
vs strip).
