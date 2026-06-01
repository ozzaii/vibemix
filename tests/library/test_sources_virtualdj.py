# SPDX-License-Identifier: Apache-2.0
"""VirtualDJSource contract tests.

VirtualDJ stores scanned BPM as seconds per beat, not displayed BPM. These
offline tests pin that conversion while keeping the source import light:
stdlib XML in, existing TrackEntry/CuePoint/TempoNode rows out.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from vibemix.library.rekordbox import TrackEntry
from vibemix.library.sources.base import LibrarySource
from vibemix.state.harmonics import to_camelot


def _write_database(tmp_path: Path) -> Path:
    database = """<?xml version="1.0" encoding="UTF-8"?>
<VirtualDJ_Database Version="8.2">
  <Song FilePath="/Users/test/Music/Psy/Track One.mp3" FileSize="25724840">
    <Tags Author="Artist A" Title="Track One" Album="Album X" Genre="Psytrance"
          Label="Label Y" Stars="4" />
    <Infos SongLength="421.5" PlayCount="7" Bitrate="320" />
    <Scan Version="801" Bpm="0.405405" Key="8A" />
    <Comment Text="energy note" />
    <Poi Pos="0.000000" Type="beatgrid" Bpm="0.405405" />
    <Poi Name="Intro" Pos="16.000000" Type="cue" Num="1" />
    <Poi Name="Loop" Pos="64.000000" Type="saved_loop" Num="2" Size="16.000000" />
  </Song>
  <Song FilePath="/Users/test/Music/Bare/Bare.wav">
    <Tags Author="Artist B" />
    <Infos SongLength="300" />
    <Scan Bpm="120" Key="Am" />
  </Song>
</VirtualDJ_Database>
"""
    path = tmp_path / "database.xml"
    path.write_text(database, encoding="utf-8")
    return path


def test_virtualdj_source_import_pulls_no_heavy_dep():
    code = (
        "import sys; import vibemix.library.sources.virtualdj; "
        "assert 'torch' not in sys.modules, 'torch leaked'; "
        "assert 'laion_clap' not in sys.modules, 'laion_clap leaked'"
    )
    repo_src = str(Path(__file__).resolve().parents[2] / "src")
    env = {**dict(os.environ), "PYTHONPATH": repo_src}
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, env=env
    )
    assert result.returncode == 0, result.stderr


def test_virtualdj_source_detect_explicit_path(tmp_path):
    from vibemix.library.sources.virtualdj import VirtualDJSource

    database_path = _write_database(tmp_path)
    source = VirtualDJSource(database_path=str(database_path))

    assert source.name == "virtualdj"
    assert source.detect() is True
    assert Path(source.resolved_path or "") == database_path
    assert isinstance(source, LibrarySource)


def test_virtualdj_source_detect_missing_returns_false(tmp_path):
    from vibemix.library.sources.virtualdj import VirtualDJSource

    source = VirtualDJSource(database_path=str(tmp_path / "missing.xml"))

    assert source.detect() is False


def test_virtualdj_source_iter_tracks_maps_metadata_cues_bpm_and_beatgrid(tmp_path):
    from vibemix.library.sources.virtualdj import VirtualDJSource

    database_path = _write_database(tmp_path)
    entries = list(VirtualDJSource(database_path=str(database_path)).iter_tracks())

    assert len(entries) == 2
    assert all(isinstance(entry, TrackEntry) for entry in entries)

    first = entries[0]
    assert first.track_id.startswith("virtualdj:")
    assert first.title == "Track One"
    assert first.artist == "Artist A"
    assert first.album == "Album X"
    assert first.genre == "Psytrance"
    assert first.label == "Label Y"
    assert first.comments == "energy note"
    assert first.play_count == 7
    assert first.rating == 4
    assert first.bpm == pytest.approx(148.0, abs=0.001)
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
    assert first.beatgrid[0].bpm == pytest.approx(148.0, abs=0.001)
    assert first.beatgrid[0].battito == 1

    second = entries[1]
    assert second.track_id.startswith("virtualdj:")
    assert second.title == "Bare"
    assert second.artist == "Artist B"
    assert second.bpm == 120.0
    assert second.key == "Am"
    assert second.camelot == "8A"
    assert second.cues == ()
    assert second.beatgrid == ()


def test_virtualdj_source_missing_database_raises(tmp_path):
    from vibemix.library.sources.virtualdj import VirtualDJSource

    source = VirtualDJSource(database_path=str(tmp_path / "missing.xml"))

    with pytest.raises(FileNotFoundError, match=r"database\.xml"):
        list(source.iter_tracks())
