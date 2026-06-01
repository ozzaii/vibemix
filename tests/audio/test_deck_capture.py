# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import numpy as np
import pytest

from vibemix.audio.deck_capture import (
    DeckAudioCapture,
    deck_audio_routing_from_env,
    rekordbox_deck_output_routing_hint,
)


def test_deck_audio_routing_defaults_to_stereo_global_capture(monkeypatch) -> None:
    monkeypatch.delenv("VIBEMIX_INPUT_CHANNELS", raising=False)
    monkeypatch.delenv("VIBEMIX_DECK_AUDIO_CHANNELS", raising=False)
    monkeypatch.delenv("VIBEMIX_MASTER_AUDIO_CHANNELS", raising=False)

    routing = deck_audio_routing_from_env(input_channels=2)

    assert routing.opened_channels == 2
    assert routing.master_channels == (0, 1)
    assert routing.deck_channels == {}
    assert routing.enabled is False
    assert routing.reason == "disabled"
    assert routing.context()["deck_audio_routing_source"] == "env"


def test_deck_audio_routing_enables_zero_based_deck_pairs(monkeypatch) -> None:
    monkeypatch.setenv("VIBEMIX_DECK_AUDIO_CHANNELS", "A=0,1;B=2,3")

    routing = deck_audio_routing_from_env(input_channels=16)

    assert routing.opened_channels == 4
    assert routing.master_channels == (0, 1, 2, 3)
    assert routing.deck_channels == {"A": (0, 1), "B": (2, 3)}
    assert routing.enabled is True
    assert routing.reason == "configured"


def test_rekordbox_deck_output_routing_hint_reads_external_deck_outputs(tmp_path) -> None:
    settings = tmp_path / "rekordbox3.settings"
    settings.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<SETTINGS>
  <VALUE name="audioDeviceManager_PerformanceMode_old">
    <DEVICESETUP audioOutputDeviceName="DDJ-FLX4" MixerMode_Is_Internal="1"
                 Date="1" OutputChannel_Deck0_L="0" OutputChannel_Deck0_R="1"
                 OutputChannel_Deck1_L="-1" OutputChannel_Deck1_R="-1"/>
  </VALUE>
  <VALUE name="audioDeviceManager_PerformanceMode_aggregate">
    <DEVICESETUP audioOutputDeviceName="Aggregate Device" MixerMode_Is_Internal="0"
                 Date="2" OutputChannel_Deck0_L="0" OutputChannel_Deck0_R="1"
                 OutputChannel_Deck1_L="2" OutputChannel_Deck1_R="3"
                 OutputChannel_Deck2_L="4" OutputChannel_Deck2_R="5"/>
  </VALUE>
</SETTINGS>
""",
        encoding="utf-8",
    )

    hint = rekordbox_deck_output_routing_hint(
        settings_paths=(settings,),
        capture_device_name="BlackHole 16ch",
        input_channels=16,
    )

    assert hint is not None
    assert hint["source"] == "rekordbox_settings"
    assert hint["settings_entry"] == "audioDeviceManager_PerformanceMode_aggregate"
    assert hint["output_device"] == "Aggregate_Device"
    assert hint["mixer_mode"] == "external"
    assert hint["deck_channels"] == {"A": (0, 1), "B": (2, 3)}
    assert hint["fits_input_channels"] is True
    assert hint["rule"] == "rekordbox_output_routing_hint_not_live_audio_proof"


def test_rekordbox_current_output_blocks_stale_external_deck_hint(tmp_path) -> None:
    settings = tmp_path / "rekordbox3.settings"
    settings.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<SETTINGS>
  <VALUE name="audioDeviceManager">
    <DEVICESETUP audioOutputDeviceName="Multi-Output Device" MixerMode_Is_Internal="1"
                 Date="20" OutputChannel_Master_L="0" OutputChannel_Master_R="1"/>
  </VALUE>
  <VALUE name="audioDeviceManager_PerformanceMode_aggregate">
    <DEVICESETUP audioOutputDeviceName="Aggregate Device" MixerMode_Is_Internal="0"
                 Date="10" OutputChannel_Deck0_L="0" OutputChannel_Deck0_R="1"
                 OutputChannel_Deck1_L="2" OutputChannel_Deck1_R="3"/>
  </VALUE>
</SETTINGS>
""",
        encoding="utf-8",
    )

    hint = rekordbox_deck_output_routing_hint(
        settings_paths=(settings,),
        capture_device_name="BlackHole 16ch",
        input_channels=16,
    )

    assert hint is None


