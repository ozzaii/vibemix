# SPDX-License-Identifier: Apache-2.0
"""Legacy voice names shared by settings/config normalization."""

from __future__ import annotations

DEFAULT_VOICE = "Adam"

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
    """Normalize config values that came from retired pre-Chatterbox voice pickers."""
    candidate = _clean_voice(value)
    if not candidate or candidate.lower() in LEGACY_CLOUD_TTS_VOICES:
        return DEFAULT_VOICE
    return candidate
