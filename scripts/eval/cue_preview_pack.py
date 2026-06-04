#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Create listenable preview snippets for VM cue points in a Rekordbox XML.

This is a by-ear proof helper for cue landing: after Viber exports a set, slice
each VM-stamped cue from a few seconds before the cue point so a DJ can hear
whether the landing moment is right without scrubbing every deck manually.

The tool reads only the importable Rekordbox XML and the referenced audio files.
It never writes a Rekordbox database and never mutates the source audio.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import urllib.parse
import xml.etree.ElementTree as ET
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

DEFAULT_OUT_DIR = Path.home() / "Downloads" / "vibemix-cue-previews"
DEFAULT_PRE_ROLL_S = 3.0
DEFAULT_DURATION_S = 8.0
FFMPEG_TIMEOUT_S = 8.0


@dataclass(frozen=True, slots=True)
class CuePreviewRow:
    track: str
    artist: str
    cue_name: str
    slot: str
    cue_start_s: float
    preview_start_s: float
    duration_s: float
    source_audio: str
    output: str
    command: tuple[str, ...]


def parse_vm_cues(
    xml_path: Path,
    *,
    pre_roll_s: float = DEFAULT_PRE_ROLL_S,
    duration_s: float = DEFAULT_DURATION_S,
    out_dir: Path = DEFAULT_OUT_DIR,
) -> list[CuePreviewRow]:
    """Return preview rows for VM-stamped POSITION_MARK rows in ``xml_path``."""
    root = ET.parse(xml_path).getroot()
    rows: list[CuePreviewRow] = []
    for track_index, track in enumerate(root.findall(".//TRACK"), start=1):
        source_audio = _track_location_to_path(track.attrib.get("Location", ""))
        title = str(track.attrib.get("Name") or f"track-{track_index:02d}")
        artist = str(track.attrib.get("Artist") or "")
        for mark in track.findall("POSITION_MARK"):
            cue_name = str(mark.attrib.get("Name") or "")
            if not cue_name.startswith("VM "):
                continue
            try:
                cue_start_s = max(0.0, float(mark.attrib.get("Start", "0") or 0.0))
            except (TypeError, ValueError):
                continue
            preview_start_s = max(0.0, cue_start_s - pre_roll_s)
            slot = str(mark.attrib.get("Num") or "")
            output = out_dir / _preview_filename(
                index=len(rows) + 1,
                track=title,
                cue_name=cue_name,
                cue_start_s=cue_start_s,
            )
            command = _ffmpeg_command(
                source_audio,
                output,
                start_s=preview_start_s,
                duration_s=duration_s,
            )
            rows.append(
                CuePreviewRow(
                    track=title,
                    artist=artist,
                    cue_name=cue_name,
                    slot=slot,
                    cue_start_s=round(cue_start_s, 6),
                    preview_start_s=round(preview_start_s, 6),
                    duration_s=round(float(duration_s), 6),
                    source_audio=str(source_audio),
                    output=str(output),
                    command=tuple(command),
                )
            )
    return rows


def create_preview_pack(
    xml_path: Path,
    *,
    out_dir: Path = DEFAULT_OUT_DIR,
    pre_roll_s: float = DEFAULT_PRE_ROLL_S,
    duration_s: float = DEFAULT_DURATION_S,
    runner: Callable[..., subprocess.CompletedProcess[Any]] = subprocess.run,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Slice cue previews and write ``manifest.json`` under ``out_dir``."""
    out_dir = out_dir.expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = parse_vm_cues(
        xml_path.expanduser(),
        pre_roll_s=pre_roll_s,
        duration_s=duration_s,
        out_dir=out_dir,
    )
    errors: list[dict[str, str]] = []
    written = 0
    for row in rows:
        source = Path(row.source_audio)
        if not source.is_file():
            errors.append(
                {
                    "cue_name": row.cue_name,
                    "track": row.track,
                    "reason": f"missing source audio: {source}",
                }
            )
            continue
        if not dry_run:
            try:
                runner(
                    list(row.command),
                    check=True,
                    timeout=FFMPEG_TIMEOUT_S,
                    capture_output=True,
                    text=True,
                )
            except subprocess.CalledProcessError as exc:
                errors.append(
                    {
                        "cue_name": row.cue_name,
                        "track": row.track,
                        "reason": f"ffmpeg rc={exc.returncode}: {(exc.stderr or '')[:200]}",
                    }
                )
                continue
            except subprocess.TimeoutExpired:
                errors.append(
                    {
                        "cue_name": row.cue_name,
                        "track": row.track,
                        "reason": "ffmpeg timeout",
                    }
                )
                continue
        written += 1

    manifest = {
        "schema": "cue_preview_pack_v1",
        "ok": bool(rows) and not errors,
        "xml_path": str(xml_path.expanduser()),
        "out_dir": str(out_dir),
        "pre_roll_s": pre_roll_s,
        "duration_s": duration_s,
        "dry_run": dry_run,
        "cue_count": len(rows),
        "written": written,
        "errors": errors,
        "previews": [asdict(row) for row in rows],
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def _track_location_to_path(location: str) -> Path:
    if location.startswith("file://"):
        parsed = urllib.parse.urlparse(location)
        # Rekordbox XML commonly writes file://localhost//abs/path.
        path = urllib.parse.unquote(parsed.path)
        if parsed.netloc == "localhost" and path.startswith("//"):
            path = path[1:]
        return Path(path)
    return Path(urllib.parse.unquote(location))


def _preview_filename(*, index: int, track: str, cue_name: str, cue_start_s: float) -> str:
    safe_track = _slug(track) or "track"
    safe_cue = _slug(cue_name.removeprefix("VM ").strip()) or "cue"
    return f"{index:02d}-{safe_track}-{safe_cue}-{cue_start_s:07.3f}s.wav"


def _slug(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")[:80]


def _ffmpeg_command(
    source_audio: Path,
    output: Path,
    *,
    start_s: float,
    duration_s: float,
) -> list[str]:
    ffmpeg = shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"
    return [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-ss",
        f"{start_s:.3f}",
        "-i",
        str(source_audio),
        "-t",
        f"{duration_s:.3f}",
        "-ac",
        "2",
        "-ar",
        "44100",
        str(output),
    ]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("xml", type=Path, help="Rekordbox XML exported by vibemix")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--pre-roll-s", type=float, default=DEFAULT_PRE_ROLL_S)
    parser.add_argument("--duration-s", type=float, default=DEFAULT_DURATION_S)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true", help="print manifest JSON")
    args = parser.parse_args(argv)

    manifest = create_preview_pack(
        args.xml,
        out_dir=args.out_dir,
        pre_roll_s=args.pre_roll_s,
        duration_s=args.duration_s,
        dry_run=bool(args.dry_run),
    )
    if args.json:
        print(json.dumps(manifest, indent=2, sort_keys=True))
    elif manifest["ok"]:
        print(f"cue preview pack ok: {manifest['out_dir']}")
    else:
        print(json.dumps(manifest, indent=2, sort_keys=True), file=sys.stderr)
    return 0 if manifest["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
