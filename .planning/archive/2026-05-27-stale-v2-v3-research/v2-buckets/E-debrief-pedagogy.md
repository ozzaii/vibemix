# Bucket E — Post-Session Debrief + DJ Pedagogy Research

> Research for vibemix v2 post-session debrief feature. Pivot context: Kaan has reframed vibemix as "more tutorial than hype" — coaching is now the primary use case, hype mode is secondary. Live mode is latency- and intrusion-constrained (1-2 sentences max). The **post-session debrief is where actual teaching happens.**

---

## TL;DR (5 bullets)

- **Build ONE deliberate-practice loop, not a dashboard.** Real teaching = identify-cause-correct cycles tied to specific timestamps in the user's recorded set. Everything in this spec serves that loop. Drop the temptation to ship "metrics galore" — Whoop and Strava get away with metrics because users have already bought into self-quantification; DJs have not.
- **Skill ladder, not flat critique.** Beginner / Intermediate / Pro lenses change *what gets flagged*, not just the wording. Beginner = mechanical (beatmatch drift, phrase entry points, mic bleed). Intermediate = phrasing + energy curve + harmonic moves. Pro = micro-craft (filter timing, EQ kills, narrative arc resolution).
- **Grounding via mandatory citations, not better prompts.** Every critique must cite an `events.jsonl` line + an audio timestamp range. If Gemini cannot cite, it cannot critique. This is the single most important anti-hallucination lever and it directly extends the [project_anti_slop_grounded_gemini_thesis] grounding stack into the debrief layer.
- **Output shape: chaptered written review + voiced TL;DR + clickable timeline + 3 drills for next session.** Not voiced playback (too long, not skimmable). Not a dashboard (no narrative). Not a single wall of text (no entry points). Strava-style chapter cards with audio scrub-to-marker beats Synthesia-style per-note scoring for this domain.
- **Long-term DJ profile = structured JSON + 8-12 short prose "tendencies" lines, regenerated each session.** Not a vector DB. Not mem0. The total per-user state fits in <2 KB and gets injected verbatim into the next session's system prompt. Vector retrieval over 30 past sessions is the wrong primitive — DJ tendencies are summarisable in a tweet-sized profile, not searchable.

---

## DJ teaching pedagogy synthesis (what works, sources cited)

**The canonical curriculum order is remarkably consistent across the major schools.** Phil Morse's Digital DJ Tips, Point Blank Music School, Crossfader, and Mixed In Key's books all teach the same five-stage sequence — disagreements are about emphasis, not order:

