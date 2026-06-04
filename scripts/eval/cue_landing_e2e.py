#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""End-to-end proof for Viber cue landing across carriers and the pill.

This is a deterministic current-source gate for the product promise:

    Viber builds a set -> auto-cues land in DJ-software carriers ->
    the running next-suggestion pill can see the same cue slots.

The probe uses a temporary copy of the in-repo MP3 fixture for the Serato/Mixxx
Markers2 carrier, so no user audio file or Rekordbox private database is
mutated. Rekordbox proof is the XML + grid audit; Serato/Mixxx proof is a
Markers2 read-back from the copied file; pill proof is a real
``next_suggestion()`` transition payload after ``export_set(target="all")``.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from vibemix.intel.transition_scorer import SectionRecord  # noqa: E402
from vibemix.library import toolset as tool_mod  # noqa: E402
from vibemix.library.export_serato import read_serato_cues  # noqa: E402
from vibemix.library.next_suggestion import next_suggestion  # noqa: E402
from vibemix.library.rekordbox import (  # noqa: E402
    CuePoint,
    RekordboxLibrary,
    TempoNode,
    TrackEntry,
)
from vibemix.library.toolset import LibraryToolset  # noqa: E402

SCHEMA = "cue_landing_e2e_v1"
DEFAULT_OUT_DIR = ROOT / ".planning" / "eval-runs" / "cue-landing-e2e-current"
FIXTURE_MP3 = ROOT / "tests" / "bench" / "data" / "t1_pyrez_darkside.mp3"


class _FakeBackend:
    def __init__(self, ids: list[str], vectors: np.ndarray) -> None:
        self._ids = ids
        self._vectors = vectors

    def load_all(self) -> tuple[list[str], np.ndarray]:
        return self._ids, self._vectors


class _FakeStore:
    def __init__(self) -> None:
        self._backend = _FakeBackend(
            ["src", "dst"],
            np.eye(2, 8, dtype=np.float32),
        )
        self.section_vectors: dict[str, Any] = {}

    def search_centered(self, _qvec: np.ndarray, k: int = 10) -> list[tuple[str, float]]:
        return [("src", 0.99), ("dst", 0.88)][:k]


def _head_sha() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=ROOT,
            text=True,
        ).strip()
    except Exception:
        return None


def _track(
    track_id: str,
    *,
    title: str,
    filepath: str,
    cues: tuple[CuePoint, ...] = (),
    beatgrid: tuple[TempoNode, ...] = (),
) -> TrackEntry:
    return TrackEntry(
        track_id=track_id,
        title=title,
        artist="Vibemix Proof",
        album="",
        bpm=124.0,
        key="8A" if track_id == "src" else "9A",
        duration_s=300.0,
        cues=cues,
        filepath=filepath,
        beatgrid=beatgrid,
    )


def _section(section_id: str, role: str, start_s: float, end_s: float) -> SectionRecord:
    track_id = section_id.split("#", 1)[0]
    return SectionRecord(
        section_id=section_id,
        track_id=track_id,
        role=role,
        source="anlz",
        source_detail="pssi",
        confidence=0.92,
        start_s=start_s,
        end_s=end_s,
        start_beat=round(start_s * 124.0 / 60.0),
        end_beat=round(end_s * 124.0 / 60.0),
        bar_count=(end_s - start_s) * 124.0 / 60.0 / 4.0,
        bpm=124.0,
        camelot="9A" if track_id == "dst" else "8A",
        cue_source="anlz",
        cue_confidence=0.92,
    )


def _patched_sections_for_entry(entry: TrackEntry) -> tuple[SectionRecord, ...]:
    if entry.track_id == "dst":
        return (
            _section("dst#intro", "intro", 15.51, 40.0),
            _section("dst#drop", "drop", 61.98, 128.0),
        )
    return (_section("src#outro", "outro", 224.0, 300.0),)


def _grid_audit(xml_path: Path) -> dict[str, Any]:
    root = ET.parse(xml_path).getroot()
    rows: list[dict[str, Any]] = []
    for track in root.findall(".//TRACK"):
        tempo = track.find("TEMPO")
        bpm = float((tempo.attrib.get("Bpm") if tempo is not None else 0.0) or 0.0)
        inizio = float((tempo.attrib.get("Inizio") if tempo is not None else 0.0) or 0.0)
        beat_s = 60.0 / bpm if bpm > 0 else None
        for mark in track.findall("POSITION_MARK"):
            name = mark.attrib.get("Name", "")
            if not name.startswith("VM "):
                continue
            start_s = float(mark.attrib.get("Start", "0") or 0.0)
            if beat_s is None:
                err_ms = None
                beat_index = None
            else:
                beat_index = (start_s - inizio) / beat_s
                nearest = round(beat_index)
                err_ms = abs(start_s - (inizio + nearest * beat_s)) * 1000.0
            rows.append(
                {
                    "track": track.attrib.get("Name", ""),
                    "name": name,
                    "slot": mark.attrib.get("Num"),
                    "start_s": start_s,
                    "bpm": bpm,
                    "beat_index": None if beat_index is None else round(float(beat_index), 6),
                    "grid_error_ms": None if err_ms is None else round(float(err_ms), 6),
                }
            )
    errors = [row["grid_error_ms"] for row in rows if row["grid_error_ms"] is not None]
    return {
        "vm_cues": len(rows),
        "max_grid_error_ms": round(max(errors), 6) if errors else None,
        "over_1ms": sum(1 for err in errors if err > 1.0),
        "rows": rows,
    }


