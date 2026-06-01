# SPDX-License-Identifier: Apache-2.0
"""AI-message observability helpers.

The live trace already records low-level events (MIDI, LLM invoke, citation
counts). This module adds the higher-level forensic row: one saved AI message
with the surrounding move/deck evidence and engine metadata.

All writers are fail-soft. Observability must never change a DJ session.
"""

from __future__ import annotations

import json
import os
import re
import threading
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

AI_MESSAGE_SCHEMA_VERSION = 1
_ENV_ENABLED = "VIBEMIX_AI_OBSERVABILITY"
_LOG_LOCK = threading.Lock()
_SLUG_RE = re.compile(r"[^A-Za-z0-9_.-]+")


def _enabled() -> bool:
    raw = os.environ.get(_ENV_ENABLED)
    if raw is None:
        return True
    return raw.strip().lower() not in ("0", "false", "no", "off", "")


def _safe_slug(value: object, *, fallback: str = "ai_message") -> str:
    text = _SLUG_RE.sub("_", str(value or "").strip()).strip("._-")
    return (text or fallback)[:96]


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="milliseconds")


def _coerce_float(value: object) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _coerce_int(value: object, default: int | None = None) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _bounded_text(value: object, *, limit: int = 4000) -> str | None:
    if value is None:
        return None
    text = str(value)
    if len(text) <= limit:
        return text
    return text[: limit - 16] + "...<truncated>"


def normalize_recent_moves(raw: object, *, limit: int = 8) -> list[dict[str, object]]:
    """Return a JSON-safe recent-move list.

    Accepts the runtime shape ``[(age_s, label), ...]`` and the Viber proof
    shape ``["A_low cut", ...]``. The newest moves are kept.
    """
    if not isinstance(raw, (list, tuple)):
        return []
    rows: list[dict[str, object]] = []
    for item in raw[-limit:]:
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            age = _coerce_float(item[0])
            label = str(item[1]).strip()
            if not label:
                continue
            rec: dict[str, object] = {"label": label}
            if age is not None:
                rec["age_s"] = round(age, 3)
            rows.append(rec)
        else:
            label = str(item).strip()
            if label:
                rows.append({"label": label})
    return rows


def _event_moves(event_obj: object | None) -> list[dict[str, object]]:
    extra = getattr(event_obj, "extra", None)
    if not isinstance(extra, dict):
        return []
    return normalize_recent_moves(extra.get("moves"))


def _deck_controls(raw: object) -> dict[str, object]:
    if not isinstance(raw, dict):
        return {}
    out: dict[str, object] = {}
    for key in ("vol", "eq_low", "eq_mid", "eq_hi", "filter", "tempo", "play", "cue"):
        if key not in raw:
            continue
        value = raw.get(key)
        if isinstance(value, bool):
            out[key] = value
        elif isinstance(value, (int, float)):
            out[key] = int(value)
        elif value is not None:
            out[key] = str(value)
    return out


def _deck_mixer_from_state(state: object | None) -> dict[str, object]:
    if state is None:
        return {}
    return {
        "connected": bool(getattr(state, "controller_connected", False)),
        "xfader": _coerce_int(getattr(state, "xfader", None), 64),
        "deck_confidence": round(float(getattr(state, "deck_confidence", 0.0) or 0.0), 3),
        "A": _deck_controls(getattr(state, "deck_a", {})),
        "B": _deck_controls(getattr(state, "deck_b", {})),
    }


def _copy_dict(raw: object) -> dict:
    return dict(raw) if isinstance(raw, dict) else {}


def _copy_list(raw: object) -> list:
    return list(raw) if isinstance(raw, (list, tuple)) else []


def _snapshot_state_unlocked(state: object) -> SimpleNamespace:
    return SimpleNamespace(
        audible=bool(getattr(state, "audible", False)),
        audible_deck=str(getattr(state, "audible_deck", "none") or "none"),
        audible_track=getattr(state, "audible_track", None),
        audible_track_confidence=float(
            _coerce_float(getattr(state, "audible_track_confidence", None)) or 0.0
        ),
        phase=str(getattr(state, "phase", "") or ""),
        rms=float(_coerce_float(getattr(state, "rms", None)) or 0.0),
        bpm=float(_coerce_float(getattr(state, "bpm", None)) or 0.0),
        vocal_active=bool(getattr(state, "vocal_active", False)),
        onset_density=float(_coerce_float(getattr(state, "onset_density", None)) or 0.0),
        controller_connected=bool(getattr(state, "controller_connected", False)),
        xfader=_coerce_int(getattr(state, "xfader", None), 64),
        deck_confidence=float(_coerce_float(getattr(state, "deck_confidence", None)) or 0.0),
        deck_a=_copy_dict(getattr(state, "deck_a", {})),
        deck_b=_copy_dict(getattr(state, "deck_b", {})),
        recent_moves=_copy_list(getattr(state, "recent_moves", [])),
        audio_delta=_copy_list(getattr(state, "audio_delta", [])),
        set_seconds=float(_coerce_float(getattr(state, "set_seconds", None)) or 0.0),
    )


