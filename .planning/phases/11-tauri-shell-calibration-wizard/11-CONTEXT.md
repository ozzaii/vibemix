# Phase 11: Tauri Shell + Calibration Wizard - Context

**Gathered:** 2026-05-12
**Status:** Ready for planning
**Mode:** Smart discuss — autonomous; recommendations auto-accepted per `/gsd-autonomous fully`.

<domain>
## Phase Boundary

Phase 11 wraps the `vibemix` Python sidecar in a Tauri 2.x shell (PyInstaller `--onedir`) with documented IPC + WS contracts, and runs a 3-step calibration wizard on first launch on macOS + Windows: permissions → output device + sample-rate test → controller probe.

Owns:
- Tauri 2.x Rust shell + `tauri/ui/` (vanilla TS, no React; lifts mocks/vibemix-app-ui.html token system for visual continuity into Phase 12).
- `externalBin` Python sidecar lifecycle (spawn, watchdog, restart, log capture, exit-code banner).
- IPC contract between Rust shell and Python sidecar via the existing `vibemix.runtime.ws_bus` (port `127.0.0.1:8765`) + a shared JSON Schema source-of-truth at `tauri/ui/src/ipc/messages.schema.json`.
- 3-step calibration wizard UI in `tauri/ui/src/wizard/` with OS-aware flows.
- First-run state at `~/Library/Application Support/vibemix/config.json` (mac) / `%APPDATA%\vibemix\config.json` (win).
- BlackHole detection + one-click install link to existential.audio.

Does NOT own:
- Live session UI shell (Phase 12).
- Reactive mascot (Phase 13 — though wizard reserves a corner slot for it).
- FL-Studio-tier visual polish loop (Phase 14).
- Recording browser (Phase 15).
- Signed/notarized installer (Phase 18).

</domain>

<decisions>
## Implementation Decisions

### Area 1: IPC & Sidecar Architecture

- **IPC protocol:** Reuse `vibemix.runtime.ws_bus` on `127.0.0.1:8765` for Tauri ↔ Python. Tauri shell connects as a WS client; new message types prefixed `ipc.*` (e.g., `ipc.calibration.probe_audio`, `ipc.status.tick`). One bus = one failure mode; mascot.html proves the pattern.
- **Crash recovery:** Tauri shell owns sidecar lifecycle via `externalBin`. Exit-code watchdog with 3× automatic restart attempts, then surfaces "vibemix-core stopped — restart?" banner per success criterion 1. Manual "Restart" button reuses the spawn path.
- **Schema sync:** Single source-of-truth JSON Schema at `tauri/ui/src/ipc/messages.schema.json`. Build-time CI gate: Python `ui_bus/messages.py` dataclass + TypeScript `messages.ts` types both validate against the schema (`scripts/check_ipc_schema.py`). Drift breaks CI.
- **Sidecar logging:** Tauri captures stdout/stderr, writes to rolling file under OS app-data dir (`~/Library/Application Support/vibemix/logs/sidecar.log` mac / `%LOCALAPPDATA%\vibemix\logs\sidecar.log` win). 10MB × 5 rotation. Last error line surfaces in the crash banner.

### Area 2: Calibration Wizard UX Flow

- **Step 1 (Permissions):** OS-aware content, uniform "Step 1/3" header. macOS: Screen Recording deep-link (`tccutil` / `x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture`) + Microphone prompt. Windows: Microphone via standard runtime permission. Both OSes detect permission state after the user returns and auto-advance when granted.
- **Step 2 (Output device + sample-rate test):** Auto-detect headphones (CoreAudio default / WASAPI default) shown as primary selection with "Change…" chevron exposing full dropdown. Auto-play 1kHz sine 1.5s + "Did you hear it?" Yes / Retry. Programmatic guard runs in parallel (`assert_blackhole_rate` mac / `assert_wasapi_loopback_rate` win); both audible + programmatic must pass to advance.
- **Step 3 (Controller probe):** Detected controller name shown ("Pioneer DDJ-FLX4") + "Press any pad or button" with a live 10-second countdown. First MIDI event confirms wiring. Timeout → "Skip — use generic mapping" button registers generic fallback.
- **Wizard exit:** Plays one AI greeting in headphones using the prompts/matrix.py Beginner/Hype template ("yo we're live, deck spins when you are") — satisfies success criterion 3's smoke-test requirement.

### Area 3: First-run State & Window Picker

- **First-run state location:** JSON config file at OS app-config dir — mac `~/Library/Application Support/vibemix/config.json`, win `%APPDATA%\vibemix\config.json`. Schema: `{first_run_completed: bool, calibrated_at: iso8601, output_device_id: str, controller_profile: str, target_dj_app_hint: str|null, target_window_id: str|null, blackhole_install_seen: bool}`. Tauri reads/writes via `tauri-plugin-fs`.
- **Window picker UX:** DJ-app hint list first — auto-detect from running windows in this order: djay Pro, Rekordbox, Serato DJ Pro, Traktor Pro 3, VirtualDJ. If none detected, fall back to "Pick a window" full enumeration with privacy warning ("vibemix only captures the window you pick — never your full screen"). Selection persisted to config.json.
- **Non-DJ app safety:** Warn + allow. If user picks a non-DJ app, show "vibemix works best with DJ software — continue anyway?" dialog; choice logged to events.jsonl for Phase 16 verification harness. Empowers experimentation without nanny-state blocking.
- **Re-run wizard:** One-time on first run, re-runnable via Settings → "Re-run calibration" (Phase 12 surfaces the entry point). Subsequent boots skip wizard if `config.first_run_completed === true` AND all probed assets still resolve (device id, controller name) — on resolution failure, wizard auto-re-runs from the failed step.

