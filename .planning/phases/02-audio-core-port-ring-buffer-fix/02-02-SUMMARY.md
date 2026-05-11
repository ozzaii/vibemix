---
phase: 02-audio-core-port-ring-buffer-fix
plan: 02
type: summary
status: complete
completed_at: 2026-05-11
wave: 2
commit: 59fdb62
---

# Wave 2 — Pre-allocated Ring Buffers (np.concatenate fix)

**Commit:** `59fdb62`

## What Wave 2 Delivered

The np.concatenate-per-callback regression (PITFALLS.md P5) is structurally fixed. All four buffer primitives ported from `cohost_v4.py:289-523` into `src/vibemix/audio/buffers.py`:

- **AudioBuffer** (16kHz int16 mono, default 140s ring) — pre-allocated `np.zeros(size)` + modular write-pointer + `threading.Lock`. Zero-alloc on push. Fixes v4:300.
- **MicBuffer** (48kHz float32 mono, 200ms ring) — same pre-allocated pattern + distinct `_read`/`_write` pointers (pull consumes). LOAD-BEARING `_current_gain` mic-gate IP (v4:449-457) intact. Fixes v4:462.
- **PassthroughBuffer** (bytearray, 500ms cap) — verbatim drop-half-on-overflow (v4:487-492). Underflow zero-pads per PATTERNS.md §7 (fixes v4 PassthroughBuffer-vs-PlaybackQueue inconsistency).
- **PlaybackQueue** (unbounded bytearray) — verbatim port of v4:503-523. `push` triggers `levels.update_voice`; empty `pull` triggers `levels.decay_voice` — the feedback-suppression IP.

Plus `BufferRegistry` (frozen dataclass) aggregating the four buffers + shared `Levels` for Plan 04's `AudioMacOS(registry, ...)` constructor.

## Files Created

- `src/vibemix/audio/buffers.py` — 4 buffer classes (~250 LOC)
- `src/vibemix/audio/registry.py` — `BufferRegistry` frozen dataclass
- `tests/audio/test_buffers.py` — 21 tests covering wrap, zero-alloc, identity, cold-start, drop-half, underflow zero-pad, levels integration, edge cases, parametrized sizes

## Files Modified

- `src/vibemix/audio/__init__.py` — re-exports `AudioBuffer`, `MicBuffer`, `PassthroughBuffer`, `PlaybackQueue`, `BufferRegistry`

## Verification

- `grep -rE "np\.concatenate" src/vibemix/audio/` returns ONLY docstring mentions of the bug being fixed (4 matches, all inside `"""..."""`) — zero matches in push paths
- `uv run pytest tests/audio/ -x -q` — 35 tests green (14 Wave 1 + 21 Wave 2)
- `uv run pytest -x -q` — full suite 45 green
- `uv run ruff check src/vibemix/audio tests/audio` — clean
- `uv run ruff format --check src/vibemix/audio tests/audio` — clean
- `tracemalloc` test: 100 sustained 480-frame pushes allocate < 1KB in `buffers.py` (both `AudioBuffer` and `MicBuffer` paths)
- `id(buf._buf)` stable across 1000 pushes (object-identity canary)

## Decisions

- Both pre-allocated ndarray + write-pointer + lock — RESEARCH.md Q1: rolled our own (~30 LOC per class), no `dvg-ringbuffer` / `numpy-ringbuffer` dep
- `snapshot(n, out=None)` accepts optional pre-allocated output ndarray (RESEARCH.md Pitfall 1: Phase 3 state_refresh_loop reads at ~10Hz)
- `MicBuffer.push` calls `levels.update_mic(samples * gain)` OUTSIDE its own lock (Levels has its own lock) → no deadlock with snapshot readers
- `PassthroughBuffer.pull` zero-pads inline (drops v4 `b""` inconsistency per PATTERNS.md §7) — caller never branches on length
- Two tracemalloc tests (AudioBuffer + MicBuffer paths) so both v4 bug sites (300 + 462) are independently pinned

## Deviations from Plan

- `PassthroughBuffer.pull` zero-pads on underflow (PATTERNS.md §7 reconciliation), diverging from v4:494-500's `b""` return. Documented in class docstring + RING-09 test pins the new behavior.

## Handoff to Wave 3

Plan 03 can now:
- Import `AudioBuffer.snapshot(n)` for the DSP free functions (`snapshot_features`, `estimate_bpm`, `energy_curve`, `long_arc_curve`, `snapshot_wav`)
- Import `BufferRegistry` for Plan 04's AudioMacOS constructor signature

## Threat Mitigation

- **T-02-02-01 (DoS — push regression)**: RING-02 + RING-03 tests fail CI if np.concatenate creeps back
- **T-02-02-03 (Tampering — mic-mute bypass)**: RING-06 + RING-07 pin the feedback-suppression IP
- **T-02-02-04 (Info Disclosure — cold-start)**: RING-04 pins the `_filled` counter behavior
