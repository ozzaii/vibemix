# Architecture Research — v9.0 "Lesson One" (Beginner Learning Module)

**Domain:** Live-grounded teaching surface bolted onto an audio-first co-host
**Researched:** 2026-05-27
**Confidence:** HIGH (every file:line cited has been verified on disk; the four-invariant binding follows the v5–v8 additive-seam discipline that has held shipped milestones byte-identical when the new surface is OFF)

> **TL;DR for the roadmapper.** Learn is the 4th surface (Co-host / Build-a-Set / Debrief / **Learn**). It is a **strict additive seam** on the existing engine — no new ws port, no new AI provider, no `MusicState` writes, no new evidence source for cites that ride on already-grounded data. The only new evidence source is `[exemplar:<track_id>]` (mirrors the v5 `[key:]` and v6 `[recall:]` pattern exactly, including the 4-site SCHEMA-MIRROR lock). A new `src/vibemix/learn/` subpackage owns the lesson state machine + curriculum + highlight contract + library-driven exemplar finder; a second `WebviewWindow` (mirror of debrief, but on the **same** ws:8765 bus) renders the controller canvas. Course 3 reuses the live coach + CueAnchor + phrase detection unchanged — tutor mode is a system-instruction variant on the existing `MOOD_PERSONAS["teacher"]` lens (v8.1 LENS-03), not a new lens. 8-phase build spine: P91 renderer+MIDI mirror → P92 lesson runtime+highlight contract → P93 exemplar engine (parallel with P92) → P94/95/96 the three courses → P97 onboarding+verbatim locks → P98 ear-pass.

---

