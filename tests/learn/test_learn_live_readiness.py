# SPDX-License-Identifier: Apache-2.0
"""Contracts for the Learn live-readiness preflight."""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
from pathlib import Path

from scripts import learn_live_readiness as readiness


class _FakeWebSocket:
    def __enter__(self):
        return self

    def __exit__(self, *_exc_info):
        return False


def test_matching_lines_and_names_are_case_insensitive() -> None:
    text = "MacBook Pro\nDDJ-FLX4 MIDI\nrekordbox Aggregate Device\n"

    assert readiness.matching_lines(text, ("flx",)) == ["DDJ-FLX4 MIDI"]
    assert readiness.matching_names(["BlackHole 2ch", "Speakers"], ("blackhole",)) == [
        "BlackHole 2ch"
    ]


def test_check_usb_controller_falls_back_to_audio_profiler_for_alphatheta_endpoint(
    monkeypatch,
) -> None:
    calls: list[tuple[str, ...]] = []

    def fake_run_command(cmd: list[str], **_kwargs):
        calls.append(tuple(cmd))
        if cmd == ["system_profiler", "SPUSBDataType"]:
            return readiness.CommandResult(ok=True, stdout="USB:\n  USB 3.1 Bus:\n")
        return readiness.CommandResult(
            ok=True,
            stdout="DDJ-FLX4:\n  Manufacturer: AlphaTheta Corporation\n",
        )

    monkeypatch.setattr(readiness.sys, "platform", "darwin")
    monkeypatch.setattr(readiness, "run_command", fake_run_command)

    check = readiness.check_usb_controller()

    assert check["ok"] is True
    assert check["source"] == "SPAudioDataType"
    assert check["controller_matches"] == [
        "DDJ-FLX4:",
        "Manufacturer: AlphaTheta Corporation",
    ]
    assert calls == [
        ("system_profiler", "SPUSBDataType"),
        ("system_profiler", "SPAudioDataType"),
    ]


def test_check_socket_uses_websocket_handshake(monkeypatch) -> None:
    calls: list[tuple[str, float]] = []

    def fake_open(url: str, *, timeout_s: float):
        calls.append((url, timeout_s))
        return _FakeWebSocket()

    monkeypatch.setattr(readiness, "_open_sidecar_websocket", fake_open)

    check = readiness.check_socket("ws://127.0.0.1:9876", timeout_s=0.2)

    assert check == {
        "ok": True,
        "url": "ws://127.0.0.1:9876",
        "host": "127.0.0.1",
        "port": 9876,
        "protocol": "websocket",
    }
    assert calls == [("ws://127.0.0.1:9876", 0.2)]


def test_check_socket_reports_websocket_handshake_failure(monkeypatch) -> None:
    def fake_open(_url: str, *, timeout_s: float):
        raise OSError(f"closed after {timeout_s}")

    monkeypatch.setattr(readiness, "_open_sidecar_websocket", fake_open)
    monkeypatch.setattr(readiness, "_socket_listener", lambda _port: None)

    check = readiness.check_socket("ws://127.0.0.1:9876", timeout_s=0.2)

    assert check["ok"] is False
    assert check["host"] == "127.0.0.1"
    assert check["port"] == 9876
    assert check["listener"] is None
    assert "closed after 0.2" in check["error"]


def test_check_socket_reports_foreign_listener_on_handshake_failure(monkeypatch) -> None:
    def fake_open(_url: str, *, timeout_s: float):
        raise OSError(f"server rejected WebSocket connection: HTTP 403 after {timeout_s}")

    monkeypatch.setattr(readiness, "_open_sidecar_websocket", fake_open)
    monkeypatch.setattr(
        readiness,
        "_socket_listener",
        lambda _port: {
            "command": "uvicorn",
            "pid": "85484",
            "raw": "uvicorn 85484 ozai 63u IPv4 TCP 127.0.0.1:8765 (LISTEN)",
        },
    )

    check = readiness.check_socket("ws://127.0.0.1:8765", timeout_s=0.2)

    assert check["ok"] is False
    assert check["listener"]["command"] == "uvicorn"
    assert check["listener"]["pid"] == "85484"


def test_audio_check_recognizes_loopback_and_dj_devices() -> None:
    check = readiness.check_audio_devices(
        sounddevice_names=[
            "MacBook Pro Speakers",
            "BlackHole 2ch",
            "rekordbox Aggregate Device",
            "DDJ-FLX4",
        ],
        profiler_output="",
    )

    assert check["ok"] is True
    assert check["loopback_present"] is True
    assert check["dj_audio_present"] is True
    assert check["controller_audio_present"] is True
    assert check["rekordbox_aggregate_present"] is True


def test_audio_route_check_accepts_loopback_default_output() -> None:
    check = readiness.check_audio_route(
        current_output="BlackHole 16ch",
        current_system="BlackHole 16ch",
        switch_available=True,
    )

    assert check["ok"] is True
    assert check["output_device"] == "BlackHole 16ch"
    assert check["loopback_matches"] == ["BlackHole 16ch", "BlackHole 16ch"]
    assert check["blockers"] == []


def test_audio_route_check_reports_speaker_default_output() -> None:
    check = readiness.check_audio_route(
        current_output="MacBook Pro Speakers",
        current_system="MacBook Pro Speakers",
        switch_available=True,
    )

    assert check["ok"] is False
    assert "MacBook Pro Speakers" in check["blockers"][0]
    assert "loopback capture" in check["blockers"][0]


def test_check_rekordbox_audio_settings_parses_current_device(tmp_path: Path) -> None:
    settings_path = tmp_path / "rekordbox3.settings"
    settings_path.write_text(
        """
<SETTINGS>
  <VALUE name="audioDeviceManager_DeviceSetup_DDJ-FLX4">
    <DEVICESETUP
      audioOutputDeviceName="DDJ-FLX4"
      audioInputDeviceName="DDJ-FLX4"
      audioDeviceRate="48000.0"
      Date="1000.0" />
  </VALUE>
  <VALUE name="audioDeviceManager">
    <DEVICESETUP
      audioOutputDeviceName="BlackHole 2ch"
      audioInputDeviceName="BlackHole 2ch"
      audioDeviceRate="44100.0"
      audioDeviceBufferSize="128"
      MixerMode_Is_Internal="1"
      OutputChannel_Master_L="1"
      OutputChannel_Master_R="2" />
  </VALUE>
</SETTINGS>
""".strip(),
        encoding="utf-8",
    )

    check = readiness.check_rekordbox_audio_settings(settings_path)

    assert check["ok"] is True
    assert check["path"] == str(settings_path)
    assert check["current"]["audio_output_device_name"] == "BlackHole 2ch"
    assert check["current"]["audio_device_rate"] == "44100.0"
    assert check["recent"][0]["name"] == "audioDeviceManager"
    assert check["blockers"] == []


def test_check_rekordbox_audio_settings_reports_missing_file(tmp_path: Path) -> None:
    check = readiness.check_rekordbox_audio_settings(tmp_path / "missing.settings")

    assert check["ok"] is False
    assert check["current"] is None
    assert "not found" in check["error"]
    assert "Rekordbox settings file was not found" in check["blockers"]


def test_select_loopback_signal_device_prefers_current_output() -> None:
    selected = readiness.select_loopback_signal_device(
        [
            {
                "name": "BlackHole 2ch",
                "max_input_channels": 2,
                "default_samplerate": 44100,
            },
            {
                "name": "BlackHole 16ch",
                "max_input_channels": 16,
                "default_samplerate": 48000,
            },
        ],
        preferred_device="BlackHole 16ch",
    )

    assert selected is not None
    assert selected["index"] == 1
    assert selected["name"] == "BlackHole 16ch"
    assert selected["sample_rate"] == 48000
    assert selected["channels"] == 2


def test_preferred_loopback_device_for_course3_uses_rekordbox_output() -> None:
    selected = readiness.preferred_loopback_device_for_readiness(
        requirement="course3",
        audio_route_check={"output_device": "BlackHole 16ch"},
        rekordbox_audio_settings_check={
            "current": {"audio_output_device_name": "BlackHole 2ch"}
        },
    )

    assert selected == "BlackHole 2ch"


def test_preferred_loopback_device_for_screen_uses_macos_output() -> None:
    selected = readiness.preferred_loopback_device_for_readiness(
        requirement="screen",
        audio_route_check={"output_device": "BlackHole 16ch"},
        rekordbox_audio_settings_check={
            "current": {"audio_output_device_name": "BlackHole 2ch"}
        },
    )

    assert selected == "BlackHole 16ch"


