# SPDX-License-Identifier: Apache-2.0
"""Phase 77 Plan 01 (Wave 0) — WIRE-02 + WIRE-03 regression PINS.

WIRE-02 (shipped ``ccf4930``) and WIRE-03 (shipped ``a9979b8``) are already
TRUE today. This file is a PIN — NOT new functionality. It locks the two
shipped wires against silent regression so a future refactor that drops the
genre-chain task surfacing or the detected-genre evidence field fails LOUDLY
here.

WIRE-02 — the 8 genre-chain detectors surface their MEASURED payload to the
prompt (``AICoach.task_for_event`` has a dedicated branch per type) instead of
the old "React naturally." fallthrough that discarded the measurement.

WIRE-03 — ``AICoach.evidence_line`` emits a gated ``genre=<name>`` field when
``MusicState.detected_genre`` is set ABOVE the confidence floor (0.5), and
OMITS it (no ``genre=unknown`` spam) below floor / unset.

No re-implementation: assertions only against the existing public surface.
No genai.Client, no API key.

Mechanism located this session:
  * WIRE-02 — ``src/vibemix/state/prompt_builder.py::AICoach.task_for_event`` branches
    at lines 598-694 (ACID_LINE_ENTRY / KICK_SWAP / SUB_LAYER_ARRIVAL /
    KICK_DENSITY_SHIFT / DISTORTION_CLIMB / BREAKDOWN_KICK_KILL /
    REENTRY_KICK_LAND / PHRASE_BOUNDARY); fallthrough "React naturally." at :695.
  * WIRE-03 — ``src/vibemix/state/prompt_builder.py::AICoach.evidence_line`` gate at
    :334 (``detected_genre != "unknown" and genre_confidence >= 0.5`` →
    ``e.append(f"genre={state.detected_genre}")``).
"""

from __future__ import annotations

import pytest

from vibemix.state import AICoach, Event, MusicState

# The 8 genre-chain detector event types, each with a representative measured
# payload (mirrors the ev.extra keys read by each task_for_event branch).
_GENRE_CHAIN_EVENTS: dict[str, dict] = {
    "ACID_LINE_ENTRY": {"formant_hz": 1200, "resonance_q": 8.0},
    "KICK_SWAP": {"prev_centroid_hz": 60, "new_centroid_hz": 90, "delta_hz": 30},
    "SUB_LAYER_ARRIVAL": {"prev_sub": 0.1, "new_sub": 0.4, "sub_jump": 0.3},
    "KICK_DENSITY_SHIFT": {"prev_density": 4, "new_density": 8, "delta": 4},
    "DISTORTION_CLIMB": {"distortion_db": 6.0, "chain_position": 2},
    "BREAKDOWN_KICK_KILL": {"sub_drop": 0.5, "new_sub": 0.05},
    "REENTRY_KICK_LAND": {"kill_age_s": 12, "sub_at_reentry": 0.4},
    "PHRASE_BOUNDARY": {"phrase_length_bars": 16, "bpm": 132},
}

_FALLBACK = "React naturally."


# ---------------------------------------------------------------------------
# WIRE-02 pin — genre-chain detectors reach the prompt (not the fallthrough)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("ev_type,extra", sorted(_GENRE_CHAIN_EVENTS.items()))
def test_wire02_genre_chain_event_yields_real_task(
    ev_type: str, extra: dict
) -> None:
    """Each genre-chain event produces a substantive task, NOT the fallback.

    Pin: if a refactor drops a branch, that event falls back to
    "React naturally." and the deepest perception in the system silently stops
    reaching Gemini — this assertion catches that regression.
    """
    ev = Event(ev_type, MusicState(), extra)
    task = AICoach.task_for_event(ev)
    assert task != _FALLBACK, (
        f"{ev_type} fell through to the generic fallback — its measured "
        "evidence is no longer reaching the prompt (WIRE-02 regressed)"
    )
    assert task.strip(), f"{ev_type} produced an empty task"


def test_wire02_all_eight_detectors_are_wired() -> None:
    """Exactly the 8 genre-chain detector types have a dedicated task branch."""
    assert len(_GENRE_CHAIN_EVENTS) == 8
    for ev_type, extra in _GENRE_CHAIN_EVENTS.items():
        task = AICoach.task_for_event(Event(ev_type, MusicState(), extra))
        assert task != _FALLBACK, f"{ev_type} not wired"


def test_wire02_measured_payload_surfaces_in_task() -> None:
    """A measured number from ev.extra is narrated in the task string.

    The genre-chain branches are narrate-style (the measurements are not
    registry-citable tokens — see coach.py:594), so the pin proves the SPECIFIC
    measured fact reaches the model rather than being discarded.
    """
    ev = Event(
        "KICK_SWAP",
        MusicState(),
        {"prev_centroid_hz": 60, "new_centroid_hz": 90, "delta_hz": 30},
    )
    task = AICoach.task_for_event(ev)
    # The measured centroid move is narrated (grounded only in the numbers).
    assert "60" in task and "90" in task, (
        "the measured kick-centroid payload no longer reaches the prompt"
    )


def test_wire02_unknown_event_still_falls_back() -> None:
    """An unrecognised event type STILL returns the generic fallback (no overreach)."""
    ev = Event("TOTALLY_UNKNOWN_EVENT", MusicState(), {})
    assert AICoach.task_for_event(ev) == _FALLBACK


# ---------------------------------------------------------------------------
# WIRE-03 pin — detected_genre surfaces in evidence_line, confidence-gated
# ---------------------------------------------------------------------------


def _audible_state(genre: str, conf: float) -> MusicState:
    s = MusicState()
    s.audible = True
    s.audible_deck = "A"
    s.detected_genre = genre
    s.genre_confidence = conf
    return s


def test_wire03_genre_present_above_floor() -> None:
    """detected_genre above the 0.5 floor surfaces as genre=<name> in evidence."""
    out = AICoach.evidence_line(_audible_state("hardtechno", 0.8))
    assert "genre=hardtechno" in out


def test_wire03_genre_omitted_below_floor() -> None:
    """Below the confidence floor → the genre field is OMITTED (no spam)."""
    out = AICoach.evidence_line(_audible_state("hardtechno", 0.4))
    assert "genre=" not in out, (
        "a low-confidence genre leaked into the prompt (anti-hallucination "
        "floor regressed)"
    )


def test_wire03_no_genre_unknown_spam() -> None:
    """An unset/unknown genre never emits genre=unknown (trust-the-audio)."""
    s = MusicState()
    s.audible = True
    s.audible_deck = "A"
    # default detected_genre == "unknown", genre_confidence == 0.0
    out = AICoach.evidence_line(s)
    assert "genre=unknown" not in out
    assert "genre=" not in out


def test_wire03_floor_is_inclusive_boundary() -> None:
    """Exactly at the 0.5 floor the genre IS surfaced (>= gate, shipped behavior)."""
    out = AICoach.evidence_line(_audible_state("psytrance", 0.5))
    assert "genre=psytrance" in out
