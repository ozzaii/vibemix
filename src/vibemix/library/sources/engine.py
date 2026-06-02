# SPDX-License-Identifier: Apache-2.0
"""Engine DJ ``m.db`` source for the shared LibrarySource contract.

Engine DJ libraries are SQLite catalogs. This source reads an ``m.db`` file
read-only and maps supported track rows onto the existing ``TrackEntry`` shape
used by Rekordbox/Traktor/VirtualDJ ingest.

This first slice intentionally avoids Engine DJ write-back and the opaque
``PerformanceData`` blobs. If a catalog exposes cues or beatgrids as ordinary
relational rows, they are parsed; otherwise those fields stay honestly empty.
"""

from __future__ import annotations

import hashlib
import sqlite3
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from vibemix.library.rekordbox import CuePoint, TempoNode, TrackEntry
from vibemix.state.harmonics import to_camelot

_MACOS_DEFAULTS = (
    "~/Music/Engine Library/Database2/m.db",
    "~/Library/Application Support/Engine DJ/Database2/m.db",
    "~/Library/Application Support/Engine/Database2/m.db",
)
_WINDOWS_DEFAULTS = (
    r"~\Music\Engine Library\Database2\m.db",
    r"~\AppData\Local\Engine DJ\Database2\m.db",
)

_TRACK_TABLES = ("Track", "Tracks", "LibraryTrack", "LibraryTracks", "Song", "Songs")
_CUE_TABLES = ("Cue", "Cues", "HotCue", "HotCues", "CuePoint", "CuePoints")
_BEATGRID_TABLES = ("BeatGrid", "BeatGrids", "Beatgrid", "Beatgrids", "Tempo", "Tempos")

_TRACK_ID_COLUMNS = ("id", "track_id", "trackid", "uuid", "persistent_id", "persistentid")
_TITLE_COLUMNS = ("title", "name", "track_title")
_ARTIST_COLUMNS = ("artist", "artist_name", "artistname")
_ALBUM_COLUMNS = ("album", "album_name", "albumname")
_BPM_COLUMNS = ("bpm", "tempo", "average_bpm", "averagebpm")
_KEY_COLUMNS = ("key", "musical_key", "musicalkey", "key_text", "keytext")
_PATH_COLUMNS = ("filepath", "file_path", "path", "filename", "file", "location", "absolute_path")
_DURATION_COLUMNS = (
    "duration_s",
    "duration_seconds",
    "length_s",
    "length_seconds",
    "duration",
    "length",
    "duration_ms",
    "length_ms",
)
_GENRE_COLUMNS = ("genre", "genre_name", "genrename")
_LABEL_COLUMNS = ("label", "record_label", "publisher")
_RATING_COLUMNS = ("rating", "stars", "star_rating")
_PLAY_COUNT_COLUMNS = ("play_count", "playcount", "plays")
_COMMENT_COLUMNS = ("comment", "comments", "notes")

_CUE_TRACK_COLUMNS = ("track_id", "trackid", "track", "song_id", "songid")
_CUE_POSITION_COLUMNS = (
    "position_s",
    "position",
    "position_ms",
    "start_s",
    "start",
    "start_ms",
    "time_s",
    "time",
    "time_ms",
    "offset",
)
_CUE_NAME_COLUMNS = ("name", "label", "title")
_CUE_TYPE_COLUMNS = ("type", "kind", "cue_type", "cuetype")
_CUE_NUMBER_COLUMNS = ("number", "hotcue", "hot_cue", "slot", "idx", "index")
_CUE_LENGTH_COLUMNS = (
    "length_s",
    "length",
    "duration_s",
    "duration",
    "loop_length",
    "size",
    "length_ms",
    "duration_ms",
)

_GRID_TRACK_COLUMNS = _CUE_TRACK_COLUMNS
_GRID_POSITION_COLUMNS = _CUE_POSITION_COLUMNS
_GRID_BPM_COLUMNS = _BPM_COLUMNS
_GRID_METER_COLUMNS = ("meter", "metro", "time_signature", "timesignature")
_GRID_BEAT_COLUMNS = ("beat", "battito", "phase")


