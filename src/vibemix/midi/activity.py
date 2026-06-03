# SPDX-License-Identifier: Apache-2.0
"""Pure controller MIDI activity classification helpers."""

from __future__ import annotations


def classify_controller_midi_activity(
    controller: object | None,
    *,
    connected: bool,
) -> tuple[str, int, int, int]:
    """Classify controller MIDI traffic without treating an open port as proof.

    ``connected=True`` only proves that the OS port opened. A live controller
    lane also needs actual MIDI frames, mapped events, and then human-readable
    moves before downstream code may treat deck controls as observable.
    """
    if not connected:
        return "disconnected", 0, 0, 0
    if controller is None:
        return "unknown", 0, 0, 0
    activity_fn = getattr(controller, "activity_snapshot", None)
    if not callable(activity_fn):
        return "unknown", 0, 0, 0
    try:
        snap = activity_fn()
    except Exception:
        return "unknown", 0, 0, 0
    if not isinstance(snap, dict):
        return "unknown", 0, 0, 0

    def _count(key: str) -> int:
        try:
            return max(0, int(snap.get(key) or 0))
        except (TypeError, ValueError):
            return 0

    messages = _count("messages_seen_total")
    events = _count("events_seen_total")
    moves = _count("moves_seen_total")
    if messages == 0:
        activity = "connected_no_midi_traffic"
    elif events == 0:
        activity = "midi_traffic_unmapped"
    elif moves == 0:
        activity = "midi_events_no_moves"
    else:
        activity = "active"
    return activity, messages, events, moves
