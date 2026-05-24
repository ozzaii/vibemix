---
phase: 70-github-sexified-generated-tested
plan: 04
wave: 3
subsystem: demo-poster-film-route
tags: [github, demo, poster, assets, reproducibility, cdj-whisper, gh-01, kaan-action, wave-3]
requirements:
  - GH-01
provides:
  - "docs/assets/sources/demo-poster.html — fixed 1280×720 headless-render source in CDJ-Whisper aesthetic (recessed-glass .display-window LCD + amber-ringed play glyph + brand LED + silk-40 JetBrains-Mono 'demo film coming soon' empty-state caption; palette/fonts lifted verbatim from mocks/vibemix-direction-final.html)"
  - "docs/assets/demo-poster.png — generated 1280×720 demo-video poster (the still the README hero <video poster=> + the landing demo window show until the real demo.mp4 lands), Pillow-normalized for byte-determinism, 72 KB"
  - "scripts/regenerate_assets.sh — demo-poster generator branch (headless Chrome --window-size=1280,720 --virtual-time-budget=4000 + Pillow deterministic re-encode), sibling of the Wave 1 og-card step"
  - "docs/assets/MANIFEST.yaml — demo-poster assets entry pinned by SHA-256 bc448645...66a0"
  - "README.md — hero <video poster=> repointed demo-placeholder.gif → demo-poster.png (sha256=PLACEHOLDER sentinel preserved; check_readme_hero_hash.py stays green)"
  - "KAAN-ACTION-LEGAL.md — §ASSETS-DEMO-CUT cluster routing the real 30-sec demo.mp4 capture (Francesco per §VIS-09) + ≤8MB cap + cross-browser inline-play + PLACEHOLDER→real-SHA flip"
affects:
  - docs/assets/sources/demo-poster.html (NEW)
  - docs/assets/demo-poster.png (NEW, 72 KB, 1280×720)
  - scripts/regenerate_assets.sh (MODIFIED: demo-poster case)
  - docs/assets/MANIFEST.yaml (MODIFIED: 1 → 2 assets entries)
  - README.md (MODIFIED: hero <video poster=> + <img> fallback repointed)
  - KAAN-ACTION-LEGAL.md (MODIFIED: append-only — §ASSETS-DEMO-CUT cluster)
  - tests/repo/test_readme_shape.py (MODIFIED: Rule-1 — required-asset ref → demo-poster.png)
tech-stack:
  added: []
  patterns:
    - "Reuse of the Wave 1 og-card headless-Chrome → Pillow byte-deterministic render recipe (70P02): --headless=new + fixed --window-size + --force-device-scale-factor=1 + --virtual-time-budget=4000 (font-race fix) → Pillow quantize-256 MEDIANCUT no-dither + optimize + compress_level 9. Verified byte-identical across runs (git diff --exit-code clean). Pillow is a tracked dep — no new dep; Node/Chrome stays CI-side."
    - "demo-poster sized 1280×720 (16:9) to match the README hero <video width=720> aspect + the landing .display-window demo embed (UI-SPEC §2). The og-card precedent was 1200×630 (OG aspect) — same generator mechanism, different fixed dims."
    - "MANIFEST sha-pin workflow (from 70P02): append entry sha256: PENDING → render via regenerator → read produced sha → pin. Schema test accepts PENDING|64-hex; the plan verify requires non-PENDING for the shipped asset."
    - "§V7-LIVE / §V7-LANDING 6-section soft-discharge cluster shape reused for §ASSETS-DEMO-CUT: surface / why-not-CI / fix-path / owner-clock / cross-reference / sign-off block. Append-only to KAAN-ACTION-LEGAL.md."
key-files:
  created:
    - docs/assets/sources/demo-poster.html
    - docs/assets/demo-poster.png
    - .planning/phases/70-github-sexified-generated-tested/70P04-SUMMARY.md
  modified:
    - scripts/regenerate_assets.sh
    - docs/assets/MANIFEST.yaml
    - README.md
    - KAAN-ACTION-LEGAL.md
    - tests/repo/test_readme_shape.py
  deleted: []
