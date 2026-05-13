# Phase 14: CDJ Whisper v5 Migration + Polish — Pattern Map

**Mapped:** 2026-05-13
**Files analyzed:** 27 (legacy-ref consumers) + 4 surface roots + 2 HTML entry points + `tokens.css` + `main.ts` = 35 in scope
**Analogs found:** 4 / 4 surfaces have a closest-analog "already-on-v5" reference file inside their own surface — the migration recipes lift from sibling code that has already been retoned

This is a **migration-recipe map**, not a greenfield analog map. The "closest analog" per surface is a file that already consumes v5 primitives correctly; sibling files copy from it. Each migration recipe shows the legacy → v5 swap with line-numbered before/after pairs.

---

## File Classification

Per-surface inventory with role, data flow, closest already-v5 analog, and migration weight (from 14-RESEARCH.md grep counts). Files are sorted within each surface by legacy-ref count descending — the planner reads this as "biggest moves first inside each wave".

### Surface 1 — Wizard (Wave 1) — 225 legacy refs / 15 files

| File | Role | Data Flow | Closest Analog (already v5) | Legacy refs | Match Quality |
|------|------|-----------|------------------------------|-------------|---------------|
| `wizard/components/window-picker.ts` | component | request-response | `wizard/components/primary-panel.ts` | 37 | role-match (glass surface) |
| `wizard/components/dropdown-device.ts` | component | request-response | `session/components/picker.ts` | 31 | exact (picker pattern) |
| `wizard/components/controller-probe.ts` | component | event-driven | `session/components/timecode.ts` | 31 | partial (numeric LCD) |
| `wizard/components/audio-test-button.ts` | component | event-driven | `session/components/meter.ts` | 30 | partial (amber pulse rings) |
| `wizard/components/blackhole-banner.ts` | component | request-response | `crash-banner.ts` (in `src/`) | 18 | exact (status banner pattern) |
| `wizard/components/status-bar.ts` | component | event-driven | `session/components/status-bar.ts` | 17 | exact (4 LED dots) |
| `wizard/components/permissions-card.ts` | component | request-response | `wizard/components/primary-panel.ts` | 17 | role-match (card surface) |
| `wizard/smoke-test.ts` | view | request-response | `wizard/components/primary-panel.ts` | 16 | role-match |
| `wizard/step1-permissions.ts` | view | request-response | `wizard/components/primary-panel.ts` | 7 | role-match |
| `wizard/components/step-indicator.ts` | component | request-response | `session/components/status-bar.ts` | 7 | partial (LED state machine) |
| `wizard/components/mascot-corner.ts` | component | n/a | **DELETE (no analog needed)** | 6 | n/a |
| `wizard/components/primary-panel.ts` | component | request-response | `session/components/panel.ts` | 3 | exact — **THIS FILE IS ALREADY THE TEMPLATE** |
| `wizard/controllers/ddj-flx4.svg.ts` | asset | n/a | (recolor only) | 2 | n/a |
| `wizard/icons/{speaker,shield}.svg.ts` | asset | n/a | (recolor only) | 2 | n/a |
| `wizard/components/button.ts` | component | request-response | `settings/SettingsDrawer.ts` `.vmx-settings-drawer__btn` | 1 | exact (button anatomy) |
| `index.html` (wizard root markup) | view | n/a | (structural collapse) | 0 — markup change | n/a |

### Surface 2 — Live Session UI (Wave 2) — 25 legacy refs / 6 files

| File | Role | Data Flow | Closest Analog (already v5) | Legacy refs | Match Quality |
|------|------|-----------|------------------------------|-------------|---------------|
| `session/SessionLayout.ts` | composer | streaming (30Hz rAF) | `settings/SettingsDrawer.ts` glass root | 8 | exact (root composer) |
| `session/components/titlebar.ts` | component | streaming | `session/components/panel.ts` header | 7 | exact (header pattern) |
| `session/components/meter.ts` | component | streaming | (same file owns the v5 mock contract) | 4 | self |
| `session/components/drop-chip.ts` | component | event-driven | `session/components/panel.ts` badge | 3 | role-match |
| `session/components/rocker.ts` | component | request-response | mock §01 `.mood-btn` | 2 | role-match |
| `session/components/panel.ts` | component | request-response | (self — **already v5; do not touch**) | 1 | self |

### Surface 3 — Settings Drawer (Wave 3) — 15 legacy refs / 5 files (+ 1 NEW)

| File | Role | Data Flow | Closest Analog (already v5) | Legacy refs | Match Quality |
|------|------|-----------|------------------------------|-------------|---------------|
| `settings/SettingsDrawer.ts` | composer | request-response | (self — **already v5; add `.border-anim` only**) | 5 | self |
| `settings/components/retention-slider.ts` | component | request-response | `settings/SettingsDrawer.ts` `.vmx-settings-drawer__btn` | 4 | role-match |
| `settings/components/mascot-group.ts` | component | request-response | `settings/components/group.ts` | 4 | exact |
| `settings/components/hotkey-capture.ts` | component | event-driven | `crash-banner.ts` (in `src/`) | 3 | partial (amber-bordered chip) |
| `settings/components/confirm-dialog.ts` | component | request-response | `settings/SettingsDrawer.ts` modal-slot pattern | 0 (rgba audit only) | role-match |
| `settings/components/performance-group.ts` | **NEW** | request-response | `settings/components/mascot-group.ts` | 0 (new file) | exact |

### Surface 4 — Mascot Overlay Window Chrome (Wave 4) — 6 legacy refs / 1 file (+ 1 HTML)

