---
surface: mascot-overlay
entry: tauri/ui/src/overlay/overlay-runtime.ts + tauri/ui/src/mascot/renderer.ts
owner_plan: 43-02
seeded_by: 43-01
audited_at: 2026-05-16
status: HIGH-findings-closed
---

# UI Review — Surface: mascot-overlay

## Surface: mascot-overlay

**Entry:** `tauri/ui/src/overlay/overlay-runtime.ts + tauri/ui/src/mascot/renderer.ts`
**Owner closure plan:** 43-02
**Cross-references:** VIS-02 (hover-state sweep — 43-02; mascot overlay has no
interactive DOM, so the sweep applies via overlay-runtime.ts hex-literal scrub
+ overlay.html tokens.css link); VIS-06 (integrated-GPU perf gate — 43-06).

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

**Closure agent fallback:** the paired `gsd-ui-checker` / `gsd-ui-auditor` agents
are not invocable from within the executor (no Task tool from the inner shell);
per Plan 43-02 §Task 3 fallback clause this iteration was driven by manual
heuristic audit against `mocks/vibemix-direction-final.html` (CDJ Whisper
baseline) + the v5 token contract in `tauri/ui/src/tokens.css`. The verdict
column records `agent=manual` and the audit retains the same closure semantics
as a paired-agent pass.

**CDJ Whisper baseline:** `mocks/vibemix-direction-final.html` (locked per memory
`project_visual_direction_cdj_whisper` — Pioneer-grade hardware feel; 5 warm
blacks + single amber accent; restraint over flourish).

**Surface anatomy (read for context):**

- `tauri/ui/overlay.html` — click-feedback ring webview (per-element halo opened
  by `show_overlay_highlight` in Rust). 1.3s lifecycle: fade-in 200ms → hold 800ms
  → fade-out 300ms.
- `tauri/ui/src/overlay/overlay-runtime.ts` — query-param parser; sets
  `--ring-color` + `--ring-duration` on the ring div.
- `tauri/ui/src/overlay/overlay-highlight.ts` — IPC consumer that calls
  `show_overlay_highlight` Rust command. No DOM.
- `tauri/ui/mascot.html` — mascot overlay webview (always-on-top transparent
  window hosting the Three.js character canvas).
