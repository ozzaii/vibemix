# SPDX-License-Identifier: Apache-2.0
"""VirtualDJ ``database.xml`` source for the shared LibrarySource contract.

VirtualDJ stores library rows in a UTF-8 XML database. This source reads that
database read-only and maps each ``Song`` row onto the existing ``TrackEntry``
shape used by Rekordbox/Traktor ingest. It intentionally avoids any VirtualDJ
runtime, audio decode, CLAP, or database dependency.

Important format detail: VirtualDJ's scanned BPM field is stored as seconds per
beat, not displayed BPM. ``Bpm="0.5"`` means 120 BPM.
"""

from __future__ import annotations

import hashlib
import xml.etree.ElementTree as ET
from collections.abc import Iterable
from pathlib import Path

from vibemix.library.rekordbox import CuePoint, TempoNode, TrackEntry
from vibemix.state.harmonics import to_camelot

_MACOS_DEFAULTS = (
    "~/Documents/VirtualDJ/database.xml",
    "~/Library/Application Support/VirtualDJ/database.xml",
)
_WINDOWS_DEFAULTS = (
    r"~\Documents\VirtualDJ\database.xml",
    r"~\AppData\Local\VirtualDJ\database.xml",
)


class VirtualDJSource:
    """VirtualDJ ``database.xml`` source (structural :class:`LibrarySource`)."""

    name = "virtualdj"

    def __init__(self, database_path: str | None = None) -> None:
        self._explicit_path = database_path
        self.resolved_path: str | None = None

    def default_paths(self) -> list[Path]:
        candidates: list[str] = []
        if self._explicit_path:
            candidates.append(self._explicit_path)
        candidates.extend(_MACOS_DEFAULTS)
        candidates.extend(_WINDOWS_DEFAULTS)

        out: list[Path] = []
        for candidate in candidates:
            try:
                out.append(Path(candidate).expanduser())
            except (RuntimeError, OSError):  # pragma: no cover - wrong-OS path
                out.append(Path(candidate))
        return out

    def detect(self) -> bool:
        """Return True iff a VirtualDJ ``database.xml`` exists at a candidate path."""
        for candidate in self.default_paths():
            try:
                if candidate.is_file():
                    self.resolved_path = str(candidate)
                    return True
            except OSError:  # pragma: no cover - permission/odd FS
                continue
        return False

    def iter_tracks(self) -> Iterable[TrackEntry]:
        """Yield parsed VirtualDJ database rows as ``TrackEntry`` objects."""
        if self.resolved_path is None and not self.detect():
            raise FileNotFoundError(
                "VirtualDJSource: no database.xml detected - pass an explicit "
                "path or point setup at your VirtualDJ database.xml"
            )

        assert self.resolved_path is not None
        root = ET.parse(self.resolved_path).getroot()
        yield from (_track_from_song(song) for song in _song_nodes(root))


def _song_nodes(root: ET.Element) -> list[ET.Element]:
    return [node for node in root.iter() if _local_name(node.tag) == "Song"]


def _track_from_song(song: ET.Element) -> TrackEntry:
    tags = _first_child(song, "Tags")
    infos = _first_child(song, "Infos")
    scan = _first_child(song, "Scan")
    filepath = _first_text(_attr(song, "FilePath"))
    title = _first_text(_attr(tags, "Title"), default=_path_stem(filepath))
    artist = _first_text(_attr(tags, "Author"), _attr(tags, "Artist"))
    key = _first_text(_attr(tags, "Key"), _attr(scan, "Key"))
    bpm = _virtualdj_bpm(_attr(scan, "Bpm"), _attr(tags, "Bpm"))
    cues = tuple(_cue_from_poi(poi) for poi in _cue_pois(song))
    beatgrid = tuple(_beatgrid_from_poi(poi, bpm) for poi in _beatgrid_pois(song))

    return TrackEntry(
        track_id=_track_id(song, filepath, title, artist),
        title=title,
        artist=artist,
        album=_first_text(_attr(tags, "Album")),
        bpm=bpm,
        key=key,
        duration_s=_float_attr(infos, "SongLength"),
        cues=cues,
        filepath=filepath,
        genre=_first_text(_attr(tags, "Genre")),
        label=_first_text(_attr(tags, "Label")),
        rating=_rating(_attr(tags, "Stars")),
        play_count=_int_attr(infos, "PlayCount"),
        comments=_comment(song, tags),
        camelot=to_camelot(key),
        beatgrid=beatgrid,
    )


