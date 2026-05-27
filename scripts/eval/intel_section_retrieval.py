# SPDX-License-Identifier: Apache-2.0
"""Compare section-level retrieval against pooled whole-track retrieval.

The fixture path is intentionally small and synthetic, but the evaluator mirrors
the production question: does a query retrieve a mixable musical section, or only
a vague whole-track vibe?
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_FIXTURE_DIR = ROOT / "tests" / "intel" / "fixtures"
DEFAULT_MIN_ROLE_CONFIDENCE = 0.70
DEFAULT_MIN_BAR_COUNT = 4.0
LOW_CONFIDENCE_FLOOR = 0.55

Mode = Literal["section", "whole_track"]


@dataclass(frozen=True, slots=True)
class RetrievalQuery:
    query_id: str
    target_role: str
    vector: tuple[float, ...]
    mixable_roles: tuple[str, ...]
    min_role_confidence: float = DEFAULT_MIN_ROLE_CONFIDENCE
    min_bar_count: float = DEFAULT_MIN_BAR_COUNT


@dataclass(frozen=True, slots=True)
class Candidate:
    candidate_id: str
    role: str
    role_confidence: float
    bar_count: float | None
    source_detail: str
    vector: tuple[float, ...]


def score_fixture_dir(
    fixture_dir: Path | str = DEFAULT_FIXTURE_DIR,
    *,
    mode: str = "compare",
    k: int = 10,
    queries_path: Path | str | None = None,
) -> dict[str, Any]:
    base = Path(fixture_dir)
    default_queries = base / "section_queries.jsonl"
    return score_paths(
        sections_path=base / "sections.json",
        vectors_path=base / "section_vectors_8d.json",
        queries_path=queries_path if queries_path is not None else default_queries,
        mode=mode,
        k=k,
        source=f"fixture:{base.name}",
    )


def score_paths(
    *,
    sections_path: Path | str,
    vectors_path: Path | str,
    queries_path: Path | str | None = None,
    mode: str = "compare",
    k: int = 10,
    source: str = "private:redacted",
) -> dict[str, Any]:
    sections = _load_json(Path(sections_path))
    vectors = _load_json(Path(vectors_path))
    normalized_mode = _normalize_mode(mode)
    queries, query_errors = _load_queries(
        queries_path=Path(queries_path) if queries_path is not None else None,
        sections=tuple(sections),
        vectors=dict(vectors),
    )
    if normalized_mode == "compare":
        return compare_retrieval_modes(
            sections=tuple(sections),
            vectors=dict(vectors),
            queries=queries,
            query_errors=query_errors,
            k=k,
            source=source,
        )
    return score_retrieval_mode(
        sections=tuple(sections),
        vectors=dict(vectors),
        queries=queries,
        query_errors=query_errors,
        mode=normalized_mode,
        k=k,
        source=source,
    )


def compare_retrieval_modes(
    *,
    sections: tuple[dict[str, Any], ...],
    vectors: dict[str, Any],
    queries: tuple[RetrievalQuery, ...],
    query_errors: tuple[str, ...] = (),
    k: int = 10,
    source: str,
) -> dict[str, Any]:
    section = score_retrieval_mode(
        sections=sections,
        vectors=vectors,
        queries=queries,
        query_errors=query_errors,
        mode="section",
        k=k,
        source=source,
    )
    whole_track = score_retrieval_mode(
        sections=sections,
        vectors=vectors,
        queries=queries,
        query_errors=query_errors,
        mode="whole_track",
        k=k,
        source=source,
    )
    metrics = {
        "section_role_hit_at_5": _metric(section, "role_hit_at_5"),
        "whole_track_role_hit_at_5": _metric(whole_track, "role_hit_at_5"),
        "section_minus_whole_track_role_hit_at_5": round(
            _metric(section, "role_hit_at_5") - _metric(whole_track, "role_hit_at_5"), 6
        ),
        "section_mixable_window_hit_at_5": _metric(section, "mixable_window_hit_at_5"),
        "whole_track_mixable_window_hit_at_5": _metric(whole_track, "mixable_window_hit_at_5"),
        "section_minus_whole_track_mixable_window_hit_at_5": round(
            _metric(section, "mixable_window_hit_at_5")
            - _metric(whole_track, "mixable_window_hit_at_5"),
            6,
        ),
        "section_low_confidence_result_rate": _metric(section, "low_confidence_result_rate"),
        "whole_track_low_confidence_result_rate": _metric(
            whole_track, "low_confidence_result_rate"
        ),
    }
    return {
        "schema": "intel_section_retrieval_compare_v1",
        "source": source,
        "valid": bool(section.get("valid")) and bool(whole_track.get("valid")),
        "privacy": {"local_paths_redacted": True, "raw_vectors_redacted": True},
        "metrics": metrics,
        "by_mode": {"section": section, "whole_track": whole_track},
    }


def score_retrieval_mode(
    *,
    sections: tuple[dict[str, Any], ...],
    vectors: dict[str, Any],
    queries: tuple[RetrievalQuery, ...],
    query_errors: tuple[str, ...] = (),
    mode: Mode,
    k: int = 10,
    source: str,
) -> dict[str, Any]:
    errors = list(query_errors)
    section_candidates, candidate_errors = _section_candidates(sections, vectors)
    errors.extend(candidate_errors)
    role_prototypes = _role_prototypes(section_candidates)
    candidates = (
        section_candidates
        if mode == "section"
        else _whole_track_candidates(section_candidates, role_prototypes)
    )

    query_results = []
    role_hit_at_5 = 0
    role_hit_at_10 = 0
    mixable_window_hit_at_5 = 0
    low_confidence_results = 0
    total_results = 0
    top_k = max(1, int(k))

    for query in queries:
        ranked = sorted(
            (
                (candidate, _cosine(query.vector, candidate.vector))
                for candidate in candidates
                if candidate.vector
            ),
            key=lambda item: item[1],
            reverse=True,
        )[:top_k]
        top_5 = ranked[:5]
        top_10 = ranked[:10]
        if any(candidate.role == query.target_role for candidate, _score in top_5):
            role_hit_at_5 += 1
        if any(candidate.role == query.target_role for candidate, _score in top_10):
            role_hit_at_10 += 1
        if any(_is_mixable_window(candidate, query) for candidate, _score in top_5):
            mixable_window_hit_at_5 += 1
        for candidate, _score in ranked:
            total_results += 1
            if _is_low_confidence(candidate):
                low_confidence_results += 1
        query_results.append(
            {
                "query_id": query.query_id,
                "target_role": query.target_role,
                "top_results": tuple(
                    {
                        "rank": rank,
                        "result_ref": _public_ref(candidate.candidate_id),
                        "role": candidate.role,
                        "role_confidence": round(candidate.role_confidence, 6),
                        "bar_count": candidate.bar_count,
                        "source_detail": candidate.source_detail,
                        "score": round(score, 6),
                    }
                    for rank, (candidate, score) in enumerate(ranked[:5], start=1)
                ),
            }
        )

    query_count = len(queries)
    metrics = {
        "role_hit_at_5": _rate(role_hit_at_5, query_count),
        "role_hit_at_10": _rate(role_hit_at_10, query_count),
        "mixable_window_hit_at_5": _rate(mixable_window_hit_at_5, query_count),
        "low_confidence_result_rate": _rate(low_confidence_results, total_results),
    }
    return {
        "schema": "intel_section_retrieval_v1",
        "source": source,
        "mode": mode,
        "valid": bool(queries) and bool(candidates) and not errors,
        "privacy": {"local_paths_redacted": True, "raw_vectors_redacted": True},
        "totals": {
            "sections": len(sections),
            "candidates": len(candidates),
            "queries": query_count,
            "results_scored": total_results,
            "missing_section_vectors": len(candidate_errors),
        },
        "metrics": metrics,
        "errors": tuple(errors),
        "query_results": tuple(query_results),
    }


def _section_candidates(
    sections: tuple[dict[str, Any], ...], vectors: dict[str, Any]
) -> tuple[tuple[Candidate, ...], tuple[str, ...]]:
    candidates: list[Candidate] = []
    errors: list[str] = []
    for section in sections:
        section_id = str(section.get("section_id") or "")
        vector_ref = str(section.get("semantic_vector_ref") or "")
        vector = _vector_for_ref(vectors, vector_ref)
        if vector is None:
            errors.append(f"{section_id or '<missing_section_id>'}:missing_vector:{vector_ref}")
            continue
        candidates.append(
            Candidate(
                candidate_id=section_id,
                role=str(section.get("role") or "unknown"),
                role_confidence=_float(section.get("role_confidence"), 0.0),
                bar_count=_float_or_none(section.get("bar_count")),
                source_detail=str(section.get("source_detail") or ""),
                vector=vector,
            )
        )
    return tuple(candidates), tuple(errors)


def _whole_track_candidates(
    section_candidates: tuple[Candidate, ...],
    role_prototypes: dict[str, tuple[float, ...]],
) -> tuple[Candidate, ...]:
    by_track: dict[str, list[Candidate]] = defaultdict(list)
    for candidate in section_candidates:
        track_id = candidate.candidate_id.split("#s", 1)[0]
        by_track[track_id].append(candidate)

    whole_track: list[Candidate] = []
    for track_id, rows in sorted(by_track.items()):
        vector = _mean_vector(tuple(row.vector for row in rows))
        role = _nearest_role(vector, role_prototypes)
        confidence = _mean(
            row.role_confidence for row in rows if row.role == role and row.role_confidence > 0
        )
        if confidence == 0.0:
            confidence = _nearest_role_confidence(vector, role, role_prototypes)
        if any(row.role == "unknown" or row.source_detail == "whole_track" for row in rows):
            role = "unknown"
            confidence = min(confidence, 0.45)
        whole_track.append(
            Candidate(
                candidate_id=f"{track_id}#whole",
                role=role,
                role_confidence=confidence,
                bar_count=_sum_known(row.bar_count for row in rows),
                source_detail="whole_track_baseline",
                vector=vector,
            )
        )
    return tuple(whole_track)


def _load_queries(
    *,
    queries_path: Path | None,
    sections: tuple[dict[str, Any], ...],
    vectors: dict[str, Any],
) -> tuple[tuple[RetrievalQuery, ...], tuple[str, ...]]:
    role_prototypes = _fixture_role_prototypes(sections, vectors)
    if queries_path is None or not queries_path.exists():
        return _default_queries(role_prototypes), ()

    rows = _load_json_or_jsonl(queries_path)
    queries: list[RetrievalQuery] = []
    errors: list[str] = []
    for index, row in enumerate(rows):
        query_id = str(row.get("query_id") or f"query_{index:03d}")
        vector = _query_vector(row, role_prototypes, vectors)
        target_role = str(row.get("target_role") or row.get("role") or "")
        if not target_role:
            errors.append(f"{query_id}:missing_target_role")
            continue
        if vector is None:
            errors.append(f"{query_id}:missing_query_vector")
            continue
        mixable_roles = tuple(str(role) for role in row.get("mixable_roles") or (target_role,))
        queries.append(
            RetrievalQuery(
                query_id=query_id,
                target_role=target_role,
                vector=vector,
                mixable_roles=mixable_roles,
                min_role_confidence=_float(
                    row.get("min_role_confidence"), DEFAULT_MIN_ROLE_CONFIDENCE
                ),
                min_bar_count=_float(row.get("min_bar_count"), DEFAULT_MIN_BAR_COUNT),
            )
        )
    return tuple(queries), tuple(errors)


def _default_queries(role_prototypes: dict[str, tuple[float, ...]]) -> tuple[RetrievalQuery, ...]:
    return tuple(
        RetrievalQuery(
            query_id=f"fixture:role:{role}",
            target_role=role,
            vector=vector,
            mixable_roles=(role,),
        )
        for role, vector in sorted(role_prototypes.items())
    )


def _fixture_role_prototypes(
    sections: tuple[dict[str, Any], ...], vectors: dict[str, Any]
) -> dict[str, tuple[float, ...]]:
    role_vectors: dict[str, list[tuple[float, ...]]] = defaultdict(list)
    for section in sections:
        role = str(section.get("role") or "unknown")
        if role == "unknown" or _float(section.get("role_confidence"), 0.0) < 0.70:
            continue
        vector = _vector_for_ref(vectors, str(section.get("semantic_vector_ref") or ""))
        if vector is not None:
            role_vectors[role].append(vector)
    return {
        role: _mean_vector(tuple(items))
        for role, items in sorted(role_vectors.items())
        if len(items) >= 2
    }


def _role_prototypes(candidates: tuple[Candidate, ...]) -> dict[str, tuple[float, ...]]:
    role_vectors: dict[str, list[tuple[float, ...]]] = defaultdict(list)
    for candidate in candidates:
        if candidate.role == "unknown" or candidate.role_confidence < 0.70:
            continue
        role_vectors[candidate.role].append(candidate.vector)
    return {
        role: _mean_vector(tuple(items))
        for role, items in sorted(role_vectors.items())
        if len(items) >= 2
    }


def _query_vector(
    row: dict[str, Any],
    role_prototypes: dict[str, tuple[float, ...]],
    vectors: dict[str, Any],
) -> tuple[float, ...] | None:
    vector = _as_float_vector(row.get("vector") or row.get("query_vector"))
    if vector is not None:
        return vector
    vector_ref = row.get("vector_ref") or row.get("query_vector_ref")
    if vector_ref:
        return _vector_for_ref(vectors, str(vector_ref))
    prototype_role = row.get("prototype_role")
    if prototype_role:
        return role_prototypes.get(str(prototype_role))
    return None


def _nearest_role(vector: tuple[float, ...], role_prototypes: dict[str, tuple[float, ...]]) -> str:
    if not role_prototypes:
        return "unknown"
    return max(role_prototypes, key=lambda role: _cosine(vector, role_prototypes[role]))


def _nearest_role_confidence(
    vector: tuple[float, ...],
    role: str,
    role_prototypes: dict[str, tuple[float, ...]],
) -> float:
    if role not in role_prototypes:
        return 0.0
    # Cosine here is a weak whole-track semantic confidence, not section evidence.
    return max(0.0, min(1.0, _cosine(vector, role_prototypes[role])))


def _is_mixable_window(candidate: Candidate, query: RetrievalQuery) -> bool:
    return (
        candidate.role in query.mixable_roles
        and candidate.role_confidence >= query.min_role_confidence
        and (candidate.bar_count or 0.0) >= query.min_bar_count
    )


def _is_low_confidence(candidate: Candidate) -> bool:
    return (
        candidate.role == "unknown"
        or candidate.role_confidence < LOW_CONFIDENCE_FLOOR
        or candidate.source_detail == "whole_track"
    )


def _normalize_mode(mode: str) -> Mode | Literal["compare"]:
    clean = mode.replace("-", "_")
    if clean in {"section", "whole_track", "compare"}:
        return clean  # type: ignore[return-value]
    msg = f"unknown section retrieval mode: {mode}"
    raise ValueError(msg)


def _metric(result: dict[str, Any], name: str) -> float:
    return _float((result.get("metrics") or {}).get(name), 0.0)


def _cosine(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    if len(a) != len(b):
        return 0.0
    norm_a = math.sqrt(sum(value * value for value in a))
    norm_b = math.sqrt(sum(value * value for value in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return sum(left * right for left, right in zip(a, b, strict=True)) / (norm_a * norm_b)


def _mean_vector(vectors: tuple[tuple[float, ...], ...]) -> tuple[float, ...]:
    if not vectors:
        return ()
    width = len(vectors[0])
    return tuple(sum(vector[index] for vector in vectors) / len(vectors) for index in range(width))


def _mean(values: Any) -> float:
    items = [float(value) for value in values]
    if not items:
        return 0.0
    return sum(items) / len(items)


def _sum_known(values: Any) -> float | None:
    items = [float(value) for value in values if value is not None]
    if not items:
        return None
    return round(sum(items), 6)


def _rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 6) if denominator else 0.0


def _vector_for_ref(vectors: dict[str, Any], vector_ref: str) -> tuple[float, ...] | None:
    if not vector_ref:
        return None
    return _as_float_vector(vectors.get(vector_ref))


def _as_float_vector(value: Any) -> tuple[float, ...] | None:
    if not isinstance(value, list | tuple) or not value:
        return None
    try:
        return tuple(float(item) for item in value)
    except (TypeError, ValueError):
        return None


def _public_ref(candidate_id: str) -> str:
    digest = hashlib.sha256(candidate_id.encode("utf-8")).hexdigest()[:12]
    return f"ref:{digest}"


def _float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    return _float(value, 0.0)


def _float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_json_or_jsonl(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []
    if path.suffix == ".jsonl":
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    raw = json.loads(text)
    return raw if isinstance(raw, list) else [raw]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture-dir", type=Path, default=DEFAULT_FIXTURE_DIR)
    parser.add_argument("--sections", type=Path, help="Section manifest JSON")
    parser.add_argument("--vectors", type=Path, help="Section vector JSON")
    parser.add_argument("--queries", type=Path, help="Section query JSON/JSONL")
    parser.add_argument(
        "--mode",
        choices=("compare", "section", "whole-track", "whole_track"),
        default="compare",
    )
    parser.add_argument("--k", type=int, default=10)
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    args = parser.parse_args(argv)

    if args.sections or args.vectors:
        if not args.sections or not args.vectors:
            parser.error("--sections and --vectors must be provided together")
        result = score_paths(
            sections_path=args.sections,
            vectors_path=args.vectors,
            queries_path=args.queries,
            mode=args.mode,
            k=args.k,
        )
    else:
        result = score_fixture_dir(
            args.fixture_dir,
            mode=args.mode,
            k=args.k,
            queries_path=args.queries,
        )

    if args.json:
        json.dump(result, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    elif result["schema"] == "intel_section_retrieval_compare_v1":
        metrics = result["metrics"]
        print(
            "Section retrieval comparison: "
            f"valid={result['valid']} "
            f"role_delta={metrics['section_minus_whole_track_role_hit_at_5']} "
            f"mixable_delta={metrics['section_minus_whole_track_mixable_window_hit_at_5']}"
        )
    else:
        metrics = result["metrics"]
        print(
            "Section retrieval: "
            f"mode={result['mode']} valid={result['valid']} "
            f"role@5={metrics['role_hit_at_5']} "
            f"mixable@5={metrics['mixable_window_hit_at_5']}"
        )
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    raise SystemExit(main())
