# SPDX-License-Identifier: Apache-2.0
"""Compare vibemix smart-cue proposals against cue baseline XML snapshots.

This is the INTEL-19 measurement spine. It parses redacted/synthetic Rekordbox
XML snapshots, diffs POSITION_MARK records, loads vibemix SmartCueProposal-like
JSON, and emits a redacted scorecard. No Rekordbox UI, master.db, process memory,
audio, or local paths are touched.
"""

from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FIXTURE_DIR = ROOT / "tests" / "intel" / "fixtures"

CueBaseline = Literal["rekordbox_auto", "dj", "naive_anlz", "vibemix", "fallback"]
CueType = Literal["hot_cue", "memory_cue", "loop", "load", "unknown"]
DiffKind = Literal["added", "changed", "removed", "unchanged"]
DistanceBand = Literal["exact", "near", "phrase_near", "different", "missing"]


@dataclass(frozen=True, slots=True)
class BaselineCue:
    baseline: CueBaseline
    track_id: str
    slot: str | None
    type: CueType
    start_s: float
    end_s: float | None
    label: str
    source_xml_snapshot_id: str | None = None
    source_section_id: str | None = None
    confidence: float | None = None


@dataclass(frozen=True, slots=True)
class CueDiff:
    kind: DiffKind
    track_id: str
    slot: str | None
    before: BaselineCue | None
    after: BaselineCue | None


@dataclass(frozen=True, slots=True)
class SlotComparison:
    track_id: str
    slot: str
    vibemix: BaselineCue | None
    baseline: BaselineCue | None
    distance_s: float | None
    distance_beats: float | None
    distance_band: DistanceBand
    outcome: str


def compare_fixture_dir(fixture_dir: Path | str = DEFAULT_FIXTURE_DIR) -> dict[str, Any]:
    base = Path(fixture_dir)
    return compare_paths(
        before_xml=base / "cue_baseline_before.xml",
        after_xml=base / "cue_baseline_after.xml",
        proposals_json=base / "smart_cue_proposals.json",
        tracks_json=base / "tracks.json",
        source=f"fixture:{base.name}",
    )


def compare_paths(
    *,
    before_xml: Path | str,
    after_xml: Path | str,
    proposals_json: Path | str,
    tracks_json: Path | str,
    source: str = "private",
) -> dict[str, Any]:
    """Compare one before/after baseline pair with one vibemix proposal export."""
    tracks = _load_tracks(Path(tracks_json))
    before = parse_rekordbox_cues(
        before_xml,
        baseline="dj",
        snapshot_id="before",
    )
    after = parse_rekordbox_cues(
        after_xml,
        baseline="rekordbox_auto",
        snapshot_id="after",
    )
    diffs = diff_cue_snapshots(before, after)
    baseline_cues = tuple(
        diff.after for diff in diffs if diff.kind in {"added", "changed"} and diff.after
    )
    vibemix_cues = load_vibemix_proposals(proposals_json)
    return build_scorecard(
        baseline_cues=baseline_cues,
        vibemix_cues=vibemix_cues,
        tracks=tracks,
        diffs=diffs,
        source=source,
    )


def parse_rekordbox_cues(
    xml_path: Path | str,
    *,
    baseline: CueBaseline,
    snapshot_id: str | None = None,
) -> tuple[BaselineCue, ...]:
    """Parse POSITION_MARK records into redacted cue facts."""
    root = ET.parse(str(xml_path)).getroot()
    cues: list[BaselineCue] = []
    for track in root.findall(".//TRACK"):
        track_id = str(track.attrib.get("TrackID") or "").strip()
        if not track_id:
            continue
        for mark in track.findall("POSITION_MARK"):
            cues.append(
                BaselineCue(
                    baseline=baseline,
                    track_id=track_id,
                    slot=_slot_from_num(mark.attrib.get("Num")),
                    type=_mark_type(mark.attrib.get("Type"), mark.attrib.get("Num")),
                    start_s=_float_attr(mark.attrib.get("Start"), default=0.0),
                    end_s=_optional_float_attr(mark.attrib.get("End")),
                    label=str(mark.attrib.get("Name") or ""),
                    source_xml_snapshot_id=snapshot_id,
                )
            )
    return tuple(cues)


