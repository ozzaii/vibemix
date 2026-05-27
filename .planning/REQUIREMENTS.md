# Requirements — v9.0 "Lesson One" (Beginner Learning Module)

> Beginner DJ teaching module. Each requirement is user-centric, atomic, testable. Phases continue from v8.2 (P83-P88) and post-v8.2 wire-ins (P89/P90) — v9.0 starts at **P91**.
>
> Source: `.planning/research/SUMMARY.md` (synthesis of 4 opus researchers — STACK / FEATURES / ARCHITECTURE / PITFALLS).
> Mode: `gsd-autonomous fully` · all-opus · default-YES on every scope question.
> Iconic opening dialog verbatim-locked (byte-equality fixture test) — see TONE-01.

## v9.0 Requirements

### TONE — release-gate slop discipline (v9.0's Invariant-#2 equivalent)

- [ ] **TONE-01**: A beginner opens vibemix → picks Learn → sees the verbatim 4-line iconic opening dialog ("Hello vibemix, what are you?" / "I'm the best DJ app in the world." / "If you are the best, then who the fuck am I?" / "Oh bestie, don't worry. You know why? Because I'm the beginner module of vibemix. Let's go.") — byte-equality test against `src/vibemix/learn/transcripts/course_1_anatomy/01_welcome.json` fixture, CI-red on any drift.
- [ ] **TONE-02**: Every one of the 36 lesson scripts is HAND-AUTHORED (committed to `src/vibemix/learn/transcripts/course_<N>/<lesson_id>.json`) and NEVER LLM-generated on-the-fly; static test (`tests/learn/test_scripts_are_fixtures.py`) confirms no live generative call writes a `tutor_speak` envelope's `text` field.
- [ ] **TONE-03**: A new AI-slop blocklist `scripts/launch/check_no_tutor_slop.py` (extends `check_no_ai_slop.py`) catches ≥20 tutor-tic tokens ("Great question!" / "Today we'll be learning…" / "Awesome!" / "You crushed it!" / "Let's dive in!" / "Don't worry, you'll get the hang of it" + 14 more); CI-gated; runs against ALL `learn/transcripts/**.json` AND runtime AI interjections.
- [ ] **TONE-04**: The tutor system instruction includes a hard lock forbidding the four learned moves: NO complimenting user actions · NO summarizing what just happened · NO previewing what's next · NO closing with an upbeat hook. State ONE grounded observation + ONE forward sentence the lesson script provided. Pinned by `tests/learn/test_tutor_system_instruction_lock.py`.

### RENDER — controller visualization + MIDI position mirror

