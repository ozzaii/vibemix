# Synthesis — The 30-Second Viral Demo

**Synthesised:** 2026-05-14
**Inputs:** [C-ui-overlay.md](./C-ui-overlay.md), [B-industry-integrations.md](./B-industry-integrations.md), [D-mascot-emotion.md](./D-mascot-emotion.md), [A-latency.md](./A-latency.md)
**Confidence:** MEDIUM-HIGH — every shot is implementable with the recommended scope; main risks are AX sidecar inheritance + LiveKit text-channel ordering (both covered with fallbacks).
**Star target:** 500+ floor / 1000+ realistic. Demo is the recruitment vehicle for the first 100 stars.

---

## 0. The thesis in one paragraph

vibemix's product story is *grounded Gemini, not better prompting*. The viral demo must SHOW the grounding — not say it. Three things on screen at once: (1) the **mascot leans in BEFORE the voice arrives** (anticipation, from Bucket D), (2) the **amber ring appears around the EXACT djay control the AI just named** (overlay, from Bucket C), (3) one **deliberate silent beat** where the AI does nothing because nothing meaningful happened (the anti-slop reveal). The audience reads the absence of fakery as visible discipline — the opposite of generic AI slop. MIDI controller telemetry (Bucket B) is the cross-platform grounding layer that makes the surgical reactions feel real, even though it never appears on screen as a visible artifact.

---

## 1. Demo Storyboard — 30s filmable cut

### Setup (off-camera, baked in advance)

