# SPDX-License-Identifier: Apache-2.0
"""state_refresh_loop — the 10Hz single writer to MusicState.

Verbatim port of cohost_v4.py:1647-1751 with **ONE structural deviation** from
v4: the four audio-related calls that v4 made as METHODS on ``AudioBuffer`` are
rewritten here as FREE FUNCTION calls per Phase 2's refactor (Phase 2 SUMMARY
rationale: testability without standing up the whole audio package).

The rewrites (every other line is byte-for-byte v4):
    v4: audio_buf.snapshot_features(seconds=4.0)
    P3: snapshot_features(audio_buf, seconds=4.0)

    v4: audio_buf.energy_curve(seconds=12.0, hop=1.0)
    P3: energy_curve(audio_buf, seconds=12.0, hop=1.0)

    v4: audio_buf.estimate_bpm(seconds=6.0)
    P3: estimate_bpm(audio_buf, seconds=6.0)

    v4: audio_buf.long_arc_curve(seconds=120.0, hop=10.0)
    P3: long_arc_curve(audio_buf, seconds=120.0, hop=10.0)

Single-writer contract: this is the ONLY function in the codebase that writes
to MusicState fields. EventDetector and AICoach are read-only. The write
batch is wrapped in ``with state._lock:`` so multi-field consistent snapshots
are achievable by readers that opt in (most readers don't bother — single-tick
read tearing is acceptable at 10Hz cadence).

Error wrap: the entire per-tick body is ``try / except Exception``; the loop
NEVER exits on exception (verbatim v4 behavior — keep running even if one
feature snapshot throws).
"""

from __future__ import annotations

import asyncio
import sys
import time
from typing import TYPE_CHECKING

from vibemix.audio import (
    AUDIBLE_DEBOUNCE_SEC,
    SILENCE_DEBOUNCE_SEC,
    SILENT_RMS,
    AudioBuffer,
    energy_curve,
    estimate_bpm,
    long_arc_curve,
    snapshot_features,
)
from vibemix.state.music_state import MusicState
from vibemix.state.phase import classify_phase
from vibemix.state.track_resolver import derive_audible_deck, derive_audible_track

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
) -> tuple[float, float, float, float]:
    """One iteration of the state_refresh_loop body. Extracted so tests can
    drive single ticks deterministically with fake time and fake snapshots.

    Returns the updated (last_audible_high, last_audible_low, bpm_cache,
    last_bpm_at) tuple for the caller to thread through the next tick.

    The body is v4:1660-1751 verbatim except for the four free-function
    rewrites described in the module docstring.
    """
    # Audio features (cheap — ~5-10ms)
    feats = snapshot_features(audio_buf, seconds=4.0)
    curve = energy_curve(audio_buf, seconds=12.0, hop=1.0)
    rms = feats.get("rms", 0.0)
    currently_loud = rms > SILENT_RMS

    # BPM updated every 3s — autocorr is heavier
    if now - last_bpm_at > 3.0 and currently_loud:
        bpm_cache = estimate_bpm(audio_buf, seconds=6.0)
        last_bpm_at = now

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

        # Phase
        new_phase = classify_phase(curve, state.audible)
        if new_phase != state.phase:
            state.phase_history.append((now, state.phase, new_phase))
            if len(state.phase_history) > 6:
                state.phase_history.pop(0)
            state.phase = new_phase
            state.phase_started_at = now

        # Controller snapshot
        cs = controller_state.deck_snapshot()
        state.deck_a = cs["A"]
        state.deck_b = cs["B"]
        state.xfader = cs["xfader"]
        state.controller_connected = cs["connected"]

        # Audible deck inference
        aud_deck, deck_conf = derive_audible_deck(cs["A"], cs["B"], cs["xfader"], cs["connected"])
        state.audible_deck = aud_deck
        state.deck_confidence = deck_conf

        # Track inference (cross-reference with audible deck)
        tsnap = track_info.snapshot()
        tt, tc = derive_audible_track(
            tsnap.get("title") or None, aud_deck, deck_conf, state.audible
        )
        # Record audibly-confirmed track flips into track_history (only when
        # confidence is decent — prevents jittery deck inference from polluting
        # the history with phantom transitions).
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

    return last_audible_high, last_audible_low, bpm_cache, last_bpm_at


async def state_refresh_loop(
    state: MusicState,
    audio_buf: AudioBuffer,
    controller_state: ControllerState,
    track_info: TrackInfo,
    stop_event: asyncio.Event,
) -> None:
    """Updates MusicState every 100ms from all sources. The ONLY writer to state.
    Audible flag is debounced — sustained samples required to flip in either
    direction so a brief dip doesn't yank the AI into 'silent' mid-track.

    10Hz cadence (v4:1659 — ``await asyncio.sleep(0.1)`` at top of loop).
    """
    last_audible_high = 0.0
    last_audible_low = 0.0
    bpm_cache = 0.0
    last_bpm_at = 0.0

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
            )
        except Exception as e:
            print(f"[state refresh err] {e}", file=sys.stderr)
