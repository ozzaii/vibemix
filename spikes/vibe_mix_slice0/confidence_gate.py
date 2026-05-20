# SPDX-License-Identifier: Apache-2.0
"""The anti-slop law: drop any cue we are not confident about."""
from __future__ import annotations

from spikes.vibe_mix_slice0.types import CueCandidate

# Conservative by intent. A wrong cue fired in front of a crowd is worse
# than the manual prep we removed, so the bar to auto-place is high.
DEFAULT_THRESHOLD: float = 0.85


def gate_cues(
    candidates: list[CueCandidate], threshold: float = DEFAULT_THRESHOLD
) -> list[CueCandidate]:
    """Return only candidates at or above ``threshold``, order preserved."""
    return [c for c in candidates if c.confidence >= threshold]
