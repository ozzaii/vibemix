# SPDX-License-Identifier: Apache-2.0
"""EventDetector — verbatim port of cohost_v4.py:1169-1325.

THREE STRUCTURAL DEVIATIONS FROM V4:
  1. (Phase 3) v4:1182-1186 had three class-level constants
     (MUSIC_PRESENCE_MIN_SECONDS, BPM_VALID_MIN, BPM_VALID_MAX). 02-PATTERNS.md
     + 03-CONTEXT.md lifted them OUT to ``vibemix.audio.constants`` so all
     tuning lives in one place. EventDetector imports them at module scope
     here; the class no longer defines them as attributes.
  2. (Phase 6) LAYER_ARRIVAL is now gated on ``not state.vocal_active`` —
     vocal-arrival band jumps are suppressed when the vocal-section detector
     (Phase 6 Wave 2) has flagged active vocals (06-CONTEXT.md §EventDetector).
     The baseline ``self.last_band_signature = sig`` line is preserved so a
     non-vocal post-vocal jump doesn't false-fire against a stale baseline.
     Every other gate + cooldown is v4 byte-identical.
  3. (Phase 17 Plan 05) EventDetector now COMPOSES a ``GenreRouter`` (SENSE-11)
     and consults its active chain on every ``.detect()`` call AFTER the v4
     baseline rules (TRACK_CHANGE / PHASE / LAYER_ARRIVAL / MIX_MOVE) and
     BEFORE the HEARTBEAT fallthrough. The constructor gains an OPTIONAL
     ``audio_buf=None`` kwarg that's threaded through to chain detectors
     that need raw samples (KickSwap, PhraseBoundary). Default ``None``
     preserves backward compat with ``EventDetector()`` callers (coach.py
     unchanged; tests that exercise baseline rules unchanged).

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

Priority order with the genre chain inserted:
    KAAN_SPOKE > MANUAL > [music-presence gate] > TRACK_CHANGE > PHASE
    > LAYER_ARRIVAL > MIX_MOVE > [genre-chain detectors in chain order]
    > HEARTBEAT
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from vibemix.audio.constants import (
    BPM_VALID_MAX,
    BPM_VALID_MIN,
    EVENT_GLOBAL_MIN_GAP,
    LOW_RMS,
    MIN_EVENT_GAP_PER_TYPE,
    MUSIC_PRESENCE_MIN_SECONDS,
    TRACK_CHANGE_MIN_CONFIDENCE,
)
from vibemix.state.deck_poller import DECK_CITE_MIN_CONF
from vibemix.state.event import Event
from vibemix.state.evidence_registry import EvidenceRegistry
from vibemix.state.genre_router import GenreRouter
from vibemix.state.harmonics import is_clash, semitone_distance
from vibemix.state.music_state import MusicState

if TYPE_CHECKING:
    from vibemix.audio.buffers import AudioBuffer

# Phase 60 (HARMONIC-02) — tonal-share floor for the melodic-overlap gate.
# A clash needs simultaneous MELODIC content. A drum-only / atonal tool track
# parks almost all energy in sub/low; require a minimum combined mid+high share
# so percussive overlaps ("hard to clash where there's hardly any harmony",
# FEATURES line 56) are suppressed. Deliberately conservative — start low and
# only raise if false-fires appear in the Kaan-ear corpus (Plan 60-03).
TONAL_SHARE_FLOOR: float = 0.20


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

    def __init__(
        self,
        audio_buf: "AudioBuffer | None" = None,
        *,
        evidence_registry: EvidenceRegistry | None = None,
        harmonic_clash_enabled: bool = False,
    ) -> None:
        """Construct EventDetector with optional ``audio_buf`` for genre-chain
        detectors that need raw samples (KickSwap, PhraseBoundary).

        Default ``audio_buf=None`` preserves backward compat — every existing
        caller (``coach.py`` test fixtures, the v4-baseline test suite) still
        constructs ``EventDetector()`` with no arguments. Genre detectors that
        need samples will gracefully no-op when audio_buf is None (their
        snapshot calls return empty data → first-call seeding only).

        Phase 18 Plan 02: optional ``evidence_registry`` kwarg threads the
        EvidenceRegistry through to ``_fire`` so every event fire writes a
        ``[ev:<TYPE>@<t_session>]`` observation. Default ``None`` preserves
        backward compat with all existing callers (tests + standalone runs)
        — registry writes are best-effort and skipped when not wired."""
        self.last_event_at = 0.0
        self.last_per_type_at: dict[str, float] = {}
        self.last_phase: str = "silent"
        self.last_audible_track: str | None = None
        self.last_band_signature: tuple[float, float] | None = None
        self.last_mix_moves_seen: list[str] = []
        # Music-presence tracking
        self._audible_since: float | None = None

        # Phase 17 Plan 05 — genre-chain composition. Router defaults to
        # the "unknown" baseline chain (empty list), so behavior matches v4
        # byte-identical until a state with active_genre != "unknown"
        # arrives. The audio_buf is THREADED through to chain detectors on
        # every iteration (see .detect() below).
        self.audio_buf = audio_buf
        self.router = GenreRouter(initial_genre="unknown")

        # Phase 18 Plan 02 — EvidenceRegistry write target. None = no-op path.
        # Registry write happens INSIDE _fire AFTER cooldown bookkeeping so
        # a registry exception cannot corrupt cooldown gates (Test D pin).
        self._registry: EvidenceRegistry | None = evidence_registry

        # Phase 60 Plan 02 (HARMONIC-02/03) — default-OFF harmonic-clash gate.
        # Mirrors DeckPoller._vision_enabled (deck_poller.py:97-116): the
        # KEY_CLASH + TRANSITION_OPPORTUNITY branches stay COMPLETELY quiet
        # until this flips. False is conservative-by-design — a wrong key tag
        # (~57-70% library accuracy) reaching the audience as false expertise
        # is the exact anti-slop hallucination class this phase guards. The
        # flag flips ONLY after the Kaan-ear veto corpus passes (Plan 60-03 —
        # the KAAN-ACTION ship gate). Until then NO clash reaches the audience,
        # even with a fully-resolved clashing deck pair. The kwarg shape mirrors
        # ``vision_enabled`` so a caller / test flips it without monkeypatching.
        self._harmonic_clash_enabled = bool(harmonic_clash_enabled)

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

    def _melodic_overlap_gate(self, state: MusicState) -> bool:
        """True iff BOTH decks are plausibly contributing simultaneous MELODIC
        content — the precondition for ANY clash note (HARMONIC-02).

        Built ENTIRELY from shipped MusicState signals (no new detector stack,
        no new audio computation). A clash note CANNOT fire unless this returns
        True. Suppresses, in order:
          1. single-deck (audible_deck != "mix") — no overlap to clash;
          2. sub-LOW_RMS sections — a dropped-out mix disguises a clash;
          3. breakdown / silent / low phase — harmony has dropped out, keys
             don't matter (FEATURES line 57);
          4. acapella overlap (vocal_active) — no instrumental harmony to clash;
          5. percussive / atonal content — combined mid+high band share below
             TONAL_SHARE_FLOOR ≈ drum-only tool track (FEATURES line 56).

        Read-only: never writes deck-state (single-writer rule in refresh.py)."""
        if state.audible_deck != "mix":
            return False
        if state.rms < LOW_RMS:
            return False
        if state.phase in ("breakdown", "silent", "low"):
            return False
        if state.vocal_active:
            return False
        if (state.bands.get("mid", 0.0) + state.bands.get("high", 0.0)) < TONAL_SHARE_FLOOR:
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

        # Phase 17 Plan 05 — atomic chain swap on active_genre flip. The swap
        # happens HERE at the top of detect(), BEFORE any iteration so a swap
        # mid-call cannot leave a half-iterated chain (T-17-05-02 mitigation).
        # Same-genre swap is a no-op (idempotent — chain detectors keep their
        # seeded baselines across spurious-equal flips).
        if state.active_genre != self.router.current_genre:
            self.router.swap(state.active_genre)

        # Mic + manual bypass silence guards (conversation/control events)
        if kaan_just_spoke and self._cooldown_ok("MIC", now):
            # cooldown_key="MIC" preserves v4's MIC cooldown bucket, but the
            # registry observation is keyed on the EVENT TYPE ("KAAN_SPOKE")
            # so the prompt grammar + Phase 20 linter see the externally
            # visible event name, not the internal cooldown bucket.
            self._fire("KAAN_SPOKE", now, state, cooldown_key="MIC")
            return Event("KAAN_SPOKE", state)

        if manual and self._cooldown_ok("MANUAL", now):
            self._fire("MANUAL", now, state)
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
                self._fire("TRACK_CHANGE", now, state)
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
                self._fire("PHASE", now, state)
                return ev
        self.last_phase = state.phase

        # 3) Layer arrival — sudden jump in mid or high band share
        sig = (round(state.bands["mid"], 2), round(state.bands["high"], 2))
        if self.last_band_signature is not None and self._cooldown_ok("LAYER_ARRIVAL", now):
            mid_jump = sig[0] - self.last_band_signature[0]
            high_jump = sig[1] - self.last_band_signature[1]
            if (
                (mid_jump > 0.15 or high_jump > 0.10)
                and state.rms > LOW_RMS
                and not state.vocal_active
            ):
                ev = Event(
                    "LAYER_ARRIVAL",
                    state,
                    extra={
                        "mid_jump": round(mid_jump, 2),
                        "high_jump": round(high_jump, 2),
                    },
                )
                self.last_band_signature = sig
                self._fire("LAYER_ARRIVAL", now, state)
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
            self._fire("MIX_MOVE", now, state)
            return ev
        # Always keep seen-list fresh so we don't replay old moves later
        self.last_mix_moves_seen = [m for _, m in state.recent_moves][-12:]

        # 4a) KEY_CLASH (Phase 60 Plan 02 — HARMONIC-02/03). Deterministic
        # harmonic clash on a simultaneous melodic overlap. Placed AFTER
        # MIX_MOVE so a real structural mix move still beats a clash, BEFORE the
        # genre chain + HEARTBEAT fallthrough. Layered conservatism:
        #   (i)   default-off flag — quiet until the Kaan-ear veto (Plan 60-03);
        #   (ii)  _melodic_overlap_gate — both decks melodic + audible + tonal;
        #   (iii) cross-deck + cite-floor — BOTH decks resolved (camelot) AND
        #         confidence >= DECK_CITE_MIN_CONF (a sub-floor deck has NO key:
        #         observation in Phase 59, so a clash citing it would be stripped
        #         anyway — we gate here so we never even emit the turn);
        #   (iv)  is_clash() — the deterministic Camelot verdict (Plan 60-01);
        #   (v)   the inherited 28s KEY_CLASH cooldown.
        # READ-ONLY on deck-state (single-writer rule). The LLM later only
        # narrates the verdict — it never computes the interval.
        if self._harmonic_clash_enabled and self._melodic_overlap_gate(state):
            decks = state.deck_state.decks
            a, b = decks.get("A"), decks.get("B")
            if (
                a is not None
                and b is not None
                and a.camelot
                and b.camelot
                and a.confidence >= DECK_CITE_MIN_CONF
                and b.confidence >= DECK_CITE_MIN_CONF
                and is_clash(a.camelot, b.camelot)
                and self._cooldown_ok("KEY_CLASH", now)
            ):
                ev = Event(
                    "KEY_CLASH",
                    state,
                    extra={
                        "a_side": "A",
                        "a_camelot": a.camelot,
                        "b_side": "B",
                        "b_camelot": b.camelot,
                        "semitones": semitone_distance(a.camelot, b.camelot),
                    },
                )
                self._fire("KEY_CLASH", now, state)
                return ev

        # 4b) TRANSITION_OPPORTUNITY (Phase 60 Plan 02 — HARMONIC-04).
        # RETROSPECTIVE, groundable-only blend note. Open Q2 / §5: vibemix has
        # NO per-deck phrase grid and NO dual-deck low-band, so phrase-alignment
        # / bass-swap notes are NOT groundable and MUST stay silent (silence over
        # a guess — acceptable to be near-zero this phase). We fire ONLY on what
        # deck-state CAN ground retrospectively: BOTH decks resolved + cited AND
        # a recent STRUCTURAL xfader/EQ move (reusing the MIX_MOVE significance
        # keys) that indicates a blend just happened. The coach narrates it
        # past-tense ("you just blended A→B, the keys sit fine / clash") — no
        # present-tense imperative (those arrive 5-10s late, Pitfall 3).
        if self._harmonic_clash_enabled and self._cooldown_ok("TRANSITION_OPPORTUNITY", now):
            decks = state.deck_state.decks
            a, b = decks.get("A"), decks.get("B")
            both_cited = (
                a is not None
                and b is not None
                and a.camelot
                and b.camelot
                and a.confidence >= DECK_CITE_MIN_CONF
                and b.confidence >= DECK_CITE_MIN_CONF
            )
            structural_blend = any(
                any(
                    k in label
                    for k in ("killed", "_low:", "_mid:", "_hi:", "_filter:", "xfader")
                )
                for _age, label in state.recent_moves
            )
            if both_cited and structural_blend:
                ev = Event(
                    "TRANSITION_OPPORTUNITY",
                    state,
                    extra={
                        "a_side": "A",
                        "a_camelot": a.camelot,
                        "b_side": "B",
                        "b_camelot": b.camelot,
                        "clash": is_clash(a.camelot, b.camelot),
                    },
                )
                self._fire("TRANSITION_OPPORTUNITY", now, state)
                return ev

        # 5) Genre-chain detectors (Phase 17 Plan 05 — SENSE-11 / SENSE-15).
        # Iterate the active per-genre chain in registration order; first
        # detector to return an Event wins. The audio_buf threaded into
        # __init__ is passed to each detector — those that don't need it
        # (SubLayerArrival, KickDensityShift, BreakdownKickKill) ignore it.
        # This is BEFORE the HEARTBEAT step so a real genre event always
        # beats the long-silence catch-all.
        for det in self.router.active_chain():
            ev = det.detect(state, self.audio_buf, now)
            if ev is not None:
                return ev

        # 6) Heartbeat — long silence in conversation while music is going
        if self._cooldown_ok("HEARTBEAT", now):
            self._fire("HEARTBEAT", now, state)
            return Event("HEARTBEAT", state)

        return None

    def _fire(
        self,
        ev_type: str,
        now: float,
        state: MusicState,
        *,
        cooldown_key: str | None = None,
    ) -> None:
        """Update cooldown bookkeeping + write the [ev:<TYPE>@<t>] observation.

        ``ev_type`` is the EXTERNALLY visible event name (the ``Event.type``
        the caller returns). ``cooldown_key`` defaults to ``ev_type`` and is
        only overridden for the KAAN_SPOKE → "MIC" mapping that preserves
        v4's MIC cooldown bucket while exposing the event-type name to the
        registry / prompt grammar.

        Cooldown bookkeeping (``last_event_at`` + ``last_per_type_at``) is
        updated FIRST and is authoritative. Registry write follows in a
        try/except — a registry failure must NEVER block event firing or
        corrupt cooldown gates (Test D pin, T-18-02-04 mitigation).

        ``t_session`` is ``now - state.set_start_at`` clamped at 0.0 so an
        unset ``set_start_at`` (== 0.0) doesn't write a unix-timestamp-sized
        float into the registry. Sub-second resolution preserved (no rounding
        at write time — Phase 20 linter owns rounding per GROUND-07).
        """
        bucket = cooldown_key or ev_type
        self.last_event_at = now
        self.last_per_type_at[bucket] = now

        # Phase 18 Plan 02 — registry write. Best-effort: a downstream
        # registry exception cannot leak past the cooldown contract.
        if self._registry is not None:
            try:
                t_session = max(0.0, now - state.set_start_at)
                self._registry.write("ev", ev_type, t_session)
            except Exception:
                pass
