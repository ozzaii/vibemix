# CODEX VERDICT — B1-RAMP

Item: `CODEX_READY-B1B2-HARDENING-PINS.md` / PIN B1-RAMP.

Code SHA: cdc369fd `fix(learn): ramp owned deck rate changes`

## User Value

A Pro Learn user on the fused beatmatch practice path gets smoother owned-deck
audio when they move the pitch control quickly: the practice loop glides instead
of zipper-clicking at the block boundary.

## What Changed

- `MiniDeck` now carries previous playback rates and equal-power gains.
- When `rate_a`, `rate_b`, or `xfader` changes between blocks, `render_block`
  linearly ramps that value across the next block.
- Rate ramps integrate the per-frame rate into the carried fractional cursor,
  preserving the no-gap/no-drift invariant.
- `TwoDeckPlayer` clamps once at the output boundary after copying the rendered
  block into the headphone stream buffer.

## Proof

Focused tests:

- `uv run pytest -q tests/audio/test_miniplayer_gain_ramp.py tests/learn/test_two_deck_player.py tests/learn/test_practice_loop.py`
  - `16 passed`
- `uv run pytest -q tests/learn/test_runtime_invariants.py tests/state/test_refresh.py tests/state/test_music_state.py`
  - `85 passed`
- `uv run pytest -q tests/learn/test_no_speculative_phrase.py tests/prompts/test_negative_dict.py tests/state/test_hype_anti_slop.py tests/state/test_coach_anti_slop.py`
  - `36 passed`
- `uv run pytest -q tests/learn/test_no_new_ws_port.py tests/runtime/test_ws_bus.py`
  - `19 passed`
- `uv run ruff check src/vibemix/audio/miniplayer.py src/vibemix/learn/two_deck_player.py tests/audio/test_miniplayer_gain_ramp.py tests/learn/test_two_deck_player.py`
  - `All checks passed`
- `git diff --check -- ...touched paths...`
  - clean

Offline by-eye audio proof, meeting-safe:

```json
{
  "rate_b_error": 0.0,
  "rate_b_expected_integral": 188.16,
  "rate_b_frame": 188.16,
  "xfader_first_post_sample": 1.0,
  "xfader_last_pre_sample": 1.0,
  "xfader_max_seam_delta": 0.03225809335708618
}
```

Interpretation:

- The post-jump xfader block starts at the same level as the prior block ended.
- The largest seam-adjacent delta is a small ramp step, not a full-scale jump.
- The `rate_b` cursor equals the exact integrated ramp, with zero error.

## Assumptions

- By-ear Learn playback was not exercised because Kaan had asked to avoid
  surprise speaker output. The proof is an in-memory render of the same
  `MiniDeck` path used by the headphone callback.
- The live-set safety gate remained unchanged: `TwoDeckPlayer.can_play()` still
  refuses lesson audio while a live set is active and audible.
