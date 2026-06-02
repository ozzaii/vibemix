# SPDX-License-Identifier: Apache-2.0
"""L3 Mastered marker writer safety tests."""

from __future__ import annotations

from pathlib import Path

from vibemix.learn import mastered_marker_writer as writer
from vibemix.library.export_serato import SeratoCue


def test_mastered_marker_requires_in_track_position(tmp_path: Path) -> None:
    track = tmp_path / "track.mp3"
    track.write_bytes(b"fake")

    result = writer.write_mastered_marker(
        skill_id="harmonic_mixing",
        track_path=track,
        position_s=None,
        allow_write=True,
    )

    assert result.written is False
    assert result.reason == "missing_in_track_position"


def test_mastered_marker_requires_explicit_write_opt_in(tmp_path: Path) -> None:
    track = tmp_path / "track.mp3"
    track.write_bytes(b"fake")

    result = writer.write_mastered_marker(
        skill_id="harmonic_mixing",
        track_path=track,
        position_s=64.25,
    )

    assert result.written is False
    assert result.reason == "opt_in_required"
    assert result.position_ms == 64250


def test_mastered_marker_uses_first_free_hot_cue_slot(
    tmp_path: Path, monkeypatch
) -> None:
    track = tmp_path / "track.mp3"
    track.write_bytes(b"fake")
    writes: list[tuple[Path, list[SeratoCue], bool, bool]] = []

    monkeypatch.setattr(
        writer,
        "read_serato_cues",
        lambda path: [SeratoCue(0, 1000, (1, 2, 3), "DJ cue")],
    )

    def _write(path, cues, *, allow_write, merge):
        writes.append((Path(path), list(cues), allow_write, merge))
        return {"written": True, "cue_count": 2, "path": str(path)}

    monkeypatch.setattr(writer, "write_serato_cues", _write)

    result = writer.write_mastered_marker(
        skill_id="harmonic_mixing",
        track_path=track,
        position_s=64.25,
        allow_write=True,
    )

    assert result.written is True
    assert result.index == 1
    assert result.position_ms == 64250
    assert result.name == "Mastered: harmonic mixing"
    assert len(writes) == 1
    path, cues, allow_write, merge = writes[0]
    assert path == track
    assert allow_write is True
    assert merge is True
    assert cues == [SeratoCue(1, 64250, (40, 226, 20), "Mastered: harmonic mixing")]


def test_mastered_marker_does_not_duplicate_existing_marker(
    tmp_path: Path, monkeypatch
) -> None:
    track = tmp_path / "track.mp3"
    track.write_bytes(b"fake")
    monkeypatch.setattr(
        writer,
        "read_serato_cues",
        lambda path: [SeratoCue(3, 64000, (40, 226, 20), "Mastered: transitions")],
    )
    monkeypatch.setattr(
        writer,
        "write_serato_cues",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("must not write")),
    )

    result = writer.write_mastered_marker(
        skill_id="transitions",
        track_path=track,
        position_s=65.0,
        allow_write=True,
    )

    assert result.written is False
    assert result.reason == "already_present"
    assert result.index == 3
    assert result.position_ms == 64000


def test_mastered_marker_abstains_when_all_hot_cue_slots_are_used(
    tmp_path: Path, monkeypatch
) -> None:
    track = tmp_path / "track.mp3"
    track.write_bytes(b"fake")
    monkeypatch.setattr(
        writer,
        "read_serato_cues",
        lambda path: [SeratoCue(i, i * 1000, (1, 2, 3), f"cue {i}") for i in range(8)],
    )
    monkeypatch.setattr(
        writer,
        "write_serato_cues",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("must not write")),
    )

    result = writer.write_mastered_marker(
        skill_id="eq_mixing",
        track_path=track,
        position_s=12.0,
        allow_write=True,
    )

    assert result.written is False
    assert result.reason == "no_free_hot_cue_slot"


def test_mastered_marker_never_raises_on_export_error(
    tmp_path: Path, monkeypatch
) -> None:
    track = tmp_path / "track.mp3"
    track.write_bytes(b"fake")

    def _boom(path):
        raise RuntimeError("bad tag")

    monkeypatch.setattr(writer, "read_serato_cues", _boom)

    result = writer.write_mastered_marker(
        skill_id="eq_mixing",
        track_path=track,
        position_s=12.0,
        allow_write=True,
    )

    assert result.written is False
    assert result.reason == "write_error:RuntimeError"
