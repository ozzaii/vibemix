# SPDX-License-Identifier: Apache-2.0
"""PERCEIVE-03 — pure genre reconciliation + confidence-band normalization tests.

These pin THE flagged risk (RESEARCH Pitfall 4 / Assumption A3): the centered
cosine confidence (natural floor ~PROTO_FLOOR ≈ 0.25) must normalize into
coach.py's ``>= 0.5`` render band, AND the embedding-wins-when-confident
reconciliation policy must fuse embedding-genre + DSP-genre into one coherent
label. Pure functions — no state, no I/O, no API.
"""

from __future__ import annotations

import pytest

from vibemix.library.genre_prototypes import PROTO_FLOOR
from vibemix.state.genre.genre_reconcile import (
    normalize_embedding_confidence,
    reconcile_genre,
)


# ---------- normalize_embedding_confidence — the flagged-risk pin ----------


def test_normalize_clears_render_gate_above_floor():
    """A centered cosine clearing the ~0.25 floor maps to >= 0.5 (clears the
    coach.py:334 render gate) — the over-suppression risk closed."""
    assert normalize_embedding_confidence(0.40) >= 0.5
    assert normalize_embedding_confidence(0.82) >= 0.5


def test_normalize_suppresses_below_floor():
    """A sub-floor centered cosine maps below 0.5 (suppressed → abstain holds)."""
    assert normalize_embedding_confidence(0.20) < 0.5
    assert normalize_embedding_confidence(0.10) < 0.5


def test_normalize_anchors_and_clamps():
    """Anchors: floor → ~0.5, 1.0 → 1.0; out-of-range clamps to [0, 1]."""
    assert normalize_embedding_confidence(PROTO_FLOOR) == pytest.approx(0.5)
    assert normalize_embedding_confidence(1.0) == pytest.approx(1.0)
    # Clamp — a cosine above 1.0 / below 0 never escapes the render band.
    assert normalize_embedding_confidence(1.5) == pytest.approx(1.0)
    assert normalize_embedding_confidence(-0.5) == 0.0


def test_normalize_is_monotone():
    """Stronger match never renders weaker (monotone increasing)."""
    a = normalize_embedding_confidence(0.30)
    b = normalize_embedding_confidence(0.50)
    c = normalize_embedding_confidence(0.90)
    assert a < b < c


# ---------- reconcile_genre — embedding-wins-when-confident policy ----------


def test_reconcile_confident_embedding_wins_on_disagree():
    """Disagree + confident embedding → embedding label wins, render-band conf."""
    label, conf = reconcile_genre("hard_techno", 0.40, "house", 0.6)
    assert label == "hard_techno"
    assert conf >= 0.5


def test_reconcile_agree_uses_embedding_band():
    """Agree (same label) + confident embedding → that label on the render band."""
    label, conf = reconcile_genre("techno", 0.50, "techno", 0.6)
    assert label == "techno"
    assert conf >= 0.5


def test_reconcile_sub_floor_embedding_falls_back_to_dsp():
    """Embedding below floor → DSP fallback at the DSP native confidence."""
    assert reconcile_genre("trance", 0.10, "house", 0.6) == ("house", 0.6)


def test_reconcile_unknown_embedding_falls_back_to_dsp():
    """Unknown embedding label → DSP fallback (embedding does not override)."""
    assert reconcile_genre("unknown", 0.0, "house", 0.6) == ("house", 0.6)


def test_reconcile_both_unknown():
    """Both unknown → ("unknown", 0.0)."""
    assert reconcile_genre("unknown", 0.0, "unknown", 0.0) == ("unknown", 0.0)
