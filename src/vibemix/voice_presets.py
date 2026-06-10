# SPDX-License-Identifier: Apache-2.0
"""Legacy voice names shared by settings/config normalization."""

from __future__ import annotations

DEFAULT_VOICE = "Sven"

# Retired voice ids from pre-Chatterbox pickers. "adam" is the old
# ElevenLabs-era default — stored configs carrying it migrate forward to
# DEFAULT_VOICE just like the retired Gemini cloud ids.
LEGACY_CLOUD_TTS_VOICES = frozenset(
    {
        "adam",
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
