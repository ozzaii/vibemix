# SPDX-License-Identifier: Apache-2.0
"""Phase 32 Plan 32-05 — SessionLoop profile.* handler integration.

Covers:
- The 4 new handlers register on the SessionLoop bus.
- ``ipc.profile.view`` returns the on-disk snapshot + byte count + consent.
- ``ipc.profile.view`` with consent OFF returns profile=null even if a file
  exists on disk (privacy: never leak a stale profile post-revocation).
- ``ipc.profile.regenerate`` with consent OFF returns ok=false / consent_off.
- ``ipc.profile.regenerate`` with consent ON but no EvidenceRegistry returns
  ok=false / insufficient_evidence (the builder's empty-evidence path).
- ``ipc.profile.regenerate`` with consent ON + synthetic evidence saves a new
  profile + returns ok=true with the new dict.
- ``ipc.profile.delete`` unlinks an existing file (ok=true) and round-trips
  to a not_found ack on a missing file.
- ``ipc.profile.set_consent`` from the Settings panel persists to state.json.

Every reply is schema-validated by FakeBus.emit (the bus calls
``vibemix.ui_bus.validator.validate_message`` on each emit).
"""

from __future__ import annotations

import asyncio
import json
import sys
from collections.abc import Awaitable, Callable
from pathlib import Path

import pytest

from vibemix.runtime.session_loop import SessionLoop
from vibemix.ui_bus.validator import validate_message


class FakeBus:
    """Mirror of tests/runtime/test_session_loop.py FakeBus."""

    def __init__(self) -> None:
        self.handlers: dict[str, Callable[[dict], Awaitable[None]]] = {}
        self.emitted: list[dict] = []
        self.started = False
        self.stopped = False

    def register_handler(
        self, message_type: str, handler: Callable[[dict], Awaitable[None]]
    ) -> None:
        self.handlers[message_type] = handler

    async def start(self) -> None:
        self.started = True

    async def stop(self) -> None:
        self.stopped = True

    async def emit(self, msg: dict) -> None:
        validate_message(msg)
        self.emitted.append(json.loads(json.dumps(msg)))

    def emitted_by_type(self, msg_type: str) -> list[dict]:
        return [m for m in self.emitted if m.get("type") == msg_type]


@pytest.fixture
def fake_bus() -> FakeBus:
    return FakeBus()


@pytest.fixture(autouse=True)
def _isolate_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """All tests run with HOME pointed at tmp_path so the on-disk
    ~/.config/vibemix/profile.json + state.json are scoped to the test."""
    monkeypatch.setenv("HOME", str(tmp_path))
    if sys.platform == "win32":
        monkeypatch.setenv("USERPROFILE", str(tmp_path))
    yield


def _drive(bus: FakeBus, msg: dict) -> None:
    handler = bus.handlers[msg["type"]]
    asyncio.run(handler(msg))


class _StaticEvidenceRegistry:
    """Duck-typed EvidenceRegistry — only ``snapshot()`` is called."""

    def __init__(self, snapshot: dict[str, dict[str, tuple[float, ...]]]):
        self._snapshot = snapshot

    def snapshot(self) -> dict[str, dict[str, tuple[float, ...]]]:
        return self._snapshot


# ---------------------------------------------------------------------------
# Handler registration
# ---------------------------------------------------------------------------


def test_register_handlers_covers_profile_ipc(fake_bus: FakeBus) -> None:
    """All 4 profile.* handlers registered on the SessionLoop bus."""
    loop = SessionLoop(fake_bus)
    loop.register_handlers()
    expected = {
        "ipc.profile.view",
        "ipc.profile.regenerate",
        "ipc.profile.delete",
        "ipc.profile.set_consent",
    }
    assert expected.issubset(set(fake_bus.handlers.keys()))


# ---------------------------------------------------------------------------
# view
# ---------------------------------------------------------------------------


