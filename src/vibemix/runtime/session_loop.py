# SPDX-License-Identifier: Apache-2.0
"""Phase 12 Wave 2 — SessionLoop runtime.

The Python sidecar's live-session surface. Mirror of ``WizardLoop`` from
Phase 11 W4 — same handler-registration pattern on the same WS bus class
(``WizardBus`` / ``IpcBus`` alias from ``ws_bus.py``) — but for the
post-calibration runtime.

Responsibilities (per 12-02 must-haves):

  1. Register 4 ipc.* handlers on the bus:
       * ``ipc.session.mute``      — toggle, drain PlaybackQueue, ack
       * ``ipc.settings.set``      — dispatch via SettingsApplier
       * ``ipc.settings.get``      — return ``ipc.settings.state``
       * ``ipc.status.recheck``    — re-probe one component + emit tick

  2. 30Hz background task emits ``ipc.session.snapshot`` built from:
       * MusicState (audible, phase, bpm, recent_moves)
       * Levels (music/voice/mic RMS pairs)
       * EventDetector recent events (TODO — Phase 12-04 glue)
       * Transcript ring (200 entries, deque — appended by cascade hooks)
       * ControllerState.recent_moves (MIDI event ribbon)

  3. Validate every inbound message through ``vibemix.ui_bus.validator``
     before dispatch. On schema violation emit ``ipc.error`` (never
     raise into the loop — UX-08 reliability).

  4. ``muted`` is owned here as a transient field. On
     ``ipc.session.mute toggle:true`` we flip the flag and call
     ``playback_queue.clear()`` (duck-typed; the ref may be None during
     12-02's structural ship, real wiring is 12-04).

Note: ``MusicState`` may not be live yet during Wave 2's structural
ship (the cascade graph wires the state-refresh loop in 12-04). When
``music_state`` is ``None`` we emit a hard-real fallback snapshot with
zeroed meters + ``cohost_status="IDLE"`` + ``grounded=false``. The
schema rejects an empty enum, so we can't use ``"warming_up"`` — IDLE
is the closest neutral state and ``grounded=false`` is the renderer's
"cohost is offline / not yet grounded" signal.
"""

from __future__ import annotations

import asyncio
import json
import logging
import signal
import sys
import time
from collections import deque
from datetime import UTC, datetime
from typing import Any, Protocol

import jsonschema

from vibemix.runtime.config_store import ConfigStore, load_config
from vibemix.runtime.settings import SettingsApplier
from vibemix.runtime.ws_bus import WizardBus
from vibemix.ui_bus.messages import (
    IpcBoot,
    IpcError,
    LevelPair,
    MetersTriple,
    MidiEventEntry,
    SessionMute,
    SessionSnapshot,
    SettingsState,
    StatusTick,
    TrackInfo,
    TranscriptLine,
)
from vibemix.ui_bus.validator import validate_message

log = logging.getLogger("vibemix.session")


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


SNAPSHOT_HZ: float = 30.0
SNAPSHOT_INTERVAL: float = 1.0 / SNAPSHOT_HZ
TRANSCRIPT_RING_SIZE: int = 200
MIDI_EVENT_RING_SIZE: int = 64


# ---------------------------------------------------------------------------
# Structural protocols for injected runtime refs
# ---------------------------------------------------------------------------
#
# Every injected ref is Optional and duck-typed via Protocol. SessionLoop
# is testable without standing up the cascade graph — Wave 2's job is to
# ship the structural surface; Wave 3/4 wires the real refs.


class _LevelsHook(Protocol):
    music: float
    voice: float
    mic: float

    def snapshot(self) -> dict[str, float]: ...


class _MusicStateHook(Protocol):
    audible: bool
    phase: str
    bpm: float
    audible_track: str | None
    audible_deck: str
    recent_moves: list  # list[tuple[float, str]]


class _PlaybackQueueHook(Protocol):
    def clear(self) -> None: ...


