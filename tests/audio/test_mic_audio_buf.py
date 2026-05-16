# SPDX-License-Identifier: Apache-2.0
"""Plan 40-01 Task 1 — mic_audio_buf ring + resample-and-zero-fill callback.

Pins the new mic-as-2nd-Gemini-Part audio pipeline:

* ``MIC_AUDIO_PART_SECONDS / _RECENCY_S / _PRESENCE_RMS`` constants surface.
* ``_mic_callback_factory(mic, mic_audio_buf)`` extended signature: when
  ``mic_audio_buf`` is provided the callback resamples 48k→16k, zero-fills
  while AI talks, clips to int16, and pushes — preserving the v2.1 byte-
  identical path when ``mic_audio_buf`` is None (backward compat).
* Ring size = 12s × 16kHz = 192000 int16 samples.
* AudioBuffer zero-alloc invariant carries over (id(_buf) stable across pushes).

v4 reference (READ-ONLY POC): cohost_v4.py:2257 instantiation,
cohost_v4.py:2278-2296 callback body.
"""

from __future__ import annotations

import numpy as np
import pytest

from tests.audio.conftest import int16_sine
from vibemix.audio import (
    AudioBuffer,
    INPUT_SR_NATIVE,
    INPUT_SR_TARGET,
    Levels,
    MIC_GAIN,
    MIC_GAIN_AT_AI_TALK,
    MicBuffer,
)


# ---------- constant surface ----------


def test_mic_audio_part_constants_exported() -> None:
    """T1-Pre: the three new MIC_AUDIO_PART_* constants are imported from
    ``vibemix.audio`` (re-exported from constants.py)."""
    from vibemix.audio import (
        MIC_AUDIO_PART_PRESENCE_RMS,
        MIC_AUDIO_PART_RECENCY_S,
        MIC_AUDIO_PART_SECONDS,
    )

    # v4-baseline values per Plan 40-01 frontmatter:
    #   MIC_AUDIO_PART_SECONDS = 8.0  (snapshot width into Gemini Part 2)
    #   MIC_AUDIO_PART_RECENCY_S = 4.0  (KAAN_SPOKE-recent gate)
    #   MIC_AUDIO_PART_PRESENCE_RMS = 0.005  (silence floor)
    assert MIC_AUDIO_PART_SECONDS == 8.0
    assert MIC_AUDIO_PART_RECENCY_S == 4.0
    assert MIC_AUDIO_PART_PRESENCE_RMS == 0.005


# ---------- ring behaviour ----------


def test_t1_push_and_snapshot_16khz_sine() -> None:
    """T1: pushing 1s of 16kHz int16 sine to mic_audio_buf produces a
    snapshot_wav with non-zero RMS at 16kHz."""
    from vibemix.audio import snapshot_wav

    mic_audio_buf = AudioBuffer(seconds=12.0, sr=INPUT_SR_TARGET)
    samples = int16_sine(freq_hz=440.0, duration_sec=1.0, sample_rate=INPUT_SR_TARGET)
    mic_audio_buf.push(samples)

    wav = snapshot_wav(mic_audio_buf, seconds=1.0)
    # RIFF header
    assert wav[:4] == b"RIFF"
    # Sample-rate field is at bytes 24-28 (little-endian uint32) inside fmt chunk
    sr_field = int.from_bytes(wav[24:28], "little")
    assert sr_field == INPUT_SR_TARGET
    # Snapshot non-empty + non-zero energy
    snap = mic_audio_buf.snapshot(INPUT_SR_TARGET)
    assert snap.size == INPUT_SR_TARGET
    rms = float(np.sqrt(np.mean(snap.astype(np.float32) ** 2)))
    assert rms > 100.0  # int16-domain RMS for a half-amplitude sine ≈ 11580


