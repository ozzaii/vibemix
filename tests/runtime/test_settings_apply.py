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
from vibemix.runtime.settings import (
    GENRE_OVERLAY_S,
    GenreProfileLoader,
    SettingsApplier,
    apply_persona_config_to_env,
    resolve_genre_profile_name,
)

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


@pytest.fixture(autouse=True)
def _isolate_applier_env():
    """Snapshot + restore the OS env vars the applier writes directly.

    ``_apply_skill`` (and any future ``_apply_*`` that exports an env var) sets
    ``os.environ[...]`` *inside the applier* — that is a real process-global
    mutation, NOT a monkeypatch, so without this fixture ``VIBEMIX_SKILL_LEVEL``
    leaks out of ``test_skill_happy_path`` and corrupts ``_resolve_prompt_cell``
    in any test file that runs afterwards in the same process (Phase 79 Wave-0
    finding: adjacent settings→dj_cohost runs flipped the co-host cell to the
    leaked 'pro' persona). ``monkeypatch`` cannot undo a key it never recorded a
    prior value for, so we capture-then-restore the raw values explicitly.
    """
    import os

    keys = ("VIBEMIX_SKILL_LEVEL", "VIBEMIX_MODE", "VIBEMIX_MOOD")
    saved = {k: os.environ.get(k) for k in keys}
    try:
        yield
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


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
    success, error = _apply(applier, "voice", "Bella")
    assert (success, error) == (True, None)
    cascade.set_voice.assert_called_once_with("Bella")
    assert store.voice == "Bella"
    assert _redirect_config_path.exists()


def test_voice_legacy_cloud_id_normalizes_before_live_hook(store, cascade):
    applier = SettingsApplier(config_store=store, cascade_agent=cascade)
    success, error = _apply(applier, "voice", "kore")
    assert (success, error) == (True, None)
    cascade.set_voice.assert_called_once_with("Adam")
    assert store.voice == "Adam"


def test_voice_missing_hook_persists_with_warning(store, caplog):
    """No live cascade hook (LiveKit path) → persist + succeed (deferred-live),
    like genre — the voice sticks for the next session, not a dead error."""
    applier = SettingsApplier(config_store=store)
    with caplog.at_level("WARNING"):
        success, error = _apply(applier, "voice", "Bella")
    assert success is True
    assert error is None
    assert store.voice == "Bella"
    assert any("cascade_agent not wired" in r.message for r in caplog.records)


def test_voice_legacy_cloud_id_normalizes_when_deferred(store, caplog):
    applier = SettingsApplier(config_store=store)
    with caplog.at_level("WARNING"):
        success, error = _apply(applier, "voice", "puck")
    assert (success, error) == (True, None)
    assert store.voice == "Adam"
    assert any("persisted voice='Adam'" in r.message for r in caplog.records)


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


def test_mode_apply_exports_env_for_next_agent_build(store, event_detector, monkeypatch):
    monkeypatch.delenv("VIBEMIX_MODE", raising=False)
    applier = SettingsApplier(config_store=store, event_detector=event_detector)
    success, error = _apply(applier, "mode", "coach")
    assert (success, error) == (True, None)
    import os

    assert os.environ["VIBEMIX_MODE"] == "coach"


def test_mode_missing_hook_persists_with_warning(store, caplog):
    """No live event_detector hook → persist + succeed (deferred-live)."""
    applier = SettingsApplier(config_store=store)
    with caplog.at_level("WARNING"):
        success, error = _apply(applier, "mode", "hype")
    assert success is True
    assert error is None
    assert store.mode == "hype"
    assert any("event_detector not wired" in r.message for r in caplog.records)


def test_mode_invalid_value(store, event_detector):
    applier = SettingsApplier(config_store=store, event_detector=event_detector)
    success, _error = _apply(applier, "mode", "chill")
    assert success is False
    event_detector.set_mode.assert_not_called()


def test_apply_persona_config_to_env_seeds_prompt_resolver_env():
    env: dict[str, str] = {}
    store = ConfigStore(
        mode="coach",
        extra={"skill": "pro", "mood": "teacher"},
    )
    applied = apply_persona_config_to_env(store, env)
    assert applied == {"mode": "coach", "skill": "pro", "mood": "teacher"}
    assert env == {
        "VIBEMIX_MODE": "coach",
        "VIBEMIX_SKILL_LEVEL": "pro",
        "VIBEMIX_MOOD": "teacher",
    }


