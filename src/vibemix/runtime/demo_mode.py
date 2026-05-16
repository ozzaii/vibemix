# SPDX-License-Identifier: Apache-2.0
"""Demo-mode deterministic event sequencer.

VIS-09 (Phase 43, Plan 43-09): seeds a fixed 30-event sequence that
plays back identically across capture-day takes. Hooks into the
existing event dispatcher when ``vibemix --demo-mode`` is set.

Sequence anchors (per CONTEXT §VIS-09):

  0:00   track_start  (Track A)
  2:33   kick_swap    (mascot celebrate trigger)
  4:50   layer_drop   (mascot teacher line trigger)
  6:00   track_end

Between anchors: filler events (``controller_move``, ``bpm_shift``,
``mood_tick``) distributed to feel natural. Total = 30 events.

Reset workflow: ``vibemix --demo-mode reset`` calls :func:`reset` to
return the cursor to step 0 for the next take.

Public surface
==============

- :data:`DEMO_SEQUENCE` — frozen ``tuple[DemoEvent, ...]`` (length 30).
- :func:`load_sequence` — reset and return a fresh :class:`DemoState`.
- :func:`step` — return the current event and advance. ``None`` when exhausted.
- :func:`reset` — return cursor to step 0.

Threat model (Plan 43-09 §threat_model):

- T-43-09-01 (Tampering — DEMO_SEQUENCE timestamps): mitigated by the
  module-level invariant asserts below + the pytest pin suite at
  ``tests/runtime/test_demo_mode_sequence.py``.
- T-43-09-02 (DoS — accidentally enabled in shipped binary): mitigated
  by requiring an explicit ``--demo-mode`` CLI flag — this module is
  inert until ``load_sequence()`` / ``step()`` is invoked. Default
  vibemix behaviour is live input.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class DemoEvent:
    """A single event in the deterministic demo sequence.

    ``kind`` is one of:

    - ``"track_start"`` — beginning of Track A (step 0 / 0:00)
    - ``"kick_swap"`` — mascot celebrate trigger (anchor at 2:33)
    - ``"layer_drop"`` — mascot teacher line trigger (anchor at 4:50)
    - ``"track_end"`` — track ends (anchor at 6:00)
    - ``"controller_move"`` — filler: MIDI knob/fader/cue activity
    - ``"bpm_shift"`` — filler: BPM nudge/transition
    - ``"mood_tick"`` — filler: persona heartbeat (Hype-man/Teacher/Coach)
    """

    timestamp_s: float
    kind: str
    payload: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# 30-event deterministic sequence (per CONTEXT §VIS-09).
# Times in seconds; track plays 0:00 → 6:00.
#
# Layout (anchor + filler distribution):
#   step  0  →  0.0s    track_start              (anchor 1 — 0:00)
#   steps 1–8 → 15s..125s   pre-kick-swap fillers (8 events)
#   step  9  →  153.0s   kick_swap                (anchor 2 — 2:33)
#   steps 10–18 → 170..285s post-kick fillers     (9 events)
#   step  19 →  290.0s  layer_drop                (anchor 3 — 4:50)
#   steps 20–28 → 295..358s post-drop fillers     (9 events)
#   step  29 →  360.0s   track_end                (anchor 4 — 6:00)
#
# Filler timings are intentionally non-uniform; the pytest suite pins
# the anchors only.
# ---------------------------------------------------------------------------

DEMO_SEQUENCE: tuple[DemoEvent, ...] = (
    DemoEvent(0.0,   "track_start",     {"track": "A"}),
    # Pre-kick-swap fillers (0:15 → 2:05) — 8 events of natural texture
    DemoEvent(15.0,  "controller_move", {"control": "filter_hi", "delta": 0.1}),
    DemoEvent(30.0,  "bpm_shift",       {"from": 128.0, "to": 128.0}),
    DemoEvent(45.0,  "mood_tick",       {"mood": "coach"}),
    DemoEvent(60.0,  "controller_move", {"control": "eq_mid_a", "delta": -0.05}),
    DemoEvent(75.0,  "controller_move", {"control": "fader_a",  "delta": 0.0}),
    DemoEvent(90.0,  "bpm_shift",       {"from": 128.0, "to": 128.5}),
    DemoEvent(105.0, "mood_tick",       {"mood": "coach"}),
    DemoEvent(125.0, "controller_move", {"control": "filter_lo", "delta": 0.05}),
    # ▶ Anchor: 2:33 = 153.0s
    DemoEvent(153.0, "kick_swap",       {"from": "kick_a", "to": "kick_b"}),
    # Post-kick-swap fillers (2:50 → 4:45) — 9 events
    DemoEvent(170.0, "mood_tick",       {"mood": "hype-man"}),
    DemoEvent(185.0, "controller_move", {"control": "fx_echo", "delta": 0.15}),
    DemoEvent(200.0, "controller_move", {"control": "eq_hi_b", "delta": 0.08}),
    DemoEvent(215.0, "bpm_shift",       {"from": 128.5, "to": 129.0}),
    DemoEvent(230.0, "controller_move", {"control": "filter_hi", "delta": -0.1}),
    DemoEvent(245.0, "mood_tick",       {"mood": "hype-man"}),
    DemoEvent(260.0, "controller_move", {"control": "cue_b", "delta": 1.0}),
    DemoEvent(275.0, "controller_move", {"control": "fader_a", "delta": -0.2}),
    DemoEvent(285.0, "controller_move", {"control": "fader_b", "delta": 0.4}),
    # ▶ Anchor: 4:50 = 290.0s
    DemoEvent(290.0, "layer_drop",      {"layer": "synth_pad", "energy": 0.7}),
    # Post-layer-drop fillers (4:55 → 5:58) — 9 events
    DemoEvent(295.0, "mood_tick",       {"mood": "teacher"}),
    DemoEvent(305.0, "controller_move", {"control": "eq_lo_b", "delta": 0.1}),
    DemoEvent(315.0, "controller_move", {"control": "fx_filter", "delta": 0.2}),
    DemoEvent(325.0, "bpm_shift",       {"from": 129.0, "to": 129.0}),
    DemoEvent(335.0, "controller_move", {"control": "fader_b", "delta": 0.0}),
    DemoEvent(345.0, "mood_tick",       {"mood": "coach"}),
    DemoEvent(350.0, "controller_move", {"control": "filter_lo", "delta": -0.05}),
    DemoEvent(355.0, "controller_move", {"control": "cue_a", "delta": 1.0}),
    DemoEvent(358.0, "controller_move", {"control": "fader_b", "delta": -0.5}),
    # ▶ Anchor: 6:00 = 360.0s
    DemoEvent(360.0, "track_end",       {"track": "A"}),
)


# Module-level invariants — these are tamper-detect asserts (T-43-09-01).
# If anyone reorders DEMO_SEQUENCE or removes the track_end anchor, the
# import itself fails — the demo cannot run with a broken sequence.
assert len(DEMO_SEQUENCE) == 30, (
    f"DEMO_SEQUENCE must have 30 events, got {len(DEMO_SEQUENCE)}"
)

_timestamps = [e.timestamp_s for e in DEMO_SEQUENCE]
assert _timestamps == sorted(_timestamps), (
    "DEMO_SEQUENCE must be sorted by timestamp ascending"
)

# Anchor timestamps — load-bearing for the capture day storyboard.
assert any(e.kind == "kick_swap"  and e.timestamp_s == 153.0 for e in DEMO_SEQUENCE), (
    "DEMO_SEQUENCE missing kick_swap anchor at 153.0s (2:33)"
)
assert any(e.kind == "layer_drop" and e.timestamp_s == 290.0 for e in DEMO_SEQUENCE), (
    "DEMO_SEQUENCE missing layer_drop anchor at 290.0s (4:50)"
)
assert DEMO_SEQUENCE[-1].kind == "track_end" and DEMO_SEQUENCE[-1].timestamp_s == 360.0, (
    "DEMO_SEQUENCE last event must be track_end at 360.0s (6:00)"
)


@dataclass
class DemoState:
    """Cursor state for the demo sequencer. Single per-process instance
    held below as ``_state`` — load_sequence/step/reset all act on it."""

    step_index: int = 0


# Module-level singleton state. The vibemix runtime is single-process
# single-event-loop; this module is inert until --demo-mode invokes
# load_sequence() (T-43-09-02 mitigation).
_state = DemoState()


def load_sequence() -> DemoState:
    """Reset the sequencer and return the fresh state object.

    Francesco's take workflow calls this before each take. The returned
    state is the same module-level singleton as ``_state`` — callers
    inspect ``state.step_index`` for diagnostics; mutation should go
    through :func:`step` and :func:`reset`.
    """
    reset()
    return _state


def step() -> Optional[DemoEvent]:
    """Return the current event and advance the cursor.

    Returns ``None`` when the sequence is exhausted (after 30 calls).
    Subsequent calls remain ``None`` until :func:`reset` or
    :func:`load_sequence` is invoked.
    """
    if _state.step_index >= len(DEMO_SEQUENCE):
        return None
    event = DEMO_SEQUENCE[_state.step_index]
    _state.step_index += 1
    return event


def reset() -> None:
    """Return the cursor to step 0 (for the next take)."""
    _state.step_index = 0


__all__ = [
    "DEMO_SEQUENCE",
    "DemoEvent",
    "DemoState",
    "load_sequence",
    "reset",
    "step",
]
