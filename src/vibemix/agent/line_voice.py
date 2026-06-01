# SPDX-License-Identifier: Apache-2.0
"""One-shot synth seam — drive the existing MOSS live TTS chain for one line.

The live co-host voice is a LiveKit ``tts.FallbackAdapter`` with one provider:
local ``MossLocalTTS``. The viral auto-mix demo has no room, but the reel is
deterministic: every reaction line is known before audio starts. So instead of
rebuilding a voice, this drives that exact adapter's ``.synthesize(text)`` once
per line and assembles the int16 frames into a finished stereo float32 buffer the
demo mixes over the deck.

``synthesize_line`` is the seam (tested with a fake adapter — no network, no key);
``build_default_line_adapter`` is the live wiring. Same chain, same MOSS voice.
"""
from __future__ import annotations

import numpy as np

# A non-zero default keeps downstream resample/duration math safe even if a stream
# yields no frames.
_DEFAULT_SR: int = 24000


def int16_frames_to_stereo(arrays: list[np.ndarray], num_channels: int) -> np.ndarray:
    """Concatenate int16 PCM chunks → contiguous ``(N, 2)`` float32 in [-1, 1].

    Mono is duplicated to both channels; interleaved stereo is de-interleaved. An
    empty input yields a zero-length stereo buffer (the honest no-audio case).
    """
    if not arrays:
        return np.zeros((0, 2), dtype=np.float32)
    pcm = np.concatenate([np.asarray(a, dtype=np.int16).reshape(-1) for a in arrays])
    audio = pcm.astype(np.float32) / 32768.0
    if num_channels >= 2:
        wide = audio.reshape(-1, num_channels)[:, :2]
        return np.ascontiguousarray(wide, dtype=np.float32)
    return np.ascontiguousarray(np.stack([audio, audio], axis=1), dtype=np.float32)


async def synthesize_line(adapter, text: str) -> tuple[np.ndarray, int]:
    """Drive ``adapter.synthesize(text)`` to completion → ``(stereo float32, sr)``.

    Iterates the LiveKit ``ChunkedStream`` (each event's ``.frame`` carries int16
    ``.data`` + ``.sample_rate`` + ``.num_channels``), collects the PCM, and always
    closes the stream. Reusing the live adapter means the demo speaks in the live
    co-host's own voice.
    """
    arrays: list[np.ndarray] = []
    sr = _DEFAULT_SR
    num_channels = 1
    stream = adapter.synthesize(text)
    try:
        async for ev in stream:
            frame = ev.frame
            sr = int(getattr(frame, "sample_rate", sr) or sr)
            num_channels = int(getattr(frame, "num_channels", num_channels) or num_channels)
            arrays.append(np.frombuffer(bytes(frame.data), dtype=np.int16))
    finally:
        aclose = getattr(stream, "aclose", None)
        if aclose is not None:
            try:
                await aclose()
            except Exception:  # pragma: no cover — best-effort stream cleanup
                pass
    return int16_frames_to_stereo(arrays, num_channels), sr


def build_default_line_adapter():
    """Build the live MOSS-only TTS FallbackAdapter from local model state."""

    from vibemix.agent.tts_chain import build_tts_chain

    return build_tts_chain(mode="direct")
