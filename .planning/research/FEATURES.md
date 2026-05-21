<!-- refreshed: 2026-05-21 for milestone v5.0 "The Useful Cut" (supersedes v3.1 distribution-pass research) -->
# Feature Research — v5.0 "The Useful Cut"

**Domain:** Live AI DJ co-host — full-deck awareness, harmonic/transition coaching, actionable feedback persona, floating-pill live UI
**Researched:** 2026-05-21
**Confidence:** HIGH on harmonic theory + transition mechanics (multiple DJ-authoritative sources agree); MEDIUM on pill-UX specifics (reference-app behavior inferred from product pages + clones, not source); HIGH on grounding/anti-slop ties (internal source-of-truth)

---

## Framing: everything answers "what hallucination class does it close?"

vibemix's central thesis (`project_anti_slop_grounded_gemini_thesis`): a feature is only worth building if it is **tied to a real observed event** and survives the EvidenceRegistry citation linter. v5.0's three features each map cleanly onto that test:

| v5.0 feature | What it grounds on | Hallucination class it closes |
|--------------|--------------------|-------------------------------|
| Full deck awareness | both decks' track metadata (key/BPM/title) + audible-deck weights | "AI talks about a transition that isn't happening" / "AI invents the incoming track" |
| Harmonic clash detection | both tracks' **Camelot key** (a hard, checkable fact) | "AI says it sounds harmonic when it clashes" — a *math-checkable* claim, the strongest possible grounding |
| Transition-execution feedback | phrase position + EQ/MIDI moves + dual-deck audio | "AI gives generic mixing advice unrelated to what Kaan just did" |
| Actionable-not-hype persona | the cited event itself | "AI narrates vibes (slop) instead of coaching" |

The harmonic feature is special: a key clash is **deterministically verifiable** (8A→2A *is* a clash, no LLM judgment needed). That makes it the most defensible anti-slop feature in the whole product — the AI can be *proven right or wrong*. Lean into that.

---

## A) HARMONIC MIXING DOMAIN — the theory the tool must encode

### The Camelot wheel (must be encoded as a lookup table, NOT left to the LLM)

24 keys, coded `N{A|B}` where N=1–12 (clock position), A=minor, B=major. The wheel is the circle of fifths relabeled. **Encode the rules deterministically in Python** and feed the *verdict* to the LLM as a cited fact — never ask Gemini to do the key math (it will hallucinate intervals). This is the single most important architectural call in feature A.

#### Compatible moves (from a track at `8A`, as worked example)

| Move | Example | Relationship | Effect | Verdict |
|------|---------|--------------|--------|---------|
| **Same key** | 8A→8A | identical | seamless, can blend indefinitely | PERFECT |
| **+1 / -1 (adjacent same letter)** | 8A→9A / 8A→7A | perfect fifth / perfect fourth, one note differs | smooth, subtle energy shift | COMPATIBLE (the bread-and-butter move) |
| **Relative major/minor (A↔B, same number)** | 8A→8B | relative key, same notes, different tonal centre | mood lift (minor→major brighter) / darken | COMPATIBLE (mood change, not energy) |
| **Diagonal (±1 AND swap letter)** | 8A→9B / 8A→7B | stacks fifth-step + relative swap | changes *both* mood and altitude | COMPATIBLE-ADVANCED |
| **+2 (energy boost, "the best mix")** | 8A→10A | up two semitones | reliable energy lift, safer than +7 | COMPATIBLE-ENERGY |
| **+7 / -5 (one-semitone lift)** | 8A→3A | up exactly one semitone (dominant) | hard energy boost, classic "lift the room" | RISKY-CREATIVE (works but can sound abrupt; MixedInKey prefers +2) |

#### Genuine clashes (flag these)

| Move | Example | Why it clashes |
|------|---------|----------------|
| **2 steps on the wheel** | 8A→6A | shares fewer notes — "noticeable but manageable" only on short blends/breakdowns; on a long overlap it's muddy |
| **3+ steps** | 8A→5A | true key clash — only survives quick-cut, breakdown, FX bridge, or transition track |
| **The "slam"** | 3A→9A | intentional brazen clash — a *creative choice*, not an error. Do NOT flag if executed deliberately on a cut/drop |

