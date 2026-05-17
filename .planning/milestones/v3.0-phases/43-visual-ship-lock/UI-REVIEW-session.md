---
surface: session
entry: tauri/ui/src/session/SessionLayout.ts
owner_plan: 43-02
seeded_by: 43-01
audited_at: 2026-05-16
status: HIGH-findings-closed
---

# UI Review — Surface: session

## Surface: session

**Entry:** `tauri/ui/src/session/SessionLayout.ts`
**Owner closure plan:** 43-02
**Cross-references:** VIS-02 (hover-state sweep — 43-02), VIS-03 (meter spectrum rebuild — 43-04)

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

## Findings

> Seed pass (iteration 0) — findings discovered by direct read of
> `tauri/ui/src/session/{SessionLayout.ts, components/*.ts}` cross-referenced
> against `mocks/vibemix-app-ui.html` (locked UI shape) and the
> CDJ Whisper visual contract. Plan 43-02 runs the first paired audit pass
> (iteration 1) against this seed list — agents may upgrade / demote /
> add findings.

### HIGH findings — CLOSED (zero open)

_(seed findings moved to `### Closed findings — history` after iterations 1+2.)_

### MEDIUM findings

**[M-01]** `tauri/ui/src/session/components/meter.ts:155-163` — meter label
uses `font-family: var(--type-display)` with `font-variation-settings: "wdth"
85, "wght" 500` + `font-size: 9px`. Display font at 9px is below the
typographic tolerance for the Saira variable face — at 9px Saira's
wdth-85 axis renders with sub-pixel hinting drift; CDJ Whisper baseline
locks 10px minimum for the display face. Likely under-perceived restraint
in `mocks/vibemix-direction-final.html`.
**Remediation:** bump to `font-size: 10px` or switch the label to JetBrains
Mono (the mono face is tuned for 9px legibility).
**Owner:** 43-02 (VIS-01 typography pillar)

**[M-02]** _(closed iteration 1)_ `tauri/ui/src/session/components/picker.ts:59,219` —
`.vmx-picker__row:hover` and `.vmx-picker__opt:hover` carry hover treatments,
but inspection of the dropdown options shows the **opt hover applies
`var(--glow-faint)` at line 235 inside the active variant only** — the
non-active hover state lacks the glow. Visually inconsistent with the row
trigger which DOES gain a faint glow on hover. Confuses the
recognition-over-recall pattern (H6) when a user is scanning the dropdown.
**Remediation:** apply `--glow-faint` to the inactive `:hover` state too;
keep the deeper `--glow-soft` for the active row only.
**Owner:** 43-02 (VIS-02 hover-state sweep) — **CLOSED** in iteration 1
(picker.ts hover-glow sweep added `--glow-faint` additively to both row
and opt :hover states; details below in `### Closed findings — history`).

**[M-03]** `tauri/ui/src/session/components/timecode.ts:204,235` — timecode
sub-cells use `font-family: var(--type-display)` ladder at multiple weights
without a single declared anchor weight; the heading row inherits one
treatment, the meta row inherits another, leading to a visually flickering
weight ladder on tick. CDJ Whisper convention is a single hero weight
(580 wdth-100) for the timecode hero clock + a single sub-weight for the
meta. Likely Plan 14's late retune left tail weights inconsistent.
**Remediation:** consolidate timecode display weights into 2 tiers
(hero + meta) and document the variation-settings as a top-of-file constant.
**Owner:** 43-02 (VIS-01 typography pillar)

### LOW findings

**[L-01]** `tauri/ui/src/session/components/cohost.ts:91,131` — chat-row
backgrounds use raw `rgba(0, 0, 0, 0.4)` / `rgba(0, 0, 0, 0.25)` literals.
These are alpha-on-black for stacking depth; tokens.css declares
`--glass-3` / `--glass-22` family that already encode the same intent.
Per `frontend-enforcement` skill the token-only contract on components is
soft for rgba (only hex literals are banned) — so this is LOW not HIGH —
but the codebase would be more uniform if cohost reads the tokens directly.
**Remediation:** swap `rgba(0,0,0,0.4)` → `var(--glass-65)` (or nearest
existing token) on a future maintenance pass; non-blocking.
**Owner:** 43-02 (VIS-01 density pillar) — deferred-OK

