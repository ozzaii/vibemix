# vibemix — Capabilities Brief for Partners

*Prepared for outreach. May 2026.*

---

## In one line

**The only AI co-host that actually listens to your set.**

vibemix runs locally on a DJ's Mac or PC, listens to the master output, watches the DJ software, reads the MIDI controller, and talks back into the headphones — as a hype-man or a coach — grounded in what the DJ actually just did.

Not generic AI commentary. Not hallucinated track names. Not late reactions. The whole product is engineered around one bar: *"does this feel like a real DJ friend in your ear, or does it feel like AI slop?"* If reactions are scripted, late, hallucinated, or generic, it has failed regardless of polish.

Open source under Apache 2.0. Built by [Bravoh](https://bravoh.ai) as the open-source warm-up for our main product launch.

---

## The four capabilities

### 1. Live co-host

While a DJ plays, vibemix runs three grounding sources in parallel and speaks back into the headphones in real time:

- **Audio** — master output via BlackHole (Mac) / WASAPI loopback (Windows). Hears every cut, EQ move, transition, drop.
- **Screen** — DJ software window via screen capture. Reads current track, BPM, key, deck states, cue points on screen.
- **MIDI** — controller directly over USB. Knows when the filter swept, the loop hit, the crossfader moved.

These feed a state-of-the-art multimodal model through Bravoh's proxy, and the reaction comes back as streaming TTS — calm, warm, or gruff.

**Two modes, three skill levels, six voices.**

| | Hype-man (party energy) | Coach (post-cue critique) |
|--|--|--|
| **Beginner** | *"Nice. You held the EQ steady through that intro."* | *"That cut was a beat off. Try waiting for the downbeat next time."* |
| **Intermediate** | *"Clean swap. Bassline locked."* | *"You're filtering on every transition. Mix it up — let one through dry."* |
| **Pro** | *"That was a stack and a hot-cue trigger inside one bar. Disgusting."* | *"You're hitting the same loop tool four tracks in a row. Crowd's reading it."* |

Each cell speaks a different vocabulary on purpose. Coach mode is always past-tense — vibemix won't talk over a working DJ.

### 2. Vibe Library

A local-only search engine across the DJ's own collection.

- **Cross-modal search** — *"Find me something darker."* *"Tracks that feel like the one I just played."*
- **Track-to-track similarity** by audio fingerprint, not metadata.
- **100% local** — on-device CLAP model (~785 MB, one-time). The DJ's library never leaves their machine.
- **Cue-anchored** — fingerprints the mixable sections (intro, breakdown, drop, outro), not the random middle, so similarity reflects what a DJ would actually mix.

Today: Rekordbox `collection.xml` ingest shipping. Serato and Traktor next.

### 3. Set Builder ("Viber")

A grounded set-prep agent that turns a brief into a sequenced, harmonically valid set.

- **Discover** — DJ describes the set ("warm-up into peak-time techno, 90 min, dark room"). Viber pulls a pool from the DJ's library using Vibe Library plus hard filters on key, BPM, energy.
- **Sequence** — orders the pool along a chosen energy curve via beam-search on a harmonic transition graph. 3–5 diverse paths to compare.
- **Explain every transition** — for each move, *why*: same key, Camelot hop, BPM bridge, energy lift, vibe rhyme. The DJ learns by reading.
- **One-click export** to Rekordbox XML with order, key/BPM, memory cues, hot cues, beatgrids preserved.

Optional Telegram bridge: curate a playlist from your phone on the commute, find it ready on the laptop at home.

### 4. Beginner Module (v9.0, in build)

The next major release. An interactive teaching mode for someone who just bought their first controller.

- **Visual controller mirror** — the user's actual controller renders on screen at scale. The AI highlights the next control to touch. The user touches the physical control. The lesson advances.
- **36 lessons across 3 courses** — *Anatomy of a Deck* (16), *Transitions* (14), *Play Mode* (6 + a proactive tutor lens that rides alongside a real set).
- **Library-driven exemplars** — when the lesson explains the low EQ, the AI plays a track from the user's own library that demonstrates it. They *hear* the kick drop out.
- **The tone** — friendly, confident, not condescending. Opening dialog locked verbatim: *"Hello vibemix, what are you?" — "I'm the best DJ app in the world." — "If you are the best, then who the fuck am I?" — "Oh bestie, don't worry. You know why? Because I'm the beginner module of vibemix. Let's go."*

The Beginner Module turns vibemix from a tool DJs use into a path a non-DJ can walk to become one — the natural integration point for DJ schools and controller manufacturers.

---

## The moat — citation grounding

vibemix doesn't drift into AI slop for structural reasons, not prompt-engineered ones.

Every reaction must cite real evidence — the audio chunk, the MIDI event, the on-screen track, the cue point in the file. A central `EvidenceRegistry` holds the citable facts. If the AI claims something it can't cite, the citation linter strips it to a one-word ack before the user ever hears it. Discipline is enforced at four points in the pipeline, locked in by tests, held by four cardinal product invariants.

Layered on top: an anti-slop vocabulary blocklist, past-tense framing for coach mode, a `<silence/>` token so the model can choose to say nothing, per-session anti-repetition, and a hallucination verification gate (≥95% grounded reactions on real sets) that must pass before any release ships.

The difference between *"DJ tries it once, decides it's a gimmick"* and *"DJ keeps it open every set."*

---

## Supported gear

**DJ software (works alongside, no integration needed):** rekordbox · Serato · Traktor · djay Pro · VirtualDJ · Mixxx. App-agnostic by design — if the audio routes through BlackHole or WASAPI loopback, vibemix can co-host it.

**Controllers mapped out of the box (10):** Pioneer DDJ-FLX4 · DDJ-FLX6 · DDJ-FLX10 · DDJ-400 · DDJ-1000 · DDJ-SX3 · XDJ-RX3 · Numark Party Mix Live · Hercules DJControl Inpulse 300 · Inpulse 500. Anything else uses a generic positional fallback; new mappings ship via a contributor recipe (`scripts/sniff_controller.py` + a JSON profile). CI auto-merges clean profile additions.

---

## Privacy & data

- **Live co-host** streams audio + screen + MIDI through Bravoh's proxy at `api.bravoh.ai`, which forwards to our hosted AI model. **No raw audio stored on Bravoh's servers.**
- **Vibe Library** and **Set Builder** run 100% locally. Library never leaves the machine.
- **Recordings** stay local under `recordings/<session>/`, 7-day default retention, configurable from 1 day to forever.
- **No telemetry by default.** Anonymous crash reports are opt-in via the first-run wizard.
- **BYO-key path** — point vibemix at your own model-provider API key via env var; Apache 2.0 makes a private fork trivial.

Full disclosure in `SECURITY.md` (responsible disclosure, threat model, proxy's role).

---

## Platforms & install

- **macOS Apple Silicon** — signed and notarized, shipping today via DMG.
- **Windows 11** — ships with v0.1.0 stable. SignPath OSS signing approval in flight.
- **Linux** — out for v1 (open to a community PR).
- **License** — Apache 2.0. Fork it, point it at your own key, ship it inside something else. We're fine.

---

## Where this is going

In rough priority order:

1. **Beginner Module ship** (v9.0, in build) — the teaching surface; the natural fit for controller makers and DJ schools.
2. **Serato + Traktor library ingest** — close the parity gap with rekordbox.
3. **Mixxx OSC** — direct deck-state read instead of screen-vision inference.
4. **Pioneer Pro DJ Link** — direct hardware deck-state read for CDJ/XDJ users (probe in flight).
5. **Auto-cue engine** — server-side CUE-DETR + downbeat detection labelling phrase structure for every track in the library.

Out of scope on purpose: stem separation, multi-provider AI, enterprise dashboards, social feeds. vibemix optimizes for the minimum useful surface.

---

## Built by Bravoh

[Bravoh](https://bravoh.ai) is the AI creative team for music artists — four AI-powered agent personas helping artists with creative direction, marketing, production, release strategy. **Currently in closed beta.**

vibemix is Bravoh's first open-source release — not a side project, the warm-up. A polished, narrow-scope utility for a community Bravoh wants to be trusted by. Target on its own: 500–1,000+ GitHub stars at launch, a working installed base across rekordbox / Serato / Traktor, and a Discord community giving real feedback against real sets.

---

## Where partners fit

**Controller manufacturers** — official sign-off on the bundled mapping. Co-branded launch around the Beginner Module (the controller you make is the one the user sees on screen). Joint content for the DJ-school channel.

**DJ software vendors** — deeper integration than the audio + screen + MIDI floor. OSC, direct library access, native co-host surface inside your app. Mixxx is the obvious open-source candidate; everyone else is a conversation.

**DJ schools and educators** — the Beginner Module as a teaching surface. Branded curriculum slots. A measurable funnel from "first time touching a controller" to "first set played."

**Distribution, community, press** — Discord, festival activations, influencer DJs on real sets, write-ups in DJ media. The product is most shareable when an actual DJ is using it in an actual room.

Private demo on real hardware (Pioneer DDJ-FLX4, rekordbox, Mac) — Kaan can run it for you on a call or in person.

---

**Contact**

- **Kaan Özkan** — co-founder · `kaan@bravoh.ai`
- **Francesco Fasanella** — co-founder · `francesco@bravoh.ai`
- **Repo** — `github.com/bravoh-ai/vibemix`
- **Bravoh** — [bravoh.ai](https://bravoh.ai)
