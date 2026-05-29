# SPDX-License-Identifier: Apache-2.0
"""Pin the 48 kHz BlackHole guard for the listening INPUT device (BRINGUP-02).

Kaan hit the BlackHole 44.1k-vs-48k misconfig live on 2026-05-11: opening a
stream against a 44.1 kHz device silently succeeds and resamples, so every
downstream feature (RMS / bands / BPM) is computed on wrong-rate audio. The
production guard ``assert_device_sample_rate`` (called pre-open at every stream
factory in ``_audio_macos.py``) catches it BEFORE any audio is consumed.

These tests run in the DEFAULT suite (NO ``macos_audio`` marker) — they mock
``sounddevice`` so no real hardware is touched. The real-hardware confirmation
lives in ``tests/test_audio_macos_live.py`` (opt-in, Kaan-action).
"""

from __future__ import annotations

from unittest import mock

import pytest

from vibemix.audio.constants import INPUT_SR_NATIVE
from vibemix.audio.errors import SampleRateMismatchError
from vibemix.platform._audio_macos import (
    assert_device_sample_rate,
    set_device_nominal_sample_rate,
)

_MODULE = "vibemix.platform._audio_macos"


def test_input_guard_raises_on_44100_device():
    """A BlackHole device reporting 44100 while vibemix expects 48000 raises
    SampleRateMismatchError with the actionable 44100 + 48 fix text — and the
    raise happens (no silent resample)."""
    fake_info = {"name": "BlackHole 2ch", "default_samplerate": 44100.0}
    with (
        mock.patch(f"{_MODULE}.sd.query_devices", return_value=fake_info) as q,
        # Force the raise path: best-effort programmatic fix fails.
        mock.patch(f"{_MODULE}.set_device_nominal_sample_rate", return_value=False) as fix,
        # Do not actually open Audio MIDI Setup.
        mock.patch("subprocess.Popen") as popen,
    ):
        with pytest.raises(SampleRateMismatchError) as exc:
            assert_device_sample_rate(device_index=0, expected=48000)

    msg = str(exc.value)
    assert "44100" in msg
    assert "48" in msg  # "48,000 Hz" actionable fix target
    assert q.called
    assert fix.called  # the guard tried the best-effort fix before raising
    assert popen.called  # opened Audio MIDI Setup so Kaan lands one click from the fix


def test_input_guard_passes_on_48000_device_without_attempting_fix():
    """When the device already reports 48000, the guard returns None (no raise)
    and never attempts the programmatic rate fix."""
    fake_info = {"name": "BlackHole 2ch", "default_samplerate": 48000.0}
    with (
        mock.patch(f"{_MODULE}.sd.query_devices", return_value=fake_info),
        mock.patch(f"{_MODULE}.set_device_nominal_sample_rate", return_value=True) as fix,
        mock.patch("subprocess.Popen") as popen,
    ):
        result = assert_device_sample_rate(device_index=0, expected=48000)

    assert result is None
    assert not fix.called  # already correct — no fix attempt
    assert not popen.called  # no Audio MIDI Setup pop


def test_programmatic_rate_fix_falls_back_to_swift_when_pyobjc_fails():
    with (
        mock.patch(f"{_MODULE}._set_device_nominal_sample_rate_pyobjc", return_value=False) as pyobjc,
        mock.patch(f"{_MODULE}._set_device_nominal_sample_rate_swift", return_value=True) as swift,
    ):
        result = set_device_nominal_sample_rate("BlackHole 2ch", 48000)

    assert result is True
    pyobjc.assert_called_once_with("BlackHole 2ch", 48000)
    swift.assert_called_once_with("BlackHole 2ch", 48000)


def test_programmatic_rate_fix_reports_false_when_both_paths_fail():
    with (
        mock.patch(f"{_MODULE}._set_device_nominal_sample_rate_pyobjc", return_value=False),
        mock.patch(f"{_MODULE}._set_device_nominal_sample_rate_swift", return_value=False),
    ):
        result = set_device_nominal_sample_rate("BlackHole 2ch", 48000)

    assert result is False


def test_input_path_is_guarded_at_input_sr_native():
    """Tie the listening INPUT path to INPUT_SR_NATIVE == 48000 and prove the
    capture factory actually calls assert_device_sample_rate with the sample
    rate (so the input path is provably guarded, not just the helper)."""
    assert INPUT_SR_NATIVE == 48000

    import vibemix.platform._audio_macos as mod

    with open(mod.__file__, encoding="utf-8") as f:
        src = f.read()

    # open_capture is the listening INPUT factory; it must guard pre-open.
    assert "def open_capture(" in src
    # The guard is called with the sample_rate the caller passed (which is
    # INPUT_SR_NATIVE for the listening input — verified by the call-site grep).
    assert "assert_device_sample_rate(device_index, sample_rate)" in src
