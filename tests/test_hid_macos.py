# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from types import SimpleNamespace

import pytest

from vibemix.platform._hid_macos import (
    LED_FULL,
    S2_MK3_DFU_PRODUCT_ID,
    S2_MK3_PRODUCT_ID,
    S2_MK3_VENDOR_ID,
    S2Mk3Decoder,
    S2Mk3HIDMacOS,
    build_led_report,
    list_s2_mk3_devices,
)


class _FakeHidDevice:
    def __init__(self) -> None:
        self.open_calls: list[tuple[int, int]] = []
        self.nonblocking: list[int] = []
        self.writes: list[bytes] = []
        self.closed = False
        self.read_reports: list[list[int]] = []

    def open(self, vendor_id: int, product_id: int) -> None:
        self.open_calls.append((vendor_id, product_id))

    def set_nonblocking(self, value: int) -> None:
        self.nonblocking.append(value)

    def read(self, _size: int) -> list[int]:
        if not self.read_reports:
            return []
        return self.read_reports.pop(0)

    def write(self, payload: bytes) -> int:
        self.writes.append(payload)
        return len(payload)

    def close(self) -> None:
        self.closed = True


def _fake_hid_module(device: _FakeHidDevice):
    calls: list[tuple[int, int]] = []

    def _enumerate(vendor_id: int, product_id: int):
        calls.append((vendor_id, product_id))
        return [{"vendor_id": vendor_id, "product_id": product_id}]

    module = SimpleNamespace(device=lambda: device, enumerate=_enumerate)
    module.enumerate_calls = calls
    return module


def test_open_uses_operational_s2_pid_never_dfu_pid() -> None:
    device = _FakeHidDevice()
    bridge = S2Mk3HIDMacOS.open(hid_module=_fake_hid_module(device))

    assert isinstance(bridge, S2Mk3HIDMacOS)
    assert device.open_calls == [(S2_MK3_VENDOR_ID, S2_MK3_PRODUCT_ID)]
    assert all(pid != S2_MK3_DFU_PRODUCT_ID for _vid, pid in device.open_calls)
    assert device.nonblocking == [1]


def test_list_devices_enumerates_only_operational_pid() -> None:
    device = _FakeHidDevice()
    module = _fake_hid_module(device)

    rows = list_s2_mk3_devices(module)

    assert rows == [{"vendor_id": S2_MK3_VENDOR_ID, "product_id": S2_MK3_PRODUCT_ID}]
    assert module.enumerate_calls == [(S2_MK3_VENDOR_ID, S2_MK3_PRODUCT_ID)]
    assert all(pid != S2_MK3_DFU_PRODUCT_ID for _vid, pid in module.enumerate_calls)


def test_report_01_decodes_transport_buttons_and_jog_delta() -> None:
    decoder = S2Mk3Decoder(clock=lambda: 100.0, emit_initial=True)
    report = bytearray(0x14)
    report[0] = 0x01
    report[0x02] = 0x0D  # sync + cue + play, deck A
    report[0x08] = 0x40  # jog touch, deck A
    report[0x0C:0x10] = (100).to_bytes(4, "little")

    events = decoder.decode_report(report)

    assert [(ev.kind, ev.deck, ev.value_raw, ev.magnitude) for ev in events] == [
        ("sync", "A", 127, None),
        ("cue", "A", 127, None),
        ("play", "A", 127, None),
        ("jog_touch", "A", 127, None),
    ]
    assert [ev.id for ev in events] == [0, 1, 2, 3]

    report[0x0C:0x10] = (103).to_bytes(4, "little")
    jog_events = decoder.decode_report(report)

    assert [(ev.kind, ev.deck, ev.field, ev.value_raw, ev.magnitude) for ev in jog_events] == [
        ("cc", "A", "jog", 65, 1.0)
    ]
    assert jog_events[0].id == 4


def test_report_02_scalars_emit_generic_cc_events_after_baseline() -> None:
    decoder = S2Mk3Decoder(clock=lambda: 200.0)
    baseline = bytearray(39)
    baseline[0] = 0x02
    changed = bytearray(baseline)
    changed[1:3] = (4095).to_bytes(2, "little")

    assert decoder.decode_report(baseline) == []
    events = decoder.decode_report(changed)

    assert [(ev.kind, ev.deck, ev.field, ev.value_raw, ev.magnitude) for ev in events] == [
        ("cc", None, "hid_scalar_00", 127, 1.0)
    ]
    assert events[0].at == 200.0


def test_led_report_builds_report_80_payload_and_validates_ranges() -> None:
    report = build_led_report({0: 1, 60: LED_FULL})

    assert len(report) == 62
    assert report[0] == 0x80
    assert report[1] == 1
    assert report[-1] == LED_FULL

    with pytest.raises(ValueError, match="LED index"):
        build_led_report({61: 1})
    with pytest.raises(ValueError, match="LED value"):
        build_led_report({0: LED_FULL + 1})
