# Learn Launched Tauri Smoke - Failed - 2026-06-04

HEAD: `054a6638`

## Command

```bash
PATH=/opt/homebrew/opt/node@22/bin:$PATH VIBEMIX_LEARN_E2E_TIMEOUT_MS=180000 node scripts/e2e/learn_launched_tauri_smoke.mjs --out /tmp/vibemix-live-learn-proof/learn-tauri-smoke-current-054a6638.json
```

## Result

The launched Tauri smoke reached the Learn webview and completed the L1.01 flow, but failed its quality phase.

- `passed=false`
- `completed_lesson_id=L1.01`
- `l101_completed=true`
- `quality_ok=false`
- Failure: axe `aria-prohibited-attr` on `.learn-waveforms`

This is the same frontend-owned accessibility failure seen in `.planning/eval-runs/learn-quality-current-20260604-054a6638/frontend-quality.json`.

No `tauri/ui` source was edited in this Learn proof slice.
