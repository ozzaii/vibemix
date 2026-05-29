# vibemix — Capabilities Brief for Partners

*Prepared for outreach. May 2026.*

---

## In one line

**The only AI co-host that actually listens to your set.**

vibemix runs locally on a DJ's Mac or PC, listens to their master output, watches their DJ software, reads their MIDI controller, and talks back into their headphones as either a hype-man or a coach — grounded in what they actually just did.

Not generic AI commentary. Not hallucinated track names. Not late reactions. Built by DJs, tuned against real sessions on rekordbox, Serato, Traktor, and djay Pro.

Open source under Apache 2.0. Built by [Bravoh](https://bravoh.ai) as the open-source warm-up for our main product launch.

---

## Why this exists

DJs don't need another voice assistant. They don't need a chatbot. They don't need a generic LLM riffing on the word "drop" while the kick they just dropped is still ringing out.

What they need — and what the category has never delivered — is a co-host that **notices the actual thing they just did, in time, in vocabulary, and in tone.** A hype-man that calls out the stack-and-hot-cue inside one bar because it heard the bar. A coach that tells them the cut landed a beat early because it heard the beat.

That's what vibemix is. The whole product is engineered around one bar: *"does this feel like a real DJ friend in your ear, or does it feel like AI slop?"* If reactions are scripted, late, hallucinated, or generic, the product has failed regardless of how polished the rest looks.

---

## The four capabilities

### 1. Live co-host

The flagship surface. While a DJ plays, vibemix runs three grounding sources in parallel and speaks back into the headphones in real time.

- **Audio grounding** — Listens to the master output through a virtual audio device (BlackHole on Mac, WASAPI loopback on Windows). Hears every cut, every EQ move, every transition, every drop.
- **Screen grounding** — Watches the DJ software's window via screen capture. Reads the current track, the BPM, the key, the deck states, the cue points actually loaded on screen.
- **MIDI grounding** — Reads the DJ's controller directly over USB. Knows when the filter knob just swept, when the loop button was hit, when the crossfader moved.

These three streams feed a state-of-the-art multimodal model through Bravoh's proxy, and the reaction comes back as streaming TTS into the user's headphones — voice options range from calm to warm to gruff.

**Two modes, three skill levels, six distinct voices.**

| | Hype-man (party energy) | Coach (post-cue critique) |
|--|--|--|
| **Beginner** | *"Nice. You held the EQ steady through that intro."* | *"That cut was a beat off. Try waiting for the downbeat next time."* |
| **Intermediate** | *"Clean swap. Bassline locked."* | *"You're filtering on every transition. Mix it up — let one through dry."* |
| **Pro** | *"That was a stack and a hot-cue trigger inside one bar. Disgusting."* | *"You're hitting the same loop tool four tracks in a row. Crowd's reading it."* |

Each cell speaks a different vocabulary on purpose. Beginner is encouragement-heavy. Pro assumes the vocabulary. Coach mode is always past-tense — vibemix won't talk over a working DJ.

### 2. Vibe Library

A local-only search engine across the DJ's own music collection. The DJ types or says what they want, and vibemix finds the tracks in their library that actually fit.

- **Cross-modal search** — *"Find me something darker."* *"Something with more space."* *"Tracks that feel like the one I just played."*
- **Track-to-track similarity** — Point at any track in the library, get the closest neighbours by audio fingerprint, not by metadata.
- **100% local, 100% private** — Powered by an on-device CLAP audio model (a one-time ~785 MB download on first Library open). The DJ's library never leaves their machine.
- **Cue-anchored embeddings** — vibemix doesn't fingerprint the random middle of a track; it anchors on the mixable sections (intro, breakdown, drop, outro) so the similarity actually reflects what a DJ would mix.

Today: Rekordbox `collection.xml` ingest shipping. Serato and Traktor library ingest are next.

### 3. Set Builder ("Viber")

A grounded set-prep agent that turns a brief into a sequenced, harmonically valid set.

- **Discover** — The DJ describes the set ("warm-up into peak-time techno, 90 minutes, dark room"). Viber pulls a candidate pool from the DJ's own library using Vibe Library's engine plus hard filters on key, BPM, and energy.
- **Sequence** — Orders the pool along a chosen energy curve (warm-up, peak-time, closing, custom) with beam-search across a harmonic transition graph. Produces 3–5 diverse paths the DJ can compare.
- **Explain every transition** — Not a black-box recommendation. For each track-to-track move, Viber tells the DJ *why* — same key, key change with a Camelot wheel hop, BPM bridge, energy lift, vibe rhyme. The DJ learns by reading.
- **One-click export** — Writes the set straight back to a Rekordbox-compatible XML with the order, key/BPM/genre, memory cues, hot cues, and beatgrids preserved. The DJ opens rekordbox and the set is there, ready to play.

There's also an optional Telegram bridge so the DJ can ask Viber to curate a playlist from their phone while commuting, and find it ready on their laptop when they get home.

### 4. Beginner Module (v9.0, in build)

The next major release. An interactive teaching mode for someone who just bought their first controller.

- **Visual controller mirror** — The user's actual controller (one of the 10 mapped models) renders on screen at scale. The AI highlights the control to touch next. The user touches the physical control. The lesson advances. Every step is tied to the user's real hardware.
- **36 lessons across 3 courses** — *Anatomy of a Deck* (16 lessons, the controls themselves), *Transitions* (14 lessons, the mixing fundamentals), *Play Mode* (6 lessons + a proactive tutor lens that rides alongside a real set).
- **Library-driven exemplars** — When the lesson explains what the low EQ does, the AI plays a track from the user's own library that demonstrates it. They don't read about kick drums; they *hear* the kick drum drop out when the EQ sweeps.
- **The tone** — Friendly, confident, not condescending. The opening dialog is locked verbatim: *"Hello vibemix, what are you?" — "I'm the best DJ app in the world." — "If you are the best, then who the fuck am I?" — "Oh bestie, don't worry. You know why? Because I'm the beginner module of vibemix. Let's go."*

The Beginner Module turns vibemix from a tool DJs use into a path a non-DJ can walk to become one. It's also where partnerships with DJ schools and controller manufacturers make the most sense.

---

## The moat — citation grounding

The reason vibemix doesn't drift into AI slop is structural, not prompt-engineered.

Every reaction the AI tries to emit must cite real evidence — the audio chunk it analyzed, the MIDI event it just saw, the track name actually on screen, the cue point actually in the file. A central `EvidenceRegistry` keeps the registry of citable facts. If the AI tries to claim something it can't cite, the citation linter strips it down to a one-word acknowledgement before the user ever hears it.

That discipline is enforced at four points in the pipeline, locked in by tests, and held by four cardinal product invariants — the kind of thing a general-purpose LLM wrapper can't get to from clever prompting alone.

Layered on top of citation grounding:

- An anti-slop vocabulary blocklist that catches generic AI tells before they ship
- Past-tense framing for coach mode so vibemix never talks over a working DJ
- A `<silence/>` short-circuit token so the model can choose to say nothing
- Per-session anti-repetition so the same observation can't fire twice
- A hallucination verification gate (Kaan's personal ear-pass on real sets, ≥95% grounded reactions) that must pass before any release ships

This is the difference between "DJ tries it once, decides it's a gimmick, never opens it again" and "DJ keeps it open every set." The grading bar — *real friend in your ear, no AI slop* — is the only metric Kaan blocks releases on.

---

## Supported gear

### DJ software (works alongside, no integration needed)

rekordbox · Serato · Traktor · djay Pro · VirtualDJ · Mixxx

vibemix is app-agnostic by design — it listens to the master output, watches the screen, and reads the controller. If the audio routes through BlackHole on Mac (or WASAPI loopback on Windows), vibemix can co-host it.

### Controllers with out-of-the-box mappings (10)

Pioneer DDJ-FLX4 · Pioneer DDJ-FLX6 · Pioneer DDJ-FLX10 · Pioneer DDJ-400 · Pioneer DDJ-1000 · Pioneer DDJ-SX3 · Pioneer XDJ-RX3 · Numark Party Mix Live · Hercules DJControl Inpulse 300 · Hercules DJControl Inpulse 500

Anything else uses a generic positional fallback, and a contributor recipe (`scripts/sniff_controller.py` + a JSON profile) ships new mappings via PR. CI auto-merges clean profile additions.

---

## Privacy & data

Stated plainly because partners ask:

- **Live co-host** streams audio + screen + MIDI through Bravoh's proxy at `api.bravoh.ai`, which forwards to our hosted AI model. **No raw audio is stored on Bravoh's servers.**
- **Vibe Library and Set Builder** run 100% locally. The DJ's library never leaves their machine.
- **Recordings** stay on the DJ's machine under `recordings/<session>/` with a 7-day default retention, configurable to anything from 1 day to forever in Settings.
- **No telemetry by default.** Anonymous crash reports are opt-in via the first-run wizard.
- **BYO-key path** — A DJ who doesn't want to use Bravoh's proxy can point vibemix at their own model-provider API key via env var. The Apache 2.0 license makes a private fork trivial.

The full disclosure (`SECURITY.md` in the repo) covers responsible disclosure, threat model, and the proxy's role.

---

## Platforms & install

- **macOS Apple Silicon** — signed and notarized, shipping today via DMG.
- **Windows 11** — ships with v0.1.0 stable. Signing approval through SignPath's OSS program is in flight.
- **Linux** — explicitly out for v1. djay Pro is Mac/Win only; the Linux loopback stack (PulseAudio / PipeWire) triples the platform layer's maintenance cost. Open to a community PR.
- **License** — Apache 2.0. Fork it, point it at your own key, ship it inside something else. We're fine.

Auto-update is on by default for release builds; opt out in Settings.

---

## Where this is going

Confirmed for v2 and beyond, in rough priority order:

1. **Beginner Module ship** (v9.0, in build now) — the teaching surface; the natural integration point for controller manufacturers and DJ schools.
2. **Serato + Traktor library ingest** — close the parity gap with rekordbox.
3. **Mixxx OSC integration** — direct deck-state read instead of screen-vision inference; the open-source community asked.
4. **Pioneer Pro DJ Link** — direct hardware deck-state read for CDJ/XDJ users (probe in flight; conditional on real hardware availability).
5. **Auto-cue engine** — server-side CUE-DETR + downbeat detection that labels phrase structure (intro / build / breakdown / drop / outro) for every track in the library. Currently the best-in-class research model run on Bravoh infrastructure.
6. **Memory copilot** — vibemix remembers past moments from a DJ's sessions and grounds future reactions in them ("you ran this build longer last time too"). Engineering-complete, gated off until a Kaan ear-pass.
7. **OBS browser-source overlay** — the mascot renders as a transparent overlay inside OBS scenes for streaming DJs. Shipped; underused.

Out of scope on purpose: stem separation, multi-provider AI, enterprise dashboards, social/community feeds. vibemix optimizes for the minimum useful surface.

---

## Built by Bravoh

[Bravoh](https://bravoh.ai) is the AI creative team for music artists — four AI-powered agent personas that help artists with creative direction, marketing, production, and release strategy. **Currently in closed beta.**

vibemix is Bravoh's first open-source release. It's not a side project — it's the warm-up. A polished, narrow-scope utility for a community Bravoh wants to be trusted by. Every DJ who installs vibemix is one who'll be on the Bravoh waitlist by the time the closed beta opens.

The target for vibemix on its own: 500–1,000+ GitHub stars at launch, a working installed base across rekordbox / Serato / Traktor users, and a Discord community of DJs giving real feedback against real sets.

---

## Where partners fit

Four shapes of partnership we're actively looking for:

**Controller manufacturers** — Official sign-off on the bundled mapping for your hardware. Co-branded launch around the Beginner Module (the controller you make is the controller the user sees on screen). Joint content for the DJ-school channel.

**DJ software vendors** — Deeper integration than the audio + screen + MIDI grounding floor. OSC, direct library access, native co-host surface inside your app. Mixxx is the obvious open-source candidate; everyone else is a conversation.

**DJ schools and educators** — The Beginner Module as a teaching surface. Branded curriculum slots. Real beginners walking the 36 lessons before they ever sit at a real club setup. A measurable funnel from "first time touching a controller" to "first set played."

**Distribution, community, press** — Discord, festival activations, influencer DJs running vibemix on real sets, write-ups in DJ media. The product is at its most shareable when an actual DJ is using it in an actual room.

If you want a private demo on real hardware — Pioneer DDJ-FLX4, rekordbox, Mac — Kaan can run it for you on a call or in person.

---

**Contact**

- **Kaan Özkan** — co-founder, engineering, product. `kaan@bravoh.ai`
- **Francesco Fasanella** — co-founder, product, marketing, partnerships. `francesco@bravoh.ai`
- **Repo** — `github.com/bravoh-ai/vibemix` (release pinned in Releases tab)
- **Bravoh** — [bravoh.ai](https://bravoh.ai)
