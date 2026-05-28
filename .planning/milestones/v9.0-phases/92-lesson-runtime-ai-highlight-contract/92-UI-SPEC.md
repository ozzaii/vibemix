---
phase: 92
slug: lesson-runtime-ai-highlight-contract
status: draft
shadcn_initialized: false
preset: none
created: 2026-05-28
---

# Phase 92 — UI Design Contract

> Visual and interaction contract for the LESSON-MODE layer painted on top of the P91 Learn-window surface. P91 shipped the schematic-as-stage; P92 adds the lesson HUD, the tutor-speak dock, the highlight envelope (CSS-variable swap on slots P91 scaffolded), the 3-strike hint state, the "I got it" skip control, and the "Reset Learn Progress" row extension to the existing settings drawer. The hero is still the controller schematic — every new surface is a quiet sibling that lets the user keep both eyes on the hardware they're learning.

> **Inheritance:** Every token, every component pattern, every copywriting rule from `91-UI-SPEC.md` carries forward. P92 only declares what's NEW or CHANGED. Where P91 said "stays a placeholder" (highlight slots, lesson-HUD scaffolding), P92 lights it up.

> **Pre-population sources:** CONTEXT.md (locked decisions §LessonRuntime / §12 IPC envelopes / §Highlight paint / §Tutor persona / §Hand-authored scripts / §Lesson advancement / §Progress persistence) · `91-UI-SPEC.md` (visual baseline + token vocabulary) · `.planning/research/SUMMARY.md` §4 envelope list / §6 persona reuse / §10 tone gate · `.planning/research/PITFALLS.md` P1 tone failure class · `mocks/vibemix-rebuild-session.html` "Deck Speaks" hero-on-void + ghost-recede + receipt-rule precedent.

---

## Design System

