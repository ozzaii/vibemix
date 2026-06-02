# SPDX-License-Identifier: Apache-2.0
"""Serato ``_Serato_`` library source for the shared LibrarySource contract.

Serato stores its catalog and crates as tagged binary chunks. This parser keeps
the same posture as the Traktor/VirtualDJ/Engine sources: read-only,
stdlib-only, tolerant of malformed rows, and mapped onto ``TrackEntry``. Hot
cues are read from the owned Serato Markers2 tag decoder; this module does not
reimplement the cue payload format.
"""

from __future__ import annotations

import hashlib
import logging
import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path

from vibemix.library.export_serato import read_serato_cues
from vibemix.library.rekordbox import CuePoint, TrackEntry
from vibemix.state.harmonics import to_camelot

logger = logging.getLogger("vibemix.library")

_DATABASE_NAME = "database V2"
_SUBCRATES_DIR = "Subcrates"
_MACOS_DEFAULTS = (
    "~/Music/_Serato_",
    "~/Documents/_Serato_",
)
_WINDOWS_DEFAULTS = (
    r"~\Music\_Serato_",
    r"~\Documents\_Serato_",
)
_TAG_RE = re.compile(rb"^[A-Za-z0-9_ ]{4}$")

_PATH_TAGS = ("pfil", "ptrk", "path")
_TITLE_TAGS = ("tsng", "titl", "name")
_ARTIST_TAGS = ("tart", "arti")
_ALBUM_TAGS = ("talb", "albm")
_BPM_TAGS = ("tbpm", "bpm ")
_KEY_TAGS = ("tkey", "key ")
_DURATION_TAGS = ("tlen", "ttim", "tdur", "len ")
_GENRE_TAGS = ("tgen", "genr")
_LABEL_TAGS = ("tlbl", "lbl ")
_RATING_TAGS = ("trat", "rate")
_PLAY_COUNT_TAGS = ("tply", "pcnt")
_COMMENT_TAGS = ("tcmt", "comm")


class SeratoSource:
    """Serato ``database V2`` source (structural :class:`LibrarySource`)."""

    name = "serato"

    def __init__(self, library_path: str | None = None) -> None:
        self._explicit_path = library_path
        self.resolved_path: str | None = None

    def default_paths(self) -> list[Path]:
        candidates: list[str | Path] = []
        if self._explicit_path:
            candidates.append(self._explicit_path)
        candidates.extend(_MACOS_DEFAULTS)
        candidates.extend(_WINDOWS_DEFAULTS)
        candidates.extend(_volume_serato_roots())

        out: list[Path] = []
        seen: set[str] = set()
        for candidate in candidates:
            try:
                path = Path(candidate).expanduser()
            except (RuntimeError, OSError):  # pragma: no cover - wrong-OS path
                path = Path(candidate)
            key = str(path)
            if key in seen:
                continue
            seen.add(key)
            out.append(path)
        return out

    def detect(self) -> bool:
        """Return True iff a Serato ``database V2`` exists at a candidate path."""
        for candidate in self.default_paths():
            try:
                database = _database_path(candidate)
                if database.is_file():
                    self.resolved_path = str(database)
                    return True
            except OSError:  # pragma: no cover - permission/odd FS
                continue
        return False

    def iter_tracks(self) -> Iterable[TrackEntry]:
        """Yield parsed Serato database/crate rows as ``TrackEntry`` objects."""
        if self.resolved_path is None and not self.detect():
            raise FileNotFoundError(
                "SeratoSource: no _Serato_/database V2 detected - pass an "
                "explicit _Serato_ folder or database V2 path"
            )

        assert self.resolved_path is not None
        database = Path(self.resolved_path)
        root = database.parent
        metadata_rows = _database_rows(database)
        by_path = {row.filepath: row for row in metadata_rows if row.filepath}
        yielded: set[str] = set()

        crate_paths = _crate_paths(root)
        selected_paths = crate_paths or [row.filepath for row in metadata_rows]
        for filepath in selected_paths:
            row = by_path.get(filepath) or _SeratoRow(filepath=filepath)
            try:
                track = _track_from_row(row)
            except Exception as exc:  # pragma: no cover - defensive malformed row
                logger.warning("SeratoSource: skipped malformed track %r: %s", filepath, exc)
                continue
            if track.filepath in yielded:
                continue
            yielded.add(track.filepath)
            yield track

        for row in metadata_rows:
            if row.filepath in yielded:
                continue
            try:
                yield _track_from_row(row)
            except Exception as exc:  # pragma: no cover - defensive malformed row
                logger.warning("SeratoSource: skipped malformed database row: %s", exc)


