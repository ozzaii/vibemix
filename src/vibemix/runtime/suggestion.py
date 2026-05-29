# SPDX-License-Identifier: Apache-2.0
"""SuggestionService — owns the pill "what's next" state, off the hot path.

Holds the session-scoped ``played_ids`` set and the latest computed suggestion
("the holder"), and recomputes it from the now-playing seed. It is deliberately
SEPARATE from ``MusicState`` (single-writer invariant: the state-refresh loop is
the only writer of ``MusicState`` — the suggestion is derived UI state, not
authoritative music state) and from the coach reaction loop (the compute runs
in an executor so it never blocks reactions).

Data flow:

    coach_loop sees a TRACK_CHANGE  →  service.maybe_schedule_compute_from_state(state)
        (executor scheduled once per seed — store read is sync)│
                                                             ▼
    seed = deck_state.decks[audible_side] (track_id + camelot + bpm)
        → stored seed vector (cached, ~free) → next_suggestion(...)
        → service.current() holds the dict
        → service.current_for_state(state) can reselect inside shortlist + refresh cue/timing
                                                             │
    ws_broadcast reads service.current_for_state() at the serialize edge
        → merges it onto the flat mascot frame as ``next_suggestion``
        → pill renders it.

Grounding: the engine (``next_suggestion``) only surfaces ids present in BOTH
the store and the live library, and returns ``None`` when nothing qualifies —
``current()`` then carries ``None`` (honest silence; the pill shows no
suggestion rather than a fabricated one).
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from vibemix.intel.feedback import FeedbackEvent, parse_feedback_event
from vibemix.library.next_suggestion import (
    annotate_transition_selection,
    next_suggestion,
    prepared_target_candidate_payload,
    promote_transition_alternative,
    ranked_transition_alternatives,
    seed_vector_for_track_id,
    transition_payload_for_candidate,
    vectors_for_track_ids,
)
from vibemix.library.prepared_pool import PreparedPool, next_track_id_after

logger = logging.getLogger(__name__)

BAR_LOCK_CONFIDENCE_FLOOR = 0.80
BAR_BOUNDARY_TOLERANCE = 0.10
LIVE_REFRESH_INTERVAL_S = 0.75
FULL_COMPUTE_RETRY_S = 5.0
FULL_COMPUTE_DISPATCH_GUARD_S = 0.25
CONTROLLER_TARGET_VOLUME_FLOOR = 16
CONTROLLER_XFADER_FACTOR_FLOOR = 0.20
TARGET_DECK_TRACK_CONFIDENCE_FLOOR = 0.50
SOURCE_LOOP_RECENCY_S = 8.0
GRADE_XP_LEVEL_STEP = 250
EXPLICIT_FEEDBACK_ACTIONS: dict[str, tuple[str, str]] = {
    "accept": ("suggestion_accepted", "accepted"),
    "keep": ("suggestion_accepted", "accepted"),
    "later": ("suggestion_rejected", "not_now"),
    "not_now": ("suggestion_rejected", "not_now"),
    "timing": ("timing_claim_wrong", "wrong_timing"),
    "wrong_timing": ("timing_claim_wrong", "wrong_timing"),
}


@dataclass(frozen=True, slots=True)
class LiveTimingHint:
    """Conservative live timing hint derived from the state bar lock."""

    remaining_bars: int | None
    playhead_confidence: float
    blend_active: bool = False
    source_position_s: float | None = None
    source_loop_recent: bool = False


@dataclass(frozen=True, slots=True)
class ResolvedSeed:
    """Grounded now-playing seed plus deck context for the next move."""

    track_id: str
    camelot: str | None
    bpm: float | None
    source_deck: str | None = None
    target_deck: str | None = None
    target_track_id: str | None = None


@dataclass(frozen=True, slots=True)
class PreparedTarget:
    """A bounded target hint for the next-suggestion engine."""

    track_id: str
    reason_prefix: str
    source: str
    strict: bool


def resolve_seed_context(state: Any) -> ResolvedSeed | None:
    """Resolve the now-playing seed (track_id, camelot, bpm) from MusicState.

    Reads the AUDIBLE deck's ``DeckTrack`` (``deck_state.decks[side]``). Returns
    ``None`` when there is no resolved ``track_id`` (folder-only library with no
    title match, no Rekordbox import, or nothing audible) — the caller then
    leaves the current suggestion untouched. PURE READ.
    """
    deck_state = getattr(state, "deck_state", None)
    decks = getattr(deck_state, "decks", None) or {}
    if not decks:
        return None

    side = getattr(state, "audible_deck", None)
    source_deck = side if isinstance(side, str) and side in decks else None
    dt = decks.get(source_deck) if source_deck is not None else None
    if dt is None:
        # "mix" / "none" / unknown side → pick the highest-confidence deck.
        source_deck, dt = max(
            decks.items(),
            key=lambda item: getattr(item[1], "confidence", 0.0),
        )

    track_id = getattr(dt, "track_id", None)
    if not track_id:
        return None
    camelot = getattr(dt, "camelot", None)
    bpm = getattr(dt, "bpm", None)
    bpm = bpm if (bpm and bpm > 0.0) else None
    target_deck = _target_deck(source_deck, side)
    return ResolvedSeed(
        track_id=track_id,
        camelot=camelot,
        bpm=bpm,
        source_deck=source_deck,
        target_deck=target_deck,
        target_track_id=_prepared_target_track_id(
            decks,
            target_deck=target_deck,
            source_track_id=track_id,
        ),
    )


def resolve_seed(state: Any) -> tuple[str, str | None, float | None] | None:
    """Backward-compatible seed tuple for older callers/tests."""
    seed = resolve_seed_context(state)
    if seed is None:
        return None
    return seed.track_id, seed.camelot, seed.bpm


def resolve_live_timing(state: Any) -> LiveTimingHint:
    """Resolve a bar-level timing hint from MusicState.

    This is intentionally narrower than a track playhead. A confident
    ``beat_phase`` lock can support "now / next bar" cue timing, but if the lock
    is weak or malformed we withhold exact bars and let the scorer expose only
    the destination cue.
    """
    blend_active = bool(
        getattr(state, "audible_deck", None) == "mix"
        or resolve_controller_mix_context(state).get("controller_blend_active")
    )
    source_deck = _deck_label(getattr(state, "audible_deck", None))
    source_loop_recent = _source_loop_recent(state, source_deck=source_deck)
    source_position_s = _float_or(getattr(state, "audible_track_position_s", None), None)
    position_confidence = _clamp01(
        _float_or(getattr(state, "audible_track_position_confidence", 0.0), 0.0) or 0.0
    )
    if source_position_s is not None and position_confidence >= 0.5:
        return LiveTimingHint(
            None,
            position_confidence,
            blend_active,
            source_position_s,
            source_loop_recent,
        )

    confidence = _float_or(getattr(state, "bpm_confidence", 0.0), 0.0)
    confidence = _clamp01(confidence)
    if confidence < BAR_LOCK_CONFIDENCE_FLOOR:
        return LiveTimingHint(None, confidence, blend_active, None, source_loop_recent)

    phase = _float_or(getattr(state, "beat_phase", None), None)
    if phase is None:
        phase = _float_or(getattr(state, "downbeat_phase", 0.0), None)
    if phase is None or not 0.0 <= phase < 1.0:
        return LiveTimingHint(None, 0.0, blend_active, None, source_loop_recent)

    distance_to_bar_boundary = min(phase, 1.0 - phase)
    remaining_bars = 0 if distance_to_bar_boundary <= BAR_BOUNDARY_TOLERANCE else 1
    return LiveTimingHint(remaining_bars, confidence, blend_active, None, source_loop_recent)


def resolve_controller_mix_context(
    state: Any,
    *,
    source_deck: str | None = None,
    target_deck: str | None = None,
) -> dict[str, Any]:
    """Return a prompt-safe summary of controller mix posture."""
    source = _deck_label(source_deck) or _deck_label(getattr(state, "audible_deck", None))
    target = _deck_label(target_deck) or ("B" if source == "A" else "A" if source == "B" else None)
    xfader = _int_0_127(getattr(state, "xfader", 64), 64)
    connected = bool(getattr(state, "controller_connected", False))
    source_state = _deck_controller_state(state, source)
    target_state = _deck_controller_state(state, target)
    target_channel_open = bool(
        target
        and target_state.get("volume_raw", 0) >= CONTROLLER_TARGET_VOLUME_FLOOR
        and _xfader_factor(target, xfader) >= CONTROLLER_XFADER_FACTOR_FLOOR
    )
    controller_blend_active = bool(connected and source in {"A", "B"} and target_channel_open)
    return {
        "connected": connected,
        "xfader": xfader,
        "source": source_state,
        "target": target_state,
        "target_channel_open": target_channel_open,
        "controller_blend_active": controller_blend_active,
    }


class SuggestionService:
    """Thread-safe holder + recompute for the pill next-suggestion."""

    def __init__(
        self,
        store: Any,
        library: Any,
        *,
        k: int = 5,
        feedback_sink: Callable[[FeedbackEvent], None] | None = None,
        session_id: str | None = None,
        taste_scores: dict[tuple[str, str], float] | None = None,
        prepared_pool_loader: Callable[[], PreparedPool | None] | None = None,
    ) -> None:
        self._store = store
        self._library = library
        self._k = k
        self._feedback_sink = feedback_sink
        self._feedback_session_id = _feedback_token(session_id or "live_session")
        self._taste_scores = dict(taste_scores or {})
        self._prepared_pool_loader = prepared_pool_loader
        self._lock = threading.Lock()
        self._played: set[str] = set()
        self._current: dict | None = None
        self._seed_track_id: str | None = None
        self._seed_vector: Any | None = None
        self._candidate_track_id: str | None = None
        self._candidate_vector: Any | None = None
        self._candidate_vectors_by_track_id: dict[str, Any] = {}
        self._prepared_target_track_id: str | None = None
        self._pinned_candidate_track_id: str | None = None
        self._timing_suppressed_pairs: set[tuple[str, str]] = set()
        self._grade_progress: dict[str, Any] = _empty_grade_progress()
        self._last_refresh_at = 0.0
        self._last_compute_seed_track_id: str | None = None
        self._compute_inflight = False
        self._compute_inflight_seed_track_id: str | None = None
        self._next_compute_allowed_at = 0.0

    def current(self) -> dict | None:
        """Latest suggestion dict (or None). Called at the ws serialize edge."""
        with self._lock:
            return self._current

    def _prepared_target_for_seed(self, seed: ResolvedSeed) -> PreparedTarget | None:
        """Return the strong deck target or soft saved-pool next target."""
        if seed.target_track_id:
            return PreparedTarget(
                track_id=seed.target_track_id,
                reason_prefix="loaded on target deck",
                source="target_deck",
                strict=True,
            )
        loader = self._prepared_pool_loader
        if loader is None:
            return None
        try:
            pool = loader()
        except Exception as e:  # pragma: no cover — defensive
            logger.warning("[suggestion] prepared pool lookup failed: %s", e)
            return None
        if pool is None:
            return None
        target_id = next_track_id_after(pool, seed.track_id)
        if not target_id:
            return None
        try:
            if self._library.lookup_by_id(target_id) is None:
                return None
        except Exception as e:  # pragma: no cover — defensive
            logger.warning("[suggestion] prepared pool target lookup failed: %s", e)
            return None
        return PreparedTarget(
            track_id=target_id,
            reason_prefix="next in saved pool",
            source="prepared_pool",
            strict=False,
        )

    def _prepared_target_for_context(self, seed: ResolvedSeed | None) -> str | None:
        if seed is None:
            return None
        with self._lock:
            if self._seed_track_id == seed.track_id:
                return self._prepared_target_track_id
        return seed.target_track_id

    def current_for_state(self, state: Any) -> dict | None:
        """Latest suggestion after a throttled live shortlist refresh.

        This keeps the expensive embedding shortlist stable between TRACK_CHANGE
        recomputes while letting the set-aware winner and timing follow the
        live playhead. It is
        safe to call from the 30Hz broadcast edge: the expensive full library
        ranking is only scheduled when no current pick exists for the live seed,
        and this path refreshes timing at most every
        ``LIVE_REFRESH_INTERVAL_S`` seconds.
        """
        self.maybe_schedule_compute_from_state(state)
        return self.refresh_from_state(state)

    def choose_alternative(
        self,
        *,
        candidate_id: str | None = None,
        track_id: str | None = None,
        state: Any | None = None,
    ) -> dict | None:
        """Promote a visible transition alternative without a full rerank."""
        with self._lock:
            current = dict(self._current) if self._current is not None else None
            seed_track_id = self._seed_track_id
            candidate_vectors_by_track_id = {
                tid: vector.copy() for tid, vector in self._candidate_vectors_by_track_id.items()
            }
            fallback_candidate_track_id = self._candidate_track_id
            fallback_candidate_vector = (
                self._candidate_vector.copy() if self._candidate_vector is not None else None
            )

        if current is None:
            return None

        alternatives = _coerce_transition_alternatives(current.get("transition_alternatives"))
        selected_before = _matching_alternative(
            alternatives,
            candidate_id=candidate_id,
            track_id=track_id,
        )
        previous_before = alternatives[0] if alternatives else None
        promoted = promote_transition_alternative(
            alternatives,
            candidate_id=candidate_id,
            track_id=track_id,
        )
        if promoted == alternatives:
            if _alternative_already_selected(
                alternatives,
                candidate_id=candidate_id,
                track_id=track_id,
            ):
                return current
            return None

        fallback_track = fallback_candidate_track_id or str(current.get("track_id") or "")
        selected_track_id, selected_vector = _apply_winning_alternative(
            current,
            promoted,
            candidate_vectors_by_track_id,
            fallback_candidate_track_id=fallback_track,
            fallback_candidate_vector=fallback_candidate_vector,
        )
        with self._lock:
            next_grade_progress = dict(self._grade_progress)
        current, next_grade_progress = _attach_grade_progress(current, next_grade_progress)
        if state is not None:
            current["decision"] = self._safe_decision_payload_for_suggestion(state, current)

        feedback_event = self._feedback_event_for_choice(
            selected_before=selected_before,
            selected_after=promoted[0] if promoted else None,
            previous_before=previous_before,
            seed_track_id=seed_track_id,
            requested_candidate_id=candidate_id,
            requested_track_id=track_id,
        )
        with self._lock:
            if self._current is None:
                return None
            self._grade_progress = next_grade_progress
            self._current = current
            self._candidate_track_id = selected_track_id
            self._candidate_vector = selected_vector.copy() if selected_vector is not None else None
            self._pinned_candidate_track_id = selected_track_id
            result = self._current

        if feedback_event is not None:
            self._emit_feedback(feedback_event)
        return result

    def update_taste_scores(
        self, new_scores: dict[tuple[str, str], float] | None
    ) -> None:
        """One Mind S3 — apply a fresh taste model to the LIVE service.

        Previously ``_taste_scores`` was set once at construction and never
        moved: a transition the DJ rejected mid-set only changed scoring at the
        NEXT launch. The live feedback sink now re-reads the just-appended
        feedback into a fresh taste model and hands the scores here, so the
        pill + coach pivot THIS session. Lock-guarded against concurrent
        scoring (the sink is invoked lock-free, so this acquire can't deadlock).
        ``None`` / empty is a no-op — a transient load failure must never wipe
        the scores we already had.
        """
        if not new_scores:
            return
        with self._lock:
            self._taste_scores = dict(new_scores)

    def record_feedback(
        self,
        feedback: str | None,
        *,
        state: Any | None = None,
    ) -> FeedbackEvent | None:
        """Record an explicit live-pill feedback control for the current pick."""
        key = _feedback_key(feedback)
        action_label = EXPLICIT_FEEDBACK_ACTIONS.get(key)
        if action_label is None:
            return None
        action, label = action_label
        with self._lock:
            suggestion = dict(self._current) if self._current is not None else None
            seed_track_id = self._seed_track_id
            candidate_track_id = self._candidate_track_id
            candidate_vectors_by_track_id = {
                tid: vector.copy() for tid, vector in self._candidate_vectors_by_track_id.items()
            }
            fallback_candidate_track_id = self._candidate_track_id
            fallback_candidate_vector = (
                self._candidate_vector.copy() if self._candidate_vector is not None else None
            )
        if suggestion is None:
            return None
        active_seed = resolve_seed_context(state) if state is not None else None
        event = self._feedback_event_for_suggestion(
            action=action,
            label=label,
            suggestion=suggestion,
            seed_track_id=active_seed.track_id if active_seed is not None else seed_track_id,
            inferred=False,
        )
        if event is not None:
            self._emit_feedback(event)
        if label == "accepted" and candidate_track_id is not None:
            with self._lock:
                if self._current is not None:
                    self._pinned_candidate_track_id = candidate_track_id
        if label == "not_now":
            self._promote_next_backup_after_feedback(
                suggestion,
                candidate_vectors_by_track_id,
                fallback_candidate_track_id=fallback_candidate_track_id,
                fallback_candidate_vector=fallback_candidate_vector,
                state=state,
            )
        if label == "wrong_timing" and seed_track_id is not None and candidate_track_id is not None:
            self._suppress_timing_for_pair(
                seed_track_id,
                candidate_track_id,
                state=state,
            )
        return event

    def _promote_next_backup_after_feedback(
        self,
        suggestion: dict,
        candidate_vectors_by_track_id: dict[str, Any],
        *,
        fallback_candidate_track_id: str | None,
        fallback_candidate_vector: Any | None,
        state: Any | None,
    ) -> None:
        alternatives = _coerce_transition_alternatives(suggestion.get("transition_alternatives"))
        if len(alternatives) < 2:
            return
        backup = alternatives[1]
        backup_track_id = _str_or_none(backup.get("track_id"))
        backup_candidate_id = _str_or_none(backup.get("candidate_id"))
        promoted = promote_transition_alternative(
            alternatives,
            candidate_id=backup_candidate_id,
            track_id=backup_track_id,
        )
        if promoted == alternatives:
            return

        fallback_track = fallback_candidate_track_id or str(suggestion.get("track_id") or "")
        selected_track_id, selected_vector = _apply_winning_alternative(
            suggestion,
            promoted,
            candidate_vectors_by_track_id,
            fallback_candidate_track_id=fallback_track,
            fallback_candidate_vector=fallback_candidate_vector,
        )
        with self._lock:
            next_grade_progress = dict(self._grade_progress)
        suggestion, next_grade_progress = _attach_grade_progress(
            suggestion,
            next_grade_progress,
        )
        if state is not None:
            suggestion["decision"] = self._safe_decision_payload_for_suggestion(state, suggestion)

        with self._lock:
            if self._current is None:
                return
            self._grade_progress = next_grade_progress
            self._current = suggestion
            self._candidate_track_id = selected_track_id
            self._candidate_vector = selected_vector.copy() if selected_vector is not None else None
            self._pinned_candidate_track_id = selected_track_id

    def _suppress_timing_for_pair(
        self,
        seed_track_id: str,
        candidate_track_id: str,
        *,
        state: Any | None,
    ) -> None:
        key = (seed_track_id, candidate_track_id)
        with self._lock:
            current = dict(self._current) if self._current is not None else None
            self._timing_suppressed_pairs.add(key)
        if current is None:
            return
        _strip_suggestion_timing(current, candidate_track_id)
        if state is not None:
            current["decision"] = self._safe_decision_payload_for_suggestion(state, current)
        with self._lock:
            if self._current is not None and self._seed_track_id == seed_track_id:
                self._current = current

    def _feedback_event_for_choice(
        self,
        *,
        selected_before: dict | None,
        selected_after: dict | None,
        previous_before: dict | None,
        seed_track_id: str | None,
        requested_candidate_id: str | None,
        requested_track_id: str | None,
    ) -> FeedbackEvent | None:
        if self._feedback_sink is None or selected_after is None:
            return None
        transition = _dict_or_none(selected_after.get("transition"))
        if transition is None and selected_before is not None:
            transition = _dict_or_none(selected_before.get("transition"))
        row: dict[str, Any] = {
            "event_id": f"live_next_choice_{self._feedback_session_id}_{time.time_ns()}",
            "session_id": self._feedback_session_id,
            "surface": "live_next_pill",
            "action": "transition_labeled",
            "label": "played_next",
            "split": "calibration",
            "candidate_id": _str_or_none(
                (selected_before or {}).get("candidate_id")
                or selected_after.get("candidate_id")
                or requested_candidate_id
            ),
            "selected_track_id": _str_or_none(selected_after.get("track_id") or requested_track_id),
            "requested_candidate_id": _str_or_none(requested_candidate_id),
            "requested_track_id": _str_or_none(requested_track_id),
            "seed_track_id": _str_or_none(seed_track_id),
            "replaced_candidate_id": _str_or_none((previous_before or {}).get("candidate_id")),
            "replaced_track_id": _str_or_none((previous_before or {}).get("track_id")),
            "promoted_candidate_id": _str_or_none(selected_after.get("candidate_id")),
            "profile_consent": True,
        }
        if transition is not None:
            row.update(_transition_feedback_fields(transition))
        return parse_feedback_event(row)

    def _feedback_event_for_seed_change(
        self,
        *,
        previous: dict | None,
        previous_seed_track_id: str | None,
        new_seed_track_id: str | None,
    ) -> FeedbackEvent | None:
        if previous is None or not new_seed_track_id or new_seed_track_id == previous_seed_track_id:
            return None
        suggested_track_id = _str_or_none(previous.get("track_id"))
        if suggested_track_id is None:
            return None
        label = "played_next" if new_seed_track_id == suggested_track_id else "different_track"
        return self._feedback_event_for_suggestion(
            action="suggestion_played_next"
            if label == "played_next"
            else "suggestion_different_track",
            label=label,
            suggestion=previous,
            seed_track_id=previous_seed_track_id,
            actual_next_track_id=new_seed_track_id,
            inferred=True,
        )

    def _feedback_event_for_suggestion(
        self,
        *,
        action: str,
        label: str | None,
        suggestion: dict | None,
        seed_track_id: str | None,
        actual_next_track_id: str | None = None,
        inferred: bool,
    ) -> FeedbackEvent | None:
        if self._feedback_sink is None or suggestion is None:
            return None
        transition = _dict_or_none(suggestion.get("transition"))
        row: dict[str, Any] = {
            "event_id": f"live_next_{action}_{self._feedback_session_id}_{time.time_ns()}",
            "session_id": self._feedback_session_id,
            "surface": "live_next_pill",
            "action": action,
            "label": label,
            "split": "calibration",
            "candidate_id": _candidate_id_for_suggestion(suggestion),
            "selected_track_id": _str_or_none(suggestion.get("track_id")),
            "actual_next_track_id": _str_or_none(actual_next_track_id),
            "seed_track_id": _str_or_none(seed_track_id),
            "inferred": inferred,
            "profile_consent": True,
        }
        if transition is not None:
            row.update(_transition_feedback_fields(transition))
        return parse_feedback_event(row)

    def _emit_feedback(self, event: FeedbackEvent) -> None:
        sink = self._feedback_sink
        if sink is None:
            return
        try:
            sink(event)
        except Exception as e:
            logger.warning("[suggestion] feedback sink failed: %s", e)

    def context_for_state(
        self,
        state: Any,
        *,
        packet_id: str = "ctx_live_next_pill",
    ) -> Any | None:
        """Compile the live pill shortlist into a model-safe context envelope."""
        suggestion = self.current_for_state(state)
        if suggestion is None:
            return None
        return self._context_for_suggestion(state, suggestion, packet_id=packet_id)

    def _context_for_suggestion(
        self,
        state: Any,
        suggestion: dict,
        *,
        packet_id: str,
    ) -> Any | None:
        seed = resolve_seed_context(state)
        timing = resolve_live_timing(state)
        prepared_target_track_id = self._prepared_target_for_context(seed)
        controller = resolve_controller_mix_context(
            state,
            source_deck=seed.source_deck if seed is not None else None,
            target_deck=seed.target_deck if seed is not None else None,
        )
        current = {
            "active_track_id": seed.track_id if seed is not None else None,
            "source_deck": seed.source_deck if seed is not None else None,
            "target_deck": seed.target_deck if seed is not None else None,
            "prepared_target_track_id": prepared_target_track_id,
            "grade_progress": suggestion.get("grade_progress")
            if isinstance(suggestion.get("grade_progress"), dict)
            else None,
            "blend_active": timing.blend_active,
            "source_loop_recent": timing.source_loop_recent,
            "playhead_confidence": timing.playhead_confidence,
            "source_position_s": timing.source_position_s,
            "source_context": self._source_context(seed, timing),
            "controller": controller,
        }
        from vibemix.intel.context_compiler import compile_suggestion_context

        return compile_suggestion_context(
            packet_id=packet_id,
            current=current,
            suggestion=suggestion,
        )

    def _source_context(
        self,
        seed: ResolvedSeed | None,
        timing: LiveTimingHint,
    ) -> dict[str, Any] | None:
        """Return model-safe current/next source-section context for live mode."""
        if seed is None or timing.source_position_s is None:
            return None
        source_entry = self._library.lookup_by_id(seed.track_id)
        if source_entry is None:
            return None
        try:
            from vibemix.library.section_builder import (
                bars_until_section_end,
                bars_until_section_start,
                next_section_after_position,
                section_at_position,
                sections_for_entry,
            )

            sections = sections_for_entry(source_entry)
            current_section = section_at_position(sections, timing.source_position_s)
            next_section = next_section_after_position(sections, timing.source_position_s)
            return {
                "track_id": seed.track_id,
                "position_s": timing.source_position_s,
                "playhead_confidence": timing.playhead_confidence,
                "source_loop_recent": timing.source_loop_recent,
                "lookahead_allowed": not timing.source_loop_recent,
                "section_clock": "loop_hold" if timing.source_loop_recent else "playhead",
                "current_section": _section_context_payload(current_section),
                "next_section": _section_context_payload(next_section),
                "bars_to_current_section_end": bars_until_section_end(
                    current_section,
                    timing.source_position_s,
                ),
                "bars_to_next_section_start": bars_until_section_start(
                    next_section,
                    timing.source_position_s,
                ),
            }
        except Exception as e:
            logger.debug("[suggestion] source context unavailable: %s", e)
            return None

    def decision_for_state(
        self,
        state: Any,
        *,
        packet_id: str = "ctx_live_next_pill",
        snapshot_id: str = "snapshot_live_next_pill",
        decision_id: str = "dec_live_next_pill",
        trace_id: str = "trace_live_next_pill",
    ) -> Any | None:
        """Return a validated deterministic/model-safe decision for the pill."""
        suggestion = self.current_for_state(state)
        if suggestion is None:
            return None
        return self._decision_for_suggestion(
            state,
            suggestion,
            packet_id=packet_id,
            snapshot_id=snapshot_id,
            decision_id=decision_id,
            trace_id=trace_id,
        )

    def _decision_for_suggestion(
        self,
        state: Any,
        suggestion: dict,
        *,
        packet_id: str,
        snapshot_id: str,
        decision_id: str,
        trace_id: str,
    ) -> Any | None:
        envelope = self._context_for_suggestion(state, suggestion, packet_id=packet_id)
        if envelope is None:
            return None
        from vibemix.intel.decision_runtime import RuntimeInputSnapshot, decide

        return decide(
            "live",
            "live_next_pill",
            RuntimeInputSnapshot(snapshot_id, envelope),
            decision_id=decision_id,
            trace_id=trace_id,
        )

    def decision_payload_for_state(
        self,
        state: Any,
        *,
        packet_id: str = "ctx_live_next_pill",
        snapshot_id: str = "snapshot_live_next_pill",
        decision_id: str = "dec_live_next_pill",
        trace_id: str = "trace_live_next_pill",
    ) -> dict | None:
        """Compact, JSON-safe validated decision payload for UI wires."""
        suggestion = self.current_for_state(state)
        if suggestion is None:
            return None
        return self._decision_payload_for_suggestion(
            state,
            suggestion,
            packet_id=packet_id,
            snapshot_id=snapshot_id,
            decision_id=decision_id,
            trace_id=trace_id,
        )

    def _decision_payload_for_suggestion(
        self,
        state: Any,
        suggestion: dict,
        *,
        packet_id: str,
        snapshot_id: str,
        decision_id: str,
        trace_id: str,
    ) -> dict | None:
        result = self._decision_for_suggestion(
            state,
            suggestion,
            packet_id=packet_id,
            snapshot_id=snapshot_id,
            decision_id=decision_id,
            trace_id=trace_id,
        )
        if result is None:
            return None
        decision = result.final_decision
        return {
            "decision_id": result.decision_id,
            "decision_source": result.decision_source,
            "emitted": result.emitted,
            "validation_status": result.validation_result.status,
            "validation_errors": list(result.validation_result.errors),
            "suppressed_reasons": list(result.trace.suppressed_reasons),
            "gate_results": [
                {"name": gate.name, "status": gate.status, "reason": gate.reason}
                for gate in result.trace.gate_results
            ],
            "action": decision.action,
            "candidate_id": decision.candidate_id,
            "cue_slot": decision.cue_slot,
            "timing_text": decision.timing_text,
            "spoken_text": decision.spoken_text,
            "cited_claims": list(decision.cited_claims),
            "cited_claim_ids": list(decision.cited_claim_ids),
            "confidence": decision.confidence,
        }

    def _safe_decision_payload_for_suggestion(self, state: Any, suggestion: dict) -> dict | None:
        try:
            return self._decision_payload_for_suggestion(
                state,
                suggestion,
                packet_id="ctx_live_next_pill",
                snapshot_id="snapshot_live_next_pill",
                decision_id="dec_live_next_pill",
                trace_id="trace_live_next_pill",
            )
        except Exception as e:
            logger.warning("[suggestion] decision payload failed: %s", e)
            return None

    def maybe_schedule_compute_from_state(
        self,
        state: Any,
        *,
        loop: asyncio.AbstractEventLoop | None = None,
        now: float | None = None,
    ) -> bool:
        """Schedule a non-blocking full compute when the current seed needs one.

        The broadcast loop may call this every frame. The method is intentionally
        conservative: it schedules at most one executor job at a time, skips when
        a current suggestion already matches the resolved seed, and backs off
        after an unresolved/no-candidate result.
        """
        seed = resolve_seed_context(state)
        if seed is None:
            return False
        timing = resolve_live_timing(state)
        now = time.monotonic() if now is None else now
        with self._lock:
            if self._compute_inflight:
                return False
            if self._current is not None and self._seed_track_id == seed.track_id:
                return False
            if (
                self._current is None
                and self._last_compute_seed_track_id == seed.track_id
                and now < self._next_compute_allowed_at
            ):
                return False
            self._compute_inflight = True
            self._compute_inflight_seed_track_id = seed.track_id
            self._next_compute_allowed_at = now + FULL_COMPUTE_DISPATCH_GUARD_S

        try:
            loop = loop or asyncio.get_running_loop()
        except RuntimeError:
            with self._lock:
                if self._compute_inflight_seed_track_id == seed.track_id:
                    self._compute_inflight = False
                    self._compute_inflight_seed_track_id = None
            return False

        fut = loop.run_in_executor(None, self.compute_for_seed, seed, timing)
        fut.add_done_callback(lambda f: self._finish_scheduled_compute(seed.track_id, f))
        return True

    def compute(
        self,
        seed_track_id: str,
        *,
        seed_camelot: str | None = None,
        seed_bpm: float | None = None,
        source_deck: str | None = None,
        target_deck: str | None = None,
        prepared_target_track_id: str | None = None,
        prepared_target_reason_prefix: str = "loaded on target deck",
        prepared_target_source: str = "target_deck",
        prepared_target_strict: bool = True,
        live_remaining_bars: int | None = None,
        live_playhead_confidence: float = 0.0,
        blend_active: bool = False,
        source_loop_recent: bool = False,
        source_position_s: float | None = None,
    ) -> dict | None:
        """Recompute from a seed track_id. Marks the seed played, returns +
        stores the new suggestion dict (or None). Sync — run in an executor.
        """
        vec = seed_vector_for_track_id(self._store, seed_track_id)
        if vec is None:
            with self._lock:
                self._last_compute_seed_track_id = seed_track_id
            return self.current()  # seed not embedded → leave current as-is

        with self._lock:
            played = set(self._played)
            self._played.add(seed_track_id)

        try:
            sugg = next_suggestion(
                self._store,
                self._library,
                seed_vector=vec,
                seed_track_id=seed_track_id,
                played_ids=played,
                seed_camelot=seed_camelot,
                seed_bpm=seed_bpm,
                source_deck=source_deck,
                target_deck=target_deck,
                prepared_target_track_id=prepared_target_track_id,
                prepared_target_reason_prefix=prepared_target_reason_prefix,
                prepared_target_source=prepared_target_source,
                k=self._k,
                live_remaining_bars=live_remaining_bars,
                live_playhead_confidence=live_playhead_confidence,
                blend_active=blend_active,
                source_loop_recent=source_loop_recent,
                source_position_s=source_position_s,
                taste_scores=self._taste_scores,
            )
        except Exception as e:
            logger.warning("[suggestion] compute failed: %s", e)
            return self.current()

        d = sugg.to_dict() if sugg is not None else None
        candidate_track_id = d.get("track_id") if d is not None else None
        candidate_track_ids = _transition_alternative_track_ids(d)
        candidate_vectors_by_track_id = (
            vectors_for_track_ids(self._store, list(candidate_track_ids))
            if candidate_track_ids
            else {}
        )
        candidate_vector = None
        if isinstance(candidate_track_id, str):
            candidate_vector = candidate_vectors_by_track_id.get(candidate_track_id)
            if candidate_vector is None:
                candidate_vector = seed_vector_for_track_id(self._store, candidate_track_id)
        outcome_event: FeedbackEvent | None = None
        with self._lock:
            previous = dict(self._current) if self._current is not None else None
            previous_seed_track_id = self._seed_track_id
            if previous is not None and previous_seed_track_id != seed_track_id:
                outcome_event = self._feedback_event_for_seed_change(
                    previous=previous,
                    previous_seed_track_id=previous_seed_track_id,
                    new_seed_track_id=seed_track_id,
                )
            if d is not None:
                d, self._grade_progress = _attach_grade_progress(d, self._grade_progress)
            else:
                self._grade_progress = _empty_grade_progress(
                    _int_range(self._grade_progress.get("total_xp"), 0, 999_999, 0)
                )
            self._current = d
            self._seed_track_id = seed_track_id if d is not None else None
            self._seed_vector = vec.copy() if d is not None else None
            self._candidate_track_id = (
                candidate_track_id if isinstance(candidate_track_id, str) else None
            )
            self._prepared_target_track_id = (
                _context_prepared_target(
                    prepared_target_track_id,
                    candidate_track_id,
                    strict=prepared_target_strict,
                )
                if d is not None
                else None
            )
            self._candidate_vector = (
                candidate_vector.copy() if candidate_vector is not None else None
            )
            self._candidate_vectors_by_track_id = {
                track_id: vector.copy()
                for track_id, vector in candidate_vectors_by_track_id.items()
            }
            self._pinned_candidate_track_id = None
            if previous_seed_track_id != seed_track_id:
                self._timing_suppressed_pairs = {
                    pair for pair in self._timing_suppressed_pairs if pair[0] == seed_track_id
                }
            self._last_compute_seed_track_id = seed_track_id
            self._last_refresh_at = 0.0
        if outcome_event is not None:
            self._emit_feedback(outcome_event)
        shown_event = self._feedback_event_for_suggestion(
            action="suggestion_shown",
            label=None,
            suggestion=d,
            seed_track_id=seed_track_id,
            inferred=True,
        )
        if shown_event is not None:
            self._emit_feedback(shown_event)
        return d

    def compute_for_seed(self, seed: ResolvedSeed, timing: LiveTimingHint) -> dict | None:
        """Compute from already-resolved seed/timing facts."""
        prepared = self._prepared_target_for_seed(seed)
        return self.compute(
            seed.track_id,
            seed_camelot=seed.camelot,
            seed_bpm=seed.bpm,
            source_deck=seed.source_deck,
            target_deck=seed.target_deck,
            prepared_target_track_id=prepared.track_id if prepared is not None else None,
            prepared_target_reason_prefix=prepared.reason_prefix
            if prepared is not None
            else "loaded on target deck",
            prepared_target_source=prepared.source if prepared is not None else "target_deck",
            prepared_target_strict=prepared.strict if prepared is not None else True,
            live_remaining_bars=timing.remaining_bars,
            live_playhead_confidence=timing.playhead_confidence,
            blend_active=timing.blend_active,
            source_loop_recent=timing.source_loop_recent,
            source_position_s=timing.source_position_s,
        )

    def compute_from_state(self, state: Any) -> dict | None:
        """Resolve the seed from MusicState, then compute. No-op (returns the
        current suggestion) when the now-playing track_id can't be resolved."""
        seed = resolve_seed_context(state)
        if seed is None:
            return self.current()
        timing = resolve_live_timing(state)
        prepared = self._prepared_target_for_seed(seed)
        return self.compute(
            seed.track_id,
            seed_camelot=seed.camelot,
            seed_bpm=seed.bpm,
            source_deck=seed.source_deck,
            target_deck=seed.target_deck,
            prepared_target_track_id=prepared.track_id if prepared is not None else None,
            prepared_target_reason_prefix=prepared.reason_prefix
            if prepared is not None
            else "loaded on target deck",
            prepared_target_source=prepared.source if prepared is not None else "target_deck",
            prepared_target_strict=prepared.strict if prepared is not None else True,
            live_remaining_bars=timing.remaining_bars,
            live_playhead_confidence=timing.playhead_confidence,
            blend_active=timing.blend_active,
            source_loop_recent=timing.source_loop_recent,
            source_position_s=timing.source_position_s,
        )

    def refresh_from_state(
        self,
        state: Any,
        *,
        now: float | None = None,
        min_interval_s: float = LIVE_REFRESH_INTERVAL_S,
    ) -> dict | None:
        """Refresh only the live transition payload for the current pick."""
        now = time.monotonic() if now is None else now
        with self._lock:
            if min_interval_s > 0 and now - self._last_refresh_at < min_interval_s:
                return self._current
            self._last_refresh_at = now
            current = dict(self._current) if self._current is not None else None
            seed_track_id = self._seed_track_id
            seed_vector = self._seed_vector.copy() if self._seed_vector is not None else None
            cached_candidate_track_id = self._candidate_track_id
            candidate_vector = (
                self._candidate_vector.copy() if self._candidate_vector is not None else None
            )
            candidate_vectors_by_track_id = {
                track_id: vector.copy()
                for track_id, vector in self._candidate_vectors_by_track_id.items()
            }
            pinned_candidate_track_id = self._pinned_candidate_track_id
            timing_suppressed_pairs = set(self._timing_suppressed_pairs)

        if current is None or seed_track_id is None or seed_vector is None:
            return current

        seed = resolve_seed_context(state)
        if seed is None:
            return current
        if seed.track_id != seed_track_id:
            feedback_event = self._feedback_event_for_seed_change(
                previous=current,
                previous_seed_track_id=seed_track_id,
                new_seed_track_id=seed.track_id,
            )
            with self._lock:
                if self._seed_track_id == seed_track_id:
                    self._current = None
                    self._seed_track_id = None
                    self._seed_vector = None
                    self._candidate_track_id = None
                    self._candidate_vector = None
                    self._candidate_vectors_by_track_id = {}
                    self._prepared_target_track_id = None
                    self._pinned_candidate_track_id = None
                    self._grade_progress = _empty_grade_progress(
                        _int_range(self._grade_progress.get("total_xp"), 0, 999_999, 0)
                    )
                    self._timing_suppressed_pairs = {
                        pair for pair in self._timing_suppressed_pairs if pair[0] != seed_track_id
                    }
                    self._last_compute_seed_track_id = None
            if feedback_event is not None:
                self._emit_feedback(feedback_event)
            return None

        candidate_track_id = current.get("track_id")
        if not isinstance(candidate_track_id, str) or not candidate_track_id:
            return current
        if candidate_track_id != cached_candidate_track_id:
            candidate_vector = None

        timing = resolve_live_timing(state)
        prepared = self._prepared_target_for_seed(seed)
        prepared_target_track_id = prepared.track_id if prepared is not None else None
        alternatives = _coerce_transition_alternatives(current.get("transition_alternatives"))
        if alternatives:
            refreshed_transitions: dict[str, dict | None] = {}
            for alternative in alternatives:
                track_id = alternative.get("track_id")
                if not isinstance(track_id, str) or not track_id:
                    continue
                refreshed_transitions[track_id] = transition_payload_for_candidate(
                    self._store,
                    self._library,
                    seed_track_id=seed_track_id,
                    seed_vector=seed_vector,
                    candidate_track_id=track_id,
                    source_deck=seed.source_deck,
                    target_deck=seed.target_deck,
                    remaining_bars=timing.remaining_bars,
                    playhead_confidence=timing.playhead_confidence,
                    blend_active=timing.blend_active,
                    source_loop_recent=timing.source_loop_recent,
                    source_position_s=timing.source_position_s,
                    destination_vector=candidate_vectors_by_track_id.get(track_id),
                    taste_scores=self._taste_scores,
                )
                if (seed_track_id, track_id) in timing_suppressed_pairs:
                    refreshed_transitions[track_id] = _strip_transition_timing(
                        refreshed_transitions[track_id]
                    )
            if prepared_target_track_id and not any(
                alternative.get("track_id") == prepared_target_track_id
                for alternative in alternatives
            ):
                target_payload = prepared_target_candidate_payload(
                    self._store,
                    self._library,
                    seed_vector=seed_vector,
                    track_id=prepared_target_track_id,
                    reason_prefix=prepared.reason_prefix
                    if prepared is not None
                    else "loaded on target deck",
                    source=prepared.source if prepared is not None else "target_deck",
                )
                if target_payload is not None:
                    target_alternative, target_vector = target_payload
                    transition = transition_payload_for_candidate(
                        self._store,
                        self._library,
                        seed_track_id=seed_track_id,
                        seed_vector=seed_vector,
                        candidate_track_id=prepared_target_track_id,
                        source_deck=seed.source_deck,
                        target_deck=seed.target_deck,
                        remaining_bars=timing.remaining_bars,
                        playhead_confidence=timing.playhead_confidence,
                        blend_active=timing.blend_active,
                        source_loop_recent=timing.source_loop_recent,
                        source_position_s=timing.source_position_s,
                        destination_vector=target_vector,
                        taste_scores=self._taste_scores,
                    )
                    if (seed_track_id, prepared_target_track_id) in timing_suppressed_pairs:
                        transition = _strip_transition_timing(transition)
                    if transition is not None:
                        target_alternative["transition"] = transition
                        alternatives = (*alternatives, target_alternative)
                        refreshed_transitions[prepared_target_track_id] = transition
                        candidate_vectors_by_track_id[prepared_target_track_id] = target_vector
            alternatives = ranked_transition_alternatives(
                alternatives,
                refreshed_transitions,
            )
            if prepared_target_track_id and _alternative_has_transition(
                alternatives,
                track_id=prepared_target_track_id,
            ):
                alternatives = promote_transition_alternative(
                    alternatives,
                    track_id=prepared_target_track_id,
                )
            elif pinned_candidate_track_id:
                alternatives = promote_transition_alternative(
                    alternatives,
                    track_id=pinned_candidate_track_id,
                )
            candidate_track_id, candidate_vector = _apply_winning_alternative(
                current,
                alternatives,
                candidate_vectors_by_track_id,
                fallback_candidate_track_id=candidate_track_id,
                fallback_candidate_vector=candidate_vector,
            )
        else:
            transition = transition_payload_for_candidate(
                self._store,
                self._library,
                seed_track_id=seed_track_id,
                seed_vector=seed_vector,
                candidate_track_id=candidate_track_id,
                source_deck=seed.source_deck,
                target_deck=seed.target_deck,
                remaining_bars=timing.remaining_bars,
                playhead_confidence=timing.playhead_confidence,
                blend_active=timing.blend_active,
                source_loop_recent=timing.source_loop_recent,
                source_position_s=timing.source_position_s,
                destination_vector=candidate_vector,
                taste_scores=self._taste_scores,
            )
            transition = annotate_transition_selection(
                transition,
                _float_or(current.get("similarity"), None),
            )
            if (seed_track_id, candidate_track_id) in timing_suppressed_pairs:
                transition = _strip_transition_timing(transition)
            current["transition"] = transition
        with self._lock:
            next_grade_progress = dict(self._grade_progress)
        current, next_grade_progress = _attach_grade_progress(current, next_grade_progress)
        current["decision"] = self._safe_decision_payload_for_suggestion(state, current)
        with self._lock:
            if self._seed_track_id == seed_track_id and self._current is not None:
                self._grade_progress = next_grade_progress
                self._current = current
                self._candidate_track_id = candidate_track_id
                self._prepared_target_track_id = _context_prepared_target(
                    prepared_target_track_id,
                    candidate_track_id,
                    strict=prepared.strict if prepared is not None else True,
                )
                self._candidate_vector = (
                    candidate_vector.copy() if candidate_vector is not None else None
                )
                self._pinned_candidate_track_id = (
                    pinned_candidate_track_id
                    if pinned_candidate_track_id == candidate_track_id
                    else None
                )
                return self._current
            return self._current

    def _finish_scheduled_compute(self, seed_track_id: str, fut: Any) -> None:
        try:
            result = fut.result()
        except Exception as e:
            logger.warning("[suggestion] scheduled compute failed: %s", e)
            result = None
        with self._lock:
            if self._compute_inflight_seed_track_id == seed_track_id:
                self._compute_inflight = False
                self._compute_inflight_seed_track_id = None
            if result is None:
                self._next_compute_allowed_at = time.monotonic() + FULL_COMPUTE_RETRY_S
            else:
                self._next_compute_allowed_at = 0.0


def _transition_alternative_track_ids(raw: dict | None) -> tuple[str, ...]:
    if raw is None:
        return ()
    alternatives = _coerce_transition_alternatives(raw.get("transition_alternatives"))
    ids = [
        alternative.get("track_id")
        for alternative in alternatives
        if isinstance(alternative.get("track_id"), str) and alternative.get("track_id")
    ]
    track_id = raw.get("track_id")
    if isinstance(track_id, str) and track_id:
        ids.insert(0, track_id)
    return tuple(dict.fromkeys(str(track_id) for track_id in ids))


def _empty_grade_progress(total_xp: int = 0) -> dict[str, Any]:
    return {
        "key": "",
        "slug": "",
        "streak": 0,
        "xp": 0,
        "total_xp": max(0, int(total_xp)),
        "last_xp": 0,
        "earned": False,
        "heat": 0,
        "level_up": False,
        "levels_gained": 0,
    }


def _attach_grade_progress(
    suggestion: dict,
    previous_progress: dict[str, Any],
) -> tuple[dict, dict[str, Any]]:
    current = dict(suggestion)
    progress = _next_grade_progress(previous_progress, current)
    current["grade_progress"] = _public_grade_progress(progress)
    return current, progress


def _next_grade_progress(
    previous_progress: dict[str, Any],
    suggestion: dict,
) -> dict[str, Any]:
    total_xp = _int_range(previous_progress.get("total_xp"), 0, 999_999, 0)
    grade = _selected_move_grade(suggestion)
    key = _suggestion_grade_key(suggestion, grade)
    if grade is None or not key:
        return _empty_grade_progress(total_xp)

    slug = _str_or_none(grade.get("slug")) or ""
    xp = _int_range(grade.get("xp"), 0, 999, 0)
    if previous_progress.get("key") == key and previous_progress.get("slug") == slug:
        return dict(previous_progress)

    earned = bool(grade.get("deserved")) and slug not in {"mid", "negative"}
    streak = (
        _int_range(previous_progress.get("streak"), 0, 999, 0) + 1
        if earned
        else 0
    )
    last_xp = xp if earned else 0
    next_total_xp = min(999_999, total_xp + last_xp)
    previous_level = _grade_xp_level(total_xp)["level"]
    next_level = _grade_xp_level(next_total_xp)["level"]
    levels_gained = max(0, next_level - previous_level) if earned else 0
    return {
        "key": key,
        "slug": slug,
        "streak": streak,
        "xp": xp,
        "total_xp": next_total_xp,
        "last_xp": last_xp,
        "earned": earned,
        "heat": min(
            100,
            max(
                _int_range(grade.get("intensity"), 0, 100, 0),
                streak * 18,
            ),
        )
        if earned
        else 0,
        "level_up": levels_gained > 0,
        "levels_gained": levels_gained,
    }


def _public_grade_progress(progress: dict[str, Any]) -> dict[str, Any]:
    total_xp = _int_range(progress.get("total_xp"), 0, 999_999, 0)
    return {
        "streak": _int_range(progress.get("streak"), 0, 999, 0),
        "total_xp": total_xp,
        "last_xp": _int_range(progress.get("last_xp"), 0, 999, 0),
        "earned": bool(progress.get("earned")),
        "heat": _int_range(progress.get("heat"), 0, 100, 0),
        "level_up": bool(progress.get("level_up")),
        "levels_gained": _int_range(progress.get("levels_gained"), 0, 999, 0),
        **_grade_xp_level(total_xp),
    }


def _grade_xp_level(total_xp: int) -> dict[str, int]:
    total = _int_range(total_xp, 0, 999_999, 0)
    step = GRADE_XP_LEVEL_STEP
    level = min(999, total // step + 1)
    level_xp = total % step
    return {
        "level": level,
        "level_xp": level_xp,
        "next_level_xp": step,
        "level_progress": round((level_xp / step) * 100),
    }


def _selected_move_grade(suggestion: dict) -> dict[str, Any] | None:
    transition = _dict_or_none(suggestion.get("transition"))
    grade = _dict_or_none((transition or {}).get("move_grade"))
    if grade is not None:
        return grade
    for alternative in _coerce_transition_alternatives(suggestion.get("transition_alternatives")):
        if alternative.get("selected") is False:
            continue
        transition = _dict_or_none(alternative.get("transition"))
        grade = _dict_or_none((transition or {}).get("move_grade"))
        if grade is not None:
            return grade
    return None


def _suggestion_grade_key(suggestion: dict, grade: dict[str, Any] | None) -> str:
    if grade is None:
        return ""
    transition = _dict_or_none(suggestion.get("transition")) or {}
    parts = (
        _str_or_none(suggestion.get("track_id")),
        _str_or_none(transition.get("candidate_id")),
        _str_or_none(transition.get("from_track_id")),
        _str_or_none(transition.get("to_track_id")),
        _str_or_none(transition.get("from_section_id")),
        _str_or_none(transition.get("to_section_id")),
        _str_or_none(transition.get("cue_slot")),
        _str_or_none(grade.get("slug")),
    )
    return "|".join(part or "" for part in parts)


def _int_range(raw: Any, floor: int, ceiling: int, default: int) -> int:
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return default
    return max(floor, min(ceiling, value))


def _context_prepared_target(
    prepared_target_track_id: str | None,
    candidate_track_id: Any,
    *,
    strict: bool,
) -> str | None:
    target = _str_or_none(prepared_target_track_id)
    if target is None:
        return None
    if strict:
        return target
    return target if candidate_track_id == target else None


def _coerce_transition_alternatives(raw: Any) -> tuple[dict, ...]:
    if not isinstance(raw, (list, tuple)):
        return ()
    return tuple(dict(item) for item in raw if isinstance(item, dict))


def _matching_alternative(
    alternatives: tuple[dict, ...],
    *,
    candidate_id: str | None,
    track_id: str | None,
) -> dict | None:
    wanted_candidate_id = candidate_id.strip() if isinstance(candidate_id, str) else ""
    wanted_track_id = track_id.strip() if isinstance(track_id, str) else ""
    if not wanted_candidate_id and not wanted_track_id:
        return None
    for alternative in alternatives:
        if wanted_candidate_id and alternative.get("candidate_id") == wanted_candidate_id:
            return dict(alternative)
        if wanted_track_id and alternative.get("track_id") == wanted_track_id:
            return dict(alternative)
    return None


def _alternative_already_selected(
    alternatives: tuple[dict, ...],
    *,
    candidate_id: str | None,
    track_id: str | None,
) -> bool:
    if not alternatives:
        return False
    first = alternatives[0]
    wanted_candidate_id = candidate_id.strip() if isinstance(candidate_id, str) else ""
    wanted_track_id = track_id.strip() if isinstance(track_id, str) else ""
    return bool(
        (wanted_candidate_id and first.get("candidate_id") == wanted_candidate_id)
        or (wanted_track_id and first.get("track_id") == wanted_track_id)
    )


def _alternative_has_transition(alternatives: tuple[dict, ...], *, track_id: str) -> bool:
    return any(
        alternative.get("track_id") == track_id and isinstance(alternative.get("transition"), dict)
        for alternative in alternatives
    )


def _apply_winning_alternative(
    current: dict,
    alternatives: tuple[dict, ...],
    candidate_vectors_by_track_id: dict[str, Any],
    *,
    fallback_candidate_track_id: str,
    fallback_candidate_vector: Any | None,
) -> tuple[str, Any | None]:
    if not alternatives:
        return fallback_candidate_track_id, fallback_candidate_vector

    winner = alternatives[0]
    track_id = winner.get("track_id")
    if not isinstance(track_id, str) or not track_id:
        current["transition_alternatives"] = alternatives
        return fallback_candidate_track_id, fallback_candidate_vector

    for key in ("track_id", "title", "artist", "similarity", "why", "camelot", "bpm"):
        if key in winner:
            current[key] = winner[key]
    current["transition"] = winner.get("transition")
    current["transition_alternatives"] = alternatives

    vector = candidate_vectors_by_track_id.get(track_id)
    if vector is None and track_id == fallback_candidate_track_id:
        vector = fallback_candidate_vector
    return track_id, vector


def _strip_suggestion_timing(suggestion: dict, track_id: str) -> None:
    transition = _dict_or_none(suggestion.get("transition"))
    if transition is not None and transition.get("to_track_id") == track_id:
        suggestion["transition"] = _strip_transition_timing(transition)
    alternatives = []
    for alternative in _coerce_transition_alternatives(suggestion.get("transition_alternatives")):
        row = dict(alternative)
        if row.get("track_id") == track_id:
            row["transition"] = _strip_transition_timing(_dict_or_none(row.get("transition")))
        alternatives.append(row)
    if alternatives:
        suggestion["transition_alternatives"] = tuple(alternatives)


def _strip_transition_timing(transition: dict | None) -> dict | None:
    if transition is None:
        return None
    out = dict(transition)
    out["start_in_bars"] = None
    out["timing_basis"] = None
    out["timing_anchor"] = None
    out["source_anchor_s"] = None
    risk_flags = [str(flag) for flag in (out.get("risk_flags") or ())]
    if "timing_feedback_suppressed" not in risk_flags:
        risk_flags.append("timing_feedback_suppressed")
    out["risk_flags"] = risk_flags
    return out


def _section_context_payload(section: Any | None) -> dict[str, Any] | None:
    if section is None:
        return None
    return {
        "section_id": section.section_id,
        "track_id": section.track_id,
        "role": section.role,
        "source": section.source,
        "source_detail": section.source_detail,
        "confidence": section.confidence,
        "start_s": section.start_s,
        "end_s": section.end_s,
        "start_beat": section.start_beat,
        "end_beat": section.end_beat,
        "bar_count": section.bar_count,
        "bpm": section.bpm,
        "camelot": section.camelot,
        "cue_slot": section.cue_slot,
        "cue_source": section.cue_source,
        "cue_confidence": section.cue_confidence,
    }


def _float_or(raw: Any, default: float | None) -> float | None:
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _deck_controller_state(state: Any, deck: str | None) -> dict[str, Any]:
    if deck == "A":
        raw = getattr(state, "deck_a", None)
    elif deck == "B":
        raw = getattr(state, "deck_b", None)
    else:
        raw = None
    raw = raw if isinstance(raw, dict) else {}
    eq_low = _int_0_127(raw.get("eq_low"), 64)
    eq_mid = _int_0_127(raw.get("eq_mid"), 64)
    eq_hi = _int_0_127(raw.get("eq_hi"), 64)
    filter_value = _int_0_127(raw.get("filter"), 64)
    return {
        "deck": deck,
        "volume_raw": _int_0_127(raw.get("vol"), 0),
        "eq": {
            "low": _knob_tier(eq_low),
            "mid": _knob_tier(eq_mid),
            "hi": _knob_tier(eq_hi),
        },
        "filter": _knob_tier(filter_value),
        "low_cut": _knob_tier(eq_low) in {"killed", "deep_cut", "cut"},
    }


def _deck_label(deck: Any) -> str | None:
    if not isinstance(deck, str):
        return None
    deck = deck.strip().upper()
    return deck if deck in {"A", "B"} else None


def _source_loop_recent(state: Any, *, source_deck: str | None) -> bool:
    if source_deck not in {"A", "B"}:
        return False
    prefix = f"{source_deck}_loop_"
    for raw in getattr(state, "recent_moves", ()) or ():
        if not isinstance(raw, (list, tuple)) or len(raw) < 2:
            continue
        age = _float_or(raw[0], None)
        label = str(raw[1])
        if age is not None and age <= SOURCE_LOOP_RECENCY_S and label.startswith(prefix):
            return True
    return False


def _int_0_127(raw: Any, default: int) -> int:
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return default
    return max(0, min(127, value))


def _knob_tier(value: int) -> str:
    if value < 8:
        return "killed"
    if value < 30:
        return "deep_cut"
    if value < 55:
        return "cut"
    if value <= 73:
        return "flat"
    if value <= 100:
        return "boost"
    return "max"


def _xfader_factor(side: str, xfader: int) -> float:
    if side == "A":
        if xfader >= 112:
            return 0.0
        if xfader >= 80:
            return 0.3
        if xfader >= 48:
            return 0.7
        return 1.0
    if xfader < 16:
        return 0.0
    if xfader < 48:
        return 0.3
    if xfader <= 80:
        return 0.7
    return 1.0


def _dict_or_none(value: Any) -> dict | None:
    return dict(value) if isinstance(value, dict) else None


def _candidate_id_for_suggestion(suggestion: dict) -> str | None:
    transition = _dict_or_none(suggestion.get("transition"))
    if transition is not None:
        candidate_id = _str_or_none(transition.get("candidate_id"))
        if candidate_id is not None:
            return candidate_id
    alternatives = _coerce_transition_alternatives(suggestion.get("transition_alternatives"))
    if alternatives:
        candidate_id = _str_or_none(alternatives[0].get("candidate_id"))
        if candidate_id is not None:
            return candidate_id
    return None


def _transition_feedback_fields(transition: dict) -> dict[str, Any]:
    return {
        "role_from": _str_or_none(transition.get("from_role")),
        "role_to": _str_or_none(transition.get("to_role")),
        "from_section_id": _str_or_none(transition.get("from_section_id")),
        "to_section_id": _str_or_none(transition.get("to_section_id")),
        "cue_slot": _str_or_none(transition.get("cue_slot")),
        "cue_source": _str_or_none(transition.get("cue_source")),
        "cue_confidence": _float_or(transition.get("cue_confidence"), None),
        "score": _float_or(transition.get("score"), None),
        "confidence": _float_or(transition.get("confidence"), None),
        "risk_flags": [str(flag) for flag in (transition.get("risk_flags") or ())],
        "source_selection": _str_or_none(transition.get("source_selection")),
        "timing_basis": _str_or_none(transition.get("timing_basis")),
    }


def _str_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _feedback_token(value: str) -> str:
    token = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value)
    return token.strip("_") or "live_session"


def _feedback_key(value: str | None) -> str:
    if value is None:
        return ""
    return value.strip().lower().replace("-", "_").replace(" ", "_")


def _target_deck(source_deck: str | None, audible_deck: Any) -> str | None:
    """Return the opposite deck only when the audible side is explicit."""
    if source_deck not in {"A", "B"}:
        return None
    if audible_deck != source_deck:
        return None
    return "B" if source_deck == "A" else "A"


def _prepared_target_track_id(
    decks: Any,
    *,
    target_deck: str | None,
    source_track_id: str,
) -> str | None:
    if target_deck not in {"A", "B"} or not isinstance(decks, dict):
        return None
    target = decks.get(target_deck)
    if target is None:
        return None
    track_id = _str_or_none(getattr(target, "track_id", None))
    if track_id is None or track_id == source_track_id:
        return None
    confidence = _float_or(getattr(target, "confidence", 0.0), 0.0) or 0.0
    if _clamp01(confidence) < TARGET_DECK_TRACK_CONFIDENCE_FLOOR:
        return None
    return track_id


__all__ = [
    "FULL_COMPUTE_RETRY_S",
    "LIVE_REFRESH_INTERVAL_S",
    "LiveTimingHint",
    "ResolvedSeed",
    "SuggestionService",
    "resolve_controller_mix_context",
    "resolve_live_timing",
    "resolve_seed",
    "resolve_seed_context",
]
