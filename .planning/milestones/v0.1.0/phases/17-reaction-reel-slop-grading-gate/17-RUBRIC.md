# Phase 17 — Reaction-Reel Grading Rubric

**Status:** Locked spec — referenced verbatim by `scripts/reaction_reel/grade.py` (Plan 17-02) and `scripts/reaction_reel/analyze.py` (Plan 17-03).
**Source-of-truth for:** VERIFY-02.
**Audience:** the four blind raters (kaan, francesco, dj1, dj2).

---

## 1. Purpose & Gate Semantics

This rubric governs the Phase 17 reaction-reel slop grading gate per **VERIFY-02**: "Hand-graded reaction reel — 30 min varied DJing, blind-rated 1-5 by Kaan + Francesco + 2 DJ network friends; pass requires ≥4.0 average with zero 1-2 ratings." It exists because vibemix's central product claim — "real DJ friend in your ear, not AI slop doing music commentary" — is a taste call, not a metric. The gate operationalises taste: four DJs score every reaction blind on a 1-5 scale, the scores aggregate, and the result is a binary pass/fail before release.

Pass requires **average ≥ 4.0** across all (reactions × raters) AND **zero 1-2 ratings** from any rater on any reaction. Both conditions must hold. A 4.3 average with a single 2 fails. A 3.95 average with no 1s or 2s also fails. The two conditions are not negotiable — they come from ROADMAP Phase 17 Success Criterion #3 verbatim:

> "Average rating ≥4.0 with zero 1-2 ratings across all reactions; if gate fails, Phase 10 (prompt-engineering) re-enters with iteration budget (up to 3 cycles) before considering scope-cut to Hype-man-only."

If the gate fails, the loop documented in `17-ITERATION-LOOP.md` governs what happens next. This document only defines the scoring.

---

## 2. The 1-5 Scale

Each reaction (one `kind=="ai_text"` utterance from the AI, with its ±15s audio + screen + MIDI context) gets exactly one integer score in `{1, 2, 3, 4, 5}` per rater. You evaluate the reaction against five anchors. Pick the highest score the reaction clearly clears — if it almost makes 4 but stumbles on personality, that is a 3, not a generous 4.

### Score 5 — "Real friend in my ear"

The reaction is timely (lands within the window where the event still matters, typically <2s from the cue), grounded in audible or visible evidence (the AI is reacting to something the rater can identify in the music or on screen), doesn't repeat anything the AI said in the prior 30s, sits cleanly inside its persona (Hype-man pushes, Coach observes — neither breaks character), and would survive a clip on Kaan's IG story without making him cringe. A 5 is rare. A reel of all 5s would mean Plan 17 over-engineered the gate.

Concrete examples (illustrative — vibemix may not actually say these, but if it did, they would land):

- Hype-man, techno drop: *"Okay there it goes — that low end is doing exactly what you wanted."* — short, grounded in the drop the rater can hear, fits the hype persona, IG-clip-worthy.
- Coach, house mid-mix: *"You stayed in the EQ a beat too long there — try cutting lows half a bar earlier next time."* — observation tied to an audible mix move, specific timing critique, no generic phrasing.

### Score 4 — "Solid"

The reaction is grounded and mostly timely, has no slop tokens, fits the persona — but something slightly off. Phrasing is a touch generic, or the timing is 2-3s late, or the personality wobbles for a beat. A DJ hearing this in headphones would not object, would not tear them off, but also would not save the clip. The majority of well-tuned reactions live here; this is the floor that makes the gate pass.

Examples:

- Hype-man, techno drop: *"Yeah, that's the moment right there."* — grounded, timely, but generic enough that it could fit any drop in any genre. Solid, not memorable.
- Coach, drum & bass: *"Nice cut — the breakdown lands clean."* — true observation, slightly late by ~2s, no slop, but doesn't push the rater to action like a 5 would.

### Score 3 — "Neutral"

