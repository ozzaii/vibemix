# SPDX-License-Identifier: Apache-2.0
"""Tests for cue_export — CueAnchor → Rekordbox hot-cue XML round-trip.

No network, no pyrekordbox: a FakeXml builder is injected so the mapping +
grounding gate are exercised in pure Python. The real ``RekordboxXml`` path is
only taken when ``xml_builder is None`` (not covered here — it needs the dep).
"""

from __future__ import annotations

from typing import Any

import pytest

from vibemix.library.cue_export import (
    _LABEL_COLORS,
    _LABEL_TO_MARK_NAME,
    cue_anchor_to_mark_kwargs,
    export_cues,
)
from vibemix.library.cue_types import CueAnchor

# -- fakes ----------------------------------------------------------------- #


class FakeMark:
    """A PositionMark with mutable RGB (set after add_mark, as in 0.4.4)."""

    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs
        self.Red: int | None = None
        self.Green: int | None = None
        self.Blue: int | None = None


class FakeTrack:
    """Records each add_mark call; returns a FakeMark the caller colors."""

    def __init__(self) -> None:
        self.marks: list[FakeMark] = []

    def add_mark(self, **kwargs: Any) -> FakeMark:
        mark = FakeMark(**kwargs)
        self.marks.append(mark)
        return mark


class FakeTrackRaisesOnMark(FakeTrack):
    def add_mark(self, **kwargs: Any) -> FakeMark:
        raise RuntimeError("boom in add_mark")


class FakeXml:
    """Records add_track + save; returns a FakeTrack."""

    def __init__(self, track: FakeTrack | None = None) -> None:
        self.track = track or FakeTrack()
        self.add_track_location: str | None = None
        self.add_track_kwargs: dict[str, Any] | None = None
        self.saved_path: str | None = None

    def add_track(self, location: str, **kwargs: Any) -> FakeTrack:
        # location is POSITIONAL in pyrekordbox's real add_track — mirror it.
        self.add_track_location = location
        self.add_track_kwargs = kwargs
        return self.track

    def save(self, path: str) -> None:
        self.saved_path = path


def _cue(label: str, start: float, end: float = 0.0) -> CueAnchor:
    return CueAnchor(
        label=label, start_s=start, end_s=end, confidence=0.9, source="auto"
    )


# -- cue_anchor_to_mark_kwargs (pure mapping) ------------------------------ #


def test_mark_kwargs_pure_mapping() -> None:
    kwargs = cue_anchor_to_mark_kwargs(_cue("drop", 64.0, 80.0), num=2)
    assert kwargs == {
        "Name": "VM DROP",
        "Type": "cue",
        "Start": 64.0,
        "End": None,  # point hot cue, not a loop region
        "Num": 2,
    }


def test_mark_kwargs_each_label_name() -> None:
    for label, expected in _LABEL_TO_MARK_NAME.items():
        kwargs = cue_anchor_to_mark_kwargs(_cue(label, 1.0), num=0)
        assert kwargs["Name"] == f"VM {expected}"
        assert kwargs["Type"] == "cue"
        assert kwargs["End"] is None


# -- export_cues ----------------------------------------------------------- #


def test_export_maps_each_label_to_name_and_color(tmp_path) -> None:
    cues = [
        _cue("intro", 0.0),
        _cue("build", 30.0),
        _cue("breakdown", 60.0),
        _cue("drop", 90.0),
        _cue("outro", 120.0),
    ]
    fake = FakeXml()
    out = str(tmp_path / "cues.xml")

    res = export_cues("/music/song.aiff", cues, out, xml_builder=fake)

    assert res["exported"] is True
    assert res["cue_count"] == 5
    assert len(fake.track.marks) == 5
    for mark, cue in zip(fake.track.marks, cues, strict=True):
        assert mark.kwargs["Name"] == f"VM {_LABEL_TO_MARK_NAME[cue.label]}"
        r, g, b = _LABEL_COLORS[cue.label]
        assert (mark.Red, mark.Green, mark.Blue) == (r, g, b)


