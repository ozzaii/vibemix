# SPDX-License-Identifier: Apache-2.0
"""LibraryToolset — the grounded tool core shared by every Viber backend.

This is the single implementation of the playlist-curation tool surface and,
critically, of the **grounding gate** (Cardinal Invariant #2). The product
Codex backend uses it as the one tool spine, so the anti-hallucination contract
lives at the tool boundary instead of in a prompt:

* ``mcp_server.py`` — the FastMCP STDIO server that exposes these same tools
  to Codex (``provider: openai-codex``, the Hermes pattern, native CLI).

The base playlist tools:

* ``search_vibe`` / ``discover_pool`` — the grounded discovery paths. Every id
  either returns is recorded in a per-run ``seen`` set.
* ``get_track_features`` — deterministic facts (Camelot via
  ``harmonics.to_camelot``; LLM never computes keys). Honest null for absent
  fields.
* ``create_playlist`` — the single validated write. **Gate #1:** every
  ``track_id`` must be in ``seen`` (returned by ``search_vibe`` or
  ``discover_pool`` this run) — an invented id rejects the whole call. **Gate #2:**
  ``create_playlist.create_playlist`` re-validates each surviving id against
  the live library. A playlist can never reference a track the agent invented
  or the library does not contain.

No-hang: ``dispatch`` runs every handler under a hard per-tool timeout, and
the handlers RETURN error dicts — they never raise — so a bad arg degrades to
a recoverable message instead of wedging the caller's loop.
"""

from __future__ import annotations

import concurrent.futures
import json
import logging
import math
import os
import pathlib
import re
import threading
from collections.abc import Callable
from dataclasses import asdict, replace
from typing import TYPE_CHECKING, Any, Literal, Protocol

from vibemix.library.create_playlist import PlaylistResult, create_playlist

if TYPE_CHECKING:
    # Type-only reference (no runtime import — the engine is lazy-imported in the
    # export_set handler). Makes ``ExportResult`` a genuinely-referenced name in
    # src so the orphan-inventory gate stops flagging it as defined-but-unused.
    from vibemix.intel.agent_contract import AgentContextEnvelope
    from vibemix.intel.transition_scorer import SectionRecord, TransitionCandidate
    from vibemix.library.export_rekordbox import ExportResult
    from vibemix.library.smart_cues import SmartCueProposal
from vibemix.library.rekordbox import CuePoint, RekordboxLibrary
from vibemix.library.search import vibe_search
from vibemix.library.section_builder import (
    best_source_section,
    destination_sections,
    section_to_dict,
    sections_for_entry,
)
from vibemix.library.section_vectors import resolve_section_vector
from vibemix.library.store import LibraryStore
from vibemix.state import harmonics

logger = logging.getLogger(__name__)

# Hard wall-clock per tool call. A pathological handler (or a wedged search)
# can never park a caller's loop past this.
TOOL_CALL_TIMEOUT_S = 30.0
# Candidate inspection intentionally batches many deterministic local reads into
# one MCP round trip, so it needs more room than the tiny one-track tools.
BATCH_TOOL_CALL_TIMEOUT_S = 120.0
# Local library ingest can legitimately touch hundreds of files; keep the hard
# no-hang wall, but give the "get music in" tool more room than search/export.
INGEST_TOOL_CALL_TIMEOUT_S = 15 * 60.0

# Phase 99 HARDEN-RETRY (Decision 3, locked): after N consecutive empty
# ``search_vibe`` returns or ``{"error": ...}`` tool responses, the next
# ``dispatch()`` call short-circuits with a terminal ``tool_starvation``
# stop_reason. Default 3 — fast feedback on real failure modes without
# false-firing on a single missed search. Tunable in tests via monkeypatch.
# Wiring (counter increment + threshold trip) lands in Plan 99-02 / 99-03.
TOOL_STARVATION_THRESHOLD: int = 3
MAX_INSPECT_CANDIDATES: int = 24
INSPECT_CANDIDATES_WORKERS: int = 8
_INGEST_SOURCE_NAMES: frozenset[str] = frozenset(
    {"auto", "folder", "rekordbox", "traktor", "serato", "virtualdj", "engine"}
)

FRESHNESS_GUARDED_TOOLS: frozenset[str] = frozenset(
    {
        "search_vibe",
        "get_track_features",
        "get_track_sections",
        "inspect_candidates",
        "transition_slate",
        "compile_musical_context",
        "smart_hot_cues",
        "create_playlist",
        "get_track_energy",
        "discover_pool",
        "sequence_set",
        "export_set",
        "export_smart_cues",
        "quote_moment",
    }
)

# Phase 100 HARDEN-CLARIFY (Decision 2, locked): choices-length bounds for
# the Factor-7 request_clarification tool. 0/1 = no real disambiguation;
# 6+ = choice paralysis (Hick's law / 5±2 cognitive bound). Module
# constants so KAAN-ACTION §HARDEN-PHASE-B-CLARIFICATION-TONE can tune on
# funded-key ear-pass without code edits to the handler body.
MIN_CHOICES: int = 2
MAX_CHOICES: int = 5


class _EmbeddingProvider(Protocol):
    def embed_query(self, query: str) -> Any: ...


