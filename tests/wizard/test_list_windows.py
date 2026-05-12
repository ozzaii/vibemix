# SPDX-License-Identifier: Apache-2.0
"""ipc.calibration.list_windows handler coverage (Warning #4 — WS-path).

The window-picker enumeration is the load-bearing Warning #4 deviation:
window enumeration happens in Python (Quartz / EnumWindows) and is served
back to the webview over the WS bus — NOT via a Rust Tauri command. These
tests pin both the contract (schema-valid window_list emit on every call)
and the auto-select behavior (first DJ-app hint match wins).

Privacy gate (T-11-W4-06): titles are returned over the WS, NEVER logged.
This test suite doesn't assert on logging because the wizard's logger is
INFO-level and titles are explicitly omitted from log lines — the audit
is at code-review time (grep for log.*/print(*) calls that reference
WindowInfo.title in src/vibemix/runtime/wizard.py).
"""

from __future__ import annotations

import asyncio

from tests.wizard.conftest import FakeBus
from vibemix.platform._windows_macos import WindowInfoNative
from vibemix.runtime.wizard import WizardLoop


def _drive(bus: FakeBus) -> dict:
    asyncio.run(
        bus.handlers["ipc.calibration.list_windows"](
            {
                "type": "ipc.calibration.list_windows",
                "ts": "2026-05-12T08:00:00+00:00",
                "payload": {},
            }
        )
    )
    return bus.emitted_by_type("ipc.calibration.window_list")[0]


def test_empty_enumeration_emits_empty_list(
    fake_bus: FakeBus, mock_platform_windows: list
) -> None:
    """No windows → emits window_list with empty windows array."""
    loop = WizardLoop(fake_bus)
    loop.register_handlers()
    payload = _drive(fake_bus)["payload"]
    assert payload["windows"] == []


def test_djay_window_dj_app_hint_resolved(
    fake_bus: FakeBus, mock_platform_windows: list
) -> None:
    """djay Pro window matches the djay hint table entry."""
    mock_platform_windows.append(
        WindowInfoNative(
            id="123",
            app_name="djay Pro AI",
            title="Deck A · Deck B",
            dj_app_hint="djay",
        )
    )
    loop = WizardLoop(fake_bus)
    loop.register_handlers()
    payload = _drive(fake_bus)["payload"]
    assert len(payload["windows"]) == 1
    w = payload["windows"][0]
    assert w["id"] == "123"
    assert w["app_name"] == "djay Pro AI"
    assert w["dj_app_hint"] == "djay"


def test_non_dj_app_window_dj_app_hint_null(
    fake_bus: FakeBus, mock_platform_windows: list
) -> None:
    """Non-DJ window → dj_app_hint is null (schema allows it)."""
    mock_platform_windows.append(
        WindowInfoNative(
            id="999",
            app_name="Chrome",
            title="GitHub — anthropics/claude-code",
            dj_app_hint=None,
        )
    )
    loop = WizardLoop(fake_bus)
    loop.register_handlers()
    payload = _drive(fake_bus)["payload"]
    assert len(payload["windows"]) == 1
    assert payload["windows"][0]["dj_app_hint"] is None


def test_multiple_windows_all_emitted(
    fake_bus: FakeBus, mock_platform_windows: list
) -> None:
    """All native rows surface in the wire payload (no filtering at handler)."""
    mock_platform_windows.extend(
        [
            WindowInfoNative(id="1", app_name="djay Pro AI", title="Main", dj_app_hint="djay"),
            WindowInfoNative(id="2", app_name="Chrome", title="GitHub", dj_app_hint=None),
            WindowInfoNative(id="3", app_name="Terminal", title="bash", dj_app_hint=None),
        ]
    )
    loop = WizardLoop(fake_bus)
    loop.register_handlers()
    payload = _drive(fake_bus)["payload"]
    assert len(payload["windows"]) == 3
    ids = [w["id"] for w in payload["windows"]]
    assert ids == ["1", "2", "3"]


def test_emit_validates_against_schema(
    fake_bus: FakeBus, mock_platform_windows: list
) -> None:
    """The FakeBus.emit calls validate_message internally — passing the test
    means the schema accepts the emitted payload shape. Catches regressions
    from messages.schema.json drift vs the WindowInfo dataclass.
    """
    mock_platform_windows.append(
        WindowInfoNative(id="42", app_name="App", title="Title", dj_app_hint="djay")
    )
    loop = WizardLoop(fake_bus)
    loop.register_handlers()
    msg = _drive(fake_bus)  # Would have raised on validation failure.
    assert msg["type"] == "ipc.calibration.window_list"


def test_platform_macos_dj_hint_match() -> None:
    """The macOS platform helper resolves djay strings correctly."""
    from vibemix.platform._windows_macos import _match_dj_app_hint

    assert _match_dj_app_hint("djay Pro AI", "Main") == "djay"
    assert _match_dj_app_hint("rekordbox", "Deck A") == "rekordbox"
    assert _match_dj_app_hint("Serato DJ Pro", "Main") == "serato"
    assert _match_dj_app_hint("Traktor Pro 3", "Main") == "traktor"
    assert _match_dj_app_hint("VirtualDJ 2024", "Main") == "virtualdj"
    assert _match_dj_app_hint("Chrome", "GitHub") is None


def test_platform_windows_dj_hint_match() -> None:
    """The Windows platform helper resolves DJ-app strings — same table sans djay."""
    from vibemix.platform._windows_windows import _match_dj_app_hint

    assert _match_dj_app_hint("rekordbox.exe", "Deck A") == "rekordbox"
    assert _match_dj_app_hint("Serato DJ Pro.exe", "Main") == "serato"
    assert _match_dj_app_hint("traktor.exe", "Main") == "traktor"
    assert _match_dj_app_hint("VirtualDJ.exe", "Main") == "virtualdj"
    # djay is macOS-only — no Windows entry.
    assert _match_dj_app_hint("djay.exe", "Main") is None
    assert _match_dj_app_hint("notepad.exe", "untitled") is None


def test_platform_selector_dispatches_by_sys_platform() -> None:
    """vibemix.platform.windows selector module aliases the right impl."""
    import sys

    from vibemix.platform import windows as platform_windows

    expected_module = (
        "vibemix.platform._windows_macos"
        if sys.platform == "darwin"
        else "vibemix.platform._windows_windows"
    )
    assert platform_windows.enumerate_windows.__module__ == expected_module
