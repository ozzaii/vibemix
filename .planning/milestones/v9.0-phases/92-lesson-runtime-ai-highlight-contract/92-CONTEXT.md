# Phase 92: Lesson Runtime + AI Highlight Contract — Context

**Gathered:** 2026-05-28
**Status:** Ready for planning
**Mode:** Smart discuss (auto-accepted recommended defaults per `gsd-autonomous fully`); decisions cross-checked against `.planning/research/SUMMARY.md` (14 LOCKED axes — §1 phase concern matrix · §4 12 envelopes · §6 persona reuse · §9 persistence · §10 tone/slop gate).

<domain>
## Phase Boundary

P92 ships the **lesson runtime + AI highlight contract**: the LessonRuntime state machine, the remaining 11 `ipc.learn.*` envelopes (P91 landed 2 of the 12), the AI tutor persona wiring via `MOOD_PERSONAS["teacher"]`, the lesson progress JSON, and the "hello world" 1-step lesson that runs end-to-end (AI says "press play on deck A" → highlight glows on rendered play button via CSS-variable swap → user presses physical play → lesson advances).

This phase **lands all 4 cardinal-invariant pins for v9.0**:
1. **Single-writer #1**: `LessonRuntime` is sole writer of `LearnState`. AST gate `tests/learn/test_runtime_invariants.py` greps `src/vibemix/learn/` for ANY write to `MusicState` / `ControllerState` (zero matches required).
2. **One-socket #4**: All 11 new envelopes ride existing ws:8765. AST gate `tests/learn/test_no_new_ws_port.py` (already green from P91, must stay green).
3. **Tone fixture lock**: `tests/learn/test_tutor_system_instruction_lock.py` AST-greps for the 4 forbidden tutor moves (NO complimenting / NO summarizing / NO previewing / NO upbeat-hook closer).
4. **IPC schema lock**: All 11 new envelopes have `additionalProperties: false`; ajv validator regenerated; `scripts/check_ipc_schema.py` count parity green.

**REQ-IDs delivered:** TONE-02, TONE-04, LESSON-01, LESSON-02, LESSON-03, LESSON-04, LESSON-05, LESSON-06, RENDER-04 (highlight paint).

**Out of scope:**
- Course 1 / 2 / 3 lesson scripts → P94 / P95 / P96 (only the "hello world" 1-step lesson lives here)
- Verbatim opening dialog byte-equality test → P94 (`tests/learn/test_opening_dialog_byte_equality.py`)
- `check_no_tutor_slop.py` v2 blocklist → P94 (extends existing `check_no_ai_slop.py`)
- Exemplar engine + `[exemplar:]` evidence source → P93 (parallelizable, but P92 wires the `exemplar_play` / `exemplar_stop` envelope shapes only)
- Course 3 `[cue:<anchor_id>]` evidence source → P96 (conditional)
- Mode picker on main window + verbatim opening dialog UX → P97
- BlackHole / Multi-Output wizard discharge → P97 KAAN-ACTION

</domain>

<decisions>
## Implementation Decisions

### LessonRuntime architecture (LOCKED per SUMMARY §1 + Pitfalls PERSISTENCE)

- **State machine library:** `python-statemachine ^3.1.2` — ONE new MIT pure-Python dep (~30 KB). GREEN install impact (no transitive deps, no native code). Add to `pyproject.toml` `[tool.uv.dependencies]`.
- **Module home:** `src/vibemix/learn/runtime.py` (NEW) — declares `LessonRuntime` class. Each lesson = ONE state. Transitions are declarative entry/exit predicates.
- **Single-writer guarantee:** `LessonRuntime` is the SOLE writer of `LearnState` (a new dataclass in `src/vibemix/learn/state.py` — NEW; sibling of `runtime.py`). AST gate `tests/learn/test_runtime_invariants.py` enforces this with a static grep for `MusicState\.` / `ControllerState\.` assignments inside `src/vibemix/learn/`.
- **Read path:** `LessonRuntime` reads from `MidiMirror.snapshot()` (already shipped P91) + `ControllerState.deck_snapshot()` (already shipped). It WRITES only to `LearnState`.

### 12 IPC envelopes (LOCKED per SUMMARY §4 + Invariant #4)