def test_apply_persona_config_to_env_ignores_invalid_extra_values():
    env: dict[str, str] = {}
    store = ConfigStore(
        mode="hype",
        extra={"skill": "wizard", "mood": "storm"},
    )
    applied = apply_persona_config_to_env(store, env)
    assert applied == {"mode": "hype"}
    assert env == {"VIBEMIX_MODE": "hype"}


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
    success, _error = _apply(applier, "genre", "")
    assert success is False
    genre_loader.reload.assert_not_called()


def test_live_genre_profile_loader_maps_drawer_dnb_to_dsp_profile():
    from vibemix.state.genre import (
        get_active_profile,
        is_auto_enabled,
        set_active_profile,
        set_auto_enabled,
    )

    set_active_profile(None)
    set_auto_enabled(True)
    try:
        GenreProfileLoader().reload("dnb")
        active = get_active_profile()
        assert active is not None
        assert active.name == "drum_and_bass"
        assert is_auto_enabled() is False
    finally:
        set_active_profile(None)
        set_auto_enabled(True)


def test_live_genre_profile_loader_generic_reenables_auto_detection():
    from vibemix.state.genre import (
        get_active_profile,
        is_auto_enabled,
        set_active_profile,
        set_auto_enabled,
    )

    set_active_profile("techno")
    set_auto_enabled(False)
    try:
        GenreProfileLoader().reload("edm-generic")
        assert get_active_profile() is None
        assert is_auto_enabled() is True
    finally:
        set_active_profile(None)
        set_auto_enabled(True)


def test_resolve_genre_profile_name_accepts_profile_names_and_ui_aliases():
    assert resolve_genre_profile_name("techno") == "techno"
    assert resolve_genre_profile_name("tech-house") == "house"
    assert resolve_genre_profile_name("hip-hop") is None


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


def test_output_device_missing_hook_persists_with_warning(store, caplog):
    """No live audio_core hook → persist + succeed (deferred-live)."""
    applier = SettingsApplier(config_store=store)
    with caplog.at_level("WARNING"):
        success, error = _apply(applier, "output_device_id", "dev-3")
    assert success is True
    assert error is None
    assert store.output_device_id == "dev-3"
    assert any("audio_core not wired" in r.message for r in caplog.records)


def test_output_device_invalid_type(store, audio_core):
    applier = SettingsApplier(config_store=store, audio_core=audio_core)
    success, _error = _apply(applier, "output_device_id", 42)
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
    success, _error = _apply(applier, "output_profile", "studio")
    assert success is False
    audio_core.set_mic_gating_profile.assert_not_called()


def test_output_profile_missing_hook_persists_with_warning(store, caplog):
    """No live audio_core hook → persist + succeed (deferred-live)."""
    applier = SettingsApplier(config_store=store)
    with caplog.at_level("WARNING"):
        success, error = _apply(applier, "output_profile", "spk")
    assert success is True
    assert error is None
    assert store.output_profile == "spk"
    assert any("audio_core not wired" in r.message for r in caplog.records)


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
    success, _error = _apply(applier, "retention_days", -1)
    assert success is False
    assert store.retention_days == 7


def test_retention_days_non_numeric_rejected(store):
    applier = SettingsApplier(config_store=store)
    success, _error = _apply(applier, "retention_days", "many")
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
    success, _error = _apply(applier, "push_to_mute_hotkey", "")
    assert success is False


# ---------------------------------------------------------------------------
# skill (persona level) — 2026-05-25
# ---------------------------------------------------------------------------


def test_skill_happy_path(store, monkeypatch):
    """No runtime hook — persists to extra + sets the env var the agent's
    prompt-cell resolver reads at its next build."""
    monkeypatch.delenv("VIBEMIX_SKILL_LEVEL", raising=False)
    applier = SettingsApplier(config_store=store)
    success, error = _apply(applier, "skill", "pro")
    assert (success, error) == (True, None)
    assert store.extra["skill"] == "pro"
    import os

    assert os.environ["VIBEMIX_SKILL_LEVEL"] == "pro"


def test_skill_invalid_value_rejected(store, monkeypatch):
    monkeypatch.delenv("VIBEMIX_SKILL_LEVEL", raising=False)
    applier = SettingsApplier(config_store=store)
    success, error = _apply(applier, "skill", "expert")
    assert success is False
    assert "skill" in error
    assert "skill" not in store.extra
    import os

    # Rejected at the trust boundary — env var untouched.
    assert "VIBEMIX_SKILL_LEVEL" not in os.environ


