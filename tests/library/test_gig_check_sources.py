# SPDX-License-Identifier: Apache-2.0
"""Gig Check over every LibrarySource — one verdict engine, five ecosystems.

The hand-of-god queue's "Serato input" item, generalized: the Phase 89
sources already parse Serato/Traktor/VirtualDJ/Engine into ``TrackEntry``,
so the audit engine must accept any of them, not just a Rekordbox XML.
Fixtures mirror the shapes in ``test_sources_*.py``.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from vibemix.library.gig_check import detect_source_kind, run_gig_check
from vibemix.library.rekordbox import RekordboxLibrary

# --- fixtures (mirroring test_sources_*.py builders) -------------------------- #


def _chunk(tag: str, body: bytes | str) -> bytes:
    payload = body.encode("utf-8") if isinstance(body, str) else body
    return tag.encode("ascii") + len(payload).to_bytes(4, "big") + payload


def _write_serato_library(tmp_path: Path) -> Path:
    root = tmp_path / "Music" / "_Serato_"
    root.mkdir(parents=True)
    audio_dir = tmp_path / "Music" / "PSY"
    audio_dir.mkdir()
    first = audio_dir / "Track One.mp3"
    second = audio_dir / "Bare.wav"
    first.write_bytes(b"audio")
    second.write_bytes(b"audio")

    def _track(path: Path, title: str, artist: str) -> bytes:
        return _chunk(
            "otrk",
            b"".join(
                (
                    _chunk("pfil", str(path)),
                    _chunk("tsng", title),
                    _chunk("tart", artist),
                    _chunk("tbpm", "148.0"),
                    _chunk("tkey", "8A"),
                    _chunk("tlen", "421500"),
                )
            ),
        )

    (root / "database V2").write_bytes(
        b"header" + _track(first, "Track One", "Artist A") + _track(second, "Bare", "B")
    )
    subcrates = root / "Subcrates"
    subcrates.mkdir()
    (subcrates / "Psy.crate").write_bytes(
        _chunk("otrk", _chunk("ptrk", str(first)))
        + _chunk("otrk", _chunk("ptrk", str(second)))
    )
    return root


def _write_nml(tmp_path: Path) -> Path:
    audio = tmp_path / "Track One.mp3"
    audio.write_bytes(b"audio")
    nml = f"""<?xml version="1.0" encoding="UTF-8"?>
<NML VERSION="19">
  <COLLECTION ENTRIES="1">
    <ENTRY TITLE="Entry Title" ARTIST="Entry Artist">
      <LOCATION DIR="/{tmp_path.as_posix().strip('/').replace('/', '/:')}/" FILE="Track One.mp3" />
      <INFO TITLE="Track One" ARTIST="Artist A" PLAYTIME_FLOAT="421.5" />
      <TEMPO BPM="148.000" />
      <MUSICAL_KEY VALUE="8A" />
      <CUE_V2 NAME="Intro" TYPE="0" START="16.000" LEN="0.000" HOTCUE="1" />
      <CUE_V2 NAME="Out" TYPE="0" START="400.000" LEN="0.000" HOTCUE="2" />
    </ENTRY>
  </COLLECTION>
</NML>
"""
    path = tmp_path / "collection.nml"
    path.write_text(nml, encoding="utf-8")
    return path


def _write_virtualdj_database(tmp_path: Path) -> Path:
    tmp_path.mkdir(exist_ok=True)
    audio = tmp_path / "Track One.mp3"
    audio.write_bytes(b"audio")
    database = f"""<?xml version="1.0" encoding="UTF-8"?>
<VirtualDJ_Database Version="8.2">
  <Song FilePath="{audio}" FileSize="100">
    <Tags Author="Artist A" Title="Track One" />
    <Infos SongLength="421.5" />
    <Scan Version="801" Bpm="0.405405" Key="8A" />
    <Poi Pos="0.000000" Type="beatgrid" Bpm="0.405405" />
    <Poi Name="Intro" Pos="16.000000" Type="cue" Num="1" />
    <Poi Name="Out" Pos="400.000000" Type="cue" Num="2" />
  </Song>
