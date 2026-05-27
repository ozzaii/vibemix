# Phase 91: Controller Renderer + MIDI Mirror — Context

**Gathered:** 2026-05-27
**Status:** Ready for planning
**Mode:** Smart discuss (auto-accepted recommended defaults per `gsd-autonomous fully`); decisions cross-checked against `.planning/research/SUMMARY.md` (14 LOCKED axes).

<domain>
## Phase Boundary

P91 ships the **controller renderer + MIDI position mirror** as a *standalone-verifiable artifact*: a DJ plugs in any of the 10 supported MIDI controllers (DDJ-FLX4 / FLX6 / FLX10 / 400 / 1000 / SX3 · XDJ-RX3 · Numark Party Mix Live · Hercules Inpulse 300 / 300-MK2 / 500) and within 2 seconds sees a CDJ-Whisper-styled inline SVG schematic of that exact controller on screen, with every physical control mirroring its current position via incoming MIDI within ≤50 ms P95. A generic fallback (labeled-zone layout) renders when fingerprint confidence is low.

**NO lessons yet. NO AI. NO highlight envelope.** Kaan ear-pass is available the moment this lands (plug controller → see knob move).

**REQ-IDs delivered:** RENDER-01, RENDER-02, RENDER-03, RENDER-05, RENDER-06, RENDER-07. RENDER-04 (highlight paint) is painted-but-tested-in-P92. RENDER-08 (disclaimer copy) lands in P97. RENDER-01 explicitly enumerates 10 SKUs + 1 generic (the Hercules Inpulse 300-MK2 is a distinct profile from the original 300).

**Out of scope (defers):**
- IPC envelopes 1, 2, 3, 4, 5, 7, 8, 9, 10, 11, 12 → Phase 92
- Highlight glow contract + `ipc.learn.highlight` → Phase 92
- Disclaimer copy in app footer + repo README → Phase 97 (RENDER-08)
- ExemplarPlayer + headphone device picker in wizard → P93 + P97
- AI tutor / Gemini wiring → Phase 92+
- Any hand-authored lesson script → Phase 94+

</domain>

<decisions>
## Implementation Decisions

### SVG authoring + style (locked per SUMMARY §5)

- **Source pipeline:** Hand-authored from Pioneer + Numark + Hercules **official hardware-diagram PDFs only** (factual control geometry). NO Pioneer logo. NO Pioneer brand-orange (`#FF7F00` and adjacent); CDJ-Whisper amber accent (`--learn-highlight: var(--cdj-amber-2)` from `tauri/ui/src/lib/tokens.css`). NO photo-lift faceplates. Stylized schematic only — Mixxx-precedent nominative fair use posture.
- **File layout:** 11 inline SVG files at `tauri/ui/src/learn/controllers/<controller_id>.svg.ts` (10 specific + 1 `_generic.svg.ts`), Vite `?raw` string import. Precedent: `tauri/ui/src/wizard/controllers/ddj-flx4.svg.ts`.
- **Aspect ratio:** `viewBox`-driven (no fixed pixel size). Authored to a 1280×720 grid for design parity; SVGs scale to fill the Learn window viewport.
- **Hit regions:** Every interactive control is a `<g data-control-id="<field>">` group. The `<field>` value is the SAME identifier used in `src/vibemix/midi/profiles/<id>.json` (one canonical key per control across SVG ↔ profile ↔ Python binding).

### MIDI position mirror (locked per SUMMARY §4 envelope #6)

- **Push rate:** 30 Hz steady-state push of `ipc.learn.midi_position` (≈33 ms cadence). On rapid input bursts the python sender coalesces deltas inside the 33 ms window. The 30 Hz cap is the bus contract, not a hard ceiling — see contingency below.
- **Update delta:** Only send when the integer LSB of any tracked control changed since last send (delta > 0). Below-LSB jitter on potentiometers is suppressed at the listener; otherwise we'd flood ws:8765 at every micro-twist.
- **Identity:** Each control is keyed `(controller_id, field)` where `field` matches the SVG `data-control-id` AND the `field` value in `midi/profiles/<id>.json`. Single source of truth.
- **State home:** New module `src/vibemix/learn/midi_mirror.py`. Subscribes to `midi/listener.py`'s event stream (same daemon thread that feeds the live co-host — DO NOT add a second listener). Hands a `MidiMirrorSnapshot` dict to the ws_bus writer at the 30 Hz cadence. Read-only from the listener's perspective.
- **Latency contingency (KAAN-ACTION § LEARN-LATENCY-CONTINGENCY):** If `tauri/ui/tests/learn/highlight-latency.test.ts` measures > 80 ms P95 in CI, the contingency in SUMMARY §5 is invoked — Rust-direct `midir` MIDI listener feeding Tauri events directly to the Learn webview, bypassing the Python ws hop. NOT built in P91; flagged for v9.x.

