# Bucket D — Mascot Emotional Intelligence Research

**Researched:** 2026-05-13
**Scope:** What it takes to push vibemix's mascot from "one-emote-per-event" to "feels alive and grounded"
**Confidence:** MEDIUM-HIGH. Most architecture moves are well-trodden (Three.js additive layers, inline emote tags from LLMs); the open risks are asset cost and the Mixamo-no-blendshapes ceiling.

---

## TL;DR (5 bullets)

1. **The complaint is real and the cause is structural, not creative.** The current state machine is a single-layer flat priority router (one clip wins, others denied). "Hard tech, same emote every time" is the predictable output of a one-clip-at-a-time system. The fix is a **layered animation architecture** (mood baseline + anticipation overlay + speak/reaction transients) with **additive blending** — not "more clips per event".
2. **Anticipation is the highest-leverage win and costs ~3 days.** Today the mascot only starts moving when the talk_loop fires, which is well AFTER the trigger detector decided to react. Insert a `react_prep` micro-clip (lean-in + head turn) the instant the event detector fires, BEFORE the prompt round-trips to Gemini. Crossfade into talk_loop when first TTS audio frame lands. This masks ~600-1200 ms of round-trip without hallucinating anything new.
3. **Beat-coupled idle already has the data — wire it through.** `cohost_v4.py` already publishes `bpm` to the WS bus and the state machine already accepts `downbeatPhase` for beat-locked entry. What's missing is a **bone-subset additive bob layer** weighted by RMS that runs continuously while idle, not just as a fresh clip swap on phase change. ~2 days, no new assets needed.
4. **Inline emote tags from Gemini are the right plan, but Gemini Live's audio modality is a constraint.** Open-LLM-VTuber's emotion-tag pattern (`[joy] that drop was filthy`) is the proven template. The trick on vibemix's stack: Gemini 2.5 native audio model has a text side-channel (transcripts), so we ask for the tag in a tool-style preamble (text-first) and only START audio gen after parsing the tag. ~1 week to design vocabulary + plumb through prompt + side-channel parser.
5. **Procedural mouth shape is a Mixamo trap — defer it.** Mixamo stopped exporting blendshapes in 2020; current mascot has none. Adding ARKit visemes means re-rigging the model (Reallusion CC4 or HeadAudio transfer tool) — that's a 2-3 week side quest with uncanny-valley risk. **Recommendation: ship 3 amplitude-banded talk variants instead** (talk_calm / talk_normal / talk_energetic, modulated by AI TTS RMS) — gets you 80% of the "alive mouth" feel at 10% of the cost.

---

## Sentiment-driven character animation SOTA

### What real VTuber tools do (state of the art as of 2026)