def snapshot_state_for_ai_message(state: object | None) -> object | None:
    """Freeze the live state used to build an AI prompt.

    ``Event.state`` intentionally points at the mutable ``MusicState`` object.
    Gemini can take seconds to respond, while the refresh thread keeps changing
    controller and deck fields. The AI-message row should describe the prompt
    evidence, so copy the small set of fields the observability record reads.
    """
    if state is None:
        return None
    lock = getattr(state, "_lock", None)
    if lock is not None:
        try:
            with lock:
                return _snapshot_state_unlocked(state)
        except Exception:
            pass
    try:
        return _snapshot_state_unlocked(state)
    except Exception:
        return None


def move_context(
    *,
    state: object | None = None,
    event_obj: object | None = None,
    live_context: dict[str, Any] | None = None,
) -> dict[str, object]:
    """Build the move/deck/audio context attached to an AI-message row."""
    out: dict[str, object] = {}
    if event_obj is not None:
        out["event_moves"] = _event_moves(event_obj)
        out["event_type"] = str(getattr(event_obj, "type", "") or "")
    if state is not None:
        out["recent_moves"] = normalize_recent_moves(getattr(state, "recent_moves", []))
        mixer = _deck_mixer_from_state(state)
        if mixer:
            out["deck_mixer"] = mixer
        audio_delta = getattr(state, "audio_delta", None)
        if isinstance(audio_delta, list):
            out["audio_delta"] = [str(x) for x in audio_delta[-6:]]
        out["audible_deck"] = str(getattr(state, "audible_deck", "none") or "none")
        out["audible_track"] = getattr(state, "audible_track", None)
        out["phase"] = str(getattr(state, "phase", "") or "")
        out["set_seconds"] = _coerce_float(getattr(state, "set_seconds", None))
        out["vocal_active"] = bool(getattr(state, "vocal_active", False))
        out["onset_density"] = _coerce_float(getattr(state, "onset_density", None))
    if live_context:
        out["live_context_recent_moves"] = normalize_recent_moves(live_context.get("recent_moves"))
        audio_delta = live_context.get("audio_delta")
        if isinstance(audio_delta, list):
            out["live_context_audio_delta"] = [str(x) for x in audio_delta[-6:]]
        if isinstance(live_context.get("deck_mixer"), dict):
            out["live_context_deck_mixer"] = live_context["deck_mixer"]
        out["live_context_deck"] = live_context.get("deck")
        out["live_context_schema_version"] = live_context.get("live_context_schema_version")
    return out


