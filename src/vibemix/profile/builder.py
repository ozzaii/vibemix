# SPDX-License-Identifier: Apache-2.0
"""Profile builder — aggregate session evidence into a 2KB DJ profile.

Phase 32 / PROFILE-01, PROFILE-02, PROFILE-06. The builder consumes:

- The **prior profile** (loaded from ``~/.config/vibemix/profile.json`` — may
  be ``None`` if first ever build) — used as the fallback value when a
  tendency field has insufficient new evidence (P06 ≥2-citation rule).
- The **session events** — list of ``vibemix.state.Event`` from THIS session,
  used for tempo histogram + duration aggregate.
- The **evidence snapshot** — ``dict[source, dict[key, tuple[float, ...]]]``
  from ``EvidenceRegistry.snapshot()`` — drives the citation-count
  aggregation per tendency field.

Builder is **pure** (no I/O, no globals). Storage is a separate layer.

PROFILE-06 (≥2-citation rule):
  For each tendency field (genre, tempo bin, response prefs), require ≥2
  distinct citations. If <2, retain prior value (or omit/`"unknown"` if
  no prior). This prevents one-session noise from polluting the profile.

PROFILE-02 (allowlist + 2KB cap):
  Builder produces ONLY the allowlist fields. ``serialize_profile`` enforces
  the schema + 2048-byte cap at the boundary. Builder cannot smuggle a
  ``track_title`` field in — the schema rejects it.

PROFILE-05 (consent gate):
  ``consent=False`` short-circuits to ``None`` immediately. Caller does NOT
  persist; cache section becomes empty.
"""

from __future__ import annotations

import json
from collections import Counter
from typing import Any, Final

from vibemix.profile.schema import (
    EVENT_TYPES_FOR_PREFS,
    GENRES,
    MIX_STYLE_TAGS,
    TEMPO_BINS,
    ProfileError,
    validate_profile,
)

#: Hard 2KB cap from Pitfall P51 size. Empirically tested for cache token cost.
MAX_PROFILE_BYTES: Final[int] = 2048

#: Per-tendency-field minimum citation count (Pitfall P06 drift prevention).
MIN_CITATIONS_PER_TENDENCY: Final[int] = 2

#: Cadence cutoffs: distinct citation count → cadence label.
#: Tuned so 1-2 reads as "rarely", 3-5 as "sometimes", ≥6 as "always".
_CADENCE_CUTOFFS: Final[tuple[tuple[int, str], ...]] = (
    (6, "always"),
    (3, "sometimes"),
    (1, "rarely"),
)


def _bpm_to_bin(bpm: float) -> str | None:
    """Map a BPM value to a tempo bin. Returns None for non-positive / NaN."""
    if not (bpm > 0):
        return None
    if bpm < 120:
        return "110-120"
    if bpm < 128:
        return "120-128"
    if bpm < 138:
        return "128-138"
    if bpm < 150:
        return "138-150"
    return "150+"


def _aggregate_tempo_bin(
    session_events: list[Any],
    prior: str | None,
) -> str | None:
    """Return modal BPM bin from session events; fall back to prior on <2 obs.

    P06: requires ≥2 BPM observations. The state.bpm attribute may be 0
    (cold start), which is treated as a non-observation.
    """
    bpms: list[float] = []
    for ev in session_events:
        bpm = getattr(getattr(ev, "state", None), "bpm", 0.0) or 0.0
        if bpm > 0:
            bpms.append(float(bpm))
    if len(bpms) < MIN_CITATIONS_PER_TENDENCY:
        return prior
    bins: list[str] = []
    for bpm in bpms:
        b = _bpm_to_bin(bpm)
        if b is not None:
            bins.append(b)
    if not bins:
        return prior
    counter = Counter(bins)
    most = counter.most_common(1)[0][0]
    return most


def _aggregate_session_duration(
    session_events: list[Any],
    prior: float | None,
) -> float:
    """Return current session's last-seen session_t in minutes, blended with prior.

    Phase 32 ships with simple alpha-blend (0.3 new / 0.7 prior) so a single
    short session can't crash the running average. Cold-start = the session's
    own duration; cap at 720 min.
    """
    if not session_events:
        return float(prior or 0.0)
    # session_t is the relative seconds since session start; the last event's
    # state.session_t approximates total session duration. Fall back to 0 if
    # the attribute is missing (e.g., synthetic test fixtures).
    last = session_events[-1]
    seconds = float(getattr(getattr(last, "state", None), "session_t", 0.0) or 0.0)
    current_minutes = max(0.0, min(720.0, seconds / 60.0))
    if prior is None or prior <= 0:
        return current_minutes
    blended = 0.3 * current_minutes + 0.7 * float(prior)  # alpha-blend
    return max(0.0, min(720.0, blended))


