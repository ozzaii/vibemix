# SPDX-License-Identifier: Apache-2.0
"""Phase 95 — Course 2 Recital (L2.14) tests.

Pins the Course 2 mode of :class:`RecitalRuntime` (extended in Plan 95
to handle the L2.14 transition recital + course_3_unlocked gate).

The L2.14 recital differs from L1.16 in TWO ways:

  1. **Pool entries carry ``transition_type``** — the controller
     auto-detects "course_2" mode from this field. Course 1 entries
     have no transition_type → mode stays "course_1".

  2. **Pass criteria is double-floor:** ``score >= 5`` AND
     ``>= 3 distinct transition_type values across the 5
     correctly-performed prompts``. The variety floor is the anti-grind
     gate — a user who hits the same transition five times in a row
     scores 5/5 but fails the floor.

  3. **Unlock target is ``course_3_unlocked``** (not
     ``course_2_unlocked``).

Ten tests:

  1. Course-2 detection — pool with ``transition_type`` flips
     internal mode to "course_2".

  2. Pass at 5/5 + 3 distinct types unlocks course_3.

  3. Pass at 5/5 + 5 distinct types unlocks course_3.

  4. **Fail at 5/5 + 2 distinct types** — the user crushed it but
     hit the same transition over and over → stays locked. Anti-grind.

  5. Fail at <5 + 4 distinct types — variety alone isn't enough,
     score floor still binds.

  6. course_2_unlocked is NOT flipped by a Course 2 recital pass
     (only course_3_unlocked).

  7. Course-1 contract preserved — pool WITHOUT transition_type
     stays in legacy mode, flips course_2_unlocked + IGNORES distinct-
     type count.

  8. Outcome copy substitutes both ``{score}`` and ``{types}``
     placeholders.

  9. Default seed pulls from day-of-epoch (same as L1.16 contract).

  10. Pool sampling is deterministic when given a fixed seed.

REQ-ID: CURR-2.14 (Course 2 Recital — gate to unlock Course 3).
"""
from __future__ import annotations

import random
from typing import Any
from unittest.mock import MagicMock

import pytest

from vibemix.learn.progress import LearnProgress
from vibemix.learn.recital import (
    _COURSE_2_DISTINCT_TYPES_REQUIRED,
    _RECITAL_SUBSET_SIZE,
    RecitalRuntime,
)

# ---------------------------------------------------------------------------
# Helpers — Course 2 recital pool fixtures (mirrors L2.14 shape).
# ---------------------------------------------------------------------------


_COURSE_2_POOL: list[dict[str, Any]] = [
    {
        "from_lesson": "L2.03",
        "transition_type": "long_blend",
        "prompt": "perform a long blend.",
        "expected_action": {
            "type": "cc",
            "control": "xfader",
            "min_delta": 100,
        },
    },
    {
        "from_lesson": "L2.04",
        "transition_type": "eq_swap",
        "prompt": "perform an eq swap.",
        "expected_action": {
            "type": "cc",
            "control": "eq_low",
            "deck": "A",
            "min_delta": 80,
        },
    },
    {
        "from_lesson": "L2.05",
        "transition_type": "bassline_swap",
        "prompt": "perform a bassline swap.",
        "expected_action": {
            "type": "cc",
            "control": "eq_low",
            "deck": "B",
            "min_delta": 80,
        },
    },
    {
        "from_lesson": "L2.06",
        "transition_type": "filter_fade",
        "prompt": "perform a filter fade.",
        "expected_action": {
            "type": "cc",
            "control": "filter",
            "deck": "A",
            "min_delta": 60,
        },
    },
    {
        "from_lesson": "L2.07",
        "transition_type": "echo_out",
        "prompt": "perform an echo-out.",
        "expected_action": {
            "type": "button",
            "control": "fx_echo",
            "deck": "A",
            "direction": "down",
        },
    },
    {
        "from_lesson": "L2.08",
        "transition_type": "drop_swap",
        "prompt": "perform a drop swap.",
        "expected_action": {
            "type": "cc",
            "control": "xfader",
            "min_delta": 100,
        },
    },
    {
        "from_lesson": "L2.09",
        "transition_type": "loop_transition",
        "prompt": "perform a loop transition.",
        "expected_action": {
            "type": "button",
            "control": "loop_in",
            "deck": "A",
            "direction": "down",
        },
    },
]


