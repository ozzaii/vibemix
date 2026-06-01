# SPDX-License-Identifier: Apache-2.0
"""Judge voice evidence reaches the TRACK_CHANGE prompt only when measured."""

from __future__ import annotations

from vibemix.state import AICoach, Event, MusicState


def test_track_change_prompt_uses_judge_evidence_line() -> None:
    state = MusicState()
    line = (
        "[judge:transition@128.4] Judge graded the transition: compatible keys; "
        "clean low end, one bass ducked (blend score 0.88/1)"
    )
    prompt = AICoach.build_prompt(
        Event(type="TRACK_CHANGE", state=state, extra={"judge_evidence_line": line})
    )
    assert line in prompt
    assert "Keep the bracketed citation exactly" in prompt
    assert "do not add fader, EQ, or deck-control causes" in prompt


def test_track_change_prompt_without_judge_line_keeps_ordinary_track_task() -> None:
    state = MusicState()
    prompt = AICoach.build_prompt(
        Event(type="TRACK_CHANGE", state=state, extra={"prev_track": "old"})
    )
    assert "Track flipped" in prompt
    assert "Judge graded the transition" not in prompt