def test_t2_callback_resamples_48k_to_16k() -> None:
    """T2: driving _mic_callback_factory with 1s of 48kHz indata pushes
    16000 samples (not 48000) into the mic_audio_buf — resample applied."""
    from vibemix.__main__ import _mic_callback_factory

    levels = Levels()
    mic = MicBuffer(gain=MIC_GAIN, levels=levels)
    mic_audio_buf = AudioBuffer(seconds=12.0, sr=INPUT_SR_TARGET)

    callback = _mic_callback_factory(mic, mic_audio_buf)
    # Synthesize 1s of 48kHz mono float32 sine, shaped (N, 1) like sounddevice
    n_native = INPUT_SR_NATIVE
    t = np.arange(n_native, dtype=np.float32) / INPUT_SR_NATIVE
    indata = (0.5 * np.sin(2.0 * np.pi * 440.0 * t)).reshape(-1, 1)

    callback(indata, n_native, None, None)

    # 48k → 16k via resample_poly: 1s @ 48kHz becomes 1s @ 16kHz = 16000 samples
    assert mic_audio_buf._filled == INPUT_SR_TARGET
    snap = mic_audio_buf.snapshot(INPUT_SR_TARGET)
    assert snap.size == INPUT_SR_TARGET
    # Non-zero energy preserved through the resample
    rms = float(np.sqrt(np.mean(snap.astype(np.float32) ** 2)))
    assert rms > 100.0


def test_t3_zero_fill_during_ai_talk(monkeypatch: pytest.MonkeyPatch) -> None:
    """T3: when mic._current_gain() returns MIC_GAIN_AT_AI_TALK (AI is
    talking), the pushed energy ends up as silence in the ring — load-
    bearing IP per RESEARCH Pitfall 1 (self-loop prevention)."""
    from vibemix.__main__ import _mic_callback_factory

    levels = Levels()
    mic = MicBuffer(gain=MIC_GAIN, levels=levels)
    mic_audio_buf = AudioBuffer(seconds=12.0, sr=INPUT_SR_TARGET)

    # Monkeypatch the gain method to simulate "AI is talking right now".
    monkeypatch.setattr(mic, "_current_gain", lambda: MIC_GAIN_AT_AI_TALK)

    callback = _mic_callback_factory(mic, mic_audio_buf)
    n_native = INPUT_SR_NATIVE
    t = np.arange(n_native, dtype=np.float32) / INPUT_SR_NATIVE
    indata = (0.5 * np.sin(2.0 * np.pi * 440.0 * t)).reshape(-1, 1)

    callback(indata, n_native, None, None)

    # Ring filled (resample still runs), but all samples must be zero.
    assert mic_audio_buf._filled == INPUT_SR_TARGET
    snap = mic_audio_buf.snapshot(INPUT_SR_TARGET)
    assert int(np.abs(snap).max()) == 0


def test_t4_ring_size_192000() -> None:
    """T4: AudioBuffer(seconds=12.0, sr=16000) reserves exactly 192000
    int16 samples — matches v4:2257 mic_audio_buf shape."""
    mic_audio_buf = AudioBuffer(seconds=12.0, sr=INPUT_SR_TARGET)
    assert mic_audio_buf._size == int(12.0 * INPUT_SR_TARGET)
    assert mic_audio_buf._size == 192000


def test_t5_zero_alloc_invariant_across_pushes() -> None:
    """T5: id(mic_audio_buf._buf) is stable across 100 pushes — the
    pre-allocated ring is never reallocated (carries over the AudioBuffer
    invariant; np.concatenate-per-callback regression remains fixed)."""
    mic_audio_buf = AudioBuffer(seconds=12.0, sr=INPUT_SR_TARGET)
    initial_id = id(mic_audio_buf._buf)
    chunk = int16_sine(
        freq_hz=440.0, duration_sec=0.01, sample_rate=INPUT_SR_TARGET
    )  # 160 samples
    for _ in range(100):
        mic_audio_buf.push(chunk)
    assert id(mic_audio_buf._buf) == initial_id


# ---------- backward compat ----------


def test_callback_backward_compat_when_mic_audio_buf_none() -> None:
    """The v2.1 byte-identical path is preserved when mic_audio_buf=None:
    only mic.push runs, no resample, no second-buffer write."""
    from vibemix.__main__ import _mic_callback_factory

    levels = Levels()
    mic = MicBuffer(gain=MIC_GAIN, levels=levels)

    callback = _mic_callback_factory(mic)  # second arg defaults to None
    n_native = INPUT_SR_NATIVE
    t = np.arange(n_native, dtype=np.float32) / INPUT_SR_NATIVE
    indata = (0.5 * np.sin(2.0 * np.pi * 440.0 * t)).reshape(-1, 1)
    # MUST not raise even though no mic_audio_buf was provided.
    callback(indata, n_native, None, None)
    # Mic buffer received the natural 48kHz push.
    assert mic._filled > 0
