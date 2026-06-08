<!-- refreshed: 2026-06-08 -->
# Architecture

**Analysis Date:** 2026-06-08

## System Overview

vibemix is a single packaged Python app (`src/vibemix/`) driven by an async
orchestrator, wrapped in a Tauri desktop shell (`tauri/`) that spawns the Python
process as a **sidecar** and talks to it over ONE WebSocket bus on
`127.0.0.1:8765` (debrief uses `8766`). The Python side listens to the master
audio output, watches the DJ app's screen, reads MIDI, derives musical state,
and speaks back as Sven (the live co-host).

```text
┌──────────────────────────────────────────────────────────────────────┐
│  Tauri desktop shell  `tauri/src-tauri/` (Rust parent process)         │
│  main window + mascot + pill + debrief + learn windows                 │
│  TS webview UI  `tauri/ui/src/`  (shell · session · library · mascot)  │
└───────────────────────────────┬──────────────────────────────────────┘
                                │  ws bus  127.0.0.1:8765  (debrief 8766)
                                │  contract: `tauri/ui/src/ipc/messages.schema.json`
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│  Python sidecar — async orchestrator                                   │
│  `src/vibemix/__main__.py::main()`  (asyncio.run)                      │
├──────────────┬───────────────┬───────────────┬───────────────────────┤
│  audio/      │  platform/    │  state/ (brain)│  agent/ (Sven)        │
│  ring buffers│  per-OS       │  MusicState +  │  LiveKit RealtimeModel│
│  `buffers.py`│  backends     │  refresh loop  │  `dj_cohost.py`       │
└──────┬───────┴───────┬───────┴───────┬────────┴──────────┬────────────┘
       │ OS audio       │ daemon thread │ asyncio loops     │ asyncio
       │ callback       │ (MIDI, mido)  │ (state/coach/ws)  │
       ▼                ▼               ▼                   ▼
┌──────────────────────────────────────────────────────────────────────┐
│  Cross-thread state via threading.Lock in buffer classes               │
│  audio capture → lock-protected buffers → state_refresh_loop (10Hz,    │
│  SOLE writer of MusicState) → EventDetector → AICoach.build_prompt →    │
│  Gemini reaction → CitationLinter gate → local MOSS TTS → ws bus → UI   │
└──────────────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| Async orchestrator | Boot, activate/stop live session, wire all loops, spawn ws bus | `src/vibemix/__main__.py` (`main()`, `_activate_session`) |
| Audio ring buffers | Lock-protected PCM buffers across the audio-thread / event-loop boundary | `src/vibemix/audio/buffers.py` |
| Platform firewall | Typing-only Protocols; per-OS audio/screen/MIDI/track backends | `src/vibemix/platform/audio.py` (+ `_audio_macos.py`, `_audio_windows.py`) |
| MusicState (single source of truth) | The read-only evidence snapshot every consumer grounds against | `src/vibemix/state/music_state.py` |
| State refresh loop (SOLE writer) | 10Hz writer of MusicState from DSP features | `src/vibemix/state/refresh.py` (`state_refresh_loop`, `_tick_once`) |
| Event detector | Emits typed events with per-type cooldowns | `src/vibemix/state/event_detector.py` (`EventDetector.detect`) |
| Coach (prompt builder) | Builds evidence-grounded prompts per event type | `src/vibemix/state/prompt_builder.py` (`AICoach.build_prompt`) |
| Coach loop | Drives detect→prompt→agent each tick | `src/vibemix/runtime/coach.py` (`coach_loop`) |
| Evidence registry | Backs citation grounding (`EVIDENCE_SOURCES`) | `src/vibemix/state/evidence_registry.py` |
| Citation linter | Response-level binary anti-slop gate | `src/vibemix/coach/citation_linter.py`, called in `agent/dj_cohost.py::llm_node` |
| Sven agent | LiveKit `RealtimeModel` session + Gemini reaction path | `src/vibemix/agent/dj_cohost.py` (`DJCoHostAgent`) |
| Model router | Config-driven model resolution (no hardcoded literals) | `src/vibemix/llm/model_router.py` (`resolve`) |
| ws bus | Single `websockets.serve` on 8765; snapshot + handler routing | `src/vibemix/runtime/ws_bus.py` (`ws_broadcast`, `IpcRouterBus`) |
| Suggestion pill | "What's next" engine + SuggestionService | `src/vibemix/runtime/suggestion.py`, `src/vibemix/library/next_suggestion.py` |

## Pattern Overview

**Overall:** Single-writer reactive pipeline behind a platform-backend firewall,
fronted by a sidecar+webview desktop shell.

**Key Characteristics:**
- **Single-writer state** — only `state_refresh_loop` mutates `MusicState`;
  every other component (event detector, coach, agent, learn, ws bus) reads.
- **Platform firewall** — `__main__.py` is OS-agnostic; all OS-specific imports
  live behind Protocols in `platform/` (enforced by `tests/test_platform.py`).
- **Grounding-first** — nothing un-cited reaches the user's ears; the
  `CitationLinter` strips an entire turn to silence if any atom is unbacked.
- **Three execution domains** — OS audio threads (sounddevice callbacks), a MIDI
  daemon thread (blocking mido), and the asyncio event loop, bridged only by
  `threading.Lock`-protected buffers (no async queues across the boundary).

## Layers

**Capture (OS threads):**
- Purpose: pull master audio, screen frames, MIDI, now-playing metadata.
- Location: `src/vibemix/platform/`, `src/vibemix/audio/`.
- Contains: sounddevice callbacks, Quartz/ScreenCaptureKit crop, mido listener.
- Depends on: OS APIs (CoreAudio/WASAPI, Quartz, rtmidi).
- Used by: writes into lock-protected buffers consumed by the state loop.

**State / brain (asyncio):**
- Purpose: turn raw features into grounded musical evidence + typed events.
- Location: `src/vibemix/state/`.
- Contains: `MusicState`, refresh loop, event detector, evidence registry,
  deck-aware state, harmonics, detectors, genre routing.
- Depends on: buffers (read), `audio/` DSP helpers.
- Used by: coach loop, agent, learn, ws bus.

**Reaction (asyncio):**
- Purpose: build a grounded prompt, call Gemini, gate it, render speech.
- Location: `src/vibemix/state/prompt_builder.py`, `src/vibemix/runtime/coach.py`,
  `src/vibemix/agent/`, `src/vibemix/llm/`, `src/vibemix/coach/`, `src/vibemix/prompts/`.
- Depends on: MusicState (read), EvidenceRegistry, model_router, local MOSS TTS.
- Used by: ws bus (broadcasts `transcript_delta`).

**Transport / UI (asyncio + Rust + webview):**
- Purpose: one ws bus to the shell; render mascot, pill, session deck, library.
- Location: `src/vibemix/runtime/ws_bus.py`, `src/vibemix/ui_bus/`, `tauri/`.
- Depends on: everything above (read-only snapshots).

## Data Flow

### Primary Reaction Path (the live co-host)

1. OS audio thread pushes master PCM into a ring buffer (`src/vibemix/audio/buffers.py::AudioBuffer.push`).
2. `state_refresh_loop` reads buffers, computes DSP features, and **writes**
   `MusicState` (the only writer) at ~10Hz (`src/vibemix/state/refresh.py::_tick_once`).
3. `coach_loop` asks the detector for an event (`src/vibemix/state/event_detector.py::EventDetector.detect`) — typed (`TRACK_CHANGE`, `PHASE`, `LAYER_ARRIVAL`, `MIX_MOVE`, `HEARTBEAT`, …) with per-type cooldowns.
4. `AICoach.build_prompt` composes an evidence-grounded prompt for that event type (`src/vibemix/state/prompt_builder.py:1125`).
5. `DJCoHostAgent.llm_node` runs the Gemini generation, then the silence/slop gate, then `CitationLinter.check(...)` (`src/vibemix/agent/dj_cohost.py:2733`).
6. Any unbacked citation → the whole turn is stripped to silence (`_build_citation_strip`, `dj_cohost.py:1232`, `citation_strip` event logged, no audio).
7. Surviving text → local MOSS TTS (`src/vibemix/agent/tts_chain.py`) → playback sink.
8. Reaction text broadcasts to the UI over the ws bus as `transcript_delta` (`src/vibemix/runtime/ws_bus.py`), NOT stderr.

### Suggestion (pill) Flow

1. `SuggestionService` reads MusicState + library to compute "what's next" (`src/vibemix/runtime/suggestion.py::SuggestionService`).
2. Mean-centered candidate scoring against the CLAP store (`src/vibemix/library/next_suggestion.py`).
3. Emitted over the ws bus → rendered by the pill window (`tauri/ui/src/pill/`).

### Session Lifecycle

1. `main()` boots housekeeping and the ws bus first (`src/vibemix/__main__.py:1467`).
2. `_start_live_session` creates a per-run `stop_event` and `_activate_session` task (`__main__.py:2845`).
3. `_activate_session` spawns capture, screen, track-poll, deck-poll, `state_refresh_loop`, and `coach_loop` tasks bound to `run_stop_event` (`__main__.py:2180`).
4. `_stop_live_session` sets the run stop event; every loop cooperatively exits.

**State Management:**
- `MusicState` is the single source of truth, written only by the refresh loop.
- `LearnState` is the learn-package counterpart, sole writer `learn/runtime.py`.
- Controller/MIDI state is written only by the MIDI listener thread.
- Cross-thread sharing is via `threading.Lock` inside buffer classes — never
  async queues across the audio/event-loop boundary.

## Key Abstractions

**MusicState:**
- Purpose: the read-only evidence snapshot the co-host is allowed to talk about.
- Examples: `src/vibemix/state/music_state.py`.
- Pattern: single-writer; consumers read fields, never assign them.

**EvidenceRegistry / EVIDENCE_SOURCES:**
- Purpose: the set of citation source kinds a reaction may cite; backs grounding.
- Examples: `src/vibemix/state/evidence_registry.py` (frozenset `EVIDENCE_SOURCES`).
- Pattern: a citation grammar that the `CitationLinter` resolves against; the
  registry regex alternation must be edited in lock-step with `EVIDENCE_SOURCES`.

**Platform Protocols:**
- Purpose: keep `__main__` OS-agnostic; `audio.py`/`midi.py`/`screen.py`/`track.py`
  declare `Protocol`s, `_*_macos.py`/`_*_windows.py` implement them.
- Examples: `src/vibemix/platform/audio.py`, `_audio_macos.py`, `_audio_windows.py`.
- Pattern: runtime backend selection; the typing module imports zero OS modules.

**Model router:**
- Purpose: config-driven model resolution; zero hardcoded model literals (CI grep-gated).
- Examples: `src/vibemix/llm/model_router.py::resolve`.
- Pattern: always `model_router.resolve("<path>")`, never inline a model name.

## Entry Points

**Python sidecar:**
- Location: `src/vibemix/__main__.py::main()` (run via `python -m vibemix`).
- Triggers: spawned by the Tauri Rust parent (`tauri/src-tauri/src/sidecar.rs`).
- Responsibilities: async orchestration of all capture/state/reaction/ws loops.

**Tauri shell:**
- Location: `tauri/src-tauri/src/main.rs` (Rust parent), `tauri/ui/src/main.ts` (webview).
- Triggers: app launch; binds windows (main, mascot, pill, debrief, learn).
- Responsibilities: spawn + supervise the sidecar, bridge ws, render UI.

**Library CLI:**
- Location: `python -m vibemix library <cmd>` routed through `src/vibemix/__main__.py`.
- Triggers: developer/operator commands (ingest, search, curate, build-set).

## Architectural Constraints

- **Threading:** asyncio main loop (`asyncio.run(main())`); sounddevice audio
  callbacks run on OS audio threads (synchronous); the MIDI listener runs on a
  daemon thread (mido is blocking). Blocking work is offloaded via
  `loop.run_in_executor`. Cross-thread state crosses only through
  `threading.Lock`-guarded buffers (`audio/buffers.py`).
- **Single in-flight generation:** exactly one Gemini generation at a time,
  guarded by an `in_flight` flag with a stale-age force-clear; a loop failure
  never wedges the gate (errors caught per-loop, logged to stderr + `events.jsonl`).
- **Single socket:** the mascot/wizard bus binds `127.0.0.1:8765` only; debrief
  uses `8766`. Constants in `src/vibemix/audio/constants.py` (`WS_HOST`, `WS_PORT`).
- **Global state:** the only module-level singletons are feature flags
  (`_HAS_*`); all real state objects are allocated in `main()` and passed
  explicitly (DI over globals).
- **`intel/` is import-light:** no model clients, no audio capture, no Tauri,
  no filesystem writes — pure musical-intelligence primitives.

## Cardinal Invariants (TEST-ENFORCED — do not break)

These five are the test-enforced spine of the "real DJ friend, no AI slop"
promise. The `vibemix-grounding-review` skill runs them before any
speech/timing change. A green feature test is NOT enough — these are
cross-cutting.

### Invariant #1 — Single-writer MusicState
Only `state/refresh.py::state_refresh_loop` writes `MusicState`; everything else
reads. `LearnState` writes are confined to `learn/runtime.py`/`learn/state.py`;
the MIDI listener is the sole writer of controller state. A second writer races
the source of truth and makes grounding non-deterministic.
**Gate:** `tests/learn/test_runtime_invariants.py` (static grep reddens on any
`MusicState.<field> =` under `learn/`), `tests/state/test_refresh.py`,
`tests/state/test_music_state.py`.

### Invariant #2 — Citation grounding (THE anti-slop release gate)
Every citation a reaction emits must resolve in `EvidenceRegistry`. An un-cited
or unbacked reaction is stripped to silence — `<silence/>` beats an invented
citation. The chokepoint is `DJCoHostAgent.llm_node` running
`CitationLinter.check(full_text, snapshot, mode="live")`; decision is
**response-level binary** (one bad atom strips the whole turn, logs
`citation_strip`, no audio). This is the single hard release gate.
**Gate:** `tests/state/test_coach_anti_slop.py`, `tests/agent/test_citation_strip_emit.py`.

### Invariant #3 — Trust the audio / no speculative phrasing
Live audio evidence is authoritative; the co-host reacts to real detected
events, never invents them. Two layers: a static AST gate keeps `learn/` from
computing its own phrase structure (no `numpy.fft`/`scipy.signal`/`librosa.beat`/
`librosa.onset` imports), and the post-hoc slop filter
(`prompts/filter.py::filter_for_slop` vs `prompts/negative_dict.py`,
≥40 phrases) nukes banned generic-AI phrasing → `<silence/>` + `slop_suppressed`.
**Gate:** `tests/learn/test_no_speculative_phrase.py`, `tests/prompts/test_negative_dict.py`,
`tests/state/test_hype_anti_slop.py`.

### Invariant #4 — One socket
The mascot/wizard bus binds `127.0.0.1:8765` only (never two listeners); debrief
uses `8766`. No new `websockets.serve` that races the one bus; import `WS_PORT`,
never hardcode. Two listeners on 8765 is the "VIBEMIX-CORE STOPPED" / empty-screen
class of bug.
**Gate:** `tests/learn/test_no_new_ws_port.py`, `tests/runtime/test_ws_bus.py`.

### Invariant #5 — Idle ≠ fault
`SessionLayout`'s grounding-failure timer runs ONLY while the co-host is ACTIVE.
At idle, `grounded=false` is expected (no music to ground to) and must read as
calm "silent", never flip the deck to a fake "AI SERVICE OFFLINE" fault with a
blank hero. `GROUNDING_FAILURE_MS` = 5000; `screen=denied` is badge-only.
**Gate (the one TypeScript invariant):** `tauri/ui/tests/session/grounding-failure.spec.ts`.

> **Prompt composition contract:** `docs/PROMPT-COMPOSITION.md` is the single
> named source for what enters the live prompt per event type (EventType ×
> evidence-fields × citation-sources × recall-fragment × diet-mode × cooldown).

## Anti-Patterns

### Writing MusicState from a consumer
**What happens:** A coach/agent/learn/new-detector path assigns a `MusicState`
field directly to "fix" a value.
**Why it's wrong:** It races the single writer (Invariant #1); the evidence the
linter grounds against can flip mid-turn, so the co-host reacts to a state that
never coherently existed.
**Do this instead:** Compute it inside `state/refresh.py::_tick_once`; consumers
read only. Local per-loop scratch state stays in the loop's local scope.

### Speculative / predictive phrasing
**What happens:** A prompt or learn module predicts structure ("the drop is
coming", "breakdown in 16 beats") or a learn module imports an FFT/beat-tracking
primitive to compute it.
**Why it's wrong:** Speculation is hallucination with better grammar; it
violates Invariant #3 and is exactly the slop Kaan blocks release on.
**Do this instead:** Cite only observed events from `state/refresh.py` +
`CueAnchor`; let the detector fire on real audio.

### Hardcoding a model name or a ws port
**What happens:** Inlining `"gemini-..."` in code, or `websockets.serve(..., 8765)`
on a new surface.
**Why it's wrong:** Breaks the model-router CI grep gate / Invariant #4; a second
listener on 8765 silently eats reactions.
**Do this instead:** `model_router.resolve("<path>")`; piggy-back the existing
`ws_broadcast` producer and import `WS_PORT` from `audio/constants.py`.

### Shipping a one-ended IPC type
**What happens:** A new `ipc.*` type is declared in `messages.schema.json` and
wired on only one end (sender or handler).
**Why it's wrong:** It ships green (schema parity holds, `tsc` passes) but does
nothing live — the "button does nothing / panel stays blank" bug.
**Do this instead:** Wire BOTH ends and run the `ipc-wiring-checker` skill
(`.claude/skills/ipc-wiring-checker/scripts/check_ipc_wiring.py`).

## Error Handling

**Strategy:** Per-loop try/except; a loop failure is logged but never wedges the
single in-flight Gemini gate or the whole orchestrator.

**Patterns:**
- Errors bracket-tagged to stderr (e.g. `[coach err]`) and written as structured
  per-session events to `events.jsonl`.
- AI reactions go to the UI over the ws bus (`transcript_delta`), not stderr.
- Capture/permission failures should surface as `ipc.error` to the shell, not
  stderr-only (stderr-only failures look identical to "still warming" → the
  recurring go-live flail).

## Cross-Cutting Concerns

**Logging:** startup lines `-> ...`; errors bracket-tagged to stderr; structured
session events to `events.jsonl`; reactions over the ws bus.
**Validation:** IPC frames validated against `tauri/ui/src/ipc/messages.schema.json`
via a PRE-COMPILED ajv validator (`validator.generated.mjs`); Python side mirrors
in `src/vibemix/ui_bus/` (`messages.py`, `validator.py`, `schemas/`).
**Grounding:** the `CitationLinter` + `EvidenceRegistry` are the cross-cutting
anti-slop spine; every speech surface (co-host, pill, learn tutor, debrief) must
pass through it.

## Tauri / TypeScript Frontend Architecture

The shell is a TS webview (`tauri/ui/src/`) over a Rust parent
(`tauri/src-tauri/src/`). The Rust side is mostly a generic
`forward_ipc_to_sidecar` passthrough plus per-window commands.

**Window topology** (each a Rust module + a TS surface):
- Main shell — `tauri/src-tauri/src/main.rs` + `tauri/ui/src/shell/` (`DesktopShell.ts`, `Sidebar.ts`, `app.ts`, `surfaces.ts`).
- Session deck — `tauri/ui/src/session/` (`SessionLayout.ts`, `render-loop.ts`, `ws-bridge.ts`, `cohost-model.ts`).
- Mascot organism — `tauri/src-tauri/src/mascot_window.rs` + `tauri/ui/src/mascot/` (particle organism, layers, ws-client) and root `mascot.html`.
- Pill — `tauri/src-tauri/src/pill_window.rs` + `tauri/ui/src/pill/` (`index.ts`, `next-suggestion.ts`, `state-machine.ts`).
- Debrief — `tauri/src-tauri/src/debrief_window.rs` + `tauri/ui/src/debrief/` (ws on 8766).
- Learn — `tauri/src-tauri/src/learn_window.rs` + `tauri/ui/src/learn/` (`SkillWall.ts`, controllers SVGs).
- Library / Viber — `tauri/ui/src/library/` (`index.ts`, `api.ts`, `state-machine.ts`).
- Wizard / onboarding — `tauri/ui/src/wizard/` (step-driven router).
- Settings drawer — `tauri/ui/src/settings/` (`SettingsDrawer.ts`, `state.ts`).

**IPC contract (the single source of truth for the wire):**
- Types declared once in `tauri/ui/src/ipc/messages.schema.json` (88 `const`
  types). A type is a real feature only when BOTH ends touch it.
- TS client: `tauri/ui/src/ipc/client.ts` (`emitIpc` / `sendIpcRequest` /
  `subscribeIpc`), validated by `tauri/ui/src/ipc/validator.generated.mjs`
  (PRE-COMPILED — run `npm run codegen:ipc` after editing the schema or new
  fields are rejected).
- Python side: `register_handler("ipc.x.y", ...)` in `src/vibemix/runtime/ws_bus.py`
  and outbound factory constants in `src/vibemix/ui_bus/messages.py` +
  `ui_bus/learn_messages.py`.
- Rust passthrough: `tauri/src-tauri/src/ws_client.rs` (`forward_ipc_to_sidecar`).
- Wiring gate: `.claude/skills/ipc-wiring-checker/scripts/check_ipc_wiring.py`.

**Frontend convention (load-bearing):** settings controls must repaint
OPTIMISTICALLY — flip `data-active` locally in the click handler (the ~3ms
round-trip stays authoritative and self-corrects); waiting on the
`ipc.settings.state` echo looks dead.

---

*Architecture analysis: 2026-06-08*