| Property | Value |
|----------|-------|
| Tool | **none** (no shadcn; vibemix v5 "CDJ Whisper" design language already at `tauri/ui/src/tokens.css`; NO new tokens — Critical Constraint #1 LOCKED) |
| Preset | not applicable |
| Component library | **none** (vanilla TS + DOM; mirrors the P91 hand-authored component pattern in `tauri/ui/src/learn/components/`) |
| Icon library | **none external** — `<svg>` glyphs hand-authored inline at the call-site (matches `empty-state.ts` PLUG_GLYPH precedent). NO Lucide / Heroicons / Tabler. |
| Font | **Saira** (display + body; variable axes `wdth` + `wght`) + **JetBrains Mono** (numerics + control labels + progress index). Inherited from `tokens.css`; identical to P91 (Critical Constraint #8). |
| Window topology | EXTENDS the existing P91 `learn` `WebviewWindow` (`tauri/src-tauri/src/learn_window.rs` — already wired). NO new window. NO new ws port — all 11 new envelopes ride `127.0.0.1:8765` (Invariant #4 / Critical Constraint LOCKED). |
| Window grid | P91 was `<titlebar 56px> <stage 1fr> <statusbar 40px>` — P92 reshapes the middle row to `<lesson-hud 56px> <stage 1fr> <tutor-dock auto>` and keeps the outer titlebar + statusbar. The schematic still owns the dominant 1fr; HUD + dock are quiet bookends. |

---

## Spacing Scale

Inherited verbatim from `91-UI-SPEC.md` § Spacing Scale (all multiples of 4 from `tokens.css` `--sp-*`). **Zero new spacing tokens** — Critical Constraint #1.

New P92 usages of existing tokens:

| Token | Value | NEW usage in Phase 92 |
|-------|-------|------------------------|
| `--sp-1` | 4px | Hairline gap between a progress-dot and its index label (when expanded on hover). Inset padding inside the "I got it" silk-22 ghost button. |
| `--sp-2` | 8px | Gap between lesson HUD elements (course chip · lesson title · progress index). Inset between tutor-dock kinetic chip + the rest of the text. |
| `--sp-3` | 12px | Gap between progress-dot row and lesson title in HUD. Vertical breathing inside tutor-speak dock between cite-receipt line and skip-control row. |
| `--sp-4` | 16px | Outer padding inside the tutor-speak dock; gap between HUD's left-bunch and right-bunch. |
| `--sp-5` | 24px | Tutor-speak dock side padding (matches statusbar's `--sp-5` horizontal padding for column-rail continuity). Lesson HUD side padding. |
| `--sp-6` | 40px | Vertical margin above the tutor-speak dock (separates from the schematic stage). Lesson HUD vertical breathing when the dock is in `data-state="hint"` (the dock expands slightly). |

**Lesson HUD height:** **56px** (matches `--titlebar-h` so the HUD reads as a "second tier" of titlebar chrome, not a new content surface).

**Tutor-speak dock minimum height:** **120px** at rest (one ghost line + the active "now" line + the receipt rule + the I-got-it row). **160px** in `data-state="hint"` (hint adds the highlight-pulse-intensify + one extra hint-text line; the dock GROWS DOWN, never up — never crops the schematic). The stage's `min-height: 0` already absorbs the resize.

**Highlight pulse-ring inner radius:** the SVG geometry P91 authored is the source of truth; pulse-ring stroke = **4px** (Critical Constraint #4 dual-channel cue: color = amber, shape = 4px-stroke pulse-ring). Pulse-ring outer radius = `data-control-id`'s native bbox + **8px** breathing room.

**"I got it" skip-button hit target:** **44×24 CSS px** (44px wide — comfortable for keyboard-and-mouse-only users; 24px tall — same height as the existing rocker pill the user already knows from the session deck).

---

## Typography

Inherited verbatim from `91-UI-SPEC.md` § Typography. **Zero new font sizes, zero new font weights** — Critical Constraint #8.

**Typography map for NEW Phase-92 surfaces:**

| Role | Family / variation | Size | Weight | Line height | Letter spacing | NEW usage in Phase 92 |
|------|-------------------|------|--------|-------------|----------------|------------------------|
| Display (lesson title in HUD) | Saira `wdth 85, wght 600`, UPPERCASE | **14px** | 600 | 1.0 | 0.12em | The current lesson title in the HUD (e.g. `L0.00 PRESS PLAY`). Reuses the rocker-pill display vocabulary (10-14px Saira `wdth 85, wght 600`) — NOT the 28px controller-name display register (controller is still the hero; lesson title is the meta-label). |
| Display (tutor-speak hero line) | Saira `wdth 92, wght 600` | **clamp(24px, 2.6vw, 32px)** | 600 | 1.06 | 0.003em | The AI tutor's CURRENT directive ("find deck A's play button"). Inherits the rebuild-session mock's `.now` class register (the `clamp(30px, 3.6vw, 48px)` hero line, scaled down because Learn-window is 1280×720 not the full session surface). The schematic is the hero; the tutor line is the second voice. |
| Body (ghost / receded prior tutor lines) | Saira `wdth 100, wght 400` | **14px** | 400 | 1.4 | 0 | The prior tutor line(s), receded into silk-22 / silk-12 (one or two lines max — same pattern as the rebuild-session mock's `.ghost.g1` / `.ghost.g2`). |
| Body (hint copy) | Saira `wdth 100, wght 400`, italic | **14px** | 400 | 1.4 | 0 | The hand-authored hint text when `data-state="hint"`. Italic distinguishes it from the directive line at a glance (the only italic use in the Learn window — accessibility: italic + position + dock-state-attribute = triple-channel cue). |
| Label (course chip in HUD) | Saira `wdth 85, wght 600`, UPPERCASE | **10px** | 600 | 1.0 | 0.22em | The course identifier (e.g. `COURSE 1 · ANATOMY`). Reuses the `rebuild-session` mock's `.persona .k` label register (10px Saira wdth 85 wght 600 letter-spacing 0.22em UPPERCASE). |
| Mono (progress index in HUD, cite-receipt) | JetBrains Mono | **11px** | 500 | 1.0 | 0.18em UPPERCASE | The lesson index (e.g. `L1.01 OF 16`) and the cite-receipt chip text (e.g. `◂ DECK A PLAY`). Matches P91's status-bar latency-text register exactly. |
| Mono (numeric "I got it" key-hint) | JetBrains Mono | **10px** | 500 | 1.0 | 0.1em UPPERCASE | Faint key-hint glyph next to "I got it" — e.g. `SPACE ↵`. silk-22 at rest, silk-40 on hover. |

**Variable-axis discipline:** As in P91 — all Saira routed through `font-variation-settings: "wdth" N, "wght" M` — never `font-weight: bold`. Test gate `tauri/ui/tests/learn/test_no_inline_font_weight.spec.ts` (NEW, optional — annotated `expect: nice-to-have`).

**Forbidden font choices** (same list as P91): Inter, Roboto, Arial, system-ui, Helvetica, default Tailwind sans. The blocklist `scripts/launch/check_no_tutor_slop.py` (P94 lands the runtime tutor-tone gate, but the *font* discipline is enforced in P92 via the inheritance of P91's test gates).

---

## Color

Inherited verbatim from `91-UI-SPEC.md` § Color (20/80 split, warm-black void dominant, silk secondary, amber accent). **Zero new color tokens** — Critical Constraint #1.

**P91's amber reserved-for list was 5 elements. P92 extends to 7 elements** — and the list HARD-CAPS HERE for v9.0. No phase past P92 grows the amber surface.

**Updated amber reserved-for list (the explicit seven-fingers list):**

1. Keyboard focus ring (inherited from `tokens.css` `*:focus-visible`).
2. Controller-name title under-stroke (the breathing amber light below the wordmark, P91).
3. **`--learn-highlight` CSS variable, NOW LIT in P92 on the highlighted `<g data-control-id>` group** — this is the load-bearing P92 paint. Color via `color: var(--amber)` propagates through `currentColor` to all strokes/fills inside the group. Shape via the `<g class="cue-shape">` slot (P91 scaffolded; P92 paints) renders the 4px-stroke `var(--amber)` pulse-ring.
4. "Controller unplugged" red banner border (destructive — `--led-fault`).
5. "MIDI mirror live" green status pip (OK — `--led-ok`).
6. **NEW: Tutor-speak receipt rule + cite chip** — exactly mirrors the rebuild-session mock's `.receipt .rule` (1px amber-40 → amber linear gradient drawing L→R 360-880ms) and `.cite` chip (amber-pale text on amber-22 border + amber-22 background). The cite chip lights ONLY when the tutor envelope contains a `citations` payload non-empty (LESSON-05 will add citations in P94 once the exemplar engine ships in P93; for the P92 "hello world" 1-step lesson, the lesson script's `tutor_speak[].citations` is the empty array `[]`, so the cite chip does NOT render. The receipt rule still draws — but terminates blunt instead of igniting a chip. **Decision documented for retrospective ratification: the rule-without-cite is the "tutor speaks but has nothing to cite yet" rest state; in P94 once exemplar citations exist, the chip lights at the rule's terminus.**)
7. **NEW: Lesson-HUD progress dots, ACTIVE slot only** — the current lesson's dot fills with `var(--amber)` + `--glow-faint` ring (one 6px solid amber circle). Inactive dots are `var(--silk-22)` outlined empty circles. Completed dots are `var(--silk-65)` solid (NOT amber — completed lessons are not the focus). Adding amber to inactive or completed dots violates the 20/80 rule.

**That is the WHOLE list. Adding amber to an eighth element (e.g. the "I got it" skip button, the lesson title, the hint italic) breaks the 20/80 rule and fails the checker.**

The **"I got it" skip button** is explicitly silk-40 at rest, silk-65 on hover/focus, NEVER amber. Reasoning: it's a fail-safe escape hatch, not a primary CTA. Amber here would teach the user that the skip is the right answer; that breaks pedagogy. Same logic for the lesson title — silk-65 at rest, silk-full when the dock is in `data-state="hint"` (the dock surfaces it).

**Highlight color contract** (RENDER-04 binding):

| Property | Value | Rationale |
|----------|-------|-----------|
| `--learn-highlight` (CSS custom property) | `var(--amber)` | Already declared in P91's `learn.css` line 37 (P91 declared the variable but lit it on NO controls). P92 wires `ipc.learn.highlight` envelope consumers to set this property + the `data-cue-color` / `data-cue-shape` attributes on the target `<g>` group. |
| Pulse-ring stroke color | `var(--amber-65)` (the ring is OUTLINE not FILL — full amber would over-saturate at the schematic's standard 1280×720 zoom level) | Dual-channel cue: color (amber) + shape (4px ring expanding 0.92 → 1.06 over `--motion-led-pulse` 1400ms, ease-in-out, infinite). |
| Pulse-ring stroke width | **4px** at the SVG user-unit scale of the schematic (which means ~3.2 CSS pixels at default zoom on the 1280×720 viewBox). | RENDER-05 dual-channel cue verified by `tauri/ui/tests/learn/test_a11y_highlight_dual_cue.spec.ts` (already shipped in P91; P92 promotes the test from `expect: stub-only` to `expect: live`). |
| Highlight fill (knob bodies, button caps) when `<g>` group has `data-active="lit"` | `color: var(--learn-highlight)` (cascades through `currentColor` to every stroke + fill inside the group) | The CSS-variable swap that P91's stylesheet scaffold (`learn.css` line 142-143) already routes via `currentColor: var(--silk-22) → var(--learn-highlight)`. |

**Dual-channel cue baseline (verified):**

```css
/* learn.css extension landing in P92 — TWO channels per highlight, no
 * amber-only path. Color-blind users (deuteranopia / protanopia / tritanopia)
 * see the ring shape even when they can't distinguish amber from silk. */
.learn-stage svg [data-control-id][data-cue-color="amber"] {
  color: var(--learn-highlight);  /* channel 1: color */
}
.learn-stage svg [data-control-id][data-cue-shape="pulse-ring"] .cue-shape::before {
  /* channel 2: shape — animated stroke expanding from the slot P91 scaffolded */
  content: "";
  position: absolute;
  inset: -4px;
  border: 4px solid var(--amber-65);
  border-radius: 50%;
  animation: learnPulseRing var(--motion-led-pulse) ease-in-out infinite;
}
```

**Forbidden colors** (extends P91's list):

- `#FF7F00` Pioneer brand orange + any hue within 10° (P91 gate `test_no_pioneer_orange.spec.ts` already covers).
- ANY amber-family color on the "I got it" skip button (silk-only — see above rationale).
- ANY amber-family color on hint italic text (silk-only — hint is a fail recovery, not a celebration).
- ANY amber-family color on progress dots for completed or inactive lessons.

---

## Copywriting Contract

All copy in lowercase. NO exclamation marks anywhere in any tutor-facing surface. NO marketing-voice patterns. **Tutor-system-instruction lock (TONE-04, Critical Constraint #3)** forbids the four learned moves at the AI's runtime; the *fixture-author lock* (TONE-02, hand-authored scripts) enforces them at write time. Both gates land in P92.

### Lesson HUD copy

| Element | Copy | Source / notes |
|---------|------|----------------|
| Course chip (left of HUD) | `COURSE <N> · <NAME>` — e.g. `COURSE 1 · ANATOMY` | UPPERCASE auto via CSS `text-transform`. JSON fixture stores normal-case (`course_1`, `Anatomy`). Course 0 = hello-world (the P92 deliverable) is shown as `COURSE 0 · HELLO WORLD`. |
| Lesson title (center of HUD) | `<lesson_title>` — e.g. `press play` (for the P92 "hello world" 1-step lesson) | lowercase, period-FREE (titles don't terminate, sentences do). From `CURRICULUM[lesson_id].title` in `src/vibemix/learn/curriculum.py`. |
| Progress index (right of HUD) | `L<N>.<NN> OF <NN>` — e.g. `L0.00 OF 1` (hello-world has 1 lesson) | JetBrains Mono. The N.NN pattern matches the v9.0 REQ-ID prefix system. |

### Tutor-speak dock copy

| Element | Copy | Source / notes |
|---------|------|----------------|
| Active tutor line (hero) | From `lesson_script.tutor_speak[current_beat].text` — for the P92 hello-world lesson, beat 0 reads: `find deck A's play button — it's lit up on your controller.` | Hand-authored fixture JSON (LESSON-05 / TONE-02 binding). NEVER LLM-generated on the fly. Lowercase, period-terminated, NO exclamation. The em-dash is allowed (the rebuild-session mock uses em-dashes). |
| Ghost lines (prior beats) | Receded prior tutor.text values, capped at 2 lines visible | `.ghost.g1` (most recent prior, silk-22) and `.ghost.g2` (one back, silk-12). When the beat advances, the current line slides INTO `.g1` and the prior `.g1` slides into `.g2` and the prior `.g2` fades out. |
| Empty-state (no lesson active) | (the tutor-speak dock is HIDDEN when no lesson is active — its `data-state="idle"` collapses height to 0) | The Learn window in idle reverts to the P91 layout exactly. The dock only appears on `ipc.learn.lesson_loaded`. |
| Cite chip (P92 hello-world: not rendered; P93+ lit) | `◂ DECK A PLAY` (the wire shape will be `[track:<id>]` or `[exemplar:<track_id>]` once those evidence sources exist) | Mirrors the rebuild-session mock's `.cite` chip exactly. For P92's hello-world lesson, `tutor_speak[].citations` is `[]` → chip does NOT render → receipt rule terminates blunt (a 1px amber-40 line that just stops). |
| Hint copy (when `data-state="hint"` after 3 strikes / 30s) | From `lesson_script.hints[strike_index].text` — for hello-world, three hints pre-authored: `strike 1: deck A is on the left side of your controller.`; `strike 2: look for the triangular play glyph on a square button.`; `strike 3: the play button is the bottom-row leftmost button on most controllers — press it now.` | Hand-authored. NOT generated. Each hint adds ONE concrete piece of information; never repeats earlier hint copy verbatim. |
| Anti-speedrun hint (when user tries to advance under 45s min-dwell) | NO copy surfaced — the "I got it" button is simply non-interactive (visually opacity-0.4, no click handler firing) until 45s elapses. Hover tooltip: `at least 45 seconds per lesson — that's the floor.` | Tooltip is silk-65 JetBrains Mono 10px UPPERCASE. The floor protects the curriculum's pedagogical weight without nagging the user via copy. |

### Skip / "I got it" control copy

| Element | Copy | Source / notes |
|---------|------|----------------|
| "I got it" skip button label | `i got it` | lowercase, no quotes, no period. Mirrors the rebuild-session mock's controls register (10px Saira wdth 85 wght 600 letter-spacing 0.22em UPPERCASE auto via CSS). |
| Key-hint glyph (faint, right of "i got it") | `SPACE` or `↵` (whichever is bound to skip — both work) | JetBrains Mono 10px silk-22 at rest, silk-40 on focus. The hint exists so the user discovers the keyboard shortcut without nagging. |
| Skip-confirmation toast (after click) | (NONE — clicking "i got it" advances the lesson silently; the next tutor line slides in. No "Lesson skipped!" / "Got it, moving on" / "OK!" toast — tutor-slop blocklist territory.) | The advance IS the confirmation. |

### Settings drawer extension copy (the "Reset Learn Progress" row)

| Element | Copy | Source / notes |
|---------|------|----------------|
| Section heading (where the row lives) | The existing `LEARN` section header in the settings drawer (NEW section in P92 — sits between `RECORDING` and `MASCOT` per the existing group ordering). Display text: `LEARN` (UPPERCASE auto). | Reuses `tauri/ui/src/settings/components/group.ts` exactly. NO new component. |
| Row label | `reset learn progress` | lowercase, period-FREE (it's a label, not a sentence). Settings drawer convention. |
| Row body / secondary text | `clears all completed lessons. cannot be undone.` | Two short sentences. The "cannot be undone" wording is the existing drawer's destructive-action convention (see `confirm-dialog.ts` for the precedent — same pattern as `Delete Recording` confirm copy). |
| Destructive confirm dialog heading | `reset learn progress?` | Question form. lowercase. Mirrors the existing recording-delete confirm pattern. |
| Destructive confirm dialog body | `all 36 lessons across 3 courses will reset to not started. your library and DJ profile are not affected.` | Two sentences. Specific count + scope. Honesty: tells the user exactly what's NOT touched. |
| Destructive confirm dialog primary CTA | `reset` | One word, lowercase. NOT "Yes, reset" / "Confirm reset" / "I understand". The verb alone is enough — the dialog is the context. |
| Destructive confirm dialog secondary | `cancel` | One word, lowercase. |
| Post-reset toast | `learn progress reset.` | One sentence, period-terminated. No celebration. No "Done!" — that's tutor-slop in another costume. |

### Forbidden copy patterns (extends P91's list)

- **NO** `great!` / `awesome!` / `perfect!` / `nice!` / `well done!` (the four-tutor-moves locked by TONE-04).
- **NO** `let's start` / `let's begin` / `let's dive in` / `let's go` (the verbatim-opening dialog line "Let's go." is the EXCEPTION — it appears EXACTLY ONCE in the entire v9.0 curriculum, at the close of the iconic 4-line opening — and is enforced by the byte-equality test in P94. Outside the opening, "let's go" is blocklisted.)
- **NO** `today we'll be learning…` / `in this lesson we'll cover…` / `by the end of this lesson…` (these are preamble-tics — pedagogy genuinely benefits from setup, but the lesson title is the only setup the user needs; verbosity here is slop).
- **NO** `now let's…` / `next we'll…` / `coming up…` (previewing-tic).
- **NO** `recap` / `to summarize` / `as we just saw` (summarizing-tic).
- **NO** `don't worry` (the iconic opening's "Oh bestie, don't worry" is the EXCEPTION + ONE-TIME-ONLY; outside that line, "don't worry" is blocklisted because it's the soft-edtech-mascot voice).
- **NO** `please` / `kindly` / `thank you for` (carry-forward from P91 — Learn does not beg).

The runtime blocklist `scripts/launch/check_no_tutor_slop.py` lands in P94 with ≥20 tokens; P92's contribution is the *system instruction lock* that forbids the four learned moves at the AI's runtime composition layer (TONE-04 test gate `tests/learn/test_tutor_system_instruction_lock.py`).

---

## Component Inventory (P92-specific, executor-facing)

NEW components landing in P92. Each one extends the P91 surface; none replaces an existing P91 component.

| Component | File (NEW unless noted) | Purpose | Visual contract |
|-----------|-------------------------|---------|-----------------|
| `LessonHud` | `tauri/ui/src/learn/lesson/hud.ts` | 56px-tall rail between titlebar and stage; mounts on `ipc.learn.lesson_loaded`; clears on `ipc.learn.complete_lesson`. Three regions: course chip (left) · lesson title + progress dots (center) · progress index (right). | Background: subtle hairline-bordered band — `border-bottom: 1px solid var(--glass-edge)` at the bottom, NO panel fill (the void shows through). Matches the rebuild-session mock's `.rail` exactly. Course chip uses persona-block typography (10px Saira wdth 85 wght 600 letter-spacing 0.22em UPPERCASE silk-22). Progress dots row right-of-title: 6px circles, silk-22 outline = pending, silk-65 fill = completed, amber fill + glow = current. |
| `TutorSpeakDock` | `tauri/ui/src/learn/lesson/tutor-dock.ts` | Bottom region below the stage; mounts on `ipc.learn.tutor_speak`; consumes `text`, `tts_marker`, `citations`. Houses the active line + ghost lines + receipt rule + cite chip + "i got it" skip + (when state="hint") the hint italic. | Background: TRANSPARENT (the cinematic void shows through). 1px `var(--glass-edge)` top border. Internal grid: top row = ghost lines (silk-12, silk-22), middle row = active line (`.now` register clamp(24-32px)), bottom row = receipt + skip control. Min-height 120px at rest, 160px when `data-state="hint"`. The dock GROWS DOWN (squeezing the stage's 1fr) — never up. |
| `HighlightOverlay` | EXTENDS `tauri/ui/src/learn/components/controller-stage.ts` (existing P91) | Consumes `ipc.learn.highlight`; flips `data-cue-color` + `data-cue-shape` attributes on the target `<g data-control-id>` group; the CSS-variable cascade (P91 already wired) does the paint. ≤16ms paint budget (composited; no SVG re-render). | **NO** new visual element — the P91 schematic IS the surface. The highlight is a state attribute swap, not a layered DOM node. `cue_color: "amber"` → `[data-cue-color="amber"]`; `cue_shape: "pulse-ring"` → activates the `<g class="cue-shape">` slot P91 scaffolded; `cue_shape: "static-glow"` (alternate channel for reduced-motion) → activates a `<g class="cue-glow">` slot rendering a 1.5px stroke + `--glow-soft` outer shadow. |
| `LessonSkipButton` | `tauri/ui/src/learn/lesson/skip-button.ts` | The "i got it" override. Always-visible, low-ink at rest, full-ink on hover/focus. Wired to `ipc.learn.complete_lesson { reason: "user_skip" }` envelope. Disabled (opacity 0.4, no click) until 45s anti-speedrun min-dwell elapses. | Padded ghost button (no border at rest, silk-22 1px border on hover). 10px Saira wdth 85 wght 600 letter-spacing 0.22em UPPERCASE silk-40 → silk on hover. Key-hint glyph (`SPACE ↵`) silk-22 to the right of the label. Positioned at the right edge of the tutor-speak dock's bottom row, vertically aligned with the receipt rule. |
| `HintExpansion` | inline in `tutor-dock.ts` | Renders when `data-state="hint"` (i.e. after 3 strikes / 30s of no expected action). Pre-authored hint text from the lesson JSON fixture. Distinct visual: italic, silk-65, ONE line max per strike, accumulates (strike 2 adds a SECOND italic line below strike 1's, strike 3 adds a THIRD). | NO new component shell — extends the `tutor-dock` DOM. The hint italic row sits BELOW the active "now" line, ABOVE the receipt rule. The highlight pulse-ring on the schematic intensifies in parallel (amplitude grows from `var(--motion-led-pulse)` 1400ms ease-in-out infinite to a tighter `var(--motion-snap)` 150ms snappy pulse during hint state — a SECOND a11y channel signaling "the system is more actively guiding you now"). |
| `ResetLearnProgressRow` | `tauri/ui/src/settings/components/learn-group.ts` (NEW section in existing drawer) | Adds a `LEARN` group to the existing `SettingsDrawer` between `RECORDING` and `MASCOT`. ONE row: `reset learn progress` label + destructive confirm dialog → `ipc.learn.progress_state { action: "reset" }`. | Reuses `renderSettingsGroup` from `tauri/ui/src/settings/components/group.ts` (exactly the same pattern as `MascotGroup` / `HelpGroup`). Row is silk-65 label + silk-22 secondary line ("clears all completed lessons. cannot be undone."). Click → existing `renderConfirmDialog` ⇒ post-reset toast (reuses existing toast surface). NO new dialog component. |

**P92 components that are NOT built (defer markers):**

- `LessonProgressList` (full course-list browser with "pick up where I left off") — defers to P97 ONBOARD-05. P92 only ships the progress DOTS in the HUD, not the standalone list view.
- `ModePicker` (the main-window-level Co-host / Learn / Build / Debrief switcher) — defers to P97 ONBOARD-01.
- `OpeningDialogSequence` (the verbatim 4-line iconic dialog UI) — defers to P94 CURR-1.01.
- `ExemplarPlayerControls` (play / stop / volume for `ipc.learn.exemplar_play`) — defers to P93 (engine) and P94 (UI surface in the EQ-as-Tutor demo, L1.14). P92 wires only the ENVELOPE SHAPES for `exemplar_play` / `exemplar_stop`, NOT a UI consumer.
- `ControllerHeadphonePicker` (the new wizard row for `learn.headphone_device_index`) — defers to P97 ONBOARD-04.

---

## Lesson HUD layout

```
┌─────────────────────────────── titlebar (56px, P91, unchanged) ────────────────────────────────┐
│  ◂ LEARN              <controller display name>              <clock>                            │
├──── HUD (56px, NEW P92) ──── 1px hairline ────────────────────────────────────────────────────┤
│  COURSE 0 · HELLO WORLD     press play     ● ○ ○ ○ ○ ○ ○            L0.00 OF 1                 │
├──── stage (1fr, P91 schematic, NOW with highlight pulse-ring active) ─────────────────────────┤
│                                                                                                │
│                       ┌─────────────────────────────────────────┐                              │
│                       │   ⊙ ⊙ ⊙  ◯◯◯  ⊙ ⊙ ⊙                       │                              │
│                       │            ▢▢▢▢  ▢▢▢▢                    │     ← amber pulse-ring      │
│                       │   ░░░░  ⟨▶⟩ ⟨◼⟩  ⟨◀⟩  ░░░░                │       on DECK A PLAY button │
│                       │                                          │                              │
│                       └─────────────────────────────────────────┘                              │
│                                                                                                │
├──── tutor-speak dock (auto, NEW P92, min 120px) ──── 1px hairline ───────────────────────────┤
│   crowd was waiting for this one          ← .ghost.g2 (silk-12)                                │
│   the breakdown landed three bars ago     ← .ghost.g1 (silk-22)                                │
│   FIND DECK A'S PLAY BUTTON —             ← .now (silk, the hero line at clamp(24-32px))       │
│   IT'S LIT UP ON YOUR CONTROLLER.                                                              │
│                                                                                                │
│   ─────────────── ◂ DECK A PLAY              i got it  SPACE ↵                                │
│   (receipt rule — drawn 360-880ms)         (silk-40, persistent low-ink)                       │
│                                                                                                │
├──── status bar (40px, P91, NOW with extra segment for advance-state hint) ────────────────────┤
│   pioneer ddj-flx4 · midi mirror live  |  P95: 0.66 ms •  |  waiting for: deck A play          │
└────────────────────────────────────────────────────────────────────────────────────────────────┘
```

ASCII is approximate. The schematic geometry is the real authored SVG — the rectangle is just a placeholder for the diagram.

**Status bar segment 3 changes in P92:** the P91 hint "cmd+tab to deck" is REPLACED (when a lesson is active) with `waiting for: <expected_action human-readable>` — e.g. `waiting for: deck A play`. When no lesson is active, the segment reverts to P91's `cmd+tab to deck` hint. This gives Kaan's ear-pass a *third* live-confirmation surface (alongside the highlight ring + the tutor-speak text).

---

## Hardest UI question — RESOLVED: tutor-speak placement = BOTTOM DOCK

Three options were on the table (per the note to researcher). Decision rationale:

### Option (a) Positional caption — REJECTED

Pros: ties tutor narration directly to the highlighted control (a literal speech-bubble for the AI).
Cons: occludes adjacent schematic geometry on dense controllers (FLX10, XDJ-RX3 have ~80+ controls in 1280×720 — a caption near one EQ knob crops 2-3 neighboring knobs). Forces the eye to dart between the schematic and the caption. Violates `frontend-enforcement` SKILL.md rule 1 ("no Material chat-bubble overlay aesthetic"). Doesn't read as "the AI is talking to you" — reads as "this control has a comment attached."

### Option (b) Bottom dock — ACCEPTED ✓

Pros:
1. **Matches the rebuild-session "Deck Speaks" hero-on-void pattern** verbatim — that mock's `.speak` element (`.ghost.g2` → `.ghost.g1` → `.now` → `.receipt`) IS the proven tutor-speak surface. P91 already inherited the mock's `--motion-led-pulse` and the void-without-cards principle; P92 inherits the speak surface as the next natural step.
2. **Doesn't crop the schematic** — the schematic stays the 1fr middle region; the dock takes only the auto-height needed.
3. **Subtitle-film positioning trains the eye** — film and Twitch subtitles + WebVTT have ~80 years of UX trained into users; tutor-as-subtitle reads instantly.
4. **Receipt rule + cite chip render naturally** — the rebuild mock already proved the L→R rule draw + cite ignite at 360-900ms. P92 adopts that exact choreography for tutor citations (when they exist in P93+).
5. **Sliding ghost lines + active line gives a sense of conversation history** — without becoming a chat log. The user can glance up to see where they've been in the lesson.

Cons:
1. Splits the eye between schematic (top) and tutor text (bottom). MITIGATION: the highlight pulse-ring on the schematic is the *anchor*; the tutor-dock text *names* what the highlight is pointing at. The user looks at the schematic FIRST (the dock text is contextual, not primary). This matches how a real teacher works — the teacher points at the thing, the words come after.
2. Slightly less direct than (a) for "AI talks about THIS specific control." MITIGATION: the cite-receipt rule at the dock bottom + the ANIMATED highlight ring on the control = a visual *line of sight* binding the two surfaces. The eye traces the cite chip → up the schematic → to the pulsing control.

### Option (c) Side panel — REJECTED

Pros: more vertical real estate for long tutor explanations.
Cons:
1. **Eats schematic real estate** — at 1280×720, a 280-320px side panel forces the schematic to a 960×720 viewport, cropping the wide controllers (FLX10, XDJ-RX3). Violates the "schematic IS the surface" P91 baseline.
2. **Reads as a dashboard panel** — exactly the "card with rounded shadow" anti-pattern the frontend-enforcement skill blocks.
3. **The "Deck Speaks" rebuild mock explicitly rejected side panels** — the mock's iteration history (4 iterations from 27/40 → 30/40 critique) collapsed all sidebar/panel surfaces into the hero-on-void pattern.

**DECISION (b) bottom dock + 3-strike hint surface = INLINE EXTENSION of same dock (not a separate overlay).**

The hint state extends the SAME dock — `[data-state="hint"]` adds italic hint lines BELOW the active "now" line, ABOVE the receipt rule. The user never has to look anywhere new. The pulse-ring on the schematic also intensifies (snap-pulse instead of slow-breathe) so the secondary visual cue is doing the heavy lifting on "the system is being MORE assertive now"; the dock copy stays calm.

This also handles the case "user is making a third strike but didn't read the second hint" — the third hint accumulates BELOW the second hint, both still visible. Pre-authored hints are short (≤120 chars each) so three of them fit in the expanded dock without scroll.

---

## Motion + Interaction (P92-specific)

| Motion element | Token / value | Trigger | Purpose |
|----------------|---------------|---------|---------|
| Highlight pulse-ring breathe | `learnPulseRing` 1400ms ease-in-out infinite (re-uses `--motion-led-pulse`). Border-radius 50%, scale 0.92 → 1.06, opacity 0.6 → 1.0. | `ipc.learn.highlight { cue_shape: "pulse-ring" }` envelope | The "look here" signal. Color (amber) and shape (expanding ring) are simultaneously visible — RENDER-05 dual-channel cue. |
| Highlight static glow (reduced-motion fallback) | NO animation; border 1.5px `var(--amber)` + box-shadow `var(--glow-soft)` static | `prefers-reduced-motion: reduce` OR `cue_shape: "static-glow"` | Accessibility: users with vestibular sensitivity see the highlight without motion. The fallback is enforced by the inherited `tokens.css` @media query. |
| Highlight clear | 200ms opacity 1 → 0 + a `transition-property: --learn-highlight, color` ease-out | `ipc.learn.highlight { control_id: null }` (the un-light envelope shape) OR receipt of `ipc.learn.advance` | Smooth release — doesn't snap to silk-22 instantly. |
| Tutor-line rise | `learnTutorRise` 400ms cubic-bezier(.16,1,.3,1). Opacity 0 → 1 + translateY(10px) → 0. | New `ipc.learn.tutor_speak` envelope arrives | Same recipe as the rebuild-session mock's `@keyframes rise` (verbatim). The line settles in feeling deliberate, not a popup. |
| Tutor-line ghost recede | 700ms ease-out color transition (silk → silk-22 → silk-12). When a new line rises, the prior `.now` becomes `.g1` and the prior `.g1` becomes `.g2`; `.g2` fades to opacity 0 over 700ms. | New tutor envelope arrives → cascade prior lines down a register | Atmospheric memory — the user sees the recent lesson breath without a chat log. |
| Receipt rule draw | 520ms cubic-bezier(.22,1,.36,1) with 360ms delay. `transform: scaleX(0) → scaleX(1)` from left. | Tutor line rise (same keyframe as the mock) | The "AI is drawing its receipt" signature gesture. Carried over verbatim from the rebuild-session mock. |
| Cite chip ignite (when citations non-empty) | `learnCiteIgnite` 380ms cubic-bezier(.16,1,.3,1) with 900ms delay. Opacity 0 → 1 + color silk-40 → amber → amber-pale, border + glow + text-shadow modulated. | Tutor line rise WITH a non-empty citations array | The "evidence chip lights at the rule's terminus" gesture. Re-used verbatim from the mock. NOTE: for P92 hello-world, citations is `[]` → chip does NOT render → no ignite animation. P94 lights it once exemplar citations arrive. |
| Hint state expansion | 280ms ease-out (tutor-dock height auto → +40px). | Tutor-dock element receives `data-state="hint"` attribute (set by lesson runtime on 3rd strike or 30s without expected action) | Communicates "I'm being more helpful now" — the dock GROWS DOWN, the stage 1fr absorbs the resize. Hint italic line fades in (300ms opacity 0 → 1) below the active "now" line. |
| Pulse-ring intensify (during hint state) | `learnPulseRingIntense` 600ms ease-in-out infinite. Amplitude 0.86 → 1.10 (vs base 0.92 → 1.06). | Tutor-dock `data-state="hint"` → toggle a `.hint-active` class on the highlighted `<g>` group via the stage component | Secondary a11y channel — the highlight is more emphatic, which a user can perceive via peripheral vision while reading the dock copy. |
| Progress-dot fill transition (lesson completion) | 280ms ease-in-out — dot transitions outline-only (silk-22) → outline + fill (silk-65) over 280ms; if the dot was the CURRENT lesson (amber + glow), the amber-and-glow fades out as the silk-65 fades in. | `ipc.learn.complete_lesson` envelope arrives | The accumulation feedback. Restrained — completed lessons are quiet (silk-65), not celebratory amber. |
| "I got it" hover | 150ms ease-out opacity 0.4 → 1.0, border-color transparent → var(--silk-22). | `:hover` or `:focus-visible` on the skip button | Reveals the affordance without screaming for attention. Same motion register as the rebuild-session mock's `.controls` pattern. |
| "I got it" min-dwell lockout release | Instant (no animation; the disabled state is replaced by the active state at the 45s mark) | `min_dwell_elapsed_at` reached | The lockout is a binary — communicating "you can do it now" via a fade would feel like a permission grant; instant unlock just *lets it work*. |
| Settings reset confirmation dialog appear / dismiss | Inherits existing `renderConfirmDialog` motion (200ms ease-out opacity + scale 0.96 → 1.0). | User clicks "reset learn progress" row | Re-uses the existing pattern. |
| Reset post-confirmation toast | 320ms ease-out opacity 0 → 1 + translateY(8px) → 0, holds 3s, then 240ms ease-in opacity 1 → 0. | `ipc.learn.progress_state { action: "reset_ack" }` arrives | Quiet acknowledgment. Same recipe as existing recordings-delete toast. |

**Forbidden motion** (extends P91's list):

- **NO confetti** on lesson completion, recital pass, or course graduation. Pedagogy-grade celebration via copywriting only ("course 1 done." — see P94 for the actual completion copy).
- **NO "ding" / chime sound effects** on highlight-paint, lesson-advance, or hint-trigger. The Learn window is silent (the exemplar audio in P93+ is the ONLY audio surface from Learn). Sound effects are tutor-slop in audio costume.
- **NO bouncing arrows / wiggling glyphs** pointing at the highlighted control. The pulse-ring is the entire visual call-to-action.
- **NO progress-bar fill animation** at the end of a lesson. The dot's silk-22 → silk-65 fill is the whole reward.
- **NO confetti on the iconic opening dialog** when it lands in P94. The dialog speaks for itself; visual flourishes would undermine the verbatim weight Kaan locked.

---

## Accessibility Contract (RENDER-04 + RENDER-05 binding, extends P91)

| Surface | Requirement | Test gate |
|---------|-------------|-----------|
| Highlight envelope reception → paint within 16ms | `tauri/ui/tests/learn/highlight-paint.test.ts` (NEW) — measures `ipc.learn.highlight` receive timestamp → next-rAF paint timestamp. CI red >16ms P95. | RENDER-04 binding |
| Dual-channel cue (color + shape) on EVERY highlight envelope | The envelope schema requires BOTH `cue_color` AND `cue_shape` (no envelope ships only one channel). `cue_color` enum: `"amber" \| "warning"`. `cue_shape` enum: `"pulse-ring" \| "static-glow"`. Static-glow is the auto-substitute for `prefers-reduced-motion: reduce`. | RENDER-05 promotion — P91 shipped `test_a11y_highlight_dual_cue.spec.ts` as `expect: stub-only`; P92 promotes to `expect: live`. |
| Lesson HUD progress dots are keyboard-navigable | `<button>` elements, Tab cycles through completed + current + pending dots; Enter on a *completed* dot fires `ipc.learn.start_lesson { lesson_id, level: "replay" }` envelope (replay a completed lesson). Enter on a *current* dot is a no-op (already there). Enter on a *pending* dot is a no-op + tooltip `prerequisite lessons not yet complete.` | `tauri/ui/tests/learn/test_hud_progress_dots_keyboard.spec.ts` (NEW) |
| Tutor-speak dock screen-reader announcement | New `data-state="active"` → emits the active tutor line on the existing `<div aria-live="polite" aria-atomic="true">` region P91 already wires (`#learn-sr-announcement`). Subsequent tutor lines REPLACE the announcement content (atomic = true, so the SR reads each new line in full). | `tauri/ui/tests/learn/test_tutor_speak_sr_announcement.spec.ts` (NEW) |
| Hint state SR announcement | When `data-state="hint"` activates, announce: `hint <N>: <hint text>` on the same aria-live region. Strike 1 / 2 / 3 each fire ONCE (no repeat announcements if the hint state persists). | Same SR test (above) covers |
| "I got it" skip button keyboard discoverability | Reachable via Tab order (Tab cycles: titlebar wordmark → controller name (skip if empty) → clock → course chip → progress dots → progress index → schematic data-control-id groups → tutor-line (focusable via tabindex=0 for SR scroll, no interaction) → "i got it" button → status bar). The Space and Enter keys both fire the click handler when focus is on the button. | `tauri/ui/tests/learn/test_keyboard_skip_reachable.spec.ts` (NEW) |
| 45s min-dwell visual indication | The "i got it" button has `aria-disabled="true"` during the lockout + `data-min-dwell-locked="true"` attribute. Hover-tooltip explains: `at least 45 seconds per lesson — that's the floor.` On unlock: aria-disabled is removed; no SR announcement (silent unlock). | `tauri/ui/tests/learn/test_min_dwell_aria.spec.ts` (NEW) |
| Color contrast (tutor-speak hero line, hint italic) | Tutor `.now` line silk (`#d6cfc7`) on void (`#020205`) = WCAG AAA at 24-32px. Hint italic silk-65 on void = AA Large at 14px. The hint italic falls below AAA at 14px — accepted because hint is supplementary (the highlight ring + the active `.now` line are the primary channels). | `tauri/ui/tests/learn/test_contrast_p92.spec.ts` (NEW) |
| Reduced-motion fallback | `prefers-reduced-motion: reduce` → (1) pulse-ring becomes static-glow (no animation, 1.5px stroke + glow-soft); (2) tutor-line rise becomes instant opacity swap; (3) ghost-recede becomes instant color set; (4) cite ignite becomes instant opacity 1 (no flash); (5) progress-dot fill becomes instant. The `--motion-led-pulse` token is already overridden by `tokens.css` @media query to NOT freeze (it's a sign-of-life signal); P92 inherits. | Inherited from `tokens.css` lines 357-368 |
| The 3-strike hint surface is not announced for the same strike twice | If user lingers on strike 2 for 2 minutes, no re-announcement. New announce only when strike state INCREMENTS or RESETS. | Same SR test |
| Settings drawer reset row is reachable | Tab order through existing drawer: ... → LEARN section header → reset row label (focusable) → reset confirm dialog (already keyboard-trapped per existing dialog component). | Reuses existing `tauri/ui/tests/settings/*` keyboard-nav suite (already covers `MascotGroup`, `HelpGroup` etc.) |

---

## Registry Safety

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| shadcn official | none (project uses no shadcn) | not applicable |
| Third-party shadcn registries | none | not applicable |

**P92 adds ZERO new JS dependencies** (Critical Constraint, anti-creep acid test §12). The new IPC envelopes ride existing ws:8765 + the existing `IpcRouterBus`; the new lesson runtime uses the ONE-and-only new Python dep (`python-statemachine ^3.1.2` — server-side only, zero JS surface). No `npm install` runs in P92.

**Test gate inherited:** `tests/repo/test_no_new_npm_deps.py` (if not present, MAY land in P92 as a regression guard — annotated `expect: nice-to-have`).

---

## Wiring contract (executor-facing — what each new envelope paints)

The 11 NEW `ipc.learn.*` envelopes (P91 already shipped 2: `controller_detected` and `midi_position`) each have a precise UI consumer. Documented so the planner can copy these into PLAN tasks verbatim.

| # | Envelope | Direction | UI consumer | Visual paint |
|---|----------|-----------|-------------|--------------|
| 3 | `start_course` | shell → sidecar | (none — fires Python lesson runtime) | No paint (out-of-band — the sidecar replies with `lesson_loaded` for the first lesson) |
| 4 | `start_lesson` | shell → sidecar | (none — Python LessonRuntime jumps to lesson_id) | No paint (sidecar replies with `lesson_loaded`) |
| 5 | `complete_lesson` | bidirectional | `LessonHud` (progress-dot fills), `TutorSpeakDock` (collapses to next lesson's first tutor line) | Progress dot transitions silk-22 outline → silk-65 fill over 280ms ease-in-out; next lesson's first `tutor_speak` envelope arrives shortly after and the dock content updates |
| 6 | `lesson_loaded` | sidecar → shell | `LessonHud` (mount/refresh), `TutorSpeakDock` (mount if first lesson), `LessonSkipButton` (reset 45s min-dwell timer) | HUD renders with the new course chip + lesson title + progress index + dots. Dock mounts if previously idle. Skip-button enters lockout state (opacity 0.4) until 45s elapses. |
| 7 | `highlight` | sidecar → shell | `HighlightOverlay` (data-attr swap on the target `<g data-control-id>` group) | Pulse-ring fires (or static-glow if reduced-motion). ≤16ms paint. |
| 8 | `advance` | bidirectional | `LessonHud` (progress dot fills + advances to next dot), `TutorSpeakDock` (active line transitions to next), `HighlightOverlay` (clears current, prepares next) | Dot fill + ghost-recede + new tutor-line rise + new receipt-rule draw all sequenced on a 700ms-ish settle window. |
| 9 | `ack` | shell → sidecar | (none — confirms user touched the right control to the sidecar; sidecar replies with `advance`) | No paint (out-of-band) |
| 10 | `tutor_speak` | sidecar → shell | `TutorSpeakDock` (active line replace; receipt rule + cite chip if citations non-empty) | New `.now` line rises (400ms cubic-bezier rise + 360-880ms receipt-rule draw + 900ms cite ignite when citations exist). Prior `.now` recedes to `.g1`; prior `.g1` recedes to `.g2`; prior `.g2` fades out. |
| 11 | `exemplar_play` | sidecar → shell | (P92: log-only — envelope shape ships but no UI consumer until P93's `ExemplarPlayerControls`) | No paint in P92 (engine + shape only) |
| 12 | `exemplar_stop` | sidecar → shell | (P92: log-only) | No paint in P92 |
| 13 | `progress_state` | bidirectional | `LessonHud` (re-render progress dots), `ResetLearnProgressRow` (post-reset toast on `action: "reset_ack"`) | Dot states refresh from authoritative server snapshot. On reset_ack: toast `learn progress reset.` slides in for 3s. |

---

## Wiring the existing settings drawer (the "Reset Learn Progress" row)

Mirroring the existing patterns at `tauri/ui/src/settings/SettingsDrawer.ts` lines 65-75 (`MascotGroup`, `HelpGroup`, `PerformanceGroup`):

```ts
// NEW: tauri/ui/src/settings/components/learn-group.ts
import { renderSettingsGroup } from "./group.js";
import { renderConfirmDialog } from "./confirm-dialog.js";
import { emitIpc } from "../../ipc/client.js";

export function LearnGroup(): HTMLElement {
  const resetRow = document.createElement("button");
  resetRow.className = "vmx-settings-row vmx-settings-row--destructive";
  resetRow.innerHTML = `
    <div class="vmx-settings-row__label">reset learn progress</div>
    <div class="vmx-settings-row__secondary">clears all completed lessons. cannot be undone.</div>
  `;
  resetRow.addEventListener("click", () => {
    renderConfirmDialog({
      heading: "reset learn progress?",
      body: "all 36 lessons across 3 courses will reset to not started. your library and DJ profile are not affected.",
      primaryLabel: "reset",
      secondaryLabel: "cancel",
      destructive: true,
      onConfirm: () => {
        emitIpc("ipc.learn.progress_state", { action: "reset" });
      },
    });
  });

  return renderSettingsGroup({
    header: "LEARN",
    children: [resetRow],
  });
}

// Then in SettingsDrawer.ts insertion order: between RECORDING and MASCOT.
```

The destructive row class `--destructive` already exists in the settings stylesheet (used by recording-browser's delete pattern). No new CSS — only the new `LearnGroup` module.

---

## Open Decisions Flagged for Retrospective Ratification (autonomous-mode best-judgment calls)

Per `gsd-autonomous fully` mode + the note that Kaan ratifies grey-area calls retrospectively, the following were decided without blocking:

| # | Decision | Rationale | Ratify by |
|---|----------|-----------|-----------|
| 1 | **Tutor-speak surface = bottom dock (Option B)**, NOT positional caption (A) and NOT side panel (C). | The rebuild-session "Deck Speaks" mock already proved this pattern visually + critique-passed it 30/40. Subtitle-film positioning trains the eye via 80 years of UX precedent. Doesn't crop the schematic. Stays a quiet sibling of the schematic surface. | P92 ear-pass session (after the 1-step "hello world" lesson runs live) |
| 2 | **3-strike hint surface = INLINE extension of the same tutor-dock**, NOT a separate overlay. Visually: italic lines accumulate below the active "now" line; pulse-ring intensifies (snap-pulse vs slow-breathe). | Two-surface fragmentation is the AI-slop tell ("oh look, a popup is offering me a hint!"). One surface, one mental model. The dual a11y channel (italic copy + intensified pulse) covers reduced-motion + color-blind users without doubling the UI. | P92 ear-pass session |
| 3 | **Amber on lesson-HUD progress dots is RESERVED-LIST element #7 (the current/active lesson dot only)**. Completed dots are silk-65; pending dots are silk-22 outline. NOT amber for completion. | Pedagogy: completion is the floor, not the ceiling. Amber on completed lessons would train the user that "more amber dots = better" — anti-pedagogy. Amber stays the "here you are right now" beacon, exactly mirroring its session-deck role. | Phase 94 UI-SPEC (first time multiple lessons exist) |
| 4 | **"I got it" skip button is SILK-FOREVER**, never amber. Persistent low-ink (opacity 0.4 ghost) at rest, full ink (opacity 1) on hover/focus. | The escape hatch is a fail-safe, not a primary CTA. Amber would teach "skip is the right answer." silk-40 + key-hint glyph signals "this exists but isn't the goal." | P92 ear-pass session |
| 5 | **45s anti-speedrun min-dwell is a hard floor with NO countdown timer visible.** The "i got it" button is disabled at opacity 0.4 + aria-disabled; hover-tooltip explains. | Countdown timers train rushing ("3 more seconds till I can skip!"). The floor protects the curriculum; the silence protects the user. | P92 ear-pass session |
| 6 | **Lesson HUD takes 56px (same as `--titlebar-h`).** | Visual rhythm: two equal-height chrome rows above the schematic reads as "double titlebar" — the user understands the HUD is meta-information, not a third content surface. Going thinner (40px) would crowd the course chip + progress dots + index. Going thicker (72px+) would eat schematic real estate. | P92 ear-pass session |
| 7 | **Tutor-dock min-height 120px at rest, 160px in hint state.** | 120px fits two ghost lines + the active `.now` line + receipt rule + skip-row without scroll. 160px fits the same + 1 hint italic line + (potentially) 2 more accumulated hints. Going smaller crops the hero line; going taller eats schematic real estate. | P92 ear-pass session |
| 8 | **Cite chip does NOT render in P92's "hello world" lesson** (citations array empty). Receipt rule still draws + terminates blunt. | The hello-world lesson is about "press deck A play" — there's no library track to cite. Lighting a fake chip would be slop. P94+ (once exemplar engine ships in P93) is where the chip lights. The rule-without-chip = honest "tutor speaks but has nothing to cite yet." | P93 / P94 (first phase where citations exist) |
| 9 | **Highlight pulse-ring stroke width = 4px in SVG user units** (≈3.2 CSS pixels at default zoom on the 1280×720 viewBox). | Thin enough to not over-saturate; thick enough to read in peripheral vision while the user looks at the dock copy. Matches the rebuild-session mock's restraint discipline. | P92 ear-pass session |
| 10 | **Status bar segment 3 swaps from `cmd+tab to deck` (P91) → `waiting for: <expected_action>` (P92, when lesson active)**. | Gives Kaan's ear-pass a third live-confirmation surface alongside the highlight ring + tutor copy. Disappears (reverts to P91 hint) when no lesson is active. | P92 ear-pass session |
| 11 | **Italic for hint copy is the ONLY italic in the Learn window** (and so the ONLY italic in v9.0 Learn-mode surfaces). | Triple-channel a11y cue (color silk-65, position below active line, italic style) for users who miss one channel. Italic is otherwise blocked in the design system. | P92 ear-pass session |
| 12 | **No completion-celebration animation, sound, or copywriting.** Lesson-complete = dot fills silk-65, next lesson loads. Course-complete = (will be defined in P94 — but no confetti). | Anti-tutor-slop fundamentalism. The user knows they completed it; the system doesn't need to perform for them. | P94 UI-SPEC (first multi-lesson surface) |

---

## Anti-creep acid test self-check (Critical Constraint compliance)

| Constraint | This SPEC complies because... |
|------------|-------------------------------|
| 1. No new design tokens | Every color, spacing, motion value cited above is already in `tauri/ui/src/tokens.css`. The "Reset Learn Progress" row uses existing settings-drawer tokens. The progress-dot animations use `--motion-led-pulse` (existing). |
| 2. Inherit P91 "Deck Speaks" aesthetic | The bottom dock pattern is lifted verbatim from `mocks/vibemix-rebuild-session.html` `.speak` element. The HUD is a quiet sibling of the existing P91 titlebar. NO card-chrome, NO Material chat bubbles, NO centered hero-card. |
| 3. Tone copy lock (lowercase, no exclamations, no tutor-slop tics) | Every label, every body line, every confirm-dialog string written in lowercase. Zero exclamation marks. Zero "great!" / "let's go" / "today we'll be learning". The four-forbidden-moves list is enforced at the AI's system instruction level (TONE-04). |
| 4. Dual-channel cue | The `cue_color` + `cue_shape` envelope fields are MANDATORY (no envelope ships only one channel). The static-glow alternative covers reduced-motion. Verified by P91's `test_a11y_highlight_dual_cue.spec.ts` (promoted from stub to live). |
| 5. ≤16 ms highlight paint | CSS-variable swap on `<g data-control-id>` attribute — composited, no SVG re-render. Pinned by `tauri/ui/tests/learn/highlight-paint.test.ts` (NEW). |
| 6. Apache-clean | All amber instances are `var(--amber)` (`#ff8a3d`), NOT Pioneer brand orange `#FF7F00`. No new SVG faceplate artwork in P92 — the P91 schematics are the surface and were already Apache-clean. The lesson HUD + tutor dock + skip button are pure DOM (no SVG manufacturer art). |
| 7. Skip + hint discipline | "I got it" always present, motor-impaired-safe. 3-strike progressive hint pre-authored in JSON. ≥45s min-dwell hard-floored. No time pressure ever shown. |
| 8. Saira + JetBrains Mono ONLY | Every typography role above cites either Saira (`--type-display` / `--type-body`) or JetBrains Mono (`--type-mono`). NO Inter / Roboto / system-ui. Reuses P91's font ramp exactly. |

---

## Checker Sign-Off

- [ ] Dimension 1 Copywriting: PASS
- [ ] Dimension 2 Visuals: PASS
- [ ] Dimension 3 Color: PASS
- [ ] Dimension 4 Typography: PASS
- [ ] Dimension 5 Spacing: PASS
- [ ] Dimension 6 Registry Safety: PASS

**Approval:** pending
