# SPDX-License-Identifier: Apache-2.0
"""SURF-03 — the single, rare, earned "Mastered" unlock vocal.

The ONLY co-host voice the Earned Wall ever triggers. It must fire EXACTLY ONCE
per skill's not-mastered→mastered flip — never on Competent, never on partial fill,
never again after the flip. The copy is HAND-AUTHORED JSON (slop-gated by
`check_no_tutor_slop` over `learn/transcripts/`), never free LLM generation that
could slop. Final tone is a KAAN-ACTION ear-pass (`§EARNED-MASTERED-VOCAL-EAR`).
"""
from __future__ import annotations

import json
from pathlib import Path

from scripts.launch.check_no_tutor_slop import TUTOR_SLOP_BLOCKLIST

from vibemix.learn.mastered_vocal import (
    MASTERED_VOCALS,
    mastered_unlock_line,
)

_FIXTURE = (
    Path(__file__).resolve().parents[2]
    / "src" / "vibemix" / "learn" / "vocals" / "mastered_vocals.json"
)


def test_fires_on_the_not_mastered_to_mastered_flip():
    line = mastered_unlock_line("eq_mixing", was_mastered=False, now_mastered=True)
    assert isinstance(line, str) and line.strip()


def test_silent_when_already_mastered():
    # A 4th/5th cited demo after the flip must NOT re-fire the vocal.
    assert mastered_unlock_line("eq_mixing", was_mastered=True, now_mastered=True) is None


def test_silent_on_competent_with_no_flip():
    # Partial fill / a credit that did not cross the threshold → no voice.
    assert mastered_unlock_line("eq_mixing", was_mastered=False, now_mastered=False) is None


def test_silent_on_impossible_demotion():
    # mastered is monotonic; a (True→False) input is nonsense but must never speak.
    assert mastered_unlock_line("eq_mixing", was_mastered=True, now_mastered=False) is None


def test_fires_exactly_once_across_a_demo_sequence():
    # Simulate the real sequence: the flip demo speaks once; every later demo is silent.
    spoken: list[str] = []
    # demo that flips it (count crossed threshold this call)
    line = mastered_unlock_line("transitions", was_mastered=False, now_mastered=True)
    if line is not None:
        spoken.append(line)
    # two more demos, already mastered
    for _ in range(2):
        line = mastered_unlock_line("transitions", was_mastered=True, now_mastered=True)
        if line is not None:
            spoken.append(line)
    assert len(spoken) == 1


def test_unknown_skill_falls_back_to_default_line():
    line = mastered_unlock_line("not_a_real_skill", was_mastered=False, now_mastered=True)
    assert line == MASTERED_VOCALS["_default"]
    assert isinstance(line, str) and line.strip()


def test_every_vocal_line_passes_the_tutor_slop_blocklist():
    # The copy IS co-host speech → it must clear the same gate the lessons do.
    for key, line in MASTERED_VOCALS.items():
        low = line.lower()
        for tok in TUTOR_SLOP_BLOCKLIST:
            assert tok not in low, f"mastered vocal {key!r} contains slop token {tok!r}: {line!r}"


def test_every_vocal_line_is_factual_proof_feedback():
    """Mastered speech names the cited proof, not a generic reward."""

    empty_reward_tokens = (
        "earned",
        "for real",
        "yours",
        "by you",
        "by your",
        "that one was real",
    )
    for key, line in MASTERED_VOCALS.items():
        low = line.lower()
        assert "cited" in low, f"mastered vocal {key!r} must name cited proof: {line!r}"
        for tok in empty_reward_tokens:
            assert tok not in low, (
                f"mastered vocal {key!r} contains reward filler {tok!r}: {line!r}"
            )


def test_no_vocal_line_uses_em_dash_glue():
    # Mirror the transcripts dash-glue rule: spoken copy stays terse (commas/colons/
    # periods, no em/en dashes). The fixture lives outside transcripts/, so we pin it here.
    for key, line in MASTERED_VOCALS.items():
        assert "—" not in line and "–" not in line, f"mastered vocal {key!r} uses a dash glue: {line!r}"


def test_fixture_exists_is_valid_json_and_has_a_default():
    assert _FIXTURE.is_file(), f"missing hand-authored fixture: {_FIXTURE}"
    data = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    assert "_default" in data and isinstance(data["_default"], str) and data["_default"].strip()
    # the module's loaded copy mirrors the fixture (single source on disk)
    assert MASTERED_VOCALS == data