class LibraryToolset:
    """The grounded Codex/Viber tool core: handlers + per-run seen-set + dispatch.

    One instance == one curation run. The ``seen`` set is the grounding
    spine; it MUST live for the whole run (across every tool call) and MUST
    NOT be shared between runs, or one user's search could ground another's
    playlist. Backends allocate a fresh instance per request.
    """

    def __init__(
        self,
        embedder: _EmbeddingProvider,
        store: LibraryStore,
        library: RekordboxLibrary,
        *,
        freshness_provider: Callable[[], Any] | None = None,
        knowledge_embedder: _EmbeddingProvider | None = None,
    ) -> None:
        self._embedder = embedder
        self._store = store
        self._library = library
        self._freshness_provider = freshness_provider
        self._knowledge_embedder = knowledge_embedder
        # Lazily-loaded DJ-knowledge RAG store (retrieve_dj_knowledge). Built on
        # first use from disk; honest empty-results when no KB is present.
        self._knowledge_store: Any | None = None
        # The grounding spine: ids any search_vibe returned THIS run.
        self.seen: set[str] = set()
        # Similarity/confidence issued by discovery tools. sequence_set can use
        # the inverse as a bounded novelty signal without inventing any facts.
        self.seen_similarity: dict[str, float] = {}
        # INTEL grounding holders. Track ids are discovered first, then section
        # and transition/context aliases are issued from deterministic code.
        self.seen_sections: dict[str, SectionRecord] = {}
        self._seen_sections_lock = threading.Lock()
        self.issued_transition_candidates: dict[str, TransitionCandidate] = {}
        self.issued_cue_proposals: dict[str, SmartCueProposal] = {}
        self.issued_context_packets: dict[str, AgentContextEnvelope] = {}
        # Grounding spine for external research: fetch_url may only read URLs
        # issued by web_search in this run, mirroring the track-id seen gate.
        self.seen_urls: set[str] = set()
        # Cross-turn working-set title map (ground ledger). Populated ONLY by
        # seed_working_set after each id re-validated against the live library
        # THIS process — display meta for seeded ids, never an evidence source.
        self.seeded_working_set: dict[str, dict[str, str]] = {}
        self.created: PlaylistResult | None = None
        # BL-02: the successful set-prep export (mirrors ``created``). Set by the
        # export_set handler; the agent loop reads it to break with a terminal
        # "exported" stop_reason and surface the path.
        self.exported: ExportResult | None = None
        # Phase 99 HARDEN-RETRY (Plans 99-01..04, Decisions 1 + 4):
        # per-run consecutive empty/error counter + terminal stop_reason surface.
        # Counter is incremented + reset + threshold-tripped inside ``dispatch()``
        # below (the SINGLE writer site, on the dispatch-calling thread — see
        # the toolset.py:407-411 serialization analog for the safety argument).
        # ``stop_reason`` is written by ``_build_starvation_payload`` on trip and
        # read by ``_write_side_channel`` (env-gated, observability/propagation),
        # the ``create_playlist`` short-circuit, and the terminal dispatch-top
        # short-circuit.
        self._consecutive_empties: int = 0
        self.stop_reason: dict[str, Any] | None = None
        # SEAM #1 (CURATE-01): lazily-built genre lookup, the SAME mechanism the
        # co-host reads (genre_prototypes.GenrePrototypeLookup). Built on first
        # get_track_features call so __init__ stays import-boundary clean (no
        # genre_prototypes import here) and repeated feature lookups in one run
        # reuse the built prototype table.
        self._genre_lookup: Any | None = None
        self._genre_lookup_lock = threading.Lock()
        # Taste plumb: consent-gated role-pair taste scores from the SAME local
        # feedback store the live pill reads (app_data_dir()/taste_feedback.jsonl,
        # mirroring __main__'s _load_live_taste_scores). Loaded lazily on first
        # transition_slate and cached for the whole run — one disk read per
        # toolset instance. Consent OFF / empty store / any read failure caches
        # None, which leaves the scorer's taste component at its flat 0.50
        # default — byte-identical to the unwired behavior, so receipts never
        # imply a taste signal that does not exist.
        self._taste_scores: dict[tuple[str, str], float] | None = None
        self._taste_scores_loaded = False
        self._taste_scores_lock = threading.Lock()

    def _resolve_knowledge_embedder(self, store: Any) -> tuple[Any | None, str | None]:
        """Return the text embedder for DJ-knowledge retrieval.

        The main library embedder is CLAP/512. The bundled DJ-knowledge store is
        a separate text space, so a non-512 store must get a dedicated text
        embedder instead of falling through to CLAP and tripping the dim guard.
        """
        if self._knowledge_embedder is not None:
            return self._knowledge_embedder, None

        store_dim = getattr(store, "dim", None)
        if store_dim is None:
            return self._embedder, None

        try:
            from vibemix.library._cosine import EMBEDDING_DIM
        except Exception:
            EMBEDDING_DIM = 512

        if int(store_dim) == int(EMBEDDING_DIM):
            return self._embedder, None

        from vibemix.library.dj_knowledge import build_default_knowledge_embedder

        embedder, error = build_default_knowledge_embedder(output_dimensionality=int(store_dim))
        if embedder is not None:
            self._knowledge_embedder = embedder
            return embedder, None
        return None, (
            f"retrieve_dj_knowledge: knowledge store is dim {int(store_dim)} but no "
            f"matching text embedder is available: {error}"
        )

    def _freshness_payload(self) -> dict[str, Any]:
        """Return a dict freshness snapshot from the optional product provider."""
        if self._freshness_provider is None:
            return {"status": "unchecked", "stale": False, "reason": "freshness_guard_disabled"}
        try:
            status = self._freshness_provider()
        except Exception as e:
            return {
                "status": "cache_unreadable",
                "stale": True,
                "reason": f"freshness_check_failed:{type(e).__name__}",
            }
        if hasattr(status, "to_dict") and callable(status.to_dict):
            try:
                payload = status.to_dict()
            except Exception as e:
                return {
                    "status": "cache_unreadable",
                    "stale": True,
                    "reason": f"freshness_payload_failed:{type(e).__name__}",
                }
        elif isinstance(status, dict):
            payload = dict(status)
        else:
            return {
                "status": "cache_unreadable",
                "stale": True,
                "reason": f"freshness_payload_invalid:{type(status).__name__}",
            }
        payload.setdefault("status", "unknown")
        payload.setdefault("stale", payload.get("status") != "fresh")
        payload.setdefault("reason", "freshness_unknown")
        return payload

    def _freshness_guard_for_tool(self, name: str) -> dict[str, Any] | None:
        """Block local-library tools when Viber's source/index state is stale."""
        if self._freshness_provider is None or name not in FRESHNESS_GUARDED_TOOLS:
            return None
        payload = self._freshness_payload()
        status = str(payload.get("status") or "unknown")
        stale = payload.get("stale")
        if status == "fresh" and stale is False:
            return None
        reason = str(payload.get("reason") or status)
        return {
            "error": (
                "library freshness guard: the local library index is not current "
                f"({status}: {reason}). Re-import or refresh the library before "
                f"using Viber tool {name!r} for set generation."
            ),
            "blocked_by": "library_freshness",
            "library_freshness": payload,
        }

    def seed_working_set(self, track_ids: list[str]) -> list[str]:
        """Seed prior-turn working-set ids into this run's grounding spine.

        Cross-turn continuity for Viber chat (the ground ledger): ids a
        previous turn of THIS conversation discovered and validated are
        accepted ONLY after each one re-resolves in the live library in THIS
        process — a dead/foreign id drops silently, so the seeded surface is
        exactly as grounded as a fresh discovery return and the model can
        reference earlier finds (sequence/export/drop) without re-searching.
        The downstream write gates (create_playlist / export_set library
        re-validation) stay untouched: belt and braces. Returns the
        survivors, order-preserving.
        """
        survivors: list[str] = []
        for tid in track_ids:
            if not isinstance(tid, str) or not tid or tid in survivors:
                continue
            entry = self._library.lookup_by_id(tid)
            if entry is None:
                continue
            # Invariant-#2-justified write: the id just re-resolved in the
            # live library above, making this seed equivalent to a discovery
            # return. Counted by the seen-write gates in tests/repo/
            # test_no_seen_relaxation.py + tests/library/
            # test_request_clarification_no_track_surface.py (baseline 3).
            self.seen.add(tid)
            self.seeded_working_set[tid] = {"title": entry.title, "artist": entry.artist}
            survivors.append(tid)
        return survivors

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
        except Exception as e:
            logger.warning("[viber] search_vibe failed: %s", e)
            return {"error": f"search_vibe failed: {type(e).__name__}: {e}"}
        for r in results:
            self.seen.add(r.track_id)
            score = _unit_float_or_none(r.confidence)
            if score is not None:
                self.seen_similarity[r.track_id] = score
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

    def get_track_sections(self, args: dict[str, Any]) -> dict[str, Any]:
        """Issue grounded section records for one already-discovered track.

        v1 derives sections from Rekordbox cues when available, with a
        conservative fallback intro/outro map when the library has no cues. The
        full section store can replace the producer later without changing the
        holder or candidate contracts.
        """
        track_id = args.get("track_id")
        if not isinstance(track_id, str) or not track_id:
            return {"error": "get_track_sections: 'track_id' must be a string"}
        if track_id not in self.seen:
            return self._invented_track_id_error(track_id)
        entry = self._library.lookup_by_id(track_id)
        if entry is None:
            return {"error": f"unknown track_id {track_id!r}"}
        sections = sections_for_entry(entry)
        with self._seen_sections_lock:
            for section in sections:
                self.seen_sections[section.section_id] = section
        return {
            "track_id": track_id,
            "sections": [section_to_dict(section) for section in sections],
        }

    @staticmethod
    def _invented_track_id_error(track_id: str) -> dict[str, str]:
        return {
            "error": (
                "rejected: track_id was never returned by search_vibe/"
                f"discover_pool this run (invented): {track_id!r}"
            )
        }

    def inspect_candidates(self, args: dict[str, Any]) -> dict[str, Any]:
        """Batch deterministic candidate facts for already-discovered tracks.

        This is a speed tool, not a new authority surface: each id must already
        be in ``seen`` from search_vibe/discover_pool. It collapses the common
        get_track_features + get_track_sections + get_track_energy loop into
        one tool call while preserving honest-null/error behavior per row.
        """
        raw_track_ids = args.get("track_ids")
        if not isinstance(raw_track_ids, list) or not raw_track_ids:
            return {"error": "inspect_candidates: 'track_ids' must be a non-empty list"}

        truncated = len(raw_track_ids) > MAX_INSPECT_CANDIDATES
        def inspect_one(raw_track_id: Any) -> dict[str, Any]:
            if not isinstance(raw_track_id, str) or not raw_track_id:
                return {
                    "track_id": raw_track_id,
                    "error": "inspect_candidates: each track_id must be a non-empty string",
                }
            if raw_track_id not in self.seen:
                return {"track_id": raw_track_id, **self._invented_track_id_error(raw_track_id)}

            features = self.get_track_features({"track_id": raw_track_id})
            sections = self.get_track_sections({"track_id": raw_track_id})
            energy = self.get_track_energy({"track_id": raw_track_id})

            row: dict[str, Any] = {"track_id": raw_track_id}
            if "error" in features:
                row["features_error"] = features["error"]
            else:
                row["features"] = features
            if "error" in sections:
                row["sections_error"] = sections["error"]
            else:
                row["sections"] = sections.get("sections", [])
            if "error" in energy:
                row["energy_error"] = energy["error"]
            else:
                row["energy"] = {
                    key: value
                    for key, value in energy.items()
                    if key in {"energy", "breakdown"}
                }
            return row

        candidate_ids = raw_track_ids[:MAX_INSPECT_CANDIDATES]
        max_workers = min(INSPECT_CANDIDATES_WORKERS, len(candidate_ids))
        if max_workers <= 1:
            rows = [inspect_one(raw_track_id) for raw_track_id in candidate_ids]
        else:
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
                rows = list(ex.map(inspect_one, candidate_ids))

        out: dict[str, Any] = {
            "candidates": rows,
            "track_ids": [
                row["track_id"]
                for row in rows
                if isinstance(row.get("track_id"), str) and "error" not in row
            ],
            "limit": MAX_INSPECT_CANDIDATES,
            "truncated": truncated,
        }
        if truncated:
            out["note"] = f"truncated to first {MAX_INSPECT_CANDIDATES} track_ids"
        return out

    def _taste_scores_for_run(self) -> dict[tuple[str, str], float] | None:
        """Return cached consent-gated taste scores (the live pill's source).

        Fail-soft on every hop: a consent-read or store-parse failure degrades
        to None (flat taste) — handlers must return, never raise. The lock
        keeps "one disk read per run" true even if a concurrent dispatch races
        the first load (the `_genre_lookup_lock` idiom).
        """
        with self._taste_scores_lock:
            if self._taste_scores_loaded:
                return self._taste_scores
            self._taste_scores_loaded = True
            try:
                from vibemix.profile import load_consent

                consent = bool(load_consent())
            except Exception as e:
                logger.warning("[viber] taste consent read skipped: %s", e)
                return None
            if not consent:
                return None
            try:
                from vibemix.intel.taste_model import load_taste_model
                from vibemix.runtime.config_store import app_data_dir

                model = load_taste_model(
                    app_data_dir() / "taste_feedback.jsonl",
                    profile_consent=consent,
                )
            except Exception as e:
                logger.warning("[viber] taste disabled: %s", e)
                return None
            # Role-pair keyed weights only — no track ids ride in, so nothing
            # here can reach the seen-set / grounding spine (Invariant #2).
            self._taste_scores = model.taste_scores() or None
            return self._taste_scores

    def transition_slate(self, args: dict[str, Any]) -> dict[str, Any]:
        """Issue deterministic section-to-section transition candidates.

        The model supplies only grounded ids and high-level mode hints. The
        scorer resolves BPM/key/cue/phrase facts from issued sections and stored
        vectors; every emitted candidate is recorded in
        ``issued_transition_candidates`` before the model may reference it.
        """
        source_section_id = args.get("source_section_id")
        source_track_id = args.get("source_track_id")
        candidate_track_ids = args.get("candidate_track_ids")
        if not isinstance(candidate_track_ids, list) or not candidate_track_ids:
            return {"error": "transition_slate: 'candidate_track_ids' must be a non-empty list"}
        invented = [t for t in candidate_track_ids if not (isinstance(t, str) and t in self.seen)]
        if invented:
            return {
                "error": (
                    "rejected: these candidate_track_ids were never returned by "
                    f"search_vibe/discover_pool this run (invented): {invented}"
                )
            }

        source = self._resolve_source_section(source_section_id, source_track_id)
        if isinstance(source, dict):
            return source

        destinations = self._resolve_destination_sections(candidate_track_ids)
        if not destinations:
            return {"error": "transition_slate: no destination sections resolved"}

        mode = _mode_arg(args.get("mode"))
        max_candidates = _int_arg(args.get("max_candidates"), default=(5 if mode == "live" else 12))
        max_candidates = max(1, min(12, max_candidates))
        live_position = None
        if mode == "live":
            from vibemix.intel.transition_scorer import LivePosition

            live_position = LivePosition(
                remaining_bars=_optional_int_arg(args.get("remaining_bars")),
                playhead_confidence=_float_arg(args.get("playhead_confidence"), default=0.0),
                blend_active=bool(args.get("blend_active", False)),
            )
        try:
            from vibemix.intel.transition_scorer import (
                TransitionScoringInput,
                score_transition_slate,
            )

            source_vector_result = self._section_vector(source)
            destination_vector_results = {
                section.section_id: self._section_vector(section) for section in destinations
            }
            slate = score_transition_slate(
                TransitionScoringInput(
                    source=source,
                    destinations=tuple(destinations),
                    source_vector=source_vector_result.vector,
                    destination_vectors={
                        section_id: result.vector
                        for section_id, result in destination_vector_results.items()
                        if result.vector is not None
                    },
                    semantic_basis_by_section={
                        source.section_id: source_vector_result.basis,
                        **{
                            section_id: result.basis
                            for section_id, result in destination_vector_results.items()
                        },
                    },
                    played_track_ids=frozenset(
                        t for t in args.get("played_track_ids", []) if isinstance(t, str)
                    )
                    if isinstance(args.get("played_track_ids"), list)
                    else frozenset(),
                    candidate_pool_track_ids=frozenset(candidate_track_ids),
                    genre_profile=args.get("genre_profile")
                    if isinstance(args.get("genre_profile"), str)
                    else None,
                    live_position=live_position,
                    mode=mode,
                    taste_scores=self._taste_scores_for_run(),
                ),
                max_candidates=max_candidates,
            )
        except Exception as e:
            logger.warning("[viber] transition_slate failed: %s", e)
            return {"error": f"transition_slate failed: {type(e).__name__}: {e}"}

        for candidate in slate:
            self.issued_transition_candidates[candidate.candidate_id] = candidate
        return {
            "source_section_id": source.section_id,
            "candidates": [_transition_candidate_to_dict(candidate) for candidate in slate],
        }

    def compile_musical_context(self, args: dict[str, Any]) -> dict[str, Any]:
        """Issue a bounded context packet over already-issued transition ids."""
        candidate_ids = args.get("candidate_ids")
        if not isinstance(candidate_ids, list) or not candidate_ids:
            return {"error": "compile_musical_context: 'candidate_ids' must be a non-empty list"}
        candidates = []
        unknown = []
        for cid in candidate_ids:
            if not isinstance(cid, str) or cid not in self.issued_transition_candidates:
                unknown.append(cid)
            else:
                candidates.append(self.issued_transition_candidates[cid])
        if unknown:
            return {
                "error": (
                    "rejected: these candidate_ids were not issued by transition_slate "
                    f"this run: {unknown}"
                )
            }
        mode = _mode_arg(args.get("mode"))
        intent = args.get("intent")
        if not isinstance(intent, str) or not intent:
            intent = "live_next_pill" if mode == "live" else "transition_slate"
        current = args.get("current")
        current = current if isinstance(current, dict) else {}
        packet_id = f"ctx_{len(self.issued_context_packets) + 1:03d}"
        try:
            from vibemix.intel.context_compiler import compile_transition_context

            envelope = compile_transition_context(
                packet_id=packet_id,
                mode=mode,
                intent=intent,  # type: ignore[arg-type]
                current=current,
                candidates=tuple(candidates),
            )
        except Exception as e:
            logger.warning("[viber] compile_musical_context failed: %s", e)
            return {"error": f"compile_musical_context failed: {type(e).__name__}: {e}"}
        self.issued_context_packets[packet_id] = envelope
        return {"packet": asdict(envelope)}

    def smart_hot_cues(self, args: dict[str, Any]) -> dict[str, Any]:
        """Issue reviewable smart hot-cue proposals for seen tracks.

        The model supplies only grounded track ids and optional genre/policy
        hints. Cue positions are generated by deterministic code from library
        sections/cues; every proposal is stored before the model may reference
        its proposal/cue ids.
        """
        track_ids_arg = args.get("track_ids")
        if isinstance(track_ids_arg, list):
            track_ids = [track_id for track_id in track_ids_arg if isinstance(track_id, str)]
        else:
            track_id = args.get("track_id")
            track_ids = [track_id] if isinstance(track_id, str) and track_id else []
        if not track_ids:
            return {"error": "smart_hot_cues: provide 'track_id' or non-empty 'track_ids'"}
        invented = [track_id for track_id in track_ids if track_id not in self.seen]
        if invented:
            return {
                "error": (
                    "rejected: these track_ids were never returned by "
                    f"search_vibe/discover_pool this run (invented): {invented}"
                )
            }

        genre_hint = args.get("genre")
        genre_hint = genre_hint if isinstance(genre_hint, str) and genre_hint.strip() else None
        proposals = []
        try:
            from vibemix.library.smart_cues import propose_smart_cues

            for track_id in track_ids:
                entry = self._library.lookup_by_id(track_id)
                if entry is None:
                    return {"error": f"unknown track_id {track_id!r}"}
                sections = sections_for_entry(entry)
                for section in sections:
                    self.seen_sections[section.section_id] = section
                proposal = propose_smart_cues(
                    entry,
                    sections,
                    genre=genre_hint or self._resolve_genre(track_id) or entry.genre,
                )
                self.issued_cue_proposals[proposal.proposal_id] = proposal
                proposals.append(proposal)
        except Exception as e:
            logger.warning("[viber] smart_hot_cues failed: %s", e)
            return {"error": f"smart_hot_cues failed: {type(e).__name__}: {e}"}

        return {"proposals": [_smart_cue_proposal_to_dict(proposal) for proposal in proposals]}

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
                with self._genre_lookup_lock:
                    if self._genre_lookup is None:
                        from vibemix.library.genre_prototypes import GenrePrototypeLookup

                        self._genre_lookup = GenrePrototypeLookup(self._store)
            label, _conf = self._genre_lookup.classify_playing(track_id)
            return label if label and label != "unknown" else None
        except Exception:
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
        invented = [t for t in track_ids if not (isinstance(t, str) and t in self.seen)]
        if invented:
            return {
                "error": (
                    "rejected: these track_ids were never returned by "
                    f"search_vibe/discover_pool this run (invented): {invented}. "
                    "Only use ids from a discovery result."
                )
            }
        try:
            result = create_playlist(self._library, name, track_ids)
        except Exception as e:
            logger.warning("[viber] create_playlist failed: %s", e)
            return {"error": f"create_playlist failed: {type(e).__name__}: {e}"}
        self.created = result
        return {
            "created": True,
            "name": result.name,
            "track_ids": result.track_ids,
            "track_count": len(result.track_ids),
            "m3u_path": str(result.m3u_path),
            "json_path": str(result.json_path),
            "dropped_ids": result.dropped_ids,
        }

    # -- web research tools (grounded external lookup; module is dep-injected) #

    def web_search(self, args: dict[str, Any]) -> dict[str, Any]:
        """Web-search for DJ knowledge the library can't supply (track/label/
        artist facts, releases, scene context). Returns {results:[{title, url,
        snippet, score}], query}. Needs TAVILY_API_KEY; honest error if absent.
        Every result carries a url — cite it, never paraphrase it as fact."""
        from vibemix.library import web_research

        query = args.get("query")
        if not isinstance(query, str) or not query.strip():
            return {"error": "web_search: 'query' must be a non-empty string"}
        k = args.get("k", 5)
        try:
            k = int(k)
        except (TypeError, ValueError):
            k = 5
        result = web_research.web_search(query, k=k)
        results = result.get("results") if isinstance(result, dict) else None
        if isinstance(results, list):
            for row in results:
                if not isinstance(row, dict):
                    continue
                url = row.get("url")
                if isinstance(url, str) and url.strip():
                    self.seen_urls.add(url)
        return result

    def fetch_url(self, args: dict[str, Any]) -> dict[str, Any]:
        """Fetch one web page's readable text (from a prior web_search url).
        Returns {url, title, text}. http(s) only; honest error otherwise. Use to
        read a source you cited — never invent page contents."""
        from vibemix.library import web_research

        url = args.get("url")
        if not isinstance(url, str) or not url:
            return {"error": "fetch_url: 'url' must be a string"}
        if url not in self.seen_urls:
            return {
                "error": (
                    "rejected: url was not returned by web_search this run: "
                    f"{url!r}"
                )
            }
        return web_research.fetch_url(url)

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
        except Exception as e:
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
        except Exception as e:
            return {"error": f"discover_pool unavailable: {type(e).__name__}: {e}"}

        query = args.get("query")
        text_query = query if isinstance(query, str) and query.strip() else None
        refs = args.get("ref_track_ids")
        ref_track_ids = [t for t in refs if isinstance(t, str)] if isinstance(refs, list) else None

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
        exclude_ids = {t for t in excl if isinstance(t, str)} if isinstance(excl, list) else None
        bpm_min = _opt_float("bpm_min")
        bpm_max = _opt_float("bpm_max")
        min_duration_s = _opt_float("min_duration_s")
        max_duration_s = _opt_float("max_duration_s")
        try:
            pool = discovery.discover_pool(
                self._store,
                self._library,
                self._embedder,
                ref_track_ids=ref_track_ids,
                text_query=text_query,
                k=k,
                bpm_min=bpm_min,
                bpm_max=bpm_max,
                min_duration_s=min_duration_s,
                max_duration_s=max_duration_s,
                exclude_ids=exclude_ids,
            )
        except Exception as e:
            logger.warning("[viber] discover_pool failed: %s", e)
            return {"error": f"discover_pool failed: {type(e).__name__}: {e}"}
        for item in pool:
            self.seen.add(item.track_id)
            score = _unit_float_or_none(item.similarity)
            if score is not None:
                self.seen_similarity[item.track_id] = score

        metadata_warnings: list[dict[str, Any]] = []
        if (bpm_min is not None or bpm_max is not None) and pool:
            unknown_bpm = sum(1 for item in pool if item.bpm is None)
            if unknown_bpm:
                metadata_warnings.append(
                    {
                        "field": "bpm",
                        "reason": "missing_library_metadata",
                        "requested_min": bpm_min,
                        "requested_max": bpm_max,
                        "unknown_count": unknown_bpm,
                        "total_count": len(pool),
                        "message": (
                            "BPM filter requested, but some returned tracks have "
                            "unknown BPM in the library cache; do not treat the "
                            "range as verified for those rows."
                        ),
                    }
                )

        out: dict[str, Any] = {
            "filters": {
                "bpm_min": bpm_min,
                "bpm_max": bpm_max,
                "min_duration_s": min_duration_s,
                "max_duration_s": max_duration_s,
            },
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
        if metadata_warnings:
            out["metadata_warnings"] = metadata_warnings
        return out

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
        invented = [t for t in track_ids if not (isinstance(t, str) and t in self.seen)]
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
                    camelot = harmonics.to_camelot(entry.key) if entry.key else None
                    duration_s = float(entry.duration_s or 0.0)
                    fp = getattr(entry, "filepath", None)
                    if fp:
                        try:
                            score = score_energy_cached(str(fp))
                            energy = score.score if score is not None else None
                        except Exception:
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
                        cues=(tuple(getattr(entry, "cues", ()) or ()) if entry is not None else ()),
                    )
                )
            if not pool:
                return {"error": "sequence_set: no track had a stored vector"}
            pool, deduped_track_ids = _dedupe_sequence_pool(pool)
            if not pool:
                return {"error": "sequence_set: every grounded track collapsed as a duplicate"}
            n_slots = args.get("n_slots")
            try:
                n_slots = int(n_slots) if n_slots is not None else len(pool)
            except (TypeError, ValueError):
                n_slots = len(pool)
            novelty = _bounded_float_arg(
                args.get("novelty", args.get("novelty_weight", args.get("surprise_weight"))),
                minimum=0.0,
                maximum=1.0,
                default=0.0,
            )
            weights = {"gamma": novelty} if novelty > 0.0 else None
            surprise = (
                {
                    tid: 1.0 - score
                    for tid in track_ids
                    if tid not in deduped_track_ids
                    if (score := self.seen_similarity.get(tid)) is not None
                }
                if novelty > 0.0
                else None
            )
            candidates = sequencer.sequence_set(
                pool,
                curve=curve,
                n_slots=n_slots,
                weights=weights,
                surprise=surprise,
            )
        except KeyError as e:  # unknown curve preset → actionable error
            return {"error": f"sequence_set: unknown curve preset {e}"}
        except Exception as e:
            logger.warning("[viber] sequence_set failed: %s", e)
            return {"error": f"sequence_set failed: {type(e).__name__}: {e}"}
        out: dict[str, Any] = {
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
        if deduped_track_ids:
            out["deduped_track_ids"] = deduped_track_ids
        return out

    def ingest_source(self, args: dict[str, Any]) -> dict[str, Any]:
        """Import a local folder or DJ-software catalog into the Viber library.

        This is the "get music in" counterpart to ``export_set``. It uses the
        same local, keyless ingest engines as the CLI and refreshes this
        toolset's in-memory library after a successful cache write so later
        calls in the same Viber run can search the imported tracks.
        """
        raw_source = args.get("source", "auto")
        source_name = _normalize_ingest_source_name(raw_source)
        if source_name is None:
            return {
                "error": (
                    "ingest_source: 'source' must be one of "
                    f"{sorted(_INGEST_SOURCE_NAMES)}"
                )
            }

        path, path_error = _ingest_path_arg(args.get("path"))
        if path_error is not None:
            return {"error": f"ingest_source: {path_error}"}
        compute_key = bool(args.get("compute_key", True))
        compute_bpm = bool(args.get("compute_bpm", True))

        try:
            if source_name == "auto":
                route = _infer_ingest_route(path)
            else:
                route = _ingest_route_for_source(source_name, path)
            if route is None:
                return _ingest_missing_source_payload(source_name, path)

            if route["kind"] == "folder":
                folder = route["path"]
                from vibemix.library import ingest_folder

                report = ingest_folder(
                    folder,
                    self._embedder,
                    self._store,
                    persist_library=True,
                    compute_band_shares=True,
                    compute_key=compute_key,
                    compute_bpm=compute_bpm,
                )
                refreshed_tracks = self._refresh_library_cache_after_ingest()
                return _ingest_tool_report(
                    source="folder",
                    catalog=str(folder),
                    report=report,
                    refreshed_tracks=refreshed_tracks,
                )

            source = route["source"]
            if not source.detect():
                return _ingest_source_not_detected_payload(source_name, source)

            from vibemix.library.ingest import ingest_source as ingest_library_source

            report = ingest_library_source(
                source,
                self._embedder,
                self._store,
                persist_library=True,
                compute_key=compute_key,
                compute_bpm=compute_bpm,
            )
            refreshed_tracks = self._refresh_library_cache_after_ingest()
            return _ingest_tool_report(
                source=str(getattr(source, "name", source_name)),
                catalog=str(getattr(source, "resolved_path", "") or ""),
                report=report,
                refreshed_tracks=refreshed_tracks,
            )
        except Exception as e:
            logger.warning("[viber] ingest_source failed: %s", e)
            return {"error": f"ingest_source failed: {type(e).__name__}: {e}"}

    def _refresh_library_cache_after_ingest(self) -> int:
        refreshed = RekordboxLibrary()
        if refreshed.try_load_cache():
            self._library = refreshed
        return len(getattr(self._library, "tracks", {}) or {})

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
        invented = [t for t in track_ids if not (isinstance(t, str) and t in self.seen)]
        if invented:
            return {
                "error": (
                    "rejected: these track_ids were never returned by "
                    f"search_vibe/discover_pool this run (invented): {invented}."
                )
            }
        try:
            target = _export_target_arg(args.get("target", args.get("export", "both")))
        except ValueError as exc:
            return {"error": f"export_set: {exc}"}
        tag_write_granted = bool(args.get("tag_write_granted", args.get("write_tags", False)))
        if _target_wants_tags(target) and not tag_write_granted:
            return {
                "error": (
                    "export_set: target writes Serato/Mixxx Markers2 tags into audio files; "
                    "pass tag_write_granted=True after explicit user permission"
                )
            }
        auto_cue_enabled = bool(args.get("cue", args.get("auto_cue", True))) and (
            _target_wants_rekordbox(target) or _target_wants_tags(target)
        )
        auto_cue_report: dict[str, Any] = _auto_cue_report(enabled=auto_cue_enabled)
        try:
            from vibemix.library import export_rekordbox

            items: list[dict[str, Any]] = []
            for tid in track_ids:
                # GATE #2: re-validate against the live library.
                entry = self._library.lookup_by_id(tid)
                if entry is None:
                    continue
                camelot = harmonics.to_camelot(entry.key) if entry.key else None
                cue_payload = _export_cues_and_grid(entry)
                if auto_cue_enabled:
                    auto_cue_report["tracks_attempted"] += 1
                    try:
                        auto_marks, proposal_summary = _auto_cue_marks_for_export(
                            entry,
                            genre=self._resolve_genre(tid) or entry.genre,
                            occupied_slots=_occupied_hotcue_slots(cue_payload.get("cues", ())),
                        )
                    except Exception as cue_exc:
                        logger.warning(
                            "[viber] export_set auto-cue skipped for %s: %s", tid, cue_exc
                        )
                        auto_cue_report["skipped_failed"] += 1
                    else:
                        _add_auto_cue_summary(auto_cue_report, proposal_summary, len(auto_marks))
                        if auto_marks:
                            cue_payload["cues"] = [*cue_payload.get("cues", []), *auto_marks]
                _add_auto_cue_snap_summary(
                    auto_cue_report,
                    _snap_machine_cues_to_export_grid(cue_payload),
                )
                items.append(
                    {
                        "track_id": tid,
                        "filepath": getattr(entry, "filepath", None),
                        "title": entry.title,
                        "artist": entry.artist,
                        "bpm": entry.bpm if (entry.bpm and entry.bpm > 0) else None,
                        "camelot": camelot,
                        "duration_s": entry.duration_s or None,
                        **cue_payload,
                    }
                )
            if not items:
                return {"error": "export_set: no track resolved in the library"}
            out_path = args.get("out_path")
            if not (isinstance(out_path, str) and out_path.strip()):
                suffix = ".m3u8" if target == "m3u8" else ".xml"
                out_path = str(_default_set_export_path(name, suffix=suffix))
            outputs: dict[str, str] = {}
            dropped: list[dict[str, Any]] = []
            tag_receipts: list[dict[str, Any]] = []
            written = 0
            referenced = len(items)
            result: ExportResult | None = None
            if _target_wants_rekordbox(target):
                xml_path = _with_export_suffix(out_path, ".xml")
                result = export_rekordbox.export_set(items, name, xml_path, library=self._library)
                outputs["rekordbox"] = str(result.path)
                written = result.written
                referenced = result.referenced
                dropped.extend(result.dropped)
            if _target_wants_m3u8(target):
                from vibemix.library.cue_folder import write_m3u8

                m3u8_path = _with_export_suffix(out_path, ".m3u8")
                write_m3u8(items, m3u8_path)
                outputs["m3u8"] = str(m3u8_path)
                if result is None:
                    written = len(items)
                    referenced = len(items)
            if _target_wants_tags(target):
                tag_receipt = _write_export_set_markers2_tags(
                    items,
                    carrier=_markers2_carrier_for_target(target),
                    granted=tag_write_granted,
                )
                tag_receipts.append(tag_receipt)
                if tag_receipt["tagged"] <= 0 and not outputs:
                    return {
                        "error": (
                            "export_set: no Serato/Mixxx tag carrier written; "
                            f"{tag_receipt['skipped']} track(s) skipped"
                        ),
                        "tag_receipts": tag_receipts,
                    }
                if result is None and not outputs:
                    written = int(tag_receipt["tagged"])
                    referenced = int(tag_receipt["tagged"])
            if result is None and not outputs and not tag_receipts:
                return {"error": f"export_set: unsupported target {target!r}"}
            materialized_for_pill = _materialize_landed_machine_cues_for_pill(
                self._library,
                items,
            )
        except Exception as e:
            logger.warning("[viber] export_set failed: %s", e)
            return {"error": f"export_set failed: {type(e).__name__}: {e}"}
        # BL-02: record the export so the agent loop can break with a terminal
        # "exported" stop_reason and carry the path into the result (mirrors how
        # ``created`` ends a create_playlist run).
        if result is not None:
            self.exported = result
        primary_path = (
            outputs.get("rekordbox")
            or outputs.get("m3u8")
            or (
                tag_receipts[0]["files"][0]
                if tag_receipts and tag_receipts[0].get("files")
                else str(out_path)
            )
        )
        return {
            "exported": True,
            "target": target,
            "path": primary_path,
            "outputs": outputs,
            "tag_receipts": tag_receipts,
            "import_instructions": _export_import_instructions(
                outputs=outputs,
                tag_receipts=tag_receipts,
            ),
            "written": written,
            "referenced": referenced,
            "dropped": dropped,
            "auto_cues": auto_cue_report,
            "pill_cues_materialized": materialized_for_pill,
        }

    def export_smart_cues(self, args: dict[str, Any]) -> dict[str, Any]:
        """Export selected cue ids from an issued SmartCueProposal.

        This is the agent-safe smart-cue write path: it rejects raw cue payloads
        and arbitrary track paths, revalidates the proposal/track, and preserves
        A-H slot numbers through `export_set`.
        """
        if "cues" in args or "track_path" in args:
            return {
                "error": (
                    "export_smart_cues rejects raw cue payloads; call "
                    "smart_hot_cues first and pass issued proposal/cue ids"
                )
            }
        proposal_id = args.get("proposal_id")
        if not isinstance(proposal_id, str) or not proposal_id:
            return {"error": "export_smart_cues: 'proposal_id' must be a string"}
        proposal = self.issued_cue_proposals.get(proposal_id)
        if proposal is None:
            return {
                "error": (
                    "rejected: proposal_id was not issued by smart_hot_cues "
                    f"this run: {proposal_id!r}"
                )
            }
        entry = self._library.lookup_by_id(proposal.track_id)
        if entry is None:
            return {"error": f"export_smart_cues: proposal track missing {proposal.track_id!r}"}
        if proposal.track_id not in self.seen:
            return {
                "error": (
                    "rejected: proposal track_id is no longer grounded in this run: "
                    f"{proposal.track_id!r}"
                )
            }

        selected = args.get("selected_cue_ids")
        if selected is None:
            selected_ids: set[str] | None = None
        elif isinstance(selected, list) and selected:
            selected_ids = {cue_id for cue_id in selected if isinstance(cue_id, str)}
            if len(selected_ids) != len(selected):
                return {"error": "export_smart_cues: selected_cue_ids must all be strings"}
        else:
            return {"error": "export_smart_cues: selected_cue_ids must be a non-empty list or null"}

        proposal_cue_ids = {cue.cue_id for cue in proposal.cues}
        if selected_ids is not None:
            unknown = sorted(selected_ids - proposal_cue_ids)
            if unknown:
                return {
                    "error": (
                        f"rejected: selected cue ids were not issued in this proposal: {unknown}"
                    )
                }

        include_review = bool(args.get("include_review", selected_ids is not None))
        include_preserved = bool(args.get("include_preserved", False))
        try:
            from vibemix.library import export_rekordbox
            from vibemix.library.cue_landing import (
                cue_set_from_proposal,
                export_marks_for_cueset,
            )

            cueset = cue_set_from_proposal(
                entry,
                proposal,
                include_review=include_review,
                include_preserved=include_preserved,
            )
            marks = export_marks_for_cueset(cueset)
            if selected_ids is not None:
                marks = [mark for mark in marks if mark.get("cue_id") in selected_ids]
            if not marks:
                return {"error": "export_smart_cues: no exportable cues selected"}

            out_path = args.get("out_path")
            if not (isinstance(out_path, str) and out_path.strip()):
                from pathlib import Path as _Path

                out_path = str(
                    _Path.home()
                    / ".cache"
                    / "vibemix"
                    / "cues"
                    / f"{proposal.track_id}-smart-cues.xml"
                )

            camelot = harmonics.to_camelot(entry.key) if entry.key else None
            result: ExportResult = export_rekordbox.export_set(
                [
                    {
                        "track_id": entry.track_id,
                        "filepath": entry.filepath,
                        "title": entry.title,
                        "artist": entry.artist,
                        "bpm": entry.bpm if (entry.bpm and entry.bpm > 0) else None,
                        "camelot": camelot,
                        "duration_s": entry.duration_s or None,
                        "genre": entry.genre or None,
                        "cues": marks,
                    }
                ],
                name=f"{entry.title or entry.track_id} Smart Cues",
                out_path=out_path,
                library=self._library,
            )
        except Exception as e:
            logger.warning("[viber] export_smart_cues failed: %s", e)
            return {"error": f"export_smart_cues failed: {type(e).__name__}: {e}"}

        self.exported = result
        return {
            "exported": True,
            "proposal_id": proposal.proposal_id,
            "track_id": proposal.track_id,
            "path": str(result.path),
            "cue_count": len(marks),
            "cue_ids": [str(mark.get("cue_id")) for mark in marks],
            "written": result.written,
            "dropped": result.dropped,
        }

    # -- DJ-knowledge / source capability tools (grounded; lazy modules) ---- #

    def quote_moment(self, args: dict[str, Any]) -> dict[str, Any]:
        """Point at a specific [start,end] moment inside a grounded track.

        GATE (invariant #2): track_id MUST be in ``seen`` (returned by a prior
        search_vibe/discover_pool this run) and MUST resolve in the live library
        — quote_moment threads ``self.seen`` so an invented id is rejected
        before a quote is ever built. Metadata only (no audio decode).
        """
        track_id = args.get("track_id")
        if not isinstance(track_id, str) or not track_id:
            return {"available": False, "error": "quote_moment: 'track_id' must be a string"}
        try:
            start_s = float(args.get("start_s"))
            end_s = float(args.get("end_s"))
        except (TypeError, ValueError):
            return {"available": False, "error": "quote_moment: start_s/end_s must be numbers"}
        label = args.get("label")
        label = label if isinstance(label, str) and label else None
        caption = args.get("caption")
        caption = caption if isinstance(caption, str) and caption.strip() else None
        from vibemix.library.quote_moment import resolve_quote

        return resolve_quote(
            self._library,
            track_id,
            start_s,
            end_s,
            label=label,
            caption=caption,
            seen=self.seen,
        )

    def retrieve_dj_knowledge(self, args: dict[str, Any]) -> dict[str, Any]:
        """TUTOR-lens grounding over the DJ-knowledge text store (link-out
        citations). Honest empty-results when no KB is on disk — never invents
        technique facts."""
        from vibemix.library.dj_knowledge import (
            DEFAULT_KNOWLEDGE_DIR,
            KnowledgeStore,
        )
        from vibemix.library.dj_knowledge import (
            retrieve_dj_knowledge as _retrieve,
        )

        query = args.get("query")
        if not isinstance(query, str) or not query.strip():
            return {"error": "retrieve_dj_knowledge: 'query' must be a non-empty string"}
        if self._knowledge_store is None:
            self._knowledge_store = KnowledgeStore.load(DEFAULT_KNOWLEDGE_DIR / "dj_knowledge")
        k = args.get("k", 4)
        embedder, embedder_error = self._resolve_knowledge_embedder(self._knowledge_store)
        if embedder_error:
            return {"error": embedder_error, "results": []}
        return _retrieve(
            self._knowledge_store,
            query,
            embedder=embedder,
            topic=args.get("topic"),
            skill_level=args.get("skill_level"),
            k=k if isinstance(k, int) else 4,
        )

    # -- dispatch (hard per-tool timeout; never raises) --------------------- #

    def _build_starvation_payload(
        self, last_tool: str, args: dict[str, Any]
    ) -> dict[str, Any]:
        """Phase 99 HARDEN-RETRY Decision 5: deterministic three-case hint.

        Built from the toolset's view of the world at threshold-trip time —
        NEVER LLM-generated (the hint must reflect REAL counter state, never
        invented text; this extends Cardinal Invariant #3 "trust the audio"
        to the curation surface).

        Three named cases, evaluated in order:
          A. Zero-track library — ``self._library.tracks`` is empty/falsy →
             the user has not run ``library ingest`` yet.
          B. No theme match — library has tracks AND the last tool was
             ``search_vibe`` (so the threshold tripped on empty results from
             a too-narrow theme).
          C. Tool error — last tool was NOT ``search_vibe``; threshold tripped
             on repeated ``{"error": ...}`` responses from some other handler.

        Hint copy is SEEDED per D-05; KAAN-ACTION
        §HARDEN-PHASE-A-EAR-PASS (parked at milestone close) polishes wording.
        Tests pin substring structure ("library has 0 tracks", "no tracks
        matched", "kept failing"), not full-string equality — ear-pass tolerant.

        T-99-02 (security): the ``theme`` user input (Case B) is interpolated
        into an f-string ONLY — never ``exec`` / ``eval``. Output destinations
        are stderr (CLI) + ``strip_leaks`` (Telegram, scrubs FS paths).
        """
        # Case A: zero-track library — user has not ingested anything yet.
        if not self._library.tracks:
            hint = "library has 0 tracks — run `library ingest` first"
        # Case B: library non-empty AND last tool was search_vibe →
        # theme was too narrow.
        elif last_tool == "search_vibe":
            theme = args.get("query", "")
            hint = (
                f"no tracks matched '{theme}' — try a broader theme or "
                f"different BPM range"
            )
        # Case C: library non-empty AND last tool was NOT search_vibe →
        # a non-discovery handler kept erroring out.
        else:
            hint = (
                f"tool '{last_tool}' kept failing — try again or check "
                f"codex installation"
            )
        return {
            "reason": "tool_starvation",
            "hint": hint,
            "tool": last_tool,
            "consecutive": self._consecutive_empties,
        }

    def _build_clarification_payload(
        self, question: str, choices: list[str]
    ) -> dict[str, Any]:
        """Phase 100 HARDEN-CLARIFY Decision 3: discriminated-union payload.

        Sibling of ``_build_starvation_payload`` (Plan 99-03). The wrapper
        side-channel writer (``_write_side_channel``, Plan 99-04) is REUSED
        UNCHANGED — its forward-compat docstring (line ~1096) authorizes the
        sibling extension by ``reason`` discriminator. Wrappers that read
        the side-channel file branch on ``payload.get("reason")`` and add
        an ``elif "clarification_needed":`` arm without restructuring the
        existing ``tool_starvation`` branch.

        Payload shape (locked by Plan 100-01 tests):
          * ``reason`` — discriminator, always the literal
            ``"clarification_needed"`` (NEVER LLM-generated).
          * ``question`` — the LLM-supplied clarification prompt (string,
            validated non-empty by the handler).
          * ``choices`` — list of 2-5 non-empty strings, defensively copied
            via ``list(choices)`` so caller-side mutation cannot corrupt
            the in-process ``stop_reason`` attr (mirrors the
            ``dict(self.stop_reason)`` shallow-copy posture in the
            dispatch-top terminal short-circuit at line ~1143).
          * ``tool`` — the literal ``"request_clarification"`` so
            downstream surfaces can disambiguate which handler tripped
            this terminal stop (mirrors the ``tool`` field
            ``_build_starvation_payload`` carries).

        Security/grounding note: ``question`` + ``choices`` originate from
        Codex's tool-call args (LLM reasoning over the user's theme), not
        arbitrary user input. Downstream surfaces (CLI stderr + Telegram
        ``format_reply``) defensively apply ``strip_leaks`` for any
        FS-path leak; Plan 100-01 only writes the in-process attr + the
        side-channel JSON.
        """
        return {
            "reason": "clarification_needed",
            "question": question,
            "choices": list(choices),
            "tool": "request_clarification",
        }

    def request_clarification(self, args: dict[str, Any]) -> dict[str, Any]:
        """Phase 100 HARDEN-CLARIFY Plan 100-01: Factor-7 clarification tool.

        Codex calls this when the user's theme is materially ambiguous and
        a single sensible default cannot be picked (e.g. "uplifting" —
        bedroom-headphones or peak-time-club? 80 BPM ambient or 130 BPM
        driving?). Instead of silently picking one heuristic, the LLM
        emits 2-5 specific choices that bound the disambiguation space.

        Decision 1 (signature): ``(self, args: dict)`` mirrors every other
        handler in this class — keeps the ``dispatch()`` contract uniform
        (one ``args`` dict in, one ``dict`` out, table-driven look-up at
        toolset.py:1145-1163).

        Decision 2 (length bounds): ``MIN_CHOICES <= len(choices) <=
        MAX_CHOICES``. Module constants for KAAN-ACTION tunability.

        Decision 3 (payload shape): on valid args, writes the
        discriminated-union clarification payload (built by the private
        helper above) to ``self.stop_reason``. The side-channel writer
        (``_write_side_channel``) is REUSED unchanged from Plan 99-04 —
        the writer is discriminator-agnostic and writes any payload that
        carries a ``reason`` key.

        Decision 4 (terminal semantics): writing ``self.stop_reason``
        trips the dispatch-top short-circuit at line ~1142. Every
        subsequent ``dispatch()`` call returns the terminal echo
        WITHOUT invoking any handler — single-turn semantic. The run
        ENDS at clarification; the wrapper (CLI / Telegram) renders the
        question + choices, the user composes a new theme, and Codex is
        restarted for the next run. This is Phase 99's terminal pattern
        sibling-extended — no new control flow.

        Decision 8 (test posture): unit-tested directly against the
        toolset via ``tests/library/test_toolset_clarification.py``
        (Plan 100-01 RED → GREEN).

        Rejection contract: invalid args return
        ``{"error": "...", "rejected": True}`` and DO NOT write
        ``self.stop_reason`` — the run CONTINUES so Codex can retry
        with corrected args. This is distinct from Phase 99's
        threshold-trip path, which IS terminal by design.

        Cardinal Invariant #2 (citation grounding): no track_id surface.
        Body reads ONLY ``args.get("question")`` and
        ``args.get("choices")`` — never ``args.get("track_id")`` /
        ``args.get("trackId")`` / etc. The handler MUST NOT touch
        ``self.seen`` / ``self.seen_sections`` / ``self.issued_*``.
        Plan 100-06 ships the AST gate at
        ``tests/library/test_request_clarification_no_track_surface.py``;
        the behavioral pin lives in Plan 100-01's test file
        (``test_no_track_id_surface_on_accept`` +
        ``test_handler_does_not_read_track_id_from_args``).

        Known cosmetic: Phase 99's dispatch-top short-circuit returns
        ``{"error": "tool_starvation", "stop_reason": ...}`` — the
        literal ``"error"`` value is ``"tool_starvation"`` regardless of
        which terminal reason fired. Wave 3-4 wrappers (Plan 100-03 /
        100-04) read ``payload.get("reason")`` from the inner
        ``stop_reason`` dict, NEVER the outer ``"error"`` key, so the
        cosmetic does not leak into user-visible surfaces. Out of scope
        for Plan 100-01.
        """
        question = args.get("question")
        choices = args.get("choices")

        # Validate question: must be a non-empty (after .strip()) str.
        if not isinstance(question, str) or not question.strip():
            return {
                "error": (
                    "request_clarification: 'question' must be a "
                    "non-empty string"
                ),
                "rejected": True,
            }

        # Validate choices: must be a list (NOT tuple/dict/str/...) of
        # MIN_CHOICES..MAX_CHOICES non-empty strings.
        if not isinstance(choices, list):
            return {
                "error": (
                    f"request_clarification: 'choices' must be a list of "
                    f"{MIN_CHOICES}-{MAX_CHOICES} non-empty strings"
                ),
                "rejected": True,
            }
        if len(choices) < MIN_CHOICES or len(choices) > MAX_CHOICES:
            return {
                "error": (
                    f"request_clarification: 'choices' must contain "
                    f"{MIN_CHOICES}-{MAX_CHOICES} entries; got "
                    f"{len(choices)}"
                ),
                "rejected": True,
            }
        for choice in choices:
            if not isinstance(choice, str) or not choice.strip():
                return {
                    "error": (
                        "request_clarification: every entry in 'choices' "
                        "must be a non-empty string"
                    ),
                    "rejected": True,
                }

        # Valid args. Write the terminal payload (sibling of Phase 99's
        # threshold-trip write at line ~1203) and ride the same side-
        # channel writer Plan 99-04 wired. The dispatch-top short-circuit
        # at line ~1142 turns every subsequent dispatch() call into an
        # idempotent terminal echo by construction — no new control flow.
        self.stop_reason = self._build_clarification_payload(question, choices)
        self._write_side_channel(self.stop_reason)
        # Return the payload to Codex so it sees its own tool call
        # succeeded; the dispatch-top short-circuit on the NEXT call is
        # what actually terminates the run.
        return {
            "clarification_needed": True,
            "question": question,
            "choices": list(choices),
        }

    def _write_side_channel(self, payload: dict[str, Any]) -> None:
        """Phase 99 HARDEN-RETRY Plan 99-04: Channel A cross-process write.

        If the side-channel env var (see ``os.environ.get`` call below)
        is set, write ``payload`` as JSON to that path so the parent-process
        wrapper
        (``codex_curate.curate_with_codex`` / ``build_set_with_codex``) can
        read it after the Codex CLI subprocess exits. RESEARCH.md
        § Stop-Reason Propagation Channel locked this as Channel A — the
        load-bearing seam that bypasses the LLM entirely.

        If the env var is ABSENT or empty, this is a silent no-op — direct
        CLI usage and unit tests without the env var keep working with only
        the in-process ``stop_reason`` write from Plan 99-03 (no
        regression).

        Best-effort write: an FS issue (read-only fs, permission denied,
        bad path) catches the ``OSError`` and returns silently. Never wedge
        ``dispatch()`` on a side-channel failure — the in-process payload
        is the authoritative surface; the file is observability/propagation.

        Forward-compat (Phase 100): the payload's ``reason`` field is the
        discriminator. Phase 100 will reuse the same file with
        ``reason="clarification_needed"``; this writer is unchanged.
        """
        path = os.environ.get("VIBEMIX_STOP_REASON_FILE")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(payload, f)
        except (OSError, TypeError, ValueError):
            # Best-effort — never wedge dispatch on FS / encoding /
            # serialization issues. The in-process ``self.stop_reason`` is the
            # authoritative surface; this file is observability + propagation
            # only, so an over-broad catch here is safer than letting an
            # unexpected exception escape into the dispatch return path.
            # (UnicodeEncodeError ⊂ UnicodeError ⊂ ValueError.)
            return

    @staticmethod
    def _tool_event_arg_summary(name: str, args: dict[str, Any] | None) -> str:
        """Short, redacted argument label for the live tool tape."""
        if not isinstance(args, dict):
            return ""

        def text(key: str, *, limit: int = 80) -> str:
            raw = args.get(key)
            if raw is None:
                return ""
            return str(raw).replace("\n", " ").strip()[:limit]

        def count(key: str) -> int | None:
            raw = args.get(key)
            return len(raw) if isinstance(raw, (list, tuple)) else None

        if name in ("search_vibe", "discover_pool"):
            parts = [text("query")]
            bpm_min = args.get("bpm_min")
            bpm_max = args.get("bpm_max")
            if bpm_min is not None or bpm_max is not None:
                parts.append(f"bpm={bpm_min or '?'}-{bpm_max or '?'}")
            min_duration_s = args.get("min_duration_s")
            max_duration_s = args.get("max_duration_s")
            if min_duration_s is not None:
                parts.append(f"min_dur={min_duration_s}s")
            if max_duration_s is not None:
                parts.append(f"max_dur={max_duration_s}s")
            if args.get("k") is not None:
                parts.append(f"k={args.get('k')}")
            return "; ".join(p for p in parts if p)[:160]
        if name in ("get_track_features", "get_track_energy", "get_track_sections"):
            return text("track_id", limit=120)
        if name == "inspect_candidates":
            n = count("track_ids")
            return f"{n} tracks" if n is not None else ""
        if name == "sequence_set":
            n = count("track_ids")
            parts = [text("curve", limit=40), f"{n} tracks" if n is not None else ""]
            if args.get("n_slots") is not None:
                parts.append(f"slots={args.get('n_slots')}")
            novelty = args.get("novelty", args.get("novelty_weight", args.get("surprise_weight")))
            if novelty is not None:
                parts.append(f"novelty={novelty}")
            return "; ".join(p for p in parts if p)[:160]
        if name in ("create_playlist", "export_set"):
            n = count("track_ids")
            parts = [text("name", limit=80), f"{n} tracks" if n is not None else ""]
            return "; ".join(p for p in parts if p)[:160]
        if name == "transition_slate":
            n = count("candidate_track_ids")
            parts = [text("mode", limit=40), f"{n} candidates" if n is not None else ""]
            source = text("source_section_id", limit=40) or text("source_track_id", limit=40)
            if source:
                parts.append(f"source={source}")
            return "; ".join(p for p in parts if p)[:160]
        if name == "compile_musical_context":
            n = count("candidate_ids")
            parts = [text("mode", limit=40), f"{n} candidates" if n is not None else ""]
            intent = text("intent", limit=70)
            if intent:
                parts.append(intent)
            return "; ".join(p for p in parts if p)[:160]
        if name == "request_clarification":
            return text("question", limit=140)
        if name in ("web_search", "retrieve_dj_knowledge"):
            return text("query", limit=140)
        if name == "fetch_url":
            return text("url", limit=140)
        if name == "quote_moment":
            return text("track_id", limit=80)
        if name == "smart_hot_cues":
            n = count("track_ids")
            parts = [text("track_id", limit=80), f"{n} tracks" if n is not None else ""]
            return "; ".join(p for p in parts if p)[:160]
        if name == "export_smart_cues":
            return text("proposal_id", limit=120)

        for key in ("query", "name", "track_id", "proposal_id", "mode"):
            value = text(key)
            if value:
                return value[:160]
        return ""

    @staticmethod
    def _tool_event_summary(name: str, result: dict[str, Any]) -> str:
        """A short human one-liner for the live tool tape (≤160 chars).

        Errors carry their (now legible) message; discovery tools carry a
        count; the rest fall back to a plain "ok". Deliberately tolerant of
        unknown result shapes — the tape must never crash on a new tool."""
        if not isinstance(result, dict):
            return ""
        err = result.get("error")
        if err is not None:
            return str(err)[:160]
        if name in ("search_vibe", "discover_pool"):
            items = result.get("results")
            if items is None:
                items = result.get("pool") or result.get("track_ids") or []
            n = len(items) if isinstance(items, (list, tuple)) else 0
            parts = [f"{n} track{'' if n == 1 else 's'}"]
            warnings = result.get("metadata_warnings")
            if isinstance(warnings, list):
                for warning in warnings:
                    if not isinstance(warning, dict) or warning.get("field") != "bpm":
                        continue
                    unknown = warning.get("unknown_count")
                    total = warning.get("total_count")
                    if unknown is not None and total is not None:
                        parts.append(f"bpm_unknown={unknown}/{total}")
                    break
            return "; ".join(parts)[:160]
        if name == "sequence_set":
            # sequence_set returns ranked {"candidates": [{track_ids, …}]}.
            cands = result.get("candidates")
            if isinstance(cands, (list, tuple)):
                n = len(cands)
                parts = [f"{n} candidate{'' if n == 1 else 's'}"]
                deduped = result.get("deduped_track_ids")
                if isinstance(deduped, list) and deduped:
                    parts.append(f"deduped={len(deduped)}")
                return "; ".join(parts)
        if name == "inspect_candidates":
            rows = result.get("candidates")
            if isinstance(rows, (list, tuple)):
                n = len(rows)
                return f"{n} candidate inspection{'' if n == 1 else 's'}"
        if name in ("create_playlist", "export_set"):
            ids = result.get("track_ids")
            if ids is None:
                pl = result.get("playlist")
                ids = pl.get("track_ids") if isinstance(pl, dict) else None
            if isinstance(ids, (list, tuple)):
                n = len(ids)
                return f"{n} track{'' if n == 1 else 's'}"
        # Unknown shape: the tool NAME + ok/err is the signal; no noisy "ok".
        return ""

    @staticmethod
    def _tool_event_receipt(name: str, result: dict[str, Any]) -> dict[str, Any] | None:
        """Structured, redacted receipt for tool events that write artifacts.

        The live tape's human summary stays tiny, but parent processes also need
        enough machine-readable data to render "where did my DJ-software handoff
        land?" after Codex exits. Keep this limited to artifact paths/counts and
        export receipts; never include raw candidate vectors or broad metadata.
        """
        if name != "export_set" or not isinstance(result, dict) or result.get("error"):
            return None
        receipt: dict[str, Any] = {}
        for key in ("target", "path"):
            value = result.get(key)
            if isinstance(value, str) and value:
                receipt[key] = value
        outputs = result.get("outputs")
        if isinstance(outputs, dict):
            receipt["outputs"] = {
                str(key): str(value)
                for key, value in outputs.items()
                if isinstance(key, str) and isinstance(value, str)
            }
        for key in ("tag_receipts", "import_instructions"):
            rows = result.get(key)
            if isinstance(rows, list):
                receipt[key] = [dict(row) for row in rows if isinstance(row, dict)]
        auto_cues = result.get("auto_cues")
        if isinstance(auto_cues, dict):
            receipt["auto_cues"] = dict(auto_cues)
        pill = result.get("pill_cues_materialized")
        if isinstance(pill, dict):
            receipt["pill_cues_materialized"] = dict(pill)
        return receipt or None

    def _emit_tool_event(
        self, name: str, result: dict[str, Any], args: dict[str, Any] | None = None
    ) -> None:
        """Append one tool-call record to the live tool-event side-channel.

        Mirrors ``_write_side_channel`` exactly: env-gated
        (``VIBEMIX_TOOL_EVENTS_FILE``), best-effort, never raises. One JSONL
        line per call (append, not overwrite) so the parent wrapper can tail
        the file and surface each tool the agent fires — search, sequence,
        create — the moment it fires, turning the opaque Codex run into a
        visible agentic tape. Silent no-op when the env var is absent, so
        direct CLI usage and unit tests are unaffected."""
        path = os.environ.get("VIBEMIX_TOOL_EVENTS_FILE")
        if not path:
            return
        import time  # local — `time` is not a module-top import here

        record = {
            "tool": name,
            "arg": self._tool_event_arg_summary(name, args),
            "ok": not (isinstance(result, dict) and result.get("error") is not None),
            "summary": self._tool_event_summary(name, result),
            "ts": time.time(),
        }
        receipt = self._tool_event_receipt(name, result)
        if receipt is not None:
            record["receipt"] = receipt
        try:
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
        except (OSError, TypeError, ValueError):
            # Best-effort — never wedge dispatch on a tape write (mirrors the
            # _write_side_channel rationale). The tape is observability only.
            return

    def _is_empty_or_error(self, name: str, result: dict[str, Any]) -> bool:
        """Phase 99 HARDEN-RETRY Decision 2: identify counter-incrementing returns.

        True if ``result`` is an error dict OR an empty ``search_vibe`` result.
        Other handlers' empty returns (e.g. ``discover_pool`` with an empty pool)
        do NOT count — Decision 2 locked only ``search_vibe`` for the empty-list
        trigger; everything else counts only via the ``{"error": ...}`` path.

        This predicate is the SINGLE source of truth for empty/error detection
        and is consulted exactly once per ``dispatch()`` call. Plan 99-03 reuses
        it from the same call site for the threshold-trip wiring.
        """
        if isinstance(result, dict) and result.get("error") is not None:
            return True
        if name == "search_vibe":
            return not result.get("results")
        return False

    def dispatch(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        # ─── PHASE 99 HOOK (Plan 99-03 — terminal short-circuit) ─────────
        # Once the threshold has tripped (the ``stop_reason`` attr is set),
        # the run is TERMINAL. Every subsequent ``dispatch()`` call returns
        # the same idempotent terminal echo WITHOUT invoking any handler —
        # which is why the counter freezes at threshold (the ``else``
        # counter-reset branch below is unreachable after a trip). The
        # shallow copy prevents callers from mutating the internal payload
        # (RESEARCH.md Open Q2).
        if self.stop_reason is not None:
            return {"error": "tool_starvation", "stop_reason": dict(self.stop_reason)}

        handlers: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
            "search_vibe": self.search_vibe,
            "get_track_features": self.get_track_features,
            "get_track_sections": self.get_track_sections,
            "inspect_candidates": self.inspect_candidates,
            "transition_slate": self.transition_slate,
            "compile_musical_context": self.compile_musical_context,
            "smart_hot_cues": self.smart_hot_cues,
            "create_playlist": self.create_playlist,
            "get_track_energy": self.get_track_energy,
            "discover_pool": self.discover_pool,
            "sequence_set": self.sequence_set,
            "ingest_source": self.ingest_source,
            "export_set": self.export_set,
            "export_smart_cues": self.export_smart_cues,
            "web_search": self.web_search,
            "fetch_url": self.fetch_url,
            "quote_moment": self.quote_moment,
            "request_clarification": self.request_clarification,
            "retrieve_dj_knowledge": self.retrieve_dj_knowledge,
        }
        handler = handlers.get(name)
        if handler is None:
            return {"error": f"unknown tool {name!r}"}
        freshness_block = self._freshness_guard_for_tool(name)
        if freshness_block is not None:
            self._emit_tool_event(name, freshness_block, args)
            return freshness_block
        # Hard per-tool timeout — a pathological handler can never park the loop.
        if name == "ingest_source":
            timeout_s = INGEST_TOOL_CALL_TIMEOUT_S
        elif name == "inspect_candidates":
            timeout_s = BATCH_TOOL_CALL_TIMEOUT_S
        else:
            timeout_s = TOOL_CALL_TIMEOUT_S
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            fut = ex.submit(handler, args)
            try:
                result = fut.result(timeout=timeout_s)
            except concurrent.futures.TimeoutError:
                result = {"error": f"tool {name!r} timed out"}
            except Exception as e:
                result = {"error": f"tool {name!r} crashed: {type(e).__name__}: {e}"}

        # ─── LIVE TOOL TAPE — make the agentic work visible ──────────────
        # Append one record per call to the tool-event side-channel so the
        # parent wrapper can tail it and stream "what Viber is doing" to the
        # UI as it happens, instead of the run being opaque until the final
        # result. Env-gated + best-effort (mirrors ``_write_side_channel``).
        self._emit_tool_event(name, result, args)

        # ─── PHASE 99 HOOK (Plan 99-02 — counter telemetry, no terminal) ───
        # Counter writes confined to the dispatch-calling thread (NEVER the
        # ThreadPoolExecutor worker thread that ran ``handler``). Safe by
        # construction: the worker has been joined via ``fut.result()`` /
        # the surrounding ``with ThreadPoolExecutor`` block exited before
        # this point. The serialization guarantee is the same one
        # documented at toolset.py:407-411 for the lazy ``_genre_lookup``.
        # Plan 99-03 will extend this block with the threshold trip +
        # the ``stop_reason`` payload write. ``return result`` below is
        # byte-equivalent to pre-plan behavior.
        if self._is_empty_or_error(name, result):
            self._consecutive_empties += 1
            # ─── PHASE 99 HOOK (Plan 99-03 — threshold trip, terminal write) ─
            # First-write-wins: the ``stop_reason is None`` guard makes
            # the payload write idempotent under any conceivable racy path
            # (T-99-03 mitigation, though the dispatch-calling-thread
            # serialization at 407-411 prevents the race in the first
            # place). After this assignment, the short-circuit at the top
            # of ``dispatch()`` returns the terminal echo on every
            # subsequent call. Plan 99-04: the side-channel write rides
            # the same first-write-wins guard, so the file lands exactly
            # once (env-var-conditional, silent no-op when absent).
            if (
                self._consecutive_empties >= TOOL_STARVATION_THRESHOLD
                and self.stop_reason is None
            ):
                self.stop_reason = self._build_starvation_payload(
                    last_tool=name, args=args
                )
                self._write_side_channel(self.stop_reason)
        else:
            self._consecutive_empties = 0

        return result

    def _resolve_source_section(
        self, source_section_id: Any, source_track_id: Any
    ) -> SectionRecord | dict[str, str]:
        if isinstance(source_section_id, str) and source_section_id:
            section = self.seen_sections.get(source_section_id)
            if section is None:
                return {
                    "error": (
                        "transition_slate: source_section_id was not issued by "
                        f"get_track_sections this run: {source_section_id!r}"
                    )
                }
            return section
        if not isinstance(source_track_id, str) or not source_track_id:
            return {"error": ("transition_slate: provide 'source_section_id' or 'source_track_id'")}
        if source_track_id not in self.seen:
            return {
                "error": (
                    "rejected: source_track_id was never returned by search_vibe/"
                    f"discover_pool this run (invented): {source_track_id!r}"
                )
            }
        entry = self._library.lookup_by_id(source_track_id)
        if entry is None:
            return {"error": f"unknown source_track_id {source_track_id!r}"}
        sections = sections_for_entry(entry)
        for section in sections:
            self.seen_sections[section.section_id] = section
        return best_source_section(sections)

    def _resolve_destination_sections(self, track_ids: list[Any]) -> list[SectionRecord]:
        out: list[SectionRecord] = []
        for track_id in track_ids:
            if not isinstance(track_id, str):
                continue
            entry = self._library.lookup_by_id(track_id)
            if entry is None:
                continue
            sections = sections_for_entry(entry)
            for section in sections:
                self.seen_sections[section.section_id] = section
            out.extend(destination_sections(sections))
        return out

    def _track_vector(self, track_id: str) -> Any | None:
        try:
            from vibemix.library.next_suggestion import seed_vector_for_track_id

            return seed_vector_for_track_id(self._store, track_id)
        except Exception:
            return None

    def _section_vector(self, section: SectionRecord) -> Any:
        return resolve_section_vector(
            self._store,
            section.section_id,
            fallback_vector=self._track_vector(section.track_id),
        )


def _normalize_ingest_source_name(raw: Any) -> str | None:
    if raw is None:
        return "auto"
    if not isinstance(raw, str):
        return None
    value = raw.strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "": "auto",
        "detect": "auto",
        "dj_library": "auto",
        "music_folder": "folder",
        "raw_folder": "folder",
        "rekordbox_xml": "rekordbox",
        "collection_xml": "rekordbox",
        "xml": "rekordbox",
        "traktor_nml": "traktor",
        "nml": "traktor",
        "database_v2": "serato",
        "serato_database": "serato",
        "virtual_dj": "virtualdj",
        "virtualdj_database": "virtualdj",
        "engine_dj": "engine",
        "engine_prime": "engine",
    }
    value = aliases.get(value, value)
    return value if value in _INGEST_SOURCE_NAMES else None


