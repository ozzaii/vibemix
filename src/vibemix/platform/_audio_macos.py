# SPDX-License-Identifier: Apache-2.0
"""Concrete ``AudioBackend`` impl for macOS.

Owns all sounddevice / scipy imports — the Phase 1 platform firewall keeps these
out of `vibemix.platform.audio` (the typing-only Protocol module). Wires the v4
stream factories (cohost_v4.py:855-947 + 1895-1908) into a class that satisfies
the Phase 1 Protocol firewall.

Sample-rate sanity guard (RESEARCH.md Q2) catches the BlackHole 44100-vs-48000
mismatch Kaan hit live on 2026-05-11 — Audio MIDI Setup misconfig is detected
pre-open (via `sd.query_devices(idx)['default_samplerate']`, the only API on
macOS CoreAudio that reflects the live device setting) AND post-open (via
``Stream.samplerate`` for hardware drift on Multi-Output Devices).

Drops the v4 ``_HAS_VISION`` / ``_HAS_WS`` / ``_HAS_QUARTZ`` feature-flag
anti-pattern (PATTERNS.md §AntiPatterns-2) — if `sounddevice` fails to import,
this module fails loud, no silent degradation.
"""

from __future__ import annotations

import sounddevice as sd

from vibemix.audio.errors import SampleRateMismatchError
from vibemix.audio.recorder import VoiceRecorder
from vibemix.audio.registry import BufferRegistry
from vibemix.platform.audio import AudioCallback, AudioStream, Kind


def assert_device_sample_rate(device_index: int, expected: int) -> None:
    """Pre-open guard: assert the device's CURRENT driver sample rate matches `expected`.

    Reads ``sd.query_devices(idx)['default_samplerate']`` — on macOS CoreAudio
    this reflects ``kAudioDevicePropertyNominalSampleRate``, i.e. whatever
    Audio MIDI Setup is configured to right now. NOT the same as
    ``Stream.samplerate`` after opening (which reports the PortAudio-negotiated
    rate and silently lies about device drift — RESEARCH.md Q2).

    Raises ``SampleRateMismatchError`` with a multi-line actionable message
    including the Audio MIDI Setup fix steps + Drift Correction note.
    """
    info = sd.query_devices(device_index)
    actual = int(info["default_samplerate"])
    name = info.get("name", f"device {device_index}")
    if actual != expected:
        raise SampleRateMismatchError(
            f"{name} is configured at {actual}Hz but vibemix expects {expected}Hz.\n"
            f"Fix: open Audio MIDI Setup -> {name} -> Format -> "
            f"{expected:,} Hz (2 ch, 32-bit float).\n"
            f"Also enable Drift Correction on BlackHole if you use a Multi-Output Device."
        )


class _SoundDeviceStreamHandle:
    """Adapter from ``sd.Input/Output/RawInput/RawOutputStream`` to the Phase 1
    ``AudioStream`` Protocol (latency_ms + start/stop/close)."""

    def __init__(
        self,
        stream: sd.InputStream | sd.OutputStream | sd.RawInputStream | sd.RawOutputStream,
    ) -> None:
        self._stream = stream

    @property
    def latency_ms(self) -> float:
        lat = self._stream.latency
        # sd.Stream.latency is a (in, out) tuple for duplex streams; scalar otherwise.
        if isinstance(lat, tuple):
            lat = lat[0]
        return float(lat) * 1000.0

    def start(self) -> None:
        self._stream.start()

    def stop(self) -> None:
        self._stream.stop()

    def close(self) -> None:
        self._stream.close()


