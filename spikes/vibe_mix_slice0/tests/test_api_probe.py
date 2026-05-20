# SPDX-License-Identifier: Apache-2.0
"""Empirical confirmation of the pyrekordbox RekordboxXml write API.

The spike's empirical anchor: pins the exact working write call in the
installed pyrekordbox 0.4.4. Confirmed casing: add_track(location=...),
add_mark(Name=, Type=, Start=, Num=), save(path=), track.marks.
"""
from pyrekordbox import RekordboxXml


def test_rekordboxxml_write_roundtrip_minimal(tmp_path):
    """A new XML with one track + one hot cue saves and re-parses."""
    xml = RekordboxXml()
    track = xml.add_track(location="file://localhost/tmp/demo.mp3")
    track.add_mark(Name="A", Type="cue", Start=12.5, Num=1)

    out = tmp_path / "out.xml"
    xml.save(path=str(out))

    assert out.exists() and out.stat().st_size > 0
    # Re-parse with a fresh reader to prove the mark persisted.
    reparsed = RekordboxXml(str(out))
    tracks = list(reparsed.get_tracks())
    assert len(tracks) == 1
    marks = list(tracks[0].marks)
    assert len(marks) == 1
    assert marks[0].Name == "A"
    assert abs(float(marks[0].Start) - 12.5) < 1e-6
    assert int(marks[0].Num) == 1
