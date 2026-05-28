# SPDX-License-Identifier: Apache-2.0
"""Phase 99 HARDEN-RETRY — Plan 99-01 scaffolding tests.

These pin the pure-scaffolding contract of Plan 99-01:

* ``TOOL_STARVATION_THRESHOLD = 3`` exists at module scope in
  ``vibemix.library.toolset`` (per Decision 3, NON-NEGOTIABLE).
* ``LibraryToolset.__init__`` allocates ``self._consecutive_empties: int = 0``
  and ``self.stop_reason: dict | None = None`` (per Decisions 1 and 4).

Plan 99-01 is *pure scaffolding* — no behavior change in ``dispatch()`` yet.
The dispatch hook and threshold-trip logic land in Plans 99-02 / 99-03; the
cross-process side-channel lands in Plan 99-04; the AST/grep single-writer
gate lands in Plan 99-05. This test file is the per-phase append target —
future plans extend it; do not delete existing tests.

Fixture posture mirrors ``tests/library/test_toolset.py:148-170`` (fake
``library`` / ``embedder`` / ``store``). We re-define the minimal subset
locally instead of cross-importing — pytest convention, and it keeps
single-source ownership of each fixture inside its own file.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from vibemix.library import toolset as tool_mod
from vibemix.library.rekordbox import RekordboxLibrary, TrackEntry
from vibemix.library.toolset import LibraryToolset


def _make_track(tid: str, bpm: float = 124.0, key: str = "8A") -> TrackEntry:
    """Minimal track entry — mirrors the canonical helper in test_toolset.py."""
    return TrackEntry(
        track_id=tid,
        title=f"Title {tid}",
        artist=f"Artist {tid}",
        album="A",
        bpm=bpm,
        key=key,
        duration_s=300.0,
        cues=(),
        filepath=f"/tmp/{tid}.mp3",
    )


@pytest.fixture
def library() -> RekordboxLibrary:
    lib = RekordboxLibrary()
    lib.tracks = {f"t{i:03d}": _make_track(f"t{i:03d}") for i in range(5)}
    return lib


@pytest.fixture
def toolset(library) -> LibraryToolset:
    return LibraryToolset(MagicMock(), MagicMock(), library)


def test_threshold_constant_present() -> None:
    """Decision 3 — module-level ``TOOL_STARVATION_THRESHOLD = 3`` (int)."""
    assert hasattr(tool_mod, "TOOL_STARVATION_THRESHOLD"), (
        "TOOL_STARVATION_THRESHOLD must be defined at module scope in "
        "vibemix.library.toolset (Phase 99 Decision 3, threshold=3)."
    )
    value = tool_mod.TOOL_STARVATION_THRESHOLD
    assert isinstance(value, int), (
        f"TOOL_STARVATION_THRESHOLD must be an int; got {type(value).__name__}"
    )
    assert value == 3, (
        f"TOOL_STARVATION_THRESHOLD must equal 3 (Decision 3 locked); got {value}"
    )


def test_counter_initial_zero(toolset: LibraryToolset) -> None:
    """Decision 1 — ``self._consecutive_empties`` starts at 0 on a fresh instance."""
    assert hasattr(toolset, "_consecutive_empties"), (
        "LibraryToolset.__init__ must allocate self._consecutive_empties "
        "(Phase 99 Decision 1, per-instance counter)."
    )
    assert toolset._consecutive_empties == 0, (
        f"_consecutive_empties must start at 0; got {toolset._consecutive_empties!r}"
    )
    assert isinstance(toolset._consecutive_empties, int), (
        "_consecutive_empties must be an int (Phase 99 scaffolding contract)."
    )


def test_stop_reason_initial_none(toolset: LibraryToolset) -> None:
    """Decision 4 — ``self.stop_reason`` starts as None on a fresh instance."""
    assert hasattr(toolset, "stop_reason"), (
        "LibraryToolset.__init__ must allocate self.stop_reason "
        "(Phase 99 Decision 4, parallel to self.created / self.exported)."
    )
    assert toolset.stop_reason is None, (
        f"stop_reason must start as None; got {toolset.stop_reason!r}"
    )
