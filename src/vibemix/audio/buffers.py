# SPDX-License-Identifier: Apache-2.0
"""Pre-allocated ring buffers replacing the cohost_v4.py:300 + cohost_v4.py:462
``np.concatenate``-per-callback regression (PITFALLS.md P5).

Zero-alloc on push by design: writes via modular indexing into a fixed-size
pre-allocated ndarray. Snapshot/pull reads copy at most two contiguous slices
around the wrap point — one allocation per read, not per push.

At 100Hz callback rate x 4.5MB ring on v4's AudioBuffer (140s x 16kHz x int16),
v4 was allocating ~900MB/s of throwaway ndarrays on the audio thread. The fix
is structural — the ring never reallocates after construction; `_buf is _buf`
holds for the entire process lifetime. Plan 02's RING-02 (tracemalloc) +
RING-03 (object identity) tests pin this property in CI.
"""

from __future__ import annotations

import threading
import time

import numpy as np

from vibemix.audio.constants import (
    AI_TALK_THRESHOLD,
    INPUT_SR_TARGET,
    MIC_GAIN_AT_AI_TALK,
    MIC_HOLD_AFTER_AI_MS,
)
from vibemix.audio.levels import Levels


class AudioBuffer:
    """Pre-allocated rolling int16 PCM ring at INPUT_SR_TARGET (16kHz default).

    Zero-alloc on push: modular write-pointer into a fixed-size ndarray.
    Snapshot reads copy the last N samples into a fresh contiguous output
    array via at most two numpy slices (the wrap-around).

    Fixes np.concatenate-per-callback regression at cohost_v4.py:300.

    The v4 dual-buffer pattern (`audio_buf` for gain-boosted state features +
    `clean_audio_buf` for natural-level LLM Part snapshots, both at v4:1880-1881)
    uses two AudioBuffer instances with different `seconds` — same class.
    """

    def __init__(self, seconds: float = 140.0, sr: int = INPUT_SR_TARGET) -> None:
        self._sr = sr
        self._size = int(sr * seconds)
        # Pre-allocated, NEVER reallocated. id(self._buf) is stable for life.
        self._buf = np.zeros(self._size, dtype=np.int16)
        self._write = 0  # next write index (modular)
        self._filled = 0  # total samples ever written, capped at self._size
        self._lock = threading.Lock()

    def push(self, pcm_int16: np.ndarray) -> None:
        """O(n) memcpy into the ring at the current write pointer. Zero alloc.

        Pathological branch: if n >= size, only the tail of the input fits;
        overwrite the ring entirely and reset write/filled.
        """
        n = pcm_int16.size
        if n == 0:
            return
        if n >= self._size:
            # Caller pushed more than the ring holds — defensive, shouldn't
            # happen in practice (sounddevice blocksize ≤ 1024 frames).
            with self._lock:
                self._buf[:] = pcm_int16[-self._size :]
                self._write = 0
                self._filled = self._size
            return
        with self._lock:
            end = self._write + n
            if end <= self._size:
                self._buf[self._write : end] = pcm_int16
            else:
                # Wrap: split into tail + head.
                first = self._size - self._write
                self._buf[self._write :] = pcm_int16[:first]
                self._buf[: n - first] = pcm_int16[first:]
            self._write = (self._write + n) % self._size
            self._filled = min(self._filled + n, self._size)

    def snapshot(self, n_samples: int, out: np.ndarray | None = None) -> np.ndarray:
        """Copy the most recent n_samples into a fresh contiguous ndarray.

        If `out` is provided, it must have size == n (after min(n, filled));
        callers can reuse a pre-allocated buffer to avoid per-call allocation
        on high-frequency read paths (Phase 3 state_refresh_loop at ~10Hz —
        RESEARCH.md Pitfall 1).

        Returns an ndarray of size `min(n_samples, _filled)` — cold-start
        snapshots only contain real pushed samples, NOT the zero-init prefix.
        """
        with self._lock:
            n = min(n_samples, self._filled)
            if n == 0:
                return np.zeros(0, dtype=np.int16) if out is None else out[:0]
            start = (self._write - n) % self._size
            if start + n <= self._size:
                # Contiguous: single slice copy.
                if out is None:
                    return self._buf[start : start + n].copy()
                if out.size != n:
                    raise ValueError(f"out buffer size {out.size} != requested {n}")
                out[:] = self._buf[start : start + n]
                return out
            # Wrap: tail + head.
            first = self._size - start
            if out is None:
                result = np.empty(n, dtype=np.int16)
            else:
                if out.size != n:
                    raise ValueError(f"out buffer size {out.size} != requested {n}")
                result = out
            result[:first] = self._buf[start:]
            result[first:] = self._buf[: n - first]
            return result


