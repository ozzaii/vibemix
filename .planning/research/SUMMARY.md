# Project Research Summary — vibemix v9.0 "Lesson One"

**Project:** vibemix (Bravoh's first OSS release — beginner DJ learning module)
**Domain:** Hardware-aware, library-grounded, AI-mentored interactive DJ pedagogy on a live-grounded co-host stack
**Researched:** 2026-05-27
**Confidence:** HIGH on the engineering spine (every file:line and dep is verified in-tree). MEDIUM on pedagogical thresholds + AI-tutor-tone-at-scale (Khanmigo/Duolingo are closest precedents but not DJ-specific). LOW only on long-tail firmware × OS combinatorics that don't bite until v9.0 Phase 9.X probe matrix runs.

> Mode: `gsd-autonomous fully` · all-opus · default-YES on scope · phase numbering continues from P88 → v9.0 starts at **P91**. Must be ADDITIVE — new `src/vibemix/learn/` subpackage; existing engines untouched; must NOT regress the rc1 bundle/launchd fixes.

> **THE iconic opening dialog (verbatim-locked, byte-equality test required):**
> User: *"Hello vibemix, what are you?"*
> vibemix: *"I'm the best DJ app in the world."*
> User: *"If you are the best, then who the fuck am I?"*
> vibemix: *"Oh bestie, don't worry. You know why? Because I'm the beginner module of vibemix. Let's go."*

---

## Executive Summary

v9.0 turns vibemix into the **AI beginner-DJ teaching module**: open the app, pick **Learn**, three progressive courses (Anatomy of a Deck · Transitions · Play Mode) walk a stranger through DJing with **THEIR specific MIDI controller mirrored on screen** as an interactive vector visualization, with the AI highlighting physical controls, narrating in a hand-authored tutor voice, and proving each EQ band audibly by pulling a track from **THEIR library** where that band is most prominent — so as they turn the knob, they HEAR the band swell.

The Learn surface is built **purely additively** on top of the v8.x engines (CLAP library, MIDI registry, EvidenceRegistry, MOOD_PERSONAS["teacher"] lens, IpcRouterBus on ws:8765, sounddevice multi-stream pattern) with exactly **ONE new Python dep** (`python-statemachine`, MIT pure-Python ~30 KB) and **ZERO new JS deps, ZERO new ws ports, ZERO new AI providers**. The 10 already-mapped controllers (Pioneer DDJ-FLX4/6/10/400/1000/SX3 · XDJ-RX3 · Numark Party Mix Live · Hercules Inpulse 300/500) all get CDJ-Whisper-styled inline SVG schematics with `<g data-control-id="eq_low_a">` hit regions, painted in ≤16 ms per highlight. The lesson runtime is server-authoritative (Python = state, TS = renderer + input ferry), mirroring how the live co-host already works.

The build spine is **8 phases (P91-P98)** with P91/P93 parallelizable: **P91** ships the controller renderer + MIDI-position mirror as a *standalone-verifiable artifact* (plug controller → see knob move on canvas in <50ms, no lessons yet — Kaan ear-pass available the moment this lands); **P92** wires the lesson runtime + AI highlight contract + 12 `ipc.learn.*` envelopes; **P93** (parallel with P92) builds the band-share exemplar engine + the one new `exemplar:` evidence source (mirrors v6 `recall:` exactly across 4 schema-mirror sites); **P94/P95/P96** ship the three courses in dependency order; **P97** locks the verbatim opening dialog + tone byte-equality + mode picker; **P98** is the live audit + Kaan ear-pass hand-off.

The acid test for every phase: *"Does this deliver a working slice of the BEGINNER module without adding a new AI provider, new ws port, new IPC envelope family beyond `learn.*`, new DSP library, or new community/multi-user surface? Does it NOT regress any of the 4 cardinal invariants or the rc1 bundle fix?"* If it doesn't pass, defer.

The **three milestone-blocking risks** are (1) **tutor tone** — the v9.0 equivalent of Invariant #2; lesson scripts are HAND-AUTHORED, AI adds only one grounded interjection per beat, and a second AI-slop blocklist (`check_no_tutor_slop.py`) extends the existing `check_no_ai_slop.py` to ≥20 tutor-tic tokens ("Great question!", "Today we'll be learning…", "Awesome!"); (2) **Course 3 citation grounding** — the tutor lens MUST NEVER predict a phrase boundary unless grounded on `[cue:<anchor_id>]` evidence (new evidence source added IF AND ONLY IF Course 3 demands count-ins; pinned by `test_no_speculative_phrase` BEFORE any Gemini wiring); and (3) **copyright posture** — stylized CDJ-Whisper schematic SVG with NO Pioneer logo, NO Pioneer orange, NO faceplate photo lift, plus disclaimer in app + repo (Mixxx-precedent nominative fair use path is well-trodden). Anti-creep is enforced by the explicit defer list (intermediate course · scratching · effects deep-dive · production · mobile · community · scraping moat · DAW surfaces · ProDJ Link as primary — all DEFERRED to v9.x or Bravoh).

---

## Reconciliation Decisions (the 14 axes the researchers diverged on)

Decisions are LOCKED — these are the inputs to REQUIREMENTS.md + ROADMAP.md.

### 1. PHASE COUNT — **8 phases (P91-P98)**

Architecture's 8-phase spine wins, harmonized with Stack's "ship-the-renderer-standalone-for-ear-pass-first" insight (P91 = renderer + MIDI mirror with NO lessons; gives Kaan a real artifact before any AI is wired). Pitfalls' 12 topics (PEDAGOGY · TONE · HARDWARE · RENDERER · EXEMPLAR · AUDIO · TUTOR_LENS · IPC · PERSISTENCE · A11Y · LATENCY · UAT · LEGAL) thread through P91-P98 as concerns, not separate phases.

**Phase ↔ concern matrix:**

| Phase | Topic concerns it addresses |
|-------|------------------------------|
| **P91 Renderer + MIDI Mirror** | RENDERER · LATENCY · HARDWARE · A11Y · IPC (midi_position only) |
| **P92 Lesson Runtime + Highlight Contract** | IPC (full 12 envelopes) · PERSISTENCE · TONE (system instruction lock) · cardinal invariant pins (#1, #4) |
| **P93 Exemplar Engine** | EXEMPLAR · AUDIO (`ExemplarPlayer`) · cardinal invariant pin (#2 — `exemplar:` schema-mirror) |
| **P94 Course 1 Anatomy** | PEDAGOGY · TONE (first 16 lessons hand-authored) |
| **P95 Course 2 Transitions** | PEDAGOGY · EXEMPLAR wiring · TONE (next 14 lessons) |
| **P96 Course 3 Play Mode** | TUTOR_LENS (`[cue:]` source if needed) · cardinal invariant pin (#3) · LATENCY · AUDIO (active-session guard) |
| **P97 Onboarding + Tone Lock + Mode Picker** | TONE (verbatim byte-equality test) · LEGAL (disclaimer copy) · UX |
| **P98 Live Audit + Ear-Pass Hand-Off** | UAT (Kaan ear-pass on all 36 lessons) · LEGAL (Francesco/lawyer sight-check) · BUNDLE-CHECK (rc1 regression) |

**Dependency graph:** `P91 → P92 → P94 → P95 → P96 → P97 → P98`, with `P91 → P93` running in parallel and `P93` feeding cite-grounding for `P95` and `P96`.

### 2. CONTROLLER SCOPE — **10-controller scope with FLX4 as canonical ear-pass golden; 9 non-FLX4 live-verify rides forward as KAAN-ACTION**

Kaan said "fully comprehensive" and "default-YES" — ship the renderer scope for all 10 controllers in v9.0. Lesson content is controller-agnostic (lesson references controls by `field` name — same identifier the SVG `data-control-id` uses and the same key in `midi/profiles/<id>.json`), so all 10 controllers run all 36 lessons automatically.

**The trade Kaan should know about:** Pitfalls argues for a 3-controller cap (FLX4 + Inpulse 300 + Party Mix Live) because hand-authoring 10 accurate SVGs is ~80-120 hours of vector work and per-controller live ear-pass is the only honest verification path. **The default-YES compromise:** ship all 10 SVG files; **FLX4 = the canonical ear-pass golden** (Kaan's own hardware); the other 9 get a CI-gated SVG↔profile parity test + the **live ear-pass for the other 9 rides forward as KAAN-ACTION** in P98 (`§LEARN-CONTROLLER-EAR` — 9 items, one per non-FLX4 SKU). Generic fallback always present (low-confidence detection → labeled-zone layout, not fake-realistic).

### 3. LESSON COUNT — **36 lessons (16 Course 1 + 14 Course 2 + 6 Course 3) with explicit defer list**

Default-YES per Kaan. Features cataloged the full 36; Pitfalls' 10-lesson cap is the v9.0 *MVP* floor, not the *ceiling*. Mitigation for Pitfalls' "30+ scripts is too many to ear-pass" concern: lesson scripts are HAND-AUTHORED (NOT LLM-generated); AI adds only one grounded interjection per beat; Kaan ear-passes per course (3 ear-pass sessions, not 36).

**v9.0 36-lesson manifest (REQ-ID prefix `LEARN-CURR-*`):**
- **Course 1 Anatomy** (16 lessons, REQ-CURR-1.01..1.16): Opening Dialog · Meet Your Controller · Channel Strip · Crossfader · Pitch Fader · Transport Buttons · Jog Wheel (nudge mode) · Headphone Cueing · Master/Booth/Headphone Volumes · Anatomy of a Song · Counting Bars · Spot Breakdown By Ear · Spot Breakdown By Eye (waveform) · **EQ-as-Tutor Demo (THE marquee/moat lesson)** · Load Two Tracks · Course 1 Recital.
- **Course 2 Transitions** (14 lessons, REQ-CURR-2.01..2.14): Beatmatching By Ear · Beatmatching With Sync · Long Blend · EQ Swap · Bassline Swap · Filter Fade · Echo-Out · Drop Swap · Loop Transition · Hot Cues & Memory Cues · Camelot Wheel · Phrase Matching · Diagnosing a Train Wreck · Course 2 Recital.
- **Course 3 Play Mode** (6 lessons, REQ-CURR-3.01..3.06): First 5-Minute Mix · First 15-Minute Set · Reading The Room · First 30-Minute Set (capstone) · Recovery Drills · DJ Profile Graduation.

### 4. IPC ENVELOPE COUNT — **12 envelopes in the `ipc.learn.*` namespace**

| # | Envelope `type` | Direction | Purpose |
|---|----------------|-----------|---------|
| 1 | `ipc.learn.start_course` | shell → sidecar | Begin a course; `{course_id, controller_id}` |
| 2 | `ipc.learn.start_lesson` | shell → sidecar | Skip into a specific lesson; `{lesson_id, level}` |
| 3 | `ipc.learn.complete_lesson` | bidirectional | User skip / system advance |
| 4 | `ipc.learn.lesson_loaded` | sidecar → shell | Lesson active; HUD metadata |
| 5 | `ipc.learn.highlight` | sidecar → shell | Glow a control + annotation + expected_action |
| 6 | `ipc.learn.midi_position` | sidecar → shell | 30Hz controller-position mirror |
| 7 | `ipc.learn.advance` | bidirectional | Tutor-confirms-MIDI OR user skip |
| 8 | `ipc.learn.ack` | shell → sidecar | User touched physical control or clicked SVG |
| 9 | `ipc.learn.tutor_speak` | sidecar → shell | Narration text + TTS marker + citations |
| 10 | `ipc.learn.exemplar_play` | sidecar → shell | Audio playback started |
| 11 | `ipc.learn.exemplar_stop` | sidecar → shell | Playback ended |
| 12 | `ipc.learn.progress_state` | bidirectional | Snapshot of courses + lessons completed |

All envelopes ride existing `127.0.0.1:8765` ws_bus (Invariant #4 preserved). All `additionalProperties: false`. Python dataclass mirrors land in `src/vibemix/ui_bus/learn_messages.py` (NEW). MANDATORY post-edit: `cd tauri/ui && npm run codegen:ipc`.

### 5. RENDERER TECHNOLOGY — **inline SVG with `<g data-control-id>` hit regions, in a separate `WebviewWindow`**

LOCKED. Renderer = inline SVG, Vite `?raw` import, 11 files at `tauri/ui/src/learn/controllers/<id>.svg.ts` (10 specific + 1 generic). Precedent: `tauri/ui/src/wizard/controllers/ddj-flx4.svg.ts`. CSS-variable swap for `--learn-highlight` is composited (60 fps guaranteed). ≤16 ms paint per frame. **NOT Canvas, NOT WebGL/Three.js.**

Window topology = separate `WebviewWindow` at `tauri/src-tauri/src/learn_window.rs` — mirror of `debrief_window.rs`. **SAME ws:8765 socket** (one-socket invariant preserved).

**Copyright posture:** stylized CDJ-Whisper schematic — NO Pioneer logo, NO Pioneer orange, NO faceplate photo lift. Authored from Pioneer's official hardware-diagram PDFs (factual control geometry only). Mixxx is GPL-2.0 so we CANNOT import their SVGs. Disclaimer copy in app + repo.

**Latency dual-path:** highlight overlay paints from 30Hz `ipc.learn.midi_position` push. If P91 CI measures >80 ms P95, introduce direct MIDI→Rust→Tauri-event path via `midir` for highlight-only.

### 6. PERSONA / LENS — **reuse `MOOD_PERSONAS["teacher"]` with course/lesson `system_instruction` addendum**

No new lens. `prompts/matrix.py:53-66` already ships `MOOD_PERSONAS["teacher"]`. v9.0 = `COURSE_FRAMES[course_id]` + `CURRICULUM[lesson_id].system_instruction_addendum` (≤200 chars) + `controller_frame` + the base tutor lens system instruction.

### 7. NEW EVIDENCE SOURCE — **`[exemplar:<track_id>]` LOCKED; `[cue:<anchor_id>]` CONDITIONAL in P96**

`exemplar:` is the primary new evidence source (mirrors v6 `[recall:]` EXACTLY across **4 schema-mirror sites** — atomic single-commit add):

1. `src/vibemix/state/evidence_registry.py:111` — add `"exemplar"` to `EVIDENCE_SOURCES`
2. `src/vibemix/state/evidence_registry.py:137` — add `|exemplar` to `_SOURCE_ALT` regex
3. `src/vibemix/prompts/matrix.py` (`CITATION_GRAMMAR_BLOCK`) — add `[exemplar:<track_id>]` form
4. `src/vibemix/agent/dj_cohost.py` (`_build_citation_strip`) — add `"exemplar"` to strip set

**Course 3 `[cue:<anchor_id>]`** added conditionally in P96 if predictive count-ins are needed; default-YES per Kaan = add it (identical 4-site mirror pattern).

### 8. AUDIO ROUTING — **dedicated `ExemplarPlayer`; PlaybackQueue reuse REJECTED**

`_audio_macos.open_voice_output(device_index, ...)` exposes per-call device index (verified at `_audio_macos.py:298-380`). **DO NOT reuse `PlaybackQueue`** (mono int16 + wired into mic-gating at `audio/buffers.py:195`).

`ExemplarPlayer` LOCKED in `src/vibemix/learn/audio_cue.py` (NEW). Own `sd.OutputStream` on user-picked headphone device. Stereo float32 @ track sample rate. Headphone device picker added to existing wizard. Default-safe -12 dB tutor playback (or -18 dB if master > -6 dBFS). BlackHole/Multi-Output Device setup = KAAN-ACTION wizard discharge. Course 3 active-session guard: NEVER play tutor exemplars while user is mid-set.

### 9. PROGRESS PERSISTENCE — **JSON at `~/.cache/vibemix/learn-progress.json`**

Atomic write (privacy-fixture-tested from v3.1). Schema-versioned. Corruption → nuke + emit fresh empty + one-line toast. NOT `memory.db` (violates raw-in/raw-out contract). NOT settings JSON (different cadence).

### 10. TONE / SLOP GATE — **verbatim opening dialog fixture-locked; `check_no_tutor_slop.py` v2 blocklist**

Four-part defense:
1. Verbatim opening dialog byte-equality test — fixture at `src/vibemix/learn/transcripts/course_1_anatomy/01_welcome.json`.
2. Hand-authored lesson scripts (NEVER LLM-generated on the fly). AI adds ONLY one grounded interjection per beat.
3. `scripts/launch/check_no_tutor_slop.py` (NEW, extends `check_no_ai_slop.py`) — ≥20 tutor-tic tokens.
4. System instruction lock — *"Do NOT compliment user actions. Do NOT summarize what just happened. Do NOT preview what's next. Do NOT close with an upbeat hook. State ONE grounded observation + ONE forward sentence the lesson script provided."*

Per-lesson tone audit = Kaan ear-pass on all 36 lessons in P98. **Gemini Flash only** for v9.0 (Codex tutor deferred to v9.x).

### 11. COURSE 3 CITATION GROUNDING — **`test_no_speculative_phrase` BEFORE Gemini integration**

Course 3 = second milestone-blocker. Order of operations in P96:
1. Land `tests/learn/test_no_speculative_phrase.py` FIRST (AST gate — no `numpy.fft` / `scipy.signal` / phrase-guessing primitives in `learn/`).
2. Land `tests/learn/test_course3_uses_existing_coach.py` (every tutor-narration built by `state/coach.py:AICoach.build_prompt`).
3. Run-time gate at `state/coach.py::evidence_line`: if `bpm_confidence < 0.8` OR `phrase_position_confidence < 0.7`, disable count-in language, downgrade to retrospective.
4. ONLY THEN wire tutor narration to Gemini.
5. Add `[cue:<anchor_id>]` evidence source via 4-site mirror.

### 12. ANTI-CREEP ACID TEST

**v9.0 acid test (LOCKED):**

> *"Does this phase deliver a working slice of the BEGINNER (level 1, all 10 mapped controllers, 36-lesson curriculum, library exemplar engine + packaged fallback, scripted curriculum with grounded AI interjections) module — WITHOUT adding a new AI provider, new ws port, new IPC envelope family beyond `learn.*`, new DSP library, new content beyond the 36 hand-authored lessons, or new community/multi-user feature surface? Does it NOT regress any of the 4 cardinal invariants or the rc1 bundle fix?"*

**EXPLICIT DEFER LIST (v9.x / Bravoh, NOT v9.0):**
- Intermediate / Pro courses → v9.x
- Scratching lessons → v9.x or never
- Effects deep-dive beyond filter → v9.x
- Production / DAW / sample-making → Bravoh
- Per-genre branches (wedding-DJ, techno-DJ, etc.) → v9.1+ (only after telemetry justifies)
- Stem isolation / mashups / live remixing → never on device
- Mobile app → never (CLAUDE.md platform constraint)
- Linux → never
- Web catalog → defer
- 1001Tracklists scraping moat → Bravoh
- Community-shared lessons / leaderboards / streaks / cohort mode → Bravoh
- Cross-device progress sync → Bravoh
- DAW surfaces / Push / Maschine integration → never
- ProDJ Link as primary source → keep deferred
- Hardware-free "Explore" mode for Course 1 → v9.1
- Photorealistic faceplate art → never (copyright + maintenance burden)
- Localization beyond English → v9.1
- Lesson sharing / Mixcloud-style export → v9.x
- Per-controller MIDI self-test auto-fix → v9.x

### 13. BUILD ORDER — final phase spine (P91-P98)

| Phase | Name | Goal | Hard deps | Est. plans | KAAN-ACTION % | Risk |
|-------|------|------|-----------|------------|---------------|------|
| **P91** | Controller Renderer + MIDI Mirror | Plug controller → see knob move <50ms. NO lessons yet. | rc1 ship landed | 3-4 | 10% | LOW |
| **P92** | Lesson Runtime + AI Highlight Contract | "Hello world" 1-step lesson. 4 cardinal-invariant pins land here. | P91 | 4-5 | 0% | MEDIUM |
| **P93** | Exemplar Engine + `[exemplar:]` Evidence Source | DSP-band engine + 4-site schema mirror. NO UI yet — just engine. | P91 (parallel with P92) | 3-4 | 10% | MEDIUM |
| **P94** | Course 1 — Anatomy (L1.01-L1.16) | Beginner completes anatomy walkthrough. Tone byte-equality test on opening dialog. | P92 | 4-5 | 30% | LOW-MEDIUM |
| **P95** | Course 2 — Transitions (L2.01-L2.14) | User learns 5 canonical transitions. Exemplar wiring throughout. | P93 + P94 | 5-6 | 30% | MEDIUM |
| **P96** | Course 3 — Play Mode (L3.01-L3.06) | Proactive tutor coach on real set. `test_no_speculative_phrase` BEFORE Gemini wiring. | P95 | 6-8 | 50% | HIGH |
| **P97** | Onboarding + Verbatim Tone Locks + Mode Picker | Seamless first-run. Mode picker on main window. | P94-P96 | 3-4 | 30% | LOW-MEDIUM |
| **P98** | Live Audit + Ear-Pass Hand-Off + rc1 Regression Smoke | Kaan-walk recording. v9.0-MILESTONE-AUDIT.md. rc1 standalone sidecar smoke MUST PASS unregressed. | P97 | 2-3 | 80% | LOW |

### 14. OPEN QUESTIONS / KAAN-ACTION

**BLOCKING (must resolve before v9.0 ships):**
- 🔴 **§LEARN-LEGAL-DISCLAIMER** — Francesco/lawyer sight-check on rendered controllers + disclaimer copy.
- 🔴 **§LEARN-EAR-COURSE-1/2/3** — Kaan ear-pass on all 36 lessons (3 sessions, one per course).
- 🔴 **§LEARN-CUE-DECISION (P96)** — Course 3 proactive count-ins (needs `[cue:]`) OR retrospective-only? Default-YES = count-ins.

**NON-BLOCKING (ride forward to KAAN-ACTION queue):**
- 🟡 **§LEARN-CONTROLLER-EAR** — Live-verify on 9 non-FLX4 controllers (FLX4 = canonical golden).
- 🟡 **§LEARN-AUDIO-ROUTING-WIZARD-DISCHARGE** — BlackHole/Multi-Output wizard for master+cue split.
- 🟡 **§LEARN-CLAP-FIRST-RUN-UX** — CLAP ONNX model first-run download UX.
- 🟡 **§LEARN-OVERNIGHT-DISCIPLINE** — One-page overnight-run handoff doc.
- 🟡 **§LEARN-LATENCY-CONTINGENCY** — If P91 measures >80 ms P95, Rust-direct MIDI→Tauri amendment.
- 🟡 **§LEARN-MK2-DETECTION** — Hercules Inpulse 300 vs 300 MK2 detection.
- 🟡 **§LEARN-FIRMWARE-VARIANTS** — DDJ-FLX4 v1.07 variant detection.
- 🟡 **§LEARN-OFFLINE-TONE-PATH** — Codex tutor parity deferred to v9.x.
- 🟡 **§LEARN-LOCALIZATION-IT-TR** — en-only v9.0; v9.1 drops `tr.py`/`it.py`.
- 🟡 **§LEARN-PEDAGOGY-INSTRUCTOR-REVIEW** — 36-lesson ordering past beginner-track DJ instructor.

---

## Key Findings

### Recommended Stack

ONE new Python dep (`python-statemachine`, MIT, pure-Python, ~30 KB, GREEN install impact). ZERO new JS deps, ZERO new ws ports, ZERO new IPC envelope families beyond `learn.*`, ZERO new AI providers. ~3-5 MB installer growth for band-exemplar audio fallback bundle.

- `python-statemachine ^3.1.2` (NEW): lesson runtime FSM
- Inline SVG with `<g data-control-id>`, Vite `?raw` import: 11 controller schematics
- Existing `mido` + `python-rtmidi` + `vibemix.midi.registry`
- Existing `sounddevice ^0.5.5` for `ExemplarPlayer`
- Existing Tauri 2.x shell, second `WebviewWindow`
- Existing `vibemix.audio.features.snapshot_features` band-share scalars
- Existing `vibemix.llm.model_router` (Gemini Flash via `resolve("standard")`)
- Existing CLAP ONNX library engine (decode path lifted to shared `audio/decode.py`)
- NOT essentia (AGPL), NOT librosa, NOT XState, NOT Mixxx SVGs (GPL-2.0)

### Expected Features

**36 hand-authored lessons across 3 progressive courses.** Closes canon-named foundations from Phil Morse Complete DJ Course / Crossfader / Pioneer rekordbox Tutorial Mode / DJ TechTools / Mixed In Key / Beatportal / DJ.studio.

**Differentiators that nobody ships:**
- **EQ-as-Tutor Demo (L1.14)** — load-bearing moat. AI plays YOUR library track where the band dominates, gates on YOUR knob via MIDI, citation-grounded `[exemplar:<track_id>]`. CC0 packaged fallback.
- **Hardware Mirror UI With Live Highlights** — 10 mapped controllers, sub-50 ms MIDI→canvas highlight.
- **Live Proactive Co-pilot (Course 3)** — pivots v8.x reactive co-host to PROACTIVE count-ins. Grounded on CueAnchor + phrase detector + `[cue:<anchor_id>]` — never invents.

### Architecture Approach

Learn is the **4th surface** (Co-host / Build-a-Set / Debrief / **Learn**). Strict additive seam. New `src/vibemix/learn/` subpackage owns lesson FSM + curriculum + highlight contract + exemplar finder; second `WebviewWindow` renders controller canvas. Course 3 reuses live coach + CueAnchor + phrase detection UNCHANGED.

**12 major components** (all file:line verified): `LearnRuntime`, `LearnState`, `Curriculum`, `HighlightEnvelope`, `ExemplarFinder`, `ExemplarPlayer`, `LessonProgress`, `TutorPrompts`, MIDI Matchers, Transcripts, `LearnRouter`, `LearnWindow`.

**Cardinal Invariant Bindings** (one named test per invariant):

| Invariant | Static pin | Dynamic pin |
|-----------|------------|-------------|
| #1 Single-writer | `tests/learn/test_runtime_invariants.py::test_musicstate_never_mutated_by_learn` | `::test_only_learnruntime_writes_learnstate` |
| #2 Citation grounding | `tests/learn/test_exemplar_citation_schema_mirror.py` | `tests/learn/test_exemplar_grounding_e2e.py` |
| #3 Trust the audio | `tests/learn/test_no_speculative_phrase.py` | `tests/learn/test_course3_uses_existing_coach.py` |
| #4 One socket | `tests/learn/test_no_new_ws_port.py` | `tests/learn/test_learn_rides_existing_bus.py` |
| Tone lock | `tests/learn/test_tutor_prompts_byte_equality.py` | — |
| IPC schema parity | `tests/learn/test_highlight_envelope_schema.py` | `scripts/check_ipc_schema.py` (existing) |
| SVG↔profile parity | `tauri/ui/tests/learn/test_svg_profile_parity.spec.ts` | — |
| Course 1 curriculum resolution | `tests/learn/test_course_1_curriculum_resolves.py` | — |

### Critical Pitfalls

Top 5 milestone-blocking:

1. **AI Tutor Tone (P1) — MILESTONE-BLOCKER.** Mitigation: hand-authored scripts + `check_no_tutor_slop.py` v2 + system-instruction lock + per-lesson Kaan ear-pass.
2. **Citation Grounding in Course 3 (P9) — MILESTONE-BLOCKER.** Mitigation: `test_no_speculative_phrase` lands BEFORE Gemini wiring + runtime confidence gates + new `[cue:]` evidence source.
3. **Copyright Posture (P5) — MILESTONE-BLOCKER, launch-suicide if missed.** Mitigation: stylized CDJ-Whisper schematic (NO Pioneer logo/orange/photo) + disclaimer copy + Mixxx-precedent + Francesco/lawyer sight-check.
4. **Exemplar Engine Reliability (P6) — anti-product if it lies.** Mitigation: DSP-band engine (NOT CLAP cosine — CLAP is semantic, not spectral) + compressed-kick guard (Pearson r > 0.8 → exclude) + honest-null + CC-BY packaged fallback.
5. **Audio Routing Setup (P7) — hardware-safety surface; can blow speakers.** Mitigation: probe + wizard + default-safe -12 dB tutor playback + NEVER play during active co-host session.

Plus: P3 hardware variation · P4 renderer accuracy · P8 latency · P10 lesson gating · P13 integration regression w/ mascot + rc1.

---

## Implications for Roadmap

**8 phases (P91-P98)** per §13. Each phase plan asserts the acid test (§12). Each phase has explicit cardinal-invariant pin coverage + KAAN-ACTION carry-forward per §14.

### Research Flags

Phases likely needing deeper research during planning:
- **P93** — compressed-kick guard threshold tuning, CC-BY exemplar bank sourcing, first-run CLAP download UX dependency
- **P96** — `[cue:<anchor_id>]` evidence source semantics, `bpm_confidence`/`phrase_position_confidence` threshold tuning, tutor narration cadence under live-coach `in_flight` competition
- **P97** — mode picker existing `tauri/ui/src/session/state.ts` extension shape verification

Phases with standard patterns (skip research-phase):
- **P91** — proven `debrief_window.rs` mirror pattern; SVG-with-data-attributes precedent
- **P92** — schema-mirror pattern proven (v6 `recall:`); `python-statemachine` straightforward
- **P94** — purely declarative content
- **P95** — content + exemplar wiring established by P93 + P94
- **P98** — canonical close pattern (4th milestone-close iteration)

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| **Stack** | **HIGH** | Every recommendation verified in-tree file:line or single MIT/pure-Python dep with verified version. |
| **Features** | **HIGH on canon, MEDIUM on AI-tutor tone, LOW on Course 3 surface** | 36 lessons back-referenced; AI-tutor canon is Khanmigo/Duolingo; Course 3 proactive co-pilot has NO shipped prior art (moat). |
| **Architecture** | **HIGH** | Every cited file:line verified. 4 cardinal-invariant bindings have named static + dynamic pins each. |
| **Pitfalls** | **HIGH on tone/copyright/audio-routing/hardware-variation/integration, MEDIUM on lesson-gating thresholds + Codex-vs-Gemini parity, LOW on long-tail firmware × OS combinatorics** | 17 pitfalls cross-referenced to 50+ external sources. |

**Overall:** HIGH on engineering spine and milestone shape; MEDIUM on tone-at-scale (mitigation: hand-authored + blocklist + per-course Kaan ear-pass).

### Gaps to Address

- Tone-at-scale across 36 hand-authored lessons (mitigated)
- Course 3 proactive co-pilot under live speculation pressure (mitigated by `test_no_speculative_phrase`)
- 9-controller non-FLX4 live-verify ear-pass (KAAN-ACTION rides forward)
- Hercules Inpulse 300 vs MK2 detection
- DDJ-FLX4 firmware variants (pre-1.07 vs 1.07)
- Compressed-kick guard threshold validation on Kaan's library
- CC-BY exemplar bank sourcing
- Mode picker `tauri/ui/src/session/state.ts` extension shape verification
- Tutor narration cadence under heavy live-coach `in_flight` competition
- i18n it+tr (v9.1)

---

*Research synthesized: 2026-05-27 by gsd-research-synthesizer (4 opus researchers → SUMMARY.md)*
*Ready for requirements writer + roadmapper: yes*
*v9.0 milestone starts at Phase 91. Acid test locked. Defer list explicit. KAAN-ACTION queue parked.*