| File | Role | Data Flow | Closest Analog (already v5) | Legacy refs | Match Quality |
|------|------|-----------|------------------------------|-------------|---------------|
| `mascot/index.ts` (lines 376–411 — `resolveCssColor` block) | bootstrap | event-driven | (none — Three.js boundary, see special map below) | 6 + 3 hex | partial |
| `mascot.html` (transparent root markup) | view | n/a | `tauri/ui/index.html` `.wizard-app` shell | 0 — markup change | role-match |
| `mascot/mood.ts` | model | event-driven | (verify chrome stays amber regardless of mood) | 0 | n/a |
| `mascot/renderer.ts` | service | streaming | (no chrome refs — review only) | 0 | n/a |

### Surface 5 — Subtractive (Wave 5) — `tokens.css` + `LICENSE-3RD-PARTY.md` + 4 WOFF2 deletes

| File | Role | Data Flow | Action | Notes |
|------|------|-----------|--------|-------|
| `tauri/ui/src/tokens.css` | tokens | n/a | DELETE lines 38–76 (legacy @font-face), DELETE lines 175–231 (shim), REPLACE line 35 (@import → vendored @font-face), ADD `prefers-reduced-motion` block + `html[data-blur-perf="on"]` override | The migration's source-of-truth file |
| `tauri/ui/public/fonts/{Workbench,DMMono-Regular,DMMono-Medium,DSEG7Classic-Bold,Caveat-Bold}.woff2` | asset | n/a | DELETE | 4 files |
| `tauri/ui/public/fonts/Saira-VariableFont_wdth,wght.woff2` + `JetBrainsMono-{Regular,Medium,SemiBold}.woff2` | asset | n/a | ADD | 4 files vendored |
| `tauri/ui/LICENSE-3RD-PARTY.md` | docs | n/a | DROP 4 entries, ADD 2 entries with SHA-256 | Attestation step |
| `scripts/check_v5_migration.sh` | tooling | n/a | CREATE (NEW) | Pre-commit gate; see code excerpt below |
| `.git/hooks/pre-commit` | tooling | n/a | CREATE + DELETE within wave 5 | One-shot wiring |

---

## Pattern Assignments

### THE GOLD STANDARDS (lift everything from these)

Three files are **already correct v5** and serve as the migration recipes for everything else:

| Gold-standard file | Used as analog for | Why |
|--------------------|--------------------|-----|
| `tauri/ui/src/session/components/panel.ts` (the entire file — 156 lines) | wizard primary-panel, session SessionLayout root, settings drawer body, mascot window wrapper | The canonical "glass panel" anatomy. Already reads `--glass-2 / --blur-glass-light / --glass-edge / --glass-top / --rad-md`, uses `var(--type-display)` with variable-axis settings, has `.vmx-glass-streak` injected, and only contains mock-verbatim `rgba(0,0,0,*)` inline shadows. |
| `tauri/ui/src/settings/SettingsDrawer.ts` (lines 62–237 — the CSS block) | all four surface roots' glass treatment, button.ts, dropdown-device.ts | Already uses Saira variable axes (`font-variation-settings: "wdth" 85, "wght" 700`), uses every silk/amber alpha token correctly, models the `:focus-visible` and hover transition vocabulary. |
| `tauri/ui/src/crash-banner.ts` block in `tokens.css:466–530` | hotkey-capture pulse, blackhole-banner halo, audio-test-button rings, controller-probe `caught` state | The only "amber-glow against glass" component already retoned — copy its `text-shadow: 0 0 4px var(--amber-65)`, `box-shadow: inset 0 0 14px var(--amber-22)`, and `border: 1px solid var(--amber-40)` pattern. |

---

### Surface 1 — Wizard (Wave 1)

#### Analog A: `wizard/components/primary-panel.ts` (3 legacy refs, mostly v5-compliant)

This file is **already on v5 primitives** (verified: `tauri/ui/src/wizard/components/primary-panel.ts:18–69` reads `--glass-2 / --blur-glass-light / --glass-edge / --glass-top / --rad-md / --type-display / --silk / --amber* / --sp-3 / --sp-5`). The only legacy residue is in the jsdoc comment lines 4–8. Wave 1 audit: delete the stale jsdoc + add `<div class="border-anim"></div>` as the first child inside the `PrimaryPanel()` factory.

**Border-anim insertion point** (`tauri/ui/src/wizard/components/primary-panel.ts:73–82`):

```ts
// CURRENT (lines 73–83):
export function PrimaryPanel(props: PrimaryPanelProps): HTMLElement {
  const root = document.createElement("section");
  root.className = "cmp-primary-panel";

  // Shared glass-fingerprint streak — unifies wizard surfaces with the
  // session deck panels.
  const streak = document.createElement("span");
  streak.className = "vmx-glass-streak";
  streak.setAttribute("aria-hidden", "true");
  root.append(streak);
  // ...

// AFTER (insert border-anim FIRST CHILD, before the streak):
export function PrimaryPanel(props: PrimaryPanelProps): HTMLElement {
  const root = document.createElement("section");
  root.className = "cmp-primary-panel";

  // v5 animated border — first child of every glass panel.
  // tokens.css:302 .border-anim handles the conic-gradient + mask-composite.
  const borderAnim = document.createElement("div");
  borderAnim.className = "border-anim";
  borderAnim.setAttribute("aria-hidden", "true");
  root.append(borderAnim);

  // Shared glass-fingerprint streak — keep.
  const streak = document.createElement("span");
  streak.className = "vmx-glass-streak";
  // ...
```

#### Migration recipe (sibling files copy from primary-panel.ts)

Heavy-legacy-ref wizard files (`window-picker.ts`, `dropdown-device.ts`, `controller-probe.ts`, `audio-test-button.ts`, `blackhole-banner.ts`, `permissions-card.ts`) all share the same legacy vocabulary. Per the RESEARCH.md per-token migration map, the swap table is:

