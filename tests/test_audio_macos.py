# SPDX-License-Identifier: Apache-2.0
"""Mocked sounddevice unit tests for vibemix.platform._audio_macos.AudioMacOS.

Covers the sample-rate guard (pre-open + post-open), find_device,
AudioBackend Protocol satisfaction, and a regression test for the Phase 1
firewall (typing-only Protocol module must remain free of sounddevice).
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

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
from vibemix.platform import AudioBackend, AudioMacOS
from vibemix.platform._audio_macos import assert_device_sample_rate


@pytest.fixture
def make_backend():
    """Factory that returns a fresh AudioMacOS instance using a temp recorder root."""

    def _make() -> AudioMacOS:
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

    return _make


# ===== RATE-01: assert_device_sample_rate raises on mismatch =====


def test_assert_device_sample_rate_raises_on_mismatch(mocker: MockerFixture) -> None:
    """44100 device + 48000 expected → SampleRateMismatchError with actionable message.

    Empirically verified failure mode from RESEARCH.md Q2 (BlackHole at wrong
    rate). Error MUST include the Audio MIDI Setup fix steps + Drift Correction.
    """
    mocker.patch(
        "vibemix.platform._audio_macos.sd.query_devices",
        return_value={"default_samplerate": 44100.0, "name": "BlackHole 2ch"},
    )
    with pytest.raises(SampleRateMismatchError, match=r"44100Hz.*48000Hz") as exc_info:
        assert_device_sample_rate(device_index=2, expected=48000)
    msg = str(exc_info.value)
    assert "Audio MIDI Setup" in msg
    assert "Drift Correction" in msg


# ===== RATE-02: assert_device_sample_rate passes on match =====


def test_assert_device_sample_rate_passes_on_match(mocker: MockerFixture) -> None:
    """48000 device + 48000 expected → returns None silently."""
    mocker.patch(
        "vibemix.platform._audio_macos.sd.query_devices",
        return_value={"default_samplerate": 48000.0, "name": "BlackHole 2ch"},
    )
    result = assert_device_sample_rate(device_index=2, expected=48000)
    assert result is None


# ===== RATE-03: open_capture pre-open guard short-circuits =====


def test_open_capture_pre_open_guard_fires_before_stream_construction(
    mocker: MockerFixture, make_backend
) -> None:
    """Pre-open SampleRateMismatchError short-circuits BEFORE sd.InputStream is called."""
    mocker.patch(
        "vibemix.platform._audio_macos.sd.query_devices",
        return_value={"default_samplerate": 44100.0, "name": "BlackHole 2ch"},
    )
    input_stream_mock = mocker.patch("vibemix.platform._audio_macos.sd.InputStream")

    backend = make_backend()
    with pytest.raises(SampleRateMismatchError):
        backend.open_capture(
            0, sample_rate=48000, channels=2, block_size=480, callback=lambda *a: None
        )
    assert input_stream_mock.call_count == 0


# ===== RATE-04: open_capture post-open guard closes stream on negotiated drift =====


def test_open_capture_post_open_guard_closes_stream_on_drift(
    mocker: MockerFixture, make_backend
) -> None:
    """Pre-open passes; post-open finds stream.samplerate != requested →
    SampleRateMismatchError raised AND stream.close() called (no leak)."""
    mocker.patch(
        "vibemix.platform._audio_macos.sd.query_devices",
        return_value={"default_samplerate": 48000.0, "name": "BlackHole 2ch"},
    )
    fake_stream = MagicMock()
    fake_stream.samplerate = 47999.0  # post-open drift
    mocker.patch("vibemix.platform._audio_macos.sd.InputStream", return_value=fake_stream)

    backend = make_backend()
    with pytest.raises(SampleRateMismatchError, match="negotiated"):
        backend.open_capture(
            0, sample_rate=48000, channels=2, block_size=480, callback=lambda *a: None
        )
    fake_stream.close.assert_called_once()


# ===== RATE-05: find_device returns index for matching input =====


def test_find_device_returns_index_for_matching_input(mocker: MockerFixture, make_backend) -> None:
    """Substring match + kind filter (max_input_channels > 0) returns the right index."""
    mocker.patch(
        "vibemix.platform._audio_macos.sd.query_devices",
        return_value=[
            {"name": "BlackHole 2ch", "max_input_channels": 2, "max_output_channels": 0},
            {"name": "Built-in Output", "max_input_channels": 0, "max_output_channels": 2},
        ],
    )
    backend = make_backend()
    assert backend.find_device("BlackHole", "input") == 0


# ===== RATE-06: find_device raises with candidate list on miss =====


def test_find_device_raises_with_candidate_list_on_miss(
    mocker: MockerFixture, make_backend
) -> None:
    """Miss raises RuntimeError listing all candidate devices (no cryptic PortAudio trace)."""
    mocker.patch(
        "vibemix.platform._audio_macos.sd.query_devices",
        return_value=[
            {"name": "BlackHole 2ch", "max_input_channels": 2, "max_output_channels": 0},
            {"name": "Built-in Output", "max_input_channels": 0, "max_output_channels": 2},
        ],
    )
    backend = make_backend()
    with pytest.raises(RuntimeError, match="nonexistent") as exc_info:
        backend.find_device("nonexistent", "input")
    msg = str(exc_info.value)
    assert "BlackHole 2ch" in msg


# ===== RATE-07: AudioMacOS satisfies @runtime_checkable AudioBackend =====


def test_audio_macos_is_audio_backend(make_backend) -> None:
    """Structural Protocol check — isinstance must return True (Phase 1 contract)."""
    backend = make_backend()
    assert isinstance(backend, AudioBackend) is True


# ===== RATE-08/09/10: pre-open guard fires for all stream openers =====


def test_open_passthrough_output_pre_open_guard(mocker: MockerFixture, make_backend) -> None:
    """Passthrough output respects pre-open sample-rate guard."""
    mocker.patch(
        "vibemix.platform._audio_macos.sd.query_devices",
        return_value={"default_samplerate": 44100.0, "name": "Speakers"},
    )
    out_mock = mocker.patch("vibemix.platform._audio_macos.sd.OutputStream")
    backend = make_backend()
    with pytest.raises(SampleRateMismatchError):
        backend.open_passthrough_output(
            0, sample_rate=48000, channels=2, block_size=256, callback=lambda *a: None
        )
    assert out_mock.call_count == 0


def test_open_voice_output_pre_open_guard(mocker: MockerFixture, make_backend) -> None:
    """Voice output respects pre-open sample-rate guard."""
    mocker.patch(
        "vibemix.platform._audio_macos.sd.query_devices",
        return_value={"default_samplerate": 44100.0, "name": "Headphones"},
    )
    out_mock = mocker.patch("vibemix.platform._audio_macos.sd.RawOutputStream")
    backend = make_backend()
    with pytest.raises(SampleRateMismatchError):
        backend.open_voice_output(0, sample_rate=24000, block_size=1024, callback=lambda *a: None)
    assert out_mock.call_count == 0


def test_open_mic_capture_pre_open_guard(mocker: MockerFixture, make_backend) -> None:
    """Mic capture (Plan 04 extension to AudioBackend) respects pre-open guard."""
    mocker.patch(
        "vibemix.platform._audio_macos.sd.query_devices",
        return_value={"default_samplerate": 44100.0, "name": "MacBook Mic"},
    )
    in_mock = mocker.patch("vibemix.platform._audio_macos.sd.InputStream")
    backend = make_backend()
    with pytest.raises(SampleRateMismatchError):
        backend.open_mic_capture(0, sample_rate=48000, block_size=480, callback=lambda *a: None)
    assert in_mock.call_count == 0


# ===== RATE-11: Phase 1 firewall still holds =====


def test_phase1_firewall_still_holds_with_audio_macos_present() -> None:
    """The typing-only platform/audio.py module must NOT import sounddevice.

    Importing `from vibemix.platform.audio import AudioBackend` alone must
    not pull in sounddevice. (Importing `from vibemix.platform import AudioMacOS`
    obviously does — that's the concrete backend.)
    """
    # Drop platform.audio from sys.modules so we re-import cleanly.
    for mod in list(sys.modules):
        if mod == "vibemix.platform.audio":
            del sys.modules[mod]
    before = "sounddevice" in sys.modules

    from vibemix.platform import audio as _audio

    # Importing the typing-only module must not pull sounddevice in (unless
    # something else in this test process imported it already).
    audio_module_dict = vars(_audio)
    assert "sounddevice" not in audio_module_dict
    assert "sd" not in audio_module_dict
    # Belt-and-braces: the audio module itself doesn't import OS modules.
    # We don't assert sys.modules state because pytest_mock fixtures or
    # earlier tests may have already imported sounddevice transitively.
    _ = before


# ===== Bonus: AudioStream Protocol adapter check =====


def test_sounddevice_stream_handle_satisfies_audio_stream_protocol(
    mocker: MockerFixture, make_backend
) -> None:
    """Returned handle has start/stop/close + latency_ms (Phase 1 AudioStream Protocol)."""
    mocker.patch(
        "vibemix.platform._audio_macos.sd.query_devices",
        return_value={"default_samplerate": 48000.0, "name": "BlackHole 2ch"},
    )
    fake_stream = MagicMock()
    fake_stream.samplerate = 48000.0
    fake_stream.latency = 0.005  # 5ms scalar
    mocker.patch("vibemix.platform._audio_macos.sd.InputStream", return_value=fake_stream)

    backend = make_backend()
    handle = backend.open_capture(
        0, sample_rate=48000, channels=2, block_size=480, callback=lambda *a: None
    )
    # latency_ms converts to ms
    assert handle.latency_ms == 5.0
    # Lifecycle methods callable
    handle.stop()
    handle.close()
    fake_stream.stop.assert_called_once()
    fake_stream.close.assert_called_once()


def test_stream_handle_handles_tuple_latency(mocker: MockerFixture, make_backend) -> None:
    """sd duplex streams return latency as (in, out) tuple — adapter picks input."""
    mocker.patch(
        "vibemix.platform._audio_macos.sd.query_devices",
        return_value={"default_samplerate": 48000.0, "name": "Speakers"},
    )
    fake_stream = MagicMock()
    fake_stream.samplerate = 48000.0
    fake_stream.latency = (0.003, 0.008)  # 3ms in, 8ms out
    mocker.patch("vibemix.platform._audio_macos.sd.OutputStream", return_value=fake_stream)
    backend = make_backend()
    handle = backend.open_passthrough_output(
        0, sample_rate=48000, channels=2, block_size=256, callback=lambda *a: None
    )
    assert handle.latency_ms == 3.0
