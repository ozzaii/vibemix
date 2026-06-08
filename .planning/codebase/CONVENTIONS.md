# Coding Conventions

**Analysis Date:** 2026-06-08

vibemix is a polyglot tree: Python 3.12 under `src/vibemix/` (app logic), TypeScript/Vite under `tauri/ui/` (desktop webviews), Rust under `tauri/src-tauri/` (parent process), plus vanilla JS/HTML/CSS in `mascot.html`. Conventions below are split by language; the hard cross-cutting rules (model-router, optimistic repaint, shared-git-commit, `LC_ALL=C`) are called out explicitly because they are the ones that bite.

## Naming Patterns

**Python (`src/vibemix/`):**
- Modules + functions: `snake_case` (`music_state.py`, `event_detector.py`, `next_suggestion.py`).
- Classes: `PascalCase` (`MusicState`, `RekordboxLibrary`, `ClapEmbedder`, `ModelRouter`).
- Module constants: `UPPER_SNAKE_CASE` (`HEARTBEAT_SEC`, `PASSTHROUGH_GAIN`, `WS_HOST`, `WS_PORT`, `BUILD_SET_TIMEOUT_S`, `TRANSCRIPT_RING_CAP`).
- Private helpers: `_prefixed` (`_to_service_tier`, `_python_gate_check`, `_router_config._ROUTES`). The leading underscore also marks "do not import across packages."
- Module feature flags: `_HAS_*` (`_HAS_QUARTZ`, `_HAS_PIL` in `src/vibemix/platform/_screen_macos.py`). NOTE: newer platform backends prefer a capability-probe function `is_available()` over module-level `_HAS_*` flags (`src/vibemix/platform/screen.py`, `src/vibemix/platform/_audio_macos.py` both document dropping the v4 flags) — follow `is_available()` for new platform code; `_HAS_*` survives only where a hard import-time guard is genuinely needed.
- Long-running async tasks: `*_loop` (`live_grade_loop`, `tick_loop` in `src/vibemix/learn/runtime.py`; `run_poll_loop`, `run_capture_loop` in `src/vibemix/platform/`; `_serve_loop` in `src/vibemix/debrief/main.py`).
- Per-OS backend modules: `_<surface>_<os>.py` (`_audio_macos.py`, `_screen_windows.py`, `_track_macos.py`) under `src/vibemix/platform/`.

**TypeScript (`tauri/ui/src/`):**
- Files: `kebab-case.ts` (`cohost-model.ts`, `event-ribbon.ts`, `render-loop.ts`); component/shell classes occasionally `PascalCase.ts` (`SessionLayout.ts`, `DesktopShell.ts`, `Sidebar.ts`).
- Test files: `*.test.ts` (co-located unit) and `*.spec.ts` (DOM/integration), `*.dom.spec.ts` for explicitly-jsdom specs.
- Interfaces/types: `PascalCase` (`SessionState`, `MetersTriple`, `StatusFlags`, `CohostReaction`).
- Functions: `camelCase` (`setSessionState`, `appendTranscript`, `mountSessionLayout`, `renderSessionFrame`).
- Test-only helpers carry the `_` prefix + `ForTests` suffix (`_resetSessionStateForTests` in `tauri/ui/src/session/state.ts`).
- IPC envelopes: dotted `ipc.<domain>.<verb>` strings (`ipc.session.snapshot`, `ipc.settings.set`, `ipc.library.import_progress`, `ipc.session.set_mode`).

## Code Style

**Python — ruff (`[tool.ruff]` in `pyproject.toml`):**
- `target-version = "py312"`, `line-length = 100`, `src = ["src"]`.
- Lint select: `["E4", "E7", "E9", "F", "B", "I", "UP", "RUF"]`. `E501` (line length) is ignored — the formatter owns wrapping, not the linter.
- `RUF001/002/003` ignored: docstrings/comments intentionally carry Turkish text, sigma notation, and DJ-math glyphs.
- Format: `quote-style = "double"`, `indent-style = "space"`, `docstring-code-format = true`.
- Retired POC files (`cohost*.py`, `test_voice.py`, `generate_bat.py`) are blanket-ignored via `per-file-ignores` — do not add new code there; they are scrub-gated to stay deleted anyway.

**TypeScript:**
- `tsc --noEmit` is the type gate (run as the first half of `npm run build`). No separate ESLint/Prettier config is checked in — `tsc` strictness + vitest are the discipline.
- Strict null handling everywhere: optional fields are typed `T | null` and explicitly defaulted in `makeDefault()` so the render loop never reads `undefined` (`tauri/ui/src/session/state.ts`).

## Type Hints (Python)

