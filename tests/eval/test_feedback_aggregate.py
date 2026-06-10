# SPDX-License-Identifier: Apache-2.0
"""Unit coverage for the deterministic cross-session feedback aggregator."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.eval.feedback_aggregate import aggregate, load_reviews, render_markdown


def _review(session: str, persona: str, *, annoyances, score=5, parked=False) -> dict:
    review = (
        {"error": "429 parked"}
        if parked
        else {
            "overall_feeling": "fine",
            "would_use_again_0_10": score,
            "top_annoyances": annoyances,
            "top_likes": [{"what": "the one drop call was on time", "evidence_t": 120}],
            "change_one_thing": "speak more during builds",
        }
    )
    return {
        "schema": "vibemix_session_review_v1",
        "session_name": session,
        "persona": persona,
        "stats": {
            "time_to_first_line_s": 40.0,
            "longest_silence_s": 180.0,
            "spoken_lines": 0 if parked else 3,
            "gated_silent": 5,
            "max_latency_s": 4.2,
        },
        "review": review,
    }


def test_aggregate_ranks_complaints_by_frequency(tmp_path: Path) -> None:
    docs = [
        _review("s1", "beginner", annoyances=[{"category": "silence", "what": "nothing for 3 min"}]),
        _review("s2", "pro", annoyances=[
            {"category": "silence", "what": "dead air through the build"},
            {"category": "repetition", "what": "same line twice"},
        ]),
        _review("s3", "pro", annoyances=[{"category": "silence", "what": "quiet again"}], score=2),
        _review("s4", "beginner", annoyances=[], parked=True),
    ]
    report = aggregate(docs)

    assert report["objective"]["reviews_total"] == 4
    assert report["objective"]["reviews_scored"] == 3
    assert report["objective"]["reviews_parked"] == 1
    top = report["complaints_ranked"][0]
    assert top["category"] == "silence"
    assert top["complaints"] == 3
    assert top["distinct_sessions"] == 3
    assert report["would_use_again_by_persona"]["pro"]["mean"] == 3.5
    assert report["objective"]["sessions_fully_silent"] == 1

    md = render_markdown(report, "test report")
    assert "silence — 3 complaints" in md
    assert "Parked reviews (1)" in md


def test_load_reviews_skips_foreign_json(tmp_path: Path) -> None:
    good = tmp_path / "a.json"
    good.write_text(json.dumps(_review("s1", "pro", annoyances=[])), encoding="utf-8")
    (tmp_path / "junk.json").write_text(json.dumps({"schema": "other"}), encoding="utf-8")
    (tmp_path / "broken.json").write_text("{nope", encoding="utf-8")

    docs = load_reviews(sorted(tmp_path.glob("*.json")))
    assert len(docs) == 1
    assert docs[0]["session_name"] == "s1"
