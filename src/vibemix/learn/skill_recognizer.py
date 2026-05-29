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
``EvidenceRegistry`` / ``EventDetector`` are owned by concurrent sessions and
must not be runtime-imported here. The live wiring (DEFERRED KAAN-ACTION
``§EARNED-LIVE-MASTERED-VERIFY``) passes ``lambda s, k, t: registry.has(s, k, t,
tol=1.0)``; tests pass ``lambda s, k, t: True`` / ``... : False``. Type hints for
event/registry shapes are ``TYPE_CHECKING``-only (mirrors ``exemplar.py:40``) —
NO runtime ``state/`` import.

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
     deferred live caller (``§EARNED-LIVE-MASTERED-VERIFY``) MUST therefore pass
     that same value explicitly via ``recognize(..., event_t=t_session)`` — the
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

# HONEST-UNCREDITABLE in v11.0 (Finding #1, anti-slop):
#   - beatmatching: there is NO BEATMATCH/SYNC_ENGAGED event; "{deck}_sync_hit"
#     is a MIDI move BELOW the MIX_MOVE significance threshold, so no ``ev``
#     ever fires for it. On-beat-blend is not a detected/citable event.
#   - harmonic_mixing: the only harmonic events (KEY_CLASH /
#     TRANSITION_OPPORTUNITY) are default-OFF (harmonic_clash_enabled=False,
#     never flipped in production — gated behind the unshipped Plan 60-03
#     Kaan-ear veto), so in a real session today they NEVER fire.
# Both therefore have NO entry in EVENT_SKILL_MAP and NO MIX_MOVE move resolves
# to them — NO proxy-credit, NO new detector. They are capped at Competent and
# future-detector-gated (KAAN-ACTION §EARNED-MASTERY-THRESHOLD-TUNE). Silently
# proxy-mapping them to a wrong signal is the exact false-expertise anti-slop
# class this product guards — so we do not. Pinned by
# ``test_unsignalled_skills_never_auto_master``.
_HONEST_UNCREDITABLE_V11: tuple[str, ...] = ("beatmatching", "harmonic_mixing")


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