- [x] **RENDER-01**: A DJ plugs their MIDI controller and sees a CDJ-Whisper-styled inline SVG schematic of that exact controller on screen within 2 seconds of plug-in — 10 supported (DDJ-FLX4 / FLX6 / FLX10 / 400 / 1000 / SX3 · XDJ-RX3 · Numark Party Mix Live · Hercules Inpulse 300 / 300-MK2 / 500) + 1 generic fallback (labeled-zone layout when fingerprint is low-confidence). Auto-detect via `mido.get_input_names()` + `midi/registry.find_mapping`.
- [x] **RENDER-02**: Every physical control (knob/fader/button/jog/cue pad) on the rendered SVG mirrors the controller's current position via incoming MIDI within ≤50 ms P95 latency, measured by `tauri/ui/tests/learn/highlight-latency.test.ts`. CI fails red on regression beyond 80 ms P95 (triggers `§LEARN-LATENCY-CONTINGENCY` Rust-direct amendment).
- [x] **RENDER-03**: Every rendered control has a `<g data-control-id="<field>">` hit region with ARIA `role="button"` + `aria-label` for accessibility (e.g. `aria-label="EQ-HI knob, deck A"`); keyboard navigation works for users browsing the curriculum without hardware.
- [ ] **RENDER-04**: An AI highlight glow paints on a rendered control within 16 ms of receiving the `ipc.learn.highlight` envelope, composited via CSS-variable swap (no full SVG re-render); pinned by `tauri/ui/tests/learn/highlight-paint.test.ts`.
- [x] **RENDER-05**: Highlights use a dual-channel cue (color + shape) so color-blind users (deuteranopia / protanopia / tritanopia) can distinguish active vs inactive — not amber-only; verified by `tauri/ui/tests/learn/test_a11y_highlight_dual_cue.spec.ts` colour-difference assertion.
- [x] **RENDER-06**: Every SVG controller file passes a bi-directional CI parity gate against its MIDI profile JSON (`tauri/ui/tests/learn/test_svg_profile_parity.spec.ts`): every `data-control-id` in the SVG resolves to a binding in `midi/profiles/<id>.json` AND every profile binding has a matching `<g>` group in the SVG. Stops schema drift across all 11 files.
- [x] **RENDER-07**: The Learn surface runs in a SEPARATE `WebviewWindow` (mirror of `tauri/src-tauri/src/debrief_window.rs` → new `tauri/src-tauri/src/learn_window.rs`); the user can `Cmd+Tab` between Learn and the deck; both share the SAME ws:8765 socket (one-socket invariant).
- [ ] **RENDER-08**: All 11 controller SVGs are stylized CDJ-Whisper schematics — NO Pioneer logo, NO Pioneer orange brand color, NO faceplate photo-lifts; authored from official hardware-diagram PDFs (factual control geometry only). Disclaimer copy ships in app footer + repo README. Test `tests/learn/test_disclaimer_present.py` verifies disclaimer text exists in both surfaces.

### LESSON — runtime + IPC + progress persistence

