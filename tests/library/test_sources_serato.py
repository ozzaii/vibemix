# SPDX-License-Identifier: Apache-2.0
"""SeratoSource contract tests.

These stay source-level and offline: no Serato runtime, no audio decode, no
CLAP. A synthetic ``_Serato_`` folder with tagged chunks enters the existing
LibrarySource / TrackEntry / CuePoint shape.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from vibemix.library.export_serato import SeratoCue
from vibemix.library.rekordbox import TrackEntry
from vibemix.library.sources.base import LibrarySource
from vibemix.state.harmonics import to_camelot


def _chunk(tag: str, body: bytes | str) -> bytes:
    payload = body.encode("utf-8") if isinstance(body, str) else body
    return tag.encode("ascii") + len(payload).to_bytes(4, "big") + payload


def _track_chunk(
    *,
    path: Path,
    title: str,
    artist: str,
    bpm: str = "148.0",
    key: str = "8A",
) -> bytes:
    return _chunk(
        "otrk",
        b"".join(
            (
                _chunk("pfil", str(path)),
                _chunk("tsng", title),
                _chunk("tart", artist),
                _chunk("talb", "Album X"),
                _chunk("tbpm", bpm),
                _chunk("tkey", key),
                _chunk("tlen", "421500"),
                _chunk("tgen", "Psytrance"),
                _chunk("tlbl", "Label Y"),
                _chunk("trat", "4"),
                _chunk("tply", "7"),
                _chunk("tcmt", "energy note"),
            )
        ),
    )


def _write_serato_library(tmp_path: Path) -> tuple[Path, Path, Path]:
    root = tmp_path / "Music" / "_Serato_"
    root.mkdir(parents=True)
    audio_dir = tmp_path / "Music" / "PSY"
    audio_dir.mkdir()
    first_audio = audio_dir / "Track One.mp3"
    second_audio = audio_dir / "Bare.wav"
    first_audio.write_bytes(b"audio")
    second_audio.write_bytes(b"audio")

    database = root / "database V2"
    database.write_bytes(
        b"header that should be skipped"
        + _track_chunk(path=first_audio, title="Track One", artist="Artist A")
        + _track_chunk(path=second_audio, title="", artist="Artist B", bpm="120", key="Am")
        + b"BROK\x00\x00\xff\xff"  # malformed trailing chunk: skipped, never fatal
    )

    subcrates = root / "Subcrates"
    subcrates.mkdir()
    (subcrates / "Psy.crate").write_bytes(
        _chunk("otrk", _chunk("ptrk", str(first_audio)))
        + _chunk("otrk", _chunk("ptrk", str(second_audio)))
    )
    return root, first_audio, second_audio


def test_serato_source_import_pulls_no_heavy_dep():
    code = (
        "import sys; import vibemix.library.sources.serato; "
        "assert 'torch' not in sys.modules, 'torch leaked'; "
        "assert 'laion_clap' not in sys.modules, 'laion_clap leaked'; "
        "assert 'mutagen' not in sys.modules, 'mutagen leaked'"
    )
    repo_src = str(Path(__file__).resolve().parents[2] / "src")
    env = {**dict(os.environ), "PYTHONPATH": repo_src}
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, env=env
    )
    assert result.returncode == 0, result.stderr


def test_serato_source_detect_explicit_folder(tmp_path):
    from vibemix.library.sources.serato import SeratoSource

    root, _, _ = _write_serato_library(tmp_path)
    source = SeratoSource(library_path=str(root))

    assert source.name == "serato"
    assert source.detect() is True
    assert Path(source.resolved_path or "") == root / "database V2"
    assert isinstance(source, LibrarySource)


def test_serato_source_detect_explicit_database_file(tmp_path):
    from vibemix.library.sources.serato import SeratoSource

    root, _, _ = _write_serato_library(tmp_path)
    source = SeratoSource(library_path=str(root / "database V2"))

    assert source.detect() is True
    assert Path(source.resolved_path or "") == root / "database V2"


def test_serato_source_detect_missing_returns_false(tmp_path):
    from vibemix.library.sources.serato import SeratoSource

    source = SeratoSource(library_path=str(tmp_path / "_Serato_"))

    assert source.detect() is False


def test_serato_source_iter_tracks_maps_metadata_crate_order_and_cues(
    tmp_path, monkeypatch
):
    import vibemix.library.sources.serato as serato_mod
    from vibemix.library.sources.serato import SeratoSource

    root, first_audio, _ = _write_serato_library(tmp_path)

    def _fake_cues(path: str):
        if Path(path) == first_audio:
            return [SeratoCue(index=0, position_ms=16000, color=(0xCC, 0, 0), name="Intro")]
        return []

    monkeypatch.setattr(serato_mod, "read_serato_cues", _fake_cues)

    entries = list(SeratoSource(library_path=str(root)).iter_tracks())

    assert len(entries) == 2
    assert all(isinstance(entry, TrackEntry) for entry in entries)

    first = entries[0]
    assert first.track_id.startswith("serato:")
    assert first.title == "Track One"
    assert first.artist == "Artist A"
    assert first.album == "Album X"
    assert first.genre == "Psytrance"
    assert first.label == "Label Y"
    assert first.comments == "energy note"
    assert first.play_count == 7
    assert first.rating == 4
    assert first.bpm == 148.0
    assert first.key == "8A"
    assert first.camelot == to_camelot(first.key)
    assert first.duration_s == 421.5
    assert first.filepath == str(first_audio)

    assert len(first.cues) == 1
    assert first.cues[0].name == "Intro"
    assert first.cues[0].type == "cue"
    assert first.cues[0].start_s == 16.0
    assert first.cues[0].end_s is None
    assert first.cues[0].number == 1

    second = entries[1]
    assert second.track_id.startswith("serato:")
    assert second.title == "Bare"
    assert second.artist == "Artist B"
    assert second.bpm == 120.0
    assert second.key == "Am"
    assert second.camelot == "8A"
    assert second.cues == ()


def test_serato_source_missing_database_raises(tmp_path):
    from vibemix.library.sources.serato import SeratoSource

    source = SeratoSource(library_path=str(tmp_path / "_Serato_"))

    with pytest.raises(FileNotFoundError, match=r"database V2"):
        list(source.iter_tracks())
