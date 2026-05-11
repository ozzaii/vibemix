# SPDX-License-Identifier: Apache-2.0
"""validate_bpm — half/double snap to profile.bpm_range (Phase 6 Wave 2).

Autocorrelation BPM estimation often locks onto half- or double-speed
patterns:
- 62 BPM detected on a 124 BPM techno track (locked on the alternating
  kick/clap pattern).
- 250 BPM on a 125 BPM track (autocorr's first peak is at the 8th note
  rather than the 4th).

The validator inspects the active genre profile's BPM range. If ``raw_bpm``
falls within the range — pass through. If ``raw_bpm * 2`` fits — double-corrected
(the autocorr was probably tracking half-time). If ``raw_bpm / 2`` fits — halve.
Otherwise pass through unchanged; the existing ``BPM_VALID_MIN/MAX`` gate in
``vibemix.audio.constants`` filters out-of-range BPMs downstream.

Defensive zero/negative short-circuit: ``estimate_bpm`` returns 0.0 as the
"no signal" marker. Doubling zero is zero. We surface (0.0, False) for both
zero AND negative inputs (autocorr can theoretically emit negative on a math
glitch — treat as no-signal).
"""

from __future__ import annotations

from vibemix.state.genre.profile import GenreProfile


def validate_bpm(raw_bpm: float, profile: GenreProfile) -> tuple[float, bool]:
    """Snap raw_bpm to profile.bpm_range via half/double correction.

    Returns (normalized_bpm, was_corrected).

    - raw_bpm <= 0.0 → (0.0, False) (defensive no-signal short-circuit)
    - lo <= raw_bpm <= hi → (raw_bpm, False) (pass-through)
    - lo <= raw_bpm * 2 <= hi → (raw_bpm * 2, True) (half-detected, double it)
    - lo <= raw_bpm / 2 <= hi → (raw_bpm / 2, True) (double-detected, halve)
    - otherwise → (raw_bpm, False) (out of range; downstream gate filters)
    """
    if raw_bpm <= 0.0:
        return (0.0, False)

    lo, hi = float(profile.bpm_range[0]), float(profile.bpm_range[1])

    if lo <= raw_bpm <= hi:
        return (raw_bpm, False)

    doubled = raw_bpm * 2.0
    if lo <= doubled <= hi:
        return (doubled, True)

    halved = raw_bpm / 2.0
    if lo <= halved <= hi:
        return (halved, True)

    return (raw_bpm, False)
