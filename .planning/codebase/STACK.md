# Technology Stack

**Analysis Date:** 2026-06-08

vibemix is a three-language packaged desktop app: a Python sidecar (the live co-host engine), a Rust/Tauri parent shell, and a TypeScript/Vite webview frontend, plus a build-step-free vanilla-JS canvas overlay. Authoritative pins live in `pyproject.toml` + `uv.lock` (Python), `tauri/ui/package.json` + `tauri/ui/package-lock.json` (frontend), and `tauri/src-tauri/Cargo.toml` + `Cargo.lock` (Rust). Versions below are the RESOLVED pins from `uv.lock` where the lockfile is authoritative, else the declared floor.

## Languages

**Primary:**
- Python 3.12 (`requires-python = ">=3.12,<3.13"`, `.python-version` = `3.12`) — all app/engine logic under `src/vibemix/`. Entry point `src/vibemix/__main__.py` (`python -m vibemix`).
- TypeScript 5.7 — Tauri webview surfaces under `tauri/ui/src/` (session, wizard, debrief, library, Viber). `tsconfig.json`; build = `tsc --noEmit && vite build`.
- Rust (edition 2021, `rust-version = "1.77"`) — Tauri parent process / sidecar lifecycle under `tauri/src-tauri/src/` (entry `main.rs`).

**Secondary:**
- Vanilla JS / HTML / CSS — `mascot.html` at repo root (Canvas 2D overlay, NO build step, wired to `vibemix.runtime.ws_bus`; CI gate `mascot-audit`). A separate Three.js GLB pipeline lives inside `tauri/ui/` for the in-app organism.

## Runtime

**Environment:**
- CPython 3.12.x (the `.venv/` is 3.12). Hard-pinned `<3.13` — do not assume 3.13 compatibility.
- Tauri 2.x desktop runtime (macOS WebKit / Windows WebView2). Min macOS 12.3 (`tauri.conf.json5` `minimumSystemVersion`). Linux explicitly excluded.
- Apple Silicon GPU (MLX) for the local Chatterbox voice path; falls back voiceless (never to cloud) when absent.

**Package Managers:**
- `uv` — Python runner + lockfile tool. Lockfile: `uv.lock` (present, authoritative). The uv venv has NO `pip` — install extras with `uv pip install`.
- `npm` — frontend. Lockfile: `tauri/ui/package-lock.json` (present).
- `cargo` — Rust shell. Lockfile: `tauri/src-tauri/Cargo.lock` (present).

## Frameworks

**Core:**
- `livekit` 1.1.8 + `livekit-agents` 1.5.14 + `livekit-plugins-google` 1.5.14 — the live co-host (Sven) pipeline. `RealtimeModel` / `AgentSession` path; ships a native FFI lib (`liblivekit_ffi.dylib`) the PyInstaller spec explicitly collects. `livekit-plugins-openai` rides in transitively via `livekit-agents` (the spec collects `livekit.plugins.openai`) and backs the OpenRouter live-brain route.
- `google-genai` 2.0.1 — Sven's Gemini reaction-planning brain (cloud). Resolved via `model_router`, never inlined.
- Tauri 2.11 — Rust shell framework (`tauri/src-tauri/Cargo.toml`), features `macos-private-api`, `config-json5`, `tray-icon`, `image-png`, `protocol-asset`, `devtools`.
- `three` 0.170 — the only frontend runtime dependency (`tauri/ui/package.json`); the in-app particle organism / mascot WebGL surface.

**Testing:**
- `pytest` 8.x — authoritative Python test runner (`tests/`, `[tool.pytest.ini_options]`). Markers: `macos_audio`, `windows_only`, `integration`, `slow`, `parity`, `cli`, `e2e`, `network`, `flaky`, `real_model_status` (default run = `-m 'not network'`).
- `pytest-mock` 3.15, `vcrpy` 8.x + `pytest-recording` 0.13 — Gemini API calls cached to cassettes (`tests/eval/cassettes/`) so PR CI runs at $0.
- `vitest` 4.1 — frontend unit tests (`vitest run`, ~886 tests). Config `tauri/ui/vitest.config.ts`; `jsdom` 29 DOM env.
- `@playwright/test` 1.50 — e2e suites (`test:e2e:learn|pill|mascot|visual`); `pixelmatch` 7 + `axe-core` 4.11 for visual/a11y gates.

