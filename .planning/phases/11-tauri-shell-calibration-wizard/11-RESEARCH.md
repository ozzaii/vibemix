# Phase 11: Tauri Shell + Calibration Wizard — Research

**Researched:** 2026-05-12
**Domain:** Tauri 2.x desktop shell + PyInstaller `--onedir` sidecar + WebSocket IPC + first-run calibration wizard (vanilla TS UI)
**Confidence:** HIGH (Tauri sidecar pattern, PyInstaller flow, IPC mechanics, OS perm flows); MEDIUM (cross-platform schema-sync codegen tradeoffs); MEDIUM (exact crate selection for log rotation — multiple viable)

## Summary

Phase 11 is the **biggest remaining phase by surface area**: it stands up the Tauri 2.x Rust shell, ships the Python sidecar as a PyInstaller `--onedir` bundle wired through `externalBin`, fixes the IPC contract between Rust ↔ Python (WS bus on `127.0.0.1:8765`, JSON Schema source-of-truth), and builds the 3-step calibration wizard UI. All four pillars (Rust shell, sidecar packaging, IPC schema sync, wizard UX) need to land or the next 9 phases can't run on real distributed binaries.

The good news: **every single piece is mainstream, well-documented, and de-risked by existing project research** (`.planning/research/STACK.md`, `.planning/research/PITFALLS.md`). The wizard UX contract is already locked in `11-UI-SPEC.md`, and `11-CONTEXT.md` resolves every open product decision. This phase is mostly **integration work**, not novel engineering.

**Primary recommendation:** Build in 5 waves — (W0) repo scaffolding + IPC schema sync infrastructure (no Tauri yet) → (W1) PyInstaller `--onedir` build + sidecar entry verification → (W2) Tauri shell + sidecar lifecycle wired (no UI yet) → (W3) wizard UI screens (token system + components from `11-UI-SPEC.md`) → (W4) wizard flow logic + exit smoke test + crash banner + config persistence. Don't try to land it all in one swing.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Window chrome + DOM | Tauri Webview (vanilla TS) | — | UI surface; no React per CONTEXT |
| Sidecar process lifecycle (spawn/watchdog/restart/log) | Tauri Rust shell | — | OS-process ownership belongs to the shell, not the webview |
| Audio I/O + MIDI + screen probes | Python sidecar | — | `sounddevice` / `mido` / `mss` already there; no Rust audio dep |
| WS bus (telemetry + IPC commands) | Python sidecar (server) | Tauri Rust + JS (clients) | Existing `vibemix.runtime.ws_bus` is the single bus |
| First-run config persistence | Tauri Rust + JS (`tauri-plugin-store`) | — | OS app-data dir, owned by shell |
| Permission requests (Screen Recording / Mic) | Tauri Rust (deep-links) + Python sidecar (AVCaptureDevice probe) | — | Tauri opens System Settings; Python reports current state |
| BlackHole detection | Python sidecar (`sounddevice.query_devices`) | — | Existing Phase 2 path |
| 1kHz sine test | Python sidecar (gen + play + verify) | Tauri JS (UI state) | Python owns audio I/O |
| Controller probe (10s listen) | Python sidecar (`mido` event capture) | Tauri JS (countdown UI) | MIDI lives in sidecar |
| Exit-greeting smoke test | Python sidecar (LLM + TTS cascade) | Tauri JS (replay button) | Reuses Phase 4 cascade agent |
| Auto-update | Tauri Rust (`tauri-plugin-updater`) | — | Stubbed in Phase 11; signed in Phase 18 |
| Schema validation (build-time) | CI scripts (Python + Node) | — | Cross-language contract enforcement |

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| **ARCH-01** | Consolidate three POC variants into single shipping `vibemix` Python package — **Tauri shell aspect** | Q1 (externalBin spawning `python -m vibemix`), Q2 (PyInstaller `--onedir` of the package), Q5 (sidecar lifecycle ownership) |
| **DIST-05** | Tauri 2.x desktop shell wrapping the Python sidecar (10× smaller than Electron) | Q1 (tauri.conf.json5 layout), Q2 (PyInstaller bundle for `externalBin`), Q5 (lifecycle), Q12 (updater stub for Phase 18) |
| **UX-01** | Calibration wizard on first run — 3-step fast path: permissions → output device + sample-rate test → controller detect + smoke test | Q6 (OS perm flows), Q7 (device enumeration), Q8 (1kHz test), Q9 (config persistence), Q10 (BlackHole detect), `11-UI-SPEC.md` (visual + interaction contract) |
| **UX-11** | Status badges — LiveKit / Gemini / MIDI / screen visible failure indicators | Q4 (schema for `ipc.status.tick`), `11-UI-SPEC.md` §12 (Phase 11 = schema + minimal step checks; full live bar in Phase 12) |
</phase_requirements>

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Area 1 — IPC & Sidecar Architecture:**
- IPC protocol: Reuse `vibemix.runtime.ws_bus` on `127.0.0.1:8765` for Tauri ↔ Python. Tauri shell connects as a WS client; new message types prefixed `ipc.*` (e.g., `ipc.calibration.probe_audio`, `ipc.status.tick`). One bus = one failure mode; mascot.html proves the pattern.
- Crash recovery: Tauri shell owns sidecar lifecycle via `externalBin`. Exit-code watchdog with 3× automatic restart attempts, then surfaces "vibemix-core stopped — restart?" banner. Manual "Restart" button reuses the spawn path.
- Schema sync: Single source-of-truth JSON Schema at `tauri/ui/src/ipc/messages.schema.json`. Build-time CI gate: Python `ui_bus/messages.py` dataclass + TypeScript `messages.ts` types both validate against the schema (`scripts/check_ipc_schema.py`). Drift breaks CI.
- Sidecar logging: Tauri captures stdout/stderr, writes to rolling file under OS app-data dir (`~/Library/Application Support/vibemix/logs/sidecar.log` mac / `%LOCALAPPDATA%\vibemix\logs\sidecar.log` win). 10MB × 5 rotation. Last error line surfaces in the crash banner.

**Area 2 — Calibration Wizard UX Flow:**
- Step 1 (Permissions): OS-aware content, uniform "Step 1/3" header. macOS: Screen Recording deep-link + Microphone prompt. Windows: Microphone via standard runtime permission. Both OSes auto-advance when granted.
- Step 2 (Output device + sample-rate test): Auto-detect headphones shown as primary. Auto-play 1kHz sine 1.5s + "Did you hear it?" Yes / Retry. Programmatic guard (`assert_blackhole_rate` mac / `assert_wasapi_loopback_rate` win) runs in parallel; both audible + programmatic must pass.
- Step 3 (Controller probe): Detected controller name shown + "Press any pad or button" with live 10-second countdown. First MIDI event confirms. Timeout → "Skip — use generic mapping" registers generic fallback.
- Wizard exit: Plays one AI greeting in headphones using `prompts/matrix.py` Beginner/Hype template.

**Area 3 — First-run State & Window Picker:**
- Config file at OS app-config dir; schema `{first_run_completed, calibrated_at, output_device_id, controller_profile, target_dj_app_hint, target_window_id, blackhole_install_seen}`. Tauri reads/writes via `tauri-plugin-fs` / `tauri-plugin-store`.
- Window picker UX: DJ-app hint list first (djay Pro, Rekordbox, Serato, Traktor, VirtualDJ). Fall back to full enumeration with privacy warning. Non-DJ pick = warn + allow (logged to events.jsonl). Re-run wizard via Settings (Phase 12 surfaces button).

**Area 4 — BlackHole + Status Badges + Python Pin:**
- BlackHole detection: any device starting with `BlackHole` via `sounddevice.query_devices()`. Accept 2ch/16ch/64ch.
- BlackHole install: clickable button opens `https://existential.audio/blackhole` via `tauri-plugin-shell`. Wizard waits with "Once installed, click Recheck."
- Status badges (Phase 11 scope): Define IPC schema `ipc.status.tick` + minimal per-step green checkmarks. Full live-UI badge bar deferred to Phase 12.
- Python pin: `>=3.12,<3.13` (already in `pyproject.toml:10`). Phase 11 verifies PyInstaller builds against same.

### Claude's Discretion
- Exact Rust crate selection (sidecar spawn impl, log rotation, JSON schema validator).
- TypeScript / vanilla-JS choice inside `tauri/ui/` — default vanilla TS + Vite.
- Wizard step transition animations + token continuity from `mocks/vibemix-app-ui.html`.
- Asset directory: where wizard HTML/CSS/audio ship inside the bundle.

### Deferred Ideas (OUT OF SCOPE)
- Live UI badge bar (UX-11 visual surface — Phase 12).
- Recording retention controls (Phase 15).
- Auto-update wiring (Phase 18 signs the manifest; Phase 11 only stubs the plugin).
- Linux — out of scope per PROJECT.md.
- Reactive mascot integration (Phase 13 hooks into reserved corner).
- Per-controller learn-mode (post-v1).
</user_constraints>

---

## Project Constraints (from CLAUDE.md)

Directives the planner MUST honor (treat as locked decisions):

- **"POC = Reference, Devour It"** — `cohost.py` / `cohost_v2.py` / `cohost_lk.py` / `cohost_v4.py` are trusted intuition. Don't preserve them as legacy; lift IP into new shape.
- **`cohost_v4.py` is the canonical baseline** (per `MEMORY.md`) — has OpenRouter-primary TTS chain, tuned event cooldowns from real DJ session 2026-05-11, "trust the audio" anti-hallucination rule, BlackHole 48kHz format requirement.
- **No pydantic in Python sidecar** — Phase 6 convention. Hand-validated JSON loaders + `jsonschema` (validation-only, no model gen).
- **GSD workflow enforcement** — all repo edits go through GSD commands.
- **Project skill `frontend-enforcement`** — loaded by planner/executor/ui-checker. Hard rules: 20/80 amber-on-charcoal, textured material feel, no Inter/Roboto, retro-futurist hardware vocabulary, Workbench + DM Mono + DSEG7 typography. Already lifted in `11-UI-SPEC.md`.
- **macOS-only deps are already isolated** behind `vibemix/platform/` Protocol firewall (Phase 1). Tauri shell is a new process — does **not** import vibemix. Only the IPC schema is shared.
- **Python pinned 3.12.x** in `pyproject.toml:10` — PyInstaller targets this. Don't bump.
- **Apache 2.0 + DCO** — license obligations for every new Rust crate + TS dep (compatible licenses only).
- **`./run_v4.sh` must keep working** throughout Phase 11 — POC files diff-untouched (carried convention from Phases 2-10).

---

## Standard Stack