Correct but forgettable. The AI did not hallucinate, did not repeat itself, did not use slop language — but the reaction is the "voice assistant doing music commentary" failure mode. It is technically defensible but adds nothing to the DJ's awareness or vibe. A 3 is *not* failure on its own (no single 3 fails the gate), but a reel full of 3s drags the average below 4.0 and the gate fails on the math. If you find yourself scoring most reactions as 3, the prompt templates need work — flag it in `comment`.

Examples:

- Hype-man, pop transition: *"Nice transition into the next track."* — true, neutral, has no opinion or texture.
- Coach, disco verse: *"The bassline is steady here."* — observation without insight; the rater already knew that.

### Score 2 — "Slop"

The reaction trips at least one of the failure modes: generic AI phrasing pulled from the anti-slop dictionary, late by more than 4 seconds, repeats something the AI said in the prior 30s, hallucinates an event that did not happen (claims a drop on a non-drop, says "the crowd is going crazy" when there is no crowd context), or fakes hype on a transition that was musically a non-event. **A single 2 from any rater on any reaction fails the gate.** Apply 2 with intent — if you are 50/50 between 2 and 3, the 3 may be more honest, but if any of the five 2-criteria is unambiguously present, score 2.

Examples (these are deliberately bad — score them 2):

- Hype-man, mid-house: *"Wow, the energy in the room is electric!"* — slop dictionary hit ("Wow"), no context (there is no room, vibemix runs in a bedroom), generic.
- Coach, techno: *"That was a fantastic mix!"* — slop dictionary hit ("fantastic"), empty praise, no observation.
- Either mode, on a non-drop: *"Here comes the drop!"* — hallucinated event.

### Score 1 — "Embarrassing"

