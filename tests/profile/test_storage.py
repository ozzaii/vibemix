# SPDX-License-Identifier: Apache-2.0
"""Profile storage tests — Phase 32-02.

Covers load / save / delete roundtrip + consent + privacy chmod.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

from vibemix.profile import (
    ProfileError,
    delete_profile,
    load_consent,
    load_profile,
    profile_path,
    save_consent,
    save_profile,
)


@pytest.fixture(autouse=True)
def _isolate_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Redirect Path.home() so every test runs against a clean ~/.config."""
    monkeypatch.setenv("HOME", str(tmp_path))
    # Path.home() honors HOME on POSIX; on Windows it uses USERPROFILE.
    if sys.platform == "win32":
        monkeypatch.setenv("USERPROFILE", str(tmp_path))
    yield


def _valid_profile() -> dict:
    return {
        "preferred_genre": "techno",
        "avg_session_duration": 60.0,
        "mix_style_tags": ["long_blends"],
        "tempo_preference_bin": "128-138",
        "event_type_response_preferences": {
            "TRACK_CHANGE": "sometimes",
            "PHASE": "sometimes",
            "KAAN_SPOKE": "rarely",
            "MIX_MOVE": "sometimes",
            "DISTORTION_CLIMB": "never",
            "ACID_LINE_ENTRY": "never",
            "HEARTBEAT": "rarely",
            "LAYER_ARRIVAL": "sometimes",
        },
    }


def test_load_missing_profile_returns_none() -> None:
    assert load_profile() is None


def test_save_then_load_roundtrip() -> None:
    profile = _valid_profile()
    save_profile(profile)
    loaded = load_profile()
    assert loaded == profile


def test_save_creates_directory() -> None:
    save_profile(_valid_profile())
    assert profile_path().parent.is_dir()


def test_save_rejects_oversize_via_serialize() -> None:
    """save_profile relies on serialize_profile's cap → ProfileError on oversize.

    We exercise the cap by monkeypatching it below the natural footprint.
    """
    from vibemix.profile import builder as _builder

    orig = _builder.MAX_PROFILE_BYTES
    _builder.MAX_PROFILE_BYTES = 10
    try:
        with pytest.raises(ProfileError):
            save_profile(_valid_profile())
    finally:
        _builder.MAX_PROFILE_BYTES = orig
    # Verify the file does NOT exist (atomic write — failure leaves nothing).
    assert not profile_path().exists()


def test_save_rejects_invalid_schema() -> None:
    bad = _valid_profile()
    bad["recent_tracks"] = ["foo"]  # P51 forbidden field
    with pytest.raises(ProfileError):
        save_profile(bad)
    assert not profile_path().exists()


def test_chmod_600_on_save() -> None:
    if sys.platform == "win32":
        pytest.skip("chmod semantics differ on Windows")
    save_profile(_valid_profile())
    mode = os.stat(profile_path()).st_mode & 0o777
    assert mode == 0o600, f"expected 0o600, got {oct(mode)}"


def test_load_corrupted_file_returns_none() -> None:
    profile_path().parent.mkdir(parents=True, exist_ok=True)
    profile_path().write_text("not valid json {[", encoding="utf-8")
    assert load_profile() is None


def test_load_schema_violation_returns_none() -> None:
    profile_path().parent.mkdir(parents=True, exist_ok=True)
    bad = _valid_profile()
    bad["library_titles"] = ["leak"]
    profile_path().write_text(json.dumps(bad), encoding="utf-8")
    assert load_profile() is None


def test_delete_existing_returns_true() -> None:
    save_profile(_valid_profile())
    assert delete_profile() is True
    assert not profile_path().exists()


def test_delete_missing_returns_false() -> None:
    assert delete_profile() is False


# ----------------------------------------------------------------------------
# Consent (state.json shared with wizard)
# ----------------------------------------------------------------------------


def test_consent_default_is_false() -> None:
    """PROFILE-05 default-OFF: no state.json → load_consent() returns False."""
    assert load_consent() is False


def test_save_consent_true_then_load() -> None:
    save_consent(True)
    assert load_consent() is True


def test_save_consent_false() -> None:
    save_consent(True)
    save_consent(False)
    assert load_consent() is False


def test_save_consent_preserves_other_state_keys() -> None:
    """Wizard's first_run_completed flag etc. must NOT be clobbered by consent
    toggle — they share state.json."""
    from vibemix.profile.storage import consent_path

    consent_path().parent.mkdir(parents=True, exist_ok=True)
    consent_path().write_text(
        json.dumps({
            "first_run_completed": True,
            "calibrated_at": "2026-05-15T00:00:00Z",
        }),
        encoding="utf-8",
    )
    save_consent(True)
    data = json.loads(consent_path().read_text(encoding="utf-8"))
    assert data["first_run_completed"] is True
    assert data["calibrated_at"] == "2026-05-15T00:00:00Z"
    assert data["profile_consent"] is True