| Legacy token | v5 replacement | Evidence in primary-panel.ts |
|--------------|----------------|------------------------------|
| `var(--panel-lift)` | `var(--glass-2)` | line 21 |
| `var(--panel)` (gradient stop) | `var(--glass-1)` | use for primary surfaces |
| `var(--panel-deep)` | `var(--glass-3)` (display-window) OR `var(--void-2)` (button pressed) | use --glass-3 for recessed |
| `var(--bezel-1)` | `var(--glass-edge)` | line 24 |
| `var(--bezel-2)` | DELETE (no 3D bevels in v5) | n/a — drop the line |
| `var(--bezel-3)` | DELETE | n/a |
| `var(--brushed-hi)` | `var(--glass-top)` (in `inset 0 1px 0`) | line 27 |
| `var(--brushed-lo)` | inline `rgba(0,0,0,0.45)` | line 28 |
| `var(--ink)` | `var(--silk)` | line 47 |
| `var(--ink-dim)` | `var(--silk-65)` | use in muted captions |
| `var(--ink-deep)` | `var(--silk-40)` | use in dim labels |
| `var(--ink-engraved)` | `var(--silk-22)` | use in pending step dots |
| `var(--phosphor)` | `var(--amber)` | line 61 |
| `var(--phosphor-warm)` | `var(--amber-deep)` | meter-fill left stop |
| `var(--phosphor-dim)` | `var(--amber-22)` | line 60 |
| `var(--phosphor-soft)` | `var(--amber-22)` (in `rgba(255,138,61,0.08)` for fill, `--amber-22` for border) | lines 59–60 |
| `var(--phosphor-glow)` | `var(--glow-soft)` | use for text-shadow / hover |
| `var(--phosphor-halo)` | `var(--glow-soft)` (composite) | use for outer halos |

#### Before/after: `wizard/components/window-picker.ts:30–110` (largest-ref file in wave)

**Before** (`tauri/ui/src/wizard/components/window-picker.ts:30–67`):

```css
.cmp-window-picker__hint {
  display: grid;
  grid-template-columns: 80px 1fr auto;
  align-items: center;
  gap: var(--sp-md);
  padding: var(--sp-md);
  background: linear-gradient(180deg, var(--panel-lift), var(--panel));
  border: 1px solid var(--bezel-1);
  border-radius: 6px;
}
.cmp-window-picker__thumb {
  width: 80px;
  height: 80px;
  background: var(--panel-deep);
  border: 1px solid var(--bezel-1);
  border-radius: 4px;
}
/* ... */
.cmp-window-picker__app {
  font-family: "DM Mono", monospace;
  font-weight: 500;
  font-size: 14px;
  color: var(--ink);
}
.cmp-window-picker__title {
  font-family: "DM Mono", monospace;
  font-size: 11px;
  color: var(--ink-dim);
}
```

**After** (copy patterns from `primary-panel.ts:18–69` + `panel.ts:27–40`):

```css
.cmp-window-picker__hint {
  display: grid;
  grid-template-columns: 80px 1fr auto;
  align-items: center;
  gap: var(--sp-4);                                  /* was --sp-md */
  padding: var(--sp-4);                              /* was --sp-md */
  background: var(--glass-2);                        /* was linear-gradient(--panel-lift, --panel) */
  backdrop-filter: var(--blur-glass-light);
  -webkit-backdrop-filter: var(--blur-glass-light);
  border: 1px solid var(--glass-edge);               /* was --bezel-1 */
  border-radius: var(--rad-md);                      /* was 6px literal */
  box-shadow:
    inset 0 1px 0 var(--glass-top),
    inset 0 -1px 0 rgba(0, 0, 0, 0.45);
}
.cmp-window-picker__thumb {
  width: 80px;
  height: 80px;
  background: var(--glass-3);                        /* was --panel-deep */
  border: 1px solid var(--glass-edge);
  border-radius: var(--rad-sm);                      /* was 4px literal */
}
.cmp-window-picker__app {
  font-family: var(--type-body);                     /* was "DM Mono", monospace */
  font-weight: 500;
  font-variation-settings: "wdth" 100, "wght" 500;
  font-size: 14px;
  color: var(--silk);                                /* was --ink */
}
.cmp-window-picker__title {
  font-family: var(--type-mono);                     /* was "DM Mono", monospace — JBM is the v5 mono */
  font-size: 11px;
  color: var(--silk-65);                             /* was --ink-dim */
}
```

#### Before/after: forbidden-font `"Workbench"` swap (controller-probe.ts:79)

**Before** (`tauri/ui/src/wizard/components/controller-probe.ts:75–84`):

```css
.cmp-ctrl-probe__connected {
  display: inline-flex;
  align-items: center;
  gap: var(--sp-xs);
  font-family: "Workbench", "Courier New", monospace;
  font-size: 9px;
  letter-spacing: 0.32em;
  text-transform: uppercase;
  color: var(--ok);
}
```

**After** (copy pattern from `SettingsDrawer.ts:113–125` "settings title"):

```css
.cmp-ctrl-probe__connected {
  display: inline-flex;
  align-items: center;
  gap: var(--sp-1);                                  /* was --sp-xs */
  font-family: var(--type-display);                  /* was "Workbench", "Courier New", monospace */
  font-variation-settings: "wdth" 85, "wght" 600;
  font-size: 9px;
  letter-spacing: 0.22em;                            /* was 0.32em — mock-verbatim is 0.22em */
  text-transform: uppercase;
  color: var(--led-ok);                              /* was --ok (semantic alias, same value) */
  text-shadow: 0 1px 0 rgba(0, 0, 0, 0.7);           /* engraved-look — load-bearing per UI-SPEC */
}
```

#### Before/after: DSEG7 → JetBrains Mono tabular-nums (controller-probe.ts:112–133)

**Before** (legacy DSEG7 readout):

```css
.cmp-ctrl-probe__lcd {
  font-family: "DSEG7", "DM Mono", monospace;
  font-size: 48px;
  color: var(--phosphor);
  text-shadow: var(--phosphor-glow);
}
```

**After** (copy pattern from `session/components/timecode.ts` "display window" — same family used for time-hero):

