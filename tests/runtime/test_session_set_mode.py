# SPDX-License-Identifier: Apache-2.0
"""Phase 97 / ONBOARD-01 — ``ipc.session.set_mode`` handler contract.

Pins the sidecar half of the mode picker round-trip:

* Valid mode (one of cohost/learn/build/debrief) → persisted to
  ``ConfigStore.extra["session.mode"]`` + saved to disk + ``ipc.settings.state``
  emitted as the echo.
* Invalid mode (typo, wrong type, missing field) → ``ipc.error`` emitted with
  the rejecting reason; no persist + no settings.state.
* Handler registered on the bus under exactly ``ipc.session.set_mode``.

Uses the same FakeBus pattern as ``tests/runtime/test_session_loop.py`` —
no real ws server; the assertion is "the handler did the right thing
to the persisted state + the bus output queue."
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from vibemix.runtime import config_store as cs_mod
from vibemix.runtime.config_store import ConfigStore
from vibemix.runtime.session_loop import SessionLoop
from vibemix.runtime.settings import SettingsApplier
from vibemix.ui_bus.validator import validate_message


class FakeBus:
    """In-memory stand-in for ``vibemix.runtime.ws_bus.WizardBus``."""

    def __init__(self) -> None:
        self.handlers: dict[str, Callable[[dict], Awaitable[None]]] = {}
        self.emitted: list[dict] = []

    def register_handler(
        self, message_type: str, handler: Callable[[dict], Awaitable[None]]
    ) -> None:
        self.handlers[message_type] = handler

    async def start(self) -> None: ...
    async def stop(self) -> None: ...

    async def emit(self, msg: dict) -> None:
        validate_message(msg)
        self.emitted.append(json.loads(json.dumps(msg)))

    def emitted_by_type(self, msg_type: str) -> list[dict]:
        return [m for m in self.emitted if m.get("type") == msg_type]


@pytest.fixture
def fake_bus() -> FakeBus:
    return FakeBus()


@pytest.fixture(autouse=True)
def _redirect_config_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect ``save_config()`` writes into ``tmp_path/config.json`` so the
    handler's persist branch doesn't write to the user's real app-data dir."""
    target = tmp_path / "config.json"
    monkeypatch.setattr(cs_mod, "config_path", lambda: target)
    return target


@pytest.fixture
def session_loop(fake_bus: FakeBus, tmp_path: Path) -> SessionLoop:
    """Minimal SessionLoop wired with a FakeBus + tmp-path config store +
    a no-op SettingsApplier. The set_mode handler only touches
    config_store + bus, so the other refs stay None / MagicMock."""
    config_store = ConfigStore()  # default values
    settings_applier = SettingsApplier(
        config_store=config_store,
        cascade_agent=None,
        event_detector=None,
        genre_loader=None,
        audio_core=None,
        music_state=None,
    )
    loop = SessionLoop(
        bus=fake_bus,
        config_store=config_store,
        settings_applier=settings_applier,
        music_state=None,
        levels=MagicMock(),
        playback_queue=None,
        controller_state=None,
        screen_available=False,
    )
    loop.register_handlers()
    return loop


# ---------------------------------------------------------------------------
# Handler registration
# ---------------------------------------------------------------------------


def test_session_set_mode_handler_is_registered(
    fake_bus: FakeBus, session_loop: SessionLoop
) -> None:
    """The handler MUST be registered under the canonical envelope name."""
    assert "ipc.session.set_mode" in fake_bus.handlers


