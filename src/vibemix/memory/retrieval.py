# SPDX-License-Identifier: Apache-2.0
"""Phase 65 Plan 65-03 (Wave 1) — MemoryRecall enrichment service.

The off-hot-path, event-gated, similarity-floored, current-session-excluded
retrieval seam. An architectural clone of ``library/grounding.py::Grounding``
(lock-guarded ``_latest``, ``on_event``/``get_latest``/``clear``), pointed at
``MemoryStore`` instead of the library: it turns a track-aware live event into
a short list of past-session ``Record`` moments for the coach prompt to fence
(the PAST-tense fence + the ``recall[…]`` block land in Plan 65-04, not here).

Invariants (the milestone's anti-poisoning + off-path core):

    * No-live-path: imports NO live-reaction-path surface (no coach loop, no
      ``MusicState``, no ``ws_bus``, no agent, no prompts). It reads
      ``MemoryStore.query_topk`` + an injected product embedder's
      ``embed_query`` only, writes only its own ``_latest``, opens no socket,
      never writes ``MusicState``.
      Lives in ``memory/`` so the shipped no-live-path / no-extraction static
      gates auto-cover this file.
    * No-extraction: the ONLY model call is ``embedder.embed_query(query_text)``
      — never a generation surface (raw-in/raw-out).
    * Anti-poisoning trio (RECALL-03): below the cosine floor → dropped → ``[]``;
      the current session is excluded from its own retrieval via
      ``query_topk(..., exclude_session=current_session_id)``.
    * Budget / off-path (RECALL-04): event-gated to track-aware events (NEVER
      HEARTBEAT — the highest-frequency class), exactly one local CLAP query
      embed per gated event, cosine-only (NO time-decay blend — that is a
      KAAN-ACTION deferral, not v1), conservative top-K. MIX_MOVE is eligible
      only when the caller has move + global or per-deck sound-change evidence,
      so knob/fader history can be recalled without embedding every controller
      twitch. The hard deadline (``RECALL_DEADLINE_S``) is enforced AGENT-side
      (Plan 65-04) via ``asyncio.wait_for``; defined here as the shared default.
"""

from __future__ import annotations

import logging
import re
import threading
from typing import Protocol

from vibemix.memory.store import MemoryStore, Record
from vibemix.state.deck_context import normalize_audio_window_context_text

logger = logging.getLogger(__name__)


class _RecallEmbedder(Protocol):  # pragma: no cover - structural typing only
    def embed_query(self, query: str): ...


# ---------------------------------------------------------------------------
# Retrieval policy defaults (research §Retrieval Policy Defaults). Conservative
# cosine-only v1; the cosine-vs-time blend / half-life / exact floor are
# DEFERRED to the Kaan-ear pass (KAAN-ACTION).
# ---------------------------------------------------------------------------

# COPY of library/grounding.py:39 CITATION_THRESHOLD. Mirrored (not imported) to
# avoid a memory→library coupling — the value is intentionally duplicated.
RECALL_SIMILARITY_FLOOR = 0.7  # mirrors library/grounding.py:39 CITATION_THRESHOLD

# Conservative top-K: cap the past-moment pull at a small handful.
RECALL_TOP_K = 3

# The shared off-loop budget. The agent (Plan 65-04) enforces this via
# asyncio.wait_for; defined here as the single source of the default.
RECALL_DEADLINE_S = 0.5

# Event gate — track-aware events ONLY. HEARTBEAT / KAAN_SPOKE / MANUAL stay
# out. MIX_MOVE is admitted only behind ``should_recall_event(ev)``'s
# move+audio-delta evidence gate at the agent dispatch seam; the service-level
# ``on_event`` still gates only by event_type because it intentionally receives
# no live state object.
RECALL_EVENT_GATE: frozenset[str] = frozenset(
    {"TRACK_CHANGE", "PHASE", "LAYER_ARRIVAL", "MIX_MOVE"}
)
_UNTRUSTED_AUDIO_WINDOW = "omitted_untrusted_audio_window"
_AUDIO_WINDOW_DECK_A_RE = re.compile(r"\bdeckA_audio=(P[2-9][0-9]?)\b")
_AUDIO_WINDOW_DECK_B_RE = re.compile(r"\bdeckB_audio=(P[2-9][0-9]?)\b")
_AUDIO_WINDOW_FORBIDDEN_ATOMS = (
    "deckA_audio=attached",
    "deckB_audio=attached",
    "deckA_audio=stem",
    "deckB_audio=stem",
    "per_deck_audio=attached",
    "isolated_decks=true",
)


