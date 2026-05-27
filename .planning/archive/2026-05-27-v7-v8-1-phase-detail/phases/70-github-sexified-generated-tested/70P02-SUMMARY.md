---
phase: 70-github-sexified-generated-tested
plan: 02
wave: 1
subsystem: og-social-card
tags: [github, og-card, social-card, assets, reproducibility, cdj-whisper, gh-03, wave-1]
requirements:
  - GH-03
provides:
  - "docs/assets/sources/og-card.html — fixed 1200×630 headless-render source template in CDJ-Whisper aesthetic (Saira wordmark + JetBrains Mono micro-label, amber #ff8a3d LED + one amber word, void stack + cinematic vignette + feTurbulence film-grain lifted verbatim from mocks/vibemix-direction-final.html)"
  - "docs/assets/og-card.png — generated 1200×630 OG/social card, Pillow-normalized for byte-determinism, palette-quantized to 97 KB"
  - "scripts/regenerate_assets.sh — og-card generator branch (headless Chrome --headless=new --window-size=1200,630 --force-device-scale-factor=1 + _find_chrome cross-platform locator + Pillow deterministic re-encode), the FIRST real assets entry the regenerator owns"
  - "docs/assets/MANIFEST.yaml — og-card assets entry pinned by SHA-256 089a8a91...c3728"
  - "README.md — documented og:image / repo social-preview path (literal docs/assets/og-card.png present for Wave 4 presence test; manual repo-settings action routed to §V7-LANDING)"
affects:
  - docs/assets/sources/og-card.html (NEW)
  - docs/assets/og-card.png (NEW, 97 KB, 1200×630)
  - scripts/regenerate_assets.sh (MODIFIED: og-card case + _find_chrome helper)
  - docs/assets/MANIFEST.yaml (MODIFIED: assets [] → 1 entry)
  - README.md (MODIFIED: og:image documentation comment in hero block)
tech-stack:
  added: []
  patterns:
    - "Headless-Chrome render over npx puppeteer (CONTEXT Claude's-Discretion): Chrome --headless=new --screenshot mirrors the existing docs/assets/screenshots/regen.sh precedent, is already installed on dev/CI, and avoids an npm fetch (smaller supply-chain surface, T-70P02-SC). Node/npx stays CI-side — NOT a Python dep."
    - "Byte-determinism via Pillow re-encode (Rule-1): Chrome's PNG encoder emits drifting bytes across runs even when PIXELS are byte-identical (verified: ImageChops.difference bbox=None, max diff 0, yet file sha differed). The og-card branch re-saves through Pillow (quantize-256 MEDIANCUT no-dither + optimize + compress_level 9, metadata-stripped) so the asset-bitrot git-diff gate passes byte-for-byte. Pillow is a tracked dep — no new dep. Side benefit: 190 KB → 97 KB."
    - "MANIFEST sha-pin workflow: append entry with sha256: PENDING → render via regenerator → read the produced sha → set it. Schema test accepts PENDING|64-hex; the plan's verify requires non-PENDING for a shipped asset."
    - "CDJ-Whisper tokens lifted VERBATIM from mocks/vibemix-direction-final.html (:root void/silk/amber/rave, body vignette gradients, body::before two-layer feTurbulence). 20/80 holds at card scale: amber = the brand LED dot + the single word 'listens'."
key-files:
  created:
    - docs/assets/sources/og-card.html
    - docs/assets/og-card.png
    - .planning/phases/70-github-sexified-generated-tested/70P02-SUMMARY.md
  modified:
    - scripts/regenerate_assets.sh
    - docs/assets/MANIFEST.yaml
    - README.md
  deleted: []
decisions:
  - "Render mechanism = headless Google Chrome, not npx puppeteer. Chrome is installed (verified), deterministic with fixed --window-size + --force-device-scale-factor=1, mirrors the repo's existing screenshots/regen.sh, and adds zero npm-fetch supply-chain surface. T-70P02-SC mitigation: the committed PNG is the trust anchor; the tool only re-derives it."
  - "social-card.png NOT touched — it stays a MANIFEST opt_out (Wave 0 reconciliation option (a)). og-card.png is its source-generated, hash-pinned successor; social-card.png is the retained hand-cut predecessor with zero live refs."
  - "README og:image = documented HTML comment (not a duplicate visible <img>). A raw <meta property=og:image> does not render in GitHub markdown; the live meta tag lives in the Wave 2 Pages <head>. The repo Settings → Social preview image is a manual action → §V7-LANDING. The literal path docs/assets/og-card.png appears 3× in README for Wave 4's presence assertion."
  - "Image budget: untouched. og-card.png is 97 KB against ~567 KB headroom (docs/assets images were ~1.48 MB / 2 MB cap). No cap bump — shrink-first satisfied by the Pillow quantize step."
