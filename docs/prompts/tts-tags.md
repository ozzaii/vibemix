# Retired Gemini TTS Tags — MOSS Live Voice Policy

vibemix's live co-host voice is **local MOSS-only**. The live product does not
route speech through Gemini TTS, OpenAI TTS, Cartesia, or any other cloud voice
provider, and the old cloud-TTS router aliases are intentionally invalid.

This page documents the retired Gemini TTS tag DSL so future work does not
accidentally re-enable it. The constants still exist for compatibility tests and
old prompt builders, but the live Sven/MOSS path opts out of the DSL.

## Current Live Contract

| Surface | Contract |
| --- | --- |
| Voice source | `vibemix.agent.tts_chain.build_tts_chain(mode=...)` builds the single local `MossLocalTTS` provider. |
| Live prompt | `DJCoHostAgent` calls `build_system_instruction(..., include_tag_dsl=False, include_audio_vibe_contract=True, include_coach_closing=True)`. |
| Legacy tag cleanup | `vibemix.agent.emote_parser.strip_emote_tags` strips known voice tags before speech/transcript output. |
| Router contract | `vibemix.llm.model_router.resolve(...)` has no product cloud-TTS route. |
| Proof tests | `tests/llm/test_tts_3_1.py`, `tests/llm/test_model_router.py`, `tests/agent/test_tts_chain.py`, and `tests/agent/test_dj_cohost.py`. |

The important separation: the co-host still gets the audio-vibe contract and
the professional coach closing, but it does **not** get prompted to write
delivery tags such as `[chill]` or `[excited]`.

## Legacy Tag Set

These six tags are historical Gemini-TTS controls. Treat them as internal
compatibility markers, not product behavior.

| Tag | Old intent | Current live behavior |
| --- | --- | --- |
| `[whisper]` | Lowered volume / intimate delivery | Not prompted; stripped if emitted. |
| `[laugh]` | Pre-recorded laughter overlay | Not prompted; stripped if emitted. |
| `[fast]` | Faster cadence | Not prompted; stripped if emitted. |
| `[slow]` | Drawn-out cadence | Not prompted; stripped if emitted. |
| `[excited]` | Pitched-up / energetic delivery | Not prompted; stripped if emitted. |
| `[chill]` | Relaxed delivery | Not prompted; stripped if emitted. |

Known tags may still appear in legacy fixtures, memory-ingest fixtures, and
compatibility tests. They should not appear in live prompt text, spoken text, or
new product-facing examples.

## Compatibility API

The compatibility constants live in `src/vibemix/prompts/matrix.py`:

- `TTS_TAGS`
- `TTS_TAG_DSL_BLOCK`
- `COACH_TAG_DSL_BLOCK`
- `build_system_instruction(include_tag_dsl=...)`

`build_system_instruction(...)` still defaults `include_tag_dsl=True` for old
byte-identity callers and prompt tests. Live co-host callers must pass
`include_tag_dsl=False` and separately keep `include_audio_vibe_contract=True`
when they need audio-grounding instructions.

## Do Not Re-Introduce

Do not add a new provider fallback or router alias to make the old DSL "work"
again. If MOSS is unavailable, the app should surface that voice is unavailable
or start muted by design; it must not silently route speech to paid/cloud TTS.

Do not use tags as a style-control substitute for better prompting. For live
Sven, the correct path is grounded, English-only, citation-checked text flowing
through the MOSS sanitizer, not bracket controls in the model output.

## Source Of Truth

| Layer | Path |
| --- | --- |
| MOSS-only TTS factory | `src/vibemix/agent/tts_chain.py` |
| Proxy-mode MOSS shim | `src/vibemix/agent/proxy_client.py` |
| Legacy tag parser/sanitizer | `src/vibemix/agent/emote_parser.py` |
| Prompt matrix compatibility constants | `src/vibemix/prompts/matrix.py` |
| Live prompt opt-out | `src/vibemix/agent/dj_cohost.py` |
| Router retirement tests | `tests/llm/test_tts_3_1.py` and `tests/llm/test_model_router.py` |