class EngineDJSource:
    """Engine DJ ``m.db`` source (structural :class:`LibrarySource`)."""

    name = "engine"

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
        """Return True iff an Engine DJ ``m.db`` exists at a candidate path."""
        for candidate in self.default_paths():
            try:
                if candidate.is_file():
                    self.resolved_path = str(candidate)
                    return True
            except OSError:  # pragma: no cover - permission/odd FS
                continue
        return False

    def iter_tracks(self) -> Iterable[TrackEntry]:
        """Yield parsed Engine DJ catalog rows as ``TrackEntry`` objects."""
        if self.resolved_path is None and not self.detect():
            raise FileNotFoundError(
                "EngineDJSource: no m.db detected - pass an explicit path or point "
                "setup at your Engine DJ Database2/m.db"
            )

        assert self.resolved_path is not None
        conn = sqlite3.connect(f"file:{self.resolved_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        try:
            track_table = _pick_track_table(conn)
            if track_table is None:
                raise RuntimeError("EngineDJSource: no supported track table found in m.db")
            cues = _cues_by_track(conn)
            beatgrids = _beatgrids_by_track(conn)
            for row in _select_all(conn, track_table):
                yield _track_from_row(row, cues=cues, beatgrids=beatgrids)
        finally:
            conn.close()


def _pick_track_table(conn: sqlite3.Connection) -> str | None:
    tables = _table_names(conn)
    by_lower = {table.lower(): table for table in tables}
    for candidate in _TRACK_TABLES:
        table = by_lower.get(candidate.lower())
        if table and _looks_like_track_table(conn, table):
            return table
    for table in tables:
        if _looks_like_track_table(conn, table):
            return table
    return None


def _looks_like_track_table(conn: sqlite3.Connection, table: str) -> bool:
    columns = _columns(conn, table)
    return _has_any(columns, _PATH_COLUMNS) and (
        _has_any(columns, _TITLE_COLUMNS)
        or _has_any(columns, _ARTIST_COLUMNS)
        or _has_any(columns, _TRACK_ID_COLUMNS)
    )


def _track_from_row(
    row: sqlite3.Row,
    *,
    cues: Mapping[str, tuple[CuePoint, ...]],
    beatgrids: Mapping[str, tuple[TempoNode, ...]],
) -> TrackEntry:
    raw_id = _first_text(_row_value(row, *_TRACK_ID_COLUMNS))
    filepath = _first_text(_row_value(row, *_PATH_COLUMNS))
    title = _first_text(_row_value(row, *_TITLE_COLUMNS), default=_path_stem(filepath))
    artist = _first_text(_row_value(row, *_ARTIST_COLUMNS))
    key = _first_text(_row_value(row, *_KEY_COLUMNS))
    duration_value, duration_column = _row_value_with_column(row, *_DURATION_COLUMNS)

    return TrackEntry(
        track_id=_track_id(raw_id, filepath, title, artist),
        title=title,
        artist=artist,
        album=_first_text(_row_value(row, *_ALBUM_COLUMNS)),
        bpm=_float_value(_row_value(row, *_BPM_COLUMNS)),
        key=key,
        duration_s=_seconds_value(duration_value, duration_column),
        cues=cues.get(raw_id, ()),
        filepath=filepath,
        genre=_first_text(_row_value(row, *_GENRE_COLUMNS)),
        label=_first_text(_row_value(row, *_LABEL_COLUMNS)),
        rating=_rating(_row_value(row, *_RATING_COLUMNS)),
        play_count=_int_value(_row_value(row, *_PLAY_COUNT_COLUMNS)),
        comments=_first_text(_row_value(row, *_COMMENT_COLUMNS)),
        camelot=to_camelot(key),
        beatgrid=beatgrids.get(raw_id, ()),
    )


def _cues_by_track(conn: sqlite3.Connection) -> dict[str, tuple[CuePoint, ...]]:
    table = _pick_optional_table(
        conn,
        _CUE_TABLES,
        required_columns=_CUE_TRACK_COLUMNS,
        payload_columns=_CUE_POSITION_COLUMNS,
    )
    if table is None:
        return {}

    out: dict[str, list[CuePoint]] = {}
    for row in _select_all(conn, table):
        track_id = _first_text(_row_value(row, *_CUE_TRACK_COLUMNS))
        if not track_id:
            continue
        position_value, position_column = _row_value_with_column(row, *_CUE_POSITION_COLUMNS)
        length_value, length_column = _row_value_with_column(row, *_CUE_LENGTH_COLUMNS)
        start_s = _seconds_value(position_value, position_column)
        length_s = _seconds_value(length_value, length_column)
        typ = _first_text(_row_value(row, *_CUE_TYPE_COLUMNS)).lower().replace(" ", "_")
        cue_type = "loop" if length_s > 0 or "loop" in typ else "cue"
        cue = CuePoint(
            name=_first_text(_row_value(row, *_CUE_NAME_COLUMNS)),
            type=cue_type,
            start_s=start_s,
            end_s=start_s + length_s if cue_type == "loop" and length_s > 0 else None,
            number=_hotcue_number(_row_value(row, *_CUE_NUMBER_COLUMNS)),
        )
        out.setdefault(track_id, []).append(cue)
    return {track_id: tuple(items) for track_id, items in out.items()}


def _beatgrids_by_track(conn: sqlite3.Connection) -> dict[str, tuple[TempoNode, ...]]:
    table = _pick_optional_table(
        conn,
        _BEATGRID_TABLES,
        required_columns=_GRID_TRACK_COLUMNS,
        payload_columns=_GRID_POSITION_COLUMNS,
    )
    if table is None:
        return {}

    out: dict[str, list[TempoNode]] = {}
    for row in _select_all(conn, table):
        track_id = _first_text(_row_value(row, *_GRID_TRACK_COLUMNS))
        if not track_id:
            continue
        position_value, position_column = _row_value_with_column(row, *_GRID_POSITION_COLUMNS)
        node = TempoNode(
            inizio_s=_seconds_value(position_value, position_column),
            bpm=_float_value(_row_value(row, *_GRID_BPM_COLUMNS)),
            metro=_first_text(_row_value(row, *_GRID_METER_COLUMNS)),
            battito=max(1, _int_value(_row_value(row, *_GRID_BEAT_COLUMNS)) or 1),
        )
        out.setdefault(track_id, []).append(node)
    return {track_id: tuple(items) for track_id, items in out.items()}


def _pick_optional_table(
    conn: sqlite3.Connection,
    candidates: tuple[str, ...],
    *,
    required_columns: tuple[str, ...],
    payload_columns: tuple[str, ...],
) -> str | None:
    tables = _table_names(conn)
    by_lower = {table.lower(): table for table in tables}
    ordered = [by_lower[name.lower()] for name in candidates if name.lower() in by_lower]
    ordered.extend(table for table in tables if table not in ordered)
    for table in ordered:
        columns = _columns(conn, table)
        if _has_any(columns, required_columns) and _has_any(columns, payload_columns):
            return table
    return None


def _table_names(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    return [str(row[0]) for row in rows]


def _columns(conn: sqlite3.Connection, table: str) -> dict[str, str]:
    rows = conn.execute(f"PRAGMA table_info({_quote_identifier(table)})").fetchall()
    return {str(row[1]).lower(): str(row[1]) for row in rows}


def _has_any(columns: Mapping[str, str], names: tuple[str, ...]) -> bool:
    return any(name.lower() in columns for name in names)


def _select_all(conn: sqlite3.Connection, table: str) -> Iterable[sqlite3.Row]:
    columns = _columns(conn, table)
    order_column = _first_column(columns, *_TRACK_ID_COLUMNS)
    order_by = f" ORDER BY {_quote_identifier(order_column)}" if order_column else ""
    return conn.execute(f"SELECT * FROM {_quote_identifier(table)}{order_by}")


def _first_column(columns: Mapping[str, str], *names: str) -> str:
    for name in names:
        column = columns.get(name.lower())
        if column:
            return column
    return ""


def _row_value(row: sqlite3.Row, *names: str) -> Any:
    value, _column = _row_value_with_column(row, *names)
    return value


def _row_value_with_column(row: sqlite3.Row, *names: str) -> tuple[Any, str]:
    keys = {key.lower(): key for key in row.keys()}
    for name in names:
        column = keys.get(name.lower())
        if column is not None:
            return row[column], column
    return None, ""


def _quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def _track_id(raw_id: str, filepath: str, title: str, artist: str) -> str:
    if raw_id:
        return f"engine:{raw_id}"
    seed = "\x1f".join((filepath, title, artist))
    digest = hashlib.sha1(seed.encode("utf-8", "surrogatepass")).hexdigest()[:16]
    return f"engine:{digest}"


def _seconds_value(value: Any, column: str = "") -> float:
    seconds = _float_value(value)
    if seconds <= 0:
        return 0.0
    lower = column.lower()
    if lower.endswith("_ms") or lower in {"durationms", "lengthms", "positionms"}:
        return seconds / 1000.0
    if seconds > 36_000:
        return seconds / 1000.0
    return seconds


def _float_value(value: Any) -> float:
    if value is None:
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _int_value(value: Any) -> int:
    if value is None:
        return 0
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def _rating(value: Any) -> int:
    return max(0, min(5, _int_value(value)))


def _hotcue_number(value: Any) -> int:
    number = _int_value(value)
    return number if number > 0 else -1


def _first_text(*values: Any, default: str = "") -> str:
    for value in values:
        text = "" if value is None else str(value).strip()
        if text:
            return text
    return default


def _path_stem(filepath: str) -> str:
    return Path(filepath.replace("\\", "/")).stem


__all__ = ["EngineDJSource"]