```css
.cmp-ctrl-probe__lcd {
  font-family: var(--type-mono);                     /* JetBrains Mono */
  font-variant-numeric: tabular-nums;
  font-feature-settings: "tnum";                     /* belt + braces */
  font-size: 48px;
  color: var(--amber);
  text-shadow: var(--glow-soft);
}
```

#### Wizard root markup: single-column collapse (index.html:29–32)

**Before** (`tauri/ui/index.html:29–32`):

```html
<div class="wizard-grid">
  <section id="wizard-primary" class="primary-panel-mount"></section>
  <aside id="mascot-corner"></aside>
</div>
```

**After**:

```html
<div class="wizard-grid">
  <section id="wizard-primary" class="primary-panel-mount"></section>
</div>
```

Plus in `tokens.css:439–446` collapse `.wizard-grid` to single-column (the inline TODO comment at `tokens.css:155–158` already flags this). And in `wizard/router.ts:202` + `wizard/router.ts:344` delete the `mascotMount` references entirely (mascot-corner.ts is deleted in this same wave).

#### Wizard root: add border-anim once the structural collapse lands

The wizard root panel that receives `.border-anim` is the `#wizard-primary` mount — which is filled by `PrimaryPanel()` from `primary-panel.ts`. So the border-anim insertion shown above (inside `PrimaryPanel()`) is the sole insertion point. No separate `index.html` change needed.

---

### Surface 2 — Live Session UI (Wave 2)

#### Analog: `session/components/panel.ts` (already perfect v5)

This file at `tauri/ui/src/session/components/panel.ts:26–103` is the **canonical glass-panel anatomy** for the whole project. It already has:
- `background: var(--glass-2)` (line 29)
- Full `backdrop-filter` + `-webkit-backdrop-filter` pair (lines 30–31)
- `border: 1px solid var(--glass-edge)` (line 32)
- `border-radius: var(--rad-md)` (line 33)
- The complete v5 box-shadow stack with `inset 0 1px 0 var(--glass-top)`, deep drop shadow, almost-imperceptible outer rim (lines 34–38)
- `.vmx-glass-streak` injection (lines 113–117)
- Saira variable-axis header (lines 49–50 — `font-variation-settings: "wdth" 85, "wght" 600`)
- Engraved text-shadow `0 1px 0 rgba(0, 0, 0, 0.7)` (line 55)

#### Border-anim insertion point: `session/SessionLayout.ts:183–194`

```ts
// CURRENT (lines 183–194):
const root = document.createElement("div");
root.className = "vmx-session";

// Corner screws — pure ornament per UI-SPEC §Panel screws.
for (const corner of ["tl", "tr", "bl", "br"] as const) {
  const sc = document.createElement("span");
  sc.className = "vmx-session__screw";
  // ...
}

// AFTER (insert border-anim BEFORE the screws):
const root = document.createElement("div");
root.className = "vmx-session";

// v5 animated border — first child of the session glass panel.
const borderAnim = document.createElement("div");
borderAnim.className = "border-anim";
borderAnim.setAttribute("aria-hidden", "true");
root.append(borderAnim);

// Corner screws — pure ornament. v5 may demote/delete these in audit;
// for now keep, but recolor --bezel-3 → --silk-22.
for (const corner of ["tl", "tr", "bl", "br"] as const) {
  // ...
}
```

#### Required SessionLayout CSS adjustments (`session/SessionLayout.ts:121–174`)

The `.vmx-session` root currently uses `--sp-lg / --sp-md / --sp-xl / --bezel-3` aliases. These must migrate to v5 primitives. Concrete swap list:

| Line | Current | After |
|------|---------|-------|
| `SessionLayout.ts:126` | `--gap-col: var(--sp-lg);` | `--gap-col: var(--sp-5);` |
| `SessionLayout.ts:139` | `color: var(--bezel-3);` (screws) | `color: var(--silk-22);` |
| `SessionLayout.ts:149` | `padding: var(--sp-xl);` | `padding: 32px; /* mock-verbatim */` (no v5 equivalent for 32) |
| `SessionLayout.ts:156` | `gap: var(--sp-md);` | `gap: var(--sp-4);` |
| `SessionLayout.ts:164` | `gap: var(--sp-md);` | `gap: var(--sp-4);` |
| `SessionLayout.ts:167` | `padding: var(--sp-md) 0 0;` | `padding: var(--sp-4) 0 0;` |

The session glass panel chrome itself is the `.vmx-session` div with `position: relative` (line 130) and `overflow: hidden` (line 131) — both already satisfy `.border-anim` parent invariants.

---

### Surface 3 — Settings Drawer (Wave 3)

#### Analog: `settings/SettingsDrawer.ts` (already perfect v5)

Lines 62–237 are the **canonical drawer glass** — already migrated. Concrete v5 features in place:
- `background: var(--glass-1)` (line 87)
- `backdrop-filter: var(--blur-glass)` + `-webkit-` (lines 88–89)
- `border-left: 1px solid var(--glass-edge)` (line 90)
- `box-shadow:` stack with `inset 1px 0 0 var(--glass-top)` (lines 91–94)
- Header title uses Saira variable axes + engraved text-shadow (lines 117–124)
- Amber pre-bullet on `::before` (lines 126–133) — uses `--amber` + composite glow
- `--silk-40 / --silk-22 / --amber / --amber-40 / --amber-22 / --glass-edge` everywhere

**Only audit work for `SettingsDrawer.ts` itself: add `.border-anim` and convert 5 `--sp-*` aliases.**

#### Border-anim insertion point: `settings/SettingsDrawer.ts:284–289`

