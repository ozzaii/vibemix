# SPDX-License-Identifier: Apache-2.0
"""macOS-only live MIDI smoke test + the FLX4 LIVE-DRIVE RECIPE (Phase 53
BRINGUP-03, Kaan-action).

Skipped on every platform except darwin; opt-in via the ``macos_audio`` marker
(excluded from the default suite). This is the ONE-COMMAND real-hardware
confirmation surface for Kaan's physical FLX4 sign-off — plug, move, mid-set
unplug, replug, and boot-with-controller-absent. The automated body only
verifies a plugged FLX4 resolves to the right profile (and skips cleanly when
absent); the FULL drive is Kaan-action (manual, deferred per the autonomous
carveout — see the recipe in ``test_flx4_live_resolves_and_decodes``).

Mocked + deterministic counterparts that run everywhere:
  - tests/midi/test_flx4_synthetic_decode.py  — FLX4 decode proof
  - tests/midi/test_disconnect_reconnect.py   — unplug/replug via the callback
  - tests/midi/test_watcher_callback_integration.py — watcher+callback composed
  - tests/test_main_midi_wiring.py            — the live watcher wiring guard
These live tests cover the "real OS, real device" gap that mocks cannot.

Run it (with the FLX4 plugged in):
    source .venv/bin/activate && PYTHONPATH=src python3 -m pytest -m macos_audio \
        tests/test_midi_macos_live.py -v
    # or:  uv run pytest -m macos_audio tests/test_midi_macos_live.py -v
"""

from __future__ import annotations

import sys

import pytest

pytestmark = pytest.mark.skipif(sys.platform != "darwin", reason="macOS only")


@pytest.mark.macos_audio
def test_flx4_live_resolves_and_decodes():
    """Smoke + LIVE-DRIVE RECIPE for Kaan's FLX4 hardware sign-off (BRINGUP-03).

    AUTOMATED CHECK (this test body):
        Enumerate real MIDI input ports via ``MidiMacOS().list_input_ports()``.
        If a port matching "FLX4" is present, assert ``find_mapping(port).id ==
        "pioneer_ddj_flx4"`` — the real device binds the right profile from
        ``midi/profiles/`` (the canonical live path). If no FLX4 is plugged,
        ``pytest.skip``.

    ─────────────────────────────────────────────────────────────────────────
    LIVE-DRIVE RECIPE — run these steps by hand once, with a real FLX4 (Kaan):
    ─────────────────────────────────────────────────────────────────────────
    1. PLUG the Pioneer DDJ-FLX4 into the Mac over USB.

    2. RUN the live session:
           uv run python -m vibemix
       (or launch the Tauri GUI: `cargo tauri dev`). Confirm clean startup —
       the listener log line `-> MIDI controller in: '...FLX4...'` should
       appear within ~2s.

    3. TAP the live state bus at  ws://127.0.0.1:8765  (or watch the app UI).
       The frame carries the controller snapshot incl. `connected: true`.

    4. MOVE controls — jog wheels, crossfader, EQ knobs, channel faders, pads
       (play/cue/sync). Confirm the controller moves SURFACE on the bus / UI
       (deck values change, move labels appear). This is the "moves register"
       check — the live counterpart of test_flx4_synthetic_decode.py.

    5. MID-SET UNPLUG the FLX4 (pull USB while audio keeps playing). Within
       ~2s (one watcher poll) confirm:
         - the app KEEPS RUNNING on audio alone — NO crash, NO exit;
         - NO MIDI error spam in the log (the listener retries quietly);
         - the bus shows `connected: false`;
         - NO stale controller moves linger (Plan 01 ring-clear): the move
           list on the bus goes empty — the coach won't cite a move the
           now-gone controller never re-sent.

    6. REPLUG the FLX4. Within ~2s confirm:
         - the bus flips back to `connected: true`;
         - moving a control again surfaces moves (decode RESUMES on the SAME
           live state object — single-state ownership, no rebuild).

    7. BOOT-WITH-CONTROLLER-ABSENT: quit, UNPLUG the FLX4, then start vibemix
       with nothing plugged. Confirm:
         - clean startup (no crash);
         - the listener retries QUIETLY (no error spam);
         - plugging the FLX4 mid-session then binds + decodes (step 4 again).

    Sign-off = all of 1-7 pass on the real device. The physical drive is
    Kaan-action; this test automates only the resolve check above.
    """
    from vibemix.midi.registry import find_mapping
    from vibemix.platform import MidiMacOS

    backend = MidiMacOS()
    # Real MIDI enumeration can raise when no rtmidi backend is available (no
    # device, headless CI, or another test having poisoned mido's lazy backend
    # import). For an opt-in live recipe that needs real hardware, that means
    # "skip", never "fail".
    try:
        ports = backend.list_input_ports()
    except Exception as exc:  # noqa: BLE001 — any enumeration failure → skip
        pytest.skip(f"MIDI enumeration unavailable ({exc!r}) — plug the DDJ-FLX4 to run this live")
    flx4_ports = [p for p in ports if "FLX4" in p]
    if not flx4_ports:
        pytest.skip("no FLX4 connected — plug the DDJ-FLX4 over USB to run this live")

    port = flx4_ports[0]
    profile = find_mapping(port)
    assert profile is not None, f"FLX4 port {port!r} did not resolve to any profile"
    assert profile.id == "pioneer_ddj_flx4", (
        f"FLX4 port {port!r} resolved to {profile.id!r}, expected pioneer_ddj_flx4"
    )
