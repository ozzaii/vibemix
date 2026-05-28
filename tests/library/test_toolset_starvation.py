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


# ---------------------------------------------------------------------------
# Plan 99-03 Task 1 — threshold-trip + three-case hint + terminal idempotence.
#
# These seven tests pin Decisions 3 + 4 + 5 + RESEARCH.md Open Q2:
#   * D-03: threshold = ``tool_mod.TOOL_STARVATION_THRESHOLD`` (module attr
#           lookup so monkeypatch tunes runtime behavior — Pitfall 7).
#   * D-04: terminal write to ``self.stop_reason`` with the payload shape
#           ``{"reason": "tool_starvation", "hint": <str>, "tool": <str>,
#             "consecutive": <int>}``. Idempotent — only the first trip writes.
#   * D-05: deterministic three-case hint. Case A (zero-track library) /
#           Case B (no theme matches) / Case C (repeated tool error).
#           Tests pin SUBSTRINGS of key phrases ("library has 0 tracks",
#           "no tracks matched", "kept failing") so KAAN-ACTION
#           §HARDEN-PHASE-A-EAR-PASS can polish wording without breaking tests.
#   * RESEARCH Q2: after trip, subsequent ``dispatch()`` calls become
#           idempotent no-ops returning ``{"error": "tool_starvation",
#           "stop_reason": dict(self.stop_reason)}`` — handler NOT invoked.
# ---------------------------------------------------------------------------


def test_threshold_trip_sets_stop_reason(
    toolset: LibraryToolset, monkeypatch
) -> None:
    """D-03 + D-04: 3 consecutive empty ``search_vibe`` writes ``stop_reason``.

    The library has 5 tracks (per fixture) so case A (zero-track) does NOT
    fire — Case B (no theme matches) is the expected hint case. The trip
    payload shape must include all four required keys.
    """
    _stub_empty_search(monkeypatch)
    for _ in range(3):
        toolset.dispatch("search_vibe", {"query": "narrow theme"})

    assert toolset.stop_reason is not None, (
        "3 empty search_vibe calls must trip the threshold and write "
        "self.stop_reason (D-04). Got None — threshold-trip not wired."
    )
    payload = toolset.stop_reason
    assert payload["reason"] == "tool_starvation", (
        f'payload["reason"] must equal "tool_starvation"; got {payload["reason"]!r}'
    )
    assert payload["tool"] == "search_vibe", (
        f'payload["tool"] must record the last-dispatched tool name; '
        f"got {payload['tool']!r}"
    )
    assert payload["consecutive"] == 3, (
        f'payload["consecutive"] must equal the counter at trip time (3); '
        f"got {payload['consecutive']!r}"
    )
    assert isinstance(payload.get("hint"), str) and payload["hint"], (
        f"payload['hint'] must be a non-empty string; got {payload.get('hint')!r}"
    )


def test_threshold_is_tunable(toolset: LibraryToolset, monkeypatch) -> None:
    """Pitfall 7: ``monkeypatch.setattr(tool_mod, "TOOL_STARVATION_THRESHOLD", 2)``
    actually changes runtime behavior. After 2 empty searches the trip MUST fire.

    If this test fails, the dispatch hook is reading a captured-at-import copy
    of the constant — fix by switching to module-attribute lookup (Pitfall 7).
    """
    monkeypatch.setattr(tool_mod, "TOOL_STARVATION_THRESHOLD", 2)
    _stub_empty_search(monkeypatch)

    toolset.dispatch("search_vibe", {"query": "x"})
    assert toolset.stop_reason is None, (
        "after only 1 empty search, threshold (=2) is not yet hit — "
        f"stop_reason must stay None; got {toolset.stop_reason!r}"
    )
    toolset.dispatch("search_vibe", {"query": "x"})
    assert toolset.stop_reason is not None, (
        "with threshold=2, the second empty search must trip the terminal "
        "write. If stop_reason is still None, the dispatch hook is NOT "
        "reading tool_mod.TOOL_STARVATION_THRESHOLD via the module "
        "attribute (Pitfall 7 — captured-at-import constant). Switch to "
        "sys.modules[__name__].TOOL_STARVATION_THRESHOLD."
    )
    assert toolset.stop_reason["consecutive"] == 2, (
        f'consecutive must equal threshold at trip time (2); '
        f"got {toolset.stop_reason['consecutive']!r}"
    )


def test_hint_zero_track_library(monkeypatch) -> None:
    """D-05 Case A: zero-track library → hint mentions ingest.

    Substring match (not full-string equality) so KAAN-ACTION ear-pass can
    polish wording without breaking the test.
    """
    empty_lib = RekordboxLibrary()
    empty_lib.tracks = {}
    ts = LibraryToolset(MagicMock(), MagicMock(), empty_lib)
    _stub_empty_search(monkeypatch)

    for _ in range(3):
        ts.dispatch("search_vibe", {"query": "anything"})

    assert ts.stop_reason is not None, (
        "3 empties on an empty-library toolset must trip; got None"
    )
    hint = ts.stop_reason["hint"]
    assert "library has 0 tracks" in hint, (
        f'Case A hint must contain "library has 0 tracks" — D-05 seed '
        f"copy. Substring match (ear-pass tolerant). Got: {hint!r}"
    )
    assert "library ingest" in hint, (
        f'Case A hint must contain "library ingest" — D-05 seed copy '
        f"names the action user should take. Got: {hint!r}"
    )


