# SPDX-License-Identifier: Apache-2.0
"""Concrete ``AudioBackend`` impl for Windows via PyAudioWPatch (WASAPI loopback).

Mirrors the Phase 2 ``_audio_macos.py`` shape so the platform selector
(``vibemix.platform.__init__``) can swap impls transparently. The substantive
differences vs. macOS:

1. **Capture path** — WASAPI loopback on the default playback device. No virtual
   cable required (BlackHole-equivalent install is the macOS-only tax). The
   loopback index is whatever ``pyaudiowpatch.PyAudio().get_default_wasapi_loopback_device()``
   returns; the ``device_index`` argument to ``open_capture`` is IGNORED for the
   v1 contract — Phase 11 calibration may revisit if users need to target a
   non-default loopback.

2. **Sample-rate guard** — ``assert_wasapi_loopback_rate`` queries the loopback
   device's ``defaultSampleRate`` and raises ``SampleRateMismatchError`` (the
   shared exception type from ``vibemix.audio.errors`` introduced in Phase 2)
   with a Windows-specific actionable message: "Control Panel → Sound →
   Properties → Advanced → set Default Format to 48,000 Hz, 16-bit". The
   macOS guard's "Audio MIDI Setup → Format → 48000 Hz" message is the same
   shape of fix on a different OS.

3. **Critical Constraint 3 — lazy imports** — ``import pyaudiowpatch`` lives
   ONLY inside method bodies, NEVER at module top. This keeps the file
   importable on macOS (where the package isn't installed — pyproject's
   ``sys_platform == 'win32'`` marker skips it) so:
     - the platform selector can eagerly import the right impl on win32 and
       eagerly fail at startup on missing-impl bugs (Phase 7 Wave 1 design);
     - mocked unit tests (``tests/test_audio_windows.py``) run on Kaan's macOS
       dev box by injecting a ``MagicMock`` into ``sys.modules["pyaudiowpatch"]``
       before the lazy import fires.

4. **No post-open negotiated-rate re-check** — PyAudio's Stream class doesn't
   expose a ``negotiated_samplerate`` attribute equivalent to sounddevice's
   ``Stream.samplerate``. The WASAPI loopback ``defaultSampleRate`` pre-check
   is the authoritative source on Windows; if the OS lies about the rate
   we'll catch it later via downstream ``AudioBuffer`` clock-skew detection
   (Phase 8 territory).

5. **No silent degradation** — drops the v4 ``_HAS_VISION`` / ``_HAS_WS`` /
   ``_HAS_QUARTZ`` feature-flag anti-pattern (PATTERNS.md §AntiPatterns-2). If
   ``pyaudiowpatch`` fails to import inside a method body on Windows, the
   exception propagates loudly. The lazy import guards platform reach, NOT
   degraded behaviour.

Phase 11 (Tauri shell + Calibration Wizard) reads ``sys.platform`` to pick the
OS-specific permission-flow walkthrough; Phase 18 (PyInstaller --onedir)
bundles ``pyaudiowpatch`` into the Windows MSI; Phase 20 (CI matrix) runs
``tests/test_audio_windows_live.py`` against ``windows-latest`` and Kaan
smoke-tests on a real Windows 11 machine before sign-off.
"""

from __future__ import annotations

from typing import Literal

from vibemix.audio.errors import SampleRateMismatchError
from vibemix.audio.recorder import VoiceRecorder
from vibemix.audio.registry import BufferRegistry
from vibemix.platform.audio import AudioCallback, AudioStream, Kind

# NO top-level ``import pyaudiowpatch`` — Critical Constraint 3. All
# Windows-only imports live inside method bodies so this file imports cleanly
# on macOS for mocked testing.


