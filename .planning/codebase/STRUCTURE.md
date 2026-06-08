# Codebase Structure

**Analysis Date:** 2026-06-08

## Directory Layout

```text
dj-set-ai/
├── src/vibemix/            # The packaged Python app (entry: python -m vibemix)
│   ├── __main__.py         # Async orchestrator — main() (the entry point, ~360KB)
│   ├── _main_helpers.py    # main() helpers
│   ├── voice_presets.py    # voice preset table
│   ├── audio/              # capture/playback ring buffers, DSP, levels, cues, ws constants
│   ├── platform/           # per-OS backends (the firewall keeping __main__ OS-agnostic)
│   ├── state/              # THE BRAIN — MusicState + refresh loop + events + grounding
│   │   ├── detectors/      # micro event detectors (kick swap, breakdown, phrase boundary…)
│   │   └── genre/          # genre autodetect + per-genre profiles
│   ├── agent/              # Sven: LiveKit RealtimeModel + Gemini reaction + local MOSS TTS
│   │   └── moss_tts/       # local MOSS-TTS model cache mount (no .py — runtime assets)
│   ├── llm/                # model_router (config-driven, no hardcoded literals) + thinking_gate
│   ├── library/            # CLAP ONNX embeddings + sqlite-vec vibe search + Viber curator
│   │   └── sources/        # crate importers (rekordbox, serato, traktor, virtualdj)
│   ├── intel/              # pure musical-intelligence primitives (import-light, no I/O)
│   ├── learn/              # the teaching engine (skill tree, lessons, practice loops)
│   │   ├── assets/         # band exemplars (sub/low/mid/high)
│   │   ├── transcripts/    # course/lesson transcripts
│   │   └── vocals/         # tutor vocal assets
│   ├── runtime/            # ws_bus, suggestion pill, session_loop, wizard, soak, ttft
│   ├── coach/              # citation_linter + prompt_fragments (anti-slop)
│   ├── prompts/            # slop filter, negative_dict, matrix, scorecard, turn_history
│   ├── profile/            # long-term DJ profile (schema/storage/builder)
│   ├── memory/             # local memory.db copilot store (sqlite-vec), gated off by default
│   ├── debrief/            # post-session review engine (second window, port 8766)
│   ├── events/             # event taxonomy
│   │   └── genres/         # per-genre event tuning (house/techno/psytrance/…)
│   ├── midi/               # MIDI decode + 10-controller profiles/ catalog
│   │   └── profiles/       # controller MIDI maps
│   ├── install/            # blackhole_probe + install helpers
│   ├── ui_bus/             # Python side of the IPC contract (messages, validator, schemas/)
│   ├── bench/              # Sven prompt bench (dev/eval harness, NOT a runtime feature)
│   └── eval/               # session_report eval helper
├── tauri/                  # desktop shell
│   ├── ui/                 # TS webview frontend (Vite + TS)
│   │   └── src/            # shell / session / library / mascot / learn / pill / ipc / …
│   └── src-tauri/          # Rust parent process (sidecar supervisor + windows)
│       ├── src/            # main.rs, sidecar.rs, ws_client.rs, *_window.rs, *_cmds.rs
│       └── binaries/       # PyInstaller-frozen sidecar bundle (BUILD ARTIFACT — not source)
├── tests/                  # pytest suite (mirrors src/vibemix/ subpackages)
├── tauri/ui/tests/         # vitest specs for the TS frontend
├── docs/                   # design, install, prompts, security, library, ship runbooks
├── mocks/                  # HTML visual contracts (the design source of truth for UI)
├── .planning/              # GSD planning home (ROADMAP, REQUIREMENTS, codebase maps, packets)
├── packaging/ installer/   # packaging + installer scaffolds
├── proxy/ native/ spikes/  # Bravoh-side keyless proxy, native spikes, parked experiments
├── pyproject.toml          # hatchling project + dependency pins
├── uv.lock                 # uv lockfile (authoritative)
├── vibemix-core.macos.spec # PyInstaller spec (macOS) — auto-bundles vibemix.* submodules
├── vibemix-core.windows.spec # PyInstaller spec (Windows)
├── mascot.html             # live Canvas-2D overlay wired to runtime.ws_bus (NOT a POC)
└── CLAUDE.md               # project ground truth (architecture + invariants)
```

## Directory Purposes

**`src/vibemix/state/` — the brain:**
- Purpose: single source of truth + grounding.
- Contains: `music_state.py` (`MusicState`), `refresh.py` (sole writer,
  `state_refresh_loop`), `event_detector.py` (typed events + cooldowns),
  `evidence_registry.py` (`EVIDENCE_SOURCES`), `prompt_builder.py` (`AICoach`),
  deck-aware state (`deck_state.py`, `deck_context.py`, `deck_poller.py`,
  `deck_vision.py`), `harmonics.py` (Camelot), `phase.py`, `genre_router.py`,
  plus `detectors/` and `genre/`.