def test_collect_readiness_samples_rekordbox_loopback_for_course3(monkeypatch) -> None:
    sampled: list[tuple[str, str | None]] = []

    monkeypatch.setattr(readiness, "check_socket", lambda _url: {"ok": False})
    monkeypatch.setattr(readiness, "check_rekordbox_process", lambda: {"ok": True})
    monkeypatch.setattr(
        readiness,
        "check_rekordbox_audio_settings",
        lambda: {
            "ok": True,
            "current": {"audio_output_device_name": "BlackHole 2ch"},
            "blockers": [],
        },
    )
    monkeypatch.setattr(
        readiness,
        "check_midi_ports",
        lambda: {
            "ok": True,
            "ports": ["DDJ-FLX4"],
            "controller_matches": ["DDJ-FLX4"],
        },
    )
    monkeypatch.setattr(
        readiness,
        "check_usb_controller",
        lambda: {"ok": True, "controller_matches": ["DDJ-FLX4"]},
    )
    monkeypatch.setattr(
        readiness,
        "check_audio_devices",
        lambda: {
            "ok": True,
            "loopback_present": True,
            "dj_audio_present": True,
            "controller_audio_present": True,
        },
    )
    monkeypatch.setattr(
        readiness,
        "check_audio_route",
        lambda: {
            "available": True,
            "ok": True,
            "output_device": "BlackHole 16ch",
            "blockers": [],
        },
    )

    def fake_signal(*, preferred_device: str | None, **_kwargs):
        sampled.append(("signal", preferred_device))
        return None

    def fake_self_test(*, preferred_device: str | None, **_kwargs):
        sampled.append(("self_test", preferred_device))
        return None

    monkeypatch.setattr(readiness, "check_loopback_signal", fake_signal)
    monkeypatch.setattr(readiness, "check_loopback_self_test", fake_self_test)
    monkeypatch.setattr(readiness, "check_capture_matrix", lambda **_kwargs: None)

    readiness.collect_readiness(
        requirement="course3",
        url="ws://127.0.0.1:8765",
        loopback_signal_seconds=0.1,
        loopback_self_test_seconds=0.1,
    )

    assert sampled == [
        ("signal", "BlackHole 2ch"),
        ("self_test", "BlackHole 2ch"),
    ]


def test_select_loopback_route_device_requires_duplex_loopback() -> None:
    selected = readiness.select_loopback_route_device(
        [
            {
                "name": "BlackHole Input Only",
                "max_input_channels": 2,
                "max_output_channels": 0,
                "default_samplerate": 48000,
            },
            {
                "name": "BlackHole 16ch",
                "max_input_channels": 16,
                "max_output_channels": 16,
                "default_samplerate": 48000,
            },
        ],
        preferred_device="BlackHole 16ch",
    )

    assert selected is not None
    assert selected["index"] == 1
    assert selected["name"] == "BlackHole 16ch"


def test_check_loopback_signal_reports_direct_capture_signal(monkeypatch) -> None:
    def fake_record(**_kwargs):
        return {"rms": 0.0123, "peak": 0.15}

    monkeypatch.setattr(readiness, "_record_loopback_signal", fake_record)

    check = readiness.check_loopback_signal(
        seconds=0.25,
        preferred_device="BlackHole 16ch",
        devices=[
            {
                "name": "BlackHole 16ch",
                "max_input_channels": 16,
                "default_samplerate": 48000,
            }
        ],
    )

    assert check is not None
    assert check["ok"] is True
    assert check["device"]["name"] == "BlackHole 16ch"
    assert check["rms"] == 0.0123
    assert check["peak"] == 0.15
    assert check["blockers"] == []


def test_check_loopback_signal_reports_silent_capture(monkeypatch) -> None:
    def fake_record(**_kwargs):
        return {"rms": 0.0, "peak": 0.0}

    monkeypatch.setattr(readiness, "_record_loopback_signal", fake_record)

    check = readiness.check_loopback_signal(
        seconds=0.25,
        preferred_device="BlackHole 16ch",
        devices=[
            {
                "name": "BlackHole 16ch",
                "max_input_channels": 16,
                "default_samplerate": 48000,
            }
        ],
    )

    assert check is not None
    assert check["ok"] is False
    assert check["rms"] == 0.0
    assert "direct loopback capture is silent" in check["blockers"]


def test_check_loopback_self_test_reports_healthy_route(monkeypatch) -> None:
    def fake_playrec(**_kwargs):
        return {"rms": 0.028, "peak": 0.08, "emitted_peak": 0.08}

    monkeypatch.setattr(readiness, "_playrec_loopback_self_test", fake_playrec)

    check = readiness.check_loopback_self_test(
        seconds=0.25,
        preferred_device="BlackHole 16ch",
        devices=[
            {
                "name": "BlackHole 16ch",
                "max_input_channels": 16,
                "max_output_channels": 16,
                "default_samplerate": 48000,
            }
        ],
    )

    assert check is not None
    assert check["ok"] is True
    assert check["device"]["name"] == "BlackHole 16ch"
    assert check["rms"] == 0.028
    assert check["emitted_peak"] == 0.08


def test_check_loopback_self_test_reports_broken_route(monkeypatch) -> None:
    def fake_playrec(**_kwargs):
        return {"rms": 0.0, "peak": 0.0, "emitted_peak": 0.08}

    monkeypatch.setattr(readiness, "_playrec_loopback_self_test", fake_playrec)

    check = readiness.check_loopback_self_test(
        seconds=0.25,
        preferred_device="BlackHole 16ch",
        devices=[
            {
                "name": "BlackHole 16ch",
                "max_input_channels": 16,
                "max_output_channels": 16,
                "default_samplerate": 48000,
            }
        ],
    )

    assert check is not None
    assert check["ok"] is False
    assert "loopback route self-test did not capture injected signal" in check["blockers"]


def test_check_capture_matrix_ranks_sampled_inputs(monkeypatch) -> None:
    def fake_record(**kwargs):
        if kwargs["device_index"] == 2:
            return {"rms": 0.018, "peak": 0.2}
        return {"rms": 0.0, "peak": 0.0}

    monkeypatch.setattr(readiness, "_record_input_signal", fake_record)

    check = readiness.check_capture_matrix(
        seconds=0.25,
        devices=[
            {
                "name": "BlackHole 16ch",
                "max_input_channels": 16,
                "default_samplerate": 48000,
            },
            {
                "name": "MacBook Pro Microphone",
                "max_input_channels": 1,
                "default_samplerate": 48000,
            },
            {
                "name": "rekordbox Aggregate Device",
                "max_input_channels": 2,
                "default_samplerate": 44100,
            },
        ],
    )

    assert check is not None
    assert check["ok"] is True
    assert check["top_signal"]["name"] == "rekordbox Aggregate Device"
    assert check["rows"][0]["rms"] == 0.018
    assert all(row["name"] != "MacBook Pro Microphone" for row in check["rows"])


def test_auto_master_recommendation_prefers_live_48k_capture() -> None:
    recommendation = readiness.recommend_auto_master_input(
        capture_matrix_check={
            "enabled": True,
            "ok": True,
            "top_signal": {
                "name": "BlackHole 16ch",
                "rms": 0.018,
                "peak": 0.2,
                "sample_rate": 48000,
                "signal": True,
            },
            "rows": [],
        },
    )

    assert recommendation["ok"] is True
    assert recommendation["status"] == "ready"
    assert recommendation["source"] == "capture_matrix_top_signal"
    assert recommendation["reason"] == "live_signal"
    assert recommendation["device_name"] == "BlackHole 16ch"
    assert recommendation["sample_rate"] == 48000
    assert recommendation["live_signal"] is True


def test_auto_master_recommendation_reports_live_rate_mismatch() -> None:
    recommendation = readiness.recommend_auto_master_input(
        capture_matrix_check={
            "enabled": True,
            "ok": True,
            "top_signal": {
                "name": "rekordbox Aggregate Device",
                "rms": 0.018,
                "peak": 0.2,
                "sample_rate": 44100,
                "signal": True,
            },
            "rows": [],
        },
    )

    assert recommendation["ok"] is False
    assert recommendation["status"] == "needs_rate_fix"
    assert recommendation["reason"] == "live_signal_rate_mismatch"
    assert recommendation["device_name"] == "rekordbox Aggregate Device"
    assert recommendation["sample_rate"] == 44100
    assert "48000Hz" in recommendation["next_action"]


def test_auto_master_recommendation_uses_saved_rekordbox_route() -> None:
    recommendation = readiness.recommend_auto_master_input(
        capture_matrix_check={
            "enabled": True,
            "ok": False,
            "rows": [
                {
                    "name": "BlackHole 2ch",
                    "rms": 0.0,
                    "peak": 0.0,
                    "sample_rate": 48000,
                    "signal": False,
                }
            ],
        },
        rekordbox_audio_settings_check={
            "current": {"audio_output_device_name": "BlackHole 2ch"}
        },
    )

    assert recommendation["ok"] is True
    assert recommendation["source"] == "rekordbox_audio_settings"
    assert recommendation["reason"] == "saved_loopback_route"
    assert recommendation["device_name"] == "BlackHole 2ch"


def test_auto_master_candidates_match_rekordbox_aggregate_alias() -> None:
    recommendation = readiness.recommend_auto_master_input(
        capture_matrix_check={
            "enabled": True,
            "ok": False,
            "rows": [
                {
                    "name": "rekordbox Aggregate Device",
                    "rms": 0.000166,
                    "peak": 0.000763,
                    "sample_rate": 44100,
                    "signal": False,
                },
                {
                    "name": "BlackHole 16ch",
                    "rms": 0.0,
                    "peak": 0.0,
                    "sample_rate": 48000,
                    "signal": False,
                },
            ],
        },
        rekordbox_audio_settings_check={
            "current": {
                "audio_output_device_name": "Aggregate Device",
                "audio_device_rate": "48000.0",
            }
        },
    )

    aggregate = next(
        candidate
        for candidate in recommendation["candidates"]
        if candidate["name"] == "rekordbox Aggregate Device"
    )
    assert aggregate["sampled"] is True
    assert aggregate["source"] == "capture_matrix+rekordbox_audio_settings"
    assert "saved_rekordbox_route" in aggregate["reasons"]
    assert all(candidate["name"] != "Aggregate Device" for candidate in recommendation["candidates"])