#### CRITICAL distinction the tool must get right (and most cheap tools get wrong)

A **one-step Camelot move (8A→9A) is SAFE** (perfect fifth, one note apart) — but a **one-semitone *pitch* clash is the worst sound in DJing** (two tracks a semitone apart playing simultaneously = beating dissonance). These are different things. The +7 move *reaches* a key one semitone higher, which is fine when you *transition* to it; the disaster is two melodic tracks a semitone apart **overlapping**. The tool must reason about **simultaneous overlap of melodic content**, not just the endpoint key.

#### Energy/BPM interplay with key (the part that separates a credible tool from a key-matcher)

- **Key is irrelevant where there's no harmony.** Percussive techno, peak-time tech-house tool tracks, drum-only sections — "it's hard to create a harmonic clash when there's hardly any harmony." A credible tool **suppresses harmonic feedback** when the overlapping content is percussive/atonal (detectable: low spectral tonality, single repeated note, drum-dominant). Flagging a key clash on two kick-and-hat loops is *annoying and wrong* — exactly the slop to avoid.
- **Clash only matters during overlap of *melodic* elements.** Mixing at the **end of a track** (where melody has dropped out) or **during a breakdown** legitimately disguises a clash. The tool must know *where in the arrangement* the blend happens before judging harmony.
- **Energy direction (minor↔major, +2, -2) is a mood/arc statement, not a right/wrong.** A skilled DJ wants the tool to *notice the arc* ("you've gone minor→major, the room just lifted") not *grade* it.
- **Phrase alignment trumps key.** "Even a perfect harmonic match clashes if phrases collide." Harmonic OK + phrase-misaligned = still a bad mix. Feature A and B are coupled.

#### What a skilled DJ finds USEFUL vs ANNOYING (harmonic)