```ts
// CURRENT (lines 284–289):
const drawer = document.createElement("aside");
drawer.className = "vmx-settings-drawer";
drawer.dataset.open = "false";
drawer.setAttribute("aria-label", "settings");
drawer.setAttribute("role", "complementary");

// Header
const header = document.createElement("div");

// AFTER (insert border-anim as FIRST CHILD before header):
const drawer = document.createElement("aside");
drawer.className = "vmx-settings-drawer";
drawer.dataset.open = "false";
drawer.setAttribute("aria-label", "settings");
drawer.setAttribute("role", "complementary");

// v5 animated border — first child of the drawer glass.
const borderAnim = document.createElement("div");
borderAnim.className = "border-anim";
borderAnim.setAttribute("aria-hidden", "true");
drawer.append(borderAnim);

// Also requires CSS adjustment: .vmx-settings-drawer currently has
// `display: flex; flex-direction: column` (lines 96–97) which would
// flow the border-anim into the layout. Add `overflow: hidden` (already
// implicit via translateX) and ensure the body's z-index >= 1.
```

CSS adjustment needed at `SettingsDrawer.ts:78–98`:
- Confirm `position: fixed` already there (line 79) — `position: relative` semantically equivalent for `.border-anim` absolute-positioned child.
- Add `overflow: hidden` to `.vmx-settings-drawer` block.
- Add `z-index: 1` (or ensure header/body siblings already render above the border-anim's z-index 4 — actually `.border-anim` is z-index 4 per tokens.css:326, so set `.vmx-settings-drawer > :not(.border-anim) { position: relative; z-index: 5; }` to keep header + body above the sweep peak).

#### NEW component: `settings/components/performance-group.ts`

Lift the analog directly from `settings/components/mascot-group.ts` (same structure, same group factory call). Pseudocode shown in 14-RESEARCH.md:725–747 — concrete CSS pattern lifts from `SettingsDrawer.ts:198–222` (the `.vmx-settings-drawer__btn` block) for the toggle pill anatomy.

```ts
// Source: copy the function-component shape from settings/components/mascot-group.ts
// CSS lifts from SettingsDrawer.ts:198–222 (button anatomy)
// Toggle "off" state = glass-3 background; "on" state = amber-backlit per
// the mood-pill .on anatomy in the v5 mock.

export function PerformanceGroup(): HTMLElement {
  return renderSettingsGroup({
    header: "PERFORMANCE",
    children: buildRow("LIGHTER BLUR", getCurrentBlurPerf(), (on) => {
      applyBlurPerfPreference(on);     // see 14-RESEARCH.md:730–737
      void toggleBlurPerf(on);          // IPC write through SettingsApplier
    }),
  });
}
```

---

### Surface 4 — Mascot Overlay Window Chrome (Wave 4)

#### Special map: there is no "already-v5 mascot frame" in code

The Phase 13 mascot overlay is currently a transparent canvas (`mascot.html:51–53`) with NO chrome around it. Wave 4 adds the chrome **for the first time** — so the closest analog is `session/components/panel.ts` (the canonical glass panel) adapted to wrap a transparent canvas.

#### Border-anim + chrome wrapper insertion: `tauri/ui/mascot.html:51–54`

**Before** (`tauri/ui/mascot.html:51–54`):

```html
<body style="background: transparent; margin: 0; padding: 0; overflow: hidden;">
  <canvas id="mascot-canvas" aria-hidden="true"></canvas>
  <script type="module" src="/src/mascot/index.ts"></script>
</body>
```

**After** (wrap canvas in v5 glass chrome with `.border-anim.slow.rev`):

```html
<body style="background: transparent; margin: 0; padding: 0; overflow: hidden;">
  <div class="mascot-window">
    <div class="border-anim slow rev" aria-hidden="true"></div>
    <div class="mascot-window__top-label">
      <span class="mascot-window__caption">OVERLAY · STICKY · ALL SPACES · 320×420</span>
    </div>
    <canvas id="mascot-canvas" aria-hidden="true"></canvas>
    <div class="mascot-window__state-caption" aria-hidden="true">idle · bop-to-beat</div>
  </div>
  <script type="module" src="/src/mascot/index.ts"></script>
</body>
```

Plus inline `<style>` (or moved to a new `src/mascot/chrome.css` imported by `index.ts`):

```css
.mascot-window {
  position: relative;
  width: 100vw;
  height: 100vh;
  overflow: hidden;
  border-radius: 8px;                                /* 8px per UI-SPEC §Mascot — vs 6px elsewhere */
  background: var(--glass-3);                        /* recessed; minimal blur per Pitfall 1 */
  backdrop-filter: var(--blur-glass-display);
  -webkit-backdrop-filter: var(--blur-glass-display);
  border: 1px solid var(--glass-edge);
  box-shadow:
    inset 0 1px 0 var(--glass-top),
    inset 0 -1px 0 rgba(255, 138, 61, 0.06),         /* faint amber undertone on bottom edge */
    0 32px 64px rgba(0, 0, 0, 0.85),
    0 0 0 1px rgba(255, 255, 255, 0.018);
}
.mascot-window > * { position: relative; z-index: 1; }
.mascot-window__top-label {
  position: absolute;
  top: var(--sp-2);
  left: 50%;
  transform: translateX(-50%);
  z-index: 3;
}
.mascot-window__caption {
  font-family: var(--type-mono);
  font-size: 9px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--silk-40);
}
.mascot-window__state-caption {
  position: absolute;
  bottom: var(--sp-2);
  left: 50%;
  transform: translateX(-50%);
  z-index: 3;
  font-family: var(--type-mono);
  font-size: 9px;
  letter-spacing: 0.18em;
  color: var(--silk-40);
}
```

**Critical:** `tokens.css` is NOT loaded by `mascot.html` currently (mascot.html has only inline styles, lines 34–49). Wave 4 must either (a) `<link rel="stylesheet" href="/src/tokens.css">` into mascot.html, OR (b) inline the necessary v5 CSS vars into mascot.html's `<style>` block. Recommendation: option (a) — keeps mascot chrome composing through the same cascade as the rest of the app. Adding the link causes the body background-color to also become non-transparent (because tokens.css sets `body { background-color: var(--void); }` at line 260), which **breaks** the transparent overlay. Workaround: after linking tokens.css, override `html, body { background: transparent !important; }` in mascot.html's inline `<style>`. The `!important` is justified because the overlay window must composite over the desktop per Phase 13 invariant.

#### `mascot/index.ts:376–411` — the resolveCssColor cleanup

**Before** (`tauri/ui/src/mascot/index.ts:376–411`):

```ts
/**
 * Resolve a CSS variable to a THREE.Color. Falls back to phosphor amber
 * if the var is missing/empty (the variable may not be present in the
 * mascot window's reduced stylesheet at boot).
 *
 * The fallback amber hex is the canonical --phosphor token VALUE
 * (#ffa12e) from tokens.css — duplicated here only as a literal-string
 * default for THREE.Color when CSS resolution fails. tokens.css remains
 * the single source-of-truth for accent paint at the CSS layer.
 */
function resolveCssColor(varName: string, fallback: string): Color {
  try {
    const root = document.documentElement;
    const raw = getComputedStyle(root).getPropertyValue(varName).trim();
    const value = raw.length > 0 ? raw : fallback;
    return new Color(value);
  } catch {
    return new Color(fallback);
  }
}

function handleMoodChange(mood: MoodName): void {
  // ...
  let color: Color;
  if (mood === "hype-man") {
    color = resolveCssColor("--phosphor", "#ffa12e");
  } else if (mood === "teacher") {
    color = resolveCssColor("--phosphor-soft", "#efe6d6");
  } else {
    color = resolveCssColor("--ink-deep", "#3d424c");
  }
```

**After**:

```ts
/**
 * Resolve a CSS variable to a THREE.Color. Falls back to v5 amber if the
 * var is missing/empty. tokens.css remains the single source-of-truth
 * at the CSS layer; this duplicates the hex only as a literal-string
 * default for THREE.Color when CSS resolution fails.
 */
function resolveCssColor(varName: string, fallback: string): Color {
  try {
    const root = document.documentElement;
    const raw = getComputedStyle(root).getPropertyValue(varName).trim();
    const value = raw.length > 0 ? raw : fallback;
    return new Color(value);
  } catch {
    return new Color(fallback);
  }
}

function handleMoodChange(mood: MoodName): void {
  // ...
  let color: Color;
  if (mood === "hype-man") {
    color = resolveCssColor("--amber", "#ff8a3d");     // was --phosphor / #ffa12e
  } else if (mood === "teacher") {
    // Mood-specific cream tint — kept as plan-authorised inline fallback.
    color = resolveCssColor("--silk", "#d6cfc7");      // was --phosphor-soft / #efe6d6
  } else {
    // coach — slate; v5 silk-40 reads as a desaturated coach tint.
    color = resolveCssColor("--silk-40", "#3d424c");   // was --ink-deep / same hex
  }
```

Note: the three hex fallbacks at line 403/407/410 were already counted as the **only** hardcoded hex literals outside `tokens.css` (RESEARCH.md:177–181). The "v5 win": `#ff8a3d` replaces `#ffa12e`; `#d6cfc7` (v5 silk) replaces `#efe6d6`; `#3d424c` (the original coach slate value) stays — it's not a v5 token primitive but it's a legitimate Three.js color literal.

---

### Wave 5 — Subtractive (tokens.css surgery)

#### `tokens.css:35` — replace Google Fonts `@import` with vendored `@font-face`

**Before** (`tauri/ui/src/tokens.css:35`):

```css
@import url('https://fonts.googleapis.com/css2?family=Saira:wdth,wght@75..125,300..800&family=JetBrains+Mono:wght@400;500;600&display=swap');
```

**After** (replace line 35 with vendored block — full snippet at 14-RESEARCH.md:582–614):

```css
/* === v5 type — Saira + JetBrains Mono (vendored WOFF2) ================ */

@font-face {
  font-family: 'Saira';
  src: url('/fonts/Saira-VariableFont_wdth,wght.woff2') format('woff2-variations'),
       url('/fonts/Saira-VariableFont_wdth,wght.woff2') format('woff2');
  font-weight: 300 800;
  font-stretch: 75% 125%;
  font-style: normal;
  font-display: swap;
}

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

#### `tokens.css:38–76` — DELETE legacy @font-face block

Already itemized in 14-UI-SPEC.md "Shim Removal Surgery". Five blocks deleted: Workbench, DM Mono Regular, DM Mono Medium, DSEG7, Caveat.

#### `tokens.css:175–231` — DELETE shim block

Already itemized. The token-by-token deletion list lives in 14-UI-SPEC.md "Tokens DELETED from tokens.css".

#### NEW: perf-fallback CSS block (insert before `}` of `:root` OR after `.border-anim` definition)

Full snippet at 14-RESEARCH.md:696–721. The placement is **after the existing `:root { ... }` block closes (`tokens.css:231`)** and before the reset at line 233:

```css
/* === Perf fallback — accessibility + user-toggled lighter blur ======== */

