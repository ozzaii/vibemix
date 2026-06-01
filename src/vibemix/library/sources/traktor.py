# SPDX-License-Identifier: Apache-2.0
"""Traktor ``collection.nml`` source for the shared LibrarySource contract.

This parser is intentionally small and stdlib-only. It reads the exported
Traktor NML collection file and maps each collection ``ENTRY`` onto the same
``TrackEntry`` dataclass used by the rest of the library/search/Viber pipeline.

Lazy-import contract: no audio, CLAP, torch, database, or Traktor runtime
imports at module import time. This source only parses XML that the DJ already
owns on disk.
"""

from __future__ import annotations

import hashlib
import xml.etree.ElementTree as ET
from collections.abc import Iterable
from pathlib import Path
from urllib.parse import unquote

from vibemix.library.rekordbox import CuePoint, TrackEntry
from vibemix.state.harmonics import to_camelot

_MACOS_DEFAULTS = (
    "~/Documents/Native Instruments/Traktor 4.0.0/collection.nml",
    "~/Documents/Native Instruments/Traktor 3.0.0/collection.nml",
    "~/Documents/Native Instruments/Traktor/collection.nml",
)
_WINDOWS_DEFAULTS = (
    r"~\Documents\Native Instruments\Traktor 4.0.0\collection.nml",
    r"~\Documents\Native Instruments\Traktor 3.0.0\collection.nml",
    r"~\Documents\Native Instruments\Traktor\collection.nml",
)
_RATING_BYTE_TO_STARS: dict[int, int] = {0: 0, 51: 1, 102: 2, 153: 3, 204: 4, 255: 5}


class TraktorSource:
    """Traktor ``collection.nml`` source (structural :class:`LibrarySource`)."""

    name = "traktor"

    def __init__(self, nml_path: str | None = None) -> None:
        self._explicit_path = nml_path
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
        """Return True iff a Traktor ``collection.nml`` exists at a candidate path."""
        for candidate in self.default_paths():
            try:
                if candidate.is_file():
                    self.resolved_path = str(candidate)
                    return True
            except OSError:  # pragma: no cover - permission/odd FS
                continue
        return False

    def iter_tracks(self) -> Iterable[TrackEntry]:
        """Yield parsed Traktor collection rows as ``TrackEntry`` objects."""
        if self.resolved_path is None and not self.detect():
            raise FileNotFoundError(
                "TraktorSource: no collection.nml detected - pass an explicit "
                "path or export your Traktor collection to collection.nml"
            )

        assert self.resolved_path is not None
        root = ET.parse(self.resolved_path).getroot()
        yield from (_track_from_entry(entry) for entry in _collection_entries(root))


def _collection_entries(root: ET.Element) -> list[ET.Element]:
    collections = [child for child in root.iter() if _local_name(child.tag) == "COLLECTION"]
    if collections:
        entries = [
            child
            for child in list(collections[0])
            if _local_name(child.tag) == "ENTRY"
        ]
        if entries:
            return entries
    return [child for child in root.iter() if _local_name(child.tag) == "ENTRY"]


def _track_from_entry(entry: ET.Element) -> TrackEntry:
    info = _first_child(entry, "INFO")
    tempo = _first_child(entry, "TEMPO")
    key_node = _first_child(entry, "MUSICAL_KEY")
    filepath = _location_path(_first_child(entry, "LOCATION"))
    key = _first_text(
        _attr(key_node, "VALUE"),
        _attr(key_node, "KEY"),
        _attr(info, "KEY"),
        _attr(entry, "KEY"),
        default="",
    )

    title = _first_text(_attr(info, "TITLE"), _attr(entry, "TITLE"), default=Path(filepath).stem)
    artist = _first_text(_attr(info, "ARTIST"), _attr(entry, "ARTIST"))
    album = _first_text(_attr(info, "ALBUM"), _attr(entry, "ALBUM"))

    return TrackEntry(
        track_id=_track_id(entry, filepath, title, artist),
        title=title,
        artist=artist,
        album=album,
        bpm=_float_attr(tempo, "BPM"),
        key=key,
        duration_s=_float_attr(info, "PLAYTIME_FLOAT", "PLAYTIME"),
        cues=tuple(_cue_from_node(cue) for cue in _children(entry, "CUE_V2")),
        filepath=filepath,
        genre=_first_text(_attr(info, "GENRE"), _attr(entry, "GENRE")),
        label=_first_text(_attr(info, "LABEL"), _attr(entry, "LABEL")),
        rating=_rating(_attr(info, "RANKING"), _attr(entry, "RANKING")),
        play_count=_int_attr(info, "PLAYCOUNT"),
        comments=_first_text(_attr(info, "COMMENT"), _attr(entry, "COMMENT")),
        camelot=to_camelot(key),
    )