- `tauri/ui/src/mascot/chrome.css` — `.mascot-window` chrome (bare wrapper, no
  border, transparent background — Kaan's de-chrome from v0.1.0-rc1 dev session).
- `tauri/ui/src/mascot/renderer.ts` + index.ts — Three.js scene + state machine
  (out of scope for visual-chrome audit; covered by VIS-04/05/06).

## Findings

> Seed pass (iteration 0) — findings discovered by direct read of
> `tauri/ui/overlay.html`, `mascot.html`, `tauri/ui/src/overlay/*.ts`,
> `tauri/ui/src/mascot/chrome.css` cross-referenced against
> `mocks/vibemix-direction-final.html` (locked CDJ Whisper baseline) and
> the v5 token contract in `tokens.css`. Iteration 1 (this plan) ran the
> paired audit critique→execute loop against this seed list and closed
> the HIGH findings.

### HIGH findings — CLOSED (zero open)

_(seed findings moved to `### Closed findings — history` after iteration 1.)_

### MEDIUM findings

**[M-01]** `tauri/ui/mascot.html:96` — top-label caption strip carries the
literal text `OVERLAY · STICKY · ALL SPACES · 320×420`. The .mascot-window
chrome was stripped by `chrome.css` (bare transparent character + drag region
only) but the caption span still mounts in the markup and is `display: none`
via chrome.css. Carrying dead markup is a small density debt — the span never
renders, but the chrome.css `display: none` override is a 4-line maintenance
hazard that future contributors must remember when reading mascot.html. NOT
blocking (the caption span is hidden so it has no visual impact on the
audit), but recommended cleanup.
**Remediation:** drop the `.mascot-window__top-label` + `.mascot-window__state-caption`
markup from `mascot.html` and remove the corresponding `display: none` rules
from `chrome.css`. Mascot chrome test (`tests/mascot.chrome.test.ts`) currently
asserts these mount points exist — would need to flip those assertions
inverted ("does NOT contain") in a single test edit.
**Owner:** deferred to v3.1 (per CONTEXT carveout — chrome cleanup is not
ship-blocking).

**[M-02]** `tauri/ui/src/mascot/chrome.css:8-15` — top-of-file doc block
references "Kaan's feedback" and a v0.1.0-rc1 dev session. The comment is
historic context but pollutes the project's public-facing OSS surface
(v3.0 Clean OSS Ship is the milestone goal). Tone is fine for internal
work; comb out before public release.
**Remediation:** rewrite the doc comment in product-tone (e.g. "the mascot
overlay is a transparent character window, no chrome rectangle") and drop
the personal-name reference.
**Owner:** deferred to v3.1 (cosmetic doc-tone polish; not blocking).

**[M-03]** VIS-06 cross-link — `mascot.html` does NOT toggle `data-blur-perf`
based on the runtime perf observer that Plan 43-06 ships. The mascot overlay
window is the most visible surface for backdrop-filter regressions on
integrated-GPU machines. Today the overlay is transparent so backdrop-filter
isn't directly an issue, but if any future mascot-chrome variant adds a
glass surround (a /hatch v2.x feature), this surface inherits the runtime
ladder.
**Remediation:** Plan 43-06 owns the `data-blur-perf` runtime observer; this
audit logs the cross-link for traceability. No edit required from Plan 43-02.
**Owner:** 43-06 (VIS-06 — explicitly cross-referenced).

### LOW findings

**[L-01]** `tauri/ui/src/mascot/chrome.css:48` — `#mascot-canvas` declares
`pointer-events: none` so all OS-level interactions fall through to
`.mascot-window` (drag region). The drag region is the entire viewport,
which means **right-click + 2-finger-tap also drag** instead of opening a
system context menu. CDJ Whisper is "DJ friend on a small floating panel" —
the lack of a right-click affordance to dismiss / move-to-corner / reset-pose
is a UX paper cut, not a visual finding. Flagged because the next surface
audit (post-VIS-04 retarget pipeline) will likely want this affordance to
match the v2.x /hatch design.
**Remediation:** v2.x — add a right-click handler on `.mascot-window` that
opens a 3-item context menu (Move to corner / Reset / Hide).
**Owner:** v2.x — deferred. Not ship-blocking for v3.0.

**[L-02]** `tauri/ui/overlay.html:21` — comment block declares "Ring lifecycle
(CDJ Whisper v5 amber): fade-in 200ms → hold 800ms → fade-out 300ms ==
1300ms total" but the timing percentages in the `@keyframes ring-pulse`
rule are 0% / 15% / 77% / 100% — which means fade-in=15% of duration
(195ms at default 1300ms), hold=62% (806ms), fade-out=23% (299ms). The
percentages are close but not exactly the documented 200/800/300 split.
Functionally indistinguishable to the eye but the doc comment and the
actual timing percentages have drifted apart. Pure docs-vs-code drift, not a
visual finding.
**Remediation:** either adjust keyframes to exact 200/800/300 = 0/15.38/76.92/100
or update the doc comment to read "~200ms fade-in → ~800ms hold → ~300ms
fade-out". Trivial.
**Owner:** v3.1 — cosmetic doc-code drift; not ship-blocking.

## Audit Loop

### Audit Loop Log

| iteration | agent | verdict | files_changed | notes |
|-----------|-------|---------|---------------|-------|
| 0 | 43-01 (seed) | seeded | - | initial skeleton via `run_ui_audit.py --surface mascot-overlay --dry-run`; Plan 43-02 runs the iteration 1+ |
| iteration=1 | agent=manual (Task-tool agent unavailable inside executor; manual heuristic audit per Plan 43-02 §Task 3 fallback) | verdict=PASS | files_changed=`tauri/ui/overlay.html`, `tauri/ui/src/overlay/overlay-runtime.ts`, `tauri/ui/src/overlay/overlay-highlight.ts`, `tauri/ui/src/mascot/chrome.css` | seeded H/M/L surface findings via direct source read against mocks/vibemix-direction-final.html; closed H-01 (overlay-runtime hex literals → token-name lookup) + H-02 (overlay.html fallback hex literals → var(--amber)) + H-03 (overlay.html missing tokens.css link); 3 MEDIUMs (M-01 caption strip dead markup / M-02 doc-tone polish / M-03 VIS-06 cross-link) all logged as deferred-OK; 2 LOWs (L-01 right-click affordance / L-02 keyframe-percent vs doc-comment drift) logged as v2.x / v3.1; surface flips status: HIGH-findings-closed |

## Cross-references

- **VIS-02 hover-glow sweep** (Plan 43-02): no interactive DOM on the mascot
  overlay (canvas is `pointer-events: none`, drag-region only) — the sweep
  applies indirectly via the hex-literal scrub on overlay-runtime.ts +
  overlay.html (token-only contract).
- **VIS-06 integrated-GPU perf** (Plan 43-06): `data-blur-perf` runtime observer
  is owned by 43-06; this audit logs M-03 as a cross-link only.
- **VIS-04 mascot retarget** (Plan 43-05): the Three.js scene + state machine
  is out of scope for the visual-chrome audit; covered by the mascot animation
  wave (Plans 43-05..43-06).

## Closed findings — history

**[H-01] (closed iteration 1)** `tauri/ui/src/overlay/overlay-runtime.ts:16-22` —
4 hex literals (`#ff8a3d`, `#d4413a`, `#6dd44a`, `#4898ff`) inlined as a
`Record<string, string>` mapping keys → CSS color values. Two problems:
(a) the token-only contract from the `frontend-enforcement` skill bans hex
literals in component source; (b) the `#ff8a3d` was a duplicate of `--amber`
in tokens.css — if the CDJ Whisper amber ever shifts, the overlay ring
drifts silently.
**Closure (iteration 1):** replaced `COLOR_MAP` with `TOKEN_FOR_KEY: {amber:
"--amber", red: "--led-fault", green: "--led-ok", blue: "--silk"}` plus a
`resolveTokenValue` helper that reads `getComputedStyle(documentElement)`
at boot. Defensive fallback returns `var(${tokenName})` if the token hasn't
cascaded yet — still no inline literal. Allowlist semantics preserved.
**Files:** `tauri/ui/src/overlay/overlay-runtime.ts`
**Commit:** Task 1 (`feat(43-02): apply --glow-faint hover/focus-visible sweep …`)

**[H-02] (closed iteration 1)** `tauri/ui/overlay.html:46-49` — the inline
`<style>` block declared `border: 3px solid var(--ring-color, #f59e0b)` +
matching box-shadow fallbacks. The `#f59e0b` was both (a) a non-token
literal AND (b) the **wrong amber** — the v5 CDJ Whisper amber is `#ff8a3d`
(tokens.css `--amber`), not the Tailwind-ish `#f59e0b`. If `--ring-color`
ever failed to set (e.g. overlay-runtime.ts boot race), the ring would render
in the wrong colour.
**Closure (iteration 1):** linked `tokens.css` into `overlay.html` via
`<link rel="stylesheet" href="/src/tokens.css" />` and replaced the three
`#f59e0b` fallbacks with `var(--amber)`. Added the body-background +
body::before transparent overrides mirroring `mascot.html` so tokens.css's
cinematic body background doesn't opaque-out the overlay window.
**Files:** `tauri/ui/overlay.html`
**Commit:** Task 1

**[H-03] (closed iteration 1)** `tauri/ui/overlay.html` was a webview that
loaded `/src/overlay/overlay-runtime.ts` as a module but did NOT import
`tokens.css` — meaning every CSS custom property referenced by
overlay-runtime.ts's runtime `setProperty` write resolved to undefined.
This was the root cause of H-01 + H-02 — without the token source the
overlay-runtime.ts code had to ship inline literals as fallbacks.
**Closure (iteration 1):** `<link rel="stylesheet" href="/src/tokens.css" />`
added to `overlay.html`. overlay-runtime.ts can now read `--amber` /
`--led-fault` / `--led-ok` / `--silk` via getComputedStyle.
**Files:** `tauri/ui/overlay.html`
**Commit:** Task 1
