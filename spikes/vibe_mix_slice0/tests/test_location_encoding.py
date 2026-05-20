# SPDX-License-Identifier: Apache-2.0
"""The written Location must match Rekordbox's canonical URI form.

Regression guard for the pyrekordbox macOS double-slash quirk: a plain
absolute POSIX path must serialize to ``file://localhost/Users/...`` (single
slash), NOT ``file://localhost//Users/...`` — or Rekordbox import fails to
attach cues to the real file.
"""
import sys

import pytest

from spikes.vibe_mix_slice0.cue_writer import write_cues
from spikes.vibe_mix_slice0.types import CueCandidate


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX path-encoding quirk")
def test_location_is_canonical_single_slash(tmp_path):
    out = tmp_path / "cues.xml"
    write_cues(
        [CueCandidate("/Users/dj/Music/Demo Track 1.mp3", "DROP", "cue", 64.0, 1, 0.99)],
        out_path=str(out),
    )
    xml_text = out.read_text()
    assert 'Location="file://localhost/Users/dj/Music/Demo%20Track%201.mp3"' in xml_text
    # The bug we are guarding against:
    assert "file://localhost//Users" not in xml_text
