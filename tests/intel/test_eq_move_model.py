# SPDX-License-Identifier: Apache-2.0
"""Clean-room EQ move response predictor tests."""

from __future__ import annotations

from vibemix.audio.band_features import _BANDS
from vibemix.intel.eq_move_model import BAND_WINDOWS, canonical_eq_move, predicted_band_gains


def test_predicted_band_gains_match_band_feature_windows() -> None:
    assert BAND_WINDOWS == _BANDS
    assert set(predicted_band_gains("low_kill", 48_000)) == {"sub", "low", "mid", "high"}


def test_low_kill_predicts_bass_bands_fall() -> None:
    gains = predicted_band_gains("low_kill", 48_000)

    assert gains["sub"] < -8.0
    assert gains["low"] < -3.0
    assert abs(gains["high"]) < 1.0


def test_high_kill_predicts_high_band_falls() -> None:
    gains = predicted_band_gains("high_kill", 48_000)

    assert gains["high"] < -8.0
    assert gains["sub"] > -1.0


def test_low_boost_predicts_bass_bands_rise() -> None:
    gains = predicted_band_gains("low_boost", 48_000)

    assert gains["sub"] > 3.0
    assert gains["low"] > 2.0


def test_filter_sweeps_predict_their_edge_loss() -> None:
    hp = predicted_band_gains("filter_hp", 48_000)
    lp = predicted_band_gains("filter_lp", 48_000)

    assert hp["sub"] < -3.0
    assert lp["high"] < -3.0


def test_raw_move_labels_canonicalize_and_unknown_abstains() -> None:
    assert canonical_eq_move("A_low: flat→killed (big twist)") == "low_kill"
    assert canonical_eq_move("B_hi: flat->boosted") == "high_boost"
    assert canonical_eq_move("A_filter: high-pass sweep") == "filter_hp"
    assert predicted_band_gains("xfader->center", 48_000) == {}
