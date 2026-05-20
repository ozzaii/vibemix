# SPDX-License-Identifier: Apache-2.0
"""Grounded DSP genre auto-detector (Phase 52 / GENRE-01).

Picks the active ``GenreProfile`` from the features ALREADY computed each tick —
stabilized BPM + band shares (sub/low/mid/high) + crest factor — by scoring
nearest-match across the profile library. Pure numpy on existing features: no
CLAP/MERT/OpenL3, no new heavy deps, zero per-tick API cost (Critical
Constraint 6 + [[feedback_no_clap_use_gemini_embedding]]).

Anti-slop ([[project_anti_slop_grounded_gemini_thesis]]) is non-negotiable:

  1. **Confidence gate + ``unknown`` fallback.** If no profile clears
     ``GENRE_CONFIDENCE_MIN``, OR the best beats the runner-up by less than
     ``GENRE_TIE_MARGIN``, the detector returns ``("unknown", best_conf)`` —
     NEVER a false-confident guess. Mirrors ``derive_audible_track``'s
     unsure/unknown pattern.
  2. **Hysteresis.** ``GenreHysteresis`` + ``apply_genre_hysteresis`` debounce
     profile switches with an N-tick dwell so the detected genre does not
     flicker bar-to-bar. ``unknown`` commits immediately (like ``silent`` in
     the phase ``HysteresisState``) — when we lose confidence we say so at once.
  3. **Env override wins.** ``set_auto_enabled(False)`` (set in ``__main__`` when
     the user explicitly pinned ``VIBEMIX_GENRE_PROFILE``) makes ``_tick_once``
     SCORE but NOT re-point the active profile. Honesty fields
     (``detected_genre``/``genre_confidence``) are surfaced either way.

Scoring (grounded, per profile, each axis in [0, 1]):
  - **BPM axis:** 1.0 inside ``bpm_range``; else linear falloff by distance to
    the nearest edge over ``_BPM_TOLERANCE``, floored at 0. ``bpm <= 0`` → 0
    (no BPM lock — anti-hallucination).
  - **Band axis:** per band, midpoint-proximity ``max(0, 1 - |obs - mid| /
    _BAND_TOLERANCE)`` — rewards being NEAR the profile centre, not merely
    in-range. Critical: psytrance's band ranges are a SUBSET of techno's, so a
    pure membership test cannot separate them (the exact misclassification
    bug). Midpoint distance does. Average the 4 bands.
  - **Crest axis:** 1.0 inside ``expected_crest_factor``; else falloff over
    ``_CREST_TOLERANCE``. ``crest <= 0`` → neutral 0.5 (a missing crest must
    not dominate).
  - **Confidence = weighted mean** (BPM 0.4, bands 0.4, crest 0.2 — BPM + bands
    are the strongest psy-vs-techno discriminators).
"""

from __future__ import annotations

from dataclasses import dataclass

from vibemix.state.genre.profile import GenreProfile

# --- Anti-slop gate constants (load-bearing) ---
# Below this, the best profile is not trusted -> "unknown" (no false confidence).
GENRE_CONFIDENCE_MIN = 0.55
# If best - second_best < this, the two are too close to call -> "unknown".
GENRE_TIE_MARGIN = 0.08

# --- Scoring tolerances ---
# BPM falloff window outside the profile band (BPM). 10 BPM ~= one half-bar of
# drift; beyond it the tempo is clearly a different genre.
_BPM_TOLERANCE = 12.0
# Band-share midpoint tolerance. Tight enough to separate psytrance (subset of
# techno's ranges) by centre distance — at this width the psy/techno midpoint
# lead is 0.106 > GENRE_TIE_MARGIN so each scores itself — loose enough not to
# punish normal per-tick band jitter.
_BAND_TOLERANCE = 0.08
# Crest factor falloff window outside the profile band.
_CREST_TOLERANCE = 3.0

# Axis weights — BPM + bands carry the discrimination; crest is a tie-breaker.
_W_BPM = 0.4
_W_BANDS = 0.4
_W_CREST = 0.2

# N-tick dwell before a genre switch commits (mirrors phase HysteresisState's 3).
_HYSTERESIS_DWELL_TICKS = 3

_BANDS = ("sub", "low", "mid", "high")


def _bpm_axis(bpm: float, profile: GenreProfile) -> float:
    """1.0 inside bpm_range; linear falloff over _BPM_TOLERANCE; 0 if no lock."""
    if bpm <= 0:
        return 0.0
    lo, hi = profile.bpm_range
    if lo <= bpm <= hi:
        return 1.0
    dist = (lo - bpm) if bpm < lo else (bpm - hi)
    return max(0.0, 1.0 - dist / _BPM_TOLERANCE)


