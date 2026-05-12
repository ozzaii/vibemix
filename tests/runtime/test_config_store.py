# SPDX-License-Identifier: Apache-2.0
"""Phase 12 Wave 2 — config_store round-trip + Phase 11 superset coverage.

Covers:
  * Round-trip read/write of all Phase 11 + Phase 12 fields.
  * Atomic write — the tmp-then-rename path leaves no half-written
    file even when interrupted.
  * Phase 11 superset preservation — unknown top-level keys (e.g.
    tauri-plugin-store's ``first_run_state`` wrapper) survive a load
    → save round trip.
  * OS-specific path resolution — macOS via HOME, Windows via APPDATA,
    each monkeypatched into a tmp dir so no real config gets touched.
  * Platform-aware hotkey default — cmd+shift+m on darwin, ctrl+shift+m on win32.
  * Corrupt / missing config files load as all-defaults without crashing.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from vibemix.runtime import config_store as cs_mod
from vibemix.runtime.config_store import (
    ConfigStore,
    _default_hotkey,
    config_path,
    load_config,
    save_config,
)


# ---------------------------------------------------------------------------
# Defaults + dataclass shape
# ---------------------------------------------------------------------------


def test_defaults_phase12_fields() -> None:
    """A fresh ``ConfigStore`` carries the Phase 12 defaults verbatim."""
    cfg = ConfigStore()
    assert cfg.voice == "kore"
    assert cfg.mode == "coach"
    assert cfg.genre == "tech-house"
    assert cfg.output_device_id is None
    assert cfg.output_profile == "hp"
    assert cfg.retention_days == 7
    # Hotkey is platform-aware — match whatever this process is on.
    assert cfg.push_to_mute_hotkey == _default_hotkey()


def test_default_hotkey_per_platform(monkeypatch: pytest.MonkeyPatch) -> None:
    """Hotkey resolver swaps cmd↔ctrl on darwin/win32."""
    monkeypatch.setattr(sys, "platform", "darwin")
    assert _default_hotkey() == "cmd+shift+m"
    monkeypatch.setattr(sys, "platform", "win32")
    assert _default_hotkey() == "ctrl+shift+m"


# ---------------------------------------------------------------------------
# Round-trip
# ---------------------------------------------------------------------------


def test_round_trip_phase12_fields(tmp_path: Path) -> None:
    """Writing then reading recovers every Phase 12 field."""
    target = tmp_path / "config.json"
    cfg = ConfigStore(
        voice="puck",
        mode="hype",
        genre="dnb",
        output_device_id="dev-7",
        output_profile="spk",
        retention_days=30,
        push_to_mute_hotkey="cmd+option+m",
    )
    save_config(cfg, target)
    assert target.exists()
    loaded = load_config(target)
    assert loaded.voice == "puck"
    assert loaded.mode == "hype"
    assert loaded.genre == "dnb"
    assert loaded.output_device_id == "dev-7"
    assert loaded.output_profile == "spk"
    assert loaded.retention_days == 30
    assert loaded.push_to_mute_hotkey == "cmd+option+m"


def test_round_trip_preserves_phase11_fields(tmp_path: Path) -> None:
    """Phase 11 first-run-completed + calibrated_at survive a write+read."""
    target = tmp_path / "config.json"
    cfg = ConfigStore(
        first_run_completed=True,
        calibrated_at="2026-05-12T09:00:00+00:00",
        controller_profile="ddj-flx4",
        target_dj_app_hint="djay",
        target_window_id="win-12345",
        blackhole_install_seen=True,
    )
    save_config(cfg, target)
    loaded = load_config(target)
    assert loaded.first_run_completed is True
    assert loaded.calibrated_at == "2026-05-12T09:00:00+00:00"
    assert loaded.controller_profile == "ddj-flx4"
    assert loaded.target_dj_app_hint == "djay"
    assert loaded.target_window_id == "win-12345"
    assert loaded.blackhole_install_seen is True


def test_round_trip_preserves_unknown_keys(tmp_path: Path) -> None:
    """Top-level keys we don't own (e.g. tauri-plugin-store wrapper) survive."""
    target = tmp_path / "config.json"
    # Simulate the Rust shell having written first_run_state via
    # tauri-plugin-store ahead of any Python writes.
    target.write_text(
        json.dumps(
            {
                "first_run_state": {
                    "first_run_completed": True,
                    "calibrated_at": "2026-05-12T09:00:00+00:00",
                }
            }
        )
    )
    loaded = load_config(target)
    # Unknown key landed in extra
    assert "first_run_state" in loaded.extra
    # Defaults filled in for everything else
    assert loaded.voice == "kore"
    # Now write and verify the unknown key survives
    loaded.voice = "puck"
    save_config(loaded, target)
    on_disk = json.loads(target.read_text())
    assert on_disk["first_run_state"]["first_run_completed"] is True
    assert on_disk["voice"] == "puck"