def test_build_summary_marks_screen_ready_without_controller() -> None:
    summary = readiness.build_summary(
        requirement="screen",
        socket_check={"ok": True},
        rekordbox_check={"ok": False},
        midi_check={"ok": False, "ports": [], "controller_matches": []},
        usb_check={"ok": False, "controller_matches": []},
        audio_check={"ok": True, "loopback_present": True, "dj_audio_present": True},
    )

    assert summary["passed"] is True
    assert summary["readiness"] == {
        "screen_learn": True,
        "physical_learn": False,
        "course3_audio": False,
    }
    assert "uv run python scripts/live_learn_screen_probe.py --seconds 60" in summary[
        "next_commands"
    ]
    assert summary["course3_route_doctor"] is None


def test_build_summary_names_foreign_port_owner() -> None:
    summary = readiness.build_summary(
        requirement="screen",
        socket_check={
            "ok": False,
            "listener": {
                "command": "uvicorn",
                "pid": "85484",
            },
        },
        rekordbox_check={"ok": False},
        midi_check={"ok": False, "ports": [], "controller_matches": []},
        usb_check={"ok": False, "controller_matches": []},
        audio_check={"ok": True, "loopback_present": True, "dj_audio_present": True},
    )

    assert summary["passed"] is False
    assert (
        "port 8765 is occupied by uvicorn pid 85484, "
        "not the Vibemix Learn sidecar websocket"
    ) in summary["blockers"]


def test_course3_route_doctor_turns_blockers_into_operator_steps() -> None:
    summary = readiness.build_summary(
        requirement="course3",
        socket_check={
            "ok": False,
            "listener": {"command": "python3.1", "pid": "85484"},
        },
        rekordbox_check={"ok": True},
        midi_check={"ok": True, "ports": ["DDJ-FLX4"], "controller_matches": ["DDJ-FLX4"]},
        usb_check={"ok": True, "controller_matches": ["DDJ-FLX4"]},
        audio_check={"ok": True, "loopback_present": True, "dj_audio_present": True},
        audio_route_check={
            "available": True,
            "ok": False,
            "blockers": [
                "current macOS output route is 'MacBook Pro Speakers', not a loopback capture device"
            ],
        },
        loopback_signal_check={
            "enabled": True,
            "ok": False,
            "blockers": ["direct loopback capture is silent"],
        },
        live_context_check={
            "ok": False,
            "blockers": ["live master audio is not audible yet"],
        },
        nowplaying_check={
            "available": True,
            "full_title": "Baga Tek",
            "bundle_identifier": "WebKit GPU",
            "is_playing": False,
            "looks_like_rekordbox": False,
        },
    )

    doctor = summary["course3_route_doctor"]

    assert doctor["operator_steps"][:4] == [
        "Free 127.0.0.1:8765 so the Vibemix Learn sidecar owns the app socket.",
        "Route macOS/Rekordbox output to BlackHole 16ch or the intended loopback route.",
        "Play a real Rekordbox library track through the routed master output.",
        "Stop unrelated browser/system media so Now Playing can point at Rekordbox.",
    ]
    assert doctor["next_step"].startswith("Free 127.0.0.1:8765")
    assert (
        "Switch macOS output/system audio to BlackHole 16ch or the intended loopback route."
        not in doctor["operator_steps"]
    )
    assert doctor["proof_command"].endswith(
        "--out /tmp/vibemix-live-learn-proof/proof-course3-auto-master-current.json"
    )


def test_build_summary_requires_usb_or_controller_audio_for_physical_readiness() -> None:
    summary = readiness.build_summary(
        requirement="physical",
        socket_check={"ok": True},
        rekordbox_check={"ok": True},
        midi_check={"ok": True, "ports": ["DDJ-FLX4"], "controller_matches": ["DDJ-FLX4"]},
        usb_check={"ok": False, "controller_matches": []},
        audio_check={
            "ok": True,
            "loopback_present": True,
            "dj_audio_present": True,
            "controller_audio_present": False,
        },
    )

    assert summary["passed"] is False
    assert summary["readiness"]["physical_learn"] is False
    assert "physical controller is not visible on USB or controller audio" in summary["blockers"]
    assert summary["physical_connection_doctor"]["status"] == "missing_usb_or_audio"
    assert summary["physical_connection_doctor"]["operator_steps"] == [
        "Confirm macOS sees DDJ-FLX4 in USB or audio devices before starting the proof."
    ]


def test_build_summary_names_bluetooth_midi_only_flx4_for_physical_readiness() -> None:
    summary = readiness.build_summary(
        requirement="physical",
        socket_check={"ok": True},
        rekordbox_check={"ok": True},
        midi_check={
            "ok": True,
            "ports": ["DDJ-FLX4 Bluetooth MIDI"],
            "controller_matches": ["DDJ-FLX4 Bluetooth MIDI"],
        },
        usb_check={"ok": False, "controller_matches": []},
        audio_check={
            "ok": True,
            "loopback_present": True,
            "dj_audio_present": True,
            "controller_audio_present": False,
        },
    )

    assert summary["passed"] is False
    assert summary["readiness"]["physical_learn"] is False
    assert summary["hardware_connection"] == {
        "bluetooth_midi_only": True,
        "bluetooth_midi_matches": ["DDJ-FLX4 Bluetooth MIDI"],
        "controller_hardware_ready": False,
    }
    assert (
        "DDJ-FLX4 is visible only as Bluetooth MIDI; connect it by USB "
        "for Learn hardware/audio proof"
    ) in summary["blockers"]
    assert "physical controller is not visible on USB or controller audio" not in summary[
        "blockers"
    ]
    assert summary["physical_connection_doctor"]["status"] == "bluetooth_midi_only"
    assert summary["physical_connection_doctor"]["operator_steps"] == [
        "Connect the DDJ-FLX4 by USB; Bluetooth MIDI is not enough for hardware proof."
    ]


def test_build_summary_accepts_controller_audio_when_usb_profiler_misses_device() -> None:
    summary = readiness.build_summary(
        requirement="physical",
        socket_check={"ok": True},
        rekordbox_check={"ok": True},
        midi_check={"ok": True, "ports": ["DDJ-FLX4"], "controller_matches": ["DDJ-FLX4"]},
        usb_check={"ok": False, "controller_matches": []},
        audio_check={
            "ok": True,
            "loopback_present": True,
            "dj_audio_present": True,
            "controller_audio_present": True,
        },
    )

    assert summary["passed"] is True
    assert summary["readiness"]["physical_learn"] is True
    assert "physical controller is not visible on USB or controller audio" not in summary[
        "blockers"
    ]


def test_build_summary_reports_physical_controller_blockers() -> None:
    summary = readiness.build_summary(
        requirement="physical",
        socket_check={"ok": True},
        rekordbox_check={"ok": True},
        midi_check={"ok": False, "ports": [], "controller_matches": []},
        usb_check={"ok": False, "controller_matches": []},
        audio_check={
            "ok": True,
            "loopback_present": True,
            "dj_audio_present": True,
        },
    )

    assert summary["passed"] is False
    assert summary["readiness"]["physical_learn"] is False
    assert "physical controller is not visible as a MIDI input" in summary["blockers"]
    assert "physical controller is not visible on USB or controller audio" in summary["blockers"]


def test_build_summary_marks_course3_ready_with_rekordbox_and_loopback() -> None:
    summary = readiness.build_summary(
        requirement="course3",
        socket_check={"ok": True},
        rekordbox_check={"ok": True},
        midi_check={"ok": True, "ports": ["DDJ-FLX4"], "controller_matches": ["DDJ-FLX4"]},
        usb_check={"ok": True, "controller_matches": ["DDJ-FLX4"]},
        audio_check={"ok": True, "loopback_present": True, "dj_audio_present": True},
    )

    assert summary["passed"] is True
    assert summary["readiness"]["course3_audio"] is True
    assert (
        "uv run python scripts/live_course3_lens_probe.py --require-count-in --seconds 30"
        in summary["next_commands"]
    )


def test_build_summary_refuses_course3_when_live_context_has_no_deck() -> None:
    summary = readiness.build_summary(
        requirement="course3",
        socket_check={"ok": True},
        rekordbox_check={"ok": True},
        midi_check={"ok": True, "ports": ["DDJ-FLX4"], "controller_matches": ["DDJ-FLX4"]},
        usb_check={"ok": True, "controller_matches": ["DDJ-FLX4"]},
        audio_check={"ok": True, "loopback_present": True, "dj_audio_present": True},
        live_context_check={
            "ok": False,
            "blockers": ["live audio is not attributed to deck A, B, or mix"],
        },
    )

    assert summary["passed"] is False
    assert summary["readiness"]["course3_audio"] is False
    assert "live audio is not attributed to deck A, B, or mix" in summary["blockers"]
    assert summary["checks"]["course3_live_context"]["ok"] is False


def test_build_summary_adds_audio_route_blocker_when_course3_is_silent() -> None:
    summary = readiness.build_summary(
        requirement="course3",
        socket_check={"ok": True},
        rekordbox_check={"ok": True},
        midi_check={"ok": True, "ports": ["DDJ-FLX4"], "controller_matches": ["DDJ-FLX4"]},
        usb_check={"ok": True, "controller_matches": ["DDJ-FLX4"]},
        audio_check={"ok": True, "loopback_present": True, "dj_audio_present": True},
        audio_route_check={
            "available": True,
            "ok": False,
            "blockers": [
                "current macOS output route is 'MacBook Pro Speakers', not a loopback capture device"
            ],
        },
        live_context_check={
            "ok": False,
            "blockers": ["live master audio is not audible yet"],
        },
    )

    assert "live master audio is not audible yet" in summary["blockers"]
    assert (
        "current macOS output route is 'MacBook Pro Speakers', not a loopback capture device"
        in summary["blockers"]
    )
    assert summary["checks"]["audio_route"]["ok"] is False
    assert summary["course3_audio_diagnosis"]["code"] == "macos_output_not_loopback"


