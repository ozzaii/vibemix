---
phase: 70-github-sexified-generated-tested
plan: 03
wave: 2
subsystem: docs/landing (GitHub Pages) + CI + KAAN-ACTION
requirements: [GH-02]
tags: [frontend, cdj-whisper, github-pages, lighthouse, a11y, ci, kaan-action]
status: SHIPPED
dependency_graph:
  requires:
    - 70-02 (og-card.png — the landing's og:image)
  provides:
    - docs/landing/index.html (the Pages site root — hero + demo + install CTA + waitlist + footer)
    - .github/workflows/lighthouse.yml (local-build Lighthouse gate a11y>=95/perf>=90 + anti-backsliding grep)
    - KAAN-ACTION-LEGAL.md §V7-LANDING (4 soft Kaan-discharge items)
  affects:
    - 70-05 (GH-05 presence suite pins docs/landing/ + lighthouse.yml)
tech_stack:
  added:
    - none (buildless static HTML/CSS/JS; lighthouse@12 is CI-side only — NOT a Python dep)
  patterns:
    - single-file no-build CDJ-Whisper landing (mocks/*.html precedent)
    - SHA-pinned-actions CI posture lifted from packaging-audit.yml
    - §V7-LIVE 6-section soft-discharge cluster shape
key_files:
  created:
    - docs/landing/index.html
    - .github/workflows/lighthouse.yml
  modified:
    - KAAN-ACTION-LEGAL.md (append-only — §V7-LANDING cluster)
decisions:
  - "CSS+JS inline in index.html (UI-SPEC discretion #5: best for perf/CLS, matches mock precedent) — did NOT create separate style.css/app.js"
  - "Demo poster points at the existing docs/assets/demo-placeholder.gif (demo-poster.png is Wave 3 / GH-01) to keep the <video> non-broken now"
  - "og:image + footer links use repo-relative / bravoh-ai/vibemix forms (Pages-safe + matches README badge convention) rather than the ozzaii origin"
  - "lighthouse pinned via npm install -g lighthouse@12 (not npx --yes) — explicit + reproducible"
metrics:
  duration: ~35 min
  completed: 2026-05-24
  tasks: 3
  commits: 4
---

# Phase 70 Plan 03: GitHub Pages Landing (GH-02) Summary

A buildless single-file CDJ-Whisper GitHub Pages landing (`docs/landing/index.html`) that grabs a stranger in 30 seconds — hero pitch + recessed-glass demo window + amber install CTA (brew/scoop one-liners with vanilla copy-to-clipboard) + default-OFF opt-in Bravoh-waitlist + OSS footer — gated in CI by a local-build Lighthouse run (a11y≥95 / perf≥90) plus a fail-fast anti-backsliding grep, with the live-URL run, Kaan-felt aesthetic sign-off, real waitlist URL, and repo social-preview routed to a new `§V7-LANDING` soft-discharge cluster.

## What shipped (per task)

### Task 1 — `docs/landing/index.html` (commit `d5d7877`)
Buildless single-file static site. `:root` tokens lifted **verbatim** from `mocks/vibemix-direction-final.html` (5 warm blacks, amber `#ff8a3d`, silk, glass tiers, `--sp-*`, `--rad-*`, the body cinematic vignette, the two-layer `feTurbulence` film-grain, the `.btn`/`.btn.on` anodised treatment, the recessed `.display-window`, the conic-gradient `.border-anim` perimeter sweep). Saira + JetBrains Mono via the exact Google Fonts `<link>` + `preconnect` from the mock.

**UI-SPEC sections implemented:**
- **Header** — sticky meta-bar: vibemix wordmark + the single amber brand LED (`brandPulse 5s`) + mono version tags.
- **§1 Hero** — two-zone `grid 1.1fr 1fr` (collapses ≤900px), the 30-sec pitch headline (`THE ONLY AI CO-HOST` / amber accent `THAT ACTUALLY LISTENS`), the subhead with one amber `<em>` keyword. Hero `clamp(40px,9vw,88px)` so it never overflows a 360px phone.
- **§2 Demo embed** — recessed `.display-window` glass with the `.border-anim` amber sweep + the README `<video controls muted playsinline poster>` pattern with an `<img>` fallback (descriptive alt), `aspect-ratio:16/9` to avoid CLS, "demo film coming soon" caption.
- **§3 Install CTA** — amber `.btn.on` primary `GET VIBEMIX` + a recessed JetBrains-Mono code tile (`brew install bravoh-ai/tap/vibemix` / `scoop install vibemix`, tabular-nums, `user-select:all`) with a vanilla copy-to-clipboard affordance (degrades to selectable text via `user-select:all` if `navigator.clipboard` is absent), plus a secondary "or download from GitHub Releases" link (Discretion #1).
- **§4 Waitlist** — secondary silk tile (NO amber by default); amber lights only on hover/focus; the UTM outbound link (`utm_source=vibemix&utm_medium=landing&utm_campaign=oss`) fires only on click; **zero analytics/tracking script auto-loads on page view** (default-OFF funnel rule).
- **Footer** — JetBrains-Mono OSS links (GitHub · Contributing · License Apache-2.0 · Security · Code of Conduct) + a static ok-LED + the tagline.
- **a11y contract** — `<html lang="en">`, one `<h1>`, sequential `<h2>`s (no skipped levels), exactly one header/main/footer, `<section aria-labelledby>`, skip link, viewport + description meta + descriptive title, `aria-hidden="true"` on the grain/LED/border decoratives, `aria-label` on copy buttons, **visible amber `outline:2px solid var(--amber)` focus rings via `:focus-visible`** (no bare `outline:none`), 44px min touch targets on CTA + waitlist + copy buttons, and a `@media (prefers-reduced-motion: reduce)` block that kills all animation/transition.
- **og:image** — `<meta property="og:image" content="../assets/og-card.png">` (+ twitter:image, og:title, og:description) referencing the Wave-1 hash-pinned card.

### Task 2 — `.github/workflows/lighthouse.yml` (commit `f93eac4`)
Lighthouse against a **LOCAL** static-server build (`python3 -m http.server 8099 --directory docs/landing`) — Pages isn't enabled in CI (CONTEXT reconciliation #4). Security posture lifted from `packaging-audit.yml`: `on: pull_request` (not the privileged trigger), `permissions.contents: read`, `concurrency: cancel-in-progress`, `timeout-minutes: 15`, checkout SHA-pinned to v4.3.1 (the same pin packaging-audit uses), setup-node SHA-pinned to the repo-standard v4.4.0. **Gate 1 (fail-fast):** `grep -ri 'geist|fraunces' docs/landing/` → exit 1. **Gate 2:** a Python inline check asserts `accessibility >= 0.95` AND `performance >= 0.90` from `lh.json`, exit 1 below threshold. `lighthouse@12` installed CI-side (no `pyproject.toml`/`uv.lock` entry).

### Task 3 — `KAAN-ACTION-LEGAL.md §V7-LANDING` (commit `91a4cbd`)
New append-only `## §V7-LANDING` cluster mirroring the §V7-LIVE 6-section shape, with four soft Kaan-discharge items: **01** Pages enablement + live-URL Lighthouse, **02** Kaan-felt CDJ-Whisper aesthetic sign-off, **03** real canonical Bravoh-waitlist URL, **04** repo social-preview image (og-card.png). Each has Surface / Why-it-can't-ship-green / Fix-path / Owner-clock / Cross-reference / Sign-off; plus a discharge-tracking table and a consolidated sign-off block. States explicitly that all four are **SOFT under `gsd-autonomous fully` and do NOT gate the v7.0 milestone close** — engineering closes GH-02 on the local Lighthouse pass + the anti-backsliding grep + asset reproducibility.

## Verification results

| Gate | Result |
|------|--------|
| `grep -ri 'geist\|fraunces' docs/landing/` | **ZERO** (clean) |
| Landing parses as HTML | PASS |
| `lighthouse.yml` parses as YAML, declares job | PASS |
| `grep -cE '^## §V7-LANDING'` | **1** (exactly one h2 cluster header) + 4 `###` subsections |
| `pull_request_target` in lighthouse.yml | **0** (fork-PR-safe) |
| checkout SHA pin matches packaging-audit | PASS (`34e1148…`) |
| analytics on page view (`gtag\|googletagmanager\|fbq`) | **ZERO** |
| og:image present | PASS (`../assets/og-card.png`) |
| a11y structure (1 h1, 1 header/main/footer, lang, viewport, alt, aria-hidden, focus rings, reduced-motion) | PASS |
| **CARDINAL:** `git diff src/vibemix/` | **EMPTY** |
| **CARDINAL:** `git diff pyproject.toml uv.lock` | **EMPTY** |
| Test baseline | `4207 passed / 26 skipped / 4 xpassed / 2 failed` — **identical to Wave 1 baseline** |

The 2 failures (`tests/repo/test_readme_feature_matrix_sync.py`) are the **pre-existing P68 AUTO-GEN drift** documented in the executor context — confirmed unrelated (my 3 commits touch neither README.md nor that test). The landing/CI/docs changes added **+0** to the Python grid as expected (static HTML + CI-side workflow + docs).

## Lighthouse disposition

**CI-only.** `lighthouse` is not installed on Kaan's machine (node/npm are present, but a global `npm install -g lighthouse@12` is a system-modifying side effect not requested under autonomous mode). The **real Lighthouse run is the CI gate** (`.github/workflows/lighthouse.yml`, on every push/PR against the local build), and the **live-URL run is routed to §V7-LANDING-01** (Kaan's repo-Settings clock). The landing was built to actually hit ≥95 a11y / ≥90 perf — not aspirationally — via the offline structural audit above (semantic landmarks, single h1, alt text, visible focus rings, reduced-motion, no render-blocking CSS beyond `&display=swap` fonts, reserved media aspect-ratio, zero JS on the critical path beyond a tiny copy handler, no analytics auto-load).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Bug] Self-tripping anti-backsliding grep in the font comment**
- **Found during:** Task 1 verification.
- **Issue:** My own CSS comment said "NO Geist, NO Fraunces, NO Inter" — the blunt anti-backsliding grep (`grep -ri 'geist|fraunces'`) is a substring scan, so the comment naming the forbidden faces *broke the gate* (1 match).
- **Fix:** Rewrote the comment to describe the lock as "only these two families ship" without naming the rejected faces, with a note explaining why. Gate now returns ZERO.
- **File:** `docs/landing/index.html` · **Commit:** `d5d7877`

**2. [Rule 1 — Bug] Self-tripping `pull_request_target` grep in the workflow comment**
- **Found during:** Task 2 verification.
- **Issue:** The header comment said "(NOT pull_request_target)" — the literal string tripped the `grep -c 'pull_request_target'` MUST-be-0 gate.
- **Fix:** Reworded the comment to "the privileged pull-request trigger is deliberately NOT used here" — no forbidden literal. Gate now returns 0.
- **File:** `.github/workflows/lighthouse.yml` · **Commit:** `f93eac4`

**3. [Rule 3 — Blocking] setup-node SHA pin consistency**
- **Found during:** Task 2 verification.
- **Issue:** I first used `setup-node@39370e3…# v4.1.0`; the rest of the repo (dep-audit, mascot-audit, release, sbom) uses the verified `49933ea5…# v4.4.0`.
- **Fix:** Repinned to the repo-standard `49933ea5288caeca8642d1e84afbd3f7d6820020 # v4.4.0` (verified-good in-tree).
- **File:** `.github/workflows/lighthouse.yml` · **Commit:** `f93eac4`

### Discretion calls (UI-SPEC ambiguity resolutions)
- **CSS/JS delivery:** Went fully inline in `index.html` (UI-SPEC discretion #5: best for perf/CLS, matches mock precedent). Did NOT create the `style.css`/`app.js` files the plan frontmatter listed — the action text explicitly allowed "inline... executor's call as long as it stays buildless," and inline is the perf-optimal no-build choice. The plan's verify gate + the success criteria check `index.html` only.
- **Demo poster:** Pointed `poster=` and the `<img>` fallback at the **existing** `docs/assets/demo-placeholder.gif` rather than `demo-poster.png` (which is a Wave 3 / GH-01 deliverable that doesn't exist yet) — keeps the `<video>` non-broken now, same contract as the README hero.
- **og:image + footer URLs:** Used repo-relative `../assets/og-card.png` (Pages-safe regardless of org) and `github.com/bravoh-ai/vibemix` footer links (matching the README badge convention) rather than the current `ozzaii/vibemix` origin.

## Known Stubs
None that block the GH-02 goal. The `<video src="../assets/demo.mp4">` points at a not-yet-present file (KAAN-ACTION §ASSETS-DEMO-CUT / Wave 3 GH-01) — but the poster + `<img>` fallback keep it non-broken, identical to the README hero pattern, and the "demo film coming soon" caption signals it. The waitlist URL is the locked placeholder (real URL → §V7-LANDING-03). Both are intentional, documented, and resolve in later waves / Kaan-clock — not slop.

## Self-Check: PASSED
- `docs/landing/index.html` — FOUND
- `.github/workflows/lighthouse.yml` — FOUND
- `KAAN-ACTION-LEGAL.md` §V7-LANDING — FOUND (1 h2 header)
- Commits `d5d7877`, `f93eac4`, `91a4cbd` — all present in `git log`

## EXECUTION COMPLETE
