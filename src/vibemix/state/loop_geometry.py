# SPDX-License-Identifier: Apache-2.0
"""Loop and beatjump geometry receipts for future live grounding.

Loops and beatjumps are one of the few DJ move classes whose musical effect can
be described from controller timing plus a beatgrid, without spectral
inference. This module does not emit events or speech. It gives the MIDI layer a
stable loop-performance vocabulary and gives future deck-context wiring a
citation-safe ``mix:`` key shape for a beatgrid-exact receipt.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from fractions import Fraction

DEFAULT_MOVE_DEDUP_WINDOW_S = 0.4
BEAT_SIZE_LATTICE: tuple[Fraction, ...] = (
    Fraction(1, 32),
    Fraction(1, 16),
    Fraction(1, 8),
    Fraction(1, 4),
    Fraction(1, 2),
    Fraction(1, 1),
    Fraction(2, 1),
    Fraction(4, 1),
    Fraction(8, 1),
    Fraction(16, 1),
    Fraction(32, 1),
    Fraction(64, 1),
)

_BEATLOOP_ROLL_RE = re.compile(r"^(?:beatloop|loop)_roll_(?P<size>.+)$")
_BEATLOOP_RE = re.compile(r"^(?:beatloop|loop)_(?P<size>.+)$")
_BEATJUMP_RE = re.compile(
    r"^beatjump_(?P<direction>fwd|forward|back|backward|rev|reverse|plus|minus|\+|-)_"
    r"(?P<size>.+)$"
)

__all__ = [
    "BEAT_SIZE_LATTICE",
    "DEFAULT_MOVE_DEDUP_WINDOW_S",
    "LoopControl",
    "beatgrid_exact_atom",
    "inside_move_dedup_window",
    "is_loop_control_kind",
    "loop_move_label",
    "loop_size_label",
    "parse_loop_control_kind",
    "retrigger_interval_s",
]


@dataclass(frozen=True, slots=True)
class LoopControl:
    """A normalized loop/beatjump control from a controller profile."""

    action: str
    size_beats: float | None = None
    direction: int = 0


def is_loop_control_kind(kind: str) -> bool:
    """Return True for profile button kinds handled by the loop geometry path."""
    return parse_loop_control_kind(kind) is not None


def parse_loop_control_kind(kind: str) -> LoopControl | None:
    """Normalize profile button kinds such as ``beatloop_roll_1_4``.

    Existing FLX4 ``loop_in`` / ``loop_out`` kinds stay valid. Future profile
    mappings can use ``beatloop_<size>``, ``beatloop_roll_<size>``, and
    ``beatjump_fwd_<size>`` / ``beatjump_back_<size>`` where ``size`` is a beat
    count, decimal, or fraction token.
    """
    raw = _normalize_kind(kind)
    if raw == "loop_in":
        return LoopControl("loop_in")
    if raw == "loop_out":
        return LoopControl("loop_out")

    match = _BEATLOOP_ROLL_RE.match(raw)
    if match is not None:
        size = _parse_size_beats(match.group("size"))
        return LoopControl("loop_roll", float(size)) if size is not None else None

    match = _BEATJUMP_RE.match(raw)
    if match is not None:
        size = _parse_size_beats(match.group("size"))
        if size is None:
            return None
        direction = -1 if match.group("direction") in {"back", "backward", "rev", "reverse", "minus", "-"} else 1
        return LoopControl("beatjump", float(size), direction)

    match = _BEATLOOP_RE.match(raw)
    if match is not None:
        size = _parse_size_beats(match.group("size"))
        return LoopControl("beatloop", float(size)) if size is not None else None

    return None


def loop_move_label(deck: str | None, kind: str, *, play_on: bool = False) -> str | None:
    """Return the human move-ring label for a loop control kind."""
    control = parse_loop_control_kind(kind)
    if control is None:
        return None
    side = str(deck or "M").upper()
    if control.action == "loop_in":
        suffix = " (play=ON)" if play_on else ""
        return f"{side}_loop_in_hit{suffix}"
    if control.action == "loop_out":
        return f"{side}_loop_out_hit"
    if control.size_beats is None:
        return None
    label = loop_size_label(control.size_beats)
    if control.action == "loop_roll":
        return f"{side}_loop_roll:{label}"
    if control.action == "beatloop":
        return f"{side}_loop:{label}"
    if control.action == "beatjump":
        sign = "+" if control.direction >= 0 else "-"
        return f"{side}_beatjump:{sign}{label}"
    return None


def loop_size_label(size_beats: float) -> str:
    """Return a compact beat-size label for move text."""
    frac = _validated_size(size_beats)
    if frac.denominator == 1:
        return f"{frac.numerator}beat"
    return f"{frac.numerator}/{frac.denominator}beat"


def beatgrid_exact_atom(
    deck: str | None,
    action: str,
    size_beats: float,
    *,
    beat_index: int | None = None,
) -> str:
    """Return a citation-safe ``mix`` key for a beatgrid-exact loop receipt."""
    side = re.sub(r"[^A-Za-z0-9]+", "_", str(deck or "M").upper()).strip("_") or "M"
    clean_action = re.sub(r"[^a-z0-9]+", "_", str(action or "loop").lower()).strip("_") or "loop"
    size = _safe_size_token(size_beats)
    fields = [f"loop_boundary_beatgrid_exact=deck_{side}", clean_action, size]
    if beat_index is not None:
        fields.append(f"beat_{int(beat_index)}")
    return ":".join(fields)


def retrigger_interval_s(size_beats: float, bpm: float) -> float | None:
    """Return seconds between retriggers for a beat-sized roll, or ``None``."""
    try:
        size = float(size_beats)
        tempo = float(bpm)
    except (TypeError, ValueError):
        return None
    if not (math.isfinite(size) and math.isfinite(tempo)) or size <= 0.0 or tempo <= 0.0:
        return None
    return 60.0 / tempo * size


def inside_move_dedup_window(
    size_beats: float,
    bpm: float,
    *,
    window_s: float = DEFAULT_MOVE_DEDUP_WINDOW_S,
) -> bool:
    """Return True when a loop roll can retrigger inside the move dedup window."""
    interval = retrigger_interval_s(size_beats, bpm)
    return interval is not None and interval < window_s


def _normalize_kind(kind: str) -> str:
    return str(kind or "").strip().lower().replace("-", "_").replace(" ", "_")


def _parse_size_beats(raw: str) -> Fraction | None:
    token = str(raw or "").strip().lower()
    token = token.replace("beats", "").replace("beat", "").strip("_")
    if not token:
        return None
    try:
        if "/" in token:
            value = Fraction(token)
        elif re.fullmatch(r"\d+_\d+", token):
            first, second = token.split("_", 1)
            value = Fraction(int(first), int(second))
        else:
            value = Fraction(token.replace("p", ".").replace("_", "."))
    except (ValueError, ZeroDivisionError):
        return None
    if value <= 0:
        return None
    return value


def _validated_size(size_beats: float) -> Fraction:
    try:
        raw = float(size_beats)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"size_beats must be finite and > 0, got {size_beats!r}") from exc
    if not math.isfinite(raw) or raw <= 0.0:
        raise ValueError(f"size_beats must be finite and > 0, got {size_beats!r}")
    frac = Fraction(raw).limit_denominator(64)
    if not math.isclose(float(frac), raw, rel_tol=1e-9, abs_tol=1e-9):
        frac = Fraction(round(raw * 1000), 1000)
    return frac


def _safe_size_token(size_beats: float) -> str:
    return loop_size_label(size_beats).replace("/", "_")
