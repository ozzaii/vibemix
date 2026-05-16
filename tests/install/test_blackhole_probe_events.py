# SPDX-License-Identifier: Apache-2.0
"""Phase 40 / Plan 40-06 / AUDIO-07 — BlackHole probe structured-event
emission coverage.

Pins the three event names (`audio.probe.detected`, `audio.probe.missing`,
`audio.probe.cta_fired`), the Pitfall 5 fresh-boot retry path, the
``retry_on_missing=False`` fast-path used by tests, the emit-failure
swallow contract (T-40-06-01), the ``emit_cta_fired`` payload shape,
and the byte-identical legacy probe-dict contract preserved from
Phase 33.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from vibemix.install import blackhole_probe
from vibemix.install.blackhole_probe import (
    BLACKHOLE_INSTALL_URL,
    emit_cta_fired,
    probe_blackhole,
)


def _patch_devices(monkeypatch: pytest.MonkeyPatch, devices: list[dict[str, Any]]) -> None:
    """Patch ``sounddevice.query_devices`` to return the given device list.

    Mirrors the helper in ``test_blackhole_probe.py`` so the AUDIO-07
    suite reuses the Phase 33 device-list mocking convention.
    """
    import sounddevice as sd

    def _fake_query(idx: int | None = None) -> Any:
        if idx is None:
            return devices
        return devices[idx] if 0 <= idx < len(devices) else {}

    monkeypatch.setattr(sd, "query_devices", _fake_query)


def test_emit_event_detected_when_blackhole_present(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_devices(
        monkeypatch,
        [{"name": "BlackHole 2ch", "max_input_channels": 2}],
    )
    mock = MagicMock()
    result = probe_blackhole(emit_event=mock, retry_on_missing=False)

    assert result == {"installed": True, "device_name": "BlackHole 2ch"}
    mock.assert_called_once_with(
        "audio.probe.detected",
        {"device_name": "BlackHole 2ch"},
    )


def test_emit_event_missing_when_blackhole_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_devices(
        monkeypatch,
        [{"name": "Built-in Microphone", "max_input_channels": 1}],
    )
    mock = MagicMock()
    result = probe_blackhole(emit_event=mock, retry_on_missing=False)

    assert result == {"installed": False, "device_name": None}
    mock.assert_called_once_with(
        "audio.probe.missing",
        {"device_name": None},
    )


def test_pitfall_5_retry_succeeds_on_second_try(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pitfall 5 — fresh-boot CoreAudio race. First probe misses,
    second probe (post-1.5s sleep) sees BlackHole. Only ONE event
    emitted: ``audio.probe.detected``."""
    sleep_mock = MagicMock()
    monkeypatch.setattr(blackhole_probe.time, "sleep", sleep_mock)

    call_count = {"n": 0}

    def _flaky_probe_once() -> dict:
        call_count["n"] += 1
        if call_count["n"] == 1:
            return {"installed": False, "device_name": None}
        return {"installed": True, "device_name": "BlackHole 2ch"}

    monkeypatch.setattr(blackhole_probe, "_probe_once", _flaky_probe_once)

    emit_mock = MagicMock()
    result = probe_blackhole(emit_event=emit_mock, retry_on_missing=True)

    assert result == {"installed": True, "device_name": "BlackHole 2ch"}
    sleep_mock.assert_called_once_with(1.5)
    emit_mock.assert_called_once_with(
        "audio.probe.detected",
        {"device_name": "BlackHole 2ch"},
    )
    assert call_count["n"] == 2


