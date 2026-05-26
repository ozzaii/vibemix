# SPDX-License-Identifier: Apache-2.0
"""Tests for quote_moment — grounded "quote-a-moment" references.

No network, no audio decoding. A tiny fake library exposes ``lookup_by_id``
returning real ``TrackEntry`` rows; the optional clip seam is exercised with a
fake writer (never a real decode).
"""

from __future__ import annotations

from vibemix.library.cue_types import CueAnchor
from vibemix.library.quote_moment import Quote, quote_from_cue, resolve_quote
from vibemix.library.rekordbox import TrackEntry


class FakeLibrary:
    """Minimal ``lookup_by_id`` stand-in over a dict of TrackEntry rows."""

    def __init__(self, tracks: dict[str, TrackEntry]) -> None:
        self._tracks = tracks

    def lookup_by_id(self, track_id: str) -> TrackEntry | None:
        return self._tracks.get(track_id)


def _entry(track_id: str, *, duration_s: float = 420.0) -> TrackEntry:
    return TrackEntry(
        track_id=track_id,
        title="Resonant Decay",
        artist="Vortex",
        album="",
        bpm=140.0,
        key="8A",
        duration_s=duration_s,
        cues=(),
        filepath="/music/vortex - resonant decay.flac",
    )


def _lib(*ids: str, duration_s: float = 420.0) -> FakeLibrary:
    return FakeLibrary({tid: _entry(tid, duration_s=duration_s) for tid in ids})


# --------------------------------------------------------------------------- #
# resolved quote                                                              #
# --------------------------------------------------------------------------- #


def test_resolve_quote_synthesizes_caption_with_mmss() -> None:
    out = resolve_quote(_lib("T1"), "T1", 192.0, 228.0, label="breakdown")
    assert out["available"] is True
    assert out["track_id"] == "T1"
    assert out["label"] == "breakdown"
    assert out["start_s"] == 192.0 and out["end_s"] == 228.0
    # "[breakdown @ 3:12-3:48] Vortex - Resonant Decay"
    assert out["caption"] == "[breakdown @ 3:12-3:48] Vortex - Resonant Decay"
    assert "clamped" not in out


def test_resolve_quote_uses_given_caption_verbatim() -> None:
    out = resolve_quote(
        _lib("T1"), "T1", 10.0, 20.0, caption="this is the bit I mean"
    )
    assert out["available"] is True
    assert out["caption"] == "this is the bit I mean"


def test_resolve_quote_no_label_drops_label_segment() -> None:
    out = resolve_quote(_lib("T1"), "T1", 0.0, 12.0)
    assert out["available"] is True
    assert out["caption"] == "[@ 0:00-0:12] Vortex - Resonant Decay"
    assert out["label"] is None


def test_quote_to_dict_round_trips() -> None:
    q = Quote(
        track_id="T1",
        title="t",
        artist="a",
        start_s=1.0,
        end_s=2.0,
        label="drop",
        caption="c",
        available=True,
    )
    d = q.to_dict()
    assert d == {
        "track_id": "T1",
        "title": "t",
        "artist": "a",
        "start_s": 1.0,
        "end_s": 2.0,
        "label": "drop",
        "caption": "c",
        "available": True,
    }


# --------------------------------------------------------------------------- #
# grounding gates                                                             #
# --------------------------------------------------------------------------- #


def test_unknown_track_id_is_unavailable() -> None:
    out = resolve_quote(_lib("T1"), "GHOST", 1.0, 2.0)
    assert out["available"] is False
    assert out["error"] == "unknown track_id"


def test_ungrounded_id_rejected_when_seen_provided() -> None:
    # seen given but the id is absent -> ungrounded, rejected before lookup.
    out = resolve_quote(_lib("T1"), "T1", 1.0, 2.0, seen={"OTHER"})
    assert out["available"] is False
    assert "ungrounded" in out["error"]


def test_grounded_id_in_seen_resolves() -> None:
    out = resolve_quote(_lib("T1"), "T1", 1.0, 2.0, seen={"T1", "OTHER"})
    assert out["available"] is True


def test_seen_none_skips_grounding_gate() -> None:
    # No per-run context (e.g. direct CLI) -> gate #1 skipped, still resolves.
    out = resolve_quote(_lib("T1"), "T1", 1.0, 2.0, seen=None)
    assert out["available"] is True


