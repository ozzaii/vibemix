# Gemini 3.1 Flash TTS — Audio Tag DSL

vibemix's live coach speaks through Gemini 3.1 Flash TTS. The TTS supports
six **inline audio tags** that the LLM emits as the first token of a
response; the TTS reads them at synthesis time as expressivity directives
(volume, cadence, pitch).

This DSL replaces inline prose hints like "you whisper conspiratorially"
with a structured marker the TTS understands directly.

| Source | Constant |
| ------ | -------- |
| Tag set | [`vibemix.prompts.matrix.TTS_TAGS`](../../src/vibemix/prompts/matrix.py) |
| Inline DSL block (rendered into every coach turn's system instruction) | [`vibemix.prompts.matrix.TTS_TAG_DSL_BLOCK`](../../src/vibemix/prompts/matrix.py) |
| TTS model id | [`vibemix.llm.model_router.resolve("live_coach_tts")`](../../src/vibemix/llm/model_router.py) → `gemini-3.1-flash-tts-preview` |

## The 6 supported tags

| Tag | Intent | Example | Recommended events |
| --- | ------ | ------- | ------------------ |
| `[whisper]` | Lowered volume, intimate, sotto voce | `[whisper] insider tip — that loop's a sleeper` | KAAN_SPOKE replies that share insider knowledge; pre-drop hush moments |
| `[laugh]` | Pre-recorded laughter overlay | `[laugh] yeah that bassline got me good` | Shared inside jokes; wild blend reactions. **Use sparingly** — overuse reads as theatrical. |
| `[fast]` | Accelerated cadence, urgent | `[fast] DROP HERE — kick comes in 2 bars` | PHASE event hits; hyped drops; warning calls |
| `[slow]` | Drawn-out cadence | `[slow] feel that bassline settling in` | Emotional anchors; deep grooves; ambient sections |
| `[excited]` | Pitched-up, energetic | `[excited] THAT'S the drop right there` | PHASE event hits; build resolutions; peak energy |
| `[chill]` | Relaxed, low-key | `[chill] easy now, just floating` | Warmup phase; late-set wind-downs; ambient sections |

## How the LLM uses tags

The tag is the **first token** of the spoken reply (after optional
whitespace). Scope is the rest of the line. **One tag per reply** is the
norm; multi-tag is undefined behavior.

```text
[whisper] that one's a sleeper, watch what happens at 8 bars in
```

vs the untagged default (casual studio-friend voice):

```text
that one's a sleeper, watch what happens at 8 bars in
```

**Default is no tag.** Reach for one only when the moment warrants it —
the "real DJ friend in your ear" anti-slop principle applies: tag-stuffing
sounds like AI announcer voice, the opposite of what we ship.

## Where the DSL lives in the prompt

The DSL block (`TTS_TAG_DSL_BLOCK`) is appended to every live coach
system instruction by default via
`build_system_instruction(include_tag_dsl=True)`. The block lives **after**
the citation-grammar block and the fail-soft fragment — the LLM learns
grounding first (load-bearing for the anti-hallucination thesis), then
expressivity second.

```python
# Default — tags rendered:
body = build_system_instruction(skill="intermediate", mode="hype")
# body contains all 6 tag examples + intent descriptions

# Byte-identity callers (persona.SYSTEM_INSTRUCTION) — tags suppressed:
body = build_system_instruction(
    skill="intermediate",
    mode="hype",
    include_citation_grammar=False,
    include_listening_fallback=False,
    include_tag_dsl=False,
)
# body byte-identical to v4 HYPE_INTERMEDIATE
```

## Persona overlay opt-in / opt-out

Persona overlays opt in by default (every live coach turn sees the DSL).
To suppress tags for a specific persona (e.g. a minimal-affect "stoic
coach" persona), pass `include_tag_dsl=False` at the dispatcher boundary.

```python
# Stoic-coach persona — no expressivity tags:
body = build_system_instruction(
    skill="pro",
    mode="coach",
    mood="teacher",  # or a future "stoic" mood
    include_tag_dsl=False,
)
```

There is currently no per-event-type tag whitelist; the LLM decides
when to reach for a tag based on context + intent. Future iterations
may add `{event_type: [allowed_tags]}` whitelisting if Phase 16 ear-test
data shows overuse of a particular tag.

## Unknown tags

Behavior when the LLM emits a tag NOT in the canonical set (e.g.
`[invented_tag] hi`):

- **Pinned via VCR cassette** in
  [`tests/llm/test_tts_3_1.py::test_unknown_tag_behavior_documented`](../../tests/llm/test_tts_3_1.py).
- **Cassette recording is deferred to a Kaan-action item** — the test
  is skipped until cassettes are recorded via
  `VCR_RECORD_MODE=new_episodes uv run pytest tests/llm/test_tts_3_1.py`
  with a real `GEMINI_API_KEY`.
- Whichever shape Gemini 3.1 Flash TTS captures (pass-through-literal vs
  strip-with-warning) IS the canonical contract. Once cassettes are
  recorded, update this section to document the observed behavior.

The threat model considers unknown tags low-risk (T-41-04-05):
worst-case is a literal `[invented_tag]` audible in the output — a
user-noticeable bug, not a security risk. No code execution surface;
the LLM is not given filesystem / network access via tag syntax.

## Where the spec came from

- Gemini 2026-Q1 release notes — "200+ audio tags" for 3.1 Flash TTS.
- vibemix's curated subset = 6 tags chosen for DJ-coach intent
  coverage (insider/hype/anchor/build/chill spectrum), not the full
  200+ set. Adding tags is a one-line edit to `TTS_TAGS` +
  `TTS_TAG_DSL_BLOCK` + an entry in the table above.

## Where the spec lives

| Layer | Path |
| ----- | ---- |
| Tag set + DSL block constant | `src/vibemix/prompts/matrix.py` |
| Per-turn injection point | `vibemix.prompts.matrix.build_system_instruction(include_tag_dsl=True)` |
| Default-on for live coach | `DJCoHostAgent.__init__` (via `_resolve_prompt_cell`) |
| TTS model resolution | `vibemix.llm.model_router.resolve("live_coach_tts")` |
| Tests | `tests/llm/test_tts_3_1.py` + `tests/prompts/test_matrix.py` |

## Public surface

This document is part of the **public-facing OSS surface** post-v3.0
ship — external contributors who want to extend the DSL (add tags,
change intent mapping) start here. The DSL is intentionally short —
new tags require a Phase-16 ear-test pass before landing.
