# SPDX-License-Identifier: Apache-2.0
"""PERCEIVE-03 — pure genre reconciliation + confidence-band normalization.

This module solves THE flagged risk of Phase 78 (RESEARCH Pitfall 4 / Assumption
A3): the embedding genre lookup (``library.genre_prototypes``) returns a RAW
centered-cosine confidence whose natural floor sits at ~``PROTO_FLOOR`` (≈0.25),
but the single prompt render gate in ``coach.evidence_line`` (coach.py:334) is
``genre_confidence >= 0.5``. A raw centered cosine of ~0.25 would NEVER clear
0.5, so a confident embedding genre would be silently over-suppressed.

The fix is an affine rescale that maps the centered-cosine band into the
``>= 0.5`` render band, plus an explicit reconciliation policy that fuses the
embedding genre with the existing DSP ``score_genre`` path into ONE coherent
label per tick.

PURE module — analog ``state.genre.genre_autodetect``: no state write, no I/O,
no model literal, no API call. The single-writer ``refresh._tick_once`` calls
``reconcile_genre`` and writes the result; this module never touches the live
state dataclass (invariant #1).

Reconciliation policy (RESEARCH Open Q1 recommendation — the simplest coherent
rule): prefer the embedding genre when it is a real label AND its NORMALIZED
confidence clears the render floor; otherwise fall back to the DSP
``(label, confidence)``. The committed label is run through
``apply_genre_hysteresis`` by the caller (no flicker) — this module returns the
raw reconciled ``(label, render_band_confidence)``.
"""

from __future__ import annotations

from vibemix.library.genre_prototypes import PROTO_FLOOR

# The render gate coach.py:334 asserts genre= only at genre_confidence >= 0.5.
# This is the affine anchor: a centered cosine at PROTO_FLOOR maps to exactly
# the render floor, and a perfect cosine (1.0) maps to 1.0.
_RENDER_FLOOR: float = 0.5


def normalize_embedding_confidence(cosine: float, *, floor: float = PROTO_FLOOR) -> float:
    """Map a centered-cosine confidence into coach.py's ``>= 0.5`` render band.

    THE flagged-risk fix (RESEARCH Pitfall 4). The centered cosine separation
    sits on a tighter scale than the DSP confidence (centered floor ≈ 0.25 vs
    DSP 0.55), so the raw cosine cannot be compared against the single
    ``>= 0.5`` render gate directly. This deterministic, monotone affine rescale
    anchors the two scales:

        floor (≈0.25)  →  _RENDER_FLOOR (0.5)   — a match exactly at the floor
                                                   sits on the render boundary
        1.0            →  1.0                    — a perfect match stays perfect

    so a cosine clearing ``floor`` by any margin maps to ``>= 0.5`` (clears the
    gate) and a sub-``floor`` cosine maps to ``< 0.5`` (suppressed → the abstain
    contract holds). Clamped to ``[0, 1]``. Monotone increasing in ``cosine``,
    so a stronger match never renders weaker.
    """
    span = 1.0 - floor
    if span <= 0.0:  # degenerate floor guard — never let a /0 manufacture conf
        return _RENDER_FLOOR if cosine >= floor else 0.0
    scaled = _RENDER_FLOOR + (cosine - floor) / span * (1.0 - _RENDER_FLOOR)
    return max(0.0, min(1.0, scaled))


def reconcile_genre(
    emb_label: str,
    emb_conf_raw: float,
    dsp_label: str,
    dsp_conf: float,
    *,
    emb_floor: float = PROTO_FLOOR,
) -> tuple[str, float]:
    """Fuse embedding-genre + DSP-genre into ONE coherent ``(label, conf)``.

    Policy (RESEARCH Open Q1): the embedding genre wins when it is a real label
    (``!= "unknown"``) AND its NORMALIZED confidence clears the render floor
    (equivalently: its raw centered cosine clears ``emb_floor``). Otherwise the
    DSP ``score_genre`` result is the fallback — including its native
    confidence, which is ALREADY on the DSP [0, 1] / ``>= 0.5`` scale.

    - **Agree** (same label, embedding confident) → embedding wins; its
      normalized confidence is on the render band and a real-vs-real agreement
      is at least as confident as either source.
    - **Disagree + confident embedding** → embedding label wins (86.5%-validated
      embedding signal beats the coarse 3-band DSP proxy).
    - **Embedding below floor / unknown** → DSP fallback at its native conf.
    - **Both unknown** → ``("unknown", 0.0)``.

    Returns ``(label, render_band_confidence)`` — the caller runs the label
    through ``apply_genre_hysteresis`` before committing.
    """
    if emb_label and emb_label != "unknown":
        emb_conf_norm = normalize_embedding_confidence(emb_conf_raw, floor=emb_floor)
        if emb_conf_norm >= _RENDER_FLOOR:
            return (emb_label, emb_conf_norm)
    # Embedding unavailable / sub-floor → the existing DSP path owns the label.
    return (dsp_label, dsp_conf)


__all__ = ["reconcile_genre", "normalize_embedding_confidence"]
