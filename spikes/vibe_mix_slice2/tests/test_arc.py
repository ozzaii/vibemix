# SPDX-License-Identifier: Apache-2.0
from spikes.vibe_mix_slice2.arc import (
    Track,
    arc_order,
    energy_is_unimodal,
    energy_only_order,
    harmonic_adjacency_ratio,
)


def test_opener_is_lowest_energy():
    tracks = [
        Track("a", 0.8, "8A"), Track("b", 0.2, "8A"), Track("c", 0.5, "8A"),
    ]
    assert arc_order(tracks)[0].id == "b"


def test_energy_follows_unimodal_arc():
    tracks = [
        Track("t1", 0.1, "8A"), Track("t2", 0.4, "9A"), Track("t3", 0.7, "10A"),
        Track("t4", 0.95, "11A"), Track("t5", 0.6, "12A"), Track("t6", 0.3, "1A"),
    ]
    order = arc_order(tracks)
    assert energy_is_unimodal(order)
    assert order[0].energy == 0.1  # opener is the lowest-energy track


def test_harmonic_grounding_beats_energy_only():
    # A vibe-filtered pool clusters at similar energy: the opener at 0.2, then
    # four tracks all at 0.5 whose keys form a Camelot chain in one order only.
    # Energy alone can't distinguish them; harmonic awareness must.
    tracks = [
        Track("o", 0.20, "8A"),
        Track("p", 0.50, "9A"),    # 8A -> 9A
        Track("q", 0.50, "10A"),   # 9A -> 10A
        Track("r", 0.50, "11A"),   # 10A -> 11A
        Track("s", 0.50, "3B"),    # the odd one out
    ]
    order = arc_order(tracks)
    arc = harmonic_adjacency_ratio(order)
    baseline = harmonic_adjacency_ratio(energy_only_order(tracks))
    assert energy_is_unimodal(order)            # arc shape preserved
    assert arc > baseline                       # grounding strictly helps here
    assert arc >= 0.75                           # chains 8A->9A->10A->11A


def test_arc_never_worse_than_energy_only_on_distinct_energies():
    tracks = [
        Track("a", 0.1, "1A"), Track("b", 0.3, "2A"),
        Track("c", 0.6, "3A"), Track("d", 0.9, "4A"),
    ]
    order = arc_order(tracks)
    assert energy_is_unimodal(order)
    assert harmonic_adjacency_ratio(order) >= harmonic_adjacency_ratio(
        energy_only_order(tracks)
    )


def test_deterministic():
    tracks = [Track(f"t{i}", (i % 5) / 5.0, f"{(i % 12) + 1}A") for i in range(20)]
    assert [t.id for t in arc_order(tracks)] == [t.id for t in arc_order(tracks)]


def test_handles_unknown_keys_without_crashing():
    tracks = [
        Track("a", 0.2, None), Track("b", 0.6, "garbage"), Track("c", 0.9, "8A"),
    ]
    order = arc_order(tracks)
    assert len(order) == 3
    assert energy_is_unimodal(order)
