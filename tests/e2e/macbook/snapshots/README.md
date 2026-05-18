# Phase 50 — Visual Regression Snapshot Contract

## Workflow

### First baseline capture (engineering scaffold)
```
npx playwright install --with-deps chromium
TAURI_DEV_URL=http://localhost:1420 npx playwright test -c tests/e2e/macbook/playwright.config.ts --update-snapshots
```

This produces PNG baselines at `tests/e2e/macbook/__snapshots__/`. Commit them to the repo.

### Regular run (CI / local validation)
```
TAURI_DEV_URL=http://localhost:1420 npx playwright test -c tests/e2e/macbook/playwright.config.ts
```

Tests assert each captured screenshot matches the stored baseline within `maxDiffPixelRatio: 0.02` per REQ E2E-03.

### Re-baseline trigger (§VIS-04 Kaan-action)
The current baselines are captured against **Phase 47 placeholder GLBs** at `tauri/ui/assets/mascot/animations/`. When §VIS-04 lands real Mixamo retargets, all snapshots MUST be re-captured:

```
# After §VIS-04 real GLBs ship:
rm -rf tests/e2e/macbook/__snapshots__/*
npx playwright test -c tests/e2e/macbook/playwright.config.ts --update-snapshots
git add tests/e2e/macbook/__snapshots__/
git commit -m "chore(visual): re-baseline snapshots vs real Mixamo GLBs (§VIS-04 discharge)"
```

## Platform tagging
Snapshot path template embeds the platform tag in the directory name:

```
__snapshots__/persona_smoke.spec.ts--darwin-arm64/base_idle.png
__snapshots__/persona_smoke.spec.ts--darwin-x64/base_idle.png
__snapshots__/persona_smoke.spec.ts--win32-x64/base_idle.png
```

This isolates AS-Mac, Intel-Mac, and Win baselines — each platform has its own pixel-stable baseline.

## Diff outputs (on test failure)
Failed runs write diff PNGs to:
```
dist/e2e-macbook-runs/playwright-output/<test>/<test>-actual.png
dist/e2e-macbook-runs/playwright-output/<test>/<test>-diff.png
```

The `report.html` Visual dimension section thumbnails these diffs.

## PITFALLS § 8 fallback (tauri-plugin-playwright maturity)

`tauri-plugin-playwright==0.1.0` does not yet stably drive macOS WKWebView. The specs in this directory use `beforeAll` health checks against `TAURI_DEV_URL`; if the dev server is unreachable, the spec marks itself as `test.skip` rather than failing. This satisfies the engineering scaffold for Phase 50; real-baseline capture is a Kaan-side discharge at §E2E-50A-WALK.

CI fallback: WebView2-only on Win runners + manual Mac walk (50a).

## Pin

- `@playwright/test==1.50.x` per `.planning/research/STACK.md` § Bucket 4
- `pixelmatch==7.1.0` per same
- `maxDiffPixelRatio: 0.02` — REQ E2E-03 verbatim
- `tauri-plugin-playwright==0.1.0` — accepted-maturity scaffold per PITFALLS § 8
