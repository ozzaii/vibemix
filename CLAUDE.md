# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> **STATUS — vibemix is PARKED (2026-06-19).** Priority shifted to **Viber WA** (BRAVOH's WhatsApp
> CMO superagent → `~/projects/bravoh-ai/CLAUDE.md`). Code is intact; the 122 vibemix project
> memories were archived on park (nothing deleted; the archive dir is NOT under `~/.claude` on this
> Mac — ask Kaan for the location before un-parking). This file stays the vibemix product reference for when work resumes.

<!-- GSD:project-start source:PROJECT.md -->
## Project *(il progetto)*

**vibemix — AI DJ Co-Host**

*Dunque* — a commercial AI co-host product for live DJ sets, with an Apache-licensed client.
Runs locally on macOS or Windows: listens to your master output, watches your DJ
software's screen, ingests your controller actions over MIDI, and talks back into
your headphones or speakers as either a hype-man (party mode) or a coach
(feedback mode). Three user levels — Beginner / Intermediate / Pro — with prompt
templates tuned to each, plus a curated library of ~10 popular MIDI controllers
mapped out of the box.

Bravoh's first vibemix release is a monetized product path, not a
fully-open-source promise. Keep public copy honest: the client is Apache-licensed;
hosted Bravoh services and release infrastructure are commercial.

**Core Value:** The AI reacts to your set in a way that feels alive and grounded — never hallucinating, never breaking the flow, never sounding like generic AI slop. If reactions feel forced, late, fake, or scripted, the product fails. The bar is "real DJ friend in your ear", not "voice assistant doing music commentary".

### Constraints *(i vincoli)*

- **Timeline**: No hard calendar target — ship-when-ready per `gsd-autonomous fully` mode. External Apple + SignPath approvals are the critical path; engineering parallelizes around the external clock.
- **Quality bar**: "Real DJ friend in your ear, no AI slop" — Kaan will block release if reactions feel scripted, late, hallucinated, or generic.
- **Budget**: 150-200 € launch marketing (IG ads, paid posts), ~50 €/month ongoing Gemini API for end-user requests. Reassess if usage scales.
- **Tech stack**: Sven, the live co-host, is locked on the LiveKit pipeline + Gemini
  Flash for grounded reaction planning, with speech rendered by the local Chatterbox
  voice only (exact model versions resolved via `model_router`, never inlined). Viber is the
  library/set-prep agent/operator, pinned to local Codex via MCP; do not call
  Viber the co-host and do not route it through Gemini. **Name collision:** this
  vibemix-Viber is unrelated to **"Viber WA"** — BRAVOH's Momo WhatsApp CMO superagent
  on the altidus server (`hermes-viber.service`, gpt-5.5/Codex). Same name, different
  system → `~/projects/bravoh-ai/CLAUDE.md`. (Sven = the live co-host voice, the third name.)
- **Platforms**: macOS + Windows in v1. Linux explicitly excluded.
- **Team**: Kaan (engineering + product), Francesco (cofounder — product/marketing/DJ network for outreach), Momo (Bravoh team). Bravoh main product takes priority — vibemix runs alongside.
- **Open-source license**: Apache 2.0 (in `LICENSE`; `__main__.py` carries the SPDX header). Permits Bravoh internal reuse.
- **Security**: API key embedded in distributed binary is the API-key-protection problem of the year — solve via Bravoh-side proxy with per-client rate limit, not by shipping a raw key.
- **Hallucination grounding**: No release until verification phase confirms reactions are tied to real events. This is a hard gate.
<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->
## Technology Stack *(lo stack tecnologico)*

> Hand-maintained (this GSD block has no auto-syncer — update it when you refactor `src/vibemix/`). Authoritative dependency pins live in `pyproject.toml` + `uv.lock`; this is the orientation summary.

### Languages & runtime *(i linguaggi)*
- **Python 3.12** (`requires-python = ">=3.12,<3.13"`; `.venv/` is 3.12.x). All app logic under `src/vibemix/`.
- **TypeScript + Rust** — Tauri desktop shell under `tauri/` (`tauri/ui/` TS frontend, `tauri/src-tauri/` Rust parent process).
- **Vanilla JS / HTML / CSS** — `mascot.html` overlay (Canvas 2D, no build step), wired to `vibemix.runtime.ws_bus`.
- Packaged with **hatchling**; **`uv`** is the runner + lockfile tool (`uv.lock`).

