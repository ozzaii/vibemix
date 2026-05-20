# SPDX-License-Identifier: Apache-2.0
"""End-to-end prep-flow shape test, fully offline via injected fakes."""
import numpy as np

from spikes.vibe_mix_slice1.prep_flow import prep_set
from spikes.vibe_mix_slice2.arc import energy_is_unimodal

# A tiny fake library: id -> (vector, energy, camelot).
_LIB = {
    "deep1":  (np.array([1.0, 0.0, 0.0], np.float32), 0.20, "8A"),
    "deep2":  (np.array([0.95, 0.1, 0.0], np.float32), 0.50, "9A"),
    "drive1": (np.array([0.9, 0.2, 0.0], np.float32),  0.50, "10A"),
    "peak1":  (np.array([0.85, 0.3, 0.0], np.float32), 0.50, "11A"),
    "offvibe":(np.array([0.0, 0.0, 1.0], np.float32),  0.90, "3B"),
}


def _search(_query: str):
    return list(_LIB.keys())


def _vector_of(tid: str):
    return _LIB[tid][0]


def _meta_of(tid: str):
    _, energy, camelot = _LIB[tid]
    return energy, camelot


def test_prep_flow_end_to_end():
    picked = {}

    def _pick(anchors):
        picked["anchors"] = anchors
        return anchors[0]  # the DJ takes the prototypical anchor

    order = prep_set(
        "deep hypnotic set",
        search_fn=_search,
        vector_of=_vector_of,
        meta_of=_meta_of,
        pick_fn=_pick,
        set_size=4,
    )

    # Calibration offered exactly 3 anchors.
    assert len(picked["anchors"]) == 3
    # The off-vibe track is the farthest point -> it must be one of the anchors
    # (calibration surfaces distinct poles so the DJ can reject it).
    assert "offvibe" in picked["anchors"]

    ids = [t.id for t in order]
    assert len(ids) == 4                       # capped at set_size
    assert len(set(ids)) == 4                   # no duplicates
    assert "offvibe" not in ids                 # focused re-extract drops the outlier
    assert energy_is_unimodal(order)            # arc shape holds end-to-end


def test_empty_search_returns_empty():
    order = prep_set(
        "no matches",
        search_fn=lambda q: [],
        vector_of=_vector_of,
        meta_of=_meta_of,
        pick_fn=lambda a: a[0],
    )
    assert order == []