@media (prefers-reduced-motion: reduce) {
  :root {
    --blur-glass:         blur(16px);
    --blur-glass-light:   blur(8px);
    --blur-glass-display: blur(4px);
    --motion-border-sweep: 0s;
  }
  .border-anim { animation: none; opacity: 0.6; }
}

html[data-blur-perf="on"] {
  --blur-glass:         blur(16px);
  --blur-glass-light:   blur(8px);
  --blur-glass-display: blur(4px);
}
```

---

### Pre-commit gate script — NEW file `scripts/check_v5_migration.sh`

Full implementation at 14-RESEARCH.md:621–673. Closest analog in the project: `scripts/check_ipc_schema.py` (existing standalone-script pattern). Wave 5 wiring:

```bash
# Wave 5 start:
cat > .git/hooks/pre-commit <<'EOF'
#!/usr/bin/env bash
exec "$(git rev-parse --show-toplevel)/scripts/check_v5_migration.sh" --strict
EOF
chmod +x .git/hooks/pre-commit

# After shim-delete commit lands:
rm .git/hooks/pre-commit
```

This is the ONLY commit in Phase 14 where the hook is wired. Per Pitfall 8 (RESEARCH.md:557–563), every other commit in the phase runs the script in `--warn-only` mode (informational) or not at all.

---

## Shared Patterns (cross-cutting — applied to all relevant surfaces)

### Shared Pattern 1 — `.border-anim` insertion

**Source:** `tokens.css:302–331` (the utility itself, fully defined)
**Apply to:** all four surface roots — wizard primary panel, session layout root, settings drawer aside, mascot.html `.mascot-window`

**Parent invariants** (verified against `tokens.css:296`):
- Parent must be `position: relative` AND `overflow: hidden`
- Component content at `z-index: 1+` (the border-anim itself is `z-index: 4` per tokens.css:326)

**Per-surface modifier choice:**

| Surface | Border-anim class | Duration | Direction | Why |
|---------|-------------------|----------|-----------|-----|
| Wizard primary panel | `.border-anim` | 22s | forward | default |
| Session root | `.border-anim` | 22s | forward | default |
| Settings drawer | `.border-anim` | 22s | forward | drawer occludes session; safe to share timing |
| Mascot overlay | `.border-anim slow rev` | 32s | reverse | de-sync from session per CONTEXT Area 3 |

**Concrete excerpt (the canonical insertion — copy into all four surface composers):**

```ts
const borderAnim = document.createElement("div");
borderAnim.className = "border-anim";              // or "border-anim slow rev" for mascot
borderAnim.setAttribute("aria-hidden", "true");
root.append(borderAnim);                            // first child — before other content
```

### Shared Pattern 2 — Saira variable-axis font-family swap

**Source:** `tauri/ui/src/settings/SettingsDrawer.ts:117–124` (the canonical Saira header)
**Apply to:** every `font-family: "Workbench"` / `font-family: "DM Mono"` / `font-family: "DSEG7"` declaration outside `tokens.css`

**Concrete swap recipe:**

```css
/* WAS — uppercase label using Workbench */
font-family: "Workbench", "Courier New", monospace;
font-size: 11px;
letter-spacing: 0.22em;
text-transform: uppercase;

