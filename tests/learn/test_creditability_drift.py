# SPDX-License-Identifier: Apache-2.0
"""Single-source pin: the manifest's `live_creditable=False` skills MUST equal the
recognizer's `_HONEST_UNCREDITABLE_V11`.

`what_remains` (SURF-01) reads `SkillSpec.live_creditable` to stay honest about which
skills have a live Mastered path — but the AUTHORITATIVE truth of which event types
credit which skill lives in `skill_recognizer`. This pin fails loud if either side
drifts, so the honest-uncreditable list can never silently disagree across the two
modules (the readable manifest stays the single source per SKILL-01/03).
"""
from __future__ import annotations

from vibemix.learn.skill_recognizer import _HONEST_UNCREDITABLE_V11
from vibemix.learn.skill_tree import SKILL_MANIFEST


def test_manifest_uncreditable_matches_recognizer():
    manifest_uncreditable = {
        sid for sid, spec in SKILL_MANIFEST.items() if not spec.live_creditable
    }
    assert manifest_uncreditable == set(_HONEST_UNCREDITABLE_V11)


def test_beatmatching_is_the_only_honest_uncreditable_skill():
    # The judge/consumer engine exists, but no production live loop emits
    # BEATMATCH_GRADED yet. Keep the wall honest until that producer lands.
    assert set(_HONEST_UNCREDITABLE_V11) == {"beatmatching"}
    assert SKILL_MANIFEST["beatmatching"].live_creditable is False
    assert SKILL_MANIFEST["harmonic_mixing"].live_creditable is True
    assert all(
        spec.live_creditable
        for sid, spec in SKILL_MANIFEST.items()
        if sid != "beatmatching"
    )
