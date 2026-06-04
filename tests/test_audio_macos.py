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

import numpy as np
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
    mocker.patch(
        "vibemix.platform._audio_macos.set_device_nominal_sample_rate",
        return_value=False,
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


# ===== RATE-03: open_capture opens at the device's NATIVE rate + resamples =====


def test_open_capture_native_rate_resamples_instead_of_raising(
    mocker: MockerFixture, make_backend
) -> None:
    """A 44.1k master device no longer crashes: open_capture opens at the device's
    native rate and resamples to the analysis rate, mirroring the proven
    open_passthrough_output path. The raw callback is wrapped (not passed through)."""
    mocker.patch(
        "vibemix.platform._audio_macos.sd.query_devices",
        return_value={"default_samplerate": 44100.0, "name": "BlackHole 2ch"},
    )
    fake_stream = MagicMock()
    fake_stream.samplerate = 44100
    input_stream_mock = mocker.patch(
        "vibemix.platform._audio_macos.sd.InputStream", return_value=fake_stream
    )

    backend = make_backend()
    real_cb = lambda *a: None  # noqa: E731
    backend.open_capture(0, sample_rate=48000, channels=2, block_size=480, callback=real_cb)

    ck = input_stream_mock.call_args.kwargs
    assert ck["samplerate"] == 44100, "must open at the device's native rate, not force 48k"
    assert ck["callback"] is not real_cb, "callback must be the resampling wrapper"
    fake_stream.start.assert_called_once()


def test_open_capture_48k_passes_raw_callback_unchanged(
    mocker: MockerFixture, make_backend
) -> None:
    """device already at 48000 → byte-identical path: opened at 48000 with the raw
    callback (no resample wrapper), so the working case is untouched."""
    mocker.patch(
        "vibemix.platform._audio_macos.sd.query_devices",
        return_value={"default_samplerate": 48000.0, "name": "BlackHole 2ch"},
    )
    fake_stream = MagicMock()
    fake_stream.samplerate = 48000
    input_stream_mock = mocker.patch(
        "vibemix.platform._audio_macos.sd.InputStream", return_value=fake_stream
    )

    backend = make_backend()
    real_cb = lambda *a: None  # noqa: E731
    backend.open_capture(0, sample_rate=48000, channels=2, block_size=480, callback=real_cb)

    ck = input_stream_mock.call_args.kwargs
    assert ck["samplerate"] == 48000
    assert ck["callback"] is real_cb, "48k path must pass the raw callback unchanged"


def test_input_resampler_converts_device_rate_to_analysis_rate() -> None:
    """The capture wrapper resamples device-rate buffers to the analysis rate so the
    grounding engine always sees target_sr audio — the anti-mis-ground guarantee."""
    from vibemix.audio.resample import resample_audio
    from vibemix.platform._audio_macos import _make_input_resampler

    received: dict[str, object] = {}

    def real_cb(buf, frames, time_info, status):
        received["buf"] = buf
        received["frames"] = frames

    wrapped = _make_input_resampler(real_cb, device_sr=44100, target_sr=48000, channels=2)
    indata = np.ones((441, 2), dtype=np.float32)
    wrapped(indata, 441, None, None)

    expected_len = len(resample_audio(indata[:, 0], source_sr=44100, target_sr=48000))
    assert received["frames"] == expected_len
    assert received["buf"].shape == (expected_len, 2)
    assert received["buf"].dtype == np.float32


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


# ===== RATE-06b: find_device("BlackHole 2ch", input) on a real rig picks BlackHole, NOT the controller =====


def test_find_device_master_input_skips_controller_on_founder_rig(
    mocker: MockerFixture, make_backend
) -> None:
    """Release-blocking regression (2026-05-24): the co-host grabbed the
    DDJ-FLX4 controller soundcard instead of BlackHole 2ch.

    Through the real ``find_device`` path, with the controller + aggregates
    enumerated BEFORE BlackHole, the backend MUST return the BlackHole 2ch
    index and never the controller.
    """
    devices = [
        {"name": "MacBook Pro Microphone", "max_input_channels": 1, "max_output_channels": 0},
        {"name": "DDJ-FLX4", "max_input_channels": 4, "max_output_channels": 4},
        {"name": "rekordbox Aggregate Device", "max_input_channels": 4, "max_output_channels": 4},
        {"name": "AI Capture", "max_input_channels": 2, "max_output_channels": 2},
        {"name": "BlackHole 2ch", "max_input_channels": 2, "max_output_channels": 0},
        {"name": "BlackHole 16ch", "max_input_channels": 16, "max_output_channels": 0},
    ]
    mocker.patch("vibemix.platform._audio_macos.sd.query_devices", return_value=devices)
    backend = make_backend()
    idx = backend.find_device("BlackHole 2ch", "input")
    assert devices[idx]["name"] == "BlackHole 2ch"


def test_find_device_master_input_raises_when_blackhole_absent(
    mocker: MockerFixture, make_backend
) -> None:
    """No BlackHole present → RuntimeError carrying the requested name (so the
    __main__ FATAL handler classifies it as an input miss → exit 3), NOT a
    silent fallback to the controller."""
    devices = [
        {"name": "MacBook Pro Microphone", "max_input_channels": 1, "max_output_channels": 0},
        {"name": "DDJ-FLX4", "max_input_channels": 4, "max_output_channels": 4},
    ]
    mocker.patch("vibemix.platform._audio_macos.sd.query_devices", return_value=devices)
    backend = make_backend()
    with pytest.raises(RuntimeError, match="BlackHole 2ch") as exc:
        backend.find_device("BlackHole 2ch", "input")
    assert "blackhole-2ch" in str(exc.value)


def test_find_device_honors_explicit_blackhole_variant(
    mocker: MockerFixture,
    make_backend,
) -> None:
    """An explicit BlackHole variant request is not rewritten to 2ch."""
    devices = [
        {"name": "BlackHole 2ch", "max_input_channels": 2, "max_output_channels": 2},
        {"name": "BlackHole 16ch", "max_input_channels": 16, "max_output_channels": 16},
    ]
    mocker.patch("vibemix.platform._audio_macos.sd.query_devices", return_value=devices)
    backend = make_backend()

    assert backend.find_device("BlackHole 16ch", "input") == 1


def test_find_device_auto_master_input_chooses_live_48k_variant(
    mocker: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
    make_backend,
) -> None:
    """Auto master finder follows the actual live signal, not the static 2ch default."""
    devices = [
        {
            "name": "BlackHole 2ch",
            "max_input_channels": 2,
            "max_output_channels": 2,
            "default_samplerate": 44100.0,
        },
        {
            "name": "BlackHole 16ch",
            "max_input_channels": 16,
            "max_output_channels": 16,
            "default_samplerate": 48000.0,
        },
    ]
    mocker.patch("vibemix.platform._audio_macos.sd.query_devices", return_value=devices)

    def fake_rec(frames, *, samplerate, channels, dtype, device, blocking):
        del samplerate, dtype, blocking
        value = 0.05 if device == 1 else 0.0
        return np.full((frames, channels), value, dtype=np.float32)

    mocker.patch("vibemix.platform._audio_macos.sd.rec", side_effect=fake_rec)
    monkeypatch.setenv("VIBEMIX_AUTO_MASTER_INPUT", "1")

    backend = make_backend()
    assert backend.find_device("BlackHole 2ch", "input") == 1


def test_find_device_auto_master_input_prefers_live_2ch_over_louder_live_16ch(
    mocker: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
    make_backend,
) -> None:
    """When both provisioned loopbacks carry master audio, pick canonical 2ch."""
    devices = [
        {
            "name": "BlackHole 2ch",
            "max_input_channels": 2,
            "max_output_channels": 2,
            "default_samplerate": 48000.0,
        },
        {
            "name": "BlackHole 16ch",
            "max_input_channels": 16,
            "max_output_channels": 16,
            "default_samplerate": 48000.0,
        },
    ]
    mocker.patch("vibemix.platform._audio_macos.sd.query_devices", return_value=devices)

    def fake_rec(frames, *, samplerate, channels, dtype, device, blocking):
        del samplerate, dtype, blocking
        value = 0.02 if device == 0 else 0.06
        return np.full((frames, channels), value, dtype=np.float32)

    mocker.patch("vibemix.platform._audio_macos.sd.rec", side_effect=fake_rec)
    monkeypatch.setenv("VIBEMIX_AUTO_MASTER_INPUT", "1")

    backend = make_backend()
    assert backend.find_device("BlackHole 2ch", "input") == 0


def test_find_device_auto_master_input_falls_back_to_48k_variant_when_silent(
    mocker: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
    make_backend,
) -> None:
    """Auto mode prefers a usable 48 kHz BlackHole over a 44.1 kHz exact default."""
    devices = [
        {
            "name": "BlackHole 2ch",
            "max_input_channels": 2,
            "max_output_channels": 2,
            "default_samplerate": 44100.0,
        },
        {
            "name": "BlackHole 16ch",
            "max_input_channels": 16,
            "max_output_channels": 16,
            "default_samplerate": 48000.0,
        },
    ]
    mocker.patch("vibemix.platform._audio_macos.sd.query_devices", return_value=devices)
    mocker.patch(
        "vibemix.platform._audio_macos.sd.rec",
        return_value=np.zeros((64, 2), dtype=np.float32),
    )
    monkeypatch.setenv("VIBEMIX_AUTO_MASTER_INPUT", "1")

    backend = make_backend()
    assert backend.find_device("BlackHole 2ch", "input") == 1


def test_find_device_auto_master_input_uses_preferred_fallback_when_silent(
    mocker: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
    make_backend,
) -> None:
    """The proof runner can keep auto mode while hinting Rekordbox's route."""
    devices = [
        {
            "name": "BlackHole 2ch",
            "max_input_channels": 2,
            "max_output_channels": 2,
            "default_samplerate": 48000.0,
        },
        {
            "name": "BlackHole 16ch",
            "max_input_channels": 16,
            "max_output_channels": 16,
            "default_samplerate": 48000.0,
        },
    ]
    mocker.patch("vibemix.platform._audio_macos.sd.query_devices", return_value=devices)
    mocker.patch(
        "vibemix.platform._audio_macos.sd.rec",
        return_value=np.zeros((64, 2), dtype=np.float32),
    )
    monkeypatch.setenv("VIBEMIX_AUTO_MASTER_INPUT", "1")
    monkeypatch.setenv("VIBEMIX_AUTO_MASTER_FALLBACK_DEVICE", "BlackHole 2ch")

    backend = make_backend()
    assert backend.find_device("BlackHole 2ch", "input") == 0


def test_find_device_auto_master_input_honors_explicit_blackhole_variant(
    mocker: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
    make_backend,
) -> None:
    """The sidecar's auto-master env must not hijack an explicit 16ch upgrade."""
    devices = [
        {
            "name": "BlackHole 2ch",
            "max_input_channels": 2,
            "max_output_channels": 2,
            "default_samplerate": 48000.0,
        },
        {
            "name": "BlackHole 16ch",
            "max_input_channels": 16,
            "max_output_channels": 16,
            "default_samplerate": 48000.0,
        },
    ]
    mocker.patch("vibemix.platform._audio_macos.sd.query_devices", return_value=devices)
    rec = mocker.patch(
        "vibemix.platform._audio_macos.sd.rec",
        return_value=np.zeros((64, 2), dtype=np.float32),
    )
    monkeypatch.setenv("VIBEMIX_AUTO_MASTER_INPUT", "1")

    backend = make_backend()
    assert backend.find_device("BlackHole 16ch", "input") == 1
    rec.assert_not_called()


# ===== RATE-07: AudioMacOS satisfies @runtime_checkable AudioBackend =====


def test_audio_macos_is_audio_backend(make_backend) -> None:
    """Structural Protocol check — isinstance must return True (Phase 1 contract)."""
    backend = make_backend()
    assert isinstance(backend, AudioBackend) is True


# ===== RATE-08/09/10: pre-open guard fires for all stream openers =====


def test_open_passthrough_output_resamples_instead_of_raising(
    mocker: MockerFixture,
    make_backend,
) -> None:
    """Passthrough output opens at the device rate when output is 44.1 kHz."""
    mocker.patch(
        "vibemix.platform._audio_macos.sd.query_devices",
        return_value={"default_samplerate": 44100.0, "name": "Speakers"},
    )
    fake_stream = MagicMock()
    fake_stream.samplerate = 44100
    out_mock = mocker.patch(
        "vibemix.platform._audio_macos.sd.OutputStream",
        return_value=fake_stream,
    )
    backend = make_backend()
    handle = backend.open_passthrough_output(
        0, sample_rate=48000, channels=2, block_size=480, callback=lambda *a: None
    )

    assert handle is not None
    out_mock.assert_called_once()
    call_kwargs = out_mock.call_args.kwargs
    assert call_kwargs["samplerate"] == 44100
    assert call_kwargs["blocksize"] == 441
    assert callable(call_kwargs["callback"])
    fake_stream.start.assert_called_once()


def test_open_voice_output_resamples_instead_of_raising(
    mocker: MockerFixture, make_backend
) -> None:
    """2026-05-18 — voice output no longer raises on rate mismatch.

    Aggregate devices (AI Capture stacking on top of BlackHole, AirPods at
    44.1k) refuse 24kHz Gemini TTS opens, so the backend now opens the
    stream at the device's native rate and wraps the source callback with
    either an integer-ratio np.repeat upsample or the local resampler.
    The pre-open guard remains only for capture / passthrough / mic paths
    where the upstream pipeline assumes lock-step rates.
    """
    mocker.patch(
        "vibemix.platform._audio_macos.sd.query_devices",
        return_value={"default_samplerate": 44100.0, "name": "Headphones"},
    )
    fake_stream = MagicMock()
    fake_stream.samplerate = 44100  # what PortAudio actually negotiated
    out_mock = mocker.patch(
        "vibemix.platform._audio_macos.sd.RawOutputStream",
        return_value=fake_stream,
    )

    backend = make_backend()
    handle = backend.open_voice_output(
        0, sample_rate=24000, block_size=1024, callback=lambda *a: None
    )

    # Backend wraps the raw sd.RawOutputStream in an _SoundDeviceStreamHandle.
    assert handle is not None
    out_mock.assert_called_once()
    # Stream was opened at the device's native rate, not the requested 24kHz.
    call_kwargs = out_mock.call_args.kwargs
    assert call_kwargs["samplerate"] == 44100
    # Wrapped callback differs from the user-supplied lambda — backend
    # injected the resample shim.
    assert callable(call_kwargs["callback"])
    fake_stream.start.assert_called_once()


def test_open_mic_capture_native_rate_resamples_instead_of_raising(
    mocker: MockerFixture, make_backend
) -> None:
    """A 44.1k mic (common on USB/interface rigs) no longer silently vanishes:
    open_mic_capture opens at the mic's native rate and resamples to the analysis
    rate (mono), so talk-back survives a rate mismatch instead of being dropped."""
    mocker.patch(
        "vibemix.platform._audio_macos.sd.query_devices",
        return_value={"default_samplerate": 44100.0, "name": "MacBook Mic"},
    )
    fake_stream = MagicMock()
    fake_stream.samplerate = 44100
    in_mock = mocker.patch(
        "vibemix.platform._audio_macos.sd.InputStream", return_value=fake_stream
    )
    backend = make_backend()
    real_cb = lambda *a: None  # noqa: E731
    backend.open_mic_capture(0, sample_rate=48000, block_size=480, callback=real_cb)

    ck = in_mock.call_args.kwargs
    assert ck["samplerate"] == 44100, "must open the mic at its native rate"
    assert ck["channels"] == 1
    assert ck["callback"] is not real_cb, "callback must be the resampling wrapper"
    fake_stream.start.assert_called_once()


def test_open_mic_capture_48k_passes_raw_callback_unchanged(
    mocker: MockerFixture, make_backend
) -> None:
    """Mic already at the analysis rate → byte-identical path: raw callback, no wrapper."""
    mocker.patch(
        "vibemix.platform._audio_macos.sd.query_devices",
        return_value={"default_samplerate": 48000.0, "name": "MacBook Mic"},
    )
    fake_stream = MagicMock()
    fake_stream.samplerate = 48000
    in_mock = mocker.patch(
        "vibemix.platform._audio_macos.sd.InputStream", return_value=fake_stream
    )
    backend = make_backend()
    real_cb = lambda *a: None  # noqa: E731
    backend.open_mic_capture(0, sample_rate=48000, block_size=480, callback=real_cb)

    ck = in_mock.call_args.kwargs
    assert ck["samplerate"] == 48000
    assert ck["callback"] is real_cb, "48k mic path must pass the raw callback unchanged"


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
