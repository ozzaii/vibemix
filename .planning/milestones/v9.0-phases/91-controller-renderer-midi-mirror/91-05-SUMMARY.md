---
phase: 91-controller-renderer-midi-mirror
plan: 05
subsystem: ui
tags: [learn, tauri, webview, svg, ws-client, ipc, ajv, midi-mirror, vite, render-01, render-02, render-03, render-05, render-06, render-07]

# Dependency graph
requires:
  - phase: 91-controller-renderer-midi-mirror
    provides: |
      Plan 91-01 ipc.learn.controller_detected + ipc.learn.midi_position
      envelope contract + pre-compiled ajv `validator.generated.mjs` + the
      placeholder learn-window.ts shell + dist/learn.html Vite entry +
      "learn" window label in capabilities/default.json windows scope.
      Plan 91-02 14 vitest/playwright TS test stubs under
      `tauri/ui/tests/learn/` — Plan 05 flips 12 of them GREEN. Plan
      91-03 the Python MidiMirror class + ws_broadcast 30Hz emit
      wiring. Plan 91-04 the Rust learn_window.rs shell + the
      open_learn_window Tauri command (the window the webview now
      occupies).
provides:
  - "tauri/ui/src/learn/learn-window.ts (REAL renderer — REPLACES Plan 01's 51-line placeholder; 229 lines orchestrator with rAF-drained midi_position consumer, aria-live SR announcement, dynamic-import SVG mount)"
  - "tauri/ui/src/learn/ws-client.ts (LearnWsClient — opens `ws://127.0.0.1:8765` literal, ajv-validates every frame, dispatches typed CustomEvent on window, 1s linear-backoff reconnect)"
  - "tauri/ui/src/learn/controllers/pioneer_ddj_flx4.svg.ts (the canonical FLX4 inline schematic — 25 `<g data-control-id>` groups bidirectionally parity-clean against `pioneer_ddj_flx4.json`)"
  - "tauri/ui/src/learn/controllers/_generic.svg.ts (labeled-zone fallback — DECK A · MIXER · DECK B dashed rectangles + JetBrains Mono labels)"
  - "tauri/ui/src/learn/controllers/_aria-labels.ts (48-entry ARIA_LABELS lookup keyed on `<field>:<deck>`, hand-authored once for all 10 controller profiles)"
  - "tauri/ui/src/learn/components/controller-stage.ts (the SVG host — dynamic-import allowlist, applyPositionFrame transform-only + data-active swaps)"
  - "tauri/ui/src/learn/components/titlebar.ts (LearnTitlebar — wordmark + controller name + live clock, 56px)"
  - "tauri/ui/src/learn/components/empty-state.ts (centered 'no controller detected' surface with plug glyph)"
  - "tauri/ui/src/learn/components/status-bar.ts (3-segment status rail — mirror state + 240-sample P95 latency probe + window-switch hint)"
  - "tauri/ui/src/learn/components/unplugged-toast.ts (4s auto-dismiss toast on controller disconnect)"
  - "tauri/ui/src/learn/styles/learn.css (306 lines page-scoped — window grid layout + titlebar/stage/status-bar/empty-state/toast styling + breathing under-stroke animation + `--learn-highlight` CSS variable declaration)"
  - "FLX4 + generic SVG cases in 7 Plan-02 test files flip from skip to assertion GREEN; the 9 non-FLX4 controllers' cases stay properly skipped pending Plan 06"
affects: [91-06, 91-07, 92, 93, 94, 95, 96]

