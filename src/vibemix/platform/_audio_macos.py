# SPDX-License-Identifier: Apache-2.0
"""Concrete ``AudioBackend`` impl for macOS.

Owns all sounddevice / resampler imports — the Phase 1 platform firewall keeps these
out of `vibemix.platform.audio` (the typing-only Protocol module). Wires the v4
stream factories (cohost_v4.py:855-947 + 1895-1908) into a class that satisfies
the Phase 1 Protocol firewall.

Sample-rate sanity guard (RESEARCH.md Q2) catches the BlackHole 44100-vs-48000
mismatch Kaan hit live on 2026-05-11 — Audio MIDI Setup misconfig is detected
pre-open (via `sd.query_devices(idx)['default_samplerate']`, the only API on
macOS CoreAudio that reflects the live device setting) AND post-open (via
``Stream.samplerate`` for hardware drift on Multi-Output Devices).

Drops the v4 ``_HAS_VISION`` / ``_HAS_WS`` / ``_HAS_QUARTZ`` feature-flag
anti-pattern (PATTERNS.md §AntiPatterns-2) — if `sounddevice` fails to import,
this module fails loud, no silent degradation.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

import sounddevice as sd

from vibemix.audio.device_select import (
    MasterCaptureNotFoundError,
    find_device_index,
    is_controller_device,
    is_mic_device,
    select_master_input,
    select_output_device,
)
from vibemix.audio.errors import SampleRateMismatchError
from vibemix.audio.recorder import VoiceRecorder
from vibemix.audio.registry import BufferRegistry
from vibemix.platform.audio import AudioCallback, AudioStream, Kind

_AUTO_MASTER_ENV = "VIBEMIX_AUTO_MASTER_INPUT"
_AUTO_MASTER_FALLBACK_ENV = "VIBEMIX_AUTO_MASTER_FALLBACK_DEVICE"
_AUTO_MASTER_REQUESTS = {"auto", "auto-master", "master", "master-auto"}
_AUTO_MASTER_EXPECTED_SR = 48000
_AUTO_MASTER_PROBE_SECONDS = 0.35
_AUTO_MASTER_RMS_FLOOR = 0.003
_LOOPBACK_TOKENS = (
    "blackhole",
    "loopback",
    "vb-cable",
    "soundflower",
    "capture",
    "aggregate",
)


def assert_device_sample_rate(device_index: int, expected: int) -> None:
    """Pre-open guard: assert the device's CURRENT driver sample rate matches `expected`.

    Reads ``sd.query_devices(idx)['default_samplerate']`` — on macOS CoreAudio
    this reflects ``kAudioDevicePropertyNominalSampleRate``, i.e. whatever
    Audio MIDI Setup is configured to right now. NOT the same as
    ``Stream.samplerate`` after opening (which reports the PortAudio-negotiated
    rate and silently lies about device drift — RESEARCH.md Q2).

    On mismatch, attempts to set the rate programmatically via
    ``set_device_nominal_sample_rate`` (best-effort — PyObjC's CoreAudio
    binding for void* is not always usable). If that fails, opens Audio
    MIDI Setup so the user can flip the rate by hand, then raises a
    ``SampleRateMismatchError`` with the exact fix steps.
    """
    info = sd.query_devices(device_index)
    actual = int(info["default_samplerate"])
    name = info.get("name", f"device {device_index}")
    if actual == expected:
        return
    if set_device_nominal_sample_rate(name, expected):
        info = sd.query_devices(device_index)
        if int(info["default_samplerate"]) == expected:
            return
    # Best-effort auto-fix failed — fall back to opening Audio MIDI Setup
    # so the user lands one click from the right device.
    try:
        import subprocess

        subprocess.Popen(
            ["open", "-a", "Audio MIDI Setup"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass
    raise SampleRateMismatchError(
        f"{name} is configured at {actual}Hz but vibemix expects {expected}Hz.\n"
        f"Opened Audio MIDI Setup — select {name} on the left, then "
        f"set Format to {expected:,} Hz, 2 ch.\n"
        f"For BlackHole-backed Multi-Output Devices, also tick 'Drift "
        f"Correction' on the BlackHole row so the OS resamples cleanly."
    )


def _make_input_resampler(
    callback: AudioCallback,
    *,
    device_sr: int,
    target_sr: int,
    channels: int,
) -> AudioCallback:
    """Wrap an input callback so device-native-rate capture buffers are resampled
    to ``target_sr`` before the grounding callback sees them.

    The inverse of ``open_passthrough_output``'s resample_wrapper: capture pulls
    device-rate audio in and converts it to the analysis rate, so the grounding
    engine always operates at the rate it expects regardless of the hardware
    default. Holding grounding on the right rate is the anti-mis-ground guarantee.
    """
    import numpy as np

    from vibemix.audio.resample import resample_audio

    def resample_input_wrapper(indata, frames, time_info, status):
        per_channel = [
            resample_audio(
                np.asarray(indata[:, ch], dtype=np.float32),
                source_sr=device_sr,
                target_sr=target_sr,
            )
            for ch in range(channels)
        ]
        out_frames = per_channel[0].shape[0] if per_channel else 0
        converted = np.zeros((out_frames, channels), dtype=np.float32)
        for ch in range(channels):
            converted[:, ch] = per_channel[ch]
        callback(converted, out_frames, time_info, status)

    return resample_input_wrapper


def set_device_nominal_sample_rate(device_name: str, rate: int) -> bool:
    """Set a CoreAudio device's nominal sample rate via the AudioToolbox API.

    Uses pyobjc's CoreAudio bindings to walk
    kAudioHardwarePropertyDevices, match by deviceNameCFString, then write
    kAudioDevicePropertyNominalSampleRate. Falls back to the system Swift
    CoreAudio bridge because PyObjC cannot reliably marshal this void-buffer
    API on every local install. Returns True on success, False on any failure
    (device not found, rate unsupported, API error).
    """
    return _set_device_nominal_sample_rate_pyobjc(
        device_name,
        rate,
    ) or _set_device_nominal_sample_rate_swift(device_name, rate)


def _set_device_nominal_sample_rate_pyobjc(device_name: str, rate: int) -> bool:
    """Best-effort PyObjC implementation for programmatic rate repair."""
    try:
        from CoreAudio import (  # type: ignore[import-not-found]
            AudioObjectGetPropertyData,
            AudioObjectGetPropertyDataSize,
            AudioObjectPropertyAddress,
            AudioObjectSetPropertyData,
        )
    except Exception:
        return False

    def fourcc(s: str) -> int:
        return int.from_bytes(s.encode("ascii"), "big")

    kAudioObjectSystemObject = 1
    kAudioHardwarePropertyDevices = fourcc("dev#")
    kAudioDevicePropertyDeviceNameCFString = fourcc("lnam")
    kAudioDevicePropertyNominalSampleRate = fourcc("nsrt")
    kAudioObjectPropertyScopeGlobal = fourcc("glob")
    kAudioObjectPropertyElementMain = 0

    addr = AudioObjectPropertyAddress(
        kAudioHardwarePropertyDevices,
        kAudioObjectPropertyScopeGlobal,
        kAudioObjectPropertyElementMain,
    )
    try:
        status, size = AudioObjectGetPropertyDataSize(kAudioObjectSystemObject, addr, 0, None, None)
    except Exception:
        return False
    if status != 0 or size == 0:
        return False

    try:
        status, _size, device_ids = AudioObjectGetPropertyData(
            kAudioObjectSystemObject, addr, 0, None, size, None
        )
    except Exception:
        return False
    if status != 0 or not device_ids:
        return False

    name_addr = AudioObjectPropertyAddress(
        kAudioDevicePropertyDeviceNameCFString,
        kAudioObjectPropertyScopeGlobal,
        kAudioObjectPropertyElementMain,
    )
    rate_addr = AudioObjectPropertyAddress(
        kAudioDevicePropertyNominalSampleRate,
        kAudioObjectPropertyScopeGlobal,
        kAudioObjectPropertyElementMain,
    )

    for dev_id in device_ids:
        try:
            status_n, name_size = AudioObjectGetPropertyDataSize(dev_id, name_addr, 0, None, None)
            if status_n != 0:
                continue
            status_n, _sz, name_obj = AudioObjectGetPropertyData(
                dev_id, name_addr, 0, None, name_size, None
            )
            if status_n != 0 or name_obj is None:
                continue
            device_str = str(name_obj)
        except Exception:
            continue
        if device_str != device_name:
            continue
        try:
            status_r, _sz, cur_rate = AudioObjectGetPropertyData(
                dev_id, rate_addr, 0, None, 8, None
            )
        except Exception:
            return False
        if status_r != 0:
            return False
        try:
            cur_value = float(cur_rate)
        except (TypeError, ValueError):
            cur_value = 0.0
        if int(cur_value) == rate:
            return True
        try:
            set_status = AudioObjectSetPropertyData(dev_id, rate_addr, 0, None, 8, float(rate))
        except Exception:
            return False
        return set_status == 0
    return False


def _set_device_nominal_sample_rate_swift(device_name: str, rate: int) -> bool:
    """Use Swift/CoreAudio to set a device rate when PyObjC marshalling fails."""
    script = f"""