def test_profile_view_returns_consent_state(fake_bus: FakeBus) -> None:
    """view returns the current consent flag in the reply (so the UI can
    switch between loaded/empty/consent-off states in one round trip)."""
    loop = SessionLoop(fake_bus)
    loop.register_handlers()
    _drive(
        fake_bus,
        {
            "type": "ipc.profile.view",
            "ts": "2026-05-15T00:00:00+00:00",
            "payload": {},
        },
    )
    replies = fake_bus.emitted_by_type("ipc.profile.view_result")
    assert len(replies) == 1
    payload = replies[0]["payload"]
    assert payload["consent"] is False  # default-OFF
    assert payload["profile"] is None
    assert payload["bytes"] == 0


def test_profile_view_consent_off_returns_null_even_when_file_exists(
    fake_bus: FakeBus,
) -> None:
    """Privacy: if a profile.json was left on disk before consent was
    revoked, view MUST return profile=null. Delete is the user's
    responsibility but view never leaks past consent."""
    from vibemix.profile import save_consent, save_profile

    save_consent(False)  # explicit off
    # Force a profile file on disk by enabling, writing, then disabling.
    save_consent(True)
    save_profile(
        {
            "preferred_genre": "techno",
            "avg_session_duration": 60.0,
            "mix_style_tags": [],
            "tempo_preference_bin": "128-138",
            "event_type_response_preferences": {},
        }
    )
    save_consent(False)

    loop = SessionLoop(fake_bus)
    loop.register_handlers()
    _drive(
        fake_bus,
        {
            "type": "ipc.profile.view",
            "ts": "2026-05-15T00:00:00+00:00",
            "payload": {},
        },
    )
    payload = fake_bus.emitted_by_type("ipc.profile.view_result")[0]["payload"]
    assert payload["consent"] is False
    assert payload["profile"] is None
    assert payload["bytes"] == 0


def test_profile_view_loaded_state(fake_bus: FakeBus) -> None:
    """view with consent ON + a real profile returns the dict + byte count."""
    from vibemix.profile import save_consent, save_profile

    save_consent(True)
    profile = {
        "preferred_genre": "hard_tek",
        "avg_session_duration": 72.0,
        "mix_style_tags": ["long_blends", "loud_drops"],
        "tempo_preference_bin": "138-150",
        "event_type_response_preferences": {"PHASE": "sometimes"},
    }
    save_profile(profile)

    loop = SessionLoop(fake_bus)
    loop.register_handlers()
    _drive(
        fake_bus,
        {
            "type": "ipc.profile.view",
            "ts": "2026-05-15T00:00:00+00:00",
            "payload": {},
        },
    )
    payload = fake_bus.emitted_by_type("ipc.profile.view_result")[0]["payload"]
    assert payload["consent"] is True
    assert payload["profile"] == profile
    assert payload["bytes"] > 0
    assert payload["bytes"] <= 2048  # P51 hard cap


# ---------------------------------------------------------------------------
# regenerate
# ---------------------------------------------------------------------------


def test_profile_regenerate_consent_off_returns_error(fake_bus: FakeBus) -> None:
    """Consent OFF → ok=false, error='consent_off'."""
    loop = SessionLoop(fake_bus)
    loop.register_handlers()
    _drive(
        fake_bus,
        {
            "type": "ipc.profile.regenerate",
            "ts": "2026-05-15T00:00:00+00:00",
            "payload": {},
        },
    )
    payload = fake_bus.emitted_by_type("ipc.profile.regenerate_result")[0][
        "payload"
    ]
    assert payload["ok"] is False
    assert payload["profile"] is None
    assert payload["error"] == "consent_off"


