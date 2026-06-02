# SPDX-License-Identifier: Apache-2.0
"""Single-source pin for skills that are not live-creditable.

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


def test_no_honest_uncreditable_skill_remains_after_beatmatch_producer_lands():
    # Beatmatching now has ``learn.practice_loop`` as its measured producer.
    assert set(_HONEST_UNCREDITABLE_V11) == set()
    assert all(spec.live_creditable for spec in SKILL_MANIFEST.values())
