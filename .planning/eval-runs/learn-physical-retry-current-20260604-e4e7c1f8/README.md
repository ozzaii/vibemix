# Learn Physical Proof Retry

HEAD at run start: `e4e7c1f8`

This run closes the strict physical-controller Learn proof for `L1.07`.

## Commands

```bash
PYTHONPATH=src .venv/bin/python scripts/run_learn_live_proof.py \
  --start-app \
  --no-screen \
  --physical \
  --wait-physical-seconds 30 \
  --physical-seconds 50 \
  --say-physical-prompts \
  --auto-master-input \
  --out .planning/eval-runs/learn-physical-retry-current-20260604-e4e7c1f8/physical-proof.json

PYTHONPATH=src .venv/bin/python scripts/validate_learn_live_proof.py \
  --require physical \
  .planning/eval-runs/learn-physical-retry-current-20260604-e4e7c1f8/physical-proof.json

PYTHONPATH=src .venv/bin/python scripts/verify_learn_package.py \
  --no-frontend-check \
  --exemplar-approval .planning/eval-runs/learn-exemplar-playback-current-20260604-45e96150/ear-pass-approval.json \
  --frontend-quality .planning/eval-runs/learn-quality-current-20260604-054a6638/frontend-quality.json \
  --desktop-quality .planning/eval-runs/learn-quality-current-20260604-054a6638/desktop-quality.json \
  --tauri-smoke .planning/eval-runs/learn-tauri-smoke-current-20260604-054a6638/tauri-smoke-failed.json \
  --live-proof .planning/eval-runs/learn-screen-path-current-20260604-16a547dd/proof.json \
  --live-proof .planning/eval-runs/learn-course1-head-proof-current-20260604-2a0d93ee/summary.json \
  --live-proof .planning/eval-runs/learn-l210-cue-playhead-proof-20260604-5a7bdb05/summary.json \
  --live-proof .planning/eval-runs/learn-l109-master-vol-audio-proof-20260604-9a52eb03/summary.json \
  --live-proof .planning/eval-runs/learn-l211-harmonic-practice-proof-20260604-47982741/summary.json \
  --live-proof .planning/eval-runs/learn-physical-retry-current-20260604-e4e7c1f8/physical-proof.json \
  --out .planning/eval-runs/learn-physical-retry-current-20260604-e4e7c1f8/package-verification-with-physical.json
```

## Result

- `physical-proof.json`: passed.
- `validate_learn_live_proof.py --require physical`: `valid=true`, no errors.
- `L1.07` loaded, `jog:A` position was observed, the proof sent the ACK, and
  `ipc.learn.advance` was observed.
- `app_stop` passed; no sidecar was left running.
- `package-verification-with-physical.json`: the physical controller blocker is
  no longer present.

## Remaining Package Blockers

- Full Learn frontend quality gate is missing or failing.
- Launched Tauri Learn smoke is missing or failing.
- Course 3 routed-audio count-in proof is not strictly proven.
