# SPDX-License-Identifier: Apache-2.0
"""Skill-recognizer — the citation-gated event→skill credit spine (MAST-02/03).

Phase 103 (v11.0 "Earned"), Plan 02. This is the anti-slop heart of v11.0:
``recognize`` maps a detected live event to the skill(s) it demonstrates via a
reverse map keyed on the REAL ``state/event_detector.py`` event-type string
literals (MAST-02 — no new detectors), then grants Mastered credit ONLY when an
INJECTED citation predicate resolves true (MAST-03 — un-cited / fabricated →
ZERO credit). Credit is applied through :func:`skill_tree.record_live_demo`
(Plan 103-01), which itself enforces the MAST-01 Competent floor + the flip
math — the recognizer never re-implements either.

WHY the citation check is INJECTED (a ``Callable``, not a real
``EvidenceRegistry``): it keeps the engine offline-unit-testable and island-clean
(RESEARCH Pitfall 3). This module is owned by the learn island; the live
``EvidenceRegistry`` / ``EventDetector`` are owned by runtime code and must not be
runtime-imported here. The live wiring now lives in
``runtime/coach.py::_credit_live_skill_demo`` and passes
``lambda s, k, t: registry.has(s, k, t, tol=1.0)``; tests pass
``lambda s, k, t: True`` / ``... : False``. Type hints for event/registry shapes
are ``TYPE_CHECKING``-only (mirrors ``exemplar.py:40``) — NO runtime ``state/``
import.

The credit pipeline per event:

  1. Reverse map: ``event.type`` → candidate skill id(s). A ``MIX_MOVE`` resolves
     by inspecting ``event.extra["moves"]`` substrings (EQ-band → eq_mixing;
     play-toggle/xfader → deck_control; a single MIX_MOVE can credit BOTH —
     that is one event crediting two distinct skills, NOT a double-count). No
     match → return ``[]`` (no fill, ever).
  2. Citation gate (MAST-03): for each candidate, build the ``ev`` citation key
     ``(source="ev", key=event.type, t_target=<session-relative t>)`` — the exact
     tuple the EventDetector wrote at fire time (event_detector.py:509) — and
     skip the candidate if ``citation_check(...)`` is False. The session-relative
     ``t`` is NOT a field on the real ``Event`` (it carries only type/state/extra/
     priority); the EventDetector derives it as ``max(0.0, now -
     state.set_start_at)`` at fire time and writes it into the registry. The
     live caller MUST therefore pass that same value explicitly via
     ``recognize(..., event_t=t_session)`` — the
     ``_event_time`` attribute fallback exists ONLY for the synthetic test stubs.
  3. Dedup (MAST-04): by ``(event.type, round(t, 1))`` within the credit batch
     (a transient ``seen`` set, NOT persisted). The same fire handed twice
     credits once; distinct skills from one event each credit once.
  4. Apply: ``record_live_demo(progress, skill_id, now=now)`` — the MAST-01
     Competent gate + the MAST-04 threshold flip live there.

HONEST-UNCREDITABLE in v11.0 (Finding #1, anti-slop) — see EVENT_SKILL_MAP.

REQ-IDs: MAST-02 (reverse map over the existing taxonomy), MAST-03 (HEADLINE
citation gate; un-cited/fabricated → zero credit; Invariants #2 + #3 binding).
"""
from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from vibemix.learn.skill_tree import record_live_demo

if TYPE_CHECKING:  # type hints only — NEVER a runtime state/ import (Pitfall 3)
    # Documents the shapes the recognizer consumes (synthetic in tests, real in
    # the deferred live wiring). Type-only — these names are never bound at
    # runtime, so the engine has no runtime dependency on the state/ island.
    from vibemix.state.event import Event  # noqa: F401
    from vibemix.state.evidence_registry import EvidenceRegistry  # noqa: F401