def _ingest_path_arg(raw: Any) -> tuple[pathlib.Path | None, str | None]:
    if raw is None:
        return None, None
    if not isinstance(raw, str):
        return None, "'path' must be a string when provided"
    stripped = raw.strip()
    if not stripped:
        return None, None
    try:
        return pathlib.Path(stripped).expanduser(), None
    except (RuntimeError, OSError) as exc:
        return None, f"could not resolve path: {exc}"


def _infer_ingest_route(path: pathlib.Path | None) -> dict[str, Any] | None:
    if path is not None:
        catalog = _catalog_source_for_path(path)
        if catalog is not None:
            return {"kind": "catalog", "source": catalog}
        if path.is_dir():
            return {"kind": "folder", "path": path}
        return None

    for source_name in ("rekordbox", "serato", "traktor", "virtualdj", "engine"):
        source = _source_for_name(source_name, None)
        try:
            if source.detect():
                return {"kind": "catalog", "source": source}
        except Exception:
            continue
    return None


def _ingest_route_for_source(source_name: str, path: pathlib.Path | None) -> dict[str, Any] | None:
    if source_name == "folder":
        if path is not None and path.is_dir():
            return {"kind": "folder", "path": path}
        return None
    return {"kind": "catalog", "source": _source_for_name(source_name, path)}