### Area 4: BlackHole + Status Badges + Python Pin

- **BlackHole detection:** Look for any device whose name starts with `BlackHole` via `sounddevice.query_devices()`. POC standard is 2ch but accept 16ch / 64ch too (functionally identical — just channel count). If a non-2ch variant is detected, log `blackhole_variant: "16ch"` to events.jsonl for Phase 16 visibility but proceed.
- **BlackHole install flow:** Clickable "Open install page" button opens `https://existential.audio/blackhole` in default browser via `tauri-plugin-shell`. Wizard waits with "Once installed, click Recheck". Recheck re-runs `sounddevice.query_devices()`.
- **Status badges scope (Phase 11):** Define IPC schema (`ipc.status.tick` message with `{livekit: ok|connecting|down, gemini: ok|down, midi: count|null, screen: ok|denied}`) + minimal calibration-step indicators (green check per completed step). Full live-UI badge bar deferred to Phase 12 surface.
- **Python pin:** Already pinned `>=3.12,<3.13` in `pyproject.toml:10` — locked. Phase 11 verifies PyInstaller builds against the same interpreter in CI matrix.

### Claude's Discretion

- Exact Rust crate selection (tauri-plugin-shell vs spawn impl, log rotation crate, JSON schema validator).
- TypeScript / vanilla-JS choice inside `tauri/ui/` — default vanilla TS + Vite (no React; faster build, smaller bundle, mirrors mascot.html aesthetic).
- Wizard step transition animations + token continuity from `mocks/vibemix-app-ui.html` (anodised charcoal + phosphor amber + DSEG7 LCD font + WORKBENCH header + film-grain overlay).
- Asset directory: where the wizard's HTML + CSS + audio (1kHz sine) ship inside the Tauri bundle.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/vibemix/__main__.py` — canonical entry, async orchestrator. Tauri spawns this via `externalBin`.
- `src/vibemix/runtime/ws_bus.py` — existing WS bus on `127.0.0.1:8765` (Phase 4); Tauri shell extends this with `ipc.*` namespace.
- `src/vibemix/audio/` — Levels + features + recording.
- `src/vibemix/platform/` — Protocol firewall; `AudioMacOS` / `AudioWindows` already provide `assert_sample_rate` / device enumeration.
- `src/vibemix/midi/registry.py` + `src/vibemix/midi/watcher.py` — controller detect with 2s hot-plug; Phase 11 wizard step 3 calls `find_mapping_or_generic` after listening.
- `src/vibemix/midi/profiles/*.json` — 10 hand-validated controller JSONs.
- `src/vibemix/prompts/matrix.py` — `HYPE_BEGINNER` template used for wizard-exit AI greeting.
- `mocks/vibemix-app-ui.html` — visual token system to lift (charcoal/amber/DSEG7/WORKBENCH/grain).
- `mascot.html` — proof that WS bus pattern works for cross-process IPC.

### Established Patterns
- Platform firewall via Protocols (Phase 1) — Tauri shell is a NEW process so it doesn't import vibemix at all; only ts-side wraps the IPC schema.
- WS bus at `127.0.0.1:8765` is single bus; new message types added by registration, not by separate ports.
- 10Hz `state_refresh_loop` is the only writer of `MusicState` — wizard probes operate outside this loop (separate async tasks).
- JSON profiles hand-validated (no pydantic dep, Phase 6 / 9 convention) — schema validator written by hand.
- `sounddevice.query_devices()` is the cross-platform device list (Phase 2/7).

### Integration Points
- `python -m vibemix` is what Tauri's `externalBin` invokes.
- Tauri receives WS messages from Python and pushes wizard commands back via the same socket.
- First-run config gates whether Tauri auto-spawns the sidecar or runs the wizard first.

</code_context>

<specifics>
## Specific Ideas

- **Visual continuity with mocks/vibemix-app-ui.html**: The wizard should feel like the live session UI is loading — same anodised charcoal background, phosphor amber accent, DSEG7 LCD for numeric readouts (sample rate, MIDI device count), WORKBENCH header font. Don't introduce a "wizard skin" that diverges from session aesthetic.
- **90-second budget**: Success criterion 3 caps the wizard at <90s on a fresh non-dev macOS box. Means: minimize click count, no marketing copy, no animations longer than 250ms.
- **One AI greeting smoke test at exit**: Required by success criterion 3. Use `HYPE_BEGINNER` template, single-shot through the cascade agent, verifies LLM + TTS + audio output chain end-to-end.
- **Re-run from settings**: Wizard must be re-invokable via a single IPC message `ipc.wizard.start`. Settings panel (Phase 12) wires the button.
- **Mascot corner slot reserved**: Wizard layout reserves bottom-right 256×256 for Phase 13's Avery mascot (not filled in Phase 11 — empty rect is fine).

</specifics>

<deferred>
## Deferred Ideas

- **Live UI badge bar** (UX-11 LiveKit/Gemini/MIDI/Screen badges) — schema defined in Phase 11; visual surface lives in Phase 12.
- **Recording retention controls** — Phase 15 owns Settings panel for retention.
- **Auto-update wiring** — Phase 18 signs the manifest; Phase 11 only stubs the Tauri updater plugin.
- **Linux** — explicitly out of scope per PROJECT.md.
- **Reactive mascot integration** — Phase 13 hooks into the wizard's reserved corner slot.
- **Per-controller learn-mode** (assignable MIDI mappings beyond the 10 curated profiles) — post-v1.

</deferred>
