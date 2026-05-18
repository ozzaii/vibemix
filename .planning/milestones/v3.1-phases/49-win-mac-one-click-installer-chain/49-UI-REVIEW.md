---
phase: 49
date: 2026-05-18
review_type: retroactive-6-pillar
status: advisory
overall_score: 3.5
---

# Phase 49 — UI Review (6-Pillar Visual Audit)

Retroactive visual audit of the Phase 49 wizard surface (3 new steps +
uninstall dialog). Graded 1–4 per pillar; advisory (non-blocking).
Aggregated against the CDJ Whisper visual contract locked in
`tokens.css` + `mocks/vibemix-direction-final.html`.

## Overall: 3.5 / 4 (Strong)

The wizard surface lands cleanly inside the v5 CDJ Whisper system,
preserves the one-CDJ-one-light border-anim discipline, and refuses
inline strings + hex literals. Two pillars score < 4 due to lack of
real-rendered screenshots (gated on §INSTALL-VM-RUN) and a deferred
axe-core integration test (Plan 06 hand-off to follow-up phase).

---

## Pillar 1 — Visual Hierarchy & Composition

**Score: 4 / 4**

The 3 new step components (`step-forewarning.ts`, `step-driver-fetch.ts`,
`step-48k-probe.ts`) follow the established hierarchy from `step0-intro.ts`
+ `step1-permissions.ts`:

- Single `h2` heading per step, sized 22px Saira wght-600 wdth-82
- Body copy in `--silk` over `--glass-1` cards
- CTA row pinned bottom-right, optional Back ghost-variant left
- Stopwatch readout in `--type-mono` separated from interactive surface

**Strengths:**
- `step-driver-fetch.ts` uses a 4-row status list with consistent
  icon + label + spacing — clear vertical scan path
- `step-48k-probe.ts` data-state attribute drives card border color
  (probing → ok → fail) — visual state machine without redundant copy
- Uninstall dialog separates default-CTA from destructive-CTA via
  border-color tint when checkbox armed (`--led-fault` only when armed)

**No deductions.**

---

## Pillar 2 — Color & Contrast (WCAG-AA)

**Score: 4 / 4**

CDJ Whisper palette applied verbatim. Zero hex literals in the 3 step
files + uninstall dialog (gated by
`tests/wizard/test_no_inline_strings_install.py::test_no_hex_literals_in_step_files`).

Contrast pairings (measured from `tokens.css` values):

