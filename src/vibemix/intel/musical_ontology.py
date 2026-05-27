# SPDX-License-Identifier: Apache-2.0
"""Canonical section roles and transition grammar for set-aware mix points."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

SectionRole = Literal[
    "intro",
    "groove",
    "build",
    "breakdown",
    "drop",
    "outro",
    "bridge",
    "unknown",
]

VALID_ROLES: frozenset[str] = frozenset(
    {"intro", "groove", "build", "breakdown", "drop", "outro", "bridge", "unknown"}
)

ROLE_PAIR_BASE: dict[tuple[str, str], float] = {
    ("outro", "intro"): 0.95,
    ("outro", "groove"): 0.88,
    ("groove", "intro"): 0.78,
    ("groove", "groove"): 0.72,
    ("groove", "build"): 0.76,
    ("build", "drop"): 0.84,
    ("build", "intro"): 0.58,
    ("build", "breakdown"): 0.52,
    ("breakdown", "intro"): 0.68,
    ("breakdown", "build"): 0.74,
    ("breakdown", "drop"): 0.82,
    ("drop", "intro"): 0.64,
    ("drop", "groove"): 0.70,
    ("drop", "drop"): 0.62,
    ("drop", "breakdown"): 0.56,
    ("intro", "intro"): 0.45,
    ("intro", "drop"): 0.50,
}

ROLE_PAIR_RISKS: dict[tuple[str, str], tuple[str, ...]] = {
    ("drop", "drop"): ("drop_stack_fatigue",),
    ("drop", "breakdown"): ("energy_drop_unplanned",),
    ("breakdown", "intro"): ("energy_drop_unplanned",),
}

GENRE_ROLE_ADJUSTMENTS: dict[str, dict[tuple[str, str], float]] = {
    "techno": {
        ("outro", "groove"): 0.08,
        ("groove", "groove"): 0.08,
        ("groove", "build"): 0.04,
        ("drop", "groove"): 0.05,
        ("drop", "drop"): -0.04,
        ("breakdown", "intro"): -0.04,
    },
    "hardtek": {
        ("outro", "groove"): 0.08,
        ("groove", "groove"): 0.08,
        ("groove", "build"): 0.04,
        ("drop", "groove"): 0.05,
        ("drop", "drop"): -0.04,
        ("breakdown", "intro"): -0.04,
    },
    "hard_tek": {
        ("outro", "groove"): 0.08,
        ("groove", "groove"): 0.08,
        ("groove", "build"): 0.04,
        ("drop", "groove"): 0.05,
        ("drop", "drop"): -0.04,
        ("breakdown", "intro"): -0.04,
    },
    "house": {
        ("outro", "intro"): 0.05,
        ("breakdown", "build"): 0.05,
        ("build", "drop"): 0.06,
        ("drop", "drop"): -0.08,
    },
    "disco": {
        ("outro", "intro"): 0.08,
        ("groove", "groove"): 0.04,
        ("breakdown", "intro"): 0.03,
        ("drop", "drop"): -0.10,
    },
    "drum_and_bass": {
        ("breakdown", "drop"): 0.08,
        ("build", "drop"): 0.08,
        ("drop", "drop"): 0.04,
        ("outro", "intro"): 0.04,
    },
    "dnb": {
        ("breakdown", "drop"): 0.08,
        ("build", "drop"): 0.08,
        ("drop", "drop"): 0.04,
        ("outro", "intro"): 0.04,
    },
    "psytrance": {
        ("groove", "groove"): 0.06,
        ("build", "drop"): 0.05,
        ("breakdown", "build"): 0.06,
        ("drop", "drop"): -0.06,
    },
    "pop": {
        ("intro", "drop"): 0.05,
        ("breakdown", "drop"): 0.08,
        ("outro", "intro"): 0.04,
        ("drop", "drop"): -0.12,
    },
}

RISK_PENALTIES: dict[str, float] = {
    "harmonic_clash": 0.30,
    "tempo_jump": 0.24,
    "off_phrase": 0.20,
    "timing_low_confidence": 0.18,
    "short_entry_window": 0.15,
    "fallback_entry": 0.14,
    "energy_cliff": 0.12,
    "tempo_push": 0.10,
    "semantic_unknown": 0.08,
    "harmonic_drift": 0.08,
    "role_unknown": 0.08,
    "drop_stack_fatigue": 0.07,
    "energy_drop_unplanned": 0.07,
    "no_cue_slot": 0.07,
    "bpm_unknown": 0.06,
    "key_unknown": 0.06,
    "phrase_unknown": 0.06,
    "energy_unknown": 0.05,
    "auto_cue_review": 0.04,
}


@dataclass(frozen=True, slots=True)
class RoleSemantics:
    role: str
    mix_in_score: float
    mix_out_score: float
    energy_expectation: str
    tonal_sensitivity: str
    language_floor: float


@dataclass(frozen=True, slots=True)
class TransitionGrammarRule:
    from_role: str
    to_role: str
    base_score: float
    risk_flags: tuple[str, ...]
    explanation_bits: tuple[str, ...]


def clamp01(value: float) -> float:
    """Clamp a finite-ish score to the scorer's normalized range."""
    if value != value:
        return 0.0
    return max(0.0, min(1.0, float(value)))


