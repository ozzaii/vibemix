<phase>49</phase>
<phase_name>Win + Mac One-Click Installer Chain</phase_name>
<date>2026-05-18</date>
<mode>auto (gsd-autonomous fully) — single-pass cap</mode>

# Discussion Log

Auto-mode: every gray area selected; every question answered with the recommended option. Selections logged inline for audit.

## Area 1 — Companion script layout

**Q:** Where do the new companion fetch + audio config scripts live?
**Options:** `installer/companion/` sibling | `scripts/install/companion/` | inside Tauri sidecar bin
**Selected:** `installer/companion/` sibling (recommended per ARCHITECTURE.md § Feature 1; matches existing `installer/windows/` pattern)

## Area 2 — Driver fetch strategy

**Q:** Bundle vendor drivers vs post-install fetch from official URLs?
**Options:** Bundle (redistribute) | Post-install fetch with SHA-256 verify | Detect-only + manual guide
**Selected:** Post-install fetch with SHA-256 verify (recommended; bundle redistribution legal blocker per VB-Audio EULA and BlackHole licensing; bundle ceiling invariant)

## Area 3 — Companion signing chain

**Q:** Where in release.yml does companion script signing land?
**Options:** Reuse existing SIGN stage | New `companion-sign` stage between BUILD + SIGN | Skip signing
**Selected:** New `companion-sign` stage between BUILD + SIGN (recommended per ROADMAP P49 success criterion #4 + ARCHITECTURE data-flow)

## Area 4 — Wizard copy location

**Q:** Where do user-facing wizard strings live?
**Options:** Inline in React components | Single JSON file (`installer/companion/onboarding_copy.json`) | i18n string catalog
**Selected:** Single JSON file (recommended; one anti-slop grep target; localization-ready structure but en-only in v3.1)

## Area 5 — Copy substitutions dictionary

**Q:** Where does the vocabulary substitution dictionary live, and what's the initial vocabulary?
**Options:** New file `docs/internal/copy-substitutions.md` | Add to existing CLAUDE.md | Inline in anti-slop checker
**Selected:** New file `docs/internal/copy-substitutions.md` (recommended per ROADMAP P49 invariants; reusable across future phases). Initial vocabulary: seamless → one-tap, robust → tested, leverage → use, intuitive → clear, powerful → fast, delightful → good, AI-powered → Gemini-grounded, smart → responsive, deeply integrated forbidden, next-generation forbidden.

## Area 6 — Wizard step shape

**Q:** How many wizard steps and what shape?
**Options:** 2-card minimal | 4-card structured (Welcome / Forewarning / Driver fetch / 48 kHz probe) | 6-card multi-step
**Selected:** 4-card structured (recommended; covers INSTALL-03 forewarning + INSTALL-04 fetch + INSTALL-10 probe in clear ordering; CDJ Whisper restraint per memory `project_visual_direction_cdj_whisper`)

## Area 7 — Onboarding stopwatch IPC

**Q:** New IPC event or reuse existing `audio.probe.*` family?
**Options:** New `install.*` event family | Reuse `audio.probe.*` + add `auto_install_attempted` payload field | No IPC, log-only
**Selected:** Reuse `audio.probe.*` (recommended per ARCHITECTURE.md § Feature 1 MODIFIED components; preserves v3.0 IPC contract)

## Area 8 — Uninstall data preservation

**Q:** Does uninstall remove user library by default?
**Options:** Always remove all | Preserve by default + clean-uninstall opt-in | Always preserve
**Selected:** Preserve by default + clean-uninstall opt-in (recommended per INSTALL-07; matches user-data-residency norms; preserve library + debrief unless explicit opt-in)

## Area 9 — Fresh-VM matrix execution

**Q:** Real Tart VM execution in CI or scaffold-and-defer?
**Options:** Real Tart in CI (expensive) | Scaffold harness + defer real-run to §INSTALL-VM-RUN | No matrix
**Selected:** Scaffold harness + defer (recommended per ROADMAP P49 Kaan-action surface; CI runners cannot freely spawn Tart; SHIP-04 v3.0 was scoped identically)

## Area 10 — Plan count

**Q:** How many plans should the planner produce?
**Options:** 3 large plans | 6 focused plans | 10 plans (one per REQ-ID)
**Selected:** 6 focused plans (recommended; matches Phase 48 plan-count discipline; each plan ~1-2 REQ-IDs; minimizes blast radius per agent-stall lesson from Phase 47/48)

## Deferred ideas (captured, not in scope)

- VB-Audio OEM redistribution agreement (KAAN-ACTION-LEGAL §SHIP-CONTACT-VBAUDIO)
- i18n on wizard copy (v3.x backlog)
- Reduced Security Apple Silicon auto-reboot path (cannot auto-trigger Recovery Mode)
- Linux installer (excluded by PROJECT.md)
- Auto-update over installer flow (Tauri updater scaffolded but separate)
- Companion install telemetry beacon (v3.x backlog)

## Auto-mode pass cap

Single-pass complete. CONTEXT.md written; no second pass.
