# SPDX-License-Identifier: Apache-2.0
"""Truthfulness guards for learner-facing Learn transcript copy."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

SPECULATIVE_DEBRIEF_AUTO_OPEN_PHRASES = (
    "debrief opens",
    "debrief will open",
    "opens automatically",
    "open automatically",
    "should have opened automatically",
    "the debrief is open",
)


def transcript_copy(script: Mapping[str, Any]) -> str:
    """Return the learner-facing text fields used by copy truthfulness checks."""
    fields: list[str] = []
    for value in (
        script.get("system_instruction_addendum"),
        script.get("title"),
    ):
        if isinstance(value, str):
            fields.append(value)
    for collection_name in ("tutor_speak", "hints"):
        rows = script.get(collection_name)
        if not isinstance(rows, list):
            continue
        for row in rows:
            if isinstance(row, Mapping) and isinstance(row.get("text"), str):
                fields.append(str(row["text"]))
    return "\n".join(fields)


def unsupported_debrief_auto_open_phrases(script: Mapping[str, Any]) -> tuple[str, ...]:
    """Return unwired debrief auto-open phrases present in learner copy."""
    lower = transcript_copy(script).lower()
    return tuple(
        phrase
        for phrase in SPECULATIVE_DEBRIEF_AUTO_OPEN_PHRASES
        if phrase in lower
    )


__all__ = [
    "SPECULATIVE_DEBRIEF_AUTO_OPEN_PHRASES",
    "transcript_copy",
    "unsupported_debrief_auto_open_phrases",
]