def build_recall_query(ev) -> str:
    """Build the query string for ``ev``, mirroring the stored signature prefix.

    Reuses the Phase-64 ``coach_line`` signature template head
    (``vibemix/memory/ingest.py::build_coach_line_signature`` :138-141) so the
    live query embedding and the stored coach-line embeddings share a vector
    space (query↔stored symmetry). At retrieval time there is no spoken line
    yet, so this emits the CONTEXT PREFIX only — ``track``/``phase``/``deck``/
    ``event`` — and OMITS the ``cite=`` and ``said:`` tail.

    Reads ``ev.state`` + ``ev.type`` by attribute (duck-typed) so this module
    never imports ``MusicState`` (no-live-path invariant). Missing fields fall
    back to the same ``unknown``/``none``/``MANUAL`` defaults the ingest builder
    uses, keeping the prefix byte-symmetric.

    Phase 65 review WR-02 — when the state object exposes a ``_lock``
    attribute (the canonical MusicState lock used by state_refresh_loop's
    single-writer rule), the three field reads are snapshotted UNDER that
    lock so they cannot mix values from two refresh ticks. Duck-typed: if
    ``_lock`` is absent (test stubs, simple SimpleNamespace fixtures), fall
    through to unlocked attribute reads — the no-live-path invariant is
    preserved (we still do not import MusicState).
    """
    state = getattr(ev, "state", None)
    if state is None:
        etype = getattr(ev, "type", None) or "MANUAL"
        return f"coach_line | track=unknown | phase=unknown | deck=none | event={etype}"
    lock = getattr(state, "_lock", None)
    if lock is not None:
        # Snapshot the three needed fields under the state lock so they
        # cannot mix values from two refresh-loop ticks — mirrors the
        # state_refresh_loop single-writer / locked-read contract.
        with lock:
            track = getattr(state, "audible_track", None) or "unknown"
            phase = getattr(state, "phase", None) or "unknown"
            deck = getattr(state, "audible_deck", None) or "none"
    else:
        track = getattr(state, "audible_track", None) or "unknown"
        phase = getattr(state, "phase", None) or "unknown"
        deck = getattr(state, "audible_deck", None) or "none"
    etype = getattr(ev, "type", None) or "MANUAL"
    # Prefix only — omit cite=/said: (no spoken line at retrieval time).
    base = f"coach_line | track={track} | phase={phase} | deck={deck} | event={etype}"

    # Optional caller-supplied context mirrors the ingest signature fields. The
    # memory layer intentionally does not import live deck helpers; the agent
    # can pass these strings through ``ev.extra`` when it already has them.
    extra = getattr(ev, "extra", None)
    if not isinstance(extra, dict):
        return base
    pieces: list[str] = []
    for field, key in (
        ("context_feed", "context_feed_contract"),
        ("deck_lane", "deck_lane_context"),
        ("deck_ref", "deck_reference_context"),
        ("deck_source", "deck_source_context"),
        ("deck_audio", "deck_audio_context"),
        ("deck_audio_separation", "deck_audio_separation_context"),
        ("deck_audio_features", "deck_audio_features_context"),
        ("deck_audio_delta", "deck_audio_delta_context"),
        ("deck_audio_window", "deck_audio_window_context"),
        ("audio_window", "audio_window_context"),
        ("live_evidence", "live_evidence_context"),
        ("move", "move_context"),
        ("move_effect", "move_effect_context"),
        ("audio_delta", "audio_delta"),
    ):
        if field == "context_feed":
            cap = 420
        elif field == "live_evidence":
            cap = 640
        else:
            cap = 240
        if key == "audio_window_context":
            rendered = _query_audio_window_field(extra.get(key), cap=cap)
        else:
            rendered = _query_field(extra.get(key), cap=cap)
        if rendered != "none":
            pieces.append(f"{field}={rendered}")
    if not pieces:
        return base
    return base + " | " + " | ".join(pieces)


