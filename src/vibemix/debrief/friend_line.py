# SPDX-License-Identifier: Apache-2.0
"""Grounded one-line debrief friend copy.

These helpers are intentionally small and resolver-backed. A line only exists
when its citation resolves against the same EvidenceRegistry snapshot contract
used by debrief drills. That keeps "Last Night, Heard" from becoming a pretty
sentence wrapped around decorative citation text.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from vibemix.debrief.drills import _citation_resolves
from vibemix.debrief.near_miss_detector import NearMissResult

EvidenceSnapshot = dict[str, dict[str, list[float]]]

_LONG_PHASE_MIN_BARS = 12.0
_DEFAULT_BPM = 120.0


@dataclass(frozen=True, slots=True)
class FriendLine:
    """A display/speech line plus the receipt text behind it."""

    kind: str
    text: str
    receipt_text: str
    citation: str

    def to_dict(self) -> dict[str, str]:
        return {
            "kind": self.kind,
            "text": self.text,
            "receipt_text": self.receipt_text,
            "citation": self.citation,
        }


@dataclass(frozen=True, slots=True)
class MorningFriendLines:
    """The two-line "Last Night, Heard" payload."""

    near_miss: FriendLine | None = None
    gap: FriendLine | None = None

    def to_dict(self) -> dict[str, dict[str, str] | None]:
        return {
            "near_miss": self.near_miss.to_dict() if self.near_miss else None,
            "gap": self.gap.to_dict() if self.gap else None,
        }


def build_morning_friend_lines(
    *,
    near_miss: NearMissResult | None,
    events: list[dict[str, Any]],
    evidence_snapshot: EvidenceSnapshot,
) -> MorningFriendLines:
    """Build the near-miss and gap lines, each honest-null independently."""
    return MorningFriendLines(
        near_miss=(
            build_near_miss_friend_line(near_miss, evidence_snapshot)
            if near_miss is not None
            else None
        ),
        gap=build_gap_friend_line(events, evidence_snapshot),
    )


def build_near_miss_friend_line(
    near_miss: NearMissResult,
    evidence_snapshot: EvidenceSnapshot,
) -> FriendLine | None:
    """Return the resolver-backed near-miss line, or ``None``.

    The detector creates the ``[mix:near_miss@t]`` atom from the real master
    input. We add that derived observation to a local snapshot copy, then run
    the standard debrief resolver. A mismatched source/key/timestamp will still
    fail.
    """
    snapshot = _with_near_miss_evidence(evidence_snapshot, near_miss)
    if not _citation_resolves(near_miss.citation, snapshot):
        return None

    ms = _beats_to_ms(near_miss.phase_error_beats_peak, near_miss.bpm)
    direction = "late" if near_miss.phase_error_beats_peak > 0 else "early"
    bars = _format_bars(near_miss.recovery_bars)
    citation = near_miss.citation
    text = (
        f"I heard the mix drift about {ms} ms {direction}, then you pulled it "
        f"back inside {bars} bars {citation}"
    )
    receipt = (
        f"the mix recovered by ear at {_format_clock(near_miss.t_center_s)}; "
        f"depth {near_miss.depth_beats:.2f} beat, back in {bars} bars {citation}"
    )
    return FriendLine(kind="near_miss", text=text, receipt_text=receipt, citation=citation)


def build_gap_friend_line(
    events: list[dict[str, Any]],
    evidence_snapshot: EvidenceSnapshot,
) -> FriendLine | None:
    """Return one resolver-backed long-breakdown line, or ``None``."""
    candidate = _long_phase_candidate(events)
    if candidate is None:
        return None
    t_s, phase, bars = candidate
    citation = f"[ev:PHASE@{t_s:.3f}]"
    if not _citation_resolves(citation, evidence_snapshot):
        return None

    bars_text = _format_bars(bars)
    text = (
        f"The mix lingered in the {phase} for about {bars_text} bars; "
        f"next time, decide sooner {citation}"
    )
    receipt = f"{phase} held at {_format_clock(t_s)} for about {bars_text} bars {citation}"
    return FriendLine(kind="gap", text=text, receipt_text=receipt, citation=citation)


async def synthesize_friend_line_audio(
    line: FriendLine,
    *,
    adapter_factory=None,
    line_synthesizer=None,
):
    """Speak a grounded friend line through the existing product voice seam."""
    from vibemix.agent.line_voice import build_default_line_adapter, synthesize_line

    if adapter_factory is None:
        adapter_factory = build_default_line_adapter
    if line_synthesizer is None:
        line_synthesizer = synthesize_line
    adapter = adapter_factory()
    return await line_synthesizer(adapter, line.text)


def _with_near_miss_evidence(
    evidence_snapshot: EvidenceSnapshot,
    near_miss: NearMissResult,
) -> EvidenceSnapshot:
    snapshot: EvidenceSnapshot = {
        source: {key: list(times) for key, times in keys.items()}
        for source, keys in evidence_snapshot.items()
    }
    mix = snapshot.setdefault("mix", {})
    mix.setdefault("near_miss", [])
    mix["near_miss"].append(float(near_miss.t_center_s))
    return snapshot


def _long_phase_candidate(events: list[dict[str, Any]]) -> tuple[float, str, float] | None:
    phase_events: list[tuple[float, str, float]] = []
    for event in events:
        if str(event.get("kind") or "") != "event":
            continue
        if str(event.get("type") or "") != "PHASE":
            continue
        t_s = _event_time_s(event)
        phase = str(event.get("phase") or "").strip().lower()
        if t_s is None or phase not in {"breakdown", "low"}:
            continue
        bpm = _event_bpm(event) or _DEFAULT_BPM
        phase_events.append((t_s, phase, bpm))
    if not phase_events:
        return None

    best: tuple[float, str, float] | None = None
    for idx, (t_s, phase, bpm) in enumerate(phase_events):
        next_t = _next_structural_time(events, after_s=t_s)
        if next_t is None and idx + 1 < len(phase_events):
            next_t = phase_events[idx + 1][0]
        if next_t is None or next_t <= t_s:
            continue
        bars = (next_t - t_s) / (4.0 * 60.0 / bpm)
        if bars < _LONG_PHASE_MIN_BARS:
            continue
        if best is None or bars > best[2]:
            best = (t_s, phase, bars)
    return best


def _next_structural_time(events: list[dict[str, Any]], *, after_s: float) -> float | None:
    best: float | None = None
    for event in events:
        if str(event.get("kind") or "") != "event":
            continue
        event_type = str(event.get("type") or "")
        if event_type not in {"PHASE", "TRACK_CHANGE", "MIX_MOVE"}:
            continue
        t_s = _event_time_s(event)
        if t_s is None or t_s <= after_s:
            continue
        if best is None or t_s < best:
            best = t_s
    return best


def _event_time_s(event: dict[str, Any]) -> float | None:
    value = event.get("t")
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        return float(value)
    return None


def _event_bpm(event: dict[str, Any]) -> float | None:
    value = event.get("bpm")
    if isinstance(value, (int, float)) and math.isfinite(float(value)) and value > 0:
        return float(value)
    return None


def _beats_to_ms(error_beats: float, bpm: float) -> int:
    if bpm <= 0.0:
        return 0
    return round(abs(error_beats) * (60_000.0 / bpm))


def _format_clock(t_s: float) -> str:
    total = max(0, round(t_s))
    minutes, seconds = divmod(total, 60)
    return f"{minutes}:{seconds:02d}"


def _format_bars(value: float) -> str:
    rounded = round(value)
    if abs(value - rounded) < 0.05:
        return str(int(rounded))
    return f"{value:.1f}"
