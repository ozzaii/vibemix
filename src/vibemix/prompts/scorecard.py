# SPDX-License-Identifier: Apache-2.0
"""Coach scorecard — qualitative session summary.

``summarize_session(events)`` returns one of four bands:

- ``"clean"``       — well-behaved session
- ``"decent"``      — minor slop or some abrupt moves
- ``"abrupt"``      — meaningful rough edges
- ``"train-wreck"`` — multiple severe issues

NEVER numeric. CONTEXT §Coach scorecard explicitly bans any 8/10 / 80% /
0.8 style score — qualitative bands only. Coach mode persists this at
session end via ``events.jsonl`` as a ``coach_scorecard`` event.

Counted signals:
- ``slop_suppressed`` events (the post-hoc filter caught a banned phrase)
- ``MIX_MOVE`` events with ``extra={"abrupt": True}`` (set by EventDetector
  in Phase 3 / 6 — Phase 10 just consumes the flag)

NOT counted (well-behaved or unrelated):
- ``silence_short_circuit`` (LLM correctly emitted ``<silence/>``)
- ``llm_invoke`` / ``ai_text`` / ``track_resolved`` / ... (telemetry, not slop)

Bands derived from CONTEXT §Coach scorecard:
- clean:       slop ≤ 1 AND abrupt_moves ≤ 2
- decent:      slop in [2, 3] OR abrupt_moves in [3, 5]
- abrupt:      slop in [4, 7] OR abrupt_moves in [6, 10]
- train-wreck: slop ≥ 8 OR abrupt_moves ≥ 11

Worst-band-wins on combined inputs (slop count and abrupt-moves count are
evaluated independently; the higher band is returned).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

# Band rank — higher is worse. Used for max() / worst-wins reduction.
_BAND_RANK = {
    "clean": 0,
    "decent": 1,
    "abrupt": 2,
    "train-wreck": 3,
}
_RANK_TO_BAND = {v: k for k, v in _BAND_RANK.items()}


def _band_for_slop(count: int) -> str:
    if count <= 1:
        return "clean"
    if count <= 3:
        return "decent"
    if count <= 7:
        return "abrupt"
    return "train-wreck"


def _band_for_abrupt_moves(count: int) -> str:
    if count <= 2:
        return "clean"
    if count <= 5:
        return "decent"
    if count <= 10:
        return "abrupt"
    return "train-wreck"


def _is_abrupt_mix_move(ev: Mapping[str, Any]) -> bool:
    """True if the event is a MIX_MOVE flagged abrupt."""
    if ev.get("kind") != "MIX_MOVE":
        return False
    extra = ev.get("extra")
    if not isinstance(extra, Mapping):
        return False
    return bool(extra.get("abrupt"))


def summarize_session(events: Sequence[Mapping[str, Any]]) -> str:
    """Classify a session into one of four qualitative bands.

    Args:
        events: Sequence of event dicts (typically read from
            ``events.jsonl``). Each dict must have a ``"kind"`` key. Other
            keys depend on the event type.

    Returns:
        One of ``"clean"`` / ``"decent"`` / ``"abrupt"`` / ``"train-wreck"``.
        Never a number, never a score.
    """
    slop_count = 0
    abrupt_move_count = 0
    for ev in events:
        if not isinstance(ev, Mapping):
            continue
        kind = ev.get("kind")
        if kind == "slop_suppressed":
            slop_count += 1
        elif _is_abrupt_mix_move(ev):
            abrupt_move_count += 1
        # All other event kinds (silence_short_circuit, llm_invoke, ai_text,
        # track_resolved, etc.) are intentionally ignored — they don't
        # signal AI slop or rough mix moves.

    slop_band = _band_for_slop(slop_count)
    abrupt_band = _band_for_abrupt_moves(abrupt_move_count)
    worst_rank = max(_BAND_RANK[slop_band], _BAND_RANK[abrupt_band])
    return _RANK_TO_BAND[worst_rank]