- `from __future__ import annotations` is the house rule — present in 348 of 360 `src/vibemix/` modules. Add it to the top of every new module.
- PEP 604 unions throughout: `ServiceTier | None`, `str | None`, `asyncio.Event | None`.
- numpy arrays typed `np.ndarray`.
- **No enforced mypy/pyright** — hints are documentation + IDE assist, not a CI gate. pydantic is banned for model-gen (jsonschema validates the IPC boundary instead; see `pyproject.toml` comment at the `jsonschema` dep). Do not reach for a runtime type-validation framework.

## Async vs Sync (Python)

The threading model is load-bearing — get it wrong and you race the audio callback or wedge the event loop:
- **asyncio main loop** owns AI calls, the ws bus, and all state loops. Entry: `asyncio.run(main())` in `src/vibemix/__main__.py`.
- **sounddevice callbacks are synchronous** and run on OS audio threads (CoreAudio / WASAPI). Never `await` inside one; never block one.
- **The MIDI listener runs on a daemon thread** (mido is blocking).
- **Cross-thread state crosses via `threading.Lock`** inside the buffer classes — NOT async queues across the audio/event-loop boundary.
- **Blocking work is offloaded** with `loop.run_in_executor(...)`.
- **Long-running coroutines are named `*_loop`** and take a `stop_event: asyncio.Event` (see Shutdown).
- A single in-flight Gemini generation is enforced by an `in_flight` flag with a stale-age force-clear; a per-loop exception must never leave that gate stuck.

## DI Over Globals (Python)

- State objects are allocated in `main()` (`src/vibemix/__main__.py`) and passed explicitly down the call tree. Do not reach for module-level mutable singletons.
- The ONLY sanctioned module-level singletons are feature flags (`_HAS_*`) and frozen config tables (`ROUTER_PATHS`, `_ROUTES`).
- TS mirror: `tauri/ui/src/session/state.ts` holds one `currentState` singleton, but it is write-restricted — only `ws-bridge.ts` writes, the rAF render loop reads. There is no pub/sub; see the optimistic-repaint rule below.

## Cooperative Shutdown (Python)

- Every long-running coroutine takes `stop_event: asyncio.Event` as a cooperative stop signal (`src/vibemix/__main__.py:566`, `:2181`; `learn/runtime.py` loops). Check it in the loop body; never rely on task cancellation alone.
- Per-resource teardown errors are caught and bracket-tagged to stderr (`[close stream err]`, `[close mic err]`, `[close recorder err]`, …) so a failing close never blocks the rest of shutdown.

## The Hard Model-Router Rule (CI grep-gated)

**Zero hardcoded model literals in `src/vibemix/`.** Resolve every model id through `vibemix.llm.model_router`:

```python
from vibemix.llm.model_router import resolve, resolve_model
model_id, tier = resolve("agent.cohost.realtime")   # (model_id, ServiceTier | None)
model_id = resolve_model("library.embed")            # str only, no Gemini SDK import
```

- The single allowlisted file that may carry a literal is `src/vibemix/llm/_router_config.py` (`_ROUTES`). Add a new path there and `resolve(...)` it — never inline `"gemini-…"` in code.
- Enforced two ways that must stay in lockstep: the bash gate `scripts/release/check_no_hardcoded_model.sh` (GitHub Actions truth, `.github/workflows/model-literal-check.yml`) and the pytest mirror `tests/repo/test_model_literal_gate.py` (cross-platform, runs in the default suite). Banned pattern set: `gemini-3-flash`, `gemini-3-pro`, `gemini-embedding-`, `gemini-3.1-flash`, `gemini-2.5-flash`, `gemini-3.1-flash-live`.
- Scope is `src/vibemix/` only — `tests/`, `scripts/`, `docs/` may carry literals (contract canaries, eval judges).
- `resolve(path)` raises `RouterPathError` (a `KeyError` subclass) on an unknown path and lists every valid key in the message — let it raise, do not swallow.

## Logging Conventions

- **Startup lines** are `print(f"-> ...")` (`src/vibemix/__main__.py`: `-> brain:`, `-> tts:`, `-> env:`). Diagnostic startup lines go to stderr with `flush=True`.
- **Errors are bracket-tagged to stderr**: `print(..., file=sys.stderr)` with a `[<area> err]` tag (`[coach err]`, `[buf push err]`, `[close … err]`). The tag names the subsystem so a stderr scan is greppable.
- **AI reactions are NOT logged to stderr** — they broadcast to the UI over the ws bus as `transcript_delta` (and `ipc.session.cohost-reaction` with citation strips). Keep reaction text off stderr.
- **Structured per-session events** go to `events.jsonl` (one JSON object per line) for offline analysis (bench, debrief). A loop failure logs to BOTH stderr and `events.jsonl` and never wedges the `in_flight` gate.

