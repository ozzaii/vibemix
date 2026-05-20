# SPDX-License-Identifier: Apache-2.0
"""Input contract for the cue write-back spike."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CueCandidate:
    """A detected cue point + the detector's confidence.

    Field names track ``vibemix.library.rekordbox.CuePoint`` so this is a
    drop-in upstream of the production reader. ``confidence`` is in [0, 1];
    the confidence gate (the anti-slop law) drops anything below threshold.
    """

    track_location: str   # file:// URI of the audio file
    name: str             # cue label, e.g. "DROP"
    type: str             # "cue" (hot/memory) — strict set only at this gate
    start_s: float        # cue position in seconds
    number: int           # 1..8 = hot cue slot; -1 = memory cue
    confidence: float     # [0, 1]
