# SPDX-License-Identifier: Apache-2.0
"""EMA-smoothed RMS levels for music / AI voice / mic.

Verbatim port of cohost_v4.py:255-286 (byte-identical between v3 and v4 per
02-PATTERNS.md). Thread-safe — audio-thread writers + asyncio readers share a
single threading.Lock held only for the EMA arithmetic, not the RMS compute.
"""

from __future__ import annotations

import threading

import numpy as np


class Levels:
    """EMA-smoothed RMS levels for music / AI voice / mic.

    Thread-safety contract: audio-thread writers call update_music / update_voice
    / update_mic (potentially from multiple sounddevice callbacks); asyncio
    readers call snapshot(). The internal lock guards only the EMA arithmetic
    — the RMS compute runs lock-free on the caller's stack with the raw bytes
    / ndarray they own.

    EMA coefficients (verbatim from v4:267, 275, 280, 284) — see 02-PATTERNS.md
    "Levels" section:
        music  = music  * 0.6 + rms * 0.4   # faster — music level shifts mid-mix
        voice  = voice  * 0.5 + rms * 0.5   # 50/50 — needs to drop fast so mic-gate releases promptly
        mic    = mic    * 0.5 + rms * 0.5
        decay  = voice *= 0.7               # called from PlaybackQueue.pull() when empty
    """

    def __init__(self) -> None:
        self.music: float = 0.0
        self.voice: float = 0.0
        self.mic: float = 0.0
        self._lock = threading.Lock()

    def update_music(self, mono_int16: np.ndarray) -> None:
        """Update music EMA from int16 mono PCM. v4:264-267."""
        rms = float(np.sqrt(np.mean(mono_int16.astype(np.float32) ** 2))) / 32768.0
        with self._lock:
            self.music = self.music * 0.6 + rms * 0.4

    def update_voice(self, pcm_int16: bytes) -> None:
        """Update AI voice EMA from int16 mono PCM bytes. v4:269-275."""
        if not pcm_int16:
            return
        arr = np.frombuffer(pcm_int16, dtype=np.int16).astype(np.float32)
        rms = float(np.sqrt(np.mean(arr**2))) / 32768.0
        with self._lock:
            self.voice = self.voice * 0.5 + rms * 0.5

    def update_mic(self, samples_float: np.ndarray) -> None:
        """Update mic EMA from float32 samples (already in -1..1, no /32768 needed). v4:277-280."""
        rms = float(np.sqrt(np.mean(samples_float**2)))
        with self._lock:
            self.mic = self.mic * 0.5 + rms * 0.5

    def decay_voice(self) -> None:
        """Decay voice level by 0.7. Called from PlaybackQueue.pull on empty buffer. v4:282-284."""
        with self._lock:
            self.voice *= 0.7

    def snapshot(self) -> dict[str, float]:
        """Return a fresh dict of the current levels (safe to read concurrent with updates). v4:286-288."""
        with self._lock:
            return {"music": self.music, "voice": self.voice, "mic": self.mic}