# Tech tracking
tech-stack:
  added: []  # Zero new dependencies — uses existing ajv (pre-compiled) + Vite ?raw dynamic imports
  patterns:
    - "Vite code-split inline SVG via dynamic import — each controller chunks separately (FLX4 16.5kB, generic 1.7kB, learn entry 8.7kB) so first-paint stays under the 2s budget regardless of how many controllers we ship"
    - "Hardcoded controller-id allowlist in dynamic-import — defends against import-string injection (T-91-05-02 mitigation): unknown ids fall back to _generic, never reach the dynamic-import path as raw user input"
    - "rAF frame-flood drainer with pendingPositions LWW — only the latest midi_position frame between repaint slots paints (RESEARCH §Pitfall 6); tab-resume backlog floods coalesce into one frame, no CPU spike"
    - "Idempotent stage.render — skipping no-op remounts on spammed controller_detected envelopes (T-91-05-03 mitigation)"
    - "Single `WebSocket(WS_URL_8765)` literal — the grep gate `test_ws_client_uses_8765.spec.ts` scans for the literal string at every `new WebSocket(...)` call site; identifier indirection (`this.url`, etc.) would fail the gate"
    - "Static default-import + `// @ts-expect-error` for validator.generated.mjs — mirrors the precedent in src/ipc/validator.ts; keeps tsc clean without adding @types/jsdom or any other typings"
    - "20/80 amber discipline in styles — page declares `--learn-highlight: var(--amber)` ONCE; the SVGs use currentColor everywhere and inherit `color: var(--silk-22)` from the stage class (P92 flips the color on the highlighted `<g>`)"

key-files:
  created:
    - "tauri/ui/src/learn/ws-client.ts (139 lines)"
    - "tauri/ui/src/learn/controllers/_aria-labels.ts (101 lines)"
    - "tauri/ui/src/learn/controllers/_generic.svg.ts (49 lines)"
    - "tauri/ui/src/learn/controllers/pioneer_ddj_flx4.svg.ts (353 lines)"
    - "tauri/ui/src/learn/components/controller-stage.ts (175 lines)"
    - "tauri/ui/src/learn/components/empty-state.ts (44 lines)"
    - "tauri/ui/src/learn/components/status-bar.ts (142 lines)"
    - "tauri/ui/src/learn/components/titlebar.ts (72 lines)"
    - "tauri/ui/src/learn/components/unplugged-toast.ts (48 lines)"
    - "tauri/ui/src/learn/styles/learn.css (306 lines)"
  modified:
    - "tauri/ui/src/learn/learn-window.ts (51-line placeholder REPLACED with 210-line orchestrator)"

key-decisions:
  - "FLX4 SVG = 25 `<g data-control-id>` groups (the EXACT profile cardinality), authored to viewBox 0 0 1280 720 with deck A left + mixer center + deck B right layout. Jog wheels 100px radius, EQ knobs 22px radius, transport buttons 60×40 rect, pitch faders 200px vertical, channel faders 220px vertical, crossfader 300px horizontal. Knobs carry data-cx/data-cy so the latency harness + production applyPositionFrame can read pivot coordinates."
  - "Generic fallback uses NO `<g data-control-id>` entries (per UI-SPEC §Asset Pipeline rule 8) — it's the honest 'we don't know this controller' surface. The parity gate special-cases the `_generic` row in `test_svg_profile_parity.spec.ts`."
  - "Wire-shape divergence — the FLX4 profile defines `kind: jog_touch` on buttons, but ControllerState.handle_msg in `state.py:317` writes the deck snapshot as `jog_touched`. The SVG uses the PROFILE's literal `jog_touch:A/B` (so the parity gate sees forward+reverse equality) and `controller-stage.ts::applyPositionFrame` swaps `jog_touched:` → `jog_touch:` at runtime when looking up the matching `<g>`. Documented at line 110 of `controller-stage.ts`."
  - "ws-client uses STATIC default-import of `validator.generated.mjs` (the precedent from `src/ipc/validator.ts`), NOT dynamic import. Trade-off: validator code joins the main learn-entry chunk (363kB minified validator → 34kB gzipped). The dynamic-import path would need an `await import` inside `onMessage` (synchronisation cost on every frame) or a one-shot lazy gate (extra `null` check). Static is simpler + matches debrief precedent; the bundle-size impact is acceptable for a single non-shared validator."
  - "Controller-stage's `render` switch-statement is hand-rolled per controller (not a parameterised path). Vite static-analysis requires literal module paths to code-split; the switch case lands as a literal `await import(\"../controllers/pioneer_ddj_flx4.svg.js\")`. Plan 06 will add 9 more case branches in lockstep with each SVG file."
  - "No new design tokens were added. Every CSS value references existing tokens.css primitives. `--learn-highlight` is declared as `var(--amber)` on `#learn-root` so P92's highlight contract can flip it via a single CSS-variable swap on highlighted `<g>` groups — no per-component override needed."
  - "Latency harness P95 measurement reads **0.66 ms** in jsdom (target 50ms, red guardrail 80ms). jsdom is faster than the real WebKit compositor, but the headroom is enormous: 80ms / 0.66ms = ~120x. §LEARN-LATENCY-CONTINGENCY (Rust-direct midir) stays parked — no trigger."