def should_recall_event(ev) -> bool:
    """Return whether an event is worth a memory recall query.

    This is the cheap caller-side cost gate. Track/phase/layer events are
    already sparse enough. MIX_MOVE can be noisy, so it only passes when the
    event carries a concrete controller move and the state/extra payload carries
    global or per-deck audio delta evidence. That is the grounded
    "knob/fader -> sound changed" condition the historical memory is meant to
    learn.
    """
    etype = getattr(ev, "type", None)
    if etype not in RECALL_EVENT_GATE:
        return False
    if etype != "MIX_MOVE":
        return True

    extra = getattr(ev, "extra", None)
    moves = extra.get("moves") if isinstance(extra, dict) else None
    if not isinstance(moves, (list, tuple)) or not any(str(item).strip() for item in moves):
        return False

    return _has_sound_change_evidence(ev)


def _has_sound_change_evidence(ev) -> bool:
    extra = getattr(ev, "extra", None)
    if isinstance(extra, dict):
        if _has_evidence_value(extra.get("audio_delta")):
            return True
        if _has_evidence_value(extra.get("deck_audio_delta_context")):
            return True
        if _has_evidence_value(extra.get("deck_audio_window_context")):
            return True
        capture = extra.get("audio_capture_context")
        if isinstance(capture, dict) and (
            _has_evidence_value(capture.get("deck_audio_deltas"))
            or _has_evidence_value(capture.get("deck_audio_delta_context"))
            or _has_evidence_value(capture.get("deck_audio_windows"))
            or _has_evidence_value(capture.get("deck_audio_window_context"))
        ):
            return True
    return _has_evidence_value(getattr(getattr(ev, "state", None), "audio_delta", None))


def _has_evidence_value(value: object) -> bool:
    if value is None or isinstance(value, bool):
        return False
    if isinstance(value, dict):
        return any(_has_evidence_value(item) for item in value.values())
    if isinstance(value, (list, tuple, set, frozenset)):
        return any(_has_evidence_value(item) for item in value)
    text = str(value).strip()
    return bool(text) and text.lower() not in {"none", "null", "[]", "{}"}


def _query_field(value: object, *, cap: int = 240) -> str:
    if isinstance(value, (list, tuple)):
        raw = "; ".join(str(item) for item in value[:4] if item)
    else:
        raw = str(value) if value else ""
    raw = " ".join(raw.split()).replace("|", "/")
    return raw[:cap] if raw else "none"


def _query_audio_window_field(value: object, *, cap: int = 240) -> str:
    rendered = _query_field(value, cap=900)
    if rendered == "none":
        return "none"
    trusted = normalize_audio_window_context_text(rendered, max_len=900)
    if trusted:
        return _query_field(trusted, cap=cap)
    if _audio_window_context_is_untrusted(rendered):
        return _UNTRUSTED_AUDIO_WINDOW
    return _query_field(rendered, cap=cap)


def _audio_window_context_is_untrusted(text: str) -> bool:
    if "audio_window_context[" not in text:
        return False
    if any(atom in text for atom in _AUDIO_WINDOW_FORBIDDEN_ATOMS):
        return True
    deck_a = _AUDIO_WINDOW_DECK_A_RE.search(text)
    deck_b = _AUDIO_WINDOW_DECK_B_RE.search(text)
    if deck_a or deck_b:
        return not (deck_a and deck_b) or deck_a.group(1) == deck_b.group(1)
    return "per_deck_audio=deck_pair_parts" in text