# ---------------------------------------------------------------------------
# EVENT_SKILL_MAP (MAST-02, single source per GA2) — REAL event-type literals
# ---------------------------------------------------------------------------
# Keys are the exact ``Event.type`` strings fired in ``state/event_detector.py``
# (verified this session). Values are the skill ids the event demonstrates. NO
# phantom event constants; NO new detector. MIX_MOVE is handled separately
# below (it resolves by move-label substring, not a flat skill list).
EVENT_SKILL_MAP: dict[str, tuple[str, ...]] = {
    "LAYER_ARRIVAL": ("transitions",),  # a layer/element arrival = a transition
    "PHASE": ("phrasing_performance",),  # a phase change = phrase-locked play
    "PHRASE_BOUNDARY": ("phrasing_performance",),  # the genre-chain variant
}

# MIX_MOVE move-label substrings → the skill each significance class credits.
# These mirror the EventDetector significance set (event_detector.py:325-334)
# and the midi/state.py _record_move label vocabulary. EQ-band twists/kills
# demonstrate eq_mixing; play-toggle/xfader moves demonstrate deck_control. A
# single MIX_MOVE carrying both kinds credits BOTH skills (one event, two
# distinct skills — correct, not a double-count).
#
# ``_filter:`` (IN-01) is in the EventDetector MIX_MOVE significance set
# (event_detector.py:330) and midi/state.py:348-355 emits filter twists as
# "{deck}_filter: low→high (big twist)"; a filter sweep is an EQ-family move,
# so it credits eq_mixing too — without this, a filter-only mix move resolved
# to ``[]`` and silently under-credited a real, citable move.
_MIX_MOVE_EQ_SUBSTRINGS: tuple[str, ...] = ("_low:", "_mid:", "_hi:", "_filter:", "killed")
_MIX_MOVE_DECK_SUBSTRINGS: tuple[str, ...] = ("_play→", "xfader")

# HONEST-UNCREDITABLE in v11.0 (Finding #1, anti-slop).
# RETIRED from this tuple as their citable production events shipped:
#   - harmonic_mixing: the Judge's ``transition_judged`` event — a verdict with a
#     COMPATIBLE harmonic component (the DJ blended two trusted in-key tracks) is
#     resolved in ``_candidate_skills`` and credited under the MAST-03 gate.
# Still uncreditable:
#   - beatmatching: the owned-deck Judge and BEATMATCH_GRADED consumer are
#     future-ready, but no production loop calls the grader or emits the event.
#     The wall must not promise "3 more live demos" until that producer exists.
#     Synthetic BEATMATCH_GRADED tests can still exercise the branch; production
#     creditability is this list plus ``SkillSpec.live_creditable``.
_HONEST_UNCREDITABLE_V11: tuple[str, ...] = ("beatmatching",)


