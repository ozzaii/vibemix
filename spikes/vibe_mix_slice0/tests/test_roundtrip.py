# SPDX-License-Identifier: Apache-2.0
"""Cues written by the spike survive a read-back through the SHIPPING reader."""
from vibemix.library.rekordbox import RekordboxLibrary

from spikes.vibe_mix_slice0.cue_writer import write_cues
from spikes.vibe_mix_slice0.types import CueCandidate


def test_written_cues_readback_through_production_reader(tmp_path, monkeypatch):
    out = tmp_path / "vibemix-cues.xml"
    cands = [
        CueCandidate("file://localhost/tmp/a.mp3", "INTRO", "cue", 0.0, 1, 0.99),
        CueCandidate("file://localhost/tmp/a.mp3", "DROP", "cue", 64.0, 3, 0.99),
    ]
    write_cues(cands, out_path=str(out))

    # Isolate the production reader's pickle cache to a tmp location.
    monkeypatch.setattr(
        RekordboxLibrary, "CACHE_PATH", tmp_path / "cache.pkl", raising=True
    )
    lib = RekordboxLibrary()
    n = lib.load_xml(str(out))
    assert n == 1

    (entry,) = lib.tracks.values()
    cues = {c.name: c for c in entry.cues}
    assert set(cues) == {"INTRO", "DROP"}
    assert cues["DROP"].start_s == 64.0
    assert cues["DROP"].number == 3
    assert cues["DROP"].type == "cue"
    assert cues["INTRO"].number == 1