**Build/Dev:**
- `hatchling` — Python wheel build backend (`[tool.hatch.build.targets.wheel]` packages `src/vibemix`); package data (JSON profiles, exemplar `*.wav`) ships automatically.
- `pyinstaller` 6.20.0 (dev dep) — freezes the sidecar into `--onedir` bundles. Specs: `vibemix-core.macos.spec`, `vibemix-core.windows.spec`. NEVER `--onefile`/`upx`/`console=True` (AV false-positives + headless spawn). Auto-bundles every `vibemix.*` submodule via `collect_submodules`; a new third-party dep MUST be added to the spec.
- `vite` 6 + `vite-plugin-static-copy` 2.2 — frontend bundler/dev server (`tauri/ui/`, dev port 1420).
- `cargo tauri build` — packages `app` + `dmg` (`tauri.conf.json5` `bundle.targets`). Release profile: `lto`, `panic = "abort"`, `strip`, `opt-level = "s"`, `codegen-units = 1`.
- `@gltf-transform/cli` 4 + `gltf-pipeline` 4 — GLB asset pipeline (mascot/organism mesh, Draco compression).
- `json-schema-to-typescript` 15 + `ajv` 8.20 + `ajv-formats` 3 — IPC contract codegen/validation (`npm run codegen:ipc` regenerates the PRE-COMPILED `validator.generated.mjs` from `src/ipc/messages.schema.json`).

**Lint/Format:**
- `ruff` 0.7 (dev) — `target-version = "py312"`, `line-length = 100`, `select = ["E4","E7","E9","F","B","I","UP","RUF"]` (E501/RUF001-003 ignored for Turkish/DJ-math text). `quote-style = "double"`.

## Key Dependencies

**Critical (always installed, `pyproject.toml` base `dependencies`):**
- `google-genai` 2.0.1 — Sven live reaction brain (cloud, needs `GEMINI_API_KEY`).
- `livekit` 1.1.8 / `livekit-agents` 1.5.14 / `livekit-plugins-google` 1.5.14 — live pipeline.
- `numpy` 2.4.4 — audio DSP, model decode, 48k→16k resample.
- `av` 17.0.1 (PyAV/FFmpeg) — direct runtime dep for CLAP/CUE decode + debrief MP3 encode (NOT relied on transitively).
- `sounddevice` 0.5.5 — CoreAudio (macOS) / WASAPI I/O.
- `mido` 1.3.3 + `python-rtmidi` 1.5.8 — MIDI controller decode (blocking daemon thread).
- `sqlite-vec` 0.1.9 — local vector store (library vibe-search v2.1 + memory v6.0); loads its `vec0` native extension at runtime (PyInstaller bundles it next to `sqlite_vec/__init__.py`).
- `mcp` 1.27.1 (FastMCP) — STDIO MCP server exposing the 3 grounded library tools to the Codex Viber CLI. Only the optional curation agent imports it; the live co-host never does.
- `httpx` 0.28.1 — HTTP (proxy client, downloads).
- `keyring` 25.7.0 — OS keychain (BYO-key path).
- `pyjwt` 2.12.1 — JWT for the Bravoh keyless proxy.
- `jsonschema` 4.26.0 — validates `ipc.*` messages at the Python↔TS boundary (Draft-07, validation-only — pydantic is banned).
- `websockets` 15.0.1 — the `ws_bus` socket (`127.0.0.1:8765`; debrief `8766`).
- `watchfiles` 1.1.1 — library/catalog freshness watcher (degrades to polling in frozen builds).
- `python-dotenv` 1.2.2 — loads repo-root `.env`.
- `python-statemachine` 3.1.2 — Learn lesson runtime engine (MIT, pure-Python, no transitive deps).
- `pillow` 12.2.0 — screen JPEG capture + CUE-DETR image preprocess.

**Library import (Rekordbox), base deps with the SQLCipher path excluded:**
- `pyrekordbox` 0.4.4 (installed `--no-deps`) — `collection.xml` XML import ONLY; SQLCipher path explicitly UNUSED. `sqlcipher3-wheels` is overridden out via a never-matching marker in `[tool.uv].override-dependencies` (saves ~3.2 MB, excludes an unexecuted C-extension). Transitives co-declared explicitly: `bidict==0.23.1`, `construct==2.10.70`, `SQLAlchemy==2.0.49`, `psutil==7.2.2`, `python-dateutil==2.9.0.post0`.