- Key files: `src/vibemix/state/refresh.py`, `src/vibemix/state/music_state.py`,
  `src/vibemix/state/event_detector.py`, `src/vibemix/state/evidence_registry.py`.

**`src/vibemix/platform/` — the OS firewall:**
- Purpose: keep `__main__` OS-agnostic; all OS imports live here.
- Contains: typing-only Protocol modules (`audio.py`, `midi.py`, `screen.py`,
  `track.py`, `permissions.py`, `windows.py`) + `_*_macos.py` / `_*_windows.py`
  implementations + `_audio_replay.py` (recorded-session replay backend).
- Key files: `src/vibemix/platform/audio.py` (Protocol), `_audio_macos.py`, `_audio_windows.py`.

**`src/vibemix/agent/` — Sven:**
- Purpose: live co-host LiveKit session + Gemini reaction + local speech.
- Key files: `dj_cohost.py` (`DJCoHostAgent`, `llm_node`), `tts_chain.py`,
  `chatterbox_tts.py`, `playback_sink.py`, `proxy_client.py`, `persona.py`.

**`src/vibemix/library/` — CLAP + Viber:**
- Purpose: on-device CLAP ONNX embeddings, sqlite-vec vibe search, Viber curator.
- Key files: `clap_engine.py`, `index_sqlite_vec.py`/`index_numpy.py`,
  `next_suggestion.py` (pill engine), `toolset.py`/`codex_curate.py`/
  `mcp_server.py`/`telegram_bridge.py` (Viber), `cue_detr.py`/`cue_engine.py`.

**`src/vibemix/runtime/` — transport + loops:**
- Purpose: the ws bus, suggestion pill, session lifecycle, dev harnesses.
- Key files: `ws_bus.py` (single 8765 serve, `ws_broadcast`, `IpcRouterBus`),
  `coach.py` (`coach_loop`), `suggestion.py` (`SuggestionService`),
  `session_loop.py`, `wizard.py`, `speak_gate.py`.

**`tauri/ui/src/` — TS webview:**
- Purpose: the visible app shell.
- Contains: `shell/`, `session/`, `library/`, `mascot/`, `learn/`, `pill/`,
  `debrief/`, `wizard/`, `settings/`, `overlay/`, `runtime/`, and the `ipc/`
  contract.
- Key files: `tauri/ui/src/main.ts`, `tauri/ui/src/shell/DesktopShell.ts`,
  `tauri/ui/src/session/SessionLayout.ts`, `tauri/ui/src/ipc/client.ts`.

**`tauri/src-tauri/src/` — Rust parent:**
- Purpose: spawn/supervise the Python sidecar, own native windows.
- Key files: `main.rs`, `sidecar.rs`, `ws_client.rs` (`forward_ipc_to_sidecar`),
  `mascot_window.rs`, `pill_window.rs`, `debrief_window.rs`, `learn_window.rs`,
  `library_cmds.rs`, `wizard_cmds.rs`.

## Key File Locations

**Entry Points:**
- `src/vibemix/__main__.py`: `main()` async orchestrator (`python -m vibemix`).
- `tauri/src-tauri/src/main.rs`: Rust parent; spawns the sidecar.
- `tauri/ui/src/main.ts`: webview bootstrap.

**Configuration:**
- `pyproject.toml`: hatchling project, dependency pins, pytest markers.
- `uv.lock`: authoritative lockfile.
- `.env` (repo root): `GEMINI_API_KEY` (Sven live brain only). Existence only —
  never read contents.
- `src/vibemix/audio/constants.py`: `WS_HOST`, `WS_PORT` (8765), audio gains.
- `tauri/src-tauri/tauri.conf.json5`: Tauri window/app config.
- `tauri/ui/src/ipc/messages.schema.json`: the IPC contract (88 types).

**Core Logic:**
- `src/vibemix/state/refresh.py`: the single writer of `MusicState`.
- `src/vibemix/state/event_detector.py`: typed event emission + cooldowns.
- `src/vibemix/agent/dj_cohost.py`: Gemini reaction + CitationLinter gate.
- `src/vibemix/runtime/ws_bus.py`: the single 8765 bus.

**Testing:**
- `tests/`: pytest, mirrors subpackages (`tests/state/`, `tests/agent/`,
  `tests/learn/`, `tests/library/`, `tests/runtime/`, …).
- `tauri/ui/tests/`: vitest specs (e.g. `tests/session/grounding-failure.spec.ts`).

## Naming Conventions

**Files (Python):**
- `snake_case.py` modules. Private/OS-specific backends are `_prefixed`
  (`_audio_macos.py`, `_midi_windows.py`). Long-running async tasks are `*_loop`.

