"""Tauri runtime activation-policy guards."""

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_pill_window_does_not_demote_whole_app_to_accessory_policy() -> None:
    """The pill may float, but the main app must stay a foregroundable app."""

    pill_window = (REPO_ROOT / "tauri/src-tauri/src/pill_window.rs").read_text(
        encoding="utf-8"
    )
    cargo = (REPO_ROOT / "tauri/src-tauri/Cargo.toml").read_text(encoding="utf-8")

    forbidden = (
        "set_activation_policy",
        "ActivationPolicy::Accessory",
        "Accessory-activation-policy",
    )
    for phrase in forbidden:
        assert phrase not in pill_window

    assert "Do not use" in cargo
    assert "ActivationPolicy::Accessory" in cargo