def test_build_summary_adds_loopback_signal_blocker_when_course3_is_silent() -> None:
    summary = readiness.build_summary(
        requirement="course3",
        socket_check={"ok": True},
        rekordbox_check={"ok": True},
        midi_check={"ok": True, "ports": ["DDJ-FLX4"], "controller_matches": ["DDJ-FLX4"]},
        usb_check={"ok": True, "controller_matches": ["DDJ-FLX4"]},
        audio_check={"ok": True, "loopback_present": True, "dj_audio_present": True},
        audio_route_check={"available": True, "ok": True, "blockers": []},
        loopback_signal_check={
            "enabled": True,
            "ok": False,
            "blockers": ["direct loopback capture is silent"],
        },
        live_context_check={
            "ok": False,
            "blockers": ["live master audio is not audible yet"],
        },
    )

    assert "live master audio is not audible yet" in summary["blockers"]
    assert "direct loopback capture is silent" in summary["blockers"]
    assert summary["checks"]["loopback_signal"]["ok"] is False


def test_build_summary_refuses_course3_when_explicit_loopback_signal_is_silent() -> None:
    summary = readiness.build_summary(
        requirement="course3",
        socket_check={"ok": True},
        rekordbox_check={"ok": True},
        midi_check={"ok": True, "ports": ["DDJ-FLX4"], "controller_matches": ["DDJ-FLX4"]},
        usb_check={"ok": True, "controller_matches": ["DDJ-FLX4"]},
        audio_check={"ok": True, "loopback_present": True, "dj_audio_present": True},
        loopback_signal_check={
            "enabled": True,
            "ok": False,
            "blockers": ["direct loopback capture is silent"],
        },
    )

    assert summary["passed"] is False
    assert summary["readiness"]["course3_audio"] is False
    assert "direct loopback capture is silent" in summary["blockers"]


def test_build_summary_refuses_course3_when_explicit_capture_matrix_is_silent() -> None:
    summary = readiness.build_summary(
        requirement="course3",
        socket_check={"ok": True},
        rekordbox_check={"ok": True},
        midi_check={"ok": True, "ports": ["DDJ-FLX4"], "controller_matches": ["DDJ-FLX4"]},
        usb_check={"ok": True, "controller_matches": ["DDJ-FLX4"]},
        audio_check={"ok": True, "loopback_present": True, "dj_audio_present": True},
        capture_matrix_check={
            "enabled": True,
            "ok": False,
            "blockers": ["all sampled DJ/loopback capture inputs are below signal floor"],
        },
    )

    assert summary["passed"] is False
    assert summary["readiness"]["course3_audio"] is False
    assert "all sampled DJ/loopback capture inputs are below signal floor" in summary["blockers"]


def test_build_summary_adds_self_test_blocker_when_course3_is_silent() -> None:
    summary = readiness.build_summary(
        requirement="course3",
        socket_check={"ok": True},
        rekordbox_check={"ok": True},
        midi_check={"ok": True, "ports": ["DDJ-FLX4"], "controller_matches": ["DDJ-FLX4"]},
        usb_check={"ok": True, "controller_matches": ["DDJ-FLX4"]},
        audio_check={"ok": True, "loopback_present": True, "dj_audio_present": True},
        audio_route_check={"available": True, "ok": True, "blockers": []},
        loopback_self_test_check={
            "enabled": True,
            "ok": False,
            "blockers": ["loopback route self-test did not capture injected signal"],
        },
        live_context_check={
            "ok": False,
            "blockers": ["live master audio is not audible yet"],
        },
    )

    assert "loopback route self-test did not capture injected signal" in summary["blockers"]
    assert summary["checks"]["loopback_self_test"]["ok"] is False
    assert (
        summary["course3_audio_diagnosis"]["code"]
        == "loopback_route_failed_self_test"
    )


def test_build_summary_treats_rekordbox_owned_self_test_as_inconclusive() -> None:
    summary = readiness.build_summary(
        requirement="course3",
        socket_check={"ok": True},
        rekordbox_check={"ok": True},
        midi_check={"ok": True, "ports": ["DDJ-FLX4"], "controller_matches": ["DDJ-FLX4"]},
        usb_check={"ok": True, "controller_matches": ["DDJ-FLX4"]},
        audio_check={
            "ok": True,
            "loopback_present": True,
            "dj_audio_present": True,
            "controller_audio_present": True,
        },
        audio_route_check={
            "available": True,
            "ok": True,
            "output_device": "BlackHole 16ch",
            "blockers": [],
        },
        loopback_self_test_check={
            "enabled": True,
            "ok": False,
            "device": {"name": "BlackHole 2ch"},
            "blockers": ["loopback route self-test did not capture injected signal"],
        },
        loopback_signal_check={"enabled": True, "ok": False, "blockers": []},
        capture_matrix_check={
            "enabled": True,
            "ok": False,
            "rows": [
                {
                    "name": "BlackHole 2ch",
                    "rms": 0.0,
                    "peak": 0.0,
                    "sample_rate": 48000,
                    "signal": False,
                },
                {
                    "name": "DDJ-FLX4",
                    "rms": 0.000177,
                    "peak": 0.000671,
                    "sample_rate": 44100,
                    "signal": False,
                },
            ],
            "blockers": ["all sampled DJ/loopback capture inputs are below signal floor"],
        },
        live_context_check={
            "ok": False,
            "blockers": ["live master audio is not audible yet"],
        },
        rekordbox_audio_settings_check={
            "ok": True,
            "path": "/tmp/rekordbox3.settings",
            "current": {
                "audio_output_device_name": "BlackHole 2ch",
                "audio_input_device_name": "BlackHole 2ch",
            },
            "recent": [],
            "blockers": [],
        },
    )

    assert "loopback route self-test did not capture injected signal" not in summary[
        "blockers"
    ]
    diagnosis = summary["course3_audio_diagnosis"]
    assert (
        diagnosis["code"]
        == "rekordbox_route_self_test_inconclusive_external_playback_absent"
    )
    assert diagnosis["severity"] == "start_playback"
    assert "self-test is inconclusive" in diagnosis["message"]
    assert diagnosis["loopback_self_test_inconclusive"]["device"]["name"] == "BlackHole 2ch"


def test_build_summary_adds_capture_matrix_blocker_when_course3_is_silent() -> None:
    summary = readiness.build_summary(
        requirement="course3",
        socket_check={"ok": True},
        rekordbox_check={"ok": True},
        midi_check={"ok": True, "ports": ["DDJ-FLX4"], "controller_matches": ["DDJ-FLX4"]},
        usb_check={"ok": True, "controller_matches": ["DDJ-FLX4"]},
        audio_check={"ok": True, "loopback_present": True, "dj_audio_present": True},
        audio_route_check={"available": True, "ok": True, "blockers": []},
        capture_matrix_check={
            "enabled": True,
            "ok": False,
            "blockers": ["all sampled DJ/loopback capture inputs are below signal floor"],
        },
        live_context_check={
            "ok": False,
            "blockers": ["live master audio is not audible yet"],
        },
    )

    assert "all sampled DJ/loopback capture inputs are below signal floor" in summary[
        "blockers"
    ]
    assert summary["checks"]["capture_matrix"]["ok"] is False


def test_build_summary_reports_signal_on_wrong_capture_when_loopback_is_silent() -> None:
    summary = readiness.build_summary(
        requirement="course3",
        socket_check={"ok": True},
        rekordbox_check={"ok": True},
        midi_check={"ok": True, "ports": ["DDJ-FLX4"], "controller_matches": ["DDJ-FLX4"]},
        usb_check={"ok": True, "controller_matches": ["DDJ-FLX4"]},
        audio_check={"ok": True, "loopback_present": True, "dj_audio_present": True},
        audio_route_check={"available": True, "ok": True, "blockers": []},
        loopback_signal_check={"enabled": True, "ok": False, "blockers": []},
        capture_matrix_check={
            "enabled": True,
            "ok": True,
            "top_signal": {"name": "rekordbox Aggregate Device"},
            "blockers": [],
        },
        live_context_check={
            "ok": False,
            "blockers": ["live master audio is not audible yet"],
        },
    )

    assert (
        "capture signal is present on 'rekordbox Aggregate Device', "
        "but the selected loopback capture is silent"
    ) in summary["blockers"]
    assert summary["course3_audio_diagnosis"]["code"] == "signal_on_unselected_capture"
    assert (
        summary["course3_audio_diagnosis"]["top_signal"]["name"]
        == "rekordbox Aggregate Device"
    )


def test_build_summary_diagnoses_healthy_loopback_but_absent_external_playback() -> None:
    summary = readiness.build_summary(
        requirement="course3",
        socket_check={"ok": True},
        rekordbox_check={"ok": True},
        midi_check={"ok": True, "ports": ["DDJ-FLX4"], "controller_matches": ["DDJ-FLX4"]},
        usb_check={"ok": True, "controller_matches": ["DDJ-FLX4"]},
        audio_check={"ok": True, "loopback_present": True, "dj_audio_present": True},
        audio_route_check={"available": True, "ok": True, "blockers": []},
        loopback_self_test_check={"enabled": True, "ok": True, "blockers": []},
        loopback_signal_check={"enabled": True, "ok": False, "blockers": []},
        capture_matrix_check={"enabled": True, "ok": False, "blockers": []},
        live_context_check={
            "ok": False,
            "blockers": ["live master audio is not audible yet"],
        },
    )

    diagnosis = summary["course3_audio_diagnosis"]
    assert diagnosis["code"] == "loopback_route_healthy_external_playback_absent"
    assert diagnosis["severity"] == "start_playback"
    assert "Start real Rekordbox deck playback" in diagnosis["next_action"]


