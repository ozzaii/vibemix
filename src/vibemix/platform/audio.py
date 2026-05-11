# SPDX-License-Identifier: Apache-2.0
"""AudioBackend protocol — OS audio capture / passthrough / playback surface.

Lifted from cohost_v3.py:873-927 (start_input_capture) / cohost.py:479-528 (passthrough +
playback) / cohost.py:139-148 (find_device). Phase 2 macOS impl (_audio_macos.py) and
Phase 7 Windows impl (_audio_windows.py) satisfy this Protocol.

Implementations own all sounddevice / CoreAudio / WASAPI imports. This module is typing-only
and MUST NOT import any OS-specific module (enforced by tests/test_platform.py).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal, Protocol, runtime_checkable

Kind = Literal["input", "output"]

# sounddevice-shaped: (indata, frames, time_info, status)
AudioCallback = Callable[..., None]


class AudioStream(Protocol):
    """Open audio stream handle. Lifecycle: start() -> running -> stop() -> close().

    Returned by AudioBackend.open_* methods. Not @runtime_checkable — only the top-level
    backend needs runtime introspection. Concrete impls wrap sounddevice.Stream / equivalents.
    """

    @property
    def latency_ms(self) -> float: ...

    def start(self) -> None: ...

    def stop(self) -> None: ...

    def close(self) -> None: ...


@runtime_checkable
class AudioBackend(Protocol):
    """OS audio I/O firewall — capture input, route passthrough, play AI voice.

    Three open_* methods mirror the POC's three sounddevice streams (input capture from
    BlackHole, passthrough copy to speakers, AI voice playback to headphones). callback
    runs on the audio thread — must not block.
    """

    def find_device(self, name_substring: str, kind: Kind) -> int: ...

    def open_capture(
        self,
        device_index: int,
        *,
        sample_rate: int,
        channels: int,
        block_size: int,
        callback: AudioCallback,
    ) -> AudioStream: ...

    def open_passthrough_output(
        self,
        device_index: int,
        *,
        sample_rate: int,
        channels: int,
        block_size: int,
        callback: AudioCallback,
    ) -> AudioStream: ...

    def open_voice_output(
        self,
        device_index: int,
        *,
        sample_rate: int,
        block_size: int,
        callback: AudioCallback,
    ) -> AudioStream: ...
