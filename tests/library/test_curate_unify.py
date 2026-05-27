# SPDX-License-Identifier: Apache-2.0
"""Codex Viber curator seam pins.

The product Library/Viber curator is local Codex over MCP. These tests keep the
shared taste/lens/privacy seams honest without importing the retired Gemini
``library.agent`` harness.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import vibemix.library.codex_curate as codex_mod

REPO = Path(__file__).resolve().parents[2]

_PROFILE_GENRE = "hardtechno"
_PROFILE = {
    "preferred_genre": _PROFILE_GENRE,
    "avg_session_duration": 90,
    "mix_style_tags": ["long-blends", "rolling"],
    "tempo_preference_bin": "140-150",
    "event_type_response_preferences": {},
}


def _reset_codex_caches() -> None:
    codex_mod._SYSTEM_PROMPT_CACHE = None
    codex_mod._SYSTEM_PROMPT_LENS = None


def _patch_profile(monkeypatch, profile, *, consent: bool = True) -> None:
    import vibemix.profile as profile_mod

    monkeypatch.setattr(profile_mod, "load_profile", lambda: profile, raising=True)
    monkeypatch.setattr(profile_mod, "load_consent", lambda: consent, raising=True)


def test_taste_hint_reaches_codex_backend(tmp_path, monkeypatch) -> None:
    import vibemix.runtime.config_store as cs_mod

    target = tmp_path / "config.json"
    monkeypatch.setattr(cs_mod, "config_path", lambda: target)
    _patch_profile(monkeypatch, _PROFILE)

    _reset_codex_caches()
    try:
        prompt = codex_mod._system_prompt()
        assert _PROFILE_GENRE in prompt
    finally:
        _reset_codex_caches()


def test_curator_taste_cold_path_identical_when_no_profile(tmp_path, monkeypatch) -> None:
    import vibemix.runtime.config_store as cs_mod
    from vibemix.prompts.matrix import build_curator_instruction

    target = tmp_path / "config.json"
    monkeypatch.setattr(cs_mod, "config_path", lambda: target)
    _patch_profile(monkeypatch, None)

    _reset_codex_caches()
    try:
        prompt = codex_mod._system_prompt()
        expected = build_curator_instruction("tutor") + " " + codex_mod._RULES_BLOCK
        assert prompt == expected
    finally:
        _reset_codex_caches()


def test_curator_taste_gated_off_when_consent_off(tmp_path, monkeypatch) -> None:
    import vibemix.runtime.config_store as cs_mod

    target = tmp_path / "config.json"
    monkeypatch.setattr(cs_mod, "config_path", lambda: target)
    _patch_profile(monkeypatch, _PROFILE, consent=False)

    _reset_codex_caches()
    try:
        prompt = codex_mod._system_prompt()
        assert _PROFILE_GENRE not in prompt
    finally:
        _reset_codex_caches()


def test_taste_hint_no_track_titles_leak() -> None:
    from vibemix.profile import render_profile_for_cache

    leaky = dict(_PROFILE)
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
        assert forbidden not in rendered
    assert _PROFILE_GENRE in rendered


def test_codex_lens_reads_shared_selection(tmp_path, monkeypatch) -> None:
    import vibemix.runtime.config_store as cs_mod

    target = tmp_path / "config.json"
    monkeypatch.setattr(cs_mod, "config_path", lambda: target)
    store = cs_mod.ConfigStore()
    store.extra["lens"] = "critique"
    cs_mod.save_config(store)

    assert codex_mod._shared_lens() == "critique"


def test_curator_does_not_import_musicstate() -> None:
    script = (
        "import vibemix.library.toolset as t\n"
        "import vibemix.library.codex_curate as c\n"
        "bad = []\n"
        "for mod in (t, c):\n"
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
    assert result.stdout.strip() == "CLEAN", result.stdout + result.stderr


def test_existing_product_surfaces_still_import() -> None:
    import vibemix.library.telegram_bridge as _tg  # noqa: F401
    from vibemix.library.codex_curate import chat_with_codex, curate_with_codex
    from vibemix.library.mcp_server import build_toolset
    from vibemix.library.next_suggestion import next_suggestion

    assert callable(build_toolset)
    assert callable(next_suggestion)
    assert callable(chat_with_codex)
    assert callable(curate_with_codex)