def test_skill_non_string_rejected(store):
    applier = SettingsApplier(config_store=store)
    success, _error = _apply(applier, "skill", 3)
    assert success is False
    assert "skill" not in store.extra


# ---------------------------------------------------------------------------
# lens (shared co-host + curator lens) — Phase 79 Wave 0 scaffolds
#
# Mirror the skill trio: no runtime hook, persists to extra["lens"], takes
# effect at the next builder read (co-host _resolve_prompt_cell + curator seam).
#
# Tier split (honest-green discipline):
#   * happy_path is xfail-strict — extra["lens"] persistence does NOT happen
#     until Plan 03 adds _apply_lens + the dispatch case. Flips green then.
#   * invalid / non_string are REAL-GREEN guards — a bad lens value MUST be
#     rejected with extra untouched both TODAY (unknown-field fallthrough) and
#     AFTER Plan 03 (enum validation). The rejection contract must never regress
#     to a silent persist, so these stay green through the implementation.
# ---------------------------------------------------------------------------


def test_apply_lens_happy_path(store, _redirect_config_path):
    """apply('lens','critique') → (True, None) and persists extra['lens']."""
    applier = SettingsApplier(config_store=store)
    success, error = _apply(applier, "lens", "critique")
    assert (success, error) == (True, None)
    assert store.extra["lens"] == "critique"
    assert _redirect_config_path.exists()


def test_apply_lens_invalid_value_rejected(store):
    """apply('lens','bogus') → (False, ...) and extra is untouched.

    REAL-GREEN guard: a bad lens value must NEVER silently persist — true today
    (unknown-field fallthrough) and after Plan 03 (enum validation).
    """
    applier = SettingsApplier(config_store=store)
    success, error = _apply(applier, "lens", "bogus")
    assert success is False
    assert error is not None and "lens" in error
    assert "lens" not in store.extra


def test_apply_lens_non_string_rejected(store):
    """apply('lens', 123) → (False, ...) and extra is untouched.

    REAL-GREEN guard: a non-string lens must never persist.
    """
    applier = SettingsApplier(config_store=store)
    success, _error = _apply(applier, "lens", 123)
    assert success is False
    assert "lens" not in store.extra


# ---------------------------------------------------------------------------
# Unknown field
# ---------------------------------------------------------------------------


def test_unknown_field_returns_error(store):
    applier = SettingsApplier(config_store=store)
    success, error = _apply(applier, "color", "blue")
    assert success is False
    assert "color" in error


# ---------------------------------------------------------------------------
# lighter_blur (Phase 14-04 — perf-blur preference)
# ---------------------------------------------------------------------------


def test_lighter_blur_happy_path_true(store, _redirect_config_path):
    """Setting lighter_blur=True persists the flag without touching hooks."""
    applier = SettingsApplier(config_store=store)
    success, error = _apply(applier, "lighter_blur", True)
    assert (success, error) == (True, None)
    assert store.lighter_blur is True
    # Verify atomic write landed on disk.
    import json

    on_disk = json.loads(_redirect_config_path.read_text())
    assert on_disk["lighter_blur"] is True


def test_lighter_blur_happy_path_false(store, _redirect_config_path):
    """Setting lighter_blur=False persists and clears the bit."""
    store.lighter_blur = True
    applier = SettingsApplier(config_store=store)
    success, error = _apply(applier, "lighter_blur", False)
    assert (success, error) == (True, None)
    assert store.lighter_blur is False
    import json

    on_disk = json.loads(_redirect_config_path.read_text())
    assert on_disk["lighter_blur"] is False


def test_lighter_blur_rejects_non_bool(store):
    """Non-boolean payloads are rejected at the trust boundary."""
    applier = SettingsApplier(config_store=store)
    for bad in ("on", 1, 0, None, "true"):
        success, error = _apply(applier, "lighter_blur", bad)
        assert success is False
        assert error and "bool" in error
    # Store stays at default — invalid writes never reach disk.
    assert store.lighter_blur is False


# ---------------------------------------------------------------------------
# Persistence happens
# ---------------------------------------------------------------------------


def test_apply_persists_to_disk(store, cascade, _redirect_config_path):
    applier = SettingsApplier(config_store=store, cascade_agent=cascade)
    _apply(applier, "voice", "Bella")
    import json

    on_disk = json.loads(_redirect_config_path.read_text())
    assert on_disk["voice"] == "Bella"
