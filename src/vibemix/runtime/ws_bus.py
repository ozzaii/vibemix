# SPDX-License-Identifier: Apache-2.0
"""ws_broadcast — verbatim port of cohost_v4.py:1872-1918.

Mascot WebSocket bus on ``127.0.0.1:8765``. Inbound: ``{"action":
"trigger"}`` sets ``manual_trigger``. Outbound: 30Hz state snapshot
(levels + audible/deck/phase) to all connected clients. Dead clients are
removed lazily on send failure.

The v4 ``_HAS_WS`` feature flag is dropped — ``websockets`` is now an
explicit pyproject dep (Phase 2 declared it). On import failure the
program fails loud with ImportError; this matches the Phase 2
anti-pattern note in ``02-PATTERNS.md §AntiPatterns-2``.
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from collections import deque
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any, Protocol

import jsonschema as _jsonschema
import websockets

from vibemix.audio import SILENT_RMS, WS_HOST, WS_PORT, Levels
from vibemix.runtime.drop_display import predicted_drop_bars
from vibemix.state import MusicState
from vibemix.state.deck_context import (
    live_evidence_packet,
    render_audio_delta_items,
    render_audio_part_context,
    render_audio_window_context,
    render_audio_window_map,
    render_band_env_context,
    render_deck_audio_context,
    render_deck_audio_delta_context,
    render_deck_audio_features_context,
    render_deck_audio_separation_context,
    render_deck_audio_window_context,
    render_deck_lane_context,
    render_deck_reference_context,
    render_deck_source_context,
)
from vibemix.ui_bus.validator import (
    normalize_legacy_timestamp as _normalize_legacy_timestamp,
)
from vibemix.ui_bus.validator import validate_message as _validate_outbound

if TYPE_CHECKING:
    # WR-06: hint-only import to avoid pulling vibemix.learn into the
    # runtime import graph (the Learn island is optional — present in the
    # full app but not in any reduced runtime). The Protocol below is the
    # actual structural type used in the signature; this import is here
    # purely so type-checkers can verify that the concrete `MidiMirror`
    # satisfies the protocol.
    from vibemix.learn.midi_mirror import MidiMirror  # noqa: F401


class _MidiMirrorProtocol(Protocol):
    """Structural type the ``ws_broadcast`` 30 Hz tick needs from a
    midi_mirror.

    WR-06 fix (REVIEW.md): the kwarg was previously typed ``Any | None``
    so a stale caller passing the wrong object would only surface at
    runtime via the existing try/except (``[learn drain err]`` /
    ``[learn snapshot err]``) — and those messages don't indicate root
    cause. A Protocol captures the call shape (drain + snapshot returning
    well-defined types) without forcing a hard import of the
    :mod:`vibemix.learn` package into this module.
    """

    def drain_pending_detected(self) -> list[dict]: ...

    def snapshot(self) -> dict | None: ...


# ---------------------------------------------------------------------------
# ipc.session.snapshot — wired into the LIVE runtime (the real cohost).
# ---------------------------------------------------------------------------
#
# The Tauri shell spawns the sidecar FLAG-LESS → ``__main__.py:main()`` (the
# real cohost). The app's session panels (meters/bpm/phase/track/cohost
# status/grounded/midi/transcript) are driven by ``ipc.session.snapshot``
# frames — but ``main()`` historically only ran ``ws_broadcast`` here, which
# emitted ONLY the flat mascot frame (no ``type`` field). The unused Phase 12
# W2 ``SessionLoop`` stub was the only emitter of ``ipc.session.snapshot`` and
# the app no longer spawns ``--session``, so every panel was DEAD.
#
# Fix: ``ws_broadcast`` now ALSO emits a schema-valid ``ipc.session.snapshot``
# to the same connected clients (downsampled — see SNAPSHOT_EVERY_N). The
# mascot frame keeps its EXACT shape + 30Hz cadence (mascot.html + the WS
# tests pin both); the snapshot is an ADDITIONAL frame on the same socket.
#
# Snapshot SHAPE + field mapping mirror SessionLoop._build_snapshot (the
# reference stub). Every snapshot is validated before send; on validation /
# emit failure we log to stderr and CONTINUE so a single bad frame can never
# bring the loop down or kill the mascot frames (the snapshot is strictly
# additive — its failure never touches the mascot path).

# Emit one ipc.session.snapshot every Nth mascot tick. 30Hz / 2 = 15Hz —
# plenty for the UI panels, half the wire volume of the mascot stream. The
# mascot sleep stays 1/30 (pinned by test_ws_07); only the snapshot is gated.
SNAPSHOT_EVERY_N: int = 2

# Cap the AI transcript drained per snapshot so a burst can't blow the frame.
_TRANSCRIPT_DRAIN_CAP: int = 8
# MIDI event ribbon cap per snapshot — mirrors SessionLoop.MIDI_EVENT_RING_SIZE.
_MIDI_EVENT_CAP: int = 64

# Emit one ipc.status.tick every Nth mascot tick (~1Hz at 30Hz). The status
# badges (audio/screen/midi) are slow-changing, so 1Hz is ample and keeps the
# screen-permission probe (a sync CGPreflight call) off the hot path. Until
# this existed the live session emitted NO status tick, so the badges stayed
# neutral. HONEST + NEVER-FAULTS by construction: livekit/gemini are emitted
# "ok" (the real gemini-down signal is the SessionLayout grounding-failure
# timer, not this tick; we have no honest audio-drop signal so livekit never
# goes "down"), midi is the real connected-controller count, and screen is a
# live non-prompting probe used only to light the badge — screen-denied is NOT
# a deck fault (audio-only is a valid mode; see faultInput in SessionLayout.ts).
# A missing capture backend reports "unavailable" instead of a false green "ok".
STATUS_EVERY_N: int = 30
_COURSE3_CUE_CONFIDENCE_FLOOR: float = 0.7
_COURSE3_DECK_CITE_MIN_CONF: float = 0.6
_COURSE3_ATTRIBUTED_DECKS = frozenset({"A", "B", "mix"})


def _safe_print(*args: object, **kwargs: object) -> None:
    try:
        print(*args, **kwargs)
    except (BrokenPipeError, OSError):
        pass


def _probe_screen_status(screen_available: bool | None = None) -> str:
    """Return "ok"/"denied"/"unavailable" for live screen capture status.

    ``screen_available=False`` means the capture backend cannot run (missing
    ScreenCaptureKit/Quartz/PIL, or equivalent). Permission denied is distinct:
    the backend exists, but TCC says no. Any probe exception degrades to
    "unavailable" so the UI does not show a false green badge.
    """
    if screen_available is False:
        return "unavailable"
    try:
        from vibemix.platform.permissions import check_screen_recording_permission

        return "ok" if check_screen_recording_permission() == "authorized" else "denied"
    except Exception:
        return "unavailable"


def _probe_midi_count(
    controller_state: Any | None,
    music_state: MusicState | None = None,
) -> int | None:
    """Controller connection count for the compact status badge.

    Detailed movement honesty still lives in ``deck_mixer.midi_activity`` and
    Course 3 operator actions. The footer LED answers the simpler product
    question: is a controller connected to vibemix?
    """
    if music_state is not None:
        try:
            activity = str(getattr(music_state, "controller_midi_activity", "") or "")
            connected = bool(getattr(music_state, "controller_connected", False))
            if connected and activity != "disconnected":
                return 1
            if activity == "disconnected":
                return 0
            messages = max(0, int(getattr(music_state, "controller_midi_messages_seen", 0) or 0))
            if messages > 0:
                return 1
            if connected:
                return 1
        except Exception:
            pass
    if controller_state is None:
        return None
    try:
        return 1 if getattr(controller_state, "port_name", "") else 0
    except Exception:
        return None


def _now_iso() -> str:
    """ISO-8601 UTC timestamp (mirror of ui_bus.messages._now_iso)."""
    from vibemix.ui_bus.messages import _now_iso as _impl

    return _impl()


LIVE_CONTEXT_SCHEMA_VERSION = 2
LIVE_CONTEXT_CAPABILITIES: tuple[str, ...] = (
    "deck_state",
    "deck_mixer",
    "deck_lanes_context",
    "deck_reference_context",
    "deck_source_context",
    "deck_source_status",
    "deck_audio_context",
    "deck_audio_separation_context",
    "deck_audio_features_context",
    "deck_audio_delta_context",
    "deck_audio_window_context",
    "audio_part_context",
    "audio_window_context",
    "audio_window_map",
    "band_env_context",
    "audio_delta",
    "live_evidence",
)


def _serialize_deck_state(state: MusicState) -> dict[str, dict[str, Any]]:
    """Read-only serialize ``MusicState.deck_state`` → flat-frame ``deck_state`` map.

    Maps Phase-59 ``DeckState.decks`` → ``{side: {title, track_id, camelot,
    key, bpm, confidence, source}}`` for the additive field on the flat 30Hz
    mascot frame (PILL-03, the producer half consumed by Plan 62-04's
    deck-chips and Viber live grounding).

    Three invariants this helper exists to GUARANTEE:

      * **Read-only / single-writer** — this is a PURE READ at the serialize
        boundary; it never assigns into ``state.deck_state``. The only writer of
        ``deck_state.decks`` remains ``state_refresh_loop._tick_once`` (DECK-04).
      * **Honest-null (anti-slop)** — ``camelot`` and ``key`` pass THROUGH as-is,
        so an unresolved deck serializes JSON ``null`` (Phase-59
        uncitable-by-construction guarantee carried to the UI surface). Never a
        fabricated key, never recomputed here (``_tick_once`` already normalized
        camelot via ``harmonics.to_camelot``).
      * **Golden-equivalence** — when ``decks`` is empty (the boot / no-decks
        case) this returns ``{}`` so the additive field is inert and existing
        subscribers (mascot.html) are byte-undisturbed.

    ``getattr`` is used defensively so an older state object lacking a
    ``deck_state`` (or a deck_state lacking ``decks``) degrades to ``{}`` rather
    than raising — robust to state-shape skew.
    """
    deck_state = getattr(state, "deck_state", None)
    decks = getattr(deck_state, "decks", None) or {}
    return {
        side: {
            "title": dt.title,
            "track_id": dt.track_id,
            "camelot": dt.camelot,  # honest-null: None -> JSON null, never fabricated
            "key": dt.key,  # honest-null: None -> JSON null, never fabricated
            "genre": dt.genre,  # honest-null: source metadata only, never inferred here
            # honest-null: DeckTrack defaults bpm to 0.0 (typed-empty), NOT None.
            # An unresolved deck (0.0) must NOT serialize a fabricated "0 BPM" on
            # the pill — treat a non-positive bpm as unknown (JSON null), same
            # discipline as camelot/key. Mirrors the snapshot's own
            # `bpm = raw if raw > 0 else None` normalization below (CR-02).
            "bpm": dt.bpm if dt.bpm and dt.bpm > 0.0 else None,
            "confidence": dt.confidence,
            # Source provenance is load-bearing for Viber/Gemini grounding:
            # "rekordbox_xml" is an XML-backed deck row, "folder_cache" is the
            # local folder ingest cache, "screen_vision" is the future
            # independent panel read, and "unknown" stays honest.
            "source": dt.source or "unknown",
        }
        for side, dt in decks.items()
    }


_DECK_SOURCE_STATUS_KEYS: tuple[str, ...] = (
    "controller",
    "controller_connection",
    "controller_midi_activity",
    "controller_midi_messages",
    "controller_midi_events",
    "controller_midi_moves",
    "library",
    "library_tracks",
    "library_source",
    "library_match",
    "nowplaying",
    "nowplaying_owner",
    "nowplaying_title",
    "audible_deck",
    "resolution",
    "resolved_side",
    "second_deck_source",
    "screen_vision",
    "last_known_sides",
    "last_known_rule",
)


def _source_status_token(raw: Any) -> str | None:
    if raw is None:
        return None
    text = " ".join(str(raw).split()).strip()
    if not text:
        return None
    out = "".join(
        ch if (ch.isalnum() or ch in "._:-+=@") else "_" for ch in text[:96].lower()
    ).strip("_")
    return out or None


def _serialize_deck_source_status(state: MusicState) -> dict[str, str]:
    """Read-only serialize bounded deck-source diagnostics.

    This is provenance, not identity proof. It lets Viber/Gemini explain why a
    deck is unresolved (`nowplaying=blocked_non_deck_owner`, etc.) without
    reverse-parsing `deck_source_context[...]` or treating a browser/media-player
    title as deck evidence.
    """
    status = getattr(getattr(state, "deck_state", None), "source_status", None)
    if not isinstance(status, dict):
        return {}
    out: dict[str, str] = {}
    for key in _DECK_SOURCE_STATUS_KEYS:
        token = _source_status_token(status.get(key))
        if token:
            out[key] = token
    return out


def _int_0_127(raw: Any, default: int) -> int:
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return default
    return max(0, min(127, value))


def _serialize_deck_controls(raw: Any) -> dict[str, Any]:
    deck = raw if isinstance(raw, dict) else {}
    return {
        "vol": _int_0_127(deck.get("vol"), 0),
        "eq_low": _int_0_127(deck.get("eq_low"), 64),
        "eq_mid": _int_0_127(deck.get("eq_mid"), 64),
        "eq_hi": _int_0_127(deck.get("eq_hi"), 64),
        "filter": _int_0_127(deck.get("filter"), 64),
        "play": bool(deck.get("play", False)),
    }


def _serialize_deck_mixer(state: MusicState) -> dict[str, Any]:
    """Read-only serialize per-deck mixer posture for live deck reasoning."""
    return {
        "connected": bool(getattr(state, "controller_connected", False)),
        "midi_activity": str(getattr(state, "controller_midi_activity", "unknown") or "unknown"),
        "midi_messages_seen": max(0, int(getattr(state, "controller_midi_messages_seen", 0) or 0)),
        "midi_events_seen": max(0, int(getattr(state, "controller_midi_events_seen", 0) or 0)),
        "midi_moves_seen": max(0, int(getattr(state, "controller_midi_moves_seen", 0) or 0)),
        "xfader": _int_0_127(getattr(state, "xfader", 64), 64),
        "deck_confidence": max(
            0.0,
            min(1.0, float(getattr(state, "deck_confidence", 0.0) or 0.0)),
        ),
        "A": _serialize_deck_controls(getattr(state, "deck_a", {})),
        "B": _serialize_deck_controls(getattr(state, "deck_b", {})),
    }


def _serialize_audio_delta(state: MusicState) -> list[str]:
    """Read-only serialize bounded DSP deltas for Viber live grounding."""
    return render_audio_delta_items(state)


def _serialize_recent_moves(state: MusicState, *, max_age_s: float = 8.0) -> list[str]:
    """Read-only serialize recent controller labels for live move grounding."""
    out: list[str] = []
    for item in getattr(state, "recent_moves", []) or []:
        if not isinstance(item, (list, tuple)) or len(item) < 2:
            continue
        try:
            age = float(item[0])
        except (TypeError, ValueError):
            continue
        label = str(item[1]).strip()
        if age <= max_age_s and label:
            out.append(" ".join(label.split())[:72])
    return out[-6:]


def _serialize_audio_window_context(
    state: MusicState,
    recent_moves: list[str] | tuple[str, ...],
    *,
    force: bool = False,
) -> str | None:
    """Read-only serialize the time map between P1 audio and recent moves."""
    return render_audio_window_context(state, recent_moves, force=force)


def _serialize_audio_window_map(
    state: MusicState,
    recent_moves: list[str] | tuple[str, ...],
    *,
    force: bool = False,
) -> dict[str, Any] | None:
    """Read-only serialize structured P1 old/current/future audio labels."""
    return render_audio_window_map(state, recent_moves, force=force)


def _deck_pair_capture_configured(audio_capture_context: dict[str, object] | None) -> bool:
    """Return True when the live capture has a real A/B deck-pair map."""
    if not isinstance(audio_capture_context, dict):
        return False
    if not bool(audio_capture_context.get("deck_audio_capture_enabled")):
        return False
    deck_channels = audio_capture_context.get("deck_channels")
    if not isinstance(deck_channels, dict):
        return False
    return all(side in deck_channels and deck_channels.get(side) for side in ("A", "B"))


def _serialize_live_evidence(
    state: MusicState,
    *,
    audio_delta_items: list[str] | tuple[str, ...] | None = None,
    audio_capture_context: dict[str, object] | None = None,
) -> dict[str, Any]:
    """Read-only serialize bounded evidence refs for Viber live grounding.

    The payload names evidence categories only: it is not a transition verdict,
    a skill grade, or raw audio. Viber still has to obey the claim policy.
    """
    return live_evidence_packet(
        state,
        audio_delta_items=audio_delta_items,
        audio_capture_context=audio_capture_context,
    )


def _course3_float(raw: Any, default: float = 0.0) -> float:
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


def _course3_deck_has_citable_track(state: MusicState, audible_deck: str) -> bool:
    """True when deck-state can cite the currently audible deck's track.

    Course 3 can only teach phrasing from grounded deck evidence. For A/B we
    require that same side to clear the track confidence floor; for a crossfader
    "mix" attribution, either deck may be the citable source. A stale row on the
    silent side never makes a single-deck attribution look ready.
    """
    deck_state = getattr(state, "deck_state", None)
    decks = getattr(deck_state, "decks", None) or {}
    if not isinstance(decks, dict) or audible_deck not in _COURSE3_ATTRIBUTED_DECKS:
        return False

    if audible_deck in {"A", "B"}:
        candidates = [decks.get(audible_deck)]
    else:
        candidates = list(decks.values())

    for track in candidates:
        if track is None or not getattr(track, "track_id", None):
            continue
        if _course3_float(getattr(track, "confidence", 0.0)) >= _COURSE3_DECK_CITE_MIN_CONF:
            return True
    return False


def _course3_operator_action(
    *,
    blockers: list[str],
    session_active: bool,
    audio_active: bool,
    deck_attributed: bool,
    deck_track_citable: bool,
    cue_ready: bool,
    controller_midi_activity: str,
) -> dict[str, Any] | None:
    """Return one calm Course 3 action from observed lens blockers.

    This is a projection of facts already serialized in ``course3_lens``. It
    does not inspect Rekordbox settings, route devices, or proof artifacts, so
    it cannot claim a specific BlackHole route. The richer route doctor remains
    owned by ``learn_live_readiness.py``; the live socket only says the next
    safe move it can prove from ``MusicState``.
    """
    if cue_ready or not (session_active or audio_active):
        return None
    blocker_set = set(blockers)
    if "waiting_for_audio" in blocker_set:
        return {
            "prompt": "Press play on deck.",
            "steps": [
                "Route Rekordbox to the routed master audio path selected by readiness.",
                "Load and play a real Rekordbox library track.",
                "Raise the playing channel fader and master until the status changes.",
            ],
        }
    if audio_active and controller_midi_activity == "connected_no_midi_traffic":
        return {
            "prompt": "Enable FLX4 MIDI.",
            "steps": [
                "The FLX4 port is visible, but macOS has not delivered any MIDI frames to vibemix.",
                "In Rekordbox controller/MIDI settings, enable FLX4 MIDI output or reconnect the controller.",
                "Move an EQ knob or fader until the status changes from no MIDI traffic.",
            ],
        }
    if audio_active and controller_midi_activity == "midi_traffic_unmapped":
        return {
            "prompt": "Map the controller.",
            "steps": [
                "MIDI frames are arriving, but the active controller profile is not decoding them.",
                "Run the controller sniff tool and update the FLX4/profile mapping before trusting deck moves.",
            ],
        }
    if audio_active and not deck_attributed:
        return {
            "prompt": "Open one channel.",
            "steps": [
                "Open one deck channel so the coach can attribute deck A or B.",
                "Keep the master up while the live lens listens.",
            ],
        }
    if audio_active and deck_attributed and not deck_track_citable:
        return {
            "prompt": "Load a track.",
            "steps": [
                "Load a Rekordbox library track on the audible deck so the coach can cite it.",
            ],
        }
    if "waiting_for_cue" in blocker_set:
        return {
            "prompt": "Keep playing.",
            "steps": [
                "Keep the phrase playing until cue-section lookahead locks the next phrase.",
            ],
        }
    return None


def _serialize_course3_lens(state: MusicState) -> dict[str, Any]:
    """Read-only serialize Course 3 live-teaching lens state.

    The Learn integration pass needs to prove the live audio/course lens without
    peeking into process memory. This rides on the existing flat 30 Hz socket
    frame, just like ``deck_state``. The source remains ``MusicState`` and the
    single writer remains ``state_refresh_loop``; the bus is a dumb wire.

    Defaults are honest-cold:
      - ``session_active=False`` means Course 3 live coaching is not active.
      - ``next_phrase_at=None`` and ``next_phrase_cue_id=None`` mean no citable
        forward count-in exists.
      - confidence is clamped into [0, 1] so malformed test doubles cannot leak
        invalid wire values.
      - readiness fields explain the cold path without making the UI inspect
        unrelated flat-frame fields.
    """
    confidence = getattr(state, "phrase_position_confidence", 0.0)
    try:
        confidence_f = float(confidence)
    except (TypeError, ValueError):
        confidence_f = 0.0
    confidence_f = max(0.0, min(1.0, confidence_f))

    next_phrase_at = getattr(state, "next_phrase_at", None)
    try:
        next_phrase_at_f = float(next_phrase_at) if next_phrase_at is not None else None
    except (TypeError, ValueError):
        next_phrase_at_f = None

    cue_id = getattr(state, "next_phrase_cue_id", None)
    cue_id_s = str(cue_id) if cue_id else None
    session_active = bool(getattr(state, "session_active", False))
    audio_active = (
        bool(getattr(state, "audible", False))
        and _course3_float(getattr(state, "rms", 0.0)) >= SILENT_RMS
    )
    controller_midi_activity = str(
        getattr(state, "controller_midi_activity", "unknown") or "unknown"
    )
    audible_deck = str(getattr(state, "audible_deck", "none") or "none")
    deck_attributed = audible_deck in _COURSE3_ATTRIBUTED_DECKS
    deck_track_citable = _course3_deck_has_citable_track(state, audible_deck)
    cue_ready = (
        session_active
        and confidence_f >= _COURSE3_CUE_CONFIDENCE_FLOOR
        and next_phrase_at_f is not None
        and cue_id_s is not None
    )
    blockers: list[str] = []
    if not audio_active:
        blockers.append("waiting_for_audio")
    if not deck_attributed:
        blockers.append("waiting_for_deck")
    if not deck_track_citable:
        blockers.append("waiting_for_deck_track")
    if not cue_ready:
        blockers.append("waiting_for_cue")
    lens = {
        "session_active": session_active,
        "phrase_position_confidence": confidence_f,
        "next_phrase_at": next_phrase_at_f,
        "next_phrase_cue_id": cue_id_s,
        "audio_active": audio_active,
        "deck_attributed": deck_attributed,
        "deck_track_citable": deck_track_citable,
        "cue_ready": cue_ready,
        "blockers": blockers,
    }
    operator_action = _course3_operator_action(
        blockers=blockers,
        session_active=session_active,
        audio_active=audio_active,
        deck_attributed=deck_attributed,
        deck_track_citable=deck_track_citable,
        cue_ready=cue_ready,
        controller_midi_activity=controller_midi_activity,
    )
    if operator_action is not None:
        lens["operator_action"] = operator_action
    return lens


def _validate_snapshot(msg: dict) -> None:
    """Validate an outbound ipc.session.snapshot against the IPC schema.

    Thin re-export so the snapshot path uses the SAME outbound validator the
    WizardBus / SessionLoop use (``vibemix.ui_bus.validator.validate_message``).
    """
    from vibemix.ui_bus.validator import validate_message as _v

    _v(msg)


def _build_session_snapshot(
    levels: Levels,
    state: MusicState,
    *,
    transcript_buf: deque | None = None,
    controller_state: Any | None = None,
    last_move_ts: list[float] | None = None,
    audio_capture_context: dict[str, object] | None = None,
) -> dict:
    """Build a schema-valid ``ipc.session.snapshot`` dict from live refs.

    Pure-ish builder (the only side effects are draining ``transcript_buf``
    and advancing ``last_move_ts[0]``) so it can be unit-tested against
    fake refs without binding a socket. Mirrors the field mapping in
    ``SessionLoop._build_snapshot``: meters (music/voice/mic), bpm, track
    (title from ``state.audible_track``, deck from ``state.audible_deck``),
    cohost_status (TALKING when voice rms > 0.05, LISTENING when audible music
    is still visible on the live meters, else IDLE), MIDI ribbon, transcript.
    """
    from vibemix.ui_bus.messages import (
        LevelPair,
        LiveClaimPolicyPayload,
        MetersTriple,
        MidiEventEntry,
        SessionSnapshot,
        TrackInfo,
        TranscriptLine,
    )

    snap = levels.snapshot()
    music_rms = max(0.0, min(1.0, float(snap.get("music", 0.0))))
    voice_rms = max(0.0, min(1.0, float(snap.get("voice", 0.0))))
    mic_rms = max(0.0, min(1.0, float(snap.get("mic", 0.0))))
    music_peak = max(0.0, min(1.0, float(snap.get("music_peak", music_rms))))
    voice_peak = max(0.0, min(1.0, float(snap.get("voice_peak", voice_rms))))
    mic_peak = max(0.0, min(1.0, float(snap.get("mic_peak", mic_rms))))
    meters = MetersTriple(
        music=LevelPair(rms=music_rms, peak=music_peak),
        voice=LevelPair(rms=voice_rms, peak=voice_peak),
        mic=LevelPair(rms=mic_rms, peak=mic_peak),
    )

    grounded = bool(getattr(state, "audible", False)) and music_rms > SILENT_RMS
    if voice_rms > 0.05:
        cohost_status = "TALKING"
    elif grounded:
        cohost_status = "LISTENING"
    else:
        cohost_status = "IDLE"

    raw_bpm = _trusted_bpm_for_display(
        state,
        grounded=grounded,
        speaking=cohost_status == "TALKING",
    )
    bpm = raw_bpm if raw_bpm > 0.0 else None
    drop_bpm = raw_bpm if grounded else 0.0
    drop_bars = predicted_drop_bars(getattr(state, "predicted_drop_in_sec", None), drop_bpm)

    audible_track = getattr(state, "audible_track", None)
    audible_deck = getattr(state, "audible_deck", None)
    if grounded and audible_track:
        track = TrackInfo(
            title=str(audible_track),
            artist=None,
            deck=str(audible_deck) if audible_deck else None,
        )
    else:
        track = None

    # Transcript delta — drain newly spoken AI lines (FIFO), capped.
    transcript_delta: tuple[TranscriptLine, ...] = ()
    if transcript_buf is not None and transcript_buf:
        drained: list[TranscriptLine] = []
        while transcript_buf and len(drained) < _TRANSCRIPT_DRAIN_CAP:
            text = transcript_buf.popleft()
            drained.append(
                TranscriptLine(role="ai", text=str(text), ts=_now_iso())  # type: ignore[arg-type]
            )
        transcript_delta = tuple(drained)

    # MIDI ribbon — drain moves observed since the last snapshot. The real
    # ControllerState exposes ``moves_since(t) -> [(age_secs, label), ...]``;
    # we track an absolute wall-clock high-water mark in ``last_move_ts[0]``.
    midi_events: tuple[MidiEventEntry, ...] = ()
    recent_move_labels: tuple[str, ...] = ()
    if controller_state is not None and last_move_ts is not None:
        try:
            now = time.time()
            moves = controller_state.moves_since(last_move_ts[0])
            last_move_ts[0] = now
            if moves:
                recent_move_labels = tuple(
                    str(label) for _age, label in moves[-_MIDI_EVENT_CAP:]
                )
                midi_events = tuple(
                    MidiEventEntry(control=str(label), value=None, ts=_now_iso())
                    for label in recent_move_labels
                )
        except Exception:
            midi_events = ()

    try:
        from vibemix.state.deck_context import live_claim_policy

        policy, reason = live_claim_policy(
            state,
            recent_move_labels,
            audio_capture_context=audio_capture_context,
        )
    except Exception:
        policy, reason = "requires_more_evidence", None
    level = {
        "supported_verdict": "green",
        "candidate_not_verdict": "yellow",
        "watch_not_claim": "yellow",
        "requires_more_evidence": "yellow",
        "blocked": "red",
    }.get(policy, "yellow")
    claim_policy = LiveClaimPolicyPayload(
        policy=policy,  # type: ignore[arg-type]
        level=level,  # type: ignore[arg-type]
        reason=reason,
    )

    msg = SessionSnapshot.make(
        meters=meters,
        phase=(),
        phase_now_pct=0.0,
        bpm=bpm,
        drop_pred_bars=drop_bars,
        transcript_delta=transcript_delta,
        midi_events=midi_events,
        track=track,
        cohost_status=cohost_status,  # type: ignore[arg-type]
        latency_ms=None,
        grounded=grounded,
        claim_policy=claim_policy,
    )
    return json.loads(msg.to_json())


def _trusted_bpm_for_display(
    state: MusicState,
    *,
    grounded: bool,
    speaking: bool = False,
) -> float:
    """Return last-known BPM for UI readouts without treating voice as music.

    ``grounded`` remains the source of truth for live musical evidence. While
    Sven is talking, TTS loopback can briefly make the trusted music gate go
    false; the public counter should hold the cached tempo instead of blinking
    to zero. This never makes ``grounded`` true and never refreshes the BPM from
    the voice-contaminated capture.
    """
    if not (grounded or speaking):
        return 0.0
    try:
        bpm = float(getattr(state, "bpm", 0.0) or 0.0)
    except (TypeError, ValueError):
        return 0.0
    if not (bpm > 0.0):
        return 0.0
    return bpm


def _trusted_flat_bpm(
    state: MusicState,
    *,
    grounded: bool | None = None,
    speaking: bool = False,
) -> float:
    """Return the legacy numeric BPM for the flat mascot/pill frame."""
    if grounded is None:
        grounded = bool(getattr(state, "audible", False))
    return _trusted_bpm_for_display(state, grounded=grounded, speaking=speaking)


class IpcRouterBus:
    """Minimal WizardBus-shaped adapter so the LIVE ``main()`` path can run
    ``SessionLoop``'s request handlers (ipc.settings.*, ipc.profile.*,
    ipc.recordings.*) over the SAME socket ``ws_broadcast`` already owns.

    Why this exists (2026-05-25): the Tauri GUI session window emits
    ipc.settings.set/get + ipc.profile.view + ipc.recordings.list and waits
    for a reply. But the live ``main()`` path serves the bus via
    ``ws_broadcast`` (outbound mascot/snapshot broadcast + manual-trigger only)
    and never instantiated ``SessionLoop`` — so every request silently
    dropped and the renderer timed out (controls looked dead, settings pages
    blank). We can't bind a second listener (One Socket invariant). This
    adapter bridges the gap: ``SessionLoop`` registers its handlers here, and
    ``ws_broadcast`` routes inbound ipc.* frames into ``dispatch`` + lends its
    client set via ``bind_emit`` so handler replies reach every connected
    surface. Reuses SessionLoop's tested handlers verbatim — no duplication.

    Implements only the WizardBus surface SessionLoop touches:
    ``register_handler`` + ``emit``. ``start``/``stop`` are no-ops (ws_broadcast
    owns the server; we never call ``SessionLoop.run()``, only
    ``register_handlers()``).
    """

    def __init__(self) -> None:
        self._handlers: dict[str, Any] = {}
        self._emit: Any | None = None
        self._latest_replayable: dict[str, dict] = {}

    def register_handler(self, message_type: str, handler: Any) -> None:
        self._handlers[message_type] = handler

    def bind_emit(self, emit_fn: Any) -> None:
        """ws_broadcast hands us its 'send dict to all clients' coroutine."""
        self._emit = emit_fn

    async def emit(self, msg: dict) -> None:
        mtype = msg.get("type")
        if mtype == "ipc.library.staleness_nudge":
            self._latest_replayable[mtype] = msg
        if self._emit is not None:
            await self._emit(msg)

    def clear_retained(self, message_type: str) -> None:
        self._latest_replayable.pop(message_type, None)

    async def replay_to(self, ws: Any) -> None:
        """Replay sticky status messages to a newly connected client.

        Most bus frames are edge-triggered events and must not replay. Library
        staleness is user-visible status: boot can detect it before the Tauri
        bridge is connected, so late clients need the latest nudge once.
        """

        for msg in list(self._latest_replayable.values()):
            await ws.send(json.dumps(msg))

    async def start(self) -> None:  # pragma: no cover — never called
        return None

    async def stop(self) -> None:  # pragma: no cover — never called
        return None

    async def dispatch(self, msg: dict) -> bool:
        """Route one inbound frame to its registered handler. Returns True if
        a handler ran (so the caller knows it was a recognized ipc request),
        False otherwise. Never raises — a handler fault is logged + swallowed
        so the ws read loop never wedges."""
        mtype = msg.get("type")
        handler = self._handlers.get(mtype) if isinstance(mtype, str) else None
        if handler is None:
            return False
        try:
            await handler(msg)
        except Exception as e:  # pragma: no cover — defensive
            _safe_print(f"[ipc-router] handler {mtype} failed: {e!r}", file=sys.stderr)
        return True


async def ws_broadcast(
    levels: Levels,
    state: MusicState,
    manual_trigger: asyncio.Event,
    stop_event: asyncio.Event,
    *,
    transcript_buf: deque | None = None,
    controller_state: Any | None = None,
    suggestion_holder: Any | None = None,
    tracer: Any | None = None,
    ipc_router: IpcRouterBus | None = None,
    screen_available: bool | None = None,
    midi_mirror: _MidiMirrorProtocol | None = None,
    audio_capture_context: dict[str, object] | None = None,
    voice_muted: bool = False,
) -> None:
    """30Hz outbound mascot broadcast + inbound manual-trigger handler.

    Verbatim port of cohost_v4.py:1872-1918 with the ``_HAS_WS``
    early-return removed (Phase 2 anti-pattern note — fail loud).

    Additionally emits a schema-valid ``ipc.session.snapshot`` to the same
    clients every ``SNAPSHOT_EVERY_N`` ticks (~15Hz) so the Tauri session
    panels light up under the real cohost. ``transcript_buf`` (an AI-text
    deque, drained per snapshot) and ``controller_state`` (for the MIDI
    ribbon) are OPTIONAL with ``None`` defaults — existing 4-arg callers and
    the WS tests are unaffected. The mascot frame's shape + 30Hz cadence are
    untouched; the snapshot is strictly additive and its failure is isolated.
    """
    clients: set = set()
    # Snapshot downsample counter + MIDI high-water mark (boxed in a list so
    # the builder can advance it across ticks).
    tick = 0
    last_move_ts: list[float] = [time.time()]

    def _tr(event: str, **detail: Any) -> None:
        # Fail-soft WS trace shim. WS frames at 30Hz are NOT traced (too noisy);
        # only high-signal inbound user actions + client (dis)connects are.
        if tracer is None:
            return
        try:
            tracer.ws(event, **detail)
        except Exception:
            pass

    async def _send_all(payload: dict) -> None:
        """Send one schema-shaped dict to every connected client (handler
        replies — settings.state, profile/recordings results). Dead sockets
        are dropped, mirroring the broadcast loop's send guard."""
        msg = json.dumps(payload)
        dead: list = []
        for c in list(clients):
            try:
                await c.send(msg)
            except Exception:
                dead.append(c)
        for c in dead:
            clients.discard(c)

    # Let SessionLoop's handlers (registered on ipc_router) reply over our
    # client set — see IpcRouterBus. Bound once, before any client connects.
    if ipc_router is not None:
        ipc_router.bind_emit(_send_all)

    async def handler(ws):
        clients.add(ws)
        _tr("client_connect", clients=len(clients))
        if ipc_router is not None:
            try:
                await ipc_router.replay_to(ws)
            except Exception:
                clients.discard(ws)
                _tr("client_disconnect", clients=len(clients))
                return
        try:
            async for msg in ws:
                try:
                    data = json.loads(msg) if isinstance(msg, str) else {}
                except Exception:
                    data = {}
                if data.get("action") == "trigger":
                    _safe_print("\n[ws] manual trigger requested")
                    _tr("manual_trigger")
                    manual_trigger.set()
                elif data.get("action") == "next_suggestion.choose":
                    if suggestion_holder is not None and hasattr(
                        suggestion_holder, "choose_alternative"
                    ):
                        try:
                            choice = suggestion_holder.choose_alternative(
                                candidate_id=data.get("candidate_id"),
                                track_id=data.get("track_id"),
                                state=state,
                            )
                        except Exception as e:
                            _safe_print(f"[ws] suggestion choose failed: {e}", file=sys.stderr)
                            choice = None
                        _tr(
                            "next_suggestion_choose",
                            candidate_id=data.get("candidate_id"),
                            track_id=data.get("track_id"),
                            ok=choice is not None,
                        )
                elif data.get("action") == "next_suggestion.feedback":
                    if suggestion_holder is not None and hasattr(
                        suggestion_holder, "record_feedback"
                    ):
                        try:
                            event = suggestion_holder.record_feedback(
                                data.get("feedback"),
                                state=state,
                            )
                        except Exception as e:
                            _safe_print(f"[ws] suggestion feedback failed: {e}", file=sys.stderr)
                            event = None
                        _tr(
                            "next_suggestion_feedback",
                            feedback=data.get("feedback"),
                            ok=event is not None,
                        )
                elif ipc_router is not None and isinstance(data.get("type"), str):
                    # Route ipc.settings.* / ipc.profile.* / ipc.recordings.*
                    # into SessionLoop's handlers (2026-05-25 GUI-control fix).
                    handled = await ipc_router.dispatch(data)
                    if handled:
                        _tr("ipc_request", type=data.get("type"))
        except Exception:
            pass
        finally:
            clients.discard(ws)
            _tr("client_disconnect", clients=len(clients))

    server = await websockets.serve(handler, WS_HOST, WS_PORT)
    _safe_print(
        f"-> mascot bus on ws://{WS_HOST}:{WS_PORT} (send {{action: trigger}} for manual fire)"
    )

    try:
        while not stop_event.is_set():
            # Phase 13-05 — extend the 30Hz snapshot with mood +
            # bpm_confidence + downbeat_phase so the mascot renderer
            # (Plan 13-04) can subscribe to a single stream. Anti-
            # hallucination: bpm_confidence < 0.6 → renderer skips
            # beat-locked entry; mood drives clip-pool + voice swap.
            #
            # Phase 22-02 — extend further with `beat_phase` +
            # `active_genre`. `beat_phase` is a Phase-17-named alias of
            # `downbeat_phase` (both ∈ [0, 1) — fraction-through-current-
            # bar). Both ride on the wire simultaneously because the
            # Plan 13-06 dispatcher binds to `downbeat_phase` and the
            # Phase 22 anticipation/hip-bob layers bind to `beat_phase`;
            # carrying both lets the renderer migrate incrementally
            # without breaking existing subscribers. `active_genre` is a
            # registered event-chain genre (or "unknown") and feeds the
            # GenreRouter on the renderer side. Anti-hallucination is
            # the renderer's job (the bus is a dumb wire) — under low
            # bpm_confidence the bus still emits beat_phase as-is and
            # the renderer (Plan 13-04 Open Q 4) ignores beat-locked
            # behavior.
            # Phase 31 — 4-layer mascot extension (ADDITIVE per Pitfall
            # P47). `emotion` ("neutral"/"focused"/"hyped"/"concerned"/
            # None) drives the priority-60 EmotionLayer on the frontend.
            # `reaction_intent` (MascotReaction whitelist value / None)
            # and `reaction_intent_seq` are set by the AICoach emote-tag
            # parser and consumed by the mascot. The seq lets the 30Hz
            # frontend subscriber fire each intent once while still allowing
            # the same intent to re-fire on a later co-host turn.
            # Build the mascot frame as a dict FIRST so we can gate the send
            # at the emit boundary (BRINGUP-04). The key set / ordering / 30Hz
            # cadence are unchanged — the guard below only decides whether to
            # PUT this tick on the wire, it never reshapes a valid frame.
            audio_delta = _serialize_audio_delta(state)
            recent_moves = _serialize_recent_moves(state)
            force_audio_window = _deck_pair_capture_configured(audio_capture_context)
            audio_window_context = _serialize_audio_window_context(
                state,
                recent_moves,
                force=force_audio_window,
            )
            audio_window_map = _serialize_audio_window_map(
                state,
                recent_moves,
                force=force_audio_window,
            )
            audio_part_context = render_audio_part_context(
                audio_seconds=6.0,
                surface="live_context",
                p1_model_heard=False,
            )
            deck_lanes_context = render_deck_lane_context(state)
            deck_reference_context = render_deck_reference_context(state)
            deck_source_context = render_deck_source_context(state)
            deck_audio_context = render_deck_audio_context(state)
            deck_audio_separation_context = render_deck_audio_separation_context(
                audio_capture_context
            )
            deck_audio_features_context = render_deck_audio_features_context(audio_capture_context)
            deck_audio_delta_context = render_deck_audio_delta_context(audio_capture_context)
            deck_audio_window_context = render_deck_audio_window_context(audio_capture_context)
            band_env_context = render_band_env_context(state)
            deck_source_status = _serialize_deck_source_status(state)
            level_snap = levels.snapshot()
            level_voice_rms = max(0.0, min(1.0, float(level_snap.get("voice", 0.0))))
            # The flat mascot/pill frame is a compact UI readout, so hold BPM
            # against the debounced MusicState audible flag. The richer
            # ipc.session.snapshot still carries the stricter grounded flag.
            level_grounded = bool(getattr(state, "audible", False))
            mascot_frame = {
                **level_snap,
                "live_context_schema_version": LIVE_CONTEXT_SCHEMA_VERSION,
                "live_context_capabilities": list(LIVE_CONTEXT_CAPABILITIES),
                "audible": state.audible,
                "deck": state.audible_deck,
                "phase": state.phase,
                "bpm": _trusted_flat_bpm(
                    state,
                    grounded=level_grounded,
                    speaking=level_voice_rms > 0.05,
                ),
                "mood": state.mood,
                "bpm_confidence": state.bpm_confidence,
                "downbeat_phase": state.downbeat_phase,
                "beat_phase": state.beat_phase,
                "active_genre": state.active_genre,
                # Phase 52 (GENRE-02) — additive. `detected_genre` is the FULL-
                # LIBRARY auto-detected genre name (Plan 52-03), distinct from
                # the routeable `active_genre` event-chain signal above.
                # Anti-hallucination is honored at the SOURCE: the
                # detector writes "unknown" when it is unsure, so the bus is a
                # dumb wire that carries the value as-is — never a fabricated
                # label. `genre_confidence` is the detector's score in [0,1].
                "detected_genre": state.detected_genre,
                "genre_confidence": state.genre_confidence,
                "emotion": state.emotion,
                "reaction_intent": state.last_reaction_intent,
                "reaction_intent_seq": state.last_reaction_intent_seq,
                # Phase 62 (PILL-03) — additive, read-only. The per-deck
                # ``deck_state`` map ({side: {title, camelot, key, bpm,
                # confidence}}) read from the Phase-59 ``MusicState.deck_state``
                # so the pill's deck-context chips have a real per-deck source.
                # Honest-null is preserved: an unresolved deck carries
                # ``camelot: null`` / ``key: null`` (never a fabricated key —
                # the bus is a dumb wire). Empty deck_state -> ``{}`` so this
                # field is golden-equivalent for existing subscribers. This is a
                # PURE READ at the serialize edge; the single writer
                # (``_tick_once``) is upstream and untouched.
                "deck_state": _serialize_deck_state(state),
                # Per-deck mixer posture — additive, read-only. This is the
                # cheap controller context Viber/Gemini need to distinguish
                # "deck A low was cut" from "a musical transition happened":
                # deck faders/EQ/filter/play, crossfader, and attribution
                # confidence. It is evidence only, not a quality verdict.
                "deck_mixer": _serialize_deck_mixer(state),
                # Structured source/provenance diagnostics, separate from deck
                # identity. The text prompt context below is for LLM grammar;
                # this map is for lossless UI/Viber transport and debugging.
                **({"deck_source_status": deck_source_status} if deck_source_status else {}),
                # Direct deck1/deck2 text maps for Viber/Gemini. These repeat
                # the same state as deck_state/deck_mixer in a bounded prompt
                # grammar so downstream agents do not have to infer that
                # deck1=A/deck2=B from separate fields. They are context, not
                # verdicts, and are omitted when the source state is cold.
                **({"deck_lanes_context": deck_lanes_context} if deck_lanes_context else {}),
                **(
                    {"deck_reference_context": deck_reference_context}
                    if deck_reference_context
                    else {}
                ),
                **({"deck_source_context": deck_source_context} if deck_source_context else {}),
                **({"deck_audio_context": deck_audio_context} if deck_audio_context else {}),
                "deck_audio_separation_context": deck_audio_separation_context,
                **(
                    {"deck_audio_features_context": deck_audio_features_context}
                    if deck_audio_features_context
                    else {}
                ),
                **(
                    {"deck_audio_delta_context": deck_audio_delta_context}
                    if deck_audio_delta_context
                    else {}
                ),
                **(
                    {"deck_audio_window_context": deck_audio_window_context}
                    if deck_audio_window_context
                    else {}
                ),
                "audio_part_context": audio_part_context,
                # Bounded DSP deltas from the existing perceive snapshot. This
                # gives Viber/Gemini a cheap "what changed in the sound" hint
                # around recent moves without adding another model/audio pass.
                "audio_delta": audio_delta,
                **({"band_env_context": band_env_context} if band_env_context else {}),
                # Time-aligned "old/action/future" context for Viber/Gemini.
                # This is a live timing contract, not an audio stem and not a
                # quality verdict. Recent moves annotate it when present; cold
                # frames still carry move_anchor=none whenever live state gives
                # us a reference (controller, audio, deck rows, or lookahead).
                **({"recent_moves": recent_moves} if recent_moves else {}),
                **({"audio_window_context": audio_window_context} if audio_window_context else {}),
                **({"audio_window_map": audio_window_map} if audio_window_map else {}),
                # Bounded evidence keys for Viber/Gemini. These are citable
                # categories (deck route, move scope, DSP delta, MIDI move),
                # not quality verdicts; existing consumers can ignore them.
                "live_evidence": _serialize_live_evidence(
                    state,
                    audio_delta_items=audio_delta,
                    audio_capture_context=audio_capture_context,
                ),
                # Learn Course 3 live lens — additive, read-only. Lets the
                # integration pass verify live audio/course/phrase readiness
                # over the existing socket without inspecting process memory.
                # Honest-cold defaults mean no citable count-in exists.
                "course3_lens": _serialize_course3_lens(state),
            }
            # Phase (PILL next-suggestion) — additive, read-only. The pill's
            # "what's next" card reads ``next_suggestion`` = the latest grounded
            # suggestion dict ({track_id, title, artist, similarity, why,
            # camelot, bpm, transition, decision}) or ``null`` (honest silence
            # — never a fabricated track). Full ranking is computed off-loop by
            # the SuggestionService on TRACK_CHANGE; this serialize edge may ask
            # the holder for a throttled live refresh so the shortlist winner,
            # validator-checked decision, and "in N bars" follow the playhead
            # without reranking the library at 30Hz. Guarded so a holder fault
            # can never break the wire; absent when no holder is wired
            # (golden-equivalent for existing subscribers).
            if suggestion_holder is not None:
                try:
                    if hasattr(suggestion_holder, "current_for_state"):
                        mascot_frame["next_suggestion"] = suggestion_holder.current_for_state(state)
                    else:
                        mascot_frame["next_suggestion"] = suggestion_holder.current()
                except Exception as e:
                    _safe_print(f"[ws] suggestion read failed: {e}", file=sys.stderr)
            # Emit-boundary guard (BRINGUP-04): never serialize an empty or
            # meter-less payload onto the wire. ``Levels.snapshot()`` always
            # returns the 3 meter keys and the static keys above are literal,
            # so this branch is normally unreachable — but it makes the
            # "no {} / no meter-less frame" contract permanent at the SEND
            # boundary regardless of any future upstream regression (a
            # snapshot returning {} or a state attr vanishing). A skipped
            # tick keeps the loop + cadence intact; we just don't send a
            # malformed frame. Logged once-per-occurrence to stderr.
            if not mascot_frame or not all(k in mascot_frame for k in ("music", "voice", "mic")):
                _safe_print(
                    "[ws] skipped malformed mascot frame "
                    f"(missing meter keys; got {sorted(mascot_frame)})",
                    file=sys.stderr,
                )
                await asyncio.sleep(1 / 30)
                continue
            payload = json.dumps(mascot_frame)
            dead = []
            for c in list(clients):
                try:
                    await c.send(payload)
                except Exception:
                    dead.append(c)
            for c in dead:
                clients.discard(c)

            # Phase 91 (RENDER-01 + RENDER-02) — Learn surface emit.
            # Drain THEN snapshot, in that strict order: a fresh plug-in's
            # ipc.learn.controller_detected envelope MUST hit the wire BEFORE
            # any ipc.learn.midi_position envelope from the same controller, so
            # the webview sees "controller appeared" before it sees position
            # data for that controller. Both envelopes ride the SAME _send_all
            # closure (Invariant #4 preserved — no second WS listener); the
            # port_watcher callback in __main__ ENQUEUES via
            # midi_mirror.queue_controller_detected and never calls _send_all
            # directly (that closure is not reachable from outside this
            # coroutine). Each step is guarded by its own try/except so a
            # learn-side fault NEVER touches the mascot path above or the
            # snapshot path below.
            if midi_mirror is not None:
                # 1) Drain controller_detected queue and emit each pending
                # envelope. The drain itself is cheap (locked O(N) copy+clear;
                # N is normally 0 — plug-in events are user-driven, ≤1/s).
                try:
                    pending = midi_mirror.drain_pending_detected()
                except Exception as e:
                    _safe_print(f"[learn drain err] {e}", file=sys.stderr)
                    pending = []
                for envelope in pending:
                    try:
                        await _send_all(envelope)
                    except Exception as e:
                        _safe_print(f"[learn detected emit err] {e}", file=sys.stderr)
                # 2) Pull position snapshot. midi_mirror.snapshot() returns
                # None when no profile is bound or when no tracked control's
                # integer LSB has changed since the last call (delta
                # suppression — RESEARCH §Pattern 2).
                try:
                    pos_frame = midi_mirror.snapshot()
                except Exception as e:
                    _safe_print(f"[learn snapshot err] {e}", file=sys.stderr)
                    pos_frame = None
                if pos_frame is not None:
                    try:
                        await _send_all(pos_frame)
                    except Exception as e:
                        _safe_print(f"[learn pos emit err] {e}", file=sys.stderr)

            # Additive ipc.session.snapshot @ ~15Hz (every Nth tick). Built +
            # validated + sent in its OWN try/except so a bad snapshot frame
            # NEVER touches the mascot path above or the loop cadence below.
            tick += 1
            if tick % SNAPSHOT_EVERY_N == 0:
                try:
                    snap_msg = _build_session_snapshot(
                        levels,
                        state,
                        transcript_buf=transcript_buf,
                        controller_state=controller_state,
                        last_move_ts=last_move_ts,
                        audio_capture_context=audio_capture_context,
                    )
                    _validate_snapshot(snap_msg)
                    snap_payload = json.dumps(snap_msg, separators=(",", ":"))
                    snap_dead = []
                    for c in list(clients):
                        try:
                            await c.send(snap_payload)
                        except Exception:
                            snap_dead.append(c)
                    for c in snap_dead:
                        clients.discard(c)
                except Exception as e:
                    _safe_print(f"[ws snapshot] emit failed: {e}", file=sys.stderr)

            # Additive ipc.status.tick @ ~1Hz (every STATUS_EVERY_N ticks).
            # Lights the status-row badges (audio/screen/midi). Built + sent in
            # its OWN try/except so a status fault NEVER touches the mascot or
            # snapshot paths above. Values are honest + never-fault (see the
            # STATUS_EVERY_N comment): livekit/gemini="ok", midi=real count,
            # screen=live probe (badge-only, not a deck fault).
            if tick % STATUS_EVERY_N == 0:
                try:
                    from vibemix.ui_bus.messages import StatusTick

                    status_msg = StatusTick.make(
                        livekit="ok",
                        gemini="ok",
                        midi=_probe_midi_count(controller_state, state),
                        screen=_probe_screen_status(screen_available),
                        voice="muted" if voice_muted else "ok",
                    )
                    status_payload = status_msg.to_json()
                    status_dead = []
                    for c in list(clients):
                        try:
                            await c.send(status_payload)
                        except Exception:
                            status_dead.append(c)
                    for c in status_dead:
                        clients.discard(c)
                except Exception as e:
                    _safe_print(f"[ws status] emit failed: {e}", file=sys.stderr)

            await asyncio.sleep(1 / 30)
    finally:
        server.close()
        await server.wait_closed()