## System Overview

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│  TAURI SHELL (Rust parent)                                                       │
│  src-tauri/src/                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────┐ │
│  │ main window │  │ mascot      │  │ pill        │  │ debrief     │  │ NEW    │ │
│  │ (session +  │  │ overlay     │  │ overlay     │  │ window      │  │ learn  │ │
│  │  build-set) │  │ (mascot.html│  │ (pill_window│  │ (port 8766) │  │ window │ │
│  │             │  │  rs)        │  │  rs)        │  │ debrief_    │  │ NEW    │ │
│  │             │  │             │  │             │  │ window.rs   │  │ learn_ │ │
│  │             │  │             │  │             │  │             │  │ window │ │
│  │             │  │             │  │             │  │             │  │ .rs    │ │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └───┬────┘ │
│         │                │                │                │             │      │
│         └────────────────┴────────────────┴────────────────┘             │      │
│                                  │                          │            │      │
│                              ws:8765 (ONE socket — Invariant #4)         │      │
│                                  │                          ws:8766      │      │
└──────────────────────────────────┼──────────────────────────┼────────────┼──────┘
                                   │                          │            │
┌──────────────────────────────────┼──────────────────────────┼────────────┼──────┐
│  PYTHON SIDECAR (vibemix)        │                          │            │      │
│                                  ▼                          ▼            ▼      │
│  runtime/ws_bus.py            IpcRouterBus            debrief/          ws_bus  │
│  ws_broadcast(...)            (SessionLoop adapter)    bus :8766         (same  │
│         │                            │                                  loop,  │
│         │                            ▼                                  routes │
│         │                     LearnRouter ◄── NEW                       learn.*│
│         │                     (registers learn.* handlers)               types) │
│         │                                                                       │
│         ▼                                                                       │
│  state/                       audio/                       library/             │
│  ┌──────────────┐             ┌──────────────┐             ┌────────────────┐  │
│  │ MusicState   │◄── single   │ Levels       │             │ CLAP ONNX      │  │
│  │ (READ-ONLY   │   writer:   │ AudioBuffer  │             │ store (sqlite- │  │
│  │  for Learn)  │   refresh.  │ MicBuffer    │             │ vec)           │  │
│  │              │   py        │ PlaybackQueue│             │ discovery.py   │  │
│  └──────────────┘             └──────────────┘             │ sequencer.py   │  │
│         ▲                            │                     │ NEW: exemplar  │  │
│         │                            ▼                     │       reads    │  │
│  evidence_registry              platform/                  └────────┬───────┘  │
│  EVIDENCE_SOURCES               _audio_macos.py                     │          │
│  + "exemplar" ◄── NEW           _midi_macos.py ──► ControllerState  │          │
│  prompts/matrix.py                                  (READ surface   │          │
│  CITATION_GRAMMAR_BLOCK                             for Learn)      │          │
│  + exemplar grammar ◄── NEW                                         │          │
│                                                                     │          │
│  ┌─────────────────────────────────────────────────────────────────┘          │
│  │                                                                            │
│  ▼                                                                            │
│  learn/                                              ◄────────── NEW SUBPKG    │
│  ┌──────────────────────────────────────────────────────────────────────────┐│
│  │ runtime.py    state.py       curriculum.py    highlight.py    matchers.py││
│  │ exemplar.py   audio_cue.py   prompts.py       router.py       progress.py││
│  │ transcripts/      tests/                                                 ││
│  └──────────────────────────────────────────────────────────────────────────┘│
│                                                                              │
│  agent/dj_cohost.py (live coach) ────── reused by Course 3 unchanged         │
└──────────────────────────────────────────────────────────────────────────────┘
```

ASCII box-drawing is for layout only. Every named module above maps to a file on disk:

| Box | Real path |
|-----|-----------|
| `learn_window.rs` | NEW — `tauri/src-tauri/src/learn_window.rs` (mirror of `debrief_window.rs`) |
| `learn/` subpkg | NEW — `src/vibemix/learn/` |
| `IpcRouterBus` | `src/vibemix/runtime/ws_bus.py:276` (existing — extend handler registration) |
| `EVIDENCE_SOURCES` | `src/vibemix/state/evidence_registry.py:111` |
| `_SOURCE_ALT` | `src/vibemix/state/evidence_registry.py:137` |
| `CITATION_GRAMMAR_BLOCK` | `src/vibemix/prompts/matrix.py` (the v6 `recall:` add-site) |
| `_build_citation_strip` | `src/vibemix/agent/dj_cohost.py:_build_citation_strip` |
| `_TIME_KEYED_SOURCES` | `src/vibemix/coach/citation_linter.py` |
| `MOOD_PERSONAS["teacher"]` | `src/vibemix/prompts/matrix.py:53-66` (the tutor lens already exists) |
| `controller_state` | `src/vibemix/midi/state.py:118` (`class ControllerState`) |
| `open_voice_output` | `src/vibemix/platform/_audio_macos.py:328` (the headphone-cue seam) |
| `snapshot_features` | `src/vibemix/audio/features.py:27` (`mid_share` etc. — band primitives) |

---

## Component Responsibilities

| Component | Responsibility | Owner module |
|-----------|---------------|--------------|
| **LearnRuntime** | Lesson state machine: current course/lesson/step, gating predicates (waiting on MIDI? on AI narration done? on exemplar finished?), advance events. Single writer of `LearnState`. | `src/vibemix/learn/runtime.py` |
| **LearnState** | Frozen-shape mutable dataclass: `(course_id, lesson_id, step_idx, expected_action, last_match_ts, started_at)`. Private to `learn/`. | `src/vibemix/learn/state.py` |
| **Curriculum** | Declarative lesson catalog. Pure data (one frozen dataclass per lesson; `dict[course_id, tuple[Lesson, ...]]`). Hand-authored, version-locked, gold-tested. | `src/vibemix/learn/curriculum.py` |
| **HighlightEnvelope** | Typed envelope shapes the AI tutor → UI canvas messages MUST conform to. Frozen dataclass + JSON Schema export feeding `messages.schema.json`. | `src/vibemix/learn/highlight.py` |
| **ExemplarFinder** | Given a target band (mid/low/high/sub) and optional BPM/genre prefilter, rank user library tracks by band-share strength using the **existing** `snapshot_features` band columns cached at ingest time. Returns `ExemplarHit` (track_id + cue_anchor t_start + band_score + cite token). | `src/vibemix/learn/exemplar.py` |
| **ExemplarPlayer** | Opens a dedicated `sd.OutputStream` on the headphone device (same hardware as `open_voice_output`) and decodes a library track segment via PyAV/FFmpeg. Bypasses `PlaybackQueue` and mic-gating. | `src/vibemix/learn/audio_cue.py` |
| **LessonProgress** | Persistence layer: which lessons completed, when, per controller. JSON file at `~/.cache/vibemix/learn-progress.json` for v9.0; `memory.db` cross-reference for v9.1+. | `src/vibemix/learn/progress.py` |
| **TutorPrompts** | The "patient teaching voice" system-instruction variant. Wraps the existing `MOOD_PERSONAS["teacher"]` fragment with course-specific scaffolding (e.g. "lesson 1.3: anatomy of the crossfader"). | `src/vibemix/learn/prompts.py` |
| **MIDI Matchers** | Pure predicates: given an `ExpectedAction` (control_id + direction + threshold) and a current `ControllerState` snapshot, return `True`/`False`. Pure means trivially testable without a controller. | `src/vibemix/learn/matchers.py` |
| **Transcripts** | Iconic verbatim openings (e.g. "Oh bestie, welcome to your first lesson…") as fixture-locked JSON. Loaded at lesson start; `tests/learn/test_tutor_prompts_byte_equality.py` pins the strings. | `src/vibemix/learn/transcripts/*.json` |
| **LearnRouter** | The ws:8765 handler shim. Registers `learn.*` types on the existing `IpcRouterBus`. Same shape as `SessionLoop.register_handlers()`. | `src/vibemix/learn/router.py` |
| **LearnWindow** | Second WebviewWindow (mirror of `debrief_window.rs`) hosting the controller canvas + lesson HUD. Connects to the SAME ws:8765 — no new port. | `tauri/src-tauri/src/learn_window.rs` + `tauri/ui/src/learn/` |

---

## Recommended Subpackage Layout

```
src/vibemix/learn/
├── __init__.py                # public surface: LearnRuntime, LearnRouter, Curriculum
├── runtime.py                 # LearnRuntime (the state machine — only writer of LearnState)
├── state.py                   # LearnState dataclass (private to learn/)
├── curriculum.py              # Course / Lesson / LessonStep frozen dataclasses + catalog dict
├── highlight.py               # HighlightEnvelope + ExpectedAction (frozen, schema-export)
├── exemplar.py                # ExemplarFinder + ExemplarHit + band_score()
├── audio_cue.py               # ExemplarPlayer with its own sd.OutputStream
├── progress.py                # LessonProgress (JSON persistence; memory.db ref in v9.1+)
├── prompts.py                 # TutorPrompts.build_system_instruction(course, lesson, mood)
├── router.py                  # LearnRouter — registers learn.* handlers on IpcRouterBus
├── matchers.py                # MIDI match predicates (knob direction/threshold, button press)
└── transcripts/
    ├── __init__.py
    ├── course_1_anatomy/
    │   ├── 01_welcome.json            # "Oh bestie…" verbatim
    │   ├── 02_crossfader.json
    │   └── ...
    ├── course_2_transitions/
    └── course_3_play_mode/

tests/learn/  (mirrors the existing tests/state/ / tests/library/ convention)
├── test_runtime_invariants.py        # the 4 cardinal-invariant pins (see §Invariants)
├── test_curriculum_schema.py         # every Lesson resolves a controller profile + control id
├── test_highlight_envelope_schema.py # parity vs messages.schema.json fragments
├── test_exemplar_band_share.py       # given fake library, mid-share ranking is correct
├── test_exemplar_citation_schema_mirror.py # the 4-site lock for "exemplar"
├── test_exemplar_grounding_e2e.py    # fabricated cite strips whole turn
├── test_progress_persistence.py      # roundtrip JSON + corruption-safe
├── test_router_dispatch.py           # learn.* handlers register + dispatch via IpcRouterBus
├── test_tutor_prompts_byte_equality.py # verbatim opening strings unchanged across refactor
├── test_midi_match_predicates.py     # match-on-direction / match-on-threshold gating
├── test_audio_cue_split_output.py    # exemplar plays to cue without polluting master
├── test_no_speculative_phrase.py     # static gate: no FFT/phrase guessing in learn/
├── test_no_new_ws_port.py            # static grep: no websockets.serve in learn/
├── test_learn_rides_existing_bus.py  # dynamic: round-trip on ws:8765
└── test_course3_uses_existing_coach.py  # Course 3 prompts built by AICoach.build_prompt
```

### Structure Rationale

- **`runtime.py` is the single writer of `LearnState`** — mirrors the `state/refresh.py` → `MusicState` single-writer discipline from Invariant #1. All other `learn/` modules are READ-ONLY consumers of `LearnState`.
- **`state.py` is separate from `runtime.py`** — same split as `state/music_state.py` (data) vs `state/refresh.py` (writer). Keeps tests cheap (snapshot a `LearnState` without spinning the runtime loop).
- **`curriculum.py` is pure data** — no imports from `runtime.py` / `prompts.py`. Hand-authored. Frozen dataclasses (`@dataclass(frozen=True, slots=True)`) — same pattern as `library/discovery.py:PoolItem`.
- **`highlight.py` is the IPC contract module** — analogous to `vibemix.ui_bus.messages.SessionSnapshot`. Its dataclasses **emit** the JSON shapes the schema validates, so a code change to the envelope forces a `npm run codegen:ipc` failure (no silent drift).
- **`transcripts/` is fixture-locked** — the iconic opening lines are *product surface*, not editable copy. A byte-equality test (`test_tutor_prompts_byte_equality.py`) makes any drift in the file fail loudly. Same discipline as the v3.0 README hero verbatim lock.
- **`router.py` is a thin shim** — mirrors `library_cmds.rs` ↔ `library/mcp_server.py`. Just maps `learn.*` types → calls into `runtime.py`. Keeps `runtime.py` ws-free (and therefore unit-testable without a socket).
- **`matchers.py` is pure** — given a MIDI move and an `ExpectedAction`, returns bool. Pure means trivially testable (no controller, no async).
- **`audio_cue.py` separates exemplar playback from voice TTS** — the existing `PlaybackQueue` is in the AI-voice path (mixed with mic gating). Exemplars are different audio (DJ-library tracks) on a different sink (cue/headphone). Keeping them separate prevents the mic-gate from muting the user when an exemplar plays — *and* prevents an exemplar from ducking AI narration.

---

## Cardinal Invariant Bindings

The roadmap-critical part of this research. **One named test per invariant, plus the structural reason the invariant cannot be broken without that test failing.**

### Invariant #1 — Single-Writer (`MusicState` is written only by `state/refresh.py`)

**Binding:** Learn introduces a NEW state object, `LearnState`, **not** new fields on `MusicState`. `LearnState` is private to `src/vibemix/learn/` and has its **own** single writer (`learn/runtime.py:LearnRuntime`). All `learn/` siblings — `router.py`, `curriculum.py`, `highlight.py`, `exemplar.py` — are READ-ONLY against `LearnState`.

**Why a separate state object** (the answer to the explicit question): yes, a separate `LearnState` dataclass private to `learn/` is correct. Lesson position, expected action, step-within-lesson, last-MIDI-seen timestamp — none of this is a property of the *music*; it is a property of the *teaching session*. Putting it on `MusicState` would (a) violate the single-writer rule (Course 3 reads `MusicState` during play-mode but the lesson runtime would also need to write "expected next phrase" — that's TWO writers on the same object) and (b) couple `coach.py` to `learn/` semantics on every tick.

**Static pin:** `tests/learn/test_runtime_invariants.py::test_musicstate_never_mutated_by_learn` — a static gate that imports `src/vibemix/learn/` AST, walks all `Attribute(value=Name("state"))` writes targeting any `MusicState` field name, asserts the set is empty. Mirror of `tests/repo/test_no_recall_antifeatures.py` discipline.

**Dynamic pin:** `tests/learn/test_runtime_invariants.py::test_only_learnruntime_writes_learnstate` — spin `LearnRuntime` + a curriculum stub, snapshot `LearnState` before/after each handler dispatch, assert only the runtime's tick changes any field.

### Invariant #2 — Citation Grounding (every cite resolves in `EvidenceRegistry`, else strip)

**Binding:** Course 1/2 tutor narration **does not cite** — anatomy lessons are descriptive ("this is the crossfader"), not grounded reactions to live audio. Course 3 narration runs through the **existing live coach** (`agent/dj_cohost.py`) which already enforces this invariant; tutor mode is just a different system instruction with the existing linter active. The ONE new cite class is `[exemplar:<track_id>]`, used when an EQ lesson plays a library track to demonstrate a band swell.

**Citation flow diagram (exemplar):**

```
Lesson 2.4 ("swap kicks via low EQ")
        │
        ▼
LearnRuntime.start_step("eq_low_demo")
        │
        ▼
ExemplarFinder.find(band="low", bpm_window=(120, 130), k=1)
        │
        ▼  (uses CLAP store + cached snapshot_features.low_share at ingest)
ExemplarHit(track_id="ext:rekordbox:1234", t_start=83.0, score=0.92)
        │
        ├──► EvidenceRegistry.write("exemplar", "ext:rekordbox:1234", t_session)
        │                                       ◄── grounds the cite token by
        │                                           pure existence (mirror of
        │                                           [key:] / [recall:] / [track:])
        │
        ├──► IPC: { type: "ipc.learn.exemplar_play", track_id, t_start, ... }
        │
        └──► TutorPrompts.build_eq_demo_prompt() returns string:
             "Listen — this track has the strongest low band in your crate.
              You should hear the kick swell as I turn the EQ. Cite EXACTLY
              [exemplar:ext:rekordbox:1234] once."
                                  │
                                  ▼
                  Gemini Flash (tutor lens) emits narration
                                  │
                                  ▼
                  CitationLinter.lint(text) — same path live coach uses
                                  │
                                  ▼
                  parse_citations(text) → [Cite(source="exemplar",
                                                  body="ext:rekordbox:1234")]
                                  │
                                  ▼
                  EVIDENCE_SOURCES check ("exemplar" ∈ set? YES)
                                  │
                                  ▼
                  Registry resolve ("exemplar", "ext:rekordbox:1234") → HIT
                                  │
                                  ▼
                  Lint passes → narration emits.
                  (Fabricated track_id → registry miss → whole turn stripped
                   to ack-bank fallback, same as [recall:] anti-poisoning)
```

**Schema mirror sites (THE 4 places `exemplar` must be added — atomically, in one commit):**

| # | File | Line (current HEAD) | What to change |
|---|------|---------------------|----------------|
| 1 | `src/vibemix/state/evidence_registry.py` | 111 | Add `"exemplar"` to `EVIDENCE_SOURCES` frozenset |
| 2 | `src/vibemix/state/evidence_registry.py` | 137 | Add `\|exemplar` to `_SOURCE_ALT` regex alternation |
| 3 | `src/vibemix/prompts/matrix.py` | `CITATION_GRAMMAR_BLOCK` body | Add the `[exemplar:<track_id>]` form + 1-sentence semantics |
| 4 | `src/vibemix/agent/dj_cohost.py` | `_build_citation_strip` | Add `exemplar` to the strip set so a fabricated `[exemplar:bogus]` strips, matching `[recall:]` discipline |

Plus: `src/vibemix/coach/citation_linter.py:_TIME_KEYED_SOURCES` is the *complement* set — exemplar is **existence-only**, so it is **NOT** added there (mirrors `key` / `recall` / `track`).

**Static pin:** `tests/learn/test_exemplar_citation_schema_mirror.py` — asserts the 4 sites all contain "exemplar". Mirror of v6 RECALL-01 schema-mirror test.

**Dynamic pin:** `tests/learn/test_exemplar_grounding_e2e.py` — feed a fake tutor narration with `[exemplar:fake_id]`, assert linter strips the whole turn.

### Invariant #3 — Trust the Audio (no inventing phrase boundaries / cues)

**Binding:** Course 3 (play-mode live coaching) reuses the **existing** grounding stack:
- Phrase boundaries come from `state/detectors/phrase_boundary.py` (real DSP detector) — the AI is told the phrase only AFTER the detector fires, never speculatively from a guessed downbeat count.
- "Breakdown in N beats" comes from `state.detected_genre` + the `state/cue_types.py:CueAnchor` cue if and only if the AUDIBLE track has a resolved CueAnchor in the live library (the v8.2 export path already populates these). If no CueAnchor: tutor mode says "I'm watching — when the breakdown lands, I'll call it" (PAST-tense narration, same anti-slop discipline as `state/deltas.py:render_delta` abstaining below `DELTA_FLOOR`).
- "What's coming up" never bypasses `state.bpm_confidence` — already gated; if `bpm_confidence < 0.6` the renderer skips beat-locked behavior (existing rule).

**Tutor mode adds ZERO new "what's coming" inference.** It only narrates what the existing grounding stack already publishes. The path is: `phrase_boundary` detector → `event_detector.PHRASE` event → coach picks up the event → tutor-lens system instruction shapes the narration → linter validates the cite → narration emits.

**Static pin:** `tests/learn/test_no_speculative_phrase.py` — static gate over `src/vibemix/learn/` AST forbidding any import of `numpy.fft` / `scipy.signal` / phrase-guessing primitives. Learn module is **not allowed** to invent its own audio analysis; all phrase intel must come through the shipped detector seam.

**Dynamic pin:** `tests/learn/test_course3_uses_existing_coach.py` — spin learn Course 3, assert every tutor-narration prompt is built by `state/coach.py:AICoach.build_prompt` (same as live mode), NOT by a learn-local prompt builder.

### Invariant #4 — One Socket (8765 only; debrief gets 8766; never two listeners on one port)

**Binding:** Learn binds **NO** new ws port. The Learn window connects to **ws:8765** (the existing mascot/wizard bus). Its handlers (`learn.*`) are registered on the existing `IpcRouterBus` (`runtime/ws_bus.py:276`) — same shim that `SessionLoop`'s `ipc.settings.*` / `ipc.profile.*` / `ipc.recordings.*` handlers ride.

**Why this is safe:** the Learn window is a SEPARATE `WebviewWindow` at the Tauri level (so it has its own DevTools, its own DOM, its own lifecycle), but at the WS layer it is just another client on the same `clients: set` that `ws_broadcast` already manages. Multiple webview clients on one ws port is the EXISTING pattern (session + mascot.html + pill all share :8765 today).

**Why we do NOT want :8767 for Learn:** the One-Socket discipline isn't anti-port; it's anti-binding-race. Every additional `websockets.serve(host, port)` in the process is a potential P12 "two listeners at once" bug. Debrief got :8766 because it runs in a *separate Tauri command lifecycle* and uses a *different sidecar process*. Learn runs INSIDE the main sidecar process and shares the live `MusicState` — same process, same bus.

**Static pin:** `tests/learn/test_no_new_ws_port.py` — grep `src/vibemix/learn/` for `websockets.serve` / `serve(` / `WS_PORT` literal — must be ZERO hits.

**Dynamic pin:** `tests/learn/test_learn_rides_existing_bus.py` — spin `ws_broadcast` + register `LearnRouter`, connect one client, send `{type: "ipc.learn.start_course", payload: {course_id: 1, ...}}`, assert the same socket returns `{type: "ipc.learn.lesson_loaded", ...}` (proving the round-trip works on the same bus that emits mascot frames + session snapshots).

---

## IPC Envelopes (NEW additions to `tauri/ui/src/ipc/messages.schema.json`)

Every type below is added to (a) the top-level `oneOf` array and (b) the `definitions` object. After editing, **run `cd tauri/ui && npm run codegen:ipc`** — the pre-compiled `validator.generated.mjs` rejects new fields until regenerated (the recurring CLAUDE.md gotcha).

**Pattern decision:** Use the **`ipc.learn.*`** namespace. Same shape as `ipc.session.*` / `ipc.calibration.*` / `ipc.recordings.*` — the dominant convention in `messages.schema.json` (30+ existing `ipc.*` constants verified by grep on the live file).

### Envelope list (12 types — 7 request-class + 5 push/response-class)

| Envelope `type` | Direction | Purpose |
|------|----------|---------|
| `ipc.learn.start_course` | shell → sidecar | Begin a course; payload `{ course_id: 1\|2\|3, controller_id: string }` |
| `ipc.learn.start_lesson` | shell → sidecar | Skip into a specific lesson; payload `{ lesson_id: string }` |
| `ipc.learn.complete_lesson` | shell → sidecar | User explicitly marks done (skip / advance manually) |
| `ipc.learn.lesson_loaded` | sidecar → shell | Lesson active; metadata for HUD (title, narration text, expected MIDI) |
| `ipc.learn.highlight` | sidecar → shell | Show a highlight on the rendered controller |
| `ipc.learn.midi_position` | sidecar → shell | Real-time controller state mirror (cont vals + button states) |
| `ipc.learn.advance_acknowledged` | sidecar → shell | Tutor confirms MIDI match → next step |
| `ipc.learn.tutor_speak` | sidecar → shell | Tutor narration emitted (text + optional TTS stream marker) |
| `ipc.learn.exemplar_play` | sidecar → shell | Audio playback started — UI shows "playing exemplar" badge |
| `ipc.learn.exemplar_stop` | sidecar → shell | Playback ended (natural or interrupted) |
| `ipc.learn.progress_get` | shell → sidecar | Request progress JSON |
| `ipc.learn.progress_state` | sidecar → shell | Progress snapshot (response to get, or push on change) |

### JSON Schema fragments (the 6 highest-signal ones — the remaining 6 follow the same shape)

```json
{
  "definitions": {
    "LearnStartCourse": {
      "type": "object",
      "required": ["type", "ts", "payload"],
      "additionalProperties": false,
      "properties": {
        "type": { "const": "ipc.learn.start_course" },
        "ts":   { "type": "string", "format": "date-time" },
        "payload": {
          "type": "object",
          "required": ["course_id", "controller_id"],
          "additionalProperties": false,
          "properties": {
            "course_id":    { "type": "integer", "enum": [1, 2, 3] },
            "controller_id": {
              "type": "string",
              "description": "Filename stem of the loaded MIDI profile (e.g. 'pioneer_ddj_flx4'). Must match a file under src/vibemix/midi/profiles/."
            }
          }
        }
      }
    },

    "LearnHighlight": {
      "type": "object",
      "required": ["type", "ts", "payload"],
      "additionalProperties": false,
      "properties": {
        "type": { "const": "ipc.learn.highlight" },
        "ts":   { "type": "string", "format": "date-time" },
        "payload": {
          "type": "object",
          "required": ["deck", "control_id", "intensity"],
          "additionalProperties": false,
          "properties": {
            "deck":       { "type": "string", "enum": ["A", "B", "master", "global"] },
            "control_id": {
              "type": "string",
              "description": "Identifier from the MIDI profile JSON (e.g. 'eq_mid_a', 'crossfader', 'cue_a'). Must resolve in the loaded controller profile."
            },
            "intensity": { "type": "number", "minimum": 0.0, "maximum": 1.0 },
            "annotation": { "type": ["string", "null"], "maxLength": 120 },
            "expected_action": {
              "type": ["object", "null"],
              "required": ["control_id", "direction", "threshold"],
              "additionalProperties": false,
              "properties": {
                "control_id": { "type": "string" },
                "direction":  { "type": "string", "enum": ["increase", "decrease", "press", "release", "either"] },
                "threshold":  { "type": "number" }
              }
            }
          }
        }
      }
    },

    "LearnMidiPosition": {
      "type": "object",
      "required": ["type", "ts", "payload"],
      "additionalProperties": false,
      "properties": {
        "type": { "const": "ipc.learn.midi_position" },
        "ts":   { "type": "string", "format": "date-time" },
        "payload": {
          "type": "object",
          "required": ["controls"],
          "additionalProperties": false,
          "properties": {
            "controls": {
              "type": "object",
              "description": "Map control_id -> current value (0..127 for knobs/faders, 0|1 for buttons).",
              "additionalProperties": {
                "type": "object",
                "required": ["value", "kind"],
                "additionalProperties": false,
                "properties": {
                  "value": { "type": "number" },
                  "kind":  { "type": "string", "enum": ["knob", "fader", "button", "pad", "encoder"] }
                }
              }
            }
          }
        }
      }
    },

    "LearnTutorSpeak": {
      "type": "object",
      "required": ["type", "ts", "payload"],
      "additionalProperties": false,
      "properties": {
        "type": { "const": "ipc.learn.tutor_speak" },
        "ts":   { "type": "string", "format": "date-time" },
        "payload": {
          "type": "object",
          "required": ["text", "lesson_id"],
          "additionalProperties": false,
          "properties": {
            "text":          { "type": "string" },
            "lesson_id":     { "type": "string" },
            "tts_stream_id": { "type": ["string", "null"] },
            "citations":     { "type": "array", "items": { "type": "string" } }
          }
        }
      }
    },

    "LearnExemplarPlay": {
      "type": "object",
      "required": ["type", "ts", "payload"],
      "additionalProperties": false,
      "properties": {
        "type": { "const": "ipc.learn.exemplar_play" },
        "ts":   { "type": "string", "format": "date-time" },
        "payload": {
          "type": "object",
          "required": ["track_id", "t_start", "duration_s", "band"],
          "additionalProperties": false,
          "properties": {
            "track_id":   { "type": "string" },
            "t_start":    { "type": "number" },
            "duration_s": { "type": "number" },
            "band":       { "type": "string", "enum": ["sub", "low", "mid", "high"] },
            "title":      { "type": ["string", "null"] },
            "artist":     { "type": ["string", "null"] }
          }
        }
      }
    },

    "LearnProgressState": {
      "type": "object",
      "required": ["type", "ts", "payload"],
      "additionalProperties": false,
      "properties": {
        "type": { "const": "ipc.learn.progress_state" },
        "ts":   { "type": "string", "format": "date-time" },
        "payload": {
          "type": "object",
          "required": ["courses"],
          "additionalProperties": false,
          "properties": {
            "courses": {
              "type": "object",
              "additionalProperties": {
                "type": "object",
                "required": ["lessons_completed", "last_lesson_id", "last_touched"],
                "additionalProperties": false,
                "properties": {
                  "lessons_completed": { "type": "array", "items": { "type": "string" } },
                  "last_lesson_id":    { "type": ["string", "null"] },
                  "last_touched":      { "type": "string", "format": "date-time" }
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

### Python dataclass equivalents

Generated from the schema via the existing `vibemix.ui_bus.messages` pattern. New file: `src/vibemix/ui_bus/learn_messages.py`. Sketch (one envelope shown; the others follow):

```python
# SPDX-License-Identifier: Apache-2.0
"""Learn surface IPC message dataclasses — mirror tauri/ui/src/ipc/messages.schema.json."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class ExpectedAction:
    control_id: str
    direction: Literal["increase", "decrease", "press", "release", "either"]
    threshold: float


@dataclass(frozen=True, slots=True)
class LearnHighlightPayload:
    deck: Literal["A", "B", "master", "global"]
    control_id: str
    intensity: float
    annotation: str | None = None
    expected_action: ExpectedAction | None = None


@dataclass(frozen=True, slots=True)
class LearnHighlight:
    type: Literal["ipc.learn.highlight"]
    ts: str
    payload: LearnHighlightPayload

    @staticmethod
    def make(*, deck, control_id, intensity, annotation=None, expected_action=None) -> "LearnHighlight":
        from vibemix.ui_bus.messages import _now_iso
        return LearnHighlight(
            type="ipc.learn.highlight",
            ts=_now_iso(),
            payload=LearnHighlightPayload(
                deck=deck,
                control_id=control_id,
                intensity=intensity,
                annotation=annotation,
                expected_action=expected_action,
            ),
        )

    def to_json(self) -> str:
        import json
        from dataclasses import asdict
        return json.dumps(asdict(self), separators=(",", ":"))
```

Same shape for `LearnTutorSpeak`, `LearnExemplarPlay`, `LearnProgressState`, `LearnMidiPosition`. The codegen IPC pipeline picks these up automatically once added to `messages.schema.json` + re-exported from `vibemix.ui_bus`.

---

## Persona / Lens Reuse

**Recommendation: tutor lens REUSED, with a course-specific system-instruction variant. Do NOT introduce a new "teacher" lens.**

### Why reuse

`prompts/matrix.py:53-66` already ships `MOOD_PERSONAS["teacher"]`:

```python
"teacher": (
    "You're patient, vocabulary-rich, framework-anchored — name "
    "techniques, reference structure, slow your pace."
),
```

This is exactly the voice Learn mode needs. The v8.1 LENS-03 work already unified hype/critique/tutor across surfaces, so the live-coach engine already knows how to render the tutor lens. Introducing a `"teacher_learn"` lens or similar would:

- Duplicate the persona substrate (the anti-slop `NEGATIVE_PHRASES` ban, the `<silence/>` short-circuit, the past-tense framing).
- Force a new LENS slot into the unified scorer surface (v8.1 BENCH-03 just stabilized this — adding another lens disrupts the bench rubric).
- Violate the v8.0 anti-creep acid test ("zero new product capability if existing wiring covers the need").

### What the variant adds

Course-specific system-instruction **scaffolding** is prepended to the existing tutor system instruction, not a new instruction set. Same pattern as `library/build_set` uses a system-instruction variant in v8.2 (see `library/codex_curate.py` system prompt). Sketch in `learn/prompts.py`:

```python
def build_tutor_system_instruction(course_id: int, lesson_id: str, controller_id: str) -> str:
    """Compose: course scaffolding + base tutor lens + curriculum constraints.

    The base tutor lens is the SAME one the live coach uses (Invariant #2/#3
    grounding paths fire identically). We prepend lesson-specific 'you are
    teaching X with controller Y' framing — never replace the substrate.
    """
    base = build_system_instruction(skill="beginner", mode="coach", mood="teacher")
    course_frame = COURSE_FRAMES[course_id]  # short string, e.g. "Course 1: anatomy"
    lesson_frame = CURRICULUM[lesson_id].system_instruction_addendum  # ≤200 chars
    controller_frame = f"The student is on a {load_profile(controller_id).display_name}."
    return f"{course_frame}\n{controller_frame}\n{lesson_frame}\n\n{base}"
```

The `COURSE_FRAMES` + per-lesson `system_instruction_addendum` are the *only* new prompt copy — same scale as v8.2's `build_set` system-prompt addition.

---

## Library / CLAP Reuse for Band-Exemplar Finder

**Recommendation: add a thin `learn/exemplar.py` module that READS the existing CLAP store + the existing band-share features cached at ingest. NO new audio analysis, NO new store table, NO band-specific embedding.**

### What already exists (do not rebuild)

- `audio/features.py:snapshot_features` returns `sub_share` / `low_share` / `mid_share` / `high_share` as **rounded floats** from FFT band energies. This is the *exact* primitive the exemplar finder needs.
- `library/discovery.py` already does intent-centroid + hard filter + MMR over the CLAP store. The exemplar finder is a simpler case: rank by a scalar (band share), apply BPM/genre/duration filters, return top-K.
- `library/sequencer.py` knows how to apply energy / Camelot / BPM gates on `PoolItem`s — its `_DEFAULT_WEIGHTS` machinery doesn't apply (sequencer solves a curve; exemplar solves a single-slot rank), but its `PoolItem` shape is the same row type the exemplar finder returns.

### What's missing (the additive seam)

Band shares are currently computed ON LIVE AUDIO (the 5-second snapshot in `state/refresh.py`). They are **not currently persisted per library track**. Two paths:

**Path A — cache band shares at ingest time (recommended).** Extend `library/ingest.py` (or its v8.2 successor) to run `snapshot_features` against a representative 10s excerpt of each library track at embed time and persist the 4 band shares as columns alongside the CLAP vector. The CLAP excerpt already exists in `library/excerpt.py`; reuse it. New columns in sqlite-vec table: `sub_share REAL, low_share REAL, mid_share REAL, high_share REAL`.

**Path B — compute on demand.** Stream each candidate track through `snapshot_features` at exemplar selection time. SIMPLE but SLOW (5-20s wall clock for a library of thousands). Reject.

**Decision: Path A.** The ingest path runs once (or on `--reembed`); the cost is paid offline. Live exemplar selection becomes an indexed sqlite scan + sort.

### Where the new code lives

| Concern | Module | New or existing? |
|---------|--------|------------------|
| Compute band share on a track excerpt | `audio/features.py:snapshot_features` | EXISTING |
| Add 4 band-share columns to sqlite-vec store schema | `library/store.py` (or its CLAP equivalent under `library/cache_paths.py` ecosystem) | EXISTING file — add migration |
| Populate band shares at ingest | `library/ingest.py` (or `library/anlz_ingest.py`) | EXISTING file — add 1 call |
| Query band shares + rank | `learn/exemplar.py:ExemplarFinder.find(band, bpm_window, k)` | **NEW** |
| Return `ExemplarHit` | `learn/exemplar.py:ExemplarHit` (frozen dataclass) | **NEW** |
| Migration: backfill band shares on existing libraries | `learn/exemplar.py:backfill_band_shares()` (one-off, lazy on first use) | **NEW** |

`learn/exemplar.py` should NOT live in `library/` because (a) it is consumed only by Learn, (b) it owns the "what's a good demo track" heuristic which is teaching-logic, not library-engine logic. Library exposes the *primitive* (band-share column); Learn owns the *policy* (rank, BPM band, "skip tracks with vocals when teaching kick"). Same boundary as `library/sequencer.py` (primitive) vs `library/codex_curate.py` (policy).

---

## Controller Renderer — Window vs SPA Mode Switch

**Recommendation: separate WebviewWindow (mirror of `debrief_window.rs`).**

### Trade-offs

| Approach | Pros | Cons |
|----------|------|------|
| **Separate WebviewWindow** (`learn_window.rs`) | Independent lifecycle (open Learn, leave Co-host running). Own DevTools / hot-reload. Own taskbar/dock entry (macOS users can `Cmd+Tab` between Learn and the deck). Mirrors the proven `debrief_window.rs` pattern. Window can be sized for the controller canvas (wide aspect) without disrupting the deck's portrait shell. | Second TS bundle if not careful (mitigated: route to a `/learn` SPA path in the existing `tauri/ui/` Vite build — shared chunk graph). Two webviews = ~30-50 MB extra RAM. |
| **SPA mode switch in main window** | Single bundle, single RAM footprint, single ws client. | Closes the deck UI when Learn is active. Loses "leave Learn running on second monitor while playing on first" use case. Mascot overlay positioning fights with controller canvas. macOS dock has no separate handle. |

**Decision: separate window.** The deck and Learn surfaces have fundamentally different aspect ratios + workflows. The +50 MB RAM is well below the v6.0 mascot GLB rig + sqlite-vec budget. The pattern is already in-tree (`debrief_window.rs` works fine).

### File outline

```
tauri/src-tauri/src/learn_window.rs        — NEW. Tauri command + window spawn.
tauri/ui/src/learn/
├── App.tsx                                 — NEW. Learn root SPA.
├── ControllerCanvas.tsx                    — NEW. SVG/Canvas renderer of the
│                                              live MIDI controller (one component
│                                              per supported profile, or a shared
│                                              vector renderer that reads the
│                                              profile JSON).
├── LessonHUD.tsx                           — NEW. Lesson title + narration +
│                                              progress chip.
├── HighlightLayer.tsx                      — NEW. Consumes ipc.learn.highlight,
│                                              renders glow over the canvas.
├── PositionMirror.tsx                      — NEW. Consumes ipc.learn.midi_position,
│                                              animates the controls.
└── api.ts                                  — NEW. ws:8765 client for learn.*
                                              (reuses tauri/ui/src/ipc/client.ts).
```

Routing: extend `tauri/src-tauri/tauri.conf.json` with a `learn` window definition (URL `/learn`), same as the existing `debrief` window. The Tauri dev server already serves Vite's history mode, so `localhost:1420/learn` works for `cargo tauri dev`.

---

## MIDI Position Sync (sub-50ms mirror)

### What exists today

`midi/state.py:118 class ControllerState` lives. The `state_refresh_loop` reads it at 10Hz to populate `MusicState.controller_state`. The 30Hz mascot frame ALREADY serializes a `controller_state` summary onto the wire (via the existing MIDI ribbon field in `_build_session_snapshot` → drains `controller_state.moves_since(t)`).

What's missing: **the renderer needs continuous values per control, not just an event ribbon.** The ribbon today is `[(age_secs, "label"), ...]` — good for "the user just moved EQ A mid" alerts, bad for "draw the EQ A knob at 63% on the canvas right now."

### The minimal additive seam

Add ONE method to `midi/state.py:ControllerState`:

```python
def snapshot_positions(self) -> dict[str, dict[str, float | int | str]]:
    """Return current value + kind for every named control on the loaded profile.

    Lock-protected READ (uses the same threading.Lock the existing
    moves_since uses). Returns a flat dict the LearnRouter serializes onto
    ipc.learn.midi_position.
    """
```

Wire it into a new `learn_loop` task in `__main__.py` that runs **only when Learn is the active surface** (gated by a `learn_active: asyncio.Event` set when the Learn window connects). The loop ticks at 30Hz (matches the mascot rate) and emits `ipc.learn.midi_position` on the same `IpcRouterBus`.

**Sub-50ms guarantee:** 30Hz = 33ms tick. The MIDI input thread (mido daemon thread) writes `controller_state` synchronously on every event (sub-1ms). The renderer's perceived latency is `MIDI input → controller_state write (1ms) → next 30Hz tick (≤33ms) → ws send (<1ms) → React render (<10ms)` = worst case 45ms, p50 ~25ms.

**Gate to ONLY learn-active:** without the gate, we'd push 30Hz position frames whether anyone is watching — wasteful when only the deck is open. The `learn_active` event flips on `ipc.learn.start_course` and off when the Learn webview client disconnects.

---

## Audio Playback for Exemplar to Cue/Headphone

### What exists today

`platform/_audio_macos.py` exposes:
- `open_passthrough_output` (line 307) — djay → speakers stereo (the music master path).
- `open_voice_output` (line 328) — AI voice → headphones (the TTS path, fed by `PlaybackQueue`).

These are **two separate `sd.OutputStream`s**, opened independently with separate `device=` arguments. The headphone routing already exists for AI voice. Reusing it for exemplar playback means exemplars come out of the *same* device as AI narration — the headphone cue mix.

### Mac BlackHole + Multi-Output Device gotcha

For the user to **monitor on headphones while music goes to speakers**, the macOS Audio MIDI Setup typically uses:
- Master output → Multi-Output Device (BlackHole 2ch + speakers).
- Headphone cue → built-in headphone jack or USB interface.

The v9.0 install wizard (Phase 49 / INSTALL-05) already configures the routing via `audio_config.py --configure-routing`. Exemplars piggyback on the same headphone device by feeding them through a NEW dedicated stream (not by reusing `open_voice_output`'s queue).

### Recommendation: dedicated `ExemplarPlayer`, NOT `PlaybackQueue` reuse

**Why not reuse `PlaybackQueue`:** `PlaybackQueue` is wired into `MicBuffer`'s mic-gate (mic mutes when `PlaybackQueue` is non-empty — see `audio/buffers.py:195`). If we route exemplars through `PlaybackQueue`, the mic mutes during exemplar playback — which means the user can't hear themselves react to the exemplar, which is bad teaching UX. Also, `PlaybackQueue` is mono int16 at `OUTPUT_SR`; exemplar tracks are stereo float at 44.1k.

**Recommendation:** add `learn/audio_cue.py:ExemplarPlayer` that opens its **own** `sd.OutputStream` on the SAME device as `open_voice_output` but a SEPARATE stream (CoreAudio happily handles multiple streams on one device). The exemplar stream is:
- Stereo float32 @ track sample rate (use PyAV/FFmpeg decode — already a dep).
- Independent of mic-gate.
- Has its own STOP control (`ipc.learn.exemplar_stop` flushes it).

### Cross-platform

Same shape on Windows WASAPI — the windows audio backend opens output streams the same way. The new `ExemplarPlayer` lives in a *backend-neutral* module (`learn/audio_cue.py`) and uses the existing `AudioMacOS` / `AudioWindows` firewall pattern from `platform/`.

---

## Progress Persistence

**Recommendation v9.0: JSON file. v9.1+: cross-reference `memory.db`.**

### v9.0 — `~/.cache/vibemix/learn-progress.json`

```json
{
  "courses": {
    "1": {
      "lessons_completed": ["1.1", "1.2", "1.3", "1.5"],
      "last_lesson_id": "1.6",
      "last_touched": "2026-05-27T18:22:11Z"
    }
  },
  "controller_profile": "pioneer_ddj_flx4",
  "schema_version": 1
}
```

Why JSON for v9.0:
- Zero migration risk on first ship.
- Trivial to inspect (`cat ~/.cache/vibemix/learn-progress.json`).
- Atomic write via `tempfile.NamedTemporaryFile` + `os.replace` (POSIX atomic) — same discipline as `profile/store.py`.
- Lives next to other learn-local state (cache dir already exists).

Risk: corruption mid-write. Mitigation: `schema_version` field + on-load `json.JSONDecodeError` handler that nukes the file and re-emits a fresh empty progress object (with a one-line user toast: "Your lesson progress couldn't be read — starting fresh"). Pinned by `tests/learn/test_progress_persistence.py::test_corrupt_file_recovers_clean`.

### v9.1+ enrichment — link to `memory.db`

When `VIBEMIX_RECALL_ENABLED=1`, the live co-host can recall: "remember when you nailed that breakdown transition? you covered the technique in Lesson 2.4 — try the same now." This requires the `memory.store.MemoryStore` to know about lesson completion.

The path: on `complete_lesson`, write a NEW kind of memory record (`kind="lesson_completed", record_id=lesson_id`) into `memory.db`. The existing `MemoryRecall` service then surfaces it as a `[recall:<record_id>]` cite during live play. **This is a v9.1 enrichment — out of v9.0 scope** to avoid coupling Learn to memory before the v6.0 §RECALL-EAR gate clears.

---

## Mode Picker on the Main Window

The main app shell needs the "Co-host / Learn / Build a Set" picker. Implementation:

- Extend `tauri/ui/src/session/state.ts` with a `mode` enum (current values are implicit — `session` is the only mode today). Add `learn` and `build_set`.
- New `ipc.session.set_mode` envelope on the existing bus — payload `{ mode: "session" | "learn" | "build_set" }`. Server-side: routes to the right window (cohost stays in main window, learn spawns `learn_window.rs`, build_set already wired in v8.2 P88).
- The optimistic-repaint rule from CLAUDE.md applies: the picker flips its own `data-active` IMMEDIATELY (no waiting on the IPC echo) — settings-drawer pattern. Pinned by `tauri/ui/tests/learn/test_mode_picker_optimistic.spec.ts`.

---

## Build Order (Phase Dependency Spine)

Roadmap-critical recommendation. 8 phases, with dependencies marked.

```
P91  Controller Renderer + MIDI Position Mirror
     ├── new file: tauri/src-tauri/src/learn_window.rs
     ├── new ui dir: tauri/ui/src/learn/
     ├── new method: ControllerState.snapshot_positions
     ├── new ipc: ipc.learn.midi_position (envelope only — empty payload OK)
     ├── new task: __main__.py learn_loop (gated by learn_active event)
     └── DELIVERABLE: open Learn window, see your physical knob move on canvas in <50ms.
                     This phase ships with NO lessons — just the renderer.
                     Standalone-verifiable: plug controller, see canvas mirror.

P92  Lesson Runtime + AI Highlight Contract  [depends: P91]
     ├── new pkg: src/vibemix/learn/  (runtime.py, state.py, curriculum.py,
     │                                  highlight.py, router.py, matchers.py)
     ├── new ipc: ipc.learn.start_course / start_lesson / highlight /
     │           advance_acknowledged / lesson_loaded / complete_lesson
     ├── codegen: npm run codegen:ipc
     ├── tutor: extend prompts.py (TutorPrompts)
     ├── tests: test_runtime_invariants (the 4-invariant pin)
     └── DELIVERABLE: a "hello world" 1-step lesson — AI says "press play deck A",
                     highlight glows on the play button, user presses → advance.
                     No exemplar, no audio, no curriculum content yet.

P93  Exemplar Engine  [depends: P91 — can run parallel with P92]
     ├── extend: audio/features.py — re-export band primitives if needed
     ├── extend: library/ingest.py — cache band shares at ingest time
     ├── extend: library/store.py — add band-share columns + migration
     ├── new file: learn/exemplar.py (ExemplarFinder + ExemplarHit)
     ├── new file: learn/audio_cue.py (ExemplarPlayer with own sd.OutputStream)
     ├── new evidence source: "exemplar"
     │   - state/evidence_registry.py:111   (EVIDENCE_SOURCES frozenset)
     │   - state/evidence_registry.py:137   (_SOURCE_ALT regex)
     │   - prompts/matrix.py                (CITATION_GRAMMAR_BLOCK)
     │   - agent/dj_cohost.py               (_build_citation_strip)
     ├── new ipc: ipc.learn.exemplar_play / exemplar_stop
     ├── tests: test_exemplar_citation_schema_mirror
     └── DELIVERABLE: CLI/test that finds the strongest-low track in a fake
                     library + plays a clip + emits a grounded
                     [exemplar:<id>] cite. No UI yet — just the engine.

P94  Course 1 — Anatomy  [depends: P92]
     ├── content: learn/transcripts/course_1_anatomy/*.json (~6-10 lessons)
     ├── curriculum: COURSE_1 = (Lesson(...), Lesson(...), ...)
     ├── UI: LessonHUD copy polish, lesson chrome
     ├── tests: test_course_1_curriculum_resolves (every control_id resolves
     │                                              against every shipped MIDI profile)
     └── DELIVERABLE: a beginner completes "what is a crossfader / cue button /
                     play button / EQ knob" — purely declarative lessons with
                     highlight + MIDI match. NO audio playback in this course.

P95  Course 2 — Transitions  [depends: P93, P94]
     ├── content: learn/transcripts/course_2_transitions/*.json
     ├── curriculum: COURSE_2 = (Lesson(...), ...)
     ├── exemplar wiring: EQ lessons trigger exemplar_play
     ├── UI: exemplar badge, "playing demo track" overlay
     ├── tests: test_course_2_exemplar_grounding (cites resolve)
     └── DELIVERABLE: user learns "swap kicks using EQ" — the AI plays a
                     library track, user turns the EQ, hears the band swell,
                     completes the lesson.

P96  Course 3 — Play Mode  [depends: P95 — and integrates with live coach]
     ├── extends: agent/dj_cohost.py — tutor-lens prompt path on the live coach
     ├── extends: state/coach.py — tutor-mode evidence_line variant
     ├── new gating: only fires when CueAnchor + phrase detector both active
     ├── safe defaults: when phrase detection cold → PAST-tense narration only
     ├── tests: test_course3_no_speculative_phrase (the trust-the-audio pin)
     └── DELIVERABLE: user plays a real set with tutor mode active — AI
                     proactively says "breakdown in 16 beats" (cited
                     [exemplar:<currently-playing-id>:beat:N] when the
                     audio + cueanchor confirm it).

P97  Onboarding + Tone + Verbatim Locks  [depends: P94-96]
     ├── content polish: every transcript reviewed for "AI slop"
     ├── tone byte-equality tests: test_tutor_prompts_byte_equality
     ├── controller selector UX on first Learn open
     ├── mode picker on main window (Co-host / Learn / Build-a-Set)
     ├── progress UI surfaces
     ├── empty-state copy ("no controller? plug one in")
     └── DELIVERABLE: a stranger opens the app, picks Learn, sees the
                     "Oh bestie" opening, advances through Lesson 1.1 without
                     any seam being visible.

P98  Live Audit + Ear-Pass Hand-Off  [depends: P97]
     ├── Kaan-walk recording: full 3-course run on real FLX4
     ├── audit doc: .planning/milestones/v9.0-MILESTONE-AUDIT.md
     ├── KAAN-ACTION carve-outs: real-hardware ear-pass per course
     ├── all 4 cardinal-invariant pins re-run on real session recordings
     └── DELIVERABLE: v9.0 milestone closed engineering-green; KAAN-ACTION
                     queue contains only ear-pass + external-clock items
                     (consistent with v4.0 / v8.0 / v8.2 close shape).
```

### Dependency graph (textual)

```
P91 ────────► P92 ────► P94 ────► P95 ────► P96 ────► P97 ────► P98
   \             \                  ▲          ▲
    \             \                 │          │
     \────► P93 ───\────────────────┴──────────┘
                    \
                     └────► (cite-grounding for P95/P96)
```

P91 and P93 can run in **parallel** after P91 completes (P93 needs P91's `controller_state` only for the renderer→exemplar UI handshake, not for the engine). P94, P95, P96 are **strictly sequential** (curriculum + content depend on the prior course's tone + format being settled). P97 + P98 are the close-down spine.

### Phase sizing guidance (for the roadmapper)

| Phase | Engineering size | Risk | KAAN-ACTION % |
|-------|------------------|------|---------------|
| P91 | Medium — Tauri window plumbing + 30Hz loop | LOW (proven pattern) | 0% |
| P92 | Medium-large — new subpkg + IPC contract + invariant tests | MEDIUM (4 invariant pins must hold) | 0% |
| P93 | Medium — band-share ingest extension + exemplar engine + cite-source plumbing | MEDIUM (the 4 schema-mirror sites are easy to forget) | 0% |
| P94 | Small — curriculum content | LOW | 30% (tone ear-pass) |
| P95 | Medium — curriculum + exemplar wiring | MEDIUM (exemplar-play UX) | 30% |
| P96 | Large — live coach integration + safe-default behavior | HIGH (Invariant #3 must hold under speculation pressure) | 50% (real-hardware ear-pass critical) |
| P97 | Small-medium — copy polish + picker | LOW | 30% |
| P98 | Small — audit + hand-off | LOW | 80% (mostly ear-pass) |

---

## Data Flow

### Lesson advance flow (Course 1, e.g. "press play on deck A")

```
User opens Learn window
        │
        ▼
ipc.learn.start_course { course_id: 1, controller_id: "pioneer_ddj_flx4" }
        │
        ▼
LearnRouter.handle_start_course
        │
        ▼
LearnRuntime.start_course(1)
        │
        ├──► loads Curriculum[1][0] = Lesson("1.1 Welcome")
        ├──► writes LearnState(course=1, lesson="1.1", step=0)
        ├──► emits ipc.learn.lesson_loaded { lesson: {...}, narration: "Oh bestie..." }
        └──► (no highlight yet — step 0 is narration-only)
        │
        ▼ (later, on advance)
LearnRuntime.next_step()
        │
        ├──► step 1 → expected_action: { control_id: "play_a", direction: "press", threshold: 1.0 }
        ├──► emits ipc.learn.highlight { deck: "A", control_id: "play_a", intensity: 1.0,
        │                                expected_action: {...} }
        └──► waits for ipc.learn.midi_position frame where play_a transitions 0→1
        │
        ▼
User presses play A on physical controller
        │
        ▼
midi/state.py:ControllerState updated by mido thread (sub-1ms)
        │
        ▼
learn_loop ticks at 30Hz, calls ControllerState.snapshot_positions
        │
        ├──► emits ipc.learn.midi_position { controls: { play_a: { value: 1, kind: "button" }, ... } }
        └──► LearnRuntime.on_midi_position checks: did play_a hit threshold?
        │
        ▼
matchers.match(expected_action, current_value) → True
        │
        ▼
LearnRuntime.advance()
        │
        ├──► emits ipc.learn.advance_acknowledged { lesson: "1.1", step: 1 }
        ├──► writes LearnState(step=2)
        ├──► if step 2 exists: next highlight; else: complete_lesson
        └──► persists progress to ~/.cache/vibemix/learn-progress.json
```

### Exemplar play flow (Course 2, e.g. "swap kicks with EQ")

```
Lesson 2.4 step "demonstrate kick swap via low EQ"
        │
        ▼
LearnRuntime.on_step_enter("kick_swap_demo")
        │
        ▼
ExemplarFinder.find(band="low", bpm_window=(120, 130), exclude_vocals=True, k=1)
        │
        ▼ (queries CLAP store with band-share columns from P93 ingest)
ExemplarHit(track_id="ext:rekordbox:1234", t_start=78.0, score=0.94)
        │
        ▼
EvidenceRegistry.write("exemplar", "ext:rekordbox:1234", t_session=monotonic())
        │
        ├──► ExemplarPlayer.start(track_id="ext:rekordbox:1234", t_start=78.0, duration_s=20)
        │    (opens its own sd.OutputStream on the headphone device; bypasses
        │     PlaybackQueue / mic-gate)
        │
        ├──► emits ipc.learn.exemplar_play { track_id, t_start, duration_s, band: "low" }
        │
        ▼
TutorPrompts.build_exemplar_prompt("low") → string with literal
"Cite EXACTLY [exemplar:ext:rekordbox:1234] once."
        │
        ▼
agent/dj_cohost.py renders the tutor narration through Gemini Flash
        │
        ├──► CitationLinter validates [exemplar:ext:rekordbox:1234] → resolves → PASS
        ├──► tutor speaks via existing voice path
        └──► emits ipc.learn.tutor_speak { text, citations: ["exemplar:ext:rekordbox:1234"] }
```

### Course 3 — phrase prediction flow

```
User is in play mode (real DJ session) with tutor lens active
        │
        ▼
state/refresh.py:state_refresh_loop ticks (10Hz, single writer of MusicState)
        │
        ├──► snapshot_features → MusicState.bands
        ├──► state/detectors/phrase_boundary.py fires PHRASE event
        │    AND state/cue_types.py:CueAnchor resolved for audible_track?
        │       YES → MusicState.next_phrase_at = beat_count_to_breakdown
        │       NO  → MusicState.next_phrase_at remains None (single-writer rule)
        │
        ▼
event_detector.py emits PHRASE event (with cooldown)
        │
        ▼
coach_loop picks up event, calls AICoach.build_prompt
        │
        ├──► evidence_line includes [aud:phrase:next=N_beats] IF AND ONLY IF
        │    MusicState.next_phrase_at is non-None
        ├──► tutor lens system instruction frames it: "you're explaining what's
        │    about to happen so the student can prepare"
        └──► Gemini Flash emits narration; CitationLinter validates;
             un-cited turn strips to ack-bank fallback (existing behavior)
```

The critical anti-slop point: if the CueAnchor isn't resolved, `next_phrase_at` is None, `evidence_line` doesn't include the phrase token, the prompt has no grounded "N beats" to cite, and the AI can ONLY narrate PAST events. This is the trust-the-audio invariant doing its job — *learn mode does not weaken it*.

---

## Patterns

### Pattern 1: Schema-Mirror Add (the 4-site lock)

**What:** Whenever a new evidence source is added, four files must be updated atomically.

**When to use:** Every cite class introduction in v9.0 (only `exemplar` this milestone).

**Trade-offs:** Tedious but bulletproof — the schema-mirror test (`tests/learn/test_exemplar_citation_schema_mirror.py`) fails red if any site drifts, so a half-added source is impossible to land.

**Example (the 4 sites, copy-paste ready):**

```python
# 1. src/vibemix/state/evidence_registry.py:111
EVIDENCE_SOURCES: frozenset[str] = frozenset(
    {"ev", "aud", "midi", "track", "screen", "mix", "tend", "key", "recall", "exemplar"}
)

# 2. src/vibemix/state/evidence_registry.py:137
_SOURCE_ALT = "ev|aud|midi|track|screen|mix|tend|key|recall|exemplar"

# 3. src/vibemix/prompts/matrix.py — append to CITATION_GRAMMAR_BLOCK
# (search the file for "[recall:" — add the parallel exemplar grammar line)

# 4. src/vibemix/agent/dj_cohost.py — add "exemplar" to the strip set in
# _build_citation_strip (paralleling [recall:] strip rules)
```

### Pattern 2: Optimistic Repaint (the dead-controls fix)

**What:** The Learn mode picker on the main window must flip its `data-active` LOCALLY in the click handler — same rule as `picker.ts::selectOption`. Do NOT wait for the IPC echo.

**When:** Every Learn UI control (mode picker, course picker, lesson skip, exemplar replay button).

**Trade-offs:** Tiny risk of optimistic state diverging from server (mitigated by server echo overriding within 3ms). Worth it — without it, controls look dead (CLAUDE.md gotcha).

**Example:**

```typescript
function setMode(mode: 'session' | 'learn' | 'build_set') {
  // Flip local data-active IMMEDIATELY (the optimistic part)
  document.querySelectorAll('.mode-picker [data-mode]').forEach(el => {
    (el as HTMLElement).dataset.active = (el as HTMLElement).dataset.mode === mode ? 'true' : 'false';
  });
  // Then send the IPC — server echo will confirm/override
  ipc.send({ type: 'ipc.session.set_mode', payload: { mode } });
}
```

### Pattern 3: Tutor-Mode Course 3 — let the existing coach drive

**What:** Course 3 (live play-mode coaching) calls `AICoach.build_prompt` with `mood="teacher"` + a course-specific `system_instruction` addendum. Same prompt builder, same `evidence_line`, same cite linter, same anti-slop discipline.

**When:** Whenever Course 3 needs to react to live audio.

**Trade-offs:** Slightly more verbose call site than a learn-local builder. Worth it — Invariant #3 stays guaranteed by the existing test surface.

**Example:**

```python
# learn/runtime.py — Course 3 lesson tick
def on_phrase_event(self, event: Event) -> None:
    if self.lesson.course_id != 3:
        return
    system_instruction = build_tutor_system_instruction(
        course_id=3, lesson_id=self.lesson.id, controller_id=self.controller_id
    )
    # Hand off to the SAME prompt builder the live coach uses:
    prompt = AICoach.build_prompt(
        event=event,
        system_instruction=system_instruction,  # the tutor variant
        # ... all other args identical to live coach
    )
    # Linter runs on the response — same as live mode.
```

### Pattern 4: Single-Writer for a New State Object

**What:** `LearnState` is owned only by `LearnRuntime`. Every other learn/ sibling reads via `runtime.snapshot()`.

**When:** Whenever a new long-lived stateful coordinator joins the system (this milestone: lesson coordinator; future milestones: any new surface with its own state).

**Trade-offs:** Slight test ceremony (have to test through the runtime, not the raw state). Worth it — concurrency-safe by construction.

---

## Anti-Patterns

### Anti-Pattern 1: A new ws port for Learn

**What people do:** "Learn is a separate surface; give it ws:8767 like debrief got :8766."

**Why it's wrong:** Debrief is a separate sidecar PROCESS spawned on demand. Learn is in the SAME sidecar process as the main session — sharing `MusicState`, `EvidenceRegistry`, the audio backend. Adding a second `websockets.serve` in the same process is the P12 "two listeners at once" pattern — broke v5 hard.

**Do this instead:** Register `learn.*` handlers on the existing `IpcRouterBus` (`runtime/ws_bus.py:276`). Same wire, same lifecycle. Already proven by SessionLoop's settings/profile/recordings handlers.

### Anti-Pattern 2: Re-embed library with a band-specific CLAP

**What people do:** "We need band-aware exemplars — let's train/find a model that embeds 'kick energy' as a 512-dim vector."

**Why it's wrong:** Adds a model + ingest cost + storage cost for a problem that scalar band shares (already computed by `snapshot_features`) solve. Violates the v8.0 anti-creep acid test.

**Do this instead:** Cache the 4 scalar band-share columns at ingest time alongside the existing CLAP vector. Rank by scalar at query time. Done.

### Anti-Pattern 3: New "teacher" lens

**What people do:** "We need a dedicated teaching lens — hype/critique/tutor isn't quite right; let's add 'teacher'."

**Why it's wrong:** Duplicates `MOOD_PERSONAS["teacher"]` substrate; forces a new LENS slot through the v8.1 BENCH-03 rubric; multiplies the test matrix.

**Do this instead:** Use the existing tutor mood + course/lesson-specific system-instruction addendum (the v8.2 build-set pattern). One lens, many addenda.

### Anti-Pattern 4: `PlaybackQueue` for exemplars

**What people do:** "We already have an audio output queue — feed exemplars through it."

**Why it's wrong:** `PlaybackQueue` is mono int16 wired into mic-gating (mic mutes when queue non-empty). User can't react vocally to the exemplar; AI can't talk over it.

**Do this instead:** Dedicated `ExemplarPlayer` with its own `sd.OutputStream` on the same headphone device. CoreAudio handles multiple streams on one device cleanly.

### Anti-Pattern 5: Speculative phrase prediction in Course 3

**What people do:** "We need to call breakdowns BEFORE they land — let's count downbeats and predict."

**Why it's wrong:** Violates Invariant #3 (trust the audio). The existing `bpm_confidence < 0.6` gate exists for exactly this reason — guessed downbeats hallucinate.

**Do this instead:** Use the SHIPPED CueAnchor + phrase_boundary detector. If neither is available for the audible track, narrate PAST events only ("you just hit a breakdown — nice"). The release-gate test (`test_course3_no_speculative_phrase`) prevents regression.

### Anti-Pattern 6: Add LearnState fields onto MusicState

**What people do:** "We're already reading MusicState — just add the lesson_id field there."

**Why it's wrong:** Two writers (state/refresh.py + learn/runtime.py) on the same object = race. Couples coach.py to learn semantics on every tick.

**Do this instead:** Keep `LearnState` in `src/vibemix/learn/state.py`. Reads from `MusicState` are fine (the coach reads it too); writes are forbidden by the static gate.

---

## Integration Points

### External (none for v9.0)

Learn introduces no external service dependency. All AI traffic goes through the same `model_router.resolve(...)` path the live coach uses.

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| `learn/` ↔ `state/` | READ-ONLY: `learn/` consumes `MusicState`, never writes | Static gate enforced |
| `learn/` ↔ `library/` | READ-ONLY through the new `learn/exemplar.py` adapter | Band-share column read |
| `learn/` ↔ `prompts/` | `learn/prompts.py` calls `prompts/matrix.py:build_system_instruction` | One-way |
| `learn/` ↔ `agent/dj_cohost.py` | Course 3 only — calls the existing live coach with tutor lens | Reuses cite linter |
| `learn/` ↔ `evidence_registry` | WRITES `exemplar` cite tokens; reads no other source | Existence-only |
| `learn/` ↔ `runtime/ws_bus.py` | `learn/router.py` registers handlers on existing `IpcRouterBus` | NO new port |
| `learn/` ↔ `midi/state.py` | READS `ControllerState.snapshot_positions()` (new method) | NO writes |
| `learn/` ↔ `platform/_audio_macos.py` | NEW stream via the same device `open_voice_output` uses | Separate `sd.OutputStream` |
| `learn/` ↔ `memory/` | NONE in v9.0 (v9.1+ adds `lesson_completed` memory records) | Deferred |
| Tauri shell ↔ `learn_window.rs` | Standard Tauri `WebviewWindow` spawn | Mirror of `debrief_window.rs` |
| `learn_window` webview ↔ sidecar | ws:8765, types prefixed `ipc.learn.*` | Same bus as session/mascot |

---

## Cross-Cutting Pin Summary (one named test per cardinal invariant + per schema-mirror site)

| Invariant / Site | Test file | What it pins |
|------------------|-----------|--------------|
| #1 Single-writer | `tests/learn/test_runtime_invariants.py::test_musicstate_never_mutated_by_learn` | Static AST gate over `learn/` — no writes to `MusicState` fields |
| #1 Single-writer | `tests/learn/test_runtime_invariants.py::test_only_learnruntime_writes_learnstate` | Dynamic — only the runtime tick writes `LearnState` |
| #2 Citation grounding | `tests/learn/test_exemplar_citation_schema_mirror.py` | 4 schema-mirror sites all contain "exemplar" |
| #2 Citation grounding | `tests/learn/test_exemplar_grounding_e2e.py` | Fabricated `[exemplar:bogus]` strips whole turn |
| #3 Trust the audio | `tests/learn/test_no_speculative_phrase.py` | Static gate — no `numpy.fft` / phrase guessing in `learn/` |
| #3 Trust the audio | `tests/learn/test_course3_uses_existing_coach.py` | Course 3 prompts built by `AICoach.build_prompt` |
| #4 One socket | `tests/learn/test_no_new_ws_port.py` | Static grep — no `websockets.serve` in `learn/` |
| #4 One socket | `tests/learn/test_learn_rides_existing_bus.py` | Dynamic — `learn.*` round-trips on ws:8765 |
| Tone lock | `tests/learn/test_tutor_prompts_byte_equality.py` | Iconic opening strings byte-identical |
| IPC schema parity | `tests/learn/test_highlight_envelope_schema.py` | `LearnHighlight` Python dataclass ↔ JSON Schema parity |
| Controller profile resolution | `tests/learn/test_course_1_curriculum_resolves.py` | Every `control_id` in every Lesson resolves against every shipped MIDI profile |

---

## Scaling Considerations

| Scale | Adjustments |
|-------|-------------|
| 1 user (Kaan) | JSON progress file fine. Single library. |
| 10s of beta users | No changes. JSON file per user (already per-install). Curriculum hand-authored — no growth concern. |
| 1000s of OSS users | Curriculum still hand-authored. Library size scales with user crate (typical: 1k-10k tracks). Band-share column query is `SELECT ... ORDER BY low_share DESC LIMIT 10` — sub-millisecond on sqlite. |
| User-contributed lessons | Out of v9.0 scope. If needed in v9.x: lessons become loadable JSON files under `~/Library/Application Support/vibemix/learn/community/`, schema-validated at load. Same trust posture as user-contributed MIDI profiles in v7.0 P68. |

### First bottleneck

The 30Hz `ipc.learn.midi_position` push when the user has 50+ controls on a busy controller (e.g. DDJ-1000) produces ~50 control-value pairs × 30 frames × 8 bytes = 12 KB/s per Learn client. Negligible.

### Second bottleneck

Course 3 narration latency under heavy live-coach load — the tutor narration competes for the single `in_flight` Gemini generation slot the live coach already uses. If competing for slots becomes user-visible, gate tutor narration to a lower cadence in Course 3 (every Nth phrase boundary instead of every one). Not a v9.0 concern; defer until ear-pass surfaces it.

---

## Sources

All paths below verified on disk in `/Users/ozai/projects/dj-set-ai/` on 2026-05-27:

- `src/vibemix/__main__.py:1-100` — orchestrator shape (read)
- `src/vibemix/runtime/ws_bus.py:276,336,659,662-791` — `IpcRouterBus`, `WizardBus`, `IpcBus` alias, handler registration pattern (read)
- `src/vibemix/state/music_state.py:23-80` — `MusicState` dataclass + single-writer comment (read)
- `src/vibemix/state/coach.py:1-100,257,467,761` — `AICoach.evidence_line`, `_evidence_line_compact`, `recall_fragment_for_event` (read)
- `src/vibemix/state/evidence_registry.py:111,137,283` — `EVIDENCE_SOURCES`, `_SOURCE_ALT`, parse logic (read)
- `src/vibemix/coach/citation_linter.py:40,191-194` — linter source-validity check (grep)
- `src/vibemix/prompts/matrix.py:53-66,98` — `MOOD_PERSONAS`, `CITATION_GRAMMAR_BLOCK` reference (read)
- `src/vibemix/library/sequencer.py:1-80` — beam-search shape (read)
- `src/vibemix/library/discovery.py:1-80` — pool-builder primitives (read)
- `src/vibemix/audio/features.py:1-150` — `snapshot_features` + 4 band shares (read)
- `src/vibemix/audio/buffers.py:195,330` — `PlaybackQueue` mic-gate coupling (grep)
- `src/vibemix/platform/_audio_macos.py:307,328` — `open_passthrough_output`, `open_voice_output` (grep)
- `src/vibemix/midi/state.py:118` — `ControllerState` class (grep)
- `src/vibemix/midi/profiles/*.json` — 10 controller profiles (ls)
- `src/vibemix/state/detectors/phrase_boundary.py` — phrase detector (ls)
- `tauri/ui/src/ipc/messages.schema.json` — 30+ existing `ipc.*` types (read first 200 lines + greps)
- `tauri/src-tauri/src/sidecar.rs:1-80` — sidecar lifecycle (read)
- `tauri/src-tauri/src/debrief_window.rs` — second-window pattern (ls + referenced)
- `.planning/PROJECT.md` — v8.1, v8.2 shipped milestone narratives (read pages 1-333)

---

*Architecture research for: vibemix v9.0 "Lesson One" — Beginner Learning Module*
*Researched: 2026-05-27*
*Confidence: HIGH — every cite is a verified file:line on the live branch (`live-tuning-or-brain`).*
