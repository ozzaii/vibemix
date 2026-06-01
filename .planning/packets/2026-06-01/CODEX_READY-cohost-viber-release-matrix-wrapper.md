# CODEX_READY: Cohost/Viber Release Matrix Wrapper

Date: 2026-06-01
Author: Codex
Status: LAND packet, release-gate composition slice
Package: Package 1E - Cohost/Viber Release Matrix Wrapper

## Decision

LAND this slice as `test(release): compose cohost viber release gates`.

This is the one-command coordinator for the current cohost/Viber acceptance
checks. It composes the latest-session autopilot, refreshed failure-corpus
benchmark, runtime canaries, and optional/required FLX4 live-context proof.

## Files

- `scripts/release/check_cohost_viber_matrix.sh`
- `tests/eval/test_check_cohost_viber_matrix_sh.py`
- `.planning/handoffs/2026-05-31-package-checklist.md`
- `.planning/packets/2026-06-01/INDEX.md`
- `.planning/packets/2026-06-01/CODEX_READY-cohost-viber-release-matrix-wrapper.md`

## What Changed

- Added a release wrapper that coordinates the cohost/Viber proof lanes and
  writes their stdout/stderr/report artifacts into one run directory.
- Supports `automation`, `release`, `first-pass`, and `audio-evidence` modes.
- Supports FLX4 proof policy as `auto`, `required`, or `skip`.
- Projects the next recommended command/action when a gate fails, including
  live rehearsal, runtime canaries, FLX4 retries, and direct MIDI diagnostics.

## Evidence

Syntax:

```text
bash -n scripts/release/check_cohost_viber_matrix.sh
```

Wrapper tests:

```text
uv run pytest -q tests/eval/test_check_cohost_viber_matrix_sh.py
20 passed in 3.23s
```

Lint:

```text
uv run ruff check tests/eval/test_check_cohost_viber_matrix_sh.py tests/eval/test_check_cohost_viber_live_rehearsal_sh.py
All checks passed!
```

Safe automation run:

```text
COHOST_VIBER_MATRIX_MODE=automation COHOST_VIBER_MATRIX_FLX4=skip COHOST_VIBER_MATRIX_OUT_DIR=/tmp/vibemix-cohost-viber-matrix-codex PYTHON="$PWD/.venv/bin/python" PYTHONPATH="$PWD/src" bash scripts/release/check_cohost_viber_matrix.sh
PASS check_cohost_viber_matrix: mode=automation ok=True autopilot=True corpus=True runtime=True flx4=skip first_pass=True reprompt_debt=0 audio_evidence_debt=0 direct_midi=skip midi_motion_diag=skip flx4_missing=skip next_action=ready actions=1 recommended_command=none runbook=/tmp/vibemix-cohost-viber-matrix-codex/operator_action_runbook.sh out_dir=/tmp/vibemix-cohost-viber-matrix-codex
```

## Boundaries

- No broad staging, no commit, and no product-release claim.
- This is release/proof automation only; it does not change runtime behavior.
- The safe automation proof skipped physical FLX4 hardware. Release mode still
  needs `COHOST_VIBER_MATRIX_FLX4=required` on the final rig.
- `/tmp` run outputs are scratch evidence; this packet and the checklist are the
  durable record.

## Next Required Proof

Before release, rerun the matrix in release mode after the final source/package
is settled, with `COHOST_VIBER_MATRIX_FLX4=required` when the DDJ-FLX4 rig and
live socket are ready.
