# SPDX-License-Identifier: Apache-2.0
"""Tests for the Serato Markers2 cue-tag writer - the portable cue carrier.

The binary payload is reimplemented from the documented format
(github.com/Holzhaus/serato-tags), not copied from any GPL parser. Green tests
prove byte/round-trip conformance; app-specific pad rendering is a manual
eye-check.

The pure encoder/decoder is asserted against EXACT spec bytes (a golden oracle
hand-derived from the documented CUE entry layout) + a round-trip - never
encode->decode self-symmetry alone. The 'a real Mixxx/Serato actually renders the
pad' claim is a separate one-time human eye-check (no-slop gate).

CUE entry layout (Serato Markers2 spec):
    offset 0  : 1 byte   0x00 (unknown)
    offset 1  : 1 byte   hotcue index
    offset 2  : 4 bytes  position ms, uint32 BIG-endian
    offset 6  : 1 byte   0x00 (unknown)
    offset 7  : 3 bytes  RGB color
    offset 10 : 2 bytes  0x00 0x00 (unknown)
    offset 12 : N bytes  UTF-8 name, null-terminated
wrapped as:  b"CUE\\x00" + uint32_BE(len(body)) + body
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from vibemix.library.export_serato import (
    SeratoCue,
    _cue_entry,
    _decode_inner,
    _inner_blob,
    _merge_cues,
    decode_markers2,
    encode_markers2,
    marks_to_serato_cues,
    read_serato_cues,
    write_serato_cues,
)

_REAL_MP3 = (
    Path(__file__).resolve().parents[1] / "bench" / "data" / "t1_pyrez_darkside.mp3"
)
_MARKS = [
    {"type": "cue", "start_s": 5.0, "num": 0, "name": "INTRO"},
    {"type": "cue", "start_s": 64.0, "num": 1, "name": "DROP"},
]


def test_cue_entry_matches_exact_spec_bytes() -> None:
    """The golden oracle: a known cue encodes to the exact documented bytes."""
    cue = SeratoCue(index=0, position_ms=5000, color=(0xCC, 0x00, 0x00), name="INTRO")
    body = (
        b"\x00"                       # unknown 0
        + b"\x00"                     # index 0
        + (5000).to_bytes(4, "big")  # position ms, BE  -> 00 00 13 88
        + b"\x00"                     # unknown 0
        + bytes((0xCC, 0x00, 0x00))  # RGB
        + b"\x00\x00"                 # unknown
        + b"INTRO\x00"               # null-terminated name
    )
    assert _cue_entry(cue) == b"CUE\x00" + len(body).to_bytes(4, "big") + body
    assert body[2:6] == b"\x00\x00\x13\x88"  # 5000 ms, big-endian


def test_inner_blob_has_header_and_terminator() -> None:
    blob = _inner_blob([SeratoCue(0, 5000, (0xCC, 0, 0), "INTRO")])
    assert blob[:2] == b"\x01\x01"   # decoded-content header
    assert blob.endswith(b"\x00")    # single null terminator
    assert b"CUE\x00" in blob


def test_encode_markers2_outer_container_header() -> None:
    data = encode_markers2([SeratoCue(0, 5000, (0xCC, 0, 0), "INTRO")])
    assert data[:2] == b"\x01\x01"           # outer tag header
    assert _decode_inner(data)[:2] == b"\x01\x01"  # round-trips through base64


def test_decode_inner_accepts_unpadded_base64_payload() -> None:
    data = encode_markers2([SeratoCue(0, 5000, (0xCC, 0, 0), "INTRO")])
    compact = data[:2] + data[2:].rstrip(b"\x00=").replace(b"\n", b"") + b"\x00"
    assert decode_markers2(compact)[0].name == "INTRO"


def test_round_trip_preserves_cue_fields() -> None:
    cues = [
        SeratoCue(0, 5000, (0xCC, 0x00, 0x00), "INTRO"),
        SeratoCue(1, 64000, (0xE6, 0x28, 0x28), "DROP"),
        SeratoCue(2, 123456, (0x10, 0x68, 0xE9), "BREAKDOWN"),
    ]
    assert decode_markers2(encode_markers2(cues)) == cues


def test_position_round_trips_in_milliseconds() -> None:
    out = decode_markers2(encode_markers2([SeratoCue(3, 123456, (1, 2, 3), "X")]))
    assert out[0].position_ms == 123456


def test_decode_ignores_non_cue_entries() -> None:
    """A payload with COLOR + BPMLOCK + CUE yields only the CUE."""
    import base64

    color = b"COLOR\x00" + (4).to_bytes(4, "big") + b"\x00\x99\xff\x99"
    bpmlock = b"BPMLOCK\x00" + (1).to_bytes(4, "big") + b"\x01"
    cue = _cue_entry(SeratoCue(0, 1000, (0xCC, 0, 0), "A"))
    inner = b"\x01\x01" + color + bpmlock + cue + b"\x00"
    b64 = base64.b64encode(inner)
    data = b"\x01\x01" + b64 + b"\x00"

    out = decode_markers2(data)
    assert len(out) == 1
    assert out[0].name == "A"
    assert out[0].position_ms == 1000


def test_marks_to_serato_cues_maps_index_ms_name_and_color() -> None:
    """cue_folder marks -> SeratoCue: index, ms (start_s*1000), name, label color."""
    cues = marks_to_serato_cues(_MARKS)
    assert [c.index for c in cues] == [0, 1]
    assert [c.position_ms for c in cues] == [5000, 64000]
    assert [c.name for c in cues] == ["INTRO", "DROP"]
    assert cues[0].color == (40, 226, 20)   # intro = green
    assert cues[1].color == (230, 40, 40)   # drop = red


def test_marks_to_serato_cues_stamps_machine_sources_and_rejects_dj_spoof() -> None:
    marks = [
        {"start_s": 5.0, "num": 0, "name": "INTRO", "source": "auto"},
        {"start_s": 64.0, "num": 1, "name": "DROP", "source": "dj"},
        {"start_s": 80.0, "num": 2, "name": "VM SPOOF", "source": "dj"},
    ]

    cues = marks_to_serato_cues(marks)

    assert [c.name for c in cues] == ["VM INTRO", "DROP"]
    assert cues[0].color == (40, 226, 20)
    assert cues[1].color == (230, 40, 40)


def test_merge_cues_preserves_foreign_index_and_overrides_same() -> None:
    """A DJ's hand-set cue at a pad vibemix doesn't write is preserved; a pad
    vibemix does write is overridden by vibemix's structural cue."""
    existing = [
        SeratoCue(5, 99000, (1, 2, 3), "MINE"),
        SeratoCue(0, 1000, (9, 9, 9), "OLD"),
    ]
    new = [SeratoCue(0, 5000, (40, 226, 20), "INTRO")]
    merged = {c.index: c for c in _merge_cues(existing, new)}
    assert merged[5].name == "MINE"    # foreign pad preserved
    assert merged[0].name == "INTRO"   # same pad overridden


