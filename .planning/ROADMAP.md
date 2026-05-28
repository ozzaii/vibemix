# vibemix — Roadmap

**Project:** vibemix — AI DJ Co-Host
**Current work:** v9.0 "Lesson One" — IN PROGRESS (started 2026-05-27). Phases 91–98 turn vibemix into the AI teaching module beginner DJs have been waiting for (3 progressive courses · 10-controller real-time renderer · library-grounded exemplar engine · 36 hand-authored lessons · proactive Course 3 tutor lens). All-opus · `gsd-autonomous fully` · default-YES on every scope question.
**Last shipped:** v8.2 "Set Builder" — 2026-05-26 (audit PASSED; engine + agent + CLI + GUI shipped, UI-02 funded-key ear-pass parked as KAAN-ACTION). Prior: v8.1 "One Mind" — 2026-05-26.
**Open alongside:** v4.0 "SHIP" — engineering-complete (8/8), publish gated on the external Apple Dev + SignPath signature clock (NOT archived) — **v7.0's OSS-04 discharges §SHIP-V4 for real; v4.0 closes alongside when the real cut fires**. Also: **v0.1.0-rc1 ship work** (bundle/launchd fixes in flight; KAAN-ACTION ear-pass + signed-release decision parked — see `.planning/handoffs/2026-05-27-session-end.md`).

---

## Milestones

- ✅ **v0.1.0 MVP Foundation** — Phases 1–14 (shipped 2026-05-13) — see `.planning/milestones/v0.1.0/`
- ✅ **v2.0 Research-Driven Ship** — Phases 15–26 (shipped 2026-05-14, tech_debt accepted) — see `.planning/milestones/v2.0-ROADMAP.md`
- ✅ **v2.1 The Unified Cut** — Phases 27–39 (shipped 2026-05-16, tech_debt accepted) — see `.planning/milestones/v2.1-ROADMAP.md`
- ✅ **v3.0 Clean OSS Ship** — Phases 40–45 (shipped 2026-05-17, tech_debt accepted) — see `.planning/milestones/v3.0-ROADMAP.md`
- ✅ **v3.1 Distribution-Ready Pass** — Phases 46–50 (shipped 2026-05-18, tech_debt accepted) — see `.planning/milestones/v3.1-ROADMAP.md`
- 🟡 **v4.0 SHIP** — Phases 51–58 (engineering-complete 8/8, publish on signature clock — NOT archived; closes alongside v7.0 OSS-04) — see `.planning/milestones/v4.0-ROADMAP.md`
- ✅ **v5.0 The Useful Cut** — Phases 59–62 (shipped 2026-05-22, tech_debt accepted) — see `.planning/milestones/v5.0-ROADMAP.md`
- ✅ **v6.0 The Memory Turn** — Phases 63–66 (shipped 2026-05-23, tech_debt accepted) — see `.planning/milestones/v6.0-ROADMAP.md`
- ✅ **v7.0 Open House** — Phases 67–70 (shipped 2026-05-24, tech_debt accepted) — see `.planning/milestones/v7.0-ROADMAP.md`
- ✅ **v8.0 Proof & Polish** — Phases 71–76 (shipped 2026-05-25, tech_debt accepted) — *this file, below* · audit `.planning/v8.0-MILESTONE-AUDIT.md`
- ✅ **v8.1 One Mind** — Phases 77–82 (shipped 2026-05-26, audit PASSED; KAAN-ACTION human gates parked) — see `.planning/milestones/v8.1-ROADMAP.md` · audit `.planning/milestones/v8.1-MILESTONE-AUDIT.md` · charter `.planning/archive/2026-05-27-stale-one-mind-research/one-mind-charter.md`
- ✅ **v8.2 Set Builder** — Phases 83–88 (shipped 2026-05-26, audit PASSED; UI-02 funded-key ear-pass parked) — *this file, below* · audit `.planning/v8.2-MILESTONE-AUDIT.md` · status `.planning/phases/v8.2-STATUS.md`
- 🔵 **v9.0 Lesson One** — Phases 91–98 (in progress, started 2026-05-27) — *this file, below* · requirements `.planning/REQUIREMENTS.md` · research `.planning/research/{SUMMARY,STACK,FEATURES,ARCHITECTURE,PITFALLS}.md`

---

# v9.0 "Lesson One" — ▶ IN PROGRESS (started 2026-05-27)

This is the live v9.0 plan — eight phases (P91–P98) turning vibemix into the **AI teaching module beginner DJs have been waiting for**. Three progressive courses (Anatomy of a Deck · Transitions · Play Mode) walk a stranger through DJing with **their specific MIDI controller mirrored on screen** as a real-time interactive vector visualization. The AI highlights physical controls, narrates in a hand-authored tutor voice, and proves each EQ band audibly by pulling a track from **their library** where that band is most prominent — so as they turn the knob, they HEAR the band swell.

**Mode:** `gsd-autonomous fully` · all-opus · default-YES on every scope question. Phase numbering continues from P88 (P89/P90 = direct wire-ins) — v9.0 starts at **P91**, no reset.

**Iconic opening dialog (verbatim-locked, byte-equality test in P94):**

> user: "Hello vibemix, what are you?"
> vibemix: "I'm the best DJ app in the world."
> user: "If you are the best, then who the fuck am I?"
> vibemix: "Oh bestie, don't worry. You know why? Because I'm the beginner module of vibemix. Let's go."

**Anti-creep acid test (v9.0, locked):**

> *"Does this phase deliver a working slice of the BEGINNER (level 1, all 10 mapped controllers, 36-lesson curriculum, library exemplar engine + packaged fallback, scripted curriculum with grounded AI interjections) module — WITHOUT adding a new AI provider, new ws port, new IPC envelope family beyond `learn.*`, new DSP library, new content beyond the 36 hand-authored lessons, or new community/multi-user feature surface? Does it NOT regress any of the 4 cardinal invariants or the rc1 bundle fix?"*

**Hard constraints (locked, encoded in every phase):**

