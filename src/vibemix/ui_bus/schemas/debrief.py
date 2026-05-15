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


# ---------------------------------------------------------------------------
# Phase 29 Plan 29-03 — DEBRIEF v2.1 additive wrappers (P82 lock baseline)
# ---------------------------------------------------------------------------
# These 6 payload structs are appended BELOW the 3 Phase 25 baselines.
# Phase 25 baselines are NEVER mutated (additive-only schema lock per
# pitfall P82). Future plans that need new debrief surface area must
# either extend optional fields on these structs OR add new structs
# below.


@dataclass(frozen=True, slots=True)
class ChapterRegionPayload:
    """One chapter region — used inside :class:`DebriefChapterListPayload`.

    Fields:
        id: stable identifier (e.g. "track-01", "phase-build-04:32").
        start: seconds from session start.
        end: seconds from session start; end >= start.
        label: human-visible label rendered in the sidebar.
        kind: one of ``track | phase | layer | mix | crowd``.
        citation_event_id: resolves against the EvidenceRegistry snapshot.
    """

    id: str
    start: float
    end: float
    label: str
    kind: str
    citation_event_id: str


@dataclass(frozen=True, slots=True)
class DebriefChapterListPayload:
    """Chapter list emitted after :func:`derive_chapters` runs.

    Fields:
        chapters: tuple of :class:`ChapterRegionPayload`.
        derived_at: ISO 8601 timestamp recording when derivation ran.
    """

    chapters: tuple[ChapterRegionPayload, ...]
    derived_at: str


@dataclass(frozen=True, slots=True)
class DebriefTldrAudioPayload:
    """TLDR MP3 metadata frame — emitted once the audio is on disk.

    The actual bytes live at ``<session>/debrief_tldr.mp3``; the renderer
    fetches via ``asset://`` (Tauri filesystem scope).

    Fields:
        audio_relative_path: filename relative to session_dir (e.g.
            "debrief_tldr.mp3").
        duration_s: MP3 decode duration in seconds (60-90 per DEBRIEF-04).
        tldr_sha256: hex SHA-256 of the MP3 bytes — cache key.
        mime_type: always ``"audio/mpeg"`` for v2.1 (MP3-only per P81).
    """

    audio_relative_path: str
    duration_s: float
    tldr_sha256: str
    mime_type: str


@dataclass(frozen=True, slots=True)
class DrillPayload:
    """Single SBI/STAR-AR drill row used inside :class:`DebriefDrillsPayload`.

    Fields:
        situation: descriptive context for the drill.
        behavior: what the DJ did (cited).
        impact: what happened audibly (cited).
        action_recommended: actionable next-time advice (cited).
        citation: a single canonical ``[ev:*] / [track:*] / [mix:*]`` tag
            that the renderer uses for the citation chip + tooltip.
    """

    situation: str
    behavior: str
    impact: str
    action_recommended: str
    citation: str


@dataclass(frozen=True, slots=True)
class DebriefDrillsPayload:
    """Exactly 3 drills — DEBRIEF-06 requires min=3, max=3."""

    drills: tuple[DrillPayload, ...]


@dataclass(frozen=True, slots=True)
class DebriefCitationTooltipReqPayload:
    """Renderer → sidecar: ask for the evidence behind a citation tag.

    Fields:
        event_id: the citation body (e.g. "DROP_HIT@01:23" or a
            ``source:key`` resolvable against the snapshot).
    """

    event_id: str


@dataclass(frozen=True, slots=True)
class DebriefCitationTooltipPayload:
    """Sidecar → renderer: evidence behind a citation tag.

    Fields:
        event_id: the originally requested id.
        evidence_text: short human-readable description.
        timestamp: seconds from session start; 0.0 when not resolvable.
        found: whether the snapshot resolved the id at ±2.0s tolerance.
    """

    event_id: str
    evidence_text: str
    timestamp: float
    found: bool


@dataclass(frozen=True, slots=True)
class DebriefErrorPayload:
    """Error envelope emitted by the debrief sidecar.

    Fields:
        reason: one of the allowlisted reason codes used by the renderer
            to map to user-facing copy (see Plan 29-05 ``error-banner``).
            Allowed values: ``events_missing | session_too_short |
            invalid_session_dir | sidecar_crashed | tldr_generation_failed
            | drills_generation_failed | port_in_use | unknown_kind``.
        message: free-form developer-readable detail (logged, not
            user-rendered verbatim).
    """

    reason: str
    message: str
