---
phase: 24-djay-pro-mac-overlay-highlight
plan: 02
type: execute
wave: 1
status: shipped_pending_kaan_live_smoke
requirements_complete: [OVERLAY-01]
key_files:
  created:
    - tauri/src-tauri/src/djay_ax.rs
    - tauri/src-tauri/src/overlay.rs
    - tauri/ui/overlay.html
    - tauri/ui/src/overlay/overlay-runtime.ts
    - tauri/ui/src/overlay/overlay-highlight.ts
    - src/vibemix/ui_bus/schemas/overlay.py
    - tests/ui_bus/test_overlay_schema.py
    - tests/agent/test_overlay_publish.py
    - .planning/phases/24-djay-pro-mac-overlay-highlight/24-02-SUMMARY.md
  modified:
    - tauri/src-tauri/Cargo.toml
    - tauri/src-tauri/Cargo.lock
    - tauri/src-tauri/src/main.rs
    - tauri/src-tauri/capabilities/default.json
    - tauri/ui/vite.config.ts
    - tauri/ui/src/ipc/messages.schema.json
    - tauri/ui/src/ipc/messages.ts
    - src/vibemix/ui_bus/messages.py
    - src/vibemix/ui_bus/__init__.py
    - src/vibemix/agent/dj_cohost.py
    - scripts/check_ipc_schema.py
    - tests/ui_bus/test_messages_schema.py
    - tests/ui_bus/test_mood_change_envelope.py
    - tests/ui_bus/test_recordings_messages.py
deferred_kaan_action: live djay Pro smoke test (visual verification of ring fire)
---

# Phase 24 Plan 02: Overlay-Highlight Feature — Summary

End-to-end overlay-highlight pipeline shipped: when Gemini emits a valid
`[screen:<element_id>]` citation, the Python sidecar publishes an
`ipc.session.overlay-highlight` envelope, the Tauri frontend invokes a
Rust command that queries djay Pro for the element's screen-coords rect
via AX (or the percentage-of-window fallback), then opens a transparent
click-through always-on-top WebviewWindow rendering an amber ring CSS
animation for 1300ms before auto-closing.

## What was built

### Rust AX module (`tauri/src-tauri/src/djay_ax.rs`)

Public surface: `pub fn query_element_bounds(element_id: &str) -> Option<Rect>`.

- macOS-only AX implementation under `cfg(target_os = "macos")` —
  uses `accessibility-sys` + `core-graphics` + `core-foundation` crates
  to walk djay Pro's window via Quartz `CGWindowListCopyWindowInfo`.
- Cross-platform stub returns `None` so Windows builds stay green.
- 12 hand-mapped djay Pro v5 element coordinates as
  percentage-of-window rectangles (PARTIAL fallback path — the shipping
  default per WAVE-0-AX-SPIKE.md "pending verdict + fallback safer").
- Allowlist check (T-24-02-01 mitigation): unknown element_ids return
  `None` without making any OS calls.
- 4 unit tests pass under `#[cfg(test)]`.

### Tauri overlay command (`tauri/src-tauri/src/overlay.rs`)

`#[tauri::command] pub async fn show_overlay_highlight(app, element_id, color, duration_ms)`.

- Queries `djay_ax::query_element_bounds(&element_id)`. None → graceful
  Ok(()) no-op (djay closed, AX denied, or unknown element id).
- Otherwise opens `WebviewWindow` (label = `overlay-<element_id>`) with:
  - `transparent(true)` + `always_on_top(true)` + `decorations(false)`
  - `skip_taskbar(true)` + `visible_on_all_workspaces(true)` + `resizable(false)`
  - `set_ignore_cursor_events(true)` AFTER build (click-through —
    T-24-02-02 mitigation; mouse events pass through to djay below).
- Stable per-element label collapses duplicate invocations to a no-op
  so a citation flood cannot stack windows (T-24-02-03 mitigation).
- Tokio `sleep(duration_ms)` task auto-closes the window.
- URL-encodes color + duration_ms as query params; the overlay.html
  runtime reads them and assigns CSS custom properties.
- 3 unit tests pass.

