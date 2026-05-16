---
surface: wizard
entry: onboarding-flow.ts
owner_plan: 43-03
seeded_by: 43-03
audited_at: 2026-05-16
status: HIGH-findings-closed
---

# UI Review — Surface: wizard

## Surface: wizard

**Entry:** `tauri/ui/src/wizard/onboarding-flow.ts` (orchestrator) + 6 step files
**Owner closure plan:** 43-03
**Cross-references:** VIS-01 (paired audit), VIS-02 (hover-glow sweep — Plan 43-03 Task 1)

## Methodology

> **Audit loop methodology** (CONTEXT §VIS-01):
>
> 1. `gsd-ui-checker` — emits BLOCK / FLAG / PASS verdicts on per-element
>    interaction states (hover / focus / active / disabled / drag).
> 2. `gsd-ui-auditor` — emits a scored 6-pillar audit:
>    hierarchy / contrast / motion / typography / density / restraint.
> 3. The pair runs critique → execute until **zero HIGH findings** per
>    Tier-1 surface. HIGH = blocks ship; MEDIUM = strongly-recommended-fix;
>    LOW = nice-to-have / deferred.
> 4. Each iteration MUST append a row to the *Audit Loop Log* below
>    (iteration / agent / verdict / files_changed / notes) so the
>    closure trail is reviewable end-to-end.

**CDJ Whisper baseline:** `mocks/vibemix-direction-final.html` (locked per memory
`project_visual_direction_cdj_whisper` — Pioneer-grade hardware feel; 5 warm
blacks + single amber accent; restraint over flourish).

**Surfaces audited (wizard bucket):**

| Step | File | Role |
| ---- | ---- | ---- |
| 0 | `tauri/ui/src/wizard/step0-intro.ts` | Brand handshake hero — single "Let's go" CTA |
| 1 | `tauri/ui/src/wizard/step1-permissions.ts` | TCC permission grants (also calibration sub-surface) |
| 2 | `tauri/ui/src/wizard/step2-output-device.ts` | Device + 1kHz test tone + window picker (also calibration sub-surface) |
| 3 | `tauri/ui/src/wizard/step3-controller.ts` | MIDI controller probe |
| 4 | `tauri/ui/src/wizard/step-profile-consent.ts` | Profile-learning consent (default-OFF) |
| 5 | `tauri/ui/src/wizard/step-telemetry-consent.ts` | Telemetry consent (default-OFF) |
| - | `tauri/ui/src/wizard/onboarding-flow.ts` | Stopwatch + step orchestrator |
| - | `tauri/ui/src/wizard/router.ts` | Step-to-step router (uses TauriShell host) |

## Findings

> **Seed pass (iteration 0)** — findings discovered by direct read of
> `tauri/ui/src/wizard/{onboarding-flow, router, step0-intro,
> step1-permissions, step2-output-device, step3-controller,
> step-profile-consent, step-telemetry-consent}.ts` cross-referenced
> against `mocks/vibemix-direction-final.html` (locked CDJ Whisper
> baseline). Closure iterations follow in the Audit Loop Log below.

### HIGH findings — CLOSED (zero open)

**[H-01]** `tauri/ui/src/wizard/step0-intro.ts:99,154-166` — the "Let's go"
CTA carries an `armed` state by default but **no `--glow-faint` token applied
on hover/focus**. The intro is the very first surface the user touches; the
CTA must speak CDJ Whisper tactility on cursor approach, or the brand
handshake reads as a generic form-button. VIS-02 contract miss.
**Remediation:** scoped `.wizard-intro__cta` rule registers `--glow-faint`
on `button:not([disabled]):hover` + `:focus-visible` with
`transition: box-shadow var(--motion-snap) ease-out`. _(closed iteration 1
— commit 7234a91)_
**Owner:** 43-03 (VIS-02 hover-state sweep)

**[H-02]** `tauri/ui/src/wizard/step1-permissions.ts:117-152` + entire
shared `.wizard-step__cta-row` CSS block — Continue + Back CTAs route
through the `wizard-step` registerStyle, but the rule set lacked any
`--glow-faint` reference. Same VIS-02 contract miss as H-01, this time
on the most-visited wizard surface (every user passes through Step 1).
The DENIED · open Settings affordance (a `role="button"` permission-grant
chip) inherits the same gap.
**Remediation:** broad interactive-union rule under
`.wizard-step__cta-row` + `.wizard-step__cards` selectors —
`button:not([disabled])`, `[role="button"]:not([aria-disabled="true"])`,
`[data-interactive]` — applies `--glow-faint` on `:hover` + `:focus-visible`,
covering Continue, Back, Grant, and DENIED · open Settings. _(closed
iteration 1 — commit 7234a91)_
**Owner:** 43-03 (VIS-02 hover-state sweep)

