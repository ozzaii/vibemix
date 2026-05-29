#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Preflight the live Learn proof environment.

This does not prove a lesson by itself. It answers the boring but crucial
question before the live probes run: can this Mac currently see the sidecar
socket, Rekordbox, the controller as MIDI/USB/audio, and the loopback audio
devices that Course 3 depends on?
"""
from __future__ import annotations

import argparse
import asyncio
import json
import shutil
import subprocess
import sys
import threading
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse

DEFAULT_WS_URL = "ws://127.0.0.1:8765"
CONTROLLER_NEEDLES = ("ddj", "flx", "pioneer", "alphatheta")
BLUETOOTH_NEEDLES = ("bluetooth", "bt", "ble")
AUDIO_LOOPBACK_NEEDLES = ("blackhole", "loopback", "vb-cable")
DJ_AUDIO_NEEDLES = ("rekordbox aggregate", "ddj", "flx", "pioneer", "alphatheta")
CAPTURE_MATRIX_NEEDLES = AUDIO_LOOPBACK_NEEDLES + DJ_AUDIO_NEEDLES + ("aggregate",)
Requirement = Literal["none", "screen", "physical", "course3"]
AUDIBLE_MUSIC_FLOOR = 0.012
LOOPBACK_SIGNAL_RMS_FLOOR = 0.003
CAPTURE_SIGNAL_RMS_FLOOR = LOOPBACK_SIGNAL_RMS_FLOOR
EXPECTED_CAPTURE_SAMPLE_RATE = 48000
DECK_CITE_MIN_CONF = 0.6
ATTRIBUTED_DECKS = frozenset({"A", "B", "mix"})
_REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REKORDBOX_SETTINGS_PATH = (
    Path.home()
    / "Library"
    / "Application Support"
    / "Pioneer"
    / "rekordbox6"
    / "rekordbox3.settings"
)
COURSE3_READINESS_COMMAND = (
    "uv run python scripts/learn_live_readiness.py --require course3 "
    "--live-context-seconds 5 --loopback-signal-seconds 2 "
    "--loopback-self-test-seconds 1 --capture-matrix-seconds 2 "
    "--out /tmp/vibemix-live-learn-proof/learn-course3-readiness-current.json"
)
PHYSICAL_READINESS_COMMAND = (
    "uv run python scripts/learn_live_readiness.py --require physical "
    "--out /tmp/vibemix-live-learn-proof/learn-physical-readiness-current.json"
)
PHYSICAL_PROOF_COMMAND = (
    "uv run python scripts/run_learn_live_proof.py --start-app --no-screen "
    "--physical --wait-physical-seconds 30 --physical-seconds 40 "
    "--say-physical-prompts --auto-master-input "
    "--out /tmp/vibemix-live-learn-proof/proof-physical-ddj-current.json"
)
COURSE3_PROOF_COMMAND = (
    "uv run python scripts/run_learn_live_proof.py --start-app --no-screen "
    "--course3 --seed-course3-unlocked --auto-master-input "
    "--nudge-rekordbox-playback --require-count-in --say-course3-prompts "
    "--wait-loopback-signal-seconds 30 --wait-capture-signal-seconds 30 "
    "--wait-course3-seconds 120 --course3-context-seconds 5 "
    "--loopback-signal-seconds 2 --loopback-self-test-seconds 1 "
    "--capture-matrix-seconds 2 "
    "--out /tmp/vibemix-live-learn-proof/proof-course3-auto-master-current.json"
)
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


@dataclass(frozen=True, slots=True)
class CommandResult:
    ok: bool
    stdout: str = ""
    stderr: str = ""
    returncode: int | None = None
    error: str | None = None


def _lower_lines(text: str) -> list[tuple[str, str]]:
    return [(line.strip(), line.lower()) for line in text.splitlines() if line.strip()]


def matching_lines(text: str, needles: tuple[str, ...]) -> list[str]:
    """Return lines containing any case-insensitive needle."""
    return [
        original
        for original, lowered in _lower_lines(text)
        if any(needle in lowered for needle in needles)
    ]


def matching_names(names: list[str], needles: tuple[str, ...]) -> list[str]:
    return [
        name
        for name in names
        if any(needle in name.lower() for needle in needles)
    ]


def bluetooth_midi_controller_matches(midi_check: dict[str, Any]) -> list[str]:
    """Return controller-like MIDI ports that appear to be Bluetooth transport."""
    rows: list[str] = []
    for source_key in ("controller_matches", "ports"):
        source = midi_check.get(source_key)
        if not isinstance(source, list):
            continue
        for raw in source:
            name = str(raw).strip()
            lowered = name.lower()
            if (
                name
                and any(needle in lowered for needle in CONTROLLER_NEEDLES)
                and any(needle in lowered for needle in BLUETOOTH_NEEDLES)
                and name not in rows
            ):
                rows.append(name)
    return rows


def _trim_rows(rows: list[str], *, limit: int = 8, width: int = 240) -> list[str]:
    trimmed: list[str] = []
    for row in rows[:limit]:
        if len(row) <= width:
            trimmed.append(row)
        else:
            trimmed.append(row[: width - 3] + "...")
    return trimmed


def _open_sidecar_websocket(url: str, *, timeout_s: float):
    """Open a real WebSocket handshake to the sidecar.

    The old readiness check used a raw TCP connect. That answered "is something
    listening" but made the WebSocket server log invalid-handshake tracebacks on
    every readiness poll. A real handshake keeps proof artifacts' stderr tails
    useful for actual app failures.
    """
    from websockets.sync.client import connect

    return connect(
        url,
        open_timeout=timeout_s,
        close_timeout=max(0.05, min(0.35, timeout_s)),
        ping_interval=None,
        proxy=None,
    )


def _socket_listener(port: int) -> dict[str, Any] | None:
    """Return the local process listening on a TCP port, when lsof can see it."""
    result = run_command(
        ["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN"],
        timeout_s=1.5,
    )
    if not result.stdout:
        return None
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    if len(lines) < 2:
        return None
    parts = lines[1].split()
    if len(parts) < 2:
        return None
    command = parts[0]
    pid = parts[1]
    return {
        "command": command,
        "pid": pid,
        "raw": lines[1],
    }


def check_socket(url: str = DEFAULT_WS_URL, *, timeout_s: float = 0.35) -> dict[str, Any]:
    parsed = urlparse(url)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 8765
    try:
        with _open_sidecar_websocket(url, timeout_s=timeout_s):
            return {
                "ok": True,
                "url": url,
                "host": host,
                "port": port,
                "protocol": "websocket",
            }
    except Exception as exc:
        listener = _socket_listener(port)
        return {
            "ok": False,
            "url": url,
            "host": host,
            "port": port,
            "listener": listener,
            "error": str(exc),
        }


def run_command(args: list[str], *, timeout_s: float = 3.0) -> CommandResult:
    try:
        proc = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )
    except FileNotFoundError as exc:
        return CommandResult(ok=False, error=str(exc))
    except subprocess.TimeoutExpired as exc:
        return CommandResult(
            ok=False,
            stdout=exc.stdout or "",
            stderr=exc.stderr or "",
            error=f"timed out after {timeout_s:.1f}s",
        )
    return CommandResult(
        ok=proc.returncode == 0,
        stdout=proc.stdout,
        stderr=proc.stderr,
        returncode=proc.returncode,
    )


def _float_or_none(raw: Any) -> float | None:
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def check_nowplaying() -> dict[str, Any]:
    cli = shutil.which("nowplaying-cli") or "/opt/homebrew/bin/nowplaying-cli"
    if not Path(cli).is_file():
        return {
            "available": False,
            "ok": False,
            "cli": cli,
            "error": "nowplaying-cli not found",
        }
    result = run_command([cli, "get-raw"], timeout_s=1.5)
    if not result.ok:
        return {
            "available": True,
            "ok": False,
            "cli": cli,
            "error": result.error or result.stderr.strip() or f"exit {result.returncode}",
        }
    try:
        raw = json.loads(result.stdout or "{}")
    except json.JSONDecodeError as exc:
        return {
            "available": True,
            "ok": False,
            "cli": cli,
            "error": f"invalid nowplaying JSON: {exc}",
        }
    if not isinstance(raw, dict):
        raw = {}
    title = str(raw.get("kMRMediaRemoteNowPlayingInfoTitle") or "").strip()
    artist = str(raw.get("kMRMediaRemoteNowPlayingInfoArtist") or "").strip()
    bundle = str(raw.get("kMRMediaRemoteNowPlayingInfoClientBundleIdentifier") or "").strip()
    playback_rate = _float_or_none(raw.get("kMRMediaRemoteNowPlayingInfoPlaybackRate"))
    full_title = f"{artist} - {title}" if artist and title else title
    return {
        "available": True,
        "ok": bool(title or artist),
        "cli": cli,
        "title": title,
        "artist": artist,
        "full_title": full_title,
        "bundle_identifier": bundle,
        "playback_rate": playback_rate,
        "is_playing": bool(playback_rate and playback_rate > 0),
        "looks_like_rekordbox": "rekordbox" in bundle.lower(),
        "error": None,
    }


def check_rekordbox_process(ps_output: str | None = None) -> dict[str, Any]:
    if ps_output is None:
        result = run_command(["ps", "-axo", "pid,comm,args"])
        ps_output = result.stdout if result.ok or result.stdout else ""
        error = result.error
    else:
        error = None
    matches = matching_lines(ps_output, ("rekordbox",))
    return {"ok": bool(matches), "matches": _trim_rows(matches), "error": error}


def check_midi_ports(port_names: list[str] | None = None) -> dict[str, Any]:
    error: str | None = None
    if port_names is None:
        try:
            from scripts.sniff_controller import enumerate_ports

            port_names = enumerate_ports()
        except Exception as exc:  # pragma: no cover - depends on local MIDI stack
            port_names = []
            error = repr(exc)
    matches = matching_names(list(port_names), CONTROLLER_NEEDLES)
    return {
        "ok": bool(matches),
        "ports": list(port_names),
        "controller_matches": matches,
        "error": error,
    }


def check_usb_controller(usb_output: str | None = None) -> dict[str, Any]:
    available = sys.platform == "darwin"
    error: str | None = None
    source = "provided"
    if usb_output is None and available:
        result = run_command(["system_profiler", "SPUSBDataType"], timeout_s=6.0)
        usb_output = result.stdout
        error = result.error or (None if result.ok else result.stderr.strip() or None)
        source = "SPUSBDataType"
    elif usb_output is None:
        usb_output = ""
        source = "unavailable"
    matches = matching_lines(usb_output, CONTROLLER_NEEDLES)
    if not matches and source == "SPUSBDataType" and available:
        result = run_command(["system_profiler", "SPAudioDataType"], timeout_s=6.0)
        audio_output = result.stdout
        audio_error = result.error or (None if result.ok else result.stderr.strip() or None)
        audio_matches = matching_lines(audio_output, CONTROLLER_NEEDLES)
        if audio_matches:
            matches = audio_matches
            source = "SPAudioDataType"
            error = error or audio_error
    return {
        "ok": bool(matches),
        "available": available,
        "controller_matches": matches[:12],
        "source": source,
        "error": error,
    }


def _sounddevice_names() -> tuple[list[str], str | None]:
    try:
        import sounddevice as sd

        devices = sd.query_devices()
    except Exception as exc:  # pragma: no cover - depends on local audio stack
        return [], repr(exc)
    names: list[str] = []
    for row in devices:
        if isinstance(row, dict):
            name = row.get("name")
        else:
            name = getattr(row, "get", lambda _key, _default=None: None)("name")
        if isinstance(name, str) and name:
            names.append(name)
    return names, None


def check_audio_devices(
    *,
    sounddevice_names: list[str] | None = None,
    profiler_output: str | None = None,
) -> dict[str, Any]:
    sounddevice_error: str | None = None
    if sounddevice_names is None:
        sounddevice_names, sounddevice_error = _sounddevice_names()

    profiler_available = sys.platform == "darwin"
    profiler_error: str | None = None
    if profiler_output is None and profiler_available:
        result = run_command(["system_profiler", "SPAudioDataType"], timeout_s=6.0)
        profiler_output = result.stdout
        profiler_error = result.error or (None if result.ok else result.stderr.strip() or None)
    elif profiler_output is None:
        profiler_output = ""

    profiler_matches = matching_lines(
        profiler_output,
        AUDIO_LOOPBACK_NEEDLES + DJ_AUDIO_NEEDLES,
    )
    all_names = list(sounddevice_names) + profiler_matches
    loopback_matches = matching_names(all_names, AUDIO_LOOPBACK_NEEDLES)
    dj_matches = matching_names(all_names, DJ_AUDIO_NEEDLES)
    controller_audio_matches = matching_names(all_names, CONTROLLER_NEEDLES)
    rekordbox_aggregate_matches = matching_names(all_names, ("rekordbox aggregate",))
    return {
        "ok": bool(loopback_matches),
        "loopback_present": bool(loopback_matches),
        "dj_audio_present": bool(dj_matches),
        "controller_audio_present": bool(controller_audio_matches),
        "rekordbox_aggregate_present": bool(rekordbox_aggregate_matches),
        "sounddevice_names": list(sounddevice_names),
        "sounddevice_error": sounddevice_error,
        "profiler_available": profiler_available,
        "profiler_matches": profiler_matches[:16],
        "profiler_error": profiler_error,
    }


def _current_switch_audio_source(kind: str) -> CommandResult:
    return run_command(["SwitchAudioSource", "-c", "-t", kind], timeout_s=1.5)


def check_audio_route(
    *,
    current_output: str | None = None,
    current_system: str | None = None,
    switch_available: bool | None = None,
) -> dict[str, Any]:
    """Inspect whether macOS default output is aimed at a loopback device.

    This is diagnostic, not a proof requirement. Rekordbox may use its own
    aggregate device and bypass the default output entirely, so live socket
    context remains authoritative. When the live context is silent, this check
    gives the operator the likely next fix instead of only saying "no audio".
    """
    output_error: str | None = None
    system_error: str | None = None
    if switch_available is None:
        result = run_command(["which", "SwitchAudioSource"], timeout_s=1.5)
        switch_available = result.ok
    if current_output is None and switch_available:
        result = _current_switch_audio_source("output")
        current_output = result.stdout.strip()
        output_error = result.error or (None if result.ok else result.stderr.strip() or None)
    if current_system is None and switch_available:
        result = _current_switch_audio_source("system")
        current_system = result.stdout.strip()
        system_error = result.error or (None if result.ok else result.stderr.strip() or None)

    names = [name for name in (current_output, current_system) if name]
    loopback_matches = matching_names(names, AUDIO_LOOPBACK_NEEDLES)
    ok = bool(loopback_matches)
    blockers: list[str] = []
    if switch_available and not ok:
        current = current_output or current_system or "unknown"
        blockers.append(
            f"current macOS output route is {current!r}, not a loopback capture device"
        )
    elif not switch_available:
        blockers.append("could not inspect macOS output route; SwitchAudioSource is unavailable")

    return {
        "ok": ok,
        "available": bool(switch_available),
        "output_device": current_output or None,
        "system_device": current_system or None,
        "loopback_matches": loopback_matches,
        "blockers": blockers,
        "errors": {
            "output": output_error,
            "system": system_error,
        },
    }


def _device_setup_row(value_name: str, setup: ET.Element) -> dict[str, Any]:
    def attr(name: str) -> str | None:
        value = setup.attrib.get(name)
        return value if value not in {None, ""} else None

    return {
        "name": value_name,
        "device_type": attr("deviceType"),
        "audio_output_device_name": attr("audioOutputDeviceName"),
        "audio_input_device_name": attr("audioInputDeviceName"),
        "audio_device_rate": attr("audioDeviceRate") or attr("SampleRate"),
        "audio_device_buffer_size": attr("audioDeviceBufferSize") or attr("BufferSize"),
        "mixer_mode_internal": attr("MixerMode_Is_Internal"),
        "master_l": attr("OutputChannel_Master_L"),
        "master_r": attr("OutputChannel_Master_R"),
        "cue_l": attr("OutputChannel_Cue_L"),
        "cue_r": attr("OutputChannel_Cue_R"),
        "date": attr("Date"),
    }


def _sort_rekordbox_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def sort_key(row: dict[str, Any]) -> tuple[int, float]:
        is_current = 1 if row.get("name") == "audioDeviceManager" else 0
        try:
            date = float(row.get("date") or 0.0)
        except (TypeError, ValueError):
            date = 0.0
        return is_current, date

    return sorted(rows, key=sort_key, reverse=True)


def check_rekordbox_audio_settings(
    settings_path: Path | None = None,
) -> dict[str, Any]:
    """Read-only parse Rekordbox's persisted CoreAudio device settings."""
    path = settings_path or DEFAULT_REKORDBOX_SETTINGS_PATH
    try:
        root = ET.parse(path).getroot()
    except FileNotFoundError:
        return {
            "ok": False,
            "path": str(path),
            "error": "settings file not found",
            "current": None,
            "recent": [],
            "blockers": ["Rekordbox settings file was not found"],
        }
    except (OSError, ET.ParseError) as exc:
        return {
            "ok": False,
            "path": str(path),
            "error": repr(exc),
            "current": None,
            "recent": [],
            "blockers": ["Rekordbox settings file could not be parsed"],
        }

    rows: list[dict[str, Any]] = []
    for value in root.findall("VALUE"):
        name = value.attrib.get("name") or ""
        if not name.startswith("audioDeviceManager"):
            continue
        setup = value.find("DEVICESETUP")
        if setup is None:
            continue
        rows.append(_device_setup_row(name, setup))
    rows = _sort_rekordbox_rows(rows)
    current = next((row for row in rows if row.get("name") == "audioDeviceManager"), None)
    blockers: list[str] = []
    if not rows:
        blockers.append("Rekordbox settings did not contain audio device rows")
    if current is None and rows:
        blockers.append("Rekordbox current audioDeviceManager row is missing")
    return {
        "ok": bool(rows),
        "path": str(path),
        "error": None,
        "current": current,
        "recent": rows[:8],
        "blockers": blockers,
    }


