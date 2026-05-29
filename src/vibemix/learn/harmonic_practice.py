# SPDX-License-Identifier: Apache-2.0
"""Library-grounded harmonic practice for Learn.

The Camelot lesson should not feel like a diagram lesson when the DJ has a
crate. This module picks one deterministic, compatible pair from the user's
library so Course 2 can teach melody through music the user already owns.
It does not play audio, open a new socket, or ask a model to do key math.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from vibemix.library.track_relation import TrackRelation, compute_relation
from vibemix.state.harmonics import to_camelot

_MAX_TRACKS_TO_SCAN = 200
_MAX_DISPLAY_NAME_CHARS = 54
_MAX_PROMPT_CHARS = 260


@dataclass(frozen=True, slots=True)
class HarmonicPracticeTrack:
    """One library track reduced to the facts the lesson may voice."""

    track_id: str
    title: str
    artist: str
    bpm: float | None
    camelot: str
    rating: int = 0
    play_count: int = 0

    def display_name(self, *, max_chars: int = _MAX_DISPLAY_NAME_CHARS) -> str:
        """Return a compact, learner-facing track label."""
        title = self.title.strip() or self.track_id
        artist = self.artist.strip()
        name = f"{artist} - {title}" if artist else title
        if len(name) <= max_chars:
            return name
        return name[: max(0, max_chars - 3)].rstrip() + "..."


@dataclass(frozen=True, slots=True)
class HarmonicPracticePair:
    """A deterministic practice pair chosen from the user's library."""

    source: HarmonicPracticeTrack
    target: HarmonicPracticeTrack
    relation: TrackRelation
    score: float

    @property
    def why(self) -> str:
        """Return the human harmonic/tempo relation phrase."""
        return self.relation.why()


def pick_harmonic_practice_pair(
    library: Any,
    *,
    seed_track_id: str | None = None,
    max_tracks: int = _MAX_TRACKS_TO_SCAN,
) -> HarmonicPracticePair | None:
    """Pick one compatible Camelot pair from a Rekordbox-like library.

    ``seed_track_id`` is optional future wiring for "pick a track you love."
    Without a seed, the chooser favors tracks the user appears to care about
    (rating/play count), then picks the strongest harmonic + tempo relation.
    Missing keys stay honest: no key, no pair.
    """
    tracks = _practice_tracks(library)
    if not tracks:
        return None

    if seed_track_id:
        seed = str(seed_track_id)
        sources = [track for track in tracks if track.track_id == seed]
        if not sources:
            return None
    else:
        sources = sorted(tracks, key=_familiarity_sort_key)[:max_tracks]
    candidates = sorted(tracks, key=_familiarity_sort_key)[:max_tracks]

    best: HarmonicPracticePair | None = None
    for source in sources:
        for target in candidates:
            if source.track_id == target.track_id:
                continue
            relation = compute_relation(
                src_track_id=source.track_id,
                dst_track_id=target.track_id,
                cosine=0.0,
                src_camelot=source.camelot,
                dst_camelot=target.camelot,
                src_bpm=source.bpm,
                dst_bpm=target.bpm,
            )
            if not relation.harmonic_compatible:
                continue
            if "tempo_jump" in relation.tempo_flags:
                continue
            pair = HarmonicPracticePair(
                source=source,
                target=target,
                relation=relation,
                score=_pair_score(source, target, relation),
            )
            if best is None or _pair_sort_key(pair) < _pair_sort_key(best):
                best = pair
    return best


def build_harmonic_practice_prompt(pair: HarmonicPracticePair) -> str:
    """Render the Course 2 library prompt, bounded for the tutor dock."""
    source = pair.source.display_name()
    target = pair.target.display_name()
    why = pair.why or f"{pair.source.camelot}->{pair.target.camelot}"
    text = (
        f"your library pair: {source} into {target}. {why}. "
        "load the first, then tap continue."
    )
    if len(text) <= _MAX_PROMPT_CHARS:
        return text
    compact = (
        f"your library pair: {pair.source.camelot} into {pair.target.camelot}. "
        "load the first track, then tap continue."
    )
    return compact[:_MAX_PROMPT_CHARS].rstrip()


def harmonic_practice_citations(
    pair: HarmonicPracticePair,
    registry: Any | None,
) -> tuple[str, ...]:
    """Return resolvable ``[track:<id>]`` citations for the picked pair."""
    if registry is None:
        return ()
    citations: list[str] = []
    for track in (pair.source, pair.target):
        track_id = track.track_id
        if not _safe_citation_body(track_id):
            continue
        try:
            if not registry.has("track", track_id, 0.0, tol=0.5):
                continue
        except Exception:
            continue
        citations.append(f"[track:{track_id}]")
    return tuple(citations)


def _practice_tracks(library: Any) -> list[HarmonicPracticeTrack]:
    raw_tracks = getattr(library, "tracks", None)
    if isinstance(raw_tracks, dict):
        rows = list(raw_tracks.values())
    elif isinstance(raw_tracks, (list, tuple)):
        rows = list(raw_tracks)
    else:
        return []

    tracks: list[HarmonicPracticeTrack] = []
    for fallback_index, row in enumerate(rows, start=1):
        track = _practice_track(row, fallback_index=fallback_index)
        if track is not None:
            tracks.append(track)
    return tracks


def _practice_track(row: Any, *, fallback_index: int) -> HarmonicPracticeTrack | None:
    track_id = str(getattr(row, "track_id", "") or f"track_{fallback_index}").strip()
    if not track_id:
        return None
    camelot = getattr(row, "camelot", None)
    if not camelot:
        camelot = to_camelot(str(getattr(row, "key", "") or ""))
    if not camelot:
        return None
    bpm = _finite_positive_or_none(getattr(row, "bpm", None))
    return HarmonicPracticeTrack(
        track_id=track_id,
        title=str(getattr(row, "title", "") or track_id),
        artist=str(getattr(row, "artist", "") or ""),
        bpm=bpm,
        camelot=camelot,
        rating=max(0, int(getattr(row, "rating", 0) or 0)),
        play_count=max(0, int(getattr(row, "play_count", 0) or 0)),
    )


def _finite_positive_or_none(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number) or number <= 0:
        return None
    return number


def _familiarity_sort_key(track: HarmonicPracticeTrack) -> tuple[int, int, str, str, str]:
    return (
        -track.rating,
        -track.play_count,
        track.artist.lower(),
        track.title.lower(),
        track.track_id,
    )


def _pair_score(
    source: HarmonicPracticeTrack,
    target: HarmonicPracticeTrack,
    relation: TrackRelation,
) -> float:
    familiarity = min(1.0, (source.rating + target.rating) / 10.0)
    play_memory = min(1.0, (source.play_count + target.play_count) / 50.0)
    return (
        relation.harmonic * 0.62
        + relation.tempo * 0.24
        + familiarity * 0.09
        + play_memory * 0.05
    )


def _pair_sort_key(pair: HarmonicPracticePair) -> tuple[float, str, str]:
    return (
        -pair.score,
        pair.source.display_name().lower(),
        pair.target.display_name().lower(),
    )


def _safe_citation_body(value: str) -> bool:
    return bool(value) and not any(ch.isspace() or ch in ",]" for ch in value)


__all__ = [
    "HarmonicPracticePair",
    "HarmonicPracticeTrack",
    "build_harmonic_practice_prompt",
    "harmonic_practice_citations",
    "pick_harmonic_practice_pair",
]
