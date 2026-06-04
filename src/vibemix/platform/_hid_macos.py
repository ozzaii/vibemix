# SPDX-License-Identifier: Apache-2.0
"""macOS HID bridge for Native Instruments Traktor Kontrol S2 MK3.

Clean-room boundary: this module uses public USB HID descriptor facts and
byte-offset tables for the S2 MK3 (VID:PID 17cc:1710). It does not copy Mixxx's
GPL JavaScript mapping or LED state machines. The output is the existing
``MidiEvent`` shape so the live engine stays transport-blind.
"""

from __future__ import annotations

import importlib
import threading
import time
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from vibemix.midi.state import MidiEvent

S2_MK3_VENDOR_ID = 0x17CC
S2_MK3_PRODUCT_ID = 0x1710
S2_MK3_DFU_PRODUCT_ID = 0x1712

REPORT_BUTTONS_AND_JOGS = 0x01
REPORT_SCALARS = 0x02
REPORT_LEDS = 0x80
LED_REPORT_PAYLOAD_BYTES = 61
LED_FULL = 0x7E

REPORT_01_MIN_BYTES = 0x14
REPORT_02_SCALAR_COUNT = 19
REPORT_02_MIN_BYTES = 1 + (REPORT_02_SCALAR_COUNT * 2)


@dataclass(frozen=True, slots=True)
class _ButtonBit:
    offset: int
    mask: int
    kind: str
    deck: str | None


# Public S2 MK3 HID facts. Offsets are packet offsets including the report ID
# byte at index 0. We start with the load-bearing transport/touch bits that
# already have canonical MidiEvent kinds in vibemix.
BUTTON_BITS: tuple[_ButtonBit, ...] = (
    _ButtonBit(0x02, 0x01, "sync", "A"),
    _ButtonBit(0x02, 0x04, "cue", "A"),
    _ButtonBit(0x02, 0x08, "play", "A"),
    _ButtonBit(0x05, 0x04, "sync", "B"),
    _ButtonBit(0x05, 0x10, "cue", "B"),
    _ButtonBit(0x05, 0x20, "play", "B"),
    _ButtonBit(0x08, 0x40, "jog_touch", "A"),
    _ButtonBit(0x08, 0x80, "jog_touch", "B"),
)

JOG_WHEEL_OFFSETS = {"A": 0x0C, "B": 0x10}

# Report 0x02's HID descriptor exposes 19 12-bit scalers, but the packet's
# field-to-physical-control map is not manufacturer-documented in this module's
# source set. Emit generic CC-shaped fields until a verified table lands.
SCALAR_FIELDS = tuple(f"hid_scalar_{index:02d}" for index in range(REPORT_02_SCALAR_COUNT))


def _load_hid_module() -> Any:
    try:
        return importlib.import_module("hid")
    except ImportError as exc:  # pragma: no cover - host dependency dependent
        raise RuntimeError(
            "hid package is not installed; S2 MK3 HID support requires python-hid "
            "plus native hidapi (for example: brew install hidapi)"
        ) from exc


def _new_hid_device(hid_module: Any) -> Any:
    factory = getattr(hid_module, "device", None)
    if callable(factory):
        return factory()
    cls = getattr(hid_module, "Device", None)
    if callable(cls):
        return cls()
    raise RuntimeError("hid module exposes neither device() nor Device()")


def _clamp_unit(value: float) -> float:
    if value < -1.0:
        return -1.0
    if value > 1.0:
        return 1.0
    return value


def _as_bytes(report: bytes | bytearray | Iterable[int]) -> bytes:
    if isinstance(report, bytes):
        return report
    if isinstance(report, bytearray):
        return bytes(report)
    return bytes(int(v) & 0xFF for v in report)


def _u32_le(report: bytes, offset: int) -> int:
    return int.from_bytes(report[offset : offset + 4], "little", signed=False)


def _u16_le(report: bytes, offset: int) -> int:
    return int.from_bytes(report[offset : offset + 2], "little", signed=False)