### Core (Rust shell)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `tauri` | **2.9.x** | Desktop shell + Webview wrapper | [VERIFIED: Context7 `/websites/v2_tauri_app`] Tauri 2 is the current stable line; 2.9 ships with `tauri-plugin-store` improvements + `data_directory` config |
| `tauri-plugin-shell` | **2.x** | Spawn the Python sidecar via `externalBin`; open `https://existential.audio/blackhole` in default browser | [VERIFIED: Tauri docs §sidecar] The canonical pattern. `app.shell().sidecar("vibemix-core")` returns `(rx, child)` |
| `tauri-plugin-store` | **2.x** | Read/write `config.json` in OS app-data dir | [VERIFIED: Context7] `Store.load('config.json')` with `autoSave: 500` debounce + `defaults` |
| `tauri-plugin-fs` | **2.x** | Read sidecar log file for crash-banner "last error line" | [VERIFIED: Tauri docs] Use `BaseDirectory.AppLocalData` for log path |
| `tauri-plugin-updater` | **2.x** | **Stub only** in Phase 11 — wired but no real endpoints. Phase 18 fills `pubkey` + `endpoints` | [VERIFIED: Tauri docs §updater] `tauri_plugin_updater::Builder::new().build()` in setup; `createUpdaterArtifacts: true` in bundle config |
| `tauri-plugin-positioner` | **2.x** | Centre wizard window on primary display | [CITED: `11-UI-SPEC.md` line 42] |
| `tauri-plugin-process` | **2.x** | `relaunch()` after updater install (Phase 18 use; stubbed in 11) | [VERIFIED: Tauri docs §updater] |
| `tokio` | **1.x** | Async runtime (Tauri pulls it in) | [VERIFIED: standard] |
| `tokio-tungstenite` | **0.28.x** | WebSocket client → connect to Python WS bus on `127.0.0.1:8765` | [VERIFIED: Context7 `/snapview/tokio-tungstenite`] The canonical async WS client for Tokio; mature, low-dep |
| `serde` + `serde_json` | **1.x** | IPC message (de)serialization | [VERIFIED: standard] |
| `tracing` + `tracing-appender` | **0.1** / **0.2** | Sidecar stdout/stderr capture → rolling file (10MB × 5) | [VERIFIED: docs.rs] `RollingFileAppender::builder().rotation(Rotation::HOURLY).max_log_files(5)` — though for size-based rotation `file-rotate` crate is the alternative |

### Core (Python sidecar)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `pyinstaller` | **6.20.0** | Build `vibemix-core` sidecar binary (`--onedir`) | [CITED: `.planning/research/STACK.md`] 6.14+ has stable numpy 2.x hooks; 6.20 is current stable |
| `jsonschema` | **4.23.x** | Validate `ui_bus/messages.py` dataclass instances against `messages.schema.json` at build time | [VERIFIED: PyPI] Lightweight; no model-generation (no pydantic). Pure-Python validation only. |
| (existing) `websockets` | **16.0** | WS bus server (already there; Phase 4) | [CITED: CLAUDE.md] |

### Core (TypeScript UI)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `typescript` | **5.7.x** | Type checking | [VERIFIED: npm] |
| `vite` | **6.x** | Dev server + production build (no React) | [VERIFIED: tauri docs] Tauri 2 starter template default |
| `@tauri-apps/api` | **2.x** | JS bindings for Tauri commands (`invoke`, `Emitter`) | [VERIFIED: Tauri docs] |
| `@tauri-apps/plugin-shell` | **2.x** | JS side of shell plugin (open URL, sidecar args) | [VERIFIED: Tauri docs] |
| `@tauri-apps/plugin-store` | **2.x** | JS side of store plugin (`Store.load`) | [VERIFIED: Tauri docs] |
| `ajv` + `ajv-formats` | **8.x** / **3.x** | Runtime JSON Schema validation in TS (lightweight; same schema source) | [VERIFIED: ajv.js.org] Industry-standard JSON Schema validator for JS |
| `json-schema-to-typescript` | **15.x** | **Build-time codegen** of `messages.ts` from `messages.schema.json` (dev-dep only) | [VERIFIED: npm] Most-used JSON Schema → TS type generator |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `file-rotate` (Rust crate) | **0.7.x** | Size-based log rotation (10MB threshold) | Use **instead of** `tracing-appender` if size-based rotation is required (tracing-appender does time-based) |
| `dirs-next` (Rust crate) | **2.x** | Cross-platform "where's the app-data dir" lookup | Backup for if `tauri-plugin-store` doesn't expose the resolved path |
| `notify` (Rust crate) | **6.x** | Watch sidecar log file for "last error line" updates | Used by crash banner to read tail of `sidecar.log` |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `tokio-tungstenite` | `tungstenite` (sync) | Sync API doesn't compose with Tauri's tokio runtime — async is correct here. |
| `vite` + vanilla TS | React + Vite | React costs ~140KB bundle + ecosystem complexity for ~12 wizard screens. Vanilla TS matches `mascot.html` aesthetic + 2× faster cold start. **CONTEXT explicitly favors vanilla TS.** |
| `pydantic` for IPC schema | hand-written `@dataclass` + `jsonschema` | Phase 6 convention bans pydantic. `jsonschema` is validation-only; no model gen. |
| `json-schema-to-typescript` codegen | Pure-runtime `ajv` validation (no codegen) | Codegen gives **compile-time** type errors; ajv only catches runtime. Use BOTH: codegen for DX, ajv for runtime guard. |
| `tracing-appender` (time-rotation) | `file-rotate` (size-rotation) | CONTEXT says **10MB × 5** rotation = size-based. Use `file-rotate`. |
| Tauri's built-in IPC | WS bus on `127.0.0.1:8765` | Tauri IPC only spans Rust ↔ Webview, not Rust ↔ Python sidecar. WS bus already exists. **Reuse, don't add a second IPC path.** |

**Installation:**

```bash
# Rust deps (Cargo.toml — src-tauri/)
cargo add tauri --features "macos-private-api"
cargo add tauri-plugin-shell tauri-plugin-store tauri-plugin-fs tauri-plugin-updater tauri-plugin-positioner tauri-plugin-process
cargo add tokio-tungstenite tokio --features "full"
cargo add serde --features "derive"
cargo add serde_json
cargo add tracing tracing-subscriber file-rotate notify dirs-next

# Python deps (pyproject.toml)
uv add --dev pyinstaller==6.20.0
uv add jsonschema

# Node deps (tauri/ui/package.json)
npm install --save-dev typescript vite @tauri-apps/api @tauri-apps/plugin-shell @tauri-apps/plugin-store
npm install --save-dev ajv ajv-formats json-schema-to-typescript
```

**Version verification (must run at planning time):**

```bash
npm view @tauri-apps/api version            # currently 2.x
npm view @tauri-apps/plugin-store version
npm view ajv version
pip index versions pyinstaller              # confirm 6.20.0 still latest
pip index versions jsonschema
cargo search tauri --limit 1
cargo search tokio-tungstenite --limit 1
```

Document the *verified* version + publish date next to each Plan task's installation step. Training data may lag the registry — never trust a version number you didn't `pip index` / `npm view` / `cargo search` in this session.

---

## Architecture Patterns

### System Architecture Diagram

```
                              ┌─────────────────────────────────────────────┐
                              │                Tauri Shell                  │
                              │             (Rust process)                  │
                              │                                             │
   ┌──────────────────────┐   │  ┌──────────────────────────────────────┐   │
   │  System Settings     │←──┼──│ tauri-plugin-shell                   │   │
   │  (Screen Recording   │   │  │   - Opens deep-links                 │   │
   │   Mic, deep-links)   │   │  │   - Opens existential.audio in       │   │
   └──────────────────────┘   │  │     default browser                  │   │
                              │  │   - Spawns sidecar via externalBin   │   │
                              │  └──────────────┬───────────────────────┘   │
                              │                 │ spawn + watchdog (3×)     │
                              │                 ▼                           │
                              │  ┌──────────────────────────────────────┐   │
                              │  │ tauri-plugin-store                   │   │
                              │  │   config.json in $APP_DATA           │   │
                              │  └──────────────────────────────────────┘   │
                              │                                             │
                              │  ┌──────────────────────────────────────┐   │
   ┌──────────────────────┐   │  │ Rust main                            │   │
   │  Webview             │   │  │   - WS client (tokio-tungstenite)    │   │
   │  (Vanilla TS UI)     │←──┼──│   - Forwards WS events to JS via     │   │
   │   - Wizard 3 steps   │   │  │     tauri::Emitter::emit()           │   │
   │   - Permissions      │   │  │   - Reads stdout/stderr → rolling    │   │
   │   - Audio test       │   │  │     log (file-rotate, 10MB×5)        │   │
   │   - Controller probe │   │  │   - Detects exit; restarts 3×        │   │
   │   - Smoke test       │──┐│  └──────────────┬───────────────────────┘   │
   └──────────────────────┘  ││                 │                           │
              ▲              ││                 │ stdout/stderr             │
              │              ││                 ▼                           │
              │              ││  ┌──────────────────────────────────────┐   │
              │              ││  │ Python sidecar process               │   │
              │              ││  │ (PyInstaller --onedir of `vibemix`)  │   │
              │ Tauri        ││  │                                      │   │
              │ Emitter      ││  │   python -m vibemix --wizard         │   │
              │ events       ││  │     ├─ vibemix.runtime.ws_bus        │   │
              │              ││  │     │   (existing — port 8765)       │   │
              │              ││  │     ├─ vibemix.platform.audio_*      │   │
              │              ││  │     │   (BlackHole detect, 1kHz test)│   │
              │              ││  │     ├─ vibemix.midi.watcher          │   │
              │              ││  │     │   (10s controller probe)       │   │
              │              ││  │     └─ vibemix.agent.dj_cohost       │   │
              │              ││  │         (exit-greeting smoke test)   │   │
              │              ││  └──────────────────────────────────────┘   │
              │              ││                  ▲                          │
              │              │└──────────────────│  WebSocket on 127.0.0.1: │
              │              │                   │  8765 (JSON messages,    │
              │              │  ipc.wizard.*     │  ipc.* namespace +       │
              │              └───────────────────┘  existing levels/manual) │
              │                  ipc.calibration.*
              └──────────────────  ipc.status.tick (30Hz) ──────────────────┘
                                   ipc.wizard.start/done
```

**Data flow — first-run wizard (single primary use case):**

