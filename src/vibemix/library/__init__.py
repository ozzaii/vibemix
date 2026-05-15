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
    EXCERPT_STRATEGY_VERSION,
    GEMINI_EMBEDDING_MODEL,
    LibraryEmbedder,
)
from vibemix.library.index_numpy import NumpyStore
from vibemix.library.rekordbox import (
    CuePoint,
    RekordboxLibrary,
    TrackEntry,
)
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
    "CuePoint",
    "EMBEDDING_DIM",
    "EXCERPT_STRATEGY_VERSION",
    "GEMINI_EMBEDDING_MODEL",
    "LibraryEmbedder",
    "LibraryStore",
    "NumpyStore",
    "RekordboxLibrary",
    "SNOOZE_DURATION_SECONDS",
    "STALE_AGE_SECONDS",
    "TrackEntry",
    "apply_snooze_action",
    "cosine_topk",
    "emit_nudge_if_stale",
    "is_snoozed",
    "is_stale",
    "l2_normalize",
    "open_store",
    "snapshot_hash",
]