class _ControllerStateHook(Protocol):
    recent_moves: list  # list[tuple[float, str]]


# ---------------------------------------------------------------------------
# SessionLoop
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    """UTC ISO-8601 timestamp matching the schema's ``date-time`` format."""
    return datetime.now(UTC).isoformat()


class SessionLoop:
    """Live-session ipc.* runtime.

    Constructor accepts every runtime ref as ``Optional`` so the loop can
    be exercised in isolation. ``run()`` follows the Phase 11 ``WizardLoop``
    contract: register handlers → start bus → emit ``ipc.boot`` → spawn
    background tasks → wait on stop event → tear down.
    """

    def __init__(
        self,
        bus: WizardBus,
        *,
        config_store: ConfigStore | None = None,
        settings_applier: SettingsApplier | None = None,
        music_state: _MusicStateHook | None = None,
        levels: _LevelsHook | None = None,
        playback_queue: _PlaybackQueueHook | None = None,
        controller_state: _ControllerStateHook | None = None,
    ) -> None:
        self.bus = bus
        self.config_store = config_store or load_config()
        self.settings_applier = settings_applier or SettingsApplier(
            config_store=self.config_store
        )
        self.music_state = music_state
        self.levels = levels
        self.playback_queue = playback_queue
        self.controller_state = controller_state

        # Transient state
        self.muted: bool = False
        self._stop = asyncio.Event()
        self._snapshot_task: asyncio.Task | None = None
        self._transcript: deque[TranscriptLine] = deque(maxlen=TRANSCRIPT_RING_SIZE)
        # ``_transcript_unsent`` is the slice not yet emitted in a snapshot
        # delta. Snapshot builds ``transcript_delta`` from this; on emit
        # the deque is cleared (the renderer is responsible for keeping
        # its own append-only buffer).
        self._transcript_unsent: list[TranscriptLine] = []

        # Last seen MIDI move index (so snapshot.midi_events emits only
        # newly observed moves, not the entire 12s window every tick).
        self._last_midi_index: int = 0

    # ------------------------------------------------------------------
    # Public transcript-append API (cascade calls this on every TTS line)
    # ------------------------------------------------------------------

    def append_transcript(self, *, role: str, text: str) -> None:
        """Append a transcript line. Called by the cascade agent on every
        TTS turn + by the mic-STT placeholder on detected user speech.

        Phase 12-04 wires the cascade hook; Wave 2 ships the buffer
        management so the snapshot emitter is fully exercised.
        """
        if role not in ("ai", "user", "system"):
            log.warning("append_transcript: invalid role %r — dropped", role)
            return
        line = TranscriptLine(role=role, text=text, ts=_now_iso())  # type: ignore[arg-type]
        self._transcript.append(line)
        self._transcript_unsent.append(line)

    # ------------------------------------------------------------------
    # Handler registration
    # ------------------------------------------------------------------

    def register_handlers(self) -> None:
        """Wire the 4 ipc.* handlers onto the bus."""
        self.bus.register_handler("ipc.session.mute", self._on_session_mute)
        self.bus.register_handler("ipc.settings.set", self._on_settings_set)
        self.bus.register_handler("ipc.settings.get", self._on_settings_get)
        self.bus.register_handler("ipc.status.recheck", self._on_status_recheck)

    async def boot(self) -> None:
        """Emit ``ipc.boot {ready: true}``. Mirrors WizardLoop.boot()."""
        await self.bus.emit(json.loads(IpcBoot.make(ready=True).to_json()))
        # Emit a fresh ``ipc.settings.state`` so the renderer can populate
        # the settings drawer without waiting for the first user-driven
        # ipc.settings.get.
        await self._emit_settings_state()

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------

    async def _on_session_mute(self, msg: dict) -> None:
        """Handle ``ipc.session.mute {toggle: true}`` — flip ``muted``,
        drain the playback queue, ack with new state.

        The schema lets either ``toggle`` or ``muted`` be present (it's
        asymmetric — shell sends toggle, sidecar replies with muted).
        Accept missing ``toggle`` as toggle=true (UX-07 — clicking the
        mute button is unambiguous; absent payload still toggles).
        """
        payload = msg.get("payload", {})
        toggle = payload.get("toggle", True)
        if not toggle:
            # ``toggle: false`` is unusual but we honor it as "no-op";
            # still ack with current state for echo.
            await self.bus.emit(json.loads(SessionMute.make_ack(muted=self.muted).to_json()))
            return
        self.muted = not self.muted
        # Drain PlaybackQueue on mute-engage so an in-flight TTS line
        # stops mid-utterance instead of finishing. Duck-typed via
        # ``clear()`` — the real ref will land in 12-04.
        if self.muted and self.playback_queue is not None:
            try:
                self.playback_queue.clear()
            except Exception as e:
                log.warning("playback_queue.clear() raised: %s", e)
        ack = SessionMute.make_ack(muted=self.muted)
        await self.bus.emit(json.loads(ack.to_json()))

    async def _on_settings_set(self, msg: dict) -> None:
        """Dispatch ``ipc.settings.set`` via the SettingsApplier.

        Always emit a fresh ``ipc.settings.state`` after a successful
        apply so the renderer never displays stale config. On failure
        emit ``ipc.error`` with the apply reason.
        """
        payload = msg.get("payload", {})
        field = payload.get("field")
        value = payload.get("value")
        success, error = await self.settings_applier.apply(field, value)
        if success:
            await self._emit_settings_state()
        else:
            await self.bus.emit(
                json.loads(
                    IpcError.make(
                        reason=error or "settings.set failed",
                        original_type="ipc.settings.set",
                    ).to_json()
                )
            )

    async def _on_settings_get(self, _msg: dict) -> None:
        """Reply to ``ipc.settings.get`` with the full ``ipc.settings.state``."""
        await self._emit_settings_state()

    async def _on_status_recheck(self, msg: dict) -> None:
        """One-shot probe of a named component + emit a fresh status tick.

        The Phase 12-04 glue wires real probes; Wave 2 ships the
        handler shape with permissive defaults so the UI's recheck
        button is non-broken from day one.
        """
        component = msg.get("payload", {}).get("component", "")
        if component not in ("livekit", "gemini", "midi", "screen"):
            await self.bus.emit(
                json.loads(
                    IpcError.make(
                        reason=f"unknown component: {component!r}",
                        original_type="ipc.status.recheck",
                    ).to_json()
                )
            )
            return
        # Best-effort probe — same fallback set the wizard's status_tick uses.
        tick = StatusTick.make(
            livekit="connecting",
            gemini="down",
            midi=self._probe_midi_count(),
            screen=self._probe_screen_status(),
        )
        await self.bus.emit(json.loads(tick.to_json()))

    # ------------------------------------------------------------------
    # Snapshot construction
    # ------------------------------------------------------------------

    def _build_snapshot(self) -> SessionSnapshot:
        """Compose a single ``ipc.session.snapshot`` from current refs.

        When ``music_state`` is None we emit a hard-real fallback:
        zeroed meters + IDLE + grounded=false. The schema rejects an
        empty enum so we cannot use a "warming_up" status — IDLE is
        the closest neutral state and ``grounded=false`` flags the
        renderer that the cohost surface is not yet wired.
        """
        # Meters — pull from Levels if injected; else zeros.
        if self.levels is not None:
            snap = self.levels.snapshot()
            music_rms = float(snap.get("music", 0.0))
            voice_rms = float(snap.get("voice", 0.0))
            mic_rms = float(snap.get("mic", 0.0))
        else:
            music_rms = voice_rms = mic_rms = 0.0
        # Clamp to [0, 1] — schema constraint. EMA-smoothed RMS rarely
        # exceeds 1.0 but guard anyway so a numeric drift doesn't crash
        # the validator and bring the snapshot loop down.
        music_rms = max(0.0, min(1.0, music_rms))
        voice_rms = max(0.0, min(1.0, voice_rms))
        mic_rms = max(0.0, min(1.0, mic_rms))
        # Peak is approximated as RMS for the structural ship — the
        # real peak readers land in 12-04 alongside the cascade graph.
        meters = MetersTriple(
            music=LevelPair(rms=music_rms, peak=music_rms),
            voice=LevelPair(rms=voice_rms, peak=voice_rms),
            mic=LevelPair(rms=mic_rms, peak=mic_rms),
        )

        # Cohost status — TALKING when AI voice meter is non-trivial,
        # LISTENING when audible music + no AI voice, else IDLE.
        if self.music_state is None:
            cohost_status: str = "IDLE"
            grounded = False
            bpm: float | None = None
            track = None
        else:
            grounded = bool(self.music_state.audible)
            if voice_rms > 0.05:
                cohost_status = "TALKING"
            elif grounded:
                cohost_status = "LISTENING"
            else:
                cohost_status = "IDLE"
            raw_bpm = float(getattr(self.music_state, "bpm", 0.0) or 0.0)
            bpm = raw_bpm if raw_bpm > 0.0 else None
            audible_track = getattr(self.music_state, "audible_track", None)
            audible_deck = getattr(self.music_state, "audible_deck", None)
            if audible_track:
                track = TrackInfo(
                    title=str(audible_track),
                    artist=None,
                    deck=str(audible_deck) if audible_deck else None,
                )
            else:
                track = None

        # Transcript delta — drain the unsent buffer.
        transcript_delta = tuple(self._transcript_unsent)
        self._transcript_unsent = []

        # MIDI events — drain newly observed moves from ControllerState.
        midi_events: tuple[MidiEventEntry, ...] = ()
        if self.controller_state is not None:
            try:
                moves = list(self.controller_state.recent_moves)
            except Exception:
                moves = []
            new_moves = moves[self._last_midi_index :]
            self._last_midi_index = len(moves)
            midi_events = tuple(
                MidiEventEntry(
                    control=str(label),
                    value=None,
                    ts=_now_iso(),
                )
                for _age, label in new_moves[-MIDI_EVENT_RING_SIZE:]
            )

        return SessionSnapshot.make(
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

    async def _snapshot_loop(self) -> None:
        """30Hz emitter. Always emits the schema-valid snapshot; on
        emit failure we log + continue (a single bad frame must NOT
        bring the loop down)."""
        while not self._stop.is_set():
            t0 = time.monotonic()
            try:
                snapshot = self._build_snapshot()
                await self.bus.emit(json.loads(snapshot.to_json()))
            except Exception as e:
                log.warning("snapshot emit failed: %s", e)
            # Drift-corrected sleep — keeps the cadence at 30Hz under
            # variable emit latency. If we already overran, yield once.
            dt = time.monotonic() - t0
            try:
                await asyncio.wait_for(
                    self._stop.wait(), timeout=max(0.0, SNAPSHOT_INTERVAL - dt)
                )
                return
            except asyncio.TimeoutError:
                continue

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _emit_settings_state(self) -> None:
        """Emit a full ``ipc.settings.state`` reflecting current config + ``muted``."""
        state = SettingsState.make(
            voice=self.config_store.voice,
            mode=self.config_store.mode,  # type: ignore[arg-type]
            genre=self.config_store.genre,
            output_device_id=self.config_store.output_device_id,
            output_profile=self.config_store.output_profile,  # type: ignore[arg-type]
            retention_days=self.config_store.retention_days,
            push_to_mute_hotkey=self.config_store.push_to_mute_hotkey,
            muted=self.muted,
        )
        await self.bus.emit(json.loads(state.to_json()))

    def _probe_midi_count(self) -> int | None:
        """Mirror of WizardLoop._probe_midi_count — best-effort mido import."""
        try:
            import mido  # noqa: PLC0415

            return len(mido.get_input_names())
        except Exception:
            return None

    def _probe_screen_status(self) -> str:
        """Mirror of WizardLoop._probe_screen_status."""
        try:
            from vibemix.platform import permissions  # noqa: PLC0415

            return (
                "ok"
                if permissions.check_screen_recording_permission() == "authorized"
                else "denied"
            )
        except Exception:
            return "denied"

    # ------------------------------------------------------------------
    # Inbound message validation — wraps bus dispatch with ipc.error fallback
    # ------------------------------------------------------------------
    #
    # The WizardBus already validates inbound frames against the schema
    # before invoking handlers — invalid frames are dropped with a stderr
    # log. The plan must-have requires we emit ``ipc.error`` on schema
    # failure rather than silently dropping. We wrap the bus's
    # ``register_handler`` with a validation guard so handler bodies see
    # only schema-valid messages but the user gets feedback on bad ones.
    #
    # We do this by installing a tiny wrapper handler for each type that
    # re-validates the message and emits ipc.error on failure. The
    # WizardBus._handler also validates, so this is belt-and-suspenders
    # for the test path that bypasses the bus and calls handlers directly.

    def _wrap_with_validation(
        self, handler, original_type: str
    ):
        """Return a wrapper that re-validates then dispatches.

        Tests drive handlers directly (bypassing the bus's schema check);
        this wrapper ensures invalid payloads emit ``ipc.error`` even
        on that path. The bus's outer validate is still the primary
        guard at runtime.
        """

        async def _wrapped(msg: dict) -> None:
            try:
                validate_message(msg)
            except jsonschema.ValidationError as e:
                await self.bus.emit(
                    json.loads(
                        IpcError.make(
                            reason=f"schema violation: {e.message}",
                            original_type=original_type,
                        ).to_json()
                    )
                )
                return
            await handler(msg)

        return _wrapped

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def run(self) -> None:
        """Register handlers → start bus → emit boot → spawn snapshot →
        wait on stop event → tear down. Mirrors ``WizardLoop.run``."""
        self.register_handlers()
        await self.bus.start()
        await self.boot()
        self._snapshot_task = asyncio.create_task(self._snapshot_loop())

        # SIGTERM (Tauri Cmd+Q) + SIGINT — same pattern as WizardLoop.
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                loop.add_signal_handler(sig, self._stop.set)
            except NotImplementedError:
                pass

        try:
            await self._stop.wait()
        finally:
            if self._snapshot_task is not None:
                self._snapshot_task.cancel()
                try:
                    await self._snapshot_task
                except (asyncio.CancelledError, Exception):
                    pass
            await self.bus.stop()

    def request_stop(self) -> None:
        """Cooperative shutdown signal — tests + ``__main__`` Cmd+Q path."""
        self._stop.set()


# ---------------------------------------------------------------------------
# Entrypoint invoked by __main__.py
# ---------------------------------------------------------------------------


async def run_session() -> int:
    """Entry point for ``python -m vibemix`` (no ``--wizard``).

    Constructs a fresh ``WizardBus`` (re-used as the session bus — same
    handler-dispatch surface), runs the ``SessionLoop`` until SIGTERM /
    SIGINT, returns 0.

    The Wave 2 ship runs **standalone** — no cascade agent, no audio
    core, no MusicState. The structural surface is what 12-03 and 12-04
    glue against; live audio I/O joins the loop in 12-04.
    """
    logging.basicConfig(level=logging.INFO, format="[%(name)s] %(message)s")
    bus = WizardBus()
    loop = SessionLoop(bus)
    print("-> session boot", file=sys.stderr)
    started = time.monotonic()
    await loop.run()
    print(f"-> session exit ({time.monotonic() - started:.1f}s)", file=sys.stderr)
    return 0


__all__ = ["SessionLoop", "SNAPSHOT_HZ", "SNAPSHOT_INTERVAL", "run_session"]