### Window topology + IPC (locked per SUMMARY §5 + Invariant #4)

- **Window:** New `tauri/src-tauri/src/learn_window.rs` — direct mirror of `debrief_window.rs`. Opens on a separate `WebviewWindow` so the user can `Cmd+Tab` between Learn and the live deck. Window title "Learn — vibemix".
- **Socket:** SAME ws:8765 (one-socket invariant `#4` preserved). Existing `ws_bus` is the only producer/consumer; the Learn window opens its own ws client at the same `127.0.0.1:8765`.
- **Envelopes P91 lands:** Exactly 2 — `ipc.learn.controller_detected` (sidecar→shell, single fire per plug-in) and `ipc.learn.midi_position` (sidecar→shell, 30 Hz). The other 10 `ipc.learn.*` envelopes defer to P92. Schema lives at `tauri/ui/src/ipc/messages.schema.json`; MANDATORY `npm run codegen:ipc` after edits (pre-compiled ajv validator).
- **Schema mirror sites:** `src/vibemix/ui_bus/learn_messages.py` (NEW Python dataclasses) + `tauri/ui/src/ipc/messages.schema.json` (JSON Schema) + `tauri/ui/src/ipc/messages.ts` (TS types) + check-parity test `tests/ipc/test_learn_envelope_parity.py`.

### Accessibility + testing (locked per SUMMARY §5 + research/PITFALLS-A11Y)

- **ARIA:** Every `<g data-control-id>` carries `role="button"` + `aria-label` describing the control human-readably (e.g. `aria-label="EQ-HI knob, deck A"` from the same profile binding). Keyboard navigation via `Tab` cycles between groups for hardware-free curriculum browsing.
- **Color-blind cue:** Highlight rendering (P92) will use color (amber) + shape (pulse-ring around the control geometry) — dual-channel cue verified by `tauri/ui/tests/learn/test_a11y_highlight_dual_cue.spec.ts`. P91 lands the ARIA scaffolding + a unit-test stub that asserts every `<g>` has the dual attributes (since the highlight itself is P92, the test is annotated `expect: stub-only` for the actual paint).
- **Latency CI gate:** `tauri/ui/tests/learn/highlight-latency.test.ts` (synthetic harness — fixture MIDI burst + measure DOM update latency). Target 50 ms P95, **fails red at 80 ms P95** which triggers the SUMMARY §5 latency contingency KAAN-ACTION.
- **SVG↔profile parity gate:** `tauri/ui/tests/learn/test_svg_profile_parity.spec.ts` — bidirectional CI gate across all 11 files. Every SVG `data-control-id` resolves to a binding in the matching `midi/profiles/<id>.json` AND every profile binding has a matching `<g>`. Stops schema drift permanently.

### Claude's Discretion

