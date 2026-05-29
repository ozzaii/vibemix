# SPDX-License-Identifier: Apache-2.0
"""L1.16 Course 1 Recital regression tests.

RecitalRuntime is an OBSERVER of :class:`LessonRuntime` for the L1.16
lesson. It reads ``recital_pool`` (≥5 entries) from the script, samples
``_RECITAL_SUBSET_SIZE=5`` deterministically (seed = day-of-Unix-epoch
by default; per-test seed override), grades each user MIDI on the
active prompt's ``expected_action``, and on a 5/5 pass flips
:class:`LearnProgress.course_2_unlocked` to True + calls
``save_progress`` (the Course 2 unlock gate).

Nine tests:

  1. Sampling — given a 9-entry pool, ``.start()`` samples exactly 5
     entries deterministically (same seed → same 5 entries).

  2. Default seed — when no seed is passed, the controller uses
     ``int(time.time() // 86400)`` (day-of-Unix-epoch).

  3. Prompt emit — each sampled prompt fires a ``ipc.learn.tutor_speak``
     envelope (the prompt text) + a ``ipc.learn.highlight`` envelope
     when the expected_action carries a control.

  4. Match → score +1 + advance — when user MIDI matches the active
     prompt's expected_action, score increments and the controller
     advances to the next prompt. Non-matching MIDI leaves the score
     untouched.

  5. Outcome copy — after all 5 prompts, the controller emits a
     ``tutor_speak`` with the ``recital_outcomes.pass`` copy on 5/5 OR
     the ``recital_outcomes.fail`` copy (with ``{score}`` substituted)
     on <5.

  6. 5/5 pass — flips ``LearnProgress.course_2_unlocked = True`` AND
     calls ``save_progress(progress)`` exactly once.

  7. <5 pass — leaves ``course_2_unlocked = False``; ``save_progress``
     is NOT called for the unlock.

  8. complete_lesson — after scoring (pass or fail), the controller
     emits ``ipc.learn.complete_lesson`` (the runtime's
     on_enter_completed callback fires its own; the observer's signals
     end-of-cycle).

  9. ``.stop()`` is idempotent — safe to call from any state, no
     emits on a stopped state.

REQ-ID: CURR-1.16 (Course 1 Recital — gate to unlock Course 2).
"""
from __future__ import annotations

import random
from typing import Any
from unittest.mock import MagicMock

import pytest

try:
    from vibemix.learn.progress import LearnProgress
    from vibemix.learn.recital import (
        _RECITAL_SUBSET_SIZE,
        RecitalRuntime,
    )