class S2Mk3Decoder:
    """Decode S2 MK3 HID input reports into ``MidiEvent`` records.

    Startup packets establish baseline by default. Set ``emit_initial=True`` in
    tests or probes when you deliberately want the first pressed-bit snapshot to
    emit events.
    """

    def __init__(
        self,
        *,
        clock: Callable[[], float] = time.time,
        emit_initial: bool = False,
    ) -> None:
        self._clock = clock
        self._emit_initial = bool(emit_initial)
        self._next_event_id = 0
        self._button_state: dict[tuple[int, int], bool] = {}
        self._jog_state: dict[str, int] = {}
        self._scalar_state: dict[str, int] = {}

    def decode_report(self, report: bytes | bytearray | Iterable[int]) -> list[MidiEvent]:
        data = _as_bytes(report)
        if not data:
            return []
        report_id = data[0]
        if report_id == REPORT_BUTTONS_AND_JOGS:
            return self._decode_buttons_and_jogs(data)
        if report_id == REPORT_SCALARS:
            return self._decode_scalars(data)
        if report_id == REPORT_LEDS:
            # Host->device echo/readback is not controller input.
            return []
        return []

    def _event(
        self,
        *,
        kind: str,
        deck: str | None,
        field: str | None,
        value_raw: int,
        magnitude: float | None,
    ) -> MidiEvent:
        ev = MidiEvent(
            id=self._next_event_id,
            at=self._clock(),
            kind=kind,
            deck=deck,
            field=field,
            value_raw=max(0, min(127, int(value_raw))),
            magnitude=magnitude,
        )
        self._next_event_id += 1
        return ev

    def _decode_buttons_and_jogs(self, report: bytes) -> list[MidiEvent]:
        if len(report) < REPORT_01_MIN_BYTES:
            return []

        events: list[MidiEvent] = []
        for bit in BUTTON_BITS:
            pressed = bool(report[bit.offset] & bit.mask)
            key = (bit.offset, bit.mask)
            previous = self._button_state.get(key)
            self._button_state[key] = pressed
            if previous is None:
                if not self._emit_initial or not pressed:
                    continue
                previous = False
            if previous == pressed:
                continue
            events.append(
                self._event(
                    kind=bit.kind,
                    deck=bit.deck,
                    field=None,
                    value_raw=127 if pressed else 0,
                    magnitude=None,
                )
            )

        for deck, offset in JOG_WHEEL_OFFSETS.items():
            value = _u32_le(report, offset)
            previous = self._jog_state.get(deck)
            self._jog_state[deck] = value
            if previous is None:
                continue
            delta = int(value) - int(previous)
            if delta == 0:
                continue
            events.append(
                self._event(
                    kind="cc",
                    deck=deck,
                    field="jog",
                    value_raw=65 if delta > 0 else 63,
                    magnitude=1.0 if delta > 0 else -1.0,
                )
            )
        return events

    def _decode_scalars(self, report: bytes) -> list[MidiEvent]:
        if len(report) < REPORT_02_MIN_BYTES:
            return []

        events: list[MidiEvent] = []
        for index, field in enumerate(SCALAR_FIELDS):
            offset = 1 + (index * 2)
            raw12 = max(0, min(4095, _u16_le(report, offset)))
            value_raw = round((raw12 / 4095.0) * 127.0)
            previous = self._scalar_state.get(field)
            self._scalar_state[field] = value_raw
            if previous is None:
                if not self._emit_initial:
                    continue
                previous = value_raw
            if previous == value_raw:
                continue
            events.append(
                self._event(
                    kind="cc",
                    deck=None,
                    field=field,
                    value_raw=value_raw,
                    magnitude=_clamp_unit((value_raw - previous) / 127.0),
                )
            )
        return events


def list_s2_mk3_devices(hid_module: Any | None = None) -> list[Mapping[str, Any]]:
    """List operational S2 MK3 HID devices.

    Deliberately enumerates only PID 0x1710. PID 0x1712 is the DFU/bootloader
    PID and must never be opened by the live bridge.
    """

    module = hid_module or _load_hid_module()
    enumerate_fn = getattr(module, "enumerate", None)
    if not callable(enumerate_fn):
        return []
    return list(enumerate_fn(S2_MK3_VENDOR_ID, S2_MK3_PRODUCT_ID))


def build_led_report(values: Mapping[int, int] | None = None) -> bytes:
    """Build a report-0x80 LED packet (report ID + 61 intensity bytes)."""
    payload = bytearray(1 + LED_REPORT_PAYLOAD_BYTES)
    payload[0] = REPORT_LEDS
    for index, value in (values or {}).items():
        if index < 0 or index >= LED_REPORT_PAYLOAD_BYTES:
            raise ValueError(f"LED index {index} out of range 0..{LED_REPORT_PAYLOAD_BYTES - 1}")
        if value < 0 or value > LED_FULL:
            raise ValueError(f"LED value {value} out of range 0..{LED_FULL}")
        payload[1 + index] = int(value)
    return bytes(payload)


class S2Mk3HIDMacOS:
    """Thin ``hid`` device wrapper for the S2 MK3 operational PID."""

    def __init__(
        self,
        device: Any,
        *,
        decoder: S2Mk3Decoder | None = None,
    ) -> None:
        self._device = device
        self.decoder = decoder or S2Mk3Decoder()

    @classmethod
    def open(
        cls,
        *,
        hid_module: Any | None = None,
        nonblocking: bool = True,
        decoder: S2Mk3Decoder | None = None,
    ) -> S2Mk3HIDMacOS:
        module = hid_module or _load_hid_module()
        device = _new_hid_device(module)
        device.open(S2_MK3_VENDOR_ID, S2_MK3_PRODUCT_ID)
        set_nonblocking = getattr(device, "set_nonblocking", None)
        if callable(set_nonblocking):
            set_nonblocking(1 if nonblocking else 0)
        return cls(device, decoder=decoder)

    def close(self) -> None:
        close = getattr(self._device, "close", None)
        if callable(close):
            close()

    def read_events(self, *, size: int = 64, timeout_ms: int | None = None) -> list[MidiEvent]:
        if timeout_ms is None:
            report = self._device.read(size)
        else:
            report = self._device.read(size, timeout_ms)
        return self.decoder.decode_report(report)

    def write_leds(self, values: Mapping[int, int] | None = None) -> int:
        return int(self._device.write(build_led_report(values)))

    def __enter__(self) -> S2Mk3HIDMacOS:
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        self.close()
        return False


def start_s2_mk3_listener(
    on_event: Callable[[MidiEvent], None],
    stop_event: threading.Event,
    *,
    hid_module: Any | None = None,
    poll_seconds: float = 0.005,
) -> threading.Thread:
    """Start a daemon HID read loop and call ``on_event`` for decoded events."""

    def _run() -> None:
        try:
            with S2Mk3HIDMacOS.open(hid_module=hid_module) as bridge:
                while not stop_event.is_set():
                    for event in bridge.read_events():
                        on_event(event)
                    time.sleep(poll_seconds)
        except Exception:
            # Match MIDI listener posture: device failures are not allowed to
            # crash the co-host process. Integration can add stderr diagnostics
            # when the bridge is wired into boot.
            return

    thread = threading.Thread(target=_run, name="s2-mk3-hid-listener", daemon=True)
    thread.start()
    return thread