1. User double-clicks `vibemix.app` → Tauri Rust `main()` starts.
2. Rust reads `config.json` via store plugin → `first_run_completed === false` → spawn sidecar in `--wizard` mode.
3. Tauri spawns `vibemix-core` (PyInstaller `--onedir`) via `app.shell().sidecar("vibemix-core").args(["--wizard"]).spawn()`.
4. Python sidecar boots WS bus on `127.0.0.1:8765`, sends `{"type":"ipc.boot","ready":true}`.
5. Rust connects WS client → forwards inbound messages to webview via `app.emit("ipc-message", payload)`.
6. Webview shows Step 1 (Permissions). User clicks `[ Grant ]` → Webview calls Tauri command `open_screen_recording_settings` → Rust opens deep-link via shell plugin.
7. Webview polls Python every 1s via `ipc.permission.check` → Python reports via AVAuthorizationStatus (mac) / Windows mic gate.
8. On all granted → auto-advance to Step 2 → Webview emits `ipc.calibration.list_devices` → Python returns from `sounddevice.query_devices`.
9. User picks device + clicks `[ ▶ PLAY 1 kHz TEST ]` → Webview emits `ipc.calibration.play_sine` → Python plays 1.5s + runs `assert_blackhole_rate` in parallel → emits `ipc.calibration.audio_result` with `{audible: bool, programmatic_pass: bool, actual_rate: int}`.
10. Both pass → advance to Step 3 → Webview emits `ipc.calibration.start_midi_listen` with 10s timeout → Python listens 10s, emits first event or `ipc.calibration.midi_timeout`.
11. Step 3 pass → Webview emits `ipc.calibration.smoke_test` → Python runs `HYPE_BEGINNER` greeting through cascade agent → TTS plays in headphones.
12. User clicks `[ Open vibemix → ]` → Webview emits `ipc.wizard.done` → Rust writes `first_run_completed: true` + calibration result to `config.json` → restarts sidecar in normal mode (no `--wizard` flag).
13. On any sidecar crash during the flow: Rust detects exit; restarts up to 3×; on 4th failure shows crash banner with `tail -1 sidecar.log`.

### Recommended Project Structure

```
dj-set-ai/
├── src/vibemix/                          # existing — Python sidecar lives here
│   ├── __main__.py                       # extend: add --wizard flag dispatch
│   ├── runtime/
│   │   ├── ws_bus.py                     # existing (Phase 4) — add ipc.* handlers
│   │   └── wizard.py                     # NEW: WizardLoop (registers ipc.* handlers)
│   ├── ui_bus/                           # NEW: schema-validated IPC message types
│   │   ├── __init__.py
│   │   ├── messages.py                   # @dataclass IPC messages
│   │   └── validator.py                  # jsonschema runtime guard
│   └── platform/
│       ├── audio_macos.py                # extend: gen_sine_1khz(), play_with_assert()
│       └── audio_windows.py              # extend: same
├── tauri/                                # NEW — Tauri 2.x project
│   ├── src-tauri/                        # Rust shell
│   │   ├── Cargo.toml
│   │   ├── tauri.conf.json5
│   │   ├── build.rs
│   │   ├── icons/                        # placeholder icons (Phase 18 ships real)
│   │   ├── capabilities/
│   │   │   └── default.json              # allowlist (sidecar, shell-open, store, fs)
│   │   ├── Entitlements.plist            # macOS — Hardened Runtime entitlements
│   │   ├── Info.plist                    # macOS — NSScreenCaptureUsageDescription, NSMicrophoneUsageDescription
│   │   ├── binaries/                     # PyInstaller output goes here per target-triple
│   │   │   ├── vibemix-core-x86_64-apple-darwin/
│   │   │   ├── vibemix-core-aarch64-apple-darwin/
│   │   │   └── vibemix-core-x86_64-pc-windows-msvc/
│   │   └── src/
│   │       ├── main.rs                   # entry — sets up plugins, spawns sidecar
│   │       ├── sidecar.rs                # spawn + watchdog + log capture + restart
│   │       ├── ws_client.rs              # tokio-tungstenite → emit to webview
│   │       ├── permissions.rs            # macOS deep-link helpers, Windows mic gate
│   │       └── config.rs                 # config.json wrapper
│   └── ui/                               # TS webview
│       ├── package.json
│       ├── tsconfig.json
│       ├── vite.config.ts
│       ├── index.html
│       ├── public/
│       │   ├── fonts/
│       │   │   ├── Workbench-Regular.woff2
│       │   │   ├── DMMono-Regular.woff2
│       │   │   ├── DMMono-Medium.woff2
│       │   │   ├── DSEG7Classic-Bold.woff2
│       │   │   └── Caveat-Bold.woff2
│       │   └── audio/
│       │       └── sine-1khz-1500ms.wav  # generated at build-time
│       └── src/
│           ├── main.ts                   # entry — mounts wizard
│           ├── tokens.css                # CSS custom properties from 11-UI-SPEC
│           ├── ipc/
│           │   ├── messages.schema.json  # SCHEMA SOURCE-OF-TRUTH
│           │   ├── messages.ts           # codegen output (json-schema-to-typescript)
│           │   ├── client.ts             # listen to Tauri events, dispatch ipc.*
│           │   └── validator.ts          # ajv runtime guard
│           └── wizard/
│               ├── step1-permissions.ts
│               ├── step2-output-device.ts
│               ├── step3-controller.ts
│               ├── smoke-test.ts
│               ├── crash-banner.ts
│               ├── components/
│               │   ├── step-indicator.ts
│               │   ├── primary-panel.ts
│               │   ├── button.ts
│               │   ├── dropdown-device.ts
│               │   ├── permissions-card.ts
│               │   ├── audio-test-button.ts
│               │   ├── blackhole-banner.ts
│               │   ├── window-picker.ts
│               │   └── controller-probe.ts
│               ├── icons/
│               │   ├── shield.svg.ts
│               │   ├── microphone.svg.ts
│               │   ├── headphones.svg.ts
│               │   └── speaker.svg.ts
│               └── controllers/
│                   └── ddj-flx4.svg.ts   # 10 controller silhouettes
├── scripts/
│   ├── build_sidecar.py                  # PyInstaller invocation per platform
│   ├── gen_sine.py                       # writes sine-1khz-1500ms.wav
│   ├── check_ipc_schema.py               # CI gate: validate dataclass↔schema
│   └── codegen_ts_types.sh               # runs json-schema-to-typescript
├── vibemix.spec.macos                    # PyInstaller spec (macOS, --onedir)
├── vibemix.spec.windows                  # PyInstaller spec (Windows, --onedir)
└── pyproject.toml                        # existing
```

### Pattern 1: Sidecar Spawn + Watchdog + Log Rotation

**What:** Tauri Rust spawns `vibemix-core` via `tauri-plugin-shell`. Watchdog re-spawns up to 3× on exit; emits `sidecar-state` events to the webview. stdout/stderr stream to a size-rotated log.

**When to use:** Single entry-point pattern for the entire Tauri shell. **Every** sidecar interaction goes through this.

**Example:**

```rust
// Source: Tauri 2 sidecar docs — https://v2.tauri.app/develop/sidecar
// + tracing-appender + file-rotate for log rotation
use tauri_plugin_shell::ShellExt;
use tauri_plugin_shell::process::CommandEvent;
use tauri::{AppHandle, Emitter};
use file_rotate::{FileRotate, ContentLimit, suffix::AppendCount, compression::Compression};
use std::io::Write;
use std::sync::{Arc, Mutex};

pub async fn spawn_sidecar_with_watchdog(
    app: AppHandle,
    wizard_mode: bool,
    log_path: std::path::PathBuf,
) -> Result<(), String> {
    let mut restart_count = 0u32;
    const MAX_RESTARTS: u32 = 3;

    let log = Arc::new(Mutex::new(FileRotate::new(
        log_path.clone(),
        AppendCount::new(5),                 // keep last 5 logs
        ContentLimit::Bytes(10 * 1024 * 1024), // 10MB per file
        Compression::None,
        None,
    )));

    loop {
        let mut cmd = app.shell().sidecar("vibemix-core")
            .map_err(|e| format!("sidecar lookup failed: {e}"))?;
        if wizard_mode { cmd = cmd.args(["--wizard"]); }

        let (mut rx, child) = cmd.spawn()
            .map_err(|e| format!("spawn failed: {e}"))?;

        app.emit("sidecar-state", serde_json::json!({"state": "running"})).ok();

        let log_clone = log.clone();
        let app_clone = app.clone();
        let result = tokio::spawn(async move {
            while let Some(event) = rx.recv().await {
                match event {
                    CommandEvent::Stdout(b) | CommandEvent::Stderr(b) => {
                        if let Ok(mut g) = log_clone.lock() {
                            let _ = g.write_all(&b);
                        }
                    }
                    CommandEvent::Error(e) => {
                        app_clone.emit("sidecar-error", e).ok();
                    }
                    CommandEvent::Terminated(payload) => {
                        return payload.code.unwrap_or(-1);
                    }
                    _ => {}
                }
            }
            -1
        }).await.unwrap_or(-1);

        if result == 0 {
            // clean exit — done
            app.emit("sidecar-state", serde_json::json!({"state": "stopped"})).ok();
            return Ok(());
        }

        restart_count += 1;
        if restart_count > MAX_RESTARTS {
            // tail last line of log → crash banner
            let last_line = read_last_log_line(&log_path).unwrap_or_default();
            app.emit("sidecar-crashed", serde_json::json!({
                "restart_count": restart_count,
                "last_error": last_line,
            })).ok();
            return Err("sidecar crashed after 3 restarts".into());
        }

        app.emit("sidecar-state", serde_json::json!({
            "state": "restarting",
            "attempt": restart_count,
        })).ok();
        tokio::time::sleep(std::time::Duration::from_millis(500 * restart_count as u64)).await;
    }
}

fn read_last_log_line(p: &std::path::Path) -> Option<String> {
    use std::io::{BufRead, BufReader};
    let f = std::fs::File::open(p).ok()?;
    BufReader::new(f).lines().filter_map(|l| l.ok()).last()
}
```

[VERIFIED: Tauri Context7 `/websites/v2_tauri_app`] for the `shell().sidecar(...).spawn()` + `CommandEvent` enum shape.
[VERIFIED: docs.rs] for `file-rotate` `FileRotate::new(...)` API.

### Pattern 2: WS Bus Client in Rust → Forward to Webview