def test_write_serato_cues_requires_opt_in(tmp_path: Path) -> None:
    """Tag-writing mutates the user's audio file, so it is opt-in: no allow_write
    -> no disk touch."""
    res = write_serato_cues(
        tmp_path / "x.mp3", marks_to_serato_cues(_MARKS), allow_write=False
    )
    assert res["written"] is False
    assert "opt-in" in res["reason"].lower()
    assert not (tmp_path / "x.mp3").exists()  # never created the file


@pytest.mark.skipif(not _REAL_MP3.exists(), reason="needs the in-repo test mp3")
def test_write_and_read_serato_cues_round_trip_real_mp3(tmp_path: Path) -> None:
    pytest.importorskip("mutagen")
    dst = tmp_path / "track.mp3"
    shutil.copy(_REAL_MP3, dst)
    res = write_serato_cues(dst, marks_to_serato_cues(_MARKS), allow_write=True)
    assert res["written"] is True
    assert res["cue_count"] == 2
    back = read_serato_cues(dst)
    assert [c.name for c in back] == ["INTRO", "DROP"]
    assert [c.position_ms for c in back] == [5000, 64000]
    assert [c.index for c in back] == [0, 1]


@pytest.mark.skipif(not _REAL_MP3.exists(), reason="needs the in-repo test mp3")
def test_write_serato_cues_merge_preserves_hand_set_cue(tmp_path: Path) -> None:
    pytest.importorskip("mutagen")
    dst = tmp_path / "track.mp3"
    shutil.copy(_REAL_MP3, dst)
    # A DJ's own cue at pad 5.
    write_serato_cues(dst, [SeratoCue(5, 99000, (1, 2, 3), "MINE")], allow_write=True, merge=False)
    # vibemix writes its structural cues with merge.
    write_serato_cues(dst, marks_to_serato_cues(_MARKS), allow_write=True, merge=True)
    back = {c.index: c.name for c in read_serato_cues(dst)}
    assert back[5] == "MINE"   # hand-set cue survived
    assert back[0] == "INTRO"
    assert back[1] == "DROP"
