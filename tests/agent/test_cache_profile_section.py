# SPDX-License-Identifier: Apache-2.0
"""GeminiContextCache.profile_section tests — Phase 32-02 / PROFILE-03.

Pitfall P60: profile is concatenated into the cache body, NOT injected into
the per-turn prompt. The cache key remains stable across calls with the same
profile_section, the 1024-token floor is still respected.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from vibemix.agent.cache import GEMINI_CACHE_TOKEN_FLOOR, GeminiContextCache


def _make_cache(body: str, profile_section: str = "") -> GeminiContextCache:
    return GeminiContextCache(
        client=MagicMock(),
        system_instruction_body=body,
        profile_section=profile_section,
    )


def test_default_profile_section_is_empty_string() -> None:
    """P53 byte-identical: omitting profile_section produces identical
    padded_body() to the pre-Phase-32 path (just body + pad)."""
    body = "SHORT BODY"
    cache_no_profile = _make_cache(body)
    cache_explicit_empty = _make_cache(body, profile_section="")
    assert cache_no_profile.padded_body() == cache_explicit_empty.padded_body()


def test_profile_section_concatenated_after_body() -> None:
    body = "SYSPROMPT"
    section = "\n\n# profile\n- preferred_genre: techno\n"
    cache = _make_cache(body, profile_section=section)
    padded = cache.padded_body()
    # Both parts present.
    assert section in padded
    assert padded.startswith(body)
    # Profile section appears AFTER body.
    assert padded.index(section) >= len(body)


def test_token_floor_still_respected_when_profile_short() -> None:
    """Combined body + profile < floor → pad block still appended."""
    short_body = "x" * 100  # ~25 token-proxy
    short_section = "\n\n# profile\n- x: y\n"
    cache = _make_cache(short_body, profile_section=short_section)
    padded = cache.padded_body()
    assert (len(padded) // 4) >= GEMINI_CACHE_TOKEN_FLOOR
    assert "vibemix-pad-block-do-not-edit-cache-key-stability" in padded


def test_token_floor_skipped_when_combined_above_floor() -> None:
    """Combined body + profile ≥ floor → no pad block needed."""
    long_body = "x" * (GEMINI_CACHE_TOKEN_FLOOR * 4 + 100)  # well above floor
    cache = _make_cache(long_body, profile_section="\n# p\n")
    padded = cache.padded_body()
    assert "vibemix-pad-block-do-not-edit-cache-key-stability" not in padded


def test_cache_key_stability_identical_inputs() -> None:
    """Cache-key stability invariant — same body + section → same padded_body."""
    body = "SYSPROMPT"
    section = "\n# profile-v1\n- genre: techno\n- bpm: 128-138\n"
    cache_a = _make_cache(body, profile_section=section)
    cache_b = _make_cache(body, profile_section=section)
    assert cache_a.padded_body() == cache_b.padded_body()


def test_padded_body_repeatable_within_one_instance() -> None:
    """Calling padded_body() twice returns the same string."""
    cache = _make_cache("BODY", profile_section="\n# p\n")
    assert cache.padded_body() == cache.padded_body()
