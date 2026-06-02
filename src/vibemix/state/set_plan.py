# SPDX-License-Identifier: Apache-2.0
"""Derived live progress through the latest saved set-prep pool.

The saved pool is a user-authored plan, not live proof. This module therefore
only derives bounded progress when the current audible deck resolves to a
track_id that is present in the pool. Off-plan, mixed-deck, low-confidence, or
last-slot states abstain.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from vibemix.library.prepared_pool import PreparedPool, PreparedPoolTrack
from vibemix.state.deck_state import DeckState

_AUDIBLE_PLAN_DECKS = frozenset({"A", "B"})


def derive_set_progress(
    pool: PreparedPool | None,
    *,
    audible_deck: object,
    deck_state: DeckState | None,
    min_deck_confidence: float,
) -> dict[str, object] | None:
    """Return bounded saved-pool progress for the current deck, or ``None``.

    The match is by citable deck ``track_id`` only. Title matching would make
    this look smarter while being less grounded; the live deck identity is the
    actual evidence source we can cite.
    """

    if pool is None or deck_state is None:
        return None
    side = _clean_deck(audible_deck)
    if side is None:
        return None

    decks = getattr(deck_state, "decks", None)
    if not isinstance(decks, Mapping):
        return None
    live_track = decks.get(side)
    if live_track is None:
        return None

    try:
        confidence = float(getattr(live_track, "confidence", 0.0) or 0.0)
    except (TypeError, ValueError):
        confidence = 0.0
    if confidence < min_deck_confidence:
        return None

    current_track_id = _clean_text(getattr(live_track, "track_id", None))
    if current_track_id is None:
        return None

    tracks = tuple(getattr(pool, "tracks", ()) or ())
    if len(tracks) < 2:
        return None

    current_index = _index_for_track_id(tracks, current_track_id)
    if current_index is None or current_index + 1 >= len(tracks):
        return None

    current_slot = tracks[current_index]
    next_slot = tracks[current_index + 1]
    next_track_id = _clean_text(getattr(next_slot, "track_id", None))
    if next_track_id is None or next_track_id == current_track_id:
        return None

    return {
        "source": "prepared_pool",
        "pool_name": _clean_text(getattr(pool, "name", None)) or "saved pool",
        "pool_path": str(getattr(pool, "json_path", "") or ""),
        "audible_deck": side,
        "confidence": round(confidence, 3),
        "current_track_id": current_track_id,
        "current_title": _clean_text(getattr(current_slot, "title", None))
        or _clean_text(getattr(live_track, "title", None)),
        "current_artist": _clean_text(getattr(current_slot, "artist", None)),
        "current_index": current_index,
        "total": len(tracks),
        "next_track_id": next_track_id,
        "next_title": _clean_text(getattr(next_slot, "title", None)),
        "next_artist": _clean_text(getattr(next_slot, "artist", None)),
    }


def _clean_deck(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    side = value.strip().upper()
    return side if side in _AUDIBLE_PLAN_DECKS else None


def _clean_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = " ".join(value.split())
    return text or None


def _index_for_track_id(
    tracks: tuple[PreparedPoolTrack, ...],
    track_id: str,
) -> int | None:
    for index, track in enumerate(tracks):
        if getattr(track, "track_id", None) == track_id:
            return index
    return None


__all__ = ["derive_set_progress"]