**What:** `tokio-tungstenite` connects to `ws://127.0.0.1:8765` (Python sidecar's existing WS bus). Each inbound JSON message is re-emitted to the webview via `app.emit()`.

**When to use:** The single conduit for Python → Webview communication.

**Example:**

```rust
// Source: tokio-tungstenite docs (Context7 /snapview/tokio-tungstenite)
//       + Tauri Emitter pattern (Context7 /websites/v2_tauri_app)
use futures_util::{SinkExt, StreamExt};
use tokio_tungstenite::{connect_async, tungstenite::Message};
use tauri::{AppHandle, Emitter};

pub async fn run_ws_client(app: AppHandle) {
    let mut backoff_ms = 250u64;
    loop {
        match connect_async("ws://127.0.0.1:8765").await {
            Ok((mut ws, _resp)) => {
                backoff_ms = 250;
                app.emit("ws-state", "connected").ok();

                while let Some(msg) = ws.next().await {
                    match msg {
                        Ok(Message::Text(text)) => {
                            // Validate against schema (optional but recommended)
                            if let Ok(value) = serde_json::from_str::<serde_json::Value>(&text) {
                                let msg_type = value.get("type").and_then(|v| v.as_str()).unwrap_or("unknown");
                                app.emit(&format!("ipc:{msg_type}"), value).ok();
                            }
                        }
                        Ok(Message::Close(_)) | Err(_) => break,
                        _ => {}
                    }
                }
            }
            Err(_e) => {
                // sidecar not up yet → reconnect with exponential backoff
            }
        }
        app.emit("ws-state", "reconnecting").ok();
        tokio::time::sleep(std::time::Duration::from_millis(backoff_ms)).await;
        backoff_ms = (backoff_ms * 2).min(5000);
    }
}
```

[CITED: tokio-tungstenite README, `connect_async()` + `SinkExt`/`StreamExt` pattern] — the canonical async client shape.

### Pattern 3: JSON Schema as Source-of-Truth — Codegen + Runtime Validation

**What:** `messages.schema.json` defines every `ipc.*` message type. Python validates dataclass instances against it at runtime. TypeScript types are generated at build time from the same file. Both languages also support runtime validation.

**When to use:** Every IPC message crossing the Rust↔Webview or Python↔Rust boundary.

**Example schema fragment:**

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "vibemix.ipc.messages",
  "oneOf": [
    { "$ref": "#/definitions/StatusTick" },
    { "$ref": "#/definitions/CalibrationProbeAudio" },
    { "$ref": "#/definitions/CalibrationAudioResult" }
  ],
  "definitions": {
    "StatusTick": {
      "type": "object",
      "required": ["type", "ts", "payload"],
      "properties": {
        "type":  { "const": "ipc.status.tick" },
        "ts":    { "type": "string", "format": "date-time" },
        "payload": {
          "type": "object",
          "required": ["livekit", "gemini", "midi", "screen"],
          "properties": {
            "livekit": { "enum": ["ok", "connecting", "down"] },
            "gemini":  { "enum": ["ok", "down"] },
            "midi":    { "type": ["integer", "null"], "minimum": 0 },
            "screen":  { "enum": ["ok", "denied"] }
          },
          "additionalProperties": false
        }
      },
      "additionalProperties": false
    },
    "CalibrationProbeAudio": {
      "type": "object",
      "required": ["type", "ts", "payload"],
      "properties": {
        "type": { "const": "ipc.calibration.probe_audio" },
        "ts": { "type": "string", "format": "date-time" },
        "payload": {
          "type": "object",
          "required": ["output_device_id", "expected_rate"],
          "properties": {
            "output_device_id": { "type": "string" },
            "expected_rate": { "type": "integer", "enum": [44100, 48000] }
          }
        }
      }
    }
  }
}
```

**Python side (`src/vibemix/ui_bus/messages.py`):**

```python
# Source: project convention — hand-written @dataclass, NO pydantic (Phase 6)
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Literal, Optional
import json
from datetime import datetime, timezone
import jsonschema
from pathlib import Path

_SCHEMA_PATH = Path(__file__).resolve().parents[3] / "tauri" / "ui" / "src" / "ipc" / "messages.schema.json"
_SCHEMA = json.loads(_SCHEMA_PATH.read_text())

@dataclass
class StatusTickPayload:
    livekit: Literal["ok", "connecting", "down"]
    gemini:  Literal["ok", "down"]
    midi:    Optional[int]
    screen:  Literal["ok", "denied"]

@dataclass
class StatusTick:
    type: Literal["ipc.status.tick"]
    ts: str
    payload: StatusTickPayload

    @staticmethod
    def make(livekit, gemini, midi, screen) -> "StatusTick":
        return StatusTick(
            type="ipc.status.tick",
            ts=datetime.now(timezone.utc).isoformat(),
            payload=StatusTickPayload(livekit, gemini, midi, screen),
        )

    def to_json(self) -> str:
        d = asdict(self)
        jsonschema.validate(d, _SCHEMA)  # validate on serialize — drift guard
        return json.dumps(d)
```

**TypeScript side (`tauri/ui/src/ipc/messages.ts` — codegen output):**

```bash
# Source: json-schema-to-typescript docs
npx json-schema-to-typescript \
    tauri/ui/src/ipc/messages.schema.json \
    --output tauri/ui/src/ipc/messages.ts
```

Generates discriminated-union types automatically:

```typescript
export type IpcMessage = StatusTick | CalibrationProbeAudio | CalibrationAudioResult;

export interface StatusTick {
  type: "ipc.status.tick";
  ts: string;
  payload: {
    livekit: "ok" | "connecting" | "down";
    gemini:  "ok" | "down";
    midi: number | null;
    screen: "ok" | "denied";
  };
}
```

**Runtime guard with ajv (`tauri/ui/src/ipc/validator.ts`):**

```typescript
import Ajv from "ajv";
import addFormats from "ajv-formats";
import schema from "./messages.schema.json";
import type { IpcMessage } from "./messages";

const ajv = new Ajv({ allErrors: true, strict: false });
addFormats(ajv);
const validate = ajv.compile(schema);

export function parseIpcMessage(raw: unknown): IpcMessage {
  if (!validate(raw)) throw new Error(`IPC schema violation: ${ajv.errorsText(validate.errors)}`);
  return raw as IpcMessage;
}
```

**Build-time CI gate (`scripts/check_ipc_schema.py`):**

```python
"""Fails CI if Python dataclasses can't roundtrip the schema."""
import json, sys
from pathlib import Path
import jsonschema
from vibemix.ui_bus import messages as M
from datetime import datetime, timezone

SCHEMA = json.loads(Path("tauri/ui/src/ipc/messages.schema.json").read_text())

EXAMPLES = [
    M.StatusTick.make("ok", "ok", 1, "ok"),
    # add one example per dataclass
]

errors = 0
for ex in EXAMPLES:
    try:
        d = json.loads(ex.to_json())
        jsonschema.validate(d, SCHEMA)
    except Exception as e:
        print(f"FAIL: {type(ex).__name__}: {e}", file=sys.stderr)
        errors += 1

if errors: sys.exit(1)
print(f"OK: {len(EXAMPLES)} dataclasses validate against schema")
```

**npm script for TS gate (`tauri/ui/package.json`):**

```json
{
  "scripts": {
    "codegen:ipc": "json-schema-to-typescript src/ipc/messages.schema.json --output src/ipc/messages.ts",
    "check:ipc": "npm run codegen:ipc && tsc --noEmit"
  }
}
```

CI runs both: `python scripts/check_ipc_schema.py && (cd tauri/ui && npm run check:ipc)`.

### Pattern 4: Tauri Capabilities — Tight Scope, No Wildcards

**What:** Tauri 2 enforces *explicit* permissions via `capabilities/default.json`. Phase 11 needs: sidecar spawn, opening one URL, fs read/write to `$APPDATA/vibemix/`, store plugin.

**Example:**

```json
{
  "$schema": "../gen/schemas/desktop-schema.json",
  "identifier": "default",
  "description": "Capability for the main window",
  "windows": ["main"],
  "permissions": [
    "core:default",
    "core:window:default",
    "core:webview:default",
    "store:default",
    "positioner:default",
    {
      "identifier": "shell:allow-execute",
      "allow": [
        { "name": "binaries/vibemix-core", "sidecar": true, "args": [{ "validator": "^--wizard$" }] }
      ]
    },
    {
      "identifier": "shell:allow-open",
      "allow": [
        { "url": "https://existential.audio/blackhole" },
        { "url": "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture" },
        { "url": "x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone" }
      ]
    },
    {
      "identifier": "fs:allow-read-text-file",
      "allow": [{ "path": "$APPLOCALDATA/vibemix/logs/sidecar.log" }]
    },
    "updater:default"
  ]
}
```

[VERIFIED: Tauri Context7] — exact validator syntax for sidecar args + `shell:allow-open` URL allowlist.

**Anti-pattern to avoid:** `"shell:allow-execute"` without an `allow` array (gives blanket permission to spawn anything — silent security regression).

### Anti-Patterns to Avoid

- **Spawning the sidecar from the Webview via `Command.sidecar`.** Use it from Rust only — the Rust side owns the watchdog loop. Webview should never directly spawn; it sends `ipc.wizard.start` events instead.
- **Tauri IPC + WS bus side-by-side.** One bus. CONTEXT is explicit: WS bus on `127.0.0.1:8765`. Tauri events are *only* used to forward WS messages to the webview (`app.emit`). Do not invent a second JSON-RPC layer through `#[tauri::command]`.
- **Hard-coding `target_triple` in `externalBin`.** `externalBin` requires the **target-triple-suffixed filename** (e.g., `vibemix-core-aarch64-apple-darwin`). Tauri's bundler picks the right one at build time. Wrong suffix → "binary not found".
- **PyInstaller `--onefile`.** [CITED: `.planning/research/PITFALLS.md` P6, `STACK.md` line 348] AV false positives. Use `--onedir`. CONTEXT also locks this.
- **Pydantic for IPC schema.** Phase 6 convention — hand-validated. `jsonschema` for validation only.
- **Running CI without the schema gate.** If `messages.schema.json` and `ui_bus/messages.py` drift, **silent runtime errors** in production. The gate is non-negotiable.
- **Reading sidecar logs while file-rotate is writing.** `notify` watch the path; debounce reads to ≥250ms to avoid partial-line race.
- **Webview hardcoded `localhost:8765`.** The webview should **never** open its own WebSocket; only Rust does. Webview gets events via `tauri::Emitter`. This is a *security boundary* — webview should not be able to talk directly to localhost ports.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| WebSocket client with reconnect | Custom Tokio loop | `tokio-tungstenite` + exponential backoff helper | Battle-tested; handles close frames, ping/pong, fragmentation |
| Cross-platform app-data dir | Manual `$HOME/.config` logic | `tauri-plugin-store` or `dirs-next` | Resolves macOS/Windows/Linux paths correctly; Tauri integration |
| JSON Schema validation (Python) | Manual `isinstance` checks | `jsonschema` (4.23+) | Draft-07 conformance, descriptive errors |
| JSON Schema validation (TS) | Hand-written type guards | `ajv` + `ajv-formats` | Same schema as Python; runtime + compile-time coverage |
| TS type generation from schema | Hand-writing types twice | `json-schema-to-typescript` | Single source-of-truth; drift impossible |
| Log file rotation | Custom file-size checking | `file-rotate` crate | 10MB × 5 rotation works out of the box |
| PyInstaller hidden-import discovery | `--hidden-import X` × 200 | `collect_submodules` + `collect_all` from PyInstaller hooks | `.planning/research/STACK.md` already lists the right flags |
| Updater protocol | Custom URL-fetch + verify | `tauri-plugin-updater` | Signed manifest, Ed25519 verification, cross-platform installers |
| Spawning sidecar process | `std::process::Command` | `tauri-plugin-shell::ShellExt::sidecar` | Handles per-target-triple binary lookup, capability allowlist, stdout/stderr streaming as async events |
| macOS permission deep-linking | Custom AppleScript bridge | `x-apple.systempreferences:` URL opened via `tauri-plugin-shell` | Already in the URL allowlist; Apple-supported scheme |

