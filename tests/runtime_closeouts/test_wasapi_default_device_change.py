# SPDX-License-Identifier: Apache-2.0
"""Phase 27-07 — LATENCY-14 WASAPI device-change soft-restart tests.

Pitfall P70 critical: ``OnDefaultDeviceChanged`` callback MUST return < 1ms
(Microsoft hard requirement). Synchronous work in the callback → Windows
kills the audio service.

The `windows_only` marker (registered in pyproject.toml pytest config) skips
real-COM-path tests on macOS; the macOS stub + grep gate run cross-platform.
"""

from __future__ import annotations

import re
import sys
import threading
import time
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parents[2]
AUDIO_WINDOWS_PATH = PROJECT_ROOT / "src" / "vibemix" / "platform" / "_audio_windows.py"


# ----------------------------------------------------------------------
# Cross-platform tests (macOS + Windows) — exercise the stub + grep gate
# ----------------------------------------------------------------------


def test_macos_stub_imports_without_comtypes() -> None:
    """Importing _audio_windows on macOS does NOT pull in comtypes.

    Per CONTEXT decision LATENCY-14: macOS gets a graceful stub so the
    platform selector can `from ... import WindowsLoopbackAudio` cross-
    platform. Verify by asserting comtypes is absent from sys.modules
    after the import.
    """
    if sys.platform == "win32":
        pytest.skip("Windows runner — comtypes is expected to be present")
    # Ensure module isn't already loaded under a different test path.
    sys.modules.pop("vibemix.platform._audio_windows", None)
    sys.modules.pop("comtypes", None)
    from vibemix.platform._audio_windows import WindowsLoopbackAudio  # noqa: F401

    assert "comtypes" not in sys.modules, (
        "macOS import path leaked comtypes into sys.modules — "
        "Pitfall P69 violation: Windows-only dep imported on macOS"
    )


def test_macos_stub_start_stop_no_op() -> None:
    """On macOS, WindowsLoopbackAudio.start()/stop() are no-ops + don't crash."""
    if sys.platform == "win32":
        pytest.skip("Windows path tested elsewhere")
    from vibemix.platform._audio_windows import WindowsLoopbackAudio

    called = {"count": 0}

    def cb() -> None:
        called["count"] += 1

    audio = WindowsLoopbackAudio(on_restart=cb)
    audio.start()  # no-op on macOS
    assert audio.has_pending_restart() is False
    audio.stop()
    # on_restart should never have been invoked on the no-op path
    assert called["count"] == 0


def test_grep_gate_no_blocking_in_callback() -> None:
    """Pitfall P70 enforcement: OnDefaultDeviceChanged MUST be non-blocking.

    Microsoft docs: "methods of IMMNotificationClient must be nonblocking".
    Test asserts the function body contains ONLY signal + return — no
    logging.*, no print, no try/except, no time.sleep.
    """
    src = AUDIO_WINDOWS_PATH.read_text(encoding="utf-8")
    # Find the function body — match up to the next def or class at the same indentation.
    m = re.search(
        r"def OnDefaultDeviceChanged\([^)]*\):\n((?:        .*\n?)+)",
        src,
    )
    assert m, "OnDefaultDeviceChanged not found in _audio_windows.py"
    body = m.group(1)
    body_lines = [
        ln.strip()
        for ln in body.splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ]
    # The function body MUST contain exactly two non-comment statements:
    # `self._restart_event.set()` and `return 0`.
    assert any("self._restart_event.set()" in ln for ln in body_lines), (
        f"P70 violation: OnDefaultDeviceChanged must signal restart_event. "
        f"Body lines: {body_lines!r}"
    )
    assert any("return 0" in ln for ln in body_lines), (
        f"P70 violation: OnDefaultDeviceChanged must return S_OK (0). "
        f"Body lines: {body_lines!r}"
    )
    # Reject blocking patterns explicitly.
    blocking_patterns = ["logging.", "print(", "time.sleep", "try:", "except"]
    for ln in body_lines:
        for pat in blocking_patterns:
            assert pat not in ln, (
                f"P70 violation: blocking pattern {pat!r} in "
                f"OnDefaultDeviceChanged body line: {ln!r}"
            )


