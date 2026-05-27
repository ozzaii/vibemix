# SPDX-License-Identifier: Apache-2.0
"""Structured feedback rows for deterministic taste learning."""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

PRIVATE_PAYLOAD_PATTERNS = (
    re.compile(r"/Users/[^\"'\s]+"),
    re.compile(r"/Volumes/[^\"'\s]+"),
    re.compile(r"[A-Za-z]:\\\\[^\"'\s]+"),
    re.compile(r"file://[^\"'\s]+", re.I),
)


@dataclass(frozen=True, slots=True)
class FeedbackEvent:
    """One private, structured taste/feedback event.

    These rows are product evidence, not prompt prose. They may carry synthetic
    or private IDs locally, but public reports must only expose aggregate counts.
    """

    event_id: str
    session_id: str
    surface: str
    action: str
    label: str | None = None
    split: str = "calibration"
    role_from: str | None = None
    role_to: str | None = None
    candidate_id: str | None = None
    risk_flags: tuple[str, ...] = ()
    score: float | None = None
    inferred: bool = False
    profile_consent: bool = True
    raw: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)

    @property
    def role_pair(self) -> tuple[str, str] | None:
        if not self.role_from or not self.role_to:
            return None
        return (self.role_from, self.role_to)


def parse_feedback_event(row: dict[str, Any]) -> FeedbackEvent:
    return FeedbackEvent(
        event_id=str(row.get("event_id") or ""),
        session_id=str(row.get("session_id") or ""),
        surface=str(row.get("surface") or ""),
        action=str(row.get("action") or ""),
        label=_str_or_none(row.get("label")),
        split=str(row.get("split") or "calibration"),
        role_from=_str_or_none(row.get("role_from")),
        role_to=_str_or_none(row.get("role_to")),
        candidate_id=_str_or_none(row.get("candidate_id")),
        risk_flags=tuple(str(flag) for flag in row.get("risk_flags") or ()),
        score=_float_or_none(row.get("score")),
        inferred=bool(row.get("inferred", False)),
        profile_consent=bool(row.get("profile_consent", True)),
        raw=dict(row),
    )


def load_feedback_events(path: Path | str) -> tuple[FeedbackEvent, ...]:
    text = Path(path).read_text(encoding="utf-8").strip()
    if not text:
        return ()
    if Path(path).suffix == ".jsonl":
        rows = [json.loads(line) for line in text.splitlines() if line.strip()]
    else:
        raw = json.loads(text)
        rows = raw if isinstance(raw, list) else [raw]
    return tuple(parse_feedback_event(row) for row in rows)


def feedback_event_to_row(
    event: FeedbackEvent,
    *,
    profile_consent: bool | None = None,
) -> dict[str, Any]:
    """Return a JSON-safe row preserving structured extras from ``raw``."""
    row = dict(event.raw)
    row.update(
        {
            "event_id": event.event_id,
            "session_id": event.session_id,
            "surface": event.surface,
            "action": event.action,
            "split": event.split,
            "risk_flags": list(event.risk_flags),
            "inferred": event.inferred,
            "profile_consent": event.profile_consent
            if profile_consent is None
            else bool(profile_consent),
        }
    )
    optional = {
        "label": event.label,
        "role_from": event.role_from,
        "role_to": event.role_to,
        "candidate_id": event.candidate_id,
        "score": event.score,
    }
    for key, value in optional.items():
        if value is not None:
            row[key] = value
        else:
            row.pop(key, None)
    return row


def append_feedback_event(
    path: Path | str,
    event: FeedbackEvent,
    *,
    profile_consent: bool = True,
) -> bool:
    """Append one consent-gated feedback row to JSONL local taste storage."""
    if not profile_consent or not event.profile_consent:
        return False

    row = feedback_event_to_row(event, profile_consent=True)
    errors = feedback_privacy_errors((parse_feedback_event(row),))
    if errors:
        raise ValueError(";".join(errors))

    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if sys.platform != "win32":
        try:
            os.chmod(p.parent, 0o700)
        except OSError:
            pass
    with p.open("a", encoding="utf-8") as fh:
        json.dump(row, fh, ensure_ascii=False, sort_keys=True)
        fh.write("\n")
    if sys.platform != "win32":
        try:
            os.chmod(p, 0o600)
        except OSError:
            pass
    return True


def persistable_events(
    events: tuple[FeedbackEvent, ...], *, profile_consent: bool
) -> tuple[FeedbackEvent, ...]:
    """Return events allowed to be written to long-term taste storage."""
    if not profile_consent:
        return ()
    return tuple(event for event in events if event.profile_consent)


def feedback_privacy_errors(events: tuple[FeedbackEvent, ...]) -> tuple[str, ...]:
    errors: list[str] = []
    for event in events:
        prefix = f"{event.event_id or '<missing>'}:"
        if not event.event_id:
            errors.append(prefix + "missing_event_id")
        if not event.session_id:
            errors.append(prefix + "missing_session_id")
        if _contains_private_payload(event.raw):
            errors.append(prefix + "private_payload_present")
    return tuple(errors)


def _contains_private_payload(value: Any) -> bool:
    if isinstance(value, dict):
        return any(
            str(key).lower()
            in {"path", "filepath", "file_path", "local_path", "raw_audio", "raw_vector"}
            or _contains_private_payload(item)
            for key, item in value.items()
        )
    if isinstance(value, list | tuple):
        return any(_contains_private_payload(item) for item in value)
    if isinstance(value, str):
        lowered = value.lower()
        return (
            lowered.startswith("audio:raw")
            or lowered.startswith("vector:")
            or any(pattern.search(value) for pattern in PRIVATE_PAYLOAD_PATTERNS)
        )
    return False


def _str_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


__all__ = [
    "FeedbackEvent",
    "append_feedback_event",
    "feedback_event_to_row",
    "feedback_privacy_errors",
    "load_feedback_events",
    "parse_feedback_event",
    "persistable_events",
]
