# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

<!-- GSD:project-start source:PROJECT.md -->
## Project

**vibemix — AI DJ Co-Host**

A free, open-source AI co-host for live DJ sets. Runs locally on macOS or Windows: listens to your master output, watches your DJ software's screen, ingests your controller actions over MIDI, and talks back into your headphones or speakers as either a hype-man (party mode) or a coach (feedback mode). Three user levels — Beginner / Intermediate / Pro — with prompt templates tuned to each, plus a curated library of ~10 popular MIDI controllers mapped out of the box.

Bravoh's first open-source release. Built as a polished, narrow-scope utility that warms an audience converting into Bravoh's waitlist.

**Core Value:** The AI reacts to your set in a way that feels alive and grounded — never hallucinating, never breaking the flow, never sounding like generic AI slop. If reactions feel forced, late, fake, or scripted, the product fails. The bar is "real DJ friend in your ear", not "voice assistant doing music commentary".

### Constraints

- **Timeline**: No hard calendar target — ship-when-ready per `gsd-autonomous fully` mode. External Apple + SignPath approvals are the critical path; engineering parallelizes around the external clock.
- **Quality bar**: "Real DJ friend in your ear, no AI slop" — Kaan will block release if reactions feel scripted, late, hallucinated, or generic.
- **Budget**: 150-200 € launch marketing (IG ads, paid posts), ~50 €/month ongoing Gemini API for end-user requests. Reassess if usage scales.
- **Tech stack**: Locked on LiveKit pipeline + Gemini 3 Flash + Gemini TTS streaming. No other LLM providers (Bravoh is Gemini-only).
- **Platforms**: macOS + Windows in v1. Linux explicitly excluded.
- **Team**: Kaan (engineering + product), Francesco (cofounder — product/marketing/DJ network for outreach), Momo (Bravoh team). Bravoh main product takes priority — vibemix runs alongside.
- **Open-source license**: Apache 2.0 (in `LICENSE`; `__main__.py` carries the SPDX header). Permits Bravoh internal reuse.
- **Security**: API key embedded in distributed binary is the API-key-protection problem of the year — solve via Bravoh-side proxy with per-client rate limit, not by shipping a raw key.
- **Hallucination grounding**: No release until verification phase confirms reactions are tied to real events. This is a hard gate.
<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->
## Technology Stack

> Hand-maintained (this GSD block has no auto-syncer — update it when you refactor `src/vibemix/`). Authoritative dependency pins live in `pyproject.toml` + `uv.lock`; this is the orientation summary.

### Languages & runtime
- **Python 3.12** (`requires-python = ">=3.12,<3.13"`; `.venv/` is 3.12.x). All app logic under `src/vibemix/`.
- **TypeScript + Rust** — Tauri desktop shell under `tauri/` (`tauri/ui/` TS frontend, `tauri/src-tauri/` Rust parent process).
- **Vanilla JS / HTML / CSS** — `mascot.html` overlay (Canvas 2D, no build step), wired to `vibemix.runtime.ws_bus`.
- Packaged with **hatchling**; **`uv`** is the runner + lockfile tool (`uv.lock`).

### Core dependencies (pins in `pyproject.toml`)
- `google-genai` — the **sole** AI provider (Gemini Flash multimodal + TTS + embeddings). No other LLM/embedding provider, ever (Bravoh is Gemini-only).
- `livekit` + `livekit-agents` + `livekit-plugins-google` + `livekit-plugins-openai` — LiveKit pipeline (Gemini Live `RealtimeModel` path; the openai plugin is the TTS-fallback seam, not a second AI provider).
- `numpy` + `scipy` — all audio DSP (RMS, FFT bands, onset, BPM, 48k→16k resample).
- `sounddevice` — CoreAudio (macOS) / WASAPI (Windows) I/O.
- `mido` + `python-rtmidi` — MIDI controller decode.
- `httpx`, `keyring` — HTTP + OS keychain (BYO-key path).
- `pyrekordbox` (`==0.4.4`, installed `--no-deps`) — Rekordbox `collection.xml` import only; SQLCipher path explicitly unused (see the install-recipe comment in `pyproject.toml`).
- System (not pip): macOS — BlackHole 2ch, `nowplaying-cli` (Homebrew), `pyobjc-*` (Quartz window crop). Windows — WASAPI loopback (`docs/windows-setup.md`).