import CoreAudio
import Foundation

let targetName = {json.dumps(device_name)}
let targetRate = Float64({float(rate)!r})

var devicesAddress = AudioObjectPropertyAddress(
    mSelector: kAudioHardwarePropertyDevices,
    mScope: kAudioObjectPropertyScopeGlobal,
    mElement: kAudioObjectPropertyElementMain
)
var dataSize: UInt32 = 0
var status = AudioObjectGetPropertyDataSize(
    AudioObjectID(kAudioObjectSystemObject),
    &devicesAddress,
    0,
    nil,
    &dataSize
)
if status != noErr {{ exit(10) }}
let count = Int(dataSize) / MemoryLayout<AudioDeviceID>.size
var devices = [AudioDeviceID](repeating: 0, count: count)
status = AudioObjectGetPropertyData(
    AudioObjectID(kAudioObjectSystemObject),
    &devicesAddress,
    0,
    nil,
    &dataSize,
    &devices
)
if status != noErr {{ exit(11) }}

func nominalRate(_ id: AudioDeviceID) -> Float64? {{
    var rateAddress = AudioObjectPropertyAddress(
        mSelector: kAudioDevicePropertyNominalSampleRate,
        mScope: kAudioObjectPropertyScopeGlobal,
        mElement: kAudioObjectPropertyElementMain
    )
    var rate = Float64(0)
    var size = UInt32(MemoryLayout<Float64>.size)
    let status = AudioObjectGetPropertyData(id, &rateAddress, 0, nil, &size, &rate)
    return status == noErr ? rate : nil
}}

