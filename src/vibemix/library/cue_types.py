# SPDX-License-Identifier: Apache-2.0
"""CueAnchor — the cross-session contract for structural cue points.

This is the single shared seam between the auto-cue *producer* (the offline
pipeline assembled by :mod:`vibemix.library.cue_engine`, ``source="auto"``), the
Rekordbox ANLZ structure floor (``source="anlz"``), and the *consumer* (the
embedding/ingest path that slices <=80s mixable windows and, later, the live
co-host's "enter on hot cue 2" suggestions). DJ-library cues (Rekordbox/Serato
hot cues) enter the same vocabulary as ``source="dj"``.

The field set is intentionally minimal and FROZEN — both sides depend on it, so
engine-internal richness (phrase length, snapped-to-grid flag, Camelot key,
mix-in/out role) is kept inside the engine and NOT leaked here. A CueAnchor is
just: what kind of moment, where it starts/ends, how much to trust it, and who
placed it.

Label vocabulary (5 dance-structure functions):

    intro      — first mixable region; the load / blend-in point.
    build      — rising-energy run that terminates at a drop (tension).
    breakdown  — bass collapse mid-track while melody/pads persist (blend-out).
    drop       — full-band energy landing; the moment the floor wants.
    outro      — decaying tail; the blend-out region.

On non-dance / beatless material the producer degrades gracefully and emits
only the position-defined labels (``intro`` / ``outro``) — it never forces a
``drop`` onto ambient (the anti-hallucination contract, "trust the audio").
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

__all__ = ["CueAnchor", "CueLabel", "CueSource"]

CueLabel = Literal["intro", "build", "breakdown", "drop", "outro"]
CueSource = Literal["dj", "anlz", "auto"]


@dataclass(frozen=True, slots=True)
class CueAnchor:
    """A single structural cue point with a mixable window.

    ``end_s - start_s`` is the <=80s mixable window (the span a DJ blends over
    and the single-call audio-embed cap). ``confidence`` ∈ [0, 1] is the
    producer's trust in this anchor; consumers gate on it (a low-confidence cue
    falls back to mean-excerpt embedding / is hedged or suppressed in the live
    pill). ``source`` records who placed it: ``"dj"`` (from a DJ library),
    ``"anlz"`` (Rekordbox offline structure), or ``"auto"`` (this engine).
    """

    label: CueLabel
    start_s: float
    end_s: float
    confidence: float
    source: CueSource
