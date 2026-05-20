# SPDX-License-Identifier: Apache-2.0
"""Narrative arc ordering: energy shape first, mix in key where you can.

Orders a set into opener -> builder -> peak -> cooldown while preferring
harmonically-compatible adjacencies. The energy arc is the narrative spine
(primary); Camelot compatibility is the constraint we satisfy whenever it does
not fight the arc (secondary). That priority is deliberate: a DJ follows the
energy story and mixes in key when they have the choice — not the reverse.

Algorithm (deterministic, guaranteed-unimodal):

1. Build an energy "tent" (``energy_only_order``): sorted energies arranged so
   they rise to a single peak then fall. This fixes the energy at every slot
   and is unimodal by construction.
2. Reorder only WITHIN runs of (near-)equal energy to chain harmonically from
   the track before the run. Equal-energy tracks are arc-interchangeable, so
   this improves key compatibility without disturbing the energy shape.

This is the honest scope: with distinct energies the arc is energy-determined
(no harmonic freedom); the win shows up exactly when the pool clusters at
similar energy — which a vibe-filtered pool does. Full multi-objective
optimization (beam search / ILP over arc + harmonic jointly) is deferred to
the real build; the spike proves the Camelot logic is correct and that
harmonic-aware ordering never scores worse than an energy-only sort.
"""
from __future__ import annotations

from dataclasses import dataclass

from spikes.vibe_mix_slice2.camelot import are_compatible

_EQUAL_ENERGY_TOL = 1e-9


@dataclass(frozen=True, slots=True)
class Track:
    id: str
    energy: float          # 0..1 (a deep-feature output; an input here)
    camelot: str | None    # raw key string or Camelot code; None if unknown


def energy_only_order(tracks: list[Track]) -> list[Track]:
    """Baseline: a unimodal energy tent with no harmonic awareness."""
    ordered = sorted(tracks, key=lambda t: (t.energy, t.id))
    rise = ordered[::2]                 # lower energies first, ascending
    fall = ordered[1::2][::-1]          # remaining, descending after the peak
    return rise + fall


def _chain_group(group: list[Track], prev: Track | None) -> list[Track]:
    """Order an equal-energy run to chain harmonically from ``prev``."""
    remaining = list(group)
    chain: list[Track] = []
    cur = prev
    while remaining:
        if cur is None:
            nxt = min(remaining, key=lambda t: t.id)
        else:
            nxt = min(
                remaining,
                key=lambda t: (0 if are_compatible(cur.camelot, t.camelot) else 1, t.id),
            )
        chain.append(nxt)
        remaining.remove(nxt)
        cur = nxt
    return chain


def arc_order(tracks: list[Track]) -> list[Track]:
    """Order ``tracks`` along the arc, mixing in key where the arc allows."""
    if len(tracks) <= 1:
        return list(tracks)

    tent = energy_only_order(tracks)
    out: list[Track] = []
    i = 0
    while i < len(tent):
        j = i
        while (
            j + 1 < len(tent)
            and abs(tent[j + 1].energy - tent[i].energy) <= _EQUAL_ENERGY_TOL
        ):
            j += 1
        group = tent[i : j + 1]
        if len(group) > 1:
            group = _chain_group(group, out[-1] if out else None)
        out.extend(group)
        i = j + 1
    return out


def harmonic_adjacency_ratio(order: list[Track]) -> float:
    """Fraction of adjacent pairs that are a safe harmonic mix (0..1)."""
    if len(order) < 2:
        return 1.0
    compat = sum(
        are_compatible(a.camelot, b.camelot) for a, b in zip(order, order[1:])
    )
    return compat / (len(order) - 1)


def energy_is_unimodal(order: list[Track], tol: float = 1e-9) -> bool:
    """True iff energies rise (weakly) to a single peak, then fall (weakly)."""
    energies = [t.energy for t in order]
    peak = energies.index(max(energies))
    rising = all(energies[i] <= energies[i + 1] + tol for i in range(peak))
    falling = all(
        energies[i] >= energies[i + 1] - tol
        for i in range(peak, len(energies) - 1)
    )
    return rising and falling
