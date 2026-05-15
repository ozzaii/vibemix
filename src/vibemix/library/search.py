# SPDX-License-Identifier: Apache-2.0
"""Phase 28 Plan 03 — natural-language vibe-search.

User-facing flow: ``vibemix library search "driving acid techno around 138 BPM"``.

The 24h LRU cache key is ``sha256(query_text + library_snapshot_hash)`` —
re-importing the library invalidates all stale cached results without
explicit user action (snapshot_hash changes when the track set changes).

Co-locates the cache table in Plan 01's ``embeddings.db`` so a single
sqlite file owns all library cache state.
"""

from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from vibemix.library.embed import EMBED_CACHE_DB_PATH, LibraryEmbedder
from vibemix.library.rekordbox import RekordboxLibrary
from vibemix.library.store import LibraryStore

logger = logging.getLogger(__name__)

# 24h TTL — query results rotate daily even when nothing else changes.
QUERY_CACHE_TTL = 86400
QUERY_CACHE_TABLE = "query_cache"


def _open_query_cache(
    db_path: Path | None = None,
) -> sqlite3.Connection:
    """Open / init the query_cache table inside embeddings.db."""
    p = Path(db_path) if db_path else EMBED_CACHE_DB_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(p))
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS query_cache (
            key TEXT PRIMARY KEY,
            query_text TEXT NOT NULL,
            result_json TEXT NOT NULL,
            ts REAL NOT NULL
        )
        """
    )
    conn.commit()
    return conn


@dataclass(frozen=True, slots=True)
class VibeSearchResult:
    """A single match in a vibe-search response."""

    track_id: str
    title: str
    artist: str
    bpm: float | None
    confidence: float  # cosine in [0, 1], rounded to 4 decimals
    snippet: str  # human-readable, max 80 chars

    def to_dict(self) -> dict:
        return asdict(self)


def _format_snippet(title: str, artist: str, bpm: float | None) -> str:
    if bpm is not None and bpm > 0:
        s = f"{title} — {artist} @ {int(round(bpm))} BPM"
    else:
        s = f"{title} — {artist}"
    return s[:80]


def vibe_search(
    embedder: LibraryEmbedder,
    store: LibraryStore,
    library: RekordboxLibrary,
    query: str,
    k: int = 10,
    cache_db: sqlite3.Connection | None = None,
) -> tuple[list[VibeSearchResult], bool]:
    """Run a natural-language vibe-search query.

    Returns ``(matches, cache_hit)``. ``cache_hit`` is the truth value used
    by ``LibrarySearchResult`` IPC payload (Plan 09).

    Empty library short-circuits — no embed call, no API spend.
    """
    tracks = list(library.tracks)
    if not tracks:
        return [], False

    snapshot = store.snapshot_hash()
    cache_key = hashlib.sha256(
        f"{query}|{snapshot}".encode("utf-8")
    ).hexdigest()
    own_conn = cache_db is None
    conn = cache_db if cache_db is not None else _open_query_cache()
    try:
        row = conn.execute(
            "SELECT result_json, ts FROM query_cache WHERE key = ?",
            (cache_key,),
        ).fetchone()
        if row is not None:
            result_json, ts = row
            if (time.time() - float(ts)) < QUERY_CACHE_TTL:
                cached = json.loads(result_json)
                return (
                    [VibeSearchResult(**d) for d in cached],
                    True,
                )

        qvec = embedder.embed_query(query)
        topk = store.search(qvec, k=k)

        # Build track_id → TrackEntry lookup once per call.
        index = {t.track_id: t for t in tracks}
        out: list[VibeSearchResult] = []
        for tid, sim in topk:
            t = index.get(tid)
            if t is None:
                logger.warning(
                    "vibe_search: track_id %s in store but not in library "
                    "(reimport may have removed it); skipping",
                    tid,
                )
                continue
            confidence = round(min(max(float(sim), 0.0), 1.0), 4)
            out.append(
                VibeSearchResult(
                    track_id=tid,
                    title=t.title,
                    artist=t.artist,
                    bpm=t.bpm if (t.bpm and t.bpm > 0) else None,
                    confidence=confidence,
                    snippet=_format_snippet(t.title, t.artist, t.bpm),
                )
            )

        conn.execute(
            "INSERT OR REPLACE INTO query_cache "
            "(key, query_text, result_json, ts) VALUES (?, ?, ?, ?)",
            (
                cache_key,
                query,
                json.dumps([r.to_dict() for r in out]),
                time.time(),
            ),
        )
        conn.commit()
        return out, False
    finally:
        if own_conn:
            conn.close()


__all__ = [
    "QUERY_CACHE_TTL",
    "QUERY_CACHE_TABLE",
    "VibeSearchResult",
    "vibe_search",
]
