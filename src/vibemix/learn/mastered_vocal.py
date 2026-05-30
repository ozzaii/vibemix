# SPDX-License-Identifier: Apache-2.0
"""SURF-03 — the single, rare, earned "Mastered" unlock vocal selection.

The Earned Wall is a read-only render; this module holds the ONE place the mastery
spine ever speaks. It is pure selection logic + a hand-authored copy bank loaded from
``vocals/mastered_vocals.json``. The copy lives OUTSIDE ``transcripts/`` (that dir's
inventory contract claims every JSON as a lesson fixture); the same anti-slop gate is
applied by ``test_mastered_vocal_fires_once.py`` — every line is scanned against the
tutor-slop blocklist AND the em-dash-glue rule, exactly as the lesson transcripts are.

Anti-slop contract:

  * The copy is HAND-AUTHORED JSON, never free LLM generation (a generated
    "achievement unlocked!" line is the exact gamification slop v11.0 forbids).
  * :func:`mastered_unlock_line` fires EXACTLY ONCE per skill — only on the
    not-mastered→mastered FLIP. Already-mastered (a 4th/5th demo) is silent;
    Competent / partial fill is silent. Fire-once is by construction: only the
    flip is non-None, so a re-call after the flip returns ``None``.
  * Final tone is a KAAN-ACTION ear-pass (``§EARNED-MASTERED-VOCAL-EAR``): real
    friend marking a genuinely-earned moment, not a scripted reward chime.

Import-light by design (stdlib + a single fixture read) so it can sit on the
``learn/`` island and be called from the live credit site without dragging in the
co-host stack.
"""
from __future__ import annotations

import json
from pathlib import Path

_FIXTURE = Path(__file__).resolve().parent / "vocals" / "mastered_vocals.json"

# Honest fallback if the fixture is somehow unreadable (never raise into the
# reaction loop). The fixture is the single source on disk; this only guards a
# packaging accident.
_FALLBACK: dict[str, str] = {
    "_default": "That one was real, and it was yours. You earned that in a live set.",
}


def _load() -> dict[str, str]:
    try:
        data = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return dict(_FALLBACK)
    if not isinstance(data, dict) or "_default" not in data:
        return dict(_FALLBACK)
    # Keep only string values (defensive — the slop gate scans the same file).
    return {k: v for k, v in data.items() if isinstance(v, str)}


# Loaded once at import (the copy is static). Public so the fire-once test can
# assert it mirrors the on-disk fixture (single source).
MASTERED_VOCALS: dict[str, str] = _load()


def mastered_unlock_line(
    skill_id: str, *, was_mastered: bool, now_mastered: bool
) -> str | None:
    """The hand-authored line to speak IFF ``skill_id`` JUST flipped to Mastered.

    Returns the per-skill copy (falling back to ``_default`` for an unknown id) only
    on the not-mastered→mastered transition; ``None`` in every other case
    (already-mastered, no-flip, the impossible demotion). The caller captures
    ``was_mastered`` BEFORE crediting and ``now_mastered`` after, then routes a
    non-None return through the existing co-host fixed-text path exactly once.
    """
    if was_mastered or not now_mastered:
        return None
    return MASTERED_VOCALS.get(skill_id) or MASTERED_VOCALS["_default"]
