# Learn Physical + Course 3 Readiness

HEAD at run start: `6f0cd654`

This run probed the remaining non-frontend Learn proof gates after the packaged
EQ exemplar ear-pass was approved.

## Commands

```bash
PYTHONPATH=src .venv/bin/python scripts/learn_live_readiness.py \
  --require physical \
  --out .planning/eval-runs/learn-physical-course3-readiness-current-20260604-6f0cd654/physical-readiness.json

PYTHONPATH=src .venv/bin/python scripts/learn_live_readiness.py \
  --require course3 \
  --loopback-signal-seconds 2 \
  --capture-matrix-seconds 2 \
  --out .planning/eval-runs/learn-physical-course3-readiness-current-20260604-6f0cd654/course3-readiness.json

PYTHONPATH=src .venv/bin/python scripts/run_learn_live_proof.py \
  --start-app \
  --no-screen \
  --physical \
  --wait-physical-seconds 30 \
  --physical-seconds 45 \
  --say-physical-prompts \
  --auto-master-input \
  --out .planning/eval-runs/learn-physical-course3-readiness-current-20260604-6f0cd654/physical-proof.json
```

## Physical Result

- The initial readiness preflight was red only because the sidecar was not
  listening.
- The started-app proof reached `L1.07`; the bus reported `midi_position` live.
- The proof spoke the left-jog prompt.
- The proof failed because it saw no `jog:A` position, sent no ACK, and saw no
  lesson advance.
- The artifact's physical doctor says the hardware path is ready and the next
  operator step is: nudge the left jog wheel during the active proof window.

## Course 3 Result

Course 3 is still route-blocked:

- Sidecar was not listening during the standalone readiness preflight.
- Direct loopback capture was silent.
- Every sampled DJ/loopback capture input stayed below the signal floor.
- macOS Now Playing was `Azealia Banks - Idle Delilah` from
  `com.apple.WebKit.GPU`, not a Rekordbox deck title.
- Rekordbox settings currently name `DDJ-FLX4`; the route doctor recommends
  switching Rekordbox audio to `BlackHole 16ch @ 48000Hz`, playing a real
  library track, and raising channel/master faders before rerunning the Course 3
  count-in proof.

No sidecar was left running after the proof command exited.
