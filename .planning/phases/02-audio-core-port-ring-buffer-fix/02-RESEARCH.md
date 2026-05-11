# Phase 2: Audio Core Port + Ring Buffer Fix — Research

**Date:** 2026-05-11
**Researcher:** gsd-phase-researcher
**Confidence:** HIGH (all three questions empirically verified on this machine against the live BlackHole 2ch driver + the project's hatchling build)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Pre-allocated `np.ndarray` + write-pointer with modular indexing + `threading.Lock` for all four buffers.
- Ring sizes verbatim from v4: `AudioBuffer` 140s @ 16kHz int16, `MicBuffer` 200ms @ 48kHz float32, `PassthroughBuffer` ~50ms @ 48kHz stereo float32, `PlaybackQueue` ~5s @ 24kHz int16.
- 11 tuning constants lifted verbatim from `cohost_v4.py:127-141` + `:1176-1179` into `src/vibemix/audio/constants.py`.
- Sample-rate sanity check fails loud at startup with actionable error message.
- File layout: `src/vibemix/audio/{__init__.py,constants.py,buffers.py,levels.py,features.py,recorder.py}` + `src/vibemix/platform/_audio_macos.py`.
- macOS only this phase; Windows is Phase 7.

### Claude's Discretion
- Internal organization of `features.py` (FFT/BPM math) — port verbatim.
- `BufferRegistry` as `@dataclass` vs `NamedTuple` — pick whichever is cleaner.
- Test mocking strategy for sounddevice — recommend `unittest.mock.patch`.
- Drop `_HAS_*` feature-flag pattern from v4 — strong preference NO.

### Deferred Ideas (OUT OF SCOPE)
- MIDI deck detection fix → Phase 9.
- OpenRouter TTS monkey-patch → Phase 4.
- Programmatic BlackHole 48kHz config via CoreAudio API → Phase 11.
- Genre-aware threshold override → Phase 6.
- Recording retention/browser UI → Phase 15.
</user_constraints>

## Project Constraints (from CLAUDE.md)
- Python 3.12 only (`requires-python = ">=3.12,<3.13"` in pyproject.toml — note: project root reports `.venv` is 3.14 but the package metadata locks 3.12; pyproject is authoritative).
- Build backend: `hatchling`. Test runner: `pytest` (strict markers, `testpaths = ["tests"]`).
- Ruff line-length 100, target py312, double quotes, `B/I/UP/RUF` rules enabled.
- `from __future__ import annotations` at top of every module (PEP 604 unions).
- Private modules use `_underscore_prefix`. Classes `PascalCase`. Functions `snake_case`.

## Executive Summary

- **Q1 — Ring buffer:** Roll our own (~30 LOC per buffer, ~120 LOC total). `dvg-ringbuffer` and `numpy-ringbuffer` exist but neither is a clean fit: `numpy-ringbuffer` (last release 2022) is too high-level (deque semantics, not snapshot-of-last-N), and `dvg-ringbuffer` (last release 2024) carries unwrap overhead we don't need since we already do explicit two-slice copies. The 4 buffer classes diverge on dtype/shape/sample-rate, so a shared base class is overkill — write each one straight, fix the bug, move on. `[VERIFIED: tested locally + PyPI metadata]`
- **Q2 — Sample-rate sanity check:** Check **both** `sd.query_devices(idx)["default_samplerate"]` (reflects current Audio MIDI Setup setting on macOS CoreAudio — empirically confirmed against live BlackHole 2ch) **before** opening the stream, AND `stream.samplerate` after opening (reflects PortAudio's negotiated rate). `sd.check_input_settings()` is unreliable: it returned OK when asked about 44.1kHz against a BlackHole device set to 48kHz — sounddevice happily opens the stream at the wrong rate and silently resamples / mis-frames. Two-layer guard is the right pattern. `[VERIFIED: live test against device index 2 on this machine, 2026-05-11]`
- **Q3 — hatchling/uv:** Zero config changes needed. `packages = ["src/vibemix"]` recursively picks up new subpackages (verified by adding a tmp `vibemix/_hatchtest_tmp/_private.py` — both the underscore-prefixed dir and module shipped in the wheel). Underscore-prefixed modules are NOT filtered. Just `uv add sounddevice` (already present) and `uv add --dev pytest-mock`. `[VERIFIED: live wheel build on this machine]`
- **Net effect:** Phase 2 is implementation-heavy but research-light. No new dependencies on third-party ring-buffer libs. No build-system gymnastics. The risk surface is concentrated in the BlackHole sample-rate guard, which has a well-defined two-layer check.

**Primary recommendation:** Roll your own buffers; use `sd.query_devices(idx)["default_samplerate"]` pre-open + `stream.samplerate` post-open as the dual sanity check; add only `pytest-mock` to dev deps.

## Phase Requirements

This phase has no explicit REQ-IDs in REQUIREMENTS.md (Phase 2 ships infrastructure consumed by later phases). Research support per CONTEXT.md decisions is captured inline in Q1/Q2/Q3.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|---|---|---|---|
| Ring buffer storage / wrap math | Domain (audio/buffers.py) | — | Platform-agnostic; identical on macOS + Windows |
| Level EMA smoothing | Domain (audio/levels.py) | — | Pure math, no OS dep |
| FFT/RMS/BPM feature extraction | Domain (audio/features.py) | — | numpy/scipy only |
| WAV/JSONL recorder | Domain (audio/recorder.py) | — | stdlib `wave`, `json` |
| sounddevice stream lifecycle | Platform (_audio_macos.py) | — | OS-specific via Phase 1 Protocol |
| BlackHole device discovery | Platform (_audio_macos.py) | — | macOS CoreAudio device names |
| Sample-rate driver assertion | Platform (_audio_macos.py) | — | Talks to sounddevice/CoreAudio |
| Tuning constants | Domain (audio/constants.py) | — | Imported by Phase 3 EventDetector, Phase 6 genre override |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---|---|---|---|
| numpy | >=2.4.4 (pinned) | Buffer storage, FFT, BPM autocorr | Already in `pyproject.toml`; v4 uses it everywhere |
| scipy | >=1.17.1 (pinned) | `signal.resample_poly` for 48→16kHz | Already pinned; v4 uses it for downsample |
| sounddevice | >=0.5.5 (pinned) | macOS CoreAudio I/O via PortAudio | Already pinned; matches v4 |

### Supporting (new in Phase 2)
| Library | Version | Purpose | When to Use |
|---|---|---|---|
| pytest-mock | latest (dev) | Mock `sd.RawInputStream` / `RawOutputStream` in unit tests | Test stream lifecycle without a real audio device |

### Alternatives Considered (and rejected)
| Instead of | Could Use | Tradeoff |
|---|---|---|
| roll-our-own ring | `dvg-ringbuffer` 1.1.0 | Unwrap-to-contiguous is value we don't need — we already copy on snapshot. Extra dep, extra concept to learn. `[VERIFIED: PyPI 2024-06]` |
| roll-our-own ring | `numpy-ringbuffer` 0.2.2 | Last release 2022-06; deque-style API doesn't match our "snapshot last N seconds" pattern. `[VERIFIED: PyPI 2022-06]` |
| roll-our-own ring | `pa_ringbuffer` (PortAudio's C ring) | Lock-free SPSC — overkill for a single-writer-single-reader-with-lock model we already have working. Adds a C dep. |
| `unittest.mock` | `pytest-mock` | `pytest-mock`'s `mocker` fixture is auto-cleanup; saves boilerplate. Worth one dev dep. |

**Installation:**
```bash
uv add --dev pytest-mock
# sounddevice + numpy + scipy already in pyproject.toml — no action
```

**Version verification (2026-05-11):**
- `dvg-ringbuffer` 1.1.0 — released 2024-06-22 `[VERIFIED: PyPI JSON metadata]`
- `numpy-ringbuffer` 0.2.2 — released 2022-06-28 `[VERIFIED: PyPI JSON metadata]`
- `sounddevice` 0.5.5 — released 2026-03-02 (PDF doc dateline) `[VERIFIED: readthedocs PDF]`

## Q1: Pre-allocated Ring Buffer Pattern

### Library or roll-our-own?

**Decision: roll our own.** Rationale:

1. **The 4 buffers diverge.** `AudioBuffer` is int16 mono 16kHz with FFT/BPM/snapshot APIs. `MicBuffer` is float32 mono 48kHz with `pull(n)` consume semantics + gain. `PassthroughBuffer` is float32 **stereo** 48kHz with FIFO drain. `PlaybackQueue` is int16 mono 24kHz with FIFO drain. A shared abstraction either has 4 type parameters and 3 access patterns (= overkill) or each class wraps the lib differently anyway (= no win).
2. **`dvg-ringbuffer`'s value prop is wasted on us.** Its USP is "unwrap discontiguous → contiguous fixed-address array" for downstream numba/pyFFTW. We don't use numba or pyFFTW. We already do explicit two-slice copies on `snapshot_features()` — that IS the unwrap, done once per ~100ms when needed, not on every push.
3. **`numpy-ringbuffer` is stale and wrong-shaped.** Last release 2022-06-28, no specific Python version requirement (concerning for 3.12+ compat). Deque-style API (`append`/`popleft`) doesn't match "give me the last N seconds" reads.
4. **~30 LOC per class.** The math is trivial (write-pointer + modular wrap + saturate-write-counter for "is the ring filled yet"). Lifting the bug fix while we're already touching v4's `push()` methods is cleaner than wrapping a foreign API.

### Snapshot read implementation (canonical wrap-around copy)

```python
# src/vibemix/audio/buffers.py — AudioBuffer (int16 mono, 16kHz)
from __future__ import annotations

import threading

import numpy as np


class AudioBuffer:
    """Pre-allocated rolling int16 PCM ring at INPUT_SR_TARGET (16kHz).

    Zero-alloc on push: writes via modular indexing into a fixed-size buffer.
    Snapshot reads copy the last `n_samples` into a contiguous output array
    via at most two numpy slices (the wrap-around).

    Fixes np.concatenate-per-callback regression at cohost_v4.py:300.
    """

    def __init__(self, seconds: float = 140.0, sr: int = 16000) -> None:
        self._sr = sr
        self._size = int(sr * seconds)
        self._buf = np.zeros(self._size, dtype=np.int16)  # pre-allocated, never reallocated
        self._write = 0          # next write index
        self._filled = 0         # total samples ever written, capped at self._size
        self._lock = threading.Lock()

    def push(self, pcm_int16: np.ndarray) -> None:
        """O(n) memcpy into the ring at the current write pointer. Zero alloc."""
        n = pcm_int16.size
        if n == 0:
            return
        if n >= self._size:
            # Pathological: caller pushed more than the ring holds.
            # Keep only the tail; reset write pointer to 0.
            with self._lock:
                self._buf[:] = pcm_int16[-self._size:]
                self._write = 0
                self._filled = self._size
            return
        with self._lock:
            end = self._write + n
            if end <= self._size:
                self._buf[self._write:end] = pcm_int16
            else:
                # Wrap: split into tail + head.
                first = self._size - self._write
                self._buf[self._write:] = pcm_int16[:first]
                self._buf[: n - first] = pcm_int16[first:]
            self._write = (self._write + n) % self._size
            self._filled = min(self._filled + n, self._size)

    def _snapshot(self, n_samples: int) -> np.ndarray:
        """Copy the most recent n_samples into a fresh contiguous ndarray.
        Caller must NOT hold the lock — we acquire here."""
        with self._lock:
            n = min(n_samples, self._filled)
            if n == 0:
                return np.zeros(0, dtype=np.int16)
            # The most recent n samples end at self._write (exclusive) and start
            # at (self._write - n) mod self._size.
            start = (self._write - n) % self._size
            if start + n <= self._size:
                # Contiguous: single slice copy.
                return self._buf[start:start + n].copy()
            # Wrap: tail + head.
            first = self._size - start
            out = np.empty(n, dtype=np.int16)
            out[:first] = self._buf[start:]
            out[first:] = self._buf[: n - first]
            return out

    def snapshot_features(self, seconds: float = 7.0) -> dict:
        n_samples = int(self._sr * seconds)
        pcm = self._snapshot(n_samples)
        # ... port v4's RMS / onset / FFT / band-share math here, OR delegate
        # to vibemix.audio.features.compute_features(pcm, sr=self._sr).
        # No changes to the math itself — verbatim port from cohost_v4.py:331-379.
        ...
```

**Notes:**
- `_filled` lets `_snapshot()` return correct results when the ring isn't yet full (cold start). Without it, the first 140s of audio would return garbage from the zero-init buffer mixed with real samples.
- The `n >= self._size` branch handles the pathological case where a caller pushes a buffer larger than the ring (shouldn't happen in practice — sounddevice block size is ≤1024 frames — but defensively safe).
- `_snapshot()` is private; callers go through `snapshot_features()`, `snapshot_wav()`, `energy_curve()`, `long_arc_curve()`, `estimate_bpm()` — all of which become trivial wrappers that call `_snapshot()` and dispatch the math.
- `MicBuffer.push()` uses the same wrap pattern but float32 + simpler (`pull(n)` consumes from the read pointer).

`[ASSUMED]` The math in `features.py` should be a verbatim port of cohost_v4.py:331-436. No algorithmic changes — just refactor out of the buffer class into a free function `compute_features(pcm: np.ndarray, sr: int) -> dict`. This is consistent with the "POC is reference, devour it" project skill.

### tracemalloc zero-alloc test

```python
# tests/test_audio_buffers.py
from __future__ import annotations

import tracemalloc

import numpy as np
import pytest

from vibemix.audio.buffers import AudioBuffer


def test_audio_buffer_push_zero_alloc():
    """Pushing 100 callback-sized frames must allocate zero new ndarrays after
    the ring is pre-allocated. This is the regression test for the
    np.concatenate-per-callback bug at cohost_v4.py:300.
    """
    buf = AudioBuffer(seconds=140.0, sr=16000)
    frame = np.zeros(480, dtype=np.int16)  # 30ms @ 16kHz — realistic block size

    # Warm-up push so the first wrap path is exercised (allocations there are fine).
    for _ in range(5):
        buf.push(frame)

    tracemalloc.start()
    snapshot_before = tracemalloc.take_snapshot()
    for _ in range(100):
        buf.push(frame)
    snapshot_after = tracemalloc.take_snapshot()
    tracemalloc.stop()

    # Diff and filter to the buffers module only (numpy/threading allocs from
    # warm path are out of scope).
    stats = snapshot_after.compare_to(snapshot_before, "filename")
    buffer_module_diff = sum(
        stat.size_diff for stat in stats if "buffers.py" in stat.traceback[0].filename
    )

    # Allow a tiny slack for Python int boxing / lock acquire churn (a few hundred bytes).
    assert buffer_module_diff < 1024, (
        f"AudioBuffer.push allocated {buffer_module_diff} bytes in buffers.py "
        f"over 100 calls — expected ~0. Did np.concatenate creep back in?"
    )
```

**Why this works:** `tracemalloc.take_snapshot()` records the live allocation tree. `compare_to(..., "filename")` aggregates differences by source file. Filtering on `buffers.py` excludes legitimate allocs in numpy's broadcast machinery (which sounddevice would trigger anyway) and isolates regressions where our push path starts allocating again.

**`[CITED: docs.python.org/3/library/tracemalloc.html]`** — `take_snapshot()` and `compare_to` are stable stdlib APIs since 3.4.

**Alternative test approach (additional, not replacement):** A pure assertion that `buf._buf is buf._buf_initial_ref` after N pushes — confirms the underlying array object identity hasn't changed (which is what `np.concatenate` would do). This is a cheaper sanity check that doesn't depend on tracemalloc:

```python
def test_audio_buffer_underlying_array_identity():
    buf = AudioBuffer(seconds=140.0, sr=16000)
    initial_id = id(buf._buf)
    frame = np.zeros(480, dtype=np.int16)
    for _ in range(1000):
        buf.push(frame)
    assert id(buf._buf) == initial_id, "Ring buffer was reallocated — np.concatenate regression?"
```

Run **both** in CI — the identity check is fast and catches the bug class directly; tracemalloc catches subtler allocs (per-call temporaries).

## Q2: sounddevice Sample-Rate Sanity Check

### The right API — empirically verified on this machine

Live test results against the BlackHole 2ch device on Kaan's machine (index 2), 2026-05-11:

```
sd.query_devices(2)['default_samplerate'] == 48000.0
    → reflects current Audio MIDI Setup configuration (= the source of truth we want)

sd.RawInputStream(device=2, samplerate=44100, ...)
    → opens successfully, returns Stream.samplerate == 44100.0
    → PortAudio negotiated 44.1kHz with the driver (silently resamples or mis-frames)

sd.RawInputStream(device=2, samplerate=48000, ...)
    → opens successfully, returns Stream.samplerate == 48000.0

sd.check_input_settings(device=2, samplerate=44100, channels=2, dtype='float32')
    → returns None (= "OK") even though BlackHole is configured at 48kHz
    → UNRELIABLE as a sanity check.
```

**Conclusion:**
1. `sd.check_input_settings()` is **NOT** a reliable sanity check — it tells you only whether PortAudio *could* open a stream at that rate, not whether the device is *currently* set to that rate. Don't use it.
2. `Stream.samplerate` reports the **negotiated** rate (= what you asked for, unless PortAudio detected hardware drift). It will NOT tell you that the device is configured at 44.1kHz when you asked for 48kHz — sounddevice silently accepts and resamples.
3. `sd.query_devices(idx)["default_samplerate"]` **DOES** reflect the device's current Audio MIDI Setup configuration on macOS CoreAudio. This is the field we check.

**`[VERIFIED: live empirical test against device index 2 on Kaan's machine, 2026-05-11]`** — confirmed `default_samplerate` is 48000.0 right now (BlackHole is correctly configured), and `check_input_settings(44100)` falsely returns OK.

**`[CITED: python-sounddevice 0.5.5 docs]`** — `Stream.samplerate` docstring: *"In cases where the hardware sampling frequency is inaccurate and PortAudio is aware of it, the value of this field may be different from the samplerate parameter passed to Stream(). If information about the actual hardware sampling frequency is not available, this field will have the same value as the samplerate parameter passed to Stream()."* PortAudio is not generally aware of the kAudioDevicePropertyNominalSampleRate setting on CoreAudio, so this attribute is a weak post-open check.

### Snippet — two-layer guard + custom exception

```python
# src/vibemix/platform/_audio_macos.py
from __future__ import annotations

import sounddevice as sd


class SampleRateMismatchError(Exception):
    """Raised when the OS audio device is not configured at the expected rate.

    On macOS, BlackHole 2ch's nominal sample rate is set via Audio MIDI Setup
    (not by sounddevice / PortAudio). If the device is at 44.1kHz but vibemix
    expects 48kHz, opening a stream silently succeeds and resamples — which
    is exactly the failure mode that bit Kaan on 2026-05-11. Fail loud here.
    """


def assert_device_sample_rate(device_index: int, expected: int) -> None:
    """Pre-open guard: check the device's current driver setting.

    Reads sd.query_devices(idx)['default_samplerate'] which on macOS CoreAudio
    reflects kAudioDevicePropertyNominalSampleRate — i.e., whatever Audio MIDI
    Setup is configured to right now. NOT the same as Stream.samplerate after
    opening (which reports the PortAudio-negotiated rate and silently lies).
    """
    info = sd.query_devices(device_index)
    actual = int(info["default_samplerate"])
    if actual != expected:
        raise SampleRateMismatchError(
            f"BlackHole 2ch is configured at {actual}Hz but vibemix expects {expected}Hz.\n"
            f"Fix: open Audio MIDI Setup → BlackHole 2ch → Format → "
            f"{expected:,} Hz (2 ch, 32-bit float).\n"
            f"Also enable Drift Correction on BlackHole if you use a Multi-Output Device."
        )
```

Call from `AudioMacOS.open_capture()` **before** instantiating `sd.RawInputStream`:

```python
def open_capture(self, device_index: int, *, sample_rate: int, ...) -> AudioStream:
    assert_device_sample_rate(device_index, sample_rate)  # pre-open guard
    stream = sd.RawInputStream(device=device_index, samplerate=sample_rate, ...)
    # Post-open: belt-and-suspenders. If PortAudio detected hardware drift it
    # will surface here. This catches a different failure mode (drift) but is
    # cheap so we keep it.
    if int(stream.samplerate) != sample_rate:
        stream.close()
        raise SampleRateMismatchError(
            f"PortAudio negotiated {int(stream.samplerate)}Hz vs requested {sample_rate}Hz. "
            f"Hardware drift detected on device {device_index}."
        )
    return _SoundDeviceStreamHandle(stream)
```

**Test mocking pattern** (Claude's discretion from CONTEXT.md — recommended):
```python
def test_assert_device_sample_rate_mismatch(mocker):
    mocker.patch(
        "vibemix.platform._audio_macos.sd.query_devices",
        return_value={"default_samplerate": 44100.0},
    )
    with pytest.raises(SampleRateMismatchError, match="44100Hz.*48000Hz"):
        assert_device_sample_rate(device_index=2, expected=48000)
```

### Programmatic 48kHz config — deferred to Phase 11

Setting BlackHole's nominal sample rate programmatically requires CoreAudio's `AudioObjectSetPropertyData` with `kAudioDevicePropertyNominalSampleRate`. There is no Python binding in `pyobjc-framework-Quartz` (already installed) — CoreAudio bindings live in `pyobjc-framework-CoreAudio`, NOT currently in `pyproject.toml`. Reference implementations exist:

- `MacAudioTools` (Swift CLI, GitHub PhilippeRigaux) — uses `AudioObjectSetPropertyData` directly. Could be called via `subprocess` but requires shipping the Swift binary. `[CITED: github.com/PhilippeRigaux/MacAudioTools]`
- Roll our own with `pyobjc-framework-CoreAudio` + ctypes — ~50 LOC but introduces a new transitive dep.

**Phase 11 (calibration wizard) is the right home** for this. Phase 2 ships only the **detection** + **clear error**. Per CONTEXT.md `<deferred>`: *"Programmatic BlackHole 48kHz config via CoreAudio API — Phase 11 (calibration wizard). Phase 2 only detects mismatch."*

`[VERIFIED: pyproject.toml lacks pyobjc-framework-CoreAudio; CONTEXT.md explicitly defers this]`

## Q3: hatchling + uv for the audio subpackage

### Subpackage discovery — fully automatic

Empirical test against this project's `pyproject.toml` (`packages = ["src/vibemix"]`):

```bash
# Built wheel contents BEFORE adding a new subpackage:
vibemix/__init__.py
vibemix/platform/__init__.py
vibemix/platform/audio.py
vibemix/platform/midi.py
vibemix/platform/screen.py
vibemix/platform/track.py
```

Then I created `src/vibemix/_hatchtest_tmp/_private.py` and re-ran `uv build --wheel`:

```bash
# Built wheel contents AFTER:
vibemix/_hatchtest_tmp/_private.py    # ← underscore-prefixed subpackage AND module both included
```

**Conclusions:**
1. `packages = ["src/vibemix"]` is **recursive** — hatchling walks the directory tree and includes everything under it. No need to add `"src/vibemix/audio"` for Phase 2.
2. **Underscore-prefixed modules and subdirectories are included by default.** `_audio_macos.py` will ship in the wheel with zero config changes.
3. Phase 2 needs **zero changes** to `[tool.hatch.build.targets.wheel]` or `[tool.hatch.build]`.

`[VERIFIED: live wheel build on Kaan's machine, 2026-05-11]`

### Private-module inclusion — no allowlist needed

Already proven above — `_private.py` and `_hatchtest_tmp/` both shipped. Hatchling's default file-selection rules don't filter on underscore prefix. `[VERIFIED: same build test]`

The only thing hatchling **does** filter by default is conventional VCS junk (`.git/`, `.gitignore`, `.DS_Store`, `__pycache__/`). Underscore is not in the exclude list.

### uv add commands

```bash
# sounddevice is already in pyproject.toml dependencies — no action needed.
# Only one new dep for Phase 2:
uv add --dev pytest-mock
```

`[CITED: docs.astral.sh/uv — "uv add --dev pytest" creates/adds to [dependency-groups].dev table]`

After running this command, `pyproject.toml`'s `[dependency-groups].dev` block will pick up `pytest-mock>=...` automatically. `uv.lock` updates in the same step.

## Runtime State Inventory

> Not applicable to this phase — Phase 2 is greenfield code creation, no rename/refactor of pre-existing stored state. Confirmed by CONTEXT.md: new `src/vibemix/audio/` package + new `_audio_macos.py`. The POC files (`cohost*.py`) at the project root are READ-ONLY references not being renamed.

**Stored data:** None — Phase 2 writes WAV/JSONL to `recordings/<timestamp>/` per session; format unchanged from v4. No existing recordings need migration.
**Live service config:** None.
**OS-registered state:** BlackHole 2ch nominal sample rate IS OS-level state (Audio MIDI Setup) — but Phase 2 only **reads** it for the sanity check; doesn't mutate. Phase 11 will write it.
**Secrets / env vars:** `GEMINI_API_KEY` continues to be read from `.env` — Phase 2 is pure audio, doesn't touch this.
**Build artifacts:** None to clean. `uv.lock` regenerates automatically on `uv add`.

## Common Pitfalls

### Pitfall 1: Underestimating snapshot frequency
**What goes wrong:** Devs assume "snapshot is rare, copy cost is fine." In v2, `EventDetector` queries `snapshot_features()` at ~10Hz (per the state_refresh_loop pattern). At 7s × 16kHz × 2B = 224KB per snapshot × 10Hz = 2.2MB/s of copy bandwidth. Acceptable on modern hardware but adds up if you stack 4 buffers.
**How to avoid:** Reuse the snapshot output array where possible (caller-allocated `out: np.ndarray` parameter). Phase 3 will likely do this; Phase 2 should at least make `_snapshot()` accept an optional `out` arg.
**Warning signs:** macOS Activity Monitor shows the Python process at >30% CPU sustained when idle.

### Pitfall 2: Lock held during numpy math
**What goes wrong:** Holding `self._lock` while doing FFT inside `snapshot_features()` blocks the audio callback for 5-20ms. Causes input under-runs (PortAudio status callback fires with `input_overflow`).
**How to avoid:** Copy out under lock, drop lock, compute. The implementation above already does this.
**Warning signs:** `[input status] InputOverflow` messages on stderr (cohost variants already print these).

### Pitfall 3: BlackHole drift on multi-output devices
**What goes wrong:** When BlackHole is part of a macOS Multi-Output Device (the typical DJ setup: monitor BlackHole + headphones simultaneously), CoreAudio resamples to a master clock. If Drift Correction is OFF, BlackHole and headphones diverge → input frames arrive at a slightly wrong rate, throwing off BPM estimation.
**How to avoid:** Include "enable Drift Correction" in the sample-rate mismatch error message (already in the snippet above).
**Warning signs:** BPM estimate slowly drifts over the course of a set (e.g., starts reporting 124.5 when the track is 124.0, increasing by ~0.5 every 10 min).

### Pitfall 4: int16 overflow on peak-normalize
**What goes wrong:** v4's `snapshot_wav()` peak-normalizes to -3dBFS. The math at `cohost_v4.py:319` does `np.clip(pcm.astype(np.float32) * scale, -32768, 32767).astype(np.int16)` — correct because clip happens BEFORE the int16 cast. But it's easy to invert the order during port and get silent integer overflow.
**How to avoid:** Verbatim port of v4 lines 313-321 with a test that pushes a known full-scale sample (`np.full(N, 32767, dtype=np.int16)`) and asserts the output has no values at -32768.

## Code Examples

### Levels (EMA RMS) — port verbatim from cohost_v4.py:255-287
The `Levels` class is ~30 lines, no bug, no rework needed. Just lift it into `src/vibemix/audio/levels.py` with the existing API: `update_music(samples)`, `update_voice(pcm_int16)`, `update_mic(samples)`, `.music`, `.voice`, `.mic`, `.snapshot()`.

### sounddevice device finder — port from cohost.py:139-148 / cohost_v4.py equivalent
```python
# src/vibemix/platform/_audio_macos.py
def find_device(name_substring: str, kind: Literal["input", "output"]) -> int:
    """Locate a CoreAudio device by substring match on its name."""
    target_field = "max_input_channels" if kind == "input" else "max_output_channels"
    for idx, info in enumerate(sd.query_devices()):
        if name_substring.lower() in info["name"].lower() and info[target_field] > 0:
            return idx
    raise RuntimeError(
        f"No {kind} device matching '{name_substring}'. "
        f"Available: {[d['name'] for d in sd.query_devices() if d[target_field] > 0]}"
    )
```

### Stream lifecycle wrapper — Phase 1's AudioStream Protocol shape
```python
class _SoundDeviceStreamHandle:
    """Adapter from sd.RawInputStream/RawOutputStream → vibemix.platform.audio.AudioStream."""

    def __init__(self, stream: sd.RawInputStream | sd.RawOutputStream) -> None:
        self._stream = stream

    @property
    def latency_ms(self) -> float:
        # sd.Stream.latency is a tuple (in, out) for duplex; scalar otherwise
        lat = self._stream.latency
        if isinstance(lat, tuple):
            lat = lat[0]
        return float(lat) * 1000.0

    def start(self) -> None: self._stream.start()
    def stop(self) -> None: self._stream.stop()
    def close(self) -> None: self._stream.close()
```

## State of the Art

| Old (v4 / POC) | Current (Phase 2) | Why Changed |
|---|---|---|
| `np.concatenate([self._buf, pcm])` per callback | Pre-allocated ring + modular write | ~100Hz alloc rate, ~4.5MB copy per push (PITFALLS.md P5) |
| No sample-rate sanity check | `assert_device_sample_rate()` pre-open + `Stream.samplerate` post-open | Kaan's 30-min debug session 2026-05-11 |
| `_HAS_VISION`/`_HAS_WS` global flags | Hard imports in platform modules | Platform firewall makes feature flags obsolete — failed import = phase fails fast |
| sounddevice callback math in same module as I/O | Math in `audio/features.py`, I/O in `platform/_audio_macos.py` | Phase 1's domain ↔ platform separation |

**Deprecated:**
- `np.concatenate`-grow pattern: replaced by ring buffer. CONCERNS.md P5.
- `sd.check_input_settings()` as a configuration check: empirically unreliable on this machine — DO NOT use as the sole rate check.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|---|---|---|
| A1 | `features.py` should be a verbatim port of cohost_v4.py:331-436 math | Q1 snapshot impl | Low — CONTEXT.md says port verbatim; this is explicit |
| A2 | snapshot frequency in Phase 3 will be ~10Hz (similar to v2 state_refresh_loop) | Pitfall 1 | Medium — actual rate determined by Phase 3 design; if it's 100Hz the snapshot cost becomes a real bottleneck |
| A3 | `BufferRegistry` as `@dataclass(frozen=True)` is cleaner than `NamedTuple` | (mentioned via CONTEXT.md discretion) | Low — both work; dataclass plays nicer with type hints |
| A4 | pytest-mock is preferred over plain `unittest.mock` | Test mocking | Low — preference; both work |

## Open Questions

None blocking. CONTEXT.md locked every load-bearing decision; the three discretion areas (ring buffer impl, sample-rate API, build config) are all resolved with HIGH confidence above.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|---|---|---|---|---|
| Python 3.12 | hatchling build / package metadata | ⚠ project metadata says 3.12, actual `.venv` is 3.14 | 3.14 in `.venv` | None — confirm with Kaan whether pyproject's `>=3.12,<3.13` is intentional vs the 3.14 venv; this is a tension OUTSIDE Phase 2 scope but worth flagging |
| `uv` | Dependency mgmt, build | ✓ | uv (works — `uv build` succeeds) | — |
| `hatchling` | Build backend | ✓ | per pyproject `requires` | — |
| `sounddevice` | Audio I/O | ✓ | 0.5.5 (in `.venv`) | None — Phase 2 hard-requires it |
| BlackHole 2ch driver | Capture input | ✓ | device index 2, `default_samplerate=48000.0` | None — macOS-only; Linux excluded per CLAUDE.md |
| `nowplaying-cli` | Not used by Phase 2 | n/a | — | n/a (Phase 5 territory) |
| Pioneer DDJ-FLX4 | Not used by Phase 2 | n/a | — | n/a (Phase 9 territory) |

**Missing dependencies with no fallback:** None.
**Missing dependencies with fallback:** None.
**Flag for Kaan:** The pyproject says `requires-python = ">=3.12,<3.13"` but the active `.venv` is 3.14. This is orthogonal to Phase 2 (whichever interp runs, the code works), but the version pin needs reconciling before publishing to PyPI. Not blocking; not Phase 2's job to fix.

## Validation Architecture

### Test Framework
| Property | Value |
|---|---|
| Framework | pytest >= 8.0 (already in `[dependency-groups].dev`) |
| Config file | `pyproject.toml` → `[tool.pytest.ini_options]` (testpaths=["tests"], strict-markers) |
| Quick run command | `uv run pytest tests/test_audio_buffers.py -x` |
| Full suite command | `uv run pytest` |

### Phase Requirements → Test Map
| Test ID | Behavior | Test Type | Automated Command | File Exists? |
|---|---|---|---|---|
| RING-01 | Ring buffer wrap-around preserves last N samples correctly | unit | `uv run pytest tests/test_audio_buffers.py::test_wrap_preserves_recent -x` | ❌ Wave 0 |
| RING-02 | `push()` is zero-allocation after warm-up (tracemalloc) | unit | `uv run pytest tests/test_audio_buffers.py::test_audio_buffer_push_zero_alloc -x` | ❌ Wave 0 |
| RING-03 | Underlying array identity stable across 1000 pushes | unit | `uv run pytest tests/test_audio_buffers.py::test_audio_buffer_underlying_array_identity -x` | ❌ Wave 0 |
| RING-04 | Cold-start snapshot (filled < size) returns only real samples, no zeros from init | unit | `uv run pytest tests/test_audio_buffers.py::test_cold_start_snapshot -x` | ❌ Wave 0 |
| LEVELS-01 | EMA smoothing decays toward zero on silent input | unit | `uv run pytest tests/test_levels.py -x` | ❌ Wave 0 |
| RATE-01 | `assert_device_sample_rate` raises `SampleRateMismatchError` on mismatch (mocked device) | unit | `uv run pytest tests/test_audio_macos.py::test_sample_rate_mismatch -x` | ❌ Wave 0 |
| RATE-02 | `assert_device_sample_rate` passes silently when device matches expected | unit | `uv run pytest tests/test_audio_macos.py::test_sample_rate_match -x` | ❌ Wave 0 |
| FEAT-01 | `snapshot_features` returns the v4 dict shape (silent, rms, onsets_per_sec, sub_share, low_share, mid_share, high_share) | unit | `uv run pytest tests/test_features.py -x` | ❌ Wave 0 |
| REC-01 | `VoiceRecorder` writes input.wav with valid RIFF header | integration | `uv run pytest tests/test_recorder.py -x` | ❌ Wave 0 |
| SMOKE-01 | `AudioMacOS.open_capture()` opens against device index 2 (BlackHole) without raising — runs only if BlackHole present | smoke (skip on CI) | `uv run pytest tests/test_audio_macos_live.py -x -m macos_audio` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_audio_buffers.py tests/test_levels.py -x` (~2s — unit only)
- **Per wave merge:** `uv run pytest` (full suite — still all unit, ~5s)
- **Phase gate:** Full suite green + manual BlackHole smoke (`SMOKE-01`) on Kaan's machine before `/gsd-verify-work`.

### Wave 0 Gaps
- [ ] `tests/test_audio_buffers.py` — covers RING-01..04 + zero-alloc regression test
- [ ] `tests/test_levels.py` — covers LEVELS-01
- [ ] `tests/test_audio_macos.py` — covers RATE-01, RATE-02 (mocked sd.query_devices)
- [ ] `tests/test_features.py` — covers FEAT-01 (verbatim port of v4 dict shape)
- [ ] `tests/test_recorder.py` — covers REC-01
- [ ] `tests/test_audio_macos_live.py` — SMOKE-01, marked `@pytest.mark.macos_audio` for opt-in
- [ ] `tests/conftest.py` — shared fixtures (synthetic int16 sine generator at known RMS)
- [ ] `pytest-mock` install: `uv add --dev pytest-mock`
- [ ] Custom marker registration in `[tool.pytest.ini_options]`: add `markers = ["macos_audio: requires BlackHole 2ch present"]` to silence strict-markers warnings on opt-in tests

## Security Domain

**`security_enforcement`** is not explicitly set in `.planning/config.json` — treating as enabled per default.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---|---|---|
| V2 Authentication | no | Phase 2 has no auth surface (local audio I/O only) |
| V3 Session Management | no | No sessions |
| V4 Access Control | no | No remote access |
| V5 Input Validation | yes | Validate sample-rate parameter, validate device index bounds before `sd.query_devices(idx)` (raises `PortAudioError` on out-of-range — convert to a clearer error) |
| V6 Cryptography | no | No crypto in this phase |
| V7 Error Handling | yes | `SampleRateMismatchError` is the canonical example; all audio errors should be specific exceptions, never bare `Exception` |
| V8 Data Protection | yes | `VoiceRecorder` writes to `recordings/<timestamp>/` — directory should be `mode=0o700` (owner-only) to match Kaan's privacy posture in `~/CLAUDE.md` (private OZ/Hermes/local-AI HARD RULE). Recordings contain Kaan's voice + any speech in the room — sensitive by default. |
| V12 File / Resource | yes | Recording dir creation must be atomic (`mkdir -p` + chmod) before any writer opens; otherwise concurrent runs race on the same timestamp |

### Known Threat Patterns for sounddevice + macOS audio capture

| Pattern | STRIDE | Standard Mitigation |
|---|---|---|
| Path traversal in recording filename | Tampering | Generate timestamp filename internally; never accept caller-supplied filenames in Phase 2 |
| Recording-dir world-readable leaks Kaan's voice | Information Disclosure | `os.makedirs(rec_dir, mode=0o700, exist_ok=True)` + verify perms on existing dirs |
| Audio callback raises → audio thread dies silently → set continues with stale buffer | Denial of Service | sounddevice's `status` callback parameter exposes input/output overflow flags; log them via `VoiceRecorder.log_event` |
| BlackHole driver not installed → cryptic PortAudio error | Usability (security-adjacent) | `find_device("BlackHole", "input")` raises a clear "please install BlackHole 2ch" error before the user gets a stack trace |

## Sources

### Primary (HIGH confidence)
- `sounddevice` 0.5.5 docs (readthedocs PDF, dated 2026-03-02): https://python-sounddevice.readthedocs.io/ — Stream.samplerate docstring, query_devices return shape, check_input_settings semantics
- Live empirical test on Kaan's machine (2026-05-11) — BlackHole 2ch behavior verified
- Live `uv build --wheel` test on this project — hatchling recursive subpackage + underscore inclusion confirmed
- `python-sounddevice` source via `uv run python -c "help(sd.RawInputStream.samplerate)"` — authoritative docstring
- Project's `pyproject.toml` — hatchling config baseline, dependency pins

### Secondary (MEDIUM confidence)
- Hatch build docs: https://hatch.pypa.io/latest/config/build/ — `packages` option semantics (cross-referenced against empirical wheel build)
- Hatch wheel builder plugin docs: https://hatch.pypa.io/latest/plugins/builder/wheel/ — default file selection behavior
- uv dependency docs: https://docs.astral.sh/uv/concepts/projects/dependencies/ — `uv add --dev` syntax
- PyPI metadata for `dvg-ringbuffer` 1.1.0 (released 2024-06-22) and `numpy-ringbuffer` 0.2.2 (released 2022-06-28)

### Tertiary (LOW confidence — flagged for validation if it matters)
- CoreAudio `kAudioDevicePropertyNominalSampleRate` programmatic setter — referenced from MacAudioTools (Swift) and CamillaDSP docs, NOT verified from Python. Deferred to Phase 11 per CONTEXT.md, so LOW confidence here is acceptable.

## Metadata

**Confidence breakdown:**
- Q1 ring buffer pattern: HIGH — implementation is straightforward numpy + locks; both empirical test pattern and POC reference are solid
- Q2 sample-rate sanity check: HIGH — empirically verified on live BlackHole device on this machine
- Q3 hatchling/uv: HIGH — empirically verified by building the wheel and inspecting contents

**Research date:** 2026-05-11
**Valid until:** ~2026-07-11 (60 days — sounddevice and hatchling are both stable; uv moves faster but `uv add` syntax has been stable for >1 year)