# ---------------------------------------------------------------------------
# Phase 11 Wave 4 — WizardBus: handler-registration + ipc.* dispatch.
# ---------------------------------------------------------------------------
#
# The WizardBus runs ONLY in ``--wizard`` mode (the live-runtime ``main()``
# uses ``ws_broadcast`` above which has a different lifecycle and is
# mascot-only). Both bind ``127.0.0.1:8765`` — they never run at the same
# time because the Tauri shell spawns ``vibemix --wizard`` first, waits for
# ``ipc.wizard.done``, then respawns ``vibemix`` without the flag.
#
# Inbound message dispatch:
#   1. Parse JSON → dict.
#   2. ``vibemix.ui_bus.validator.validate_message(dict)`` — drop frame on
#      ValidationError; do NOT close the socket (T-11-W4-04 mitigation).
#   3. Route to a handler registered for ``msg["type"]``; if none, log + drop.
#
# Outbound: ``emit(dict)`` validates the schema before broadcasting (catches
# Python-side schema drift at runtime — RESEARCH Pitfall 10).
#
# The mascot.html broadcast contract is NOT extended here. The wizard does
# not broadcast levels/state — those are computed by the live-runtime
# ``state_refresh_loop`` which only exists in the non-wizard process.


IpcHandler = Callable[[dict], Awaitable[None]]