**Key insight:** Tauri 2 has plugins for *every* cross-cutting concern. The temptation to "just use `std::process::Command`" or "write a quick WebSocket client" wastes a wave and produces less-secure code than the canonical pattern. Use plugins; spend the iteration budget on the wizard UX instead.

---

## Runtime State Inventory

> This phase introduces *new* state. The 5 categories detect places where runtime state could outlive a code-only change.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | (1) `config.json` at `$APP_DATA/vibemix/config.json` (mac: `~/Library/Application Support/vibemix/config.json`; win: `%APPDATA%\vibemix\config.json`). (2) Rolling log `sidecar.log` (5 files, 10MB each) at `$APP_LOCAL_DATA/vibemix/logs/`. | New artifacts created by this phase. Test cleanup: a deletion script (`scripts/reset_first_run.py`) helps Kaan / QA reproduce first-run state without manual rm -rf. |
| Live service config | (1) macOS Privacy & Security: Screen Recording + Microphone consent for `vibemix.app` bundle identifier `world.bravoh.vibemix` — granted state lives in `tccd` (TCC database), not in the bundle. (2) Windows: Mic permission lives in `Settings > Privacy & Security > Microphone` (per-app). | First-run state propagation hazard: if user grants permission to a *test build* of vibemix.app, then installs the *real signed build* (Phase 18) with the **same bundle id**, mac trust carries over (good). If bundle id changes (e.g., dev vs. prod), permissions are lost. **Pin bundle id to `world.bravoh.vibemix` in Phase 11 and never change it.** |
| OS-registered state | (1) Tauri auto-launch — NOT enabled in Phase 11 (could be added Phase 18). (2) macOS `nowplaying-cli` Homebrew install — already in CLAUDE.md, must be bundled in DMG per `STACK.md` line 67. | Phase 11 doesn't register OS-level startup items. Note: if Phase 11 spawns a long-lived sidecar, ensure it exits cleanly when the Tauri shell quits (sigterm handler in Python `__main__`). |
| Secrets/env vars | (1) `.env` file with `GEMINI_API_KEY` remains the dev path (per `MEMORY.md` v4 canonical baseline). (2) Phase 5 added install-UUID JWT in OS keychain — Phase 11 sidecar doesn't change this; it inherits from Phase 5. | No new secrets in this phase. Verify the PyInstaller-bundled sidecar reads `.env` from a known path (e.g., dev mode reads from CWD; prod mode reads from `$APP_DATA`). Document in `__main__.py`. |
| Build artifacts / installed packages | (1) PyInstaller produces `dist/vibemix-core-{target-triple}/` with `vibemix-core{.exe}` + bundled deps. (2) Tauri bundler produces `tauri/src-tauri/target/release/bundle/{macos,dmg,msi}/`. (3) `tauri/ui/dist/` (Vite build output). | All gitignored. CI matrix (macos-14 + windows-latest) builds them on tag push (Phase 20 wires the actual matrix). **Caveat:** Tauri caches Rust + npm builds — a stale build directory across target triples can produce stale binaries. Document `cargo clean && npm clean && rm -rf dist/` recipe for fresh-machine reproduction. |

**Critical:** Phase 11 introduces the `world.bravoh.vibemix` bundle identifier. Once Phase 18 codesigns with this identifier, **all macOS permission grants are keyed to it**. Changing it post-launch invalidates every user's granted permissions. Lock it in `tauri.conf.json5` and treat as load-bearing.

---

## Common Pitfalls

### Pitfall 1: PyInstaller `--onefile` triggers AV / Defender false positives

**What goes wrong:** Single-file binaries unpack themselves to a temp dir at runtime — Windows Defender and macOS Gatekeeper heuristics flag this as trojan-like behaviour.

**Why it happens:** `pyinstaller --onefile` writes the bootloader binary which extracts the runtime to `$TEMP` on every launch. AV scanners see "binary creating + executing files in temp" → trojan signature.

**How to avoid:** Use `--onedir` (CONTEXT + STACK.md both already lock this). Sign every nested `.dll`/`.so`/`.dylib` (per `.planning/research/PITFALLS.md` line 204).

**Warning signs:** Windows SmartScreen modal "Windows protected your PC"; macOS "vibemix.app cannot be opened" Gatekeeper modal. Fresh-machine install rehearsal (Phase 20) catches this.