### Configuration
- `.env` at repo root: `GEMINI_API_KEY` (required) + `OPENROUTER_API_KEY` (TTS fallback chain). Loaded via `python-dotenv`.
- **Model selection is config-driven through `vibemix.llm.model_router` — zero hardcoded model literals in code (CI grep-gated).** Never inline a model name; resolve via `model_router.resolve(...)`.
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

- **Naming:** `snake_case` modules/functions, `PascalCase` classes, `UPPER_SNAKE_CASE` module constants. Private helpers `_prefixed`; module feature flags `_HAS_*`. Long-running async tasks named `*_loop`.
- **Type hints:** `from __future__ import annotations` + PEP 604 unions throughout; numpy arrays typed `np.ndarray`. No enforced mypy/pyright — hints are documentation.
- **Async vs sync:** `asyncio` main loop (`asyncio.run(main())` in `__main__.py`). sounddevice audio callbacks are synchronous and run on OS audio threads; the MIDI listener runs on a daemon thread (mido is blocking). Cross-thread state is shared via `threading.Lock` in buffer classes — no async queues across the audio/event-loop boundary. Blocking work is offloaded with `loop.run_in_executor`.
- **DI over globals:** state objects are allocated in `main()` and passed explicitly. The only module-level singletons are feature flags.
- **Shutdown:** every long-running coroutine takes `stop_event: asyncio.Event` as a cooperative stop signal.
- **Comments:** explain *why* (especially DSP constants/thresholds), not *what*. Module docstrings describe data flow.
- **Logging:** startup lines `-> ...`; errors bracket-tagged to stderr (e.g. `[coach err]`); AI transcript `AI> `; structured per-session events to `events.jsonl`.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Single packaged app under `src/vibemix/`. Entry point: `python -m vibemix` → `vibemix.__main__:main()` — an async orchestrator (ported from the retired `cohost_v4.py`, then restructured behind platform backends so it stays OS-agnostic). The Tauri shell (`tauri/`) spawns this Python process as a sidecar.

