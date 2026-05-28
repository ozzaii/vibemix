# Phase 92: Lesson Runtime + AI Highlight Contract — Research

**Researched:** 2026-05-28
**Domain:** Deterministic lesson FSM + 11 IPC envelopes + AI tutor system-instruction composition + atomic JSON persistence + ≤16 ms CSS-variable highlight paint
**Confidence:** HIGH on engineering spine (every file:line in-tree). HIGH on `python-statemachine 3.1.2` (verified on PyPI: pure-Python MIT, ~30 KB, no transitive runtime deps). MEDIUM on tutor-tone discipline at the system-instruction level (TONE-04 is fixture-locked but mature ear-pass coverage waits for P94). LOW only on the `learn_tutor` model-router path name (CONTEXT.md says `resolve("standard")`, but `_router_config._ROUTES` has no `"standard"` key — see Open Q1 below; treat as a name to be ratified by the planner).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**LessonRuntime architecture (per SUMMARY §1 + Pitfalls PERSISTENCE):**
- State machine library: `python-statemachine ^3.1.2` — ONE new MIT pure-Python dep (~30 KB). GREEN install impact (no transitive deps, no native code). Add to `pyproject.toml` `[tool.uv.dependencies]`.
- Module home: `src/vibemix/learn/runtime.py` (NEW) — declares `LessonRuntime` class. Each lesson = ONE state. Transitions are declarative entry/exit predicates.
- Single-writer guarantee: `LessonRuntime` is the SOLE writer of `LearnState` (a new dataclass in `src/vibemix/learn/state.py` — NEW; sibling of `runtime.py`). AST gate `tests/learn/test_runtime_invariants.py` enforces this with a static grep for `MusicState\.` / `ControllerState\.` assignments inside `src/vibemix/learn/`.
- Read path: `LessonRuntime` reads from `MidiMirror.snapshot()` (already shipped P91) + `ControllerState.deck_snapshot()` (already shipped). It WRITES only to `LearnState`.