| USEFUL (build these) | ANNOYING/WRONG (avoid these) |
|----------------------|------------------------------|
| "Deck B is 2A, you're in 8A — three steps apart, that'll clash if you let the melodies overlap. Cut on the drop or kill B's mids." | "These tracks aren't in the same key." (no — one-step-adjacent is fine, you'd be wrong) |
| "Both 5A — totally safe to ride a long 32-bar blend here." | Flagging a clash on two percussive tool-tracks with no melody |
| "You jumped 8A→3A — bold semitone lift. Cut it tight, don't let pads overlap." | "Mix in key for better results" (generic, uncited, slop) |
| Silence when the incoming track is atonal/drum-only | Repeating the key on every single transition (nagging) |
| "B's in the relative major — nice, that's the lift into the back half." | Treating a deliberate creative clash as a mistake |

**Confidence: HIGH.** Theory cross-verified across MixedInKey (originators of the Camelot system), DJ.Studio, Mixgraph, Pioneer DJ. The +7=one-semitone and +2=two-semitone-energy-boost facts are consistent across sources.

---

## B) TRANSITION-EXECUTION FEEDBACK — what DJs actually want mid-set

### The mechanics a credible tool must reference

**Phrase structure (the spine of everything).** Dance tracks are built in 4/8/16/32-bar phrases (usually 8 or 16-bar sections). Transitions that **start and end on phrase boundaries** sound natural because the listener's brain is already tracking that structure. The single highest-value transition note is **"you came in off-phrase"** — starting the blend mid-phrase is the most common amateur trainwreck and is *detectable* from beat-grid + where the incoming track was launched.

**Bass swap / EQ trade (the core long-blend technique).** The textbook move: start track B with its **bass killed** on the one of a new phrase, bring up B's mids/highs over 8 bars while dipping A's, then on the next phrase change **swap the bass in one clean move** — cut A's lows, bring in B's. Two full basslines thumping at once = mud. A tool that can say *"both basslines are running — kill one"* is giving the single most useful EQ note in DJing.

**Blend length judgment.**
- **Too long:** riding a 32-bar blend on two tracks that don't share enough harmonic/rhythmic content → it drags and muddies. Long blends *demand* harmonic + phrase alignment.
- **Too short / cut:** fine and often *correct* on a clash, a breakdown, or a high-energy peak. Not an error.
- The tool should judge length **relative to the content**, not impose a fixed ideal.

**Intro/outro & breakdown usage.** Classic safe transition: wait for A's breakdown (pads/vox, little bass), start B's intro 16–32 bars before its drop, kill A right before B drops. A tool that recognizes "you're in A's breakdown, good window to bring B in" is *prescriptive and timely*.

**Filter / echo-out.** Sweeping a high-pass filter on the outgoing track or an echo/reverb tail-out is the standard way to exit a track gracefully or bridge an otherwise-clashing transition. Useful note: "that clash is coming — filter A out or echo the tail instead of a flat blend."

**When NOT to mix harmonically.** Percussive/atonal sections, quick cuts, peak-time energy slams — explicitly the moments to *not* nag about key (ties to A).

### Table stakes vs differentiator (transition notes)

| Tier | Note type | Why |
|------|-----------|-----|
| **Table stakes** | Phrase-alignment ("you came in off-phrase / on-phrase, clean") | #1 amateur error, fully detectable, every DJ-coach mentions it first |
| **Table stakes** | Bass-clash ("two basslines running — swap the lows") | Most audible mistake; detectable from dual-deck low-band energy |
| **Table stakes** | Beatmatch drift ("the beats are drifting apart") | Foundational; on sync-enabled controllers less relevant but still table stakes for manual |
| **Differentiator** | Blend-length judgment tied to content ("this blend's running long for tracks that don't share a key — tighten it") | Requires both decks' analysis; few tools do this |
| **Differentiator** | Prescriptive next-move ("you're in the breakdown — bring B's intro in now") | Timely + prescriptive; the "real DJ friend" payoff |
| **Differentiator** | "Don't mix harmonic here, it's percussive — just cut on the drop" | Anti-slop sophistication; *withholding* the wrong advice is itself a feature |

### What feels like AI slop (transition feedback to avoid)

- Generic textbook recital uncoupled from the moment: "Remember to beatmatch and use EQ." (uncited → must strip)
- Praising a transition that didn't happen / mislabeling a cut as a blend
- Commenting after the transition is over (latency = slop; the existing cooldown/TTFT stack guards this)
- "Nice transition!" with no observed mechanic (this is hype, not coaching — the whole point of C)

**Confidence: HIGH** on mechanics (DJ.Studio, Native Instruments, Mixgraph, SpinStart agree). **MEDIUM** on detectability of each from vibemix's existing signals — see Dependencies.

---

## C) ACTIONABLE-vs-HYPE FEEDBACK — phrasing the coach voice

The pattern from coaching pedagogy (SBI / AID models) maps perfectly onto a grounded DJ co-host, because both demand **observed → specific → prescriptive**:

- **Action/Situation:** name the *observed, cited* event (this is the EvidenceRegistry anchor — built-in grounding)
- **Impact:** what it did to the mix/room
- **Do-differently:** the concrete next move

That structure is *also* the anti-slop contract: if there's no observed event to cite, there's no feedback (strip to ack-bank). Hype mode names an event then *celebrates*; coach mode names the same event then *prescribes*. Same grounding, different verb.

### GOOD actionable lines (observed → prescriptive)

- "Both basslines are running — kill the lows on the outgoing deck." *(observed: dual low-band energy; prescriptive)*
- "You came in half a phrase early — next one, wait for the 1 of the 16." *(observed: launch offset vs phrase grid)*
- "Deck B's 2A against your 8A — three steps off. Cut it on the drop, don't ride the pads." *(observed: both keys; prescriptive)*
- "That blend's been 32 bars and the keys don't sit — tighten it or filter A out." *(observed: blend duration + key distance)*
- "You're in the breakdown — good window, bring B's intro in now." *(observed: phase=breakdown; timely prescription)*
- "Beats are drifting, B's pulling ahead — nudge it back." *(observed: beat-grid divergence)*

### BAD hype/slop lines (retire these)

- "This is fire! 🔥 The energy is unreal right now." *(no observed mechanic, pure narration)*
- "Love where this set is going, you're really in the pocket." *(vibe, uncited)*
- "Beautiful mixing, the crowd is loving it." *(invents the crowd — hallucination)*
- "Deep, hypnotic groove building here." *(the `\bdeeply\s+\w+` blocklist already bans this register)*
- "Nice transition!" *(names nothing — the difference between hype and coaching is the prescription)*

### How to stay grounded while prescriptive

1. **No event, no note.** The note's subject MUST be a registry-cited event (existing contract — extend, don't rebuild).
2. **One observation, one prescription.** Don't stack three notes; pick the highest-value one (the cooldown stack already enforces single-in-flight).
3. **Prescribe in DJ verbs:** kill, swap, cut, filter, wait, ride, tighten, bring in. Never adjective-soup ("vibey", "epic", "deeply").
4. **Pro level = terse + technical; Beginner = name the technique + why.** The level matrix already exists; v5.0 sharpens the *coach* register specifically. Builds on the in-flight `live-tuning-or-brain` English-pro-feedback work — extends it.

