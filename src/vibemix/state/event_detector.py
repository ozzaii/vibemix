# SPDX-License-Identifier: Apache-2.0
"""EventDetector — verbatim port of cohost_v4.py:1169-1325.

ONE STRUCTURAL DEVIATION FROM V4: v4:1182-1186 had three class-level constants
(MUSIC_PRESENCE_MIN_SECONDS, BPM_VALID_MIN, BPM_VALID_MAX). 02-PATTERNS.md +
03-CONTEXT.md lifted them OUT to ``vibemix.audio.constants`` so all tuning
lives in one place. EventDetector imports them at module scope here; the
class no longer defines them as attributes. Every other line of the v4 body
is byte-for-byte identical.

The three cardinal rules (from v4:1170-1180):
    1. KAAN_SPOKE + MANUAL always bypass the music-presence gate.
    2. Auto-events only fire when MUSIC IS TRULY PLAYING — meaning
       continuous audible RMS for MUSIC_PRESENCE_MIN_SECONDS AND a BPM in
       the valid dance-music range. This kills phantom triggers from mic
       ambient + stale nowplaying-cli entries.
    3. Quality > quantity: skip an ambiguous event rather than fire a bad one.

MIX_MOVE significance keys (v4:1299-1305 — verbatim, this is the v4 anti-slop
tightening from v3's looser set):
    ('killed', '_low:', '_mid:', '_hi:', '_filter:', 'xfader', 'big', '_play→')
"""

from __future__ import annotations

import time

from vibemix.audio.constants import (
    BPM_VALID_MAX,
    BPM_VALID_MIN,
    EVENT_GLOBAL_MIN_GAP,
    LOW_RMS,
    MIN_EVENT_GAP_PER_TYPE,
    MUSIC_PRESENCE_MIN_SECONDS,
    TRACK_CHANGE_MIN_CONFIDENCE,
)
from vibemix.state.event import Event
from vibemix.state.music_state import MusicState


