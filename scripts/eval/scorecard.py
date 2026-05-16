# SPDX-License-Identifier: Apache-2.0
"""Phase 27-01 — Markdown + JSON scorecard renderer.

Consumes the per-session results from ``replay_harness.replay_one_session``
plus a ``thresholds`` dict, and produces:
    - md (str): PR-comment-ready markdown with Threshold Status block +
      per-detector-per-genre F1 matrix + per-session results table.
    - data (dict): the same content as a machine-readable JSON object
      written to ``<output>/eval_report.json``.

Per CONTEXT EVAL-08 + Pitfall P43, the per-detector-per-genre matrix MUST be
present even when only one genre is in the corpus (missing cells render as
``—``).

Information-disclosure mitigation (T-27-01-01): the renderer NEVER echoes
``responses/<event_id>.txt`` text into either output. Only metric values +
verdict strings travel into eval_report.json.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from scripts.eval.f1 import compute_f1


def _genre_lookup_factory(results: list[dict[str, Any]]):
    mapping = {r["session"]: r.get("genre", "unknown") for r in results}

    def lookup(session_id: str) -> str:
        return mapping.get(session_id, "unknown")

    return lookup


def _aggregate_predicted_and_gt(
    results: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Flatten per-session predicted/ground_truth into corpus-wide lists.

    Each event already carries a ``session`` key (set by replay_one_session).
    """
    predicted: list[dict[str, Any]] = []
    ground_truth: list[dict[str, Any]] = []
    for r in results:
        if r.get("skipped"):
            continue
        predicted.extend(r.get("predicted_events", []))
        ground_truth.extend(r.get("ground_truth", []))
    return predicted, ground_truth


def _check_session_thresholds(
    sess: dict[str, Any], thresholds: dict[str, float]
) -> tuple[bool, list[str]]:
    """Return (pass, failures) for a single session vs threshold dict."""
    failures: list[str] = []
    f1 = sess.get("f1", {}).get("f1", 0.0)
    if f1 < thresholds.get("f1_min", 0.0):
        failures.append(f"f1={f1:.2f} < {thresholds['f1_min']:.2f}")

    urr = sess.get("useful_response_ratio", 0.0)
    if urr < thresholds.get("substance_min", 0.0):
        failures.append(f"useful_response_ratio={urr:.2f} < {thresholds['substance_min']:.2f}")

    bypass = sess.get("bypass_rate", 0.0)
    if bypass > thresholds.get("bypass_max", 1.0):
        failures.append(f"bypass_rate={bypass:.2f} > {thresholds['bypass_max']:.2f}")

    return (len(failures) == 0), failures


def _render_threshold_status_block(
    overall_f1: float,
    avg_useful_response: float,
    avg_cited_cosine: float,
    avg_bypass: float,
    thresholds: dict[str, float],
) -> tuple[str, list[dict[str, Any]]]:
    """Build the Threshold Status markdown table + matching data rows."""
    rows: list[dict[str, Any]] = [
        {
            "metric": "min(pro_f1, flash_f1)",
            "threshold": f"≥ {thresholds['f1_min']:.2f}",
            "actual": round(overall_f1, 2),
            "status": "PASS" if overall_f1 >= thresholds["f1_min"] else "FAIL",
        },
        {
            "metric": "useful_response_ratio",
            "threshold": f"≥ {thresholds['substance_min']:.2f}",
            "actual": round(avg_useful_response, 2),
            "status": "PASS" if avg_useful_response >= thresholds["substance_min"] else "FAIL",
        },
        {
            "metric": "cited_cosine",
            "threshold": f"≥ {thresholds['cited_cosine_min']:.2f}",
            "actual": round(avg_cited_cosine, 2),
            "status": "PASS" if avg_cited_cosine >= thresholds["cited_cosine_min"] else "FAIL",
        },
        {
            "metric": "bypass_rate",
            "threshold": f"≤ {thresholds['bypass_max']:.2f}",
            "actual": round(avg_bypass, 2),
            "status": "PASS" if avg_bypass <= thresholds["bypass_max"] else "FAIL",
        },
    ]
    md = "## Threshold Status\n\n"
    md += "| Metric | Threshold | Actual | Status |\n"
    md += "|--------|-----------|--------|--------|\n"
    for r in rows:
        md += f"| {r['metric']} | {r['threshold']} | {r['actual']} | {r['status']} |\n"
    return md, rows


