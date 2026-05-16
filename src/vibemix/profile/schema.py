# SPDX-License-Identifier: Apache-2.0
"""Profile schema — Draft-07 jsonschema, ``additionalProperties: false``.

Phase 32 / PROFILE-02. Pitfall P51 privacy: the only fields that may ever
appear in a profile.json are the five named here. The schema is the
canonical privacy gate — any future builder bug that tries to write a
``recent_tracks`` / ``library_titles`` / free-form field fails fast at
``validate_profile`` BEFORE the bytes are serialized.

Project convention (D-Area-4.4): no pydantic. jsonschema only.
"""

from __future__ import annotations

from typing import Final

import jsonschema

#: All allowed mix-style tags. Edit with extreme care — any change to this
#: list shifts the privacy contract and the public-disclosure copy on the
#: wizard's PROFILE step.
MIX_STYLE_TAGS: Final[tuple[str, ...]] = (
    "long_blends",
    "quick_cuts",
    "loops",
    "filter_sweeps",
    "loud_drops",
    "subtle_transitions",
    "vocal_pickups",
    "bass_riding",
    "tempo_jumps",
    "phrase_locked",
    "off-grid",
)

#: All event types that may carry a per-type response preference. Mirrors
#: ``vibemix.state.event.EVENT_PRIORITY`` minus the bookkeeping internals
#: (``MANUAL``) — those don't have meaningful tendency aggregates.
EVENT_TYPES_FOR_PREFS: Final[tuple[str, ...]] = (
    "TRACK_CHANGE",
    "PHASE",
    "KAAN_SPOKE",
    "MIX_MOVE",
    "DISTORTION_CLIMB",
    "ACID_LINE_ENTRY",
    "HEARTBEAT",
    "LAYER_ARRIVAL",
)

#: Allowed genre enums. ``"unknown"`` is the cold-start value.
GENRES: Final[tuple[str, ...]] = ("hard_tek", "techno", "house", "unknown")

#: Tempo bins (BPM ranges). Closed-open semantics: a track at exactly 128.0
#: belongs to "128-138".
TEMPO_BINS: Final[tuple[str, ...]] = (
    "110-120",
    "120-128",
    "128-138",
    "138-150",
    "150+",
)

#: Cadence enums for per-event-type response preferences.
RESPONSE_CADENCES: Final[tuple[str, ...]] = ("always", "sometimes", "rarely", "never")


PROFILE_SCHEMA: Final[dict] = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "$id": "vibemix.profile.v1",
    "title": "vibemix long-term DJ profile (~2KB JSON)",
    "description": (
        "Content-allowlisted summary of the user's DJ tendencies. "
        "Stored locally only; cache-side injected into Gemini context. "
        "No track titles. No library contents. No free-form strings. "
        "Pitfall P51 privacy + 2048-byte size cap enforced at serialize-time."
    ),
    "type": "object",
    "additionalProperties": False,
    "required": [
        "preferred_genre",
        "avg_session_duration",
        "mix_style_tags",
        "tempo_preference_bin",
        "event_type_response_preferences",
    ],
    "properties": {
        "preferred_genre": {"enum": list(GENRES)},
        "avg_session_duration": {
            "type": "number",
            "minimum": 0,
            "maximum": 720,  # cap at 12 hours
        },
        "mix_style_tags": {
            "type": "array",
            "maxItems": 8,
            "uniqueItems": True,
            "items": {"enum": list(MIX_STYLE_TAGS)},
        },
        "tempo_preference_bin": {"enum": list(TEMPO_BINS)},
        "event_type_response_preferences": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                ev: {"enum": list(RESPONSE_CADENCES)} for ev in EVENT_TYPES_FOR_PREFS
            },
        },
    },
}


# Module-level compiled validator — Draft-07 ref-resolver cached internally.
_VALIDATOR: Final[jsonschema.Draft7Validator] = jsonschema.Draft7Validator(
    PROFILE_SCHEMA
)


class ProfileError(ValueError):
    """Raised on schema violation OR size-cap violation.

    Use a single exception type so callers don't have to discriminate —
    every reason to reject a profile is the same kind of bug (allowlist
    drift). The error message carries the actionable detail.
    """


def validate_profile(profile: dict) -> None:
    """Raise ``ProfileError`` if profile doesn't match the schema.

    Used by ``serialize_profile`` and by ``storage.load_profile`` on read
    (corrupted file → treated as missing). Pure function; no I/O.
    """
    try:
        _VALIDATOR.validate(profile)
    except jsonschema.ValidationError as e:
        # Compact the jsonschema error path into a single line — the full
        # stack trace is huge and rarely useful for the kinds of bugs
        # this catches (unknown field, wrong enum value).
        path = "/".join(str(p) for p in e.absolute_path) or "<root>"
        raise ProfileError(f"profile schema violation at {path}: {e.message}") from e
