# SPDX-License-Identifier: Apache-2.0
"""state_refresh_loop — the 10Hz single writer to MusicState.

Verbatim port of cohost_v4.py:1647-1751 with **ONE structural deviation** from
v4 (Phase 3): the four audio-related calls that v4 made as METHODS on
``AudioBuffer`` are rewritten here as FREE FUNCTION calls per Phase 2's
refactor.

**Phase 6 additions** (this commit):
- Per-tick crest_factor + EMA smoothing.
- Per-tick BPM half/double validation against active genre profile.
- Per-tick VocalDetector with 1.5s/2.5s hysteresis.
- Per-tick dispatch into classify_phase (percentile path when profile active,
  v4 absolute-threshold path when no profile).
- Writes 4 new MusicState fields: crest_factor, vocal_active, bpm_corrected,
  genre_profile_name.

The genre-aware state (EmaSmoother / VocalDetector / HysteresisState /
feature_history deque) lives in the loop's LOCAL scope (NOT in MusicState —
Critical Constraint 7: MusicState holds consumer-readable evidence;
hysteresis machinery is internal detector state). Loop-local state is
threaded through `_tick_once` via kwargs.

Single-writer contract: this is the ONLY function in the codebase that writes
to MusicState fields. EventDetector and AICoach are read-only. The write
batch is wrapped in ``with state._lock:`` so multi-field consistent snapshots
are achievable by readers that opt in.

Error wrap: the entire per-tick body is ``try / except Exception``; the loop
NEVER exits on exception (verbatim v4 behavior).
"""

from __future__ import annotations

import asyncio
import os
import re
import sys
import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from vibemix.audio import (
    AUDIBLE_DEBOUNCE_SEC,
    BPM_VALID_MAX,
    BPM_VALID_MIN,
    SILENCE_DEBOUNCE_SEC,
    SILENT_RMS,
    AudioBuffer,
    compute_downbeat_phase,
    energy_curve,
    estimate_bpm,
    long_arc_curve,
    snapshot_features,
)
from vibemix.audio.constants import (
    BUILDUP_SLOPE_WINDOW_S,
    GENRE_BPM_BANDS,
    GENRE_CENTROID_HARD_TEK_MIN,
)
from vibemix.audio.lufs import SHORT_TERM_WINDOW_S, short_term_lufs
from vibemix.library.section_builder import next_section_after_position, sections_for_entry
from vibemix.midi.state import classify_controller_midi_activity
from vibemix.state.deck_context import (
    live_mix_evidence_keys,
    midi_evidence_key,
    render_audio_delta_items,
)
from vibemix.state.deck_poller import DECK_CITE_MIN_CONF
from vibemix.state.deltas import DELTA_FLOOR, render_delta
from vibemix.state.drop_predict import predict_drop_in_sec
from vibemix.state.emotion_router import derive_emotion
from vibemix.state.evidence_registry import EvidenceRegistry
from vibemix.state.genre import (
    EmaSmoother,
    GenreHysteresis,
    HysteresisState,
    VocalDetector,
    apply_genre_hysteresis,
    crest_factor,
    get_active_profile,
    is_auto_enabled,
    list_profiles,
    load_profile,
    score_genre,
    set_active_profile,
    validate_bpm,
)
from vibemix.state.genre.genre_reconcile import reconcile_genre
from vibemix.state.harmonics import to_camelot
from vibemix.state.loop_geometry import beatgrid_exact_atom, parse_loop_control_kind
from vibemix.state.music_state import MusicState
from vibemix.state.phase import classify_phase
from vibemix.state.set_plan import derive_set_progress
from vibemix.state.track_resolver import derive_audible_deck, derive_audible_track

# BPM stabilization — estimate_bpm is bimodal on dense material: a strong
# subdivision lock can land at ~200 while the true kick reads ~130 (measured on
# a real psytrance track, 2026-05-21). One raw sample per 3 s tick flickered
# active_genre to unknown/house, which destabilised the genre profile and let
# phase classification fall back to the no-hysteresis path → live phase flicker.
_BPM_RING_MAXLEN = 5  # ~15 s at the 3 s estimate cadence
_COURSE3_CUE_CONF_FLOOR = 0.7

# Dormant drop-anticipation signal (SYSTEM-AUDIT C9). Only anticipate a drop the
# detector is at least half-sure of, and never "call" one more than ~a phrase or two
# out — a too-early or low-confidence prediction is worse than silence.
_DROP_CUE_CONF_FLOOR = 0.5
_DROP_HORIZON_S = 32.0
_COURSE3_MIX_TITLE_MATCH_POSITION_CONF = 0.75
_COURSE3_REVIEW_ONLY_LESSONS = frozenset({"L3.06"})
_PREPARED_POOL_REFRESH_INTERVAL_S = 5.0
_MOVE_AUDIO_DELTA_WINDOW_S = 6.0
_MOVE_AUDIO_BASELINE_TTL_S = 8.0
_MOVE_AUDIO_BASELINE_RESET_S = 0.4


# Phase 52 (GENRE-01): cache the loaded GenreProfile library once — the profile
# JSONs do not change at runtime, so re-loading all of them every tick (10Hz)
# would be wasteful. Lazily populated on first use; the genre auto-detector
# scores nearest-match across this list.
_PROFILE_CACHE: list | None = None


def _cached_profiles() -> list:
    """Return the loaded GenreProfile library, loaded once and cached."""
    global _PROFILE_CACHE
    if _PROFILE_CACHE is None:
        _PROFILE_CACHE = [p for p in (load_profile(n) for n in list_profiles()) if p is not None]
    return _PROFILE_CACHE