class MicBuffer:
    """Pre-allocated mic ring at 48kHz float32 mono (200ms = 9600 samples).

    Verbatim port of cohost_v4.py:439-477 with the np.concatenate bug at
    v4:462 fixed. `_current_gain` is the LOAD-BEARING feedback-suppression
    IP — mic mutes the instant AI audio enters PlaybackQueue (via
    levels.voice), holds mute for MIC_HOLD_AFTER_AI_MS after AI silence to
    catch tails. This pair of side effects with PlaybackQueue is what makes
    real-time mic-gating work without a separate scheduler.

    Push/pull use distinct write/read pointers. Underflow zero-pads inline
    (PATTERNS.md §7 — picks the v4 PlaybackQueue policy over the v4
    PassthroughBuffer-returns-empty inconsistency).
    """

    MAX_FRAMES = 48000 * 200 // 1000  # 9600 — verbatim v4:442

    def __init__(self, gain: float, levels: Levels) -> None:
        self.base_gain = gain
        self._levels = levels
        self._buf = np.zeros(self.MAX_FRAMES, dtype=np.float32)
        self._write = 0
        self._read = 0
        self._filled = 0
        self._lock = threading.Lock()
        self._last_ai_active = 0.0

    def _current_gain(self) -> float:
        """LOAD-BEARING feedback-suppression. Verbatim port of v4:449-457.

        If levels.voice > AI_TALK_THRESHOLD → mute (record timestamp).
        Else if within MIC_HOLD_AFTER_AI_MS of last AI-active → still mute.
        Else return base_gain.
        """
        ai = self._levels.voice
        now = time.time()
        if ai > AI_TALK_THRESHOLD:
            self._last_ai_active = now
            return MIC_GAIN_AT_AI_TALK
        if now - self._last_ai_active < MIC_HOLD_AFTER_AI_MS / 1000:
            return MIC_GAIN_AT_AI_TALK
        return self.base_gain

    def push(self, samples: np.ndarray) -> None:
        """Update mic level (gain-adjusted) THEN ring-write. Zero alloc.

        Levels.update_mic acquires its own lock — must run before we grab
        ours to avoid any (theoretical) deadlock with snapshot readers.
        """
        # Levels write OUTSIDE our lock (Levels has its own).
        self._levels.update_mic(samples * self._current_gain())
        n = samples.size
        if n == 0:
            return
        if n >= self.MAX_FRAMES:
            with self._lock:
                self._buf[:] = samples[-self.MAX_FRAMES :]
                self._write = 0
                self._read = 0
                self._filled = self.MAX_FRAMES
            return
        with self._lock:
            end = self._write + n
            if end <= self.MAX_FRAMES:
                self._buf[self._write : end] = samples
            else:
                first = self.MAX_FRAMES - self._write
                self._buf[self._write :] = samples[:first]
                self._buf[: n - first] = samples[first:]
            self._write = (self._write + n) % self.MAX_FRAMES
            self._filled = min(self._filled + n, self.MAX_FRAMES)

    def pull(self, n_samples: int) -> np.ndarray:
        """Consume n_samples from the read pointer. Zero-pad inline on underflow.

        Multiplies output by `_current_gain()` so AI-talk windows produce
        silence (matches v4:466-477).
        """
        gain = self._current_gain()
        out = np.zeros(n_samples, dtype=np.float32)
        with self._lock:
            available = self._filled
            take = min(n_samples, available)
            if take > 0:
                start = self._read % self.MAX_FRAMES
                if start + take <= self.MAX_FRAMES:
                    out[:take] = self._buf[start : start + take]
                else:
                    first = self.MAX_FRAMES - start
                    out[:first] = self._buf[start:]
                    out[first:take] = self._buf[: take - first]
                self._read = (self._read + take) % self.MAX_FRAMES
                self._filled -= take
        return out * gain


