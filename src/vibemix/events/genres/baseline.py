# SPDX-License-Identifier: Apache-2.0
"""Baseline (default) chain — empty by design.

Returned when ``state.active_genre`` is ``"unknown"`` (or any unregistered
value — the GenreRouter falls back to baseline + WARN log per
T-17-05-01 mitigation). Also the chain returned for "unknown" tracks before
the genre detector locks in.

Contract: per-genre chains ADD detectors on top of the v4 baseline rules in
``vibemix.state.event_detector.EventDetector`` — they NEVER replace baseline
rules. The baseline TRACK_CHANGE / PHASE / LAYER_ARRIVAL / MIX_MOVE /
HEARTBEAT path stays byte-identical to v4 even when the active chain is
empty (this baseline) — that's the SENSE-15 backward-compat contract.

Why empty rather than "the v4 detection logic moved here"? Because moving
the v4 logic into a chain detector would require porting the cardinal
gating rules (KAAN_SPOKE bypass, music-presence gate, _audible_since
tracking, _reset_change_refs) out of EventDetector — a structural rewrite
the plan explicitly forbids. Keeping baseline detection inside
EventDetector and letting the chain ADD genre-specific detectors is the
minimal-deviation path to the SENSE-11 router architecture.
"""

from __future__ import annotations


def build_baseline_chain() -> list:
    """Return the baseline detector chain — empty list.

    The v4 baseline detection (TRACK_CHANGE / PHASE / LAYER_ARRIVAL /
    MIX_MOVE / HEARTBEAT) is implemented inline in
    ``vibemix.state.event_detector.EventDetector.detect`` and runs on every
    tick regardless of chain contents. The empty chain here is what every
    genre that doesn't have a registered builder falls back to.
    """
    return []
