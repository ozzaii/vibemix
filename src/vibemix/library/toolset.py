# SPDX-License-Identifier: Apache-2.0
"""LibraryToolset — the grounded tool core shared by every Viber backend.

This is the single implementation of the playlist-curation tool surface and,
critically, of the **grounding gate** (Cardinal Invariant #2). Both backends
reuse it verbatim so the anti-hallucination contract can never drift between
them:

* ``ViberAgent`` (``agent.py``) — the Gemini function-calling harness.
* ``mcp_server.py`` — the FastMCP STDIO server that exposes these same tools
  to Codex (``provider: openai-codex``, the Hermes pattern, native CLI).

The three tools:

* ``search_vibe`` — the ONLY discovery path. Every id it returns is recorded
  in a per-run ``seen`` set.
* ``get_track_features`` — deterministic facts (Camelot via
  ``harmonics.to_camelot``; LLM never computes keys). Honest null for absent
  fields.
* ``create_playlist`` — the single validated write. **Gate #1:** every
  ``track_id`` must be in ``seen`` (returned by a prior ``search_vibe`` this
  run) — an invented id rejects the whole call. **Gate #2:**
  ``create_playlist.create_playlist`` re-validates each surviving id against
  the live library. A playlist can never reference a track the agent invented
  or the library does not contain.

No-hang: ``dispatch`` runs every handler under a hard per-tool timeout, and
the handlers RETURN error dicts — they never raise — so a bad arg degrades to
a recoverable message instead of wedging the caller's loop.
"""

from __future__ import annotations

import concurrent.futures
import logging
from typing import Any, Callable

from vibemix.library.create_playlist import PlaylistResult, create_playlist
from vibemix.library.embed import LibraryEmbedder
from vibemix.library.rekordbox import RekordboxLibrary
from vibemix.library.search import vibe_search
from vibemix.library.store import LibraryStore
from vibemix.state import harmonics

logger = logging.getLogger(__name__)

# Hard wall-clock per tool call. A pathological handler (or a wedged search)
# can never park a caller's loop past this.
TOOL_CALL_TIMEOUT_S = 30.0