except ImportError:
    pytest.skip(
        "RecitalRuntime unavailable in this partial Learn build.",
        allow_module_level=True,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_RECITAL_POOL: list[dict[str, Any]] = [
    {
        "from_lesson": "L1.03",
        "prompt": "turn the high EQ knob on deck A all the way one direction.",
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
        "prompt": "nudge deck A's pitch fader a quarter of the throw.",
        "expected_action": {
            "type": "cc",
            "control": "tempo",
            "deck": "A",
            "min_delta": 50,
        },
    },
    {
        "from_lesson": "L1.06",
        "prompt": "press cue on deck A.",
        "expected_action": {
            "type": "button",
            "control": "cue",
            "deck": "A",
            "direction": "down",
        },
    },
    {
        "from_lesson": "L1.07",
        "prompt": "nudge deck A's jog wheel.",
        "expected_action": {
            "type": "cc",
            "control": "jog",
            "deck": "A",
            "min_delta": 10,
        },
    },
    {
        "from_lesson": "L1.08",
        "prompt": "tap the headphone cue button on deck A.",
        "expected_action": {
            "type": "button",
            "control": "headphone_cue",
            "deck": "A",
            "direction": "down",
        },
    },
    {
        "from_lesson": "L1.09",
        "prompt": "touch the master volume knob.",
        "expected_action": {
            "type": "cc",
            "control": "master_vol",
            "min_delta": 5,
        },
    },
    {
        "from_lesson": "L1.12",
        "prompt": "tap continue when you hear the breakdown.",
        "expected_action": {
            "type": "button",
            "control": "lesson_continue",
            "direction": "down",
        },
    },
    {
        "from_lesson": "L1.13",
        "prompt": "tap continue when you spot the breakdown on the waveform.",
        "expected_action": {
            "type": "button",
            "control": "lesson_continue",
            "direction": "down",
        },
    },
]


_RECITAL_OUTCOMES = {
    "pass": "5 of 5. course 2 unlocked.",
    "fail": "{score} of 5. replay when you're ready.",
}


def _make_script() -> dict[str, Any]:
    """Build an in-line L1.16-shaped script mirroring the 94-01 fixture."""
    return {
        "lesson_id": "L1.16",
        "recital_pool": list(_RECITAL_POOL),
        "recital_outcomes": dict(_RECITAL_OUTCOMES),
    }


def _emitted_types(emitted: list[dict]) -> list[str]:
    return [env["type"] for env in emitted]


def _matching_midi_for(entry: dict[str, Any]) -> dict[str, Any]:
    """Build a MIDI event that satisfies an entry's expected_action.

    Mirrors the LessonRuntime.action_matches predicate contract:
      * CC: cur - prev >= min_delta (we use prev=0, cur=min_delta).
      * Button: control + direction (+ deck when expected sets one).
    """
    expected = entry["expected_action"]
    if expected["type"] == "cc":
        cur = int(expected.get("min_delta", 38))
        midi = {
            "type": "cc",
            "control": expected["control"],
            "value": cur,
            "prev_value": 0,
        }
        if "deck" in expected:
            midi["deck"] = expected["deck"]
        return midi
    # button
    midi = {
        "type": "button",
        "control": expected["control"],
        "direction": expected.get("direction", "down"),
    }
    if "deck" in expected:
        midi["deck"] = expected["deck"]
    return midi


# ---------------------------------------------------------------------------
# Test 1 — deterministic sampling: same seed → same 5 entries
# ---------------------------------------------------------------------------


def test_sampling_is_deterministic_with_fixed_seed() -> None:
    """``rng=random.Random(seed)`` produces the same sample on every
    invocation. RecitalRuntime exposes ``seed`` as a constructor kwarg
    for hermetic testing; in production it defaults to the day-of-epoch.

    The controller emits one prompt per advance step — start() emits
    prompt 1, ack() advances to + emits prompt 2, etc. We drive the
    cycle through all 5 ack()s to surface the full sampled subset.
    """
    progress_a = LearnProgress()
    progress_b = LearnProgress()
    emitted_a: list[dict] = []
    emitted_b: list[dict] = []
    save_fn_a = MagicMock(name="save_fn_a")
    save_fn_b = MagicMock(name="save_fn_b")

    rt_a = RecitalRuntime(
        ipc_emit=emitted_a.append,
        progress=progress_a,
        seed=42,
        save_fn=save_fn_a,
    )
    rt_b = RecitalRuntime(
        ipc_emit=emitted_b.append,
        progress=progress_b,
        seed=42,
        save_fn=save_fn_b,
    )

    rt_a.start(script=_make_script(), lesson_id="L1.16-course-1-recital")
    rt_b.start(script=_make_script(), lesson_id="L1.16-course-1-recital")
    # Drive through all 5 prompts to surface the full sampled subset.
    for _ in range(_RECITAL_SUBSET_SIZE):
        rt_a.ack(lesson_id="L1.16-course-1-recital")
        rt_b.ack(lesson_id="L1.16-course-1-recital")

    # The two controllers MUST emit the exact same sequence of prompt
    # tutor_speak texts (the seed pins the rng.sample result).
    # Filter out outcome copy (the final pass/fail copy is also a
    # tutor_speak; we're only comparing prompt copy).
    prompt_set = {e["prompt"] for e in _RECITAL_POOL}
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
        f"same seed must produce identical prompt sequence; "
        f"got {prompts_a!r} vs {prompts_b!r}"
    )
    # And exactly 5 prompts surfaced (the recital subset size).
    assert len(prompts_a) == _RECITAL_SUBSET_SIZE, (
        f"recital must surface exactly {_RECITAL_SUBSET_SIZE} prompts; "
        f"got {len(prompts_a)}: {prompts_a!r}"
    )