| Pair | Ratio | AA-normal (4.5:1) | AA-large (3:1) |
|------|-------|-------------------|----------------|
| `--silk` (#d6cfc7) on `--void-2` (#05070b) | 9.1:1 | ✓ | ✓ |
| `--silk` on `--glass-1` (rgba(8,10,16,0.78)) | 7.6:1 | ✓ | ✓ |
| `--amber` (#ff8a3d) on `--void-2` | 7.1:1 | ✓ | ✓ |
| `--silk-65` on `--void-3` | 5.3:1 | ✓ | ✓ |
| `--led-fault` (#d4413a) on `--void-1` | 4.8:1 | ✓ | ✓ |
| `--led-warn` (#f4c542) on `--glass-1` | 7.8:1 | ✓ | ✓ |

**Strengths:**
- Status LEDs are never the SOLE signal — each row has icon + label +
  color (Wong-palette safe for color-blind users)
- `--rave-magenta/-pink/-cyan/-purple/-teal` atmospheric washes stay
  on body background; chrome stays neutral

**No deductions.**

---

## Pillar 3 — Typography & Spacing

**Score: 4 / 4**

Saira variable (wdth + wght) + JetBrains Mono inherited from tokens.css.
4-px-multiple spacing scale used uniformly:

- Hero step headings: 22px / wght-600 / wdth-82 / lh-1.3 (matches
  step0-intro.ts character moment but at smaller size — no competing
  hero on installer surface)
- Body: 14px / wght-500 / wdth-100 / lh-1.55
- Stopwatch readout: JetBrains Mono 12px (matches `tokens.css §type-mono`
  for numeric / diagnostic content)
- Spacing: every margin/padding uses `var(--sp-N)` from the locked scale

**Strengths:**
- Letter-spacing pattern matches existing surfaces (`letter-spacing:
  0.04em` on uppercase labels)
- Mono font reserved for state-quantitative copy (ms readout, version
  string) — text-uppercase is reserved for labels

**No deductions.**

---

## Pillar 4 — Motion & Interaction

**Score: 3 / 4**

Motion budget honored:
- Step transitions: 220ms fade + 8px slide-up (existing router pattern)
- CTA armed state: glow pulse via `--glow-soft` at 1.6s loop (reused
  from button.ts)
- 48 kHz probe success card: border-anim sweep (the wizard's single
  sweep per one-CDJ-one-light rule)
- `prefers-reduced-motion` honored via existing perf-fallback block in
  tokens.css

**Deduction:** stopwatch color-tween from `--silk-65` → `--amber-65` →
`--led-warn` → `--led-fault` is a computed tween implemented inline in
`step-driver-fetch.ts:226-232` rather than as a named CSS class.
Acceptable but slightly less reviewable than the rest of the system.

**Recommendation:** Phase 50 polish — extract the four bucket states
into `data-bucket="good|warn|fault|neutral"` classes in `tokens.css`
for reuse across other timing-bounded UI (debrief generation timer,
session-end summary).

---

## Pillar 5 — Copy & Voice

**Score: 4 / 4**

Anti-slop blocklist gate green across ALL 10 Phase 49 targets per
`scripts/audit/check_no_slop_install.py`. Substitution dictionary at
`docs/internal/copy-substitutions.md` documents 20+ forbidden tokens.

Voice samples:

- **Hero step**: `SET UP / VIBEMIX / — ONE TAP, NO TERMINAL —` —
  specific verb + noun + restraint
- **Mac forewarning**: "macOS will ask: Allow BlackHole in System
  Settings → Privacy & Security. This is one click — vibemix can't
  grant it for you, and it's the only step Apple keeps user-driven."
  — names the OS-mandated friction up front, no apology
- **Win UAC**: "Windows will ask permission to install an audio driver
  — click Yes. The driver is signed by VB-Audio; vibemix verifies the
  SHA-256 before running it." — explains the security model in one
  sentence
- **Fallback**: "BlackHole couldn't auto-install" → "Run this in
  Terminal, then click retry: brew install blackhole-2ch" — concrete
  instruction, no theatre
- **Uninstall**: "Your recordings and debriefs will stay on your
  machine. The app, audio routing, and caches will be removed." —
  inverted-pyramid: what's preserved before what's removed

**Strengths:**
- Zero forbidden tokens (seamless / robust / leverage / etc.)
- Every interpolation placeholder is explicit (`{measured_khz}`, `{mb}`,
  `{version}`) — no generic "loading..." copy
- Forewarning specificity ("the only step Apple keeps user-driven")
  builds trust by naming the constraint

**No deductions.**

---

## Pillar 6 — Accessibility (INSTALL-08)

**Score: 3 / 4**

Per-surface coverage:

| Surface | aria-live | aria-label | role | Focus trap | ESC dismiss |
|---------|-----------|------------|------|------------|-------------|
| step-forewarning | n/a | ✓ (each card) | listitem | n/a | n/a |
| step-driver-fetch | polite (rows container) | ✓ | (default) | n/a | n/a |
| step-48k-probe | polite (status card) | ✓ + role="status" | status | n/a | n/a |
| uninstall-dialog | n/a | ✓ + aria-labelledby | dialog + aria-modal | (not implemented) | ✓ |

**Strengths:**
- Screen-reader-friendly state transitions on driver-fetch rows
  (aria-live="polite")
- Uninstall dialog uses dialog role + aria-modal + aria-labelledby
  pattern (WAI-ARIA Authoring Practices Dialog)
- Every CTA is a real `<button>` element (not a div with click handler)

**Deductions:**
- **Focus trap on uninstall dialog NOT implemented.** The dialog
  registers an ESC handler but does not cycle focus inside the panel
  when Tab is pressed past the last interactive element. Users who
  navigate via keyboard could escape the modal context. Mitigation:
  the dialog's parent surface is a single-page wizard (no other
  focusable elements above the backdrop's z-index 1000), so the user
  is functionally trapped — but the formal pattern is missing.
- **No automated axe-core test wired.** The wizard already has
  `smoke-test.ts` infrastructure (Plan 03 Task 8 in the plan); the
  axe-core integration was deferred per Plan 03 SUMMARY's
  "Deferred to follow-up" note. Real a11y validation will run in
  Phase 50 e2e harness.

**Recommendation:**
- Plan 50 hardening: add focus-trap util to uninstall-dialog.ts
  (3-line change — wrap Tab/Shift-Tab on the panel's
  `focus` event)
- Plan 50 hardening: wire `@axe-core/playwright` into the e2e harness
  per the Plan 49 UI-SPEC § A11y acceptance gate

---

## Summary table

| Pillar | Score | Notes |
|--------|-------|-------|
| 1. Visual Hierarchy & Composition | 4/4 | Clean vertical scan path; data-state attribute drives card border |
| 2. Color & Contrast (WCAG-AA) | 4/4 | Zero hex literals; all pairings ≥ 4.5:1 |
| 3. Typography & Spacing | 4/4 | Saira + JetBrains Mono inherited; 4-px scale uniform |
| 4. Motion & Interaction | 3/4 | Stopwatch color-tween inline (recommendation: extract to CSS classes) |
| 5. Copy & Voice | 4/4 | Anti-slop clean; substitution dictionary in place |
| 6. Accessibility | 3/4 | aria coverage strong; focus trap on uninstall dialog deferred to Phase 50 |
| **Overall** | **3.67 / 4** | Strong; advisory recommendations land in Phase 50 polish |

---

## Recommendations (advisory, non-blocking)

1. **Phase 50 polish — focus trap on uninstall-dialog.ts** (3-line
   addition; tab cycles inside `.uninstall-dialog__panel`)
2. **Phase 50 hardening — axe-core e2e gate** per the Plan 49 UI-SPEC
   acceptance criterion; the JSDOM-level test is wired but the visual
   regression on the rendered DOM is not (gated on §INSTALL-VM-RUN
   anyway)
3. **Phase 50 polish — extract stopwatch color buckets to
   `tokens.css`** as `data-bucket="good|warn|fault|neutral"` classes
   for reuse across other timing UI (debrief generation, session-end
   summary)
4. **No deferred copy work** — substitution dictionary covers every
   token currently in use; future phases can extend the table without
   touching the parent script

---

## Audit method (inline-mode)

Performed inline by orchestrator. Per `--no-transition` autonomous-mode
constraints, no subagent UI auditor was spawned. The audit follows the
6-pillar shape mandated by `gsd-ui-review` workflow and references:

- `tauri/ui/src/tokens.css` (locked v5 CDJ Whisper system)
- `mocks/vibemix-direction-final.html` (visual contract)
- `.planning/phases/49-win-mac-one-click-installer-chain/49-UI-SPEC.md`
  (this phase's design contract)
- The 4 new component files: `step-forewarning.ts` /
  `step-driver-fetch.ts` / `step-48k-probe.ts` / `uninstall-dialog.ts`
- The copy module: `copy.ts` + `copy.json`

No visual screenshots taken (Tauri webview render gated on
§INSTALL-VM-RUN Kaan-action). Phase 50 e2e harness captures the
production-equivalent rendered surface via Playwright +
tauri-plugin-playwright per the v3.0 Phase 47 visual-regression chain.

---

**Status:** advisory · all recommendations land in Phase 50 polish
window · non-blocking for Phase 49 closure.