def diff_cue_snapshots(
    before: tuple[BaselineCue, ...], after: tuple[BaselineCue, ...]
) -> tuple[CueDiff, ...]:
    """Diff cue snapshots by track + slot + cue type."""
    before_map = {_diff_key(cue): cue for cue in before}
    after_map = {_diff_key(cue): cue for cue in after}
    diffs: list[CueDiff] = []
    for key in sorted(set(before_map) | set(after_map)):
        old = before_map.get(key)
        new = after_map.get(key)
        track_id, slot, _cue_type = key
        if old is None and new is not None:
            diffs.append(CueDiff("added", track_id, slot, None, new))
        elif old is not None and new is None:
            diffs.append(CueDiff("removed", track_id, slot, old, None))
        elif old is not None and new is not None:
            if (
                abs(old.start_s - new.start_s) > 1e-6
                or old.label != new.label
                or old.end_s != new.end_s
            ):
                diffs.append(CueDiff("changed", track_id, slot, old, new))
            else:
                diffs.append(CueDiff("unchanged", track_id, slot, old, new))
    return tuple(diffs)


def load_vibemix_proposals(path: Path | str) -> tuple[BaselineCue, ...]:
    """Load committed fixture proposals or exported SmartCueProposal JSON."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    proposals = raw if isinstance(raw, list) else [raw]
    cues: list[BaselineCue] = []
    for proposal in proposals:
        if not isinstance(proposal, dict):
            continue
        track_id = str(proposal.get("track_id") or "")
        cue_rows = proposal.get("cues")
        if cue_rows is None:
            cue_rows = proposal.get("anchors", [])
        if not track_id or not isinstance(cue_rows, list):
            continue
        for cue in cue_rows:
            if not isinstance(cue, dict):
                continue
            slot = cue.get("slot")
            start_s = cue.get("start_s")
            if not isinstance(slot, str) or start_s is None:
                continue
            cues.append(
                BaselineCue(
                    baseline="vibemix",
                    track_id=track_id,
                    slot=slot[:1].upper(),
                    type="hot_cue",
                    start_s=float(start_s),
                    end_s=_optional_float_attr(cue.get("end_s")),
                    label=str(cue.get("label") or cue.get("role") or slot),
                    source_section_id=cue.get("section_id")
                    if isinstance(cue.get("section_id"), str)
                    else cue.get("source_section_id")
                    if isinstance(cue.get("source_section_id"), str)
                    else None,
                    confidence=_optional_float_attr(cue.get("confidence")),
                )
            )
    return tuple(cues)


def build_scorecard(
    *,
    baseline_cues: tuple[BaselineCue, ...],
    vibemix_cues: tuple[BaselineCue, ...],
    tracks: dict[str, dict[str, Any]],
    diffs: tuple[CueDiff, ...] = (),
    source: str,
) -> dict[str, Any]:
    comparisons = compare_cue_sets(
        vibemix_cues=vibemix_cues,
        baseline_cues=baseline_cues,
        tracks=tracks,
    )
    per_track: dict[str, dict[str, Any]] = {}
    for track_id in sorted({cue.track_id for cue in baseline_cues + vibemix_cues}):
        track_comparisons = [item for item in comparisons if item.track_id == track_id]
        per_track[track_id] = {
            "genre": tracks.get(track_id, {}).get("genre", "unknown"),
            "baseline_cue_count": sum(1 for cue in baseline_cues if cue.track_id == track_id),
            "vibemix_cue_count": sum(1 for cue in vibemix_cues if cue.track_id == track_id),
            "required_slots_filled": sorted(
                cue.slot
                for cue in vibemix_cues
                if cue.track_id == track_id and cue.slot in {"A", "D", "F"}
            ),
            "review_required_count": sum(
                1
                for cue in vibemix_cues
                if cue.track_id == track_id
                and (cue.confidence is not None and cue.confidence < 0.78)
            ),
            "comparisons": [comparison_to_dict(item) for item in track_comparisons],
        }

    return {
        "schema": "intel_cue_baseline_compare_v1",
        "source": source,
        "valid": bool(comparisons) and bool(vibemix_cues),
        "privacy": {"local_paths_redacted": True},
        "totals": {
            "tracks": len(per_track),
            "baseline_cues": len(baseline_cues),
            "vibemix_cues": len(vibemix_cues),
            "snapshot_added": sum(1 for diff in diffs if diff.kind == "added"),
            "snapshot_changed": sum(1 for diff in diffs if diff.kind == "changed"),
            "snapshot_removed": sum(1 for diff in diffs if diff.kind == "removed"),
        },
        "outcomes": _count_values(item.outcome for item in comparisons),
        "distance_bands": _count_values(item.distance_band for item in comparisons),
        "comparative_lift": _comparative_lift(comparisons),
        "per_slot": _per_slot(comparisons),
        "per_track": per_track,
    }


def compare_cue_sets(
    *,
    vibemix_cues: tuple[BaselineCue, ...],
    baseline_cues: tuple[BaselineCue, ...],
    tracks: dict[str, dict[str, Any]],
) -> tuple[SlotComparison, ...]:
    by_track_slot_vibe = _index_by_track_slot(vibemix_cues)
    by_track_slot_base = _index_by_track_slot(baseline_cues)
    keys = sorted(set(by_track_slot_vibe) | set(by_track_slot_base))
    comparisons: list[SlotComparison] = []
    for track_id, slot in keys:
        vibe = by_track_slot_vibe.get((track_id, slot))
        base = by_track_slot_base.get((track_id, slot))
        bpm = _optional_float_attr(tracks.get(track_id, {}).get("bpm"))
        if vibe is None or base is None:
            comparisons.append(
                SlotComparison(
                    track_id=track_id,
                    slot=slot,
                    vibemix=vibe,
                    baseline=base,
                    distance_s=None,
                    distance_beats=None,
                    distance_band="missing",
                    outcome="vibemix_missing" if vibe is None else "baseline_missing",
                )
            )
            continue
        distance_s = abs(vibe.start_s - base.start_s)
        distance_beats = distance_s * bpm / 60.0 if bpm and bpm > 0 else None
        band = _distance_band(distance_s=distance_s, distance_beats=distance_beats, bpm=bpm)
        comparisons.append(
            SlotComparison(
                track_id=track_id,
                slot=slot,
                vibemix=vibe,
                baseline=base,
                distance_s=round(distance_s, 6),
                distance_beats=round(distance_beats, 6) if distance_beats is not None else None,
                distance_band=band,
                outcome="both_present_" + band,
            )
        )
    return tuple(comparisons)


def comparison_to_dict(comparison: SlotComparison) -> dict[str, Any]:
    data = asdict(comparison)
    data["vibemix"] = _cue_to_public_dict(comparison.vibemix)
    data["baseline"] = _cue_to_public_dict(comparison.baseline)
    return data


def _cue_to_public_dict(cue: BaselineCue | None) -> dict[str, Any] | None:
    if cue is None:
        return None
    return {
        "baseline": cue.baseline,
        "slot": cue.slot,
        "type": cue.type,
        "start_s": cue.start_s,
        "end_s": cue.end_s,
        "label": cue.label,
        "source_section_id": cue.source_section_id,
        "confidence": cue.confidence,
    }


def _load_tracks(path: Path) -> dict[str, dict[str, Any]]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    return {
        str(row["track_id"]): row for row in rows if isinstance(row, dict) and "track_id" in row
    }


def _index_by_track_slot(cues: tuple[BaselineCue, ...]) -> dict[tuple[str, str], BaselineCue]:
    out = {}
    for cue in cues:
        if cue.slot is None:
            continue
        key = (cue.track_id, cue.slot)
        prev = out.get(key)
        if prev is None or cue.start_s < prev.start_s:
            out[key] = cue
    return out


def _diff_key(cue: BaselineCue) -> tuple[str, str | None, CueType]:
    return (cue.track_id, cue.slot, cue.type)


def _mark_type(raw_type: Any, raw_num: Any) -> CueType:
    value = str(raw_type if raw_type is not None else "").lower()
    if value in {"4", "loop"}:
        return "loop"
    if value in {"3", "load"}:
        return "load"
    if value in {"0", "cue"}:
        num = _int_or_none(raw_num)
        return "memory_cue" if num == -1 else "hot_cue"
    return "unknown"


def _slot_from_num(raw_num: Any) -> str | None:
    num = _int_or_none(raw_num)
    if num is None or num < 0:
        return None
    if 0 <= num < 16:
        return chr(ord("A") + num)
    return None


def _distance_band(
    *, distance_s: float, distance_beats: float | None, bpm: float | None
) -> DistanceBand:
    if distance_beats is not None:
        if distance_beats <= 1:
            return "exact"
        if distance_beats <= 4:
            return "near"
        if distance_beats <= 16:
            return "phrase_near"
        return "different"
    if distance_s <= 0.5:
        return "exact"
    if distance_s <= 2.0:
        return "near"
    if bpm and bpm > 0 and distance_s <= 16 * 60.0 / bpm:
        return "phrase_near"
    return "different"


def _per_slot(comparisons: tuple[SlotComparison, ...]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for slot in sorted({item.slot for item in comparisons}):
        slot_items = [item for item in comparisons if item.slot == slot]
        out[slot] = {
            "count": len(slot_items),
            "outcomes": _count_values(item.outcome for item in slot_items),
            "distance_bands": _count_values(item.distance_band for item in slot_items),
        }
    return out


def _comparative_lift(comparisons: tuple[SlotComparison, ...]) -> dict[str, int]:
    counts = {
        "vibemix_kept_and_baseline_missing": 0,
        "baseline_kept_and_vibemix_missing": 0,
        "both_kept_same_or_near": 0,
        "both_present_phrase_near": 0,
        "both_present_different": 0,
    }
    for item in comparisons:
        if item.outcome == "baseline_missing":
            counts["vibemix_kept_and_baseline_missing"] += 1
        elif item.outcome == "vibemix_missing":
            counts["baseline_kept_and_vibemix_missing"] += 1
        elif item.distance_band in {"exact", "near"}:
            counts["both_kept_same_or_near"] += 1
        elif item.distance_band == "phrase_near":
            counts["both_present_phrase_near"] += 1
        elif item.distance_band == "different":
            counts["both_present_different"] += 1
    return counts


def _count_values(values: Any) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        key = str(value)
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def _float_attr(raw: Any, *, default: float) -> float:
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


def _optional_float_attr(raw: Any) -> float | None:
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _int_or_none(raw: Any) -> int | None:
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture-dir", type=Path, default=DEFAULT_FIXTURE_DIR)
    parser.add_argument("--before", type=Path, help="Before Rekordbox XML snapshot")
    parser.add_argument("--after", type=Path, help="After/baseline Rekordbox XML snapshot")
    parser.add_argument("--proposals", type=Path, help="Vibemix smart-cue proposal JSON")
    parser.add_argument("--tracks", type=Path, help="Redacted track metadata JSON")
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    args = parser.parse_args(argv)

    explicit_paths = (args.before, args.after, args.proposals, args.tracks)
    if any(explicit_paths):
        if not all(explicit_paths):
            parser.error("--before, --after, --proposals, and --tracks must be provided together")
        result = compare_paths(
            before_xml=args.before,
            after_xml=args.after,
            proposals_json=args.proposals,
            tracks_json=args.tracks,
            source="private:redacted",
        )
    else:
        result = compare_fixture_dir(args.fixture_dir)
    if args.json:
        json.dump(result, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    else:
        totals = result["totals"]
        print(
            "Cue baseline compare: "
            f"tracks={totals['tracks']} baseline={totals['baseline_cues']} "
            f"vibemix={totals['vibemix_cues']} outcomes={result['outcomes']}"
        )
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    raise SystemExit(main())
