# SPDX-License-Identifier: Apache-2.0
"""Session loader — load events.jsonl + evidence_registry.json + voice.wav meta.

Plan 29-02 sidecar invokes :func:`load_session` first; on
:class:`SessionTooShort` / :class:`EventsMissing` it surfaces an
``ipc.debrief.error`` frame to the renderer (Plan 29-05 disabled-button
path also reads these signals via the recordings list).
"""

from __future__ import annotations

import json
import logging
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any

__all__ = [
    "EventsMissing",
    "InvalidSessionDir",
    "SessionTooShort",
    "VoiceWavMeta",
    "load_session",
]

logger = logging.getLogger(__name__)

# Minimum session length below which we refuse to generate a debrief.
# 5 minutes per CONTEXT D-11 + RESEARCH Pitfall 6.
_MIN_SESSION_DURATION_S = 300.0


class SessionTooShort(Exception):
    """Session shorter than the 5-minute minimum."""

    def __init__(self, duration_s: float, reason: str = "session_too_short"):
        super().__init__(f"session too short: {duration_s:.1f}s < {_MIN_SESSION_DURATION_S}s")
        self.reason = reason
        self.duration_s = duration_s


class EventsMissing(Exception):
    """events.jsonl absent in the session_dir."""

    def __init__(self, session_dir: Path, reason: str = "events_missing"):
        super().__init__(f"events.jsonl missing in {session_dir}")
        self.reason = reason
        self.session_dir = session_dir


class InvalidSessionDir(Exception):
    """Path-traversal or non-existent session_dir."""

    def __init__(self, session_dir: Path | str, reason: str = "invalid_session_dir"):
        super().__init__(f"invalid session dir: {session_dir}")
        self.reason = reason
        self.session_dir = session_dir


@dataclass(frozen=True, slots=True)
class VoiceWavMeta:
    """Metadata about the session's voice.wav (Gemini reply audio).

    Renderer uses ``duration_s`` to size the WaveSurfer.js timeline.
    """

    path: Path
    sample_rate: int
    duration_s: float
    n_frames: int


def _read_events(events_jsonl_path: Path) -> list[dict]:
    """Parse events.jsonl into a list of dicts; skip malformed lines."""
    events: list[dict] = []
    with events_jsonl_path.open("r", encoding="utf-8") as f:
        for line_no, raw in enumerate(f, start=1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                events.append(json.loads(raw))
            except json.JSONDecodeError as e:
                logger.warning(
                    "[debrief] events.jsonl line %d malformed: %s", line_no, e
                )
    return events


def _compute_duration_s(events: list[dict]) -> float:
    """Compute session duration from first→last event ``t``."""
    if not events:
        return 0.0
    ts = [e.get("t", 0.0) for e in events if isinstance(e.get("t"), (int, float))]
    if not ts:
        return 0.0
    return float(max(ts) - min(ts))


def _read_voice_wav_meta(voice_wav_path: Path) -> VoiceWavMeta:
    """Read voice.wav header for sample_rate + duration via stdlib wave."""
    with wave.open(str(voice_wav_path), "rb") as wf:
        sr = wf.getframerate()
        n_frames = wf.getnframes()
    duration_s = n_frames / sr if sr > 0 else 0.0
    return VoiceWavMeta(
        path=voice_wav_path,
        sample_rate=sr,
        duration_s=duration_s,
        n_frames=n_frames,
    )


def load_session(session_dir: Path) -> tuple[list[dict], dict[str, Any], VoiceWavMeta | None]:
    """Load a recorded session and return (events, evidence_snapshot, voice_meta).

    Raises:
        EventsMissing: when ``session_dir/events.jsonl`` does not exist.
        SessionTooShort: when the computed duration is < 5 minutes.
        InvalidSessionDir: when ``session_dir`` is not a directory.

    Notes:
        - ``evidence_registry.json`` is OPTIONAL — Plan 29-00 added it to new
          sessions but legacy recordings predating Phase 18 may not have it.
          Returns an empty dict in that case (logged warning).
        - ``voice.wav`` is OPTIONAL — returns None if missing (renderer
          falls back to a placeholder waveform).
    """
    session_dir = Path(session_dir)
    if not session_dir.is_dir():
        raise InvalidSessionDir(session_dir)

    events_jsonl = session_dir / "events.jsonl"
    if not events_jsonl.exists():
        raise EventsMissing(session_dir)

    events = _read_events(events_jsonl)
    duration_s = _compute_duration_s(events)
    if duration_s < _MIN_SESSION_DURATION_S:
        raise SessionTooShort(duration_s=duration_s)

    # Optional evidence_registry.json (Plan 29-00 added it).
    evidence_snapshot: dict[str, Any] = {}
    evi_path = session_dir / "evidence_registry.json"
    if evi_path.exists():
        try:
            evidence_snapshot = json.loads(evi_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            logger.warning("[debrief] evidence_registry.json malformed: %s", e)
            evidence_snapshot = {}
    else:
        logger.info(
            "[debrief] no evidence_registry.json in %s — using empty snapshot",
            session_dir,
        )

    voice_meta: VoiceWavMeta | None = None
    voice_path = session_dir / "voice.wav"
    if voice_path.exists() and voice_path.stat().st_size > 0:
        try:
            voice_meta = _read_voice_wav_meta(voice_path)
        except Exception as e:  # noqa: BLE001 — degrade gracefully
            logger.warning("[debrief] voice.wav meta read failed: %s", e)

    return (events, evidence_snapshot, voice_meta)
