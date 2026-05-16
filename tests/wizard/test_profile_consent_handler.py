# SPDX-License-Identifier: Apache-2.0
"""WizardLoop.ipc.profile.set_consent handler — Phase 32 / PROFILE-05.

Verifies:
- Handler registers under the right type.
- consent=False (default) persists profile_consent: false to state.json.
- consent=True persists true.
- Reply is a schema-valid ipc.profile.consent_state envelope.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import pytest

from tests.wizard.conftest import FakeBus
from vibemix.runtime.wizard import WizardLoop


@pytest.fixture(autouse=True)
def _isolate_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    if sys.platform == "win32":
        monkeypatch.setenv("USERPROFILE", str(tmp_path))
    yield


def _drive(bus: FakeBus, msg: dict) -> None:
    handler = bus.handlers[msg["type"]]
    asyncio.run(handler(msg))


def test_profile_set_consent_persists_true(fake_bus: FakeBus) -> None:
    from vibemix.profile import load_consent

    loop = WizardLoop(fake_bus)
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


def test_profile_set_consent_persists_false(fake_bus: FakeBus) -> None:
    from vibemix.profile import load_consent, save_consent

    save_consent(True)  # baseline
    loop = WizardLoop(fake_bus)
    loop.register_handlers()
    _drive(
        fake_bus,
        {
            "type": "ipc.profile.set_consent",
            "ts": "2026-05-15T00:00:00+00:00",
            "payload": {"consent": False},
        },
    )
    assert load_consent() is False


def test_profile_set_consent_emits_consent_state_reply(fake_bus: FakeBus) -> None:
    loop = WizardLoop(fake_bus)
    loop.register_handlers()
    _drive(
        fake_bus,
        {
            "type": "ipc.profile.set_consent",
            "ts": "2026-05-15T00:00:00+00:00",
            "payload": {"consent": True},
        },
    )
    replies = fake_bus.emitted_by_type("ipc.profile.consent_state")
    assert len(replies) == 1
    assert replies[0]["payload"] == {"consent": True}


def test_profile_set_consent_default_off_path(fake_bus: FakeBus) -> None:
    """PROFILE-05 — sidecar default state has profile_consent: False.

    The wizard's renderer-side default is OFF; this asserts that without
    any handler call, load_consent() returns False.
    """
    from vibemix.profile import load_consent

    # No handler invocation — consent should be False by default.
    assert load_consent() is False