for id in devices {{
    var nameAddress = AudioObjectPropertyAddress(
        mSelector: kAudioObjectPropertyName,
        mScope: kAudioObjectPropertyScopeGlobal,
        mElement: kAudioObjectPropertyElementMain
    )
    var name: CFString = "" as CFString
    var nameSize = UInt32(MemoryLayout<CFString>.size)
    let nameStatus = AudioObjectGetPropertyData(
        id,
        &nameAddress,
        0,
        nil,
        &nameSize,
        &name
    )
    if nameStatus != noErr || (name as String) != targetName {{ continue }}
    if Int(nominalRate(id) ?? 0) == Int(targetRate) {{ exit(0) }}

    var rateAddress = AudioObjectPropertyAddress(
        mSelector: kAudioDevicePropertyNominalSampleRate,
        mScope: kAudioObjectPropertyScopeGlobal,
        mElement: kAudioObjectPropertyElementMain
    )
    var newRate = targetRate
    let setStatus = AudioObjectSetPropertyData(
        id,
        &rateAddress,
        0,
        nil,
        UInt32(MemoryLayout<Float64>.size),
        &newRate
    )
    if setStatus != noErr {{ exit(13) }}
    for _ in 0..<20 {{
        if Int(nominalRate(id) ?? 0) == Int(targetRate) {{ exit(0) }}
        usleep(100_000)
    }}
    exit(14)
}}
exit(12)
"""
    try:
        proc = subprocess.run(
            ["swift", "-"],
            input=script,
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return proc.returncode == 0


def _env_enabled(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _info_name(info) -> str:
    name = info.get("name") if hasattr(info, "get") else None
    return name if isinstance(name, str) else ""


def _info_int(info, key: str) -> int:
    try:
        return int(info.get(key, 0) or 0)
    except (TypeError, ValueError):
        return 0


def _is_loopback_candidate(name: str) -> bool:
    low = name.lower()
    return any(token in low for token in _LOOPBACK_TOKENS)


def _active_master_candidates(devices) -> list[tuple[int, object]]:
    """Candidate master inputs for the signal-aware auto finder."""
    candidates: list[tuple[int, object]] = []
    for idx, info in enumerate(devices):
        if _info_int(info, "max_input_channels") <= 0:
            continue
        name = _info_name(info)
        if not name:
            continue
        if is_controller_device(name) or is_mic_device(name):
            continue
        if not _is_loopback_candidate(name):
            continue
        candidates.append((idx, info))
    return candidates


def _probe_input_rms(
    device_index: int,
    info,
    *,
    seconds: float = _AUTO_MASTER_PROBE_SECONDS,
) -> dict:
    """Sample a candidate briefly and return signal metrics.

    This is intentionally small and startup-only. It never runs on the normal
    deterministic path unless ``VIBEMIX_AUTO_MASTER_INPUT`` or ``auto`` is used.
    """
    import numpy as np

    name = _info_name(info)
    sample_rate = _info_int(info, "default_samplerate") or _AUTO_MASTER_EXPECTED_SR
    channels = max(1, min(2, _info_int(info, "max_input_channels") or 1))
    frames = max(1, int(sample_rate * seconds))
    try:
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
        error = None
    except Exception as exc:
        rms = 0.0
        peak = 0.0
        error = repr(exc)
    return {
        "index": device_index,
        "name": name,
        "sample_rate": sample_rate,
        "rms": rms,
        "peak": peak,
        "error": error,
    }


def _master_probe_score(row: dict) -> tuple[float, float, int, int]:
    name = str(row.get("name") or "").lower()
    rms = float(row.get("rms") or 0.0)
    sample_rate = int(row.get("sample_rate") or 0)
    live = 1 if rms >= _AUTO_MASTER_RMS_FLOOR else 0
    rate_match = 1 if sample_rate == _AUTO_MASTER_EXPECTED_SR else 0
    exact_2ch = 1 if name == "blackhole 2ch" else 0
    blackhole = 1 if "blackhole" in name else 0
    # Live signal dominates; rate match beats exact 2ch when the signal is on
    # another BlackHole variant. The small name bonus only breaks true ties.
    return (
        float(live * 1000) + min(rms * 1000.0, 100.0),
        float(rate_match * 100 + exact_2ch * 5 + blackhole),
        -int(row.get("index") or 0),
        0,
    )


def _preferred_auto_master_fallback(probes: list[dict]) -> dict | None:
    requested = os.environ.get(_AUTO_MASTER_FALLBACK_ENV, "").strip().lower()
    if not requested:
        return None
    exact = [row for row in probes if str(row.get("name") or "").strip().lower() == requested]
    if exact:
        return max(exact, key=_master_probe_score)
    fuzzy = [row for row in probes if requested in str(row.get("name") or "").strip().lower()]
    if fuzzy:
        return max(fuzzy, key=_master_probe_score)
    return None


def select_active_master_input(devices) -> int:
    """Signal-aware master input selection for live rigs.

    Static ranking is still the default. This helper is the opt-in "auto master
    finder": briefly sample loopback/capture candidates, pick the one that is
    actually carrying audio, and prefer the expected 48 kHz path when multiple
    candidates are live. If nothing is live, fall back to the existing
    BlackHole-only selector so startup remains deterministic and safe.
    """
    candidates = _active_master_candidates(devices)
    probes = [_probe_input_rms(idx, info) for idx, info in candidates]
    live = [row for row in probes if float(row.get("rms") or 0.0) >= _AUTO_MASTER_RMS_FLOOR]
    if live:
        chosen = max(live, key=_master_probe_score)
        print(
            "[audio] auto master input: "
            f"{chosen['name']} @ {chosen['sample_rate']}Hz "
            f"rms={chosen['rms']:.4f} peak={chosen['peak']:.4f}",
            file=sys.stderr,
            flush=True,
        )
        return int(chosen["index"])
    preferred = _preferred_auto_master_fallback(probes)
    if preferred is not None:
        print(
            "[audio] auto master input: "
            f"{preferred['name']} @ {preferred['sample_rate']}Hz "
            "(preferred fallback; no live signal during startup probe)",
            file=sys.stderr,
            flush=True,
        )
        return int(preferred["index"])
    expected_rate = [
        row
        for row in probes
        if int(row.get("sample_rate") or 0) == _AUTO_MASTER_EXPECTED_SR
        and "blackhole" in str(row.get("name") or "").lower()
    ]
    if expected_rate:
        chosen = max(expected_rate, key=_master_probe_score)
        print(
            "[audio] auto master input: "
            f"{chosen['name']} @ {chosen['sample_rate']}Hz "
            "(48k fallback; no live signal during startup probe)",
            file=sys.stderr,
            flush=True,
        )
        return int(chosen["index"])
    try:
        return select_master_input(devices)
    except MasterCaptureNotFoundError as exc:
        probe_summary = [
            {
                "name": row["name"],
                "sample_rate": row["sample_rate"],
                "rms": round(float(row["rms"]), 6),
                "peak": round(float(row["peak"]), 6),
                "error": row["error"],
            }
            for row in probes
        ]
        raise RuntimeError(
            f"auto master input: no live loopback/capture input found; probes={probe_summary}"
        ) from exc


class _SoundDeviceStreamHandle:
    """Adapter from ``sd.Input/Output/RawInput/RawOutputStream`` to the Phase 1
    ``AudioStream`` Protocol (latency_ms + start/stop/close)."""

    def __init__(
        self,
        stream: sd.InputStream | sd.OutputStream | sd.RawInputStream | sd.RawOutputStream,
    ) -> None:
        self._stream = stream

    @property
    def latency_ms(self) -> float:
        lat = self._stream.latency
        # sd.Stream.latency is a (in, out) tuple for duplex streams; scalar otherwise.
        if isinstance(lat, tuple):
            lat = lat[0]
        return float(lat) * 1000.0

    def start(self) -> None:
        self._stream.start()

    def stop(self) -> None:
        self._stream.stop()

    def close(self) -> None:
        self._stream.close()


class AudioMacOS:
    """macOS ``AudioBackend`` impl wrapping sounddevice.

    Satisfies the Phase 1 ``AudioBackend`` Protocol structurally via
    ``@runtime_checkable`` — no inheritance. Plus ``open_mic_capture`` as a
    macOS-only extension (PATTERNS.md §AntiPatterns-5 — wraps the v4:1895-1908
    inline mic stream into a proper factory for symmetry with the other three).

    Constructor takes the `BufferRegistry` + `VoiceRecorder` so a caller-side
    factory can build the v4 dual-buffer input callback (Plan 04 of Phase 3
    territory) by closing over them. This class itself focuses on I/O lifecycle
    + sample-rate guards, not the dual-buffer choreography.
    """

    def __init__(self, registry: BufferRegistry, recorder: VoiceRecorder) -> None:
        self.registry = registry
        self.recorder = recorder

    def find_device(self, name_substring: str, kind: Kind) -> int:
        """Find a CoreAudio device for ``name_substring`` of the given ``kind``.

        MASTER-CAPTURE path (the release-blocking bug, 2026-05-24): generic
        BlackHole requests still delegate to
        :func:`vibemix.audio.device_select.select_master_input`, which *ranks*
        candidates — exact ``BlackHole 2ch`` first, then other BlackHole
        variants — and EXCLUDES the DJ-controller soundcard (DDJ-FLX4 et al.)
        and any microphone. The old naive substring scan returned whichever
        input CoreAudio enumerated first, so the co-host grabbed the
        controller instead of the master output.

        Live rigs can opt into ``VIBEMIX_AUTO_MASTER_INPUT=1`` (or request
        ``"auto"``) to briefly sample loopback/capture inputs and choose the
        one actually carrying the master. Explicit variant requests like
        ``"BlackHole 16ch"`` are honored exactly; they no longer get rewritten
        back to the canonical 2ch default.

        OUTPUT and MIC paths keep a plain case-insensitive substring match
        (the caller passes an explicit, unambiguous device name there). On a
        miss, raises ``RuntimeError`` with the candidate-device list so the
        user sees "available inputs: [...]" rather than a cryptic PortAudio
        stack trace (RESEARCH.md Threat 4).
        """
        devices = sd.query_devices()
        low = name_substring.strip().lower()
        if kind == "input" and (
            low in _AUTO_MASTER_REQUESTS or ("blackhole" in low and _env_enabled(_AUTO_MASTER_ENV))
        ):
            return select_active_master_input(devices)
        if kind == "input" and "blackhole" in low:
            if low not in {"blackhole", "blackhole 2ch"}:
                return find_device_index(devices, name_substring, kind)
            try:
                return select_master_input(devices)
            except MasterCaptureNotFoundError as e:
                # Re-raise as RuntimeError carrying the requested name so the
                # __main__ FATAL handler's ``INPUT_DEVICE in str(e)`` check
                # still classifies this as an input-device miss (exit code 3).
                raise RuntimeError(f"{name_substring}: {e}") from e
        return find_device_index(devices, name_substring, kind)

    def find_output_device(self, preferred_index: int | None, fallback_name: str) -> int:
        """Resolve the AI-voice / passthrough OUTPUT device, degrading gracefully.

        Unlike :meth:`find_device` (which hard-fails on a substring miss), this
        never crashes when the hardcoded ``OUTPUT_DEVICE`` name is absent — a Mac
        mini / Mac Studio / iMac, external speakers or headphones, a renamed
        output, or a non-English macOS all lack "MacBook Pro Speakers". It prefers
        the wizard-persisted output device index, then the name, then the OS
        default output, then any real (non-loopback) output. See
        :func:`vibemix.audio.device_select.select_output_device`.
        """
        devices = sd.query_devices()
        default_out: int | None = None
        try:
            d = sd.default.device  # (input_idx, output_idx)
            if isinstance(d, (list, tuple)) and len(d) >= 2 and isinstance(d[1], int) and d[1] >= 0:
                default_out = int(d[1])
        except Exception:
            default_out = None
        return select_output_device(
            devices,
            preferred_index=preferred_index,
            fallback_name=fallback_name,
            default_index=default_out,
        )

    def describe_capture_input(
        self,
        device_index: int,
        *,
        requested_device: str,
        opened_channels: int,
    ) -> dict[str, object]:
        """Return bounded capture metadata for live LLM deck-audio context."""
        try:
            info = sd.query_devices(device_index)
        except Exception:
            return {
                "requested_device": requested_device,
                "device_name": "unknown",
                "input_channels": 0,
                "opened_channels": opened_channels,
                "sample_rate": 0,
            }
        return {
            "requested_device": requested_device,
            "device_name": str(info.get("name") or "unknown"),
            "input_channels": int(info.get("max_input_channels") or 0),
            "opened_channels": int(opened_channels),
            "sample_rate": int(float(info.get("default_samplerate") or 0)),
        }

    def open_capture(
        self,
        device_index: int,
        *,
        sample_rate: int,
        channels: int,
        block_size: int,
        callback: AudioCallback,
    ) -> AudioStream:
        """Open input capture stream (sd.InputStream @ float32 low-latency).

        Pre-open: ``assert_device_sample_rate`` (reads Audio MIDI Setup state).
        Post-open: ``stream.samplerate`` belt-and-suspenders (catches hardware
        drift on Multi-Output Devices). On either failure raises
        ``SampleRateMismatchError`` AND closes the stream to avoid leaks.
        """
        info = sd.query_devices(device_index)
        device_sr = int(info["default_samplerate"])
        if device_sr != sample_rate:
            # Master device runs at a non-analysis rate (e.g. a factory-default
            # 44.1k BlackHole). Open at its native rate and resample to the
            # analysis rate instead of forcing the OS rate — mirrors
            # open_passthrough_output. Grounding still sees ``sample_rate`` audio,
            # so a 44.1k rig no longer crashes main() at the first track.
            open_block = max(1, round(block_size * (device_sr / sample_rate)))
            wrapped = _make_input_resampler(
                callback, device_sr=device_sr, target_sr=sample_rate, channels=channels
            )
            stream = sd.InputStream(
                device=device_index,
                samplerate=device_sr,
                channels=channels,
                dtype="float32",
                blocksize=open_block,
                latency="low",
                callback=wrapped,
            )
            if int(stream.samplerate) != device_sr:
                negotiated = int(stream.samplerate)
                stream.close()
                raise SampleRateMismatchError(
                    f"PortAudio negotiated {negotiated}Hz vs requested {device_sr}Hz on "
                    f"device {device_index!r}."
                )
            stream.start()
            return _SoundDeviceStreamHandle(stream)

        # Device already at the analysis rate — the proven 48k path, unchanged.
        assert_device_sample_rate(device_index, sample_rate)
        stream = sd.InputStream(
            device=device_index,
            samplerate=sample_rate,
            channels=channels,
            dtype="float32",
            blocksize=block_size,
            latency="low",
            callback=callback,
        )
        if int(stream.samplerate) != sample_rate:
            negotiated = int(stream.samplerate)
            stream.close()
            raise SampleRateMismatchError(
                f"PortAudio negotiated {negotiated}Hz vs requested {sample_rate}Hz on "
                f"device {device_index!r}. Hardware drift detected — enable Drift "
                f"Correction in Audio MIDI Setup."
            )
        stream.start()
        return _SoundDeviceStreamHandle(stream)

    def open_passthrough_output(
        self,
        device_index: int,
        *,
        sample_rate: int,
        channels: int,
        block_size: int,
        callback: AudioCallback,
    ) -> AudioStream:
        """Open passthrough output (sd.OutputStream @ float32 stereo).

        Passthrough is not authoritative analysis audio; it is a monitor path
        and is currently silent by default. Open it at the device's native rate
        when the selected output is 44.1 kHz so Rekordbox/macOS output routing
        does not prevent vibemix from booting.
        """
        import numpy as np

        info = sd.query_devices(device_index)
        device_sr = int(info["default_samplerate"])
        if device_sr == sample_rate:
            open_sr = sample_rate
            open_block = block_size
            wrapped = callback
        else:
            from vibemix.audio.resample import resample_audio

            open_sr = device_sr
            open_block = max(1, round(block_size * (open_sr / sample_rate)))

            def resample_wrapper(outdata, frames, time_info, status):
                src_frames = max(1, round(frames * (sample_rate / open_sr)))
                src = np.zeros((src_frames, channels), dtype=np.float32)
                callback(src, src_frames, time_info, status)
                converted = np.zeros((frames, channels), dtype=np.float32)
                for channel in range(channels):
                    channel_data = resample_audio(
                        src[:, channel],
                        source_sr=sample_rate,
                        target_sr=open_sr,
                    )
                    if len(channel_data) < frames:
                        channel_data = np.pad(
                            channel_data,
                            (0, frames - len(channel_data)),
                        )
                    elif len(channel_data) > frames:
                        channel_data = channel_data[:frames]
                    converted[:, channel] = channel_data
                outdata[:] = converted

            wrapped = resample_wrapper
        stream = sd.OutputStream(
            device=device_index,
            samplerate=open_sr,
            channels=channels,
            dtype="float32",
            blocksize=open_block,
            latency="low",
            callback=wrapped,
        )
        if int(stream.samplerate) != open_sr:
            negotiated = int(stream.samplerate)
            stream.close()
            raise SampleRateMismatchError(
                f"PortAudio negotiated {negotiated}Hz vs requested {open_sr}Hz on "
                f"passthrough output device {device_index!r}."
            )
        stream.start()
        return _SoundDeviceStreamHandle(stream)

    def open_voice_output(
        self,
        device_index: int,
        *,
        sample_rate: int,
        block_size: int,
        callback: AudioCallback,
    ) -> AudioStream:
        """Open AI voice output (sd.RawOutputStream @ int16 mono — to headphones).

        2026-05-18 — Aggregate devices (e.g. AI Capture sitting on top of
        BlackHole) often refuse rates below 44.1 kHz, so a 24 kHz Gemini
        TTS stream can't open the device at its requested rate. When the
        device's native rate is an integer multiple of the requested
        rate, open the stream at the device rate and wrap the source
        callback so it sees the source rate (it pulls source-rate bytes
        from PlaybackQueue) while the OS sees device-rate audio (we
        upsample by integer N via ``np.repeat`` — sample-and-hold, no
        general resampler needed, fine for monophonic voice).
        """
        import numpy as np

        info = sd.query_devices(device_index)
        device_sr = int(info["default_samplerate"])
        if device_sr == sample_rate:
            open_sr = sample_rate
            wrapped = callback
        elif device_sr % sample_rate == 0:
            ratio = device_sr // sample_rate
            open_sr = device_sr

            # The source callback (in __main__.py:_voice_callback_factory) is
            # ``outdata[:] = playback.pull(frames * 2)``. It assumes frame-
            # count matches its native source rate. So we pull
            # ``frames // ratio`` source frames worth of bytes, decode int16
            # mono, np.repeat by ratio, and write to outdata at device rate.
            def upsampling_wrapper(outdata, frames, time_info, status):
                src_frames = frames // ratio
                src_bytes = bytearray(src_frames * 2)  # mono int16

                class _SrcView:
                    def __setitem__(self, _key, val):
                        # callback signature: outdata[:] = bytes
                        # We capture into src_bytes.
                        n = len(val)
                        src_bytes[:n] = val
                        # Zero-fill if source produced less than requested.
                        if n < src_frames * 2:
                            for i in range(n, src_frames * 2):
                                src_bytes[i] = 0

                callback(_SrcView(), src_frames, time_info, status)
                src_arr = np.frombuffer(src_bytes, dtype=np.int16)
                up = np.repeat(src_arr, ratio)
                # outdata is a buffer of total bytes = frames * 2 (mono int16)
                outdata[:] = up.tobytes()

            wrapped = upsampling_wrapper
        else:
            # Non-integer ratio (e.g. 44100/24000) — resample so the user
            # isn't forced to flip Audio MIDI Setup.
            from math import gcd

            from vibemix.audio.resample import resample_audio

            g = gcd(device_sr, sample_rate)
            up = device_sr // g
            down = sample_rate // g
            open_sr = device_sr

            def resample_wrapper(outdata, frames, time_info, status):
                src_frames = (frames * down) // up
                src_bytes = bytearray(src_frames * 2)

                class _SrcView:
                    def __setitem__(self, _key, val):
                        n = len(val)
                        src_bytes[:n] = val
                        if n < src_frames * 2:
                            for i in range(n, src_frames * 2):
                                src_bytes[i] = 0

                callback(_SrcView(), src_frames, time_info, status)
                src_arr = np.frombuffer(src_bytes, dtype=np.int16).astype(np.float32)
                out_f = resample_audio(src_arr, source_sr=sample_rate, target_sr=device_sr)
                out_i = np.clip(out_f, -32768, 32767).astype(np.int16)
                # Pad or trim to exact frame count expected by sd.
                if len(out_i) < frames:
                    out_i = np.pad(out_i, (0, frames - len(out_i)))
                elif len(out_i) > frames:
                    out_i = out_i[:frames]
                outdata[:] = out_i.tobytes()

            wrapped = resample_wrapper

        stream = sd.RawOutputStream(
            device=device_index,
            samplerate=open_sr,
            channels=1,
            dtype="int16",
            blocksize=int(block_size * (open_sr / sample_rate)),
            latency="low",
            callback=wrapped,
        )
        if int(stream.samplerate) != open_sr:
            negotiated = int(stream.samplerate)
            stream.close()
            raise SampleRateMismatchError(
                f"PortAudio negotiated {negotiated}Hz vs requested {open_sr}Hz on "
                f"voice output device {device_index!r}."
            )
        stream.start()
        return _SoundDeviceStreamHandle(stream)

    def open_mic_capture(
        self,
        device_index: int,
        *,
        sample_rate: int,
        block_size: int,
        callback: AudioCallback,
    ) -> AudioStream:
        """Open mic capture (sd.InputStream @ float32 mono).

        Wraps the v4:1895-1908 inline mic stream as a proper factory
        (PATTERNS.md §AntiPatterns-5 — every other stream has a factory, mic
        doesn't in v4). This is a macOS-only extension to ``AudioBackend`` —
        NOT in the Phase 1 Protocol. If Phase 3 reveals callers always need
        mic capture cross-platform, Phase 3 (or Phase 7 Windows port) should
        amend the Protocol via a separate commit.
        """
        info = sd.query_devices(device_index)
        device_sr = int(info["default_samplerate"])
        if device_sr != sample_rate:
            # 44.1k mic (common on USB/interface rigs) → open at native rate +
            # resample to the analysis rate (mono) instead of dropping talk-back.
            open_block = max(1, round(block_size * (device_sr / sample_rate)))
            wrapped = _make_input_resampler(
                callback, device_sr=device_sr, target_sr=sample_rate, channels=1
            )
            stream = sd.InputStream(
                device=device_index,
                samplerate=device_sr,
                channels=1,
                dtype="float32",
                blocksize=open_block,
                latency="low",
                callback=wrapped,
            )
            if int(stream.samplerate) != device_sr:
                negotiated = int(stream.samplerate)
                stream.close()
                raise SampleRateMismatchError(
                    f"PortAudio negotiated {negotiated}Hz vs requested {device_sr}Hz on "
                    f"mic device {device_index!r}."
                )
            stream.start()
            return _SoundDeviceStreamHandle(stream)

        # Mic already at the analysis rate — the proven path, unchanged.
        assert_device_sample_rate(device_index, sample_rate)
        stream = sd.InputStream(
            device=device_index,
            samplerate=sample_rate,
            channels=1,
            dtype="float32",
            blocksize=block_size,
            latency="low",
            callback=callback,
        )
        if int(stream.samplerate) != sample_rate:
            negotiated = int(stream.samplerate)
            stream.close()
            raise SampleRateMismatchError(
                f"PortAudio negotiated {negotiated}Hz vs requested {sample_rate}Hz on "
                f"mic device {device_index!r}."
            )
        stream.start()
        return _SoundDeviceStreamHandle(stream)
