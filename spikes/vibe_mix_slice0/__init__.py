# SPDX-License-Identifier: Apache-2.0
"""Vibe Mix Slice 0 — Rekordbox cue write-back de-risk spike.

OUT of the src/vibemix grep gate (see spikes/__init__.py). The unknown under
test is WRITE-BACK SAFETY, not cue detection. Direct master.db writes are
deliberately excluded (no stable/safe write API — GitHub discussion #113); the
safe path is a collection.xml round-trip the DJ imports into Rekordbox.

Confirmed pyrekordbox 0.4.4 write API (Task 1 probe):
    track = xml.add_track(location="file://localhost/...")   # lowercase positional
    track.add_mark(Name="DROP", Type="cue", Start=64.0, Num=3)  # capitalized kwargs
    xml.save(path="out.xml")
    # read-back: track.marks (attribute), mark.Name / mark.Start / mark.Num
"""