**Confidence: HIGH.** Coaching-pedagogy structure (SBI/AID) is well-established; the grounded-prescription mapping aligns directly with vibemix's existing citation contract.

---

## D) FLOATING PILL UX — Super-Whisper-style live surface

Reference apps confirmed: Superwhisper (dictation pill), macOS Dynamic Island clones (NotchNook, Alcove, MediaMate, MacIsland), Raycast floating windows, Loom record pill. The convergent pattern across all of them:

### The states (this is the core spec)

| State | Appearance | Trigger |
|-------|-----------|---------|
| **Idle / dormant** | Small compact pill, low-key, out of the way. Maybe a faint live audio level so you know it's listening. | Default; session running, nothing to say |
| **Listening/active (ambient)** | Pill with a subtle waveform / level meter showing it's hearing the master | Audio present (ties to existing `Levels` bus) |
| **Speaking / emoting** | Pill expands; shows the co-host text + a "speaking" animation (waveform pulse synced to TTS RMS — vibemix already tracks `Levels.update_voice`) | A reaction fires; collapses back to idle after |
| **Expand-on-event** | Pill grows to show the cited note + (optionally) the citation strip / deck context | Reaction with content; auto-collapse after a few seconds |

Dynamic Island's defining behavior: **"stays out of the way until needed, then expands."** That's exactly the co-host's job — invisible until it has a grounded thing to say, expands to say it, collapses. The pill *is* the anti-slop principle made visual: no event → nothing to show.

### Table stakes for a draggable assistant pill

