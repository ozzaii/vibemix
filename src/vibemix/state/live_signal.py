# SPDX-License-Identifier: Apache-2.0
"""The single typed contract the Judge (and any future engine) reads.

One frozen frame unifies the two previously non-comparable feature vocabularies
(master `snapshot_features` vs per-lane `_deck_frame_features`). Engines attach
as pure (frame) -> signal functions: additive, never invasive. No audio capture,
no model client, no Tauri — pure data.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LaneObservation:
    """One deck lane's trustworthy state at a moment.

    `bands` is the per-lane band-energy *ratio* map {sub,low,mid,high} in [0,1]
    summing to ~1.0, or None when no per-lane spectrum is available (honest-null
    upstream). `source_trusted` is False for now-playing rows of unknown/last-known
    provenance — the Judge must abstain on the harmonic signal in that case.
    """

    active: bool
    source_trusted: bool
    camelot: str | None
    bands: dict[str, float] | None
    rms: float
    track_id: str | None


@dataclass(frozen=True, slots=True)
class LiveSignalFrame:
    """The Judge's whole input. Assembled by the caller from already-live state;
    the engine NEVER resolves anything itself (single-writer invariant respected).

    `policy` is the `live_claim_policy(...)` verdict string; the Judge asserts
    policy == 'supported_verdict' as its activation precondition. `routing_enabled`
    mirrors DeckAudioRouting.enabled — False on master-only rigs.
    """

    t_session: float
    policy: str
    routing_enabled: bool
    lanes: dict[str, LaneObservation]

    def lane_sides(self) -> tuple[str, ...]:
        return tuple(sorted(self.lanes.keys()))

    def lane(self, side: str) -> LaneObservation | None:
        return self.lanes.get(side)

    def both_lanes_active(self) -> bool:
        sides = self.lane_sides()
        if len(sides) < 2:
            return False
        return all(self.lanes[s].active for s in sides)
