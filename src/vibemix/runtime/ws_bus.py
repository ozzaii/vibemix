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
from typing import Any

import jsonschema as _jsonschema
import websockets

from vibemix.audio import WS_HOST, WS_PORT, Levels
from vibemix.state import MusicState
from vibemix.ui_bus.validator import validate_message as _validate_outbound

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


def _probe_midi_count(controller_state: Any | None) -> int | None:
    """Honest count of the connected controller from the shared ControllerState.

    v1 tracks a single active port (``port_name``) — 1 when a controller is
    open, 0 when none. ``None`` when no controller_state is wired (the badge
    then reads neutral, not a fabricated zero)."""
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


def _serialize_deck_state(state: MusicState) -> dict[str, dict[str, Any]]:
    """Read-only serialize ``MusicState.deck_state`` → flat-frame ``deck_state`` map.

    Maps Phase-59 ``DeckState.decks`` → ``{side: {title, camelot, key, bpm,
    confidence}}`` for the additive field on the flat 30Hz mascot frame (PILL-03,
    the producer half consumed by Plan 62-04's deck-chips).

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
            "camelot": dt.camelot,  # honest-null: None -> JSON null, never fabricated
            "key": dt.key,  # honest-null: None -> JSON null, never fabricated
            # honest-null: DeckTrack defaults bpm to 0.0 (typed-empty), NOT None.
            # An unresolved deck (0.0) must NOT serialize a fabricated "0 BPM" on
            # the pill — treat a non-positive bpm as unknown (JSON null), same
            # discipline as camelot/key. Mirrors the snapshot's own
            # `bpm = raw if raw > 0 else None` normalization below (CR-02).
            "bpm": dt.bpm if dt.bpm and dt.bpm > 0.0 else None,
            "confidence": dt.confidence,
        }
        for side, dt in decks.items()
    }


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
) -> dict:
    """Build a schema-valid ``ipc.session.snapshot`` dict from live refs.

    Pure-ish builder (the only side effects are draining ``transcript_buf``
    and advancing ``last_move_ts[0]``) so it can be unit-tested against
    fake refs without binding a socket. Mirrors the field mapping in
    ``SessionLoop._build_snapshot``: meters (music/voice/mic), bpm, track
    (title from ``state.audible_track``, deck from ``state.audible_deck``),
    cohost_status (TALKING when voice rms > 0.05, LISTENING when audible,
    else IDLE), grounded (= ``state.audible``), MIDI ribbon, transcript.
    """
    from vibemix.ui_bus.messages import (
        LevelPair,
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
    meters = MetersTriple(
        music=LevelPair(rms=music_rms, peak=music_rms),
        voice=LevelPair(rms=voice_rms, peak=voice_rms),
        mic=LevelPair(rms=mic_rms, peak=mic_rms),
    )

    grounded = bool(getattr(state, "audible", False))
    if voice_rms > 0.05:
        cohost_status = "TALKING"
    elif grounded:
        cohost_status = "LISTENING"
    else:
        cohost_status = "IDLE"

    raw_bpm = float(getattr(state, "bpm", 0.0) or 0.0)
    bpm = raw_bpm if raw_bpm > 0.0 else None

    audible_track = getattr(state, "audible_track", None)
    audible_deck = getattr(state, "audible_deck", None)
    if audible_track:
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
    if controller_state is not None and last_move_ts is not None:
        try:
            now = time.time()
            moves = controller_state.moves_since(last_move_ts[0])
            last_move_ts[0] = now
            if moves:
                midi_events = tuple(
                    MidiEventEntry(control=str(label), value=None, ts=_now_iso())
                    for _age, label in moves[-_MIDI_EVENT_CAP:]
                )
        except Exception:
            midi_events = ()

    msg = SessionSnapshot.make(
        meters=meters,
        phase=(),
        phase_now_pct=0.0,
        bpm=bpm,
        drop_pred_bars=None,
        transcript_delta=transcript_delta,
        midi_events=midi_events,
        track=track,
        cohost_status=cohost_status,  # type: ignore[arg-type]
        latency_ms=None,
        grounded=grounded,
    )
    return json.loads(msg.to_json())


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

    def register_handler(self, message_type: str, handler: Any) -> None:
        self._handlers[message_type] = handler

    def bind_emit(self, emit_fn: Any) -> None:
        """ws_broadcast hands us its 'send dict to all clients' coroutine."""
        self._emit = emit_fn

    async def emit(self, msg: dict) -> None:
        if self._emit is not None:
            await self._emit(msg)

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
            print(f"[ipc-router] handler {mtype} failed: {e!r}", file=sys.stderr)
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
        try:
            async for msg in ws:
                try:
                    data = json.loads(msg) if isinstance(msg, str) else {}
                except Exception:
                    data = {}
                if data.get("action") == "trigger":
                    print("\n[ws] manual trigger requested")
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
                            print(f"[ws] suggestion choose failed: {e}", file=sys.stderr)
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
                            print(f"[ws] suggestion feedback failed: {e}", file=sys.stderr)
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
    print(f"-> mascot bus on ws://{WS_HOST}:{WS_PORT} (send {{action: trigger}} for manual fire)")

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
            # without breaking existing subscribers. `active_genre`
            # ("house"/"techno"/"hard_tek"/"unknown") feeds the
            # GenreRouter on the renderer side. Anti-hallucination is
            # the renderer's job (the bus is a dumb wire) — under low
            # bpm_confidence the bus still emits beat_phase as-is and
            # the renderer (Plan 13-04 Open Q 4) ignores beat-locked
            # behavior.
            # Phase 31 — 4-layer mascot extension (ADDITIVE per Pitfall
            # P47). `emotion` ("neutral"/"focused"/"hyped"/"concerned"/
            # None) drives the priority-60 EmotionLayer on the frontend.
            # `reaction_intent` (MascotReaction whitelist value / None)
            # is set by the AICoach emote-tag parser and consumed by
            # the priority-80 ReactionLayer. Both fields default None
            # which the renderer interprets as "no-op" — backward
            # compatible with v2.0 subscribers that don't read them.
            # Build the mascot frame as a dict FIRST so we can gate the send
            # at the emit boundary (BRINGUP-04). The key set / ordering / 30Hz
            # cadence are unchanged — the guard below only decides whether to
            # PUT this tick on the wire, it never reshapes a valid frame.
            mascot_frame = {
                **levels.snapshot(),
                "audible": state.audible,
                "deck": state.audible_deck,
                "phase": state.phase,
                "bpm": state.bpm,
                "mood": state.mood,
                "bpm_confidence": state.bpm_confidence,
                "downbeat_phase": state.downbeat_phase,
                "beat_phase": state.beat_phase,
                "active_genre": state.active_genre,
                # Phase 52 (GENRE-02) — additive. `detected_genre` is the FULL-
                # LIBRARY auto-detected genre name (Plan 52-03), distinct from
                # the coarse `active_genre` house/techno/hard_tek renderer
                # signal above. Anti-hallucination is honored at the SOURCE: the
                # detector writes "unknown" when it is unsure, so the bus is a
                # dumb wire that carries the value as-is — never a fabricated
                # label. `genre_confidence` is the detector's score in [0,1].
                "detected_genre": state.detected_genre,
                "genre_confidence": state.genre_confidence,
                "emotion": state.emotion,
                "reaction_intent": state.last_reaction_intent,
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
                    print(f"[ws] suggestion read failed: {e}", file=sys.stderr)
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
                print(
                    "[ws] skipped malformed mascot frame "
                    f"(missing meter keys; got {sorted(mascot_frame)})",
                    file=sys.stderr,
                )
                await asyncio.sleep(1 / 30)
                continue
            payload = json.dumps(mascot_frame)
            dead = []
            for c in clients:
                try:
                    await c.send(payload)
                except Exception:
                    dead.append(c)
            for c in dead:
                clients.discard(c)

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
                    )
                    _validate_snapshot(snap_msg)
                    snap_payload = json.dumps(snap_msg, separators=(",", ":"))
                    snap_dead = []
                    for c in clients:
                        try:
                            await c.send(snap_payload)
                        except Exception:
                            snap_dead.append(c)
                    for c in snap_dead:
                        clients.discard(c)
                except Exception as e:
                    print(f"[ws snapshot] emit failed: {e}", file=sys.stderr)

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
                        midi=_probe_midi_count(controller_state),
                        screen=_probe_screen_status(screen_available),
                    )
                    status_payload = status_msg.to_json()
                    status_dead = []
                    for c in clients:
                        try:
                            await c.send(status_payload)
                        except Exception:
                            status_dead.append(c)
                    for c in status_dead:
                        clients.discard(c)
                except Exception as e:
                    print(f"[ws status] emit failed: {e}", file=sys.stderr)

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
        print(f"-> wizard bus on ws://{WS_HOST}:{WS_PORT} (handlers: {len(self._handlers)})")

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
        for c in self._clients:
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
                    print(f"[wizard bus] non-JSON frame: {e}", file=sys.stderr)
                    continue
                if not isinstance(msg, dict):
                    print(
                        f"[wizard bus] top-level not object: {type(msg).__name__}",
                        file=sys.stderr,
                    )
                    continue
                try:
                    validate_message(msg)
                except _jsonschema.ValidationError as e:
                    print(f"[wizard bus] schema violation: {e.message}", file=sys.stderr)
                    continue
                msg_type = msg.get("type", "")
                handler = self._handlers.get(msg_type)
                if handler is None:
                    print(
                        f"[wizard bus] no handler for {msg_type}",
                        file=sys.stderr,
                    )
                    continue
                try:
                    await handler(msg)
                except Exception as e:
                    # Handler-internal failure must not close the WS.
                    print(
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
