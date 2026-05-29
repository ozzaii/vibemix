#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Live sidecar socket probe for the on-screen Learn path.

Start vibemix first, then run:

    uv run python scripts/live_learn_screen_probe.py --seconds 60

The probe connects to the established ``ws://127.0.0.1:8765`` bus, starts
``L1.01``, sends the same screen-click ``lesson_continue`` ACKs as the Learn UI,
and waits for the runtime to emit completion plus a persisted progress snapshot.
It is the live proof for the "use the DJ set on the screen" path when no
physical controller is currently visible to macOS MIDI.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime
from typing import Any

DEFAULT_WS_URL = "ws://127.0.0.1:8765"
LESSON_ID = "L1.01"
CONTROL_ID = "lesson_continue"
CONTINUE_ACKS_REQUIRED = 4


def envelope(message_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": message_type,
        "ts": datetime.now(UTC).isoformat(),
        "payload": payload,
    }


def continue_ack() -> dict[str, Any]:
    return envelope(
        "ipc.learn.ack",
        {
            "control_id": CONTROL_ID,
            "source": "click",
            "value": 127,
            "prev_value": 0,
            "direction": "down",
        },
    )


def progress_marks_completed(msg: dict[str, Any], *, lesson_id: str = LESSON_ID) -> bool:
    if msg.get("type") != "ipc.learn.progress_state":
        return False
    payload = msg.get("payload")
    if not isinstance(payload, dict):
        return False
    progress = payload.get("progress")
    if not isinstance(progress, dict):
        return False
    lessons = progress.get("lessons")
    if not isinstance(lessons, dict):
        return False
    row = lessons.get(lesson_id)
    return isinstance(row, dict) and row.get("completed") is True


def _safe_json_loads(raw: str | bytes) -> dict[str, Any] | None:
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", errors="replace")
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


async def run_screen_probe(
    *,
    url: str = DEFAULT_WS_URL,
    seconds: float = 60.0,
    lesson_id: str = LESSON_ID,
) -> dict[str, Any]:
    """Run the live screen-deck probe and return a JSON summary."""
    import websockets

    observed_types: list[str] = []
    tutor_lines: list[str] = []
    lesson_loaded: dict[str, Any] | None = None
    complete: dict[str, Any] | None = None
    progress_completed = False
    acks_sent = 0
    advance_count = 0
    deadline = asyncio.get_running_loop().time() + max(1.0, float(seconds))

    async with websockets.connect(url) as ws:
        await ws.send(
            json.dumps(
                envelope(
                    "ipc.learn.start_lesson",
                    {"lesson_id": lesson_id, "level": "fresh"},
                ),
                separators=(",", ":"),
            )
        )
        print(
            f"connected to {url}. Starting {lesson_id} and clicking continue.",
            file=sys.stderr,
            flush=True,
        )
        while asyncio.get_running_loop().time() < deadline:
            remaining = deadline - asyncio.get_running_loop().time()
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=max(0.05, remaining))
            except TimeoutError:
                break
            msg = _safe_json_loads(raw)
            if msg is None:
                continue
            msg_type = msg.get("type")
            if isinstance(msg_type, str):
                observed_types.append(msg_type)
            if msg_type == "ipc.learn.lesson_loaded":
                lesson_loaded = msg
            elif msg_type == "ipc.learn.tutor_speak":
                payload = msg.get("payload")
                if isinstance(payload, dict) and isinstance(payload.get("text"), str):
                    tutor_lines.append(payload["text"])
                if acks_sent < CONTINUE_ACKS_REQUIRED:
                    await ws.send(json.dumps(continue_ack(), separators=(",", ":")))
                    acks_sent += 1
            elif msg_type == "ipc.learn.advance":
                advance_count += 1
            elif msg_type == "ipc.learn.complete_lesson":
                payload = msg.get("payload")
                if isinstance(payload, dict) and payload.get("lesson_id") == lesson_id:
                    complete = msg
            if progress_marks_completed(msg, lesson_id=lesson_id):
                progress_completed = True
            if complete is not None and progress_completed:
                break

    passed = (
        lesson_loaded is not None
        and acks_sent == CONTINUE_ACKS_REQUIRED
        and advance_count >= CONTINUE_ACKS_REQUIRED
        and complete is not None
        and progress_completed
    )
    return {
        "passed": passed,
        "url": url,
        "lesson_id": lesson_id,
        "control_id": CONTROL_ID,
        "lesson_loaded": lesson_loaded is not None,
        "lesson_loaded_controller_id": (
            lesson_loaded.get("payload", {}).get("controller_id")
            if lesson_loaded is not None
            else None
        ),
        "acks_sent": acks_sent,
        "advance_count": advance_count,
        "complete_seen": complete is not None,
        "progress_completed": progress_completed,
        "tutor_lines": tutor_lines,
        "observed_types": observed_types,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="live_learn_screen_probe",
        description="Prove live Learn L1.01 on-screen completion over ws://127.0.0.1:8765.",
    )
    parser.add_argument(
        "--url",
        default=DEFAULT_WS_URL,
        help=f"WebSocket URL (default: {DEFAULT_WS_URL}).",
    )
    parser.add_argument(
        "--seconds",
        type=float,
        default=60.0,
        help="Capture window in seconds. Full completion needs the 45s Learn dwell.",
    )
    parser.add_argument("--lesson-id", default=LESSON_ID, help=f"Lesson id (default: {LESSON_ID}).")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        summary = asyncio.run(
            run_screen_probe(
                url=args.url,
                seconds=args.seconds,
                lesson_id=args.lesson_id,
            )
        )
    except OSError as exc:
        summary = {
            "passed": False,
            "url": args.url,
            "error": f"could not connect to live sidecar socket: {exc}",
        }
    except Exception as exc:  # pragma: no cover - defensive CLI boundary
        summary = {"passed": False, "url": args.url, "error": repr(exc)}
    print(json.dumps(summary, sort_keys=True))
    return 0 if summary.get("passed") is True else 4


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