**Files (TS):**
- `PascalCase.ts` for component classes/surfaces (`SessionLayout.ts`,
  `DesktopShell.ts`, `Sidebar.ts`); `kebab-case.ts` for modules
  (`ws-client.ts`, `render-loop.ts`, `next-suggestion.ts`); `*.test.ts` /
  `*.spec.ts` for tests.

**Files (Rust):**
- `snake_case.rs`; per-window modules `*_window.rs`; per-area commands `*_cmds.rs`.

**Code:**
- Python: `snake_case` functions/modules, `PascalCase` classes,
  `UPPER_SNAKE_CASE` constants, `_prefixed` privates, `_HAS_*` feature flags.
- IPC types: dotted `ipc.<area>.<verb>` literals in the schema.

**Directories:**
- lowercase single-word subpackages (`state`, `agent`, `library`).

## Where to Add New Code

**New live co-host behavior (speech/events):**
- Event type / cooldown: `src/vibemix/state/event_detector.py`.
- Prompt per event type: `src/vibemix/state/prompt_builder.py` (`AICoach`).
- Tests: `tests/state/`. RUN the `vibemix-grounding-review` skill (Invariants #1–#3).

**New state field:**
- Add the field to `src/vibemix/state/music_state.py`, write it ONLY inside
  `src/vibemix/state/refresh.py::_tick_once` (Invariant #1). Consumers read only.

**New OS-specific capability:**
- Declare the Protocol in the typing module (`src/vibemix/platform/<area>.py`),
  implement in `_<area>_macos.py` and `_<area>_windows.py`. Keep the typing
  module free of OS imports (`tests/test_platform.py` enforces this).

**New IPC-wired control (button/panel):**
- Declare the type in `tauri/ui/src/ipc/messages.schema.json`, run
  `npm run codegen:ipc`. Wire BOTH ends: TS sender via `emitIpc`/`sendIpcRequest`
  (`tauri/ui/src/ipc/client.ts`) AND Python `register_handler` in
  `src/vibemix/runtime/ws_bus.py` (or an outbound constant in
  `src/vibemix/ui_bus/messages.py`). Run the `ipc-wiring-checker` skill.

**New UI surface:**
- TS under the matching `tauri/ui/src/<area>/`; if it needs its own native
  window, add a `*_window.rs` module + register it in `tauri/src-tauri/src/main.rs`.
- Honor the optimistic-repaint convention for settings-style controls.

**New library / Viber capability:**
- `src/vibemix/library/`; crate importers under `library/sources/`.

**New musical-intelligence primitive:**
- `src/vibemix/intel/` — keep it import-light (no model clients, no audio
  capture, no Tauri, no filesystem writes).

**New teaching content/logic:**
- `src/vibemix/learn/`; transcripts under `learn/transcripts/`, exemplar audio
  under `learn/assets/`. Learn may NOT compute its own phrase structure
  (Invariant #3) and writes only `LearnState` (Invariant #1).

**Shared helpers / utilities:**
- Audio DSP: `src/vibemix/audio/`. Prompt/anti-slop: `src/vibemix/prompts/`,
  `src/vibemix/coach/`. Model resolution: ALWAYS `src/vibemix/llm/model_router.py`.

## Special Directories

**`tauri/src-tauri/binaries/vibemix-core-*/`:**
- Purpose: PyInstaller-frozen Python sidecar bundle.
- Generated: Yes (BUILD ARTIFACT). Lags edited `src/` — verify backend wiring by
  running `main()` on current source, not the bundled binary.
- Committed: present in tree but not hand-edited source.

**`src/vibemix/agent/moss_tts/`:**
- Purpose: local MOSS-TTS model mount; no `.py` source.
- Generated/cached: the model itself lives under `~/.cache/vibemix/moss-tts-onnx/`.

**`mocks/`:**
- Purpose: HTML visual contracts (the design source of truth). Canonical:
  `vibemix-rebuild-session.html` (app shell), `vibemix-direction-final.html`
  (visual language). Treated as the visual contract by `frontend-enforcement`.
- Generated: No. Committed: Yes.

**`.planning/`:**
- Purpose: GSD source of truth — `ROADMAP.md`, `REQUIREMENTS.md`, `PROJECT.md`,
  `STATE.md`, `codebase/*.md` (these maps), `research/`, `packets/`, `phases/`,
  `handoffs/`.
- Committed: Yes.

**`~/.cache/vibemix/` (runtime, off-tree):**
- Purpose: on-disk model + library state — `clap-onnx/`, `moss-tts-onnx/`,
  `library-clap.db` (sqlite-vec), `embeddings.db`, `library.pkl`, `memory.db`.
- Generated: Yes. Committed: No.

---

*Structure analysis: 2026-06-08*
