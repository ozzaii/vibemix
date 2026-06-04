# SPDX-License-Identifier: Apache-2.0
"""Vibe Mix export — ``export_set`` writes a Rekordbox-importable collection.xml.

The export is the LAST mile of the sequencer: an ordered, sequenced set →
a self-contained ``collection.xml`` (``DJ_PLAYLISTS → PRODUCT + COLLECTION +
PLAYLISTS``) that Rekordbox 6/7 can import with order + key + BPM + cues +
beatgrid intact (research §C). These tests build the XML to a tmp path and
RE-PARSE it (raw ``xml.etree`` — no real disk files needed, pyrekordbox just
URI-encodes the location string) to assert the contract holds end to end.

Cardinal facts the tests pin:
* playlist ORDER is preserved (the guaranteed win, research §C);
* ``Tonality`` is the CLASSICAL key (``Am``), never the internal Camelot
  code (``8A``) — a Camelot tag in the XML would be a silent corruption;
* a single ``TEMPO`` (beatgrid) and ``POSITION_MARK`` (cue) round-trip;
* dedup by location: the same file twice → ONE collection track, TWO
  playlist refs (no ``XmlDuplicateError`` crash);
* a missing/empty filepath is honestly SKIPPED (recorded as dropped), the
  export never crashes on it;
* an unknown Camelot key OMITS Tonality rather than fabricating one.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace

import pytest

from vibemix.library.export_rekordbox import export_set


def _parse(path: Path) -> ET.Element:
    """Raw re-parse of a written collection.xml → DJ_PLAYLISTS root."""
    return ET.parse(str(path)).getroot()


def _collection_tracks(root: ET.Element) -> list[ET.Element]:
    coll = root.find("COLLECTION")
    assert coll is not None
    return coll.findall("TRACK")


def _playlist_keys(root: ET.Element, name: str) -> list[str]:
    """Ordered list of Key attrs (TrackID refs) in the named playlist node."""
    node = root.find(f'.//PLAYLISTS//NODE[@Name="{name}"]')
    assert node is not None, f"playlist node {name!r} not found"
    return [el.attrib["Key"] for el in node.findall("TRACK")]


def _track(genre: str | None = None, **over) -> dict:
    """A minimal well-formed set item; override fields per test."""
    base = {
        "track_id": "t1",
        "filepath": "/Music/a.wav",
        "title": "Track A",
        "artist": "Artist A",
        "bpm": 128.0,
        "camelot": "8A",
        "duration_s": 312.4,
    }
    if genre is not None:
        base["genre"] = genre
    base.update(over)
    return base


# --------------------------------------------------------------------- #
# Happy path: a valid file is written and re-parses cleanly             #
# --------------------------------------------------------------------- #


def test_export_writes_parseable_collection_xml(tmp_path):
    out = tmp_path / "set.xml"
    result = export_set(
        [_track(genre="Techno")],
        name="Saturday Set",
        out_path=out,
    )
    assert result == out
    assert out.exists()

    root = _parse(out)
    assert root.tag == "DJ_PLAYLISTS"
    assert root.find("PRODUCT") is not None
    assert root.find("COLLECTION") is not None
    assert root.find("PLAYLISTS") is not None

    tracks = _collection_tracks(root)
    assert len(tracks) == 1
    t = tracks[0]
    assert t.attrib["Name"] == "Track A"
    assert t.attrib["Artist"] == "Artist A"
    assert t.attrib["Genre"] == "Techno"
    assert float(t.attrib["AverageBpm"]) == pytest.approx(128.0)
    # TotalTime is integer seconds, rounded.
    assert t.attrib["TotalTime"] == "312"


def test_location_is_uri_encoded_not_pre_encoded(tmp_path):
    out = tmp_path / "set.xml"
    export_set(
        [_track(filepath="/Music/My Track.wav")],
        name="S",
        out_path=out,
    )
    root = _parse(out)
    loc = _collection_tracks(root)[0].attrib["Location"]
    # The setter URI-encodes (space → %20) and adds the file://localhost prefix.
    assert loc.startswith("file://localhost/")
    assert "My%20Track.wav" in loc
    # Never double-encoded.
    assert "%2520" not in loc


# --------------------------------------------------------------------- #
# Tonality MUST be classical, never Camelot                             #
# --------------------------------------------------------------------- #


def test_tonality_is_classical_not_camelot(tmp_path):
    out = tmp_path / "set.xml"
    export_set([_track(camelot="8A")], name="S", out_path=out)
    root = _parse(out)
    t = _collection_tracks(root)[0]
    assert t.attrib["Tonality"] == "Am"  # 8A → Am
    assert t.attrib["Tonality"] != "8A"


def test_unknown_camelot_omits_tonality(tmp_path):
    out = tmp_path / "set.xml"
    export_set([_track(camelot="not-a-key")], name="S", out_path=out)
    root = _parse(out)
    t = _collection_tracks(root)[0]
    assert "Tonality" not in t.attrib  # honest omission, no fabrication


def test_none_camelot_omits_tonality(tmp_path):
    out = tmp_path / "set.xml"
    export_set([_track(camelot=None)], name="S", out_path=out)
    root = _parse(out)
    assert "Tonality" not in _collection_tracks(root)[0].attrib


# --------------------------------------------------------------------- #
# Playlist ORDER is preserved — the guaranteed win                      #
# --------------------------------------------------------------------- #


def test_playlist_order_preserved(tmp_path):
    out = tmp_path / "set.xml"
    set_tracks = [
        _track(track_id="t1", filepath="/Music/1.wav", title="One"),
        _track(track_id="t2", filepath="/Music/2.wav", title="Two"),
        _track(track_id="t3", filepath="/Music/3.wav", title="Three"),
    ]
    export_set(set_tracks, name="Ordered", out_path=out)
    root = _parse(out)

    keys = _playlist_keys(root, "Ordered")
    assert len(keys) == 3
    # Map collection TrackIDs back to titles, then verify playlist order.
    id_to_title = {
        t.attrib["TrackID"]: t.attrib["Name"] for t in _collection_tracks(root)
    }
    assert [id_to_title[k] for k in keys] == ["One", "Two", "Three"]


# --------------------------------------------------------------------- #
# Beatgrid (TEMPO) + cues (POSITION_MARK)                               #
# --------------------------------------------------------------------- #


def test_beatgrid_tempo_written(tmp_path):
    out = tmp_path / "set.xml"
    export_set(
        [_track(beatgrid={"inizio": 0.012, "bpm": 128.0, "metro": "4/4", "battito": 1})],
        name="S",
        out_path=out,
    )
    root = _parse(out)
    tempo = _collection_tracks(root)[0].find("TEMPO")
    assert tempo is not None
    assert float(tempo.attrib["Bpm"]) == pytest.approx(128.0)
    assert float(tempo.attrib["Inizio"]) == pytest.approx(0.012)
    assert tempo.attrib["Metro"] == "4/4"
    assert tempo.attrib["Battito"] == "1"


def test_beatgrid_defaults_from_bpm_only(tmp_path):
    """A beatgrid dict carrying only bpm → constant-tempo node with defaults."""
    out = tmp_path / "set.xml"
    export_set(
        [_track(beatgrid={"bpm": 124.0})],
        name="S",
        out_path=out,
    )
    root = _parse(out)
    tempo = _collection_tracks(root)[0].find("TEMPO")
    assert tempo is not None
    assert float(tempo.attrib["Bpm"]) == pytest.approx(124.0)
    assert float(tempo.attrib["Inizio"]) == pytest.approx(0.0)
    assert tempo.attrib["Metro"] == "4/4"
    assert tempo.attrib["Battito"] == "1"


def test_hot_and_memory_cues_written(tmp_path):
    out = tmp_path / "set.xml"
    cues = [
        {"name": "DROP", "type": "cue", "start_s": 64.5, "num": 0},  # hot cue A
        {"name": "MEM", "type": "cue", "start_s": 12.0, "num": -1},  # memory cue
        {"name": "LOOP", "type": "loop", "start_s": 96.0, "end_s": 104.0, "num": 1},
    ]
    export_set([_track(cues=cues)], name="S", out_path=out)
    root = _parse(out)
    marks = _collection_tracks(root)[0].findall("POSITION_MARK")
    assert len(marks) == 3

    by_name = {m.attrib["Name"]: m for m in marks}
    assert by_name["DROP"].attrib["Num"] == "0"
    assert float(by_name["DROP"].attrib["Start"]) == pytest.approx(64.5)
    # Type is stored as the numeric code: cue == "0", loop == "4".
    assert by_name["DROP"].attrib["Type"] == "0"
    assert by_name["MEM"].attrib["Num"] == "-1"
    # Loop carries an End.
    assert by_name["LOOP"].attrib["Type"] == "4"
    assert float(by_name["LOOP"].attrib["End"]) == pytest.approx(104.0)


def test_machine_cue_provenance_is_visible_and_dj_cues_are_preserved(tmp_path):
    """Auto/ANLZ/fallback cues must not land byte-identical to DJ cues.

    Rekordbox XML has no Source attribute on POSITION_MARK, so the visible
    carrier provenance is the reserved VM prefix. DJ-authored names stay
    verbatim unless they try to use that prefix, in which case the mark is
    rejected instead of masquerading.
    """
    out = tmp_path / "set.xml"
    cues = [
        {"name": "DROP", "type": "cue", "start_s": 64.5, "num": 0, "source": "dj"},
        {"name": "INTRO", "type": "cue", "start_s": 8.0, "num": 1, "source": "auto"},
        {"name": "BUILD", "type": "cue", "start_s": 32.0, "num": 2, "source": "anlz"},
        {
            "name": "BREAKDOWN",
            "type": "cue",
            "start_s": 96.0,
            "num": 3,
            "source": "fallback",
        },
        {"name": "VM SPOOF", "type": "cue", "start_s": 128.0, "num": 4, "source": "dj"},
    ]
    export_set([_track(cues=cues)], name="S", out_path=out)

    root = _parse(out)
    marks = _collection_tracks(root)[0].findall("POSITION_MARK")
    names = [m.attrib["Name"] for m in marks]
    assert names == ["DROP", "VM INTRO", "VM BUILD", "VM BREAKDOWN"]
    assert "VM SPOOF" not in names
    by_name = {m.attrib["Name"]: m for m in marks}
    assert by_name["DROP"].attrib["Num"] == "0"
    assert by_name["VM INTRO"].attrib["Num"] == "1"
    assert by_name["VM BUILD"].attrib["Num"] == "2"
    assert by_name["VM BREAKDOWN"].attrib["Num"] == "3"

    rbxml = pytest.importorskip("pyrekordbox.rbxml")
    rb = rbxml.RekordboxXml(out)
    rb_tracks = rb.get_tracks()
    assert len(rb_tracks) == 1
    rb_marks = rb_tracks[0].marks
    by_num = {mark.Num: mark for mark in rb_marks}
    assert set(by_num) == {0, 1, 2, 3}
    assert by_num[0].Name == "DROP"
    assert not by_num[0].Name.startswith("VM ")
    for num in (1, 2, 3):
        assert by_num[num].Name.startswith("VM ")


# --------------------------------------------------------------------- #
# Optional metadata: Colour + Rating                                    #
# --------------------------------------------------------------------- #


def test_colour_and_rating_written(tmp_path):
    out = tmp_path / "set.xml"
    export_set(
        [_track(colour="0xFF007F", rating=4)],
        name="S",
        out_path=out,
    )
    root = _parse(out)
    t = _collection_tracks(root)[0]
    assert t.attrib["Colour"] == "0xFF007F"
    # Rating uses the byte mapping: 4 → "204".
    assert t.attrib["Rating"] == "204"


# --------------------------------------------------------------------- #
# Dedup: same file twice → one collection track, two playlist refs      #
# --------------------------------------------------------------------- #


def test_duplicate_location_deduped_in_collection_referenced_twice(tmp_path):
    out = tmp_path / "set.xml"
    set_tracks = [
        _track(track_id="t1", filepath="/Music/same.wav", title="Same"),
        _track(track_id="t2", filepath="/Music/same.wav", title="SameAgain"),
        _track(track_id="t3", filepath="/Music/other.wav", title="Other"),
    ]
    export_set(set_tracks, name="Dedup", out_path=out)
    root = _parse(out)

    # The shared file appears ONCE in the collection (2 unique locations).
    assert len(_collection_tracks(root)) == 2
    # But the playlist references it in every slot the set asked for (3 total).
    keys = _playlist_keys(root, "Dedup")
    assert len(keys) == 3
    # The first two slots reference the SAME collection track id.
    assert keys[0] == keys[1]
    assert keys[2] != keys[0]


# --------------------------------------------------------------------- #
# Honest skip: missing/empty filepath                                   #
# --------------------------------------------------------------------- #


def test_missing_filepath_skipped_not_crash(tmp_path):
    out = tmp_path / "set.xml"
    set_tracks = [
        _track(track_id="t1", filepath="/Music/ok.wav", title="OK"),
        _track(track_id="t2", filepath="", title="NoPath"),
        _track(track_id="t3", filepath="/Music/ok2.wav", title="OK2"),
    ]
    # Must not raise.
    export_set(set_tracks, name="Skips", out_path=out)
    root = _parse(out)
    titles = {t.attrib["Name"] for t in _collection_tracks(root)}
    assert titles == {"OK", "OK2"}
    assert "NoPath" not in titles
    # Playlist only references the surviving two.
    assert len(_playlist_keys(root, "Skips")) == 2


def test_none_filepath_skipped(tmp_path):
    out = tmp_path / "set.xml"
    set_tracks = [
        _track(track_id="t1", filepath=None, title="Gone"),
        _track(track_id="t2", filepath="/Music/keep.wav", title="Keep"),
    ]
    export_set(set_tracks, name="S", out_path=out)
    root = _parse(out)
    titles = {t.attrib["Name"] for t in _collection_tracks(root)}
    assert titles == {"Keep"}


def test_empty_set_writes_valid_empty_collection(tmp_path):
    """An empty (or all-skipped) set still produces a valid, parseable file."""
    out = tmp_path / "set.xml"
    export_set([], name="Empty", out_path=out)
    root = _parse(out)
    assert root.tag == "DJ_PLAYLISTS"
    assert len(_collection_tracks(root)) == 0
    assert _playlist_keys(root, "Empty") == []


def test_returns_written_path(tmp_path):
    out = tmp_path / "nested" / "deep" / "set.xml"
    # Parent dirs should be created.
    result = export_set([_track()], name="S", out_path=out)
    assert result == out
    assert out.exists()


# --------------------------------------------------------------------- #
# Re-parse with pyrekordbox itself (proves Rekordbox-importable shape)  #
# --------------------------------------------------------------------- #


# --------------------------------------------------------------------- #
# WR-03: the CLI export-set re-validates against the live library        #
# --------------------------------------------------------------------- #


def test_cli_export_set_drops_ungrounded_when_library_present():
    """WR-03. The CLI validation helper drops a set item that resolves to no
    library track (by id or filepath), keeping only grounded entries."""
    from vibemix.__main__ import _validate_export_tracks_against_library
    from vibemix.library.rekordbox import RekordboxLibrary, TrackEntry

    lib = RekordboxLibrary()
    lib.tracks = {
        "t1": TrackEntry(
            track_id="t1",
            title="Real",
            artist="A",
            album="",
            bpm=124.0,
            key="8A",
            duration_s=300.0,
            cues=(),
            filepath="/Music/real.wav",
        )
    }
    tracks = [
        {"track_id": "t1", "filepath": "/Music/real.wav", "title": "Real"},
        {"track_id": "GHOST", "filepath": "/Music/ghost.wav", "title": "Ghost"},
    ]
    kept, dropped = _validate_export_tracks_against_library(tracks, lib)
    kept_ids = [t["track_id"] for t in kept]
    assert kept_ids == ["t1"]  # only the grounded id survived
    assert len(dropped) == 1
    assert dropped[0]["track_id"] == "GHOST"
    assert "ungrounded" in dropped[0]["reason"]


def test_cli_export_set_resolves_by_filepath():
    """A track with an unknown id but a matching filepath is still grounded."""
    from vibemix.__main__ import _validate_export_tracks_against_library
    from vibemix.library.rekordbox import RekordboxLibrary, TrackEntry

    lib = RekordboxLibrary()
    lib.tracks = {
        "lib-id": TrackEntry(
            track_id="lib-id",
            title="Real",
            artist="A",
            album="",
            bpm=124.0,
            key="8A",
            duration_s=300.0,
            cues=(),
            filepath="/Music/real.wav",
        )
    }
    # id mismatch but filepath matches (normpath) → kept.
    tracks = [{"track_id": "other-id", "filepath": "/Music/./real.wav"}]
    kept, dropped = _validate_export_tracks_against_library(tracks, lib)
    assert len(kept) == 1
    assert dropped == []


def test_cli_export_set_allow_unvalidated_exports_new_local_files(
    tmp_path, monkeypatch, capsys
):
    """The default CLI gate protects grounded set exports, but an explicit
    advanced flag lets users build a Rekordbox XML for brand-new local files
    (for example generated cue-listen clips) that are not in the cache yet.
    """
    import json

    import vibemix.library as lib_pkg
    from vibemix.__main__ import _cmd_library_export_set
    from vibemix.library import export_rekordbox as export_mod

    class FakeLibrary:
        def __init__(self):
            self.tracks = {}

        def try_load_cache(self):
            return True

    captured: dict[str, object] = {}

    def fake_export_set(tracks, name, out_path):
        captured["tracks"] = tracks
        captured["name"] = name
        captured["out_path"] = out_path
        return SimpleNamespace(path=Path(out_path), written=len(tracks), referenced=len(tracks), dropped=[])

    monkeypatch.setattr(lib_pkg, "RekordboxLibrary", FakeLibrary)
    monkeypatch.setattr(export_mod, "export_set", fake_export_set)

    set_json = tmp_path / "clips.json"
    set_json.write_text(
        json.dumps(
            {
                "tracks": [
                    {
                        "track_id": "clip-001",
                        "filepath": str(tmp_path / "new-local-clip.mp3"),
                        "title": "A_INTRO__cue-8.533s__start-5.533s",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    code = _cmd_library_export_set(
        Namespace(
            set_json=str(set_json),
            out=str(tmp_path / "clips.xml"),
            name="Cue Clips",
            allow_unvalidated=True,
            json=True,
        )
    )

    assert code == 0
    assert captured["name"] == "Cue Clips"
    assert captured["out_path"] == str(tmp_path / "clips.xml")
    assert captured["tracks"] == [
        {
            "track_id": "clip-001",
            "filepath": str(tmp_path / "new-local-clip.mp3"),
            "title": "A_INTRO__cue-8.533s__start-5.533s",
        }
    ]
    assert "--allow-unvalidated set" in capsys.readouterr().err


def test_file_round_trips_through_pyrekordbox(tmp_path):
    from pyrekordbox.rbxml import RekordboxXml

    out = tmp_path / "set.xml"
    export_set(
        [
            _track(track_id="t1", filepath="/Music/1.wav", title="One", camelot="8A"),
            _track(track_id="t2", filepath="/Music/2.wav", title="Two", camelot="11A"),
        ],
        name="RoundTrip",
        out_path=out,
    )
    xml = RekordboxXml(str(out))
    tracks = xml.get_tracks()
    assert len(tracks) == 2
    names = {t["Name"] for t in tracks}
    assert names == {"One", "Two"}
    tonalities = {t["Tonality"] for t in tracks}
    assert tonalities == {"Am", "F#m"}  # 8A→Am, 11A→F#m, classical

    pl = xml.get_playlist("RoundTrip")
    assert pl.entries == 2
