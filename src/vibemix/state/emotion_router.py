# SPDX-License-Identifier: Apache-2.0
"""Phase 31 Plan 03 — Emotion router (pure function).

Derives a mascot emotion label from the live ``MusicState``. The label is
broadcast on the ws_bus ``emotion`` field; the frontend ``EmotionLayer``
subscribes and updates its priority-60 channel on change.

4 emotions:

- ``hyped`` — high RMS (any genre). Peak / drop landed.
- ``focused`` — techno or house at mid RMS. Heads-down working groove.
- ``concerned`` — low RMS persisting for >= 30s. Dead-air risk.
- ``neutral`` — default fall-through.

Anti-hallucination:

- When ``active_genre == "unknown"`` (typical during BPM lock-up), we
  STILL emit an emotion based on RMS alone. The bar for emotion is
  "real audio energy", not "confident genre" — so low-confidence
  scenarios still get a sensible mascot expression rather than freezing
  on ``neutral``.
- We never read wall-clock; ``time_in_phase`` is passed in.

Thresholds align with cohost_v4 phase classification gates
(``audio/constants.py:_classify_active_genre``-adjacent) — the same RMS
band the v4 prompt template used for "is this peak energy?" decisions.
"""

from __future__ import annotations

from typing import Literal

MascotEmotion = Literal["neutral", "focused", "hyped", "concerned"]

# Energy thresholds — match v4 informal "is this loud" cutoffs.
# Anything sustained >= 0.18 RMS is "peak energy"; below 0.08 is
# "dead air" territory.
RMS_HIGH = 0.18
RMS_LOW = 0.08

# Long-phase threshold for "concerned": low energy persisting past this
# many seconds = mascot worried about dead air.
LONG_PHASE_SEC = 30.0

# Genres that get the "focused" mid-energy treatment. hard_tek skips
# focused because hard_tek at mid-RMS is still a build, not a groove.
FOCUSED_GENRES: frozenset[str] = frozenset({"techno", "house"})


def derive_emotion(
    active_genre: str,
    rms: float,
    time_in_phase: float,
) -> MascotEmotion:
    """Map (genre, rms, time_in_phase) → MascotEmotion.

    Priority order matches the contract above:

    1. ``hyped`` wins on high RMS regardless of genre.
    2. ``focused`` for techno/house at mid RMS.
    3. ``concerned`` for sustained low RMS.
    4. ``neutral`` is the fall-through.
    """
    if rms >= RMS_HIGH:
        return "hyped"
    if active_genre in FOCUSED_GENRES and rms >= RMS_LOW:
        return "focused"
    if rms < RMS_LOW and time_in_phase >= LONG_PHASE_SEC:
        return "concerned"
    return "neutral"
