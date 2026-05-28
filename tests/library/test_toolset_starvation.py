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


# ---------------------------------------------------------------------------
# Plan 99-02 Task 1 — counter-update behavior in dispatch().
#
# These five tests pin Decisions 2 + 7 (CONTEXT.md):
#   * D-02: counter increments on (a) empty search_vibe results AND
#           (b) any handler returning {"error": ...}; resets on any
#           successful non-empty/non-error tool return.
#   * D-07: unit-tested against the toolset directly with fake
#           embedder / store / library, NO Codex install required.
#
# The threshold-trip / stop_reason write lands in Plan 99-03 — every
# scenario in this plan keeps the counter BELOW threshold so
# self.stop_reason remains None. The "monotonic_no_terminal_below_threshold"
# test pins that explicitly.
# ---------------------------------------------------------------------------


def _stub_empty_search(monkeypatch) -> None:
    """Make ``vibe_search`` return a zero-result tuple (the empty-search signal)."""

    def fake(emb, st, lib, query, k=15):
        return ([], False)

    monkeypatch.setattr(tool_mod, "vibe_search", fake)


def _stub_nonempty_search(monkeypatch, ids: list[str]) -> None:
    """Make ``vibe_search`` return ``ids`` as concrete results."""
    from types import SimpleNamespace

    def fake(emb, st, lib, query, k=15):
        return (
            [
                SimpleNamespace(
                    track_id=t, title=f"T{t}", artist="A", bpm=124.0, confidence=0.9
                )
                for t in ids
            ],
            False,
        )

    monkeypatch.setattr(tool_mod, "vibe_search", fake)


def test_empty_search_increments(toolset: LibraryToolset, monkeypatch) -> None:
    """D-02(a): empty ``search_vibe`` results increment the counter by 1.

    No terminal write below the threshold (Plan 99-03 lands that).
    """
    _stub_empty_search(monkeypatch)
    result = toolset.dispatch("search_vibe", {"query": "hypnotic", "k": 5})

    # Surface: empty results dict, byte-equivalent to pre-plan handler output.
    assert result == {"results": []}, (
        f"empty search must return {{'results': []}}; got {result!r}"
    )
    # Counter: incremented exactly once.
    assert toolset._consecutive_empties == 1, (
        f"empty search_vibe must increment counter to 1; got "
        f"{toolset._consecutive_empties!r}"
    )
    # No terminal yet — Plan 99-03 wires the trip.
    assert toolset.stop_reason is None, (
        f"counter below threshold must keep stop_reason None; got "
        f"{toolset.stop_reason!r}"
    )


def test_handler_error_increments(toolset: LibraryToolset) -> None:
    """D-02(b): any handler returning ``{"error": ...}`` increments the counter.

    ``get_track_features`` with an unknown track_id is the canonical error path
    (handler returns ``{"error": "unknown track_id ..."}``). The dispatch hook
    must recognize this AS an error-return and bump the counter.
    """
    out = toolset.dispatch("get_track_features", {"track_id": "NOT_IN_LIBRARY"})

    # Surface: error dict, byte-equivalent to pre-plan handler output.
    assert "error" in out, f"unknown track_id must return error dict; got {out!r}"
    # Counter: incremented exactly once.
    assert toolset._consecutive_empties == 1, (
        f"handler error must increment counter to 1; got "
        f"{toolset._consecutive_empties!r}"
    )
    # No terminal yet — Plan 99-03 wires the trip.
    assert toolset.stop_reason is None, (
        f"counter below threshold must keep stop_reason None; got "
        f"{toolset.stop_reason!r}"
    )


def test_counter_resets_on_success(toolset: LibraryToolset, monkeypatch) -> None:
    """D-02 reset clause: a successful non-empty tool return resets to 0.

    Sequence: empty search (counter=1) → non-empty search (counter=0).
    """
    # Step 1: empty search → counter = 1
    _stub_empty_search(monkeypatch)
    toolset.dispatch("search_vibe", {"query": "narrow theme"})
    assert toolset._consecutive_empties == 1, (
        f"after empty search counter must be 1; got "
        f"{toolset._consecutive_empties!r}"
    )

    # Step 2: non-empty search → counter resets to 0.
    _stub_nonempty_search(monkeypatch, ["t000", "t001"])
    out = toolset.dispatch("search_vibe", {"query": "broader theme"})
    assert "results" in out and len(out["results"]) == 2, (
        f"non-empty search must return 2 results; got {out!r}"
    )
    assert toolset._consecutive_empties == 0, (
        f"successful non-empty search must reset counter to 0; got "
        f"{toolset._consecutive_empties!r}"
    )
    assert toolset.stop_reason is None, (
        f"reset path must keep stop_reason None; got {toolset.stop_reason!r}"
    )


def test_counter_resets_after_partial_failures(
    toolset: LibraryToolset, monkeypatch
) -> None:
    """D-02 reset clause under a mixed sequence.

    Sequence: empty (0→1) → error (1→2) → success (2→0).
    Pins "consecutive" semantics: a single success wipes prior failures.
    """
    # Step 1: empty search → 1
    _stub_empty_search(monkeypatch)
    toolset.dispatch("search_vibe", {"query": "x"})
    assert toolset._consecutive_empties == 1

    # Step 2: handler error → 2
    out = toolset.dispatch("get_track_features", {"track_id": "STILL_UNKNOWN"})
    assert "error" in out
    assert toolset._consecutive_empties == 2, (
        f"error after empty must increment counter to 2; got "
        f"{toolset._consecutive_empties!r}"
    )

    # Step 3: successful non-empty search → 0 (the "consecutive" reset).
    _stub_nonempty_search(monkeypatch, ["t000"])
    toolset.dispatch("search_vibe", {"query": "broader"})
    assert toolset._consecutive_empties == 0, (
        f"successful non-empty after error must reset counter to 0; got "
        f"{toolset._consecutive_empties!r}"
    )
    assert toolset.stop_reason is None


def test_counter_monotonic_no_terminal_below_threshold(
    toolset: LibraryToolset, monkeypatch
) -> None:
    """Below threshold: counter strictly increments, no stop_reason write.

    Bumps the threshold to 4 (via monkeypatch on the module constant so the
    dispatch hook reads it fresh on each call — Pitfall 7) and fires 3 empties.
    Counter lands at 3; stop_reason stays None; every dispatch return value is
    byte-equivalent to the original handler output (no short-circuit).
    """
    monkeypatch.setattr(tool_mod, "TOOL_STARVATION_THRESHOLD", 4)
    _stub_empty_search(monkeypatch)

    expected: list[dict] = []
    for i in range(3):
        out = toolset.dispatch("search_vibe", {"query": f"narrow_{i}"})
        expected.append(out)

    # Counter at exactly 3 (threshold − 1).
    assert toolset._consecutive_empties == 3, (
        f"three empties must take counter to 3; got "
        f"{toolset._consecutive_empties!r}"
    )
    # No terminal write yet (Plan 99-03 lands the trip).
    assert toolset.stop_reason is None, (
        f"counter below threshold must keep stop_reason None; got "
        f"{toolset.stop_reason!r}"
    )
    # Each dispatch return value is the original handler result — byte-equivalent.
    assert all(out == {"results": []} for out in expected), (
        f"dispatch return values must be byte-equivalent to handler output; "
        f"got {expected!r}"
    )
