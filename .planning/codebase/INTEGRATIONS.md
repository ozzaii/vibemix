# External Integrations

**Analysis Date:** 2026-06-08

vibemix's product design splits cleanly into ONE cloud brain (Gemini, for Sven's live reactions) and an otherwise local/on-device stack (CLAP embeddings, Chatterbox voice, CUE-DETR cues, Codex Viber). The only product-required cloud key is `GEMINI_API_KEY`. Everything below is tagged **[CLOUD]** or **[LOCAL/on-device]** and notes whether a key is required.

## APIs & External Services

**Live co-host brain — [CLOUD], key REQUIRED:**
- **Google Gemini** (`google-genai` 2.0.1) — Sven's live reaction-planning brain; the ONLY cloud model in the product path. "Only Gemini sees the listener" on the LiveKit pipeline.
  - SDK/Client: `google-genai`; live wiring `src/vibemix/agent/dj_cohost.py`, config `src/vibemix/agent/config.py`.
  - Model resolution: `src/vibemix/llm/model_router.py` → `_router_config.py` (`live_coach` = `gemini-3.5-flash` STANDARD tier). NO model literal outside that one allowlisted file.
  - Auth: `GEMINI_API_KEY` (repo-root `.env`). Direct-mode live co-host hard-requires it; voice goes silent (honest reason, no fallback) when the key is exhausted/absent.
  - Cost lane routes: `debrief`, `library_auto_tag`, `embedding` (legacy migration only) → FLEX tier.

**LiveKit pipeline — [CLOUD transport / local agent runtime], no separate key:**
- **LiveKit Agents** (`livekit` 1.1.8, `livekit-agents` 1.5.14, `livekit-plugins-google` 1.5.14) — the realtime co-host pipeline (`RealtimeModel`/`AgentSession`). `livekit-plugins-google` is used as the **Gemini LLM leaf only** (`src/vibemix/agent/_livekit_google_slim.py`); the STT/TTS leaves are explicitly excluded from the frozen bundle.
  - Ships a native FFI lib `liblivekit_ffi.dylib` (collected by `vibemix-core.macos.spec`).
  - Runtime requires `livekit.agents.cli` (NOT excludable — `agent_session.py::start()` imports it).

**OpenRouter live-brain route — [CLOUD], key for that mode:**
- **OpenRouter** — alternate live-brain path `live_coach_openrouter` → `google/gemini-3.5-flash:nitro`, consumed through `livekit-plugins-openai` (transitive via `livekit-agents`; spec collects `livekit.plugins.openai`). Client `src/vibemix/agent/openrouter_llm.py`. Recently activated (commit `2ba8f6d2` "activate OpenRouter live brain").
  - Auth: `OPENROUTER_API_KEY` (`.env`). Not the product default — do NOT treat OpenRouter as a speech provider.

**Bravoh keyless proxy — [CLOUD], JWT (no end-user Gemini key):**
- **`api.altidus.world`** (Bravoh prod, AWS) — the BYO-key alternative: a JWT-gated Gemini passthrough with per-client rate limit + cost caps, so the shipped binary never embeds a raw Gemini key.
  - Client: `src/vibemix/agent/proxy_client.py`; JWT cache `src/vibemix/agent/jwt_cache.py`; per-install id `src/vibemix/agent/install_uuid.py`.
  - Auth/config: `VIBEMIX_PROXY_BASE_URL`, `VIBEMIX_PROXY_JWT`, `VIBEMIX_CLIENT_VERSION`; `/register` issues the JWT. NOTE: proxy mode resolves speech to LOCAL Chatterbox (proxy is brain-only, no cloud TTS).

