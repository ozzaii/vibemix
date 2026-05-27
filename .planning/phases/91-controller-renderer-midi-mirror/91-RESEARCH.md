# Phase 91: Controller Renderer + MIDI Mirror — Research

**Researched:** 2026-05-27
**Domain:** Tauri WebviewWindow + MIDI mirror loop + inline-SVG renderer + dual-channel a11y scaffolding
**Confidence:** HIGH on engineering spine (every assertion below verified file:line in-tree). MEDIUM on the latency contingency boundary (50 ms target is achievable on the existing path per the live wizard precedent, but the 11×SVG × 30 Hz redraw budget needs first-load verification). LOW only on iSerialNumber availability across the 9 non-FLX4 SKUs (we don't have hardware to test).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**SVG authoring + style:**
- Source: Hand-authored from Pioneer + Numark + Hercules **official hardware-diagram PDFs only**. NO Pioneer logo. NO Pioneer brand-orange (`#FF7F00` and adjacent); CDJ-Whisper amber accent (`var(--amber)` from `tauri/ui/src/tokens.css`). NO photo-lift faceplates. Mixxx-precedent nominative fair use posture.
- File layout: 11 inline SVG files at `tauri/ui/src/learn/controllers/<controller_id>.svg.ts` (10 specific + 1 `_generic.svg.ts`), Vite `?raw` string import. Precedent: `tauri/ui/src/wizard/controllers/ddj-flx4.svg.ts`.
- Aspect ratio: `viewBox="0 0 1280 720"` — no fixed pixel size. SVGs scale to fill the Learn window viewport.
- Hit regions: Every interactive control is a `<g data-control-id="<field>">` group. The `<field>` value is the SAME identifier used in `src/vibemix/midi/profiles/<id>.json`.

**MIDI position mirror:**
- Push rate: 30 Hz steady-state push of `ipc.learn.midi_position` (≈33 ms cadence). Delta-suppressed: only send when integer LSB of any tracked control changed since last send.
- Identity: Each control is keyed `(controller_id, field)` where `field` matches the SVG `data-control-id` AND the `field` value in `midi/profiles/<id>.json`.
- State home: New module `src/vibemix/learn/midi_mirror.py`. Subscribes to existing MIDI listener thread (DO NOT add a second listener). Hands a `MidiMirrorSnapshot` dict to the ws_bus writer at the 30 Hz cadence. Read-only from listener's perspective.
- Latency contingency `§LEARN-LATENCY-CONTINGENCY`: if `tauri/ui/tests/learn/highlight-latency.test.ts` measures > 80 ms P95 in CI, Rust-direct `midir` MIDI listener is invoked — NOT in P91; flagged for v9.x.

**Window topology + IPC:**
- Window: New `tauri/src-tauri/src/learn_window.rs` — direct mirror of `debrief_window.rs`. Separate `WebviewWindow` so user can `Cmd+Tab` between Learn and live deck. Window title `"Learn — vibemix"`.
- Socket: SAME ws:8765 (one-socket invariant `#4` preserved).
- Envelopes P91 lands: EXACTLY 2 — `ipc.learn.controller_detected` + `ipc.learn.midi_position`. Other 10 `ipc.learn.*` envelopes DEFER TO P92.
- Schema mirror sites (NEW): `src/vibemix/ui_bus/learn_messages.py` (Python dataclasses) + `tauri/ui/src/ipc/messages.schema.json` (JSON Schema additions) + `tauri/ui/src/ipc/messages.ts` (TS types, auto-regenerated) + `tests/ipc/test_learn_envelope_parity.py` (NEW parity test).
- MANDATORY post-edit: `cd tauri/ui && npm run codegen:ipc`.

**Accessibility + testing:**
- ARIA: Every `<g data-control-id>` carries `role="button"` + `aria-label` (e.g. `aria-label="EQ-HI knob, deck A"`).
- Dual-channel cue scaffolding: Each `<g>` has TWO empty child slots `<g class="cue-color"></g>` + `<g class="cue-shape"></g>`. P91 ships the slots — the actual highlight paint is P92.
- Latency CI gate: `tauri/ui/tests/learn/highlight-latency.test.ts` — synthetic harness, target 50 ms P95, FAILS RED at 80 ms P95.
- SVG↔profile parity gate: `tauri/ui/tests/learn/test_svg_profile_parity.spec.ts` — bidirectional across all 11 files.

### Claude's Discretion

- Exact SVG geometry (pad layouts, jog-wheel diameter, fader length ratios) within the no-logo/no-faceplate-photo constraints.
- Exact CSS animation curves for the pulse-ring shape (kept off during P91 — no highlight ipc yet).
- Internal Python module structure inside `src/vibemix/learn/` (`__init__.py`, `midi_mirror.py`, etc.) — subject to existing-subpackage AGENTS pattern.
- Test fixture format for the latency harness — must be reproducible and CI-runnable headless.

### Deferred Ideas (OUT OF SCOPE)

- IPC envelopes 1, 2, 3, 4, 5, 7, 8, 9, 10, 11, 12 → **Phase 92**
- Highlight glow contract + `ipc.learn.highlight` → **Phase 92**
- Disclaimer copy in app footer + repo README → **Phase 97** (RENDER-08)
- ExemplarPlayer + headphone device picker in wizard → **P93** + **P97**
- AI tutor / Gemini wiring → **Phase 92+**
- Any hand-authored lesson script → **Phase 94+**
- Hercules MK2 specific detection — `§LEARN-MK2-DETECTION` KAAN-ACTION (P91 ships 300 schematic for both; MK2 detection deferred)
- DDJ-FLX4 firmware variants — `§LEARN-FIRMWARE-VARIANTS` KAAN-ACTION
- Live ear-pass on 9 non-FLX4 SKUs → `§LEARN-CONTROLLER-EAR` KAAN-ACTION, **Phase 98**

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| **RENDER-01** | A DJ plugs MIDI controller, sees CDJ-Whisper SVG schematic of that exact controller within 2s. 10 supported + 1 generic fallback. Auto-detect via `mido.get_input_names()` + `midi/registry.find_mapping`. | §Standard Stack (mido + registry exists), §Architecture Pattern 1 (controller_detected envelope from port_watcher), §Code Examples §1. |
| **RENDER-02** | Every physical control mirrors current position via MIDI within ≤50 ms P95 latency, measured by `tauri/ui/tests/learn/highlight-latency.test.ts`. Fails red at 80 ms P95 (triggers §LEARN-LATENCY-CONTINGENCY Rust-direct amendment). | §Architecture Pattern 2 (30 Hz coalescing mirror loop), §Common Pitfalls Pitfall 2 (PROPRIOCEPTIVE-LATENCY), §Code Examples §3 (latency-measurement harness shape). |
| **RENDER-03** | Every rendered control has `<g data-control-id="<field>">` hit region with ARIA `role="button"` + `aria-label`; keyboard navigation works for hardware-free curriculum browsing. | §Architecture Pattern 4 (aria-label lookup table), §A11Y test gate `test_aria_labels_present.spec.ts`. |
| **RENDER-05** | Highlights use dual-channel cue (color + shape) — not amber-only; verified by `test_a11y_highlight_dual_cue.spec.ts`. **P91 lands scaffolding only**; actual paint = P92. | §Architecture Pattern 5 (cue-color + cue-shape empty slot pattern). Annotated `expect: stub-only` for the paint itself. |
| **RENDER-06** | Every SVG controller file passes bidirectional CI parity gate against its MIDI profile JSON (`test_svg_profile_parity.spec.ts`). | §Architecture Pattern 6 (bidirectional parity), §Test Layout §SVG↔Profile parity gate. |
| **RENDER-07** | Learn surface runs in SEPARATE `WebviewWindow` (mirror of `debrief_window.rs`); user can Cmd+Tab between Learn and deck; both share SAME ws:8765 (one-socket invariant). | §Standard Stack §Tauri (`WebviewWindow` precedent in `debrief_window.rs`), §Architecture Pattern 7 (full mirror diff), §Code Examples §2. |

</phase_requirements>

## Project Constraints (from CLAUDE.md)

| Directive | Source | How P91 Honors |
|-----------|--------|----------------|
| **One-socket invariant (#4)** | CLAUDE.md §Architecture | Two new envelopes ride ws:8765 — no second `websockets.serve`. CI gate: `tests/learn/test_no_new_ws_port.py`. |
| **Single-writer invariant (#1)** | CLAUDE.md §Architecture | `LearnState`-equivalent surface for P91 is read-only — `MidiMirror` only READS `ControllerState.deck_snapshot()` + `events_since()`. NEVER writes `MusicState`. |
| **No model literals — `model_router` only** | CLAUDE.md §Configuration | N/A in P91 (no AI calls). |
| **Frontend settings controls must repaint OPTIMISTICALLY** | CLAUDE.md §Conventions | N/A in P91 (no settings controls in Learn window for now; `state.ts` pub/sub gap is in the live-deck session loop, not Learn). |
| **`codegen:ipc` mandatory after schema edit** | CLAUDE.md §Commands | `npm run codegen:ipc` is a REQUIRED step after the messages.schema.json edit in P91. Plan must include it. |
| **`cargo tauri dev` = STALE frozen sidecar** | CLAUDE.md §Commands | Verify backend wiring by running `main()` on current source — bundled Python sidecar in `cargo tauri dev` is FROZEN. For P91, `learn_window.rs` is a Rust change and DOES get rebuilt by `cargo tauri dev`; but the Python `midi_mirror.py` does NOT. Use `python -m vibemix` directly to verify the Python side; Tauri-command surfaces via `tsc --noEmit` + `vite build` + `vitest run`. |
| **Concurrent sessions on `live-tuning-or-brain`** | CLAUDE.md §Project Skills + CONTEXT.md §code_context | Commit by NAMED paths only. Shared-file edits (`messages.schema.json`, `main.rs`) must be solo+sequential. New-file islands at `src/vibemix/learn/`, `tauri/ui/src/learn/`, `tauri/src-tauri/src/learn_window.rs`. |
| **Apache-clean: no Pioneer logo, no orange, no photo-lift** | CLAUDE.md §Constraints + UI-SPEC.md §Asset Pipeline | CI gate: `test_no_pioneer_orange.spec.ts` (greps for `#ff7f00` and neighbors in `learn/**.svg.ts`). |
| **Frontend-enforcement skill rule 2 (20/80)** | `.claude/skills/frontend-enforcement/SKILL.md` | UI-SPEC §Color hardcaps amber to 5 elements in P91. The schematic strokes are silk-22 (dominant); amber is reserved for the title under-stroke + the eventual highlight (P92). |
| **Frontend-enforcement skill rule 4 (forbidden fonts)** | `.claude/skills/frontend-enforcement/SKILL.md` | Saira + JetBrains Mono — already vendored in `tauri/ui/public/fonts/`. No Inter / Roboto / Arial. |
| **CodeGen sync — pre-compiled ajv validator** | `feedback_schema_edit_needs_codegen_ipc.md` | Plan MUST include `npm run codegen:ipc` as a discrete step after `messages.schema.json` edit. Tests will reject new envelope shapes without it. |

## Summary

P91 is a **standalone-verifiable artifact**: plug a DDJ-FLX4, see a CDJ-Whisper SVG schematic of the FLX4 appear in a separate Tauri window within 2s, and watch every physical knob/fader/button mirror its current position via incoming MIDI within ≤50 ms P95. **NO lessons. NO AI. NO highlight envelope.** Kaan ear-pass is available the moment this lands — the contract is "see your hardware on screen, responsive to your touch."

The technical lift is small but precise: **2 new Python files** (`learn/__init__.py`, `learn/midi_mirror.py`), **1 new Python schema-mirror file** (`ui_bus/learn_messages.py`), **11 new TS controller SVG files** (`tauri/ui/src/learn/controllers/<id>.svg.ts`), **3 new TS frontend files** (`learn-window.ts` + 2 helper components), **1 new HTML entry** (`tauri/ui/learn.html`), **1 new Rust window-spawn module** (`learn_window.rs` mirroring `debrief_window.rs`), **2 new envelope shapes** in `messages.schema.json`, **3 lines added to `main.rs`** (mod registration + command registration + handle manage), **3 lines added to `vite.config.ts`** (5th HTML entry point). The acid test: every file lands inside `src/vibemix/learn/` or `tauri/ui/src/learn/` or `tauri/src-tauri/src/learn_window.rs` — three new-file islands, zero modifications to existing engines, no second ws port, no second AI provider.

**Primary recommendation:** Adopt the **mirror-of-debrief_window.rs** pattern verbatim for the Tauri Rust side (Pattern 7 below); subscribe to the EXISTING `midi/listener.py` daemon thread via a shared queue (Pattern 2) rather than forking a second listener; drive the 30 Hz `midi_position` push from `runtime/ws_bus.py`'s outer broadcast loop (Pattern 2 §coalescing) rather than introducing a new async task; auto-generate the 11 `aria-label` strings from `midi/profiles/<id>.json` (Pattern 4) so the SVG↔profile parity gate becomes a 1:1 check.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| MIDI port enumeration + hot-plug detection | **Python sidecar** (`midi/watcher.py`) | — | Existing `port_watcher_task` polls `mido.get_input_names()` at 2 Hz. We REUSE — no second polling loop. |
| MIDI message decode (CC → field semantic) | **Python sidecar** (`midi/state.py::ControllerState`) | — | Existing `handle_msg` (FLX4 golden, byte-equivalent to v4). The Learn mirror SUBSCRIBES (read-only) — never decodes itself. |
| 30 Hz position-snapshot coalescing + delta suppression | **Python sidecar** (`learn/midi_mirror.py` — NEW) | — | Single-writer for `learn.midi_position` envelopes. Reads from the shared `ControllerState`; coalesces inside the 33 ms window. |
| Controller detection event emission | **Python sidecar** (`learn/midi_mirror.py` + `port_watcher` callback) | — | The existing port watcher's `on_change` callback signals connect/disconnect; midi_mirror translates into `ipc.learn.controller_detected` envelope. |
| WS bus serve (one socket) | **Python sidecar** (`runtime/ws_bus.py::ws_broadcast`) | — | Existing `IpcRouterBus` adapter; midi_mirror emits via the SAME `_send_all` path the snapshot broadcast uses. |
| Learn window spawn + lifecycle | **Rust shell** (`tauri/src-tauri/src/learn_window.rs` — NEW) | — | Mirror of `debrief_window.rs`. NO Python sidecar process spawn (Learn is a passive frontend window — there's only one Python sidecar process, shared). |
| Learn frontend rendering (SVG mount + position update) | **Browser webview** (`tauri/ui/src/learn/*.ts` — NEW) | — | Inline-SVG via Vite `?raw` import. CSS `transform` + attribute mutations only (no full SVG repaint). |
| WS client for the Learn webview | **Browser webview** (`tauri/ui/src/learn/ws-client.ts` — NEW; mirror of `debrief/ws-client.ts`) | — | Connects to `ws://127.0.0.1:8765` from the Learn webview (a 2nd WebSocket client, but on the SAME ws server — invariant #4 preserved). |
| Schema validation (round-trip) | **Python sidecar** (`ui_bus/validator.py`) + **Webview** (ajv standalone via `validator.generated.mjs`) | — | Two-sided gate. Both wrappers added in P91. |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `mido` | already pinned in `pyproject.toml` | MIDI port enumeration + message decode (existing daemon thread) | Standard for Python MIDI on macOS+Windows; rtmidi backend handles platform-specific quirks. |
| `python-rtmidi` | already pinned | Native MIDI backend for `mido` | Default mido backend; no alternative needed. |
| `jsonschema` (Draft-07) | already pinned | Python-side envelope validation | Existing pattern in `ui_bus/messages.py`; reused verbatim. |
| `websockets` | already pinned | ws:8765 (one socket) | Existing pattern in `runtime/ws_bus.py`; not added. |
| `tauri` | 2.x (already in `Cargo.toml`) | `WebviewWindow` creation | Existing pattern in `debrief_window.rs`. |
| `ajv` | ^8.20 (already in `tauri/ui/package.json`) | Frontend ipc validation | Pre-compiled via `npm run codegen:ipc` — existing pattern, no new dep. |
| `vite` | ^6.0 (already in `tauri/ui/package.json`) | `?raw` SVG import | Built-in Vite feature; no plugin needed. |
| `vitest` | ^2.1 (already in `tauri/ui/package.json`) | Unit + integration test runner (latency harness, parity gate) | Existing test pattern; matches `tauri/ui/tests/wizard/step0-intro.spec.ts` shape. |

**ZERO new dependencies in P91.** Every library above is already pinned in `pyproject.toml` / `package.json` / `Cargo.toml` and has been in production since Phase 11.

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `playwright` | ^1.50 (already in `tauri/ui/package.json`) | Visual regression / DOM-walk a11y tests | If the latency harness or a11y tests need a real DOM at scale. The synthetic harness in `vitest` is preferred for the latency CI gate; playwright is reserved for the keyboard-nav order test (`test_keyboard_nav_order.spec.ts`). |
| `axe-core` | already vendored via `tauri/ui/tests/visual/` precedent | Accessibility audit (color contrast gate) | `test_contrast_ratios.spec.ts` — axe-core run on the Learn window. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Inline SVG via Vite `?raw` | `<img src="...svg">` raster | Loses `data-control-id` hit regions; can't CSS-target individual paths for highlights. **REJECTED — locked in SUMMARY §5.** |
| Inline SVG via Vite `?raw` | Canvas/WebGL | Repaint cost on every MIDI update + no DOM hit regions + harder accessibility. **REJECTED — locked.** |
| New ws:8767 for Learn-only traffic | One-socket on ws:8765 | Two listeners contend on the same loopback interface (Linux-only oddity, but also breaks the live deck contract). **REJECTED — invariant #4.** |
| Forking a second `mido.open_input` listener for Learn | Subscribe to the existing `ControllerState` | Two listeners can't bind the same port on most platforms — they'd compete or one would fail. **REJECTED — locked in CONTEXT.md.** |
| Python `python-statemachine` for MIDI mirror | Plain stateful coroutine | FSM library is overkill for "is there a port? is it bound? what was the last sent snapshot?". `python-statemachine` lands in P92 for the LESSON runtime, not P91. **REJECTED for P91 — appropriate scoping.** |
| Tauri events (`app.emit`) for `midi_position` push | ws frames | Tauri events bypass the schema validator + Python single-writer; would require Rust to decode MIDI itself. **REJECTED — would split the source of truth.** |

**Installation:**
```bash
# Nothing new to install. P91 uses 100% existing dependencies.
# Verify by running:
cd tauri/ui && npm test  # vitest existing
PYTHONPATH=src python3 -m pytest -q tests/midi/  # existing midi tests pass
```

**Version verification:**
```bash
# Python (existing, no install):
grep -E "(mido|python-rtmidi|websockets|jsonschema)" pyproject.toml

# JS (existing, no install):
grep -E "(ajv|vite|vitest)" tauri/ui/package.json
```

All packages verified `[VERIFIED: in-tree, already shipping]`.

## Package Legitimacy Audit

> **N/A — P91 installs ZERO new packages.** Every library used is already pinned in `pyproject.toml` / `tauri/ui/package.json` / `Cargo.toml` and has been in production since prior phases. The slopcheck gate doesn't apply because there is no new install to verify.

| Package | Registry | Disposition |
|---------|----------|-------------|
| `mido` | PyPI | Pre-existing — no change |
| `python-rtmidi` | PyPI | Pre-existing — no change |
| `tauri` (Rust crate) | crates.io | Pre-existing — no change |
| `vite` | npm | Pre-existing — no change |
| `vitest` | npm | Pre-existing — no change |
| `ajv` | npm | Pre-existing — no change |

If the planner later proposes a new dep (e.g. for the latency harness), the Package Legitimacy Gate MUST run before that install lands. For P91 as scoped, no slopcheck invocation is required.

## Architecture Patterns

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Rust shell (tauri/src-tauri/src/)                                            │
│                                                                              │
│  main.rs:                                                                    │
│    mod learn_window;                       ← NEW (1 line)                    │
│    .invoke_handler(generate_handler![      ← +1 entry                        │
│       learn_window::open_learn_window,                                       │
│    ])                                                                        │
│    .manage(LearnSidecarHandle::default())  ← NO — learn shares sidecar       │
│                                                                              │
│  learn_window.rs (NEW, mirror of debrief_window.rs):                         │
│    pub const LEARN_WINDOW_LABEL: &str = "learn";                             │
│    pub async fn open_learn_window(app: AppHandle) {                          │
│      // mostly verbatim debrief_window.rs minus:                             │
│      //   - sidecar spawn (we share the main sidecar; no --learn flag)       │
│      //   - session_dir validation (no per-session path)                     │
│      //   - DebriefDeepLink (no deep-link payload)                           │
│      let url = "learn.html";                                                 │
│      WebviewWindowBuilder::new(&app, LEARN_WINDOW_LABEL, url.into())         │
│        .title("Learn — vibemix")                                             │
│        .inner_size(1280.0, 720.0).min_inner_size(960.0, 540.0)               │
│        .resizable(true).decorations(true).build()                            │
│    }                                                                         │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │ spawn WebviewWindow
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Learn webview (tauri/ui/learn.html + src/learn/)                             │
│                                                                              │
│  learn-window.ts:                                                            │
│    1. parse URLSearchParams (none in P91 — empty for now)                    │
│    2. mount LearnWsClient(8765) — same port as session                       │
│    3. on "learn.controller_detected": LOAD_SVG(controller_id) into stage     │
│    4. on "learn.midi_position": for each (field, value) → UPDATE_DOM         │
│                                                                              │
│  ws-client.ts (mirror of debrief/ws-client.ts):                              │
│    new WebSocket("ws://127.0.0.1:8765")                                      │
│    onmessage → ajv validate → CustomEvent(type) dispatch                     │
│                                                                              │
│  controllers/<id>.svg.ts × 11:                                               │
│    export const PIONEER_DDJ_FLX4_SVG = `<svg viewBox="0 0 1280 720" ...>     │
│      <g data-control-id="eq_low_a" role="button"                             │
│         aria-label="EQ-LOW knob, deck A">                                    │
│        <circle cx="..." cy="..." r="32" stroke="currentColor" .../>          │
│        <g class="cue-color"></g>                                             │
│        <g class="cue-shape"></g>                                             │
│      </g>                                                                    │
│      ...                                                                     │
│    </svg>` ;                                                                 │
└──────────────────────────────────▲──────────────────────────────────────────┘
                                   │
                                   │ ws://127.0.0.1:8765 (the ONLY socket)
                                   │ frames:
                                   │   ipc.learn.controller_detected (1× per plug)
                                   │   ipc.learn.midi_position (30 Hz, delta-suppressed)
                                   │
┌──────────────────────────────────┴──────────────────────────────────────────┐
│ Python sidecar (src/vibemix/)                                                │
│                                                                              │
│  runtime/ws_bus.py (EXISTING — no change beyond wiring):                     │
│    ws_broadcast() loop. Already emits 30 Hz mascot frame + 15 Hz snapshot.   │
│    We ADD: pull from MidiMirror.snapshot() inside the same 30 Hz tick;       │
│    emit only when delta_changed = True. Pure outbound additive.              │
│                                                                              │
│  learn/midi_mirror.py (NEW, ~150 lines):                                     │
│    class MidiMirror:                                                         │
│      def __init__(self, controller_state, profile):                          │
│        self.cs = controller_state            ← read-only reference           │
│        self.profile = profile                ← read-only reference           │
│        self._last_snapshot: dict = {}        ← integer LSB cache             │
│      def snapshot(self) -> dict | None:                                      │
│        # called from ws_broadcast tick at 30 Hz                              │
│        cur = self._read_current_positions()                                  │
│        delta = self._integer_lsb_delta(cur, self._last_snapshot)             │
│        if not delta:                                                         │
│          return None                                                         │
│        self._last_snapshot = cur                                             │
│        return LearnMidiPosition.make(                                        │
│          controller_id=self.profile.id,                                      │
│          positions=cur,                                                      │
│        ).to_dict()                                                           │
│                                                                              │
│  port_watcher (EXISTING) → on connect/disconnect:                            │
│    callback fires → emit LearnControllerDetected envelope ONCE               │
│                                                                              │
│  midi/listener.py (EXISTING — UNTOUCHED):                                    │
│    daemon thread. handle_msg() decodes into ControllerState.deck/xfader.     │
│    ↑                                                                         │
│    MidiMirror.snapshot() reads from this without locking the listener.       │
│    (ControllerState.deck_snapshot() already lock-guards the read.)           │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Recommended Project Structure

```
src/vibemix/
├── learn/                        # NEW — P91 island
│   ├── __init__.py               # exports MidiMirror + small surface
│   └── midi_mirror.py            # MidiMirror class + helpers
└── ui_bus/
    └── learn_messages.py         # NEW — dataclasses for the 2 envelopes

tauri/ui/
├── learn.html                    # NEW — 5th webview entry
└── src/
    └── learn/                    # NEW — P91 island
        ├── learn-window.ts       # entrypoint, mirrors debrief/debrief-window.ts
        ├── ws-client.ts          # mirrors debrief/ws-client.ts
        ├── controllers/          # 11 inline-SVG modules
        │   ├── _generic.svg.ts
        │   ├── _aria-labels.ts   # field → human label lookup
        │   ├── pioneer_ddj_flx4.svg.ts
        │   ├── pioneer_ddj_flx6.svg.ts
        │   ├── pioneer_ddj_flx10.svg.ts
        │   ├── pioneer_ddj_400.svg.ts
        │   ├── pioneer_ddj_1000.svg.ts
        │   ├── pioneer_ddj_sx3.svg.ts
        │   ├── pioneer_xdj_rx3.svg.ts
        │   ├── numark_party_mix_live.svg.ts
        │   ├── hercules_inpulse_300.svg.ts
        │   └── hercules_inpulse_500.svg.ts
        └── components/
            ├── controller-stage.ts    # SVG mount + position update
            ├── empty-state.ts         # "no controller detected"
            ├── status-bar.ts          # latency probe + status pip
            └── unplugged-toast.ts     # mid-session disconnect

tauri/src-tauri/src/
└── learn_window.rs                    # NEW — full mirror of debrief_window.rs

tauri/ui/src/ipc/
└── messages.schema.json               # EDIT — add 2 oneOf entries

tests/learn/                           # NEW
├── __init__.py
├── test_midi_mirror_unit.py           # MidiMirror.snapshot() + delta logic
├── test_no_new_ws_port.py             # grep-gate for learn/ (zero websockets.serve)
└── test_no_pioneer_brand_marks.py     # grep for "Pioneer DJ" / #FF7F00 in SVGs

tests/ipc/
└── test_learn_envelope_parity.py      # NEW — 2 envelopes round-trip

tauri/ui/tests/learn/                  # NEW
├── highlight-latency.test.ts          # 50ms target, 80ms red guardrail
├── test_svg_profile_parity.spec.ts    # bidirectional 11-file gate
├── test_aria_labels_present.spec.ts   # every <g> has role + aria-label
├── test_dual_cue_slots_present.spec.ts # cue-color + cue-shape slots
├── test_keyboard_nav_order.spec.ts    # Tab cycles control groups
├── test_contrast_ratios.spec.ts       # axe-core run on Learn window
├── test_no_pioneer_orange.spec.ts     # grep #FF7F00 / Pioneer in SVG strings
├── test_svg_currentcolor_only.spec.ts # no hex inside SVG bodies
└── test_sr_announcement.spec.ts       # aria-live polite on detection
```

### Pattern 1: Controller Detection Envelope (single fire per plug)

**What:** `ipc.learn.controller_detected` envelope, emitted once per port-bind / unbind event.

**When to use:** P91 uses this exactly twice in a normal session — once on `('connected', port, profile)` from `port_watcher_task`, once on `('disconnected', port)`. The frontend uses it to swap in the right SVG (or `_generic` on no-match).

**Wire shape:**
```json
{
  "type": "ipc.learn.controller_detected",
  "ts": "2026-05-27T22:48:00Z",
  "payload": {
    "connected": true,
    "controller_id": "pioneer_ddj_flx4",
    "display_name": "Pioneer DDJ-FLX4",
    "port_name": "DDJ-FLX4 USB MIDI Input"
  }
}
```

On disconnect:
```json
{
  "type": "ipc.learn.controller_detected",
  "ts": "...",
  "payload": {
    "connected": false,
    "controller_id": "pioneer_ddj_flx4",
    "display_name": "Pioneer DDJ-FLX4",
    "port_name": "DDJ-FLX4 USB MIDI Input"
  }
}
```

**Wired into existing infrastructure:**
- Source: existing `MidiMacOS.start_port_watcher` callback (via `handle_port_change_single_state`). We wrap a thin emission adapter around the existing on_change tuple.
- Emit: `IpcRouterBus.emit({...})` (the `_send_all` coroutine in `ws_broadcast`).
- Generic-fallback: when `find_mapping(port_name)` returns the synthesized generic profile (per `registry.find_mapping_or_generic`), `controller_id = "_generic"` and `display_name = "Unknown Controller"`.

### Pattern 2: 30 Hz Coalesced MIDI Position Push

**What:** `ipc.learn.midi_position` envelope, pushed at 30 Hz **with delta suppression** — only emit when at least one tracked control's integer LSB changed since last send.

**Wire shape:**
```json
{
  "type": "ipc.learn.midi_position",
  "ts": "...",
  "payload": {
    "controller_id": "pioneer_ddj_flx4",
    "positions": {
      "eq_hi:A": 64, "eq_mid:A": 64, "eq_low:A": 64, "vol:A": 0, "filter:A": 64, "tempo:A": 64,
      "eq_hi:B": 64, "eq_mid:B": 64, "eq_low:B": 64, "vol:B": 0, "filter:B": 64, "tempo:B": 64,
      "xfader": 64,
      "play:A": 0, "cue:A": 0, "sync:A": 0, "jog_touched:A": 0,
      "play:B": 0, "cue:B": 0, "sync:B": 0, "jog_touched:B": 0
    }
  }
}
```

**Key encoding:** `"<field>:<deck>"` for deck-bound controls; bare `"<field>"` for master-section (xfader). Each value is integer 0..127 (MIDI native) or 0/1 for boolean buttons.

**Why integer 0..127, not float [0,1]:** the LSB delta is the suppression gate. Floating-point would either lose precision (lossy) or trip false-positive deltas (re-emitting on f64 rounding noise). Integer LSB is what mido already gives us — exactly the natural unit.

**Wired into existing infrastructure:**
- **Source:** the existing daemon-thread `ControllerState` mutated by `midi/state.py::handle_msg`. `ControllerState.deck_snapshot()` is already lock-guarded (`threading.Lock` in `state.py:144`) and is exactly the read API midi_mirror needs.
- **Coalescing host:** the existing `runtime/ws_bus.py::ws_broadcast` 30 Hz loop. Lines 462-end iterate at 1/30 s. We add ONE method call inside: `_maybe_emit_learn_position(state, midi_mirror, last_send_ts)`. The mascot frame's 30 Hz cadence and shape stay untouched (pinned by `test_ws_07`).
- **Emit path:** the same `_send_all` coroutine `ws_broadcast` uses for `ipc.session.snapshot`.

**Single-writer:** Only `midi_mirror.py` writes `learn.midi_position` envelopes. The listener thread is read-only from our perspective; we just snapshot its `ControllerState` at 30 Hz.

### Pattern 3: SVG Hit Regions + `data-control-id` Convention

**What:** every interactive element in every controller SVG is wrapped in:

```html
<g data-control-id="<field>:<deck>"
   role="button"
   aria-label="EQ-LOW knob, deck A"
   tabindex="0">
  <!-- factual geometry from manufacturer PDF -->
  <circle cx="..." cy="..." r="32"
          stroke="currentColor" stroke-width="1.5" fill="none"/>
  <!-- empty dual-cue slots (P91 scaffolding for P92 highlight) -->
  <g class="cue-color"></g>
  <g class="cue-shape"></g>
</g>
```

**The `data-control-id` value is the EXACT same string** used:
1. In `src/vibemix/midi/profiles/<id>.json::controls.*.field` (and deck suffix from `controls.*.deck`).
2. In the `ipc.learn.midi_position` envelope's `positions` keys.
3. In the `_aria-labels.ts` lookup table.

This is the **single source of truth** for control identity across SVG ↔ profile ↔ Python ↔ TS. The bidirectional parity gate (Pattern 6) enforces it.

**Encoding rule:** `"<field>:<deck>"` for deck-bound; bare `"<field>"` for master-section. Mirrors the wire format.

### Pattern 4: ARIA Label Lookup (Auto-Generated from Profile)

**What:** A hand-written `_aria-labels.ts` lookup keyed on `(field, deck)`:

```typescript
// tauri/ui/src/learn/controllers/_aria-labels.ts
// Hand-authored once; covers every (field, deck) pair the 11 profiles use.
export const ARIA_LABELS: Record<string, string> = {
  "eq_hi:A": "EQ-HI knob, deck A",
  "eq_hi:B": "EQ-HI knob, deck B",
  "eq_mid:A": "EQ-MID knob, deck A",
  "eq_mid:B": "EQ-MID knob, deck B",
  "eq_low:A": "EQ-LOW knob, deck A",
  "eq_low:B": "EQ-LOW knob, deck B",
  "vol:A": "channel fader, deck A",
  "vol:B": "channel fader, deck B",
  "tempo:A": "pitch fader, deck A",
  "tempo:B": "pitch fader, deck B",
  "filter:A": "filter knob, deck A",
  "filter:B": "filter knob, deck B",
  "xfader": "crossfader",
  "play:A": "play button, deck A",
  "play:B": "play button, deck B",
  "cue:A": "cue button, deck A",
  "cue:B": "cue button, deck B",
  "sync:A": "sync button, deck A",
  "sync:B": "sync button, deck B",
  "jog_touched:A": "jog wheel, deck A",
  "jog_touched:B": "jog wheel, deck B",
  "loop_in:A": "loop-in button, deck A",
  "loop_in:B": "loop-in button, deck B",
  "loop_out:A": "loop-out button, deck A",
  "loop_out:B": "loop-out button, deck B",
  // ...add hotcue:A:1..8 / filter_fx / tap_tempo as 9 Wave-2 profiles need them
};
```

**Parity gate:** `test_svg_profile_parity.spec.ts` asserts that every `data-control-id` in every SVG has a key in `ARIA_LABELS`, and every key in `ARIA_LABELS` is referenced by at least one SVG.

### Pattern 5: Dual-Channel Cue Scaffolding (slots only, no paint in P91)

**What:** Every `<g data-control-id>` carries TWO empty child slots:

```html
<g data-control-id="eq_hi:A" ...>
  <!-- factual geometry -->
  <circle .../>
  <!-- dual-cue scaffolding (P91 ships empty; P92 lights them) -->
  <g class="cue-color"></g>
  <g class="cue-shape"></g>
</g>
```

**P92 contract (defer, but design for):**
- `cue-color` will receive a `<circle>` or `<rect>` with `fill="var(--learn-highlight)"` — the color channel.
- `cue-shape` will receive a `<circle>` with stroke + stroke-width + dasharray for the pulse-ring — the shape channel.
- Both light at once on `ipc.learn.highlight` (P92), giving dual-channel a11y per WCAG color-blind guidance (Pitfall 11).

**P91 test:** `test_dual_cue_slots_present.spec.ts` — annotated `expect: stub-only`. Asserts every `<g data-control-id>` has the two empty child slots in DOM order. The actual paint test (`test_a11y_highlight_dual_cue.spec.ts`) ships in P92.

### Pattern 6: Bidirectional SVG↔Profile Parity Gate

**What:** CI gate that, for each of the 11 profiles, asserts:

1. **Forward:** every `controls.*` field + `buttons.*` kind in `profiles/<id>.json` has a matching `<g data-control-id="<field>:<deck>">` in `controllers/<id>.svg.ts`.
2. **Reverse:** every `<g data-control-id>` in `controllers/<id>.svg.ts` resolves to a binding in `profiles/<id>.json`.

**Implementation:** The test imports both `profiles/<id>.json` (via Vite `?json` import or Node `fs`) and the SVG string. Parses the SVG into a DOM (jsdom is already in `tauri/ui/package.json` devDeps). Extracts all `data-control-id` attribute values via `querySelectorAll('[data-control-id]')`. Builds the expected set from the JSON. Asserts equal sets.

**Test file:** `tauri/ui/tests/learn/test_svg_profile_parity.spec.ts`. Parameterized over 11 controllers.

**Hercules MK2 carveout:** `hercules_inpulse_300_mk2.json` is NOT shipped in P91 (KAAN-ACTION §LEARN-MK2-DETECTION). The 300 SVG renders for both 300 + 300-MK2 detection; the parity gate runs against the 300 profile only.

### Pattern 7: WebviewWindow Mirror — `debrief_window.rs` Diff

**The exact Rust diff** to copy from `debrief_window.rs` into `learn_window.rs`, with these differences:

| Aspect | `debrief_window.rs` | `learn_window.rs` (P91) |
|--------|---------------------|--------------------------|
| Window label const | `"debrief"` | `"learn"` |
| Window title | `format!("Debrief — {session_label}")` | `"Learn — vibemix"` (static) |
| URL | `format!("debrief.html?session={url_encoded}")` | `"learn.html"` (no query params in P91) |
| Sidecar spawn | Spawns NEW Python sidecar with `--debrief <session_dir>` | **NO sidecar spawn** — Learn shares the main sidecar (existing `vibemix/__main__.py`'s default flag-less `main()`). |
| Session-dir validation | `recordings::validate_under_root` | **None** — no per-session path. |
| Deep-link payload | `DebriefDeepLink` Optional | **None** — P91 has no deep-link surface. |
| Sidecar handle State | `DebriefSidecarHandle` (`Arc<Mutex<Option<CommandChild>>>`) | **None** — no sidecar to manage. |
| Close-handler kill | `kill_debrief_child(&app_for_close)` | **None** — no child to kill. |
| Crash watcher | Forwards `CommandEvent::Terminated` to `sidecar-learn-crashed` | **None**. |
| Default inner_size | 1280.0 × 720.0 | 1280.0 × 720.0 ✓ |
| Min inner_size | 960.0 × 540.0 | 960.0 × 540.0 ✓ |

**Net effect:** `learn_window.rs` is MUCH smaller than `debrief_window.rs` (~80 lines vs 384). The pattern is just "open a new WebviewWindow pointing at `learn.html` — no sidecar lifecycle needed".

Three additions to `main.rs`:
```rust
mod learn_window;                              // line ~26 — alongside mod debrief_window
// ... inside .invoke_handler:
learn_window::open_learn_window,               // alongside debrief_window::open_debrief_window
```

**No `.manage(LearnSidecarHandle::default())`** — Learn shares the main sidecar process.

### Pattern 8: Tauri Capability Allowlist

Tauri 2.x gates which commands the webview can invoke via `capabilities/default.json`. The Learn webview MUST be able to invoke `open_learn_window`. Verify after adding:
```bash
grep -n "open_learn_window" tauri/src-tauri/capabilities/default.json
# Must appear in the allowlist.
```

### Pattern 9: Vite Multi-Page Build (`learn.html` as 5th Entry)

Three-line addition to `tauri/ui/vite.config.ts:rollupOptions.input`:
```typescript
input: {
  main: resolve(projectRoot, "index.html"),
  mascot: resolve(projectRoot, "mascot.html"),
  overlay: resolve(projectRoot, "overlay.html"),
  debrief: resolve(projectRoot, "debrief.html"),
  library: resolve(projectRoot, "library.html"),
  pill: resolve(projectRoot, "pill.html"),
  learn: resolve(projectRoot, "learn.html"),  // NEW
},
```

### Anti-Patterns to Avoid

- **Second `websockets.serve` for Learn-only traffic** — violates invariant #4. CI gate `tests/learn/test_no_new_ws_port.py` greps `src/vibemix/learn/` for `websockets.serve` and fails on any match.
- **Second `mido.open_input` listener for Learn** — would compete with the live session listener on most OSes; the existing daemon thread is the canonical source.
- **Repaint the entire SVG on every `midi_position` frame** — would burn the GPU. The contract is `transform`-only updates on knobs (CSS `rotate()`), `transform: translateY()` on faders, and `data-active="0|1"` attribute swap on buttons. The SVG path geometry NEVER mutates after first mount.
- **Forking the renderer to a Canvas context** — same issue. Stylized SVG + targeted CSS-variable swaps is the locked path.
- **Adding amber to a 6th element in P91** — frontend-enforcement skill rule 2 (20/80). The reserved-for list (UI-SPEC §Color) hard-caps amber at 5 elements.
- **Hard-coding `#FF7F00` (Pioneer brand orange) anywhere in `learn/`** — Apache-clean. `test_no_pioneer_orange.spec.ts` greps for it and fails red.
- **Tracing controller geometry from marketing photos** — copyright trap (Pitfall P5). Hand-authored from manufacturer PDF appendix diagrams ONLY.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| WebviewWindow lifecycle (spawn / focus / close) | A custom Rust window-manager | `tauri::WebviewWindowBuilder` (already in `debrief_window.rs`) | Tauri handles cross-platform window semantics. |
| MIDI port enumeration | Reimplementing port discovery | `mido.get_input_names()` via the existing `port_watcher_task` | Already runs at 2 Hz in `__main__.py`; just hook the existing callback. |
| MIDI message decode | Decoding CC/note bytes in `midi_mirror.py` | `ControllerState.handle_msg()` (existing, byte-equivalent to v4) | The single source of truth for "what does CC 7 on channel 0 mean?". Re-decoding is gold-plated regression risk. |
| JSON Schema validation (Python) | A custom validator | `jsonschema.Draft7Validator` (existing pattern in `ui_bus/messages.py`) | Already wired. |
| JSON Schema validation (TS) | A runtime ajv `.compile()` call (CSP blocks it) | The pre-compiled `validator.generated.mjs` via `npm run codegen:ipc` | CSP forbids `unsafe-eval`; pre-compiled is the only path. |
| TS types from JSON Schema | Hand-writing TS interfaces | `json-schema-to-typescript` via `npm run codegen:ipc` | Already wired; auto-syncs. |
| ARIA label authoring | Manually writing per-control aria-labels in 11 SVGs | A single `_aria-labels.ts` lookup keyed on the same `data-control-id` strings | Single source of truth; parity gate enforces. |
| Latency measurement | A custom timing harness | `performance.now()` + delta from synthetic MIDI burst in vitest | Standard browser API; reproducible in headless vitest run. |
| Color-blind verification | A manual contrast check | `axe-core` (already in tauri/ui devDeps via playwright tests) | One existing tool covers WCAG contrast + dual-channel cue diff. |

**Key insight:** every "problem" in P91 either has an exact precedent in the codebase (`debrief_window.rs`, `port_watcher_task`, `ControllerState`, `validator.generated.mjs`, `_aria-labels.ts`-equivalent) or a one-line standard library answer. The phase is a precise composition exercise — there is no greenfield invention here.

## Runtime State Inventory

> P91 is **additive** (not a rename or migration). Section retained for completeness; no migration items found.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | **None** — P91 introduces no persistent storage. The 30 Hz position snapshots are ephemeral, in-memory only. | None |
| Live service config | **None** — no external services modified. | None |
| OS-registered state | **None** — no new OS-level registrations (no new TCC permissions, no new background tasks, no new login items). The Tauri window auto-registers via `WebviewWindowBuilder`; that's already a covered surface for `debrief_window`. | None |
| Secrets/env vars | **None** — P91 does NOT read any env var. The `VIBEMIX_LATENCY_LOG=1` env Kaan might want for live-debug latency telemetry is a Claude's-Discretion add (not required). | None |
| Build artifacts | Vite's `dist/learn.html` is auto-emitted by the new `rollupOptions.input` entry. Verify `npm run build` emits it after the vite.config.ts edit. | One-time verify post-edit. |

**Nothing migratory.** P91 is purely new-island work.

## Common Pitfalls

### Pitfall 1: SVG↔Profile Drift (the silent killer)

**What goes wrong:** Someone adds a new `<g data-control-id="effects_a">` to the FLX4 SVG (cosmetic, "just for the rendering") without updating `pioneer_ddj_flx4.json`. The renderer paints it, but no MIDI ever lights it (no profile binding). User points to it, asks "why isn't this responding?" The bug looks like a MIDI issue but is actually SVG drift.

**Why it happens:** SVGs and profile JSONs are authored in different files at different times by different people. The natural drift class.

**How to avoid:**
- **Bidirectional parity gate** — `test_svg_profile_parity.spec.ts` runs on every CI invocation across all 11 SVG↔profile pairs. Forward (profile → SVG) AND reverse (SVG → profile). Asserts SET equality, not subset.
- **Single-source-of-truth identifier** — the `field` (or `field:deck`) string in `profiles/<id>.json` IS the `data-control-id`. There is no translation layer. If they ever diverge, the gate fails red.

**Warning signs:** CI red on `test_svg_profile_parity.spec.ts`; or a control silently never lights even with the right MIDI.

### Pitfall 2: Proprioceptive Latency >80 ms (the user-facing killer)

**What goes wrong:** User twists the EQ knob. 200 ms later the on-screen knob rotates. User perceives the renderer as "laggy" / "broken". DJ flow-state breaks.

**Why it happens:** Path is MIDI → daemon-thread `handle_msg` → asyncio loop (via lock-protected read) → ws_broadcast tick → ws frame serialize → ws send → webview ws receive → ajv validate → CustomEvent dispatch → DOM mutation → paint. Each hop is 5-15 ms on a modern Mac.

**Budget per hop (best estimate):**
- `handle_msg` lock-protected write: ~0.1 ms
- ws_broadcast tick wait: up to 33 ms worst case (we tick at 30 Hz)
- ws frame send (loopback): ~1-2 ms
- ws frame receive + JSON.parse + ajv validate: ~2-5 ms
- DOM mutation (CSS transform on single `<circle>`): ~5-10 ms paint
- **Total worst-case:** ~45-55 ms — *just under* the 50 ms target and *well under* the 80 ms red guardrail.

**Mitigation built into P91:**
- The 30 Hz tick is the dominant variance. Phase-align the tick to MIDI arrival (push immediately on the FIRST delta in a window, then wait until next 33 ms slot if still pending).
- DOM updates use `transform` (compositor-only) NOT `width`/`height`/`x`/`y` (layout-triggering). Modern browser compositor can hit 60 fps on 11 SVGs of this scale.

**Contingency:** If `tauri/ui/tests/learn/highlight-latency.test.ts` measures >80 ms P95 in CI, **§LEARN-LATENCY-CONTINGENCY** fires — Rust-direct `midir` listener feeds Tauri events to the webview, bypassing the Python ws hop. NOT built in P91; flagged for v9.x. The test gate IS the trigger.

**Warning signs:**
- Latency probe P95 readout (`status-bar P95: NN ms`) creeps above 50 ms during real-time use.
- Users describe the renderer as "sluggish" or "always behind."

### Pitfall 3: Hercules Inpulse 300 vs 300-MK2 (the latent surprise)

**What goes wrong:** A user plugs in their **Hercules Inpulse 300-MK2 (2023 release)**. `mido.get_input_names()` returns `"DJControl Inpulse 300 MIDI Out"` — substring-matches the 300 profile's port hint `"Inpulse 300"`. The renderer draws the 300 schematic. But the MK2 has slightly different MIDI maps (per DJUCED docs); some EQ knob CCs don't match — those controls never move on screen.

**Why it happens:** Same product NAME, different MIDI map. `iSerialNumber` is the disambiguator but isn't always populated.

**Mitigation in P91:**
- Both 300 and 300-MK2 render the 300 schematic in P91 (§LEARN-MK2-DETECTION KAAN-ACTION — Kaan ratifies after seeing the divergence with live hardware).
- The SVG↔profile parity gate runs against the 300 profile only — if MK2 emits unmapped CCs, they're silently dropped by `_cc_lookup.get` returning None (per `state.py:285`). No crash; just an unmoving knob on screen.
- A `hercules_inpulse_300_mk2.json` profile is added in v9.0 ONBOARDING-03 (P97) — out of scope for P91.

**Warning signs:** MK2 user reports "the EQ-HI knob doesn't move on screen but my play button does" → mismatched CC.

### Pitfall 4: Pioneer Trade-Dress / Logo Leak (the launch-suicide)

**What goes wrong:** A designer mockup of the FLX4 SVG includes the "Pioneer DJ" wordmark or uses Pioneer brand orange (`#FF7F00`) on the jog wheel. Ships. Pioneer's IP team sends a cease-and-desist. Feature pulled mid-launch.

**Why it happens:** Designer instinct toward visual fidelity; press photos as reference instead of factual hardware diagrams.

**Mitigation in P91:**
- CI gate `test_no_pioneer_orange.spec.ts` greps every `learn/**.svg.ts` for `#ff7f00` / `#FF7F00` and color literals within 10° hue of it. Fails red on any match.
- CI gate `test_no_pioneer_brand_marks.py` greps for the string `Pioneer DJ` and `Pioneer ®` rendered as SVG paths. Fails red.
- The SVGs use `currentColor` only — no `fill`/`stroke` hex literals (per `test_svg_currentcolor_only.spec.ts`). Default color from parent CSS `color: var(--silk-22)`.
- Hand-authored from manufacturer PDF appendix diagrams only — provenance noted in each SVG file's header comment.

**Warning signs:** A reviewer pings "this looks like the real thing!" — that's the trade-dress red zone, escalate.

### Pitfall 5: Vite `?raw` Import 11×File Cost

**What goes wrong:** Eleven inline SVGs imported via Vite `?raw` (each 5-15 KB) bundled into a single chunk → 100-150 KB inline blob → page first-paint slowed past the 2 s budget.

**Why it happens:** Vite `?raw` returns the raw string at build time; without code-splitting, all 11 SVGs land in the same chunk regardless of which one the user needs.

**Mitigation in P91:**
- **Dynamic import** for the controller SVG: `const { PIONEER_DDJ_FLX4_SVG } = await import("./controllers/pioneer_ddj_flx4.svg.js")`. Vite code-splits dynamic imports automatically; only the detected controller's chunk loads.
- The generic fallback `_generic.svg.ts` is the ONE SVG that's eagerly imported (kept in the main bundle so the "no controller" path renders instantly).
- Total cost per SVG fetch: a single 5-15 KB chunk on first-detect; cached for subsequent reconnects.

**Verification:** Add a vitest assertion that the dynamic import chunk is < 20 KB gzipped. (Or, since this is JS-bundler territory, defer to vite's default code-splitting and just measure in the build output.)

**Warning signs:** `npm run build` output shows `dist/assets/index-*.js` > 200 KB → likely all 11 SVGs landed in the main chunk.

### Pitfall 6: ws frames stalling during the JS pause-on-tab-switch

**What goes wrong:** User opens Learn window, focuses the main session window. macOS / Chrome throttles background tab JS to 1 Hz. The 30 Hz `midi_position` frames pile up in the browser's receive buffer. User refocuses Learn → 200 frames flood in at once → CPU spike + visible flutter.

**Why it happens:** `requestAnimationFrame` and ws message-handlers slow to ~1 Hz when the tab/window is in background on modern browsers.

**Mitigation in P91:**
- Frontend: in the `learn-window.ts` ws onmessage handler, only KEEP the latest `midi_position` frame when multiple are buffered between repaint slots. Drop the rest. Strict last-write-wins.
- Backend: `midi_mirror.py` already delta-suppresses, so the Python sidecar isn't wasting CPU emitting steady-state. The frontend drop is for the backlog-flush case.
- **Implementation pattern:** maintain a `let pendingPositions: object | null = null;` module-level; ws message sets it; a `requestAnimationFrame` callback drains it. When focus returns and 200 frames flood, only the last sets `pendingPositions`; the first rAF callback paints it.

**Warning signs:** users report "the Learn window catches up suddenly after I refocus" — frame-flood handling missing.

### Pitfall 7: Concurrent-Session Schema Drift on `messages.schema.json`

**What goes wrong:** Two Codex sessions are editing `tauri/ui/src/ipc/messages.schema.json` in parallel. Session A adds `LearnControllerDetected`; Session B adds `LessonAdvance`. Merge conflict; one envelope silently lost from the `oneOf` list. The Python wrapper still works (jsonschema doesn't validate against `oneOf` list size) but the ajv validator rejects the orphaned envelope.

**Why it happens:** CLAUDE.md §Concurrent Work warns that shared-file edits must be solo+sequential. `messages.schema.json` is a shared file by definition.

**Mitigation:**
- **Solo + sequential rule:** the planner explicitly schedules `messages.schema.json` edits as a SOLO task; no parallel sub-tasks touch this file. P91 lands BOTH envelopes in ONE commit (`ipc.learn.controller_detected` + `ipc.learn.midi_position` together).
- **CodeGen-after-edit:** `npm run codegen:ipc` regenerates `validator.generated.mjs` AND `messages.ts` — both committed. CI compares the committed files to a fresh codegen run; drift fails red.
- **Count-parity test:** `scripts/check_ipc_schema.py` (existing) asserts `oneOf` length == wrapper-dataclass count. P91 adds 2 wrappers → must add 2 oneOf entries.

**Warning signs:** ajv validation errors at runtime ("unknown schema $ref"); or `check_ipc_schema.py` red.

## Code Examples

Verified patterns from existing sources in this repo. Each shows what the new code should mirror.

### Code Example 1: MidiMirror class skeleton (the file:line-traceable design)

```python
# src/vibemix/learn/midi_mirror.py — NEW
# SPDX-License-Identifier: Apache-2.0
"""MidiMirror — 30 Hz delta-coalesced controller-position snapshotter.

Phase 91 (RENDER-02). Reads (read-only) the existing ControllerState updated
by `vibemix.midi.state::handle_msg`, integer-LSB-suppresses identical frames,
and produces a `LearnMidiPosition` envelope dict for `ws_broadcast` to emit
on its existing 30 Hz outbound tick.

Threading: lives on the ASYNCIO main loop (called from `ws_broadcast`). The
ControllerState it reads from runs on the MIDI daemon thread; reads are safe
via ControllerState's own lock (state.py:144).

Single-writer (invariant #1): MidiMirror is the SOLE writer of
`ipc.learn.midi_position` envelopes. It never writes to MusicState; it never
writes to ControllerState. Read-only consumer of both.
"""
from __future__ import annotations

from typing import Any

from vibemix.midi.profile import ControllerProfile
from vibemix.ui_bus.learn_messages import (
    LearnControllerDetected,
    LearnMidiPosition,
)


class MidiMirror:
    """Snapshot the live ControllerState into a delta-coalesced position dict
    suitable for the `ipc.learn.midi_position` envelope.

    Owner: `vibemix.__main__.main()` instantiates ONE MidiMirror after the
    MIDI listener thread is up (alongside `midi_macos`). Hands it to
    `ws_broadcast` via a new kwarg so the broadcast loop can pull `.snapshot()`
    at 30 Hz.

    Methods:
        snapshot(profile) -> dict | None
            Read current ControllerState; integer-LSB compare against
            self._last; if any delta, return a LearnMidiPosition.to_dict()
            and advance self._last. Else return None (suppress).
        controller_detected(connected, profile, port_name) -> dict
            Build a LearnControllerDetected.to_dict() — caller emits it.
    """

    def __init__(self, controller_state: Any) -> None:
        self._cs = controller_state
        # Cache of last-sent positions (integer values). The LSB-delta gate.
        self._last_positions: dict[str, int] = {}
        # Profile binding can change on hot-plug; midi_mirror tracks the
        # currently-bound profile so it knows which controls to surface.
        # Updated by the port_watcher callback hook (see __main__ wiring).
        self._profile: ControllerProfile | None = None

    def bind_profile(self, profile: ControllerProfile) -> None:
        """Called once on each `('connected', port, profile)` event."""
        self._profile = profile
        # Reset the delta cache on profile-swap so the first frame after
        # connect always emits (filling the renderer with current state).
        self._last_positions = {}

    def unbind(self) -> None:
        """Called on `('disconnected', port)` — clears cached profile."""
        self._profile = None
        self._last_positions = {}

    def snapshot(self) -> dict | None:
        """Return a LearnMidiPosition envelope dict if any tracked position
        changed since last call; else None (caller should not emit)."""
        if self._profile is None:
            return None
        cur = self._read_current_positions()
        # Integer-LSB delta: skip emit if every position is byte-equal to last.
        if cur == self._last_positions:
            return None
        self._last_positions = cur
        return LearnMidiPosition.make(
            controller_id=self._profile.id,
            positions=cur,
        ).to_dict()

    def controller_detected(
        self,
        *,
        connected: bool,
        profile: ControllerProfile,
        port_name: str,
    ) -> dict:
        """Single-fire on connect/disconnect. Caller invokes this from the
        existing port_watcher callback (handle_port_change_single_state in
        vibemix.platform._midi_common). Returns the envelope dict; the
        caller emits via ws_broadcast's `_send_all`."""
        return LearnControllerDetected.make(
            connected=connected,
            controller_id=profile.id,
            display_name=profile.display_name,
            port_name=port_name,
        ).to_dict()

    # ---- internal ----

    def _read_current_positions(self) -> dict[str, int]:
        """Read the live ControllerState into the wire shape.

        Uses ControllerState.deck_snapshot() which already lock-guards the
        read (state.py:144). Single thread-safe read; never holds the lock
        outside this method.

        Wire shape: `{"<field>:<deck>": int}` for deck-bound controls;
        bare `"<field>": int` for master-section (xfader).
        """
        snap = self._cs.deck_snapshot()
        out: dict[str, int] = {}
        # Per-deck CC controls: vol / eq_low / eq_mid / eq_hi / filter / tempo
        # plus booleans play / cue / jog_touched (as 0/1).
        for deck_letter, deck_dict in snap.items():
            if deck_letter in ("xfader", "connected"):
                continue
            # CC knobs/faders (0..127)
            for field in ("vol", "eq_low", "eq_mid", "eq_hi", "filter", "tempo"):
                if field in deck_dict:
                    out[f"{field}:{deck_letter}"] = int(deck_dict[field])
            # Booleans (0/1)
            for field in ("play", "cue", "jog_touched"):
                if field in deck_dict:
                    out[f"{field}:{deck_letter}"] = 1 if deck_dict[field] else 0
        # Master-section: xfader
        if "xfader" in snap:
            out["xfader"] = int(snap["xfader"])
        return out
```

### Code Example 2: learn_window.rs (the trimmed mirror)

```rust
// tauri/src-tauri/src/learn_window.rs — NEW
// SPDX-License-Identifier: Apache-2.0
//! Phase 91 RENDER-07 — Learn window second WebviewWindow.
//!
//! Trimmed mirror of `debrief_window.rs` — no sidecar lifecycle, no
//! session_dir validation, no deep-link payload. The Learn window is a
//! passive frontend surface that connects to the EXISTING main sidecar's
//! ws:8765 (one-socket invariant #4 preserved).

use tauri::{AppHandle, Manager, WebviewUrl, WebviewWindowBuilder};

pub const LEARN_WINDOW_LABEL: &str = "learn";

const DEFAULT_WIDTH: f64 = 1280.0;
const DEFAULT_HEIGHT: f64 = 720.0;
const MIN_WIDTH: f64 = 960.0;
const MIN_HEIGHT: f64 = 540.0;

/// Open the Learn window. Focus-existing pattern (at most one Learn
/// window at a time). Shares the main sidecar — no Python process is
/// spawned by this command.
#[tauri::command]
pub async fn open_learn_window(app: AppHandle) -> Result<(), String> {
    // Focus existing window if already open.
    if let Some(existing) = app.get_webview_window(LEARN_WINDOW_LABEL) {
        let _ = existing.set_focus();
        return Ok(());
    }

    let _window = WebviewWindowBuilder::new(
        &app,
        LEARN_WINDOW_LABEL,
        WebviewUrl::App("learn.html".into()),
    )
    .title("Learn — vibemix")
    .inner_size(DEFAULT_WIDTH, DEFAULT_HEIGHT)
    .min_inner_size(MIN_WIDTH, MIN_HEIGHT)
    .resizable(true)
    .decorations(true)
    .build()
    .map_err(|e| format!("window build: {e}"))?;

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn learn_window_label_const_is_lowercase_no_spaces() {
        assert_eq!(LEARN_WINDOW_LABEL, "learn");
        assert!(LEARN_WINDOW_LABEL.chars().all(|c| c.is_lowercase()));
        assert!(!LEARN_WINDOW_LABEL.contains(' '));
    }
}
```

### Code Example 3: Latency Measurement Harness (vitest, headless)

```typescript
// tauri/ui/tests/learn/highlight-latency.test.ts — NEW
// Tests the MIDI→DOM mirror latency in a synthetic harness. Target 50 ms
// P95; FAILS RED at 80 ms P95 (triggers §LEARN-LATENCY-CONTINGENCY).

import { describe, it, expect, beforeAll } from "vitest";
import { JSDOM } from "jsdom";
import { PIONEER_DDJ_FLX4_SVG } from "../../src/learn/controllers/pioneer_ddj_flx4.svg.js";

const N_BURST = 240;     // 240 synthetic frames @ 30 Hz = 8s of simulated MIDI
const P95_TARGET_MS = 50;
const P95_RED_GUARDRAIL_MS = 80;

interface PositionFrame {
  controller_id: string;
  positions: Record<string, number>;
  emit_ts: number;   // when frame was synthesized
}

describe("midi_position → DOM mirror latency", () => {
  let dom: JSDOM;
  let document: Document;

  beforeAll(() => {
    dom = new JSDOM(
      `<!DOCTYPE html><html><body>
         <div id="learn-stage">${PIONEER_DDJ_FLX4_SVG}</div>
       </body></html>`,
    );
    document = dom.window.document;
  });

  it("P95 latency ≤ 50 ms target; FAILS RED at 80 ms", () => {
    const samples: number[] = [];

    // Synthesize 240 frames; sweep eq_hi:A through 0→127→0 over the burst.
    for (let i = 0; i < N_BURST; i++) {
      const v = i < 120 ? i : 240 - i;  // triangle 0..127..0
      const frame: PositionFrame = {
        controller_id: "pioneer_ddj_flx4",
        positions: { "eq_hi:A": v },
        emit_ts: performance.now(),
      };

      // Mirror update path: find <g data-control-id="eq_hi:A">, rotate child <circle>.
      const t0 = performance.now();
      applyPositionFrame(document, frame);
      const t1 = performance.now();

      samples.push(t1 - frame.emit_ts);  // emit→paint delta
    }

    samples.sort((a, b) => a - b);
    const p95 = samples[Math.floor(samples.length * 0.95)];
    console.log(`midi_position P95 latency: ${p95.toFixed(2)} ms`);

    // Soft fail: warn but don't break CI when between 50-80 ms.
    if (p95 > P95_TARGET_MS && p95 <= P95_RED_GUARDRAIL_MS) {
      console.warn(
        `LATENCY WARNING: P95 ${p95.toFixed(2)} ms exceeds target ${P95_TARGET_MS} ms ` +
        `but within red guardrail ${P95_RED_GUARDRAIL_MS} ms. ` +
        `Investigate before §LEARN-LATENCY-CONTINGENCY triggers.`,
      );
    }

    // Red fail: above 80 ms → CI red, §LEARN-LATENCY-CONTINGENCY invoked.
    expect(p95).toBeLessThanOrEqual(P95_RED_GUARDRAIL_MS);
  });
});

// The exact path the production mirror takes — verified identical to the
// runtime applyPositionFrame() in src/learn/components/controller-stage.ts.
function applyPositionFrame(doc: Document, frame: PositionFrame): void {
  for (const [controlId, value] of Object.entries(frame.positions)) {
    const group = doc.querySelector(`[data-control-id="${controlId}"]`) as SVGGElement | null;
    if (!group) continue;
    // Knobs rotate: map 0..127 → -135°..+135°. transform-only update.
    const degrees = ((value / 127) * 270) - 135;
    group.setAttribute("transform", `rotate(${degrees} ${getCenterX(group)} ${getCenterY(group)})`);
  }
}

function getCenterX(g: SVGGElement): number { return Number(g.dataset.cx ?? 0); }
function getCenterY(g: SVGGElement): number { return Number(g.dataset.cy ?? 0); }
```

**Notes on the harness:**
- Runs headless via vitest + jsdom (already in `tauri/ui/package.json` devDeps).
- The `emit_ts → paint_ts` delta is the timing measure. In production, `emit_ts` would be the ws frame's `ts` field; here we use `performance.now()` at synthesis.
- Reproducible: 240 samples is enough for a stable P95 measurement. Triangle sweep exercises both edges of the integer range.
- **Caveat:** jsdom is a synthetic DOM; real browser paint involves the compositor. The 50 ms target in jsdom is conservative — real Tauri webview should be faster. The 80 ms red guardrail is the production-relevant gate; if jsdom can't even hit 80 ms, prod definitely can't.

### Code Example 4: ipc.learn.controller_detected — Python dataclass

```python
# src/vibemix/ui_bus/learn_messages.py — NEW
# SPDX-License-Identifier: Apache-2.0
"""Phase 91 — ipc.learn.* envelope dataclasses.

Two envelopes land in P91:
  - LearnControllerDetected (sidecar→shell, single-fire per plug)
  - LearnMidiPosition       (sidecar→shell, 30 Hz delta-suppressed)

Mirrors of `messages.schema.json::LearnControllerDetected` +
`messages.schema.json::LearnMidiPosition`. Validation by the shared
`_VALIDATOR` already loaded in `vibemix.ui_bus.messages` — we re-use, not
re-instantiate.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

from vibemix.ui_bus.messages import _now_iso, _serialize


@dataclass(frozen=True, slots=True)
class LearnControllerDetectedPayload:
    connected: bool
    controller_id: str
    display_name: str
    port_name: str


@dataclass(frozen=True, slots=True)
class LearnControllerDetected:
    type: Literal["ipc.learn.controller_detected"]
    ts: str
    payload: LearnControllerDetectedPayload

    @classmethod
    def make(
        cls,
        *,
        connected: bool,
        controller_id: str,
        display_name: str,
        port_name: str,
    ) -> LearnControllerDetected:
        return cls(
            type="ipc.learn.controller_detected",
            ts=_now_iso(),
            payload=LearnControllerDetectedPayload(
                connected=connected,
                controller_id=controller_id,
                display_name=display_name,
                port_name=port_name,
            ),
        )

    def to_json(self) -> str:
        return _serialize(self)

    def to_dict(self) -> dict:
        import json
        return json.loads(self.to_json())


@dataclass(frozen=True, slots=True)
class LearnMidiPositionPayload:
    controller_id: str
    # positions is dict[str, int]; the schema uses `additionalProperties: {type: integer}`
    # to express "any key → integer value". asdict serializes as-is.
    positions: dict[str, int]


@dataclass(frozen=True, slots=True)
class LearnMidiPosition:
    type: Literal["ipc.learn.midi_position"]
    ts: str
    payload: LearnMidiPositionPayload

    @classmethod
    def make(
        cls,
        *,
        controller_id: str,
        positions: dict[str, int],
    ) -> LearnMidiPosition:
        return cls(
            type="ipc.learn.midi_position",
            ts=_now_iso(),
            payload=LearnMidiPositionPayload(
                controller_id=controller_id,
                positions=positions,
            ),
        )

    def to_json(self) -> str:
        return _serialize(self)

    def to_dict(self) -> dict:
        import json
        return json.loads(self.to_json())
```

### Code Example 5: messages.schema.json additions (the 2 oneOf entries)

```jsonc
// tauri/ui/src/ipc/messages.schema.json — ADDITIONS
// 1. Add to top-level "oneOf": [...] list (TWO new entries):

{ "$ref": "#/definitions/LearnControllerDetected" },
{ "$ref": "#/definitions/LearnMidiPosition" },

// 2. Add to "definitions": {...}:

"LearnControllerDetected": {
  "$comment": "Sidecar → shell. Single fire per MIDI port-bind / unbind event. Phase 91 RENDER-01 / RENDER-07.",
  "type": "object",
  "additionalProperties": false,
  "required": ["type", "ts", "payload"],
  "properties": {
    "type": { "const": "ipc.learn.controller_detected" },
    "ts": { "type": "string", "format": "date-time" },
    "payload": {
      "type": "object",
      "additionalProperties": false,
      "required": ["connected", "controller_id", "display_name", "port_name"],
      "properties": {
        "connected": { "type": "boolean" },
        "controller_id": { "type": "string", "minLength": 1 },
        "display_name": { "type": "string", "minLength": 1 },
        "port_name": { "type": "string" }
      }
    }
  }
},

"LearnMidiPosition": {
  "$comment": "Sidecar → shell. 30 Hz delta-suppressed controller position snapshot. Phase 91 RENDER-02. Keys in 'positions' follow '<field>:<deck>' (deck-bound) or bare '<field>' (master-section) convention; values 0..127 for CC controls, 0/1 for booleans.",
  "type": "object",
  "additionalProperties": false,
  "required": ["type", "ts", "payload"],
  "properties": {
    "type": { "const": "ipc.learn.midi_position" },
    "ts": { "type": "string", "format": "date-time" },
    "payload": {
      "type": "object",
      "additionalProperties": false,
      "required": ["controller_id", "positions"],
      "properties": {
        "controller_id": { "type": "string", "minLength": 1 },
        "positions": {
          "type": "object",
          "additionalProperties": { "type": "integer", "minimum": 0, "maximum": 127 }
        }
      }
    }
  }
}
```

**Post-edit MUST run:**
```bash
cd tauri/ui && npm run codegen:ipc  # regenerates messages.ts + validator.generated.mjs
```

### Code Example 6: ws_broadcast wiring — 30 Hz pull on existing tick

```python
# src/vibemix/runtime/ws_bus.py — DIFF (additive inside existing ws_broadcast)
# Approximate insertion point: inside the `while not stop_event.is_set():` loop
# in ws_broadcast(), AFTER the snapshot emit block.

# ... existing 30Hz tick loop ...
        try:
            # ... existing snapshot path ...

            # NEW — Phase 91: pull a position frame from MidiMirror if delta.
            if midi_mirror is not None:
                pos_frame = midi_mirror.snapshot()
                if pos_frame is not None:
                    try:
                        await _send_all(pos_frame)
                    except Exception as e:
                        print(f"[learn pos emit err] {e}", file=sys.stderr)

            await asyncio.sleep(1.0 / 30)  # existing 30 Hz tick
            tick += 1

# `midi_mirror` is a NEW kwarg on ws_broadcast — defaults to None for
# backward-compat with existing test callers. __main__.main() builds a
# MidiMirror after midi_macos.controller_state exists and threads it in.
```

```python
# src/vibemix/__main__.py — DIFF (additive inside main() after midi_macos init)

    # ... existing midi_macos = MidiMacOS() at line 844 ...

    # NEW — Phase 91: wire MidiMirror for the Learn window.
    from vibemix.learn.midi_mirror import MidiMirror

    midi_mirror = MidiMirror(controller_state=midi_macos.controller_state)
    # Also hook the port watcher's on_change callback so controller_detected
    # envelopes fire on connect/disconnect. Wrap the existing single-state
    # handler so we don't fork its behavior.

    # ... when handing midi_mirror to ws_broadcast at the ws_broadcast() call:
    asyncio.create_task(
        ws_broadcast(
            levels=levels,
            state=state,
            manual_trigger=manual_trigger,
            stop_event=stop_event,
            transcript_buf=transcript_buf,
            controller_state=midi_macos.controller_state,
            suggestion_holder=suggestion_holder,
            tracer=tracer,
            ipc_router=ipc_router,
            screen_available=screen_available,
            midi_mirror=midi_mirror,  # NEW
        )
    )
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Tauri 1.x event model (raw `app.emit`) | Tauri 2.x `WebviewWindowBuilder` + URL params | Tauri 2.0 release Q3 2024 | The `debrief_window.rs` precedent is on 2.x — we follow. |
| Hand-written ajv validator | Pre-compiled `validator.generated.mjs` via `npm run codegen:ipc` | Phase 11 Wave 0 (this codebase) | CSP `unsafe-eval` block forces pre-compile path; we follow. |
| Canvas-based DJ controller rendering (e.g. Mixxx 2.4) | Inline-SVG with `data-*` hit regions (locked here) | Project-specific 2026-05-27 | SVG + CSS-variable swap is composited and a11y-native; Canvas has neither benefit. |

**Deprecated/outdated:**
- The Tauri 1.x `app.listen` global event approach is replaced by per-window `Manager::get_webview_window()` resolution — already used in `debrief_window.rs:113`.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The existing 30 Hz `ws_broadcast` loop tolerates one additional `await _send_all()` per tick without missing its 1/30 s budget. | Pattern 2 + Code Example 6 | If `_send_all` takes >5 ms on average (it shouldn't — loopback ws is sub-ms), the mascot frame's 30 Hz cadence could drift. Verified by existing tests `test_ws_07*`; if they still pass with the addition, we're safe. Add `tests/runtime/test_ws_broadcast_30hz_under_learn_load.py` to pin. |
| A2 | Vite's dynamic-import code-splitting effectively chunks the 11 controller SVGs so first-paint stays under 2 s. | Pitfall 5 | If the SVGs are too big or Vite chunks them aggressively-tiny (10 separate HTTP requests), first-paint could exceed budget. Verifiable in `npm run build` output: each `dist/assets/<id>.svg-*.js` chunk should be 5-15 KB gzipped. |
| A3 | jsdom's synthetic `setAttribute('transform', ...)` timing in vitest is a conservative proxy for real Tauri WebKit paint. | Code Example 3 | If jsdom is much faster than real browser, the 50ms target could pass in test but fail in production. Mitigation: the 80 ms red guardrail provides ample headroom; if real-prod measurements diverge, §LEARN-LATENCY-CONTINGENCY triggers regardless. |
| A4 | Hercules Inpulse 300 + 300-MK2 share the port_name_hints from the 300 profile sufficient for substring match. | Pitfall 3 | If MK2 reports an entirely different port name (e.g. "MK2"), the 300 profile won't match and the generic fallback renders. Acceptable degradation. The §LEARN-MK2-DETECTION KAAN-ACTION is the resolution path. |
| A5 | The `_aria-labels.ts` lookup is hand-authored once and covers every (field, deck) combination across all 11 profiles. | Pattern 4 | If a Wave-2 profile (DDJ-1000/SX3) has 8 hotcue pads per deck that we forget to add aria-labels for, the parity gate fails. Verifiable BEFORE shipping P91 by grepping the 11 profiles for unique field names. |
| A6 | The `currentColor` discipline in SVG (no hex literals inside) is enforced by `test_svg_currentcolor_only.spec.ts`. | Pattern 1 SVG shape | If a designer inserts a hex literal, the test catches it. New test ships in P91; if it doesn't ship, hex leaks become possible. |
| A7 | jsdom is available at test runtime via `tauri/ui/package.json` devDeps. | Code Example 3 | Verified — `jsdom: "^29.1.1"` is already in devDeps. |

**If this table is empty:** Not applicable; 7 assumptions tagged for ratification.

## Open Questions (RESOLVED 2026-05-27)

1. **Should P91 wire a `VIBEMIX_LATENCY_LOG=1` env to dump rolling latency samples to `events.jsonl`?**
   - **RESOLVED: YES — wire in P91.** Trivial cost (single `os.environ.get("VIBEMIX_LATENCY_LOG")` branch in `MidiMirror`), hugely valuable during ear-pass. Planner discretion on exact event shape.

2. **Should the 11 controller SVG files all ship together in P91, or only FLX4 + generic in P91 with the other 9 in P98?**
   - **RESOLVED: ALL 11 SVGs in P91 per Kaan's "fully-comprehensive / default-YES" directive (SUMMARY §2 LOCKED).** FLX4 is the canonical ear-pass golden (Plan 07); the other 9 controllers' SVGs ship but their live ear-passes ride forward as §LEARN-CONTROLLER-EAR KAAN-ACTION queue items into P98. Plan 06 schedules the 9 non-FLX4 SVGs as a single re-entrant batch — the parity gate goes green per-SVG, so the work is incrementally committable.

3. **Does the Learn window need a Tauri capability allowlist entry?**
   - **RESOLVED: YES, but the entry goes into the `windows` scope array (NOT a permission identifier).** The existing pattern (verified by reading `tauri/src-tauri/capabilities/default.json` description text + the `"windows": ["main", "mascot", "overlay-*", "debrief", "pill", "library"]` array) is: Tauri 2.x auto-allows webview→app-command invocation for any command registered in `invoke_handler`, so `open_learn_window` does NOT need a permission identifier. What it DOES need is the window label `"learn"` appended to the top-level `windows` scope array (mirroring how `"debrief"`, `"pill"`, `"library"` were added in prior phases). Attempting to add an `"open_learn_window"` or `"learn_window:default"` permission identifier would FAIL the Tauri build with "permission identifier not found" — the description text on line 4 explicitly warns about this. **This supersedes the original recommendation in this section, which was technically wrong.**

4. **What's the test fixture format for the SVG↔profile parity gate?**
   - **RESOLVED: TS tests read the JSON directly from `src/vibemix/midi/profiles/<id>.json` via `fs.readFileSync` (vitest+jsdom Node context).** No Python round-trip; no shared fixture file. Vitest is already configured with `environment: 'jsdom'`.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Tauri 2.x (Rust crate) | `learn_window.rs` | ✓ | Per existing `tauri/src-tauri/Cargo.toml` | — |
| Vite | `learn.html` build + `?raw` import | ✓ | ^6.0 | — |
| vitest + jsdom | Latency harness + parity gate | ✓ | vitest ^2.1, jsdom ^29.1.1 | — |
| axe-core (via playwright) | Contrast gate | ✓ | Vendored via playwright | — |
| `npm run codegen:ipc` toolchain (ajv + json-schema-to-typescript) | Post-edit schema regen | ✓ | Already wired | — |
| mido + python-rtmidi | MIDI listener | ✓ | Per `pyproject.toml` | — |
| websockets | ws:8765 server | ✓ | Per `pyproject.toml` | — |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** none.

P91 runs cleanly on the existing environment. No new install gate.

## Validation Architecture

> Required because `workflow.nyquist_validation` is not explicitly false. Section drives VALIDATION.md.

### Test Framework

| Property | Value |
|----------|-------|
| Python framework | pytest (`PYTHONPATH=src python3 -m pytest -q`) |
| TS framework | vitest (`cd tauri/ui && npm test`) |
| TS spec (DOM-walking) framework | playwright (`cd tauri/ui && npx playwright test` — used for keyboard-nav + axe-core gates) |
| Rust framework | `cargo test` (already wired in `tauri/src-tauri/`) |
| Quick run command | `cd tauri/ui && npm test` (vitest, ~3-5s) + `PYTHONPATH=src python3 -m pytest -q tests/learn/ tests/ipc/test_learn_envelope_parity.py` (pytest, ~5-10s) |
| Full suite command | `PYTHONPATH=src python3 -m pytest -q && cd tauri/ui && npm test && cd ../src-tauri && cargo test` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| **RENDER-01** | Plug FLX4 → SVG mount within 2s | unit + integration | `cd tauri/ui && npx vitest run tests/learn/test_controller_detected_mounts_svg.test.ts` | ❌ Wave 0 |
| **RENDER-01** | `controller_detected` envelope shape | unit | `PYTHONPATH=src python3 -m pytest tests/ipc/test_learn_envelope_parity.py::test_controller_detected_roundtrip -x` | ❌ Wave 0 |
| **RENDER-01** | All 11 controllers have SVG files | unit | `cd tauri/ui && npx vitest run tests/learn/test_all_11_svgs_present.spec.ts` | ❌ Wave 0 |
| **RENDER-01** | Generic fallback renders on no-match | unit | `cd tauri/ui && npx vitest run tests/learn/test_generic_fallback.spec.ts` | ❌ Wave 0 |
| **RENDER-02** | Synthetic latency P95 ≤ 50 ms target | unit | `cd tauri/ui && npx vitest run tests/learn/highlight-latency.test.ts` | ❌ Wave 0 |
| **RENDER-02** | Synthetic latency P95 ≤ 80 ms red guardrail | unit (same test, hard fail) | `cd tauri/ui && npx vitest run tests/learn/highlight-latency.test.ts` | ❌ Wave 0 (same file as above) |
| **RENDER-02** | MidiMirror delta suppression — no emit when positions unchanged | unit | `PYTHONPATH=src python3 -m pytest tests/learn/test_midi_mirror_unit.py::test_no_emit_when_steady -x` | ❌ Wave 0 |
| **RENDER-02** | MidiMirror emits on first frame after bind | unit | `PYTHONPATH=src python3 -m pytest tests/learn/test_midi_mirror_unit.py::test_first_frame_after_bind -x` | ❌ Wave 0 |
| **RENDER-02** | MidiMirror 30 Hz cadence under ws_broadcast | integration | `PYTHONPATH=src python3 -m pytest tests/runtime/test_ws_broadcast_30hz_under_learn_load.py -x` | ❌ Wave 0 |
| **RENDER-03** | Every `<g data-control-id>` has `role="button"` + `aria-label` | unit (DOM walk) | `cd tauri/ui && npx vitest run tests/learn/test_aria_labels_present.spec.ts` | ❌ Wave 0 |
| **RENDER-03** | Tab cycles through control groups in DOM order | spec (playwright) | `cd tauri/ui && npx playwright test tests/learn/test_keyboard_nav_order.spec.ts` | ❌ Wave 0 |
| **RENDER-03** | Screen-reader polite announcement on detect | unit | `cd tauri/ui && npx vitest run tests/learn/test_sr_announcement.spec.ts` | ❌ Wave 0 |
| **RENDER-05** | Each `<g>` has `cue-color` + `cue-shape` empty slots (stub) | unit (annotated stub-only) | `cd tauri/ui && npx vitest run tests/learn/test_dual_cue_slots_present.spec.ts` | ❌ Wave 0 |
| **RENDER-06** | Bidirectional SVG↔profile parity across 11 files | unit (parameterized) | `cd tauri/ui && npx vitest run tests/learn/test_svg_profile_parity.spec.ts` | ❌ Wave 0 |
| **RENDER-07** | Learn window opens via `open_learn_window` Tauri command | unit (Rust) | `cd tauri/src-tauri && cargo test learn_window` | ❌ Wave 0 |
| **RENDER-07** | Learn window label is "learn" (lowercase, no spaces) | unit (Rust) | `cd tauri/src-tauri && cargo test learn_window_label_const_is_lowercase` | ❌ Wave 0 |
| **RENDER-07** | Learn webview connects to ws:8765 (not a new port) | unit (TS) + grep gate | `cd tauri/ui && npx vitest run tests/learn/test_ws_client_uses_8765.spec.ts` + `PYTHONPATH=src python3 -m pytest tests/learn/test_no_new_ws_port.py -x` | ❌ Wave 0 |
| **N/A — Brand safety** | No `#FF7F00` / `#ff7f00` in `learn/**.svg.ts` | unit (regex grep) | `cd tauri/ui && npx vitest run tests/learn/test_no_pioneer_orange.spec.ts` | ❌ Wave 0 |
| **N/A — Brand safety** | No "Pioneer DJ" string in any `learn/**.svg.ts` | unit | `PYTHONPATH=src python3 -m pytest tests/learn/test_no_pioneer_brand_marks.py -x` | ❌ Wave 0 |
| **N/A — currentColor** | No `fill="#..."` / `stroke="#..."` hex literals inside SVG bodies | unit (regex grep) | `cd tauri/ui && npx vitest run tests/learn/test_svg_currentcolor_only.spec.ts` | ❌ Wave 0 |
| **N/A — IPC parity** | 2 wrappers ↔ 2 oneOf entries (count parity) | unit | `python3 scripts/check_ipc_schema.py` (existing — runs against new envelopes after schema edit) | ✅ Existing |
| **N/A — IPC parity** | Round-trip — Python dataclass → JSON → ajv validate → Python parse | unit | `PYTHONPATH=src python3 -m pytest tests/ipc/test_learn_envelope_parity.py -x` | ❌ Wave 0 |
| **N/A — A11Y contrast** | Learn window passes axe-core contrast | spec (playwright) | `cd tauri/ui && npx playwright test tests/learn/test_contrast_ratios.spec.ts` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `cd tauri/ui && npm test -- tests/learn/` (vitest only — ~3-5 s)
- **Per wave merge:** `cd tauri/ui && npm test && PYTHONPATH=src python3 -m pytest -q tests/learn/ tests/ipc/test_learn_envelope_parity.py` (~10 s)
- **Phase gate:** Full suite green before `/gsd:verify-work` — `PYTHONPATH=src python3 -m pytest -q && cd tauri/ui && npm test && npx playwright test tests/learn/ && cd ../src-tauri && cargo test`

### Wave 0 Gaps

- [ ] `tests/learn/__init__.py` — Python test package marker
- [ ] `tests/learn/test_midi_mirror_unit.py` — covers RENDER-02 backend unit tests
- [ ] `tests/learn/test_no_new_ws_port.py` — grep-gate for `learn/` (zero `websockets.serve`)
- [ ] `tests/learn/test_no_pioneer_brand_marks.py` — grep-gate for Pioneer wordmark
- [ ] `tests/ipc/test_learn_envelope_parity.py` — round-trip + count parity for the 2 new envelopes
- [ ] `tests/runtime/test_ws_broadcast_30hz_under_learn_load.py` — 30 Hz cadence pin
- [ ] `tauri/ui/tests/learn/` directory (NEW) + all 14 spec files (highlight-latency, svg_profile_parity, aria_labels_present, keyboard_nav_order, contrast_ratios, sr_announcement, dual_cue_slots_present, no_pioneer_orange, svg_currentcolor_only, all_11_svgs_present, generic_fallback, controller_detected_mounts_svg, ws_client_uses_8765, learn_window_label)
- [ ] Vite config edit: add `learn: resolve(projectRoot, "learn.html")` to `rollupOptions.input`
- [ ] `tauri/ui/learn.html` — 5th HTML entry point
- [ ] Capability allowlist edit: add `learn_window:default` to `tauri/src-tauri/capabilities/default.json` (if Tauri 2.x requires per-command capability gating)

*(Existing test infrastructure covers IPC count-parity via `scripts/check_ipc_schema.py` — no new infra needed for that one gate.)*

## Security Domain

> `security_enforcement` is implicit (config not set to false). Section included.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | The Learn webview is a same-origin local Tauri window; no user-auth surface. |
| V3 Session Management | no | No server-side session; ws:8765 is loopback-only. |
| V4 Access Control | no | No multi-user surface. |
| V5 Input Validation | yes | **The 2 new envelopes are JSON-validated bidirectionally** — Python via `jsonschema.Draft7Validator` (`_VALIDATOR.validate` in `ui_bus/messages.py:84`); TS via `validator.generated.mjs` pre-compiled ajv. `additionalProperties: false` on every payload. CSP forbids `unsafe-eval` so ajv standalone is mandatory. |
| V6 Cryptography | no | No new crypto. |
| V8 Sensitive Data | yes | **No new sensitive data captured.** MIDI positions are not personally-identifying. Controller display names + port names are local-machine-only over ws:8765 loopback. CLAUDE.md privacy rule (Hermes/LM-Studio paths off-limits) is NOT touched by P91. |
| V12 Files & Resources | yes | SVG files ship as static bundled assets (no user upload). No file I/O from the webview. The Tauri `WebviewUrl::App(...)` constructor is what loads `learn.html` — same-origin, no remote fetch. |
| V13 API & Web Services | yes | ws:8765 is bound to 127.0.0.1 only (per existing `audio/__init__.py::WS_HOST` constant). No external network surface. |

### Known Threat Patterns for vibemix Tauri+Python stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Untrusted ws frame from spoofed client | Tampering | jsonschema validation on every frame (Python side) + pre-compiled ajv validation (TS side). `additionalProperties: false` enforced. |
| XSS via SVG `<script>` injection | Tampering | SVGs are hand-authored from manufacturer PDFs — no user content. No `<script>` tag will exist in the SVGs (CI gate `test_svg_no_script_tag.spec.ts` recommended). |
| Tauri capability bypass (unauthorized command) | Elevation | `open_learn_window` MUST be added to `tauri/src-tauri/capabilities/default.json`. Tauri 2.x rejects unauthorized command invocations by default. |
| Hex/path-traversal injection via Tauri URL | Tampering | The Learn URL is hardcoded `"learn.html"` (no query params in P91) — no user-controllable URL fragment. (Contrast with `debrief_window.rs` which validates the `session_dir` query.) |
| Trade-dress / logo leak from SVG geometry | (legal, not technical STRIDE) | CI gates `test_no_pioneer_orange.spec.ts` + `test_no_pioneer_brand_marks.py`. |

## Sources

### Primary (HIGH confidence — in-tree file:line verified)
- `tauri/src-tauri/src/debrief_window.rs:1-384` — the exact precedent for the WebviewWindow second-window pattern
- `tauri/ui/src/wizard/controllers/ddj-flx4.svg.ts:6` — the Vite `?raw` SVG inline-import pattern
- `src/vibemix/midi/state.py:118-484` — `ControllerState` + `MidiEvent` + the `handle_msg` decode path
- `src/vibemix/midi/registry.py:23-60` — `find_mapping` / `find_mapping_or_generic`
- `src/vibemix/midi/profile.py:80-383` — `ControllerProfile` dataclass + JSON loader
- `src/vibemix/midi/profiles/pioneer_ddj_flx4.json` — the 1:1 mapping the FLX4 SVG must match
- `src/vibemix/midi/watcher.py:39-124` — `port_watcher_task` async hot-plug
- `src/vibemix/platform/_midi_common.py:83-321` — daemon-thread listener + `ListenerHolder` + `handle_port_change_single_state`
- `src/vibemix/platform/_midi_macos.py:96-218` — `MidiMacOS.start_listener_thread` + `start_port_watcher` integration
- `src/vibemix/runtime/ws_bus.py:276-460` — `IpcRouterBus` + `ws_broadcast` 30 Hz tick
- `src/vibemix/ui_bus/messages.py:84-2081` — jsonschema-Draft7 validator pattern + dataclass wrappers
- `src/vibemix/__main__.py:843-852` — where `midi_macos` is instantiated in `main()`
- `tauri/ui/scripts/codegen-ipc.mjs` — the codegen pattern that auto-regenerates `validator.generated.mjs`
- `tauri/ui/src/ipc/messages.schema.json:200-292` — the existing `IpcBoot` / `StatusTick` schema shape to mirror
- `tauri/ui/src/debrief/debrief-window.ts:1-100` — webview entrypoint pattern
- `tauri/ui/debrief.html:1-50` — second-window HTML entry pattern
- `tauri/ui/vite.config.ts:89-113` — multi-page rollup input pattern
- `tauri/src-tauri/src/main.rs:21-116` — mod registration + invoke_handler + manage pattern
- `tauri/ui/src/tokens.css:76-205` — design tokens (silk, void, amber, spacing)
- `.planning/research/SUMMARY.md` — 14 LOCKED axes (especially §5 RENDERER TECHNOLOGY)
- `.planning/research/PITFALLS.md:96-401` — P3 (HARDWARE), P4 (RENDERER), P5 (COPYRIGHT), P8 (LATENCY), P11 (A11Y)
- `.planning/phases/91-controller-renderer-midi-mirror/91-CONTEXT.md` — user-confirmed decisions
- `.planning/phases/91-controller-renderer-midi-mirror/91-UI-SPEC.md` — 6/6 PASS visual contract
- `.planning/REQUIREMENTS.md:18-27` — RENDER-01..RENDER-08

### Secondary (MEDIUM — referenced via SUMMARY/PITFALLS, verified through code)
- WCAG 2.1 dual-channel cue research (via PITFALLS §P11) — color + shape together for color-blind users
- Tauri 2.x WebviewWindowBuilder semantics — `debrief_window.rs` works, so we trust the API

### Tertiary (LOW — none for P91, the spine is fully verified in-tree)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every dep already shipping; zero new packages.
- Architecture: HIGH — every pattern (1 through 9) has an exact precedent in this repo (`debrief_window.rs`, `wizard/controllers/ddj-flx4.svg.ts`, `IpcRouterBus`, `port_watcher_task`, `ControllerState`).
- Pitfalls: HIGH — every pitfall has either a CI gate or a defer-to-KAAN-ACTION mitigation already pinned in CONTEXT.md.
- Latency contingency (§LEARN-LATENCY-CONTINGENCY): MEDIUM — the 50 ms target is reasonable but unverified on the production webview path until the CI gate runs.

**Research date:** 2026-05-27
**Valid until:** 2026-06-27 (30 days — stable spine, no fast-moving dep). Reset on any of: (a) Tauri major release, (b) mido / python-rtmidi major release, (c) §LEARN-LATENCY-CONTINGENCY triggering.

---

**Ready for planning.** Every locked decision in CONTEXT.md is reconciled with an exact-precedent code pattern. The planner can write tasks against:

- 7 new file paths under `src/vibemix/learn/` + `src/vibemix/ui_bus/learn_messages.py`
- 14+ new file paths under `tauri/ui/src/learn/` + `tauri/ui/tests/learn/` + `tauri/ui/learn.html`
- 1 new file under `tauri/src-tauri/src/learn_window.rs`
- 2 oneOf entries + 2 definitions in `tauri/ui/src/ipc/messages.schema.json`
- 3 lines in `tauri/src-tauri/src/main.rs`
- 3 lines in `tauri/ui/vite.config.ts`
- 1 entry in `tauri/src-tauri/capabilities/default.json`
- 1 additive kwarg in `src/vibemix/runtime/ws_bus.py` + 1 wiring block in `src/vibemix/__main__.py`

Plus a discrete `npm run codegen:ipc` task after the schema edit (CLAUDE.md mandate).

Plus 11 hand-authored controller SVG files (~80-120 hours of vector authoring — the load-bearing manual effort).