</VirtualDJ_Database>
"""
    path = tmp_path / "database.xml"
    path.write_text(database, encoding="utf-8")
    return path


def _write_engine_database(tmp_path: Path) -> Path:
    audio = tmp_path / "Track One.mp3"
    audio.write_bytes(b"audio")
    db_path = tmp_path / "m.db"
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(
            f"""
            CREATE TABLE Track (
                id TEXT PRIMARY KEY, title TEXT, artist TEXT, album TEXT,
                bpm REAL, key TEXT, duration_ms INTEGER, path TEXT,
                genre TEXT, label TEXT, rating INTEGER, play_count INTEGER,
                comment TEXT
            );
            INSERT INTO Track VALUES (
                'track-1', 'Track One', 'Artist A', '', 148.0, '8A', 421500,
                '{audio}', '', '', 4, 7, ''
            );
            CREATE TABLE Cue (
                track_id TEXT, position_ms INTEGER, name TEXT, type TEXT,
                hotcue INTEGER, length_ms INTEGER
            );
            INSERT INTO Cue VALUES ('track-1', 16000, 'Intro', 'cue', 1, 0);
            INSERT INTO Cue VALUES ('track-1', 400000, 'Out', 'cue', 2, 0);
            CREATE TABLE BeatGrid (
                track_id TEXT, position_ms INTEGER, bpm REAL, meter TEXT,
                beat INTEGER
            );
            INSERT INTO BeatGrid VALUES ('track-1', 0, 148.0, '4/4', 1);
            """
        )
        conn.commit()
    finally:
        conn.close()
    return db_path


# --- source-kind sniffing ------------------------------------------------------ #


def test_detect_source_kind_by_shape(tmp_path):
    assert detect_source_kind(_write_nml(tmp_path)) == "traktor"
    assert detect_source_kind(_write_engine_database(tmp_path)) == "engine"
    serato_root = _write_serato_library(tmp_path)
    assert detect_source_kind(serato_root) == "serato"
    assert detect_source_kind(serato_root.parent) == "serato"  # parent of _Serato_
    vdj = _write_virtualdj_database(tmp_path / "vdj_dir")
    assert detect_source_kind(vdj) == "virtualdj"
    rb = tmp_path / "collection.xml"
    rb.write_text('<?xml version="1.0"?><DJ_PLAYLISTS Version="1.0.0"/>')
    assert detect_source_kind(rb) == "rekordbox"


def test_detect_source_kind_rejects_unknown(tmp_path):
    weird = tmp_path / "notes.txt"
    weird.write_text("hello")
    with pytest.raises(ValueError):
        detect_source_kind(weird)


# --- run_gig_check over each ecosystem ------------------------------------------ #


def test_gig_check_traktor(tmp_path, monkeypatch):
    monkeypatch.setattr(RekordboxLibrary, "CACHE_PATH", tmp_path / "library.pkl")
    report = run_gig_check(_write_nml(tmp_path))
    assert report["source"] == "traktor"
    assert report["totals"]["tracks"] == 1
    # the fixture track has labeled hot cues incl. a late mix-out anchor
    assert report["verdict"] in ("take_it", "fix_first")


def test_gig_check_virtualdj(tmp_path, monkeypatch):
    monkeypatch.setattr(RekordboxLibrary, "CACHE_PATH", tmp_path / "library.pkl")
    report = run_gig_check(_write_virtualdj_database(tmp_path))
    assert report["source"] == "virtualdj"
    assert report["totals"]["tracks"] == 1


def test_gig_check_engine(tmp_path, monkeypatch):
    monkeypatch.setattr(RekordboxLibrary, "CACHE_PATH", tmp_path / "library.pkl")
    report = run_gig_check(_write_engine_database(tmp_path))
    assert report["source"] == "engine"
    assert report["totals"]["tracks"] == 1


def test_gig_check_serato_sees_crates_as_playlists(tmp_path, monkeypatch):
    monkeypatch.setattr(RekordboxLibrary, "CACHE_PATH", tmp_path / "library.pkl")
    report = run_gig_check(_write_serato_library(tmp_path), bloat_threshold=1)
    assert report["source"] == "serato"
    assert report["totals"]["tracks"] == 2
    # the Psy crate carries 2 members > threshold 1 → bloat receipt
    assert any(b["playlist"] == "Psy" for b in report["crate_bloat"])


def test_gig_check_serato_accepts_parent_directory(tmp_path, monkeypatch):
    # The natural CLI input is the folder CONTAINING _Serato_ (a music drive
    # root) — the source must be pinned to the resolved _Serato_ dir, not
    # the raw path.
    monkeypatch.setattr(RekordboxLibrary, "CACHE_PATH", tmp_path / "library.pkl")
    serato_root = _write_serato_library(tmp_path)
    report = run_gig_check(serato_root.parent)
    assert report["source"] == "serato"
    assert report["totals"]["tracks"] == 2


def test_gig_check_explicit_source_overrides_sniff(tmp_path, monkeypatch):
    monkeypatch.setattr(RekordboxLibrary, "CACHE_PATH", tmp_path / "library.pkl")
    # database.xml would sniff as virtualdj; an explicit source must win
    report = run_gig_check(_write_virtualdj_database(tmp_path), source="virtualdj")
    assert report["source"] == "virtualdj"
