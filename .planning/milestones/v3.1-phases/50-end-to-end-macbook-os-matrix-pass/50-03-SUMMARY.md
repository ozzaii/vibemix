# Plan 50-03 SUMMARY — Visual regression baselines

**Status:** complete · **REQs:** E2E-03 · **Specs:** 3 spec files + config + README

Playwright + pixelmatch scaffold against Tauri+Three.js production surfaces. `maxDiffPixelRatio: 0.02` per REQ E2E-03 verbatim. Viewport 1024×768, DPR 2, dark scheme, `reducedMotion: 'reduce'` for pixel-stable baselines.

Three spec stubs target persona-smoke (7 emotion states from Phase 47 EVENT_LAYER_PRIORITY_MAP) + library page (empty + populated Tier-1) + live session (Tier-1). All include PITFALLS § 8 fallback: skip on Tauri-dev-server unreachable rather than failing.

`mascot.html` NEVER referenced (POC immutability + Phase 47 grep gate). Baselines target Phase 47 placeholder GLBs; re-baseline trigger documented at §VIS-04 discharge. `package.json` gains @playwright/test, pixelmatch, playwright devDeps + `test:e2e:visual` script.
