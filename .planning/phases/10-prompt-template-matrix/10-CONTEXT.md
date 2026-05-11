# Phase 10: Prompt Template Matrix - Context

**Gathered:** 2026-05-12
**Status:** Ready for planning
**Mode:** Auto-generated (autonomous)

<domain>
## Phase Boundary

Build the prompt-engineering substrate that makes vibemix sound like a real DJ friend, not generic AI slop. Six prompt templates (Beginner / Intermediate / Pro × Hype-man / Coach) + the full anti-slop stack: negative dictionary, TurnHistory ring, `<silence/>` token, describe-before-infer anchoring, past-tense framing, reaction throttle, Coach scorecard.

**Scope:** Python prompt-template module (`vibemix.prompts/`), TurnHistory ring, negative-dictionary regex bans + post-hoc filter, `<silence/>` token consumer in the cascade, scorecard module, wiring into `dj_cohost.py` so the agent picks the right cell from a `(skill_level, mode)` setting.

**Out of scope:** UI for picking skill/mode (Phase 11/12 — Settings panel), live A/B test of prompts on real audio (Phase 16 + 17), multi-language prompts (out of v1 — English only).
</domain>

<decisions>
## Implementation Decisions

### Locked

- **Matrix shape**: 6 cells = 3 skill levels × 2 modes.
  - Skill levels: `beginner` / `intermediate` / `pro`
  - Modes: `hype` (the existing v4 persona — "DJ friend in your ear") / `coach` (more critical; honest feedback bias; offers concrete improvement nudges)
- **Per-cell vocabulary anchoring**: each prompt has 8-12 concrete phrases the persona naturally uses (e.g., Beginner-Hype: "yo that drop", "this groove is sick", "vibe check"; Pro-Coach: "phrase ended on the 3", "EQ swap was clean", "low-mid pile-up there"). NOT generic adjectives.
- **Negative dictionary** (~40 words, hard ban):
  - Generic AI tells: "as an AI", "I don't have", "I'm here to help", "let me know", "feel free", "happy to assist", "delve", "leverage", "synergy", "robust", "seamless", "comprehensive", "elevate", "unleash", "tapestry"
  - Empty hype: "amazing", "awesome", "incredible", "fantastic", "great mix", "wonderful", "superb", "outstanding", "impressive", "love it", "killing it", "nailed it"
  - Slop framings: "in this dynamic world", "at the intersection of", "navigate the landscape", "unlock the potential"
