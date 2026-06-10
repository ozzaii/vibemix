#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""feedback_aggregate.py — cross-session feedback report from session reviews.

The missing half of the simulated-DJ-fleet harvest: ``session_review.py``
produces one JSON per (session, persona) with a deterministic ``stats`` block
and a persona-voiced ``review`` whose complaints use a FIXED category enum.
This aggregator ingests N of those JSONs and ranks failure modes by frequency —
"31 of 36 simulated DJs complained about silence" — with exemplar quotes,
per-persona breakdowns, and objective stat medians. Deterministic and keyless:
no LLM, plain counting, so the report is reproducible from the same inputs.

Usage:
    uv run --no-sync python scripts/eval/feedback_aggregate.py \
        --reviews ".planning/eval-runs/<wave>/reviews" \
        --out-md report.md --out-json report.json
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def load_reviews(paths: list[Path]) -> list[dict[str, Any]]:
    docs: list[dict[str, Any]] = []
    for path in paths:
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(doc, dict) and doc.get("schema") == "vibemix_session_review_v1":
            doc["_path"] = str(path)
            docs.append(doc)
    return docs


def _median(values: list[float]) -> float | None:
    return round(statistics.median(values), 1) if values else None


def aggregate(docs: list[dict[str, Any]]) -> dict[str, Any]:
    parked = [d for d in docs if not isinstance(d.get("review"), dict) or d["review"].get("error")]
    scored = [d for d in docs if d not in parked]

    complaint_count: Counter[str] = Counter()
    complaint_sessions: dict[str, set[str]] = defaultdict(set)
    complaint_examples: dict[str, list[dict[str, Any]]] = defaultdict(list)
    likes: list[dict[str, Any]] = []
    scores_by_persona: dict[str, list[int]] = defaultdict(list)
    change_one_thing: list[dict[str, str]] = []

    for d in scored:
        review = d["review"]
        who = f"{d.get('persona')}@{d.get('session_name')}"
        for a in review.get("top_annoyances") or []:
            if not isinstance(a, dict):
                continue
            cat = str(a.get("category", "other")).strip().lower()
            complaint_count[cat] += 1
            complaint_sessions[cat].add(str(d.get("session_name")))
            if len(complaint_examples[cat]) < 4:
                complaint_examples[cat].append(
                    {"who": who, "what": a.get("what"), "evidence_t": a.get("evidence_t")}
                )
        for like in review.get("top_likes") or []:
            if isinstance(like, dict) and like.get("what"):
                likes.append({"who": who, "what": like["what"]})
        score = review.get("would_use_again_0_10")
        if isinstance(score, (int, float)):
            scores_by_persona[str(d.get("persona"))].append(int(score))
        if review.get("change_one_thing"):
            change_one_thing.append({"who": who, "change": str(review["change_one_thing"])})

    all_stats = [d.get("stats") or {} for d in docs]

    def stat_values(key: str) -> list[float]:
        return [float(s[key]) for s in all_stats if isinstance(s.get(key), (int, float))]

    n_sessions = len({d.get("session_name") for d in docs})
    objective = {
        "reviews_total": len(docs),
        "reviews_scored": len(scored),
        "reviews_parked": len(parked),
        "distinct_sessions": n_sessions,
        "median_time_to_first_line_s": _median(stat_values("time_to_first_line_s")),
        "median_longest_silence_s": _median(stat_values("longest_silence_s")),
        "median_spoken_lines": _median(stat_values("spoken_lines")),
        "median_gated_silent": _median(stat_values("gated_silent")),
        "max_latency_s": max(stat_values("max_latency_s"), default=None),
        "sessions_fully_silent": sum(1 for s in all_stats if s.get("spoken_lines") == 0),
    }

    complaints_ranked = [
        {
            "category": cat,
            "complaints": count,
            "reviews_pct": round(100 * count / max(1, len(scored)), 1),
            "distinct_sessions": len(complaint_sessions[cat]),
            "examples": complaint_examples[cat],
        }
        for cat, count in complaint_count.most_common()
    ]

    return {
        "schema": "vibemix_feedback_report_v1",
        "objective": objective,
        "complaints_ranked": complaints_ranked,
        "would_use_again_by_persona": {
            persona: {"mean": round(sum(vals) / len(vals), 1), "n": len(vals)}
            for persona, vals in sorted(scores_by_persona.items())
        },
        "likes": likes[:20],
        "change_one_thing": change_one_thing[:20],
        "parked": [
            {
                "path": d.get("_path") or d.get("session_name"),
                "error": (d.get("review") or {}).get("error"),
            }
            for d in parked
        ],
    }


def render_markdown(report: dict[str, Any], title: str) -> str:
    o = report["objective"]
    lines = [
        f"# {title}",
        "",
        f"{o['reviews_total']} persona-reviews over {o['distinct_sessions']} sessions "
        f"({o['reviews_scored']} scored, {o['reviews_parked']} parked).",
        "",
        "## What the fleet experienced (objective)",
        f"- Median time to first spoken line: **{o['median_time_to_first_line_s']}s**",
        f"- Median longest silence: **{o['median_longest_silence_s']}s**",
        f"- Median spoken lines per session: **{o['median_spoken_lines']}** "
        f"(median {o['median_gated_silent']} reactions gated to silence)",
        f"- Sessions with ZERO speech: **{o['sessions_fully_silent']}**",
        f"- Worst line latency: **{o['max_latency_s']}s**",
        "",
        "## Complaints ranked by frequency",
        "",
    ]
    for c in report["complaints_ranked"]:
        lines.append(
            f"### {c['category']} — {c['complaints']} complaints "
            f"({c['reviews_pct']}% of reviews, {c['distinct_sessions']} sessions)"
        )
        for ex in c["examples"]:
            t = f" (t≈{ex['evidence_t']}s)" if ex.get("evidence_t") is not None else ""
            lines.append(f"- *{ex['who']}*{t}: {ex['what']}")
        lines.append("")
    lines.append("## Would use again (0-10) by persona")
    for persona, v in report["would_use_again_by_persona"].items():
        lines.append(f"- **{persona}**: {v['mean']} (n={v['n']})")
    if report["likes"]:
        lines += ["", "## What landed"]
        lines += [f"- *{like['who']}*: {like['what']}" for like in report["likes"][:10]]
    if report["change_one_thing"]:
        lines += ["", "## \"Change one thing\""]
        lines += [f"- *{c['who']}*: {c['change']}" for c in report["change_one_thing"][:10]]
    if report["parked"]:
        lines += ["", f"## Parked reviews ({len(report['parked'])}) — no scores fabricated"]
        lines += [f"- `{p['path']}`: {p['error']}" for p in report["parked"]]
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reviews", required=True, help="dir of *.json reviews (or a single file)")
    ap.add_argument("--out-md", default=None)
    ap.add_argument("--out-json", default=None)
    ap.add_argument("--title", default="Simulated-DJ fleet feedback report")
    args = ap.parse_args()

    root = Path(args.reviews).expanduser()
    paths = sorted(root.glob("*.json")) if root.is_dir() else [root]
    docs = load_reviews(paths)
    if not docs:
        print(f"FAIL: no vibemix_session_review_v1 docs under {root}", file=sys.stderr)
        return 2

    report = aggregate(docs)
    md = render_markdown(report, args.title)
    if args.out_json:
        out = Path(args.out_json).expanduser()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    if args.out_md:
        out = Path(args.out_md).expanduser()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(md)
    print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