def _stabilize_bpm(ring: list[float]) -> float:
    """Lower-median of the in-range BPM samples in ``ring`` (0.0 if none).

    Drops anything outside [BPM_VALID_MIN, BPM_VALID_MAX] before taking the
    median, so a transient subdivision lock (>180) can never reach genre/phase.
    Lower-median (``valid[len//2]`` over the sorted list) guarantees the result
    is an actually-observed sample — never a manufactured between-samples value
    that could fall in a cross-genre gap. A mean/EMA would average 130+200 into
    the ~165 'unknown' gap, which is strictly worse — hence median, not EMA.
    """
    valid = sorted(b for b in ring if BPM_VALID_MIN <= b <= BPM_VALID_MAX)
    if not valid:
        return 0.0
    return float(valid[len(valid) // 2])


def _float_field(value: object) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _current_perceive_snapshot(state: MusicState) -> dict[str, float | None]:
    bands = getattr(state, "bands", {}) if isinstance(getattr(state, "bands", {}), dict) else {}
    return {
        "rms": _float_field(getattr(state, "rms", 0.0)),
        "sub": _float_field(bands.get("sub", 0.0)),
        "low": _float_field(bands.get("low", 0.0)),
        "mid": _float_field(bands.get("mid", 0.0)),
        "high": _float_field(bands.get("high", 0.0)),
        "onset_density": _float_field(getattr(state, "onset_density", 0.0)),
    }


def _render_move_audio_delta_items(
    state: MusicState,
    baseline: dict[str, object],
    *,
    cap: int = 4,
) -> list[str]:
    if not getattr(state, "audible", False) or not baseline:
        return []
    current = _current_perceive_snapshot(state)
    candidates = (
        ("sub energy", current.get("sub"), "sub"),
        ("low energy", current.get("low"), "low"),
        ("mid energy", current.get("mid"), "mid"),
        ("high energy", current.get("high"), "high"),
        ("RMS", current.get("rms"), "rms"),
        ("onset density", current.get("onset_density"), "onset_density"),
    )
    out: list[str] = []
    for label, cur, key in candidates:
        if cur is None:
            continue
        phr = render_delta(label, cur, _float_field(baseline.get(key)), floor=DELTA_FLOOR)
        if phr is not None:
            out.append(phr)
        if len(out) >= cap:
            break
    return out


def _update_move_audio_delta(
    state: MusicState,
    *,
    now: float,
    move_audio_baselines: dict[str, dict[str, object]] | None,
) -> None:
    state.move_audio_delta = []
    if move_audio_baselines is None:
        return
    if not getattr(state, "audible", False):
        move_audio_baselines.clear()
        return
    recent: list[tuple[float, str]] = []
    for raw in getattr(state, "recent_moves", []) or []:
        if not isinstance(raw, (list, tuple)) or len(raw) < 2:
            continue
        try:
            age = float(raw[0])
        except (TypeError, ValueError):
            continue
        if age < 0.0 or age > _MOVE_AUDIO_BASELINE_TTL_S:
            continue
        label = str(raw[1])
        key = midi_evidence_key(label)
        if not key:
            continue
        move_at = now - age
        rec = move_audio_baselines.get(key)
        prev = getattr(state, "prev_perceive", None)
        if (
            isinstance(prev, dict)
            and prev
            and (
                not isinstance(rec, dict)
                or _float_field(rec.get("move_at")) is None
                or move_at
                > (_float_field(rec.get("move_at")) or float("-inf"))
                + _MOVE_AUDIO_BASELINE_RESET_S
            )
        ):
            move_audio_baselines[key] = {
                "move_at": move_at,
                "last_seen": now,
                "snapshot": dict(prev),
            }
        elif isinstance(rec, dict):
            rec["last_seen"] = now
        recent.append((age, key))

    for key, rec in list(move_audio_baselines.items()):
        if not isinstance(rec, dict):
            move_audio_baselines.pop(key, None)
            continue
        last_seen = _float_field(rec.get("last_seen"))
        move_at = _float_field(rec.get("move_at"))
        if (
            last_seen is None
            or move_at is None
            or now - last_seen > _MOVE_AUDIO_BASELINE_TTL_S
            or now - move_at > _MOVE_AUDIO_BASELINE_TTL_S
        ):
            move_audio_baselines.pop(key, None)

    if not recent:
        return
    age, key = min(recent, key=lambda item: item[0])
    if age > _MOVE_AUDIO_DELTA_WINDOW_S:
        return
    rec = move_audio_baselines.get(key)
    snapshot = rec.get("snapshot") if isinstance(rec, dict) else None
    if isinstance(snapshot, dict):
        state.move_audio_delta = _render_move_audio_delta_items(state, snapshot)


def _classify_active_genre(bpm: float, feats: dict) -> str:
    """Coarse BPM-band + spectral-centroid heuristic for `active_genre`.

    Per CONTEXT D-04: house 118-128, techno 128-138, hard_tek 140-BPM_VALID_MAX,
    "unknown" otherwise. Bands intentionally non-overlapping; the gaps
    (128-128, 138-140) → "unknown" (per "trust the audio" — don't force-classify
    ambiguous tempos).

    Anti-hallucination: invalid BPM (≤ 0 or outside the autocorr-noise-reject
    window BPM_VALID_MIN..BPM_VALID_MAX) yields "unknown" — no fabricated genre
    during BPM lock-up. Mirrors the v4 `_music_truly_playing` rule
    (T-17-01-01 mitigation in 17-01-PLAN threat register).

    Hard Tek extra gate: when BPM lands in the hard_tek band, also require
    `(mid_share + high_share) >= GENRE_CENTROID_HARD_TEK_MIN` — distorted-kick
    spectral signature gate, anti-misclassify-on-house-with-fast-tempo. Below
    floor → "unknown" (we'd rather not classify than mis-classify).
    """
    if bpm <= 0 or not (BPM_VALID_MIN <= bpm <= BPM_VALID_MAX):
        return "unknown"
    centroid = feats.get("mid_share", 0.0) + feats.get("high_share", 0.0)
    for name, (lo, hi) in GENRE_BPM_BANDS.items():
        if name == "unknown":
            continue
        if lo <= bpm < hi or (name == "hard_tek" and bpm == hi):
            if name == "hard_tek" and centroid < GENRE_CENTROID_HARD_TEK_MIN:
                return "unknown"
            return name
    return "unknown"


def _routeable_active_genre(
    preferred_genre: str,
    *,
    bpm: float,
    feats: dict,
) -> str:
    """Return the event-router genre, preferring a registered profile label.

    ``detected_genre`` may be richer than the legacy coarse BPM buckets. When
    that richer label has a detector chain, route events through it; otherwise
    preserve the old coarse classifier as the honest fallback.
    """
    if preferred_genre != "unknown":
        try:
            from vibemix.events.genres import GENRE_REGISTRY

            if preferred_genre in GENRE_REGISTRY:
                return preferred_genre
        except Exception:
            pass
    return _classify_active_genre(bpm, feats)


def _course3_session_lens_active(learn_state) -> bool:
    """Return whether the current Learn lesson should activate live coaching.

    Course 3 contains one post-set review lesson (L3.06) whose fixture marks
    ``proactive_lens_active=false``. Keep the hot-path dependency light by
    keying off the stable lesson id instead of importing the curriculum table.
    Older callers that only supply ``current_course_id`` keep the coarse Course
    3 behavior for compatibility.
    """
    if getattr(learn_state, "current_course_id", None) != "course_3_play_mode":
        return False
    lesson_id = getattr(learn_state, "current_lesson_id", None)
    if lesson_id in _COURSE3_REVIEW_ONLY_LESSONS:
        return False
    return True


def _log_drop_countdown(
    new_drop: float | None,
    prev_drop: float | None,
    track_title: str | None,
) -> None:
    """Live-bench countdown for the dormant drop signal (DROP_DEBUG, opt-in).

    Off unless ``VIBEMIX_DROP_DEBUG`` is set. Prints once per integer second as the
    predicted drop approaches, plus a ``NOW`` marker when a small ETA resolves to
    ``None`` (the drop section reached) — so a live tester can compare the
    prediction against the music by ear. No reaction fires; this is observation only.
    """
    if not os.environ.get("VIBEMIX_DROP_DEBUG"):
        return
    title = (track_title or "?")[:32]
    if new_drop is not None:
        if prev_drop is None or int(new_drop) != int(prev_drop):
            print(f"-> [drop] ~{new_drop:4.0f}s  {title}", flush=True)
    elif prev_drop is not None and prev_drop <= 2.0:
        print(f"-> [drop] >>> NOW <<<  {title}", flush=True)


def _compute_buildup_score(curve: list, window_s: float, hop_s: float = 1.0) -> float:
    """Slope of the trailing `int(window_s/hop_s)` samples of `curve`,
    normalized into [0.0, 1.0]. Negative slopes (energy falling) clamp to 0.0
    — buildups are monotonic-climbs only; falling energy is a job for
    BREAKDOWN_KICK_KILL, NOT a negative buildup.

    Bound contract: `buildup_score ∈ [0.0, 1.0]`. Cheap (n=8 polyfit, ~µs;
    T-17-01-03 in threat register).
    """
    n = int(window_s / hop_s)
    if n <= 1 or not curve:
        return 0.0
    tail = list(curve)[-n:]
    if len(tail) < 2:
        return 0.0
    xs = np.arange(len(tail), dtype=np.float64)
    ys = np.asarray(tail, dtype=np.float64)
    # Least-squares slope (deg=1). Epsilon-floor catches polyfit float noise
    # on flat curves (np yields ~1e-16 instead of exact 0.0); below 1e-9 is
    # numerically indistinguishable from "no slope" given energy_curve
    # values are themselves rounded by snapshot_features.
    slope = float(np.polyfit(xs, ys, 1)[0])
    if slope <= 1e-9:
        return 0.0
    max_recent = max(0.05, float(np.max(ys)))
    score = (slope * window_s) / max_recent
    if score < 0.0:
        return 0.0
    if score > 1.0:
        return 1.0
    return score


def _optional_float(raw: object) -> float | None:
    try:
        return float(raw)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _write_live_grounding_evidence(
    evidence_registry: EvidenceRegistry | None,
    state: MusicState,
    *,
    t_session: float,
    evidence_dedupe: set[str] | None,
    audio_delta_items: list[str],
    audio_capture_context: dict[str, object] | None = None,
) -> None:
    """Register citable deck/move/audio-delta facts without hot-loop spam."""
    if evidence_registry is None:
        return
    try:
        for raw in state.recent_moves:
            if not isinstance(raw, (list, tuple)) or len(raw) < 2:
                continue
            try:
                age = max(0.0, float(raw[0]))
            except (TypeError, ValueError):
                continue
            if age > 8.0:
                continue
            label = str(raw[1])
            key = midi_evidence_key(label)
            move_t = round(max(0.0, t_session - age), 1)
            dedupe_key = f"midi:{key}@{move_t:.1f}"
            if evidence_dedupe is not None and dedupe_key in evidence_dedupe:
                continue
            evidence_registry.write("midi", key, move_t)
            if evidence_dedupe is not None:
                evidence_dedupe.add(dedupe_key)

        for key in live_mix_evidence_keys(
            state,
            state.recent_moves,
            audio_delta_items=audio_delta_items,
            audio_capture_context=audio_capture_context,
        ):
            dedupe_key = f"mix:{key}"
            if evidence_dedupe is not None and dedupe_key in evidence_dedupe:
                continue
            evidence_registry.write("mix", key, t_session)
            if evidence_dedupe is not None:
                evidence_dedupe.add(dedupe_key)
    except Exception:
        pass


def _write_loop_geometry_evidence(
    evidence_registry: EvidenceRegistry | None,
    controller_state,
    *,
    now: float,
    set_start_at: float,
    evidence_dedupe: set[str] | None,
) -> None:
    """Register beat-sized loop/beatjump receipts from typed controller events."""
    if evidence_registry is None:
        return
    events_since = getattr(controller_state, "events_since", None)
    if not callable(events_since):
        return
    try:
        events = events_since(now - 8.0)
        for event in events:
            event_at = getattr(event, "at", None)
            try:
                event_at_f = float(event_at)
            except (TypeError, ValueError):
                continue
            age = now - event_at_f
            if age < 0.0 or age > 8.0:
                continue
            control = parse_loop_control_kind(str(getattr(event, "kind", "")))
            if control is None or control.size_beats is None:
                continue
            action = control.action
            if action == "beatjump":
                action = "beatjump_back" if control.direction < 0 else "beatjump_fwd"
            key = beatgrid_exact_atom(getattr(event, "deck", None), action, control.size_beats)
            t_session = round(max(0.0, event_at_f - set_start_at), 1)
            dedupe_key = f"mix:{key}@{t_session:.1f}"
            if evidence_dedupe is not None and dedupe_key in evidence_dedupe:
                continue
            evidence_registry.write("mix", key, t_session)
            if evidence_dedupe is not None:
                evidence_dedupe.add(dedupe_key)
    except Exception:
        pass


def _compose_trajectory(phase_history: list, buildup_score: float, recent_moves: list) -> str:
    """PERCEIVE-02: compose ONE bounded multi-scale trajectory narrative from
    the already-bounded MusicState fields. PURE — no state write, no I/O; called
    from the single-writer ``_tick_once``.

    Three scales joined into one compact string (e.g.
    ``"build→drop→groove; building; last move: bass-swap 20s ago"``):
      - **phrase** — last-3 phase chain from ``phase_history`` (capped 6 upstream).
      - **energy-arc** — ``buildup_score`` → "building" (>= 0.5) / "settled".
      - **moves** — newest ``recent_moves`` entry + its age in seconds.

    Bounded: inputs are themselves capped (phase_history ≤ 6 → last 3 here;
    one move; one arc label), so the output length cannot grow across ticks. A
    fully-cold state (no phases, no moves, buildup 0) → "" so the coach gate omits
    (cold-path byte-identity).
    """
    parts: list[str] = []

    # Phrase scale — last-3 phase chain (mirror coach's phase_history render).
    if phase_history:
        chain: list[str] = []
        for i, (_, fr, to) in enumerate(phase_history[-3:]):
            if i == 0:
                chain.append(str(fr))
            chain.append(str(to))
        if chain:
            parts.append("→".join(chain))

    # Energy-arc scale — only assert a label when there is a phrase or a move to
    # anchor it (a bare "settled" on a cold state would break byte-identity).
    if parts or recent_moves:
        parts.append("building" if buildup_score >= 0.5 else "settled")

    # Moves scale — newest move + its age (recent_moves is a (age, label) list,
    # smallest age = newest). WR-03 — filter to the SAME 8s window coach uses
    # (coach.py:369, `age <= 8.0`) before picking the newest. state.recent_moves
    # is populated over a wider 12s window (refresh.py moves_since(now - 12.0)),
    # so without this filter the trajectory could report "last move: bass-swap
    # 11s ago" while the coach's recent_moves[8s] block simultaneously says NONE —
    # the two surfaces contradicting reads as AI slop.
    recent_8s = [m for m in recent_moves if m[0] <= 8.0]
    if recent_8s:
        age, label = min(recent_8s, key=lambda m: m[0])
        parts.append(f"last move: {label} {age:.0f}s ago")

    return "; ".join(parts)


def _dispatch_genre_lookup(genre_source, track_id: str) -> None:
    """Fire the embedding genre lookup OFF the 10Hz tick (PERCEIVE-03).

    Mirrors the Grounding off-loop dispatch: ``clear()`` discards any superseded
    in-flight lookup (generation token), then a daemon thread runs
    ``classify_playing`` which fills the holder's OWN ``_latest`` — the worker
    NEVER writes MusicState (invariant #1; ``_tick_once`` is the sole writer that
    READS ``get_latest()``). Best-effort + try-guarded so a lookup failure logs
    to stderr and never wedges the tick or the ``in_flight`` gate (T-78-04-04).
    """
    try:
        genre_source.clear()

        def _worker() -> None:
            try:
                genre_source.classify_playing(track_id)
            except Exception as e:  # never let an off-loop failure escape
                print(f"[genre lookup err] {e}", file=sys.stderr)

        threading.Thread(target=_worker, name="genre-lookup", daemon=True).start()
    except Exception as e:  # clear()/thread-spawn failure must not wedge the tick
        print(f"[genre dispatch err] {e}", file=sys.stderr)


@dataclass(frozen=True, slots=True)
class _Course3PhraseAnchor:
    confidence: float
    next_phrase_at: float
    cue_id: str


@dataclass(frozen=True, slots=True)
class _Course3AnchorDeck:
    track_id: str
    deck_confidence: float
    position_confidence: float


def _lookup_section_entry(section_source, track_id: str):
    if section_source is None or not track_id:
        return None
    try:
        lookup = getattr(section_source, "lookup_by_id", None)
        if callable(lookup):
            return lookup(track_id)
        tracks = getattr(section_source, "tracks", None)
        if isinstance(tracks, dict):
            return tracks.get(track_id)
        if isinstance(section_source, dict):
            return section_source.get(track_id)
        if callable(section_source):
            return section_source(track_id)
    except Exception:
        return None
    return None


def _cue_anchor_id(section) -> str:
    raw = f"{section.track_id}:{section.role}@{float(section.start_s):.1f}"
    return re.sub(r"[\s,\[\]]+", "_", raw)


def _normalized_title(raw: object) -> str:
    return str(raw or "").strip().casefold()


def _course3_anchor_deck(
    *,
    deck_snap: dict | None,
    audible_deck: str,
    track_title: str | None,
    position_confidence: float,
) -> _Course3AnchorDeck | None:
    if deck_snap is None:
        return None

    if audible_deck in {"A", "B"}:
        dt = deck_snap.get(audible_deck)
        if dt is None or not getattr(dt, "track_id", None):
            return None
        deck_confidence = float(getattr(dt, "confidence", 0.0) or 0.0)
        if deck_confidence < DECK_CITE_MIN_CONF:
            return None
        return _Course3AnchorDeck(
            track_id=str(dt.track_id),
            deck_confidence=deck_confidence,
            position_confidence=position_confidence,
        )

    if audible_deck != "mix":
        return None

    title = _normalized_title(track_title)
    if not title:
        return None

    matches: list[_Course3AnchorDeck] = []
    for side in ("A", "B"):
        dt = deck_snap.get(side)
        if dt is None or not getattr(dt, "track_id", None):
            continue
        deck_confidence = float(getattr(dt, "confidence", 0.0) or 0.0)
        if deck_confidence < DECK_CITE_MIN_CONF:
            continue
        if _normalized_title(getattr(dt, "title", None)) != title:
            continue
        matches.append(
            _Course3AnchorDeck(
                track_id=str(dt.track_id),
                deck_confidence=deck_confidence,
                position_confidence=max(
                    float(position_confidence or 0.0),
                    _COURSE3_MIX_TITLE_MATCH_POSITION_CONF,
                ),
            )
        )
    if len(matches) != 1:
        return None
    return matches[0]


def _resolve_course3_phrase_anchor(
    *,
    section_source,
    deck_snap: dict | None,
    audible_deck: str,
    track_title: str | None,
    position_s: float | None,
    position_confidence: float,
    now: float,
    set_start_at: float,
) -> _Course3PhraseAnchor | None:
    if section_source is None:
        return None
    if position_s is None:
        return None
    anchor_deck = _course3_anchor_deck(
        deck_snap=deck_snap,
        audible_deck=audible_deck,
        track_title=track_title,
        position_confidence=position_confidence,
    )
    if anchor_deck is None:
        return None

    entry = _lookup_section_entry(section_source, anchor_deck.track_id)
    if entry is None:
        return None
    try:
        next_section = next_section_after_position(sections_for_entry(entry), position_s)
    except Exception:
        return None
    if next_section is None or next_section.source != "dj":
        return None

    cue_confidence = (
        next_section.cue_confidence
        if next_section.cue_confidence is not None
        else next_section.confidence
    )
    section_confidence = min(float(next_section.confidence), float(cue_confidence or 0.0))
    if section_confidence < _COURSE3_CUE_CONF_FLOOR:
        return None

    confidence = max(
        0.0,
        min(
            1.0,
            section_confidence,
            anchor_deck.deck_confidence,
            anchor_deck.position_confidence,
        ),
    )
    if confidence <= 0.0:
        return None
    set_seconds = max(0.0, now - set_start_at)
    seconds_to_boundary = max(0.0, float(next_section.start_s) - max(0.0, position_s))
    next_phrase_at = set_seconds + seconds_to_boundary
    return _Course3PhraseAnchor(
        confidence=confidence,
        next_phrase_at=next_phrase_at,
        cue_id=_cue_anchor_id(next_section),
    )


if TYPE_CHECKING:
    from vibemix.platform._midi_macos import ControllerState
    from vibemix.platform._track_macos import TrackInfo


def _tick_once(
    state: MusicState,
    audio_buf: AudioBuffer,
    controller_state: ControllerState,
    track_info: TrackInfo,
    *,
    now: float,
    last_audible_high: float,
    last_audible_low: float,
    bpm_cache: float,
    last_bpm_at: float,
    bpm_ring: list[float] | None = None,
    crest_smoother: EmaSmoother | None = None,
    vocal_detector: VocalDetector | None = None,
    hysteresis_state: HysteresisState | None = None,
    feature_history: deque[dict] | None = None,
    evidence_registry: EvidenceRegistry | None = None,
    genre_hysteresis: GenreHysteresis | None = None,
    deck_source=None,
    genre_source=None,
    learn_state=None,
    section_source=None,
    prepared_pool=None,
    evidence_dedupe: set[str] | None = None,
    audio_capture_context: dict[str, object] | None = None,
    move_audio_baselines: dict[str, dict[str, object]] | None = None,
) -> tuple[float, float, float, float]:
    """One iteration of the state_refresh_loop body. Extracted so tests can
    drive single ticks deterministically with fake time and fake snapshots.

    Returns the updated (last_audible_high, last_audible_low, bpm_cache,
    last_bpm_at) tuple for the caller to thread through the next tick.

    Phase 6 additions: crest factor, BPM validation, vocal detection, phase
    dispatch — all gated on the active genre profile.

    Phase 18 Plan 02 additions: optional ``evidence_registry`` kwarg. When
    wired, writes citable observations INSIDE the same ``with state._lock:``
    batch as MusicState writes — single-snapshot consistency contract:
      - "aud" source: 7 audio-feature keys per tick, GATED on state.audible
        (silent ticks are not citable — closes the "cite RMS at silent
        moment" hallucination class).
      - "mix" source: ``phase=<name>`` and ``audible_deck=<name>``, written
        ONLY on change (per-tick noise filtering — phase already debounced
        via state.phase_history; deck handled by tracking prev_deck below).

    Lock ordering: ``state._lock`` OUTER, ``EvidenceRegistry._lock`` INNER —
    consistent across all writers (refresh.py + EventDetector._fire). Closes
    Pitfall P12 (registry race) at the runtime boundary. All registry writes
    wrapped in try/except so a downstream failure cannot kill the tick.

    Phase 96 Course 3 lens: optional ``learn_state`` is read-only. This
    function remains the sole writer to ``MusicState``; LearnRuntime never
    writes live audio state. ``session_active`` flips on only when the
    active lesson course is Course 3 and this tick has an audible deck.
    """
    # Lazy-default Phase 6 loop-local state for tests that omit them.
    if crest_smoother is None:
        crest_smoother = EmaSmoother(alpha=0.3)
    if vocal_detector is None:
        vocal_detector = VocalDetector()
    if hysteresis_state is None:
        hysteresis_state = HysteresisState()
    if feature_history is None:
        feature_history = deque(maxlen=5)
    if genre_hysteresis is None:
        genre_hysteresis = GenreHysteresis()

    # Re-read active profile per tick — Phase 12 UI may flip mid-session.
    active_profile = get_active_profile()
    profile_name = active_profile.name if active_profile is not None else "unknown"

    # Audio features (cheap — ~5-10ms)
    feats = snapshot_features(audio_buf, seconds=4.0)
    curve = energy_curve(audio_buf, seconds=12.0, hop=1.0)
    try:
        master_lufs = short_term_lufs(
            audio_buf.snapshot(int(audio_buf._sr * SHORT_TERM_WINDOW_S)),
            audio_buf._sr,
        )
    except Exception:
        master_lufs = None
    rms = feats.get("rms", 0.0)
    currently_loud = rms > SILENT_RMS

    # Phase 6: crest factor over the same 4s window.
    pcm_for_crest = audio_buf.snapshot(int(audio_buf._sr * 4.0))
    raw_crest = crest_factor(pcm_for_crest)
    # Don't smooth on silence — keep last-known value to prevent EMA decay
    # during track gaps.
    if raw_crest > 0:
        smoothed_crest = crest_smoother.update(raw_crest)
    else:
        smoothed_crest = crest_smoother.value

    # BPM updated every 3s — autocorr is heavier
    if now - last_bpm_at > 3.0 and currently_loud:
        raw_bpm = estimate_bpm(audio_buf, seconds=6.0)
        last_bpm_at = now
        if bpm_ring is not None:
            # Median-stabilize: reject transient subdivision locks (the live
            # ~200 BPM cluster) instead of letting a single bad tick flip genre.
            bpm_ring.append(raw_bpm)
            if len(bpm_ring) > _BPM_RING_MAXLEN:
                del bpm_ring[0]
            stabilized = _stabilize_bpm(bpm_ring)
            if stabilized > 0:  # keep last-good until an in-range sample lands
                bpm_cache = stabilized
        else:
            bpm_cache = raw_bpm  # backward-compat path for direct _tick_once tests

    # Phase 6: BPM half/double validation against active profile.
    if active_profile is not None and bpm_cache > 0:
        normalized_bpm, was_corrected = validate_bpm(bpm_cache, active_profile)
        bpm_cache = normalized_bpm
    else:
        was_corrected = False

    # Phase 6: vocal-section detection. Compute BEFORE appending feats so
    # `recent_features` excludes the current snapshot.
    recent_for_vocal = list(feature_history)
    vocal_active = vocal_detector.is_vocal_section(feats, recent_for_vocal, now=now)
    feature_history.append(feats)

    # Audible debouncing — both directions sustained
    if currently_loud:
        if last_audible_high == 0.0:
            last_audible_high = now
        last_audible_low = 0.0
    else:
        if last_audible_low == 0.0:
            last_audible_low = now
        last_audible_high = 0.0

    with state._lock:
        if state.audible:
            if last_audible_low > 0 and (now - last_audible_low) >= SILENCE_DEBOUNCE_SEC:
                state.audible = False
        else:
            if last_audible_high > 0 and (now - last_audible_high) >= AUDIBLE_DEBOUNCE_SEC:
                state.audible = True

        state.rms = rms
        state.master_lufs = master_lufs if currently_loud else None
        state.bands = {
            "sub": feats.get("sub_share", 0.0),
            "low": feats.get("low_share", 0.0),
            "mid": feats.get("mid_share", 0.0),
            "high": feats.get("high_share", 0.0),
        }
        state.onset_density = feats.get("onsets_per_sec", 0.0)
        state.bpm = bpm_cache
        state.energy_curve = curve

        # Phase 6: write the 4 new fields.
        state.crest_factor = round(smoothed_crest, 2)
        state.vocal_active = vocal_active
        state.bpm_corrected = was_corrected
        state.genre_profile_name = profile_name

        # Phase 52 (GENRE-01) — grounded DSP genre auto-detection. Pure-numpy
        # score over features ALREADY computed this tick (stabilized bpm_cache +
        # band shares + smoothed_crest); nearest-match across the cached profile
        # library. Anti-slop: score_genre returns "unknown" below confidence /
        # on a tie, and GenreHysteresis debounces the committed label (no
        # bar-to-bar flicker; "unknown" commits immediately). Written here
        # inside the single-writer batch.
        raw_genre, raw_genre_conf = score_genre(
            bpm_cache,
            {
                "sub": feats.get("sub_share", 0.0),
                "low": feats.get("low_share", 0.0),
                "mid": feats.get("mid_share", 0.0),
                "high": feats.get("high_share", 0.0),
            },
            smoothed_crest,
            _cached_profiles(),
        )
        # Phase 78 (PERCEIVE-03) — reconcile the embedding-genre lookup with the
        # DSP score. The off-loop GenrePrototypeLookup worker (dispatched on
        # TRACK_CHANGE below) fills its OWN holder; here the single writer READS
        # get_latest() (the deck-snapshot copy-in idiom — never the worker
        # writing state.*) and fuses it with the DSP (raw_genre, raw_genre_conf)
        # via reconcile_genre: embedding wins when its NORMALIZED centered-cosine
        # confidence clears coach.py's >=0.5 render band, else DSP fallback.
        #
        # Hysteresis policy: the per-tick DSP score is noisy bar-to-bar, so it is
        # debounced through apply_genre_hysteresis (3-tick dwell). The embedding
        # genre is the opposite — it is dispatched ONLY on TRACK_CHANGE (once per
        # track, not per-tick) and is a high-trust 86.5%-validated signal, so
        # re-debouncing it through the dwell would wrongly suppress a correct
        # genre for the first 3 ticks of every track. When the embedding wins we
        # therefore commit it IMMEDIATELY and RESYNC the hysteresis state to it
        # (mirrors how "unknown" commits immediately) so subsequent DSP ticks do
        # not instantly flip away. genre_source=None / empty holder / sub-floor
        # embedding → pure DSP-through-hysteresis path → v8.0 byte-identical.
        emb_won = False
        if genre_source is not None:
            latest = genre_source.get_latest()
            if latest is not None:
                emb_label, emb_conf = latest
                rec_label, rec_conf = reconcile_genre(
                    emb_label, emb_conf, raw_genre, raw_genre_conf
                )
                # WR-01 — Trust reconcile_genre's output instead of re-deriving the
                # win from labels. reconcile already fused the render-band
                # confidence and decided the win: the embedding won iff it returned
                # the (real, non-"unknown") embedding label at render-band conf
                # (>=0.5). This INCLUDES the embedding↔DSP agreement case
                # (emb_label == raw_genre) — the old guard `emb_label not in
                # (..., raw_genre)` wrongly EXCLUDED agreement, so an agreed-on
                # genre fell back to the low per-tick DSP confidence (e.g. 0.3) and
                # was suppressed at coach.py's >=0.5 render gate even though both
                # signals confidently agreed (RESEARCH Pitfall 4 — the exact
                # over-suppression this path exists to fix). We now commit
                # reconcile's fused render-band confidence so agreement RENDERS.
                # Sub-floor / "unknown" embedding still falls through to the DSP
                # path below (abstain-safety preserved).
                if rec_label == emb_label and emb_label != "unknown" and rec_conf >= 0.5:
                    # Resync the hysteresis dwell only when the committed label is
                    # actually changing (mirrors how "unknown" commits immediately)
                    # so subsequent noisy DSP ticks don't instantly flip away.
                    if genre_hysteresis.current_label != rec_label:
                        genre_hysteresis.current_label = rec_label
                        genre_hysteresis.pending_label = None
                        genre_hysteresis.pending_ticks = 0
                    committed_genre = rec_label
                    state.detected_genre = committed_genre
                    state.genre_confidence = round(rec_conf, 2)
                    emb_won = True
        if not emb_won:
            committed_genre = apply_genre_hysteresis(raw_genre, genre_hysteresis)
            state.detected_genre = committed_genre
            state.genre_confidence = round(raw_genre_conf, 2)

        # Env override wins: only re-point the active profile when the user did
        # NOT explicitly pin a genre (is_auto_enabled), the detector committed a
        # real (non-unknown) genre, and it differs from the current active
        # profile. set_active_profile mutates a module singleton (not
        # MusicState), called from this one tick path only. The honesty fields
        # above are surfaced regardless of the flag.
        if is_auto_enabled() and committed_genre != "unknown" and committed_genre != profile_name:
            try:
                set_active_profile(committed_genre)
            except ValueError:
                pass  # committed name not a loadable profile — never flip

        # Phase 13-05: downbeat-phase + bpm_confidence (mascot beat-lock).
        # Pure function over the same 4-second audio window. Invalid BPM
        # yields (0.0, 0.0) so the renderer (Plan 13-04) falls back to
        # immediate switch — never beat-locks against fabricated phase.
        # mood is owned by SettingsApplier, never touched here.
        new_phase_frac, new_bpm_conf = compute_downbeat_phase(
            pcm_for_crest,
            bpm_cache,
            audio_buf._sr,
            prior_phase=state.downbeat_phase,
        )
        state.downbeat_phase = new_phase_frac
        state.bpm_confidence = new_bpm_conf

        # Phase 17 — Hard Tek detectors v1 (SENSE-13). Three of the four new
        # MusicState fields are written here; `predicted_drop_in_sec` stays at
        # the dataclass default `None` because predictive drop firing is
        # OFF-by-default in v2.0 per CONTEXT D (telemetry-guarded flip is v2.1
        # work, NOT Phase 17). `beat_phase` is a Phase-17-named alias of
        # `downbeat_phase` so SENSE-12 detector module imports don't reach
        # into Phase-13 naming. No new audio I/O — `feats` and `curve` are
        # already in scope from the Phase 6 path above.
        route_preference = committed_genre
        if not is_auto_enabled() and profile_name != "unknown":
            route_preference = profile_name
        state.active_genre = _routeable_active_genre(
            route_preference,
            bpm=bpm_cache,
            feats=feats,
        )
        state.buildup_score = _compute_buildup_score(curve, BUILDUP_SLOPE_WINDOW_S)
        state.beat_phase = state.downbeat_phase

        # Phase — dispatch on active profile.
        if active_profile is None:
            new_phase = classify_phase(curve, state.audible)
        else:
            new_phase, _ = classify_phase(
                curve,
                state.audible,
                profile=active_profile,
                features=feats,
                hysteresis_state=hysteresis_state,
            )

        if new_phase != state.phase:
            state.phase_history.append((now, state.phase, new_phase))
            if len(state.phase_history) > 6:
                state.phase_history.pop(0)
            state.phase = new_phase
            state.phase_started_at = now
            # Phase 18 Plan 02 — mix-source change-only write.
            if evidence_registry is not None:
                try:
                    t_session = max(0.0, now - state.set_start_at)
                    evidence_registry.write("mix", f"phase={new_phase}", t_session)
                except Exception:
                    pass

        # Phase 31 Plan 03 — Mascot emotion derivation (ADDITIVE per
        # Pitfall P47). Pure function over the just-written MusicState
        # fields. The frontend EmotionLayer reads this via the ws_bus
        # `emotion` field and re-fires its priority-60 channel only when
        # the value changes (no per-tick churn).
        time_in_phase = max(0.0, now - state.phase_started_at) if state.phase_started_at else 0.0
        state.emotion = derive_emotion(state.active_genre, state.rms, time_in_phase)

        # Controller snapshot
        cs = controller_state.deck_snapshot()
        state.deck_a = cs["A"]
        state.deck_b = cs["B"]
        state.xfader = cs["xfader"]
        state.controller_connected = cs["connected"]
        (
            state.controller_midi_activity,
            state.controller_midi_messages_seen,
            state.controller_midi_events_seen,
            state.controller_midi_moves_seen,
        ) = classify_controller_midi_activity(
            controller_state,
            connected=state.controller_connected,
        )

        # Audible deck inference. Capture prev_deck BEFORE the assignment so
        # we can detect a deck flip and write a change-only "mix" observation
        # to the EvidenceRegistry (Phase 18 Plan 02).
        prev_deck = state.audible_deck
        aud_deck, deck_conf = derive_audible_deck(cs["A"], cs["B"], cs["xfader"], cs["connected"])
        state.audible_deck = aud_deck
        state.deck_confidence = deck_conf
        course3_live = _course3_session_lens_active(learn_state)
        state.session_active = bool(course3_live and state.audible and aud_deck != "none")
        prev_phrase_cue_id = state.next_phrase_cue_id
        # Course 3 may coach live, but stale forward calls are worse than silence.
        # Clear first; the grounded section-source block below writes these back
        # only after it resolves a DJ-authored cue section and registers evidence.
        state.phrase_position_confidence = 0.0
        state.next_phrase_at = None
        state.next_phrase_cue_id = None
        if evidence_registry is not None and prev_deck != aud_deck:
            try:
                t_session = max(0.0, now - state.set_start_at)
                evidence_registry.write("mix", f"audible_deck={aud_deck}", t_session)
            except Exception:
                pass

        # Track inference (cross-reference with audible deck)
        tsnap = track_info.snapshot()
        tt, tc = derive_audible_track(
            tsnap.get("title") or None, aud_deck, deck_conf, state.audible
        )
        if tt and tc >= 0.5:
            last_title = state.track_history[-1][1] if state.track_history else None
            if tt != last_title:
                state.track_history.append((now, tt))
                if len(state.track_history) > 6:
                    state.track_history.pop(0)
                # Phase 78 (PERCEIVE-03) — TRACK_CHANGE → dispatch the embedding
                # genre lookup OFF the 10Hz tick (mirrors the Grounding off-loop
                # dispatch). clear() FIRST so any superseded in-flight lookup is
                # discarded (generation-token contract from Plan 03); then the
                # worker fills its OWN holder and the next tick READS get_latest()
                # — the worker NEVER writes the live state dataclass (invariant
                # #1). Best-effort: a lookup failure logs and never wedges the
                # tick or the in_flight gate (T-78-04-04).
                if genre_source is not None:
                    _dispatch_genre_lookup(genre_source, tt)
        state.audible_track = tt
        state.audible_track_confidence = tc
        position_s = _optional_float(tsnap.get("position_sec"))
        duration_s = _optional_float(tsnap.get("duration_sec"))
        if tt and tc >= 0.5 and position_s is not None:
            state.audible_track_position_s = max(0.0, position_s)
            state.audible_track_duration_s = duration_s if duration_s and duration_s > 0 else None
            state.audible_track_position_confidence = tc
        else:
            state.audible_track_position_s = None
            state.audible_track_duration_s = None
            state.audible_track_position_confidence = 0.0

        # Phase 59-04 (DECK-04) — deck-state single-writer copy. The deck poller
        # is the THIRD external snapshot producer (after ControllerState /
        # TrackInfo): it writes its OWN holder, and THIS is the only place
        # state.deck_state.decks is ever assigned (single-writer invariant,
        # Pitfall 3). Capture the prior (side, camelot) BEFORE the reassignment so
        # the key:/track: registry writes can be change-only — mirrors the
        # mix:audible_deck prev_deck pattern above.
        if deck_source is not None:
            prev_camelot = {side: dt.camelot for side, dt in state.deck_state.decks.items()}
            deck_snap = deck_source.snapshot()
            for dt in deck_snap.values():
                # Normalize the raw Tonality tag → Camelot inside the lock — pure
                # µs-cost transform on the writer side (RESEARCH §Code Examples).
                dt.camelot = to_camelot(dt.key)
            state.deck_state.decks = deck_snap
            state.deck_state.updated_at = now
            try:
                source_status = (
                    deck_source.source_snapshot()
                    if hasattr(deck_source, "source_snapshot")
                    else {}
                )
            except Exception:
                source_status = {}
            state.deck_state.source_status = (
                dict(source_status) if isinstance(source_status, dict) else {}
            )

            # Change-only, confidence-gated key:/track: registry writes. Bounded
            # registry growth (Pitfall T-59-04-04): only write when a deck's
            # (side, camelot) changes AND the deck clears the citation floor
            # (Pitfall 4 cross-deck suppression — a sub-floor deck is uncitable).
            # try/except so a registry-write failure cannot kill the tick.
            if evidence_registry is not None:
                for side, dt in deck_snap.items():
                    if dt.confidence < DECK_CITE_MIN_CONF or not dt.camelot:
                        continue
                    if prev_camelot.get(side) == dt.camelot:
                        continue  # unchanged — no duplicate write
                    try:
                        t_session = max(0.0, now - state.set_start_at)
                        evidence_registry.write("key", f"{side}:{dt.camelot}", t_session)
                        if dt.track_id:
                            evidence_registry.write("track", dt.track_id, t_session)
                    except Exception:
                        pass
        else:
            deck_snap = None

        state.set_progress = derive_set_progress(
            prepared_pool,
            audible_deck=state.audible_deck,
            deck_state=state.deck_state,
            min_deck_confidence=DECK_CITE_MIN_CONF,
        )

        # Dormant drop-anticipation signal (SYSTEM-AUDIT C9 dead-end). Populate the
        # read-only predicted_drop_in_sec from the audible deck's OWN detected
        # structure (cue_detect / DJ sections — never a hand-fed time, compose-
        # existing). This closes the long-standing None and makes the signal
        # AVAILABLE so its live accuracy can be measured — the prerequisite for the
        # v2.1 telemetry-guarded flip. NO reaction fires on it: predictive drop
        # FIRING stays gated (v2.0 CONTEXT D) until that accuracy is validated.
        _prev_drop = state.predicted_drop_in_sec
        state.predicted_drop_in_sec = None
        if (
            section_source is not None
            and deck_snap is not None
            and state.audible_deck in ("A", "B")
            and state.audible_track_position_s is not None
        ):
            _drop_dt = deck_snap.get(state.audible_deck)
            _drop_track_id = getattr(_drop_dt, "track_id", None) if _drop_dt is not None else None
            if _drop_track_id:
                _drop_entry = _lookup_section_entry(section_source, _drop_track_id)
                if _drop_entry is not None:
                    try:
                        state.predicted_drop_in_sec = predict_drop_in_sec(
                            sections_for_entry(_drop_entry),
                            state.audible_track_position_s,
                            min_confidence=_DROP_CUE_CONF_FLOOR,
                            max_horizon_s=_DROP_HORIZON_S,
                        )
                    except Exception:
                        pass  # detection hiccup → honest None, never wedge the tick
        # Live-bench observability (DROP_DEBUG). The signal stays dormant (no reaction
        # fires), but log the countdown on integer-second crossings + the arrival so we
        # can eyeball predicted-vs-actual drop during a live set. Off unless VIBEMIX_DROP_DEBUG.
        _log_drop_countdown(state.predicted_drop_in_sec, _prev_drop, state.audible_track)

        if state.session_active:
            course3_position_s = state.audible_track_position_s
            course3_position_confidence = state.audible_track_position_confidence
            if (
                course3_position_s is None
                and state.audible_deck == "mix"
                and tt
                and position_s is not None
            ):
                course3_position_s = max(0.0, position_s)
                course3_position_confidence = tc
            anchor = _resolve_course3_phrase_anchor(
                section_source=section_source,
                deck_snap=deck_snap,
                audible_deck=state.audible_deck,
                track_title=tt,
                position_s=course3_position_s,
                position_confidence=course3_position_confidence,
                now=now,
                set_start_at=state.set_start_at,
            )
            if anchor is not None:
                state.phrase_position_confidence = anchor.confidence
                state.next_phrase_at = anchor.next_phrase_at
                state.next_phrase_cue_id = anchor.cue_id
                if evidence_registry is not None and anchor.cue_id != prev_phrase_cue_id:
                    try:
                        evidence_registry.write("cue", anchor.cue_id, anchor.next_phrase_at)
                    except Exception:
                        pass

        # Recent moves
        state.recent_moves = controller_state.moves_since(now - 12.0)
        _update_move_audio_delta(
            state,
            now=now,
            move_audio_baselines=move_audio_baselines,
        )
        audio_delta_items = render_audio_delta_items(state, use_cached=False)
        state.audio_delta = audio_delta_items
        _write_live_grounding_evidence(
            evidence_registry,
            state,
            t_session=max(0.0, now - state.set_start_at),
            evidence_dedupe=evidence_dedupe,
            audio_delta_items=audio_delta_items,
            audio_capture_context=audio_capture_context,
        )
        _write_loop_geometry_evidence(
            evidence_registry,
            controller_state,
            now=now,
            set_start_at=state.set_start_at,
            evidence_dedupe=evidence_dedupe,
        )

        # Long arc — recompute every cycle is fine (cheap reduction over the
        # 16k ring buffer, ~1ms)
        state.long_arc = long_arc_curve(audio_buf, seconds=120.0, hop=10.0)

        # Phase 78 (PERCEIVE-02) — multi-scale trajectory narrative. Composed
        # HERE (after phase_history / recent_moves / long_arc are written this
        # tick) from the ALREADY-bounded fields so it reads consistent values:
        #   - phrase scale: last-3 phase chain from phase_history (capped 6)
        #   - energy-arc scale: buildup_score → "building" / "settled" label
        #   - moves scale: newest recent_moves entry + its age
        # Recomputed each tick from bounded inputs — NEVER accumulated, so the
        # string length is bounded (no unbounded growth). Falsy "" on a cold
        # state → coach's gated branch omits → byte-identity holds.
        state.trajectory_narrative = _compose_trajectory(
            state.phase_history, state.buildup_score, state.recent_moves
        )

        # Phase 18 Plan 02 — aud-source per-tick writes, GATED on state.audible.
        # Silent ticks do NOT register aud observations — closes the
        # "Gemini cites aud:rms@45.2 at a silent moment" hallucination class.
        # All 7 keys are written together so a single snapshot tick exposes
        # the full audio surface to the prompt grammar (Plan 18-03 reads
        # the snapshot once per llm_node invocation).
        if evidence_registry is not None and state.audible:
            try:
                t_session = max(0.0, now - state.set_start_at)
                evidence_registry.write("aud", "rms", t_session)
                evidence_registry.write("aud", "bpm", t_session)
                evidence_registry.write("aud", "onset_density", t_session)
                evidence_registry.write("aud", "sub_share", t_session)
                evidence_registry.write("aud", "low_share", t_session)
                evidence_registry.write("aud", "mid_share", t_session)
                evidence_registry.write("aud", "high_share", t_session)
            except Exception:
                pass

        # Phase 78 (PERCEIVE-01) — prior-tick scalar snapshot. Captured as the
        # LAST write inside the lock so the NEXT tick diffs current-vs-this and
        # the prior it reads is consistent with this tick's committed scalars.
        # SINGLE-WRITER: this is the ONLY assignment of state.prev_perceive.
        # Default {} (no prior) makes the first tick abstain in coach.render_delta.
        state.prev_perceive = {
            "rms": state.rms,
            "master_lufs": state.master_lufs,
            "sub": state.bands.get("sub", 0.0),
            "low": state.bands.get("low", 0.0),
            "mid": state.bands.get("mid", 0.0),
            "high": state.bands.get("high", 0.0),
            "onset_density": state.onset_density,
            "bpm": state.bpm,
            "crest": state.crest_factor,
        }

    return last_audible_high, last_audible_low, bpm_cache, last_bpm_at


async def state_refresh_loop(
    state: MusicState,
    audio_buf: AudioBuffer,
    controller_state: ControllerState,
    track_info: TrackInfo,
    stop_event: asyncio.Event,
    *,
    evidence_registry: EvidenceRegistry | None = None,
    deck_source=None,
    genre_source=None,
    learn_state=None,
    section_source=None,
    prepared_pool_loader=None,
    audio_capture_context: dict[str, object] | None = None,
) -> None:
    """Updates MusicState every 100ms from all sources. The ONLY writer to state.
    Audible flag is debounced — sustained samples required to flip in either
    direction so a brief dip doesn't yank the AI into 'silent' mid-track.

    10Hz cadence (v4:1659 — ``await asyncio.sleep(0.1)`` at top of loop).

    Phase 6: maintains EmaSmoother / VocalDetector / HysteresisState /
    feature_history deque as loop-local state, threaded through _tick_once.
    These are NOT in MusicState — they're internal detector machinery, not
    consumer evidence.

    Phase 18 Plan 02: optional ``evidence_registry`` kwarg threads through
    to ``_tick_once`` on every iteration. When wired, per-tick aud + on-change
    mix observations are written INSIDE the same ``with state._lock:`` batch
    that writes MusicState fields — single-snapshot consistency. Default
    ``None`` preserves backward compat with all existing callers.

    Phase 96 Course 3 lens: optional ``learn_state`` threads the current
    course id into the single-writer loop so ``MusicState.session_active``
    reflects real Course 3 live coaching only when the deck is audible.
    ``section_source`` may be a read-only RekordboxLibrary; when present, Course
    3 count-ins can use DJ-authored cue sections instead of staying cold.

    ``prepared_pool_loader`` is an optional low-frequency hook for the latest
    saved Viber/prepared pool. The loader is polled outside the state lock and
    the cached pool is passed into ``_tick_once`` so the hot path never scans
    the playlist directory at 10Hz.
    """
    last_audible_high = 0.0
    last_audible_low = 0.0
    bpm_cache = 0.0
    last_bpm_at = 0.0
    bpm_ring: list[float] = []  # rolling raw estimates for median stabilization

    # Phase 6 loop-local state — created once per session.
    crest_smoother = EmaSmoother(alpha=0.3)
    active_profile_at_start = get_active_profile()
    vocal_detector = VocalDetector(profile=active_profile_at_start)
    hysteresis_state = HysteresisState()
    feature_history: deque[dict] = deque(maxlen=5)
    # Phase 52 (GENRE-01) loop-local genre-detector hysteresis — separate
    # state object from the phase HysteresisState above; threaded into _tick_once.
    genre_hysteresis = GenreHysteresis()
    evidence_dedupe: set[str] = set()
    prepared_pool = None
    last_prepared_pool_check_at = float("-inf")
    move_audio_baselines: dict[str, dict[str, object]] = {}

    while not stop_event.is_set():
        await asyncio.sleep(0.1)
        try:
            now = time.time()
            if (
                prepared_pool_loader is not None
                and now - last_prepared_pool_check_at >= _PREPARED_POOL_REFRESH_INTERVAL_S
            ):
                last_prepared_pool_check_at = now
                try:
                    prepared_pool = prepared_pool_loader()
                except Exception:
                    prepared_pool = None
            last_audible_high, last_audible_low, bpm_cache, last_bpm_at = _tick_once(
                state,
                audio_buf,
                controller_state,
                track_info,
                now=now,
                last_audible_high=last_audible_high,
                last_audible_low=last_audible_low,
                bpm_cache=bpm_cache,
                last_bpm_at=last_bpm_at,
                bpm_ring=bpm_ring,
                crest_smoother=crest_smoother,
                vocal_detector=vocal_detector,
                hysteresis_state=hysteresis_state,
                feature_history=feature_history,
                evidence_registry=evidence_registry,
                genre_hysteresis=genre_hysteresis,
                deck_source=deck_source,
                genre_source=genre_source,
                learn_state=learn_state,
                section_source=section_source,
                prepared_pool=prepared_pool,
                evidence_dedupe=evidence_dedupe,
                audio_capture_context=audio_capture_context,
                move_audio_baselines=move_audio_baselines,
            )
        except Exception as e:
            print(f"[state refresh err] {e}", file=sys.stderr)
