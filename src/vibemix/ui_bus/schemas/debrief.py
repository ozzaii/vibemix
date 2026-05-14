# SPDX-License-Identifier: Apache-2.0
"""Phase 25 Plan 25-03 — DEBRIEF IPC payload structs (architectural slot).

v2.0 reserves the surface; v2.1 implements the chaptered TL;DR + drill
cards + clickable timeline behind these 3 message types without breaking
the sidecar API. No emit path in v2.0 (DEBRIEF-01 + DEBRIEF-02 are
reservation-only).

Schema sources match the established pattern from Plan 20-04 (citation)
and Plan 24-02 (overlay) — payload-only structs live here; wrapper
classes live in ``vibemix.ui_bus.messages``; the JSON schema definitions
mirror them in ``tauri/ui/src/ipc/messages.schema.json``.

Locked field names + types (count-parity-tested at
``scripts/check_ipc_schema.py``):

- ``DebriefSessionLoadedPayload``: ``session_id`` / ``started_at`` /
  ``duration_s``
- ``DebriefCitationSummaryPayload``: ``total`` / ``valid`` / ``stripped``
  / ``bypassed`` (all int, ≥0)
- ``DebriefEventTimelinePayload``: ``events: tuple[dict, ...]``
  (chronologically ordered events.jsonl projection; tuple is required
  for dataclass-hashability under ``frozen=True, slots=True``)
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DebriefSessionLoadedPayload:
    """Emitted once when the DEBRIEF sidecar opens a session_dir.

    Fields:
        session_id: opaque identifier of the loaded session (e.g.
            ``"20260513-210410"``). Matches the ``recordings/<dir>`` name.
        started_at: epoch seconds when the session began (recordings
            metadata reads this from the session's first wall-clock event).
        duration_s: total session duration in seconds.
    """

    session_id: str
    started_at: float
    duration_s: float


@dataclass(frozen=True, slots=True)
class DebriefCitationSummaryPayload:
    """Aggregate citation stats over the loaded session.

    Fields mirror Phase 20 ``CitationLinter`` + ``StrippedRateTracker``
    telemetry so the v2.1 UI can render "what the grounding stack caught
    vs. let through" without re-deriving the numbers.

    Fields:
        total: total citations Gemini emitted during the session.
        valid: count whose ``[source:body]`` resolved against the
            ``EvidenceRegistry`` within ``tol=±2.0s`` (debrief tolerance
            band per GROUND-07).
        stripped: count the linter removed pre-TTS.
        bypassed: count silenced by the bypass guard
            (``StrippedRateTracker`` threshold trip).
    """

    total: int
    valid: int
    stripped: int
    bypassed: int


@dataclass(frozen=True, slots=True)
class DebriefEventTimelinePayload:
    """The session's event timeline rendered as a sortable tuple.

    Each entry is a dict shaped like the events.jsonl rows
    (``{"t": float, "kind": str, ...}``); the schema declares
    ``additionalProperties: true`` so v2.1 can grow the event row shape
    without versioning this wrapper.

    Fields:
        events: tuple of event dicts in chronological order. Each dict
            MUST have at least ``t`` (seconds from session start) and
            ``kind`` (event-type tag); both are required by the JSON
            schema.

    Tuple (not list) is required because ``@dataclass(frozen=True,
    slots=True)`` rejects unhashable defaults; serialization to JSON
    via ``messages._tuples_to_lists`` converts to array at write time.
    """

    events: tuple[dict, ...]