Would make the DJ tear off their headphones. Condescending tone, breaks the fourth wall ("As an AI, I can hear..."), shows confusion about basic facts (calls house "techno", names the wrong section, claims to recognise a track that isn't playing), or is cringe in a way no DJ friend would ever produce. **A single 1 fails the gate.** A 1 is a louder failure than a 2 — a 2 is dull or generic; a 1 is actively harmful to the DJ's flow. Apply sparingly; when applied, it should be obvious to anyone listening.

Examples:

- *"As an AI, I'm not sure what's playing but it sounds like a good song!"* — fourth-wall break + admits no grounding + empty praise. 1.
- *"Great energy in this drum & bass track!"* on a house track — factual genre error. 1.
- Hype-man delivering coach-toned advice mid-drop: persona collapse + bad timing → 1.

---

## 3. Per-Reaction Grade Fields (LOCKED Schema)

The 10 fields below are the exact keys written into `recordings/<session>/grades/<rater>.jsonl` — one JSON object per line, one line per reaction graded.

| Field             | JSON Type | Allowed Values                                                          | Description                                                                                       |
|-------------------|-----------|-------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------|
| `reaction_id`     | string    | SHA8 hex (8 chars) of the voice.wav clip filename                       | Anonymised reaction identifier; mapping back to original lives in `grades.key.json` (analyzer only). |
| `score`           | integer   | `1`, `2`, `3`, `4`, `5`                                                 | Your integer score per the anchors in Section 2. No half-scores.                                  |
| `rater`           | string    | `"kaan"`, `"francesco"`, `"dj1"`, `"dj2"`                               | Rater identity; set once at grade.py start, written into every record.                            |
| `grounded`        | bool      | `true` / `false`                                                        | True if the reaction is tied to something audible or visible in the ±15s context.                 |
| `timely`          | bool      | `true` / `false`                                                        | True if the reaction landed within ~2s of the cue it responds to. False if >4s late.              |
| `unique`          | bool      | `true` / `false`                                                        | True if the reaction does not paraphrase anything the AI said in the prior 30s.                   |
| `personality_fit` | bool      | `true` / `false`                                                        | True if the persona (Hype-man vs Coach) fits — hype pushes, coach observes; neither breaks character. |
| `slop_flag`       | string    | `"none"`, `"late"`, `"generic"`, `"hallucination"`, `"repetition"`, `"cringe"` | Primary failure mode; `"none"` for any 3-5 score with no specific failure.                       |
| `comment`         | string    | free text (may be empty for 4-5 with no notes; required for 1-3)        | One-line rater note. Mandatory for any score ≤ 3.                                                 |
| `would_clip`      | bool      | `true` / `false`                                                        | True if you would clip this reaction to Kaan's IG story. Approximate proxy for the 5-anchor.      |

**Implementation pointer:** Plan 17-02's `scripts/reaction_reel/grade.py` writes these fields verbatim into `recordings/<session>/grades/<rater>.jsonl`. Plan 17-03's `scripts/reaction_reel/analyze.py` reads them to produce the pass/fail verdict. The field names in this document are the contract — drift between rubric and tooling is caught by the Plan 17-03 integration test.

---

## 4. `slop_flag` Semantics

You pick the primary failure mode when scoring 1, 2, or 3 (and may pick one for 4 if there is a minor flavor issue). For 5s, always use `"none"`.

- **`none`** — No specific failure mode present. Use for any 3-5 score that simply lacks spark; the reaction is correct, just unremarkable. Always use this for 5s.
- **`late`** — The reaction landed more than ~4 seconds after the cue it responds to. The content may have been correct, but by the time the AI spoke, the DJ had already moved on. Late reactions break the "real friend in your ear" illusion even when grounded.
- **`generic`** — The reaction uses phrasing a real DJ friend would not use. The canonical reference is the Phase 10 anti-slop dictionary at `src/vibemix/prompts/negative_dict.py` — 40 phrases across three buckets (AI tells like *"as an AI"* / *"delve"* / *"leverage"*, empty hype like *"amazing"* / *"awesome"* / *"incredible"*, and slop framings like *"in this dynamic world"* / *"at the intersection of"*). Any of those 40 in a reaction is a likely `generic` flag — do not score by the dictionary alone, but if you hear one of them, the flag fits. Do **not** duplicate the 40 phrases here; the dictionary at `src/vibemix/prompts/negative_dict.py` is the source-of-truth and may evolve in Phase 10.
- **`hallucination`** — The reaction asserts an event that did not happen: "here comes the drop" on a non-drop, "the crowd is loving this" when there is no crowd, "you switched to track X" when no track switch occurred, "the bass just dropped" on a flat section. Hallucinations are the biggest threat to the product's core value — flag them aggressively.
- **`repetition`** — The reaction paraphrases something the AI said in the prior 30s. Different words, same content. The `unique` field captures the binary; this flag captures the failure mode reason.
- **`cringe`** — The reaction is condescending, breaks the fourth wall, claims AI identity, or otherwise crosses into territory no DJ friend would. Often co-occurs with score 1.

---

## 5. Pass Thresholds & Tie-Breaker

**Pass condition (both must hold):**

1. Average score across all (reactions × raters) is **≥ 4.0**.
2. **Zero** ratings of 1 or 2 from any rater on any reaction.

**Tie-breaker:** If the average lands in `[3.95, 4.05]` (i.e. avg == 4.00 ± 0.05) AND any 3-score appears in more than 25% of reactions, escalate to **Kaan** for a "ship vs. one more Phase 10 cycle" decision. The math passes; the texture might not. Kaan looks at the report's per-genre / per-mode breakdown and either approves or pushes a Phase 10 cycle. This is a human override, not a metric.

---

## 6. Rater Instructions

You grade **blind**. The grading CLI strips persona, mode, genre, and skill metadata from the on-screen UI — you hear the voice.wav clip and see the ±15s music + screen + MIDI context. You score one reaction at a time. Always write a one-line `comment` for scores ≤ 3 (the analyzer surfaces these verbatim in the report). For scores 4-5 the comment is optional but appreciated when a reaction stood out.

Use `slop_flag="none"` for any 3-5 score that has no specific failure mode. Do not invent a flag to add texture — `"none"` is the honest answer for a forgettable-but-not-broken reaction.

Reaction order is shuffled deterministically by rater seed, so if you abandon mid-grading and resume tomorrow, you pick up where you left off without re-rating reactions you already scored. Do not consult other raters' grades. Do not let your earlier scores anchor your later scores — score each reaction fresh against the anchors in Section 2.
