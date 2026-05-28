# SPDX-License-Identifier: Apache-2.0
"""Phase 94 Plan 03 — L1.14 ExemplarLessonController tests (TDD RED → GREEN).

The controller is an OBSERVER of LessonRuntime — it consumes the runtime
+ ExemplarFinder + ExemplarPlayer + ipc emit seam, but NEVER writes
LearnState (Invariant #1 stays bound to LessonRuntime alone; the AST gate
``tests/learn/test_runtime_invariants.py`` greps for forbidden writes).

Five tests:

  1. ``.start()`` reads ``exemplar_cycle[0]`` → emits
     ``ipc.learn.exemplar_play`` (with the picked track_id) +
     ``ipc.learn.tutor_speak`` (carrying the ``[exemplar:<track_id>]``
     citation atom) for the FIRST band.

  2. ``.ack()`` while the first band is active stops the active pick
     (``ipc.learn.exemplar_stop``) and advances to band 2
     (``ipc.learn.exemplar_play`` for the second band's pick).

  3. After all 3 bands cycle (3 ack()s), the controller emits
     ``ipc.learn.complete_lesson`` and stops the player.

  4. When ``ExemplarFinder.find()`` returns ``[]`` (degraded install —
     neither library nor packaged bank has audio), the controller emits
     a honest-null ``ipc.learn.tutor_speak`` with NO citation (no
     fabricated ``[exemplar:_packaged:<band>:null]`` atom), the cycle
     still advances on user MIDI, and the lesson completes after all 3
     bands regardless.

  5. ``.stop()`` is idempotent — safe from any state; emits a final
     ``ipc.learn.exemplar_stop`` if a pick was active; never raises.

REQ-ID: CURR-1.14 (EQ-as-Tutor marquee demo backend).
"""
from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

try:
    from vibemix.learn.exemplar import ExemplarPick  # P93-04
    from vibemix.learn.exemplar_lesson import ExemplarLessonController  # Plan 94-03