**Platform-gated base deps (markers in `pyproject.toml`):**
- macOS (`sys_platform == 'darwin'`): `pyobjc-core`, `pyobjc-framework-Cocoa`, `pyobjc-framework-Quartz`, `pyobjc-framework-ScreenCaptureKit`, `pyobjc-framework-AVFoundation` (all `>=12.1`) — window crop, ScreenCaptureKit capture, mic-permission probe.
- Windows (`sys_platform == 'win32'`): `pyaudiowpatch>=0.2.12` (WASAPI loopback), `pywin32>=308` (EnumWindows/SMTC), `winsdk>=1.0.0b10` (SMTC reads, beta-pinned), `mss>=10.2.0` (screen capture).

**Optional extras (`[project.optional-dependencies]` — installer path uses `ai-local`):**
- `clap` = `onnxruntime>=1.20` + `tokenizers>=0.22` — CLAP ONNX embedder (the product similarity engine).
- `cue` = `onnxruntime>=1.20` — CUE-DETR hot-cue detector.
- `tts-local` = `mlx-audio>=0.3` (darwin + arm64 only) — local Chatterbox co-host voice.
- `ai-local` = `onnxruntime` + `tokenizers` + `mlx-audio` (darwin arm64) — the full local-AI install; the app/installer path. `uv run --extra ai-local python -m vibemix`. Plain `uv run` PRUNES `onnxruntime`/`tokenizers` → local features silently fall back.
- `telegram` = `python-telegram-bot>=21` (resolved 22.7) — optional Viber mobile bridge.
- `serato` = `mutagen>=1.47` (resolved 1.47.0) — Serato file-tag cue export. **GPL-2.0-or-later**: runtime-import only, lazy, NEVER vendored.
- Resolved local-AI pins (`uv.lock`): `onnxruntime` 1.26.0, `tokenizers` 0.22.2, `mlx-audio` 0.4.3.

**Frontend deps (`tauri/ui/package.json`):**
- Runtime: `three` 0.170 (only runtime dep).
- Dev/build: `@tauri-apps/api` 2.11 + plugins `plugin-dialog` 2.7.1 / `plugin-shell` 2.3 / `plugin-store` 2.4, `typescript` 5.7, `vite` 6, `vitest` 4.1, `playwright` 1.50, `jsdom` 29, `ajv` 8.20 + `ajv-formats` 3, `json-schema-to-typescript` 15, `@gltf-transform/*` 4, `gltf-pipeline` 4, `pixelmatch` 7, `axe-core` 4.11, `@types/three` / `@types/node`. `overrides: { "tmp": "^0.2.6" }`.

**Rust deps (`tauri/src-tauri/Cargo.toml`):**
- `tauri` 2.11 + plugins: `tauri-plugin-shell` 2.3 (sidecar spawn), `-store` 2.4, `-fs` 2.5, `-dialog` 2.7.1, `-positioner` 2.3, `-updater` 2.10, `-process` 2.3, `-global-shortcut` 2.3 (push-to-mute).
- Async/WS: `tokio` 1 (full), `tokio-tungstenite` 0.29, `futures-util` 0.3 (Rust client → Python `ws_bus`).
- Serde: `serde` 1 (derive), `serde_json` 1.
- Logging: `tracing` 0.1, `file-rotate` 0.8 (10 MB × 5).
- Misc: `dirs-next` 2, `libc` 0.2 (POSIX `kill(2)` for the bundled-sidecar watchdog).
- macOS-only (`cfg(target_os = "macos")`): `core-graphics` 0.24, `core-foundation` 0.10, `accessibility-sys` 0.1 (djay AX overlay), `tauri-plugin-macos-permissions` 2.3.0 (TCC), `window-vibrancy` 0.6.0 (Pill HUD NSVisualEffectView).

## Configuration