def _candidate_skills(event: Any) -> list[str]:
    """Resolve the skill id(s) a detected event demonstrates (MAST-02).

    No match → ``[]`` (no fill, ever). For ``MIX_MOVE`` the resolution inspects
    ``event.extra["moves"]`` move-label substrings; a garbage / missing
    ``extra`` degrades to ``{}`` (never raises — mirrors the engine's
    never-raises posture). Order is deterministic: eq_mixing before deck_control
    for a MIX_MOVE carrying both.
    """
    ev_type = getattr(event, "type", None)
    if not isinstance(ev_type, str):
        return []

    if ev_type == "MIX_MOVE":
        extra = getattr(event, "extra", None)
        moves = extra.get("moves", []) if isinstance(extra, dict) else []
        if not isinstance(moves, (list, tuple)):
            moves = []
        labels = [m for m in moves if isinstance(m, str)]
        candidates: list[str] = []
        if any(sub in label for label in labels for sub in _MIX_MOVE_EQ_SUBSTRINGS):
            candidates.append("eq_mixing")
        if any(
            sub in label for label in labels for sub in _MIX_MOVE_DECK_SUBSTRINGS
        ):
            candidates.append("deck_control")
        return candidates

    if ev_type == "transition_judged":
        # v11.0 the Vibe Judge — the clean citable production event that retires
        # harmonic_mixing from honest-uncreditable. The verdict's COMPATIBLE
        # harmonic component (> 0 = the Camelot prior; a clash is 0.0) is a real
        # harmonic-mixing demonstration: the DJ blended two trusted, in-key
        # tracks. A clash / absent component credits NOTHING (it proves the
        # opposite). beatmatching is deliberately NOT resolved here — the Judge
        # measures no tempo/phase signal yet, and proxying it onto bass-collision
        # is the exact false-expertise slop ``_HONEST_UNCREDITABLE_V11`` guards.
        extra = getattr(event, "extra", None)
        components = extra.get("components", {}) if isinstance(extra, dict) else {}
        if not isinstance(components, dict):
            return []
        harmonic = components.get("harmonic")
        if isinstance(harmonic, (int, float)) and not isinstance(harmonic, bool) and harmonic > 0.0:
            return ["harmonic_mixing"]
        return []

    if ev_type == "BEATMATCH_GRADED":
        # The owned-deck Beatmatch Judge consumer branch. It is future-ready, but
        # beatmatching stays honest-uncreditable until a production live loop can
        # actually emit this cited event. Because the learn module OWNS both decks,
        # the grade is MEASURED, not inferred.
        # A genuine demonstration is a LOCKED grade: tempo matched AND phase
        # locked AND not abstaining (== verdict "locked"). A trainwreck / drift /
        # tempo-off / abstain credits NOTHING — it proves the opposite, the exact
        # proxy-slop ``_HONEST_UNCREDITABLE_V11`` once guarded. Read the
        # load-bearing booleans (resilient to verdict-string drift); the payload
        # is ``beatmatch_judge.grade_to_event_extra``.
        extra = getattr(event, "extra", None)
        if not isinstance(extra, dict):
            return []
        if extra.get("abstain"):
            return []
        if bool(extra.get("tempo_matched")) and bool(extra.get("phase_locked")):
            return ["beatmatching"]
        return []

    return list(EVENT_SKILL_MAP.get(ev_type, ()))


def _event_time(event: Any) -> float:
    """SYNTHETIC-STUB FALLBACK for the ``ev`` citation t_target — NOT the live path.

    The REAL ``state/event.py::Event`` dataclass has exactly four fields —
    ``type``, ``state``, ``extra``, ``priority`` — and NO session-relative time
    attribute. The session-relative ``t_session`` the registry was written with
    is computed by the EventDetector at fire time as
    ``max(0.0, now - state.set_start_at)`` (event_detector.py:508-509); it lives
    only in the registry, never on the ``Event`` object. So a real ``Event`` has
    nothing for this function to read and it returns ``0.0``.

    The LIVE caller therefore MUST pass the registry time explicitly via
    ``recognize(..., event_t=t_session)``; this attribute read is the fallback
    ONLY for the synthetic test stubs (``SimpleNamespace(..., t_session=t)``).
    Reading ``0.0`` here for a real ``Event`` would deny credit for the whole set
    after t≈1s (it would land within ±tol of ``set_start_at`` only for the first
    ~1s) — which is exactly why ``recognize`` prefers an explicit ``event_t``."""
    t = getattr(event, "t_session", None)
    if isinstance(t, (int, float)):
        return float(t)
    return 0.0