_COURSE_2_OUTCOMES = {
    "pass": (
        "5 of 5 with {types} different transition types. "
        "course 3 unlocked."
    ),
    "fail": (
        "{score} of 5 with {types} different transition types. "
        "replay when you're ready."
    ),
}


# A Course 1 pool (no transition_type) for the legacy-mode preservation
# test. Mirrors the L1.16 fixture shape verbatim.
_COURSE_1_POOL: list[dict[str, Any]] = [
    {
        "from_lesson": "L1.03",
        "prompt": "turn the high eq knob on deck a.",
        "expected_action": {
            "type": "cc",
            "control": "eq_hi",
            "deck": "A",
            "min_delta": 80,
        },
    },
    {
        "from_lesson": "L1.04",
        "prompt": "slide the crossfader fully to one side.",
        "expected_action": {
            "type": "cc",
            "control": "xfader",
            "min_delta": 100,
        },
    },
    {
        "from_lesson": "L1.05",
        "prompt": "nudge deck a's pitch fader.",
        "expected_action": {
            "type": "cc",
            "control": "tempo",
            "deck": "A",
            "min_delta": 50,
        },
    },
    {
        "from_lesson": "L1.06",
        "prompt": "press cue on deck a.",
        "expected_action": {
            "type": "button",
            "control": "cue",
            "deck": "A",
            "direction": "down",
        },
    },
    {
        "from_lesson": "L1.07",
        "prompt": "nudge deck a's jog wheel.",
        "expected_action": {
            "type": "cc",
            "control": "jog",
            "deck": "A",
            "min_delta": 10,
        },
    },
    {
        "from_lesson": "L1.08",
        "prompt": "tap headphone cue on deck a.",
        "expected_action": {
            "type": "button",
            "control": "headphone_cue",
            "deck": "A",
            "direction": "down",
        },
    },
    {
        "from_lesson": "L1.12",
        "prompt": "tap continue at the breakdown.",
        "expected_action": {
            "type": "button",
            "control": "lesson_continue",
            "direction": "down",
        },
    },
]


_COURSE_1_OUTCOMES = {
    "pass": "5 of 5. course 2 unlocked.",
    "fail": "{score} of 5. replay when you're ready.",
}


def _make_c2_script() -> dict[str, Any]:
    """Course 2 (L2.14-shaped) script with transition_type fields."""
    return {
        "lesson_id": "L2.14",
        "recital_pool": list(_COURSE_2_POOL),
        "recital_outcomes": dict(_COURSE_2_OUTCOMES),
    }


def _make_c1_script() -> dict[str, Any]:
    """Course 1 (L1.16-shaped) script — no transition_type fields."""
    return {
        "lesson_id": "L1.16",
        "recital_pool": list(_COURSE_1_POOL),
        "recital_outcomes": dict(_COURSE_1_OUTCOMES),
    }


def _emitted_types(emitted: list[dict]) -> list[str]:
    return [env["type"] for env in emitted]


def _build_c2_rt(
    *,
    progress: LearnProgress | None = None,
    seed: int = 42,
    save_fn: Any | None = None,
) -> tuple[RecitalRuntime, list[dict], LearnProgress, MagicMock]:
    """Build a fresh RecitalRuntime + emit-sink + progress + save_fn
    mock. Returns the 4-tuple so each test wires it without copy-paste.
    """
    progress = progress or LearnProgress()
    emitted: list[dict] = []
    save = save_fn or MagicMock(name="save_fn")
    rt = RecitalRuntime(
        ipc_emit=emitted.append,
        progress=progress,
        seed=seed,
        save_fn=save,
    )
    return rt, emitted, progress, save


# ---------------------------------------------------------------------------
# Test 1 — Course-2 detection from pool shape.
# ---------------------------------------------------------------------------


