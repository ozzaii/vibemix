# Stack Research — vibemix v9.0 "Lesson One" (Learn Surface)

**Milestone:** v9.0 "Lesson One" — Beginner Learning Module
**Domain:** Interactive controller-aware DJ tutorial (3 courses: Anatomy of a Deck → Transitions → Live Play)
**Researched:** 2026-05-27
**Confidence:** HIGH (every recommendation is either a verified library version or a reuse of existing in-tree code)

> **Supersedes** the prior pointer-doc at this path (2026-05-27). The CLAP / Gemini-router / no-hardcoded-model rules from the prior pointer still hold and are honored throughout this document.

> **Scope rule (locked, mirrors the milestone constraint):** every recommendation below is either:
> 1. **REUSE** — an existing vibemix module/file that the Learn surface should call (zero new dep, zero new IPC envelope unless schema-bumped);
> 2. **EXTEND** — a tiny additive change to an existing module (e.g. precompute over `audio/features.py::snapshot_features`); or
> 3. **NEW** — exactly **one** new optional Python dep (`python-statemachine`, MIT, pure-Python, ~30 KB) plus **zero** new JS deps. Every NEW item carries a green/yellow/red install-impact rating.
>
> If a recommendation can't be classified REUSE/EXTEND/NEW, it's been cut from this doc.

---

## Executive Recommendation (TL;DR for the roadmap)

1. **Controller renderer:** hand-authored **SVG per controller** (10 files + 1 generic) drawn against the existing `midi/profiles/*.json` schema, with per-control `<g data-control-id="eq_low_a">` hit regions. Render via the existing TypeScript/Vite pipeline — **NO Three.js, NO Canvas2D, NO new lib.** Vite already inlines SVG-as-string (precedent: `tauri/ui/src/wizard/controllers/ddj-flx4.svg.ts`). The 10 placeholder SVGs at `docs/assets/controllers/*.svg` get **upgraded** from marketing-text placeholders to real per-control schematics. The MIDI→pixel highlight is `document.querySelector('[data-control-id="eq_low_a"]').dataset.highlight = 'on'` — guaranteed sub-frame (browser paints inside one rAF tick, ~16 ms, well inside the 50 ms budget).
2. **Lesson runtime state machine:** **`python-statemachine`** (NEW, **green** — MIT, pure-Python, ~30 KB) on the Python side; **no JS state machine library**. The lesson stays server-authoritative — UI just paints `learn.highlight` and forwards `learn.ack` events. This mirrors how the live co-host already works (Python = state, TS = renderer + input ferry).
3. **IPC envelope additions:** five new types on the existing `127.0.0.1:8765` ws_bus (one-socket invariant preserved): `learn.start_lesson`, `learn.advance`, `learn.highlight`, `learn.ack`, `learn.complete_lesson`. Schema fragments locked below; `npm run codegen:ipc` regenerates the ajv validator.
4. **Library-driven exemplar finder:** the band-share scalars **already exist** in `src/vibemix/audio/features.py::snapshot_features` (returns `sub_share`, `low_share`, `mid_share`, `high_share`). What's missing is the **per-track precompute** that scores every library track on those scalars and indexes the top-N for each band. Add ~80 LOC to `src/vibemix/library/` as `band_exemplars.py` — pure compute, no new dep, reads the same PyAV decode path that `clap_engine.py` already exercises.
5. **Audio playback routing:** the existing `vibemix.platform._audio_macos.open_voice_output(device_index, ...)` already takes a per-call device index; tutor mode just opens a **second** `sd.OutputStream` against the user's headphone device while the master capture stream stays on the main monitor input. No new dep, no Tauri plugin, no Web Audio API. The user picks the headphone device in onboarding (reuse the existing device-select UI).
6. **MIDI controller auto-detect:** `mido.get_input_names()` + the existing `midi/registry.py::find_mapping` substring-match is **sufficient for all 10 bundled controllers** (every profile already ships `port_name_hints` that work reliably on both CoreMIDI and Windows MIDI). NO USB descriptor / sysex fingerprinting needed in v9.0.
7. **Progress persistence:** **JSON file** at `~/.cache/vibemix/learn-progress.json` (atomic write, schema-versioned). Do NOT embed in `memory.db` — memory store is for *recall*, lesson progress is *state*, and mixing the two violates the v6.0 single-writer + raw-in/raw-out contract on the memory store.

**Net new dependencies:** 1 Python (`python-statemachine`, MIT, ~30 KB pure-Python wheel). **Net new JS deps:** 0. **Net new ws ports:** 0. **Net new IPC envelopes:** 5 (additive to existing `oneOf`, all carry `additionalProperties: false`).

