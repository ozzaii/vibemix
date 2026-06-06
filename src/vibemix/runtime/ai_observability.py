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
LIVE_RESPAN_SPAN_SCHEMA_VERSION = 1
LIVE_RESPAN_SPAN_CATEGORY = "sven-live-session"
SVEN_FEEDBACK_SCHEMA_VERSION = 1
SVEN_FEEDBACK_LABELS: frozenset[str] = frozenset(
    {
        "good",
        "bad",
        "not_actionable",
        "late",
        "early",
        "wrong",
        "too_much",
        "unsafe",
    }
)
_SVEN_FEEDBACK_ALIASES: dict[str, str] = {
    "up": "good",
    "thumbs_up": "good",
    "helpful": "good",
    "useful": "good",
    "actionable": "good",
    "keep": "good",
    "yes": "good",
    "down": "bad",
    "thumbs_down": "bad",
    "no": "bad",
    "narration": "not_actionable",
    "narrator": "not_actionable",
    "not-actionable": "not_actionable",
    "not actionable": "not_actionable",
    "vague": "not_actionable",
    "too_late": "late",
    "wrong_timing": "late",
    "too_early": "early",
    "incorrect": "wrong",
    "hallucinated": "wrong",
    "slop": "wrong",
    "chatty": "too_much",
    "too_long": "too_much",
    "too much": "too_much",
}
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


def _bounded_json(value: object, *, limit: int = 1200) -> str:
    try:
        text = json.dumps(value, ensure_ascii=False, sort_keys=True)
    except Exception:
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


def build_live_respan_span(record: dict[str, Any]) -> dict[str, Any]:
    """Return a privacy-safe Respan span for one live Sven decision.

    The span contains only text metadata already present in the AI-message row:
    evidence digest, emitted/suppressed line, citation decision, and local
    artifact paths. It intentionally omits raw audio bytes, screen frames, and
    the full prompt body.
    """

    response_id = str(record.get("response_id") or "")
    event = record.get("event")
    message = str(record.get("message") or "")
    citation = record.get("citation") if isinstance(record.get("citation"), dict) else {}
    citation_action = str(citation.get("action") or "")
    suppression = record.get("suppression")
    stop_reason = record.get("stop_reason")
    live_decision = "spoke" if citation_action == "emit" and message.strip() else "silent"
    silence_reason = None if live_decision == "spoke" else (suppression or stop_reason or citation_action)
    moves = record.get("moves") if isinstance(record.get("moves"), dict) else {}
    evidence_digest = _live_span_evidence_digest(
        response_id=response_id,
        event=event,
        live_decision=live_decision,
        silence_reason=silence_reason,
        citation=citation,
        moves=moves,
        extra=record.get("extra"),
    )
    metadata = {
        "schema": "vibemix_live_sven_respan_span_v1",
        "schema_version": LIVE_RESPAN_SPAN_SCHEMA_VERSION,
        "surface": record.get("surface"),
        "engine": record.get("engine"),
        "direction": record.get("direction"),
        "response_id": response_id,
        "event": event,
        "live_decision": live_decision,
        "silence_reason": silence_reason,
        "stop_reason": stop_reason,
        "suppression": suppression,
        "citation": citation,
        "grounded": bool(citation_action == "emit" and citation.get("valid") is not False),
        "should_evaluate_five_dim": bool(live_decision == "spoke" and message.strip()),
        "moves": moves,
        "artifacts": dict(record.get("artifacts") or {}),
        "privacy": {
            "contains_audio_bytes": False,
            "contains_screen_frames": False,
            "contains_full_prompt": False,
            "source": "ai_message_text_digest",
        },
    }
    return {
        "schema": "vibemix_live_sven_respan_span_v1",
        "schema_version": LIVE_RESPAN_SPAN_SCHEMA_VERSION,
        "model": record.get("model") or "unknown",
        "log_type": "chat",
        "input": [{"role": "user", "content": evidence_digest}],
        "output": {"role": "assistant", "content": message},
        # Legacy chat fields are still accepted by Respan and keep the local file
        # easy to use with older upload helpers.
        "prompt_messages": [{"role": "user", "content": evidence_digest}],
        "completion_message": {"role": "assistant", "content": message},
        "status": "success",
        "status_code": 200,
        "category": LIVE_RESPAN_SPAN_CATEGORY,
        "custom_identifier": response_id,
        "metadata": metadata,
    }