def test_rekordbox_active_settings_block_legacy_current_output_hint(tmp_path) -> None:
    active = tmp_path / "rekordbox6.settings"
    active.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<SETTINGS>
  <VALUE name="audioDeviceManager">
    <DEVICESETUP audioOutputDeviceName="Multi-Output Device" MixerMode_Is_Internal="1"
                 Date="30" OutputChannel_Master_L="0" OutputChannel_Master_R="1"/>
  </VALUE>
</SETTINGS>
""",
        encoding="utf-8",
    )
    legacy = tmp_path / "rekordbox.settings"
    legacy.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<SETTINGS>
  <VALUE name="audioDeviceManager">
    <DEVICESETUP audioOutputDeviceName="DDJ-FLX4" MixerMode_Is_Internal="1"
                 Date="20" OutputChannel_Master_L="0" OutputChannel_Master_R="1"/>
  </VALUE>
  <VALUE name="audioDeviceManager_PerformanceMode_0">
    <DEVICESETUP audioOutputDeviceName="DDJ-FLX4" MixerMode_Is_Internal="1"
                 Date="10" OutputChannel_Deck0_L="0" OutputChannel_Deck0_R="1"
                 OutputChannel_Deck1_L="2" OutputChannel_Deck1_R="3"/>
  </VALUE>
</SETTINGS>
""",
        encoding="utf-8",
    )

    hint = rekordbox_deck_output_routing_hint(
        settings_paths=(active, legacy),
        capture_device_name="BlackHole 16ch",
        input_channels=16,
    )

    assert hint is None


def test_rekordbox_current_output_allows_matching_external_deck_hint(tmp_path) -> None:
    settings = tmp_path / "rekordbox3.settings"
    settings.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<SETTINGS>
  <VALUE name="audioDeviceManager">
    <DEVICESETUP audioOutputDeviceName="Aggregate Device" MixerMode_Is_Internal="0"
                 Date="20" OutputChannel_Deck0_L="0" OutputChannel_Deck0_R="1"
                 OutputChannel_Deck1_L="2" OutputChannel_Deck1_R="3"/>
  </VALUE>
  <VALUE name="audioDeviceManager_PerformanceMode_blackhole">
    <DEVICESETUP audioOutputDeviceName="BlackHole 16ch" MixerMode_Is_Internal="0"
                 Date="30" OutputChannel_Deck0_L="0" OutputChannel_Deck0_R="1"
                 OutputChannel_Deck1_L="2" OutputChannel_Deck1_R="3"/>
  </VALUE>
</SETTINGS>
""",
        encoding="utf-8",
    )

    hint = rekordbox_deck_output_routing_hint(
        settings_paths=(settings,),
        capture_device_name="BlackHole 16ch",
        input_channels=16,
    )

    assert hint is not None
    assert hint["settings_entry"] == "audioDeviceManager"
    assert hint["output_device"] == "Aggregate_Device"
    assert hint["deck_channels"] == {"A": (0, 1), "B": (2, 3)}


def test_global_per_deck_default_ignores_stale_external_hint_when_current_is_stereo(
    monkeypatch, tmp_path
) -> None:
    settings = tmp_path / "rekordbox3.settings"
    settings.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<SETTINGS>
  <VALUE name="audioDeviceManager">
    <DEVICESETUP audioOutputDeviceName="Multi-Output Device" MixerMode_Is_Internal="1"
                 Date="20" OutputChannel_Master_L="0" OutputChannel_Master_R="1"/>
  </VALUE>
  <VALUE name="audioDeviceManager_PerformanceMode_aggregate">
    <DEVICESETUP audioOutputDeviceName="Aggregate Device" MixerMode_Is_Internal="0"
                 Date="10" OutputChannel_Deck0_L="0" OutputChannel_Deck0_R="1"
                 OutputChannel_Deck1_L="2" OutputChannel_Deck1_R="3"/>
  </VALUE>
</SETTINGS>
""",
        encoding="utf-8",
    )
    monkeypatch.delenv("VIBEMIX_DECK_AUDIO_CHANNELS", raising=False)
    monkeypatch.delenv("VIBEMIX_INPUT_CHANNELS", raising=False)
    monkeypatch.delenv("VIBEMIX_MASTER_AUDIO_CHANNELS", raising=False)

    routing = deck_audio_routing_from_env(
        input_channels=16,
        capture_device_name="BlackHole 16ch",
        rekordbox_settings_paths=(settings,),
    )

    assert routing.enabled is False
    assert routing.deck_channels == {}
    assert routing.reason == "disabled"
    assert routing.source == "env"