def test_build_summary_adds_rekordbox_route_hint_when_blackhole_is_silent() -> None:
    summary = readiness.build_summary(
        requirement="course3",
        socket_check={"ok": True},
        rekordbox_check={"ok": True},
        midi_check={"ok": True, "ports": ["DDJ-FLX4"], "controller_matches": ["DDJ-FLX4"]},
        usb_check={"ok": False, "controller_matches": []},
        audio_check={
            "ok": True,
            "loopback_present": True,
            "dj_audio_present": True,
            "controller_audio_present": True,
        },
        audio_route_check={
            "available": True,
            "ok": True,
            "output_device": "BlackHole 16ch",
            "blockers": [],
        },
        loopback_self_test_check={"enabled": True, "ok": True, "blockers": []},
        loopback_signal_check={"enabled": True, "ok": False, "blockers": []},
        capture_matrix_check={
            "enabled": True,
            "ok": False,
            "rows": [
                {
                    "name": "DDJ-FLX4",
                    "rms": 0.000177,
                    "peak": 0.000671,
                    "sample_rate": 44100,
                    "signal": False,
                },
                {
                    "name": "rekordbox Aggregate Device",
                    "rms": 0.000175,
                    "peak": 0.000702,
                    "sample_rate": 44100,
                    "signal": False,
                },
                {
                    "name": "BlackHole 16ch",
                    "rms": 0.0,
                    "peak": 0.0,
                    "sample_rate": 48000,
                    "signal": False,
                },
            ],
            "blockers": ["all sampled DJ/loopback capture inputs are below signal floor"],
        },
        live_context_check={
            "ok": False,
            "blockers": ["live master audio is not audible yet"],
        },
        rekordbox_audio_settings_check={
            "ok": True,
            "path": "/tmp/rekordbox3.settings",
            "current": {
                "audio_output_device_name": "BlackHole 2ch",
                "audio_input_device_name": "BlackHole 2ch",
                "audio_device_rate": "44100.0",
                "mixer_mode_internal": "1",
            },
            "recent": [],
            "blockers": [],
        },
    )

    diagnosis = summary["course3_audio_diagnosis"]
    assert diagnosis["code"] == "loopback_route_healthy_external_playback_absent"
    assert "BlackHole 2ch" in diagnosis["next_action"]
    assert "Rekordbox Audio preferences" in diagnosis["next_action"]
    assert diagnosis["rekordbox_route_hint"]["code"] == "rekordbox_may_bypass_macos_output"
    assert diagnosis["rekordbox_route_hint"]["loopback_rows"][0]["name"] == "BlackHole 16ch"
    assert diagnosis["rekordbox_route_hint"]["dj_capture_rows"][0]["name"] == "DDJ-FLX4"
    assert (
        diagnosis["rekordbox_route_hint"]["current_rekordbox_settings"][
            "audio_output_device_name"
        ]
        == "BlackHole 2ch"
    )
    assert diagnosis["rekordbox_audio_settings"]["path"] == "/tmp/rekordbox3.settings"
    assert (
        summary["checks"]["rekordbox_audio_settings"]["current"][
            "audio_output_device_name"
        ]
        == "BlackHole 2ch"
    )


def test_build_summary_diagnoses_rekordbox_loopback_rate_mismatch() -> None:
    summary = readiness.build_summary(
        requirement="course3",
        socket_check={"ok": True},
        rekordbox_check={"ok": True},
        midi_check={"ok": True, "ports": ["DDJ-FLX4"], "controller_matches": ["DDJ-FLX4"]},
        usb_check={"ok": False, "controller_matches": []},
        audio_check={
            "ok": True,
            "loopback_present": True,
            "dj_audio_present": True,
            "controller_audio_present": True,
        },
        audio_route_check={
            "available": True,
            "ok": True,
            "output_device": "BlackHole 16ch",
            "blockers": [],
        },
        loopback_self_test_check={"enabled": True, "ok": True, "blockers": []},
        loopback_signal_check={"enabled": True, "ok": False, "blockers": []},
        capture_matrix_check={
            "enabled": True,
            "ok": False,
            "rows": [
                {
                    "name": "BlackHole 16ch",
                    "rms": 0.0,
                    "peak": 0.0,
                    "sample_rate": 48000,
                    "signal": False,
                },
                {
                    "name": "BlackHole 2ch",
                    "rms": 0.0,
                    "peak": 0.0,
                    "sample_rate": 44100,
                    "signal": False,
                },
                {
                    "name": "DDJ-FLX4",
                    "rms": 0.000177,
                    "peak": 0.000671,
                    "sample_rate": 44100,
                    "signal": False,
                },
            ],
            "blockers": ["all sampled DJ/loopback capture inputs are below signal floor"],
        },
        live_context_check={
            "ok": False,
            "blockers": ["live master audio is not audible yet"],
        },
        rekordbox_audio_settings_check={
            "ok": True,
            "path": "/tmp/rekordbox3.settings",
            "current": {
                "audio_output_device_name": "BlackHole 2ch",
                "audio_input_device_name": "BlackHole 2ch",
                "audio_device_rate": "44100.0",
            },
            "recent": [],
            "blockers": [],
        },
    )

    diagnosis = summary["course3_audio_diagnosis"]
    assert diagnosis["code"] == "rekordbox_loopback_sample_rate_mismatch"
    assert diagnosis["severity"] == "fix_rate"
    assert "Set BlackHole 2ch to 48000Hz" in diagnosis["next_action"]
    assert diagnosis["rate_mismatch"]["sample_rate"] == 44100
    assert diagnosis["rate_mismatch"]["expected_sample_rate"] == 48000
    assert (
        diagnosis["rate_mismatch"]["capture_row"]["name"]
        == "BlackHole 2ch"
    )


def test_build_summary_diagnoses_rekordbox_saved_rate_mismatch() -> None:
    summary = readiness.build_summary(
        requirement="course3",
        socket_check={"ok": True},
        rekordbox_check={"ok": True},
        midi_check={"ok": True, "ports": ["DDJ-FLX4"], "controller_matches": ["DDJ-FLX4"]},
        usb_check={"ok": False, "controller_matches": []},
        audio_check={
            "ok": True,
            "loopback_present": True,
            "dj_audio_present": True,
            "controller_audio_present": True,
        },
        audio_route_check={
            "available": True,
            "ok": True,
            "output_device": "BlackHole 16ch",
            "blockers": [],
        },
        loopback_self_test_check={"enabled": True, "ok": True, "blockers": []},
        loopback_signal_check={"enabled": True, "ok": False, "blockers": []},
        capture_matrix_check={
            "enabled": True,
            "ok": False,
            "rows": [
                {
                    "name": "BlackHole 2ch",
                    "rms": 0.0,
                    "peak": 0.0,
                    "sample_rate": 48000,
                    "signal": False,
                },
                {
                    "name": "DDJ-FLX4",
                    "rms": 0.000177,
                    "peak": 0.000671,
                    "sample_rate": 44100,
                    "signal": False,
                },
            ],
            "blockers": ["all sampled DJ/loopback capture inputs are below signal floor"],
        },
        live_context_check={
            "ok": False,
            "blockers": ["live master audio is not audible yet"],
        },
        rekordbox_audio_settings_check={
            "ok": True,
            "path": "/tmp/rekordbox3.settings",
            "current": {
                "audio_output_device_name": "BlackHole 2ch",
                "audio_input_device_name": "BlackHole 2ch",
                "audio_device_rate": "44100.0",
            },
            "recent": [],
            "blockers": [],
        },
    )

    diagnosis = summary["course3_audio_diagnosis"]
    assert diagnosis["code"] == "rekordbox_saved_sample_rate_mismatch"
    assert diagnosis["severity"] == "fix_rate"
    assert "from 44100Hz to 48000Hz" in diagnosis["next_action"]
    assert diagnosis["saved_rate_mismatch"]["saved_sample_rate"] == 44100
    assert diagnosis["saved_rate_mismatch"]["capture_sample_rate"] == 48000
    assert (
        diagnosis["rekordbox_route_hint"]["saved_rate_mismatch"]["code"]
        == "rekordbox_saved_sample_rate_mismatch"
    )


