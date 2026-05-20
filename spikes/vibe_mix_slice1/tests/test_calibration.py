# SPDX-License-Identifier: Apache-2.0
import numpy as np

from spikes.vibe_mix_slice1.calibration import calibrate


def _vec(*dirs: float) -> np.ndarray:
    return np.asarray(dirs, dtype=np.float64)


def test_returns_all_when_pool_at_or_below_k():
    pool = [("a", _vec(1, 0)), ("b", _vec(0, 1))]
    assert calibrate(pool, k=3) == ["a", "b"]


def test_picks_one_from_each_of_three_clusters():
    # Three tight clusters pointing in three different directions, plus
    # near-duplicates inside each. Calibration must surface one per cluster.
    pool = [
        ("x1", _vec(1.0, 0.0, 0.0)), ("x2", _vec(0.98, 0.02, 0.0)),
        ("y1", _vec(0.0, 1.0, 0.0)), ("y2", _vec(0.02, 0.98, 0.0)),
        ("z1", _vec(0.0, 0.0, 1.0)), ("z2", _vec(0.0, 0.02, 0.98)),
    ]
    picks = set(calibrate(pool, k=3))
    assert len(picks) == 3
    # Exactly one representative from each cluster {x*, y*, z*}.
    assert len({p[0] for p in picks}) == 3  # first letters x, y, z all distinct


def test_deterministic_same_pool_same_picks():
    rng = np.random.default_rng(0)
    pool = [(f"t{i}", rng.normal(size=8)) for i in range(40)]
    assert calibrate(pool, k=3) == calibrate(pool, k=3)


def test_first_pick_is_centroid_medoid():
    # A track sitting at the cloud's center should be picked first (the
    # "most typical" reading of the vibe).
    pool = [
        ("center", _vec(1.0, 1.0)),
        ("ne", _vec(2.0, 0.05)),
        ("nw", _vec(0.05, 2.0)),
    ]
    assert calibrate(pool, k=3)[0] == "center"


def test_handles_k_one():
    pool = [("a", _vec(1, 0)), ("b", _vec(0, 1)), ("c", _vec(1, 1))]
    assert calibrate(pool, k=1) == ["c"]  # the medoid of the three