patterns-established:
  - "Learn webview architecture: ws-client → CustomEvent on window → component-local addEventListener → DOM mutation. No central state store, no pub/sub — each component subscribes to its own envelope class. Plan 92 will add lesson-engine envelopes; this pattern scales naturally."
  - "Dynamic-import SVG code-split: each controller `<id>.svg.ts` chunks separately; only the matched controller's payload fetches on detection. Adding a controller = adding its switch-case in controller-stage + the .svg.ts file. The generic fallback IS eagerly imported only inside the unknown-id branch of the same switch."
  - "Brand-safety prose discipline: the case-insensitive `Pioneer DJ` wordmark grep gate scans ENTIRE file bodies including SPDX comments. Provenance prose in SVG files MUST use the publisher name (AlphaTheta Corp.) — NOT the trade-dress wordmark."
  - "Test-grep regex defense: literal `new WebSocket(...)` in comments is flagged by the ws-port grep gate as a non-literal-arg offender. Comments referencing the constructor MUST phrase it as 'WebSocket constructor argument' or similar — never as a literal call expression."

requirements-completed: [RENDER-01, RENDER-02, RENDER-03, RENDER-05, RENDER-06]

# Metrics
duration: 12min
completed: 2026-05-28
---

# Phase 91 Plan 05: Controller Renderer + MIDI Mirror — Learn Webview Frontend Summary

**11 frontend files under `tauri/ui/src/learn/` ship the user-facing artifact: the LearnWindow webview now opens a ws:8765 client, mounts the FLX4 inline SVG (25 hit-regions) on `ipc.learn.controller_detected`, and mirrors physical knob positions onto the SVG via transform-only updates inside a rAF-coalesced drainer — P95 synthetic latency 0.66ms (target 50ms, red 80ms).**

## Performance

- **Duration:** ~12 min (~691 seconds wall-clock)
- **Started:** 2026-05-27T21:47:09Z
- **Completed:** 2026-05-27T21:58:40Z
- **Tasks:** 2 atomic task commits + this metadata commit
- **Files created:** 10 new
- **Files modified:** 1 (`learn-window.ts` — 51-line placeholder REPLACED with 210-line orchestrator)
- **Total lines shipped:** 1639

## Accomplishments

