"""Section-continuity in the beam edge cost (the eta term).

The optimizer scored edges with whole-track coherence + graded Camelot only;
the persisted section vectors it ignored can say whether THIS outro flows
into THAT intro. eta folds that in, cache-only, with the honest-degrade
contract pinned: missing section evidence contributes ZERO cost, so a
section-less library orders byte-identically to before.
"""

from __future__ import annotations

import numpy as np

from vibemix.library.sequencer import PoolTrack, sequence_set


def _track(tid: str, vec: np.ndarray, bpm: float = 124.0) -> PoolTrack:
    return PoolTrack(
        track_id=tid,
        title=f"T{tid}",
        artist="A",
        vec=vec,
        bpm=bpm,
        camelot="8A",
        energy=50.0,
        duration_s=300.0,
        cues=(),
    )


def _uniform_pool() -> list[PoolTrack]:
    # Identical track vectors + keys + energy: coherence/harmonic/curve terms
    # are constant across orders, so ONLY the section term can break the tie.
    base = np.ones(8, dtype=np.float32)
    return [_track(t, base.copy()) for t in ("a", "b", "c")]


def _axis(i: int) -> np.ndarray:
    v = np.zeros(8, dtype=np.float32)
    v[i] = 1.0
    return v


def test_section_continuity_flips_the_order() -> None:
    pool = _uniform_pool()
    # a's outro matches b's intro exactly and OPPOSES c's intro; b's outro
    # then flows into c. The only section-coherent order is a -> b -> c.
    section_io = {
        "a": (_axis(0), _axis(7)),
        "b": (_axis(1), _axis(0)),
        "c": (_axis(2), -_axis(0)),
    }
    out = sequence_set(pool, curve=[50.0, 50.0, 50.0], n_slots=3, section_io=section_io)
    assert out, "expected at least one candidate"
    assert out[0].track_ids == ["a", "b", "c"]


def test_missing_section_vectors_change_nothing() -> None:
    pool = _uniform_pool()
    baseline = sequence_set(pool, curve=[50.0, 50.0, 50.0], n_slots=3)
    none_io = sequence_set(pool, curve=[50.0, 50.0, 50.0], n_slots=3, section_io=None)
    half_io = sequence_set(
        pool,
        curve=[50.0, 50.0, 50.0],
        n_slots=3,
        # Only one side present anywhere -> every (out, in) pair is incomplete
        # -> all-ones matrix -> zero added cost everywhere.
        section_io={"a": (_axis(0), None)},
    )
    for variant in (none_io, half_io):
        assert [c.track_ids for c in variant] == [c.track_ids for c in baseline]
        assert [c.cost for c in variant] == [c.cost for c in baseline]


def test_candidates_expose_total_cost() -> None:
    out = sequence_set(_uniform_pool(), curve=[50.0, 50.0, 50.0], n_slots=3)
    assert out
    # cost is the beam objective the toolset now surfaces; ranked cheapest-first.
    costs = [c.cost for c in out]
    assert costs == sorted(costs)
