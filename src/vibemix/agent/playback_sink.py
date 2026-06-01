# SPDX-License-Identifier: Apache-2.0
"""PlaybackQueueAudioOutput — verbatim port of cohost_v4.py:1596-1640.

Bridges LiveKit's int16 PCM TTS frames back into Phase 2's PlaybackQueue (which
feeds the sounddevice output stream) AND VoiceRecorder.push_voice (which
appends to ``voice.wav`` for the audit trail).

One adjustment vs v4: v4:1624 references ``self._sample_rate`` (a private attr
on LiveKit 1.5.x's ``voice_io.AudioOutput`` parent class). In current LiveKit
the canonical attr is ``self.sample_rate`` (a property). Read the property —
fall back to OUTPUT_SR if both ``frame.sample_rate`` and the property happen
to be None.
"""

from __future__ import annotations

import os
import time

import numpy as np
from livekit import rtc
from livekit.agents.voice import io as voice_io

from vibemix.audio import OUTPUT_SR, PlaybackQueue, VoiceRecorder

# 2026-05-21 (Kaan: "sesini yuksege al") — software gain on the AI voice
# before it hits the speaker. Local MOSS speech can still get buried under
# the music passthrough, so multiply the int16 PCM with hard-clip protection.
# Env-tunable (VIBEMIX_VOICE_GAIN); 1.0 = bypass.
VOICE_GAIN: float = float(os.environ.get("VIBEMIX_VOICE_GAIN", "2.0"))


class PlaybackQueueAudioOutput(voice_io.AudioOutput):
    """Bridges LiveKit's TTS audio frames back into v2's PlaybackQueue (which
    feeds the existing sounddevice output stream). Forwards int16 PCM bytes
    and calls on_playback_finished on flush so AgentSession knows the segment
    drained."""

    def __init__(
        self,
        playback: PlaybackQueue,
        recorder: VoiceRecorder,
        sample_rate: int = OUTPUT_SR,
    ):
        super().__init__(
            label="dj-cohost.playback",
            capabilities=voice_io.AudioOutputCapabilities(pause=False),
            sample_rate=sample_rate,
        )
        self._playback = playback
        self._recorder = recorder
        self._segment_started_at: float | None = None
        self._segment_duration: float = 0.0

    async def capture_frame(self, frame: rtc.AudioFrame) -> None:
        await super().capture_frame(frame)
        if self._segment_started_at is None:
            self._segment_started_at = time.time()
            self.on_playback_started(created_at=self._segment_started_at)
        pcm = bytes(frame.data)
        if pcm:
            # Apply the AI-voice gain with int16 clip protection (speech
            # peaks are occasional, so mild clipping at >1.0 is inaudible).
            # voice.wav keeps the BOOSTED bytes so the audit matches what
            # was actually played.
            if VOICE_GAIN != 1.0:
                arr = np.frombuffer(pcm, dtype=np.int16).astype(np.float32)
                arr = np.clip(arr * VOICE_GAIN, -32768.0, 32767.0)
                pcm = arr.astype(np.int16).tobytes()
            self._playback.push(pcm)
            self._recorder.push_voice(pcm)
        # frame.duration is samples_per_channel / sample_rate; sum across frames
        self._segment_duration += frame.samples_per_channel / float(
            frame.sample_rate or self.sample_rate or OUTPUT_SR
        )

    def flush(self) -> None:
        super().flush()
        if self._segment_started_at is not None:
            self.on_playback_finished(
                playback_position=self._segment_duration,
                interrupted=False,
            )
        self._segment_started_at = None
        self._segment_duration = 0.0

    def clear_buffer(self) -> None:
        # PlaybackQueue is a simple ring; the v2 design assumed FIFO drain.
        # For interruption we'd reset the buffer here, but v4 currently runs
        # allow_interruptions=False so this is a no-op stub.
        pass