class EventDetector:
    """Reads MusicState diffs, emits at most ONE event per cycle.
    Returns None most of the time. Cardinal rules:
      1. KAAN_SPOKE + MANUAL always bypass.
      2. Auto-events only fire when MUSIC IS TRULY PLAYING — meaning
         continuous audible RMS for MUSIC_PRESENCE_MIN_SECONDS AND a BPM in
         the valid dance-music range. This kills phantom triggers from mic
         ambient + stale nowplaying-cli entries.
      3. Quality > quantity: skip an ambiguous event rather than fire a bad
         one. The AI should feel attentive, not chatty."""

    # v4:1182-1186 had MUSIC_PRESENCE_MIN_SECONDS / BPM_VALID_MIN / BPM_VALID_MAX
    # as class-level attrs. 02-PATTERNS.md + 03-CONTEXT.md lifted them to
    # vibemix.audio.constants so the constants are configurable from one place.
    # EventDetector imports them at module scope (above); no class-attrs needed.

    def __init__(self):
        self.last_event_at = 0.0
        self.last_per_type_at: dict[str, float] = {}
        self.last_phase: str = "silent"
        self.last_audible_track: str | None = None
        self.last_band_signature: tuple[float, float] | None = None
        self.last_mix_moves_seen: list[str] = []
        # Music-presence tracking
        self._audible_since: float | None = None

    def _cooldown_ok(self, ev_type: str, now: float) -> bool:
        gap = MIN_EVENT_GAP_PER_TYPE.get(ev_type, EVENT_GLOBAL_MIN_GAP)
        last = self.last_per_type_at.get(ev_type, 0.0)
        return (now - last) > gap and (now - self.last_event_at) > EVENT_GLOBAL_MIN_GAP

    def _music_truly_playing(self, state: MusicState, now: float) -> bool:
        """Sustained-audible + valid-BPM gate. Eliminates phantom auto-fires
        from mic ambient and stale nowplaying-cli entries."""
        if state.audible:
            if self._audible_since is None:
                self._audible_since = now
        else:
            self._audible_since = None
            return False
        if (now - self._audible_since) < MUSIC_PRESENCE_MIN_SECONDS:
            return False
        bpm = state.bpm or 0
        if bpm < BPM_VALID_MIN or bpm > BPM_VALID_MAX:
            return False
        return True

    def _reset_change_refs(self, state: MusicState) -> None:
        """When music isn't truly playing we still keep the change-detection
        refs in sync with the current state — so that the moment music DOES
        start, we don't fire spurious 'change' events on stale baselines."""
        self.last_phase = state.phase
        self.last_audible_track = state.audible_track
        self.last_band_signature = None
        self.last_mix_moves_seen = [m for _, m in state.recent_moves][-12:]

    def detect(self, state: MusicState, *, kaan_just_spoke: bool, manual: bool) -> Event | None:
        now = time.time()

        # Mic + manual bypass silence guards (conversation/control events)
        if kaan_just_spoke and self._cooldown_ok("MIC", now):
            self._fire("MIC", now)
            return Event("KAAN_SPOKE", state)

        if manual and self._cooldown_ok("MANUAL", now):
            self._fire("MANUAL", now)
            return Event("MANUAL", state)

        # MUSIC-TRULY-PLAYING GATE — the cardinal rule. No auto-events
        # while mic ambient is fluttering RMS, while a stale nowplaying-cli
        # title is hanging around from another app, or while BPM autocorr
        # is locking onto noise. The AI stays quiet until Kaan actually
        # mixes something.
        if not self._music_truly_playing(state, now):
            self._reset_change_refs(state)
            return None

        # 1) Track change — new audible track different from last seen.
        # Gate on confidence so stale nowplaying-cli entries from other apps
        # (Spotify / YouTube / a paused djay deck) don't trigger phantom events.
        if (
            state.audible_track
            and state.audible_track != self.last_audible_track
            and state.audible_track_confidence >= TRACK_CHANGE_MIN_CONFIDENCE
        ):
            if self._cooldown_ok("TRACK_CHANGE", now):
                ev = Event(
                    "TRACK_CHANGE",
                    state,
                    extra={
                        "prev_track": self.last_audible_track,
                        "new_track": state.audible_track,
                    },
                )
                self.last_audible_track = state.audible_track
                self._fire("TRACK_CHANGE", now)
                return ev
        self.last_audible_track = state.audible_track

        # 2) Phase transition — significant change with cooldown
        if state.phase != self.last_phase and state.phase not in ("silent",):
            if self._cooldown_ok("PHASE", now):
                ev = Event(
                    "PHASE",
                    state,
                    extra={
                        "prev_phase": self.last_phase,
                        "new_phase": state.phase,
                    },
                )
                self.last_phase = state.phase
                self._fire("PHASE", now)
                return ev
        self.last_phase = state.phase

        # 3) Layer arrival — sudden jump in mid or high band share
        sig = (round(state.bands["mid"], 2), round(state.bands["high"], 2))
        if self.last_band_signature is not None and self._cooldown_ok("LAYER_ARRIVAL", now):
            mid_jump = sig[0] - self.last_band_signature[0]
            high_jump = sig[1] - self.last_band_signature[1]
            if (mid_jump > 0.15 or high_jump > 0.10) and state.rms > LOW_RMS:
                ev = Event(
                    "LAYER_ARRIVAL",
                    state,
                    extra={
                        "mid_jump": round(mid_jump, 2),
                        "high_jump": round(high_jump, 2),
                    },
                )
                self.last_band_signature = sig
                self._fire("LAYER_ARRIVAL", now)
                return ev
        self.last_band_signature = sig

        # 4) Mix move — significant controller move while audible. Only react to
        # NEW moves (not seen before this cycle). Significance: vol up/down,
        # xfader edge crossings, EQ kills/restores, filter extremes, play toggles.
        new_significant = []
        for _age, label in state.recent_moves:
            if label in self.last_mix_moves_seen:
                continue
            if any(
                k in label
                for k in (
                    "killed",  # any EQ kill
                    "_low:",
                    "_mid:",
                    "_hi:",
                    "_filter:",  # EQ band tier change
                    "xfader",  # xfader move
                    "big",  # large vol move
                    "_play→",  # deck play/pause
                )
            ):
                new_significant.append(label)
        if new_significant and self._cooldown_ok("MIX_MOVE", now):
            self.last_mix_moves_seen = [m for _, m in state.recent_moves][-12:]
            ev = Event("MIX_MOVE", state, extra={"moves": new_significant[-3:]})
            self._fire("MIX_MOVE", now)
            return ev
        # Always keep seen-list fresh so we don't replay old moves later
        self.last_mix_moves_seen = [m for _, m in state.recent_moves][-12:]

        # 5) Heartbeat — long silence in conversation while music is going
        if self._cooldown_ok("HEARTBEAT", now):
            self._fire("HEARTBEAT", now)
            return Event("HEARTBEAT", state)

        return None

    def _fire(self, ev_type: str, now: float):
        self.last_event_at = now
        self.last_per_type_at[ev_type] = now