class MemoryRecall:
    """Stateful recall service the agent holds — a ``Grounding`` clone.

    Holds the most recent survivor list so the agent's prompt builder can pull
    ``get_latest()`` when constructing the next coach turn. Thread-safe
    (lock-guarded): the agent fires ``on_event`` from a different thread than
    the one that reads ``get_latest`` / calls ``clear``.
    """

    def __init__(self, embedder: _RecallEmbedder, store: MemoryStore) -> None:
        self._embedder = embedder
        self._store = store
        self._lock = threading.Lock()
        self._latest: list[Record] = []
        # Phase 65 review CR-04 — per-dispatch generation token. Incremented
        # at the start of every ``on_event`` AND every ``clear``; captured by
        # the executor thread at dispatch time, and re-checked before the
        # final ``_latest = survivors`` write. If ``clear()`` ran between
        # dispatch and write (deadline missed in the asyncio wrapper while
        # the executor was mid-``query_topk``), the stale survivors are
        # DISCARDED instead of latched — closes the "TimeoutError clears
        # then the slow executor re-populates" race. Guarded by ``_lock``.
        self._inflight_gen: int = 0

    def on_event(
        self,
        event_type: str,
        query_text: str,
        current_session_id: str,
    ) -> list[Record]:
        """Run recall for an emitted event. Returns + latches the survivors.

        Gate first (no embed on a non-track-aware event), then a single local
        CLAP query embed, then ``query_topk`` over the pre-embedded corpus with
        the current session excluded, then the cosine-floor filter. Survivors
        are latched under the lock for ``get_latest`` and returned.

        Phase 65 review CR-04 — a per-dispatch generation token is captured
        BEFORE the (potentially slow) embed + ranking and re-checked before
        the final latch write. If ``clear()`` was called in between (the
        asyncio deadline wrapper fired ``TimeoutError`` mid-``query_topk``),
        the token check fails and ``_latest`` is NOT mutated — the stale
        result is silently dropped instead of overwriting the cleared latch.
        The list is still returned to the caller (callers that aren't gated
        by the deadline wrapper, such as the synchronous unit-test path,
        still see the result).
        """
        # Event gate — short-circuit BEFORE any embed (no model call on a
        # HEARTBEAT / non-track-aware event).
        if event_type not in RECALL_EVENT_GATE:
            return []

        # Capture the generation BEFORE the slow work — held across the embed
        # + query window. A concurrent ``clear()`` will bump ``_inflight_gen``
        # while we're outside the lock, which the final check below detects.
        with self._lock:
            self._inflight_gen += 1
            my_gen = self._inflight_gen

        # Exactly one local query embed (no per-candidate re-embed, no retry).
        qvec = self._embedder.embed_query(query_text)

        # Current session excluded BEFORE ranking (the live session can't
        # "remember itself"). Stale pre-CLAP memory vectors or backend damage
        # must never perturb a live turn; fail empty and clear the latch for
        # this dispatch.
        try:
            hits = self._store.query_topk(qvec, RECALL_TOP_K, exclude_session=current_session_id)
        except Exception as exc:
            logger.warning("memory recall query failed: %s", exc)
            with self._lock:
                if my_gen == self._inflight_gen:
                    self._latest = []
            return []

        # Cosine floor — a weak callback is no callback (cosine-only, no decay).
        survivors = [r for r in hits if r.score >= RECALL_SIMILARITY_FLOOR]

        with self._lock:
            # Token check — if the agent's deadline wrapper fired ``clear()``
            # between dispatch and now, ``_inflight_gen`` has been bumped and
            # this result is stale. Drop it without touching ``_latest`` so
            # the deadline-miss "no recall this turn" contract holds.
            if my_gen != self._inflight_gen:
                return list(survivors)
            self._latest = survivors
        return list(survivors)

    def get_latest(self) -> list[Record]:
        """Snapshot the most recent survivor list (a copy, lock-guarded)."""
        with self._lock:
            return list(self._latest)

    def clear(self, bump_generation: bool = True) -> None:
        """Reset the latched survivors to ``[]``.

        Called per-turn (and on a deadline miss, Plan 65-04) so a stale recall
        cannot bleed into a later turn / a next HEARTBEAT replays nothing.

        Phase 65 review CR-04 — by default bumps ``_inflight_gen`` so any
        in-flight ``on_event`` whose executor thread is still mid-
        ``query_topk`` will fail its token check at write-time and discard
        its (now-stale) survivors instead of overwriting the cleared latch.
        This is the deadline-miss path's contract: the dispatch we are
        cancelling IS the one whose write we must invalidate.

        Phase 65 review iter-3 WR-03 — callers that want to clear the
        latched value WITHOUT invalidating a concurrent in-flight dispatch
        (the reactive ``get_latest()``-exception path in
        ``DJCoHostAgent.llm_node``) pass ``bump_generation=False``. In that
        path the in-flight dispatch is unrelated to the failed read (it is
        building survivors for a FUTURE turn) and bumping the generation
        would silently torpedo its healthy write. The cold/feature-off path
        and the CR-04 race-discard test both keep the default
        ``bump_generation=True`` and remain BYTE-IDENTICAL in semantics.
        """
        with self._lock:
            if bump_generation:
                self._inflight_gen += 1
            self._latest = []


__all__ = [
    "RECALL_DEADLINE_S",
    "RECALL_EVENT_GATE",
    "RECALL_SIMILARITY_FLOOR",
    "RECALL_TOP_K",
    "MemoryRecall",
    "build_recall_query",
    "should_recall_event",
]