def preferred_loopback_device_for_readiness(
    *,
    requirement: Requirement,
    audio_route_check: dict[str, Any] | None,
    rekordbox_audio_settings_check: dict[str, Any] | None,
) -> str:
    """Choose the loopback route to sample for direct signal/self-test checks."""
    if requirement == "course3" and isinstance(rekordbox_audio_settings_check, dict):
        current = rekordbox_audio_settings_check.get("current")
        if isinstance(current, dict):
            output_name = str(current.get("audio_output_device_name") or "").strip()
            if output_name and matching_names([output_name], AUDIO_LOOPBACK_NEEDLES):
                return output_name
    if isinstance(audio_route_check, dict):
        return str(audio_route_check.get("output_device") or "")
    return ""


def _info_name(info: Any) -> str:
    if isinstance(info, dict):
        value = info.get("name")
    else:
        value = getattr(info, "get", lambda _key, _default=None: None)("name")
    return str(value or "")


def _info_int(info: Any, key: str, default: int = 0) -> int:
    if isinstance(info, dict):
        value = info.get(key, default)
    else:
        value = getattr(info, "get", lambda _key, _default=None: default)(key, default)
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _sounddevice_rows() -> tuple[list[Any], str | None]:
    try:
        import sounddevice as sd

        return list(sd.query_devices()), None
    except Exception as exc:  # pragma: no cover - depends on local audio stack
        return [], repr(exc)


