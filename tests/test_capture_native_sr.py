# SPDX-License-Identifier: Apache-2.0
"""The master capture opens at the device's NATIVE rate (44.1k/48k/...) and
resamples to 16k internally — instead of forcing 48k and crashing a fresh user
whose BlackHole/loopback is at 44.1kHz (the most common rate). `_resolve_capture_
native_sr` reads the device rate already resolved by `describe_capture_input`
into the capture context, with a safe fallback for a missing/absurd value.
"""
from __future__ import annotations

from vibemix.__main__ import _resolve_capture_native_sr
from vibemix.audio.constants import INPUT_SR_NATIVE


def test_resolves_device_native_rate():
    assert _resolve_capture_native_sr({"sample_rate": 44100}) == 44100
    assert _resolve_capture_native_sr({"sample_rate": 48000}) == 48000


def test_accepts_common_pro_audio_rates():
    for sr in (44100, 48000, 88200, 96000, 176400, 192000):
        assert _resolve_capture_native_sr({"sample_rate": sr}) == sr


def test_falls_back_for_missing_or_absurd_rate():
    assert _resolve_capture_native_sr({}) == INPUT_SR_NATIVE
    assert _resolve_capture_native_sr(None) == INPUT_SR_NATIVE
    assert _resolve_capture_native_sr({"sample_rate": 0}) == INPUT_SR_NATIVE
    assert _resolve_capture_native_sr({"sample_rate": None}) == INPUT_SR_NATIVE
    assert _resolve_capture_native_sr({"sample_rate": 5}) == INPUT_SR_NATIVE  # absurd-low
    assert _resolve_capture_native_sr({"sample_rate": 10_000_000}) == INPUT_SR_NATIVE  # absurd-high
    assert _resolve_capture_native_sr({"sample_rate": "not-a-number"}) == INPUT_SR_NATIVE