- [ ] **LESSON-01**: The Learn runtime drives lesson state via a deterministic state machine in `src/vibemix/learn/runtime.py` (using `python-statemachine` ^3.1.2 — ONE new MIT pure-Python dep, GREEN install impact); each lesson is one state with declarative entry/exit/transition predicates; integration test `tests/learn/test_runtime_invariants.py` confirms ZERO writes to `MusicState` from the `learn/` package (Invariant #1 binding).
- [ ] **LESSON-02**: Twelve new IPC envelopes in the `ipc.learn.*` namespace (start_course / start_lesson / complete_lesson / lesson_loaded / highlight / midi_position / advance / ack / tutor_speak / exemplar_play / exemplar_stop / progress_state) ride the existing `127.0.0.1:8765` ws_bus through `IpcRouterBus` (one-socket invariant preserved); all `additionalProperties: false`; pre-compiled ajv validator regenerated via `cd tauri/ui && npm run codegen:ipc`. Python dataclass mirrors land in `src/vibemix/ui_bus/learn_messages.py`. CI gate `tests/learn/test_no_new_ws_port.py` greps `learn/` for any `websockets.serve` (zero allowed).
- [ ] **LESSON-03**: Lesson progress persists between sessions in atomic JSON at `~/.cache/vibemix/learn-progress.json` — schema-versioned (`schema_version: 1`), corruption-recovery (JSONDecodeError → nuke + emit fresh empty + one-line toast); user can resume mid-course; pinned by `tests/learn/test_progress_persistence.py::test_corrupt_file_recovers_clean`. Reset CLI `vibemix learn reset` + "Reset Learn Progress" button in existing settings drawer.
- [ ] **LESSON-04**: Lesson advancement requires the user to perform the expected MIDI action (CC drop ≥30% of range OR button press matching `expected_action.control` + `direction`); a 3-strike progressive hint surface guides the user; an "I got it" override skip is always available (motor-impaired-safe — no time-pressure); anti-speedrun min-dwell ≥45s per lesson prevents click-through gaming.
- [ ] **LESSON-05**: The tutor persona reuses `MOOD_PERSONAS["teacher"]` from `prompts/matrix.py:53-66` (v8.1 LENS-03) — NO new lens. The lesson runtime composes `build_tutor_system_instruction(course_id, lesson_id, controller_id)` = `COURSE_FRAMES[course_id]` + `controller_frame` + `CURRICULUM[lesson_id].system_instruction_addendum` (≤200 chars) + base tutor lens system instruction.
- [ ] **LESSON-06**: All AI dialog flows through Gemini Flash via `vibemix.llm.model_router.resolve("standard")` (zero hardcoded model literals; CI grep-gated). Codex offline tutor parity deferred to v9.x (`§LEARN-OFFLINE-TONE-PATH`).

### EXEMPLAR — library-driven band exemplars + `[exemplar:]` evidence source

- [ ] **EXEMPLAR-01**: For each EQ band lesson (low/mid/high in Course 1 + transition demos in Course 2), the system picks the strongest-band track from the DJ's CLAP-embedded library by computing band-share scalars (`sub_share` / `low_share` / `mid_share` / `high_share` — primitives EXIST at `audio/features.py:27-90`) at ingest time and persisting in a new sqlite-vec band-share column via library store migration. Engine: `src/vibemix/learn/exemplar.py::ExemplarFinder` (NEW, pure-compute, dim-agnostic, offline-unit-testable on synthetic fixtures).
- [ ] **EXEMPLAR-02**: The exemplar engine uses a DSP-band ranker — NOT CLAP semantic cosine (CLAP is semantic, not spectral; would mislabel "uplifting trance" as high-band when it's actually mid+sub). Includes a compressed-kick guard: if Pearson r > 0.8 between a track's mid-band energy and sub-band energy, exclude as kick-sideband false-positive. Pinned by `tests/learn/test_exemplar_kick_guard.py`.
- [ ] **EXEMPLAR-03**: When the user's library is empty or below confidence threshold (≤3 tracks pass the band-share floor), the system falls back to a ~3-5 MB packaged CC-BY exemplar bank at `assets/learn/band_exemplars/{sub,low,mid,high}/*` (4 tracks, instrumental, no vocals, ≤60 s each) — honest-null reasoning surfaced as `"Your library doesn't have a great example of this — listen to this one we packaged"`. Empty-library path verified by `tests/learn/test_exemplar_packaged_fallback.py`.
- [ ] **EXEMPLAR-04**: Exemplar audio plays through a dedicated `src/vibemix/learn/audio_cue.py::ExemplarPlayer` (NEW) on a SECOND `sd.OutputStream` to a user-picked headphone device — NOT reusing `audio.buffers.PlaybackQueue` (which is mic-gated at `audio/buffers.py:195` and would mute the user during exemplar playback). Stereo float32 @ track sample rate via PyAV/FFmpeg decode. Default-safe playback gain: -12 dB (or -18 dB if master deck audio > -6 dBFS — defer until quiet). Device picker added to existing wizard; persists as `learn.headphone_device_index` on existing `ipc.settings.set` envelope.
- [ ] **EXEMPLAR-05**: AI claims about exemplar tracks resolve via a NEW `[exemplar:<track_id>]` evidence source — added atomically to the 4 schema-mirror sites in a single commit (mirrors v6 `[recall:]` precedent exactly): `state/evidence_registry.py:111` (`EVIDENCE_SOURCES` frozenset) · `state/evidence_registry.py:137` (`_SOURCE_ALT` regex) · `prompts/matrix.py` (`CITATION_GRAMMAR_BLOCK`) · `agent/dj_cohost.py` (`_build_citation_strip`). Pinned by `tests/learn/test_exemplar_citation_schema_mirror.py` (4-site lock test) + `tests/learn/test_exemplar_grounding_e2e.py` (fabricated `[exemplar:bogus]` strips whole turn — Invariant #2 binding).
- [ ] **EXEMPLAR-06**: Course 3 active-session guard: NEVER play tutor exemplar audio while the user is mid-set (`MusicState.audible_deck != none` AND `state.session_active`). Course 3 = verbal coaching only; exemplar playback restricted to "between sets" lessons. Pinned by `tests/learn/test_course3_no_exemplar_during_live.py`.

### CURR-1 — Course 1: Anatomy of a Deck (16 lessons)

- [ ] **CURR-1.01**: Opening Dialog — verbatim-locked iconic 4-line exchange (TONE-01 fixture). Lesson 1 of Course 1.
- [ ] **CURR-1.02**: Meet Your Controller — AI introduces the rendered controller by manufacturer + model + 3 most-used controls.
- [ ] **CURR-1.03**: Channel Strip — channel fader role; user moves deck A channel fader 0→max and back; advance on full sweep.
- [ ] **CURR-1.04**: Crossfader — center / left / right; user demonstrates each position.
- [ ] **CURR-1.05**: Pitch Fader — user shifts pitch ±4%; AI explains tempo as a percentage of BPM.
- [ ] **CURR-1.06**: Transport Buttons — play / cue / sync / load; user presses each in sequence.
- [ ] **CURR-1.07**: Jog Wheel (nudge mode only) — user nudges forward/back; AI explains scratch is a different art form (deferred to v9.x).
- [ ] **CURR-1.08**: Headphone Cueing — cue button + headphones cue mix knob; user pre-listens deck B while deck A plays.
- [ ] **CURR-1.09**: Master / Booth / Headphone Volumes — "don't touch the master fader" hygiene + red-zone clipping awareness.
- [ ] **CURR-1.10**: Anatomy of a Song — intro / breakdown / drop / outro on a real library track; AI annotates each section tied to playback.
- [ ] **CURR-1.11**: Counting Bars — AI counts 1-2-3-4 over playback; user counts along; AI listens for tap-tempo or beat-button consistency.
- [ ] **CURR-1.12**: Spot Breakdown By Ear — AI plays a track, user presses cue when they hear the breakdown.
- [ ] **CURR-1.13**: Spot Breakdown By Eye (waveform) — user identifies breakdown on the deck waveform.
- [ ] **CURR-1.14**: **EQ-as-Tutor Demo** (THE marquee/moat lesson) — for each EQ band (low/mid/high), AI plays a track from user's library where that band dominates (EXEMPLAR-01..05), user turns the EQ knob, hears the band swell live; cited `[exemplar:<track_id>]`.
- [ ] **CURR-1.15**: Load Two Tracks — user loads track to deck A and track to deck B using controller load buttons.
- [ ] **CURR-1.16**: Course 1 Recital — 5-prompt mixed gate (random subset of CURR-1.03..1.13 controls); user must perform each correctly to unlock Course 2.

### CURR-2 — Course 2: Transitions (14 lessons)

- [ ] **CURR-2.01**: Beatmatching By Ear (manual) — AI gates progression on user pitch-shifting deck B to match deck A's BPM within ±0.5%; canonical sync-OFF.
- [ ] **CURR-2.02**: Beatmatching With Sync — modern consensus side-by-side teaching (per Features research §FEATURES — DJ Shortee / Mixcloud / SpinStart / DJ Mentors agree sync IS a tool, not gatekeeping).
- [ ] **CURR-2.03**: Long Blend — 32-bar fade with crossfader; AI count-in at -8 bars.
- [ ] **CURR-2.04**: EQ Swap — bring up incoming deck mids + highs, kill outgoing deck mids + highs; reverse for sub-bass.
- [ ] **CURR-2.05**: Bassline / Kick Swap — kill outgoing deck low EQ, bring up incoming deck low EQ on the beat-1 of next phrase.
- [ ] **CURR-2.06**: Filter Fade — sweep filter HPF on outgoing deck through the transition.
- [ ] **CURR-2.07**: Echo-Out (the bail-out transition for beginners with no beatmatching ability — taught early as safety net per Features research).
- [ ] **CURR-2.08**: Drop Swap — cut outgoing deck on the drop of incoming deck.
- [ ] **CURR-2.09**: Loop Transition — loop outgoing deck 16 bars while incoming deck enters.
- [ ] **CURR-2.10**: Hot Cues & Memory Cues — pre-set cue points on a track in user's library; AI demonstrates entering on cue 2 (the breakdown). Fallback path for users without rekordbox-imported cues: "set your own cue in vibemix" UI add.
- [ ] **CURR-2.11**: Camelot Wheel — harmonic-key matching using existing `harmonics.py` Camelot table; AI walks user through finding compatible neighbors.
- [ ] **CURR-2.12**: Phrase Matching — align deck B's phrase start with deck A's phrase start; AI counts in.
- [ ] **CURR-2.13**: Diagnosing a Train Wreck — AI plays a deliberately misaligned mix; user identifies the issue (off-phrase, off-key, off-BPM).
- [ ] **CURR-2.14**: Course 2 Recital — user performs a 5-track 10-minute mix using ≥3 different transition types; unlocks Course 3.

### CURR-3 — Course 3: Play Mode (live coaching, 6 lessons)

- [ ] **CURR-3.01**: First 5-Minute Mix — user plays freely with proactive tutor lens active; AI suggests one move per minute, grounded.
- [ ] **CURR-3.02**: First 15-Minute Set — uses v8.2 Build-a-Set engine to prepare a sequenced pool; user plays the set with AI coaching.
- [ ] **CURR-3.03**: Reading The Room — AI walks user through reading energy curve mid-set + adjusting next track accordingly.
- [ ] **CURR-3.04**: First 30-Minute Set Capstone — proactive co-pilot mode through a full 30-minute set; AI gives count-ins ("breakdown in 16 beats — get ready") only when grounded on `[cue:<anchor_id>]` evidence.
- [ ] **CURR-3.05**: Recovery Drills — AI synthetically introduces a train-wreck during user's set (one drill: an unexpected key clash; another: a misaligned phrase); user practices the bail-out via echo-out / filter fade / cut.
- [ ] **CURR-3.06**: DJ Profile Graduation — user reviews their accumulated DJ-profile insights from the v8.1 long-term profile + lesson completion summary in the v2.1 debrief surface (port 8766).
- [ ] **CURR-3.07**: Course 3 proactive tutor lens — when active, the tutor narrates upcoming structure ("breakdown in 16 beats") IF AND ONLY IF grounded on `[cue:<anchor_id>]` evidence (NEW evidence source added via the 4-site mirror pattern à la EXEMPLAR-05); when `bpm_confidence < 0.8` OR `phrase_position_confidence < 0.7` OR `MusicState.next_phrase_at` is None, the tutor downgrades to retrospective-only narration ("that was a breakdown — see how the bass dropped out"). Pinned by `tests/learn/test_no_speculative_phrase.py` (AST gate landed BEFORE Gemini wiring) + `tests/learn/test_course3_uses_existing_coach.py` (every tutor-narration prompt built by `state/coach.py:AICoach.build_prompt`).

### ONBOARD — onboarding, hardware-aware, mode picker

- [ ] **ONBOARD-01**: A new user opens the app and sees a mode picker on the main window (Co-host / Learn / Build a Set / Debrief) — extending `tauri/ui/src/session/state.ts` with a `mode` enum; mode picker flips `data-active` IMMEDIATELY on click (CLAUDE.md optimistic-repaint rule), then settles on the round-trip `ipc.session.set_mode` ack.
- [ ] **ONBOARD-02**: First-launch hardware probe sniffs MIDI via `mido.get_input_names()` + `midi/registry.find_mapping(port_name)`; if a known controller is detected, render its SVG and announce by name ("I see your DDJ-FLX4 — let's go"); if unknown, fall back to the generic SVG with manual picker.
- [ ] **ONBOARD-03**: Hercules Inpulse 300 vs 300-MK2 (2023) detection — TWO profile files ship in v9.0 (`hercules_inpulse_300.json`, `hercules_inpulse_300_mk2.json`); first-run MIDI-signature probe picks by `iSerialNumber` (Pitfalls §P3 — DJUCED treats as different controllers with different MIDI maps). Live-verify ride forward as `§LEARN-MK2-DETECTION` KAAN-ACTION.
- [ ] **ONBOARD-04**: Headphone device picker added to existing wizard — user selects which output device hosts tutor exemplar playback (default = system output; advanced = BlackHole + Multi-Output Device routing path documented at `docs/audio-routing.md` as `§LEARN-AUDIO-ROUTING-WIZARD-DISCHARGE` KAAN-ACTION).
- [ ] **ONBOARD-05**: Lesson progress list UI in Learn window — each lesson shows a dot (empty/in-progress/completed); user can pick up where they left off OR replay any completed lesson; consumes `ipc.learn.progress_state`.
- [ ] **ONBOARD-06**: Empty-state copy ("no controller? plug one in") + keyboard-nav for users browsing the curriculum without hardware (hardware-free "Explore" mode for Course 1 anatomy DEFERRED to v9.1 per anti-creep acid test).
- [ ] **ONBOARD-07**: LEGAL disclaimer copy visible in app footer + repo README — *"Visual representation for instructional use. DDJ-FLX4, XDJ-RX3, etc. are trademarks of AlphaTheta / Pioneer DJ. Inpulse is a trademark of Hercules. Numark is a trademark of inMusic Brands. vibemix is not affiliated with or endorsed by these manufacturers."*

### AUDIT — milestone close-out + ear-pass + regression smoke

- [ ] **AUDIT-01**: A Kaan-walk recording (screencast + audio) captures the full 3-course run on real FLX4 hardware end-to-end; saved to `docs/learn/2026-XX-kaan-walk.webm`; one item per course (Course 1 anatomy / Course 2 transitions / Course 3 live coaching) — 3 sessions, ≥90 minutes total. Surfaced as `§LEARN-EAR-COURSE-1/2/3` KAAN-ACTION (cannot be self-verified — Kaan's ear is the gate).
- [ ] **AUDIT-02**: The v9.0 milestone audit doc `.planning/milestones/v9.0-MILESTONE-AUDIT.md` lands at P98 close — covers REQ-ID satisfaction matrix · 4 cardinal-invariant pin re-runs on real session recordings · KAAN-ACTION queue · pitfall coverage.
- [ ] **AUDIT-03**: Francesco / lawyer sight-check on the rendered controllers + disclaimer copy + Mixxx-precedent nominative fair use posture — `§LEARN-LEGAL-DISCLAIMER` KAAN-ACTION; mandatory before public ship.
- [ ] **AUDIT-04**: rc1 standalone sidecar smoke MUST PASS unregressed — the in-flight v0.1.0-rc1 bundle/launchd fixes (`patch_livekit_agents_init.py` + sidecar.rs std::process + spec blocklist) confirmed still working post-v9.0 via `scripts/smoke/sidecar_bundle_smoke.sh` (or equivalent — write if missing). v9.0 must not block rc1.

## Future Requirements (deferred — v9.1+ vibemix milestones or Bravoh commercial)

### v9.1 Localization & Pedagogy expansions
- **LOCALE-IT-01**: Italian lesson copy at `src/vibemix/learn/copy/it.py` (en-only ships v9.0)
- **LOCALE-TR-01**: Turkish lesson copy at `src/vibemix/learn/copy/tr.py`
- **PEDAGOGY-INSTRUCTOR-REVIEW**: 36-lesson ordering reviewed by a beginner-track DJ instructor (Francesco contact / Kaan); recorded as `LESSONS-CANON-REVIEWED.md`
- **EXPLORE-MODE**: Hardware-free "Explore" mode for Course 1 anatomy (keyboard-only) — defer until sign-up bounce telemetry justifies
- **TUTOR-CODEX-PARITY**: Codex offline tutor mode (Gemini-Flash-only in v9.0)

### v9.x Curriculum expansions
- Intermediate course (post-graduation from Course 3)
- Pro course (advanced techniques)
- Per-genre branches (wedding-DJ / techno-DJ / house-DJ / hip-hop-DJ) — only after telemetry justifies
- Effects deep-dive beyond filter (Beat-FX, color-FX, custom routing)
- Lesson sharing / Mixcloud-style export of completed sets
- Per-controller MIDI self-test auto-fix (auto-rebuild profile from observed CCs)

## Out of Scope (explicit — DEFER to Bravoh commercial / never in OSS vibemix)

| Feature | Reason |
|---------|--------|
| Scratching lessons | Separate art form; not table-stakes; deferred to v9.x or never |
| Production / DAW / sample-making | Bravoh's main product owns production |
| Stem isolation / mashups / live remixing | Server-side at Bravoh if at all; not on-device |
| Mobile app | CLAUDE.md platform constraint (macOS + Windows only) |
| Linux support | CLAUDE.md platform constraint |
| Web catalog of curriculum | In-app surface first; add web catalog if outreach shows demand |
| 1001Tracklists scraping moat | Commercial Bravoh work; not OSS |
| Community-shared lessons / leaderboards / streaks / cohort mode | Bravoh commercial |
| Cross-device progress sync | Bravoh commercial |
| DAW surfaces (Push / Maschine integration) | Out of vibemix scope |
| ProDJ Link as primary source | Laptop-only PRO DJ LINK proved dead (project memory) — kept deferred |
| Photorealistic faceplate art | Copyright risk + maintenance burden (Pitfalls P5); Mixxx-precedent stylized only |
| New AI provider | Gemini Flash + local Codex only — no new providers |
| New ws port | Invariant #4 one-socket — `learn.*` rides existing `:8765` |
| New MIR library / DSP framework | essentia AGPL excluded; librosa unnecessary; scipy/torch/Pinecone/pgvector out |
| Mem0 / managed memory frameworks | Rejected; lesson progress uses local JSON |
| `MusicState` writes from `learn/` | Invariant #1 — `LearnState` private to `learn/` |

## Traceability
> Each v9.0 REQ-ID maps to exactly one phase (100% coverage, no orphans, no duplicates). Phases continue from v8.2 (P83-P88) and post-v8.2 wire-ins (P89/P90) — start at **P91**, no reset.

| Requirement | Phase | Status |
|-------------|-------|--------|
| TONE-01 | Phase 94 — Course 1 Anatomy (fixture lands with L1.01) | Pending |
| TONE-02 | Phase 92 — Lesson Runtime (no-LLM-write static gate) | Pending |
| TONE-03 | Phase 94 — Course 1 Anatomy (tutor-slop blocklist) | Pending |
| TONE-04 | Phase 92 — Lesson Runtime (system instruction lock) | Pending |
| RENDER-01 | Phase 91 — Controller Renderer + MIDI Mirror | Complete |
| RENDER-02 | Phase 91 — Controller Renderer + MIDI Mirror | Complete |
| RENDER-03 | Phase 91 — Controller Renderer + MIDI Mirror | Complete |
| RENDER-04 | Phase 92 — Lesson Runtime + Highlight Contract | Pending |
| RENDER-05 | Phase 91 — Controller Renderer + MIDI Mirror | Complete |
| RENDER-06 | Phase 91 — Controller Renderer + MIDI Mirror | Complete |
| RENDER-07 | Phase 91 — Controller Renderer + MIDI Mirror | Complete |
| RENDER-08 | Phase 97 — Onboarding + Tone Locks + Mode Picker (disclaimer copy) | Pending |
| LESSON-01 | Phase 92 — Lesson Runtime + Highlight Contract | Pending |
| LESSON-02 | Phase 92 — Lesson Runtime + Highlight Contract | Pending |
| LESSON-03 | Phase 92 — Lesson Runtime + Highlight Contract | Pending |
| LESSON-04 | Phase 92 — Lesson Runtime + Highlight Contract | Pending |
| LESSON-05 | Phase 92 — Lesson Runtime + Highlight Contract | Pending |
| LESSON-06 | Phase 92 — Lesson Runtime + Highlight Contract | Pending |
| EXEMPLAR-01 | Phase 93 — Exemplar Engine + `[exemplar:]` Evidence Source | Pending |
| EXEMPLAR-02 | Phase 93 — Exemplar Engine + `[exemplar:]` Evidence Source | Pending |
| EXEMPLAR-03 | Phase 93 — Exemplar Engine + `[exemplar:]` Evidence Source | Pending |
| EXEMPLAR-04 | Phase 93 — Exemplar Engine + `[exemplar:]` Evidence Source | Pending |
| EXEMPLAR-05 | Phase 93 — Exemplar Engine + `[exemplar:]` Evidence Source | Pending |
| EXEMPLAR-06 | Phase 96 — Course 3 Play Mode (active-session guard) | Pending |
| CURR-1.01 .. 1.16 | Phase 94 — Course 1 Anatomy | Pending |
| CURR-2.01 .. 2.14 | Phase 95 — Course 2 Transitions | Pending |
| CURR-3.01 .. 3.07 | Phase 96 — Course 3 Play Mode | Pending |
| ONBOARD-01 | Phase 97 — Onboarding + Tone Locks + Mode Picker | Pending |
| ONBOARD-02 | Phase 97 — Onboarding + Tone Locks + Mode Picker | Pending |
| ONBOARD-03 | Phase 97 — Onboarding + Tone Locks + Mode Picker | Pending |
| ONBOARD-04 | Phase 97 — Onboarding + Tone Locks + Mode Picker | Pending |
| ONBOARD-05 | Phase 97 — Onboarding + Tone Locks + Mode Picker | Pending |
| ONBOARD-06 | Phase 97 — Onboarding + Tone Locks + Mode Picker | Pending |
| ONBOARD-07 | Phase 97 — Onboarding + Tone Locks + Mode Picker | Pending |
| AUDIT-01 | Phase 98 — Live Audit + Ear-Pass Hand-Off + rc1 Regression Smoke | Pending |
| AUDIT-02 | Phase 98 — Live Audit + Ear-Pass Hand-Off + rc1 Regression Smoke | Pending |
| AUDIT-03 | Phase 98 — Live Audit + Ear-Pass Hand-Off + rc1 Regression Smoke | Pending |
| AUDIT-04 | Phase 98 — Live Audit + Ear-Pass Hand-Off + rc1 Regression Smoke | Pending |

**Coverage:**
- v9.0 requirements: 71 total (4 TONE + 8 RENDER + 6 LESSON + 6 EXEMPLAR + 16 CURR-1 + 14 CURR-2 + 7 CURR-3 + 7 ONBOARD + 4 AUDIT)
- Mapped to phases: 71
- Unmapped: 0 ✓

**Dependency spine:** (P91 RENDER ∥ P93 EXEMPLAR after P91) → P92 LESSON RUNTIME (depends on P91) → P94 COURSE 1 (depends P92) → P95 COURSE 2 (depends P93 + P94) → P96 COURSE 3 (depends P95) → P97 ONBOARD (depends P94-P96) → P98 AUDIT (depends P97).

---
*Requirements defined: 2026-05-27*
*Last updated: 2026-05-27 after initial definition (v9.0 "Lesson One" — based on 4 opus researcher synthesis at `.planning/research/SUMMARY.md`)*

---

## Note on REQ-ID Count (added 2026-05-27 by gsd-roadmapper)

The `**Coverage**` block above text-says **71 total**, but the actual REQ-ID sum is **72** (4 TONE + 8 RENDER + 6 LESSON + 6 EXEMPLAR + 16 CURR-1 + 14 CURR-2 + 7 CURR-3 + 7 ONBOARD + 4 AUDIT = 72). Treating the **72** as authoritative for coverage purposes — the Traceability table maps all 72 with no orphans and no duplicates. The "71" in line 194 is a one-off transcription artifact; existing rows untouched.

ROADMAP.md v9.0 section quotes **72 REQ-IDs** to match the actual sum.
