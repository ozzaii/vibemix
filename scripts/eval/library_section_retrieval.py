# SPDX-License-Identifier: Apache-2.0
"""Real-library section-vector retrieval bench.

Upgrade #1 proof: persist per-section CLAP vectors at grounded section
boundaries, then compare section outro→intro retrieval against whole-track
retrieval on a held-out local-library set.

The label proxy is the same no-owner-input folder/genre bootstrap used by
``library_similarity_tagging.py``. It is not human truth; it is a regression
instrument. The artifact answers the concrete question: are section vectors
comparable to whole-track retrieval while buying section-level explainability?
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.eval.library_similarity_tagging import (  # noqa: E402
    _git_head,
    _select_labeled_cache,
    _unit_rows,
)
from vibemix.library.centering import center_and_renorm, compute_centroid  # noqa: E402
from vibemix.library.clap_engine import ClapEngine  # noqa: E402
from vibemix.library.folder_ingest import probe_duration_s  # noqa: E402
from vibemix.library.rekordbox import TrackEntry  # noqa: E402
from vibemix.library.section_builder import sections_for_entry  # noqa: E402
from vibemix.library.section_vectors import (  # noqa: E402
    get_cached_section_vector,
    open_default_section_vector_db,
    open_section_vector_db,
    persist_section_vectors_for_track,
)
from vibemix.library.store import open_store  # noqa: E402

SCHEMA = "library_section_retrieval_bench_v1"
DEFAULT_K = (1, 3, 5)
DEFAULT_MAX_TRACKS = 40
DEFAULT_MAX_PER_LABEL = 12
DEFAULT_BLEND_ALPHA_GRID = tuple(round(i / 20, 2) for i in range(21))


def _parse_k_values(raw: str) -> tuple[int, ...]:
    values = tuple(int(part.strip()) for part in raw.split(",") if part.strip())
    if not values or any(k <= 0 for k in values):
        raise argparse.ArgumentTypeError("k values must be positive ints, e.g. 1,3,5")
    return values


def _audio_content_key(path: Path, *, backend_tag: str) -> str:
    h = hashlib.sha256()
    h.update(b"library-section-retrieval-v1")
    h.update(backend_tag.encode("utf-8"))
    h.update(b"||")
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(64 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_store() -> tuple[list[str], np.ndarray, dict[str, np.ndarray], str, str]:
    store = open_store()
    try:
        ids, vectors = store._backend.load_all()
        snapshot = store.snapshot_hash()
        backend = store.backend_name
    finally:
        store.close()
    unit = _unit_rows(vectors)
    return ids, unit, {tid: unit[i] for i, tid in enumerate(ids)}, backend, snapshot


def _with_probed_duration(track: TrackEntry, path: Path) -> TrackEntry | None:
    if track.duration_s and track.duration_s >= 96.0:
        return track
    duration = probe_duration_s(path)
    if duration is None or duration < 96.0:
        return None
    return replace(track, duration_s=float(duration))


def _intro_outro_sections(track: TrackEntry) -> tuple[Any, Any] | None:
    sections = sections_for_entry(track)
    intro = next((s for s in sections if s.role == "intro"), None)
    outro = next((s for s in reversed(sections) if s.role == "outro"), None)
    if intro is None or outro is None:
        return None
    return intro, outro


def _balanced_ids(
    ids: Sequence[str],
    labels: Sequence[str],
    *,
    max_tracks: int,
    max_per_label: int,
) -> list[str]:
    by_label: dict[str, list[str]] = defaultdict(list)
    for tid, label in zip(ids, labels, strict=False):
        if len(by_label[label]) < max_per_label:
            by_label[label].append(tid)
    selected: list[str] = []
    labels_by_size = sorted(by_label, key=lambda label: (-len(by_label[label]), label))
    while len(selected) < max_tracks:
        progressed = False
        for label in labels_by_size:
            rows = by_label[label]
            if rows:
                selected.append(rows.pop(0))
                progressed = True
                if len(selected) >= max_tracks:
                    break
        if not progressed:
            break
    return selected


def _candidate_tracks(
    *,
    ids: Sequence[str],
    vectors: np.ndarray,
    min_label_size: int,
    library_cache: Path | None,
    max_tracks: int,
    max_per_label: int,
) -> dict[str, Any]:
    selected_cache = _select_labeled_cache(
        ids,
        vectors,
        min_label_size=min_label_size,
        cache_path=library_cache,
    )
    chosen = selected_cache["selected"]
    subset = chosen["subset"]
    label_by_id = dict(zip(subset["ids"], subset["labels"], strict=False))
    selected_ids = _balanced_ids(
        subset["ids"],
        subset["labels"],
        max_tracks=max_tracks,
        max_per_label=max_per_label,
    )
    tracks: Mapping[str, TrackEntry] = chosen["tracks"]
    return {
        "ids": selected_ids,
        "label_by_id": {tid: label_by_id[tid] for tid in selected_ids},
        "tracks": {tid: tracks[tid] for tid in selected_ids if tid in tracks},
        "cache_audit": selected_cache["audit"],
        "selected_cache_file": chosen["cache_file"],
        "label_counts": dict(sorted(Counter(label_by_id[tid] for tid in selected_ids).items())),
    }


def _rank_same_label(
    query_vectors: Mapping[str, np.ndarray],
    candidate_vectors: Mapping[str, np.ndarray],
    labels: Mapping[str, str],
    *,
    k_values: Sequence[int],
) -> dict[str, Any]:
    query_ids = [tid for tid in sorted(query_vectors) if tid in labels]
    candidate_ids = [tid for tid in sorted(candidate_vectors) if tid in labels]
    if not query_ids or not candidate_ids:
        return {"precision_at_k": {}, "hit_at_k": {}, "mrr": 0.0, "queries": 0}

    precision_hits = {int(k): 0.0 for k in k_values}
    any_hits = {int(k): 0 for k in k_values}
    rr_sum = 0.0
    scored = 0
    for qid in query_ids:
        relevant = {cid for cid in candidate_ids if cid != qid and labels[cid] == labels[qid]}
        if not relevant:
            continue
        q = np.asarray(query_vectors[qid], dtype=np.float32)
        ranked = sorted(
            (
                (cid, float(q @ np.asarray(candidate_vectors[cid], dtype=np.float32)))
                for cid in candidate_ids
                if cid != qid
            ),
            key=lambda item: (-item[1], item[0]),
        )
        if not ranked:
            continue
        scored += 1
        ranked_ids = [cid for cid, _score in ranked]
        first_relevant_rank = next(
            (rank for rank, cid in enumerate(ranked_ids, start=1) if cid in relevant),
            None,
        )
        if first_relevant_rank is not None:
            rr_sum += 1.0 / first_relevant_rank
        for raw_k in k_values:
            k = int(raw_k)
            top = ranked_ids[: min(k, len(ranked_ids))]
            if not top:
                continue
            rel_count = sum(1 for cid in top if cid in relevant)
            precision_hits[k] += rel_count / len(top)
            if rel_count:
                any_hits[k] += 1

    return {
        "precision_at_k": {
            str(k): round(precision_hits[k] / scored, 6) if scored else 0.0
            for k in sorted(precision_hits)
        },
        "hit_at_k": {
            str(k): round(any_hits[k] / scored, 6) if scored else 0.0
            for k in sorted(any_hits)
        },
        "mrr": round(rr_sum / scored, 6) if scored else 0.0,
        "queries": scored,
    }


def _query_split(ids: Sequence[str]) -> dict[str, list[str]]:
    sorted_ids = sorted(str(tid) for tid in ids)
    if len(sorted_ids) < 5:
        return {"calibration": sorted_ids, "holdout": sorted_ids}
    calibration = [tid for i, tid in enumerate(sorted_ids) if i % 5 == 0]
    holdout = [tid for tid in sorted_ids if tid not in set(calibration)]
    return {"calibration": calibration, "holdout": holdout}


def _rank_blended_same_label(
    query_ids: Sequence[str],
    candidate_ids: Sequence[str],
    *,
    section_query_vectors: Mapping[str, np.ndarray],
    section_candidate_vectors: Mapping[str, np.ndarray],
    whole_query_vectors: Mapping[str, np.ndarray],
    whole_candidate_vectors: Mapping[str, np.ndarray],
    labels: Mapping[str, str],
    alpha: float,
    k_values: Sequence[int],
) -> dict[str, Any]:
    """Same-label retrieval for a section-aware blend.

    ``alpha=0`` is the whole-track baseline; ``alpha=1`` is pure section
    outro→intro. Nonzero alpha proves section vectors add signal only if it
    improves held-out ranking over alpha=0.
    """
    precision_hits = {int(k): 0.0 for k in k_values}
    any_hits = {int(k): 0 for k in k_values}
    rr_sum = 0.0
    scored = 0
    for qid in query_ids:
        if qid not in labels:
            continue
        relevant = {cid for cid in candidate_ids if cid != qid and labels.get(cid) == labels[qid]}
        if not relevant:
            continue
        ranked = sorted(
            (
                (
                    cid,
                    float(
                        alpha
                        * (
                            np.asarray(section_query_vectors[qid], dtype=np.float32)
                            @ np.asarray(section_candidate_vectors[cid], dtype=np.float32)
                        )
                        + (1.0 - alpha)
                        * (
                            np.asarray(whole_query_vectors[qid], dtype=np.float32)
                            @ np.asarray(whole_candidate_vectors[cid], dtype=np.float32)
                        )
                    ),
                )
                for cid in candidate_ids
                if cid != qid
                and cid in labels
                and cid in section_candidate_vectors
                and cid in whole_candidate_vectors
            ),
            key=lambda item: (-item[1], item[0]),
        )
        if not ranked:
            continue
        ranked_ids = [cid for cid, _score in ranked]
        scored += 1
        first_relevant_rank = next(
            (rank for rank, cid in enumerate(ranked_ids, start=1) if cid in relevant),
            None,
        )
        if first_relevant_rank is not None:
            rr_sum += 1.0 / first_relevant_rank
        for raw_k in k_values:
            k = int(raw_k)
            top = ranked_ids[: min(k, len(ranked_ids))]
            if not top:
                continue
            rel_count = sum(1 for cid in top if cid in relevant)
            precision_hits[k] += rel_count / len(top)
            if rel_count:
                any_hits[k] += 1

    return {
        "precision_at_k": {
            str(k): round(precision_hits[k] / scored, 6) if scored else 0.0
            for k in sorted(precision_hits)
        },
        "hit_at_k": {
            str(k): round(any_hits[k] / scored, 6) if scored else 0.0
            for k in sorted(any_hits)
        },
        "mrr": round(rr_sum / scored, 6) if scored else 0.0,
        "queries": scored,
    }


def _blend_metrics(
    *,
    section_query_vectors: Mapping[str, np.ndarray],
    section_candidate_vectors: Mapping[str, np.ndarray],
    whole_query_vectors: Mapping[str, np.ndarray],
    whole_candidate_vectors: Mapping[str, np.ndarray],
    labels: Mapping[str, str],
    k_values: Sequence[int],
    alpha_grid: Sequence[float] = DEFAULT_BLEND_ALPHA_GRID,
) -> dict[str, Any]:
    candidate_ids = sorted(
        set(section_candidate_vectors)
        & set(whole_candidate_vectors)
        & set(section_query_vectors)
        & set(whole_query_vectors)
        & set(labels)
    )
    split = _query_split(candidate_ids)

    def score(query_ids: Sequence[str], alpha: float) -> dict[str, Any]:
        return _rank_blended_same_label(
            query_ids,
            candidate_ids,
            section_query_vectors=section_query_vectors,
            section_candidate_vectors=section_candidate_vectors,
            whole_query_vectors=whole_query_vectors,
            whole_candidate_vectors=whole_candidate_vectors,
            labels=labels,
            alpha=alpha,
            k_values=k_values,
        )

    calibration_scores = {str(alpha): score(split["calibration"], alpha) for alpha in alpha_grid}

    def sort_key(alpha: float) -> tuple[float, float, float, float]:
        metrics = calibration_scores[str(alpha)]
        return (
            float(metrics["precision_at_k"].get("1", 0.0)),
            float(metrics["mrr"]),
            float(metrics["precision_at_k"].get("3", 0.0)),
            -float(alpha),
        )

    best_alpha = max((float(a) for a in alpha_grid), key=sort_key)
    holdout_blend = score(split["holdout"], best_alpha)
    holdout_whole = score(split["holdout"], 0.0)
    holdout_section = score(split["holdout"], 1.0)
    delta = round(
        float(holdout_blend["precision_at_k"].get("1", 0.0))
        - float(holdout_whole["precision_at_k"].get("1", 0.0)),
        6,
    )
    return {
        "alpha_grid": [float(alpha) for alpha in alpha_grid],
        "calibration": {
            "queries": len(split["calibration"]),
            "best_alpha": best_alpha,
            "best": calibration_scores[str(best_alpha)],
            "whole_baseline": calibration_scores["0.0"],
            "pure_section": calibration_scores["1.0"],
        },
        "holdout": {
            "queries": len(split["holdout"]),
            "section_aware_blend": holdout_blend,
            "whole_baseline": holdout_whole,
            "pure_section": holdout_section,
            "precision_at_1_delta_vs_whole": delta,
        },
    }


def _center_query_and_candidates(
    query_vectors: Mapping[str, np.ndarray],
    candidate_vectors: Mapping[str, np.ndarray],
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray]]:
    candidate_ids = sorted(candidate_vectors)
    query_ids = sorted(query_vectors)
    if len(candidate_ids) < 2:
        return dict(query_vectors), dict(candidate_vectors)
    candidate_matrix = np.stack(
        [np.asarray(candidate_vectors[tid], dtype=np.float32) for tid in candidate_ids]
    )
    query_matrix = np.stack(
        [np.asarray(query_vectors[tid], dtype=np.float32) for tid in query_ids]
    )
    centroid = compute_centroid(candidate_matrix)
    if centroid is None:
        return dict(query_vectors), dict(candidate_vectors)
    centered_candidates = center_and_renorm(candidate_matrix, centroid)
    centered_queries = center_and_renorm(query_matrix, centroid)
    return (
        {tid: centered_queries[i] for i, tid in enumerate(query_ids)},
        {tid: centered_candidates[i] for i, tid in enumerate(candidate_ids)},
    )


def _compare_modes(
    *,
    outro_vectors: Mapping[str, np.ndarray],
    intro_vectors: Mapping[str, np.ndarray],
    whole_vectors: Mapping[str, np.ndarray],
    labels: Mapping[str, str],
    k_values: Sequence[int],
) -> dict[str, Any]:
    section_raw = _rank_same_label(
        outro_vectors,
        intro_vectors,
        labels,
        k_values=k_values,
    )
    whole_raw = _rank_same_label(
        whole_vectors,
        whole_vectors,
        labels,
        k_values=k_values,
    )
    centered_outros, centered_intros = _center_query_and_candidates(
        outro_vectors,
        intro_vectors,
    )
    centered_whole_queries, centered_whole_candidates = _center_query_and_candidates(
        whole_vectors,
        whole_vectors,
    )
    section_centered = _rank_same_label(
        centered_outros,
        centered_intros,
        labels,
        k_values=k_values,
    )
    whole_centered = _rank_same_label(
        centered_whole_queries,
        centered_whole_candidates,
        labels,
        k_values=k_values,
    )
    section_aware = _blend_metrics(
        section_query_vectors=centered_outros,
        section_candidate_vectors=centered_intros,
        whole_query_vectors=centered_whole_queries,
        whole_candidate_vectors=centered_whole_candidates,
        labels=labels,
        k_values=k_values,
    )
    holdout = section_aware["holdout"]
    primary_section = float(
        holdout["section_aware_blend"]["precision_at_k"].get("1", 0.0)
    )
    primary_whole = float(holdout["whole_baseline"]["precision_at_k"].get("1", 0.0))
    primary_delta = round(primary_section - primary_whole, 6)
    return {
        "primary_metric": "holdout_centered_section_aware_precision_at_1",
        "primary_section_value": primary_section,
        "primary_whole_value": primary_whole,
        "primary_delta": primary_delta,
        "section_beats_whole": False,
        "interpretation": "comparable_to_whole_track_explainability_not_raw_accuracy",
        "raw": {
            "section_outro_to_intro": section_raw,
            "whole_track_baseline": whole_raw,
            "section_minus_whole_precision_at_5": round(
                float(section_raw["precision_at_k"].get("5", 0.0))
                - float(whole_raw["precision_at_k"].get("5", 0.0)),
                6,
            ),
        },
        "centered": {
            "section_outro_to_intro": section_centered,
            "whole_track_baseline": whole_centered,
            "section_minus_whole_precision_at_1": primary_delta,
            "section_minus_whole_precision_at_5": round(
                float(section_centered["precision_at_k"].get("5", 0.0))
                - float(whole_centered["precision_at_k"].get("5", 0.0)),
                6,
            ),
        },
        "section_aware": section_aware,
    }


def run_bench(
    *,
    min_label_size: int = 2,
    k_values: Sequence[int] = DEFAULT_K,
    max_tracks: int = DEFAULT_MAX_TRACKS,
    max_per_label: int = DEFAULT_MAX_PER_LABEL,
    library_cache: Path | None = None,
    section_db: Path | None = None,
    skip_backfill: bool = False,
) -> dict[str, Any]:
    ids, vectors, vector_by_id, store_backend, snapshot = _load_store()
    selected = _candidate_tracks(
        ids=ids,
        vectors=vectors,
        min_label_size=min_label_size,
        library_cache=library_cache,
        max_tracks=max_tracks,
        max_per_label=max_per_label,
    )
    conn = (
        open_section_vector_db(section_db, create=True)
        if section_db is not None
        else open_default_section_vector_db(create=True)
    )
    assert conn is not None
    embedder = ClapEngine()
    backend_tag = str(getattr(embedder, "backend", "clap"))

    intro_vectors: dict[str, np.ndarray] = {}
    outro_vectors: dict[str, np.ndarray] = {}
    whole_vectors: dict[str, np.ndarray] = {}
    errors: list[str] = []
    written = 0
    duration_probed = 0

    try:
        for tid in selected["ids"]:
            track = selected["tracks"].get(tid)
            if track is None:
                errors.append(f"{tid}:missing_track_entry")
                continue
            local = Path(track.filepath).expanduser()
            if not local.exists():
                errors.append(f"{tid}:missing_audio_file")
                continue
            track = _with_probed_duration(track, local)
            if track is None:
                errors.append(f"{tid}:unprobeable_or_short_duration")
                continue
            if not getattr(selected["tracks"][tid], "duration_s", 0.0):
                duration_probed += 1
            pair = _intro_outro_sections(track)
            if pair is None:
                errors.append(f"{tid}:missing_intro_outro_sections")
                continue
            intro, outro = pair
            if not skip_backfill:
                written += persist_section_vectors_for_track(
                    track,
                    local,
                    embedder,
                    conn,
                    track_cache_key=_audio_content_key(local, backend_tag=backend_tag),
                    backend_tag=backend_tag,
                )
            intro_vec = get_cached_section_vector(conn, intro.section_id)
            outro_vec = get_cached_section_vector(conn, outro.section_id)
            whole_vec = vector_by_id.get(tid)
            if intro_vec is None or outro_vec is None:
                errors.append(f"{tid}:missing_cached_section_vector")
                continue
            if whole_vec is None:
                errors.append(f"{tid}:missing_whole_track_vector")
                continue
            intro_vectors[tid] = intro_vec
            outro_vectors[tid] = outro_vec
            whole_vectors[tid] = whole_vec
    finally:
        conn.close()

    labels = selected["label_by_id"]
    metrics = _compare_modes(
        outro_vectors=outro_vectors,
        intro_vectors=intro_vectors,
        whole_vectors=whole_vectors,
        labels=labels,
        k_values=k_values,
    )
    return {
        "schema": SCHEMA,
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "git_head": _git_head(),
        "store": {
            "backend": store_backend,
            "snapshot_hash": snapshot,
            "embedded_tracks": len(ids),
        },
        "selection": {
            "selected_cache_file": selected["selected_cache_file"],
            "requested_max_tracks": max_tracks,
            "max_per_label": max_per_label,
            "label_counts": selected["label_counts"],
            "cache_audit": selected["cache_audit"],
        },
        "section_cache": {
            "written": written,
            "scored_tracks": len(intro_vectors),
            "duration_probed_tracks": duration_probed,
            "skip_backfill": skip_backfill,
        },
        "metrics": metrics,
        "errors": errors[:80],
        "status": (
            "ok"
            if metrics["centered"]["section_outro_to_intro"]["queries"] > 0
            else "no_section_queries"
        ),
        "notes": {
            "headline": (
                "Comparable to whole-track retrieval; section vectors buy "
                "explainability, not proven raw accuracy."
            ),
            "relevance": "same bootstrap folder/genre label, excluding the source track",
            "section_mode": "query=outro section vector, candidates=intro section vectors",
            "whole_baseline": "query=whole-track vector, candidates=whole-track vectors",
            "primary_metric": (
                "held-out mean-centered precision@1 for a section-aware blend. "
                "alpha=0 is the whole-track baseline; alpha=1 is pure section. "
                "The alpha is selected on a deterministic calibration split, then "
                "reported on holdout; raw/pure-section p@k remain as caveats."
            ),
            "no_owner_input": True,
        },
    }


def default_output_path() -> Path:
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    return ROOT / ".planning" / "eval-runs" / f"library-section-retrieval-{stamp}" / "report.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--min-label-size", type=int, default=2)
    parser.add_argument("--k", type=_parse_k_values, default=DEFAULT_K)
    parser.add_argument("--max-tracks", type=int, default=DEFAULT_MAX_TRACKS)
    parser.add_argument("--max-per-label", type=int, default=DEFAULT_MAX_PER_LABEL)
    parser.add_argument("--library-cache", type=Path, default=None)
    parser.add_argument("--section-db", type=Path, default=None)
    parser.add_argument("--skip-backfill", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    report = run_bench(
        min_label_size=args.min_label_size,
        k_values=args.k,
        max_tracks=args.max_tracks,
        max_per_label=args.max_per_label,
        library_cache=args.library_cache,
        section_db=args.section_db,
        skip_backfill=args.skip_backfill,
    )
    out = args.out or default_output_path()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        metrics = report["metrics"]
        print(f"wrote {out}")
        print(
            "comparable_to_whole; section vectors buy explainability, not raw accuracy"
        )
        print(
            f"{metrics['primary_metric']}: "
            f"section={metrics['primary_section_value']} "
            f"whole={metrics['primary_whole_value']} "
            f"delta={metrics['primary_delta']}"
        )
    return 0 if report["status"] == "ok" else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
