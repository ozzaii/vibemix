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
import time
from dataclasses import dataclass
from typing import Literal

from vibemix.state import Event

SpeakGateVerdict = Literal["speak", "silent", "hold"]

_GROUNDED_VOICE_EXTRA_KEYS = frozenset(
    {
        "energy_read_voice_line",
        "move_grade_voice_line",
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

WORTHINESS_MIN_DESCRIBE_BANK = 0.38
WORTHINESS_MIN_PRIORITY = 0.24

_EVENT_BASE_WORTHINESS: dict[str, float] = {
    "HEARTBEAT": 0.02,
    "PHASE": 0.12,
    "LAYER_ARRIVAL": 0.12,
    "SUB_LAYER_ARRIVAL": 0.14,
    "PHRASE_BOUNDARY": 0.10,
    "TRACK_CHANGE": 0.42,
    "MIX_MOVE": 0.22,
    "TRANSITION_OPPORTUNITY": 0.22,
    "KICK_DENSITY_SHIFT": 0.26,
    "DISTORTION_CLIMB": 0.28,
    "ACID_LINE_ENTRY": 0.28,
    "KICK_SWAP": 0.38,
    "BREAKDOWN_KICK_KILL": 0.40,
    "REENTRY_KICK_LAND": 0.40,
    "KEY_CLASH": 0.52,
    "DROP": 0.82,
}

_STRUCTURAL_PHASE_PAIRS = frozenset(
    {
        ("silent", "low"),
        ("low", "groove"),
        ("groove", "build"),
        ("build", "drop"),
        ("drop", "groove"),
        ("drop", "peak"),
        ("peak", "breakdown"),
        ("groove", "breakdown"),
        ("breakdown", "build"),
        ("breakdown", "reentry"),
        ("reentry", "drop"),
    }
)


@dataclass(frozen=True, slots=True)
class SpeakGateDecision:
    verdict: SpeakGateVerdict
    reason: str
    tier: str = "runtime_value_gate"
    worthiness: float | None = None

    @property
    def should_speak(self) -> bool:
        return self.verdict == "speak"


def _has_grounded_voice_payload(ev: Event) -> bool:
    return bool(grounded_voice_payload_keys(ev))


def grounded_voice_payload_keys(ev: Event) -> tuple[str, ...]:
    extra = ev.extra if isinstance(ev.extra, dict) else {}
    return tuple(key for key in _GROUNDED_VOICE_EXTRA_KEYS if bool(extra.get(key)))


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


def interruption_worthiness(ev: Event, *, now_s: float | None = None) -> float:
    """Return a deterministic pre-generation interruption score in ``[0, 1]``."""

    state = ev.state
    score = _EVENT_BASE_WORTHINESS.get(ev.type, 0.20)
    if bool(getattr(state, "audible", False)):
        score += 0.06
    if _safe_float(getattr(state, "rms", 0.0)) >= 0.04:
        score += 0.03
    score += 0.42 * _clamp01(_safe_float(getattr(state, "buildup_score", 0.0)))
    score += 0.30 * _drop_proximity(getattr(state, "predicted_drop_in_sec", None))
    score += 0.22 * _phase_structural_score(ev)
    score += 0.22 * _delta_magnitude(getattr(state, "audio_delta", ()))
    score += 0.26 * _delta_magnitude(getattr(state, "move_audio_delta", ()))
    score += 0.34 * _phrase_lookahead_score(state, now_s=now_s)
    score += _cadence_adjustment(state, now_s=now_s)
    return round(_clamp01(score), 3)


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
        return SpeakGateDecision("speak", "human_or_manual", worthiness=1.0)
    worthiness = interruption_worthiness(ev)
    if (
        recent_fingerprints
        and (ev.type in _DESCRIBE_BANK_EVENT_TYPES or _has_grounded_voice_payload(ev))
        and event_speak_fingerprint(ev) in recent_fingerprints
    ):
        return SpeakGateDecision("silent", "repeat_of_recent", worthiness=worthiness)
    if ev.type in _DESCRIBE_BANK_EVENT_TYPES:
        if not _has_grounded_voice_payload(ev):
            return SpeakGateDecision("silent", "describe_bank_only", worthiness=worthiness)
        if worthiness < WORTHINESS_MIN_DESCRIBE_BANK:
            return SpeakGateDecision("silent", "below_worthiness", worthiness=worthiness)
        return SpeakGateDecision("speak", "grounded_voice_payload", worthiness=worthiness)
    if worthiness < WORTHINESS_MIN_PRIORITY:
        return SpeakGateDecision("hold", "priority_below_floor", worthiness=worthiness)
    return SpeakGateDecision("speak", "event_priority", worthiness=worthiness)


def _safe_float(value: object) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return number if math.isfinite(number) else 0.0


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _drop_proximity(value: object) -> float:
    if value is None:
        return 0.0
    eta = _safe_float(value)
    if eta < 0.0:
        return 0.0
    if eta <= 2.0:
        return 1.0
    if eta <= 4.0:
        return 0.70
    if eta <= 8.0:
        return 0.35
    return 0.0


def _phase_structural_score(ev: Event) -> float:
    extra = ev.extra if isinstance(ev.extra, dict) else {}
    prev = _text_atom(extra.get("prev_phase")).lower()
    new = _text_atom(extra.get("new_phase") or getattr(ev.state, "phase", "")).lower()
    if not prev or not new or prev == new:
        return 0.0
    if (prev, new) in _STRUCTURAL_PHASE_PAIRS:
        return 1.0
    return 0.35


def _delta_magnitude(value: object) -> float:
    if not isinstance(value, list | tuple):
        return 0.0
    items = tuple(str(item).strip() for item in value if str(item).strip())
    if not items:
        return 0.0
    return min(1.0, 0.50 + 0.20 * (len(items) - 1))


def _phrase_lookahead_score(state: object, *, now_s: float | None) -> float:
    confidence = _safe_float(getattr(state, "phrase_position_confidence", 0.0))
    next_phrase_at = getattr(state, "next_phrase_at", None)
    if confidence < 0.60 or next_phrase_at is None:
        return 0.0
    try:
        set_seconds = float(getattr(state, "set_seconds", 0.0))
    except Exception:
        set_start_at = _safe_float(getattr(state, "set_start_at", 0.0))
        now = time.time() if now_s is None else now_s
        set_seconds = max(0.0, now - set_start_at) if set_start_at else 0.0
    eta = _safe_float(next_phrase_at) - set_seconds
    if eta < 0.0 or eta > 16.0:
        return 0.0
    return max(0.25, 1.0 - eta / 16.0)


def _cadence_adjustment(state: object, *, now_s: float | None) -> float:
    last_spoke_at = _safe_float(getattr(state, "last_kaan_spoke_at", 0.0))
    if last_spoke_at <= 0.0:
        return 0.0
    now = time.time() if now_s is None else now_s
    elapsed = max(0.0, now - last_spoke_at)
    if elapsed < 18.0:
        return -0.20 * (1.0 - elapsed / 18.0)
    if elapsed >= 90.0:
        return 0.06
    return 0.0


__all__ = [
    "SpeakGateDecision",
    "SpeakGateVerdict",
    "decide_speak_gate",
    "event_speak_fingerprint",
    "grounded_voice_payload_keys",
    "interruption_worthiness",
]
