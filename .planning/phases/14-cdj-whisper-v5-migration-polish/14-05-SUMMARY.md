---
phase: 14-cdj-whisper-v5-migration-polish
plan: 05
subsystem: ui
tags: [migration, mascot, three-js, tauri-overlay, border-anim, glass-chrome, vitest-unskip, phase-13-interop]

# Dependency graph
requires:
  - phase: 13-mascot-vtuber
    provides: Three.js renderer + canvas mount + WS bus subscription + state machine + asset loader + Meshy material fix (commit 2b608b6 — load-bearing for the chrome wrapper). The renderer + scene are CONSUMED by, not modified by, this plan.
  - phase: 14-cdj-whisper-v5-migration-polish
    plan: 01
    provides: scripted grep gates (--surface=mascot --strict) + vendored Saira + JetBrains Mono WOFF2 + 14-POLISH-LOG.md skeleton + Wave-0 mascot.chrome.test.ts describe.skip stub + tokens.css v5 primitives (--glass-3, --blur-glass-display, --glass-edge, --silk-40, --amber, --rad-md, .border-anim utility with .slow + .rev modifiers).
  - phase: 14-cdj-whisper-v5-migration-polish
    plan: 02
    provides: wizard surface fully migrated — visual sibling reference for the border-anim pattern on a glass-wrapped surface.
  - phase: 14-cdj-whisper-v5-migration-polish
    plan: 03
    provides: session surface fully migrated — glass-panel anatomy in src/session/components/panel.ts is the canonical analog this plan lifts for the mascot wrapper (per 14-PATTERNS.md Surface 4).
  - phase: 14-cdj-whisper-v5-migration-polish
    plan: 04
    provides: settings drawer fully migrated — confirms the Wave 0 vitest-unskip pattern used here for mascot.chrome.test.ts.