- **Reuse-first.** No new AI provider (Gemini Flash via `model_router.resolve("standard")` for tutor dialog; local Codex offline tutor deferred to v9.x). No new MIR libraries (essentia AGPL excluded; librosa unnecessary; scipy/torch/Pinecone/pgvector out). **Exactly ONE new Python dep:** `python-statemachine ^3.1.2` (MIT, pure-Python, ~30 KB wheel — GREEN install impact). **ZERO new JS deps.** No new ws ports — `learn.*` envelopes ride existing `127.0.0.1:8765` ws_bus through `IpcRouterBus` (Invariant #4 holds). No new IPC envelope family beyond `learn.*` (12 envelopes); MANDATORY `cd tauri/ui && npm run codegen:ipc` after every `messages.schema.json` edit (the ajv validator is pre-compiled — per `feedback_schema_edit_needs_codegen_ipc`).
- **All four cardinal invariants hold by ADDITIVE design.**
  - **#1 single-writer** — Lesson state lives in a private `LearnState` dataclass under `src/vibemix/learn/`, NOT in `MusicState`. Sole writer = `LearnRuntime`. Static AST gate `tests/learn/test_runtime_invariants.py::test_musicstate_never_mutated_by_learn` pins it in P92.
  - **#2 citation grounding** — ONE new evidence source: `[exemplar:<track_id>]` added atomically to 4 schema-mirror sites in a single commit (mirrors v6 `[recall:]` precedent: `state/evidence_registry.py:111` EVIDENCE_SOURCES · `:137` _SOURCE_ALT regex · `prompts/matrix.py` CITATION_GRAMMAR_BLOCK · `agent/dj_cohost.py` _build_citation_strip). Fabricated `[exemplar:bogus]` strips whole turn. Lands in P93.
  - **#3 trust the audio** — Course 3 tutor narration prediction (count-ins) requires `[cue:<anchor_id>]` evidence (CONDITIONAL: default-YES per Kaan = add via identical 4-site mirror in P96); confidence gates `bpm_confidence < 0.8` OR `phrase_position_confidence < 0.7` downgrade to retrospective-only. `tests/learn/test_no_speculative_phrase.py` AST gate lands in P96 **BEFORE** any Gemini wiring.
  - **#4 one socket** — every `learn.*` envelope rides `:8765`; `tests/learn/test_no_new_ws_port.py` static greps `learn/` for `websockets.serve` (zero allowed). Lands in P92.
- **Tone is the release gate.** "Real DJ friend in your ear, no AI slop" is doubly-load-bearing. Verbatim opening dialog fixture-locked (byte-equality test in P94). All 36 lesson scripts are HAND-AUTHORED (committed JSON at `src/vibemix/learn/transcripts/`), NEVER LLM-generated on-the-fly (static gate `tests/learn/test_scripts_are_fixtures.py` in P92). New `scripts/launch/check_no_tutor_slop.py` blocklist catches ≥20 tutor-tic tokens ("Great question!" / "Today we'll be learning…" / "Awesome!" / etc.) — CI-gated; runs against all `learn/transcripts/**.json` AND runtime AI interjections. System instruction lock forbids the four learned moves (compliment / summarize / preview / upbeat hook) — pinned by `tests/learn/test_tutor_system_instruction_lock.py`. All in P94.
- **Hardware-aware onboarding.** First launch sniffs MIDI (`mido.get_input_names()` + `midi/registry.find_mapping`); 10 supported controllers (Pioneer DDJ-FLX4/6/10/400/1000/SX3 · XDJ-RX3 · Numark Party Mix Live · Hercules Inpulse 300/300-MK2/500) + 1 generic fallback. Stylized CDJ-Whisper schematic SVGs (NO Pioneer logo, NO Pioneer orange, NO faceplate photo-lifts) — authored from official hardware-diagram PDFs, factual control geometry only. Mixxx-precedent nominative fair use posture. Disclaimer copy in app footer + repo README. **FLX4 = canonical ear-pass golden (Kaan's hardware); 9 non-FLX4 live-verify rides forward as `§LEARN-CONTROLLER-EAR` KAAN-ACTION.**
- **Accessibility.** Dual-channel cue (color + shape) so color-blind users (deuteranopia / protanopia / tritanopia) can distinguish — not amber-only. Keyboard-nav for users without hardware. No time-pressure on lesson advancement (motor-impaired-safe). Visual phrase markers for hearing-impaired Course 3 use. Anti-speedrun min-dwell ≥45s + "I got it" override always available.
- **Honest green.** Every `learn/` engine module offline-unit-testable (lesson state machine, exemplar finder, highlight serializer, MIDI matchers). The live-app verification gate (`cargo tauri dev` + `ui.log` `[vmx:click]/[vmx:ipc>]/[vmx:ipc<]/[vmx:error]`) is HARD per `feedback_verify_live_app_not_just_tests`. **The bundled-sidecar path (in-flight v0.1.0-rc1 fixes — `patch_livekit_agents_init.py` + `sidecar.rs` std::process + spec blocklist) MUST NOT regress; P98 runs `scripts/smoke/sidecar_bundle_smoke.sh` (or writes it).**
- **Apache-clean copyright posture** — stylized vector schematics, not Pioneer faceplate art; nominative fair use only. KAAN-ACTION `§LEARN-LEGAL-DISCLAIMER` Francesco/lawyer sight-check before public ship.
- **`gsd-autonomous fully`** — blockers (Kaan's ear-pass · physical hardware verification · controller-renderer aesthetic sign-off · legal sight-check · cue-decision) ride forward to KAAN-ACTION; only the privacy hard rule + destructive risk pause.

**Charter + research (consumed):** `.planning/PROJECT.md` § Current Milestone · `.planning/research/SUMMARY.md` (14-axis synthesis from 4 opus researchers) · `.planning/research/{STACK,FEATURES,ARCHITECTURE,PITFALLS}.md` · `.planning/REQUIREMENTS.md` (72 v9.0 REQ-IDs).

**EXPLICIT DEFER LIST (v9.x / Bravoh, NOT v9.0 — quoted from SUMMARY §12):** Intermediate / Pro courses → v9.x · Scratching lessons → v9.x or never · Effects deep-dive beyond filter → v9.x · Production / DAW / sample-making → Bravoh · Per-genre branches (wedding-DJ, techno-DJ, etc.) → v9.1+ (only after telemetry justifies) · Stem isolation / mashups / live remixing → never on device · Mobile app → never (CLAUDE.md platform constraint) · Linux → never · Web catalog → defer · 1001Tracklists scraping moat → Bravoh · Community-shared lessons / leaderboards / streaks / cohort mode → Bravoh · Cross-device progress sync → Bravoh · DAW surfaces / Push / Maschine integration → never · ProDJ Link as primary source → keep deferred · Hardware-free "Explore" mode for Course 1 → v9.1 · Photorealistic faceplate art → never (copyright + maintenance burden) · Localization beyond English → v9.1 · Lesson sharing / Mixcloud-style export → v9.x · Per-controller MIDI self-test auto-fix → v9.x.

**Empirical grounding:** v9.0 lessons backed by canon (Phil Morse "Rock The Dancefloor" / Crossfader Complete DJ Course / Pioneer rekordbox Tutorial Mode / DJ TechTools phrasing 101 / Mixed In Key Camelot / Beatport "10 Lessons" / ClubReady DJ School / DJ.studio 16 transitions); AI-tutor tone canon = Khanmigo / Duolingo Max (both flagged for "scripted dialog" failure mode — mitigation = hand-authored scripts + slop blocklist v2 + per-course Kaan ear-pass).

## Phases

- [ ] **Phase 91: Controller Renderer + MIDI Mirror** — Plug controller → see knob move on canvas in <50ms (P95). Standalone-verifiable; NO lessons yet — Kaan ear-pass available the moment this lands.
- [ ] **Phase 92: Lesson Runtime + AI Highlight Contract** — "Hello world" 1-step lesson; the 4 cardinal-invariant pins land here; 12 `ipc.learn.*` envelopes wired.
- [ ] **Phase 93: Exemplar Engine + `[exemplar:]` Evidence Source** — DSP-band engine + 4-site schema mirror + `ExemplarPlayer` + packaged fallback. NO UI yet — just engine + CLI test.
- [ ] **Phase 94: Course 1 — Anatomy (L1.01–L1.16)** — Beginner completes anatomy walkthrough. Verbatim opening dialog byte-equality test + tutor-slop blocklist v2 + tutor system instruction lock land here.
- [ ] **Phase 95: Course 2 — Transitions (L2.01–L2.14)** — User learns 5 canonical transitions + harmonic mixing. Exemplar wiring throughout (depends P93 + P94).
- [ ] **Phase 96: Course 3 — Play Mode (L3.01–L3.06) + tutor lens proactive integration** — User plays real set with proactive tutor mode active. `test_no_speculative_phrase` AST gate lands BEFORE Gemini wiring. `[cue:<anchor_id>]` evidence source added via 4-site mirror.
- [ ] **Phase 97: Onboarding + Verbatim Tone Locks + Mode Picker** — Stranger opens app, picks Learn, sees "Oh bestie" opening, advances through L1.1 seamlessly. Mode picker on main window. Hercules MK2 detection. Disclaimer copy.
- [ ] **Phase 98: Live Audit + Ear-Pass Hand-Off + rc1 Regression Smoke** — Kaan-walk recording: full 3-course run on real FLX4 → `.planning/milestones/v9.0-MILESTONE-AUDIT.md`. rc1 standalone sidecar smoke MUST PASS unregressed.

| # | Phase | Goal | REQ-IDs | SC count |
|---|-------|------|---------|----------|
| 91 | Controller Renderer + MIDI Mirror | 7/7 | Complete   | 2026-05-27 |
| 92 | Lesson Runtime + AI Highlight Contract | 4/7 | In Progress|  |
| 93 | Exemplar Engine + `[exemplar:]` Evidence Source | DSP-band exemplar engine picks strongest-band track from user's library; falls back to packaged CC-BY bank when empty; plays through dedicated `ExemplarPlayer`; `[exemplar:<id>]` resolves via 4-site mirror | EXEMPLAR-01, EXEMPLAR-02, EXEMPLAR-03, EXEMPLAR-04, EXEMPLAR-05 (5) | 4 |
| 94 | Course 1 — Anatomy (L1.01–L1.16) | Beginner opens Learn, sees verbatim 4-line opening dialog, walks through 16 hand-authored anatomy lessons culminating in EQ-as-Tutor demo using library exemplars | TONE-01, TONE-03, CURR-1.01..1.16 (18) | 5 |
| 95 | Course 2 — Transitions (L2.01–L2.14) | User learns beatmatching (ear + sync) + 5 canonical transitions (long blend, EQ swap, kick swap, filter fade, echo-out, drop swap, loop) + harmonic mixing via Camelot wheel | CURR-2.01..2.14 (14) | 4 |
| 96 | Course 3 — Play Mode (L3.01–L3.07) + tutor lens proactive integration | User plays real 30-min set with proactive tutor mode active; count-ins grounded on `[cue:]` evidence ONLY; recovery drills + DJ profile graduation | EXEMPLAR-06, CURR-3.01..3.07 (8) | 5 |
| 97 | Onboarding + Verbatim Tone Locks + Mode Picker | Stranger opens app, picks Learn from mode picker, first-launch MIDI probe detects controller, sees verbatim opening, advances seamlessly; disclaimer copy ships | RENDER-08, ONBOARD-01..07 (8) | 4 |
| 98 | Live Audit + Ear-Pass Hand-Off + rc1 Regression Smoke | Kaan-walk recording captures full 3-course run on real FLX4; v9.0-MILESTONE-AUDIT.md lands; rc1 sidecar smoke confirmed unregressed | AUDIT-01, AUDIT-02, AUDIT-03, AUDIT-04 (4) | 4 |

**Dependency spine:** `P91 → P92 → P94 → P95 → P96 → P97 → P98`, with `P91 → P93` running in parallel and `P93` feeding cite-grounding for `P95` and `P96`.

## Phase Details

### Phase 91: Controller Renderer + MIDI Mirror
**Goal:** A DJ plugs their MIDI controller and sees a CDJ-Whisper-styled inline SVG schematic of that exact controller on screen within 2 seconds of plug-in (10 supported + 1 generic fallback), with every physical control mirroring its current position via incoming MIDI within ≤50 ms P95 latency. **Standalone-verifiable artifact: NO lessons yet** — Kaan ear-pass available the moment this lands.
**Depends on:** rc1 ship landed (parallelizable with P93). First v9.0 phase.
**Requirements:** RENDER-01, RENDER-02, RENDER-03, RENDER-05, RENDER-06, RENDER-07
**Success Criteria** (what must be TRUE):
  1. A DJ with any of the 10 supported controllers plugged in opens the Learn surface (new `WebviewWindow` via `tauri/src-tauri/src/learn_window.rs`, mirror of `debrief_window.rs`, on the SAME ws:8765 — Invariant #4 holds) and sees the correct CDJ-Whisper-styled inline SVG schematic of that controller (11 files at `tauri/ui/src/learn/controllers/<id>.svg.ts`, Vite `?raw` import) within 2 seconds; auto-detect via `mido.get_input_names()` + `midi/registry.find_mapping(port_name)` (already substring-matches `port_name_hints` from the 10 bundled profiles). Generic fallback labeled-zone layout when fingerprint confidence is low. **RENDER-01.**
  2. Every physical control (knob/fader/button/jog/cue pad) on the rendered SVG mirrors the controller's current MIDI position within ≤50 ms P95 latency — measured by `tauri/ui/tests/learn/highlight-latency.test.ts` in a synthetic harness; CI fails red on regression beyond 80 ms P95 (triggers `§LEARN-LATENCY-CONTINGENCY` Rust-direct `midir` amendment). CSS-variable swap for `--learn-highlight` is composited (60 fps guaranteed). **RENDER-02 + RENDER-04 painted-but-tested-in-P92.**
  3. Every rendered control has a `<g data-control-id="<field>">` hit region with ARIA `role="button"` + `aria-label` (e.g. `aria-label="EQ-HI knob, deck A"`) + a dual-channel cue (color + shape) so deuteranopia/protanopia/tritanopia users can distinguish active vs inactive — verified by `tauri/ui/tests/learn/test_a11y_highlight_dual_cue.spec.ts`; keyboard-nav works for hardware-free curriculum browsing. **RENDER-03 + RENDER-05.**
  4. Every SVG controller file passes a bi-directional CI parity gate (`tauri/ui/tests/learn/test_svg_profile_parity.spec.ts`): every `data-control-id` in the SVG resolves to a binding in `midi/profiles/<id>.json` AND every profile binding has a matching `<g>` group; stops schema drift across all 11 files. **RENDER-06 + RENDER-07.**

**Plans:** 7 plans
- [x] 91-01-PLAN.md — IPC schema + Vite/HTML/capability scaffolding + Python envelope dataclasses (Wave 1)
- [x] 91-02-PLAN.md — Test scaffolding (5 Python + 14 TS test stubs covering every per-task verification row) (Wave 1)
- [x] 91-03-PLAN.md — Python backend `learn/midi_mirror.py` + `ws_bus.py` + `__main__.py` wiring (Wave 2)
- [x] 91-04-PLAN.md — Rust shell `learn_window.rs` + `main.rs` registration (Wave 2)
- [x] 91-05-PLAN.md — Webview entry + FLX4 SVG + generic fallback + ARIA lookup + 5 components (Wave 3) — bfa01b80 → 71d218cd 2026-05-28; latency P95 **0.66ms** (target 50ms, red guardrail 80ms); §LEARN-LATENCY-CONTINGENCY parked
- [x] 91-06-PLAN.md — 9 remaining controller SVGs + extended `_aria-labels.ts` + `controller-stage.ts` allowlist (Wave 4)
- [x] 91-07-PLAN.md — Kaan FLX4 ear-pass checkpoint (live verification per `feedback_verify_live_app_not_just_tests`) (Wave 5)
**UI hint**: yes

### Phase 92: Lesson Runtime + AI Highlight Contract
**Goal:** A "hello world" 1-step lesson runs end-to-end: AI says "press play on deck A", the highlight glows on the rendered play button, the user presses their physical play button, and the lesson advances. The 4 cardinal-invariant pins (single-writer #1 + one-socket #4 + tone fixture lock + IPC schema lock) all land here. 12 `ipc.learn.*` envelopes wired through `IpcRouterBus`.
**Depends on:** Phase 91 (controller renderer + MIDI mirror).
**Requirements:** TONE-02, TONE-04, LESSON-01, LESSON-02, LESSON-03, LESSON-04, LESSON-05, LESSON-06, RENDER-04
**Success Criteria** (what must be TRUE):
  1. The Learn runtime drives lesson state via a deterministic `python-statemachine ^3.1.2` (ONE new MIT pure-Python dep — GREEN install impact) state machine in `src/vibemix/learn/runtime.py`; each lesson is one state with declarative entry/exit/transition predicates; **integration test `tests/learn/test_runtime_invariants.py` confirms ZERO writes to `MusicState` from the `learn/` package (Invariant #1 binding, static AST gate)**. **LESSON-01.**
  2. Twelve new IPC envelopes in the `ipc.learn.*` namespace (start_course / start_lesson / complete_lesson / lesson_loaded / highlight / midi_position / advance / ack / tutor_speak / exemplar_play / exemplar_stop / progress_state) ride existing `127.0.0.1:8765` ws_bus through `IpcRouterBus` — all `additionalProperties: false`; ajv validator regenerated via `cd tauri/ui && npm run codegen:ipc`; Python dataclass mirrors in `src/vibemix/ui_bus/learn_messages.py`; **`tests/learn/test_no_new_ws_port.py` static gate greps `learn/` for `websockets.serve` (zero allowed — Invariant #4 binding)**. Highlight paints in ≤16 ms of receiving `ipc.learn.highlight` (CSS-variable swap, no full SVG re-render) — pinned by `tauri/ui/tests/learn/highlight-paint.test.ts`. **LESSON-02 + RENDER-04.**
  3. Lesson advancement requires the user to perform the expected MIDI action (CC drop ≥30% of range OR button press matching `expected_action.control` + `direction`); a 3-strike progressive hint surface guides the user; an "I got it" override skip is always available (motor-impaired-safe — no time-pressure); anti-speedrun min-dwell ≥45s prevents click-through gaming. Lesson progress persists between sessions in atomic JSON at `~/.cache/vibemix/learn-progress.json` (schema-versioned; corruption → nuke + emit fresh empty + one-line toast); reset CLI `vibemix learn reset` + "Reset Learn Progress" button in existing settings drawer. **LESSON-03 + LESSON-04.**
  4. The tutor persona reuses `MOOD_PERSONAS["teacher"]` from `prompts/matrix.py:53-66` (v8.1 LENS-03 — NO new lens); the lesson runtime composes `build_tutor_system_instruction(course_id, lesson_id, controller_id)` = `COURSE_FRAMES[course_id]` + `controller_frame` + `CURRICULUM[lesson_id].system_instruction_addendum` (≤200 chars) + base tutor lens system instruction. All AI dialog flows through Gemini Flash via `vibemix.llm.model_router.resolve("standard")` (zero hardcoded model literals; CI grep-gated). **Tutor system instruction lock pinned by `tests/learn/test_tutor_system_instruction_lock.py` — forbids the four learned moves (NO complimenting · NO summarizing · NO previewing · NO upbeat hook closer)**. Static fixture gate `tests/learn/test_scripts_are_fixtures.py` confirms no live generative call writes a `tutor_speak` envelope's `text` field — all 36 scripts hand-authored JSON. **TONE-02 + TONE-04 + LESSON-05 + LESSON-06.**
**Plans:** 7 plans (1 of 7 SHIPPED)
- [x] 92-01-PLAN.md — Foundation: pyproject.toml + uv sync + learn_tutor route + messages.schema.json +11 envelopes + codegen:ipc + Python dataclasses + 5 count-parity test files (Wave 1) — SHIPPED 2026-05-28 commits 2214911f → fcdda017; count parity 77/77; codegen idempotent; LESSON-02 + LESSON-06 done
- [x] 92-02-PLAN.md — Test scaffolding: 10 Python + 8 TS test files (Nyquist-compliant; gated-skip pattern with named-Plan dependencies) (Wave 2)
- [x] 92-03-PLAN.md — Python backend core: state.py + runtime.py + curriculum.py + prompts.py + hello_world JSON fixture (Wave 2)
- [x] 92-04-PLAN.md — Progress persistence + `vibemix learn reset` CLI + __main__.main() LessonRuntime wiring (Wave 3)
- [ ] 92-05-PLAN.md — Lesson UI: hud.ts + tutor-dock.ts + skip-button.ts + applyHighlight on controller-stage + 11 envelope handlers in learn-window.ts (Wave 4)
- [ ] 92-06-PLAN.md — Settings drawer LearnGroup (Reset Learn Progress row + destructive confirm dialog) (Wave 4)
- [ ] 92-07-PLAN.md — Kaan FLX4 ear-pass checkpoint (live verification per feedback_verify_live_app_not_just_tests) (Wave 5)
**UI hint**: yes

### Phase 93: Exemplar Engine + `[exemplar:]` Evidence Source
**Goal:** DSP-band exemplar engine picks the strongest-band track from the DJ's CLAP-embedded library for each EQ lesson (low/mid/high), with a compressed-kick guard (Pearson r > 0.8 → exclude) and an honest-null fallback to a packaged ~3–5 MB CC-BY exemplar bank when the library is empty. Audio plays through a dedicated `ExemplarPlayer` on a second `sd.OutputStream` to a user-picked headphone device. The `[exemplar:<track_id>]` evidence source lands atomically across 4 schema-mirror sites. **NO UI yet — just engine + CLI test.**
**Depends on:** Phase 91 (parallelizable with Phase 92). Feeds cite-grounding to P95 + P96.
**Requirements:** EXEMPLAR-01, EXEMPLAR-02, EXEMPLAR-03, EXEMPLAR-04, EXEMPLAR-05
**Success Criteria** (what must be TRUE):
  1. For each EQ band (low/mid/high) the system picks the strongest-band track from the DJ's CLAP-embedded library by computing band-share scalars (`sub_share` / `low_share` / `mid_share` / `high_share`) — primitives EXIST at `audio/features.py:27-90`; engine extracted at ingest time and persisted via a new sqlite-vec band-share column migration. **Engine = DSP-band ranker, NOT CLAP semantic cosine** (CLAP is semantic, not spectral; would mislabel "uplifting trance" as high-band when actually mid+sub). Includes compressed-kick guard: if Pearson r > 0.8 between mid-band energy and sub-band energy, exclude as kick-sideband false-positive — pinned by `tests/learn/test_exemplar_kick_guard.py`. `src/vibemix/learn/exemplar.py::ExemplarFinder` is pure-compute, dim-agnostic, offline-unit-testable on synthetic fixtures. **EXEMPLAR-01 + EXEMPLAR-02.**
  2. When the user's library is empty or ≤3 tracks pass the band-share floor, the system falls back to a packaged ~3–5 MB CC-BY exemplar bank at `assets/learn/band_exemplars/{sub,low,mid,high}/*` (4 tracks, instrumental, no vocals, ≤60s each) — honest-null reasoning surfaced as *"Your library doesn't have a great example of this — listen to this one we packaged"*. Empty-library path verified by `tests/learn/test_exemplar_packaged_fallback.py`. **EXEMPLAR-03.**
  3. Exemplar audio plays through a dedicated `src/vibemix/learn/audio_cue.py::ExemplarPlayer` on a SECOND `sd.OutputStream` to a user-picked headphone device — NOT reusing `audio.buffers.PlaybackQueue` (which is mic-gated at `audio/buffers.py:195` and would mute the user). Stereo float32 @ track sample rate via PyAV/FFmpeg decode. Default-safe playback gain: -12 dB (or -18 dB if master deck audio > -6 dBFS — defer until quiet). Headphone device picker added to existing wizard; persists as `learn.headphone_device_index` on existing `ipc.settings.set` envelope. **EXEMPLAR-04.**
  4. AI claims about exemplar tracks resolve via a NEW `[exemplar:<track_id>]` evidence source — added atomically to the 4 schema-mirror sites in a single commit (mirrors v6 `[recall:]` precedent EXACTLY): `state/evidence_registry.py:111` (EVIDENCE_SOURCES frozenset) · `state/evidence_registry.py:137` (`_SOURCE_ALT` regex) · `prompts/matrix.py` (CITATION_GRAMMAR_BLOCK) · `agent/dj_cohost.py` (`_build_citation_strip`). Pinned by `tests/learn/test_exemplar_citation_schema_mirror.py` (4-site lock test) + `tests/learn/test_exemplar_grounding_e2e.py` (fabricated `[exemplar:bogus]` strips whole turn — **Invariant #2 binding**). **EXEMPLAR-05.**
**Plans**: TBD

### Phase 94: Course 1 — Anatomy (L1.01–L1.16)
**Goal:** A beginner opens vibemix, picks Learn, sees the verbatim 4-line iconic opening dialog ("Oh bestie…"), and walks through 16 hand-authored anatomy lessons culminating in the EQ-as-Tutor marquee demo using library exemplars. **The tone byte-equality test on opening dialog + tutor-slop blocklist v2 + tutor system instruction lock all land here.**
**Depends on:** Phase 92 (lesson runtime). Phase 93 needed for CURR-1.14 (EQ-as-Tutor demo); CURR-1.14 wires the exemplar engine.
**Requirements:** TONE-01, TONE-03, CURR-1.01..1.16
**Success Criteria** (what must be TRUE):
  1. A beginner opens vibemix → picks Learn → sees the verbatim 4-line iconic opening dialog ("Hello vibemix, what are you?" / "I'm the best DJ app in the world." / "If you are the best, then who the fuck am I?" / "Oh bestie, don't worry. You know why? Because I'm the beginner module of vibemix. Let's go.") — **byte-equality test against `src/vibemix/learn/transcripts/course_1_anatomy/01_welcome.json` fixture, CI-red on any drift** (`tests/learn/test_tutor_prompts_byte_equality.py`). **TONE-01 + CURR-1.01.**
  2. The user advances through 15 hand-authored anatomy lessons in canonical pedagogical order (Meet Your Controller · Channel Strip · Crossfader · Pitch Fader · Transport Buttons · Jog Wheel (nudge only) · Headphone Cueing · Master/Booth/Headphone Volumes + red-zone hygiene · Anatomy of a Song · Counting Bars · Spot Breakdown By Ear · Spot Breakdown By Eye (waveform) · Load Two Tracks); each lesson gates on actual MIDI events from the rendered controller. **CURR-1.02..1.13 + CURR-1.15.**
  3. **The EQ-as-Tutor Demo (L1.14, marquee/moat lesson) lands working end-to-end:** for each EQ band (low/mid/high), the AI plays a track from the user's library where that band dominates (via P93's `ExemplarFinder`); the user turns the EQ knob on their physical controller; they HEAR the band swell live; the AI's claim is cited `[exemplar:<track_id>]` (Invariant #2). Honest-null fallback to packaged bank when library is empty. **CURR-1.14.**
  4. Course 1 Recital (CURR-1.16) is a 5-prompt mixed gate (random subset of CURR-1.03..1.13 controls) — user must perform each correctly to unlock Course 2; replayable; honest grading. **CURR-1.16.**
  5. **Tone discipline gates land:** (a) NEW `scripts/launch/check_no_tutor_slop.py` extends `check_no_ai_slop.py` to catch ≥20 tutor-tic tokens ("Great question!" / "Today we'll be learning…" / "Awesome!" / "You crushed it!" / "Let's dive in!" / "Don't worry, you'll get the hang of it" + 14 more); CI-gated against all `learn/transcripts/**.json` AND runtime AI interjections. (b) Tutor system instruction includes hard lock forbidding the four learned moves (NO complimenting · NO summarizing · NO previewing · NO upbeat hook) — pinned by `tests/learn/test_tutor_system_instruction_lock.py`. **TONE-03.**
**Plans**: TBD
**UI hint**: yes

### Phase 95: Course 2 — Transitions (L2.01–L2.14)
**Goal:** The user learns 5 canonical transitions in canonical pedagogical order, beatmatching (ear + sync side-by-side per modern consensus), harmonic mixing via Camelot wheel, and a Course 2 Recital gating into Course 3. Exemplar wiring (P93) cited throughout transition demos.
**Depends on:** Phase 93 (exemplar engine + `[exemplar:]` evidence source) + Phase 94 (Course 1 must be passed before Course 2 unlocks).
**Requirements:** CURR-2.01..2.14
**Success Criteria** (what must be TRUE):
  1. Beatmatching taught both ways (CURR-2.01 manual by-ear ±0.5% BPM gate, sync-OFF; CURR-2.02 sync side-by-side per modern consensus: DJ Shortee / Mixcloud / SpinStart / DJ Mentors — sync IS a tool, not gatekeeping). AI mutes sync and narrates "this one is faster/slower" tempo deviation as the user nudges. **CURR-2.01 + CURR-2.02.**
  2. User performs all 5 canonical transitions on their controller in canonical order: Long Blend (CURR-2.03, 32-bar fade with crossfader, AI count-in at -8 bars) · EQ Swap (CURR-2.04) · Bassline/Kick Swap (CURR-2.05, kill outgoing low EQ + bring up incoming low EQ on beat-1 of next phrase) · Filter Fade (CURR-2.06) · Echo-Out (CURR-2.07, the bail-out for beginners with no beatmatching) · Drop Swap (CURR-2.08) · Loop Transition (CURR-2.09). Each performed live with AI count-in on two tracks from the user's library matched by Camelot + BPM ±6%. **CURR-2.03..2.09.**
  3. Hot Cues & Memory Cues (CURR-2.10) — AI demonstrates entering on cue 2 (the breakdown); fallback for users without rekordbox-imported cues = "set your own cue in vibemix" UI. Camelot Wheel (CURR-2.11) — harmonic-key matching using existing `harmonics.py` Camelot table; AI walks user through finding compatible neighbors. Phrase Matching (CURR-2.12) — align deck B's phrase start with deck A's phrase start, AI counts in. Diagnosing a Train Wreck (CURR-2.13) — AI plays deliberately misaligned mix; user identifies the issue (off-phrase / off-key / off-BPM). **CURR-2.10..2.13.**
  4. Course 2 Recital (CURR-2.14) — user performs a 5-track 10-minute mix using ≥3 different transition types; honest grading against the L2.x protocol; unlocks Course 3. **CURR-2.14.**
**Plans**: TBD

### Phase 96: Course 3 — Play Mode (L3.01–L3.06) + tutor lens proactive integration
**Goal:** The user plays a real 30-minute set with proactive tutor mode active; the AI gives count-ins ("breakdown in 16 beats — get ready to bring in track 2") **only when grounded on `[cue:<anchor_id>]` evidence**, downgrading to retrospective-only narration ("that was a breakdown — see how the bass dropped out") when confidence thresholds fail. **`test_no_speculative_phrase.py` AST gate lands BEFORE any Gemini wiring.** Active-session guard: NEVER play tutor exemplar audio while user is mid-set.
**Depends on:** Phase 95 (Course 2 must be passed). Reuses live coach (`agent/dj_cohost.py`) + CueAnchor + phrase detection UNCHANGED.
**Requirements:** EXEMPLAR-06, CURR-3.01..3.07
**Success Criteria** (what must be TRUE):
  1. **`test_no_speculative_phrase.py` AST gate lands FIRST** — static gate (no `numpy.fft` / `scipy.signal` / phrase-guessing primitives in `learn/`). THEN `test_course3_uses_existing_coach.py` lands (every tutor-narration prompt built by `state/coach.py:AICoach.build_prompt`). THEN runtime gate at `state/coach.py::evidence_line`: if `bpm_confidence < 0.8` OR `phrase_position_confidence < 0.7` OR `MusicState.next_phrase_at is None`, disable count-in language → downgrade to retrospective narration. **ONLY THEN wire tutor narration to Gemini.** New `[cue:<anchor_id>]` evidence source added via identical 4-site mirror pattern à la EXEMPLAR-05 (default-YES per Kaan = add it). Invariant #3 binding. **CURR-3.07 + Invariant #3 pin.**
  2. User plays a freely-chosen 5-minute mix (CURR-3.01) with proactive tutor lens active; AI suggests one grounded move per minute. Then a 15-minute set (CURR-3.02) using v8.2 Build-a-Set engine to prepare a sequenced pool; AI live-coaches each transition. Then Reading The Room (CURR-3.03) — AI walks user through reading energy curve mid-set + adjusting next-track choice. **CURR-3.01..3.03.**
  3. First 30-Minute Set Capstone (CURR-3.04) — proactive co-pilot through full 30-min set; count-ins only when `[cue:<anchor_id>]` evidence present, otherwise retrospective only. Session recorded; debrief surface (port 8766) auto-opens with cited critique. **CURR-3.04.**
  4. Recovery Drills (CURR-3.05) — AI synthetically introduces a train-wreck during user's set (drill 1: unexpected key clash; drill 2: misaligned phrase); user practices bail-out via echo-out / filter fade / cut; gate = recovery within 4 bars. DJ Profile Graduation (CURR-3.06) — user reviews their accumulated DJ-profile insights from v8.1 long-term profile + lesson completion summary in the v2.1 debrief surface. **CURR-3.05 + CURR-3.06.**
  5. **Active-session guard pinned:** NEVER play tutor exemplar audio while `MusicState.audible_deck != none` AND `state.session_active` — Course 3 = verbal coaching only; exemplar playback restricted to "between sets" lessons. Pinned by `tests/learn/test_course3_no_exemplar_during_live.py`. **EXEMPLAR-06.**
**Plans**: TBD

### Phase 97: Onboarding + Verbatim Tone Locks + Mode Picker
**Goal:** A stranger opens the app, picks Learn from a mode picker on the main window, first-launch MIDI probe detects their controller and announces it by name ("I see your DDJ-FLX4 — let's go"), they see the verbatim opening dialog and advance seamlessly through L1.1. Disclaimer copy ships. Hercules MK2 detection works. Headphone device picker in wizard. Lesson progress list UI.
**Depends on:** Phases 94 + 95 + 96 (all three courses must exist for mode picker to navigate into them).
**Requirements:** RENDER-08, ONBOARD-01..07
**Success Criteria** (what must be TRUE):
  1. A new user opens the app and sees a mode picker on the main window (Co-host / Learn / Build a Set / Debrief) — extending `tauri/ui/src/session/state.ts` with a `mode` enum; mode picker flips `data-active` IMMEDIATELY on click (CLAUDE.md optimistic-repaint rule), then settles on the round-trip `ipc.session.set_mode` ack. First-launch hardware probe sniffs MIDI via `mido.get_input_names()` + `midi/registry.find_mapping(port_name)`; if a known controller is detected, render its SVG and announce by name; if unknown, fall back to the generic SVG with manual picker. **ONBOARD-01 + ONBOARD-02.**
  2. Hercules Inpulse 300 vs 300-MK2 (2023) detection — TWO profile files ship (`hercules_inpulse_300.json`, `hercules_inpulse_300_mk2.json`); first-run MIDI-signature probe picks by `iSerialNumber` (Pitfalls §P3 — DJUCED treats as different controllers with different MIDI maps). Live-verify on real MK2 rides forward as `§LEARN-MK2-DETECTION` KAAN-ACTION. Headphone device picker added to existing wizard — user selects which output device hosts tutor exemplar playback (default = system output; advanced = BlackHole + Multi-Output Device routing path documented at `docs/audio-routing.md` as `§LEARN-AUDIO-ROUTING-WIZARD-DISCHARGE` KAAN-ACTION). **ONBOARD-03 + ONBOARD-04.**
  3. Lesson progress list UI in Learn window — each lesson shows a dot (empty/in-progress/completed); user can pick up where they left off OR replay any completed lesson; consumes `ipc.learn.progress_state`. Empty-state copy ("no controller? plug one in") + keyboard-nav for users browsing curriculum without hardware; hardware-free "Explore" mode for Course 1 anatomy DEFERRED to v9.1 per anti-creep acid test. **ONBOARD-05 + ONBOARD-06.**
  4. **All 11 controller SVGs are stylized CDJ-Whisper schematics** — NO Pioneer logo, NO Pioneer orange brand color, NO faceplate photo-lifts; authored from official hardware-diagram PDFs (factual control geometry only). LEGAL disclaimer copy visible in app footer + repo README: *"Visual representation for instructional use. DDJ-FLX4, XDJ-RX3, etc. are trademarks of AlphaTheta / Pioneer DJ. Inpulse is a trademark of Hercules. Numark is a trademark of inMusic Brands. vibemix is not affiliated with or endorsed by these manufacturers."* Test `tests/learn/test_disclaimer_present.py` verifies disclaimer text exists in both surfaces. **RENDER-08 + ONBOARD-07.**
**Plans**: TBD
**UI hint**: yes

### Phase 98: Live Audit + Ear-Pass Hand-Off + rc1 Regression Smoke
**Goal:** Kaan-walk recording captures the full 3-course run on real FLX4 hardware end-to-end. v9.0-MILESTONE-AUDIT.md lands. Francesco/lawyer sight-check on rendered controllers + disclaimer copy + Mixxx-precedent nominative fair use posture. **rc1 standalone sidecar smoke MUST PASS unregressed.** Three KAAN-ACTION ear-pass sessions (one per course) parked. Mostly KAAN-ACTION discharge (~80%).
**Depends on:** Phase 97 (onboarding must work for stranger walk-through).
**Requirements:** AUDIT-01, AUDIT-02, AUDIT-03, AUDIT-04
**Success Criteria** (what must be TRUE):
  1. A Kaan-walk recording (screencast + audio) captures the full 3-course run on real FLX4 hardware end-to-end; saved to `docs/learn/2026-XX-kaan-walk.webm`; one session per course (Course 1 anatomy / Course 2 transitions / Course 3 live coaching) — 3 sessions, ≥90 minutes total. Surfaced as `§LEARN-EAR-COURSE-1/2/3` KAAN-ACTION (cannot be self-verified — Kaan's ear is the gate). **AUDIT-01.**
  2. The v9.0 milestone audit doc `.planning/milestones/v9.0-MILESTONE-AUDIT.md` lands at P98 close — covers 72-REQ-ID satisfaction matrix · 4 cardinal-invariant pin re-runs on real session recordings · KAAN-ACTION queue · pitfall coverage (Pitfalls §P1–P17) · acid-test self-check per phase. **AUDIT-02.**
  3. Francesco / lawyer sight-check on the rendered controllers + disclaimer copy + Mixxx-precedent nominative fair use posture — `§LEARN-LEGAL-DISCLAIMER` KAAN-ACTION; mandatory before public ship. **AUDIT-03.**
  4. **rc1 standalone sidecar smoke MUST PASS unregressed** — the in-flight v0.1.0-rc1 bundle/launchd fixes (`patch_livekit_agents_init.py` + `sidecar.rs` std::process + spec blocklist) confirmed still working post-v9.0 via `scripts/smoke/sidecar_bundle_smoke.sh` (or equivalent — write if missing). v9.0 must not block rc1. Additionally: envelope namespace audit (mascot frame handler not broken by `learn.*` additions — `tauri/ui/tests/mascot/learn-envelope-doesnt-break-mascot.spec.ts`); standalone `vibemix-core --session` + `vibemix-core --wizard` launchd-spawn unregressed. **AUDIT-04.**
**Plans**: TBD

## Progress Table

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 91. Controller Renderer + MIDI Mirror | 5/7 | In progress | - |
| 92. Lesson Runtime + AI Highlight Contract | 0/? | Not started | - |
| 93. Exemplar Engine + `[exemplar:]` Evidence Source | 0/? | Not started | - |
| 94. Course 1 — Anatomy | 0/? | Not started | - |
| 95. Course 2 — Transitions | 0/? | Not started | - |
| 96. Course 3 — Play Mode + tutor lens proactive | 0/? | Not started | - |
| 97. Onboarding + Tone Locks + Mode Picker | 0/? | Not started | - |
| 98. Live Audit + Ear-Pass + rc1 Regression Smoke | 0/? | Not started | - |

## KAAN-ACTION Queue (v9.0 — surfaced + parked, never faked)

**BLOCKING (must resolve before v9.0 public ship):**
- 🔴 `§LEARN-LEGAL-DISCLAIMER` — Francesco/lawyer sight-check on rendered controllers + disclaimer copy.
- 🔴 `§LEARN-EAR-COURSE-1` — Kaan ear-pass on Course 1 (16 lessons) on real FLX4.
- 🔴 `§LEARN-EAR-COURSE-2` — Kaan ear-pass on Course 2 (14 lessons) on real FLX4.
- 🔴 `§LEARN-EAR-COURSE-3` — Kaan ear-pass on Course 3 (6 lessons) on real FLX4 mid-set.
- 🔴 `§LEARN-CUE-DECISION` (P96) — Course 3 proactive count-ins (needs `[cue:]`) OR retrospective-only? Default-YES = count-ins. Kaan ratifies during P96 planning.

**NON-BLOCKING (ride forward to KAAN-ACTION queue):**
- 🟡 `§LEARN-CONTROLLER-EAR` — Live-verify on 9 non-FLX4 controllers (FLX4 = canonical golden; other 9 stay SVG-shipped + CI-parity-gated, ear-pass deferred per controller).
- 🟡 `§LEARN-AUDIO-ROUTING-WIZARD-DISCHARGE` — BlackHole/Multi-Output Device wizard for master+cue split (`docs/audio-routing.md`).
- 🟡 `§LEARN-CLAP-FIRST-RUN-UX` — CLAP ONNX model first-run download UX (existing library Models row at `tauri/ui/library.html:170-176` is the load-bearing path — DO NOT bypass from Learn mode).
- 🟡 `§LEARN-OVERNIGHT-DISCIPLINE` — One-page overnight-run handoff doc (Pitfalls §P16).
- 🟡 `§LEARN-LATENCY-CONTINGENCY` — If P91 measures >80 ms P95, Rust-direct MIDI→Tauri amendment via `midir` crate (skip Python sidecar for highlight-only events).
- 🟡 `§LEARN-MK2-DETECTION` — Hercules Inpulse 300 vs 300-MK2 live-verify on real hardware.
- 🟡 `§LEARN-FIRMWARE-VARIANTS` — DDJ-FLX4 v1.07 variant detection (Beat-FX behavior change under rekordbox).
- 🟡 `§LEARN-OFFLINE-TONE-PATH` — Codex tutor parity deferred to v9.x.
- 🟡 `§LEARN-LOCALIZATION-IT-TR` — en-only v9.0; v9.1 drops `tr.py`/`it.py`.
- 🟡 `§LEARN-PEDAGOGY-INSTRUCTOR-REVIEW` — 36-lesson ordering past beginner-track DJ instructor (Francesco contact / Kaan).

---

# v8.2 "Set Builder" — ✅ SHIPPED 2026-05-26 (audit PASSED)

This section is the historical implementation plan for v8.2. Current source
has shipped the engine, agent, CLI, and GUI path; use
`.planning/v8.2-MILESTONE-AUDIT.md`, `.planning/phases/v8.2-STATUS.md`, and
`.planning/research/CODEX-full-product-sweep-map.md` for live status.

**Goal:** Wire the Viber agent engine into a DJ **set-prep co-host** — turn the flat-playlist curator into a tool that *discovers a pool from the DJ's OWN crate → sequences it on an energy curve with harmonically-valid transitions → exports one-click to Rekordbox → and explains why each transition works.* This is the library-local (Mode A) half of Francesco's "Vibe Mix Discovery & Sequencing" spec, built inside vibemix's locked constraints. The deep DJ value: *"give me a sequenced, harmonically-correct, energy-curved set from my own library, ready to load — and tell me why,"* the thing DJs spend hours on, grounded so it never invents a track.

**Anti-creep acid test (v8.2):** *"Does this turn the flat curator into a grounded, energy-curved, harmonically-valid, exportable set-prep flow over the DJ's OWN library — without a network catalog, an affiliate link, an extra set-builder dependency, or breaking a cardinal invariant?"* If not, defer (→ Bravoh commercial / a later vibemix milestone).

**Hard constraints (locked, encoded in every phase):**
- **Mode A library-local ONLY.** DEFER to Bravoh-commercial (explicit out-of-scope): public catalog (Beatport/Spotify/SoundCloud) + affiliate + purchase links (Modes B/C), Chromaprint/AcoustID fingerprint, XGBoost energy regressor, 1001Tracklists scraping moat, Serato/Engine/Traktor export (Rekordbox first).
- **Live co-host brain is separate and config-resolved; Viber set-prep/chat uses local Codex for the demo/test phase.** Library embeddings are local **CLAP ONNX** (no Gemini Embedding path); **sqlite-vec local**; no extra Set-Builder deps beyond the approved CLAP/onnxruntime/tokenizers stack (essentia = AGPL poison, NOT installed; librosa unnecessary; scipy/torch/Pinecone/pgvector out) — pure-compute over numpy + ffmpeg/PyAV + pyrekordbox(0.4.4, `--no-deps`).
- **All four cardinal invariants hold by ADDITIVE design.** The grounding gate (seen-set + library re-validation, Invariant #2) is UNCHANGED — every track_id the agent touches flows through `discover_pool`'s seen-set; the agent can never sequence/export a track discovery didn't surface.
- **New modules are dim-agnostic** — `discovery.py`/`sequencer.py` operate on current 512D CLAP vectors or any future D from `store._backend.load_all()`; they never hardcode D.
- **Honest green** — every engine module (`energy`/`discovery`/`sequencer`/`export_rekordbox`) is pure-compute, offline-unit-testable, no API key, no Gemini call. Live-app verification (`cargo tauri dev` + `ui.log`) is a **hard gate** for the UI phase (green vitest ≠ working app — `feedback_verify_live_app_not_just_tests`).
- **Shared-tree discipline:** check current ownership before touching CLAP/CueAnchor/metadata work, keep edits scoped, and do **NOT** refresh `.planning/codebase/orphans.csv` unless the orphan baseline is your explicit task.
- **`gsd-autonomous fully`** — blockers ride forward to KAAN-ACTION; only the privacy rule + destructive risk pause.

**Empirical grounding (research-confirmed, implementation-ready):** the energy v1 formula (7-feature linear combiner, **spectral flux 0.22** the strongest perceived-arousal term, crest-corrected loudness, fixed-window normalization — NOT corpus min-max — over busy frames only) is hardened in `vibe-mix-engine-research.md §A`; the sequencer is a fixed-length subset-select+order trellis solved by **beam search** (<100ms, M≈50, dominance-dedup pruning, relaxation ladder that TAGS never fabricates) — §B; the Rekordbox **`pyrekordbox.rbxml.RekordboxXml` WRITE path works under the `--no-deps` install** (pure-stdlib xml.etree, zero SQLCipher coupling — do NOT hand-roll ElementTree) — §C. Scope reconciliation: `vibe-mix-agent-engine-synthesis.md`. UI/IPC seams + dead-button inventory: `vibe-mix-ui-ipc-button-audit.md`.

## Phases

- [x] **Phase 83: ENERGY — Perceived-Dancefloor-Energy v1** — `library/energy.py` (reuse existing DSP + new spectral-flux term, genre-agnostic, content-hash cached) + `get_track_energy` tool.
- [x] **Phase 84: DISCOVER — Pool Building (library-local)** — `library/discovery.py` (intent centroid + hard filters + MMR) + `discover_pool` tool.
- [x] **Phase 85: SEQUENCE — Energy-Curved, Harmonically-Valid Ordering** — `library/sequencer.py` (curve presets + transition graph + beam search → 3-5 diverse paths, honest fit labels) + `sequence_set` tool.
- [x] **Phase 86: EXPORT — One-Click to Rekordbox** — `harmonics.to_classical` + `library/export_rekordbox.py` (RekordboxXml write path: order + key/BPM/genre + memory & hot cues + beatgrid) + `export_set` tool + `library export-set` CLI.
- [x] **Phase 87: AGENT — The Set-Prep Co-Host Flow** — Viber build-set backend (discover→sequence→explain each transition, mentor not black-box, grounded) + `library build-set` CLI, on the existing no-hang harness + shared persona/lens.
- [x] **Phase 88: UI — "Build a Set" Path** — Tauri "Build a Set" path (brief + curve picker → sequenced result + per-transition why + Export) in CDJ-Whisper aesthetic. UI-02 funded-key ear-pass remains KAAN-ACTION, not an engineering gap.

| # | Phase | Goal | REQ-IDs | SC count |
|---|-------|------|---------|----------|
| 83 | ENERGY — Perceived-Dancefloor-Energy v1 | A trustworthy 0-100 per-track energy score (genre-agnostic, cached) + tool | ENERGY-01, ENERGY-02, ENERGY-03 | 4 |
| 84 | DISCOVER — Pool Building | An intent-centroid + filtered + MMR-diversified candidate pool from the DJ's own crate + grounded tool | DISCOVER-01, DISCOVER-02, DISCOVER-03 | 4 |
| 85 | SEQUENCE — Energy-Curved Ordering | 3-5 diverse, energy-curved, harmonically-valid ordered sets with honest labels + tool | SEQUENCE-01, SEQUENCE-02, SEQUENCE-03 | 4 |
| 86 | EXPORT — One-Click to Rekordbox | A Rekordbox-importable XML (order + cues + beatgrid) + tool + CLI | EXPORT-01, EXPORT-02 | 4 |
| 87 | AGENT — Set-Prep Co-Host Flow | A NL-brief build-set flow that discovers→sequences→explains, grounded, no-hang | AGENT-01, AGENT-02 | 4 |
| 88 | UI — "Build a Set" Path | A live, no-dead-button "Build a Set" UI ending in a downloaded Rekordbox file | UI-01, UI-02 | 4 |

## Phase Details

### Phase 83: ENERGY — Perceived-Dancefloor-Energy v1
**Goal:** Give the DJ a trustworthy 0-100 perceived-dancefloor-energy score for any track in their library — one that reflects how hard a track *hits the floor*, not just how loud it is — computed offline from the local audio file, genre-agnostic, cached, and exposed to the agent. This is the energy axis the sequencer's curve will (optionally) ride; it is a pure-compute foundation, NON-BLOCKING for sequencing (the sequencer degrades to a BPM proxy when energy is absent).
**Depends on:** Nothing (first v8.2 phase). Pure-compute; reuses existing DSP primitives. Parallelizable with Phase 84 (ENERGY ∥ DISCOVER are independent).
**Requirements:** ENERGY-01, ENERGY-02, ENERGY-03
**Success Criteria** (what must be TRUE):
  1. A DJ gets a 0-100 perceived-energy score for any decodable track, computed offline from the local file by reusing the existing hand-rolled DSP (`cue_detect.decode_to_mono` + `audio/features` band-split/onset/`energy_curve` + `crest_factor` + `sub_share`) PLUS a new ~15-LOC spectral-flux term — the single strongest perceived-arousal predictor (ENERGY-01).
  2. The score is genre-agnostic — a pairwise-ranking + hypnotic-regression unit test proves a quiet hypnotic after-hours track does NOT read as low-energy and a loud-but-sparse intro does NOT read as high (fixed perceptual-window normalization with per-track clip + busy-frame aggregation, NOT corpus min-max; raw RMS demoted, flux/brightness/crest-corrected-loudness promoted) (ENERGY-02).
  3. Scores are cached by content hash so re-runs are free, and `get_track_energy(track_id)` is exposed as a grounded agent tool in `LibraryToolset` (inherited by gemini + codex/MCP + Telegram) that returns an honest `null` when a track has no decodable audio (ENERGY-03).
  4. The whole module is offline-unit-testable on synthetic fixtures — no API key, no Gemini call, no new dep; weights live as one-line-edit constants in `audio/constants.py`.
**Plans**: TBD

### Phase 84: DISCOVER — Pool Building (library-local)
**Goal:** Turn "a vibe + some reference tracks" into a focused, varied candidate pool drawn ONLY from the DJ's own library — ranked by coherence with a single computed intent, hard-filtered to what is actually mixable tonight, and diversity-re-ranked so it is a real pool not 50 near-identical tracks. Every track_id flows through the grounding seen-set, so nothing downstream can reference a track discovery didn't surface.
**Depends on:** Nothing structurally (operates on the existing `store` + `harmonics`). Parallelizable with Phase 83 (ENERGY ∥ DISCOVER independent). Consumed by Phase 85 (the pool) and Phase 87 (the agent).
**Requirements:** DISCOVER-01, DISCOVER-02, DISCOVER-03
**Success Criteria** (what must be TRUE):
  1. A DJ provides reference tracks and/or a text vibe prompt and gets a candidate pool from their OWN library, ranked by coherence with a single computed intent centroid (weighted multi-reference vector blend + α-blended CLAP text embedding) over the local mean-centered store (`store.search_centered`) (DISCOVER-01).
  2. The pool is hard-filtered to tonight's mixable set — BPM range, Camelot compatibility against the references (`harmonics.compatible`), usable duration, recently-played exclusion (local `played_ids`/memory, NOT Mem0), and explicit DJ excludes — then MMR-diversified (`score = λ·sim(intent) − (1−λ)·max_sim(selected)`) so the pool is varied (DISCOVER-02).
  3. `discover_pool(query|ref_track_ids, k, bpm_min/max, key, exclude_played_days, exclude_ids)` is exposed in `LibraryToolset`, and every returned track_id is recorded in the grounding seen-set (Cardinal Invariant #2) so the agent can never sequence a track the discovery step didn't surface (DISCOVER-03).
  4. The module is dim-agnostic (centroid/KNN/MMR operate on whatever D `load_all()` returns — current 512D CLAP or future D) and offline-unit-testable on fixture vectors (no API for the vector math; text-embed path mockable).
**Plans**: TBD

### Phase 85: SEQUENCE — Energy-Curved, Harmonically-Valid Ordering
**Goal:** Order a candidate pool into a full set that follows a chosen energy arc with technically-valid transitions throughout — and return several genuinely-different options with honest labels, so the DJ chooses, not the machine. This is the heart of the set-prep value: the harmonically-correct, energy-curved sequence DJs spend hours hand-building.
**Depends on:** Phase 84 (the candidate pool is the input) + optionally Phase 83 (energy gives curve fidelity; **degrades gracefully to a BPM proxy** when energy is absent — sequencing is never blocked on the DSP energy pass). Consumed by Phase 87 (the agent) and Phase 88 (the UI result list).
**Requirements:** SEQUENCE-01, SEQUENCE-02, SEQUENCE-03
**Success Criteria** (what must be TRUE):
  1. A DJ picks an energy-curve preset (opener / peak-time / after-hours / festival) or supplies a custom curve, and the pool is ordered into an N-slot set following that curve — the curve parameterized by normalized set-position (`np.interp` resample) so it works for any set length (SEQUENCE-01).
  2. Every transition is technically valid — harmonically compatible (Camelot same/±1/relative via `harmonics.compatible`) and BPM within ±6% — degrading gracefully when a track lacks key/BPM (NEVER dropped for missing metadata: `compatible` returns False on unknown, so the gate rejects only when BOTH are known and incompatible), and any relaxed transition (the widen-BPM→drop-cross-letter→unknown-key-bridge ladder) is TAGGED honestly ("BPM jump here"), never silently fabricated (SEQUENCE-02).
  3. `sequence_set(track_ids, curve_preset|curve_array, n_slots)` returns 3-5 ranked, Jaccard-diverse candidate sets (each ≥30% different tracks, or character-diverse weight presets) each with honest fit labels (energy fit, average coherence) for DJ optionality — exposed as a grounded `LibraryToolset` tool (ids must be in the seen-set) (SEQUENCE-03).
  4. The sequencer is pure-compute (beam search, <100ms at M≈50, dominance-dedup pruning), dim-agnostic, and offline-unit-testable (curve-follow, transition-validity, relaxation-tagging, diversity, dead-frontier honest-short-set). Cue-aware structure must consume landed `CueAnchor`/`cue_engine` data only when metadata is present and must degrade honestly when it is absent.
**Plans**: TBD

### Phase 86: EXPORT — One-Click to Rekordbox
**Goal:** Let the DJ get a sequenced set out of vibemix and into Rekordbox in one action — a self-contained importable XML that preserves track ORDER plus the rich per-track metadata and cues, so the set is ready to load. The single new validated write path, mirroring `create_playlist`'s grounding gate.
**Depends on:** Phase 85 conceptually (a sequenced set is the natural input) but the EXPORT module itself is independent of SEQUENCE internals — it serializes any ordered list of grounded track_ids; consumed by Phase 87 (the agent's final step).
**Requirements:** EXPORT-01, EXPORT-02
**Success Criteria** (what must be TRUE):
  1. A DJ exports a sequenced set to a Rekordbox-importable XML file in one action, and on import into Rekordbox the playlist appears with track ORDER preserved plus per-track key/BPM/genre/colour/rating and memory + hot cues + beatgrid — written via the verified `pyrekordbox.rbxml.RekordboxXml` write path (NOT hand-rolled ElementTree; dedup by Location before add_track; use SETTER for Rating byte-mapping) (EXPORT-01).
  2. Internal Camelot keys convert deterministically to classical notation for Rekordbox's `Tonality` field via a new `harmonics.to_classical(camelot) -> str|None` (24-entry inverse of `to_camelot`, honest-null on unknown, round-trip-testable), and export is exposed through an `export_set` agent tool + a `vibemix library export-set` CLI command (EXPORT-02).
  3. The hot-cue-COLOR gap (pyrekordbox 0.4.4 `PositionMark.ATTRIBS` has no RGB) is documented as "colours assigned by Rekordbox" rather than faked; the guaranteed win is ORDER (cues are a bonus, most valuable for not-yet-analyzed tracks).
  4. The writer is offline-unit-testable (build XML → parse back → assert order + Tonality + cues), adds ZERO new dep (pyrekordbox already pinned `--no-deps`), and does NOT mutate any existing Rekordbox database (file write only).
**Plans**: TBD

### Phase 87: AGENT — The Set-Prep Co-Host Flow
**Goal:** Wire the three engines behind one natural-language conversation — the DJ asks the co-host to build a set from a brief, and the agent discovers → sequences → and explains *why* each critical transition works, acting as a mentor rather than a black box. This is where the tools become a co-host, on the existing bounded no-hang harness so it can never wedge and its voice matches the live co-host's.
**Depends on:** Phase 84 (`discover_pool`), Phase 85 (`sequence_set`), Phase 86 (`export_set`) — the tools it orchestrates. Consumed by Phase 88 (the UI spawns this CLI surface as a subprocess).
**Requirements:** AGENT-01, AGENT-02
**Success Criteria** (what must be TRUE):
  1. A DJ runs `vibemix library build-set "<brief>"` (Viber set-prep; local Codex) and gets a full set built from a natural-language brief — the agent discovers → sequences → and explains in 1-2 sentences why each critical transition works (key/BPM/energy/vibe), as a mentor not a black box, with every track grounded (never invented — all ids flow through the seen-set) (AGENT-01).
  2. The set-prep flow REUSES the bounded no-hang Viber backend harness (iteration cap `MAX_TOOL_ITERATIONS`, per-call + per-tool timeouts, handlers RETURN errors never raise) and the shared persona/lens seam (Phase-79/82), so it can never wedge and its voice matches the co-host's (AGENT-02).
  3. The flow lands as a "set-prep" system-instruction VARIANT layered on the existing matrix/lens seam — no persona drift; current app path is local Codex.
  4. The agent path is testable offline against a fake client (tool-call sequencing + grounding-gate + no-hang bounds) without the live API; the live e2e run on the funded key rides forward as a soft KAAN-ACTION ear-pass, never faked.
**Plans**: TBD

### Phase 88: UI — "Build a Set" Path
**Goal:** Give the DJ a first-class "Build a Set" path in the app — brief + curve picker → a sequenced result they can read (each slot's track, key/BPM/energy, and the per-transition reasoning) → an Export-to-Rekordbox button — in the CDJ-Whisper aesthetic, with every control working LIVE end-to-end. This is where the engine becomes a product surface; the live button-audit is a hard gate.
**Depends on:** Phase 87 (the CLI/agent surface the Tauri command spawns as a subprocess and parses JSON stdout). frontend-enforcement skill applies (20/80 rule, retro-futurist hardware vocabulary, no AI slop).
**Requirements:** UI-01, UI-02
**Success Criteria** (what must be TRUE):
  1. The app exposes a "Build a Set" path — brief input + energy-curve preset picker → a sequenced result list showing each slot's track, key/BPM/energy, and the per-transition reasoning → an Export-to-Rekordbox button — in the CDJ-Whisper aesthetic (phosphor-amber accent on anodised charcoal, segment-LED/material treatment, no generic Tailwind slop) (UI-01).
  2. Every control in the "Build a Set" path works live end-to-end — verified in the REAL `cargo tauri dev` app via `ui.log` (`[vmx:click]/[vmx:ipc>]/[vmx:ipc<]/[vmx:error]`), not just green vitest — with NO dead/no-op buttons, and the result is a downloaded Rekordbox file + clear next-step import instructions (UI-02).
  3. Library/curate results flow via Tauri commands (subprocess stdout), NOT ws IPC — so NO `messages.schema.json` edit / `codegen:ipc` is required (one-socket Invariant #4 holds); if any schema edit DOES become necessary, `npm run codegen:ipc` is run (pre-compiled ajv validator).
  4. The live-app verification is a HARD GATE per `feedback_verify_live_app_not_just_tests` — green vitest ≠ working app; launch the real app, click every control, confirm each fires + gets a reply (no timeouts) in `ui.log`.
**Plans**: TBD
**UI hint**: yes

### v8.2 Coverage

✓ All 13 v8.2 REQ-IDs mapped to exactly one phase (ENERGY-01/02/03 → P83 · DISCOVER-01/02/03 → P84 · SEQUENCE-01/02/03 → P85 · EXPORT-01/02 → P86 · AGENT-01/02 → P87 · UI-01/02 → P88). No orphans, no duplicates.
✓ Dependency spine: (P83 ENERGY ∥ P84 DISCOVER, independent) → P85 SEQUENCE (needs DISCOVER's pool + optionally ENERGY's curve fidelity — degrades to BPM proxy) ‖ P86 EXPORT (independent of SEQUENCE internals; serializes any ordered grounded set) → P87 AGENT (orchestrates DISCOVER/SEQUENCE/EXPORT tools) → P88 UI (consumes the AGENT/CLI surface).

### v8.2 Progress Table

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 83. ENERGY — Perceived-Dancefloor-Energy v1 | shipped | Complete | 2026-05-26 |
| 84. DISCOVER — Pool Building | shipped | Complete | 2026-05-26 |
| 85. SEQUENCE — Energy-Curved Ordering | shipped | Complete | 2026-05-26 |
| 86. EXPORT — One-Click to Rekordbox | shipped | Complete | 2026-05-26 |
| 87. AGENT — Set-Prep Co-Host Flow | shipped | Complete | 2026-05-26 |
| 88. UI — "Build a Set" Path | shipped | Complete; UI-02 KAAN-ACTION ear-pass remains | 2026-05-26 |

---

# v8.1 "One Mind" — ✅ SHIPPED 2026-05-26 (audit PASSED; full details archived in `.planning/milestones/v8.1-ROADMAP.md`)

**Goal:** Connect vibemix's disconnected islands into ONE grounded product — *"an AI that hears music with you, and gets you."* The shallowness isn't a Gemini limit; it's a **wiring gap** + asking Gemini to be the ear. Make the DSP/MIDI/embedding stack the **EAR** (structured state + multi-scale trajectory + the DJ's moves + genre), Gemini the taste/culture **VOICE**, with a shared **taste layer** and **three lenses** (hype / critique / tutor) across both surfaces (live co-host + library curator).

**Anti-creep acid test (v8.1, historical):** *"Does this CONNECT an existing-but-orphaned capability into the one grounded product, or make the grounded reaction measurably deeper / less-slop — WITHOUT adding a new AI/embedding provider, a new MIR library, a new ws port, or a new IPC envelope?"* If not, defer. The v8.1 Gemini-only/no-CLAP rule was later superseded only for local library embeddings by Phase 90; Mem0/Letta/Zep/Cognee remain out.

**Hard constraints (locked, encoded in every phase):**
- **Ship, don't over-engineer** — each phase ships ONE connected, tested wire (the DSP rabbit-hole was the lesson).
- **Historical v8.1 AI-provider lock**; **no new MIR libraries / no new DSP detectors** (GPL/AGPL/NC license wall vs Apache-2.0 + Bravoh reuse); no new ws ports; no new IPC envelopes; no managed-memory frameworks. Phase 90 superseded the embedding side with local CLAP ONNX only.
- **Four cardinal invariants hold by ADDITIVE design** (single-writer · citation-grounding · trust-the-audio · one-socket) — the gated-off cold path stays **byte-identical** to the v8.0 baseline.
- **Honest green** — unit-testable without the API; live e2e on the funded key (`...32u744`, project 709533190790). Never fake results.
- **`gsd-autonomous fully`** — blockers (Gemini billing — resolved; any live-hardware ear-pass) ride forward to KAAN-ACTION; never pause.

**Empirical grounding:** 3 frontier models returned 3 different genres for one track (raw-audio bench floor) → Gemini's raw ear isn't reliable; ground it. Genre-from-embeddings hit **86.5%** nearest-prototype accuracy at **€0** (cached vectors). An env-var ghost key shadowing `.env` was found + fixed (WIRE-06).

**Charter + research:** `.planning/archive/2026-05-27-stale-one-mind-research/one-mind-charter.md` · `.planning/archive/2026-05-27-stale-one-mind-research/connection-map.md` (top-5 wires, file:line) · `.planning/archive/2026-05-27-stale-one-mind-research/genre-from-embeddings.md` (the 86.5% win) · `.planning/archive/2026-05-27-stale-one-mind-research/gemini-audio-truth-test.md` (floor data) · `.planning/archive/2026-05-27-stale-one-mind-research/gsd-operational-playbook.md`.

**Dependency spine:** P77 (WIRE — connect the islands; the grounding→agent wire is highest leverage) → P78 (PERCEIVE — deltas/confidence/trajectory/genre-prototype, riding on the wired evidence) → P79 (LENS) ‖ P80 (GROUND) [both build on the wired+deepened prompt] → P81 (BENCH — the instrument that benches model × grounding × prompting × contexting × lens × taste; depends on GROUND + LENS being in place to bench them) → P82 (CURATE — unify curator + co-host on the proven shared engine / taste / lens).

## Phases

- [ ] **Phase 77: WIRE — Connect the Islands** — Grounding→live agent + persona/lens unify + memory ingest on live path + env-key override fix (WIRE-02/03 already shipped).
- [ ] **Phase 78: PERCEIVE — Deeper, Generalized Ear** — deltas + calibrated confidence + multi-scale trajectory + mean-centered genre-prototype lookup (no new DSP, no MIR libs). **4 plans, 3 waves.**
- [ ] **Phase 79: LENS — Three Grounded Modes** — hype / critique / tutor as prompt lenses over one structured state, lens selection shared across surfaces.
- [x] **Phase 80: GROUND — Gemini as Secondary Ear** — audio part fed alongside structured evidence, hallucination-guarded; reaction model config-resolved by the bench.
- [ ] **Phase 81: BENCH — The Validation Instrument** — multi-dimensional bench (model × grounding × prompting × contexting × lens × taste) + auto first-pass eval + Kaan's-ear review surface. **4 plans, 4 waves.**
- [ ] **Phase 82: CURATE — Unify Curator + Co-Host** — both surfaces share the perception engine + structured-state contract + taste layer + persona.

| # | Phase | Goal | REQ-IDs | SC count |
|---|-------|------|---------|----------|
| 77 | WIRE — Connect the Islands | 4/4 | Complete    | 2026-05-25 |
| 78 | PERCEIVE — Deeper, Generalized Ear | 4/4 | Complete    | 2026-05-26 |
| 79 | LENS — Three Grounded Modes | 3/3 | Complete    | 2026-05-26 |
| 80 | GROUND — Gemini as Secondary Ear | 2/2 | Complete    | 2026-05-26 |
| 81 | BENCH — The Validation Instrument | 4/4 | Complete    | 2026-05-26 |
| 82 | CURATE — Unify Curator + Co-Host | 2/2 | Complete    | 2026-05-26 |

## Phase Details

### Phase 77: WIRE — Connect the Islands
**Goal:** Turn the strongest islands into one grounded mind — the live co-host references what is actually playing (via the already-armed-but-orphaned Grounding engine), both surfaces speak with one persona/lens, the recall store actually fills on a real session, and the app loads its API key without a ghost env var shadowing `.env`.
**Depends on:** Nothing (first v8.1 phase). Builds additively on the v8.0 reaction path.
**Requirements:** WIRE-01, WIRE-02 (✅ shipped `ccf4930` — NO new work), WIRE-03 (✅ shipped `a9979b8` — NO new work), WIRE-04, WIRE-05, WIRE-06
**Success Criteria** (what must be TRUE):
  1. On a track-aware event, the live co-host cites the actual track from `library.db` — `DJCoHostAgent` now takes a `grounding` kwarg, the armed `Grounding` object is passed in, and `identify_playing` injects a `[track:<id>]` citation that survives the citation-grounding gate (WIRE-01).
  2. The 8 genre-chain detectors' measured evidence appears in the prompt and registers in `EvidenceRegistry` (WIRE-02 — already TRUE via `ccf4930`; pinned by a regression test, no new work), and `detected_genre` is surfaced confidence-gated in the prompt evidence (WIRE-03 — already TRUE via `a9979b8`; pinned, no new work).
  3. The hype/critique/tutor persona is resolved from `prompts/matrix.py` by BOTH the live co-host and the then-current library curator — the old standalone agent stops hardcoding `_SYSTEM_INSTRUCTION` and reads a curator-context variant of the same lens (WIRE-04).
  4. `memory.db` is populated on the live `main()` path — the boot + session-close ingest sweeps fire in a real session (lifted out of the never-called `SessionLoop.run()`), so recall has fuel to retrieve (WIRE-05).
  5. The app loads `GEMINI_API_KEY` from `.env` even when a stale shell env var is present — `.env` wins (override or clear the ghost key), verified by a test that sets a decoy env var (WIRE-06).
**Plans**: 4 plans
Plans:
- [x] 77-01-PLAN.md — Wave 0: failing test scaffolds for WIRE-01/04/05/06 + WIRE-02/03 regression pins
- [x] 77-02-PLAN.md — Wave 1: WIRE-04 — build_curator_instruction seam; both curator backends read it
- [x] 77-03-PLAN.md — Wave 1: WIRE-06 — .env override=True (funded key wins over ghost shell var)
- [x] 77-04-PLAN.md — Wave 2: WIRE-01 (grounding→agent off-loop seam) + WIRE-05 (gated memory.db ingest on live path)

### Phase 78: PERCEIVE — Deeper, Generalized Ear
**Goal:** Make the existing ear *speak in change, not snapshots* — the prompt evidence carries deltas + calibrated per-fact confidence (so Gemini can abstain), a multi-scale trajectory (phrase / energy-arc / recent-moves) so it reasons over time, and an embedding-driven mean-centered genre prototype lookup (86.5%-validated, €0). All additive to the single-writer `MusicState`; **NO new DSP, NO MIR libs.**
**Depends on:** Phase 77 (the wired evidence_line + grounding are the surface these enrich)
**Requirements:** PERCEIVE-01, PERCEIVE-02, PERCEIVE-03
**Success Criteria** (what must be TRUE):
  1. Prompt evidence carries deltas + a calibrated confidence per fact (not raw absolute scalars) — Gemini reads "kick density rose 18%" rather than a bare number, and can abstain when confidence is low (PERCEIVE-01).
  2. The prompt carries a multi-scale trajectory (phase-chain position / energy-arc / recent DJ moves) so a reaction can reference where the set has been and is going, not just the current bar (PERCEIVE-02).
  3. `detected_genre` is driven by a mean-centered nearest-prototype cosine lookup over cached embeddings — written ONLY by the single-writer refresh loop, confidence-floored so a genre is never asserted the audio doesn't support (PERCEIVE-03).
  4. When trajectory/genre signal is cold or below the confidence floor, the prompt is byte-identical to the v8.0 baseline (additive-design invariant holds; the cold path adds nothing).
**Plans:** 4 plans (3 waves)
- [x] 78-01-PLAN.md — Wave-0 RED scaffolds (xfail-strict) for PERCEIVE-01/02/03 + the cold-path byte-identity REAL-GREEN pin [wave 1]
- [x] 78-02-PLAN.md — PERCEIVE-01 deltas + calibrated confidence & PERCEIVE-02 multi-scale trajectory (additive MusicState fields, deltas.py, single-writer + gated render) [wave 2]
- [x] 78-03-PLAN.md — PERCEIVE-03 mechanism: library/genre_prototypes.py (mean-centered nearest-prototype build/classify + thread-safe holder, no state writes) [wave 2, parallel with 78-02]
- [x] 78-04-PLAN.md — PERCEIVE-03 wiring: genre_reconcile.py (centered-cosine→0.5-render-band normalization, the flagged risk) + single-writer refresh feed [wave 3]

### Phase 79: LENS — Three Grounded Modes
**Goal:** Make hype / critique / tutor three real grounded lenses over the SAME structured state — not three separate brains — with lens selection shared across the co-host and the curator. The tutor lens explains DJing based on who you are + the semantics + reality + taste; the critique lens says what to fix; hype is the party voice. All three read the same wired+deepened evidence.
**Depends on:** Phase 77 (unified persona seam), Phase 78 (the deepened evidence the lenses interpret)
**Requirements:** LENS-01, LENS-02
**Success Criteria** (what must be TRUE):
  1. hype / critique / tutor exist as three grounded prompt lenses over the same structured state — switching lens changes the voice/intent, not the underlying grounded facts (LENS-01).
  2. Lens selection is shared across the co-host and curator surfaces — choosing "tutor" once flows to both (LENS-02).
  3. Each lens still passes the citation-grounding gate — a lens may change tone but cannot fabricate evidence; un-cited output strips to the ack-bank fallback regardless of lens.
**Plans:** 3 plans, 3 waves
  - [x] 79-01-PLAN.md — Wave-0 RED scaffolds (xfail-strict for LENS-01/02) + default-lens / cold-path byte-identity pin
  - [x] 79-02-PLAN.md — LENS-01: LENS_TO_MODE_MOOD map + build_lens_instruction selector over the untouched build_system_instruction
  - [x] 79-03-PLAN.md — LENS-02: shared ConfigStore.extra["lens"] selection (_apply_lens) read by both co-host + curator, no IPC/schema bump

### Phase 80: GROUND — Gemini as Secondary Ear
**Goal:** Let Gemini *also* hear the audio as a secondary grounding input ("if it can hear in hollow space, use it") — fed alongside the structured DSP evidence, never as the primary perceiver — hallucination-guarded throughout. The reaction model is config-resolved via `model_router` (zero hardcoded literals) and the actual choice is decided by the bench (P81).
**Depends on:** Phase 77 (wired evidence), Phase 78 (deepened evidence the audio rides alongside)
**Requirements:** GROUND-01, GROUND-02
**Success Criteria** (what must be TRUE):
  1. The audio part is fed to Gemini alongside the structured evidence — and a Gemini claim that contradicts or isn't backed by the DSP evidence is hallucination-guarded (strips / abstains), so trust-the-audio still wins (GROUND-01).
  2. The reaction model is resolved via `model_router.resolve(...)` with zero hardcoded model literals (CI grep-gate holds), so the bench's winning model can be swapped in by config alone (GROUND-02).
  3. With the audio-secondary path gated off, the prompt + reaction are byte-identical to the v8.0 baseline (additive design).
**Plans**: 2 plans
- [x] 80-01-PLAN.md — Wave-0 RED scaffolds: the un-backed-audio-claim strip guard + flag-ON framing (xfail-strict) + cold-path byte-identity & GROUND-02 router-resolve pins (real-green)
- [x] 80-02-PLAN.md — gated `secondary_ear` framing in `build_parts_description`, thread `VIBEMIX_GROUND_SECONDARY_EAR` → kwarg → call site, flip the guard xfails, document `live_coach` as the bench-swap alias

### Phase 81: BENCH — The Validation Instrument
**Goal:** Build the experiment that PROVES the architecture — a multi-dimensional bench over model × input-grounding (raw audio | DSP-evidence-only/no-audio | audio+DSP | audio+DSP+trajectory+genre) × prompting (generic | structured) × contexting (snapshot | trajectory) × lens (hype/critique/tutor) × taste (with/without rubric), run on real tracks. An automated first-pass scores each cell (groundedness vs DSP facts, specificity, mode-fidelity); the cells are then surfaced for **Kaan's ear as the final judge** (Phase-16 rule). The "no-audio" cell tests "does the intelligence reside elsewhere."
**Depends on:** Phase 80 (the GROUND audio-secondary path) + Phase 79 (the three lenses) must exist to be benched; Phase 78 (trajectory/genre) supplies the grounding axes.
**Requirements:** BENCH-01, BENCH-02, BENCH-03
**Success Criteria** (what must be TRUE):
  1. A multi-dimensional bench harness runs model × grounding × prompting × contexting × lens × taste on real tracks and records each cell's output (BENCH-01).
  2. An automated first-pass eval scores groundedness (vs DSP facts), specificity, and mode-fidelity per cell — unit-testable on fixtures without the live API (BENCH-02).
  3. Bench cells are surfaced for Kaan's-ear final judgment via a KAAN-ACTION review surface — the automated score ranks, Kaan's ear decides the winning architecture + model (BENCH-03).
  4. The bench runs honest-green offline (mocked/fixture cells unit-testable) AND has a documented live e2e path on the funded key — results are never faked.
**Plans**: 4 plans (4 waves)
Plans:
- [x] 81-01-PLAN.md — Wave 0: failing xfail-strict scaffolds for BENCH-01/02/03 + _FakeClient/_RaisingClient fixtures + in-repo .mp3 data + the bench model-literal guard
- [x] 81-02-PLAN.md — BENCH-01: the harness (cell/matrix/fixtures/assemble/run) composing the real seams + the no-audio cell + the 429 fail-safe + `vibemix bench` CLI
- [x] 81-03-PLAN.md — BENCH-02: pure eval scorers (groundedness via reused CitationLinter + specificity + lens-fidelity; ranks, never decides)
- [x] 81-04-PLAN.md — BENCH-03: the ranked KAAN-ACTION review surface (EMPTY verdict) + docs/bench.md (produce step + parked verdict/rubric)

### Phase 82: CURATE — Unify Curator + Co-Host
**Goal:** Close the diamond — the agentic library/Viber curator and the live co-host become two facets of "AI that hears music with you," sharing ONE perception engine + structured-state contract and ONE taste layer + persona. The curator can curate "for this DJ"; the co-host can lean on what the DJ's library says about their taste.
**Depends on:** Phase 77 (unified persona seam + shared grounding), Phase 78 (shared perception/state contract), Phase 79 (shared lens), Phase 81 (the bench-proven engine choice)
**Requirements:** CURATE-01, CURATE-02
**Success Criteria** (what must be TRUE):
  1. Curator and co-host share the perception engine + the structured-state contract — both read one "what is true about this music / track" representation, not two parallel ones (CURATE-01).
  2. Curator and co-host share the taste layer + persona — the long-term DJ profile + the hype/critique/tutor lens reach both surfaces (CURATE-02).
  3. The unification is additive — the existing `library curate` / Telegram CLI surfaces keep working, and the four cardinal invariants still hold (no new ws port, no new IPC envelope, single-writer untouched).
**Plans:** 2 plans
Plans:
- [x] 82-01-PLAN.md — Wave-0 RED scaffolds (CURATE-01/02 xfail) + lens/no-MusicState/no-leak/surfaces real-green pins
- [x] 82-02-PLAN.md — SEAM #1 genre-via-genre_prototypes (toolset) + SEAM #2 _taste_hint reads shared profile (gemini+interactive+codex)

### v8.1 Coverage

✓ All 18 v8.1 REQ-IDs mapped to exactly one phase (WIRE-01..06 → P77 · PERCEIVE-01..03 → P78 · LENS-01..02 → P79 · GROUND-01..02 → P80 · BENCH-01..03 → P81 · CURATE-01..02 → P82). No orphans, no duplicates.
✓ WIRE-02 (`ccf4930`) + WIRE-03 (`a9979b8`) already satisfied — placed in P77, marked DONE, no new work planned (P77's remaining work is WIRE-01/04/05/06).

### v8.1 Progress Table

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 77. WIRE — Connect the Islands | shipped | Complete | 2026-05-26 |
| 78. PERCEIVE — Deeper, Generalized Ear | shipped | Complete | 2026-05-26 |
| 79. LENS — Three Grounded Modes | shipped | Complete | 2026-05-26 |
| 80. GROUND — Gemini as Secondary Ear | shipped | Complete | 2026-05-26 |
| 81. BENCH — The Validation Instrument | shipped | Complete; BENCH-03 verdict parked | 2026-05-26 |
| 82. CURATE — Unify Curator + Co-Host | shipped | Complete | 2026-05-26 |

---

# v8.0 "Proof & Polish" — SHIPPED 2026-05-25 (tech_debt accepted)

**Goal:** Take the system from "engineering-sound on paper" to **proven, easy, and live on GitHub** — everything logged · simulated · reported · tested · fixed · re-tested · verified · GitHub-done, plus real **ease of use** and a **whole-design level-up loop**. The deep audit (`.planning/ALL-MILESTONES-DEEP-AUDIT.md`) already finds the system **sound** (4256 tests green at branch HEAD, 4 cardinal invariants hold); v8.0 *proves and polishes* — it does not rescue.

**Anti-creep acid test:** *"Does this make an existing capability genuinely logged / simulated / reported / tested / fixed / verified / pushed — or easier to use / better-looking — WITHOUT a new product capability, AI/embedding provider, managed framework, ws port, or IPC envelope?"* If not, defer. Gemini-only holds; the four cardinal invariants hold by zero-touch on the reaction path.

**Dependency spine:** P71 (land in-flight branch work) → P72 (log everything + simulate hardware) → P73 (report + full-grid test + fix loop + verify + close audit findings) → P74 (ease of use) ‖ P75 (design level-up) [both depend on P71-landed UI, run after P73 green] → P76 (GitHub done: push backlog, CI green; signed-release + social stay KAAN-ACTION).

| # | Phase | Goal | REQ-IDs |
|---|-------|------|---------|
| 71 | Land & Verify | Finish + verify + commit the uncommitted live-tuning + observability branch work; green its new Py/TS/Rust tests | LOG-01, LOG-03 |
| 72 | Logged & Simulated | Unified structured logging end-to-end; simulation/replay harness for hardware-gated paths (BlackHole/FLX4/device-select) | LOG-02, LOG-04, SIM-01..03 |
| 73 | Reported · Tested · Fixed · Verified | Reports (test/coverage/session); full marker-grid run + fix loop to green; close deep-audit findings #1–#4; verify | RPT-01..03, TEST-01..05 |
| 74 | Ease of Use | First-run/onboarding friction, device-select UX, settings clarity, actionable failure states | UX-01..04 |
| 75 | Design Level-Up Loop | Whole-design CDJ-Whisper glow-up (impeccable + frontend-enforcement) across all surfaces; review→fix→re-review to zero HIGH | DESIGN-01..04 |
| 76 | GitHub Done | Push the ~528-commit backlog + branch; origin/main current; CI green on full matrix; repo presence finalized | GH-01..03 (GH-04 = KAAN-ACTION) |

### Phase 71 — Land & Verify
**Goal:** The in-flight `live-tuning-or-brain` work (device_select, the debug-log surface, tray-mood, audio/sidecar/session changes) is finished, verified, and committed in clean atomic commits.
**Success criteria:** (1) `device_select.py` + new audio backend changes land with `test_device_select` + `test_audio_macos` additions green; (2) debug-log surface (`debug_log.rs` + `debug-log.ts` + `debug-log-ws.ts` + `debug-log.spec`) wired one-socket-safe and green; (3) `tray-mood` + `test_proxy_fallback` land green; (4) default `pytest -q` stays 0-red (≥4256 passed); (5) TS + Rust suites run for the changed files.

### Phase 72 — Logged & Simulated
**Goal:** Everything important is logged through one structured surface, and the hardware-gated paths are simulatable headlessly.
**Success criteria:** (1) reaction turns log evidence packet + citation-gate decision (LOG-02); (2) a log-level switch gates verbosity without changing default UX (LOG-04); (3) a sim harness replays a session end-to-end with no hardware + no live Gemini (SIM-01); (4) synthetic BlackHole/FLX4/device fixtures verify the §V7-LIVE paths in CI (SIM-02); (5) the sim emits a deterministic artifact (SIM-03).

### Phase 73 — Reported · Tested · Fixed · Verified
**Goal:** The whole suite is run, reported, every red driven green, and the result verified; the deep-audit housekeeping is closed.
**Success criteria:** (1) saved test+coverage report artifact (RPT-01); (2) sim-session report (RPT-02); (3) full default suite 0-red + opt-in marker grid exercised (TEST-01/02); (4) TS+Rust green (TEST-03); (5) audit findings #1–#4 closed (TEST-04); (6) fix→re-test loop ends green + committed, no new skip/xfail graveyards (TEST-05); (7) v8.0 verification report ties each REQ to evidence (RPT-03).

### Phase 74 — Ease of Use
**Goal:** A stranger's path from install to first reaction is effortless and forgiving.
**Success criteria:** (1) guided first-run with clear empty/loading/permission states (UX-01); (2) self-explanatory device selection + routing, no BlackHole guesswork (UX-02); (3) clear, reversible mode/level/settings controls (UX-03); (4) every failure mode (no audio/key/proxy/MIDI) gives actionable guidance (UX-04).

### Phase 75 — Design Level-Up Loop
**Goal:** Every surface is leveled up to the CDJ-Whisper bar through an auditor-driven loop, no AI slop.
**Success criteria:** (1) session UI + pill zero HIGH findings (DESIGN-01); (2) mascot overlay + debrief + wizard + settings pass the bar (DESIGN-02); (3) review→fix→re-review loop run to zero HIGH (DESIGN-03); (4) consistent design tokens across surfaces (DESIGN-04).

### Phase 76 — GitHub Done
**Goal:** GitHub reflects the verified reality; the only thing left is Kaan's signature-gated public publish.
**Success criteria:** (1) ~528-commit backlog + branch pushed; origin/main current (GH-01); (2) CI green on full matrix for the pushed state (GH-02); (3) repo presence finalized, no stale claims (GH-03); (4) §SHIP-V4 signed-release + social documented as the sole KAAN-ACTION carveout, NOT auto-fired (GH-04).

---

# v7.0 "Open House" — SHIPPED 2026-05-24 (tech_debt accepted)

<details>
<summary>✅ v7.0 Open House (Phases 67–70) — SHIPPED 2026-05-24 (tech_debt accepted)</summary>

4 phases shipped engineering-green under `gsd-autonomous fully` mode. 20 plans, 37 tasks, 19/19 v7.0 REQ-IDs satisfied (engineering-side), 6/6 cross-phase wirings sound, UI-review PASS 23/24 on the landing. A **WIRING + DISCHARGE + POLISH milestone with ZERO new product capability** — zero net-new dependencies, zero new ws ports, zero new IPC envelopes. The four cardinal invariants (single-writer / citation-grounding / trust-the-audio / one-socket) held by zero-touch (only Phase 69 touched `src/vibemix/agent/` for the client-side proxy fallback).

- [x] Phase 67: All Tests Pass (5/5 plans) — 2026-05-23 (TEST-01..04; default `pytest -q` 0-red, 21-job `full-test-matrix.yml` CI, static skip/flake gates, 10× flake-hunt baseline)
- [x] Phase 68: All Devices Ready (5/5 plans) — 2026-05-23 (DEV-01..05; 10 profile contracts + synthetic-MIDI smokes, catalog reconciled to single `profiles/` source, hot-plug + audio-backend matrices, contributor recipe)
- [x] Phase 69: OSS Fully Integrated (5/5 plans) — 2026-05-24 (OSS-01..05; 4 OSS docs + presence test, client-side proxy fallback "Co-host unavailable this session", BYO-key doc, Homebrew+Scoop scaffolds, §SHIP-V4 publish pre-staged)
- [x] Phase 70: GitHub Sexified, Generated, Tested (5/5 plans) — 2026-05-24 (GH-01..05; asset reproducibility pipeline + auto-gen og-card, CDJ-Whisper Pages landing, demo poster, one-stop `test_github_presence.py`)

**KAAN-ACTION (live-confirm / external-clock, rides forward):** §V7-LIVE-01..11 (live hardware + first-CI-green + BYO walk) + §V7-PROXY (Bravoh server-side hardening) + §V7-LANDING (Pages-live + Kaan-felt aesthetic sign-off + real waitlist URL) + §ASSETS-DEMO-CUT (real 30-sec demo film, Francesco capture) + **§SHIP-V4 (HARD external clock — OSS-04 real `cut_release.sh v0.1.0-rc1` publish, gated on Apple Dev + SignPath; v4.0 "SHIP" closes alongside when it fires)**. All in `KAAN-ACTION-LEGAL.md`.

**Git tag + branch merge deferred** (consistent with v4.0 + v5.0 + v6.0): the `v7.0` tag + `live-tuning-or-brain` → main merge are Kaan's call on his clock (the OSS-04 publish + v4.0 close ride the same signature clock).

Full archive: `.planning/milestones/v7.0-ROADMAP.md` · Requirements: `.planning/milestones/v7.0-REQUIREMENTS.md` · Audit: `.planning/milestones/v7.0-MILESTONE-AUDIT.md`

</details>

---

# v6.0 "The Memory Turn" — SHIPPED 2026-05-23 (tech_debt accepted)

<details>
<summary>✅ v6.0 The Memory Turn (Phases 63–66) — SHIPPED 2026-05-23 (tech_debt accepted)</summary>

4 phases shipped engineering-green under `gsd-autonomous fully` mode. 12 plans, 14/14 v6.0 REQ-IDs satisfied, 6/6 cross-phase integration seams WIRED, 53/53 must-haves verified, 247/247 v6.0 surface tests GREEN. A **WIRING / REUSE milestone with ZERO net-new dependencies** — built entirely on the shipped `src/vibemix/library/` primitives (sqlite-vec, cosine_topk, embed-cache, grounding pattern, EVIDENCE_SOURCES schema).

- [x] Phase 63: Memory Store (3/3 plans) — 2026-05-22 (STORE-01..04 GREEN; 19/19 tests/memory/)
- [x] Phase 64: Session Ingest (3/3 plans) — 2026-05-22 (INGEST-01..03 GREEN; one v1 moment kind = `coach_line`; `moment` cut, `audio_moment` deferred)
- [x] Phase 65: Memory Retrieval Seam — ANTI-SLOP RELEASE GATE (4/4 plans) — 2026-05-22 (RECALL-01..04 GREEN; existence-only `recall` source à la P59 `key:`, fabricated `[recall:<id>]` strips whole turn)
- [x] Phase 66: Visible Copilot Move (2/2 plans) — 2026-05-22 (COPILOT-01..03 GREEN; transition-shape + vocabulary callbacks; ships behind `VIBEMIX_RECALL_ENABLED=0` until §RECALL-EAR Kaan-ear pass)

**KAAN-ACTION (live-confirm, rides forward):** §RECALL-EAR felt-quality discharge (4 ear items) + §LIVE-EMBED real-session FLEX-tier round-trip + two doc-drifts (code correct) + STORE-03 recordings-UI call-site (out of v6.0 scope; future recordings-UI phase). All in `KAAN-ACTION-LEGAL.md §RECALL-EAR` + `66-HUMAN-UAT.md`.

**Git tag deferred** (consistent with v4.0 + v5.0): the `v6.0` tag + branch merge are Kaan's call on his clock.

Full archive: `.planning/milestones/v6.0-ROADMAP.md` · Requirements: `.planning/milestones/v6.0-REQUIREMENTS.md` · Audit: `.planning/milestones/v6.0-MILESTONE-AUDIT.md`

</details>

---

# v5.0 "The Useful Cut" — SHIPPED 2026-05-22 (tech_debt accepted)

<details>
<summary>✅ v5.0 The Useful Cut (Phases 59–62) — SHIPPED 2026-05-22 (tech_debt accepted)</summary>

Deck-aware, actionable, unobtrusive. Full session-wide deck-state (pyrekordbox XML → Gemini-vision → numpy ladder) with a citable `key:` evidence source; a deterministic Camelot harmonic key-clash gate the LLM only narrates (ships **default-OFF** behind the Kaan-ear veto); an actionable-not-hype coach persona extending the `live-tuning-or-brain` branch (hype goldens regression-fenced); and a transparent, draggable, non-focus-stealing **floating pill** as the primary live surface (Three.js mascot kept opt-in/secondary, mascot-audit green). 4/4 phases, 17/17 requirements satisfied, 4/4 cross-phase integration seams WIRED.

- [x] Phase 59: Full Deck Awareness + Grounding (5/5 plans) — 2026-05-21
- [x] Phase 60: Harmonic-Feedback Confidence Gate (4/4 plans) — 2026-05-21 (detector default-OFF until the Kaan-ear veto flip)
- [x] Phase 61: Actionable-Not-Hype Coach Persona (2/2 plans) — 2026-05-21
- [x] Phase 62: Floating Pill UI (5/5 plans) — 2026-05-22

Full archive: `.planning/milestones/v5.0-ROADMAP.md` · Requirements: `.planning/milestones/v5.0-REQUIREMENTS.md` · Audit: `.planning/milestones/v5.0-MILESTONE-AUDIT.md`

</details>

---

# v4.0 SHIP — OPEN (engineering-complete 8/8, publish on signature clock — NOT archived)

> **Status:** All 8 phases (51–58) are engineering-complete. The milestone is deliberately **left open and unarchived** — its public RC publish stays gated on the external signature clock (Apple Dev Agreement via Francesco + SignPath OSS cert). **v7.0's OSS-04 actually consumes this publish** (closes alongside §SHIP-V4 discharge). Do not delete or archive this section until OSS-04 fires.

<details>
<summary>🟡 v4.0 SHIP (Phases 51–58) — engineering-complete 2026-05-21, publish on signature clock</summary>

- [x] Phase 51: Real-Hardware Bring-Up (3/3 plans) — 2026-05-21
- [x] Phase 52: Audio Path + Feature Grounding (4/4 plans) — 2026-05-21
- [x] Phase 53: Controller Live + Graceful Fallback (2/2 plans) — 2026-05-21
- [x] Phase 54: Hype Mode Live (4/4 plans) — 2026-05-20
- [x] Phase 55: Feedback Mode Live + Citation Integrity (3/3 plans) — 2026-05-21
- [x] Phase 56: Performance + Live Mascot (3/3 plans) — 2026-05-21
- [x] Phase 57: Sexify Finish (3/3 plans) — 2026-05-21
- [x] Phase 58: Ship Readiness (4/4 plans) — 2026-05-21 (`cut_release.sh --dry-run v0.1.0-rc1` GREEN; publish hard-guard regression-pinned)

**Critical path at close:** External clock — Apple Dev Agreement (Francesco) + SignPath OSS Foundation (Kaan, ~1-week SLA). `KAAN-ACTION-LEGAL.md §SHIP-V4` documents the one-button SHIP-CUT sequence. **v4.0 closes alongside v7.0 OSS-04.**

Full archive: `.planning/milestones/v4.0-ROADMAP.md`

</details>

---

## Phase History (Archived)

<details>
<summary>✅ v0.1.0 MVP Foundation (Phases 1–14) — SHIPPED 2026-05-13</summary>

See `.planning/milestones/v0.1.0/` for full archive.

</details>

<details>
<summary>✅ v2.0 Research-Driven Ship (Phases 15–26) — SHIPPED 2026-05-14 (tech_debt accepted)</summary>

12 phases shipped — 10 Claude-side end-to-end + 2 deferred to Kaan-action (Phase 15 Plan 04 UAT + entire Phase 16 ear-test gate). 38 plans, 1961 passing tests, 220 commits since `v0.1.0-rc1`, ~45.7k LOC across `src/vibemix/`, `tauri/`, `scripts/`, `tests/`.

Full archive: `.planning/milestones/v2.0-ROADMAP.md` · Requirements: `.planning/milestones/v2.0-REQUIREMENTS.md` · Audit: `.planning/milestones/v2.0-MILESTONE-AUDIT.md`

</details>

<details>
<summary>✅ v2.1 The Unified Cut (Phases 27–39) — SHIPPED 2026-05-16 (tech_debt accepted)</summary>

13 phases shipped engineering-green under `gsd-autonomous fully` mode. 96 plans, 633 phase-scope tests added, 225 commits since `v2.0` tag, net ~+45k LOC. 105/105 v2.1 REQ-IDs engineering-satisfied. All 5 cross-phase integration seams audited WIRED.

Full archive: `.planning/milestones/v2.1-ROADMAP.md` · Requirements: `.planning/milestones/v2.1-REQUIREMENTS.md` · Audit: `.planning/milestones/v2.1-MILESTONE-AUDIT.md`

</details>

<details>
<summary>✅ v3.0 Clean OSS Ship (Phases 40–45) — SHIPPED 2026-05-17 (tech_debt accepted)</summary>

6 phases shipped engineering-green under `gsd-autonomous fully` mode. 41 plans, 250 commits since `v2.1.0` tag, net ~+61k LOC. 57/57 v3.0 REQ-IDs engineering-satisfied. All 3 integration seams + 5 flows audited.

Full archive: `.planning/milestones/v3.0-ROADMAP.md` · Requirements: `.planning/milestones/v3.0-REQUIREMENTS.md` · Audit: `.planning/milestones/v3.0-MILESTONE-AUDIT.md`

</details>

<details>
<summary>✅ v3.1 Distribution-Ready Pass (Phases 46–50) — SHIPPED 2026-05-18 (tech_debt accepted)</summary>

5 phases shipped engineering-green under `gsd-autonomous fully` mode. 32 plans, 61 commits since `v3.0` tag, net ~+57.5k LOC. 44/44 v3.1 REQ-IDs engineering-satisfied. All 5 cross-phase integration seams audited WIRED.

Full archive: `.planning/milestones/v3.1-ROADMAP.md` · Requirements: `.planning/milestones/v3.1-REQUIREMENTS.md` · Audit: `.planning/milestones/v3.1-MILESTONE-AUDIT.md`

</details>

---

## Milestone-Level Progress

| Milestone | Phases | Status | Shipped |
|-----------|--------|--------|---------|
| v0.1.0 MVP Foundation | 1–14 | ✅ Shipped | 2026-05-13 |
| v2.0 Research-Driven Ship | 15–26 | ✅ Shipped (tech_debt) | 2026-05-14 |
| v2.1 The Unified Cut | 27–39 | ✅ Shipped (tech_debt) | 2026-05-16 |
| v3.0 Clean OSS Ship | 40–45 | ✅ Shipped (tech_debt) | 2026-05-17 |
| v3.1 Distribution-Ready Pass | 46–50 | ✅ Shipped (tech_debt) | 2026-05-18 |
| v4.0 SHIP | 51–58 | 🟡 Engineering-complete (8/8) — publish on signature clock; closes alongside v7.0 OSS-04 | - |
| v5.0 The Useful Cut | 59–62 | ✅ Shipped (tech_debt) | 2026-05-22 |
| v6.0 The Memory Turn | 63–66 | ✅ Shipped (tech_debt) | 2026-05-23 |
| v7.0 Open House | 67–70 | ✅ Shipped (tech_debt) | 2026-05-24 |
| v8.0 Proof & Polish | 71–76 | ✅ Shipped (tech_debt) | 2026-05-25 |
| v8.1 One Mind | 77–82 | ✅ Shipped (audit PASSED) | 2026-05-26 |
| v8.2 Set Builder | 83–88 | ✅ Shipped (audit PASSED; UI-02 KAAN-ACTION) | 2026-05-26 |

### Phase 89: DJ-Library Ingest — Rekordbox MVP, clean metadata, cue-anchored excerpts, local CLAP, sqlite-vec

**Goal:** As a DJ, I want to have vibemix auto-detect my Rekordbox library and embed my tracks on-device, so that my library is searchable and ready in minutes.
**Mode:** mvp
**Requirements**: TBD
**Depends on:** local CLAP embedder + landed `CueAnchor`/`cue_engine` seams. NOT the v8.2 UI phase.
**Scope (MVP slice):** Rekordbox-only, end-to-end walking skeleton (detect → parse `collection.xml` → cue-anchored excerpts → `clap_engine` embed → sqlite-vec store). Serato/Traktor adapters + the file watcher are deferred to follow-up phases (91, 92 — 90 is the CLAP embedding-swap). Design spec: `docs/superpowers/specs/2026-05-26-dj-library-ingest-design.md`.
**Plans:** 3/3 plans complete

Plans:
- [x] 89-01-PLAN.md — Walking-skeleton ingest slice: auto-detect collection.xml + LibrarySource protocol + ingest_source orchestrator (detect → parse → on-device clap embed → sqlite-vec store, resumable/honest) + `library ingest` CLI
- [x] 89-02-PLAN.md — Metadata-richness slice: extend rekordbox.py to read genre/label/rating/play_count/comments + TEMPO beatgrid + Camelot-at-parse + cue Type fidelity; SCHEMA_VERSION bump
- [x] 89-03-PLAN.md — Cue-anchored excerpt slice: excerpt.py (dj-first CueAnchors, detect_cues auto fallback) → ≤80s windows; rewire ingest to mean-pool cue-anchored CLAP vectors

### Phase 90: CLAP — on-device full-precision library embeddings (512-dim cross-modal, replaces Gemini embedding)

**Goal:** The library vibe-search / curator / next-suggestion / Set-Builder discover layer embeds on-device via **CLAP** (`Xenova/larger_clap_music_and_speech` ONNX, 512-dim) instead of Gemini Embedding — killing the per-track API cost while keeping audio on the device. Ship default is **full-precision fp32 ONNX** (audio + text models pinned by size/SHA) for quality-first parity; fp16/q8 are available upstream but stay future optimization variants until they pass the same real-library parity gate. Gemini stays for live/TTS; Viber set-prep/chat uses local Codex during the current demo/test phase; neither path is used for library embeddings. Set-Builder modules (P83–87) were built dim-agnostic and now run over CLAP's 512D vectors.

**Requirements:** Direct implementation complete (no GSD phase-plan split per Kaan): Xenova ONNX backend in `library/clap_engine.py`; torch-free Slaney mel path; no-pad text query path; `ClapEmbedder` drop-in; `_cosine.EMBEDDING_DIM=512`; embedding factory/grounding routed through the CLAP interface; cache/store namespacing for the 512D swap; `library models` status/install/repair UX; full-precision model manifest with SHA/size verification. Remaining work: live re-embed of the real library without clobbering the old 1536D store, funded-key curate ear-pass, and optional fp16/q8 parity testing if install size/perf becomes the bottleneck.
**Depends on:** local CLAP model cache + `onnxruntime`; independent of the Set-Builder phase chain (P83–88) because those modules are dim-agnostic.
**Plans:** direct implementation complete; see `docs/clap-engine.md`, `docs/library.md`, and `.planning/research/CODEX-full-product-sweep-map.md`.

**HARD GATE:** curate genre separation must MATCH the proven baseline (techno + psy 100% on the real-library test) before the live library is permanently re-embedded at 512D. The fp32 ONNX path has passed the offline gate with torch absent; fp16/q8 cannot become defaults until they match it.

Plans:
- [x] CLAP ONNX embedding path wired and verified offline
- [x] Full-precision model installer/status/repair surface wired
- [ ] Live real-library re-embed + funded-key curate ear-pass

---

*Roadmap extended 2026-05-23 for v7.0 "Open House" — **4 phases (67–70)** continuing numbering from v6.0 (which ran 63–66). v4.0 "SHIP" stays OPEN and unarchived above — its publish closes alongside v7.0's OSS-04 (KAAN-ACTION §SHIP-V4 discharge fires `cut_release.sh v0.1.0-rc1` for real). v7.0 derives from 19 requirements across 4 pillars (TEST · DEV · OSS · GH), one phase per pillar, sized by `.planning/REQUIREMENTS.md` Traceability — 4/5/5/5 REQ-IDs per phase, zero orphans, zero duplicates. **Hard scope rule (locked):** v7.0 is WIRING + DISCHARGE + POLISH — zero new product capability, zero new AI providers, zero new managed-memory frameworks, zero new ws ports, zero new IPC envelopes. The four cardinal invariants (single-writer / citation grounding / "trust the audio" / one socket) hold by zero-touch — no phase modifies the reaction path. The v4.0 external signature clock is unchanged. Critical path: P67 (test infrastructure, dependency-free) → P68 (controller catalog reconciliation + audio backends, lands on P67's CI matrix) → P69 (OSS surface + actual publish gated on §SHIP-V4) → P70 (GitHub front-porch + Kaan-felt landing-page sign-off). Under `gsd-autonomous fully`, OSS-04 routes to §SHIP-V4 if signatures haven't landed at execution; the other 18 REQ-IDs ship unblocked.*

*Roadmap extended 2026-05-25 for v8.1 "One Mind" — **6 phases (77–82)** continuing numbering from v8.0 (which ran 71–76) — NO reset. 18 v8.1 REQ-IDs mapped to exactly one phase (100% coverage, no orphans, no duplicates): WIRE-01..06 → P77 (6; WIRE-02 `ccf4930` + WIRE-03 `a9979b8` already SHIPPED — placed in P77, marked DONE, no new work) · PERCEIVE-01..03 → P78 (3) · LENS-01..02 → P79 (2) · GROUND-01..02 → P80 (2) · BENCH-01..03 → P81 (3) · CURATE-01..02 → P82 (2). **Hard scope rule (locked):** ship-not-over-engineer (one connected, tested wire per phase) · Gemini-only · NO new MIR libraries / NO new DSP detectors · no new ws ports / no new IPC envelopes · the four cardinal invariants (single-writer / citation-grounding / trust-the-audio / one-socket) hold by ADDITIVE design (gated-off cold path byte-identical to the v8.0 baseline) · honest green (unit-testable without the API; live e2e on the funded key). Dependency spine: P77 (WIRE) → P78 (PERCEIVE) → P79 (LENS) ‖ P80 (GROUND) → P81 (BENCH — depends on GROUND + LENS being in place to bench them) → P82 (CURATE). Under `gsd-autonomous fully`, blockers (Gemini billing — resolved; any live-hardware ear-pass) ride forward to KAAN-ACTION — they never block. Charter: `.planning/archive/2026-05-27-stale-one-mind-research/one-mind-charter.md`.*

*Roadmap extended 2026-05-26 for v8.2 "Set Builder" — **6 phases (83–88)** continuing numbering from v8.1 (which ran 77–82) — NO reset. 13 v8.2 REQ-IDs mapped to exactly one phase (100% coverage, no orphans, no duplicates): ENERGY-01/02/03 → P83 · DISCOVER-01/02/03 → P84 · SEQUENCE-01/02/03 → P85 · EXPORT-01/02 → P86 · AGENT-01/02 → P87 · UI-01/02 → P88. **Hard scope rule (locked):** Mode A library-local ONLY (public catalog / affiliate / fingerprint / XGBoost / scraping / Serato+Engine+Traktor export all DEFER → Bravoh-commercial or later) · Gemini conversational brain/TTS · local Codex for demo/test set-prep/chat · CLAP ONNX local embeddings · sqlite-vec local · no extra Set-Builder deps beyond the approved CLAP/onnxruntime/tokenizers stack · grounding seen-set gate (Invariant #2) UNCHANGED · new modules dim-agnostic over current 512D CLAP vectors/future D · honest-green offline-unit-testable engine modules · the live `cargo tauri dev` + `ui.log` button-audit is a HARD gate for P88. Shared-tree discipline applies around CLAP/CueAnchor/metadata ownership. Dependency spine: (P83 ENERGY ∥ P84 DISCOVER, independent) → P85 SEQUENCE (DISCOVER pool + optional ENERGY curve fidelity, degrades to BPM proxy) ‖ P86 EXPORT (independent of SEQUENCE internals) → P87 AGENT (orchestrates the three tools, on the no-hang harness + shared lens) → P88 UI ("Build a Set" path, frontend-enforcement applies). Under `gsd-autonomous fully`, blockers (live ear-pass, Apple/SignPath signature clock) ride forward to KAAN-ACTION. Charter: `.planning/research/vibe-mix-agent-engine-synthesis.md`; implementation research: `.planning/research/vibe-mix-engine-research.md`; UI/IPC seams: `.planning/research/vibe-mix-ui-ipc-button-audit.md`.*