- **2 already shipped in P91:** `ipc.learn.controller_detected`, `ipc.learn.midi_position`.
- **11 NEW envelopes in this phase:**
  1. `ipc.learn.start_course` (shell→sidecar) — `{course_id, controller_id}`
  2. `ipc.learn.start_lesson` (shell→sidecar) — `{lesson_id, level}` (skip into specific lesson)
  3. `ipc.learn.complete_lesson` (bidirectional) — user skip or system advance
  4. `ipc.learn.lesson_loaded` (sidecar→shell) — lesson active + HUD metadata
  5. `ipc.learn.highlight` (sidecar→shell) — `{control_id, deck, cue_color, cue_shape, annotation, expected_action}` — glow a control on the rendered SVG
  6. `ipc.learn.advance` (bidirectional) — tutor-confirms-MIDI OR user skip
  7. `ipc.learn.ack` (shell→sidecar) — user touched physical control OR clicked SVG
  8. `ipc.learn.tutor_speak` (sidecar→shell) — `{text, tts_marker, citations}` — narration
  9. `ipc.learn.exemplar_play` (sidecar→shell) — exemplar audio playback started (shape only; engine in P93)
  10. `ipc.learn.exemplar_stop` (sidecar→shell) — exemplar playback ended (shape only)
  11. `ipc.learn.progress_state` (bidirectional) — snapshot of courses + lessons completed
- All envelopes ride existing `127.0.0.1:8765`. Python dataclasses extend `src/vibemix/ui_bus/learn_messages.py` (already shipped P91 with 2 dataclasses). JSON Schema additions extend `tauri/ui/src/ipc/messages.schema.json`. TS types regenerate via `cd tauri/ui && npm run codegen:ipc` MANDATORY.
- All 11 carry `additionalProperties: false`. CI gate `scripts/check_ipc_schema.py` count parity must stay green (wrappers ↔ oneOf entries).

### Highlight paint contract (LOCKED per SUMMARY §5 + UI-SPEC §Motion)

- **CSS-variable swap on `<g data-control-id>`:** `--learn-highlight: var(--cdj-amber-2)` slot already scaffolded in P91 SVGs via `data-cue-color` + `data-cue-shape` attribute slots. P92 wires `ipc.learn.highlight` consumers to set the CSS custom property + animate the pulse-ring shape.
- **≤16 ms paint budget:** composited (no full SVG re-render). Pinned by `tauri/ui/tests/learn/highlight-paint.test.ts` (NEW).
- **Dual-channel cue:** color (`cue_color: "amber" | "warning"`) + shape (`cue_shape: "pulse-ring" | "static-glow"`). Empty slots from P91 get populated.

### Tutor persona (LOCKED per SUMMARY §6 + Pitfalls TONE)

- **Reuse `MOOD_PERSONAS["teacher"]`** from `src/vibemix/prompts/matrix.py:53-66` (v8.1 LENS-03). NO new lens.
- **System instruction composition** (NEW helper in `src/vibemix/learn/prompts.py`):
  - `build_tutor_system_instruction(course_id, lesson_id, controller_id)` returns:
    - `COURSE_FRAMES[course_id]` (NEW const in `src/vibemix/learn/curriculum.py`)
    - + `controller_frame` (NEW — derived from `midi/registry::find_mapping(controller_id)`)
    - + `CURRICULUM[lesson_id].system_instruction_addendum` (≤200 chars; NEW const in same `curriculum.py`)
    - + base tutor lens system instruction (from `MOOD_PERSONAS["teacher"]`)
- **Tutor system instruction lock** (`tests/learn/test_tutor_system_instruction_lock.py` — NEW):
  - AST-greps for the 4 forbidden tutor moves in the system instruction:
    1. NO complimenting user actions (e.g. "Great question!", "Nice job!")
    2. NO summarizing what just happened
    3. NO previewing what's next
    4. NO closing with an upbeat hook
  - The actual forbidden-tokens list lives in `scripts/launch/check_no_tutor_slop.py` (P94 lands this — for P92, use the locked system instruction string itself as the asserting fixture).
- **All AI dialog flows through `vibemix.llm.model_router.resolve("standard")`** → Gemini Flash. Zero hardcoded model literals. CI grep-gated (existing `tests/llm/test_model_router_no_inline_literals.py`).

### Hand-authored scripts (LOCKED per SUMMARY §10)