- **Enforcement strategy** (3-layer):
  1. **Prompt-level**: each template explicitly enumerates the bans + says "use these phrases instead".
  2. **Post-hoc filter** in `vibemix.prompts.filter`: regex-check the LLM output before TTS; if any banned phrase matches, log a metric event and replace with `<silence/>` token (don't try to rewrite — just suppress). Tracked in `events.jsonl` as `slop_suppressed` events.
  3. **Tests**: per-cell golden test that verifies the prompt string contains the ban list + a unit test on the filter that exercises the regex on synthetic LLM outputs.
- **TurnHistory** (port from `cohost.py:~1075`): per-session ring of last N=12 model utterances. Injected as `<recent_turns>` block in every prompt. Coach prompts get an explicit "do not repeat openers from the last 10 minutes" rule.
- **`<silence/>` short-circuit**: LLM is told to emit literal `<silence/>` (no other text) when nothing's worth reacting to. The cascade `llm_node` override in `dj_cohost.py` checks for this token in the streaming output; if present, suppresses the entire turn (no TTS, no playback). Logged to `events.jsonl` as `silence_short_circuit`.
- **Describe-before-infer anchoring**: every prompt includes "describe what you HEAR first (one phrase) before any judgment or genre tag". Anti-hallucination pattern.
- **Past-tense framing**: reactions describe what just happened ("that cut landed clean") not what's happening ("this cut is landing clean") — prevents real-time hallucination when the model's audio context is 2-7s stale.
- **Reaction throttle**: max-rate cap (1 reaction per 30s per event-type) AND a global cap (1 reaction per 8s any type) both enforced in `EventDetector` (Phase 3). Phase 10 just adds the global cap; per-type cooldown already exists.
- **Coach scorecard**: at session end, Coach-mode emits a qualitative summary by band — `clean` (no slop fired, 0-2 abrupt moves) / `decent` (1-2 slop suppressions, 3-5 abrupt) / `abrupt` (more) / `train-wreck`. NEVER numeric. Persisted in `events.jsonl` as `coach_scorecard`.
- **Wiring**: `vibemix.agent.persona` becomes a thin re-export of `vibemix.prompts.matrix.build_system_instruction(skill, mode)`. `dj_cohost.py` reads `(VIBEMIX_SKILL_LEVEL, VIBEMIX_MODE)` env vars (defaults: `intermediate`, `hype`).

### Claude's Discretion

- Exact wording of each of the 6 prompt cells — derive from v4's existing SYSTEM_INSTRUCTION (Hype-Intermediate is essentially v4); the other 5 cells differentiate by skill register + mode bias.
- Filter post-processing: replace banned phrase in-place vs suppress whole turn — pick suppress-whole-turn (cheaper, blunter, can be relaxed in Phase 14 polish).
- TurnHistory storage: in-memory only (no disk persistence v1).
</decisions>

<code_context>
## Existing Code Insights

- `src/vibemix/agent/persona.py` — single SYSTEM_INSTRUCTION constant ported from v4 (Phase 4 — byte-identical to v4:150-213).
- `src/vibemix/agent/dj_cohost.py` — `DJCoHostAgent` class wraps LiveKit AgentSession; `llm_node` override calls `google.genai.aio.models.generate_content_stream` directly.
- `src/vibemix/state/coach.py` (155 lines) — AICoach class with task strings byte-identical to v4:1391-1427. Phase 10 keeps this as-is and adds the prompt-matrix layer above it.
- `cohost_v4.py:1075-1090` (approximate) — original TurnHistory class with `push_user`, `push_model`, `as_text` ring methods. 12-turn capacity. Port verbatim.
- `cohost.py` (POC) had per-turn `<recent_turns>` injection — port the format.
- EventDetector (Phase 3) already has per-event-type cooldowns. Add global `MIN_INTER_EVENT_GAP_SEC=8.0` cap on top.
- `events.jsonl` already structured — add `slop_suppressed`, `silence_short_circuit`, `coach_scorecard` event types.
</code_context>

<specifics>
## Specific Ideas

1. **Module layout**:
   - `src/vibemix/prompts/__init__.py`
   - `src/vibemix/prompts/matrix.py` — `build_system_instruction(skill, mode) -> str`; cells stored as 6 module-level constants
   - `src/vibemix/prompts/negative_dict.py` — `NEGATIVE_PHRASES: tuple[str, ...]` + `NEGATIVE_REGEX` compiled
   - `src/vibemix/prompts/filter.py` — `filter_for_slop(text) -> tuple[str, list[str]]` returns (filtered_text_or_<silence/>, list_of_matches)
   - `src/vibemix/prompts/turn_history.py` — `TurnHistory` class (port from POC)
   - `src/vibemix/prompts/scorecard.py` — `summarize_session(events) -> str` returns one of 4 bands
2. **Tests**:
   - `tests/prompts/test_matrix.py` — all 6 cells exist + each contains ≥8 anchor phrases + each contains negative-dict ban list + each contains describe-before-infer + past-tense rules + `<silence/>` instruction
   - `tests/prompts/test_filter.py` — synthetic LLM outputs containing each of the 40 ban phrases get suppressed; clean outputs pass through unchanged
   - `tests/prompts/test_turn_history.py` — push/pull/ring overflow at N=12; `as_text` format matches POC
   - `tests/prompts/test_scorecard.py` — band classification by event counts
3. **Wiring tests** in `tests/agent/`:
   - `test_dj_cohost_picks_matrix_cell.py` — env var dispatch
   - `test_dj_cohost_silence_short_circuit.py` — mock LLM stream returning `<silence/>` → no TTS call
4. **CONTEXT thread**: `<recent_turns>` block injected into the cascade prompt by `dj_cohost.py:llm_node` before the audio Part — append to the system_instruction or include as a system message.

</specifics>

<deferred>
## Deferred Ideas

- **Real A/B testing** of prompt cells against recorded sets — Phase 16 + 17.
- **Multi-language prompts** — out of v1 (English only).
- **UI for picking skill/mode** — Phase 11/12 (Settings panel surfaces env-var-equivalent toggles).
- **Per-genre prompt variants** — Phase 6 already feeds genre into evidence packets; no per-genre prompt cells needed (the genre context is data, not a different persona).
- **Dynamic prompt rewriting** based on user feedback — out of v1.
</deferred>
