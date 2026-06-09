# SPDX-License-Identifier: Apache-2.0
"""sequencer — order a candidate pool into an N-slot set following an energy
curve via beam search over technically-valid (Camelot + BPM) transitions.

Pure-compute: synthetic PoolTracks with hand-set vec/bpm/camelot/energy. No
network, no Gemini, no store. Pins: curve resample, the transition gate
(both-known degrade), curve-following ordering, dominance dedup + Jaccard
diversity, and the honest-degrade edge cases (never an invalid untagged
transition, never a fabricated track).
"""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from vibemix.library import sequencer as seq
from vibemix.library.sequencer import (
    CURVE_PRESETS,
    PoolTrack,
    SetCandidate,
    sequence_set,
)


# ---------------------------------------------------------------------------
# Synthetic pool helpers
# ---------------------------------------------------------------------------
def _vec(seed: int, dim: int = 1536) -> np.ndarray:
    """Deterministic unit-norm float32 vector."""
    rng = np.random.default_rng(seed)
    v = rng.standard_normal(dim).astype(np.float32)
    n = float(np.linalg.norm(v))
    return (v / n).astype(np.float32)


def _pt(
    tid: str,
    *,
    seed: int = 0,
    bpm: float | None = 124.0,
    camelot: str | None = "8A",
    energy: float | None = 50.0,
    vec: np.ndarray | None = None,
    duration_s: float = 300.0,
    cues: tuple[object, ...] = (),
) -> PoolTrack:
    return PoolTrack(
        track_id=tid,
        title=f"Title {tid}",
        artist=f"Artist {tid}",
        vec=_vec(seed) if vec is None else vec,
        bpm=bpm,
        camelot=camelot,
        energy=energy,
        duration_s=duration_s,
        cues=cues,
    )


def _cue(start_s: float, name: str = "", cue_type: str = "cue") -> SimpleNamespace:
    return SimpleNamespace(start_s=start_s, name=name, type=cue_type)


# ===========================================================================
# Curve presets + resample
# ===========================================================================
def test_curve_presets_exist_and_in_range():
    for name in ("opener", "peak_time", "after_hours", "festival"):
        assert name in CURVE_PRESETS
        arr = np.asarray(CURVE_PRESETS[name], dtype=float)
        assert arr.size >= 2
        assert arr.min() >= 0.0 and arr.max() <= 100.0


def test_curve_resample_to_n_slots():
    # A preset (any length) resamples to EXACTLY n_slots via np.interp.
    for n in (1, 4, 12, 20, 37):
        out = seq.resample_curve("peak_time", n)
        assert len(out) == n
        assert all(0.0 <= v <= 100.0 for v in out)


def test_curve_resample_accepts_raw_list():
    # A raw list[float] also resamples (curve param = preset name OR list).
    out = seq.resample_curve([0.0, 100.0], 5)
    assert len(out) == 5
    assert out[0] == pytest.approx(0.0)
    assert out[-1] == pytest.approx(100.0)
    # linear interp midpoint
    assert out[2] == pytest.approx(50.0, abs=1e-6)


def test_opener_rises_overall():
    out = seq.resample_curve("opener", 20)
    assert out[-1] > out[0]  # opener climbs low -> high


