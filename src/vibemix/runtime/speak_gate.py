# SPDX-License-Identifier: Apache-2.0
"""Runtime value gate for Sven speech turns.

The citation/slop filters decide whether a generated line is safe to speak.
This gate runs earlier: it decides whether a live event is worth asking the
LLM about at all. The first hard rule is intentionally conservative: plain
low-value narration events with no grounded voice payload are describe-bank
territory, so they stay silent by default.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from vibemix.state import Event

SpeakGateVerdict = Literal["speak", "silent", "hold"]

_GROUNDED_VOICE_EXTRA_KEYS = frozenset(
    {
        "next_suggestion_voice_line",
        "transition_verdict_voice_line",
        "set_progress_voice_line",
        "judge_evidence_line",
    }
)

_DESCRIBE_BANK_EVENT_TYPES = frozenset(
    {"HEARTBEAT", "PHASE", "LAYER_ARRIVAL", "TRACK_CHANGE"}
)


@dataclass(frozen=True, slots=True)
class SpeakGateDecision:
    verdict: SpeakGateVerdict
    reason: str
    tier: str = "runtime_value_gate"

    @property
    def should_speak(self) -> bool:
        return self.verdict == "speak"


def _has_grounded_voice_payload(ev: Event) -> bool:
    extra = ev.extra if isinstance(ev.extra, dict) else {}
    return any(bool(extra.get(key)) for key in _GROUNDED_VOICE_EXTRA_KEYS)


def decide_speak_gate(
    ev: Event,
    *,
    manual: bool = False,
    kaan_just_spoke: bool = False,
) -> SpeakGateDecision:
    """Return whether the runtime should ask Sven to generate a line.

    Manual/user speech paths always pass. MIX_MOVE, DROP, and genre-specific
    structural events keep the event priority ladder. The describe-bank-prone
    automatic events (plain HEARTBEAT / PHASE / LAYER_ARRIVAL / TRACK_CHANGE)
    only reach Sven when code has already attached a grounded deterministic
    voice payload.
    """

    if manual or kaan_just_spoke or ev.type in {"MANUAL", "KAAN_SPOKE"}:
        return SpeakGateDecision("speak", "human_or_manual")
    if ev.type in _DESCRIBE_BANK_EVENT_TYPES:
        if _has_grounded_voice_payload(ev):
            return SpeakGateDecision("speak", "grounded_voice_payload")
        return SpeakGateDecision("silent", "describe_bank_only")
    return SpeakGateDecision("speak", "event_priority")


__all__ = [
    "SpeakGateDecision",
    "SpeakGateVerdict",
    "decide_speak_gate",
]