# ---------------------------------------------------------------------------
# Atomic write
# ---------------------------------------------------------------------------


def test_atomic_write_uses_tmp_then_replace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``save_config`` writes to a tmp file then ``os.replace`` swaps in."""
    target = tmp_path / "config.json"
    cfg = ConfigStore(voice="puck")
    saw_tmp: list[Path] = []

    real_replace = cs_mod.os.replace

    def _spy_replace(src, dst):
        saw_tmp.append(Path(src))
        return real_replace(src, dst)

    monkeypatch.setattr(cs_mod.os, "replace", _spy_replace)
    save_config(cfg, target)
    # tmp filename mirrors target with .tmp suffix
    assert len(saw_tmp) == 1
    assert saw_tmp[0].name == "config.json.tmp"
    assert target.exists()


def test_atomic_write_creates_parent_dir(tmp_path: Path) -> None:
    """``save`` mkdir-p's the parent so a fresh install doesn't ENOENT."""
    target = tmp_path / "deep" / "nested" / "config.json"
    cfg = ConfigStore(voice="puck")
    save_config(cfg, target)
    assert target.exists()


# ---------------------------------------------------------------------------
# Load fallbacks
# ---------------------------------------------------------------------------


def test_load_missing_file_returns_defaults(tmp_path: Path) -> None:
    """No file on disk → fresh defaults without raising."""
    target = tmp_path / "nope.json"
    cfg = load_config(target)
    assert cfg.voice == "kore"
    assert cfg.retention_days == 7


def test_load_corrupt_json_returns_defaults(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Malformed JSON logs a warning then returns defaults — never crashes."""
    target = tmp_path / "config.json"
    target.write_text("{not json")
    cfg = load_config(target)
    assert cfg.voice == "kore"
    captured = capsys.readouterr()
    assert "config_store" in captured.err


def test_load_non_dict_returns_defaults(tmp_path: Path) -> None:
    """A JSON array or scalar at the top level falls back to defaults."""
    target = tmp_path / "config.json"
    target.write_text("[1, 2, 3]")
    cfg = load_config(target)
    assert cfg.voice == "kore"


def test_load_coerces_retention_days(tmp_path: Path) -> None:
    """``retention_days`` arriving as a string coerces to int when possible."""
    target = tmp_path / "config.json"
    target.write_text(json.dumps({"retention_days": "14"}))
    cfg = load_config(target)
    assert cfg.retention_days == 14


def test_load_drops_bad_retention_days(tmp_path: Path) -> None:
    """Non-coercible retention_days falls back to default."""
    target = tmp_path / "config.json"
    target.write_text(json.dumps({"retention_days": "many"}))
    cfg = load_config(target)
    assert cfg.retention_days == 7


# ---------------------------------------------------------------------------
# OS-specific path resolution
# ---------------------------------------------------------------------------


def test_config_path_macos(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """On darwin, ``~/Library/Application Support/vibemix/config.json``."""
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setenv("HOME", str(tmp_path))
    p = config_path()
    assert p == tmp_path / "Library" / "Application Support" / "vibemix" / "config.json"


def test_config_path_windows(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """On win32, ``%APPDATA%/vibemix/config.json``."""
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setenv("APPDATA", str(tmp_path))
    p = config_path()
    assert p == tmp_path / "vibemix" / "config.json"


def test_config_path_windows_appdata_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """On win32 with APPDATA unset, fall back to ``~/AppData/Roaming``."""
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.delenv("APPDATA", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    # Win path expanding ~ on a posix host honors HOME; assertion is on shape.
    p = config_path()
    assert p.name == "config.json"
    assert p.parent.name == "vibemix"
    assert "Roaming" in str(p)


def test_config_path_linux_xdg(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """On a non-Mac/Win runner, honor XDG_CONFIG_HOME (CI safety)."""
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    p = config_path()
    assert p == tmp_path / "vibemix" / "config.json"


# ---------------------------------------------------------------------------
# Muted is NOT persisted
# ---------------------------------------------------------------------------


def test_muted_is_not_a_field(tmp_path: Path) -> None:
    """``muted`` is owned by SessionLoop; ConfigStore must not carry it."""
    cfg = ConfigStore()
    assert not hasattr(cfg, "muted")
    target = tmp_path / "config.json"
    save_config(cfg, target)
    on_disk = json.loads(target.read_text())
    assert "muted" not in on_disk
