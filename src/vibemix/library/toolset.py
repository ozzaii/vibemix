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
from typing import TYPE_CHECKING, Any, Callable

from vibemix.library.create_playlist import PlaylistResult, create_playlist

if TYPE_CHECKING:
    # Type-only reference (no runtime import — the engine is lazy-imported in the
    # export_set handler). Makes ``ExportResult`` a genuinely-referenced name in
    # src so the orphan-inventory gate stops flagging it as defined-but-unused.
    from vibemix.library.export_rekordbox import ExportResult
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
        # BL-02: the successful set-prep export (mirrors ``created``). Set by the
        # export_set handler; the agent loop reads it to break with a terminal
        # "exported" stop_reason and surface the path.
        self.exported: ExportResult | None = None
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
            # WR-03: this lazy-init is an unguarded check-then-set, which is safe
            # ONLY because dispatch serializes tool calls within a run — `dispatch`
            # runs each handler on a fresh single-worker ThreadPoolExecutor and the
            # agent loop dispatches calls one at a time, so two `get_track_features`
            # never race this line. If a future caller ever dispatches tool calls
            # concurrently against the same toolset, guard this with a per-instance
            # lock. (The inner GenrePrototypeLookup is itself thread-safe via
            # double-checked locks, so the worst case today is wasted work, never
            # corruption.)
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

    # -- set-prep tools (Vibe Mix engine; lazy-import the engine modules) ---- #

    def get_track_energy(self, args: dict[str, Any]) -> dict[str, Any]:
        """Deterministic perceived-dancefloor-energy (0-100) for one track.

        The energy is COMPUTED from the audio (``energy.score_energy_cached``),
        never supplied by the model (invariant #3). Honest-null
        (``energy: None``) when the track has no file or the audio is
        undecodable — the model must reason around a missing value, never invent
        one.
        """
        track_id = args.get("track_id")
        if not isinstance(track_id, str) or not track_id:
            return {"error": "get_track_energy: 'track_id' must be a string"}
        entry = self._library.lookup_by_id(track_id)
        if entry is None:
            return {"error": f"unknown track_id {track_id!r}"}
        filepath = getattr(entry, "filepath", None)
        if not filepath:
            return {"track_id": track_id, "energy": None}
        try:
            from vibemix.library.energy import score_energy_cached

            score = score_energy_cached(str(filepath))
        except Exception as e:  # noqa: BLE001 — handler must not raise
            logger.warning("[viber] get_track_energy failed: %s", e)
            return {"track_id": track_id, "energy": None}
        if score is None:
            return {"track_id": track_id, "energy": None}
        return {
            "track_id": track_id,
            "energy": round(score.score, 1),
            "breakdown": dict(score.breakdown),
        }

    def discover_pool(self, args: dict[str, Any]) -> dict[str, Any]:
        """Build a grounded, diverse candidate pool from the user's library.

        Mode A (library-local) discovery: a text vibe and/or reference tracks →
        an MMR-diverse, hard-filtered pool of the DJ's OWN tracks. Every id it
        returns is recorded in ``seen`` — so it is a discovery path on par with
        ``search_vibe`` for grounding (sequence_set / create_playlist / export
        accept its ids). Never surfaces a fabricated track.
        """
        try:
            from vibemix.library import discovery
        except Exception as e:  # noqa: BLE001
            return {"error": f"discover_pool unavailable: {type(e).__name__}"}

        query = args.get("query")
        text_query = query if isinstance(query, str) and query.strip() else None
        refs = args.get("ref_track_ids")
        ref_track_ids = (
            [t for t in refs if isinstance(t, str)] if isinstance(refs, list) else None
        )

        def _opt_int(key: str) -> int | None:
            v = args.get(key)
            try:
                return int(v) if v is not None else None
            except (TypeError, ValueError):
                return None

        def _opt_float(key: str) -> float | None:
            v = args.get(key)
            try:
                return float(v) if v is not None else None
            except (TypeError, ValueError):
                return None

        k = _opt_int("k") or 50
        k = max(1, min(200, k))
        excl = args.get("exclude_ids")
        exclude_ids = (
            {t for t in excl if isinstance(t, str)} if isinstance(excl, list) else None
        )
        try:
            pool = discovery.discover_pool(
                self._store,
                self._library,
                self._embedder,
                ref_track_ids=ref_track_ids,
                text_query=text_query,
                k=k,
                bpm_min=_opt_float("bpm_min"),
                bpm_max=_opt_float("bpm_max"),
                min_duration_s=_opt_float("min_duration_s"),
                max_duration_s=_opt_float("max_duration_s"),
                exclude_ids=exclude_ids,
            )
        except Exception as e:  # noqa: BLE001 — handler must not raise
            logger.warning("[viber] discover_pool failed: %s", e)
            return {"error": f"discover_pool failed: {type(e).__name__}"}
        for item in pool:
            self.seen.add(item.track_id)
        return {
            "pool": [
                {
                    "track_id": item.track_id,
                    "title": item.title,
                    "artist": item.artist,
                    "bpm": item.bpm,
                    "camelot": item.camelot,
                    "similarity": item.similarity,
                }
                for item in pool
            ]
        }

    def sequence_set(self, args: dict[str, Any]) -> dict[str, Any]:
        """Order grounded track_ids into an energy-curve-following set.

        GATE (invariant #2): every track_id MUST be in ``seen`` (returned by a
        prior search_vibe / discover_pool THIS run) — an invented id rejects the
        whole call. Per-track vec/bpm/camelot/energy are resolved deterministically
        (stored vector + library metadata + computed energy); the model supplies
        only the ORDER intent (the curve), never the facts.
        """
        track_ids = args.get("track_ids")
        if not isinstance(track_ids, list) or not track_ids:
            return {"error": "sequence_set: 'track_ids' must be a non-empty list"}
        curve = args.get("curve")
        if not isinstance(curve, str) or not curve.strip():
            return {"error": "sequence_set: 'curve' must be a preset name"}
        invented = [
            t for t in track_ids if not (isinstance(t, str) and t in self.seen)
        ]
        if invented:
            return {
                "error": (
                    "rejected: these track_ids were never returned by "
                    f"search_vibe/discover_pool this run (invented): {invented}. "
                    "Only sequence ids from a discovery result."
                )
            }
        try:
            from vibemix.library import sequencer
            from vibemix.library.energy import score_energy_cached
            from vibemix.library.next_suggestion import seed_vector_for_track_id

            pool: list[Any] = []
            for tid in track_ids:
                vec = seed_vector_for_track_id(self._store, tid)
                if vec is None:
                    continue  # no stored vector → cannot place; skip (grounding)
                entry = self._library.lookup_by_id(tid)
                bpm = None
                camelot = None
                duration_s = 0.0
                energy = None
                if entry is not None:
                    bpm = entry.bpm if (entry.bpm and entry.bpm > 0) else None
                    camelot = (
                        harmonics.to_camelot(entry.key) if entry.key else None
                    )
                    duration_s = float(entry.duration_s or 0.0)
                    fp = getattr(entry, "filepath", None)
                    if fp:
                        try:
                            score = score_energy_cached(str(fp))
                            energy = score.score if score is not None else None
                        except Exception:  # noqa: BLE001 — best-effort energy
                            energy = None
                pool.append(
                    sequencer.PoolTrack(
                        track_id=tid,
                        title=entry.title if entry is not None else tid,
                        artist=entry.artist if entry is not None else "",
                        vec=vec,
                        bpm=bpm,
                        camelot=camelot,
                        energy=energy,
                        duration_s=duration_s,
                    )
                )
            if not pool:
                return {"error": "sequence_set: no track had a stored vector"}
            n_slots = args.get("n_slots")
            try:
                n_slots = int(n_slots) if n_slots is not None else len(pool)
            except (TypeError, ValueError):
                n_slots = len(pool)
            candidates = sequencer.sequence_set(
                pool, curve=curve, n_slots=n_slots
            )
        except KeyError as e:  # unknown curve preset → actionable error
            return {"error": f"sequence_set: unknown curve preset {e}"}
        except Exception as e:  # noqa: BLE001 — handler must not raise
            logger.warning("[viber] sequence_set failed: %s", e)
            return {"error": f"sequence_set failed: {type(e).__name__}"}
        return {
            "candidates": [
                {
                    "track_ids": c.track_ids,
                    "energy_fit": c.energy_fit,
                    "avg_coherence": c.avg_coherence,
                    "relaxed_transitions": c.relaxed_transitions,
                }
                for c in candidates
            ]
        }

    def export_set(self, args: dict[str, Any]) -> dict[str, Any]:
        """Export an ordered, grounded set to a Rekordbox-importable XML.

        Two-gate grounding (mirrors create_playlist): every track_id must be in
        ``seen`` (gate #1), then each is re-validated against the live library
        (gate #2) — an id the library no longer contains is dropped honestly.
        """
        track_ids = args.get("track_ids")
        name = args.get("name")
        if not isinstance(track_ids, list) or not track_ids:
            return {"error": "export_set: 'track_ids' must be a non-empty list"}
        if not isinstance(name, str) or not name.strip():
            return {"error": "export_set: 'name' must be a non-empty string"}
        invented = [
            t for t in track_ids if not (isinstance(t, str) and t in self.seen)
        ]
        if invented:
            return {
                "error": (
                    "rejected: these track_ids were never returned by "
                    f"search_vibe/discover_pool this run (invented): {invented}."
                )
            }
        try:
            from vibemix.library import export_rekordbox

            items: list[dict[str, Any]] = []
            for tid in track_ids:
                # GATE #2: re-validate against the live library.
                entry = self._library.lookup_by_id(tid)
                if entry is None:
                    continue
                camelot = harmonics.to_camelot(entry.key) if entry.key else None
                items.append(
                    {
                        "track_id": tid,
                        "filepath": getattr(entry, "filepath", None),
                        "title": entry.title,
                        "artist": entry.artist,
                        "bpm": entry.bpm if (entry.bpm and entry.bpm > 0) else None,
                        "camelot": camelot,
                        "duration_s": entry.duration_s or None,
                    }
                )
            if not items:
                return {"error": "export_set: no track resolved in the library"}
            out_path = args.get("out_path")
            if not (isinstance(out_path, str) and out_path.strip()):
                from pathlib import Path as _Path

                slug = "".join(
                    ch if ch.isalnum() or ch in "-_" else "-"
                    for ch in name.strip().lower()
                ).strip("-") or "set"
                out_path = str(
                    _Path.home() / ".cache" / "vibemix" / "sets" / f"{slug}.xml"
                )
            result: ExportResult = export_rekordbox.export_set(
                items, name, out_path, library=self._library
            )
        except Exception as e:  # noqa: BLE001 — handler must not raise
            logger.warning("[viber] export_set failed: %s", e)
            return {"error": f"export_set failed: {type(e).__name__}"}
        # BL-02: record the export so the agent loop can break with a terminal
        # "exported" stop_reason and carry the path into the result (mirrors how
        # ``created`` ends a create_playlist run).
        self.exported = result
        return {
            "exported": True,
            "path": str(result.path),
            "written": result.written,
            "referenced": result.referenced,
            "dropped": result.dropped,
        }

    # -- dispatch (hard per-tool timeout; never raises) --------------------- #

    def dispatch(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        handlers: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
            "search_vibe": self.search_vibe,
            "get_track_features": self.get_track_features,
            "create_playlist": self.create_playlist,
            "get_track_energy": self.get_track_energy,
            "discover_pool": self.discover_pool,
            "sequence_set": self.sequence_set,
            "export_set": self.export_set,
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
