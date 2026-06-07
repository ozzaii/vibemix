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
from math import gcd

import numpy as np
from scipy import signal
from livekit import rtc
from livekit.agents.voice import io as voice_io

from vibemix.audio import INPUT_SR_NATIVE, OUTPUT_SR, PlaybackQueue, VoiceRecorder

# 2026-05-21 (Kaan: "sesini yuksege al") — software gain on the AI voice
# before it hits the speaker. Local co-host speech can still get buried under
# the music passthrough, so multiply the int16 PCM with hard-clip protection.
# Env-tunable (VIBEMIX_VOICE_GAIN); 1.0 = bypass.
VOICE_GAIN: float = float(os.environ.get("VIBEMIX_VOICE_GAIN", "2.0"))


def _voice_playback_speed() -> float:
    raw = os.environ.get("VIBEMIX_VOICE_PLAYBACK_SPEED", "1.0")
    try:
        speed = float(raw)
    except (TypeError, ValueError):
        return 1.0
    if speed < 0.75 or speed > 1.5:
        return 1.0
    return speed


def _wrap_phase(angle: np.ndarray) -> np.ndarray:
    return angle - (2.0 * np.pi) * np.round(angle / (2.0 * np.pi))


def _time_stretch_int16_mono(pcm: bytes, *, speed: float, sample_rate: int) -> bytes:
    """Pitch-preserving time stretch for complete mono int16 speech segments."""
    if not pcm or abs(speed - 1.0) < 0.01:
        return pcm
    samples = np.frombuffer(pcm, dtype=np.int16)
    if samples.size < 2048:
        return pcm

    x = samples.astype(np.float32) / 32768.0
    n_fft = 1024
    hop = 256
    _, _, spec = signal.stft(
        x,
        fs=sample_rate,
        window="hann",
        nperseg=n_fft,
        noverlap=n_fft - hop,
        boundary="zeros",
        padded=True,
    )
    if spec.shape[1] < 2:
        return pcm

    time_steps = np.arange(0.0, spec.shape[1] - 1, speed, dtype=np.float64)
    if time_steps.size < 2:
        return pcm

    omega = (2.0 * np.pi * hop * np.arange(spec.shape[0], dtype=np.float32)) / float(n_fft)
    phase_acc = np.angle(spec[:, 0]).astype(np.float32)
    out = np.empty((spec.shape[0], time_steps.size), dtype=np.complex64)

    for out_idx, step in enumerate(time_steps):
        left = int(step)
        frac = float(step - left)
        right = min(left + 1, spec.shape[1] - 1)
        left_col = spec[:, left]
        right_col = spec[:, right]
        mag = (1.0 - frac) * np.abs(left_col) + frac * np.abs(right_col)
        phase_delta = np.angle(right_col) - np.angle(left_col) - omega
        phase_acc = phase_acc + omega + _wrap_phase(phase_delta)
        out[:, out_idx] = mag * np.exp(1j * phase_acc)

    _, stretched = signal.istft(
        out,
        fs=sample_rate,
        window="hann",
        nperseg=n_fft,
        noverlap=n_fft - hop,
        input_onesided=True,
        boundary=True,
    )
    target = max(1, int(round(samples.size / speed)))
    if stretched.size < target:
        stretched = np.pad(stretched, (0, target - stretched.size))
    stretched = stretched[:target]
    return np.clip(stretched * 32768.0, -32768.0, 32767.0).astype(np.int16).tobytes()


def _resample_int16_mono_pcm(pcm: bytes, *, source_sr: int, target_sr: int) -> bytes:
    """Resample mono int16 PCM bytes while preserving speech duration."""
    if not pcm or source_sr <= 0 or target_sr <= 0 or source_sr == target_sr:
        return pcm
    samples = np.frombuffer(pcm, dtype=np.int16)
    if samples.size < 2:
        return pcm
    common = gcd(source_sr, target_sr)
    up = target_sr // common
    down = source_sr // common
    x = samples.astype(np.float32) / 32768.0
    y = signal.resample_poly(x, up, down)
    return np.clip(y * 32768.0, -32768.0, 32767.0).astype(np.int16).tobytes()


