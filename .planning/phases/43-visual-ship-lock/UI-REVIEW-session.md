---
surface: session
entry: tauri/ui/src/session/SessionLayout.ts
owner_plan: 43-02
seeded_by: 43-01
audited_at: 2026-05-16
status: HIGH-findings-open
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

### HIGH findings

**[H-01]** `tauri/ui/src/session/components/rocker.ts:70` — `.vmx-rocker__seg:hover`
mutates colour only (`color: var(--silk)`); **no `--glow-faint` token applied**.
The rocker segments are the primary interactive control in the persona panel
(BEG/INT/PRO + HYPE/TEACH/COACH) — without a glow on hover the affordance
disappears against the silk-22 frame, breaking the VIS-02 hover-coverage
contract for every `[data-interactive]` / `<button>` / `[role="button"]`
element on the surface.
**Remediation:** add `box-shadow: var(--glow-faint);` to the `:hover` rule.
**Owner:** 43-02 (VIS-02 hover-state sweep)

**[H-02]** `tauri/ui/src/session/components/titlebar.ts:154` —
`.vmx-titlebar__settings:hover` carries colour + border-colour pokes only;
**no `--glow-faint` token applied**. Critique pass 2 (2026-05-14) inline note
admits the gear button was deliberately detuned to avoid out-shouting LIVE;
the fix overshot — there is now zero glow signal on hover, leaving the
button feeling dead under cursor. Same VIS-02 contract miss as H-01.
**Remediation:** add a damped `box-shadow: var(--glow-faint);` (or a half-
intensity variant if one is added to `tokens.css`) so the gear acknowledges
the cursor without competing with LIVE.
**Owner:** 43-02 (VIS-02 hover-state sweep)

**[H-03]** `tauri/ui/src/session/components/meter.ts:34-164` — the meter
renders as a **smooth amber gradient with continuous opacity transitions**
(see the `.vmx-meter__seg` rule at line 59 — `flex: 1` body + linear-gradient
fills per zone). The CDJ Whisper visual contract calls for a hardware-LED-
strip render: discrete 12-segment bars with no gradient between segments,
amber peak-hold lozenge with 1.2s decay, silk-12 minor grid lines every Nth
segment. The current 16-segment flex-fill design renders aesthetically as a
web-app gradient meter, not a Pioneer-CDJ hardware LED. Today this is the
single most-visceral CDJ-Whisper signal on the surface — getting it wrong
breaks the brand promise of "real DJ friend, not generic AI slop".
**Remediation:** Plan 43-04 (VIS-03) replaces the gradient with the LED-strip
+ peak-hold + silk-grid render. Tracked as HIGH here because closure-plan
43-02 must NOT ship the session surface as polished while the meter still
renders as a gradient — the audit loop blocks until 43-04 lands.
**Owner:** 43-04 (VIS-03 meter rebuild) — but the HIGH **gates 43-02 ship**

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

**[M-02]** `tauri/ui/src/session/components/picker.ts:59,219` —
`.vmx-picker__row:hover` and `.vmx-picker__opt:hover` carry hover treatments,
but inspection of the dropdown options shows the **opt hover applies
`var(--glow-faint)` at line 235 inside the active variant only** — the
non-active hover state lacks the glow. Visually inconsistent with the row
trigger which DOES gain a faint glow on hover. Confuses the
recognition-over-recall pattern (H6) when a user is scanning the dropdown.
**Remediation:** apply `--glow-faint` to the inactive `:hover` state too;
keep the deeper `--glow-soft` for the active row only.
**Owner:** 43-02 (VIS-02 hover-state sweep)

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