- **Lesson scripts are HAND-AUTHORED JSON fixtures**, NOT LLM-generated on the fly.
- **For P92, only the "hello world" 1-step lesson script ships:** `src/vibemix/learn/transcripts/hello_world/01_press_play.json` (NEW). Course 1-3 (36 lessons total) hand-authored in P94/P95/P96.
- **AI adds only ONE grounded interjection per beat.** The `tutor_speak` envelope's `text` field is ALWAYS read from the JSON fixture; AI only fills in grounding citations.
- **Static gate** `tests/learn/test_scripts_are_fixtures.py` (NEW) — AST-grep `src/vibemix/learn/` for any `generate_content` / `tutor_speak` builder that synthesizes the `text` field at runtime (zero allowed).

### Lesson advancement + accessibility (LOCKED per SUMMARY §1 PEDAGOGY + UAT)

- **Expected action match:** Lesson advances when user performs the expected MIDI action — CC drop ≥30% of range OR button press matching `expected_action.control` + `direction`.
- **3-strike progressive hint surface:** After 3 ungated frames or 30 s, the highlight grows + the tutor offers a hint. Hints are pre-authored in the JSON fixture (NOT live-generated).
- **"I got it" skip override:** Always available (motor-impaired-safe — NO time-pressure on any lesson).
- **Anti-speedrun min-dwell ≥45 s:** Prevents click-through gaming of lesson advancement. Lesson cannot complete in less than 45 s wall-clock.

### Progress persistence (LOCKED per SUMMARY §9)

- **File path:** `~/.cache/vibemix/learn-progress.json` (atomic write via `os.replace`; privacy-fixture-tested pattern from v3.1 — see existing `src/vibemix/recordings/storage.py` for the atomic pattern).
- **Schema-versioned:** `{schema_version: 1, courses: {...}, lessons: {...}}`. Corruption → nuke + emit fresh empty + one-line toast.
- **Reset CLI:** `vibemix learn reset` (NEW subcommand). Wires through existing `src/vibemix/cli/main.py` (or wherever the CLI dispatch lives).
- **"Reset Learn Progress" button** in the EXISTING settings drawer (`tauri/ui/src/settings/SettingsDrawer.ts`). New row in the drawer; click → ipc envelope (reuse one of the existing settings.* envelopes OR add `ipc.learn.progress_state` reset path). Decision: extend `progress_state` envelope with `{action: "reset" | "snapshot"}`.

### Claude's Discretion

- Exact state machine transition predicates inside `LessonRuntime` — match the lesson script's `expected_action` semantics.
- Exact `LearnState` dataclass shape — must capture current course / current lesson / progress-per-lesson / 3-strike hint counter / wall-clock dwell.
- Exact `tauri/ui/src/learn/lesson/` directory layout — sub-components for HUD, tutor-speak bubble, hint overlay.
- Exact wiring of the `Reset Learn Progress` button — settings drawer extension pattern.

</decisions>

<code_context>
## Existing Code Insights

### Reusable assets
- `src/vibemix/prompts/matrix.py:53-66` — `MOOD_PERSONAS["teacher"]` (v8.1 LENS-03 — REUSE, NO new lens)
- `src/vibemix/llm/model_router.py::resolve("standard")` — Gemini Flash model resolution (NO hardcoded literals)
- `src/vibemix/learn/midi_mirror.py` — shipped P91, exposes `snapshot()` + `current_profile()` reads
- `src/vibemix/learn/__init__.py` — shipped P91 package marker
- `src/vibemix/ui_bus/learn_messages.py` — shipped P91 with 2 dataclasses (controller_detected, midi_position)
- `tauri/ui/src/ipc/messages.schema.json` — shipped P91 with 2 oneOf entries; add 11 more
- `tauri/ui/src/learn/components/controller-stage.ts` — shipped P91; consumes highlight envelope here
- `tauri/ui/src/learn/controllers/*.svg.ts` × 11 — shipped P91 with `data-cue-color` + `data-cue-shape` empty slots ready to populate
- `tauri/ui/src/settings/SettingsDrawer.ts` — existing drawer; extend with "Reset Learn Progress" row
- `src/vibemix/recordings/storage.py` — atomic-write pattern reference (`os.replace` for `learn-progress.json`)
- `tests/learn/test_no_new_ws_port.py` — shipped P91 (already green; must stay green)
- `tests/learn/test_no_pioneer_brand_marks.py` — shipped P91