class AudioMacOS:
    """macOS ``AudioBackend`` impl wrapping sounddevice.

    Satisfies the Phase 1 ``AudioBackend`` Protocol structurally via
    ``@runtime_checkable`` — no inheritance. Plus ``open_mic_capture`` as a
    macOS-only extension (PATTERNS.md §AntiPatterns-5 — wraps the v4:1895-1908
    inline mic stream into a proper factory for symmetry with the other three).

    Constructor takes the `BufferRegistry` + `VoiceRecorder` so a caller-side
    factory can build the v4 dual-buffer input callback (Plan 04 of Phase 3
    territory) by closing over them. This class itself focuses on I/O lifecycle
    + sample-rate guards, not the dual-buffer choreography.
    """

    def __init__(self, registry: BufferRegistry, recorder: VoiceRecorder) -> None:
        self.registry = registry
        self.recorder = recorder

    def find_device(self, name_substring: str, kind: Kind) -> int:
        """Find a CoreAudio device by case-insensitive substring match on its name.

        On miss, raises ``RuntimeError`` with the candidate-device list so the
        user sees "available inputs: [...]" rather than a cryptic PortAudio
        stack trace (RESEARCH.md Threat 4). Verbatim port of v4:241-250 with
        the improved error message.
        """
        target_field = "max_input_channels" if kind == "input" else "max_output_channels"
        devices = sd.query_devices()
        needle = name_substring.lower()
        for idx, info in enumerate(devices):
            if needle in info["name"].lower() and info[target_field] > 0:
                return idx
        available = [d["name"] for d in devices if d[target_field] > 0]
        raise RuntimeError(
            f"No {kind} device matching {name_substring!r}. Available {kind} devices: {available}"
        )

    def open_capture(
        self,
        device_index: int,
        *,
        sample_rate: int,
        channels: int,
        block_size: int,
        callback: AudioCallback,
    ) -> AudioStream:
        """Open input capture stream (sd.InputStream @ float32 low-latency).

        Pre-open: ``assert_device_sample_rate`` (reads Audio MIDI Setup state).
        Post-open: ``stream.samplerate`` belt-and-suspenders (catches hardware
        drift on Multi-Output Devices). On either failure raises
        ``SampleRateMismatchError`` AND closes the stream to avoid leaks.
        """
        assert_device_sample_rate(device_index, sample_rate)
        stream = sd.InputStream(
            device=device_index,
            samplerate=sample_rate,
            channels=channels,
            dtype="float32",
            blocksize=block_size,
            latency="low",
            callback=callback,
        )
        if int(stream.samplerate) != sample_rate:
            negotiated = int(stream.samplerate)
            stream.close()
            raise SampleRateMismatchError(
                f"PortAudio negotiated {negotiated}Hz vs requested {sample_rate}Hz on "
                f"device {device_index!r}. Hardware drift detected — enable Drift "
                f"Correction in Audio MIDI Setup."
            )
        stream.start()
        return _SoundDeviceStreamHandle(stream)

    def open_passthrough_output(
        self,
        device_index: int,
        *,
        sample_rate: int,
        channels: int,
        block_size: int,
        callback: AudioCallback,
    ) -> AudioStream:
        """Open passthrough output (sd.OutputStream @ float32 — djay → speakers stereo)."""
        assert_device_sample_rate(device_index, sample_rate)
        stream = sd.OutputStream(
            device=device_index,
            samplerate=sample_rate,
            channels=channels,
            dtype="float32",
            blocksize=block_size,
            latency="low",
            callback=callback,
        )
        if int(stream.samplerate) != sample_rate:
            negotiated = int(stream.samplerate)
            stream.close()
            raise SampleRateMismatchError(
                f"PortAudio negotiated {negotiated}Hz vs requested {sample_rate}Hz on "
                f"passthrough output device {device_index!r}."
            )
        stream.start()
        return _SoundDeviceStreamHandle(stream)

    def open_voice_output(
        self,
        device_index: int,
        *,
        sample_rate: int,
        block_size: int,
        callback: AudioCallback,
    ) -> AudioStream:
        """Open AI voice output (sd.RawOutputStream @ int16 mono — to headphones)."""
        assert_device_sample_rate(device_index, sample_rate)
        stream = sd.RawOutputStream(
            device=device_index,
            samplerate=sample_rate,
            channels=1,
            dtype="int16",
            blocksize=block_size,
            latency="low",
            callback=callback,
        )
        if int(stream.samplerate) != sample_rate:
            negotiated = int(stream.samplerate)
            stream.close()
            raise SampleRateMismatchError(
                f"PortAudio negotiated {negotiated}Hz vs requested {sample_rate}Hz on "
                f"voice output device {device_index!r}."
            )
        stream.start()
        return _SoundDeviceStreamHandle(stream)

    def open_mic_capture(
        self,
        device_index: int,
        *,
        sample_rate: int,
        block_size: int,
        callback: AudioCallback,
    ) -> AudioStream:
        """Open mic capture (sd.InputStream @ float32 mono).

        Wraps the v4:1895-1908 inline mic stream as a proper factory
        (PATTERNS.md §AntiPatterns-5 — every other stream has a factory, mic
        doesn't in v4). This is a macOS-only extension to ``AudioBackend`` —
        NOT in the Phase 1 Protocol. If Phase 3 reveals callers always need
        mic capture cross-platform, Phase 3 (or Phase 7 Windows port) should
        amend the Protocol via a separate commit.
        """
        assert_device_sample_rate(device_index, sample_rate)
        stream = sd.InputStream(
            device=device_index,
            samplerate=sample_rate,
            channels=1,
            dtype="float32",
            blocksize=block_size,
            latency="low",
            callback=callback,
        )
        if int(stream.samplerate) != sample_rate:
            negotiated = int(stream.samplerate)
            stream.close()
            raise SampleRateMismatchError(
                f"PortAudio negotiated {negotiated}Hz vs requested {sample_rate}Hz on "
                f"mic device {device_index!r}."
            )
        stream.start()
        return _SoundDeviceStreamHandle(stream)