def _source_for_name(source_name: str, path: pathlib.Path | None) -> Any:
    path_str = str(path) if path is not None else None
    if source_name == "traktor":
        from vibemix.library.sources.traktor import TraktorSource

        return TraktorSource(nml_path=path_str) if path_str else TraktorSource()
    if source_name == "virtualdj":
        from vibemix.library.sources.virtualdj import VirtualDJSource

        return VirtualDJSource(database_path=path_str) if path_str else VirtualDJSource()
    if source_name == "engine":
        from vibemix.library.sources.engine import EngineDJSource

        return EngineDJSource(database_path=path_str) if path_str else EngineDJSource()
    if source_name == "serato":
        from vibemix.library.sources.serato import SeratoSource

        return SeratoSource(library_path=path_str) if path_str else SeratoSource()

    from vibemix.library.sources.rekordbox import RekordboxSource

    return RekordboxSource(xml_path=path_str) if path_str else RekordboxSource()


def _catalog_source_for_path(path: pathlib.Path) -> Any | None:
    if path.is_dir() and (path / "database V2").is_file():
        return _source_for_name("serato", path)

    lower_name = path.name.lower()
    suffix = path.suffix.lower()
    if suffix == ".nml":
        return _source_for_name("traktor", path)
    if lower_name == "database.xml":
        return _source_for_name("virtualdj", path)
    if lower_name == "m.db" or suffix == ".db":
        return _source_for_name("engine", path)
    if lower_name == "database v2":
        return _source_for_name("serato", path)
    if suffix == ".xml":
        return _source_for_name("rekordbox", path)
    return None