### Established patterns
- IPC envelopes: Python dataclass → JSON Schema → ajv via codegen:ipc → TS types. The pattern is locked.
- AST gates: pytest tests that grep `src/vibemix/learn/` for forbidden patterns. Multiple precedents: `test_no_new_ws_port.py`, `test_no_pioneer_brand_marks.py`.
- Atomic file writes: `os.replace` pattern (see `recordings/storage.py`, `keychain.py`).
- CLI subcommands: dispatch through `src/vibemix/__main__.py` or `src/vibemix/cli/main.py`.

### Integration points
- Python sidecar: instantiate `LessonRuntime` in `__main__.main()` alongside `MidiMirror`. Hand to `ws_broadcast` for tick-driven snapshot.
- Tauri shell: no new commands needed — Learn webview already loads via `open_learn_window`.
- Frontend Learn webview: `learn-window.ts` ws-client consumes the 11 new envelopes. The HUD + tutor-speak bubble + hint overlay = new components under `tauri/ui/src/learn/lesson/` (NEW directory).
- Settings drawer: extend `SettingsDrawer.ts` with new row + ipc message.

### Concurrent-session discipline
- Same constraint as P91: commit by NAMED PATHS only. The P92 island includes:
  - NEW: `src/vibemix/learn/runtime.py`, `src/vibemix/learn/state.py`, `src/vibemix/learn/prompts.py`, `src/vibemix/learn/curriculum.py`, `src/vibemix/learn/progress.py`, `src/vibemix/learn/transcripts/hello_world/01_press_play.json`, `tauri/ui/src/learn/lesson/` (multiple component files), `tests/learn/test_runtime_invariants.py`, `tests/learn/test_tutor_system_instruction_lock.py`, `tests/learn/test_scripts_are_fixtures.py`, `tauri/ui/tests/learn/highlight-paint.test.ts`.
  - SHARED (solo+sequential): `pyproject.toml` (+1 dep), `tauri/ui/src/ipc/messages.schema.json` (+11 envelopes), `tauri/ui/src/ipc/validator.generated.mjs` (codegen output), `src/vibemix/ui_bus/learn_messages.py` (+11 dataclasses), `src/vibemix/__main__.py` (LessonRuntime wiring), `src/vibemix/runtime/ws_bus.py` (optional 11-envelope drain extension if needed), `tauri/ui/src/learn/learn-window.ts` (consume new envelopes), `tauri/ui/src/learn/components/controller-stage.ts` (highlight paint), `tauri/ui/src/settings/SettingsDrawer.ts` (reset button).

</code_context>

<specifics>
## Specific Ideas

- The "hello world" 1-step lesson script: `{lesson_id: "L0.00-press-play", title: "Press play on deck A", system_instruction_addendum: "Wait for the user to press deck A's play button. Do not narrate over them.", tutor_speak: [{text: "Find deck A's play button — it's lit up on your controller.", tts_marker: "cue-001"}, ...], expected_action: {control: "transport:play", deck: "A", direction: "down"}, hints: [{strike: 1, text: "..."}, {strike: 2, text: "..."}, {strike: 3, text: "..."}]}`.
- This is THE end-to-end demo. The 1-step lesson + the press-play highlight + the AI saying "press play" + the user's FLX4 play button advancing the lesson = P92 is shippable.

</specifics>

<deferred>
## Deferred Ideas

- 36 Course 1-3 lesson scripts → P94 (16 anatomy) / P95 (14 transitions) / P96 (6 play-mode + tutor lens proactive)
- Verbatim opening dialog (Kaan's iconic 4-line) byte-equality test → P94
- `check_no_tutor_slop.py` v2 blocklist (≥20 tutor-tic tokens) → P94
- Exemplar engine + `[exemplar:]` evidence source (4-site schema mirror) → P93 (parallelizable with P92)
- `ExemplarPlayer` + dedicated `sd.OutputStream` → P93
- Course 3 `[cue:<anchor_id>]` evidence source (4-site mirror) → P96 conditional
- Headphone device picker in onboarding wizard → P97
- Mode picker on main window → P97
- Live audit / Kaan ear-pass / rc1 regression smoke → P98

</deferred>