def _loopback_input_candidates(devices: list[Any]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for index, info in enumerate(devices):
        name = _info_name(info)
        if not name or _info_int(info, "max_input_channels") <= 0:
            continue
        if not matching_names([name], AUDIO_LOOPBACK_NEEDLES):
            continue
        sample_rate = _info_int(info, "default_samplerate", 48000)
        channels = max(1, min(2, _info_int(info, "max_input_channels", 1)))
        candidates.append(
            {
                "index": index,
                "name": name,
                "sample_rate": sample_rate,
                "channels": channels,
            }
        )
    return candidates


def _loopback_duplex_candidates(devices: list[Any]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for index, info in enumerate(devices):
        name = _info_name(info)
        if not name:
            continue
        input_channels = _info_int(info, "max_input_channels")
        output_channels = _info_int(info, "max_output_channels")
        if input_channels <= 0 or output_channels <= 0:
            continue
        if not matching_names([name], AUDIO_LOOPBACK_NEEDLES):
            continue
        sample_rate = _info_int(info, "default_samplerate", 48000)
        channels = max(1, min(2, input_channels, output_channels))
        candidates.append(
            {
                "index": index,
                "name": name,
                "sample_rate": sample_rate,
                "channels": channels,
            }
        )
    return candidates


def _capture_matrix_candidates(devices: list[Any]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for index, info in enumerate(devices):
        name = _info_name(info)
        if not name or _info_int(info, "max_input_channels") <= 0:
            continue
        if not matching_names([name], CAPTURE_MATRIX_NEEDLES):
            continue
        sample_rate = _info_int(info, "default_samplerate", 48000)
        channels = max(1, min(2, _info_int(info, "max_input_channels", 1)))
        candidates.append(
            {
                "index": index,
                "name": name,
                "sample_rate": sample_rate,
                "channels": channels,
            }
        )
    return candidates


def select_loopback_signal_device(
    devices: list[Any],
    *,
    preferred_device: str | None = None,
) -> dict[str, Any] | None:
    """Pick the loopback input to sample for a direct route signal check."""
    candidates = _loopback_input_candidates(devices)
    if not candidates:
        return None
    preferred = (preferred_device or "").strip().lower()

    def score(row: dict[str, Any]) -> tuple[int, int, int, int]:
        name = str(row["name"]).lower()
        exact = 1 if preferred and name == preferred else 0
        contains = 1 if preferred and (preferred in name or name in preferred) else 0
        rate_match = 1 if int(row["sample_rate"]) == 48000 else 0
        blackhole = 1 if "blackhole" in name else 0
        return exact, contains, rate_match, blackhole

    return max(candidates, key=score)


def select_loopback_route_device(
    devices: list[Any],
    *,
    preferred_device: str | None = None,
) -> dict[str, Any] | None:
    """Pick a duplex loopback device for an injected route self-test."""
    candidates = _loopback_duplex_candidates(devices)
    if not candidates:
        return None
    preferred = (preferred_device or "").strip().lower()

    def score(row: dict[str, Any]) -> tuple[int, int, int, int]:
        name = str(row["name"]).lower()
        exact = 1 if preferred and name == preferred else 0
        contains = 1 if preferred and (preferred in name or name in preferred) else 0
        rate_match = 1 if int(row["sample_rate"]) == 48000 else 0
        blackhole = 1 if "blackhole" in name else 0
        return exact, contains, rate_match, blackhole

    return max(candidates, key=score)


def _record_input_signal(
    *,
    device_index: int,
    sample_rate: int,
    channels: int,
    seconds: float,
) -> dict[str, float]:
    import numpy as np
    import sounddevice as sd

    frames = max(1, int(sample_rate * max(0.05, seconds)))
    audio = sd.rec(
        frames,
        samplerate=sample_rate,
        channels=channels,
        dtype="float32",
        device=device_index,
        blocking=True,
    )
    rms = float(np.sqrt(np.mean(np.square(audio)))) if audio.size else 0.0
    peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    return {"rms": rms, "peak": peak}


def _record_loopback_signal(**kwargs: Any) -> dict[str, float]:
    return _record_input_signal(**kwargs)


def _playrec_loopback_self_test(
    *,
    device_index: int,
    sample_rate: int,
    channels: int,
    seconds: float,
    amplitude: float = 0.08,
) -> dict[str, float]:
    import numpy as np
    import sounddevice as sd

    seconds = max(0.05, seconds)
    frames = max(1, int(sample_rate * seconds))
    timeline = np.arange(frames, dtype=np.float32) / float(sample_rate)
    tone = amplitude * np.sin(2 * np.pi * 440.0 * timeline)
    output = np.zeros((frames, channels), dtype=np.float32)
    output[:, 0] = tone
    if channels > 1:
        output[:, 1] = tone
    recorded = sd.playrec(
        output,
        samplerate=sample_rate,
        channels=channels,
        dtype="float32",
        device=(device_index, device_index),
        blocking=True,
    )
    rms = float(np.sqrt(np.mean(np.square(recorded)))) if recorded.size else 0.0
    peak = float(np.max(np.abs(recorded))) if recorded.size else 0.0
    return {
        "rms": rms,
        "peak": peak,
        "emitted_peak": float(amplitude),
    }


def check_loopback_signal(
    *,
    seconds: float,
    preferred_device: str | None = None,
    devices: list[Any] | None = None,
) -> dict[str, Any] | None:
    """Optionally sample the selected loopback input for direct signal energy."""
    if seconds <= 0:
        return None
    device_error: str | None = None
    if devices is None:
        devices, device_error = _sounddevice_rows()
    selected = select_loopback_signal_device(
        devices,
        preferred_device=preferred_device,
    )
    if selected is None:
        return {
            "ok": False,
            "enabled": True,
            "device": None,
            "seconds": round(float(seconds), 3),
            "rms": 0.0,
            "peak": 0.0,
            "rms_floor": LOOPBACK_SIGNAL_RMS_FLOOR,
            "blockers": ["no loopback input device could be sampled"],
            "error": device_error,
        }
    try:
        metrics = _record_loopback_signal(
            device_index=int(selected["index"]),
            sample_rate=int(selected["sample_rate"]),
            channels=int(selected["channels"]),
            seconds=seconds,
        )
        error = None
    except Exception as exc:  # pragma: no cover - depends on local audio stack
        metrics = {"rms": 0.0, "peak": 0.0}
        error = repr(exc)
    rms = float(metrics["rms"])
    peak = float(metrics["peak"])
    ok = rms >= LOOPBACK_SIGNAL_RMS_FLOOR
    blockers = [] if ok else ["direct loopback capture is silent"]
    return {
        "ok": ok,
        "enabled": True,
        "device": selected,
        "seconds": round(float(seconds), 3),
        "rms": round(rms, 6),
        "peak": round(peak, 6),
        "rms_floor": LOOPBACK_SIGNAL_RMS_FLOOR,
        "blockers": blockers,
        "error": error,
    }


def check_loopback_self_test(
    *,
    seconds: float,
    preferred_device: str | None = None,
    devices: list[Any] | None = None,
) -> dict[str, Any] | None:
    """Optionally inject a known tone through a duplex loopback and capture it."""
    if seconds <= 0:
        return None
    device_error: str | None = None
    if devices is None:
        devices, device_error = _sounddevice_rows()
    selected = select_loopback_route_device(
        devices,
        preferred_device=preferred_device,
    )
    if selected is None:
        return {
            "ok": False,
            "enabled": True,
            "device": None,
            "seconds": round(float(seconds), 3),
            "rms": 0.0,
            "peak": 0.0,
            "emitted_peak": 0.0,
            "rms_floor": LOOPBACK_SIGNAL_RMS_FLOOR,
            "blockers": ["no duplex loopback device could run the self-test"],
            "error": device_error,
        }
    try:
        metrics = _playrec_loopback_self_test(
            device_index=int(selected["index"]),
            sample_rate=int(selected["sample_rate"]),
            channels=int(selected["channels"]),
            seconds=seconds,
        )
        error = None
    except Exception as exc:  # pragma: no cover - depends on local audio stack
        metrics = {"rms": 0.0, "peak": 0.0, "emitted_peak": 0.0}
        error = repr(exc)
    rms = float(metrics["rms"])
    peak = float(metrics["peak"])
    ok = rms >= LOOPBACK_SIGNAL_RMS_FLOOR
    blockers = [] if ok else ["loopback route self-test did not capture injected signal"]
    return {
        "ok": ok,
        "enabled": True,
        "device": selected,
        "seconds": round(float(seconds), 3),
        "rms": round(rms, 6),
        "peak": round(peak, 6),
        "emitted_peak": round(float(metrics.get("emitted_peak") or 0.0), 6),
        "rms_floor": LOOPBACK_SIGNAL_RMS_FLOOR,
        "blockers": blockers,
        "error": error,
    }


def check_capture_matrix(
    *,
    seconds: float,
    devices: list[Any] | None = None,
) -> dict[str, Any] | None:
    """Optionally sample every relevant DJ/loopback input and rank signal."""
    if seconds <= 0:
        return None
    device_error: str | None = None
    if devices is None:
        devices, device_error = _sounddevice_rows()
    candidates = _capture_matrix_candidates(devices)
    rows: list[dict[str, Any]] = []
    for candidate in candidates:
        try:
            metrics = _record_input_signal(
                device_index=int(candidate["index"]),
                sample_rate=int(candidate["sample_rate"]),
                channels=int(candidate["channels"]),
                seconds=seconds,
            )
            error = None
        except Exception as exc:  # pragma: no cover - depends on local audio stack
            metrics = {"rms": 0.0, "peak": 0.0}
            error = repr(exc)
        rms = float(metrics["rms"])
        peak = float(metrics["peak"])
        rows.append(
            {
                **candidate,
                "rms": round(rms, 6),
                "peak": round(peak, 6),
                "signal": rms >= CAPTURE_SIGNAL_RMS_FLOOR,
                "error": error,
            }
        )
    rows.sort(key=lambda row: (float(row["rms"]), float(row["peak"])), reverse=True)
    top_signal = next((row for row in rows if row["signal"]), None)
    blockers: list[str] = []
    if not rows:
        blockers.append("no DJ or loopback capture inputs could be sampled")
    elif top_signal is None:
        blockers.append("all sampled DJ/loopback capture inputs are below signal floor")
    return {
        "ok": top_signal is not None,
        "enabled": True,
        "seconds": round(float(seconds), 3),
        "rms_floor": CAPTURE_SIGNAL_RMS_FLOOR,
        "rows": rows,
        "top_signal": top_signal,
        "blockers": blockers,
        "error": device_error,
    }


def _safe_json_loads(raw: str | bytes) -> dict[str, Any] | None:
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", errors="replace")
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _float_value(raw: Any, default: float = 0.0) -> float:
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


def _deck_state_has_citable_track(deck_state: Any, deck: str) -> bool:
    if not isinstance(deck_state, dict) or deck not in ATTRIBUTED_DECKS:
        return False
    rows = deck_state.values() if deck == "mix" else [deck_state.get(deck)]
    for row in rows:
        if not isinstance(row, dict) or not row.get("track_id"):
            continue
        if _float_value(row.get("confidence")) >= DECK_CITE_MIN_CONF:
            return True
    return False


def _course3_nowplaying_blocker(nowplaying_check: dict[str, Any] | None) -> str | None:
    if not isinstance(nowplaying_check, dict):
        return None
    if nowplaying_check.get("available") is False:
        return "macOS now-playing metadata is unavailable, so deck_state cannot cite a Rekordbox title"
    title = str(nowplaying_check.get("full_title") or "").strip()
    bundle = str(nowplaying_check.get("bundle_identifier") or "").strip()
    if not title:
        return None
    if nowplaying_check.get("looks_like_rekordbox") is True:
        return None
    source = bundle or "unknown app"
    playing = "playing" if nowplaying_check.get("is_playing") else "not playing"
    return (
        f"macOS now-playing is {title!r} from {source} ({playing}), not Rekordbox; "
        "deck_state needs a Rekordbox-published title that matches the imported library"
    )


def _course3_external_playback_action(
    *,
    rekordbox_hint: dict[str, Any] | None,
    rekordbox_audio_settings_check: dict[str, Any] | None = None,
    auto_master_recommendation: dict[str, Any] | None = None,
    nowplaying_blocker: str | None,
) -> dict[str, Any]:
    settings = (
        rekordbox_hint.get("current_rekordbox_settings")
        if isinstance(rekordbox_hint, dict)
        else None
    )
    if not isinstance(settings, dict) and isinstance(rekordbox_audio_settings_check, dict):
        current_settings = rekordbox_audio_settings_check.get("current")
        settings = current_settings if isinstance(current_settings, dict) else None
    settings = settings if isinstance(settings, dict) else {}
    device = str(settings.get("audio_output_device_name") or "").strip()
    sample_rate = _float_or_none(settings.get("audio_device_rate"))
    auto_device = ""
    auto_rate = None
    if isinstance(auto_master_recommendation, dict):
        auto_device = str(auto_master_recommendation.get("device_name") or "").strip()
        auto_rate = _float_or_none(auto_master_recommendation.get("sample_rate"))
    if auto_device and auto_rate:
        auto_route = f"{auto_device} @ {int(auto_rate)}Hz"
    elif auto_device:
        auto_route = auto_device
    else:
        auto_route = ""
    if device and sample_rate:
        current_route = f"{device} @ {int(sample_rate)}Hz"
    elif device:
        current_route = device
    else:
        current_route = ""

    current_route_aligned = (
        rekordbox_hint.get("current_rekordbox_route_aligned")
        if isinstance(rekordbox_hint, dict)
        else None
    )
    if current_route_aligned is False:
        route = auto_route or "the selected loopback capture route"
    elif current_route:
        route = current_route
    elif auto_route:
        route = auto_route
    else:
        route = "the selected loopback capture route"

    steps: list[str] = []
    if nowplaying_blocker:
        steps.append("Stop unrelated media or make Rekordbox the active playing source.")
    if current_route_aligned is False:
        if current_route and route:
            steps.append(
                "In Rekordbox Audio preferences, set the audio output from "
                f"{current_route} to {route}."
            )
        else:
            steps.append(
                "In Rekordbox Audio preferences, set the audio output to the "
                f"{route}."
            )
    steps.extend(
        [
            f"In Rekordbox, load and play a real library track through {route}.",
            "Raise the playing channel fader and master until the loopback capture has signal.",
            "Rerun the Course 3 live proof with --require-count-in.",
        ]
    )
    prompt = f"Play a real Rekordbox library track through {route} with channel and master faders up."
    if current_route_aligned is False:
        prompt = (
            f"Set Rekordbox audio to {route}, then play a real library track "
            "with channel and master faders up."
        )
    return {
        "prompt": prompt,
        "route": route,
        "current_rekordbox_route": current_route or None,
        "target_capture_route": auto_route or None,
        "nowplaying_blocker": nowplaying_blocker,
        "steps": steps,
    }


def _course3_rate_fix_operator_action(
    *,
    device: str,
    expected_rate: int,
    current_rate: int | None = None,
    current_rekordbox_rate: int | None = None,
    capture_device: str | None = None,
    first_step: str | None = None,
) -> dict[str, Any]:
    """Return a one-action Course 3 operator packet for sample-rate fixes."""
    device = device.strip() or "Rekordbox audio route"
    capture_device = (capture_device or "").strip()
    route_device = capture_device or device
    target_route = f"{route_device} @ {expected_rate}Hz"
    current_route = (
        f"{route_device} @ {current_rate}Hz"
        if current_rate
        else None
    )
    if first_step and first_step.strip():
        first_step_text = first_step.strip()
    elif capture_device and capture_device.lower() != device.lower():
        first_step_text = (
            f"Set Rekordbox's {device!r} route, sampled as {capture_device!r}, "
            f"from {current_rate}Hz to {expected_rate}Hz in Audio MIDI Setup."
        )
    elif current_rate:
        first_step_text = (
            f"Set Rekordbox's {device!r} route from {current_rate}Hz to "
            f"{expected_rate}Hz."
        )
    else:
        first_step_text = f"Set Rekordbox's {device!r} route to {expected_rate}Hz."
    if current_rekordbox_rate:
        current_rekordbox_route = f"{device} @ {current_rekordbox_rate}Hz"
    elif current_rate and not capture_device:
        current_rekordbox_route = f"{device} @ {current_rate}Hz"
    else:
        current_rekordbox_route = device

    return {
        "prompt": f"Set Rekordbox's {device!r} route to {expected_rate}Hz.",
        "route": target_route,
        "current_rekordbox_route": current_rekordbox_route,
        "current_capture_route": current_route,
        "target_capture_route": target_route,
        "steps": [
            first_step_text,
            "Play a real Rekordbox library track through the routed master output.",
            "Raise the playing channel fader and master until capture has signal.",
            "Rerun the Course 3 live proof with --require-count-in.",
        ],
    }


def summarize_live_course3_context(
    *,
    frames_seen: int,
    last_context: dict[str, Any] | None,
    last_lens: dict[str, Any] | None,
    max_music: float,
) -> dict[str, Any]:
    """Summarize live flat-frame context required before Course 3 proof.

    This is not the count-in proof. It only answers whether the live sidecar can
    currently hear routed audio and attribute it to a citable deck row. Count-in
    and cue readiness remain owned by ``live_course3_lens_probe`` and the proof
    validator.
    """
    context = last_context or {}
    lens = last_lens or {}
    deck = str(context.get("deck") or "none")
    has_frame_music = "music" in context
    frame_music_active = max_music >= AUDIBLE_MUSIC_FLOOR
    frame_phase = str(context.get("phase") or "").lower()
    frame_audio_active = (
        frame_music_active
        if has_frame_music
        else context.get("audible") is True and frame_phase != "silent"
    )
    lens_audio_active = lens.get("audio_active") is True if "audio_active" in lens else None
    audio_active = (
        bool(lens_audio_active and frame_audio_active)
        if lens_audio_active is not None and has_frame_music
        else bool(frame_audio_active if lens_audio_active is None else lens_audio_active)
    )
    deck_attributed = (
        lens.get("deck_attributed") is True
        if "deck_attributed" in lens
        else deck in ATTRIBUTED_DECKS
    )
    deck_track_citable = (
        lens.get("deck_track_citable") is True
        if "deck_track_citable" in lens
        else _deck_state_has_citable_track(context.get("deck_state"), deck)
    )
    blockers: list[str] = []
    if frames_seen < 1:
        blockers.append("live sidecar emitted no flat context frames")
    if not audio_active:
        blockers.append("live master audio is not audible yet")
    if not deck_attributed:
        blockers.append("live audio is not attributed to deck A, B, or mix")
    if not deck_track_citable:
        blockers.append("live deck_state has no citable track_id at confidence floor")

    return {
        "ok": not blockers,
        "frames_seen": frames_seen,
        "audio_active": audio_active,
        "deck_attributed": deck_attributed,
        "deck_track_citable": deck_track_citable,
        "max_music": round(max_music, 6),
        "last_context": last_context,
        "last_lens": last_lens,
        "blockers": blockers,
    }


async def _check_live_course3_context_async(
    url: str,
    *,
    seconds: float,
) -> dict[str, Any]:
    import websockets

    deadline = asyncio.get_running_loop().time() + max(0.1, float(seconds))
    frames_seen = 0
    last_context: dict[str, Any] | None = None
    last_lens: dict[str, Any] | None = None
    max_music = 0.0
    async with websockets.connect(url) as ws:
        while asyncio.get_running_loop().time() < deadline:
            remaining = deadline - asyncio.get_running_loop().time()
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=max(0.05, remaining))
            except TimeoutError:
                break
            except websockets.exceptions.ConnectionClosed:
                break
            msg = _safe_json_loads(raw)
            if msg is None or "type" in msg:
                continue
            frames_seen += 1
            context = {
                key: msg.get(key)
                for key in (
                    "music",
                    "audible",
                    "deck",
                    "phase",
                    "bpm",
                    "bpm_confidence",
                    "deck_state",
                )
                if key in msg
            }
            last_context = context
            max_music = max(max_music, _float_value(context.get("music")))
            lens = msg.get("course3_lens")
            if isinstance(lens, dict):
                last_lens = lens
            summary = summarize_live_course3_context(
                frames_seen=frames_seen,
                last_context=last_context,
                last_lens=last_lens,
                max_music=max_music,
            )
            if summary["ok"]:
                return summary
    return summarize_live_course3_context(
        frames_seen=frames_seen,
        last_context=last_context,
        last_lens=last_lens,
        max_music=max_music,
    )


def check_live_course3_context(
    url: str = DEFAULT_WS_URL,
    *,
    seconds: float = 1.5,
) -> dict[str, Any]:
    """Sample the live sidecar socket for deck-attributed Course 3 context."""
    def _failure(error: str) -> dict[str, Any]:
        return {
            "ok": False,
            "error": error,
            "blockers": ["could not read live sidecar context"],
        }

    def _run() -> dict[str, Any]:
        return asyncio.run(_check_live_course3_context_async(url, seconds=seconds))

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        try:
            return _run()
        except OSError as exc:
            return _failure(str(exc))
        except Exception as exc:  # pragma: no cover - defensive CLI boundary
            return _failure(repr(exc))

    holder: dict[str, Any] = {}

    def _thread_target() -> None:
        try:
            holder["result"] = _run()
        except OSError as exc:
            holder["error"] = str(exc)
        except Exception as exc:  # pragma: no cover - defensive thread boundary
            holder["error"] = repr(exc)

    thread = threading.Thread(target=_thread_target, daemon=True)
    thread.start()
    thread.join(timeout=max(3.0, float(seconds) + 2.0))
    if thread.is_alive():
        return _failure(f"timed out after {max(3.0, float(seconds) + 2.0):.1f}s")
    result = holder.get("result")
    if isinstance(result, dict):
        return result
    return _failure(str(holder.get("error") or "unknown live-context error"))


def _capture_row_name(row: dict[str, Any]) -> str:
    return str(row.get("name") or "")


def _is_loopback_capture_row(row: dict[str, Any]) -> bool:
    return bool(matching_names([_capture_row_name(row)], AUDIO_LOOPBACK_NEEDLES))


def _is_dj_capture_row(row: dict[str, Any]) -> bool:
    name = _capture_row_name(row)
    return bool(name) and bool(matching_names([name], DJ_AUDIO_NEEDLES))


def _is_rekordbox_capture_route_name(name: str) -> bool:
    lowered = name.strip().lower()
    return bool(lowered) and (
        bool(matching_names([lowered], AUDIO_LOOPBACK_NEEDLES))
        or "aggregate" in lowered
    )


def _trim_capture_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    trimmed: list[dict[str, Any]] = []
    for row in rows[:4]:
        trimmed.append(
            {
                "name": row.get("name"),
                "rms": row.get("rms"),
                "peak": row.get("peak"),
                "sample_rate": row.get("sample_rate"),
                "signal": row.get("signal"),
            }
        )
    return trimmed


def _rekordbox_route_hint(
    capture_matrix_check: dict[str, Any] | None,
    rekordbox_audio_settings_check: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Explain the common Rekordbox routing trap without claiming proof.

    Rekordbox can bypass the macOS default output and play through its own
    controller or aggregate device. When the selected BlackHole route is healthy
    but passive capture is silent, this hint gives the operator the missing
    mental model: selecting BlackHole in macOS is not enough if Rekordbox's own
    audio preferences still point elsewhere.
    """
    if capture_matrix_check is None or capture_matrix_check.get("enabled") is not True:
        return None
    raw_rows = capture_matrix_check.get("rows")
    if not isinstance(raw_rows, list):
        return None
    rows = [row for row in raw_rows if isinstance(row, dict)]
    loopback_rows = [row for row in rows if _is_loopback_capture_row(row)]
    dj_rows = [
        row
        for row in rows
        if _is_dj_capture_row(row) and not _is_loopback_capture_row(row)
    ]
    if not loopback_rows or not dj_rows:
        return None
    current_settings = None
    current_row = None
    current_route_aligned = False
    saved_rate_mismatch = _rekordbox_saved_rate_mismatch(
        capture_matrix_check,
        rekordbox_audio_settings_check,
    )
    if isinstance(rekordbox_audio_settings_check, dict):
        current = rekordbox_audio_settings_check.get("current")
        if isinstance(current, dict):
            current_settings = {
                "audio_output_device_name": current.get("audio_output_device_name"),
                "audio_input_device_name": current.get("audio_input_device_name"),
                "audio_device_rate": current.get("audio_device_rate"),
                "mixer_mode_internal": current.get("mixer_mode_internal"),
            }
            current_output = str(current.get("audio_output_device_name") or "").strip()
            if current_output:
                current_row = _capture_row_by_name(capture_matrix_check, current_output)
                current_route_aligned = (
                    isinstance(current_row, dict)
                    and _is_rekordbox_capture_route_name(current_output)
                    and _info_int(current_row, "sample_rate")
                    == EXPECTED_CAPTURE_SAMPLE_RATE
                    and saved_rate_mismatch is None
                )
    next_action = (
        "In Rekordbox Audio preferences, set the master/recording route to "
        "BlackHole 16ch or to an aggregate that includes BlackHole, then play "
        "a deck with the channel and master faders up."
    )
    if saved_rate_mismatch is not None:
        next_action = (
            "Rekordbox is saved to "
            f"{saved_rate_mismatch['rekordbox_output_device']!r} at "
            f"{saved_rate_mismatch['saved_sample_rate']}Hz while vibemix "
            f"captures that route at {EXPECTED_CAPTURE_SAMPLE_RATE}Hz; set "
            "Rekordbox Audio preferences or Audio MIDI Setup to 48000Hz, then "
            "play a deck with channel and master faders up."
        )
    elif current_route_aligned and current_settings:
        next_action = (
            "Rekordbox is saved to "
            f"{current_settings.get('audio_output_device_name')!r} and that "
            "capture route is at 48000Hz; start real deck playback with "
            "channel and master faders up."
        )
    elif current_settings and current_settings.get("audio_output_device_name"):
        next_action = (
            "Rekordbox settings currently name "
            f"{current_settings.get('audio_output_device_name')!r}; align "
            "Rekordbox Audio preferences with the vibemix capture input "
            "(BlackHole 16ch or an aggregate that includes it), then play a "
            "deck with channel and master faders up."
        )
    return {
        "code": "rekordbox_may_bypass_macos_output",
        "message": (
            "Rekordbox can use its own audio device, so macOS output on BlackHole "
            "does not prove Rekordbox master audio is routed to BlackHole."
        ),
        "next_action": next_action,
        "current_rekordbox_settings": current_settings,
        "current_rekordbox_route_aligned": current_route_aligned,
        "saved_rate_mismatch": saved_rate_mismatch,
        "current_rekordbox_capture_row": (
            {
                "name": current_row.get("name"),
                "rms": current_row.get("rms"),
                "peak": current_row.get("peak"),
                "sample_rate": current_row.get("sample_rate"),
                "signal": current_row.get("signal"),
            }
            if isinstance(current_row, dict)
            else None
        ),
        "loopback_rows": _trim_capture_rows(loopback_rows),
        "dj_capture_rows": _trim_capture_rows(dj_rows),
    }


def _rekordbox_loopback_rate_mismatch(
    capture_matrix_check: dict[str, Any] | None,
    rekordbox_audio_settings_check: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(capture_matrix_check, dict) or not isinstance(
        rekordbox_audio_settings_check, dict
    ):
        return None
    current = rekordbox_audio_settings_check.get("current")
    if not isinstance(current, dict):
        return None
    output_name = str(current.get("audio_output_device_name") or "").strip()
    if not output_name:
        return None
    rows = capture_matrix_check.get("rows")
    if not isinstance(rows, list):
        return None
    matched_row = next(
        (
            row
            for row in rows
            if isinstance(row, dict)
            and str(row.get("name") or "").strip().lower() == output_name.lower()
        ),
        None,
    )
    if not isinstance(matched_row, dict):
        return None
    sample_rate = _info_int(matched_row, "sample_rate")
    if sample_rate in {0, EXPECTED_CAPTURE_SAMPLE_RATE}:
        return None
    return {
        "code": "rekordbox_loopback_sample_rate_mismatch",
        "rekordbox_output_device": output_name,
        "sample_rate": sample_rate,
        "expected_sample_rate": EXPECTED_CAPTURE_SAMPLE_RATE,
        "capture_row": {
            "name": matched_row.get("name"),
            "rms": matched_row.get("rms"),
            "peak": matched_row.get("peak"),
            "sample_rate": matched_row.get("sample_rate"),
            "signal": matched_row.get("signal"),
        },
    }


def _rekordbox_saved_rate_mismatch(
    capture_matrix_check: dict[str, Any] | None,
    rekordbox_audio_settings_check: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Detect a saved Rekordbox route whose rate disagrees with capture."""
    if not isinstance(capture_matrix_check, dict) or not isinstance(
        rekordbox_audio_settings_check, dict
    ):
        return None
    current = rekordbox_audio_settings_check.get("current")
    if not isinstance(current, dict):
        return None
    output_name = str(current.get("audio_output_device_name") or "").strip()
    if not output_name:
        return None
    saved_rate = _info_int(current, "audio_device_rate")
    if saved_rate in {0, EXPECTED_CAPTURE_SAMPLE_RATE}:
        return None
    matched_row = _capture_row_by_name(capture_matrix_check, output_name)
    if not isinstance(matched_row, dict):
        return None
    capture_rate = _info_int(matched_row, "sample_rate")
    if capture_rate != EXPECTED_CAPTURE_SAMPLE_RATE:
        return None
    return {
        "code": "rekordbox_saved_sample_rate_mismatch",
        "rekordbox_output_device": output_name,
        "saved_sample_rate": saved_rate,
        "capture_sample_rate": capture_rate,
        "expected_sample_rate": EXPECTED_CAPTURE_SAMPLE_RATE,
        "current_settings": {
            "audio_output_device_name": current.get("audio_output_device_name"),
            "audio_input_device_name": current.get("audio_input_device_name"),
            "audio_device_rate": current.get("audio_device_rate"),
            "mixer_mode_internal": current.get("mixer_mode_internal"),
        },
        "capture_row": {
            "name": matched_row.get("name"),
            "rms": matched_row.get("rms"),
            "peak": matched_row.get("peak"),
            "sample_rate": matched_row.get("sample_rate"),
            "signal": matched_row.get("signal"),
        },
    }


def _rekordbox_saved_route_capture_rate_mismatch(
    capture_matrix_check: dict[str, Any] | None,
    rekordbox_audio_settings_check: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Detect a saved Rekordbox route whose sampled capture row is not 48 kHz."""
    if not isinstance(capture_matrix_check, dict) or not isinstance(
        rekordbox_audio_settings_check, dict
    ):
        return None
    current = rekordbox_audio_settings_check.get("current")
    if not isinstance(current, dict):
        return None
    output_name = str(current.get("audio_output_device_name") or "").strip()
    if not output_name:
        return None
    matched_row = _capture_row_by_name(capture_matrix_check, output_name)
    if not isinstance(matched_row, dict):
        return None
    capture_rate = _info_int(matched_row, "sample_rate")
    if capture_rate in {0, EXPECTED_CAPTURE_SAMPLE_RATE}:
        return None
    return {
        "code": "rekordbox_saved_route_capture_rate_mismatch",
        "rekordbox_output_device": output_name,
        "matched_capture_device": matched_row.get("name"),
        "saved_sample_rate": _info_int(current, "audio_device_rate") or None,
        "capture_sample_rate": capture_rate,
        "expected_sample_rate": EXPECTED_CAPTURE_SAMPLE_RATE,
        "current_settings": {
            "audio_output_device_name": current.get("audio_output_device_name"),
            "audio_input_device_name": current.get("audio_input_device_name"),
            "audio_device_rate": current.get("audio_device_rate"),
            "mixer_mode_internal": current.get("mixer_mode_internal"),
        },
        "capture_row": {
            "name": matched_row.get("name"),
            "rms": matched_row.get("rms"),
            "peak": matched_row.get("peak"),
            "sample_rate": matched_row.get("sample_rate"),
            "signal": matched_row.get("signal"),
        },
    }


def _rekordbox_output_name(
    rekordbox_audio_settings_check: dict[str, Any] | None,
) -> str:
    if not isinstance(rekordbox_audio_settings_check, dict):
        return ""
    current = rekordbox_audio_settings_check.get("current")
    if not isinstance(current, dict):
        return ""
    return str(current.get("audio_output_device_name") or "").strip()


def _capture_rows(capture_matrix_check: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(capture_matrix_check, dict):
        return []
    rows = capture_matrix_check.get("rows")
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def _capture_row_by_name(
    capture_matrix_check: dict[str, Any] | None,
    name: str,
) -> dict[str, Any] | None:
    target = name.strip().lower()
    if not target:
        return None
    for row in _capture_rows(capture_matrix_check):
        if _capture_row_matches_name(row, target):
            return row
    return None


def _capture_row_matches_name(row: dict[str, Any], target_name: str) -> bool:
    row_name = str(row.get("name") or "").strip().lower()
    target = target_name.strip().lower()
    if not row_name or not target:
        return False
    if row_name == target:
        return True
    # Rekordbox-created aggregate capture endpoints are often exposed by CoreAudio
    # as "rekordbox Aggregate Device" while Rekordbox persists "Aggregate Device".
    if row_name.startswith("rekordbox ") and row_name.removeprefix("rekordbox ") == target:
        return True
    return False


def _current_rekordbox_sample_rate(
    rekordbox_audio_settings_check: dict[str, Any] | None,
) -> int:
    if not isinstance(rekordbox_audio_settings_check, dict):
        return 0
    current = rekordbox_audio_settings_check.get("current")
    if not isinstance(current, dict):
        return 0
    return _info_int(current, "audio_device_rate")


def _auto_master_candidate_evidence(
    *,
    capture_matrix_check: dict[str, Any] | None,
    rekordbox_audio_settings_check: dict[str, Any] | None,
    audio_route_check: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """Build a ranked, bounded explanation of auto-master capture candidates."""
    rows_by_name: dict[str, dict[str, Any]] = {}
    top_signal = (
        capture_matrix_check.get("top_signal")
        if isinstance(capture_matrix_check, dict)
        else None
    )
    raw_rows = list(_capture_rows(capture_matrix_check))
    if isinstance(top_signal, dict):
        raw_rows.append(top_signal)

    rekordbox_output = _rekordbox_output_name(rekordbox_audio_settings_check)
    macos_output = ""
    if isinstance(audio_route_check, dict):
        macos_output = str(audio_route_check.get("output_device") or "").strip()

    def add_candidate(
        *,
        name: str,
        row: dict[str, Any] | None,
        sampled: bool,
        sources: list[str],
        reasons: list[str],
        sample_rate: int = 0,
    ) -> None:
        candidate_name = name.strip()
        if not candidate_name:
            return
        key = candidate_name.lower()
        existing = rows_by_name.get(key)
        if existing is None:
            row_sample_rate = _info_int(row, "sample_rate") if isinstance(row, dict) else 0
            row_rms = row.get("rms") if isinstance(row, dict) and "rms" in row else None
            row_peak = row.get("peak") if isinstance(row, dict) and "peak" in row else None
            row_signal = bool(row.get("signal")) if isinstance(row, dict) else False
            existing = {
                "name": candidate_name,
                "sample_rate": row_sample_rate or sample_rate or None,
                "expected_sample_rate": EXPECTED_CAPTURE_SAMPLE_RATE,
                "sampled": sampled,
                "sources": [],
                "reasons": [],
                "signal": row_signal,
                "live_signal": False,
                "rate_ok": (row_sample_rate or sample_rate) == EXPECTED_CAPTURE_SAMPLE_RATE,
                "loopback": bool(matching_names([candidate_name], AUDIO_LOOPBACK_NEEDLES)),
                "dj_capture": bool(matching_names([candidate_name], DJ_AUDIO_NEEDLES)),
            }
            if row_rms is not None:
                existing["rms"] = row_rms
            if row_peak is not None:
                existing["peak"] = row_peak
            rows_by_name[key] = existing
        else:
            existing["sampled"] = bool(existing.get("sampled")) or sampled
            if existing.get("sample_rate") is None and sample_rate:
                existing["sample_rate"] = sample_rate
                existing["rate_ok"] = sample_rate == EXPECTED_CAPTURE_SAMPLE_RATE
            if isinstance(row, dict):
                existing["signal"] = bool(existing.get("signal")) or bool(row.get("signal"))
                if "rms" in row:
                    existing["rms"] = max(
                        float(existing.get("rms") or 0.0),
                        float(row.get("rms") or 0.0),
                    )
                if "peak" in row:
                    existing["peak"] = max(
                        float(existing.get("peak") or 0.0),
                        float(row.get("peak") or 0.0),
                    )
        for source in sources:
            if source and source not in existing["sources"]:
                existing["sources"].append(source)
        for reason in reasons:
            if reason and reason not in existing["reasons"]:
                existing["reasons"].append(reason)
        if "live_signal" in existing["reasons"]:
            existing["live_signal"] = True

    top_name = str(top_signal.get("name") or "").strip() if isinstance(top_signal, dict) else ""
    for row in raw_rows:
        if not isinstance(row, dict):
            continue
        name = _capture_row_name(row).strip()
        if not name:
            continue
        reasons = ["sampled_capture"]
        sources = ["capture_matrix"]
        if top_name and name.lower() == top_name.lower() and row.get("signal") is True:
            reasons = ["live_signal"]
            sources = ["capture_matrix_top_signal"]
        if rekordbox_output and _capture_row_matches_name(row, rekordbox_output):
            reasons.append("saved_rekordbox_route")
            sources.append("rekordbox_audio_settings")
        if macos_output and _capture_row_matches_name(row, macos_output):
            reasons.append("macos_output_route")
            sources.append("macos_output_route")
        if (
            _is_loopback_capture_row(row)
            and _info_int(row, "sample_rate") == EXPECTED_CAPTURE_SAMPLE_RATE
            and row.get("signal") is not True
        ):
            reasons.append("silent_48k_loopback_fallback")
        add_candidate(
            name=name,
            row=row,
            sampled=True,
            sources=sources,
            reasons=reasons,
        )

    if rekordbox_output and _capture_row_by_name(capture_matrix_check, rekordbox_output) is None:
        add_candidate(
            name=rekordbox_output,
            row=None,
            sampled=False,
            sources=["rekordbox_audio_settings"],
            reasons=["saved_rekordbox_route", "unsampled_route"],
            sample_rate=_current_rekordbox_sample_rate(rekordbox_audio_settings_check),
        )
    if macos_output and _capture_row_by_name(capture_matrix_check, macos_output) is None:
        add_candidate(
            name=macos_output,
            row=None,
            sampled=False,
            sources=["macos_output_route"],
            reasons=["macos_output_route", "unsampled_route"],
        )

    def score(candidate: dict[str, Any]) -> tuple[int, int, int, int, int, int, float, float]:
        reasons = set(candidate.get("reasons") or [])
        name = str(candidate.get("name") or "").lower()
        return (
            1 if candidate.get("signal") else 0,
            1 if candidate.get("rate_ok") else 0,
            1 if "saved_rekordbox_route" in reasons else 0,
            1 if "macos_output_route" in reasons else 0,
            1 if candidate.get("loopback") else 0,
            1 if "blackhole" in name else 0,
            float(candidate.get("rms") or 0.0),
            float(candidate.get("peak") or 0.0),
        )

    candidates = sorted(rows_by_name.values(), key=score, reverse=True)
    for rank, candidate in enumerate(candidates, start=1):
        candidate["rank"] = rank
        candidate["source"] = "+".join(candidate["sources"])
    return candidates[:8]


def _auto_master_candidate(
    *,
    status: str,
    source: str,
    reason: str,
    row: dict[str, Any] | None,
    next_action: str,
    live_signal: bool = False,
    candidates: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    device_name = str(row.get("name") or "").strip() if isinstance(row, dict) else None
    sample_rate = _info_int(row, "sample_rate") if isinstance(row, dict) else 0
    ok = bool(device_name) and status == "ready"
    candidate: dict[str, Any] = {
        "ok": ok,
        "status": status,
        "source": source,
        "reason": reason,
        "device_name": device_name or None,
        "sample_rate": sample_rate or None,
        "expected_sample_rate": EXPECTED_CAPTURE_SAMPLE_RATE,
        "live_signal": live_signal,
        "next_action": next_action,
    }
    if isinstance(row, dict):
        if "rms" in row:
            candidate["rms"] = row.get("rms")
        if "peak" in row:
            candidate["peak"] = row.get("peak")
    candidate["candidates"] = candidates or []
    return candidate


def recommend_auto_master_input(
    *,
    capture_matrix_check: dict[str, Any] | None = None,
    rekordbox_audio_settings_check: dict[str, Any] | None = None,
    audio_route_check: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Resolve a product-facing auto-master recommendation from readiness data.

    The proof runner and future Learn UI should not reverse-engineer the capture
    matrix. This function returns one bounded answer: use this 48 kHz capture
    input, fix this rate, or keep waiting for real playback.
    """
    candidates = _auto_master_candidate_evidence(
        capture_matrix_check=capture_matrix_check,
        rekordbox_audio_settings_check=rekordbox_audio_settings_check,
        audio_route_check=audio_route_check,
    )
    rows = _capture_rows(capture_matrix_check)
    top_signal = (
        capture_matrix_check.get("top_signal")
        if isinstance(capture_matrix_check, dict)
        else None
    )
    if isinstance(top_signal, dict):
        sample_rate = _info_int(top_signal, "sample_rate")
        if sample_rate == EXPECTED_CAPTURE_SAMPLE_RATE:
            return _auto_master_candidate(
                status="ready",
                source="capture_matrix_top_signal",
                reason="live_signal",
                row=top_signal,
                live_signal=True,
                next_action=(
                    f"Use {top_signal.get('name')!r} as the master capture input."
                ),
                candidates=candidates,
            )
        return _auto_master_candidate(
            status="needs_rate_fix",
            source="capture_matrix_top_signal",
            reason="live_signal_rate_mismatch",
            row=top_signal,
            live_signal=True,
            next_action=(
                f"Set {top_signal.get('name')!r} to "
                f"{EXPECTED_CAPTURE_SAMPLE_RATE}Hz before using it as master capture."
            ),
            candidates=candidates,
        )

    rekordbox_output = _rekordbox_output_name(rekordbox_audio_settings_check)
    if rekordbox_output and matching_names([rekordbox_output], AUDIO_LOOPBACK_NEEDLES):
        row = _capture_row_by_name(capture_matrix_check, rekordbox_output) or {
            "name": rekordbox_output
        }
        sample_rate = _info_int(row, "sample_rate")
        if sample_rate in {0, EXPECTED_CAPTURE_SAMPLE_RATE}:
            return _auto_master_candidate(
                status="ready",
                source="rekordbox_audio_settings",
                reason="saved_loopback_route",
                row=row,
                next_action=(
                    f"Use Rekordbox's saved route {rekordbox_output!r}; start deck playback."
                ),
                candidates=candidates,
            )
        return _auto_master_candidate(
            status="needs_rate_fix",
            source="rekordbox_audio_settings",
            reason="saved_loopback_rate_mismatch",
            row=row,
            next_action=(
                f"Set {rekordbox_output!r} to {EXPECTED_CAPTURE_SAMPLE_RATE}Hz "
                "before using it as master capture."
            ),
            candidates=candidates,
        )

    macos_output = ""
    if isinstance(audio_route_check, dict):
        macos_output = str(audio_route_check.get("output_device") or "").strip()
    if macos_output and matching_names([macos_output], AUDIO_LOOPBACK_NEEDLES):
        row = _capture_row_by_name(capture_matrix_check, macos_output) or {
            "name": macos_output
        }
        sample_rate = _info_int(row, "sample_rate")
        if sample_rate in {0, EXPECTED_CAPTURE_SAMPLE_RATE}:
            return _auto_master_candidate(
                status="ready",
                source="macos_output_route",
                reason="loopback_default_output",
                row=row,
                next_action=(
                    f"Use macOS output route {macos_output!r}; start deck playback."
                ),
                candidates=candidates,
            )
        return _auto_master_candidate(
            status="needs_rate_fix",
            source="macos_output_route",
            reason="loopback_default_rate_mismatch",
            row=row,
            next_action=(
                f"Set {macos_output!r} to {EXPECTED_CAPTURE_SAMPLE_RATE}Hz "
                "before using it as master capture."
            ),
            candidates=candidates,
        )

    fallback_rows = [
        row
        for row in rows
        if _is_loopback_capture_row(row)
        and _info_int(row, "sample_rate") == EXPECTED_CAPTURE_SAMPLE_RATE
    ]
    if fallback_rows:
        chosen = max(
            fallback_rows,
            key=lambda row: (
                1 if "blackhole" in _capture_row_name(row).lower() else 0,
                float(row.get("rms") or 0.0),
                float(row.get("peak") or 0.0),
            ),
        )
        return _auto_master_candidate(
            status="ready",
            source="capture_matrix_48k_loopback",
            reason="silent_48k_loopback_fallback",
            row=chosen,
            next_action=f"Use {chosen.get('name')!r}; start deck playback.",
            candidates=candidates,
        )

    return {
        "ok": False,
        "status": "no_candidate",
        "source": None,
        "reason": "no_usable_capture_input",
        "device_name": None,
        "sample_rate": None,
        "expected_sample_rate": EXPECTED_CAPTURE_SAMPLE_RATE,
        "live_signal": False,
        "candidates": candidates,
        "next_action": "Connect or create a 48000Hz loopback master capture input.",
    }


def _loopback_self_test_is_inconclusive_for_rekordbox_route(
    loopback_self_test_check: dict[str, Any] | None,
    rekordbox_audio_settings_check: dict[str, Any] | None,
) -> bool:
    """Return true when a failed self-test is likely contending with Rekordbox.

    The injected duplex self-test is useful before a DJ app owns the loopback.
    Once Rekordbox is configured to the same route, a zero capture can be an
    ownership/contention artifact, not proof that the user-facing master route
    is broken. Passive signal and socket context remain authoritative.
    """
    if not isinstance(loopback_self_test_check, dict):
        return False
    if loopback_self_test_check.get("enabled") is not True:
        return False
    if loopback_self_test_check.get("ok") is not False:
        return False
    device = loopback_self_test_check.get("device")
    if not isinstance(device, dict):
        return False
    tested_name = str(device.get("name") or "").strip().lower()
    rekordbox_output = _rekordbox_output_name(rekordbox_audio_settings_check).lower()
    return bool(tested_name and rekordbox_output and tested_name == rekordbox_output)


def diagnose_course3_audio(
    *,
    audio_route_check: dict[str, Any] | None = None,
    loopback_self_test_check: dict[str, Any] | None = None,
    loopback_signal_check: dict[str, Any] | None = None,
    capture_matrix_check: dict[str, Any] | None = None,
    live_context_check: dict[str, Any] | None = None,
    rekordbox_audio_settings_check: dict[str, Any] | None = None,
    auto_master_recommendation: dict[str, Any] | None = None,
    nowplaying_check: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a stable diagnosis code for Course 3 audio readiness."""
    if live_context_check is not None and live_context_check.get("ok") is True:
        return {
            "code": "live_deck_context_ready",
            "severity": "ready",
            "message": "Live audio is audible, deck-attributed, and has a citable track row.",
            "next_action": "Run the Course 3 lens proof.",
        }
    rekordbox_output = _rekordbox_output_name(rekordbox_audio_settings_check)
    if audio_route_check is not None and audio_route_check.get("available") is True:
        if audio_route_check.get("ok") is False:
            macos_output = str(audio_route_check.get("output_device") or "").strip()
            rekordbox_bypasses_macos = bool(
                rekordbox_output
                and macos_output
                and rekordbox_output.lower() != macos_output.lower()
            )
            if not rekordbox_bypasses_macos:
                return {
                    "code": "macos_output_not_loopback",
                    "severity": "fix_route",
                    "message": "macOS output is not currently routed to a loopback capture device.",
                    "next_action": "Switch macOS output/system audio to BlackHole 16ch or the intended loopback route.",
                }
    if loopback_self_test_check is not None and loopback_self_test_check.get("enabled") is True:
        self_test_inconclusive = _loopback_self_test_is_inconclusive_for_rekordbox_route(
            loopback_self_test_check,
            rekordbox_audio_settings_check,
        )
        if loopback_self_test_check.get("ok") is False and not self_test_inconclusive:
            return {
                "code": "loopback_route_failed_self_test",
                "severity": "fix_route",
                "message": "The selected loopback device did not capture an injected test tone.",
                "next_action": "Fix the loopback device before testing Rekordbox playback.",
            }
    if capture_matrix_check is not None and capture_matrix_check.get("enabled") is True:
        top_signal = capture_matrix_check.get("top_signal")
        if isinstance(top_signal, dict):
            loopback_ok = (
                loopback_signal_check is not None
                and loopback_signal_check.get("ok") is True
            )
            if not loopback_ok:
                return {
                    "code": "signal_on_unselected_capture",
                    "severity": "fix_route",
                    "message": (
                        "Audio signal is present on another capture input while the selected "
                        "loopback capture is silent."
                    ),
                    "next_action": f"Route Rekordbox/master audio into {top_signal.get('name')!r} or switch vibemix to that input.",
                    "top_signal": top_signal,
                }
    if (
        loopback_self_test_check is not None
        and (
            loopback_self_test_check.get("ok") is True
            or _loopback_self_test_is_inconclusive_for_rekordbox_route(
                loopback_self_test_check,
                rekordbox_audio_settings_check,
            )
        )
        and loopback_signal_check is not None
        and loopback_signal_check.get("ok") is False
        and capture_matrix_check is not None
        and capture_matrix_check.get("enabled") is True
        and capture_matrix_check.get("ok") is False
    ):
        self_test_inconclusive = _loopback_self_test_is_inconclusive_for_rekordbox_route(
            loopback_self_test_check,
            rekordbox_audio_settings_check,
        )
        rekordbox_hint = _rekordbox_route_hint(
            capture_matrix_check,
            rekordbox_audio_settings_check=rekordbox_audio_settings_check,
        )
        rate_mismatch = _rekordbox_loopback_rate_mismatch(
            capture_matrix_check,
            rekordbox_audio_settings_check,
        )
        saved_rate_mismatch = _rekordbox_saved_rate_mismatch(
            capture_matrix_check,
            rekordbox_audio_settings_check,
        )
        route_capture_rate_mismatch = _rekordbox_saved_route_capture_rate_mismatch(
            capture_matrix_check,
            rekordbox_audio_settings_check,
        )
        if rate_mismatch is not None:
            device = rate_mismatch["rekordbox_output_device"]
            current_rate = rate_mismatch["sample_rate"]
            expected = rate_mismatch["expected_sample_rate"]
            next_action = (
                f"Set {device} to {expected}Hz in Audio MIDI Setup, or change "
                "Rekordbox Audio preferences to BlackHole 16ch or a 48k "
                "aggregate that includes BlackHole, then play a deck with "
                "channel and master faders up."
            )
            return {
                "code": "rekordbox_loopback_sample_rate_mismatch",
                "severity": "fix_rate",
                "message": (
                    "Rekordbox is saved to a loopback output, but that capture "
                    "device is not at vibemix's expected sample rate."
                ),
                "next_action": next_action,
                "rate_mismatch": rate_mismatch,
                "rekordbox_route_hint": rekordbox_hint,
                "operator_action": _course3_rate_fix_operator_action(
                    device=str(device),
                    current_rate=int(current_rate),
                    expected_rate=int(expected),
                    first_step=next_action,
                ),
                "rekordbox_audio_settings": (
                    {
                        "path": rekordbox_audio_settings_check.get("path"),
                        "current": rekordbox_audio_settings_check.get("current"),
                        "recent": rekordbox_audio_settings_check.get("recent"),
                    }
                    if isinstance(rekordbox_audio_settings_check, dict)
                    else None
                ),
            }
        if saved_rate_mismatch is not None:
            device = saved_rate_mismatch["rekordbox_output_device"]
            saved_rate = saved_rate_mismatch["saved_sample_rate"]
            expected = saved_rate_mismatch["expected_sample_rate"]
            next_action = (
                f"Set Rekordbox's {device} route from {saved_rate}Hz to "
                f"{expected}Hz in Rekordbox Audio preferences or Audio MIDI "
                "Setup, then play a deck with channel and master faders up."
            )
            return {
                "code": "rekordbox_saved_sample_rate_mismatch",
                "severity": "fix_rate",
                "message": (
                    "Rekordbox is saved to the selected loopback output, but "
                    "its persisted audio rate does not match vibemix's capture "
                    "rate."
                ),
                "next_action": next_action,
                "saved_rate_mismatch": saved_rate_mismatch,
                "rekordbox_route_hint": rekordbox_hint,
                "operator_action": _course3_rate_fix_operator_action(
                    device=str(device),
                    current_rate=int(saved_rate),
                    expected_rate=int(expected),
                    first_step=next_action,
                ),
                "rekordbox_audio_settings": (
                    {
                        "path": rekordbox_audio_settings_check.get("path"),
                        "current": rekordbox_audio_settings_check.get("current"),
                        "recent": rekordbox_audio_settings_check.get("recent"),
                    }
                    if isinstance(rekordbox_audio_settings_check, dict)
                    else None
                ),
            }
        if route_capture_rate_mismatch is not None:
            device = route_capture_rate_mismatch["rekordbox_output_device"]
            capture_device = route_capture_rate_mismatch["matched_capture_device"]
            capture_rate = route_capture_rate_mismatch["capture_sample_rate"]
            saved_rate = route_capture_rate_mismatch["saved_sample_rate"]
            expected = route_capture_rate_mismatch["expected_sample_rate"]
            next_action = (
                f"Set Rekordbox's {device!r} route, sampled as "
                f"{capture_device!r}, from {capture_rate}Hz to {expected}Hz "
                "in Audio MIDI Setup or choose a 48k BlackHole/aggregate route, "
                "then play a deck with channel and master faders up."
            )
            return {
                "code": "rekordbox_saved_route_capture_rate_mismatch",
                "severity": "fix_rate",
                "message": (
                    "Rekordbox is saved to a capture-capable route, but the "
                    "matching sampled input is not at vibemix's expected sample rate."
                ),
                "next_action": next_action,
                "route_capture_rate_mismatch": route_capture_rate_mismatch,
                "rekordbox_route_hint": rekordbox_hint,
                "operator_action": _course3_rate_fix_operator_action(
                    device=str(device),
                    capture_device=str(capture_device or ""),
                    current_rate=int(capture_rate),
                    current_rekordbox_rate=int(saved_rate) if saved_rate else None,
                    expected_rate=int(expected),
                    first_step=next_action,
                ),
                "rekordbox_audio_settings": (
                    {
                        "path": rekordbox_audio_settings_check.get("path"),
                        "current": rekordbox_audio_settings_check.get("current"),
                        "recent": rekordbox_audio_settings_check.get("recent"),
                    }
                    if isinstance(rekordbox_audio_settings_check, dict)
                    else None
                ),
            }
        nowplaying_blocker = _course3_nowplaying_blocker(nowplaying_check)
        next_action = (
            "Start real Rekordbox deck playback and route its master output to "
            "BlackHole 16ch or the intended capture input."
        )
        if rekordbox_hint is not None:
            next_action = rekordbox_hint["next_action"]
        if nowplaying_blocker:
            next_action = (
                f"{next_action} Current macOS now-playing is not a citable "
                "Rekordbox deck title; stop unrelated media or make Rekordbox the "
                "active playing source."
            )
        operator_action = _course3_external_playback_action(
            rekordbox_hint=rekordbox_hint,
            rekordbox_audio_settings_check=rekordbox_audio_settings_check,
            auto_master_recommendation=auto_master_recommendation,
            nowplaying_blocker=nowplaying_blocker,
        )
        return {
            "code": (
                "rekordbox_route_self_test_inconclusive_external_playback_absent"
                if self_test_inconclusive
                else "loopback_route_healthy_external_playback_absent"
            ),
            "severity": "start_playback",
            "message": (
                "Rekordbox owns the selected loopback route, so the injected "
                "self-test is inconclusive; no sampled DJ/loopback input is "
                "receiving external playback."
                if self_test_inconclusive
                else "The loopback device captures an injected signal, but no sampled "
                "DJ/loopback input is receiving external playback."
            ),
            "next_action": next_action,
            "loopback_self_test_inconclusive": (
                {
                    "reason": "tested route matches Rekordbox audio output",
                    "device": loopback_self_test_check.get("device"),
                }
                if self_test_inconclusive
                else None
            ),
            "rekordbox_route_hint": rekordbox_hint,
            "operator_action": operator_action,
            "rekordbox_audio_settings": (
                {
                    "path": rekordbox_audio_settings_check.get("path"),
                    "current": rekordbox_audio_settings_check.get("current"),
                    "recent": rekordbox_audio_settings_check.get("recent"),
                }
                if isinstance(rekordbox_audio_settings_check, dict)
                else None
            ),
            "nowplaying_hint": nowplaying_blocker,
            "nowplaying": nowplaying_check,
        }
    if loopback_signal_check is not None and loopback_signal_check.get("ok") is False:
        return {
            "code": "selected_loopback_silent",
            "severity": "start_playback",
            "message": "The selected loopback capture is silent.",
            "next_action": "Start playback into the selected loopback route.",
        }
    return {
        "code": "course3_audio_context_incomplete",
        "severity": "unknown",
        "message": "Course 3 audio context is not proven yet.",
        "next_action": "Run readiness with live context and audio diagnostics enabled.",
    }


def build_course3_route_doctor(
    *,
    course3_ready: bool,
    diagnosis: dict[str, Any],
    blockers: list[str] | None = None,
    auto_master_recommendation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return the compact operator packet for discharging Course 3 routing."""
    operator_action = diagnosis.get("operator_action")
    operator_action = operator_action if isinstance(operator_action, dict) else {}
    steps = operator_action.get("steps")
    operator_steps = (
        [str(step) for step in steps if str(step).strip()]
        if isinstance(steps, list)
        else []
    )
    has_operator_action_steps = bool(operator_steps)
    next_action = str(diagnosis.get("next_action") or "").strip()
    if not operator_steps and next_action:
        operator_steps = [next_action]
    blocker_steps = _course3_blocker_operator_steps(blockers or [])
    if blocker_steps:
        if has_operator_action_steps:
            blocker_steps = _filter_redundant_course3_blocker_steps(
                blocker_steps,
                operator_action=operator_action,
                operator_steps=operator_steps,
            )
        if has_operator_action_steps or diagnosis.get("severity") == "fix_rate":
            operator_steps = _dedupe_course3_operator_steps(operator_steps + blocker_steps)
        else:
            operator_steps = _dedupe_course3_operator_steps(blocker_steps + operator_steps)
    route = operator_action.get("route")
    return {
        "ok": bool(course3_ready),
        "status": "ready" if course3_ready else str(diagnosis.get("severity") or "unknown"),
        "diagnosis_code": diagnosis.get("code"),
        "route": str(route) if route else None,
        "next_step": operator_steps[0] if operator_steps else next_action,
        "operator_steps": operator_steps,
        "readiness_command": COURSE3_READINESS_COMMAND,
        "proof_command": COURSE3_PROOF_COMMAND,
        "uses_spoken_prompt": "--say-course3-prompts" in COURSE3_PROOF_COMMAND,
        "auto_master_recommendation": auto_master_recommendation,
    }


def build_physical_connection_doctor(
    *,
    physical_ready: bool,
    blockers: list[str],
    hardware_connection: dict[str, Any],
) -> dict[str, Any]:
    """Return the compact operator packet for discharging physical-controller proof."""
    operator_steps = _physical_blocker_operator_steps(blockers)
    if not operator_steps and physical_ready:
        operator_steps = ["Nudge the left jog wheel during the active L1.07 proof window."]
    elif not operator_steps:
        operator_steps = [
            "Connect and power the DDJ-FLX4 with a USB data cable, then wait for it to appear."
        ]
    if hardware_connection.get("bluetooth_midi_only") is True:
        status = "bluetooth_midi_only"
    elif any("MIDI input" in blocker for blocker in blockers):
        status = "missing_midi"
    elif any("USB or controller audio" in blocker for blocker in blockers):
        status = "missing_usb_or_audio"
    else:
        status = "ready" if physical_ready else "not_ready"
    return {
        "ok": bool(physical_ready),
        "status": status,
        "next_step": operator_steps[0],
        "operator_steps": operator_steps,
        "hardware_connection": hardware_connection,
        "readiness_command": PHYSICAL_READINESS_COMMAND,
        "proof_command": PHYSICAL_PROOF_COMMAND,
        "uses_spoken_prompt": "--say-physical-prompts" in PHYSICAL_PROOF_COMMAND,
    }


def _physical_blocker_operator_steps(blockers: list[str]) -> list[str]:
    steps: list[str] = []
    if any("Bluetooth MIDI" in blocker for blocker in blockers):
        steps.append(
            "Connect the DDJ-FLX4 by USB; Bluetooth MIDI is not enough for hardware proof."
        )
    if any("not visible as a MIDI input" in blocker for blocker in blockers):
        steps.append(
            "Use a data-capable USB cable or powered adapter, then wait for DDJ-FLX4 in MIDI."
        )
    if any("not visible on USB or controller audio" in blocker for blocker in blockers):
        steps.append(
            "Confirm macOS sees DDJ-FLX4 in USB or audio devices before starting the proof."
        )
    return _dedupe_course3_operator_steps(steps)


def _course3_blocker_operator_steps(blockers: list[str]) -> list[str]:
    steps: list[str] = []
    if any("port 8765 is occupied" in blocker for blocker in blockers):
        steps.append(
            "Free 127.0.0.1:8765 so the Vibemix Learn sidecar owns the app socket."
        )
    if any("Bluetooth MIDI" in blocker for blocker in blockers):
        steps.append(
            "Connect the DDJ-FLX4 by USB; Bluetooth MIDI is not enough for routed-audio proof."
        )
    if any("not a loopback capture device" in blocker for blocker in blockers):
        steps.append(
            "Route macOS/Rekordbox output to BlackHole 16ch or the intended loopback route."
        )
    if any("direct loopback capture is silent" in blocker for blocker in blockers):
        steps.append(
            "Play a real Rekordbox library track through the routed master output."
        )
    if any("not Rekordbox" in blocker and "now-playing" in blocker for blocker in blockers):
        steps.append(
            "Stop unrelated browser/system media so Now Playing can point at Rekordbox."
        )
    return steps


def _dedupe_course3_operator_steps(steps: list[str]) -> list[str]:
    deduped: list[str] = []
    seen_buckets: set[str] = set()
    for step in steps:
        bucket = _course3_operator_step_bucket(step)
        if bucket in seen_buckets:
            continue
        seen_buckets.add(bucket)
        deduped.append(step)
    return deduped


def _filter_redundant_course3_blocker_steps(
    blocker_steps: list[str],
    *,
    operator_action: dict[str, Any],
    operator_steps: list[str],
) -> list[str]:
    operator_buckets = {
        _course3_operator_step_bucket(step)
        for step in operator_steps
        if step.strip()
    }
    route = str(operator_action.get("route") or "").strip()
    filtered: list[str] = []
    for step in blocker_steps:
        bucket = _course3_operator_step_bucket(step)
        if bucket in operator_buckets:
            continue
        if bucket == "loopback_route" and route:
            continue
        filtered.append(step)
    return filtered


def _course3_operator_step_bucket(step: str) -> str:
    text = step.lower()
    if "127.0.0.1:8765" in text or "sidecar owns the app socket" in text:
        return "sidecar_socket"
    if (
        "route macos/rekordbox output" in text
        or "switch macos output/system audio" in text
        or "route rekordbox master/output audio" in text
    ):
        return "loopback_route"
    if (
        "real rekordbox library track" in text
        or "start playback" in text
        or ("real library track" in text and "play" in text)
    ):
        return "deck_playback"
    if (
        "now playing" in text
        or "now-playing" in text
        or "stop unrelated media" in text
        or "active playing source" in text
    ):
        return "nowplaying_source"
    return text


def build_summary(
    *,
    requirement: Requirement,
    socket_check: dict[str, Any],
    rekordbox_check: dict[str, Any],
    midi_check: dict[str, Any],
    usb_check: dict[str, Any],
    audio_check: dict[str, Any],
    audio_route_check: dict[str, Any] | None = None,
    loopback_signal_check: dict[str, Any] | None = None,
    loopback_self_test_check: dict[str, Any] | None = None,
    capture_matrix_check: dict[str, Any] | None = None,
    live_context_check: dict[str, Any] | None = None,
    rekordbox_audio_settings_check: dict[str, Any] | None = None,
    nowplaying_check: dict[str, Any] | None = None,
) -> dict[str, Any]:
    def socket_blocker() -> str:
        listener = socket_check.get("listener")
        if isinstance(listener, dict) and listener.get("command"):
            pid = listener.get("pid")
            pid_suffix = f" pid {pid}" if pid else ""
            return (
                f"port 8765 is occupied by {listener['command']}{pid_suffix}, "
                "not the Vibemix Learn sidecar websocket"
            )
        return "sidecar socket is not listening on ws://127.0.0.1:8765"

    def append_blockers_unique(source: Any) -> None:
        if not isinstance(source, list):
            return
        for blocker in source:
            text = str(blocker)
            if text and text not in blockers:
                blockers.append(text)

    screen_ready = bool(socket_check.get("ok"))
    controller_hardware_ready = bool(usb_check.get("ok")) or bool(
        audio_check.get("controller_audio_present")
    )
    bluetooth_midi_matches = bluetooth_midi_controller_matches(midi_check)
    physical_ready = (
        screen_ready
        and bool(midi_check.get("ok"))
        and controller_hardware_ready
    )
    loopback_signal_failed = (
        requirement == "course3"
        and loopback_signal_check is not None
        and loopback_signal_check.get("enabled") is True
        and loopback_signal_check.get("ok") is False
    )
    capture_matrix_failed = (
        requirement == "course3"
        and capture_matrix_check is not None
        and capture_matrix_check.get("enabled") is True
        and capture_matrix_check.get("ok") is False
    )
    loopback_self_test_failed = (
        requirement == "course3"
        and loopback_self_test_check is not None
        and loopback_self_test_check.get("enabled") is True
        and loopback_self_test_check.get("ok") is False
        and not _loopback_self_test_is_inconclusive_for_rekordbox_route(
            loopback_self_test_check,
            rekordbox_audio_settings_check,
        )
    )
    course3_diagnostics_ready = not (
        loopback_signal_failed or capture_matrix_failed or loopback_self_test_failed
    )
    course3_ready = (
        screen_ready
        and bool(rekordbox_check.get("ok"))
        and bool(audio_check.get("loopback_present"))
        and bool(audio_check.get("dj_audio_present"))
        and course3_diagnostics_ready
        and (live_context_check is None or bool(live_context_check.get("ok")))
    )
    blockers: list[str] = []
    if not screen_ready:
        blockers.append(socket_blocker())
    if requirement == "physical" and not midi_check.get("ok"):
        blockers.append("physical controller is not visible as a MIDI input")
    if requirement == "physical" and not controller_hardware_ready:
        if bluetooth_midi_matches:
            blockers.append(
                "DDJ-FLX4 is visible only as Bluetooth MIDI; connect it by USB "
                "for Learn hardware/audio proof"
            )
        else:
            blockers.append("physical controller is not visible on USB or controller audio")
    if requirement == "course3" and not rekordbox_check.get("ok"):
        blockers.append("Rekordbox process is not running")
    if requirement == "course3" and not audio_check.get("loopback_present"):
        blockers.append("loopback audio device is not visible")
    if requirement == "course3" and not audio_check.get("dj_audio_present"):
        if bluetooth_midi_matches:
            blockers.append(
                "DDJ-FLX4 Bluetooth MIDI does not provide controller audio to this Mac; "
                "use USB or a routed Rekordbox/loopback audio device"
            )
        else:
            blockers.append("DJ app or controller audio device is not visible")
    if loopback_self_test_failed:
        append_blockers_unique(loopback_self_test_check.get("blockers"))
    if loopback_signal_failed:
        append_blockers_unique(loopback_signal_check.get("blockers"))
    if capture_matrix_failed:
        append_blockers_unique(capture_matrix_check.get("blockers"))
    if requirement == "course3" and live_context_check is not None and not live_context_check.get("ok"):
        append_blockers_unique(live_context_check.get("blockers"))
        if (
            "live master audio is not audible yet" in live_context_check.get("blockers", [])
            and audio_route_check is not None
            and audio_route_check.get("available") is True
            and audio_route_check.get("ok") is False
        ):
            append_blockers_unique(audio_route_check.get("blockers"))
        if (
            "live master audio is not audible yet" in live_context_check.get("blockers", [])
            and loopback_self_test_check is not None
            and loopback_self_test_check.get("enabled") is True
            and loopback_self_test_check.get("ok") is False
            and not _loopback_self_test_is_inconclusive_for_rekordbox_route(
                loopback_self_test_check,
                rekordbox_audio_settings_check,
            )
        ):
            append_blockers_unique(loopback_self_test_check.get("blockers"))
        if (
            "live master audio is not audible yet" in live_context_check.get("blockers", [])
            and loopback_signal_check is not None
            and loopback_signal_check.get("enabled") is True
            and loopback_signal_check.get("ok") is False
        ):
            append_blockers_unique(loopback_signal_check.get("blockers"))
        if (
            "live master audio is not audible yet" in live_context_check.get("blockers", [])
            and capture_matrix_check is not None
            and capture_matrix_check.get("enabled") is True
        ):
            if capture_matrix_check.get("ok") is False:
                append_blockers_unique(capture_matrix_check.get("blockers"))
            elif (
                loopback_signal_check is not None
                and loopback_signal_check.get("ok") is False
                and isinstance(capture_matrix_check.get("top_signal"), dict)
            ):
                top_signal = capture_matrix_check["top_signal"]
                blockers.append(
                    "capture signal is present on "
                    f"{top_signal.get('name')!r}, but the selected loopback capture is silent"
                )
    if requirement == "course3" and not course3_ready:
        nowplaying_blocker = _course3_nowplaying_blocker(nowplaying_check)
        if nowplaying_blocker and nowplaying_blocker not in blockers:
            blockers.append(nowplaying_blocker)

    readiness = {
        "screen_learn": screen_ready,
        "physical_learn": physical_ready,
        "course3_audio": course3_ready,
    }
    if requirement == "none":
        passed = True
    else:
        passed = bool(readiness[requirement_to_readiness_key(requirement)])
    auto_master_recommendation = recommend_auto_master_input(
        capture_matrix_check=capture_matrix_check,
        rekordbox_audio_settings_check=rekordbox_audio_settings_check,
        audio_route_check=audio_route_check,
    )
    course3_audio_diagnosis = diagnose_course3_audio(
        audio_route_check=audio_route_check,
        loopback_self_test_check=loopback_self_test_check,
        loopback_signal_check=loopback_signal_check,
        capture_matrix_check=capture_matrix_check,
        live_context_check=live_context_check,
        rekordbox_audio_settings_check=rekordbox_audio_settings_check,
        auto_master_recommendation=auto_master_recommendation,
        nowplaying_check=nowplaying_check,
    )
    hardware_connection = {
        "bluetooth_midi_only": bool(bluetooth_midi_matches)
        and not controller_hardware_ready,
        "bluetooth_midi_matches": bluetooth_midi_matches,
        "controller_hardware_ready": controller_hardware_ready,
    }
    physical_connection_doctor = (
        build_physical_connection_doctor(
            physical_ready=physical_ready,
            blockers=blockers,
            hardware_connection=hardware_connection,
        )
        if requirement == "physical"
        else None
    )
    course3_route_doctor = (
        build_course3_route_doctor(
            course3_ready=course3_ready,
            diagnosis=course3_audio_diagnosis,
            blockers=blockers,
            auto_master_recommendation=auto_master_recommendation,
        )
        if requirement == "course3"
        else None
    )
    return {
        "passed": passed,
        "requirement": requirement,
        "readiness": readiness,
        "blockers": blockers,
        "course3_audio_diagnosis": course3_audio_diagnosis,
        "course3_route_doctor": course3_route_doctor,
        "auto_master_recommendation": auto_master_recommendation,
        "hardware_connection": hardware_connection,
        "physical_connection_doctor": physical_connection_doctor,
        "checks": {
            "sidecar_socket": socket_check,
            "rekordbox_process": rekordbox_check,
            "midi_controller": midi_check,
            "usb_controller": usb_check,
            "audio_devices": audio_check,
            "audio_route": audio_route_check,
            "loopback_signal": loopback_signal_check,
            "loopback_self_test": loopback_self_test_check,
            "capture_matrix": capture_matrix_check,
            "course3_live_context": live_context_check,
            "rekordbox_audio_settings": rekordbox_audio_settings_check,
            "nowplaying": nowplaying_check,
        },
        "next_commands": next_commands(readiness),
    }


def requirement_to_readiness_key(requirement: Requirement) -> str:
    return {
        "none": "screen_learn",
        "screen": "screen_learn",
        "physical": "physical_learn",
        "course3": "course3_audio",
    }[requirement]


def next_commands(readiness: dict[str, bool]) -> list[str]:
    commands = [
        "VIBEMIX_LEARN_PROGRESS_PATH=/tmp/vibemix-live-learn-proof/learn-progress.json uv run python -m vibemix",
    ]
    if readiness.get("screen_learn"):
        commands.append("uv run python scripts/live_learn_screen_probe.py --seconds 60")
    if readiness.get("physical_learn"):
        commands.append("uv run python scripts/live_learn_socket_jog_probe.py --seconds 20")
    else:
        commands.append("uv run python scripts/sniff_controller.py --list")
    if readiness.get("course3_audio"):
        commands.append("uv run python scripts/live_course3_lens_probe.py --require-count-in --seconds 30")
    return commands


def collect_readiness(
    *,
    requirement: Requirement,
    url: str,
    live_context_seconds: float = 0.0,
    loopback_signal_seconds: float = 0.0,
    loopback_self_test_seconds: float = 0.0,
    capture_matrix_seconds: float = 0.0,
) -> dict[str, Any]:
    socket_check = check_socket(url)
    rekordbox_check = check_rekordbox_process()
    rekordbox_audio_settings_check = check_rekordbox_audio_settings()
    midi_check = check_midi_ports()
    usb_check = check_usb_controller()
    audio_check = check_audio_devices()
    audio_route_check = check_audio_route()
    nowplaying_check = check_nowplaying() if requirement == "course3" else None
    preferred_loopback = preferred_loopback_device_for_readiness(
        requirement=requirement,
        audio_route_check=audio_route_check,
        rekordbox_audio_settings_check=rekordbox_audio_settings_check,
    )
    loopback_signal_check = check_loopback_signal(
        seconds=loopback_signal_seconds,
        preferred_device=preferred_loopback,
    )
    loopback_self_test_check = check_loopback_self_test(
        seconds=loopback_self_test_seconds,
        preferred_device=preferred_loopback,
    )
    capture_matrix_check = check_capture_matrix(seconds=capture_matrix_seconds)
    live_context_check = None
    if requirement == "course3" and socket_check.get("ok") and live_context_seconds > 0:
        live_context_check = check_live_course3_context(url, seconds=live_context_seconds)
    return build_summary(
        requirement=requirement,
        socket_check=socket_check,
        rekordbox_check=rekordbox_check,
        midi_check=midi_check,
        usb_check=usb_check,
        audio_check=audio_check,
        audio_route_check=audio_route_check,
        loopback_signal_check=loopback_signal_check,
        loopback_self_test_check=loopback_self_test_check,
        capture_matrix_check=capture_matrix_check,
        live_context_check=live_context_check,
        rekordbox_audio_settings_check=rekordbox_audio_settings_check,
        nowplaying_check=nowplaying_check,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="learn_live_readiness",
        description="Preflight live Learn proof readiness without starting new listeners.",
    )
    parser.add_argument("--url", default=DEFAULT_WS_URL, help=f"Sidecar URL (default: {DEFAULT_WS_URL}).")
    parser.add_argument(
        "--live-context-seconds",
        type=float,
        default=1.5,
        help=(
            "When --require course3 and the sidecar is live, sample flat socket "
            "frames for audible deck + citable deck_state context."
        ),
    )
    parser.add_argument(
        "--loopback-signal-seconds",
        type=float,
        default=0.0,
        help=(
            "Optionally sample the selected loopback input directly and report "
            "RMS/peak signal evidence."
        ),
    )
    parser.add_argument(
        "--loopback-self-test-seconds",
        type=float,
        default=0.0,
        help=(
            "Optionally emit a quiet known tone through the selected loopback "
            "device and capture it back to prove loopback route health."
        ),
    )
    parser.add_argument(
        "--capture-matrix-seconds",
        type=float,
        default=0.0,
        help=(
            "Optionally sample every relevant DJ/loopback input and rank "
            "where signal is actually present."
        ),
    )
    parser.add_argument(
        "--require",
        choices=("none", "screen", "physical", "course3"),
        default="none",
        help="Exit non-zero unless this proof path is ready.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Optionally write the readiness JSON to this artifact path.",
    )
    return parser


def write_summary(summary: dict[str, Any], out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return out_path


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    live_context_seconds = args.live_context_seconds if args.require == "course3" else 0.0
    summary = collect_readiness(
        requirement=args.require,
        url=args.url,
        live_context_seconds=live_context_seconds,
        loopback_signal_seconds=args.loopback_signal_seconds,
        loopback_self_test_seconds=args.loopback_self_test_seconds,
        capture_matrix_seconds=args.capture_matrix_seconds,
    )
    if args.out is not None:
        write_summary(summary, args.out)
    print(json.dumps(summary, sort_keys=True))
    return 0 if summary.get("passed") is True else 4


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
