# SPDX-License-Identifier: Apache-2.0
"""Phase 44 Plan 44-03 — cohost reaction broadcast IPC payload struct.

LAUNCH-02: every AI reaction the cohost agent emits to the user gets
mirrored to the live session UI as a structured envelope carrying the
reaction text, the LLM event tag, and the parsed ``citation_strip``.
The frontend (``tauri/ui/src/session/components/citation-strip.ts``)
renders the chip strip below the corresponding transcript line; clicking
a chip invokes the Tauri ``open_debrief_window`` command with a
``deep_link`` payload pointing at the chip's timestamp.

Schema-mirror counterpart: ``tauri/ui/src/ipc/messages.schema.json``
``definitions.SessionCohostReaction``.

This module is the SINGLE SOURCE for the payload field set; the wrapper
class (``vibemix.ui_bus.messages.SessionCohostReaction``) imports
``SessionCohostReactionPayload`` from here, matching the
``schemas/<domain>.py`` subpackage layout established by Plan 20-04
(citation) + Plan 24-02 (overlay).

Anti-slop note (LAUNCH-02 white-space §6.2): ``citation_strip`` is an
empty list — NEVER None — when no citation atom in the reaction text
resolves to a registry observation. Keeping the type stable lets the
TS consumer write a single rendering branch (``if (chips.length === 0)
return null``) instead of guarding against null at every site.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CitationChipPayload:
    """One chip entry in the ``citation_strip`` list.

    Fields:
        event_id: stable citation atom in source-prefixed form,
            e.g. ``"ev:KICK_SWAP@45.2"``. The debrief deep-link uses
            this as the timeline-region key. Range-bounded to keep
            arbitrary LLM-emitted payloads from blowing out the wire
            (1..128 chars).
        verb: 1-3 word lowercase label rendered as the chip text
            (e.g. ``"kick swap"``). Bounded to 32 chars so the chip
            never overruns the strip width.
        timestamp_s: session-relative time at which the cited event
            was observed by the registry, in seconds. Float so sub-
            second precision survives the wire (the chip displays
            ``mm:ss`` but click→debrief deep-link is precise).
    """

    event_id: str
    verb: str
    timestamp_s: float


@dataclass(frozen=True, slots=True)
class SessionCohostReactionPayload:
    """Payload struct for ``ipc.session.cohost-reaction``.

    Fields:
        text: the full reaction text the cohost emitted (post linter,
            post slop filter). May contain bracketed citation atoms
            verbatim — the UI does NOT strip them when rendering the
            transcript; the chips are an additive surface, not a
            replacement. Bounded to 2048 chars to refuse pathological
            payloads.
        event_id: the LLM event tag (``ev.type`` from the
            :class:`vibemix.state.Event` that triggered the reaction),
            e.g. ``"HEARTBEAT"``, ``"KAAN_SPOKE"``. Used as a stable
            id for the frontend's reaction-state ring (one entry per
            broadcast). The chip strip is keyed off this id so chips
            attach to the right reaction when transcripts diff.
        citation_strip: ordered list of resolved evidence chips. May
            be empty — never None. Capped at
            :const:`vibemix.agent.dj_cohost.CITATION_STRIP_MAX_CHIPS`
            (3) by the backend.
    """

    text: str
    event_id: str
    citation_strip: tuple[CitationChipPayload, ...]