**Viber set-prep agent — [LOCAL CLI subprocess], BYO ChatGPT-sub:**
- **Codex CLI** — the product Viber backend (library chat / curate / build-set). Reached via `codex exec` subprocess + an MCP STDIO server, NOT a cloud API we call directly.
  - MCP server: `src/vibemix/library/mcp_server.py` (FastMCP, `mcp` 1.27.1) exposes 3 grounded tools (`search_vibe` / `get_track_features` / `create_playlist`). Driver: `src/vibemix/library/codex_curate.py`, shared core `src/vibemix/library/toolset.py`.
  - Auth/config: `codex login` (BYO ChatGPT subscription, provider `openai-codex`) + `VIBEMIX_CODEX_ALLOW_SHELL=1`. Codex binary is NOT bundled; `codex_curate.py` searches common dirs and honors `VIBEMIX_CODEX_BIN` / `VIBEMIX_NODE_BIN` (Finder-launched apps miss shell PATH). Do NOT reintroduce a Gemini Viber fallback.

**Optional MCP music surfaces — [LOCAL/external], flagged off:**
- **Rekordbox MCP** — `VIBEMIX_REKORDBOX_MCP_ENABLED` + `_COMMAND`/`_ARGS`/`_CWD` (external MCP server for live Rekordbox).
- **Nuclear MCP** — `VIBEMIX_NUCLEAR_MCP_ENABLED` + `_URL` (arms-length over the user's own Nuclear player MCP; post-launch Viber spike only — AGPL/ToS gated).

## Data Storage

**Databases (all LOCAL under `~/.cache/vibemix/`):**
- `library-clap.db` — sqlite-vec CLAP vectors (512-dim). Client: `sqlite-vec` 0.1.9 (macOS native ext / Windows numpy fallback, bit-identical top-K parity).
- `embeddings.db` — CLAP-tagged cache rows.
- `memory.db` — copilot recall store (sqlite-vec); gated behind `VIBEMIX_RECALL_ENABLED` (default OFF).
- `library.pkl` — track-title cache. `library-clap_centroid.npy` — cached query centroid (auto-recomputed on store change). Historical Gemini `library.db` may exist — do not clobber on CLAP re-embed.
- **Test gotcha:** library/rekordbox tests MUST monkeypatch `RekordboxLibrary.CACHE_PATH` to a tmp dir or they overwrite the real `library.pkl`.

**Model caches (LOCAL, optional download):**
- CLAP ONNX: `~/.cache/vibemix/clap-onnx/` (or `VIBEMIX_CLAP_ONNX_DIR`).
- CUE-DETR ONNX: `~/.cache/vibemix/cue-detr-onnx/cuedetr.fp32.onnx` (or `VIBEMIX_CUE_ONNX_PATH`).
- Chatterbox voice model + reference clip (mlx-audio, bundled separately by `scripts/dist/chatterbox_bundle.py`).
- Downloader/status: `uv run python -m vibemix library models [--install clap|cue|all]`.

**File Storage:**
- Local filesystem only. App data root `~/Library/Application Support/vibemix/` (macOS) / `%APPDATA%\vibemix\` (Windows). Session recordings under `<appdata>/vibemix/recordings/` (exposed read-only to the webview via Tauri `asset://` protocol, scope-locked).
- Per-session structured events: `events.jsonl`.

**Caching:**
- Content-hash embed cache (resumable folder embed). sqlite-vec vector cache. JWT cache (`jwt_cache.py`).

## On-Device AI Models

**CLAP embeddings — [LOCAL/on-device], NO key:**
- The product similarity / library / search / curate engine. Model `Xenova/larger_clap_music_and_speech` (non-fusion), 512-dim, deterministic 10s-chunk mean-pool, mean-centered (anisotropy fix, query-side only).
- Engine: `src/vibemix/library/clap_engine.py` (`onnx` backend default = `onnxruntime` + `tokenizers` + local mel/tokenizer; torch reference backend for validation only). Decode via PyAV/FFmpeg + numpy (no librosa/scipy in the ship path).
- Config: `VIBEMIX_CLAP_ONNX_DIR`, `VIBEMIX_CLAP_BACKEND`, `VIBEMIX_CLAP_NO_AUTODOWNLOAD`. Extra: `[clap]` / `[ai-local]`.

**Chatterbox-Turbo voice (Sven's co-host voice) — [LOCAL/on-device], NO key, Apple-Silicon-only:**
- The product co-host voice. `mlx-audio` `chatterbox-turbo-8bit` on Apple GPU — zero-shot voice clone from a reference clip, paralinguistic tags (`[laugh]`/`[gasp]`/`[sigh]`) at temp 0.4, one contiguous PCM segment.
- Engine: `src/vibemix/agent/chatterbox_tts.py` (LiveKit `TTS` provider with injectable `ChatterboxEngine` seam); chain `src/vibemix/agent/tts_chain.py`. Selected by `VIBEMIX_TTS_ENGINE=chatterbox` (default). `mlx-audio` is lazy-imported, NEVER a base dep; absent engine/clip → start voiceless with an honest reason (NO cloud fallback).
- Config: `VIBEMIX_CHATTERBOX_MODEL`/`_MODEL_REVISION`/`_REF`/`_STREAM`/`_TEMP`/`_MAX_TOKENS`/`_START_WARMUP_TIMEOUT_S`/`_LIVE_CACHE_ONLY`/`_PCM_CACHE`. Extra: `[tts-local]` / `[ai-local]` (darwin + arm64 marker).
- **Doc-drift note:** `CLAUDE.md` and several handoffs call the voice "MOSS-TTS-Nano"; the code/dependency ground truth (`pyproject.toml` `tts-local`, the macOS spec, and `src/vibemix/agent/chatterbox_tts.py`) is **Chatterbox-Turbo via mlx-audio**. Treat Chatterbox as authoritative. Cartesia/OpenRouter/cloud TTS are RETIRED from the product speech path.

**CUE-DETR hot-cue detection — [LOCAL/on-device], NO key:**
- Hot-cue placement model (`cuedetr.fp32.onnx`, `onnxruntime`). Log-mel frontend via `src/vibemix/library/audio_decode.py`; path resolution `src/vibemix/library/cache_paths.py`.
- Config: `VIBEMIX_CUE_ONNX_PATH`/`_URL`/`_SHA256`/`_SIZE`. Extra: `[cue]` / `[ai-local]`. (MIT weights need an offline torch→ONNX export; no first-party ONNX yet.)

## Authentication & Identity

**Co-host brain auth:**
- BYO key: `GEMINI_API_KEY` in `.env` (direct mode).
- Keyless: Bravoh proxy issues a JWT (`pyjwt` 2.12.1) per install (`install_uuid.py`), cached (`jwt_cache.py`), `VIBEMIX_PROXY_JWT`.
- OS keychain via `keyring` 25.7.0 for the BYO-key path.

**Viber auth:** `codex login` (BYO ChatGPT subscription), gated by `VIBEMIX_CODEX_ALLOW_SHELL=1`.

**Telegram auth:** numeric chat-id allow-list `VIBEMIX_TELEGRAM_ALLOWED_CHATS` (fail-closed) — the v1 auth.

## Monitoring & Observability

**AI observability — [CLOUD], dev/observe-mode, gated:**
- **Respan / KeywordsAI** (LLM obs/evals) — `RESPAN_API_KEY`, enabled via `VIBEMIX_AI_OBSERVABILITY` (and `_IN_TESTS`). Observe-mode (manual TEXT-only spans on the live path), NOT a gateway; cloud-only, account needs provider creds.

**Error Tracking / Logs:**
- Python: startup `-> ...` lines; bracket-tagged stderr errors (`[coach err]`); AI reactions broadcast over the ws bus (`transcript_delta`), not stderr; structured per-session events to `events.jsonl`.
- Rust shell: `tracing` 0.1 + `file-rotate` 0.8 (10 MB × 5 rotation).

## CI/CD & Deployment

**Hosting / distribution:**
- Desktop app (no server backend for vibemix itself). macOS `.dmg` (signed + notarized + stapled, arch-specific arm64 + x86_64 sidecars bundled). Windows build via SignPath.
- The Bravoh proxy + updater manifests are hosted on `api.altidus.world` (PM2 backend `bravoh-clean-backend`).

**CI Pipeline:**
- GitHub Actions (`.github/`, `release.yml`) — gates: ruff, pytest, vitest, mascot-audit, no-hardcoded-model grep, IPC schema, updater-key-rotation. Security skills present under `.agents/skills/` (gitleaks secret-scan, semgrep SAST, snyk SCA, code-signing).
- Critical path is EXTERNAL: Apple notarization + SignPath approvals (engineering parallelizes around them).

**Updater — [CLOUD], minisign-signed:**
- `tauri-plugin-updater` 2.10. Endpoint `https://api.altidus.world/vibemix/updates/{{target}}/{{arch}}/{{current_version}}`, minisign pubkey in `tauri.conf.json5`. `dialog: true` (built-in prompt), gated by `update_check_on_launch`.

## Environment Configuration

**Required env vars (product path):**
- `GEMINI_API_KEY` — Sven live brain (direct mode). The ONLY product-required cloud key.

**Optional / mode-specific:**
- `OPENROUTER_API_KEY` (OpenRouter live-brain route), `VIBEMIX_PROXY_JWT`/`_BASE_URL` (keyless proxy mode), `VIBEMIX_TELEGRAM_TOKEN`/`_ALLOWED_CHATS` (Telegram), `RESPAN_API_KEY` (observability).
- Local features (CLAP search, ingest, chat, curate, build-set, Chatterbox voice, CUE) require NO key — just the optional model downloads + `--extra ai-local`.

**Secrets location:**
- Repo-root `.env` (git-ignored; loaded by `python-dotenv`). OS keychain (`keyring`) for BYO key. Updater private key at `~/.tauri/vibemix_updater.key` (NEVER committed); Windows signing via SignPath; macOS Dev-ID via Apple keychain.
- Dev `.env` also carries `CARTESIA_API_KEY`, `COMPOSIO_API_KEY`, `TAVILY_API_KEY` (experimental/retired surfaces, not product-path).
- The PyInstaller specs exclude `*.env`/`*credentials*`/`*.key`/`*.pem` from bundled data (leak gate).

## System Dependencies (not pip)

**macOS — [LOCAL]:**
- BlackHole 2ch (virtual audio device; `brew install blackhole-2ch`) — the master-output capture route.
- `nowplaying-cli` (`brew install nowplaying-cli`) — NowPlaying track metadata (`src/vibemix/platform/_track_macos.py`; the macOS spec HARD-fails the build if absent, bundles it from `/opt/homebrew/bin` or `/usr/local/bin`).
- ScreenCaptureKit / Quartz / Cocoa / AVFoundation / CoreAudio via pyobjc frameworks — screen crop, mic-permission probe, audio I/O.
- Pioneer DDJ-FLX4 (optional, USB MIDI; graceful fallback).

**Windows — [LOCAL]:**
- WASAPI loopback via `pyaudiowpatch` (no BlackHole); `pywin32` (EnumWindows), `winsdk` (SMTC track metadata), `mss` (screen capture). See `docs/windows-setup.md`.

## Webhooks & Callbacks

**Incoming:**
- Telegram long-poll bot (NOT a webhook): `src/vibemix/library/telegram_bridge.py` (optional `telegram` extra, lazy-imports `python-telegram-bot` 22.7). Auth = `VIBEMIX_TELEGRAM_TOKEN` (BotFather) + `VIBEMIX_TELEGRAM_ALLOWED_CHATS` (fail-closed allow-list). Outbound messages path-scrubbed; each request runs the local Codex Viber under a wall-clock timeout.
- Local WS bus `127.0.0.1:8765` (single listener — cardinal Invariant #4; debrief `8766`) — Rust shell ↔ Python sidecar IPC. NOT externally reachable.

**Outgoing:**
- Gemini API calls (live brain), OpenRouter (optional route), Bravoh proxy `/register` + passthrough, Tauri updater check, Rekordbox `collection.xml` read (local file, `pyrekordbox` 0.4.4, XML-only — SQLCipher path unused). No other outbound network in the product path.

---

*Integration audit: 2026-06-08*