@dataclass(frozen=True, slots=True)
class _SeratoRow:
    filepath: str
    title: str = ""
    artist: str = ""
    album: str = ""
    bpm: float = 0.0
    key: str = ""
    duration_s: float = 0.0
    genre: str = ""
    label: str = ""
    rating: int = 0
    play_count: int = 0
    comments: str = ""


def _volume_serato_roots() -> list[Path]:
    roots: list[Path] = []
    volumes = Path("/Volumes")
    try:
        for volume in volumes.iterdir():
            roots.append(volume / "_Serato_")
    except OSError:
        pass
    return roots


def _database_path(candidate: Path) -> Path:
    if candidate.name == _DATABASE_NAME:
        return candidate
    return candidate / _DATABASE_NAME


def _database_rows(path: Path) -> list[_SeratoRow]:
    try:
        data = path.read_bytes()
    except OSError as exc:
        logger.warning("SeratoSource: could not read %s: %s", path, exc)
        return []

    rows: list[_SeratoRow] = []
    for tag, body in _tagged_chunks(data):
        if tag != "otrk":
            continue
        fields = _fields_from_track_body(body)
        filepath = _first_field(fields, *_PATH_TAGS)
        if not filepath:
            continue
        rows.append(
            _SeratoRow(
                filepath=filepath,
                title=_first_field(fields, *_TITLE_TAGS, default=_path_stem(filepath)),
                artist=_first_field(fields, *_ARTIST_TAGS),
                album=_first_field(fields, *_ALBUM_TAGS),
                bpm=_float_field(fields, *_BPM_TAGS),
                key=_first_field(fields, *_KEY_TAGS),
                duration_s=_duration_field(fields, *_DURATION_TAGS),
                genre=_first_field(fields, *_GENRE_TAGS),
                label=_first_field(fields, *_LABEL_TAGS),
                rating=_rating_field(fields, *_RATING_TAGS),
                play_count=_int_field(fields, *_PLAY_COUNT_TAGS),
                comments=_first_field(fields, *_COMMENT_TAGS),
            )
        )
    return rows


def _crate_paths(root: Path) -> list[str]:
    subcrates = root / _SUBCRATES_DIR
    try:
        crate_files = sorted(subcrates.glob("*.crate"), key=lambda item: item.name.lower())
    except OSError:
        return []

    paths: list[str] = []
    seen: set[str] = set()
    for crate in crate_files:
        try:
            data = crate.read_bytes()
        except OSError as exc:
            logger.warning("SeratoSource: could not read crate %s: %s", crate, exc)
            continue
        for tag, body in _tagged_chunks(data):
            if tag != "otrk":
                continue
            fields = _fields_from_track_body(body)
            filepath = _first_field(fields, "ptrk", *_PATH_TAGS)
            if not filepath:
                filepath = _text_from_body(body)
            if not filepath or filepath in seen:
                continue
            seen.add(filepath)
            paths.append(filepath)
    return paths


