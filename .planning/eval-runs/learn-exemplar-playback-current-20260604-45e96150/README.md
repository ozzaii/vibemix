# Learn Exemplar Playback + Ear-Pass

HEAD: `45e96150`

This run closes the packaged EQ exemplar human ear-pass gate for the current
four-loop bank. The WAV hashes are bound into the approval artifact, so changing
the bank invalidates this proof.

## Commands

```bash
PYTHONPATH=src .venv/bin/python scripts/audition_learn_exemplars.py \
  --play \
  --device-index 5 \
  --say-prompts \
  --out .planning/eval-runs/learn-exemplar-playback-current-20260604-45e96150/audition.json

PYTHONPATH=src .venv/bin/python scripts/audition_learn_exemplars.py \
  --approve-ear-pass \
  --approved-by 'Kaan Özkan' \
  --audition .planning/eval-runs/learn-exemplar-playback-current-20260604-45e96150/audition.json \
  --approval-out .planning/eval-runs/learn-exemplar-playback-current-20260604-45e96150/ear-pass-approval.json \
  --out .planning/eval-runs/learn-exemplar-playback-current-20260604-45e96150/approved-summary.json

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
  --out .planning/eval-runs/learn-exemplar-playback-current-20260604-45e96150/package-verification-with-ear-pass.json

PYTHONPATH=src .venv/bin/python -m pytest -q \
  tests/learn/test_exemplar_audition.py \
  tests/learn/test_verify_learn_package.py
```

## Result

- `audition.json`: played all four packaged EQ exemplar loops through output
  device `5` with spoken band prompts.
- `ear-pass-approval.json`: explicit approval for bank fingerprint
  `34e7aafe568b2e8badecb75fd28e0a8bd710f4fd1b1f2d84e7ff4a78584096e9`.
- `approved-summary.json`: exemplar bank `release_ready=true`.
- `package-verification-with-ear-pass.json`: package blocker list no longer
  includes packaged EQ exemplar human ear-pass.
- Focused tests: `46 passed`.

## Remaining Package Blockers

- Full Learn frontend quality gate is missing or failing.
- Launched Tauri Learn smoke is missing or failing.
- Physical controller lesson proof is not strictly proven.
- Course 3 routed-audio count-in proof is not strictly proven.