### Core dependencies *(le dipendenze)* (pins in `pyproject.toml`)
- `google-genai` — Sven's live co-host reaction-planning brain. It is **not** the
  Library/Viber reasoning, embedding, or speech path; speech is local Chatterbox,
  library/search/curate embeddings use local CLAP ONNX, and Viber set-prep runs
  through local Codex.
- Codex CLI — current local Viber reasoning backend for chat/curate/build-set during testing, reached through `codex exec` + `library/mcp_server.py`.
- `livekit` + `livekit-agents` + `livekit-plugins-google` + `livekit-plugins-openai` — LiveKit pipeline (Gemini Live `RealtimeModel` path; production speech is local Chatterbox, so do not reintroduce paid/cloud speech providers).
- `numpy` + PyAV/FFmpeg — audio DSP, local model decode, and 48k→16k resample.
- `sounddevice` — CoreAudio (macOS) / WASAPI (Windows) I/O.
- `mido` + `python-rtmidi` — MIDI controller decode.
- `httpx`, `keyring` — HTTP + OS keychain (BYO-key path).
- `pyrekordbox` (`==0.4.4`, installed `--no-deps`) — Rekordbox `collection.xml` import only; SQLCipher path explicitly unused (see the install-recipe comment in `pyproject.toml`).
- System (not pip): macOS — BlackHole 2ch, `nowplaying-cli` (Homebrew), `pyobjc-*` (Quartz window crop). Windows — WASAPI loopback (`docs/windows-setup.md`).

### Configuration *(la configurazione)*
- `.env` at repo root: `GEMINI_API_KEY` is required for Sven's live Gemini
  reaction-planning brain only; library embeddings and Viber/Codex set-prep are
  local/keyless. Do not treat `OPENROUTER_API_KEY` as a product speech provider.
  Loaded via `python-dotenv`.
- **Model selection is config-driven through `vibemix.llm.model_router` — zero hardcoded model literals in code (CI grep-gated).** Never inline a model name; resolve via `model_router.resolve(...)`.
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions *(le convenzioni)*

- **Naming:** `snake_case` modules/functions, `PascalCase` classes, `UPPER_SNAKE_CASE` module constants. Private helpers `_prefixed`; module feature flags `_HAS_*`. Long-running async tasks named `*_loop`.
- **Type hints:** `from __future__ import annotations` + PEP 604 unions throughout; numpy arrays typed `np.ndarray`. No enforced mypy/pyright — hints are documentation.
- **Async vs sync:** `asyncio` main loop (`asyncio.run(main())` in `__main__.py`). sounddevice audio callbacks are synchronous and run on OS audio threads; the MIDI listener runs on a daemon thread (mido is blocking). Cross-thread state is shared via `threading.Lock` in buffer classes — no async queues across the audio/event-loop boundary. Blocking work is offloaded with `loop.run_in_executor`.
- **DI over globals:** state objects are allocated in `main()` and passed explicitly. The only module-level singletons are feature flags.
- **Shutdown:** every long-running coroutine takes `stop_event: asyncio.Event` as a cooperative stop signal.
- **Comments:** explain *why* (especially DSP constants/thresholds), not *what*. Module docstrings describe data flow.
- **Logging:** startup lines `-> ...`; errors bracket-tagged to stderr (e.g. `[coach err]`); AI reactions broadcast to the UI over the ws bus (`transcript_delta`), not stderr; structured per-session events to `events.jsonl`.
- **Frontend settings controls must repaint OPTIMISTICALLY.** `tauri/ui/src/session/state.ts::setSessionState` has no pub/sub and the settings drawer never re-renders on the `ipc.settings.state` echo — a rocker/pill that waits for the round-trip looks dead ("no buttons work"). Flip `data-active` locally in the click handler (mirror `picker.ts::selectOption`); the ~3ms round-trip stays authoritative and self-corrects.
- **Shell numerics (this Mac is Turkish-locale):** prefix `awk`/`printf`/`bc` output that feeds `ffmpeg -ss`/numeric tools with `LC_ALL=C` — otherwise the locale emits comma decimals (`117,37`) ffmpeg can't parse and clip renders fail silently.
- **`git commit` is shared across concurrent Claude sessions on this tree** — Kaan runs 2+ sessions in parallel and `git commit` absorbs *every* file staged across all sessions, regardless of who staged it. Verify `git diff --cached --name-only` matches your intended set BEFORE committing. `git reset --soft HEAD~1` to split a mixed commit keeps racing (the next concurrent commit re-absorbs your unstaged units within seconds). Safe atomic fix when nothing is staged: `git commit --amend -m "..."` (message-only rewrite, no race window). When a SHARED file (e.g. `CLAUDE.md`) already carries ANOTHER session's uncommitted hunks, stage only yours at hunk level — interactive `git add -p` is unavailable here, so write a filtered patch (your hunks only, drop theirs) and `git apply --cached --recount`, then verify `git diff --cached` shows only your hunks before committing.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture *(l'architettura)*

