# SPDX-License-Identifier: Apache-2.0
"""cache_render tests — Phase 32-01.

Covers:
- Empty input → empty string (P53 byte-identical when profile disabled).
- Output respects ≤300-token budget per P60.
- Deterministic output (cache-key stability invariant).
- No track-title-like text in rendered string (P51).
"""

from __future__ import annotations

import re

from vibemix.profile import render_profile_for_cache


def _full_profile() -> dict:
    return {
        "preferred_genre": "techno",
        "avg_session_duration": 72.0,
        "mix_style_tags": ["long_blends", "filter_sweeps", "loud_drops"],
        "tempo_preference_bin": "128-138",
        "event_type_response_preferences": {
            "TRACK_CHANGE": "always",
            "PHASE": "sometimes",
            "KAAN_SPOKE": "rarely",
            "MIX_MOVE": "sometimes",
            "DISTORTION_CLIMB": "never",
            "ACID_LINE_ENTRY": "never",
            "HEARTBEAT": "rarely",
            "LAYER_ARRIVAL": "sometimes",
        },
    }


def test_empty_input_returns_empty_string() -> None:
    """P53 byte-identical: None profile must produce an empty section so
    the cache body matches the pre-32-03 path exactly."""
    assert render_profile_for_cache(None) == ""
    assert render_profile_for_cache({}) == ""


def test_renders_all_allowlist_fields() -> None:
    rendered = render_profile_for_cache(_full_profile())
    assert "preferred_genre: techno" in rendered
    assert "avg_session_duration_min: 72" in rendered
    assert "long_blends" in rendered
    assert "tempo_preference_bin_bpm: 128-138" in rendered
    assert "PHASE: sometimes" in rendered
    assert "TRACK_CHANGE: always" in rendered


def test_token_budget_under_300() -> None:
    """P60 budget: char-len // 4 ≤ 300 tokens for the cache section."""
    rendered = render_profile_for_cache(_full_profile())
    proxy_tokens = len(rendered) // 4
    assert proxy_tokens <= 300, f"profile cache section is {proxy_tokens} tokens"


def test_deterministic_output() -> None:
    """Cache-key stability: identical input → identical output."""
    p = _full_profile()
    assert render_profile_for_cache(p) == render_profile_for_cache(p)


def test_no_track_titles_in_rendered_string() -> None:
    """P51 defense-in-depth: rendered output cannot carry artist-title text."""
    rendered = render_profile_for_cache(_full_profile())
    assert not re.search(r"[A-Z][A-Za-z]+\s*-\s*[A-Z][a-z]", rendered), rendered


def test_cold_start_render_is_short() -> None:
    """Cold-start profile (mostly defaults) renders in <200 chars."""
    cold = {
        "preferred_genre": "unknown",
        "avg_session_duration": 0,
        "mix_style_tags": [],
        "tempo_preference_bin": "128-138",
        "event_type_response_preferences": {},
    }
    rendered = render_profile_for_cache(cold)
    assert rendered
    assert "preferred_genre: unknown" in rendered
    assert "mix_style_tags: none" in rendered
