# SPDX-License-Identifier: Apache-2.0
"""DEV-04 audio backend matrix.

Mocks the two production audio device-enumeration surfaces vibemix relies on
across macOS and Windows, then asserts the existing pre-open guard +
fallback behavior holds without modifying any production source:

  - macOS: ``sounddevice.query_devices()`` via ``monkeypatch.setattr`` —
    BlackHole 2ch present, BlackHole 16ch present, BlackHole absent (graceful
    fallback). Pattern lifted verbatim from
    ``tests/install/test_blackhole_probe.py::_patch_devices`` (lines 23-31).

  - Windows: ``pyaudiowpatch.PyAudio()`` via
    ``monkeypatch.setitem(sys.modules, "pyaudiowpatch", MagicMock())`` —
    WASAPI loopback found at 48kHz, no-loopback-driver fallback raising
    ``OSError`` from the production lazy import path. Pattern lifted from
    ``tests/test_audio_windows.py::_make_fake_pa``.

The two production functions under exercise (``probe_blackhole`` from
``vibemix.install.blackhole_probe`` + ``assert_wasapi_loopback_rate`` from
``vibemix.platform._audio_windows``) are READ-ONLY — this test imports them
and drives them through their mocked dependency surfaces; their source
files are unchanged after this commit (acceptance gate enforced via
``git diff --stat`` on the four sacred audio paths).

Live capture parity (real BlackHole + real WASAPI loopback on real
hardware) rides KAAN-ACTION §V7-LIVE-08 (macOS) + §V7-LIVE-09 (Windows)
in Wave 4 (P05).
"""

from __future__ import annotations

import sys
from typing import Any
from unittest.mock import MagicMock

import pytest


def _patch_devices(monkeypatch: pytest.MonkeyPatch, devices: list[dict[str, Any]]) -> None:
    """Monkeypatch ``sounddevice.query_devices`` to return ``devices`` (or
    the single device at the requested index). Lifted verbatim from
    ``tests/install/test_blackhole_probe.py:23-31``.
    """
    import sounddevice as sd

    def _fake_query(idx: int | None = None) -> Any:
        if idx is None:
            return devices
        return devices[idx] if 0 <= idx < len(devices) else {}

    monkeypatch.setattr(sd, "query_devices", _fake_query)


def _inject_fake_pyaudiowpatch(
    monkeypatch: pytest.MonkeyPatch,
    *,
    loopback_info: dict | None = None,
    raises_oserror: bool = False,
) -> MagicMock:
    """Inject a ``MagicMock`` pyaudiowpatch module into ``sys.modules`` BEFORE
    the lazy import inside ``vibemix.platform._audio_windows`` fires.

    Two modes:
      - ``raises_oserror=False`` (default) — ``get_default_wasapi_loopback_device()``
        returns ``loopback_info``.
      - ``raises_oserror=True`` — same method raises
        ``OSError("no loopback driver")``, simulating the Windows-with-no-WASAPI-
        loopback edge (assumption A6 in 68-RESEARCH: OSError IS the fallback
        surface; the production guard propagates).

    Uses ``monkeypatch.setitem`` for fixture-scoped cleanup — never bare
    sys.modules assignment (68-RESEARCH Pitfall #4 — cross-test
    contamination).

    Also evicts ``vibemix.platform._audio_windows`` from ``sys.modules`` so the
    next import re-binds ``import pyaudiowpatch`` against the fake module.
    """
    fake_pa_mod = MagicMock()
    fake_pa_mod.paInt16 = 8
    fake_pa_mod.paFloat32 = 1

    fake_instance = MagicMock()
    if raises_oserror:
        fake_instance.get_default_wasapi_loopback_device.side_effect = OSError(
            "no loopback driver"
        )
    else:
        fake_instance.get_default_wasapi_loopback_device.return_value = loopback_info
    fake_instance.terminate = MagicMock()
    fake_pa_mod.PyAudio = MagicMock(return_value=fake_instance)

    # Drop stale module cache so the next ``from vibemix.platform._audio_windows
    # import assert_wasapi_loopback_rate`` re-binds the lazy ``import
    # pyaudiowpatch`` against the fake.
    sys.modules.pop("vibemix.platform._audio_windows", None)
    monkeypatch.setitem(sys.modules, "pyaudiowpatch", fake_pa_mod)
    return fake_pa_mod