class LibraryToolset:
    """The grounded tool core: handlers + per-run seen-set + dispatch.

    One instance == one curation run. The ``seen`` set is the grounding
    spine; it MUST live for the whole run (across every tool call) and MUST
    NOT be shared between runs, or one user's search could ground another's
    playlist. Backends allocate a fresh instance per request.
    """

    def __init__(
        self,
        embedder: LibraryEmbedder,
        store: LibraryStore,
        library: RekordboxLibrary,
    ) -> None:
        self._embedder = embedder
        self._store = store
        self._library = library
        # The grounding spine: ids any search_vibe returned THIS run.
        self.seen: set[str] = set()
        self.created: PlaylistResult | None = None
        # SEAM #1 (CURATE-01): lazily-built genre lookup, the SAME mechanism the
        # co-host reads (genre_prototypes.GenrePrototypeLookup). Built on first
        # get_track_features call so __init__ stays import-boundary clean (no
        # genre_prototypes import here) and repeated feature lookups in one run
        # reuse the built prototype table.
        self._genre_lookup: Any | None = None

    # -- tool handlers (RETURN error strings, never raise) ------------------ #

    def search_vibe(self, args: dict[str, Any]) -> dict[str, Any]:
        query = args.get("query")
        if not isinstance(query, str) or not query.strip():
            return {"error": "search_vibe: 'query' must be a non-empty string"}
        k = args.get("k", 15)
        try:
            k = int(k)
        except (TypeError, ValueError):
            k = 15
        k = max(1, min(50, k))
        try:
            results, _cache_hit = vibe_search(
                self._embedder, self._store, self._library, query, k=k
            )
        except Exception as e:  # noqa: BLE001 — handler must not raise
            logger.warning("[viber] search_vibe failed: %s", e)
            return {"error": f"search_vibe failed: {type(e).__name__}"}
        for r in results:
            self.seen.add(r.track_id)
        return {
            "results": [
                {
                    "track_id": r.track_id,
                    "title": r.title,
                    "artist": r.artist,
                    "bpm": r.bpm,
                    "confidence": r.confidence,
                }
                for r in results
            ]
        }

    def get_track_features(self, args: dict[str, Any]) -> dict[str, Any]:
        track_id = args.get("track_id")
        if not isinstance(track_id, str) or not track_id:
            return {"error": "get_track_features: 'track_id' must be a string"}
        entry = self._library.lookup_by_id(track_id)
        if entry is None:
            return {"error": f"unknown track_id {track_id!r}"}
        # Camelot is deterministic — harmonics.to_camelot, never LLM-computed.
        camelot = harmonics.to_camelot(entry.key) if entry.key else None
        return {
            "track_id": entry.track_id,
            "title": entry.title,
            "artist": entry.artist,
            "bpm": entry.bpm if (entry.bpm and entry.bpm > 0) else None,
            "key": camelot,  # honest null when unrecognized/absent
            "duration_s": entry.duration_s or None,
            # SEAM #1 (CURATE-01): genre is a deterministic library-side fact,
            # resolved through the ONE genre_prototypes mechanism the co-host
            # reads (refresh.py -> GenrePrototypeLookup.classify_playing). Honest
            # null on abstain — the model NEVER supplies genre (invariant #3).
            "genre": self._resolve_genre(track_id),
        }

    def _resolve_genre(self, track_id: str) -> str | None:
        """Resolve genre via the SHARED genre_prototypes mechanism (CURATE-01).

        Routes through the SAME ``GenrePrototypeLookup.classify_playing`` the
        co-host reads, so the curator and co-host derive genre from ONE source.
        Reads the track's CACHED library embedding at €0 (no live embed). On the
        mechanism's own abstain (``("unknown", _)`` — track not in the library /
        degenerate prototype table) returns ``None`` (honest-null, byte-identical
        class to the prior hardcoded ``genre: None``), never a fabricated label.

        Per Pitfall 2 ALL prototype-distance math is delegated to
        genre_prototypes — this method adds none (no re-rolled centering).
        Lazy-import + lazy lookup-build keep the
        import-boundary discipline (Pattern 1). Guarded: any failure degrades to
        honest-null so a feature lookup never raises.
        """
        try:
            if self._genre_lookup is None:
                from vibemix.library.genre_prototypes import GenrePrototypeLookup

                self._genre_lookup = GenrePrototypeLookup(self._store)
            label, _conf = self._genre_lookup.classify_playing(track_id)
            return label if label and label != "unknown" else None
        except Exception:  # noqa: BLE001 — feature lookup must not raise
            return None

    def create_playlist(self, args: dict[str, Any]) -> dict[str, Any]:
        name = args.get("name")
        track_ids = args.get("track_ids")
        if not isinstance(name, str) or not name.strip():
            return {"error": "create_playlist: 'name' must be a non-empty string"}
        if not isinstance(track_ids, list) or not track_ids:
            return {"error": "create_playlist: 'track_ids' must be a non-empty list"}
        # GROUNDING gate #1: every id must be in this run's seen-set. An id the
        # model produced without a prior search_vibe is a hallucination —
        # reject the whole call so it cannot smuggle one in.
        invented = [
            t for t in track_ids if not (isinstance(t, str) and t in self.seen)
        ]
        if invented:
            return {
                "error": (
                    "rejected: these track_ids were never returned by "
                    f"search_vibe this run (invented): {invented}. Only use "
                    "ids from a search_vibe result."
                )
            }
        try:
            result = create_playlist(self._library, name, track_ids)
        except Exception as e:  # noqa: BLE001 — handler must not raise
            logger.warning("[viber] create_playlist failed: %s", e)
            return {"error": f"create_playlist failed: {type(e).__name__}"}
        self.created = result
        return {
            "created": True,
            "name": result.name,
            "track_count": len(result.track_ids),
            "m3u_path": str(result.m3u_path),
            "json_path": str(result.json_path),
            "dropped_ids": result.dropped_ids,
        }

    # -- dispatch (hard per-tool timeout; never raises) --------------------- #

    def dispatch(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        handlers: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
            "search_vibe": self.search_vibe,
            "get_track_features": self.get_track_features,
            "create_playlist": self.create_playlist,
        }
        handler = handlers.get(name)
        if handler is None:
            return {"error": f"unknown tool {name!r}"}
        # Hard per-tool timeout — a pathological handler can never park the loop.
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            fut = ex.submit(handler, args)
            try:
                return fut.result(timeout=TOOL_CALL_TIMEOUT_S)
            except concurrent.futures.TimeoutError:
                return {"error": f"tool {name!r} timed out"}
            except Exception as e:  # noqa: BLE001 — defensive; handlers return errors
                return {"error": f"tool {name!r} crashed: {type(e).__name__}"}


__all__ = ["TOOL_CALL_TIMEOUT_S", "LibraryToolset"]