def test_build_summary_diagnoses_ddj_saved_rate_mismatch() -> None:
    summary = readiness.build_summary(
        requirement="course3",
        socket_check={"ok": True},
        rekordbox_check={"ok": True},
        midi_check={"ok": True, "ports": ["DDJ-FLX4"], "controller_matches": ["DDJ-FLX4"]},
        usb_check={"ok": True, "controller_matches": ["DDJ-FLX4"]},
        audio_check={
            "ok": True,
            "loopback_present": True,
            "dj_audio_present": True,
            "controller_audio_present": True,
        },
        audio_route_check={
            "available": True,
            "ok": False,
            "output_device": "MacBook Pro Speakers",
            "blockers": [
                "current macOS output route is 'MacBook Pro Speakers', not a loopback capture device"
            ],
        },
        loopback_self_test_check={"enabled": True, "ok": True, "blockers": []},
        loopback_signal_check={
            "enabled": True,
            "ok": False,
            "blockers": ["direct loopback capture is silent"],
        },
        capture_matrix_check={
            "enabled": True,
            "ok": False,
            "rows": [
                {
                    "name": "DDJ-FLX4",
                    "rms": 0.000169,
                    "peak": 0.000763,
                    "sample_rate": 48000,
                    "signal": False,
                },
                {
                    "name": "BlackHole 16ch",
                    "rms": 0.0,
                    "peak": 0.0,
                    "sample_rate": 48000,
                    "signal": False,
                },
            ],
            "blockers": ["all sampled DJ/loopback capture inputs are below signal floor"],
        },
        live_context_check={
            "ok": False,
            "blockers": ["live master audio is not audible yet"],
        },
        rekordbox_audio_settings_check={
            "ok": True,
            "path": "/tmp/rekordbox3.settings",
            "current": {
                "audio_output_device_name": "DDJ-FLX4",
                "audio_input_device_name": "DDJ-FLX4",
                "audio_device_rate": "44100.0",
            },
            "recent": [],
            "blockers": [],
        },
        nowplaying_check={
            "available": True,
            "ok": True,
            "full_title": "Paused browser",
            "bundle_identifier": "com.apple.WebKit.GPU",
            "playback_rate": 0.0,
            "is_playing": False,
            "looks_like_rekordbox": False,
        },
    )

    diagnosis = summary["course3_audio_diagnosis"]
    assert diagnosis["code"] == "rekordbox_saved_sample_rate_mismatch"
    assert diagnosis["severity"] == "fix_rate"
    assert diagnosis["saved_rate_mismatch"]["rekordbox_output_device"] == "DDJ-FLX4"
    assert diagnosis["operator_action"]["route"] == "DDJ-FLX4 @ 48000Hz"
    doctor = summary["course3_route_doctor"]
    assert doctor["status"] == "fix_rate"
    assert doctor["next_step"].startswith("Set Rekordbox's DDJ-FLX4 route")
    assert doctor["route"] == "DDJ-FLX4 @ 48000Hz"


def test_build_summary_says_start_playback_when_rekordbox_loopback_is_aligned() -> None:
    summary = readiness.build_summary(
        requirement="course3",
        socket_check={"ok": True},
        rekordbox_check={"ok": True},
        midi_check={"ok": True, "ports": ["DDJ-FLX4"], "controller_matches": ["DDJ-FLX4"]},
        usb_check={"ok": False, "controller_matches": []},
        audio_check={
            "ok": True,
            "loopback_present": True,
            "dj_audio_present": True,
            "controller_audio_present": True,
        },
        audio_route_check={
            "available": True,
            "ok": True,
            "output_device": "BlackHole 16ch",
            "blockers": [],
        },
        loopback_self_test_check={"enabled": True, "ok": True, "blockers": []},
        loopback_signal_check={"enabled": True, "ok": False, "blockers": []},
        capture_matrix_check={
            "enabled": True,
            "ok": False,
            "rows": [
                {
                    "name": "BlackHole 2ch",
                    "rms": 0.0,
                    "peak": 0.0,
                    "sample_rate": 48000,
                    "signal": False,
                },
                {
                    "name": "DDJ-FLX4",
                    "rms": 0.000177,
                    "peak": 0.000671,
                    "sample_rate": 44100,
                    "signal": False,
                },
            ],
            "blockers": ["all sampled DJ/loopback capture inputs are below signal floor"],
        },
        live_context_check={
            "ok": False,
            "blockers": ["live master audio is not audible yet"],
        },
        rekordbox_audio_settings_check={
            "ok": True,
            "path": "/tmp/rekordbox3.settings",
            "current": {
                "audio_output_device_name": "BlackHole 2ch",
                "audio_input_device_name": "BlackHole 2ch",
                "audio_device_rate": "48000.0",
            },
            "recent": [],
            "blockers": [],
        },
    )

    diagnosis = summary["course3_audio_diagnosis"]
    assert diagnosis["code"] == "loopback_route_healthy_external_playback_absent"
    assert "start real deck playback" in diagnosis["next_action"]
    assert "align Rekordbox Audio preferences" not in diagnosis["next_action"]
    assert diagnosis["rekordbox_route_hint"]["current_rekordbox_route_aligned"] is True
    assert diagnosis["operator_action"]["route"] == "BlackHole 2ch @ 48000Hz"
    assert "real Rekordbox library track" in diagnosis["operator_action"]["prompt"]
    assert diagnosis["operator_action"]["steps"][-1] == (
        "Rerun the Course 3 live proof with --require-count-in."
    )
    doctor = summary["course3_route_doctor"]
    assert doctor["ok"] is False
    assert doctor["status"] == "start_playback"
    assert doctor["diagnosis_code"] == "loopback_route_healthy_external_playback_absent"
    assert doctor["route"] == "BlackHole 2ch @ 48000Hz"
    assert "--say-course3-prompts" in doctor["proof_command"]
    assert doctor["uses_spoken_prompt"] is True
    assert doctor["operator_steps"] == diagnosis["operator_action"]["steps"]


def test_build_summary_aligns_controller_route_before_course3_playback() -> None:
    summary = readiness.build_summary(
        requirement="course3",
        socket_check={"ok": True},
        rekordbox_check={"ok": True},
        midi_check={"ok": True, "ports": ["DDJ-FLX4"], "controller_matches": ["DDJ-FLX4"]},
        usb_check={"ok": True, "controller_matches": ["DDJ-FLX4"]},
        audio_check={
            "ok": True,
            "loopback_present": True,
            "dj_audio_present": True,
            "controller_audio_present": True,
        },
        audio_route_check={
            "available": True,
            "ok": False,
            "output_device": "MacBook Pro Speakers",
            "blockers": ["current macOS output route is not loopback"],
        },
        loopback_self_test_check={"enabled": True, "ok": True, "blockers": []},
        loopback_signal_check={"enabled": True, "ok": False, "blockers": []},
        capture_matrix_check={
            "enabled": True,
            "ok": False,
            "rows": [
                {
                    "name": "DDJ-FLX4",
                    "rms": 0.000176,
                    "peak": 0.000824,
                    "sample_rate": 48000,
                    "signal": False,
                },
                {
                    "name": "BlackHole 16ch",
                    "rms": 0.0,
                    "peak": 0.0,
                    "sample_rate": 48000,
                    "signal": False,
                },
            ],
            "blockers": ["all sampled DJ/loopback capture inputs are below signal floor"],
        },
        live_context_check={"ok": False, "blockers": ["live master audio is not audible yet"]},
        rekordbox_audio_settings_check={
            "ok": True,
            "path": "/tmp/rekordbox3.settings",
            "current": {
                "audio_output_device_name": "DDJ-FLX4",
                "audio_input_device_name": "DDJ-FLX4",
                "audio_device_rate": "48000.0",
            },
            "recent": [],
            "blockers": [],
        },
    )

    diagnosis = summary["course3_audio_diagnosis"]
    assert diagnosis["code"] == "loopback_route_healthy_external_playback_absent"
    assert diagnosis["rekordbox_route_hint"]["current_rekordbox_route_aligned"] is False
    assert "align Rekordbox Audio preferences" in diagnosis["next_action"]
    assert diagnosis["operator_action"]["current_rekordbox_route"] == "DDJ-FLX4 @ 48000Hz"
    assert diagnosis["operator_action"]["target_capture_route"] == "BlackHole 16ch @ 48000Hz"
    assert diagnosis["operator_action"]["route"] == "BlackHole 16ch @ 48000Hz"
    assert diagnosis["operator_action"]["prompt"] == (
        "Set Rekordbox audio to BlackHole 16ch @ 48000Hz, then play a real "
        "library track with channel and master faders up."
    )
    assert diagnosis["operator_action"]["steps"][0] == (
        "In Rekordbox Audio preferences, set the audio output from DDJ-FLX4 @ 48000Hz "
        "to BlackHole 16ch @ 48000Hz."
    )
    assert diagnosis["operator_action"]["steps"][1] == (
        "In Rekordbox, load and play a real library track through BlackHole 16ch @ 48000Hz."
    )
    doctor = summary["course3_route_doctor"]
    assert doctor["next_step"] == diagnosis["operator_action"]["steps"][0]
    assert doctor["route"] == "BlackHole 16ch @ 48000Hz"


