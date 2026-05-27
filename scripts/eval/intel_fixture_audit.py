# SPDX-License-Identifier: Apache-2.0
"""Audit the public INTEL synthetic fixture corpus."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FIXTURE_DIR = ROOT / "tests" / "intel" / "fixtures"

REQUIRED_FILES = (
    "README.md",
    "MANIFEST.json",
    "dataset_card.json",
    "tracks.json",
    "sections.json",
    "anlz_bundles.json",
    "section_vectors_8d.json",
    "section_vectors_512d.npy",
    "transition_pairs.json",
    "transition_slates.json",
    "smart_cue_proposals.json",
    "cue_baseline_before.xml",
    "cue_baseline_after.xml",
    "context_packets.json",
    "claim_ledgers.json",
    "agent_decisions.jsonl",
    "decision_traces.jsonl",
    "live_awareness_snapshots.jsonl",
    "gold_labels_redacted.jsonl",
)

JSON_FILES = tuple(name for name in REQUIRED_FILES if name.endswith(".json"))
JSONL_FILES = tuple(name for name in REQUIRED_FILES if name.endswith(".jsonl"))
XML_FILES = tuple(name for name in REQUIRED_FILES if name.endswith(".xml"))

LOCAL_PATH_PATTERNS = (
    re.compile(r"/Users/[^\"'\s]+"),
    re.compile(r"/Volumes/[^\"'\s]+"),
    re.compile(r"[A-Za-z]:\\\\[^\"'\s]+"),
    re.compile(r"file://[^\"'\s]+"),
)

TRACK_ID_RE = re.compile(r"^fx-[a-z0-9]+-[0-9]{3}$")
SECTION_ID_RE = re.compile(r"^(fx-[a-z0-9]+-[0-9]{3})#s[0-9]{3}$")


@dataclass(frozen=True, slots=True)
class AuditResult:
    valid: bool
    errors: tuple[str, ...]
    files_checked: int
    manifest_hash: str


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_jsonl(path: Path) -> list[Any]:
    rows = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path.name}:{lineno} is not valid JSONL: {exc}") from exc
    return rows


def _sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _manifest_hash(manifest: Any) -> str:
    blob = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:12]


def _scan_privacy_text(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    errors = []
    for pattern in LOCAL_PATH_PATTERNS:
        if pattern.search(text):
            errors.append(f"{path}: contains local/private path pattern {pattern.pattern}")

    # Fixture URIs are allowed to end with audio-like extensions. Other raw
    # audio paths are not allowed in the INTEL public corpus.
    for match in re.finditer(r"[^\"'\s]+\.(?:wav|mp3|flac|aiff|m4a)", text, flags=re.I):
        value = match.group(0)
        if not value.startswith("fixture://") and "tests/audio/fixtures" not in value:
            errors.append(f"{path}: raw audio path is not fixture-scoped: {value}")
    return errors


def _is_number_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, int | float) for item in value)


def _scan_raw_vectors(obj: Any, *, path: str = "$") -> list[str]:
    errors = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            next_path = f"{path}.{key}"
            if "vector" in key.lower() and _is_number_list(value) and len(value) > 16:
                errors.append(f"{next_path}: raw vector has {len(value)} dimensions")
            errors.extend(_scan_raw_vectors(value, path=next_path))
    elif isinstance(obj, list):
        for idx, item in enumerate(obj):
            errors.extend(_scan_raw_vectors(item, path=f"{path}[{idx}]"))
    return errors


def _validate_tracks(tracks: Any) -> list[str]:
    errors = []
    if not isinstance(tracks, list):
        return ["tracks.json must contain a list"]
    seen = set()
    for track in tracks:
        track_id = track.get("track_id") if isinstance(track, dict) else None
        if not isinstance(track_id, str) or not TRACK_ID_RE.match(track_id):
            errors.append(f"invalid synthetic track_id: {track_id!r}")
            continue
        if track_id in seen:
            errors.append(f"duplicate track_id: {track_id}")
        seen.add(track_id)
        if not str(track.get("title", "")).startswith("Fixture"):
            errors.append(f"{track_id}: title must start with Fixture")
        if not str(track.get("artist", "")).startswith("Fixture"):
            errors.append(f"{track_id}: artist must start with Fixture")
        if not str(track.get("location", "")).startswith("fixture://"):
            errors.append(f"{track_id}: location must use fixture://")
    return errors


def _validate_sections(sections: Any, track_ids: set[str]) -> list[str]:
    errors = []
    if not isinstance(sections, list):
        return ["sections.json must contain a list"]
    seen = set()
    for section in sections:
        section_id = section.get("section_id") if isinstance(section, dict) else None
        if not isinstance(section_id, str) or not SECTION_ID_RE.match(section_id):
            errors.append(f"invalid section_id: {section_id!r}")
            continue
        if section_id in seen:
            errors.append(f"duplicate section_id: {section_id}")
        seen.add(section_id)
        track_id = section.get("track_id")
        if track_id not in track_ids:
            errors.append(f"{section_id}: unknown track_id {track_id!r}")
        if not isinstance(section.get("role"), str):
            errors.append(f"{section_id}: role must be a string")
        confidence = section.get("role_confidence")
        if not isinstance(confidence, int | float) or not 0 <= confidence <= 1:
            errors.append(f"{section_id}: role_confidence must be in [0, 1]")
    return errors


def _validate_vector_files(fixture_dir: Path, sections: list[dict[str, Any]]) -> list[str]:
    errors = []
    section_ids = [section["section_id"] for section in sections]
    vectors_8d = _load_json(fixture_dir / "section_vectors_8d.json")
    expected_refs = {f"vec8:{section_id}" for section_id in section_ids}
    actual_refs = set(vectors_8d)
    if actual_refs != expected_refs:
        errors.append("section_vectors_8d.json keys must match sections.json section IDs")
    for ref, vector in vectors_8d.items():
        if not _is_number_list(vector) or len(vector) != 8:
            errors.append(f"{ref}: expected 8 numeric dimensions")

    vectors_512 = np.load(fixture_dir / "section_vectors_512d.npy")
    if vectors_512.shape != (len(section_ids), 512):
        errors.append(
            f"section_vectors_512d.npy shape {vectors_512.shape} != ({len(section_ids)}, 512)"
        )
    if str(vectors_512.dtype) != "float32":
        errors.append("section_vectors_512d.npy must be float32")
    return errors


def _validate_references(fixture_dir: Path) -> list[str]:
    errors = []
    sections = _load_json(fixture_dir / "sections.json")
    section_ids = {section["section_id"] for section in sections}
    track_ids = {section["track_id"] for section in sections}
    pairs = _load_json(fixture_dir / "transition_pairs.json")
    pair_ids = set()
    for pair in pairs:
        pair_ids.add(pair.get("candidate_id"))
        if pair.get("from_section_id") not in section_ids:
            errors.append(f"{pair.get('candidate_id')}: unknown from_section_id")
        if pair.get("to_section_id") not in section_ids:
            errors.append(f"{pair.get('candidate_id')}: unknown to_section_id")

    packets = _load_json(fixture_dir / "context_packets.json")
    packet_ids = set()
    for packet in packets:
        packet_ids.add(packet.get("packet_id"))
        for candidate_id in packet.get("candidate_ids", []):
            if candidate_id not in pair_ids:
                errors.append(f"{packet.get('packet_id')}: unknown candidate_id {candidate_id}")
        current_track = packet.get("current", {}).get("track_id")
        if current_track and current_track not in track_ids:
            errors.append(f"{packet.get('packet_id')}: unknown current track {current_track}")

    ledgers = _load_json(fixture_dir / "claim_ledgers.json")
    ledger_packet_ids = {ledger.get("packet_id") for ledger in ledgers}
    if not ledger_packet_ids.issubset(packet_ids):
        errors.append("claim_ledgers.json references unknown packet IDs")

    for name in ("agent_decisions.jsonl", "decision_traces.jsonl", "gold_labels_redacted.jsonl"):
        for row in _load_jsonl(fixture_dir / name):
            packet_id = row.get("packet_id")
            if packet_id and packet_id not in packet_ids:
                errors.append(f"{name}: unknown packet_id {packet_id}")
            candidate_id = row.get("candidate_id")
            if candidate_id and candidate_id not in pair_ids:
                errors.append(f"{name}: unknown candidate_id {candidate_id}")
    return errors


def validate_privacy_file(path: Path | str) -> list[str]:
    target = Path(path)
    errors = _scan_privacy_text(target)
    if target.suffix == ".json":
        try:
            errors.extend(_scan_raw_vectors(_load_json(target), path=target.name))
        except json.JSONDecodeError as exc:
            errors.append(f"{target}: invalid JSON: {exc}")
    elif target.suffix == ".jsonl":
        try:
            for row in _load_jsonl(target):
                errors.extend(_scan_raw_vectors(row, path=target.name))
        except ValueError as exc:
            errors.append(str(exc))
    return errors


def validate_fixture_dir(fixture_dir: Path | str = DEFAULT_FIXTURE_DIR) -> AuditResult:
    path = Path(fixture_dir)
    errors: list[str] = []

    if not path.exists():
        return AuditResult(False, (f"fixture dir not found: {path}",), 0, "")

    for name in REQUIRED_FILES:
        if not (path / name).exists():
            errors.append(f"missing required fixture file: {name}")

    if errors:
        return AuditResult(False, tuple(errors), 0, "")

    manifest = _load_json(path / "MANIFEST.json")
    manifest_files = manifest.get("files", {})
    for name, expected_hash in manifest_files.items():
        target = path / name
        if not target.exists():
            errors.append(f"manifest references missing file: {name}")
            continue
        actual_hash = _sha256(target)
        if actual_hash != expected_hash:
            errors.append(f"{name}: manifest hash {expected_hash} != actual {actual_hash}")

    for name in JSON_FILES:
        try:
            _load_json(path / name)
        except json.JSONDecodeError as exc:
            errors.append(f"{name}: invalid JSON: {exc}")

    for name in JSONL_FILES:
        try:
            _load_jsonl(path / name)
        except ValueError as exc:
            errors.append(str(exc))

    for name in XML_FILES:
        try:
            ET.parse(path / name)
        except ET.ParseError as exc:
            errors.append(f"{name}: invalid XML: {exc}")

    tracks = _load_json(path / "tracks.json")
    track_ids = {track["track_id"] for track in tracks if isinstance(track, dict)}
    sections = _load_json(path / "sections.json")
    errors.extend(_validate_tracks(tracks))
    errors.extend(_validate_sections(sections, track_ids))
    errors.extend(_validate_vector_files(path, sections))
    errors.extend(_validate_references(path))

    for target in path.iterdir():
        if target.is_dir():
            continue
        if target.suffix in {".json", ".jsonl", ".xml", ".md"}:
            errors.extend(validate_privacy_file(target))

    return AuditResult(
        valid=not errors,
        errors=tuple(errors),
        files_checked=len(REQUIRED_FILES),
        manifest_hash=_manifest_hash(manifest),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture-dir", type=Path, default=DEFAULT_FIXTURE_DIR)
    parser.add_argument("--json", action="store_true", help="emit machine-readable audit result")
    args = parser.parse_args(argv)

    result = validate_fixture_dir(args.fixture_dir)
    if args.json:
        print(
            json.dumps(
                {
                    "valid": result.valid,
                    "errors": list(result.errors),
                    "files_checked": result.files_checked,
                    "manifest_hash": result.manifest_hash,
                },
                indent=2,
                sort_keys=True,
            )
        )
    elif result.valid:
        print(
            "INTEL fixture audit passed "
            f"({result.files_checked} files, manifest {result.manifest_hash})"
        )
    else:
        for error in result.errors:
            print(f"[intel-fixture-audit] {error}", file=sys.stderr)
    return 0 if result.valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
