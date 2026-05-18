# Phase 50 UI-SPEC: E2E Report.html + Mascot Visual-Diff Snapshots

**Created:** 2026-05-18
**Mode:** `/gsd-autonomous fully` — auto-accept design decisions; no AskUserQuestion pauses.

## Surface in Scope

This phase produces TWO visual surfaces — both internal-tooling, not user-facing app UI:

1. **`dist/e2e-macbook-runs/<UTC>/report.html`** — structured e2e report. Read by Kaan + CI gate; consumed by `scripts/e2e/check_e2e_report.sh`.
2. **Visual-diff snapshots** at `tests/e2e/macbook/__snapshots__/` — Playwright-captured PNGs of Tauri+Three.js production surfaces. Baselines, not visible UI.

The PRODUCTION Tauri app UI is NOT redesigned in this phase. Phase 50 only validates existing surfaces visually.

---

## 1. Layout

### `report.html`
Single-page structured report. No tabs, no JS routing, no client-side state — static HTML + scoped CSS.

```
┌──────────────────────────────────────────────────┐
│  vibemix e2e — <UTC run ID>                      │  ← header (Geist Mono, brand black bg)
│  build: <git sha>  ·  dmg: <path>  ·  duration   │
├──────────────────────────────────────────────────┤
│  OVERALL STATUS: PASS / FAIL                     │  ← single status pill, top-right of header
├──────────────────────────────────────────────────┤
│  Functional      PASS  · 12/12 assertions        │  ← 5 dimension rows
│  Visual          PASS  ·  7/7 snapshots in band  │
│  Aesthetic       PASS  ·  Nielsen 10 ✓           │
│  Usability       PASS  ·  Onboarding 47s ≤ 60s   │
│  Hallucination   PASS  ·  Gate 2b green          │
├──────────────────────────────────────────────────┤
│  Privacy fixture: 0 writes to off-limits paths ✓ │  ← invariant row
│  Anti-slop:       report.html clean ✓            │
├──────────────────────────────────────────────────┤
│  ▼ Details (collapsible <details> per dimension) │
│      ▼ Functional — log of 12 assertions         │
│      ▼ Visual — thumbnail strip + diff %         │
│      ...                                          │
└──────────────────────────────────────────────────┘
```

### Mascot Snapshot Pages
No layout — they ARE the layout. Playwright navigates to `tauri://localhost/mascot` test routes, captures full-page PNG at 1024×768 fixed viewport.

---

## 2. Typography

**Family stack:** `'Geist Mono', 'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, monospace` for report (test-report aesthetic, fixed-width tabular feel).

**Scale (report.html):**
- `--font-h1`: 18px / 1.3 line-height — header title
- `--font-h2`: 14px / 1.4 — dimension row labels
- `--font-body`: 13px / 1.5 — detail text
- `--font-caption`: 11px / 1.4 — timestamps, build sha, file paths

**Weights:** 400 (body), 500 (labels), 600 (status pill + headers). No italics. No 700+ — keep it understated.

**Anti-slop applies to ALL strings:** no "deeply", no "thoughtfully", no marketing-prose adjectives. Test reports speak in nouns + verbs + numbers.

---

## 3. Color

Borrowed from vibemix CDJ Whisper direction — Pioneer-grade hardware in library mode (memory `project_visual_direction_cdj_whisper`). Slightly desaturated for internal-tooling distinction.

| Token | Value | Use |
|-------|-------|-----|
| `--bg`        | `#0A0A0A` | page background |
| `--bg-card`   | `#141414` | dimension rows |
| `--border`    | `#222`    | row separators |
| `--text`      | `#E8E8E8` | body text |
| `--text-dim`  | `#777`    | timestamps, captions, paths |
| `--accent`    | `#F2A03D` | brand amber — used ONLY on status pill PASS state + header underline |
| `--ok`        | `#73C47B` | small inline PASS dots in dimension rows |
| `--fail`      | `#E15555` | FAIL pill / row dot |
| `--warn`      | `#E0B341` | partial / skipped |

**Status pill rule:** PASS = `--ok` background + black text; FAIL = `--fail` background + white text; PARTIAL = `--warn`. ONE pill at top — dimension rows use 8px colored dots, not pills (visual hierarchy).

---

## 4. Spacing

**Scale:** 4px base. Use `--space-1` through `--space-8` (4, 8, 12, 16, 24, 32, 48, 64).

| Element | Value |
|---------|-------|
| page padding (desktop) | `--space-5` (24px) |
| section gap | `--space-6` (32px) |
| row internal padding | `--space-4` (16px) horizontal · `--space-3` (12px) vertical |
| label-to-value gap | `--space-4` (16px) |
| `<details>` indent | `--space-5` (24px) |

Max content width: `880px` centered. Report is a document, not a dashboard — no wide tables, no two-column layouts.

---

## 5. Copywriting

**Voice:** Terse engineering log. Not friendly, not corporate. No emojis. No "✨" "🎉" anywhere.

**Approved patterns:**
- `Functional   PASS   12/12 assertions`
- `Visual       FAIL   1/7 snapshots out of band (mascot.alert_quick_turn: 3.1% diff > 2.0%)`
- `Privacy fixture: 0 writes to off-limits paths`
- `Gate 2b: green (last run 2026-05-18T14:32:11Z)`

