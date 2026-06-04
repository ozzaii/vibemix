# SPDX-License-Identifier: Apache-2.0
"""Measure local Rekordbox ANLZ PSSI structure against DJ cue references.

This is an eval/proof tool, not product wiring. It answers two questions:

* Is ANLZ PSSI phrase structure available for tracks in the current library cache?
* When DJ-authored cue references exist, how closely do those cues agree with
  the ANLZ phrase anchors?

If the local cache has no DJ cue references, the score is an honest null. That
is materially different from 0.0: with no reference cues there is no agreement
number to claim.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from collections.abc import Iterable, Mapping
from pathlib import Path
from statistics import mean
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from vibemix.library.anlz_ingest import (  # noqa: E402
    AnlzIndex,
    anchors_from_anlz,
    build_anlz_index,
    dj_cue_anchors_from_anlz,
    match_track_to_anlz,
)
from vibemix.library.cue_agreement import cue_agreement, weak_labels  # noqa: E402
from vibemix.library.excerpt import anchors_for_track  # noqa: E402
from vibemix.library.rekordbox import RekordboxLibrary, TrackEntry  # noqa: E402

SCHEMA = "anlz_cue_agreement_v1"
STRUCTURAL_CUE_TYPES = frozenset({"cue", "loop"})


def _track_has_structural_cues(track: TrackEntry) -> bool:
    return any(cue.type in STRUCTURAL_CUE_TYPES for cue in track.cues or ())


def _dj_anchors_for_track(track: TrackEntry, *, max_cues: int) -> list[Any]:
    if not _track_has_structural_cues(track):
        return []
    return [
        anchor
        for anchor in anchors_for_track(track, max_cues=max_cues)
        if getattr(anchor, "source", None) == "dj"
    ]


def _cue_source_counts(tracks: Iterable[TrackEntry]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for track in tracks:
        for cue in track.cues or ():
            counts[str(getattr(cue, "source", "") or "")] += 1
    return counts


def evaluate_anlz_cue_agreement(
    tracks: Mapping[str, TrackEntry],
    anlz_index: AnlzIndex,
    *,
    max_cues: int = 8,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    scored: list[float] = []
    offsets: list[float] = []
    weak_count = 0
    matched_tracks = 0
    first_fill_tracks = 0
    tracks_with_pssi_anchors = 0
    anlz_anchor_count = 0
    dj_reference_tracks = 0
    cache_dj_reference_tracks = 0
    sidecar_dj_reference_tracks = 0
    sidecar_dj_anchor_count = 0

    for track_id, track in sorted(tracks.items(), key=lambda item: item[0]):
        meta = match_track_to_anlz(track, anlz_index)
        if meta is None:
            continue
        matched_tracks += 1
        anlz_anchors = anchors_from_anlz(track, meta, max_cues=max_cues)
        if not anlz_anchors:
            continue
        tracks_with_pssi_anchors += 1
        anlz_anchor_count += len(anlz_anchors)
        if not _track_has_structural_cues(track):
            first_fill_tracks += 1

        dj_anchors = _dj_anchors_for_track(track, max_cues=max_cues)
        reference_source = "cache"
        if dj_anchors:
            cache_dj_reference_tracks += 1
        else:
            dj_anchors = dj_cue_anchors_from_anlz(track, meta, max_cues=max_cues)
            reference_source = "anlz_pcob_pco2"
            sidecar_dj_anchor_count += len(dj_anchors)
            if dj_anchors:
                sidecar_dj_reference_tracks += 1
        if dj_anchors:
            dj_reference_tracks += 1
        result = cue_agreement(dj_anchors, anlz_anchors)
        weak = weak_labels(result)
        weak_count += len(weak)
        if result.agreement_score is not None:
            scored.append(float(result.agreement_score))
        if result.mean_abs_offset_s is not None:
            offsets.append(float(result.mean_abs_offset_s))

        if dj_anchors or len(rows) < 12:
            rows.append(
                {
                    "track_id": track_id,
                    "title": track.title,
                    "filepath_basename": Path(track.filepath).name,
                    "anlz_anchor_count": len(anlz_anchors),
                    "dj_anchor_count": len(dj_anchors),
                    "dj_reference_source": reference_source if dj_anchors else None,
                    "matched": len(result.matched),
                    "dj_only": len(result.dj_only),
                    "anlz_only": len(result.auto_only),
                    "agreement_score": (
                        round(result.agreement_score, 6)
                        if result.agreement_score is not None
                        else None
                    ),
                    "mean_abs_offset_s": (
                        round(result.mean_abs_offset_s, 6)
                        if result.mean_abs_offset_s is not None
                        else None
                    ),
                }
            )

    status = "ok" if scored else "honest_null_no_dj_reference_cues"
    return {
        "schema": SCHEMA,
        "cache_loaded": True,
        "cached_tracks": len(tracks),
        "anlz_index_tracks": len(anlz_index.by_basename),
        "anlz_index_metas": sum(len(items) for items in anlz_index.by_basename.values()),
        "anlz_matched_cached_tracks": matched_tracks,
        "tracks_with_pssi_anchors": tracks_with_pssi_anchors,
        "pssi_anchor_count": anlz_anchor_count,
        "pssi_first_fill_candidate_tracks": first_fill_tracks,
        "cached_cue_source_counts": dict(sorted(_cue_source_counts(tracks.values()).items())),
        "dj_reference_tracks": dj_reference_tracks,
        "cache_dj_reference_tracks": cache_dj_reference_tracks,
        "anlz_sidecar_dj_reference_tracks": sidecar_dj_reference_tracks,
        "anlz_sidecar_dj_anchor_count": sidecar_dj_anchor_count,
        "cue_agreement_scored_tracks": len(scored),
        "cue_agreement_mean_score": round(mean(scored), 6) if scored else None,
        "cue_agreement_mean_abs_offset_s": round(mean(offsets), 6) if offsets else None,
        "cue_agreement_weak_labels": weak_count,
        "status": status,
        "notes": {
            "agreement_score_is_not_fabricated_without_dj_refs": not scored,
            "anlz_first_fill_already_in_current_source": True,
            "compares": "dj_or_anlz_pcob_pco2_cues_vs_anlz_pssi_phrase_anchors",
        },
        "sample_rows": rows[:40],
    }


def load_cached_library() -> tuple[dict[str, TrackEntry], str | None]:
    lib = RekordboxLibrary()
    if not lib.try_load_cache():
        return {}, None
    return dict(lib.tracks), lib.xml_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--anlz-root", type=Path, default=None)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)

    tracks, source_path = load_cached_library()
    if not tracks:
        report = {
            "schema": SCHEMA,
            "cache_loaded": False,
            "cached_tracks": 0,
            "status": "blocked_no_library_cache",
        }
    else:
        index = build_anlz_index(args.anlz_root)
        report = evaluate_anlz_cue_agreement(tracks, index)
        report["library_source_path"] = source_path

    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    sys.stdout.write(text)
    return 0 if report.get("status") != "blocked_no_library_cache" else 2


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    raise SystemExit(main())
