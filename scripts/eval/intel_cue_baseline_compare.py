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
import math
import re
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
SMART_CUE_SLOTS = frozenset("ABCDEFGH")
PRIVATE_PAYLOAD_PATTERNS = (
    re.compile(r"/Users/[^\"'\s<>]+"),
    re.compile(r"/Volumes/[^\"'\s<>]+"),
    re.compile(r"[A-Za-z]:\\\\[^\"'\s<>]+"),
    re.compile(r"file://[^\"'\s<>]+", re.I),
    re.compile(r"\braw_(?:audio|vector)s?\b", re.I),
)
AUDIO_PATH_PATTERN = re.compile(r"\.(?:wav|aiff|aif|mp3|flac)\b", re.I)


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
    track_rows = _load_json_list(Path(tracks_json))
    tracks = _tracks_index(track_rows)
    proposal_rows = _load_json_list(Path(proposals_json))
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
    vibemix_cues = _vibemix_cues_from_rows(proposal_rows)
    evidence_errors = _evidence_shape_errors(
        before_xml=Path(before_xml),
        after_xml=Path(after_xml),
        track_rows=track_rows,
        proposal_rows=proposal_rows,
        tracks=tracks,
        before_cues=before,
        after_cues=after,
    )
    return build_scorecard(
        baseline_cues=baseline_cues,
        vibemix_cues=vibemix_cues,
        tracks=tracks,
        diffs=diffs,
        source=source,
        evidence_errors=evidence_errors,
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
    return _vibemix_cues_from_rows(_load_json_list(Path(path)))


def _vibemix_cues_from_rows(proposals: list[dict[str, Any]]) -> tuple[BaselineCue, ...]:
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
    evidence_errors: tuple[str, ...] = (),
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
        "valid": bool(comparisons) and bool(vibemix_cues) and not evidence_errors,
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
        "evidence_errors": tuple(evidence_errors),
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


def _load_json_list(path: Path) -> list[dict[str, Any]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    rows = raw if isinstance(raw, list) else [raw]
    return [row for row in rows if isinstance(row, dict)]


def _tracks_index(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(row["track_id"]): row for row in rows if "track_id" in row}


def _evidence_shape_errors(
    *,
    before_xml: Path,
    after_xml: Path,
    track_rows: list[dict[str, Any]],
    proposal_rows: list[dict[str, Any]],
    tracks: dict[str, dict[str, Any]],
    before_cues: tuple[BaselineCue, ...],
    after_cues: tuple[BaselineCue, ...],
) -> tuple[str, ...]:
    errors: list[str] = []
    errors.extend(_private_payload_errors(track_rows, "tracks"))
    errors.extend(_private_payload_errors(proposal_rows, "proposals"))
    errors.extend(_xml_private_payload_errors(before_xml, "before_xml"))
    errors.extend(_xml_private_payload_errors(after_xml, "after_xml"))
    errors.extend(_duplicate_field_errors(track_rows, key="track_id", label="track"))
    errors.extend(_duplicate_field_errors(proposal_rows, key="proposal_id", label="proposal"))
    errors.extend(_track_row_errors(track_rows))
    errors.extend(_proposal_row_errors(proposal_rows, tracks=tracks))
    errors.extend(_xml_mark_errors(before_xml, label="before_xml", tracks=tracks))
    errors.extend(_xml_mark_errors(after_xml, label="after_xml", tracks=tracks))
    errors.extend(_duplicate_cue_key_errors(before_cues, label="before_xml"))
    errors.extend(_duplicate_cue_key_errors(after_cues, label="after_xml"))
    return tuple(errors)


def _track_row_errors(rows: list[dict[str, Any]]) -> tuple[str, ...]:
    errors: list[str] = []
    for index, row in enumerate(rows):
        track_id = str(row.get("track_id") or f"<track_{index}>")
        if not row.get("track_id"):
            errors.append(f"{track_id}:missing_track_id")
        bpm = row.get("bpm")
        if bpm is not None and not _is_finite_number(bpm):
            errors.append(f"{track_id}:nonfinite_bpm")
        duration = row.get("duration_s")
        if duration is not None:
            parsed = _finite_number_or_none(duration)
            if parsed is None:
                errors.append(f"{track_id}:nonfinite_duration")
            elif parsed <= 0:
                errors.append(f"{track_id}:nonpositive_duration")
    return tuple(errors)


def _proposal_row_errors(
    rows: list[dict[str, Any]], *, tracks: dict[str, dict[str, Any]]
) -> tuple[str, ...]:
    errors: list[str] = []
    for index, row in enumerate(rows):
        proposal_id = str(row.get("proposal_id") or f"<proposal_{index}>")
        track_id = str(row.get("track_id") or "")
        if not track_id:
            errors.append(f"{proposal_id}:missing_track_id")
        elif track_id not in tracks:
            errors.append(f"{proposal_id}:{track_id}:unknown_track_id")
        cue_rows = row.get("cues")
        if cue_rows is None:
            cue_rows = row.get("anchors")
        if not isinstance(cue_rows, list):
            errors.append(f"{proposal_id}:missing_cues")
            continue
        slots: list[str] = []
        duration = _finite_number_or_none(tracks.get(track_id, {}).get("duration_s"))
        for cue_index, cue in enumerate(cue_rows):
            if not isinstance(cue, dict):
                errors.append(f"{proposal_id}:cue_{cue_index}:invalid_cue")
                continue
            cue_label = str(cue.get("slot") or f"cue_{cue_index}")
            slot = cue.get("slot")
            if not isinstance(slot, str) or slot[:1].upper() not in SMART_CUE_SLOTS:
                errors.append(f"{proposal_id}:{cue_label}:invalid_slot")
            else:
                slots.append(slot[:1].upper())
            start_s = _finite_number_or_none(cue.get("start_s"))
            if start_s is None:
                errors.append(f"{proposal_id}:{cue_label}:nonfinite_start_s")
            elif duration is not None and start_s > duration:
                errors.append(f"{proposal_id}:{cue_label}:start_after_duration")
            end_s = cue.get("end_s")
            parsed_end = _finite_number_or_none(end_s) if end_s is not None else None
            if end_s is not None and parsed_end is None:
                errors.append(f"{proposal_id}:{cue_label}:nonfinite_end_s")
            elif parsed_end is not None and start_s is not None and parsed_end < start_s:
                errors.append(f"{proposal_id}:{cue_label}:end_before_start")
            confidence = cue.get("confidence")
            parsed_confidence = (
                _finite_number_or_none(confidence) if confidence is not None else None
            )
            if confidence is not None and parsed_confidence is None:
                errors.append(f"{proposal_id}:{cue_label}:nonfinite_confidence")
            elif parsed_confidence is not None and not 0.0 <= parsed_confidence <= 1.0:
                errors.append(f"{proposal_id}:{cue_label}:confidence_out_of_range")
        errors.extend(f"{proposal_id}:{error}" for error in _duplicate_values(slots, label="slot"))
    return tuple(errors)


def _xml_mark_errors(
    path: Path, *, label: str, tracks: dict[str, dict[str, Any]]
) -> tuple[str, ...]:
    errors: list[str] = []
    root = ET.parse(str(path)).getroot()
    for track_index, track in enumerate(root.findall(".//TRACK")):
        track_id = str(track.attrib.get("TrackID") or "")
        track_label = track_id or f"<track_{track_index}>"
        if not track_id:
            errors.append(f"{label}:{track_label}:missing_track_id")
        elif track_id not in tracks:
            errors.append(f"{label}:{track_id}:unknown_track_id")
        duration = _finite_number_or_none(tracks.get(track_id, {}).get("duration_s"))
        for mark_index, mark in enumerate(track.findall("POSITION_MARK")):
            mark_label = str(mark.attrib.get("Name") or f"mark_{mark_index}")
            mark_id = f"{label}:{track_label}:{mark_label}"
            start_s = _finite_number_or_none(mark.attrib.get("Start"))
            if start_s is None:
                errors.append(f"{mark_id}:nonfinite_start")
            elif duration is not None and start_s > duration:
                errors.append(f"{mark_id}:start_after_duration")
            end_s = mark.attrib.get("End")
            parsed_end = _finite_number_or_none(end_s) if end_s is not None else None
            if end_s is not None and parsed_end is None:
                errors.append(f"{mark_id}:nonfinite_end")
            elif parsed_end is not None and start_s is not None and parsed_end < start_s:
                errors.append(f"{mark_id}:end_before_start")
    return tuple(errors)


def _duplicate_field_errors(rows: list[dict[str, Any]], *, key: str, label: str) -> tuple[str, ...]:
    values = [str(row.get(key) or "") for row in rows if row.get(key)]
    return _duplicate_values(values, label=label)


def _duplicate_values(values: list[str], *, label: str) -> tuple[str, ...]:
    seen: set[str] = set()
    errors: list[str] = []
    for value in values:
        if value in seen:
            errors.append(f"{value}:duplicate_{label}")
        seen.add(value)
    return tuple(errors)


def _duplicate_cue_key_errors(cues: tuple[BaselineCue, ...], *, label: str) -> tuple[str, ...]:
    keys = [":".join((cue.track_id, cue.slot or "memory", cue.type)) for cue in cues]
    return tuple(f"{label}:{error}" for error in _duplicate_values(keys, label="cue"))


def _private_payload_errors(value: Any, label: str) -> tuple[str, ...]:
    errors: list[str] = []
    for text in _iter_strings(value):
        if text.startswith("fixture://"):
            continue
        if any(pattern.search(text) for pattern in PRIVATE_PAYLOAD_PATTERNS):
            errors.append(f"{label}:private_payload_present")
            break
        if AUDIO_PATH_PATTERN.search(text) and ("/" in text or "\\" in text):
            errors.append(f"{label}:private_audio_path_present")
            break
    return tuple(errors)


def _xml_private_payload_errors(path: Path, label: str) -> tuple[str, ...]:
    root = ET.parse(str(path)).getroot()
    return _private_payload_errors(root.attrib | _xml_attributes(root), label)


def _xml_attributes(root: ET.Element) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for index, item in enumerate(root.iter()):
        for key, value in item.attrib.items():
            attrs[f"{index}:{key}"] = value
    return attrs


def _iter_strings(value: Any) -> tuple[str, ...]:
    strings: list[str] = []
    if isinstance(value, str):
        return (value,)
    if isinstance(value, dict):
        for key, item in value.items():
            strings.extend(_iter_strings(str(key)))
            strings.extend(_iter_strings(item))
    elif isinstance(value, list | tuple):
        for item in value:
            strings.extend(_iter_strings(item))
    return tuple(strings)


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
        value = float(raw)
    except (TypeError, ValueError):
        return default
    return value if math.isfinite(value) else default


def _optional_float_attr(raw: Any) -> float | None:
    if raw is None:
        return None
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def _finite_number_or_none(raw: Any) -> float | None:
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def _is_finite_number(raw: Any) -> bool:
    return _finite_number_or_none(raw) is not None


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
    return 0 if result.get("valid") is True else 1


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    raise SystemExit(main())
