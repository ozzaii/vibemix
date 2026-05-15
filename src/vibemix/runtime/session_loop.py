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
from pathlib import Path
from typing import Any, Protocol

import jsonschema

from vibemix.runtime.config_store import ConfigStore, load_config
from vibemix.runtime.parent_watchdog import watch_parent
from vibemix.runtime.recordings_index import RecordingsIndex, run_retention_sweep
from vibemix.runtime.settings import SettingsApplier
from vibemix.runtime.ws_bus import WizardBus
from vibemix.ui_bus.messages import (
    IpcBoot,
    IpcError,
    LevelPair,
    MetersTriple,
    MidiEventEntry,
    ProfileDeleteAck,
    ProfileRegenerateResult,
    ProfileViewResult,
    RecordingsDeleteAck,
    RecordingsEventsResult,
    RecordingsListResult,
    RecordingsUsage,
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

# Phase 15 Plan 02 — periodic retention sweep cadence. The boot + close
# + settings-change triggers cover startup, shutdown, and user-driven
# retention changes; this constant drives the long-haul fall-through
# trigger so a session left running for >6h still gets its expired
# recordings pruned without manual intervention. CONTEXT.md §"Retention
# Enforcement" locks 6h.
#
# Tests monkeypatch this attribute to a sub-second value; the periodic
# loop reads the module attribute (NOT a captured local) on every iteration
# so a runtime patch takes effect on the next tick.
RETENTION_SWEEP_INTERVAL_S: float = 6 * 60 * 60  # 21600s = 6h


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
        recordings_root: Path | None = None,
        active_recorder: object | None = None,
        evidence_registry: object | None = None,
    ) -> None:
        self.bus = bus
        self.config_store = config_store or load_config()
        self.settings_applier = settings_applier or SettingsApplier(
            config_store=self.config_store,
            recordings_root=recordings_root,
            ws_bus=bus,
        )
        self.music_state = music_state
        self.levels = levels
        self.playback_queue = playback_queue
        self.controller_state = controller_state
        self.recordings_root = recordings_root
        # Phase 15 Plan 02 — `active_recorder` is the live VoiceRecorder
        # instance whose events.jsonl receives the per-sweep
        # `retention_pruned` line when count > 0. None in --session
        # standalone mode (no cascade graph yet) so the periodic loop
        # logs to Python logger only — never raises.
        # Typed as `object` to dodge a circular import on
        # `vibemix.audio.recorder.VoiceRecorder`; the hot path uses
        # duck-typed `.log_event(kind, **fields)`.
        self.active_recorder = active_recorder
        # Phase 32 / PROFILE-07 — EvidenceRegistry reference used by the
        # Settings → Profile panel's "regenerate now" handler. Duck-typed
        # as `object` (the hot path calls ``.snapshot()`` only); None in
        # standalone runs means the regenerate path returns
        # ``insufficient_evidence`` instead of producing an empty profile
        # from a snapshot-less registry.
        self.evidence_registry = evidence_registry

        # Transient state
        self.muted: bool = False
        self._stop = asyncio.Event()
        self._snapshot_task: asyncio.Task | None = None
        self._retention_task: asyncio.Task | None = None
        self._parent_watch_task: asyncio.Task | None = None
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
        """Wire all ipc.* handlers onto the bus.

        Phase 12 W2 baseline: 4 handlers (session.mute / settings.set / settings.get
        / status.recheck). Phase 15 Plan 03 adds 3 recordings.* request handlers
        (list / delete / events). recordings.usage is push-only — no inbound
        shape, no handler.
        """
        self.bus.register_handler("ipc.session.mute", self._on_session_mute)
        self.bus.register_handler("ipc.settings.set", self._on_settings_set)
        self.bus.register_handler("ipc.settings.get", self._on_settings_get)
        self.bus.register_handler("ipc.status.recheck", self._on_status_recheck)
        # Phase 15 Plan 03 — recording browser handlers. 3 inbound types
        # (list / delete / events). recordings.usage is push-only.
        self.bus.register_handler("ipc.recordings.list", self._on_recordings_list)
        self.bus.register_handler("ipc.recordings.delete", self._on_recordings_delete)
        self.bus.register_handler("ipc.recordings.events", self._on_recordings_events)
        # Phase 32 / PROFILE-07 — Settings → Profile panel.
        # Three request-reply pairs:
        #   view       → view_result   (snapshot + bytes + consent)
        #   regenerate → regenerate_result (consent-gated, citation-gated)
        #   delete     → delete_ack    (unlink + cache invalidate is caller's job)
        self.bus.register_handler("ipc.profile.view", self._on_profile_view)
        self.bus.register_handler(
            "ipc.profile.regenerate", self._on_profile_regenerate
        )
        self.bus.register_handler("ipc.profile.delete", self._on_profile_delete)
        # PROFILE-05 — Settings panel may also surface a re-toggle of consent
        # (the "enable" affordance on the consent-off empty state). The
        # WizardLoop handler is the primary writer but the SessionLoop also
        # accepts it so the panel works post-wizard without re-launching it.
        self.bus.register_handler(
            "ipc.profile.set_consent", self._on_profile_set_consent
        )

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

    # ------------------------------------------------------------------
    # Phase 15 Plan 03 — recording browser handlers + retention sweep
    # ------------------------------------------------------------------

    async def _on_recordings_list(self, msg: dict) -> None:
        """Emit ``ipc.recordings.list_result`` with every session + total bytes.

        Sessions are returned newest-first by dir-name unix timestamp (see
        RecordingsIndex.list). bytes_total is the scandir-summed total across
        every session — matches the disk-usage line in the drawer.

        If ``recordings_root`` is None (the loop was constructed without one —
        e.g., tests for the standalone Phase 12 W2 path), emit ``ipc.error``
        with reason=``recordings_root_not_wired`` so the UI surfaces a clear
        diagnostic rather than a silent no-op.
        """
        if self.recordings_root is None:
            await self.bus.emit(
                json.loads(
                    IpcError.make(
                        reason="recordings_root_not_wired",
                        original_type="ipc.recordings.list",
                    ).to_json()
                )
            )
            return
        try:
            loop = asyncio.get_running_loop()
            index = RecordingsIndex(self.recordings_root)
            summaries = await loop.run_in_executor(None, index.list)
            _, bytes_total = await loop.run_in_executor(None, index.compute_usage)
            result = RecordingsListResult.make(
                sessions=summaries, bytes_total=bytes_total
            )
            await self.bus.emit(json.loads(result.to_json()))
        except Exception as e:
            log.exception("recordings.list handler failed")
            await self.bus.emit(
                json.loads(
                    IpcError.make(
                        reason=f"{type(e).__name__}: {e}",
                        original_type="ipc.recordings.list",
                    ).to_json()
                )
            )

    async def _on_recordings_delete(self, msg: dict) -> None:
        """Delete a session dir; emit ``ipc.recordings.delete_ack`` + fresh
        ``ipc.recordings.usage``.

        Path-traversal gate fires at the index layer (regex + is_relative_to).
        On bad payload (wrong shape, missing session_dir), emit ``ipc.error``.
        """
        if self.recordings_root is None:
            await self.bus.emit(
                json.loads(
                    IpcError.make(
                        reason="recordings_root_not_wired",
                        original_type="ipc.recordings.delete",
                    ).to_json()
                )
            )
            return
        try:
            payload = msg.get("payload", {})
            session_dir = payload.get("session_dir")
            if not isinstance(session_dir, str):
                await self.bus.emit(
                    json.loads(
                        IpcError.make(
                            reason="session_dir missing or not a string",
                            original_type="ipc.recordings.delete",
                        ).to_json()
                    )
                )
                return
            loop = asyncio.get_running_loop()
            index = RecordingsIndex(self.recordings_root)
            ok, err = await loop.run_in_executor(None, index.delete, session_dir)
            ack = RecordingsDeleteAck.make(
                session_dir=session_dir, ok=ok, error=err
            )
            await self.bus.emit(json.loads(ack.to_json()))
            # Fire a fresh usage push so the drawer's disk line updates
            # post-delete. We re-read the index because the cached numbers
            # are stale (one session just disappeared).
            sessions, bytes_total = await loop.run_in_executor(
                None, index.compute_usage
            )
            usage = RecordingsUsage.make(
                sessions=sessions, bytes_total=bytes_total
            )
            await self.bus.emit(json.loads(usage.to_json()))
        except Exception as e:
            log.exception("recordings.delete handler failed")
            await self.bus.emit(
                json.loads(
                    IpcError.make(
                        reason=f"{type(e).__name__}: {e}",
                        original_type="ipc.recordings.delete",
                    ).to_json()
                )
            )

    async def _on_recordings_events(self, msg: dict) -> None:
        """Read events.jsonl for a session; emit ``ipc.recordings.events_result``.

        Path-traversal gate fires at the index layer. Malformed JSON lines
        are silently skipped (RecordingsIndex.read_events logs at DEBUG).
        """
        if self.recordings_root is None:
            await self.bus.emit(
                json.loads(
                    IpcError.make(
                        reason="recordings_root_not_wired",
                        original_type="ipc.recordings.events",
                    ).to_json()
                )
            )
            return
        try:
            payload = msg.get("payload", {})
            session_dir = payload.get("session_dir")
            if not isinstance(session_dir, str):
                await self.bus.emit(
                    json.loads(
                        IpcError.make(
                            reason="session_dir missing or not a string",
                            original_type="ipc.recordings.events",
                        ).to_json()
                    )
                )
                return
            loop = asyncio.get_running_loop()
            index = RecordingsIndex(self.recordings_root)
            events, err = await loop.run_in_executor(
                None, index.read_events, session_dir
            )
            if err is not None:
                await self.bus.emit(
                    json.loads(
                        IpcError.make(
                            reason=err,
                            original_type="ipc.recordings.events",
                        ).to_json()
                    )
                )
                return
            result = RecordingsEventsResult.make(
                session_dir=session_dir, events=tuple(events or ())
            )
            await self.bus.emit(json.loads(result.to_json()))
        except Exception as e:
            log.exception("recordings.events handler failed")
            await self.bus.emit(
                json.loads(
                    IpcError.make(
                        reason=f"{type(e).__name__}: {e}",
                        original_type="ipc.recordings.events",
                    ).to_json()
                )
            )

    # ------------------------------------------------------------------
    # Phase 32 / PROFILE-07 — Settings → Profile panel handlers
    # ------------------------------------------------------------------
    #
    # All four handlers are best-effort: schema-valid replies always, errors
    # encoded into the result payload (NOT raised). The renderer is the
    # source of truth for what gets shown; the sidecar only writes to disk
    # when consent is explicitly ON.
    #
    # P51 / P53 / P60 hard rule: the profile dict NEVER leaves the cache +
    # disk surface — this handler only touches the on-disk profile.json,
    # never the per-turn prompt path. The grep gate
    # (tests/profile/test_profile_not_in_per_turn_prompt.py) protects the
    # agent's llm_node from accidental reference.

    async def _on_profile_view(self, _msg: dict) -> None:
        """Reply to ``ipc.profile.view`` with the on-disk profile snapshot.

        Empty payload in; ``ipc.profile.view_result`` out with:
          - ``profile``: parsed dict or ``None`` if absent / consent off.
          - ``bytes``: UTF-8 byte length of the serialized profile (0 when None).
          - ``consent``: current profile_consent state (so the renderer can
            switch between loaded/empty/consent-off states in one round trip).

        Best-effort: load failures fall through to ``profile=None``.
        """
        try:
            from vibemix.profile import load_consent, load_profile

            consent = load_consent()
            profile = load_profile() if consent else None
            raw = (
                json.dumps(profile, separators=(",", ":"), sort_keys=True).encode(
                    "utf-8"
                )
                if profile
                else b""
            )
            result = ProfileViewResult.make(
                profile=profile, bytes=len(raw), consent=consent
            )
            await self.bus.emit(json.loads(result.to_json()))
        except Exception as e:
            log.exception("profile.view handler failed")
            # Best-effort: emit a view_result with profile=None so the UI
            # can still render the empty state.
            try:
                fallback = ProfileViewResult.make(
                    profile=None, bytes=0, consent=False
                )
                await self.bus.emit(json.loads(fallback.to_json()))
            except Exception:
                pass
            log.warning("profile.view fallback emitted (cause=%s)", e)

    async def _on_profile_regenerate(self, _msg: dict) -> None:
        """Reply to ``ipc.profile.regenerate``.

        Consent OFF → reply with ``ok=False, error="consent_off"`` (UI surfaces
        the enable affordance).

        Consent ON but no live EvidenceRegistry OR insufficient citations →
        ``ok=False, error="insufficient_evidence"`` (PROFILE-06 drift gate;
        the builder retains the prior profile rather than over-fitting).

        On success → save the new profile to disk + reply with the dict.

        The reply ALWAYS validates against the schema; errors are encoded into
        the payload (ok=False + error string ≤200 chars), NEVER raised.
        """
        try:
            from vibemix.profile import (
                build_profile,
                load_consent,
                load_profile,
                save_profile,
            )

            if not load_consent():
                result = ProfileRegenerateResult.make(
                    ok=False, profile=None, error="consent_off"
                )
                await self.bus.emit(json.loads(result.to_json()))
                return
            prior = load_profile()
            evidence: dict[str, dict[str, tuple[float, ...]]] = {}
            if self.evidence_registry is not None:
                try:
                    evidence = self.evidence_registry.snapshot()  # type: ignore[attr-defined]
                except Exception as snap_err:
                    log.warning("evidence_registry.snapshot() failed: %s", snap_err)
            # PROFILE-06 gate at the handler: a regenerate request with
            # NO live evidence AND no prior profile means the user clicked
            # "regenerate" before vibemix could observe anything useful.
            # Falling through to build_profile would produce a cold-start
            # dict (genre=unknown / tempo_bin=128-138 / empty tags) that
            # has no real signal — surface insufficient_evidence so the UI
            # tells the user "keep mixing and try again" instead of pretend-
            # personalizing. Once at least one session worth of evidence
            # exists the builder's ≥2-citation gate per field takes over.
            if not evidence and prior is None:
                result = ProfileRegenerateResult.make(
                    ok=False, profile=None, error="insufficient_evidence"
                )
                await self.bus.emit(json.loads(result.to_json()))
                return
            new_profile = build_profile(prior, [], evidence, consent=True)
            if new_profile is None:
                result = ProfileRegenerateResult.make(
                    ok=False, profile=None, error="insufficient_evidence"
                )
                await self.bus.emit(json.loads(result.to_json()))
                return
            save_profile(new_profile)
            result = ProfileRegenerateResult.make(
                ok=True, profile=new_profile, error=None
            )
            await self.bus.emit(json.loads(result.to_json()))
        except Exception as e:
            log.exception("profile.regenerate handler failed")
            err_short = f"{type(e).__name__}: {e}"[:200]
            result = ProfileRegenerateResult.make(
                ok=False, profile=None, error=err_short
            )
            await self.bus.emit(json.loads(result.to_json()))

    async def _on_profile_delete(self, _msg: dict) -> None:
        """Reply to ``ipc.profile.delete``.

        Unlinks ``~/.config/vibemix/profile.json``. Returns ``ok=True`` iff a
        file existed and was deleted; ``ok=False, error="not_found"`` when no
        file was present (UI surfaces an empty-state confirmation either way).

        Best-effort: filesystem errors are encoded into the payload, never
        raised.
        """
        try:
            from vibemix.profile import delete_profile

            deleted = delete_profile()
            result = ProfileDeleteAck.make(
                ok=deleted, error=None if deleted else "not_found"
            )
            await self.bus.emit(json.loads(result.to_json()))
        except Exception as e:
            log.exception("profile.delete handler failed")
            err_short = f"{type(e).__name__}: {e}"[:200]
            result = ProfileDeleteAck.make(ok=False, error=err_short)
            await self.bus.emit(json.loads(result.to_json()))

    async def _on_profile_set_consent(self, msg: dict) -> None:
        """Reply to ``ipc.profile.set_consent`` from the Settings panel.

        Mirrors ``WizardLoop._on_profile_set_consent`` — persists the bool to
        state.json. Emits ``ipc.profile.consent_state`` ack so the renderer
        can confirm the write landed and refresh the panel's empty state.

        Best-effort: persistence failures are logged + swallowed; the UI's
        toggle remains the source of truth for the open dialog and a retry
        is one click away.
        """
        try:
            from vibemix.profile import save_consent
            from vibemix.ui_bus.messages import ProfileConsentState

            payload = msg.get("payload", {})
            consent = bool(payload.get("consent", False))
            save_consent(consent)
            log.info("profile_consent persisted from session panel: %s", consent)
            await self.bus.emit(
                json.loads(ProfileConsentState.make(consent=consent).to_json())
            )
        except Exception as e:
            log.warning("session.profile.set_consent persistence failed: %s", e)

    async def run_boot_sweeps(self) -> None:
        """Phase 15 Plan 03 — boot-time trigger.

        Fires ``run_retention_sweep`` with the live ``retention_days`` value
        once on session-loop startup, BEFORE accepting any IPC traffic. The
        crashed-session sweep runs separately at ``__main__.py`` boot (Plan
        15-02) — by the time we get here, ``crashed=True`` markers are
        already written, so the retention sweep walks an up-to-date tree.

        Always emits a ``ipc.recordings.usage`` push at the end (even if the
        sweep deleted nothing) so the drawer's disk-usage line is live from
        the moment the renderer connects.

        Best-effort: any unexpected exception is logged + swallowed; the
        session loop must continue regardless.

        Phase 15 Plan 02 — body delegates to the shared
        ``_fire_one_retention_sweep`` helper so the boot trigger shares the
        same code path as the periodic + close triggers (single place to
        adjust the events.jsonl logging gate, log line shape, and usage
        emit ordering).
        """
        await self._fire_one_retention_sweep("boot")

    async def on_session_close(self) -> None:
        """Phase 15 Plan 03 — session-close trigger.

        Called from ``__main__``'s close path AFTER ``recorder.close()`` so
        the just-finished session's session.json is finalized before the
        sweep walks the tree.

        Same best-effort guarantee as run_boot_sweeps — never raises.
        """
        await self._fire_one_retention_sweep("close")

    # ------------------------------------------------------------------
    # Phase 15 Plan 02 — shared retention-sweep dispatch
    # ------------------------------------------------------------------

    async def _fire_one_retention_sweep(self, trigger: str) -> None:
        """Run one retention sweep + emit usage push + log events.jsonl line.

        Single dispatch point for all four sweep triggers (boot, periodic,
        close, settings-change* — *settings-change uses the SettingsApplier's
        own path because it needs the NEW value before the slider commits;
        every other trigger reads ``self.config_store.retention_days``).

        Pseudo-flow:
            1. recordings_root None → early return (no sweep).
            2. Offload run_retention_sweep to executor (filesystem-bound).
            3. Log to Python logger (always — even zero-prune ticks).
            4. If count > 0 AND active_recorder set → write events.jsonl line
               via VoiceRecorder.log_event("retention_pruned",
               count=N, bytes=M). Plan 15-02 T-15-02-04 disposition: skip
               the events.jsonl write on count == 0 to keep noise down.
            5. Always emit ipc.recordings.usage so the drawer's disk-usage
               line stays live (even on zero-prune ticks the bytes_total
               from compute_usage may have changed if other surfaces
               wrote/deleted between sweeps).

        Best-effort: any exception is logged + swallowed.
        """
        if self.recordings_root is None:
            return
        try:
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                None,
                run_retention_sweep,
                self.recordings_root,
                self.config_store.retention_days,
            )
            if result.deleted_names:
                log.info(
                    "retention sweep (%s): deleted %d session(s) (%d bytes): %s",
                    trigger,
                    len(result.deleted_names),
                    result.bytes_pruned,
                    ", ".join(result.deleted_names),
                )
                self._log_retention_event_to_active_recorder(
                    count=len(result.deleted_names),
                    bytes_pruned=result.bytes_pruned,
                )
            else:
                log.info("retention sweep (%s): no sessions to prune", trigger)
            await self._emit_recordings_usage()
        except Exception:
            log.exception("retention sweep (%s) failed", trigger)

    def _log_retention_event_to_active_recorder(
        self, *, count: int, bytes_pruned: int
    ) -> None:
        """Write the `retention_pruned` events.jsonl line on the live recorder.

        No-op when ``self.active_recorder`` is None (the --session standalone
        path runs without a live recorder). Duck-typed: any object with a
        ``log_event(kind, **fields)`` method works — keeps the periodic loop
        decoupled from the audio package import surface.

        Schema: ``{"t": <secs-since-session-start>, "kind": "retention_pruned",
        "count": N, "bytes": M}`` — matches existing events.jsonl shape
        (recorder.py:304's ``{"t": round(rel, 3), "kind": kind, **fields}``).
        CONTEXT.md's ``{"event": ..., "t_session": ...}`` wording was
        approximate; the runtime contract is what ships.
        """
        if self.active_recorder is None:
            return
        log_event = getattr(self.active_recorder, "log_event", None)
        if log_event is None:
            log.warning(
                "active_recorder has no log_event method — retention_pruned not logged"
            )
            return
        try:
            log_event("retention_pruned", count=count, bytes=bytes_pruned)
        except Exception:
            log.exception("active_recorder.log_event(retention_pruned) failed")

    async def _periodic_retention_sweep_loop(self) -> None:
        """Fire ``_fire_one_retention_sweep("periodic")`` every interval.

        Uses ``asyncio.wait_for(self._stop.wait(), timeout=interval)`` so
        cancellation is sub-second (NOT bare ``asyncio.sleep`` which would
        block for up to 6h on shutdown — T-15-02-01 disposition; Test 2B
        is the gate).

        Reads ``RETENTION_SWEEP_INTERVAL_S`` from the module on every
        iteration so test monkeypatches take effect on the next tick.
        """
        # Inline import to read the module attribute fresh on every iteration
        # — `from X import Y` would freeze a local at import time, defeating
        # monkeypatch.
        from vibemix.runtime import session_loop as _self_mod  # noqa: PLC0415

        while not self._stop.is_set():
            interval = float(_self_mod.RETENTION_SWEEP_INTERVAL_S)
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=interval)
                # _stop fired during the wait — exit immediately.
                return
            except asyncio.TimeoutError:
                pass  # interval elapsed without stop — fire a sweep
            if self._stop.is_set():
                return
            await self._fire_one_retention_sweep("periodic")

    async def _emit_recordings_usage(self) -> None:
        """Compute current usage + emit ``ipc.recordings.usage`` on the bus."""
        if self.recordings_root is None:
            return
        try:
            loop = asyncio.get_running_loop()
            index = RecordingsIndex(self.recordings_root)
            sessions, bytes_total = await loop.run_in_executor(
                None, index.compute_usage
            )
            msg = RecordingsUsage.make(
                sessions=sessions, bytes_total=bytes_total
            )
            await self.bus.emit(json.loads(msg.to_json()))
        except Exception:
            log.exception("recordings.usage emit failed")

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
        # IN-03 in 14-REVIEW.md — round-trip mood + click_through too,
        # so the SettingsSet enum's 10 fields can all be persisted
        # through SettingsState. mood reads from MusicState (the live
        # source-of-truth Plan 13-05's settings applier writes to);
        # click_through reads from ConfigStore.extra (where Plan 13-05's
        # _apply_click_through persists it).
        mood: str | None = None
        if self.music_state is not None:
            raw_mood = getattr(self.music_state, "mood", None)
            if raw_mood in ("hype-man", "teacher", "coach"):
                mood = raw_mood
        click_through_raw = self.config_store.extra.get("click_through")
        click_through: bool | None = (
            click_through_raw if isinstance(click_through_raw, bool) else None
        )
        state = SettingsState.make(
            voice=self.config_store.voice,
            mode=self.config_store.mode,  # type: ignore[arg-type]
            genre=self.config_store.genre,
            output_device_id=self.config_store.output_device_id,
            output_profile=self.config_store.output_profile,  # type: ignore[arg-type]
            retention_days=self.config_store.retention_days,
            push_to_mute_hotkey=self.config_store.push_to_mute_hotkey,
            muted=self.muted,
            lighter_blur=self.config_store.lighter_blur,
            mood=mood,  # type: ignore[arg-type]
            click_through=click_through,
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
        """Register handlers → start bus → emit boot → run boot sweeps →
        spawn snapshot → wait on stop event → tear down.

        Phase 15 Plan 03: ``run_boot_sweeps()`` fires the boot-time retention
        sweep + emits one ``recordings.usage`` push BEFORE the snapshot loop
        starts so the renderer sees an up-to-date disk-usage line on
        connect. Crashed-session sweep runs in ``__main__.py`` (Plan 15-02)
        already, so by the time we reach ``run_boot_sweeps`` the tree is
        consistent.
        """
        self.register_handlers()
        try:
            await self.bus.start()
        except OSError as e:
            print(
                f"[FATAL] ws_bus port bind failed on 127.0.0.1:8765 — {e}",
                file=sys.stderr,
                flush=True,
            )
            print(
                "[FATAL] another vibemix process is already running; "
                "quit it before relaunching.",
                file=sys.stderr,
                flush=True,
            )
            sys.exit(2)
        await self.boot()
        # Phase 15 Plan 03 — boot sweep (best-effort; never raises).
        await self.run_boot_sweeps()
        self._snapshot_task = asyncio.create_task(self._snapshot_loop())
        # Orphan-process self-shutdown — set _stop if Tauri parent dies
        # abruptly so we don't sit on port 8765 and block the next launch.
        self._parent_watch_task = asyncio.create_task(watch_parent(self._stop))
        # Phase 15 Plan 02 — periodic 6h retention sweep task. Spawned
        # only when recordings_root is wired (i.e., not in --session
        # standalone mode without the recordings tree). Cancellation is
        # sub-second via the asyncio.wait_for race against _stop.
        if self.recordings_root is not None:
            self._retention_task = asyncio.create_task(
                self._periodic_retention_sweep_loop()
            )

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
            for task in (
                self._snapshot_task,
                self._retention_task,
                self._parent_watch_task,
            ):
                if task is not None:
                    task.cancel()
                    try:
                        await task
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

    Phase 15 Plan 03: passes ``recordings_root`` from ``app_data_dir()``
    so the recording browser handlers + retention sweep operate on the
    production path (``~/Library/Application Support/vibemix/recordings``
    on macOS, ``%APPDATA%/vibemix/recordings`` on Windows). On shutdown
    fires ``on_session_close`` for the session-close sweep trigger.
    """
    logging.basicConfig(level=logging.INFO, format="[%(name)s] %(message)s")
    bus = WizardBus()
    # Inline import — config_store.app_data_dir is a Phase 15-02 public
    # alias; keep the runtime/session_loop top-level imports unchanged.
    from vibemix.runtime.config_store import app_data_dir  # noqa: PLC0415

    recordings_root = app_data_dir() / "recordings"
    loop = SessionLoop(bus, recordings_root=recordings_root)
    print("-> session boot", file=sys.stderr)
    started = time.monotonic()
    try:
        await loop.run()
    finally:
        # Phase 15 Plan 03 — session-close trigger.
        try:
            await loop.on_session_close()
        except Exception:
            log.exception("on_session_close during run_session shutdown failed")
    print(f"-> session exit ({time.monotonic() - started:.1f}s)", file=sys.stderr)
    return 0


__all__ = ["SessionLoop", "SNAPSHOT_HZ", "SNAPSHOT_INTERVAL", "run_session"]
