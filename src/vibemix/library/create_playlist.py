# SPDX-License-Identifier: Apache-2.0
"""create_playlist — the Viber tool surface's single validated write.

Phase 1's only persistence path. Exports a NEUTRAL playlist (M3U + JSON) to
``~/.cache/vibemix/playlists/`` — deliberately NOT a Rekordbox-XML write-back
(the master.db-write-unsafe problem; keep to neutral formats per design §6).

Grounding (Cardinal Invariant #2 applied to the agent): EVERY ``track_id`` is
re-validated against the live library via ``RekordboxLibrary.lookup_by_id``.
Unknown ids are dropped and reported in ``dropped_ids`` — a playlist can never
reference a track the library does not contain. The toolset-side seen-set gate
is the first line; this re-check against the authoritative library is the
second.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from vibemix.library.rekordbox import RekordboxLibrary

PLAYLISTS_DIR = Path.home() / ".cache" / "vibemix" / "playlists"

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slugify(name: str) -> str:
    slug = _SLUG_RE.sub("-", name.strip().lower()).strip("-")
    return slug or "playlist"


@dataclass(slots=True)
class PlaylistResult:
    """A persisted playlist + the validation outcome."""

    name: str
    track_ids: list[str]  # validated, in order
    m3u_path: Path
    json_path: Path
    dropped_ids: list[str] = field(default_factory=list)  # unknown → dropped

    def to_dict(self) -> dict:
        d = asdict(self)
        d["m3u_path"] = str(self.m3u_path)
        d["json_path"] = str(self.json_path)
        return d


def create_playlist(
    library: RekordboxLibrary,
    name: str,
    track_ids: list[str],
    *,
    out_dir: Path | None = None,
) -> PlaylistResult:
    """Validate ``track_ids`` against ``library`` and persist M3U + JSON.

    Every id is checked with ``library.lookup_by_id``; unknown ids are dropped
    (reported in ``dropped_ids``) so the persisted playlist references only
    real tracks. De-dupes while preserving order.

    Raises:
        ValueError: if ``name`` is empty or NO id survives validation (an
            all-invalid request is a hard error, not a silent empty file).
    """
    if not name or not name.strip():
        raise ValueError("playlist name must be non-empty")

    validated: list[str] = []
    dropped: list[str] = []
    seen: set[str] = set()
    for tid in track_ids:
        if not isinstance(tid, str) or tid in seen:
            if isinstance(tid, str):
                continue  # silent de-dupe
            dropped.append(str(tid))
            continue
        if library.lookup_by_id(tid) is None:
            dropped.append(tid)
            continue
        validated.append(tid)
        seen.add(tid)

    if not validated:
        raise ValueError(
            "create_playlist: no valid track_ids survived library validation "
            f"(dropped {len(dropped)})"
        )

    base = out_dir if out_dir is not None else PLAYLISTS_DIR
    base.mkdir(parents=True, exist_ok=True)
    stem = f"{_slugify(name)}-{int(time.time())}"
    m3u_path = base / f"{stem}.m3u8"
    json_path = base / f"{stem}.json"

    # M3U (extended) — neutral, portable into most DJ software.
    m3u_lines = ["#EXTM3U"]
    payload_tracks = []
    for tid in validated:
        entry = library.lookup_by_id(tid)
        assert entry is not None  # validated above
        secs = round(entry.duration_s) if entry.duration_s else -1
        m3u_lines.append(f"#EXTINF:{secs},{entry.artist} - {entry.title}")
        m3u_lines.append(entry.filepath or "")
        payload_tracks.append(
            {
                "track_id": tid,
                "title": entry.title,
                "artist": entry.artist,
                "bpm": entry.bpm if (entry.bpm and entry.bpm > 0) else None,
                "key": entry.key or None,
                "filepath": entry.filepath or None,
            }
        )
    m3u_path.write_text("\n".join(m3u_lines) + "\n", encoding="utf-8")

    json_path.write_text(
        json.dumps(
            {
                "name": name,
                "created_at": time.time(),
                "track_count": len(validated),
                "dropped_ids": dropped,
                "tracks": payload_tracks,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    return PlaylistResult(
        name=name,
        track_ids=validated,
        m3u_path=m3u_path,
        json_path=json_path,
        dropped_ids=dropped,
    )


__all__ = ["PLAYLISTS_DIR", "PlaylistResult", "create_playlist"]
