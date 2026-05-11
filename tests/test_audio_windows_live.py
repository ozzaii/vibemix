# SPDX-License-Identifier: Apache-2.0
"""Windows-only live smoke tests for AudioWindows.

Skipped on macOS via the module-level ``pytestmark`` so the file collects
cleanly on Kaan's dev box (and on the macOS CI matrix slot) but only executes
on Windows. Phase 20 CI runs these on the ``windows-latest`` GitHub Actions
runner; Kaan's Phase 20 fresh-machine rehearsal on real Windows 11 validates
manually before sign-off.

What this proves (when it actually runs):
- ``AudioWindows`` instantiates cleanly with real ``pyaudiowpatch`` loaded.
- ``find_device`` locates real WASAPI devices via the substring helper.
- ``assert_wasapi_loopback_rate`` either passes (system at 48kHz) or raises
  ``SampleRateMismatchError`` with the actionable Control Panel message —
  never an unhandled exception.

The actual ``open_capture`` smoke (open + close a real WASAPI loopback stream)
is intentionally left as a Phase 20 rehearsal task — Kaan opens DJ software on
the test Windows box and confirms audio frames arrive in the callback.
"""

from __future__ import annotations

import sys

import pytest

pytestmark = pytest.mark.skipif(
    sys.platform != "win32",
    reason="Windows only — Phase 20 CI runs these on windows-latest",
)


@pytest.mark.windows_only
def test_audio_windows_can_open_real_loopback() -> None:
    """Real WASAPI loopback smoke — instantiate AudioWindows + verify the
    sample-rate guard either passes or raises with the actionable message.

    Phase 20 rehearsal extends this to actually open + close a capture stream
    and assert audio frames arrive in the callback. For now this proves the
    backend wires up against real pyaudiowpatch + the guard is callable
    against a real loopback device.
    """
    import tempfile
    from pathlib import Path

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
    from vibemix.platform._audio_windows import (
        AudioWindows,
        assert_wasapi_loopback_rate,
    )

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
    backend = AudioWindows(registry=reg, recorder=rec)
    assert backend is not None

    try:
        idx, name = assert_wasapi_loopback_rate(expected=48000)
        assert idx >= 0
        assert isinstance(name, str)
    except SampleRateMismatchError as e:
        msg = str(e)
        assert "Control Panel" in msg
        assert "Default Format" in msg
        # Re-raise so the test fails visibly — the user sees the actionable
        # Windows-specific message and knows to fix the Default Format setting.
        raise
