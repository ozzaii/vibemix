# SPDX-License-Identifier: Apache-2.0
"""Read saved playlist/set-prep pools as grounded runtime context."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from vibemix.library.create_playlist import PLAYLISTS_DIR

MIN_PREPARED_POOL_TRACKS = 5


@dataclass(frozen=True, slots=True)
class PreparedPoolTrack:
    """One grounded row from a saved playlist JSON artifact."""

    track_id: str
    title: str | None = None
    artist: str | None = None
    bpm: float | None = None
    key: str | None = None

    def display_name(self) -> str:
        """Return a compact display name suitable for tutor copy."""
        if self.artist and self.title:
            return f"{self.artist} - {self.title}"
        if self.title:
            return self.title
        if self.artist:
            return self.artist
        return self.track_id


@dataclass(frozen=True, slots=True)
class PreparedPool:
    """A validated latest saved pool Learn and live suggestions may reference."""

    name: str
    created_at: float
    json_path: Path
    tracks: tuple[PreparedPoolTrack, ...]

    @property
    def track_count(self) -> int:
        return len(self.tracks)


def load_latest_prepared_pool(
    *,
    playlists_dir: Path | None = None,
    min_tracks: int = MIN_PREPARED_POOL_TRACKS,
) -> PreparedPool | None:
    """Return the newest valid saved pool, or ``None``."""
    base = playlists_dir if playlists_dir is not None else PLAYLISTS_DIR
    try:
        paths = tuple(base.glob("*.json"))
    except OSError:
        return None

    candidates: list[PreparedPool] = []
    for path in paths:
        pool = _load_pool_file(path, min_tracks=min_tracks)
        if pool is not None:
            candidates.append(pool)
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda pool: (
            pool.created_at,
            _mtime_or_zero(pool.json_path),
            str(pool.json_path),
        ),
    )


def build_prepared_pool_prompt(pool: PreparedPool, *, max_chars: int = 260) -> str:
    """Build the deterministic tutor line for an available prepared pool."""
    first = _clip(pool.tracks[0].display_name(), 58)
    second = _clip(pool.tracks[1].display_name(), 58)
    name = _clip(pool.name, 52)
    text = (
        f"latest saved pool: {name}, {pool.track_count} tracks. "
        f"start with {first}; load {second} on the other deck."
    )
    return _clip(text, max_chars)


def next_track_id_after(pool: PreparedPool, current_track_id: str) -> str | None:
    """Return the next planned track id after ``current_track_id``."""
    current = current_track_id.strip() if isinstance(current_track_id, str) else ""
    if not current:
        return None
    for index, track in enumerate(pool.tracks):
        if track.track_id != current:
            continue
        if index + 1 >= len(pool.tracks):
            return None
        target = pool.tracks[index + 1].track_id
        return target if target and target != current else None
    return None


def _load_pool_file(path: Path, *, min_tracks: int) -> PreparedPool | None:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(raw, dict):
        return None
    tracks_raw = raw.get("tracks")
    if not isinstance(tracks_raw, list):
        return None
    tracks = tuple(
        track
        for row in tracks_raw
        if isinstance(row, dict)
        for track in (_coerce_track(row),)
        if track is not None
    )
    if len(tracks) < min_tracks:
        return None

    name = _non_empty_str(raw.get("name")) or path.stem
    created_at = _float_or_none(raw.get("created_at"))
    if created_at is None:
        created_at = _mtime_or_zero(path)
    return PreparedPool(
        name=name,
        created_at=created_at,
        json_path=path,
        tracks=tracks,
    )


def _coerce_track(row: dict[str, Any]) -> PreparedPoolTrack | None:
    track_id = _non_empty_str(row.get("track_id"))
    if track_id is None:
        return None
    return PreparedPoolTrack(
        track_id=track_id,
        title=_non_empty_str(row.get("title")),
        artist=_non_empty_str(row.get("artist")),
        bpm=_positive_float_or_none(row.get("bpm")),
        key=_non_empty_str(row.get("key")),
    )


def _non_empty_str(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = " ".join(value.split())
    return text or None


def _float_or_none(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _positive_float_or_none(value: Any) -> float | None:
    number = _float_or_none(value)
    if number is None or number <= 0:
        return None
    return number


def _mtime_or_zero(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except OSError:
        return 0.0


def _clip(text: str, limit: int) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= limit:
        return normalized
    if limit <= 3:
        return normalized[:limit]
    return normalized[: limit - 3].rstrip() + "..."


__all__ = [
    "MIN_PREPARED_POOL_TRACKS",
    "PreparedPool",
    "PreparedPoolTrack",
    "build_prepared_pool_prompt",
    "load_latest_prepared_pool",
    "next_track_id_after",
]