except ImportError:
    pytest.skip(
        "tests/learn/test_exemplar_lesson.py awaiting Plan 94-03 "
        "(ExemplarLessonController in src/vibemix/learn/exemplar_lesson.py). "
        "When the module lands, this module-level skip flips to live "
        "assertions.",
        allow_module_level=True,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_script() -> dict[str, Any]:
    """Build an in-line L1.14-shaped script with 3 exemplar_cycle entries.

    Mirrors the verbatim shape of
    ``src/vibemix/learn/transcripts/course_1_anatomy/14_eq_as_tutor.json``
    but stays hermetic (no filesystem read).
    """
    return {
        "lesson_id": "L1.14",
        "exemplar_cycle": [
            {
                "band": "low",
                "expected_action": {
                    "type": "cc",
                    "control": "eq_low",
                    "deck": "A",
                    "min_delta": 80,
                },
                "tutor_speak": (
                    "i picked a low-heavy track from your library. turn "
                    "deck A's low EQ knob and listen to the bass swell."
                ),
            },
            {
                "band": "mid",
                "expected_action": {
                    "type": "cc",
                    "control": "eq_mid",
                    "deck": "A",
                    "min_delta": 80,
                },
                "tutor_speak": (
                    "now a mid-heavy track. turn deck A's mid EQ knob "
                    "and listen to the vocals move."
                ),
            },
            {
                "band": "high",
                "expected_action": {
                    "type": "cc",
                    "control": "eq_hi",
                    "deck": "A",
                    "min_delta": 80,
                },
                "tutor_speak": (
                    "and a high-heavy track. turn deck A's high EQ knob "
                    "and listen to the shimmer change."
                ),
            },
        ],
    }


def _make_pick(band: str, idx: int = 0) -> ExemplarPick:
    """Build a synthetic ExemplarPick for a band. ``library:<band>:<idx>``
    is a deliberately invalid library prefix to avoid colliding with real
    ingested track ids — the test only cares about the citation atom
    round-trip, not real library resolution.
    """
    return ExemplarPick(
        track_id=f"library:{band}:{idx}",
        file_path=f"/tmp/synthetic-{band}.wav",
        band_score=0.55,
        reason=f"from your library — strongest {band}-band track",
    )


def _emitted_types(emitted: list[dict]) -> list[str]:
    """Return the ``type`` field of every captured envelope dict in order."""
    return [env["type"] for env in emitted]


# ---------------------------------------------------------------------------
# Test 1 — start() emits play + speak (with citation) for the first band
# ---------------------------------------------------------------------------


def test_start_emits_play_and_speak_with_citation_for_first_band() -> None:
    finder = MagicMock(name="finder")
    finder.find.side_effect = [
        [_make_pick("low")],
        [_make_pick("mid")],
        [_make_pick("high")],
    ]
    player = MagicMock(name="player")
    emitted: list[dict] = []
    controller = ExemplarLessonController(
        finder=finder,
        player=player,
        ipc_emit=emitted.append,
    )
    controller.start(script=_make_script(), lesson_id="L1.14")

    types = _emitted_types(emitted)
    assert "ipc.learn.exemplar_play" in types, (
        f"controller.start() must emit exemplar_play for band 0; saw {types!r}"
    )
    assert "ipc.learn.tutor_speak" in types, (
        f"controller.start() must emit tutor_speak for band 0; saw {types!r}"
    )

    # Pull the first exemplar_play + tutor_speak envelopes.
    play = next(e for e in emitted if e["type"] == "ipc.learn.exemplar_play")
    speak = next(e for e in emitted if e["type"] == "ipc.learn.tutor_speak")

    # The pick's track_id is on the wire.
    assert play["payload"]["track_id"] == "library:low:0", (
        f"exemplar_play.track_id must be the finder's pick; got {play['payload']['track_id']!r}"
    )

    # The tutor_speak citation contains the [exemplar:<track_id>] atom —
    # Invariant #2 binding. ExemplarFinder.find() pre-registered the pick
    # in EvidenceRegistry; the controller is responsible for emitting a
    # citation that resolves through that registration.
    citations = speak["payload"]["citations"]
    assert any("[exemplar:library:low:0]" == c for c in citations), (
        f"tutor_speak.citations must include the exemplar atom for the "
        f"picked track_id; got citations={citations!r}"
    )

    # Player.play() was called with the pick's file_path.
    player.play.assert_called_once_with("/tmp/synthetic-low.wav")


# ---------------------------------------------------------------------------
# Test 2 — ack() advances to the next band (stop + play sequence)
# ---------------------------------------------------------------------------


def test_ack_advances_to_next_band_emitting_stop_then_play() -> None:
    finder = MagicMock(name="finder")
    finder.find.side_effect = [
        [_make_pick("low")],
        [_make_pick("mid")],
        [_make_pick("high")],
    ]
    player = MagicMock(name="player")
    emitted: list[dict] = []
    controller = ExemplarLessonController(
        finder=finder,
        player=player,
        ipc_emit=emitted.append,
    )
    controller.start(script=_make_script(), lesson_id="L1.14")

    # Snapshot length so we measure the post-ack delta only.
    initial_count = len(emitted)
    controller.ack(lesson_id="L1.14")

    new_emits = emitted[initial_count:]
    new_types = _emitted_types(new_emits)
    # The advance sequence must include both stop (for the prior pick)
    # AND play (for the next pick).
    assert "ipc.learn.exemplar_stop" in new_types, (
        f"ack() must emit exemplar_stop for the prior pick; saw {new_types!r}"
    )
    assert "ipc.learn.exemplar_play" in new_types, (
        f"ack() must emit exemplar_play for the next pick; saw {new_types!r}"
    )

    # exemplar_stop carries the prior pick's track_id; exemplar_play
    # carries the NEW pick's track_id.
    stop_env = next(e for e in new_emits if e["type"] == "ipc.learn.exemplar_stop")
    play_env = next(e for e in new_emits if e["type"] == "ipc.learn.exemplar_play")
    assert stop_env["payload"]["track_id"] == "library:low:0"
    assert play_env["payload"]["track_id"] == "library:mid:0"


# ---------------------------------------------------------------------------
# Test 3 — completing all 3 bands emits complete_lesson + stops the player
# ---------------------------------------------------------------------------


def test_full_cycle_emits_complete_lesson_after_three_bands() -> None:
    finder = MagicMock(name="finder")
    finder.find.side_effect = [
        [_make_pick("low")],
        [_make_pick("mid")],
        [_make_pick("high")],
    ]
    player = MagicMock(name="player")
    emitted: list[dict] = []
    controller = ExemplarLessonController(
        finder=finder,
        player=player,
        ipc_emit=emitted.append,
    )
    controller.start(script=_make_script(), lesson_id="L1.14")
    controller.ack(lesson_id="L1.14")  # low → mid
    controller.ack(lesson_id="L1.14")  # mid → high
    controller.ack(lesson_id="L1.14")  # high → complete

    types = _emitted_types(emitted)
    assert "ipc.learn.complete_lesson" in types, (
        f"controller must emit complete_lesson after all 3 bands; saw {types!r}"
    )
    complete_env = next(
        e for e in emitted if e["type"] == "ipc.learn.complete_lesson"
    )
    assert complete_env["payload"]["lesson_id"] == "L1.14"

    # Player.stop() must have been called as part of the final teardown
    # (or earlier on each advance). At minimum, it MUST have been called
    # at least once before complete_lesson fires.
    assert player.stop.call_count >= 1, (
        "controller must call player.stop() during the full cycle teardown"
    )


# ---------------------------------------------------------------------------
# Test 4 — degraded install: finder returns [] → honest-null + no citation
# ---------------------------------------------------------------------------


def test_degraded_install_emits_honest_null_speak_with_no_citation() -> None:
    """When ExemplarFinder.find() returns [] for ALL bands, the
    controller surfaces a honest-null tutor copy with EMPTY citations
    (Rule: never fabricate a citation atom for a track that doesn't exist).
    The cycle still advances on user MIDI; complete_lesson fires after
    all 3 bands.
    """
    finder = MagicMock(name="finder")
    finder.find.side_effect = [[], [], []]
    player = MagicMock(name="player")
    emitted: list[dict] = []
    controller = ExemplarLessonController(
        finder=finder,
        player=player,
        ipc_emit=emitted.append,
    )
    controller.start(script=_make_script(), lesson_id="L1.14")

    # No exemplar_play (no audio to play); a tutor_speak with EMPTY
    # citations and the honest-null phrasing.
    types = _emitted_types(emitted)
    assert "ipc.learn.exemplar_play" not in types, (
        f"degraded install must NOT emit exemplar_play (no audio); "
        f"saw {types!r}"
    )
    assert "ipc.learn.tutor_speak" in types
    speak_env = next(
        e for e in emitted if e["type"] == "ipc.learn.tutor_speak"
    )
    citations = speak_env["payload"]["citations"]
    assert citations == [], (
        f"honest-null tutor_speak must carry NO citation (no fabricated "
        f"[exemplar:...] atoms); got citations={citations!r}"
    )

    # Cycle still advances on user MIDI — 3 ack()s must reach
    # complete_lesson without raising (the controller must not block on
    # missing audio).
    controller.ack(lesson_id="L1.14")
    controller.ack(lesson_id="L1.14")
    controller.ack(lesson_id="L1.14")
    final_types = _emitted_types(emitted)
    assert "ipc.learn.complete_lesson" in final_types, (
        f"degraded install must still complete after 3 ack()s; "
        f"saw {final_types!r}"
    )

    # Player.play() must NEVER be called in the degraded-install branch.
    player.play.assert_not_called()


# ---------------------------------------------------------------------------
# Test 5 — stop() is idempotent and safe from any state
# ---------------------------------------------------------------------------


def test_stop_is_idempotent_and_safe_from_any_state() -> None:
    """Calling .stop() repeatedly from any state (no-active-cycle,
    mid-cycle, post-cycle) must not raise. The first stop after a
    started cycle emits a final ipc.learn.exemplar_stop for the active
    pick; subsequent calls are silent no-ops.
    """
    finder = MagicMock(name="finder")
    finder.find.return_value = [_make_pick("low")]
    player = MagicMock(name="player")
    emitted: list[dict] = []
    controller = ExemplarLessonController(
        finder=finder,
        player=player,
        ipc_emit=emitted.append,
    )

    # No active cycle yet — must not raise.
    controller.stop(lesson_id="L1.14")
    controller.stop(lesson_id="L1.14")

    # Start a cycle, then stop mid-flight.
    controller.start(script=_make_script(), lesson_id="L1.14")
    pre_stop_count = len(emitted)
    controller.stop(lesson_id="L1.14")
    new_after_stop = emitted[pre_stop_count:]
    assert any(
        e["type"] == "ipc.learn.exemplar_stop" for e in new_after_stop
    ), (
        f"stop() during an active cycle must emit exemplar_stop; "
        f"saw {_emitted_types(new_after_stop)!r}"
    )

    # Second stop must not re-emit (idempotent).
    second_pre_count = len(emitted)
    controller.stop(lesson_id="L1.14")
    second_new = emitted[second_pre_count:]
    assert not any(
        e["type"] == "ipc.learn.exemplar_stop" for e in second_new
    ), (
        f"second stop() must be idempotent (no new exemplar_stop); "
        f"saw {_emitted_types(second_new)!r}"
    )