def build_ai_message_record(
    *,
    engine: str,
    surface: str,
    direction: str,
    text: str | None = None,
    response_id: str | None = None,
    event: str | None = None,
    provider: str | None = None,
    model: str | None = None,
    stop_reason: str | None = None,
    latency_s: float | None = None,
    prompt_chars: int | None = None,
    response_chars: int | None = None,
    citation_count: int | None = None,
    citation_action: str | None = None,
    citation_valid: bool | None = None,
    citation_reason: str | None = None,
    suppression: str | None = None,
    state: object | None = None,
    event_obj: object | None = None,
    live_context: dict[str, Any] | None = None,
    tool_trace: list[dict[str, Any]] | None = None,
    tools_used: list[str] | None = None,
    move_grades: list[dict[str, Any]] | None = None,
    artifacts: dict[str, str] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return the canonical JSON-safe AI-message observability row."""
    msg = text or ""
    rec: dict[str, Any] = {
        "schema_version": AI_MESSAGE_SCHEMA_VERSION,
        "ts_iso": _now_iso(),
        "engine": str(engine),
        "surface": str(surface),
        "direction": str(direction),
        "response_id": response_id,
        "event": event,
        "provider": provider,
        "model": model,
        "stop_reason": stop_reason,
        "latency_s": latency_s,
        "message": msg,
        "message_chars": len(msg),
        "prompt_chars": prompt_chars,
        "response_chars": response_chars if response_chars is not None else len(msg),
        "suppression": suppression,
        "citation": {
            "count": citation_count,
            "action": citation_action,
            "valid": citation_valid,
            "reason": citation_reason,
        },
        "moves": move_context(state=state, event_obj=event_obj, live_context=live_context),
        "tools_used": list(tools_used or []),
        "tool_trace": list(tool_trace or []),
        "move_grades": list(move_grades or []),
        "artifacts": dict(artifacts or {}),
    }
    if extra:
        rec["extra"] = extra
    return rec


def record_session_ai_message(recorder: object | None, **kwargs: Any) -> dict[str, Any]:
    """Append an ``ai_message`` row to the active session's ``events.jsonl``."""
    prompt = kwargs.pop("prompt", None)
    response = kwargs.pop("response", None)
    try:
        rec = build_ai_message_record(**kwargs)
    except Exception:
        rec = {
            "schema_version": AI_MESSAGE_SCHEMA_VERSION,
            "ts_iso": _now_iso(),
            "engine": str(kwargs.get("engine", "unknown")),
            "surface": str(kwargs.get("surface", "unknown")),
            "direction": str(kwargs.get("direction", "assistant")),
            "message": "",
            "message_chars": 0,
            "observability_error": "record_build_failed",
        }
    if recorder is None or not _enabled():
        return rec
    try:
        _write_session_ai_artifacts(recorder, rec, prompt=prompt, response=response)
        recorder.log_event("ai_message", **rec)
    except Exception:
        pass
    return rec


def _write_session_ai_artifacts(
    recorder: object,
    rec: dict[str, Any],
    *,
    prompt: object | None,
    response: object | None,
) -> None:
    if prompt is None and response is None:
        return
    session_dir = getattr(recorder, "session_dir", None)
    if session_dir is None:
        return
    try:
        root = Path(session_dir)
        response_id = rec.get("response_id") or (
            f"{datetime.now().strftime('%Y%m%d-%H%M%S-%f')[:-3]}_"
            f"{_safe_slug(rec.get('surface'))}_{_safe_slug(rec.get('engine'))}"
        )
        rec["response_id"] = str(response_id)
        artifact_dir = root / "ai_messages" / "artifacts" / _safe_slug(response_id)
        artifact_dir.mkdir(parents=True, exist_ok=True)
        artifacts = dict(rec.get("artifacts") or {})
        if prompt is not None:
            prompt_text = str(prompt)
            prompt_path = artifact_dir / "prompt.txt"
            prompt_path.write_text(prompt_text, encoding="utf-8")
            artifacts["session_prompt_path"] = str(prompt_path)
            rec["prompt_chars"] = len(prompt_text)
        if response is not None:
            response_text = str(response)
            response_path = artifact_dir / "response.txt"
            response_path.write_text(response_text, encoding="utf-8")
            artifacts["session_response_path"] = str(response_path)
            rec["response_chars"] = len(response_text)
        meta_path = artifact_dir / "meta.json"
        artifacts["session_meta_path"] = str(meta_path)
        rec["artifacts"] = artifacts
        meta_path.write_text(json.dumps(rec, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def append_global_ai_message(
    *,
    root: Path | None = None,
    prompt: str | None = None,
    response: str | None = None,
    record: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Append an AI-message row outside a live session.

    Used by non-session engines such as Library/Viber Codex. Full prompt and
    response bodies are saved as artifacts; the JSONL row carries paths plus
    compact metadata.
    """
    try:
        rec = dict(record or build_ai_message_record(**kwargs))
    except Exception:
        rec = {
            "schema_version": AI_MESSAGE_SCHEMA_VERSION,
            "ts_iso": _now_iso(),
            "engine": str(kwargs.get("engine", "unknown")),
            "surface": str(kwargs.get("surface", "unknown")),
            "direction": str(kwargs.get("direction", "assistant")),
            "message": "",
            "message_chars": 0,
            "observability_error": "record_build_failed",
        }
    if not _enabled():
        return rec
    if (
        root is None
        and os.environ.get("PYTEST_CURRENT_TEST")
        and not os.environ.get("VIBEMIX_AI_OBSERVABILITY_IN_TESTS")
    ):
        return rec
    try:
        if root is None:
            from vibemix.runtime.config_store import app_data_dir

            root = app_data_dir()
        log_dir = root / "ai_messages"
        log_dir.mkdir(parents=True, exist_ok=True)
        response_id = rec.get("response_id") or (
            f"{datetime.now().strftime('%Y%m%d-%H%M%S-%f')[:-3]}_"
            f"{_safe_slug(rec.get('surface'))}_{_safe_slug(rec.get('engine'))}"
        )
        rec["response_id"] = str(response_id)
        artifact_dir = log_dir / "artifacts" / _safe_slug(response_id)
        artifacts = dict(rec.get("artifacts") or {})
        artifact_dir.mkdir(parents=True, exist_ok=True)
        if prompt is not None:
            prompt_path = artifact_dir / "prompt.txt"
            prompt_path.write_text(prompt, encoding="utf-8")
            artifacts["prompt_path"] = str(prompt_path)
            rec["prompt_chars"] = len(prompt)
        if response is not None:
            response_path = artifact_dir / "response.txt"
            response_path.write_text(response, encoding="utf-8")
            artifacts["response_path"] = str(response_path)
            rec["response_chars"] = len(response)
        meta_path = artifact_dir / "meta.json"
        artifacts["meta_path"] = str(meta_path)
        rec["artifacts"] = artifacts
        meta_path.write_text(json.dumps(rec, indent=2, ensure_ascii=False), encoding="utf-8")
        line = json.dumps(rec, ensure_ascii=False)
        with _LOG_LOCK:
            with (log_dir / "ai_messages.jsonl").open("a", encoding="utf-8") as fh:
                fh.write(line)
                fh.write("\n")
    except Exception:
        pass
    return rec


def compact_prompt_preview(prompt: object, *, limit: int = 4000) -> str | None:
    return _bounded_text(prompt, limit=limit)


__all__ = [
    "AI_MESSAGE_SCHEMA_VERSION",
    "append_global_ai_message",
    "build_ai_message_record",
    "compact_prompt_preview",
    "move_context",
    "normalize_recent_moves",
    "record_session_ai_message",
    "snapshot_state_for_ai_message",
]