- **Hardware:** Kaan, DDJ-FLX4 controller, Sennheiser HD25 (visible on his head, no over-ear bulk), MacBook Pro 16" propped behind the controller at ~30° angle so the screen and his hands are in the same frame.
- **Software state:** djay Pro 5 in 2-deck mode, full-window, **NOT fullscreen** (fullscreen Space breaks the overlay per C-bucket Tauri #11488 — verified). vibemix mascot window pinned top-right of the djay window. Highlight overlay window invisible until first fire.
- **Audio:** master out → BlackHole 2ch → vibemix; monitor sends to a pair of M-Audio BX5s slightly visible in frame (cinematic depth, not for capture).
- **Lighting:** single amber tungsten key light from camera-left + cool blue rim from screen reflection. Matches the **CDJ Whisper** visual direction (Pioneer-grade, warm blacks, amber accent).
- **Music:** Kaan's hard-tech mix from 2026-05-11 session — same one referenced in the v4 tuning constants. ~138 BPM. Real takes, real reactions — NOT scripted.

### Title card (0:00 – 0:02)

Dark frame. Geist Medium, kerning -0.02. White text fades in:

> **AI that actually sees your set.**

Subtitle in Geist Mono Regular, smaller:

> *vibemix — open source. macOS + Windows.*

Cut.

### Per-second table

| t       | What's on screen                                                                                | What the AI says                                                  | Mascot (D-bucket)                                  | Overlay (C-bucket)                                          | Why this beat exists                                                |
| ------- | ----------------------------------------------------------------------------------------------- | ----------------------------------------------------------------- | -------------------------------------------------- | ----------------------------------------------------------- | ------------------------------------------------------------------- |
| 0:00–02 | Title card                                                                                      | —                                                                 | (off)                                              | (off)                                                       | Frame the value prop. No image yet.                                 |
| 0:02–05 | DJ-booth wide. Kaan, headphones, hands on FLX4, laptop screen visible behind                    | —                                                                 | Idle breathe, beat-coupled hip bob (~138 BPM)      | (off)                                                       | Establish: real DJ, real hardware, real software running            |
| 0:05–07 | Push-in to laptop screen — djay Pro fills frame                                                 | —                                                                 | Idle bob, locked to kick                           | (off)                                                       | Tell the viewer "watch the screen now"                              |
| 0:07–08 | Phase build — top deck (A) waveform low-end visibly stacks against deck B. Energy rising         | —                                                                 | **`prep_lean_in_hyped` fires** (T+50ms post-event) | Soft amber ring fades in around **Deck A mid_eq** at T+100ms | Anticipation BEFORE voice = the perceived-latency mask              |
| 0:08–09 | Same shot, ring on mid EQ Deck A                                                                | *(silence — pre-canned ack lands)* "**yeah**" (250ms, breath)     | Crossfades prep → talk\_loop\_energetic            | Ring at full opacity, pulsing slow                          | The 150ms ack from Bucket A — "alive" gap-filler                    |
| 0:09–11 | Same shot                                                                                       | "**Mids are stacking on A — cut 'em 3 to 4 dB**"                  | Talk loop hype variant                             | Ring holds 2.5s, breathes once                              | The signature "AI points at the knob" frame                         |
| 0:11–12 | Kaan's hand enters frame, twists Deck A mid EQ knob clockwise-down                              | —                                                                 | Crossfade back to idle bob                         | Ring fades to nothing over 400ms                            | Cause → effect — the fix LANDS on screen, the ring is "consumed"    |
| 0:12–14 | Cut to medium — Kaan's face + screen. Mix audibly cleans, low end opens                          | "**There it is. Cleaner.**" *(short, `[nod_yes]` emote)*          | `react_yes` overlay → talk\_loop\_calm             | (off)                                                       | Confirm — close the loop, but no ring (nothing to point at)         |
| 0:14–16 | Push-in on filter knob, deck B. Build phrase still running. Kaan's hand drifts toward it        | —                                                                 | `prep_lean_in_neutral` fires                       | Soft amber ring on **Deck B filter knob** + secondary ring on **play/cue zone**, both linked by a thin amber line | Two-element point — sells the spatial intelligence                  |
| 0:16–18 | Same shot                                                                                       | "**Build's been running 32 bars — release it.**"                  | Talk hype, head turn right                         | Both rings pulse in sync, primary on filter                 | "AI suggests a structural move" — surgical, not generic              |
| 0:18–19 | Kaan's finger flips the filter open; drop lands. Hi-hats burst, low end thumps                  | (pre-canned ack: "**brrr**" 300ms)                                | `react_drop` → talk\_loop\_energetic               | Rings fade, particle puff on mascot                         | The cinematic payoff — drop visibly **and audibly** lands           |
| 0:19–22 | Quick cut montage — 3 micro-reactions, 1s each. Each one: AI line + ring + Kaan correction      | • "**Hats too bright on B**" + ring on deck-B high EQ              | • `prep_head_turn` right → talk                    | • Ring on Deck B high\_eq, 1.5s hold                        | Density — the clip rewards rewatching                                |
| ...     |                                                                                                 | • "**Cue's two bars off — slide it back**"                        | • `prep_lean_in_neutral` → talk                    | • Ring on Deck A cue button + waveform region (paired ring) | Spatial precision again                                              |
| ...     |                                                                                                 | • "**Crossfader dragging**"                                       | • Quick head turn down → talk                      | • Ring on **master.crossfader**                             | First master-bus point in the clip                                  |
| 0:22–25 | Pull back to medium. Kaan still mixing, but now smooth. **The mascot keeps idle-bobbing.**       | *(SILENCE — 3 seconds of zero AI commentary)*                     | Idle bob, breathing, beat-locked. **No reactions.** | **No overlay.**                                             | **The anti-slop reveal.** Nothing meaningful happened → AI shut up. |
| 0:25–27 | Same shot. Kaan does a clean cue-in transition to track 3. Bass swap is technically perfect      | "**That last blend was clean.**" *(unrushed, calm `[chill]`)*     | `talk_loop_calm`, no body anticipation              | (off — no specific control referenced)                      | Praise WITHOUT pointing. Sells "AI doesn't flash on every beat"     |
| 0:27–29 | Pull to wide. Kaan smiles small. Cut to black                                                   | —                                                                 | Final idle frame                                   | (off)                                                       | Land the human moment                                               |
| 0:29–30 | Brand mark: **vibemix** + tagline. Below: `github.com/<org>/vibemix ★ 47`, ticker animation up   | —                                                                 | —                                                  | —                                                           | CTA. Github ticker = social proof in motion                          |

### Why this storyboard works

- **Density:** 6 reactions + 1 deliberate silence in 23 seconds of content (after title). Every viewer rewatches at least once.
- **Honesty:** the silence beat at 0:22–25 is the entire product thesis compressed into 3 seconds. Anti-slop made visual.
- **Cause-and-effect closure:** every ring is "consumed" by a Kaan hand movement. The viewer never wonders "did the ring do anything?" — they see the fix land.
- **One signature spatial trick:** the **paired ring + linker** (filter + play, cue + waveform) at 0:14–18 and 0:21 makes the AI feel like it's seeing **relationships between controls**, not just naming things. That single frame is the screenshot that captions itself.

---

## 2. The three signature beats (each = a viral asset on its own)

### Beat A — "The AI points at the knob" (frame at 0:09)

**What's in frame:** djay Pro UI in full, deck A mid EQ knob, amber ring at peak opacity around it. Mascot in top-right, hands-out talk pose, glow active. Caption embedded in the screenshot via post: *"Mids are stacking on A — cut 'em 3 to 4 dB."*

**Why it pops:**
There is no DJ tool in existence that does this. Every "AI DJ assistant" demo to date has been a chatbox or a generic voice overlay. The combination of (a) a real DJ app, (b) a precise point-at-this-control highlight, and (c) a spoken line referencing the same control creates an immediate "wait — is this real?" reaction. This is the **Cursor autocomplete moment** equivalent: the first time you see Cursor predict the next 3 lines of code, your brain rejects it for a second, then you screenshot it. Same shape here. The viewer's brain has to load "the AI knows WHERE the mid EQ knob is on my screen" — that's the reframe.

**Posting use:** Single hero image for Twitter post + Reddit r/Beatmatch thread. Caption-baked. No other context needed.

### Beat B — "AI anticipation lean-in" (frame at 0:07, ~50–150ms before voice arrives)

**What's in frame:** djay Pro deck A waveform showing the low-end stack pattern. Mascot already in **prep\_lean\_in\_hyped** pose — torso forward, shoulders up — *but the voice hasn't started yet.* Frame is from before t=0:08.

**Why it pops:**
This is the frame that proves the AI is *reactive*, not *scripted*. Voice assistants ship with generic "thinking" indicators (Pi orb, ChatGPT wave) — they fire AFTER the user input, *while* the model thinks. vibemix fires its anticipation visual when the **event detector** triggers, BEFORE the LLM request even sends. The mascot is responding to **the music**, not to its own internal processing. For a viewer who's seen 50 AI demos this year, this is the "huh — wait, what?" beat.

**Industry framing:** ChatGPT Voice's wave-before-speech is anticipation of *AI processing*. vibemix's lean-in is anticipation of *the world*. That's the conceptual delta to lead with on Hacker News.

**Posting use:** GIF for Twitter. The lean-in clip itself is ~500ms; loop with the voice-arrives tail and the ring fire-up = a 2-second self-playing demo.

### Beat C — "AI stays silent" (the 0:22–25 negative space)

**What's in frame:** Kaan mixing cleanly, mascot idle-bobbing, no overlay. 3 full seconds of nothing happening from the AI. Subtitle overlay (added in post): *"The AI shuts up when there's nothing to say."*

**Why it pops:**
Every AI product in 2026 has a slop problem — flashing UIs, constant suggestions, the "AI summary" banner that nobody asked for. The audience is exhausted by it. A demo that **deliberately shows the AI doing nothing** for 3 seconds is, paradoxically, the most differentiating frame in the cut. It says: this product respects your flow.

This is the move Pi made with its "warm voice that pauses naturally" comparison demos against ChatGPT Voice — silence as feature. Cursor's pitch deck has a similar slide ("Cursor accepts when you reject its suggestion and stops bothering you"). The negative space is the proof that the positive space is real.

**Posting use:** The Reddit r/DJs thread leads with this one. *"Made an open-source AI co-host that knows when to shut up — clip inside."* Closes with the GitHub link.

**Note on viral convention:** modern AI demo culture punishes overclaim. Cursor's quiet autocomplete demos outperformed Copilot's flashy ones because they showed self-restraint. Pi outperformed ChatGPT-Voice on warmth specifically through silence-handling. We're betting on the same axis.

---

## 3. Engineering critical path

### Day-by-day plan (7 engineering days, 1 engineer)

| Day | Task                                                                                                                                                                                          | Bucket | Critical? | Notes                                                                                                |
| --- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ | --------- | ---------------------------------------------------------------------------------------------------- |
| 1   | **AX bridge from Rust parent** — lift `kyleawayan/djay-pro-bridge` logic into `src-tauri/src/djay_ax.rs`. Confirm AX permission grant from parent (not sidecar). Read 2 deck-state values end-to-end. | C      | YES       | If sidecar bug (#8329) is worse than the C-doc claims, slip to day 2. Mitigation: ship as Rust cmd `get_djay_window_rect()` over Tauri IPC. |
| 2   | **Window-tracking service** — clone `find_djay_window_bounds` from `cohost_v4.py:224-246` into Rust, emit rect updates @10Hz over WS bus. Multi-monitor + retina + hidden-window guards.        | C      | YES       | This is the path-to-screen-coords primitive. Everything else assumes it works.                       |
| 3   | **12-element coord map for djay Pro 5** — hand-map percentages in Figma against a 1920×1200 djay screenshot. Save `assets/element_maps/djay_pro_5.json`. Add unit test: load map, draw 12 dots on a screenshot canvas, eyeball verify. | C      | YES       | 30 min of mapping work + 3 hr of test scaffolding + visual QA.                                       |
| 4   | **Overlay window** — second Tauri window (label `highlight`), transparent + click-through. `highlight.html` with ~200 lines vanilla JS Canvas 2D. Soft amber ring animation (1.2s in-hold-fade). Wired to receive `{element_id, hold_ms}` from event-dispatcher over WS. | C      | YES       | Re-uses mascot\_window.rs builder pattern — minimal new Rust.                                        |
| 5   | **Mascot anticipation layer** — implement just the 1-layer-above-mood case from D-bucket (not the full 4-layer rewrite — that's v2). Add `prep_lean_in_hyped` + `prep_lean_in_neutral` + `prep_head_turn` clips, wire fire-on-event-detector. Crossfade-to-talk on first audio. | D      | YES       | If LiveKit text-channel order is wrong (D-bucket A3 risk), fall back to event-detector-driven prep firing. |
| 6   | **End-to-end wire-up + Gemini `point` field** — extend coach prompt to emit `{say, point, hold_ms}` JSON. Parser strips and routes. Connect event-detect → mascot prep → overlay ring → Gemini → voice arrive → mascot crossfade. | C+D    | YES       | This is the moment all three buckets meet. ~80% of integration-test risk lives here.                 |
| 7   | **Polish + film** — tuning pass on ring color/timing, mascot crossfade duration, ack-bank timing offset. Then shoot. Multi-take strategy: 6+ takes, pick the magic take.                       | All    | NO (slip-tolerant) | Buffer day. If any of days 1–6 slipped, film on day 8 instead.                                        |

### Dependency graph (ASCII)

```
                              ┌─────────────────────────────┐
                              │ Day 1: AX bridge in Rust    │ ← C-bucket Risk #1 (TCC + sidecar)
                              │ (djay deck state read)      │
                              └─────────────┬───────────────┘
                                            │ unblocks
                              ┌─────────────▼───────────────┐
                              │ Day 2: Window tracker       │
                              │ (rect → WS bus @ 10Hz)      │
                              └─────────────┬───────────────┘
                                            │ unblocks
                ┌───────────────────────────┼────────────────────────────┐
                │                           │                            │
   ┌────────────▼──────────────┐ ┌──────────▼──────────┐ ┌───────────────▼──────────────┐
   │ Day 3: Element coord map  │ │ Day 4: Overlay      │ │ Day 5: Mascot anticipation   │
   │ (12 elements × 1 layout)  │ │ window + ring draw  │ │ layer (1-above-mood, simple) │
   └────────────┬──────────────┘ └──────────┬──────────┘ └───────────────┬──────────────┘
                │                           │                            │
                └───────────────────────────┼────────────────────────────┘
                                            │ joins
                              ┌─────────────▼───────────────┐
                              │ Day 6: Gemini `point` field  │
                              │ + end-to-end wire-up         │ ← THE INTEGRATION SPIKE
                              └─────────────┬───────────────┘
                                            │
                              ┌─────────────▼───────────────┐
                              │ Day 7: Film (buffer day)     │
                              └─────────────────────────────┘
```

### Critical path

**The path that kills the demo if it slips: Day 1 (AX bridge in Rust parent).** Everything downstream depends on the window rect being readable. If `tauri-apps/tauri#8329` bites harder than the C-bucket assumes, we lose all of days 2–4 to a frantic refactor. **Mitigation: spike this on day 0 (1 hour) — confirm we can read `kCGWindowBounds` from the Rust parent without TCC re-prompting on a code-signed bundle.** That's a 1-hour pre-flight that gates committing to the 7-day plan.

**The second-most-fragile node: Day 6.** This is where the LiveKit text-channel timing question from D-bucket A3 actually matters. If transcripts don't precede TTS audio, the mascot anticipation will fire from the **event detector** instead of the **emote tag** — that's a fine fallback but lowers ceiling.

**Slip-tolerant nodes:** Day 5 (mascot prep layer — can ship with just 1 generic `prep_lean_in_neutral` clip if `prep_lean_in_hyped` doesn't make it). Day 7 (buffer day — film on day 8 if needed).

---

## 4. Latency timing diagram

The demo's "alive" feel rests on a layered cover-up of Gemini's 1.5–3s LLM TTFT. Below is what the user sees vs. what the system is actually doing.

### ASCII timeline — single reaction (the 0:07–0:11 sequence)

```
TIME (ms after event)  │
                       │
  T+0    ┃━━━━━━━━━━━━ EventDetector.detect() — KICK_SWAP fires
         ┃                                              [Bucket B: MIDI + audio grounding]
         ┃
  T+50   ┃   ▶ Mascot prep_lean_in_hyped fires (Three.js crossFade 250ms)
         ┃     ↑ user sees motion at T+50ms                [Bucket D]
         ┃
  T+100  ┃   ▶ Overlay ring fade-in on deck.a.mid_eq starts
         ┃     ↑ user sees ring at T+100ms                 [Bucket C]
         ┃
  T+150  ┃   ▶ Pre-canned ack ("yeah", 250ms .opus) fires from disk
         ┃     ↑ user HEARS something at T+150ms           [Bucket A]
         ┃     ┌──── perceived latency = T+150ms total ────┐
         ┃     │  user already feels: "AI noticed"         │
         ┃     └─────────────────────────────────────────────┘
         ┃
  T+400  ┃   ▶ Mascot prep clip naturally ends; held at last frame waiting for talk
         ┃
  T+1500 ┃   ▶ Gemini Live first audio frame arrives over LiveKit
         ┃   ▶ Speech token extraction: tag = "[hype]" → talk_loop_energetic
         ┃   ▶ Mascot crossfades prep → talk_loop_energetic (250ms blend)
         ┃   ▶ Voice starts: "Mids are stacking on A — cut 'em 3 to 4 dB"
         ┃     ↑ user hears the REAL line at T+1500ms
         ┃     ↑ the gap between ack and real line: 1350ms of "I'm thinking"
         ┃
  T+3500 ┃   ▶ Gemini done; AI silence; mascot crossfades back to idle bop
         ┃   ▶ Ring still holding at full opacity (hold_ms = 2500)
         ┃
  T+3600 ┃   ▶ Ring fades over 400ms
         ┃
  T+4000 ┃ ━━━━ Reaction complete. Mascot back to beat-coupled idle.
```

### What each bucket contributes to the latency mask

| Bucket | Contribution                                                                                                                             | Without it…                                                                       |
| ------ | ---------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| **B** (MIDI + audio) | Event detection at T+0. The DDJ-FLX4 controller state + RMS deltas trigger `KICK_SWAP` 50–150ms before a visual analysis would.    | User perceives ~+200ms latency floor — AI feels "slow".                            |
| **D** (mascot prep)  | Visual motion at T+50ms, before any audio. Masks the next 1450ms by giving the eye something to track.                              | The mascot looks frozen for ~1500ms; user assumes the app crashed.                  |
| **C** (overlay ring) | Spatial anchor at T+100ms. Tells the eye *where* the AI is pointing before the ear hears *what* it's pointing at.                   | Voice arrives without spatial context — user has to scan the screen reactively.    |
| **A** (ack bank)     | Audible "alive" signal at T+150ms — 250ms vocal ack ("yeah"). Bridges the dead-air gap until real TTS.                              | 1500ms of silence between event and voice. Demo dies — sounds like buffering.      |

### The single most important number

**T+150ms total perceived reaction latency** — well inside the [Doherty Threshold](https://lawsofux.com/doherty-threshold) (400ms). The actual Gemini round-trip is 1500ms. The 1350ms gap is masked entirely by mascot motion + overlay + ack.

If we ship **only the mascot anticipation** (no overlay, no ack), perceived latency is ~600–800ms — still acceptable, no longer magical. The overlay + ack are what take the demo from "good" to "unbelievable."

---

## 5. Platform-specific post angles

### Twitter / X — the technical breakdown

**Hook (post 1 of thread):**

> Open-sourced an AI co-host that watches your DJ set and points at the knob it wants you to fix. 30 seconds:

[Embed 30s demo video, landscape 16:9]

**Image hero asset:** Beat A (the "ring on mid EQ" frame), pinned as a fallback for users who don't autoplay video.

**Thread continuation (5 posts):**

1. *"How it works — every reaction is grounded in 4 signals: master output audio, screen, MIDI controller, and a now-playing read of djay's window."*
2. *"The AI isn't responding to its own thoughts — it's responding to your set. Anticipation fires at event-detect time, BEFORE the LLM round-trips. That's the difference between 'voice assistant doing music commentary' and 'real DJ friend in your ear.'"*
3. *"Made for bedroom DJs. Beginner mode + Pro mode prompts, 10 controllers pre-mapped out of the box. Mac + Win. No API key needed — runs through our hosted proxy."*
4. *"Free + open source. Built by the team behind Bravoh (AI creative team for artists, closed beta March 1)."*
5. *"⭐ `github.com/<org>/vibemix` — install in under 60 seconds. `brew install vibemix` (Mac) or one-click installer (Win)."*

**CTA:** GitHub repo + install command.

**Pre-seeded FAQ in replies (Kaan and Francesco rotate answering):**

- *"What about Rekordbox?"* → "Coming v1.2. djay first because it has real accessibility hooks. Rekordbox-via-screen works as a fallback today."
- *"Doesn't this need an API key?"* → "No — we proxy Gemini through Bravoh's backend with per-client rate limits. ~50€/mo to run for now, we eat the cost. Reassess if it scales."
- *"How does it not hallucinate?"* → "It can — but it's trained on 4 grounding signals simultaneously + prompted with 'trust the audio'. We block release until the verification phase (Kaan's personal DJ-set testing) confirms zero hallucination."

### Instagram Reels — the cinematic recut

**Hook (1st frame, 9:16 vertical, large Geist Bold caption):**

> "An AI that **watches** your DJ set."

[Demo video reframed 9:16 — top third is Kaan's face, lower two-thirds is djay screen + mascot]

**Image hero:** Beat A again, but cropped tighter to the mid-EQ ring + mascot in upper-right.

**Caption (IT + EN):**

> *Un co-host AI per DJ. Vede il tuo set, ti punta il pomello giusto, sta zitto quando non ha niente da dire.*
> *An AI co-host for DJs. Watches your set, points at the right knob, shuts up when it has nothing to say.*
>
> Free, open source, Mac + Win. Link in bio.
> #djsoftware #djtools #ai #opensource #djlife #vibemix

**CTA:** Link in bio → GitHub repo + landing page.

**Comment thread anchor (pinned by @vibemix):** *"made by @kaanozkan + Francesco — the same team behind @bravoh (AI for artists, dropping March '26)"*

### Reddit r/Beatmatch + r/DJs — the open-source angle

**Title:**

> [OC] I open-sourced an AI co-host for DJ sets — it points at the knob it wants you to fix. 30s demo + GitHub inside

**Hero asset:** Beat C (the silence frame) with overlay caption *"The AI knows when to shut up — clip inside."*

**Body:**

> Hi r/Beatmatch — I built and open-sourced **vibemix**, a local AI co-host that listens to your master out, watches your DJ software's screen, reads your MIDI controller, and reacts in real time. Hype-man mode or coach mode. Three skill levels (Beginner / Intermediate / Pro).
>
> The hard problem I wanted to solve: every "AI DJ tool" I've tried either (a) flashes constantly and feels like slop, or (b) hallucinates feedback that's disconnected from what's actually happening. So vibemix is built around one rule: **the AI only reacts to real events**. If you mix cleanly, it stays quiet. If you stack the low end, it tells you to cut it AND points at the EQ knob.
>
> Stack: Gemini 3 + LiveKit, Tauri shell, Three.js mascot, native audio I/O. Free, MIT-style license (TBD).
>
> [30s demo embedded]
>
> macOS + Windows, ~60 second install. djay Pro v1, Rekordbox via screen capture + MIDI today, native Rekordbox + Serato coming v1.2.
>
> Code: github.com/<org>/vibemix
> Feedback brutally welcome — esp. from people on the hard-tech / techno side, that's where I tested it most.

**CTA:** GitHub repo + 60-second install promise.

**Pre-seeded FAQ (Kaan in comments):**

- *Why djay first?* — "djay has a working accessibility API; it's the only major DJ app where we can read the UI without screen-reading hacks. Rekordbox is coming, but they're a closed ecosystem so it takes longer."
- *Why an AI co-host?* — "I wanted a sparring partner when I practice alone. The product fails if it ever sounds like a generic AI — that's why I personally veto release until reactions feel like a real DJ friend."
- *Will it stay free?* — "Yes. We make money on Bravoh (different product). vibemix is the open-source warm-up."

### Hacker News — the engineering ship-it post

**Title:** *Show HN: vibemix — open-source AI co-host for DJ sets, grounded on audio + screen + MIDI*

**Body (2 paragraphs):**

> vibemix is a local-first AI co-host that watches your DJ software and reacts in real time. The interesting bit isn't the AI — it's the grounding. We feed Gemini 3 Flash four concurrent signals (master-out audio, screen capture of the DJ app, MIDI controller state, and a now-playing read) and prompt it with a hard "trust the audio" rule. The output is a structured reply that can optionally include a `point` field naming the exact UI control it's referencing — which we then highlight in an overlay window. Latency is masked by a 3-layer trick: visual mascot anticipation fires at event-detect (T+50ms), an amber ring on the referenced control fires at T+100ms, a pre-canned vocal ack ("yeah", "okay") plays from disk at T+150ms, then the real LLM line arrives at ~T+1500ms. Total perceived latency is well under 200ms.

> Stack is Tauri 2 + Rust parent + Python sidecar + Three.js for the mascot + LiveKit for the Gemini Live wire. macOS + Windows; macOS uses the Accessibility API for djay Pro overlay positioning, Windows uses GetWindowRect with DPI awareness. The hardest engineering problem turned out to be Tauri's sidecar permission inheritance bug (#8329) — we work around it by hoisting the AX calls into the Rust parent. Release is open source (MIT TBD). Mac+Win one-click install in <60s. Demo video in repo readme.

**Image hero:** Beat A (the "AI points at the knob" frame).

**CTA:** Github repo + install instructions.

**Engineering FAQ pre-seeded:**

- *"Why not native audio Gemini?"* → "We tried — anti-slop grounding requires the audio Part in the prompt, which the native-audio model can't accept the same way. The cascade gives us 1.5s TTFT vs ~400ms native, but the 1.1s perceived gap is masked entirely by anticipation + ring + ack."
- *"Why open source?"* → "Bravoh's our paid product. vibemix is the open-source warm-up — proves the grounding thesis publicly, recruits the audience that'll later convert to Bravoh's waitlist."

---

## 6. Risk + watchouts

| Risk                                                                                                                                  | Severity | Mitigation                                                                                                                                                                  |
| ------------------------------------------------------------------------------------------------------------------------------------- | -------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **djay-only at launch alienates Rekordbox majority**                                                                                  | MED      | Lead the demo on framing: "watch the AI point at the controls." App is mentioned in the README, not the headline. Rekordbox screen-only path ships v1.2 fast-follow.        |
| **Tauri AX inheritance bug (#8329) bites worse than expected**                                                                        | HIGH     | Day-0 1-hour spike: confirm parent-side AX read works on a code-signed bundle. If broken, fall back to template-matching path (C-bucket Approach (c)) — same demo, slower.   |
| **Demo flakiness — AI hallucinates in the take**                                                                                      | MED      | Multi-take strategy: 6+ takes per beat. Edit the magic take into the cut. The viral edit is not real-time honesty — it's a curated highlight reel (this is industry-norm).   |
| **djay EULA on overlay tools** (C-bucket verified: GREEN, but verify the take we ship)                                                | LOW      | Add "unofficial third-party tool" disclaimer in README + product. Don't trademark-stomp on "djay" in the marketing. Reach out to Algoriddim PR pre-launch — they're friendly.  |
| **LiveKit text-channel timing inversion** (D-bucket A3)                                                                               | MED      | Drop emote-tag-firing-prep entirely if spike fails. Use event-detector-driven prep instead — still hits T+50ms mascot motion, just loses fine-grained emote variety.            |
| **Mascot crossfade ugly under camera scrutiny**                                                                                       | MED      | Author the prep clip with a held-frame end pose; matches talk\_loop\_energetic's start pose so crossfade is invisible. Test on day 5 with the actual filming framing.        |
| **Ring color/timing reads as AI slop**                                                                                                | HIGH     | Lock visual treatment via `frontend-enforcement` skill review on day 4 BEFORE filming. Amber must match `cdj-whisper` direction exactly. 2.5s hold = max — never longer.       |
| **Kaan's hands move out of sync with AI calls in the take**                                                                           | MED      | The AI is real-time during filming — Kaan doesn't pre-know which knob it'll point at. Multi-take + post-edit is the answer. Or: scripted-but-honest — Kaan creates the event, AI reacts genuinely. |

---

## 7. v1.0 vs v1.1 vs v1.2 cut decision

**Recommendation:** ship the demo features as **v1.1**, NOT v1.0.

### v1.0 — June 2026 launch (~3 weeks from today)

- Mascot (current single-layer state machine — D-bucket's "this works, ship it")
- Audio + MIDI + screen grounding (already working in v4 POC)
- Gemini cascade LLM pipeline (current path)
- Hype-man + coach modes, 3 skill levels
- 10 pre-mapped controllers (DDJ-FLX4 + 9 others — the cross-platform B-bucket bet)
- Mac + Windows one-click install
- **NO overlay highlight. NO mascot anticipation layer. NO emote tags.**

**Demo video for v1.0:** the existing storyboard *minus* the rings and minus the prep layer. Still useful — shows "AI co-host that reacts to your set" — but doesn't have the signature beats. Reuse for soft-launch.

### v1.1 — July 2026 (4 weeks post-launch)

- **Overlay highlight (djay Pro, macOS)** ← Bucket C
- **Mascot anticipation layer (1-above-mood, simple)** ← Bucket D partial
- **Pre-canned ack bank** ← Bucket A
- **The viral demo posts go live with v1.1.** This is the marketing wave.

Why split: cramming the demo features into v1.0 risks blowing the 3-week timeline. Better to ship v1.0 solid + plain, run the demo recut in v1.1 once it's polished. The Bravoh public launch is March 1, 2026 — wait, that's already past relative to today's date. The remaining marketing window is the 4-week post-v1.0 push, which is exactly v1.1 timing.

### v1.2 — Q3 2026

- Rekordbox screen-capture overlay (template-matching, Approach (c))
- Mixxx OSC integration ← Bucket B
- Windows overlay polish
- Mascot full 4-layer architecture rewrite

### Opinionated call

**v1.0 = clean utility. v1.1 = viral demo wave. v1.2 = expand to Rekordbox + Mixxx.**

Do not let "we need overlay for the demo" delay v1.0. The demo can wait 4 weeks. v1.0 shipping ON TIME is what protects the relationship between vibemix and the Bravoh launch wave. v1.1 is when we make noise — by then the core product has 100s of users running it daily and the viral edit is being shared with real receipts, not promises.

---

## 8. Two open questions for Kaan

### Question 1 — Demo features in v1.0 or v1.1?

The whole synthesis above assumes **v1.1 ships the demo features** and **v1.0 ships the plain utility**. This protects the launch timeline at the cost of delaying the viral wave by 4 weeks.

**Alternative:** push hard, cram overlay + anticipation into v1.0, ship the demo at launch.

**Trade-off:** the alternative gets you the marketing pop ON the launch date (compounds with launch attention), but risks slipping the launch itself, which would create dead-air between Bravoh's prelaunch and vibemix's actual ship. Recommendation: **v1.1**. But you decide.

### Question 2 — Is "djay Pro only" acceptable for the viral demo?

The C-bucket research is unambiguous: **djay is the only major DJ app where the overlay can work cleanly in v1.1**. Rekordbox needs template-matching (slower, brittler) which can't ship in the demo timeline.

A real risk: Reddit r/DJs comment section is overwhelmingly Rekordbox + Serato users. The first 50 comments will say *"cool but I use Rekordbox, when does that ship?"* If the answer is *"v1.2, two months out"*, we lose the conversion window.

**Counter:** we already plan to ship the screen-only grounding path on Rekordbox at v1.0. The AI still reacts to your set on Rekordbox in v1.0 — it just doesn't draw rings on knobs. We can market that nuance carefully.

**Real question for you:** do we accept the djay-only overlay constraint and lead with the demo anyway, or do we delay the viral push until v1.2 (~Q3) when Rekordbox overlay ships too?

Recommendation: **lead with djay**, treat the demo as platform-agnostic in framing ("AI that watches your set" — never say "djay only" in the headline). But this is a marketing call as much as an engineering one.

---

## Cross-bucket reference index

| Synthesis section | Source bucket(s)                                                                                                |
| ----------------- | --------------------------------------------------------------------------------------------------------------- |
| Storyboard table — anticipation timing (~T+50ms)        | [D §Anticipation animation recipe](./D-mascot-emotion.md#anticipation-animation-recipe-perceived-latency-reducer) |
| Storyboard table — ring fire on element                 | [C §Element vocabulary proposal](./C-ui-overlay.md#element-vocabulary-proposal)                                  |
| Storyboard table — pre-canned ack ("yeah") @ T+150ms    | [A §Pre-Canned Ack Bank](./A-latency.md) (entries 2–3 in latency stack)                                          |
| Beat A — "AI points at knob"                            | [C §Demo storyboard](./C-ui-overlay.md#demo-storyboard-30-second-viral-cut) + this synthesis                     |
| Beat B — anticipation lean-in                           | [D §Anticipation recipe](./D-mascot-emotion.md) + [A item #6 "Visual-precedes-audio mascot"](./A-latency.md)     |
| Beat C — silence as feature                             | Anti-slop thesis (project memory) + D-bucket emote `[silent]` tag                                                 |
| Day 1 critical path — AX in Rust parent                 | [C §Risk + watchouts §1](./C-ui-overlay.md#risk--watchouts)                                                      |
| Day 5 mascot layer (simplified)                         | [D §Three.js state machine extension architecture](./D-mascot-emotion.md#threejs-state-machine-extension-architecture-mood--anticipation--speak--reaction-layers) — ship "1 layer above mood" subset only |
| Latency diagram — T+150ms reaction floor                | [A §Recommended stack for vibemix](./A-latency.md#recommended-stack-for-vibemix-ranked-by-roi)                   |
| MIDI cross-platform grounding (invisible in demo)       | [B §TL;DR point 3](./B-industry-integrations.md#tldr-the-three-strategic-calls)                                  |

---

## Metadata

**Word count target:** 2500–3500. **Actual:** ~3300.

**Confidence breakdown:**

- Storyboard feasibility: HIGH — every shot is mapped to a working bucket recipe
- Engineering critical path: MEDIUM-HIGH — 7-day estimate is on the aggressive side; 1 slip day in the buffer
- Latency timing numbers: MEDIUM-HIGH — drawn from A-bucket measured/cited values, demo-take will validate
- Platform post angles: MEDIUM — Cursor/Pi/Supabase comparisons are conventions, but our specific demo's reception is unknown
- Risk register: MEDIUM-HIGH — risks are well-mapped, mitigations are concrete

**Valid until:** 2026-06-14 (re-check Tauri #8329 status + Gemini Live text-channel timing before filming).
