# SPDX-License-Identifier: Apache-2.0
"""Learn tutor observability rows.

Learn tutor copy is authored, not model-generated, but it is still assistant
speech. Keep it in the same ``ai_message`` stream as live coach and Viber so a
session timeline can answer "what did the system say?" with one query.
"""

from __future__ import annotations

from typing import Any

from vibemix.runtime.ai_observability import build_ai_message_record

__all__ = [
    "learn_tutor_speak_observability_events",
]


def _payload_from_speak(speak: dict[str, Any]) -> dict[str, Any] | None:
    payload = speak.get("payload") if isinstance(speak, dict) else None
    return payload if isinstance(payload, dict) else None


def learn_tutor_speak_observability_events(
    speak: dict[str, Any],
    *,
    lesson_id: str,
    course_id: str = "",
    step_id: str | None = None,
    source: str = "learn_runtime",
) -> list[tuple[str, dict[str, Any]]]:
    """Return ``learn_tutor_speak`` + shared ``ai_message`` events for a speak envelope."""
    payload = _payload_from_speak(speak)
    if payload is None:
        return []

    text = str(payload.get("text", "") or "")
    tts_marker = str(payload.get("tts_marker", "") or "")
    citations = payload.get("citations", [])
    citation_rows = list(citations) if isinstance(citations, (list, tuple)) else []
    data_state = str(payload.get("data_state", "") or "")
    teaching_loop = payload.get("teaching_loop")
    teaching_loop_row = teaching_loop if isinstance(teaching_loop, dict) else None

    speak_fields: dict[str, Any] = {
        "lesson_id": lesson_id,
        "course_id": course_id,
        "step_id": step_id,
        "text": text,
        "tts_marker": tts_marker,
        "citations": citation_rows,
        "data_state": data_state,
    }
    record = build_ai_message_record(
        engine="learn_tutor",
        surface="learn",
        direction="assistant",
        text=text,
        response_id=f"learn:{source}:{course_id}:{lesson_id}:{step_id or 'unknown'}:{tts_marker}",
        event="learn_tutor_speak",
        provider="authored_fixture",
        model=None,
        stop_reason="authored_fixture",
        response_chars=len(text),
        citation_count=len(citation_rows),
        citation_action="emit",
        citation_valid=bool(citation_rows),
        extra={
            "lesson_id": lesson_id,
            "course_id": course_id,
            "step_id": step_id,
            "tts_marker": tts_marker,
            "citations": citation_rows,
            "data_state": data_state,
            "source": source,
            "teaching_loop": teaching_loop_row,
        },
    )
    return [("learn_tutor_speak", speak_fields), ("ai_message", record)]
