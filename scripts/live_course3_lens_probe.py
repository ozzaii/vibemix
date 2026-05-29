#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Probe Course 3 live lens evidence on the existing sidecar socket.

Run while vibemix is running and Course 3/Rekordbox/audio are active:

    uv run python scripts/live_course3_lens_probe.py --require-count-in

The probe watches the flat 30 Hz ws://127.0.0.1:8765 frames for
``course3_lens`` and prints one JSON summary.
"""
from __future__ import annotations

import argparse
import asyncio
import json
from datetime import UTC, datetime
from typing import Any

DEFAULT_WS_URL = "ws://127.0.0.1:8765"
DEFAULT_COURSE3_LESSON_ID = "L3.01"
AUDIBLE_MUSIC_FLOOR = 0.012
DECK_CITE_MIN_CONF = 0.6
_CONTEXT_KEYS = (
    "music",
    "audible",
    "deck",
    "phase",
    "bpm",
    "bpm_confidence",
    "deck_state",
    "course3_lens",
)


def envelope(message_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": message_type,
        "ts": datetime.now(UTC).isoformat(),
        "payload": payload,
    }


def extract_course3_lens(msg: dict[str, Any]) -> dict[str, Any] | None:
    """Return a Course 3 lens dict from a flat ws frame, if present."""
    if "type" in msg:
        return None
    lens = msg.get("course3_lens")
    return lens if isinstance(lens, dict) else None


def extract_course3_context(msg: dict[str, Any]) -> dict[str, Any] | None:
    """Return the flat-frame evidence context around the Course 3 lens.

    The lens alone only says "cold" or "ready." The surrounding flat frame says
    why: whether music was audible, which deck was attributed, and whether the
    deck-state publisher had a citable track row.
    """
    if "type" in msg:
        return None
    context = {key: msg.get(key) for key in _CONTEXT_KEYS if key in msg}
    return context or None


def lens_has_count_in(lens: dict[str, Any]) -> bool:
    """True when the lens has a citable forward count-in shape."""
    return (
        lens.get("session_active") is True
        and float(lens.get("phrase_position_confidence") or 0.0) >= 0.7
        and lens.get("next_phrase_at") is not None
        and bool(lens.get("next_phrase_cue_id"))
    )


def _safe_json_loads(raw: str | bytes) -> dict[str, Any] | None:
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", errors="replace")
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _float_value(raw: Any, default: float = 0.0) -> float:
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


def _deck_state_has_citable_track(deck_state: Any) -> bool:
    if not isinstance(deck_state, dict):
        return False
    for row in deck_state.values():
        if not isinstance(row, dict):
            continue
        if not row.get("track_id"):
            continue
        if _float_value(row.get("confidence")) >= DECK_CITE_MIN_CONF:
            return True
    return False


def course3_diagnostics(summary: dict[str, Any]) -> dict[str, Any]:
    """Explain why the proof is not count-in ready using observed evidence."""
    blockers: list[str] = []
    if summary.get("start_sent") and summary.get("lesson_loaded") is not True:
        blockers.append("Course 3 lesson did not load")
    if int(summary.get("lens_frames") or 0) < 1:
        blockers.append("no Course 3 lens frames arrived")

    max_music = _float_value(summary.get("max_music"))
    if max_music < AUDIBLE_MUSIC_FLOOR:
        blockers.append("live master audio stayed below the audible music floor")
    elif summary.get("audible_seen") is not True:
        blockers.append("music was present but the app never marked it audible")

    deck_values = summary.get("deck_values") or []
    if not deck_values:
        blockers.append("audible deck stayed none")
    if summary.get("deck_state_seen") is not True:
        blockers.append("deck_state stayed empty")
    elif summary.get("citable_deck_state_seen") is not True:
        blockers.append("deck_state had no citable track_id at confidence floor")
    if summary.get("active_seen") is not True:
        blockers.append("Course 3 session_active never became true")
    if summary.get("count_in_seen") is not True:
        blockers.append("no cue-backed next phrase count-in was observed")
    diagnostics: dict[str, Any] = {"blockers": blockers}
    operator_action = summary.get("operator_action")
    if isinstance(operator_action, dict) and operator_action.get("prompt"):
        diagnostics["operator_action"] = operator_action
    return diagnostics


def _normalize_operator_action(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    prompt = str(raw.get("prompt") or "").strip()
    if not prompt:
        return None
    steps = (
        [
            str(step).strip()
            for step in raw.get("steps", [])
            if str(step).strip()
        ]
        if isinstance(raw.get("steps"), list)
        else []
    )
    route = str(raw.get("route") or "").strip()
    return {
        "prompt": prompt,
        **({"route": route} if route else {}),
        **({"steps": steps} if steps else {}),
    }


async def run_course3_lens_probe(
    *,
    url: str = DEFAULT_WS_URL,
    seconds: float = 20.0,
    require_active: bool = False,
    require_count_in: bool = False,
    start_lesson_id: str | None = None,
) -> dict[str, Any]:
    import websockets

    deadline = asyncio.get_running_loop().time() + max(1.0, float(seconds))
    frames_seen = 0
    lens_frames = 0
    active_seen = False
    count_in_seen = False
    last_lens: dict[str, Any] | None = None
    last_context: dict[str, Any] | None = None
    max_music = 0.0
    audible_seen = False
    deck_values: set[str] = set()
    deck_state_seen = False
    citable_deck_state_seen = False
    lens_blockers: set[str] = set()
    operator_action: dict[str, Any] | None = None
    start_sent = False
    lesson_loaded = False

    async with websockets.connect(url) as ws:
        if start_lesson_id:
            await ws.send(
                json.dumps(
                    envelope(
                        "ipc.learn.start_lesson",
                        {"lesson_id": start_lesson_id, "level": "fresh"},
                    ),
                    separators=(",", ":"),
                )
            )
            start_sent = True
        while asyncio.get_running_loop().time() < deadline:
            remaining = deadline - asyncio.get_running_loop().time()
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=max(0.05, remaining))
            except TimeoutError:
                break
            except websockets.exceptions.ConnectionClosed:
                break
            msg = _safe_json_loads(raw)
            if msg is None:
                continue
            if msg.get("type") == "ipc.learn.lesson_loaded":
                payload = msg.get("payload")
                if (
                    isinstance(payload, dict)
                    and payload.get("lesson_id") == start_lesson_id
                ):
                    lesson_loaded = True
            frames_seen += 1
            context = extract_course3_context(msg)
            if context is not None:
                last_context = context
                max_music = max(max_music, _float_value(context.get("music")))
                audible_seen = audible_seen or context.get("audible") is True
                deck = context.get("deck")
                if isinstance(deck, str) and deck and deck != "none":
                    deck_values.add(deck)
                deck_state = context.get("deck_state")
                if isinstance(deck_state, dict) and deck_state:
                    deck_state_seen = True
                    citable_deck_state_seen = (
                        citable_deck_state_seen
                        or _deck_state_has_citable_track(deck_state)
                    )
            lens = extract_course3_lens(msg)
            if lens is None:
                continue
            lens_frames += 1
            last_lens = lens
            blockers = lens.get("blockers")
            if isinstance(blockers, list):
                lens_blockers.update(blocker for blocker in blockers if isinstance(blocker, str))
            operator_action = _normalize_operator_action(lens.get("operator_action")) or operator_action
            active_seen = active_seen or lens.get("session_active") is True
            count_in_seen = count_in_seen or lens_has_count_in(lens)
            if require_count_in and count_in_seen:
                break
            if require_active and not require_count_in and active_seen:
                break
            if not require_active and not require_count_in:
                break

    passed = lens_frames > 0
    if require_active:
        passed = passed and active_seen
    if require_count_in:
        passed = passed and count_in_seen
    summary = {
        "passed": passed,
        "url": url,
        "frames_seen": frames_seen,
        "lens_frames": lens_frames,
        "active_seen": active_seen,
        "count_in_seen": count_in_seen,
        "last_lens": last_lens,
        "last_context": last_context,
        "max_music": round(max_music, 6),
        "audible_seen": audible_seen,
        "deck_values": sorted(deck_values),
        "deck_state_seen": deck_state_seen,
        "citable_deck_state_seen": citable_deck_state_seen,
        "lens_blockers": sorted(lens_blockers),
        "operator_action": operator_action,
        "start_lesson_id": start_lesson_id,
        "start_sent": start_sent,
        "lesson_loaded": lesson_loaded,
        "requirements": {
            "active": require_active,
            "count_in": require_count_in,
        },
    }
    summary["diagnostics"] = course3_diagnostics(summary)
    return summary


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="live_course3_lens_probe",
        description="Watch the existing sidecar socket for Course 3 live lens evidence.",
    )
    parser.add_argument("--url", default=DEFAULT_WS_URL, help=f"WebSocket URL (default: {DEFAULT_WS_URL}).")
    parser.add_argument("--seconds", type=float, default=20.0, help="Capture window in seconds.")
    parser.add_argument(
        "--start-lesson",
        default=None,
        help=(
            "Send ipc.learn.start_lesson before watching the lens "
            f"(for live Course 3 proof, use {DEFAULT_COURSE3_LESSON_ID})."
        ),
    )
    parser.add_argument(
        "--require-active",
        action="store_true",
        help="Fail unless a frame shows Course 3 session_active=true.",
    )
    parser.add_argument(
        "--require-count-in",
        action="store_true",
        help="Fail unless a frame shows active Course 3 plus next phrase cue evidence.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        summary = asyncio.run(
            run_course3_lens_probe(
                url=args.url,
                seconds=args.seconds,
                require_active=args.require_active or args.require_count_in,
                require_count_in=args.require_count_in,
                start_lesson_id=args.start_lesson,
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
