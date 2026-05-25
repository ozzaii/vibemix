# SPDX-License-Identifier: Apache-2.0
"""SuggestionService — owns the pill "what's next" state, off the hot path.

Holds the session-scoped ``played_ids`` set and the latest computed suggestion
("the holder"), and recomputes it from the now-playing seed. It is deliberately
SEPARATE from ``MusicState`` (single-writer invariant: the state-refresh loop is
the only writer of ``MusicState`` — the suggestion is derived UI state, not
authoritative music state) and from the coach reaction loop (the compute runs
in an executor so it never blocks reactions).

Data flow:

    coach_loop sees a TRACK_CHANGE  →  service.compute_from_state(state)
        (in an executor — store read is sync)                │
                                                             ▼
    seed = deck_state.decks[audible_side] (track_id + camelot + bpm)
        → stored seed vector (cached, ~free) → next_suggestion(...)
        → service.current() holds the dict
                                                             │
    ws_broadcast reads service.current() at the serialize edge (PURE READ)
        → merges it onto the flat mascot frame as ``next_suggestion``
        → pill renders it.

Grounding: the engine (``next_suggestion``) only surfaces ids present in BOTH
the store and the live library, and returns ``None`` when nothing qualifies —
``current()`` then carries ``None`` (honest silence; the pill shows no
suggestion rather than a fabricated one).
"""

from __future__ import annotations

import logging
import threading
from typing import Any

from vibemix.library.next_suggestion import (
    next_suggestion,
    seed_vector_for_track_id,
)

logger = logging.getLogger(__name__)


def resolve_seed(state: Any) -> tuple[str, str | None, float | None] | None:
    """Resolve the now-playing seed (track_id, camelot, bpm) from MusicState.

    Reads the AUDIBLE deck's ``DeckTrack`` (``deck_state.decks[side]``). Returns
    ``None`` when there is no resolved ``track_id`` (folder-only library with no
    title match, no Rekordbox import, or nothing audible) — the caller then
    leaves the current suggestion untouched. PURE READ.
    """
    deck_state = getattr(state, "deck_state", None)
    decks = getattr(deck_state, "decks", None) or {}
    if not decks:
        return None

    side = getattr(state, "audible_deck", None)
    dt = decks.get(side) if side in decks else None
    if dt is None:
        # "mix" / "none" / unknown side → pick the highest-confidence deck.
        dt = max(decks.values(), key=lambda d: getattr(d, "confidence", 0.0))

    track_id = getattr(dt, "track_id", None)
    if not track_id:
        return None
    camelot = getattr(dt, "camelot", None)
    bpm = getattr(dt, "bpm", None)
    bpm = bpm if (bpm and bpm > 0.0) else None
    return track_id, camelot, bpm


class SuggestionService:
    """Thread-safe holder + recompute for the pill next-suggestion."""

    def __init__(self, store: Any, library: Any, *, k: int = 5) -> None:
        self._store = store
        self._library = library
        self._k = k
        self._lock = threading.Lock()
        self._played: set[str] = set()
        self._current: dict | None = None

    def current(self) -> dict | None:
        """Latest suggestion dict (or None). Called at the ws serialize edge."""
        with self._lock:
            return self._current

    def compute(
        self,
        seed_track_id: str,
        *,
        seed_camelot: str | None = None,
        seed_bpm: float | None = None,
    ) -> dict | None:
        """Recompute from a seed track_id. Marks the seed played, returns +
        stores the new suggestion dict (or None). Sync — run in an executor.
        """
        vec = seed_vector_for_track_id(self._store, seed_track_id)
        if vec is None:
            return self.current()  # seed not embedded → leave current as-is

        with self._lock:
            played = set(self._played)
            self._played.add(seed_track_id)

        try:
            sugg = next_suggestion(
                self._store,
                self._library,
                seed_vector=vec,
                seed_track_id=seed_track_id,
                played_ids=played,
                seed_camelot=seed_camelot,
                seed_bpm=seed_bpm,
                k=self._k,
            )
        except Exception as e:  # noqa: BLE001 — never let it break the loop
            logger.warning("[suggestion] compute failed: %s", e)
            return self.current()

        d = sugg.to_dict() if sugg is not None else None
        with self._lock:
            self._current = d
        return d

    def compute_from_state(self, state: Any) -> dict | None:
        """Resolve the seed from MusicState, then compute. No-op (returns the
        current suggestion) when the now-playing track_id can't be resolved."""
        seed = resolve_seed(state)
        if seed is None:
            return self.current()
        track_id, camelot, bpm = seed
        return self.compute(track_id, seed_camelot=camelot, seed_bpm=bpm)


__all__ = ["SuggestionService", "resolve_seed"]