- Exact SVG geometry (Pioneer pad layouts, jog wheel diameter, fader length ratios) within the no-logo/no-faceplate-photo constraints.
- Exact CSS animation curves for the pulse-ring shape (kept off during P91 — there's no highlight ipc yet).
- Internal Python module structure inside `src/vibemix/learn/` (`__init__.py`, `midi_mirror.py`, `__main__.py` if any) — subject to the AGENTS pattern in existing subpackages.
- Test fixture format for the latency harness — must be reproducible and CI-runnable headless.

</decisions>

<code_context>
## Existing Code Insights

### Reusable assets
- `src/vibemix/midi/listener.py` — daemon-thread mido listener; emits typed events. Subscribe (don't fork).
- `src/vibemix/midi/registry.py` — `find_mapping(port_name)` substring-matches the 10 bundled `midi/profiles/<id>.json` against `mido.get_input_names()`.
- `src/vibemix/midi/profiles/*.json` — 10 controller profiles already shipped, single source of truth for `field` identifiers + binding metadata.
- `src/vibemix/runtime/ws_bus.py` — existing `IpcRouterBus`; new dataclasses register here.
- `tauri/ui/src/wizard/controllers/ddj-flx4.svg.ts` — Vite `?raw` inline SVG precedent; the Learn renderer adopts the same import shape.
- `tauri/src-tauri/src/debrief_window.rs` — the precise mirror for `learn_window.rs`.
- `src/vibemix/ui_bus/messages.py` — typed envelope dataclasses; learn_messages.py extends this pattern.
- `tauri/ui/src/ipc/messages.schema.json` + `tauri/ui/src/ipc/validator.generated.mjs` — schema + pre-compiled ajv; codegen needed after edit.
- `tauri/ui/src/lib/tokens.css` — design tokens; amber + warm-black palette already defined.

### Established patterns
- Daemon-thread MIDI + asyncio main loop — cross-thread state via `threading.Lock`. The midi_mirror lives on the same thread as the listener (read-side only) or accepts events through a thread-safe queue.
- All `ipc.*` envelopes ride ws:8765 (one-socket invariant). Python writes via `runtime.ws_bus`; TS consumes via `ui_bus`.
- New `WebviewWindow` is a Tauri pattern; `debrief_window.rs` is the canonical example.
- Frontend tests: `vitest` for unit, `playwright` for spec — `tauri/ui/tests/` layout.
- Backend tests: `pytest -q` from repo root, `PYTHONPATH=src`.

### Integration points
- Python side: hook `midi_mirror.py` into the main session loop (`src/vibemix/__main__.py:main()`) as another long-running task (`stop_event` co-op shutdown pattern). It opens a sender into `runtime.ws_bus` for `ipc.learn.*`.
- Rust side: `learn_window.rs` registered in `tauri/src-tauri/src/main.rs` alongside `debrief_window` (window-open command + command registration).
- TS side: new `tauri/ui/src/learn/` directory — `index.ts`, `controllers/<id>.svg.ts` × 11, `renderer.ts`, `state.ts`, hit-region registry, midi-mirror consumer.

### concurrent-session discipline (CRITICAL)
- 3 Codex + rc1 ship sessions on `live-tuning-or-brain`. Commits by NAMED PATHS only — never `git add -A` or `git add .`. New files under `src/vibemix/learn/` and `tauri/ui/src/learn/` are this session's island; shared files (e.g. `messages.schema.json`, `main.rs`) require careful coordination — solo + sequential edits only.

</code_context>

<specifics>
## Specific Ideas

- The standalone-verifiable artifact bar: plug a DDJ-FLX4 in, the Learn window opens, the FLX4 schematic appears within 2 s, twisting the FLX4's EQ-HI knob moves the on-screen knob within ≤50 ms. Kaan can ear-pass this immediately.
- Latency target 50 ms P95 (well below human flow-state perception). 80 ms P95 = red guardrail (triggers Rust-direct contingency).
- Hercules Inpulse 300 vs 300-MK2 detection: ride forward as `§LEARN-MK2-DETECTION` KAAN-ACTION — for P91, both render the 300 schematic (functionally identical for the rendered controls); SVG parity gate still passes against the 300 profile.

</specifics>

<deferred>
## Deferred Ideas

- Disclaimer copy in app footer + repo README — RENDER-08, **Phase 97**.
- Headphone device picker in onboarding wizard — **Phase 97**.
- `ipc.learn.highlight` envelope + the actual glow render — **Phase 92**.
- AI tutor narration / Gemini wiring — **Phase 92+**.
- ExemplarPlayer + `[exemplar:]` evidence source — **Phase 93**.
- Hercules MK2 specific detection — `§LEARN-MK2-DETECTION` KAAN-ACTION.
- Firmware-variant detection (e.g. DDJ-FLX4 v1.07) — `§LEARN-FIRMWARE-VARIANTS` KAAN-ACTION.
- Live ear-pass on 9 non-FLX4 SKUs — `§LEARN-CONTROLLER-EAR` KAAN-ACTION, parked for **Phase 98**.

</deferred>
