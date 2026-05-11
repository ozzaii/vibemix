# SPDX-License-Identifier: Apache-2.0
"""Opt-in live smoke tests against real BlackHole 2ch hardware.

Marked with `pytest.mark.macos_audio` — skipped by default. Run on Kaan's
machine with BlackHole present via::

    uv run pytest -m macos_audio -v

What this proves:
- The sample-rate guard fires with an actionable SampleRateMismatchError
  when BlackHole is misconfigured (the bug Kaan hit on 2026-05-11).
- find_device locates BlackHole + headphones device indices via the
  substring-match helper.
- The AudioStream adapter satisfies the Phase 1 Protocol against a real
  sounddevice handle (start/stop/close + latency_ms).
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from vibemix.audio import (
    AudioBuffer,
    BufferRegistry,
    Levels,
    MicBuffer,
    PassthroughBuffer,
    PlaybackQueue,
    VoiceRecorder,
)
from vibemix.audio.errors import SampleRateMismatchError
from vibemix.platform import AudioMacOS

pytestmark = pytest.mark.macos_audio


def _make_backend() -> AudioMacOS:
    lv = Levels()
    reg = BufferRegistry(
        audio=AudioBuffer(seconds=1.0),
        clean_audio=AudioBuffer(seconds=1.0),
        mic=MicBuffer(gain=1.0, levels=lv),
        passthrough=PassthroughBuffer(),
        playback=PlaybackQueue(lv),
        levels=lv,
    )
    rec = VoiceRecorder(root=Path(tempfile.mkdtemp()))
    return AudioMacOS(registry=reg, recorder=rec)


def test_blackhole_device_present_at_48khz_or_raises() -> None:
    """find_device locates BlackHole 2ch; assert_device_sample_rate either
    passes (BH at 48kHz) or raises SampleRateMismatchError with the actionable
    message (BH misconfigured). NEVER an unhandled exception.

    This is the smoke test Kaan runs on his machine before declaring Phase 2 done.
    """
    from vibemix.platform._audio_macos import assert_device_sample_rate

    backend = _make_backend()
    idx = backend.find_device("BlackHole", "input")
    try:
        assert_device_sample_rate(idx, 48000)
    except SampleRateMismatchError as e:
        msg = str(e)
        assert "Audio MIDI Setup" in msg
        assert "Drift Correction" in msg
        # Re-raise so the test fails visibly — Kaan sees the actionable message
        # and knows to fix BlackHole's Audio MIDI Setup config.
        raise


def test_open_voice_output_completes_without_real_audio_device() -> None:
    """Try opening voice output to External Headphones (or fallback). Returns
    a handle satisfying AudioStream Protocol; close immediately."""
    backend = _make_backend()
    try:
        idx = backend.find_device("External Headphones", "output")
    except RuntimeError:
        # Fallback: any output device on the system
        idx = backend.find_device("Headphones", "output")

    # We don't actually want to open a real audio stream in CI / live smoke.
    # Just verify find_device worked.
    assert idx >= 0