def _aggregate_response_prefs(
    evidence_snapshot: dict[str, dict[str, tuple[float, ...]]],
    prior: dict[str, str] | None,
) -> dict[str, str]:
    """Map per-event-type citation counts to cadence labels.

    Uses ``evidence_snapshot["event"][TYPE]`` — the count of distinct
    timestamps. <2 = retain prior (P06); ≥2 falls into the cadence cutoffs.
    """
    event_observations = evidence_snapshot.get("event", {})
    prefs: dict[str, str] = {}
    for ev_type in EVENT_TYPES_FOR_PREFS:
        timestamps = event_observations.get(ev_type, ())
        # Distinct timestamps protect against the same event being recorded
        # twice in a tick (defense-in-depth; EvidenceRegistry already dedups).
        count = len({round(t, 3) for t in timestamps})
        if count < MIN_CITATIONS_PER_TENDENCY:
            # P06 retain prior (or omit). If no prior, default to "never"
            # so the schema's `additionalProperties: false` on
            # event_type_response_preferences accepts a complete object
            # without forcing the caller to handle missing keys.
            prefs[ev_type] = (prior or {}).get(ev_type, "never")
            continue
        for threshold, cadence in _CADENCE_CUTOFFS:
            if count >= threshold:
                prefs[ev_type] = cadence
                break
    return prefs


def _aggregate_genre(
    evidence_snapshot: dict[str, dict[str, tuple[float, ...]]],
    prior: str | None,
) -> str:
    """Pick the modal genre tag from evidence_snapshot["genre"].

    The ``genre`` source is written by ``GenreClassifier`` (Phase 6+). Keys
    are genre labels matching :data:`GENRES`. P06: <2 distinct observations
    → retain prior; cold-start → "unknown".
    """
    genre_obs = evidence_snapshot.get("genre", {})
    counts: Counter[str] = Counter()
    for key, timestamps in genre_obs.items():
        if key in GENRES:
            counts[key] += len(timestamps)
    total = sum(counts.values())
    if total < MIN_CITATIONS_PER_TENDENCY:
        return prior if prior in GENRES else "unknown"
    return counts.most_common(1)[0][0]


def _aggregate_mix_style_tags(
    session_events: list[Any],
    evidence_snapshot: dict[str, dict[str, tuple[float, ...]]],
    prior: list[str] | None,
) -> list[str]:
    """Top-N (≤8) mix-style tags from EventDetector emissions.

    Reads ``evidence_snapshot["mix_style"]`` (tag → timestamps). Filters to
    the allowlist (defense-in-depth — schema would reject unknown tags
    anyway). Requires ≥2 citations per tag to include it.
    """
    style_obs = evidence_snapshot.get("mix_style", {})
    counts: Counter[str] = Counter()
    for tag, timestamps in style_obs.items():
        if tag in MIX_STYLE_TAGS and len(timestamps) >= MIN_CITATIONS_PER_TENDENCY:
            counts[tag] = len(timestamps)
    if not counts:
        # Cold-start: retain prior (intersected with allowlist to survive
        # any allowlist shrink in future schema versions).
        if prior:
            return [t for t in prior if t in MIX_STYLE_TAGS][:8]
        return []
    top = [tag for tag, _ in counts.most_common(8)]
    return top


def build_profile(
    prior_profile: dict | None,
    session_events: list[Any],
    evidence_snapshot: dict[str, dict[str, tuple[float, ...]]],
    *,
    consent: bool = False,
) -> dict | None:
    """Aggregate session evidence into a profile dict.

    Returns ``None`` if ``consent`` is False (PROFILE-05 default-OFF gate).
    Otherwise returns a profile dict satisfying :data:`PROFILE_SCHEMA`.

    All tendency fields apply the ≥2-citation rule (PROFILE-06): if the new
    session lacks evidence for a field, the prior value is retained.

    The returned dict is NOT serialized — callers run :func:`serialize_profile`
    to apply the 2048-byte cap + schema validation.
    """
    if not consent:
        return None

    prior = prior_profile or {}

    profile: dict[str, Any] = {
        "preferred_genre": _aggregate_genre(
            evidence_snapshot, prior.get("preferred_genre")
        ),
        "avg_session_duration": _aggregate_session_duration(
            session_events, prior.get("avg_session_duration")
        ),
        "mix_style_tags": _aggregate_mix_style_tags(
            session_events, evidence_snapshot, prior.get("mix_style_tags")
        ),
        "tempo_preference_bin": _aggregate_tempo_bin(
            session_events, prior.get("tempo_preference_bin")
        )
        or "128-138",  # cold-start default — modal techno bin
        "event_type_response_preferences": _aggregate_response_prefs(
            evidence_snapshot, prior.get("event_type_response_preferences")
        ),
    }

    return profile


def serialize_profile(profile: dict) -> bytes:
    """Validate + serialize to UTF-8 bytes, enforcing the 2048-byte cap.

    Raises :class:`ProfileError` on schema violation OR size violation.
    Compact JSON (no spaces) maximizes the byte budget. Sorted keys make
    cache-key stability easier on the GeminiContextCache side.
    """
    validate_profile(profile)
    raw = json.dumps(profile, separators=(",", ":"), sort_keys=True).encode("utf-8")
    if len(raw) > MAX_PROFILE_BYTES:
        raise ProfileError(
            f"profile exceeds {MAX_PROFILE_BYTES}-byte cap (got {len(raw)} bytes)"
        )
    return raw