**Environment:**
- Repo-root `.env` (present; loaded via `python-dotenv`). Holds `GEMINI_API_KEY` (the ONLY product-required key — Sven's live brain). Other key NAMES present in the dev `.env` (values never read): `OPENROUTER_API_KEY`, `CARTESIA_API_KEY`, `RESPAN_API_KEY`, `COMPOSIO_API_KEY`, `TAVILY_API_KEY` — dev/experimental surfaces, not product-path requirements. Library search/ingest/chat/curate/build-set are local/keyless.
- **Model selection is config-driven via `vibemix.llm.model_router` — zero hardcoded model literals in `src/vibemix/`.** The ONLY allowlisted file with model ids is `src/vibemix/llm/_router_config.py` (`_ROUTES`). CI grep gate: `scripts/release/check_no_hardcoded_model.sh`. Live brain route `live_coach` → `gemini-3.5-flash` (swap is a one-line router edit).
- ~95 `VIBEMIX_*` runtime flags (grep `src/vibemix/`). High-signal ones:
  - Voice/TTS: `VIBEMIX_TTS_ENGINE` (default `chatterbox`), `VIBEMIX_CHATTERBOX_MODEL`/`_REF`/`_STREAM`/`_START_WARMUP_TIMEOUT_S`, `VIBEMIX_LOCAL_TTS`, `VIBEMIX_VOICE_GAIN`, `VIBEMIX_SYSTEM_TTS_FALLBACK`.
  - Models: `VIBEMIX_CLAP_ONNX_DIR`, `VIBEMIX_CLAP_BACKEND`, `VIBEMIX_CUE_ONNX_PATH`/`_URL`/`_SHA256`, `VIBEMIX_CACHE_DIR`, `VIBEMIX_MODEL_PROGRESS`.
  - Brain/mode: `VIBEMIX_LLM_MODE`, `VIBEMIX_MODE`, `VIBEMIX_MOOD`, `VIBEMIX_SKILL_LEVEL`, `VIBEMIX_GENRE_PROFILE`, `VIBEMIX_ANTI_SLOP`.
  - Proxy: `VIBEMIX_PROXY_BASE_URL`, `VIBEMIX_PROXY_JWT`, `VIBEMIX_CLIENT_VERSION`.
  - Viber/Codex: `VIBEMIX_CODEX_ALLOW_SHELL`, `VIBEMIX_CODEX_BIN`, `VIBEMIX_NODE_BIN`.
  - Integrations: `VIBEMIX_TELEGRAM_TOKEN`/`_ALLOWED_CHATS`, `VIBEMIX_NUCLEAR_MCP_*`, `VIBEMIX_REKORDBOX_MCP_*`, `VIBEMIX_AI_OBSERVABILITY` (Respan).
  - Audio devices: `VIBEMIX_INPUT_DEVICE`/`_OUTPUT_DEVICE`/`_MIC_DEVICE`, `VIBEMIX_INPUT_CHANNELS`, `VIBEMIX_MASTER_AUDIO_CHANNELS`, `VIBEMIX_ENABLE_MIC`.
  - Debug/QA: `VIBEMIX_DROP_DEBUG`, `VIBEMIX_TRACE`, `VIBEMIX_REPLAY_SESSION`, `VIBEMIX_SOAK_SECONDS`, `VIBEMIX_SVEN_PROBE_*`.
- Packaged `.app` launched via `open -a` does NOT inherit `VIBEMIX_*` flags (launchd strips env) — launch the binary directly to pass flags.

**Build:**
- `pyproject.toml` + `uv.lock` — Python deps/build/test/lint config (single source).
- `tauri/src-tauri/tauri.conf.json5` — bundle (`app`+`dmg`), identifier `world.bravoh.vibemix` (LOCKED), CSP, updater endpoint, sidecar resource dirs (3 arch triples), min macOS 12.3, hardened runtime + `entitlements.plist`.
- `tauri/src-tauri/Cargo.toml` — Rust crate + release profile.
- `tauri/ui/package.json` / `vite.config.ts` / `vitest.config.ts` / `tsconfig.json` — frontend.
- `vibemix-core.{macos,windows}.spec` — PyInstaller freeze (hidden imports, native-lib collection, secret-leak excludes, `nowplaying-cli` bundling).

## Platform Requirements

**Development:**
- macOS (Apple Silicon primary): `uv`, BlackHole 2ch (`brew install blackhole-2ch`), `nowplaying-cli` (`brew install nowplaying-cli` — the macos spec HARD-fails the build if absent), a DJ app routed through BlackHole, optional Pioneer DDJ-FLX4 over USB. Node/npm + Rust toolchain for the shell.
- Windows: WASAPI loopback (no BlackHole), MSVC toolchain. See `docs/windows-setup.md`.

**Production:**
- Distributed as a signed/notarized macOS `.dmg` (`dist/vibemix-0.0.1.dmg`, arm64, Francesco Dev-ID) and a Windows build (SignPath path). Bundle ID `world.bravoh.vibemix`. Tauri auto-updater pulls signed deltas from `https://api.altidus.world/vibemix/updates/...` (minisign-verified). One instance only (socket `127.0.0.1:8765`).

---

*Stack analysis: 2026-06-08*
