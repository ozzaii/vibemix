# SPDX-License-Identifier: Apache-2.0
"""Gig Check — read-only preflight verdict over a parsed DJ library.

The 2026-06-11 hand-of-god research pack landed one executable conclusion:
the missing piece is a preflight AUDIT (missing files / cue debt / crate
bloat / duplicates) that ends in a take-it-or-not verdict. These tests pin
that contract: pure scoring over ``TrackEntry`` rows plus an XML loader path.

Pure-logic tests construct ``TrackEntry`` directly; the loader test goes
through a tmp ``collection.xml`` with ``RekordboxLibrary.CACHE_PATH``
monkeypatched to tmp (the cache-clobber gotcha in CLAUDE.md).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from vibemix.library.gig_check import (
    PlaylistRef,
    audit_library,
    format_report,
    run_gig_check,
)
from vibemix.library.rekordbox import CuePoint, RekordboxLibrary, TempoNode, TrackEntry

BEATGRID = (TempoNode(inizio_s=0.05, bpm=126.0, metro="4/4", battito=1),)


def _cue(name: str, start_s: float, number: int = 1, source: str = "dj") -> CuePoint:
    return CuePoint(
        name=name, type="cue", start_s=start_s, end_s=None, number=number, source=source
    )


def _track(
    tmp_path: Path,
    track_id: str,
    *,
    title: str = "",
    artist: str = "Artist",
    cues: tuple[CuePoint, ...] | None = None,
    beatgrid: tuple[TempoNode, ...] = BEATGRID,
    duration_s: float = 300.0,
    file_exists: bool = True,
    rating: int = 0,
) -> TrackEntry:
    """A gig-ready track unless a flaw is asked for: real file on disk, one
    labeled hot cue early + one late (the mix-out anchor), a beatgrid."""
    audio = tmp_path / f"{track_id}.mp3"
    if file_exists:
        audio.write_bytes(b"\x00")
    if cues is None:
        cues = (_cue("intro", 8.0, 1), _cue("outro", duration_s * 0.9, 2))
    return TrackEntry(
        track_id=track_id,
        title=title or f"Track {track_id}",
        artist=artist,
        album="",
        bpm=126.0,
        key="Am",
        duration_s=duration_s,
        cues=cues,
        filepath=str(audio),
        rating=rating,
        beatgrid=beatgrid,
    )


# --- pure audit: track readiness ------------------------------------------ #


def test_clean_library_takes_it(tmp_path):
    tracks = {str(i): _track(tmp_path, str(i)) for i in range(4)}
    report = audit_library(tracks)
    assert report["verdict"] == "take_it"
    assert report["totals"] == {"tracks": 4, "ready": 4, "warn": 0, "blocked": 0}
    assert report["blockers"] == []
    assert report["schema"].startswith("vibemix.gig-check.")


def test_missing_file_blocks_track(tmp_path):
    # 1 of 4 blocked (25%) sits under the 30% do-not-take flip: fixable.
    tracks = {str(i): _track(tmp_path, str(i)) for i in range(1, 4)}
    tracks["4"] = _track(tmp_path, "4", file_exists=False)
    report = audit_library(tracks)
    assert report["totals"]["blocked"] == 1
    assert [m["track_id"] for m in report["missing_files"]] == ["4"]
    assert report["verdict"] == "fix_first"


def test_track_without_dj_hot_cues_is_blocked(tmp_path):
    # auto/anlz-materialized cues are suggestions, not the DJ's own prep —
    # they must not silence the "you are naked on this track" signal.
    auto_only = (_cue("drop", 60.0, 1, source="anlz"),)
    tracks = {"1": _track(tmp_path, "1", cues=auto_only)}
    report = audit_library(tracks)
    assert report["totals"]["blocked"] == 1
    debt = {d["track_id"]: d for d in report["cue_debt"]}
    assert "no_hot_cues" in debt["1"]["issues"]


def test_unlabeled_cues_warn(tmp_path):
    cues = (_cue("", 8.0, 1), _cue("", 270.0, 2))
    tracks = {"1": _track(tmp_path, "1", cues=cues)}
    report = audit_library(tracks)
    assert report["totals"]["warn"] == 1
    debt = {d["track_id"]: d for d in report["cue_debt"]}
    assert "unlabeled_cues" in debt["1"]["issues"]


def test_no_mix_out_anchor_warns(tmp_path):
    # all cues land in the first half — nothing anchors the exit.
    cues = (_cue("intro", 8.0, 1), _cue("drop", 60.0, 2))
    tracks = {"1": _track(tmp_path, "1", cues=cues, duration_s=300.0)}
    report = audit_library(tracks)
    debt = {d["track_id"]: d for d in report["cue_debt"]}
    assert "no_mix_out_anchor" in debt["1"]["issues"]
    assert report["totals"]["warn"] == 1


def test_zero_duration_skips_mix_out_check(tmp_path):
    cues = (_cue("intro", 8.0, 1),)
    tracks = {"1": _track(tmp_path, "1", cues=cues, duration_s=0.0)}
    report = audit_library(tracks)
    debt = {d["track_id"]: d for d in report["cue_debt"]}
    assert "no_mix_out_anchor" not in debt.get("1", {}).get("issues", ())


def test_missing_beatgrid_warns(tmp_path):
    tracks = {"1": _track(tmp_path, "1", beatgrid=())}
    report = audit_library(tracks)
    debt = {d["track_id"]: d for d in report["cue_debt"]}
    assert "no_beatgrid" in debt["1"]["issues"]


# --- pure audit: library-level checks ------------------------------------- #


def test_duplicates_grouped(tmp_path):
    tracks = {
        "1": _track(tmp_path, "1", title="Strobe", artist="deadmau5"),
        "2": _track(tmp_path, "2", title="  strobe ", artist="Deadmau5"),
        "3": _track(tmp_path, "3", title="Other", artist="X"),
    }
    report = audit_library(tracks)
    assert len(report["duplicates"]) == 1
    ids = sorted(t["track_id"] for t in report["duplicates"][0])
    assert ids == ["1", "2"]


def test_crate_bloat_flagged(tmp_path):
    tracks = {str(i): _track(tmp_path, str(i)) for i in range(3)}
    fat = PlaylistRef(name="Peak Time", track_ids=tuple(str(i) for i in range(150)))
    lean = PlaylistRef(name="Warmup", track_ids=("1", "2"))
    report = audit_library(tracks, playlists=(fat, lean), bloat_threshold=80)
    assert len(report["crate_bloat"]) == 1
    assert report["crate_bloat"][0]["playlist"] == "Peak Time"
    assert report["crate_bloat"][0]["tracks"] == 150


# --- verdict ladder -------------------------------------------------------- #


def test_verdict_do_not_take_when_blocked_majority(tmp_path):
    tracks = {
        "1": _track(tmp_path, "1", file_exists=False),
        "2": _track(tmp_path, "2", file_exists=False),
        "3": _track(tmp_path, "3"),
    }
    report = audit_library(tracks)
    assert report["verdict"] == "do_not_take"
    assert report["blockers"]  # human-readable drivers, never empty on red


def test_empty_library_is_do_not_take():
    report = audit_library({})
    assert report["verdict"] == "do_not_take"


# --- tonight crate --------------------------------------------------------- #


def test_tonight_crate_is_ready_tracks_only_capped(tmp_path):
    tracks = {
        "1": _track(tmp_path, "1", rating=5),
        "2": _track(tmp_path, "2", rating=3),
        "3": _track(tmp_path, "3", file_exists=False),
    }
    report = audit_library(tracks, tonight_cap=1)
    assert len(report["tonight"]) == 1
    # ready tracks ranked by rating first — the 5-star leads.
    assert report["tonight"][0]["track_id"] == "1"
    assert all(t["track_id"] != "3" for t in report["tonight"])


# --- loader: XML → report -------------------------------------------------- #


def _write_collection_xml(tmp_path: Path) -> Path:
    present = tmp_path / "present.mp3"
    present.write_bytes(b"\x00")
    xml = tmp_path / "collection.xml"
    xml.write_text(
        "<?xml version='1.0' encoding='utf-8'?>\n"
        '<DJ_PLAYLISTS Version="1.0.0">\n'
        '  <PRODUCT Name="vibemix" Version="1.0.0" Company="vibemix-test" />\n'
        '  <COLLECTION Entries="2">\n'
        f'    <TRACK Location="file://localhost{present}" TrackID="1" Name="Ready One"'
        ' Artist="A" AverageBpm="126.0" Tonality="Am" TotalTime="300">\n'
        '      <TEMPO Inizio="0.05" Bpm="126.0" Metro="4/4" Battito="1" />\n'
        '      <POSITION_MARK Name="intro" Type="0" Start="8.0" Num="1" />\n'
        '      <POSITION_MARK Name="outro" Type="0" Start="280.0" Num="2" />\n'
        "    </TRACK>\n"
        f'    <TRACK Location="file://localhost{tmp_path}/gone.mp3" TrackID="2" Name="Gone"'
        ' Artist="B" AverageBpm="128.0" Tonality="Cm" TotalTime="300">\n'
        '      <POSITION_MARK Name="intro" Type="0" Start="8.0" Num="1" />\n'
        "    </TRACK>\n"
        "  </COLLECTION>\n"
        "  <PLAYLISTS>\n"
        '    <NODE Name="ROOT" Type="0" Count="1">\n'
        '      <NODE Name="Peak Time" Type="1" Entries="2">\n'
        '        <TRACK Key="1" />\n'
        '        <TRACK Key="2" />\n'
        "      </NODE>\n"
        "    </NODE>\n"
        "  </PLAYLISTS>\n"
        "</DJ_PLAYLISTS>\n"
    )
    return xml


def test_run_gig_check_from_xml(tmp_path, monkeypatch):
    monkeypatch.setattr(RekordboxLibrary, "CACHE_PATH", tmp_path / "library.pkl")
    xml = _write_collection_xml(tmp_path)
    report = run_gig_check(xml)
    assert report["totals"]["tracks"] == 2
    assert [m["track_id"] for m in report["missing_files"]] == ["2"]
    # playlists came along for the ride (crate-bloat input wired end-to-end)
    assert report["params"]["playlists_seen"] == 1
    assert report["verdict"] in ("fix_first", "do_not_take")


def test_run_gig_check_missing_xml_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(RekordboxLibrary, "CACHE_PATH", tmp_path / "library.pkl")
    with pytest.raises(FileNotFoundError):
        run_gig_check(tmp_path / "nope.xml")


# --- human report ----------------------------------------------------------- #


# --- CLI: verdict → exit code ------------------------------------------------ #


def test_cli_exit_codes_follow_verdict(tmp_path, monkeypatch, capsys):
    import argparse

    import vibemix.__main__ as m

    monkeypatch.setattr(RekordboxLibrary, "CACHE_PATH", tmp_path / "library.pkl")
    xml = _write_collection_xml(tmp_path)
    args = argparse.Namespace(
        xml=str(xml), json=False, bloat_threshold=80, tonight_cap=40
    )
    # the loader fixture has 1 of 2 tracks broken → 50% blocked → do_not_take (2)
    assert m._cmd_library_gig_check(args) == 2
    out = capsys.readouterr().out
    assert "DO NOT TAKE" in out


def test_cli_json_output_is_machine_readable(tmp_path, monkeypatch, capsys):
    import argparse
    import json

    import vibemix.__main__ as m

    monkeypatch.setattr(RekordboxLibrary, "CACHE_PATH", tmp_path / "library.pkl")
    xml = _write_collection_xml(tmp_path)
    args = argparse.Namespace(
        xml=str(xml), json=True, bloat_threshold=80, tonight_cap=40
    )
    m._cmd_library_gig_check(args)
    payload = json.loads(capsys.readouterr().out)
    assert payload["schema"].startswith("vibemix.gig-check.")
    assert payload["verdict"] == "do_not_take"


def test_cli_missing_xml_exits_1(tmp_path, capsys):
    import argparse

    import vibemix.__main__ as m

    args = argparse.Namespace(
        xml=str(tmp_path / "nope.xml"), json=False, bloat_threshold=80, tonight_cap=40
    )
    assert m._cmd_library_gig_check(args) == 1
    assert "not found" in capsys.readouterr().err.lower()


def test_format_report_carries_verdict_and_counts(tmp_path):
    tracks = {str(i): _track(tmp_path, str(i)) for i in range(1, 4)}
    tracks["4"] = _track(tmp_path, "4", file_exists=False)
    text = format_report(audit_library(tracks))
    assert "FIX FIRST" in text
    assert "blocked 1" in text
    assert "Track 4" in text  # the broken track is named, not just counted