def assert_wasapi_loopback_rate(expected: int) -> tuple[int, str]:
    """Pre-open guard: assert the default WASAPI loopback device runs at ``expected`` Hz.

    Queries ``pyaudiowpatch.PyAudio().get_default_wasapi_loopback_device()``
    which returns the loopback handle for whatever's currently routed to the
    system's default playback device. Reads ``defaultSampleRate`` from the
    returned dict and compares against ``expected``.

    Raises ``SampleRateMismatchError`` with a Windows-specific actionable
    message on mismatch. The message is multi-line and includes the named
    device so the user knows which "Speakers" entry to fix in Control Panel.

    Returns ``(loopback_index, loopback_name)`` on success — the caller
    (``open_capture``) reuses the index without re-querying. Always
    ``terminate()``s the temporary PyAudio instance, even on raise (no leaks).

    Reuses the Phase 2 ``SampleRateMismatchError`` exception type from
    ``vibemix.audio.errors`` — the WASAPI 44100/48000 misconfig is the
    Windows-side equivalent of the BlackHole misconfig Kaan hit on 2026-05-11
    (RESEARCH.md Q2 / macOS PATTERNS.md).
    """
    import pyaudiowpatch as pa

    p = pa.PyAudio()
    try:
        info = p.get_default_wasapi_loopback_device()
        actual = int(info["defaultSampleRate"])
        name = info.get("name", "default loopback device")
        index = int(info["index"])
        if actual != expected:
            raise SampleRateMismatchError(
                f"WASAPI loopback device {name!r} is configured at {actual}Hz "
                f"but vibemix expects {expected}Hz.\n"
                f"Fix: open Control Panel → Sound → Right-click 'Speakers' → "
                f"Properties → Advanced → set Default Format to {expected:,} Hz, "
                f"16-bit. Then restart vibemix.\n"
                f"Note: Windows applies the change immediately for new streams; "
                f"in-flight DAWs may need a restart too."
            )
        return index, name
    finally:
        p.terminate()


class _PyAudioStreamHandle:
    """Adapter from a ``pyaudiowpatch`` Stream → Phase 1 ``AudioStream`` Protocol.

    Matches the macOS ``_SoundDeviceStreamHandle`` adapter shape. ``latency_ms``
    delegates to ``Stream.get_input_latency()`` for input streams and
    ``get_output_latency()`` for output streams (PyAudio splits the sounddevice
    duplex-tuple latency into two separate getters).

    ``close()`` calls ``Stream.close()`` AND ``PyAudio.terminate()`` on the
    parent instance — every ``open_*`` factory creates its own ``PyAudio()``
    instance and stows it on the handle so close() can release it. This
    matches sounddevice's ``sd.Stream`` lifecycle model where each stream owns
    its own PortAudio handle behind the scenes.
    """

    def __init__(self, stream, pyaudio_instance, kind: Literal["input", "output"]) -> None:
        self._stream = stream
        self._pa = pyaudio_instance
        self._kind = kind

    @property
    def latency_ms(self) -> float:
        if self._kind == "input":
            sec = self._stream.get_input_latency()
        else:
            sec = self._stream.get_output_latency()
        return float(sec) * 1000.0

    def start(self) -> None:
        self._stream.start_stream()

    def stop(self) -> None:
        self._stream.stop_stream()

    def close(self) -> None:
        self._stream.close()
        self._pa.terminate()


