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


def test_no_honest_uncreditable_skills_remain():
    # v11.0 reality after the owned-deck Beatmatch Judge shipped: EVERY skill now
    # has a live Mastered path. beatmatching was the last honest-uncreditable skill;
    # the Judge's BEATMATCH_GRADED signal (test_judge_credits_beatmatch.py) is the
    # tempo/phase event it was explicitly waiting for, so it is now creditable like
    # the rest. A future RE-uncreditable skill would be a deliberate edit here.
    assert set(_HONEST_UNCREDITABLE_V11) == set()
    assert SKILL_MANIFEST["beatmatching"].live_creditable is True
    assert SKILL_MANIFEST["harmonic_mixing"].live_creditable is True
    assert all(spec.live_creditable for spec in SKILL_MANIFEST.values())