1. **Mechanical fundamentals** — tempo matching, beatmatching, headphone use, gain staging. Phil Morse explicitly decomposes beatmixing into "tempo matching → beat alignment → phrase matching" ([Digital DJ Tips](https://www.digitaldjtips.com/phil-morse/), [House Ninja review](https://houseninjamusic.com/blog/ddjt-complete-dj-course-review/)).
2. **Phrasing** — 4/4 grid, 8/16/32-bar phrases, mixing in/out on phrase boundaries. Phil's hammer rule: "if you're mixing OUT of a well-known track, mix INTO a well-known track." Crossfader chronologically gates this lesson behind beatmatching ([Crossfader course flow](https://wearecrossfader.co.uk/online-dj-courses)).
3. **Energy curve and set arc** — peak/valley landscape, intentional rises and releases. Mixed In Key teaches it as a sketch-on-paper exercise; Dubspot frames it as "narrative arc" ([Mixed In Key](https://mixedinkey.com/book/control-the-energy-level-of-your-dj-sets/), [Dubspot Building an Arc](https://blog.dubspot.com/building-an-arc-bringing-narrative-structure-to-your-dj-sets), [DJ.Studio Anatomy](https://dj.studio/blog/anatomy-great-dj-mix-structure-energy-flow-transition-logic)). Standard recipe: one main peak ~2/3 of the way through, 1-2 smaller earlier highs, deeper middle, finale with controlled release.
4. **Harmonic mixing** — Camelot Wheel rules (same key, same number ±1, A↔B at same number). Point Blank teaches Camelot to brand-new students because it gives "professional-sounding" mixes quickly; intermediates use it for library planning ([Music City SF](https://musiccitysf.com/accelerator-blog/camelot-wheel-dj-mixing-guide/), [Mixed In Key Harmonic Mixing Guide](https://mixedinkey.com/harmonic-mixing-guide/), [DJ.Studio Camelot guide](https://dj.studio/blog/camelot-wheel)).
5. **Creative / advanced skills** — scratching, FX, drop mixes, idents/drops, harmonic + acapella layering, sonic identity. Point Blank's "Creative DJ Skills" sits explicitly above their "Essential DJ Skills" course ([Point Blank DJ Skills L1](https://www.pointblankmusicschool.com/courses/la/dj-courses/dj-skills-level-1/), [DJ Mag launch coverage](https://djmag.com/news/point-blank-launches-new-beginner-and-advanced-dj-skills-courses)).

**For the digital-DJ-with-controller case specifically** (vibemix's actual users), the curriculum diverges from vinyl in two ways: (a) Camelot becomes mandatory-from-day-one because key data is already in Rekordbox, (b) Rekordbox prep (beatgrids, hot cues, memory cues) is treated as a *teachable phase* preceding live mixing — Point Blank's Essential DJ Skills course opens with Rekordbox management.

**Feedback shape that works** (consistent across Crossfader, Digital DJ Tips, jazz pedagogy research, and education research):
- **Identify → Cause → Correct.** Not "feedback sandwich" — Radical Candor's research and Faculty Focus's pedagogy review both show the sandwich is ineffective. The validated alternative is **SBI (Situation-Behavior-Impact)** or **Ask-Tell-Ask** ([Radical Candor](https://www.radicalcandor.com/blog/feedback-sandwich-praise-criticism), [Faculty Focus](https://www.facultyfocus.com/articles/effective-teaching-strategies/is-the-sandwich-method-getting-stale-fresh-approaches-to-providing-effective-student-feedback/)).
- **Bite-sized, sequential** — Crossfader explicitly chunks lessons into 5-20 minute bites linked chronologically. Long-form crit doesn't stick.
- **"What improved / what still needs work / what to try next"** — Structural Learning's deliberate-practice guide makes this triad the canonical reflection format ([Structural Learning](https://www.structural-learning.com/post/deliberate-practice)).

**Beginner / Intermediate / Pro emphasis shift** (synthesised across sources):
| Level | Critical errors | What we surface | What we ignore |
|---|---|---|---|
| Beginner | Train-wrecks, beatmatch drift >2 BPM, wrong phrase entry, mic bleed, gain clipping | All mechanical errors with exact timestamps + "try this hot cue point instead" | Energy arc subtleties, harmonic finesse — don't overwhelm |
| Intermediate | Phrasing collisions, harmonic clashes, flat energy across 30+ min, predictable transitions | Phrase boundary diagnoses, Camelot violations, energy curve plot | Hyper-fine FX timing critique |
| Pro | Filter timing within bar, EQ kill placement, narrative arc resolution, signature flourish over-use | Micro-craft (eighth-note-level FX timing), set-arc analysis with comparison to canonical arcs | Anything mechanical — assume it's solid |

---

## Evidence-based coaching frameworks applied to DJ coaching

**Anders Ericsson's deliberate practice** ([Sentio summary](https://sentio.org/what-is-deliberate-practice), [Frontiers paper](https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2019.02396/full), [Cambridge handbook chapter](https://www.cambridge.org/core/books/cambridge-handbook-of-expertise-and-expert-performance/differential-influence-of-experience-practice-and-deliberate-practice-on-the-development-of-superior-individual-performance-of-experts/757F5B791A5EAE0C46E738A26B2AAFC1)) gives the operational definition for what vibemix is trying to be:

> "Engagement in highly structured activities created specifically to improve performance through immediate feedback, requiring high concentration, not inherently enjoyable. Rehearsal within the zone of proximal development, ongoing performance assessment, tailored goal-setting, and close mentoring with expert feedback."

Mapping to vibemix:
- **Structured activity** = the DJ set itself, with the AI watching specific failure modes.
- **Immediate feedback** = live mode (1-2 sentence flags). Limited by latency budget.
- **Tailored goal-setting** = drills prescribed per-session-debrief.
- **Close mentoring** = the debrief itself — long-form, multi-turn-evidence, prescriptive.
- **Zone of proximal development** = the user-level dial. A beginner getting pro-level critique is outside their ZPD.

**Reflection-based vs prescriptive coaching** — research on jazz improvisation pedagogy ([Frontiers on improvisation pedagogy](https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2017.00911/full), [Davis 2023 on self-assessment in jazz](https://journals.sagepub.com/doi/10.1177/03057356221135344), [Jazzadvice 36-question audit](https://www.jazzadvice.com/lessons/your-jazz-improvisation-audit-36-questions-that-will-test-your-musical-skills/)) finds that reflective questioning ("how did that transition feel? what were you trying to communicate?") works *in addition to* prescriptive correction, not instead of it. The strongest pedagogical result combines both: a 70/30 prescriptive-to-reflective ratio. The Self-Awareness theme is identified as the meta-theme connecting empathy, self-doubt, transcendence, and prior knowledge.

**Feedback sandwich is dead.** Multiple sources converge ([Radical Candor](https://www.radicalcandor.com/blog/feedback-sandwich-praise-criticism), [BetterUp](https://www.betterup.com/blog/feedback-sandwich), [PMC clinical coaching paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC6354721/)) on three validated alternatives:
- **SBI (Situation-Behavior-Impact)** — "At 23:14 (situation), you mixed in over the breakdown of the outgoing track (behavior), which killed the build that was supposed to release here (impact)."
- **STAR AR (Situation-Task-Action-Result + Alternative)** — adds an explicit "what to try next time."
- **Ask-Tell-Ask** — invite self-reflection first, then teach, then verify uptake.

**vibemix recommendation:** use **SBI for critique + STAR AR for drills**. Skip Ask-Tell-Ask in v1 (requires interactive turn-taking; v2.x stretch). Counter-intuitive but research-backed: open with the *corrective* item, not praise. Studies cited in Faculty Focus + BetterUp find "corrective-positive-positive" beats "positive-corrective-positive" because the corrective lands when attention is highest.

---

## Post-session debrief UX patterns (with comparable products surveyed)

| Product | Debrief pattern | What we steal | What we skip |
|---|---|---|---|
| **Strava** ([Built for Mars case study](https://builtformars.com/case-studies/strava), [JunWei UX](https://medium.com/@wjun8815/ui-ux-case-study-strava-fitness-app-0fc2ff1884ba)) | Chaptered activity card: map, splits, segments, kudos. Each segment is clickable, scrubs to map. | Chaptered review with clickable timeline → audio scrub-to-marker | Social/leaderboard hooks (Bravoh's domain, not vibemix's) |
| **Whoop** ([Everyday Industries UX eval](https://everydayindustries.com/whoop-wearable-health-fitness-user-experience-evaluation/)) | Auto-detected activity + daily journal + monthly performance report. Trust built via auto-detection feeling intelligent. | Auto-everything — user doesn't tag anything; session is fully reconstructed from `events.jsonl` | Monthly aggregate is too slow for DJ learning loop; weekly at most |
| **Duolingo** ([Duolingo home redesign post](https://blog.duolingo.com/new-duolingo-home-screen-design/)) | Streak + next lesson + per-skill XP. End-of-lesson screen = ✓/✗ per question + summary. | "What you nailed / what to drill" two-column visual at the top of the debrief | Streak gamification — gross fit for DJ identity, will read as patronising to a Pro |
| **Synthesia (piano)** ([Synthesia knowledge base](https://tools.aiformusic.org/knowledgebase/articles/synthesia-interactive-midi-based-piano-learning-and-practice-software), [Pianoers review](https://pianoers.com/synthesia-piano-review/)) | Real-time note-accuracy scoring, replay with correct/incorrect note overlay. | The replay-with-overlay concept (audio + event markers) | Per-note scoring isn't a fit — DJing is performative, not "correct/incorrect" |
| **iZotope Neutron Mix Assistant** ([iZotope Assistants overview](https://www.izotope.com/en/learn/meet-the-izotope-assistants), [Neutron 5 docs](https://docs.izotope.com/neutron5/en/assistant.html)) | Analyse → suggest settings → user accepts/tweaks. "Begin Listening" pattern. | The "this is what the AI heard, here's what it recommends" framing — explicit grounding | Settings-output isn't analogous; vibemix outputs critique, not parameters |
| **Sonible smart:EQ / smart:limit** | Same pattern as iZotope, slightly more aggressive auto-application | Same as above | Same as above |

**Time-on-screen budget research** — Strava's typical post-activity card is read in ~30-90 seconds; Whoop's daily Recovery card in ~15 seconds; Duolingo end-of-lesson screen <10 seconds. For a substantive DJ debrief, the budget is **3-5 minutes of attentive reading** if it's chapter-cards-with-scrub. If it's a wall of text or a long voiced piece, users bail by minute 2.

**Linear vs metrics vs question-led** — the Synthesia/Whoop pattern is clear: **linear narrative with embedded metrics + interactive scrub** keeps users coming back. Pure metrics dashboards (think Garmin Connect old-school) have high bounce. Pure question-led reflection (Duolingo's "rate this lesson") doesn't drive learning — it drives PMs' OKRs.

**Verdict for vibemix:** **chaptered narrative** with embedded scrub markers, two structured panels (Wins / Drills), and an optional 60-90s voiced TL;DR at the top for users who'd rather listen than read.

---

## AI-specific grounding strategy (hallucination prevention)

The thesis from [project_anti_slop_grounded_gemini_thesis] applies verbatim: hallucination is solved by data, not by better prompting. The debrief layer extends this with explicit citation discipline.

**Mandatory citation pattern** (drawn from [Chain-of-Verification paper](https://aclanthology.org/2024.findings-acl.212.pdf), [arXiv citation-grounded code paper](https://arxiv.org/html/2512.12117v1), and Mitigating Hallucination survey [arXiv 2510.24476](https://arxiv.org/html/2510.24476v1)):

Every critical claim in the debrief MUST be one of:
- **Event-cited** — references a specific line in `events.jsonl` with timestamp `t` and `kind` (e.g., `[ev: t=423.1 TRACK_CHANGE]`).
- **Audio-cited** — references a specific time range in `input.wav` (e.g., `[aud: 07:03-07:18]`) that the user can click to scrub to.
- **MIDI-cited** — references a controller move (e.g., `[midi: t=412.7 deckA filter cc=23 val=98]`).
- **Track-cited** — references the now-playing log (e.g., `[track: "Boys Noize – Mvinline" t=420.0]`).

If Gemini emits an unsourced claim, the post-processor strips that sentence. Hard rule. We enforce this both via prompt and via a regex-based output linter that scans Gemini's response for sentences lacking a citation tag and either drops them or re-prompts with "the following sentence was unsourced, either cite or remove."

**Chain-of-Verification** (CoVe — [ACL 2024 paper](https://aclanthology.org/2024.findings-acl.212.pdf)) is overkill for v1 but the right shape for v2.x: have Gemini generate the debrief, then independently verify each claim, then disregard inconsistent claims and regenerate. Worth ~2x the Gemini cost; do it on opt-in "deep debrief" only.

**Lead with what the AI heard** — the iZotope/Neutron pattern. Open the debrief with a 1-paragraph "Here's what I observed in this session" that explicitly shows the user the AI's perception of their set (tracks identified, BPM range, energy profile, controller moves logged). This both grounds the user and gives them a chance to spot mis-identification *before* reading the critique — a transparency move that is itself an anti-slop signal.

---

## Concrete debrief feature spec for vibemix

> **One feature. One Gemini call per session. One screen. Three drills.**

### Input data

Per session (already captured by `VoiceRecorder` in `cohost_v4.py` lines 779-859):
- `input.wav` — master output, 16 kHz mono int16 (Gemini-ready)
- `voice.wav` — AI reactions, 24 kHz mono
- `events.jsonl` — append-only log with these `kind` values observed in v4:
  - `session_start` (with `wall_clock_iso`)
  - `event` (typed: `TRACK_CHANGE`, `PHASE`, `LAYER_ARRIVAL`, `MIX_MOVE`, `HEARTBEAT`, `KAAN_SPOKE`, `MANUAL`) — with `audible`, `deck`, `track`, `track_conf`, `phase`
  - `llm_invoke` — every Gemini call (event, audible, deck, track, phase, audio bytes, has_screen, prompt, invoke_dir)
  - `ai_text` — what the AI said back (text, latency_s)
  - `session_error` / `turn_error`

Plus (already available in `cohost_v4.py` runtime, must be persisted to a `session_summary.json` at session end):
- now-playing log (chronological `(t, track_title, deck)` from `TrackInfo` polling)
- MIDI move log from `ControllerState` (the existing 12s ring widened to full-session retention)
- v2 additions: Rekordbox priors per track if available (key, BPM, beatgrid, hot/memory cues — from pyrekordbox, [project_v2_open_candidates])

**Session summary payload to Gemini** (~30-60 KB text + WAV bytes):
```json
{
  "session_id": "20260513-2104",
  "duration_seconds": 4823,
  "user_level": "intermediate",
  "tracks_played": [{"t_start": 0, "t_end": 412, "title": "...", "key": "8A", "bpm": 128}, ...],
  "events": [<events.jsonl rows>],
  "midi_moves": [<significant moves only — significance filter from cohost_v4>],
  "ai_reactions": [<ai_text rows with timestamps>],
  "user_profile_priors": "<long-term profile, see next section>",
  "energy_proxy": [<RMS samples every 5s>]
}
```

### Gemini prompt template + grounding citations

```
You are vibemix's post-session DJ coach. You are reviewing a recorded DJ set.

USER LEVEL: {beginner | intermediate | pro}
USER LONG-TERM PROFILE (from past sessions): {profile_blob}

EVIDENCE PROVIDED:
1. Full input audio (~80 min, attached as audio Part)
2. Structured event log (below) — every track change, phase, mix move, controller event
3. Track list with key/BPM (from Rekordbox priors if available)
4. AI reactions logged during the session (for context only; do NOT critique the AI)

YOUR JOB:
Write a 4-chapter post-session review. For EVERY critical observation, you MUST cite
evidence using one of these tags:
  [ev: t=<sec> <KIND>]     — event log reference
  [aud: <mm:ss>-<mm:ss>]   — audio range the user can scrub to
  [midi: t=<sec> ...]      — controller move
  [track: "<title>" t=...]

If you cannot cite, you cannot claim. Unsourced sentences will be stripped.

LEVEL CALIBRATION:
- Beginner: flag mechanical errors (beatmatch drift, wrong phrase entry, gain).
  Do NOT critique energy arc or harmonic subtlety unless catastrophic.
- Intermediate: phrasing, harmonic moves (Camelot), energy curve. Skip micro-craft.
- Pro: micro-craft (filter timing within bar, EQ kill placement, narrative arc
  resolution). Assume mechanics are solid.

TONE:
You are a real DJ friend at the studio table after the set. You are honest,
specific, and never preachy. You acknowledge what worked before prescribing
fixes. You do NOT use phrases like "great job!", "you should consider", or
"as an AI". You speak like a peer. Casual contractions OK. Brief curses OK
if the user's locale config allows.

OUTPUT STRUCTURE:
## What I heard
1 paragraph. What tracks, what energy profile, what arc shape, what the
user appeared to be going for. This is the grounding paragraph.

## What worked (2-4 bullets, each with citation)
Specific moments where the choice was strong. Use SBI: situation, behavior, impact.

## What to drill (2-4 bullets, each with citation)
SBI + alternative action. Open with the highest-leverage corrective.

## 3 drills for next session
Structured drills, see DRILL FORMAT below.

DRILL FORMAT (each drill):
- title: <≤8 words>
- why: <1 sentence tied to a specific moment in THIS session>
- how: <3-5 concrete bullet steps the user does next session>
- success: <how the user knows they nailed it>

Final paragraph: optional reflective prompt (1 question).
```

### Output UX

**Single page, scroll-friendly.** Three regions:

```
┌─────────────────────────────────────────────────────────────┐
│ [Voiced TL;DR — 60-90 sec, optional play button]           │  ← top
│  "Solid set. Two things worth tightening: the 23-min       │
│   filter sweep and the mid-set energy dip."                 │
├─────────────────────────────────────────────────────────────┤
│ TIMELINE STRIP — clickable, color-coded by phase           │  ← anchor
│ [intro][build][peak1][valley][peak2][outro]                 │
│   ↑ markers for each chapter's cited moments                │
├─────────────────────────────────────────────────────────────┤
│ ## What I heard       (grounding paragraph)                 │
│ ## What worked        (2-4 cards, each with [aud: ▶ scrub])│
│ ## What to drill      (2-4 cards, each with [aud: ▶ scrub])│
│ ## 3 drills for next session                                │
│   [drill card 1] [drill card 2] [drill card 3]              │
│ ## One thing to chew on (reflective prompt)                 │
└─────────────────────────────────────────────────────────────┘
```

Click any `[aud: 23:14-23:30]` tag → audio scrubs to that range, plays inline. The timeline strip across the top is the navigation primitive — click a marker, jump to the chapter. This is the Strava chaptered-card pattern, adapted to a 1-hour audio asset instead of a 30-min ride.

**Voiced TL;DR is optional, off by default for Pros, on by default for Beginners.** Generated by Gemini TTS using the same OpenRouter-primary chain in v4. Beginners get it because they're more likely to skim text; Pros tend to prefer to read.

**Why not full voiced playback?** Long-form voiced feedback has no skim affordance, can't be scrolled back through, and feels worse than reading once it crosses 90 seconds. The Whoop / Strava data converges: people skim debriefs visually first, then dive deeper into ~1 section. Voiced is for the 60-90s summary, not the body.

### Drills-to-do format

3 drills max per session. More than 3 = none get done (research consensus across [Curious Lion deliberate practice guide](https://curiouslionlearning.com/deliberate-practice/) and [The Geeky Leader](https://thegeekyleader.com/2024/04/07/deliberate-practice-explained-how-focused-training-transforms-skill-acquisition/) — more drills, less stickiness).

Each drill is a card:
```
┌──────────────────────────────────────────────┐
│ 🎯 Drill the 32-bar wait                     │
│                                              │
│ WHY                                          │
│ At 23:14 you mixed in 8 bars early and       │
│ collided with the outgoing track's bridge.   │
│ [aud: ▶ 23:00-23:30]                         │
│                                              │
│ HOW                                          │
│ • Pick 2 tracks from your library now        │
│ • For each, mark the 32-bar phrase boundary  │
│ • Next session: hold the mix-in until the    │
│   next phrase boundary, even when it feels   │
│   late                                       │
│                                              │
│ SUCCESS                                      │
│ Three clean phrase-boundary mix-ins in a row │
│                                              │
│ [Pin to next session →]                      │
└──────────────────────────────────────────────┘
```

The "Pin to next session" CTA adds the drill to the next session's *live-mode* prompt context — so when the user plays again tomorrow, the live mode AI knows to listen for this specific behaviour and flag it in real time. This is the **deliberate-practice loop closing**: long-form critique → short-form drill → live-mode reinforcement → next debrief verifies progress.

### Link back to library intelligence (Bucket F)

When a drill mentions a specific track-craft issue (harmonic clash, energy drop, BPM jump), the drill card includes a **"3 tracks from your library that fix this"** strip below SUCCESS. Implementation:
- Issue: harmonic clash at 8A → 5A
- Use Gemini Embedding 2 over the library, filter by Camelot-compatible (same number, ±1, or A/B sibling)
- Surface 3 tracks the user hasn't played in the last 5 sessions

This is the bucket-bridge: debrief diagnoses the issue, library intelligence proposes the fix. The cross-bucket arrow that makes both features feel substantially better than either alone.

---

## Long-term DJ profile architecture

**Reject mem0 / motorhead / vector DB for this purpose.** Research surfaced mem0 ([mem0 GitHub](https://github.com/mem0ai/mem0), [mem0 production-ready paper](https://arxiv.org/html/2504.19413v1), [Data Camp tutorial](https://www.datacamp.com/tutorial/mem0-tutorial)) as the best-in-class personal-AI memory layer — Qdrant/Chroma/FAISS backends, Gemini-compatible, can run fully local. **But it solves the wrong problem.**

Why mem0 is wrong here:
- mem0 is built for *conversational* memory — chat-style retrievable factoids about a user. DJ tendencies are not retrievable factoids; they're summarisable invariants.
- Retrieval-augmented memory shines when the corpus is too big to fit in context. A DJ's tendency profile fits in 2 KB — there is no retrieval problem to solve.
- mem0 adds an install dependency (Qdrant or similar vector DB) which violates [project_one_click_install_hard_req] — every dep choice rated green/yellow/red, and a vector DB is yellow/red.
- mem0's value (semantic similarity retrieval over many conversations) is exactly what Gemini Embedding 2 already does for the library use case (Bucket F). Bringing in mem0 for a 2 KB profile is overkill.

**Recommended profile architecture:**

A single per-user `~/Library/Application Support/vibemix/profile.json` (and Windows equivalent) shaped like:

```json
{
  "user_id": "kaan",
  "level": "intermediate",
  "sessions_logged": 27,
  "last_session": "20260513-2104",
  "tendencies": [
    "Energy curve flatlines between 30-45 min — needs a midset reset move",
    "Favours 128-132 BPM tech-house; rarely ventures outside ±4 BPM",
    "Filter sweeps tend to last too long (avg 8.4 bars; pros sit at 4-6)",
    "Strong on phrase boundaries when warming up, drifts late peak-time",
    "Camelot moves are mostly +1/-1 — almost never uses A↔B sibling",
    "Mic talk is sparse (good); when it happens it's clean (good)",
    "Recent improvement: tighter beat-matching since session 22",
    "Recurring issue: layering 3+ stems for 90+ sec when 1-deck shifts could carry"
  ],
  "active_drills": [
    {"id": "phrase-32bar-wait", "pinned_at": "20260513", "progress": "in_progress"}
  ],
  "preferred_genres": ["tech house", "minimal", "deep house"],
  "preferred_bpm_window": [126, 132]
}
```

Generation: at debrief end, Gemini gets the previous profile + this session's diagnoses and emits an updated profile. The `tendencies` list is capped at ~10 entries; old entries get superseded if the new session contradicts them. This is **structured summarisation, not retrieval**.

Injection into next live session: the entire `tendencies` list + `active_drills` is concatenated into the live-mode system prompt verbatim. ~600-800 tokens. Free.

When the user reaches ~30+ sessions, optionally surface a "Tendencies over time" timeline view — but that's v2.x stretch.

---

## Tone + voice calibration

**Kaan rejected AI slop emphatically.** The grounded-Gemini thesis applies, but tone has a second axis: persona register.

Borrowing from [Pinnacle's AI coaching writeup](https://www.heypinnacle.com/blog/how-does-ai-coaching-improve-difficult-feedback-conversations) and [Culture Amp's AI coach science page](https://support.cultureamp.com/en/articles/11718591-the-science-behind-ai-coach):

- **Context-aware empathy over therapeutic default.** Don't open critiques with "I hear that you..." Don't ever validate before correcting. Real DJ friends don't.
- **Specificity is the anti-slop.** Generic praise reads as patronising. "That filter sweep at 12:43 was sharp" is fine. "Great energy management!" is not.
- **No second-person preaching.** "You should consider..." is dead. "Try X next session" is alive.
- **No AI-self-reference.** Never "as an AI", never "in my opinion as a model", never "based on the data provided". The AI is a peer at the table, not a service.
- **Locale-aware register.** If the user opts in, casual contractions, mild profanity, in-scene slang ("you smashed the 32-bar wait", "the build ate it"). Off by default. Opt-in setting in v1.
- **Honesty bias.** When the set was mid, say it was mid. When it was a banger, say so but with citation. Validation without evidence reads as slop; honest critique with evidence reads as trust.

**Per-level tone shift:**
- Beginner — slightly more encouraging, more mechanical-explainer, more "here's why this matters." Never condescending; never simplified to the point of insult.
- Intermediate — peer register, balanced critique/praise, assumes vocabulary.
- Pro — terse, technical, sometimes blunt. Assumes everything except the specific micro-craft issue.

---

## Risk + watchouts

1. **Long-Gemini-call cost.** A full debrief with 80 min of audio + structured evidence + screen JPEG snapshots is ~150-300K input tokens depending on audio encoding. At Gemini 2.5 Flash pricing this is ~$0.05-0.15 per debrief. Within the 50 €/mo budget for ~300-500 debriefs/mo. **Mitigation:** downsample input.wav to 16 kHz mono before Gemini call (already the case). Don't attach screen captures retroactively — they're only useful in live mode.
2. **Citation linter false positives.** A regex that strips unsourced sentences will occasionally strip valid context-setting sentences ("This was your second session of the week"). **Mitigation:** allow-list a small set of grounding paragraph patterns; only enforce citation in the "What worked" / "What to drill" sections.
3. **User-level mis-calibration.** A Beginner getting Pro-level critique drowns; a Pro getting Beginner-level critique tunes out. **Mitigation:** the level dial is in onboarding + always visible in settings; users can change it. Optionally auto-suggest level upgrades after 10+ clean sessions at a given level.
4. **Voiced TL;DR over-promise.** A bad 60s voiced TL;DR is worse than no voiced TL;DR. **Mitigation:** ship text-only first, add voiced TL;DR after Kaan's ear-test gate passes ([project_phase_16_kaan_dj_testing]).
5. **Drill staleness.** Pinned drills that never get verified become noise. **Mitigation:** after 3 sessions with no detection of progress on a drill, the next debrief explicitly asks "still working on this?" and offers to retire it.
6. **Profile drift.** Tendencies that contradict each other accumulate over 20+ sessions. **Mitigation:** Gemini regenerates the full profile each session from prior + new evidence; it's not a diff/append log. ~10-entry cap forces honest pruning.
7. **Privacy of session recordings.** All recordings live locally in `~/recordings/<session_id>/`. Debrief Gemini call sends audio to Google. **Mitigation:** explicit consent screen at first debrief; opt-out = no debrief feature (degrade gracefully).
8. **Hallucinated tracks.** Gemini may "hear" a track that isn't there. **Mitigation:** track citations MUST come from the now-playing log; Gemini cannot identify tracks ex-nihilo. Enforce in the prompt + linter.

---

## Open questions for Kaan (3-5 max)

1. **Voiced TL;DR — on by default for Beginners?** Default On reads as helpful; default Off reads as respect for attention. Pro is clearly Off; Intermediate is ambiguous. Pick one.
2. **Drill cap of 3 — hard cap or soft cap?** Hard cap is sticky-research-backed. Soft cap (e.g., "3-5") gives Gemini room to be honest when the set had many issues. Lean hard cap; flag your call.
3. **Profile-injection volume.** 8-10 tendencies = ~600 tokens added to every live session system prompt. Acceptable, but at 30+ sessions logged we might want a tighter cap (5-6 tendencies) to avoid live-mode prompt bloat. OK to cap at 8?
4. **Auto-trigger debrief?** Should the debrief generate automatically at session end (background Gemini call → notification when ready), or on user click? Auto = lower friction but spends Gemini budget on sessions users don't care to review. Lean: auto-trigger only if session > 15 min.
5. **Cross-session memory crossover with Bravoh.** A DJ profile is incredibly valuable for the Bravoh artist OS. Is there a future where the vibemix profile *exports* to Bravoh? If yes, the JSON schema needs to be designed with that in mind from day one. If no, keep it local-only forever. Worth a decision before locking the format.

---

## Sources

- [Phil Morse — Digital DJ Tips](https://www.digitaldjtips.com/phil-morse/)
- [Digital DJ Tips Complete Course review (House Ninja)](https://houseninjamusic.com/blog/ddjt-complete-dj-course-review/)
- [Point Blank DJ Skills Level 1](https://www.pointblankmusicschool.com/courses/la/dj-courses/dj-skills-level-1/)
- [Point Blank launches new DJ skills courses (DJ Mag)](https://djmag.com/news/point-blank-launches-new-beginner-and-advanced-dj-skills-courses)
- [Crossfader online DJ courses](https://wearecrossfader.co.uk/online-dj-courses)
- [Crossfader review (DJingPro)](https://djingpro.com/crossfader-dj-course-review/)
- [DJ.Studio — Anatomy of a great DJ mix](https://dj.studio/blog/anatomy-great-dj-mix-structure-energy-flow-transition-logic)
- [Dubspot — Building an Arc](https://blog.dubspot.com/building-an-arc-bringing-narrative-structure-to-your-dj-sets)
- [Mixed In Key — Control the energy level](https://mixedinkey.com/book/control-the-energy-level-of-your-dj-sets/)
- [Mixed In Key Harmonic Mixing Guide](https://mixedinkey.com/harmonic-mixing-guide/)
- [DJ.Studio Camelot Wheel guide](https://dj.studio/blog/camelot-wheel)
- [Music City SF — Camelot Wheel curriculum](https://musiccitysf.com/accelerator-blog/camelot-wheel-dj-mixing-guide/)
- [Ericsson deliberate practice — Sentio](https://sentio.org/what-is-deliberate-practice)
- [Frontiers — Deliberate practice original definition](https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2019.02396/full)
- [Cambridge handbook chapter — Deliberate practice](https://www.cambridge.org/core/books/cambridge-handbook-of-expertise-and-expert-performance/differential-influence-of-experience-practice-and-deliberate-practice-on-the-development-of-superior-individual-performance-of-experts/757F5B791A5EAE0C46E738A26B2AAFC1)
- [Radical Candor — Feedback sandwich is ineffective](https://www.radicalcandor.com/blog/feedback-sandwich-praise-criticism)
- [BetterUp — Feedback sandwich pros/cons](https://www.betterup.com/blog/feedback-sandwich)
- [Faculty Focus — Beyond the sandwich](https://www.facultyfocus.com/articles/effective-teaching-strategies/is-the-sandwich-method-getting-stale-fresh-approaches-to-providing-effective-student-feedback/)
- [PMC — Clinical coaching beyond the sandwich](https://pmc.ncbi.nlm.nih.gov/articles/PMC6354721/)
- [Jazz improvisation self-assessment (Davis 2023)](https://journals.sagepub.com/doi/10.1177/03057356221135344)
- [Frontiers — Teaching improvisation through processes](https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2017.00911/full)
- [Jazzadvice — 36-question improvisation audit](https://www.jazzadvice.com/lessons/your-jazz-improvisation-audit-36-questions-that-will-test-your-musical-skills/)
- [Structural Learning — Deliberate Practice guide](https://www.structural-learning.com/post/deliberate-practice)
- [Curious Lion — Deliberate practice 5 steps](https://curiouslionlearning.com/deliberate-practice/)
- [Built for Mars — Strava UX case study](https://builtformars.com/case-studies/strava)
- [Strava UI/UX Case Study (JunWei)](https://medium.com/@wjun8815/ui-ux-case-study-strava-fitness-app-0fc2ff1884ba)
- [Everyday Industries — Whoop UX eval](https://everydayindustries.com/whoop-wearable-health-fitness-user-experience-evaluation/)
- [Duolingo home screen redesign](https://blog.duolingo.com/new-duolingo-home-screen-design/)
- [Synthesia knowledge base (AIforMusic)](https://tools.aiformusic.org/knowledgebase/articles/synthesia-interactive-midi-based-piano-learning-and-practice-software)
- [Pianoers — Synthesia review](https://pianoers.com/synthesia-piano-review/)
- [iZotope Assistants overview](https://www.izotope.com/en/learn/meet-the-izotope-assistants)
- [iZotope Neutron 5 docs — Assistant](https://docs.izotope.com/neutron5/en/assistant.html)
- [Mitigating Hallucination in LLMs survey (arXiv 2510.24476)](https://arxiv.org/html/2510.24476v1)
- [Citation-grounded code comprehension (arXiv 2512.12117)](https://arxiv.org/html/2512.12117v1)
- [Chain-of-Verification reduces hallucination (ACL 2024)](https://aclanthology.org/2024.findings-acl.212.pdf)
- [mem0 GitHub](https://github.com/mem0ai/mem0)
- [mem0 production-ready (arXiv 2504.19413)](https://arxiv.org/html/2504.19413v1)
- [mem0 tutorial (DataCamp)](https://www.datacamp.com/tutorial/mem0-tutorial)
- [Pinnacle — AI coaching difficult conversations](https://www.heypinnacle.com/blog/how-does-ai-coaching-improve-difficult-feedback-conversations)
- [Culture Amp — Science behind AI Coach](https://support.cultureamp.com/en/articles/11718591-the-science-behind-ai-coach)
