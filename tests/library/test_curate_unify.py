# SPDX-License-Identifier: Apache-2.0
"""Phase 82 Plan 01 (Wave 0) — CURATE-02 taste seam scaffolds + the
one-mechanism / no-MusicState / lens-shared / no-title-leak / surfaces-import
real-green pins.

Phase 82 closes the diamond: the library/Viber **curator** and the live
**co-host** become two facets of ONE mind. CURATE-02 shares the taste layer —
the long-term DJ **profile/** reaches BOTH curator backends (gemini =
``library/agent.py``, codex = ``library/codex_curate.py``) via the SAME
privacy-safe vehicle the co-host already uses (``render_profile_for_cache``).

Three tiers (the documented Phase 77-81 Wave-0 convention):

  * CURATE-02 taste scaffolds (a, c) — real-green as of Plan 02: the curator
    system instruction now carries a profile-derived token because Plan 02
    appended ``_taste_hint()`` at the SEAM #2 build sites (agent.py
    _system_instruction/_interactive + codex_curate.py _system_prompt). The
    xfail markers flipped.
  * Real-green "must-stay-true" pins (b cold-path, d no-title-leak, e
    lens-shared, f no-MusicState, g surfaces-import) — PASS today and must STAY
    green through Plan 02.

Honest green: NO genai.Client, NO GEMINI_API_KEY, NO package install. The
backends cache the built instruction keyed by lens, so every built-instruction
assertion resets the relevant module-cache globals first.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

import vibemix.library.agent as agent_mod
import vibemix.library.codex_curate as codex_mod

REPO = Path(__file__).resolve().parents[2]

# A populated, allowlisted profile (the CURATE-02 taste payload). Only the five
# allowlisted fields — NO track titles, NO free-form (Pitfall 4 / P51 privacy).
_PROFILE_GENRE = "hardtechno"
_PROFILE = {
    "preferred_genre": _PROFILE_GENRE,
    "avg_session_duration": 90,
    "mix_style_tags": ["long-blends", "rolling"],
    "tempo_preference_bin": "140-150",
    "event_type_response_preferences": {},
}


def _reset_gemini_caches() -> None:
    """Reset the gemini backend instruction caches so a re-build is exercised."""
    agent_mod._SYSTEM_INSTRUCTION_CACHE = None
    agent_mod._SYSTEM_INSTRUCTION_LENS = None
    agent_mod._INTERACTIVE_SYSTEM_INSTRUCTION_CACHE = None
    agent_mod._INTERACTIVE_SYSTEM_INSTRUCTION_LENS = None


def _reset_codex_caches() -> None:
    """Reset the codex backend prompt cache so a re-build is exercised."""
    codex_mod._SYSTEM_PROMPT_CACHE = None
    codex_mod._SYSTEM_PROMPT_LENS = None


def _patch_profile(monkeypatch, profile) -> None:
    """Point BOTH backends' lazy ``load_profile`` import at a fixed profile.

    The seam lazy-imports ``from vibemix.profile import load_profile, ...``
    inside ``_taste_hint`` (Pattern 1), so we patch the source module attribute
    that the lazy import resolves to.
    """
    import vibemix.profile as profile_mod

    monkeypatch.setattr(profile_mod, "load_profile", lambda: profile, raising=True)


# ---------------------------------------------------------------------------
# (a) CURATE-02 taste — gemini backend (xfail-strict until Plan 02)
# ---------------------------------------------------------------------------


def test_curator_taste_hint_present_when_profile_set(tmp_path, monkeypatch) -> None:
    """With a populated profile, the gemini curator instruction carries a taste token.

    Today the built ``_system_instruction()`` is ``build_curator_instruction(lens)
    + RULES`` with NO profile bias → the preferred_genre token is ABSENT → RED.
    Plan 02 appends ``render_profile_for_cache(load_profile())`` → token present.
    """
    import vibemix.runtime.config_store as cs_mod

    target = tmp_path / "config.json"
    monkeypatch.setattr(cs_mod, "config_path", lambda: target)
    _patch_profile(monkeypatch, _PROFILE)

    _reset_gemini_caches()
    try:
        voice = agent_mod._system_instruction()
        assert _PROFILE_GENRE in voice, (
            "CURATE-02: the curator instruction must carry the profile-derived "
            "taste hint (preferred_genre) when a profile is set"
        )
    finally:
        _reset_gemini_caches()


# ---------------------------------------------------------------------------
# (b) Cold-path identity — REAL-GREEN must-stay-true guard
# ---------------------------------------------------------------------------


def test_curator_taste_cold_path_identical_when_no_profile(tmp_path, monkeypatch) -> None:
    """With NO profile (consent-OFF default), the cold path is byte-identical.

    REAL-GREEN: the taste seam must be ADDITIVE — when ``load_profile()`` is
    ``None`` the built instruction equals ``build_curator_instruction(lens) +
    "\\n" + _RULES_BLOCK`` (today's exact cold path). This must STAY true through
    Plan 02 (Pattern 2: per-surface default-when-unset, no bias on empty).
    """
    import vibemix.runtime.config_store as cs_mod
    from vibemix.prompts.matrix import build_curator_instruction

    target = tmp_path / "config.json"
    monkeypatch.setattr(cs_mod, "config_path", lambda: target)
    _patch_profile(monkeypatch, None)  # consent-OFF / absent profile

    _reset_gemini_caches()
    try:
        voice = agent_mod._system_instruction()
        expected = build_curator_instruction("tutor") + "\n" + agent_mod._RULES_BLOCK
        assert voice == expected, (
            "CURATE-02: with no profile the curator cold path must be "
            "byte-identical to today's build_curator_instruction + RULES"
        )
    finally:
        _reset_gemini_caches()


# ---------------------------------------------------------------------------
# (c) CURATE-02 taste reaches the codex backend too (xfail-strict — acid test)
# ---------------------------------------------------------------------------


def test_taste_hint_reaches_codex_backend(tmp_path, monkeypatch) -> None:
    """SEAM #2 reaches BOTH backends — the codex prompt carries the taste token.

    The CURATE acid test: neither backend may be orphaned. Today the codex
    ``_system_prompt()`` has no profile bias → RED; Plan 02 appends the same
    ``_taste_hint()`` at codex_curate.py:125 → token present.
    """
    import vibemix.runtime.config_store as cs_mod

    target = tmp_path / "config.json"
    monkeypatch.setattr(cs_mod, "config_path", lambda: target)
    _patch_profile(monkeypatch, _PROFILE)

    _reset_codex_caches()
    try:
        prompt = codex_mod._system_prompt()
        assert _PROFILE_GENRE in prompt, (
            "CURATE-02: the codex curator prompt must carry the profile-derived "
            "taste hint — both backends share the taste layer (acid test)"
        )
    finally:
        _reset_codex_caches()


# ---------------------------------------------------------------------------
# (d) No track-title leak — REAL-GREEN privacy pin (ASVS V5 / T-82-01)
# ---------------------------------------------------------------------------


def test_taste_hint_no_track_titles_leak() -> None:
    """``render_profile_for_cache`` emits ONLY the 5 allowlisted fields — no titles.

    REAL-GREEN: even if a profile dict smuggles extra title-shaped keys, the
    renderer never serializes them — only preferred_genre, avg_session_duration,
    mix_style_tags, tempo_preference_bin, event_response_preferences cross the
    boundary. Pins T-82-01 (Information Disclosure) and STAYS green through Plan 02.
    """
    from vibemix.profile import render_profile_for_cache

    leaky = dict(_PROFILE)
    # Would-be leaks: track titles / library contents / free-form. NONE may cross.
    leaky["recent_tracks"] = ["Charlotte de Witte - Doppler", "Amelie Lens - In My Mind"]
    leaky["favorite_artist"] = "Secret Artist Name"
    leaky["free_form_note"] = "played at warehouse rave last friday"

    rendered = render_profile_for_cache(leaky)

    for forbidden in (
        "Charlotte de Witte",
        "Doppler",
        "Amelie Lens",
        "In My Mind",
        "Secret Artist Name",
        "warehouse rave",
        "recent_tracks",
        "favorite_artist",
        "free_form_note",
    ):
        assert forbidden not in rendered, (
            f"T-82-01 privacy leak: {forbidden!r} crossed into the curator hint; "
            "only the 5 allowlisted fields may render"
        )
    # The allowlisted taste signal IS present (the renderer works).
    assert _PROFILE_GENRE in rendered


# ---------------------------------------------------------------------------
# (e) Lens shared across BOTH backends — REAL-GREEN regression pin (Phase 79 DONE)
# ---------------------------------------------------------------------------


def test_lens_shared_across_both_backends(tmp_path, monkeypatch) -> None:
    """BOTH backends' ``_shared_lens`` resolve the SAME ``read_shared_lens`` value.

    REAL-GREEN regression pin (Pitfall 1 — the persona half is ALREADY shared,
    Phase 79). Setting ``extra["lens"]="critique"`` once makes BOTH the gemini
    and codex curator backends return ``"critique"`` — proving one shared
    selection drives both surfaces. This forbids re-implementing the lens seam.
    """
    import vibemix.runtime.config_store as cs_mod

    target = tmp_path / "config.json"
    monkeypatch.setattr(cs_mod, "config_path", lambda: target)
    store = cs_mod.ConfigStore()
    store.extra["lens"] = "critique"
    cs_mod.save_config(store)

    assert agent_mod._shared_lens() == "critique"
    assert codex_mod._shared_lens() == "critique"


# ---------------------------------------------------------------------------
# (f) Curator does NOT import the live MusicState path — REAL-GREEN (invariant #1)
# ---------------------------------------------------------------------------


def test_curator_does_not_import_musicstate() -> None:
    """The curator path never imports the live ``MusicState`` / ``EventDetector`` object.

    REAL-GREEN (invariant #1, single-writer): the shared perception is the
    LIBRARY representation (genre_prototypes + toolset features over the offline
    embedding store), NEVER the live ``MusicState`` object. A fresh interpreter
    binds the three curator modules and asserts neither ``MusicState`` nor
    ``EventDetector`` is reachable as a curator-module attribute — i.e. the
    curator never imports the live state OBJECT into its own namespace.

    Why an attribute check, not a ``sys.modules`` scan: ``toolset.py`` imports
    ``from vibemix.state import harmonics`` (a pure Camelot helper), and
    ``state/__init__`` eagerly binds ``MusicState``/``EventDetector`` as a side
    effect — so the module is transitively present in ``sys.modules`` regardless.
    Invariant #1 is about the curator not READING/WRITING the live object, which
    is precisely what ``test_no_live_path_import``'s FORBIDDEN_NAMES static gate
    pins: the curator must not import the *name* into its module namespace.
    Plan 02's lazy genre/profile reads must keep this true.
    """
    script = (
        "import vibemix.library.toolset as t\n"
        "import vibemix.library.agent as a\n"
        "import vibemix.library.codex_curate as c\n"
        "bad = []\n"
        "for mod in (t, a, c):\n"
        "    for name in ('MusicState', 'EventDetector'):\n"
        "        obj = getattr(mod, name, None)\n"
        "        if obj is not None and isinstance(obj, type):\n"
        "            bad.append(mod.__name__ + '.' + name)\n"
        "print('LEAKED:' + ','.join(bad) if bad else 'CLEAN')\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        cwd=REPO,
        env={**os.environ, "PYTHONPATH": str(REPO / "src")},
    )
    assert result.stdout.strip() == "CLEAN", (
        "invariant #1 breach: a curator module imported the live MusicState/"
        f"EventDetector object into its namespace. stdout={result.stdout!r}; "
        f"stderr={result.stderr!r}"
    )


# ---------------------------------------------------------------------------
# (g) Existing surfaces still import — REAL-GREEN regression smoke pin
# ---------------------------------------------------------------------------


def test_existing_surfaces_still_import() -> None:
    """The existing curate / Telegram / pill / MCP surfaces stay importable.

    REAL-GREEN: a cheap smoke pin that Plan 02's wiring does not break the
    surfaces (the deeper behavioral pins live in their own test files which
    Plan 02 must keep green). CURATE SC #3 — nothing orphaned.
    """
    from vibemix.library.agent import ViberAgent  # noqa: F401
    from vibemix.library.mcp_server import build_toolset  # noqa: F401
    from vibemix.library.next_suggestion import next_suggestion  # noqa: F401

    import vibemix.library.telegram_bridge as _tg  # noqa: F401

    assert callable(build_toolset)
    assert callable(next_suggestion)
    assert isinstance(ViberAgent, type)
