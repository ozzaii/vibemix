# Feature Research — v9.0 "Lesson One" (Beginner Learning Module)

**Domain:** Hardware-aware, library-grounded, AI-mentored beginner DJ instruction (3 progressive courses) layered onto vibemix's existing live co-host stack.
**Researched:** 2026-05-27
**Confidence:** HIGH on canon (curriculum order, EQ pedagogy, phrase counting, transition taxonomy, common mistakes — 4+ sources each agree). MEDIUM on AI-tutor tone (Khanmigo/Duolingo are the closest precedents but not DJ-specific). MEDIUM on the EQ-as-tutor demo (the technique exists pedagogically in every EQ guide, but no shipped product wires "AI plays the exemplar from YOUR library and grounds you on the right knob"). LOW on the third-course live-coaching surface (PulseDJ and Harmovio claim adjacent capability but are reactive recommenders, not proactive tutors with a count-in voice).

**Default-YES rule applied** (Kaan: "fully comprehensive for every beginner DJ"): when canon names a skill or concept and at least one trustworthy source recommends it for beginners, it is admitted as a candidate lesson. Anti-features are the *short* list and carry explicit reasoning. The roadmap stage will cut, not this file.

**Source canon used** (every lesson back-referenced to at least one of these):
- Digital DJ Tips / Phil Morse — "Rock The Dancefloor" 5-step formula + Complete DJ Course (8 modules / 70+ video lessons) → the most-cited DJ pedagogy source on the public web; gear → music → mixing → performing → success.
- Crossfader — free 9-lesson Complete DJ Course + per-controller paths (Denon DDJ-FLX2 etc).
- Pioneer DJ + rekordbox "Tutorial Mode" (DDJ-400 / DDJ-FLX4 / FLX2 / WeDJ) — manufacturer-blessed in-software curriculum.
- DJ TechTools — phrasing 101, gain-staging, waveform reading, DDJ→CDJ progression.
- Mixed In Key — Camelot wheel, harmonic mixing, visualize-the-structure book chapters.
- Beatport / Beatportal — "10 Lessons Every DJ Should Know."
- DJ.studio blog — 16 basic transitions, mixing fundamentals.
- ClubReady DJ School — "7 common beginner mistakes," EQ vs faders, booth output, bass-swap pitfalls.
- Beatmatch Guru, DJfuturo — phrase counting + bars.
- DJ Mentors / SpinStart / DJ Shortee / Mixcloud Blog / Midnight Rebels — sync-vs-beatmatch modern consensus.
- Serato Practice Mode + Native Instruments Maschine tutorials + Pioneer DJ Pete Tong DJ Academy — vendor-blessed practice paths.
- Khan Academy Khanmigo + Duolingo voice guidelines — AI-tutor tone canon.
- WCAG 2.2 / Section 508 — dual-cue accessibility for color-blind users.
- PulseDJ / Harmovio — current AI-DJ-copilot prior art (so vibemix knows what's already claimed).

---

## Course Architecture (the v9.0 Skeleton)

Kaan's brief explicitly named three courses; pedagogy canon supports this trichotomy (Phil Morse's Mixing Part 1 = "universal skills regardless of hardware" + Part 2 = "performing the mix on the floor"; rekordbox Tutorial Mode's progression = pad/cue mechanics → transitions → drop-mix performance).

| Course | Codename | What the user *can do* by the end | Phase analog in canon |
|--------|----------|-----------------------------------|----------------------|
| **Course 1: Anatomy** | "Know Your Gear, Know Your Song" | Identify every fader/knob/button on their controller; count bars; spot intro/breakdown/drop/outro by waveform AND by ear; load tracks; pre-cue in headphones; hold safe gain staging. | Phil Morse Step 1 (Gear) + Step 2 (Music) + Crossfader free Lessons 1-3 + rekordbox Tutorial Mode "Basic Operation." |
| **Course 2: Transitions** | "From Two Tracks To One Mix" | Beatmatch by ear + verify with sync; execute the five canonical transitions (long blend, EQ swap, bassline swap, echo-out, filter-fade); mix two tracks in compatible key/BPM end-to-end; identify a train wreck and recover. | Phil Morse Step 3 (Mixing Part 1) + DJ.studio "16 basic transitions" + Mixed In Key Camelot intro + Beatport "10 Lessons" #3-7. |
| **Course 3: Play-mode** | "You DJ, vibemix Watches" | Play a 30-minute beginner set under live proactive AI coaching: count-ins, "start your incoming track in 16 bars," "kill the lows at the kick," crowd-energy reads, recovery drills. | Phil Morse Step 4 (Performing) + Crossfader "extended sets" + DJ TechTools "controlling-the-dancefloor" + Practice Mode (Serato) ethos. |

**Why this order is canonical:** Every source surveyed orders fundamentals → mixing mechanics → performance. Phil Morse: *"start with gear and music because everything else fails without them."* Beatportal #1 of the "10 Lessons" is *music structure & theory.* Crossfader's free course opens with *"What is a DJ controller / what do the buttons do?"* before touching the crossfader. The only deviation worth flagging: DJ TechTools' "DDJ to CDJs" essay argues Pioneer hardware-mode literacy should come earlier — vibemix's hardware-aware approach already does this by mirroring the user's actual MIDI controller from lesson 1.

---

## Feature Landscape

### TABLE STAKES (Course 1 — Anatomy of the Gear & Song)

> Every source we surveyed names these as the must-have foundations. Missing any of these = "this is not a comprehensive beginner module." Each is wired through the user's actual MIDI controller from `src/vibemix/midi/profiles/*.json` (10 controllers shipped). Complexity ratings reflect engineering effort *given the existing vibemix stack* (CLAP library + MIDI ingest + EvidenceRegistry grounding + Tauri UI all exist).

| Lesson ID | Lesson Title | Why Table Stakes | Complexity | Notes |
|-----------|-------------|------------------|------------|-------|
| **L1.01** | **"What Is A DJ? — The Opening Dialog"** | First-run trust ritual; sets the persona; defuses gatekeeping anxiety ("if you're the best who the fuck am I"). Kaan's verbatim vision. | LOW | Single scripted exchange; gates "Start Course 1" button. See §Tone Calibration for the bestie-line decision. |
| **L1.02** | **"Meet Your Controller"** | Every canonical curriculum opens here (Crossfader Lesson 1, Phil Morse Step 1 / "Gear" module, Pioneer rekordbox Tutorial). Without this the AI can't reference specific knobs. | MEDIUM | Hardware-mirror UI (`tauri/ui/` renders the user's exact controller from `midi/profiles/`); annotated highlight overlays on the rendered controller (decks A/B, mixer section, crossfader, jog wheels, pads, performance controls). |
| **L1.03** | **"The Channel Strip" — Fader, Gain, EQ Hi/Mid/Low** | Sweetwater + DJfuturo + DJ.studio + Phil Morse all begin Module 1 here. The channel strip is the atomic unit of every DJ mixer. | MEDIUM | Each control highlighted in turn; AI explains what it does; user moves it; AI confirms the MIDI event landed. |
| **L1.04** | **"The Crossfader — Left, Right, Middle"** | Universally named. DJ.studio: "moving left and right transitions from one source to another, either lightning quick or gradually." | LOW | Highlight on rendered controller; user sweeps; gate on full sweep observed on MIDI CC 31 (FLX4 example). |
| **L1.05** | **"The Pitch / Tempo Fader"** | Universal. ±6%/±8%/±16% range explainer (canon: most controllers ±8%, stay under ±6% for natural pitch). | LOW | User nudges; AI shows live BPM delta calculated from CC value × range × track BPM. |
| **L1.06** | **"Play, Cue, Sync — The Transport Buttons"** | Universal. Pioneer DDJ-400 Tutorial Mode names these first three pad-mode behaviors. | LOW | Play A/B, Cue A/B, Sync A/B — three button events; profiles already mapped (notes 11/12/96 on FLX4). |
| **L1.07** | **"The Jog Wheel — Nudge, Pitch-bend, Search"** | Mixed In Key, DJ TechTools, every Pioneer tutorial. Jog-touch already mapped (note 54 on FLX4). | MEDIUM | Three discrete sub-modes; only the nudge sub-mode is required at beginner level (the scratch sub-mode is anti-feature — see §Anti-Features). |
| **L1.08** | **"Headphone Cueing — Hearing The Next Track Privately"** | Cue button universally named as foundational by all sources (English DJ in France Lesson 5, Rane support, Algoriddim, Best DJ Tips, DJfuturo Lesson 9). Without cueing, the user cannot beatmatch. | MEDIUM | Requires audio routing UX (already exists in vibemix; rebind for headphone preview); split-cue explainer optional. |
| **L1.09** | **"The Master / Booth / Headphone Volumes — And The Red Zone"** | DJ TechTools "Gain Staging For DJs + Staying Out Of The Red" + DJ Times "Cringe-Worthy Habits Of DJs." Beginners blowing levels = #2 most-cited gear mistake. | LOW | Visual meter mirroring the existing CDJ-Whisper amber meter; lesson gate = "keep peaks in green/amber, never red for 8 bars." |
| **L1.10** | **"The Anatomy Of A Song — Intro, Breakdown, Drop, Outro"** | Mixed In Key's "Visualize The Structure Of Dance Music" entire book chapter + Cymatics + Unison + Beatportal #1. Without this nothing else in DJing makes sense. | MEDIUM | AI plays a track from the user's library (or a curated demo if library empty), annotates the waveform with phase chips (existing `state/event_detector.py` already emits PHASE events). Mixed In Key ABAB notation explained. |
| **L1.11** | **"Counting Bars — 1, 2, 3, 4 / 2, 2, 3, 4 ..."** | DJ TechTools "How to DJ 101: Why You Must Understand Phrasing" (universally cited), Beatmatch Guru, DJfuturo Lesson 4, Steemit "Most Important Skill To Develop." Eight bars = 32 beats = phrase. | MEDIUM | AI counts along (TTS-cadenced) over a 32-bar loop from the user's library; user taps a key/pad on each "1"; gate = ≥7/8 phrase-starts hit within ±100ms. |
| **L1.12** | **"Spotting The Breakdown By Ear"** | Mixed In Key + every electronic music structure article. The single most important phrase boundary because it announces "the drop is coming, the dance floor will detonate." | LOW | AI plays a track, asks "raise your hand when you hear the breakdown" (= press play/cue/any pad). Phase events from `MusicState` are the ground truth. |
| **L1.13** | **"Spotting The Breakdown By Eye (Waveform)"** | DJ TechTools "Reading Wave Forms" + Core Mixing "How to Read DJ Waveforms" + Serato Support docs. The waveform-vs-ear dual literacy is canonical. | MEDIUM | Renders a real track's three-band-colored waveform (Serato/Pioneer-style: red=low, green=mid, blue=high or equivalent). User clicks where the breakdown is; checked against `event_detector.py` PHASE boundaries. |
| **L1.14** | **"The EQ Demo — Highs, Mids, Lows ARE Different Things"** | Kaan's signature vision lesson: "Plays a breakdown of a song that has highs or mids or vocals... as user increases it really goes higher." Industry canon: every EQ tutorial (Crossfader, Pirate.com, Songstuff, Ten Kettles) teaches the bands as 20-200Hz / 200Hz-5kHz / 5-20kHz. | HIGH | The "EQ-as-tutor demo" — see dedicated §EQ-as-Tutor design block below. AI must pick library tracks where the band-isolation demo is *audible* (vocal-heavy for mid, kick-heavy for low, hi-hat-heavy for high). |
| **L1.15** | **"Loading Your First Two Tracks"** | Phil Morse Step 2 (Music). Every tutorial bridges anatomy → mixing here. | LOW | Library picker pre-filtered to BPM-compatible candidates (vibemix's `library/` already has this); explicit instruction to pick tracks ±6% BPM apart and Camelot ±1. |
| **L1.16** | **"Course 1 Recital — Pre-cue and play"** | Every course's first capstone. Crossfader Lesson 3, Beat Refinery, all assess: load → preview in headphones → start at the right time. | MEDIUM | Gate-on-completion drill: load track A, pre-cue, play; load track B, pre-cue, identify its first downbeat. No transition yet. |

### TABLE STAKES (Course 2 — Anatomy of a Transition)

> The five canonical transitions in canonical pedagogical order (cross-checked against DJ.studio, Crossfader, Digital DJ Tips, Mixgraph, Native Instruments blog, ZIPDJ "Top 5 Easy DJ Transitions To Learn In 2026," DJingPro). All sources converge on this taxonomy and largely on this order.

| Lesson ID | Lesson Title | Why Table Stakes | Complexity | Notes |
|-----------|-------------|------------------|------------|-------|
| **L2.01** | **"Beatmatching By Ear" — Manual** | Modern consensus (DJ Shortee, Midnight Rebels, SpinStart, Mixcloud Blog March 2026): teach manual *and* sync — manual is the ear-training crucible; sync is the everyday tool. Skipping manual produces DJs who can't recover when sync misreads BPM. | HIGH | AI gives the user two BPM-close tracks, mutes sync, narrates the "this one is faster/slower than the other" feedback as it reads tempo deviation. Gate = user holds two tracks beat-in-sync for 32 bars manually. |
| **L2.02** | **"Beatmatching With Sync" — When And Why** | Modern consensus (2025-2026): sync is industry-standard hardware; the gatekeeping is dead. Mixcloud Blog: *"sync lowers the barrier so beginners can focus on phrasing, energy, storytelling."* | LOW | Toggle sync on, demonstrate, then critically: "now you have one less thing to worry about — but never trust it blindly because beatgrids can be wrong." |
| **L2.03** | **"Long Blend / Slow Mix" — The First Transition Beginners Learn** | DJ.studio's #1 beginner transition. Crossfader, Beatport, Phil Morse all open with this. Trades drums then bass then melody over 32+ bars. House DJ default. | MEDIUM | Two-track scaffolded drill; AI prompts each step ("now bring up the channel fader to 50% — wait for the next phrase"). Live MIDI events checked against the script. |
| **L2.04** | **"EQ Swap" — The Foundation Of Clean Mixing** | EVERY source. Crossfader: "the second most important transition tool." Skilz DJ Academy + Pirate.com: standard EQ-blend protocol — lows out on incoming, highs at noon, gradually bring in mid then low while cutting outgoing low. | MEDIUM | Drill: at a phrase boundary, swap the lows; gate = mid/low cut on incoming until the drop, then full swap. |
| **L2.05** | **"Bassline Swap / Kick Swap" — When The Kick Hands Off** | DJ.studio, DJingPro, ClubReady DJ School "Bass Swapping" all teach this as Transition #2. The frequency where mixes go "muddy" lives in the lows; one kick at a time, always. | MEDIUM | Built on L2.04; specifically times the lows-swap to a kick downbeat. |
| **L2.06** | **"Filter Fade" — The Lazy Hero Transition** | DJ.studio, DJingPro, Crossfader's "12 high-energy transitions." Easy because filter is forgiving. | LOW | Bipolar filter knob (FLX4 CC 23/24) sweep; HPF on outgoing as LPF on incoming. |
| **L2.07** | **"Echo-Out / Echo-Tail" — The Bail-Out Transition** | TikTok @nextdimensional + Digital DJ Tips: "super easy for beginners with only a laptop or basic controller — you can do this with no beatmatching or phrase matching." The transition for "I just need to swap genres/BPMs and survive." | LOW | Trigger echo on outgoing, pause it, start incoming on the echo tail. Cross-genre and cross-BPM safe. |
| **L2.08** | **"Drop Swap" — Hit The Drop Together"** | Pioneer DDJ-400 Tutorial Mode official curriculum (drop mix, drop swapping). High-energy genres (festival house, EDM, big-room techno) standard move. | MEDIUM | Beatmatch + queue both tracks to the same phrase-start; play both, kill outgoing right at the drop. |
| **L2.09** | **"Loop Transition" — Buy Yourself Time** | DJ.studio, Crossfader looping guide, BPM Music blog. Looping the outro lets the beginner DJ catch up — a confidence-builder. | MEDIUM | Set 4/8/16-bar loop on outgoing at end of phrase; bring in incoming under the loop. FLX4 loop_in/loop_out (notes 16/17). |
| **L2.10** | **"Hot Cues & Memory Cues" — Mark Your Map** | Crossfader "Hot Cues Complete Guide," Pioneer DJ forums, DeeJay Plaza, every DDJ Tutorial Mode lesson. Without cues, beginners cannot reliably hit the right phrase-start. | MEDIUM | Drill: set a hot cue at the breakdown of one of *the user's* tracks; recall it. (`pyrekordbox` already imports cues in vibemix.) |
| **L2.11** | **"Harmonic Mixing 101 — The Camelot Wheel"** | Mixed In Key's wheel + every modern DJ curriculum since 2010. vibemix has `harmonics.py` (Camelot conversion already shipped). | MEDIUM | Visual Camelot wheel; AI explains "same number = same key, different mood; ±1 number = adjacent gear"; AI suggests two harmonically-compatible tracks from the user's library. |
| **L2.12** | **"Phrase Matching — Don't Just Beatmatch, Phrase-match"** | DJ TechTools "Why You Must Understand Phrasing": beatmatching without phrase awareness is the train-wreck-on-time mistake. | HIGH | Builds on L1.11; drill = "press play on track B such that its phrase-1 lines up with track A's phrase-9-start." Hard. Gate is generous (±2 bars). |
| **L2.13** | **"Diagnosing a Train Wreck"** | DJ.studio "How Pro DJs Use Waveforms," ClubReady "5 Mistakes Beginners Make," every "common mistakes" article. The recovery drill is what separates beginners from intermediates. | MEDIUM | AI intentionally mis-syncs and asks "what's wrong — too fast, too slow, or off-phrase?" |
| **L2.14** | **"Course 2 Recital" — Two Tracks, One Clean Mix** | Every course's mid-capstone. | MEDIUM | User executes a single full transition (their choice of L2.03-L2.09); AI grades against the L2.x protocol; replayable. |

### TABLE STAKES (Course 3 — Play-mode with Proactive AI Co-pilot)

> Kaan's verbatim vision: "vibemix is alongside them giving feedback — it can see the future of the song. It can suggest user stops the track, tells the user 'at this point enter track 2, start increasing the crossfader, start blending in the mids and lows.'" This is the differentiator surface — see §Live Coaching Co-pilot for the design.

| Lesson ID | Lesson Title | Why Table Stakes | Complexity | Notes |
|-----------|-------------|------------------|------------|-------|
| **L3.01** | **"Your First 5-Minute Mix" — Two Tracks, Recorded** | Beatport "10 Lessons" #10 (live performance); Phil Morse Step 4 (Performing). Recording = the single best way to improve (DJ TechTools, Digital DJ Tips: "Recording Your Sets: The Single Best Way To Improve Your DJing"). | MEDIUM | AI announces phase boundaries 8/4/2/1 bars out; user executes; session recorded to existing `recordings/` dir; debrief surface auto-opens (v2.1 debrief UI already exists). |
| **L3.02** | **"Your First 15-Minute Set" — 4-5 Tracks, AI Guides You** | Phil Morse / Crossfader extended-set lessons. Critical jump from "one transition" to "actual DJ set." | MEDIUM | AI prepares the playlist (uses v8.2 Build-a-Set engine), then live-coaches each transition in turn. |
| **L3.03** | **"Reading The Room (Even When Your Room Is Empty)"** | Relentless Beats, Hercules, City Nights Disco, PCDJ Crowd-Reading 101, Beatportal "Behind the Booth." The pedagogy of energy arcs over peak-hammering. | LOW | Conceptual lesson + simulated energy-meter drill ("don't peak until minute 8"); AI references the user's energy curve via existing `MusicState`. |
| **L3.04** | **"Your First 30-Minute Set" — Course 3 Final, Live AI Beside You** | Phil Morse "Rock The Dancefloor" graduation drill; Crossfader complete-course capstone. | HIGH | The capstone. Live proactive co-host: count-ins, "drop the lows on the kick," "stop touching the master fader," "great breakdown call." Session recorded; debrief flags + commendations posted. |
| **L3.05** | **"Recovery Drills" — Surviving Mistakes In Public** | Common-mistakes canon (ClubReady, The DJ Revolution, Ghost Production): every beginner train-wrecks; the difference between a beginner and an intermediate is recovery. | MEDIUM | AI intentionally induces controlled mis-syncs ("oops, your sync just lied — what now?"); user must catch with manual nudge + jog. Gate = recovery within 4 bars. |
| **L3.06** | **"Your DJ Profile — What You've Learned"** | Profile already exists (`src/vibemix/profile/`). After Course 3 graduates the user out of "beginner module." | LOW | Reuses existing long-term DJ profile (v2.1). Tracks lesson-by-lesson mastery, opens differentiator content (intermediate path, library curation, building sets). |

### DIFFERENTIATORS (Where vibemix Owns Beginner-DJ Pedagogy)

> Features no other DJ course has — these are the moat. Each ties directly to vibemix's existing infrastructure (CLAP library, MIDI, EvidenceRegistry, Build-a-Set engine, live grounded co-host).

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **EQ-as-Tutor Demo (L1.14)** | The "highlight section of deck 1/2 + play the relevant track segment + prove what each knob does using the user's OWN library" — exists nowhere shipped. PulseDJ recommends tracks; Harmovio detects phrases; rekordbox Tutorial Mode highlights pads. None play a vocal-heavy clip from *your* music and gate on you turning the mid knob. | HIGH | See §EQ-as-Tutor design block. Library-grounded (CLAP picks vocal-heavy / kick-heavy / hi-hat-heavy tracks); MIDI-grounded (gate on actual knob movement); falls back to a curated demo track when library is too small. |
| **Hardware Mirror UI With Live Highlights** | Native Instruments Maschine, Ableton Push, Serato Practice Mode, rekordbox Tutorial Mode all do *some* version of this — but none mirror *the user's actual controller* (10 profiles shipped). The AI says "press the play button on deck A" → the rendered controller's exact play button lights amber + the user's real button is what arms the gate. | HIGH | Lift mock pattern from `mocks/vibemix-rebuild-session.html`. Annotation JSON schema: `{"deck": "A", "control": "play_a", "highlight": "primary"\|"secondary"\|"path", "label": "Press play"}`. Renderer per profile in `tauri/ui/`. |
| **Library-Grounded Exemplars** | Every demo, every "listen to this track and notice the mid" plays a track *from the user's library*. Empty library = curated CC0/Apache-clean fallback (3-5 demo tracks shipped). | MEDIUM | CLAP library already shipped; reuse `library/next_suggestion.py` mean-centered matcher to pick tracks fitting an "exemplar brief" ("vocal-heavy, mid-band-dominant, breakdown at bar 33"). |
| **Live Proactive Co-pilot (Course 3)** | "I can see the future of the song" — vibemix already has 3-second lookahead (Phase 40 / AUDIO-02). Tutor mode pivots it from reactive to proactive: count-in voice prompts BEFORE phrase boundaries, BEFORE the drop. PulseDJ/Harmovio recommend tracks; they don't say "in 8 bars, drop the lows." | HIGH | Builds on `event_detector.py` phase prediction + the FLEX-routed Gemini TTS path; new "tutor-lens" persona in `coach/`. See §Live Coaching Co-pilot. |
| **Adaptive Pacing — No Time Pressure** | Khanmigo precedent: "guides students to discover answers, asks probing questions, no shaming." vibemix lessons never time out; mastery-gate not clock-gate. | LOW | UI choice; no new code. |
| **"Show Your Receipt" Citation Grounding (Course 3 feedback)** | Cardinal Invariant #2 already enforces this. When tutor says "great mid kill at bar 33," the assertion is registered in EvidenceRegistry; if grounding fails, the line strips. No fake praise. | LOW | Reuse `evidence_registry.py`; new evidence sources: `lesson_step_observed:<L_id>:<event>`, `mid_knob_moved:<target_value>:<tolerance>`. |
| **Per-Controller Mapping Confidence** | If the user's controller isn't one of the 10 mapped, lessons that need a specific CC fall back to generic + the user manually-identifies their knob. Honest, not silent. | MEDIUM | `midi/profiles/__init__.py` already returns `None` on unknown; UI shows "we don't fully recognize your gear — point at the mid knob." |
| **Lesson Replay With Debrief Surface** | v2.1 debrief UI exists. Lessons auto-replay with the AI commenting on the user's actual MIDI events frame-by-frame. | MEDIUM | Reuse port 8766 / debrief WebviewWindow. |
| **Personality Calibration — Beginner Lens** | vibemix already ships 3 user-levels (Beginner / Intermediate / Pro) with persona prompts. Course 3 specifically wires the tutor lens (already shipped in v8.1) to the lesson context. | LOW | Already wired; new `tutor_lesson_<L_id>` context tags. |
| **Multi-language (English + Italian + Turkish)** | Bravoh team is Italian; Kaan is Turkish. Beginner content lives or dies on idiomatic warmth. | MEDIUM | Gemini Flash TTS already supports en/it/tr; prompt templates and lesson scripts need parallel localization. Closed-beta English-first, then it/tr (Bravoh i18n pattern). |
| **Hardware-Free "Explore" Mode** | A pre-controller user can still walk through Course 1 anatomy lessons using keyboard mappings (also useful as accessibility — see §Accessibility). Demonstrates "this is what DJing IS" before commitment. | MEDIUM | Generic profile maps PC keys to controls; `midi/profiles/keyboard.json` new. |
| **Real-Hardware Drift Auto-Detection** | If MIDI hot-plugs mid-lesson, lesson re-binds; if user buys a new controller, the same lesson re-renders against the new hardware. | LOW | `midi/profile_loader.py` already does port-name matching; add lesson re-bind hook. |
| **"Listen with me" passive lessons** | Mixed In Key's "Visualize the Structure" book chapter is *passive* (read the waveform, no touching). Some beginners need ear-only sessions first. | LOW | Lessons L1.10, L1.12 already this. |
| **Per-Genre Beginner Paths** | "I want to be a wedding DJ" vs "I want to play techno" branch from a shared L1 trunk. Wedding DJ canon (extensive MC/announcement, mic skills, multi-genre selection); techno canon (long blend, EQ-melt, single-genre depth). vibemix's `state/genre/` already detects which genre a user plays. | HIGH | Defer to v9.1+: ship a single beginner path first, fork by elective once we have telemetry on which way users go. |

### ANTI-FEATURES (Defensible Excludes)

> Things every beginner DJ might *think* they want, that canon says do not belong in a beginner module. Each carries the "alternative" so the user isn't dead-ended.

| Anti-Feature | Why Beginners Ask | Why It's Problematic | Alternative |
|--------------|-------------------|----------------------|-------------|
| **Scratching lessons** | Hip-hop visibility; "this looks cool." | Universally treated as a separate art form (DJ TechTools, Crossfader, Digital DJ Tips, Studio Scratches, ZIPDJ "Basic Scratching Techniques"). Skill ceiling is months-to-years; cannot be faked. Belongs in a separate "Scratch DJ" course module (v9.x or v10+). | Link to canonical scratching primer (Crossfader / Studio Scratches) in the "What's Next After Course 3" surface; don't gate any beginner credit on scratching ability. |
| **Mashups / live remixing / stem separation** | TikTok visibility; "AI DJs do this." | Beyond beginner mastery curve; depends on intermediate transition technique + library prep + stem-engine deps (Demucs/Spleeter not in vibemix's scope per CLAUDE.md "no scope creep" rule). | Defer to a future "Creative DJ" module; surface PulseDJ/djay Pro as adjacent tools. |
| **Production / sample-making / DAW lessons** | "DJs make music." | Different craft entirely; Bravoh's main product addresses production. | Bravoh waitlist (existing v3.0 hook). |
| **Theory-heavy music theory** | "Understanding music makes you better." | Camelot wheel is the *exact* amount of theory canonical pedagogy says a beginner needs (Mixed In Key, the entire harmonic-mixing literature). More music theory = different course. | L2.11 (Camelot 101). |
| **Lecture-only video lessons** | "YouTube does this." | The whole vibemix differentiator is hardware-aware live interaction. If we ship 70 video lessons, we are Phil Morse, not vibemix. | Every lesson is interactive; the AI talks while the user is invited to *act*. |
| **"Practice with virtual hardware" mode (no controller required, ALL lessons)** | Lower barrier; "I don't have a controller yet." | Conflicts with the core differentiator (your real hardware is the instrument). | "Explore" mode covers L1 anatomy only; L2+ require a MIDI controller (one of 10 supported, or a generic-MIDI fallback). Make the controller requirement explicit at sign-up; defer the controller-free option to v9.1+ if telemetry justifies. |
| **Live online classroom / multi-user lessons** | "Learn with friends." | Out of scope for a local-first app; concurrency, moderation, infra. Bravoh is the multi-user surface. | Single-user only in v9.0; if Course 3 recordings can be shared (export → upload manually to Mixcloud etc), that's enough social. |
| **Beat-matching by jog wheel only (no sync teaching)** | Vinyl-purist gatekeeping. | Industry consensus 2025-2026 explicitly rejected this (DJ Shortee, Mixcloud Blog, DJ Mentors): teach both. | L2.01 (ear) + L2.02 (sync) side-by-side. |
| **"DJ business" lessons** (booking, fees, contracts, social media) | Phil Morse Step 5 (Success). | This is for someone who has *finished* a beginner module; off-mission for v9.0. | Surface link to Phil Morse Step 5 / Crossfader business modules from the Course-3-graduation screen. |
| **Wedding-DJ MC scripts / formal-event timeline coordination** | Practical career path. | High-context, scripted-event domain; not the "real DJ friend in your ear" vibe. Wedding DJs need binders, not vibes. | Defer to specialized v9.x branch IF telemetry shows wedding-DJ user base; otherwise leave it to dedicated wedding-DJ schools. |
| **Voice-coached scratching / drum & bass technical mixing** | Skill-curiosity. | Belongs in genre-specialty modules (v10+). | "What's next" surface. |
| **Real-time critique of *creative* taste** | "Tell me if my track choice is good." | The AI grounds on TECHNIQUE (was the transition clean? did you kill lows on the kick?). Critiquing taste = paternalism / generic-AI-slop risk that violates vibemix's core principle. | Tutor reports facts ("you played 5 tracks at the same BPM for 20 minutes — try a small change next time"); never says "your music sucks." |

---

## EQ-as-Tutor Demo (L1.14) — Design Block

This is the load-bearing differentiator lesson. Detailed spec because the roadmap will need to feasibility-gate this against the existing CLAP + library + grounding stack.

**Brief:** "When I increase the mid knob, the melody/vocals go up. AI proves this by playing a track from MY library where the mid band is dominant, plays a few seconds, asks me to turn the mid knob, confirms my movement on MIDI, plays the change."

**Step-by-step:**
1. AI says: "Let me show you what the MIDS knob does. The mids are the body of music — vocals, melody, hi-mid percussion."
2. AI picks a track from the user's library where the mid band is dominant in a breakdown or come-up (CLAP can be coaxed via mean-centered query for "vocal heavy / melodic / mid-rich"; fallback to canonical demo track).
3. AI plays 8-16 bars on deck A.
4. The hardware-mirror UI highlights the MID knob on deck A in amber.
5. AI says: "Try cutting the mids — turn this knob to the left."
6. User turns the knob. MIDI CC 11 ch 0 (FLX4 example) updates `MusicState.deck_A.eq_mid`.
7. AI says: "Hear how the vocals disappeared? You've removed the 'body' of the track. The kick and hi-hats remain because they're in the lows and highs."
8. Reverse the demo: bring mids back, then cut highs (hi-hats vanish), then cut lows (kick vanishes).
9. Lesson gate: user moved each of the 3 EQ knobs at least once with the AI's narration tracking.

**Per-band exemplar selection (CLAP-grounded, mean-centered query):**
- **Mid demo** → vocal-heavy / breakdown-with-vocal-stem-up tracks. Easy to source.
- **Low demo** → kick-driven techno / house with clean low end. Easy.
- **High demo** → tracks with prominent hi-hats, shakers, cymbal-driven percussion (deep house, breakbeat). Slightly harder; CLAP can do it but the published Bravoh CLAP-text-to-audio caveat applies — fallback to a known demo.

**Published pedagogical risk (canon agrees):** the high-band demo is the weakest. Hi-hats are perceptually masked easily; users may not hear the change. Mitigation: pick tracks with prominent claps/shakers in the 5-10kHz region; cut more dramatically; or use the master-output amber-meter to *visualize* the cut alongside the audible change.

**Fallback:** ship 3-5 demo tracks (CC0 / Apache-clean / commissioned) baked in for the case where the user's library is empty or doesn't yield good band-isolated exemplars. Storage: ~30MB acceptable per Inno Setup / DMG audit (v3.1 audit allows; check `docs/AUDIT.md`).

**Prior art check:** No shipped product does this (verified by canvassing rekordbox Tutorial Mode, Serato Practice Mode, NI Maschine tutorials, Mixed In Key tutorials, every DJ-academy curriculum). EQ tutorials exist universally as text + video; the "AI gates on YOUR knob using YOUR track" pattern is genuinely novel.

---

## Live Coaching Co-pilot (Course 3) — Design Block

Kaan's vision: *"vibemix is alongside them giving feedback — it can see the future of the song. It can suggest user stops the track, tells the user 'at this point enter track 2, start increasing the crossfader, start blending in the mids and lows.'"*

**The key differentiator vs v8.x live co-host:**
- v8.x live co-host is **reactive** — it observes events (PHASE, LAYER_ARRIVAL, MIX_MOVE) and comments on them after they happen.
- v9.0 Course 3 tutor is **proactive** — it observes upcoming phase boundaries (via the existing 3-second lookahead from `AUDIO-02`) and instructs the user *before* the move ("in 8 bars, start your transition").

**Prior art check (LOW confidence — they claim but don't ship):**
- **PulseDJ** — "AI copilot analyzes tracks in real-time and suggests the best next songs" → next-song recommendation, NOT proactive in-set coaching.
- **Harmovio** — "in-app AI DJ Coach that lets you learn while you mix, real-time phrase detection" → claims live coaching but published feature list is closer to phrase-detection than count-in voice prompts.
- **PCDJ / Serato / Pioneer rekordbox** — no published live-coaching feature.

**Proactive tutor moves (canon-grounded set):**
- **Count-ins:** "8 bars to your transition... 4... 2... 1." (Sourced from DJ TechTools phrasing 101 + every "set preparation" article; standard DJ shorthand.)
- **Action prompts:** "Now drop the lows on your outgoing track" (timed to a kick boundary detected by `event_detector.py`).
- **Pre-flagged drills:** "This next track has a breakdown at 1:47 — pre-cue it now."
- **Recovery prompts:** "Your sync drifted — nudge the jog wheel left for 2 seconds."
- **Calibration prompts:** "Your master output is hitting red — turn it down 2 notches."
- **Commendations (citation-grounded):** "Great kick-swap at bar 33 — you killed the outgoing low exactly on the downbeat." (Backed by EvidenceRegistry; falsifiable.)

**Cardinal Invariants — how the third course doesn't break them:**
- **#1 single-writer:** tutor reads `MusicState`, never writes.
- **#2 citation-grounding:** every commendation registers `lesson_step_observed:L3.04:kick_swap_clean` evidence; un-registered praise strips to ack-bank ("nice mix").
- **#3 trust-the-audio:** the audio detection still drives the events; the tutor's predictions are derived from real detected events (no invented future state).
- **#4 one-socket:** lessons stream over the same `127.0.0.1:8765` ws as the rest of the app; debrief on 8766 unchanged.

**Engineering footprint estimate:** new `tutor/proactive_loop.py` (~200 LOC) that subscribes to the existing phase-prediction events from `event_detector.py`, emits `tutor_action_<L_id>` events into the live coach prompt context, with cooldowns mirrored from v3.0 PHASE 10s / MIX_MOVE 14s. Persona-prompt block added to `prompts/`. The tutor lens (already shipped v8.1) provides the voice.

---

## Tone Calibration — The "Oh Bestie" Decision

> Kaan's vision verbatim:
> User: *"If you are the best, who the fuck am I?"*
> vibemix: *"Oh bestie don't worry. I'm the beginner module of vibemix, let's go."*

**Critique (canon-grounded):**

| Tone Pattern | What canon says | Risk for vibemix |
|--------------|-----------------|------------------|
| **Khanmigo (Khan Academy):** supportive, motivating, Socratic, never gives the answer. | High confidence: works for K-12 learners; some adults find it "patronizing" but it doesn't age badly. | Too "school-teachery" for DJs. vibemix's core voice is the cool friend in the booth, not the patient teacher. |
| **Duolingo (post-2024):** AI characters (Lily, Eddy, etc.) with playful tone; users complained the AI strip "felt repetitive, robotic, lacked the playful tone." | AI tone is *hard*. Personality must be consistent and feel "soul-ful." | Validates that an AI tutor with personality CAN work, but ages badly if generic. |
| **"Bestie" / Gen-Z casual** (TikTok-native voice). | Lands hard with the target audience now; ages quickly (cf. "yass kween" 2018). | Aging risk is REAL. "Bestie" specifically has a half-life — already moving from "ironic warm" to "trying-too-hard" by mid-2025. |
| **"Real DJ friend in your ear"** (vibemix's stated bar). | Best practice in education-AI character design (Younite, Tavus on "Persona Builder"): authentic, consistent, slightly self-aware. | This is the brief. The dialog needs to *sound* like a DJ friend, not a chatbot trying to be Gen-Z. |

**Recommendation (default-YES per Kaan, but with safety net):**

The verbatim "Oh bestie don't worry. I'm the beginner module of vibemix, let's go." is **kept as the v9.0 launch dialog** because:
1. It's Kaan's vision and the persona-anchor for the entire course.
2. It captures the disarm-the-gatekeeping mood that the canon (Mixcloud Blog 2026, SpinStart, DJ Mentors) explicitly says beginner DJs need to hear.
3. Verbatim dialog is the kind of thing roadmap can A/B-test later without breaking the engineering.

**Safety net (recommended addition):**
- Localized dialog file (`prompts/intro_dialog.<lang>.json`) so we can swap copy without a release if "bestie" ages or doesn't translate to it/tr.
- The bestie line is the **only** Gen-Z slang in the module. All lesson voice-overs use the neutral-warm tutor lens already shipped v8.1 ("Nice — you cut the lows right on the kick" not "slay queen the kick is dead").
- A secondary opening dialog variant for the "I'm not 22" user — same warmth, no slang. Default "bestie" path; opt-out via Settings → Voice → Casual / Warm-neutral.

**What to AVOID (canon-grounded anti-patterns):**
- **Over-praise** ("amazing job!! you crushed it!!" — Duolingo's failure mode; loses meaning fast).
- **Patronizing reassurance** ("don't worry, you'll get it eventually" — Khanmigo's risk).
- **Generic AI-slop** ("Let's dive deep into the fascinating world of EQ!" — vibemix's central anti-feature, already a CI grep gate per `LAUNCH-01`).
- **Apology spirals** ("I'm sorry, I didn't catch that, let me try again" — breaks the DJ-friend illusion).
- **Inconsistency** (warm in lesson 1, formal in lesson 7 — kills trust).

The CI grep gate that protects the live co-host from AI-slop should extend to the lesson prompts. Add `lesson_*.json` to the existing `LAUNCH-01` blocklist scope.

---

## Accessibility (Per the Quality Gate)

| Concern | Source canon / standard | vibemix v9.0 plan |
|---------|------------------------|-------------------|
| **Color-blind users** | WCAG 2.2 §1.4.1 "Use of Color"; AudioEye / Boldist / RGblind / Section508.gov: never communicate meaning via color alone. CDJ-Whisper aesthetic uses amber accent (4 intensities) — for ~8% of male users, amber-on-warm-black is the worst-case red-green color-blind region. | Every amber highlight on the hardware-mirror UI gets a **dual cue**: a thick outline (3:1 contrast) AND a textual label ("← MID KNOB"). For path animations (e.g. "move the crossfader from left to right"), add a chevron pattern in addition to the amber. Lesson UI already test-gated by `tauri/ui/tests/session/grounding-failure.spec.ts` pattern; extend test coverage to lesson highlight components. |
| **Hearing-impaired / Deaf users** | AI-tutor accessibility canon (IDEAF, OrCam, Aristek). | Lesson voice-overs ALWAYS have a synchronized text transcript displayed alongside (reuse the existing `transcript_delta` ws message). Visual phrase markers + waveform annotations carry the same info the audio narration carries. Course 3 live coaching pings as text-first; audio is the augment. |
| **Low-vision users** | WCAG 2.2 4.5:1 contrast / 18pt large text. | High-contrast lesson mode (toggleable) — CDJ-Whisper palette has 5 warm blacks; bind a high-contrast variant to deepest black + brightest amber + bone white. Validated by automated contrast checker in CI (extend `tauri/ui` lint to lesson templates). |
| **Motor-impaired / cognitively-paced users** | Khanmigo precedent: no time pressure, mastery gates not clock gates. | NO LESSON HAS A CLOCK. Recital drills accept ±100ms tolerance for phrase-hits at L1.11 (relaxable per user); manual nudge gates have no time limit; user-initiated "I'm done" advances. Re-do is one click. |
| **Keyboard-only navigation** | Standard accessibility. | Hardware-mirror UI is keyboard-navigable for the "Explore" mode (L1.02-L1.10 work without a controller via PC-keyboard mapping). Tab-order through controls; space-bar = press; arrow keys = knob nudge. |
| **Non-English speakers** | i18n is Bravoh-standard. | en/it/tr from v9.0 day one (already supported by Gemini Flash TTS); lesson dialog files swappable per locale. |
| **Beginner anxiety / impostor syndrome** | Kaan's brief, canon (ClubReady, "5 Mistakes Beginner DJs Make" / "DJs feel pressure to impress") — the gatekeeping problem is real. | Opening dialog (L1.01) explicitly defuses; "no train wreck destroys your progress, the lesson is the train wreck recovery itself" framing throughout. |

---

## Feature Dependencies

```
L1.01 Opening Dialog
    │
    └─> L1.02 Meet Your Controller (requires MIDI profile detected OR keyboard fallback)
            │
            ├─> L1.03 Channel Strip ──> L1.05 Pitch ──> L1.06 Transport ──> L1.07 Jog
            ├─> L1.04 Crossfader
            ├─> L1.08 Headphone Cueing (requires audio routing UX)
            └─> L1.09 Master/Booth/Headphone Volumes
                      │
                      └─> L1.10 Anatomy Of A Song (requires CLAP library OR fallback demo tracks)
                              │
                              └─> L1.11 Counting Bars
                                      │
                                      ├─> L1.12 Spot Breakdown By Ear
                                      ├─> L1.13 Spot Breakdown By Eye
                                      └─> L1.14 EQ-As-Tutor Demo (requires CLAP exemplar query + MIDI gating)
                                              │
                                              └─> L1.15 Load Two Tracks
                                                      │
                                                      └─> L1.16 Course 1 Recital
                                                              │
                                                              └─> Gate: Course 2 unlocked

Course 2:
    L2.01 Beatmatching By Ear (manual) ────┐
    L2.02 Beatmatching By Sync ────────────┤
                                            │
                                            v
    L2.03 Long Blend ──> L2.04 EQ Swap ──> L2.05 Bassline Swap ──> L2.06 Filter Fade ──> L2.07 Echo-Out ──> L2.08 Drop Swap ──> L2.09 Loop Transition
                                            │
                                            ├─> L2.10 Hot Cues (rekordbox cues optional, manual cues required)
                                            ├─> L2.11 Camelot Wheel
                                            └─> L2.12 Phrase Matching
                                                    │
                                                    └─> L2.13 Diagnosing a Train Wreck
                                                            │
                                                            └─> L2.14 Course 2 Recital
                                                                    │
                                                                    └─> Gate: Course 3 unlocked

Course 3:
    L3.01 First 5-min mix (requires Course 2 graduation + recording surface)
            │
            └─> L3.02 First 15-min set (requires Build-a-Set engine = v8.2 shipped)
                    │
                    └─> L3.03 Reading The Room (concepts + simulated)
                            │
                            └─> L3.04 First 30-min set (the capstone — requires Proactive Co-pilot loop)
                                    │
                                    └─> L3.05 Recovery Drills
                                            │
                                            └─> L3.06 DJ Profile
                                                    │
                                                    └─> Graduation → unlocks intermediate (out of scope)
```

### Dependency Notes
- **L1.02 Meet Your Controller** is the load-bearing dependency for every L1.03-L1.07 lesson. Without a known MIDI profile (10 shipped) or keyboard fallback, lessons can't gate on real input.
- **L1.10 Anatomy Of A Song requires CLAP library OR fallback demos.** If the user library is empty AND the demo bundle is missing, this lesson cannot run; first-run UX must ship at least 3 demo tracks.
- **L1.14 EQ-As-Tutor Demo enhances every Course 2 transition lesson** — once the user understands what EQ does, transitions become teachable; without it L2.04 (EQ Swap) is a magic-incantation.
- **L1.11 Counting Bars precedes EVERYTHING in Course 2.** Phrase awareness is non-negotiable.
- **L2.01 + L2.02 are parallel** (manual + sync taught side-by-side per modern consensus). User must pass both to advance to L2.03.
- **L3.01 requires the existing recording infrastructure** (already shipped v0.1.0). L3.02 requires Build-a-Set engine (shipped v8.2). L3.04 requires the new Proactive Co-pilot loop (the engineering moat).
- **L3.04 conflicts with v8.x reactive co-host's MIX_MOVE cooldown** if both run during the lesson — cooldowns must be lesson-aware (suppress reactive comments while lesson is driving the prompt).
- **All Course 1 lessons can run without GEMINI_API_KEY** if we pre-record voice-overs locally (defer this decision; v9.0 day-one Gemini TTS is acceptable since Bravoh proxy is the cost-guard already shipped).

---

## MVP Definition

### Launch With (v9.0 — "Lesson One")

The hard floor: a beginner with one of the 10 shipped controllers, an empty library, and zero DJ experience can complete Course 1 + 2 + 3 capstones and call themselves "a beginner DJ who can do a clean 30-min set."

- [ ] **L1.01-L1.16 (Course 1)** — all 16 anatomy lessons. The EQ-as-Tutor Demo (L1.14) is the marquee.
- [ ] **L2.01-L2.14 (Course 2)** — all 14 transition lessons, including the 5 canonical transitions + harmonic mixing + train-wreck diagnosis.
- [ ] **L3.01-L3.06 (Course 3)** — the full proactive-tutor surface.
- [ ] **Hardware-mirror UI for all 10 controllers.**
- [ ] **3-5 baked-in CC0/Apache-clean demo tracks** for library-empty fallback.
- [ ] **en/it/tr localization** of all lesson dialog files.
- [ ] **Accessibility passes** for color-blind dual-cues + transcripts + high-contrast mode + keyboard nav.
- [ ] **Tutor-aware reactive-cooldown suppression** so Course 3 isn't talking over itself.
- [ ] **The opening "I'm the beginner module" dialog** (Kaan-verbatim, with the secondary warm-neutral variant available via Settings).
- [ ] **Lesson progress persistence** (extend existing `profile/` json).

### Add After Validation (v9.1)

- [ ] **Per-genre branches** (wedding-DJ + techno-DJ + house-DJ + hip-hop-DJ specializations) — only after telemetry shows enough split to justify forking.
- [ ] **Pre-controller "Explore" mode** for Course 1 (keyboard-only) — defer until we see how many sign-ups bounce on "no controller detected."
- [ ] **Lesson sharing** — export a lesson recital recording as a shareable Mixcloud-style clip.
- [ ] **Live group lessons / cohort mode** — only if Bravoh community drives demand.

### Future Consideration (v10+)

- [ ] **Scratching course module** — distinct second module, lifts Crossfader / Studio Scratches pedagogy.
- [ ] **Intermediate course** — picks up where L3.06 graduates; layered effects, multi-track set construction, longer-set arc planning.
- [ ] **Production / DAW lessons** — only via Bravoh handoff, not in vibemix.

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Course 1 anatomy lessons (L1.02-L1.13) | HIGH | MEDIUM | P1 |
| L1.01 Opening Dialog | HIGH | LOW | P1 |
| **L1.14 EQ-As-Tutor Demo (the moat)** | HIGH | HIGH | P1 |
| L1.15-L1.16 First Load + Course 1 Recital | HIGH | LOW | P1 |
| Course 2 transition lessons (L2.01-L2.09) | HIGH | MEDIUM | P1 |
| L2.10 Hot Cues | HIGH | MEDIUM | P1 |
| L2.11 Camelot Wheel | HIGH | LOW (already shipped harmonics.py) | P1 |
| L2.12-L2.14 Phrase matching + Train wreck + Recital | HIGH | MEDIUM | P1 |
| Course 3 L3.01-L3.04 Live coaching | HIGH | HIGH | P1 |
| L3.05 Recovery drills | MEDIUM | MEDIUM | P1 |
| L3.06 DJ Profile graduation | MEDIUM | LOW (existing profile) | P1 |
| Hardware-mirror UI for all 10 controllers | HIGH | HIGH | P1 |
| Library-grounded exemplars + 3-5 demo tracks | HIGH | MEDIUM | P1 |
| en/it/tr localization | MEDIUM | MEDIUM | P1 |
| Accessibility (dual-cues + transcript + a11y nav) | HIGH | MEDIUM | P1 |
| Tutor-aware cooldown suppression | HIGH | LOW | P1 |
| Per-genre beginner branches | MEDIUM | HIGH | P2 |
| Hardware-free "Explore" mode | LOW | MEDIUM | P2 |
| Recital share / export | MEDIUM | LOW | P2 |
| Scratching module | MEDIUM | HIGH | P3 |
| Intermediate course | MEDIUM | HIGH | P3 |
| Production handoff to Bravoh | LOW | LOW | P3 |
| Cohort / group lessons | LOW | HIGH | P3 |

---

## Competitor Feature Analysis

| Feature | rekordbox Tutorial Mode (Pioneer DJ) | Serato Practice Mode | Crossfader / Digital DJ Tips | PulseDJ / Harmovio (AI tools) | vibemix v9.0 |
|---------|---------------------------------------|---------------------|------------------------------|-------------------------------|--------------|
| Anatomy of controller | Yes (DDJ-400/FLX2 only, specific to Pioneer) | No (focused on practice without hardware) | Yes (per-controller free courses) | No | **Yes — all 10 shipped controllers, AI-narrated, MIDI-gated** |
| Anatomy of a song | Static visual guide | No | Yes (Mixed In Key book, Phil Morse Step 2) | Phrase detection (analysis only) | **Yes — using user's library + AI-narrated structure ID + waveform annotation** |
| Counting bars / phrase awareness | Limited | No | Yes (DJ TechTools 101 article, Beatmatch Guru) | Harmovio: phrase detect | **Yes — interactive tap-along drill** |
| EQ-as-Tutor (AI plays your track and gates on your knob) | No (static EQ knobs on screen) | No | No (text + video only) | No | **Yes — the differentiator** |
| Beatmatching tutorial | Static how-to-use | Practice with two software decks | Universal video lessons | Auto-sync only | **Manual + sync side-by-side; ear-trained with AI feedback** |
| Transition tutorials | Yes (drop mix, drop swap, FX, looping) | No | Universal | PulseDJ: track suggestion only | **All 5 canonical transitions, AI-gated, MIDI-graded** |
| Harmonic mixing (Camelot) | Software shows key | No | Yes | Yes (Harmovio's "intelligent search") | **Yes — interactive Camelot exploration + AI suggestions from user's library** |
| Live proactive coaching in a real set | No | No | No | Reactive recommendation, not proactive coaching | **The Course 3 moat — count-ins + action prompts + recovery prompts** |
| Hardware diversity | Pioneer-only | Any controller (Serato-compatible) | Multi-vendor courses | Software-agnostic | **10 controllers shipped, generic-MIDI + keyboard fallback** |
| Grounded / falsifiable AI feedback | N/A (no AI) | N/A (no AI) | N/A (human videos) | Not explicitly grounded | **Cardinal Invariant #2 — every commendation is registered evidence; ungrounded praise strips** |
| Accessibility (color-blind, hearing-impaired, motor) | Standard software a11y | Standard | Captioned video | Unknown | **Dual-cue + transcript + high-contrast + mastery-gate (not clock-gate)** |
| Localized (en + it + tr) | en + some | en + some | en + some | en | **en + it + tr from day one** |
| Cost | Free with hardware purchase | Free | Mostly free, premium paid | Subscription | **Free + open source (Apache 2.0)** |

---

## Sources

### DJ Pedagogy Canon (curriculum, transitions, mixing fundamentals)
- [Phil Morse / Digital DJ Tips — The Complete DJ Course (Five-Step Formula)](https://www.digitaldjtips.com/dj-courses/the-complete-dj/) — gear → music → mixing → performing → success; 8 modules, 70+ video lessons; the most-cited pedagogy on the public web.
- [Digital DJ Tips — Phil Morse author page](https://www.digitaldjtips.com/phil-morse/)
- [Phil Morse — Rock The Dancefloor (PDF, the five-step formula book)](https://www.digitaldjtips.com/app/uploads/delightful-downloads/2017/07/Rock-The-Dancefloor-by-Phil-Morse.pdf)
- [Crossfader — Learn to DJ: The Complete Beginners Guide](https://wearecrossfader.co.uk/blog/learn-to-dj-the-complete-beginners-guide/)
- [Crossfader — The Complete DJ Course (FREE)](https://wearecrossfader.co.uk/blog/the-complete-dj-course-free/)
- [Crossfader — Beginner DJ Courses Page](https://wearecrossfader.co.uk/beginner-tutorials/)
- [Crossfader — How to Mix with EQs](https://wearecrossfader.co.uk/blog/how-to-mix-with-eqs/)
- [Crossfader — DJ Looping Guide: How to Set and Use Loops](https://wearecrossfader.co.uk/blog/dj-looping-guide/)
- [Crossfader — Hot Cues in DJing: The Complete Guide](https://wearecrossfader.co.uk/blog/hot-cues-complete-guide/)
- [Crossfader — Scratching for Beginners](https://wearecrossfader.co.uk/blog/scratching-for-beginners/)
- [Crossfader — Getting Started With The DDJ-400](https://wearecrossfader.co.uk/blog/getting-started-with-the-ddj-400/)
- [DJ TechTools — How to DJ 101: Why You Must Understand Phrasing](https://djtechtools.com/2014/11/16/how-to-dj-101-why-you-must-understand-phrasing/)
- [DJ TechTools — Gain Staging For DJs + Staying Out Of The Red](https://djtechtools.com/2015/10/11/gain-staging-for-djs-staying-out-of-the-red/)
- [DJ TechTools — Reading Wave Forms](https://djtechtools.com/2010/01/05/understand-your-wave-forms/)
- [DJ TechTools — DDJ to CDJs: Practicing For CDJs](https://djtechtools.com/2017/07/23/ddj-cdjs-practicing-cdjs-pioneer-dj-controller/)
- [DJ TechTools — 5 Critical Tips For Using CDJs For The First Time](https://djtechtools.com/2017/08/27/5-critical-tips-using-cdjs-first-time/)
- [DJ TechTools — Controlling The Dancefloor: A Guide On Organizing Playlists by Energy](https://djtechtools.com/2022/11/25/controlling-the-dancefloor-a-guide-on-organizing-playlists-by-energy/)
- [DJ TechTools — Recording DJ Mixes: How To Do It Right and Why It Matters](https://djtechtools.com/2012/09/05/recording-dj-mixes/)
- [Mixed In Key — Camelot Wheel](https://mixedinkey.com/camelot-wheel/)
- [Mixed In Key — Harmonic Mixing Guide](https://mixedinkey.com/harmonic-mixing-guide/)
- [Mixed In Key — Harmonic Mixing Explained](https://mixedinkey.com/wiki/harmonic-mixing-explained-everything-you-need-to-know/)
- [Mixed In Key — Visualize The Structure Of Dance Music (book chapter)](https://mixedinkey.com/book/visualize-the-structure-of-dance-music/)
- [Mixed In Key — 5 Mixing Techniques Every DJ Should Know](https://mixedinkey.com/wiki/5-mixing-techniques-every-dj-should-know/)
- [Beatportal — 10 Lessons Every DJ Should Know](https://www.beatportal.com/articles/3919-10-lessons-every-dj-should-know)
- [DJ.studio — A Beginner's Guide to DJ Mixing Techniques](https://dj.studio/blog/dj-mixing-beginners)
- [DJ.studio — 16 Basic DJ Transition Techniques](https://dj.studio/blog/basic-transition-techniques)
- [DJ.studio — The DJ Transitions Playbook](https://dj.studio/blog/the-dj-transitions-playbook)
- [DJ.studio — The Ultimate Skill Guide: DJ Mixing Different Genres](https://dj.studio/blog/dj-mixing-genres)
- [DJ.studio — The Camelot Wheel and Harmonic Mixing](https://dj.studio/blog/camelot-wheel)
- [DJ.studio — Mixing dB Levels for DJs (gain staging)](https://dj.studio/blog/mixing-db-levels)
- [DJingPro — 5 Easy DJ Transitions Every DJ Should Learn 2026](https://djingpro.com/dj-transitions/)
- [DJingPro — DJ EQing: Tips to EQ Mixing to Transform your Sets](https://djingpro.com/dj-eq-tips/)
- [DJingPro — How to Use a DJ Mixer for Beginners 2026](https://djingpro.com/how-to-use-a-dj-mixer/)
- [DJingPro — Camelot Wheel: Full Guide to Harmonic Mixing 2026](https://djingpro.com/camelot-wheel-harmonic-mixing/)
- [DJingPro — 10+ Tips on How to Use Headphones to DJ](https://djingpro.com/use-headphones-to-dj/)
- [ZIPDJ — Top 5 Easy DJ Transitions To Learn In 2026](https://www.zipdj.com/blog/dj-transitions)
- [ZIPDJ — 10 Basic DJ Scratching Techniques You Need To Know 2026](https://www.zipdj.com/blog/dj-scratching-techniques)
- [ZIPDJ — The 10 Best DJ Tutorials For Beginners 2026](https://www.zipdj.com/blog/best-dj-tutorials)
- [Mixgraph — DJ Transition Techniques: 7 Ways to Mix Between Tracks](https://www.mixgraph.io/learn/dj-transition-techniques)
- [Native Instruments Blog — 5 basic DJ transitions to keep your music in the flow](https://blog.native-instruments.com/dj-transitions/)
- [Pioneer DJ — The total beginner's guide to DJ gear](https://www.pioneerdj.com/en/news/2020/beginner-dj-what-do-you-need/)
- [Pioneer DJ — Mixing techniques behind every major genre](https://blog.pioneerdj.com/djtips/we-uncover-the-mixing-techniques-behind-every-major-genre/)
- [Pioneer DJ — DDJ-400 Master The Basics announcement](https://www.pioneerdj.com/en/news/2018/master-the-basics-with-the-new-ddj-400-controller-for-rekordbox-dj/)
- [Pioneer DJ — DDJ-400 DJ Controller Mixing Technique Tutorials](https://www.pioneerdj.com/en/news/2019/ddj-400-dj-controller-mixing-technique-tutorials/)
- [Pioneer DJ — Start From Scratch landing page](https://www.pioneerdj.com/en/landing/start-from-scratch/)
- [Pioneer DJ — Learn how to DJ online](https://www.pioneerdj.com/en/news/2019/learn-how-to-dj-online/)
- [Pioneer DJ — Pete Tong DJ Academy: How to Start DJing](https://rekordbox.com/en/connect/pete-tong-dj-academy/how-to-start-djing/)
- [Pioneer DJ — DJ School Partners](https://www.pioneerdj.com/en/landing/dj-school-partners/)
- [Pointblank Music School — Pioneer DJ DJ Basics tutorials with DDJ-400](https://www.pointblankmusicschool.com/blog/watch-pt-1-of-pioneer-dj-point-blanks-dj-basics-tutorials-w-the-ddj-400/)
- [Pioneer DJ Forums — Hot cues & memory cues on CDJs](https://forums.pioneerdj.com/hc/en-us/community/posts/360043612152-Hot-cues-memory-cues-on-CDJs-what-you-need-to-know-and-how-to-set-them-the-same-automatically)
- [DeeJay Plaza — Ultimate Rekordbox Hot Cue and Cue Point tutorial](https://www.deejayplaza.com/en/articles/rekordbox-memory-cue-point-hot-cue)
- [Fact Mag — Pioneer DJ DDJ-400 tutorial mode announcement](https://www.factmag.com/2018/06/26/pioneer-dj-ddj-400-controller-announced/)
- [Beatmatch Guru — What is a Bar in DJing? Counting Beats, Bars & Phrases](https://beatmatchguru.com/what-is-a-bar-in-djing-counting-beats-bars-phrases/)
- [DJfuturo — From 0 to DJ #4: Counting Music Beats, Bars and Phrases](https://djfuturo.com/en/count-music-beats-bars-phrases/)
- [DJfuturo — From 0 to DJ #9: Pre-Cueing (How to Use DJ Headphones)](https://djfuturo.com/en/pre-cueing/)
- [DJfuturo — From 0 to DJ #2: Parts of a DJ Mixer](https://djfuturo.com/en/dj-mixer-parts/)
- [English DJ in France — Lesson 5: What is cueing and how do you do it?](https://www.englishdjinfrance.com/dj-course/2022/11/10/dj-lesson-5-what-is-cueing-and-how-do-you-do-it)
- [English DJ in France — Lesson 10: Understanding Your Tunes - Bars and Phrases](https://www.englishdjinfrance.com/dj-course/2022/11/14/dj-lesson-10-understanding-your-tunes-bars-and-phrases)
- [Steemit — The Novice DJ's Most Important Skill: Counting Beats, Bars and Phrases](https://steemit.com/music/@munteanu/the-novice-dj-s-most-important-skill-to-develop-counting-beats-bars-and-phrases)
- [DJ.studio — What is DJ Phrase Mixing?](https://dj.studio/blog/phrasing-dj-mixing)
- [Skilz DJ Academy — Understanding the Blending: DJ Mix with EQ](https://www.skilzdjacademy.com/post/understanding-the-blending-dj-mix-with-eq)
- [Pirate.com — What Is EQ? How To Use It When Mixing Music](https://pirate.com/en/blog/dj-tips/how-to-mix-using-eq/)
- [Pirate.com — How to Beatmatch (DJ Tips)](https://pirate.com/en/blog/how-to-beatmatch/)
- [Pirate.com — Crossfader DJ Course and Pirate DJ Studios](https://pirate.com/en/artist-hub/crossfader/)
- [Pirate.com — Types of DJs](https://pirate.com/en/blog/types-of-djs/)
- [Pirate.com — How To Use Serato DJ Lite and Pro - Beginner's Tutorial](https://pirate.com/en/blog/how-to-use-serato-dj/)
- [PulseDJ — How to Beatmatch for DJs: The Ultimate Guide](https://blog.pulsedj.com/how-to-beatmatch)
- [PulseDJ — Harmonic Mixing for DJs](https://blog.pulsedj.com/harmonic-mixing)
- [PulseDJ — AI DJ Software](https://blog.pulsedj.com/ai-dj-software)
- [PulseDJ — How to Record a DJ Mix](https://blog.pulsedj.com/record-dj-mix)
- [Home DJ Studio — How To Master Gain Staging For Your Sets](https://homedjstudio.com/gain-structure/)
- [Home DJ Studio — The Complete Guide To DJ EQing](https://homedjstudio.com/dj-eqing/)
- [Home DJ Studio — Is Using The Sync Button Bad?](https://homedjstudio.com/sync-button/)
- [Home DJ Studio — How To Use A DJ Loop In Your Sets](https://homedjstudio.com/dj-loops/)
- [Home DJ Studio — How To Organize Your Music Library](https://homedjstudio.com/organize-music-library/)
- [Ten Kettles — Highs and Lows: an Audio Primer (Part 2)](https://www.tenkettles.com/highs-and-lows-an-audio-primer-part-2/)
- [Songstuff — EQ Frequencies](https://www.songstuff.com/recording/article/eq-frequencies/)

### Modern Sync-vs-Beatmatch Consensus
- [DJ Mentors / Dan — Is the Sync Button Bad?](https://www.djmentors.com/p/the-sync-button)
- [DJ Shortee — Manual Beat Matching vs Sync](https://www.djshortee.com/manual-beat-matching-vs-sync-which-is-better-for-djs-classic-dj-skills-vs-new-technology/)
- [Mixcloud Blog — Should DJs be using the sync button? (March 2026)](https://www.mixcloud.com/blog/2026/03/25/should-djs-be-using-the-sync-button/)
- [Mixcloud Blog — How To Master The Art of DJing With Crossfader](https://www.mixcloud.com/blog/2024/04/08/how-to-master-the-art-of-djing-with-crossfader/)
- [Midnight Rebels — Sync vs. Manual Beatmatching: What Pro DJs Really Think](https://midnightrebels.com/sync-vs-manual-beatmatching-what-pro-djs-really-think/)
- [SpinStart — Beatmatching Explained: Old-School Skill or Still Essential?](https://www.djmasterycourses.com/is-beatmatching-still-necessary/)
- [Digital DJ Tips — Is Sync Really So Different To Beatmatching?](https://www.digitaldjtips.com/your-questions-is-sync-really-so-different-to-beatmatching/)
- [ClubReady DJ School — What's wrong with SYNC!](https://www.clubreadydjschool.com/tribe-talk/getting-started/whats-wrong-with-using-sync/)
- [BizCommunity — More than a sync button: DJ training matters](https://www.bizcommunity.com/article/more-than-a-sync-button-dj-training-matters-732562a)

### Common Beginner Mistakes (anti-feature evidence)
- [ClubReady DJ School — 7 Common Beginner DJ Mistakes](https://www.clubreadydjschool.com/tribe-talk/getting-started/7-common-beginner-dj-mistakes/)
- [ClubReady DJ School — 5 Mistakes Beginner DJs Make](https://www.clubreadydjschool.com/tribe-talk/getting-started/5-mistakes-beginner-djs-make/)
- [ClubReady DJ School — Bass Swapping: Don't Make This Common Mistake](https://www.clubreadydjschool.com/tribe-talk/getting-started/bass-swapping-dont-make-this-common-mistake/)
- [ClubReady DJ School — 10 Beginner DJ Tips](https://www.clubreadydjschool.com/tribe-talk/getting-started/10-beginner-dj-tips/)
- [ClubReady DJ School — DJ Transition Techniques (Volume Faders vs EQ)](https://www.clubreadydjschool.com/tribe-talk/getting-started/dj-transition-techniques/)
- [The Ghost Production — DJ Mistakes Beginners Make](https://theghostproduction.com/dj-resources/dj-mistakes-beginners/)
- [The Ghost Production — How to Practice DJing Daily](https://theghostproduction.com/dj-resources/how-to-practice-djing-daily/)
- [The DJ Revolution — 20 DJ Mistakes Beginners Make](https://www.thedjrevolution.com/dj-mistakes/)
- [SpinStart — 5 Common Mistakes Beginner DJs Make](https://www.djmasterycourses.com/dj-mistakes/)
- [DJ Times — A Club Designer Sounds Off: The Cringe-Worthy Habits of DJs](https://www.djtimes.com/2020/03/dj-sound-redlining-booth-levels/)
- [DJ.studio — 7 Common Bad DJ Mixing Mistakes to Avoid](https://dj.studio/blog/bad-dj-mixing-mistakes)
- [Digital DJ Tips — How To Use Booth Monitors (And What To Do When There Aren't Any!)](https://www.digitaldjtips.com/how-to-use-booth-monitors-and-what-to-do-when-there-arent-any/)
- [Digital DJ Tips — How To Use The Echo Effect When DJing](https://www.digitaldjtips.com/how-to-use-echo-when-djing/)
- [Digital DJ Tips — How To Record And Critique Your Sets](https://www.digitaldjtips.com/rock-the-dancefloor/how-to-record-and-critique-your-sets/)
- [Digital DJ Tips — Recording Your Sets: The Single Best Way To Improve Your DJing](https://www.digitaldjtips.com/recording-your-dj-sets-habit/)
- [Digital DJ Tips — Adding EQ, Filters And Effects](https://www.digitaldjtips.com/rock-the-dancefloor/adding-eq-filters-and-effects/)
- [Digital DJ Tips — Five Basic DJ Transitions](https://www.digitaldjtips.com/rock-the-dancefloor/five-basic-dj-transitions/)
- [Digital DJ Tips — Facts And Myths About Booth Outputs On DJ Controllers](https://www.digitaldjtips.com/facts-and-myths-dj-booth-outputs/)
- [Digital DJ Tips — DJ Mixer Inputs & Outputs: Every Connection Explained](https://www.digitaldjtips.com/dj-mixer-inputs-outputs-guide/)
- [Digital DJ Tips — How To Find Time To Learn DJing](https://www.digitaldjtips.com/find-time-for-djing/)
- [Digital DJ Tips — Scratching: 5 Things You're (Almost Certainly) Doing Wrong](https://www.digitaldjtips.com/5-errors-you-are-making-in-your-scratching/)

### Reading the Crowd / Energy Management
- [Relentless Beats — Behind the Booth: How DJs Read a Crowd](https://relentlessbeats.com/2026/02/behind-the-booth-how-djs-read-a-crowd-and-control-a-nights-energy/)
- [Bauhaus LV — DJ Spotlight: The Art of Reading a Crowd](https://bauhauslv.com/blogs/dj-spotlight-the-art-of-reading-a-crowd-and-building-energy-on-the-dance-floor/)
- [Hercules — Mastering the art of reading a crowd](https://www.hercules.com/en/mastering-the-art-of-reading-a-crowd/)
- [Hercules — So you want to learn how to scratch?](https://www.hercules.com/en-us/so-you-want-to-learn-how-to-scratch/)
- [Product London — How to Read the Crowd: DJ Tips for Beginners](https://www.productlondon.com/how-to-read-the-crowd-djing/)
- [Product London — 10 Essential Tips for Reading the Crowd as a DJ](https://www.productlondon.com/how-to-read-the-crowd-as-a-dj/)
- [Product London — Mastering Scratching Effects for DJ Sets](https://www.productlondon.com/mastering-scratching-effects-for-dj-sets/)
- [Learning To DJ — How To Read The Dancefloor For Energy Cues](https://learningtodj.com/blog/how-to-read-the-dancefloor-for-energy-cues/)
- [City Nights Disco — How DJs Read Dancefloors for Energy Cues](https://www.citynightsdisco.co.uk/how-djs-read-dancefloors-for-energy-cues/)
- [PCDJ — Crowd Reading 101](https://pcdj.com/crowd-reading-101-how-to-adapt-your-set-on-the-fly-for-maximum-engagement/)
- [PCDJ — How Are Wedding DJs and Club DJs Different?](https://pcdj.com/how-are-wedding-djs-and-club-djs-different/)
- [Melbourne Entertainment Co — What Makes a Wedding DJ Different From a Club DJ](https://melbourneentertainmentco.com.au/what-makes-a-wedding-dj-different-from-a-club-dj/)
- [Star DJ Hire — What Is the Difference Between a Wedding DJ and a Club DJ?](https://www.stardjhire.com.au/blog/difference-between-a-wedding-dj-and-a-club-dj/)
- [TikTok — @nextdimensional Echo Out Transition explainer](https://www.tiktok.com/@nextdimensional/video/7269908847484095775?lang=en)

### Cueing, Hot Cues, Library Organization
- [Rane DJ — Understanding and Utilizing the Headphone Cue](https://support.rane.com/en/support/solutions/articles/69000858891-understanding-and-utilizing-the-headphone-cue)
- [Algoriddim — Pre-Cueing: Previewing with headphones](https://www.algoriddim.com/hardware/precueing)
- [Algoriddim — Setting up audio & pre-cueing in djay](https://help.algoriddim.com/topic/first-steps/audio-setup)
- [Algoriddim — Loops user manual](https://help.algoriddim.com/user-manual/djay-pro-windows/dj-tools/cueing-looping/loops)
- [The DJ Podcast — How to DJ: Headphone Cueing & Split Cue Tutorial](https://thedjpodcast.com/episodes/dj-headphone-cueing-split-cue-tutorial/)
- [Best DJ Tips — How To Use Headphones For Cueing](https://www.bestdjtips.com/how-to-use-headphones-for-cueing/)
- [Beatport DJ — Headphone Cue Tutorial (YouTube)](https://www.youtube.com/watch?v=Sl2cVi-_FPM)
- [Deft DJ Tips — DJ Music Crate Mastery](https://deftdjtips.com/music-crate-organization/)
- [ZIPDJ — How To Organize Your DJ Playlists & Crates In 2026](https://www.zipdj.com/blog/how-to-organize-dj-playlists)
- [Pioneer DJ Blog — How to manage your music like a pro](https://blog.pioneerdj.com/djtips/how-to-manage-your-music-like-a-pro/)
- [DJ.studio — How To Organize Your Music Library](https://dj.studio/blog/dj-music-organizer-software)
- [Crossfader — How to Organise Your DJ Music Collection and USB](https://wearecrossfader.co.uk/blog/organise-dj-music-collection/)
- [Lexicon DJ — Library Management For Professional DJs](https://www.lexicondj.com/)
- [Crossfader — DJ Lessons Free](https://wearecrossfader.co.uk/blog/free-lessons/)
- [Crossfader — Online DJ Courses](https://wearecrossfader.co.uk/online-dj-courses)
- [Crossfader — Rekordbox Tutorials](https://wearecrossfader.co.uk/rekordbox-tutorials/page/7/?v=79cba1185463)
- [Crossfader — 12 High-Energy DJ Transitions You Can Learn!](https://wearecrossfader.co.uk/blog/12-high-energy-dj-transitions/)
- [Crossfader — Difference between Hot Cues and Memory Cues](https://wearecrossfader.co.uk/blog/the-difference-between-hot-cues-and-memory-cues-monday-dj-tips/)
- [Crossfader — Getting Started with the Pioneer DDJ-FLX10](https://wearecrossfader.co.uk/blog/ddj-flx10-getting-started/)
- [Crossfader — Scratching DJ Tutorial: How to instantly scratch better](https://wearecrossfader.co.uk/blog/dj-scratching-lesson/)
- [Bop DJ — Crossfader Denon DJ Beginner Course (32 lessons / 5.5 hours)](https://www.bopdj.com/crossfader-denon-dj-beginner-course.html)

### Waveform Reading / Beatgrid
- [Core Mixing — How to Read DJ Waveforms - Visual Mixing Guide](https://www.coremixing.com/blog/how-to-read-dj-waveforms)
- [Serato Support — Main Waveform Display](https://support.serato.com/hc/en-us/articles/224969307-Main-Waveform-Display)
- [Serato Support — Introduction to Beatgrids](https://support.serato.com/hc/en-us/articles/202523390-Introduction-to-Beatgrids)
- [Serato Support — Practice mode](https://support.serato.com/hc/en-us/articles/360001274635-Practice-mode)
- [Serato — DJ Pro Tutorials](https://serato.com/dj/pro/tutorials)
- [Serato — DJ Lite Tutorials](https://serato.com/dj/lite/tutorials)
- [DJ File — How to use Practice Mode in Serato DJ](https://djfile.com/how-use-practice-mode-serato-dj)
- [DJ TechZone — Serato DJ Pro adds Practice Mode](https://djtechzone.com/serato-dj-pro-and-serato-dj-lite-released-adds-practice-mode/)

### Song Structure Canon (EDM/Dance Music)
- [Cymatics — EDM Song Structure: Turn Your Loop Into A Song!](https://cymatics.fm/blogs/production/edm-song-structure)
- [Unison — EDM Song Structure 101](https://unison.audio/edm-song-structure/)
- [EDM Tips — EDM Song Structure: Arrange Your Loop into a Full Song](https://edmtips.com/edm-song-structure/)
- [SoundClasses — How to Structure an EDM Track](https://soundclasses.com/how-to-structure-an-edm-track-a-practical-guide-for-producers/)
- [Mix Elite — Mastering EDM Song Structure](https://mixelite.com/blog/edm-song-structure/)
- [Audio Services — Understanding Arrangements in Electronic Music Production](https://audioservices.studio/blog/understanding-arrangements-in-electronic-music-production)
- [Subaqueous Music — Song Structure in Electronic Music and Dubstep](https://www.subaqueousmusic.com/dubstep-and-electronic-music-song-structure/)
- [The Ghost Production — EDM Arrangement Guide](https://theghostproduction.com/producer-resources/edm-arrangement-guide/)

### AI Tutor Tone & Pedagogy
- [Khanmigo — AI Learning Assistant by Khan Academy (official)](https://www.khanmigo.ai/)
- [Khanmigo for learners](https://www.khanmigo.ai/learners)
- [Khanmigo for teachers](https://www.khanmigo.ai/teachers)
- [Khanmigo for parents](https://www.khanmigo.ai/parents)
- [Khanmigo overview at TrendingAITools](https://www.trendingaitools.com/ai-tools/khanmigo-2/)
- [AVID Open Access — Khanmigo as an AI Personal Tutor and Assistant](https://avidopenaccess.org/resource/khanmigo-as-an-ai-personal-tutor-and-assistant/)
- [Freethink — Sal Khan wants to give every student on Earth a personal AI tutor](https://www.freethink.com/consumer-tech/khanmigo-ai-tutor)
- [Numa School — Khanmigo AI Tutor for Homeschool Explained](https://numaschool.com/learn/glossary/khanmigo)
- [Skywork — Khanmigo Deep Dive](https://skywork.ai/skypage/en/Khanmigo-Deep-Dive:-How-Khan-Academy's-AI-is-Shaping-the-Future-of-Education/1972857707881885696)
- [Paula Johnson Tech — Transform Teaching with Khanmigo](https://paulajohnsontech.com/2025/08/26/transform-teaching-with-khanmigo-an-ai-classroom-assistant/)
- [Vietnam Foundation — Khanmigo and its pioneering role in the AI education era](https://vnfoundation.org/en/khanmigo-and-its-pioneering-role-in-the-ai-education-era/)
- [Indiana Learning — Future of Accessibility in Education: How AI is Changing the Game](https://keepindianalearning.org/future-of-accessibility-in-education-how-ai-is-changing-the-game/)
- [Microsoft Source — Khan Academy and Microsoft partner to expand access to AI tools](https://news.microsoft.com/source/features/ai/khan-academy-and-microsoft-partner-to-expand-access-to-ai-tools/)
- [Duolingo — Brand Voice Guidelines](https://design.duolingo.com/writing/voice)
- [TechRadar — You can now chat and play games with Duolingo's AI characters](https://www.techradar.com/computing/artificial-intelligence/you-can-now-chat-and-play-games-with-duolingos-ai-characters-to-learn-spanish-or-french)
- [Solutions Review — How Duolingo's AI-First Strategy Lost the Human Touch](https://solutionsreview.com/how-duolingos-ai-first-strategy-lost-the-human-touch/)
- [Mahabali — Language Learning as Plastic Surgery (Duolingo critique)](https://blog.mahabali.me/pedagogy/language-learning-as-plastic-surgery-the-illusion-of-learning-from-gamification-ai-apps-like-duolingo/)
- [Younite — Building Personality into AI: The Path to Authentic Connection](https://younite.ai/building-personality-into-ai-the-path-to-authentic-connection)
- [Tavus — Introducing Persona Builder](https://www.tavus.io/post/introducing-persona-builder)

### Accessibility / Color-blind / Dual-Cue UI
- [Section508.gov — Making Color Usage Accessible](https://www.section508.gov/create/making-color-usage-accessible/)
- [W3C WAI — WCAG 2.2 SC 1.4.1 Use of Color](https://www.w3.org/WAI/WCAG21/Understanding/use-of-color.html)
- [AudioEye — 8 ways to design a color-blind friendly website](https://www.audioeye.com/post/8-ways-to-design-a-color-blind-friendly-website/)
- [accessiBe — How designers can make websites more accessible for color blindness](https://accessibe.com/blog/knowledgebase/accessible-website-for-people-with-color-blindness)
- [The A11Y Collective — An Introduction to Colour Blindness Accessibility](https://www.a11y-collective.com/blog/color-blind-accessibility-guidelines/)
- [Boldist — UI Design for Color Blind Users](https://boldist.co/usability/ui-design-for-color-blind-users/)
- [Number Analytics — Color Blind Friendly UI Design](https://www.numberanalytics.com/blog/color-blind-friendly-ui-design-strategies)
- [Think Design — When Red & Green Look the Same: Inclusive UI Design for Colorblindness](https://think.design/blog/inclusive-ui-design-for-colorblindness/)
- [RGBlind — Accessible UI Design for Color Blindness](https://rgblind.com/blog/accessible-ui-design-for-color-blindness)
- [Recite Me — Color-Blind Accessibility: Design Color Accessible Websites](https://reciteme.com/us/news/color-blind-accessibility/)
- [All Accessible — Color Contrast Accessibility Complete WCAG 2025 Guide](https://www.allaccessible.org/blog/color-contrast-accessibility-wcag-guide-2025)
- [Color Blind Vision Simulator (Skynet Technologies)](https://www.skynettechnologies.com/color-blindness-simulator)
- [Color Blind Simulator App — Designing for Color Blind Users Guide](https://colorblindsimulator.app/blog/design-for-color-blind-users)
- [Lem Apperson (Medium) — Mastering UI Design: Accessible Color Schemes](https://medium.com/@lemapp09/mastering-ui-design-designing-accessible-color-schemes-2d0d202c06ad)
- [IDEAF — AI Tools Improving Access for Hearing Impaired Communities](https://www.ideaf.uk/posts/ai-access-hearing-impaired)
- [Aristek Systems (Medium) — How AI helps to create an accessible learning environment](https://medium.com/@aristeksystems/how-ai-helps-to-create-an-accessible-learning-environment-271baabfaf50)
- [OrCam — AI in Education: Enhancing Accessibility for All Students](https://www.orcam.com/en-us/blog/practical-applications-ai-in-education-accessibility)
- [arxiv — AI for Accessible Education: Personalized Audio-Based Learning for Blind Students](https://arxiv.org/pdf/2504.17117)

### Hardware-Aware Tutorial Mode Precedents
- [Pioneer DDJ-200 smart DJ controller tutorial videos (WeDJ)](https://www.pioneerdj.com/en-us/landing/smart-dj-controller-ddj-200/tutorial/)
- [Pioneer rekordbox DJ download page](https://rekordbox.com/en/2020/04/ddj-400-official-introduction/)
- [AlphaTheta Help Center — How to use the DDJ-400](https://support.pioneerdj.com/hc/en-us/articles/4404919716761-How-to-use-the-Pioneer-DJ-DDJ-400-2-channel-DJ-controller-Instruction-Manual)
- [DJworx — Pioneer DJ DDJ-400 (rekordbox beginner's box)](https://djworx.com/pioneer-dj-ddj-400-rekordbox-beginners-box/)
- [BPM Music Blog — Learn the Basics with Pioneer's New DDJ-400](https://blog.bpmmusic.io/news/learn-the-basics-with-pioneers-new-portable-and-affordable-controller-the-ddj-400/)
- [BPM Music Blog — Recording Your DJ Set: Do's & Don'ts](https://blog.bpmmusic.io/news/recording-your-dj-set-dos-donts/)
- [BPM Music Blog — How and Why to Use Loops as a DJ](https://blog.bpmmusic.io/news/how-and-why-to-use-loops-as-a-dj/)
- [Native Instruments — Maschine and Ableton Live Guide (community)](https://community.native-instruments.com/discussion/450/guide-getting-the-most-out-of-maschine-ableton-live-push)
- [Native Instruments — Maschine Studio Getting Started PDF](https://www.native-instruments.com/fileadmin/ni_media/downloads/manuals/maschine_276/MASCHINE_STUDIO_2.7.6_0518_Getting_Started_English.pdf)
- [Native Instruments Blog — Best Maschine tutorials 2024](https://blog.native-instruments.com/maschine-tutorials/)
- [Mixxx — Learning Resources Wiki](https://github.com/mixxxdj/mixxx/wiki/learning_resources)
- [Mixxx — DJing With Mixxx Manual](https://manual.mixxx.org/2.3/en/chapters/djing_with_mixxx.html)
- [Mixxx — Quickstart Manual](https://manual.mixxx.org/2.1/fi/chapters/quickstart)
- [Mixxx — Project Page](https://mixxx.org/)
- [Mixxx — Wiki Home](https://github.com/mixxxdj/mixxx/wiki/)
- [Mixxx — Open Source Tutorial (Digital DJ Tips)](https://www.digitaldjtips.com/how-to-dj-open-source-for-free-no-subscriptions-no-tie-ins/)
- [Mixxx — TechBloat Overview](https://www.techbloat.com/mixxx-the-best-free-and-open-source-dj-software-for-windows-macos-and-linux.html)

### AI DJ Copilot Prior Art
- [Harmovio — AI Copilot for DJs (App Store)](https://apps.apple.com/us/app/harmovio-ai-copilot-for-djs/id6752530143)
- [PulseDJ — AI DJ Copilot homepage](https://blog.pulsedj.com/)
- [Facebook Serato Group — Has anyone used PulseAI](https://www.facebook.com/groups/seratogroup/posts/2544668639217756/)

### DJ Schools & Curriculum Examples (cross-validation of order)
- [Bach to Rock — Beginner DJ Lessons (Beat Refinery)](https://www.bachtorock.com/beginner-dj-lessons/)
- [Bach to Rock — What Technical Skills Should DJs Know](https://www.bachtorock.com/blog/what-technical-skills-should-djs-know-blgpst/)
- [Bach to Rock — How to Create Your First DJ Setlist](https://www.bachtorock.com/blog/how-to-create-your-first-dj-setlist-tips-and-tricks-blgpst/)
- [Sol Passion Music — Beginner DJ](https://solpassionmusic.com/product/beginner-dj/)
- [Beginner DJ Lessons — Free Training](https://beginnerdjlessons.com/free-training-1)
- [Beginner DJ Lessons — Online DJ School](https://beginnerdjlessons.com/)
- [Beginner DJ Lessons — Entire DJ Course](https://beginnerdjlessons.com/entire-dj-1)
- [Skillshare — The Complete DJ Course for Beginners (Jak Bradley)](https://www.skillshare.com/en/classes/the-complete-dj-course-for-beginners-a-full-step-by-step-guide-to-djing/1692694063)
- [Udemy — Learn How To DJ - Beginner DJ Lessons](https://www.udemy.com/course/learn-how-to-dj-from-scratch/)
- [Udemy — How to Become a DJ - Learn How to Start DJing Online Today](https://www.udemy.com/course/online-dj-course/)
- [Udemy — The Complete DJ Course For Beginners (10 steps)](https://www.udemy.com/course/10steps2dj/)
- [Udemy — Ultimate Pioneer DJ Course Part 1](https://www.udemy.com/course/ultimate-pioneer-dj-course-part-1-of-2/)
- [Save the Music — DJ Resources and Tools for Music Learning](https://www.savethemusic.org/music-education-resources/music-tech-setup-guide/exploring-the-world-of-djing/)
- [LSA London Sound Academy — Beginner DJ Course](https://www.londonsoundacademy.com/courses/beginner-dj-course)
- [LSA — Best Pioneer DJ Course in the World](https://www.londonsoundacademy.com/blog/join-the-best-pioneer-dj-course-in-the-world-at-london-sound-academy)
- [LSA — 10 Hip-Hop DJ Transitions](https://www.londonsoundacademy.com/blog/10-hip-hop-dj-transitions)
- [School of Electronic Music — Complete DJ Course (4 months)](https://schoolofelectronicmusic.com/dj-courses/complete-dj-course/)
- [Pioneer India — Pioneer DJ in Education](https://pioneer-india.in/pdj/pioneerdj-in-education/)
- [United DJ School — Basic Course Pioneer DDJ-200](https://elearning.uniteddjschool.com/en/course/basic-course-pioneer-ddj-200/)
- [The DJ Coach — Free Pioneer DJ Course](https://thedjcoach.com/pioneerdj)
- [Make Me A DJ — Advanced DJ Course](https://makemeadj.com/online-courses/advanced-dj-course/)
- [London Amp — Advanced DJ Certificate Course](https://www.londonamp.com/courses/advanced-dj-certificate-course/)
- [Fruit Punch Course — How to DJ for Beginners 2026](https://www.fruitpunchcourse.com/blog/how-to-dj-for-beginners-2026-step-by-step-guide-to-start-mixing-like-a-pro)
- [Blackout Audio — How to Beatmatch by Ear: A Beginner's Guide](https://blackoutaudio.com/blogs/gear-guides/how-to-beatmatch-by-ear-a-beginner-s-guide)
- [Blackout Audio — BPM Key Matching for DJ Mixing](https://blackoutaudio.com/blogs/gear-guides/understanding-bpm-and-key-matching-for-djs)
- [Musical Advice — How to Beatmatch properly: The Ultimate Guide 2025](https://musicaladvice.com/dj/how-to-beatmatch/)
- [Musical Advice — What Are DJ Loops](https://musicaladvice.com/dj/what-are-dj-loops/)
- [Soundplate — DJ Pitch & Tempo Calculator](https://soundplate.com/dj-pitch-tempo-calculator/)
- [PlayVirtuoso — How to use DJ effects to improve transitions](https://playvirtuoso.com/blog/how-to-use-dj-effects-to-improve-your-transitions-and-blends/79)
- [Final Scratch — How to Transition When DJing](https://finalscratch.com/blog/how-to-dj-transition/)
- [Studio Scratches — Advice For Beginner Scratch DJs](https://studioscratches.com/advice-for-beginner-scratch-djs/)
- [Pointblank — A Beginner's Guide to Beat Matching for DJs](https://www.pointblankmusicschool.com/blog/a-beginners-guide-to-beat-matching-for-djs/)
- [DJ Aerodynamix — Wedding DJ vs Club DJ](https://djaerodynamix.ca/wedding-dj-vs-club-dj/)
- [Malta DJ Events — Wedding DJ vs Club DJ](https://maltadj.events/wedding-dj-vs-club-dj/)
- [Famous DJ Agency — Wedding DJ or Club DJ? Why Not Both?](https://www.famousdjagency.com/wedding-dj-or-club-dj-why-not-both/)
- [John Byrne Music — Wedding DJ vs Club DJ](https://www.johnbyrnemusic.com/post/wedding-dj-vs-club-dj-what-s-the-difference)
- [EDM Cave — Club DJ Vs Wedding DJ](https://edmcave.com/club-dj-vs-wedding-dj/)
- [DJ DDrop — Club DJ vs Wedding DJ](https://djddrop.com/drop-blogs/f/club-dj-vs-wedding-dj-why-the-right-one-matters-for-your-big-da)
- [Elegante Entertainment — Club DJ versus wedding DJ](https://www.fhpentertainment.com/blog/3687/club-dj-versus-wedding-dj/)
- [DropTrack — DJ Genres Explained](https://www.droptrack.com/dj-genres-explained-the-ultimate-guide-to-targeting-the-right-djs-for-your-music/)
- [DJ TechTools Forum — Difference between Hip Hop DJing vs EDM](http://forum.djtechtools.com/showthread.php?t=57103)
- [Music City SF — The Camelot Wheel Explained 2025](https://musiccitysf.com/accelerator-blog/camelot-wheel-dj-mixing-guide/)
- [Mixed In Key — Use Advanced Harmonic Mixing Techniques](https://mixedinkey.com/book/use-advanced-harmonic-mixing-techniques/)
- [Mixed In Key — Harmonic Mixing 101](https://mixedinkey.com/integration/harmonic-mixing-101/)
- [Mixed In Key — Interview with Mark Davis](https://mixedinkey.com/book/how-to-use-harmonic-mixing/interview-with-mark-davis/)
- [Mixed In Key — The Art of DJing: Practice makes perfect](https://mixedinkey.com/wiki/the-art-of-djing-practice-makes-perfect/)
- [Y2Mate Group — First DJ Set Roadmap: Bedroom to Gig 2025](https://y2mate.group/first-dj-set-roadmap/)
- [Musicianstool — Building the Perfect DJ Set from Scratch](https://musicianstool.com/blog/building-the-perfect-dj-set-from-scratch)
- [DJ.studio Help — BPM Controls Tips and FAQs](https://help.dj.studio/en/articles/8261956-bpm-controls-tips-and-faqs)
- [DJ.studio Help — Tips and Tricks](https://help.dj.studio/en/articles/8124421-tips-and-tricks)
- [DJ.studio Academy — How to create Loop effects](https://dj.studio/academy/effects-loop)
- [DJ.studio — DJ Mix Workflows for Effects, Loops and Automation](https://dj.studio/blog/creative-powerhouse-workflows-effects-loops-mashups-automation-structured-dj-mixes)
- [DJ.studio — DJ Set Preparation](https://dj.studio/blog/dj-set-preparation)
- [Sweetwater — Getting Started with DJ Controllers](https://www.sweetwater.com/sweetcare/articles/getting-started-with-dj-controllers/)
- [Become Singers — DJ Mixer's Parts, Features Control Knobs and Buttons](https://becomesingers.com/on-stage/dj-mixer-parts-features)
- [Beats By Jay — What do the Buttons on the DJ Controller Do?](https://www.beatsbyjaynj.com/post/what-do-the-buttons-on-the-dj-controller-do)
- [OBSBOT — The Ultimate Beginner DJ Setup Guide 2026](https://www.obsbot.com/blog/music-production/beginner-dj-setup)
- [The DJ Revolution — DJ Mixer Basics: EQ'ing, Faders and Levels](https://www.thedjrevolution.com/a-quick-introduction-to-dj-mixers-eqing-faders-and-levels/)
- [Thomann Blog — DJ Controllers: A Beginner's Guide to Getting Started](https://www.thomann.de/blog/en/learn/dj-controllers-a-beginners-guide/)
- [Music On Stage — Pioneer DJ Equipment Explained Beginner's Guide 2025](https://www.musiconstage.com.au/blog/pioneer-dj-equipment-explained-complete-beginners-guide-2025/)
- [Music And Film Academy — DJ Mixer Techniques: Gain Staging and EQ 2026](https://musicandfilmacademy.ac.ke/music-tech-resources/dj-mixer-techniques-gain-staging-eq-guide/)
- [SchoolJournalism — DJ Basics Radio Curriculum (DC Public Schools CTE)](https://www.schooljournalism.org/wp-content/uploads/2013/09/C1L25_Music_DJ-Basics.pdf)
- [DJ Sizzle — Connecting with Your Audience: Reading the Crowd](https://djisizzle.com/connecting-with-your-audience-reading-the-crowd-and-building-energy/)
- [DJ Gym — How to Prepare For Your First DJ Gig](https://www.djgym.co.uk/post/how-to-prepare-for-your-first-dj-gig-avoid-common-mistakes)
- [DJ Diaries — Common DJ Mistakes and How to Avoid Them](https://thedj-diaries.com/common-dj-mistakes-and-how-to-avoid-them/)
- [DJs of Charleston — How DJs Read the Crowd and Build the Perfect Party Flow](https://www.djsofcharleston.com/post/how-djs-read-the-crowd-and-build-the-perfect-party-flow)
- [Audiomunk — Gain Staging for DJs](https://audiomunk.com/gain-staging-for-djs/)
- [Audio Mixer — How to Set Proper Gain Staging for Live Events](https://www.audio-mixer.com/tutorials/how-to-set-proper-gain-staging-for-live-events/)
- [iZotope — Gain Staging: What It Is and How to Do It](https://www.izotope.com/en/learn/gain-staging-what-it-is-and-how-to-do-it)
- [MixMaster Pro — A Beginner's Guide to Gain Staging](https://mixmasterpro.io/articles/gainstaging)
- [DJ Times — DJ Sound Redlining Booth Levels](https://www.djtimes.com/2020/03/dj-sound-redlining-booth-levels/)
- [DJ Sondemand — The Most Common DJ Mistakes Beginners Make](https://www.djsondemand.co.uk/the-most-common-dj-mistakes-beginners-make/)
- [Heavy Hits — The Absolute Best Way to Organize Your Virtual Crates](https://heavyhits.com/blog/the-absolute-best-way-to-organize-your-virtual-crates/)
- [Digital DJ Pool — DJ Scratch Techniques](https://digitaldjpool.com/blog/dj-scratch-techniques)
- [Jazzy Joe — The Role of Loops and Samples in DJ Mixing](https://jazzyjoe.com/the-role-of-loops-and-samples-in-dj-mixing/)
- [Amplified Discos — 3 Ways To Use A DJ Loop](https://amplifieddiscos.co.uk/ways-to-use-a-dj-loop/)
- [DJ Gear 2K — How To Organize Your Tracks/Songs](https://djgear2k.com/how-to-organize-your-tracks-dj-playlist-guide/)
- [Phil Morse — The New Mobile Dj Blueprint](https://www.course55.com/product/the-new-mobile-dj-blueprint-phil-morse/)
- [Luna Course — Phil Morse The All-New Complete DJ Course](https://lunacourse.com/product/phil-morse-the-all-new-complete-dj-course/)
- [Digital DJ Tips — 5 Steps Mixing Podcast](https://www.digitaldjtips.com/5-steps-mixing-podcast/)
- [Digital DJ Tips — 5 Steps Gear Podcast](https://www.digitaldjtips.com/5-steps-gear-podcast/)
- [Digital DJ Tips — 6 Easy Ways To Record Your DJ Sets](https://www.digitaldjtips.com/7-easy-ways-to-record-your-dj-sets/)
- [Digital DJ Tips — Complete Guide To Switching From DJ Controllers to CDJs](https://www.digitaldjtips.com/complete-guide-to-switching-from-controllers-to-cdjs/)
- [Digital DJ Tips — Free Pioneer DJ CDJ-3000 Training Tutorial](https://www.digitaldjtips.com/free-pioneer-dj-cdj-3000-training-tutorial-video-manual/)
- [Digital DJ Tips — Help, the DJ booth has no monitors](https://www.digitaldjtips.com/dj-booth-has-no-monitors/)
- [Digital DJ Tips — Complete DJ Course funnel page](https://1.digitaldjtips.com/complete-dj-course-info)
- [Digital DJ Tips — Complete DJ Course info-22](https://digitaldjtips.clickfunnels.com/complete-dj-course-info-22)
- [Pioneer DJ — DJ Controllers product page](https://www.pioneerdj.com/en/product/dj-controllers/)
- [How To Setup Pioneer DJ CDJs & DJM Mixer YouTube](https://www.youtube.com/watch?v=Z2l9fouLGrw)
- [How Pro DJs Use Waveforms YouTube](https://www.youtube.com/watch?v=TPTbGmyfdeM)
- [How to Count Phrases & Identify the Main ONE Beat (Music Theory for DJs) YouTube](https://www.youtube.com/watch?v=kpsvKJ_6bsc)
- [Echo Out Transition Tutorial YouTube](https://www.youtube.com/watch?v=R5xVG7cL4eA)
- [How To DJ For Beginners (Your First Set) YouTube](https://www.youtube.com/watch?v=FuWvvsFhKaA)
- [How To Set DJ Cue Points Pioneer XDJ-RX YouTube](https://www.youtube.com/watch?v=fV4HBAam9iU)
- [Crossfader YouTube channel](https://www.youtube.com/channel/UCM4u0gp8gm99w9MXQ7ZI8Mw)
- [Pioneer DJ Forums — Beginner Questions](https://forums.pioneerdj.com/hc/en-us/community/posts/360043223012-ABSOLUTE-BEGINNER-QUESTIONS)
- [Pioneer DJ Community — Beginner Questions (2)](https://community.pioneerdj.com/hc/en-us/community/posts/22978525373209-ABSOLUTE-BEGINNER-QUESTIONS)
- [Pioneer DJ Forums — HOT CUES AUTOPLAY](https://forums.pioneerdj.com/hc/en-us/community/posts/205049143-HOT-CUES-AUTOPLAY)
- [Pioneer DJ Forums — Booth output vs master output](https://forums.pioneerdj.com/hc/en-us/community/posts/203035269-booth-vs-master-output)
- [Pioneer DJ Forums — DJM 2000 Booth Output](https://forums.pioneerdj.com/hc/en-us/community/posts/203031739-DJM-2000-Booth-Output)
- [Pioneer DJ Forums — Waveform View in Rekordbox DJ](https://forums.pioneerdj.com/hc/en-us/community/posts/115017849783-Waveform-View-in-Rekordbox-DJ)
- [Pioneer DJ Forums — Pitch tempos and beat matching](https://forums.pioneerdj.com/hc/en-us/community/posts/203092929-pitch-tempos-and-beat-matching)
- [DJ TechTools Forum — Mixer to monitors: main output or booth output](https://forum.djtechtools.com/showthread.php?t=89915)
- [DJ TechTools Forum — Mixer to monitors thread 2](https://forum.djtechtools.com/t/mixer-to-monitors-main-output-or-booth-output/72820)
- [Serato.com Forum — Booth output vs master out](https://serato.com/forum/discussion/107003)
- [Matchfy Blog — How to set up Rekordbox and Serato Best settings](https://blog.matchfy.io/how-to-set-up-rekordbox-and-serato-best-settings/)
- [MOD WIGGLER — Mastering techno: how do they get the huge looking waveforms](https://www.modwiggler.com/forum/viewtopic.php?t=182080)
- [DJ Song Match (YesChat GPT)](https://www.yeschat.ai/gpts-2OToA3QzPK-DJ-Song-Match)

### Cross-Reference / Internal vibemix
- `.planning/PROJECT.md` (existing capabilities — v8.x shipped)
- `.planning/REQUIREMENTS.md` (existing REQ structure to mirror)
- `src/vibemix/midi/profiles/pioneer_ddj_flx4.json` (sample profile shape)
- `src/vibemix/state/event_detector.py` (PHASE / LAYER_ARRIVAL / MIX_MOVE detector reuse for proactive co-pilot)
- `src/vibemix/state/evidence_registry.py` (citation grounding seam for lesson commendations)
- `src/vibemix/harmonics.py` (Camelot table for L2.11)
- `src/vibemix/library/clap_engine.py` (CLAP exemplar-query for L1.14)
- `src/vibemix/coach/` (persona/lens seam for the tutor lens)
- `mocks/vibemix-rebuild-session.html` (Deck-Speaks aesthetic — hardware-mirror UI extension target)

---
*Feature research for: v9.0 "Lesson One" beginner learning module*
*Researched: 2026-05-27*
*Mode: Project Research — FEATURES*
*Default-YES applied per Kaan brief; anti-features are minimum-viable list.*
