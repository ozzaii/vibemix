# SPDX-License-Identifier: Apache-2.0
"""DEBRIEF WS server — 127.0.0.1:8766.

Emits Phase 25 + Plan 29-03 wrapper frames progressively:

  ipc.debrief.session-loaded  (immediate)
  ipc.debrief.chapter-list    (~ instant — Plan 29-01 derive_chapters)
  ipc.debrief.drills          (~ 5s — Gemini 3 Pro structured-output)
  ipc.debrief.tldr-audio      (~ 30s — local Chatterbox TTS + PyAV encode)

Plus on-demand replies to ``ipc.debrief.citation-tooltip-request``.

Cache-hit path emits all 4 frames in < 1s (no Gemini calls). Error path
emits ``ipc.debrief.error`` and exits.

The server logs every emit + every inbound frame with the ``[debrief]``
prefix so sidecar.log greps cleanly.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from datetime import UTC, datetime
from typing import Any

try:
    import websockets
except ImportError:  # pragma: no cover — websockets is a hard dep
    websockets = None  # type: ignore[assignment]

__all__ = ["DebriefWsServer"]

logger = logging.getLogger("vibemix.debrief")


class DebriefWsServer:
    """Async WebSocket server bound to 127.0.0.1:port.

    Public surface:

    - :meth:`enqueue_initial_frames` — fill the emit queue with the
      progressive frames built from the orchestrator state.
    - :meth:`emit_error(reason, message)` — surface a typed
      :class:`DebriefError` frame.
    - :meth:`serve_forever()` — block on ``websockets.serve``.
    - :meth:`serve_for_seconds(s)` — bounded ``serve_forever`` used by
      the one-shot error path.
    """

    def __init__(
        self,
        *,
        port: int = 8766,
        host: str = "127.0.0.1",
        state: dict[str, Any] | None = None,
    ):
        self.host = host
        self.port = port
        self.state = state or {}
        # Every emitted frame, in emit order. New connections replay the
        # full history, then receive subsequent frames live — a client
        # that connects mid-generation (or reconnects after a drop) still
        # sees every progressive frame exactly once.
        self._history: list[str] = []
        self._connections: set[Any] = set()

    # ---------------------------------------------------------------
    # Enqueue helpers
    # ---------------------------------------------------------------

    def enqueue_initial_frames(self) -> None:
        """Emit the full progressive frame set from ``self.state``.

        Order: session-loaded → near-miss → chapter-list → drills →
        tldr-audio. The served first-time path calls the per-stage
        emitters below as each generation stage completes; this
        composition remains for the cache-hit/test path.
        """
        self.emit_session_loaded()
        self.emit_near_miss()
        self.emit_chapter_list()
        self.emit_drills()
        self.emit_tldr_audio()

    def emit_session_loaded(self) -> None:
        from vibemix.ui_bus import DebriefSessionLoaded

        session_dir = self.state.get("session_dir")
        session_id = session_dir.name if session_dir else "unknown"
        voice_meta = self.state.get("voice_meta")
        duration_s = float(self.state.get("duration_s") or 0.0)
        if duration_s <= 0.0 and voice_meta:
            duration_s = voice_meta.duration_s
        self._enqueue(
            DebriefSessionLoaded.make(
                session_id=session_id,
                started_at=_started_at_unix(session_dir),
                duration_s=max(duration_s, 1.0),  # schema requires ≥ 0
            )
        )

    def emit_near_miss(self) -> None:
        from vibemix.ui_bus import DebriefNearMiss

        near_miss_payload = self.state.get("near_miss_payload")
        if near_miss_payload is None:
            return
        self._enqueue(
            DebriefNearMiss.make(
                input_wav_relative_path=near_miss_payload.input_wav_relative_path,
                t_center=near_miss_payload.t_center,
                window=near_miss_payload.window,
                receipt_text=near_miss_payload.receipt_text,
                friend_line_text=near_miss_payload.friend_line_text,
                duration_s=near_miss_payload.duration_s,
                ear_test_clip_relative_path=(
                    near_miss_payload.ear_test_clip_relative_path
                ),
                friend_line_audio_relative_path=(
                    near_miss_payload.friend_line_audio_relative_path
                ),
                waveform_peaks=near_miss_payload.waveform_peaks,
            )
        )

    def emit_chapter_list(self) -> None:
        from vibemix.ui_bus import DebriefChapterList

        chapters = self.state.get("chapters") or []
        if not chapters and self.state.get("debrief"):
            # Cache-hit: rebuild ChapterRegion-like records from the dict.
            from vibemix.debrief.chapters import ChapterRegion

            chapters = [
                ChapterRegion(
                    id=c["id"],
                    start=c["start"],
                    end=c["end"],
                    label=c["label"],
                    kind=c["kind"],
                    citation_event_id=c["citation_event_id"],
                )
                for c in self.state["debrief"].get("chapters", [])
            ]
        from vibemix.debrief.main import _chapter_to_payload

        chapter_payloads = tuple(_chapter_to_payload(c) for c in chapters)
        self._enqueue(
            DebriefChapterList.make(
                chapters=chapter_payloads,
                derived_at=datetime.now(UTC).isoformat(),
            )
        )

    def emit_drills(self) -> None:
        from vibemix.ui_bus import DebriefDrills

        drills = self.state.get("drills")
        if drills is None:
            return
        from vibemix.debrief.main import _drill_to_payload

        drill_payloads = tuple(_drill_to_payload(d) for d in drills.drills)
        self._enqueue(DebriefDrills.make(drills=drill_payloads))

    def emit_tldr_audio(self) -> None:
        from vibemix.ui_bus import DebriefTldrAudio

        debrief = self.state.get("debrief") or {}
        tldr_sha256 = debrief.get("tldr_sha256")
        if not tldr_sha256:
            return
        self._enqueue(
            DebriefTldrAudio.make(
                audio_relative_path=debrief.get("tldr_path", "debrief_tldr.mp3"),
                duration_s=_estimate_mp3_duration(self.state.get("tldr_mp3_path")),
                tldr_sha256=tldr_sha256,
                mime_type="audio/mpeg",
            )
        )

    def emit_error(self, reason: str, message: str) -> None:
        """Push an :class:`DebriefError` frame onto the queue."""
        from vibemix.ui_bus import DebriefError

        self._enqueue(DebriefError.make(reason=reason, message=message))

    def _enqueue(self, wrapper: Any) -> None:
        try:
            raw = wrapper.to_json()
        except Exception as e:
            logger.error("[debrief] enqueue failed: %s", e)
            return
        self._history.append(raw)
        logger.info("[debrief] emit %s %d bytes", wrapper.type, len(raw))
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return  # pre-loop enqueue — history replays on connect
        if self._connections:
            loop.create_task(self._broadcast(raw))

    async def _broadcast(self, raw: str) -> None:
        for ws in list(self._connections):
            try:
                await ws.send(raw)
            except Exception:
                self._connections.discard(ws)

    # ---------------------------------------------------------------
    # Lifecycle
    # ---------------------------------------------------------------

    async def _handler(self, websocket) -> None:
        """One connection — replay history, then live frames + inbound RPC."""
        logger.info("[debrief] client connected %s", websocket.remote_address)
        try:
            # Replay everything emitted so far. Only AFTER the replay
            # catches up does the connection join the live-broadcast set —
            # the no-await window between loop exit and add() makes the
            # handoff gapless and duplicate-free on the single-threaded loop.
            sent = 0
            while sent < len(self._history):
                await websocket.send(self._history[sent])
                sent += 1
            self._connections.add(websocket)
            async for raw in websocket:
                await self._dispatch_inbound(websocket, raw)
        except Exception as e:
            logger.info("[debrief] connection ended: %s", type(e).__name__)
        finally:
            self._connections.discard(websocket)

    async def _dispatch_inbound(self, websocket, raw: str) -> None:
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("[debrief] dropped malformed frame")
            return
        kind = msg.get("type", "")
        if kind == "ipc.debrief.citation-tooltip-request":
            payload = msg.get("payload", {})
            event_id = payload.get("event_id", "")
            reply = self._build_tooltip_reply(event_id)
            await websocket.send(reply)
            return
        if kind == "ipc.debrief.moment-feedback":
            self._record_moment_feedback(msg.get("payload", {}))
            return
        if kind == "hello":
            return  # ack via initial frames already sent on connect
        logger.warning("[debrief] unknown kind %r", kind)
        from vibemix.ui_bus import DebriefError

        await websocket.send(
            DebriefError.make(reason="unknown_kind", message=kind).to_json()
        )

    def _record_moment_feedback(self, payload: object) -> bool:
        """Persist explicit user feedback on a debrief moment when consent allows it."""
        if not isinstance(payload, dict):
            logger.warning("[debrief] dropped malformed moment feedback payload")
            return False
        moment_id = _str_field(payload.get("moment_id"))
        citation_id = _str_field(payload.get("citation_id"))
        verdict = _str_field(payload.get("verdict"))
        surface = _str_field(payload.get("surface"))
        if (
            moment_id is None
            or citation_id is None
            or verdict not in {"agree", "disagree", "unclear"}
            or surface not in {"transition", "live_pill", "cue"}
        ):
            logger.warning("[debrief] dropped invalid moment feedback payload")
            return False

        consent = self._profile_consent()
        if not consent:
            logger.info("[debrief] moment feedback ignored because profile consent is off")
            return False

        session_dir = self.state.get("session_dir")
        session_id = getattr(session_dir, "name", None) or "unknown"
        row = {
            "event_id": (
                f"debrief_moment_{session_id}_{_event_id_component(moment_id)}_"
                f"{time.time_ns()}"
            ),
            "session_id": session_id,
            "surface": f"debrief_{surface}",
            "action": "moment_feedback",
            "label": verdict,
            "split": "calibration",
            "candidate_id": moment_id,
            "moment_id": moment_id,
            "citation_id": citation_id,
            "moment_surface": surface,
            "profile_consent": True,
        }
        try:
            from vibemix.intel.feedback import append_feedback_event, parse_feedback_event
            from vibemix.runtime.config_store import app_data_dir

            path = self.state.get("taste_feedback_path") or (
                app_data_dir() / "taste_feedback.jsonl"
            )
            return append_feedback_event(path, parse_feedback_event(row), profile_consent=consent)
        except Exception as exc:
            logger.warning("[debrief] moment feedback persistence skipped: %s", exc)
            return False

    def _profile_consent(self) -> bool:
        if "profile_consent" in self.state:
            return bool(self.state.get("profile_consent"))
        try:
            from vibemix.profile import load_consent

            return bool(load_consent())
        except Exception as exc:
            logger.warning("[debrief] profile consent read skipped: %s", exc)
            return False

    def _build_tooltip_reply(self, event_id: str) -> str:
        from vibemix.debrief.drills import _parse_citation_atom, _parse_citation_tag
        from vibemix.ui_bus import DebriefCitationTooltip

        evidence_snapshot = self.state.get("evidence_snapshot") or {}
        # Accept both `[ev:foo@1]` form and bare `ev:foo@1` form.
        bracketed = event_id if event_id.startswith("[") else f"[{event_id}]"
        parsed = _parse_citation_tag(bracketed)
        if parsed is None:
            return DebriefCitationTooltip.make(
                event_id=event_id,
                evidence_text="",
                timestamp=0.0,
                found=False,
            ).to_json()
        source, key, t_target = parsed
        ts = (evidence_snapshot.get(source, {}) or {}).get(key, [])
        if not ts:
            atom = _parse_citation_atom(bracketed)
            if atom is not None:
                _source, raw_body = atom
                ts = (evidence_snapshot.get(source, {}) or {}).get(raw_body, [])
                if ts:
                    key = raw_body
                    t_target = None
        if not ts:
            return DebriefCitationTooltip.make(
                event_id=event_id,
                evidence_text="",
                timestamp=0.0,
                found=False,
            ).to_json()
        # Pick the closest timestamp (or first if no target).
        if t_target is None:
            chosen = ts[0]
        else:
            chosen = min(ts, key=lambda t: abs(t - t_target))
        return DebriefCitationTooltip.make(
            event_id=event_id,
            evidence_text=f"{source}:{key} @ {chosen:.1f}s",
            timestamp=float(chosen),
            found=True,
        ).to_json()

    async def serve_forever(self, *, bound: asyncio.Event | None = None) -> None:
        """Block until cancelled. Sets ``bound`` once the port is listening."""
        if websockets is None:
            raise RuntimeError("websockets package not installed")
        try:
            async with websockets.serve(self._handler, self.host, self.port):
                logger.info(
                    "[debrief] WS server bound to %s:%d", self.host, self.port
                )
                if bound is not None:
                    bound.set()
                await asyncio.Future()
        except OSError as e:
            # Port already in use → graceful exit with error.
            logger.error("[debrief] port %d unavailable: %s", self.port, e)
            from vibemix.ui_bus import DebriefError

            err = DebriefError.make(
                reason="port_in_use",
                message=f"port {self.port} unavailable: {e}",
            ).to_json()
            # Best-effort log; nothing to send to since the server didn't bind.
            logger.error("[debrief] would have emitted: %s", err)
            os._exit(1)

    async def serve_for_seconds(self, seconds: float) -> None:
        """One-shot bounded serve — used by the emit_error path."""
        if websockets is None:
            raise RuntimeError("websockets package not installed")
        try:
            async with websockets.serve(self._handler, self.host, self.port):
                await asyncio.sleep(seconds)
        except OSError as e:
            logger.error("[debrief] port %d unavailable: %s", self.port, e)


def _started_at_unix(session_dir) -> float:
    """Pull session start time from session.json if present, else 0.0."""
    if session_dir is None:
        return 0.0
    try:
        from pathlib import Path

        sj = Path(session_dir) / "session.json"
        if sj.exists():
            data = json.loads(sj.read_text(encoding="utf-8"))
            ts = data.get("started_at_unix")
            if isinstance(ts, (int, float)):
                return float(ts)
    except Exception:
        return 0.0
    return 0.0


def _str_field(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _event_id_component(value: str) -> str:
    safe = "".join(ch if ch.isalnum() else "_" for ch in value).strip("_")
    return (safe or "moment")[:64]


def _estimate_mp3_duration(mp3_path) -> float:
    """Best-effort MP3 duration via PyAV; falls back to 75.0 (midpoint)."""
    if mp3_path is None:
        return 75.0
    try:
        import av

        container = av.open(str(mp3_path))
        duration = float(container.duration) / 1_000_000.0 if container.duration else 75.0
        container.close()
        return max(duration, 1.0)
    except Exception:
        return 75.0