class WizardBus:
    """ipc.* WS bus for the calibration wizard (Phase 11 Wave 4).

    Wraps ``websockets.serve(127.0.0.1:8765)`` with a per-message-type
    handler dispatch table. Handlers are registered via ``register_handler``
    and invoked when an inbound frame matches their ``type``. Outbound
    broadcasts via ``emit`` validate the schema before send.

    Single-writer assumption: this class is constructed once per wizard
    process. ``start()`` opens the server; ``stop()`` closes it. The
    sidecar exits cleanly when the WizardLoop sets its stop event after
    receiving ``ipc.wizard.done``.
    """

    def __init__(self) -> None:
        self._clients: set = set()
        self._handlers: dict[str, IpcHandler] = {}
        self._server: object | None = None

    def register_handler(self, message_type: str, handler: IpcHandler) -> None:
        """Register an async handler for a given ipc.* message type.

        Multiple registrations for the same type overwrite — last-write
        wins. The WizardLoop registers all 8 handlers up front, so this
        case shouldn't fire in production.
        """
        self._handlers[message_type] = handler

    async def start(self) -> None:
        """Open the WS server on 127.0.0.1:8765. Idempotent — second
        call is a no-op if already running."""
        if self._server is not None:
            return
        self._server = await websockets.serve(self._handler, WS_HOST, WS_PORT)
        _safe_print(f"-> wizard bus on ws://{WS_HOST}:{WS_PORT} (handlers: {len(self._handlers)})")

    async def stop(self) -> None:
        """Close the server. Safe to call multiple times."""
        if self._server is None:
            return
        self._server.close()  # type: ignore[attr-defined]
        await self._server.wait_closed()  # type: ignore[attr-defined]
        self._server = None
        self._clients.clear()

    async def emit(self, msg: dict) -> None:
        """Broadcast an ipc.* message to all connected clients.

        Validates against the schema first — Python-side schema drift
        surfaces here at runtime (NOT just at codegen / CI). Validation
        failure raises; the WizardLoop wraps emits in try/except so a
        bad outbound frame doesn't crash the wizard.
        """
        _validate_outbound(msg)
        payload = json.dumps(msg, separators=(",", ":"))
        dead = []
        for c in list(self._clients):
            try:
                await c.send(payload)
            except Exception:
                dead.append(c)
        for c in dead:
            self._clients.discard(c)

    async def _handler(self, ws) -> None:
        """Per-connection inbound loop. Accepts ipc.* frames, dispatches
        to the registered handler, drops invalid frames without closing
        the socket (T-11-W4-04)."""
        self._clients.add(ws)
        try:
            async for raw in ws:
                if not isinstance(raw, str):
                    # Binary frames are not part of the ipc.* contract; ignore.
                    continue
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError as e:
                    _safe_print(f"[wizard bus] non-JSON frame: {e}", file=sys.stderr)
                    continue
                if not isinstance(msg, dict):
                    _safe_print(
                        f"[wizard bus] top-level not object: {type(msg).__name__}",
                        file=sys.stderr,
                    )
                    continue
                msg = _normalize_legacy_timestamp(msg)
                try:
                    validate_message(msg)
                except _jsonschema.ValidationError as e:
                    _safe_print(f"[wizard bus] schema violation: {e.message}", file=sys.stderr)
                    continue
                msg_type = msg.get("type", "")
                handler = self._handlers.get(msg_type)
                if handler is None:
                    _safe_print(
                        f"[wizard bus] no handler for {msg_type}",
                        file=sys.stderr,
                    )
                    continue
                try:
                    await handler(msg)
                except Exception as e:
                    # Handler-internal failure must not close the WS.
                    _safe_print(
                        f"[wizard bus] handler {msg_type} failed: {e}",
                        file=sys.stderr,
                    )
        except Exception:
            pass
        finally:
            self._clients.discard(ws)


def validate_message(msg: dict) -> None:
    """Thin re-export of ``vibemix.ui_bus.validator.validate_message`` for
    internal use. Exposed at this scope so ``WizardBus`` can be tested
    with monkey-patched validation without reaching into ``ui_bus``.
    """
    from vibemix.ui_bus.validator import validate_message as _v

    _v(msg)


# Phase 12 — ``IpcBus`` is the neutral alias for ``WizardBus`` used by
# ``SessionLoop``. The bus is mutually exclusive with the wizard at
# runtime (Tauri spawns one process at a time) and the dispatch surface
# is identical — so we share the class instead of forking it.
IpcBus = WizardBus


__all__ = ["IpcBus", "IpcHandler", "WizardBus", "validate_message", "ws_broadcast"]
