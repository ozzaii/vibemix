# SPDX-License-Identifier: Apache-2.0
"""DeckState / DeckTrack — the embedded per-deck state model (Phase 59 DECK-01).

``DeckState`` lives as a default-empty field of ``MusicState`` (NOT a sibling
object) so every existing consumer already receives it via the single source of
truth and there is zero read-side signature churn (Pattern 1).

Honest-default contract (mirrors ``library.rekordbox.TrackEntry``'s
"typed-empties-on-absence" shape — ``bpm=0.0`` not ``None``): a bare
``DeckTrack`` carries NO key/camelot/bpm/energy and ``source="unknown"``. There
is no false-confident default key BY CONSTRUCTION — a deck reads as honest
unknown until a source resolves it above its confidence floor.

Single-writer rule: the deck poller (Plan 59-02+) writes its OWN holder; only
``state_refresh_loop._tick_once`` copies ``deck_source.snapshot()`` into
``MusicState.deck_state`` under ``state._lock`` (DECK-04). The ``camelot`` field
is populated by ``harmonics.to_camelot`` inside that same lock batch.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DeckTrack:
    """The currently-loaded track on a single deck.

    Field set is INTENTIONALLY narrow and refined against the verified
    Rekordbox XML key format: ``key`` is the RAW tag the source gives
    (``"Am"`` / ``"F#m"``), ``camelot`` is the normalized code the coach
    reasons on (``"8A"``), ``open_key`` is the open-key form for honesty/UI.
    Every harmonic field defaults to a typed empty so an unresolved deck is
    never a fabricated key.
    """

    title: str | None = None  # resolved track label
    track_id: str | None = None  # RekordboxLibrary TrackEntry.track_id — feeds [track:<id>]
    bpm: float = 0.0  # from source metadata (AverageBpm), NOT audio autocorr
    key: str | None = None  # RAW tag as the source gives it ("Am", "F#m")
    camelot: str | None = None  # normalized via harmonics.to_camelot() ("8A", "11A")
    open_key: str | None = None  # open-key form ("1m"/"1d") for honesty/UI
    energy: int | None = None  # 1..10 if source exposes it (rekordbox), else None
    loaded_at: float = 0.0
    confidence: float = 0.0  # 0..1 — how sure we are this deck holds this track
    # "rekordbox_xml" | "folder_cache" | "screen_vision" | "numpy_key" |
    # "nowplaying" | "unknown"
    source: str = "unknown"


@dataclass
class DeckState:
    """Per-side deck-state map embedded in ``MusicState``.

    ``decks`` defaults to an empty dict so an empty ``DeckState`` serializes to
    nothing in ``evidence_line`` (golden-equivalence — Pitfall 5).
    ``source_status`` is a bounded provenance/debug map from the read-only deck
    poller: why title→deck identity did or did not resolve this tick. It is not
    a track identity and must never be treated as deck proof by itself.
    """

    decks: dict[str, DeckTrack] = field(default_factory=dict)  # {"A": DeckTrack, "B": ...}
    updated_at: float = 0.0
    source_status: dict[str, str] = field(default_factory=dict)