def _cue_pois(song: ET.Element) -> list[ET.Element]:
    return [poi for poi in _children(song, "Poi") if _is_cue_poi(poi)]


def _beatgrid_pois(song: ET.Element) -> list[ET.Element]:
    return [poi for poi in _children(song, "Poi") if _poi_type(poi) == "beatgrid"]


def _is_cue_poi(poi: ET.Element) -> bool:
    typ = _poi_type(poi)
    if typ == "beatgrid":
        return False
    return typ in {"cue", "hotcue", "hot_cue", "saved_loop", "loop"} or (
        not typ and _float_attr(poi, "Pos") > 0
    )


def _cue_from_poi(poi: ET.Element) -> CuePoint:
    start_s = _float_attr(poi, "Pos")
    length_s = _float_attr(poi, "Size")
    typ = _poi_type(poi)
    cue_type = "loop" if length_s > 0 or "loop" in typ else "cue"
    return CuePoint(
        name=_first_text(_attr(poi, "Name")),
        type=cue_type,
        start_s=start_s,
        end_s=start_s + length_s if cue_type == "loop" and length_s > 0 else None,
        number=_poi_number(poi),
    )


def _beatgrid_from_poi(poi: ET.Element, fallback_bpm: float) -> TempoNode:
    return TempoNode(
        inizio_s=_float_attr(poi, "Pos"),
        bpm=_virtualdj_bpm(_attr(poi, "Bpm")) or fallback_bpm,
        metro="",
        battito=1,
    )


def _virtualdj_bpm(*values: str | None) -> float:
    """Convert VirtualDJ's seconds-per-beat value into displayed BPM."""
    raw = _first_text(*values)
    if not raw:
        return 0.0
    try:
        value = float(raw)
    except ValueError:
        return 0.0
    if value <= 0:
        return 0.0
    if value < 10:
        return 60.0 / value
    return value


def _track_id(song: ET.Element, filepath: str, title: str, artist: str) -> str:
    seed = "\x1f".join(
        (
            filepath,
            _first_text(_attr(song, "FileSize")),
            title,
            artist,
        )
    )
    digest = hashlib.sha1(seed.encode("utf-8", "surrogatepass")).hexdigest()[:16]
    return f"virtualdj:{digest}"


def _path_stem(filepath: str) -> str:
    return Path(filepath.replace("\\", "/")).stem


def _poi_type(poi: ET.Element) -> str:
    return _first_text(_attr(poi, "Type")).lower().replace(" ", "_")


def _poi_number(poi: ET.Element) -> int:
    raw = _first_text(_attr(poi, "Num"), _attr(poi, "Slot"), _attr(poi, "Point"))
    if not raw:
        return -1
    try:
        number = int(float(raw))
    except ValueError:
        return -1
    return number if number > 0 else -1


def _rating(value: str | None) -> int:
    raw = _first_text(value)
    if not raw:
        return 0
    try:
        stars = int(float(raw))
    except ValueError:
        return 0
    return max(0, min(5, stars))


def _comment(song: ET.Element, tags: ET.Element | None) -> str:
    tag_comment = _first_text(_attr(tags, "Comment"), _attr(tags, "Comments"))
    if tag_comment:
        return tag_comment
    node = _first_child(song, "Comment")
    return _first_text(_attr(node, "Text"), _attr(node, "Value"), node.text if node is not None else None)


def _children(parent: ET.Element, tag: str) -> list[ET.Element]:
    return [child for child in list(parent) if _local_name(child.tag) == tag]


def _first_child(parent: ET.Element, tag: str) -> ET.Element | None:
    for child in list(parent):
        if _local_name(child.tag) == tag:
            return child
    return None


def _attr(node: ET.Element | None, name: str) -> str | None:
    if node is None:
        return None
    return node.attrib.get(name)


def _float_attr(node: ET.Element | None, name: str) -> float:
    raw = _first_text(_attr(node, name))
    if not raw:
        return 0.0
    try:
        return float(raw)
    except ValueError:
        return 0.0


def _int_attr(node: ET.Element | None, name: str) -> int:
    raw = _first_text(_attr(node, name))
    if not raw:
        return 0
    try:
        return int(float(raw))
    except ValueError:
        return 0


def _first_text(*values: str | None, default: str = "") -> str:
    for value in values:
        text = (value or "").strip()
        if text:
            return text
    return default


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


__all__ = ["VirtualDJSource"]