def test_build_summary_diagnoses_rekordbox_aggregate_capture_rate_mismatch() -> None:
    summary = readiness.build_summary(
        requirement="course3",
        socket_check={"ok": True},
        rekordbox_check={"ok": True},
        midi_check={"ok": True, "ports": ["DDJ-FLX4"], "controller_matches": ["DDJ-FLX4"]},
        usb_check={"ok": True, "controller_matches": ["DDJ-FLX4"]},
        audio_check={
            "ok": True,
            "loopback_present": True,
            "dj_audio_present": True,
            "controller_audio_present": True,
        },
        audio_route_check={
            "available": True,
            "ok": False,
            "output_device": "MacBook Pro Speakers",
            "blockers": [
                "current macOS output route is 'MacBook Pro Speakers', not a loopback capture device"
            ],
        },
        loopback_self_test_check={"enabled": True, "ok": True, "blockers": []},
        loopback_signal_check={
            "enabled": True,
            "ok": False,
            "blockers": ["direct loopback capture is silent"],
        },
        capture_matrix_check={
            "enabled": True,
            "ok": False,
            "rows": [
                {
                    "name": "DDJ-FLX4",
                    "rms": 0.000166,
                    "peak": 0.000763,
                    "sample_rate": 44100,
                    "signal": False,
                },
                {
                    "name": "rekordbox Aggregate Device",
                    "rms": 0.000166,
                    "peak": 0.000732,
                    "sample_rate": 44100,
                    "signal": False,
                },
                {
                    "name": "BlackHole 16ch",
                    "rms": 0.0,
                    "peak": 0.0,
                    "sample_rate": 48000,
                    "signal": False,
                },
            ],
            "blockers": ["all sampled DJ/loopback capture inputs are below signal floor"],
        },
        live_context_check={
            "ok": False,
            "blockers": [
                "live master audio is not audible yet",
                "live deck_state has no citable track_id at confidence floor",
            ],
        },
        rekordbox_audio_settings_check={
            "ok": True,
            "path": "/tmp/rekordbox3.settings",
            "current": {
                "audio_output_device_name": "Aggregate Device",
                "audio_input_device_name": None,
                "audio_device_rate": "48000.0",
            },
            "recent": [],
            "blockers": [],
        },
        nowplaying_check={
            "available": True,
            "ok": True,
            "full_title": "Web video",
            "bundle_identifier": "com.apple.WebKit.GPU",
            "playback_rate": 1.0,
            "is_playing": True,
            "looks_like_rekordbox": False,
        },
    )

    diagnosis = summary["course3_audio_diagnosis"]
    assert diagnosis["code"] == "rekordbox_saved_route_capture_rate_mismatch"
    assert diagnosis["severity"] == "fix_rate"
    assert diagnosis["route_capture_rate_mismatch"]["rekordbox_output_device"] == "Aggregate Device"
    assert (
        diagnosis["route_capture_rate_mismatch"]["matched_capture_device"]
        == "rekordbox Aggregate Device"
    )
    assert "from 44100Hz to 48000Hz" in diagnosis["next_action"]
    assert diagnosis["operator_action"]["route"] == (
        "rekordbox Aggregate Device @ 48000Hz"
    )
    assert diagnosis["operator_action"]["current_capture_route"] == (
        "rekordbox Aggregate Device @ 44100Hz"
    )
    assert diagnosis["operator_action"]["current_rekordbox_route"] == (
        "Aggregate Device @ 48000Hz"
    )
    assert diagnosis["rekordbox_route_hint"]["current_rekordbox_capture_row"]["name"] == (
        "rekordbox Aggregate Device"
    )
    doctor = summary["course3_route_doctor"]
    assert doctor["status"] == "fix_rate"
    assert doctor["route"] == "rekordbox Aggregate Device @ 48000Hz"
    assert doctor["next_step"].startswith("Set Rekordbox's 'Aggregate Device' route")
    assert doctor["operator_steps"][0] == diagnosis["next_action"]
    assert "Stop unrelated browser/system media so Now Playing can point at Rekordbox." in doctor[
        "operator_steps"
    ]


def test_course3_route_doctor_reports_ready_proof_path() -> None:
    doctor = readiness.build_course3_route_doctor(
        course3_ready=True,
        diagnosis={
            "code": "live_deck_context_ready",
            "severity": "ready",
            "next_action": "Run the Course 3 lens proof.",
        },
    )

    assert doctor["ok"] is True
    assert doctor["status"] == "ready"
    assert doctor["diagnosis_code"] == "live_deck_context_ready"
    assert doctor["next_step"] == "Run the Course 3 lens proof."
    assert doctor["readiness_command"].startswith(
        "uv run python scripts/learn_live_readiness.py --require course3"
    )


def test_build_summary_explains_nowplaying_source_mismatch() -> None:
    summary = readiness.build_summary(
        requirement="course3",
        socket_check={"ok": True},
        rekordbox_check={"ok": True},
        midi_check={"ok": True, "ports": ["DDJ-FLX4"], "controller_matches": ["DDJ-FLX4"]},
        usb_check={"ok": True, "controller_matches": ["DDJ-FLX4"]},
        audio_check={
            "ok": True,
            "loopback_present": True,
            "dj_audio_present": True,
            "controller_audio_present": True,
        },
        audio_route_check={
            "available": True,
            "ok": True,
            "output_device": "BlackHole 16ch",
            "blockers": [],
        },
        loopback_self_test_check={"enabled": True, "ok": True, "blockers": []},
        loopback_signal_check={
            "enabled": True,
            "ok": False,
            "blockers": ["direct loopback capture is silent"],
        },
        capture_matrix_check={
            "enabled": True,
            "ok": False,
            "rows": [
                {
                    "name": "BlackHole 2ch",
                    "rms": 0.0,
                    "peak": 0.0,
                    "sample_rate": 48000,
                    "signal": False,
                }
            ],
            "blockers": ["all sampled DJ/loopback capture inputs are below signal floor"],
        },
        live_context_check={
            "ok": False,
            "blockers": ["live deck_state has no citable track_id at confidence floor"],
        },
        rekordbox_audio_settings_check={
            "ok": True,
            "path": "/tmp/rekordbox3.settings",
            "current": {
                "audio_output_device_name": "BlackHole 2ch",
                "audio_input_device_name": "BlackHole 2ch",
                "audio_device_rate": "48000.0",
            },
            "recent": [],
            "blockers": [],
        },
        nowplaying_check={
            "available": True,
            "ok": True,
            "full_title": "The Diary Of A CEO - unrelated podcast",
            "bundle_identifier": "com.apple.WebKit.GPU",
            "playback_rate": 0.0,
            "is_playing": False,
            "looks_like_rekordbox": False,
        },
    )

    nowplaying_blockers = [
        blocker for blocker in summary["blockers"] if "macOS now-playing" in blocker
    ]
    assert nowplaying_blockers
    assert "not Rekordbox" in nowplaying_blockers[0]
    diagnosis = summary["course3_audio_diagnosis"]
    assert diagnosis["code"] == "loopback_route_healthy_external_playback_absent"
    assert diagnosis["nowplaying_hint"] == nowplaying_blockers[0]
    assert "active playing source" in diagnosis["next_action"]
    assert diagnosis["operator_action"]["nowplaying_blocker"] == nowplaying_blockers[0]
    assert diagnosis["operator_action"]["steps"][0] == (
        "Stop unrelated media or make Rekordbox the active playing source."
    )


def test_course3_operator_action_uses_current_rekordbox_route_without_hint() -> None:
    diagnosis = readiness.diagnose_course3_audio(
        audio_route_check={"available": True, "ok": True, "blockers": []},
        loopback_self_test_check={
            "enabled": True,
            "ok": True,
            "device": {"name": "BlackHole 16ch", "sample_rate": 48000},
        },
        loopback_signal_check={"enabled": True, "ok": False},
        capture_matrix_check={
            "enabled": True,
            "ok": False,
            "rows": [
                {
                    "name": "BlackHole 16ch",
                    "sample_rate": 48000,
                    "rms": 0.0,
                    "peak": 0.0,
                    "signal": False,
                }
            ],
            "blockers": ["all sampled DJ/loopback capture inputs are below signal floor"],
        },
        live_context_check={"ok": False},
        rekordbox_audio_settings_check={
            "ok": True,
            "path": "/tmp/rekordbox3.settings",
            "current": {
                "audio_output_device_name": "Aggregate Device",
                "audio_device_rate": "48000.0",
            },
            "recent": [],
            "blockers": [],
        },
    )

    assert diagnosis["code"] == "loopback_route_healthy_external_playback_absent"
    assert diagnosis["rekordbox_route_hint"] is None
    assert diagnosis["operator_action"]["route"] == "Aggregate Device @ 48000Hz"
    assert "Aggregate Device @ 48000Hz" in diagnosis["operator_action"]["prompt"]


def test_course3_operator_action_prefers_auto_master_when_current_route_unaligned() -> None:
    diagnosis = readiness.diagnose_course3_audio(
        audio_route_check={
            "available": True,
            "ok": True,
            "output_device": "BlackHole 16ch",
            "blockers": [],
        },
        loopback_self_test_check={
            "enabled": True,
            "ok": True,
            "device": {"name": "BlackHole 16ch", "sample_rate": 48000},
        },
        loopback_signal_check={"enabled": True, "ok": False},
        capture_matrix_check={
            "enabled": True,
            "ok": False,
            "rows": [
                {
                    "name": "DDJ-FLX4",
                    "sample_rate": 44100,
                    "rms": 0.0001,
                    "peak": 0.0007,
                    "signal": False,
                },
                {
                    "name": "BlackHole 16ch",
                    "sample_rate": 48000,
                    "rms": 0.0,
                    "peak": 0.0,
                    "signal": False,
                },
            ],
            "blockers": ["all sampled DJ/loopback capture inputs are below signal floor"],
        },
        live_context_check={"ok": False},
        rekordbox_audio_settings_check={
            "ok": True,
            "path": "/tmp/rekordbox3.settings",
            "current": {
                "audio_output_device_name": "Aggregate Device",
                "audio_device_rate": "48000.0",
            },
            "recent": [],
            "blockers": [],
        },
        auto_master_recommendation={
            "status": "ready",
            "device_name": "BlackHole 16ch",
            "sample_rate": 48000,
            "live_signal": False,
        },
    )

    assert diagnosis["rekordbox_route_hint"]["current_rekordbox_route_aligned"] is False
    assert diagnosis["operator_action"]["route"] == "BlackHole 16ch @ 48000Hz"
    assert (
        diagnosis["operator_action"]["current_rekordbox_route"]
        == "Aggregate Device @ 48000Hz"
    )
    assert diagnosis["operator_action"]["target_capture_route"] == "BlackHole 16ch @ 48000Hz"


