# SPDX-License-Identifier: Apache-2.0
"""vibemix.library — Rekordbox XML collection loader (Phase 25 Plan 25-02).

v2.0 ships the XML import path only. SQLCipher / db6 / Rekordbox6Database
paths in ``pyrekordbox`` are intentionally untouched per CONTEXT D-01 +
LIBRARY-07 — the dormancy gate in ``tests/library/test_pyrekordbox_install.py``
guards this commitment at CI time.

Public surface:
    ``from vibemix.library.rekordbox import RekordboxLibrary, TrackEntry, CuePoint``
"""

from vibemix.library.rekordbox import (
    CuePoint,
    RekordboxLibrary,
    TrackEntry,
)

__all__ = ["CuePoint", "RekordboxLibrary", "TrackEntry"]
