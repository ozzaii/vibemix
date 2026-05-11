# SPDX-License-Identifier: Apache-2.0
"""Windows-only live MIDI smoke tests — Phase 20 fills the body.

Skipped on every platform except win32. Phase 20's GitHub Actions matrix
runs these on ``windows-latest``; Kaan's fresh-Windows-machine rehearsal
validates against a real DDJ-FLX4 plugged in via USB.

Mocked counterpart lives in ``tests/test_midi_windows.py`` and runs
everywhere — these live tests cover the "real OS, real device" gap that
mocks cannot.
"""

from __future__ import annotations

import sys

import pytest

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Windows only")


@pytest.mark.windows_only
def test_midi_windows_opens_real_ddj_flx4():
    """Smoke: enumerate MIDI input ports on a real Windows host with the
    DDJ-FLX4 plugged in; assert at least one port name contains 'DDJ-FLX4'.

    Phase 20 rehearsal runs this on Kaan's Windows machine (and the CI
    matrix) — neither path is wired in Wave 4.
    """
    from vibemix.platform._midi_windows import MidiWindows

    backend = MidiWindows()
    ports = backend.list_input_ports()
    assert any("DDJ-FLX4" in p for p in ports), f"no FLX4 in {ports}"


@pytest.mark.windows_only
def test_midi_windows_listener_thread_starts_and_stops():
    """Smoke: spawn the listener thread against a real DDJ-FLX4, let it
    run for ~1s, then signal stop. Asserts the thread terminates within
    a few seconds and at least one connection attempt succeeded.

    Phase 20 rehearsal — wire in once Kaan has the Windows box on his desk.
    """
    import threading
    import time

    from vibemix.platform._midi_windows import MidiWindows

    backend = MidiWindows()
    stop_event = threading.Event()
    t = backend.start_listener_thread(stop_event)
    time.sleep(1.0)
    stop_event.set()
    t.join(timeout=3.0)
    assert not t.is_alive()
    assert backend.controller_state.is_connected()
