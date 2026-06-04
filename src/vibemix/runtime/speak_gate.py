# SPDX-License-Identifier: Apache-2.0
"""Runtime value gate for Sven speech turns.

The citation/slop filters decide whether a generated line is safe to speak.
This gate runs earlier: it decides whether a live event is worth asking the
LLM about at all. The first hard rule is intentionally conservative: plain
low-value narration events with no grounded voice payload are describe-bank
territory, so they stay silent by default.
"""

from __future__ import annotations

import math
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
    {
        "HEARTBEAT",
        "PHASE",
        "LAYER_ARRIVAL",
        "PHRASE_BOUNDARY",
        "SUB_LAYER_ARRIVAL",
        "TRACK_CHANGE",
    }
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


def _grounded_voice_payload(ev: Event) -> tuple[str, str] | None:
    extra = ev.extra if isinstance(ev.extra, dict) else {}
    for key in _GROUNDED_VOICE_EXTRA_KEYS:
        value = extra.get(key)
        if value:
            return key, str(value)
    return None


def _text_atom(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def _band_bucket(value: object) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = 0.0
    if not math.isfinite(number):
        number = 0.0
    return f"{number:.1f}"


def _band_fingerprint(ev: Event) -> str:
    bands = getattr(ev.state, "bands", {})
    if not isinstance(bands, dict):
        bands = {}
    return ",".join(
        f"{name}={_band_bucket(bands.get(name, 0.0))}"
        for name in ("sub", "low", "mid", "high")
    )


def event_speak_fingerprint(ev: Event) -> str:
    """Return a deterministic pre-generation fingerprint for repeat gating."""

    extra = ev.extra if isinstance(ev.extra, dict) else {}
    parts = [f"type={ev.type}"]
    if ev.type == "PHASE":
        phase = extra.get("new_phase") or getattr(ev.state, "phase", "")
        parts.append(f"phase={_text_atom(phase)}")
    elif ev.type in {"LAYER_ARRIVAL", "SUB_LAYER_ARRIVAL"}:
        parts.append(f"layer={_text_atom(extra.get('band'))}")
    elif ev.type == "PHRASE_BOUNDARY":
        phase = extra.get("new_phase") or getattr(ev.state, "phase", "")
        parts.append(f"phase={_text_atom(phase)}")
    elif ev.type == "TRACK_CHANGE":
        track = extra.get("new_track") or getattr(ev.state, "audible_track", "")
        parts.append(f"track={_text_atom(track)}")
    else:
        parts.append(f"phase={_text_atom(getattr(ev.state, 'phase', ''))}")

    payload = _grounded_voice_payload(ev)
    if payload is not None:
        key, text = payload
        parts.append(f"payload={key}:{text}")
    if ev.type in _DESCRIBE_BANK_EVENT_TYPES:
        parts.append(f"bands={_band_fingerprint(ev)}")
    return "|".join(parts)


def decide_speak_gate(
    ev: Event,
    *,
    manual: bool = False,
    kaan_just_spoke: bool = False,
    recent_fingerprints: tuple[str, ...] = (),
) -> SpeakGateDecision:
    """Return whether the runtime should ask Sven to generate a line.

    Manual/user speech paths always pass. MIX_MOVE, DROP, and genre-specific
    structural events keep the event priority ladder. The describe-bank-prone
    automatic events (plain HEARTBEAT / PHASE / layer-arrivals / phrase
    boundaries / TRACK_CHANGE) only reach Sven when code has already attached a
    grounded deterministic voice payload.
    """

    if manual or kaan_just_spoke or ev.type in {"MANUAL", "KAAN_SPOKE"}:
        return SpeakGateDecision("speak", "human_or_manual")
    if (
        recent_fingerprints
        and (ev.type in _DESCRIBE_BANK_EVENT_TYPES or _has_grounded_voice_payload(ev))
        and event_speak_fingerprint(ev) in recent_fingerprints
    ):
        return SpeakGateDecision("silent", "repeat_of_recent")
    if ev.type in _DESCRIBE_BANK_EVENT_TYPES:
        if _has_grounded_voice_payload(ev):
            return SpeakGateDecision("speak", "grounded_voice_payload")
        return SpeakGateDecision("silent", "describe_bank_only")
    return SpeakGateDecision("speak", "event_priority")


__all__ = [
    "SpeakGateDecision",
    "SpeakGateVerdict",
    "decide_speak_gate",
    "event_speak_fingerprint",
]