- **The user-facing artifact lights up.** After Plans 01-04 prepared the wire contract, the Python emitter, the Rust window-spawn primitive, and the test scaffolding, Plan 05 paints the pixels. A DJ plugging in a DDJ-FLX4 now sees the schematic mount, every knob/fader/button respond to physical position via incoming MIDI.
- **FLX4 SVG = 25 `<g data-control-id>` groups bidirectionally parity-clean** against `src/vibemix/midi/profiles/pioneer_ddj_flx4.json` (13 controls + 12 buttons). Every group carries `role="button"` + `aria-label` (from `_aria-labels.ts`) + `tabindex="0"` + data-cx/data-cy on knobs (for the latency-harness pivot reads) + the dual-cue empty slots (`<g class="cue-color">` + `<g class="cue-shape">`) for P92's highlight contract.
- **Generic fallback SVG renders labeled zones** (DECK A · MIXER · DECK B dashed rectangles + JetBrains Mono 32px labels) — the honest "we don't recognise this controller" surface, no fake-realistic.
- **48-entry ARIA_LABELS lookup** covering every (field, deck) pair across all 10 shipped MIDI profiles — including 4-deck variants (DDJ-1000/FLX10/SX3), filter_fx + tap_tempo master controls, and the jog_touch + jog_touched key aliases for cross-controller compatibility.
- **One-socket invariant #4 preserved** — the LearnWsClient opens `new WebSocket("ws://127.0.0.1:8765")` (literal string at the call site so the grep gate `test_ws_client_uses_8765.spec.ts` passes); same socket as the live deck.
- **rAF frame-flood drainer** (RESEARCH §Pitfall 6) — module-level `pendingPositions` is set on each midi_position event; the next rAF callback consumes it (LWW); tab-resume floods of 200 frames coalesce into a single repaint.
- **20/80 amber discipline holds.** `--learn-highlight: var(--amber)` declared once on `#learn-root`; SVG strokes are `currentColor` inheriting from `color: var(--silk-22)`; amber accent reserved to the breathing title under-stroke + focus ring + (P92 future) highlight target. No new design tokens.
- **CDJ-Whisper aesthetic intact.** Saira wdth 85 wght 700 wordmark + JetBrains Mono labels + warm-black void background (inherited from tokens.css `body` recipe). Frontend-enforcement skill compliance: zero hex literals inside SVG bodies, no Pioneer logo, no #FF7F00, no `<image href>` photo-lift, no Inter/Roboto/Arial/system-ui anywhere in `tauri/ui/src/learn/`.
- **12 Plan-02 test stubs flip GREEN.** highlight-latency, ws-client-uses-8765, controller-detected-mounts-svg, generic-fallback + FLX4 cases in test_svg_profile_parity / test_aria_labels_present / test_dual_cue_slots_present / test_all_11_svgs_present (4 of 11 parameterised tests). The 9 non-FLX4 controllers stay properly skipped pending Plan 06.

## Task Commits

Each task was committed atomically by named paths only (concurrent-session discipline — never `git add -A` / `git add .`):

1. **Task 1: Land FLX4 inline SVG + generic fallback + ARIA-label lookup** — `bfa01b80` (feat)
   - Three new files: `_aria-labels.ts` (101 lines), `pioneer_ddj_flx4.svg.ts` (353 lines), `_generic.svg.ts` (49 lines). Verify: 6 vitest gates pass + Python wordmark gate pass.

2. **Task 2: Land Learn webview entry + ws-client + 5 components + styles** — `71d218cd` (feat)
   - Eight new + modified files: `learn-window.ts` (REPLACES placeholder, 210 lines), `ws-client.ts` (139 lines), 5 components (controller-stage 175 / titlebar 72 / empty-state 44 / status-bar 142 / unplugged-toast 48 lines), `styles/learn.css` (306 lines). Verify: tsc + build pass; vitest 966 passed / 0 failed; latency P95 0.66ms.

**Plan metadata commit:** TBD (this SUMMARY + STATE.md + ROADMAP.md update — final commit below).

## SVG ↔ Profile Parity (FLX4)

The FLX4 SVG's `<g data-control-id>` set matches the `pioneer_ddj_flx4.json` field+deck set bidirectionally (set equality, not subset):

```
controls (13):  vol:A   vol:B   eq_hi:A  eq_hi:B  eq_mid:A  eq_mid:B
                eq_low:A eq_low:B tempo:A  tempo:B  filter:A  filter:B
                xfader
buttons (12):   play:A  play:B  cue:A   cue:B   sync:A     sync:B
                jog_touch:A jog_touch:B loop_in:A loop_in:B loop_out:A loop_out:B
                                                                        Total: 25
```

`tauri/ui/tests/learn/test_svg_profile_parity.spec.ts::pioneer_ddj_flx4` GREEN. The other 9 controller cases stay properly skipped.

## Latency Harness Measurement

```
midi_position P95 latency: 0.66 ms
```

