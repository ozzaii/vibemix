# SPDX-License-Identifier: Apache-2.0
"""vibemix.library public exports.

Keep this package import-light. Several shipped paths import submodules such as
``vibemix.library.mcp_server`` only to run local CLAP/Codex tools; importing the
package must not eagerly load the legacy Gemini embedder, model SDKs, or
optional local-model runtimes. The retired Gemini embedder remains importable
from ``vibemix.library.embed`` for legacy cache tests, but it is no longer a
package-level public export.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

_EXPORTS: dict[str, tuple[str, str]] = {
    "BUDGET_CEILING_EUR": ("vibemix.library.budget", "BUDGET_CEILING_EUR"),
    "CITATION_THRESHOLD": ("vibemix.library.grounding", "CITATION_THRESHOLD"),
    "CUE_ANCHORED_STRATEGY_VERSION": (
        "vibemix.library.embed_config",
        "CUE_ANCHORED_STRATEGY_VERSION",
    ),
    "DEFAULT_EMBED_STRATEGY": (
        "vibemix.library.embed_config",
        "DEFAULT_EMBED_STRATEGY",
    ),
    "EMBEDDING_DIM": ("vibemix.library._cosine", "EMBEDDING_DIM"),
    "EMBED_STRATEGIES": ("vibemix.library.embed_config", "EMBED_STRATEGIES"),
    "PLAYLISTS_DIR": ("vibemix.library.create_playlist", "PLAYLISTS_DIR"),
    "QUERY_CACHE_TTL": ("vibemix.library.search", "QUERY_CACHE_TTL"),
    "SNOOZE_DURATION_SECONDS": (
        "vibemix.library.staleness",
        "SNOOZE_DURATION_SECONDS",
    ),
    "STALE_AGE_SECONDS": ("vibemix.library.staleness", "STALE_AGE_SECONDS"),
    "SUPPORTED_SUFFIXES": ("vibemix.library.folder_ingest", "SUPPORTED_SUFFIXES"),
    "TRACK_AWARE_EVENTS": ("vibemix.library.grounding", "TRACK_AWARE_EVENTS"),
    "UNCERTAIN_THRESHOLD": ("vibemix.library.grounding", "UNCERTAIN_THRESHOLD"),
    "BudgetTelemetry": ("vibemix.library.budget", "BudgetTelemetry"),
    "Citation": ("vibemix.library.grounding", "Citation"),
    "CostProjection": ("vibemix.library.budget", "CostProjection"),
    "CueAnchor": ("vibemix.library.cue_types", "CueAnchor"),
    "CuePoint": ("vibemix.library.rekordbox", "CuePoint"),
    "Grounding": ("vibemix.library.grounding", "Grounding"),
    "IngestReport": ("vibemix.library.folder_ingest", "IngestReport"),
    "LibraryStore": ("vibemix.library.store", "LibraryStore"),
    "NumpyStore": ("vibemix.library.index_numpy", "NumpyStore"),
    "PlaylistResult": ("vibemix.library.create_playlist", "PlaylistResult"),
    "RekordboxLibrary": ("vibemix.library.rekordbox", "RekordboxLibrary"),
    "SimilarResult": ("vibemix.library.similar", "SimilarResult"),
    "TrackEntry": ("vibemix.library.rekordbox", "TrackEntry"),
    "VibeSearchResult": ("vibemix.library.search", "VibeSearchResult"),
    "apply_snooze_action": ("vibemix.library.staleness", "apply_snooze_action"),
    "build_embedder": ("vibemix.library.embed_factory", "build_embedder"),
    "cosine_topk": ("vibemix.library._cosine", "cosine_topk"),
    "create_playlist": ("vibemix.library.create_playlist", "create_playlist"),
    "detect_cues": ("vibemix.library.cue_detect", "detect_cues"),
    "detect_cues_auto": ("vibemix.library.cue_engine", "detect_cues_auto"),
    "emit_nudge_if_stale": ("vibemix.library.staleness", "emit_nudge_if_stale"),
    "folder_to_track_entry": ("vibemix.library.folder_ingest", "folder_to_track_entry"),
    "get_telemetry": ("vibemix.library.budget", "get_telemetry"),
    "identify_playing": ("vibemix.library.grounding", "identify_playing"),
    "ingest_folder": ("vibemix.library.folder_ingest", "ingest_folder"),
    "is_snoozed": ("vibemix.library.staleness", "is_snoozed"),
    "is_stale": ("vibemix.library.staleness", "is_stale"),
    "l2_normalize": ("vibemix.library._cosine", "l2_normalize"),
    "open_store": ("vibemix.library.store", "open_store"),
    "probe_duration_s": ("vibemix.library.folder_ingest", "probe_duration_s"),
    "project_monthly_cost": ("vibemix.library.budget", "project_monthly_cost"),
    "scan_folder": ("vibemix.library.folder_ingest", "scan_folder"),
    "similar_to": ("vibemix.library.similar", "similar_to"),
    "snapshot_hash": ("vibemix.library.store", "snapshot_hash"),
    "vibe_search": ("vibemix.library.search", "vibe_search"),
}

__all__ = sorted(_EXPORTS)


def __getattr__(name: str) -> Any:
    try:
        module_name, attr_name = _EXPORTS[name]
    except KeyError as exc:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc
    value = getattr(import_module(module_name), attr_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted({*globals(), *__all__})