**Banned vocabulary (sibling anti-slop script `check_no_slop_e2e.py` enforces):**
- Adverbs: `deeply`, `thoughtfully`, `seamlessly`, `effortlessly`, `elegantly`, `beautifully`
- Hype nouns: `experience`, `journey`, `magic`, `delight`
- Filler verbs: `crafted`, `curated`, `unleashes`, `empowers`
- Same 15-token blocklist as canonical `check_no_ai_slop.py` + `\bdeeply\s+\w+` regex

**Section labels — locked:**
- `Functional` (NOT "Functionality Tests" / "Behaviors")
- `Visual` (NOT "Visual Regression")
- `Aesthetic` (NOT "Look & Feel")
- `Usability` (NOT "User Experience")
- `Hallucination` (NOT "AI Quality" / "Grounding")

---

## 6. Design System Decisions

### No component library
report.html is a single template at `tests/e2e/macbook/report_template.html` rendered server-side by a Python helper (`tests/e2e/macbook/render_report.py`). No React, no Tailwind, no build step. Inline `<style>` block with the tokens above. ~150 lines total.

### Why?
- Report ships in CI artifacts; consumers can open it offline with zero JS.
- Sibling-script precedent — keep tooling thin (memory `feedback_no_scope_creep_clean_utility`).
- Anti-slop coverage simpler against a single template than a component tree.

### Snapshot capture
Playwright config (`tests/e2e/macbook/playwright.config.ts`):
- `viewport: { width: 1024, height: 768 }` — fixed across CI hosts
- `deviceScaleFactor: 2` — Retina baseline so AS Mac snapshots match Intel
- `colorScheme: 'dark'` — vibemix is dark-only
- `reducedMotion: 'reduce'` — kills mascot animation jitter for pixel-stable baselines

### Pixelmatch policy
- `maxDiffPixelRatio: 0.02` (REQ E2E-03 verbatim)
- Threshold per channel: `0.1` (standard)
- Antialiasing: enabled

### Snapshot path convention
- `tests/e2e/macbook/__snapshots__/<test-name>--<platform>.png`
- Platform tag: `darwin-arm64` / `darwin-x64` / `win32-x64`
- Diff outputs (CI artifact only): `dist/e2e-macbook-runs/<UTC>/diffs/<test-name>--<platform>.diff.png`

---

## 7. Accessibility

Report.html is keyboard-navigable (`<details>` is native). Color contrast on text against `--bg`: `#E8E8E8` on `#0A0A0A` ≈ 17.4:1 (AAA). Status pill text against pill background ≥ 4.5:1 (AA). No reliance on color alone — every PASS/FAIL has text label.

---

## 8. Implementation Notes for Planner

- Template file: `tests/e2e/macbook/report_template.html` — Jinja2 (already used by sidecar tests elsewhere).
- Renderer: `tests/e2e/macbook/render_report.py` — pure stdlib + Jinja2; emits HTML to `dist/e2e-macbook-runs/<UTC>/report.html`.
- CSS lives inline in the template — single file, no asset pipeline.
- Anti-slop gate `scripts/audit/check_no_slop_e2e.py` runs ONLY against `dist/e2e-macbook-runs/**/report.html` to avoid double-coverage with existing slop gates.
- Snapshot baseline GLBs: `tauri/ui/assets/mascot/animations/` (Phase 47 placeholders). Re-baseline trigger documented in CONTEXT.md `<deferred>`.

---

## 9. Out of Scope (Don't Build)

- Pretty charts / sparklines — pure text + status dots only.
- Real-time updating — report is captured at end-of-run; no live mode.
- Multi-run history view — each run is one self-contained `report.html`; cross-run analysis is `grep` over the directory tree.
- Email/Slack render — same HTML, different consumer. Defer.
- Light mode — vibemix is dark-only by direction.
- Custom fonts hosted from CDN — `Geist Mono` is system-fallback OK; no external network in report (offline-readable).

---

## 10. Verification (6 Dimensions Self-Check)

| Dimension | Status | Note |
|-----------|--------|------|
| Layout | LOCKED | Single-page document, 880px max width, 5 dimension rows + invariants row + collapsible details |
| Typography | LOCKED | Geist Mono stack, 4-step scale (18/14/13/11), weights 400/500/600 |
| Color | LOCKED | 10-token palette, ONE accent (amber `--accent`), status semantic colors |
| Spacing | LOCKED | 4px base, `--space-1..8`, page padding 24px, section gap 32px |
| Copywriting | LOCKED | Terse engineering log, anti-slop blocklist absolute, section labels fixed |
| Design System | LOCKED | No component library, single Jinja2 template, inline CSS, no build step |

UI-SPEC complete. Planner consumes this as design contract for plans touching `report.html` rendering, snapshot capture config, and anti-slop sibling script.

---
*Generated under `/gsd-autonomous fully` — autonomous design decisions per CDJ Whisper direction (`mocks/vibemix-direction-final.html` baseline) adapted for internal-tooling test-report aesthetic.*
