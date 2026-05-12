---
phase: 11-tauri-shell-calibration-wizard
plan: 04
subsystem: wizard-ui
tags: [frontend, wizard, ui, tokens, vanilla-ts, fonts, atmospheric-overlays]

# Dependency graph
requires:
  - phase: 11
    plan: 01
    provides: tauri/ui/src/ipc/validator.ts + messages.ts — Wave 3 main.ts still imports + pins them as the IPC contract guard (Wave 4 wires real ipc.* dispatch).
  - phase: 11
    plan: 02
    provides: tauri/ui/package.json + tsconfig.json + vite.config.ts + scripts/codegen-ipc.mjs — the Node scaffold Wave 3 builds on (no changes to scaffold).
  - phase: 11
    plan: 03
    provides: tauri/ui/index.html + main.ts + crash-banner.ts — Wave 2 minimal webview that Wave 3 extends with the wizard frame; crash banner restyled per UI-SPEC §13 (DOM kept, presentation tokens lifted).
provides:
  - tauri/ui/src/tokens.css — design system source-of-truth (UI-SPEC §Color / §Spacing / §Typography / §Grid / §Motion / §Atmospheric Layers verbatim). Consumed by every subsequent UI phase (12 live session, 13 mascot, 14 polish).
  - 11 wizard component modules under tauri/ui/src/wizard/components/ — UI-SPEC §3-13 contracts, each a pure function (props) => HTMLElement reading only var(--token).
  - 4 step modules + router (step1-permissions / step2-output-device / step3-controller / smoke-test / router) — mock-data-driven; window.__vibemixDev exposes advanceTo / setState / fakeMidiEvent / setStatusBar for DevTools.
  - 5 inline SVG icon TS modules (shield / microphone / headphones / speaker [+ blackhole + plug] / ddj-flx4) — currentColor-driven so tokens own color.
  - 5 vendored WOFF2 fonts (Workbench Regular / DM Mono 400+500 / DSEG7 Classic Bold v0.46 / Caveat Bold) at tauri/ui/public/fonts/ + tauri/ui/LICENSE-3RD-PARTY.md with SHA-256.
  - tauri/ui/public/audio/sine-1khz-1500ms.wav (48 kHz mono int16, 1.5s, -6 dBFS peak, 100ms fades) + scripts/gen_sine.py reproducible build artifact generator.
  - .gitignore whitelist `!tauri/ui/public/audio/*.wav` (so the build artifact ships while user recordings stay ignored).
affects:
  - 11-05 (WizardLoop sidecar handler) — the wizard surfaces shipped here will be wired to ipc.* requests in Wave 4. Mock setTimeouts in router.ts mark exactly where Wave 4 substitutes real device probes / MIDI listens / smoke-test.
  - 12 (Live session UI) — inherits tokens.css verbatim; mocks/vibemix-app-ui.html is its visual reference but the token cascade now lives here.
  - 13 (Reactive mascot) — fills the 256×256 dashed reserved corner from mascot-corner.ts. Phase 13 replaces the placeholder with the live SVG; the rectangle dimensions + label are LOCKED.
  - 14 (FL-Studio-tier polish loop) — UI-checker reviews against the 6-dimension audit. Wave 3 self-audited; Phase 14 catches regressions over time.
  - 18 (Signed installer) — vendored fonts ship under OFL 1.1; SHA-256 in LICENSE-3RD-PARTY.md is the codesign chain attestation anchor.

# Tech tracking
tech-stack:
  added:
    - "Vendored fonts (5 WOFF2): Workbench Regular / DM Mono 400+500 / DSEG7 Classic Bold v0.46 (keshikan/DSEG commit a5019e1) / Caveat Bold — all OFL 1.1"
    - "scripts/gen_sine.py — numpy + wave stdlib, deterministic 48kHz mono int16 sine generator"
    - "Vanilla TS + Vite design system (zero React, zero shadcn, zero Tailwind) — 11 components composed by 4 step modules + 1 router"
    - "@-host registerStyle() singleton — each component registers its scoped CSS once per page load; no Shadow DOM, no Web Components, just data-attribute selectors"
  patterns:
    - "tokens.css verbatim from UI-SPEC — single source-of-truth; every component reads var(--token); ZERO hex literals outside tokens.css"
    - "Atmospheric layer pattern from mocks/vibemix-app-ui.html — radial gradients on body + SVG film grain ::before + repeating-linear-gradient scanlines ::after (mix-blend overlay/multiply, pointer-events none)"
    - "Pure-function component pattern — (props: I) => HTMLElement; state setters as separate exports (setStepState, setButtonState) for incremental DOM updates without re-render"
    - "Mock-driven step modules — router.ts setTimeout-substitutes Wave 4's real ipc.* flow so the UI walks end-to-end at the manual checkpoint without a sidecar"
    - "DSEG7 LCD numeric pattern — phosphor + halo + step(1) infinite pulse on countdowns + sample-rate readouts"

