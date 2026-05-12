# SPDX-License-Identifier: Apache-2.0
"""Phase 12 Wave 2 — SettingsApplier dispatch matrix.

Covers the 7-field dispatch contract from 12-02 must-haves:

  voice            → cascade.set_voice
  mode             → event_detector.set_mode
  genre            → genre_profile_loader.reload
  output_device_id → audio_core.restart_output
  output_profile   → audio_core.set_mic_gating_profile
  retention_days   → config_store.set + persist
  push_to_mute_hotkey → config_store.set + persist

For each field:
  * Happy path → ``(True, None)`` and the matching hook fires + the
    config_store is mutated + persisted.
  * Missing hook → ``(False, "<reason>")`` and the config is untouched
    EXCEPT for the genre apply which persists-on-miss with a soft warn
    (so a restart picks it up — see plan note).
  * Invalid value → ``(False, "<reason>")`` and the hook is NOT fired.

Tests use ``tmp_path`` to redirect ``save_config`` writes — the
applier's persist call passes the live ConfigStore back to the module
function, which uses the resolved path (we patch ``config_path`` for
each test).
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from vibemix.runtime import config_store as cs_mod
from vibemix.runtime.config_store import ConfigStore
from vibemix.runtime.settings import GENRE_OVERLAY_S, SettingsApplier


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _redirect_config_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect ``save_config()`` writes into ``tmp_path/config.json``.

    The applier calls ``save_config(self.config_store)`` with no explicit
    path — that resolves to ``config_path()`` which hits the user's real
    home dir. Patch the module-level resolver so tests are hermetic.
    """
    target = tmp_path / "config.json"
    monkeypatch.setattr(cs_mod, "config_path", lambda: target)
    return target


@pytest.fixture
def store() -> ConfigStore:
    return ConfigStore()


@pytest.fixture
def cascade() -> MagicMock:
    return MagicMock(spec=["set_voice"])


@pytest.fixture
def event_detector() -> MagicMock:
    return MagicMock(spec=["set_mode"])


@pytest.fixture
def audio_core() -> MagicMock:
    return MagicMock(spec=["restart_output", "set_mic_gating_profile"])


@pytest.fixture
def genre_loader() -> MagicMock:
    return MagicMock(spec=["reload"])


def _apply(applier: SettingsApplier, field: str, value) -> tuple[bool, str | None]:
    return asyncio.run(applier.apply(field, value))


# ---------------------------------------------------------------------------
# voice
# ---------------------------------------------------------------------------


def test_voice_happy_path(store, cascade, _redirect_config_path):
    applier = SettingsApplier(config_store=store, cascade_agent=cascade)
    success, error = _apply(applier, "voice", "puck")
    assert (success, error) == (True, None)
    cascade.set_voice.assert_called_once_with("puck")
    assert store.voice == "puck"
    assert _redirect_config_path.exists()


def test_voice_missing_hook_returns_error(store):
    applier = SettingsApplier(config_store=store)
    success, error = _apply(applier, "voice", "puck")
    assert success is False
    assert "cascade_agent" in error
    assert store.voice == "kore"  # unchanged


def test_voice_invalid_value(store, cascade):
    applier = SettingsApplier(config_store=store, cascade_agent=cascade)
    success, error = _apply(applier, "voice", 42)
    assert success is False
    assert "voice" in error
    cascade.set_voice.assert_not_called()


# ---------------------------------------------------------------------------
# mode
# ---------------------------------------------------------------------------


def test_mode_happy_path(store, event_detector):
    applier = SettingsApplier(config_store=store, event_detector=event_detector)
    success, error = _apply(applier, "mode", "hype")
    assert (success, error) == (True, None)
    event_detector.set_mode.assert_called_once_with("hype")
    assert store.mode == "hype"


def test_mode_missing_hook(store):
    applier = SettingsApplier(config_store=store)
    success, error = _apply(applier, "mode", "hype")
    assert success is False
    assert "event_detector" in error


def test_mode_invalid_value(store, event_detector):
    applier = SettingsApplier(config_store=store, event_detector=event_detector)
    success, error = _apply(applier, "mode", "chill")
    assert success is False
    event_detector.set_mode.assert_not_called()


# ---------------------------------------------------------------------------
# genre
# ---------------------------------------------------------------------------


def test_genre_happy_path(store, genre_loader):
    applier = SettingsApplier(config_store=store, genre_loader=genre_loader)
    success, error = _apply(applier, "genre", "dnb")
    assert (success, error) == (True, None)
    genre_loader.reload.assert_called_once_with("dnb")
    assert store.genre == "dnb"


def test_genre_overlay_window_runs(store, genre_loader, monkeypatch):
    """Genre apply awaits ~``GENRE_OVERLAY_S`` to simulate the dim window."""
    sleeps: list[float] = []

    real_sleep = asyncio.sleep

    async def _spy(t):
        sleeps.append(t)
        # Avoid actually sleeping in the test — pass through with 0.
        await real_sleep(0)

    monkeypatch.setattr("vibemix.runtime.settings.asyncio.sleep", _spy)
    applier = SettingsApplier(config_store=store, genre_loader=genre_loader)
    _apply(applier, "genre", "dnb")
    assert sleeps == [GENRE_OVERLAY_S]