[VERIFIED: PyInstaller Issue #6747, #6754 — `.planning/research/PITFALLS.md` lines 834-836]

### Pitfall 2: PyInstaller hidden-import misses (sounddevice, pyobjc, scipy, livekit)

**What goes wrong:** PyInstaller's static analyzer misses dynamic imports inside `sounddevice`, `pyobjc-framework-*`, `scipy.signal`, `livekit-agents`, `livekit-plugins-google`, `google-genai`. Resulting binary launches but crashes when first audio frame is captured / first Gemini call fires.

**Why it happens:** Pure-Python `__import__` calls and `pkg_resources.iter_entry_points` are invisible to PyInstaller's AST walk.

**How to avoid:** Use `collect_submodules`, `collect_all`, `collect_data_files` PyInstaller hook functions in the `.spec` file. Reference template:

```python
# vibemix.spec.macos — Source: STACK.md line 201 + PyInstaller hooks docs
from PyInstaller.utils.hooks import collect_submodules, collect_data_files, collect_all
import sys

block_cipher = None
hiddenimports = []
datas = []
binaries = []

# Critical: lift entire packages where __import__ is dynamic
for pkg in ['scipy', 'sounddevice', 'mido', 'rtmidi',
            'livekit', 'livekit.agents', 'livekit.plugins.google',
            'google.genai', 'google.cloud',
            'mss', 'PIL']:
    sub = collect_submodules(pkg)
    hiddenimports.extend(sub)

# pyobjc-framework-ScreenCaptureKit needs --collect-all (data + binaries)
for pkg in ['ScreenCaptureKit', 'Quartz', 'Cocoa', 'AVFoundation', 'CoreAudio']:
    try:
        b, d, h = collect_all(f'pyobjc.framework.{pkg}')
        binaries.extend(b); datas.extend(d); hiddenimports.extend(h)
    except Exception:
        pass

# Data files
datas += collect_data_files('vibemix', includes=['**/*.json', '**/*.txt'])
datas += [('src/vibemix/midi/profiles', 'vibemix/midi/profiles')]
datas += [('src/vibemix/prompts', 'vibemix/prompts')]

# nowplaying-cli — bundled binary for macOS only
if sys.platform == 'darwin':
    binaries += [('/opt/homebrew/bin/nowplaying-cli', '.')]

a = Analysis(
    ['src/vibemix/__main__.py'],
    pathex=['src'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    excludes=['tkinter', 'matplotlib', 'IPython', 'pytest'],
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name='vibemix-core',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,         # never UPX — triggers AV
    console=False,     # GUI subsystem; stderr/stdout still flow via Tauri
)

coll = COLLECT(
    exe, a.binaries, a.zipfiles, a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='vibemix-core',  # produces dist/vibemix-core/
)
```

**Warning signs:** Sidecar exits within 2s of spawn on a fresh install machine; `sidecar.log` shows `ModuleNotFoundError: No module named 'scipy._cyutility'` or similar. Reproduce by running PyInstaller output on a clean VM with `vibemix.app` only (no Python installed).

[VERIFIED: PyInstaller Context7 `/pyinstaller/pyinstaller`]

### Pitfall 3: macOS permissions reset on every dev build

**What goes wrong:** Every time Tauri rebuilds the unsigned dev `.app` bundle, macOS TCC asks the user to grant Screen Recording + Microphone *again* (because the binary signature changed).

**Why it happens:** TCC permissions are keyed to the **code signature** of the bundle, not the bundle id alone. Unsigned dev builds get re-prompted.

**How to avoid:**
1. Use `tauri dev` with **ad-hoc signing** (`codesign --force --deep --sign - target/.../vibemix.app`) — Kaan only.
2. For testing the wizard flow itself: reset TCC entries with `tccutil reset ScreenCapture world.bravoh.vibemix && tccutil reset Microphone world.bravoh.vibemix` before each rebuild.
3. Phase 18 (real signed builds) eliminates this.

**Warning signs:** "Why am I being asked for screen recording permission AGAIN?" — happens every `tauri build` cycle in dev.

[CITED: Apple developer forums + Tauri macOS distribution docs]

### Pitfall 4: `externalBin` target-triple suffix gotcha

**What goes wrong:** Tauri expects `binaries/vibemix-core-{target-triple}{exe}` (e.g., `binaries/vibemix-core-aarch64-apple-darwin` on M-series Mac). If the suffix is wrong or missing, `app.shell().sidecar("vibemix-core")` fails with "binary not found" only at runtime.

**Why it happens:** Tauri's `externalBin` configuration lists the **prefix** (`binaries/vibemix-core`). The bundler appends the target triple. PyInstaller doesn't know about target triples — it just produces `dist/vibemix-core/vibemix-core`. The build script must rename / move it.

**How to avoid:** Build script (`scripts/build_sidecar.py`) detects the target triple via `rustc -vV | grep host` and renames PyInstaller output:

```python
import subprocess, shutil, pathlib, sys
triple = subprocess.check_output(["rustc", "-vV"]).decode().split("host: ")[1].split("\n")[0]
suffix = ".exe" if "windows" in triple else ""
src = pathlib.Path(f"dist/vibemix-core/vibemix-core{suffix}")
dst_dir = pathlib.Path("tauri/src-tauri/binaries")
dst_dir.mkdir(parents=True, exist_ok=True)
# Move entire onedir + rename the binary
target_dir = dst_dir / f"vibemix-core-{triple}"
if target_dir.exists(): shutil.rmtree(target_dir)
shutil.copytree(pathlib.Path("dist/vibemix-core"), target_dir)
(target_dir / f"vibemix-core{suffix}").rename(target_dir / f"vibemix-core-{triple}{suffix}")
```

**Warning signs:** `tauri build` succeeds; `tauri dev` runs; **first attempt to spawn sidecar** fails with `Os { code: 2, kind: NotFound }`.

[VERIFIED: Tauri 2 sidecar docs §"Configure External Binaries"]

### Pitfall 5: `pyinstxtractor` / `strings` API-key leak

**What goes wrong:** Phase 5 routes Gemini through the proxy, but if any test build of vibemix-core accidentally re-introduces the raw `GEMINI_API_KEY` (e.g., `.env` accidentally bundled by `collect_data_files`), `strings dist/vibemix-core/vibemix-core | grep AIza` returns hits. Day-one launch leak.

**Why it happens:** `collect_data_files('vibemix', includes=['**/*'])` is too broad — `.env` files sometimes live in source tree.

**How to avoid:**
1. **Explicit `excludes`** in `collect_data_files`: `excludes=['*.env', '.env*', '*credentials*']`.
2. CI gate: `strings dist/vibemix-core/* | grep -E "AIza[0-9A-Za-z_-]{35}" && exit 1 || exit 0` runs on every PyInstaller build.
3. **Phase 18 has VERIFY-04 (binary attack verification)** — but Phase 11 should add the CI gate now to catch regressions early.

[CITED: `.planning/research/PITFALLS.md` line 84]

### Pitfall 6: Sidecar exit during wizard = blank wizard

**What goes wrong:** If `vibemix-core` crashes during the wizard (e.g., `sounddevice` device enumeration fails on a machine without CoreAudio), the wizard webview hangs forever waiting for `ipc.calibration.device_list`.

**Why it happens:** Webview has no timeout on outbound `ipc.*` requests. The watchdog will eventually emit `sidecar-crashed`, but the wizard UI doesn't know it should react.

**How to avoid:**
1. Every `ipc.*` request in TS has a `Promise.race([request, timeoutMs])` with a 5-10s timeout.
2. Webview subscribes to `sidecar-state` events — on `stopped`/`restarting` shows the crash banner over the current wizard step.
3. Wizard step components must be **idempotent** — re-entry after sidecar restart resumes from saved state, not first principles.

**Warning signs:** Wizard step shows "WORKING..." spinner indefinitely after a hidden sidecar crash.

### Pitfall 7: Heavy calibration wizard (Pitfall 20 from PITFALLS.md)

**What goes wrong:** Wizard balloons to 7+ steps; users abandon before completing.

**Why it happens:** Scope creep — "while we're here, let's ask voice + genre + mode".

**How to avoid:** **3 steps only.** Per CONTEXT: permissions → output device + sample-rate test → controller probe. Voice/genre/mode are Phase 12 surface. Don't bundle them.

**Warning signs:** Plan tasks introducing Step 4+ — reject in plan-check.

[CITED: `.planning/research/PITFALLS.md` Pitfall 20]

### Pitfall 8: Tauri capability over-broad scope

**What goes wrong:** Default `tauri init` boilerplate uses `"core:default"` + `"shell:default"` which permit too much. Phase 11 ships with a permissive allowlist; later phases inherit it; security audit fails Phase 18.

**Why it happens:** Convenience during dev. Scopes are easier to add than to remove.

**How to avoid:** Phase 11's `capabilities/default.json` must use **explicit allowlists** for `shell:allow-execute` (only sidecar) and `shell:allow-open` (only the two URLs we need). See Pattern 4 above. Plan-checker should reject any capability with `"identifier": "shell:allow-execute"` without an `allow` array.

### Pitfall 9: Avery mascot reserved corner accidentally gets art in Phase 11

**What goes wrong:** Executor sees `mocks/vibemix-app-ui.html` mascot region and tries to render a placeholder character. Phase 13 owns this; Phase 11 = empty outline.

**How to avoid:** `11-UI-SPEC.md` line 207 is explicit: "1px dashed `--ink-engraved` border, transparent interior, centered Workbench 9px label 'AVERY · arriving phase 13' in `--ink-deep`. DO NOT fill with placeholder art." Plan-checker enforces. UI-checker verifies (Dimension 2).

### Pitfall 10: Schema drift discovered at runtime, not CI time

**What goes wrong:** Python dataclass changes a field name; TS types regenerated from old schema; CI doesn't catch; production sidecar emits message with new field; webview validator fails; wizard frozen.

**How to avoid:** **Both** gates must run on every PR:
1. `python scripts/check_ipc_schema.py` — every dataclass instance roundtrips through schema.
2. `cd tauri/ui && npm run check:ipc` — re-runs codegen + `tsc --noEmit`.

GitHub Actions step (Phase 20 wires it):
```yaml
- name: IPC schema sync gate
  run: |
    python scripts/check_ipc_schema.py
    cd tauri/ui && npm ci && npm run check:ipc
```

### Pitfall 11: 1kHz test fails on speakers because BlackHole isn't loopback-routed

**What goes wrong:** User picks "Built-in Output" instead of "BlackHole 2ch" for output — 1kHz tone plays, user hears it ("Yes, sounded clean"), but `assert_blackhole_rate` programmatic guard fails because BlackHole isn't in the input chain.

**Why it happens:** User confusion between "output device for hearing audio" and "loopback device for capturing master output".

**How to avoid:**
1. Output dropdown labels: "**Headphones / Speaker — for Avery's voice**" (clarifies user-output role).
2. Separate detection panel: "**Capture device** (BlackHole) — Detected ✓" or "Missing ✕ → install link". Read-only — not user-selectable in v1.
3. Programmatic guard reports `which_device_failed` explicitly so the error message can be specific: "BlackHole 2ch detected but reporting 48000 Hz on capture — restart Audio MIDI Setup".

### Pitfall 12: Controller probe times out because user's controller has only encoders (no pads)

**What goes wrong:** Pioneer XDJ-RX3 + similar pro-line controllers may not register pad presses if user only twists an encoder. Step 3 instruction says "press any pad or button" — encoder twists are CC, pad presses are notes.

**How to avoid:** Listen for **any** MIDI event (notes OR CCs OR pitch bend). Update copy: "press any pad, button, or twist a knob" — match what `mido` actually receives. Test against Phase 9's 10 controller JSONs.

---

## Code Examples

Verified patterns from official sources. Reference these exact shapes in Plan tasks.

### Example 1: 1kHz Sine Test (Python sidecar side)

```python
# Source: project Phase 2 platform/_audio_macos.py + sounddevice docs
# https://python-sounddevice.readthedocs.io/en/0.5.5/usage.html#playback
import numpy as np
import sounddevice as sd
import json
from vibemix.ui_bus.messages import CalibrationAudioResult

def generate_sine(freq_hz: float = 1000.0, duration_s: float = 1.5,
                  sample_rate: int = 48000, peak_dbfs: float = -6.0,
                  fade_ms: int = 100) -> np.ndarray:
    n = int(sample_rate * duration_s)
    t = np.arange(n) / sample_rate
    peak = 10 ** (peak_dbfs / 20.0)
    sine = peak * np.sin(2 * np.pi * freq_hz * t)
    # Linear fades to avoid click
    f = int(sample_rate * fade_ms / 1000)
    if f > 0:
        sine[:f] *= np.linspace(0, 1, f)
        sine[-f:] *= np.linspace(1, 0, f)
    return sine.astype(np.float32)

async def run_calibration_audio_test(output_device_id: str,
                                     ws_bus) -> CalibrationAudioResult:
    """Plays 1kHz sine + verifies BlackHole sample rate programmatically.
    Both audible-confirm and programmatic must agree → 'pass'."""
    sine = generate_sine()
    actual_rate = None
    programmatic_pass = False

    try:
        sd.play(sine, samplerate=48000, device=output_device_id, blocking=False)
        # Run programmatic guard in parallel via vibemix.platform.audio
        from vibemix.platform import audio_input
        actual_rate = audio_input.query_blackhole_sample_rate()
        programmatic_pass = (actual_rate == 48000)
        sd.wait()
    except Exception as e:
        return CalibrationAudioResult.make(
            playback_ok=False, audible_confirmed=False,
            programmatic_pass=False, actual_rate=actual_rate,
            error=str(e),
        )

    # Wait for user-confirm message via ws_bus (Yes / Retry)
    audible = await ws_bus.await_message("ipc.calibration.user_heard_tone", timeout_s=30)

    return CalibrationAudioResult.make(
        playback_ok=True,
        audible_confirmed=audible,
        programmatic_pass=programmatic_pass,
        actual_rate=actual_rate,
        error=None,
    )
```

### Example 2: macOS Permission Deep-Link + Polling

```rust
// Source: Apple URL schemes (publicly documented) + Tauri Context7
// https://developer.apple.com/library/archive/featuredarticles/iPhoneURLScheme_Reference/
use tauri::AppHandle;
use tauri_plugin_shell::ShellExt;

#[tauri::command]
pub async fn open_screen_recording_settings(app: AppHandle) -> Result<(), String> {
    let url = "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture";
    app.shell().open(url, None).map_err(|e| e.to_string())
}

#[tauri::command]
pub async fn open_microphone_settings(app: AppHandle) -> Result<(), String> {
    let url = "x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone";
    app.shell().open(url, None).map_err(|e| e.to_string())
}
```

```python
# Source: pyobjc AVFoundation bindings
# https://pypi.org/project/pyobjc-framework-AVFoundation/
# Probe permission state from the sidecar; emit via ws_bus
from AVFoundation import (
    AVCaptureDevice, AVAuthorizationStatusAuthorized,
    AVMediaTypeAudio,
)

def check_microphone_permission() -> str:
    """Returns 'authorized' | 'denied' | 'notDetermined' | 'restricted'."""
    status = AVCaptureDevice.authorizationStatusForMediaType_(AVMediaTypeAudio)
    return {
        0: "notDetermined", 1: "restricted", 2: "denied",
        3: "authorized",
    }.get(status, "unknown")
```

For screen recording on macOS the status is read via `CGPreflightScreenCaptureAccess()` (Quartz). Polling cycle: webview emits `ipc.permission.check` every 1s while step 1 is active.

### Example 3: BlackHole detection (Python)

```python
# Source: project Phase 2 + sounddevice.query_devices docs
import sounddevice as sd
from typing import Optional

def detect_blackhole() -> tuple[bool, Optional[str], Optional[str]]:
    """Returns (found, device_id, variant). variant in {'2ch','16ch','64ch'}."""
    for i, d in enumerate(sd.query_devices()):
        name = d['name']
        if name.startswith('BlackHole'):
            for variant in ('64ch', '16ch', '2ch'):
                if variant in name:
                    return True, str(i), variant
            return True, str(i), 'unknown'
    return False, None, None
```

### Example 4: TS Wizard Step Wiring (vanilla, no React)

```typescript
// Source: 11-UI-SPEC.md component contracts + Tauri 2 JS API
import { listen, emit } from "@tauri-apps/api/event";
import { parseIpcMessage } from "./ipc/validator";
import type { StatusTick, CalibrationAudioResult } from "./ipc/messages";

type WizardStep = "permissions" | "audio" | "controller" | "smoke-test" | "done";
let currentStep: WizardStep = "permissions";

// Listen for sidecar messages
await listen<unknown>("ipc:ipc.status.tick", (event) => {
  const msg = parseIpcMessage(event.payload) as StatusTick;
  renderStatusBadges(msg.payload);
});

await listen<unknown>("ipc:ipc.calibration.audio_result", (event) => {
  const msg = parseIpcMessage(event.payload) as CalibrationAudioResult;
  if (msg.payload.audible_confirmed && msg.payload.programmatic_pass) {
    advanceTo("controller");
  } else if (!msg.payload.programmatic_pass) {
    showErrorBand(`sample rate mismatch — blackhole reporting ${msg.payload.actual_rate}, expected 48000`);
  }
});

// Sidecar crash banner
await listen<{ restart_count: number; last_error: string }>("sidecar-crashed", (event) => {
  showCrashBanner(event.payload.last_error);
});

function advanceTo(step: WizardStep): void {
  currentStep = step;
  document.body.dataset.step = step;
  // Token-driven slide animation (250ms cap per 11-UI-SPEC §motion budget)
}
```

### Example 5: Tauri main.rs (entry)

```rust
// Source: Tauri 2 docs + project layout
use tauri::Manager;

mod sidecar;
mod ws_client;
mod permissions;
mod config;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_store::Builder::new().build())
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_positioner::init())
        .plugin(tauri_plugin_updater::Builder::new().build())
        .plugin(tauri_plugin_process::init())
        .invoke_handler(tauri::generate_handler![
            permissions::open_screen_recording_settings,
            permissions::open_microphone_settings,
            config::read_first_run_state,
            config::write_first_run_state,
            sidecar::restart_sidecar,
        ])
        .setup(|app| {
            let app_handle = app.handle().clone();
            let log_path = app.path()
                .app_local_data_dir()
                .unwrap()
                .join("vibemix/logs/sidecar.log");
            std::fs::create_dir_all(log_path.parent().unwrap()).ok();

            // 1. Spawn sidecar with watchdog (wizard mode if first run)
            let wizard_mode = config::is_first_run(&app_handle);
            tauri::async_runtime::spawn(sidecar::spawn_sidecar_with_watchdog(
                app_handle.clone(), wizard_mode, log_path,
            ));

            // 2. Spawn WS client (connects to 127.0.0.1:8765)
            tauri::async_runtime::spawn(ws_client::run_ws_client(app_handle));

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Tauri 1.x `tauri::api::process::Command` | Tauri 2.x `tauri-plugin-shell` + `app.shell().sidecar(...)` | Tauri 2.0 (2024-10) | Capability-based permissions; sidecar args validated by regex in `default.json` |
| Tauri 1.x `tauri.allowlist` config | Tauri 2.x `capabilities/*.json` | Tauri 2.0 | Per-window capability scopes; multiple windows = multiple capability files |
| Tauri 1.x `tauri::updater` built-in | Tauri 2.x `tauri-plugin-updater` | Tauri 2.0 | Plugin can be omitted entirely if updater isn't shipped |
| altool for macOS notarization | `notarytool` | Xcode 13 / Nov 2023 deprecation | altool fully unsupported as of Nov 2023 — Phase 18 must use notarytool |
| Quartz `CGWindowListCreateImageFromArray` | ScreenCaptureKit (`pyobjc-framework-ScreenCaptureKit`) | macOS 14 deprecation; Phase 8 shipped | Phase 11 doesn't change screen capture; Phase 8 already migrated |
| PyInstaller 5.x numpy hooks (broken) | PyInstaller 6.14+ with stable numpy 2.x hooks | PyInstaller 6.14 (2024) | Phase 11 uses 6.20.0 |
| `livekit-server --dev` bundled binary | Cascade `AgentSession` runs headless, no Room | Phase 4 retro | Phase 11 doesn't need to bundle livekit-server |

**Deprecated/outdated:**

- **Tauri 1.x sidecar pattern** (`tauri::api::process::Command::new_sidecar(...)`): replaced by `tauri-plugin-shell`. Code samples from old blog posts won't compile against Tauri 2.
- **PyInstaller `--onefile` for distributed apps**: known AV-trigger; `--onedir` is the consensus modern choice.
- **`altool` for notarization**: dead. `xcrun notarytool` is the only working path.
- **`tauri.allowlist` in `tauri.conf.json`**: removed in Tauri 2. Replaced by `capabilities/*.json`.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | macOS Screen Recording deep-link URL `x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture` is still valid on macOS 14/15 | Pattern 3, Example 2 | Permission button doesn't open Settings; user has to navigate manually. Mitigation: test on Sonoma + Sequoia before phase close. URL has been stable since Big Sur. |
| A2 | `tauri-plugin-updater` 2.x can be initialized with no `pubkey`/`endpoints` and not crash | Q12 | If plugin requires non-empty config to instantiate, Phase 11 has to ship a placeholder. Mitigation: read plugin source on first plan task; fall back to feature flag if needed. |
| A3 | `notify` crate's `RecommendedWatcher` can tail an actively-rotating log file without race conditions on Windows | Pitfall — log reading | Crash banner shows stale error line. Mitigation: 250ms debounce in tail-reader. |
| A4 | `tauri-plugin-store` writes are atomic across crashes (no half-written `config.json`) | Q9 | Corrupted first-run state; wizard re-triggers wrongly. Mitigation: `Store.load` has built-in JSON parse error → fallback to defaults. |
| A5 | `json-schema-to-typescript` 15.x produces clean discriminated unions for `oneOf` with `const`-tagged types | Pattern 3 | Generated TS types are too loose; type errors don't catch IPC-shape drift. Verify by running codegen on the sample schema fragment above before committing. |
| A6 | PyInstaller `--onedir` bundle for `vibemix` lands in 150-250MB range per platform | Q2 | If 400MB+, signing/notarization slowness adds Phase 18 risk. Per `STACK.md` line 347, expected range is documented. Measure on first build. |
| A7 | Building a target-triple-aware PyInstaller output via `scripts/build_sidecar.py` (subprocess `rustc -vV`) works in CI matrix | Pitfall 4 | CI fails to find rustc; use `cargo metadata` instead. |
| A8 | macOS bundle identifier `world.bravoh.vibemix` is unclaimed and matches Phase 18 codesigning identity | Runtime State Inventory | If claimed elsewhere, codesigning fails. Check with `xcrun stapler validate` against a test build. |
| A9 | `nowplaying-cli` Homebrew binary can be bundled into the Tauri DMG via `binaries` array in `pyinstaller.spec` without License conflicts | Pitfall 2 | License audit fails. Bundle the binary under fair-use + credit; verify license in Phase 11. |
| A10 | The exit-greeting smoke test (Step 4 — HYPE_BEGINNER greeting via cascade) reuses Phase 4 `dj_cohost_agent` without modification | Q1, Q13 | If agent requires additional context (recent_turns, music_state) it won't bootstrap cold. Mitigation: pass a minimal seed-state struct; cascade agent already handles empty TurnHistory. |
| A11 | `file-rotate` size-based rotation supports the 10MB × 5 spec without further config | Pattern 1 | If rotation only fires on next write after threshold, log might exceed 10MB briefly. Mitigation: acceptable; document. |
| A12 | Wizard window 960×680 non-resizable does NOT trigger Windows DWM scaling issues on high-DPI displays | 11-UI-SPEC §Window Dimensions | Wizard appears tiny on 4K Windows. Mitigation: `hidpi: true` in `tauri.conf.json5` (already in spec line 41). |

---

## Open Questions

1. **Does `tauri-plugin-updater` require a non-empty `pubkey` to even initialize?**
   - What we know: Plugin loads in Phase 11 *stubbed* — no real signed manifest URLs.
   - What's unclear: If the plugin builder errors on empty config, we need a placeholder pubkey.
   - Recommendation: First plan task includes a 15-min spike to confirm. If required, generate a throwaway Ed25519 key, document in code comment `// REPLACED IN PHASE 18`.

2. **Should the wizard exit-smoke-test play a *real* `HYPE_BEGINNER` greeting through Gemini, or a pre-recorded WAV?**
   - What we know: CONTEXT says HYPE_BEGINNER through cascade agent.
   - What's unclear: Phase 5 proxy URL must be reachable for live cascade. If offline (Kaan's laptop on a plane), wizard would fail.
   - Recommendation: Default to live cascade. Fall back to a bundled pre-recorded greeting WAV on `gemini=down`. Add `ipc.calibration.smoke_test_offline_fallback` event to schema.

3. **How does the wizard handle "user grants Screen Recording, then revokes mid-wizard"?**
   - Recommendation: Detect via polling (every 1s on the permissions step). If revoked while on Step 2/3, show a non-blocking warning toast but don't reset the wizard.

4. **Where does sidecar log go in dev mode (no Tauri shell)?**
   - Recommendation: When running `python -m vibemix` directly (Kaan's `./run_v4.sh`-style flow), the sidecar writes to stderr only. When spawned by Tauri, Tauri owns the rotation. Document in `__main__.py`.

5. **Does the controller probe ignore MIDI events that are pre-existing (e.g., FLX4 sends a "hello" SysEx on connect)?**
   - Recommendation: Drain MIDI input for 200ms before starting the 10s countdown to avoid auto-passing on bootstrap noise. Test on Phase 9 controllers.

6. **Bundle id collision risk between dev/prod builds.**
   - Recommendation: Pin `world.bravoh.vibemix` in Phase 11. Document in `tauri.conf.json5` comment.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Rust toolchain (`rustc`, `cargo`) | Tauri build | ✓ | (verify with `rustc --version`; check `/Users/ozai/.cargo/bin/cargo` per init) | — |
| Node.js + npm | Tauri UI build (Vite) | ✓ | (verify `node --version` ≥ 18) | — |
| Tauri CLI (`@tauri-apps/cli` 2.x) | `tauri dev`, `tauri build` | Install via `npm install -D @tauri-apps/cli` | — | — |
| Python 3.12 | Sidecar + PyInstaller | ✓ (already pinned in pyproject.toml) | 3.12.x | — |
| PyInstaller | Sidecar bundling | Install via `uv add --dev pyinstaller==6.20.0` | 6.20.0 | — |
| BlackHole 2ch | macOS audio capture (Phase 2/11 wizard test) | Kaan's dev rig has it | 2ch | Wizard surfaces install link |
| `nowplaying-cli` (Homebrew) | macOS track metadata | `/opt/homebrew/bin/nowplaying-cli` per CLAUDE.md | — | Phase 11 not strictly needed; Phase 18 bundles into DMG |
| WebView2 (Windows) | Tauri webview on Windows | Pre-installed on Win10+ since 2022 | — | Tauri 2 bundles fallback installer |
| `xcrun notarytool` | Phase 18 only — not Phase 11 | — | — | — |

**Missing dependencies with no fallback:**
- None for Phase 11 mac-side; Kaan's dev rig has all deps. Phase 20 fresh-machine rehearsal is the final gate.

**Missing dependencies with fallback:**
- Windows test environment: Kaan doesn't have Windows handy. Phase 11 testing on Mac only; Phase 20 CI matrix (windows-latest) is the authoritative live gate. Document in deferred-items.md if needed.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework (Python) | pytest 8.x (existing in pyproject.toml) |
| Framework (Rust) | `cargo test` (builtin) |
| Framework (TS) | vitest 2.x (recommended — Vite-native) |
| Config file (Python) | `pyproject.toml` `[tool.pytest.ini_options]` |
| Config file (Rust) | Cargo workspace — `tauri/src-tauri/Cargo.toml` |
| Config file (TS) | `tauri/ui/vitest.config.ts` (Wave 0 creates) |
| Quick run command (Python) | `pytest tests/ui_bus/ -x -q` |
| Quick run command (Rust) | `cargo test --manifest-path tauri/src-tauri/Cargo.toml` |
| Quick run command (TS) | `cd tauri/ui && npx vitest run --reporter=dot` |
| Full suite command | `pytest && cargo test --manifest-path tauri/src-tauri/Cargo.toml && (cd tauri/ui && npx vitest run)` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ARCH-01 | `python -m vibemix --wizard` boots sidecar in wizard mode | smoke | `pytest tests/sidecar/test_wizard_entrypoint.py -x` | ❌ Wave 0 |
| ARCH-01 | Sidecar emits `ipc.boot ready=true` within 3s of spawn | integration | `pytest tests/sidecar/test_wizard_boot.py -x` | ❌ Wave 0 |
| DIST-05 | Tauri shell spawns sidecar successfully on macOS | manual / e2e | `cd tauri && npm run tauri dev` + smoke checklist | ❌ Wave 0 (manual checklist `.md`) |
| DIST-05 | Sidecar restart triggers after force-kill (3× retry) | integration | `cargo test --manifest-path tauri/src-tauri/Cargo.toml -- sidecar::watchdog` | ❌ Wave 0 |
| DIST-05 | Crash banner surfaces last log line after 4th failure | integration | `cargo test --manifest-path tauri/src-tauri/Cargo.toml -- sidecar::crash_banner` | ❌ Wave 0 |
| DIST-05 | IPC schema validation: Python dataclass roundtrips against `messages.schema.json` | unit | `python scripts/check_ipc_schema.py` | ❌ Wave 0 |
| DIST-05 | IPC schema validation: TS codegen + `tsc --noEmit` passes | unit | `cd tauri/ui && npm run check:ipc` | ❌ Wave 0 |
| UX-01 | Wizard completes Step 1 → Step 2 transition on permission granted | unit | `pytest tests/wizard/test_step1_permissions.py -x` | ❌ Wave 0 |
| UX-01 | 1kHz sine plays on selected device + programmatic guard agrees | smoke (live audio) | `pytest tests/wizard/test_step2_audio.py -x -m macos_audio` | ❌ Wave 0 |
| UX-01 | BlackHole detection returns `(True, id, '2ch')` when installed | unit | `pytest tests/wizard/test_blackhole_detect.py -x` | ❌ Wave 0 |
| UX-01 | Controller probe captures first MIDI event within 10s OR times out cleanly | integration | `pytest tests/wizard/test_step3_controller.py -x` | ❌ Wave 0 |
| UX-01 | Wizard exit-smoke-test plays one greeting (mocked Gemini) | integration | `pytest tests/wizard/test_smoke_test_exit.py -x` | ❌ Wave 0 |
| UX-01 | `config.json` written atomically; `first_run_completed: true` after wizard | unit | `pytest tests/config/test_first_run_state.py -x` | ❌ Wave 0 |
| UX-11 | `ipc.status.tick` schema validates with full payload + null midi | unit | `pytest tests/ui_bus/test_status_tick.py -x` | ❌ Wave 0 |
| UX-11 | TS validator (`ajv`) rejects malformed status tick at runtime | unit | `cd tauri/ui && npx vitest run src/ipc/validator.spec.ts` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/<area>/ -x -q && (cd tauri/ui && npx vitest run)` (whatever area the task touched)
- **Per wave merge:** Full suite — `pytest && cargo test && (cd tauri/ui && npx vitest run) && python scripts/check_ipc_schema.py && (cd tauri/ui && npm run check:ipc)`
- **Phase gate:** Full suite green + manual e2e checklist signed off (Tauri dev mode runs wizard 3 times on macOS without errors) before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `pyproject.toml` — add `jsonschema` dep
- [ ] `tauri/src-tauri/Cargo.toml` — new file
- [ ] `tauri/ui/package.json` — new file
- [ ] `tauri/ui/vitest.config.ts` — new file
- [ ] `tests/ui_bus/conftest.py` — shared fixtures for IPC dataclass tests
- [ ] `tests/wizard/conftest.py` — shared fixtures (mock ws_bus, fake AVCaptureDevice)
- [ ] `tests/sidecar/conftest.py` — fixtures for subprocess spawn / mock CommandEvent stream
- [ ] `tauri/src-tauri/src/sidecar.rs` test module — fake CommandEvent stream + assert watchdog behavior
- [ ] `scripts/check_ipc_schema.py` — Python build-time gate
- [ ] `tauri/ui/scripts/codegen_ipc.sh` — TS codegen invocation
- [ ] `tauri/ui/src/ipc/messages.schema.json` — schema file (the SOURCE-OF-TRUTH)

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes (Phase 5 already covers install-UUID JWT) | Inherits Phase 5 JWT; Phase 11 doesn't introduce new auth |
| V3 Session Management | no | n/a — single-process desktop app |
| V4 Access Control | yes — Tauri capabilities | Allowlist in `capabilities/default.json` (Pattern 4) |
| V5 Input Validation | yes — every IPC message | `jsonschema` (Python) + `ajv` (TS) runtime validation (Pattern 3) |
| V6 Cryptography | yes — Phase 18 (updater pubkey) | `tauri-plugin-updater` uses Ed25519; Phase 11 generates throwaway key for stubbing |
| V7 Errors & Logging | yes — sidecar logs | `file-rotate` 10MB × 5; no PII; no API keys leak into logs (assert) |
| V10 Malicious Code | yes — capability scopes | Tight `shell:allow-open` URL allowlist (only 3 URLs) |
| V14 Configuration | yes — Tauri config | `hardenedRuntime: true`, `minimumSystemVersion: "12.3"` |

### Known Threat Patterns for Tauri + Python sidecar

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Webview opens arbitrary URLs (XSS-bridge) | Spoofing, Tampering | `shell:allow-open` URL allowlist (Pattern 4) — only 3 URLs permitted |
| Webview spawns arbitrary binaries | Elevation | `shell:allow-execute` allow array with `name: "binaries/vibemix-core", sidecar: true` + arg validator regex |
| API key leakage via PyInstaller bundle inspection | Information Disclosure | Phase 5 proxy + Phase 11 CI gate (`grep AIza` on dist/) + Phase 18 VERIFY-04 |
| Webview reads arbitrary local files | Information Disclosure | `fs` plugin scoped to `$APPLOCALDATA/vibemix/**` only |
| Sidecar listens on `0.0.0.0:8765` (network exposure) | Spoofing | Existing `vibemix.runtime.ws_bus` binds `127.0.0.1` (Phase 4 — verified). Re-assert in Phase 11. |
| Tauri custom protocol abuse | Tampering | Tauri 2 disables `asset` protocol by default; we don't enable it |
| Updater MITM | Tampering | Ed25519 signature verification (Phase 18 ships real key) |
| Sidecar log file contains user-visible PII (window titles!) | Information Disclosure | Log only sidecar internals; the `events.jsonl` (Phase 15) is separate. Add CI assertion that `sidecar.log` never logs raw `window_title` strings. |

### Phase 11 specific security checklist

- [ ] `127.0.0.1:8765` bind verified (no `0.0.0.0`)
- [ ] `shell:allow-open` URL allowlist (3 URLs only)
- [ ] `shell:allow-execute` sidecar-only, validator regex on args
- [ ] PyInstaller spec excludes `.env*` from data files
- [ ] CI gate: `strings dist/vibemix-core/* | grep -E "AIza[0-9A-Za-z_-]{35}"` returns no matches
- [ ] `tauri.conf.json5` sets `hardenedRuntime: true`
- [ ] `Entitlements.plist` ships with minimum required entitlements:
  - `com.apple.security.cs.allow-unsigned-executable-memory` (Python needs JIT-like behaviour for some C-exts)
  - `com.apple.security.device.audio-input`
  - `com.apple.security.device.microphone`
  - NO `com.apple.security.cs.allow-arbitrary-loads` (network whitelist for Phase 5 proxy)
- [ ] `Info.plist` ships:
  - `NSScreenCaptureUsageDescription` — "vibemix watches your DJ software window to detect cues and reactions"
  - `NSMicrophoneUsageDescription` — "vibemix listens for your voice so you can talk back to avery"
  - `LSMinimumSystemVersion` — `12.3`
- [ ] Bundle id pinned `world.bravoh.vibemix`

---

## Sources

### Primary (HIGH confidence)

- **Tauri 2 docs** [Context7 `/websites/v2_tauri_app`, 3033 snippets, score 82.48] — sidecar pattern, capabilities, updater, store, fs, macOS Info.plist + Entitlements.plist, decorations: false, `tauri::Emitter`, `tauri-plugin-positioner`
- **Tauri 2 sidecar guide** — https://v2.tauri.app/develop/sidecar (verbatim `shell().sidecar(...).spawn()` + `CommandEvent` enum)
- **PyInstaller docs** [Context7 `/pyinstaller/pyinstaller`, 2227 snippets, score 83.14] — `collect_submodules`, `collect_all`, `collect_data_files`, spec file shape, COLLECT for onedir
- **tokio-tungstenite docs** [Context7 `/snapview/tokio-tungstenite`, 60 snippets, score 85.4] — `connect_async`, `Message` enum, exponential backoff pattern
- **Project research** `.planning/research/STACK.md` — versions verified against PyPI/GitHub
- **Project research** `.planning/research/PITFALLS.md` — installer false-positives (P6), API key leak (P3), wizard creep (P20)
- **Project Phase 4 + Phase 9 SUMMARY** — establish WS bus pattern, audible-deck cascade flow, controller library

### Secondary (MEDIUM confidence)

- **Apple URL schemes** for `x-apple.systempreferences:` — publicly documented but URL format has subtle macOS-version variations; verify on test machines
- **`json-schema-to-typescript` README** — codegen for `oneOf` discriminated unions; verify on first run
- **`file-rotate` crate docs** — size-based rotation behaviour; verify default `ContentLimit::Bytes` semantics

### Tertiary (LOW confidence)

- **Tauri ecosystem blog posts** for "best practices" — Tauri 2 is recent enough that blog posts pre-2025 are likely stale; prefer canonical docs
- **PyInstaller community wisdom on hidden imports** — some community fixes are project-specific; verify each in test build

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every library verified via Context7 + project research; versions cross-checked
- Architecture: HIGH — Tauri 2 sidecar + WS bus pattern is the canonical shape, well-documented in both Tauri docs and Pitfalls/Stack
- IPC schema sync: MEDIUM — `json-schema-to-typescript` codegen tested by author on similar shapes; verify on first wave that `oneOf` + `const` produces clean TS discriminated unions
- Wizard UX: HIGH — UI-SPEC already locked, no novel UX research needed
- Sidecar lifecycle: HIGH — Tauri docs cover this verbatim; 3× restart count is project decision
- PyInstaller: HIGH — STACK.md already verified versions + flags; PyInstaller Context7 confirms hook functions
- Pitfalls: HIGH — drawn from existing project research + Tauri-specific known issues

**Research date:** 2026-05-12
**Valid until:** 2026-06-12 (30 days — Tauri 2.x is stable, PyInstaller 6.20 stable; no breaking changes expected in window)
