# SPDX-License-Identifier: Apache-2.0
"""Cross-platform OS abstraction layer — the firewall.

All four protocols (AudioBackend, ScreenBackend, MidiBackend, TrackInfoBackend) live in
sibling modules. No OS-specific imports leak past this boundary — concrete impls live in
_audio_macos.py / _audio_windows.py / _screen_macos.py / etc. (Phase 2+) and are wired in
via a factory pattern. tests/test_platform.py AST-guards this rule.

Phase 7 Wave 1 adds a ``sys.platform``-dispatched selector at the bottom of the
module that exposes ``AudioImpl`` / ``ScreenImpl`` / ``MidiImpl`` / ``TrackImpl``
— callers (the runtime orchestrator + future calibration wizard) instantiate
these names instead of the OS-specific subclasses. On darwin they alias to the
Phase 2/3 macOS impls; on win32 they will alias to the Wave 2-4 Windows impls;
all other platforms raise ``RuntimeError`` (Linux explicitly excluded per
PROJECT.md).
"""

import sys as _sys

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

# ---- Phase 7 Wave 1: platform selector (per CONTEXT Decisions §Platform Selector) ----
#
# Resolves the four concrete impls by ``sys.platform``. On darwin this is a
# zero-cost alias to the Phase 2/3 macOS classes already imported above. On
# win32 it imports the Wave 2-4 ``_*_windows`` modules (NOT yet present in
# Wave 1 — that's the contract: Wave 2 ships ``_audio_windows.py``, etc.).
# Any other platform is unsupported and raises immediately.
if _sys.platform == "darwin":
    AudioImpl = AudioMacOS
    ScreenImpl = ScreenMacOS
    MidiImpl = MidiMacOS
    TrackImpl = TrackMacOS
elif _sys.platform == "win32":
    # Wave 2-4 will create these modules. Eager import so any missing-impl bug
    # surfaces at startup, NOT at first-use.
    from vibemix.platform._audio_windows import AudioWindows as AudioImpl
    from vibemix.platform._midi_windows import MidiWindows as MidiImpl
    from vibemix.platform._screen_windows import ScreenWindows as ScreenImpl
    from vibemix.platform._track_windows import TrackWindows as TrackImpl
else:
    raise RuntimeError(
        f"Unsupported platform: {_sys.platform}. vibemix supports macOS and Windows only."
    )

# Phase 11 Wave 4 — wizard-time selectors (permissions + window enumeration).
# Imported lazily by callers as ``from vibemix.platform import permissions``
# or ``from vibemix.platform import windows`` — NOT eagerly here so that
# test runs and the live-runtime path (which doesn't need either) skip the
# pyobjc-framework-AVFoundation import on darwin.

__all__ = [
    "AudioBackend",
    "AudioCallback",
    "AudioImpl",
    "AudioMacOS",
    "AudioStream",
    "CapturedFrame",
    "Kind",
    "MidiBackend",
    "MidiImpl",
    "MidiMacOS",
    "MidiMessage",
    "MidiPort",
    "NowPlayingSnapshot",
    "ScreenBackend",
    "ScreenImpl",
    "ScreenMacOS",
    "TrackImpl",
    "TrackInfoBackend",
    "TrackMacOS",
    "WindowBounds",
    "assert_device_sample_rate",
]
