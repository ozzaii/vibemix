# Phase 14: CDJ Whisper v5 Migration + Polish - Context

**Gathered:** 2026-05-13
**Status:** Ready for planning
**Mode:** Smart discuss (autonomous — recommended answers auto-accepted; one ROADMAP/mock typeface conflict explicitly reconciled)

<domain>
## Phase Boundary

Migrate every shipping UI surface (wizard, live session UI, settings drawer, mascot overlay frame) from the Phase 11/12 FL-Studio retro-tactile token vocabulary to the CDJ Whisper v5 visual contract (`mocks/vibemix-direction-final.html`). The prototype token swap is already on disk (commit `0615344`) with a backward-compat shim flipping `--phosphor*` / `--brushed-*` / `--bezel-*` / `--panel*` / `--groove` / `--ink*` / `--col-mascot` onto v5 primitives via cascade. This phase audits and refactors at the component level so each consumer reads v5 primitives directly, deletes the shim and the legacy @font-face block, runs `gsd-ui-checker` + `gsd-ui-auditor` per surface until both gates pass, and ships an animated-border surround composed with the Phase 13 mascot overlay window. Explicit visual-quality gate **before** Phase 16's hallucination verification — Phase 14 is not a final-week sweep.

</domain>

<decisions>
## Implementation Decisions

### Area 1 — Migration Sequencing
- Surface-by-surface, one plan per surface (mirrors Phase 12 wave structure). Stable ui-checker baseline captured before moving to next surface.
- Order: **wizard → live session UI → settings drawer → mascot overlay frame**. Wizard first (smallest token surface, structural HTML only — validates the migration before tackling per-frame meters). Mascot last because Phase 13 just shipped the renderer and the Meshy material fix (commit `2b608b6`) just landed.
- Per surface: refactor consumers first (read v5 primitives directly), commit the surface as a refactor. Backward-compat shim is **not** touched until every surface is migrated. Final subtractive commit deletes the shim wholesale.
- POC files (`cohost*.py`, `cohost.streaming.py.bak`, `mascot.html`, `mocks/*`) are untouchable per the project's "POC = reference, devour it" rule. Only `tauri/ui/src/` is in scope.

