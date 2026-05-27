# SPDX-License-Identifier: Apache-2.0
"""Audit Rekordbox ANLZ structure coverage without leaking private paths.

The product parser (`vibemix.library.anlz_ingest`) is intentionally quiet: it
returns `None` for ordinary missing/partial analysis. This script is the data
excellence lens around that parser. It reports whether a library has enough
PSSI/PQTZ/PPTH structure to trust ANLZ as a cue source, and it keeps local audio
paths out of the emitted JSON.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FIXTURE_DIR = ROOT / "tests" / "intel" / "fixtures"

HIGH_CONFIDENCE_FLOOR = 0.80
MEDIUM_CONFIDENCE_FLOOR = 0.60
LOW_CONFIDENCE_FLOOR = 0.45


@dataclass(frozen=True, slots=True)
class PhraseRecord:
    role: str
    confidence: float | None
    mood: str | None = None


@dataclass(frozen=True, slots=True)
class BundleRecord:
    source_id: str
    ppth_path: str | None
    has_ppth: bool
    has_pssi: bool
    has_pqtz: bool
    parsed: bool
    phrases: tuple[PhraseRecord, ...]
    parse_error: str | None = None


def audit_fixture_dir(fixture_dir: Path | str = DEFAULT_FIXTURE_DIR) -> dict[str, Any]:
    """Audit the public synthetic fixture corpus' ANLZ-like records."""
    base = Path(fixture_dir)
    records = []
    for item in _load_json(base / "anlz_bundles.json"):
        ppth_path = _string_or_none(item.get("ppth_path"))
        pssi = item.get("pssi") if isinstance(item, dict) else None
        pqtz = item.get("pqtz") if isinstance(item, dict) else None
        pqtz_beat_count = _positive_int(pqtz.get("beat_count")) if isinstance(pqtz, dict) else 0
        phrases = []
        if isinstance(pssi, dict):
            for phrase in pssi.get("phrases", []):
                if not isinstance(phrase, dict):
                    continue
                phrases.append(
                    PhraseRecord(
                        role=str(phrase.get("role") or "unmapped"),
                        confidence=_float_or_none(phrase.get("confidence")),
                        mood=_string_or_none(pssi.get("mood")),
                    )
                )
        records.append(
            BundleRecord(
                source_id=str(item.get("track_id") or "fixture-unknown"),
                ppth_path=ppth_path,
                has_ppth=bool(ppth_path),
                has_pssi=isinstance(pssi, dict) and bool(pssi.get("phrases")),
                has_pqtz=pqtz_beat_count > 0,
                parsed=bool(ppth_path)
                and isinstance(pssi, dict)
                and bool(pssi.get("phrases"))
                and isinstance(pqtz, dict)
                and pqtz_beat_count > 0,
                phrases=tuple(phrases),
            )
        )
    return summarize_records(records, source=f"fixture:{_manifest_hash(base)}")


def audit_anlz_root(root: Path | str | None = None) -> dict[str, Any]:
    """Audit real Rekordbox `.EXT`/`.DAT` bundles under an ANLZ root."""
    from vibemix.library.anlz_ingest import iter_anlz_ext_files

    records = [
        _probe_real_bundle(path) for path in iter_anlz_ext_files(Path(root) if root else None)
    ]
    return summarize_records(records, source=f"anlz-root:{_path_hash(root)}")