/* IS — Saira at the same visual */
font-family: var(--type-display);
font-variation-settings: "wdth" 85, "wght" 700;     /* display-text axis preset */
font-size: 10px;                                    /* mock-verbatim 10px (often was 11px) */
letter-spacing: 0.22em;
text-transform: uppercase;
text-shadow: 0 1px 0 rgba(0, 0, 0, 0.7);            /* engraved feel — load-bearing */
```

```css
/* WAS — DM Mono body text */
font-family: "DM Mono", monospace;
font-weight: 500;
font-size: 14px;

/* IS — body text uses Saira-via-type-body for everything except numerics */
font-family: var(--type-body);
font-variation-settings: "wdth" 100, "wght" 500;
font-size: 14px;
```

```css
/* WAS — DSEG7 numeric readout */
font-family: "DSEG7", "DM Mono", monospace;
font-size: 48px;

/* IS — JetBrains Mono replaces DSEG7's 7-segment LCD look */
font-family: var(--type-mono);
font-variant-numeric: tabular-nums;
font-feature-settings: "tnum";
font-size: 48px;
```

**Axis preset lookup table (mock-verbatim, from RESEARCH.md:425–434):**

| Role | wdth | wght | Use case |
|------|------|------|----------|
| Body | 100 | 400 | default `html, body` |
| Silkscreen label (9–10px UPPERCASE) | 85–90 | 500 | `.label`, `.led`, `.pal-label` |
| Mid headline (18–22px UPPERCASE) | 85–100 | 500–600 | `.section-head h2`, spec-name |
| Headline (24px UPPERCASE) | 85 | 600 | section headlines |
| Display hero (64–80px UPPERCASE) | 82 | 700–800 | `.track-title`, `.h0` |
| Sub-title (run-on 18px) | 100 | 400 | `.track-title .sub` |

### Shared Pattern 3 — Hardcoded `rgba(...)` → token migration

**Source:** `tauri/ui/src/settings/SettingsDrawer.ts:179–193` (idiomatic mix — tokens where alpha matches, inline `rgba()` where mock-verbatim)
**Apply to:** every `rgba(255, 138, 61, X)` and `rgba(214, 207, 199, X)` outside `tokens.css`

**Hard rule:**
- `rgba(255, 138, 61, 0.22)` → `var(--amber-22)`
- `rgba(255, 138, 61, 0.40)` → `var(--amber-40)`
- `rgba(255, 138, 61, 0.65)` → `var(--amber-65)`
- `rgba(214, 207, 199, 0.65)` → `var(--silk-65)`
- `rgba(214, 207, 199, 0.40)` → `var(--silk-40)`
- `rgba(214, 207, 199, 0.22)` → `var(--silk-22)`
- `rgba(214, 207, 199, 0.12)` → `var(--silk-12)`

**Other alphas stay inline** if mock-verbatim, with a `/* mock-verbatim */` trailing comment. Example from `SettingsDrawer.ts:179`:

```css
background: linear-gradient(180deg, rgba(255, 138, 61, 0.09) 0%, rgba(255, 138, 61, 0.025) 100%);
```

Both `0.09` and `0.025` have no token equivalent and stay inline. The 0.09/0.025 button hover-gradient pair is **mock-verbatim** and load-bearing — it's used in `SettingsDrawer.ts:179`, `SettingsDrawer.ts:220`, and `crash-banner` in `tokens.css:517`.

### Shared Pattern 4 — Engraved text-shadow on every silkscreen label

**Source:** `tauri/ui/src/settings/SettingsDrawer.ts:124, 235` and `session/components/panel.ts:55`
**Apply to:** every silkscreen label (9–10px UPPERCASE Saira wdth 85 wght 500–700)

```css
text-shadow: 0 1px 0 rgba(0, 0, 0, 0.7);
```

This is **load-bearing** per 14-UI-SPEC.md typography table — it's what makes the 9–10px UPPERCASE labels read as engraved on glass, not floating text. The auditor flags labels missing this shadow.

### Shared Pattern 5 — Perf fallback runtime wiring

**Source:** 14-RESEARCH.md:725–747 (the TypeScript wiring pseudocode) + `tauri/ui/src/main.ts:91–137` (boot path where the toggle gets applied)
**Apply to:** `main.ts` boot + new `settings/components/performance-group.ts`

**Boot wiring** (insert into `main.ts` `boot()` function after `initCrashBanner()`):

```ts
// Apply Saira variable axes + boot-time perf-blur preference.
// Reads from SettingsApplier-managed user preference. The CSS rule at
// tokens.css html[data-blur-perf="on"] picks it up via the cascade.
try {
  const settings = await invoke<{ performance?: { lighter_blur?: boolean } }>(
    "read_settings"
  );
  if (settings?.performance?.lighter_blur) {
    document.documentElement.setAttribute("data-blur-perf", "on");
  }
} catch (err) {
  console.warn("[boot] perf preference read failed:", err);
  // No fatal — default-off blur is the safe path.
}
```

`main.ts` is the right insertion site because both wizard and session paths flow through `boot()`. **No change needed in `mascot.html`** — the overlay window doesn't need to read the toggle directly; it inherits the `data-blur-perf` from a shared `<html>` if the same Tauri webview, OR remains unaffected (the overlay's blur is `--blur-glass-display: blur(6px)` which is already minimal — Pitfall 1 mitigation).

### Shared Pattern 6 — Copy purge

**Source:** 14-UI-SPEC.md "Copywriting Contract" + RESEARCH.md "Purge dictionary residue"
**Apply to:** every `.ts` file in `tauri/ui/src/{wizard,session,settings,mascot}/` — string literals (NOT comments)

**Forbidden in string literals** (the words appear in rendered chrome):
- `brushed`, `anodised`, `phosphor`, `retro-futurist`, `knob/fader physics`, `knurled`
- `tactile` → manual review only (may be legitimate UI behavior description)

**Slop bans** (from `vibemix.prompts.negative_dict` — UI also enforces):
- `amazing`, `awesome`, `great mix`, `let me know`, `delve`, `leverage`, `as an AI`, `unleash`, `seamless`, `journey`, `craft`, `elevate`

**Concrete example (the one stub residue verified):**

`wizard/components/mascot-corner.ts:47` currently renders `"AVERY · arriving phase 13"` — this file is **deleted entirely** in Wave 1 (no chrome residue surviving).

`wizard/components/primary-panel.ts:5` jsdoc says `"brushed-metal vertical streak via ::before"` — jsdoc, not chrome, but rewrite anyway as "shared glass-fingerprint streak" to match the runtime comment at line 79.

---

## No Analog Found

| File | Role | Data Flow | Reason | Mitigation |
|------|------|-----------|--------|------------|
| `scripts/check_v5_migration.sh` | tooling | n/a | No pre-commit gate exists yet in the repo | Use the existing `scripts/check_ipc_schema.py` standalone-script PATTERN (not its CONTENT) as the analog — same shape (one shell script, no framework dep). Full implementation in 14-RESEARCH.md:621–673. |
| `settings/components/performance-group.ts` | component | request-response | NEW component | Lift function-component shape from `settings/components/mascot-group.ts`; lift toggle CSS anatomy from `SettingsDrawer.ts:198–222`. Full pseudocode in 14-RESEARCH.md:725–747. |
| `mascot.html` chrome wrapper | view | n/a | Mascot was previously a bare transparent canvas — chrome added for the first time in Wave 4 | Lift `.session-panel` anatomy from `session/components/panel.ts:27–40` and Pioneer-grade overlay caption styling from 14-UI-SPEC.md §Surface 4. Full markup excerpt above. |
| `.git/hooks/pre-commit` | tooling | n/a | No existing hooks | One-shot wiring shown above (Wave 5 task) |

---

## Metadata

**Analog search scope:** `tauri/ui/src/{wizard,session,settings,mascot}/**` + `tauri/ui/src/main.ts` + `tauri/ui/src/crash-banner.ts` + `tauri/ui/src/tokens.css` + `tauri/ui/index.html` + `tauri/ui/mascot.html`
**Files scanned:** 70 in `tauri/ui/src/` per `find` listing, of which 27 hold legacy refs per RESEARCH inventory and 4 are already-perfect v5 analogs (`session/components/panel.ts`, `settings/SettingsDrawer.ts` lines 62–237, `wizard/components/primary-panel.ts`, `tokens.css:81–173`)
**Pattern extraction date:** 2026-05-13
**Three gold standards verified:**
- `session/components/panel.ts` (156 lines) — canonical glass-panel anatomy
- `settings/SettingsDrawer.ts:62–237` (176 lines of CSS) — canonical drawer + button + label vocabulary
- `tokens.css:466–530` (crash-banner block) — canonical amber-glow-against-glass for status banners

**Out-of-scope for pattern mapping** (no migration impact):
- `mascot/{asset-loader,event-dispatcher,state-machine,particle-puff,renderer,ws-client}.ts` — all already migrated or never touched chrome tokens
- `session/{state,ws-bridge,render-loop,router,mock}.ts` — runtime state/IPC plumbing, no chrome
- `ipc/**` — IPC client, no chrome
- `wizard/icons/{headphones,microphone}.svg.ts` — confirmed zero legacy refs (grep returned 0)