### Area 2 — Shim Removal Surgery
- One subtractive commit at the end of the phase deletes all backward-compat aliases. Single revert if regression slips through; clean diff for ui-checker pre/post.
- Pre-deletion grep gate (must return zero hits before the shim-delete commit lands): `grep -rnE '(--(phosphor|brushed-(hi|lo)|bezel-[123]|panel(-lift|-deep)?|groove|ink(-(dim|deep|engraved))?|charcoal|col-mascot))\b' tauri/ui/src/ --include='*.ts' --include='*.tsx' --include='*.css' --include='*.html'`. Wired into a pre-commit hook for the shim-delete commit only.
- `--col-mascot: 256px` is **deleted**. Wizard collapses to single-column per the inline TODO already in `tokens.css`. Mascot lives as an overlay window per Phase 13 — never embedded.
- Legacy @font-face declarations (Workbench, DM Mono, DSEG7, Caveat) removed once grep confirms zero string-keyed usages. `tauri/ui/public/fonts/Workbench-Regular.woff2`, `DMMono-{Regular,Medium}.woff2`, `DSEG7Classic-Bold.woff2`, `Caveat-Bold.woff2` deleted. `tauri/ui/LICENSE-3RD-PARTY.md` updated to drop the four families and add Saira + JetBrains Mono SHA-256 attestations.
- Vendored Saira + JetBrains Mono as WOFF2 (replaces the prototype's remote `@import` from `fonts.googleapis.com`). One-click-install rule: offline-friendly distribution.

### Area 3 — Critique Loop Discipline
- Iteration cap: **3 cycles** of `ui-checker → fix → ui-auditor` per surface. After 3, surface is logged as polish debt in the polish log and escalated to Kaan (matches autonomous gap-closure 1-retry rule, slightly more permissive for visual polish).
- Polish log: `.planning/phases/14-cdj-whisper-v5-migration-polish/14-POLISH-LOG.md`. Markdown table with `surface | cycle | ui-checker output ref | ui-auditor output ref | fix commit SHA | status`. Executor appends per cycle.
- "Matches the mock" acceptance: numeric — `gsd-ui-checker` zero findings AND `gsd-ui-auditor` three audits green (20/80 dominance, no-faux-3D-bevel, typography pairing) AND side-by-side screenshot pair (live surface vs. corresponding mock section) attached to each plan summary.
- Backdrop-filter perf fallback shipped now, not deferred to Phase 16:
  - Add `--blur-glass-perf` token aliasing the standard `--blur-glass` value
  - Add `@media (prefers-reduced-motion: reduce)` override that swaps `--blur-glass` to `blur(16px)` (drops saturate)
  - Add a runtime toggle `Settings → Performance → "Lighter blur"` writing a `data-blur-perf="on"` attribute on `<html>` that swaps to the lighter blur even without `prefers-reduced-motion`
  - Tested on Kaan's M-series Mac and a Windows non-dev machine before Phase 14 closes (the Windows rehearsal can borrow from Phase 20 plan if needed)

### Area 4 — Copy Purge + Typeface Reconciliation
- Scrub scope: chrome strings only — text rendered in `tauri/ui/src/wizard/`, `tauri/ui/src/session/`, `tauri/ui/src/settings/`, `tauri/ui/src/mascot/` UIs. Excludes: code comments, console logs, error messages, planning docs, prompt templates (Phase 10's scope), Gemini transcript content (runtime, not chrome).
- Purge dictionary (case-insensitive grep gate on `tauri/ui/src/**/*.{ts,tsx}` string literals): `brushed`, `anodised`, `phosphor`, `retro-futurist`, `knob/fader physics`, `tactile` (in hardware-vocabulary context only — `tactile feedback` referring to actual UI behavior is allowed if it survives a manual review).
- Voice for new chrome copy: Pioneer-grade restraint. State words over sentences. "Listening." over "Listening to your set." "Ready" over "All systems go." Match the v5 mock's vocabulary.
- **Typeface decision (overrides ROADMAP success criterion #4):** The v5 mock and HANDOFF doc explicitly use **Saira (variable wdth + wght) + JetBrains Mono**. The ROADMAP text "Geist for chrome + Fraunces for headlines" is stale pre-v5-prototype language. The mock is named as the visual contract — mock wins. `gsd-ui-auditor` typography pairing audit is reinterpreted to enforce **Saira + JetBrains Mono, no Inter / no system-ui / no Geist / no Fraunces**. ROADMAP success-criterion text updated in this phase's first plan.

### Claude's Discretion
- Animation timing for the slow amber border sweep — `--motion-border-sweep: 22s` is the v5 default; component plans may adjust per-surface if perceptual review flags it.
- Z-index layering of the animated border within each glass panel — first child, position absolute, inset 0 per the mock pattern; component plans pick the masking technique that survives existing layout.
- Per-surface micro-decisions (hover states, focus ring intensity, etc.) at executor's discretion provided they consume v5 primitives only.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `tauri/ui/src/tokens.css` — v5 tokens already defined (`--void-{1..4}`, `--glass-{1..3}`, `--silk{,-65,-40,-22,-12}`, `--amber{,-deep,-pale,-22,-40,-65}`, `--rave-{magenta,pink,cyan,purple,teal}`, `--glow-{faint,soft,strong}`, `--type-{display,body,mono}`, `--blur-glass{,-light,-display}`, `--motion-border-sweep`) — plus the backward-compat shim that needs deletion at end.
- HANDOFF doc supplies the canonical `.border-anim` snippet (conic-gradient + mask-composite) — drop as first child of each glass panel.
- Phase 12 component pattern: pure-function components with `registerStyle()` singleton at module load + zero hardcoded hex. Established convention to keep.
- Phase 11 wizard structure: `tauri/ui/src/wizard/*` already structured for `--col-mascot` removal (single-column collapse is a layout adjustment, not a rewrite).

### Established Patterns
- All components consume CSS custom properties via `var(--token)` — never hex literals (CONVENTIONS guardrail; only `tokens.css` may contain `#xxxxxx`).
- `registerStyle()` singleton pattern (`tauri/ui/src/session/`) — adds a `<style>` block once per module load. Per-component CSS strings reference the same tokens.
- Tauri Rust glue + Python sidecar are stable — Phase 14 is pure presentation; no IPC schema changes, no sidecar changes, no Rust changes expected.
- `npm run check:ipc` + `cargo check` + `cargo test` + pytest gates are stable from Phase 12 — Phase 14 must keep all green.

### Integration Points
- `tauri/ui/src/main.ts` — boot path renders wizard or session shell. Untouched by Phase 14.
- `tauri/ui/src/wizard/index.ts` + `tauri/ui/src/wizard/views/*.ts` — wizard surface entry point.
- `tauri/ui/src/session/SessionLayout.ts` — live session UI composer. Each meter/component is a pure function.
- `tauri/ui/src/settings/index.ts` (or equivalent) — drawer composer.
- `tauri/ui/src/mascot/renderer.ts` — already up-to-date with Meshy material fix (commit `2b608b6`); the v5 frame surround is applied to the **overlay window chrome**, not the Three.js scene itself.

</code_context>

<specifics>
## Specific Ideas

- **Visual contract baseline:** `mocks/vibemix-direction-final.html` (CDJ Whisper v5 — 1481 lines, includes typography sample, system metrics, the live session mock, settings mock, wizard mock). Every surface gets a side-by-side screenshot comparison.
- **Animated border snippet:** Lift the `.border-anim` conic-gradient pattern from the HANDOFF doc (`.planning/HANDOFF-cdj-whisper-v5-ui-migration.md` lines 100–110). Surround applied to: every glass panel root in wizard, the session-UI panel, the settings drawer, and the mascot overlay window frame.
- **Mascot overlay v5 framing:** Animated-border surround applied to the **Tauri overlay window chrome** (around the transparent mascot canvas), not to the Three.js scene. Mood swap (hype-man / teacher / coach) keeps the same v5 amber accent — moods differ in TTS voice + animation clip + prompt vocabulary, not in chrome color.
- **`mocks/vibemix-direction-explorations.html`** is historical-only — do not regression-test against it.
- **Prototype on disk (commit `0615344`)** is treated as Wave 0 of this phase — already committed, already validated visually. Phase 14 picks up at component-level audit.
- **Saira variable-axis usage:** v5 mock uses `wdth` (width) + `wght` (weight) axes. Display text = `wdth 82, wght 700, UPPERCASE`. Headline = `wdth 85, wght 600, UPPERCASE`. Body = `wdth 100, wght 400`. Silkscreen labels = `wdth 85-90, wght 500, 9-10px, 0.18em tracking, UPPERCASE`. Numeric data = JetBrains Mono `tabular-nums, 11-64px range`.
- **`frontend-enforcement` skill** auto-loads on UI-touching agents. When it conflicts with CDJ Whisper v5, **CDJ Whisper wins** per `[[project_visual_direction_cdj_whisper]]` project-local memory override (HANDOFF watchout #3).
- **Phase 11/12 deferred UAT items** (live UI ≥30fps, mid-session hot-reload, push-to-mute drains queue, MIDI hot-unplug, etc.) are **out of scope for Phase 14** — they're Kaan's-rig UAT for Phase 16. Phase 14 is visual contract only.

</specifics>

<deferred>
## Deferred Ideas

- **Performance profiling deep-dive** — Phase 14 ships the `--blur-glass-perf` fallback toggle but the actual per-machine perf characterization (FPS during 60-min session) is Phase 16's measured-stutter scope. Phase 14 verifies the toggle works, Phase 16 measures.
- **Mascot mood-specific glass tinting** — could imagine the glass alpha shifting subtly per mood (teacher = cleaner, hype-man = warmer rave-ambient). Not part of the v5 contract; deferred to a future polish pass.
- **Animated-border per-surface variation** — every panel gets the same 22s sweep in v5. A future revision could speed it up on the mascot frame during high-energy events. Not scoped here.
- **Settings → Performance panel beyond "Lighter blur"** — only that one toggle is shipped this phase; other perf knobs (anim disable, particle disable) deferred.
- **Dark/light mode** — v5 is intentionally one-mode (deep dark CDJ booth aesthetic). No light mode shipped or planned.

</deferred>