def test_export_num_increments_in_start_order(tmp_path) -> None:
    # Deliberately out of timeline order; export must sort by start_s.
    cues = [_cue("drop", 90.0), _cue("intro", 0.0), _cue("build", 30.0)]
    fake = FakeXml()
    out = str(tmp_path / "cues.xml")

    export_cues("/music/song.aiff", cues, out, xml_builder=fake)

    nums = [m.kwargs["Num"] for m in fake.track.marks]
    names = [m.kwargs["Name"] for m in fake.track.marks]
    assert nums == [0, 1, 2]
    assert names == ["VM INTRO", "VM BUILD", "VM DROP"]  # sorted by start


def test_export_records_add_track_marks_and_save(tmp_path) -> None:
    cues = [_cue("intro", 0.0), _cue("drop", 64.0)]
    fake = FakeXml()
    out = str(tmp_path / "out.xml")

    res = export_cues(
        "/music/track.wav",
        cues,
        out,
        title="Night Drive",
        artist="DJ Test",
        bpm=128.0,
        xml_builder=fake,
    )

    assert res == {
        "exported": True,
        "path": out,
        "cue_count": 2,
        "track_path": "/music/track.wav",
    }
    assert fake.add_track_location == "/music/track.wav"
    assert fake.add_track_kwargs == {
        "Name": "Night Drive",
        "Artist": "DJ Test",
        "AverageBpm": 128.0,
    }
    assert len(fake.track.marks) == 2
    assert fake.saved_path == out


def test_export_omits_absent_metadata(tmp_path) -> None:
    fake = FakeXml()
    export_cues(
        "/m/a.wav", [_cue("intro", 0.0)], str(tmp_path / "o.xml"), xml_builder=fake
    )
    # location is positional; no metadata kwargs when title/artist/bpm are None.
    assert fake.add_track_location == "/m/a.wav"
    assert fake.add_track_kwargs == {}


def test_export_empty_cues_errors(tmp_path) -> None:
    res = export_cues("/m/a.wav", [], str(tmp_path / "o.xml"), xml_builder=FakeXml())
    assert res == {"error": "no cues to export"}


def test_export_builder_raise_returns_error_no_exception(tmp_path) -> None:
    fake = FakeXml(track=FakeTrackRaisesOnMark())
    res = export_cues(
        "/m/a.wav", [_cue("drop", 10.0)], str(tmp_path / "o.xml"), xml_builder=fake
    )
    assert "error" in res
    assert res["error"].startswith("export_cues failed: RuntimeError")


def test_export_add_track_raise_returns_error(tmp_path) -> None:
    class Boom:
        def add_track(self, location: str, **kwargs: Any) -> Any:
            raise ValueError("nope")

    res = export_cues(
        "/m/a.wav", [_cue("drop", 10.0)], str(tmp_path / "o.xml"), xml_builder=Boom()
    )
    assert res == {"error": "export_cues failed: ValueError"}


def test_export_against_real_pyrekordbox(tmp_path) -> None:
    """Contract lock against the REAL pyrekordbox.rbxml.RekordboxXml.

    The fake builder can't catch an add_track/add_mark signature drift (a fake
    that mirrors the wrong shape passes while the real lib raises) — so exercise
    the real default path: no xml_builder, then reload the written XML and
    assert the cues survive. Skips cleanly when pyrekordbox isn't installed.
    """
    pytest.importorskip("pyrekordbox")
    from pyrekordbox.rbxml import RekordboxXml

    cues = [
        _cue("intro", 0.0, 16.0),
        _cue("build", 64.0, 96.0),
        _cue("drop", 96.0, 128.0),
    ]
    out = str(tmp_path / "real.xml")
    res = export_cues(
        "/music/real track.aiff", cues, out,
        title="Real", artist="DJ", bpm=128.0,
    )
    assert res["exported"] is True and res["cue_count"] == 3
    # Reload the written tree: valid XML + the 3 hot cues persisted.
    reloaded = RekordboxXml(out)
    tracks = list(reloaded.get_tracks())
    assert len(tracks) == 1
    marks = tracks[0].marks
    assert len(marks) == 3
    assert [m.Name for m in marks] == ["VM INTRO", "VM BUILD", "VM DROP"]