def _track_from_row(row: _SeratoRow) -> TrackEntry:
    filepath = row.filepath
    title = row.title or _path_stem(filepath)
    key = row.key
    return TrackEntry(
        track_id=_track_id(filepath, title, row.artist),
        title=title,
        artist=row.artist,
        album=row.album,
        bpm=row.bpm,
        key=key,
        duration_s=row.duration_s,
        cues=_cue_points_for_file(filepath),
        filepath=filepath,
        genre=row.genre,
        label=row.label,
        rating=row.rating,
        play_count=row.play_count,
        comments=row.comments,
        camelot=to_camelot(key),
    )


def _cue_points_for_file(filepath: str) -> tuple[CuePoint, ...]:
    try:
        cues = read_serato_cues(filepath)
    except ModuleNotFoundError as exc:
        if exc.name and (exc.name == "mutagen" or exc.name.startswith("mutagen.")):
            logger.debug("SeratoSource: mutagen unavailable, skipping Markers2 cues")
            return ()
        raise
    except Exception as exc:
        logger.warning("SeratoSource: could not read Markers2 cues from %s: %s", filepath, exc)
        return ()
    return tuple(
        CuePoint(
            name=cue.name,
            type="cue",
            start_s=cue.position_ms / 1000.0,
            end_s=None,
            number=int(cue.index) + 1,
        )
        for cue in cues
    )


def _tagged_chunks(data: bytes) -> Iterator[tuple[str, bytes]]:
    pos = 0
    n = len(data)
    while pos + 8 <= n:
        tag = data[pos : pos + 4]
        length = int.from_bytes(data[pos + 4 : pos + 8], "big", signed=False)
        body_start = pos + 8
        body_end = body_start + length
        if _TAG_RE.fullmatch(tag) is None or body_end > n:
            pos += 1
            continue
        yield tag.decode("ascii", "replace"), data[body_start:body_end]
        pos = body_end


def _fields_from_track_body(body: bytes) -> dict[str, str]:
    fields: dict[str, str] = {}
    for tag, payload in _tagged_chunks(body):
        text = _text_from_body(payload)
        if text:
            fields.setdefault(tag, text)
    if not fields:
        text = _text_from_body(body)
        if text:
            fields["ptrk"] = text
    return fields


def _text_from_body(body: bytes) -> str:
    raw = body.strip(b"\x00\r\n\t ")
    if not raw:
        return ""
    # Serato tagged strings are usually UTF-8, but older rows can be UTF-16-ish.
    candidates = ("utf-8", "utf-16-le", "utf-16-be") if b"\x00" in raw else ("utf-8",)
    for encoding in candidates:
        try:
            text = raw.decode(encoding)
        except UnicodeDecodeError:
            continue
        text = text.replace("\x00", "").strip()
        if text:
            return text
    return raw.decode("utf-8", "replace").replace("\x00", "").strip()


def _first_field(fields: dict[str, str], *tags: str, default: str = "") -> str:
    for tag in tags:
        value = fields.get(tag)
        if value:
            return value
    return default


def _float_field(fields: dict[str, str], *tags: str) -> float:
    raw = _first_field(fields, *tags)
    if not raw:
        return 0.0
    try:
        return float(raw)
    except ValueError:
        return 0.0


def _duration_field(fields: dict[str, str], *tags: str) -> float:
    value = _float_field(fields, *tags)
    if value > 10000:
        return value / 1000.0
    return value


def _int_field(fields: dict[str, str], *tags: str) -> int:
    raw = _first_field(fields, *tags)
    if not raw:
        return 0
    try:
        return int(float(raw))
    except ValueError:
        return 0


def _rating_field(fields: dict[str, str], *tags: str) -> int:
    return max(0, min(5, _int_field(fields, *tags)))


def _path_stem(filepath: str) -> str:
    return Path(filepath.replace("\\", "/")).stem


def _track_id(filepath: str, title: str, artist: str) -> str:
    seed = "\x1f".join((filepath, title, artist))
    digest = hashlib.sha1(seed.encode("utf-8", "surrogatepass")).hexdigest()[:16]
    return f"serato:{digest}"


__all__ = ["SeratoSource"]