# --------------------------------------------------------------------------- #
# bounds validation                                                           #
# --------------------------------------------------------------------------- #


def test_start_after_end_is_error() -> None:
    out = resolve_quote(_lib("T1"), "T1", 30.0, 10.0)
    assert out["available"] is False
    assert "start_s must be < end_s" in out["error"]


def test_start_equals_end_is_error() -> None:
    out = resolve_quote(_lib("T1"), "T1", 10.0, 10.0)
    assert out["available"] is False
    assert "start_s must be < end_s" in out["error"]


def test_negative_start_is_error() -> None:
    out = resolve_quote(_lib("T1"), "T1", -5.0, 10.0)
    assert out["available"] is False
    assert "start_s must be >= 0" in out["error"]


def test_end_beyond_duration_is_clamped_and_noted() -> None:
    # duration 420s; ask for an end at 500s -> clamp to 420 and note it.
    out = resolve_quote(_lib("T1", duration_s=420.0), "T1", 400.0, 500.0)
    assert out["available"] is True
    assert out["end_s"] == 420.0
    assert out["clamped"] is True
    assert "clamped" in out["note"]
    assert "7:00" in out["note"]  # 420s -> 7:00


def test_end_within_slack_is_not_clamped() -> None:
    # 420.5s end on a 420s track is within the 1.0s slack -> untouched.
    out = resolve_quote(_lib("T1", duration_s=420.0), "T1", 10.0, 420.5)
    assert out["available"] is True
    assert out["end_s"] == 420.5
    assert "clamped" not in out


def test_start_past_duration_with_overrun_is_error() -> None:
    # start at/after duration AND end overruns -> cannot clamp into a valid
    # window, honest error rather than a zero/negative span.
    out = resolve_quote(_lib("T1", duration_s=420.0), "T1", 420.0, 500.0)
    assert out["available"] is False
    assert "duration" in out["error"]


# --------------------------------------------------------------------------- #
# quote_from_cue                                                              #
# --------------------------------------------------------------------------- #


def test_quote_from_cue_maps_anchor() -> None:
    cue = CueAnchor(
        label="breakdown",
        start_s=192.0,
        end_s=228.0,
        confidence=0.82,
        source="auto",
    )
    out = quote_from_cue(_lib("T1"), "T1", cue)
    assert out["available"] is True
    assert out["label"] == "breakdown"
    assert out["start_s"] == 192.0 and out["end_s"] == 228.0
    assert out["caption"] == "[breakdown @ 3:12-3:48] Vortex - Resonant Decay"


def test_quote_from_cue_honors_grounding() -> None:
    cue = CueAnchor(
        label="drop", start_s=10.0, end_s=40.0, confidence=0.9, source="dj"
    )
    out = quote_from_cue(_lib("T1"), "T1", cue, seen={"NOPE"})
    assert out["available"] is False
    assert "ungrounded" in out["error"]


# --------------------------------------------------------------------------- #
# injected clip seam (no real audio decode)                                   #
# --------------------------------------------------------------------------- #


def test_injected_clip_writer_is_called_and_clip_path_appears() -> None:
    calls: list[tuple[str, float, float]] = []

    def fake_writer(path: str, start_s: float, end_s: float) -> str:
        calls.append((path, start_s, end_s))
        return f"/tmp/clip-{int(start_s)}-{int(end_s)}.wav"

    out = resolve_quote(
        _lib("T1"), "T1", 192.0, 228.0, label="breakdown", clip_writer=fake_writer
    )
    assert out["available"] is True
    assert out["clip_path"] == "/tmp/clip-192-228.wav"
    assert calls == [("/music/vortex - resonant decay.flac", 192.0, 228.0)]


def test_no_clip_writer_means_no_clip_path() -> None:
    out = resolve_quote(_lib("T1"), "T1", 1.0, 2.0)
    assert "clip_path" not in out


def test_clip_writer_failure_degrades_without_raising() -> None:
    def boom(path: str, start_s: float, end_s: float) -> str:
        raise RuntimeError("decode blew up")

    out = resolve_quote(_lib("T1"), "T1", 1.0, 2.0, clip_writer=boom)
    # quote still resolves; clip failure is noted, not fatal.
    assert out["available"] is True
    assert "clip_path" not in out
    assert "clip_error" in out
