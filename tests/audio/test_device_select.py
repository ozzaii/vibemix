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
    select_output_device,
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


# ----- select_output_device: graceful fallback so first launch never crashes ----
# Regression (2026-05-29): the live runtime hardcoded OUTPUT_DEVICE='MacBook Pro
# Speakers' and hard-failed on a miss → any non-MacBook Mac / external output /
# localized device name crashed first launch with a misleading 'install BlackHole'
# banner. select_output_device must always resolve to SOME output when one exists.


def test_output_happy_path_substring_parity() -> None:
    # When the configured name exists and nothing is persisted, behaves exactly
    # like the legacy find_device_index substring match (byte-identical index).
    idx = select_output_device(FOUNDER_DEVICES, fallback_name="MacBook Pro Speakers")
    assert idx == 1
    assert idx == find_device_index(FOUNDER_DEVICES, "MacBook Pro Speakers", "output")


def test_output_prefers_persisted_index_over_name() -> None:
    # The wizard-persisted output_device_id (an index) is the user's explicit
    # choice and wins over the fallback name.
    idx = select_output_device(
        FOUNDER_DEVICES, preferred_index=4, fallback_name="MacBook Pro Speakers"
    )
    assert idx == 4  # HEADPHONEMG (output-capable)


def test_output_persisted_index_invalid_falls_through_to_name() -> None:
    # Out-of-range / non-output persisted index is ignored (device unplugged
    # since the wizard ran) → fall through to the name.
    assert (
        select_output_device(
            FOUNDER_DEVICES, preferred_index=999, fallback_name="MacBook Pro Speakers"
        )
        == 1
    )
    # index 8 is BlackHole 2ch — input-only, not output-capable → ignored.
    assert (
        select_output_device(
            FOUNDER_DEVICES, preferred_index=8, fallback_name="MacBook Pro Speakers"
        )
        == 1
    )


def test_output_name_miss_falls_back_to_os_default() -> None:
    # The crux of the first-launch fix: 'MacBook Pro Speakers' absent (Mac mini /
    # localized macOS), so fall back to the OS default output index, NOT a crash.
    devices = [_in("Mac mini Speakers", ich=0, och=2), _in("Studio Display Speakers", ich=0, och=2)]
    idx = select_output_device(devices, fallback_name="MacBook Pro Speakers", default_index=1)
    assert idx == 1


def test_output_no_default_falls_back_to_first_real_output() -> None:
    # No name match and no OS default → first non-loopback, non-controller output.
    # BlackHole + the controller must be SKIPPED (never route AI voice into them).
    devices = [
        _in("BlackHole 2ch", ich=2, och=2),  # loopback, output-capable but skip
        _in("DDJ-FLX4", ich=4, och=4),  # controller, skip
        _in("External DAC", ich=0, och=2),  # real output → chosen
    ]
    assert select_output_device(devices, fallback_name="nope") == 2


def test_output_last_resort_returns_any_output_even_loopback() -> None:
    # If the ONLY output is BlackHole, route to it rather than crash (better a
    # working-but-loopback voice path than no boot).
    devices = [_in("BlackHole 2ch", ich=2, och=2)]
    assert select_output_device(devices, fallback_name="nope") == 0


def test_output_raises_only_when_no_output_device_at_all() -> None:
    devices = [_in("BlackHole 2ch", ich=2, och=0), _in("MacBook Pro Microphone", ich=1, och=0)]
    with pytest.raises(RuntimeError, match="No output-capable"):
        select_output_device(devices, fallback_name="MacBook Pro Speakers")


def test_output_stale_persisted_index_onto_blackhole_is_rejected() -> None:
    # Anti-feedback-loop hardening: output_device_id is a positional index that
    # reorders on plug/unplug. A stale index landing on a BlackHole OUTPUT
    # variant must NOT be honored (routing AI voice into the master capture =
    # the co-host hears itself). Falls through to the real output instead.
    devices = [
        _in("BlackHole 2ch", ich=2, och=2),  # loopback, output-capable
        _in("MacBook Pro Speakers", ich=0, och=2),
    ]
    assert select_output_device(devices, preferred_index=0, fallback_name="MacBook Pro Speakers") == 1


def test_output_stale_persisted_index_onto_aggregate_is_rejected() -> None:
    # Real founder rig regression (2026-06-01): output_device_id=5 survived
    # plug/unplug, then index 5 became "rekordbox Aggregate Device". PortAudio
    # hung opening it before the websocket bound. Fall through to real speakers.
    devices = [
        _in("DDJ-FLX4", ich=2, och=4),
        _in("MacBook Pro Speakers", ich=0, och=2),
        _in("rekordbox Aggregate Device", ich=2, och=6),
    ]
    assert select_output_device(devices, preferred_index=2, fallback_name="MacBook Pro Speakers") == 1


def test_output_os_default_onto_blackhole_is_rejected() -> None:
    # Same guard on the OS-default path: a BlackHole-inclusive default output is
    # skipped in favor of a real, non-loopback output.
    devices = [
        _in("BlackHole 2ch", ich=2, och=2),
        _in("External DAC", ich=0, och=2),
    ]
    assert select_output_device(devices, fallback_name="nope", default_index=0) == 1


def test_output_os_default_onto_multi_output_is_rejected() -> None:
    devices = [
        _in("Multi-Output Device", ich=0, och=2),
        _in("External DAC", ich=0, och=2),
    ]
    assert select_output_device(devices, fallback_name="nope", default_index=0) == 1


def test_output_persisted_controller_index_is_still_honored() -> None:
    # Controllers are NOT excluded from the explicit persisted choice — a user
    # may legitimately route the voice to a controller's headphone out, and a
    # controller output is not a capture-feedback loop.
    devices = [
        _in("MacBook Pro Speakers", ich=0, och=2),
        _in("DDJ-FLX4", ich=4, och=4),  # controller output
    ]
    assert select_output_device(devices, preferred_index=1, fallback_name="MacBook Pro Speakers") == 1