(N_BURST=240 frames, 30Hz triangle sweep 0→127→0 on `eq_hi:A`, transform-only `<g>` rotate updates). Target ≤50ms, red guardrail 80ms — measurement is **~120x under the red guardrail**. §LEARN-LATENCY-CONTINGENCY (Rust-direct midir) stays parked.

Caveat: jsdom's `setAttribute('transform', ...)` is faster than the real WebKit compositor. The headroom is so large that even a 100x slowdown in production wouldn't trigger the contingency. Real measurement requires `cargo tauri dev` + a plugged-in FLX4 — that's Plan 07's gate.

## Plan-02 Test Stub Pass/Skip/Todo Breakdown After Plan 05

| Test file | Before P05 | After P05 |
|-----------|-----------|-----------|
| `highlight-latency.test.ts` | SKIP | PASS (FLX4 SVG present + ✓ P95 0.66ms) |
| `test_ws_client_uses_8765.spec.ts` | PASS (no source) | PASS (ws-client uses literal `:8765`) |
| `test_controller_detected_mounts_svg.test.ts` | SKIP | PASS (real LearnWindow + FLX4 SVG present) |
| `test_generic_fallback.spec.ts` | SKIP | PASS (`_generic.svg.ts` ships GENERIC_CONTROLLER_SVG + labels) |
| `test_no_pioneer_orange.spec.ts` | PASS (no source) | PASS (no #FF7F00 in SVGs) |
| `test_svg_currentcolor_only.spec.ts` | PASS (no source) | PASS (only currentColor / var(--silk-22) / none / var(--silk)) |
| `test_learn_window_label.spec.ts` | PASS (Plan 04) | PASS (Plan 04 still green) |
| `test_svg_profile_parity.spec.ts` | 11 SKIP | 2 PASS (FLX4 + _generic) / 9 SKIP |
| `test_aria_labels_present.spec.ts` | 11 SKIP | 2 PASS (FLX4 + _generic) / 9 SKIP |
| `test_dual_cue_slots_present.spec.ts` | 11 SKIP | 2 PASS (FLX4 + _generic) / 9 SKIP |
| `test_all_11_svgs_present.spec.ts` | 11 SKIP | 2 PASS (FLX4 + _generic) / 9 SKIP |
| `test_sr_announcement.spec.ts` | 1 TODO | 1 TODO (Plan 02 left as `it.todo` — body needs real LearnWindow mounting in jsdom; the aria-live region IS landed in `learn-window.ts` line 96, but the test contract is to mount + dispatch + assert text, not to grep the source) |
| `test_keyboard_nav_order.spec.ts` | SKIP (playwright) | SKIP (playwright runner gated separately; the SVG has tabindex=0 on every `<g data-control-id>` so the keyboard-nav contract is fulfillable when the playwright spec lands) |
| `test_contrast_ratios.spec.ts` | SKIP (playwright) | SKIP (same; tokens.css contrasts are already AAA-level for silk-on-void + amber-on-void) |

**Net:** 966 passed / 38 skipped / 1 todo / 0 failed (full vitest suite). Was 954+1 before Plan 05; **+12 passing**.

## Build Artifacts

```
dist/learn.html                                  2.0 kB
dist/assets/learn-nmTpUR1p.js                    8.7 kB    (the entry chunk)
dist/assets/pioneer_ddj_flx4.svg-cQIH3To2.js    16.5 kB    (FLX4 SVG, lazy-loaded)
dist/assets/_generic.svg-DwQcwoH_.js             1.7 kB    (generic fallback, lazy-loaded)
dist/assets/validator.generated-Coungyc_.js    363.3 kB → 34 kB gzipped  (shared with main app)
```

Dynamic-import code-splitting confirmed per RESEARCH §Pitfall 5: each controller SVG chunks separately, only the matched controller's payload fetches on detection.

## Screenshot

Screenshot of `cargo tauri dev` Learn window open with FLX4 SVG mounted is a **Kaan-action** per `feedback_verify_live_app_not_just_tests` — the bundled Python sidecar in `cargo tauri dev` is FROZEN (lags edited src/), so screenshot capture requires running `python -m vibemix` against the current source AND clicking the Tauri shell's Learn-window-open command. Plan 07 schedules that ear-pass.

## Decisions Made

- **FLX4 layout chose deck-A-left / mixer-center / deck-B-right** (the canonical CDJ-2-deck hardware layout). Jog wheels positioned mirror-symmetrically (deck A at cx=265, deck B at cx=1015). The 1280×720 viewBox preserves the FLX4's 482×272 mm physical aspect.
- **Dual-cue slots are SIBLINGS of the factual geometry, not WRAPPERS.** Each `<g data-control-id>` contains the factual `<circle>`/`<rect>`/`<line>` elements FIRST, then the two empty `<g class="cue-color">` and `<g class="cue-shape">` slots LAST. P92's highlight can either inject `<circle fill="var(--learn-highlight)">` into `cue-color` (color channel) or a stroked-dasharray ring into `cue-shape` (shape channel) — both light at once for dual-channel WCAG cue.
- **Knobs are unipolar by default in the SVG render** (data-cx/data-cy populated so `applyPositionFrame` rotates them). Bipolar controls (filter, tempo, xfader) carry the same data-cx/data-cy + a centered-detent visual cue line; the rotation map `(value/127)*270-135` is unipolar but acceptable for both axis types in P91 (P92's lesson runtime adds axis-aware rendering if needed).
- **status-bar latency probe is visible by default** (UI-SPEC §Open Decisions #1 — auto-ratified per fully-autonomous mode). The pip thresholds (green ≤50ms / amber 50-80ms / red >80ms) mirror the §LEARN-LATENCY-CONTINGENCY trigger exactly, making the surface self-verifying without devtools.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Pioneer wordmark grep gate caught provenance prose**
- **Found during:** Task 1 (post-Write Python pytest verify run)
- **Issue:** The plan's `<read_first>` for Task 1 instructed me to include a provenance comment naming the publisher. I wrote "Hand-authored from the Pioneer DJ DDJ-FLX4 Operating Instructions" — the case-insensitive Pioneer DJ wordmark grep gate in `tests/learn/test_no_pioneer_brand_marks.py` scans ENTIRE file bodies (including comments) and caught the literal "Pioneer DJ" string.
- **Fix:** Rephrased the provenance comment to "Hand-authored from the DDJ-FLX4 'Operating Instructions' appendix hardware-diagram (publisher: AlphaTheta Corp., ©2023 revision)". AlphaTheta is the legally relevant publisher entity (per the Pioneer DJ → AlphaTheta brand-transition mid-2020s), so the prose is more accurate AND clears the grep gate.
- **Files modified:** `tauri/ui/src/learn/controllers/pioneer_ddj_flx4.svg.ts` (provenance comment only — no SVG body change).
- **Verification:** `pytest tests/learn/test_no_pioneer_brand_marks.py` exits 0 PASSED.
- **Committed in:** `bfa01b80` (Task 1 atomic commit — fix landed before commit).

**2. [Rule 3 - Blocking] tsc could not type-check validator.generated.mjs**
- **Found during:** Task 2 (post-Write `npx tsc --noEmit` run)
- **Issue:** First-cut `ws-client.ts` used `await import("../ipc/validator.generated.mjs")` to lazy-load the validator inside `onMessage`. tsc reported `TS7016: Could not find a declaration file for module '../ipc/validator.generated.mjs'`. The generated .mjs ships without a .d.ts (Plan 11 pattern).
- **Fix:** Switched to the existing precedent from `tauri/ui/src/ipc/validator.ts`: static `// @ts-expect-error` + default-import + cast to `AjvValidator`. Validator is now synchronously available; the `onMessage` method drops the `async` keyword.
- **Files modified:** `tauri/ui/src/learn/ws-client.ts` (import block + onMessage signature).
- **Verification:** `npx tsc --noEmit` exits 0.
- **Committed in:** `71d218cd` (Task 2 atomic commit).

**3. [Rule 3 - Blocking] ws-port grep gate caught JSDoc comment + identifier indirection**
- **Found during:** Task 2 (post-Write `npx vitest run tests/learn/test_ws_client_uses_8765.spec.ts`)
- **Issue:** Two failures:
  - The JSDoc comment "grep gate on every `new WebSocket(...)` argument" was matched by the regex `\bnew\s+WebSocket\s*\(\s*([^)]+)\s*\)`. The captured arg was the literal three dots from the comment. Reported as `non-literal arg "..."`.
  - The `new WebSocket(this.url)` call site uses an identifier with a `this.` prefix. The grep's identifier regex `^[A-Za-z_][A-Za-z0-9_]*$` doesn't match `this.url`. Reported as `non-literal arg "this.url"`.
- **Fix:**
  - Rephrased the comment to "grep gate on every WebSocket constructor argument" (no parenthesised call expression).
  - Inlined the literal `"ws://127.0.0.1:8765"` at the call site (was `WS_URL_8765` constant, refactored to a literal string per the grep's string-literal branch). Dropped the constructor parameter entirely — `LearnWsClient()` now opens the hardcoded socket.
- **Files modified:** `tauri/ui/src/learn/ws-client.ts` (constant rename + constructor signature simplification).
- **Verification:** `npx vitest run tests/learn/test_ws_client_uses_8765.spec.ts` exits 0 PASSED.
- **Committed in:** `71d218cd` (Task 2 atomic commit — fix landed before commit).

---

**Total deviations:** 3 auto-fixed (all Rule 3 — blocking verification gates; same class as Plan 04's 3 deviations). Zero behavior change, zero scope creep — all three were prose/identifier-shape adjustments to satisfy mechanical grep gates that scan entire file bodies including comments.

**Impact on plan:** Cosmetic. The shipped functional code matches the plan's behavior contract verbatim.

## Issues Encountered

None other than the auto-fixed deviations above. Both task commits stayed clean (no `git add -A`); no file deletions in either commit; no regressions across the existing 951 vitest tests.

## Threat Flags

No new security-relevant surface beyond what the plan's `<threat_model>` anticipated. All four threat mitigations are implemented:

- **T-91-05-01 (XSS via SVG `<script>` injection):** Both SVG files are hand-authored string literals — no `<script>` tags. Audit: `git grep "<script" tauri/ui/src/learn/controllers/*.svg.ts` returns 0 matches. Manual review at commit confirmed.
- **T-91-05-02 (Tampering via spoofed controller_id):** `controller-stage.ts::loadControllerSvg` maps the incoming controller_id through a hardcoded `KNOWN_CONTROLLERS` Set; unknown ids fall back to `_generic` without ever reaching a dynamic-import path. Path-traversal injection impossible.
- **T-91-05-03 (DoS via spammed controller_detected):** `ControllerStage.render` early-returns if `this.mountedControllerId === controllerId` — same-controller reconnects are no-ops.
- **T-91-05-04 (DoS via tab-resume midi_position backlog):** `pendingPositions` LWW under the rAF drainer — only the LATEST frame between repaint slots is consumed; the backlog never paints frame-by-frame.
- **T-91-05-SC (npm/pip installs):** ZERO new packages — uses pre-existing vitest, ajv (pre-compiled), Vite ?raw, jsdom (test env).

No new threat-model surface or KAAN-ACTION items added by this plan.

## Self-Check: PASSED

Verifying file + commit claims:

- File `tauri/ui/src/learn/learn-window.ts`: FOUND (210 lines — REPLACED Plan 01's 51-line placeholder)
- File `tauri/ui/src/learn/ws-client.ts`: FOUND (139 lines)
- File `tauri/ui/src/learn/controllers/_aria-labels.ts`: FOUND (101 lines)
- File `tauri/ui/src/learn/controllers/pioneer_ddj_flx4.svg.ts`: FOUND (353 lines)
- File `tauri/ui/src/learn/controllers/_generic.svg.ts`: FOUND (49 lines)
- File `tauri/ui/src/learn/components/controller-stage.ts`: FOUND (175 lines)
- File `tauri/ui/src/learn/components/titlebar.ts`: FOUND (72 lines)
- File `tauri/ui/src/learn/components/empty-state.ts`: FOUND (44 lines)
- File `tauri/ui/src/learn/components/status-bar.ts`: FOUND (142 lines)
- File `tauri/ui/src/learn/components/unplugged-toast.ts`: FOUND (48 lines)
- File `tauri/ui/src/learn/styles/learn.css`: FOUND (306 lines)
- Commit `bfa01b80`: FOUND in `git log --oneline -3`
- Commit `71d218cd`: FOUND in `git log --oneline -3`
- `cd tauri/ui && npx tsc --noEmit`: exit 0
- `cd tauri/ui && npm run build`: exit 0, emits `dist/learn.html` (2.0kB) + lazy SVG chunks (FLX4 16.5kB, generic 1.7kB)
- `cd tauri/ui && npx vitest run tests/learn/`: 15 PASSED / 38 SKIPPED / 1 TODO / 0 FAILED
- `cd tauri/ui && npm test`: 966 PASSED / 38 SKIPPED / 1 TODO / 0 FAILED (no regression)
- `PYTHONPATH=src .venv/bin/python -m pytest tests/learn/ tests/ipc/test_learn_envelope_parity.py tests/runtime/test_ws_broadcast_30hz_under_learn_load.py`: 10/10 PASSED
- Latency P95: **0.66 ms** (target 50ms, red guardrail 80ms — both clear)
- No `<image href=` in any `tauri/ui/src/learn/` file: confirmed (0 grep hits)
- No `Inter|Roboto|Arial|system-ui` in any `tauri/ui/src/learn/` file: confirmed (0 grep hits)
- No hex literals inside SVG bodies: confirmed via `test_svg_currentcolor_only.spec.ts` PASS
- No `Pioneer DJ` wordmark in any `tauri/ui/src/learn/` file: confirmed via `pytest tests/learn/test_no_pioneer_brand_marks.py` PASS
- `new WebSocket("ws://127.0.0.1:8765")` literal at one call site (ws-client.ts line 58): confirmed
- No `websockets.serve` in `src/vibemix/learn/`: confirmed via `pytest tests/learn/test_no_new_ws_port.py` PASS (Invariant #4)
- No git deletions in either task commit: confirmed via `git diff --diff-filter=D --name-only`

## Next Phase Readiness

**Plan 91-06 (the 9 non-FLX4 SVGs)** is unblocked:
- The `ARIA_LABELS` lookup is hand-authored to cover all 10 profiles (Plan 06 just needs to use existing keys).
- The `loadControllerSvg` switch statement in `controller-stage.ts` has 9 placeholder branches (currently falling through to `_generic`). Adding a controller = adding one switch case + one `.svg.ts` file.
- The parity gate (`test_svg_profile_parity.spec.ts`) parameterised cases auto-promote per-controller as each `.svg.ts` lands — Plan 06 can ship the 9 SVGs incrementally.

**Plan 91-07 (Kaan ear-pass)** unblocked but gated on:
- Live `cargo tauri dev` + plugged-in FLX4 (the canonical ear-pass golden). All software-verifiable bits ship in P05; the visual + tactile pass is the next step.
- `python -m vibemix` running against current source (per `feedback_verify_live_app_not_just_tests` — bundled sidecar in `cargo tauri dev` is FROZEN).
- The "open Learn window" affordance — at present the Learn window opens via `learn_window::open_learn_window` Tauri command. P07 may add a session-deck button to fire it (currently devtools-invoke only).

**No KAAN-ACTION items added** by this plan. `§LEARN-LATENCY-CONTINGENCY` stays parked (synthetic P95 0.66ms, 120x under the trigger).

**Concurrent-session discipline upheld** — both task commits used named-path staging only; no `git add -A`; no deletions; no shared-file edits (Plan 01 already owned the placeholder learn-window.ts which Plan 05 was scheduled to REPLACE).

---
*Phase: 91-controller-renderer-midi-mirror*
*Plan: 05*
*Completed: 2026-05-28*
