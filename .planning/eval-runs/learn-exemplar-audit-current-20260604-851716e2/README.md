# Learn Exemplar Audit — Current HEAD

HEAD: `851716e2`

This run refreshes the packaged Learn EQ exemplar gate against current source.
It does not claim a human ear-pass.

## Commands

```bash
PYTHONPATH=src .venv/bin/python scripts/audition_learn_exemplars.py \
  --list-devices \
  --out .planning/eval-runs/learn-exemplar-audit-current-20260604-851716e2/audit.json

PYTHONPATH=src .venv/bin/python scripts/verify_learn_package.py \
  --no-frontend-check \
  --frontend-quality .planning/eval-runs/learn-quality-current-20260604-054a6638/frontend-quality.json \
  --desktop-quality .planning/eval-runs/learn-quality-current-20260604-054a6638/desktop-quality.json \
  --tauri-smoke .planning/eval-runs/learn-tauri-smoke-current-20260604-054a6638/tauri-smoke-failed.json \
  --live-proof .planning/eval-runs/learn-screen-path-current-20260604-16a547dd/proof.json \
  --live-proof .planning/eval-runs/learn-course1-head-proof-current-20260604-2a0d93ee/summary.json \
  --live-proof .planning/eval-runs/learn-l210-cue-playhead-proof-20260604-5a7bdb05/summary.json \
  --live-proof .planning/eval-runs/learn-l109-master-vol-audio-proof-20260604-9a52eb03/summary.json \
  --live-proof .planning/eval-runs/learn-l211-harmonic-practice-proof-20260604-47982741/summary.json \
  --out /tmp/vibemix-learn-verify-current-851716e2.json

PYTHONPATH=src .venv/bin/python -m pytest -q tests/learn tests/audio
```

## Result

- `audit.json`: packaged exemplar technical audit passed.
- Exemplar bank fingerprint: `34e7aafe568b2e8badecb75fd28e0a8bd710f4fd1b1f2d84e7ff4a78584096e9`.
- Four expected bands are present: `sub`, `low`, `mid`, `high`.
- All four WAVs are non-silent, stereo, clip-free, and hash-matched.
- Recommended human-audition output is device `5`, `MacBook Pro Speakers (eqMac)`.
- `package-verification.json`: still red, honestly.
- `pytest`: `1088 passed, 1 skipped`; skipped test is the opt-in live FLX4 jog proof.

## Remaining Release Blockers

- Packaged EQ exemplar human ear-pass is pending.
- Full Learn frontend quality gate is failing.
- Launched Tauri Learn smoke is failing.
- Physical controller lesson proof is not strictly proven.
- Course 3 routed-audio count-in proof is not strictly proven.

The next non-frontend Learn action for this gate is a real human audition:

```bash
PYTHONPATH=src .venv/bin/python scripts/audition_learn_exemplars.py \
  --play \
  --device-index 5 \
  --say-prompts \
  --out /tmp/vibemix-live-learn-proof/learn-exemplar-audition-current.json
```

Only after Kaan hears the four loops should the approval artifact be written.