def _cue_from_node(node: ET.Element) -> CuePoint:
    start_s = _float_attr(node, "START")
    length_s = _float_attr(node, "LEN")
    raw_type = _first_text(_attr(node, "TYPE")).lower()
    cue_type = _cue_type(raw_type, length_s)
    return CuePoint(
        name=_first_text(_attr(node, "NAME")),
        type=cue_type,
        start_s=start_s,
        end_s=start_s + length_s if cue_type == "loop" and length_s > 0 else None,
        number=_hotcue_number(_attr(node, "HOTCUE")),
    )


def _cue_type(raw_type: str, length_s: float) -> str:
    if length_s > 0 or raw_type in {"5", "loop"}:
        return "loop"
    if raw_type in {"1", "fadein", "fade_in"}:
        return "fadein"
    if raw_type in {"2", "fadeout", "fade_out"}:
        return "fadeout"
    if raw_type in {"3", "load"}:
        return "load"
    return "cue"


def _location_path(location: ET.Element | None) -> str:
    if location is None:
        return ""
    directory = _normalize_traktor_dir(_attr(location, "DIR") or "")
    filename = _decode(_attr(location, "FILE") or "")
    if not directory:
        return filename
    return str(Path(directory) / filename)


def _normalize_traktor_dir(raw: str) -> str:
    text = _decode(raw).replace("\\", "/")
    if text.startswith("file://localhost"):
        text = text.removeprefix("file://localhost")
    elif text.startswith("file://"):
        text = text.removeprefix("file://")

    # Traktor NML often stores macOS path separators as "/:" segments:
    # "/:Users/:kaano/:Music/:" or "/Users/kaano/Music/:Psy/".
    if text.startswith("/:"):
        text = "/" + text[2:]
    text = text.replace("/:", "/")

    # Older exports may use classic-Mac volume paths:
    # "Macintosh HD:Users:kaano:Music:" -> "/Users/kaano/Music".
    if "/" not in text and ":" in text:
        parts = [part for part in text.split(":") if part]
        if parts and (" " in parts[0] or parts[0].lower().endswith("hd")):
            parts = parts[1:]
        text = "/" + "/".join(parts) if parts else ""
    return text.rstrip("/")


def _track_id(entry: ET.Element, filepath: str, title: str, artist: str) -> str:
    audio_id = _first_text(_attr(entry, "AUDIO_ID"), _attr(entry, "TRACK_ID"))
    if audio_id:
        return f"traktor:{audio_id}"
    seed = "\x1f".join((filepath, title, artist))
    digest = hashlib.sha1(seed.encode("utf-8", "surrogatepass")).hexdigest()[:16]
    return f"traktor:{digest}"


def _rating(*values: str | None) -> int:
    raw = _first_text(*values)
    if not raw:
        return 0
    try:
        value = int(float(raw))
    except ValueError:
        return 0
    if value <= 5:
        return max(0, min(5, value))
    return _RATING_BYTE_TO_STARS.get(value, max(0, min(5, round(value / 51))))


def _hotcue_number(value: str | None) -> int:
    raw = _first_text(value)
    if not raw:
        return -1
    try:
        number = int(float(raw))
    except ValueError:
        return -1
    return number if number > 0 else -1


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


def _float_attr(node: ET.Element | None, *names: str) -> float:
    raw = _first_text(*(_attr(node, name) for name in names))
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
        text = _decode(value or "").strip()
        if text:
            return text
    return default


def _decode(value: str) -> str:
    return unquote(value)


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


__all__ = ["TraktorSource"]