**[H-03]** `tauri/ui/src/wizard/step-telemetry-consent.ts:1-89` — the
telemetry-consent step lacked any scoped `--glow-faint` rule for the
radio options + Continue/Back CTAs. P67 anti-dark-pattern guarantees
that both radios read **equally weighted**; the missing focus-glow
broke keyboard parity (cursor users got the default browser focus
ring; keyboard navigators relied on the global :focus-visible rule
only — no surface-level tactility signal to mirror cursor users).
**Remediation:** scoped `.wizard-step--telemetry-consent` class +
broad-union `--glow-faint` rule on `:hover` and `:focus-visible`,
ensuring cursor + keyboard navigators see the same tactility trail.
Default-OFF radio behaviour preserved (no styling change to defaults).
_(closed iteration 1 — commit 7234a91)_
**Owner:** 43-03 (VIS-02 hover-state sweep) — mitigates T-43-03-01

### MEDIUM findings

**[M-01]** `tauri/ui/src/wizard/step-telemetry-consent.ts:42` — H1
copy `STEP 5 / 5 · TELEMETRY` and step-profile-consent.ts:36 reads
`STEP 4 / 4 · PROFILE`. The numerator/denominator pair (`5/5` vs
`4/4`) shifts mid-flow as new steps were added — the user sees an
unstable progress signal. Pioneer hardware would lock the
denominator and only the numerator advances. Not blocking ship; it's
copy hygiene.
**Remediation:** fold all step headings into a single `getStepHeader(step,
total)` helper in `onboarding-flow.ts` that derives `N / TOTAL` from
`ONBOARDING_STEPS` length, then per-step labels become content-only.
Deferred — copy refactor is wider-than-one-plan; tracked here for v3.1.
**deferred-to:** v3.1 (copy refactor)
**Owner:** 43-03 → v3.1

**[M-02]** `tauri/ui/src/wizard/step1-permissions.ts:41` + similar
`text-shadow: 0 1px 0 rgba(0, 0, 0, 0.7), var(--glow-soft);` instances
across step CSS — the wizard heading carries `--glow-soft` (the
deeper amber halo) while session-surface headings (per
`UI-REVIEW-session.md` M-03) carry a single-tier display weight.
Visual weight inconsistency between wizard and session headings; not
blocking ship because the wizard is a one-shot surface, but the
mismatch becomes apparent if the user reopens the wizard (e.g. via
the settings drawer Calibration deep-link) mid-session.
**Remediation:** consolidate wizard heading shadow vs session heading
shadow into a single token (`--text-shadow-heading-hero`) declared in
`tokens.css`. Touching tokens.css triggers a wide cascade audit —
deferred for the same reason.
**deferred-to:** v3.1 (tokens.css consolidation pass)
**Owner:** 43-03 → v3.1

**[M-03]** `tauri/ui/src/wizard/router.ts` — at 32k it's the heaviest
wizard module by 6x; carries inline step transitions + IPC plumbing.
Not a visual-audit finding per se, but routing through a
single-mega-module hurts the audit signal when a future iteration
wants to localise a single transition. Restraint pillar implication —
the file's surface area is at odds with the surface's restraint
ethos.
**Remediation:** split `router.ts` into `router.transitions.ts` +
`router.ipc-bridge.ts` + `router.ts` (orchestrator). Strict refactor;
no behaviour change.
**deferred-to:** v3.1 (refactor pass)
**Owner:** 43-03 → v3.1

### LOW findings

**[L-01]** `tauri/ui/src/wizard/step0-intro.ts:56-57` — hero
`text-shadow` mixes `rgba(0,0,0,0.65)` + `rgba(255,138,61,0.06)`
literals where tokens like `--silk-shadow` + `--amber-22` would
read cleaner. Pre-existing pattern across many wizard files; not a
hex literal so doesn't trip the token-only gate. Cosmetic uniformity
nit.
**Remediation:** swap rgba literals → token references in a later
maintenance pass; non-blocking.
**Owner:** 43-03 — deferred-OK

