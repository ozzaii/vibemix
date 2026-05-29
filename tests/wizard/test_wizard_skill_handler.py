# SPDX-License-Identifier: Apache-2.0
"""WizardLoop.ipc.wizard.set_skill handler — Quick 260529-ifq.

The onboarding skill-level step fires ``ipc.wizard.set_skill`` on Continue.
The handler persists ``ConfigStore.extra["skill"]`` to config.json so the next
cold boot seeds ``VIBEMIX_SKILL_LEVEL`` (apply_persona_config_to_env), picking
the right co-host prompt cell. Mirrors the profile-consent handler precedent.

Verifies:
- Handler registers under ``ipc.wizard.set_skill``.
- A valid skill persists to ``config.json`` extra["skill"].
- An invalid skill leaves the store untouched.
- Fire-and-forget: no reply is emitted.
"""

from __future__ import annotations

import asyncio
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


def _msg(skill: str) -> dict:
    return {
        "type": "ipc.wizard.set_skill",
        "ts": "2026-05-29T00:00:00+00:00",
        "payload": {"skill": skill},
    }


def test_set_skill_handler_registers(fake_bus: FakeBus) -> None:
    loop = WizardLoop(fake_bus)
    loop.register_handlers()
    assert "ipc.wizard.set_skill" in fake_bus.handlers


def test_set_skill_persists_to_config(fake_bus: FakeBus) -> None:
    from vibemix.runtime.config_store import load_config

    loop = WizardLoop(fake_bus)
    loop.register_handlers()
    _drive(fake_bus, _msg("pro"))

    assert load_config().extra.get("skill") == "pro"


def test_set_skill_rejects_invalid(fake_bus: FakeBus) -> None:
    from vibemix.runtime.config_store import load_config

    loop = WizardLoop(fake_bus)
    loop.register_handlers()
    _drive(fake_bus, _msg("expert"))  # not a valid skill

    assert "skill" not in load_config().extra


def test_set_skill_is_fire_and_forget(fake_bus: FakeBus) -> None:
    loop = WizardLoop(fake_bus)
    loop.register_handlers()
    _drive(fake_bus, _msg("beginner"))

    # No-ack by design — nothing is emitted back to the renderer.
    assert fake_bus.emitted == []


def test_set_skill_seeds_cold_boot_persona_env(fake_bus: FakeBus) -> None:
    """Concrete end-to-end chain: the wizard write must be what the next cold
    boot reads. Drive the handler, then run the SAME seed bridge __main__ runs
    at startup (apply_persona_config_to_env) and assert it sets the env var the
    co-host resolves its prompt cell from."""
    from vibemix.runtime.config_store import load_config
    from vibemix.runtime.settings import apply_persona_config_to_env

    loop = WizardLoop(fake_bus)
    loop.register_handlers()
    _drive(fake_bus, _msg("pro"))

    env: dict[str, str] = {}
    applied = apply_persona_config_to_env(load_config(), environ=env)

    assert applied.get("skill") == "pro"
    assert env.get("VIBEMIX_SKILL_LEVEL") == "pro"
