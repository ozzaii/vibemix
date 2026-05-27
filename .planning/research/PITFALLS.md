# Pitfalls Research — v9.0 "Lesson One" Beginner Learning Module

**Domain:** AI-narrated interactive DJ pedagogy + hardware visualization + cued-audio playback inside an existing live-grounded co-host
**Researched:** 2026-05-27
**Confidence:** HIGH on tone/copyright/audio-routing/hardware-variation/integration; MEDIUM on lesson-gating thresholds and CodexAgent-vs-Gemini tone parity (no live A/B yet); LOW on long-tail firmware×OS combinatorics until Phase-9.X probe matrix runs.

> Supersedes the prior v6.0-pointer file (which itself archived the v6.0 Memory-Turn pitfalls). v6.0 pointer guidance about CLAP/embedding contracts is still in force; this file extends it for v9.0 scope.

**Reading order for downstream planners:** P1 (tone) and P9 (citation grounding) and P5 (copyright) are the three "block the milestone" risks. P3+P4+P8 are the hardware-renderer risk cluster. P6+P7 are audio-pipeline risks. P11+P12+P13 are platform/integration risks. P14+P16+P17 are governance.

---

## Critical Pitfalls

### P1: AI TUTOR TONE — the "Great question! Today we'll be learning…" failure class

**What goes wrong:**
30+ scripted lesson lines reduce to a soft "voice-assistant doing music commentary." Every transition gets a "Great job!" Every misstep gets a "No worries, let's try that again!" The bestie line lands the *first* time then ages immediately into a verbal tic. Users churn at Lesson 3 because the AI sounds like every other ed-tech mascot.

**Why it happens:**
- Pedagogy literally requires repetition and encouragement → cargo-culted into "always affirm, always rephrase the prompt back, always say what we're about to learn."
- LLMs trained on customer-service + edtech corpora default to four learned moves: (1) compliment the user, (2) summarize what they just did, (3) state what's coming next, (4) close with an upbeat hook. Each individually fine; all four every turn is the slop.
- Tutor-mode prompts in v8.1 LENS were tuned for *one-off* live coaching (drop-in feedback), not 30-turn sustained pedagogy. The persona collapses under conversational length.