def recognize(
    event: Any,
    *,
    citation_check: Callable[[str, str, float], bool],
    progress: Any,
    now: str,
    event_t: float | None = None,
    _seen: set[tuple[str, float]] | None = None,
) -> list[str]:
    """Credit the skill(s) a CITED live event demonstrates; return their ids.

    Pure-logic, offline-testable. The ``citation_check`` predicate is the SOLE
    arbiter of credit (MAST-03): a candidate skill is credited ONLY when
    ``citation_check(source="ev", key=event.type, t_target=<t>)`` returns
    True. An un-cited / fabricated event yields ``[]`` and moves no bar.

    LIVE-WIRING CONTRACT (``§EARNED-LIVE-MASTERED-VERIFY`` KAAN-ACTION): the real
    ``state/event.py::Event`` carries NO session-relative time (only type/state/
    extra/priority). The EventDetector wrote the registry with
    ``t_session = max(0.0, now - state.set_start_at)`` (event_detector.py:
    508-509), so the live caller MUST pass that SAME value as ``event_t`` —
    otherwise ``_event_time`` falls back to ``0.0`` and the ``has(..., tol=1.0)``
    check would deny credit for the whole set past t≈1s. Concretely::

        t_session = max(0.0, now_monotonic - state.set_start_at)
        recognize(event, citation_check=lambda s, k, t: reg.has(s, k, t, tol=1.0),
                  progress=progress, now=iso_now, event_t=t_session)

    Args:
        event: A detected event with ``.type`` (str) + optional ``.extra``
            (dict with ``"moves"`` for MIX_MOVE). A synthetic object suffices —
            NO MusicState required. The real ``Event`` has no time attribute, so
            the session-relative time comes from ``event_t`` (below), not the
            object.
        citation_check: ``(source, key, t_target) -> bool`` wrapping
            ``EvidenceRegistry.has`` in live wiring (injected — the engine never
            imports the registry for runtime use).
        progress: The ``LearnProgress`` whose ``skills`` live-portion is
            credited via :func:`record_live_demo` (which enforces the MAST-01
            Competent gate + the MAST-04 flip).
        now: Injected ISO timestamp stamped as ``first_mastered_at`` on the
            Mastered transition (determinism — no clock here).
        event_t: The session-relative time the registry was written with
            (``max(0.0, now - state.set_start_at)``). The live caller MUST
            supply this — it is the citation ``t_target`` and the dedup time.
            When ``None`` (synthetic test stubs only) it falls back to
            ``_event_time(event)``, which reads ``event.t_session`` off the stub.
        _seen: A transient per-batch identity set ``(type, round(t,1))`` for
            dedup across calls in one batch (MAST-04 / Pitfall 4). NOT persisted.
            Defaults to a fresh per-call set.

    Returns:
        The list of skill ids actually credited this call (may be empty). A
        single event crediting multiple distinct skills returns each once.
    """
    candidates = _candidate_skills(event)
    if not candidates:
        return []  # unmapped event → no fill, ever

    ev_type = getattr(event, "type", "")
    # The session-relative t is supplied by the live caller (the real Event has
    # no such field); the attribute read is the synthetic-stub fallback only.
    t = event_t if event_t is not None else _event_time(event)

    # Dedup identity: the (type, rounded-time) pair the EventDetector itself
    # uses as the registry key+timestamp (Event has no stable id field). Guards
    # the SAME fire handed to the recognizer twice; distinct skills from one
    # event are each credited once below.
    identity = (ev_type, round(t, 1))
    seen = _seen if _seen is not None else set()
    if identity in seen:
        return []  # this exact fire already credited in the batch
    seen.add(identity)

    # MAST-03 citation gate — the SOLE arbiter. The ``ev`` citation key is the
    # exact tuple the EventDetector wrote at fire time. Un-cited → zero credit.
    if not citation_check("ev", ev_type, t):
        return []

    credited: list[str] = []
    for skill_id in candidates:
        # record_live_demo enforces the MAST-01 Competent gate + the MAST-04
        # threshold flip — a not-Competent skill is a NO-OP there, so the
        # recognizer never over-credits a locked skill. We report a skill as
        # credited only when its count actually advanced.
        before = _live_count(progress, skill_id)
        record_live_demo(progress, skill_id, now=now)
        if _live_count(progress, skill_id) > before:
            credited.append(skill_id)
    return credited


def _live_count(progress: Any, skill_id: str) -> int:
    """The current ``live_proof_count`` for a skill, never-raises on garbage."""
    skills = getattr(progress, "skills", None)
    if not isinstance(skills, dict):
        return 0
    block = skills.get(skill_id, {})
    if not isinstance(block, dict):
        return 0
    try:
        return int(block.get("live_proof_count", 0) or 0)
    except (TypeError, ValueError):
        return 0