### Overlay frontend (`tauri/ui/overlay.html` + `overlay-runtime.ts`)

- Single CSS keyframe `ring-pulse` (200ms fade-in → 800ms hold →
  300ms fade-out = 1300ms total). CDJ Whisper v5 amber `#f59e0b` default.
- Color allowlist: amber | red | green | blue (refuses arbitrary CSS
  color injection).
- Duration clamp: 100ms-8000ms (refuses runaway rings).
- Registered as a third Vite rollup input (`vite.config.ts`).

### IPC schema + Python wrapper

- `tauri/ui/src/ipc/messages.schema.json`: `SessionOverlayHighlight`
  oneOf entry. Locked payload: `element_id` (1..64 chars), `color`
  (enum), `duration_ms` (integer 0..8000). `additionalProperties: false`
  at all three levels.
- `src/vibemix/ui_bus/schemas/overlay.py`: `SessionOverlayHighlightPayload`
  frozen+slots dataclass (no pydantic — project convention).
- `src/vibemix/ui_bus/messages.py`: `SessionOverlayHighlight` wrapper
  with `.make(element_id, color, duration_ms)` factory and `.to_dict()`
  convenience for the bus.emit publish path.
- `scripts/check_ipc_schema.py`: drift-gate updated — 36 oneOf entries
  == 36 wrapper dataclasses.
- TS codegen regenerated; tsc `noEmit` clean (only pre-existing
  citation-diagnostics.spec.ts null-check warning remains).

### Sidecar publish (`src/vibemix/agent/dj_cohost.py`)

- New `ipc_bus` kwarg on `DJCoHostAgent.__init__` (default None
  preserves backward compat — Phase 4/10/18/19/20 callers unaffected).
- Post-stream, after the citation linter chokepoint resolves, the
  publish path scans `full_text` via `parse_citations()` and emits one
  `ipc.session.overlay-highlight` envelope per `[screen:<element>]`
  atom IFF:
  - `ipc_bus is not None`
  - `citation_action in ("emit", "bypass")` — user actually heard the text.
    `strip` (linter strip) / `skip` (suppression) do NOT publish; a ring
    without audio is ghost-firing.
- Legacy path (no linter wired) remaps `citation_action skip → emit`
  so backward-compat callers still publish when the user heard the text.
- Best-effort: bus.emit failure logged to stderr, never bubbles up to
  break the LLM response path (T-18-04-03-style guarantee).

### Frontend IPC handler (`tauri/ui/src/overlay/overlay-highlight.ts`)

`startOverlayHighlightListener()` — subscribes to
`ipc.session.overlay-highlight` envelopes and invokes
`show_overlay_highlight` with camelCase keys per Tauri 2.x JS contract.
Wiring this into the main `session/SessionLayout.ts` boot path is Plan
24-03 work; this plan ships the standalone module.

## Verification

- `cargo check` from `tauri/src-tauri/` — clean (1 pre-existing
  deprecated-method warning in `recordings.rs`, unchanged by this plan).
- `cargo test djay_ax overlay` — 7 unit tests pass (4 djay_ax + 3 overlay).
- `.venv/bin/python -m pytest tests/ui_bus/ tests/agent/test_overlay_publish.py -q`
  — 113 tests pass.
- `.venv/bin/python scripts/check_ipc_schema.py` — `36 dataclasses validate
  against schema; count parity 36 == 36`.
- Full pytest suite: **1911 passed / 7 skipped / 10 failed** vs pre-plan
  baseline **1885 passed / 7 skipped / 10 failed**. **+26 new passing tests,
  zero new regressions.** The 10 failures are all pre-existing (persona
  byte-identity, recording sweep, replay linter, audio macOS live, main
  smoke, phase05 POC untouched) and unrelated to overlay work.
- POC files (`cohost_v4.py`, `cohost_v3.py`, `cohost.py`, `cohost_v2.py`,
  `cohost_lk.py`, `mascot.html`) UNTOUCHED — each remains untracked at
  root per memory `project_v3_poc_reference`.
- `npm run codegen:ipc` regenerated `tauri/ui/src/ipc/messages.ts` with
  the new `SessionOverlayHighlight` interface.