def test_peak_time_sustains_high():
    out = seq.resample_curve("peak_time", 20)
    # back half sits high (sustained 85-95 band)
    assert np.mean(out[len(out) // 2 :]) >= 80.0


# ===========================================================================
# Transition gate
# ===========================================================================
def test_transition_both_known_incompatible_rejected():
    a = _pt("a", camelot="8A", bpm=124.0)
    b = _pt("b", camelot="2A", bpm=124.0)  # 8A vs 2A = far hour -> clash/neither
    _relaxed, valid = seq._transition_valid(a, b)
    assert valid is False


def test_transition_both_known_compatible_accepted():
    a = _pt("a", camelot="8A", bpm=124.0)
    b = _pt("b", camelot="9A", bpm=124.0)  # adjacent fifth = SAFE
    relaxed, valid = seq._transition_valid(a, b)
    assert valid is True
    assert relaxed is False


def test_transition_missing_key_passes():
    a = _pt("a", camelot=None, bpm=124.0)
    b = _pt("b", camelot="2A", bpm=124.0)
    _, valid = seq._transition_valid(a, b)
    assert valid is True  # missing metadata -> PASS (graceful degrade)


def test_transition_missing_bpm_passes():
    a = _pt("a", camelot="8A", bpm=None)
    b = _pt("b", camelot="8A", bpm=200.0)
    _, valid = seq._transition_valid(a, b)
    assert valid is True


def test_transition_bpm_within_tol_accepted():
    a = _pt("a", camelot="8A", bpm=124.0)
    b = _pt("b", camelot="8A", bpm=124.0 * 1.06)  # exactly +6%
    _, valid = seq._transition_valid(a, b, bpm_tol=0.06)
    assert valid is True


def test_transition_bpm_half_double_time_accepted():
    a = _pt("a", camelot="8A", bpm=87.0)
    b = _pt("b", camelot="8A", bpm=174.0)
    _, valid = seq._transition_valid(a, b, bpm_tol=0.06)
    assert valid is True

    reverse_relaxed, reverse_valid = seq._transition_valid(b, a, bpm_tol=0.06)
    assert reverse_valid is True
    assert reverse_relaxed is False


def test_transition_bpm_over_tol_rejected():
    a = _pt("a", camelot="8A", bpm=124.0)
    b = _pt("b", camelot="8A", bpm=124.0 * 1.07)  # +7% > 6%
    _, valid = seq._transition_valid(a, b, bpm_tol=0.06)
    assert valid is False


def test_structural_cues_tag_weak_transition_without_rejecting():
    # Both tracks have cue metadata, but A has no late/outgoing anchor and B has
    # no early/incoming anchor. The sequencer keeps the set possible while
    # surfacing the structural weakness as a relaxed transition.
    a = _pt("a", seed=1, energy=25.0, cues=(_cue(8.0, "intro"),))
    b = _pt("b", seed=2, energy=75.0, cues=(_cue(240.0, "outro"),))

    cands = sequence_set([a, b], curve="opener", n_slots=2, weights={"beta": 0.0})

    assert cands
    assert cands[0].track_ids == ["a", "b"]
    assert cands[0].relaxed_transitions == [
        ("a", "b", "cue structure weak (no mix-out cue, no mix-in cue)")
    ]


def test_structural_cues_clean_when_mix_out_and_mix_in_exist():
    a = _pt(
        "a",
        seed=1,
        energy=25.0,
        cues=(_cue(12.0, "intro"), _cue(230.0, "outro")),
    )
    b = _pt(
        "b",
        seed=2,
        energy=75.0,
        cues=(_cue(8.0, "intro"), _cue(220.0, "outro")),
    )

    cands = sequence_set([a, b], curve="opener", n_slots=2, weights={"beta": 0.0})

    assert cands
    assert cands[0].track_ids == ["a", "b"]
    assert cands[0].relaxed_transitions == []


# ===========================================================================
# Beam: ordering follows the curve
# ===========================================================================
def _curve_followable_pool() -> list[PoolTrack]:
    """A pool whose energies span 0..100 so SOME ordering can track any curve.
    All same key + bpm so every transition is valid (isolates the curve term)."""
    energies = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 95]
    return [
        _pt(f"t{i}", seed=i, bpm=124.0, camelot="8A", energy=float(e))
        for i, e in enumerate(energies)
    ]


def test_beam_returns_valid_ordered_set_following_curve():
    pool = _curve_followable_pool()
    cands = sequence_set(pool, curve="opener", n_slots=8)
    assert cands, "must return at least one candidate"
    best = cands[0]
    assert isinstance(best, SetCandidate)
    assert len(best.track_ids) == 8
    # distinct tracks (no track mixed into itself)
    assert len(set(best.track_ids)) == len(best.track_ids)
    # follows the curve well: good fit + low-energy track lands early.
    assert best.energy_fit < 25.0
    by_id = {p.track_id: p for p in pool}
    first_e = by_id[best.track_ids[0]].energy
    last_e = by_id[best.track_ids[-1]].energy
    assert first_e < last_e  # opener climbs


def test_beam_low_energy_lands_in_low_slot_peak_curve():
    # peak_time ends high -> the highest-energy track should be late, not first.
    pool = _curve_followable_pool()
    best = sequence_set(pool, curve="peak_time", n_slots=8)[0]
    by_id = {p.track_id: p for p in pool}
    energies = [by_id[t].energy for t in best.track_ids]
    # late-half mean energy clearly exceeds early-half mean energy
    half = len(energies) // 2
    assert np.mean(energies[half:]) > np.mean(energies[:half])


# ===========================================================================
# Candidate count + Jaccard diversity + dominance dedup
# ===========================================================================
def test_returns_at_most_n_candidates_and_diverse():
    pool = [
        _pt(f"t{i}", seed=i, bpm=124.0, camelot="8A", energy=float((i * 7) % 100))
        for i in range(30)
    ]
    cands = sequence_set(pool, curve="peak_time", n_slots=10, n_candidates=4)
    assert 1 <= len(cands) <= 4
    # ranked by cost ascending
    costs = [c.cost for c in cands]
    assert costs == sorted(costs)
    # Jaccard-diverse: each pair shares < ~70% of tracks
    for i in range(len(cands)):
        for j in range(i + 1, len(cands)):
            si, sj = set(cands[i].track_ids), set(cands[j].track_ids)
            jac = len(si & sj) / len(si | sj)
            assert jac <= 0.7 + 1e-9


def test_dominance_dedup_prunes(monkeypatch):
    # Sanity: with dominance dedup the beam stays bounded even on a big pool.
    pool = [
        _pt(f"t{i}", seed=i, bpm=124.0, camelot="8A", energy=float((i * 3) % 100))
        for i in range(40)
    ]
    cands = sequence_set(pool, curve="festival", n_slots=12, beam_width=48)
    assert cands
    assert all(len(set(c.track_ids)) == len(c.track_ids) for c in cands)


# ===========================================================================
# Edge cases — degrade, never fabricate
# ===========================================================================
def test_pool_smaller_than_slots_returns_short_set():
    pool = [_pt(f"t{i}", seed=i, energy=float(i * 20)) for i in range(3)]
    cands = sequence_set(pool, curve="opener", n_slots=10)
    assert cands
    # cannot exceed pool size; no fabricated tracks
    assert len(cands[0].track_ids) <= 3
    assert set(cands[0].track_ids) <= {p.track_id for p in pool}


def test_all_same_bpm_harmonic_only_ordering_works():
    # Every track same bpm + compatible keys; pure coherence/energy ordering.
    pool = [
        _pt(f"t{i}", seed=i, bpm=126.0, camelot="8A", energy=float(i * 12))
        for i in range(8)
    ]
    cands = sequence_set(pool, curve="opener", n_slots=6)
    assert cands
    assert len(set(cands[0].track_ids)) == len(cands[0].track_ids)


def test_missing_energy_pool_bpm_proxy_no_crash():
    # No energy at all -> BPM proxy fills in; must not crash and must order.
    pool = [
        _pt(f"t{i}", seed=i, bpm=float(118 + i * 2), camelot="8A", energy=None)
        for i in range(8)
    ]
    cands = sequence_set(pool, curve="opener", n_slots=6)
    assert cands
    assert len(cands[0].track_ids) >= 1


def test_no_energy_no_bpm_does_not_crash():
    # energy AND bpm both None -> energy term contributes 0, coherence-driven.
    pool = [
        _pt(f"t{i}", seed=i, bpm=None, camelot="8A", energy=None)
        for i in range(6)
    ]
    cands = sequence_set(pool, curve="peak_time", n_slots=4)
    assert cands
    assert len(set(cands[0].track_ids)) == len(cands[0].track_ids)


def test_sparse_graph_relaxation_tags_or_honest_short_set():
    # Mutually incompatible keys + far BPMs -> the strict graph is near-empty.
    # The engine must EITHER tag relaxed transitions OR return an honest short
    # set, but NEVER emit an invalid UNTAGGED transition.
    pool = [
        _pt("a", seed=1, bpm=120.0, camelot="1A", energy=10.0),
        _pt("b", seed=2, bpm=150.0, camelot="6A", energy=50.0),  # clash + far bpm
        _pt("c", seed=3, bpm=180.0, camelot="11A", energy=90.0),
    ]
    cands = sequence_set(pool, curve="opener", n_slots=3)
    assert cands
    best = cands[0]
    # Every consecutive pair is either strictly valid OR recorded as relaxed.
    by_id = {p.track_id: p for p in pool}
    relaxed_pairs = {tuple(t[:2]) for t in best.relaxed_transitions}
    for x, y in zip(best.track_ids, best.track_ids[1:], strict=False):
        a, b = by_id[x], by_id[y]
        _, strict_ok = seq._transition_valid(a, b)
        if not strict_ok:
            # if it survived in the set, it MUST be tagged as relaxed
            assert (x, y) in relaxed_pairs, (
                f"untagged invalid transition {x}->{y}"
            )


def test_empty_pool_returns_empty():
    assert sequence_set([], curve="opener", n_slots=5) == []


def test_set_candidate_is_frozen():
    pool = _curve_followable_pool()
    best = sequence_set(pool, curve="opener", n_slots=5)[0]
    with pytest.raises((AttributeError, Exception)):
        best.cost = 0.0  # frozen dataclass


# ---------------------------------------------------------------------------
# S1 — graded harmonic edges (lane: next-track intelligence / engine moat)
# ---------------------------------------------------------------------------


def test_graded_harmonic_edge_prefers_cleaner_key_ordering() -> None:
    """Among gate-VALID orderings the graded harmonic edge term picks the
    cleaner-blending one. CLAP vibe (shared vec -> cosine 1), BPM (all 124) and
    the energy curve (all energy 50 -> track-independent node cost) are
    neutralized, so the harmonic edge is the ONLY differentiator: a rough-key
    track placed MID-input is pushed to an END so the two same-key tracks stay
    adjacent (the only 0-cost harmonic edge). On HEAD the edge is CLAP-only, so
    all orderings tie and the rough-key track stays mid -> RED."""
    shared = _vec(7)
    t0 = _pt("t0", camelot="8A", vec=shared)
    tR = _pt("tR", camelot="9A", vec=shared)  # +1 hour: gate-valid, harmonic 0.88
    t1 = _pt("t1", camelot="8A", vec=shared)
    best = sequence_set([t0, tR, t1], curve="opener", n_slots=3)[0]
    order = best.track_ids
    assert order.index("tR") in (0, len(order) - 1), order


def test_unknown_key_track_not_demoted_below_known_suboptimal() -> None:
    """Honest-degrade: an unknown-key track contributes ZERO graded cost (mirror
    the gate's degrade-to-pass), so it must NOT rank a worse blend than a track
    with a KNOWN-but-suboptimal key. The known +2 track (10A, harmonic 0.78) is
    pushed to an end; the unknown track keeps the favorable middle. A wrong
    unknown->0.45 cost would invert this and bury the unknown track instead."""
    shared = _vec(7)
    t0 = _pt("t0", camelot="8A", vec=shared)
    tS = _pt("tS", camelot="10A", vec=shared)  # +2 same-letter: gate-valid, harmonic 0.78
    tU = _pt("tU", camelot=None, vec=shared)   # unknown key -> 0 graded cost
    best = sequence_set([t0, tS, tU], curve="opener", n_slots=3)[0]
    order = best.track_ids
    # unknown->0 makes both tU edges free, so the only cost-0 orderings keep the
    # unknown track in the favorable MIDDLE and push the known +2 track to an end.
    # A wrong unknown->0.45 cost makes tU's edges (0.045) costlier than the +2
    # edge (0.022), inverting this and burying tU at an end.
    assert order.index("tU") not in (0, len(order) - 1), order
    assert order.index("tS") in (0, len(order) - 1), order


def test_small_harmonic_weight_does_not_flatten_energy_arc() -> None:
    """The harmonic tiebreak must stay SMALL enough not to override the energy
    curve: a +2 energy-lift track (10A) whose energy fits the peak slot must NOT
    be demoted below a same-key (8A) track that misfits the slot, just to keep
    the key static. Guards against an over-large zeta (a too-big weight flips
    this to the same-key track and flattens the arc)."""
    shared = _vec(7)
    anchor = _pt("anchor", camelot="8A", energy=30.0, vec=shared)
    lift = _pt("lift", camelot="10A", energy=52.0, vec=shared)  # +2 key, fits the peak
    same = _pt("same", camelot="8A", energy=30.0, vec=shared)   # same key, misfits the peak
    best = sequence_set([anchor, lift, same], curve=[30.0, 52.0], n_slots=2)[0]
    assert best.track_ids[1] == "lift", best.track_ids