def summarize_records(records: list[BundleRecord], *, source: str) -> dict[str, Any]:
    total = len(records)
    parsed = sum(1 for record in records if record.parsed)
    parse_errors = sum(1 for record in records if record.parse_error)
    all_phrases = [phrase for record in records for phrase in record.phrases]
    evidence_errors = _evidence_shape_errors(records)

    collision_groups: dict[str, int] = {}
    for record in records:
        if not record.ppth_path:
            continue
        key = _basename_key(record.ppth_path)
        if key:
            collision_groups[key] = collision_groups.get(key, 0) + 1
    collision_hashes = sorted(
        _short_hash(key) for key, count in collision_groups.items() if count > 1
    )

    return {
        "schema": "intel_anlz_audit_v1",
        "source": source,
        "valid": total > 0 and parsed > 0 and parse_errors == 0 and not evidence_errors,
        "privacy": {
            "local_paths_redacted": True,
            "collision_keys_hashed": True,
        },
        "totals": {
            "bundles": total,
            "parsed_bundles": parsed,
            "skipped_bundles": total - parsed,
            "parse_errors": parse_errors,
            "phrases": len(all_phrases),
        },
        "coverage": {
            "ppth": _coverage(sum(1 for record in records if record.has_ppth), total),
            "pssi": _coverage(sum(1 for record in records if record.has_pssi), total),
            "pqtz": _coverage(sum(1 for record in records if record.has_pqtz), total),
            "complete": _coverage(parsed, total),
            "parse_error_rate": _rate(parse_errors, total),
        },
        "path_collisions": {
            "collision_count": len(collision_hashes),
            "collision_key_hashes": collision_hashes,
        },
        "evidence_errors": tuple(evidence_errors),
        "phrase_quality": {
            "roles": _count_by(all_phrases, "role"),
            "moods": _count_by(all_phrases, "mood"),
            "confidence_buckets": _confidence_buckets(all_phrases),
            "avg_phrases_per_parsed_bundle": round(len(all_phrases) / parsed, 3) if parsed else 0.0,
        },
    }


def _probe_real_bundle(ext_path: Path) -> BundleRecord:
    from vibemix.library.anlz_ingest import parse_anlz_bundle

    source_id = _short_hash(str(ext_path))
    dat_path = ext_path.with_suffix(".DAT")
    has_pqtz = False
    has_ppth = False
    has_pssi = False
    ppth_path = None
    parse_error = None

    try:
        from pyrekordbox.anlz import AnlzFile

        ext_anlz = AnlzFile.parse_file(ext_path)
        ppth_tags = _tag_list(ext_anlz, "PPTH")
        pssi_tags = _tag_list(ext_anlz, "PSSI")
        has_ppth = bool(ppth_tags)
        has_pssi = bool(pssi_tags)
        if ppth_tags:
            ppth_path = _string_or_none(_value(ppth_tags[0], "path"))

        if dat_path.exists():
            dat_anlz = AnlzFile.parse_file(dat_path)
            has_pqtz = bool(_tag_list(dat_anlz, "PQTZ"))
    except Exception as exc:
        parse_error = exc.__class__.__name__

    meta = parse_anlz_bundle(ext_path) if parse_error is None else None
    phrases: tuple[PhraseRecord, ...] = ()
    if meta is not None:
        ppth_path = meta.ppth_path
        phrases = tuple(
            PhraseRecord(
                role=str(phrase.cue_label or "unmapped"),
                confidence=float(phrase.confidence),
                mood=_mood_name(phrase.mood),
            )
            for phrase in meta.phrases
        )

    return BundleRecord(
        source_id=source_id,
        ppth_path=ppth_path,
        has_ppth=has_ppth,
        has_pssi=has_pssi,
        has_pqtz=has_pqtz,
        parsed=meta is not None,
        phrases=phrases,
        parse_error=parse_error,
    )


def _tag_list(anlz_file: Any, key: str) -> list[Any]:
    try:
        return list(anlz_file.getall_tags(key))
    except Exception:
        return []