def _ingest_missing_source_payload(source_name: str, path: pathlib.Path | None) -> dict[str, Any]:
    if source_name == "folder":
        return {"error": "ingest_source: source='folder' requires an existing directory path"}
    if path is None:
        return {
            "error": (
                "ingest_source: no supported DJ library detected. Pass "
                "source='rekordbox', 'serato', 'traktor', 'virtualdj', 'engine', "
                "or 'folder' with a local path."
            )
        }
    return {
        "error": (
            "ingest_source: could not infer a supported catalog source from "
            f"{str(path)!r}"
        )
    }


def _ingest_source_not_detected_payload(source_name: str, source: Any) -> dict[str, Any]:
    try:
        probed = [str(path) for path in source.default_paths()]
    except Exception:
        probed = []
    return {
        "error": (
            f"ingest_source: no {source_name} catalog detected"
            + (f"; probed={probed}" if probed else "")
        )
    }


def _ingest_tool_report(
    *,
    source: str,
    catalog: str,
    report: Any,
    refreshed_tracks: int,
) -> dict[str, Any]:
    as_dict = getattr(report, "as_dict", None)
    if callable(as_dict):
        report_dict = as_dict()
    else:
        report_dict = {
            "total": int(getattr(report, "total", 0)),
            "embedded": int(getattr(report, "embedded", 0)),
            "skipped_cached": int(getattr(report, "skipped_cached", 0)),
            "failed": int(getattr(report, "failed", 0)),
        }
    return {
        "ingested": True,
        "source": source,
        "catalog": catalog,
        "total": int(report_dict.get("total", 0)),
        "embedded": int(report_dict.get("embedded", 0)),
        "skipped_cached": int(report_dict.get("skipped_cached", 0)),
        "failed": int(report_dict.get("failed", 0)),
        "library_tracks": refreshed_tracks,
        "report": report_dict,
    }