decisions:
  - "demo-poster.png is SOURCE-GENERATED (Chrome-rendered from docs/assets/sources/demo-poster.html), NOT hand-stamped — so it gets a MANIFEST assets entry + the regenerator branch + the SHA pin (asset-bitrot consistency, T-70P04-02). git diff --exit-code docs/assets/demo-poster.png exits 0 (deterministic). It is the og-card precedent applied to GH-01."
  - "demo-poster sized 1280×720 (16:9), not 1200×630 (the og-card OG aspect): the README hero <video width=720> + the landing .display-window are 16:9; the OG-unfurl card (og-card.png) is a separate Wave-1 asset with its own 1200×630 social-aspect canvas."
  - "README hero <video poster=> repointed demo-placeholder.gif → demo-poster.png (CONTEXT reconciliation #2 allows it). The <video src> still points at the not-yet-present docs/assets/demo.mp4; the new poster + the <img> fallback keep the hero non-broken. The sha256=PLACEHOLDER sentinel is BYTE-UNTOUCHED — check_readme_hero_hash.py stays on the pending-asset exit-0 path."
  - "§ASSETS-DEMO-CUT did NOT exist despite CONTEXT.md calling it 'existing' (grep confirmed: the only demo-capture surface was §VIS-09 at line 1344). CREATED the cluster, cross-referencing §VIS-09. The planner anticipated this exactly."
  - "demo-placeholder.gif stays committed (MANIFEST opt_out, unchanged) but is no longer README-referenced — superseded as the hero poster by demo-poster.png."
metrics:
  duration: ~30 min
  completed_date: 2026-05-24
  files_touched: 7
  baseline_before: "4207 passed / 26 skipped / 4 xpassed / 2 failed (Wave 2 close @ b4e57c9)"
  baseline_after: "4207 passed / 26 skipped / 4 xpassed / 2 failed (Wave 3 close)"
  baseline_delta: "+0 net test delta. The 2 failures are the PRE-EXISTING Phase 68 test_readme_feature_matrix_sync.py AUTO-GEN drift (documented in .planning/phases/69-oss-fully-integrated/deferred-items.md) — NOT a Phase 70 regression. A transient 3rd failure (test_readme_shape required-asset[demo-placeholder.gif]) introduced by the hero repoint was caught + fixed as a Rule-1 in-scope fix (commit 58bf854); baseline returned to exactly 2 failures."
  full_suite_wall_clock: 229.35s
  demo_poster_size_bytes: 73728
  demo_poster_sha256: bc448645dee165c9ecc86bbacd966af6bc1d0fbc90643b27411698b1aec766a0
  image_budget: "1688542 bytes / 2097152 cap (~408 KB headroom). Cap UNTOUCHED — demo-poster fit under headroom (Pillow quantize-256)."
  task_commit_shas:
    - af9373d (Task 1: demo-poster.html + regenerate_assets.sh branch + demo-poster.png + MANIFEST pin + README repoint)
    - c673ef8 (Task 2: KAAN-ACTION-LEGAL.md §ASSETS-DEMO-CUT cluster)
    - 58bf854 (Rule-1: test_readme_shape required-asset ref → demo-poster.png)
---

# Phase 70 Plan 04: Demo Film Poster + §ASSETS-DEMO-CUT (GH-01) Summary

The engineering side of GH-01: a source-generated CDJ-Whisper demo-video poster
(`docs/assets/demo-poster.png`, rendered from `docs/assets/sources/demo-poster.html`
via the Wave-0 regenerator, SHA-256-pinned in `MANIFEST.yaml`), the README hero
`<video poster=>` repointed to it while the `sha256=PLACEHOLDER` sentinel keeps
`scripts/check_readme_hero_hash.py` green, and a new `§ASSETS-DEMO-CUT` KAAN-ACTION
cluster routing the real 30-sec film to Francesco's capture clock (§VIS-09). Under
`gsd-autonomous fully` the real `demo.mp4` does NOT block — engineering closes on
the poster + the placeholder-green gate.