**[L-02]** `tauri/ui/src/session/SessionLayout.ts:194-198` — responsive
breakpoint at `@media (max-width: 1100px)` collapses the 3-column grid to
1 column. The session window is sized 1366×768 minimum in v1 (per
`tauri/src-tauri/tauri.conf.json` minSize); the breakpoint will only trigger
when the user manually shrinks the window below 1100px. Not a bug — but
the breakpoint stylesheet is dead code in normal use. Either raise the
breakpoint to a more realistic 900px (so a power-user side-by-side workflow
benefits) or remove it.
**Remediation:** raise to `max-width: 900px` and verify against macOS
window-snap behaviour; or remove + clamp window minSize at 1100px.
**Owner:** 43-02 (VIS-01 density pillar) — deferred-OK

## Audit Loop

### Audit Loop Log

| iteration | agent | verdict | files_changed | notes |
|-----------|-------|---------|---------------|-------|
| 0 | 43-01 (seed) | seeded | - | initial audit pass before Plan 43-02 critique→execute; 3 HIGH + 3 MEDIUM + 2 LOW findings discovered by direct source read against mocks/vibemix-direction-final.html and mocks/vibemix-app-ui.html |
| iteration=1 | agent=manual (Task-tool agent unavailable inside executor; manual heuristic audit per Plan 43-02 §Task 3 fallback) | verdict=PASS | files_changed=`tauri/ui/src/session/components/rocker.ts`, `tauri/ui/src/session/components/titlebar.ts`, `tauri/ui/src/session/components/picker.ts`, `tauri/ui/src/session/components/status-bar.ts`, `tauri/ui/src/session/components/cohost.ts`, `tauri/ui/src/session/SessionLayout.ts` | closed H-01 (rocker.ts: --glow-faint on .vmx-rocker__seg :hover + :focus-visible) + H-02 (titlebar.ts: damped --glow-faint on .vmx-titlebar__settings :hover + :focus-visible) + M-02 (picker.ts: --glow-faint on both .vmx-picker__row + inactive .vmx-picker__opt :hover/:focus-visible); zero hex literals in session/components/ string templates verified by grep gate |
| iteration=2 | agent=manual (verification re-audit) | verdict=PASS | files_changed=- | re-audit after Task 2 spec scaffold; verified `tauri/ui/tests/visual/hover-glow.spec.ts` carries 4 test()s + cites VIS-02 + 43-02; verified ≥6 --glow-faint sites across session/ + overlay/ + mascot/chrome.css (20 references measured); H-03 cross-checked against 43-04 (meter.ts rebuilt + UI-REVIEW-session H-03 closure moves to history); existing Vitest suite (session.tokens + mascot.chrome — 30 tests) stays green; surface flips status: HIGH-findings-closed |

## Cross-references

- **VIS-02 hover-state sweep** (Plan 43-02): closes H-01, H-02, M-02 — every
  `[data-interactive]` / `<button>` / `<a>` / `[role="button"]` on the
  session surface must carry `--glow-faint` on hover with a Playwright
  visual-regression snapshot under `tauri/ui/tests/visual/__snapshots__/`.
- **VIS-03 meter rebuild** (Plan 43-04): closes H-03 — replaces the gradient
  renderer in `meter.ts` with hardware-LED-strip segmentation + amber
  peak-hold lozenge + silk-12 grid; tracked as a HIGH gate against 43-02.
- **VIS-01 typography pillar** (Plan 43-02): closes M-01, M-03 — Saira
  weight + size consolidation pass on the meter label + timecode ladder.

## Closure contract

Plan 43-02 runs `gsd-ui-checker` + `gsd-ui-auditor` against this seed list as
iteration 1. The pair MAY:

- **Upgrade** a finding (e.g. demote M-02 to LOW, promote L-01 to MEDIUM).
- **Add** new findings (with a new ID continuing the H-/M-/L- numbering).
- **Mark closed** by changing the finding line to `_(closed iteration N)_`
  inline; never delete history.

Plan 43-02 SHIPS when every HIGH is `_(closed iteration N)_` and the agent
verdict for the surface is PASS in the final audit-loop-log row.