def test_deck_audio_routing_auto_uses_rekordbox_hint_when_requested(monkeypatch, tmp_path) -> None:
    settings = tmp_path / "rekordbox3.settings"
    settings.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<SETTINGS>
  <VALUE name="audioDeviceManager_PerformanceMode_aggregate">
    <DEVICESETUP audioOutputDeviceName="Aggregate Device" MixerMode_Is_Internal="0"
                 Date="2" OutputChannel_Deck0_L="0" OutputChannel_Deck0_R="1"
                 OutputChannel_Deck1_L="2" OutputChannel_Deck1_R="3"/>
  </VALUE>
</SETTINGS>
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("VIBEMIX_DECK_AUDIO_CHANNELS", "auto")
    monkeypatch.delenv("VIBEMIX_INPUT_CHANNELS", raising=False)
    monkeypatch.delenv("VIBEMIX_MASTER_AUDIO_CHANNELS", raising=False)

    routing = deck_audio_routing_from_env(
        input_channels=16,
        capture_device_name="BlackHole 16ch",
        rekordbox_settings_paths=(settings,),
    )

    assert routing.opened_channels == 4
    assert routing.master_channels == (0, 1, 2, 3)
    assert routing.deck_channels == {"A": (0, 1), "B": (2, 3)}
    assert routing.enabled is True
    assert routing.reason == "rekordbox_settings_auto"
    assert routing.source == "rekordbox_settings"
    context = routing.context()
    assert context["deck_audio_routing_source"] == "rekordbox_settings"
    assert "rekordbox_deck_routing_hint[" in context["deck_audio_routing_hint"]
    assert "deck_outputs=A:0,1+B:2,3" in context["deck_audio_routing_hint"]


def test_deck_audio_capture_auto_rekordbox_map_requires_both_pairs_live(
    monkeypatch, tmp_path
) -> None:
    settings = tmp_path / "rekordbox3.settings"
    settings.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<SETTINGS>
  <VALUE name="audioDeviceManager_PerformanceMode_aggregate">
    <DEVICESETUP audioOutputDeviceName="Aggregate Device" MixerMode_Is_Internal="0"
                 Date="2" OutputChannel_Deck0_L="0" OutputChannel_Deck0_R="1"
                 OutputChannel_Deck1_L="2" OutputChannel_Deck1_R="3"/>
  </VALUE>
