# SPDX-License-Identifier: Apache-2.0
"""L3 Mastered marker writer safety tests."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from vibemix.learn import mastered_marker_writer as writer
from vibemix.library.export_serato import SeratoCue
from vibemix.state.deck_state import DeckState, DeckTrack
from vibemix.state.music_state import MusicState


class _Library:
    def __init__(self, *entries):
        self._entries = {entry.track_id: entry for entry in entries}

    def lookup_by_id(self, track_id: str):
        return self._entries.get(track_id)


def _state(
    *,
    deck: str = "A",
    track_id: str = "track-1",
    deck_confidence: float = 0.95,
    position_s: float | None = 64.25,
    position_confidence: float = 0.85,
) -> MusicState:
    state = MusicState()
    state.audible_deck = deck
    state.audible_track_position_s = position_s
    state.audible_track_position_confidence = position_confidence
    state.deck_state = DeckState(
        decks={
            deck: DeckTrack(
                title="Live Track",
                track_id=track_id,
                confidence=deck_confidence,
                source="rekordbox_xml",
            )
        }
    )
    return state


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


def test_mastered_marker_request_resolves_current_track_path_and_position(tmp_path: Path) -> None:
    track = tmp_path / "Live Track.mp3"
    library = _Library(
        SimpleNamespace(track_id="track-1", filepath=f"file://localhost{track.as_posix()}")
    )

    request = writer.resolve_mastered_marker_request(
        skill_id="harmonic_mixing",
        state=_state(),
        library=library,
    )

    assert request.ok is True
    assert request.reason == "ready"
    assert request.deck == "A"
    assert request.track_id == "track-1"
    assert request.track_path == str(track)
    assert request.position_s == 64.25


def test_mastered_marker_request_refuses_mixed_deck_and_set_time() -> None:
    state = _state(deck="mix")
    library = _Library(SimpleNamespace(track_id="track-1", filepath="/music/track.mp3"))

    request = writer.resolve_mastered_marker_request(
        skill_id="harmonic_mixing",
        state=state,
        library=library,
    )

    assert request.ok is False
    assert request.reason == "missing_audible_deck"


def test_mastered_marker_request_refuses_untrusted_position(tmp_path: Path) -> None:
    track = tmp_path / "Live Track.mp3"
    library = _Library(SimpleNamespace(track_id="track-1", filepath=str(track)))

    request = writer.resolve_mastered_marker_request(
        skill_id="harmonic_mixing",
        state=_state(position_s=64.25, position_confidence=0.2),
        library=library,
    )

    assert request.ok is False
    assert request.reason == "position_untrusted"
    assert request.position_s == 64.25


def test_mastered_marker_from_state_preserves_opt_in_write_gate(
    tmp_path: Path, monkeypatch
) -> None:
    track = tmp_path / "Live Track.mp3"
    track.write_bytes(b"fake")
    library = _Library(SimpleNamespace(track_id="track-1", filepath=str(track)))
    monkeypatch.setattr(writer, "read_serato_cues", lambda path: [])
    monkeypatch.setattr(
        writer,
        "write_serato_cues",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("must not write")),
    )

    result = writer.write_mastered_marker_from_state(
        skill_id="harmonic_mixing",
        state=_state(),
        library=library,
        allow_write=False,
    )

    assert result.written is False
    assert result.reason == "opt_in_required"
    assert result.position_ms == 64250
