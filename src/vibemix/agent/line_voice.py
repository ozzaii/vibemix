# SPDX-License-Identifier: Apache-2.0
"""One-shot synth seam — drive the EXISTING live TTS chain for a single line.

The live co-host voice is a LiveKit ``tts.FallbackAdapter`` (Cartesia Sonic →
Gemini native ``Achird`` → OpenRouter standby) built in ``agent.tts_chain`` for a
streaming room. The viral auto-mix demo has no room, but the reel is deterministic:
every reaction line is known before audio starts. So instead of rebuilding a voice,
this drives that exact adapter's ``.synthesize(text)`` once per line and assembles
the int16 frames into a finished stereo float32 buffer the demo mixes over the deck.

``synthesize_line`` is the seam (tested with a fake adapter — no network, no key);
``build_default_line_adapter`` is the live wiring (Cartesia needs a loop-bound HTTP
session, so build it inside a running event loop). Same chain, same Achird voice.
"""
from __future__ import annotations

import numpy as np

# Gemini native TTS and Cartesia Sonic both emit 24 kHz PCM; a non-zero default keeps
# downstream resample/duration math safe even if a stream yields no frames.
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
    """Build the live TTS FallbackAdapter from env (Cartesia → Gemini → OpenRouter).

    Call this INSIDE a running asyncio loop — the Cartesia plugin binds an aiohttp
    session to the loop (see ``tts_chain._live_http_session``). Raises if no Gemini
    key is configured (the chain's required fallback).
    """
    import os

    from vibemix.agent.tts_chain import build_tts_chain

    gemini_key = os.environ.get("GEMINI_API_KEY")
    if not gemini_key:
        raise RuntimeError("GEMINI_API_KEY required to build the live voice chain")
    return build_tts_chain(
        gemini_api_key=gemini_key,
        cartesia_api_key=os.environ.get("CARTESIA_API_KEY") or None,
        mode="direct",
    )