### Subpackages (`src/vibemix/`)
- `audio/` — capture/playback ring buffers, `Levels` (EMA RMS), mic gating, ws constants (`WS_HOST`/`WS_PORT`).
- `platform/` — per-OS audio/screen/MIDI/track backends (`_audio_macos.py`, Windows WASAPI, etc.). The firewall that keeps `__main__` OS-agnostic; selected at runtime.
- `state/` — **the brain.** `music_state.py` (`MusicState`, single source of truth) written ONLY by `refresh.py`'s state-refresh loop; `event_detector.py` emits typed events with per-type cooldowns (`TRACK_CHANGE`, `PHASE`, `LAYER_ARRIVAL`, `MIX_MOVE`, `HEARTBEAT`, …); `coach.py` builds evidence-grounded prompts; `evidence_registry.py` backs citation grounding; `deck_*` (deck-aware state), `harmonics.py` (Camelot), plus `genre/` + `detectors/`.
- `agent/` — LiveKit `RealtimeModel` session + the Gemini reaction path (`dj_cohost.py`).
- `llm/` — `model_router.py` (config-driven model resolution, no hardcoded literals) + `thinking_gate.py`.
- `coach/`, `prompts/`, `profile/` — persona/prompt templates per user level; long-term DJ profile.
- `library/` — Gemini-embedding (1536-dim) + sqlite-vec vibe search (macOS sqlite-vec / Windows numpy, bit-identical top-K parity); also home to `next_suggestion.py` (the pill's mean-centered "what's next" engine, grounded by Invariant #2) and the Viber curator core (`toolset.py`/`agent.py`/`codex_curate.py`/`mcp_server.py`/`telegram_bridge.py`). **State on disk** under `~/.cache/vibemix/`: `library.db` (sqlite-vec vectors), `embeddings.db` (content-hash embed cache), `library.pkl` (track-title cache), `library_centroid.npy` (cached query centroid, auto-recomputed on store change). **Gotcha:** library/rekordbox tests MUST monkeypatch `RekordboxLibrary.CACHE_PATH` to a tmp dir, or they overwrite the real `library.pkl`.
- **CLAP embedding engine** (the chosen similarity/library/curate engine replacing Gemini-embedding; the co-host *brain* stays Gemini-only): staged at `library/clap_engine.py` + `docs/clap-engine.md` — laion_clap **630k-fusion** (`model_id=3`, HTSAT-tiny, 512-dim, deterministic 10s-chunk mean-pool). **Run real CLAP locally with ZERO download** via the worker venv: `/Users/ozai/projects/bravoh-gpu-worker/venv/bin/python` already has `laion_clap` + the checkpoints, and `bravoh-gpu-worker/clap_mix_only.py` holds the proven `load_and_chunk`/`embed_chunks`. **Gotchas:** the HF `transformers.ClapModel` port is broken for text→audio (use the `laion_clap` pip API only); CLAP is anisotropic so mean-centering is mandatory; text→audio is reliable for coarse genre, not fine vibe.
- `memory/` — local `memory.db` copilot store (sqlite-vec); gated behind `VIBEMIX_RECALL_ENABLED` (default off).
- `debrief/` — post-session review UI (second Tauri window, port 8766).
- `events/`, `midi/` (10-controller `profiles/` — the single-source catalog), `install/`, `ui_bus/`, `runtime/` (`ws_bus`, `wizard`, `session_loop`, `soak`, `ttft`, recordings index, `suggestion.py` = the pill's `SuggestionService`).

### Cardinal invariants (test-enforced — do not break)
1. **Single-writer** — only the state-refresh loop writes `MusicState`; everything else reads.
2. **Citation grounding** — every citation a reaction emits must resolve in `EvidenceRegistry`; un-cited reactions strip to the ack-bank fallback. This is the anti-slop release gate.
3. **Trust the audio** — live audio evidence is authoritative; the AI reacts to real detected events, never invents them.
4. **One socket** — the mascot/wizard bus binds `127.0.0.1:8765` only (never two listeners at once); debrief uses `8766`.

### Threading & generation model
sounddevice callbacks (OS audio thread) → lock-protected buffers → asyncio event loop (AI calls, ws, state loops) ← MIDI daemon thread. A single in-flight Gemini generation is enforced by an `in_flight` flag with a stale-age force-clear. Errors are caught per-loop and logged to stderr + `events.jsonl`; a loop failure never wedges the `in_flight` gate.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

| Skill | Description | Path |
|-------|-------------|------|
| frontend-enforcement | Project-local enforcement of vibemix frontend design standards. Loaded automatically by GSD agents that touch frontend code or UI design — frontend-design discipline, 20/80 rule, textured material feel, no AI slop. | `.claude/skills/frontend-enforcement/SKILL.md` |
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->

## Commands

The repo is now a packaged project: `pyproject.toml` (hatchling) + `uv.lock` at root, Python `>=3.12,<3.13` (the `.venv/` is 3.12.x — **not** 3.14, despite stale notes elsewhere in this file). `uv` is the runner. Source lives in `src/vibemix/`; the Tauri desktop shell is under `tauri/`.

**Run the co-host (dev):**

```bash
uv run python -m vibemix          # launches the real session loop (vibemix.__main__:main)
```

**Run the test suite** (the authoritative dev workflow, per CONTRIBUTING.md):

```bash
source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q
# or, without activating:  uv run pytest -q
```

Opt-in markers (default run skips them): `-m macos_audio`, `-m windows_only`, `-m integration`, `-m slow`, `-m e2e`, `-m cli`, `-m network`. See `[tool.pytest.ini_options]` in `pyproject.toml`.

**Library / vibe-search CLI** (the embedding workflow — see `docs/library.md`):

```bash
uv run python -m vibemix library embed-folder "<dir>" [--strategy mean_excerpt|cue_anchored]  # walk+embed a folder, no Rekordbox XML needed
uv run python -m vibemix library search "<text vibe>" [-k N]      # text→tracks (cross-modal)
uv run python -m vibemix library similar "<track_id|file path>"   # track→similar
uv run python -m vibemix library curate "<theme>" [--interactive] [--backend gemini|codex]  # Viber agent → grounded M3U/JSON playlist; --interactive = agent asks→builds (docs/codex-agent.md)
uv run python -m vibemix library telegram                         # Viber mobile surface — long-poll bot, curate from your phone
uv run python -m vibemix library budget --json                    # offline cost telemetry
```

The Telegram bridge (`library/telegram_bridge.py`, lazy-imports `python-telegram-bot`) needs `VIBEMIX_TELEGRAM_TOKEN` (BotFather) + `VIBEMIX_TELEGRAM_ALLOWED_CHATS` (numeric chat-id allow-list = the v1 auth, fail-closed). Pure logic (allow-list/leak-strip/reply-format) is dep-free + unit-tested; outbound messages are path-scrubbed (privacy); each request runs the Gemini agent under a wall-clock timeout (no-hang).

The Viber agent (`library/toolset.py` = shared grounded tool core) has two backends: `gemini` (built-in fn-calling, default) and `codex` (BYO ChatGPT-sub via `codex exec` + `library/mcp_server.py` MCP STDIO server — needs `codex login`). Grounding (seen-set + library re-validation) is identical across both. Codex is NOT bundled; `--backend codex` fails actionably when absent.

Embeds need `GEMINI_API_KEY` (client picks direct key first, else proxy JWT). embed-folder is resumable: a content-hash cache skips already-embedded files for free, and per-file errors are logged + skipped, never fatal. Ranking is mean-centered by default (anisotropy fix) — query-side only, persisted vectors untouched.

**Required environment:** `.env` at repo root with `GEMINI_API_KEY=...` (and `OPENROUTER_API_KEY=...` for the TTS fallback chain). Read via `python-dotenv`.

**macOS prerequisites:** BlackHole 2ch (`brew install blackhole-2ch`), `nowplaying-cli` (`brew install nowplaying-cli`), a DJ app routed through BlackHole as the audio source, Pioneer DDJ-FLX4 over USB (optional, graceful fallback). Windows uses WASAPI loopback — see `docs/windows-setup.md`.

## Planning Home

`.planning/` is the GSD source of truth — `ROADMAP.md`, `REQUIREMENTS.md`, `PROJECT.md`, `STATE.md`, plus `codebase/*.md` (codebase maps) and `research/*.md` (pre-roadmap research). The codebase maps in `.planning/codebase/` feed the GSD-managed sections of this file. `MILESTONES.md` tracks shipped milestones (v0.1.0 → v8.0 "Proof & Polish" shipped 2026-05-25; phases run continuously, currently 76+).

When a phase is active, its planning artifacts live under `.planning/phases/<NN>-<slug>/` (CONTEXT.md, RESEARCH.md, PLAN.md, etc.). Read those before touching code on that phase.

## POC Variants — RETIRED (2026-05-20)

The root POC variant zoo (`cohost.py`, `cohost_v2.py`, `cohost_lk.py`, `cohost_v3.py`, `cohost_v4.py`, `cohost.streaming.py.bak`, plus `run*.sh`, `generate_bat.py`, `test_voice.py`) has been **pruned**. Their load-bearing intuition — mic gating, evidence-packet shape, event taxonomy, audible-deck heuristics, MIDI maps, the OpenRouter-primary TTS chain and tuned event cooldowns — was lifted wholesale into `src/vibemix/` over Phases 2-13 and beyond. The variants were deleted to end the recurring "which file is canonical?" confusion now that the package supersedes them.

The retirement is enforced by `tests/repo/test_repo_scrub.py::test_retired_poc_files_stay_gone` (a stray `git add` cannot resurrect them). The v3/v4 design notes survive as research under `.planning/research/v3-shipped/`. If you need the historical source, it is in git history.

`mascot.html` at root is **not** a POC — it is the live overlay wired into `vibemix.runtime.ws_bus` + CI (`mascot-audit`). Keep it.

## UI Mocks

`mocks/` holds the design contracts referenced by UI phases — notably `vibemix-app-ui.html` (live session UI shape) and `vibemix-cinematic-storyboard.html` (hero demo storyboard). When working on Phases 11–14, treat these as the visual reference, lifted by the `frontend-enforcement` skill.
