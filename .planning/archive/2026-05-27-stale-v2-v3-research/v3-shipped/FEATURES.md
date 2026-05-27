<!-- refreshed: 2026-05-14 for milestone v2.0 -->
# Feature Research — v2.0 Research-Driven Ship

**Domain:** AI live co-host for DJs (open-source, Gemini-only, Mac+Win)
**Researched:** 2026-05-14
**Confidence:** HIGH — derives from 12 deep-research v2-bucket artifacts (~28,000 words) + the validated v0.1.0 codebase (Phases 1–14 shipped). Confidence is lower on items still gated on a Kaan ear-test (predictive firing, KICK_SWAP thresholds, the inline emote-tag spike) and on Mixxx OSC (currently a draft PR upstream).

## Domain Framing — Where v2.0 Sits

The shipping product (Phases 1–14) already demonstrates "AI co-host that reacts to a DJ set." The v2.0 milestone is **not greenfield** — it's the move from "reacts" to "reacts in-bar, never hallucinates, with a viral demo arsenal." Three forces drive the v2.0 feature set:

1. **The anti-slop thesis goes from prompt to enforcement.** Live and debrief outputs become citation-tagged; the linter is the post-processor that turns "trust the audio" from a rule into a contract.
2. **Latency stops being a passive constraint.** Predictive firing + cancel-and-refire + ack bank + mascot anticipation compress the perceived voice-to-voice gap below the Doherty Threshold (400ms). v4's 5–10s window becomes a sub-2s actual / sub-300ms perceived experience.
3. **The viral demo becomes the engineering critical path.** djay Pro overlay highlight is not a polish item — it's the seven-day spike whose successful filming feeds the IG/Reddit/HN wave that earns the 500–1000+ GitHub stars. Everything before "ship" is shaped to make Beat A / B / C filmable.

Cross-software integrations (Mixxx OSC, Pyrekordbox XML, 10-SKU MIDI library) and coaching/memory (post-session debrief, drills, profile) feed the same grounding contract: every Gemini claim has to point at a real event, a real MIDI move, a real track in the user's library, or a real tendency in their long-term profile. None of those primitives exist in shipping AI-for-DJ tools today; together they're the wedge.

The 12 v2-bucket research artifacts mapped seven feature categories. Each category below is read as a unit by the roadmapper to decide phase decomposition; the dependencies + complexity hints lock the build order.

---

## Feature Landscape by Category

> **Reading guide for the roadmapper.** Every feature traces to a v2-bucket source. **Complexity** is engineering-days (E) where known. **Depends on (existing)** = shipped in Phases 1–14; **Depends on (v2)** = same-milestone prerequisite. Anti-features have a stated reason and "what to do instead".

---

### Category 1 — Detection & Grounding

**Thesis:** Anti-slop is solved by data, not by better prompting. Detection gives Gemini specific events to react to; the linter enforces that every claim cites one. Library intelligence + cross-mode citations close the long tail.

#### Table Stakes

| Feature | Why Expected | Complexity | Depends on |
|---|---|---|---|
| **Generalized event detector v1 — 6 cross-genre detectors** (`KICK_SWAP` / `SUB_LAYER_ARRIVAL` / `BREAKDOWN_KICK_KILL` / `REENTRY_KICK_LAND` / `KICK_DENSITY_SHIFT` / `PHRASE_BOUNDARY`) | Kaan's "feels surface-level" critique post hard-tek session diagnosed v4's `LAYER_ARRIVAL` as genre-blind. These six detectors are the minimum to make hard-tek (and by extension techno, house, DnB) reactions ground in the moment that defines the bar. | M (~5 E-days) | Existing: v4 `EventDetector` + `AudioBuffer.snapshot_features` extension (kick-band centroid / harmonic ratio / crest factor) + `MusicState.phrase_position` (autocorr-derived). |
| **Citation grammar in prompts** (`[ev:KICK_SWAP@04:22]` / `[aud:peak_rms@04:22]` / `[midi:deckA_filter:23@04:22]` / `[track:"..."]`) | Without grammar in the prompt, Gemini doesn't emit tokens to lint. Seeded into system instruction at v2.0 launch; live linter enforces in v2.0 follow-on. | S (1 E-day, prompt-only) | Existing: 6-cell prompt matrix + TurnHistory (Phase 10). |
| **Cross-software MIDI grounding (10 controllers)** — DDJ-FLX4 + 9 others, magnitude-aware EQ moves | Already in scope at v0.1.0 but the v2.0 absorption confirms 10-SKU library + `MidiMapLoader` + generic-MIDI fallback ships as the *spine* of cross-platform grounding. The MIDI controller is the universal layer that works the same across every DJ app. | M (~5 E-days) | Existing: Phase 9 (FLX4 verified, 9 SKUs ship by JSON). |

#### Differentiators

| Feature | Value Proposition | Complexity | Depends on |
|---|---|---|---|
| **Citation linter (live + debrief, cross-mode)** — stdlib `re`, in-memory Evidence registry, sentence-level for debrief, response-level for live (ack-bank fallback) | The technical implementation of the anti-slop thesis. No competing AI-for-DJ tool grounds claims this way. Slop-ratio telemetry is itself a trust signal surfaced in UI. | M (~3–5 E-days) | v2: citation grammar + Evidence registry hook from EventDetector / MusicState / ControllerState / TrackInfo. Existing: anti-slop filter + scorecard (Phase 10). |
| **Library intelligence — Gemini Embedding 2 + sqlite-vec + Bravoh pipeline port** | First product to read a DJ's own library and say "track X you played last week fits here" — grounded in their actual collection, not a generic recommender. Closes the "Gemini hallucinates a track name" failure mode entirely (track citations must come from imported library). | H (~7 E-days) | v2: Pyrekordbox XML import (the library source). Existing: Phase 5 proxy quota for embed calls. |
| **Hard Tek deep-genre detector overlay** (`ACID_LINE_ENTRY`, plus tuned KICK_SWAP thresholds against 7-10 reference tracks) | Kaan's primary practice. Closes the "AI says 'lead synth' when it's a 303 sweep" hallucination class. Marketed in the demo film and Hard Tek subculture wedge. | M (~3 E-days, tuning-heavy) | v2: Generalized event detector v1 (acid overlay slots onto it). |
| **Genre auto-classifier via Gemini Embedding 2 nearest-neighbor** | One-shot at session start + on `TRACK_CHANGE`, classifies against hand-curated 40-anchor library shipped in binary. ~$0.0001 per classification. Routes the per-genre detector roster atomically without session restart. | M (~2 E-days post-library-intel) | v2: Library intelligence (uses the same embed-call infrastructure). |

#### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---|---|---|---|
| **CLAP / OpenL3 / MERT for audio understanding** | Industry "standard" for music embedding, recommended by external research. | Kaan rejected: vibemix is Gemini-only; multimodal embedding 2 covers it. Bundling 50–200MB ML models blows the one-click install budget. | Gemini Embedding 2 — natively multimodal, free tier covers most libraries, no model bundling. |
| **mem0 / vector DB for long-term DJ profile** | "Modern AI memory" pattern. | Solves the wrong problem — DJ tendencies are summarisable in 2KB JSON, not retrievable factoids. Adds Qdrant/Chroma dep, breaks one-click install. | Structured JSON profile (~2 KB, ≤10 tendencies, Gemini regenerates each session, injected verbatim into next session's prompt). |
| **30-session formal eval harness with LLM scorer** | Standard ML eval discipline. | Phase 16 is **Kaan's DJ ear**, not a formal suite (per memory `project_phase_16_kaan_dj_testing`). Building the harness eats 2–3 weeks against a 4-week marketing window. | Kaan listens to his own session recordings + scrubs to detector fires. Tuning harness CSV (`scripts/tune_hard_tek_detectors.py`) gives him the audit surface; no F1 score required. |
| **Live-mode partial citation enforcement** (strip half a 2-sentence response) | Sentence-level is the standard linter granularity. | A 1-of-2 stripped sentence in live mode leaves a fragment ("Yeah."). Worse than the unstripped response. | Response-level enforcement in live: if no valid citation anywhere, drop entire reply, fall back to pre-canned ack from Bucket A. Sentence-level only for debrief/library/genre. |
| **Streaming-incremental citation linting** | "Optimize the linter, save 50ms." | The full lint pass is ~3ms on a 2-sentence response — invisible against 1500ms LLM TTFT. Implementation complexity > the saving. | Lint synchronously between LLM-complete and TTS-start. |

**Research notes:** [G-genre-taxonomy.md](v2-buckets/G-genre-taxonomy.md) (per-genre event catalogs), [G-followup-1-hard-tek-dsp.md](v2-buckets/G-followup-1-hard-tek-dsp.md) (KICK_SWAP DSP recipe + 10 tuning tracks + per-genre detector dispatch), [E-followup-1-citation-linter.md](v2-buckets/E-followup-1-citation-linter.md) (grammar + EBNF + Python `CitationLinter`), [F-library-intelligence.md](v2-buckets/F-library-intelligence.md) (Gemini Embedding 2 + sqlite-vec + chunk strategy), [B-industry-integrations.md](v2-buckets/B-industry-integrations.md) (MIDI as universal layer).

---

### Category 2 — Latency & Liveness

**Thesis:** Cascade is the latency floor, not native audio. The fix is layered cover-up of Gemini's 1.5–3s TTFT — make T+150ms the perceived first reaction by combining a pre-canned ack, mascot anticipation, and overlay ring before the LLM finishes.

#### Table Stakes

| Feature | Why Expected | Complexity | Depends on |
|---|---|---|---|
| **Pre-canned ack bank** (~40 OPUS samples organised by event class — drop_hit / track_change / mix_move / silence_break / generic_filler) | Sub-100ms first sound is the difference between "alive" and "voice assistant doing music commentary." Industry-standard backchanneling pattern (Retell, Vapi, Google Duplex). | S (~2 E-days; generation offline once, runtime is disk-read + PlaybackQueue) | Existing: PlaybackQueue (Phase 4), VoiceRecorder (Phase 2). |
| **Prompt diet + Gemini context caching** (audio 18s→6s for non-PHASE events; drop screen on `MIX_MOVE`/`HEARTBEAT`; cached_content for system instruction with 1024-token floor) | Cheapest TTFT win (500–1500ms) with zero anti-slop regression. Caching's 1024-token floor needs deliberate padding — verified in A-followup-1. | S (~2 E-days) | Existing: cascade LLM path in `DJCoHostAgent.llm_node` (Phase 4). |

#### Differentiators

| Feature | Value Proposition | Complexity | Depends on |
|---|---|---|---|
| **Cancel-and-refire on higher-priority events** (`SpeechHandle.interrupt(force=True)`, empirically verified through cascade in A-followup-1) | Stale reactions kill the "real DJ friend" illusion. Cancel + re-fire when a higher-priority event arrives mid-generation keeps reactions in-bar. Capped at 1 cancel per 8s. | S (~2 E-days) | Existing: LiveKit `AgentSession` cascade (Phase 4). |
| **Predictive drop firing** (`buildup_score > 0.7` + `phrase_boundary_in <= 2 bars` → fire `generate_reply` 2 bars early, gate playback on actual drop, cancel on 3s timeout misfire) | The biggest semantic win for fast genres. Hard Tek at 170 BPM (1.4s/bar) cannot land an in-bar reaction without prediction. Gated on Kaan's ear-test before on-by-default. | M (~5 E-days; design complete in A.md, needs the predictive watcher + mute-able PlaybackQueue sink) | v2: cancel-and-refire + Generalized event detector v1 (the predictive signal feeds off `PHRASE_BOUNDARY` + buildup heuristic). |

#### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---|---|---|---|
| **Revert to `gemini-2.5-flash-native-audio` for the latency floor** | Native-audio claims 400ms voice-to-voice vs cascade's 1500ms+. | Kaan tested it in v2: grounding regresses badly. Native audio cannot accept the multimodal Part shape the cascade does — the whole anti-slop thesis breaks. | Stay on cascade; latency is masked by the four-layer stack, not eliminated. |
| **Speculative pre-generation parallel sessions** (PredGen-style, 2× LLM cost) | "Doubles the perceived speed." | Doubles API cost. The 50€/mo budget can't absorb it. | Predictive firing (single session, fire 2 bars early, cancel on misfire) hits the same perceived-speed target. |
| **Drop `thinking_level` to off entirely** | Saves 200–400ms TTFT. | Already at `"minimal"` — remaining win is small and trades against reaction quality on borderline calls. | Keep `"minimal"` until ear-test shows reactions feel rushed; revisit only if needed. |
| **Aggressive cancel budget** (no cap, cancel on every priority bump) | "More responsive." | Wasted API cost on canceled responses. Hard Tek's 12s/phrase rhythm means an unchecked cancel rate could 3× the per-user budget. | Cap at 1 cancel per 8s (soft); 30/hour hard cap with telemetry. |

**Research notes:** [A-latency.md](v2-buckets/A-latency.md) (12 latency levers + recommended stack + `interrupt(force=True)` empirical verification + caching 1024-token floor), [synthesis-viral-demo.md](v2-buckets/synthesis-viral-demo.md) §4 Latency timing diagram (T+150ms perceived-floor breakdown).

---

### Category 3 — Personality & Anticipation

**Thesis:** Mascot v0.1.0 is single-layer; the "feels alive" gap is structural. Four-layer additive blending (mood + anticipation + speak + effect) + beat-coupled procedural idle + inline emote-tag vocab raises the bar from "decoration" to "live indicator of what the system actually saw."

#### Table Stakes

| Feature | Why Expected | Complexity | Depends on |
|---|---|---|---|
| **Mascot anticipation layer (1-above-mood, simplified)** — `prep_lean_in_hyped` / `prep_lean_in_neutral` / `prep_head_turn` clips, fire at event-detect (T+50ms), crossfade to talk_loop on first TTS audio | The highest-leverage perceived-latency mask (400–1200ms covered). Without it, the mascot looks frozen during the 1500ms Gemini round-trip and the user assumes the app crashed. Ships ahead of the full 4-layer rewrite. | S (~3 E-days; 1 day Gemini text-channel timing spike + 2 days impl + assets) | Existing: mascot Three.js renderer (Phase 13), event-dispatcher. |
| **Beat-coupled procedural hip-bob driven by BPM + RMS** | Already 80% wired (Phase 13 accepts bpm + downbeat_phase + bpmConfidence ≥ 0.6). The missing piece is a continuous additive bone-subset overlay on `Hips`, not a clip swap. Reads as "moves WITH me." | S (~2 E-days) | Existing: Phase 13 mascot + Phase 6 BPM + phrase_position from v2 PHRASE_BOUNDARY detector. |

#### Differentiators

| Feature | Value Proposition | Complexity | Depends on |
|---|---|---|---|
| **4-layer additive state machine** (mood + anticipation + speak/reaction + effect, layered via Three.js `AnimationUtils.makeClipAdditive`) | The full structural fix for "same emote every time." Cross-layer overlaps are the entire point — mood layer keeps breathing alive even mid-react. Costs +1–2ms/frame on M2. | H (~14 E-days incl. refactor + asset commissioning + vitest port) | v2: Mascot anticipation layer (proves the 1-above-mood shape works first). |
| **Inline emote-tag vocabulary (15 tags + 1 mood-set tag)** — `[hype]` / `[chill]` / `[teach]` / `[surprise]` / `[nod_yes]` / `[gesture_deck_a]` / `[lean_listen]` / `[silent]` etc., stripped from TTS, mapped via `emotionMap` to states | Open-LLM-VTuber pattern adapted to DJ context. Lets Gemini drive mascot expression per turn instead of one default-per-event-type. Requires the layered architecture and the text-channel-timing spike. | M (~5 E-days post-spike) | v2: 4-layer state machine + 1-day spike on Gemini Live text-channel ordering (Bucket D A3 risk). |
| **Amplitude-banded talk variants** (`talk_loop_calm` / `talk_loop_normal` / `talk_loop_energetic` selected per emote tag) | 80% of the "alive mouth" feel at 10% of the cost of ARKit blendshape re-rigging. Mixamo strip-blendshapes constraint forces this path; the constraint is the feature. | S (~1 E-day code + asset cost) | v2: 4-layer state machine + emote-tag vocab. |

#### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---|---|---|---|
| **ARKit / Oculus viseme blendshapes for procedural lip-sync** | "Realistic mouth motion." | Mixamo stripped blendshape export in 2020; re-rigging is 2–3 weeks + uncanny-valley risk on the current stylised mascot. | Amplitude-banded talk variants (3 clips, 1 E-day). |
| **Live2D / anime-style 2D mascot rig** | "More expressive face." | Locks demographic (anime overlap with bedroom-DJ audience is real but narrow). Abandons the stylised-abstract head approach that dodges uncanny valley. | Body-language-first stylised 3D rig (current direction); commission 8 new clips for ~$1500–2000. |
| **Multi-mascot user-gen ("/hatch")** | Long-term retention play, "design your own pet." | v2.x stretch per memory (`project_mascot_as_vtuber_personality_surface`). Adds asset pipeline + safety/moderation surface. Not v2.0 scope. | Single mascot (DJ bat placeholder), mood variation on same rig. |
| **Procedural jaw bone rotation driven by AudioAnalyser** | "Cheap lip-sync without re-rigging." | Reads as "puppet flapping jaw" — generic, not stylised. Worth re-evaluating as a v2.x polish layer once core 4-layer ships. | Defer to v2.x; let talk variants carry expressiveness in v2.0. |

**Research notes:** [D-mascot-emotion.md](v2-buckets/D-mascot-emotion.md) (4-layer architecture, anticipation recipe, emote tag vocab, Mixamo blendshape constraint), [synthesis-viral-demo.md](v2-buckets/synthesis-viral-demo.md) §1 Storyboard table (mascot beats integrated with overlay + ack).

---

### Category 4 — Cross-Software Integration

**Thesis:** Mixxx is the only DJ platform with a real-time deck-state surface — and OSC is currently a draft PR upstream. djay Pro Mac is the only viral-demo-tractable overlay target. The MIDI controller is the cross-platform telemetry layer that works the same across every DJ app. Pyrekordbox XML is the durable library path (SQLCipher key extraction broken post-Rekordbox 6.6.5).

#### Table Stakes

| Feature | Why Expected | Complexity | Depends on |
|---|---|---|---|
| **10-SKU MIDI controller library + `MidiMapLoader`** — DDJ-FLX4 (verified) / FLX6 / FLX10 / SX3 / 400 / 1000 / XDJ-RX3 / Numark Party Mix Live / Mixstream Pro+ / Hercules Inpulse 300 + 500 | Cross-platform grounding spine. The B-bucket research found bedroom-DJ controllers are concentrated in ~5 SKUs; covering 10 hits ~80%. JSON-per-SKU + auto-detect by port-name substring. | M (~5 E-days; FLX4 verified, others Mixxx-XML-derived) | Existing: Phase 9 (`vibemix.midi/` package, `ControllerState`, generic-MIDI fallback, 2s hot-plug watcher). |
| **Pyrekordbox XML one-shot import** — file picker → SQLite cache → fuzzy title/artist/BPM lookup | The durable path. Pioneer obfuscated the SQLCipher key starting Rekordbox 6.6.5, breaking automatic master.db reads. XML export is unencrypted and works for every Rekordbox version. | S (~3 E-days; ~150 LOC parser + 4-tier fuzzy lookup) | None (greenfield); writes to `~/Library/Application Support/vibemix/library/rekordbox.db`. |
| **djay Pro Mac overlay highlight (12 elements)** — hand-mapped percentage-of-window JSON + AX refinement when available + amber-ring Canvas 2D overlay window | The viral demo anchor. djay is the only major DJ app where AX returns useful UI element data (Rekordbox + Serato render to canvas). 12 elements covers >80% of likely "point at X" utterances in a 30s cut. AX call must run in Rust parent (not sidecar — issue #8329). | M (~5–7 E-days incl. window-tracker + element map + overlay window) | Existing: Tauri shell, mascot_window.rs builder pattern, `cohost_v4.py:224-246` djay-window finder logic. |

#### Differentiators

| Feature | Value Proposition | Complexity | Depends on |
|---|---|---|---|
| **Generic-MIDI fallback that observes without inferring** | Conservative auto-classification: detect knobs + buttons by activity, NEVER auto-assign roles. Surface picker UI after 5 min of observation. Closes "controller not supported" gracefully without producing confidently-wrong "Deck B EQ killed" claims. | S (~1 E-day) | Existing: Phase 9 generic fallback foundation. |
| **Mixxx OSC bridge (opt-in, feature-flagged)** behind `--enable-mixxx-osc` for users running PR #14388 custom build | Mixxx is the only DJ app with a real-time deck-state surface, and the free-software DJ community is the right cultural audience for OSS vibemix. Ship behind flag in v2.0; promote to first-class if PR merges. | S (~2 E-days; ~190 LOC `MixxxBus` using `python-osc==1.10.2`) | None (greenfield). |

#### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---|---|---|---|
| **Pioneer ProDJ Link CDJ integration** | "Full per-deck telemetry including phrase data from CDJ-3000." | Wrong market — requires Pioneer CDJ hardware on an Ethernet LAN. Bedroom DJs run controllers, not CDJs. Install friction (JVM bridge + open-beat-control jar) is brutal. | Skip entirely. Optional add-on if a CDJ Pro SKU ever ships. |
| **Native Rekordbox/Serato/Traktor real-time API hooks** | "Every DJ app should work." | Algoriddim, Pioneer, Serato, Native Instruments all refuse to ship third-party APIs. Decompiling / dylib injection crosses the EULA red line. | Audio + screen + MIDI grounding (the current cross-platform path). Mixxx is the only platform with a real surface; everything else stays on the universal path. |
| **VirtualDJ OSC bridge in v2.0** | "Best per-deck subscribe-on-change of all closed apps." | Gated behind paid Pro license — small slice of bedroom DJs. Worth a parallel `vdj_osc.py` only if VDJ Pro user demand emerges post-launch. | Defer to v2.x demand-driven. |
| **Mapping transpiler (read Mixxx XML, emit Rekordbox/Serato/djay mapping files)** | "Cross-app mapping management." | Write-side is undocumented binary formats (Serato `.tsi`, djay `.djmap`). Out of scope; competes with Bome MIDI Translator. | Ship per-controller JSON in vibemix's own format. Users keep DJ-app mappings unchanged; vibemix parallel-listens. |
| **Rekordbox / Serato overlay highlight in v2.0** | "DJ majority uses these." | Canvas-rendered UIs return empty AX trees; only template matching works, and it's brittle/slow at multi-scale. Ships v1.2 fast-follow per the B-bucket. | Lead the viral demo on djay Pro Mac. Frame copy as platform-agnostic ("AI that watches your set"). |
| **djay UI redesign auto-detection** | "Coord map breaks on major djay version bump." | Auto-version-walking adds a fragile maintenance surface. | Version-pin the map (`djay_pro_5.json`), detect version via `CFBundleShortVersionString`, fall back to nearest-known map with a warning logged. |

**Research notes:** [B-industry-integrations.md](v2-buckets/B-industry-integrations.md) (per-platform deep dives, tractability matrix, ProDJ Link demotion), [B-followup-1-v11-integration-spec.md](v2-buckets/B-followup-1-v11-integration-spec.md) (MixxxBus 190-LOC spec, Pyrekordbox XML schema + fuzzy match, 10-SKU JSON layout + Sync note 0x58 vs 0x60 resolution), [C-ui-overlay.md](v2-buckets/C-ui-overlay.md) (djay overlay approach hybrid (a)+(b), element vocabulary, Tauri #8329 mitigation, 30s storyboard).

---

### Category 5 — Coaching & Memory

**Thesis:** Real teaching = identify-cause-correct loops tied to timestamps. The debrief is where actual coaching lives (live is too latency-constrained for long-form). Long-term DJ profile is structured summary, not vector retrieval.

#### Table Stakes

| Feature | Why Expected | Complexity | Depends on |
|---|---|---|---|
| **Post-session debrief (chaptered review + voiced TL;DR + 3 drills + clickable timeline)** — single Gemini call per session, ~$0.05–0.15 per debrief, SBI for critique + STAR-AR for drills (NOT sandwich) | Live mode can't teach (1–2 sentences max). Debrief is where deliberate practice closes. Strava-pattern chapter cards + Whoop-pattern auto-detection + Synthesia-pattern scrub markers. Voiced TL;DR optional (off by default for Pros). | H (~7 E-days; Gemini prompt + UI surface + scrub bar + 3-drill cards) | Existing: VoiceRecorder per-session `input.wav` / `voice.wav` / `events.jsonl` (Phase 2/15). v2: citation linter (sentence-level for chapters). |
| **3-drill cap with "pin to next session" CTA** | Research consensus (Curious Lion, The Geeky Leader): more drills = less stickiness. 3 is the hard cap. "Pin to next session" closes the deliberate-practice loop by injecting drill context into next session's live-mode prompt. | S (~1 E-day; structured drill card spec, profile.active_drills field) | v2: Post-session debrief. |
| **Long-term DJ profile (~2 KB structured JSON, ≤10 tendencies, regenerated each session)** | Structural summary at session end, injected verbatim (~600–800 tokens) into next session's system prompt. Rejected mem0 / vector DB — DJ tendencies aren't retrievable factoids, they're summarisable invariants. | S (~2 E-days; profile schema + regeneration prompt + live-prompt injection) | v2: Post-session debrief (generates the profile). |

#### Differentiators

| Feature | Value Proposition | Complexity | Depends on |
|---|---|---|---|
| **Skill-ladder critique (Beginner / Intermediate / Pro)** changes WHAT gets flagged, not just wording | Beginner = mechanical (beatmatch drift, phrase entry, mic bleed). Intermediate = phrasing + energy curve + harmonic. Pro = micro-craft (filter timing within bar, EQ kill placement). Same prompt scaffolding, different lenses. | S (~1 E-day; per-level templates in `vibemix/prompts/`) | Existing: 6-cell prompt matrix (Phase 10). v2: post-session debrief (the critique surface). |
| **Library-aware drill cards** ("3 tracks from your library that fix this") below each drill's SUCCESS criterion | Closes the cross-bucket arrow: debrief diagnoses → library intelligence proposes. Filtered by Camelot compatibility + recency. Promotes drills from advice to actionable practice. | S (~1 E-day post-library-intelligence) | v2: Library intelligence + post-session debrief. |
| **Per-session slop ratio surfaced in debrief UI** ("kept 47 of 52 reactions; 5 dropped for not citing real events") | Transparency feature — turns anti-slop discipline into a visible product signal. The kind of trust-building that differentiates from generic AI commentary. | S (<1 E-day, derived telemetry) | v2: citation linter telemetry. |

#### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---|---|---|---|
| **Full-set voiced playback (15+ minute debrief read aloud)** | "Listen-while-you-cook UX." | Long-form voiced has no skim affordance. Whoop / Strava users skim text first, dive into ~1 section. Voiced past 90s feels worse than reading. | 60–90s voiced TL;DR at the top + chapter-card text body. |
| **Feedback sandwich** (positive-corrective-positive) | "Soft critique pedagogy." | Research-rejected — Radical Candor + Faculty Focus + PMC clinical paper all show it's ineffective; corrective-positive-positive lands better. | SBI (Situation-Behavior-Impact) for critique + STAR-AR for drills. |
| **Per-note / per-bar accuracy scoring** (Synthesia piano pattern) | "Quantified feedback." | DJing is performative, not "correct/incorrect" — applying a scoring rubric forces a wrong model. | Identify-cause-correct loops + clickable timeline scrub. |
| **Ask-Tell-Ask interactive turn-taking in debrief** | "Reflective coaching." | Requires multi-turn Gemini calls inside the debrief — 3× cost + UI complexity. Out of v2 scope. | Defer to v2.x stretch; ship one-shot debrief at v2.0. |
| **Chain-of-Verification for every claim** (regenerate the debrief, verify each claim, discard inconsistent ones) | "Better grounding." | 2× Gemini cost; right shape for v2.x "deep debrief" opt-in but overkill for default. | Citation linter at sentence level catches 90%+ of unsourced claims at ~30–80ms cost. CoVe deferred. |
| **Auto-debrief on every session ≥1 min** | "Reduce friction." | Spends Gemini budget on sessions users don't care to review. | Auto-trigger only if session > 15 min; user-click otherwise. |
| **Streaks / XP gamification** (Duolingo pattern) | "Engagement loop." | Reads as patronising to Pros; gross-fit for DJ identity. | Skill-ladder critique (Beginner/Intermediate/Pro) — the seriousness the user wants. |
| **mem0 / motorhead / Qdrant for long-term memory** | "Personal-AI memory infrastructure." | DJ tendencies fit in 2 KB; retrieval is not the problem. Adds vector-DB dep + breaks one-click install. | Structured JSON profile + verbatim prompt injection. |
| **30-session formal eval harness for the debrief** | Standard ML eval. | Phase 16 is Kaan's DJ ear (memory directive). Don't auto-build the harness. | Tuning CSV + Kaan's session-recording audit (already exists from VoiceRecorder). |

**Research notes:** [E-debrief-pedagogy.md](v2-buckets/E-debrief-pedagogy.md) (DJ teaching pedagogy synthesis, debrief UX patterns, profile architecture rejecting mem0, anti-slop tone calibration).

---

### Category 6 — Ship & Distribution

**Thesis:** v0.1.0 milestone partially shipped (Phases 1–14); the v2.0 absorption pulls the remaining ship infrastructure (recording browser, UAT, sign+notarize, GitHub release matrix, day-zero ops) into this milestone alongside the research-driven features. Day-Zero Operations and Hallucination Verification Gate (Kaan DJ ear test) are the load-bearing release gates.

#### Table Stakes

| Feature | Why Expected | Complexity | Depends on |
|---|---|---|---|
| **Recording browser + retention enforcement** — per-session dir with `input.wav` / `voice.wav` / `events.jsonl` + UI list + delete + retention cap (configurable; default 30 days) | The VoiceRecorder already writes per-session under `recordings/`. The browser is the missing UX surface — open Finder/Explorer to session, replay AI voice, delete. Without retention enforcement, disk fills silently. | M (~2 E-days; UI surface + retention cron) | Existing: VoiceRecorder (Phase 2/15). |
| **Apple Developer ID sign + notarize + DMG** | macOS Gatekeeper rejects unsigned binaries → 0% install conversion. Kaan has the Developer ID; Issuer ID is the open blocker (Phase 18 absorbed). | S (~1 E-day once Issuer ID lands) | Existing: Phase 18 P01–05 partially shipped. |
| **SignPath Foundation Windows MSI** | Same Gatekeeper analogue (SmartScreen). SignPath OSS cert is free for OSS projects; application has ~1-week SLA — must be filed day-1 of v2.0 milestone (Phase 1 carry-forward in STATE.md). | M (~2 E-days post-cert + 3 weeks lead time on the application) | None (Kaan-blocked operationally). |
| **GitHub release matrix** (mac arm64 + intel + win x86_64 + win arm64, single tag per cut, real changelog) | Phase 18 absorbed. Auto-built via CI matrix on tag push. | M (~2 E-days CI work) | v2: Sign + notarize discipline (above). |
| **README full rewrite + branding + social assets** — hero PNG + architecture SVG + demo GIF placeholder + 8 controller logos grid + 12-question FAQ + value-prop paragraph above the fold | The repo is the front door for 100% of organic discovery. Phase 19 absorbed. Repo description + topics tags optimised for search. Privacy/cost/Linux/Gemini-Live FAQ pre-seeded. | M (~3 E-days; mostly content) | Existing: Phase 19 partially shipped (architecture SVG + hero PNG done in commit `137240b`). |
| **Day-Zero Operations** — fresh-machine rehearsal (clean macOS VM + Windows VM), install playbook, post-launch playbook (rate limit + Bravoh proxy load, support triage) | Phase 20 absorbed. Without a fresh-VM rehearsal, day-one users hit BlackHole / TCC / signing edge cases nobody anticipated. | M (~3 E-days; rehearsal + playbook authoring) | v2: Sign + notarize + release matrix. |
| **Hallucination Verification Gate (Kaan DJ ear test)** — Kaan runs 3–5 real DJ sessions with v2.0 features active, judges by feel | The hard release gate. Per memory `project_phase_16_kaan_dj_testing`: NOT a formal eval suite, Kaan's personal testing. Tuning CSV from `scripts/tune_hard_tek_detectors.py` is the audit surface. | M (~3 E-days Kaan-time, calendar-blocking) | v2: Generalized event detector + citation linter + mascot anticipation + ack bank (the surfaces under test). |

#### Differentiators

| Feature | Value Proposition | Complexity | Depends on |
|---|---|---|---|
| **One-click install <60s promise on README** (delivered via DMG + MSI + auto-deps + wizard) | The hard requirement per memory `project_one_click_install_hard_req`. Every dep choice is green/yellow/red rated for install impact (BlackHole = yellow but unavoidable on Mac audio capture; SignPath = green for end users). | S | Existing: Phase 11 calibration wizard (auto-detect devices + permission checks). |
| **Free for end users via Bravoh-managed proxy** (per-client rate limit, no API key entry) | Friction kills virality; cost is treated as marketing. Proxy already shipped (Phase 5 — JWT HS256 + Redis quota at api.altidus.world). | (shipped) | Existing: Phase 5. |
| **Polished README sexification** — branded hero banner, install GIFs, screenshots gallery, feature matrix (Beginner/Intermediate/Pro × Hype/Coach), CONTRIBUTING.md with controller-mapping contribution path | The repo doubles as the brand surface. CONTRIBUTING controller-mapping path is the most-likely external PR vector (community contributes SKUs vibemix lacks). | M | v2: README rewrite + 10-SKU MIDI library (Category 4). |

#### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---|---|---|---|
| **User-supplied Gemini API keys** | "Reduce our cost." | Friction kills virality (memory `feedback_no_scope_creep_clean_utility`). Bravoh-side proxy handles cost as marketing spend. | Bravoh proxy with per-client rate limit (Phase 5 shipped). |
| **30-session formal hallucination eval** | Standard ML release gate. | Kaan's DJ ear is the explicit test per memory. Building the harness costs 2–3 weeks. | Kaan-driven session audit + tuning CSV. |
| **Linux support** | "Niche OSS audience." | Doubles platform-engineering cost. DJ Linux audience is small. | macOS + Windows only in v2.0; Linux explicitly excluded. |
| **Custom voice cloning** | "Brand-distinct AI voice." | Bravoh-only stack; Gemini TTS prebuilt voices cover the matrix. Cloning adds privacy + safety surface. | Gemini TTS prebuilt voices (Achird default; male/female switchable). |
| **Real-time stream-to-Twitch/YouTube hook** | "Live broadcast integration." | Out of scope; recording for later sharing is enough. | Session recordings already exist; user shares clips post-hoc. |
| **Auto-update channel with silent installs** | "Modern app UX." | Adds Tauri updater complexity + signing key escrow. Out of v2.0 scope. | Tagged GitHub releases; user downloads new DMG/MSI when bumped. |
| **Anonymous telemetry without explicit consent** | "Product analytics." | Privacy-paranoid DJs would block on this. | Local-only events.jsonl per session; opt-in telemetry is a v2.x consideration. |
| **Skipping Day-Zero rehearsal "to save time"** | "Beta ship + iterate." | First-impression DJ apps that crash at day-zero hit ~5% retention. | Phase 20 fresh-VM rehearsal is mandatory before tag-push. |

**Research notes:** [project_v0_1_0_rc1_open_bugs](memory file), [project_phase_16_kaan_dj_testing](memory file), [project_one_click_install_hard_req](memory file), Phase 18+19+20 plans in `.planning/phases/` (already drafted).

---

### Category 7 — Viral Wave

**Thesis:** The viral demo is not a feature, it's the engineering critical path. Beat A (point-at-knob) + Beat B (anticipation lean-in) + Beat C (3-second silence) = three viral assets each scrolled-content-ready on their own. Cross-platform copywriting is pre-seeded; pre-seeded FAQ in comments closes the trust loop.

#### Table Stakes

| Feature | Why Expected | Complexity | Depends on |
|---|---|---|---|
| **30-second viral demo film** — single take or curated multi-take edit; djay Pro 5 in 2-deck mode; CDJ Whisper color direction; Kaan + DDJ-FLX4 + HD25 headphones | One filmable cut feeds Twitter / IG Reels (IT + EN) / Reddit / HN. 6+ takes per beat; edit magic into the cut. | M (~2 E-days post-feature-complete) | v2: djay overlay + mascot anticipation + ack bank (the three signature beats need all three present simultaneously). |
| **Twitter thread (5 posts)** — technical breakdown, Beat A hero image, code snippets, GitHub link | Twitter is the engineering-credibility channel. Thread structure mirrors how Cursor/Pi shipped their viral moments. | S (~1 E-day; content) | v2: 30s demo film. |
| **IG Reels (IT + EN) — vertical 9:16 recut** — Kaan's face top third + djay screen + mascot bottom two-thirds, caption-baked | The cinematic channel + Italian community wedge. Bravoh's 140k-view real is the same account leverage. | S (~1 E-day; reframe + caption + bilingual copy) | v2: 30s demo film. |
| **Reddit r/Beatmatch + r/DJs thread** — Beat C silence hero + open-source angle + 60-second-install promise | The DJ-community-credibility channel. Leads with Beat C (the anti-slop reveal) because the community is exhausted by AI slop. | S (~1 E-day; content + pre-seeded FAQ) | v2: 30s demo film. |
| **Hacker News Show HN post** — Beat A hero + engineering breakdown of the grounding stack + Tauri #8329 mitigation as a real story | The hacker-credibility channel. Leads with the engineering: 4 grounding signals + cascade tradeoff + sidecar AX inheritance mitigation. | S (~1 E-day; content) | v2: 30s demo film. |
| **Pre-seeded FAQ in comments** — privacy / cost / no-Linux / no-Gemini-Live / djay-only-launch / how-it-doesn't-hallucinate (8–12 questions across all four channels) | The first 20 comments make-or-break the thread momentum. Kaan + Francesco rotate answering; canned-but-honest replies that close the trust loop fast. | S (~0.5 E-days) | v2: All four channel posts. |

#### Differentiators

| Feature | Value Proposition | Complexity | Depends on |
|---|---|---|---|
| **Beat A — "AI points at the knob" hero frame at 0:09** — amber ring on Deck A mid EQ, mascot in talk pose, caption-baked "Mids are stacking on A — cut 'em 3 to 4 dB" | The screenshot that captions itself. Single image works on Twitter / Reddit / IG without context. Cursor-autocomplete-moment shape. | (part of demo) | v2: djay overlay. |
| **Beat B — "AI anticipation lean-in" frame at 0:07** — mascot already in `prep_lean_in_hyped` pose ~50–150ms before voice arrives | The "huh — wait, what?" beat for viewers exhausted by reactive AI. Frames AI as predictive, not reactive — ChatGPT Voice / Pi orb shape but anticipating the *world* not its own processing. | (part of demo) | v2: Mascot anticipation. |
| **Beat C — 3-second silence at 0:22–25** — AI says nothing; mascot keeps idle-bobbing; no overlay; subtitle in post: "The AI shuts up when there's nothing to say" | The anti-slop reveal. Pi-vs-ChatGPT-Voice "silence as feature" axis. The frame that proves the positive frames are real. | (part of demo) | v2: Citation linter live-mode strip + ack bank fallback (the actual technical reason silence happens). |
| **Paired ring + linker** (filter knob + play/cue zone connected by thin amber line at 0:14–18) | One signature spatial trick that sells "AI sees relationships between controls," not just "names things." | (part of demo) | v2: djay overlay 12-element vocabulary + ring rendering supports multi-element with connectors. |
| **GitHub stars ticker on outro frame** (0:29–30) | Social proof in motion at the CTA moment. Records pre-launch 15+ stars from friends/dev network for visible ticking. | (part of demo) | v2: Day-Zero seed wave from friends + ARRAY community (per PROJECT.md). |

#### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---|---|---|---|
| **Overpromise "works on every DJ app"** in copy | "Broader appeal." | First Reddit comment: "but I use Rekordbox" → trust collapses. | Frame copy as platform-agnostic ("AI that watches your set"); README explicitly lists djay-overlay as v2.0 with Rekordbox-overlay v1.2 fast-follow. |
| **Real-time AI demo without pre-scripted beats** | "Authentic / no editing tricks." | The AI is real-time during filming but Kaan doesn't pre-know which knob it'll point at. Multi-take + magic-take edit is industry-standard for product demos. | Multi-take strategy; honest about edit but never about behaviour. AI is real; the curation is curated. |
| **Flashing UI / constant ring fires during demo** | "More AI presence." | Reads as AI slop — the opposite of the thesis. | 8s cooldown per element; at most one ring per 3s utterance; deliberate silence beat at 0:22–25. |
| **Influencer / sponsored-post launch** | "Paid amplification." | Wrong audience cue — open-source-DJ community filters out paid promo. | Organic Francesco-DJ-network outreach + small (€50–100) IG/TikTok ads + ARRAY community + Bravoh-team friends seeded. |
| **Auto-translation of pre-seeded FAQ** | "All locales." | Loses Kaan/Francesco's voice. Reddit/HN reads as translated-AI-copy. | English + Italian (Kaan + Francesco's actual languages) hand-written. Other locales emerge organically post-launch. |
| **Demo film delayed to v2.1 "for polish"** | "Ship clean utility first, market later." | The Bravoh public launch wave window is the 4-week post-v2.0 window. Slipping the demo blows the wave. | Treat the demo film as the engineering critical path. 7-day spike day-1 of v2.0 close. Buffer day on day 7 for film. |

**Research notes:** [synthesis-viral-demo.md](v2-buckets/synthesis-viral-demo.md) (full 30s storyboard table, three signature beats, 7-day engineering critical path, per-platform post angles, risk register).

---

## Cross-Category Dependency Graph

```
Category 1: Detection & Grounding
    Generalized event detector v1 (6 detectors)
        └──> required by Category 2 (predictive firing reads PHRASE_BOUNDARY)
        └──> required by Category 5 (debrief grounds claims in event types)
        └──> required by Category 7 (Beat A spatial reactions need detector-event-tied points)
    Citation grammar in prompts
        └──> required by Citation linter (v2.0 follow-on)
        └──> required by Category 5 (debrief sentence-level enforcement)
    Library intelligence (Gemini Embedding 2 + sqlite-vec)
        └──requires──> Pyrekordbox XML import (Category 4)
        └──> required by Category 5 (library-aware drill cards)

Category 2: Latency & Liveness
    Pre-canned ack bank
        └──> required by Category 3 mascot anticipation (T+150ms audible signal)
        └──> required by Category 7 Beat B (ack lands while voice hasn't arrived)
    Cancel-and-refire
        └──requires──> Generalized event detector v1 (priority-aware events)
    Predictive drop firing
        └──requires──> Cancel-and-refire + Generalized event detector v1
        └──gated by──> Kaan ear-test (v2.0 ship-on-by-default decision)

Category 3: Personality & Anticipation
    Mascot anticipation layer (1-above-mood)
        └──> required by Category 7 Beat B (the visible-before-voice anticipation)
    4-layer additive state machine
        └──requires──> Mascot anticipation layer (proves shape first)
    Inline emote-tag vocabulary
        └──requires──> 4-layer state machine + Gemini text-channel timing spike

Category 4: Cross-Software Integration
    10-SKU MIDI controller library
        └──> already shipped (Phase 9)
    Pyrekordbox XML import
        └──> required by Category 1 Library intelligence (the source data)
        └──> required by Category 5 library-aware drills
    djay Pro Mac overlay highlight
        └──requires──> Tauri parent-side AX call (mitigates issue #8329)
        └──> required by Category 7 Beat A (the point-at-knob frame)
    Mixxx OSC bridge
        └──parallel──> independent feature-flagged path

Category 5: Coaching & Memory
    Post-session debrief
        └──requires──> Citation linter (sentence-level chapter enforcement)
        └──requires──> Generalized event detector v1 (events.jsonl provides citation anchors)
        └──> generates Long-term DJ profile
    Long-term DJ profile
        └──requires──> Post-session debrief
        └──injects-into──> Next session's live system prompt
    Library-aware drill cards
        └──requires──> Library intelligence + Post-session debrief

Category 6: Ship & Distribution
    Hallucination Verification Gate (Kaan DJ ear test)
        └──gates──> v2.0 release
        └──tests──> Generalized event detector v1 + Citation linter + Mascot anticipation + Ack bank
    Apple Developer ID sign + Windows MSI + GitHub release matrix
        └──parallel──> Kaan-blocked on Issuer ID + SignPath OSS application
    Day-Zero Operations rehearsal
        └──gates──> v2.0 release
        └──requires──> All ship-infrastructure features above

Category 7: Viral Wave
    30s viral demo film
        └──requires──> djay Pro Mac overlay + Mascot anticipation + Ack bank (all three for Beat A/B/C simultaneously)
        └──requires──> Generalized event detector v1 (grounded reactions during filming)
    Four channel posts (Twitter / IG / Reddit / HN)
        └──requires──> 30s viral demo film
```

### Cross-Category Conflicts

- **Predictive firing × Cancel-and-refire budget:** Both consume Gemini API budget. Cap predictive fires at 1 per 12s + cancels at 1 per 8s + 30/hour hard cap.
- **Emote-tag vocab × Live latency:** Emote tag must arrive on Gemini text channel BEFORE TTS audio for the anticipation to fire on time. 1-day spike before committing to the inline-tag approach (Bucket D A3 risk). Fallback: event-detector-driven anticipation (loses fine-grained variety but still hits T+50ms).
- **djay overlay × Tauri sidecar AX (#8329):** AX call must run in Rust parent, not Python sidecar. Architectural constraint that ripples through Window-tracker design + IPC schema (overlay element names cross WS bus as already-resolved screen rects).
- **Library intelligence cost × Bravoh proxy quota:** Library indexing on free tier requires BYO Gemini key (user's free-tier RPM covers it). Live queries through proxy quota. Documented in onboarding wizard.
- **Mascot 4-layer × Mascot anticipation:** Don't ship full 4-layer in v2.0 — anticipation layer alone is the "1-above-mood" simplified subset. Full 4-layer is v2.x polish epic.

---

## v2.0 Cut Recommendation

### Launch With (v2.0)

Ruthless minimum that closes "feels surface-level" + ships the viral demo arsenal.

- [ ] **Generalized event detector v1** (6 detectors: KICK_SWAP / SUB_LAYER_ARRIVAL / BREAKDOWN_KICK_KILL / REENTRY_KICK_LAND / KICK_DENSITY_SHIFT / PHRASE_BOUNDARY) — closes the surface-level critique
- [ ] **Latency stack v1** — prompt diet + Gemini caching + pre-canned ack bank + cancel-and-refire — sub-2s actual / sub-300ms perceived
- [ ] **Mascot anticipation layer** (1-above-mood simplified) + beat-coupled hip-bob — 400–1200ms perceived mask
- [ ] **Citation grammar in prompts** (prompt-only, no enforcement yet) — seeds corpus for live linter
- [ ] **Citation linter v1.1 — live mode** (strict response-level + ack-bank fallback) — anti-slop enforcement starts
- [ ] **djay Pro Mac overlay highlight** (12 elements + window tracker + overlay window) — viral demo anchor
- [ ] **Pyrekordbox XML one-shot import** — library source
- [ ] **10-SKU MIDI controller library** (already shipped Phase 9; add JSON-per-SKU + auto-detect polish)
- [ ] **Hard Tek detector tuning** against 7-10 reference tracks — Kaan ear-test gate
- [ ] **Recording browser + retention enforcement** — absorbed from v0.1.0 Phase 15
- [ ] **Apple Developer ID sign + notarize + DMG + SignPath Windows MSI + GitHub release matrix** — absorbed from v0.1.0 Phase 18
- [ ] **README full rewrite + branding + social assets** — absorbed from v0.1.0 Phase 19
- [ ] **Day-Zero Operations rehearsal** — absorbed from v0.1.0 Phase 20
- [ ] **Hallucination Verification Gate (Kaan DJ ear test)** — release gate
- [ ] **30-second viral demo film + 4 channel posts** — IG/Reddit/HN/Twitter
- [ ] **Pre-seeded FAQ + Kaan/Francesco answer rotation**

### Add After v2.0 (v2.1 polish / fast-follow)

Features explicitly out of v2.0 but on the immediate runway.

- [ ] **Predictive drop firing** — gated on Kaan ear-test with v2.0 baseline
- [ ] **4-layer mascot additive state machine** — full structural rewrite
- [ ] **Inline emote-tag vocabulary (15 tags)** — post text-channel-timing spike
- [ ] **Post-session debrief MVP** (chaptered + voiced TL;DR + 3 drills + clickable timeline)
- [ ] **Long-term DJ profile** — generated by debrief, injected into live
- [ ] **Cross-mode citation enforcement** — extend live linter to debrief + library + genre
- [ ] **Mixxx OSC bridge** behind `--enable-mixxx-osc` flag (or first-class if PR #14388 merges)
- [ ] **Library intelligence v1** (file watcher → embed → query, basic mode)
- [ ] **Library-aware drill cards** ("3 tracks from your library that fix this")

### Future Consideration (v2.2+)

Features that need infrastructure beyond v2.0/v2.1 ship.

- [ ] **Library intelligence v2** (Gemini Embedding 2 + sqlite-vec full pipeline, "what should I play next?" + "is this transition rough?" live queries)
- [ ] **Rekordbox / Serato overlay** via template matching
- [ ] **Genre expansion** — Techno → Tech House → DnB → Trance → UKG → Trap → Disco (~1 weekend per genre with v2.0 architecture)
- [ ] **VirtualDJ OSC bridge** (gated on Pro-user demand signal)
- [ ] **Windows overlay parity** (DPI + fullscreen Spaces)
- [ ] **Mascot procedural mouth from audio amplitude** (3 talk variants)
- [ ] **Genre auto-classifier via Gemini Embedding 2** (depends on library intelligence)
- [ ] **"/hatch" user-generated mascots** (v2.x stretch per memory)
- [ ] **Cross-session corpus for prompt-tuning** (slop-ratio-stripped sentence clustering)

---

## Feature Prioritization Matrix (v2.0 in-scope only)

| Feature | User Value | Implementation Cost | Priority |
|---|---|---|---|
| Generalized event detector v1 | HIGH (closes surface-level) | MEDIUM (~5d) | P1 |
| Pre-canned ack bank | HIGH (alive-feel mandatory) | LOW (~2d) | P1 |
| Prompt diet + caching | MEDIUM (TTFT win) | LOW (~2d) | P1 |
| Mascot anticipation layer | HIGH (perceived-latency mask) | LOW–MEDIUM (~3d) | P1 |
| Citation grammar in prompts | MEDIUM (seeds linter corpus) | LOW (~1d) | P1 |
| Citation linter (live mode) | HIGH (anti-slop enforcement) | MEDIUM (~3–5d) | P1 |
| djay Pro Mac overlay (12 elements) | HIGH (viral anchor) | MEDIUM–HIGH (~5–7d) | P1 |
| Pyrekordbox XML import | MEDIUM (library source) | LOW (~3d) | P1 |
| 10-SKU MIDI library polish | LOW–MEDIUM (already exists) | LOW (~2d) | P1 |
| Hard Tek detector tuning | MEDIUM (Kaan-specific, demo-critical) | MEDIUM (~3d) | P1 |
| Recording browser + retention | MEDIUM (UX surface) | MEDIUM (~2d) | P1 |
| Sign + notarize + DMG/MSI + release matrix | HIGH (zero-install conversion otherwise) | MEDIUM (~3d engineering + cert leads) | P1 |
| README + branding + social assets | HIGH (organic discovery) | MEDIUM (~3d content) | P1 |
| Day-Zero Operations rehearsal | HIGH (day-one retention) | MEDIUM (~3d) | P1 |
| Hallucination Verification Gate | HIGH (release gate) | MEDIUM (~3d Kaan-time) | P1 |
| 30s viral demo film | HIGH (engineering critical path) | MEDIUM (~2d post-feature-complete) | P1 |
| 4 channel posts + pre-seeded FAQ | HIGH (launch wave) | LOW–MEDIUM (~2d) | P1 |
| Cancel-and-refire | MEDIUM (in-bar reaction quality) | LOW (~2d) | P1–P2 |
| Mixxx OSC bridge (feature-flagged) | LOW–MEDIUM (Mixxx-only) | LOW (~2d) | P2 |

**Priority key:**
- **P1**: Must have for v2.0 ship — the demo film and the ear-test gate depend on these.
- **P2**: Should have, ship if schedule allows — Mixxx OSC behind flag.
- **P3**: Defer to v2.x — predictive firing, full 4-layer mascot, emote-tag vocab, debrief, library intelligence v2.

---

## Sources

### v2-bucket research artifacts (primary, HIGH confidence)

- [`v2-buckets/SYNTHESIS.md`](v2-buckets/SYNTHESIS.md) — integration layer + 5 strategic calls + priority matrix
- [`v2-buckets/A-latency.md`](v2-buckets/A-latency.md) (incl. `A-followup-1-cancel-and-caching` content) — latency engineering, `interrupt(force=True)` empirical verification, prompt caching 1024-token floor
- [`v2-buckets/B-industry-integrations.md`](v2-buckets/B-industry-integrations.md) — per-platform tractability matrix, ProDJ Link demotion, MIDI as universal layer
- [`v2-buckets/B-followup-1-v11-integration-spec.md`](v2-buckets/B-followup-1-v11-integration-spec.md) — MixxxBus 190-LOC spec, Pyrekordbox XML schema, 10-SKU JSON layout, Sync note 0x58 vs 0x60
- [`v2-buckets/C-ui-overlay.md`](v2-buckets/C-ui-overlay.md) — djay overlay hybrid approach, element vocabulary, Tauri #8329 mitigation, 30s storyboard
- [`v2-buckets/D-mascot-emotion.md`](v2-buckets/D-mascot-emotion.md) — 4-layer architecture, anticipation recipe, emote tag vocab, Mixamo blendshape constraint, latency-budget cover-up
- [`v2-buckets/E-debrief-pedagogy.md`](v2-buckets/E-debrief-pedagogy.md) — DJ teaching pedagogy synthesis, debrief UX patterns (Strava + Whoop + Synthesia + iZotope), profile architecture rejecting mem0, anti-slop tone
- [`v2-buckets/E-followup-1-citation-linter.md`](v2-buckets/E-followup-1-citation-linter.md) — citation grammar EBNF, regex enforcement, Python `CitationLinter` class, per-mode prompt templates, telemetry surface
- [`v2-buckets/F-library-intelligence.md`](v2-buckets/F-library-intelligence.md) — Gemini Embedding 2 audio cap (80s empirical), sqlite-vec vs alternatives, Bravoh pipeline 80% portable, drop+breakdown chunk strategy, cost projection
- [`v2-buckets/G-genre-taxonomy.md`](v2-buckets/G-genre-taxonomy.md) — Per-genre event catalogs (Hard Tek + 6 others), phrase awareness, genre auto-classifier
- [`v2-buckets/G-followup-1-hard-tek-dsp.md`](v2-buckets/G-followup-1-hard-tek-dsp.md) — 8 Hard Tek detectors with DSP recipes + 10 reference tracks + tuning harness + per-genre dispatch architecture
- [`v2-buckets/synthesis-viral-demo.md`](v2-buckets/synthesis-viral-demo.md) — 30s storyboard table, three signature beats, 7-day engineering critical path, per-platform post angles, risk register

### Project state (already-shipped baseline)

- [`.planning/PROJECT.md`](../PROJECT.md) — v2.0 milestone definition, 12 target features
- [`.planning/STATE.md`](../STATE.md) — Phases 1–14 shipped, decisions locked, Phase 15+ remaining
- `cohost_v4.py` — canonical v4 baseline (POC reference per memory)

### Memory directives (constraints driving anti-features)

- `feedback_no_clap_use_gemini_embedding` — Gemini-only, no CLAP/MERT
- `project_phase_16_kaan_dj_testing` — Kaan's DJ ear, not formal harness
- `project_one_click_install_hard_req` — every dep choice rated green/yellow/red
- `feedback_no_scope_creep_clean_utility` — clean utility only, BYO-key forbidden
- `project_anti_slop_grounded_gemini_thesis` — central product principle
- `project_v0_1_0_rc1_open_bugs` — Phases 15–20 absorbed into v2.0

---

*Feature research for: vibemix v2.0 Research-Driven Ship milestone*
*Researched: 2026-05-14*
*Confidence: HIGH on category structure + complexity hints + dependencies; MEDIUM on predictive firing / emote-tag spike (both gated on near-term experiments)*
