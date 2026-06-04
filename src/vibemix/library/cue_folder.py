# SPDX-License-Identifier: Apache-2.0
"""Folder -> auto-cue -> Rekordbox bridge: the `library cue <folder>` engine.

Task 1 of the cue+export plan - the free, point-and-go alternative to
Mixed-In-Key/Lexicon for hot cues. Walk a folder of tracks, run the shipped
auto-cue engine (`cue_engine.detect_cues_auto`) on each, and emit the exact
track-dict shape `export_rekordbox.export_set` already consumes, so the caller
gets one importable ``collection.xml`` with structural hot cues (INTRO / BUILD /
BREAKDOWN / DROP / OUTRO) on the deck pads.

Design:
  * The auto-cue engine is INJECTED (`detect=`) - defaults lazily to
    ``detect_cues_auto`` so this module's import surface stays free of
    onnxruntime, and tests run with no audio + no model.
  * Per-file errors are caught, recorded in ``skipped`` (never paths beyond the
    file given), and never fatal - mirrors ``embed-folder``'s resilience so one
    unreadable track doesn't abort a 2000-track library run.
  * Anti-slop (Invariant #3): a file the engine finds NO cues in produces NO
    track - we never fabricate a placeholder cue.

Rekordbox exposes 8 hot-cue pads (A-H); a track with more anchors keeps the 8
earliest. The bridge maps each ``CueAnchor`` to the lowercase cue dict
``_add_cues`` reads (``{type, start_s, num, name}``), reusing
``cue_export._LABEL_TO_MARK_NAME`` so the pad labels are single-sourced.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from vibemix.library.cue_export import _LABEL_TO_MARK_NAME
from vibemix.library.cue_types import CueAnchor
from vibemix.library.folder_ingest import SUPPORTED_SUFFIXES

logger = logging.getLogger("vibemix.library")

# Rekordbox hot-cue pads A-H. A track with more structural anchors keeps the
# 8 earliest (the ones a DJ reaches for first); the rest are dropped in v1
# (memory cues / num=-1 are a future enhancement).
HOT_CUE_SLOTS = 8

# Detection budget per track. 8 keeps every detected anchor mappable to a hot
# pad; raise it only alongside memory-cue support.
DEFAULT_MAX_CUES = 8

DetectFn = Callable[..., Sequence[CueAnchor]]


@dataclass(frozen=True, slots=True)
class CueFolderResult:
    """Outcome of a folder cue run. ``tracks`` are export_set-ready dicts;
    ``skipped`` records per-file decode errors / anchorless files (counts +
    the given path only, never deeper)."""

    tracks: list[dict[str, Any]] = field(default_factory=list)
    skipped: list[dict[str, str]] = field(default_factory=list)
    scanned: int = 0


@dataclass(frozen=True, slots=True)
class CueExportReport:
    """Honest counts + output paths from a folder cue-and-export run."""

    tracks_cued: int
    cues_total: int
    skipped: int
    outputs: dict[str, str] = field(default_factory=dict)


def anchors_to_marks(
    anchors: Sequence[CueAnchor], *, max_marks: int = HOT_CUE_SLOTS
) -> list[dict[str, Any]]:
    """Map structural ``CueAnchor``s -> the cue dicts ``export_set._add_cues``
    consumes: a POINT hot cue per anchor, ``Num`` 0-based ascending by
    ``start_s``, ``Name`` from the shared label map. Caps at ``max_marks``
    (the 8 earliest)."""
    ordered = sorted(anchors, key=lambda a: a.start_s)[:max_marks]
    marks: list[dict[str, Any]] = []
    for num, anc in enumerate(ordered):
        name = _LABEL_TO_MARK_NAME.get(anc.label, str(anc.label).upper())
        marks.append(
            {
                "type": "cue",
                "start_s": round(float(anc.start_s), 3),
                "num": num,
                "name": name,
                "source": anc.source,
            }
        )
    return marks


def cue_folder(
    folder: Path | str,
    *,
    max_cues: int = DEFAULT_MAX_CUES,
    detect: DetectFn | None = None,
    on_progress: Callable[[int, int, str], None] | None = None,
) -> CueFolderResult:
    """Walk ``folder`` for audio files, auto-cue each, and return export-ready
    track dicts.

    ``detect`` defaults to ``cue_engine.detect_cues_auto`` (lazy-imported). Each
    audio file becomes a track dict ``{filepath, title, cues}`` (no fabricated
    beatgrid - the cue engine carries no tempo). A file that errors or yields no
    cues is recorded in ``skipped`` and never aborts the run.
    """
    if detect is None:
        from vibemix.library.cue_engine import detect_cues_auto

        detect = detect_cues_auto

    root = Path(folder)
    files = sorted(
        p for p in root.rglob("*")
        if p.is_file() and p.suffix.lower() in SUPPORTED_SUFFIXES
    )
    result = CueFolderResult(scanned=len(files))
    total = len(files)

    for idx, path in enumerate(files, start=1):
        if on_progress is not None:
            on_progress(idx, total, path.name)
        try:
            anchors = detect(str(path), max_cues=max_cues)
        except Exception as exc:  # one unreadable track never aborts the run
            logger.warning("cue_folder: skipped %s (%s)", path.name, exc)
            result.skipped.append({"filepath": str(path), "reason": str(exc)})
            continue
        if not anchors:
            result.skipped.append(
                {"filepath": str(path), "reason": "no cues detected"}
            )
            continue
        result.tracks.append(
            {
                "filepath": str(path),
                "title": path.stem,
                "cues": anchors_to_marks(anchors),
            }
        )
    return result


def write_m3u8(tracks: Sequence[Mapping[str, Any]], out_path: Path | str) -> Path:
    """Write a neutral extended-M3U8 playlist (order + titles, no cues).

    Mixxx / Serato / most players import an ``.m3u8`` as an ADDITIVE playlist
    (Mixxx makes it a new crate) - order only; the cues ride in the Rekordbox
    XML or the Serato file tags, never here. Duration is unknown from the cue
    path, so every entry is ``#EXTINF:-1``.
    """
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = ["#EXTM3U"]
    for track in tracks:
        title = str(track.get("title") or "")
        lines.append(f"#EXTINF:-1,{title}")
        lines.append(str(track.get("filepath") or ""))
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


# Cue carriers per --export choice. Rekordbox XML reaches Rekordbox (and, via a
# USB export, Pioneer hardware); M3U8 is the neutral order-only bridge every
# player (incl. Mixxx/Serato) imports additively. Serato file-tags are the
# opt-in direct file carrier for engines that import Markers2 cues.
_EXPORT_FORMATS: dict[str, tuple[str, ...]] = {
    "rekordbox": ("rekordbox",),
    "m3u8": ("m3u8",),
    "both": ("rekordbox", "m3u8"),
}


def export_cued_folder(
    folder: Path | str,
    out: Path | str,
    *,
    export: str = "rekordbox",
    name: str = "vibemix cues",
    max_cues: int = DEFAULT_MAX_CUES,
    detect: DetectFn | None = None,
    on_progress: Callable[[int, int, str], None] | None = None,
) -> CueExportReport:
    """Auto-cue ``folder`` and write it to the requested ``export`` format(s).

    ``export`` in {``"rekordbox"`` (collection.xml, default), ``"m3u8"`` (neutral
    playlist), ``"both"``}. Orchestrates ``cue_folder`` -> the format writers and
    returns honest counts (``tracks_cued`` / ``cues_total`` / ``skipped``) plus
    an ``outputs`` map of format->path. The Rekordbox XML is imported via
    "File -> Import -> rekordbox xml" (additive - the collection is never mutated
    in place). A path with the matching suffix is used verbatim; otherwise the
    suffix is derived from ``out`` (so ``--export both --out set.xml`` also
    writes ``set.m3u8``).
    """
    formats = _EXPORT_FORMATS.get(export)
    if formats is None:
        raise ValueError(
            f"export must be one of {sorted(_EXPORT_FORMATS)}, got {export!r}"
        )

    result = cue_folder(
        folder, max_cues=max_cues, detect=detect, on_progress=on_progress
    )
    cues_total = sum(len(t["cues"]) for t in result.tracks)
    out_path = Path(out)
    outputs: dict[str, str] = {}

    if "rekordbox" in formats:
        from vibemix.library.export_rekordbox import export_set

        xml_path = (
            out_path if out_path.suffix.lower() == ".xml"
            else out_path.with_suffix(".xml")
        )
        export_set(result.tracks, name, xml_path)
        outputs["rekordbox"] = str(xml_path)

    if "m3u8" in formats:
        m3u8_path = (
            out_path if out_path.suffix.lower() == ".m3u8"
            else out_path.with_suffix(".m3u8")
        )
        write_m3u8(result.tracks, m3u8_path)
        outputs["m3u8"] = str(m3u8_path)

    return CueExportReport(
        tracks_cued=len(result.tracks),
        cues_total=cues_total,
        skipped=len(result.skipped),
        outputs=outputs,
    )


def tag_folder_serato(
    folder: Path | str,
    *,
    allow_write: bool = False,
    merge: bool = True,
    max_cues: int = DEFAULT_MAX_CUES,
    detect: DetectFn | None = None,
    on_progress: Callable[[int, int, str], None] | None = None,
) -> dict[str, int]:
    """Auto-cue ``folder`` and write Serato Markers2 cue tags INTO each file.

    This is the direct file carrier: cues are written into the audio file's
    Serato Markers2 tag for software that imports those cues, with no DB write.
    Because it mutates the user's files it is opt-in (``allow_write`` <- the CLI
    ``--write-tags``) and ``merge``-by-default (never clobbers a hand-set cue).
    Returns counts: ``{tagged, cues_total, skipped, scanned}``.
    """
    from vibemix.library.export_serato import (
        marks_to_serato_cues,
        write_serato_cues,
    )

    result = cue_folder(
        folder, max_cues=max_cues, detect=detect, on_progress=on_progress
    )
    tagged = 0
    cues_total = 0
    skipped = list(result.skipped)
    for track in result.tracks:
        cues = marks_to_serato_cues(track["cues"])
        res = write_serato_cues(
            track["filepath"], cues, merge=merge, allow_write=allow_write
        )
        if res.get("written"):
            tagged += 1
            cues_total += int(res.get("cue_count", 0))
        else:
            skipped.append(
                {"filepath": track["filepath"], "reason": res.get("reason", "not written")}
            )
    return {
        "tagged": tagged,
        "cues_total": cues_total,
        "skipped": len(skipped),
        "scanned": result.scanned,
    }


__all__ = [
    "HOT_CUE_SLOTS",
    "CueExportReport",
    "CueFolderResult",
    "anchors_to_marks",
    "cue_folder",
    "export_cued_folder",
    "tag_folder_serato",
    "write_m3u8",
]
