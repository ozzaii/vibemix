# SPDX-License-Identifier: Apache-2.0
"""VocalDetector coverage (Phase 6 Wave 2).

CONTEXT §Vocal-Section Detector — 2-of-3 rules trip "above threshold", then
hysteresis (1.5s in / 2.5s out) governs the public boolean.

Tests use deterministic ``now`` injection so timing is precise without sleeps.
"""

from __future__ import annotations

from vibemix.state.genre import VocalDetector, load_profile


def _below_feats() -> dict:
    """Feature snapshot below all 3 vocal rules."""
    return {"mid_share": 0.10, "high_share": 0.05, "sub_share": 0.40, "onsets_per_sec": 1.0}


def _above_rules1_3_feats() -> dict:
    """mid_share>0.45 AND high_share>0.20 AND sub_share<0.30 → rules 1+3 fire."""
    return {"mid_share": 0.50, "high_share": 0.30, "sub_share": 0.10, "onsets_per_sec": 1.0}


def _rule3_only_feats() -> dict:
    """Only rule 3 fires (high_share>0.20 AND sub_share<0.30); mid below."""
    return {"mid_share": 0.10, "high_share": 0.25, "sub_share": 0.20, "onsets_per_sec": 1.0}


def test_initial_state_is_false():
    vd = VocalDetector()
    assert vd.is_vocal_section({}, [], now=0.0) is False


def test_below_threshold_stays_false():
    """Sustained below-threshold features → never flips."""
    vd = VocalDetector()
    for t in [0.0, 0.1, 0.2, 0.5, 1.0, 2.0, 3.0]:
        assert vd.is_vocal_section(_below_feats(), [_below_feats()], now=t) is False


def test_rule3_alone_does_not_trip():
    """Only one rule fires → need 2-of-3 → stays False."""
    vd = VocalDetector()
    # Feed for 5 seconds; no flip because only rule3 fires.
    for t in [0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 5.0]:
        assert vd.is_vocal_section(_rule3_only_feats(), [], now=t) is False


def test_two_rules_above_threshold_for_1_5s_flips_to_true():
    """rules 1 + 3 fire; sustained 1.5s → flips True."""
    vd = VocalDetector()
    # Need sustained mid_share for rule1: feed history with sustained high mids.
    recent = [{"mid_share": 0.50}, {"mid_share": 0.50}]
    # t=0: above threshold for the first time, _above_since=0, not 1.5s yet → False
    assert vd.is_vocal_section(_above_rules1_3_feats(), recent, now=0.0) is False
    # t=0.5: still above, 0.5s < 1.5s → False
    assert vd.is_vocal_section(_above_rules1_3_feats(), recent, now=0.5) is False
    # t=1.0: 1.0s < 1.5s → False
    assert vd.is_vocal_section(_above_rules1_3_feats(), recent, now=1.0) is False
    # t=1.5: now-above_since = 1.5s ≥ in_dwell → flips True
    assert vd.is_vocal_section(_above_rules1_3_feats(), recent, now=1.5) is True


def test_drops_below_threshold_for_2_5s_flips_to_false():
    """Once active, sustained below for 2.5s → flips False."""
    vd = VocalDetector()
    recent = [{"mid_share": 0.50}, {"mid_share": 0.50}]
    # Ramp up to True
    vd.is_vocal_section(_above_rules1_3_feats(), recent, now=0.0)
    vd.is_vocal_section(_above_rules1_3_feats(), recent, now=1.5)
    assert vd._active is True

    # Now drop below threshold at t=2.0 — _below_since=2.0
    assert vd.is_vocal_section(_below_feats(), [], now=2.0) is True  # still True
    # t=3.0: 1.0s below < 2.5s → still True
    assert vd.is_vocal_section(_below_feats(), [], now=3.0) is True
    # t=4.0: 2.0s below < 2.5s → still True
    assert vd.is_vocal_section(_below_feats(), [], now=4.0) is True
    # t=4.5: 2.5s below ≥ out_dwell → flips False
    assert vd.is_vocal_section(_below_feats(), [], now=4.5) is False


def test_brief_dip_below_threshold_does_not_flip_to_false():
    """Vocal-active state survives a brief dip — the out_dwell timer resets
    when above-threshold returns."""
    vd = VocalDetector()
    recent = [{"mid_share": 0.50}, {"mid_share": 0.50}]
    # Ramp up to True
    vd.is_vocal_section(_above_rules1_3_feats(), recent, now=0.0)
    vd.is_vocal_section(_above_rules1_3_feats(), recent, now=1.5)
    assert vd._active is True

    # Brief 1s dip at t=2.0
    assert vd.is_vocal_section(_below_feats(), [], now=2.0) is True
    # Back above-threshold at t=2.5 — _below_since resets to None
    assert vd.is_vocal_section(_above_rules1_3_feats(), recent, now=2.5) is True
    # Even at t=5.0 (would-have-been past 2.5s), still True
    assert vd.is_vocal_section(_above_rules1_3_feats(), recent, now=5.0) is True


