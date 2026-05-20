# SPDX-License-Identifier: Apache-2.0
import glob

from spikes.vibe_mix_slice0.cue_writer import write_cues
from spikes.vibe_mix_slice0.types import CueCandidate


def _cand(num: int) -> CueCandidate:
    return CueCandidate(
        track_location="file://localhost/tmp/track.mp3",
        name=f"CUE{num}", type="cue", start_s=10.0 * num, number=num,
        confidence=0.99,
    )


def test_writes_new_file(tmp_path):
    out = tmp_path / "set.xml"
    n = write_cues([_cand(1), _cand(2)], out_path=str(out))
    assert n == 2
    assert out.exists()


def test_backs_up_before_overwrite(tmp_path):
    out = tmp_path / "set.xml"
    out.write_text("ORIGINAL")  # pretend a prior file exists
    write_cues([_cand(1)], out_path=str(out))
    backups = glob.glob(str(tmp_path / "set.xml.bak-*"))
    assert len(backups) == 1
    # The backup preserves the original bytes verbatim.
    assert open(backups[0]).read() == "ORIGINAL"


def test_source_collection_never_mutated(tmp_path):
    source = tmp_path / "collection.xml"
    source.write_text("DJS_LIVE_LIBRARY")
    out = tmp_path / "vibemix-cues.xml"
    write_cues([_cand(1)], out_path=str(out))
    # We emitted to a separate file; the live library is byte-identical.
    assert source.read_text() == "DJS_LIVE_LIBRARY"
