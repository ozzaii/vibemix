# SPDX-License-Identifier: Apache-2.0
"""Phase 27-01 — scorecard render tests (pure-function, no I/O)."""

from __future__ import annotations

from scripts.eval.scorecard import render_scorecard


def _mk_session(
    *,
    sid: str = "s1",
    genre: str = "techno",
    f1: float = 1.0,
    useful: float = 0.8,
    bypass: float = 0.05,
    predicted=None,
    ground_truth=None,
    verdicts=None,
) -> dict:
    return {
        "session": sid,
        "genre": genre,
        "skipped": False,
        "predicted_events": predicted
        or [{"id": "p1", "type": "TRACK_CHANGE", "t_session": 1.0, "session": sid}],
        "ground_truth": ground_truth
        or [{"id": "g1", "type": "TRACK_CHANGE", "t_session": 1.0, "session": sid}],
        "f1": {"f1": f1, "precision": f1, "recall": f1},
        "verdicts": verdicts or [{"event_id": "g1", "pro": {"verdict": "pass"}}],
        "useful_response_ratio": useful,
        "bypass_rate": bypass,
        "per_event_substance": [0.7],
    }


THRESHOLDS = {
    "f1_min": 0.80,
    "substance_min": 0.65,
    "cited_cosine_min": 0.4,
    "bypass_max": 0.15,
    "per_genre_f1_min": 0.70,
}


def test_render_scorecard_returns_md_and_data_tuple() -> None:
    md, data = render_scorecard([_mk_session()], THRESHOLDS)
    assert isinstance(md, str)
    assert isinstance(data, dict)
    assert "phase" in data
    assert "thresholds" in data
    assert "sessions" in data


def test_scorecard_md_contains_required_sections() -> None:
    md, _ = render_scorecard([_mk_session()], THRESHOLDS)
    assert "# vibemix Eval Scorecard" in md
    assert "## Threshold Status" in md
    assert "## Per-Detector-Per-Genre F1 Matrix" in md
    assert "## Per-Session Results" in md


def test_scorecard_per_genre_matrix_present_with_single_genre() -> None:
    """Pitfall P43: matrix MUST render even when only 1 genre is in the corpus."""
    md, data = render_scorecard([_mk_session(genre="techno")], THRESHOLDS)
    assert "techno" in md
    matrix = data.get("per_detector_per_genre", {})
    assert "TRACK_CHANGE" in matrix
    assert "techno" in matrix["TRACK_CHANGE"]


def test_scorecard_threshold_status_pass_path() -> None:
    """Threshold status rows for a clean happy path are all PASS."""
    md, data = render_scorecard([_mk_session()], THRESHOLDS)
    status = data["threshold_status"]
    statuses = {row["metric"]: row["status"] for row in status}
    # Note: cited_cosine is "deferred" in Plan 27-01 (Plan 02 supplies real value);
    # default 0.0 < 0.4 → FAIL is expected; that's the deferred-on-purpose row.
    assert statuses["min(pro_f1, flash_f1)"] == "PASS"
    assert statuses["useful_response_ratio"] == "PASS"
    assert statuses["bypass_rate"] == "PASS"


def test_scorecard_session_threshold_failure_marked() -> None:
    bad = _mk_session(f1=0.5, useful=0.3, bypass=0.5)
    _, data = render_scorecard([bad], THRESHOLDS)
    sess = data["sessions"][0]
    assert sess["threshold_pass"] is False
    assert len(sess["threshold_failures"]) >= 1


def test_scorecard_no_response_text_in_data() -> None:
    """T-27-01-01: scorecard data must NEVER contain raw response text."""
    sess = _mk_session()
    md, data = render_scorecard([sess], THRESHOLDS)
    serialized = repr(data)
    assert "responses/" not in serialized
    # Also: no AIza tokens leak (defensive scan).
    assert "AIza" not in serialized
    assert "AIza" not in md


def test_scorecard_empty_results_renders_without_error() -> None:
    md, data = render_scorecard([], THRESHOLDS)
    assert "no sessions" in md.lower()
    assert data["sessions"] == []


def test_scorecard_skipped_session_rendered_as_skipped() -> None:
    s = _mk_session()
    s["skipped"] = True
    s["reason"] = "too big"
    md, data = render_scorecard([s], THRESHOLDS)
    assert "SKIPPED" in md
    sess = data["sessions"][0]
    assert sess["skipped"] is True