def test_profile_regenerate_insufficient_evidence(fake_bus: FakeBus) -> None:
    """Consent ON but no evidence_registry attached + no prior profile →
    ok=false, error='insufficient_evidence'. PROFILE-06 drift gate."""
    from vibemix.profile import save_consent

    save_consent(True)
    loop = SessionLoop(fake_bus)  # no evidence_registry
    loop.register_handlers()
    _drive(
        fake_bus,
        {
            "type": "ipc.profile.regenerate",
            "ts": "2026-05-15T00:00:00+00:00",
            "payload": {},
        },
    )
    payload = fake_bus.emitted_by_type("ipc.profile.regenerate_result")[0][
        "payload"
    ]
    assert payload["ok"] is False
    assert payload["profile"] is None
    assert payload["error"] == "insufficient_evidence"


def test_profile_regenerate_with_evidence_saves_and_returns_profile(
    fake_bus: FakeBus,
) -> None:
    """Consent ON + sufficient evidence → ok=true, profile saved + returned."""
    from vibemix.profile import load_profile, save_consent

    save_consent(True)
    synthetic = {
        "event": {
            "PHASE": (1.0, 2.0, 3.0),
            "TRACK_CHANGE": (4.0, 5.0),
            "MIX_MOVE": (6.0, 7.0),
        }
    }
    loop = SessionLoop(
        fake_bus, evidence_registry=_StaticEvidenceRegistry(synthetic)
    )
    loop.register_handlers()
    _drive(
        fake_bus,
        {
            "type": "ipc.profile.regenerate",
            "ts": "2026-05-15T00:00:00+00:00",
            "payload": {},
        },
    )
    payload = fake_bus.emitted_by_type("ipc.profile.regenerate_result")[0][
        "payload"
    ]
    assert payload["ok"] is True, payload
    assert payload["profile"] is not None
    # The builder saved the new profile to disk.
    assert load_profile() == payload["profile"]


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


def test_profile_delete_round_trip(fake_bus: FakeBus) -> None:
    """delete on an existing file → ok=true; delete on a missing file →
    ok=false, error='not_found'."""
    from vibemix.profile import load_profile, save_consent, save_profile

    save_consent(True)
    profile = {
        "preferred_genre": "techno",
        "avg_session_duration": 60.0,
        "mix_style_tags": ["quick_cuts"],
        "tempo_preference_bin": "128-138",
        "event_type_response_preferences": {},
    }
    save_profile(profile)
    assert load_profile() is not None

    loop = SessionLoop(fake_bus)
    loop.register_handlers()
    _drive(
        fake_bus,
        {
            "type": "ipc.profile.delete",
            "ts": "2026-05-15T00:00:00+00:00",
            "payload": {},
        },
    )
    acks = fake_bus.emitted_by_type("ipc.profile.delete_ack")
    assert len(acks) == 1
    assert acks[0]["payload"] == {"ok": True, "error": None}
    assert load_profile() is None

    # Second delete: ok=false, error='not_found'.
    _drive(
        fake_bus,
        {
            "type": "ipc.profile.delete",
            "ts": "2026-05-15T00:00:00+00:00",
            "payload": {},
        },
    )
    acks = fake_bus.emitted_by_type("ipc.profile.delete_ack")
    assert len(acks) == 2
    assert acks[1]["payload"] == {"ok": False, "error": "not_found"}


# ---------------------------------------------------------------------------
# set_consent (Settings panel path — mirrors WizardLoop's handler)
# ---------------------------------------------------------------------------


def test_session_set_consent_persists_and_acks(fake_bus: FakeBus) -> None:
    """Settings panel's enable affordance → set_consent → state.json + ack."""
    from vibemix.profile import load_consent

    loop = SessionLoop(fake_bus)
    loop.register_handlers()
    _drive(
        fake_bus,
        {
            "type": "ipc.profile.set_consent",
            "ts": "2026-05-15T00:00:00+00:00",
            "payload": {"consent": True},
        },
    )
    assert load_consent() is True
    acks = fake_bus.emitted_by_type("ipc.profile.consent_state")
    assert len(acks) == 1
    assert acks[0]["payload"] == {"consent": True}