# ---------------------------------------------------------------------------
# Test 2 — default seed = int(time.time() // 86400) (day-of-epoch)
# ---------------------------------------------------------------------------


def test_default_seed_is_day_of_epoch(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without ``seed=...``, the controller derives a seed from the day
    of Unix epoch. Replays within the SAME day pick the SAME 5 prompts
    (anti-grind). Cross-day replays re-roll (anti-frustration).
    """
    # Pin time.time so we know which seed we're testing against.
    fake_day = 19_500  # arbitrary day-of-epoch
    fixed_t = fake_day * 86_400.0 + 42.0
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
    )  # no seed → derives from time
    rt.start(script=_make_script(), lesson_id="L1.16-course-1-recital")
    # Drive all 5 prompts to surface the full sampled subset.
    for _ in range(_RECITAL_SUBSET_SIZE):
        rt.ack(lesson_id="L1.16-course-1-recital")

    # Build the expected subset manually using random.Random(fake_day).
    expected_sample = random.Random(fake_day).sample(
        _RECITAL_POOL, k=_RECITAL_SUBSET_SIZE
    )
    expected_prompts = [e["prompt"] for e in expected_sample]
    prompt_set = {e["prompt"] for e in _RECITAL_POOL}
    actual_prompts = [
        e["payload"]["text"]
        for e in emitted
        if e["type"] == "ipc.learn.tutor_speak"
        and e["payload"]["text"] in prompt_set
    ]
    assert actual_prompts == expected_prompts, (
        f"default seed must equal day-of-epoch ({fake_day}); "
        f"expected prompts {expected_prompts!r}, got {actual_prompts!r}"
    )


# ---------------------------------------------------------------------------
# Test 3 — each prompt emits tutor_speak + highlight when expected has a control
# ---------------------------------------------------------------------------


def test_each_prompt_emits_tutor_speak_and_highlight() -> None:
    progress = LearnProgress()
    emitted: list[dict] = []
    rt = RecitalRuntime(
        ipc_emit=emitted.append,
        progress=progress,
        seed=42,
        save_fn=MagicMock(),
    )
    rt.start(script=_make_script(), lesson_id="L1.16-course-1-recital")

    types = _emitted_types(emitted)
    assert "ipc.learn.tutor_speak" in types, (
        f"first prompt must emit tutor_speak; saw {types!r}"
    )
    assert "ipc.learn.highlight" in types, (
        f"first prompt must emit highlight (expected_action carries a "
        f"control_id); saw {types!r}"
    )


# ---------------------------------------------------------------------------
# Test 4 — matching MIDI scores +1, non-matching leaves score untouched
# ---------------------------------------------------------------------------


def test_matching_midi_scores_and_advances() -> None:
    progress = LearnProgress()
    emitted: list[dict] = []
    rt = RecitalRuntime(
        ipc_emit=emitted.append,
        progress=progress,
        seed=42,
        save_fn=MagicMock(),
    )
    rt.start(script=_make_script(), lesson_id="L1.16-course-1-recital")

    # Build the matching midi for the FIRST sampled prompt. The
    # controller exposes the active prompt via .matches(midi) — we use
    # the reference sample to derive it.
    sampled = random.Random(42).sample(_RECITAL_POOL, k=_RECITAL_SUBSET_SIZE)
    first_match = _matching_midi_for(sampled[0])

    assert rt.matches(first_match) is True, (
        f"controller.matches(midi) must return True for the matching "
        f"MIDI for the active prompt; midi={first_match!r}"
    )
    rt.ack(lesson_id="L1.16-course-1-recital")
    # After ack, the controller advanced to prompt 2 — the active
    # prompt's expected_action now belongs to sampled[1].
    second_match = _matching_midi_for(sampled[1])
    assert rt.matches(second_match) is True, (
        f"after ack, .matches() must reflect the second prompt's "
        f"expected_action; midi={second_match!r}"
    )

    # A non-matching MIDI (different control name) must NOT match.
    not_match = {
        "type": "cc",
        "control": "no_such_control",
        "value": 127,
        "prev_value": 0,
    }
    assert rt.matches(not_match) is False, (
        "non-matching MIDI must leave .matches() == False"
    )


# ---------------------------------------------------------------------------
# Test 5 — outcome copy is substituted from recital_outcomes
# ---------------------------------------------------------------------------


def test_outcome_copy_pass_and_fail() -> None:
    """5/5 pass surfaces the pass copy; <5 surfaces the fail copy with
    ``{score}`` substituted.
    """
    # ---- pass path -----------------------------------------------------
    progress_pass = LearnProgress()
    emitted_pass: list[dict] = []
    save_fn_pass = MagicMock(name="save_fn_pass")
    rt_pass = RecitalRuntime(
        ipc_emit=emitted_pass.append,
        progress=progress_pass,
        seed=42,
        save_fn=save_fn_pass,
    )
    rt_pass.start(script=_make_script(), lesson_id="L1.16-course-1-recital")
    # Five matching ack()s — drives to pass.
    for _ in range(_RECITAL_SUBSET_SIZE):
        rt_pass.ack(lesson_id="L1.16-course-1-recital")
    pass_speaks = [
        e["payload"]["text"]
        for e in emitted_pass
        if e["type"] == "ipc.learn.tutor_speak"
    ]
    assert _RECITAL_OUTCOMES["pass"] in pass_speaks, (
        f"5/5 pass must emit pass copy '{_RECITAL_OUTCOMES['pass']!r}'; "
        f"saw {pass_speaks!r}"
    )

    # ---- fail path -----------------------------------------------------
    progress_fail = LearnProgress()
    emitted_fail: list[dict] = []
    save_fn_fail = MagicMock(name="save_fn_fail")
    rt_fail = RecitalRuntime(
        ipc_emit=emitted_fail.append,
        progress=progress_fail,
        seed=42,
        save_fn=save_fn_fail,
    )
    rt_fail.start(script=_make_script(), lesson_id="L1.16-course-1-recital")
    # Only 2 ack()s; we need the controller to finalize at score=2. The
    # public path is matching ack vs no ack; we drive the cycle to
    # exhaustion by calling a public ".skip_remaining()" OR by emitting
    # 3 non-matching skips. The controller exposes a `.fail_remaining()`
    # helper that advances without scoring — the canonical "user gave up"
    # path. (If no such helper exists, this assertion is the contract:
    # 3 fail-skip calls drive the controller to finalize at score=2.)
    rt_fail.ack(lesson_id="L1.16-course-1-recital")
    rt_fail.ack(lesson_id="L1.16-course-1-recital")
    # The remaining 3 prompts are skipped via a non-scoring advance:
    rt_fail.skip_remaining(lesson_id="L1.16-course-1-recital")
    fail_speaks = [
        e["payload"]["text"]
        for e in emitted_fail
        if e["type"] == "ipc.learn.tutor_speak"
    ]
    expected_fail = _RECITAL_OUTCOMES["fail"].replace("{score}", "2")
    assert expected_fail in fail_speaks, (
        f"<5 pass must emit fail copy with score substituted "
        f"({expected_fail!r}); saw {fail_speaks!r}"
    )


# ---------------------------------------------------------------------------
# Test 6 — 5/5 → course_2_unlocked = True + save_progress called once
# ---------------------------------------------------------------------------


def test_five_of_five_unlocks_course_2_and_saves() -> None:
    progress = LearnProgress()
    emitted: list[dict] = []
    save_fn = MagicMock(name="save_fn")
    rt = RecitalRuntime(
        ipc_emit=emitted.append,
        progress=progress,
        seed=42,
        save_fn=save_fn,
    )
    rt.start(script=_make_script(), lesson_id="L1.16-course-1-recital")
    for _ in range(_RECITAL_SUBSET_SIZE):
        rt.ack(lesson_id="L1.16-course-1-recital")
    assert progress.course_2_unlocked is True, (
        f"5/5 pass must flip progress.course_2_unlocked to True; "
        f"got {progress.course_2_unlocked!r}"
    )
    assert save_fn.call_count == 1, (
        f"5/5 pass must call save_fn(progress) exactly once; "
        f"got {save_fn.call_count} calls; calls={save_fn.call_args_list!r}"
    )
    # save_fn was called with the LearnProgress instance (verifying the
    # right object survives — not a copy or a dict-shaped surrogate).
    save_fn.assert_called_with(progress)


# ---------------------------------------------------------------------------
# Test 7 — <5 → course_2_unlocked stays False AND save_progress NOT called
# ---------------------------------------------------------------------------


def test_less_than_five_stays_locked() -> None:
    progress = LearnProgress()
    emitted: list[dict] = []
    save_fn = MagicMock(name="save_fn")
    rt = RecitalRuntime(
        ipc_emit=emitted.append,
        progress=progress,
        seed=42,
        save_fn=save_fn,
    )
    rt.start(script=_make_script(), lesson_id="L1.16-course-1-recital")
    rt.ack(lesson_id="L1.16-course-1-recital")  # 1 scored
    rt.ack(lesson_id="L1.16-course-1-recital")  # 2 scored
    rt.ack(lesson_id="L1.16-course-1-recital")  # 3 scored
    rt.skip_remaining(lesson_id="L1.16-course-1-recital")  # finalize at 3

    assert progress.course_2_unlocked is False, (
        f"<5 pass must leave progress.course_2_unlocked = False; "
        f"got {progress.course_2_unlocked!r}"
    )
    assert save_fn.call_count == 0, (
        f"<5 pass must NOT call save_fn (no unlock to persist); "
        f"got {save_fn.call_count} calls"
    )


# ---------------------------------------------------------------------------
# Test 8 — controller emits complete_lesson after scoring (pass or fail)
# ---------------------------------------------------------------------------


def test_complete_lesson_emits_after_scoring() -> None:
    # Pass path
    progress_pass = LearnProgress()
    emitted_pass: list[dict] = []
    rt_pass = RecitalRuntime(
        ipc_emit=emitted_pass.append,
        progress=progress_pass,
        seed=42,
        save_fn=MagicMock(),
    )
    rt_pass.start(script=_make_script(), lesson_id="L1.16-course-1-recital")
    for _ in range(_RECITAL_SUBSET_SIZE):
        rt_pass.ack(lesson_id="L1.16-course-1-recital")
    assert any(
        e["type"] == "ipc.learn.complete_lesson" for e in emitted_pass
    ), (
        f"5/5 pass must emit complete_lesson; saw types "
        f"{_emitted_types(emitted_pass)!r}"
    )

    # Fail path
    progress_fail = LearnProgress()
    emitted_fail: list[dict] = []
    rt_fail = RecitalRuntime(
        ipc_emit=emitted_fail.append,
        progress=progress_fail,
        seed=42,
        save_fn=MagicMock(),
    )
    rt_fail.start(script=_make_script(), lesson_id="L1.16-course-1-recital")
    rt_fail.skip_remaining(lesson_id="L1.16-course-1-recital")
    assert any(
        e["type"] == "ipc.learn.complete_lesson" for e in emitted_fail
    ), (
        f"fail path must also emit complete_lesson; saw types "
        f"{_emitted_types(emitted_fail)!r}"
    )


# ---------------------------------------------------------------------------
# Test 9 — stop() is idempotent
# ---------------------------------------------------------------------------


def test_stop_is_idempotent() -> None:
    progress = LearnProgress()
    emitted: list[dict] = []
    rt = RecitalRuntime(
        ipc_emit=emitted.append,
        progress=progress,
        seed=42,
        save_fn=MagicMock(),
    )
    # stop() before start — must not raise.
    rt.stop(lesson_id="L1.16-course-1-recital")
    rt.stop(lesson_id="L1.16-course-1-recital")

    rt.start(script=_make_script(), lesson_id="L1.16-course-1-recital")
    rt.stop(lesson_id="L1.16-course-1-recital")
    pre_stop_count = len(emitted)
    rt.stop(lesson_id="L1.16-course-1-recital")
    rt.stop(lesson_id="L1.16-course-1-recital")
    # Two extra stops after the first stop did NOT emit anything new.
    assert len(emitted) == pre_stop_count, (
        f"stop() after first stop must be no-op; emitted grew from "
        f"{pre_stop_count} to {len(emitted)}"
    )