def _value(obj: Any, key: str) -> Any:
    if isinstance(obj, dict):
        return obj.get(key)
    if hasattr(obj, key):
        return getattr(obj, key)
    try:
        return obj[key]
    except Exception:
        return None


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _evidence_shape_errors(records: list[BundleRecord]) -> tuple[str, ...]:
    errors: list[str] = []
    source_ids = [record.source_id for record in records if record.source_id]
    errors.extend(_duplicate_values(source_ids, label="source"))
    for record_index, record in enumerate(records):
        source_id = record.source_id or f"<bundle_{record_index}>"
        if not record.source_id:
            errors.append(f"{source_id}:missing_source_id")
        if record.parsed and record.parse_error:
            errors.append(f"{source_id}:parsed_with_parse_error")
        if record.parsed and not (record.has_ppth and record.has_pssi and record.has_pqtz):
            errors.append(f"{source_id}:parsed_missing_required_tags")
        for phrase_index, phrase in enumerate(record.phrases):
            phrase_id = f"{source_id}:phrase_{phrase_index}"
            if not phrase.role:
                errors.append(f"{phrase_id}:missing_role")
            confidence = phrase.confidence
            if confidence is None:
                continue
            if not math.isfinite(confidence):
                errors.append(f"{phrase_id}:nonfinite_confidence")
            elif not 0.0 <= confidence <= 1.0:
                errors.append(f"{phrase_id}:confidence_out_of_range")
    return tuple(errors)


def _duplicate_values(values: list[str], *, label: str) -> tuple[str, ...]:
    seen: set[str] = set()
    errors: list[str] = []
    for value in values:
        if value in seen:
            errors.append(f"{value}:duplicate_{label}")
        seen.add(value)
    return tuple(errors)


def _coverage(count: int, total: int) -> dict[str, float | int]:
    return {"count": count, "rate": _rate(count, total)}


def _rate(count: int, total: int) -> float:
    return round(count / total, 6) if total else 0.0


def _confidence_buckets(phrases: list[PhraseRecord]) -> dict[str, int]:
    buckets = {"high": 0, "medium": 0, "low": 0, "below_anchor_floor": 0, "unknown": 0}
    for phrase in phrases:
        confidence = phrase.confidence
        if confidence is None or not math.isfinite(confidence):
            buckets["unknown"] += 1
        elif confidence >= HIGH_CONFIDENCE_FLOOR:
            buckets["high"] += 1
        elif confidence >= MEDIUM_CONFIDENCE_FLOOR:
            buckets["medium"] += 1
        elif confidence >= LOW_CONFIDENCE_FLOOR:
            buckets["low"] += 1
        else:
            buckets["below_anchor_floor"] += 1
    return buckets


def _count_by(phrases: list[PhraseRecord], attr: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for phrase in phrases:
        value = getattr(phrase, attr)
        key = str(value or "unknown")
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def _basename_key(path: str) -> str:
    normalized = str(path).replace("\\", "/").rstrip("/")
    if not normalized:
        return ""
    return normalized.rsplit("/", 1)[-1].lower()


def _string_or_none(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _float_or_none(value: Any) -> float | None:
    if isinstance(value, int | float):
        return float(value)
    return None


def _positive_int(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return 0
    return max(parsed, 0)


def _mood_name(mood: int) -> str:
    return {1: "high", 2: "mid", 3: "low"}.get(int(mood), "unknown")


def _short_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", "surrogatepass")).hexdigest()[:12]


def _path_hash(path: Path | str | None) -> str:
    if path is None:
        return "default"
    return _short_hash(str(Path(path)))


def _manifest_hash(fixture_dir: Path) -> str:
    manifest = _load_json(fixture_dir / "MANIFEST.json")
    blob = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:12]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--root", type=Path, help="Rekordbox USBANLZ root to audit")
    group.add_argument(
        "--fixture-dir",
        type=Path,
        help="Synthetic INTEL fixture directory to audit instead of real ANLZ files",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    args = parser.parse_args(argv)

    result = (
        audit_fixture_dir(args.fixture_dir)
        if args.fixture_dir is not None
        else audit_anlz_root(args.root)
    )

    if args.json:
        json.dump(result, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    else:
        totals = result["totals"]
        coverage = result["coverage"]
        print(
            "ANLZ audit: "
            f"bundles={totals['bundles']} parsed={totals['parsed_bundles']} "
            f"pssi={coverage['pssi']['rate']:.1%} pqtz={coverage['pqtz']['rate']:.1%} "
            f"collisions={result['path_collisions']['collision_count']}"
        )
    return 0 if result.get("valid") is True else 1


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    raise SystemExit(main())