def _export_cues_and_grid(entry: Any) -> dict[str, Any]:
    """Return optional Rekordbox cue + beatgrid payload for export_set."""
    out: dict[str, Any] = {}

    cues = []
    for cue in getattr(entry, "cues", ()) or ():
        payload: dict[str, Any] = {
            "name": getattr(cue, "name", "") or "",
            "type": getattr(cue, "type", "cue") or "cue",
            "start_s": getattr(cue, "start_s", 0.0),
            "num": getattr(cue, "number", -1),
            "source": getattr(cue, "source", "dj") or "dj",
        }
        end_s = getattr(cue, "end_s", None)
        if end_s is not None:
            payload["end_s"] = end_s
        cues.append(payload)
    if cues:
        out["cues"] = cues

    beatgrid = getattr(entry, "beatgrid", ()) or ()
    first_tempo = beatgrid[0] if beatgrid else None
    if first_tempo is not None:
        out["beatgrid"] = {
            "inizio": getattr(first_tempo, "inizio_s", 0.0),
            "bpm": getattr(first_tempo, "bpm", None),
            "metro": getattr(first_tempo, "metro", "") or "4/4",
            "battito": getattr(first_tempo, "battito", 1),
        }
    elif getattr(entry, "bpm", 0.0) and entry.bpm > 0:
        out["beatgrid"] = {"bpm": entry.bpm}

    return out