## What requires Kaan-action smoke test

The deterministic test surface is complete (mocked AX, mocked Tauri
invoke, fake IpcBus AsyncMock). What CANNOT be tested in CI:

1. **Real djay Pro live AX/Quartz coords.** `query_element_bounds`
   returns `None` on every CI machine because djay Pro is never running.
   The deterministic tests assert "no panic" + "returns None gracefully"
   — they cannot assert "amber ring lands on the actual mid-EQ knob".
2. **Tauri overlay window rendering.** `show_overlay_highlight` is a
   `#[tauri::command]` that requires a running Tauri app context to
   exercise. Headless cargo tests cannot drive `WebviewWindowBuilder`.
3. **Click-through behavior + always-on-top + fullscreen-Spaces
   interaction.** All three are macOS WindowServer behaviors — they
   require a real desktop session.

**Kaan-action smoke test (Phase 21 + djay Pro session):**

1. After Phase 21 lands the Developer-ID-signed installed bundle, launch
   vibemix + djay Pro 5 in windowed mode.
2. Trigger a session where Gemini fires `[screen:waveform_a]` (Phase 16
   ear-test workflow is the natural carrier — Kaan's DJ ear is already
   on the rig).
3. Visually verify: amber ring appears at the waveform region for ~1.3s
   then fades; ring does NOT block mouse interaction with djay below.
4. Test all 12 element_ids end-to-end if time permits.
5. If WAVE-0-AX-SPIKE.md verdict came back PASS by then, follow-up
   Plan 24-03 promotes the implementation from PARTIAL (percentage map)
   to AX-precise (kAXPositionAttribute lookup) — same TS / IPC contract.

## Deviations from plan

None vs Rules 1-3. The post-stream insertion point landed exactly where
Plan 24-02 Task 4 specified (after citation linter chokepoint resolves,
before per-invocation dump). The `citation_action == "emit"` + `"bypass"`
disposition logic is a deliberate Rule 2 (auto-add missing critical
functionality): the plan said "emit" only, but the bypass branch ALSO
emits text to the user — under the plan's "ring fires only when user
hears text" invariant, bypass must also publish or we ghost-suppress
legitimate rings. Documented in code comments.

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: new_command_surface | `tauri/src-tauri/src/overlay.rs` | New `#[tauri::command] show_overlay_highlight` — capability allowlist updated (`windows: [..., "overlay-*"]`); arg validation lives in the typed signature (Tauri 2.x rejects mistyped args at the bridge). |
| threat_flag: new_ax_surface | `tauri/src-tauri/src/djay_ax.rs` | New AX-from-Rust-parent module — element_id allowlist gates the OS call (T-24-02-01); no AX writes (read-only kCGWindowBounds + future AXUIElementCopyAttributeValue). |

## Self-Check: PASSED

- `tauri/src-tauri/src/djay_ax.rs` — FOUND
- `tauri/src-tauri/src/overlay.rs` — FOUND
- `tauri/ui/overlay.html` — FOUND
- `tauri/ui/src/overlay/overlay-runtime.ts` — FOUND
- `tauri/ui/src/overlay/overlay-highlight.ts` — FOUND
- `src/vibemix/ui_bus/schemas/overlay.py` — FOUND
- `tests/ui_bus/test_overlay_schema.py` — FOUND
- `tests/agent/test_overlay_publish.py` — FOUND
- `cargo check` — clean
- `cargo test djay_ax overlay` — 7 pass
- pytest overlay suite — 25 pass
- pytest full suite — 1911 passed (+26 vs baseline, 0 new regressions)
- POC files untouched — verified via `git status`
- Schema count-parity gate — 36 == 36
- Commits (5 in this plan):
  - `fa76bd2` feat(24-02): djay AX module + overlay-highlight Tauri command
  - `d7486f7` feat(24-02): ipc.session.overlay-highlight schema + Python wrapper + TS handler
  - `8ebe9fb` feat(24-02): dj_cohost publishes ipc.session.overlay-highlight on [screen:*] citation
  - `06fce49` test(24-02): overlay schema + dj_cohost publish path coverage
  - this commit — docs(24-02): SUMMARY