def normalize_sven_feedback_label(value: object) -> str | None:
    """Return a canonical fast by-ear label for a Sven line."""

    raw = str(value or "").strip().lower()
    if not raw:
        return None
    key = re.sub(r"[^a-z0-9]+", "_", raw).strip("_")
    label = _SVEN_FEEDBACK_ALIASES.get(key, key)
    return label if label in SVEN_FEEDBACK_LABELS else None


def record_session_sven_feedback(
    recorder: object | None,
    *,
    label: object,
    response_id: object | None = None,
    note: object | None = None,
    source: object | None = None,
    raw: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Append one operator by-ear label for a live Sven decision.

    If ``response_id`` is omitted, the latest session ``ai_message`` row is used.
    The row is local and text-only: no raw audio bytes, screen frames, or prompt
    body are copied into the feedback artifact.
    """

    canonical = normalize_sven_feedback_label(label)
    if canonical is None:
        return None
    target = _resolve_ai_feedback_target(recorder, response_id=response_id)
    if target is None:
        return None
    session_dir = getattr(recorder, "session_dir", None)
    session_id = getattr(session_dir, "name", None) if session_dir is not None else None
    message = str(target.get("message") or "")
    citation = target.get("citation") if isinstance(target.get("citation"), dict) else {}
    feedback = {
        "schema": "vibemix_sven_feedback_v1",
        "schema_version": SVEN_FEEDBACK_SCHEMA_VERSION,
        "ts_iso": _now_iso(),
        "session_id": session_id,
        "response_id": target.get("response_id"),
        "label": canonical,
        "score": _sven_feedback_score(canonical),
        "note": _bounded_text(note, limit=500),
        "source": str(source or "ws"),
        "target": {
            "event": target.get("event"),
            "live_decision": "spoke" if message.strip() else "silent",
            "message_preview": _bounded_text(message, limit=320) or "",
            "stop_reason": target.get("stop_reason"),
            "suppression": target.get("suppression"),
            "citation_action": citation.get("action"),
            "citation_count": citation.get("count"),
        },
        "privacy": {
            "contains_audio_bytes": False,
            "contains_screen_frames": False,
            "contains_full_prompt": False,
            "source": "operator_label",
        },
    }
    compact_raw = _compact_sven_feedback_raw(raw)
    if compact_raw:
        feedback["raw"] = compact_raw
    if recorder is None or not _enabled():
        return feedback
    try:
        path = _session_sven_feedback_path(recorder)
        artifacts = {"session_sven_feedback_path": str(path)} if path is not None else {}
        if artifacts:
            feedback["artifacts"] = artifacts
        _append_session_sven_feedback(recorder, feedback, path=path)
        recorder.log_event(
            "sven_feedback",
            schema=feedback["schema"],
            response_id=feedback["response_id"],
            label=feedback["label"],
            score=feedback["score"],
            source=feedback["source"],
            event=feedback["target"]["event"],
            live_decision=feedback["target"]["live_decision"],
            path=artifacts.get("session_sven_feedback_path"),
        )
    except Exception:
        pass
    return feedback


def _sven_feedback_score(label: str) -> int:
    return 1 if label == "good" else -1


def _compact_sven_feedback_raw(raw: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(raw, dict):
        return {}
    out: dict[str, Any] = {}
    for key in ("action", "feedback", "label", "response_id", "source"):
        if key in raw:
            out[key] = _bounded_text(raw.get(key), limit=160)
    return out


def _resolve_ai_feedback_target(
    recorder: object | None,
    *,
    response_id: object | None,
) -> dict[str, Any] | None:
    wanted = str(response_id or "").strip()
    if recorder is not None:
        latest = getattr(recorder, "_vibemix_latest_ai_message_record", None)
        if isinstance(latest, dict) and (not wanted or str(latest.get("response_id")) == wanted):
            return dict(latest)
    session_dir = getattr(recorder, "session_dir", None)
    if session_dir is None:
        return None
    events_path = Path(session_dir) / "events.jsonl"
    try:
        rows = events_path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return None
    for line in reversed(rows):
        try:
            row = json.loads(line)
        except Exception:
            continue
        if not isinstance(row, dict) or row.get("kind") != "ai_message":
            continue
        if wanted and str(row.get("response_id")) != wanted:
            continue
        return row
    return None


def _session_sven_feedback_path(recorder: object) -> Path | None:
    session_dir = getattr(recorder, "session_dir", None)
    return Path(session_dir) / "sven_feedback.jsonl" if session_dir is not None else None


def _append_session_sven_feedback(
    recorder: object,
    feedback: dict[str, Any],
    *,
    path: Path | None,
) -> None:
    if path is None:
        return
    line = json.dumps(feedback, ensure_ascii=False)
    lock = getattr(recorder, "_lock", None)
    if lock is not None:
        with lock:
            with path.open("a", encoding="utf-8") as fh:
                fh.write(line)
                fh.write("\n")
    else:
        with path.open("a", encoding="utf-8") as fh:
            fh.write(line)
            fh.write("\n")


def _live_span_evidence_digest(
    *,
    response_id: str,
    event: object,
    live_decision: str,
    silence_reason: object,
    citation: dict[str, Any],
    moves: dict[str, Any],
    extra: object,
) -> str:
    lines = [
        "SVEN LIVE DECISION EVIDENCE",
        f"response_id={response_id or 'unknown'}",
        f"event={event or 'unknown'}",
        f"decision={live_decision}",
    ]
    if silence_reason:
        lines.append(f"silence_reason={silence_reason}")
    lines.append(f"citation={_bounded_json(citation, limit=900)}")
    for key in (
        "event_moves",
        "recent_moves",
        "audio_delta",
        "audible_deck",
        "audible_track",
        "phase",
        "set_seconds",
        "vocal_active",
        "onset_density",
        "deck_mixer",
    ):
        if key in moves:
            lines.append(f"{key}={_bounded_json(moves.get(key), limit=900)}")
    if isinstance(extra, dict):
        compact_extra = {
            key: extra.get(key)
            for key in (
                "head_yielded",
                "diet",
                "cache_state",
                "audio_tokens_est",
                "avoided_audio_tokens_est",
                "deck_audio_parts",
                "live_claim_defer_stream",
                "pre_llm_fast_path",
                "pre_llm_short_circuit",
                "raw_response_chars",
                "spoken_response_chars",
            )
            if key in extra
        }
        if compact_extra:
            lines.append(f"turn={_bounded_json(compact_extra, limit=900)}")
    return "\n".join(lines)


def _append_session_respan_span(
    recorder: object,
    rec: dict[str, Any],
) -> dict[str, Any] | None:
    session_dir = getattr(recorder, "session_dir", None)
    if session_dir is None:
        return None
    try:
        root = Path(session_dir)
        span = build_live_respan_span(rec)
        span_path = root / "respan_spans.jsonl"
        line = json.dumps(span, ensure_ascii=False)
        lock = getattr(recorder, "_lock", None)
        if lock is not None:
            with lock:
                with span_path.open("a", encoding="utf-8") as fh:
                    fh.write(line)
                    fh.write("\n")
        else:
            with span_path.open("a", encoding="utf-8") as fh:
                fh.write(line)
                fh.write("\n")
        artifacts = dict(rec.get("artifacts") or {})
        artifacts["session_respan_spans_path"] = str(span_path)
        rec["artifacts"] = artifacts
        return span
    except Exception:
        return None


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
        span = _append_session_respan_span(recorder, rec)
        recorder.log_event("ai_message", **rec)
        try:
            recorder._vibemix_latest_ai_message_record = dict(rec)
        except Exception:
            pass
        if span is not None:
            metadata = span.get("metadata") if isinstance(span.get("metadata"), dict) else {}
            recorder.log_event(
                "respan_span",
                schema=span.get("schema"),
                response_id=span.get("custom_identifier"),
                event=metadata.get("event"),
                live_decision=metadata.get("live_decision"),
                silence_reason=metadata.get("silence_reason"),
                citation_action=(metadata.get("citation") or {}).get("action")
                if isinstance(metadata.get("citation"), dict)
                else None,
                should_evaluate_five_dim=metadata.get("should_evaluate_five_dim"),
                path=str(Path(recorder.session_dir) / "respan_spans.jsonl"),
            )
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
    "LIVE_RESPAN_SPAN_SCHEMA_VERSION",
    "SVEN_FEEDBACK_SCHEMA_VERSION",
    "append_global_ai_message",
    "build_ai_message_record",
    "build_live_respan_span",
    "compact_prompt_preview",
    "move_context",
    "normalize_recent_moves",
    "normalize_sven_feedback_label",
    "record_session_ai_message",
    "record_session_sven_feedback",
    "snapshot_state_for_ai_message",
]
