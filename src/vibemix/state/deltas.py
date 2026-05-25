# SPDX-License-Identifier: Apache-2.0
"""Pure Δ-render + calibration helpers (Phase 78 / PERCEIVE-01).

Makes the EAR speak in CHANGE, not snapshots. Gemini reads "kick density rose
18%" instead of a bare scalar dump — the documented fix for the felt shallowness.

This module is PURE (analog: ``state/genre/genre_autodetect.py``): it computes
values and returns them; it NEVER writes ``MusicState``. The single-writer
``refresh._tick_once`` captures the prior scalar snapshot; ``coach.evidence_line``
calls ``render_delta`` on the gated render path. No library, no training, no API.

Anti-slop contract (invariants #2/#3): below the relative-change floor the helper
returns ``None`` → the caller appends NOTHING (abstain). A fact that did not
meaningfully move is NEVER asserted as a ``0%`` / ``Δ0`` delta line.
"""

from __future__ import annotations

# --- Anti-slop Δ floor (load-bearing) ---
# A relative change must clear this fraction of the prior magnitude before it is
# rendered as a delta. Below it the change is noise → abstain (omit). 0.10 = 10%:
# tight enough to surface a real kick-density swell, loose enough to suppress the
# bar-to-bar jitter that would otherwise spam "rose 2%" every tick.
DELTA_FLOOR = 0.10

# Calibration buckets (deterministic, monotone in relative magnitude). A pure
# bucket map is chosen over a logistic because the consumer is a TEXT PROMPT, not
# a numeric score: Gemini reads "(strong)" / "(slight)" far more reliably than a
# raw probability, and a bucket is trivially auditable. Boundaries are in units
# of the relative-change magnitude (|cur-prev|/|prev|).
_CONF_STRONG = 0.40  # >= 40% relative move → high confidence the change is real
_CONF_CLEAR = 0.18  # >= 18% → clear
# below _CONF_CLEAR (but >= DELTA_FLOOR) → "slight"

__all__ = ["DELTA_FLOOR", "render_delta", "calibrate_confidence"]


def calibrate_confidence(rel_magnitude: float) -> str:
    """Map a relative-change magnitude to a deterministic, monotone confidence
    bucket. Pure — no library, no training. Returns one of
    ``"strong"`` / ``"clear"`` / ``"slight"``.

    The WHY (see module docstring): the consumer is a prompt string, so a
    human-legible bucket beats a logistic probability for grounding Gemini —
    and it is trivially auditable / test-pinnable.
    """
    m = abs(rel_magnitude)
    if m >= _CONF_STRONG:
        return "strong"
    if m >= _CONF_CLEAR:
        return "clear"
    return "slight"


def render_delta(
    label: str,
    cur: float,
    prev: float | None,
    *,
    floor: float = DELTA_FLOOR,
    fmt: str = "+.0%",
) -> str | None:
    """Render a single scalar's change as grounded Δ-phrasing, or abstain.

    Returns ``None`` (abstain — caller appends nothing) when:
      - ``prev is None`` (cold path — no prior tick to diff against), OR
      - ``prev == 0.0`` (no meaningful baseline → relative change undefined), OR
      - the relative change magnitude is BELOW ``floor`` (anti-slop: a fact that
        didn't meaningfully move is not asserted as a 0% delta).

    Otherwise returns a phrasing string, e.g.::

        "kick density rose 18% (clear)"
        "RMS fell 22% (strong)"

    The verb is chosen by sign (``rose`` / ``fell``); the relative magnitude is
    formatted via ``fmt`` (default ``"+.0%"`` → ``"+18%"``-style, sign stripped
    for the magnitude word). The calibrated confidence bucket is appended so the
    AI can weight the fact.
    """
    if prev is None or prev == 0.0:
        return None
    rel = (cur - prev) / abs(prev)
    if abs(rel) < floor:
        return None  # below floor → abstain (no zero-delta noise)
    verb = "rose" if rel > 0 else "fell"
    # Magnitude word: format |rel| as a percent, no leading sign (the verb carries
    # direction). ``fmt`` defaults to a percent format; strip any sign char.
    pct = format(abs(rel), fmt).lstrip("+")
    conf = calibrate_confidence(rel)
    return f"{label} {verb} {pct} ({conf})"