**12 IPC envelopes (per SUMMARY §4 + Invariant #4):**
- 2 already shipped in P91: `ipc.learn.controller_detected`, `ipc.learn.midi_position`.
- 11 NEW envelopes in this phase: `start_course`, `start_lesson`, `complete_lesson`, `lesson_loaded`, `highlight`, `advance`, `ack`, `tutor_speak`, `exemplar_play`, `exemplar_stop`, `progress_state`.
- All envelopes ride existing `127.0.0.1:8765`. Python dataclasses extend `src/vibemix/ui_bus/learn_messages.py`. JSON Schema additions extend `tauri/ui/src/ipc/messages.schema.json`. TS types regenerate via `cd tauri/ui && npm run codegen:ipc` MANDATORY.
- All 11 carry `additionalProperties: false`. CI gate `scripts/check_ipc_schema.py` count parity must stay green (wrappers ↔ oneOf entries).

**Highlight paint contract (per SUMMARY §5 + UI-SPEC §Motion):**
- CSS-variable swap on `<g data-control-id>`: `--learn-highlight: var(--cdj-amber-2)` slot already scaffolded in P91 SVGs via `data-cue-color` + `data-cue-shape` attribute slots. P92 wires `ipc.learn.highlight` consumers to set the CSS custom property + animate the pulse-ring shape.
- ≤16 ms paint budget: composited (no full SVG re-render). Pinned by `tauri/ui/tests/learn/highlight-paint.test.ts` (NEW).
- Dual-channel cue: color (`cue_color: "amber" | "warning"`) + shape (`cue_shape: "pulse-ring" | "static-glow"`). Empty slots from P91 get populated.

**Tutor persona (per SUMMARY §6 + Pitfalls TONE):**
- Reuse `MOOD_PERSONAS["teacher"]` from `src/vibemix/prompts/matrix.py:60-73` (v8.1 LENS-03). NO new lens.
- System instruction composition (NEW helper in `src/vibemix/learn/prompts.py`): `build_tutor_system_instruction(course_id, lesson_id, controller_id)` = `COURSE_FRAMES[course_id]` + `controller_frame` + `CURRICULUM[lesson_id].system_instruction_addendum` (≤200 chars) + base tutor lens system instruction (from `MOOD_PERSONAS["teacher"]`).
- Tutor system instruction lock (`tests/learn/test_tutor_system_instruction_lock.py` — NEW): AST-greps for the 4 forbidden tutor moves: (1) NO complimenting user actions, (2) NO summarizing what just happened, (3) NO previewing what's next, (4) NO closing with an upbeat hook.
- All AI dialog flows through `vibemix.llm.model_router.resolve(...)`. Zero hardcoded model literals. CI grep-gated (existing `tests/llm/test_model_router_no_inline_literals.py`). **See Open Q1: CONTEXT.md cites `resolve("standard")`, but `_router_config._ROUTES` exposes `"live_coach"` / `"debrief"` / `"library_auto_tag"` — no `"standard"` path. Planner ratifies whether to (a) reuse `"live_coach"`, (b) add a new `"learn_tutor"` path to `_router_config._ROUTES`, or (c) rename one of the existing paths.**

**Hand-authored scripts (per SUMMARY §10):**
- Lesson scripts are HAND-AUTHORED JSON fixtures, NOT LLM-generated on the fly.
- For P92, only the "hello world" 1-step lesson script ships: `src/vibemix/learn/transcripts/hello_world/01_press_play.json` (NEW). Course 1-3 (36 lessons total) hand-authored in P94/P95/P96.
- AI adds only ONE grounded interjection per beat. The `tutor_speak` envelope's `text` field is ALWAYS read from the JSON fixture; AI only fills in grounding citations.
- Static gate `tests/learn/test_scripts_are_fixtures.py` (NEW) — AST-grep `src/vibemix/learn/` for any `generate_content` / `tutor_speak` builder that synthesizes the `text` field at runtime (zero allowed).

**Lesson advancement + accessibility (per SUMMARY §1 PEDAGOGY + UAT):**
- Expected action match: Lesson advances when user performs the expected MIDI action — CC drop ≥30% of range OR button press matching `expected_action.control` + `direction`.
- 3-strike progressive hint surface: After 3 ungated frames or 30 s, the highlight grows + the tutor offers a hint. Hints are pre-authored in the JSON fixture (NOT live-generated).
- "I got it" skip override: Always available (motor-impaired-safe — NO time-pressure on any lesson).
- Anti-speedrun min-dwell ≥45 s: Prevents click-through gaming of lesson advancement. Lesson cannot complete in less than 45 s wall-clock.

**Progress persistence (per SUMMARY §9):**
- File path: `~/.cache/vibemix/learn-progress.json` (atomic write via `os.replace`; privacy-fixture-tested pattern — see existing `src/vibemix/runtime/config_store.py:266-278` and `src/vibemix/profile/storage.py:78-92` for the atomic pattern).
- Schema-versioned: `{schema_version: 1, courses: {...}, lessons: {...}}`. Corruption → nuke + emit fresh empty + one-line toast.
- Reset CLI: `vibemix learn reset` (NEW subcommand). Wires through existing CLI dispatch.
- "Reset Learn Progress" button in the EXISTING settings drawer (`tauri/ui/src/settings/SettingsDrawer.ts`). New row in the drawer; click → `ipc.learn.progress_state { action: "reset" }` envelope.

### Claude's Discretion

- Exact state machine transition predicates inside `LessonRuntime` — match the lesson script's `expected_action` semantics.
- Exact `LearnState` dataclass shape — must capture current course / current lesson / progress-per-lesson / 3-strike hint counter / wall-clock dwell.
- Exact `tauri/ui/src/learn/lesson/` directory layout — sub-components for HUD, tutor-speak bubble, hint overlay.
- Exact wiring of the `Reset Learn Progress` button — settings drawer extension pattern (matches `MascotGroup` / `HelpGroup` / `PerformanceGroup` precedent at `SettingsDrawer.ts:913-927`).

### Deferred Ideas (OUT OF SCOPE)

- Course 1 / 2 / 3 lesson scripts → P94 / P95 / P96
- Verbatim opening dialog byte-equality test → P94 (`tests/learn/test_opening_dialog_byte_equality.py`)
- `check_no_tutor_slop.py` v2 blocklist → P94
- Exemplar engine + `[exemplar:]` evidence source → P93 (parallelizable, but P92 wires the `exemplar_play` / `exemplar_stop` envelope SHAPES only)
- Course 3 `[cue:<anchor_id>]` evidence source → P96 (conditional)
- Mode picker on main window + verbatim opening dialog UX → P97
- BlackHole / Multi-Output wizard discharge → P97 KAAN-ACTION

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| **TONE-02** | Every lesson script is HAND-AUTHORED (committed to `src/vibemix/learn/transcripts/...`) and NEVER LLM-generated on-the-fly; static test (`tests/learn/test_scripts_are_fixtures.py`) confirms no live generative call writes a `tutor_speak` envelope's `text` field. | §Architecture Pattern 8 (lesson script JSON fixture), §AST gates §"static fixture grep". |
| **TONE-04** | The tutor system instruction includes a hard lock forbidding the four learned moves: NO complimenting / NO summarizing / NO previewing / NO upbeat-hook closer. Pinned by `tests/learn/test_tutor_system_instruction_lock.py`. | §Architecture Pattern 6 (system-instruction composition), §AST gates §"tutor 4-moves lock". |
| **LESSON-01** | LessonRuntime drives lesson state via `python-statemachine` ^3.1.2 FSM; each lesson is one state; `tests/learn/test_runtime_invariants.py` confirms ZERO writes to `MusicState` from `learn/`. | §Standard Stack (`python-statemachine` ^3.1.2 verified), §Architecture Pattern 1 (LessonRuntime skeleton), §Architecture Pattern 2 (LearnState single-writer). |
| **LESSON-02** | 12 new IPC envelopes in `ipc.learn.*` namespace ride existing ws:8765 through `IpcRouterBus`; all `additionalProperties: false`; ajv regenerated. Python dataclasses extend `learn_messages.py`. CI gate `tests/learn/test_no_new_ws_port.py` (already green from P91). | §Architecture Pattern 3 (11 envelope schemas), §Code Examples §1-3 (full JSON Schema + Python dataclass). |
| **LESSON-03** | Progress persists at `~/.cache/vibemix/learn-progress.json` — schema-versioned, corruption-recovery (JSONDecodeError → nuke + emit fresh empty + one-line toast); pinned by `tests/learn/test_progress_persistence.py::test_corrupt_file_recovers_clean`. Reset CLI + drawer button. | §Architecture Pattern 7 (atomic persistence), §Code Example 4 (mirror of `config_store.save()` pattern). |
| **LESSON-04** | Advancement requires expected MIDI action (CC drop ≥30% range OR button press); 3-strike progressive hint surface; "I got it" override always available; anti-speedrun min-dwell ≥45 s. | §Architecture Pattern 1 (LessonRuntime guards + dwell), §Pitfall 4 (3-strike hint surface). |
| **LESSON-05** | Reuse `MOOD_PERSONAS["teacher"]` from `prompts/matrix.py:60-73` (NO new lens). Composes `build_tutor_system_instruction(course_id, lesson_id, controller_id)` = `COURSE_FRAMES[course_id]` + `controller_frame` + `CURRICULUM[lesson_id].system_instruction_addendum` (≤200 chars) + base tutor lens. | §Architecture Pattern 6 (system-instruction composition algorithm), §Code Example 5 (build_tutor_system_instruction skeleton). |
| **LESSON-06** | All AI dialog flows through Gemini Flash via `vibemix.llm.model_router.resolve(...)` (zero hardcoded model literals; CI grep-gated). | §Open Q1 (planner ratifies `learn_tutor` path vs `live_coach` reuse). |
| **RENDER-04** | An AI highlight glow paints on a rendered control within 16 ms of receiving the `ipc.learn.highlight` envelope, composited via CSS-variable swap (no full SVG re-render); pinned by `tauri/ui/tests/learn/highlight-paint.test.ts`. | §Architecture Pattern 5 (highlight paint wiring), §Code Example 6 (highlight-paint test harness). |

</phase_requirements>

## Project Constraints (from CLAUDE.md)

| Directive | Source | How P92 Honors |
|-----------|--------|----------------|
| **One-socket invariant (#4)** | CLAUDE.md §Architecture | 11 new envelopes ride ws:8765 — no second `websockets.serve`. CI gate `tests/learn/test_no_new_ws_port.py` (already green from P91). |
| **Single-writer invariant (#1)** | CLAUDE.md §Architecture | `LessonRuntime` is sole writer of `LearnState`. AST gate `tests/learn/test_runtime_invariants.py` greps `src/vibemix/learn/` for any `MusicState.*=` / `ControllerState.*=` assignment (zero matches required). |
| **Citation grounding (#2)** | CLAUDE.md §Architecture | Not directly enforced in P92 (no `[exemplar:]` evidence source yet — lands in P93). But `tutor_speak.citations` field SHAPE lands here; P93 populates. |
| **Trust the audio (#3)** | CLAUDE.md §Architecture | Not relevant for P92 (Course 3 concern, P96). |
| **No model literals — `model_router` only** | CLAUDE.md §Configuration | Tutor backend resolves via `resolve("learn_tutor")` (or whatever path the planner ratifies in Open Q1). Zero literal model strings in `learn/prompts.py` or `learn/runtime.py`. CI grep gate (`scripts/release/check_no_hardcoded_model.sh`) runs against new files. |
| **Frontend settings controls must repaint OPTIMISTICALLY** | CLAUDE.md §Conventions | The "Reset Learn Progress" row in the drawer follows the optimistic-paint rule: row click → immediately show "resetting…" state; flip to "done" on `progress_state { action: "reset_ack" }` envelope arrival. Don't wait for the round-trip to feel responsive. |
| **`codegen:ipc` mandatory after schema edit** | CLAUDE.md §Commands | `npm run codegen:ipc` is a REQUIRED step after the 11-envelope `messages.schema.json` edit. Plan must include it as a discrete task. |
| **`cargo tauri dev` = STALE frozen sidecar** | CLAUDE.md §Commands | Verify backend wiring by running `main()` on current source. Python edits in `learn/runtime.py` will NOT be picked up by `cargo tauri dev`'s bundled sidecar; use `python -m vibemix` for backend verification. Tauri-side via `tsc --noEmit` + `vite build` + `vitest run`. |
| **Concurrent sessions on `live-tuning-or-brain`** | CLAUDE.md §Project Skills + CONTEXT.md §code_context | Commit by NAMED paths only. Shared-file edits (`pyproject.toml`, `messages.schema.json`, `__main__.py`, `learn_messages.py`, `learn-window.ts`, `controller-stage.ts`, `SettingsDrawer.ts`) must be solo+sequential. New-file islands at `src/vibemix/learn/{runtime,state,prompts,curriculum,progress}.py`, `src/vibemix/learn/transcripts/`, `tauri/ui/src/learn/lesson/`, `tests/learn/test_*.py`. |
| **Frontend-enforcement skill rules (20/80, no Material, Saira/JetBrains Mono only)** | `.claude/skills/frontend-enforcement/SKILL.md` | UI-SPEC §Color hard-caps amber at 7 elements (P92 extends P91's 5 to 7); §Typography reuses P91 ramps; NO new tokens; NO Material chat-bubble overlay for tutor-speak (verified by §UI-SPEC Hardest UI question — REJECTED Option a). |
| **CodeGen sync — pre-compiled ajv validator** | `feedback_schema_edit_needs_codegen_ipc.md` | Plan MUST include `npm run codegen:ipc` as a discrete step after `messages.schema.json` edit. Tests will reject new envelope shapes without it. |

## Summary

P92 lands the **lesson runtime + AI highlight contract**: the `LessonRuntime` state machine (one Python dep — `python-statemachine` ^3.1.2 — pure Python, MIT, ~30 KB, GREEN install impact), the 11 new `ipc.learn.*` envelopes (P91 shipped 2; P92 ships the remaining 11), the AI tutor persona wiring via the existing `MOOD_PERSONAS["teacher"]` (NO new lens), the hand-authored JSON lesson script for the "hello world" 1-step lesson, `learn-progress.json` atomic persistence (`os.replace` pattern, mirror of `config_store.save()`), and a "Reset Learn Progress" row in the existing settings drawer (mirror of `MascotGroup` / `HelpGroup` pattern). This phase **lands all 4 cardinal-invariant pins for v9.0**: single-writer (`LessonRuntime` writes `LearnState` only), one-socket (11 envelopes ride existing ws:8765), tone fixture lock (`test_tutor_system_instruction_lock.py`), IPC schema lock (11 envelopes × `additionalProperties: false` × count parity).

The acid test for the phase: every new file lands inside `src/vibemix/learn/` or `tauri/ui/src/learn/lesson/` (4 new-file islands); shared files (`pyproject.toml`, `messages.schema.json`, `__main__.py`, `learn-window.ts`, `controller-stage.ts`, `SettingsDrawer.ts`, `learn_messages.py`) get solo-sequential additive edits; the AST gates run green; the highlight paint test measures ≤16 ms P95 in jsdom; the 11-envelope `npm run codegen:ipc` round-trips cleanly. The "hello world" 1-step lesson — AI says "press deck A play" → highlight pulses on the play button → user presses FLX4 play → lesson advances — is the shippable demo Kaan can ear-pass.

**Primary recommendation:** Use the `python-statemachine` `States are class attributes` + `transitions are class attributes` + `on_enter_<state>` / `on_exit_<state>` callback pattern verbatim (see Architecture Pattern 1 below). Compose `build_tutor_system_instruction` by APPENDING to the existing `build_system_instruction("intermediate", "coach", "teacher", include_citation_grammar=False, include_listening_fallback=False, include_tag_dsl=False)` result so the new lock-text lands AFTER the matrix cell — the four-forbidden-moves rule is the LAST thing the model reads (strongest recency, mirror of the `COACH_CLOSING_BLOCK` pattern at `matrix.py:241-251`). Mirror the `config_store.save()` atomic-write pattern (`tmp.write_text` → `os.replace`) for `learn-progress.json` so the corruption-recovery test is a straight copy of the existing test fixture. Extend the settings drawer via a new `LearnGroup` component file (mirror of `MascotGroup` at `mascot-group.ts`) that owns the "reset learn progress" row + confirm dialog, inserted between `RECORDING` and `MASCOT` per the existing group ordering at `SettingsDrawer.ts:909-927`.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Lesson FSM (state, transitions, guards, dwell counter) | **Python sidecar** (`src/vibemix/learn/runtime.py` — NEW) | — | Server-authoritative; same pattern as live co-host where Python owns state and TS renders. Mirrors the SUMMARY § "Python = state, TS = renderer + input ferry" decision. |
| `LearnState` mutation (sole writer = `LessonRuntime`) | **Python sidecar** (`src/vibemix/learn/state.py` — NEW) | — | Single-writer invariant. AST gate enforces zero non-`LessonRuntime` writes inside `learn/`. |
| Lesson script storage (JSON fixtures) | **Python sidecar** (`src/vibemix/learn/transcripts/hello_world/01_press_play.json` — NEW) | — | Hand-authored, NOT LLM-generated. Static `test_scripts_are_fixtures.py` greps for live generative writers in `learn/`. |
| Curriculum metadata (course frames, lesson titles, controller frames) | **Python sidecar** (`src/vibemix/learn/curriculum.py` — NEW) | — | Server-side dispatch table; consumed by `build_tutor_system_instruction()`. |
| Tutor system-instruction composition | **Python sidecar** (`src/vibemix/learn/prompts.py` — NEW) | — | Composed by Python before each tutor turn; reuses existing `MOOD_PERSONAS["teacher"]` via thin wrapper around `build_system_instruction(skill="intermediate", mode="coach", mood="teacher")`. |
| Tutor LLM call (Gemini Flash) | **Python sidecar** (model resolved via `vibemix.llm.model_router.resolve(...)`) | — | Same path as live co-host. Zero hardcoded model literals. Open Q1 documents the path-name ratification. |
| Progress persistence (`learn-progress.json`) | **Python sidecar** (`src/vibemix/learn/progress.py` — NEW) | — | Atomic write via `os.replace` mirroring `config_store.save()`. Schema-versioned + corruption-recovery + reset CLI. |
| 11 new IPC envelope serialization | **Python sidecar** (`src/vibemix/ui_bus/learn_messages.py` — EDIT, +11 dataclasses) | **Browser webview** (ajv via `validator.generated.mjs`) | Existing P91 pattern. Schema is the source of truth; both sides validate. |
| 11 new envelope schemas | **Both** (`tauri/ui/src/ipc/messages.schema.json` — EDIT, +11 oneOf entries + 11 definitions) | — | Same `additionalProperties: false` discipline as P91. |
| Lesson HUD (course chip + lesson title + progress dots + index) | **Browser webview** (`tauri/ui/src/learn/lesson/hud.ts` — NEW) | — | DOM mount on `ipc.learn.lesson_loaded`; passive consumer of envelopes. |
| Tutor-speak dock (active line + ghost lines + receipt rule + cite chip + skip) | **Browser webview** (`tauri/ui/src/learn/lesson/tutor-dock.ts` — NEW) | — | DOM mount on `ipc.learn.tutor_speak`; consumes text + tts_marker + citations. |
| Highlight paint (CSS-variable swap on `<g data-control-id>`) | **Browser webview** (extends `tauri/ui/src/learn/components/controller-stage.ts`) | — | ≤16 ms paint via attribute swap, no SVG re-render. Composited. |
| Skip button ("I got it") | **Browser webview** (`tauri/ui/src/learn/lesson/skip-button.ts` — NEW) | — | Always visible, low-ink at rest; emits `ipc.learn.complete_lesson { reason: "user_skip" }`; disabled until 45 s min-dwell elapsed. |
| Hint overlay (italic copy below active line) | **Browser webview** (inline in `tutor-dock.ts`) | — | Extends the SAME dock; no separate overlay. Triggered by `data-state="hint"` attribute set on the dock from `lesson_loaded.hint_state`. |
| Reset Learn Progress row | **Browser webview** (`tauri/ui/src/settings/components/learn-group.ts` — NEW) | — | Mirror of `MascotGroup` / `HelpGroup` pattern; emits `ipc.learn.progress_state { action: "reset" }`. |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard | Provenance |
|---------|---------|---------|--------------|------------|
| `python-statemachine` | `^3.1.2` (latest stable as of 2026-05-19; verified via `pip3 index versions python-statemachine` returning 3.1.2 at top) | Lesson FSM | Pure-Python MIT, declarative API, ~30 KB install. The standard Python FSM library; ~1.5k stars; bench-suitable for the small finite state graphs this phase needs. `_router_config._ROUTES`-style declarative dispatch tables map naturally. | `[VERIFIED: pypi registry — pip3 index versions returned 3.1.2 at top; slopcheck [OK] (run via slopcheck install python-statemachine; clean — naming-pattern note only)]` |
| `jsonschema` (Draft-07) | already pinned in `pyproject.toml` | Python-side envelope validation | Existing pattern in `ui_bus/messages.py` reused verbatim. | `[VERIFIED: in-tree, already shipping]` |
| `websockets` | already pinned in `pyproject.toml` | ws:8765 (one socket) | Existing pattern in `runtime/ws_bus.py`; not added. | `[VERIFIED: in-tree]` |
| `google-genai` | already pinned in `pyproject.toml` | Tutor LLM (Gemini Flash) via `vibemix.llm.model_router.resolve(...)` | Existing dep; same path as live co-host. | `[VERIFIED: in-tree]` |
| `ajv` | `^8.20` (already in `tauri/ui/package.json`) | Frontend ipc validation | Pre-compiled via `npm run codegen:ipc` — existing pattern, no new dep. | `[VERIFIED: in-tree]` |
| `vitest` + `jsdom` | `^2.1` / `^29.1.1` | Test framework + DOM environment | Existing P91 pattern; matches `highlight-latency.test.ts` shape. | `[VERIFIED: in-tree, package.json]` |

**ONE new Python dependency in P92: `python-statemachine ^3.1.2`.**

ZERO new JS deps. ZERO new Rust deps. ZERO new ws ports.

### Supporting

| Library | Version | Purpose | When to Use | Provenance |
|---------|---------|---------|-------------|------------|
| `playwright` | `^1.50` (already in `tauri/ui/package.json`) | Keyboard-nav + axe-core a11y tests (extends from P91) | The `test_hud_progress_dots_keyboard.spec.ts` and `test_keyboard_skip_reachable.spec.ts` test gates. | `[VERIFIED: in-tree, package.json devDeps]` |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `python-statemachine 3.1.2` | Plain class with `match self.state:` dispatch (no library) | Loses declarative `on_enter_<state>` / `on_exit_<state>` introspection + free graph-visualization. For 36 lesson states × 4 transitions, the explicit state-machine library pays back its own cost. **REJECTED — Pitfall PERSISTENCE recommends declarative FSM.** |
| `python-statemachine 3.1.2` | `transitions` library | Slightly larger surface area (~150 KB vs ~30 KB), no clear feature win for our needs. **REJECTED — install impact.** |
| `python-statemachine 3.1.2` | `xstate` (JS, ship via Tauri) | Would put the FSM on the wrong tier (browser, not server). Lesson runtime must be authoritative in Python. **REJECTED — tier mismatch.** |
| New `learn_tutor` model-router path | Reuse `live_coach` path | Same model (Gemini Flash 3.5), zero cost. But two surfaces with different ServiceTier / different prompt envelopes risk subtle coupling. Adding a new path costs 1 line in `_router_config._ROUTES`. **RECOMMENDED — see Open Q1.** |
| Settings-drawer extension via NEW `LearnGroup` component file | Inline the row into `SettingsDrawer.ts` | The existing pattern (MascotGroup, HelpGroup, PerformanceGroup) is one component file per group, each exporting a render function. Inlining would diverge from convention. **REJECTED — match pattern.** |

**Installation:**
```bash
# Single new Python dep — add to pyproject.toml [tool.uv.dependencies] or [dependencies]:
#   "python-statemachine>=3.1.2,<4.0",
# Then:
uv sync --refresh
# Confirm:
uv run python -c "from statemachine import StateMachine; print('ok')"
```

**Version verification:**
```bash
pip3 index versions python-statemachine  # confirmed 3.1.2 latest, 2026-05-28
```

`[VERIFIED: pypi registry — package exists at version 3.1.2, MIT license, pure-Python wheel]`

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| `python-statemachine` | PyPI | First release 2015 (`0.1.0`); current `3.1.2` released 2026-05-19 — 11 years on registry | ~1M/month per PyPI download stats (mature, widely used) | `github.com/fgmacedo/python-statemachine` | `[OK]` (clean; slopcheck note: "Name starts with 'python-' — classic LLM naming pattern. Name looks like LLM bait but package is established.") | Approved |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

`python-statemachine` is mature, MIT-licensed, pure-Python, and the de facto standard Python FSM library. Provenance `[VERIFIED: pypi + slopcheck clean + source repo on GitHub since 2015]`.

## Architecture Patterns

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Python sidecar (src/vibemix/)                                                │
│                                                                              │
│  __main__.py:                                                                │
│    + from vibemix.learn.runtime import LessonRuntime                         │
│    + lesson_runtime = LessonRuntime(                                         │
│    +     learn_state=LearnState(),                                           │
│    +     midi_mirror=midi_mirror,             ← P91-shipped                  │
│    +     controller_state=midi_macos.controller_state,                       │
│    +     ipc_router=ipc_router,                                              │
│    + )                                                                       │
│    + asyncio.create_task(lesson_runtime.tick_loop(stop_event))               │
│                                                                              │
│  learn/runtime.py (NEW, ~250 lines):                                         │
│    class LessonRuntime(StateMachine):                                        │
│      # python-statemachine class attrs                                       │
│      idle = State(initial=True)                                              │
│      loaded = State()                                                        │
│      awaiting_action = State()                                               │
│      hint_strike_1 = State()                                                 │
│      hint_strike_2 = State()                                                 │
│      hint_strike_3 = State()                                                 │
│      advancing = State()                                                     │
│      completed = State(final=True)                                           │
│                                                                              │
│      load = idle.to(loaded) | completed.to(loaded)                           │
│      begin = loaded.to(awaiting_action)                                      │
│      strike = (                                                              │
│        awaiting_action.to(hint_strike_1)                                     │
│        | hint_strike_1.to(hint_strike_2)                                     │
│        | hint_strike_2.to(hint_strike_3)                                     │
│      )                                                                       │
│      ack_action = awaiting_action.to(advancing, cond="action_matches") | \   │
│                    hint_strike_1.to(advancing, cond="action_matches") | \    │
│                    hint_strike_2.to(advancing, cond="action_matches") | \    │
│                    hint_strike_3.to(advancing, cond="action_matches")        │
│      skip = ( ... all states except idle.to(advancing) )                     │
│      finish = advancing.to(completed, cond="min_dwell_elapsed")              │
│                                                                              │
│      def on_enter_loaded(self):                                              │
│        # Emit ipc.learn.lesson_loaded                                        │
│        self._emit(LearnLessonLoaded.make(...))                               │
│                                                                              │
│      def on_enter_awaiting_action(self):                                     │
│        # Emit ipc.learn.highlight + ipc.learn.tutor_speak (beat 0)           │
│        ...                                                                   │
│                                                                              │
│      def action_matches(self, midi_event) -> bool:                           │
│        # Per the lesson's expected_action: CC drop ≥30% OR button press      │
│        ...                                                                   │
│                                                                              │
│      def min_dwell_elapsed(self) -> bool:                                    │
│        return time.monotonic() - self.state.dwell_started_at >= 45.0         │
│                                                                              │
│      async def tick_loop(self, stop_event):                                  │
│        while not stop_event.is_set():                                        │
│          await asyncio.sleep(1.0)  # 1 Hz tick — checks strike timer + dwell │
│          if self.awaiting_action.is_active or self.hint_strike_*.is_active:  │
│            if dwell_since_state_entry >= 30: self.send("strike")             │
│                                                                              │
│  learn/state.py (NEW, ~60 lines):                                            │
│    @dataclass                                                                │
│    class LearnState:                                                         │
│      current_course_id: str | None = None                                    │
│      current_lesson_id: str | None = None                                    │
│      current_beat_index: int = 0                                             │
│      strike_count: int = 0                                                   │
│      dwell_started_at: float = 0.0                                           │
│      progress: dict[str, dict[str, str]] = field(default_factory=dict)       │
│                                                                              │
│  learn/curriculum.py (NEW, ~120 lines):                                      │
│    COURSE_FRAMES: dict[str, str] = {                                         │
│      "course_0": "Course 0 is the hello-world tutorial: one lesson.",        │
│      # P94/95/96 add course_1, course_2, course_3                            │
│    }                                                                         │
│    CURRICULUM: dict[str, LessonMeta] = {                                     │
│      "L0.00-press-play": LessonMeta(                                         │
│        title="press play",                                                   │
│        course_id="course_0",                                                 │
│        system_instruction_addendum="...",                                    │
│        transcript_path="hello_world/01_press_play.json",                     │
│      ),                                                                      │
│    }                                                                         │
│                                                                              │
│  learn/prompts.py (NEW, ~80 lines):                                          │
│    def build_tutor_system_instruction(course_id, lesson_id, controller_id):  │
│      base = build_system_instruction(                                        │
│        skill="intermediate", mode="coach", mood="teacher",                   │
│        include_citation_grammar=False,                                       │
│        include_listening_fallback=False,                                     │
│        include_tag_dsl=False,                                                │
│      )                                                                       │
│      frames = "\n\n".join([                                                  │
│        COURSE_FRAMES[course_id],                                             │
│        _controller_frame(controller_id),                                     │
│        CURRICULUM[lesson_id].system_instruction_addendum,                    │
│        _FORBIDDEN_TUTOR_MOVES_LOCK,                                          │
│      ])                                                                      │
│      return base + "\n\n" + frames                                           │
│                                                                              │
│  learn/progress.py (NEW, ~120 lines):                                        │
│    def load_progress() -> LearnProgress: ...                                 │
│    def save_progress(progress: LearnProgress) -> None:                       │
│      tmp.write_text(json.dumps(progress.to_dict()...))                       │
│      os.replace(tmp, target)  # atomic                                       │
│    def reset_progress() -> None: ...                                         │
│                                                                              │
│  learn/transcripts/hello_world/01_press_play.json (NEW):                     │
│    { lesson_id, title, system_instruction_addendum,                          │
│      tutor_speak: [...], expected_action: {...}, hints: [...] }              │
│                                                                              │
│  ui_bus/learn_messages.py (EDIT, +11 dataclasses):                           │
│    @dataclass class LearnStartCourse: ...                                    │
│    @dataclass class LearnStartLesson: ...                                    │
│    @dataclass class LearnCompleteLesson: ...                                 │
│    @dataclass class LearnLessonLoaded: ...                                   │
│    @dataclass class LearnHighlight: ...                                      │
│    @dataclass class LearnAdvance: ...                                        │
│    @dataclass class LearnAck: ...                                            │
│    @dataclass class LearnTutorSpeak: ...                                     │
│    @dataclass class LearnExemplarPlay: ...                                   │
│    @dataclass class LearnExemplarStop: ...                                   │
│    @dataclass class LearnProgressState: ...                                  │
└──────────────────────────────────▲──────────────────────────────────────────┘
                                   │ ws://127.0.0.1:8765 (the ONLY socket)
                                   │ 11 NEW frames + 2 P91 frames
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Learn webview (tauri/ui/src/learn/)                                          │
│                                                                              │
│  learn-window.ts (EDIT — handlers for 11 new envelope types):                │
│    on "ipc.learn.lesson_loaded" → mount LessonHud + TutorSpeakDock           │
│    on "ipc.learn.highlight" → call HighlightOverlay.apply(payload)           │
│    on "ipc.learn.tutor_speak" → call TutorSpeakDock.show(payload)            │
│    on "ipc.learn.advance" → animate ghost-recede + dot fill                  │
│    on "ipc.learn.complete_lesson" → progress dot fills + next lesson loads   │
│    on "ipc.learn.progress_state" → re-render HUD dots + (on reset_ack) toast │
│                                                                              │
│  learn/lesson/ (NEW directory):                                              │
│    hud.ts             ← LessonHud component (56px rail)                      │
│    tutor-dock.ts      ← TutorSpeakDock (bottom dock, hero-on-void)           │
│    skip-button.ts     ← LessonSkipButton ("i got it" + key-hint)             │
│                                                                              │
│  components/controller-stage.ts (EDIT — add HighlightOverlay.apply):         │
│    function applyHighlight(payload) {                                        │
│      const g = svg.querySelector(`[data-control-id="${payload.control_id}"]`)│
│      g.setAttribute("data-cue-color", payload.cue_color);                    │
│      g.setAttribute("data-cue-shape", payload.cue_shape);                    │
│      // The CSS-variable cascade (P91 scaffolded) does the paint in <16ms    │
│    }                                                                         │
│                                                                              │
│  settings/SettingsDrawer.ts (EDIT — insert LearnGroup):                      │
│    + body.append(LearnGroup());  // between RECORDING and MASCOT             │
│                                                                              │
│  settings/components/learn-group.ts (NEW, ~40 lines):                        │
│    export function LearnGroup(): HTMLElement {                               │
│      const row = button("reset learn progress" + secondary line);            │
│      row.click → renderConfirmDialog({ ... });                               │
│      return renderSettingsGroup({ header: "LEARN", children: [row] });       │
│    }                                                                         │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Recommended Project Structure

```
src/vibemix/
├── learn/                              # P91 island; P92 extends
│   ├── __init__.py                     # EDIT — export LessonRuntime
│   ├── midi_mirror.py                  # P91
│   ├── runtime.py                      # NEW — LessonRuntime (FSM)
│   ├── state.py                        # NEW — LearnState dataclass
│   ├── curriculum.py                   # NEW — COURSE_FRAMES + CURRICULUM
│   ├── prompts.py                      # NEW — build_tutor_system_instruction
│   ├── progress.py                     # NEW — atomic JSON persistence
│   └── transcripts/                    # NEW
│       └── hello_world/
│           └── 01_press_play.json      # NEW — the 1-step lesson script
└── ui_bus/
    └── learn_messages.py               # EDIT — +11 dataclasses

tauri/ui/
├── src/
│   ├── learn/
│   │   ├── learn-window.ts             # EDIT — 11 new envelope handlers
│   │   ├── components/
│   │   │   └── controller-stage.ts     # EDIT — applyHighlight method
│   │   └── lesson/                     # NEW directory
│   │       ├── hud.ts                  # NEW — LessonHud
│   │       ├── tutor-dock.ts           # NEW — TutorSpeakDock
│   │       └── skip-button.ts          # NEW — LessonSkipButton
│   ├── ipc/
│   │   ├── messages.schema.json        # EDIT — +11 oneOf entries + defs
│   │   ├── messages.ts                 # AUTO via codegen:ipc
│   │   └── validator.generated.mjs     # AUTO via codegen:ipc
│   └── settings/
│       ├── SettingsDrawer.ts           # EDIT — insert LearnGroup
│       └── components/
│           └── learn-group.ts          # NEW — Reset Learn Progress row
└── tests/learn/
    └── highlight-paint.test.ts         # NEW — ≤16 ms paint gate

tests/learn/
├── test_runtime_invariants.py          # NEW — AST gate (single-writer)
├── test_tutor_system_instruction_lock.py # NEW — 4-forbidden-moves lock
├── test_scripts_are_fixtures.py        # NEW — AST gate (no live LLM writes)
├── test_progress_persistence.py        # NEW — atomic + corruption recovery
├── test_lesson_runtime_smoke.py        # NEW — load → begin → ack → advance
└── test_advancement_gates.py           # NEW — 3-strike + min-dwell + skip

tests/ipc/
└── test_learn_envelope_parity_p92.py   # NEW — 11 new envelopes round-trip

pyproject.toml                          # EDIT — +1 dep (python-statemachine)
```

### Pattern 1: LessonRuntime — `python-statemachine` skeleton

**What:** `python-statemachine` classes use class-attribute syntax for states and transitions, callbacks via `on_enter_<state>` / `on_exit_<state>` methods, and guards via `cond=` arguments to transitions.

**When to use:** This is the canonical pattern from the upstream docs (verified via `python-statemachine` 3.1.2 docs at PyPI). For 36 lessons, the FSM is small enough to declare states explicitly (one per lesson would be ~150 states across all 36 lessons + per-lesson sub-states; instead, we use a SHARED set of states `idle / loaded / awaiting_action / hint_strike_{1,2,3} / advancing / completed` and let `LearnState.current_lesson_id` distinguish which lesson is active).

**Example:**
```python
# src/vibemix/learn/runtime.py — NEW
# SPDX-License-Identifier: Apache-2.0
"""LessonRuntime — deterministic FSM driving the lesson lifecycle.

Phase 92 (LESSON-01). Single-writer of LearnState (Invariant #1 binding).
NEVER writes MusicState or ControllerState — read-only consumer of both.

Threading: lives on the asyncio main loop (instantiated in __main__.main()).
The 1 Hz tick_loop coroutine drives the dwell timer + strike escalation.

States:
  idle           — no lesson active; LearnState.current_lesson_id is None.
  loaded         — lesson script loaded; HUD mounted; tutor beat 0 prepared.
  awaiting_action — highlight painted, waiting for user MIDI action.
  hint_strike_1  — first hint surfaced (after 30s of no action).
  hint_strike_2  — second hint surfaced (after another 30s).
  hint_strike_3  — third hint surfaced (last automatic prompt).
  advancing      — user matched action OR clicked "I got it"; sequencing
                   the dot-fill + tutor-line ghost-recede.
  completed      — final state for the lesson (45s+ wall-clock elapsed).

Transitions:
  load(lesson_id)     — idle | completed → loaded
  begin()             — loaded → awaiting_action
  strike()            — awaiting_action → hint_strike_1
                      | hint_strike_1 → hint_strike_2
                      | hint_strike_2 → hint_strike_3
  ack_action(midi)    — awaiting_action | hint_* → advancing
                        (guard: action_matches(midi))
  skip()              — awaiting_action | hint_* → advancing
                        (guard: min_dwell_elapsed())
  finish()            — advancing → completed
"""
from __future__ import annotations

import asyncio
import time
from typing import Any

from statemachine import State, StateMachine

from vibemix.learn.curriculum import CURRICULUM, COURSE_FRAMES
from vibemix.learn.state import LearnState
from vibemix.ui_bus.learn_messages import (
    LearnHighlight, LearnTutorSpeak, LearnLessonLoaded, LearnAdvance,
    LearnCompleteLesson, LearnProgressState,
)


class LessonRuntime(StateMachine):
    """Deterministic FSM for lesson lifecycle. Sole writer of LearnState."""

    # --- States (class attributes — python-statemachine convention) -------
    idle = State(initial=True)
    loaded = State()
    awaiting_action = State()
    hint_strike_1 = State()
    hint_strike_2 = State()
    hint_strike_3 = State()
    advancing = State()
    completed = State(final=True)

    # --- Transitions ------------------------------------------------------
    load = idle.to(loaded) | completed.to(loaded)
    begin = loaded.to(awaiting_action)
    strike = (
        awaiting_action.to(hint_strike_1)
        | hint_strike_1.to(hint_strike_2)
        | hint_strike_2.to(hint_strike_3)
    )
    # Guarded transition: only advances if `action_matches(midi)` is True.
    # python-statemachine evaluates cond= on each `send("ack_action", ...)`.
    ack_action = (
        awaiting_action.to(advancing, cond="action_matches")
        | hint_strike_1.to(advancing, cond="action_matches")
        | hint_strike_2.to(advancing, cond="action_matches")
        | hint_strike_3.to(advancing, cond="action_matches")
    )
    # Skip path — guarded ONLY by min-dwell (45 s anti-speedrun).
    skip = (
        awaiting_action.to(advancing, cond="min_dwell_elapsed")
        | hint_strike_1.to(advancing, cond="min_dwell_elapsed")
        | hint_strike_2.to(advancing, cond="min_dwell_elapsed")
        | hint_strike_3.to(advancing, cond="min_dwell_elapsed")
    )
    finish = advancing.to(completed)

    def __init__(
        self,
        *,
        learn_state: LearnState,
        midi_mirror: Any,  # P91 MidiMirror; passed for read-only snapshot
        controller_state: Any,  # P91 ControllerState; read-only
        ipc_router: Any,  # IpcRouterBus; emit_to_all path
        progress_store: Any,  # learn.progress.ProgressStore — atomic R/W
    ) -> None:
        self._learn = learn_state
        self._mirror = midi_mirror
        self._cs = controller_state
        self._ipc = ipc_router
        self._progress = progress_store
        self._state_entered_at = time.monotonic()
        super().__init__()

    # --- Guards (cond= predicates) ----------------------------------------
    def action_matches(self, midi: dict[str, Any] | None = None) -> bool:
        """Returns True iff the supplied MIDI event matches the lesson's
        expected_action (CC drop ≥30% range OR button press matching
        control + direction)."""
        if midi is None:
            return False
        lesson = CURRICULUM[self._learn.current_lesson_id]
        expected = lesson.script["expected_action"]
        # CC delta — only if expected is a CC control
        if expected.get("type") == "cc":
            cur = midi.get("value", 0)
            prev = midi.get("prev_value", cur)
            if abs(cur - prev) >= 38:  # 30% of 127 = 38.1
                return midi.get("control") == expected["control"]
        # Button press — direction "down" means CC value goes from 0 → >0
        if expected.get("type") == "button":
            return (
                midi.get("control") == expected["control"]
                and midi.get("direction") == expected["direction"]
            )
        return False

    def min_dwell_elapsed(self) -> bool:
        """≥45s wall-clock since lesson begin (anti-speedrun gate)."""
        return time.monotonic() - self._learn.lesson_started_at >= 45.0

    # --- Callbacks (on_enter_<state> / on_exit_<state>) -------------------
    def on_enter_loaded(self) -> None:
        self._learn.current_beat_index = 0
        self._learn.strike_count = 0
        self._learn.lesson_started_at = time.monotonic()
        lesson = CURRICULUM[self._learn.current_lesson_id]
        self._ipc.emit(LearnLessonLoaded.make(
            course_id=self._learn.current_course_id,
            lesson_id=self._learn.current_lesson_id,
            title=lesson.title,
            controller_id=self._learn.current_controller_id,
            progress_dots=self._progress.dots_for_course(
                self._learn.current_course_id
            ),
        ).to_dict())

    def on_enter_awaiting_action(self) -> None:
        lesson = CURRICULUM[self._learn.current_lesson_id]
        # Paint the highlight on the target control
        target = lesson.script["expected_action"]
        self._ipc.emit(LearnHighlight.make(
            control_id=target["control"],
            deck=target.get("deck", ""),
            cue_color="amber",
            cue_shape="pulse-ring",
            annotation=target.get("annotation", ""),
            expected_action=target,
        ).to_dict())
        # Speak beat 0
        self._emit_tutor_beat(0)
        self._state_entered_at = time.monotonic()

    def on_enter_hint_strike_1(self) -> None:
        self._learn.strike_count = 1
        self._emit_hint(1)
        self._state_entered_at = time.monotonic()

    def on_enter_hint_strike_2(self) -> None:
        self._learn.strike_count = 2
        self._emit_hint(2)
        self._state_entered_at = time.monotonic()

    def on_enter_hint_strike_3(self) -> None:
        self._learn.strike_count = 3
        self._emit_hint(3)
        self._state_entered_at = time.monotonic()

    def on_enter_advancing(self) -> None:
        self._ipc.emit(LearnAdvance.make(
            lesson_id=self._learn.current_lesson_id,
            reason="action_matched" if self._last_was_match else "user_skip",
        ).to_dict())
        # Schedule finish() — but only if min-dwell elapsed
        asyncio.create_task(self._finish_when_dwelled())

    async def _finish_when_dwelled(self) -> None:
        # Wait for min-dwell + a small settle for the UI advance animation
        remaining = max(0.0, 45.0 - (time.monotonic() - self._learn.lesson_started_at))
        await asyncio.sleep(remaining + 0.7)
        self.send("finish")

    def on_enter_completed(self) -> None:
        # Persist + emit complete_lesson
        self._progress.mark_completed(
            self._learn.current_course_id,
            self._learn.current_lesson_id,
        )
        self._ipc.emit(LearnCompleteLesson.make(
            lesson_id=self._learn.current_lesson_id,
            reason="completed",
        ).to_dict())
        self._ipc.emit(LearnProgressState.make(
            action="snapshot",
            progress=self._progress.snapshot(),
        ).to_dict())

    # --- 1 Hz tick loop ---------------------------------------------------
    async def tick_loop(self, stop_event: asyncio.Event) -> None:
        """Drives the 30-second strike escalation timer."""
        while not stop_event.is_set():
            await asyncio.sleep(1.0)
            cur = self.current_state.id
            if cur in ("awaiting_action", "hint_strike_1", "hint_strike_2"):
                elapsed_in_state = time.monotonic() - self._state_entered_at
                if elapsed_in_state >= 30.0 and self._learn.strike_count < 3:
                    self.send("strike")
```

**Source:** `python-statemachine` 3.1.2 docs (verified via PyPI; pattern lifted from official docs example). Pure-Python MIT license `[CITED: pypi.org/project/python-statemachine]`.

### Pattern 2: `LearnState` — single-writer dataclass

**What:** A frozen dataclass field-set capturing the runtime state of the active lesson. ONLY `LessonRuntime` writes; everything else reads.

**Example:**
```python
# src/vibemix/learn/state.py — NEW
# SPDX-License-Identifier: Apache-2.0
"""LearnState — single-writer dataclass for the lesson runtime.

Phase 92. Invariant #1 binding: ONLY LessonRuntime writes these fields.
AST gate `tests/learn/test_runtime_invariants.py` greps `src/vibemix/learn/`
for any `learn_state.<field> =` assignment outside `runtime.py` and fails red.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class LearnState:
    """Runtime state of the currently-active lesson + cached progress.

    NOTE: this dataclass is MUTABLE, not frozen — LessonRuntime writes its
    fields inside the on_enter_<state> callbacks. The single-writer
    invariant is enforced statically (grep gate), not by Python typing.
    """

    # The active course + lesson IDs (None when idle)
    current_course_id: str | None = None
    current_lesson_id: str | None = None
    current_controller_id: str | None = None  # set on lesson_loaded

    # Beat index inside the current lesson's tutor_speak sequence
    current_beat_index: int = 0

    # 0..3 — escalates via strike() transitions
    strike_count: int = 0

    # Wall-clock anchor for the 45s anti-speedrun gate
    lesson_started_at: float = 0.0
```

### Pattern 3: 11 IPC Envelope Schemas — full JSON Schema

**What:** The 11 NEW envelopes added to `tauri/ui/src/ipc/messages.schema.json`. All carry `additionalProperties: false`. All ride the existing ws:8765 socket.

**Example:** See **Code Example 1** below for the full JSON Schema for each of the 11 envelopes.

### Pattern 4: 3-Strike Progressive Hint Surface

**What:** Pre-authored hints in the lesson JSON; after 30 s of no expected action, escalate one strike at a time; visual = italic copy below the active tutor line + pulse-ring intensifies.

**When to use:** The lesson is in `awaiting_action` or `hint_strike_{1,2}` for ≥30 s.

**Wire:** `LessonRuntime.tick_loop()` polls 1 Hz; when `elapsed_in_state ≥ 30.0`, sends `strike`. `on_enter_hint_strike_{1,2,3}` reads the lesson's `hints[strike_index].text` and emits `LearnTutorSpeak` with a separate `data-state: "hint"` flag.

### Pattern 5: Highlight Paint Wiring (≤16 ms via CSS-variable swap)

**What:** The `ipc.learn.highlight` envelope arrives at the webview. The webview finds the target `<g data-control-id="<id>">` element, sets its `data-cue-color` and `data-cue-shape` attributes. The P91-scaffolded CSS rules at `learn.css:142-143` cascade the `var(--learn-highlight)` ⇒ `var(--amber)` via `currentColor` to all child fills/strokes; the `<g class="cue-shape">` slot lights the pulse-ring animation.

**Why ≤16 ms:** No SVG re-render. No new DOM node. Just two attribute mutations + the GPU compositor doing the gradient + animation. jsdom can simulate the attribute swap; production WebKit will hit closer to <8 ms.

**Implementation:**
```typescript
// tauri/ui/src/learn/components/controller-stage.ts — EDIT (additive)

export function applyHighlight(stage: HTMLElement, payload: {
  control_id: string;
  deck: string;
  cue_color: "amber" | "warning";
  cue_shape: "pulse-ring" | "static-glow";
}): void {
  // Clear any prior highlight first (preserves the receipt-rule pattern
  // where the previous lesson's highlight cleans on advance).
  stage.querySelectorAll<SVGGElement>("[data-cue-color]").forEach((g) => {
    g.removeAttribute("data-cue-color");
    g.removeAttribute("data-cue-shape");
  });
  // The data-control-id encoding follows P91: "<field>:<deck>" for deck-
  // bound, bare "<field>" for master-section. The envelope's `control_id`
  // is already in this format from the lesson script's expected_action.
  const targetId = payload.deck
    ? `${payload.control_id}:${payload.deck}`
    : payload.control_id;
  const target = stage.querySelector<SVGGElement>(
    `[data-control-id="${targetId}"]`,
  );
  if (!target) {
    console.warn(`[learn] highlight: control_id "${targetId}" not found`);
    return;
  }
  target.setAttribute("data-cue-color", payload.cue_color);
  target.setAttribute("data-cue-shape", payload.cue_shape);
}
```

**CSS already in P91's `learn.css`** (verified P91-RESEARCH §Pattern 5):
```css
.learn-stage svg [data-control-id][data-cue-color="amber"] {
  color: var(--learn-highlight);  /* channel 1: color (cascades via currentColor) */
}
.learn-stage svg [data-control-id][data-cue-shape="pulse-ring"] .cue-shape::before {
  /* channel 2: shape — animated stroke (P91 scaffolded, P92 lights) */
  content: "";
  position: absolute;
  inset: -4px;
  border: 4px solid var(--amber-65);
  border-radius: 50%;
  animation: learnPulseRing var(--motion-led-pulse) ease-in-out infinite;
}
```

### Pattern 6: Tutor System-Instruction Composition (TONE-04 binding)

**What:** Compose the tutor LLM system instruction from 4 parts: (1) the existing `MOOD_PERSONAS["teacher"]` lens (via `build_system_instruction`), (2) the `COURSE_FRAMES[course_id]` frame, (3) the `controller_frame(controller_id)` derived from the MIDI profile, (4) the per-lesson `system_instruction_addendum`, (5) the four-forbidden-moves lock as the FINAL block (strongest recency).

**Algorithm:**
```python
# src/vibemix/learn/prompts.py — NEW
# SPDX-License-Identifier: Apache-2.0
"""build_tutor_system_instruction — compose the tutor LLM instruction.

Phase 92. TONE-04 binding: the FORBIDDEN_TUTOR_MOVES_LOCK lands LAST so the
model reads it most recently (mirrors the COACH_CLOSING_BLOCK precedent at
prompts/matrix.py:241-251). The 4-moves block is the AST-gate target of
tests/learn/test_tutor_system_instruction_lock.py — change its tokens and
the test goes red.

LESSON-05 binding: reuses MOOD_PERSONAS["teacher"] via build_system_instruction
(mode="coach", mood="teacher") with the runtime-only blocks DISABLED
(no citation grammar, no fail-soft fragment, no TTS DSL) because the
tutor narration is a TEXT path inside the lesson — TTS is added in P93+.
"""
from __future__ import annotations

from vibemix.learn.curriculum import COURSE_FRAMES, CURRICULUM
from vibemix.midi.registry import find_mapping
from vibemix.prompts.matrix import build_system_instruction


# The four-forbidden-moves lock. TONE-04. AST-gated.
# Mirror pattern: matrix.py's COACH_CLOSING_BLOCK lands last for strongest
# recency. This block does the same job for tutor narration.
_FORBIDDEN_TUTOR_MOVES_LOCK: str = """
--- TUTOR DISCIPLINE (HARD LOCK — these four moves are forbidden) ---

You are a DJ tutor speaking to a beginner. You must NOT:

1. COMPLIMENT user actions. Do not say "great job", "nice", "awesome",
   "well done", "perfect", "you got it", "you crushed it", or any
   praise-tic. The user does not need your approval; they need your
   observation. State ONE grounded observation about what the audio /
   the controller did, and let the action speak for itself.

2. SUMMARIZE what just happened in lesson terms. Do not say "you just
   learned X", "you've now mastered X", "you just did X correctly".
   The lesson is not a quiz; the user is not a student being graded.
   State what you observed, never what they "learned".

3. PREVIEW what's next. Do not say "now let's", "next we'll", "coming
   up", "in the next lesson", "soon you'll", "later we'll". The user
   does not need a syllabus; they need the present beat. Stay in the
   moment.

4. CLOSE with an upbeat hook. Do not end a turn with "exciting, right?",
   "this is where it gets fun", "you're going to love this", or any
   marketing/edtech wrap-up. End with the observation. Stop talking.

State ONE grounded observation + at most ONE forward sentence the lesson
script provided. That is all. The lesson script is the spine; your
contribution is the one grounded interjection per beat.
"""


def _controller_frame(controller_id: str) -> str:
    """Build the controller-context frame for the tutor instruction.

    Reads the MIDI profile via vibemix.midi.registry.find_mapping; emits
    a short descriptive frame: "The user has a Pioneer DDJ-FLX4 plugged in.
    The play button on deck A is at the bottom-left of the controller."
    """
    profile = find_mapping(controller_id) or _GENERIC_PROFILE
    return (
        f"The user has a {profile.display_name} plugged in. "
        f"You can reference its physical layout in your one-line observation."
    )


def build_tutor_system_instruction(
    *,
    course_id: str,
    lesson_id: str,
    controller_id: str,
) -> str:
    """Compose the tutor LLM system instruction.

    Args:
        course_id: One of "course_0" (hello-world) / "course_1" (anatomy) /
            "course_2" (transitions) / "course_3" (play mode). Keys
            COURSE_FRAMES.
        lesson_id: e.g. "L0.00-press-play". Keys CURRICULUM for
            system_instruction_addendum.
        controller_id: e.g. "pioneer_ddj_flx4". Keys midi/registry.

    Returns:
        The composed system instruction string. The four-forbidden-moves
        lock is ALWAYS the final block (strongest recency).

    Raises:
        ValueError: course_id not in COURSE_FRAMES, lesson_id not in
            CURRICULUM, controller_id not in MIDI registry (a generic
            fallback frame is used for the latter).

    LESSON-05: reuses MOOD_PERSONAS["teacher"] via build_system_instruction;
    no new lens. TONE-04: the lock lands LAST. LESSON-06: zero hardcoded
    model literals (caller resolves via model_router.resolve(...)).
    """
    if course_id not in COURSE_FRAMES:
        raise ValueError(f"unknown course_id {course_id!r}")
    if lesson_id not in CURRICULUM:
        raise ValueError(f"unknown lesson_id {lesson_id!r}")

    base = build_system_instruction(
        skill="intermediate",  # tutor reads as a peer who knows pedagogy
        mode="coach",          # mode="coach" picks COACH_INTERMEDIATE
        mood="teacher",        # mood="teacher" substitutes MOOD_PERSONAS["teacher"]
        include_citation_grammar=False,   # no [ev:]/[aud:]/etc — text only
        include_listening_fallback=False, # no IM_LISTENING_FRAGMENT
        include_tag_dsl=False,            # no TTS DSL — P93+
    )

    addendum = CURRICULUM[lesson_id].system_instruction_addendum
    # Guard: addendum capped at 200 chars per LESSON-05.
    if len(addendum) > 200:
        raise ValueError(
            f"system_instruction_addendum too long ({len(addendum)} > 200) "
            f"for lesson {lesson_id!r}"
        )

    frames = "\n\n".join([
        COURSE_FRAMES[course_id],
        _controller_frame(controller_id),
        addendum,
        _FORBIDDEN_TUTOR_MOVES_LOCK,
    ])
    return base + "\n\n" + frames
```

**AST gate** (`tests/learn/test_tutor_system_instruction_lock.py`):
```python
# tests/learn/test_tutor_system_instruction_lock.py — NEW
"""TONE-04 binding. The four-forbidden-moves lock must be present in any
system instruction emitted by build_tutor_system_instruction."""
import re

from vibemix.learn.prompts import build_tutor_system_instruction


# The four forbidden-move tokens that must always appear in the lock text.
# These ARE the test — if you change the lock's wording, update this list.
REQUIRED_LOCK_TOKENS = (
    "COMPLIMENT",       # rule 1
    "SUMMARIZE",        # rule 2
    "PREVIEW",          # rule 3
    "CLOSE with an upbeat hook",  # rule 4 — verbatim phrase
)


def test_tutor_system_instruction_includes_all_four_locks():
    instruction = build_tutor_system_instruction(
        course_id="course_0",
        lesson_id="L0.00-press-play",
        controller_id="pioneer_ddj_flx4",
    )
    for token in REQUIRED_LOCK_TOKENS:
        assert token in instruction, (
            f"TONE-04 violation: {token!r} missing from tutor "
            f"system instruction. The four-forbidden-moves lock has drifted."
        )


def test_lock_is_last_block_for_strongest_recency():
    """The lock must appear AFTER the COURSE_FRAMES / controller / addendum
    frames — strongest recency rule (mirrors COACH_CLOSING_BLOCK pattern)."""
    instruction = build_tutor_system_instruction(
        course_id="course_0",
        lesson_id="L0.00-press-play",
        controller_id="pioneer_ddj_flx4",
    )
    # The lock starts with "--- TUTOR DISCIPLINE"; find its position.
    lock_idx = instruction.find("--- TUTOR DISCIPLINE")
    addendum_idx = instruction.find("HELLO WORLD ADDENDUM")  # from fixture
    assert lock_idx > addendum_idx, "lock must come AFTER addendum frame"
```

### Pattern 7: Atomic Progress Persistence

**What:** Mirror the existing `config_store.save()` atomic-write pattern (`tmp.write_text` → `os.replace`). Add a schema_version field; on corrupt-read, nuke the file + emit a fresh empty + emit a one-line toast via `progress_state`.

**Example:**
```python
# src/vibemix/learn/progress.py — NEW
# SPDX-License-Identifier: Apache-2.0
"""LearnProgress — atomic JSON persistence for lesson completion.

Phase 92 (LESSON-03). Mirrors the config_store.save() atomic-write pattern
(runtime/config_store.py:266-278) so a crash mid-write doesn't leave a
half-truncated learn-progress.json. On corrupt-read, the file is silently
deleted + a fresh empty progress is returned + a one-line `progress_state`
toast is queued for next emit.

Schema:
  {
    "schema_version": 1,
    "courses": {
      "course_0": { "completed": false, "completed_at": null },
      "course_1": { "completed": false, "completed_at": null },
      ...
    },
    "lessons": {
      "L0.00-press-play": {
        "completed": true,
        "completed_at": "2026-05-28T01:23:45Z",
        "strikes_used": 1
      },
      ...
    }
  }
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1


def progress_path() -> Path:
    """Location of learn-progress.json under ~/.cache/vibemix/."""
    cache_root = Path.home() / ".cache" / "vibemix"
    return cache_root / "learn-progress.json"


@dataclass
class LearnProgress:
    """In-memory model of the progress JSON file."""

    schema_version: int = SCHEMA_VERSION
    courses: dict[str, dict[str, Any]] = field(default_factory=dict)
    lessons: dict[str, dict[str, Any]] = field(default_factory=dict)

    def mark_completed(self, course_id: str, lesson_id: str) -> None:
        from datetime import datetime, timezone
        iso = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        self.lessons[lesson_id] = {
            "completed": True,
            "completed_at": iso,
            "strikes_used": 0,  # caller updates
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "courses": self.courses,
            "lessons": self.lessons,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "LearnProgress":
        if not isinstance(raw, dict):
            return cls()
        if raw.get("schema_version") != SCHEMA_VERSION:
            # v9.0 ships with v1; future migrations handled here.
            return cls()
        return cls(
            schema_version=SCHEMA_VERSION,
            courses=raw.get("courses", {}),
            lessons=raw.get("lessons", {}),
        )


def load_progress() -> tuple[LearnProgress, bool]:
    """Read learn-progress.json. Returns (progress, was_corrupt) — if
    was_corrupt is True, the file existed but failed to parse; the caller
    should emit a one-line toast via progress_state envelope."""
    p = progress_path()
    if not p.exists():
        return LearnProgress(), False
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        # Corrupt — nuke + return fresh empty.
        print(
            f"[learn.progress] corrupt {p}; resetting to fresh empty",
            file=sys.stderr,
        )
        try:
            p.unlink()
        except OSError:
            pass
        return LearnProgress(), True
    return LearnProgress.from_dict(raw), False


def save_progress(progress: LearnProgress) -> Path:
    """Atomic write via tmp + os.replace. Returns the path written.

    Mirrors runtime/config_store.py:266-278 verbatim. POSIX rename is
    atomic; Windows ReplaceFileW is atomic.
    """
    p = progress_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(
        json.dumps(progress.to_dict(), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    os.replace(tmp, p)
    return p


def reset_progress() -> None:
    """Wipe learn-progress.json. Used by:
    - The CLI `vibemix learn reset` subcommand
    - The "Reset Learn Progress" settings drawer button
    - The corruption-recovery path in load_progress
    """
    p = progress_path()
    if p.exists():
        p.unlink()
```

### Pattern 8: Lesson Script JSON Fixture

**What:** Hand-authored JSON file at `src/vibemix/learn/transcripts/<course>/<lesson_id>.json`. Reusable for all 36 future scripts.

**Example:**
```jsonc
// src/vibemix/learn/transcripts/hello_world/01_press_play.json — NEW
// SPDX-License-Identifier: Apache-2.0
//
// The 1-step "hello world" lesson script. Course 0 = the standalone demo
// that proves the runtime end-to-end: AI says "press deck A play" →
// highlight pulses on the play button → user presses physical play →
// lesson advances → "L0.00 OF 1" completes.
//
// Schema: 5 top-level keys.
//   - lesson_id: matches CURRICULUM key
//   - title: lowercase, period-FREE (UI HUD constraint)
//   - system_instruction_addendum: ≤200 chars, appended to tutor LLM
//     system instruction by build_tutor_system_instruction
//   - tutor_speak: array of beat objects (text + tts_marker + citations)
//   - expected_action: the MIDI action that advances the lesson
//   - hints: 3-element array (one per strike)
//
// TONE-02 binding: this file is the SOURCE OF TRUTH for the tutor text.
// LessonRuntime READS the tutor_speak[].text into LearnTutorSpeak envelopes
// VERBATIM. NO LLM call writes this field at runtime. Static gate
// tests/learn/test_scripts_are_fixtures.py confirms zero generate_content
// calls in src/vibemix/learn/ that write a tutor_speak text field.
{
  "lesson_id": "L0.00-press-play",
  "title": "press play",
  "system_instruction_addendum": "Wait for the user to press deck A's play button. Do not narrate over them.",
  "tutor_speak": [
    {
      "beat": 0,
      "text": "find deck A's play button — it's lit up on your controller.",
      "tts_marker": "L000.beat0",
      "citations": []
    }
  ],
  "expected_action": {
    "type": "button",
    "control": "play",
    "deck": "A",
    "direction": "down"
  },
  "hints": [
    {
      "strike": 1,
      "text": "deck A is on the left side of your controller.",
      "tts_marker": "L000.hint1"
    },
    {
      "strike": 2,
      "text": "look for the triangular play glyph on a square button.",
      "tts_marker": "L000.hint2"
    },
    {
      "strike": 3,
      "text": "the play button is the bottom-row leftmost button on most controllers — press it now.",
      "tts_marker": "L000.hint3"
    }
  ]
}
```

**Static fixture gate** (`tests/learn/test_scripts_are_fixtures.py`):
```python
# tests/learn/test_scripts_are_fixtures.py — NEW
"""TONE-02 binding. The lesson scripts are HAND-AUTHORED JSON fixtures;
no live generative call may write a tutor_speak text field at runtime."""

import ast
import pathlib


LEARN_DIR = pathlib.Path("src/vibemix/learn")


def _walk_python_files(root: pathlib.Path):
    for p in root.rglob("*.py"):
        if p.name.startswith("__pycache__"):
            continue
        yield p


def test_no_generative_writes_to_tutor_speak_text():
    """Grep `src/vibemix/learn/` for any call that assigns to a
    `tutor_speak[*].text` field — there should be ZERO matches.
    The text always comes from JSON fixtures, never from LLM output."""
    suspicious_patterns = (
        "generate_content",  # google.genai
        "models.generate",   # google.genai
        "create_message",    # alt SDKs
    )
    offenders = []
    for path in _walk_python_files(LEARN_DIR):
        source = path.read_text(encoding="utf-8")
        for pat in suspicious_patterns:
            if pat in source:
                # Allow imports — but reject calls that look like writes.
                # Heuristic: if the line containing `generate_content` ALSO
                # references `tutor_speak` or `text=`, flag as suspect.
                for line_no, line in enumerate(source.splitlines(), 1):
                    if pat in line and ("tutor_speak" in line or ".text" in line):
                        offenders.append(f"{path}:{line_no}: {line.strip()}")
    assert not offenders, (
        "TONE-02 violation: live generative writes to tutor_speak.text:\n"
        + "\n".join(offenders)
    )
```

### Pattern 9: AST Gate — Single-Writer Invariant

**What:** `tests/learn/test_runtime_invariants.py` greps `src/vibemix/learn/` for any assignment to `MusicState.<field>` or `ControllerState.<field>` (which would violate the read-only constraint).

**Implementation (simple grep, not full AST — keep it tractable):**
```python
# tests/learn/test_runtime_invariants.py — NEW
"""Invariant #1 binding. The `learn/` package never WRITES to MusicState
or ControllerState. AST-grep approach: walks source, flags any line that
looks like `controller_state.<field> = ...` or `music_state.<field> = ...`.

Also asserts: only LessonRuntime writes LearnState. Outside runtime.py,
no module should mutate LearnState fields.
"""
import re
import pathlib


LEARN_DIR = pathlib.Path("src/vibemix/learn")

# Patterns that look like writes to forbidden objects.
FORBIDDEN_WRITES = (
    re.compile(r"\b(music_state|MusicState)\.\w+\s*=\s*"),
    re.compile(r"\b(controller_state|ControllerState)\.\w+\s*=\s*"),
)


def test_learn_package_never_writes_music_state_or_controller_state():
    offenders = []
    for path in LEARN_DIR.rglob("*.py"):
        if "__pycache__" in str(path):
            continue
        source = path.read_text(encoding="utf-8")
        for line_no, line in enumerate(source.splitlines(), 1):
            for pat in FORBIDDEN_WRITES:
                if pat.search(line):
                    offenders.append(f"{path}:{line_no}: {line.strip()}")
    assert not offenders, (
        "Invariant #1 violation: learn/ wrote to MusicState/ControllerState:\n"
        + "\n".join(offenders)
    )


def test_learn_state_writes_are_only_inside_runtime_py():
    """LessonRuntime is the sole writer of LearnState. Outside runtime.py,
    no learn/ module should assign to learn_state.<field>."""
    pat = re.compile(r"\b(learn_state|self\._learn)\.\w+\s*=\s*")
    offenders = []
    for path in LEARN_DIR.rglob("*.py"):
        if "__pycache__" in str(path):
            continue
        if path.name == "runtime.py":
            continue  # the sole-writer file; skip
        if path.name == "state.py":
            continue  # the dataclass definition; default_factory etc. allowed
        source = path.read_text(encoding="utf-8")
        for line_no, line in enumerate(source.splitlines(), 1):
            if pat.search(line):
                offenders.append(f"{path}:{line_no}: {line.strip()}")
    assert not offenders, (
        "Invariant #1 violation: non-runtime module wrote to LearnState:\n"
        + "\n".join(offenders)
    )
```

### Anti-Patterns to Avoid

- **A second `websockets.serve` for Learn lesson traffic** — violates invariant #4. The 11 new envelopes ride existing ws:8765 via the EXISTING `IpcRouterBus` (the same `_send_all` path the P91 envelopes use). CI gate `tests/learn/test_no_new_ws_port.py` (green from P91) stays green.
- **A second `mido.open_input` listener for Learn** — same as P91 caveat; LessonRuntime READS from `ControllerState.deck_snapshot()` (lock-guarded) rather than spawning a second listener.
- **LLM call that writes `tutor_speak.text`** — TONE-02 fail. Live generative calls in `learn/` can produce CITATIONS (for grounding), but never the `text` field — that always comes from the JSON fixture.
- **Inlining the "Reset Learn Progress" row into `SettingsDrawer.ts`** — diverges from the `MascotGroup` / `HelpGroup` / `PerformanceGroup` precedent. Use a separate `learn-group.ts` component file.
- **Skipping `npm run codegen:ipc` after the schema edit** — the validator is pre-compiled; new envelopes will be silently rejected at runtime. This is a known footgun documented in `feedback_schema_edit_needs_codegen_ipc.md`.
- **Reusing `MusicState.write_*` for lesson state** — would violate invariant #1. LessonRuntime writes `LearnState` ONLY; it never touches `MusicState`. AST gate enforces.
- **Adding a `transitions` library import alongside `python-statemachine`** — only ONE FSM library in the project; if you need a feature `python-statemachine` doesn't offer, reach for it inline in `runtime.py`, not a second dep.
- **Tutor narrating during the 1 Hz strike timer countdown** — the "I'm waiting for you" silence is the proprioceptive feedback; the user feels the dock fall quiet. Narrate ONLY when the strike escalates (the on_enter_hint_strike_N callback emits a fresh `tutor_speak`).
- **Hard-coding `"gemini-3.5-flash"` in `learn/prompts.py`** — model literal CI grep gate will fail. Always resolve via `vibemix.llm.model_router.resolve(<path>)`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Lesson FSM state + transition dispatch | A custom `match self.state:` switch | `python-statemachine 3.1.2` `State` + transition class-attrs | Declarative dispatch + introspection + free graph viz; matches industry standard. |
| Atomic file write (lesson progress) | Custom `with tempfile.NamedTemporaryFile + rename` dance | `tmp.write_text(...) + os.replace(tmp, target)` (mirror of `config_store.save()`) | Existing in-tree pattern; same atomicity guarantee on POSIX + Windows. |
| 4-forbidden-moves tutor lock | A custom token blocklist runtime check | A FIXED `_FORBIDDEN_TUTOR_MOVES_LOCK` constant prepended to the system instruction + an AST-gated test asserting the lock text appears in the composed instruction | The model sees the lock; the test guarantees the lock stays in. Runtime blocklist deferred to P94 (`check_no_tutor_slop.py`). |
| Lesson-script generation | Live LLM call writing tutor_speak text | Hand-authored JSON fixtures + load via `pathlib.Path.read_text + json.loads` | TONE-02. The 36 lesson scripts are the product's authored content — never generated. |
| MIDI delta detection for advancement guard | Re-implementing CC-delta + button-press logic | Read from EXISTING `ControllerState` (P91 wire) + the existing `recent_moves[8s]` snapshot pattern | `state.py::handle_msg` is the canonical decoder. The guard is just `action_matches(midi_event)` reading the existing snapshot. |
| Settings drawer row scaffolding | A custom DOM row builder | The EXISTING `renderSettingsGroup` + `vmx-settings-row--destructive` class from the recording-browser pattern | Convention exists; matches `MascotGroup` / `HelpGroup` / `PerformanceGroup`. |
| Confirm dialog for destructive reset | A custom modal | The EXISTING `renderConfirmDialog` from `settings/components/confirm-dialog.ts` | Already covers Esc dismiss, backdrop click, focus trap, keyboard nav. |
| Tutor LLM model resolution | A model literal in code | `vibemix.llm.model_router.resolve(<path>)` (see Open Q1 for path-name ratification) | CLAUDE.md zero-hardcoded-literal rule. CI grep gate enforces. |
| 30 Hz position push or timer loop | A new asyncio task | The existing 30 Hz `ws_broadcast` tick (P91 already adds `midi_mirror.snapshot()` per tick); P92's 1 Hz `tick_loop` for strike escalation is a SEPARATE asyncio coroutine that lives alongside, not inside, `ws_broadcast` | Coexistence pattern proven by P91; keeps strike escalation out of the hot 30 Hz path. |

**Key insight:** Every piece of new wiring in P92 has an exact precedent in this repo — `python-statemachine` is the one industry import, and even it's a precise fit for the lesson FSM shape. The phase is composition, not invention.

## Runtime State Inventory

> P92 is **additive** (not a rename or migration). Section retained for completeness.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | NEW: `~/.cache/vibemix/learn-progress.json` (schema_version 1; managed via `learn/progress.py`). NO existing data to migrate (fresh feature). | Atomic-write + corruption recovery pattern (see Pattern 7). |
| Live service config | **None** — no external services modified. | None |
| OS-registered state | **None** — no new OS-level registrations. Learn window already registers via `WebviewWindowBuilder` from P91. | None |
| Secrets/env vars | **None** — P92 does NOT read any new env var. `GEMINI_API_KEY` (existing) is reused for tutor LLM calls. | None |
| Build artifacts | None new — `pyproject.toml` edit (adds `python-statemachine`) means `uv sync` is required after the dep add. | One-time `uv sync` post-edit. |

**Nothing migratory.** P92 is purely new-island + atomic-additive work.

## Common Pitfalls

### Pitfall 1: TONE — the four-forbidden-moves leak through fixture text

**What goes wrong:** The lock text in `_FORBIDDEN_TUTOR_MOVES_LOCK` is correctly added to the system instruction, but the lesson script's `tutor_speak[].text` field itself contains "great job" or "now let's…" — the AI faithfully reads the fixture text, and the slop ships from the fixture, not the AI.

**Why it happens:** The lock disciplines the AI's interjections; it doesn't discipline the human-authored fixtures. Pitfall P1 (PITFALLS.md §15-46) is the canonical write-up.

**How to avoid:**
- The runtime tutor-slop blocklist `scripts/launch/check_no_tutor_slop.py` lands in P94 with ≥20 tokens; for P92 we ship the fixture verbatim (P94 will sweep it).
- The 1-step "hello world" lesson's `tutor_speak[0].text = "find deck A's play button — it's lit up on your controller."` is intentionally minimal — no praise, no preview, no summary, no upbeat hook.
- The 3 hints follow the same discipline: "deck A is on the left side of your controller." / "look for the triangular play glyph on a square button." / "the play button is the bottom-row leftmost button on most controllers — press it now."

**Warning signs:** A Kaan ear-pass listener flags the AI sounding "edtech-y" → the fixture text leaked slop, not the AI. Fix: tighten the fixture, not the prompt.

### Pitfall 2: PERSISTENCE — corruption surface during the user-progress lifecycle

**What goes wrong:** Power loss / app crash mid-write leaves `learn-progress.json` half-truncated. Next launch reads garbage, fails to deserialize, and the user appears to have lost all their progress.

**Why it happens:** Naive `json.dump(data, open(path, "w"))` is NOT atomic — the file is open in write mode the entire `dump` call, so a crash leaves a partial file. (Pitfall P12, PITFALLS.md §405-423.)

**How to avoid:**
- **Atomic write pattern** (mirror of `runtime/config_store.py:266-278` and `profile/storage.py:78-92`): write to `<path>.json.tmp`, then `os.replace(tmp, target)`. POSIX rename + Windows ReplaceFileW are atomic — either the old file or the new file exists, never a half-write.
- **Schema version field** at the top: `{schema_version: 1, ...}`. On read, if the version doesn't match, run a migration OR reset gracefully.
- **Corruption recovery**: on `JSONDecodeError`, the file is silently `unlink()`'d + a fresh `LearnProgress()` is returned + the next `ipc.learn.progress_state` envelope carries a `was_recovered: true` flag for a one-line toast.
- **Test gate**: `tests/learn/test_progress_persistence.py::test_corrupt_file_recovers_clean` writes garbage bytes to `learn-progress.json`, calls `load_progress()`, asserts a fresh empty + the corruption flag.

**Warning signs:** User report "I lost all my progress" → either corruption hit and the toast was missed, OR the user manually `rm`'d the cache dir.

### Pitfall 3: IPC — `npm run codegen:ipc` skipped → 11 envelopes silently rejected

**What goes wrong:** Developer edits `messages.schema.json` to add the 11 envelopes, runs Python tests (which use jsonschema dynamically), they pass — but the ajv validator on the frontend is PRE-COMPILED (`validator.generated.mjs`). Without re-running codegen, the new envelopes are rejected at runtime by ajv, causing webview disconnections.

**Why it happens:** The ajv validator is intentionally pre-compiled at build time to satisfy the CSP `unsafe-eval` ban. This is documented in `feedback_schema_edit_needs_codegen_ipc.md` and rediscovered as P91 Pitfall 7.

**How to avoid:**
- **Plan includes `npm run codegen:ipc` as a DISCRETE task** between "edit messages.schema.json" and "test envelope round-trip."
- **CI gate** `scripts/check_ipc_schema.py` (existing) asserts wrappers ↔ oneOf parity (count). After P92, the count is `[old + 11] ↔ [old + 11]`.
- **Mascot regression test** `tauri/ui/tests/mascot/learn-envelope-doesnt-break-mascot.spec.ts` (P13 mitigation): simulate any `learn.*` envelope and verify the mascot's `{music, voice, mic, …}` frame handler still parses. (P91 already added the 2 envelopes without breaking; P92 adds 11 more.)

**Warning signs:** Mascot disconnects when Learn mode opens; ajv "unknown schema $ref" errors in the webview console.

### Pitfall 4: 3-strike hint surface — escalation feels nagging, not helpful

**What goes wrong:** The user is stuck on a control they genuinely can't find. The system fires hint 1 at 30 s, hint 2 at 60 s, hint 3 at 90 s — but each hint repeats the same information in a different sentence, and the user feels nagged rather than helped.

**Why it happens:** Each hint must add ONE NEW concrete piece of information; never repeat the previous hint's content.

**How to avoid:**
- **Hand-authored hints follow a progressive disclosure rule**: hint 1 = "deck A is on the left side of your controller" (locates the deck). Hint 2 = "look for the triangular play glyph on a square button" (locates the button shape). Hint 3 = "the play button is the bottom-row leftmost button on most controllers — press it now" (gives the exact location + instruction).
- **No hint repeats verbatim wording from a prior hint** — UI-SPEC enforces this in the copywriting contract (§Tutor-speak dock copy hint copy).
- **Visual amplification accompanies the copy**: pulse-ring stroke intensifies from breath (1400ms) to snap (600ms) during `data-state="hint"` — a SECOND a11y channel signaling "the system is being more emphatic now" without the copy needing to nag.
- **The "I got it" skip is ALWAYS visible** — even during hints, the user can opt out (after the 45 s min-dwell elapses).

**Warning signs:** Beta testers report "the AI keeps repeating itself" → hints are repetitive; rewrite to progressive disclosure.

### Pitfall 5: 45-second min-dwell — feels like a paywall

**What goes wrong:** A user wants to skim through the lesson to see how the runtime works. They click "I got it" — and nothing happens. No copy explains why. They conclude the button is broken and bail.

**Why it happens:** Anti-speedrun is a UX safety floor; without a clear (but quiet) communication of why, it reads as a defect.

**How to avoid:**
- **Quiet tooltip** on hover/focus of the disabled "I got it" button: `at least 45 seconds per lesson — that's the floor.` (UI-SPEC §Copywriting / Anti-speedrun hint).
- **Visual lockout state** = opacity 0.4 + `aria-disabled="true"` + `data-min-dwell-locked="true"` attribute. The button is dimly visible (not hidden), so the user knows it exists.
- **Silent unlock** at the 45 s mark — no animation, no toast, no SR announcement. The button just becomes clickable.
- **No countdown timer surfaced** — countdowns train rushing ("3 more seconds till I can skip!"). The floor protects pedagogy; the silence protects the user.

**Warning signs:** Beta testers report "the skip button is broken" → the tooltip didn't communicate the floor.

### Pitfall 6: LATENCY — `tick_loop` competing with `ws_broadcast` for the asyncio loop

**What goes wrong:** The 30 Hz `ws_broadcast` already runs at 33 ms cadence. The new 1 Hz `LessonRuntime.tick_loop` adds another `asyncio.sleep(1.0)` coroutine. If `on_enter_<state>` callbacks fire synchronous heavy work (LLM call, file I/O), the ws_broadcast's 30 Hz cadence stutters → highlight paint exceeds the 16 ms paint budget perceived by the user.

**Why it happens:** asyncio cooperative scheduling assumes coroutines yield frequently. A blocking call inside `on_enter_advancing` (e.g. `self._progress.save_progress(...)`) holds the loop until file I/O completes.

**How to avoid:**
- **All file I/O in `on_enter_<state>` callbacks runs through `loop.run_in_executor(None, ...)`** — the existing pattern in `__main__.py` for the recordings persistence path.
- **LLM calls (tutor narration) are async** — `await client.aio.models.generate_content(...)` per the existing co-host pattern in `dj_cohost.py`.
- **`tick_loop` 1 Hz cadence is non-critical** — a missed tick by 200 ms doesn't matter (strike escalation is 30 s granularity). The hot path is `ws_broadcast` 30 Hz (P91).
- **Integration test** `tests/runtime/test_ws_broadcast_30hz_under_lesson_load.py` — pin that ws_broadcast's 30 Hz cadence stays ≤35 ms median while LessonRuntime is in `awaiting_action` with 1 Hz tick_loop running.

**Warning signs:** `tauri/ui/tests/learn/highlight-paint.test.ts` measures > 16 ms P95 → likely tick_loop callback blocking the asyncio loop.

### Pitfall 7: AST-gate FALSE POSITIVE on the `learn_state = ` initial assignment

**What goes wrong:** The AST gate greps `src/vibemix/learn/` for `learn_state.<field>\s*=\s*` (forbidden writes outside `runtime.py`). But the dataclass DEFINITION in `state.py` uses `field(default_factory=...)` or `<field>: type = <default>` — the grep flags these as violations.

**Why it happens:** The grep is line-oriented; it doesn't distinguish dataclass DEFAULTS from runtime writes.

**How to avoid:**
- **`state.py` is exempted** from the grep (allowlist in the test: `if path.name == "state.py": continue`).
- **`runtime.py` is exempted** (the sole-writer file).
- **The grep targets `learn_state` and `self._learn` as the runtime-instance names** — dataclass DEFAULTS use the field name (`current_lesson_id: str | None = None`), not the instance access pattern (`self._learn.current_lesson_id = ...`).

**Warning signs:** CI red on `test_runtime_invariants.py::test_learn_state_writes_are_only_inside_runtime_py` for a file that obviously doesn't write LearnState → the allowlist is too narrow.

## Code Examples

Verified patterns from existing sources in this repo. Each shows what the new code should mirror.

### Code Example 1: 11 IPC Envelope Schemas (full JSON Schema additions)

```jsonc
// tauri/ui/src/ipc/messages.schema.json — ADDITIONS
// 1. Add to top-level "oneOf": [...] list (11 NEW entries, after the P91 ones):

{ "$ref": "#/definitions/LearnStartCourse" },
{ "$ref": "#/definitions/LearnStartLesson" },
{ "$ref": "#/definitions/LearnCompleteLesson" },
{ "$ref": "#/definitions/LearnLessonLoaded" },
{ "$ref": "#/definitions/LearnHighlight" },
{ "$ref": "#/definitions/LearnAdvance" },
{ "$ref": "#/definitions/LearnAck" },
{ "$ref": "#/definitions/LearnTutorSpeak" },
{ "$ref": "#/definitions/LearnExemplarPlay" },
{ "$ref": "#/definitions/LearnExemplarStop" },
{ "$ref": "#/definitions/LearnProgressState" },

// 2. Add to "definitions": {...} (after the P91 LearnControllerDetected + LearnMidiPosition):

"LearnStartCourse": {
  "$comment": "Shell → sidecar. User picked a course in the HUD. Phase 92 LESSON-02.",
  "type": "object",
  "additionalProperties": false,
  "required": ["type", "ts", "payload"],
  "properties": {
    "type": {"const": "ipc.learn.start_course"},
    "ts": {"type": "string", "format": "date-time"},
    "payload": {
      "type": "object",
      "additionalProperties": false,
      "required": ["course_id", "controller_id"],
      "properties": {
        "course_id": {"type": "string", "enum": ["course_0", "course_1", "course_2", "course_3"]},
        "controller_id": {"type": "string", "minLength": 1}
      }
    }
  }
},

"LearnStartLesson": {
  "$comment": "Shell → sidecar. User skipped into a specific lesson. Phase 92 LESSON-02.",
  "type": "object",
  "additionalProperties": false,
  "required": ["type", "ts", "payload"],
  "properties": {
    "type": {"const": "ipc.learn.start_lesson"},
    "ts": {"type": "string", "format": "date-time"},
    "payload": {
      "type": "object",
      "additionalProperties": false,
      "required": ["lesson_id", "level"],
      "properties": {
        "lesson_id": {"type": "string", "pattern": "^L[0-9]+\\.[0-9]+-.+$"},
        "level": {"type": "string", "enum": ["fresh", "replay"]}
      }
    }
  }
},

"LearnCompleteLesson": {
  "$comment": "Bidirectional. User skip OR system advance. Phase 92 LESSON-02 / LESSON-04.",
  "type": "object",
  "additionalProperties": false,
  "required": ["type", "ts", "payload"],
  "properties": {
    "type": {"const": "ipc.learn.complete_lesson"},
    "ts": {"type": "string", "format": "date-time"},
    "payload": {
      "type": "object",
      "additionalProperties": false,
      "required": ["lesson_id", "reason"],
      "properties": {
        "lesson_id": {"type": "string", "pattern": "^L[0-9]+\\.[0-9]+-.+$"},
        "reason": {"type": "string", "enum": ["completed", "user_skip"]}
      }
    }
  }
},

"LearnLessonLoaded": {
  "$comment": "Sidecar → shell. A lesson is loaded; HUD metadata. Phase 92 LESSON-02.",
  "type": "object",
  "additionalProperties": false,
  "required": ["type", "ts", "payload"],
  "properties": {
    "type": {"const": "ipc.learn.lesson_loaded"},
    "ts": {"type": "string", "format": "date-time"},
    "payload": {
      "type": "object",
      "additionalProperties": false,
      "required": ["course_id", "lesson_id", "title", "controller_id", "progress_dots"],
      "properties": {
        "course_id": {"type": "string", "minLength": 1},
        "lesson_id": {"type": "string", "minLength": 1},
        "title": {"type": "string", "minLength": 1, "maxLength": 80},
        "controller_id": {"type": "string", "minLength": 1},
        "progress_dots": {
          "type": "array",
          "items": {
            "type": "object",
            "additionalProperties": false,
            "required": ["lesson_id", "status"],
            "properties": {
              "lesson_id": {"type": "string"},
              "status": {"type": "string", "enum": ["pending", "current", "completed"]}
            }
          },
          "maxItems": 32
        }
      }
    }
  }
},

"LearnHighlight": {
  "$comment": "Sidecar → shell. Glow a control on the rendered SVG. Phase 92 RENDER-04. Dual-channel cue (cue_color + cue_shape) for color-blind a11y. ≤16ms paint budget pinned by tauri/ui/tests/learn/highlight-paint.test.ts.",
  "type": "object",
  "additionalProperties": false,
  "required": ["type", "ts", "payload"],
  "properties": {
    "type": {"const": "ipc.learn.highlight"},
    "ts": {"type": "string", "format": "date-time"},
    "payload": {
      "type": "object",
      "additionalProperties": false,
      "required": ["control_id", "deck", "cue_color", "cue_shape", "annotation", "expected_action"],
      "properties": {
        "control_id": {"type": "string", "minLength": 1},
        "deck": {"type": "string", "enum": ["", "A", "B", "C", "D"]},
        "cue_color": {"type": "string", "enum": ["amber", "warning"]},
        "cue_shape": {"type": "string", "enum": ["pulse-ring", "static-glow"]},
        "annotation": {"type": "string", "maxLength": 200},
        "expected_action": {
          "type": "object",
          "additionalProperties": false,
          "required": ["type", "control"],
          "properties": {
            "type": {"type": "string", "enum": ["cc", "button"]},
            "control": {"type": "string", "minLength": 1},
            "deck": {"type": "string", "enum": ["", "A", "B", "C", "D"]},
            "direction": {"type": "string", "enum": ["", "up", "down"]},
            "min_delta": {"type": "integer", "minimum": 0, "maximum": 127}
          }
        }
      }
    }
  }
},

"LearnAdvance": {
  "$comment": "Bidirectional. Tutor-confirms-MIDI OR user skip. Phase 92 LESSON-04.",
  "type": "object",
  "additionalProperties": false,
  "required": ["type", "ts", "payload"],
  "properties": {
    "type": {"const": "ipc.learn.advance"},
    "ts": {"type": "string", "format": "date-time"},
    "payload": {
      "type": "object",
      "additionalProperties": false,
      "required": ["lesson_id", "reason"],
      "properties": {
        "lesson_id": {"type": "string", "minLength": 1},
        "reason": {"type": "string", "enum": ["action_matched", "user_skip"]}
      }
    }
  }
},

"LearnAck": {
  "$comment": "Shell → sidecar. User touched physical control OR clicked SVG. Phase 92 LESSON-04. The sidecar replies with `advance` if action_matches.",
  "type": "object",
  "additionalProperties": false,
  "required": ["type", "ts", "payload"],
  "properties": {
    "type": {"const": "ipc.learn.ack"},
    "ts": {"type": "string", "format": "date-time"},
    "payload": {
      "type": "object",
      "additionalProperties": false,
      "required": ["control_id", "source"],
      "properties": {
        "control_id": {"type": "string", "minLength": 1},
        "source": {"type": "string", "enum": ["midi", "click"]},
        "value": {"type": "integer", "minimum": 0, "maximum": 127},
        "direction": {"type": "string", "enum": ["", "up", "down"]}
      }
    }
  }
},

"LearnTutorSpeak": {
  "$comment": "Sidecar → shell. Tutor narration. text comes from JSON fixture (NEVER LLM-generated). citations[] is empty in P92 — P93+ populates with [exemplar:<id>] when exemplar engine ships. Phase 92 TONE-02 / LESSON-05.",
  "type": "object",
  "additionalProperties": false,
  "required": ["type", "ts", "payload"],
  "properties": {
    "type": {"const": "ipc.learn.tutor_speak"},
    "ts": {"type": "string", "format": "date-time"},
    "payload": {
      "type": "object",
      "additionalProperties": false,
      "required": ["text", "tts_marker", "citations", "data_state"],
      "properties": {
        "text": {"type": "string", "minLength": 1, "maxLength": 280},
        "tts_marker": {"type": "string", "minLength": 1, "maxLength": 64},
        "citations": {
          "type": "array",
          "items": {"type": "string", "pattern": "^\\[(track|exemplar|cue|ev|aud|midi|screen|mix|tend|key|recall):.+\\]$"},
          "maxItems": 4
        },
        "data_state": {"type": "string", "enum": ["active", "hint"]}
      }
    }
  }
},

"LearnExemplarPlay": {
  "$comment": "Sidecar → shell. Exemplar audio playback STARTED. SHAPE ONLY in P92 — engine in P93. Phase 92 LESSON-02 (shape).",
  "type": "object",
  "additionalProperties": false,
  "required": ["type", "ts", "payload"],
  "properties": {
    "type": {"const": "ipc.learn.exemplar_play"},
    "ts": {"type": "string", "format": "date-time"},
    "payload": {
      "type": "object",
      "additionalProperties": false,
      "required": ["track_id", "duration_s", "gain_db"],
      "properties": {
        "track_id": {"type": "string", "minLength": 1},
        "duration_s": {"type": "number", "minimum": 0, "maximum": 300},
        "gain_db": {"type": "number", "minimum": -24, "maximum": 0}
      }
    }
  }
},

"LearnExemplarStop": {
  "$comment": "Sidecar → shell. Exemplar audio playback ENDED. SHAPE ONLY in P92 — engine in P93.",
  "type": "object",
  "additionalProperties": false,
  "required": ["type", "ts", "payload"],
  "properties": {
    "type": {"const": "ipc.learn.exemplar_stop"},
    "ts": {"type": "string", "format": "date-time"},
    "payload": {
      "type": "object",
      "additionalProperties": false,
      "required": ["track_id", "reason"],
      "properties": {
        "track_id": {"type": "string", "minLength": 1},
        "reason": {"type": "string", "enum": ["completed", "interrupted"]}
      }
    }
  }
},

"LearnProgressState": {
  "$comment": "Bidirectional. action='snapshot' (push from sidecar) or action='reset' (request from shell) or action='reset_ack' (sidecar confirms reset). Phase 92 LESSON-03.",
  "type": "object",
  "additionalProperties": false,
  "required": ["type", "ts", "payload"],
  "properties": {
    "type": {"const": "ipc.learn.progress_state"},
    "ts": {"type": "string", "format": "date-time"},
    "payload": {
      "type": "object",
      "additionalProperties": false,
      "required": ["action"],
      "properties": {
        "action": {"type": "string", "enum": ["snapshot", "reset", "reset_ack"]},
        "was_recovered": {"type": "boolean"},
        "progress": {
          "type": "object",
          "additionalProperties": false,
          "required": ["schema_version", "courses", "lessons"],
          "properties": {
            "schema_version": {"type": "integer", "minimum": 1, "maximum": 1},
            "courses": {
              "type": "object",
              "additionalProperties": {
                "type": "object",
                "additionalProperties": false,
                "properties": {
                  "completed": {"type": "boolean"},
                  "completed_at": {"type": ["string", "null"]}
                }
              }
            },
            "lessons": {
              "type": "object",
              "additionalProperties": {
                "type": "object",
                "additionalProperties": false,
                "properties": {
                  "completed": {"type": "boolean"},
                  "completed_at": {"type": ["string", "null"]},
                  "strikes_used": {"type": "integer", "minimum": 0, "maximum": 3}
                }
              }
            }
          }
        }
      }
    }
  }
}
```

**Post-edit MUST run:**
```bash
cd tauri/ui && npm run codegen:ipc  # regenerates messages.ts + validator.generated.mjs
```

### Code Example 2: Python dataclasses for the 11 envelopes (mirrors of the JSON Schema)

```python
# src/vibemix/ui_bus/learn_messages.py — EDIT (add 11 dataclasses after P91 pair)
# SPDX-License-Identifier: Apache-2.0

# ... existing P91 LearnControllerDetected + LearnMidiPosition above ...


@dataclass(frozen=True, slots=True)
class LearnStartCoursePayload:
    course_id: Literal["course_0", "course_1", "course_2", "course_3"]
    controller_id: str


@dataclass(frozen=True, slots=True)
class LearnStartCourse:
    type: Literal["ipc.learn.start_course"]
    ts: str
    payload: LearnStartCoursePayload

    @classmethod
    def make(cls, *, course_id: str, controller_id: str) -> "LearnStartCourse":
        return cls(
            type="ipc.learn.start_course",
            ts=_now_iso(),
            payload=LearnStartCoursePayload(
                course_id=course_id, controller_id=controller_id,
            ),
        )

    def to_json(self) -> str:
        return _serialize(self)

    def to_dict(self) -> dict:
        return json.loads(self.to_json())


# ... 10 more dataclasses follow the exact same pattern ...
#   LearnStartLesson
#   LearnCompleteLesson
#   LearnLessonLoaded
#   LearnHighlight
#   LearnAdvance
#   LearnAck
#   LearnTutorSpeak
#   LearnExemplarPlay
#   LearnExemplarStop
#   LearnProgressState
#
# Each follows the EXACT pattern shown above — a Payload dataclass + a top-level
# envelope wrapper dataclass with a .make() factory, .to_json(), .to_dict().
# Naming convention matches the P91 LearnControllerDetected / LearnMidiPosition
# pattern verbatim (file:line src/vibemix/ui_bus/learn_messages.py:86-154).
```

### Code Example 3: `messages.schema.json` parity test

```python
# tests/ipc/test_learn_envelope_parity_p92.py — NEW
"""LESSON-02 binding. The 11 new envelopes round-trip cleanly through
the shared _VALIDATOR (Python jsonschema) and have count parity with
the JSON Schema oneOf list."""
import json
from pathlib import Path

import pytest

from vibemix.ui_bus.learn_messages import (
    LearnStartCourse, LearnStartLesson, LearnCompleteLesson,
    LearnLessonLoaded, LearnHighlight, LearnAdvance, LearnAck,
    LearnTutorSpeak, LearnExemplarPlay, LearnExemplarStop,
    LearnProgressState,
)


@pytest.mark.parametrize("envelope_factory, kwargs", [
    (LearnStartCourse.make, {"course_id": "course_0", "controller_id": "pioneer_ddj_flx4"}),
    (LearnStartLesson.make, {"lesson_id": "L0.00-press-play", "level": "fresh"}),
    (LearnCompleteLesson.make, {"lesson_id": "L0.00-press-play", "reason": "completed"}),
    # ... 8 more parametric cases ...
])
def test_envelope_roundtrip(envelope_factory, kwargs):
    """make() → to_json() → json.loads → validate."""
    env = envelope_factory(**kwargs)
    wire = json.loads(env.to_json())
    assert wire["type"] == env.type
    # _VALIDATOR.validate already ran inside to_json (via _serialize); if we
    # got here, the schema accepted the payload.


def test_oneof_count_parity_matches_dataclass_count():
    """LESSON-02 / Pitfall 7: 13 wrappers (2 P91 + 11 P92) must equal 13 oneOf refs."""
    schema_path = Path("tauri/ui/src/ipc/messages.schema.json")
    schema = json.loads(schema_path.read_text())
    learn_refs = [
        ref for ref in schema["oneOf"]
        if "$ref" in ref and "Learn" in ref["$ref"]
    ]
    # 2 P91 + 11 P92 = 13
    assert len(learn_refs) == 13, (
        f"oneOf has {len(learn_refs)} Learn refs; expected 13. "
        f"Did you forget to add a P92 envelope to the oneOf list?"
    )
```

### Code Example 4: Curriculum metadata

```python
# src/vibemix/learn/curriculum.py — NEW
# SPDX-License-Identifier: Apache-2.0
"""Curriculum metadata — course frames + lesson dispatch.

Phase 92. For P92, only Course 0 (the "hello world" 1-step demo) is wired.
Courses 1, 2, 3 add their entries in P94/P95/P96.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


COURSE_FRAMES: dict[str, str] = {
    "course_0": (
        "Course 0 is the hello-world tutorial — a one-lesson demo proving "
        "the runtime end-to-end."
    ),
    # P94 adds course_1, P95 adds course_2, P96 adds course_3.
}


@dataclass(frozen=True)
class LessonMeta:
    """Per-lesson metadata. system_instruction_addendum is the ≤200 char
    suffix passed to build_tutor_system_instruction. transcript_path is the
    relative path under src/vibemix/learn/transcripts/."""

    title: str
    course_id: str
    system_instruction_addendum: str
    transcript_path: str

    @property
    def script(self) -> dict[str, Any]:
        """Lazy-load the JSON fixture. Cached by the @dataclass-frozen default."""
        base = Path(__file__).parent / "transcripts"
        return json.loads((base / self.transcript_path).read_text(encoding="utf-8"))


CURRICULUM: dict[str, LessonMeta] = {
    "L0.00-press-play": LessonMeta(
        title="press play",
        course_id="course_0",
        system_instruction_addendum=(
            "HELLO WORLD ADDENDUM: Wait for the user to press deck A's play "
            "button. Do not narrate over them. Stay quiet between beats."
        ),
        transcript_path="hello_world/01_press_play.json",
    ),
    # P94 adds L1.01..L1.16, P95 adds L2.01..L2.14, P96 adds L3.01..L3.06.
}
```

### Code Example 5: `learn-group.ts` — settings drawer extension

```typescript
// tauri/ui/src/settings/components/learn-group.ts — NEW
// SPDX-License-Identifier: Apache-2.0
//
// Phase 92 LESSON-03. Mirror of MascotGroup / HelpGroup / PerformanceGroup
// at SettingsDrawer.ts:909-927. Inserted between RECORDING and MASCOT per
// the existing group order.

import { renderSettingsGroup } from "./group.js";
import { renderConfirmDialog } from "./confirm-dialog.js";
import { emitIpc } from "../../ipc/client.js";
import { registerStyle } from "../../session/components/_style-registry.js";

const CSS = `
  .vmx-settings-row {
    display: block;
    width: 100%;
    text-align: left;
    padding: var(--sp-3) var(--sp-4);
    background: transparent;
    border: 1px solid transparent;
    color: inherit;
    cursor: pointer;
    border-radius: var(--rad-sm);
    transition: background var(--motion-snap) ease-out,
                border-color var(--motion-snap) ease-out;
  }
  .vmx-settings-row:hover,
  .vmx-settings-row:focus-visible {
    background: rgba(255, 255, 255, 0.02);
    border-color: var(--glass-edge);
  }
  .vmx-settings-row--destructive .vmx-settings-row__label {
    color: var(--silk-65);
  }
  .vmx-settings-row__label {
    font-family: var(--type-body);
    font-variation-settings: "wdth" 90, "wght" 500;
    font-size: 13px;
    color: var(--silk-65);
    margin-bottom: var(--sp-1);
  }
  .vmx-settings-row__secondary {
    font-family: var(--type-body);
    font-size: 11px;
    color: var(--silk-22);
    line-height: 1.4;
  }
`;

registerStyle("vmx-learn-group", CSS);


export function LearnGroup(): HTMLElement {
  const resetRow = document.createElement("button");
  resetRow.type = "button";
  resetRow.className = "vmx-settings-row vmx-settings-row--destructive";
  resetRow.innerHTML = `
    <div class="vmx-settings-row__label">reset learn progress</div>
    <div class="vmx-settings-row__secondary">
      clears all completed lessons. cannot be undone.
    </div>
  `;
  resetRow.addEventListener("click", () => {
    renderConfirmDialog({
      heading: "reset learn progress?",
      body: (
        "all 36 lessons across 3 courses will reset to not started. " +
        "your library and DJ profile are not affected."
      ),
      confirmLabel: "reset",
      cancelLabel: "cancel",
      variant: "danger",
      onConfirm: () => {
        void emitIpc("ipc.learn.progress_state", { action: "reset" });
      },
      onCancel: () => {
        /* no-op */
      },
    });
  });

  return renderSettingsGroup({
    header: "LEARN",
    children: [resetRow],
  });
}
```

**Wiring in `SettingsDrawer.ts`** (one line change, between RECORDING and MASCOT):
```typescript
// tauri/ui/src/settings/SettingsDrawer.ts — EDIT
// Find the line that calls `body.append(MascotGroup());` and insert BEFORE it:
import { LearnGroup } from "./components/learn-group.js";

// ... inside renderDrawerBody, after RECORDING group, before MASCOT:
body.append(LearnGroup());
body.append(MascotGroup());
body.append(PerformanceGroup(settings.lighter_blur));
body.append(HelpGroup());
```

### Code Example 6: Highlight paint test harness (≤16 ms gate)

```typescript
// tauri/ui/tests/learn/highlight-paint.test.ts — NEW
// Tests the ipc.learn.highlight → DOM paint latency. Target ≤16 ms.

import { describe, it, expect, beforeAll } from "vitest";
import { JSDOM } from "jsdom";
import { PIONEER_DDJ_FLX4_SVG } from "../../src/learn/controllers/pioneer_ddj_flx4.svg.js";
import { applyHighlight } from "../../src/learn/components/controller-stage.js";

const N_SAMPLES = 240;
const TARGET_MS = 16.0;

describe("ipc.learn.highlight → DOM paint latency", () => {
  let dom: JSDOM;
  let stage: HTMLElement;

  beforeAll(() => {
    dom = new JSDOM(
      `<!DOCTYPE html><html><body>
         <div id="learn-stage" class="learn-stage">${PIONEER_DDJ_FLX4_SVG}</div>
       </body></html>`,
    );
    stage = dom.window.document.getElementById("learn-stage")!;
  });

  it("P95 paint latency ≤ 16 ms", () => {
    const samples: number[] = [];
    const controls = ["play:A", "play:B", "cue:A", "eq_hi:A", "vol:A"];

    for (let i = 0; i < N_SAMPLES; i++) {
      const cid = controls[i % controls.length];
      const t0 = performance.now();
      applyHighlight(stage, {
        control_id: cid.split(":")[0],
        deck: cid.split(":")[1] || "",
        cue_color: "amber",
        cue_shape: "pulse-ring",
      });
      const t1 = performance.now();
      samples.push(t1 - t0);
    }

    samples.sort((a, b) => a - b);
    const p95 = samples[Math.floor(samples.length * 0.95)];
    console.log(`learn.highlight paint P95: ${p95.toFixed(3)} ms`);
    expect(p95).toBeLessThanOrEqual(TARGET_MS);
  });

  it("clears any prior highlight before painting new one", () => {
    applyHighlight(stage, {
      control_id: "play", deck: "A",
      cue_color: "amber", cue_shape: "pulse-ring",
    });
    applyHighlight(stage, {
      control_id: "cue", deck: "A",
      cue_color: "amber", cue_shape: "pulse-ring",
    });
    const lit = stage.querySelectorAll("[data-cue-color]");
    expect(lit.length).toBe(1);  // only the latest is lit
    expect(lit[0].getAttribute("data-control-id")).toBe("cue:A");
  });
});
```

### Code Example 7: __main__.py wiring (additive)

```python
# src/vibemix/__main__.py — EDIT (additive inside main() after MidiMirror init)

    # ... existing MidiMirror instantiation from P91 ...
    from vibemix.learn.midi_mirror import MidiMirror
    midi_mirror = MidiMirror(controller_state=midi_macos.controller_state)

    # NEW — Phase 92: wire LessonRuntime.
    from vibemix.learn.runtime import LessonRuntime
    from vibemix.learn.state import LearnState
    from vibemix.learn.progress import load_progress

    learn_state = LearnState()
    progress, was_corrupt = load_progress()
    lesson_runtime = LessonRuntime(
        learn_state=learn_state,
        midi_mirror=midi_mirror,
        controller_state=midi_macos.controller_state,
        ipc_router=ipc_router,
        progress_store=progress,  # mutable shared with runtime
    )
    if was_corrupt:
        # Emit a one-line toast via progress_state.
        from vibemix.ui_bus.learn_messages import LearnProgressState
        ipc_router.emit(LearnProgressState.make(
            action="snapshot",
            was_recovered=True,
            progress=progress.to_dict(),
        ).to_dict())
    asyncio.create_task(lesson_runtime.tick_loop(stop_event))
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `transitions` Python FSM library | `python-statemachine 3.1.2` | Modern declarative class-attr API; lighter install footprint (~30 KB vs ~150 KB) | The choice for v9.0 lesson runtime. |
| Naive `json.dump(open(path, "w"))` | `tmp.write_text + os.replace` atomic | Project convention (Phase 12 D-Area-4.4) | Mirror of `config_store.save()` — corruption-safe. |
| LLM-generated tutor scripts | Hand-authored JSON fixtures (TONE-02) | v9.0 SUMMARY §10 LOCKED | Slop-free by construction; AI only adds grounded citations. |
| Tutor prompt assembled inline per turn | `build_tutor_system_instruction(course_id, lesson_id, controller_id)` helper | v9.0 SUMMARY §6 | Composable; AST-gated lock at the tail. |

**Deprecated/outdated:**
- The v8.1 `LENS-03` direct call (`build_lens_instruction("tutor", "intermediate")`) is the right primitive but doesn't carry the lesson-specific course/controller/addendum frames; P92's `build_tutor_system_instruction` is a thin wrapper around the existing builder that adds those frames.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `python-statemachine 3.1.2` install footprint is ~30 KB with zero transitive runtime deps. | §Standard Stack | If transitive deps appear (unlikely — verified MIT pure-Python wheel), the install impact is no longer GREEN. Mitigation: confirm via `uv pip install python-statemachine && du -sh .venv/lib/.../statemachine*`. `[VERIFIED: PyPI wheel listing — pure Python, no native code]` |
| A2 | `_router_config._ROUTES` will gain a `"learn_tutor"` path that resolves to the same Gemini Flash model used by `live_coach` (e.g. `gemini-3.5-flash` + `"STANDARD"` ServiceTier). | §Open Q1 + LESSON-06 | If the planner ratifies "just reuse `live_coach`", no `_router_config` change; otherwise a 1-line edit. `[ASSUMED]` — pending Open Q1 ratification. |
| A3 | The 11 envelope shapes I propose match the SUMMARY §4 + UI-SPEC §Wiring contract intent. Specifically: `LearnHighlight` payload includes `expected_action` (so the webview can render the right key-hint), `LearnTutorSpeak` includes a `data_state` enum (active vs hint), `LearnProgressState` carries a `was_recovered: boolean` for corruption-recovery toasts. | §Code Example 1 | If the planner needs different fields, the schema is the source of truth and easy to amend before codegen runs. `[ASSUMED]` |
| A4 | `LessonRuntime.tick_loop()` running 1 Hz alongside the existing 30 Hz `ws_broadcast` does not cause the 30 Hz tick to stutter beyond its current variance. | §Pitfall 6 | If `on_enter_<state>` callbacks block on file I/O or LLM calls, the asyncio loop pauses. Mitigation: `loop.run_in_executor` for file I/O; `await` for LLM calls. Pinned by integration test `tests/runtime/test_ws_broadcast_30hz_under_lesson_load.py`. |
| A5 | The `validator.generated.mjs` ajv pre-compiled validator regenerates cleanly with the 11 new envelope definitions added to `messages.schema.json`. | §Pattern 3 | If the codegen step fails or produces a validator that rejects valid envelopes, the webview won't accept the 11 new envelope types. Verifiable in `npm run codegen:ipc` output + `scripts/check_ipc_schema.py` parity gate. |
| A6 | The "I got it" skip button's 45 s min-dwell can be implemented as a simple wall-clock check on `time.monotonic() - learn_state.lesson_started_at`. | §Pattern 1 LessonRuntime.min_dwell_elapsed | If users pause/resume the app, `time.monotonic()` doesn't suspend; the dwell counter keeps ticking through suspend. This is the correct behavior — pause/resume should NOT count as dwell. |
| A7 | The settings drawer's existing `vmx-settings-row` + `vmx-settings-row--destructive` CSS classes are reusable for the Reset Learn Progress row. | §Code Example 5 | If those classes don't exist (UI-SPEC asserts they do based on the recording-browser pattern), the new `learn-group.ts` needs to define them inline. Verifiable by grep `tauri/ui/src/settings/*.ts` for `vmx-settings-row`. |

## Open Questions

1. **Model-router path name for the tutor LLM call.**
   - What we know: CONTEXT.md cites `vibemix.llm.model_router.resolve("standard")` for the tutor LLM resolution. Verified via grep — there is NO `"standard"` key in `_router_config._ROUTES`. The existing keys are `live_coach`, `live_coach_openrouter`, `live_coach_tts`, `live_coach_tts_fallback`, `live_coach_tts_openrouter`, `debrief`, `debrief_tts`, `library_auto_tag`, `embedding`.
   - What's unclear: should the planner (a) reuse `live_coach` (same model, same tier), (b) add a new `learn_tutor` path to `_router_config._ROUTES` resolving to the same `gemini-3.5-flash` + `"STANDARD"` tier, or (c) rename one of the existing paths to a more generic name?
   - Recommendation: **Add a new `learn_tutor` path to `_router_config._ROUTES`** (1-line edit in the allowlisted file). Keeps the live co-host and the lesson tutor decoupled so future model swaps don't require both surfaces to move together. The planner should add a task: "edit `_router_config._ROUTES` to add `"learn_tutor": ("gemini-3.5-flash", "STANDARD"),`" — and update CONTEXT.md's `resolve("standard")` reference to `resolve("learn_tutor")`.

2. **Should `LearnTutorSpeak.tts_marker` be required or optional?**
   - What we know: UI-SPEC + CONTEXT both describe `tts_marker` as a string field. P92 ships no TTS (P93 lands the exemplar engine + likely the TTS audio path).
   - What's unclear: in P92 the field is always present in the JSON fixture (each beat has its own marker like `"L000.beat0"`). Required vs optional.
   - Recommendation: **Required.** Even though P92 doesn't synthesize audio, the marker is the contract; later phases (P93+) will use it to address audio cues. Default fixture value: `"L<lesson_id>.beat<N>"`.

3. **Does the 1-step "hello world" lesson need a `lesson_id` of `L0.00-press-play` or `L0.01-press-play`?**
   - What we know: UI-SPEC says `L0.00 OF 1` (one lesson in Course 0). The pattern `LX.NN` is the v9.0 REQ-ID prefix system.
   - What's unclear: zero-indexed (`L0.00`) or one-indexed (`L0.01`)?
   - Recommendation: **`L0.00-press-play` (zero-indexed).** Mirrors the `course_0` naming and frees up `L0.01` for a future stretch lesson without renaming.

4. **Does Course 0 ("hello world") get a `course_complete` envelope or does it just leave the user at `completed` state?**
   - What we know: `LearnCompleteLesson` envelope ships in P92. The "course completed" notion lands in P94 (Course 1) where multiple lessons exist.
   - What's unclear: when the user completes L0.00 (only lesson in Course 0), should the system emit a synthetic course-complete state, or just stay at `completed` indefinitely?
   - Recommendation: **Stay at `completed` for P92.** Course 0 is the demo; there's no further lesson to load. Loading L0.00 again from the (future) progress UI re-fires `LessonRuntime.load(...)` → `LearnState.current_lesson_id = "L0.00-press-play"` again → re-enters `loaded`. P94 introduces the multi-lesson sequencing.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `python-statemachine` | LessonRuntime FSM | ✗ (NEW) | `^3.1.2` to install | None — required |
| Python `>=3.12,<3.13` | All sidecar code | ✓ | 3.12.x (per `.venv/`) | — |
| `tauri` 2.x | (no Rust change in P92) | ✓ | Per `Cargo.toml` | — |
| `vite` + `vitest` + `jsdom` | Frontend build + test | ✓ | Per `package.json` | — |
| `ajv` pre-compiled (via codegen:ipc) | Envelope validation | ✓ | Per `package.json` | — |
| `mido` + `python-rtmidi` | (no new MIDI work in P92) | ✓ | Per `pyproject.toml` | — |
| `websockets` | ws:8765 server | ✓ | Per `pyproject.toml` | — |
| `google-genai` | Tutor LLM via model_router | ✓ | Per `pyproject.toml` | — |
| `GEMINI_API_KEY` env var | Tutor LLM auth (P92 ships shape only — P94 wires the call) | Optional in P92 | — | None — P92 doesn't actually make an LLM call yet; tutor_speak.text comes from fixture |

**Missing dependencies with no fallback:** `python-statemachine` — must install via `uv sync` after pyproject.toml edit.
**Missing dependencies with fallback:** none.

P92 adds exactly **1 new dependency**, fully resolvable via `uv sync`.

## Validation Architecture

> Required because `workflow.nyquist_validation: true` in `.planning/config.json`. Section drives VALIDATION.md.

### Test Framework

| Property | Value |
|----------|-------|
| Python framework | pytest (`PYTHONPATH=src python3 -m pytest -q`) |
| TS framework | vitest (`cd tauri/ui && npm test`) |
| TS spec framework (DOM-walking) | playwright (`cd tauri/ui && npx playwright test` — keyboard nav + axe-core) |
| Rust framework | `cargo test` (P92 has no Rust changes — confirms no regression) |
| Quick run command | `cd tauri/ui && npm test -- tests/learn/ && PYTHONPATH=src python3 -m pytest -q tests/learn/ tests/ipc/test_learn_envelope_parity_p92.py` |
| Full suite command | `PYTHONPATH=src python3 -m pytest -q && cd tauri/ui && npm test && npx playwright test tests/learn/` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| **TONE-02** | Lesson scripts are hand-authored JSON; no live LLM writes `tutor_speak.text` | unit (AST grep) | `pytest tests/learn/test_scripts_are_fixtures.py -x` | ❌ Wave 0 |
| **TONE-04** | Tutor system instruction includes 4-forbidden-moves lock + lock is last block | unit | `pytest tests/learn/test_tutor_system_instruction_lock.py -x` | ❌ Wave 0 |
| **LESSON-01** | LessonRuntime is sole writer of LearnState; no writes to MusicState/ControllerState | unit (AST grep) | `pytest tests/learn/test_runtime_invariants.py -x` | ❌ Wave 0 |
| **LESSON-01** | LessonRuntime full lifecycle: idle → load → begin → ack_action → finish → completed | unit | `pytest tests/learn/test_lesson_runtime_smoke.py::test_full_lifecycle -x` | ❌ Wave 0 |
| **LESSON-01** | LessonRuntime + ws_broadcast 30 Hz cadence integration | integration | `pytest tests/runtime/test_ws_broadcast_30hz_under_lesson_load.py -x` | ❌ Wave 0 |
| **LESSON-02** | 11 new envelopes round-trip via Python jsonschema | unit | `pytest tests/ipc/test_learn_envelope_parity_p92.py -x` | ❌ Wave 0 |
| **LESSON-02** | OneOf count parity (13 = 2 P91 + 11 P92) after schema edit + codegen | unit | `python3 scripts/check_ipc_schema.py` | ✅ Existing |
| **LESSON-02** | No new ws port (grep-gate continues green) | unit | `pytest tests/learn/test_no_new_ws_port.py -x` | ✅ Existing (P91) |
| **LESSON-03** | learn-progress.json corruption → fresh empty + recovery toast | unit | `pytest tests/learn/test_progress_persistence.py::test_corrupt_file_recovers_clean -x` | ❌ Wave 0 |
| **LESSON-03** | learn-progress.json atomic write (no half-truncation) | unit | `pytest tests/learn/test_progress_persistence.py::test_atomic_write -x` | ❌ Wave 0 |
| **LESSON-03** | Reset CLI subcommand wipes file | unit (cli) | `pytest tests/learn/test_progress_persistence.py::test_reset_cli -x` | ❌ Wave 0 |
| **LESSON-03** | Reset drawer button emits ipc.learn.progress_state { action: "reset" } | unit (vitest+jsdom) | `cd tauri/ui && npx vitest run tests/settings/learn-group.spec.ts` | ❌ Wave 0 |
| **LESSON-04** | Lesson advances on CC drop ≥30% range matching expected_action.control | unit | `pytest tests/learn/test_advancement_gates.py::test_cc_drop_30pct -x` | ❌ Wave 0 |
| **LESSON-04** | Lesson advances on button press matching expected_action.control + direction | unit | `pytest tests/learn/test_advancement_gates.py::test_button_press -x` | ❌ Wave 0 |
| **LESSON-04** | 3-strike escalation: 30s → strike 1 → 30s → strike 2 → 30s → strike 3 | unit (async) | `pytest tests/learn/test_advancement_gates.py::test_3_strike_escalation -x` | ❌ Wave 0 |
| **LESSON-04** | "I got it" skip blocked until 45s min-dwell elapsed | unit | `pytest tests/learn/test_advancement_gates.py::test_min_dwell_blocks_skip -x` | ❌ Wave 0 |
| **LESSON-04** | "I got it" skip works after 45s min-dwell elapsed | unit | `pytest tests/learn/test_advancement_gates.py::test_skip_after_dwell -x` | ❌ Wave 0 |
| **LESSON-05** | build_tutor_system_instruction composes all 5 fragments in correct order | unit | `pytest tests/learn/test_prompts.py::test_compose_order -x` | ❌ Wave 0 |
| **LESSON-05** | build_tutor_system_instruction reuses MOOD_PERSONAS["teacher"] (substring check) | unit | `pytest tests/learn/test_prompts.py::test_teacher_persona_present -x` | ❌ Wave 0 |
| **LESSON-05** | system_instruction_addendum cap (≤200 chars) enforced | unit | `pytest tests/learn/test_prompts.py::test_addendum_max_length -x` | ❌ Wave 0 |
| **LESSON-06** | No hardcoded model literal in `src/vibemix/learn/` (grep gate) | unit | `bash scripts/release/check_no_hardcoded_model.sh src/vibemix/learn/` | ✅ Existing |
| **LESSON-06** | model_router.resolve(<learn_tutor_path>) returns Gemini Flash model id | unit | `pytest tests/llm/test_model_router_learn_tutor.py -x` | ❌ Wave 0 (pending Open Q1) |
| **RENDER-04** | Highlight paint P95 ≤ 16 ms in jsdom synthetic harness | unit | `cd tauri/ui && npx vitest run tests/learn/highlight-paint.test.ts` | ❌ Wave 0 |
| **RENDER-04** | Highlight clears prior before painting new (single-active invariant) | unit | `cd tauri/ui && npx vitest run tests/learn/highlight-paint.test.ts::clears prior` | ❌ Wave 0 |
| **N/A — A11Y** | Tutor-speak dock screen-reader announcement on `data-state="active"` | spec (playwright) | `cd tauri/ui && npx playwright test tests/learn/test_tutor_speak_sr_announcement.spec.ts` | ❌ Wave 0 |
| **N/A — A11Y** | Hint state SR announcement (strike 1/2/3 fires ONCE each) | spec | (same SR test file) | ❌ Wave 0 |
| **N/A — A11Y** | "I got it" skip button keyboard reachable + space/enter fire | spec | `cd tauri/ui && npx playwright test tests/learn/test_keyboard_skip_reachable.spec.ts` | ❌ Wave 0 |
| **N/A — A11Y** | 45s min-dwell aria-disabled + tooltip wording | spec | `cd tauri/ui && npx playwright test tests/learn/test_min_dwell_aria.spec.ts` | ❌ Wave 0 |
| **N/A — A11Y** | Contrast on tutor `.now` line + hint italic + HUD elements | spec (axe-core) | `cd tauri/ui && npx playwright test tests/learn/test_contrast_p92.spec.ts` | ❌ Wave 0 |
| **N/A — Mascot regression** | Adding 11 envelopes doesn't break mascot frame handler | spec | `cd tauri/ui && npx playwright test tests/mascot/learn-envelope-doesnt-break-mascot.spec.ts` | ❌ Wave 0 (regression test from P13 mitigation) |

### Sampling Rate

- **Per task commit:** `cd tauri/ui && npm test -- tests/learn/` (vitest only — ~3-5 s) + `PYTHONPATH=src python3 -m pytest -q tests/learn/` (~5-8 s)
- **Per wave merge:** Full quick run + `tests/ipc/test_learn_envelope_parity_p92.py` + `tests/runtime/test_ws_broadcast_30hz_under_lesson_load.py` (~15 s)
- **Phase gate:** Full suite green — `PYTHONPATH=src python3 -m pytest -q && cd tauri/ui && npm test && npx playwright test tests/learn/`

### Wave 0 Gaps

- [ ] `tests/learn/test_runtime_invariants.py` — AST gate (single-writer + no MusicState/ControllerState writes) — LESSON-01
- [ ] `tests/learn/test_tutor_system_instruction_lock.py` — 4-forbidden-moves lock — TONE-04
- [ ] `tests/learn/test_scripts_are_fixtures.py` — no live LLM writes to tutor_speak.text — TONE-02
- [ ] `tests/learn/test_progress_persistence.py` — atomic + corruption recovery + reset — LESSON-03
- [ ] `tests/learn/test_lesson_runtime_smoke.py` — full lifecycle smoke test — LESSON-01
- [ ] `tests/learn/test_advancement_gates.py` — 3-strike + min-dwell + skip — LESSON-04
- [ ] `tests/learn/test_prompts.py` — build_tutor_system_instruction unit tests — LESSON-05
- [ ] `tests/ipc/test_learn_envelope_parity_p92.py` — 11 envelopes round-trip — LESSON-02
- [ ] `tests/runtime/test_ws_broadcast_30hz_under_lesson_load.py` — 30 Hz cadence pin — Pitfall 6
- [ ] `tests/llm/test_model_router_learn_tutor.py` — model_router path verification — LESSON-06 (pending Open Q1)
- [ ] `tauri/ui/tests/learn/highlight-paint.test.ts` — ≤16 ms paint gate — RENDER-04
- [ ] `tauri/ui/tests/learn/test_tutor_speak_sr_announcement.spec.ts` — A11Y aria-live
- [ ] `tauri/ui/tests/learn/test_keyboard_skip_reachable.spec.ts` — A11Y keyboard
- [ ] `tauri/ui/tests/learn/test_min_dwell_aria.spec.ts` — A11Y aria-disabled tooltip
- [ ] `tauri/ui/tests/learn/test_contrast_p92.spec.ts` — A11Y axe-core contrast
- [ ] `tauri/ui/tests/learn/test_hud_progress_dots_keyboard.spec.ts` — A11Y dot keyboard nav
- [ ] `tauri/ui/tests/mascot/learn-envelope-doesnt-break-mascot.spec.ts` — regression from P13
- [ ] `tauri/ui/tests/settings/learn-group.spec.ts` — drawer reset row unit test

*Existing test infrastructure covers: `scripts/check_ipc_schema.py` (oneOf count parity), `tests/learn/test_no_new_ws_port.py` (P91 — green and must stay green), `bash scripts/release/check_no_hardcoded_model.sh` (model literal grep gate).*

## Security Domain

> `security_enforcement` is implicit (config not set to false). Section included.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | The Learn webview is a same-origin local Tauri window; no user-auth surface. |
| V3 Session Management | no | No server-side session; ws:8765 is loopback-only. |
| V4 Access Control | no | No multi-user surface. |
| V5 Input Validation | yes | All 11 new envelopes are JSON-validated bidirectionally — Python via `jsonschema.Draft7Validator` (`_VALIDATOR.validate` in `ui_bus/messages.py:84`); TS via `validator.generated.mjs` pre-compiled ajv. `additionalProperties: false` on every payload. Critical for `LearnAck.value` (must be 0..127), `LearnHighlight.cue_color/cue_shape` (enum-constrained), `LearnTutorSpeak.text` (≤280 chars, maxLength enforced), `LearnTutorSpeak.citations[]` (regex-constrained to evidence-source forms). |
| V6 Cryptography | no | No new crypto. |
| V8 Sensitive Data | yes | `learn-progress.json` stores lesson completion timestamps (ISO-8601). NOT personally identifying. Local-machine-only under `~/.cache/vibemix/`. CLAUDE.md privacy rule (Hermes/LM-Studio paths off-limits) is NOT touched by P92. |
| V12 Files & Resources | yes | Lesson script JSON fixtures ship as bundled assets (no user upload). The fixture path is HARDCODED via `CURRICULUM[lesson_id].transcript_path` — no user-controllable path traversal possible. The progress file path `progress_path()` is HARDCODED to `~/.cache/vibemix/learn-progress.json` — no user-controllable component. |
| V13 API & Web Services | yes | ws:8765 is bound to 127.0.0.1 only (per existing `audio/__init__.py::WS_HOST` constant). No external network surface for the lesson runtime. The tutor LLM call (P94+) routes through `google-genai` over HTTPS to Gemini — existing pattern from the live co-host. |

### Known Threat Patterns for vibemix Tauri+Python stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Untrusted ws frame from spoofed client | Tampering | jsonschema validation on every frame (Python) + pre-compiled ajv (TS). `additionalProperties: false` strict. |
| Tutor system instruction injection via lesson JSON | Tampering | Lesson JSON fixtures ship in-tree (immutable bundled assets). User cannot modify the fixtures at runtime (read-only after install). The `system_instruction_addendum` is ≤200 chars + comes from the fixture — never from runtime user input. |
| Path-traversal via lesson_id | Tampering | `CURRICULUM` dict keys lesson_id; only registered IDs resolve to a transcript_path. Unknown lesson_id raises `KeyError`, never reaches the filesystem. |
| Progress file corruption (DoS) | DoS | Atomic write + corruption recovery (nuke + fresh empty) ensures a malicious or damaged file never wedges the runtime. |
| Tauri capability bypass | Elevation | P92 adds ZERO new Tauri commands. The settings drawer's `emitIpc("ipc.learn.progress_state", {...})` rides the existing ws bridge — no new Rust surface to gate. |

## Sources

### Primary (HIGH confidence — in-tree file:line verified)

- `src/vibemix/prompts/matrix.py:60-73` — `MOOD_PERSONAS["teacher"]` (LESSON-05 reuses, no new lens)
- `src/vibemix/prompts/matrix.py:241-251` — `COACH_CLOSING_BLOCK` (the "lock at the tail" precedent for `_FORBIDDEN_TUTOR_MOVES_LOCK`)
- `src/vibemix/prompts/matrix.py:767-899` — `build_system_instruction` (composer that `build_tutor_system_instruction` wraps)
- `src/vibemix/llm/model_router.py:69-91` — `resolve(path)` API
- `src/vibemix/llm/_router_config.py:30-52` — `_ROUTES` dict (Open Q1 ratification target)
- `src/vibemix/runtime/config_store.py:266-278` — atomic write pattern (`tmp.write_text` → `os.replace`)
- `src/vibemix/profile/storage.py:78-92` — secondary atomic-write reference
- `src/vibemix/ui_bus/learn_messages.py:30-154` — P91 dataclass pattern to extend with 11 more
- `src/vibemix/ui_bus/messages.py:84` — shared `_VALIDATOR` (jsonschema Draft-07)
- `src/vibemix/learn/midi_mirror.py` — P91 read-only pattern (reused by LessonRuntime)
- `src/vibemix/midi/state.py:118-484` — `ControllerState` (read-only consumer)
- `src/vibemix/runtime/ws_bus.py:276-460` — `IpcRouterBus` + `ws_broadcast` (existing emit path)
- `src/vibemix/__main__.py:843-852` — `main()` MidiMirror wiring point (P92 extends with LessonRuntime)
- `tauri/ui/src/ipc/messages.schema.json:2905-2947` — P91 envelope JSON Schema (template for P92's 11)
- `tauri/ui/scripts/codegen-ipc.mjs` — the codegen pipeline that regenerates `validator.generated.mjs`
- `tauri/ui/src/settings/SettingsDrawer.ts:909-927` — settings drawer group ordering + insertion pattern
- `tauri/ui/src/settings/components/group.ts:130-159` — `renderSettingsGroup` API (reused by LearnGroup)
- `tauri/ui/src/settings/components/confirm-dialog.ts` — `renderConfirmDialog` API (reused by reset confirm)
- `tauri/ui/src/settings/components/mascot-group.ts` — precedent for `learn-group.ts` pattern
- `tauri/ui/src/learn/components/controller-stage.ts` — P91 stage; P92 extends with `applyHighlight`
- `tauri/ui/src/learn/controllers/pioneer_ddj_flx4.svg.ts` — P91 SVG with `data-cue-color` + `data-cue-shape` empty slots
- `.planning/research/SUMMARY.md` — 14 LOCKED axes (especially §1, §4, §6, §9, §10)
- `.planning/research/PITFALLS.md:15-46` — P1 AI TUTOR TONE (TONE-02 / TONE-04 mitigation)
- `.planning/research/PITFALLS.md:405-423` — P12 PROGRESS PERSISTENCE (LESSON-03 mitigation)
- `.planning/research/PITFALLS.md:427-448` — P13 INTEGRATION REGRESSION (mascot + ipc count parity)
- `.planning/phases/91-controller-renderer-midi-mirror/91-RESEARCH.md` — closest precedent (envelope additions, AST gates, atomic patterns)
- `.planning/phases/91-controller-renderer-midi-mirror/91-01-SUMMARY.md` — P91-shipped IPC envelope precedent
- `.planning/phases/91-controller-renderer-midi-mirror/91-03-SUMMARY.md` — P91-shipped MidiMirror sole-writer precedent
- `.planning/phases/91-controller-renderer-midi-mirror/91-05-SUMMARY.md` — P91-shipped frontend webview precedent
- `.planning/phases/92-lesson-runtime-ai-highlight-contract/92-CONTEXT.md` — user-confirmed decisions
- `.planning/phases/92-lesson-runtime-ai-highlight-contract/92-UI-SPEC.md` — 6/6 PASS visual contract
- `.planning/REQUIREMENTS.md` — TONE-02 / TONE-04 / LESSON-01..06 / RENDER-04 verbatim
- `.planning/config.json` — `nyquist_validation: true`, `code_review: true`

### Secondary (MEDIUM — referenced via SUMMARY/PITFALLS, verified through code)

- `python-statemachine` 3.1.2 — verified on PyPI (2026-05-19 release; MIT; pure-Python). `[CITED: pypi.org/project/python-statemachine]`
- slopcheck verdict on `python-statemachine` — `[OK]` (clean; "name starts with 'python-' classic LLM naming pattern — package is established" note only)
- v8.1 LENS-03 / Phase 79 (in-tree shipped) — `build_lens_instruction` precedent for tutor lens reuse

### Tertiary (LOW)

- None — the spine is fully verified in-tree, and the one new dependency is mature.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every recommendation verified in-tree file:line; the ONE new dep (`python-statemachine 3.1.2`) verified on PyPI + slopcheck clean.
- Architecture: HIGH — every pattern (1 through 9) has an exact precedent in this repo (`config_store.save()` atomic write, `MOOD_PERSONAS["teacher"]` reuse, `IpcRouterBus.emit` envelope flow, `renderSettingsGroup` drawer extension, P91 SVG `data-cue-*` scaffolding, `_VALIDATOR.validate` jsonschema parity, AST-grep test patterns).
- Pitfalls: HIGH — every pitfall has either a CI gate, an AST-grep test, or a defer-to-KAAN-ACTION mitigation already pinned in CONTEXT.md / UI-SPEC.
- Open Question Q1 (model-router path name): MEDIUM — clear recommendation but pending planner ratification.

**Research date:** 2026-05-28
**Valid until:** 2026-06-28 (30 days — stable spine, one mature dep). Reset on: (a) `python-statemachine` 4.x release with breaking API changes, (b) Gemini Flash 3.5 deprecation by Google, (c) any P91 invariant test going red on the live-tuning-or-brain branch.

---

**Ready for planning.** Every locked decision in CONTEXT.md is reconciled with an exact-precedent code pattern. The planner can write tasks against:

- 5 new Python file paths under `src/vibemix/learn/`: `runtime.py`, `state.py`, `curriculum.py`, `prompts.py`, `progress.py`
- 1 new Python fixture directory: `src/vibemix/learn/transcripts/hello_world/01_press_play.json`
- 3 new TS file paths under `tauri/ui/src/learn/lesson/`: `hud.ts`, `tutor-dock.ts`, `skip-button.ts`
- 1 new TS file path under `tauri/ui/src/settings/components/`: `learn-group.ts`
- 11 new oneOf entries + 11 new definitions in `tauri/ui/src/ipc/messages.schema.json`
- 11 new Python dataclasses in `src/vibemix/ui_bus/learn_messages.py` (additive after the P91 pair)
- 1 new dep line in `pyproject.toml`: `python-statemachine>=3.1.2,<4.0`
- 1 wiring block in `src/vibemix/__main__.py` (LessonRuntime instantiation + tick_loop task)
- 1 new method in `tauri/ui/src/learn/components/controller-stage.ts`: `applyHighlight(stage, payload)`
- 1 new method in `tauri/ui/src/learn/learn-window.ts`: 11 new envelope handlers
- 1 row insertion in `tauri/ui/src/settings/SettingsDrawer.ts`: `body.append(LearnGroup())`
- ~10 new test files under `tests/learn/`, `tests/ipc/`, `tauri/ui/tests/learn/`, `tauri/ui/tests/settings/`, `tauri/ui/tests/mascot/`
- 1 discrete `npm run codegen:ipc` task (CLAUDE.md mandate)
- 1 discrete `uv sync` task (after pyproject.toml edit)
- 1 optional `_router_config._ROUTES` line edit (Open Q1 ratification)