class PassthroughBuffer:
    """djay → speakers stereo passthrough byte ring.

    Storage: ``bytearray`` (NOT ndarray) — passthrough is end-to-end raw
    bytes (no math, no resample, no dtype conversion). The
    ``np.concatenate`` bug doesn't exist here, but PATTERNS.md §4 lifts
    verbatim with the drop-half-on-overflow policy intact (v4:487-492).

    Underflow zero-pads inline per PATTERNS.md §7 (drops v4's b"" return
    inconsistency between PassthroughBuffer and PlaybackQueue — callers
    never have to branch on length).
    """

    MAX_BYTES = 48000 * 2 * 4 // 2  # 192000 — 500ms @ 48kHz stereo float32 (verbatim v4:483)

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._buf = bytearray()

    def push(self, b: bytes) -> None:
        """Extend the ring; drop to 50% on overflow (verbatim v4:487-492)."""
        with self._lock:
            self._buf.extend(b)
            if len(self._buf) > self.MAX_BYTES:
                drop = len(self._buf) - self.MAX_BYTES // 2
                del self._buf[:drop]

    def pull(self, n_bytes: int) -> bytes:
        """Return n_bytes, zero-padding on underflow (PATTERNS.md §7).

        Diverges from cohost_v4.py:494-500 which returned b"" on underflow;
        zero-pad-inline matches PlaybackQueue.pull and eliminates the
        v4 inconsistency.
        """
        with self._lock:
            if len(self._buf) < n_bytes:
                chunk = bytes(self._buf)
                self._buf.clear()
                return chunk + b"\x00" * (n_bytes - len(chunk))
            chunk = bytes(self._buf[:n_bytes])
            del self._buf[:n_bytes]
            return chunk


class PlaybackQueue:
    """AI voice output queue. Verbatim port of cohost_v4.py:503-523.

    PUSH triggers levels.update_voice → mic-gate engages immediately;
    empty PULL triggers levels.decay_voice → mic-gate releases promptly.
    This pair of side effects on Levels is the LOAD-BEARING
    feedback-suppression IP that makes real-time mic-gating work.

    No MAX cap (per PATTERNS.md §5 — AI talks in short bursts; sustained
    unbounded growth requires an upstream bug e.g. output stream stopped
    consuming).
    """

    def __init__(self, levels: Levels) -> None:
        self._buffer = bytearray()
        self._lock = threading.Lock()
        self._levels = levels

    def push(self, pcm: bytes) -> None:
        """Extend the ring + update voice level OUTSIDE our lock.

        Levels.update_voice has its own lock. The v4 ordering (extend
        under our lock, then update_voice without it) is preserved so
        the mic-gate sees the level update within one callback (v4:509-512).
        """
        with self._lock:
            self._buffer.extend(pcm)
        self._levels.update_voice(pcm)

    def pull(self, n_bytes: int) -> bytes:
        """Return n_bytes; if buffer empty, call levels.decay_voice (verbatim v4:516-525).

        Zero-pads on partial-fill (caller never branches on length).
        """
        with self._lock:
            if not self._buffer:
                self._levels.decay_voice()
                return b"\x00" * n_bytes
            chunk = bytes(self._buffer[:n_bytes])
            del self._buffer[:n_bytes]
            if len(chunk) < n_bytes:
                chunk += b"\x00" * (n_bytes - len(chunk))
            return chunk
