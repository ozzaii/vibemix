# Phase 14: CDJ Whisper v5 Migration + Polish — Research

**Researched:** 2026-05-13
**Domain:** UI design-system migration; visual-contract refactor; component-level token-consumer audit; font vendoring; backdrop-filter perf; pre-commit gate wiring
**Confidence:** HIGH (codebase grep is authoritative; design contract is locked; the remaining `[ASSUMED]` items are clearly tagged below)

---

## Summary

This is a **migration phase**, not a design phase. The visual contract is fully locked by `mocks/vibemix-direction-final.html` (CDJ Whisper v5) and codified into the per-surface migration contract in `14-UI-SPEC.md`. The v5 tokens already live in `tauri/ui/src/tokens.css` (commit `0615344`) behind a backward-compat shim that flips legacy `--phosphor*` / `--brushed-*` / `--bezel-*` / `--panel*` / `--groove` / `--ink*` / `--col-mascot` aliases onto v5 primitives via cascade. Phase 14 audits each component consumer so it reads v5 primitives directly, deletes the shim and the legacy `@font-face` block + 4 legacy WOFF2 files, vendors Saira (variable wdth + wght) + JetBrains Mono as WOFF2 (replacing the prototype `@import` from `fonts.googleapis.com`), wires a one-shot pre-commit grep gate for the shim-delete commit, and runs `gsd-ui-checker` + `gsd-ui-auditor` per surface with a 3-cycle iteration cap.

Codebase inventory (this research): **272 references** to shim/legacy tokens across **27 files** outside `tokens.css`. Surface distribution: **wizard 225 refs**, **session 25 refs**, **settings 16 refs**, **mascot 7 refs**, **crash-banner 0** (already retoned in Phase 11). Additionally: **325 hardcoded `rgba()` literals** across 27 component files, **58** of which are exact `rgba(255, 138, 61, *)` amber values that should consume `--amber-22/40/65` tokens; **6** are exact `rgba(214, 207, 199, *)` silk values that should consume `--silk-*`. **3 hardcoded hex literals** outside `tokens.css` — all in `tauri/ui/src/mascot/index.ts` (`#ffa12e`, `#efe6d6`, `#3d424c`) as fallback args to a `resolveCssColor()` lookup that itself reads stale `--phosphor*` token names.

Forbidden-font residue is significant: **21 refs** to `Workbench`, **33 refs** to `DM Mono`, **10 refs** to `DSEG7`, **3 refs** to `Caveat`. Most are font-family declarations in wizard components (`font-family: "Workbench", "Courier New", monospace;`) — the shim-delete commit cannot land until every one is replaced with `var(--type-display)` / `var(--type-mono)`. Purge-dictionary residue: **5 `brushed`**, **93 `phosphor`** (mostly token refs, but a handful in jsdoc copy), **22 `bezel`**, **2 `knurled`**, **1 `retro-futurist`**, **1 `tactile`**.

No existing pre-commit infrastructure (`.husky/`, `.git/hooks/` is samples-only, no root `package.json`). Existing CI-gate precedent is `scripts/check_ipc_schema.py` invoked as a standalone Python script — Phase 14 mirrors that pattern.

**Primary recommendation:** Adopt the four-wave surface order from `14-UI-SPEC.md` (wizard → session → settings → mascot) and treat the **final subtractive commit** as wave 5. Within each surface wave, audit consumers in file-size order (largest legacy-ref count first — surfaces the migration patterns early), and add the pre-commit grep gate as a single `scripts/check_v5_migration.sh` script wired to a project-local `.git/hooks/pre-commit` only on the shim-delete commit (not globally — every-commit overhead and false-positives would block unrelated work).

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Area 1 — Migration Sequencing**
- Surface-by-surface, one plan per surface (mirrors Phase 12 wave structure). Stable ui-checker baseline captured before moving to next surface.
- Order: **wizard → live session UI → settings drawer → mascot overlay frame**. Wizard first (smallest token surface, structural HTML only). Mascot last because Phase 13 just shipped the renderer and the Meshy material fix (commit `2b608b6`) just landed.
- Per surface: refactor consumers first (read v5 primitives directly), commit the surface as a refactor. Backward-compat shim is **not** touched until every surface is migrated. Final subtractive commit deletes the shim wholesale.
- POC files (`cohost*.py`, `cohost.streaming.py.bak`, `mascot.html`, `mocks/*`) are untouchable per "POC = reference, devour it". Only `tauri/ui/src/` is in scope.

