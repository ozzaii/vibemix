# SPDX-License-Identifier: Apache-2.0
"""Phase 89 Plan 89-03 Task 1 — excerpt.anchors_for_track + cut_windows.

The cue-anchored mapping layer: a TrackEntry's DJ-placed CuePoints become
``source="dj"`` CueAnchors (positions authoritative, labels best-effort); an
un-cued track falls back to ``detect_cues_auto`` (``source="auto"``); a track
with no structure at all yields ``[]`` honestly (the ingest caller then
whole-track falls back — never a faked anchor).

Honest-green posture (CLAUDE.md hard gate):
    * NO real DSP, NO ffmpeg, NO audio file, NO torch. ``detect_cues_auto`` is
      monkeypatched. Pure mapping over synthetic TrackEntry/CuePoint objects.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from vibemix.library.anlz_ingest import (
    AnlzBeatGrid,
    AnlzIndex,
    AnlzPhrase,
    AnlzTrackMeta,
)
from vibemix.library.cue_types import CueAnchor
from vibemix.library.rekordbox import CuePoint, TrackEntry

# --------------------------------------------------------------------------- #
# Synthetic builders                                                           #
# --------------------------------------------------------------------------- #


def _cue(
    *,
    type: str = "cue",
    start_s: float = 0.0,
    number: int = -1,
    end_s: float | None = None,
    name: str = "",
) -> CuePoint:
    return CuePoint(name=name, type=type, start_s=start_s, end_s=end_s, number=number)


def _track(cues: tuple[CuePoint, ...], *, duration_s: float = 300.0) -> TrackEntry:
    return TrackEntry(
        track_id="t1",
        title="Track 1",
        artist="Artist",
        album="Album",
        bpm=128.0,
        key="8A",
        duration_s=duration_s,
        cues=cues,
        filepath="/tmp/track1.mp3",
    )


def _anlz_index_for_track() -> AnlzIndex:
    phrase = AnlzPhrase(
        index=0,
        mood=1,
        kind=1,
        raw_label="Intro 1",
        cue_label="intro",
        start_beat=1,
        end_beat=65,
        start_s=0.0,
        end_s=32.0,
        confidence=0.84,
        flags={},
    )
    meta = AnlzTrackMeta(
        ext_path=Path("/fixture/ANLZ0000.EXT"),
        dat_path=Path("/fixture/ANLZ0000.DAT"),
        ppth_path="/tmp/track1.mp3",
        basename_key="track1.mp3",
        beatgrid=AnlzBeatGrid(times_s=(0.0,), bpms=(128.0,), beat_in_bar=(1,)),
        phrases=(phrase,),
    )
    return AnlzIndex(by_basename={"track1.mp3": (meta,)})


# --------------------------------------------------------------------------- #
# anchors_for_track — DJ-first                                                 #
# --------------------------------------------------------------------------- #


def test_dj_cues_become_source_dj_anchors_sorted():
    from vibemix.library.excerpt import anchors_for_track

    track = _track(
        (
            _cue(type="cue", start_s=120.0, number=2),
            _cue(type="cue", start_s=8.0, number=0),  # hot 0 -> intro
            _cue(type="cue", start_s=64.0, number=1),
        ),
        duration_s=300.0,
    )
    anchors = anchors_for_track(track)
    assert len(anchors) == 3
    assert all(isinstance(a, CueAnchor) for a in anchors)
    assert all(a.source == "dj" for a in anchors)
    # sorted ascending by start_s
    starts = [a.start_s for a in anchors]
    assert starts == sorted(starts)
    assert starts[0] == 8.0


def test_hot_cue_zero_is_intro_others_drop():
    from vibemix.library.excerpt import anchors_for_track

    track = _track(
        (
            _cue(type="cue", start_s=0.0, number=0),
            _cue(type="cue", start_s=90.0, number=3),
        )
    )
    anchors = anchors_for_track(track)
    by_start = {a.start_s: a for a in anchors}
    assert by_start[0.0].label == "intro"
    assert by_start[90.0].label == "drop"


def test_window_end_clamped_to_80s_and_next_cue_and_duration():
    from vibemix.library.excerpt import anchors_for_track

    track = _track(
        (
            _cue(type="cue", start_s=0.0, number=0),
            _cue(type="cue", start_s=30.0, number=1),  # next cue caps first window
            _cue(type="cue", start_s=200.0, number=2),  # 80s cap (200..280 < 300)
            _cue(type="cue", start_s=290.0, number=3),  # duration caps last
        ),
        duration_s=300.0,
    )
    anchors = anchors_for_track(track)
    by_start = {a.start_s: a for a in anchors}
    # first window capped by the next cue at 30s
    assert by_start[0.0].end_s == 30.0
    # third capped by the 80s window cap (200 + 80 = 280, before next cue 290)
    assert by_start[200.0].end_s == pytest.approx(280.0)
    # last capped by duration (290 + 80 = 370 -> 300)
    assert by_start[290.0].end_s == pytest.approx(300.0)
    # every window <= 80s and > 0
    for a in anchors:
        span = a.end_s - a.start_s
        assert 0.0 < span <= 80.0


def test_memory_cues_are_usable():
    from vibemix.library.excerpt import anchors_for_track

    track = _track((_cue(type="cue", start_s=50.0, number=-1),))  # memory cue
    anchors = anchors_for_track(track)
    assert len(anchors) == 1
    assert anchors[0].source == "dj"
    assert anchors[0].label == "drop"  # not hot-0, so drop


def test_loop_cues_are_usable():
    from vibemix.library.excerpt import anchors_for_track

    track = _track((_cue(type="loop", start_s=40.0, number=1, end_s=48.0),))
    anchors = anchors_for_track(track)
    assert len(anchors) == 1
    assert anchors[0].source == "dj"


def test_max_cues_cap():
    from vibemix.library.excerpt import anchors_for_track

    cues = tuple(_cue(type="cue", start_s=float(i * 10), number=i) for i in range(8))
    track = _track(cues)
    anchors = anchors_for_track(track, max_cues=4)
    assert len(anchors) == 4


# --------------------------------------------------------------------------- #
# anchors_for_track — load/fadein/fadeout are NOT structural (T-89-08)         #
# --------------------------------------------------------------------------- #


def test_load_fade_marks_are_not_anchors_falls_through_to_auto(monkeypatch):
    import vibemix.library.cue_engine as cue_engine

    sentinel = [CueAnchor(label="drop", start_s=64.0, end_s=120.0, confidence=0.5, source="auto")]
    monkeypatch.setattr(cue_engine, "detect_cues_auto", lambda *a, **k: list(sentinel))

    from vibemix.library.excerpt import anchors_for_track

    track = _track(
        (
            _cue(type="load", start_s=0.0, number=-1),
            _cue(type="fadein", start_s=2.0, number=-1),
            _cue(type="fadeout", start_s=290.0, number=-1),
        )
    )
    anchors = anchors_for_track(track)
    # No DJ anchors from load/fade marks — falls through to the auto engine.
    assert anchors == sentinel
    assert all(a.source == "auto" for a in anchors)


# --------------------------------------------------------------------------- #
# anchors_for_track — ANLZ second                                              #
# --------------------------------------------------------------------------- #


def test_dj_cues_win_over_anlz_index():
    from vibemix.library.excerpt import anchors_for_track

    track = _track((_cue(type="cue", start_s=8.0, number=0),))
    anchors = anchors_for_track(track, anlz_index=_anlz_index_for_track())

    assert len(anchors) == 1
    assert anchors[0].source == "dj"
    assert anchors[0].start_s == 8.0


def test_no_cues_uses_anlz_before_auto(monkeypatch):
    import vibemix.library.cue_engine as cue_engine

    monkeypatch.setattr(
        cue_engine,
        "detect_cues_auto",
        lambda *a, **k: pytest.fail("auto fallback should not run when ANLZ matches"),
    )

    from vibemix.library.excerpt import anchors_for_track

    anchors = anchors_for_track(_track(()), anlz_index=_anlz_index_for_track())

    assert len(anchors) == 1
    assert anchors[0].source == "anlz"
    assert anchors[0].label == "intro"
    assert anchors[0].start_s == 0.0


def test_no_anlz_match_delegates_to_detect_cues_auto(monkeypatch):
    import vibemix.library.cue_engine as cue_engine

    sentinel = [CueAnchor(label="drop", start_s=80.0, end_s=140.0, confidence=0.6, source="auto")]
    monkeypatch.setattr(cue_engine, "detect_cues_auto", lambda *a, **k: list(sentinel))

    from vibemix.library.excerpt import anchors_for_track

    anchors = anchors_for_track(_track(()), anlz_index=AnlzIndex(by_basename={}))

    assert anchors == sentinel


def test_anlz_error_delegates_to_detect_cues_auto(monkeypatch):
    import vibemix.library.anlz_ingest as anlz_ingest
    import vibemix.library.cue_engine as cue_engine

    sentinel = [CueAnchor(label="drop", start_s=80.0, end_s=140.0, confidence=0.6, source="auto")]

    def _raise(*args, **kwargs):
        raise RuntimeError("stale synthetic index")

    monkeypatch.setattr(anlz_ingest, "match_track_to_anlz", _raise)
    monkeypatch.setattr(cue_engine, "detect_cues_auto", lambda *a, **k: list(sentinel))

    from vibemix.library.excerpt import anchors_for_track

    anchors = anchors_for_track(_track(()), anlz_index=_anlz_index_for_track())

    assert anchors == sentinel


# --------------------------------------------------------------------------- #
# anchors_for_track — auto fallback                                            #
# --------------------------------------------------------------------------- #


def test_no_cues_delegates_to_detect_cues_auto(monkeypatch):
    import vibemix.library.cue_engine as cue_engine

    sentinel = [
        CueAnchor(label="intro", start_s=0.0, end_s=40.0, confidence=0.7, source="auto"),
        CueAnchor(label="drop", start_s=80.0, end_s=140.0, confidence=0.6, source="auto"),
    ]
    captured: dict[str, object] = {}

    def _fake_detect(path, *, max_cues=4):
        captured["path"] = path
        captured["max_cues"] = max_cues
        return list(sentinel)

    monkeypatch.setattr(cue_engine, "detect_cues_auto", _fake_detect)

    from vibemix.library.excerpt import anchors_for_track

    track = _track(())
    anchors = anchors_for_track(track)
    assert anchors == sentinel
    assert str(captured["path"]) == "/tmp/track1.mp3"


def test_empty_detect_cues_returns_empty_honest(monkeypatch):
    import vibemix.library.cue_engine as cue_engine

    monkeypatch.setattr(cue_engine, "detect_cues_auto", lambda *a, **k: [])

    from vibemix.library.excerpt import anchors_for_track

    track = _track(())
    anchors = anchors_for_track(track)
    assert anchors == []  # honest — caller whole-track falls back, never a faked anchor


# --------------------------------------------------------------------------- #
# cut_windows                                                                  #
# --------------------------------------------------------------------------- #


def test_cut_windows_clamps_and_drops_degenerate():
    from vibemix.library.excerpt import cut_windows

    anchors = [
        CueAnchor(label="intro", start_s=-5.0, end_s=40.0, confidence=0.9, source="dj"),
        CueAnchor(
            label="drop", start_s=80.0, end_s=80.0, confidence=0.9, source="dj"
        ),  # degenerate
        CueAnchor(
            label="drop", start_s=100.0, end_s=400.0, confidence=0.9, source="dj"
        ),  # clamp to dur + 80s
    ]
    windows = cut_windows(anchors, duration_s=300.0)
    # degenerate dropped
    assert all(e - s >= 1.0 for s, e in windows)
    assert all(e - s <= 80.0 for s, e in windows)
    assert all(0.0 <= s and e <= 300.0 for s, e in windows)
    # first window start clamped to 0
    assert windows[0][0] == 0.0


def test_cut_windows_empty():
    from vibemix.library.excerpt import cut_windows

    assert cut_windows([], duration_s=300.0) == []


# --------------------------------------------------------------------------- #
# Import purity                                                                #
# --------------------------------------------------------------------------- #


def test_import_is_torch_free():
    import vibemix.library.excerpt  # noqa: F401

    assert "torch" not in sys.modules
