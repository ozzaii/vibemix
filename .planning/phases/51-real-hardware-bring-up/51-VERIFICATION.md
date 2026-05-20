---
phase: 51
slug: real-hardware-bring-up
status: human_needed
verified: 2026-05-21
verifier: GSD verification (Opus 4.7)
diff_range: 209a1e2..c029f6a
---

# Phase 51 — Goal-Backward Verification

> Verifies the Phase 51 implementation against its three requirements +
> success criteria, working backward from the goal. **Status: `human_needed`**
> — every engineering deliverable is verified green; the only outstanding item
> is the real ≥30-min live DJ-set soak on Kaan's Mac, which is an explicit
> Kaan-action (autonomous carveout), NOT an engineering gap.

---

## Phase goal (from 51-CONTEXT)

> Boot the app + Python sidecar on Kaan's real Mac, reach a stable live
> "listening" session with clean startup logs, and survive a ≥30-min full-set
> run with zero unhandled exceptions or unbounded memory. Covers BRINGUP-01,
> BRINGUP-04, BRINGUP-05. Audio-path (BRINGUP-02 → Phase 52) and controller
> (BRINGUP-03 → Phase 53) are out of scope.

---

## Requirement-by-requirement

### BRINGUP-01 — boots to a stable live "listening" session, clean startup

**Status: PASSED (engineering) + observed-live this session.**

- Boot was observed green live this session (51-CONTEXT §code_context):
  `cargo tauri dev` brings up the Rust app, the `vibemix-core` sidecar, Vite UI
  on `:1420`, and the mascot/levels ws_bus on `:8765` broadcasting ~30Hz at
  `phase=silent`, `mic≈0.003`, no crash.
- The boot-smoke regression test
  (`test_boot_smoke_reaches_phase_silent_cleanly`, BRINGUP-01) asserts a
  default idle `MusicState` boots to a broadcasting state within a bounded 2.0s
  window of the client connecting, every mascot frame's `phase` equals the real
  `MusicState().phase` idle default (`'silent'`, read not hard-coded, with a
  sanity pin), and ZERO empty frames over the window. **Green.**

Evidence: `pytest -m integration tests/runtime/test_ws_bus_empty_frames.py` →
2 passed (boot-smoke included).

### BRINGUP-04 — runtime errors triaged / fixed

**Status: PASSED.** Two surfaced runtime issues closed:

1. **ws_bus empty-frame** — root-caused (the live `{}` in the `:8765` tap was a
   tap-side mis-decode of WS control frames, not an app emit) and a permanent
   emit-boundary guard added so the bus can never serialize an empty/meter-less
   mascot frame even under a future upstream regression. Pinned by
   `test_ws_broadcast_emits_no_empty_frames` (real WS bind, non-zero
   frame-count guard). **Green.**
2. **Stale-sidecar dev loop** — the dev sidecar was a pre-built PyInstaller
   binary that did not reflect `src/vibemix/` edits, so source fixes were
   invisible under `cargo tauri dev`. Closed with an env-gated dev source-spawn
   (`VIBEMIX_DEV_SIDECAR=1` → `python -m vibemix` from repo HEAD) whose release
   path is byte-identical when the flag is absent (verified — see 51-REVIEW §2),
   plus `scripts/dev/run_sidecar_from_source.sh` + the dev-loop env contract.
   Pinned by 5 `resolve_sidecar` Rust unit tests incl.
   `resolve_sidecar_flag_absent_returns_bundled`. **Green.**

Evidence: `pytest -m integration tests/runtime/test_ws_bus_empty_frames.py` →
2 passed; `cargo test resolve_sidecar` → 5 passed.

### BRINGUP-05 — ≥30-min stability (no dropout / hang / leak)

**Status: PARTIAL — engineering PASSED; the real ≥30-min run is `human_needed`.**

Per the two-layer split locked in 51-CONTEXT §decisions + §deferred and
`project_phase_16_kaan_dj_testing`:

- **Engineering ships (PASSED):** a headless soak harness (`soak.py`) that
  samples sidecar RSS (psutil — no new dep) and counts playback-queue underruns
  by observing the REAL `PlaybackQueue.pull()` bytes (hot path unmodified),
  asserting bounded RSS *growth* (not absolute — macOS noise) and zero
  underruns; a SHORT `slow`-marked synthetic soak; and a one-command CLI
  (`python -m vibemix.runtime.soak --seconds N [--attach|--pid]`). The `slow`
  marker deselects the soak from the default run (proven by a real
  `--collect-only -m "not slow"` subprocess test). **Green.**
- **Kaan-action (`human_needed`, NOT a gap):** the true ≥30-min live DJ-set
  soak on Kaan's MacBook — his ears + hands, real audio through BlackHole. This
  is the deferred autonomous carveout. Run sign-off:
  `python -m vibemix.runtime.soak --seconds 1800 --attach` against the live
  sidecar during a full set; confirm zero underruns + bounded RSS + no
  dropout/hang.

Evidence: `pytest -m "slow or cli" tests/runtime/test_soak_stability.py` →
green (short synthetic soak: 0 underruns, bounded growth; CLI exits 0 HEALTHY).

---

## Success-criteria checklist (from 51-VALIDATION Per-Task map)

| Task | Requirement | Test | Result |
|------|-------------|------|--------|
| 51-01-01 | BRINGUP-04 | ws_broadcast never emits `{}`/meter-less (integration) | ✅ green |
| 51-01-02 | BRINGUP-04, 01 | boot-smoke reaches phase=silent, no empty frames | ✅ green |
| 51-02-01 | BRINGUP-04 | dev source-spawn gated by env; bundled unchanged when absent | ✅ green (5 Rust tests) |
| 51-02-02 | BRINGUP-04 | rebuild/dev-loop script present + runnable | ✅ present (`scripts/dev/run_sidecar_from_source.sh`, `bash -n` clean) |
| 51-03-01 | BRINGUP-05 | soak sampler: bounded RSS growth + zero underruns | ✅ green (slow) |
| 51-03-02 | BRINGUP-05 | slow marker deselects from default; CLI entry exists | ✅ green |

---

## Aggregate test evidence

- `pytest -m "slow or integration or cli or not slow" tests/runtime/{test_ws_bus,test_ws_bus_empty_frames,test_ws_bus_snapshot,test_soak_stability}.py` → **27 passed** (independently re-run this verification)
- `pytest -q tests/runtime/` (default markers) → **175 passed**
- `cargo test resolve_sidecar` → **5 passed**; `cargo test repo_root_from_manifest` → **1 passed**
- `cargo check` (Tauri crate) → clean
- Executor-reported full default suite → 3670 passed, 0 failed, 25 skipped (not re-run in full here; the Phase-51-touched subsets above re-verified green)

---

## Verdict

**Status: `human_needed`.**

- BRINGUP-01 ✅ passed (boot green live + regression test).
- BRINGUP-04 ✅ passed (ws_bus empty-frame + stale-sidecar dev loop both closed).
- BRINGUP-05 ✅ engineering passed (soak harness + short automated run + CLI);
  ⏳ the real ≥30-min live DJ-set soak is the deferred Kaan-action sign-off — an
  explicit autonomous carveout, NOT an engineering gap.

No `gaps_found`. The single open item is human/hardware by design. Phase 51 is
COMPLETE from an engineering standpoint and clear to transition + advance to
Phase 52, with the ≥30-min live soak carried forward on the Kaan-action surface.