*Allora* — single packaged app under `src/vibemix/`. Entry point: `python -m vibemix` → `vibemix.__main__:main()` — an async orchestrator (ported from the retired `cohost_v4.py`, then restructured behind platform backends so it stays OS-agnostic). The Tauri shell (`tauri/`) spawns this Python process as a sidecar.

### Subpackages *(i sottopacchetti)* (`src/vibemix/`)
- `audio/` — capture/playback ring buffers, `Levels` (EMA RMS), mic gating, ws constants (`WS_HOST`/`WS_PORT`).
- `platform/` — per-OS audio/screen/MIDI/track backends (`_audio_macos.py`, Windows WASAPI, etc.). The firewall that keeps `__main__` OS-agnostic; selected at runtime.
- `state/` — **the brain.** `music_state.py` (`MusicState`, single source of truth) written ONLY by `refresh.py`'s state-refresh loop; `event_detector.py` emits typed events with per-type cooldowns (`TRACK_CHANGE`, `PHASE`, `LAYER_ARRIVAL`, `MIX_MOVE`, `HEARTBEAT`, …); `coach.py` builds evidence-grounded prompts; `evidence_registry.py` backs citation grounding; `deck_*` (deck-aware state), `harmonics.py` (Camelot), plus `genre/` + `detectors/`.
- `agent/` — LiveKit `RealtimeModel` session + Sven's Gemini reaction path
  (`dj_cohost.py`). **TTS voice** = local on-device Chatterbox-Turbo via
  mlx-audio (`chatterbox_tts.py`) through `tts_chain.py` — the ONLY supported
  live engine (`tts_chain.py` raises `ChatterboxUnavailable` rather than fall
  back; macOS `say` is operator-opt-in only); cloud TTS providers are retired
  from the product path. `proxy_client.py` keeps a compatibility builder
  signature, but proxy mode also resolves to local Chatterbox speech. (MOSS is
  RETIRED — `local_tts.py` no longer exists; `moss` survives only as a legacy
  alias in `library models --install`.) All keychain access goes through
  `keyring_guard.bounded_keyring_call` (10s daemon-thread bound; a locked login
  keychain used to wedge boot forever) — never call `keyring.*` directly from a
  boot path. **Test gotcha:** the live start handler imports `chatterbox_tts`
  LAZILY, so tests that boot `main()` must mock `ChatterboxLocalTTS`/
  `engine_selected` at the SOURCE module (`vibemix.agent.chatterbox_tts`), not
  on `__main__` — a missed seam constructs the real engine (multi-GB mlx load)
  and the warm executor thread hangs the whole suite at loop shutdown.
