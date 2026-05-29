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


def test_rekordbox_hint_is_context_only_without_auto_env(monkeypatch, tmp_path) -> None:
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
    monkeypatch.delenv("VIBEMIX_DECK_AUDIO_CHANNELS", raising=False)
    monkeypatch.delenv("VIBEMIX_INPUT_CHANNELS", raising=False)
    monkeypatch.delenv("VIBEMIX_MASTER_AUDIO_CHANNELS", raising=False)

    routing = deck_audio_routing_from_env(
        input_channels=16,
        capture_device_name="BlackHole 16ch",
        rekordbox_settings_paths=(settings,),
    )

    assert routing.enabled is False
    assert routing.reason == "disabled"
    assert routing.deck_channels == {}
    assert "rekordbox_deck_routing_hint[" in routing.context()["deck_audio_routing_hint"]


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
