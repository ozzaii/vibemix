# Learn Course 3 Proof Attempt

HEAD at run start: `ae53f233`

This run attempted the strict Course 3 routed-audio count-in proof after the
exemplar and physical-controller Learn gates were closed.

## Commands

```bash
PYTHONPATH=src .venv/bin/python scripts/run_learn_live_proof.py \
  --start-app \
  --no-screen \
  --course3 \
  --seed-course3-unlocked \
  --auto-master-input \
  --nudge-rekordbox-playback \
  --require-count-in \
  --say-course3-prompts \
  --wait-loopback-signal-seconds 15 \
  --wait-capture-signal-seconds 15 \
  --wait-course3-seconds 45 \
  --course3-context-seconds 5 \
  --loopback-signal-seconds 2 \
  --loopback-self-test-seconds 1 \
  --capture-matrix-seconds 2 \
  --out .planning/eval-runs/learn-course3-proof-attempt-current-20260604-ae53f233/course3-proof.json

PYTHONPATH=src .venv/bin/python scripts/validate_learn_live_proof.py \
  --require course3 \
  .planning/eval-runs/learn-course3-proof-attempt-current-20260604-ae53f233/course3-proof.json

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
  --live-proof .planning/eval-runs/learn-course3-proof-attempt-current-20260604-ae53f233/course3-proof.json \
  --out .planning/eval-runs/learn-course3-proof-attempt-current-20260604-ae53f233/package-verification-with-course3-attempt.json
```

## Result

- `course3-proof.json`: failed.
- `capture_signal_wait`: passed.
- `loopback_signal_wait`: passed.
- `rekordbox_playback_nudge`: passed.
- `course3_probe`: skipped because Course 3 readiness failed.
- Validation errors cite no audible live master, no citable deck track, the
  current macOS output route being `MacBook Pro Speakers (eqMac)`, and Now
  Playing coming from browser/WebKit instead of Rekordbox.
- Auto-master recommendation found live signal on `BlackHole 2ch`
  (`rms=0.02519`, `peak=0.171377`) and `BlackHole 16ch`
  (`rms=0.024248`, `peak=0.203371`), but the deck identity/master-output proof
  was still not grounded enough for Course 3.
- `package-verification-with-course3-attempt.json`: Course 3 remains the only
  non-frontend Learn blocker.

## Next Action

Stop unrelated browser/system media. Make Rekordbox the active playing source
with a real imported library track, route master output to a BlackHole capture
path, and rerun the Course 3 proof with `--require-count-in`.