**Evidence:**
- Khanmigo specifically called out for "repetitive Socratic prompts," "awkward repetition" in non-math subjects, and Dan Meyer's documented finding that it eventually gives in and just produces the answer when pressured. ([myengineeringbuddy.com](https://www.myengineeringbuddy.com/blog/khanmigo-reviews-alternatives-pricing-offerings/), [danmeyer.substack.com](https://danmeyer.substack.com/p/the-chatbot-tutors-are-sick-of-your))
- Duolingo Max "Lily" character: reviews flag "scripted dialogue," 30s clips, "brief and generic" complex-question responses, "too scripted and basic" for advanced learners. ([copycatcafe.com](https://copycatcafe.com/blog/duolingo-max))
- Game-tutorial pedagogy research: minimal-guidance and dialogue-heavy tutorials BOTH show high abandonment when the player perceives "the game thinks I'm dumb." Coding-tutorial abandonment research traces it to "frustration" and "boredom," both amplified by scripted-feeling dialog. ([popmatters.com](https://www.popmatters.com/111485-active-learning-the-pedagogy-of-the-game-tutorial-2496084217.html), [psychologyofgames.com](https://www.psychologyofgames.com/2012/09/how-game-tutorials-can-strangle-player-creativity/), [arxiv.org](https://arxiv.org/pdf/1707.04291))
- Project's own existing `AI_SLOP_BLOCKLIST` at `scripts/launch/check_no_ai_slop.py:78` catches "seamless / intuitive / powerful / delightful experience / AI-powered" but it's tuned for MARKETING COPY; it does NOT catch the tutor-specific slop class ("Great question!", "Wonderful!", "You're doing great!", "Today we'll be learning…", "Let's dive in!", "Awesome!", "Got it!", "Don't worry, you'll get the hang of it.").

**How to avoid:**
1. **Tutor-mode AI-slop blocklist v2** — Phase 9.TONE introduces a SECOND blocklist scoped to tutor reactions: ≥20 tokens covering compliment-tics, transition-tics, and the "Today we're going to learn about X" preamble. CI-gated like `check_no_ai_slop.py` is for marketing copy. Test in `scripts/launch/check_no_tutor_slop.py` + invoked per tutor reaction in dev runs.
2. **Lesson scripts are HAND-AUTHORED, not LLM-generated** — the 30+ lesson lines are written by Kaan (or a DJ writer) once, stored as MD/JSON, and the AI ONLY adds the *grounded interjection* on top (e.g. "you ARE turning that knob now — that's the high band coming out"). The lesson SPINE is deterministic; the AI fills *one* live observation per beat. Same pattern as the existing `coach.py::task_for_event` which is hand-authored, not generated.
3. **Forbid the four learned moves in the system instruction:** "Do NOT compliment user actions. Do NOT summarize what just happened in lesson terms. Do NOT preview what's next. Do NOT close with an upbeat hook. State ONE grounded observation about what you HEAR in the audio + ONE forward sentence the lesson script provided. That's it."
4. **Per-lesson tone audit** — Kaan listens to each of the 30+ lessons end-to-end before ship. Ear-pass gate, mirrors the existing Phase 16 ear-test gate.
5. **The opening "bestie don't worry" line is scripted and ONE-TIME** — never recycled, never paraphrased mid-curriculum. Subsequent reassurance language must come from the hand-authored lesson script, not the AI.

**Warning signs:**
- Same compliment phrase appears in ≥2 lessons → blocklist hit
- AI says "Today we'll" / "Let's learn" / "By the end of this lesson" — those should ONLY appear in the hand-authored script intro
- Two consecutive AI lines that don't reference a *measured* event from the audio
- "User Sentiment" thread on reddit/discord that opens with "the AI sounds like Duolingo" — the canonical failure signal

**Phase to address:** Phase 9.TONE (must run *before* any lesson content gets written). Phase 9.UAT (Kaan ear-pass on all 30+ lessons before milestone close).

**Verdict:** **MUST-ADDRESS NOW in v9.0.** This is the v9.0 equivalent of Invariant #2 — break it and the milestone fails no matter how beautiful the UI is.

---

### P2: PEDAGOGICAL ORDER — teaching beatmatching before phrase awareness, sync before EQ

**What goes wrong:**
User opens Lesson 1, gets thrown into "beatmatch this." Or sync first → they never learn to hear drift. Or scratching before crossfade fundamentals. They fail at Lesson 3 because Lesson 2 didn't teach the prerequisite. Churn.

**Why it happens:**
- "Beatmatching is the foundational skill" is the conventional answer (Point Blank Music School, Crossfader) — but it's the *PROGRAM* foundational skill, not the *FIRST LESSON* skill. First-lesson goal is "make a transition that doesn't sound bad," which requires: track loaded, channels balanced, faders intuited, ONE EQ kill, gradual swap. Beatmatching by ear comes after the user has the rough motor map.
- DJ instructors disagree on scratch placement: Bach to Rock requires Mixing Level 1 before Scratching enrollment (mixing first). Other guides treat baby scratch as foundational. **For a Beginner module, scratching is OUT — it's an Intermediate/Pro skill.** ([bachtorock.com](https://www.bachtorock.com/dj-scratching-lessons/))
- Sync vs. ear-beatmatching is the modern DJ holy war. Beginners on club gear with sync available get told "sync is fine for now, ear-beatmatching is a skill you'll grow into." Pure-ear-first pedagogy alienates 90% of modern beginners. ([wearecrossfader.co.uk](https://wearecrossfader.co.uk/blog/learn-to-dj-the-complete-beginners-guide/))

**Evidence:**
- "Build foundational knowledge of bars and beats first… beatmatching as the core skill… mixing with EQ comes AFTER tracks are in sync" (Point Blank, Crossfader sources).
- Bach to Rock's L1→Scratch gate confirms scratch is a post-mixing-fundamentals skill.
- The PROJECT.md already lists "User levels: Beginner / Intermediate / Pro" with persona prompts → the persona separation EXISTS but doesn't yet enforce content separation.

**The canonical Lesson 1–10 order (anti-failure recommended):**
1. **Anatomy of the controller** (jog wheel, tempo fader, EQ knobs, channel faders, crossfader, cue buttons) — purely orientation, no music yet.
2. **Loading two tracks + master listen** (deck A loaded, deck B loaded, listen to deck A on master).
3. **Channel fader vs crossfader** (what each does, transition with NO beatmatching using just faders → sounds bad on purpose, demonstrates the *need* for the next lessons).
4. **EQ blend** (one knob: kill the lows on incoming, swap, restore on swapped → first "real" transition).
5. **Tempo fader + sync button** (what sync does, hear two tracks aligned; beginners on modern controllers SHOULD use sync — be honest about it).
6. **Hearing the kick — phrase awareness** (count 4, count 8, count 16, hear where the "1" lands) — this is the unlock for the next 4 lessons.
7. **Cue point + drop-in** (introduce next track on the phrase boundary, NOT randomly).
8. **EQ blend + phrase awareness combined** (the first transition that sounds *like a DJ* did it).
9. **Filter intro** (high-pass sweep on outgoing as you blend).
10. **First full mix end-to-end** (combine all the above).

EXPLICIT OUT for the Beginner module: scratching (any kind), loops/beat-jump, effects beyond the filter, hot cues beyond cue 1, stem isolation, sampler. Those belong in v9.x Intermediate.

**How to avoid:**
1. Order the 10 lessons exactly as above (or a Kaan-blessed re-ordering with the same gating semantics).
2. Each lesson has explicit *prerequisites* declared in metadata + the lesson-flow engine refuses to skip ahead until prereqs complete.
3. Each lesson has an explicit *out-of-scope-for-this-lesson* list (so the AI doesn't mention sync in Lesson 4 even if the user asks about it).
4. Phase 9.PEDAGOGY runs the ordering past a beginner-track DJ instructor (Kaan or a Francesco contact) for sanity check.

**Warning signs:**
- User completes Lesson 1 then drops at Lesson 2 → Lesson 2 demands a prereq Lesson 1 didn't teach
- "Can I just skip ahead?" support inquiries → pedagogy isn't motivating the order
- Lesson taking >2× the expected time → step granularity too coarse

**Phase to address:** Phase 9.PEDAGOGY (curriculum-design phase, must lock order before Phase 9.CONTENT writes the 30+ lesson scripts).

**Verdict:** **MUST-ADDRESS NOW in v9.0.** Wrong order = abandonment = milestone fails its "warm Bravoh audience" goal.

---

### P3: HARDWARE VARIATION — firmware × USB string × OS combinatorics

**What goes wrong:**
"Plug in your DDJ-FLX4" → renderer shows FLX4 layout → but the user has the FLX4 v1.07 with the Beat-FX behavior change, and a CC fires differently. The lesson "press BEAT FX" doesn't progress because the MIDI event the lesson script expected doesn't arrive. User feels broken.

Or worse: USB iSerialNumber is absent on the cheaper controllers (Numark Party Mix Live, Hercules Inpulse 200) → re-plugging into a different USB port creates a "new device" on Windows + macOS → auto-detection fires twice / loses state.

**Why it happens:**
- AlphaTheta ships firmware updates that change MIDI behavior (FLX4 v1.07 explicitly changed Beat-FX behavior with the BEAT FX CH SELECT switch under rekordbox connection). ([pioneerdj.com](https://www.pioneerdj.com/en/news/2025/ddj-flx4-firmware-update-107/))
- Hercules Inpulse 300 has firmware v1.72 with auto-detection in DJUCED; older firmware behaves differently in 3rd-party software. ([djuced.com](https://www.djuced.com/kb/hercules-djcontrol-inpulse-300-mapping-and-manual/))
- Cheap USB MIDI devices often skip the iSerialNumber descriptor; OS falls back to port-derived identification → same controller appears as different devices across ports. ([devblogs.microsoft.com](https://devblogs.microsoft.com/windows-music-dev/the-importance-of-including-a-unique-iserialnumber-in-your-usb-midi-devices/))
- Existing project state: v7.0 Phase 68 reconciled `midi/profiles/*.json` to single source — 10 controllers. But the profiles assume *single* firmware per controller; there's no `firmware_minimum` field in the schema, and there's no MIDI-event self-test ("touch the play button to confirm we agree on CC#") on first run.

**Variation matrix (v9.0 scope — 10 controllers):**

| Controller | Known firmware variants | Notable MIDI variation surface |
|---|---|---|
| Pioneer DDJ-FLX4 | v1.00, v1.04, v1.07 (current) | Beat FX behavior change at v1.07 under rekordbox; CC layout otherwise stable |
| Pioneer DDJ-FLX6 | v1.00–v1.04 | 4-channel layout vs FLX4's 2-channel; 16 pads vs 8; built-in sound card |
| Pioneer DDJ-FLX10 | v1.00–v1.0X | Motorized jog wheels (different jog-wheel CC behavior), Serato+rekordbox dual license |
| Pioneer DDJ-400 | v1.00–v1.05 | Legacy, stable; rekordbox-first |
| Pioneer DDJ-1000 | v1.00–v1.0X | 4-channel professional; on-jog displays |
| Pioneer DDJ-SX3 | v1.00–v1.04 | Serato-first; SX2 → SX3 different MIDI maps |
| Pioneer XDJ-RX3 | v1.00–v1.0X | Standalone player (not just controller); MIDI surface limited when in standalone mode |
| Numark Party Mix Live | v1.00 | Cheapest tier; iSerialNumber may be absent; built-in speakers can be confused for output device |
| Hercules Inpulse 300 | v1.72, MK2 (2023) | MK2 is a different SKU with different MIDI map; same product NAME |
| Hercules Inpulse 500 | v1.00–v1.0X | 4-channel; pads layout differs from 300 |

**The latent killer:** Hercules Inpulse 300 vs. Inpulse 300 MK2 (2023) — DJUCED treats them as different controllers with different MIDI maps. ([djuced.com](https://www.djuced.com/kb/hercules-djcontrol-inpulse-300-mk2-2023-mapping-and-manual/)) If vibemix collapses them into one profile, the MK2 user gets wrong-layout renderer + wrong-event lesson flow. Same name, different hardware.

**How to avoid:**
1. **MIDI self-test on first connection** — Phase 9.HARDWARE includes a 30-second "press your play button → press the EQ knob → press cue button A" confirmation flow that VERIFIES the profile matches the controller (CC numbers match the profile). If mismatch, fall back to graceful generic-controller mode + offer "report this layout" hook.
2. **Schema extension** — add `firmware_min`, `firmware_known_variants`, `serial_pattern` (if known) to profile JSON. Test in `tests/midi/test_profile_variants.py`.
3. **Inpulse 300 vs MK2** — TWO distinct profile files (`hercules-inpulse-300.json`, `hercules-inpulse-300-mk2.json`); first-run probe picks by MIDI signature.
4. **iSerialNumber-less hot-plug** — re-use Phase 33's TCC wizard pattern; on re-plug, prefer profile-match by MIDI signature over USB-port match.
5. **Generic-controller fallback** — if no profile matches, render a stylized "generic 2-channel" layout with labeled-zones and let the lesson advance via *audio-detected* state changes (EQ kill detected via audio band-energy drop) instead of MIDI events.

**Warning signs:**
- Lesson stuck on "press the play button" for >15s → MIDI handshake mismatch
- User reports "the highlight is on the wrong knob" → profile mis-detected
- Same USB device shows up twice in MIDI device list across reboots → iSerialNumber issue

**Phase to address:** Phase 9.HARDWARE (MIDI self-test + profile-variant schema + fallback). Phase 9.UAT extends to per-controller smoke (at least FLX4, Inpulse 300, Party Mix Live).

**Verdict:** **MUST-ADDRESS NOW in v9.0** for the 3 most-likely beginner controllers (FLX4, Inpulse 300, Party Mix Live); MONITOR for the long tail (FLX10, XDJ-RX3, SX3) which beginners rarely buy.

---

### P4: CONTROLLER RENDERER ACCURACY — "the AI says press cue but I can't find it"

**What goes wrong:**
The on-screen vector rendering of "DDJ-FLX4" has the CUE button drawn 4 cm right of where it actually sits on the user's controller. AI says "press cue A — it's on the left under your jog wheel." User looks at the screen, looks at the controller, doesn't match, freezes. Lesson dies.

**Why it happens:**
- The rendered controller is a *symbolic* approximation; physical-fidelity drift creeps in over 10 SKUs × multiple firmwares.
- Maintenance cost: 10 controllers × hand-authored SVG = ~80–120 hours of vector authoring + verification.
- Without a CI gate, the SVG can drift (someone adds a button, moves a knob) and nothing fails until a user complains.
- Two failure modes: (a) the SVG is geometrically wrong from day one (authoring error), (b) the SVG is right but the highlight-coords-by-MIDI-cc lookup table is wrong (mapping error).

**How to avoid:**
1. **Photo-overlay verification** — for each controller, take a top-down photo (or pull from manufacturer press kit), overlay the SVG at 50% opacity, verify alignment. CI gate stores the overlay snapshot in `tauri/ui/tests/controller/__snapshots__/`.
2. **Highlight-by-MIDI-CC mapping test** — given a MIDI event from a real device, the renderer SHOULD highlight the correct visual element. Test in `tauri/ui/tests/controller/highlight-by-cc.test.ts`, parameterized over all profile CC entries.
3. **Generic-controller fallback that DOESN'T claim physical layout** — if confidence < high, render a labeled-zone layout ("Channel A volume", "Channel B EQ") instead of a fake-realistic controller layout the user will try to map and fail to match.
4. **Ship 3 controllers in v9.0** — FLX4 (most-bought beginner controller), Inpulse 300 (Hercules beginner-default), Party Mix Live (cheapest tier). Other 7 ship with generic-controller layout + "we don't have your exact controller pictured yet, here's a labeled view" honest-null. Defer full art for those 7 to v9.x.
5. **Anti-creep: the renderer is NOT photorealistic.** Stylized vector art with restraint (CDJ-Whisper amber accent on charcoal). Photorealism is BOTH a copyright risk (P5) and a maintenance burden.

**Warning signs:**
- User reports "I pressed the right button but the lesson didn't advance" → MIDI→highlight mismatch
- User reports "the screen shows a button I don't have on my controller" → SVG drift / wrong profile
- Highlight flashes on the wrong location even when correct MIDI fires → mapping table desync

**Phase to address:** Phase 9.RENDERER (vector authoring + CI gate). Phase 9.HARDWARE wires the mapping. Phase 9.UAT verifies per-controller.

**Verdict:** **MUST-ADDRESS NOW in v9.0** with 3-controllers-shipped scope; long-tail fidelity DEFERRED to v9.x with graceful fallback.

---

### P5: PHOTOREALISTIC CONTROLLER ART + COPYRIGHT / TRADEMARK

**What goes wrong:**
We render the DDJ-FLX4 by lifting Pioneer's faceplate photography or rebuilding it photorealistically with Pioneer's exact color palette + logo + "Pioneer DJ" trade dress. Pioneer's IP lawyers send a cease-and-desist. We pull the feature mid-launch.

**Why it happens:**
- Photorealism feels "professional" → designer instinct → designer takes Pioneer press photo as the reference and lifts too much.
- Pioneer's marks are extensive: "Pioneer," the Pioneer logo, "APP Mode," "NEX," "Digital Bass Control," "MIXTRAX," "Pioneer Smart Sync" are all registered. Logo is the easy copy-trap. ([usa.pioneer](https://usa.pioneer/pages/trademarks))
- Trade dress (the overall look-and-feel of the product) is also protectable in the US — distinctive-product-design trade dress can stop look-alike rendering even when no logo is copied.

**The legal line (working theory, not legal advice):**

| Approach | Risk |
|---|---|
| Photo of the controller lifted from Pioneer's site | **HIGH** — direct copyright infringement of the photograph (Pioneer owns the photo) + trademark dress |
| Photorealistic vector rendering with Pioneer logo + exact colors | **HIGH** — trade dress + trademark misuse (could imply endorsement) |
| Photorealistic vector rendering WITHOUT Pioneer logo + exact colors | **MEDIUM** — still trade dress risk |
| Stylized schematic vector (CDJ-Whisper aesthetic — amber on charcoal, simplified geometry, NO logo, NO "Pioneer DJ" text) used to teach button-location semantics | **LOW** — nominative fair use territory: we're identifying the user's controller for compatibility purposes, not selling a Pioneer-branded product. Mixxx, Serato, Algoriddim all do this for compatibility tables. |
| Use the controller's NAME ("DDJ-FLX4") in lesson text | **LOW** — nominative fair use is settled law for "software compatible with X" usage |

**Evidence:**
- Nominative fair use is the operative doctrine for identifying a third-party product (e.g., "software compatible with APPLE") and is well-established in trademark law. ([trademarklawyerfirm.com](https://www.trademarklawyerfirm.com/what-is-trademark-fair-use/), [500law.com](https://500law.com/fair-use-trademark-service-mark/))
- Mixxx ships device-specific mappings and screenshots, naming "Pioneer DDJ-SX" / "Pioneer DDJ-FLX4" / "Hercules Inpulse 300" directly without apparent objection over years. ([mixxx.org](https://mixxx.org/screenshots/), [Mixxx wiki Pioneer DDJ controllers](https://github.com/mixxxdj/mixxx/wiki/Pioneer-Ddj-Controllers)) — strong precedent.
- Serato's hardware-compatibility pages name and picture Pioneer / Numark / Hercules controllers; they have explicit licensing agreements where applicable (DDJ-SX is "developed specifically for Serato DJ Pro"). vibemix does NOT have such agreements — relies on nominative fair use only.

**How to avoid:**
1. **Locked visual policy:** stylized CDJ-Whisper schematic vector — no Pioneer logo, no "Pioneer DJ" wordmark on the rendered controller, NO use of Pioneer's exact orange/blue brand colors. Use the existing project amber accent on charcoal — coincidentally matches the visual direction.
2. **Naming policy:** in text, always "Pioneer DDJ-FLX4" or "your DDJ-FLX4" — that's nominative fair use. Never claim "official Pioneer support" or "Pioneer-endorsed."
3. **Disclaimer in app + repo:** small text near the renderer: "Visual representation for instructional use. DDJ-FLX4, XDJ-RX3 etc. are trademarks of AlphaTheta / Pioneer DJ. Inpulse is a trademark of Hercules. vibemix is not affiliated with or endorsed by these manufacturers." Mirrors what Mixxx does.
4. **No use of vendor press photos** — every visual asset hand-authored from public-domain references (geometry / button counts / labels) only.
5. **Legal review** — KAAN-ACTION: have a lawyer (or at minimum Francesco's network) sight-read the rendered controllers and the disclaimer copy before public release. Cheap insurance.

**Warning signs:**
- A designer mockup includes the Pioneer logo or Pioneer's orange — escalate immediately
- "It looks just like the real thing!" feedback — that's the trade-dress red zone
- Manufacturer cease-and-desist (would arrive via Apache LICENSE contact / GitHub abuse channel) — immediate pull

**Phase to address:** Phase 9.RENDERER locks visual policy + disclaimer copy. Phase 9.LEGAL (small phase) gets Kaan/lawyer sign-off before public ship.

**Verdict:** **MUST-ADDRESS NOW in v9.0.** Launch-gating risk equivalent to the API-key-in-binary problem already called out as "the API-key-protection problem of the year." Mixxx-precedent path is well-trodden and safe; photo lifting is launch suicide.

---

### P6: EXEMPLAR ENGINE RELIABILITY — small library, mislabeled tracks, fake mid-share

**What goes wrong:**
User opens "Pick a track from your library with prominent mids" lesson. Their library is 5 tracks of monogenre hardtechno. ALL of them have the same band distribution. The engine picks "the most prominent mid example" which is *not actually* mid-prominent — it's just least-not-prominent. AI confidently says "here's a track with prominent mids" → user plays it → mids are not prominent → AI lied.

Worse: heavily-compressed kick drums fake mid-band energy (compression sidebands leak into the mid band). A pure-kick-driven track gets selected as a "mid prominent" exemplar. AI lies; user is confused.

**Why it happens:**
- Band-share scalar (sub/low/mid/high RMS ratios) is the project's existing signal (`MusicState.bands`) — it's a *relative* measure, not absolute. If the entire library is similar, "most prominent X" can be falsely small.
- CLAP embeddings (the project's library engine) are 512-dim semantic vectors — they capture *vibe* not *band balance*. "Mid prominent" is a DSP property, not a CLAP property. The library engine doesn't expose this dimension.
- The library may be incomplete (CLAP embeddings missing for some tracks → those are silently skipped).
- Audio decode can fail on some files (.flac with weird tags, .m4a from streaming-rip, corrupt mp3).
- Mislabeled metadata: Rekordbox tag says "Track Name (Original Mix)" but the file is the radio edit with mids cut.

**Evidence:**
- CLAP literature confirms text→audio is reliable for COARSE properties only (genre at coarse level) — fine-grained "this track has prominent mids" is below the discrimination threshold. ([huggingface.co/docs/transformers CLAP](https://huggingface.co/docs/transformers/model_doc/clap), [arxiv.org CLAP paper](https://arxiv.org/pdf/2206.04769)). Also noted in the project's own CLAUDE.md: *"text→audio is reliable for coarse genre, not fine vibe."*
- Class-centroid pattern (compute centroid of exemplar class, query) works at small training-set sizes — but requires HAVING exemplars to compute the centroid, which we don't have for "prominent mid" because mid-prominent-tracks-in-your-library is the thing we're trying to FIND.
- Small-library exemplar selection: known weakness of embedding-based retrieval; standard mitigation is honest-null with packaged fallback.

**How to avoid:**
1. **DSP-band exemplar engine (NOT CLAP)** — for "find a track with prominent X band," compute per-track band-energy distributions from the cached audio decode (Phase 90's CLAP pipeline already decodes audio for embedding — share the decode result). Pick the track with highest absolute-AND-relative band-X energy. CLAP is the wrong tool here.
2. **Compressed-kick guard** — if mid-band energy is highly correlated with sub-band energy (Pearson r > 0.8 over a 10s window), flag the mid-energy as suspect kick-sideband and EXCLUDE that track from mid-prominent picks.
3. **Confidence threshold + honest-null** — if no track scores above a confidence floor (say, top-1 score < 2× median), the AI says: "your library doesn't have a great example of prominent mids — let me play you one we packaged." Mirrors Invariant #3 ("trust the audio") and the existing `evidence_line` "honest decks=unknown" pattern.
4. **Ship a packaged exemplar bank** — 30 tracks (or 30s clips with usage license), 3 per band, royalty-free or CC-licensed. The fallback EVERY user has, no matter how thin their library.
5. **Audio-decode failure path** — pre-ingest probe walks the library, marks decode-failed tracks as "exemplar-ineligible," surfaces a one-line warning to the user ("3 of your tracks couldn't be analyzed for the lesson library").

**Warning signs:**
- "the AI told me the track had prominent mids but it doesn't" support inquiry → exemplar engine lying
- Same track picked as exemplar for 3 different bands → selection thresholds too loose
- Honest-null fires for >20% of users → exemplar bank too small or thresholds too tight

**Phase to address:** Phase 9.EXEMPLAR (DSP-band engine + honest-null + packaged bank). Phase 9.UAT verifies on Kaan's library AND a synthesized small-library fixture.

**Verdict:** **MUST-ADDRESS NOW in v9.0.** A lesson-library that lies is anti-product (it trains the user that the AI hallucinates — same failure class as Invariant #2).

---

### P7: AUDIO ROUTING SETUP — beginner has no BlackHole / cue channel; tutor blasts master

**What goes wrong:**
Tutor mode plays the lesson exemplar track. Beginner hasn't configured BlackHole + Multi-Output Device (Mac) or virtual audio device (Win). The audio routes to the speakers at full master gain, blasting the user (and the audience if it's a real venue). User panics. Word of mouth: "vibemix blew my speakers."

**Why it happens:**
- BlackHole setup is documented as a 3-step Audio MIDI Setup ritual — drag BlackHole into a Multi-Output Device, set as system output, choose primary clock. Non-trivial for a first-time Mac user; "you can't adjust the volume while using it" is a real footgun. ([github.com/ExistentialAudio/BlackHole wiki](https://github.com/ExistentialAudio/BlackHole/wiki/Multi-Output-Device), [DeepWiki](https://deepwiki.com/ExistentialAudio/BlackHole/3.2-multi-output-and-aggregate-devices))
- Many beginners using the FLX4/Inpulse300 will use the controller's built-in audio output (USB → controller → headphones-jack + master-jack) and NEVER touch macOS audio routing. They have no "cue channel" concept — that's a club-DJ workflow they haven't met yet.
- Lesson tutor assumes "play this to cue" → real venues route cue to headphones jack. A beginner at home with a controller doesn't have a wired headphones-cue setup.

**How to avoid:**
1. **Phase 9.AUDIO probe + wizard** — on first Learn-mode entry, probe the user's audio environment:
   - Are they using a controller with built-in audio? (use the controller's HEADPHONE output for tutor audio when one exists)
   - Do they have BlackHole + Multi-Output configured? (use cue routing)
   - Neither? (offer a small wizard: "we'll play tutor audio at -12dB through your computer speakers; turn your controller down. Want help setting up proper cueing? [Show me how]")
2. **Default-safe playback gain** — tutor exemplars play at -12dB by default (or -18dB during the lesson where the user has master playing too). User can crank if they want; never the other way.
3. **Detect master gain at lesson start** — if user has master deck audio currently playing > -6dBFS, defer tutor audio with: "your set is loud right now — I'll wait for a quiet moment to play the example." Mirrors the existing mic-gating pattern in `audio/mic_gate.py`.
4. **Honest-null for missing cue:** if no cue path exists, the lesson says: "play this example through your speakers — pause your set first if it's running, or check the controller's headphone jack." NEVER blast over a live mix.
5. **No tutor audio during ACTIVE co-host session** — Course 3 (play-mode) explicitly NEVER plays tutor exemplars while the user is mid-set. Only verbal coaching during live; exemplar playback is "between sets" only. The existing Idle≠Fault Invariant #5 helps determine session state.

**Warning signs:**
- User report: "the AI played a track on top of my set" → routing isolation broken
- User report: "everything is at one volume — when the AI plays, it's as loud as my master" → gain default missing
- The dreaded "you blew my speakers" support email — emergency

**Phase to address:** Phase 9.AUDIO (probe + wizard + gain defaults). Phase 9.CO_HOST_INTEGRATION (active-session guard for Course 3).

**Verdict:** **MUST-ADDRESS NOW in v9.0.** Hardware-safety surface as much as UX. Speakers can be damaged. Bad audio routing kills the product instantly.

---

### P8: LATENCY in MIDI→UI HIGHLIGHT — proprioceptive mismatch

**What goes wrong:**
User turns the high-EQ knob. The on-screen renderer updates 200 ms later. The visual highlight feels disconnected from the physical knob turn. User loses the "this is responsive to me" feeling → lesson feels broken even though it's technically working.

**Why it happens:**
- Path: MIDI event arrives on the daemon thread → marshalled to asyncio loop → emitted over ws bus :8765 → JS receives ws message → Canvas redraws. Each hop adds 5–50 ms.
- Tauri's Canvas rendering has known performance issues on some platforms (Linux is worst; macOS/Windows OK but not zero-cost). ([github.com/tauri-apps/tauri Issue #4891](https://github.com/tauri-apps/tauri/issues/4891), [Issue #5761](https://github.com/tauri-apps/tauri/issues/5761))
- The "rocker pill optimistic" convention in CLAUDE.md already proves: even ~3 ms IPC round-trips read as "dead" if the UI waits. Proprioceptive feedback needs ≤80 ms or it reads as lag.
- DJ controllers are physical instruments; proprioceptive coupling research from haptic music literature confirms that ≥100 ms feedback lag breaks the "gesture readability" loop. ([arxiv.org haptics paper](https://arxiv.org/pdf/1005.3182))

**Target latency budget for MIDI→UI highlight:** ≤80 ms end-to-end (P95). Achievable on Tauri+Canvas+ws if the path is tight.

**How to avoid:**
1. **Direct MIDI→Rust→Tauri-event path** — skip the Python sidecar for highlight-only MIDI events. Rust parent process reads MIDI (via `midir` crate), emits a Tauri event directly to the frontend. Frontend updates highlight on event receipt. Bypasses the asyncio + ws-bus path. The MIDI-event-to-Python path still exists for lesson-gating logic; highlight is a separate, faster channel.
2. **Optimistic highlight pattern** — mirror the "flip data-active in click handler" convention from CLAUDE.md: when a MIDI event arrives at the frontend, paint the highlight immediately; the lesson-state round-trip (via Python) confirms or corrects later.
3. **Latency test in CI** — `tauri/ui/tests/controller/highlight-latency.test.ts` measures MIDI-arrive-to-highlight-paint in a synthetic harness, gates < 50 ms (with budget to 80 ms in prod due to OS jitter).
4. **Canvas vs DOM** — small highlight overlays can be DOM with absolute positioning (cheaper than Canvas repaint on Tauri's WebKit-on-macOS). Reserve Canvas for the full controller layout that doesn't repaint frequently.
5. **Reduce the rendered controller's redraw scope** — only repaint the highlight layer on MIDI events, not the whole controller image.

**Warning signs:**
- Users describe the renderer as "laggy" or "sluggish" → over latency budget
- Highlight visibly trails the physical motion in screen recording → in-the-wild measurement
- Lesson-gate fires before the highlight appears → ordering inversion (Python lesson state ahead of UI paint)

**Phase to address:** Phase 9.RENDERER (architecture decision: dual-path MIDI). Phase 9.LATENCY (CI test gate).

**Verdict:** **MUST-ADDRESS NOW in v9.0** at architecture-decision time; revisit in v9.x if real-world measurements show drift.

---

### P9: CITATION-GROUNDING failure in Course 3 (live coaching) — count-in to a breakdown that doesn't materialize

**What goes wrong:**
Course 3 (play-mode tutor) wraps the live co-host in tutor lens. User is playing a set. AI says: "breakdown in 16 beats — when it hits, drop the high pass." User obediently blends. The "breakdown" the AI predicted DOES NOT MATERIALIZE — the AI was looking at noisy phrase-detector output, or stale CueAnchor data, or guessed from genre prototype. User blends into nothing. The transition dies on the dance floor.

**Why it happens:**
- Cardinal Invariant #3 ("trust the audio") explicitly forbids inventing events the AI hasn't measured. But the tutor-lens *encourages* anticipation ("breakdown in 16 beats") which is by definition a prediction, not a measurement.
- The 15 s lookahead engine (Phase 30 + later refinements) reads upcoming audio from the source file — works for nowplaying-cli-resolved tracks but fails on streaming-only sources (project notes "graceful skip on streaming-only" in v3.0 work).
- CueAnchor data (Phase 89 ANLZ + Phase 90 CueAnchor work) gives high-confidence phrase boundaries when the track has Rekordbox phrase analysis. Tracks without it → no high-confidence prediction.
- The tutor persona's instinct is to TEACH ("here's what's coming"), not to NARRATE ("here's what's here"). Persona drift toward prediction = Invariant #3 violation.

**Evidence:**
- The existing `state/coach.py::task_for_event` already pins narrate-not-predict for events: "PAST-TENSE only" on TRANSITION_OPPORTUNITY (line 599-617), "react to what just landed" on MIX_MOVE — never "what's coming."
- The existing `evidence_registry.py` 9 sources (ev/aud/midi/track/screen/mix/tend/key/recall) are ALL retrospective; there is no `predict` source.
- The README hero is "the only AI co-host that actually listens to your set" — predicting violates the hero.

**How to avoid:**
1. **Phase 9.TUTOR_LENS hard rule:** the tutor lens in Course 3 NEVER predicts phrase boundaries. It teaches retroactively: "that was a breakdown — see how the bass dropped out — that's where you would [filter sweep / EQ kill / etc.]." Past-tense pedagogy, not future-tense coaching.
2. **If prediction is unavoidable** (some lessons demand "count me in to the drop"), the predicted moment MUST be sourced from HIGH-CONFIDENCE CueAnchor data (Phase 89/90 produced, confidence ≥ 0.8) — and the AI must HEDGE: "if Rekordbox is right about this track, the drop is in 16 beats — count with me, but trust your ear over the count." NEVER stated as a fact.
3. **New citation source: `cue` (or `anlz`)** — extend `EVIDENCE_SOURCES` to allow `[cue:phrase@t]` citations grounded in registered CueAnchor data. Predictions WITHOUT a `[cue:...]` cite strip the turn. Mirrors how the `key` source closed the harmonic-clash hallucination class in Phase 60.
4. **Tutor-lens regression test** — fixture with audio that has NO upcoming phrase boundary; AI must NOT emit a count-in. Pinned in `tests/state/test_tutor_lens_no_prediction.py`.
5. **Run-time gate** — if `bpm_confidence < 0.8` or `phrase_position_confidence < 0.7` (using the existing thresholds at `state/refresh.py:610` and `runtime/suggestion.py:138-151`), Course 3 disables count-in language; downgrades to retrospective only.

**Warning signs:**
- AI says "in N beats" without `[cue:...]` cite → CitationLinter should already strip; if it slips, gate broken
- User report: "the AI counted me into a breakdown that didn't happen" → Invariant #3 violation; emergency triage
- Honest-null fires too often on the user's library (no high-confidence CueAnchor) → exemplar choice / library coverage issue, but the silence is the safer failure

**Phase to address:** Phase 9.TUTOR_LENS (rules + tests). Phase 9.CO_HOST_INTEGRATION (extension of `EVIDENCE_SOURCES` if `cue` lands as a real source).

**Verdict:** **MUST-ADDRESS NOW in v9.0.** v9.0 equivalent of the v2.0 anti-slop release gate. Break Invariant #3 in Course 3 and the milestone fails its core value.

---

### P10: LESSON GATING — user moves wrong knob, lesson stuck

**What goes wrong:**
Lesson 4 ("kill the lows on the incoming track"). User turns the high EQ instead. Lesson doesn't advance. User tries again, harder. Still stuck. User thinks "is it broken?" Quits.

OR opposite failure: lesson is too forgiving. User does nothing meaningful; lesson advances anyway because some random knob twitch matched the loose threshold. User completes the curriculum without learning anything. Speedruns into Lesson 10 with zero skill.

**Why it happens:**
- Threshold tuning is a usability problem disguised as a DSP problem.
- Beginners explore: they touch every knob to see what it does. The lesson-state machine must distinguish "exploring" from "completing the task."
- LLM-generated lesson scripts may say "kill the lows" but the actual MIDI event of the low EQ going to -∞ vs the audio band-energy dropping might disagree.

**How to avoid:**
1. **TWO-channel gating:** advancement requires BOTH (a) the correct MIDI event (e.g. low EQ knob CC dropped ≥30% of range) AND (b) the audio effect detected (low band energy dropped > -6 dB on the relevant deck). Either alone is not enough; both = real completion.
2. **3-strike progressive hint surface** — after 10 s with no qualifying action, AI gives a soft hint ("try the EQ knob below the gain"). After 25 s, a specific hint ("the low EQ — it's the third knob"). After 45 s, an "I can skip this if you want" option. Mirrors abandonment-prevention research from coding tutorials.
3. **"I got it" override** — user can click "I did it" to advance manually. The system records this as a "self-advance" event for telemetry but DOES NOT lie about completion.
4. **Per-lesson threshold calibration** — Phase 9.UAT walks Kaan through every lesson; thresholds tuned on the real-controller / real-audio path. NOT tuned on synthetic.
5. **Anti-speedrun: minimum lesson dwell** — Lesson 4 must take ≥45 s of *audio playing* before it can be marked complete. Prevents random-knob-twitch advancement.

**Warning signs:**
- Per-lesson telemetry shows median completion <20 s → too easy / speedrun-able
- Per-lesson telemetry shows abandonment >25% at the same lesson → too hard / wrong threshold
- Hint-displayed rate >50% at the same step → hint should be promoted to the lesson script itself

**Phase to address:** Phase 9.LESSON_FLOW (two-channel gating + hint progression). Phase 9.UAT calibrates thresholds.

**Verdict:** **MUST-ADDRESS NOW in v9.0** — broken gating is broken pedagogy.

---

## Moderate Pitfalls

### P11: ACCESSIBILITY — color-blind users on amber, motor/hearing-impaired, keyboard-only

**What goes wrong:**
- The CDJ-Whisper aesthetic is amber-on-charcoal. Protanopia (1 % of males, ~6 % of all colorblind cases) and deuteranopia (most common, ~5 % of males) struggle with amber — it shifts toward muddy yellow-brown, low contrast against charcoal. Highlight invisibility for color-blind users. ([infyways.com colorblind sim](https://www.infyways.com/tools/color-blindness-simulator/), [audioeye.com colorblind palettes](https://www.audioeye.com/post/colorblind-friendly-palettes/))
- WCAG: amber-on-dark hits AA contrast only for large text; smaller UI text + button labels need verification. ([equalizedigital.com](https://equalizedigital.com/website-accessibility-color-blind/))
- Time-pressure on advancement excludes motor-impaired users.
- Hearing-impaired user with no visual cue for kick/phrase boundaries can't follow Course 1 anatomy lessons.
- Keyboard-only browsing of the curriculum is missing.

**How to avoid:**
- DUAL channel for the highlight — color AND shape change (e.g. amber pulse + thick outline). Color-blind users see the outline; color-sighted users see both.
- WCAG AA contrast verified for all UI text via `tauri/ui/tests/a11y/contrast.spec.ts` (extends existing P74/P75 a11y work).
- No mandatory time-pressure — user can pause any lesson indefinitely.
- Visual phrase markers (beat ticker on the timeline) for hearing-impaired Course 1 lessons.
- Keyboard-nav for the curriculum browse + lesson start — Tab/Enter/Esc.

**Warning signs:** color-blind tester reports "the highlight is invisible" → fix immediately

**Phase to address:** Phase 9.A11Y (lightweight phase, mostly verification + dual-channel highlight).

**Verdict:** **MUST-ADDRESS NOW in v9.0** for the dual-channel highlight (1-line CSS change); MONITOR full WCAG sweep in v9.x.

---

### P12: PROGRESS PERSISTENCE — corruption, deletion, reset, migration

**What goes wrong:**
- User progress in `~/.cache/vibemix/learn-progress.json` corrupts mid-write (power loss, app crash) → next launch can't deserialize → user appears to have lost all progress.
- User wants to "reset" — no UI affordance for it; they have to `rm` from terminal.
- v9.0 schema → v9.1 schema migration breaks for users on v9.0 progress files.
- User deletes `~/.cache/vibemix/` to free disk → loses progress with no warning.

**How to avoid:**
- ATOMIC write pattern: write to `.tmp`, fsync, rename. Mirrors `library/model_assets.py:131-202` pattern already used for CLAP model downloads.
- Schema version field at the top; on read, if schema mismatch, run a registered migration or reset gracefully with user notification.
- Reset UI in Settings → "Reset learning progress" (with confirmation).
- If `~/.cache/vibemix/learn-progress.json` is missing on second launch but app has launched before, surface "looks like your progress was reset — start over?" instead of silently re-running first-run wizard.

**Warning signs:** "I lost all my progress" support inquiries

**Phase to address:** Phase 9.PERSISTENCE (small phase — schema + atomic writes + reset UI).

**Verdict:** **MUST-ADDRESS NOW in v9.0** at schema-design time; SHIP-BLOCKING fix if a user actually loses progress in beta.

---

### P13: INTEGRATION REGRESSION — ws bus :8765, mascot frame handler, rc1 spawn paths

**What goes wrong:**
Adding `learn.*` IPC envelopes to the ws bus collides with the mascot frame handler (`mascot.html:218` reads the existing `{music, voice, mic, audible, deck, phase, bpm, mood, ...}` frame shape). New envelopes cause schema validation errors → mascot disconnects → "AI service unreachable" empty-screen flips back on. Or: the new IPC family changes process-spawn behavior, regressing the rc1 livekit-agents bundle fix.

**Why it happens:**
- Cardinal Invariant #4 ("One socket") is structurally enforced (only port 8765), but envelope namespace collisions are NOT — anyone can register a `learn.*` envelope without checking the mascot consumer.
- The rc1 work landed `scripts/dist/patch_livekit_agents_init.py` + `sidecar.rs` std::process changes (per handoff `.planning/handoffs/2026-05-27-rc1-integration-followup.md`); a new IPC family that requires additional sidecar imports could re-introduce the frozen-importer bug.
- Ajv validator is PRE-COMPILED (`tauri/ui/src/ipc/validator.generated.mjs`); stale validator rejects new envelopes — convention in CLAUDE.md says you MUST run `npm run codegen:ipc` after schema edits.

**How to avoid:**
1. **Envelope namespace audit** — `learn.*` family added to `src/ipc/messages.schema.json`; codegen runs in CI; mascot frame handler test pins that mascot envelopes are still recognized post-`learn.*` addition.
2. **Mascot regression test** — `tauri/ui/tests/mascot/learn-envelope-doesnt-break-mascot.spec.ts` simulates a `learn.lesson_advance` envelope and verifies mascot still receives + parses its `{music, voice, ...}` frame.
3. **Spec blocklist check** — `tests/dist/test_spec_blocklist_keeps_livekit_cli.py` (NEW-1 fix from rc1 followup) parametrized + extended for any new `learn.*` modules that might add imports. If Course 3 imports new submodules into `agent/`, audit the spec.
4. **Standalone sidecar smoke** — after v9.0 phases, run `vibemix-core --session` + `vibemix-core --wizard` standalone to verify bundle doesn't regress on launchd-spawn.
5. **No new ws port** — `learn.*` rides existing :8765 (per Invariant #4); debrief stays on :8766; do not invent a 3rd port.

**Warning signs:** mascot disconnects when Learn mode is open → envelope collision; bundle crashes on first launch after a Learn-mode PR → spec/import regression

**Phase to address:** Phase 9.IPC (schema + codegen + mascot regression test). Phase 9.BUNDLE-CHECK (rerun rc1 sidecar smoke).

**Verdict:** **MUST-ADDRESS NOW in v9.0.** Regression-pinning is cheaper than re-debugging the rc1 bug.

---

### P14: TONE DRIFT under FUNDED-KEY usage — CodexAgent vs Gemini Flash

**What goes wrong:**
Tutor mode is built. Kaan ear-passes lessons using Gemini Flash on the funded key. Sounds great. A user without a key falls through to local CodexAgent (project's Viber set-prep backend) for chat-equivalent paths. CodexAgent's vocabulary, sentence length, and rhetorical defaults are NOT Gemini's. The Codex-path tutor sounds different from the Gemini-path tutor. The "real DJ friend" identity fractures by API path.

**Why it happens:**
- Project explicitly uses TWO LLMs by feature surface: Gemini Flash for live co-host (per CLAUDE.md "Live co-host is locked on LiveKit pipeline + Gemini Flash + Gemini TTS"); local Codex for Library/Viber set-prep. They have different training, different vocab, different defaults.
- For v9.0, the LEARN module mostly uses scripted lesson text (P1 mitigation) + AI for narrow grounded interjections. If those interjections use one model in production and another in offline mode, the interjections sound different.
- Ear-testing is done on ONE path; the other path is unverified.

**How to avoid:**
1. **Decide UP FRONT which model owns Course 3 grounded interjections.** PROJECT.md is explicit: live co-host = Gemini. Course 3 is the live co-host with tutor lens → Gemini. Courses 1+2 (anatomy + transitions) are NOT live co-host paths — they're scripted curriculum with narrow AI prompts. Those can run on EITHER path, BUT:
2. **Lock to ONE backend per surface for v9.0.** Recommendation: ALL of Course 1-2-3 use the live-co-host Gemini-Flash path (since the user already has GEMINI_API_KEY for v0.1.0-rc1 ship). NO Codex fallback for tutor reactions in v9.0. Defer "offline tutor mode" to v9.x.
3. **Ear-pass on the SHIPPING path** — Kaan ear-passes Gemini-Flash tutor reactions; if v9.x adds Codex tutor, separately ear-pass that path.
4. **CI snapshot tests on prompt structure** — assert the tutor prompt structure does NOT depend on the LLM backend (deterministic format); only the response varies. Drift in response style is acceptable if prompt structure is stable.

**Warning signs:** ear-pass on the funded key passes, ear-pass on local Codex fails → model-dependent tone

**Phase to address:** Phase 9.TONE (decide LLM-per-surface). Phase 9.UAT (ear-pass on the shipping path).

**Verdict:** **MUST-ADDRESS NOW in v9.0** as a decision (which model owns tutor); MONITOR drift in v9.x once an offline path is built.

---

### P15: MOBILE / OS — features that beg for web-only consumption

**What goes wrong:**
"Browse the curriculum" / "preview Lesson 3" / "watch the demo video" all read as "I'm reading about DJing on the bus." That's a WEB consumption mode, not a desktop-app mode. We build the curriculum browser in Tauri, ship it as part of v9.0, but users never open the app to browse — they want a website.

**Why it happens:**
Curriculum DISCOVERY is async (you decide whether to learn before you start). Curriculum EXECUTION is desktop-tied (you need the hardware + audio path). Conflating them puts effort in the wrong surface.

**How to avoid:**
1. **Web landing page hosts the curriculum CATALOG.** GitHub Pages site (the existing v7.0 Phase 70 OSS-LANDING work) gets a Learn tab listing the 10 lessons with descriptions, screenshots, total time, prereqs. CTA: "install vibemix to start Lesson 1."
2. **In-app surface focuses on EXECUTION.** Lesson list inside the app is functional (start / continue / reset), not marketing.
3. **NO mobile build.** Linux explicitly excluded per CLAUDE.md. Mobile too — defer to "watch the YouTube demos" instead.

**Warning signs:** "is there a web version where I can preview lessons?" support inquiries → catalog absent or insufficient

**Phase to address:** Phase 9.LANDING (web catalog — extends existing OSS landing). Phase 9.UI (in-app execution surface).

**Verdict:** **MONITOR in v9.x.** Ship in-app surface first; add web catalog if outreach shows demand. NOT a v9.0 blocker.

---

### P16: KAAN'S OVERNIGHT AUTONOMOUS RUN — blast radius

**What goes wrong:**
Kaan says "plug my DJ set in, let you run autonomous overnight, full access to my computer." The autonomous agent (Claude Code in `gsd-autonomous fully` mode) has full filesystem + git + network access by default. Overnight it could:
- Push to main / rewrite history / force-push wrong branch
- `rm -rf` something destructive
- Read off-limits LLM transcript paths (CLAUDE.md hard rule)
- Run up cloud bills (Gemini API, GitHub Actions)
- Land regressions while ear-pass isn't watching
- Get stuck in a feedback loop ("test fails → modify test → test passes → ship")

**Why it happens:**
- The `gsd-autonomous fully` mode IS the design intent for overnight runs.
- The privacy hard rule in CLAUDE.md is the explicit guard rail Kaan already authored (off-limits LLM transcript paths).
- Modern coding agents do have sandboxing tools (Safehouse, Claude Code's macOS Seatbelt-based sandbox) but they require opt-in configuration. ([anthropic.com claude-code-sandboxing](https://www.anthropic.com/engineering/claude-code-sandboxing), [tessl.io Safehouse](https://tessl.io/blog/safehouse-sandboxes-ai-coding-agents-on-macos/))

**How to avoid:**
1. **Privacy hard rule is ABSOLUTE** — already in CLAUDE.md, enforced by the user-memory `feedback_privacy_scope_narrow`. Do not extend.
2. **Git destructive ops require explicit Kaan-OK** — already in the GSD prompt: "NEVER run destructive git commands (push --force, reset --hard, checkout ., restore ., clean -f, branch -D) unless the user explicitly requests these actions." Reinforce per session.
3. **No force-push to main** — already in the prompt.
4. **Network budget guard** — Gemini API has a per-key spend cap; v9.0 autonomous runs MUST respect the existing 50 €/month budget (per CLAUDE.md project constraint). If a phase needs >5 € in API calls, defer it to Kaan-awake hours.
5. **Don't refresh shared-tree baselines** — already in the user memory `feedback_concurrent_sessions_one_tree` ("Concurrent Claude sessions on ONE working tree — discipline") — never `git add -A`; named-path staging only.
6. **No autonomous publish** — `cut_release.sh` has a hard-guard that never auto-runs `gh release create` (per v3.0 SHIP-08 work); this guard is the safety net.
7. **Loop detection** — if a phase fails 3+ times in a row, the agent stops and waits for Kaan instead of grinding overnight.

**Phase to address:** Pre-Phase 9.0 (operational hygiene — these are session-discipline rules, not code rules). Reinforce in the v9.0 ROADMAP's overnight-run handoff doc.

**Verdict:** **MUST-ADDRESS NOW in v9.0** at operational level (one-page "overnight discipline" handoff doc); no NEW code guardrails needed — existing project conventions are sufficient if they're followed.

---

### P17: SCOPE CREEP — "build a whole DJ school"

**What goes wrong:**
Kaan said "fully comprehensive." v9.0 turns from "Beginner module — 10 lessons + 3 controllers + library exemplar engine" into "full DJ school with Intermediate course + Pro course + scratching + stems + remixing + community-shared lessons + leaderboards." Six months pass. Nothing ships.

**Why it happens:**
- "Comprehensive" is the slippery word. The bestie tagline opens a category-shaped hole the team wants to fill all at once.
- Adjacent features (Intermediate course, scratching, leaderboards) all *fit* — but each adds risk surface (P1 tone, P5 copyright, P9 grounding) that compounds.
- Bravoh is the commercial home for cross-user / community / leaderboard features per CLAUDE.md ("Vibe Mix discovery wedge" memory) — vibemix is the narrow OSS utility.

**Anti-creep acid test for v9.0 phases (mirroring v7.0 / v8.0 patterns):**

*"Does this phase deliver a working slice of the BEGINNER (level 1, 3 controllers, exemplar library + packaged fallback, scripted curriculum with grounded AI interjections) module — WITHOUT adding a new AI provider, new ws port, new IPC envelope family beyond `learn.*`, new DSP library, new content beyond the 10 hand-authored lessons, or new community/multi-user feature surface? Does it NOT regress any of the 5 cardinal invariants or the rc1 bundle fix?"*

If a phase doesn't pass: defer to v9.x or to Bravoh.

**EXPLICIT DEFER LIST (v9.x / Bravoh, NOT v9.0):**
- Intermediate / Pro courses → v9.x
- Scratching lessons → v9.x or never (genre-specific, not the wedge)
- Effects beyond filter → v9.x
- Hot cues beyond cue 1 → v9.x
- Sampler / loops / beat-jump → v9.x
- Stem isolation → never on the device (Bravoh server-side only if at all)
- Remixing / remix-along → never (out of vibemix scope entirely)
- Community-shared lessons → Bravoh
- Leaderboards / streaks → Bravoh
- Long-form video lessons → not in app (YouTube / external if at all)
- Cross-device progress sync → Bravoh
- 7+ controllers with full photorealistic vector art → v9.x (3 in v9.0, generic for the rest)
- Mobile app → never (CLAUDE.md platform constraint)
- Localization beyond English → v9.x

**How to avoid:**
1. **The acid test above is in the v9.0 ROADMAP at the top** — every phase plan asserts it passes the test.
2. **EXPLICIT defer list above is in the v9.0 ROADMAP** — saying "we are NOT building X" is the strongest anti-creep tool.
3. **3-controller scope cap** — FLX4, Inpulse 300, Party Mix Live. NO other controller gets full SVG in v9.0.
4. **10-lesson scope cap** — the 10 in P2 above. NO lesson #11 in v9.0 without dropping one of the 10.

**Warning signs:** phase plan starts with "while we're in here, let's also…" → defer

**Phase to address:** v9.0 ROADMAP (acid test + defer list at the top, like v7.0 and v8.0 did).

**Verdict:** **MUST-ADDRESS NOW in v9.0** at roadmap-design time. The acid test is the milestone's most important governance artifact.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|---|---|---|---|
| LLM-generates lesson scripts on the fly | No content-authoring time | P1 tone failure; impossible to ear-pass; non-deterministic curriculum | **NEVER** in v9.0 — hand-authored scripts only |
| Skip MIDI self-test, trust profile auto-detection | Faster setup wizard | P3 firmware variation → wrong-event lessons | NEVER for the 3 shipped controllers; ACCEPTABLE for the 7 fallback controllers |
| Use the same `pad` highlight color as the kick-detected pulse | Visual reuse | Color-blind users can't tell lesson highlight from kick → P11 a11y | Never — separate visual language |
| Reuse the LIVE coach prompt for tutor lens unchanged | One less prompt to maintain | Tone slop (P1) + prediction risk (P9) | Never — tutor lens needs its own prompt family |
| Compute "prominent mids" exemplar via CLAP cosine | Reuse the embedding store | Wrong tool for the job (P6 — CLAP is semantic, not spectral) | Never — DSP-band engine instead |
| Ship the Inpulse 300 + Inpulse 300 MK2 as one profile | One less file | MK2 user gets wrong MIDI map → unrecoverable wrong highlights (P3) | Never — two profiles, MIDI-signature dispatch |
| Cache user progress in localStorage instead of file | Simpler write path | Loss on Tauri webview clear; no migration path; harder to inspect for support | Acceptable for transient UI state; NOT for lesson progress |
| Skip the cue-routing probe, always play to master | One less first-run step | P7 audio routing catastrophe (speakers blown) | Never — probe + safe-default required |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|---|---|---|
| ws bus :8765 (mascot + wizard + new learn.*) | Adding `learn.*` envelopes without testing mascot frame handler | Envelope namespace audit + mascot regression test (P13) |
| Pyrekordbox XML import | Assuming user has Rekordbox exported recently | Honest-null fallback if collection.xml missing or stale; ship packaged exemplar bank (P6) |
| CLAP ONNX local model | Assuming first-run download already happened | The library Models row + install button at `tauri/ui/library.html:170-176` is the load-bearing path — DO NOT bypass it from Learn mode (per rc1 followup §6 "CLAP first-run UX") |
| Tauri sidecar spawn (cargo tauri dev vs bundled) | Verifying against bundled binary | Per CLAUDE.md: "bundled Python sidecar in `cargo tauri dev` is FROZEN" — verify against live source via standalone smoke (rc1 pattern) |
| MIDI hot-plug | Trusting device-port pair as identity | Trust MIDI signature handshake (press-play-to-confirm) for re-connection (P3) |
| BlackHole on macOS | Assuming user has Multi-Output Device configured | Probe + offer setup wizard or fall back to safe-default master playback (P7) |
| WASAPI loopback on Windows | Assuming the user's default device is the right capture target | Pick device explicitly in the audio wizard; verify with a 1-sec tone playback |
| Gemini API key in distributed binary | Embedding raw key | Bravoh-side proxy with per-client rate limit (per CLAUDE.md security constraint) |
| Apache 2.0 license + Pioneer trademark | Assuming Apache covers trademark use | Apache is SOURCE license; trademark is separate; nominative fair use + disclaimer (P5) |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|---|---|---|---|
| MIDI→UI highlight via Python sidecar | "Laggy" highlight, 100ms+ delay | Direct Rust→Tauri-event path for highlight only (P8) | Always perceptible (≥80 ms feels laggy on any user; some users notice ≥40 ms) |
| Canvas full repaint on every MIDI event | CPU spike during fast knob turns | Highlight overlay as DOM with absolute positioning OR Canvas with dirty-rect repaint (P8) | Fast knob turns (multiple events per 100 ms) |
| Per-track DSP analysis at lesson start | 5+ second wait before lesson begins | Pre-analyze the library at ingest time (extends Phase 89 ingest); cache band-energy stats (P6) | Libraries >200 tracks |
| Re-ingesting historic 768-dim sessions on session start | ~20 dimension-mismatch warnings per launch (already observed, NEW-2 in rc1 handoff) | Suppress with explicit migration script or session-scoped error filter | Already broken at any library size; cosmetic but noisy |
| LLM call per lesson step | $$$ + latency budget blown | One LLM call per "live interjection event" (not per lesson STATE TICK); reuse v3.0 `LIVE_TTFT_BUDGET_MS=1500` discipline | Per-tick LLM calls break the 50 €/month budget within 10 hours of usage |
| Synchronous file write on every progress event | Disk wear + lesson-flow stutter | Debounce writes (1 s); atomic-write pattern per P12 | Heavy lesson sessions (Lesson 10 has many state changes) |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---|---|---|
| Allow autonomous-agent overnight to bypass privacy hard rule | Reading off-limits LLM transcripts | Privacy rule in CLAUDE.md is absolute (P16) |
| Embed Gemini API key in v9.0 release | Cost-of-the-year API-key problem | Bravoh proxy + per-client rate limit (per CLAUDE.md security constraint) |
| Send user lesson progress + library metadata to Bravoh by default | Privacy violation; cross-product data leak | Default OFF; opt-in only; same posture as v3.0 LAUNCH-05 Bravoh waitlist toggle |
| Phone-home telemetry per lesson event | Privacy + GDPR risk | Default OFF (per CLAUDE.md / v3.0 LAUNCH-05); local-only progress file |
| Tauri capability missing for the renderer's filesystem access (track playback) | Crash on first run; the v0.1.0-rc1 carryover bug class | Audit capabilities for new file-read paths; mirror the v0.1.0-rc1 fix discipline |
| Render Pioneer logo on the SVG controller | Trademark dispute → cease and desist | Stylized art + no logo + disclaimer (P5) |
| Spawn external playback process without arg sanitization | RCE if filename contains shell meta | Use `subprocess.run([...])` list form (project convention); never `shell=True` |
| Cache lesson exemplars indefinitely on disk without cleanup | Disk-fill on large libraries | Bounded cache (e.g. 1 GB) with LRU eviction; document in `~/.cache/vibemix/learn/` |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---|---|---|
| Modal lesson "you can't leave until you finish" | Trapped feeling, abandonment | Always-available "pause" + "exit"; resume from where you left off |
| AI talks during user practice (Course 3) | Stepping on the audience moment | Mute-during-active-mix gate (mirrors existing mic-gating discipline) |
| Lesson highlight on a button the user can't see | Confusion, search behavior | Spatial reference text ("the knob under your gain") in lesson script |
| No "what does this knob do?" hover | User clicks every knob to find out | Hover tooltip on every rendered control on first lesson |
| Unable to skip ahead even for self-taught DJs | Power users alienated | "I already know this" → tests fast-skip with 30-second comprehension check |
| Lesson 1 demands hardware before showing what hardware looks like | "I haven't bought a controller yet" → quit | Pre-Lesson 1 "browse what controllers we support" with the GitHub Pages catalog link |
| No-controller fallback mode | "I want to try before buying" → can't | Keyboard-only practice mode for Course 1 anatomy (defer practice with audio to v9.x) |
| Re-starting a lesson erases progress within | "I just wanted to redo step 3" → lost all | Step-level resume within a lesson |

---

## "Looks Done But Isn't" Checklist

- [ ] **Tutor tone:** Anti-slop blocklist v2 exists — verify it's CI-enforced AND ear-passed on ALL 30+ lesson reactions (P1).
- [ ] **Pedagogical order:** 10 lessons documented — verify a beginner DJ instructor sign-off (P2).
- [ ] **Hardware variation:** MIDI self-test runs on first-connect — verify FLX4 v1.04 vs v1.07 both progress through Lesson 1; Inpulse 300 vs MK2 both detect correctly (P3).
- [ ] **Renderer accuracy:** SVG matches photo overlay — verify per-controller snapshot test in CI (P4).
- [ ] **Copyright:** Disclaimer copy present — verify no Pioneer logo + no Pioneer orange in the SVG (P5).
- [ ] **Exemplar engine:** Honest-null fires when library too small — verify with synthetic 3-track fixture (P6).
- [ ] **Audio routing:** Tutor playback gain ≤-12 dB — verify per-platform smoke (P7).
- [ ] **Latency:** MIDI→highlight ≤80 ms P95 — verify with CI latency test (P8).
- [ ] **Grounding:** Course 3 tutor lens never emits unsourced predictions — verify with no-cue-data fixture test (P9).
- [ ] **Gating:** Two-channel (MIDI + audio) advancement — verify with synthetic fixtures (P10).
- [ ] **A11y:** Highlight has shape + color — verify with colorblind simulator (P11).
- [ ] **Persistence:** Atomic write + schema version — verify with mid-write kill test (P12).
- [ ] **Integration:** Mascot still receives frames when Learn mode is open — verify with combined-session test (P13).
- [ ] **Tone parity:** Gemini-Flash path ear-passed — Codex tutor path deferred to v9.x (P14).
- [ ] **Scope:** Acid test in ROADMAP — every phase plan asserts pass (P17).
- [ ] **rc1 regression:** Standalone sidecar smoke runs post-Learn-mode changes — verify wizard, session, no-args modes all boot.

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---|---|---|
| Tutor tone slop slipped through (P1) | MEDIUM | Hot-fix the lesson script (no code release); add the slop phrase to the blocklist; re-ear-pass affected lessons |
| Pedagogical order wrong (P2) | HIGH | Re-author the lesson sequence; release v9.0.1 with curriculum re-order; existing-user progress migration |
| Hardware MIDI variation broken (P3) | LOW | Ship updated profile JSON via app update or remote config; no code change needed |
| Renderer SVG wrong (P4) | LOW | Edit SVG, ship in next patch release |
| Pioneer cease-and-desist (P5) | HIGH | Pull the rendered controller from release; ship "controllers shown as labeled zones only" hotfix; engage counsel |
| Exemplar engine lies (P6) | MEDIUM | Tighten the honest-null threshold; fall back to packaged exemplars more aggressively |
| Speakers blown by audio routing (P7) | CATASTROPHIC | Pull tutor-audio playback feature; hot-fix to use ONLY headphone/cue routing; sincere apology + audit |
| Latency drift (P8) | MEDIUM | Architecture decision needs revisiting; may need Rust-direct highlight |
| Tutor predicted a breakdown that didn't happen (P9) | HIGH | Disable count-in language across Course 3 in hotfix; review prompt; re-ear-pass |
| Lesson stuck on wrong-knob (P10) | LOW | Tweak threshold in next patch; hot-fix hint progression |
| Color-blind user can't see highlight (P11) | LOW | CSS fix for dual-channel; release in patch |
| Progress file lost (P12) | LOW | Reset UI available; remind user; in next release add atomic-write if not present |
| Mascot regressed (P13) | LOW | Revert offending PR; mascot regression test added |
| Codex tone fails (P14) | LOW | Disable Codex tutor path until reviewed (already deferred to v9.x by P14) |
| Scope creep (P17) | HIGH | Stop work; revisit acid test; defer features to v9.x |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---|---|---|
| P1: AI tutor tone | Phase 9.TONE (LLM-slop blocklist v2 + hand-authored scripts + system instruction lock) | CI blocklist + Kaan ear-pass on all 30+ lessons in Phase 9.UAT |
| P2: Pedagogical order | Phase 9.PEDAGOGY (10-lesson curriculum + prereq metadata + DJ-instructor review) | Linear-progression test + abandonment telemetry in Phase 9.UAT |
| P3: Hardware variation | Phase 9.HARDWARE (MIDI self-test + profile-variant schema + generic fallback) | Per-controller smoke (FLX4, Inpulse 300, Party Mix Live) in Phase 9.UAT |
| P4: Renderer accuracy | Phase 9.RENDERER (SVG + photo-overlay CI snapshot + highlight-by-CC test) | Snapshot test + Kaan-eye verification on real hardware |
| P5: Copyright | Phase 9.RENDERER (locked visual policy + disclaimer) + Phase 9.LEGAL (lawyer/Francesco sight-check) | KAAN-ACTION-LEGAL §LEARN-LEGAL discharge gate |
| P6: Exemplar engine | Phase 9.EXEMPLAR (DSP-band engine + honest-null + packaged bank) | Synthetic 3-track fixture test + Kaan-library test |
| P7: Audio routing | Phase 9.AUDIO (probe + wizard + gain defaults) + Phase 9.CO_HOST_INTEGRATION (active-session guard for Course 3) | Per-platform smoke (macOS BlackHole, Windows WASAPI, controller-with-builtin-audio) |
| P8: Latency | Phase 9.RENDERER (dual-path MIDI architecture) | CI latency test + screen-recording verification |
| P9: Citation grounding | Phase 9.TUTOR_LENS (rules + tests) + Phase 9.CO_HOST_INTEGRATION (cue source extension if needed) | No-prediction-without-cue fixture test + Kaan ear-pass on Course 3 |
| P10: Lesson gating | Phase 9.LESSON_FLOW (two-channel gating + hint progression) | Per-lesson threshold calibration in Phase 9.UAT |
| P11: Accessibility | Phase 9.A11Y (dual-channel highlight + WCAG sweep) | Colorblind simulator + contrast tests |
| P12: Progress persistence | Phase 9.PERSISTENCE (schema + atomic writes + reset UI) | Mid-write kill test + corruption-recovery test |
| P13: Integration regression | Phase 9.IPC (schema + codegen + mascot regression) + Phase 9.BUNDLE-CHECK (rc1 sidecar smoke) | Mascot test + standalone sidecar smoke on all 3 modes |
| P14: Tone drift (Gemini vs Codex) | Phase 9.TONE (lock LLM-per-surface) | Ear-pass on Gemini-Flash path only in v9.0 |
| P15: Mobile / Web | Phase 9.LANDING (web catalog) + Phase 9.UI (in-app execution) | Web-catalog visit-to-install funnel telemetry (deferred) |
| P16: Autonomous overnight | Pre-Phase 9.0 (operational handoff doc) | Privacy rule + git destructive guards + budget cap; no new code |
| P17: Scope creep | v9.0 ROADMAP top (acid test + explicit defer list) | Every phase plan asserts acid-test pass |

---

## Sources

### Primary (this project)
- `CLAUDE.md` (privacy hard rule + tech stack + conventions + AI-slop discipline)
- `.planning/PROJECT.md` (constraints + core value + milestone history)
- `.planning/handoffs/2026-05-27-rc1-integration-followup.md` (rc1 spec/bundle fixes — do not regress)
- `src/vibemix/state/coach.py` (existing citation grammar + persona discipline + past-tense pedagogy precedent)
- `src/vibemix/state/evidence_registry.py` (9-source citation taxonomy; extension point for `cue` source)
- `scripts/launch/check_no_ai_slop.py` (existing AI-slop blocklist pattern to mirror for tutor mode)
- User memories `feedback_no_clap_use_gemini_embedding` (CLAP is the engine), `feedback_verify_live_app_not_just_tests`, `feedback_concurrent_sessions_one_tree`

### External (web research, dated 2026-05-27)
- [Khanmigo critique: scripted/repetitive — myengineeringbuddy.com](https://www.myengineeringbuddy.com/blog/khanmigo-reviews-alternatives-pricing-offerings/)
- [Dan Meyer on Khanmigo answer-giving — danmeyer.substack.com](https://danmeyer.substack.com/p/the-chatbot-tutors-are-sick-of-your)
- [Duolingo Max scripted-dialog review — copycatcafe.com](https://copycatcafe.com/blog/duolingo-max)
- [Game-tutorial pedagogy — popmatters.com](https://www.popmatters.com/111485-active-learning-the-pedagogy-of-the-game-tutorial-2496084217.html)
- [Tutorials strangle creativity — psychologyofgames.com](https://www.psychologyofgames.com/2012/09/how-game-tutorials-can-strangle-player-creativity/)
- [Coding-tutorial abandonment patterns — arxiv.org](https://arxiv.org/pdf/1707.04291)
- [Pioneer trademarks list — usa.pioneer/pages/trademarks](https://usa.pioneer/pages/trademarks)
- [Mixxx Pioneer compatibility (nominative fair use precedent) — mixxx.org wiki](https://github.com/mixxxdj/mixxx/wiki/Pioneer-Ddj-Controllers)
- [Serato hardware compatibility — serato.com/dj/hardware](https://serato.com/dj/hardware)
- [Trademark nominative fair use — trademarklawyerfirm.com](https://www.trademarklawyerfirm.com/what-is-trademark-fair-use/)
- [Lanham Act fair use — 500law.com](https://500law.com/fair-use-trademark-service-mark/)
- [DDJ-FLX4 firmware 1.07 release notes — pioneerdj.com](https://www.pioneerdj.com/en/news/2025/ddj-flx4-firmware-update-107/)
- [DDJ-FLX4 vs FLX6 — hollywooddj.com](https://hollywooddj.com/blogs/buying-guides/pioneer-flx4-vs-flx6-differences-compared)
- [Hercules Inpulse 300 MK2 mapping — djuced.com](https://www.djuced.com/kb/hercules-djcontrol-inpulse-300-mk2-2023-mapping-and-manual/)
- [USB MIDI iSerialNumber importance — devblogs.microsoft.com](https://devblogs.microsoft.com/windows-music-dev/the-importance-of-including-a-unique-iserialnumber-in-your-usb-midi-devices/)
- [BlackHole Multi-Output Device setup — github.com/ExistentialAudio/BlackHole wiki](https://github.com/ExistentialAudio/BlackHole/wiki/Multi-Output-Device)
- [Tauri Canvas performance — github.com/tauri-apps/tauri Issue #4891](https://github.com/tauri-apps/tauri/issues/4891)
- [Tauri Canvas performance — github.com/tauri-apps/tauri Issue #5761](https://github.com/tauri-apps/tauri/issues/5761)
- [Haptics in music — proprioceptive coupling — arxiv.org](https://arxiv.org/pdf/1005.3182)
- [Beatmatching pedagogy — pointblankmusicschool.com](https://www.pointblankmusicschool.com/blog/a-beginners-guide-to-beat-matching-for-djs/)
- [Beginner DJ guide — wearecrossfader.co.uk](https://wearecrossfader.co.uk/blog/learn-to-dj-the-complete-beginners-guide/)
- [Bach to Rock — mixing before scratching gate — bachtorock.com](https://www.bachtorock.com/dj-scratching-lessons/)
- [WCAG color blindness — equalizedigital.com](https://equalizedigital.com/website-accessibility-color-blind/)
- [Colorblind palettes — audioeye.com](https://www.audioeye.com/post/colorblind-friendly-palettes/)
- [Colorblind simulator — infyways.com](https://www.infyways.com/tools/color-blindness-simulator/)
- [Claude Code sandboxing — anthropic.com](https://www.anthropic.com/engineering/claude-code-sandboxing)
- [Safehouse macOS sandbox — tessl.io](https://tessl.io/blog/safehouse-sandboxes-ai-coding-agents-on-macos/)
- [CLAP audio embeddings — huggingface.co](https://huggingface.co/docs/transformers/model_doc/clap)
- [CLAP paper — arxiv.org](https://arxiv.org/pdf/2206.04769)
- [BlackHole DeepWiki — deepwiki.com](https://deepwiki.com/ExistentialAudio/BlackHole/3.2-multi-output-and-aggregate-devices)

---
*Pitfalls research for: v9.0 "Lesson One" Beginner Learning Module*
*Researched: 2026-05-27*
