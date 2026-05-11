# SPDX-License-Identifier: Apache-2.0
"""Cross-platform OS abstraction layer — the firewall.

All four protocols (AudioBackend, ScreenBackend, MidiBackend, TrackInfoBackend) live in
sibling modules. No OS-specific imports leak past this boundary — concrete impls live in
_audio_macos.py / _audio_windows.py / _screen_macos.py / etc. (Phase 2+) and are wired in
via a factory pattern. tests/test_platform.py AST-guards this rule.
"""

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
    "AudioStream",
    "CapturedFrame",
    "Kind",
    "MidiBackend",
    "MidiMessage",
    "MidiPort",
    "NowPlayingSnapshot",
    "ScreenBackend",
    "TrackInfoBackend",
    "WindowBounds",
]
