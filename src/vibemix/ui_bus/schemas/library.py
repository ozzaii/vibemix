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

Plan: 28-09. Import/staleness schemas are declared in
``tauri/ui/src/ipc/messages.schema.json``. Search/similar run through the
library Tauri command bridge, not the live ``ipc.*`` bus.
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
class LibraryStalenessNudgePayload:
    """Plan 28-07 — sidecar → renderer. 30-day re-import nudge.

    Fields:
        age_days: cache age in days since last import.
        snoozed_until_ts: epoch seconds when the snooze expires; ``None``
            when not snoozed.
        source_path: refreshable source path, when known.
        source_kind: ``"xml" | "folder"`` for the source_path, when known.
        reason: machine-readable freshness reason, when known.
    """

    age_days: int
    snoozed_until_ts: float | None
    source_path: str | None = None
    source_kind: str | None = None
    reason: str | None = None
    schema_version: str = "1"


@dataclass(frozen=True, slots=True)
class LibraryStalenessActionPayload:
    """Plan 28-07 — renderer → sidecar. User dismissed or snoozed the nudge.

    Fields:
        action: ``"dismiss" | "snooze_7d" | "reindex_folder"``.
    """

    action: str
    schema_version: str = "1"