def test_pitfall_5_retry_still_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Both probes return missing — the genuinely-not-installed path.
    Single ``audio.probe.missing`` event after the retry sleep."""
    sleep_mock = MagicMock()
    monkeypatch.setattr(blackhole_probe.time, "sleep", sleep_mock)

    call_count = {"n": 0}

    def _always_missing() -> dict:
        call_count["n"] += 1
        return {"installed": False, "device_name": None}

    monkeypatch.setattr(blackhole_probe, "_probe_once", _always_missing)

    emit_mock = MagicMock()
    result = probe_blackhole(emit_event=emit_mock, retry_on_missing=True)

    assert result == {"installed": False, "device_name": None}
    sleep_mock.assert_called_once_with(1.5)
    emit_mock.assert_called_once_with(
        "audio.probe.missing",
        {"device_name": None},
    )
    assert call_count["n"] == 2


def test_retry_disabled_skips_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    """``retry_on_missing=False`` MUST NOT sleep. Used by tests to
    keep runtime fast and by callers who handle retry themselves."""
    sleep_mock = MagicMock()
    monkeypatch.setattr(blackhole_probe.time, "sleep", sleep_mock)

    _patch_devices(monkeypatch, [{"name": "AirPods Pro"}])

    emit_mock = MagicMock()
    result = probe_blackhole(emit_event=emit_mock, retry_on_missing=False)

    assert result == {"installed": False, "device_name": None}
    sleep_mock.assert_not_called()
    emit_mock.assert_called_once_with(
        "audio.probe.missing",
        {"device_name": None},
    )


def test_emit_cta_fired_emits_correct_event() -> None:
    mock = MagicMock()
    emit_cta_fired(mock)
    mock.assert_called_once_with(
        "audio.probe.cta_fired",
        {
            "cta": "blackhole_install_link_opened",
            "url": BLACKHOLE_INSTALL_URL,
        },
    )


def test_emit_cta_fired_custom_cta_tag() -> None:
    """Future surfaces (e.g. in-app "retry probe" button) can pass
    their own CTA identifier — the helper threads it through verbatim."""
    mock = MagicMock()
    emit_cta_fired(mock, cta="blackhole_retry_button")
    mock.assert_called_once_with(
        "audio.probe.cta_fired",
        {
            "cta": "blackhole_retry_button",
            "url": BLACKHOLE_INSTALL_URL,
        },
    )


def test_emit_failure_does_not_crash_probe(monkeypatch: pytest.MonkeyPatch) -> None:
    """T-40-06-01 mitigation — emit_event raising must NOT bubble up.
    The probe's contract is "return a dict"; telemetry is best-effort."""
    _patch_devices(
        monkeypatch,
        [{"name": "BlackHole 2ch", "max_input_channels": 2}],
    )

    def _exploding_emit(_name: str, _payload: dict) -> None:
        raise ZeroDivisionError("disk full")

    # Should NOT raise.
    result = probe_blackhole(emit_event=_exploding_emit, retry_on_missing=False)
    assert result == {"installed": True, "device_name": "BlackHole 2ch"}


def test_emit_failure_in_cta_fired_does_not_crash(monkeypatch: pytest.MonkeyPatch) -> None:
    """Same swallow contract for ``emit_cta_fired`` — the wizard must
    never see an exception bubble out of the CTA-fired notification."""

    def _exploding_emit(_name: str, _payload: dict) -> None:
        raise RuntimeError("broken IPC channel")

    # Should NOT raise.
    emit_cta_fired(_exploding_emit)


def test_no_emit_event_path_byte_identical_to_legacy(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without ``emit_event``, the probe still returns the Phase 33
    contract dict shape. Pins backward-compat with the
    ``tests/install/test_blackhole_probe.py`` fixtures."""
    _patch_devices(
        monkeypatch,
        [{"name": "BlackHole 2ch", "max_input_channels": 2}],
    )
    result = probe_blackhole(retry_on_missing=False)
    # Exactly two keys; types match the TypedDict.
    assert set(result.keys()) == {"installed", "device_name"}
    assert isinstance(result["installed"], bool)
    assert result == {"installed": True, "device_name": "BlackHole 2ch"}


def test_no_emit_event_path_missing_case(monkeypatch: pytest.MonkeyPatch) -> None:
    """Same as above but for the missing path — no emit_event, no
    crash, same legacy dict shape."""
    _patch_devices(monkeypatch, [{"name": "AirPods Pro"}])
    result = probe_blackhole(retry_on_missing=False)
    assert result == {"installed": False, "device_name": None}


def test_retry_only_runs_once(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pitfall 5 mitigation is a SINGLE retry — not unbounded polling.
    Repeated misses are real misses; we don't burn 10s waiting for
    CoreAudio to wake up."""
    sleep_mock = MagicMock()
    monkeypatch.setattr(blackhole_probe.time, "sleep", sleep_mock)

    call_count = {"n": 0}

    def _always_missing() -> dict:
        call_count["n"] += 1
        return {"installed": False, "device_name": None}

    monkeypatch.setattr(blackhole_probe, "_probe_once", _always_missing)
    emit_mock = MagicMock()
    probe_blackhole(emit_event=emit_mock, retry_on_missing=True)

    # Exactly 2 probe calls (initial + 1 retry) — never more.
    assert call_count["n"] == 2
    assert sleep_mock.call_count == 1
