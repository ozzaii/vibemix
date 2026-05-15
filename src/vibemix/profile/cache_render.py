# SPDX-License-Identifier: Apache-2.0
"""Render a profile dict into a compact text block for GeminiContextCache.

Phase 32 / PROFILE-03. Pitfall P60: profile lives in the cache body, NOT in
the per-turn prompt prefix. The cache body is a string (the system instruction
plus this section), so we serialize the profile as flat key:value lines
rather than raw JSON — Gemini's instruction-following is much better on prose
than on nested JSON literals, and the prose form keeps the token budget
under ~300 (versus ~700 for the raw JSON form).

Empty profile → empty string → cache body is byte-identical to the
profile-disabled path (P53 byte-identical contract preserved).
"""

from __future__ import annotations

from typing import Any

from vibemix.profile.schema import EVENT_TYPES_FOR_PREFS

#: Prefix the cache section with a fenced header so the model sees it as a
#: distinct context block rather than a continuation of the system prompt.
_HEADER = (
    "\n\n"
    "# Long-term DJ profile (allowlist v1, ~2KB)\n"
    "# This describes the DJ's general tendencies across sessions. Use it to\n"
    "# tune coaching style — never invent specific tracks or artists from it.\n"
)


def render_profile_for_cache(profile: dict[str, Any] | None) -> str:
    """Compact flat-key form for cache injection.

    Returns an empty string if profile is ``None`` so callers can pass the
    result straight into ``GeminiContextCache(profile_section=...)``. The
    cache-key stability invariant (deterministic body for identical input)
    holds because :func:`render_profile_for_cache` is a pure function over
    a sorted iteration order.
    """
    if not profile:
        return ""
    lines = [_HEADER.strip()]
    genre = profile.get("preferred_genre", "unknown")
    lines.append(f"- preferred_genre: {genre}")
    duration = profile.get("avg_session_duration", 0)
    lines.append(f"- avg_session_duration_min: {duration:.0f}")
    tags = profile.get("mix_style_tags", [])
    lines.append("- mix_style_tags: " + (", ".join(tags) if tags else "none"))
    bin_label = profile.get("tempo_preference_bin", "unknown")
    lines.append(f"- tempo_preference_bin_bpm: {bin_label}")
    prefs = profile.get("event_type_response_preferences", {})
    lines.append("- event_response_preferences:")
    for ev in EVENT_TYPES_FOR_PREFS:
        cadence = prefs.get(ev, "never")
        # Two-space indent for prose readability within Gemini's context.
        lines.append(f"  - {ev}: {cadence}")
    return "\n\n" + "\n".join(lines) + "\n"
