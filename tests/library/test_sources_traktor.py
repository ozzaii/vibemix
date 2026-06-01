# SPDX-License-Identifier: Apache-2.0
"""TraktorSource contract tests.

These stay source-level and offline: no Traktor runtime, no audio decode, no
CLAP. The package proves that an exported Traktor ``collection.nml`` can enter
the existing LibrarySource/TrackEntry ingest shape.
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


def _write_nml(tmp_path: Path) -> Path:
    nml = """<?xml version="1.0" encoding="UTF-8"?>
<NML VERSION="19">
  <COLLECTION ENTRIES="2">
    <ENTRY AUDIO_ID="abc123" TITLE="Entry Title" ARTIST="Entry Artist">
      <LOCATION DIR="/Users/test/Music/:Psy/" FILE="Track%20One.mp3" VOLUME="Macintosh HD" />
      <INFO TITLE="Track One" ARTIST="Artist A" ALBUM="Album X" GENRE="Psytrance"
            LABEL="Label Y" COMMENT="energy note" PLAYTIME_FLOAT="421.5"
            RANKING="204" PLAYCOUNT="7" />
      <TEMPO BPM="148.000" />
      <MUSICAL_KEY VALUE="8A" />
      <CUE_V2 NAME="Intro" TYPE="0" START="16.000" LEN="0.000" HOTCUE="1" />
      <CUE_V2 NAME="Loop" TYPE="5" START="64.000" LEN="16.000" HOTCUE="2" />
    </ENTRY>
    <ENTRY TITLE="Bare Track" ARTIST="Artist B">
      <LOCATION DIR="/:Users/:test/:Music/:Bare/" FILE="Bare.wav" />
      <INFO PLAYTIME="300" RANKING="3" />
      <TEMPO BPM="120" />
      <MUSICAL_KEY VALUE="Am" />
    </ENTRY>
  </COLLECTION>
</NML>
"""
    path = tmp_path / "collection.nml"
    path.write_text(nml, encoding="utf-8")
    return path


def test_traktor_source_import_pulls_no_heavy_dep():
    code = (
        "import sys; import vibemix.library.sources.traktor; "
        "assert 'torch' not in sys.modules, 'torch leaked'; "
        "assert 'laion_clap' not in sys.modules, 'laion_clap leaked'"
    )
    repo_src = str(Path(__file__).resolve().parents[2] / "src")
    env = {**dict(os.environ), "PYTHONPATH": repo_src}
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, env=env
    )
    assert result.returncode == 0, result.stderr


def test_traktor_source_detect_explicit_path(tmp_path):
    from vibemix.library.sources.traktor import TraktorSource

    nml_path = _write_nml(tmp_path)
    source = TraktorSource(nml_path=str(nml_path))

    assert source.name == "traktor"
    assert source.detect() is True
    assert Path(source.resolved_path or "") == nml_path
    assert isinstance(source, LibrarySource)


def test_traktor_source_detect_missing_returns_false(tmp_path):
    from vibemix.library.sources.traktor import TraktorSource

    source = TraktorSource(nml_path=str(tmp_path / "missing.nml"))

    assert source.detect() is False


def test_traktor_source_iter_tracks_maps_metadata_cues_and_paths(tmp_path):
    from vibemix.library.sources.traktor import TraktorSource

    nml_path = _write_nml(tmp_path)
    entries = list(TraktorSource(nml_path=str(nml_path)).iter_tracks())

    assert len(entries) == 2
    assert all(isinstance(entry, TrackEntry) for entry in entries)

    first = entries[0]
    assert first.track_id == "traktor:abc123"
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

    second = entries[1]
    assert second.track_id.startswith("traktor:")
    assert second.title == "Bare Track"
    assert second.artist == "Artist B"
    assert second.rating == 3
    assert second.duration_s == 300.0
    assert second.filepath == "/Users/test/Music/Bare/Bare.wav"
    assert second.key == "Am"
    assert second.camelot == "8A"
    assert second.cues == ()


def test_traktor_source_missing_collection_raises(tmp_path):
    from vibemix.library.sources.traktor import TraktorSource

    source = TraktorSource(nml_path=str(tmp_path / "missing.nml"))

    with pytest.raises(FileNotFoundError, match=r"collection\.nml"):
        list(source.iter_tracks())
