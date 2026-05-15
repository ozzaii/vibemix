# SPDX-License-Identifier: Apache-2.0
"""Phase 28 — library-domain IPC payload structs.

Per RESEARCH §State of the Art + Open Q4: vibemix uses dataclasses +
jsonschema (NOT pydantic). TS codegen runs via ``npm run check:ipc`` from
``messages.schema.json``; pydantic-to-typescript is NOT used.

This module is the SINGLE source of payload field shapes for ``ipc.library.*``
messages. The wrapper classes in ``vibemix.ui_bus.messages`` import these
payloads. Frozen + slotted so the wrappers stay hashable; the
``_tuples_to_lists`` helper in ``messages.py`` flips tuples to lists at
serialise time (jsonschema's Draft-07 rejects tuples for ``type: array``).

Plan: 28-09. Schemas added in same plan to
``tauri/ui/src/ipc/messages.schema.json``.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LibraryImportPayload:
    """Plan 28-06 — renderer → sidecar. Trigger import on a Rekordbox XML.

    Fields:
        path: absolute path to the dropped XML file. Non-empty.
        schema_version: pinned to ``"1"``.
    """

    path: str
    schema_version: str = "1"


@dataclass(frozen=True, slots=True)
class LibraryImportProgressPayload:
    """Plan 28-06 — sidecar → renderer. Per-batch import progress.

    Fields:
        total: total track count in the XML.
        done: count of tracks embedded so far (including cache hits).
        current_track_name: human-readable label of the in-flight track
            (``"Artist — Title"``). Empty string when none yet.
        cache_hits: count of tracks served by the content-hash cache.
        cancelled: ``True`` on the final tick when the user pressed cancel.
    """

    total: int
    done: int
    current_track_name: str
    cache_hits: int
    cancelled: bool = False
    schema_version: str = "1"


@dataclass(frozen=True, slots=True)
class LibraryImportCancelPayload:
    """Plan 28-06 — renderer → sidecar. User pressed cancel during import."""

    schema_version: str = "1"


@dataclass(frozen=True, slots=True)
class LibrarySearchRequestPayload:
    """Plan 28-03 — renderer → sidecar. Natural-language vibe-search query."""

    query: str
    k: int = 10
    schema_version: str = "1"


@dataclass(frozen=True, slots=True)
class LibrarySearchResultPayload:
    """Plan 28-03 — sidecar → renderer. Vibe-search response.

    Fields:
        query: echo of the requested query string.
        matches: tuple of dicts with keys
            ``track_id, title, artist, bpm, confidence, snippet``.
        cache_hit: ``True`` when served from the 24h query cache.
    """

    query: str
    matches: tuple[dict, ...]
    cache_hit: bool
    schema_version: str = "1"


@dataclass(frozen=True, slots=True)
class LibraryConfidencePayload:
    """Plan 28-04 — sidecar → renderer. Grounding citation telemetry.

    Fields:
        track_id: cited track id (or ``None`` when below threshold).
        cosine: similarity in ``[-1, 1]``. Typically ``[0, 1]`` for matches.
        decision: ``"cited" | "uncertain" | "below_threshold"``.
        event_id: stable id of the event that fired the grounding lookup.
        cost_warning: ``True`` once monthly telemetry crosses 90% of the
            €50 ceiling (Plan 28-08 budget gate).
    """

    track_id: str | None
    cosine: float
    decision: str
    event_id: str
    cost_warning: bool = False
    schema_version: str = "1"


@dataclass(frozen=True, slots=True)
class LibraryStalenessNudgePayload:
    """Plan 28-07 — sidecar → renderer. 30-day re-import nudge.

    Fields:
        age_days: cache age in days since last import.
        snoozed_until_ts: epoch seconds when the snooze expires; ``None``
            when not snoozed.
    """

    age_days: int
    snoozed_until_ts: float | None
    schema_version: str = "1"


@dataclass(frozen=True, slots=True)
class LibraryStalenessActionPayload:
    """Plan 28-07 — renderer → sidecar. User dismissed or snoozed the nudge.

    Fields:
        action: ``"dismiss" | "snooze_7d"``.
    """

    action: str
    schema_version: str = "1"


@dataclass(frozen=True, slots=True)
class LibrarySimilarRequestPayload:
    """Plan 28-05 — renderer → sidecar. USER-ASKED similar-track query.

    Anti-feature guard: never autosurfaced (CONTEXT LIBRARY-14).
    """

    track_id: str
    k: int = 10
    schema_version: str = "1"


@dataclass(frozen=True, slots=True)
class LibrarySimilarResultPayload:
    """Plan 28-05 — sidecar → renderer. USER-ASKED similar-track results.

    Fields:
        track_id: echo of the seed track id.
        results: tuple of dicts with keys
            ``track_id, similarity, title, artist, bpm``.
    """

    track_id: str
    results: tuple[dict, ...]
    schema_version: str = "1"
