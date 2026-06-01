# SPDX-License-Identifier: Apache-2.0
"""One Mind S6 — the unified track→track relation vocabulary.

vibemix asks "how do these two tracks relate?" in four different places that
had drifted apart:

  * ``library/next_suggestion.py`` (the pill) — centered cosine + a *binary*
    Camelot/±BPM filter, energy ignored.
  * ``intel/transition_scorer.py`` (the set-builder) — *continuous* semantic +
    harmonic + bpm + energy weighted composite (the richest).
  * ``library/grounding.py`` (live "what's playing") — *raw* cosine, top-1.
  * ``library/similar.py`` (user-asked) — centered cosine, harmonic/energy
    ignored.

This module is the single shared vocabulary for the TRACK-LEVEL dimensions
(semantic similarity, Camelot harmony, tempo). It REUSES the proven, tested
continuous scorers from ``intel.transition_scorer`` (``harmonic_score`` /
``bpm_score``) so there is exactly one source of truth for those formulas — no
new key/tempo math is invented here. Section-aware dimensions (energy shape,
role, phrase alignment, cue operability) stay in ``transition_scorer`` where
they belong; they are NOT track properties.

A :class:`TrackRelation` is pure DATA (scores + flags). It carries NO policy:
each consumer applies its own threshold/filter/aggregation. The convenience
properties (``harmonic_compatible`` etc.) and :meth:`why` exist so consumers
agree on the *words*, not so they agree on the *decision*.

:meth:`TrackRelation.why` renders the human phrase ("8A→9A, +5 BPM") that the
co-host can eventually voice ("your loaded track pairs great — 8A→9A, +5 BPM").
That live voicing is a follow-up (it is a live-reaction musical claim → it must
ride the Invariant #2/#3 claim-validation path + a Kaan ear-pass); this module
ships the deterministic substrate, fully tested, ahead of that wiring.

Import-light by design (mirrors the intel/ contract): no model client, no audio
capture, no Tauri, no filesystem. Deterministic — same inputs always yield the
same relation, so it is safe across the Mac (sqlite-vec) / Windows (numpy)
cosine parity boundary.
"""

from __future__ import annotations

from dataclasses import dataclass

# Single source of truth for the harmonic + tempo formulas (Plan 86 set-builder
# math, already unit-tested in tests/intel/test_transition_scorer.py). Reusing
# them here — rather than reimplementing — is the whole point of S6: one place
# decides how a key pair or a tempo pair grades.
from vibemix.intel.transition_scorer import bpm_folded_delta_pct as _bpm_folded_delta_pct
from vibemix.intel.transition_scorer import bpm_score as _bpm_score
from vibemix.intel.transition_scorer import harmonic_score as _harmonic_score

# Camelot-mixable floor: harmonic_score grades same-key 1.0, relative 0.92,
# Camelot-neighbour 0.88, ±2 0.78, energy-boost cross-letter 0.72, drift 0.42,
# clash 0.12. "Compatible" (a blend a working DJ would reach for) is the
# neighbour/relative/±2/energy-boost band or better — i.e. >= 0.72 and no clash.
HARMONIC_COMPATIBLE_FLOOR = 0.72


@dataclass(frozen=True, slots=True)
class TrackRelation:
    """The track-level relation between a source and a destination track.

    ``cosine`` is whatever the caller computed (raw or mean-centered — the
    field records the value, not the centering policy). The harmonic + tempo
    fields are the continuous grades from ``intel.transition_scorer``.
    """

    src_track_id: str
    dst_track_id: str
    cosine: float

    camelot_src: str | None
    camelot_dst: str | None
    harmonic: float
    harmonic_flags: tuple[str, ...]

    bpm_src: float | None
    bpm_dst: float | None
    bpm_delta_pct: float | None  # nearest 0.5x/1x/2x BPM delta; None when unknown
    tempo: float
    tempo_flags: tuple[str, ...]

    @property
    def harmonic_clash(self) -> bool:
        """True iff the two keys are an outright Camelot clash."""
        return "harmonic_clash" in self.harmonic_flags

    @property
    def harmonic_compatible(self) -> bool:
        """Camelot-mixable: neighbour/relative/±2/energy-boost or better, no
        clash. Convenience only — consumers may use ``harmonic`` directly."""
        return not self.harmonic_clash and self.harmonic >= HARMONIC_COMPATIBLE_FLOOR

    @property
    def bpm_delta_signed(self) -> float | None:
        """Signed BPM difference (dst - src), or None when either is unknown."""
        if self.bpm_src is None or self.bpm_dst is None:
            return None
        return self.bpm_dst - self.bpm_src

    def why(self) -> str:
        """Render the human transition phrase, e.g. ``"8A→9A, +5 BPM"``.

        The substrate for the co-host's future grounded transition line. Omits
        any dimension whose metadata is unknown; returns ``""`` when nothing is
        knowable. Pure prose — never an audio DSL tag, never a citation atom.
        """
        parts: list[str] = []
        if self.camelot_src and self.camelot_dst:
            arrow = (
                self.camelot_src
                if self.camelot_src == self.camelot_dst
                else f"{self.camelot_src}→{self.camelot_dst}"
            )
            parts.append(arrow)
        delta = self.bpm_delta_signed
        if delta is not None:
            rounded = round(delta)
            ratio = (
                self.bpm_dst / self.bpm_src
                if self.bpm_src is not None
                and self.bpm_dst is not None
                and self.bpm_src > 0
                and self.bpm_dst > 0
                else None
            )
            if rounded == 0:
                parts.append("same BPM")
            elif (
                self.bpm_delta_pct is not None
                and self.bpm_delta_pct <= 0.015
                and ratio is not None
                and (ratio >= 1.5 or ratio <= 0.75)
            ):
                parts.append("double-time BPM" if delta > 0 else "half-time BPM")
            else:
                parts.append(f"{rounded:+d} BPM")
        return ", ".join(parts)


def compute_relation(
    *,
    src_track_id: str,
    dst_track_id: str,
    cosine: float,
    src_camelot: str | None,
    dst_camelot: str | None,
    src_bpm: float | None,
    dst_bpm: float | None,
) -> TrackRelation:
    """Compose a :class:`TrackRelation` from two tracks' metadata + a cosine.

    The harmonic + tempo grades come straight from ``intel.transition_scorer``
    so this never diverges from the set-builder. ``cosine`` is passed through
    verbatim (the caller owns the raw-vs-centered choice).
    """
    harmonic, harmonic_flags = _harmonic_score(src_camelot, dst_camelot)
    tempo, tempo_flags = _bpm_score(src_bpm, dst_bpm)

    delta_pct = _bpm_folded_delta_pct(src_bpm, dst_bpm)

    return TrackRelation(
        src_track_id=src_track_id,
        dst_track_id=dst_track_id,
        cosine=float(cosine),
        camelot_src=src_camelot,
        camelot_dst=dst_camelot,
        harmonic=harmonic,
        harmonic_flags=harmonic_flags,
        bpm_src=src_bpm,
        bpm_dst=dst_bpm,
        bpm_delta_pct=delta_pct,
        tempo=tempo,
        tempo_flags=tempo_flags,
    )


__all__ = [
    "HARMONIC_COMPATIBLE_FLOOR",
    "TrackRelation",
    "compute_relation",
]