- **Draggable / repositionable anywhere**, position persisted across sessions (Tauri drag capability — note: this is a *known v0.1.0-rc1 carryover bug*, "Tauri capability missing for drag" — must be fixed for v5.0; it's a dependency, not net-new).
- **Always-on-top, frameless, non-activating** (doesn't steal focus from the DJ software).
- **Idle ↔ active states** with a smooth expand/collapse (native-feeling animation; SwiftUI-style spring on the macOS clones — Framer Motion / CSS spring in the Tauri webview).
- **Text + a "speaking" indicator** (waveform pulse from TTS RMS).
- **Dismissable / collapsible** to a minimal dot without quitting the session.
- **Click to expand** (Dynamic Island toggle pattern).

### Differentiators

- **Waveform synced to the actual TTS audio** (vibemix has `Levels.update_voice` already — the pill telegraphs *real* speech, not a fake animation = anti-slop applied to UI).
- **Citation strip inside the expanded pill** — click the note → jump to the debrief timestamp (LAUNCH-02 already built this strip; reuse it in the pill).
- **Deck-context micro-display** when expanded: "8A → 2A" key chips, both deck titles (the new full-deck-awareness data made glanceable).

### Anti-features (deliberately do NOT)

| Don't build | Why | Instead |
|-------------|-----|---------|
| Full chat-window / scrollback in the pill | It's a glance surface, not a console; turns it into a distraction during a set | Last note only; full history lives in the debrief |
| Always-expanded / large persistent panel | Defeats the "out of the way" purpose; competes with the DJ software for screen | Collapse-to-pill by default, expand on event |
| Notch-only (Dynamic Island literal) | Ties to MacBook notch hardware; excludes Windows + external displays | Free-floating draggable pill, position-agnostic |
| Rich 3D character in the pill | That's the mascot's job; pill is the *information* surface | Mascot stays opt-in/secondary (Kaan-approved partial reversal); pill is text+waveform |
| Click-through controls / settings buried in pill | Over-engineering a glance surface | Settings live in the main window; pill is read-only + drag + dismiss |

**Confidence: MEDIUM.** State model and behaviors are consistent across the reference apps' product pages and clones, but exact Superwhisper internals weren't readable (marketing pages only). The pattern is well-converged enough to spec confidently.

---

## Feature Landscape

### Table Stakes (Users Expect These)

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Deterministic Camelot clash detection (lookup table, not LLM) | A "harmonic" DJ tool that gets key math wrong is instantly discredited | LOW (math) / MEDIUM (sourcing both keys) | The verdict is a *cited fact*; never let Gemini compute intervals |
| Phrase-alignment note ("on/off phrase") | #1 amateur error, every coach leads with it | MEDIUM | Needs beat-grid + launch-position vs both decks |
| Bass-clash note ("two basslines — swap lows") | Most audible mistake | MEDIUM | Needs dual-deck low-band energy; today's audible-deck detection is single-stream |
| Suppress harmonic feedback on percussive/atonal content | Flagging clash on drum loops is the canonical slop | MEDIUM | Spectral tonality / single-note detection gate |
| Actionable coach register (observed→prescriptive, DJ verbs) | The whole v5.0 premise; hype-narration fails the quality bar | LOW (prompt) / MEDIUM (level matrix tuning) | Extends `live-tuning-or-brain` pro-feedback work |
| Draggable floating pill, idle/active/speaking states | Convergent expectation for any assistant pill | MEDIUM | Fix the carryover Tauri drag bug first |
| Pill collapses by default, expands on event | "Out of the way until needed" | LOW–MEDIUM | Reuse existing ws_bus signals |

### Differentiators (Competitive Advantage)

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Full-deck awareness powering *prescriptive* transition notes | "Real DJ friend" who sees both decks and tells you the move | HIGH | The flagship; depends on the unresolved deck data-source |
| Provably-correct harmonic verdict (math-checkable anti-slop) | The most defensible non-hallucination claim in the product | LOW once data lands | Marketing-grade: "the AI can be *proven* right about key" |
| Blend-length judgment tied to content | Few tools reason about *whether* the blend should be long | HIGH | Needs both decks + duration tracking |
| Prescriptive timing ("breakdown now — bring B in") | Timely + prescriptive = the payoff moment | MEDIUM | Phase already detected; needs incoming-deck readiness |
| TTS-synced waveform + key chips in the pill | UI telegraphs *real* speech + real deck context | MEDIUM | `Levels.update_voice` + new deck data already flowing |
| Deliberately *withholding* wrong advice (no key nag on percussive) | Sophistication a generic LLM tool never shows | MEDIUM | Anti-slop as a *feature*, not a guardrail |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Auto-suggest the next track to load | "AI should pick my next track" | Out of scope (`feedback_no_scope_creep`); kills the DJ's agency; recommendation ≠ co-host | Comment on what *is* loaded; recommendation defers (v1.1 note in PROJECT) |
| Grade/score every transition 1–10 | Feels "objective" | Turns a friend into a nagging judge; most "errors" are creative choices | Notice arcs, flag genuine clashes, stay prescriptive not evaluative |
| Full chat history in the pill | "I want to scroll back" | Distraction during a live set; bloats the glance surface | Last note in pill; history in debrief |
| Headphone-cue analysis for harmonic preview | "Tell me before I drop it" | Gemini conflates cue with master → wrong reactions (`Out of Scope`, confirmed) | Judge on master overlap only |
| Real-time pitch/key *detection* from audio | "Detect key live, don't rely on metadata" | Live key detection is unreliable & heavy; would invite false-confident clash claims (anti-slop violation) | Use deck metadata (the data-source question); `unknown` honestly when absent |
| Notch-locked Dynamic Island | "Looks like iOS" | Excludes Windows + external displays + non-notch Macs | Free-floating draggable pill |
| Nagging on every transition | "Be engaged" | Over-talking is its own slop; breaks flow | Cooldown stack + highest-value-note-only |

---

## Feature Dependencies

```
Full deck awareness (DECK DATA SOURCE — unresolved, research-gated)
    └──requires──> a reliable per-deck key + BPM + title source
                       (pyrekordbox / library files / screen OCR / dual-deck audio / nowplaying)
    │
    ├──enables──> Harmonic clash detection (Camelot lookup) ── needs both decks' KEY
    ├──enables──> Transition-execution feedback ── needs both decks + phrase grid + dual-deck low-band
    └──feeds──>   Pill deck-context display (key chips, titles)

Actionable coach persona ──builds-on──> live-tuning-or-brain (OpenRouter brain + EN pro-feedback)
    └──requires──> EvidenceRegistry citation contract (EXISTING — extend)

Floating pill ──requires──> Tauri drag capability (KNOWN CARRYOVER BUG — fix first)
    ├──reuses──> ws_bus signals (phase/mood/levels/reaction_intent — EXISTING)
    ├──reuses──> Levels.update_voice (TTS RMS — EXISTING) for speaking waveform
    └──reuses──> EvidenceRegistry citation strip (LAUNCH-02 — EXISTING)

Suppress-harmonic-on-percussive ──gates──> Harmonic clash detection
    (spectral tonality gate must run BEFORE any key-clash note fires)
```

### Dependency Notes

- **Harmonic + transition both REQUIRE the deck data-source** — the explicitly research-gated open question. Until "all loaded tracks" has a recommended source + fallback, neither flagship note can ground. **This is the critical-path research item** (PROJECT.md flags it; STACK.md should land the verdict). The harmonic feature only needs **key per deck**; the transition feature needs **key + BPM + phrase grid + dual-deck low-band energy** — the audio side is harder than the metadata side.
- **The percussive-suppression gate must precede the clash note** — firing a clash note on atonal content is the canonical slop; the gate is a hard precondition, not a nicety.
- **Coach persona extends, doesn't duplicate, `live-tuning-or-brain`** — that branch already did OpenRouter brain + English pro-feedback + pacing/persona. v5.0 sharpens the *coach* register and wires it to the new deck data.
- **Pill drag bug is a precondition** — the Tauri drag capability is a documented v0.1.0-rc1 carryover; the pill can't ship without it.
- **Dual-deck audio is the hard part** — vibemix today analyzes the **master mix** (one stream). True bass-clash + transition mechanics from *audio* want per-deck signals, which the master doesn't separate. Likely resolution: metadata (key/BPM/title per deck from the data source) + **inferred** transition state from audible-deck weights + MIDI, rather than per-deck DSP. Flag for ARCHITECTURE/STACK.

---

## MVP Definition

### Launch With (v5.0)

- [ ] **Deck data-source resolved** (research output) — the gate for everything else
- [ ] **Deterministic Camelot clash detection** — lookup table, cited verdict, percussive-suppression gate
- [ ] **Actionable coach persona** — observed→prescriptive, DJ verbs, level-tuned; retire the narrator
- [ ] **Floating pill** — draggable (drag bug fixed), idle/active/speaking states, expand-on-event, TTS-synced waveform, last-note display
- [ ] **At least the table-stakes transition notes** that are *detectable from available signals* (phrase-alignment + bass-clash if dual-deck data lands; otherwise scope to what's grounded)

### Add After Validation (v5.x)

- [ ] **Key chips + deck context in the pill** — once deck data is solid and the pill is stable
- [ ] **Blend-length judgment tied to content** — needs duration tracking + both decks proven reliable
- [ ] **Prescriptive timing notes** ("breakdown now, bring B in") — once incoming-deck readiness is detectable

### Future Consideration (v6+)

- [ ] **Per-deck DSP** (true dual-stream audio analysis) — only if metadata grounding proves insufficient; heavy
- [ ] **Library-aware harmonic drill packs** — "mix these 5 Am↔C tracks in order" (already a v3.x candidate)
- [ ] **Next-track recommendation** — deferred by PROJECT scope; revisit only post-PMF

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Deck data-source resolution | HIGH | MEDIUM (research) | P1 |
| Camelot clash detection (deterministic) | HIGH | LOW–MEDIUM | P1 |
| Percussive-suppression gate | HIGH (anti-slop) | MEDIUM | P1 |
| Actionable coach persona | HIGH | LOW–MEDIUM | P1 |
| Floating pill (drag + states + waveform) | HIGH | MEDIUM | P1 |
| Phrase-alignment transition note | HIGH | MEDIUM | P1 (if grounded) |
| Bass-clash transition note | HIGH | MEDIUM–HIGH | P2 (depends on dual-deck data) |
| Blend-length judgment | MEDIUM | HIGH | P2 |
| Prescriptive timing notes | HIGH | MEDIUM | P2 |
| Pill deck-context / key chips | MEDIUM | MEDIUM | P2 |
| Per-deck DSP | MEDIUM | HIGH | P3 |

---

## Competitor Feature Analysis

| Feature | Mixed In Key / rekordbox (offline planners) | Generic "AI DJ assistant" tools | vibemix Approach |
|---------|---------------------------------------------|----------------------------------|------------------|
| Harmonic compatibility | Offline, pre-set planning, color-coded library | Often LLM-guesses key (hallucinates) | **Live + deterministic verdict, cited, suppressed on atonal** |
| Transition coaching | None (offline) | Generic textbook advice, uncoupled from moment | **Observed→prescriptive, tied to the actual blend** |
| Live presence | None | Chat window / overlay narration (slop-prone) | **Glance pill, out-of-the-way, real TTS waveform** |
| Grounding | Metadata-accurate (it's *their* analysis) | Weak — invents events | **EvidenceRegistry citation linter; no event = no note** |

vibemix's wedge vs both: it's **live**, it's **grounded** (provably so for harmony), and it **coaches the move**, not the vibe.

---

## Sources

- [Mixed In Key — Harmonic Mixing Guide](https://mixedinkey.com/harmonic-mixing-guide/) — Camelot system originators (HIGH)
- [Mixed In Key — Advanced Harmonic Mixing Techniques](https://mixedinkey.com/book/use-advanced-harmonic-mixing-techniques/) — +2 / +7 / diagonal / -2 (HIGH)
- [DJ.Studio — Camelot Wheel](https://dj.studio/blog/camelot-wheel) — compatible moves, perfect fifth/fourth (HIGH)
- [Mixgraph — Complete Camelot Wheel Guide](https://www.mixgraph.io/learn/camelot-wheel-guide) — clash steps, percussive exception (HIGH)
- [vibesdj.io — Camelot reference](https://vibesdj.io/learn/techniques/camelot-wheel) — +7/-5 semitone, diagonal mix (MEDIUM)
- [Pioneer DJ — How DJs approach harmonic mixing](https://blog.pioneerdj.com/djtips/how-do-djs-approach-harmonic-mixing/) — creative clash, sour mixes (HIGH)
- [DJ.Studio — Transitions Playbook](https://dj.studio/blog/the-dj-transitions-playbook) — bass swap, phrasing, blend length (HIGH)
- [Native Instruments — 5 basic DJ transitions](https://blog.native-instruments.com/dj-transitions/) — EQ trade, intro/outro (HIGH)
- [DJ.Studio — 7 Bad DJ Mixing Mistakes](https://dj.studio/blog/bad-dj-mixing-mistakes) — beatmatch/phrase trainwrecks (HIGH)
- [Superwhisper](https://superwhisper.com/) + [App Store listing](https://apps.apple.com/us/app/superwhisper/id6471464415) — dictation pill reference (MEDIUM)
- [MacStories — NotchNook & MediaMate](https://www.macstories.net/reviews/notchnook-and-mediamate-two-apps-to-add-a-dynamic-island-to-the-mac/) + [Alcove](https://tryalcove.com/) — Dynamic Island state model (MEDIUM)
- [HR Acuity — Constructive Feedback](https://www.hracuity.com/blog/constructive-feedback-examples/) + [ICCS — AID/SBI models](https://iccs.co/feedback-in-coaching-supervision/) — observed→prescriptive coaching structure (MEDIUM)
- Internal: PROJECT.md, REQUIREMENTS.md, CLAUDE.md anti-slop thesis, memory entries (`project_anti_slop_grounded_gemini_thesis`, `feedback_no_scope_creep_clean_utility`, `project_v0_1_0_rc1_open_bugs`) (HIGH)

---
*Feature research for: live AI DJ co-host — full-deck awareness, harmonic/transition coaching, actionable persona, floating-pill UI*
*Researched: 2026-05-21*