class AudioWindows:
    """Windows ``AudioBackend`` impl wrapping PyAudioWPatch (WASAPI loopback).

    Satisfies the Phase 1 ``AudioBackend`` Protocol structurally via
    ``@runtime_checkable`` — no inheritance, just method-name matching. Plus
    ``open_mic_capture`` as a Windows-only extension matching macOS's
    ``open_mic_capture`` shape (the natural cross-platform mic surface; if a
    future caller needs it cross-platform, the Phase 1 Protocol can be amended
    in a separate commit).

    Constructor takes the ``BufferRegistry`` + ``VoiceRecorder`` so a
    caller-side factory can build the dual-buffer input callback (Phase 4
    territory) by closing over them. This class itself focuses on I/O
    lifecycle + sample-rate guards, not the dual-buffer choreography.
    """

    def __init__(self, registry: BufferRegistry, recorder: VoiceRecorder) -> None:
        self.registry = registry
        self.recorder = recorder

    def find_device(self, name_substring: str, kind: Kind) -> int:
        """Find a WASAPI device by case-insensitive substring match on its name.

        Iterates ``PyAudio.get_device_count()`` + ``get_device_info_by_index(idx)``;
        ``maxInputChannels > 0`` for ``kind="input"``, ``maxOutputChannels > 0``
        for ``kind="output"`` (PyAudio uses camelCase keys; sounddevice uses
        snake_case — that's the substantive shape difference vs. ``AudioMacOS``).

        On miss raises ``RuntimeError`` with the candidate-device list so the
        user sees "Available <kind> devices: [...]" rather than a cryptic
        PortAudio stack trace. Matches the macOS error shape.

        Always ``terminate()``s the temporary PyAudio instance, even on raise.
        """
        import pyaudiowpatch as pa

        target_field = "maxInputChannels" if kind == "input" else "maxOutputChannels"
        p = pa.PyAudio()
        try:
            needle = name_substring.lower()
            count = p.get_device_count()
            for idx in range(count):
                info = p.get_device_info_by_index(idx)
                if needle in info["name"].lower() and info[target_field] > 0:
                    return idx
            available = []
            for idx in range(count):
                info = p.get_device_info_by_index(idx)
                if info[target_field] > 0:
                    available.append(info["name"])
            raise RuntimeError(
                f"No {kind} device matching {name_substring!r}. "
                f"Available {kind} devices: {available}"
            )
        finally:
            p.terminate()

    def open_capture(
        self,
        device_index: int,
        *,
        sample_rate: int,
        channels: int,
        block_size: int,
        callback: AudioCallback,
    ) -> AudioStream:
        """Open WASAPI loopback capture stream (paInt16 master-output mirror).

        ``device_index`` is IGNORED for the v1 WASAPI loopback path — we always
        target the default playback device's loopback. Phase 11 calibration may
        supply a non-default loopback target later.

        Pre-open: ``assert_wasapi_loopback_rate`` (raises ``SampleRateMismatchError``
        on Control Panel misconfig). Returns the loopback index from the same
        call so we don't re-query.

        Note: PyAudio's Stream class doesn't expose a ``negotiated_samplerate``
        attribute, so there's no post-open re-check here. The pre-open
        ``defaultSampleRate`` query is the authoritative source on Windows.
        """
        # Pre-open guard. Returns (loopback_idx, loopback_name); name unused
        # here but available for diagnostic logging in callers.
        loopback_idx, _loopback_name = assert_wasapi_loopback_rate(sample_rate)

        import pyaudiowpatch as pa

        p = pa.PyAudio()
        stream = p.open(
            format=pa.paInt16,
            channels=channels,
            rate=sample_rate,
            input=True,
            input_device_index=loopback_idx,
            frames_per_buffer=block_size,
            stream_callback=callback,
        )
        # PyAudio auto-starts when stream_callback is set, but call
        # start_stream() explicitly for symmetry with the macOS impl.
        stream.start_stream()
        return _PyAudioStreamHandle(stream, p, "input")

    def open_passthrough_output(
        self,
        device_index: int,
        *,
        sample_rate: int,
        channels: int,
        block_size: int,
        callback: AudioCallback,
    ) -> AudioStream:
        """Open passthrough output (paFloat32 — djay → speakers stereo).

        Mirrors macOS shape: 48kHz stereo float32 to the user-selected output
        device. Currently unused at the application level (PASSTHROUGH_GAIN=0.0
        — same as macOS) but the factory exists for symmetry.
        """
        import pyaudiowpatch as pa

        p = pa.PyAudio()
        stream = p.open(
            format=pa.paFloat32,
            channels=channels,
            rate=sample_rate,
            output=True,
            output_device_index=device_index,
            frames_per_buffer=block_size,
            stream_callback=callback,
        )
        stream.start_stream()
        return _PyAudioStreamHandle(stream, p, "output")

    def open_voice_output(
        self,
        device_index: int,
        *,
        sample_rate: int,
        block_size: int,
        callback: AudioCallback,
    ) -> AudioStream:
        """Open AI voice output (paInt16 mono — to user-selected device).

        24kHz int16 mono — same params as the macOS ``RawOutputStream``-equivalent,
        same shape Gemini TTS streams produce.
        """
        import pyaudiowpatch as pa

        p = pa.PyAudio()
        stream = p.open(
            format=pa.paInt16,
            channels=1,
            rate=sample_rate,
            output=True,
            output_device_index=device_index,
            frames_per_buffer=block_size,
            stream_callback=callback,
        )
        stream.start_stream()
        return _PyAudioStreamHandle(stream, p, "output")

    def open_mic_capture(
        self,
        device_index: int,
        *,
        sample_rate: int,
        block_size: int,
        callback: AudioCallback,
    ) -> AudioStream:
        """Open mic capture (paFloat32 mono — Kaan's voice into the AI).

        Matches the macOS ``open_mic_capture`` shape (Phase 2 extension to
        ``AudioBackend``). Same caveat: NOT in the Phase 1 Protocol; if Phase
        3+ reveals callers always need mic capture cross-platform, amend the
        Protocol in a separate commit.
        """
        import pyaudiowpatch as pa

        p = pa.PyAudio()
        stream = p.open(
            format=pa.paFloat32,
            channels=1,
            rate=sample_rate,
            input=True,
            input_device_index=device_index,
            frames_per_buffer=block_size,
            stream_callback=callback,
        )
        stream.start_stream()
        return _PyAudioStreamHandle(stream, p, "input")


__all__ = [
    "AudioWindows",
    "assert_wasapi_loopback_rate",
]