def test_course_2_mode_detected_from_transition_type_field() -> None:
    """A pool entry carrying ``transition_type`` flips the controller
    into ``course_2`` mode. The detection runs at .start() time —
    inspectable via the internal ``_mode`` flag the controller exposes.
    """
    rt, _emitted, _progress, _save = _build_c2_rt()
    rt.start(script=_make_c2_script(), lesson_id="L2.14-course-2-recital")
    assert rt._mode == "course_2", (
        f"course_2 detection failed; _mode = {rt._mode!r}, expected "
        "'course_2'. Plan 95 contract: any pool entry carrying "
        "transition_type flips mode."
    )


# ---------------------------------------------------------------------------
# Test 2 — pass at 5/5 + exactly 3 distinct types unlocks course_3.
# ---------------------------------------------------------------------------


def test_five_of_five_with_three_distinct_types_unlocks_course_3(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """5/5 score AND exactly 3 distinct transition types must satisfy
    the variety floor (``_COURSE_2_DISTINCT_TYPES_REQUIRED = 3``).

    To pin the sampled subset's transition_type distribution, we
    monkeypatch ``random.Random.sample`` to return a hand-crafted 5-
    entry subset with EXACTLY 3 distinct types (one transition type
    repeated to test the boundary condition).
    """
    # Hand-craft a 5-entry subset with 3 distinct types.
    pinned = [
        _COURSE_2_POOL[0],  # long_blend
        _COURSE_2_POOL[5],  # drop_swap (different from long_blend even
                            # though both use xfader)
        _COURSE_2_POOL[1],  # eq_swap
        _COURSE_2_POOL[0],  # long_blend (repeat — still 3 distinct)
        _COURSE_2_POOL[1],  # eq_swap (repeat — still 3 distinct)
    ]

    class _PinnedRng:
        def __init__(self, _seed: int) -> None:
            pass

        def sample(self, _pool: list, k: int) -> list:
            assert k == _RECITAL_SUBSET_SIZE
            return list(pinned)

    progress = LearnProgress()
    emitted: list[dict] = []
    save = MagicMock()
    rt = RecitalRuntime(
        ipc_emit=emitted.append,
        progress=progress,
        seed=42,
        save_fn=save,
        rng_class=_PinnedRng,
    )
    rt.start(script=_make_c2_script(), lesson_id="L2.14-course-2-recital")
    for _ in range(_RECITAL_SUBSET_SIZE):
        rt.ack(lesson_id="L2.14-course-2-recital")

    assert progress.course_3_unlocked is True, (
        f"5/5 + 3 distinct types must flip course_3_unlocked; got "
        f"{progress.course_3_unlocked!r}"
    )
    assert save.call_count == 1, (
        f"5/5 + 3 distinct types must save_fn once; got "
        f"{save.call_count} calls"
    )


# ---------------------------------------------------------------------------
# Test 3 — pass at 5/5 + 5 distinct types unlocks course_3.
# ---------------------------------------------------------------------------


def test_five_of_five_with_five_distinct_types_unlocks_course_3() -> None:
    """5/5 score AND 5 distinct transition types (maximum variety) is
    the obvious pass case. seed=42 picks 5 distinct entries from the
    7-entry pool deterministically.
    """
    rt, _emitted, progress, save = _build_c2_rt(seed=42)
    rt.start(script=_make_c2_script(), lesson_id="L2.14-course-2-recital")
    for _ in range(_RECITAL_SUBSET_SIZE):
        rt.ack(lesson_id="L2.14-course-2-recital")

    # With seed=42 + 7-entry pool, random.Random(42).sample picks 5
    # distinct entries → all 5 transition_types are distinct.
    sampled = random.Random(42).sample(_COURSE_2_POOL, k=_RECITAL_SUBSET_SIZE)
    distinct_types = {e["transition_type"] for e in sampled}
    assert len(distinct_types) >= _COURSE_2_DISTINCT_TYPES_REQUIRED, (
        f"test precondition broken: seed=42 yielded only "
        f"{len(distinct_types)} distinct types; expected >=3"
    )

    assert progress.course_3_unlocked is True, (
        f"5/5 + {len(distinct_types)} distinct types must unlock "
        f"course_3; got course_3_unlocked={progress.course_3_unlocked!r}"
    )
    assert save.call_count == 1, (
        f"course_3 unlock must save_fn once; got {save.call_count}"
    )


# ---------------------------------------------------------------------------
# Test 4 — 5/5 BUT only 2 distinct types → variety floor fails, stays locked.
# ---------------------------------------------------------------------------


def test_five_of_five_with_only_two_distinct_types_stays_locked() -> None:
    """The anti-grind gate. A user who hits the same transition five
    times in a row scores 5/5 by count but fails the variety floor
    (need ≥3 distinct types). course_3 stays locked.
    """
    # Hand-craft a 5-entry subset with only 2 distinct types:
    # long_blend (x3) + eq_swap (x2).
    pinned = [
        _COURSE_2_POOL[0],  # long_blend
        _COURSE_2_POOL[0],  # long_blend (repeat)
        _COURSE_2_POOL[1],  # eq_swap
        _COURSE_2_POOL[0],  # long_blend (repeat)
        _COURSE_2_POOL[1],  # eq_swap (repeat)
    ]

    class _PinnedRng:
        def __init__(self, _seed: int) -> None:
            pass

        def sample(self, _pool: list, k: int) -> list:
            assert k == _RECITAL_SUBSET_SIZE
            return list(pinned)

    progress = LearnProgress()
    emitted: list[dict] = []
    save = MagicMock()
    rt = RecitalRuntime(
        ipc_emit=emitted.append,
        progress=progress,
        seed=42,
        save_fn=save,
        rng_class=_PinnedRng,
    )
    rt.start(script=_make_c2_script(), lesson_id="L2.14-course-2-recital")
    for _ in range(_RECITAL_SUBSET_SIZE):
        rt.ack(lesson_id="L2.14-course-2-recital")

    # 5/5 by count, but only 2 distinct types → variety floor fails.
    assert progress.course_3_unlocked is False, (
        f"5/5 + 2 distinct types must NOT unlock course_3 (variety "
        f"floor is 3); got course_3_unlocked={progress.course_3_unlocked!r}"
    )
    assert save.call_count == 0, (
        f"variety-floor fail must NOT save_fn (no unlock to persist); "
        f"got {save.call_count} calls"
    )

    # Fail copy with {score} and {types} substituted must surface.
    fail_speaks = [
        e["payload"]["text"]
        for e in emitted
        if e["type"] == "ipc.learn.tutor_speak"
    ]
    expected_fail = _COURSE_2_OUTCOMES["fail"].replace(
        "{score}", "5"
    ).replace("{types}", "2")
    assert expected_fail in fail_speaks, (
        f"fail copy with {{score}}=5 and {{types}}=2 must surface; "
        f"expected: {expected_fail!r}\nactual: {fail_speaks!r}"
    )


# ---------------------------------------------------------------------------
# Test 5 — <5 score + lots of distinct types → still fails on score floor.
# ---------------------------------------------------------------------------


def test_low_score_with_high_variety_still_fails() -> None:
    """Variety alone is not enough — the score floor (5/5) still binds.
    User performs 3 prompts correctly across 3 distinct transitions
    then gives up via skip_remaining(). Score=3 < 5 → fail.
    """
    rt, _emitted, progress, save = _build_c2_rt(seed=42)
    rt.start(script=_make_c2_script(), lesson_id="L2.14-course-2-recital")
    rt.ack(lesson_id="L2.14-course-2-recital")  # 1 scored
    rt.ack(lesson_id="L2.14-course-2-recital")  # 2 scored
    rt.ack(lesson_id="L2.14-course-2-recital")  # 3 scored
    rt.skip_remaining(lesson_id="L2.14-course-2-recital")  # finalize @ 3

    assert progress.course_3_unlocked is False, (
        f"score=3 must NOT unlock course_3 even with variety; got "
        f"course_3_unlocked={progress.course_3_unlocked!r}"
    )
    assert save.call_count == 0, (
        f"low-score fail must NOT save_fn; got {save.call_count} calls"
    )


# ---------------------------------------------------------------------------
# Test 6 — Course 2 pass does NOT flip course_2_unlocked.
# ---------------------------------------------------------------------------


def test_course_2_pass_does_not_flip_course_2_unlocked() -> None:
    """The Course 2 recital flips ``course_3_unlocked`` only — NOT
    ``course_2_unlocked``. (course_2_unlocked is already True before
    the user can reach Course 2; the recital flipping it would be a
    no-op-with-side-effects bug.)
    """
    # Start with course_2 already unlocked (the realistic precondition
    # for a user reaching L2.14).
    progress = LearnProgress(course_2_unlocked=True)
    rt, _emitted, _progress, _save = _build_c2_rt(progress=progress, seed=42)
    rt.start(script=_make_c2_script(), lesson_id="L2.14-course-2-recital")
    for _ in range(_RECITAL_SUBSET_SIZE):
        rt.ack(lesson_id="L2.14-course-2-recital")

    # course_2 was already True; must stay True (idempotent).
    assert progress.course_2_unlocked is True
    # course_3 must now be True (the Course 2 recital's unlock target).
    assert progress.course_3_unlocked is True, (
        f"Course 2 recital pass must flip course_3_unlocked; got "
        f"course_3_unlocked={progress.course_3_unlocked!r}"
    )


# ---------------------------------------------------------------------------
# Test 7 — Course 1 contract preserved (no transition_type → legacy mode).
# ---------------------------------------------------------------------------


def test_course_1_contract_preserved_when_pool_has_no_transition_type() -> None:
    """A pool WITHOUT ``transition_type`` stays in ``course_1`` mode —
    distinct-types are NOT counted; ``course_2_unlocked`` is the unlock
    target. Pins backward compatibility with the L1.16 fixture.
    """
    rt, _emitted, progress, save = _build_c2_rt(seed=42)
    rt.start(script=_make_c1_script(), lesson_id="L1.16-course-1-recital")

    assert rt._mode == "course_1", (
        f"Course 1 pool must keep mode='course_1'; got {rt._mode!r}"
    )

    for _ in range(_RECITAL_SUBSET_SIZE):
        rt.ack(lesson_id="L1.16-course-1-recital")

    # Course 1 unlock target is course_2_unlocked.
    assert progress.course_2_unlocked is True, (
        f"Course 1 5/5 must flip course_2_unlocked; got "
        f"{progress.course_2_unlocked!r}"
    )
    # Course 1 does NOT touch course_3_unlocked.
    assert progress.course_3_unlocked is False, (
        f"Course 1 pass must NOT flip course_3_unlocked; got "
        f"{progress.course_3_unlocked!r}"
    )
    assert save.call_count == 1


# ---------------------------------------------------------------------------
# Test 8 — outcome copy substitutes both {score} and {types} placeholders.
# ---------------------------------------------------------------------------


def test_outcome_copy_substitutes_score_and_types_placeholders() -> None:
    """Both ``{score}`` and ``{types}`` substitute on emit. We drive
    the controller to a pass (5/5 + distinct types) AND verify the
    pass copy carries the substituted ``{types}`` count.
    """
    rt, emitted, _progress, _save = _build_c2_rt(seed=42)
    rt.start(script=_make_c2_script(), lesson_id="L2.14-course-2-recital")
    for _ in range(_RECITAL_SUBSET_SIZE):
        rt.ack(lesson_id="L2.14-course-2-recital")

    # With seed=42 + 7-entry pool, random.Random(42).sample picks 5
    # distinct entries.
    sampled = random.Random(42).sample(_COURSE_2_POOL, k=_RECITAL_SUBSET_SIZE)
    distinct_types = len({e["transition_type"] for e in sampled})

    expected_pass = _COURSE_2_OUTCOMES["pass"].replace(
        "{types}", str(distinct_types)
    )
    # {score} also substituted in pass copy (even though the template
    # may not use it — replace is a no-op on a missing placeholder).
    expected_pass = expected_pass.replace("{score}", "5")

    pass_speaks = [
        e["payload"]["text"]
        for e in emitted
        if e["type"] == "ipc.learn.tutor_speak"
    ]
    assert expected_pass in pass_speaks, (
        f"pass copy must substitute {{types}} (={distinct_types}); "
        f"expected: {expected_pass!r}\nactual: {pass_speaks!r}"
    )


# ---------------------------------------------------------------------------
# Test 9 — default seed = day-of-epoch (mirrors L1.16 contract).
# ---------------------------------------------------------------------------


def test_default_seed_is_day_of_epoch_for_course_2(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Without an explicit ``seed=...``, the Course 2 recital pulls
    ``int(time.time() // 86400)`` (mirroring L1.16). Replays within
    the same day pick the SAME 5 prompts (anti-grind).
    """
    fake_day = 19_600
    fixed_t = fake_day * 86_400.0 + 99.0
    monkeypatch.setattr(
        "vibemix.learn.recital.time.time",
        lambda: fixed_t,
    )

    progress = LearnProgress()
    emitted: list[dict] = []
    rt = RecitalRuntime(
        ipc_emit=emitted.append,
        progress=progress,
        save_fn=MagicMock(),
    )  # no seed → default
    rt.start(script=_make_c2_script(), lesson_id="L2.14-course-2-recital")
    # Drive all 5 prompts to surface the full sampled subset.
    for _ in range(_RECITAL_SUBSET_SIZE):
        rt.ack(lesson_id="L2.14-course-2-recital")

    expected_sample = random.Random(fake_day).sample(
        _COURSE_2_POOL, k=_RECITAL_SUBSET_SIZE
    )
    expected_prompts = [e["prompt"] for e in expected_sample]
    prompt_set = {e["prompt"] for e in _COURSE_2_POOL}
    actual_prompts = [
        e["payload"]["text"]
        for e in emitted
        if e["type"] == "ipc.learn.tutor_speak"
        and e["payload"]["text"] in prompt_set
    ]
    assert actual_prompts == expected_prompts, (
        f"default seed (day={fake_day}) must yield deterministic "
        f"prompt order; expected {expected_prompts!r}, got "
        f"{actual_prompts!r}"
    )


# ---------------------------------------------------------------------------
# Test 10 — deterministic sampling under fixed seed.
# ---------------------------------------------------------------------------


def test_course_2_sampling_is_deterministic_with_fixed_seed() -> None:
    """Two controllers with the same seed produce identical prompt
    sequences. Mirrors the L1.16 deterministic-sampling contract.
    """
    rt_a, emitted_a, _progress_a, _save_a = _build_c2_rt(seed=42)
    rt_b, emitted_b, _progress_b, _save_b = _build_c2_rt(seed=42)

    rt_a.start(script=_make_c2_script(), lesson_id="L2.14-course-2-recital")
    rt_b.start(script=_make_c2_script(), lesson_id="L2.14-course-2-recital")
    for _ in range(_RECITAL_SUBSET_SIZE):
        rt_a.ack(lesson_id="L2.14-course-2-recital")
        rt_b.ack(lesson_id="L2.14-course-2-recital")

    prompt_set = {e["prompt"] for e in _COURSE_2_POOL}
    prompts_a = [
        e["payload"]["text"]
        for e in emitted_a
        if e["type"] == "ipc.learn.tutor_speak"
        and e["payload"]["text"] in prompt_set
    ]
    prompts_b = [
        e["payload"]["text"]
        for e in emitted_b
        if e["type"] == "ipc.learn.tutor_speak"
        and e["payload"]["text"] in prompt_set
    ]
    assert prompts_a == prompts_b, (
        f"seed=42 must produce identical prompt sequences; got "
        f"{prompts_a!r} vs {prompts_b!r}"
    )
    assert len(prompts_a) == _RECITAL_SUBSET_SIZE