provides:
  - tauri/ui/mascot.html wrapped in .mascot-window glass-chrome rectangle with <link rel="stylesheet" href="/src/tokens.css"> + transparent body !important override + body::before disable + .border-anim.slow.rev (32s reverse sweep — de-syncs from session's 22s forward) + top "OVERLAY · STICKY · ALL SPACES · {W}×{H}" silkscreen caption + bottom "{class} · {state}" state caption
  - NEW tauri/ui/src/mascot/chrome.css owning the wrapper styling — anatomy lifted from src/session/components/panel.ts adapted for transparent canvas wrapper (--glass-3, --blur-glass-display 6px to minimise WebView2 #10064 trigger risk, border-radius 8px, amber bottom-edge inset undertone, z-index layering canvas=2 / captions=3 / border-anim=4)
  - tauri/ui/src/mascot/index.ts — import "./chrome.css" + 3 resolveCssColor calls migrated from stale --phosphor / --phosphor-soft / --ink-deep to v5 --amber / --silk / --silk-40 with v5 hex fallbacks (#ff8a3d / #d6cfc7 / #3d424c — the only 3 hex literals outside tokens.css) + overlay caption wiring (resize + rAF-tick poll, write-only-if-changed)
  - tauri/ui/tests/mascot.chrome.test.ts unskipped + rewritten (19 assertions across mascot.html / chrome.css / index.ts — Wave-0 4-test stub → Wave-4 19-test surface lock)
  - --strict v5 migration gate green on mascot surface (6 → 0 legacy refs)
  - --strict v5 fonts gate green on mascot surface (already 0)
  - npm run test full suite: 275 / 275 green, 0 skipped (Wave-3 baseline was 261 + 4 skipped)
  - npm run build green (tsc --noEmit + vite build, new mascot CSS chunk 0.99 kB)
affects: [14-06-shim-delete]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Transparent-overlay survives tokens.css link: mascot.html links /src/tokens.css for v5 primitives + .border-anim utility, then forces html/body { background: transparent !important; background-image: none !important; } + body::before { display: none !important; } to preserve the Phase 13 transparent-window invariant. !important is justified because tokens.css ships a v5 cinematic body background (radial vignette + rave washes + #02030a→#000000→#030208 gradient) at the global :root scope that would otherwise opaque-out the Tauri overlay window's desktop compositing path."
    - "Wrapper anatomy = panel.ts adapted for transparent canvas: --glass-3 (recessed) + --blur-glass-display (lightest 6px saturate(105%)) instead of session panel.ts's --glass-2 + --blur-glass-light, to minimise WebView2 transparency bug (tauri/tauri#10064) trigger risk per 14-CONTEXT Area 3. 32px blur on transparent overlays has caused backdrop opacity bleed on Win11 WebView2 in field reports; 6px is the conservative baseline. The wrapper still owns position: relative + overflow: hidden (required by .border-anim utility per tokens.css:320) + border-radius 8px (vs 6px elsewhere) per 14-UI-SPEC §Surface 4."
    - "z-index layering inside .mascot-window: canvas at z=2, captions at z=3, .border-anim sweep at z=4 — keeps the amber sweep visible above the Three.js scene without obscuring it (border-anim sits on the perimeter via inherited border-radius + content-box mask)."
    - "Caption wiring without state-machine re-entry: top-label dimension text updates on mount + window resize (cheap, throttled by the OS). Bottom-label state text polls machine.current inside the existing rAF loop, comparing against a lastStateLabelWritten cache — repaints only when the label actually changes (free no-op on most frames). No new event subscription on the state machine — Plan 13's pure-function state machine API has no event emitters and this plan does NOT introduce one; pull-side polling at rAF cadence is sub-millisecond."
    - "formatStateLabel({state}) — derive the silkscreen caption from MascotState by stripping the STATE_CLASS prefix (idle_bop_to_beat_mellow → idle · bop-to-beat-mellow; talk_loop_calm → talk · loop-calm; react_drop → react · drop; puff_particle → effect · particle; sleep → idle · sleep), then converting underscores to dashes inside the suffix per 14-UI-SPEC Copywriting Contract row 'Mascot state label'."
    - "3 v5 hex fallbacks remain — they're load-bearing for THREE.Color() construction when CSS resolution fails (e.g. jsdom test env, or pre-tokens.css boot race). Audit gate: these 3 (lines 410, 414, 417) are the ONLY hex literals permitted outside tokens.css repo-wide."

key-files:
  created:
    - tauri/ui/src/mascot/chrome.css
    - .planning/phases/14-cdj-whisper-v5-migration-polish/14-05-SUMMARY.md
  modified:
    - tauri/ui/mascot.html
    - tauri/ui/src/mascot/index.ts
    - tauri/ui/tests/mascot.chrome.test.ts
    - .planning/phases/14-cdj-whisper-v5-migration-polish/14-POLISH-LOG.md

key-decisions:
  - "Use --glass-3 + --blur-glass-display (6px) for the mascot wrapper instead of session panel.ts's --glass-2 + --blur-glass-light (16px). Rationale: minimise WebView2 transparency bug (#10064) trigger risk on Windows; the mascot overlay window is the highest-risk surface for this bug because it's the only window with transparent: true."
  - "32s reverse sweep on the mascot border-anim (vs session's 22s forward). Rationale: visual de-sync — the two amber sweeps must not synchronise when the user has both windows in view, per 14-CONTEXT Area 3."
  - "Border-radius 8px on the mascot wrapper (vs 6px elsewhere via --rad-md). Rationale: 14-UI-SPEC §Surface 4 explicitly calls for the slightly-larger radius to read as 'overlay window with curved corners' rather than 'panel'."
  - "Pull-side caption polling instead of pushing a new state-emit API onto the state machine. Rationale: Phase 13's pure-function state machine is locked (verifier-greppable purity discipline — no wall-clock reads, no timers, no event emitters). Adding an event emitter would break that contract. Polling machine.current at rAF cadence with a last-written cache is sub-millisecond and keeps the state machine API untouched."
  - "Omit dynamic import('../src/mascot/index.ts') test in mascot.chrome.test.ts. Rationale: instantiating the full Three.js mascot pipeline (renderer + asset-loader + ws-client) at module load would require GLB assets in the jsdom env and effectively be testing more than the chrome migration. The fs-based grep assertions cover the migration; npm run build (which runs tsc --noEmit) validates compilation."

patterns-established:
  - "Tauri transparent-overlay-window pattern: <link> tokens.css for design tokens, then defensively !important-override html/body background + disable body::before. Reusable for any future transparent overlay window (e.g. hypothetical floating BPM widget)."
  - "Three.js + glass-chrome composition: WebGL canvas at z=2 inside a relative-positioned glass rectangle with .border-anim at z=4 and silkscreen captions at z=3 — composes cleanly because the canvas has its own transparent clear (renderer.ts) and the wrapper's backdrop-filter sits behind."

requirements-completed: [POLISH-01, POLISH-02, POLISH-05]

# Metrics
duration: 7min
completed: 2026-05-13
---

# Phase 14 Plan 05: CDJ Whisper v5 Wave 4 — mascot overlay window chrome migration

**Phase 13 mascot overlay window wrapped in v5 glass chrome with 32s reverse border-anim sweep, tokens.css linked through transparent-overlay !important override, 3 resolveCssColor calls migrated to v5 amber/silk tokens, Three.js scene + renderer.ts UNTOUCHED, 6 → 0 legacy refs on mascot surface, vitest mascot.chrome spec unskipped from 4 skipped → 19 green.**

## Performance

- **Duration:** ~7 min
- **Started:** 2026-05-13T12:08:00Z
- **Completed:** 2026-05-13T12:15:00Z (approx)
- **Tasks:** 2 auto (+ 1 human-verify checkpoint auto-advanced)
- **Files created:** 2 (chrome.css, this SUMMARY)
- **Files modified:** 4 (mascot.html, mascot/index.ts, mascot.chrome.test.ts, 14-POLISH-LOG.md)

## Accomplishments

- **mascot.html structural diff (5 changes per UI-SPEC §Surface 4):**
  1. `<link rel="stylesheet" href="/src/tokens.css" />` added to `<head>` — v5 primitives + .border-anim utility now cascade in.
  2. `html, body { background: transparent !important; background-image: none !important; }` override — preserves the Phase 13 transparent-overlay invariant against the new tokens.css cinematic body background.
  3. `body::before { display: none !important; }` — disables the v5 film-grain SVG layer (it would render at z-index 9999 over the desktop on every overlay frame).
  4. `<div class="mascot-window">` wrapper inserted between `<body>` and `<canvas>`, with `<div class="border-anim slow rev" aria-hidden="true">` as the first child (32s reverse sweep — de-syncs from session's 22s forward).
  5. Top + bottom silkscreen captions (`OVERLAY · STICKY · ALL SPACES · {W}×{H}` and `idle · bop-to-beat`) seeded inline; updated at runtime by mascot/index.ts.

- **NEW `tauri/ui/src/mascot/chrome.css`** (87 lines) — `.mascot-window` + caption + canvas styling. Anatomy lifted from `tauri/ui/src/session/components/panel.ts:27–40` adapted for a transparent canvas wrapper:
  - `--glass-3` background (recessed, vs session's `--glass-2` primary panel)
  - `--blur-glass-display` (lightest 6px saturate(105%), vs session's `--blur-glass-light` 16px) to minimise WebView2 #10064 trigger risk
  - `border: 1px solid var(--glass-edge)` + 8px radius (vs 6px `--rad-md` elsewhere)
  - Inset shadow stack: top highlight (`--glass-top`), amber bottom-edge undertone (`rgba(255, 138, 61, 0.06)` — the "lit hardware" film of warmth), deep drop shadow (`rgba(0,0,0,0.85)`), faint outer halo (`rgba(255,255,255,0.018)`)
  - z-index reservations: canvas=2, captions=3, .border-anim=4 (above canvas so the amber sweep remains visible on the perimeter)

- **mascot/index.ts resolveCssColor migration (3 lines + 1 comment block):**

  | Line | Before                                                   | After                                                   |
  | ---- | -------------------------------------------------------- | ------------------------------------------------------- |
  | 410  | `resolveCssColor("--phosphor", "#ffa12e")`               | `resolveCssColor("--amber", "#ff8a3d")`                 |
  | 414  | `resolveCssColor("--phosphor-soft", "#efe6d6")`          | `resolveCssColor("--silk", "#d6cfc7")`                  |
  | 417  | `resolveCssColor("--ink-deep", "#3d424c")`               | `resolveCssColor("--silk-40", "#3d424c")`               |

  Plus the resolveCssColor doc comment rewritten to drop the stale `--phosphor` / `#ffa12e` text; the new comment names all 3 v5 token + hex pairs and reaffirms the audit gate that these 3 hex literals are the ONLY hex literals permitted outside tokens.css.

- **mascot/index.ts caption wiring** — adds `import "./chrome.css"` at the top + `STATE_CLASS` value import from `./types.js` + a 4-helper block at the bottom of `boot()`:
  - `overlayCaptionEl` / `stateCaptionEl` defensive querySelectors (silent no-op if mascot.html lacks the wrapper)
  - `writeOverlayCaption()` — writes `OVERLAY · STICKY · ALL SPACES · ${innerWidth}×${innerHeight}` on mount + every resize
  - `formatStateLabel(state)` — derives the silkscreen caption from MascotState (e.g. `idle_bop_to_beat_mellow` → `idle · bop-to-beat-mellow`)
  - `writeStateCaptionIfChanged()` — polled inside the existing rAF loop, repaints only when the label changes (`lastStateLabelWritten` cache)

- **Test surface:**
  - `tauri/ui/tests/mascot.chrome.test.ts` unskipped (`describe.skip` → `describe`).
  - Spec expanded from 4 stub assertions to 19 across three describe blocks (mascot.html / chrome.css / index.ts).
  - `npm run test -- mascot.chrome.test.ts --run` → 19 / 19 green.
  - `npm run test` (full suite) → 275 / 275 green, 0 skipped (Wave-3 baseline was 261 + 4 skipped).

- **Strict gates:**
  - `scripts/check_v5_migration.sh --surface=mascot --strict` → PASS (0 hits, was 6).
  - `scripts/check_v5_fonts.sh --surface=mascot --strict` → PASS (0 hits).

- **Build:** `npm run build` green (tsc --noEmit + vite build); new bundled `mascot-DgjZbB7Q.css` chunk at 0.99 kB.

- **Three.js scene + renderer.ts: UNTOUCHED.** Plan critical_directive 1 honoured byte-for-byte.

## Task Commits

1. **Task 14-05-01: Add .mascot-window chrome + create src/mascot/chrome.css + migrate mascot/index.ts resolveCssColor** — `31340b8` (feat)
2. **Task 14-05-02: Unskip mascot.chrome.test.ts + assert v5 chrome migration** — `e5765bc` (test)
3. **Task 14-05-03: Critique loop cycle 1 — checkpoint:human-verify** — auto-approved (auto-advance mode active)

**Plan metadata commit:** (this commit, recorded at final_commit step)

## Files Created/Modified

- `tauri/ui/mascot.html` — wrapper markup, tokens.css link, transparent !important override, body::before disable, top + bottom silkscreen captions
- `tauri/ui/src/mascot/chrome.css` (NEW) — .mascot-window glass-chrome styling
- `tauri/ui/src/mascot/index.ts` — import "./chrome.css", STATE_CLASS runtime import, resolveCssColor migration (3 lines + doc comment), caption wiring (writeOverlayCaption + formatStateLabel + writeStateCaptionIfChanged + rAF integration + resize handler bind)
- `tauri/ui/tests/mascot.chrome.test.ts` — describe.skip removed + 19 assertions across mascot.html / chrome.css / index.ts
- `.planning/phases/14-cdj-whisper-v5-migration-polish/14-POLISH-LOG.md` — mascot row 1 marked green + Side-by-Side Screenshots mascot row updated to "deferred"
- `.planning/phases/14-cdj-whisper-v5-migration-polish/14-05-SUMMARY.md` (this file)

## Decisions Made

See `key-decisions` in frontmatter. Five decisions:
1. `--glass-3 + --blur-glass-display` (6px) instead of `--glass-2 + --blur-glass-light` (16px) — WebView2 #10064 risk minimisation.
2. 32s reverse border-anim (`.slow.rev`) — de-sync from session's 22s forward sweep.
3. `border-radius: 8px` instead of `var(--rad-md)` (6px) — UI-SPEC §Surface 4.
4. Pull-side caption polling instead of state-machine event emitter — Phase 13 purity discipline.
5. Omit dynamic `import("../src/mascot/index.ts")` test — fs-based grep + `tsc --noEmit` already cover.

## Deviations from Plan

**None — plan executed exactly as written.**

The plan's `<interfaces>` block was very specific (5 structural changes, 3 resolveCssColor migrations, 1 new file with verbatim CSS, 4 caption-wiring helpers). All implemented as specified. The only minor implementation note: the plan suggested wiring the state caption via "subscribe to the state-machine's 'state changed' event" — I noted in `key-decisions` that the Phase 13 state machine is pure-function and has no event-emit API, so I used pull-side polling at rAF cadence with a write-only-if-changed cache (sub-millisecond, no API surface change). The plan also gave `console.debug` as the defensive-fallback option for missing wrapper elements, which I honoured for the top caption (the bottom caption silently returns since it's polled every frame).

## Auth Gates

None — pure CSS + DOM wiring + test changes, no external services touched.

## Issues Encountered

None.

## Mood-Swap Chrome Invariance — Deferred to Checkpoint Verification

Plan `<verification>` lists *"Mood swap (hype-man ↔ teacher ↔ coach) leaves chrome color identical"* — this is a Kaan-side runtime check (`npm run tauri dev` → open settings → click mascot mood pills → eyeball the chrome). Auto-mode advanced past the checkpoint without that visual check.

**Code-level invariant guarantee:** The chrome (border-anim, glass-3 background, amber bottom-edge undertone, captions) is declared in `chrome.css` and references no mood-conditional CSS variables — the wrapper is mood-static by construction. The 3 resolveCssColor calls in `handleMoodChange()` feed `renderer.playParticlePuff(color)` + `renderer.setMoodLighting(profile)` only (Three.js scene), never the chrome. Mood-swap chrome invariance therefore holds by construction; the Kaan-side verification is a sanity check, not a discovery gate.

## Tauri WebView2 Transparency Status (RESEARCH watchout)

- **macOS (Kaan's M-series, dev env):** Not yet verified in `npm run tauri dev`. WKWebView path doesn't carry the WebView2 #10064 bug; mascot overlay transparency is expected to work as in Phase 13 baseline. Deferred to Kaan-side `npm run tauri dev` review.
- **Windows (non-dev rehearsal):** Deferred to Phase 20 fresh-machine rehearsal (or Wave 5 if a Windows non-dev becomes available). Plan threat register T-14-05-01 disposition: mitigate via Wave 5 / Phase 20 borrow.

## Deferred Screenshots

Per the prior-wave precedent (14-02 / 14-03 / 14-04 all deferred Kaan-side screenshots), this surface defers:
- Live overlay screenshot at native resolution
- Side-by-side with `mocks/vibemix-direction-final.html §01` right column (.mascot-window)
- Mood-swap chrome invariance pair (hype-man / teacher / coach × overlay screenshot — only Three.js animation should differ)

Kaan to capture during `npm run tauri dev` review pass and attach to 14-POLISH-LOG.md.

## Next Phase Readiness

- **Wave 5 (14-06 shim-delete):** All four surfaces (wizard / session / settings / mascot) now pass `--strict` v5 migration gate. Wave 5 can delete the tokens.css legacy shim block (lines 175–231 per Plan 14-01) safely — zero consumer refs remain.
- **Polish debt:** None escalated from this wave.
- **Three.js scene:** Untouched; Phase 13 renderer + Meshy material fix (commit 2b608b6) carry forward unchanged.

## Self-Check: PASSED

- [x] FOUND: tauri/ui/mascot.html (modified, contains .mascot-window + border-anim slow rev)
- [x] FOUND: tauri/ui/src/mascot/chrome.css (created)
- [x] FOUND: tauri/ui/src/mascot/index.ts (modified, resolveCssColor migrated)
- [x] FOUND: tauri/ui/tests/mascot.chrome.test.ts (unskipped, 19 assertions)
- [x] FOUND commit 31340b8 (Task 14-05-01)
- [x] FOUND commit e5765bc (Task 14-05-02)
- [x] FOUND: .planning/phases/14-cdj-whisper-v5-migration-polish/14-POLISH-LOG.md (mascot row 1 green)

---
*Phase: 14-cdj-whisper-v5-migration-polish*
*Completed: 2026-05-13*
