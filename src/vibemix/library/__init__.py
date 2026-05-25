# SPDX-License-Identifier: Apache-2.0
"""vibemix.library — Rekordbox XML collection loader (Phase 25 Plan 25-02).

v2.0 ships the XML import path only. SQLCipher / db6 / Rekordbox6Database
paths in ``pyrekordbox`` are intentionally untouched per CONTEXT D-01 +
LIBRARY-07 — the dormancy gate in ``tests/library/test_pyrekordbox_install.py``
guards this commitment at CI time.

Public surface:
    ``from vibemix.library.rekordbox import RekordboxLibrary, TrackEntry, CuePoint``
"""

from vibemix.library._cosine import EMBEDDING_DIM, cosine_topk, l2_normalize
from vibemix.library.embed import (
    CUE_ANCHORED_STRATEGY_VERSION,
    DEFAULT_EMBED_STRATEGY,
    EMBED_STRATEGIES,
    EXCERPT_STRATEGY_VERSION,
    GEMINI_EMBEDDING_MODEL,
    LibraryEmbedder,
)
from vibemix.library.cue_detect import detect_cues
from vibemix.library.index_numpy import NumpyStore
from vibemix.library.rekordbox import (
    CuePoint,
    RekordboxLibrary,
    TrackEntry,
)
from vibemix.library.grounding import (
    CITATION_THRESHOLD,
    TRACK_AWARE_EVENTS,
    UNCERTAIN_THRESHOLD,
    Citation,
    Grounding,
    identify_playing,
)
from vibemix.library.budget import (
    BUDGET_CEILING_EUR,
    BudgetTelemetry,
    CostProjection,
    get_telemetry,
    project_monthly_cost,
)
from vibemix.library.folder_ingest import (
    SUPPORTED_SUFFIXES,
    IngestReport,
    folder_to_track_entry,
    ingest_folder,
    probe_duration_s,
    scan_folder,
)
from vibemix.library.search import (
    QUERY_CACHE_TTL,
    VibeSearchResult,
    vibe_search,
)
from vibemix.library.similar import SimilarResult, similar_to
from vibemix.library.staleness import (
    SNOOZE_DURATION_SECONDS,
    STALE_AGE_SECONDS,
    apply_snooze_action,
    emit_nudge_if_stale,
    is_snoozed,
    is_stale,
)
from vibemix.library.store import LibraryStore, open_store, snapshot_hash

__all__ = [
    "BUDGET_CEILING_EUR",
    "BudgetTelemetry",
    "CITATION_THRESHOLD",
    "CUE_ANCHORED_STRATEGY_VERSION",
    "Citation",
    "CostProjection",
    "CuePoint",
    "DEFAULT_EMBED_STRATEGY",
    "EMBED_STRATEGIES",
    "EMBEDDING_DIM",
    "EXCERPT_STRATEGY_VERSION",
    "detect_cues",
    "GEMINI_EMBEDDING_MODEL",
    "Grounding",
    "IngestReport",
    "SUPPORTED_SUFFIXES",
    "folder_to_track_entry",
    "ingest_folder",
    "probe_duration_s",
    "scan_folder",
    "LibraryEmbedder",
    "LibraryStore",
    "NumpyStore",
    "QUERY_CACHE_TTL",
    "RekordboxLibrary",
    "SNOOZE_DURATION_SECONDS",
    "STALE_AGE_SECONDS",
    "SimilarResult",
    "TRACK_AWARE_EVENTS",
    "TrackEntry",
    "UNCERTAIN_THRESHOLD",
    "VibeSearchResult",
    "apply_snooze_action",
    "cosine_topk",
    "emit_nudge_if_stale",
    "identify_playing",
    "is_snoozed",
    "is_stale",
    "l2_normalize",
    "get_telemetry",
    "open_store",
    "project_monthly_cost",
    "similar_to",
    "snapshot_hash",
    "vibe_search",
]
