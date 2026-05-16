# SPDX-License-Identifier: Apache-2.0
"""Audio capture utility for the Gemini 3.1 Flash Live music spike.

Writes int16 PCM mono audio chunks to a wav file for offline analysis.
Pure stdlib (no extra deps) so the spike runs anywhere a regular vibemix
environment runs.

Default format = 16-bit PCM mono @ 24kHz, matching Gemini Live output.
The spike operator verifies the actual output rate on first real run and
adjusts the constructor if the format differs (see OPERATOR_NOTES in
``run_live_spike.py``).
"""

from __future__ import annotations

import wave
from pathlib import Path


class RecordingHarness:
    """Append-only wav writer for Gemini Live output audio.

    Usage::

        harness = RecordingHarness(Path("spikes/recordings/foo.wav"))
        harness.push_audio(pcm_bytes)
        ...
        harness.close()

    Thread safety: the underlying ``wave.Wave_write`` is not thread-safe.
    The spike script feeds frames from a single asyncio task, so no lock
    is needed in the common path. If a future caller pushes from multiple
    threads, wrap ``push_audio`` calls in an external lock.
    """

    def __init__(
        self,
        output_path: Path,
        sample_rate: int = 24_000,
        channels: int = 1,
        sample_width: int = 2,  # bytes — 2 = int16
    ) -> None:
        self.output_path = output_path
        self.sample_rate = sample_rate
        self.channels = channels
        self.sample_width = sample_width
        output_path.parent.mkdir(parents=True, exist_ok=True)
        self._wav = wave.open(str(output_path), "wb")
        self._wav.setnchannels(channels)
        self._wav.setsampwidth(sample_width)
        self._wav.setframerate(sample_rate)
        self._frames_written = 0
        self._closed = False

    def push_audio(self, pcm_bytes: bytes) -> None:
        """Append 16-bit PCM bytes. No-op after close()."""
        if self._closed:
            return
        if not pcm_bytes:
            return
        self._wav.writeframes(pcm_bytes)
        # writeframes accepts bytes regardless of frame alignment; count
        # frames assuming `sample_width * channels` bytes per frame.
        bytes_per_frame = self.sample_width * self.channels
        if bytes_per_frame:
            self._frames_written += len(pcm_bytes) // bytes_per_frame

    @property
    def frames_written(self) -> int:
        return self._frames_written

    @property
    def seconds_written(self) -> float:
        if not self.sample_rate:
            return 0.0
        return self._frames_written / float(self.sample_rate)

    def close(self) -> None:
        """Finalize wav header and close the underlying file."""
        if self._closed:
            return
        try:
            self._wav.close()
        finally:
            self._closed = True

    def __enter__(self) -> "RecordingHarness":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