metrics:
  duration: ~25 min
  completed_date: 2026-05-24
  files_touched: 5
  baseline_before: "4207 passed / 26 skipped / 4 xpassed / 2 failed (Wave 0 close @ 706f7e0)"
  baseline_after: "4207 passed / 26 skipped / 4 xpassed / 2 failed (Wave 1 close)"
  baseline_delta: "+0 tests added by this plan (test_asset_manifest_shape.py + test_docs_assets.py still green with the new asset registered). 2 failures are the PRE-EXISTING Phase 68 README feature-matrix AUTO-GEN drift (documented in .planning/phases/69-oss-fully-integrated/deferred-items.md) — NOT a Phase 70 regression; my README edit touched only the hero-block comment, zero feature-matrix lines."
  full_suite_wall_clock: 222.52s
  og_card_size_bytes: 99584
  og_card_sha256: 089a8a910f9f8c0c326e774f5e983a380d5bf0425a966b7c90597215027c3728
  task_commit_shas:
    - 18418a2 (Task 1: docs/assets/sources/og-card.html)
    - 5410f3a (Task 2: regenerate_assets.sh og-card branch + og-card.png + MANIFEST pin + README)
    - 2ab7848 (Rule-1 fix: --virtual-time-budget font-race determinism)
---

# Phase 70 Plan 02: OG / Social Card (GH-03) Summary

A source-generated, hash-pinned 1200×630 OG/social card in the CDJ-Whisper
aesthetic: `docs/assets/sources/og-card.html` (the render source) → headless
Chrome → `docs/assets/og-card.png`, wired into the Wave 0 regenerator
(`scripts/regenerate_assets.sh` og-card branch), pinned by SHA-256 in
`docs/assets/MANIFEST.yaml`, and referenced from the README. This is the
source-generated, regenerable successor to the hand-cut `social-card.png`
(which Wave 0 already opted out as bespoke).

## og-card.png Generation Path Taken

**Puppeteer-rendered locally — NO halt, no placeholder, no CI-only deferral.**
Node 22 + npx + Google Chrome were all available on this machine, so the real
PNG was rendered locally via headless Chrome (chosen over `npx puppeteer` to
avoid an npm fetch — see Decisions). The committed PNG is the live, real render
(verified visually: silk `vibemix` wordmark, amber LED + JetBrains-Mono
`OPEN SOURCE · MAC + WIN` micro-label, pitch with the single amber word
"listens", over the void+vignette+grain background). Reads cleanly at thumbnail
scale.

## What Shipped