class PlaybackQueueAudioOutput(voice_io.AudioOutput):
    """Bridges LiveKit's TTS audio frames back into v2's PlaybackQueue (which
    feeds the existing sounddevice output stream). Forwards int16 PCM bytes
    and calls on_playback_finished on flush so AgentSession knows the segment
    drained."""

    def __init__(
        self,
        playback: PlaybackQueue,
        recorder: VoiceRecorder,
        sample_rate: int = INPUT_SR_NATIVE,
        buffer_segments: bool = False,
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
        self._buffer_segments = buffer_segments
        self._segment_pcm = bytearray()
        self._segment_started_emitted = False
        self._segment_meta: dict[str, int] | None = None
        self._segment_playback_speed = _voice_playback_speed()

    def _mark_playback_started(self, *, created_at: float) -> None:
        self._segment_started_emitted = True
        self.on_playback_started(created_at=created_at)
        try:
            meta = self._segment_meta or {}
            self._recorder.log_event(
                "voice_playback_started",
                sample_rate=int(meta.get("sample_rate") or self.sample_rate or OUTPUT_SR),
                samples_per_channel=int(meta.get("samples_per_channel") or 0),
                channels=int(meta.get("channels") or 1),
            )
        except Exception:
            pass

    async def capture_frame(self, frame: rtc.AudioFrame) -> None:
        await super().capture_frame(frame)
        if self._segment_started_at is None:
            self._segment_started_at = time.time()
            source_sr = int(frame.sample_rate or self.sample_rate or OUTPUT_SR)
            target_sr = int(self.sample_rate or OUTPUT_SR)
            self._segment_meta = {
                "sample_rate": target_sr,
                "source_sample_rate": source_sr,
                "samples_per_channel": int(frame.samples_per_channel),
                "channels": int(getattr(frame, "num_channels", 1) or 1),
            }
            if not self._buffer_segments:
                self._mark_playback_started(created_at=self._segment_started_at)
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
            if self._buffer_segments:
                self._segment_pcm.extend(pcm)
            else:
                meta = self._segment_meta or {}
                source_sr = int(meta.get("source_sample_rate") or frame.sample_rate or OUTPUT_SR)
                target_sr = int(meta.get("sample_rate") or self.sample_rate or OUTPUT_SR)
                if source_sr != target_sr:
                    pcm = _resample_int16_mono_pcm(
                        pcm,
                        source_sr=source_sr,
                        target_sr=target_sr,
                    )
                    self._recorder.log_event(
                        "voice_playback_resample",
                        source_sr=source_sr,
                        target_sr=target_sr,
                        pcm_bytes=len(pcm),
                    )
                self._playback.push(pcm)
                self._recorder.push_voice(pcm)
        # frame.duration is samples_per_channel / sample_rate; sum across frames
        self._segment_duration += frame.samples_per_channel / float(
            frame.sample_rate or self.sample_rate or OUTPUT_SR
        )

    def flush(self) -> None:
        super().flush()
        if self._segment_started_at is not None:
            if self._buffer_segments and self._segment_pcm:
                if not self._segment_started_emitted:
                    self._mark_playback_started(created_at=time.time())
                pcm = bytes(self._segment_pcm)
                source_sr = int(
                    (self._segment_meta or {}).get("source_sample_rate")
                    or self.sample_rate
                    or OUTPUT_SR
                )
                target_sr = int(
                    (self._segment_meta or {}).get("sample_rate") or self.sample_rate or OUTPUT_SR
                )
                if source_sr != target_sr:
                    pcm = _resample_int16_mono_pcm(
                        pcm,
                        source_sr=source_sr,
                        target_sr=target_sr,
                    )
                    self._recorder.log_event(
                        "voice_playback_resample",
                        source_sr=source_sr,
                        target_sr=target_sr,
                        pcm_bytes=len(pcm),
                    )
                playback_speed = _voice_playback_speed()
                if abs(playback_speed - 1.0) >= 0.01:
                    try:
                        pcm = _time_stretch_int16_mono(
                            pcm,
                            speed=playback_speed,
                            sample_rate=target_sr,
                        )
                        self._segment_playback_speed = playback_speed
                        self._recorder.log_event(
                            "voice_playback_speed",
                            speed=playback_speed,
                            sample_rate=target_sr,
                            pcm_bytes=len(pcm),
                        )
                    except Exception as exc:
                        self._segment_playback_speed = 1.0
                        self._recorder.log_event(
                            "voice_playback_speed_error",
                            speed=playback_speed,
                            error=repr(exc),
                        )
                self._playback.push(pcm)
                self._recorder.push_voice(pcm)
            duration = self._segment_duration / max(self._segment_playback_speed, 0.01)
            self.on_playback_finished(
                playback_position=duration,
                interrupted=False,
            )
            try:
                self._recorder.log_event(
                    "voice_playback_finished",
                    playback_position_s=round(duration, 3),
                    interrupted=False,
                )
            except Exception:
                pass
        self._segment_started_at = None
        self._segment_duration = 0.0
        self._segment_pcm.clear()
        self._segment_started_emitted = False
        self._segment_meta = None
        self._segment_playback_speed = _voice_playback_speed()

    def clear_buffer(self) -> None:
        # PlaybackQueue is a simple ring; the v2 design assumed FIFO drain.
        # For interruption we'd reset the buffer here, but v4 currently runs
        # allow_interruptions=False so this is a no-op stub.
        self._segment_pcm.clear()
        pass
