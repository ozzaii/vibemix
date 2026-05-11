# Prompt Templates — Reference

vibemix's reactions are driven by a 6-cell prompt matrix: 3 skill levels × 2 modes. The matrix lives in `src/vibemix/prompts/matrix.py` and is dispatched by `build_system_instruction(skill, mode)`. The agent reads two env vars to pick the cell at startup.

## Picking a Cell

```bash
export VIBEMIX_SKILL_LEVEL=intermediate   # beginner | intermediate | pro
export VIBEMIX_MODE=hype                  # hype | coach
```

Defaults (matching v4): `intermediate` + `hype`.

## The 6 Cells

| Cell | Who it's for | Anchor phrases (samples) |
|---|---|---|
| **HYPE_BEGINNER** | New DJs, casual listeners, party energy | "yo that drop", "this groove is sick", "vibe check", "you're cooking", "feeling this energy" |
| **HYPE_INTERMEDIATE** | Default — friend in the booth (v4-port byte-identical) | "that switch was clean", "real producer move", "the room is moving", "sit with it" |
| **HYPE_PRO** | Working DJs, peer-level | "that EQ swap landed", "phrase locked", "low-mid pile-up", "32 cleared", "build-release timing" |
| **COACH_BEGINNER** | Learning DJs — encouraging + 1 specific nudge | "the cut felt early — try 8 bars later", "low boost muddied the breakdown", "give the build more space" |
| **COACH_INTERMEDIATE** | Practicing DJs — concrete technical critique | "kicks stepped on each other for a half-bar", "EQ killed the lows too aggressively", "build released on the 3 — try the 1" |
| **COACH_PRO** | Working DJs — peer critique, no hand-holding | "phrase ended on the 3", "high-mid pileup at 0:42", "blend overstayed by 16", "transient stack on the kick" |

`HYPE_INTERMEDIATE` is byte-identical to the Phase 4 v4 port — preserves exact semantics for backward compat.

## Anti-Slop Stack (3 layers)

vibemix's Core Value: **"Real DJ friend in your ear, no AI slop."** Three enforcement layers prevent generic AI output:

### 1. Prompt-level bans

Each cell explicitly enumerates ~40 banned phrases the model must never use:

- **Generic AI tells** — "as an AI", "I don't have", "I'm here to help", "let me know", "feel free", "happy to assist", "delve", "leverage", "synergy", "robust", "seamless", "comprehensive", "elevate", "unleash", "tapestry"
- **Empty hype** — "amazing", "awesome", "incredible", "fantastic", "great mix", "wonderful", "superb", "outstanding", "impressive", "love it", "killing it", "nailed it"
- **Slop framings** — "in this dynamic world", "at the intersection of", "navigate the landscape", "unlock the potential"

### 2. Post-hoc filter

`vibemix.prompts.filter.filter_for_slop(text)` runs on every LLM output before it reaches TTS. If any banned phrase is detected (case-insensitive, word-boundary match), the entire turn is suppressed (returns `<silence/>`) and a `slop_suppressed` event is logged to `events.jsonl` with the matched phrases.

### 3. Tests

Every cell has a golden test verifying it contains the ban list. The filter has its own test suite with synthetic LLM outputs containing each of the 40 banned phrases.

## TurnHistory

Last 12 model utterances are kept in an in-memory ring (`vibemix.prompts.turn_history.TurnHistory`, capacity = 12). The history is injected into every prompt as a `<recent_turns>` block:

```
<recent_turns>
<user>...</user>
<model>...</model>
<user>...</user>
<model>...</model>
...
</recent_turns>
```

This kills opener repetition over a session — the model sees what it just said and avoids reusing the same hooks.

## `<silence/>` Short-Circuit

When the model decides nothing's worth saying — silent break, room tone, ambient transition — it emits the literal token `<silence/>` (no other text). The `dj_cohost.py` `llm_node` override checks for this token in the streamed output. If present, the entire turn is suppressed: no TTS, no playback, no audio interrupting the set. Logged to `events.jsonl` as `silence_short_circuit`.

This is the inverse pressure to "always say something". The most important word a DJ friend can say is sometimes nothing.

## Coach Scorecard

At session end, Coach mode summarizes the set with one of 4 qualitative bands:

- `clean` — no slop fired, ≤2 abrupt moves
- `decent` — 2-3 slop suppressions, 3-5 abrupt moves
- `abrupt` — 4-7 slop suppressions or many abrupt moves
- `train-wreck` — 8+ slop suppressions or massive abrupt-move count

**Never numeric.** No "8/10". No "73%". The persona of a DJ friend never reduces a set to a score. Persisted as `coach_scorecard` event in `events.jsonl`.

## Reaction Throttle

Two layers cap how often vibemix talks:

1. **Per-event-type cooldown** (Phase 3) — each event type (TRACK_CHANGE, PHASE, MIX_MOVE, etc.) has its own minimum gap.
2. **Global min-gap cap** (Phase 10) — `MIN_INTER_EVENT_GAP_SEC = 8.0` between any two reactions. Combined with the silence short-circuit, this kills the "voice assistant doing music commentary" feel.

## What's Deferred

- **In-app skill/mode picker** — Phase 12 Settings panel surfaces these as UI toggles.
- **A/B testing of prompt cells** against recorded sets — Phase 16 + Phase 17 hallucination + slop-grading gates.
- **Multi-language prompts** — out of v1 (English only).
- **Per-genre prompt variants** — Phase 6 already feeds genre data into evidence packets; the persona stays constant.
- **Dynamic prompt rewriting from user feedback** — out of v1.