</SETTINGS>
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("VIBEMIX_DECK_AUDIO_CHANNELS", "auto")
    monkeypatch.delenv("VIBEMIX_INPUT_CHANNELS", raising=False)
    monkeypatch.delenv("VIBEMIX_MASTER_AUDIO_CHANNELS", raising=False)
    routing = deck_audio_routing_from_env(
        input_channels=16,
        capture_device_name="BlackHole 16ch",
        rekordbox_settings_paths=(settings,),
    )
    capture = DeckAudioCapture(routing, seconds=1.0)
    master_only_on_first_pair = np.zeros((480, 4), dtype=np.float32)
    master_only_on_first_pair[:, 0] = 0.2
    master_only_on_first_pair[:, 1] = 0.2

    capture.process(master_only_on_first_pair, source_sr=48000)
    context = capture.context()

    assert context["deck_audio_capture_configured"] is True
    assert context["deck_audio_capture_enabled"] is False
    assert context["deck_audio_capture_verified"] is False
    assert context["deck_audio_capture_reason"] == "deck_pair_capture_unverified"
    assert context["deck_audio_active_sides_seen"] == "A"
    assert context["deck_audio_rms"]["A"] == pytest.approx(0.2)
    assert context["deck_audio_rms"]["B"] == pytest.approx(0.0)

    deck_b_on_second_pair = np.zeros((480, 4), dtype=np.float32)
    deck_b_on_second_pair[:, 2] = 0.3
    deck_b_on_second_pair[:, 3] = 0.3
    capture.process(deck_b_on_second_pair, source_sr=48000)
    context = capture.context()

    assert context["deck_audio_capture_enabled"] is True
    assert context["deck_audio_capture_verified"] is True
    assert context["deck_audio_active_sides_seen"] == "A,B"


def test_deck_audio_capture_manual_map_stays_operator_trusted(monkeypatch) -> None:
    monkeypatch.setenv("VIBEMIX_DECK_AUDIO_CHANNELS", "A=0,1;B=2,3")
    routing = deck_audio_routing_from_env(input_channels=4)
    capture = DeckAudioCapture(routing, seconds=1.0)
    indata = np.zeros((480, 4), dtype=np.float32)
    indata[:, 0] = 0.2
    indata[:, 1] = 0.2

    capture.process(indata, source_sr=48000)
    context = capture.context()

    assert context["deck_audio_capture_configured"] is True
    assert context["deck_audio_capture_enabled"] is True
    assert context["deck_audio_capture_verified"] is True
    assert context["deck_audio_active_sides_seen"] == "A"


def test_deck_audio_routing_auto_reports_too_narrow_capture_device(
    monkeypatch, tmp_path
) -> None:
    settings = tmp_path / "rekordbox3.settings"
    settings.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<SETTINGS>
  <VALUE name="audioDeviceManager_PerformanceMode_aggregate">
    <DEVICESETUP audioOutputDeviceName="Aggregate Device" MixerMode_Is_Internal="0"
                 Date="2" OutputChannel_Deck0_L="0" OutputChannel_Deck0_R="1"
                 OutputChannel_Deck1_L="2" OutputChannel_Deck1_R="3"/>
  </VALUE>
</SETTINGS>
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("VIBEMIX_DECK_AUDIO_CHANNELS", "auto")
    monkeypatch.delenv("VIBEMIX_INPUT_CHANNELS", raising=False)
    monkeypatch.delenv("VIBEMIX_MASTER_AUDIO_CHANNELS", raising=False)

    routing = deck_audio_routing_from_env(
        input_channels=2,
        capture_device_name="BlackHole 2ch",
        rekordbox_settings_paths=(settings,),
    )

    assert routing.opened_channels == 2
    assert routing.required_opened_channels == 4
    assert routing.deck_channels == {}
    assert routing.enabled is False
    assert routing.reason == "capture_device_too_few_channels"
    context = routing.context()
    assert context["deck_audio_capture_enabled"] is False
    assert context["deck_audio_capture_reason"] == "capture_device_too_few_channels"
    assert context["deck_audio_required_opened_channels"] == 4
    assert "deck_outputs=A:0,1+B:2,3" in context["deck_audio_routing_hint"]


_EXTERNAL_AGGREGATE_SETTINGS = """<?xml version="1.0" encoding="UTF-8"?>
<SETTINGS>
  <VALUE name="audioDeviceManager_PerformanceMode_aggregate">
    <DEVICESETUP audioOutputDeviceName="Aggregate Device" MixerMode_Is_Internal="0"
                 Date="2" OutputChannel_Deck0_L="0" OutputChannel_Deck0_R="1"
                 OutputChannel_Deck1_L="2" OutputChannel_Deck1_R="3"/>
  </VALUE>
</SETTINGS>
"""


