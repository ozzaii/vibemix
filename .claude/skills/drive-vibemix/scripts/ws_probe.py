# SPDX-License-Identifier: Apache-2.0
"""ws_probe — connect to the vibemix mascot/session bus as a CLIENT and watch it.

The live co-host serves ONE WebSocket on ``ws://127.0.0.1:8765`` (Invariant #4:
single socket). It BROADCASTS two frame families to every connected client:

  * the flat 30Hz mascot frame (no ``type`` field) — meters + audible/deck/phase
    + bpm + ``next_suggestion`` + ``deck_state`` + ``course3_lens`` + ...
  * schema-typed ``ipc.session.snapshot`` (~15Hz), ``ipc.status.tick`` (~1Hz),
    and any ``ipc.learn.*`` envelopes.

It ACCEPTS inbound action frames on the same socket. The always-safe one is
``{"action": "trigger"}`` — it sets ``manual_trigger`` so the co-host fires a
reaction on the next loop tick (no schema validation, see ws_bus.py handler()).

This probe connects as a normal client (never a second listener), prints frames
it receives, and can send a single action frame from CLI args. stdlib + the
project's own ``websockets`` dep only — no new install.

USAGE (run with the project venv so ``websockets`` is importable):
    .venv/bin/python .claude/skills/drive-vibemix/scripts/ws_probe.py            # watch all frames
    .venv/bin/python .claude/skills/drive-vibemix/scripts/ws_probe.py --watch ipc.session.snapshot
    .venv/bin/python .claude/skills/drive-vibemix/scripts/ws_probe.py --trigger  # fire a manual reaction
    .venv/bin/python .claude/skills/drive-vibemix/scripts/ws_probe.py --ipc ipc.status.recheck --payload-json '{"component":"midi"}' --watch ipc.status.tick --seconds 3
    .venv/bin/python .claude/skills/drive-vibemix/scripts/ws_probe.py --seconds 5 --watch mascot
    # or:  uv run python .claude/skills/drive-vibemix/scripts/ws_probe.py --trigger

--watch values: a substring matched against a frame's ``type`` field, or the
literal ``mascot`` to show only the flat type-less mascot frame, or ``all``.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from datetime import UTC, datetime
from typing import Any

try:
    import websockets
    from websockets.exceptions import WebSocketException
except ImportError:  # pragma: no cover — actionable, not a traceback
    print(
        "ws_probe: `websockets` not importable. Run with the project venv:\n"
        "  .venv/bin/python .claude/skills/drive-vibemix/scripts/ws_probe.py ...\n"
        "  (or: uv run python .claude/skills/drive-vibemix/scripts/ws_probe.py ...)",
        file=sys.stderr,
    )
    sys.exit(2)

# Pinned to ws_bus.py / audio/constants.py (WS_HOST/WS_PORT). The bus binds
# 127.0.0.1:8765 ONLY — connecting here is a client attach, never a 2nd server.
URI = "ws://127.0.0.1:8765"

# Frame keys we surface for the flat 30Hz mascot frame — the high-signal subset
# (full frame is large; this keeps the tail readable). All verified present in
# ws_bus.ws_broadcast's mascot_frame builder.
_MASCOT_KEYS = (
    "music",
    "voice",
    "mic",
    "audible",
    "deck",
    "phase",
    "bpm",
    "active_genre",
    "detected_genre",
    "emotion",
    "next_suggestion",
)


def _is_mascot_frame(data: dict) -> bool:
    """The mascot frame is the only one with NO ``type`` field but WITH meters."""
    return "type" not in data and all(k in data for k in ("music", "voice", "mic"))


def _summarize(data: dict) -> str:
    """One-line summary of an incoming frame for a readable tail."""
    mtype = data.get("type")
    if mtype == "ipc.session.snapshot":
        p = data.get("payload", {})
        td = p.get("transcript_delta") or []
        spoken = " | ".join(t.get("text", "") for t in td) if td else ""
        bits = [
            f"cohost={p.get('cohost_status')}",
            f"grounded={p.get('grounded')}",
            f"bpm={p.get('bpm')}",
        ]
        if (track := p.get("track")):
            bits.append(f"track={track.get('title')!r}@{track.get('deck')}")
        if spoken:
            bits.append(f"AI_SPOKE={spoken!r}")
        return "ipc.session.snapshot  " + "  ".join(bits)
    if mtype == "ipc.status.tick":
        p = data.get("payload", {})
        return (
            f"ipc.status.tick  livekit={p.get('livekit')} gemini={p.get('gemini')} "
            f"midi={p.get('midi')} screen={p.get('screen')}"
        )
    if mtype:
        return f"{mtype}  {json.dumps(data.get('payload', {}))[:160]}"
    if _is_mascot_frame(data):
        bits = []
        for k in _MASCOT_KEYS:
            if k in data and data[k] not in (None, "", {}, []):
                v = data[k]
                if isinstance(v, float):
                    v = round(v, 3)
                bits.append(f"{k}={v}")
        return "mascot  " + "  ".join(bits)
    return "?  " + json.dumps(data)[:160]


def _matches(data: dict, watch: str) -> bool:
    if watch == "all":
        return True
    if watch == "mascot":
        return _is_mascot_frame(data)
    return watch in str(data.get("type", ""))


def _parse_payload_json(raw: str) -> dict[str, Any]:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"--payload-json must be a JSON object: {e.msg}") from e
    if not isinstance(payload, dict):
        raise ValueError("--payload-json must decode to a JSON object")
    return payload


def _build_send_frame(
    *,
    trigger: bool,
    action: str | None,
    ipc: str | None,
    payload: dict[str, Any],
) -> dict[str, Any] | None:
    senders = [bool(trigger), bool(action), bool(ipc)]
    if sum(senders) > 1:
        raise ValueError("choose only one of --trigger, --action, or --ipc")
    if trigger:
        return {"action": "trigger"}
    if action:
        if action.startswith("ipc."):
            raise ValueError("use --ipc for ipc.* frames so the timestamp is schema-valid")
        if "action" in payload:
            raise ValueError("--payload-json for --action must not contain an 'action' key")
        return {"action": action, **payload}
    if ipc:
        if not ipc.startswith("ipc."):
            raise ValueError("--ipc value must start with 'ipc.'")
        return {"type": ipc, "ts": datetime.now(UTC).isoformat(), "payload": payload}
    if payload:
        raise ValueError("--payload-json requires --action or --ipc")
    return None


async def _run(uri: str, watch: str, seconds: float | None, send_frame: dict[str, Any] | None) -> int:
    try:
        async with websockets.connect(uri) as ws:
            print(f"-> connected {uri}  (watch={watch!r})", file=sys.stderr)
            if send_frame is not None:
                await ws.send(json.dumps(send_frame))
                print(f"-> sent {json.dumps(send_frame, sort_keys=True)}", file=sys.stderr)
            deadline = (time.monotonic() + seconds) if seconds else None
            count = 0
            while True:
                if deadline is not None:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        break
                    try:
                        raw = await asyncio.wait_for(ws.recv(), timeout=remaining)
                    except TimeoutError:
                        break
                else:
                    raw = await ws.recv()
                try:
                    data = json.loads(raw) if isinstance(raw, str) else {}
                except json.JSONDecodeError:
                    continue
                if not isinstance(data, dict) or not _matches(data, watch):
                    continue
                count += 1
                print(f"[{count:04d}] {_summarize(data)}")
            print(f"-> done ({count} frames matched)", file=sys.stderr)
            return 0
    except (ConnectionRefusedError, OSError, WebSocketException) as e:
        print(
            f"ws_probe: cannot reach {uri} ({e}). Is the co-host running?\n"
            "  Launch dev-source: VIBEMIX_DEV_SIDECAR=1 cargo tauri dev (in tauri/),\n"
            "  or run the engine alone: uv run python -m vibemix",
            file=sys.stderr,
        )
        return 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="vibemix WS bus probe (client-only).")
    ap.add_argument("--uri", default=URI, help=f"WS uri (default {URI})")
    ap.add_argument(
        "--watch",
        default="all",
        help="frame filter: 'all', 'mascot', or a substring of the 'type' field "
        "(e.g. 'ipc.session.snapshot', 'ipc.status.tick', 'ipc.learn').",
    )
    ap.add_argument(
        "--seconds",
        type=float,
        default=None,
        help="auto-exit after N seconds (default: watch until Ctrl-C).",
    )
    ap.add_argument(
        "--trigger",
        action="store_true",
        help="send one {action:'trigger'} frame on connect (fires a manual reaction).",
    )
    ap.add_argument(
        "--action",
        default=None,
        help="send one bare action frame, e.g. next_suggestion.feedback.",
    )
    ap.add_argument(
        "--ipc",
        default=None,
        help="send one typed ipc.* envelope with an ISO date-time ts.",
    )
    ap.add_argument(
        "--payload-json",
        default="{}",
        help="JSON object payload for --action or --ipc.",
    )
    args = ap.parse_args(argv)
    try:
        payload = _parse_payload_json(args.payload_json)
        send_frame = _build_send_frame(
            trigger=args.trigger,
            action=args.action,
            ipc=args.ipc,
            payload=payload,
        )
    except ValueError as e:
        print(f"ws_probe: {e}", file=sys.stderr)
        return 2
    try:
        return asyncio.run(_run(args.uri, args.watch, args.seconds, send_frame))
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
