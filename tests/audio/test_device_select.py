# SPDX-License-Identifier: Apache-2.0
"""Unit tests for vibemix.audio.device_select — master-capture input selection.

Release-blocking regression (2026-05-24): the co-host listened to the DJ
controller's built-in soundcard (Pioneer DDJ-FLX4) instead of the master
output captured on BlackHole 2ch. These tests pin the contract: from a real
rig's device list, selection MUST land on BlackHole 2ch and NEVER on the
controller or a microphone.
"""

from __future__ import annotations

import pytest

from vibemix.audio.device_select import (
    MasterCaptureNotFoundError,
    find_device_index,
    is_controller_device,
    is_mic_device,
    select_master_input,
)


def _in(name: str, ich: int = 2, och: int = 0) -> dict:
    return {"name": name, "max_input_channels": ich, "max_output_channels": och}


# The founder's confirmed device list (from the bug report), with realistic
# CoreAudio enumeration order — the controller / aggregates often enumerate
# BEFORE BlackHole, which is exactly what broke the naive first-match scan.
FOUNDER_DEVICES = [
    _in("MacBook Pro Microphone", ich=1, och=0),
    _in("MacBook Pro Speakers", ich=0, och=2),
    _in("DDJ-FLX4", ich=4, och=4),  # controller soundcard — input AND output
    _in("rekordbox Aggregate Device", ich=4, och=4),
    _in("HEADPHONEMG", ich=0, och=2),
    _in("Multi-Output Device", ich=0, och=2),
    _in("AIDJ", ich=2, och=2),
    _in("AI Capture", ich=2, och=2),
    _in("BlackHole 2ch", ich=2, och=0),
    _in("BlackHole 16ch", ich=16, och=0),
]


def test_selects_blackhole_2ch_from_founder_rig() -> None:
    """The whole point: BlackHole 2ch is chosen, even though it enumerates last."""
    idx = select_master_input(FOUNDER_DEVICES)
    assert FOUNDER_DEVICES[idx]["name"] == "BlackHole 2ch"


def test_never_selects_the_ddj_flx4_controller() -> None:
    """The exact founder failure: must not pick the DDJ-FLX4 controller soundcard."""
    idx = select_master_input(FOUNDER_DEVICES)
    assert "DDJ" not in FOUNDER_DEVICES[idx]["name"]
    assert "FLX" not in FOUNDER_DEVICES[idx]["name"].upper()


def test_never_selects_the_microphone() -> None:
    idx = select_master_input(FOUNDER_DEVICES)
    assert "Microphone" not in FOUNDER_DEVICES[idx]["name"]


def test_exact_2ch_preferred_over_16ch_variant() -> None:
    """Exact BlackHole 2ch wins over the 16ch variant regardless of order."""
    devices = [_in("BlackHole 16ch", ich=16), _in("BlackHole 2ch", ich=2)]
    idx = select_master_input(devices)
    assert devices[idx]["name"] == "BlackHole 2ch"


def test_falls_back_to_other_blackhole_variant_when_no_2ch() -> None:
    """A 16ch-only machine still captures (degraded but correct), never the controller."""
    devices = [_in("DDJ-FLX4", ich=4, och=4), _in("BlackHole 16ch", ich=16)]
    idx = select_master_input(devices)
    assert devices[idx]["name"] == "BlackHole 16ch"


def test_raises_when_no_blackhole_present_instead_of_grabbing_controller() -> None:
    """No BlackHole → raise with install guidance; do NOT fall back to any input.

    This is the core safety property: the old code would have returned the
    controller here. We must refuse and surface the install affordance.
    """
    devices = [
        _in("MacBook Pro Microphone", ich=1),
        _in("DDJ-FLX4", ich=4, och=4),
        _in("AI Capture", ich=2, och=2),
    ]
    with pytest.raises(MasterCaptureNotFoundError) as exc:
        select_master_input(devices)
    msg = str(exc.value)
    assert "BlackHole" in msg
    assert "blackhole-2ch" in msg  # install hint present
    # The candidate list should still surface what WAS available for debugging.
    assert "DDJ-FLX4" in msg


def test_does_not_select_blackhole_output_only_listing() -> None:
    """An output-only BlackHole listing (max_input_channels == 0) is skipped."""
    devices = [_in("BlackHole 2ch", ich=0, och=2)]
    with pytest.raises(MasterCaptureNotFoundError):
        select_master_input(devices)


def test_is_controller_device_matches_known_tokens() -> None:
    for name in ("DDJ-FLX4", "Pioneer DDJ", "rekordbox Aggregate Device", "Traktor Kontrol S4"):
        assert is_controller_device(name) is True
    assert is_controller_device("BlackHole 2ch") is False


def test_is_mic_device_matches_known_tokens() -> None:
    for name in ("MacBook Pro Microphone", "AirPods Pro", "Logitech Webcam Mic"):
        assert is_mic_device(name) is True
    assert is_mic_device("BlackHole 2ch") is False


# ----- find_device_index (output / mic path) keeps plain substring semantics -----


def test_find_device_index_output_substring() -> None:
    devices = [_in("BlackHole 2ch", ich=2, och=0), _in("MacBook Pro Speakers", ich=0, och=2)]
    assert find_device_index(devices, "MacBook Pro Speakers", "output") == 1


def test_find_device_index_raises_on_miss() -> None:
    devices = [_in("MacBook Pro Speakers", ich=0, och=2)]
    with pytest.raises(RuntimeError, match="nonexistent"):
        find_device_index(devices, "nonexistent", "output")