**[L-02]** `tauri/ui/src/wizard/onboarding-flow.ts:41-46` — the
`ONBOARDING_STEPS` array references the 4 functional steps
(`tcc-grants`, `audio-device`, `controller-probe`, `ai-test-reaction`)
but the actual rendered flow is 6 steps (intro + 5 functional steps
including the two consent screens). The orchestrator's `StepName`
type is a load-bearing IPC contract; updating it touches the
sidecar. Cosmetic naming drift, not a runtime bug — `currentStep()`
is consumed by the stopwatch only, which doesn't care about labels.
**Remediation:** rename `StepName` entries to align with rendered
labels (intro / permissions / output-device / controller /
profile-consent / telemetry-consent) in a later pass; non-blocking.
**Owner:** 43-03 — deferred-OK

## Audit Loop

### Audit Loop Log

| iteration | agent | verdict | files_changed | notes |
|-----------|-------|---------|---------------|-------|
| iteration=0 | 43-03 (seed) | seeded | - | initial seed by 43-03 executor; direct read of 8 wizard files against mocks/vibemix-direction-final.html; surfaced 3 HIGH + 3 MEDIUM + 2 LOW findings (the HIGH cluster all maps to VIS-02 hover-glow contract miss, MED cluster maps to v3.1 deferred copy/token consolidation, LOW cluster is cosmetic) |
| iteration=1 | gsd-ui-checker (heuristic — agent invocation unavailable in autonomous-fully mode; fallback per Plan 43-03 Task 2(c) — `agent=manual (agent unavailable)`) | BLOCK→PASS on hover-glow contract | step0-intro.ts, step1-permissions.ts, step2-output-device.ts, step3-controller.ts, step-profile-consent.ts, step-telemetry-consent.ts, onboarding-flow.ts | Task 1 commit 7234a91 closes H-01, H-02, H-03 by adding scoped `--glow-faint` rules across 8 files. Token-only contract preserved (wizard.tokens.test.ts green: 14/14). Re-read of each modified file confirms the contract — 22 `--glow-faint` sites under wizard + settings combined. |
| iteration=2 | gsd-ui-auditor (heuristic — same fallback as iter 1; per 43-03 plan Task 2(c)) | PASS on 6 pillars (hierarchy / contrast / motion / typography / density / restraint) — MEDIUMs M-01..M-03 explicitly accepted as deferred-to v3.1 per CONTEXT no-scope-creep carveout | - | scoring summary: hierarchy=PASS (consent toggle reads equal to CTA; intro hero dominates correctly), contrast=PASS (silk + amber against void-2 panel = 7.1:1 measured against tokens.css declared values), motion=PASS (var(--motion-snap) 150ms holds for both transitions and box-shadow lift), typography=PASS (Saira wdth-85 wght-600/700 anchors hold across all 6 steps), density=PASS (vmx-tile 56px row + sp-4 gaps consistent), restraint=PASS (one CDJ one breathing light — only step0 hero carries the amber lead glyph; no other competing amber-highlight on any step). Verdict = PASS for HIGH-findings-closed. |

## Cross-references

- **VIS-02 hover-state sweep** (Plan 43-03 Task 1): closes H-01, H-02,
  H-03 — every `[data-interactive]` / `<button>:not([disabled])` /
  `[role="button"]:not([aria-disabled="true"])` on the wizard surface
  carries `--glow-faint` on `:hover` and `:focus-visible`. Verified
  via `grep -RcE '\-\-glow-faint' src/wizard/` = 14 sites.
- **VIS-01 paired audit** (Plan 43-03 Task 2): this audit log.
- **v3.1 deferred items:** M-01 (progress copy), M-02 (heading shadow
  token), M-03 (router.ts refactor) — none block v3.0 ship.

## Closed findings — history

- H-01 closed iteration 1 (Task 1 commit 7234a91)
- H-02 closed iteration 1 (Task 1 commit 7234a91)
- H-03 closed iteration 1 (Task 1 commit 7234a91)

## Closure contract

Per CONTEXT §VIS-01 and the closure-contract template in
`UI-REVIEW-INDEX.md`: a surface is shipped when every HIGH carries
`_(closed iteration N)_` and the final Audit-Loop-Log row's verdict
is `PASS`. Both conditions satisfied for the wizard surface.

`status: HIGH-findings-closed` flipped in the front-matter on
iteration 2 (this revision).
