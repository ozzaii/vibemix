## CODEX VERDICT: BPM Title Boundary

- Item: live BPM counter stale-through-title-boundary fix
- SHAs:
  - 75f48e3a `fix(runtime): clear stale bpm on title boundary`
  - 45f00f1b `fix(runtime): hold mid-track bpm alternate locks`
- User value: A live DJ now sees the BPM counter clear at a newly confirmed title
  instead of carrying the previous track's tempo into the next track.
- Source edit: `src/vibemix/state/refresh.py` clears the loop-local BPM ring/cache,
  downbeat phase, and BPM confidence when the real refresh loop confirms a new
  audible title.
- Tests:
  - `uv run pytest -q tests/state/test_refresh.py::test_tick_clears_stale_bpm_lock_on_confirmed_track_change tests/state/test_refresh.py::test_tick_clears_pre_title_bpm_lock_on_initial_track_identification tests/state/test_refresh.py::test_tick_preserves_direct_test_bpm_lock_without_live_ring tests/state/test_bpm_stabilize.py tests/state/test_bpm_bus_grounding.py`
  - `uv run pytest -q tests/state/test_refresh.py tests/state/test_bpm_stabilize.py tests/state/test_bpm_bus_grounding.py`
  - `uv run ruff check src/vibemix/state/refresh.py tests/state/test_refresh.py`
- By-eye artifact: current-source dev app relaunched with
  `VIBEMIX_DEV_SIDECAR=1 VIBEMIX_OUTPUT_DEVICE='Multi-Output Device'`; `ui.log`
  showed `track=horsegiirL - an apple a day` with `bpm:null` at
  `2026-06-03T14:24:27.942070+00:00`, then a later lock at `bpm:171.4`.
- By-eye mid-track artifact: after `45f00f1b`, a 65s socket sampler collected
  597 `ipc.session.snapshot` frames; `100 gecs - dog food` held at `bpm:101.7`
  for the whole grounded window, with only one `grounded=false` idle dip to
  `bpm:null` before returning to `101.7`.
- Meeting-safe artifact: the same bus window showed `voice.rms=0`, `voice.peak=0`,
  and `ipc.status.tick` reported `livekit=ok`, `gemini=ok`, `midi=1`.
- Remaining note: this fixes stale BPM across title boundaries and prevents
  same-title far-away alternate locks from replacing the public counter. It does
  not claim the audio-only BPM estimator is globally perfect on every genre;
  further estimator quality work should use track metadata or model-grade beat
  analysis when available.
