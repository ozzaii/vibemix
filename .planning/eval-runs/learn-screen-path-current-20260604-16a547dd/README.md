# Learn Screen Path Proof - 2026-06-04

HEAD: `16a547dd061b519780b6ab903975d59dc34fefb0`
Sidecar: `VIBEMIX_DEV_SIDECAR=1`
Progress file: `/tmp/vibemix-live-learn-proof/learn-screen-progress-16a547dd.json`

## Commands

```bash
PYTHONPATH=src VIBEMIX_DEV_SIDECAR=1 .venv/bin/python scripts/run_learn_live_proof.py --start-app --screen-lesson-id L1.01 --screen-seconds 6 --start-timeout 30 --progress-path /tmp/vibemix-live-learn-proof/learn-screen-progress-16a547dd.json --out .planning/eval-runs/learn-screen-path-current-20260604-16a547dd/proof.json
PYTHONPATH=src .venv/bin/python scripts/validate_learn_live_proof.py .planning/eval-runs/learn-screen-path-current-20260604-16a547dd/proof.json --require screen
PYTHONPATH=src .venv/bin/python scripts/verify_learn_package.py --no-frontend-check --live-proof .planning/eval-runs/learn-screen-path-current-20260604-16a547dd/proof.json --live-proof .planning/eval-runs/learn-course1-head-proof-current-20260604-2a0d93ee/summary.json --live-proof .planning/eval-runs/learn-l210-cue-playhead-proof-20260604-5a7bdb05/summary.json --live-proof .planning/eval-runs/learn-l109-master-vol-audio-proof-20260604-9a52eb03/summary.json --live-proof .planning/eval-runs/learn-l211-harmonic-practice-proof-20260604-47982741/summary.json --out /tmp/vibemix-learn-verify-with-screen.json
```

## Result

- `proof.json` schema: `1`
- Overall proof passed: `true`
- Screen lesson: `L1.01`
- Screen ACKs sent: `4`
- Screen advances observed: `4`
- Lesson completion observed: `true`
- Progress file shows `L1.01` completed: `true`
- Strict validator: `valid=true`, no errors

`verify_learn_package.py` now marks `on_screen_deck_path` as `proven`.

## Still Not Proven

This is by-bus proof only. It does not claim human by-ear confirmation, physical controller proof, Course 3 routed-audio count-in proof, Tauri/frontend quality, desktop smoke, or packaged EQ exemplar ear-pass.
