# SPDX-License-Identifier: Apache-2.0
"""DEBRIEF WS server — 127.0.0.1:8766.

Emits Phase 25 + Plan 29-03 wrapper frames progressively:

  ipc.debrief.session-loaded  (immediate)
  ipc.debrief.chapter-list    (~ instant — Plan 29-01 derive_chapters)
  ipc.debrief.drills          (~ 5s — Gemini 3 Pro structured-output)
  ipc.debrief.tldr-audio      (~ 30s — Gemini TTS + PyAV encode)

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
        self._queue: asyncio.Queue[str] = asyncio.Queue()
        self._connections: set[Any] = set()

    # ---------------------------------------------------------------
    # Enqueue helpers
    # ---------------------------------------------------------------

    def enqueue_initial_frames(self) -> None:
        """Push the progressive frames onto the emit queue.

        Order: session-loaded → chapter-list → drills → tldr-audio.
        """
        from vibemix.ui_bus import (
            DebriefChapterList,
            DebriefDrills,
            DebriefSessionLoaded,
            DebriefTldrAudio,
        )

        session_dir = self.state.get("session_dir")
        session_id = session_dir.name if session_dir else "unknown"
        voice_meta = self.state.get("voice_meta")
        duration_s = voice_meta.duration_s if voice_meta else 0.0

        # 1. session-loaded
        self._enqueue(
            DebriefSessionLoaded.make(
                session_id=session_id,
                started_at=_started_at_unix(session_dir),
                duration_s=max(duration_s, 1.0),  # schema requires ≥ 0
            )
        )

        # 2. chapter-list
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

        # 3. drills
        drills = self.state.get("drills")
        if drills is not None:
            from vibemix.debrief.main import _drill_to_payload

            drill_payloads = tuple(_drill_to_payload(d) for d in drills.drills)
            self._enqueue(DebriefDrills.make(drills=drill_payloads))

        # 4. tldr-audio
        debrief = self.state.get("debrief") or {}
        tldr_sha256 = debrief.get("tldr_sha256")
        if tldr_sha256:
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
            self._queue.put_nowait(raw)
            logger.info(
                "[debrief] emit %s %d bytes",
                wrapper.type,
                len(raw),
            )
        except Exception as e:  # noqa: BLE001
            logger.error("[debrief] enqueue failed: %s", e)

    # ---------------------------------------------------------------
    # Lifecycle
    # ---------------------------------------------------------------

    async def _handler(self, websocket) -> None:
        """One connection — drain emit queue + dispatch tooltip requests."""
        self._connections.add(websocket)
        logger.info("[debrief] client connected %s", websocket.remote_address)
        try:
            # Send everything currently buffered.
            await self._drain_queue(websocket)
            async for raw in websocket:
                await self._dispatch_inbound(websocket, raw)
        except Exception as e:  # noqa: BLE001
            logger.info("[debrief] connection ended: %s", type(e).__name__)
        finally:
            self._connections.discard(websocket)

    async def _drain_queue(self, websocket) -> None:
        """Send everything currently in the queue without blocking."""
        while True:
            try:
                raw = self._queue.get_nowait()
            except asyncio.QueueEmpty:
                return
            try:
                await websocket.send(raw)
            except Exception:
                return

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
        if kind == "hello":
            return  # ack via initial frames already sent on connect
        logger.warning("[debrief] unknown kind %r", kind)
        from vibemix.ui_bus import DebriefError

        await websocket.send(
            DebriefError.make(reason="unknown_kind", message=kind).to_json()
        )

    def _build_tooltip_reply(self, event_id: str) -> str:
        from vibemix.debrief.drills import _parse_citation_tag
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

    async def serve_forever(self) -> None:
        """Block until cancelled."""
        if websockets is None:
            raise RuntimeError("websockets package not installed")
        try:
            async with websockets.serve(self._handler, self.host, self.port):
                logger.info(
                    "[debrief] WS server bound to %s:%d", self.host, self.port
                )
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
    except Exception:  # noqa: BLE001
        return 0.0
    return 0.0


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
    except Exception:  # noqa: BLE001
        return 75.0