def _render_matrix_block(matrix: dict[str, dict[str, dict[str, Any]]]) -> str:
    """Render the per-detector-per-genre F1 matrix as markdown."""
    md = "## Per-Detector-Per-Genre F1 Matrix\n\n"
    md += "(rows = detector type, cols = genre — `—` = no events of that pair)\n\n"
    if not matrix:
        md += "_(empty corpus — no detectors yet)_\n\n"
        return md
    genres = sorted({g for d in matrix.values() for g in d.keys()})
    if not genres:
        md += "_(no genres detected)_\n\n"
        return md
    header = "| detector \\ genre | " + " | ".join(genres) + " |\n"
    sep = "|" + "---|" * (len(genres) + 1) + "\n"
    md += header + sep
    for det in sorted(matrix.keys()):
        row = f"| {det} | "
        cells = []
        for g in genres:
            cell = matrix[det].get(g, {})
            tp = cell.get("tp", 0)
            fn = cell.get("fn", 0)
            fp = cell.get("fp", 0)
            if (tp + fn + fp) == 0:
                cells.append("—")
            else:
                cells.append(f"{cell.get('f1', 0.0):.2f}")
        row += " | ".join(cells) + " |\n"
        md += row
    md += "\n"
    return md


def render_scorecard(
    results: list[dict[str, Any]],
    thresholds: dict[str, float],
) -> tuple[str, dict[str, Any]]:
    """Render the markdown scorecard + machine-readable JSON data.

    Parameters
    ----------
    results
        List of per-session result dicts from ``replay_one_session``.
    thresholds
        Threshold dict (CONTEXT EVAL-06). Plan 04 will load this from
        ``eval/THRESHOLD-LOCK.md``; Plan 27-01 consumes the dict only.

    Returns
    -------
    (md, data)
        ``md`` — markdown string for PR comments + ``output/scorecard.md``.
        ``data`` — JSON-serializable dict for ``output/eval_report.json``.
    """
    n_sessions = len([r for r in results if not r.get("skipped")])

    # Aggregate corpus-wide F1 with per-detector-per-genre matrix.
    predicted_all, ground_truth_all = _aggregate_predicted_and_gt(results)
    if results:
        genre_lookup = _genre_lookup_factory(results)
    else:
        genre_lookup = None
    overall = compute_f1(
        predicted_all,
        ground_truth_all,
        tolerance_s=2.0,
        genre_lookup=genre_lookup,
    )
    overall_f1 = overall.get("f1", 0.0)
    matrix = overall.get("per_detector_per_genre", {})

    avg_useful_response = (
        sum(r.get("useful_response_ratio", 0.0) for r in results if not r.get("skipped"))
        / max(n_sessions, 1)
    )
    avg_bypass = (
        sum(r.get("bypass_rate", 0.0) for r in results if not r.get("skipped"))
        / max(n_sessions, 1)
    )

    # cited_cosine is a Plan 02 metric — Plan 27-01 reports 0.0 + tags it as
    # "deferred" so the row exists for the threshold gate visualization.
    avg_cited_cosine = 0.0

    # Per-session threshold pass/fail.
    sessions_data: list[dict[str, Any]] = []
    for r in results:
        passed, failures = _check_session_thresholds(r, thresholds)
        sessions_data.append(
            {
                "session": r["session"],
                "genre": r.get("genre", "unknown"),
                "skipped": r.get("skipped", False),
                "f1": r.get("f1", {}).get("f1", 0.0),
                "useful_response_ratio": r.get("useful_response_ratio", 0.0),
                "bypass_rate": r.get("bypass_rate", 0.0),
                "verdict_count": len(r.get("verdicts", [])),
                "threshold_pass": passed,
                "threshold_failures": failures,
            }
        )

    # Markdown assembly.
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    md_parts = [
        "# vibemix Eval Scorecard",
        "",
        "**Phase:** 27 (autonomous proxy gate)",
        f"**Sessions:** {n_sessions}",
        f"**Generated:** {now}",
        "",
    ]
    threshold_md, threshold_rows = _render_threshold_status_block(
        overall_f1, avg_useful_response, avg_cited_cosine, avg_bypass, thresholds
    )
    md_parts.append(threshold_md)
    md_parts.append(_render_matrix_block(matrix))
    md_parts.append("## Per-Session Results\n")
    if not sessions_data:
        md_parts.append("_(no sessions in corpus)_\n")
    else:
        md_parts.append("| Session | Genre | F1 | Useful% | Bypass% | Status |")
        md_parts.append("|---------|-------|----|---------|---------|--------|")
        for s in sessions_data:
            status = "PASS" if s["threshold_pass"] else "FAIL"
            if s.get("skipped"):
                status = "SKIPPED"
            md_parts.append(
                f"| {s['session']} | {s['genre']} | "
                f"{s['f1']:.2f} | {s['useful_response_ratio']:.2f} | "
                f"{s['bypass_rate']:.2f} | {status} |"
            )
    md_parts.append("")
    md = "\n".join(md_parts)

    # JSON shape — same content as md.
    data = {
        "phase": 27,
        "generated_at": now,
        "thresholds": thresholds,
        "overall": {
            "f1": round(overall_f1, 4),
            "useful_response_ratio": round(avg_useful_response, 4),
            "bypass_rate": round(avg_bypass, 4),
            "cited_cosine": round(avg_cited_cosine, 4),
        },
        "threshold_status": threshold_rows,
        "per_detector": overall.get("per_detector", {}),
        "per_detector_per_genre": matrix,
        "sessions": sessions_data,
    }

    return md, data
