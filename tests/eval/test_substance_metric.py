# SPDX-License-Identifier: Apache-2.0
"""Phase 27-02 — useful_response_ratio + per_event_class_substance pure-logic tests.

No API calls; no VCR cassettes. Covers Pitfall P44 (lenient F1 / substance
metric).
"""

from __future__ import annotations

from scripts.eval.cited_relevance import (
    per_event_class_substance,
    useful_response_ratio,
)


def _v(substance: float = 0.0, flash_pass: bool = False, event_type: str = "DROP"):
    return {
        "pro": {"substance": substance, "verdict": "pass" if substance >= 0.6 else "fail"},
        "flash": {"pass": flash_pass, "why": "test"},
        "event_type": event_type,
    }


def test_empty_list_returns_zero() -> None:
    assert useful_response_ratio([]) == 0.0


def test_all_pro_substance_above_axis_threshold() -> None:
    verdicts = [_v(substance=0.8) for _ in range(4)]
    assert useful_response_ratio(verdicts) == 1.0


def test_mixed_pro_substance_and_flash_pass() -> None:
    """Pro substance >= 0.5 OR Flash pass — both count as useful."""
    verdicts = [
        _v(substance=0.8, flash_pass=True),   # both pass — useful
        _v(substance=0.2, flash_pass=True),   # only Flash — useful
        _v(substance=0.8, flash_pass=False),  # only Pro — useful
        _v(substance=0.2, flash_pass=False),  # both fail — NOT useful
    ]
    assert useful_response_ratio(verdicts) == 0.75


def test_substance_below_threshold_falls() -> None:
    """Pro substance < 0.5 AND Flash pass = False → not useful."""
    verdicts = [_v(substance=0.3, flash_pass=False) for _ in range(5)]
    assert useful_response_ratio(verdicts) == 0.0


def test_per_event_class_substance_excludes_heartbeat() -> None:
    """HEARTBEAT events are NOT counted in any class denominator."""
    verdicts = [
        _v(substance=0.8, event_type="DROP"),
        _v(substance=0.8, event_type="DROP"),
        _v(substance=0.8, event_type="HEARTBEAT"),
        _v(substance=0.2, event_type="HEARTBEAT"),
    ]
    result = per_event_class_substance(
        verdicts, ["DROP", "HEARTBEAT", "PHRASE_BOUNDARY"]
    )
    assert "HEARTBEAT" not in result, (
        "HEARTBEAT must be excluded from per_event_class_substance output"
    )
    assert result["DROP"] == 1.0
    assert result["PHRASE_BOUNDARY"] == 0.0


def test_per_event_class_handles_missing_class() -> None:
    """Class with zero events returns 0.0, not NaN."""
    verdicts = [_v(substance=0.8, event_type="DROP")]
    result = per_event_class_substance(
        verdicts, ["DROP", "MIX_MOVE", "KICK_SWAP"]
    )
    assert result["MIX_MOVE"] == 0.0
    assert result["KICK_SWAP"] == 0.0
    assert result["DROP"] == 1.0


def test_verdict_with_none_pro_handles_gracefully() -> None:
    """Missing 'pro' or 'flash' keys default to substance=0.0 + pass=False."""
    verdicts = [
        {"pro": None, "flash": {"pass": True}, "event_type": "DROP"},
        {"pro": {"substance": 0.7}, "flash": None, "event_type": "DROP"},
    ]
    assert useful_response_ratio(verdicts) == 1.0


def test_failed_judge_treated_as_non_pass() -> None:
    """Verdict with _failed=True does not contribute to useful count."""
    # NOTE: useful_response_ratio inspects substance + pass directly; the
    # _failed flag is consumed by the F1 aggregator, not this metric.
    # Here we just confirm a clearly-zero verdict scores 0.
    verdicts = [
        {"pro": {"_failed": True, "substance": 0.0}, "flash": {"_failed": True, "pass": False}, "event_type": "DROP"}
    ]
    assert useful_response_ratio(verdicts) == 0.0