def test_rekordbox_external_mixer_auto_enables_per_deck_globally(monkeypatch, tmp_path) -> None:
    # Kaan 2026-05-30: "it should be global — nobody will set this [env var]."
    # A high-confidence rekordbox external-mixer config (both decks mapped, fits
    # the capture device) auto-enables per-deck grounding with NO env var set.
    # This REVERSES the prior opt-in-only contract by explicit owner decision.
    settings = tmp_path / "rekordbox3.settings"
    settings.write_text(_EXTERNAL_AGGREGATE_SETTINGS, encoding="utf-8")
    monkeypatch.delenv("VIBEMIX_DECK_AUDIO_CHANNELS", raising=False)
    monkeypatch.delenv("VIBEMIX_INPUT_CHANNELS", raising=False)
    monkeypatch.delenv("VIBEMIX_MASTER_AUDIO_CHANNELS", raising=False)

    routing = deck_audio_routing_from_env(
        input_channels=16,
        capture_device_name="BlackHole 16ch",
        rekordbox_settings_paths=(settings,),
    )

    assert routing.enabled is True
    assert routing.deck_channels == {"A": (0, 1), "B": (2, 3)}
    assert routing.reason == "rekordbox_settings_auto"
    assert routing.source == "rekordbox_settings"


def test_explicit_off_overrides_global_per_deck_default(monkeypatch, tmp_path) -> None:
    # The escape hatch: an explicit non-auto env value forces master-only even
    # when rekordbox advertises an external-mixer hint (power-user opt-out).
    settings = tmp_path / "rekordbox3.settings"
    settings.write_text(_EXTERNAL_AGGREGATE_SETTINGS, encoding="utf-8")
    monkeypatch.setenv("VIBEMIX_DECK_AUDIO_CHANNELS", "off")
    monkeypatch.delenv("VIBEMIX_INPUT_CHANNELS", raising=False)
    monkeypatch.delenv("VIBEMIX_MASTER_AUDIO_CHANNELS", raising=False)

    routing = deck_audio_routing_from_env(
        input_channels=16,
        capture_device_name="BlackHole 16ch",
        rekordbox_settings_paths=(settings,),
    )

    assert routing.enabled is False
    assert routing.deck_channels == {}


def test_global_per_deck_default_respects_capture_channel_fit(monkeypatch, tmp_path) -> None:
    # Global default still never opens more channels than the device exposes:
    # a 4-channel deck map on a 2-channel capture device stays master-only.
    settings = tmp_path / "rekordbox3.settings"
    settings.write_text(_EXTERNAL_AGGREGATE_SETTINGS, encoding="utf-8")
    monkeypatch.delenv("VIBEMIX_DECK_AUDIO_CHANNELS", raising=False)
    monkeypatch.delenv("VIBEMIX_INPUT_CHANNELS", raising=False)
    monkeypatch.delenv("VIBEMIX_MASTER_AUDIO_CHANNELS", raising=False)

    routing = deck_audio_routing_from_env(
        input_channels=2,
        capture_device_name="BlackHole 2ch",
        rekordbox_settings_paths=(settings,),
    )

    assert routing.enabled is False


def test_global_per_deck_default_signals_device_upgrade_when_narrow(monkeypatch, tmp_path) -> None:
    # The live-rig gap (2026-05-30): with NO env var, the selected capture device
    # boots as BlackHole *2ch* — too narrow for the 4-channel external-mixer map.
    # The global default must still report `capture_device_too_few_channels` (the
    # signal __main__ keys on to swap 2ch -> 16ch) rather than going silently
    # master-only "disabled" — otherwise per-deck grounding stays dark forever for
    # every real rig with a default 2ch input. A concrete capture_device_name is
    # what marks the device as upgradeable (None stays the plain-stereo default).
    settings = tmp_path / "rekordbox3.settings"
    settings.write_text(_EXTERNAL_AGGREGATE_SETTINGS, encoding="utf-8")
    monkeypatch.delenv("VIBEMIX_DECK_AUDIO_CHANNELS", raising=False)
    monkeypatch.delenv("VIBEMIX_INPUT_CHANNELS", raising=False)
    monkeypatch.delenv("VIBEMIX_MASTER_AUDIO_CHANNELS", raising=False)

    routing = deck_audio_routing_from_env(
        input_channels=2,
        capture_device_name="BlackHole 2ch",
        rekordbox_settings_paths=(settings,),
    )

    assert routing.enabled is False
    assert routing.reason == "capture_device_too_few_channels"
    assert routing.required_opened_channels == 4
    assert routing.source == "rekordbox_settings"


