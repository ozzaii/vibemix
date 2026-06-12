"""The free-Sven pool-replay gate (measurement protocol instrument #1).

Replays the 123 judged cadence-pool lines through the working-tree boundary
disposition and pins the architecture's contract: ZERO judge-liked lines
silenced, the hard fabrication classes still caught, the state
reconstruction oracle-exact, and no canned HELD reply ever speakable.

Released fabrications are itemized by design (E.1 soft-tier demotions R1/R3/
R5 + the A.6 rose-delta escape, whose 3 released lines are evidence-twins of
a judged keeper); a drop in fabrication holds BELOW the pinned floor means a
hard guard regressed.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location(
    "guard_pool_replay", REPO / "scripts" / "eval" / "guard_pool_replay.py"
)
assert _SPEC is not None and _SPEC.loader is not None
guard_pool_replay = importlib.util.module_from_spec(_SPEC)
sys.modules.setdefault("guard_pool_replay", guard_pool_replay)
_SPEC.loader.exec_module(guard_pool_replay)


@pytest.fixture(scope="module")
def report() -> dict:
    rows = guard_pool_replay.load_pool_rows()
    if len(rows) < 100:
        pytest.skip(f"judged cadence pools not present ({len(rows)} rows)")
    return guard_pool_replay.replay(rows)


def test_reconstruction_matches_recorded_policy_oracle(report: dict) -> None:
    assert report["policy_mismatches"] == []


def test_zero_silenced_keepers(report: dict) -> None:
    """The headline: no judge-liked line is ever silenced (was 3 pre-A)."""
    assert report["totals"]["silencedKeepers"] == 0
    assert report["totals"]["keeperHolds"] == 0


def test_hard_fabrication_floor_holds(report: dict) -> None:
    """The hard tier keeps catching judged fabrications (17 at ship time:
    10 event-witness, 6 spectral, 1 source-detail trim)."""
    assert report["totals"]["fabricationHolds"] >= 17
    per = report["per_policy"]
    assert per.get("event_witness_not_offered", {}).get("fabricationHolds", 0) >= 10
    assert per.get("spectral_claim_not_audible", {}).get("fabricationHolds", 0) >= 6


def test_no_canned_reply_is_ever_speakable(report: dict) -> None:
    assert report["totals"]["cannedSpeakable"] == []


def test_soft_tier_releases_ride_telemetry(report: dict) -> None:
    """The demoted detections stay measurable: spoken rows carry
    observations so the >20% judge-flag tripwire has data to read."""
    assert report["totals"]["observationRows"] >= 5
    released_with_obs = [
        r for r in report["rows"]
        if r["ok"] is False and not r["held"] and r["observations"]
    ]
    assert released_with_obs, "E.1 demotions must surface as observations"
