# SPDX-License-Identifier: Apache-2.0
"""Deterministic section-to-section transition slate scorer."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, replace
from typing import Literal

import numpy as np

from vibemix.intel.musical_ontology import (
    clamp01,
    normalize_role,
    risk_penalty,
    role_pair_risks,
    role_pair_score,
)
from vibemix.state import harmonics

RuntimeMode = Literal["prep", "live"]

SCORE_WEIGHTS: dict[str, float] = {
    "semantic": 0.24,
    "harmonic": 0.16,
    "bpm": 0.12,
    "energy_shape": 0.12,
    "role": 0.13,
    "phrase_alignment": 0.09,
    "cue_operability": 0.07,
    "taste": 0.05,
    "novelty": 0.02,
}

PREP_SECTION_CONFIDENCE_FLOOR = 0.35
LIVE_SECTION_CONFIDENCE_FLOOR = 0.55
LIVE_SELECT_CONFIDENCE_FLOOR = 0.62
EXACT_TIMING_CONFIDENCE_FLOOR = 0.80
MIN_USABLE_SECTION_SECONDS = 4.0


@dataclass(frozen=True, slots=True)
class SectionRecord:
    """A compact section row consumed by the scorer.

    This mirrors the INTEL section contract without depending on a future
    section-store implementation. The scorer accepts these already-grounded
    records and never resolves files, audio, or library state itself.
    """

    section_id: str
    track_id: str
    role: str
    source: str = "fallback"
    source_detail: str | None = None
    confidence: float = 1.0
    start_s: float = 0.0
    end_s: float = 0.0
    start_beat: int | None = None
    end_beat: int | None = None
    bar_count: float | None = None
    bpm: float | None = None
    camelot: str | None = None
    energy_start: float | None = None
    energy_end: float | None = None
    energy_mean: float | None = None
    cue_slot: str | None = None
    cue_source: str | None = None
    cue_confidence: float | None = None
    tags: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class LivePosition:
    """Live timing facts that gate exact bars without owning MusicState."""

    remaining_bars: int | None = None
    playhead_confidence: float = 0.0
    blend_active: bool = False


@dataclass(frozen=True, slots=True)
class TransitionScoringInput:
    source: SectionRecord
    destinations: tuple[SectionRecord, ...]
    source_vector: np.ndarray | None = None
    destination_vectors: dict[str, np.ndarray] | None = None
    semantic_basis_by_section: dict[str, str] | None = None
    played_track_ids: frozenset[str] = frozenset()
    candidate_pool_track_ids: frozenset[str] | None = None
    genre_profile: str | None = None
    live_position: LivePosition | None = None
    mode: RuntimeMode = "prep"
    taste_scores: dict[tuple[str, str], float] | None = None


@dataclass(frozen=True, slots=True)
class TransitionScoreComponents:
    semantic: float
    harmonic: float
    bpm: float
    energy_shape: float
    role: float
    phrase_alignment: float
    cue_operability: float
    taste: float
    novelty: float
    risk_penalty: float


@dataclass(frozen=True, slots=True)
class TransitionCandidate:
    candidate_id: str
    transition_key: str
    from_section_id: str
    to_section_id: str
    from_track_id: str
    to_track_id: str
    from_role: str
    to_role: str
    from_start_s: float
    from_end_s: float
    to_start_s: float
    to_end_s: float
    from_bpm: float | None
    to_bpm: float | None
    from_camelot: str | None
    to_camelot: str | None
    cue_slot: str | None
    start_in_bars: int | None
    score: float
    confidence: float
    semantic_basis: str
    components: TransitionScoreComponents
    risk_flags: tuple[str, ...]
    reasons: tuple[str, ...]


def score_transition_slate(
    scoring_input: TransitionScoringInput,
    *,
    max_candidates: int = 5,
    strategy_version: str = "v1-section-transition-score",
) -> tuple[TransitionCandidate, ...]:
    """Score a bounded section-to-section transition slate.

    The result is deterministic, conservative, and grounded only in the supplied
    section objects. Missing facts become neutral components plus risk flags;
    they are never invented.
    """
    if max_candidates <= 0:
        return ()
    drafts: list[TransitionCandidate] = []
    for destination in scoring_input.destinations:
        if _hard_filtered(scoring_input, destination):
            continue
        draft = _score_one(scoring_input, destination, strategy_version)
        if draft is None:
            continue
        drafts.append(draft)

    drafts.sort(key=_candidate_sort_key)
    selected = _select_diverse(drafts, scoring_input.mode, max_candidates)
    return tuple(
        replace(candidate, candidate_id=f"tr_{index:03d}")
        for index, candidate in enumerate(selected, start=1)
    )


def harmonic_score(src: str | None, dst: str | None) -> tuple[float, tuple[str, ...]]:
    """Grade Camelot compatibility without asking a model to do key math."""
    a = _camelot_parts(src)
    b = _camelot_parts(dst)
    if a is None or b is None:
        return 0.55, ("key_unknown",)

    (src_number, src_letter), (dst_number, dst_letter) = a, b
    if src_number == dst_number and src_letter == dst_letter:
        return 1.0, ()
    if src_number == dst_number and src_letter != dst_letter:
        return 0.92, ()
    if src_letter == dst_letter:
        distance = _hour_distance(src_number, dst_number)
        if distance == 1:
            return 0.88, ()
        if distance == 2:
            return 0.78, ()
        if harmonics.is_clash(src, dst):
            return 0.12, ("harmonic_clash",)
        return 0.42, ("harmonic_drift",)
    if _hour_distance(src_number, dst_number) == 1:
        return 0.72, ()
    return 0.42, ("harmonic_drift",)


def bpm_score(src: float | None, dst: float | None) -> tuple[float, tuple[str, ...]]:
    """Grade tempo compatibility from deterministic BPM metadata."""
    if src is None or dst is None or src <= 0 or dst <= 0:
        return 0.55, ("bpm_unknown",)
    delta = abs(dst - src) / src
    if delta <= 0.015:
        return 1.0, ()
    if delta <= 0.03:
        return 0.90, ()
    if delta <= 0.06:
        return 0.78, ()
    if delta <= 0.08:
        return 0.58, ("tempo_push",)
    if delta <= 0.12:
        return 0.35, ("tempo_jump",)
    return 0.10, ("tempo_jump",)


def phrase_alignment_score(
    section: SectionRecord,
    live_position: LivePosition | None = None,
    *,
    mode: RuntimeMode = "prep",
) -> tuple[float, tuple[str, ...]]:
    """Grade phrase cleanliness from beat/bar metadata."""
    flags: list[str] = []
    if mode == "live" and live_position is not None:
        if live_position.blend_active:
            flags.append("blend_active")
        if live_position.playhead_confidence < EXACT_TIMING_CONFIDENCE_FLOOR:
            flags.append("timing_low_confidence")
    if section.bar_count is not None and section.bar_count < 4:
        flags.append("phrase_short")
    if section.start_beat is None:
        flags.append("phrase_unknown")
        return 0.50, tuple(flags)

    beat = max(0, int(section.start_beat))
    if beat % 128 == 0:
        return 1.0, tuple(flags)
    if beat % 64 == 0:
        return 1.0, tuple(flags)
    if beat % 32 == 0:
        return 0.82, tuple(flags)
    if beat % 16 == 0:
        return 0.62, tuple(flags)
    if beat % 4 == 0:
        flags.append("off_phrase")
        return 0.42, tuple(flags)
    flags.append("off_phrase")
    return 0.10, tuple(flags)


def cue_operability_score(section: SectionRecord) -> tuple[float, tuple[str, ...]]:
    """Grade whether the destination has a practical cue handle."""
    flags: list[str] = []
    source = (section.cue_source or section.source or "").lower()
    if section.cue_slot:
        if source == "dj":
            score = 1.0
        elif source == "anlz":
            score = 0.82
        elif source == "auto":
            score = 0.65
            flags.append("auto_cue_review")
        elif source == "fallback":
            score = 0.25
            flags.append("fallback_entry")
        else:
            score = 0.52
    else:
        score = 0.52
        flags.append("no_cue_slot")

    if normalize_role(section.role) in {"intro", "groove"} and section.start_s <= 64.0:
        score += 0.08
    if section.bar_count is not None and section.bar_count < 16:
        score -= 0.15
        flags.append("short_entry_window")
    if section.cue_confidence is not None and section.cue_confidence < 0.5:
        score -= 0.20
        flags.append("auto_cue_review")
    return clamp01(score), tuple(dict.fromkeys(flags))


def role_score(
    src_role: str | None, dst_role: str | None, genre_profile: str | None = None
) -> tuple[float, tuple[str, ...]]:
    """Grade transition-role grammar and return role-implied risks."""
    return role_pair_score(src_role, dst_role, genre_profile), role_pair_risks(src_role, dst_role)


def _score_one(
    scoring_input: TransitionScoringInput,
    destination: SectionRecord,
    strategy_version: str,
) -> TransitionCandidate | None:
    source = scoring_input.source
    destination_vectors = scoring_input.destination_vectors or {}
    semantic, semantic_flags = _semantic_score(
        scoring_input.source_vector, destination_vectors.get(destination.section_id)
    )
    harmonic, harmonic_flags = harmonic_score(source.camelot, destination.camelot)
    bpm, bpm_flags = bpm_score(source.bpm, destination.bpm)
    energy_shape, energy_flags = _energy_shape_score(source, destination)
    role, role_flags = role_score(source.role, destination.role, scoring_input.genre_profile)
    phrase, phrase_flags = phrase_alignment_score(
        destination,
        scoring_input.live_position,
        mode=scoring_input.mode,
    )
    cue, cue_flags = cue_operability_score(destination)
    taste = _taste_score(scoring_input, destination)
    novelty = _novelty_score(scoring_input, destination)

    risk_flags = _dedupe_flags(
        semantic_flags
        + harmonic_flags
        + bpm_flags
        + energy_flags
        + role_flags
        + phrase_flags
        + cue_flags
    )
    if _severe_live_suppressor(scoring_input, destination, harmonic, bpm, risk_flags):
        return None
    penalty = risk_penalty(risk_flags)
    components = TransitionScoreComponents(
        semantic=semantic,
        harmonic=harmonic,
        bpm=bpm,
        energy_shape=energy_shape,
        role=role,
        phrase_alignment=phrase,
        cue_operability=cue,
        taste=taste,
        novelty=novelty,
        risk_penalty=penalty,
    )
    score = _weighted_score(components)
    confidence = _transition_confidence(scoring_input, destination, components, risk_flags)
    if scoring_input.mode == "live" and confidence < LIVE_SELECT_CONFIDENCE_FLOOR:
        return None

    cue_slot = destination.cue_slot
    start_in_bars = _start_in_bars(scoring_input, phrase)
    transition_key = _transition_key(
        strategy_version,
        scoring_input.mode,
        source.section_id,
        destination.section_id,
        cue_slot,
    )
    return TransitionCandidate(
        candidate_id="",
        transition_key=transition_key,
        from_section_id=source.section_id,
        to_section_id=destination.section_id,
        from_track_id=source.track_id,
        to_track_id=destination.track_id,
        from_role=normalize_role(source.role),
        to_role=normalize_role(destination.role),
        from_start_s=float(source.start_s),
        from_end_s=float(source.end_s),
        to_start_s=float(destination.start_s),
        to_end_s=float(destination.end_s),
        from_bpm=source.bpm,
        to_bpm=destination.bpm,
        from_camelot=source.camelot,
        to_camelot=destination.camelot,
        cue_slot=cue_slot,
        start_in_bars=start_in_bars,
        score=score,
        confidence=confidence,
        semantic_basis=_semantic_basis(scoring_input, destination, risk_flags),
        components=components,
        risk_flags=risk_flags,
        reasons=_reasons(source, destination, components, risk_flags),
    )


def _hard_filtered(scoring_input: TransitionScoringInput, destination: SectionRecord) -> bool:
    source = scoring_input.source
    if destination.section_id == source.section_id:
        return True
    if scoring_input.mode == "live" and destination.track_id == source.track_id:
        return True
    if destination.track_id in scoring_input.played_track_ids:
        return True
    if (
        scoring_input.candidate_pool_track_ids is not None
        and destination.track_id not in scoring_input.candidate_pool_track_ids
    ):
        return True
    if scoring_input.mode == "live" and normalize_role(destination.role) == "unknown":
        return True
    floor = (
        LIVE_SECTION_CONFIDENCE_FLOOR
        if scoring_input.mode == "live"
        else PREP_SECTION_CONFIDENCE_FLOOR
    )
    if source.confidence < floor or destination.confidence < floor:
        return True
    duration = destination.end_s - destination.start_s
    return duration > 0 and duration < MIN_USABLE_SECTION_SECONDS


def _semantic_score(
    source_vector: np.ndarray | None, destination_vector: np.ndarray | None
) -> tuple[float, tuple[str, ...]]:
    if source_vector is None or destination_vector is None:
        return 0.50, ("semantic_unknown",)
    src = np.asarray(source_vector, dtype=np.float32)
    dst = np.asarray(destination_vector, dtype=np.float32)
    src_norm = float(np.linalg.norm(src))
    dst_norm = float(np.linalg.norm(dst))
    if src_norm <= 1e-12 or dst_norm <= 1e-12:
        return 0.50, ("semantic_unknown",)
    if src.shape != dst.shape:
        return 0.50, ("semantic_unknown", "semantic_dim_mismatch")
    cosine = float(np.dot(src / src_norm, dst / dst_norm))
    return clamp01((cosine + 1.0) / 2.0), ()


def _semantic_basis(
    scoring_input: TransitionScoringInput,
    destination: SectionRecord,
    risk_flags: tuple[str, ...],
) -> str:
    if "semantic_unknown" in risk_flags:
        return "semantic_unknown"
    basis_by_section = scoring_input.semantic_basis_by_section or {}
    source_basis = basis_by_section.get(scoring_input.source.section_id)
    destination_basis = basis_by_section.get(destination.section_id)
    bases = {source_basis or "vector", destination_basis or "vector"}
    if bases == {"section_vector"}:
        return "section_vector"
    if "section_vector" in bases and "track_vector_fallback" in bases:
        return "mixed_section_track"
    if bases == {"track_vector_fallback"}:
        return "track_vector_fallback"
    return "vector"


def _energy_shape_score(
    source: SectionRecord, destination: SectionRecord
) -> tuple[float, tuple[str, ...]]:
    if source.energy_mean is None or destination.energy_mean is None:
        return 0.50, ("energy_unknown",)
    energy_delta = destination.energy_mean - source.energy_mean
    desired = _desired_energy_delta(source.role, destination.role)
    score = 1.0 - clamp01(abs(energy_delta - desired) / 60.0)
    flags: list[str] = []
    if energy_delta < -35.0 or energy_delta > 45.0:
        flags.append("energy_cliff")
    return clamp01(score), tuple(flags)


def _desired_energy_delta(from_role: str | None, to_role: str | None) -> float:
    src = normalize_role(from_role)
    dst = normalize_role(to_role)
    table = {
        ("outro", "intro"): 0.0,
        ("outro", "groove"): 5.0,
        ("groove", "build"): 15.0,
        ("build", "drop"): 30.0,
        ("breakdown", "build"): 20.0,
        ("breakdown", "drop"): 30.0,
        ("drop", "breakdown"): -20.0,
        ("drop", "intro"): -20.0,
        ("drop", "groove"): -10.0,
        ("drop", "drop"): 5.0,
    }
    return table.get((src, dst), 0.0)


def _taste_score(scoring_input: TransitionScoringInput, destination: SectionRecord) -> float:
    if not scoring_input.taste_scores:
        return 0.50
    key = (normalize_role(scoring_input.source.role), normalize_role(destination.role))
    return clamp01(scoring_input.taste_scores.get(key, 0.50))


def _novelty_score(scoring_input: TransitionScoringInput, destination: SectionRecord) -> float:
    if destination.track_id in scoring_input.played_track_ids:
        return 0.20
    if scoring_input.candidate_pool_track_ids and destination.track_id in (
        scoring_input.candidate_pool_track_ids
    ):
        return 0.70
    return 0.50


def _weighted_score(components: TransitionScoreComponents) -> float:
    base = (
        SCORE_WEIGHTS["semantic"] * components.semantic
        + SCORE_WEIGHTS["harmonic"] * components.harmonic
        + SCORE_WEIGHTS["bpm"] * components.bpm
        + SCORE_WEIGHTS["energy_shape"] * components.energy_shape
        + SCORE_WEIGHTS["role"] * components.role
        + SCORE_WEIGHTS["phrase_alignment"] * components.phrase_alignment
        + SCORE_WEIGHTS["cue_operability"] * components.cue_operability
        + SCORE_WEIGHTS["taste"] * components.taste
        + SCORE_WEIGHTS["novelty"] * components.novelty
        - components.risk_penalty
    )
    return round(clamp01(base), 6)


def _transition_confidence(
    scoring_input: TransitionScoringInput,
    destination: SectionRecord,
    components: TransitionScoreComponents,
    risk_flags: tuple[str, ...],
) -> float:
    source = scoring_input.source
    source_confidence_min = min(clamp01(source.confidence), clamp01(destination.confidence))
    section_role_confidence_min = (
        0.50
        if "role_unknown" in risk_flags
        else min(clamp01(source.confidence), clamp01(destination.confidence))
    )
    vector_presence_confidence = 1.0
    if "semantic_unknown" in risk_flags:
        vector_presence_confidence = 0.50 if scoring_input.source_vector is None else 0.65
    metadata_confidence = _metadata_confidence(source, destination)
    phrase_confidence = 0.50 if "phrase_unknown" in risk_flags else components.phrase_alignment
    live_position_confidence = (
        clamp01(scoring_input.live_position.playhead_confidence)
        if scoring_input.mode == "live" and scoring_input.live_position is not None
        else 1.0
    )
    cue_confidence = components.cue_operability
    confidence = (
        0.22 * source_confidence_min
        + 0.18 * section_role_confidence_min
        + 0.16 * vector_presence_confidence
        + 0.14 * metadata_confidence
        + 0.14 * phrase_confidence
        + 0.10 * live_position_confidence
        + 0.06 * cue_confidence
    )
    return round(clamp01(confidence - components.risk_penalty * 0.10), 6)


def _metadata_confidence(source: SectionRecord, destination: SectionRecord) -> float:
    key_known = source.camelot is not None and destination.camelot is not None
    bpm_known = (
        source.bpm is not None
        and source.bpm > 0
        and destination.bpm is not None
        and destination.bpm > 0
    )
    if key_known and bpm_known:
        return 1.0
    if key_known or bpm_known:
        return 0.70
    return 0.45


def _start_in_bars(scoring_input: TransitionScoringInput, phrase_score: float) -> int | None:
    live = scoring_input.live_position
    if scoring_input.mode != "live" or live is None:
        return None
    if live.playhead_confidence < EXACT_TIMING_CONFIDENCE_FLOOR or live.blend_active:
        return None
    if phrase_score < 0.62 or live.remaining_bars is None:
        return None
    return max(0, int(live.remaining_bars))


def _severe_live_suppressor(
    scoring_input: TransitionScoringInput,
    destination: SectionRecord,
    harmonic: float,
    bpm: float,
    risk_flags: tuple[str, ...],
) -> bool:
    if scoring_input.mode != "live":
        return False
    if "harmonic_clash" in risk_flags and _melodic_sensitive(scoring_input.source, destination):
        return True
    return "tempo_jump" in risk_flags and bpm <= 0.10


def _melodic_sensitive(source: SectionRecord, destination: SectionRecord) -> bool:
    if "percussive" in source.tags and "percussive" in destination.tags:
        return False
    sensitive_roles = {"build", "breakdown", "drop"}
    return normalize_role(source.role) in sensitive_roles or normalize_role(destination.role) in (
        sensitive_roles
    )


def _reasons(
    source: SectionRecord,
    destination: SectionRecord,
    components: TransitionScoreComponents,
    risk_flags: tuple[str, ...],
) -> tuple[str, ...]:
    positives: list[str] = []
    if components.role >= 0.80:
        positives.append(
            f"{normalize_role(source.role)} into {normalize_role(destination.role)} "
            "is a strong role pair"
        )
    if components.semantic >= 0.78 and "semantic_unknown" not in risk_flags:
        positives.append("section texture is close")
    if components.harmonic >= 0.88 and "key_unknown" not in risk_flags:
        positives.append("Camelot relationship is clean")
    if components.bpm >= 0.78 and "bpm_unknown" not in risk_flags:
        positives.append("tempo delta is workable")
    if components.phrase_alignment >= 0.82:
        positives.append("entry lands on a phrase boundary")
    if components.cue_operability >= 0.82:
        positives.append("destination has a reliable cue")

    risk_reasons = {
        "harmonic_clash": "keys clash if both melodic layers overlap",
        "tempo_jump": "tempo jump needs a bridge or quick cut",
        "off_phrase": "entry is not phrase-clean",
        "no_cue_slot": "good section, but no exported cue slot yet",
        "semantic_unknown": "section texture is not embedded yet",
        "semantic_dim_mismatch": "section texture vectors are not comparable yet",
        "timing_low_confidence": "timing is not locked, so exact bars are withheld",
    }
    ordered_risks = [risk_reasons[flag] for flag in risk_flags if flag in risk_reasons]
    return tuple(positives[:2] + ordered_risks[:2])


def _select_diverse(
    candidates: list[TransitionCandidate],
    mode: RuntimeMode,
    max_candidates: int,
) -> list[TransitionCandidate]:
    per_track_limit = 1 if mode == "live" else 3
    per_track: dict[str, int] = {}
    used_sections: set[str] = set()
    selected: list[TransitionCandidate] = []
    for candidate in candidates:
        if candidate.to_section_id in used_sections:
            continue
        count = per_track.get(candidate.to_track_id, 0)
        if count >= per_track_limit:
            continue
        selected.append(candidate)
        used_sections.add(candidate.to_section_id)
        per_track[candidate.to_track_id] = count + 1
        if len(selected) >= max_candidates:
            break
    return selected


def _candidate_sort_key(candidate: TransitionCandidate) -> tuple[float, float, float, float, str]:
    return (
        -candidate.score,
        -candidate.confidence,
        candidate.components.risk_penalty,
        _cue_sort_seconds(candidate),
        candidate.transition_key,
    )


def _cue_sort_seconds(candidate: TransitionCandidate) -> float:
    return candidate.to_start_s


def _transition_key(
    strategy_version: str,
    mode: RuntimeMode,
    from_section_id: str,
    to_section_id: str,
    cue_slot: str | None,
) -> str:
    raw = "|".join([strategy_version, mode, from_section_id, to_section_id, cue_slot or ""]).encode(
        "utf-8"
    )
    return hashlib.sha256(raw).hexdigest()[:16]


def _camelot_parts(raw: str | None) -> tuple[int, str] | None:
    code = harmonics.to_camelot(raw)
    if code is None:
        return None
    return int(code[:-1]), code[-1]


def _hour_distance(a: int, b: int) -> int:
    distance = abs(a - b) % 12
    return min(distance, 12 - distance)


def _dedupe_flags(flags: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(flag for flag in flags if flag))


__all__ = [
    "EXACT_TIMING_CONFIDENCE_FLOOR",
    "LIVE_SECTION_CONFIDENCE_FLOOR",
    "LIVE_SELECT_CONFIDENCE_FLOOR",
    "PREP_SECTION_CONFIDENCE_FLOOR",
    "SCORE_WEIGHTS",
    "LivePosition",
    "RuntimeMode",
    "SectionRecord",
    "TransitionCandidate",
    "TransitionScoreComponents",
    "TransitionScoringInput",
    "bpm_score",
    "cue_operability_score",
    "harmonic_score",
    "phrase_alignment_score",
    "role_score",
    "score_transition_slate",
]
