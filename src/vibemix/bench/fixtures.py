# SPDX-License-Identifier: Apache-2.0
"""Bench fixtures — REAL MusicState + a populated EvidenceRegistry snapshot.

``fixture_state_for(contexting, grounding) -> (MusicState, snapshot)`` builds a
REAL :class:`~vibemix.state.music_state.MusicState` (NOT ad-hoc dicts) so the
coach's additive ``evidence_line`` gating (it gates trajectory/genre branches by
field presence) exercises the product's actual grounding paths
(81-PATTERNS "bench/fixtures.py").

The ``snapshot`` is built via the REAL ``EvidenceRegistry`` so its shape is the
EXACT one ``CitationLinter.check`` consumes. It carries ``aud/bpm@0.0`` +
``aud/sub@0.0`` — matching the offline ``_FakeClient``'s canned cited line
(``[aud:bpm@0.0]``) so a grounded cell's groundedness scorer (BENCH-02) resolves
the citation; a fabricated atom absent from the snapshot scores 0. This mirrors
the ``tests/bench/conftest.py`` ``_grounded_snapshot`` so the offline gate and
the harness ground against the SAME facts (no fixture churn).

- ``contexting == "snapshot"`` → a cold audible MusicState (no trajectory fields).
- ``contexting == "trajectory"`` → the same with the multi-scale PERCEIVE-02
  fields populated, so the coach's trajectory branch fires.
- ``grounding`` ending in ``+genre`` → the detected_genre/confidence are set;
  otherwise they stay at the honest-unknown defaults.
"""

from __future__ import annotations

from vibemix.state.evidence_registry import EvidenceRegistry
from vibemix.state.music_state import MusicState


def _grounded_snapshot() -> dict[str, dict[str, tuple[float, ...]]]:
    """A populated snapshot carrying ``aud/bpm@0.0`` + ``aud/sub@0.0``.

    Built via the REAL registry (not a hand-rolled dict) so the shape is the
    exact one the linter consumes. Matches ``conftest._grounded_snapshot`` so
    the harness grounds against the same facts the offline gate validates.
    """
    reg = EvidenceRegistry()
    reg.write("aud", "bpm", 0.0)
    reg.write("aud", "sub", 0.0)
    return reg.snapshot()


def fixture_state_for(
    contexting: str,
    grounding: str,
) -> tuple[MusicState, dict[str, dict[str, tuple[float, ...]]]]:
    """Return ``(MusicState, snapshot)`` for the given contexting × grounding axes.

    Args:
        contexting: ``"snapshot"`` (cold, no trajectory fields) or
            ``"trajectory"`` (the multi-scale PERCEIVE-02 fields populated).
        grounding: the cell's grounding axis value; a ``+genre`` suffix
            populates the detected-genre fields.

    Returns:
        A real audible ``MusicState`` + a grounded ``EvidenceRegistry`` snapshot
        carrying ``aud/bpm@0.0`` (so the offline canned cited line resolves).
    """
    with_genre = "+genre" in grounding
    detected_genre = "hardtechno" if with_genre else "unknown"
    genre_confidence = 0.82 if with_genre else 0.0

    if contexting == "trajectory":
        state = MusicState(
            audible=True,
            rms=0.32,
            bands={"sub": 0.41, "low": 0.30, "mid": 0.18, "high": 0.11},
            onset_density=0.55,
            bpm=150.0,
            phase="build",
            detected_genre=detected_genre,
            genre_confidence=genre_confidence,
            trajectory_narrative=(
                "build->drop->groove; building; last move: bass-swap 20s ago"
            ),
            phase_history=[(10.0, "groove", "build"), (30.0, "build", "drop")],
            long_arc=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6],
        )
    else:
        # The cold ``snapshot`` contexting — no trajectory fields, so the
        # coach's additive trajectory branch stays OFF (byte-identical cold path).
        state = MusicState(
            audible=True,
            rms=0.32,
            bands={"sub": 0.41, "low": 0.30, "mid": 0.18, "high": 0.11},
            onset_density=0.55,
            bpm=150.0,
            phase="groove",
            detected_genre=detected_genre,
            genre_confidence=genre_confidence,
        )

    return state, _grounded_snapshot()