def test_genre_missing_hook_persists_with_warning(store, caplog):
    """Without a genre_loader we still persist + return True (so the next
    launch picks it up); a warning is logged."""
    applier = SettingsApplier(config_store=store)
    with caplog.at_level("WARNING"):
        success, error = _apply(applier, "genre", "dnb")
    assert success is True
    assert error is None
    assert store.genre == "dnb"
    assert any("genre_loader not wired" in r.message for r in caplog.records)


def test_genre_invalid_value(store, genre_loader):
    applier = SettingsApplier(config_store=store, genre_loader=genre_loader)
    success, error = _apply(applier, "genre", "")
    assert success is False
    genre_loader.reload.assert_not_called()


# ---------------------------------------------------------------------------
# output_device_id
# ---------------------------------------------------------------------------


def test_output_device_happy_path(store, audio_core):
    applier = SettingsApplier(config_store=store, audio_core=audio_core)
    success, error = _apply(applier, "output_device_id", "dev-3")
    assert (success, error) == (True, None)
    audio_core.restart_output.assert_called_once_with("dev-3")
    assert store.output_device_id == "dev-3"


def test_output_device_accepts_null(store, audio_core):
    """``null`` (auto) is a valid value — clears the override."""
    applier = SettingsApplier(config_store=store, audio_core=audio_core)
    success, error = _apply(applier, "output_device_id", None)
    assert (success, error) == (True, None)
    audio_core.restart_output.assert_called_once_with(None)
    assert store.output_device_id is None


def test_output_device_missing_hook(store):
    applier = SettingsApplier(config_store=store)
    success, error = _apply(applier, "output_device_id", "dev-3")
    assert success is False
    assert "audio_core" in error


def test_output_device_invalid_type(store, audio_core):
    applier = SettingsApplier(config_store=store, audio_core=audio_core)
    success, error = _apply(applier, "output_device_id", 42)
    assert success is False
    audio_core.restart_output.assert_not_called()


# ---------------------------------------------------------------------------
# output_profile
# ---------------------------------------------------------------------------


def test_output_profile_happy_path(store, audio_core):
    applier = SettingsApplier(config_store=store, audio_core=audio_core)
    success, error = _apply(applier, "output_profile", "spk")
    assert (success, error) == (True, None)
    audio_core.set_mic_gating_profile.assert_called_once_with("spk")
    assert store.output_profile == "spk"


def test_output_profile_invalid_value(store, audio_core):
    applier = SettingsApplier(config_store=store, audio_core=audio_core)
    success, error = _apply(applier, "output_profile", "studio")
    assert success is False
    audio_core.set_mic_gating_profile.assert_not_called()


def test_output_profile_missing_hook(store):
    applier = SettingsApplier(config_store=store)
    success, error = _apply(applier, "output_profile", "hp")
    assert success is False
    assert "audio_core" in error


# ---------------------------------------------------------------------------
# retention_days
# ---------------------------------------------------------------------------


def test_retention_days_happy_path(store):
    """No hook required — persist-only field. Phase 15 reads at boot."""
    applier = SettingsApplier(config_store=store)
    success, error = _apply(applier, "retention_days", 14)
    assert (success, error) == (True, None)
    assert store.retention_days == 14


def test_retention_days_coerces_string(store):
    applier = SettingsApplier(config_store=store)
    success, error = _apply(applier, "retention_days", "30")
    assert (success, error) == (True, None)
    assert store.retention_days == 30


def test_retention_days_negative_rejected(store):
    applier = SettingsApplier(config_store=store)
    success, error = _apply(applier, "retention_days", -1)
    assert success is False
    assert store.retention_days == 7


def test_retention_days_non_numeric_rejected(store):
    applier = SettingsApplier(config_store=store)
    success, error = _apply(applier, "retention_days", "many")
    assert success is False
    assert store.retention_days == 7


# ---------------------------------------------------------------------------
# push_to_mute_hotkey
# ---------------------------------------------------------------------------


def test_hotkey_happy_path(store):
    """No hook required — Tauri shell binds via tauri-plugin-global-shortcut."""
    applier = SettingsApplier(config_store=store)
    success, error = _apply(applier, "push_to_mute_hotkey", "cmd+option+m")
    assert (success, error) == (True, None)
    assert store.push_to_mute_hotkey == "cmd+option+m"


def test_hotkey_empty_rejected(store):
    applier = SettingsApplier(config_store=store)
    success, error = _apply(applier, "push_to_mute_hotkey", "")
    assert success is False


# ---------------------------------------------------------------------------
# Unknown field
# ---------------------------------------------------------------------------


def test_unknown_field_returns_error(store):
    applier = SettingsApplier(config_store=store)
    success, error = _apply(applier, "color", "blue")
    assert success is False
    assert "color" in error


# ---------------------------------------------------------------------------
# Persistence happens
# ---------------------------------------------------------------------------


def test_apply_persists_to_disk(store, cascade, _redirect_config_path):
    applier = SettingsApplier(config_store=store, cascade_agent=cascade)
    _apply(applier, "voice", "puck")
    import json

    on_disk = json.loads(_redirect_config_path.read_text())
    assert on_disk["voice"] == "puck"
