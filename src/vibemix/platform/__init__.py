# SPDX-License-Identifier: Apache-2.0
"""Cross-platform OS abstraction layer — the firewall.

All four protocols (AudioBackend, ScreenBackend, MidiBackend, TrackInfoBackend) live in
sibling modules. No OS-specific imports leak past this boundary — concrete impls live in
_audio_macos.py / _audio_windows.py / _screen_macos.py / etc. (Phase 2+) and are wired in
via a factory pattern. tests/test_platform.py AST-guards this rule.
"""

from vibemix.platform._audio_macos import AudioMacOS, assert_device_sample_rate
from vibemix.platform._midi_macos import MidiMacOS
from vibemix.platform._screen_macos import ScreenMacOS
from vibemix.platform._track_macos import TrackMacOS
from vibemix.platform.audio import (
    AudioBackend,
    AudioCallback,
    AudioStream,
    Kind,
)
from vibemix.platform.midi import (
    MidiBackend,
    MidiMessage,
    MidiPort,
)
from vibemix.platform.screen import (
    CapturedFrame,
    ScreenBackend,
    WindowBounds,
)
from vibemix.platform.track import (
    NowPlayingSnapshot,
    TrackInfoBackend,
)

__all__ = [
    "AudioBackend",
    "AudioCallback",
    "AudioMacOS",
    "AudioStream",
    "CapturedFrame",
    "Kind",
    "MidiBackend",
    "MidiMacOS",
    "MidiMessage",
    "MidiPort",
    "NowPlayingSnapshot",
    "ScreenBackend",
    "ScreenMacOS",
    "TrackInfoBackend",
    "TrackMacOS",
    "WindowBounds",
    "assert_device_sample_rate",
]
