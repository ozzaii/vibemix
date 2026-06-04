# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import subprocess
import sys
from types import SimpleNamespace

import pytest

import vibemix.library.anlz_ingest as anlz_ingest
from vibemix.library.anlz_ingest import (
    AnlzBeatGrid,
    AnlzDjCue,
    AnlzIndex,
    AnlzTrackMeta,
    anchors_from_anlz,
    beat_to_time,
    dj_cue_anchors_from_anlz,
    iter_anlz_ext_files,
    map_pssi_kind,
    match_track_to_anlz,
    phrases_from_pssi_entries,
)
from vibemix.library.rekordbox import TrackEntry


def _grid(n: int = 96, *, bpm: float = 120.0) -> AnlzBeatGrid:
    step = 60.0 / bpm
    return AnlzBeatGrid(
        times_s=tuple(round(i * step, 6) for i in range(n)),
        bpms=tuple(bpm for _ in range(n)),
        beat_in_bar=tuple((i % 4) + 1 for i in range(n)),
    )


def _track(filepath: str = "/music/a/fixture.wav", *, duration_s: float = 300.0) -> TrackEntry:
    return TrackEntry(
        track_id="t1",
        title="Fixture Track",
        artist="Fixture Artist",
        album="",
        bpm=120.0,
        key="8A",
        duration_s=duration_s,
        cues=(),
        filepath=filepath,
    )


def _meta(
    *,
    ppth_path: str = "/music/a/fixture.wav",
    phrases=(),
    beatgrid: AnlzBeatGrid | None = None,
    dj_cues: tuple[AnlzDjCue, ...] = (),
) -> AnlzTrackMeta:
    return AnlzTrackMeta(
        ext_path="/fixture/ANLZ0000.EXT",  # type: ignore[arg-type]
        dat_path="/fixture/ANLZ0000.DAT",  # type: ignore[arg-type]
        ppth_path=ppth_path,
        basename_key=ppth_path.rsplit("/", 1)[-1].lower(),
        beatgrid=beatgrid or _grid(),
        phrases=tuple(phrases),
        dj_cues=dj_cues,
    )


def test_high_mood_maps_core_kinds_to_cue_labels() -> None:
    assert map_pssi_kind(1, 1, {"k1": 1}) == ("Intro 1", "intro", 0.84)
    assert map_pssi_kind(1, 2, {"k2": 1}) == ("Up 2", "build", 0.82)
    assert map_pssi_kind(1, 3, {}) == ("Down", "breakdown", 0.84)
    assert map_pssi_kind(1, 5, {"k1": 1}) == ("Chorus 2", "drop", 0.80)
    assert map_pssi_kind(1, 6, {}) == ("Outro 2", "outro", 0.84)


def test_high_mood_unknown_kind_drops_from_anchor_list() -> None:
    phrases = phrases_from_pssi_entries(
        mood=1,
        end_beat=96,
        entries=[
            {"beat": 1, "kind": 99},
            {"beat": 33, "kind": 1},
        ],
        beatgrid=_grid(),
    )
    anchors = anchors_from_anlz(_track(), _meta(phrases=phrases), max_cues=4)

    assert [anchor.label for anchor in anchors] == ["intro"]
    assert all(anchor.source == "anlz" for anchor in anchors)


def test_mid_mood_verse_maps_to_hedged_build() -> None:
    phrases = phrases_from_pssi_entries(
        mood=2,
        end_beat=65,
        entries=[{"beat": 1, "kind": 2}],
        beatgrid=_grid(),
    )

    assert len(phrases) == 1
    assert phrases[0].raw_label == "Verse 1"
    assert phrases[0].cue_label == "build"
    assert phrases[0].confidence == pytest.approx(0.56)


def test_low_mood_build_below_default_anchor_floor_drops() -> None:
    phrases = phrases_from_pssi_entries(
        mood=3,
        end_beat=65,
        entries=[{"beat": 1, "kind": 2}],
        beatgrid=_grid(),
    )

    assert phrases[0].confidence == pytest.approx(0.42)
    assert anchors_from_anlz(_track(), _meta(phrases=phrases), max_cues=4) == []


def test_dj_cue_anchors_from_anlz_sidecar_cues() -> None:
    anchors = dj_cue_anchors_from_anlz(
        _track(duration_s=180.0),
        _meta(
            dj_cues=(
                AnlzDjCue(
                    source_tag="PCO2",
                    name="mix in",
                    cue_type="hotcue",
                    number=1,
                    start_s=0.5,
                ),
                AnlzDjCue(
                    source_tag="PCO2",
                    name="drop",
                    cue_type="hotcue",
                    number=2,
                    start_s=64.0,
                    end_s=96.0,
                ),
            )
        ),
        max_cues=8,
    )

    assert [anchor.source for anchor in anchors] == ["dj", "dj"]
    assert [anchor.label for anchor in anchors] == ["intro", "drop"]
    assert anchors[0].start_s == pytest.approx(0.5)
    assert anchors[0].end_s == pytest.approx(64.0)
    assert anchors[1].end_s == pytest.approx(96.0)


