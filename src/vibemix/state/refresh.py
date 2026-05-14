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
import sys
import time
from collections import deque
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
from vibemix.state.evidence_registry import EvidenceRegistry
from vibemix.state.genre import (
    EmaSmoother,
    HysteresisState,
    VocalDetector,
    crest_factor,
    get_active_profile,
    validate_bpm,
)
from vibemix.state.music_state import MusicState
from vibemix.state.phase import classify_phase
from vibemix.state.track_resolver import derive_audible_deck, derive_audible_track


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
    crest_smoother: EmaSmoother | None = None,
    vocal_detector: VocalDetector | None = None,
    hysteresis_state: HysteresisState | None = None,
    feature_history: deque[dict] | None = None,
    evidence_registry: EvidenceRegistry | None = None,
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

    # Re-read active profile per tick — Phase 12 UI may flip mid-session.
    active_profile = get_active_profile()
    profile_name = active_profile.name if active_profile is not None else "unknown"

    # Audio features (cheap — ~5-10ms)
    feats = snapshot_features(audio_buf, seconds=4.0)
    curve = energy_curve(audio_buf, seconds=12.0, hop=1.0)
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
        bpm_cache = estimate_bpm(audio_buf, seconds=6.0)
        last_bpm_at = now

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
        state.active_genre = _classify_active_genre(bpm_cache, feats)
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

        # Controller snapshot
        cs = controller_state.deck_snapshot()
        state.deck_a = cs["A"]
        state.deck_b = cs["B"]
        state.xfader = cs["xfader"]
        state.controller_connected = cs["connected"]

        # Audible deck inference. Capture prev_deck BEFORE the assignment so
        # we can detect a deck flip and write a change-only "mix" observation
        # to the EvidenceRegistry (Phase 18 Plan 02).
        prev_deck = state.audible_deck
        aud_deck, deck_conf = derive_audible_deck(cs["A"], cs["B"], cs["xfader"], cs["connected"])
        state.audible_deck = aud_deck
        state.deck_confidence = deck_conf
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
        state.audible_track = tt
        state.audible_track_confidence = tc

        # Recent moves
        state.recent_moves = controller_state.moves_since(now - 12.0)

        # Long arc — recompute every cycle is fine (cheap reduction over the
        # 16k ring buffer, ~1ms)
        state.long_arc = long_arc_curve(audio_buf, seconds=120.0, hop=10.0)

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

    return last_audible_high, last_audible_low, bpm_cache, last_bpm_at


async def state_refresh_loop(
    state: MusicState,
    audio_buf: AudioBuffer,
    controller_state: ControllerState,
    track_info: TrackInfo,
    stop_event: asyncio.Event,
    *,
    evidence_registry: EvidenceRegistry | None = None,
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
    """
    last_audible_high = 0.0
    last_audible_low = 0.0
    bpm_cache = 0.0
    last_bpm_at = 0.0

    # Phase 6 loop-local state — created once per session.
    crest_smoother = EmaSmoother(alpha=0.3)
    active_profile_at_start = get_active_profile()
    vocal_detector = VocalDetector(profile=active_profile_at_start)
    hysteresis_state = HysteresisState()
    feature_history: deque[dict] = deque(maxlen=5)

    while not stop_event.is_set():
        await asyncio.sleep(0.1)
        try:
            now = time.time()
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
                crest_smoother=crest_smoother,
                vocal_detector=vocal_detector,
                hysteresis_state=hysteresis_state,
                feature_history=feature_history,
                evidence_registry=evidence_registry,
            )
        except Exception as e:
            print(f"[state refresh err] {e}", file=sys.stderr)
