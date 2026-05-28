# SPDX-License-Identifier: Apache-2.0
"""Phase 96 Plan 01 — Course 3 proactive tutor lens confidence gate.

Pins the runtime conditional for Invariant #3 (trust the audio):
forward-looking count-in language is permitted ONLY when all three
confidence floors hold — ``bpm_confidence >= 0.8``,
``phrase_position_confidence >= 0.7``, ``next_phrase_at is not None``.
Any floor fails → downgrade to retrospective-only narration.

The marker is GATED by ``state.session_active`` so the v8.0 byte-
identical evidence_line golden stays green on the default cold path
(session_active=False → no marker emitted).

REQ-ID: CURR-3.07 + Invariant #3 binding.
"""
from __future__ import annotations

import dataclasses

from vibemix.state.coach import (
    AICoach,
    _COUNT_IN_BPM_FLOOR,
    _COUNT_IN_PHRASE_FLOOR,
    _count_in_eligible,
)
from vibemix.state.music_state import MusicState


def test_constants_locked_at_orchestrator_brief_thresholds() -> None:
    """``_COUNT_IN_BPM_FLOOR`` + ``_COUNT_IN_PHRASE_FLOOR`` pinned at
    0.8 / 0.7 per CONTEXT.md §Decisions §order-of-operations step 3."""
    assert _COUNT_IN_BPM_FLOOR == 0.8
    assert _COUNT_IN_PHRASE_FLOOR == 0.7


def test_musicstate_default_extension_safe() -> None:
    """New fields default to off / cold so v8.0 golden cold-state holds."""
    s = MusicState()
    assert s.session_active is False
    assert s.phrase_position_confidence == 0.0
    assert s.next_phrase_at is None


def test_evidence_line_cold_state_emits_no_lens_marker() -> None:
    """session_active=False (default) → NO ``lens=…`` token in the line.

    Preserves the v8.0 byte-identical evidence_line golden for every
    existing caller (the cold-path default).
    """
    s = MusicState()
    line = AICoach.evidence_line(s)
    assert "lens=" not in line, f"cold-state regression: {line!r}"


def test_lens_off_with_high_confidence_still_emits_no_marker() -> None:
    """Confidence high but session_active=False still emits no marker —
    the lens is off; cold path stays clean."""
    s = dataclasses.replace(
        MusicState(),
        bpm_confidence=0.95,
        phrase_position_confidence=0.9,
        next_phrase_at=42.5,
        session_active=False,
    )
    line = AICoach.evidence_line(s)
    assert "lens=" not in line


def test_downgrade_when_bpm_confidence_below_floor() -> None:
    s = dataclasses.replace(
        MusicState(),
        session_active=True,
        bpm_confidence=0.5,  # below floor
        phrase_position_confidence=0.9,
        next_phrase_at=42.5,
    )
    line = AICoach.evidence_line(s)
    assert "lens=retrospective_only" in line, (
        f"downgrade missing: {line!r}"
    )
    assert "lens=count_in_eligible" not in line


def test_downgrade_when_phrase_confidence_below_floor() -> None:
    s = dataclasses.replace(
        MusicState(),
        session_active=True,
        bpm_confidence=0.95,
        phrase_position_confidence=0.5,  # below floor
        next_phrase_at=42.5,
    )
    line = AICoach.evidence_line(s)
    assert "lens=retrospective_only" in line


def test_downgrade_when_next_phrase_at_is_none() -> None:
    s = dataclasses.replace(
        MusicState(),
        session_active=True,
        bpm_confidence=0.95,
        phrase_position_confidence=0.9,
        next_phrase_at=None,  # cold phrase lock
    )
    line = AICoach.evidence_line(s)
    assert "lens=retrospective_only" in line


def test_count_in_eligible_when_all_floors_pass() -> None:
    s = dataclasses.replace(
        MusicState(),
        session_active=True,
        bpm_confidence=0.95,
        phrase_position_confidence=0.9,
        next_phrase_at=42.5,
    )
    line = AICoach.evidence_line(s)
    assert "lens=count_in_eligible[next@42.5]" in line, (
        f"forward-looking marker shape wrong: {line!r}"
    )


def test_count_in_at_exact_floor_passes() -> None:
    """``>= floor`` (not strictly greater) — locked semantic per
    CONTEXT.md §Decisions §order-of-operations step 3."""
    s = dataclasses.replace(
        MusicState(),
        session_active=True,
        bpm_confidence=_COUNT_IN_BPM_FLOOR,  # exactly at floor
        phrase_position_confidence=_COUNT_IN_PHRASE_FLOOR,
        next_phrase_at=10.0,
    )
    assert _count_in_eligible(s) is True


def test_count_in_just_below_floor_downgrades() -> None:
    """Numeric edge — values just below floor downgrade."""
    s = dataclasses.replace(
        MusicState(),
        session_active=True,
        bpm_confidence=_COUNT_IN_BPM_FLOOR - 0.01,
        phrase_position_confidence=0.9,
        next_phrase_at=10.0,
    )
    assert _count_in_eligible(s) is False
