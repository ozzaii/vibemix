# Learn Quality Gate Snapshot - 2026-06-04

HEAD: `054a6638`

## Commands

```bash
PYTHONPATH=src PATH=/opt/homebrew/opt/node@22/bin:$PATH .venv/bin/python scripts/run_learn_frontend_quality.py --out /tmp/vibemix-live-learn-proof/learn-frontend-quality-current-054a6638.json
PYTHONPATH=src PATH=/opt/homebrew/opt/node@22/bin:$PATH .venv/bin/python scripts/run_learn_desktop_quality.py --out /tmp/vibemix-live-learn-proof/learn-desktop-quality-current-054a6638.json
PYTHONPATH=src .venv/bin/python scripts/verify_learn_package.py --no-frontend-check --frontend-quality /tmp/vibemix-live-learn-proof/learn-frontend-quality-current-054a6638.json --desktop-quality /tmp/vibemix-live-learn-proof/learn-desktop-quality-current-054a6638.json --live-proof .planning/eval-runs/learn-screen-path-current-20260604-16a547dd/proof.json --live-proof .planning/eval-runs/learn-course1-head-proof-current-20260604-2a0d93ee/summary.json --live-proof .planning/eval-runs/learn-l210-cue-playhead-proof-20260604-5a7bdb05/summary.json --live-proof .planning/eval-runs/learn-l109-master-vol-audio-proof-20260604-9a52eb03/summary.json --live-proof .planning/eval-runs/learn-l211-harmonic-practice-proof-20260604-47982741/summary.json --out /tmp/vibemix-learn-verify-quality-current-054a6638.json
```

## Result

- Frontend quality: `passed=false`
- Desktop quality: `passed=true`
- Verifier: `technical_passed=false`
- Verifier now marks `desktop_shell_quality` as `proven`.

## Frontend Failures

- `learn_browser_booth_playwright`: failed on `browser-axe.pw.ts`; axe reports `aria-prohibited-attr` on `.learn-waveforms`.
- `learn_e2e`: same axe failure plus `browser-python-beginner-path.pw.ts` timeout waiting for the wrong on-screen move to send the expected frame.

These failures are in `tauri/ui` and are left for the Frontend lane. No frontend source was edited in this Learn proof slice.

## Remaining Verifier Blockers

- Packaged EQ exemplar human ear-pass is pending.
- Full Learn frontend quality gate is failing.
- Launched Tauri Learn smoke is missing.
- Physical controller lesson proof is not strictly proven.
- Course 3 routed-audio count-in proof is not strictly proven.
