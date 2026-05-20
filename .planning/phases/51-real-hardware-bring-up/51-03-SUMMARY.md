# 51-03 SUMMARY — ≥30-min stability soak harness (RSS + playback-underrun)

**Requirements:** BRINGUP-05
**Status:** complete (engineering); real ≥30-min run deferred to Kaan-action

## Harness design

`src/vibemix/runtime/soak.py` — a headless, duration-configurable sampler:

- **Underrun observation (hot path untouched).** `is_underrun()` + `SoakCounters`
  classify a `PlaybackQueue.pull()` result by comparing **requested vs held**
  bytes when audio was expected (`had_pending=True`). Because `pull()` always
  zero-pads to `n`, length alone can't reveal an underrun — so the harness
  drives the queue (it knows what it pushed) and inspects the return bytes.
  `src/vibemix/audio/buffers.py` is **not modified** — underruns are *observed*,
  not instrumented into prod (RESEARCH §3 underrun_decision; verified
  `git diff --quiet buffers.py` → UNCHANGED).
- **RSS sampling via psutil** (`psutil==7.2.2`, already a dep — no new
  dependency). `sample_rss(pid)` reads `memory_info().rss`; self when `pid`
  is None.
- **`run_soak(duration_s, pid, tick_hz, queue)` → `SoakResult`** drives a
  steady-state synthetic push/pull at `tick_hz`, samples RSS ~1Hz, and returns
  `baseline_rss` / `final_rss` / `max_rss` / `samples` / `underruns` / `pulls`
  / `duration_s`. Duration falls back to `VIBEMIX_SOAK_SECONDS` then the module
  default. One PCM chunk is pre-allocated and reused every tick so the harness
  itself doesn't dominate growth.
- **`assert_healthy()` asserts on GROWTH** (`final_rss - baseline_rss`), not
  absolute RSS (macOS shared-page + PyInstaller footprint noise — RESEARCH §3
  landmine), plus zero underruns. MB-formatted failure messages.

## Tests (`tests/runtime/test_soak_stability.py`)

- **unit (default run):** underrun classifier + `SoakCounters` against a REAL
  `PlaybackQueue(Levels())` — full pulls don't count, empty/partial pulls do;
  `sample_rss` returns a positive int; `assert_healthy` raises on growth
  over-budget + on underruns, passes on a healthy result.
- **slow (`pytest -m slow`):** a short (1.0s, scaled tick) synthetic soak
  driving a real `PlaybackQueue`, asserting bounded RSS growth + zero
  underruns in steady state.
- **deselect guard (default run):** a subprocess `pytest -m "not slow"
  --collect-only` proves the slow soak is filtered from the default run
  (the unit + guard tests remain collectable).
- **cli smoke (`cli`-marked):** `python -m vibemix.runtime.soak --seconds 1`
  runs + exits 0 + prints a result summary.

## CLI entry + Kaan-action handoff

```
python -m vibemix.runtime.soak --seconds 1800 --attach          # real ≥30-min run
python -m vibemix.runtime.soak --seconds 1800 --pid <sidecar>   # explicit pid
```

`--attach` best-effort discovers the running `vibemix-core` / `-m vibemix`
sidecar pid (falls back to `--pid` / self). Verified live: `--attach` found the
running sidecar (pid 73207, the live `cargo tauri dev` session) and sampled its
RSS (117.7MB, stable) — the harness works against the real process exactly as
Kaan will use it for the ≥30-min sign-off.

## Verification (observed)

- `pytest tests/runtime/test_soak_stability.py -q -k "underrun or deselect"` → green.
- `pytest -m slow tests/runtime/test_soak_stability.py -q` → **1 passed** (bounded RSS + zero underruns).
- `pytest -m "not slow" --collect-only tests/runtime/test_soak_stability.py` → 7/8 collected (slow deselected).
- `python -m vibemix.runtime.soak --seconds 2` → **HEALTHY**, exit 0.
- `python -m vibemix.runtime.soak --seconds 1 --attach` → attached to live sidecar pid 73207, exit 0.
- `git diff --quiet src/vibemix/audio/buffers.py` → UNCHANGED (hot path untouched).

## Deviation

The three plan tasks (underrun counter → RSS sampler → slow test + CLI) landed
in a single atomic commit rather than three, because `soak.py` +
`test_soak_stability.py` are two new, fully interdependent files (splitting the
single new module across three partial-file stages would be artificial). All
three tasks' acceptance criteria are met. TDD discipline preserved: the test
file was written first (RED — `ModuleNotFoundError`) before `soak.py` made it
green.

## Kaan-action (deferred, NOT gated by this phase)

The real **≥30-min live DJ-set soak** on the MacBook (his ears + hands) is the
true BRINGUP-05 sign-off (per project_phase_16_kaan_dj_testing). Run it with the
CLI above against the live sidecar.

## Commits

- `6a80cd5` feat(51-03): stability soak harness — RSS sampler + underrun counter + slow test + CLI.
