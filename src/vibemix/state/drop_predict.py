# SPDX-License-Identifier: Apache-2.0
"""Live drop anticipation — seconds until the next drop on the audible deck.

``refresh.py`` already resolves the audible track's structural sections (DJ cues or
``cue_detect`` auto-structure) and the live play position every tick. This turns those
two facts into the one number the co-host needs to call the drop on time:
``predicted_drop_in_sec``. It is a pure read over already-detected structure — the
system's own detector feeds it, never a hand-supplied time (compose-existing) — so the
single-writer tick can populate the field the SYSTEM-AUDIT C9 gap left ``None`` forever.

Honest by construction: no upcoming drop, an unknown position, or a drop only behind a
too-low-confidence cue returns ``None`` (no claim), and a drop past the horizon is left
uncalled rather than predicted minutes early.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any

#: Section roles that count as a "drop" — section_builder already folds slam/chorus/hook
#: into role ``"drop"`` (see ``_classify``), so matching the canonical role is enough.
_DROP_ROLE = "drop"


def predict_drop_in_sec(
    sections: Sequence[Any],
    position_s: float | None,
    *,
    min_confidence: float = 0.0,
    max_horizon_s: float | None = None,
) -> float | None:
    """Seconds until the next drop section strictly after ``position_s``.

    ``sections`` are ``SectionRecord``-like objects (``.role``, ``.start_s``,
    ``.confidence``) for the audible track, in any order. Returns the gap to the
    earliest qualifying drop whose ``start_s > position_s`` and whose confidence
    clears ``min_confidence``; ``None`` when the position is unknown, no such drop
    remains, or the nearest one is beyond ``max_horizon_s``.
    """
    if position_s is None:
        return None
    best: float | None = None
    for section in sections:
        if getattr(section, "role", None) != _DROP_ROLE:
            continue
        start = float(getattr(section, "start_s", 0.0))
        if start <= position_s:
            continue  # already passed (or standing on it) — not "incoming"
        if float(getattr(section, "confidence", 0.0)) < min_confidence:
            continue
        eta = start - position_s
        if best is None or eta < best:
            best = eta
    if best is None:
        return None
    if max_horizon_s is not None and best > max_horizon_s:
        return None
    return max(0.0, best)


def next_drop_section(
    sections: Sequence[Any],
    position_s: float | None,
    *,
    min_confidence: float = 0.0,
    max_horizon_s: float | None = None,
) -> Any | None:
    """Return the next qualifying drop section, matching ``predict_drop_in_sec``."""
    if position_s is None:
        return None
    best_section = None
    best_eta: float | None = None
    for section in sections:
        if getattr(section, "role", None) != _DROP_ROLE:
            continue
        start = float(getattr(section, "start_s", 0.0))
        if start <= position_s:
            continue
        if float(getattr(section, "confidence", 0.0)) < min_confidence:
            continue
        eta = start - position_s
        if best_eta is None or eta < best_eta:
            best_eta = eta
            best_section = section
    if best_eta is None:
        return None
    if max_horizon_s is not None and best_eta > max_horizon_s:
        return None
    return best_section


#: Seconds before the drop to fire the call. Sized so the spoken line + TTS
#: latency lands the punchline ON the drop, not after it.
DROP_ARM_WINDOW_S = 2.0


def should_arm_drop_call(
    predicted_now: float | None,
    predicted_prev: float | None,
    *,
    arm_window_s: float = DROP_ARM_WINDOW_S,
) -> bool:
    """True on the SINGLE tick the drop countdown crosses DOWN into the arm window.

    Fires once per approach: the current reading sits inside ``arm_window_s`` while
    the previous reading was outside it (or unknown). A reading already inside the
    window on the prior tick does not re-fire, so one approach yields at most one
    call. ``None`` (no predicted drop) never arms.
    """
    if predicted_now is None:
        return False
    if predicted_now > arm_window_s:
        return False
    if predicted_prev is not None and predicted_prev <= arm_window_s:
        return False
    return True


def drop_call_cue(predicted_now: float | None, *, arm_window_s: float = DROP_ARM_WINDOW_S) -> str:
    """Reaction-bank key for a drop call at this ETA — the anticipation "here it
    comes" call while the drop is still inside the arm window. Kept a function so
    the cue can be tuned by ETA later without touching callers."""
    return "drop_incoming"