def test_selected_loopback_silent_names_multi_output_capture_trap() -> None:
    diagnosis = readiness.diagnose_course3_audio(
        audio_route_check={
            "available": True,
            "ok": False,
            "output_device": "MacBook Pro Speakers (eqMac)",
            "blockers": ["current macOS output route is not loopback"],
        },
        loopback_signal_check={
            "enabled": True,
            "ok": False,
            "blockers": ["direct loopback capture is silent"],
        },
        capture_matrix_check={
            "enabled": True,
            "ok": False,
            "rows": [
                {
                    "name": "DDJ-FLX4",
                    "sample_rate": 48000,
                    "rms": 0.000107,
                    "peak": 0.000519,
                    "signal": False,
                },
                {
                    "name": "BlackHole 16ch",
                    "sample_rate": 48000,
                    "rms": 0.0,
                    "peak": 0.0,
                    "signal": False,
                },
            ],
            "blockers": ["all sampled DJ/loopback capture inputs are below signal floor"],
        },
        live_context_check={"ok": False},
        rekordbox_audio_settings_check={
            "ok": True,
            "path": "/tmp/rekordbox3.settings",
            "current": {
                "audio_output_device_name": "Multi-Output Device",
                "audio_device_rate": "48000.0",
            },
            "recent": [],
            "blockers": [],
        },
        auto_master_recommendation={
            "status": "ready",
            "device_name": "BlackHole 16ch",
            "sample_rate": 48000,
            "live_signal": False,
        },
    )

    assert diagnosis["code"] == "selected_loopback_silent"
    assert "Multi-Output Device" in diagnosis["next_action"]
    assert "aggregate that includes" in diagnosis["next_action"]
    assert diagnosis["rekordbox_route_hint"]["current_rekordbox_route_aligned"] is False
    assert diagnosis["operator_action"]["current_rekordbox_route"] == (
        "Multi-Output Device @ 48000Hz"
    )
    assert diagnosis["operator_action"]["target_capture_route"] == "BlackHole 16ch @ 48000Hz"


def test_course3_operator_action_uses_auto_master_when_rekordbox_route_unknown() -> None:
    diagnosis = readiness.diagnose_course3_audio(
        audio_route_check={"available": True, "ok": True, "blockers": []},
        loopback_self_test_check={
            "enabled": True,
            "ok": True,
            "device": {"name": "BlackHole 16ch", "sample_rate": 48000},
        },
        loopback_signal_check={"enabled": True, "ok": False},
        capture_matrix_check={
            "enabled": True,
            "ok": False,
            "rows": [
                {
                    "name": "BlackHole 16ch",
                    "sample_rate": 48000,
                    "rms": 0.0,
                    "peak": 0.0,
                    "signal": False,
                }
            ],
            "blockers": ["all sampled DJ/loopback capture inputs are below signal floor"],
        },
        live_context_check={"ok": False},
        auto_master_recommendation={
            "status": "ready",
            "device_name": "BlackHole 16ch",
            "sample_rate": 48000,
            "live_signal": False,
        },
    )

    assert diagnosis["operator_action"]["route"] == "BlackHole 16ch @ 48000Hz"
    assert "BlackHole 16ch @ 48000Hz" in diagnosis["operator_action"]["steps"][0]


def test_summarize_live_course3_context_requires_citable_deck_track() -> None:
    summary = readiness.summarize_live_course3_context(
        frames_seen=1,
        last_context={
            "music": 0.08,
            "audible": True,
            "deck": "A",
            "deck_state": {"A": {"track_id": None, "confidence": 0.0}},
        },
        last_lens=None,
        max_music=0.08,
    )

    assert summary["ok"] is False
    assert summary["audio_active"] is True
    assert summary["deck_attributed"] is True
    assert summary["deck_track_citable"] is False
    assert "live deck_state has no citable track_id at confidence floor" in summary[
        "blockers"
    ]


def test_summarize_live_course3_context_rejects_silent_frame_even_if_lens_is_audible() -> None:
    summary = readiness.summarize_live_course3_context(
        frames_seen=28,
        last_context={
            "music": 0.0,
            "audible": True,
            "deck": "none",
            "phase": "silent",
            "deck_state": {},
        },
        last_lens={
            "audio_active": True,
            "deck_attributed": False,
            "deck_track_citable": False,
        },
        max_music=0.0,
    )

    assert summary["ok"] is False
    assert summary["audio_active"] is False
    assert "live master audio is not audible yet" in summary["blockers"]
    assert "live audio is not attributed to deck A, B, or mix" in summary["blockers"]


def test_summarize_live_course3_context_accepts_citable_deck_track() -> None:
    summary = readiness.summarize_live_course3_context(
        frames_seen=1,
        last_context={
            "music": 0.08,
            "audible": True,
            "deck": "A",
            "deck_state": {"A": {"track_id": "track-1", "confidence": 0.85}},
        },
        last_lens=None,
        max_music=0.08,
    )

    assert summary["ok"] is True
    assert summary["blockers"] == []


def test_check_live_course3_context_works_inside_running_event_loop(monkeypatch) -> None:
    async def fake_check(_url: str, *, seconds: float) -> dict:
        return {
            "ok": True,
            "seconds": seconds,
            "blockers": [],
        }

    monkeypatch.setattr(readiness, "_check_live_course3_context_async", fake_check)

    async def run() -> dict:
        return readiness.check_live_course3_context("ws://example.invalid:8765", seconds=0.1)

    summary = asyncio.run(run())

    assert summary["ok"] is True
    assert summary["seconds"] == 0.1


def test_build_summary_allows_course3_without_controller_when_live_route_is_ready() -> None:
    summary = readiness.build_summary(
        requirement="course3",
        socket_check={"ok": True},
        rekordbox_check={"ok": True},
        midi_check={"ok": False, "ports": [], "controller_matches": []},
        usb_check={"ok": False, "controller_matches": []},
        audio_check={
            "ok": True,
            "loopback_present": True,
            "dj_audio_present": True,
        },
    )

    assert summary["passed"] is True
    assert summary["readiness"]["physical_learn"] is False
    assert summary["readiness"]["course3_audio"] is True
    assert "physical controller is not visible as a MIDI input" not in summary["blockers"]
    assert "physical controller is not visible on USB or controller audio" not in summary["blockers"]


def test_build_summary_refuses_course3_without_dj_audio_device() -> None:
    summary = readiness.build_summary(
        requirement="course3",
        socket_check={"ok": True},
        rekordbox_check={"ok": True},
        midi_check={"ok": True, "ports": ["DDJ-FLX4"], "controller_matches": ["DDJ-FLX4"]},
        usb_check={"ok": True, "controller_matches": ["DDJ-FLX4"]},
        audio_check={
            "ok": True,
            "loopback_present": True,
            "dj_audio_present": False,
        },
    )

    assert summary["passed"] is False
    assert summary["readiness"]["course3_audio"] is False
    assert "DJ app or controller audio device is not visible" in summary["blockers"]


def test_build_summary_names_bluetooth_midi_only_flx4_for_course3_audio() -> None:
    summary = readiness.build_summary(
        requirement="course3",
        socket_check={"ok": True},
        rekordbox_check={"ok": True},
        midi_check={
            "ok": True,
            "ports": ["DDJ-FLX4 Bluetooth MIDI"],
            "controller_matches": ["DDJ-FLX4 Bluetooth MIDI"],
        },
        usb_check={"ok": False, "controller_matches": []},
        audio_check={
            "ok": True,
            "loopback_present": True,
            "dj_audio_present": False,
            "controller_audio_present": False,
        },
    )

    assert summary["passed"] is False
    assert summary["readiness"]["course3_audio"] is False
    assert (
        "DDJ-FLX4 Bluetooth MIDI does not provide controller audio to this Mac; "
        "use USB or a routed Rekordbox/loopback audio device"
    ) in summary["blockers"]
    assert "DJ app or controller audio device is not visible" not in summary["blockers"]
    assert summary["course3_route_doctor"]["operator_steps"][0] == (
        "Connect the DDJ-FLX4 by USB; Bluetooth MIDI is not enough for routed-audio proof."
    )


def test_probe_help_runs_when_invoked_by_script_path() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    proc = subprocess.run(
        [sys.executable, "scripts/learn_live_readiness.py", "--help"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    assert proc.returncode == 0
    assert "--require" in proc.stdout
    assert "--loopback-signal-seconds" in proc.stdout
    assert "--loopback-self-test-seconds" in proc.stdout
    assert "--capture-matrix-seconds" in proc.stdout
    assert "--out" in proc.stdout
    assert "screen" in proc.stdout
    assert "physical" in proc.stdout
    assert "course3" in proc.stdout


def test_default_cli_emits_json_even_when_not_ready() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    proc = subprocess.run(
        [sys.executable, "scripts/learn_live_readiness.py", "--url", "ws://127.0.0.1:9"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )

    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert payload["requirement"] == "none"
    assert "checks" in payload
    assert payload["readiness"]["screen_learn"] is False


def test_cli_writes_readiness_artifact(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    out = tmp_path / "readiness.json"
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/learn_live_readiness.py",
            "--url",
            "ws://127.0.0.1:9",
            "--out",
            str(out),
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )

    assert proc.returncode == 0
    stdout_payload = json.loads(proc.stdout)
    file_payload = json.loads(out.read_text(encoding="utf-8"))
    assert file_payload["requirement"] == "none"
    assert file_payload == stdout_payload