def _band_axis(bands: dict[str, float], profile: GenreProfile) -> float:
    """Average midpoint-proximity over the 4 bands. Rewards closeness to the
    profile's band centre — the only axis that can separate subset-overlapping
    profiles (psytrance vs techno)."""
    scores: list[float] = []
    for b in _BANDS:
        obs = float(bands.get(b, 0.0))
        lo, hi = profile.band_signature[b]
        mid = (lo + hi) / 2.0
        scores.append(max(0.0, 1.0 - abs(obs - mid) / _BAND_TOLERANCE))
    return sum(scores) / len(scores)


def _crest_axis(crest: float, profile: GenreProfile) -> float:
    """1.0 inside expected_crest_factor; falloff over _CREST_TOLERANCE; neutral
    0.5 when crest is missing (<= 0) so it cannot dominate."""
    if crest <= 0:
        return 0.5
    lo, hi = profile.expected_crest_factor
    if lo <= crest <= hi:
        return 1.0
    dist = (lo - crest) if crest < lo else (crest - hi)
    return max(0.0, 1.0 - dist / _CREST_TOLERANCE)


def _confidence(bpm: float, bands: dict[str, float], crest: float, profile: GenreProfile) -> float:
    return (
        _W_BPM * _bpm_axis(bpm, profile)
        + _W_BANDS * _band_axis(bands, profile)
        + _W_CREST * _crest_axis(crest, profile)
    )


def score_genre(
    bpm: float,
    bands: dict[str, float],
    crest: float,
    profiles: list[GenreProfile],
) -> tuple[str, float]:
    """Return ``(best_name_or_unknown, confidence)``.

    Pure function — fully unit-testable without audio. Anti-slop: returns
    ``("unknown", best_conf)`` when the best profile is below
    ``GENRE_CONFIDENCE_MIN`` OR ties the runner-up within ``GENRE_TIE_MARGIN``.

    No-BPM-lock guard (anti-hallucination, mirrors ``_classify_active_genre``):
    ``bpm <= 0`` means no tempo lock yet, so no genre can be claimed —
    return ``("unknown", 0.0)`` outright rather than letting a perfect
    band+crest match alone manufacture confidence.
    """
    if bpm <= 0:
        return ("unknown", 0.0)

    scored: list[tuple[str, float]] = []
    for prof in profiles:
        if prof is None:
            continue
        scored.append((prof.name, _confidence(bpm, bands, crest, prof)))

    if not scored:
        return ("unknown", 0.0)

    scored.sort(key=lambda t: t[1], reverse=True)
    best_name, best_conf = scored[0]

    if best_conf < GENRE_CONFIDENCE_MIN:
        return ("unknown", best_conf)

    if len(scored) >= 2:
        second_conf = scored[1][1]
        if best_conf - second_conf < GENRE_TIE_MARGIN:
            return ("unknown", best_conf)

    return (best_name, best_conf)


@dataclass
class GenreHysteresis:
    """N-tick dwell debounce for the detected genre. Mirrors the phase
    ``HysteresisState`` idiom: track ``pending_label`` + ``pending_ticks``; a
    new raw value must persist for ``_HYSTERESIS_DWELL_TICKS`` ticks before it
    commits. ``unknown`` commits immediately (anti-hallucination)."""

    current_label: str = "unknown"
    pending_label: str | None = None
    pending_ticks: int = 0


def apply_genre_hysteresis(raw: str, hs: GenreHysteresis) -> str:
    """Mutate ``hs`` in place; return the committed genre label.

    - ``unknown`` commits immediately (no dwell — when confidence drops we stop
      claiming the old genre at once, mirroring ``silent`` in the phase detector).
    - raw == current → reset pending, return current.
    - raw == pending → increment; commit at >= dwell.
    - new pending value (or oscillation) → reset counter to 1, hold current.
    """
    if raw == "unknown":
        hs.current_label = "unknown"
        hs.pending_label = None
        hs.pending_ticks = 0
        return "unknown"
    if raw == hs.current_label:
        hs.pending_label = None
        hs.pending_ticks = 0
        return hs.current_label
    if hs.pending_label == raw:
        hs.pending_ticks += 1
        if hs.pending_ticks >= _HYSTERESIS_DWELL_TICKS:
            hs.current_label = raw
            hs.pending_label = None
            hs.pending_ticks = 0
        return hs.current_label
    hs.pending_label = raw
    hs.pending_ticks = 1
    return hs.current_label


# --- Env override flag (Task 4) ---
# Auto-detect re-points the active profile only when the user did NOT explicitly
# pin VIBEMIX_GENRE_PROFILE. __main__ calls set_auto_enabled(not env_pinned).
# Scoring (detected_genre/genre_confidence) ALWAYS runs for honesty; only the
# set_active_profile flip is gated on this flag.
_AUTO_ENABLED = True


def set_auto_enabled(enabled: bool) -> None:
    """Enable/disable auto re-pointing of the active profile. Default True."""
    global _AUTO_ENABLED
    _AUTO_ENABLED = bool(enabled)


def is_auto_enabled() -> bool:
    """Whether auto-detect is allowed to flip the active profile this session."""
    return _AUTO_ENABLED