def test_hint_no_theme_match(toolset: LibraryToolset, monkeypatch) -> None:
    """D-05 Case B: library has tracks, search_vibe empty → hint mentions theme + BPM.

    Substring match on key phrases ("no tracks matched", the theme string,
    "BPM"). Tests STRUCTURE not exact wording (D-05 ear-pass tolerance).
    """
    _stub_empty_search(monkeypatch)
    theme = "uplifting 200 BPM ambient"
    for _ in range(3):
        toolset.dispatch("search_vibe", {"query": theme})

    assert toolset.stop_reason is not None
    hint = toolset.stop_reason["hint"]
    assert "no tracks matched" in hint, (
        f'Case B hint must contain "no tracks matched". Got: {hint!r}'
    )
    assert f"'{theme}'" in hint, (
        f'Case B hint must interpolate the theme as a single-quoted string '
        f"(matches D-05 seed copy). Theme={theme!r}, hint={hint!r}"
    )
    assert "BPM" in hint, (
        f'Case B hint should mention BPM (seed copy: "...try a broader '
        f'theme or different BPM range"). Got: {hint!r}'
    )


def test_hint_tool_error(toolset: LibraryToolset) -> None:
    """D-05 Case C: 3 consecutive ``get_track_features`` errors → tool-error hint.

    Library has 5 tracks (so case A doesn't fire); last tool is NOT
    ``search_vibe`` (so case B doesn't fire). Case C is the expected branch.
    """
    for _ in range(3):
        out = toolset.dispatch(
            "get_track_features", {"track_id": "STILL_NOT_THERE"}
        )
        assert "error" in out

    assert toolset.stop_reason is not None, (
        "3 consecutive handler errors must trip the threshold; got None"
    )
    hint = toolset.stop_reason["hint"]
    assert "tool 'get_track_features'" in hint, (
        f'Case C hint must contain "tool \'get_track_features\'" — names '
        f"the offending tool. Got: {hint!r}"
    )
    assert "kept failing" in hint, (
        f'Case C hint must contain "kept failing" — D-05 seed copy. '
        f"Got: {hint!r}"
    )
    assert toolset.stop_reason["tool"] == "get_track_features"


def test_terminal_idempotence_after_starvation(
    toolset: LibraryToolset, monkeypatch
) -> None:
    """After trip, subsequent dispatch calls return idempotent terminal echo.

    Counter is FROZEN at threshold (does NOT advance past it because the
    top-of-dispatch short-circuit returns BEFORE the counter hook).
    """
    _stub_empty_search(monkeypatch)
    for _ in range(3):
        toolset.dispatch("search_vibe", {"query": "narrow"})

    assert toolset.stop_reason is not None
    snapshot = dict(toolset.stop_reason)
    counter_at_trip = toolset._consecutive_empties

    # Fire another dispatch — must echo the same terminal payload.
    echo_1 = toolset.dispatch("search_vibe", {"query": "still narrow"})
    assert echo_1 == {
        "error": "tool_starvation",
        "stop_reason": snapshot,
    }, (
        f"post-trip dispatch must return idempotent terminal echo "
        f"{{'error': 'tool_starvation', 'stop_reason': <copy>}}; "
        f"got {echo_1!r}"
    )

    # Counter is FROZEN — does NOT advance past threshold.
    assert toolset._consecutive_empties == counter_at_trip, (
        f"counter must be frozen at threshold after trip; counter_at_trip="
        f"{counter_at_trip!r}, now={toolset._consecutive_empties!r}"
    )

    # Try a different tool — same terminal echo. stop_reason unchanged.
    echo_2 = toolset.dispatch("get_track_features", {"track_id": "t000"})
    assert echo_2 == {
        "error": "tool_starvation",
        "stop_reason": snapshot,
    }, (
        f"post-trip dispatch of a different tool must STILL return the "
        f"terminal echo (run is terminal); got {echo_2!r}"
    )
    assert toolset.stop_reason == snapshot, (
        "stop_reason payload must not mutate after trip — idempotent write."
    )

    # The echo's stop_reason must be a SHALLOW COPY (mutating it must not
    # affect the toolset's internal payload). Per RESEARCH.md Open Q2.
    echo_2["stop_reason"]["reason"] = "tampered"
    assert toolset.stop_reason["reason"] == "tool_starvation", (
        f"echo[stop_reason] must be a shallow copy — mutating the caller's "
        f"copy must not corrupt internal state. Got: "
        f"{toolset.stop_reason['reason']!r}"
    )


def test_starvation_short_circuits_subsequent_dispatch(
    toolset: LibraryToolset, monkeypatch
) -> None:
    """After trip, the handler is NOT invoked on subsequent dispatch calls.

    Proves the short-circuit lives at the TOP of dispatch(), BEFORE the
    ``ThreadPoolExecutor`` block. If the handler ran, it would raise — the
    short-circuit catches it first.
    """
    _stub_empty_search(monkeypatch)
    for _ in range(3):
        toolset.dispatch("search_vibe", {"query": "narrow"})

    assert toolset.stop_reason is not None

    # Replace search_vibe with a sentinel that raises if invoked.
    def explode(args):  # pragma: no cover — must NOT run
        raise RuntimeError("handler should not run after starvation trip")

    monkeypatch.setattr(toolset, "search_vibe", explode)

    # If the short-circuit fires correctly, NO exception bubbles AND we get
    # the terminal echo. If the short-circuit is below the handler dispatch,
    # the explode handler would either crash (raising or being caught as
    # ``{"error": "tool 'search_vibe' crashed: RuntimeError"}``) instead of
    # returning the terminal echo.
    echo = toolset.dispatch("search_vibe", {"query": "anything"})
    assert echo == {
        "error": "tool_starvation",
        "stop_reason": dict(toolset.stop_reason),
    }, (
        f"short-circuit must return terminal echo WITHOUT invoking handler; "
        f"got {echo!r}. If the result is a crash dict, the short-circuit "
        f"lives BELOW handler dispatch — move it to the top of dispatch()."
    )