**VTube Studio** ([DenchiSoft API wiki](https://github.com/DenchiSoft/VTubeStudio/wiki/Plugins)) is the dominant 2D platform. Its model: a fixed catalog of **expressions/hotkeys** (each one a named blendshape combo with optional animation track), triggered by an external plugin. A plugin written in 2026 [explicitly does what we want](https://github.com/DenchiSoft/VTubeStudio): "uses an LLM to intelligently select the most appropriate hotkey based on message content". Vocabulary size is typically 15-30 expressions per model. **Confidence: HIGH** (verified docs).

**Warudo** ([handbook](https://docs.warudo.app/docs/assets/character)) — 3D, ARKit-blendshape-driven. Expressions are combos of ARKit blendshapes plus optional Trigger Conditions on facial tracking values. Warudo's relevant innovation: expressions live on **layers** (VRM BlendShapeClips on layer 0, custom on layer 1+) — that maps cleanly onto what we want to build in Three.js. **Confidence: HIGH** (verified docs).

**Open-LLM-VTuber** ([repo](https://github.com/Open-LLM-VTuber/Open-LLM-VTuber)) — closest existing analogue to vibemix. Live2D + LLM voice loop. Their pattern: **inline emotion tags in the LLM response**, stripped before TTS, mapped via `emotionMap` config to expression IDs. The system prompt teaches the LLM the available tag vocabulary. **No separate sentiment classifier model** — the LLM tags its own output. This is the architecture I recommend we copy. **Confidence: HIGH** (verified docs + repo issue thread about porting to TalkingHead 3D).

### Game industry: layered mood + transient reaction

The pattern game animators use (across Naughty Dog, Massive, etc., though specific GDC talks aren't reliably searchable for citation): characters have a **base locomotion/mood layer** running continuously (driven by slow-moving state — stamina, alert level, music genre), plus a **transient reaction layer** that crossfades in for short bursts (gunshot startle, dialogue gesture, head-turn-to-look). The two compose via additive blending so the character never goes still — even mid-reaction, the mood layer keeps the breathing/idle alive. `[ASSUMED]` general industry knowledge.

### Translation to vibemix's architecture

- **Mood layer** ↔ today's `MOOD_PROFILES.idle_default` clip, but **continuously playing** with additive overlays on top, not swapped out every event.
- **Reaction layer** ↔ today's `react_*` states, but applied as **additive bone-subset overlays on the upper body**, not replacing the idle clip.
- **Speak layer** ↔ today's `talk_loop`, additive on the head/jaw subset.
- **Effect layer** ↔ today's `puff_particle`, unchanged (one-shot, non-blocking).

That's a 4-track AnimationMixer (Three.js supports this natively via `AnimationAction` weights, see below) replacing today's "one action playing at a time" model.

---

## Anticipation animation recipe (perceived latency reducer)

### The problem in numbers

vibemix's reaction-trigger pipeline:

```
EventDetector.detect()                       T=0
  → coach_loop builds prompt                 T=~5ms
  → session.generate_reply(prompt)           T=~10ms (request sent)
  → Gemini Live first audio frame back       T=~400-1200ms (the WAIT)
  → talk_loop crossfade in                   T=~400-1200ms + 300ms blend
```

Today the mascot does **nothing visible between T=0 and T=~400ms**. The user experiences this as the AI being late or scripted. The Disney principle here is straightforward: [anticipation is preparing the audience for an action so the action reads as natural](https://www.creativebloq.com/advice/understand-the-12-principles-of-animation) — a leg pulls back before a kick, eyes widen before a yell.

### The recipe

Insert a new `react_prep` state class fired from `event-dispatcher.ts` at the moment `EventDetector` decides to react — before the Gemini request is even sent. Three flavours by event class, each ~300-500ms:

| Event | react_prep clip | Why |
|-------|----------------|-----|
| TRACK_CHANGE | `prep_head_turn` (head pivots to deck-side based on `audible_deck`) | "I noticed your deck change" — cues which deck without needing words |
| PHASE → drop / peak | `prep_lean_in_hyped` (torso forward, shoulders up) | "I felt that drop coming" — the body's "here it is" pose |
| PHASE → breakdown / silent | `prep_settle` (small exhale, slight slump) | "the energy just dropped" — sympathetic deflation |
| MIX_MOVE / KAAN_SPOKE / MANUAL | `prep_lean_in_neutral` (mild forward lean) | "I'm listening" — generic attention cue |
| AI_GENERATING_REPLY (legacy) | NO-OP — already covered above | the new prep fires earlier |

### Three.js wiring

```ts
// pseudocode in event-dispatcher.ts
case "TRACK_CHANGE":
  return runRequest(machine,
    { state: "prep_head_turn", trigger: "react_prep" },
    now,
    {                                  // followup chain:
      state: "react_surprised",        // current behavior
      afterMs: 400,                    // hold prep clip ~400ms
      trigger: "track_change",
    });
```

The `react_prep` class needs its own priority bucket — slot it at **priority 50** (between dance=40 and react=60, so it can be pre-empted by a real react clip once the AI responds, but isn't blocked by the talk_loop's lower-priority interrupt). Block rule: prep is non-blocking — never denies anything lower.

**Crucially**, the `prep_*` clip should crossFade INTO `talk_loop` (not back to idle then to talk) when the talk fires. That keeps the visible motion continuous. Three.js's `crossFadeTo()` handles this natively — fade duration of 250-300 ms hides the seam. ([three.js AnimationMixer docs](https://threejs.org/docs/pages/AnimationMixer.html), [crossFadeTo discussion](https://discourse.threejs.org/t/animationaction-crossfadeto-not-working/63467))

### Latency budget

If the prep clip starts at T=0 and is ~500ms long, and Gemini's first audio frame averages 600-1000ms on the LiveKit Gemini plugin path, the prep fully covers the wait. Even on a slow network the user sees the mascot move at T=0 and only notices the wait if they're staring at a stopwatch.

### Why this works psychologically

Voice assistants like Siri use the **glowing-orb wake animation** for the same reason: it's a "I'm here, I heard you" signal that fires BEFORE the response. ChatGPT Voice uses the [orb pulsing while it "thinks"](https://docs.livekit.io/agents/multimodality/audio/). vibemix's analogue is a body-language anticipation cue tied to the type of event detected — richer than a generic pulse because it's contextual ("oh, a track change" vs "oh, a drop coming").

---

## Three.js state machine extension architecture (mood / anticipation / speak / reaction layers)

### Today's shape (recap from reading the source)

`tauri/ui/src/mascot/state-machine.ts`:
- Single `MascotState` field on `MachineState`.
- One `AnimationAction` playing at a time via `MascotRenderer.crossFadeTo()`.
- Priority + block rules choose the winner; loser is denied or queued via `pendingSwitch`.
- 21 clips, 27 states (some share clips with different `timeScale`).

This is the "flat priority router" that's producing the same-emote-every-time complaint.

### Proposed shape: 4 concurrent layers, additive blend

```
┌────────────────────────────────────────────────────────────────┐
│ Layer 3: EFFECT (priority 100)     │ Replace mode               │
│   puff_particle (non-skeletal)     │ Three.js particle group    │
├────────────────────────────────────┼────────────────────────────┤
│ Layer 2: SPEAK + REACT (60-80)     │ Additive on upper body     │
│   talk_loop_*, react_*             │ Bone subset: spine_03+head │
├────────────────────────────────────┼────────────────────────────┤
│ Layer 1: ANTICIPATION (50)         │ Additive on torso+arms     │
│   prep_lean_in, prep_head_turn     │ Bone subset: shoulders+head│
├────────────────────────────────────┼────────────────────────────┤
│ Layer 0: MOOD/IDLE (20)            │ Normal mode, weight=1.0    │
│   idle_breathe, idle_bop_*, dance_*│ Full body                  │
└────────────────────────────────────┴────────────────────────────┘
```

### How Three.js does this (concrete)

Three.js supports two `AnimationAction.blendMode` values: `NormalAnimationBlendMode` (replace) and `AdditiveAnimationBlendMode` (sum with current pose). The base mood action runs in Normal mode, the upper-layer actions run in Additive mode. ([Three.js additive skinning example](https://threejs.org/examples/webgl_animation_skinning_additive_blending.html), [AnimationUtils.makeClipAdditive](https://threejs.org/docs/#api/en/animation/AnimationUtils))

The critical preprocessing step: any clip used in Additive mode **must first be passed through `AnimationUtils.makeClipAdditive(clip)`** — it converts keyframes to delta-from-rest format. Without that step you get "skeleton nodes overscaled" (see [forum thread](https://discourse.threejs.org/t/changing-animationactions-blendmode-to-animationblendmode/46994)). This is a one-time conversion in `asset-loader.ts` after the clip is loaded.

### Bone-subset blending — the rough edge

Three.js does **NOT** have native bone-mask support like Unity's Animation Layers. Documented workarounds ([three.js forum](https://discourse.threejs.org/t/how-to-implement-bone-specific-animation-weighting-in-three-js/65329)):

1. **Author the clips with the unused bones at zero delta.** If `prep_lean_in.glb` only animates spine_03/shoulders/head, the lower-body bones contribute zero delta and the base mood layer's legs/hips stay untouched. This is what game engines do under the hood — Three.js just expects you to author it correctly.
2. **Per-bone weighting via `AnimationAction.getMixer().getBindings()` hacks.** Possible but brittle; the binding internals are private API.

**Recommendation: option 1.** Author the new `prep_*` and `react_*` and `talk_*` clips with idle lower body. We're already commissioning new clips for the prep layer; just bake the constraint into the brief.

### Updated `MachineState` shape

```ts
export interface MachineState {
  // Each layer tracks its own current state + transition timing
  mood: { current: MoodIdleState; since: number };
  anticipation: { current: PrepState | null; since: number; expiresAt: number | null };
  speak: { current: TalkState | ReactState | null; since: number };
  effect: { current: EffectState | null; since: number; expiresAt: number };
  pendingSwitch: { layer: Layer; ... } | null;
  lastEventAt: number;
  idleTimeoutMs: number;
}
```

`planTransition()` becomes `planTransition(machine, request, now) → LayerPlan` where the plan identifies which layer it affects. The block rule simplifies dramatically: only same-layer transitions can deny each other. Cross-layer overlaps are the entire point of the design.

### Cost estimate

- New types + state-machine refactor: **3-4 days**
- Asset loader's `makeClipAdditive` plumbing for layered clips: **1 day**
- Renderer's multi-action concurrent play + weight management: **2-3 days**
- Vitest port (existing 4 test files cover ~80% of state-machine surface — needs new fixtures): **3 days**

**Net: ~2 weeks for a clean refactor + tests.** Existing 27-state vocabulary stays compatible — they all default to a single layer based on `STATE_CLASS`.

---

## Beat-sync idle + genre-aware mood biasing

### What we already have (read this carefully — the data is in the bus)

- `cohost_v4.py` line ~1660-1704: `bpm_cache` updated every 3s via `audio_buf.estimate_bpm(seconds=6.0)`. Result written to `state.bpm`.
- The WS broadcast (line 1876-1922) sends `levels.snapshot() + audible + deck + phase` at 30 Hz — **bpm is NOT in the snapshot yet**. Phase 13-05 adds `bpm + bpm_confidence + downbeat_phase + mood` per a planner note in mascot code comments.
- `state-machine.ts` already accepts `bpmConfidence ≥ 0.6` and a `downbeatPhase` for beat-locked entry into idle/dance clips.

So the wiring is 80% done — the missing piece is **continuous bobbing weighted by RMS**, not just clip-swap-on-phase-change.

### The two flavours of beat sync

1. **Phase-locked bob (deterministic):** The mascot's hip Y oscillates `sin(2π × beat_phase)` where `beat_phase` advances `bpm/60` Hz. Hits zero-crossing on the kick. Best for **hard tech, techno, EDM** — anything where the kick is the focal point. Reads as "the mascot is hitting on the 1".

2. **Amplitude-driven bob (procedural):** Hip Y modulated by short-window RMS envelope. Reads as **flowing**, not punching — best for ambient, house grooves, downtempo. Doesn't lock to a specific beat.

### Genre detection — coarse but workable

vibemix doesn't have a genre classifier today, but we can derive a usable proxy from features `MusicState` already exposes:

| Genre bucket | BPM range | RMS peakiness | Recommended bob |
|--------------|-----------|---------------|-----------------|
| hard tech / techno | 130-145 | high (peak/avg >2) | phase-locked, weight 0.8 |
| house / disco | 118-128 | moderate | phase-locked, weight 0.5 |
| ambient / downtempo | <100 or no bpm | low (peak/avg <1.3) | amplitude-driven, weight 0.6 |
| breakdown / silent | any | low | none (idle_breathe only) |

`peak/avg` = max(recent RMS) / mean(recent RMS) over a 4-second window. The `MusicState.recent` list in `cohost_v4.py` already buffers this.

### Implementation

A new additive layer **below** the idle layer (priority 5), driven procedurally — not from a clip. Three.js can drive a single bone's transform directly via `bone.position.y = baseY + bobAmount * sin(phase)` in the rAF loop, then `bone.matrixWorld.needsUpdate = true`. **Confidence: HIGH** — this is straight Three.js skeletal manipulation, no edge cases.

The procedural bob doesn't need to be a clip. It's a "post-processing" step inside `MascotRenderer.tick(deltaSeconds)` that adjusts the `Hips` bone position AFTER `mixer.update()` runs. The mood layer's clip already animated the hips for breathing/bopping; the procedural bob adds a small Y offset on top — additive in code, not in clip-blend.

### Cost estimate

- Adding `bpm` + `downbeat_phase` + recent-RMS array to WS payload (Python side): **0.5 day**
- Procedural hip-bob driver in renderer: **1.5 days**
- Genre-bucket heuristic in event-dispatcher: **0.5 day**
- Tuning passes against real DJ sessions: **1-2 days**

**Net: ~3-4 days.** Massive perceived-quality win because it's the difference between "decoration on the screen" and "moves WITH me".

---

## Emote tag vocabulary proposal (table)

Vocabulary the AI emits inline. Stable, finite (15 tags + 1 mood-set tag = 16 total). Each maps to a layer/action combo. Inspired by [Open-LLM-VTuber's `emotionMap`](https://github.com/Open-LLM-VTuber/Open-LLM-VTuber), specialised for DJ-set context.

| Tag | Layer | Action | When the AI should emit it |
|-----|-------|--------|----------------------------|
| `[hype]` | speak | `talk_loop_energetic` | celebrating a clean transition / a fire track / drop landing |
| `[chill]` | speak | `talk_loop_calm` | low-energy moments, breakdowns, slow-burn observations |
| `[teach]` | speak | `talk_loop` + `point_explain` overlay | coaching mode — explaining a fix |
| `[surprise]` | speak | `react_surprised` then talk | unexpected genre shift, weird drop, sudden volume change |
| `[nod_yes]` | reaction | `react_yes` | agreement, "good call", "yeah that worked" — confidence high |
| `[shake_no]` | reaction | `react_no` | "nah", "lost the low end" — gentle disagreement |
| `[glitch]` | reaction | `react_glitch` | crash, mistake, beat slip — the "oof" reaction |
| `[drop_now]` | reaction | `react_drop` | drop is HAPPENING this bar, full-body commit |
| `[gesture_deck_a]` | anticipation | `prep_head_turn` (left) | referring to deck A audibly |
| `[gesture_deck_b]` | anticipation | `prep_head_turn` (right) | referring to deck B audibly |
| `[lean_listen]` | anticipation | `prep_lean_in_neutral` | curious, paying attention, "what is this" |
| `[lean_hype]` | anticipation | `prep_lean_in_hyped` | hype building, "here it comes" |
| `[settle]` | anticipation | `prep_settle` | energy dropped, calming down |
| `[celebrate]` | reaction | `celebrate` (existing) | drop landed clean, milestone moment |
| `[silent]` | NONE | — | AI is intentionally not reacting — just keep idle going |
| `[mood:hype-man\|teacher\|coach]` | mood | swap MoodProfile | only emitted when persona genuinely shifts (rare) |

### Prompt-template engineering

Add to the system prompt (slot in after the current "trust the audio" rules):

```
EMOTE TAGS — inline expressions that drive the mascot. Put EXACTLY ONE tag in
square brackets at the START of your reply, on its own line.
The tag is stripped before TTS — never read it aloud.

If you say nothing (silence reply for an automatic event), emit [silent] alone.
For multi-sentence replies, the tag covers the whole turn — don't switch.

Available tags: [hype] [chill] [teach] [surprise] [nod_yes] [shake_no]
[glitch] [drop_now] [gesture_deck_a] [gesture_deck_b] [lean_listen]
[lean_hype] [settle] [celebrate] [silent]

Pick the one tag that best matches the EMOTIONAL CORE of what you're about
to say. Default to [lean_listen] if unsure. Never invent new tags.
```

### Parser side (TypeScript)

Strip the tag with a regex at the WS bridge before it reaches TTS-text-display. Bus-event-dispatcher fires the corresponding state request immediately:

```ts
const TAG_RE = /^\[(\w+(?::[\w-]+)?)\]\s*\n?/;
const m = aiText.match(TAG_RE);
if (m) {
  dispatchEmoteTag(m[1], now);  // fires anticipation + speak layer state
  return aiText.slice(m[0].length);  // text shown to user (no tag)
}
```

### Latency note — VERY important

If we want the anticipation layer to fire BEFORE TTS audio plays, the tag has to arrive in the text/transcript channel **ahead of** the audio stream. Per [Gemini Live API docs](https://ai.google.dev/gemini-api/docs/live-api/capabilities), text transcripts arrive as a side-channel alongside the audio stream. **Confidence: MEDIUM — needs verification with the actual livekit-plugins-google integration.** If the transcript lags the audio, this whole flow degrades to "tag fires when talk_loop fires", which still works but loses the anticipation benefit. **This needs a spike before Phase 2 plans commit to it.**

A fallback: drop the inline-tag approach and instead **inspect the first 200ms of TTS audio amplitude + spectral centroid** to bucket into hype/chill/neutral. Coarser, lossier, but doesn't depend on Gemini behaviour. Reserve as plan B.

---

## Procedural face / mouth — recommendation

### The Mixamo problem (this is load-bearing)

Per Mixamo support and [forum threads](https://community.adobe.com/t5/mixamo-discussions/can-i-add-facial-expressions-with-mixamo/td-p/11479675): **Mixamo stopped exporting blendshapes in late 2020**. The current vibemix mascot (Meshy/Hunyuan3D → Mixamo auto-rig → 21 GLBs) has **zero facial blendshapes**. There is no `jawOpen`, no `viseme_aa`, no ARKit shape keys. **Confidence: HIGH** (multiple recent corroborating sources).

### Options ranked by ROI

**Option A — Ship 3 amplitude-banded talk variants (RECOMMENDED).**
- Already have `talk_loop`, `talk_loop_calm`, `talk_loop_energetic` in the state vocabulary (`types.ts` lines 39-41).
- Author each variant with a different head+jaw amplitude baked in.
- Pick the variant per turn based on emote tag (`[chill]` → calm, `[hype]` → energetic, default → normal).
- **Cost: 0 new pipeline work.** Just commission 3 talk clips with deliberate amplitude differences.
- Reads as "different energy" without procedural mouth shape. The mascot has stylised features so the user doesn't expect phoneme accuracy.

**Option B — Re-rig with ARKit blendshapes via HeadAudio.**
- [met4citizen/HeadAudio](https://github.com/met4citizen/HeadAudio) is an AudioWorklet that produces real-time Oculus viseme blendshape values from audio (MFCC + Mahalanobis classifier). Designed for browser use, works alongside Three.js.
- Requires re-rigging the mascot character GLB with the 15 Oculus visemes (or 52 ARKit blendshapes). Tools exist for transferring blendshapes from a reference avatar onto a target avatar that lacks them — [digitalp/arkit-blendshape-tool](https://github.com/digitalp/arkit-blendshape-tool).
- **Cost: 2-3 weeks** (re-rig + blendshape transfer + integration + tuning).
- **Risk:** the current mascot is stylised — adding photorealistic viseme accuracy will fight the aesthetic. Likely uncanny.

**Option C — Procedural jaw bone rotation.**
- Add a `jaw` bone to the rig, drive its rotation from `AudioAnalyser.getByteFrequencyData()` in 500-2000 Hz band (formant range).
- Works with any rig — no blendshape requirement.
- Reads as a puppet's flapping jaw — competent but generic.
- **Cost: 1 week.** ([three.js AudioAnalyser](https://threejs.org/docs/pages/AudioAnalyser.html))
- Useful AS A LAYER on top of Option A's talk variants. Combines well — talk_loop_energetic clip drives most of the motion, jaw rotation adds the "syllable hit".

### Recommendation

**Ship Option A in v2. Plan Option C for v2.x as a polish pass. Defer Option B forever** unless we redesign the mascot character itself.

If Kaan wants ONE thing in v2 — Option A alone, with 3 distinct talk-loop amplitudes, plus the inline emote tag picking between them, will close most of the "feels the same every time" gap.

---

## Asset pipeline + rig recommendations

### The current pipeline (from memory note + code reading)

Meshy or Hunyuan3D → Mixamo auto-rig → 21 GLB animation clips → manifest.json → Three.js GLTFLoader + DRACOLoader.

This works and the per-clip cost is low (Mixamo is free, Meshy is cheap, the GLB pipeline is solid). The question is which axis to extend.

### Body rig vs face rig — what's the higher ROI for "feels alive"?

| Axis | Current state | To unlock "alive" feel | Cost | ROI |
|------|--------------|------------------------|------|-----|
| **Body rig variety** | Mixamo standard bipedal | New prep_* / react_alt_* clips authored against the existing rig | $50-150 in Meshy/Mixamo per new clip × ~8 new clips | HIGH |
| **Face rig (blendshapes)** | None (Mixamo strips them) | Re-rig with ARKit visemes | 2-3 weeks engineering + uncanny risk | LOW |
| **Bone count** | Standard Mixamo (~65 bones) | Same — sufficient | $0 | n/a |
| **Procedural overlay** | None | Hip-bob driver in renderer | 2 days engineering | HIGH |

**Body wins.** The mascot is a stylised character — the user reads gesture and posture, not lip detail. 8 additional body-rig clips (the new `prep_*` family + 2-3 alt `talk_*` clips) cost <$1500 in asset spend and unblock the entire layered architecture.

### Specific new clips to commission

| State | Clip name | Length | Notes |
|-------|-----------|--------|-------|
| prep_lean_in_neutral | "lean_listen" | 0.5s | shoulders slightly forward, head tilt — additive, idle lower body |
| prep_lean_in_hyped | "lean_anticipate" | 0.5s | torso forward + shoulders up — additive, idle lower body |
| prep_head_turn_left | "head_turn_a" | 0.5s | head pivots to character-left (deck A direction) |
| prep_head_turn_right | "head_turn_b" | 0.5s | head pivots to character-right (deck B direction) |
| prep_settle | "settle_down" | 0.5s | exhale, slight slump, shoulders drop — additive |
| talk_loop_energetic_v2 | "talk_hype" | 2s loop | higher head/torso amplitude than current talk_loop_energetic |
| react_celebrate_alt | "celebrate_b" | 1s | second celebrate so it doesn't always look identical |
| dance_alt3 | "dance_alt3" | 4s loop | third dance variant for hard-tech rotation |

All authored with **idle/zero lower-body delta** so they additive-blend correctly without floor-skating.

### Mascot character design references

- **Pi (Inflection AI)** — orb with subtle particle/glow shifts. Strong "always alive" feel; weak personality differentiation. Sets the bar for "doesn't look cheap".
- **Neuro-sama / Open-LLM-VTuber stack** — Live2D anime style. Strong personality, very expressive eye/mouth. But anime stylisation locks the demographic.
- **Clippy reborn (no good current example)** — the warning case: any cartoony attempt that doesn't commit fully reads as cheap/embarrassing.
- **DJ-genre-native characters** (Daft Punk, Aphex Twin avatars, etc.) — heavy use of mask + silhouette + abstract head shape. Lets the body do the emotional work.

vibemix's "DJ bat" placeholder is in the right zone — abstract enough that gesture > face. **Recommendation: lock the stylised abstract head approach, push hard on body language richness.** That's the cheap, high-ROI lane.

---

## Risk + watchouts

### Asset cost creep
8 new clips at $100-200 each is $800-1600. Within v2 budget. **BUT** — Meshy auto-generation quality varies; you'll likely commission 1.5× the final count to get usable ones. Budget $2000 with a 25% reject rate. **Risk: medium.**

### Rendering perf budget
Today: 1 AnimationAction playing + 1 GLB scene + 1 directional light. ~3-5ms/frame on M2.
After layered architecture: 3-4 concurrent actions, plus per-frame additive blending, plus the procedural hip-bob bone update. Three.js skinned-mesh additive blending is "free" relative to a single replace action because both compose via the same internal matrix multiply pass — the cost is allocation of the AnimationAction objects (one-time). Realistic estimate: **+1-2ms/frame on M2 = 5-7ms/frame total = 60+fps still trivial.** **Risk: low.** [`[ASSUMED]` based on Three.js architecture, not benchmarked]

### Uncanny valley
The mascot is currently stylised enough to dodge uncanny territory. Adding ARKit visemes (Option B above) drags it toward photoreal-but-not-quite. **Risk: high if Option B pursued.** Stay on body rig + abstract head → no uncanny risk.

### Anti-slop gate
Every new emote tag is a new way for Gemini to lie. If `[drop_now]` fires but no drop is actually happening, the mascot's commit reads as MORE hallucination, not less. **Mitigation:** the emote tag is decorative on top of the existing reaction text, not a replacement for it. The "no hallucination" verification (Phase 16, Kaan's ear-test) still gates release. **Risk: medium.** Don't ship the emote-tag vocabulary until the underlying reaction system passes Kaan's DJ-set test.

### Mixamo blendshape ceiling (already covered above)
Sets the upper bound on facial expressiveness. If Kaan's quality bar for v2 actually requires photoreal lip-sync, this entire research bucket needs re-scoping. **Risk: low for v2 (Kaan's bar is "alive body language"), high for v3+ if facial detail becomes the bar.**

### LiveKit Gemini text-channel timing assumption
The whole anticipation-via-emote-tag plan rests on text transcripts arriving before TTS audio frames. If that ordering inverts (which has been seen on lossy connections), anticipation degrades to no-op. **Mitigation:** ship the anticipation layer FIRST, driven by `EventDetector` directly (T=0 prep clip), with the emote-tag refinement as a phase 2 enhancement. **Risk: medium.** Spike this with a 1-day test against the actual livekit-plugins-google integration before committing to the design.

### Mascot stuck on wrong layer
With 4 concurrent layers, bugs that wedge a layer (e.g., react_prep stays at weight=1 indefinitely) become subtle — the mascot looks slightly off but doesn't visibly fail. **Mitigation:** every additive layer needs a "max age" guard. If `anticipation.expiresAt < now` for >2 seconds, force-clear. Add to renderer's tick. **Risk: medium.**

---

## Open questions for Kaan

1. **Is the LiveKit Gemini text-channel reliable enough for anticipation tag firing?** Needs a 1-day spike before Phase 2 plans solidify. If not, fall back to event-detector-driven anticipation (cheaper, less precise, still effective).
2. **How much new asset spend is OK for v2?** Targeting ~$1500-2000 for 8-10 new clips. Lower? Then drop the `prep_head_turn_left/right` pair (deck-specific head turns) and use a single generic prep — costs us deck-direction expressiveness but saves 2 clips.
3. **Is "stylised abstract head, body-language-led emotion" the locked aesthetic for v1 + v2?** This research recommends locking it (avoids Mixamo blendshape mess, dodges uncanny valley). If the answer is "we might pivot to anime/photoreal facial expression later", the layered architecture still works — just the talk-loop variants story changes.
4. **Should the emote tag be REQUIRED in every AI turn (anti-slop) or OPTIONAL (latitude)?** Required = consistent mascot expression but forces the LLM to pick a bucket even on ambiguous turns. Optional = better text quality but mascot defaults to neutral idle on unparsed turns. Recommend **required** with `[silent]` as the valid escape hatch.
5. **Is Phase 13's flat priority router considered "done and don't touch" for v1, with the layered architecture landing in v2?** This research assumes yes — the v1 mascot ships with the current single-layer system, and the bucket-D rebuild is a v2 epic. Confirm before any planner spawns plans against this doc.

---

## Sources

### Primary (HIGH confidence — verified docs)
- [Three.js AnimationMixer API docs](https://threejs.org/docs/pages/AnimationMixer.html)
- [Three.js AnimationUtils.makeClipAdditive docs](https://threejs.org/docs/#api/en/animation/AnimationUtils)
- [Three.js additive skinning example](https://threejs.org/examples/webgl_animation_skinning_additive_blending.html)
- [Three.js AudioAnalyser docs](https://threejs.org/docs/pages/AudioAnalyser.html)
- [VTubeStudio plugin API wiki](https://github.com/DenchiSoft/VTubeStudio/wiki/Plugins)
- [Warudo character handbook](https://docs.warudo.app/docs/assets/character)
- [Open-LLM-VTuber repo + emotionMap design](https://github.com/Open-LLM-VTuber/Open-LLM-VTuber)
- [met4citizen/TalkingHead — JS class for full-body avatar lip-sync](https://github.com/met4citizen/TalkingHead)
- [met4citizen/HeadAudio — real-time viseme detector AudioWorklet](https://github.com/met4citizen/HeadAudio)
- [Gemini Live API capabilities (text + audio concurrent modalities)](https://ai.google.dev/gemini-api/docs/live-api/capabilities)
- [LiveKit Gemini plugin docs](https://docs.livekit.io/agents/models/realtime/plugins/gemini/)
- [Rhubarb Lip Sync — 6-9 mouth shapes standard](https://github.com/DanielSWolf/rhubarb-lip-sync)

### Secondary (MEDIUM confidence — community/forum, multiple corroborating)
- [Three.js forum: bone-specific animation weighting](https://discourse.threejs.org/t/how-to-implement-bone-specific-animation-weighting-in-three-js/65329)
- [Three.js forum: AnimationAction.crossFadeTo](https://discourse.threejs.org/t/animationaction-crossfadeto-not-working/63467)
- [Three.js forum: AdditiveAnimationBlendMode pitfalls](https://discourse.threejs.org/t/changing-animationactions-blendmode-to-animationblendmode/46994)
- [Disney 12 principles of animation — anticipation](https://www.creativebloq.com/advice/understand-the-12-principles-of-animation)
- [Mixamo no longer exports blendshapes (Adobe community thread)](https://community.adobe.com/t5/mixamo-discussions/can-i-add-facial-expressions-with-mixamo/td-p/11479675)
- [ARKit blendshape transfer tool](https://github.com/digitalp/arkit-blendshape-tool)

### Internal references read
- `/Users/ozai/projects/dj-set-ai/tauri/ui/src/mascot/types.ts` — state vocabulary + priority
- `/Users/ozai/projects/dj-set-ai/tauri/ui/src/mascot/state-machine.ts` — pure transition logic
- `/Users/ozai/projects/dj-set-ai/tauri/ui/src/mascot/renderer.ts` — Three.js wiring
- `/Users/ozai/projects/dj-set-ai/tauri/ui/src/mascot/mood.ts` — MoodProfile + 3 personas
- `/Users/ozai/projects/dj-set-ai/tauri/ui/src/mascot/event-dispatcher.ts` — bus → state request mapping
- `/Users/ozai/projects/dj-set-ai/tauri/ui/src/mascot/asset-loader.ts` — manifest + GLB pipeline
- `/Users/ozai/projects/dj-set-ai/tauri/ui/src/mascot/ws-client.ts` — bus subscription + backoff
- `/Users/ozai/projects/dj-set-ai/cohost_v4.py` — bpm + RMS + ws_broadcast payload

### Assumptions log (per research discipline)
| # | Claim | Risk if wrong |
|---|-------|---------------|
| A1 | Three.js additive blending costs +1-2ms/frame on M2 | Perf budget regression; mitigation: benchmark before merging |
| A2 | Game industry mood-layer + transient-reaction is universal pattern | Some specifics may differ per engine; doesn't affect Three.js plan |
| A3 | Gemini text transcripts reliably precede audio frames | Anticipation tag flow degrades; fall back to event-detector-driven prep |
| A4 | Meshy clip generation has ~25% reject rate | Asset budget under-quoted by 25%; pre-empted by quoting $2000 not $1500 |
| A5 | Re-rigging with ARKit blendshapes introduces uncanny valley on the current stylised character | Subjective — Kaan judges via Phase 16 ear-test if Option B is ever explored |
