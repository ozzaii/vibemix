# SPDX-License-Identifier: Apache-2.0
"""Phase 28 Plan 04 — "what's playing" grounding pipeline.

The anti-hallucination centerpiece of vibemix. When a track-aware event
fires (TRACK_CHANGE, LAYER_ARRIVAL, MIX_MOVE, KAAN_SPOKE), the agent
calls ``identify_playing(audio_bytes)`` to embed the recent audio buffer
and run cosine top-1 against the library. If similarity >= 0.7, the
returned ``Citation`` carries the track id — the agent injects it as
``[track:<id>]`` in the next Gemini prompt as text reference + audio
anchor (per memory ``feedback_mic_audio_as_multimodal_part``).

Cost contract (Pitfall P56): grounding is **event-gated** (Option B from
RESEARCH Open Q1). Embed calls fire only on event emission, not every
30 seconds. At 1000 DAU this lands at ~€27/month vs the continuous
3-excerpts/min path at ~€1500/month.

Decision thresholds (Open Q3):
    cosine >= 0.7  → cited        (inject [track:<id>])
    cosine >= 0.6  → uncertain    (no citation; emit telemetry)
    cosine <  0.6  → below_threshold (no citation; emit telemetry)
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from dataclasses import dataclass

from vibemix.library._cosine import EMBEDDING_DIM
from vibemix.library.embed_types import AudioBytesEmbedder
from vibemix.library.store import LibraryStore

logger = logging.getLogger(__name__)

# Decision thresholds. Locked.
CITATION_THRESHOLD = 0.7
UNCERTAIN_THRESHOLD = 0.6

# Event types that trigger a grounding lookup. Only these — others are
# either non-musical (KAAN_SPOKE on its own without music context) or
# redundant (HEARTBEAT). Locked per RESEARCH Open Q1 + cost gate (P56).
TRACK_AWARE_EVENTS: frozenset[str] = frozenset(
    {"TRACK_CHANGE", "LAYER_ARRIVAL", "MIX_MOVE"}
)


@dataclass(frozen=True, slots=True)
class Citation:
    """A grounding decision for a single event.

    Fields:
        event_id: stable id for IPC correlation.
        decision: ``"cited" | "uncertain" | "below_threshold"``.
        track_id: cited track id, or ``None`` when below threshold.
        cosine: top-1 cosine similarity in [-1, 1].
        ts: epoch-seconds when the lookup was made.
    """

    event_id: str
    decision: str
    track_id: str | None
    cosine: float
    ts: float

    @property
    def is_cited(self) -> bool:
        return self.decision == "cited"


def _decide(cosine: float) -> str:
    if cosine >= CITATION_THRESHOLD:
        return "cited"
    if cosine >= UNCERTAIN_THRESHOLD:
        return "uncertain"
    return "below_threshold"


def identify_playing(
    embedder: AudioBytesEmbedder,
    store: LibraryStore,
    audio_bytes: bytes | None,
    *,
    event_type: str = "MANUAL",
    event_id: str | None = None,
    mime_type: str = "audio/wav",
) -> Citation | None:
    """Embed the recent audio buffer + cosine top-1 against the library.

    Returns:
        Citation when an event-gated lookup ran (always — even when
        below threshold, the Citation is returned so callers can emit
        telemetry).
        None when ``event_type`` is not in TRACK_AWARE_EVENTS (skip path
        — the cost-gate guard).

    The ``audio_bytes`` arg may be ``None`` when no audio is available —
    in that case we skip embed + return ``Citation(decision="below_threshold")``.
    """
    if event_type not in TRACK_AWARE_EVENTS and event_type != "MANUAL":
        return None

    eid = event_id or f"ev-{uuid.uuid4().hex[:12]}"

    if not audio_bytes:
        return Citation(
            event_id=eid,
            decision="below_threshold",
            track_id=None,
            cosine=0.0,
            ts=time.time(),
        )

    try:
        # Phase 90: route through the embedder's public ``embed_audio_bytes``
        # surface. The product ``ClapEmbedder`` runs the local CLAP audio
        # encoder; the legacy Gemini embedder still satisfies the same method
        # in migration tests. NO more reaching into ``embedder._client``.
        qvec = embedder.embed_audio_bytes(audio_bytes, mime_type)
        assert qvec.shape == (EMBEDDING_DIM,), (
            f"grounding: embed returned {qvec.shape}, expected ({EMBEDDING_DIM},)"
        )
    except Exception as e:
        logger.warning("grounding embed failed: %s", e)
        return Citation(
            event_id=eid,
            decision="below_threshold",
            track_id=None,
            cosine=0.0,
            ts=time.time(),
        )

    topk = store.search(qvec, k=1)
    if not topk:
        return Citation(
            event_id=eid,
            decision="below_threshold",
            track_id=None,
            cosine=0.0,
            ts=time.time(),
        )
    tid, sim = topk[0]
    decision = _decide(float(sim))
    return Citation(
        event_id=eid,
        decision=decision,
        track_id=tid if decision == "cited" else None,
        cosine=float(sim),
        ts=time.time(),
    )


class Grounding:
    """Stateful grounding service the agent holds.

    Holds the most recent Citation so the agent's prompt builder can pull
    ``get_latest_citation()`` when constructing the next Gemini turn.
    Thread-safe (lock-guarded) — the audio loop fires citations from a
    different thread than the agent's coach loop.
    """

    def __init__(
        self,
        embedder: AudioBytesEmbedder,
        store: LibraryStore,
    ) -> None:
        self._embedder = embedder
        self._store = store
        self._lock = threading.Lock()
        self._latest: Citation | None = None
        # Phase 77 review CR-01 — per-dispatch generation token, mirroring
        # ``MemoryRecall._inflight_gen`` (Phase 65 review CR-04). Incremented
        # at the start of every ``on_event`` AND every ``clear``; captured by
        # the executor thread at dispatch time, and re-checked before the
        # final ``_latest = citation`` write. The WIRE-01 dispatch wraps
        # ``on_event`` in ``asyncio.wait_for(timeout=_DEADLINE_S)`` and calls
        # ``clear()`` on timeout — but ``wait_for`` timing out does NOT stop
        # the executor thread, so ``identify_playing`` keeps running and would
        # otherwise latch a stale citation AFTER ``clear()`` ran, resurrecting
        # a prior track's ``[track:<id>]`` for the wrong track (invariant #3
        # — "trust the audio"). The token check below detects the intervening
        # ``clear()`` and DISCARDS the late write. Guarded by ``_lock``.
        self._inflight_gen: int = 0

    def on_event(
        self,
        event_type: str,
        audio_bytes: bytes | None,
        *,
        event_id: str | None = None,
        mime_type: str = "audio/wav",
    ) -> Citation | None:
        """Run grounding for an emitted event. Stores the result for
        ``get_latest_citation()``. Returns None when event is not track-aware.

        Phase 77 review CR-01 — a per-dispatch generation token is captured
        BEFORE the (potentially slow) embed + library cosine and re-checked
        before the final latch write. If ``clear()`` was called in between
        (the asyncio deadline wrapper fired ``TimeoutError`` mid-embed), the
        token check fails and ``_latest`` is NOT mutated — the stale citation
        is silently dropped instead of resurrecting a wrong ``[track:<id>]``.
        The Citation is still returned to the caller so the synchronous unit
        path (and telemetry) still observe the result.
        """
        # Capture the generation BEFORE the slow work — held across the embed
        # + cosine window. A concurrent ``clear()`` bumps ``_inflight_gen``
        # while we're outside the lock, which the final check below detects.
        with self._lock:
            self._inflight_gen += 1
            my_gen = self._inflight_gen

        citation = identify_playing(
            self._embedder,
            self._store,
            audio_bytes,
            event_type=event_type,
            event_id=event_id,
            mime_type=mime_type,
        )
        if citation is not None and citation.is_cited:
            with self._lock:
                # Token check — if the agent's deadline wrapper fired
                # ``clear()`` between dispatch and now, ``_inflight_gen`` has
                # been bumped and this citation is stale. Drop it without
                # touching ``_latest`` so the deadline-miss "no citation this
                # turn" contract holds (matches the recall race-discard).
                if my_gen == self._inflight_gen:
                    self._latest = citation
        return citation

    def get_latest_citation(self) -> Citation | None:
        """Snapshot the most recent CITED Citation (or None if no recent cite)."""
        with self._lock:
            return self._latest

    def clear(self) -> None:
        """Drop the latest citation — called at end of each Gemini turn so
        a single citation isn't replayed across multiple prompts.

        Phase 77 review CR-01 — bumps ``_inflight_gen`` so any in-flight
        ``on_event`` whose executor thread is still mid-embed will fail its
        token check at write-time and discard its (now-stale) citation
        instead of overwriting the cleared latch. This is the deadline-miss
        path's contract: the dispatch we are cancelling IS the one whose
        write we must invalidate (mirrors ``MemoryRecall.clear``)."""
        with self._lock:
            self._inflight_gen += 1
            self._latest = None


__all__ = [
    "CITATION_THRESHOLD",
    "TRACK_AWARE_EVENTS",
    "UNCERTAIN_THRESHOLD",
    "Citation",
    "Grounding",
    "identify_playing",
]