def _export_target_arg(raw: Any) -> str:
    value = str(raw or "both").strip().lower().replace("-", "_")
    aliases = {
        "all_dj": "all",
        "xml": "rekordbox",
        "rekordbox_xml": "rekordbox",
        "playlist": "m3u8",
        "crate": "m3u8",
        "portable": "both",
        "serato": "serato_tags",
        "serato_markers2": "serato_tags",
        "markers2": "serato_tags",
        "tags": "serato_tags",
        "mixxx": "mixxx_tags",
    }
    value = aliases.get(value, value)
    if value in {"rekordbox", "m3u8", "both", "serato_tags", "mixxx_tags", "all"}:
        return value
    raise ValueError(
        "target must be one of 'rekordbox', 'm3u8', 'both', "
        "'serato_tags', 'mixxx_tags', 'all'"
    )


def _target_wants_rekordbox(target: str) -> bool:
    return target in {"rekordbox", "both", "all"}


def _target_wants_m3u8(target: str) -> bool:
    return target in {"m3u8", "both", "all"}


def _target_wants_tags(target: str) -> bool:
    return target in {"serato_tags", "mixxx_tags", "all"}


def _markers2_carrier_for_target(
    target: str,
) -> Literal["serato_tags", "mixxx_tags", "markers2_tags"]:
    if target == "mixxx_tags":
        return "mixxx_tags"
    if target == "all":
        return "markers2_tags"
    return "serato_tags"