| Artifact | Role |
|----------|------|
| `docs/assets/sources/og-card.html` | Fixed 1200×630 CDJ-Whisper render source (Saira + JetBrains Mono, amber #ff8a3d) |
| `docs/assets/og-card.png` | Generated 1200×630 social card, 97 KB, deterministic |
| `scripts/regenerate_assets.sh` | og-card generator branch (headless Chrome + Pillow re-encode) + `_find_chrome` |
| `docs/assets/MANIFEST.yaml` | og-card `assets` entry pinned by SHA-256 |
| `README.md` | og:image / repo social-preview documentation (literal path present) |

## Image-Budget Disposition

**Fit under headroom — cap UNTOUCHED.** docs/assets images were ~1.48 MB
against the 2 MB cap (~567 KB headroom). The Pillow quantize-256 + optimize step
brought og-card.png to **97 KB** (down from Chrome's raw 190 KB), comfortably
within headroom. `tests/repo/test_docs_assets.py` stays green at the 2 MB
ceiling — no documented cap bump needed (shrink-first satisfied).

## Deviations from Plan

### Rule-1 Auto-fixes

1. **Chrome PNG non-determinism → Pillow re-encode.** Chrome's `--screenshot`
   PNG encoder is NOT byte-stable across runs: two consecutive renders produced
   pixel-identical images (`ImageChops.difference` bbox `None`, max channel diff
   `0`) but DIFFERENT file SHAs — drift in PNG chunk ordering/metadata, which
   would break the asset-bitrot `git diff --exit-code` gate. Fix: the og-card
   branch re-encodes the Chrome screenshot through Pillow with fixed,
   metadata-stripped options (`quantize(256, MEDIANCUT, dither=NONE)` +
   `save(optimize=True, compress_level=9)`). Now byte-deterministic across runs
   (`git diff --exit-code docs/assets/og-card.png` exits 0). Pillow is a tracked
   dep — no new dependency. Bonus: 190 KB → 97 KB.

2. **Font-load race → `--virtual-time-budget=4000` (the REAL determinism fix).**
   The Pillow re-encode (fix 1) made the PNG *encoding* stable, but a deeper
   non-determinism surfaced when the bitrot gate was exercised across SEPARATE
   Chrome invocations: the render PIXELS themselves drifted (39 189 differing
   pixels in the text region, max channel diff 253). Root cause: Chrome races
   the Google-Fonts webfont fetch — without a wait it sometimes screenshots with
   the `system-ui` fallback instead of Saira. Fix: add `--virtual-time-budget=4000`
   so the page's virtual clock advances past font-load before the screenshot.
   Verified pixel-identical across 3 separate invocations, and the resulting sha
   matches the already-committed/pinned `089a8a91...c3728`. This keeps the
   UI-SPEC's "load fonts via Google Fonts `<link>`" instruction intact (no
   self-hosting) while making the render reproducible. The bitrot gate's "differs
   ONLY by intentional source edits" clause + a documented chrome-version
   tolerance still cover cross-version rasteriser drift; the font-race was the
   actual culprit and is now closed. Committed as a follow-up fix to the Task 2
   generator (commit `2ab7848`).

3. **Anti-slop comment reworded (og-card.html).** The plan's acceptance gate
   `grep -ric 'geist\|fraunces' docs/assets/sources/og-card.html` must return 0.
   My initial CSS comment named the rejected fonts literally ("NO Geist, NO
   Fraunces...") to document the anti-backsliding intent — which tripped the
   grep. Reworded to describe them without the literal family names; grep now
   returns 0. (Same Rule-1 class as Wave 0's `pull_request_target` comment hit.)

### Note on the `inter` grep

`grep -ric 'inter\b\|roboto\|arial'` returns 1 — the single match is the CSS
property `pointer-events: none` (the `inter` substring in "pointer"), NOT a
font-family. The plan's executor-context explicitly anticipates this false
match. The actual font-family declarations reference ONLY `'Saira'` +
`'JetBrains Mono'` + generic CSS fallbacks (`system-ui`, `ui-monospace`,
`monospace`, `sans-serif`) — exactly as the mock writes them and as UI-SPEC
permits. No AI-slop font is used as a face.

### Authentication Gates

None.

## Cardinal Invariant Confirmation

- `git diff --stat HEAD -- src/vibemix/` → **EMPTY** (zero reaction-path touch).
- `git diff --stat HEAD -- pyproject.toml uv.lock` → **EMPTY** (Chrome/Node is CI-side, not a Python dep; Pillow is a pre-existing tracked dep).
- `grep -c sources/og-card docs/assets/MANIFEST.yaml` → **1** (≥1, as required).
- `grep -ric 'geist\|fraunces' docs/assets/sources/og-card.html` → **0**.
- `bash scripts/regenerate_assets.sh && git diff --exit-code docs/assets/og-card.png` → exits **0** (deterministic; committed PNG matches regenerated form on this Chrome build).
- Committed PNG sha == MANIFEST pin (`089a8a91...c3728`).

## Baseline

`4207 passed / 26 skipped / 4 xpassed / 2 failed` in 222.52s (default grid,
`PYTHONPATH=src python3 -m pytest -q`) — IDENTICAL to the Wave 0 close. The 2
failures are the pre-existing Phase 68 `test_readme_feature_matrix_sync.py`
AUTO-GEN drift (documented in
`.planning/phases/69-oss-fully-integrated/deferred-items.md`) — confirmed
unrelated to this plan: my README edit added only an HTML comment in the hero
block, zero feature-matrix-table lines.

## Self-Check: PASSED

- `docs/assets/sources/og-card.html` — FOUND
- `docs/assets/og-card.png` — FOUND (1200×630, 97 KB)
- `scripts/regenerate_assets.sh` (og-card branch) — FOUND
- `docs/assets/MANIFEST.yaml` (og-card pinned) — FOUND
- `README.md` (docs/assets/og-card.png ref) — FOUND
- Commit `18418a2` — FOUND
- Commit `5410f3a` — FOUND

## EXECUTION COMPLETE
