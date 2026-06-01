# SPDX-License-Identifier: Apache-2.0
"""MOSS voice names shared by settings/config and the local TTS runtime."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

DEFAULT_MOSS_VOICE = "Adam"

# Product-facing subset of the voices present in the MOSS-TTS-Nano manifest.
# Keep this mirrored in tauri/ui/src/settings/SettingsDrawer.ts until the UI
# can read the model manifest through a settings IPC.
MOSS_UI_VOICE_OPTIONS: tuple[str, ...] = (
    "Adam",
    "Bella",
    "Ava",
    "Nathan",
    "Soyo",
    "Mei",
    "Arisa",
    "Xiaoyu",
)

LEGACY_CLOUD_TTS_VOICES = frozenset(
    {
        "kore",
        "puck",
        "charon",
        "fenrir",
        "aoede",
        "leda",
        "orus",
        "zephyr",
    }
)


def _clean_voice(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def normalize_stored_voice(value: object) -> str:
    """Normalize config values that came from the retired cloud voice picker."""
    candidate = _clean_voice(value)
    if not candidate or candidate.lower() in LEGACY_CLOUD_TTS_VOICES:
        return DEFAULT_MOSS_VOICE
    return candidate


def select_moss_voice_row(
    voices: Iterable[Mapping[str, Any]],
    requested: object,
    *,
    fallback: str = DEFAULT_MOSS_VOICE,
) -> Mapping[str, Any]:
    """Choose a MOSS manifest voice row with a deterministic default fallback."""
    rows = list(voices)
    if not rows:
        raise ValueError("MOSS manifest has no builtin voices")
    requested_name = _clean_voice(requested)
    fallback_name = _clean_voice(fallback) or DEFAULT_MOSS_VOICE
    for wanted in (requested_name, fallback_name):
        if not wanted:
            continue
        match = next((row for row in rows if row.get("voice") == wanted), None)
        if match is not None:
            return match
    return rows[0]
