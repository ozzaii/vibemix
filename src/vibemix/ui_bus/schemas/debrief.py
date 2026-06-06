# SPDX-License-Identifier: Apache-2.0
"""Phase 25/29 — DEBRIEF IPC payload structs.

The shippable debrief surface only keeps payloads that have a real sidecar
producer and renderer consumer. The old ``citation-summary`` and
``event-timeline`` placeholders were pruned rather than carried as
schema-only reservations.

Schema sources match the established pattern from Plan 20-04 (citation)
and Plan 24-02 (overlay) — payload-only structs live here; wrapper
classes live in ``vibemix.ui_bus.messages``; the JSON schema definitions
mirror them in ``tauri/ui/src/ipc/messages.schema.json``.

Locked field names + types (count-parity-tested at
``scripts/check_ipc_schema.py``):

- ``DebriefSessionLoadedPayload``: ``session_id`` / ``started_at`` /
  ``duration_s``
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


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

# ---------------------------------------------------------------------------
# Phase 29 Plan 29-03 — DEBRIEF v2.1 additive wrappers (P82 lock baseline)
# ---------------------------------------------------------------------------
# Future plans that need new debrief surface area must either extend optional
# fields on these structs OR add new structs below.


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
class DebriefNearMissPayload:
    """One "Last Night, Heard" master-replay payload.

    Fields:
        input_wav_relative_path: filename relative to session_dir. The renderer
            resolves it through the existing recordings asset scope.
        t_center: near-miss center in session seconds. ``None`` means honest
            quiet/gap state, so there is no replay seek target.
        window: ``(start, end)`` session-second span for the audible recovery.
            ``None`` means no confident near-miss window.
        receipt_text: resolver-backed proof text for the card.
        friend_line_text: one human line that may be spoken/rendered.
        ear_test_clip_relative_path: optional WAV filename relative to
            session_dir containing only the detected replay window.
        friend_line_audio_relative_path: optional MP3 filename relative to
            session_dir when the local product voice rendered the line.
        duration_s: real set duration from events/input, not ``voice.wav``.
        waveform_peaks: optional ``[[low, mid, high], ...]`` master-input
            display peaks scaled 0..255. ``None`` means the recording could
            not be decoded, not that silence was proven.
    """

    input_wav_relative_path: str
    t_center: float | None
    window: tuple[float, float] | None
    receipt_text: str
    friend_line_text: str
    duration_s: float
    ear_test_clip_relative_path: str | None = None
    friend_line_audio_relative_path: str | None = None
    waveform_peaks: tuple[tuple[int, int, int], ...] | None = None


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
class LearnReferralPayload:
    """Optional authored Learn route attached to one debrief drill.

    Fields:
        lesson_id: canonical lesson id from ``vibemix.learn.curriculum``.
        course_id: owning course id from the same curriculum row.
        course_label: human-readable course label for compact UI context.
        skill_id: owning skill-wall id.
        skill_label: human-readable skill label.
        title: authored Learn lesson title.
        reason: deterministic explanation of why this drill maps there.
        cta: short button label.
    """

    lesson_id: str
    course_id: str
    course_label: str
    skill_id: str
    skill_label: str
    title: str
    reason: str
    cta: str


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
        learn_referral: optional deterministic route into authored Learn
            practice. ``None`` means this drill did not map confidently.
    """

    situation: str
    behavior: str
    impact: str
    action_recommended: str
    citation: str
    learn_referral: LearnReferralPayload | None = None


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
class DebriefMomentFeedbackPayload:
    """Renderer → sidecar: explicit feedback on one debrief moment.

    Fields:
        moment_id: stable renderer-side id for the card/control the user judged.
        citation_id: canonical citation tag/body attached to that moment.
        verdict: user's correction label.
        surface: coarse source surface for downstream analysis.
    """

    moment_id: str
    citation_id: str
    verdict: Literal["agree", "disagree", "unclear"]
    surface: Literal["transition", "live_pill", "cue"]


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