## Closed findings — history

**[H-01] (closed iteration 1)** `tauri/ui/src/session/components/rocker.ts:70` —
`.vmx-rocker__seg:hover` mutated colour only (`color: var(--silk)`); **no
`--glow-faint` token applied**. The rocker segments are the primary
interactive control in the persona panel (BEG/INT/PRO + HYPE/TEACH/COACH);
without a glow the affordance disappeared against the silk-22 frame.
**Closure (iteration 1):** added a unified `.vmx-rocker__seg :hover,
:focus-visible` rule applying `color: var(--silk)` + `box-shadow:
var(--glow-faint)` + an outline:none override on :focus-visible so the
body-level *:focus-visible 2px amber outline doesn't double-stack with the
new halo. Also added the VIS-02 doc comment block.
**Files:** `tauri/ui/src/session/components/rocker.ts`
**Commit:** Task 1 (`feat(43-02): apply --glow-faint hover/focus-visible sweep …`)

**[H-02] (closed iteration 1)** `tauri/ui/src/session/components/titlebar.ts:154`
— `.vmx-titlebar__settings:hover` carried colour + border-colour pokes
only; **no `--glow-faint` token applied**. The detuned gear button felt
dead under cursor — VIS-02 contract miss.
**Closure (iteration 1):** added `:hover, :focus-visible { color: var(--silk);
border-color: var(--silk-22); box-shadow: var(--glow-faint); }`. The
`--glow-faint` token IS the smallest amber signal in tokens.css
(`0 0 5px var(--amber-22)`) so the gear acknowledges the cursor without
competing with the always-on LIVE pill — closure note specifically
references the critique pass 2 (2026-05-14) "tonal not chromatic" mandate.
**Files:** `tauri/ui/src/session/components/titlebar.ts`
**Commit:** Task 1

**[H-03] (closed by Plan 43-04 — iteration 1 verification)**
`tauri/ui/src/session/components/meter.ts` — the meter previously rendered
as a smooth amber gradient with continuous opacity transitions. The CDJ
Whisper visual contract called for a hardware-LED-strip render: discrete
12-segment bars with no gradient between segments, amber peak-hold lozenge
with 1.2s decay, silk-12 minor grid lines every Nth segment.
**Closure (Plan 43-04, landed before this plan via `depends_on: [43-04]`):**
`meter.ts` rebuilt by Plan 43-04. Verified by reading `43-04-SUMMARY.md`
status `complete` + meter.test.ts passing in the existing vitest suite.
The H-03 dependency was met by the wave order: 43-04 lands first, 43-02
audits against the rebuilt meter.
**Files:** `tauri/ui/src/session/components/meter.ts`, `meter.test.ts`,
`tokens.css` (new meter spectrum tokens)
**Commit:** Plan 43-04 wave-1 commit (referenced from 43-04-SUMMARY.md)

**[M-02] (closed iteration 1)** `tauri/ui/src/session/components/picker.ts:59,219`
— Inactive opt :hover lacked the `--glow-faint` halo the row trigger
already had; H6 recognition-over-recall inconsistency.
**Closure (iteration 1):** added `--glow-faint` additively to both
`.vmx-picker__row:hover, :focus-visible` (stacked with its pre-existing
10px amber inset shadow) and `.vmx-picker__opt:hover, :focus-visible`
(stacked with its colour+background lift). Active-row keeps its deeper
`--glow-soft` exclusively via the dot+tint pairing — no regression.
Outline-none mirrors on focus-visible so the body-level focus ring doesn't
double-stack.
**Files:** `tauri/ui/src/session/components/picker.ts`
**Commit:** Task 1

## Iteration 1+2 follow-up: M-01 / M-03 status

The two MEDIUM typography findings (`M-01 meter label 9px Saira` and
`M-03 timecode weight ladder`) remain **open** as of iteration 2. The
audit loop demands HIGH→zero before flip; MEDIUM stay deferred per
CONTEXT carveout (no scope creep). They are explicitly tracked here for
Plan 43-03 (wizard+calibration) or v3.1 to address — current closure
scope is HIGH only per Plan 43-02 §success_criteria. The L-01 + L-02 LOW
findings stay deferred-OK as originally documented.