def _export_import_instructions(
    outputs: dict[str, str],
    tag_receipts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Human import/reload receipt for each carrier written by export_set."""
    instructions: list[dict[str, Any]] = []
    if path := outputs.get("rekordbox"):
        instructions.append(
            {
                "app": "Rekordbox",
                "carrier": "rekordbox_xml",
                "path": path,
                "writes_audio_tags": False,
                "instruction": (
                    "Preferences -> Bridge -> Imported Library, choose this XML, "
                    "then drag the exported playlist into your collection."
                ),
            }
        )
    if path := outputs.get("m3u8"):
        instructions.append(
            {
                "app": "Any DJ app",
                "carrier": "m3u8",
                "path": path,
                "writes_audio_tags": False,
                "instruction": (
                    "Import this M3U8 as an additive playlist/crate. It carries order; "
                    "cues ride through Rekordbox XML or Markers2 tags."
                ),
            }
        )
    for receipt in tag_receipts:
        if not isinstance(receipt, dict):
            continue
        files = [str(path) for path in receipt.get("files", []) if isinstance(path, str)]
        if not files:
            continue
        apps = receipt.get("compatible_apps")
        app_names = ", ".join(str(app) for app in apps if isinstance(app, str)) or "Serato/Mixxx"
        instructions.append(
            {
                "app": app_names,
                "carrier": str(receipt.get("carrier") or "markers2_tags"),
                "files": files,
                "writes_audio_tags": True,
                "instruction": (
                    "Reload or rescan these tagged audio files in the DJ app. "
                    "VM cues are written as Markers2 tags with explicit permission; "
                    "existing cues on other pads are merged, not clobbered."
                ),
            }
        )
    return instructions


def _write_export_set_markers2_tags(
    items: list[dict[str, Any]],
    *,
    carrier: Literal["serato_tags", "mixxx_tags", "markers2_tags"],
    granted: bool,
) -> dict[str, Any]:
    from vibemix.library.export_serato import marks_to_serato_cues, write_serato_cues

    tagged = 0
    cues_total = 0
    files: list[str] = []
    skipped: list[dict[str, str]] = []
    for item in items:
        filepath = str(item.get("filepath") or "")
        if not filepath:
            skipped.append(
                {"track_id": str(item.get("track_id") or ""), "reason": "missing filepath"}
            )
            continue
        marks = [mark for mark in item.get("cues", ()) or () if isinstance(mark, dict)]
        if not marks:
            skipped.append({"track_id": str(item.get("track_id") or ""), "reason": "no cue marks"})
            continue
        res = write_serato_cues(
            filepath,
            marks_to_serato_cues(marks),
            merge=True,
            allow_write=granted,
        )
        if res.get("written"):
            tagged += 1
            cues_total += int(res.get("cue_count", len(marks)) or 0)
            files.append(str(res.get("path") or filepath))
        else:
            skipped.append(
                {
                    "track_id": str(item.get("track_id") or ""),
                    "filepath": filepath,
                    "reason": str(res.get("reason") or "not written"),
                }
            )
    return {
        "carrier": carrier,
        "compatible_apps": ["Serato", "Mixxx"],
        "tagged": tagged,
        "cues_total": cues_total,
        "skipped": len(skipped),
        "files": files,
        "skipped_tracks": skipped,
    }


def _default_set_export_path(name: str, *, suffix: str) -> pathlib.Path:
    slug = (
        "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in name.strip().lower()).strip(
            "-"
        )
        or "set"
    )
    return pathlib.Path.home() / "Music" / "vibemix" / "cues" / f"{slug}{suffix}"


def _with_export_suffix(path: str | pathlib.Path, suffix: str) -> pathlib.Path:
    out = pathlib.Path(path)
    return out if out.suffix.lower() == suffix else out.with_suffix(suffix)


_MACHINE_CUE_SOURCES = {"auto", "anlz", "fallback"}


def _snap_machine_cues_to_export_grid(cue_payload: dict[str, Any]) -> dict[str, float | int]:
    """Quantize machine-authored cue marks to the beatgrid this XML exports.

    Rekordbox imports the cue timestamp and the TEMPO grid independently. When a
    track has no persisted Rekordbox grid, ``_export_cues_and_grid`` emits a
    constant-BPM grid starting at 0.0; auto/anlz/fallback cue marks must land on
    that same grid or the pad appears off-beat after import. DJ-authored cue
    marks are preserved exactly.
    """
    grid = _export_grid_params(cue_payload)
    if grid is None:
        return {"adjusted_count": 0, "max_adjustment_ms": 0.0}
    inizio_s, bpm = grid
    beat_s = 60.0 / bpm
    adjusted_count = 0
    max_adjustment_ms = 0.0
    for mark in cue_payload.get("cues", ()) or ():
        if not isinstance(mark, dict) or not _is_machine_cue_mark(mark):
            continue
        try:
            start_s = float(mark.get("start_s", 0.0))
        except (TypeError, ValueError):
            continue
        snapped_s = max(0.0, inizio_s + round((start_s - inizio_s) / beat_s) * beat_s)
        delta_s = snapped_s - start_s
        if abs(delta_s) <= 1e-9:
            continue
        mark["start_s"] = round(snapped_s, 6)
        if mark.get("end_s") is not None:
            try:
                mark["end_s"] = round(max(0.0, float(mark["end_s"]) + delta_s), 6)
            except (TypeError, ValueError):
                pass
        adjusted_count += 1
        max_adjustment_ms = max(max_adjustment_ms, abs(delta_s) * 1000.0)
    return {
        "adjusted_count": adjusted_count,
        "max_adjustment_ms": round(max_adjustment_ms, 3),
    }


def _export_grid_params(cue_payload: dict[str, Any]) -> tuple[float, float] | None:
    raw_grid = cue_payload.get("beatgrid")
    if not isinstance(raw_grid, dict):
        return None
    try:
        bpm = float(raw_grid.get("bpm", 0.0) or 0.0)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(bpm) or bpm <= 0:
        return None
    try:
        inizio_s = float(raw_grid.get("inizio", 0.0) or 0.0)
    except (TypeError, ValueError):
        inizio_s = 0.0
    if not math.isfinite(inizio_s):
        inizio_s = 0.0
    return inizio_s, bpm


def _is_machine_cue_mark(mark: dict[str, Any]) -> bool:
    source = str(mark.get("source", "") or "").strip().lower()
    if source == "dj":
        return False
    if source in _MACHINE_CUE_SOURCES:
        return True
    name = str(mark.get("name", "") or "")
    return name.startswith("VM ")


def _auto_cue_report(*, enabled: bool) -> dict[str, Any]:
    return {
        "enabled": enabled,
        "tracks_attempted": 0,
        "tracks_cued": 0,
        "cues_added": 0,
        "snap_adjusted_count": 0,
        "snap_max_adjustment_ms": 0.0,
        "skipped_tracks": 0,
        "skipped_failed": 0,
        "proposal_export_ready_count": 0,
        "proposal_review_count": 0,
        "proposal_missing_required_count": 0,
        "proposal_suppressed_count": 0,
    }


def _auto_cue_marks_for_export(
    entry: Any,
    *,
    genre: str | None,
    occupied_slots: set[int],
) -> tuple[list[dict[str, Any]], Any]:
    from vibemix.library.cue_landing import cue_set_from_proposal, export_marks_for_cueset
    from vibemix.library.smart_cues import propose_smart_cues

    proposal = propose_smart_cues(entry, sections_for_entry(entry), genre=genre)
    marks = export_marks_for_cueset(
        cue_set_from_proposal(
            entry,
            proposal,
            include_review=False,
            include_preserved=False,
        )
    )
    if not marks and getattr(entry, "filepath", None):
        try:
            from vibemix.library.cue_engine import detect_cues_auto
            from vibemix.library.cue_landing import sections_from_anchors

            anchors = detect_cues_auto(entry.filepath, max_cues=8)
        except Exception:
            anchors = []
        if anchors:
            proposal = propose_smart_cues(
                entry,
                sections_from_anchors(entry, anchors),
                genre=genre,
            )
            marks = export_marks_for_cueset(
                cue_set_from_proposal(
                    entry,
                    proposal,
                    include_review=False,
                    include_preserved=False,
                )
            )
    fill_empty_only = [
        mark
        for mark in marks
        if _mark_hotcue_slot(mark) is None or _mark_hotcue_slot(mark) not in occupied_slots
    ]
    return fill_empty_only, proposal.summary


def _add_auto_cue_summary(report: dict[str, Any], summary: Any, cue_count: int) -> None:
    report["proposal_export_ready_count"] += int(getattr(summary, "export_ready_count", 0) or 0)
    report["proposal_review_count"] += int(getattr(summary, "review_count", 0) or 0)
    report["proposal_missing_required_count"] += int(
        getattr(summary, "missing_required_count", 0) or 0
    )
    report["proposal_suppressed_count"] += int(getattr(summary, "suppressed_count", 0) or 0)
    if cue_count > 0:
        report["tracks_cued"] += 1
        report["cues_added"] += cue_count
    else:
        report["skipped_tracks"] += 1


def _add_auto_cue_snap_summary(report: dict[str, Any], stats: dict[str, float | int]) -> None:
    adjusted = int(stats.get("adjusted_count", 0) or 0)
    if adjusted <= 0:
        return
    report["snap_adjusted_count"] += adjusted
    report["snap_max_adjustment_ms"] = max(
        float(report.get("snap_max_adjustment_ms", 0.0) or 0.0),
        float(stats.get("max_adjustment_ms", 0.0) or 0.0),
    )


def _materialize_landed_machine_cues_for_pill(
    library: RekordboxLibrary,
    items: list[dict[str, Any]],
) -> dict[str, int]:
    """Mirror successful export-time VM cue rows into the live library object.

    ``export_set`` can fill empty A-H slots from smart cues even when the source
    ``TrackEntry`` had no cue rows. Without this overlay the DJ software receives
    the VM pads but the running next-suggestion pill still sees an uncued entry
    until the user re-imports/re-ingests. This keeps the immediate runtime
    honest: only machine cues that just went through a successful carrier write
    become visible to the live pill, and DJ-authored slots remain untouched.
    """
    tracks_updated = 0
    cues_materialized = 0
    for item in items:
        track_id = str(item.get("track_id") or "")
        entry = library.lookup_by_id(track_id) if track_id else None
        if entry is None:
            continue
        existing = list(getattr(entry, "cues", ()) or ())
        occupied_slots = {
            int(cue.number)
            for cue in existing
            if getattr(cue, "type", "") in {"cue", "loop"} and 0 <= int(cue.number) <= 7
        }
        additions: list[CuePoint] = []
        for mark in item.get("cues", ()) or ():
            cue = _live_pill_cue_from_export_mark(mark, occupied_slots)
            if cue is None:
                continue
            additions.append(cue)
            if 0 <= cue.number <= 7:
                occupied_slots.add(cue.number)
        if not additions:
            continue
        merged = tuple(
            sorted(
                [*existing, *additions],
                key=lambda cue: (float(getattr(cue, "start_s", 0.0) or 0.0), int(cue.number)),
            )
        )
        library.tracks[entry.track_id] = replace(entry, cues=merged)
        tracks_updated += 1
        cues_materialized += len(additions)
    return {"tracks": tracks_updated, "cues": cues_materialized}


def _live_pill_cue_from_export_mark(
    mark: Any,
    occupied_slots: set[int],
) -> CuePoint | None:
    if not isinstance(mark, dict) or not _is_machine_cue_mark(mark):
        return None
    slot = _mark_hotcue_slot(mark)
    if slot is not None and slot in occupied_slots:
        return None
    try:
        start_s = float(mark.get("start_s", 0.0) or 0.0)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(start_s) or start_s < 0:
        return None
    try:
        end_raw = mark.get("end_s")
        end_s = float(end_raw) if end_raw is not None else None
    except (TypeError, ValueError):
        end_s = None
    if end_s is not None and (not math.isfinite(end_s) or end_s <= start_s):
        end_s = None
    confidence = _mark_confidence(mark)
    return CuePoint(
        name=str(mark.get("name") or ""),
        type=str(mark.get("type") or "cue"),
        start_s=start_s,
        end_s=end_s,
        number=slot if slot is not None else -1,
        source=str(mark.get("source") or "auto").strip().lower(),
        confidence=confidence,
    )


def _mark_confidence(mark: dict[str, Any]) -> float | None:
    raw = mark.get("confidence")
    if raw is None:
        return None
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(value):
        return None
    return min(1.0, max(0.0, value))


def _occupied_hotcue_slots(cues: Any) -> set[int]:
    return {slot for cue in cues or () if (slot := _mark_hotcue_slot(cue)) is not None}


def _mark_hotcue_slot(mark: Any) -> int | None:
    raw = mark.get("num") if isinstance(mark, dict) else getattr(mark, "num", None)
    try:
        slot = int(raw)
    except (TypeError, ValueError):
        return None
    return slot if 0 <= slot <= 7 else None


def _transition_candidate_to_dict(candidate: TransitionCandidate) -> dict[str, Any]:
    from vibemix.intel.move_grade import grade_transition_candidate

    data = asdict(candidate)
    data["move_grade"] = grade_transition_candidate(candidate)
    return data


def _smart_cue_proposal_to_dict(proposal: SmartCueProposal) -> dict[str, Any]:
    return asdict(proposal)


def _mode_arg(raw: Any) -> Literal["prep", "live"]:
    return "live" if raw == "live" else "prep"


def _int_arg(raw: Any, *, default: int) -> int:
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def _optional_int_arg(raw: Any) -> int | None:
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _float_arg(raw: Any, *, default: float) -> float:
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


_COPY_SUFFIX_RE = re.compile(r"\s+\((?:copy\s*)?\d+\)\s*$", re.IGNORECASE)
_SPACE_RE = re.compile(r"\s+")


def _dedupe_sequence_pool(pool: list[Any]) -> tuple[list[Any], list[str]]:
    """Drop obvious duplicate file copies before set sequencing.

    The key is intentionally conservative: normalized title (with only trailing
    numeric copy suffixes removed), normalized artist, and rounded duration.
    Same title but different duration stays available, so radio/extended edits
    are not collapsed.
    """
    seen: set[tuple[str, str, int]] = set()
    out: list[Any] = []
    dropped: list[str] = []
    for item in pool:
        key = _sequence_duplicate_key(item)
        if key is None:
            out.append(item)
            continue
        if key in seen:
            dropped.append(str(getattr(item, "track_id", "")))
            continue
        seen.add(key)
        out.append(item)
    return out, dropped


def _sequence_duplicate_key(item: Any) -> tuple[str, str, int] | None:
    duration = _float_arg(getattr(item, "duration_s", None), default=0.0)
    if duration <= 0:
        return None
    title = _normalize_duplicate_text(getattr(item, "title", ""))
    if not title:
        return None
    artist = _normalize_duplicate_text(getattr(item, "artist", ""))
    return (title, artist, round(duration))


def _normalize_duplicate_text(raw: Any) -> str:
    text = str(raw or "").strip().casefold()
    text = _COPY_SUFFIX_RE.sub("", text)
    return _SPACE_RE.sub(" ", text).strip()


def _bounded_float_arg(raw: Any, *, minimum: float, maximum: float, default: float) -> float:
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(value):
        return default
    return max(minimum, min(maximum, value))


def _unit_float_or_none(raw: Any) -> float | None:
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(value):
        return None
    return max(0.0, min(1.0, value))


__all__ = [
    "BATCH_TOOL_CALL_TIMEOUT_S",
    "INSPECT_CANDIDATES_WORKERS",
    "MAX_CHOICES",
    "MAX_INSPECT_CANDIDATES",
    "MIN_CHOICES",
    "TOOL_CALL_TIMEOUT_S",
    "TOOL_STARVATION_THRESHOLD",
    "LibraryToolset",
]