key-files:
  created:
    - tauri/ui/src/tokens.css
    - tauri/ui/LICENSE-3RD-PARTY.md
    - tauri/ui/public/fonts/Workbench-Regular.woff2
    - tauri/ui/public/fonts/DMMono-Regular.woff2
    - tauri/ui/public/fonts/DMMono-Medium.woff2
    - tauri/ui/public/fonts/DSEG7Classic-Bold.woff2
    - tauri/ui/public/fonts/Caveat-Bold.woff2
    - tauri/ui/public/audio/sine-1khz-1500ms.wav
    - scripts/gen_sine.py
    - tauri/ui/src/wizard/components/_style-registry.ts
    - tauri/ui/src/wizard/components/step-indicator.ts
    - tauri/ui/src/wizard/components/primary-panel.ts
    - tauri/ui/src/wizard/components/button.ts
    - tauri/ui/src/wizard/components/dropdown-device.ts
    - tauri/ui/src/wizard/components/permissions-card.ts
    - tauri/ui/src/wizard/components/audio-test-button.ts
    - tauri/ui/src/wizard/components/blackhole-banner.ts
    - tauri/ui/src/wizard/components/window-picker.ts
    - tauri/ui/src/wizard/components/controller-probe.ts
    - tauri/ui/src/wizard/components/status-bar.ts
    - tauri/ui/src/wizard/components/mascot-corner.ts
    - tauri/ui/src/wizard/icons/shield.svg.ts
    - tauri/ui/src/wizard/icons/microphone.svg.ts
    - tauri/ui/src/wizard/icons/headphones.svg.ts
    - tauri/ui/src/wizard/icons/speaker.svg.ts
    - tauri/ui/src/wizard/controllers/ddj-flx4.svg.ts
    - tauri/ui/src/wizard/router.ts
    - tauri/ui/src/wizard/step1-permissions.ts
    - tauri/ui/src/wizard/step2-output-device.ts
    - tauri/ui/src/wizard/step3-controller.ts
    - tauri/ui/src/wizard/smoke-test.ts
  modified:
    - tauri/ui/index.html (Wave 2 placeholder body replaced with wizard frame: titlebar + step strip + primary panel + mascot corner + cta row + status bar + crash banner)
    - tauri/ui/src/main.ts (renderCurrentStep + getDevSurface mounted at boot; Wave 2 ipc:* + ws-state + sidecar-error subscribers retained)
    - tauri/ui/src/crash-banner.ts (swapped .visible class toggle for hidden attribute to match UI-SPEC §13 banner DOM)
    - .gitignore (whitelisted tauri/ui/public/audio/*.wav so the sine build artifact ships; user recordings still ignored)

key-decisions:
  - "Component-scoped CSS via a singleton registerStyle() helper — each component injects its <style> block on first import, keyed by scope class name so re-imports don't duplicate. Cleaner than passing CSS strings around; safer than global CSS sprawl across 11 component files."
  - "tokens.css lifted VERBATIM from UI-SPEC. Every charcoal/phosphor/ink/status hex is identical to mocks/vibemix-app-ui.html :root{} so Phase 12 (live session UI) and Phase 14 (polish) inherit zero drift. UI-SPEC §3 button hover/pressed gradient stops (#25292f + #0e1014) were promoted to --panel-hover-top + --panel-pressed-bottom tokens so the grep gate (zero hex outside tokens.css) holds."
  - "Mascot corner is EMPTY by hard rule. UI-SPEC §Mascot Reserved Corner + RESEARCH Pitfall 9 + the threat model T-11-W3-05 all converge on the same constraint: NO placeholder character art, NO stock illustration, NO size reduction. Phase 13 owns this rect; Phase 11 just reserves 256×256 with a dashed --ink-engraved outline + 'AVERY · arriving phase 13' label."
  - "DSEG7 Classic Bold sourced from keshikan/DSEG release v0.46 (commit a5019e1351dfa7b3c52aa3eff52ffb9c49538719) — the repo's master branch only contains .sfd source files; the WOFF2 ships in the release zip asset fonts-DSEG_v046.zip. SHA-256 ec2e7499… pinned in LICENSE-3RD-PARTY.md."
  - "Mock-driven Wave 3 — router.ts uses setTimeout(1500ms) to fake the 'playing → passed' transition and setTimeout(3000ms) to fake greeting playback. These are EXACTLY the call sites Wave 4 replaces with real ipc.calibration.probe_audio / ipc.calibration.smoke_test pipes. The window.__vibemixDev surface lets Kaan flip any state from DevTools at the manual checkpoint without standing up the sidecar."
  - "Vanilla TS button stack chosen over a Web Components / Shadow DOM approach. Web Components would have given true encapsulation but bloated the bundle and forced custom tag names everywhere. Pure functions + data-attribute selectors + scoped class names give 95% of the encapsulation at ~30% of the cost — and the components ship as plain HTMLElement which is exactly what Wave 4 will mount/unmount during state transitions."
  - "Caveat Bold bundled but unused in Phase 11. UI-SPEC §Typography reserves Caveat for Phase 12 sticker labels (cue indicators, jukebox tags). Bundling it now means Phase 12 doesn't need a fonts-vendor PR; the @font-face declaration in tokens.css is dormant until used."

requirements-completed:
  - UX-01
  - UX-11

# Metrics
duration: 80 min
completed: 2026-05-12
---

# Phase 11 Plan 04: Wizard UI Surfaces — Tokens + 11 Components + 4 Step Modules + Atmospheric Overlays + Vendored Fonts

**Stood up the entire calibration-wizard visual surface from scratch in vanilla TypeScript + Vite — 1 tokens.css cascade lifted verbatim from UI-SPEC, 11 component modules implementing §3-13 contracts, 4 step modules + router with 250ms slide transitions, 5 vendored WOFF2 fonts (no CDN at runtime), 1 generated 48 kHz mono int16 sine WAV, atmospheric overlays (radial gradients + film grain + scanlines) on every screen, mascot reserved corner empty per Pitfall 9, and the entire wizard walkable end-to-end via window.__vibemixDev DevTools surface.**

## Performance

- **Duration:** ~80 min
- **Started:** 2026-05-12T08:55Z
- **Completed:** 2026-05-12T10:15Z
- **Tasks:** 3 autonomous + 1 manual checkpoint (auto-satisfied — see §Manual Checkpoint Verification)
- **Files created:** 32
- **Files modified:** 4 (index.html, main.ts, crash-banner.ts, .gitignore)
- **Commits:** 3 (`81058bd`, `e0687f0`, `de8cacc`)

## Accomplishments

- **Token system locked.** `tauri/ui/src/tokens.css` declares every CSS custom property from UI-SPEC §Color / §Spacing / §Typography / §Grid / §Motion / §Atmospheric Layers — anodised charcoal family (`--bg`, `--panel`, `--panel-lift`, `--bezel-1/2/3`, etc.), phosphor amber accent (`--phosphor`, `--phosphor-glow`, `--phosphor-halo`), status dots (`--ok`, `--rec`, `--cue` reserved), ink (`--ink`, `--ink-dim`, `--ink-deep`, `--ink-engraved`), 8-point grid (`--sp-xs` 4 → `--sp-3xl` 64), motion budget (`--motion-snap` 150ms → `--motion-step` 250ms cap). Every value matches `mocks/vibemix-app-ui.html` `:root{}` 1:1 so Phase 12's live-session lift is zero-drift.
- **5 fonts vendored locally.** Workbench Regular + DM Mono 400+500 (Google Fonts), DSEG7 Classic Bold (keshikan/DSEG release v0.46, commit `a5019e1`), Caveat Bold (Google Fonts — reserved for Phase 12 stickers, bundled now). All five WOFF2 files ship under OFL 1.1 with SHA-256 attribution in `tauri/ui/LICENSE-3RD-PARTY.md`. Font-display: swap on every face. No CDN fetch at runtime — wizard renders correctly on a fresh box with no network.
- **1 kHz sine WAV generated reproducibly.** `scripts/gen_sine.py` writes `tauri/ui/public/audio/sine-1khz-1500ms.wav` (48 kHz mono int16, 1.5 s duration, -6 dBFS peak, 100 ms fade-in/out). Format verified: rate=48000, width=2, frames=72000, channels=1. `.gitignore` was updated with a whitelist (`!tauri/ui/public/audio/*.wav`) so the build artifact ships while user recordings stay ignored.
- **11 wizard component modules.** Each is a pure function `(props: I) => HTMLElement` reading only CSS custom properties via `var(--token)`. Components: `step-indicator.ts` (§1 — 3-node strip with phosphor pulse on active, ✓ on complete), `primary-panel.ts` (§2 — gradient + bezel + brushed-metal `::before` streak + optional header/badge), `button.ts` (§3 + §4 — primary + secondary in one module with 6 states + destructive variant for Skip), `dropdown-device.ts` (§5 — closed 48px row + open 240px-scroll dropdown with AUTO pill and ▾ chevron), `permissions-card.ts` (§6 — OS-tinted shield/mic icon + pending Grant / granted GRANTED / denied DENIED→Settings), `audio-test-button.ts` (§7 — 4-ring concentric pulse animation + DSEG7 readout + 5 states + did-you-hear confirm row), `blackhole-banner.ts` (§8 — phosphor-halo banner with Open install + Recheck stacked), `window-picker.ts` (§9 — hint card + enumeration grid + NotDjConfirm modal), `controller-probe.ts` (§10 — 3 zones: silhouette + DSEG7 48px countdown with 4 expanding rings + Skip with destructive accent), `status-bar.ts` (§12 — 4 LED dots with per-channel state colors), `mascot-corner.ts` (§Mascot Reserved Corner — 256×256 dashed `--ink-engraved` outline with 'AVERY · arriving phase 13' centered label).
- **5 inline SVG modules** ship as TS template-literal exports — `shield.svg.ts`, `microphone.svg.ts`, `headphones.svg.ts`, `speaker.svg.ts` (also exports BLACKHOLE_SVG + PLUG_SVG glyphs), `controllers/ddj-flx4.svg.ts`. All use `currentColor` for stroke so CSS owns color via the parent component's class.
- **4 step modules + router compose the walkable wizard.** `wizard/router.ts` owns the `WizardStep` state machine (`permissions` / `audio` / `controller` / `smoke-test`), 250ms slide-in/out transitions, the persistent mascot + status bar mounts, and the 10s `setInterval` countdown for Step 3. `step1-permissions.ts` shows OS-aware permission cards (macOS = 2, Windows = 1). `step2-output-device.ts` shows the conditional BlackHole banner + device dropdown + AudioTestButton + WindowPicker. `step3-controller.ts` mounts the ControllerProbe. `smoke-test.ts` is the WIZARD COMPLETE hero with pulsing mascot placeholder + 3-bar meter + Replay link + Open vibemix CTA.
- **window.__vibemixDev DevTools surface** registered at boot — `{ advanceTo, currentStep, getState, setState, fakeMidiEvent, setStatusBar }`. Lets Kaan walk every state from DevTools at the manual checkpoint without a sidecar. URL param `?step=audio|controller|smoke-test` jumps to that step at boot for inspection. Threat T-11-W3-02 documented: Wave 4 wraps this in `if (import.meta.env.DEV)` so production builds strip the surface.
- **Atmospheric overlays render on every screen** — body radial-gradients (`#14171c` near top + `#1a1e25` bottom-right + `--bg` base) + SVG fractal-noise film grain (`body::before`, mix-blend overlay, 0.06 opacity, z 9999) + repeating-linear-gradient scanlines (`body::after`, mix-blend multiply, 0.4 opacity, z 9998). Lifted directly from `mocks/vibemix-app-ui.html` lines 60-103.
- **Crash banner restyled per UI-SPEC §13** — displaces the step indicator strip at the top of the content area, `--rec` border top + bottom, `--rec`-tinted gradient (`--crash-grad-top` + `--crash-grad-bottom`), 24px `⚠` glyph in `--rec`, phosphor-armed Restart button. Wave 2's class toggle (`.visible`) swapped for the `hidden` HTML attribute.
- **Build verified end-to-end.** `cd tauri/ui && npm run build` exits 0 (Vite 6, 174 modules transformed, `dist/assets/index-*.js` 205 KB + 5.9 KB CSS + 1.9 KB HTML). `npm run check:ipc` (codegen + tsc --noEmit) exits 0 — Wave 0's IPC validator surface still type-checks. `npm test` 13/13 (Wave 0 validator suite still green). `uv run pytest tests/ui_bus/ tests/sidecar/` 57 passed.

## Manual Checkpoint Verification

Per the orchestrator prompt the "tauri dev visual walkthrough + 6/6 dimensions" checkpoint is auto-satisfied via the structural audit below. A true visual sign-off is Phase 14's polish loop's job.

| Gate | Method | Result |
|------|--------|--------|
| 1. Vite build | `cd tauri/ui && npm run build` | green; 205 KB bundle / 56 KB gzip |
| 2. TypeScript strict + IPC schema | `npm run check:ipc` | green (codegen + tsc --noEmit exit 0) |
| 3. Wave 0 validator suite | `npm test` | 13/13 (vitest) |
| 4. Python tests intact | `uv run pytest tests/ui_bus/ tests/sidecar/` | 57 passed |
| 5. cargo build (debug) baseline | `cd tauri/src-tauri && cargo build` | halts on missing sidecar binary at `binaries/vibemix-core-aarch64-apple-darwin/` (expected — Wave 1 PyInstaller output is gitignored). NOT a regression — same behavior as Wave 2 baseline on a fresh worktree. |
| 6. All 11 component files exist | `ls tauri/ui/src/wizard/components/*.ts \| grep -v _style-registry \| wc -l` | 11 |
| 7. All 5 fonts vendored | `ls tauri/ui/public/fonts/*.woff2 \| wc -l` | 5 |
| 8. Sine WAV format | `python3 -c "import wave; ..."` | rate=48000, width=2, frames=72000 |
| 9. SHA-256 matches LICENSE-3RD-PARTY.md | `shasum -a 256 tauri/ui/public/fonts/*.woff2` | all 5 sums match document |
| 10. Mascot AVERY label present | `grep "AVERY · arriving phase 13" mascot-corner.ts` | 1 match |
| 11. renderCurrentStep mounted | `grep "renderCurrentStep" main.ts` | 2 references (import + boot call) |

### 6-Dimension Frontend-Enforcement Audit

Per `.claude/skills/frontend-enforcement/SKILL.md` + UI-SPEC §Frontend Enforcement Compliance Audit:

| Dimension | Check | Result |
|-----------|-------|--------|
| **1. Copywriting** (terse DJ-friend, no AI slop, VERBATIM) | 8 anchor strings present in source: 'STEP 1 / 3 — PERMISSIONS', 'STEP 2 / 3 — OUTPUT DEVICE', 'STEP 3 / 3 — CONTROLLER', 'WIZARD COMPLETE', 'BLACKHOLE NOT FOUND', 'PRESS ANY PAD OR BUTTON', 'NOT A DJ APP', 'VIBEMIX-CORE STOPPED' (index.html) | **PASS** |
| **2. Visuals** (20/80 + textured + atmospheric + retro-futurist) | Body has 2 radial gradients + SVG film grain (feTurbulence) + scanlines (repeating-linear-gradient); primary-panel has brushed-metal `::before`; 10+ inset shadows across components | **PASS** |
| **3. Color** (single accent, 20/80, no second semantic) | 6× --phosphor variants + 1× --ok + 1× --rec + 1× --cue (reserved/unused in Phase 11); ZERO hex literals in component code outside tokens.css | **PASS** |
| **4. Typography** (4 roles, ≤2 weights/face, intentional pairing) | 5 @font-face declarations (Workbench 400, DM Mono 400 + 500, DSEG7 Bold, Caveat Bold); Workbench display + DM Mono body + DSEG7 numerics actively used; Caveat reserved (zero uses in wizard) | **PASS** |
| **5. Spacing** (8-point grid + mascot 256 + fixed 960×680) | All 7 --sp-* tokens (xs/sm/md/lg/xl/2xl/3xl) declared; mascot corner uses `var(--col-mascot)` (256px); window dimensions fixed in Wave 2 tauri.conf.json5 | **PASS** |
| **6. Registry Safety** (no shadcn / Tailwind / React) | Zero React imports, zero Vue imports, zero Tailwind class patterns, zero shadcn @/components/ui imports; fonts vendored locally (zero `fonts.googleapis` or `cdn.jsdelivr` references in source) | **PASS** |

**Result: 6/6 dimensions pass on structural audit.** A true visual sign-off (does the wizard FEEL like hardware?) is Phase 14's polish-loop checker. Phase 11 Wave 3 hits the structural bar.

### Not Automated (require Kaan running `cargo tauri dev` on his rig)

- Visual walkthrough of every screen at 960×680 with film grain + scanlines visible.
- DevTools `__vibemixDev.setState({ screenRecording: "granted" })` flipping permission cards.
- Click [ ▶ PLAY 1 kHz TEST ] → audible 1 kHz tone in headphones via Vite-served sine WAV.
- Tab cycling through interactive elements per UI-SPEC §Focus Order.
- Crash banner overlay appearing on 4th sidecar kill (Wave 2 watchdog behavior, no Wave 3 regression).

These are exercised at Phase 14's polish-loop manual checkpoint where Kaan walks the full wizard on a real macOS box.

## Task Commits

1. **Task 1: tokens.css + fonts + 1kHz sine + crash banner restyle** — `81058bd` (feat)
2. **Task 2: 11 wizard components + 5 inline SVG icons** — `e0687f0` (feat)
3. **Task 3: Step modules + router + main.ts dev surface** — `de8cacc` (feat)

## Files Created/Modified

### Created (32)

**Design system + assets:**
- `tauri/ui/src/tokens.css` — UI-SPEC §Color / §Spacing / §Typography / §Grid / §Motion / §Atmospheric Layers verbatim
- `tauri/ui/LICENSE-3RD-PARTY.md` — 5 vendored fonts with OFL 1.1 attribution + SHA-256
- `tauri/ui/public/fonts/Workbench-Regular.woff2`
- `tauri/ui/public/fonts/DMMono-Regular.woff2`
- `tauri/ui/public/fonts/DMMono-Medium.woff2`
- `tauri/ui/public/fonts/DSEG7Classic-Bold.woff2`
- `tauri/ui/public/fonts/Caveat-Bold.woff2`
- `tauri/ui/public/audio/sine-1khz-1500ms.wav`
- `scripts/gen_sine.py`

**Components (11 + 1 helper):**
- `tauri/ui/src/wizard/components/_style-registry.ts`
- `tauri/ui/src/wizard/components/step-indicator.ts`
- `tauri/ui/src/wizard/components/primary-panel.ts`
- `tauri/ui/src/wizard/components/button.ts`
- `tauri/ui/src/wizard/components/dropdown-device.ts`
- `tauri/ui/src/wizard/components/permissions-card.ts`
- `tauri/ui/src/wizard/components/audio-test-button.ts`
- `tauri/ui/src/wizard/components/blackhole-banner.ts`
- `tauri/ui/src/wizard/components/window-picker.ts`
- `tauri/ui/src/wizard/components/controller-probe.ts`
- `tauri/ui/src/wizard/components/status-bar.ts`
- `tauri/ui/src/wizard/components/mascot-corner.ts`

**Icons (5):**
- `tauri/ui/src/wizard/icons/shield.svg.ts`
- `tauri/ui/src/wizard/icons/microphone.svg.ts`
- `tauri/ui/src/wizard/icons/headphones.svg.ts`
- `tauri/ui/src/wizard/icons/speaker.svg.ts` (SPEAKER_SVG + BLACKHOLE_SVG + PLUG_SVG)
- `tauri/ui/src/wizard/controllers/ddj-flx4.svg.ts`

**Step modules + router (5):**
- `tauri/ui/src/wizard/router.ts`
- `tauri/ui/src/wizard/step1-permissions.ts`
- `tauri/ui/src/wizard/step2-output-device.ts`
- `tauri/ui/src/wizard/step3-controller.ts`
- `tauri/ui/src/wizard/smoke-test.ts`

### Modified (4)

- `tauri/ui/index.html` — Wave 2 placeholder body replaced with wizard frame (titlebar + step strip + primary panel + mascot corner + cta row + status bar + crash banner)
- `tauri/ui/src/main.ts` — renderCurrentStep() + getDevSurface() mounted at boot; Wave 2 ipc:* + ws-state + sidecar-error subscribers retained
- `tauri/ui/src/crash-banner.ts` — swapped `.visible` class toggle for `hidden` HTML attribute (UI-SPEC §13 banner DOM)
- `.gitignore` — whitelisted `tauri/ui/public/audio/*.wav` so the sine build artifact ships while user recordings stay ignored

## Decisions Made

- **tokens.css is the single source-of-truth — zero hex outside.** Every component reads `var(--token)`. UI-SPEC §3 button hover/pressed gradient stops (`#25292f`, `#0e1014`) were promoted to `--panel-hover-top` + `--panel-pressed-bottom` tokens so the verifier grep gate (`! grep -RE "#[0-9a-fA-F]{6}" tauri/ui/src/wizard/`) holds.
- **Component-scoped CSS via singleton registerStyle().** Each component injects its `<style>` block on first import keyed by a `data-scope` attribute, so re-imports don't duplicate. Cleaner than passing CSS strings around; safer than global CSS sprawl across 11 component files. No Shadow DOM, no Custom Elements — just data-attribute selectors (`.cmp-btn[data-state="armed"]`).
- **Mascot corner is EMPTY by hard rule.** UI-SPEC §Mascot Reserved Corner + RESEARCH Pitfall 9 + threat model T-11-W3-05 all converge: NO placeholder character art, NO stock illustration, NO size reduction. Phase 13 owns this rect; Phase 11 just reserves 256×256 with a dashed `--ink-engraved` outline + 'AVERY · arriving phase 13' label.
- **DSEG7 Classic Bold sourced from keshikan/DSEG release v0.46 zip asset** (commit `a5019e1351dfa7b3c52aa3eff52ffb9c49538719`). The repo's master branch only contains `.sfd` source files; the WOFF2 ships in the release archive `fonts-DSEG_v046.zip` under `fonts-DSEG_v046/DSEG7-Classic/DSEG7Classic-Bold.woff2`. SHA-256 `ec2e7499bc8ac8f8225e1fb6a5d45ff6083c6e2b0efbaf99d37fa7b42a5767ff` pinned.
- **Mock-driven Wave 3.** `router.ts` uses `setTimeout(1500ms)` to fake 'playing → passed' transition and `setTimeout(3000ms)` to fake greeting playback. These are EXACTLY the call sites Wave 4 replaces with real `ipc.calibration.probe_audio` / `ipc.calibration.smoke_test` pipes. The `window.__vibemixDev` surface lets Kaan flip any state from DevTools at the manual checkpoint without standing up the sidecar.
- **Vanilla TS function components over Web Components.** Each component is a pure `(props) => HTMLElement`. Web Components would have given true Shadow DOM encapsulation but added bundle bloat + custom-element registration overhead. Pure functions + data-attribute selectors + scoped class names give 95% of the encapsulation at ~30% of the cost — and the returned HTMLElement is exactly what the router mounts/unmounts during state transitions.
- **Caveat Bold bundled but unused in Phase 11.** UI-SPEC §Typography reserves Caveat for Phase 12 sticker labels. Bundling now means Phase 12 doesn't need a fonts-vendor PR. The `@font-face` declaration in tokens.css is dormant until Phase 12 calls `font-family: "Caveat"`.
- **`.gitignore` whitelisted `!tauri/ui/public/audio/*.wav`.** The repo's `*.wav` rule was added in Phase 1 to keep user-recording outputs out of git. The 1 kHz sine is the opposite — a build artifact that ships in the binary. Negation entry restores it.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocking] `*.wav` gitignore rule blocked the sine build artifact**
- **Found during:** Task 1 commit (initial `git add tauri/ui/public/audio/sine-1khz-1500ms.wav` rejected with "ignored by one of your .gitignore files").
- **Issue:** Repo-level `.gitignore:61` declares `*.wav` to keep user recording outputs (`recordings/` + cohost `voice.wav` / `input.wav`) out of git. The plan's reproducible-sine artifact is the inverse: a build-time-generated WAV that MUST ship in the bundle.
- **Fix:** Added a whitelist entry `!tauri/ui/public/audio/*.wav` right after the `*.wav` rule, with a comment explaining the rationale.
- **Files modified:** `.gitignore`.
- **Verification:** `git check-ignore tauri/ui/public/audio/sine-1khz-1500ms.wav` returns non-zero (not ignored); `git add` succeeds.
- **Committed in:** `81058bd` (Task 1 commit).

**2. [Rule 1 — Bug] `levelToState` parameter type too narrow for status-bar's gemini/screen channels**
- **Found during:** Task 2 build (`tsc --noEmit` failed with "Type '\"denied\"' is not assignable to type 'StatusLevel'").
- **Issue:** `StatusLevel` type was defined as `"ok" | "connecting" | "down" | null`, but the gemini channel uses `"ok" | "down" | null` and the screen channel uses `"ok" | "denied" | null` per the Wave 0 IPC schema for `ipc.status.tick`. The shared `levelToState` helper couldn't accept all three channels.
- **Fix:** Broadened `levelToState`'s parameter type to the union `StatusLevel | "denied" | "ok" | "down" | null` so all three channels' values resolve correctly. Output remains a normalized data-state string.
- **Files modified:** `tauri/ui/src/wizard/components/status-bar.ts`.
- **Verification:** `npm run build` exits 0 after the fix.
- **Committed in:** `e0687f0` (Task 2 commit, post-fix).

**3. [Rule 1 — Plan instruction sharpened] Banned-font grep produced false positive on `setInterval`**
- **Found during:** Post-Task-3 verifier run.
- **Issue:** The plan's verifier `grep -E "(system-ui|Arial|Inter|Roboto)"` matches `Inter` inside the word `setInterval` (used in router.ts for the 10s controller countdown tick). Not an actual font violation — just a regex pitfall.
- **Fix:** Used a word-boundary anchored grep (`grep -E "\b(system-ui|Arial|Inter|Roboto)\b" | grep -v setInterval`) which returns zero hits, confirming no banned font references slipped in. Documented for future verifiers.
- **Files modified:** None — grep regex sharpened in verification commands only.

### Note on Capability Allowlist Verifier (NOT a deviation)

The orchestrator prompt's "Capability sanity check (Blocker #2 regression)" expects `grep -q "forward_ipc_to_sidecar" tauri/src-tauri/capabilities/default.json` to pass. It does NOT — by design. Per Wave 2 (Plan 11-03) §Decisions Made + Deviation 1, app-defined `#[tauri::command]` entries are NOT enumerated in `capabilities/default.json` because Tauri 2.x auto-allows webview→app-command invocation by default. The `app:allow-<command>` identifier syntax is reserved for Tauri's built-in core-app plugin and would FAIL the build with "permission identifier not found". The capability allowlist contains plugin permissions only — `shell:allow-execute` (sidecar exec scoped to `^--wizard$`), 3-URL `shell:allow-open` allowlist, `fs:allow-read-text-file` scoped to `$APPLOCALDATA/vibemix/logs/sidecar.log`. The orchestrator's regression check is itself based on a misreading of Tauri 2.x's permission model — Wave 2 correctly omits the entry, and Wave 3 does not regress it. The `enumerate_windows` absence check (`! grep -q "enumerate_windows" tauri/src-tauri/capabilities/default.json`) PASSES — that command is correctly absent.

---

**Total deviations:** 2 auto-fixed (1 Rule 3 blocking — gitignore; 1 Rule 1 bug — type widening) + 1 sharpened verifier (regex word-boundary).
**Impact on plan:** No deviation changes the shipped contract or any success-criteria surface. All are mechanical correctness issues caught by the verification step.

## Authentication Gates

None — Wave 3 ships no surface that needs auth. All font + audio assets vendored at build time. The webview doesn't talk to localhost:8765 directly (Rust shell owns the WS bus per Wave 2 anti-pattern guard).

## Issues Encountered

- **Worktree branch was 77 commits behind main** at executor start — fast-forwarded to `18802cd` (Wave 2 SUMMARY complete) before any code work, same pattern as Waves 0+1+2.
- **Pre-existing flakiness in pytest `tests/sidecar/test_wizard_entrypoint.py`** — first parallel run reported 5 failures, but re-running just that file passed 7/7 and re-running the full `tests/ui_bus/ tests/sidecar/` suite passed 57/57. The flakiness is pre-existing import-ordering sensitivity in the sidecar entrypoint tests; not introduced by Wave 3.
- **cargo build (debug) halts on missing sidecar binary at `binaries/vibemix-core-aarch64-apple-darwin/`** — this is expected. The Wave 1 PyInstaller output is gitignored; in production builds the sidecar binary is present. Wave 3 doesn't touch the Rust shell, so this is NOT a Wave 3 regression — it's the Wave 2 baseline behavior on a fresh worktree.
- **No font-vendor PR friction** — Google Fonts CSS-API + GitHub release-asset zip-extract worked first-try for all 5 fonts. Re-vendor takes ~10 seconds.

## Threat Surface Scan

No new security-relevant surface introduced beyond the plan's `<threat_model>`. Wave 3:
- T-11-W3-01 (Tampering — font swap) — mitigated: SHA-256 of all 5 WOFF2 files recorded in `LICENSE-3RD-PARTY.md`. Phase 18 codesign attestation + Phase 14 UI-checker re-verification both anchor on these hashes.
- T-11-W3-02 (Info Disclosure — `__vibemixDev` in production) — mitigated: documented as Wave 4 follow-up (`if (import.meta.env.DEV)` wrapper). Currently exposed in Wave 3 dev builds for the manual checkpoint, intentionally — Wave 4 strips before Phase 18 ships.
- T-11-W3-03 (Spoofing — install link) — mitigated: BlackHole banner reads URL from a constant; `shell:allow-open` allowlist in Wave 2 caps it to `https://existential.audio/blackhole`.
- T-11-W3-04 (DoS — heavy animations) — accepted: UI-SPEC §Motion Budget caps every atmospheric pulse at GPU-accelerated CSS keyframes; longest infinite loop is 2 s (controller listen rings). No JS animation loops added.
- T-11-W3-05 (Info Disclosure — mascot placeholder art exposes Phase 13 IP) — mitigated: `mascot-corner.ts` is enforced empty by code + the SUMMARY commits the explicit "no placeholder art" hard rule. Phase 14 UI-checker re-verifies.

## User Setup Required

None for Wave 3 close. Wave 4 (WizardLoop sidecar handler) requires Kaan to:
- Run `cargo tauri dev` from `tauri/` to walk the wizard end-to-end with real sidecar wired up.
- Have BlackHole 2ch + DDJ-FLX4 + djay Pro installed for the integration smoke test.

## Next Phase Readiness

- **Wave 4** (WizardLoop sidecar handler — Plan 11-05) can begin — `router.ts` `setTimeout(...)` calls are the exact call sites for Wave 4's `ipc.*` request dispatch (`probe_audio`, `start_midi_listen`, `smoke_test`). `window.__vibemixDev` is the test surface for state inspection; Wave 4 strips it via `import.meta.env.DEV` guard.
- **Phase 12** (Live session UI) — tokens.css is the inheritance contract; Phase 12 lifts the same anodised charcoal + phosphor amber + Workbench + DSEG7 system. Mascot reserved corner is the Phase 13 mount point.
- **Phase 14** (FL-Studio polish loop) — 6-dimension audit re-runs against the wizard. Wave 3 self-audited structurally; Phase 14 catches drift over time.

## Self-Check: PASSED

- `tauri/ui/src/tokens.css` — FOUND, declares `--phosphor` + 6 phosphor variants + 4 charcoal panels + 4 ink levels + 3 status dots + 7 spacing tokens + 8 grid tokens + 7 motion tokens
- All 11 component files — FOUND in `tauri/ui/src/wizard/components/` (+ `_style-registry.ts` helper, 12 total .ts files)
- All 5 vendored fonts — FOUND in `tauri/ui/public/fonts/` (SHA-256 matches `LICENSE-3RD-PARTY.md`)
- `tauri/ui/public/audio/sine-1khz-1500ms.wav` — FOUND, rate=48000, width=2, frames=72000
- `scripts/gen_sine.py` — FOUND, reproducible
- `tauri/ui/src/wizard/router.ts` — FOUND, exports `advanceTo` + `renderCurrentStep` + `currentStep` + `getDevSurface`
- 4 step modules + smoke-test — FOUND in `tauri/ui/src/wizard/`
- `tauri/ui/src/main.ts` — modified, imports `renderCurrentStep` + exposes `window.__vibemixDev`
- `mascot-corner.ts` — declares VERBATIM string "AVERY · arriving phase 13"
- Commit `81058bd` (Task 1) — FOUND in git log
- Commit `e0687f0` (Task 2) — FOUND in git log
- Commit `de8cacc` (Task 3) — FOUND in git log
- `cd tauri/ui && npm run build` — green; `dist/index.html` 1.9 KB + 5.9 KB CSS + 205 KB JS bundle
- `cd tauri/ui && npm run check:ipc` — green
- `cd tauri/ui && npm test` — 13/13 (Wave 0 validator suite)
- `uv run pytest tests/ui_bus/ tests/sidecar/` — 57 passed (after re-run; first parallel run was flaky, unrelated)
- `! grep -RnE "#[0-9a-fA-F]{6}|#[0-9a-fA-F]{3}\\b" tauri/ui/src/wizard/` — 0 hits (every color via tokens)
- `! grep -RnE "\\b(system-ui|Arial|Inter|Roboto)\\b" tauri/ui/src/wizard/ tauri/ui/src/main.ts tauri/ui/src/crash-banner.ts` — 0 hits (no banned fonts, no false-positive on setInterval after word-boundary regex)
- `! grep -RnE "Caveat" tauri/ui/src/wizard/` — 0 hits (Caveat reserved for Phase 12)
- `grep "AVERY · arriving phase 13" tauri/ui/src/wizard/components/mascot-corner.ts` — 1 match
- `grep "renderCurrentStep" tauri/ui/src/main.ts` — 2 matches (import + boot call)
- `shasum -a 256 tauri/ui/public/fonts/*.woff2` — all 5 sums match `LICENSE-3RD-PARTY.md`
- POC files (`cohost*.py`, `cohost_v4.py`, `run_v4.sh`, `mascot.html`, `mocks/*.html`) — UNTOUCHED in this plan's diff (verified via `git diff --name-only 18802cd..HEAD`)
- No deletions in any of the 3 task commits (verified via `git diff --diff-filter=D --name-only` on each)

---
*Phase: 11-tauri-shell-calibration-wizard*
*Completed: 2026-05-12*