def run_probe(out_dir: Path = DEFAULT_OUT_DIR) -> dict[str, Any]:
    out_dir = out_dir.expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)
    if not FIXTURE_MP3.exists():
        return {
            "schema": SCHEMA,
            "status": "missing_fixture",
            "fixture": str(FIXTURE_MP3.relative_to(ROOT)),
        }

    tag_copy = out_dir / "cue-landing-carrier-track.mp3"
    shutil.copy2(FIXTURE_MP3, tag_copy)

    library = RekordboxLibrary()
    library.tracks = {
        "src": _track(
            "src",
            title="Source Track",
            filepath=str(out_dir / "source-placeholder.mp3"),
            cues=(CuePoint("OUT", "cue", 224.0, None, 5),),
        ),
        "dst": _track(
            "dst",
            title="Destination Track",
            filepath=str(tag_copy),
            beatgrid=(TempoNode(inizio_s=0.125, bpm=124.0, metro="4/4", battito=1),),
        ),
    }
    store = _FakeStore()
    toolset = LibraryToolset(embedder=None, store=store, library=library)
    toolset.seen.add("dst")

    original_sections_for_entry = tool_mod.sections_for_entry
    try:
        tool_mod.sections_for_entry = _patched_sections_for_entry
        export_result = toolset.export_set(
            {
                "name": "cue landing e2e",
                "track_ids": ["dst"],
                "out_path": str(out_dir / "cue-landing-e2e.xml"),
                "target": "all",
                "tag_write_granted": True,
            }
        )
    finally:
        tool_mod.sections_for_entry = original_sections_for_entry

    outputs = export_result.get("outputs", {}) if isinstance(export_result, dict) else {}
    xml_path = Path(outputs.get("rekordbox") or out_dir / "cue-landing-e2e.xml")
    m3u8_path = Path(outputs.get("m3u8") or out_dir / "cue-landing-e2e.m3u8")
    markers2 = read_serato_cues(tag_copy)

    suggestion = next_suggestion(
        store,
        library,
        seed_vector=np.ones(8, dtype=np.float32),
        seed_track_id="src",
        played_ids=set(),
        source_deck="A",
        target_deck="B",
        source_position_s=284.0,
        live_playhead_confidence=0.90,
    )
    transition = suggestion.transition if suggestion is not None else None

    proof = {
        "schema": SCHEMA,
        "status": "ok" if export_result.get("exported") and transition else "failed",
        "head": _head_sha(),
        "out_dir": str(out_dir),
        "export_result": export_result,
        "outputs_exist": {
            "rekordbox": xml_path.exists(),
            "m3u8": m3u8_path.exists(),
            "markers2_tag_copy": tag_copy.exists(),
        },
        "rekordbox_snap": _grid_audit(xml_path) if xml_path.exists() else None,
        "m3u8": {
            "path": str(m3u8_path),
            "exists": m3u8_path.exists(),
            "contains_track_copy": str(tag_copy) in m3u8_path.read_text(encoding="utf-8")
            if m3u8_path.exists()
            else False,
        },
        "markers2_readback": [asdict(cue) for cue in markers2],
        "pill": {
            "track_id": None if suggestion is None else suggestion.track_id,
            "why": None if suggestion is None else suggestion.why,
            "transition_present": transition is not None,
            "transition": transition,
        },
        "source_file_policy": {
            "mutated_user_audio": False,
            "tagged_copy": str(tag_copy),
            "fixture_source": str(FIXTURE_MP3.relative_to(ROOT)),
        },
        "rekordbox_existing_grid_fixture": {
            "track_id": "dst",
            "inizio_s": 0.125,
            "bpm": 124.0,
            "purpose": "prove VM cues snap to a persisted Rekordbox grid, not just a BPM-only export grid",
        },
    }
    (out_dir / "proof.json").write_text(
        json.dumps(proof, indent=2, sort_keys=True), encoding="utf-8"
    )
    return proof


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--json", action="store_true", help="print proof JSON")
    args = parser.parse_args(argv)

    proof = run_probe(args.out_dir)
    if args.json:
        print(json.dumps(proof, indent=2, sort_keys=True))
    elif proof.get("status") == "ok":
        print(f"cue landing e2e ok: {args.out_dir / 'proof.json'}")
    else:
        print(json.dumps(proof, indent=2, sort_keys=True), file=sys.stderr)
    return 0 if proof.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