## demo-poster.png Generation Path Taken

**Chrome-rendered locally + MANIFEST-pinned — NO halt, no placeholder-PNG, no
CI-only deferral.** Google Chrome was available (Wave 1 confirmed it), so the real
PNG was rendered via headless Chrome reusing the documented 70P02 recipe
(`--headless=new --window-size=1280,720 --force-device-scale-factor=1
--virtual-time-budget=4000` → Pillow `quantize(256, MEDIANCUT, dither=NONE)` +
`save(optimize=True, compress_level=9)`). The committed PNG is the live render:
the recessed-glass `.display-window` LCD, the amber-ringed play glyph, the silk
`vibemix` wordmark, the brand LED + `LIVE SESSION` mono micro-label, and the
silk-40 mono `demo film coming soon` empty-state caption, over the
void+vignette+film-grain CDJ-Whisper background.

It is **source-generated, not hand-stamped** → it gets the full asset-bitrot
treatment (MANIFEST `assets` entry + `demo-poster` regenerator branch + SHA pin).
`bash scripts/regenerate_assets.sh && git diff --exit-code docs/assets/demo-poster.png`
exits 0 across runs (deterministic; verified twice).

## What Shipped

| Artifact | Role |
|----------|------|
| `docs/assets/sources/demo-poster.html` | Fixed 1280×720 CDJ-Whisper render source (Saira + JetBrains Mono, amber #ff8a3d, recessed-glass display window) |
| `docs/assets/demo-poster.png` | Generated 1280×720 demo-video poster, 72 KB, deterministic |
| `scripts/regenerate_assets.sh` | demo-poster generator branch (headless Chrome + Pillow re-encode) |
| `docs/assets/MANIFEST.yaml` | demo-poster `assets` entry pinned by SHA-256 |
| `README.md` | hero `<video poster=>` + `<img>` fallback repointed to demo-poster.png; sentinel intact |
| `KAAN-ACTION-LEGAL.md` | §ASSETS-DEMO-CUT cluster (real film + ≤8MB + cross-browser inline-play, → §VIS-09) |
| `tests/repo/test_readme_shape.py` | Rule-1: required-asset ref updated to the new poster |

## Image-Budget Disposition

**Fit under headroom — cap UNTOUCHED.** docs/assets images total
**1,688,542 bytes against the 2 MB (2,097,152) cap (~408 KB headroom)**. The
Pillow quantize-256 + optimize step brought demo-poster.png to **72 KB**,
comfortably within headroom. `tests/repo/test_docs_assets.py` stays green at the
2 MB ceiling — no documented cap bump needed (shrink-first satisfied).

## check_readme_hero_hash.py — STILL GREEN

`python3 scripts/check_readme_hero_hash.py` exits **0**:
`OK: hero asset pending Kaan-action (sha256=PLACEHOLDER)`. The repoint changed
only the `poster=` + `<img src=>` attributes; the
`<!-- vibemix:hero-start sha256=PLACEHOLDER path=docs/assets/demo.mp4 -->`
sentinel is BYTE-UNCHANGED. `grep -c 'sha256=PLACEHOLDER' README.md` = 2 (≥1).
The real demo.mp4 has not landed → the gate stays on the pending-asset exit-0
path (anti-slop demo-honesty invariant, T-70P04-01).

## §ASSETS-DEMO-CUT Cluster — CREATED

CONTEXT.md called it "existing", but grep confirmed NO `§ASSETS-DEMO-CUT` header
existed — the only demo-capture surface was `§VIS-09` (Francesco capture-day
runbook, line 1344). The planner anticipated this exactly. CREATED the cluster
in the §V7-LIVE / §V7-LANDING 6-section soft-discharge shape:

1. **Surface** — README `<video src=demo.mp4>` real asset · the PLACEHOLDER→real-SHA flip · the ≤8 MB cap (8388608) · cross-browser inline-play (Chrome + Safari + Firefox).
2. **Why-not-CI** — the 30-sec film needs Francesco's capture day (§VIS-09: AV spec, mascot headbob feel, palette sign-off); no engineering step can produce it.
3. **Fix-path** — Francesco shoots per §VIS-09 → editor cuts to ≤8 MB → Kaan drops demo.mp4 + flips sha256=PLACEHOLDER → real SHA-256 → confirms inline-play on the 3 browsers.
4. **Owner-clock** — Francesco (capture) + Kaan (drop + browser check). SOFT under gsd-autonomous fully — does NOT gate the v7.0 close.
5. **Cross-reference** — §VIS-09 · check_readme_hero_hash.py · README hero block · demo-poster.png · Wave 4 test_github_presence.py size check · §V7-LIVE/§V7-LANDING.
6. **Sign-off block** — ☐ pending · ☐ done with date/SHA/≤8MB-held/3-browser-inline-play fields.

Append-only: **100 insertions, 0 deletions** — pre-existing content byte-unchanged.

## Deviations from Plan

### Rule-1 Auto-fixes

1. **README hero repoint broke `test_readme_shape::test_readme_references_asset[demo-placeholder.gif]`.**
   The plan's Task-1 repoint (demo-placeholder.gif → demo-poster.png) removed the
   only README references to the gif, failing the parametrized required-asset
   presence test (which asserted the README references its committed assets so
   they don't 404). The gif is superseded as the hero asset; demo-poster.png is
   the new committed asset the README depends on. Fix: updated
   `REQUIRED_ASSET_REFS` to track `docs/assets/demo-poster.png` (the gif stays
   committed in MANIFEST opt_out, just no longer README-referenced). This was an
   in-scope failure directly caused by the plan's own repoint, fixed before
   final baseline. Commit `58bf854`. A transient 3rd failure during full-suite
   verification; baseline returned to exactly the 2 pre-existing failures.

### Authentication Gates

None.

## Cardinal Invariant Confirmation

- `git diff --stat HEAD -- src/vibemix/` → **EMPTY** (zero reaction-path touch).
- `git diff --stat HEAD -- pyproject.toml uv.lock` → **EMPTY** (Chrome/Node is CI-side; Pillow + PyYAML are pre-existing tracked deps).
- `grep -c '## §ASSETS-DEMO-CUT' KAAN-ACTION-LEGAL.md` → **1**.
- `grep -ric 'geist\|fraunces' docs/assets/sources/demo-poster.html` → **0**.
- `bash scripts/regenerate_assets.sh && git diff --exit-code docs/assets/demo-poster.png` → exits **0** (deterministic).
- Committed PNG sha == MANIFEST pin (`bc448645...66a0`).
- `python3 scripts/check_readme_hero_hash.py` → exit **0** (PLACEHOLDER preserved).

## Baseline

`4207 passed / 26 skipped / 4 xpassed / 2 failed` in 229.35s (default grid,
`PYTHONPATH=src python3 -m pytest -q`) — IDENTICAL to the Wave 2 baseline
(`b4e57c9`). The 2 failures are the pre-existing Phase 68
`test_readme_feature_matrix_sync.py` AUTO-GEN drift (documented in
`.planning/phases/69-oss-fully-integrated/deferred-items.md`) — confirmed
unrelated to this plan.

## Self-Check: PASSED

- `docs/assets/sources/demo-poster.html` — FOUND
- `docs/assets/demo-poster.png` — FOUND (1280×720, 72 KB)
- `scripts/regenerate_assets.sh` (demo-poster branch) — FOUND
- `docs/assets/MANIFEST.yaml` (demo-poster pinned) — FOUND
- `README.md` (demo-poster.png ref ×3) — FOUND
- `KAAN-ACTION-LEGAL.md` (§ASSETS-DEMO-CUT) — FOUND
- Commit `af9373d` — FOUND
- Commit `c673ef8` — FOUND
- Commit `58bf854` — FOUND

## EXECUTION COMPLETE