## Comments

- Explain **why**, not what — especially DSP constants and thresholds (`HEARTBEAT_SEC=180.0`, `PASSTHROUGH_GAIN=0.0`, EMA/RMS windows). A bare magic number with no rationale is off-pattern.
- Module docstrings describe **data flow** (e.g. `model_router.py`'s docstring states the resolution rules + the off-pattern warning).
- Comments routinely cite the Phase/Plan that introduced a line (`Phase 12 Wave 3`, `Plan 41-01`) — this is the project's change-provenance idiom; keep it when editing those lines.
- Prose authored into the repo (docstrings, UI copy, PR text) is subject to the `stop-slop` skill (`.claude/skills/stop-slop/SKILL.md`) — its phrase list also seeds the runtime co-host filter (`src/vibemix/prompts/negative_dict.py`).

## Frontend Conventions (`tauri/ui/`)

**Optimistic repaint — mandatory for settings controls.** `tauri/ui/src/session/state.ts::setSessionState` has NO pub/sub and the settings drawer does NOT re-render on the `ipc.settings.state` echo. A control that waits for the round-trip looks dead ("no buttons work"). Flip `data-active` locally in the click handler (mirror `picker.ts::selectOption`); the ~3ms round-trip stays authoritative and self-corrects. Every mode/mood/skill rocker in `state.ts` documents this pattern inline ("writes locally then fires the envelope").

**IPC codegen is required after schema edits.** After editing `tauri/ui/src/ipc/messages.schema.json`, run `npm run codegen:ipc` (`node scripts/codegen-ipc.mjs`). The ajv validator is **pre-compiled** to `tauri/ui/src/ipc/validator.generated.mjs` — stale codegen silently rejects new fields. The `ipc-wiring-checker` skill (`.claude/skills/ipc-wiring-checker/`) covers the Python↔TS boundary; the Python side validates the same `messages.schema.json` (Draft-07) via `jsonschema`.

**One singleton, write-restricted.** `state.ts` holds `currentState`; only `ws-bridge.ts` writes it, the rAF render loop reads it. No per-component `setInterval`/`rAF` anywhere downstream — components diff previous vs new frame and mutate CSS variables. Append paths (`appendTranscript`, `appendMidiEvents`, `appendReaction`) ring-cap (`TRANSCRIPT_RING_CAP=200`, `MIDI_EVENT_RING_CAP=12`).

**Design discipline** is enforced by the `frontend-enforcement` skill (`.claude/skills/frontend-enforcement/SKILL.md`): retro-futurist hardware aesthetic, 20/80 accent rule, textured material surfaces, no Inter/Roboto/system-ui, no generic AI slop. UI contracts live in `mocks/` (canonical: `vibemix-rebuild-session.html`, `vibemix-direction-final.html`).

## Shell-Numeric Gotcha (Turkish locale)

This Mac is Turkish-locale. Prefix any `awk`/`printf`/`bc` output that feeds `ffmpeg -ss` or numeric tooling with `LC_ALL=C` — otherwise the locale emits comma decimals (`117,37`) that ffmpeg cannot parse and clip renders fail SILENTLY. Already applied in `scripts/dist/sign_macos.sh` and `scripts/eval/clap_retrieval.py`; carry it into any new shell that pipes a computed float into a binary.

## Shared-Git-Commit Hazard

`git commit` is shared across concurrent Claude sessions on this tree (Kaan runs 2+ in parallel). `git commit` absorbs EVERY file staged across all sessions. Before committing, verify `git diff --cached --name-only` matches your intended set. `git reset --soft HEAD~1` keeps racing; the safe atomic message-only fix is `git commit --amend -m "..."` when nothing else is staged. For a shared file already carrying another session's hunks, write a filtered patch (your hunks only) and `git apply --cached --recount` (interactive `git add -p` is unavailable here). Commit identity: `Kaan Özkan <rahipdotaci@gmail.com>`.

## Function & Module Design

- Functions stay single-purpose; private helpers `_prefixed` decompose larger flows (see `model_router.resolve` delegating to `_to_service_tier`, `resolve_model`).
- Modules export an explicit `__all__` where the public surface matters (`model_router.py`: `["ROUTER_PATHS", "RouterPathError", "resolve", "resolve_model"]`).
- The `intel/` subpackage is import-light by contract: no model clients, no audio capture, no Tauri, no filesystem writes — keep new musical-intelligence primitives dependency-free.
- Every Python source file opens with `# SPDX-License-Identifier: Apache-2.0` (Apache-2.0 is the client license; `__main__.py` carries the full header).

---

*Convention analysis: 2026-06-08*
