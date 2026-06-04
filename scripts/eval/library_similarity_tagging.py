# SPDX-License-Identifier: Apache-2.0
"""Real-library CLAP similarity/tagging bench.

This is the regression instrument that must exist before claiming a library
quality upgrade. It runs over the user's cached library vectors plus a
bootstrap label proxy from the local Rekordbox/folder metadata, then emits a
JSON artifact with:

* precision@k retrieval: "does a track retrieve tracks with the same proxy label?"
* prototype cluster purity: "do embedding clusters stay label-coherent?"
* optional human-triplet agreement: "is anchor closer to positive than negative?"

No model calls, no torch/librosa, no owner input. The proxy labels are an honest
bootstrap only; a later hand-labeled triplet file can be supplied with
``--triplets`` without changing this bench.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from vibemix.library.centering import center_and_renorm, compute_centroid  # noqa: E402
from vibemix.library.rekordbox import RekordboxLibrary, TrackEntry  # noqa: E402
from vibemix.library.store import open_store  # noqa: E402

SCHEMA = "library_similarity_tagging_bench_v1"
UNKNOWN_LABEL = "unknown"
DEFAULT_K = (1, 3, 5)


def _unit_rows(vectors: np.ndarray) -> np.ndarray:
    """L2-normalize each row. Accepts arbitrary dims so unit tests stay tiny."""
    arr = np.asarray(vectors, dtype=np.float32)
    if arr.ndim != 2:
        raise ValueError(f"expected (N, D) vectors, got shape {arr.shape}")
    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    norms = np.where(norms < 1e-12, 1.0, norms)
    return (arr / norms).astype(np.float32, copy=False)


def _clean_label(value: str) -> str:
    label = " ".join(str(value or "").replace("_", " ").replace("-", " ").split())
    return label if label else UNKNOWN_LABEL


def _local_path_text(raw: str) -> str:
    text = str(raw or "").strip()
    if not text:
        return ""
    parsed = urlparse(text)
    if parsed.scheme == "file":
        return unquote(parsed.path)
    return unquote(text)


def label_for_track(entry: TrackEntry | None) -> tuple[str, str]:
    """Return ``(label, source)`` from folder first, then Rekordbox genre.

    Folder labels mirror ``genre_prototypes``' bootstrap discipline; the genre
    fallback lets folder-ingest or sparse Rekordbox exports still participate
    without owner input. Absolute paths never leave this function: only the
    parent folder name is returned.
    """
    if entry is None:
        return UNKNOWN_LABEL, "missing_entry"
    folder = _clean_label(Path(_local_path_text(entry.filepath)).parent.name)
    if folder != UNKNOWN_LABEL:
        return folder, "folder_parent"
    genre = _clean_label(entry.genre)
    if genre != UNKNOWN_LABEL:
        return genre, "rekordbox_genre"
    return UNKNOWN_LABEL, "unknown"


def _label_options_for_track(entry: TrackEntry | None) -> dict[str, str]:
    if entry is None:
        return {
            "folder_parent": UNKNOWN_LABEL,
            "rekordbox_genre": UNKNOWN_LABEL,
        }
    folder = _clean_label(Path(_local_path_text(entry.filepath)).parent.name)
    genre = _clean_label(entry.genre)
    return {
        "folder_parent": folder,
        "rekordbox_genre": genre,
    }


def _choose_label_source(
    options_by_id: Mapping[str, Mapping[str, str]],
    *,
    min_label_size: int,
) -> tuple[str, dict[str, Any]]:
    audits: dict[str, Any] = {}
    source_order = ("folder_parent", "rekordbox_genre")
    for source in source_order:
        counts = Counter(
            opts.get(source, UNKNOWN_LABEL)
            for opts in options_by_id.values()
            if opts.get(source, UNKNOWN_LABEL) != UNKNOWN_LABEL
        )
        kept = {
            label: count
            for label, count in counts.items()
            if count >= min_label_size
        }
        audits[source] = {
            "label_count": len(kept),
            "track_count": sum(kept.values()),
            "label_counts": dict(sorted(kept.items())),
        }

    def sort_key(source: str) -> tuple[int, int, int, int]:
        audit = audits[source]
        # Prefer a real multi-label source. Then prefer more labels, then more
        # tracks. Keep folder first on exact ties to mirror genre_prototypes.
        real = int(audit["label_count"] >= 2 and audit["track_count"] >= 2)
        tie = 1 if source == "folder_parent" else 0
        return (real, int(audit["label_count"]), int(audit["track_count"]), tie)

    selected = max(source_order, key=sort_key)
    return selected, audits


def prepare_labeled_subset(
    ids: Sequence[str],
    vectors: np.ndarray,
    tracks: Mapping[str, TrackEntry],
    *,
    min_label_size: int = 2,
) -> dict[str, Any]:
    """Filter cached vectors to tracks with usable proxy labels."""
    if min_label_size < 1:
        raise ValueError("min_label_size must be >= 1")
    unit = _unit_rows(vectors)
    labels_by_id: dict[str, str] = {}
    source_counts: Counter[str] = Counter()
    options_by_id = {
        str(tid): _label_options_for_track(tracks.get(str(tid))) for tid in ids
    }
    selected_source, source_audit = _choose_label_source(
        options_by_id,
        min_label_size=min_label_size,
    )
    raw_counts: Counter[str] = Counter()

    for tid in ids:
        label = options_by_id[str(tid)].get(selected_source, UNKNOWN_LABEL)
        source = selected_source if label != UNKNOWN_LABEL else "missing_label"
        labels_by_id[tid] = label
        source_counts[source] += 1
        if label != UNKNOWN_LABEL:
            raw_counts[label] += 1

    keep_labels = {label for label, count in raw_counts.items() if count >= min_label_size}
    keep_indices = [
        i for i, tid in enumerate(ids) if labels_by_id[tid] in keep_labels
    ]
    kept_ids = [str(ids[i]) for i in keep_indices]
    kept_labels = [labels_by_id[tid] for tid in kept_ids]
    kept_vectors = unit[keep_indices] if keep_indices else np.zeros((0, unit.shape[1]), dtype=np.float32)

    return {
        "ids": kept_ids,
        "labels": kept_labels,
        "vectors": kept_vectors,
        "label_counts_raw": dict(sorted(raw_counts.items())),
        "label_counts_kept": dict(sorted(Counter(kept_labels).items())),
        "label_source_counts": dict(sorted(source_counts.items())),
        "selected_label_source": selected_source,
        "candidate_label_sources": source_audit,
        "dropped_unknown": sum(1 for tid in ids if labels_by_id[tid] == UNKNOWN_LABEL),
        "dropped_too_small": sum(
            count for label, count in raw_counts.items() if label not in keep_labels
        ),
    }


def _rank_vectors(vectors: np.ndarray, *, centered: bool) -> np.ndarray:
    unit = _unit_rows(vectors)
    if not centered:
        return unit
    centroid = compute_centroid(unit)
    if centroid is None:
        return unit
    return center_and_renorm(unit, centroid)


def _top_indices(row: np.ndarray, ids: Sequence[str], *, self_index: int, k: int) -> list[int]:
    n = int(row.shape[0])
    if n <= 1:
        return []
    limit = min(k, n - 1)
    scores = row.astype(np.float32, copy=True)
    scores[self_index] = -np.inf
    if limit >= n - 1:
        candidates = [i for i in range(n) if i != self_index]
    else:
        candidates = [int(i) for i in np.argpartition(-scores, limit - 1)[:limit]]
    candidates.sort(key=lambda i: (-float(scores[i]), ids[i]))
    return candidates[:limit]


def precision_at_k(
    vectors: np.ndarray,
    ids: Sequence[str],
    labels: Sequence[str],
    *,
    k_values: Sequence[int] = DEFAULT_K,
    centered: bool = True,
) -> dict[int, float]:
    """Mean same-label precision@k over all labeled tracks."""
    if len(ids) != len(labels):
        raise ValueError("ids and labels length mismatch")
    rank_vectors = _rank_vectors(vectors, centered=centered)
    n = int(rank_vectors.shape[0])
    if n <= 1:
        return {int(k): 0.0 for k in k_values}
    sims = rank_vectors @ rank_vectors.T
    out: dict[int, float] = {}
    for raw_k in k_values:
        k = int(raw_k)
        if k <= 0:
            raise ValueError("k values must be positive")
        total = 0.0
        for i in range(n):
            top = _top_indices(sims[i], ids, self_index=i, k=k)
            if not top:
                continue
            total += sum(1 for j in top if labels[j] == labels[i]) / len(top)
        out[k] = round(total / n, 6)
    return out


def _prototype_vectors(
    vectors: np.ndarray,
    labels: Sequence[str],
    *,
    exclude_index: int | None = None,
) -> tuple[list[str], np.ndarray]:
    by_label: defaultdict[str, list[np.ndarray]] = defaultdict(list)
    for i, label in enumerate(labels):
        if exclude_index is not None and i == exclude_index:
            continue
        by_label[str(label)].append(vectors[i])
    proto_labels: list[str] = []
    protos: list[np.ndarray] = []
    for label in sorted(by_label):
        rows = by_label[label]
        if not rows:
            continue
        proto_labels.append(label)
        protos.append(np.asarray(rows, dtype=np.float32).mean(axis=0))
    if not protos:
        dim = int(vectors.shape[1]) if vectors.ndim == 2 else 0
        return [], np.zeros((0, dim), dtype=np.float32)
    return proto_labels, _unit_rows(np.stack(protos).astype(np.float32))


def prototype_cluster_metrics(
    vectors: np.ndarray,
    labels: Sequence[str],
    *,
    centered: bool = True,
) -> dict[str, Any]:
    """Nearest-prototype cluster purity and leave-one-out prototype accuracy."""
    rank_vectors = _rank_vectors(vectors, centered=centered)
    n = int(rank_vectors.shape[0])
    if n == 0:
        return {
            "prototype_cluster_purity": 0.0,
            "prototype_accuracy": 0.0,
            "prototype_accuracy_leave_one_out": 0.0,
            "clusters": {},
        }

    proto_labels, protos = _prototype_vectors(rank_vectors, labels)
    if not proto_labels:
        return {
            "prototype_cluster_purity": 0.0,
            "prototype_accuracy": 0.0,
            "prototype_accuracy_leave_one_out": 0.0,
            "clusters": {},
        }

    sims = rank_vectors @ protos.T
    assignments = [proto_labels[int(np.argmax(row))] for row in sims]
    clusters: dict[str, Counter[str]] = defaultdict(Counter)
    correct = 0
    for actual, assigned in zip(labels, assignments, strict=False):
        clusters[assigned][str(actual)] += 1
        if assigned == actual:
            correct += 1
    majority = sum(max(counts.values()) for counts in clusters.values())

    loo_scored = 0
    loo_correct = 0
    for i, actual in enumerate(labels):
        loo_labels, loo_protos = _prototype_vectors(rank_vectors, labels, exclude_index=i)
        if not loo_labels:
            continue
        row = rank_vectors[i] @ loo_protos.T
        assigned = loo_labels[int(np.argmax(row))]
        loo_scored += 1
        if assigned == actual:
            loo_correct += 1

    return {
        "prototype_cluster_purity": round(majority / n, 6),
        "prototype_accuracy": round(correct / n, 6),
        "prototype_accuracy_leave_one_out": (
            round(loo_correct / loo_scored, 6) if loo_scored else 0.0
        ),
        "loo_scored_tracks": loo_scored,
        "clusters": {
            cluster: dict(sorted(counts.items()))
            for cluster, counts in sorted(clusters.items())
        },
    }


def _read_triplet_rows(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []
    if path.suffix.lower() == ".jsonl":
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    raw = json.loads(text)
    if isinstance(raw, dict):
        raw = raw.get("triplets", [])
    if not isinstance(raw, list):
        raise ValueError("triplets must be a JSON list or {\"triplets\": [...]}")
    return [row for row in raw if isinstance(row, dict)]


def evaluate_triplets(
    vectors: np.ndarray,
    ids: Sequence[str],
    triplet_path: Path | None,
    *,
    centered: bool = True,
) -> dict[str, Any]:
    if triplet_path is None:
        return {
            "path": None,
            "count": 0,
            "scored": 0,
            "missing": 0,
            "agreement": None,
        }
    rows = _read_triplet_rows(triplet_path)
    rank_vectors = _rank_vectors(vectors, centered=centered)
    by_id = {tid: rank_vectors[i] for i, tid in enumerate(ids)}
    wins = 0
    scored = 0
    missing = 0
    for row in rows:
        anchor = str(row.get("anchor", "") or "")
        positive = str(row.get("positive", "") or "")
        negative = str(row.get("negative", "") or "")
        if anchor not in by_id or positive not in by_id or negative not in by_id:
            missing += 1
            continue
        pos_sim = float(by_id[anchor] @ by_id[positive])
        neg_sim = float(by_id[anchor] @ by_id[negative])
        scored += 1
        if pos_sim > neg_sim:
            wins += 1
    return {
        "path": str(triplet_path),
        "count": len(rows),
        "scored": scored,
        "missing": missing,
        "agreement": round(wins / scored, 6) if scored else None,
    }


def evaluate_vectors(
    ids: Sequence[str],
    vectors: np.ndarray,
    labels: Sequence[str],
    *,
    k_values: Sequence[int] = DEFAULT_K,
    triplet_path: Path | None = None,
) -> dict[str, Any]:
    """Pure metric bundle used by tests and the CLI."""
    if len(ids) != len(labels) or len(ids) != int(vectors.shape[0]):
        raise ValueError("ids, labels, and vectors row count must match")
    label_count = len(set(labels))
    status = "ok" if len(ids) >= 2 and label_count >= 2 else "insufficient_labeled_subset"
    metrics: dict[str, Any] = {}
    for mode, centered in (("raw", False), ("centered", True)):
        metrics[mode] = {
            "precision_at_k": precision_at_k(
                vectors,
                ids,
                labels,
                k_values=k_values,
                centered=centered,
            ),
            **prototype_cluster_metrics(vectors, labels, centered=centered),
            "triplets": evaluate_triplets(
                vectors,
                ids,
                triplet_path,
                centered=centered,
            ),
        }
    return {
        "status": status,
        "track_count": len(ids),
        "label_count": label_count,
        "metrics": metrics,
    }


def _git_head() -> str | None:
    try:
        out = subprocess.run(
            ["git", "log", "-1", "--format=%H"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception:
        return None
    return out.stdout.strip() or None


def _summarize_source_path(path: str) -> dict[str, Any] | None:
    if not path:
        return None
    p = Path(path)
    return {
        "name": p.name or path,
        "kind": "directory" if p.suffix == "" else "file",
    }


def _load_library_cache(cache_path: Path) -> tuple[bool, dict[str, TrackEntry], str]:
    old_cache_path = RekordboxLibrary.CACHE_PATH
    try:
        RekordboxLibrary.CACHE_PATH = cache_path
        lib = RekordboxLibrary()
        loaded = lib.try_load_cache()
        return loaded, dict(lib.tracks), lib.xml_path
    finally:
        RekordboxLibrary.CACHE_PATH = old_cache_path


def _library_cache_candidates(explicit: Path | None) -> list[Path]:
    if explicit is not None:
        return [explicit.expanduser()]
    primary = RekordboxLibrary.CACHE_PATH.expanduser()
    return [primary, primary.with_suffix(primary.suffix + ".v1bak")]


def _select_labeled_cache(
    ids: Sequence[str],
    vectors: np.ndarray,
    *,
    min_label_size: int,
    cache_path: Path | None,
) -> dict[str, Any]:
    candidates: list[dict[str, Any]] = []
    for path in _library_cache_candidates(cache_path):
        loaded, tracks, source_path = _load_library_cache(path)
        if loaded:
            subset = prepare_labeled_subset(
                ids,
                vectors,
                tracks,
                min_label_size=min_label_size,
            )
        else:
            subset = {
                "ids": [],
                "labels": [],
                "vectors": np.zeros((0, vectors.shape[1]), dtype=np.float32),
                "label_counts_raw": {},
                "label_counts_kept": {},
                "label_source_counts": {},
                "selected_label_source": "none",
                "candidate_label_sources": {},
                "dropped_unknown": len(ids),
                "dropped_too_small": 0,
            }
        label_count = len(subset["label_counts_kept"])
        track_count = len(subset["ids"])
        candidates.append(
            {
                "cache_path": path,
                "cache_file": path.name,
                "loaded": loaded,
                "cached_tracks": len(tracks),
                "source_path": source_path,
                "source_summary": _summarize_source_path(source_path),
                "subset": subset,
                "label_count": label_count,
                "track_count": track_count,
                "status": (
                    "ok"
                    if loaded and label_count >= 2 and track_count >= 2
                    else "insufficient_labeled_subset"
                ),
            }
        )

    def sort_key(candidate: dict[str, Any]) -> tuple[int, int, int]:
        return (
            int(candidate["status"] == "ok"),
            int(candidate["label_count"]),
            int(candidate["track_count"]),
        )

    selected = max(candidates, key=sort_key)
    return {
        "selected": selected,
        "audit": [
            {
                "cache_file": c["cache_file"],
                "loaded": c["loaded"],
                "cached_tracks": c["cached_tracks"],
                "source_summary": c["source_summary"],
                "track_count": c["track_count"],
                "label_count": c["label_count"],
                "status": c["status"],
                "selected_label_source": c["subset"]["selected_label_source"],
                "candidate_label_sources": c["subset"]["candidate_label_sources"],
            }
            for c in candidates
        ],
    }


def build_report(
    *,
    min_label_size: int = 2,
    k_values: Sequence[int] = DEFAULT_K,
    triplet_path: Path | None = None,
    library_cache: Path | None = None,
) -> dict[str, Any]:
    store = open_store()
    try:
        ids, vectors = store._backend.load_all()
        snapshot = store.snapshot_hash()
        backend = store.backend_name
    finally:
        store.close()

    selected_cache = _select_labeled_cache(
        ids,
        vectors,
        min_label_size=min_label_size,
        cache_path=library_cache,
    )
    chosen = selected_cache["selected"]
    subset = chosen["subset"]
    eval_out = evaluate_vectors(
        subset["ids"],
        subset["vectors"],
        subset["labels"],
        k_values=k_values,
        triplet_path=triplet_path,
    )
    label_counts_kept = subset["label_counts_kept"]
    top_labels = [
        {"label": label, "count": count}
        for label, count in Counter(label_counts_kept).most_common()
    ]
    return {
        "schema": SCHEMA,
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "git_head": _git_head(),
        "store": {
            "backend": backend,
            "snapshot_hash": snapshot,
            "embedded_tracks": len(ids),
        },
        "library_cache": {
            "selected_cache_file": chosen["cache_file"],
            "loaded": chosen["loaded"],
            "cached_tracks": chosen["cached_tracks"],
            "source_summary": chosen["source_summary"],
            "candidate_audit": selected_cache["audit"],
        },
        "label_proxy": {
            "method": "auto_select_folder_parent_or_rekordbox_genre",
            "selected_label_source": subset["selected_label_source"],
            "min_label_size": min_label_size,
            "label_source_counts": subset["label_source_counts"],
            "candidate_label_sources": subset["candidate_label_sources"],
            "label_counts_raw": subset["label_counts_raw"],
            "label_counts_kept": label_counts_kept,
            "top_labels": top_labels[:40],
            "dropped_unknown": subset["dropped_unknown"],
            "dropped_too_small": subset["dropped_too_small"],
        },
        **eval_out,
        "notes": {
            "no_model_calls": True,
            "no_owner_input": True,
            "triplet_hook": "pass --triplets triplets.jsonl with anchor/positive/negative track_ids",
            "proxy_caveat": (
                "folder/genre labels are bootstrap labels, not human truth; "
                "use the triplet hook for small owner-labeled truth later"
            ),
        },
    }


def _parse_k_values(raw: str) -> tuple[int, ...]:
    values = tuple(int(part.strip()) for part in raw.split(",") if part.strip())
    if not values or any(k <= 0 for k in values):
        raise argparse.ArgumentTypeError("k values must be positive ints, e.g. 1,3,5")
    return values


def default_output_path() -> Path:
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    return ROOT / ".planning" / "eval-runs" / f"library-similarity-tagging-{stamp}" / "report.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--min-label-size", type=int, default=2)
    parser.add_argument("--k", type=_parse_k_values, default=DEFAULT_K)
    parser.add_argument("--triplets", type=Path, default=None)
    parser.add_argument(
        "--library-cache",
        type=Path,
        default=None,
        help=(
            "explicit RekordboxLibrary pickle cache; by default the bench audits "
            "library.pkl and library.pkl.v1bak and selects the best labeled subset"
        ),
    )
    parser.add_argument("--json", action="store_true", help="also print the full JSON report")
    args = parser.parse_args(argv)

    report = build_report(
        min_label_size=args.min_label_size,
        k_values=args.k,
        triplet_path=args.triplets,
        library_cache=args.library_cache,
    )
    out_path = args.out or default_output_path()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        centered = report["metrics"]["centered"]
        print(f"wrote {out_path}")
        print(
            "centered precision@k="
            f"{centered['precision_at_k']} "
            f"cluster_purity={centered['prototype_cluster_purity']} "
            f"loo_proto_acc={centered['prototype_accuracy_leave_one_out']}"
        )
    return 0 if report["status"] == "ok" else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
