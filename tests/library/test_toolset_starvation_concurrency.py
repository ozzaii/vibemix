# SPDX-License-Identifier: Apache-2.0
"""Phase 99 HARDEN-RETRY — Plan 99-02 Task 1 concurrency acid test.

Pins the thread-safety claim from RESEARCH.md §Q7 (Pitfall 1): counter writes
live in ``dispatch()`` AFTER ``fut.result()`` returns to the dispatch-calling
thread — NEVER inside any handler body. ``toolset.py:407-411`` documents the
existing serialization guarantee that the lazy ``_genre_lookup`` init relies
on; the starvation counter rides the SAME guarantee.

The acid test: under ``N + 1`` parallel ``dispatch("search_vibe", ...)`` calls
with empty results, the final counter equals the total number of dispatch
calls (no lost updates / no double increments). A
``threading.Barrier(N + 1)`` releases every worker at the same instant to
maximize the race window.

This file is the ONLY home for concurrency tests; behavior tests live in
``test_toolset_starvation.py``.
"""

from __future__ import annotations

import threading
from unittest.mock import MagicMock

import pytest

from vibemix.library import toolset as tool_mod
from vibemix.library.rekordbox import RekordboxLibrary, TrackEntry
from vibemix.library.toolset import LibraryToolset


def _make_track(tid: str) -> TrackEntry:
    """Minimal track entry — mirrors the helper in test_toolset_starvation.py."""
    return TrackEntry(
        track_id=tid,
        title=f"Title {tid}",
        artist=f"Artist {tid}",
        album="A",
        bpm=124.0,
        key="8A",
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
def toolset(library: RekordboxLibrary) -> LibraryToolset:
    return LibraryToolset(MagicMock(), MagicMock(), library)


def test_monotonic_under_parallel_dispatch(
    toolset: LibraryToolset, monkeypatch
) -> None:
    """Counter is monotonic under N+1 parallel empty-search dispatches.

    Spawns ``N + 1`` worker threads (N = ``TOOL_STARVATION_THRESHOLD``); each
    calls ``toolset.dispatch("search_vibe", {"query": "x"})`` with a fake
    ``vibe_search`` returning ``([], False)``. A ``threading.Barrier`` releases
    all workers simultaneously so the race window is as wide as the GIL allows.

    After all workers join, ``toolset._consecutive_empties`` must equal
    ``N + 1`` — the exact number of dispatch calls — proving zero lost updates
    and zero double increments. This pins RESEARCH.md §Q7's claim that the
    dispatch-calling-thread write site is race-free by virtue of the existing
    serialization guarantee at ``toolset.py:407-411``.

    The threshold is bumped to ``N = 8`` so all ``N + 1 = 9`` workers complete
    without tripping the (currently un-wired in Plan 99-02) terminal short-
    circuit — keeping the assertion purely on counter monotonicity.
    """
    # Bump threshold high enough that none of our 9 parallel dispatches can
    # trip a (future) terminal short-circuit; Plan 99-02 does not write
    # stop_reason yet, so this is belt-and-suspenders for forward-compat
    # against Plan 99-03's wiring.
    monkeypatch.setattr(tool_mod, "TOOL_STARVATION_THRESHOLD", 100)

    # Fake vibe_search returns empty list — every dispatch is an empty-trigger.
    def fake_search(emb, st, lib, query, k=15):
        return ([], False)

    monkeypatch.setattr(tool_mod, "vibe_search", fake_search)

    n_workers = 9  # N + 1 with the bumped threshold (≥ 8 to maximize contention)
    barrier = threading.Barrier(n_workers)
    errors: list[BaseException] = []
    results: list[dict] = []
    results_lock = threading.Lock()

    def worker() -> None:
        try:
            barrier.wait(timeout=5.0)
            out = toolset.dispatch("search_vibe", {"query": "x"})
            with results_lock:
                results.append(out)
        except BaseException as e:  # noqa: BLE001 — surface to assert below
            errors.append(e)

    threads = [
        threading.Thread(target=worker, name=f"acid-{i}") for i in range(n_workers)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10.0)

    # No worker raised — dispatch is the no-raise contract.
    assert not errors, f"workers raised: {errors!r}"
    # Every worker completed and observed the empty-search result.
    assert len(results) == n_workers, (
        f"expected {n_workers} results, got {len(results)}; some workers stalled"
    )
    assert all(r == {"results": []} for r in results), (
        f"every dispatch must return the byte-equivalent empty-search result; "
        f"got {results!r}"
    )
    # The acid assertion: final counter == total dispatch calls.
    # No lost updates, no double increments.
    assert toolset._consecutive_empties == n_workers, (
        f"counter must equal total dispatch calls ({n_workers}) under parallel "
        f"contention; got {toolset._consecutive_empties!r} — this would indicate "
        f"either a lost update (counter < n) or a double increment (counter > n), "
        f"violating Pitfall 1 in RESEARCH.md §Common Pitfalls"
    )
