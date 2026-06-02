# SPDX-License-Identifier: Apache-2.0
"""EngineDJSource contract tests.

These stay source-level and offline: no Engine DJ runtime, no audio decode, no
model imports. SQLite ``m.db`` fixture rows enter the existing LibrarySource /
TrackEntry / CuePoint / TempoNode shape.
"""

from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from vibemix.library.rekordbox import TrackEntry
from vibemix.library.sources.base import LibrarySource
from vibemix.state.harmonics import to_camelot


def _write_database(tmp_path: Path) -> Path:
    db_path = tmp_path / "m.db"
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(
            """
            CREATE TABLE Track (
                id TEXT PRIMARY KEY,
                title TEXT,
                artist TEXT,
                album TEXT,
                bpm REAL,
                key TEXT,
                duration_ms INTEGER,
                path TEXT,
                genre TEXT,
                label TEXT,
                rating INTEGER,
                play_count INTEGER,
                comment TEXT
            );
            INSERT INTO Track VALUES (
                'track-1',
                'Track One',
                'Artist A',
                'Album X',
                148.0,
                '8A',
                421500,
                '/Users/test/Music/Psy/Track One.mp3',
                'Psytrance',
                'Label Y',
                4,
                7,
                'energy note'
            );
            INSERT INTO Track VALUES (
                'track-2',
                'Bare Track',
                'Artist B',
                '',
                120.0,
                'Am',
                300000,
                '/Users/test/Music/Bare/Bare.wav',
                '',
                '',
                0,
                0,
                ''
            );
            CREATE TABLE Cue (
                track_id TEXT,
                position_ms INTEGER,
                name TEXT,
                type TEXT,
                hotcue INTEGER,
                length_ms INTEGER
            );
            INSERT INTO Cue VALUES ('track-1', 16000, 'Intro', 'cue', 1, 0);
            INSERT INTO Cue VALUES ('track-1', 64000, 'Loop', 'loop', 2, 16000);
            CREATE TABLE BeatGrid (
                track_id TEXT,
                position_ms INTEGER,
                bpm REAL,
                meter TEXT,
                beat INTEGER
            );
            INSERT INTO BeatGrid VALUES ('track-1', 0, 148.0, '4/4', 1);
            """
        )
        conn.commit()
    finally:
        conn.close()
    return db_path


def _write_alternate_database(tmp_path: Path) -> Path:
    db_path = tmp_path / "alternate.m.db"
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(
            """
            CREATE TABLE tracks (
                trackid INTEGER PRIMARY KEY,
                FilePath TEXT,
                Title TEXT,
                ArtistName TEXT,
                AverageBpm REAL,
                MusicalKey TEXT,
                Length REAL
            );
            INSERT INTO tracks VALUES (
                42,
                '/Users/test/Music/Alt/Alternate.aiff',
                'Alternate',
                'Artist C',
                150.5,
                '9B',
                360.0
            );
            """
        )
        conn.commit()
    finally:
        conn.close()
    return db_path


def test_engine_source_import_pulls_no_heavy_dep():
    code = (
        "import sys; import vibemix.library.sources.engine; "
        "assert 'torch' not in sys.modules, 'torch leaked'; "
        "assert 'laion_clap' not in sys.modules, 'laion_clap leaked'"
    )
    repo_src = str(Path(__file__).resolve().parents[2] / "src")
    env = {**dict(os.environ), "PYTHONPATH": repo_src}
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, env=env
    )
    assert result.returncode == 0, result.stderr


def test_engine_source_detect_explicit_path(tmp_path):
    from vibemix.library.sources.engine import EngineDJSource

    database_path = _write_database(tmp_path)
    source = EngineDJSource(database_path=str(database_path))

    assert source.name == "engine"
    assert source.detect() is True
    assert Path(source.resolved_path or "") == database_path
    assert isinstance(source, LibrarySource)


def test_engine_source_detect_missing_returns_false(tmp_path):
    from vibemix.library.sources.engine import EngineDJSource

    source = EngineDJSource(database_path=str(tmp_path / "missing.m.db"))

    assert source.detect() is False


def test_engine_source_iter_tracks_maps_metadata_cues_and_beatgrid(tmp_path):
    from vibemix.library.sources.engine import EngineDJSource

    database_path = _write_database(tmp_path)
    entries = list(EngineDJSource(database_path=str(database_path)).iter_tracks())

    assert len(entries) == 2
    assert all(isinstance(entry, TrackEntry) for entry in entries)

    first = entries[0]
    assert first.track_id == "engine:track-1"
    assert first.title == "Track One"
    assert first.artist == "Artist A"
    assert first.album == "Album X"
    assert first.genre == "Psytrance"
    assert first.label == "Label Y"
    assert first.comments == "energy note"
    assert first.play_count == 7
    assert first.rating == 4
    assert first.bpm == 148.0
    assert first.key == "8A"
    assert first.camelot == to_camelot(first.key)
    assert first.duration_s == 421.5
    assert first.filepath == "/Users/test/Music/Psy/Track One.mp3"

    assert len(first.cues) == 2
    assert first.cues[0].name == "Intro"
    assert first.cues[0].type == "cue"
    assert first.cues[0].start_s == 16.0
    assert first.cues[0].end_s is None
    assert first.cues[0].number == 1
    assert first.cues[1].name == "Loop"
    assert first.cues[1].type == "loop"
    assert first.cues[1].start_s == 64.0
    assert first.cues[1].end_s == 80.0
    assert first.cues[1].number == 2

    assert len(first.beatgrid) == 1
    assert first.beatgrid[0].inizio_s == 0.0
    assert first.beatgrid[0].bpm == 148.0
    assert first.beatgrid[0].metro == "4/4"
    assert first.beatgrid[0].battito == 1

    second = entries[1]
    assert second.track_id == "engine:track-2"
    assert second.title == "Bare Track"
    assert second.artist == "Artist B"
    assert second.duration_s == 300.0
    assert second.key == "Am"
    assert second.camelot == "8A"
    assert second.cues == ()
    assert second.beatgrid == ()


def test_engine_source_accepts_case_variant_track_schema(tmp_path):
    from vibemix.library.sources.engine import EngineDJSource

    database_path = _write_alternate_database(tmp_path)
    entries = list(EngineDJSource(database_path=str(database_path)).iter_tracks())

    assert len(entries) == 1
    track = entries[0]
    assert track.track_id == "engine:42"
    assert track.title == "Alternate"
    assert track.artist == "Artist C"
    assert track.filepath == "/Users/test/Music/Alt/Alternate.aiff"
    assert track.bpm == 150.5
    assert track.key == "9B"
    assert track.duration_s == 360.0
    assert track.cues == ()
    assert track.beatgrid == ()


def test_engine_source_missing_database_raises(tmp_path):
    from vibemix.library.sources.engine import EngineDJSource

    source = EngineDJSource(database_path=str(tmp_path / "missing.m.db"))

    with pytest.raises(FileNotFoundError, match=r"m\.db"):
        list(source.iter_tracks())


def test_engine_source_unsupported_schema_raises(tmp_path):
    from vibemix.library.sources.engine import EngineDJSource

    database_path = tmp_path / "m.db"
    conn = sqlite3.connect(database_path)
    try:
        conn.execute("CREATE TABLE unrelated (id INTEGER PRIMARY KEY, value TEXT)")
        conn.commit()
    finally:
        conn.close()

    with pytest.raises(RuntimeError, match="track table"):
        list(EngineDJSource(database_path=str(database_path)).iter_tracks())