def test_dj_cues_from_anlz_tags_prefers_pco2_over_pcob() -> None:
    class FakeAnlz:
        def getall_tags(self, key):
            if key == "PCOB":
                return [
                    SimpleNamespace(
                        content={
                            "cue_type": "hotcue",
                            "entries": [
                                {
                                    "hot_cue": 2,
                                    "status": "enabled",
                                    "type": "single",
                                    "time": 64000,
                                    "loop_time": -1,
                                    "comment": "",
                                }
                            ],
                        }
                    )
                ]
            if key == "PCO2":
                return [
                    SimpleNamespace(
                        content={
                            "type": "hotcue",
                            "entries": [
                                {
                                    "hot_cue": 2,
                                    "type": 1,
                                    "time": 64000,
                                    "loop_time": -1,
                                    "comment": "drop",
                                },
                                {
                                    "hot_cue": 3,
                                    "type": 2,
                                    "time": 128000,
                                    "loop_time": 144000,
                                    "comment": "loop",
                                },
                            ],
                        }
                    )
                ]
            return []

    cues = anlz_ingest._dj_cues_from_anlz_tags(FakeAnlz())

    assert len(cues) == 2
    assert cues[0] == AnlzDjCue(
        source_tag="PCO2",
        name="drop",
        cue_type="hotcue",
        number=2,
        start_s=64.0,
        end_s=None,
    )
    assert cues[1].start_s == pytest.approx(128.0)
    assert cues[1].end_s == pytest.approx(144.0)


def test_fill_trims_phrase_end_and_lowers_confidence() -> None:
    phrases = phrases_from_pssi_entries(
        mood=1,
        end_beat=97,
        entries=[
            {"beat": 1, "kind": 1, "fill": 1, "beat_fill": 17},
            {"beat": 65, "kind": 5},
        ],
        beatgrid=_grid(128),
    )

    first = phrases[0]
    assert first.end_beat == 17
    assert first.end_s == pytest.approx(8.0)
    assert first.confidence == pytest.approx(0.69)
    assert first.flags["fill"] == 1


def test_phrase_end_uses_next_phrase_and_last_uses_header_end_beat() -> None:
    phrases = phrases_from_pssi_entries(
        mood=1,
        end_beat=97,
        entries=[
            {"beat": 1, "kind": 1},
            {"beat": 33, "kind": 5},
        ],
        beatgrid=_grid(128),
    )

    assert phrases[0].end_beat == 33
    assert phrases[1].end_beat == 97


def test_beat_to_time_one_indexed_mapping() -> None:
    grid = _grid(8, bpm=120.0)

    assert beat_to_time(1, grid).time_s == pytest.approx(0.0)  # type: ignore[union-attr]
    assert beat_to_time(4, grid).time_s == pytest.approx(1.5)  # type: ignore[union-attr]


def test_beat_to_time_extrapolates_from_final_bpm() -> None:
    grid = AnlzBeatGrid(times_s=(0.0, 0.5), bpms=(120.0, 120.0), beat_in_bar=(1, 2))
    value = beat_to_time(4, grid)

    assert value is not None
    assert value.extrapolated is True
    assert value.time_s == pytest.approx(1.5)


def test_beat_to_time_beyond_grid_without_bpm_returns_none() -> None:
    grid = AnlzBeatGrid(times_s=(0.0, 0.5), bpms=(), beat_in_bar=(1, 2))
    assert beat_to_time(4, grid) is None


def test_unique_basename_matches() -> None:
    meta = _meta(ppth_path="/library/a/same.wav")
    index = AnlzIndex(by_basename={"same.wav": (meta,)})

    assert match_track_to_anlz(_track("/other/path/same.wav"), index) is meta


def test_duplicate_basename_with_suffix_match_resolves() -> None:
    meta_a = _meta(ppth_path="/library/a/same.wav")
    meta_b = _meta(ppth_path="/library/b/same.wav")
    index = AnlzIndex(by_basename={"same.wav": (meta_a, meta_b)})

    assert match_track_to_anlz(_track("/library/b/same.wav"), index) is meta_b


def test_duplicate_basename_without_suffix_match_returns_none() -> None:
    meta_a = _meta(ppth_path="/library/a/same.wav")
    meta_b = _meta(ppth_path="/library/b/same.wav")
    index = AnlzIndex(by_basename={"same.wav": (meta_a, meta_b)})

    assert match_track_to_anlz(_track("/unknown/same.wav"), index) is None


def test_unmatched_basename_returns_none() -> None:
    index = AnlzIndex(by_basename={"other.wav": (_meta(ppth_path="/library/other.wav"),)})
    assert match_track_to_anlz(_track("/library/missing.wav"), index) is None


def test_iter_anlz_ext_files_scans_share_and_legacy_defaults(tmp_path, monkeypatch) -> None:
    import vibemix.library.anlz_ingest as anlz_ingest

    share_root = tmp_path / "share" / "PIONEER" / "USBANLZ"
    legacy_root = tmp_path / "PIONEER" / "USBANLZ"
    share_file = share_root / "A" / "ANLZ0000.EXT"
    legacy_file = legacy_root / "B" / "ANLZ0000.EXT"
    share_file.parent.mkdir(parents=True)
    legacy_file.parent.mkdir(parents=True)
    share_file.write_bytes(b"share")
    legacy_file.write_bytes(b"legacy")

    monkeypatch.setattr(anlz_ingest, "_DEFAULT_ANLZ_ROOTS", (share_root, legacy_root))

    assert list(iter_anlz_ext_files()) == [share_file, legacy_file]


def test_import_is_pyrekordbox_lazy() -> None:
    code = (
        "import sys\n"
        "import vibemix.library.anlz_ingest\n"
        "print(any(name.startswith('pyrekordbox') for name in sys.modules))\n"
    )
    out = subprocess.check_output([sys.executable, "-c", code], text=True)
    assert out.strip() == "False"
