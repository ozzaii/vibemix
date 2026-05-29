# SPDX-License-Identifier: Apache-2.0
"""Focused contracts for the Learn/Course 3 auto-master finder."""

from __future__ import annotations

from scripts import learn_live_readiness as readiness
from scripts import run_learn_live_proof as runner


def test_auto_master_recommendation_exposes_ranked_candidate_evidence() -> None:
    recommendation = readiness.recommend_auto_master_input(
        capture_matrix_check={
            "enabled": True,
            "ok": True,
            "top_signal": {
                "name": "rekordbox Aggregate Device",
                "rms": 0.021,
                "peak": 0.19,
                "sample_rate": 44100,
                "signal": True,
            },
            "rows": [
                {
                    "name": "BlackHole 16ch",
                    "rms": 0.0,
                    "peak": 0.0,
                    "sample_rate": 48000,
                    "signal": False,
                },
                {
                    "name": "rekordbox Aggregate Device",
                    "rms": 0.021,
                    "peak": 0.19,
                    "sample_rate": 44100,
                    "signal": True,
                },
            ],
        },
        rekordbox_audio_settings_check={
            "current": {
                "audio_output_device_name": "BlackHole 16ch",
                "audio_device_rate": "48000.0",
            }
        },
        audio_route_check={"output_device": "BlackHole 16ch"},
    )

    assert recommendation["ok"] is False
    assert recommendation["status"] == "needs_rate_fix"
    assert recommendation["reason"] == "live_signal_rate_mismatch"
    candidates = recommendation["candidates"]
    assert candidates[0]["name"] == "rekordbox Aggregate Device"
    assert candidates[0]["live_signal"] is True
    assert candidates[0]["sample_rate"] == 44100
    assert "live_signal" in candidates[0]["reasons"]
    assert candidates[1]["name"] == "BlackHole 16ch"
    assert candidates[1]["rate_ok"] is True
    assert "saved_rekordbox_route" in candidates[1]["reasons"]
    assert "macos_output_route" in candidates[1]["reasons"]
    assert "silent_48k_loopback_fallback" in candidates[1]["reasons"]


def test_auto_master_recommendation_keeps_unsampled_saved_route_honest() -> None:
    recommendation = readiness.recommend_auto_master_input(
        capture_matrix_check=None,
        rekordbox_audio_settings_check={
            "current": {
                "audio_output_device_name": "BlackHole 2ch",
                "audio_device_rate": "48000.0",
            }
        },
    )

    assert recommendation["source"] == "rekordbox_audio_settings"
    assert recommendation["reason"] == "saved_loopback_route"
    candidate = recommendation["candidates"][0]
    assert candidate["name"] == "BlackHole 2ch"
    assert candidate["sampled"] is False
    assert "unsampled_route" in candidate["reasons"]


def test_live_proof_auto_master_plan_rejects_rate_mismatch_before_startup() -> None:
    readiness_before = {
        "auto_master_recommendation": {
            "ok": False,
            "source": "rekordbox_audio_settings",
            "reason": "saved_loopback_rate_mismatch",
            "device_name": "BlackHole 2ch",
            "sample_rate": 44100,
            "live_signal": False,
            "candidates": [
                {
                    "name": "BlackHole 2ch",
                    "sample_rate": 44100,
                    "rank": 1,
                    "sampled": True,
                }
            ],
        },
        "checks": {
            "rekordbox_audio_settings": {
                "current": {"audio_output_device_name": "BlackHole 2ch"}
            },
            "capture_matrix": {
                "rows": [
                    {"name": "BlackHole 2ch", "sample_rate": 44100},
                    {"name": "BlackHole 16ch", "sample_rate": 48000},
                ]
            },
        },
    }

    plan = runner.resolve_app_audio_env(
        input_device=None,
        output_device=None,
        mic_device=None,
        auto_master_input=True,
        readiness_before=readiness_before,
    )

    assert plan["auto_master_fallback_device"] is None
    assert plan["auto_master_fallback_candidate"]["name"] == "BlackHole 2ch"
    assert "44100Hz" in plan["auto_master_fallback_rejected_reason"]