def test_deck_audio_capture_downmixes_master_and_pushes_deck_rings(monkeypatch) -> None:
    monkeypatch.setenv("VIBEMIX_DECK_AUDIO_CHANNELS", "A=0,1;B=2,3")
    routing = deck_audio_routing_from_env(input_channels=4)
    capture = DeckAudioCapture(routing, seconds=1.0)
    indata = np.zeros((480, 4), dtype=np.float32)
    indata[:, 0] = 0.2
    indata[:, 1] = 0.2
    indata[:, 2] = 0.6
    indata[:, 3] = 0.6

    frame = capture.process(indata, source_sr=48000)

    assert frame.master_mono.shape == (480,)
    assert np.allclose(frame.master_mono, 0.4)
    assert frame.passthrough_stereo.shape == (480, 2)
    assert np.allclose(frame.passthrough_stereo[:, 0], 0.4)
    assert frame.deck_rms["A"] == pytest.approx(0.2)
    assert frame.deck_rms["B"] == pytest.approx(0.6)
    assert frame.deck_features["A"]["activity"] == "active"
    assert frame.deck_features["A"]["rms"] == pytest.approx(0.2)
    assert frame.deck_features["B"]["peak"] == pytest.approx(0.6)
    assert frame.deck_deltas == {}
    assert capture.buffers["A"].snapshot(160).size == 160
    assert capture.buffers["B"].snapshot(160).size == 160
    context = capture.context()
    assert context["deck_audio_capture_enabled"] is True
    assert context["deck_audio_features"]["A"]["activity"] == "active"
    assert context["deck_audio_features"]["B"]["rms"] == pytest.approx(0.6)

    indata[:, 0] = 0.4
    indata[:, 1] = 0.4
    indata[:, 2] = 0.3
    indata[:, 3] = 0.3
    next_frame = capture.process(indata, source_sr=48000)

    assert "rms_rose_100pct_strong" in next_frame.deck_deltas["A"]
    assert "rms_fell_50pct_strong" in next_frame.deck_deltas["B"]
    context = capture.context()
    assert context["deck_audio_deltas"]["A"][0] == "rms_rose_100pct_strong"
    assert context["deck_audio_deltas"]["B"][0] == "rms_fell_50pct_strong"


def test_deck_audio_capture_context_includes_pre_current_windows(monkeypatch) -> None:
    monkeypatch.setenv("VIBEMIX_DECK_AUDIO_CHANNELS", "A=0,1;B=2,3")
    routing = deck_audio_routing_from_env(input_channels=4)
    capture = DeckAudioCapture(routing, seconds=1.0)

    pre = np.zeros((48000, 4), dtype=np.float32)
    pre[:, 0] = 0.2
    pre[:, 1] = 0.2
    pre[:, 2] = 0.6
    pre[:, 3] = 0.6
    current = np.zeros((48000, 4), dtype=np.float32)
    current[:, 0] = 0.4
    current[:, 1] = 0.4
    current[:, 2] = 0.3
    current[:, 3] = 0.3

    for _ in range(6):
        capture.process(pre, source_sr=48000)
    capture.process(current, source_sr=48000)

    windows = capture.context()["deck_audio_windows"]

    assert windows["pre_s"] == [-6.0, -1.0]
    assert windows["current_s"] == [-1.0, 0.0]
    assert windows["A"]["pre"]["rms"] == pytest.approx(0.2)
    assert windows["A"]["current"]["rms"] == pytest.approx(0.4)
    assert "rms_rose_100pct_strong" in windows["A"]["delta"]
    assert windows["B"]["pre"]["rms"] == pytest.approx(0.6)
    assert windows["B"]["current"]["rms"] == pytest.approx(0.3)
    assert "rms_fell_50pct_strong" in windows["B"]["delta"]
