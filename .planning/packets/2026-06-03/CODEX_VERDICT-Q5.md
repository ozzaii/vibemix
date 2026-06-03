# CODEX VERDICT - Q5 cue-judge real press timing

- Item: Q5 - Fix the cue-judge faked-perfect input before any cue voicing.
- SHA: `0d73c7e1 fix(learn): grade hot cues from real press timing`
- User value: a Pro Learn user practicing hot cues now earns cue credit from the actual press timing, not a fabricated drop lock.

## By-eye / live artifact

- Launched current source with `VIBEMIX_DEV_SIDECAR=1 VIBEMIX_OUTPUT_DEVICE='Multi-Output Device' uv run python -m vibemix`.
- Boot confirmed meeting-safe audio routing:
  - `AI voice -> Multi-Output Device @ 24000Hz`
  - `djay passthrough -> Multi-Output Device @ 48000Hz`
- Live session: `20260603-143126`.
- Drove L2.10 over the live ws bus:
  - `ipc.learn.start_lesson {"lesson_id":"L2.10","level":"fresh"}` returned `ipc.learn.lesson_loaded`.
  - Immediate `ipc.learn.ack {"control_id":"hotcue:B","source":"click","value":127,"prev_value":0,"direction":"down"}` returned `ipc.learn.advance` with `reason:"action_matched"`.
- Recording proof:
  - `events.jsonl` contains `learn_action_observed` for `hotcue:B` at `t=22.21`, `matched:true`.
  - `events.jsonl` contains `learn_lesson_completed` for `L2.10` at `t=22.917`.
  - `rg "CUE_PLACEMENT|learn_cue_placement"` over the session produced no cue-grade/credit event for the early press. That is the expected honest-null behavior for a non-creditable cue; the old faked-perfect path would have created citable cue credit.

## Checks

- `uv run pytest -q tests/learn/test_cue_placement_practice_driver.py tests/learn/test_cue_placement_judge.py tests/learn/test_cue_practice.py tests/learn/test_runtime_evidence_grounding.py` - 29 passed.
- `uv run ruff check src/vibemix/learn/cue_placement_practice_driver.py src/vibemix/learn/runtime.py tests/learn/test_cue_placement_practice_driver.py tests/learn/test_runtime_evidence_grounding.py` - passed.
- `git diff --check` - passed.

## Notes

- The live runtime now injects wall-clock lesson elapsed time into L2.10 cue actions until a future owned cue-audio cursor exists.
- The cue placement runtime currently logs `learn_cue_placement_practice_graded` only for creditable locks; wrong/off-target attempts return an honest grade result internally but do not write evidence or progress credit.
- No cue voicing was added in this item.