def test_rule1_requires_sustained_mid_not_just_current():
    """If current mid is high but recent_features show low mids, rule1 does
    NOT fire — only sustained mid passes."""
    vd = VocalDetector()
    # current mid=0.50 but recent are low → rule1 should NOT fire on its own
    features = {"mid_share": 0.50, "high_share": 0.05, "sub_share": 0.50, "onsets_per_sec": 1.0}
    recent = [{"mid_share": 0.10}, {"mid_share": 0.10}]
    # rule3 fails (high_share=0.05 < 0.20). rule1 needs sustained → fails.
    # Only rule1 wants to fire, fails → stays False even after long elapsed.
    for t in [0.0, 1.0, 2.0, 3.0]:
        assert vd.is_vocal_section(features, recent, now=t) is False


def test_rule2_rising_onsets_alone_below_threshold():
    """Only rule2 fires → 1-of-3 → below threshold."""
    vd = VocalDetector()
    features = {"mid_share": 0.10, "high_share": 0.05, "sub_share": 0.40, "onsets_per_sec": 4.0}
    recent = [{"onsets_per_sec": 1.0}, {"onsets_per_sec": 2.0}]
    # rule2 fires (1.0<2.0<4.0), rule1 fails, rule3 fails. → below threshold.
    for t in [0.0, 1.0, 2.0]:
        assert vd.is_vocal_section(features, recent, now=t) is False


def test_rule2_plus_rule3_flips_after_dwell():
    """rules 2+3 fire → above threshold → after 1.5s, flips True."""
    vd = VocalDetector()
    features = {"mid_share": 0.10, "high_share": 0.25, "sub_share": 0.20, "onsets_per_sec": 4.0}
    recent = [{"onsets_per_sec": 1.0}, {"onsets_per_sec": 2.0}]
    # rule2 fires (1<2<4), rule3 fires → 2-of-3 → above
    assert vd.is_vocal_section(features, recent, now=0.0) is False
    assert vd.is_vocal_section(features, recent, now=1.5) is True


def test_active_state_survives_brief_recent_features_empty():
    """If recent_features is briefly empty but current still trips 2-of-3,
    state stays active."""
    vd = VocalDetector()
    recent = [{"mid_share": 0.50}, {"mid_share": 0.50}]
    vd.is_vocal_section(_above_rules1_3_feats(), recent, now=0.0)
    vd.is_vocal_section(_above_rules1_3_feats(), recent, now=1.5)
    assert vd._active is True

    # recent_features empty — only rule3 fires alone. Below threshold → out timer starts.
    # But at the same tick the timer just started; not 2.5s elapsed → stays True.
    assert vd.is_vocal_section(_rule3_only_feats(), [], now=1.6) is True


def test_constructor_dwell_override():
    """Custom in_dwell_sec allows faster flip."""
    vd = VocalDetector(in_dwell_sec=0.5)
    recent = [{"mid_share": 0.50}, {"mid_share": 0.50}]
    vd.is_vocal_section(_above_rules1_3_feats(), recent, now=0.0)
    # 0.5s elapsed → flip True with the override
    assert vd.is_vocal_section(_above_rules1_3_feats(), recent, now=0.5) is True


def test_profile_passed_but_not_required_for_heuristics():
    """v1 heuristics are genre-agnostic; profile parameter is reserved."""
    vd_no_prof = VocalDetector()
    vd_with_prof = VocalDetector(profile=load_profile("pop"))
    # Identical inputs → identical outputs.
    recent = [{"mid_share": 0.50}, {"mid_share": 0.50}]
    a = vd_no_prof.is_vocal_section(_above_rules1_3_feats(), recent, now=2.0)
    b = vd_with_prof.is_vocal_section(_above_rules1_3_feats(), recent, now=2.0)
    assert a == b


def test_now_defaults_to_time_time(monkeypatch):
    """When ``now`` is omitted, time.time() is used."""
    import vibemix.state.genre.vocal_detector as mod

    fake_now = [100.0]

    def _fake_time():
        return fake_now[0]

    monkeypatch.setattr(mod.time, "time", _fake_time)
    vd = VocalDetector()
    recent = [{"mid_share": 0.50}, {"mid_share": 0.50}]
    # First call at t=100; _above_since=100
    vd.is_vocal_section(_above_rules1_3_feats(), recent)
    fake_now[0] = 101.6  # 1.6s elapsed > 1.5s dwell
    assert vd.is_vocal_section(_above_rules1_3_feats(), recent) is True
