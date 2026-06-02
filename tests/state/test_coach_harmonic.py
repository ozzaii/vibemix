# SPDX-License-Identifier: Apache-2.0
"""Phase 60 Plan 04 — the cited, narrate-only harmonic coach fragments.

These tests pin the contract for the two REAL harmonic ``task_for_event`` arms
that replace the Phase-59 stubs (coach.py KEY_CLASH + TRANSITION_OPPORTUNITY):

  - KEY_CLASH (HARMONIC-01): the fragment hands the LLM a system-decided
    verdict + a CITE-both-keys instruction + a hard "do NOT compute intervals"
    rule. The LLM narrates the clash the code already proved; it never decides
    or computes anything. The semitone count is pre-computed in ``ev.extra``.
  - TRANSITION_OPPORTUNITY (HARMONIC-04): the fragment is strictly
    retrospective / past-tense — no present-tense imperative verbs — because
    LLM+TTS latency makes a live "bring the fader down now" arrive 5-10s late
    (Pitfall 3).

The anti-slop guarantee is structural: an uncited / fabricated ``[key:...]``
the registry never observed strips the WHOLE turn via the existence-only
CitationLinter (shipped Phase 59 — no change). The last test proves that.

Neither type is in ACK_ELIGIBLE_EVENTS — they are substantive full-payload
events, so ``build_prompt(diet=True)`` must raise for them.
"""

from __future__ import annotations

import pytest

from vibemix.coach.citation_linter import CitationLinter
from vibemix.state.event import Event
from vibemix.state.music_state import MusicState
from vibemix.state.prompt_builder import ACK_ELIGIBLE_EVENTS, AICoach


def _clash_event() -> Event:
    """A KEY_CLASH Event carrying the exact Plan-02 detector ``extra`` shape:
    deck A = 8A, deck B = 3A, 1 semitone apart (a true 5-hour-distance clash)."""
    return Event(
        "KEY_CLASH",
        MusicState(),
        extra={
            "a_side": "A",
            "a_camelot": "8A",
            "b_side": "B",
            "b_camelot": "3A",
            "semitones": 1,
        },
    )


def _transition_event() -> Event:
    """A TRANSITION_OPPORTUNITY Event carrying the both-decks resolved keys
    the Plan-02 detector writes (a retrospective blend note)."""
    return Event(
        "TRANSITION_OPPORTUNITY",
        MusicState(),
        extra={
            "a_side": "A",
            "a_camelot": "8A",
            "b_side": "B",
            "b_camelot": "8A",
            "clash": False,
        },
    )


def _registry(*entries: tuple[str, str, tuple[float, ...] | None]) -> dict:
    """Mirror tests/coach/test_citation_linter.py::_registry — build a frozen
    snapshot from (source, key, times) triples. existence-only sources pass
    times=None → stored as an empty-tuple marker."""
    out: dict[str, dict[str, tuple[float, ...]]] = {}
    for source, key, times in entries:
        out.setdefault(source, {})[key] = tuple(times) if times is not None else ()
    return out


# ---------------------------------------------------------------------------
# KEY_CLASH — cited narration (HARMONIC-01)
# ---------------------------------------------------------------------------


def test_clash_fragment_is_cited_narration() -> None:
    """The clash fragment (a) cites BOTH decks' keys exactly, (b) states the
    verdict is system-decided (not the LLM's), (c) forbids interval/key math,
    (d) carries the 'single space to stay silent' escape."""
    frag = AICoach.task_for_event(_clash_event())

    # (a) both keys cited, exact bracket form
    assert "[key:A:8A]" in frag
    assert "[key:B:3A]" in frag

    # (b) the verdict is the SYSTEM's, not the LLM's
    low = frag.lower()
    assert "you do not decide this" in low or "you do not decide" in low

    # (c) the LLM must NOT compute intervals / invent a key
    assert "do not invent a key" in low or "do not invent" in low
    assert "compute interval" in low or "compute" in low

    # the pre-computed semitone count is narrated, not derived
    assert "1 semitone" in low

    # (d) the silence escape
    assert "single space" in low


def test_clash_fragment_no_key_math() -> None:
    """The fragment hands a DECIDED verdict — it never asks the model to
    calculate / figure out / determine whether the keys clash."""
    frag = AICoach.task_for_event(_clash_event()).lower()
    for verb in ("calculate", "figure out", "determine if", "work out whether"):
        assert verb not in frag, f"clash fragment must not ask the LLM to {verb!r}"


def test_clash_fragment_handles_none_semitones() -> None:
    """Cross-letter pairs carry semitones=None — the fragment must say
    'clashing' without interpolating a None into the text."""
    ev = Event(
        "KEY_CLASH",
        MusicState(),
        extra={
            "a_side": "A",
            "a_camelot": "8A",
            "b_side": "B",
            "b_camelot": "3B",
            "semitones": None,
        },
    )
    frag = AICoach.task_for_event(ev)
    assert "None" not in frag
    assert "[key:A:8A]" in frag
    assert "[key:B:3B]" in frag


def test_uncited_fabricated_key_strips_turn() -> None:
    """A reply citing a [key:B:12B] the registry NEVER observed is stripped by
    the existence-only CitationLinter (the structural anti-slop guarantee).

    The registry only saw deck A = 8A; the model fabricates deck B = 12B."""
    linter = CitationLinter()
    snap = _registry(("key", "A:8A", None))  # only A:8A was ever observed
    reply = "those keys are fighting [key:A:8A] [key:B:12B]"
    result = linter.check(reply, snap, mode="live")
    assert result.valid is False
    assert ("key", "B:12B") in result.missing


# ---------------------------------------------------------------------------
# TRANSITION_OPPORTUNITY — retrospective only (HARMONIC-04)
# ---------------------------------------------------------------------------


def test_transition_is_retrospective() -> None:
    """The transition fragment is past-tense / retrospective and contains NO
    present-tense imperative verbs — those arrive 5-10s late (Pitfall 3)."""
    frag = AICoach.task_for_event(_transition_event()).lower()

    # past-tense framing
    assert "just blended" in frag or "you just" in frag

    # NO present-tense imperatives anywhere in the fragment
    for imperative in ("bring the", "pull the", "drop it now", "cut it now"):
        assert imperative not in frag, f"transition fragment leaked imperative {imperative!r}"

    # the silence escape
    assert "single space" in frag


def test_transition_cites_both_keys() -> None:
    """The retrospective note cites both decks' resolved keys (the cite is
    what the linter grounds against)."""
    frag = AICoach.task_for_event(_transition_event())
    assert "[key:A:8A]" in frag
    assert "[key:B:8A]" in frag


# ---------------------------------------------------------------------------
# Diet / ack-eligibility — both types stay OUT of the diet path
# ---------------------------------------------------------------------------


def test_both_types_not_ack_eligible() -> None:
    """KEY_CLASH and TRANSITION_OPPORTUNITY are NOT ack-eligible — they are
    substantive full-payload events. ``build_prompt(diet=True)`` must raise."""
    assert "KEY_CLASH" not in ACK_ELIGIBLE_EVENTS
    assert "TRANSITION_OPPORTUNITY" not in ACK_ELIGIBLE_EVENTS

    with pytest.raises(ValueError):
        AICoach.build_prompt(_clash_event(), diet=True)
    with pytest.raises(ValueError):
        AICoach.build_prompt(_transition_event(), diet=True)