def test_grep_gate_other_callbacks_return_zero() -> None:
    """OnDeviceAdded/Removed/StateChanged/PropertyValueChanged return 0 immediately."""
    src = AUDIO_WINDOWS_PATH.read_text(encoding="utf-8")
    for method in [
        "OnDeviceAdded",
        "OnDeviceRemoved",
        "OnDeviceStateChanged",
        "OnPropertyValueChanged",
    ]:
        m = re.search(rf"def {method}\([^)]*\):\n((?:            .*\n?)+)", src)
        # Try alternative indentation (8-space)
        if not m:
            m = re.search(rf"def {method}\([^)]*\):\n((?:        .*\n?)+)", src)
        assert m, f"{method} not found in _audio_windows.py"
        body = m.group(1)
        assert "return 0" in body, (
            f"P70 violation: {method} must return 0 (S_OK). Body: {body!r}"
        )


# ----------------------------------------------------------------------
# Worker thread test (cross-platform — uses stub or real COM listener)
# ----------------------------------------------------------------------


def test_worker_thread_clears_event_after_restart(mocker) -> None:
    """The worker thread waits on _restart_event, fires on_restart, clears event."""
    from vibemix.platform._audio_windows import WindowsLoopbackAudio

    on_restart_called = threading.Event()

    def cb() -> None:
        on_restart_called.set()

    audio = WindowsLoopbackAudio(on_restart=cb)
    # Manually start the worker thread WITHOUT touching COM (so the test runs
    # cross-platform). We replicate the worker-spawn from start() inline.
    audio._stop_event.clear()
    audio._restart_thread = threading.Thread(
        target=audio._restart_worker, daemon=True, name="wasapi-restart-test"
    )
    audio._restart_thread.start()

    try:
        # Signal the event — the worker should fire on_restart within 1.5s.
        audio._restart_event.set()
        assert on_restart_called.wait(timeout=2.0), (
            "worker thread did not invoke on_restart callable"
        )
        # Event must be cleared after the worker handles it.
        # (poll briefly because the worker clears AFTER firing on_restart)
        for _ in range(20):
            if not audio._restart_event.is_set():
                break
            time.sleep(0.05)
        assert not audio._restart_event.is_set(), "_restart_event was not cleared"
    finally:
        audio._stop_event.set()
        if audio._restart_thread:
            audio._restart_thread.join(timeout=2.0)


# ----------------------------------------------------------------------
# Windows-only — real listener timing tests (skip on macOS)
# ----------------------------------------------------------------------


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-only COM path")
def test_callback_returns_within_1ms() -> None:
    """Pitfall P70 timing: OnDefaultDeviceChanged returns < 1ms.

    Construct the listener, invoke the callback directly (no real COM
    plumbing — we call the Python method on the COMObject subclass), and
    measure with time.perf_counter.
    """
    from vibemix.platform._audio_windows import _build_device_listener_class

    event = threading.Event()
    listener_cls = _build_device_listener_class(event)
    listener = listener_cls()

    start = time.perf_counter()
    rc = listener.OnDefaultDeviceChanged(0, 0, "test_device_id")
    elapsed = time.perf_counter() - start
    assert rc == 0, f"OnDefaultDeviceChanged must return S_OK (0); got {rc}"
    assert event.is_set(), "OnDefaultDeviceChanged did not signal restart_event"
    assert elapsed < 1e-3, (
        f"P70 violation: OnDefaultDeviceChanged took {elapsed * 1000:.3f}ms "
        f"(> 1ms threshold); Microsoft kills audio service"
    )


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-only COM path")
def test_other_callbacks_return_zero_immediately() -> None:
    """Other 4 IMMNotificationClient methods return 0 + don't signal restart."""
    from vibemix.platform._audio_windows import _build_device_listener_class

    event = threading.Event()
    listener_cls = _build_device_listener_class(event)
    listener = listener_cls()

    for rc in [
        listener.OnDeviceAdded("d"),
        listener.OnDeviceRemoved("d"),
        listener.OnDeviceStateChanged("d", 0),
        listener.OnPropertyValueChanged("d", "k"),
    ]:
        assert rc == 0
    # None of these should have signaled the restart event.
    assert not event.is_set()