- `llm/` — `model_router.py` (config-driven model resolution, no hardcoded literals) + `thinking_gate.py`.
- `coach/`, `prompts/`, `profile/` — persona/prompt templates per user level; long-term DJ profile.
- `library/` — local CLAP ONNX 512-dim embeddings + sqlite-vec vibe search (macOS sqlite-vec / Windows numpy, bit-identical top-K parity); also home to `next_suggestion.py` (the pill's mean-centered "what's next" engine, grounded by Invariant #2) and the Viber curator core (`toolset.py`/`codex_curate.py`/`mcp_server.py`/`telegram_bridge.py`). **State on disk** under `~/.cache/vibemix/`: `library-clap.db` (sqlite-vec vectors), `embeddings.db` / CLAP-tagged cache rows, `library.pkl` (track-title cache), `library-clap_centroid.npy` (cached query centroid, auto-recomputed on store change). Historical Gemini `library.db` may exist; do not clobber it during CLAP re-embed. **Gotcha:** library/rekordbox tests MUST monkeypatch `RekordboxLibrary.CACHE_PATH` to a tmp dir, or they overwrite the real `library.pkl`.
- **CLAP embedding engine** (the product similarity/library/curate engine): wired in `library/clap_engine.py` + `docs/clap-engine.md`; default backend is `onnx` (ship model `Xenova/larger_clap_music_and_speech`) with a torch reference backend kept for validation only. 512-dim, deterministic 10s-chunk mean-pool. `_cosine.EMBED_BACKEND` is fixed to `clap`; `build_embedder()` returns `ClapEmbedder`; `VIBEMIX_EMBED_BACKEND` is no longer the product selector. Inference target is **local per-user** (optional model download), not server-side. The full app/installer path should install the optional `[ai-local]` extra; focused jobs can use `[clap]` or `[cue]`. The shipped local path is torch-free, Transformers-free, and librosa-free: `clap`/`ai-local` install `onnxruntime` + `tokenizers`, while `cue` installs `onnxruntime`; audio decode/DSP uses PyAV/FFmpeg plus narrow numpy helpers. **Gotchas:** the HF `transformers.ClapModel` port is broken for text→audio; use the shipped Xenova ONNX path for product, CLAP is anisotropic so mean-centering is mandatory, and text→audio is reliable for coarse genre, not fine vibe. **Offline audio decode** (CLAP/CUE embed, `cue_detect.decode_to_mono`, `tempo_estimator`, energy curves) goes through `library/audio_decode.py::load_audio_mono` (bundled PyAV/`av`), NOT a system `ffmpeg`/`ffprobe` binary — those are absent in the packaged app. Don't reintroduce a binary shell-out on the decode path.
- `intel/` — pure musical-intelligence primitives (~20 modules). Deterministic claim/decision contracts (`claims.py`, `claim_validator.py`, `decision_runtime.py`, `decision_trace.py`, `decision_validator.py`), scorers (`transition_scorer.py`, `taste_model.py`), ontology + projection (`musical_ontology.py`, `profile_projection.py`), context compilation, feedback hooks, gold-label sampling/validation. Import-light by design — no model clients, no audio capture, no Tauri, no filesystem writes.
- `memory/` — local `memory.db` copilot store (sqlite-vec); gated behind `VIBEMIX_RECALL_ENABLED` (default off).
- `debrief/` — post-session review UI (second Tauri window, port 8766).
- `learn/` — **the teaching engine** (~35 modules; the v9 "Lesson One" + v11 "Earned" surface, also home to the fused-beatmatch practice loop). Skill-tree (`skill_tree.py`, `skill_recognizer.py`, `graduation.py`, `mastered_marker_writer.py`/`mastered_vocal.py`), curriculum/lessons (`curriculum.py`, `lesson_flow.py`, `course_pack.py`, `exemplar_lesson.py`), live practice + grading (`two_deck_player.py`, `beatmatch_practice_driver.py`, `beatmatch_judge.py`, `cue_placement_judge.py`, `practice_loop.py`), runtime + IPC + tutor voice (`runtime.py`, `teaching_loop.py`, `ipc_handlers.py`, `coaching_aim.py`, `prompts.py`). **Gotcha:** practice audio must NEVER play over a live set (Invariant #3) — gated by the lesson frozenset (`runtime.py`) + `TwoDeckPlayer.can_play()`, NOT the dead `exemplar_audio_forbidden` flag.
- `events/`, `midi/` (10-controller `profiles/` — the single-source catalog), `install/`, `ui_bus/`, `runtime/` (`ws_bus`, `wizard`, `session_loop`, `soak`, `ttft`, recordings index, `suggestion.py` = the pill's `SuggestionService`); `bench/` (Phase-81 dev/eval harness — multi-dimensional model bench, NOT a runtime feature).

### Cardinal invariants *(le invarianti cardinali)* (test-enforced — do not break)
1. **Single-writer** — only the state-refresh loop writes `MusicState`; everything else reads.
2. **Citation grounding** — every citation a reaction emits must resolve in `EvidenceRegistry`; un-cited reactions strip to the ack-bank fallback. This is the anti-slop release gate.
3. **Trust the audio** — live audio evidence is authoritative; the AI reacts to real detected events, never invents them.
4. **One socket** — the mascot/wizard bus binds `127.0.0.1:8765` only (never two listeners at once); debrief uses `8766`.
5. **Idle ≠ fault** — `SessionLayout`'s grounding-failure timer runs ONLY while the co-host is ACTIVE. At idle, `grounded=false` is expected (no music to ground to) — counting it falsely flips the deck to "AI service unreachable" with a blank hero (the recurring empty-screen bug). Test-guarded in `tauri/ui/tests/session/grounding-failure.spec.ts`.

> **Prompt composition contract:** see [docs/PROMPT-COMPOSITION.md](docs/PROMPT-COMPOSITION.md) — single named source for what enters the live prompt per event type (EventType × evidence-fields × citation-sources × recall-fragment × diet-mode × cooldown).

### Threading & generation model *(il modello di threading)*
sounddevice callbacks (OS audio thread) → lock-protected buffers → asyncio event loop (AI calls, ws, state loops) ← MIDI daemon thread. A single in-flight Gemini generation is enforced by an `in_flight` flag with a stale-age force-clear. Errors are caught per-loop and logged to stderr + `events.jsonl`; a loop failure never wedges the `in_flight` gate.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills *(le competenze del progetto)*

| Skill | Description | Path |
|-------|-------------|------|
| frontend-enforcement | Project-local enforcement of vibemix frontend design standards. Loaded automatically by GSD agents that touch frontend code or UI design — frontend-design discipline, 20/80 rule, textured material feel, no AI slop. | `.claude/skills/frontend-enforcement/SKILL.md` |
| stop-slop | Author-side anti-slop skill for prose Claude writes in this repo (docs, PR descriptions, plans, code comments, UI copy). Lifted from [hardikpandya/stop-slop](https://github.com/hardikpandya/stop-slop) (MIT). Its phrase list also seeds the runtime co-host filter in `src/vibemix/prompts/negative_dict.py`. | `.claude/skills/stop-slop/SKILL.md` |
<!-- GSD:skills-end -->





## Commands *(i comandi)*

*Allora* — the repo is a packaged project: `pyproject.toml` (hatchling) + `uv.lock` at root, Python `>=3.12,<3.13` (the `.venv/` is 3.12.x). `uv` is the runner. Source lives in `src/vibemix/`; the Tauri desktop shell is under `tauri/`.

**Run the co-host (dev):**

```bash
uv run python -m vibemix          # launches the real session loop (vibemix.__main__:main)
```

> **Local AI features (CLAP / CUE / local-TTS) need their extras at run time:** `uv run --extra ai-local python -m vibemix`. Plain `uv run python -m vibemix` syncs to BASE deps and PRUNES `onnxruntime`/`sentencepiece`/`tokenizers` → those features silently fall back (no error). The uv venv has no `pip` — install with `uv pip install`.

> **Local Chatterbox TTS (the product voice):** `uv run --extra ai-local python -m vibemix` — the voice is ON by default; the engine is seeded from `ConfigStore.tts_engine` via `VIBEMIX_TTS_ENGINE` in `_apply_packaged_defaults()` (setdefault, so it survives `open -a` env-stripping AND an explicit shell override still wins). The startup `-> tts:` banner reports `Chatterbox local only (provider=chatterbox-mlx)` when ready, or `unavailable (Chatterbox local only; voice muted, no fallback)` when not. Warm/dev knobs: `VIBEMIX_CHATTERBOX_START_WARMUP_TIMEOUT_S` (0 = skip start warmup), `VIBEMIX_CHATTERBOX_STREAM`, `VIBEMIX_CHATTERBOX_TEXT_PRIME`. `VIBEMIX_LOCAL_TTS` and the MOSS-TTS-Nano path are RETIRED — do not document or set them. Do not reintroduce Cartesia/cloud TTS as a speech fallback.

**Run the test suite** (the authoritative dev workflow, per CONTRIBUTING.md):

```bash
source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -q
# or, without activating:  uv run pytest -q
```

Opt-in markers (default run skips them): `-m macos_audio`, `-m windows_only`, `-m integration`, `-m slow`, `-m e2e`, `-m cli`, `-m network`, `-m parity`, `-m flaky`. See `[tool.pytest.ini_options]` in `pyproject.toml` for the authoritative set.

> **Full `pytest -q` is NOT a fast/reliable local gate.** `tests/test_main_smoke.py` boots `main()` for real and (without the source-module Chatterbox mock — see the `agent/` test gotcha above) loads the multi-GB voice model; under parallel load the full run wedges (~55min, processes pegged at 0% CPU). Practical gate: run the smoke file ALONE, and run everything else scoped by dir — `pytest -q tests/<dirs> --ignore=tests/test_main_smoke.py`.

**Tauri UI (frontend) — the authoritative gate after any `tauri/ui/` change:**

```bash
cd tauri/ui && npm run build && npm test     # build = `tsc --noEmit && vite build`; test = vitest run (~886 tests)
npm run codegen:ipc                          # REQUIRED after editing src/ipc/messages.schema.json — the ajv
                                             # validator is PRE-COMPILED (validator.generated.mjs); stale = new fields rejected
```

The bundled Python sidecar in `cargo tauri dev` is FROZEN (lags edited `src/`) → false negatives. Verify backend wiring by running `main()` on current source, not the bundled binary.

**Run the packaged GUI with env flags:** launch the binary directly — `VIBEMIX_DROP_DEBUG=1 ".../vibemix.app/Contents/MacOS/vibemix"` — Tauri inherits the shell env and passes it to the spawned sidecar (verify: `ps eww <sidecar_pid>`). `open -a vibemix` does NOT pass env (launchd strips it) → the packaged app defaults all `VIBEMIX_*` flags OFF. One instance only (socket `127.0.0.1:8765`); `pkill -f "python -m vibemix"` (or kill the sidecar PID) before relaunch.

The PyInstaller specs (`vibemix-core.{macos,windows}.spec`) auto-bundle every `vibemix.*` submodule via `collect_submodules` — a new vibemix module ships even when only lazily imported (no spec edit needed), but a new THIRD-PARTY dep must be added to the spec. To check what a rebuild actually bundled, grep the build TOC (`build/vibemix-core.macos/*.toc`) — `find dist/` only shows binary packages and misses pure-Python modules archived in the PYZ. `dist/*.dmg` is rebuilt separately from the loose `dist/vibemix-core` sidecar binary, so a sidecar rebuild does NOT refresh the .dmg.

> **Packaging gotcha:** a stale `tauri/src-tauri/target/release/installer` *file* (lowercase) case-collides with the `installer/` resource dir on macOS and makes `cargo tauri build` fail with `Not a directory (os error 20)` during the resource walk. Delete the stray file before bundling; the `installer/companion/**/*` resource glob itself is fine. The packaged app ships NO `ffmpeg`/`ffprobe` binary and `open -a` strips PATH — any code shelling to those breaks silently (the 2026-06 ingest/BPM gap); offline decode must ride bundled PyAV (`library/audio_decode.py`), not a system binary.

> **Git remotes:** `origin` = `ozzaii/vibemix` (personal); `bravoh` = `bravoh-ai/vibemix` (org, **INTERNAL** visibility, default branch `main`, dependabot-heavy). Push feature branches and open a PR into `main` — never push `main` directly.

**Library / vibe-search CLI** (the embedding workflow — see `docs/library.md`):

```bash
uv run python -m vibemix library ingest [<path>]                  # auto-detect Rekordbox + embed on-device (no flags = scan default rekordbox export)
uv run python -m vibemix library embed-folder "<dir>" [--strategy mean_excerpt|cue_anchored]  # walk+embed a folder, no Rekordbox XML needed
uv run python -m vibemix library search "<text vibe>" [-k N]      # text→tracks (cross-modal)
uv run python -m vibemix library similar "<track_id|file path>"   # track→similar
uv run python -m vibemix library gig-check <path> [--source auto|rekordbox|serato|traktor|virtualdj|engine] [--json]  # read-only preflight verdict over ANY DJ catalog (auto-sniffs collection.xml / collection.nml / database.xml / m.db / _Serato_ folder): take_it/fix_first/do_not_take, exit code IS the verdict (0/1/2). The 2026-06-12 hand-of-god wedge — map in .planning/packets/2026-06-12/HAND-OF-GOD-DIGEST.md
uv run python -m vibemix library export-guard <usb_path> --rig cdj-3000x [--json] [--filesystem fat32]  # read-only USB "will it show up?" vs a target rig (9 profiles): OneLibrary vs Device Library dual-format trap, filesystem rules, per-rig audio formats; same verdict/exit ladder. RIG_PROFILES facts are research-verified vs official AlphaTheta sources — never edit them from memory
VIBEMIX_CODEX_ALLOW_SHELL=1 uv run python -m vibemix library chat "<message>" [--history <jsonl>] [--backend codex]  # one-turn conversational Viber
VIBEMIX_CODEX_ALLOW_SHELL=1 uv run python -m vibemix library curate "<theme>" [--interactive] [--backend codex] [--name <slug>]  # Viber agent → grounded M3U/JSON playlist; local Codex is the product path
VIBEMIX_CODEX_ALLOW_SHELL=1 uv run python -m vibemix library build-set "<brief>" [--curve peak_time|...] [--n-slots N] [--export rekordbox] [--backend codex] [--name <slug>]  # discover→sequence on an energy curve→explain why; optional Rekordbox export
uv run python -m vibemix library export-set "<set.json>" --out <path> [--name <slug>]   # export a built set to Rekordbox XML
uv run --extra telegram python -m vibemix library telegram         # optional Viber mobile surface — long-poll bot, curate from your phone
uv run python -m vibemix library stats [--json]                   # offline header counts (tracks/embeddings/cache hit rate)
uv run python -m vibemix library models [--install clap|chatterbox|cue|all] [--force] [--progress] [--json]  # local AI model cache status + downloader (CLAP, Chatterbox voice, CUE-DETR; 'moss' = legacy alias)
uv run python -m vibemix library budget [--dau N] [--json]        # offline cost telemetry
```

The Telegram bridge (`library/telegram_bridge.py`, optional `telegram` extra, lazy-imports `python-telegram-bot`) needs `VIBEMIX_TELEGRAM_TOKEN` (BotFather) + `VIBEMIX_TELEGRAM_ALLOWED_CHATS` (numeric chat-id allow-list = the v1 auth, fail-closed). Pure logic (allow-list/leak-strip/reply-format) is dep-free + unit-tested; outbound messages are path-scrubbed (privacy); each request runs the local Codex Viber path under a wall-clock timeout (no-hang).

The Viber agent (`library/toolset.py` = shared grounded tool core) uses `codex` as the product backend: BYO ChatGPT-sub via `codex exec` + `library/mcp_server.py` MCP STDIO server, with `codex login` + `VIBEMIX_CODEX_ALLOW_SHELL=1`. Do not reintroduce a Gemini Viber fallback. Codex is not bundled; when absent it fails actionably. Finder-launched app paths can miss shell PATH, so `codex_curate.py` searches common Codex/Node dirs and honors `VIBEMIX_CODEX_BIN` / `VIBEMIX_NODE_BIN`.

Embeds need the CLAP ONNX model under `~/.cache/vibemix/clap-onnx/` or `VIBEMIX_CLAP_ONNX_DIR`; they do **not** need `GEMINI_API_KEY`. embed-folder is resumable: a content-hash cache skips already-embedded files for free, and per-file errors are logged + skipped, never fatal. Ranking is mean-centered by default (anisotropy fix) — query-side only, persisted vectors untouched.

**Runtime environment:** live co-host direct mode needs `GEMINI_API_KEY` in the
repo-root `.env`; do not treat `OPENROUTER_API_KEY` as a product speech fallback.
Library search, ingest, chat, curate, and build-set use local CLAP/Codex paths
and do not require a Gemini key.

**macOS prerequisites:** BlackHole 2ch (`brew install blackhole-2ch`), `nowplaying-cli` (`brew install nowplaying-cli`), a DJ app routed through BlackHole as the audio source, Pioneer DDJ-FLX4 over USB (optional, graceful fallback). Windows uses WASAPI loopback — see `docs/windows-setup.md`.

The deck passthrough stream exists to keep the output callback alive, but it ships silent: `PASSTHROUGH_GAIN=0.0` in `audio/constants.py`. It only mirrors BlackHole -> speakers if that gain is deliberately raised to `1.0`. In **Audio MIDI Setup route only the DJ app into BlackHole**; if system output or a Multi-Output device also feeds BlackHole, the co-host can hear its own voice as phantom music. Idle heartbeats are `HEARTBEAT_SEC=180.0` and speak-gated, not an automatic 45s speech loop. `VIBEMIX_DROP_DEBUG=1` prints the live drop countdown.

## Planning Home *(la base di pianificazione)*

`.planning/` is the GSD source of truth — `ROADMAP.md`, `REQUIREMENTS.md`, `PROJECT.md`, `STATE.md`, plus `codebase/*.md` (codebase maps) and `research/*.md` (pre-roadmap research). The codebase maps in `.planning/codebase/` feed the GSD-managed sections of this file. `MILESTONES.md` tracks shipped milestones (v0.1.0 → v10.0 "12-Factor Hardening", last shipped 2026-05-28). **v11.0 "Earned" — ENGINEERING-COMPLETE + audit-passed** (`717f36de`; 16/16 reqs, 3/3 phases) — the evidence-grounded DJ skill-tree: lessons fill a skill to "Competent", and only a **cited** live in-set demonstration unlocks "Mastered". Close-out ceremony HELD per Kaan; next formal milestone undecided. **Current active work: read the LATEST dated handoff in `.planning/handoffs/` FIRST**. The 2026-06-03 "WIRE-THE-GOLD" backlog and `CLAUDE_LAND_QUEUE` are SUPERSEDED history — do not treat them as the live queue. `.planning/STATE.md` holds milestone history.

When a phase is active, its planning artifacts live under `.planning/phases/<NN>-<slug>/` (CONTEXT.md, RESEARCH.md, PLAN.md, etc.). Read those before touching code on that phase.

**Ship-readiness ground truth (2026-06-10):** `.planning/audits/2026-06-10-pre-fable-gobble/` — a 15-subsystem, adversarially-verified audit of HEAD `a153915c` (24 confirmed launch findings in `RESULT.json` + `fix-lanes/*.json`, raw agent transcripts alongside). Read it before re-auditing ship-readiness or trusting an older teardown's bug list; the fix wave landing after it supersedes the per-finding status, not the map.

## POC Variants — RETIRED *(le varianti, ormai in pensione)*

Root POC zoo (`cohost*.py`, `run*.sh`, `generate_bat.py`, `test_voice.py`) deleted 2026-05-20; enforced by `tests/repo/test_repo_scrub.py::test_retired_poc_files_stay_gone`. Design notes: `.planning/archive/2026-05-27-stale-v2-v3-research/`. `mascot.html` at root is **not** a POC — live overlay wired into `vibemix.runtime.ws_bus` + CI (`mascot-audit`). Keep it.

## UI Mocks *(i mockup)*

`mocks/` holds the design contracts referenced by UI phases. The current canonical references are `vibemix-rebuild-session.html` (the settled "Deck Speaks" app shell) and `vibemix-direction-final.html` (visual language); component-level mocks (e.g. `vibemix-library-ui.html`, `vibemix-pill-hover.html`) and the older `vibemix-app-ui.html` / `vibemix-cinematic-storyboard.html` live alongside. Treat these as the visual contract, lifted by the `frontend-enforcement` skill.
