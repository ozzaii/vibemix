# CODEX VERDICT — BPM-FAR-SWITCH-STABILITY

- Item: live BPM counter jumped across far-away in-range locks on the same track.
- SHA: `a35efe01 fix(runtime): steady far-away bpm switches`
- User value: a Free user watching the live deck gets a steady tempo read instead of the counter hopping from one plausible autocorr layer to another.

## By-Eye Artifact

The live UI log on current source had shown one track moving through values like `162.2`, `113.2`, and `111.1`. The stabilizer already rejected one-off outliers, but it accepted a far-away lock after only three agreeing samples in a five-sample ring.

Pinned regression:

```python
_stabilize_bpm([162.2, 125.0, 111.1, 111.1, 111.1], previous=162.2) == 162.2
```

Real app proof after relaunch with `VIBEMIX_DEV_SIDECAR=1 VIBEMIX_OUTPUT_DEVICE='Multi-Output Device'`:

```json
{
  "samples": 991,
  "snapshot_samples": 330,
  "unique_sequence": [166.7],
  "max_unique_jump": 0.0,
  "status_last": {"livekit": "ok", "gemini": "ok", "midi": 1, "screen": "unavailable"}
}
```

## Gates

- `uv run pytest -q tests/state/test_bpm_stabilize.py tests/state/test_bpm_bus_grounding.py` -> 12 passed.
- `uv run pytest -q tests/state/test_refresh.py tests/state/test_bpm_stabilize.py tests/state/test_bpm_bus_grounding.py tests/runtime/test_ws_bus_snapshot.py` -> 94 passed.
- `uv run ruff check src/vibemix/state/refresh.py tests/state/test_bpm_stabilize.py` -> pass.
- `git diff --check` -> pass.

## Notes

- Small drift still updates immediately (`166.7 -> 169.0` stays allowed).
- A far-away switch still happens after a stronger four-sample majority, so true tempo changes can settle; the public counter just stops chasing a three-sample wrong lock.