# ---------------------------------------------------------------------------
# macOS BlackHole CoreAudio surface (mocked via sounddevice.query_devices)
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_audio_backend_macos_blackhole_2ch_present(monkeypatch: pytest.MonkeyPatch) -> None:
    """BlackHole 2ch enumerated by CoreAudio → probe reports installed=True
    with the matching device_name. Default 48kHz routing path is the
    downstream consumer; the probe is the gate before the wizard opens an
    input stream against the device."""
    _patch_devices(
        monkeypatch,
        [
            {"name": "BlackHole 2ch", "max_output_channels": 2},
            {"name": "AirPods Pro", "max_output_channels": 2},
        ],
    )
    from vibemix.install import blackhole_probe

    result = blackhole_probe.probe_blackhole(retry_on_missing=False)
    assert result == {"installed": True, "device_name": "BlackHole 2ch"}


@pytest.mark.integration
def test_audio_backend_macos_blackhole_16ch_present(monkeypatch: pytest.MonkeyPatch) -> None:
    """BlackHole 16ch variant enumerated by CoreAudio → probe reports
    installed=True. vibemix accepts any BlackHole variant (2ch/16ch/64ch)
    as functionally equivalent for the audio-routing surface."""
    _patch_devices(
        monkeypatch,
        [{"name": "BlackHole 16ch", "max_output_channels": 16}],
    )
    from vibemix.install import blackhole_probe

    result = blackhole_probe.probe_blackhole(retry_on_missing=False)
    assert result["installed"] is True
    assert result["device_name"] == "BlackHole 16ch"


@pytest.mark.integration
def test_audio_backend_macos_no_blackhole_graceful(monkeypatch: pytest.MonkeyPatch) -> None:
    """No BlackHole device enumerated → probe gracefully returns
    installed=False without raising. The wizard branches on this False to
    surface the install CTA — a crash here would block the entire
    first-run install flow."""
    _patch_devices(
        monkeypatch,
        [
            {"name": "Built-in Output", "max_output_channels": 2},
            {"name": "AirPods Pro", "max_output_channels": 2},
        ],
    )
    from vibemix.install import blackhole_probe

    result = blackhole_probe.probe_blackhole(retry_on_missing=False)
    assert result == {"installed": False, "device_name": None}


# ---------------------------------------------------------------------------
# Windows WASAPI loopback surface (mocked via sys.modules pyaudiowpatch)
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_audio_backend_windows_wasapi_loopback_found(monkeypatch: pytest.MonkeyPatch) -> None:
    """WASAPI loopback enumerated at 48kHz → ``assert_wasapi_loopback_rate``
    returns ``(index, name)`` from ``get_default_wasapi_loopback_device``
    without raising. This is the Windows-side equivalent of the macOS
    BlackHole 2ch found path — both are pre-open guards that fire before
    the audio backend opens a real input stream."""
    _inject_fake_pyaudiowpatch(
        monkeypatch,
        loopback_info={
            "name": "Speakers (Realtek(R) Audio) [Loopback]",
            "index": 7,
            "defaultSampleRate": 48000.0,
            "maxInputChannels": 2,
        },
    )
    from vibemix.platform._audio_windows import assert_wasapi_loopback_rate

    index, name = assert_wasapi_loopback_rate(expected=48000)
    assert index == 7
    assert "Loopback" in name


@pytest.mark.integration
def test_audio_backend_windows_no_loopback_driver_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No WASAPI loopback driver available → the production lazy import path
    propagates ``OSError`` cleanly (with ``terminate()`` still called on
    the temporary PyAudio instance via the ``finally`` block in
    ``assert_wasapi_loopback_rate``).

    Per 68-RESEARCH Assumption A6: OSError propagation IS the fallback
    surface. The caller (open_capture / Calibration Wizard) catches +
    surfaces an actionable error; the guard's job is only to not crash and
    not leak PyAudio instances when the loopback device is unavailable.
    """
    fake_pa_mod = _inject_fake_pyaudiowpatch(monkeypatch, raises_oserror=True)
    from vibemix.platform._audio_windows import assert_wasapi_loopback_rate

    with pytest.raises(OSError, match="no loopback"):
        assert_wasapi_loopback_rate(expected=48000)

    # The temporary PyAudio instance is still terminated on the raise path —
    # the ``finally`` block in assert_wasapi_loopback_rate guarantees no leak
    # even when the loopback-device query bombs.
    fake_instance = fake_pa_mod.PyAudio.return_value
    fake_instance.terminate.assert_called_once()