# ---------------------------------------------------------------------------
# Valid mode → persist + emit settings.state
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("mode", ["cohost", "learn", "build", "debrief"])
def test_valid_mode_persists_to_extra_and_emits_settings_state(
    mode: str,
    fake_bus: FakeBus,
    session_loop: SessionLoop,
    _redirect_config_path: Path,
) -> None:
    """Each of the 4 valid modes lands in ``ConfigStore.extra["session.mode"]``,
    triggers a ``save_config`` write, and emits an ``ipc.settings.state`` echo."""
    msg = {
        "type": "ipc.session.set_mode",
        "ts": "2026-05-28T11:00:00.000Z",
        "payload": {"mode": mode},
    }
    asyncio.run(session_loop._on_session_set_mode(msg))

    # Persisted to extra
    assert session_loop.config_store.extra.get("session.mode") == mode
    # Saved to disk (config_path was monkeypatched into tmp)
    assert _redirect_config_path.exists()
    disk = json.loads(_redirect_config_path.read_text(encoding="utf-8"))
    assert disk.get("session.mode") == mode
    # Settings.state echo
    states = fake_bus.emitted_by_type("ipc.settings.state")
    assert len(states) == 1, (
        f"expected exactly 1 settings.state echo for valid mode={mode}; got: "
        f"{[m['type'] for m in fake_bus.emitted]}"
    )
    assert states[0]["payload"]["session.mode"] == mode
    # No ipc.error emitted on the valid path
    errors = fake_bus.emitted_by_type("ipc.error")
    assert errors == [], f"valid mode={mode!r} unexpectedly emitted: {errors}"


# ---------------------------------------------------------------------------
# Invalid mode → ipc.error + NO persist
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_mode",
    [
        "live",  # plausible-looking typo
        "COHOST",  # case-sensitive
        "",  # empty
        None,  # null
        42,  # wrong type
        ["learn"],  # array
    ],
)
def test_invalid_mode_emits_ipc_error_and_does_not_persist(
    bad_mode: object,
    fake_bus: FakeBus,
    session_loop: SessionLoop,
) -> None:
    """Invalid modes MUST reject with ipc.error AND not write to extra."""
    msg = {
        "type": "ipc.session.set_mode",
        "ts": "2026-05-28T11:00:00.000Z",
        "payload": {"mode": bad_mode},
    }
    asyncio.run(session_loop._on_session_set_mode(msg))

    # No persist
    assert "session.mode" not in session_loop.config_store.extra, (
        f"bad_mode={bad_mode!r} should NOT have persisted to extra"
    )
    # No settings.state echo
    states = fake_bus.emitted_by_type("ipc.settings.state")
    assert states == [], (
        f"bad_mode={bad_mode!r} should NOT have emitted settings.state; got: "
        f"{[m['type'] for m in fake_bus.emitted]}"
    )
    # ipc.error WITH original_type pointing back at set_mode
    errors = fake_bus.emitted_by_type("ipc.error")
    assert len(errors) == 1, (
        f"bad_mode={bad_mode!r} should emit exactly one ipc.error; got: "
        f"{[m['type'] for m in fake_bus.emitted]}"
    )
    assert errors[0]["payload"]["original_type"] == "ipc.session.set_mode"
    assert "set_mode" in errors[0]["payload"]["reason"].lower() or "mode" in errors[0]["payload"]["reason"].lower()


def test_missing_mode_field_emits_ipc_error(
    fake_bus: FakeBus, session_loop: SessionLoop
) -> None:
    """An envelope with no ``mode`` key in payload rejects cleanly."""
    msg = {
        "type": "ipc.session.set_mode",
        "ts": "2026-05-28T11:00:00.000Z",
        "payload": {},
    }
    asyncio.run(session_loop._on_session_set_mode(msg))
    errors = fake_bus.emitted_by_type("ipc.error")
    assert len(errors) == 1
    assert "session.mode" not in session_loop.config_store.extra


# ---------------------------------------------------------------------------
# Round-trip — persisted mode round-trips through ConfigStore.from_dict
# ---------------------------------------------------------------------------


def test_persisted_mode_survives_round_trip_through_config_store(
    fake_bus: FakeBus, session_loop: SessionLoop, _redirect_config_path: Path
) -> None:
    """Set mode=learn → save → load → ConfigStore.extra["session.mode"] == "learn"."""
    msg = {
        "type": "ipc.session.set_mode",
        "ts": "2026-05-28T11:00:00.000Z",
        "payload": {"mode": "learn"},
    }
    asyncio.run(session_loop._on_session_set_mode(msg))

    # Re-load from disk
    raw = json.loads(_redirect_config_path.read_text(encoding="utf-8"))
    rebuilt = ConfigStore.from_dict(raw)
    assert rebuilt.extra.get("session.mode") == "learn"