def normalize_genre(genre_profile: str | None) -> str | None:
    """Normalize a genre profile name for policy lookup."""
    if not genre_profile:
        return None
    normalized = genre_profile.strip().lower().replace("-", "_").replace(" ", "_")
    if normalized in {"tech_house", "deep_house"}:
        return "house"
    if normalized in {"jungle", "neurofunk"}:
        return "drum_and_bass"
    if normalized in {"goa", "full_on"}:
        return "psytrance"
    if normalized in {"nu_disco", "funk"}:
        return "disco"
    if normalized in {"hard_tek", "hardtek", "acidcore"}:
        return "hard_tek"
    return normalized


def normalize_role(role: str | None) -> str:
    """Return a canonical section role, or ``unknown`` when unsupported."""
    if not role:
        return "unknown"
    normalized = role.strip().lower()
    return normalized if normalized in VALID_ROLES else "unknown"


def role_pair_score(from_role: str | None, to_role: str | None, genre_profile: str | None) -> float:
    """Return the deterministic role-pair score after genre adjustment."""
    src = normalize_role(from_role)
    dst = normalize_role(to_role)
    if src == "unknown" or dst == "unknown":
        return 0.35
    base = ROLE_PAIR_BASE.get((src, dst), 0.35)
    genre = normalize_genre(genre_profile)
    adjustment = GENRE_ROLE_ADJUSTMENTS.get(genre or "", {}).get((src, dst), 0.0)
    return clamp01(base + adjustment)


def role_pair_risks(from_role: str | None, to_role: str | None) -> tuple[str, ...]:
    """Return canonical risk flags implied by a role pair."""
    src = normalize_role(from_role)
    dst = normalize_role(to_role)
    flags: list[str] = []
    if src == "unknown" or dst == "unknown":
        flags.append("role_unknown")
    flags.extend(ROLE_PAIR_RISKS.get((src, dst), ()))
    return tuple(flags)


def risk_penalty(flags: tuple[str, ...] | list[str] | set[str]) -> float:
    """Accumulate risk penalties with the INTEL-11 cap."""
    total = sum(RISK_PENALTIES.get(flag, 0.0) for flag in set(flags))
    return clamp01(min(0.55, total))


__all__ = [
    "GENRE_ROLE_ADJUSTMENTS",
    "RISK_PENALTIES",
    "ROLE_PAIR_BASE",
    "ROLE_PAIR_RISKS",
    "VALID_ROLES",
    "RoleSemantics",
    "SectionRole",
    "TransitionGrammarRule",
    "clamp01",
    "normalize_genre",
    "normalize_role",
    "risk_penalty",
    "role_pair_risks",
    "role_pair_score",
]