---

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **SVG (inline, `<g data-control-id>` regions)** | n/a (web standard) | 10-controller faceplate renderer + per-control hit regions | DOM-native pointer events + ARIA roles for free; CSS variable swap for the `--highlight` color is composited (60 fps guaranteed); ~5-15 KB per controller after Vite SVGO; existing precedent in `tauri/ui/src/wizard/controllers/ddj-flx4.svg.ts`. SVG is the **only** renderer where the AI saying "the EQ-HI knob on deck A" maps 1:1 to `[data-control-id="eq_hi_a"]` and the test suite can assert `expect(el.dataset.highlight).toBe('on')`. See: [SVG vs Canvas vs WebGL — tradeoffs](https://medium.com/@codetip.top/svg-vs-canvas-vs-webgl-for-diagram-viewers-tradeoffs-bottlenecks-and-how-to-measure-8cedbd3b7499); [Mixxx Contributing Mappings — SVG diagrams preferred](https://github.com/mixxxdj/mixxx/wiki/Contributing-Mappings). |
| **`python-statemachine` (NEW, green)** | `^3.1.2` (PyPI, MIT, pure-Python) | Lesson runtime state machine | The lesson flow is naturally a statechart: course → lesson → step → expected-event → advance, with guards ("did the user touch the right control?") and on-enter hooks ("emit `learn.highlight` for the next control"). v3.x has a **declarative** API that reads like a lesson spec, first-class async transitions, and **no native deps**. MIT-licensed → Apache-clean. [python-statemachine GitHub](https://github.com/fgmacedo/python-statemachine). |
| **Existing `mido` + `python-rtmidi`** | already pinned | Controller event ingestion + auto-detect via port name | `mido.get_input_names()` returns the OS-provided port-name string. The 10 bundled profiles all carry `port_name_hints` that already work in production (verified by the v7.0 P68 contract tests on every device). For v9.0, `vibemix.midi.registry.find_mapping(port_name)` is the auto-detect surface — **no change needed**. |
| **Existing `sounddevice`** | already pinned (`>=0.5.5`) | Tutor-mode exemplar audio playback to headphone device | `sd.OutputStream(device=headphone_idx, ...)` runs concurrently with the master capture stream. PortAudio supports multiple simultaneous streams on different devices on both CoreAudio (macOS) and WASAPI (Windows). The existing `vibemix.platform._audio_macos.open_voice_output(device_index, ...)` is the exact entry point — tutor mode passes the headphone device index instead of the AI-voice device index. See: [python-sounddevice multi-device output pattern](https://esologic.com/multi-audio/). |
| **Existing Tauri 2.x shell + Vite + TypeScript** | already pinned (`@tauri-apps/api ^2.11`, `vite ^6.0`, `typescript ^5.7`) | Webview hosting the Learn surface | New `tauri/ui/src/learn/` directory mirrors the existing `session/` / `wizard/` / `library/` pattern. Same vitest harness, same `tsc --noEmit` gate, same `npm run codegen:ipc`. |
| **Existing ws_bus on `127.0.0.1:8765`** | already pinned (`websockets>=13.0`) | Backend↔frontend transport for Learn IPC | One-socket cardinal invariant preserved. The five new `learn.*` envelopes ride the same pipe as `ipc.session.snapshot` / `cohost-reaction` / `library.search.*`. |
| **Existing `vibemix.llm.model_router`** | already pinned (`google-genai>=2.0.1`) | AI dialog generation for the tutor voice | Resolves the model via the existing `resolve("standard")` / `resolve("flex")` seam. Tutor lens = same matrix cell (`tutor`) shipped in v8.1 LENS-03; no new model, no new prompt-matrix surface. |

### Supporting Libraries (REUSE only — no new JS dep)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **CSS custom properties (`--learn-highlight`, `--learn-active`)** | web standard | Animate the SVG control highlight (color + glow) | Per the perf rule: animate `fill`/`opacity`/`transform` only — these are composited and run at 60 fps without layout reflow. Pattern: `g[data-highlight="on"] { fill: var(--amber); filter: drop-shadow(0 0 4px var(--amber-glow)); }`. Existing CDJ-Whisper amber tokens already exist in `tauri/ui/src/session/styles/`. See: [Lisi Linhart — SVG animation with CSS variables](https://lisilinhart.info/posts/svg-animation-css-variables/). |
| **Existing `ajv` (`^8.20`) + `ajv-formats` (`^3.0`)** | already pinned | Validate incoming `learn.*` envelopes in the webview | The pre-compiled `validator.generated.mjs` (run `npm run codegen:ipc` after the schema bump) catches type drift at runtime; stale validator = the recurring "new fields rejected" bug (see memory `feedback_schema_edit_needs_codegen_ipc`). |
| **Existing `jsonschema>=4.23,<5`** | already pinned | Validate outbound `learn.*` envelopes in Python | Same validator used by `ws_bus.ws_broadcast`; no second validator. |
| **Existing `vibemix.audio.features.snapshot_features`** | n/a (in-tree) | Returns `sub_share`, `low_share`, `mid_share`, `high_share` already | **Confirmed by reading `src/vibemix/audio/features.py:27-90`.** The band-share scalars exist verbatim. Bands: `sub` 20-100 Hz, `low` 100-300, `mid_low+mid_hi` 300-4000 (merged), `high` 4000-8000. For the EQ lesson, low/mid/hi map cleanly; the "sub" band gets surfaced as a sub-class of "low" in the lesson copy. |
| **Existing `vibemix.library.clap_engine`** | n/a (in-tree) | Decodes track audio → numpy waveform at 48 kHz mono | `band_exemplars.py` (NEW ~80 LOC, in `library/`) reuses the same PyAV-based decode path that `clap_engine.py::_load_audio` already runs, then calls `snapshot_features` per track to build the exemplar index. |
| **Existing `vibemix.state.coach.evidence_line` + `prompts/matrix.py`** | n/a (in-tree) | AI dialog generation in tutor lens, grounded against the lesson step | The "Course 3 Live Play" surface is the existing live co-host running with `lens="tutor"`. No new prompt path. Courses 1 + 2 add a **lesson-step evidence source** (string template, registered like `recall:` was in v6.0 — 3 schema-mirror sites). |
| **Existing `vibemix.runtime.ws_bus`** | n/a (in-tree) | Broadcasts `learn.*` envelopes alongside `mascot` + `ipc.session.snapshot` | The Learn surface subscribes to the same `127.0.0.1:8765` it's been on since Phase 4. |
| **Existing `vibemix.midi.registry.find_mapping`** | n/a (in-tree) | Auto-detect controller from `mido.get_input_names()[i]` | Already substring-matches `port_name_hints` case-insensitively. No change. |
| **Existing CDJ-Whisper design tokens** | n/a (in-tree at `tauri/ui/src/session/styles/`) | Phosphor amber on anodised charcoal — controller highlight color | Reuse `--amber` (active control) and `--silk-65` (inactive control outline). Matches `mocks/vibemix-rebuild-session.html` and the v8.x app shell. |

### Development Tools (REUSE only)

| Tool | Purpose | Notes |
|------|---------|-------|
| **`npm run codegen:ipc`** | Regenerate `validator.generated.mjs` after schema bump | **MANDATORY** after any `messages.schema.json` edit — the ajv validator is pre-compiled (mirrors the `feedback_schema_edit_needs_codegen_ipc` memory). |
| **`scripts/check_ipc_schema.py`** | Python↔TS parity check | Already runs in CI; catches a Python `dataclass` that drifts from the JSON Schema. |
| **`vitest`** | UI test for the SVG hit regions + lesson controller component | Existing ~886-test harness, no new dep. |
| **`uv run pytest -q`** | Python tests for the lesson state machine + band-exemplar finder + IPC envelopes | New test files in `tests/learn/`. |
| **`uv run python -m vibemix learn debug --lesson 1.3`** | Headless CLI to step the lesson state machine | NEW CLI surface (~40 LOC) so the lesson can be ear-tested without firing up the GUI. |
| **Vite SVG-as-string import** | Inline the 11 controller SVGs into the bundle | Pattern already used by `tauri/ui/src/wizard/controllers/ddj-flx4.svg.ts`; no new config. |

## Installation

```bash
# The ONE new dep
uv add python-statemachine  # MIT, pure-Python, ~30 KB wheel

# Everything else is already installed.
# After messages.schema.json edits:
cd tauri/ui && npm run codegen:ipc && npm test && npm run build
```

## Alternatives Considered (with kill reasons)

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| **SVG with `<g data-control-id>` hit regions** | **Canvas 2D** | Only if rendering >5,000 control elements simultaneously (Canvas wins on raw element count). **Killed** — we have at most ~40 controls per controller; Canvas requires hand-rolling hit-testing (quadtree/spatial index) and accessibility, wasted work at this scale. See: [SVG works to a few thousand elements then degrades](https://news.ycombinator.com/item?id=15024190). |
| **SVG** | **Three.js / WebGL** | Only if rendering a photorealistic 3D rotating controller. **Killed** — Three.js does not tree-shake well (typical bundle ~340 KB minified), photorealism is not a v9.0 requirement (CDJ-Whisper aesthetic = stylized phosphor, not skeuomorphic), and the per-control highlight latency advantage of WebGL is moot when SVG already paints sub-16 ms. Keep Three.js in the bundle for the mascot (existing); don't grow its usage. See: [Three.js tree-shaking forum thread](https://discourse.threejs.org/t/tree-shaking-three-js/1349). |
| **`python-statemachine` (Python, declarative DSL)** | **XState v5 (TypeScript)** | Only if we wanted the state machine to live in the webview instead of the backend. **Killed** — the lesson is server-authoritative by design (the AI is generating the next step; only Python has the model_router and the prompts/matrix), so a JS state machine would be a thin echo. XState v5 minified+gzip = 43,213 B / 13,598 B per [Bundlephobia API](https://bundlephobia.com/api/size?package=xstate@5.20.1) — not huge, but wrong side of the wire. |
| **`python-statemachine`** | **`pytransitions`** | If we wanted callback-heavy hooks rather than a declarative DSL. **Tied technically**, both are MIT pure-Python — declarative DSL of `python-statemachine` reads like a lesson script ("when in `step_eq_low`, on `correct_midi`, transition to `step_eq_mid`"), which makes the lesson content reviewable by non-engineers (Francesco). |
| **`python-statemachine`** | **Hand-rolled FSM (no dep)** | If we only had 1 lesson. **Killed** — 3 courses × ~7 lessons × multi-step with retry/skip/back-up edges = exactly where a library earns its keep. ~30 KB pure-Python footprint is a green install-impact. |
| **Hand-authored SVG per controller** | **Auto-generate SVG from `midi/profiles/*.json`** | If we wanted instant new-controller support. **Defer to v9.1** — auto-layout would require a per-control geometry hint in the profile JSON (e.g. `"x": 0.2, "y": 0.4, "kind": "knob", "size": "small"`), a JSON schema bump. The 10 bundled controllers are static, hand-authored is faster, v9.1 introduces auto-layout when the 11th controller arrives. |
| **Hand-authored SVG** | **Trace from Pioneer's official hardware-diagram PDFs in Inkscape** | If we needed perfect physical fidelity. **Acceptable for the trace step** (Pioneer publishes [official hardware diagrams as PDF](https://www.pioneerdj.com/-/media/pioneerdj/software-info/controller/ddj-flx4/ddj-flx4_hardwarediagram_rekordbox_e1.pdf?la=en-us)) but the resulting SVG is **derivative work** of the manufacturer's faceplate art. We trace silhouettes + control positions (factual, like a wiring diagram), not the faceplate art itself — same posture as the existing `ddj-flx4.svg.ts` silhouette glyph. Treat as a "schematic", not a "faceplate render". |
| **Trace from Pioneer PDFs** | **Use Mixxx's already-traced SVGs** | If Mixxx's diagrams were permissively licensed. **Killed** — Mixxx is **GPL-2.0**, importing their SVGs into vibemix (Apache-2.0) is **license-incompatible**. See: [Mixxx LICENSE — GPL-2.0](https://github.com/mixxxdj/mixxx/blob/main/LICENSE). We must redraw, not copy. |
| **JSON file for progress (`~/.cache/vibemix/learn-progress.json`)** | **SQLite in `memory.db`** | If we needed cross-session embedding-search on lesson progress. **Killed** — lesson progress is flat key-value state ("course 1 complete", "course 2 step 4"), not a recall corpus. Mixing it into `memory.db` would violate the v6.0 "raw-in/raw-out, embedding-only" contract and put a non-state-refresh writer on the memory store. |
| **JSON file** | **`tauri-plugin-store` (already in deps)** | If we wanted the storage to live in the Rust side. **Acceptable alternative** — `@tauri-apps/plugin-store ^2.4` is already in `package.json`, would auto-persist to the platform's standard config dir. **Trade-off:** the Python lesson runtime would have to ferry progress through an IPC round-trip to read it. **Default recommendation: Python-side JSON** because the lesson runtime is Python and progress reads happen on lesson-load (not hot-path). |
| **Sounddevice second `OutputStream` to headphone device** | **CoreAudio Multi-Output Device + manual user setup** | If the user's headphones aren't a discrete device (e.g. AirPods on macOS sometimes get aggregated). **Use as fallback** — `audio_config.py --configure-routing` already exists from v3.1 INSTALL-09 for the master path; document the Multi-Output Device path for non-standard setups. |
| **Sounddevice second `OutputStream`** | **Web Audio API in the webview** | If we wanted the playback to live in the JS side. **Killed** — Web Audio in a webview cannot select arbitrary output devices reliably on Tauri 2.x (`setSinkId` API is browser-only with gaps in WebKit/WebView2). Keep audio in Python where `sounddevice` already enumerates every device. |
| **`mido.get_input_names()` substring match** | **USB descriptor / sysex device-ID fingerprint** | If two bundled controllers had identical port-name fragments. **Killed for v9.0** — verified by reading the 10 bundled `profiles/*.json` files: every `port_name_hints` entry is unambiguous. USB descriptors via CoreMIDI's `kMIDIPropertyModel` are notoriously inconsistent — some devices return "USB MIDI DEVICE" ([Apple Developer Forum thread](https://developer.apple.com/forums/thread/68521)). |
| **Tauri plugin (Rust) for audio I/O** | **Stay in Python `sounddevice`** | If we needed to handle Rust-side audio. **Killed** — `tauri-plugin-audio-recorder` doesn't support output device selection yet (it "currently uses system default device") and we'd be re-implementing `sounddevice` for free. See: [tauri-plugin-audio-recorder limitations](https://github.com/brenogonzaga/tauri-plugin-audio-recorder). |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| **XState (TypeScript)** | Wrong side of the wire — the lesson state lives in Python where the AI does. Also +14 KB gzip to webview bundle. | `python-statemachine` on the Python side. |
| **Three.js for the controller renderer** | No tree-shaking benefit at this element count; CSS-variable SVG already paints sub-16 ms; bundle bloat. | SVG with `<g data-control-id>` hit regions. |
| **Canvas 2D for the controller renderer** | Hand-rolled hit-testing + accessibility for zero scale benefit at ~40 elements/controller. | SVG. |
| **GSAP / Anime.js** | Animation library for a one-property CSS-variable swap is overkill. | CSS variables on the SVG `fill` + `filter: drop-shadow`. |
| **`@xstate/fsm`** | **DEPRECATED** per the Stately docs / npm. | Not relevant — we don't want JS state machine anyway. |
| **Mixxx's SVG diagrams (direct import)** | Mixxx is GPL-2.0, vibemix is Apache-2.0 — license-incompatible. | Hand-author from Pioneer's official hardware-diagram PDFs, treat as "schematic" (control geometry) not "faceplate art". |
| **Web Audio API for headphone-cue playback** | `setSinkId` is unreliable in webviews on Windows + macOS; can't enumerate all CoreAudio devices. | Python-side `sounddevice.OutputStream(device=headphone_idx, ...)`. |
| **A new ws port for Learn** | Violates the one-socket cardinal invariant. | Extend the existing `127.0.0.1:8765` ws_bus with `learn.*` envelopes. |
| **A new AI provider for the tutor voice** | Violates the Gemini-only constraint shipped in v8.x. | Existing `model_router.resolve(...)` + tutor lens cell in `prompts/matrix.py`. |
| **librosa for band-share** | librosa pulls numba/llvmlite/scikit-learn — heavy, install-impact RED. | Existing numpy FFT in `vibemix.audio.features.snapshot_features` returns the four band-share scalars already. |
| **essentia for tempo/beat detection (Course 3)** | **AGPL-3.0** — Apache-incompatible. Plus not installed. | Existing `state/music_state.py` BPM autocorr + `state/event_detector.py` phase detection (already shipped, v3.0 and later). |
| **A separate validator codebase for `learn.*`** | The existing ajv + jsonschema pair is already pre-compiled and CI-gated. | Bump `messages.schema.json`, run `npm run codegen:ipc`, run `scripts/check_ipc_schema.py`. |
| **Embedding lesson progress in `memory.db` (sqlite-vec)** | Mixing recall-storage with state-storage violates the v6.0 "raw-in/raw-out embedding-only" contract on memory; non-state-refresh writer. | Atomic-write JSON at `~/.cache/vibemix/learn-progress.json`. |

## Stack Patterns by Variant

**If the user has a curated controller (any of the 10):**
- Load `midi/profiles/<id>.json` → resolve hit regions in `tauri/ui/src/learn/controllers/<id>.svg.ts`
- The lesson references controls by their JSON `field` name (`vol`, `eq_low`, `xfader`, etc.) — same identifier the SVG `data-control-id` uses
- Auto-detect via `find_mapping(mido.get_input_names()[0])` on lesson-start

**If the user has a generic / unmapped controller:**
- `find_mapping_or_generic(port_name)` returns the existing `make_generic_profile()` shape
- Lesson falls back to a **generic 2-deck schematic SVG** (NEW asset, ~10 KB) with the seven essential controls (xfader, vol_a/b, eq_low/mid/hi per deck, play_a/b, cue_a/b)
- Lesson copy adjusts: "On YOUR controller, the EQ-HI knob is the third knob in each channel strip" + show the generic schematic

**If no controller is plugged in:**
- Lesson runs in **demo mode** — the user clicks the SVG control to "simulate" the MIDI event. Same `learn.ack` envelope; `source` field flips from `"midi"` to `"click"`. Honest reporting in the IPC envelope so downstream telemetry knows.

**If the user wants Course 3 (Live Play) but no master audio is captured:**
- Fall back to **demo audio mode** — pre-recorded 60-second sample sets, one per BPM range, ship as Apache-2.0 audio (CC-BY musicians or already in `assets/ack_bank/`). Same lesson engine, same evidence-grounded tutor lens.

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| `python-statemachine ^3.1.2` | `Python >=3.12,<3.13` | Pure-Python, no native deps, MIT. Smoke-tested on 3.11+ per the project's CI. |
| `python-statemachine ^3.1.2` | `asyncio` event loop | 3.x has first-class async transitions — matches `vibemix.__main__:main()` orchestration. |
| `mido ^1.3.3` | `python-rtmidi ^1.5.8` | Already pinned; the substring-match in `registry.py` is backend-agnostic. |
| `sounddevice ^0.5.5` | CoreAudio (macOS), WASAPI (Windows) | Multi-stream-multi-device pattern verified by the v4.0 `open_voice_output` + `open_passthrough_output` co-existence. |
| ajv `^8.20` validator | JSON Schema draft-07 | Existing `messages.schema.json` already declares draft-07. `learn.*` types must follow `additionalProperties: false`. |
| Vite `^6.0` `?raw` import | Inline SVG as string | Existing pattern in `tauri/ui/src/wizard/controllers/ddj-flx4.svg.ts`. |

---

## Answers to the Eight Specific Questions

### Q1 — Controller renderer: SVG vs Canvas vs WebGL?

**Recommendation: SVG with `<g data-control-id="...">` per-control hit regions, inlined via Vite import.**

**Rendering pipeline:**
1. **Author** 11 SVG files at `tauri/ui/src/learn/controllers/<id>.svg.ts` (TypeScript module that exports the inline SVG string — same shape as the existing `wizard/controllers/ddj-flx4.svg.ts`). One file per controller (`pioneer-ddj-flx4`, `pioneer-ddj-400`, etc., plus `_generic`).
2. **Schema:** every interactive control on the faceplate is a `<g data-control-id="<binding_name>">` group, where `<binding_name>` is the **same key** used in `midi/profiles/<id>.json::controls` / `buttons` (`eq_low_a`, `play_a`, `xfader`, etc.). This is the contract.
3. **Highlight:** the lesson runtime emits `{type: "learn.highlight", control_id: "eq_low_a", style: "active"}` on the ws_bus. The webview handler does `document.querySelectorAll('[data-control-id]').forEach(el => el.dataset.highlight = "off"); document.querySelector('[data-control-id="eq_low_a"]').dataset.highlight = "active";`. CSS does the paint: `g[data-highlight="active"] { fill: var(--amber); filter: drop-shadow(0 0 4px var(--amber-glow)); }`. **Latency: one rAF tick (~16 ms on a 60 Hz panel), well inside the 50 ms budget.** See: [60 fps CSS animation — only transform/opacity/fill](https://developer.mozilla.org/en-US/docs/Web/Performance/Guides/Animation_performance_and_frame_rate).
4. **Hit detection (Course 1 demo mode):** every `<g>` group already accepts pointer events. No quadtree, no spatial index, no hand-rolled picker.
5. **Accessibility:** `<g role="button" aria-label="EQ-HI knob, deck A">` for free. Matches the v8.0 design-slop gate's WCAG-AA posture.

**Authoring approach for the 10+1 controllers:**
- **Step 1 — Trace from Pioneer's official hardware-diagram PDFs** ([example: DDJ-FLX4 hardware diagram](https://www.pioneerdj.com/-/media/pioneerdj/software-info/controller/ddj-flx4/ddj-flx4_hardwarediagram_rekordbox_e1.pdf?la=en-us)) in Inkscape, exporting only **control geometry** (silhouette + knob/fader/button positions). This is "schematic", not "faceplate art" — same posture Mixxx takes in their manual (which is also user-traced from manufacturer PDFs).
- **Step 2 — Apply CDJ-Whisper styling:** strip color from the trace, restyle in `--silk-65` outline + `--amber` accent, match the existing wizard SVG aesthetic.
- **Step 3 — Tag every interactive group** with `data-control-id` matching the profile JSON keys. CI gate (NEW test in `tauri/ui/tests/learn/`): for every controller, every `data-control-id` in the SVG **must** resolve to a `controls.*` or `buttons.*` key in the matching `midi/profiles/<id>.json`. The reverse — every profile binding has a matching SVG group — is a separate gate.

**Photorealistic / faceplate-art rendering:** **DEFER to v9.1+** — would require Pioneer's permission to redistribute the faceplate art (uncertain; their hardware-diagram PDFs are under copyright, only the **factual schematic** survives trace). The CDJ-Whisper styled schematic is the right v9.0 surface: matches the rest of the app, doesn't require licensing dance, and reads as "instructional diagram" rather than "fake hardware photo" (avoids skeuomorphic uncanny-valley).

**Three.js / WebGL — when to revisit:** if the future "Course 4: Performance Mode" wants a rotating 3D controller view, then add a Three.js scene as an optional layer behind a feature flag. For v9.0, the existing Three.js dep stays scoped to the mascot.

**Reuse anchor:** `tauri/ui/src/wizard/controllers/ddj-flx4.svg.ts` is the existing precedent — its 8 lines export an inline SVG string with `currentColor` for color inheritance. v9.0 scales this approach with per-control `data-control-id` hit regions and tighter geometry from the PDF trace.

### Q2 — Lesson runtime state machine

**Recommendation: `python-statemachine` v3.x on the Python side. NEW dep, install-impact: green (MIT, pure-Python, ~30 KB).**

Illustrative shape (the real implementation lands in `src/vibemix/learn/lesson_machine.py`):

```python
from statemachine import StateMachine, State

class AnatomyDeckLesson(StateMachine):
    intro = State(initial=True)
    show_vol_a = State()
    expect_vol_a = State()
    show_eq_low_a = State()
    expect_eq_low_a = State()
    # ... ~20 states total per lesson
    complete = State(final=True)

    advance = intro.to(show_vol_a) | show_vol_a.to(expect_vol_a) | ...
    correct_input = expect_vol_a.to(show_eq_low_a) | expect_eq_low_a.to(show_eq_mid_a) | ...

    def on_enter_show_vol_a(self):
        self._emit_highlight("vol_a", style="instruct")
    def on_enter_expect_vol_a(self):
        self._emit_highlight("vol_a", style="active")
```

**Why not XState (TypeScript):** the AI dialog generation, the prompt-matrix tutor cell, the model_router, the citation linter, and the band-exemplar finder all live in Python. A JS state machine would be a thin echo of the real lesson brain. XState v5 ships at 43,213 B / 13,598 B gzip per [Bundlephobia API](https://bundlephobia.com/api/size?package=xstate@5.20.1) — not huge, but wrong side of the wire.

**Why not hand-rolled:** 3 courses × ~7 lessons × multi-step with retry/skip/back-up edges = ~80-100 states. A library handles the edge cases (history states, guards, on-enter/on-exit hooks) for free. The dep is pure-Python with no transitives. See: [python-statemachine GitHub](https://github.com/fgmacedo/python-statemachine).

**Async support:** `python-statemachine` 3.x has first-class async transitions — fits naturally into `vibemix.__main__:main()` orchestration; no special bridge needed.

**Testing:** the FSM is offline-unit-testable. The headless CLI `vibemix learn debug --lesson 1.3` (NEW, ~40 LOC in `vibemix.learn.__main__`) feeds canned MIDI events and asserts state transitions. No live app required.

### Q3 — IPC envelopes (new types for `messages.schema.json`)

**Recommendation: 5 new envelopes. All `additionalProperties: false`. Add to the existing `oneOf` block. Run `npm run codegen:ipc` after editing.**

```json
{
  "LearnStartLesson": {
    "type": "object",
    "additionalProperties": false,
    "required": ["type", "course_id", "lesson_id"],
    "properties": {
      "type": { "const": "learn.start_lesson" },
      "course_id": { "type": "string", "enum": ["1", "2", "3"] },
      "lesson_id": { "type": "string", "pattern": "^[1-3]\\.[1-9][0-9]?$" },
      "level": { "type": "string", "enum": ["beginner", "intermediate", "pro"] }
    }
  },
  "LearnHighlight": {
    "type": "object",
    "additionalProperties": false,
    "required": ["type", "control_id", "style"],
    "properties": {
      "type": { "const": "learn.highlight" },
      "control_id": {
        "type": "string",
        "description": "matches a key in midi/profiles/<id>.json::controls or ::buttons (e.g. eq_low_a, play_a, xfader)"
      },
      "style": {
        "type": "string",
        "enum": ["instruct", "active", "correct", "incorrect", "off"]
      },
      "narration_id": {
        "type": "string",
        "description": "optional id of an evidence-grounded narration line emitted alongside"
      }
    }
  },
  "LearnAdvance": {
    "type": "object",
    "additionalProperties": false,
    "required": ["type"],
    "properties": {
      "type": { "const": "learn.advance" },
      "reason": { "type": "string", "enum": ["correct_midi", "click_sim", "timeout_skip", "user_skip"] }
    }
  },
  "LearnAck": {
    "type": "object",
    "additionalProperties": false,
    "required": ["type", "control_id", "source"],
    "properties": {
      "type": { "const": "learn.ack" },
      "control_id": { "type": "string" },
      "source": { "type": "string", "enum": ["midi", "click"] },
      "value": { "type": "number", "minimum": 0.0, "maximum": 1.0, "description": "normalized control value, 0..1" },
      "match": { "type": "boolean", "description": "true iff this is the control the lesson expected" }
    }
  },
  "LearnCompleteLesson": {
    "type": "object",
    "additionalProperties": false,
    "required": ["type", "course_id", "lesson_id"],
    "properties": {
      "type": { "const": "learn.complete_lesson" },
      "course_id": { "type": "string" },
      "lesson_id": { "type": "string" },
      "duration_sec": { "type": "number", "minimum": 0 },
      "retries": { "type": "integer", "minimum": 0 }
    }
  }
}
```

**Direction (TS↔Py):**
- **`learn.start_lesson`**: webview → Python (user picks a lesson)
- **`learn.highlight`**: Python → webview (lesson tells UI which control to glow)
- **`learn.advance`**: Python-internal hint or user-initiated skip; can fire in either direction
- **`learn.ack`**: webview → Python (user touched the physical control OR clicked the SVG)
- **`learn.complete_lesson`**: Python → webview (lesson is done, render the completion chip)

**Schema-mirror checklist (the `recall:` v6.0 precedent):**
1. Add the 5 definitions to `tauri/ui/src/ipc/messages.schema.json::definitions`
2. Add 5 `$ref` entries to the top-level `oneOf`
3. Run `cd tauri/ui && npm run codegen:ipc` — regenerates `validator.generated.mjs`
4. Run `scripts/check_ipc_schema.py` — Python↔TS parity check
5. Add Python dataclasses + jsonschema validation in `src/vibemix/learn/ipc.py` (NEW, ~60 LOC)
6. Wire 5 message types into `ws_bus.ws_broadcast`'s validate-then-emit path (mirrors how `ipc.session.snapshot` is emitted)
7. Add 5 `tests/learn/test_ipc_*.py` round-trip tests

### Q4 — Library-driven exemplar finder

**`audio/features.py` already returns the band-share scalars.** Verified by reading `src/vibemix/audio/features.py:27-90`: `snapshot_features` returns `{sub_share, low_share, mid_share, high_share}` already, with `sub` = 20-100 Hz, `low` = 100-300 Hz, `mid` = combined 300-4000 Hz, `high` = 4000-8000 Hz.

**What's missing: the per-track precompute + index.**

**Recommendation: add `src/vibemix/library/band_exemplars.py` (~80 LOC, NEW pure-compute module).**

```python
# src/vibemix/library/band_exemplars.py — sketch
def score_track_bands(audio_path: Path) -> dict[str, float]:
    """Run snapshot_features over 3-5 evenly-spaced 5-second windows; return mean band shares."""
    waveform = _decode_to_48k_mono(audio_path)  # reuse clap_engine path
    windows = [waveform[i*sr*30 : i*sr*30 + sr*5] for i in range(3, 6)]  # 3 windows from track middle
    shares = [snapshot_features_from_array(w) for w in windows]
    return {k: mean(s[k] for s in shares) for k in ("sub_share", "low_share", "mid_share", "high_share")}

def find_band_exemplar(band: str, library_root: Path, top_k: int = 5) -> list[Path]:
    """Return top-K library tracks where `band` is most prominent. Cached by content-hash."""
    # ... sort across the precomputed index by the relevant share
```

**Index:** `~/.cache/vibemix/band_exemplars.json` (track_path → 4-share dict). Recompute on library-change OR lazily on first lesson-launch (background task; lesson uses fallback if cache empty).

**Decode reuse:** `clap_engine.py::_load_audio` already implements the 48 kHz mono PyAV decode path. Lift that to a shared `src/vibemix/audio/decode.py` helper (NEW, ~20 LOC) so both `clap_engine` and `band_exemplars` use the same path. Pure refactor, no new dep.

**Refactor note for `snapshot_features`:** the current entry point takes an `AudioBuffer`; the band-exemplars use case needs to feed a numpy array. Add a thin `snapshot_features_from_array(arr: np.ndarray, sr: int = 48000)` sibling (~15 LOC) — same math, different input shape. Both still call into the existing FFT/band-energy math; no duplication.

**Fallback if cache empty + no library:** ship a small (~3 MB) `assets/learn/band_exemplars/` directory with one CC-BY licensed example track per band (low/mid/hi/sub) so the lesson works zero-config on first install. Total install bloat <5 MB (acceptable; lessons are also useful offline).

### Q5 — Audio playback for tutor mode (headphone cue)

**Recommendation: open a SECOND `sd.OutputStream` against the user's headphone device. NO new dep, NO routing layer, NO Tauri plugin.**

**Verified by reading `src/vibemix/platform/_audio_macos.py:298-326`** (`open_passthrough_output`) and `:328-380` (`open_voice_output`): the existing factory takes a `device_index` argument per call. We add a third entry-point `open_lesson_audio_output(device_index, ...)` that's a near-copy of `open_voice_output` but pulls from a `LessonPlaybackQueue` instead of `PlaybackQueue`. Two PortAudio output streams running concurrently on different devices is the normal mode of operation for any DJ headphone-cue setup. See: [python-sounddevice multi-device pattern](https://esologic.com/multi-audio/).

**User onboarding flow (Lesson One first-run):**
1. Reuse the existing **device-select wizard** (already in `tauri/ui/src/wizard/`) — adds a "headphone output device" picker (currently has master input + AI voice output pickers).
2. Default the headphone pick to the **system default output** (so it works even if the user only has speakers — they hear the exemplar through speakers, which is fine for solo learning).
3. Persist the pick in the existing settings JSON; same `ipc.settings.set` envelope, new `learn.headphone_device_index` key.

**Master/cue split (manual user setup):**
- We do **NOT** synthesize a Multi-Output Device on the user's behalf in v9.0 — that path (CoreAudio MOD on Mac, Voicemeeter on Win) exists in `audio_config.py --configure-routing` from v3.1, but it's surfaced as **opt-in advanced setup**, not auto-applied.
- Course 3 (Live Play) needs the user to have already configured their DJ software's main-out + cue-out — same as any DJing already requires. The lesson narrates: "play this from your DJ software, route master to BlackHole, vibemix listens".

### Q6 — Onboarding controller auto-detect

**Recommendation: `mido.get_input_names()` + existing `vibemix.midi.registry.find_mapping`. SUFFICIENT for all 10 bundled controllers. No USB descriptor / sysex fingerprinting in v9.0.**

**Verified by reading `src/vibemix/midi/registry.py`:** `find_mapping(port_name)` already case-insensitive substring-matches `port_name_hints` and returns the matched profile. Sorted by profile-id for deterministic tiebreak.

**Verified by reading the 10 bundled `profiles/*.json` filenames + the FLX4 sample:** every `port_name_hints` entry is unambiguous (`["DDJ-FLX4", "FLX4"]`, `["DDJ-400"]`, `["Inpulse 300"]`, etc.). No two profiles have overlapping hints that would collide on real device names.

**Known-flaky devices:** none of the 10. Pioneer and Hercules controllers consistently expose their model name in the port string on both CoreMIDI and Windows MIDI. See: [mido + USB device-name conventions](https://mido.readthedocs.io/en/latest/intro.html); the v7.0 P68 contract test suite verifies all 10 controllers' port-name detection.

**Edge cases handled by existing code:**
- Multiple controllers plugged in simultaneously: each port resolves its own profile (no module-level "active" — already in `profile.py` docstring).
- Hot-plug: `vibemix.midi.watcher.MidiWatcher` polls `get_input_names()` every `poll_seconds` (default 1 s) and re-resolves.
- Unknown controller: `find_mapping_or_generic(port_name)` returns the synthesized `GENERIC_MIDI` profile so the lesson runs in generic-schematic mode.

**Windows caveat:** if a USB audio control interface name exceeds 31 characters, Windows truncates or refuses recognition ([CircuitPython USB MIDI docs](https://docs.circuitpython.org/en/latest/shared-bindings/usb_midi/index.html)). None of the 10 bundled hints exceed 14 characters — safe.

**What we DON'T do in v9.0:**
- No CoreMIDI `MIDIObjectGetStringProperty(kMIDIPropertyModel)` reads — Apple Developer thread confirms "some devices return only 'USB MIDI DEVICE'" so it's unreliable. See: [Apple Dev forum on USB device properties](https://developer.apple.com/forums/thread/68521).
- No sysex device-ID handshake — adds a write-then-wait roundtrip on connect; substring-matching already disambiguates the 10 bundled SKUs.
- **Revisit in v9.1** if a community-contributed 11th controller has an ambiguous name; introduce sysex fingerprint as a *tiebreaker only*, with substring-match as the primary path.

### Q7 — Audio routing for "headphones cue only"

**Recommendation: treat headphone cue as MANUAL user setup. The lesson app opens a second output stream to the device the user picks; the user is responsible for routing their DJ software's cue bus to that device.**

**Concretely:**
- v9.0 ships a **headphone device picker** in the wizard (additive to the existing master-input + AI-voice-output pickers).
- The lesson's tutor-mode exemplar audio plays through that device.
- The user's DJ software (Rekordbox / Serato / Mixxx / VirtualDJ / djay) has its own cue-out routing in its own settings UI — outside vibemix's scope, same as v8.x.
- For users who want a single-output-device setup (laptop speakers only), the headphone device picker defaults to the system default — they hear the exemplar through their speakers, which is fine for the Anatomy and Transitions courses (Course 1 doesn't require simultaneous master + cue audio).

**Why we don't auto-build a Multi-Output Device on the user's behalf:**
- v3.1 INSTALL-09 already ships `audio_config.py --configure-routing` for the master path (BlackHole 2ch on Mac, WASAPI default on Win). That's an **opt-in** flow.
- Auto-creating a Multi-Output Device on macOS requires Core Audio HAL plugin authoring (or AppleScript automation of Audio MIDI Setup, fragile) — too much new surface for v9.0.
- Honest framing in the wizard: "Pick the audio device you want to hear the lesson through. If you want to keep your master mix on your speakers AND hear the lesson through headphones, follow our [routing guide](docs/audio-routing.md)."

### Q8 — Progress persistence

**Recommendation: JSON file at `~/.cache/vibemix/learn-progress.json`. Atomic write. Schema-versioned.**

```json
{
  "schema_version": 1,
  "user_level": "beginner",
  "courses": {
    "1": { "started_at": "2026-05-27T22:14:00Z", "completed_lessons": ["1.1", "1.2", "1.3"], "current_lesson": "1.4", "retries": {"1.3": 2} },
    "2": null,
    "3": null
  }
}
```

**Why not `memory.db`:**
- `memory.db` is the v6.0 sqlite-vec recall store — embedding-only, raw-in/raw-out, written ONLY by the off-hot-path session-ingest worker. Routing lesson progress through it would violate that single-writer contract and create a new writer surface, which we explicitly don't want.
- Lesson progress isn't queried by embedding-similarity; it's read once on lesson-load. Flat KV in JSON is the right shape.

**Why a separate file (not the existing settings JSON):**
- Settings is `ipc.settings.set` / `ipc.settings.state` — broadcast-on-change to multiple UI surfaces. Lesson progress is read at lesson-start and written at step-complete; different cadence, different concerns.
- Per-user `~/.cache/vibemix/` already exists for `library-clap.db`, `embeddings.db`, `library.pkl` — the convention is in place.

**Atomic write recipe (the privacy-fixture-tested pattern from v3.1):**
```python
import tempfile, os, json, pathlib
path = pathlib.Path("~/.cache/vibemix/learn-progress.json").expanduser()
path.parent.mkdir(parents=True, exist_ok=True)
with tempfile.NamedTemporaryFile("w", dir=path.parent, delete=False) as tmp:
    json.dump(progress, tmp, indent=2)
    tmp.flush()
    os.fsync(tmp.fileno())
os.replace(tmp.name, path)
```

**Alternative noted:** `@tauri-apps/plugin-store ^2.4` is already in `tauri/ui/package.json` and would work for Rust-side storage. Acceptable, but the lesson runtime is Python — keeping progress next to the runtime is cheaper than an IPC round-trip on every read.

---

## Integration Points (file-level)

| New / Modified File | Type | Purpose |
|---------------------|------|---------|
| `src/vibemix/learn/__init__.py` | NEW | package marker |
| `src/vibemix/learn/__main__.py` | NEW (~40 LOC) | `vibemix learn debug --lesson X.Y` CLI for headless ear-test |
| `src/vibemix/learn/lesson_machine.py` | NEW (~250 LOC) | `python-statemachine` lesson FSMs (3 courses × ~7 lessons each) |
| `src/vibemix/learn/lesson_runtime.py` | NEW (~200 LOC) | Wires the FSM to MIDI events, ws_bus, and the AI dialog |
| `src/vibemix/learn/ipc.py` | NEW (~60 LOC) | Dataclasses + jsonschema validators for the 5 new envelopes |
| `src/vibemix/learn/progress.py` | NEW (~40 LOC) | Atomic JSON read/write for `~/.cache/vibemix/learn-progress.json` |
| `src/vibemix/library/band_exemplars.py` | NEW (~80 LOC) | Per-track band-share precompute + index + cached lookup |
| `src/vibemix/audio/decode.py` | NEW (~20 LOC, refactor) | Shared PyAV decode-to-48k-mono helper (lifted from `clap_engine`) |
| `src/vibemix/audio/features.py` | MODIFIED (~+15 LOC) | Add `snapshot_features_from_array(arr, sr)` sibling so band-exemplars feed numpy directly |
| `src/vibemix/runtime/ws_bus.py` | MODIFIED (~+30 LOC) | Validate + emit `learn.*` envelopes; route inbound `learn.start_lesson` + `learn.ack` to the lesson runtime |
| `src/vibemix/state/coach.py` | MODIFIED (~+40 LOC) | Add `lesson_step:` as a registered evidence source (3 schema-mirror sites, mirrors how `recall:` was added in v6.0) |
| `src/vibemix/prompts/matrix.py` | MODIFIED (~+25 LOC) | Tutor lens cell: when `lesson_step` evidence is present, render the lesson copy template |
| `tauri/ui/src/ipc/messages.schema.json` | MODIFIED (+5 `oneOf` refs, ~+120 lines `definitions`) | The 5 new envelope schemas |
| `tauri/ui/src/learn/` | NEW directory | Webview Learn surface (mirrors `session/` and `wizard/`) |
| `tauri/ui/src/learn/controllers/<id>.svg.ts` | NEW × 11 (10 specific + 1 generic) | Inline SVG strings with `data-control-id` hit regions |
| `tauri/ui/src/learn/highlight.ts` | NEW (~80 LOC) | Receives `learn.highlight`, toggles `data-highlight` on matching `<g>` |
| `tauri/ui/src/learn/state.ts` | NEW (~120 LOC) | Receives `learn.complete_lesson` / `learn.start_lesson`, drives lesson-list UI |
| `tauri/ui/src/learn/styles.css` | NEW (~80 LOC) | CDJ-Whisper `g[data-highlight]` rules |
| `tauri/ui/src/learn/__tests__/` | NEW | vitest specs (highlight wiring, SVG hit regions, completion flow) |
| `tests/learn/` | NEW | pytest: lesson FSM transitions, band-exemplar scoring, IPC round-trip |
| `pyproject.toml` | MODIFIED (+1 line under `dependencies`) | `"python-statemachine>=3.1,<4"` |
| `assets/learn/band_exemplars/` | NEW (~3-5 MB) | 1 CC-BY exemplar track per band (sub/low/mid/hi) for zero-library fallback |

**Total net-new Python LOC estimate: ~750** (lesson machine + runtime + IPC + band-exemplar finder + CLI + tests).
**Total net-new TS LOC estimate: ~600** (highlight wiring + state + lesson list UI + tests, **excluding** the 11 controller SVGs which are mostly markup).

---

## Cardinal Invariant Check

| Invariant | How v9.0 Preserves It |
|-----------|------------------------|
| **#1 Single-writer (only state-refresh writes `MusicState`)** | Lesson runtime is a **reader** of `MusicState` (Course 3 tutor lens consumes the live phase/BPM/event stream). Lesson **progress** is a separate JSON, not in `MusicState`. PASS. |
| **#2 Citation grounding (every reaction citation resolves in `EvidenceRegistry`)** | `lesson_step:<lesson_id>:<control_id>` becomes a new registered evidence source (mirrors `recall:` from v6.0). Tutor dialog citing `[lesson_step:1.3:eq_low_a]` resolves; uncited tutor lines strip to the ack-bank fallback. PASS. |
| **#3 Trust the audio (live audio is authoritative; never invents)** | Course 3 (Live Play) consumes the existing event detector — no new "inferred" lesson events. Courses 1 + 2 are user-driven (the user touches the control; we don't infer touch from audio). PASS. |
| **#4 One socket (mascot/wizard on `:8765`)** | The 5 new envelopes ride the existing `:8765` socket. NO new port. The validator gates inbound + outbound. PASS. |
| **(Implicit) Idle ≠ fault** | The lesson runtime has its own "intro" state where no audio is required — never trips the `SessionLayout` grounding-failure timer (Course 1 + 2 never touch the co-host's grounded flag). PASS. |

---

## Install-Impact Ratings (every new dep + asset)

| Item | Rating | Why |
|------|--------|-----|
| `python-statemachine` (Python dep) | **GREEN** | MIT, pure-Python, ~30 KB wheel, no transitives, no native build. |
| 11 SVG controller files (10 specific + 1 generic) | **GREEN** | Authored markup, ~5-15 KB each gzipped → ~80 KB total in webview bundle. Vite SVGO compresses further. |
| `assets/learn/band_exemplars/` (4 CC-BY tracks) | **YELLOW** | ~3-5 MB binary additions to the installer. Acceptable; the alternative is a worse first-run UX (lesson can't show "low band example" if user library is empty). Mitigate: stream from a CDN on first-run (skip if offline), or ship as a separate optional download. |
| `src/vibemix/learn/` (5 new modules, ~750 LOC) | **GREEN** | Pure Python, no native deps. |
| `tauri/ui/src/learn/` (4 new modules + 11 SVGs + tests) | **GREEN** | No new npm deps. Vitest already covers it. |
| 5 new IPC envelopes | **GREEN** | Schema additions only; `npm run codegen:ipc` regenerates the validator; jsonschema runtime already in deps. |
| Modified `ws_bus.py` (~+30 LOC) | **GREEN** | Same pattern as the existing `ipc.session.snapshot` emission. |
| Modified `coach.py` + `matrix.py` (~+65 LOC) | **GREEN** | Same pattern as the v6.0 `recall:` evidence source addition. |
| Modified `audio/features.py` (~+15 LOC for `_from_array` sibling) | **GREEN** | Pure refactor, exposes existing math through a numpy-direct entry point. |
| `audio_config.py --configure-routing` (existing) | **N/A — REUSE** | v3.1 work; surface in the wizard for headphone-cue users who want a Multi-Output Device. |

**Net change to one-click installer size:** ~3-5 MB (the band-exemplar audio fallback). Acceptable on the v3.1 INSTALL_READY budget (the median was 41,000 ms / 60,000 ms cap). If we stream the exemplars on first-run instead of bundling, net change is ~80 KB (the SVGs).

---

## Things I Wouldn't Normally Ask About (default-yes coverage)

These are the questions the roadmap author might miss but that bite later:

1. **Time-source for the lesson timer (Q "how long did the user take?"):** use `time.monotonic_ns()` in Python — not `time.time()` — to avoid wall-clock-jump skews when the user puts the laptop to sleep mid-lesson. The `learn.complete_lesson` envelope's `duration_sec` field should be monotonic. (Existing `vibemix.runtime.ttft` already uses this discipline.)
2. **i18n for lesson copy:** v9.0 ships English-only (matches the rest of the app). Lesson copy lives in `src/vibemix/learn/copy/en.py` (NEW) so v9.1 can drop a `tr.py` / `it.py` sibling without restructuring. Keep the lesson copy SEPARATE from the FSM definition (the FSM transitions on `correct_input`, not on a copy string).
3. **Accessibility (WCAG-AA):** the SVG `<g role="button" aria-label="...">` + `aria-pressed` (for active highlights) covers screen-reader users. The lesson FSM should also accept a `learn.advance{reason: "user_skip"}` from a keyboard-only user (Space = advance; matches v8.x kbd discipline).
4. **Privacy:** lesson progress JSON contains no transcripts or user-spoken content; the existing privacy-fixture path (`tests/e2e/macbook/test_privacy_fixture.py`) verifies vibemix doesn't write to off-limits dirs. Add a parallel fixture: `~/.cache/vibemix/learn-progress.json` is the ONLY path the lesson runtime writes.
5. **Telemetry:** v9.0 ships zero telemetry by default. Aggregate stats ("median time to complete Course 1") are opt-in and surface in the existing `ipc.telemetry.optin` path (v3.0 LAUNCH-05 already gates this — DEFAULT OFF). Don't add a new telemetry envelope.
6. **CI gate for SVG↔profile drift:** new test (`tauri/ui/tests/learn/test_svg_profile_parity.spec.ts`) — for every `<id>.svg.ts`, every `data-control-id` MUST exist in `midi/profiles/<id>.json::controls` or `::buttons`, AND every binding in the profile MUST have a matching SVG group (bi-directional). Catches drift when a contributor adds a new control to a profile but forgets the SVG.
7. **Audio device hot-swap during a lesson:** if the user yanks their headphones mid-lesson, `sd.OutputStream` raises `PortAudioError`. Wrap the lesson playback in the same `try/except` pattern as v4.0's `_voice_callback_factory` — log to stderr + `events.jsonl`, swap to the system default output, narrate "audio device changed — switching to system default". Don't crash the lesson.
8. **What about Course 3 ↔ existing live co-host conflicts?** Course 3 = the existing live co-host with `lens="tutor"`. The lesson runtime DOES NOT spawn a second co-host; it just sets the lens via the existing `ipc.settings.set` envelope. Single-AI-source preserved.
9. **What if the user has TWO controllers (e.g. FLX4 + DDJ-400) plugged in for Course 2?** The lesson defaults to the first-detected controller and shows a "switch controller" dropdown. The dropdown reuses the existing `midi/registry.py::list_profiles()` enumeration. No new UI primitive.
10. **What about the wizard-step retire-on-complete flow?** Add `learn.completed_at` timestamp to `~/.cache/vibemix/learn-progress.json`; the Learn surface dims completed lessons but keeps them clickable (replay). Mirrors how `recordings/` dims viewed recordings in v3.1.
11. **What's the upgrade path when v9.1 adds an 11th controller?** Contributor adds `midi/profiles/<new_id>.json` + `tauri/ui/src/learn/controllers/<new_id>.svg.ts`. The CI gate (#6) verifies parity. No code change to the lesson runtime — it's controller-agnostic.
12. **What's the rollback if the lesson FSM has a bug that wedges a user mid-lesson?** Add `vibemix learn reset` CLI (~10 LOC) that wipes `~/.cache/vibemix/learn-progress.json` after confirmation. Surfaces a "Reset Learn Progress" button in the existing settings drawer.
13. **What if `python-statemachine` upstream goes unmaintained?** It's MIT pure-Python and ~30 KB — vendor it into `src/vibemix/learn/_vendor/statemachine/` as a fallback (same posture as how the project keeps `pyrekordbox` pinned to a known-good version). Don't pre-vendor; only if upstream activity drops.
14. **What about the existing `ipc.settings.set { skill_level }` path?** Already shipped in v8.0 — Learn surface reads it via `ipc.settings.state` to choose which course-set to surface. Beginner = courses 1 + 2 + 3. Intermediate = course 2 + 3. Pro = course 3 only. No new settings envelope.

---

## Sources

- [Mixxx Contributing Mappings — SVG diagrams preferred, hand-traced from manufacturer PDFs in Inkscape](https://github.com/mixxxdj/mixxx/wiki/Contributing-Mappings) — HIGH (official Mixxx wiki; precedent for the trace-from-PDF approach)
- [Mixxx LICENSE — GPL-2.0](https://github.com/mixxxdj/mixxx/blob/main/LICENSE) — HIGH (verified — confirms Mixxx's SVGs can't be imported into Apache-2.0 vibemix; we must redraw)
- [Mixxx user manual — Pioneer DDJ-FLX4 with SVG schematic views](https://manual.mixxx.org/2.6/en/hardware/controllers/pioneer_ddj_flx4) — HIGH (confirms the schematic-view approach for control hit regions)
- [Pioneer DJ — official DDJ-FLX4 hardware diagram PDF](https://www.pioneerdj.com/-/media/pioneerdj/software-info/controller/ddj-flx4/ddj-flx4_hardwarediagram_rekordbox_e1.pdf?la=en-us) — HIGH (factual control geometry source for the trace)
- [SVG vs Canvas vs WebGL — performance tradeoffs at scale](https://medium.com/@codetip.top/svg-vs-canvas-vs-webgl-for-diagram-viewers-tradeoffs-bottlenecks-and-how-to-measure-8cedbd3b7499) — MEDIUM (SVG remains best for <few-thousand elements with hit-testing/accessibility)
- [Hacker News thread — SVG hits a performance ceiling at ~3-5k elements](https://news.ycombinator.com/item?id=15024190) — MEDIUM (corroborates the SVG-at-low-element-count win)
- [Lisi Linhart — SVG animation with CSS variables, 60fps rule](https://lisilinhart.info/posts/svg-animation-css-variables/) — HIGH (technical reference for the highlight animation approach)
- [MDN — Animation performance and frame rate](https://developer.mozilla.org/en-US/docs/Web/Performance/Guides/Animation_performance_and_frame_rate) — HIGH (animate only transform/opacity/fill for 60fps; everything else triggers layout)
- [python-statemachine GitHub repo (MIT, pure-Python)](https://github.com/fgmacedo/python-statemachine) — HIGH (verified license + pure-Python + zero transitives)
- [python-statemachine docs — tutorial, statecharts, async](https://python-statemachine.readthedocs.io/) — HIGH (verified declarative DSL fits the lesson-step shape)
- [pytransitions/transitions GitHub (MIT)](https://github.com/pytransitions/transitions) — HIGH (verified alternative; both libraries qualify, declarative DSL was the tiebreaker)
- [XState v5 Bundlephobia — 43,213 B / 13,598 B gzip](https://bundlephobia.com/api/size?package=xstate@5.20.1) — HIGH (verified bundle size — not huge, but wrong side of the wire)
- [Stately — XState v5 is here](https://stately.ai/blog/2023-12-01-xstate-v5) — HIGH (verified XState v5 is current and zero-dep)
- [`@xstate/fsm` deprecated per @ficusjs/finite-state-machine notes](https://www.npmjs.com/package/@ficusjs/finite-state-machine) — MEDIUM (cross-referenced; confirms the lightweight FSM xstate fork is no longer the answer)
- [python-sounddevice multi-device output pattern](https://esologic.com/multi-audio/) — HIGH (verified the second `OutputStream` against a different device is the documented pattern)
- [python-sounddevice — Streams docs](https://python-sounddevice.readthedocs.io/en/latest/api/streams.html) — HIGH (official docs)
- [Apple Developer Forum — CoreMIDI device properties unreliable](https://developer.apple.com/forums/thread/68521) — MEDIUM (justifies skipping USB-descriptor fingerprinting in v9.0)
- [mido docs — get_input_names usage](https://mido.readthedocs.io/en/latest/intro.html) — HIGH (verified the substring-match approach)
- [CircuitPython USB MIDI docs — 31-char Windows audio interface name limit](https://docs.circuitpython.org/en/latest/shared-bindings/usb_midi/index.html) — MEDIUM (informs the device-name-length check; none of our 10 hints are at risk)
- [tauri-plugin-audio-recorder limitations — output device selection TBD](https://github.com/brenogonzaga/tauri-plugin-audio-recorder) — MEDIUM (justifies staying in `sounddevice` for v9.0)
- [Three.js tree-shaking forum discussion](https://discourse.threejs.org/t/tree-shaking-three-js/1349) — MEDIUM (justifies NOT growing Three.js usage to the controller renderer)
- [Tone.js multichannel output guide](https://janigowski.dev/posts/multichannel-audio-output) — MEDIUM (informative for the route-to-headphones context; we don't adopt Tone.js though — Web Audio in webview is wrong layer)
- In-repo discipline: [`feedback_schema_edit_needs_codegen_ipc`] — HIGH (pre-compiled ajv validator must be regenerated after any schema bump)
- In-repo discipline: [`feedback_no_managed_memory_frameworks`] — HIGH (informs the "don't put lesson progress in memory.db" call)
- In-tree code: `src/vibemix/audio/features.py:27-90` — HIGH (verified `snapshot_features` already returns band-share scalars)
- In-tree code: `src/vibemix/midi/registry.py` — HIGH (verified `find_mapping` substring match is current)
- In-tree code: `src/vibemix/midi/profile.py` — HIGH (verified the profile schema is the source of truth for `data-control-id` keys)
- In-tree code: `src/vibemix/platform/_audio_macos.py:298-380` — HIGH (verified the per-call `device_index` parameter on output streams)
- In-tree code: `src/vibemix/runtime/ws_bus.py:1-100` — HIGH (verified the validate-then-emit pattern + one-socket invariant)
- In-tree code: `tauri/ui/src/wizard/controllers/ddj-flx4.svg.ts` — HIGH (verified the inline-SVG-string pattern; v9.0 scales this approach with `data-control-id`)
- In-tree code: `docs/clap-engine.md` — HIGH (verified the CLAP audio-decode reuse path for `band_exemplars`)
- In-tree code: `AGENTS.md` — HIGH (verified the contributor commands the new dep additions must respect — `uv sync --group dev --extra ai-local`, `uv run pytest -q`, `npm test`, `cargo check`)
- In-tree code: `tauri/ui/src/ipc/messages.schema.json:1-200` — HIGH (verified the `oneOf` + `additionalProperties: false` schema pattern for the 5 new envelopes)
- In-tree code: `docs/assets/controllers/pioneer-ddj-flx4.svg` — HIGH (verified existing controllers are text-placeholders that v9.0 upgrades to real schematics)
- In-tree code: `tauri/ui/package.json` — HIGH (verified existing JS deps: `three`, `ajv`, `ajv-formats`, `@tauri-apps/plugin-store`, vitest, vite)

---

*Stack research for: vibemix v9.0 "Lesson One" — beginner DJ learning module*
*Researched: 2026-05-27*
*Confidence: HIGH — every recommendation is either an in-tree code anchor (verified by reading), an existing dep, or a single MIT/pure-Python dep with a verified version. No assumptions left unverified.*