**Area 2 — Shim Removal Surgery**
- One subtractive commit at end of phase deletes all backward-compat aliases. Single revert if regression slips through; clean diff for ui-checker pre/post.
- Pre-deletion grep gate (must return zero hits before the shim-delete commit lands): `grep -rnE '(--(phosphor|brushed-(hi|lo)|bezel-[123]|panel(-lift|-deep)?|groove|ink(-(dim|deep|engraved))?|charcoal|col-mascot))\b' tauri/ui/src/ --include='*.ts' --include='*.tsx' --include='*.css' --include='*.html'`. Wired into a pre-commit hook for the shim-delete commit only.
- `--col-mascot: 256px` is **deleted**. Wizard collapses to single-column per the inline TODO already in `tokens.css`. Mascot lives as an overlay window per Phase 13 — never embedded.
- Legacy @font-face declarations (Workbench, DM Mono, DSEG7, Caveat) removed once grep confirms zero string-keyed usages. The four WOFF2 files at `tauri/ui/public/fonts/` deleted. `tauri/ui/LICENSE-3RD-PARTY.md` updated to drop the four families and add Saira + JetBrains Mono SHA-256 attestations.
- Vendored Saira + JetBrains Mono as WOFF2 (replaces the prototype's remote `@import` from `fonts.googleapis.com`). One-click-install rule: offline-friendly distribution.

**Area 3 — Critique Loop Discipline**
- Iteration cap: **3 cycles** of `ui-checker → fix → ui-auditor` per surface. After 3, surface is logged as polish debt in the polish log and escalated to Kaan.
- Polish log: `.planning/phases/14-cdj-whisper-v5-migration-polish/14-POLISH-LOG.md`. Markdown table with `surface | cycle | ui-checker output ref | ui-auditor output ref | fix commit SHA | status`.
- Acceptance: numeric — `gsd-ui-checker` zero findings AND `gsd-ui-auditor` three audits green (20/80 dominance, no-faux-3D-bevel, typography pairing) AND side-by-side screenshot pair attached to plan summary.
- Backdrop-filter perf fallback shipped now, not deferred to Phase 16: `--blur-glass-perf` token alias; `@media (prefers-reduced-motion: reduce)` override; runtime toggle Settings → Performance → "Lighter blur" writing `data-blur-perf="on"` on `<html>`; tested on Kaan's M-series Mac and a Windows non-dev machine before Phase 14 closes.

**Area 4 — Copy Purge + Typeface Reconciliation**
- Scrub scope: chrome strings only — text rendered in `tauri/ui/src/{wizard,session,settings,mascot}/`. Excludes: code comments, console logs, error messages, planning docs, prompt templates, Gemini transcript content.
- Purge dictionary (case-insensitive grep gate on `tauri/ui/src/**/*.{ts,tsx}` string literals): `brushed`, `anodised`, `phosphor`, `retro-futurist`, `knob/fader physics`, `tactile` (manual review only).
- Voice: Pioneer-grade restraint. State words over sentences.
- **Typeface decision (overrides ROADMAP success criterion #4):** Saira (variable wdth + wght) + JetBrains Mono. ROADMAP "Geist + Fraunces" is stale; mock wins. ROADMAP success-criterion text updated in this phase's first plan.

### Claude's Discretion
- Animation timing for the slow amber border sweep — `--motion-border-sweep: 22s` default; component plans may adjust per-surface if perceptual review flags it.
- Z-index layering of the animated border within each glass panel — first child, position absolute, inset 0; component plans pick the masking technique that survives existing layout.
- Per-surface micro-decisions (hover states, focus ring intensity, etc.) at executor's discretion provided they consume v5 primitives only.

### Deferred Ideas (OUT OF SCOPE)
- Performance profiling deep-dive — Phase 14 ships the `--blur-glass-perf` fallback toggle; per-machine perf characterization (FPS during 60-min session) is Phase 16.
- Mascot mood-specific glass tinting — not part of v5 contract; deferred to future polish pass.
- Animated-border per-surface variation — every panel gets same 22s sweep in v5.
- Settings → Performance panel beyond "Lighter blur" — only that one toggle is shipped this phase.
- Dark/light mode — v5 is intentionally one-mode.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| POLISH-01 | Dedicated polish phase — critique → execute loop against CDJ Whisper v5 contract | Loop discipline locked in CONTEXT Area 3; 3-cycle cap + polish log table schema; `gsd-ui-checker` + `gsd-ui-auditor` are the binary gates |
| POLISH-02 | Backward-compat shim removed; components reference v5 primitives directly (`--void-*` / `--glass-*` / `--silk-*` / `--amber*` / `--rave-*` / `--glow-*`) | Codebase Consumer Inventory below enumerates all 272 refs across 27 files; per-token migration map already in `14-UI-SPEC.md` Shim Removal Surgery table |
| POLISH-03 | Mascot overlay (Phase 13) renders inside v5 chrome with animated-border sweep on its frame; mood swap visibly composes with palette | Mascot surface is wave 4 in this phase; chrome amber stays identical across moods (CONTEXT Area 3); `.border-anim.slow.rev` modifier already defined in `tokens.css:330–331` |
| POLISH-04 | No FL-Studio tactile residue + no web-app residue (no bezels/brushed-metal, no Tailwind defaults, Saira + JetBrains Mono only — **NOT** Geist + Fraunces per typeface reconciliation) | Purge dictionary scan: 5 `brushed`, 22 `bezel`, 2 `knurled`, 1 `retro-futurist`, 1 `tactile`; forbidden-font scan: 21 Workbench, 33 DM Mono, 10 DSEG7, 3 Caveat refs need migration. ROADMAP text updated in Plan 14-01. |
| POLISH-05 | All copy passes "no AI slop" filter + FL-Studio vocabulary purged from chrome | Purge dictionary grep gate; copy table from `14-UI-SPEC.md` Copywriting Contract is the source of truth |
| POLISH-06 | `gsd-ui-checker` + `gsd-ui-auditor` green against CDJ Whisper baseline before phase completes; backdrop-filter perf verified on non-dev machine | Per-surface acceptance gates already itemized in `14-UI-SPEC.md`; perf measurement procedure documented in this RESEARCH §Backdrop-filter Performance Measurement below |
</phase_requirements>

---

## Project Constraints (from CLAUDE.md)

- **`tauri/ui/src/tokens.css` is the only file allowed to contain `#xxxxxx` literals.** Components consume `var(--token)` exclusively. (Already an established invariant from Phase 11 W3.) [VERIFIED: codebase grep — 3 hex literals outside tokens.css, all in `mascot/index.ts:403,407,410` as `resolveCssColor()` fallback args]
- **POC files (`cohost*.py`, `cohost.streaming.py.bak`, `mascot.html`, `mocks/*`) are untouchable.** Reference only — these are "trusted intuition to port wholesale, not legacy to preserve." Phase 14 lives entirely in `tauri/ui/src/`. [CITED: CLAUDE.md "POC = Reference, Devour It"]
- **One-click install hard requirement.** Every dep choice rated green/yellow/red on install impact. Implies: no remote `@import` for fonts in production — vendored WOFF2 only. [CITED: CLAUDE.md memory anchor `project_one_click_install_hard_req`]
- **`frontend-enforcement` skill auto-loads on UI-touching agents** — but **CDJ Whisper v5 wins** when in conflict (HANDOFF watchout #3; CONTEXT typeface reconciliation; project-local memory `project_visual_direction_cdj_whisper`). Skill's "knurled-knob shadows / segment-LED numerals / brushed aluminum" vocabulary is FL-Studio-era and superseded. Typography audit reinterpreted to enforce Saira + JetBrains Mono. [VERIFIED: read `.claude/skills/frontend-enforcement/SKILL.md` + CONTEXT.md Area 4]
- **No CLAP / no multi-provider AI / no scope creep.** Not directly relevant to Phase 14 (visual-only), but means: no new build-tools / no new font-loader libs / no CSS-in-JS framework. Stay vanilla TS + `registerStyle()` singleton. [CITED: CLAUDE.md memory anchors]
- **Bundle id `world.bravoh.vibemix` is LOCKED.** Not touched by Phase 14, but any Tauri config touched (overlay window) must preserve. [CITED: STATE.md Phase 11 W1 lock]

---

## Architectural Responsibility Map

This phase is **client-only**. No backend, no API, no IPC schema changes. Every capability lives in the browser/webview tier.

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|--------------|----------------|-----------|
| Design-token consumption (CSS custom property reads) | Browser (Tauri webview) | — | `var(--token)` lookups happen at paint time in WebView2 / WKWebView |
| Animated border (conic-gradient + mask-composite) | Browser | — | Pure CSS animation on GPU compositor; no Rust/Python involvement |
| Font loading (`@font-face` WOFF2) | Browser | — | Vite serves `tauri/ui/public/fonts/*.woff2` as static assets; Tauri's asset protocol picks them up |
| Backdrop-filter blur fallback toggle | Browser (CSS) + small Settings IPC | — | CSS reads `html[data-blur-perf]` attribute; Settings drawer toggle writes via `SettingsApplier` (existing Phase 12 IPC `settings.set`) |
| Pre-commit grep gate | Build-tooling (developer workstation, not runtime) | — | Shell script invoked by `.git/hooks/pre-commit`; ONE-SHOT for the shim-delete commit only |
| Animated border on mascot overlay window | Browser (Tauri overlay window's webview chrome) | — | Phase 13 Three.js canvas is transparent; v5 border lives on the wrapper div |

---

## Codebase Consumer Inventory (the authoritative numbers)

> **Method:** `grep -rn -E -- '--(phosphor|brushed-|bezel-|panel-(lift|deep|hover|pressed)|groove|ink-(dim|deep|engraved)|col-mascot|crash-grad|sp-(xs|sm|md|lg|xl|2xl|3xl))' tauri/ui/src/ --include='*.ts' --include='*.css' --include='*.html' | grep -v tokens.css`
> **Date:** 2026-05-13. Numbers will shift as the surface migrations land; planner consumes the per-file/per-surface delta to scope each surface plan.

### Per-surface aggregate

| Surface | Files w/ legacy refs | Legacy token refs (shim-keyed) | Hardcoded amber rgba | Hardcoded silk rgba | Forbidden font-family refs |
|---------|----------------------|--------------------------------|----------------------|---------------------|----------------------------|
| **Wizard** (`tauri/ui/src/wizard/**`) | 15 | **225** | ~28 | ~4 | Workbench × 18, DM Mono × 23, DSEG7 × 4, Caveat × 0 |
| **Session** (`tauri/ui/src/session/**`) | 6 | **25** | ~24 | ~2 | Workbench × 0, DM Mono × 4, DSEG7 × 5, Caveat × 3 |
| **Settings** (`tauri/ui/src/settings/**`) | 5 | **15** | ~5 | ~0 | Workbench × 1, DM Mono × 4, DSEG7 × 1, Caveat × 0 |
| **Mascot** (`tauri/ui/src/mascot/**`) | 1 | **6** | ~1 | ~0 | Workbench × 0, DM Mono × 0, DSEG7 × 0, Caveat × 0 |
| **Root files** (crash-banner.ts, main.ts) | 0 | **0** | ~0 | ~0 | 0 — crash-banner already retoned in Phase 11 |
| **TOTAL** | 27 | **272** | ~58 | ~6 | 21 + 33 + 10 + 3 = **67** |

### Wizard surface — per-file map (sorted by ref count)

| File | Legacy-token refs | Notes |
|------|-------------------|-------|
| `wizard/components/window-picker.ts` | 37 | Largest; list-row hover backgrounds + selected row + 5 `--panel*` refs |
| `wizard/components/dropdown-device.ts` | 31 | 11 `--phosphor*`, 5 `--ink*`, 4 `--panel*` — selected device row + AUTO pill |
| `wizard/components/controller-probe.ts` | 31 | DSEG7 48px countdown + 4 expanding rings + 7 `--ink*` |
| `wizard/components/audio-test-button.ts` | 30 | 4-ring concentric pulse + DSEG7 readout |
| `wizard/components/blackhole-banner.ts` | 18 | 7 `--phosphor*` (halo!), 3 `--ink*`, 2 `--panel*` |
| `wizard/components/status-bar.ts` | 17 | 4 `--phosphor*` LED pulse + 6 `--ink*` |
| `wizard/components/permissions-card.ts` | 17 | OS-aware permissions list; 3 `--ink*` |
| `wizard/smoke-test.ts` | 16 | "WIZARD COMPLETE" heading + success badge pulse |
| `wizard/step1-permissions.ts` | 7 | View-level styles; 2 `--phosphor*` |
| `wizard/components/step-indicator.ts` | 7 | Step strip dots + 3 `--phosphor*` |
| `wizard/components/mascot-corner.ts` | 6 | **TO DELETE** — 256×256 reserved corner gone in v5 |
| `wizard/components/primary-panel.ts` | 3 | 1 `--phosphor*` + 1 `--panel*` |
| `wizard/controllers/ddj-flx4.svg.ts` | 2 | 2 `--phosphor*` in SVG fill |
| `wizard/icons/speaker.svg.ts` | 1 | 1 `--ink*` |
| `wizard/icons/shield.svg.ts` | 1 | 1 `--ink*` |
| `wizard/components/button.ts` | 1 | Already mostly v5-compliant from earlier W3 work |

### Session surface — per-file map

| File | Legacy-token refs | Notes |
|------|-------------------|-------|
| `session/SessionLayout.ts` | 8 | Root composer; mostly `--sp-*` aliases + `--panel*` |
| `session/components/titlebar.ts` | 7 | DSEG7 22px clock + brand bullet area |
| `session/components/meter.ts` | 4 | 2 `--phosphor*`, 1 `--panel*`, 1 `--ink*` — meter cluster |
| `session/components/drop-chip.ts` | 3 | Countdown chip variant |
| `session/components/rocker.ts` | 2 | Mood pill toggle |
| `session/components/panel.ts` | 1 | Root panel utility |

### Settings surface — per-file map

| File | Legacy-token refs | Notes |
|------|-------------------|-------|
| `settings/SettingsDrawer.ts` | 5 | Drawer slide-over root |
| `settings/components/retention-slider.ts` | 4 | 3 `--phosphor*`, 1 `--panel*` — knurled retention discs need recess re-treatment |
| `settings/components/mascot-group.ts` | 4 | 1 `--phosphor*`, 1 `--ink*` + jsdoc copy purge |
| `settings/components/hotkey-capture.ts` | 3 | 2 `--phosphor*` pulse state |

### Mascot surface — per-file map

| File | Legacy-token refs | Notes |
|------|-------------------|-------|
| `mascot/index.ts` | 6 | 4 `--phosphor*`, 2 `--ink*`. Also contains 3 hardcoded hex literals on lines 403/407/410 |

### Hardcoded hex audit (outside `tokens.css`)

Only **3 hits**, all in `tauri/ui/src/mascot/index.ts`:

```ts
376:  // (#ffa12e) from tokens.css — duplicated here only as a literal-string  ← STALE; v5 is #ff8a3d
403:  color = resolveCssColor("--phosphor", "#ffa12e");                      ← rename token + update fallback
407:  color = resolveCssColor("--phosphor-soft", "#efe6d6");                 ← rename token + update fallback
410:  color = resolveCssColor("--ink-deep", "#3d424c");                      ← rename token + update fallback
```

**Mitigation:** rename the three CSS custom-property keys in `resolveCssColor()` calls (`--phosphor` → `--amber`, `--phosphor-soft` → `--amber-22`, `--ink-deep` → `--silk-40`) AND update the fallback hex string to match the v5 value (`#ff8a3d`, `rgba(255,138,61,0.22)` — but `resolveCssColor` returns a CSS color string, so use `#ff8a3d`, an approximation `#ff8a3d40` for amber-22 won't parse for Three.js — verify by reading `resolveCssColor()` implementation in Plan 14-04). Update the line 376 comment to remove the stale `#ffa12e` reference.

### Hardcoded rgba audit

**325 total** `rgba(...)` literal calls outside `tokens.css`. Top offenders by file:

| File | rgba count | Migration mode |
|------|------------|----------------|
| `wizard/components/button.ts` | 29 | Many are `rgba(255, 138, 61, *)` amber → migrate to `--amber-22/40/65`; `rgba(0,0,0,*)` inset shadows stay inline (mock-verbatim) |
| `session/components/status-bar.ts` | 26 | Mix of `rgba(0,0,0,*)` + `rgba(214,207,199,*)` silk → migrate silk to tokens |
| `settings/components/confirm-dialog.ts` | 23 | Mostly `rgba(0,0,0,*)` modal backdrop; verify against mock §dialog |
| `session/components/cohost.ts` | 23 | AI-transcript ring — migrate `rgba(255,138,61,*)` to `--amber-*` |
| `settings/components/hotkey-capture.ts` | 21 | Pulse state amber rgba → tokens |
| `session/components/phase-tape.ts` | 18 | Segment fills — migrate silk + amber rgba |
| `settings/components/retention-slider.ts` | 17 | Track + knurled disc shadows |
| `session/components/picker.ts` | 16 | List row hover/selected |
| `session/components/titlebar.ts` | 15 | Mostly shadows; verify against mock §top-strip |

**Hard rule for migration:** `rgba(255, 138, 61, X)` with alpha ∈ {0.22, 0.40, 0.65} **MUST** consume `--amber-22/40/65` tokens. Other alphas stay inline ONLY if mock-verbatim (e.g., `rgba(255, 138, 61, 0.09)` button hover-top gradient stop). Same rule for `rgba(214, 207, 199, X)` ↔ `--silk-{65,40,22,12}`.

### Inline-style audit (TS template strings, `style={...}` props)

Project pattern is `registerStyle()` singleton — components inject CSS via `<style>` blocks, not inline `style=` props. **No `style={...}` inline JSX-style usage detected** (this isn't React; vanilla TS with `HTMLElement.style` would surface differently).

Direct `element.style.setProperty(...)` calls do exist for CSS-variable hot updates (e.g., `render-loop.ts` updates `--m-low-fill` per-frame). These are **dynamic and out-of-scope** for token migration — they read from `SessionState` and don't reference legacy tokens by name. Verified: `grep -rn 'style.setProperty' tauri/ui/src/ | wc -l` → small set, all dynamic CSS-var writes, none target legacy token names. No action required.

### Purge-dictionary residue

Case-insensitive grep in `tauri/ui/src/**/*.{ts,tsx}` chrome strings:

| Term | Hits | Where | Action |
|------|------|-------|--------|
| `brushed` | 5 | jsdoc comments + 1 string in `primary-panel.ts` ("brushed-metal `::before` streak") | Replace jsdoc copy; replace string with `.vmx-glass-streak` utility |
| `anodised` | 0 | — | None |
| `phosphor` | 93 | mostly token refs (`--phosphor*`) — already counted above; a few in jsdoc copy | Token refs handled by shim removal; jsdoc copy rewritten |
| `retro-futurist` | 1 | 1 jsdoc comment | Delete |
| `knurled` | 2 | jsdoc copy in `retention-slider.ts` + 1 elsewhere | Rewrite as "recessed discs" or similar |
| `tactile` | 1 | 1 string — manual review required (may be genuine UI behavior) | Manual review per CONTEXT Area 4 |
| `bezel` | 22 | mostly token refs (`--bezel-*`); a handful in jsdoc copy | Token refs handled by shim removal; jsdoc copy rewritten |

### Forbidden-font residue

| Font | Hits | Where | Action |
|------|------|-------|--------|
| Workbench | 21 | font-family declarations in 6 wizard components + jsdoc | Replace `font-family: "Workbench", ...` with `font-family: var(--type-display); font-variation-settings: "wdth" 85, "wght" 700;` |
| DM Mono | 33 | font-family declarations in 8+ files + jsdoc | Replace `font-family: "DM Mono", monospace;` with `font-family: var(--type-mono);` (JetBrains Mono via `--type-mono`) |
| DSEG7 | 10 | font-family in `controller-probe.ts`, `audio-test-button.ts`, `retention-slider.ts`, `SessionLayout.ts`, `titlebar.ts`, `cohost.ts` jsdoc | Replace with `font-family: var(--type-mono); font-variant-numeric: tabular-nums;` — JetBrains Mono with tabular-nums replaces DSEG7's 7-seg LCD look |
| Caveat | 3 | `phase-tape.ts` jsdoc + `status-bar.ts` jsdoc + 1 in-line ref | Delete refs entirely — v5 doesn't use sticker/handwritten labels |

**Critical:** the shim-delete grep gate must include forbidden-font checks. Phase 14 needs to verify NOT just zero `--phosphor*` refs but also zero `Workbench` / `DM Mono` / `DSEG7` / `Caveat` font-family declarations remain outside `tokens.css` (the legacy `@font-face` block in `tokens.css:38–76` is itself deleted in the shim-delete commit).

---

## Standard Stack

This phase introduces **no new runtime dependencies**. Stack is verified-current against existing `tauri/ui/package.json`:

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| TypeScript | ^5.7 | All `*.ts` component files | Already pinned [VERIFIED: `tauri/ui/package.json:30`] |
| Vite | ^6.0 | Dev server + production bundler; serves `public/fonts/*.woff2` as static assets | Already pinned; serves static fonts correctly via `vite-plugin-static-copy` [VERIFIED: `tauri/ui/package.json:31`] |
| Vitest | ^2.1 | Test framework; jsdom env for DOM-touching specs | Already pinned [VERIFIED: `tauri/ui/vitest.config.ts`] |
| jsdom | ^29.1.1 | DOM env for component vitest specs | Already pinned |

### Supporting (unchanged)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `@tauri-apps/api` | ^2.11 | IPC bridge to Rust for Settings perf toggle | Already used in Phase 12 settings drawer |
| `ajv` / `ajv-formats` | ^8.20 / ^3.0 | IPC schema validation | Existing; no new IPC schema in Phase 14 |
| `three` | ^0.170.0 | Mascot scene | Existing; not touched by Phase 14 chrome work |

### NEW dependencies introduced

**None.** Font vendoring is two new files in `tauri/ui/public/fonts/` (Saira variable + JetBrains Mono) + LICENSE-3RD-PARTY.md updates. No `npm install` required.

**Version verification:**
- `npx vite --version` → 6.x (current) [VERIFIED: package.json]
- `npx vitest --version` → 2.x (current) [VERIFIED: package.json]
- Saira variable WOFF2 — fetched at vendoring time; SHA pinned in LICENSE-3RD-PARTY.md
- JetBrains Mono — fetched at vendoring time; SHA pinned

### Alternatives Considered (and rejected per locked decisions)

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `registerStyle()` singleton | CSS-in-JS lib (emotion, styled-components) | **Rejected.** Adds runtime + bundle weight; project pattern is vanilla TS + `<style>` injection. Phase 11 W3 invariant. |
| Vendored WOFF2 | `@import` from Google Fonts (prototype-only) | **Rejected.** Hard requirement: one-click install + offline-friendly. Phase 14 deletes the `@import` line. |
| Husky pre-commit framework | Manual `.git/hooks/pre-commit` shell script | **Recommendation:** manual script. Adds no new dep. Husky requires `npm install` + root `package.json`, which doesn't currently exist. Single-purpose shim-delete-only hook doesn't need framework. |
| New font (Inter / Geist / Fraunces) | Saira + JetBrains Mono | **Rejected.** ROADMAP "Geist + Fraunces" is stale per typeface reconciliation; mock wins. |

**Installation (vendoring only — no npm change):**

```bash
# Saira variable (wght + wdth) — download from Google Fonts > Selected family > Get embed code > download files
# Or via Fontsource: https://fontsource.org/fonts/saira (variable WOFF2 included)
# Place at: tauri/ui/public/fonts/Saira-VariableFont_wdth,wght.woff2

# JetBrains Mono — download from https://github.com/JetBrains/JetBrainsMono/releases
# Or via Fontsource: https://fontsource.org/fonts/jetbrains-mono
# Place at: tauri/ui/public/fonts/JetBrainsMono-Regular.woff2
#          tauri/ui/public/fonts/JetBrainsMono-Medium.woff2
#          tauri/ui/public/fonts/JetBrainsMono-SemiBold.woff2
```

---

## Architecture Patterns

### System Architecture Diagram

```
                ┌─────────────────────────────────────────────────────────────┐
                │  mocks/vibemix-direction-final.html  (v5 visual contract)   │  ← reference, not code
                └─────────────────────────────────────────────────────────────┘
                                              │
                                              │ (per-surface side-by-side compare)
                                              ▼
   ┌──────────────────────────────────────────────────────────────────────────────┐
   │  tauri/ui/src/tokens.css   ← single CSS source-of-truth + backward-compat    │
   │  ─────────────────────────                                                   │
   │  · v5 primitives: --void-* / --glass-* / --silk-* / --amber* / --rave-* /    │
   │     --glow-* / --type-* / --sp-1..8 / --rad-* / --motion-border-sweep        │
   │  · @font-face: Saira variable + JetBrains Mono (WOFF2, vendored)             │
   │  · .border-anim utility (conic-gradient + mask-composite + 22s sweep)        │
   │  · body radial-gradient stack + film-grain ::before                          │
   │  · :root[data-blur-perf="on"] override + prefers-reduced-motion media query  │
   │  · backward-compat SHIM ← DELETED in final wave (the migration's last act)   │
   └──────────────────────────────────────────────────────────────────────────────┘
                                              │
                                              │ (CSS cascade — components read var())
                                              ▼
   ┌──────────────────────────────────────────────────────────────────────────────┐
   │  Per-surface migration (4 waves, surface-by-surface)                          │
   │                                                                                │
   │  Wave 1 — Wizard       Wave 2 — Session       Wave 3 — Settings   Wave 4 —    │
   │  (225 refs)            (25 refs)              (15 refs)           Mascot      │
   │  16 component files    13 component files     8 component files   (6 refs)    │
   │  + step views          + SessionLayout root   + SettingsDrawer    + index.ts  │
   │                                                                                │
   │  Each wave:                                                                    │
   │    1. Per-file: replace legacy shim refs with v5 primitives                   │
   │    2. Add <div class="border-anim"> as first child of surface glass panel    │
   │    3. Replace Workbench/DM Mono/DSEG7/Caveat font-family with                  │
   │       var(--type-display) + font-variation-settings  OR  var(--type-mono)     │
   │    4. Replace rgba(255,138,61,*) hardcoded literals with --amber-* tokens     │
   │    5. Replace rgba(214,207,199,*) literals with --silk-* tokens               │
   │    6. Run gsd-ui-checker → fix → gsd-ui-auditor (3-cycle cap per surface)     │
   │    7. Side-by-side screenshot pair vs. mock §{surface}                        │
   │    8. Commit surface wave; advance polish log row                              │
   └──────────────────────────────────────────────────────────────────────────────┘
                                              │
                                              │ (after all 4 surfaces green)
                                              ▼
   ┌──────────────────────────────────────────────────────────────────────────────┐
   │  Wave 5 — Subtractive commit (the shim-delete commit)                         │
   │                                                                                │
   │  · scripts/check_v5_migration.sh runs as pre-commit hook for THIS commit only │
   │  · Hook asserts zero legacy-token refs + zero forbidden-font refs              │
   │  · tokens.css: DELETE shim block (lines 175–231), DELETE legacy @font-face    │
   │    block (lines 38–76), REPLACE @import line 35 with @font-face Saira + JBM   │
   │  · DELETE 4 legacy WOFF2 files at tauri/ui/public/fonts/                       │
   │  · UPDATE tauri/ui/LICENSE-3RD-PARTY.md (drop 4, add Saira + JBM SHAs)         │
   │  · ADD Settings → Performance group with "Lighter blur" toggle (new IPC)      │
   │  · One commit; one revert undoes it if regression sneaks in                    │
   └──────────────────────────────────────────────────────────────────────────────┘
```

### Recommended Project Structure (unchanged)

```
tauri/ui/src/
├── tokens.css           ← migrated + shim deleted in wave 5
├── crash-banner.ts      ← unchanged (already v5-retoned in Phase 11)
├── main.ts              ← unchanged
├── ipc/                 ← unchanged (Phase 14 = pure presentation)
├── wizard/              ← wave 1
├── session/             ← wave 2
├── settings/            ← wave 3 (+ new performance-group.ts)
└── mascot/              ← wave 4 (chrome only — Three.js untouched)

tauri/ui/public/fonts/
├── Saira-VariableFont_wdth,wght.woff2    ← NEW (vendored in wave 5)
├── JetBrainsMono-Regular.woff2           ← NEW
├── JetBrainsMono-Medium.woff2            ← NEW
├── JetBrainsMono-SemiBold.woff2          ← NEW
├── Workbench-Regular.woff2               ← DELETE in wave 5
├── DMMono-Regular.woff2                  ← DELETE
├── DMMono-Medium.woff2                   ← DELETE
├── DSEG7Classic-Bold.woff2               ← DELETE
└── Caveat-Bold.woff2                     ← DELETE

scripts/
├── check_v5_migration.sh                 ← NEW (the pre-commit gate)
└── check_ipc_schema.py                   ← unchanged (existing precedent)
```

### Pattern 1: Surface-by-surface refactor, then subtractive

**What:** Migrate every consumer to v5 primitives *while the shim still flips legacy refs through the cascade*. Only delete the shim once consumer refs hit zero.

**When to use:** Always for this phase. Migration mechanic safety net.

**Why:** Lets each component refactor land as its own commit + ui-checker cycle, without risking a global break from premature shim deletion. The grep gate at the shim-delete commit catches anything missed.

### Pattern 2: `<div class="border-anim">` as first child + parent invariants

**Required parent rules:**
- `position: relative` AND `overflow: hidden`
- Component content at `z-index: 1+` (border-anim is `z-index: 4` per tokens.css:326)

**Modifier vocabulary:**
- `.slow` → 32s sweep (use on secondary/recessed surfaces)
- `.rev` → reverse direction (pair with `.slow` on mascot overlay so primary session + mascot don't sync)

**Example (verified against tokens.css:302–331):**

```html
<!-- Source: mocks/vibemix-direction-final.html §01 .session pattern -->
<div class="session-panel" style="position: relative; overflow: hidden;">
  <div class="border-anim"></div>
  <!-- component content at z-index 1+ here -->
</div>
```

**Mascot overlay variant:**

```html
<div class="mascot-window">
  <div class="border-anim slow rev"></div>  <!-- 32s reverse so it doesn't sync with session -->
  <canvas><!-- Three.js scene --></canvas>
</div>
```

### Pattern 3: Saira variable-axis usage

Single Saira font family flexes across all chrome text roles via `wdth` + `wght` axes. JetBrains Mono is the mono companion (numerics, `tabular-nums`).

**Lifted verbatim from `mocks/vibemix-direction-final.html:1389–1402` (source of truth):**

| Role | Family | Size | `wdth` | `wght` | Case | Tracking |
|------|--------|------|--------|--------|------|----------|
| Body | Saira | 14px | 100 | 400 | sentence | 0 |
| Silkscreen label | Saira | 9–10px | 85–90 | 500 | UPPERCASE | 0.18em–0.22em |
| Mid headline | Saira | 18–22px | 85–100 | 500–600 | UPPERCASE | -0.01em to 0 |
| Headline (section) | Saira | 24px | 85 | 600 | UPPERCASE | 0 |
| Display (hero) | Saira | 64–80px | 82 | 700–800 | UPPERCASE | -0.025em |
| Numeric data | JetBrains Mono | 11–64px | n/a | 400–500 | sentence | 0 to -0.04em |
| Sub-title (run-on) | Saira | 18px | 100 | 400 | sentence | 0.02em |

**CSS application pattern (replaces Workbench / DM Mono / DSEG7):**

```css
/* WAS (Phase 11): */
.btn-label {
  font-family: "Workbench", "Courier New", monospace;
  font-size: 11px;
  letter-spacing: 0.22em;
  text-transform: uppercase;
}

/* IS (Phase 14): */
.btn-label {
  font-family: var(--type-display);
  font-variation-settings: "wdth" 85, "wght" 700;
  font-size: 10px;          /* mock-verbatim; was 11px */
  letter-spacing: 0.22em;
  text-transform: uppercase;
}

/* WAS (Phase 11): */
.dseg-readout {
  font-family: "DSEG7", "DM Mono", monospace;
  font-size: 48px;
}

/* IS (Phase 14): */
.numeric-readout {
  font-family: var(--type-mono);                     /* JetBrains Mono */
  font-feature-settings: "tnum";                     /* tabular-nums */
  font-variant-numeric: tabular-nums;                /* belt + braces */
  font-size: 48px;
}
```

### Anti-Patterns to Avoid

- **Hardcoded `rgba(255, 138, 61, X)` outside `tokens.css`.** Replace with `--amber-22/40/65` when alpha matches. If alpha is mock-verbatim (e.g., 0.09 button hover) keep inline and add `/* mock-verbatim */` comment.
- **3D bevels via bright-top + dark-bottom solid box-shadow pairs.** v5 depth is glass (`inset 0 1px 0 var(--glass-top)` + drop shadow), not skeuomorphic metal.
- **Deleting the shim before consumer refs hit zero.** Will produce a cascade break across every component still keyed to legacy aliases. The pre-commit gate prevents this.
- **Nested `.border-anim` instances in the same visible region.** Drawer + session beneath is fine (drawer occludes); two sweeps on the same panel is wrong.
- **Animating the body radial-gradient stack.** v5 contract preserves it `background-attachment: fixed` — no per-component override.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Pre-commit gate framework | Husky / lefthook / pre-commit | Plain `.git/hooks/pre-commit` shell script (or follow `scripts/check_ipc_schema.py` pattern as a stand-alone script developer runs manually) | No `package.json` at repo root; ONE-SHOT gate doesn't merit a framework. Existing precedent is `check_ipc_schema.py` |
| Font subsetting | `pyftsubset` / `glyphhanger` | Ship full `latin` subset WOFF2 as Google Fonts/Fontsource provides them | Per-file size is small (Saira variable ~80 KB, JBM weights ~30 KB each); Latin subset already minimal; subsetting adds toolchain complexity and Phase 18 codesign attestation churn |
| WOFF2 hashing | Custom SHA-256 script | `shasum -a 256 tauri/ui/public/fonts/*.woff2` (already documented in LICENSE-3RD-PARTY.md:125) | Built into macOS; matches existing pattern |
| Backdrop-filter perf measurement | Custom FPS counter widget | Browser DevTools "Performance" panel + macOS Activity Monitor for compositor load + the `tauri-plugin-macos-fps` ref FPS widget (for the live FPS readout pattern — DO NOT install the plugin itself) | Phase 14's perf gate is **does the toggle work**, not **what's the steady-state FPS**. Phase 16 measures steady-state |
| `prefers-reduced-motion` polyfill | Custom JS detector | `@media (prefers-reduced-motion: reduce) { ... }` — WebKit + WebView2 both support natively | Standard since 2019; both engines current |
| Border-sweep animation library | Framer Motion / GSAP / Lottie | Existing `.border-anim` CSS keyframes utility in `tokens.css:297–331` | Conic-gradient + mask-composite + 22s linear rotation; pure CSS, GPU-composited |
| CSS variable hot-swap framework | Theme provider / context library | Direct `document.documentElement.setAttribute('data-blur-perf', 'on')` — CSS reads `:root[data-blur-perf="on"] { ... }` | One-attribute toggle; no framework warranted |

**Key insight:** This phase is *pure CSS + token consumer refactor*. Every "what if we used X library" is unnecessary — the v5 token system handles everything via cascade. The only **new** code path is the Settings → Performance "Lighter blur" toggle wiring (single IPC handler + one CSS rule + one toggle component). Resist any agent suggestion to introduce a CSS framework.

---

## Runtime State Inventory

This phase is a **rename/refactor migration**. The runtime-state audit must answer all five categories explicitly:

| Category | Items Found | Action Required |
|----------|-------------|-----------------|
| **Stored data** | **None.** No database, no datastore, no cache keys reference the renamed strings. The renamed tokens are CSS custom-property names — exist only in `tokens.css` + component CSS strings. Settings drawer persistence (Phase 12 `ConfigStore`) stores user prefs by key (e.g., `output.device`, `hotkey.push_to_mute`); none of those keys reference legacy token names. The **NEW** `lighter_blur` boolean adds a new key, not a rename. | None |
| **Live service config** | **None.** vibemix has no external services with chrome-string config. The `livekit-server --dev` and Gemini proxy URLs are unaffected. The Tauri overlay window's `data-blur-perf` attribute is set at runtime from `SettingsApplier` — not stored externally. | None |
| **OS-registered state** | **None for chrome.** Tauri overlay window position persists per-user (Phase 13 invariant) but key is the window label, not legacy token names. macOS TCC permissions are keyed to bundle id `world.bravoh.vibemix` (locked, unchanged). Windows registry / pm2 / launchd / Task Scheduler — vibemix has nothing there yet (pre-Phase 18). | None |
| **Secrets / env vars** | **None.** No env vars reference legacy token names. `GEMINI_API_KEY` and `VIBEMIX_*` env vars are unrelated. The pre-commit gate is a developer-workstation hook; doesn't touch secrets. | None |
| **Build artifacts** | **Vite cache (`tauri/ui/node_modules/.vite/`) MAY hold stale CSS / module compilations referencing legacy tokens.** Next `npm run build` after wave 5 will rebuild; no manual invalidation expected. The PyInstaller `--onedir` bundle (Phase 11 W1) bundles the static `dist/` only; rebuild after Phase 14 close picks up new fonts + tokens automatically. | After wave 5 close: `rm -rf tauri/ui/node_modules/.vite && npm run build` to verify clean rebuild. Document in Plan 14-05 verification. |

**The canonical question:** *After every file in `tauri/ui/src/` is updated, what runtime systems still have the old string cached, stored, or registered?* — Answer: **Vite cache only.** Rebuild and verify.

---

## Common Pitfalls

### Pitfall 1: WebView2 backdrop-filter + transparent window incompatibility
**What goes wrong:** `backdrop-filter: blur(32px) saturate(140%)` does NOT render correctly when applied inside a Tauri window with `transparent: true`. The blur silently fails or shows the parent window in chunks.
**Why it happens:** Microsoft Edge WebView2 has documented inconsistencies with backdrop-blur on transparent windows ([tauri#10064](https://github.com/tauri-apps/tauri/issues/10064), [tauri#12437](https://github.com/tauri-apps/tauri/issues/12437), [tauri#6876](https://github.com/tauri-apps/tauri/issues/6876)). macOS WKWebView is less affected but can lag.
**How to avoid:** Phase 14's mascot overlay window IS transparent (Phase 13 invariant). Test the `.border-anim` + glass treatment on the mascot wrapper div EARLY in wave 4 on Windows. If broken, the **fallback path is already specified** by CONTEXT Area 3: `--blur-glass-perf` runtime toggle + `prefers-reduced-motion` override drops to `blur(16px)` without saturate. For mascot specifically: the v5 chrome treatment is `--glass-3` (recessed) which the spec already designates as `--blur-glass-display: blur(6px) saturate(105%)` — minimal blur, less likely to trip the bug.
**Warning signs:** Mascot frame shows the entire macOS desktop unblurred behind it; or Windows shows a black rect instead of blur; or the frame flickers when the window is dragged.
**Source:** [tauri#10064 backdrop blur not working with transparent window](https://github.com/tauri-apps/tauri/issues/10064) [VERIFIED via WebSearch]

### Pitfall 2: Premature shim deletion cascades
**What goes wrong:** Deleting the shim in `tokens.css` while any component still references `--phosphor`, `--ink-deep`, etc. produces invalid CSS that silently degrades to browser defaults (often `initial` or `unset`) — chrome looks horribly broken.
**Why it happens:** CSS custom properties have no compile-time check; an undefined `var(--foo)` falls back to its fallback value (if specified) or to `unset`. Components without fallbacks render with browser defaults.
**How to avoid:** Pre-commit grep gate (script below) blocks the shim-delete commit unless legacy-token grep returns zero. The gate must run **after** the consumer migrations land, **before** the shim removal commit is created. Wired in by the Plan 14-05 task.
**Warning signs:** Plain black text on plain white; lost glass effect; gigantic text.

### Pitfall 3: Saira variable-font axis support gaps in WebView2 / WKWebView
**What goes wrong:** Older WebKit versions (< Safari 14) silently ignore `font-variation-settings`. macOS 12.3+ ships Safari 15+ which supports it [VERIFIED: caniuse]; Tauri WebView2 on Windows uses Chromium (full support since v62). All Phase 14 target platforms support variable fonts.
**Why it happens:** Variable fonts are well-supported in current platforms; the risk is mostly an outdated WebView2 on Windows 10 LTSB or similar.
**How to avoid:** Tauri's WebView2 auto-updates; minimum supported is the version that ships with the bundled runtime. Test on a clean Windows 11 in Phase 16 as part of fresh-VM rehearsal. Phase 14's only verification: live wizard step 1 on Kaan's M-series Mac renders Saira at multiple `wdth` values distinctly. `[ASSUMED]` until verified.
**Warning signs:** All Saira text looks the same width regardless of `wdth` setting.

### Pitfall 4: `mask-composite: exclude` standard vs. `-webkit-mask-composite: xor` vendor prefix
**What goes wrong:** Forgetting one of the two property forms makes the `.border-anim` mask trick fail in either WebKit (Safari, WKWebView) or Blink (Chrome, WebView2) — depending on which prefix you skipped.
**Why it happens:** The standard is `mask-composite: add | subtract | intersect | exclude` (Firefox prefers); WebKit/Blink historically use `-webkit-mask-composite: source-over | source-out | source-in | xor`. The mapping is `exclude` ↔ `xor`. **Both are required** for cross-engine compatibility.
**How to avoid:** Current `tokens.css:316–324` already specifies both. Phase 14 audit: verify the dual-property pattern survives every refactor and isn't accidentally removed when reformatting. Add a grep regression test as part of the migration: `grep -A2 '\.border-anim' tokens.css | grep -E 'mask-composite|webkit-mask-composite'` must return both.
**Warning signs:** Border-anim renders as a solid rotating disc instead of a thin ring on one platform but works on the other.
**Source:** [MDN -webkit-mask-composite docs](https://developer.mozilla.org/en-US/docs/Web/CSS/-webkit-mask-composite); [Codrops mask-composite reference](https://tympanus.net/codrops/css_reference/mask-composite/) [VERIFIED via WebSearch]

### Pitfall 5: Font-vendor mismatch on Windows non-dev install
**What goes wrong:** WOFF2 served from `tauri/ui/public/fonts/` works in `npm run dev` but the production-bundled Tauri Windows MSI doesn't ship the font because the `dist/` copy step missed it.
**Why it happens:** Vite copies `public/` into `dist/` at build time. If `vite.config.ts` excludes a path or PyInstaller spec doesn't preserve `dist/fonts/`, the font path 404s in production.
**How to avoid:** Phase 14 close runs `npm run build` + verifies `tauri/ui/dist/fonts/Saira-*.woff2` exists. Phase 18 codesign step picks up `dist/` wholesale, so if the build artifact is correct the install is correct. Belt-and-braces: add a vite plugin assertion or document the manual check.
**Warning signs:** Production wizard renders in fallback font (likely system-ui / `monospace`).

### Pitfall 6: ROADMAP / REQUIREMENTS / mock contradiction propagating into ui-auditor passes
**What goes wrong:** `gsd-ui-auditor` reads ROADMAP "Geist + Fraunces" and flags the live UI for not using those fonts. Cycle wastes a critique iteration on a stale-doc issue.
**Why it happens:** Typeface reconciliation explicit in CONTEXT Area 4 but ROADMAP success criterion #4 wasn't yet updated when Phase 14 starts.
**How to avoid:** Plan 14-01 (first plan in phase) updates ROADMAP success-criterion text + REQUIREMENTS POLISH-04 in one task BEFORE any surface migration. The reconciliation lands first.

### Pitfall 7: `--col-mascot` deletion breaks `.wizard-grid` layout invisibly
**What goes wrong:** Removing `--col-mascot: 256px` token while `.wizard-grid` still has `grid-template-columns: var(--col-primary) var(--col-mascot)` produces a layout where the second (now-empty) column collapses to 0 but components still attempt to mount into it.
**Why it happens:** `tokens.css:441` defines the grid; `mascot-corner.ts` mounts at `.wizard-grid > :nth-child(2)`. Deleting the token requires deleting the grid column AND the component.
**How to avoid:** Wave 1 (wizard) deletes `mascot-corner.ts` AND updates `.wizard-grid` to single-column simultaneously. Verified by visual screenshot pair (wizard primary panel fills the full content width).
**Warning signs:** Wizard primary panel renders at 560px width inside a 560+32+0=592px effective layout; right side gap remains visible as empty space.

### Pitfall 8: Pre-commit grep gate firing on EVERY commit
**What goes wrong:** If the pre-commit hook is wired as a global hook (not one-shot), every routine commit in the phase blocks until the legacy refs hit zero. Wave 1 commits would all be blocked by the still-present wave 2/3/4 refs.
**Why it happens:** Misunderstanding "one-shot" — easy to leave a `.git/hooks/pre-commit` enabled across all commits.
**How to avoid:** Two-phase pre-commit:
  1. **During waves 1–4:** the hook is a soft check (warn-only) that prints the current ref count but doesn't block. Used as a progress dashboard.
  2. **At wave 5 (shim-delete commit):** the hook becomes blocking. Implementation choice: a single shell script with a `--strict` flag, or two separate hooks rotated in/out. Recommendation: ONE script (`scripts/check_v5_migration.sh`) with both modes; wave 5 task adds the `.git/hooks/pre-commit` symlink to the strict-mode invocation, removes it after the commit lands.
**Warning signs:** Developer running `git commit` for a routine task gets blocked by a Phase 14 gate.

### Pitfall 9: Forbidden-font residue in jsdoc comments tripping the purge gate
**What goes wrong:** The Workbench / DM Mono / DSEG7 / Caveat references in jsdoc comments (e.g., `/** Body — DM Mono 13.5px */`) get counted by a too-broad grep gate and block the shim-delete commit even after font-family declarations are migrated.
**Why it happens:** A grep that matches `DM Mono` anywhere in `*.ts` files hits comments too.
**How to avoid:** The grep gate distinguishes string literals from comments. Pragmatic approach: scope the forbidden-font gate to `font-family:` declarations specifically: `grep -rn -E 'font-family:\s*"(Workbench|DM Mono|DSEG7|Caveat)"' tauri/ui/src/ --include='*.ts' --include='*.css'`. Code-comment refs can be cleaned up but don't block.
**Warning signs:** Grep gate fails with all-jsdoc hits; nothing actually wrong with the running UI.

---

## Code Examples

### Vendored font `@font-face` (replaces `@import` on tokens.css line 35)

```css
/* Source: mocks/vibemix-direction-final.html replicating Google Fonts CSS for Saira + JBM
 * Substituted for vendored WOFF2 paths so the wizard renders offline. */

/* Saira — variable axes (wdth + wght). Single file, all weights+widths. */
@font-face {
  font-family: 'Saira';
  src: url('/fonts/Saira-VariableFont_wdth,wght.woff2') format('woff2-variations'),
       url('/fonts/Saira-VariableFont_wdth,wght.woff2') format('woff2');
  font-weight: 300 800;
  font-stretch: 75% 125%;
  font-style: normal;
  font-display: swap;
}

/* JetBrains Mono — three weights as static WOFF2 (variable axis not needed for numerics) */
@font-face {
  font-family: 'JetBrains Mono';
  src: url('/fonts/JetBrainsMono-Regular.woff2') format('woff2');
  font-weight: 400;
  font-style: normal;
  font-display: swap;
}
@font-face {
  font-family: 'JetBrains Mono';
  src: url('/fonts/JetBrainsMono-Medium.woff2') format('woff2');
  font-weight: 500;
  font-style: normal;
  font-display: swap;
}
@font-face {
  font-family: 'JetBrains Mono';
  src: url('/fonts/JetBrainsMono-SemiBold.woff2') format('woff2');
  font-weight: 600;
  font-style: normal;
  font-display: swap;
}
```

**Notes:**
- `format('woff2-variations')` is **preferred** for variable WOFF2; older WebView2 may need bare `woff2` as a fallback — the dual `src` covers both.
- `font-display: swap` matches Phase 11 W3 invariant (FOUT preferred over invisible text).
- `font-stretch: 75% 125%` enables the `wdth` axis range Saira supports.

### Pre-commit gate script (NEW — `scripts/check_v5_migration.sh`)

```bash
#!/usr/bin/env bash
# Phase 14 shim-removal gate — runs as .git/hooks/pre-commit on the shim-delete commit only.
#
# Usage:
#   ./scripts/check_v5_migration.sh           — warn-only progress dashboard
#   ./scripts/check_v5_migration.sh --strict  — block commit on any hit
#
# Exit codes: 0 = pass, 1 = legacy refs found in strict mode, 2 = invocation error
set -euo pipefail

STRICT=0
[[ "${1:-}" == "--strict" ]] && STRICT=1

# Move to repo root regardless of cwd
cd "$(git rev-parse --show-toplevel)"

# Legacy CSS-token refs outside tokens.css
LEGACY_TOKEN_PATTERN='--(phosphor|brushed-(hi|lo)|bezel-[123]|panel(-lift|-deep|-hover-top|-pressed-bottom)?|groove|ink(-(dim|deep|engraved))?|charcoal|col-mascot)\b'

# Forbidden font-family declarations
FORBIDDEN_FONT_PATTERN='font-family:\s*"(Workbench|DM Mono|DSEG7|Caveat)"'

token_hits=$(grep -rnE "$LEGACY_TOKEN_PATTERN" tauri/ui/src/ \
  --include='*.ts' --include='*.tsx' --include='*.css' --include='*.html' \
  2>/dev/null | grep -v 'tokens.css' | wc -l | tr -d ' ')

font_hits=$(grep -rnE "$FORBIDDEN_FONT_PATTERN" tauri/ui/src/ \
  --include='*.ts' --include='*.tsx' --include='*.css' \
  2>/dev/null | wc -l | tr -d ' ')

echo "Phase 14 v5 migration gate:"
echo "  legacy CSS-token refs (outside tokens.css):    $token_hits"
echo "  forbidden font-family declarations:            $font_hits"

if [[ $STRICT -eq 1 ]]; then
  if [[ $token_hits -gt 0 || $font_hits -gt 0 ]]; then
    echo ""
    echo "BLOCKED. Migrate the remaining refs before deleting the shim:"
    grep -rnE "$LEGACY_TOKEN_PATTERN" tauri/ui/src/ \
      --include='*.ts' --include='*.tsx' --include='*.css' --include='*.html' \
      2>/dev/null | grep -v 'tokens.css' | head -20
    grep -rnE "$FORBIDDEN_FONT_PATTERN" tauri/ui/src/ \
      --include='*.ts' --include='*.tsx' --include='*.css' 2>/dev/null | head -20
    exit 1
  fi
  echo "  STRICT mode: PASS (zero hits)"
else
  echo "  warn-only mode (informational)"
fi
exit 0
```

**Wiring as one-shot pre-commit hook:**

```bash
# At start of Plan 14-05 (wave 5 shim-delete task):
cat > .git/hooks/pre-commit <<'EOF'
#!/usr/bin/env bash
exec "$(git rev-parse --show-toplevel)/scripts/check_v5_migration.sh" --strict
EOF
chmod +x .git/hooks/pre-commit

# After the shim-delete commit lands:
rm .git/hooks/pre-commit
```

### CSS-variable hot-toggle for "Lighter blur" Settings toggle

```css
/* Source: tokens.css addition for Plan 14-03 (settings drawer wave) */

/* Default state — full v5 blur */
:root {
  --blur-glass:         blur(32px) saturate(140%);
  --blur-glass-light:   blur(16px) saturate(120%);
  --blur-glass-display: blur(6px)  saturate(105%);
}

/* prefers-reduced-motion override — accessibility first */
@media (prefers-reduced-motion: reduce) {
  :root {
    --blur-glass:         blur(16px);
    --blur-glass-light:   blur(8px);
    --blur-glass-display: blur(4px);
    --motion-border-sweep: 0s;
  }
  .border-anim { animation: none; opacity: 0.6; }
}

/* User-toggled "Lighter blur" — Settings > Performance > "Lighter blur" sets this */
html[data-blur-perf="on"] {
  --blur-glass:         blur(16px);
  --blur-glass-light:   blur(8px);
  --blur-glass-display: blur(4px);
  /* NOTE: do NOT freeze .border-anim here — animation cost is conic-gradient
   * repaint, not backdrop-filter; cheap on every GPU we ship to. */
}
```

**TypeScript toggle wiring (Plan 14-03):**

```ts
// Source: new tauri/ui/src/settings/components/performance-group.ts

import { sendIpcRequest } from '../../ipc/client';

/** Apply current state on boot — read from SettingsApplier, default false */
export function applyBlurPerfPreference(enabled: boolean): void {
  if (enabled) {
    document.documentElement.setAttribute('data-blur-perf', 'on');
  } else {
    document.documentElement.removeAttribute('data-blur-perf');
  }
}

/** Toggle handler — write through SettingsApplier (Phase 12 IPC) */
export async function toggleBlurPerf(enabled: boolean): Promise<void> {
  applyBlurPerfPreference(enabled);
  await sendIpcRequest({
    type: 'settings.set',
    field: 'performance.lighter_blur',
    value: enabled,
  });
}
```

**Settings IPC schema delta (Plan 14-03 task):** add `performance.lighter_blur: boolean` to the `settings.set` field dispatcher. Verify against the count-parity check in `scripts/check_ipc_schema.py` — the existing 26 ipc.* families count stays the same; this is a new field, not a new message.

### Animated border applied to mascot overlay window wrapper

```ts
// Source: Plan 14-04 — wave 4 mascot surface migration
// Adapts tokens.css .border-anim utility onto the Phase 13 overlay window's
// outermost HTML element. Three.js canvas remains transparent below the border.

const mascotShell = document.createElement('div');
mascotShell.className = 'mascot-window';
mascotShell.style.cssText = `
  position: relative;
  overflow: hidden;
  border-radius: 8px;   /* 8px vs. 6px on session/wizard — mock spec */
  background: var(--glass-3);
  backdrop-filter: var(--blur-glass-display);
  -webkit-backdrop-filter: var(--blur-glass-display);
  border: 1px solid var(--glass-edge);
  box-shadow:
    inset 0 1px 0 var(--glass-top),
    inset 0 -1px 0 rgba(255, 138, 61, 0.06),   /* mock-verbatim — faint amber undertone */
    0 32px 64px rgba(0, 0, 0, 0.85),
    0 0 0 1px rgba(255, 255, 255, 0.018);
`;

// Border-anim as FIRST CHILD — slow.rev so it doesn't sync with session 22s sweep
const borderAnim = document.createElement('div');
borderAnim.className = 'border-anim slow rev';
mascotShell.appendChild(borderAnim);

// Three.js canvas mounts here (Phase 13 invariant — renderer.ts owns this)
mascotShell.appendChild(threeJsCanvas);
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Multiple separate font files (Workbench, DM Mono, DSEG7, Caveat) | Single variable font (Saira `wdth` + `wght`) + mono companion (JetBrains Mono) | v5 visual contract (2026-05-12) | Cuts 4 WOFF2 files, ~70KB total → 2 files ~110KB total. Net wash on size; massive gain on typographic flexibility |
| Remote `@import` from `fonts.googleapis.com` | Vendored WOFF2 under `tauri/ui/public/fonts/` | Phase 14 wave 5 (this phase) | Offline-friendly; one-click install requirement satisfied; codesign attestation possible |
| `mask-composite: xor` (vendor-only) | Dual `mask-composite: exclude` + `-webkit-mask-composite: xor` | Already in `tokens.css:316–324` | Standard property + vendor fallback — works everywhere |
| Skeuomorphic 3D bevel box-shadows (`--bezel-1/2/3`, `--brushed-hi/lo`) | Glass treatment (`inset 0 1px 0 var(--glass-top)` + drop shadows) | v5 (CDJ Whisper) | Modern glass aesthetic; depth via material, not faux-metal |
| DSEG7 7-segment LCD font for numerics | JetBrains Mono with `font-variant-numeric: tabular-nums` | v5 mock §typography | More legible; pairs better with Saira; one less font file |
| `--phosphor: #ffa12e` (Phase 11/12 amber) | `--amber: #ff8a3d` (CDJ Whisper amber) | v5 (deliberate hue swap) | Slightly more orange / less yellow; matches Pioneer CDJ-3000 deck-light reference |

**Deprecated / outdated:**
- Workbench (Phase 11 W3 display font) — replaced by Saira variable.
- DM Mono (Phase 11 W3 body monospace) — replaced by JetBrains Mono.
- DSEG7 Classic Bold (Phase 11 W3 numeric LCD) — replaced by JetBrains Mono tabular-nums.
- Caveat Bold (Phase 11 W3 reserved sticker font) — never used; removed wholesale.
- `--phosphor*` token family — replaced by `--amber*`.
- `--brushed-hi/lo`, `--bezel-1/2/3` — replaced by `--glass-top` and inline `rgba(0,0,0,0.5)` for bottom shadows; bevels deleted entirely.
- `--ink*` token family — replaced by `--silk*`.
- `--col-mascot: 256px` — DELETED (mascot is overlay window, not embedded).
- `--cue: #4dc4ff` — was forbidden in Phase 11; deleted in wave 5 as part of cleanup.
- ROADMAP success criterion #4 text "Geist + Fraunces" — stale; reconciled in Plan 14-01.

---

## Validation Architecture

> Per Nyquist validation: how does the planner verify each surface migration is complete?

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Vitest ^2.1 + jsdom ^29.1.1 (already configured) |
| Config file | `tauri/ui/vitest.config.ts` — extends `include` to pick up `src/**/*.{spec,test}.ts` |
| Quick run command | `cd tauri/ui && npm test` (vitest run --reporter=dot) |
| Full suite command | `cd tauri/ui && npm test && npm run check:ipc && python3 scripts/check_ipc_schema.py` |
| Phase gate | Full suite green + manual side-by-side screenshot per surface |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| POLISH-02 | Zero legacy-token refs outside tokens.css after wave 5 | grep-script | `./scripts/check_v5_migration.sh --strict` | ❌ Wave 0 (NEW) |
| POLISH-02 | Forbidden font-families absent in `font-family:` declarations after wave 5 | grep-script | Same script — covers both | ❌ Wave 0 (NEW) |
| POLISH-02 | Zero hardcoded hex outside tokens.css | grep-script | `grep -rnE '#[0-9a-fA-F]{6}\b' tauri/ui/src/ --include='*.ts' --include='*.css' \| grep -v tokens.css` | (uses existing grep; no script needed) |
| POLISH-03 | Mascot overlay `.border-anim` mounted on the wrapper div | DOM unit test (vitest jsdom) | `vitest run src/mascot/window-chrome.test.ts` | ❌ Wave 0 (NEW — `src/mascot/window-chrome.test.ts`) |
| POLISH-04 | Purge-dictionary terms absent from string literals | grep-script (manual-review subset for `tactile`) | Same `check_v5_migration.sh` extended | (already in script above) |
| POLISH-06 (perf) | `data-blur-perf="on"` attribute on `<html>` swaps blur tokens | DOM integration test (vitest jsdom) | `vitest run src/settings/performance-group.test.ts` | ❌ Wave 3 (NEW) |
| POLISH-06 (perf) | `@media (prefers-reduced-motion: reduce)` rule present in tokens.css | grep-script | `grep -A4 'prefers-reduced-motion' tauri/ui/src/tokens.css` | ❌ Wave 0 (NEW) |
| POLISH-06 (vis) | gsd-ui-checker zero findings per surface | manual | `gsd-ui-checker` invocation; output → polish log | (existing skill) |
| POLISH-06 (vis) | gsd-ui-auditor 3 audits green per surface | manual | `gsd-ui-auditor` invocation; output → polish log | (existing skill) |
| POLISH-06 (manual) | Side-by-side screenshot pair attached to each plan SUMMARY | manual | live `npm run tauri dev` + screenshot | (Kaan-side) |

### Sampling Rate

- **Per task commit:** `cd tauri/ui && npm test --reporter=dot` (only the touched-component spec, < 5s)
- **Per wave merge:** Full suite — `npm test && npm run build` (`tsc --noEmit` catches type drift)
- **Phase gate:** `./scripts/check_v5_migration.sh --strict` + full vitest suite + manual screenshot pair per surface + `gsd-ui-checker` + `gsd-ui-auditor` 3 audits each

### Wave 0 Gaps

- [ ] `scripts/check_v5_migration.sh` — the pre-commit grep gate (warn-only + strict modes); covers POLISH-02 + POLISH-04
- [ ] `tauri/ui/src/mascot/window-chrome.test.ts` — vitest jsdom unit test verifying `.border-anim` mounts as first child of mascot overlay root with class `slow rev`
- [ ] `tauri/ui/src/settings/performance-group.test.ts` — vitest jsdom integration test for "Lighter blur" toggle: writes `data-blur-perf="on"` to `<html>` when enabled, removes when disabled, persists via mocked `sendIpcRequest`
- [ ] No framework install needed — vitest already present in `package.json`

**Manual-only test items** (no automated assertion possible):
- Mascot overlay chrome composes correctly against macOS Spaces (transparent window across desktops). Reason: requires real Tauri overlay window + multi-desktop setup; not reproducible in vitest. → **Phase 14 close manual checklist** on Kaan's M-series Mac.
- Backdrop-filter perf on Windows non-dev machine. Reason: requires Windows install. → **Phase 14 close**, can borrow from Phase 20 fresh-VM rehearsal.
- "Matches the mock" perceptual judgment. Reason: subjective. → `gsd-ui-checker` zero findings + screenshot pair attached.

---

## Security Domain

> Phase 14 is pure presentation; no auth, sessions, cryptography, or input validation introduced. Most ASVS categories are not applicable.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|------------------|
| V2 Authentication | no | n/a |
| V3 Session Management | no | n/a |
| V4 Access Control | no | n/a |
| V5 Input Validation | yes (limited) | The "Lighter blur" toggle is a boolean coming through existing Phase 12 `settings.set` IPC; existing ajv schema validation covers it [VERIFIED: existing `tauri/ui/src/ipc/validator.ts`] |
| V6 Cryptography | no | n/a |
| V14 Configuration | yes | Vendored WOFF2 files MUST have SHA-256 attestation in `tauri/ui/LICENSE-3RD-PARTY.md`; Phase 18 codesign chain depends on stable hashes [CITED: LICENSE-3RD-PARTY.md:11–12] |

### Known Threat Patterns for {Tauri webview + vanilla TS}

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| XSS via unsanitized chrome strings | Tampering | All chrome strings are static literals in TS files — no user-supplied content rendered as innerHTML. Existing Phase 11 invariant. No change in Phase 14. |
| Stale font cache after rename | Tampering / Repudiation | `scripts/check_v5_migration.sh --strict` blocks the shim-delete commit until LICENSE-3RD-PARTY.md is updated AND new WOFF2 SHAs are pinned (manual step in Plan 14-05 task list) |
| Remote font fetch leaking IP | Information Disclosure | The `@import` from `fonts.googleapis.com` in `tokens.css:35` is DELETED in wave 5 — replaced by vendored WOFF2. Privacy gate: zero outbound runtime fetches from chrome [VERIFIED: HANDOFF watchout + CONTEXT Area 2] |

**Phase 14 net security delta:** **improves** privacy posture by removing the Google Fonts runtime fetch.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node + npm | Vite, Vitest, tsc | ✓ (existing) | npm-managed in `tauri/ui/` | — |
| Bash 4+ | `scripts/check_v5_migration.sh` pre-commit hook | ✓ | macOS ships bash 3.2; script uses `${1:-}` + `set -euo pipefail` which works on bash 3.2 | If bash 3.2 fails, fall back to `/bin/sh` POSIX subset |
| `grep -E` | Same script | ✓ | macOS BSD grep + Linux GNU grep both support `-E -r --include` flags | — |
| `shasum -a 256` | Manual font SHA generation for LICENSE-3RD-PARTY.md | ✓ | macOS built-in; Linux equiv `sha256sum` | — |
| Saira variable WOFF2 source | Font vendoring step | ✗ (must fetch) | Latest from Google Fonts or Fontsource | Fontsource if Google Fonts CDN access is unreliable |
| JetBrains Mono WOFF2 source | Font vendoring step | ✗ (must fetch) | Official JetBrains/JetBrainsMono GitHub release or Fontsource | — |
| Tauri dev (`npm run tauri dev`) | Live UI smoke test per surface | ✓ (Kaan's rig) | macOS WKWebView | Browser fallback via `npm run dev` (Vite-only, no Tauri shell) |
| Windows non-dev machine | Wave 5 backdrop-filter perf verification | ⚠ (Kaan may not have) | — | Borrow Phase 20 fresh-VM CI matrix or Francesco's Windows machine — defer-but-mark per CONTEXT Area 3 |

**Missing dependencies with no fallback:** none — all required tools/runtimes are present on Kaan's rig or downloadable.
**Missing dependencies with fallback:** Windows test rig — fallback is Phase 20 borrow (already anticipated in CONTEXT Area 3).

---

## Backdrop-Filter Performance Measurement Procedure

Phase 14 doesn't need rigorous per-machine FPS profiling (that's Phase 16). It needs to **prove the toggles work** and **catch egregious stutter** on a Windows non-dev machine before the phase closes.

### What to measure
- Steady-state frame time (ms) during a typical 30-second wizard interaction + a 30-second live session UI sample.
- Whether the `data-blur-perf="on"` toggle produces a perceptible improvement (subjective, but should be measurable).
- Whether `prefers-reduced-motion` system setting takes effect in CSS (verified by inspecting computed style after enabling reduced motion in OS).

### How to measure (no new tooling)
1. **macOS (Kaan's M-series rig):**
   - In Tauri dev build, right-click → **Inspect Element** → DevTools opens (WebKit Web Inspector).
   - Performance tab → record 10s during wizard step 2 (most blur-heavy: glass primary panel + animated border + film grain).
   - Read **frametime** in the timeline. Expect < 16ms (60fps) on M-series.
   - Toggle "Lighter blur" in Settings → re-record. Frametime should drop OR stay flat (already fine).
   - Open System Settings → Accessibility → Display → enable "Reduce motion" → verify `.border-anim` stops + blur drops in computed style.
2. **Windows non-dev (Francesco / Phase 20 borrow):**
   - Install vibemix dev build (or use Phase 18 prerelease if available).
   - DevTools F12 in WebView2 (or `--remote-debugging-port` flag) → Performance tab → 10s capture.
   - Pass criterion: average frametime < 33ms (30fps minimum) on a non-dev integrated-GPU laptop.
   - If average > 33ms with `data-blur-perf` off, document and gate the production default to ON for Windows in `SettingsApplier` (deferred to Phase 16 if not Kaan-blocking).

### Pass/fail thresholds for Phase 14 close
- **Pass:** macOS frametime < 16ms with full blur; Windows frametime < 50ms with full blur AND < 33ms with `data-blur-perf="on"`.
- **Conditional pass:** Windows frametime ≥ 33ms with `data-blur-perf="on"` → set Windows default to ON, document in `14-SUMMARY.md`, escalate Phase 16 perf budget.
- **Fail:** Toggle doesn't apply OR `prefers-reduced-motion` ignored → fix before closing.

### Tools/Refs
- Tauri DevTools (built-in on dev builds). [CITED: Tauri v2 docs]
- macOS Activity Monitor → WindowServer CPU% (high % suggests compositor hammering).
- [tauri-plugin-macos-fps reference FPS counter widget code](https://github.com/userFRM/tauri-plugin-macos-fps) — reference only; DO NOT install (introduces a runtime dep we don't need). The widget code (rAF-counted FPS readout) can be lifted as a dev-only debug overlay if Kaan wants live numbers.

`[ASSUMED]` — Specific frametime thresholds (16ms / 33ms / 50ms) are my recommended Phase 14 gates derived from common 60fps/30fps targets. If Kaan has a specific number in mind, he should answer in Plan 14-03 (perf-toggle plan) before execution.

---

## Animated Border DOM/CSS Pattern Validation

### Engine support matrix

| Engine | `mask-composite: exclude` | `-webkit-mask-composite: xor` | `conic-gradient` | `@keyframes rotate(360deg)` | Composite on GPU |
|--------|---------------------------|-------------------------------|------------------|-----------------------------|------------------|
| WKWebView (macOS) | ✓ (Safari 15.4+) | ✓ (all Safari) | ✓ (Safari 12.1+) | ✓ | ✓ |
| WebView2 (Windows, Chromium) | ✓ (Chromium 120+) | ✓ (all Chromium) | ✓ (Chrome 69+) | ✓ | ✓ |

[VERIFIED via WebSearch + MDN]: Both engines fully support the standard + WebKit-prefixed dual property. The pattern as encoded in `tokens.css:302–331` is production-correct.

### Specific concern: Tauri overlay window (transparent + animated border)

Phase 13's mascot overlay window has `transparent: true` set. The animated border lives **inside** the window (on the wrapper div, not on the OS window frame), so it's:
- Rendered by WebView2/WKWebView, not by the OS compositor.
- Outside the transparent-window bug zone (see Pitfall 1) — that bug affects `backdrop-filter`, not `mask-composite`.

`[ASSUMED]`: No platform-specific fallback needed for `.border-anim`. Confirm by spinning up the mascot overlay window during wave 4 task execution with the border applied and visually verifying on macOS first, then Windows in Phase 20 borrow.

### Fallback (if engine support unexpectedly breaks)

Replace conic-gradient mask trick with a CSS pseudo-element `::before` using `linear-gradient` rotated via `transform` — visually less precise but engine-agnostic. Not anticipated to be needed.

---

## WOFF2 Font Vendoring Procedure

Step-by-step for Plan 14-05 (wave 5):

### 1. Acquire WOFF2 files

**Saira variable font (preferred path — Fontsource for guaranteed variable WOFF2):**

```bash
# From Fontsource: includes variable WOFF2 in latin subset
mkdir -p /tmp/saira-vendor
curl -L 'https://cdn.jsdelivr.net/fontsource/fonts/saira:vf@latest/latin-wght-normal.woff2' \
  -o /tmp/saira-vendor/Saira-Variable-wght-normal.woff2
# Note: Fontsource splits wght and wdth into separate VF files in 2026.
# For BOTH axes in one file, use Google Fonts download flow:
#   1. visit https://fonts.google.com/specimen/Saira
#   2. select "Get embed code" → variable axes
#   3. download .zip → contains Saira-VariableFont_wdth,wght.ttf
#   4. convert TTF → WOFF2 via woff2_compress (apt install woff2 / brew install woff2)
```

**JetBrains Mono (preferred — official GitHub release):**

```bash
# From github.com/JetBrains/JetBrainsMono releases
curl -L 'https://github.com/JetBrains/JetBrainsMono/releases/download/v2.304/JetBrainsMono-2.304.zip' \
  -o /tmp/jbm.zip
unzip /tmp/jbm.zip -d /tmp/jbm
# Convert .ttf → .woff2 for the three weights we need:
woff2_compress /tmp/jbm/fonts/ttf/JetBrainsMono-Regular.ttf
woff2_compress /tmp/jbm/fonts/ttf/JetBrainsMono-Medium.ttf
woff2_compress /tmp/jbm/fonts/ttf/JetBrainsMono-SemiBold.ttf
```

### 2. Place under repo

```bash
cp /tmp/saira-vendor/Saira-VariableFont_wdth,wght.woff2 tauri/ui/public/fonts/
cp /tmp/jbm/fonts/webfonts/JetBrainsMono-Regular.woff2 tauri/ui/public/fonts/
cp /tmp/jbm/fonts/webfonts/JetBrainsMono-Medium.woff2 tauri/ui/public/fonts/
cp /tmp/jbm/fonts/webfonts/JetBrainsMono-SemiBold.woff2 tauri/ui/public/fonts/
```

### 3. Compute SHA-256

```bash
cd tauri/ui/public/fonts
shasum -a 256 Saira-VariableFont_wdth,wght.woff2 \
  JetBrainsMono-{Regular,Medium,SemiBold}.woff2
```

### 4. Update `tauri/ui/LICENSE-3RD-PARTY.md`

- **DELETE** entries for Workbench, DM Mono (Regular + Medium), DSEG7, Caveat (5 entries total — lines ~15–63 of current file).
- **ADD** entries for Saira (variable) + JetBrains Mono (Regular + Medium + SemiBold), with:
  - SHA-256 from step 3
  - License attribution (both OFL-1.1)
  - Source URL (Fontsource / JetBrains GitHub)
  - Use-in-vibemix description per font

### 5. Replace `tokens.css` font block

- **DELETE** line 35 (`@import url('https://fonts.googleapis.com/...');`)
- **DELETE** lines 38–76 (legacy `@font-face` block for Workbench/DM Mono/DSEG7/Caveat)
- **ADD** new `@font-face` block (see Code Example above) for Saira + JetBrains Mono

### 6. Delete the legacy WOFF2 files

```bash
rm tauri/ui/public/fonts/Workbench-Regular.woff2
rm tauri/ui/public/fonts/DMMono-Regular.woff2
rm tauri/ui/public/fonts/DMMono-Medium.woff2
rm tauri/ui/public/fonts/DSEG7Classic-Bold.woff2
rm tauri/ui/public/fonts/Caveat-Bold.woff2
```

### 7. Verify build artifact

```bash
cd tauri/ui
rm -rf node_modules/.vite dist
npm run build
ls dist/fonts/    # must contain Saira + JetBrainsMono WOFF2 files
```

### 8. Subset / unicode-range strategy

`[ASSUMED]`: latin subset (U+0000–U+00FF) is sufficient — Phase 14 chrome is English-only per REQUIREMENTS scope ("Multi-language UI chrome" in v2/deferred). If Fontsource provides latin-only WOFF2, accept as-is; no further subsetting needed.

If file size becomes a concern in Phase 18 install-size review: `pyftsubset` (fonttools) can strip unused glyphs further. Not worth doing pre-emptively — current target Saira variable ~80KB is acceptable.

---

## Assumptions Log

> Claims tagged `[ASSUMED]` in this research — items that need user confirmation OR Phase 14 task-level verification before becoming locked decisions.

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Vite + Tauri auto-bundle `tauri/ui/public/fonts/*.woff2` into `dist/fonts/` without additional config | Font Vendoring Procedure step 7 | LOW — verified by `cd tauri/ui && npm run build` ; if missing, add to `vite.config.ts` `assetsInclude` |
| A2 | macOS WKWebView and WebView2 both fully support Saira variable axes (wdth + wght) on Phase 14 target platforms | Pitfall 3 | LOW — current macOS 12.3+ ships Safari 15+ (full support); Tauri WebView2 auto-updates. Verify by visual smoke test on Kaan's rig + Phase 20 Windows fresh-VM |
| A3 | The `.border-anim` mask-composite trick works on Tauri overlay windows with `transparent: true` set | Animated Border Pattern Validation | MEDIUM — transparent-window bug is for `backdrop-filter`, not `mask-composite`; but unverified on the specific Tauri overlay window setup. **Verify EARLY in wave 4** |
| A4 | Backdrop-filter Windows non-dev frametime target of < 50ms (full blur) and < 33ms (lighter blur) is acceptable for Kaan's quality bar | Backdrop-filter Performance Measurement | MEDIUM — these are my recommended thresholds; Kaan's "no AI slop" bar may want different numbers. **Resolve in Plan 14-03 perf-toggle plan task** |
| A5 | Latin subset (U+0000–U+00FF) is sufficient — no Cyrillic / CJK / Greek glyphs needed in v1 chrome | Font Vendoring step 8 | LOW — v1 is English-only per REQUIREMENTS scope; multi-lang chrome is v2/deferred |
| A6 | "Lighter blur" Settings IPC schema delta is a new `settings.set` field, not a new ipc.* message family | Validation Architecture — Code Examples | LOW — adding a field to `SettingsApplier` is the same pattern as Phase 12 added `hotkey_push_to_mute` etc.; existing IPC count parity (26) stays the same |
| A7 | Pre-commit hook is wired manually via `.git/hooks/pre-commit` symlink (no husky/lefthook installation) | Code Example pre-commit script | LOW — matches existing precedent (`scripts/check_ipc_schema.py` is a manual-run script); no team-coordination challenge since vibemix is mostly Kaan + Claude |
| A8 | Workbench/DM Mono/DSEG7/Caveat references in JSDOC comments (e.g., `/** Body — DM Mono 13.5px */`) DON'T need to be purged for the shim-delete gate to pass; only `font-family:` declarations matter | Pitfall 9 | LOW — pragmatic scope choice; comments can be cleaned up incrementally without blocking the gate |
| A9 | The 32px `--sp-xl` and 48px `--sp-2xl` legacy spacing aliases have no exact v5 equivalent and components currently using them migrate to `--sp-5` (24) / `--sp-6` (40) OR keep the literal inline | UI-SPEC §Spacing | LOW — UI-SPEC explicitly defers this to "author's call"; verify each call site during wave 1 |

**If any A-item resolves "wrong" during execution, the affected wave must replan that task and document the resolution in the polish log.**

---

## Open Questions

1. **What screenshot tool does the executor use for "side-by-side screenshot pair attached to plan SUMMARY"?**
   - What we know: Kaan-side or live `npm run tauri dev` mention in `14-UI-SPEC.md` Critique Loop Configuration table. No specific tool named.
   - What's unclear: Whether `gsd-ui-checker` itself captures screenshots, or whether Kaan manually screencaps via macOS native + diff.
   - Recommendation: Default to Kaan manually capturing via macOS Cmd+Shift+4 → drag-select the surface → save with descriptive filename (e.g., `wave-1-wizard-step-1.png`) + crop the mock §01 reference → attach both to the plan SUMMARY. If the `gsd-ui-checker` skill includes screenshot capture, it overrides this. Plan 14-01 can ask Kaan to confirm.

2. **Where does the `gsd-ui-checker` / `gsd-ui-auditor` output get written?**
   - What we know: References to "ui-checker output ref" and "ui-auditor output ref" in the polish log table schema — implying file paths.
   - What's unclear: Whether the GSD `gsd-ui-checker` skill writes to `.planning/phases/<phase>/audits/<surface>-cycle-<N>.md` or stdout-only.
   - Recommendation: Plan 14-01 confirms with Kaan and pins the convention before wave 1.

3. **What's the EXACT incantation to invoke `gsd-ui-checker` and `gsd-ui-auditor` skills?**
   - What we know: The names are referenced extensively in CONTEXT.md and 14-UI-SPEC.md but no command/agent invocation form is documented locally.
   - Recommendation: Plan 14-01 documents the invocation form. May be `/gsd-ui-check <surface>` or via an agent spawn — assume orchestrator-spawned subagent until confirmed.

4. **Should the wizard step-strip retoning (CONTEXT Area 2 wizard wave §Structural deltas) deletion of `step-indicator.ts` legacy refs happen in wave 1 OR be split into a step-strip-only task?**
   - What we know: Wave 1 is "wizard surface", which includes step-indicator. UI-SPEC §Surface 1 component list includes `components/step-indicator.ts` — see step-strip retone above.
   - Recommendation: Single wave 1 plan covers all 16 wizard files including step-indicator. The step-strip is small (7 legacy refs).

---

## Sources

### Primary (HIGH confidence)
- **Local files (codebase grep):** `tauri/ui/src/tokens.css` (current), `tauri/ui/src/**/*.{ts,css,html}` (272-ref inventory), `tauri/ui/LICENSE-3RD-PARTY.md`, `tauri/ui/vitest.config.ts`, `tauri/ui/package.json`, `scripts/check_ipc_schema.py`, `mocks/vibemix-direction-final.html`.
- **Local planning artifacts:** `14-CONTEXT.md`, `14-UI-SPEC.md`, `HANDOFF-cdj-whisper-v5-ui-migration.md`, `REQUIREMENTS.md`, `STATE.md`, `CLAUDE.md`, `.claude/skills/frontend-enforcement/SKILL.md`.

### Secondary (MEDIUM confidence — official docs + MDN, verified via WebSearch)
- [MDN -webkit-mask-composite](https://developer.mozilla.org/en-US/docs/Web/CSS/-webkit-mask-composite) — `xor` ↔ `exclude` mapping; cross-engine support.
- [MDN mask-composite](https://developer.mozilla.org/en-US/docs/Web/CSS/mask-composite) — standard property reference.
- [MDN prefers-reduced-motion](https://developer.mozilla.org/en-US/docs/Web/CSS/@media/prefers-reduced-motion) — accessibility media feature.
- [Tauri v2 Webview Versions](https://v2.tauri.app/reference/webview-versions/) — WebView2 (Windows) + WKWebView (macOS) versioning.
- [JetBrains Mono GitHub releases](https://github.com/JetBrains/JetBrainsMono) — official font + OFL-1.1 license.
- [Google Fonts Saira](https://fonts.google.com/specimen/Saira) — variable font with wdth + wght axes.

### Tertiary (MEDIUM-LOW confidence — community + GitHub issues, verified for direction not specifics)
- [Tauri issue #10064 — backdrop blur not working with transparent window](https://github.com/tauri-apps/tauri/issues/10064) — confirms WebView2 transparent-window bug.
- [Tauri issue #12437 — inconsistent backdrop-blur on transparent window](https://github.com/tauri-apps/tauri/issues/12437) — additional context on the same bug.
- [Tauri issue #6876 — transparent + backdrop-filter cannot be effective when move window](https://github.com/tauri-apps/tauri/issues/6876) — workaround context.
- [Why I Chose Tauri v2 for a Desktop Overlay in 2026 — Manasight blog](https://blog.manasight.gg/why-i-chose-tauri-v2-for-a-desktop-overlay/) — production case study citing the bug.
- [tauri-plugin-macos-fps](https://github.com/userFRM/tauri-plugin-macos-fps) — reference for FPS counter widget pattern (DO NOT install).
- [Fontsource — saira](https://fontsource.org/fonts/saira) — Fontsource distribution channel for variable WOFF2.

---

## Metadata

**Confidence breakdown:**
- Standard stack: **HIGH** — verified against existing `tauri/ui/package.json`; no new deps.
- Codebase consumer inventory: **HIGH** — direct grep against current `tauri/ui/src/` on commit `0615344`.
- Architecture patterns: **HIGH** — locked by `14-UI-SPEC.md` + `tokens.css` already on disk.
- Pitfalls: **HIGH for #2 (premature shim del), #4 (mask-composite dual property), #7 (col-mascot grid), #8 (gate scope)**; **MEDIUM for #1 (WebView2 backdrop bug)** — verified via GitHub issues but not on Phase 14's specific overlay setup; **MEDIUM for #3 (variable font axis support)** — verified for current versions, but Phase 20 Windows fresh-VM is the live confirmation.
- Validation Architecture: **HIGH** — vitest + jsdom already configured.
- Backdrop-filter perf procedure: **MEDIUM** — pragmatic Phase 14 procedure; rigorous numbers come in Phase 16.
- WOFF2 vendoring procedure: **HIGH** — standard `@font-face` declaration; verified font sources.
- Animated border validation: **MEDIUM** — engine support is HIGH; specific Tauri overlay window combo is `[ASSUMED]` until wave 4 verification.

**Research date:** 2026-05-13
**Valid until:** 2026-06-13 (30 days — stable phase; Tauri webview engines + font sources unlikely to change)

---

## Ready for Planning

Research complete. Planner can now:
1. Create Plan 14-01: ROADMAP / REQUIREMENTS typeface reconciliation + first surface (wizard wave 1 prep).
2. Create Plan 14-02: Wizard surface migration (225 legacy refs across 16 files).
3. Create Plan 14-03: Live session UI surface migration (25 legacy refs across 6 files) + Settings → Performance "Lighter blur" toggle wiring.
4. Create Plan 14-04: Settings drawer surface migration (15 legacy refs across 5 files).
5. Create Plan 14-05: Mascot overlay window chrome surface migration (6 legacy refs in 1 file) — wave 4.
6. Create Plan 14-06: Subtractive commit — shim delete + font swap + pre-commit gate + LICENSE-3RD-PARTY.md update + Vite cache invalidation + backdrop-filter perf verification (wave 5 close).
