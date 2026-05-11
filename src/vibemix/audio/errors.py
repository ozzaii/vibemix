# SPDX-License-Identifier: Apache-2.0
"""Typed exceptions for the vibemix.audio package."""

from __future__ import annotations


class SampleRateMismatchError(Exception):
    """Raised when the OS audio device is not configured at the expected rate.

    On macOS, BlackHole 2ch's nominal sample rate is set via Audio MIDI Setup
    (not by sounddevice / PortAudio). If the device is at 44.1kHz but vibemix
    expects 48kHz, opening a stream silently succeeds and resamples — which is
    exactly the failure mode that bit Kaan on 2026-05-11.

    Plan 04's `_audio_macos.AudioMacOS` raises this from `assert_device_sample_rate`
    (pre-open guard against `sd.query_devices(idx)['default_samplerate']`) AND from
    the post-open `Stream.samplerate` check. The error message includes the
    Audio MIDI Setup fix steps + Drift Correction note.

    Lives in vibemix.audio.errors (not platform/) so Phase 7's Windows port
    (_audio_windows.py via PyAudioWPatch) reuses the same exception type — the
    WASAPI equivalent of the BlackHole misconfig is the same shape of bug.
    """
