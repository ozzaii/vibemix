# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from pathlib import Path

from scripts.eval.anlz_cue_agreement import (
    evaluate_anlz_cue_agreement,
    load_rekordbox_xml_library,
)

from vibemix.library.anlz_ingest import (
    AnlzBeatGrid,
    AnlzDjCue,
    AnlzIndex,
    AnlzPhrase,
    AnlzTrackMeta,
)
from vibemix.library.rekordbox import CuePoint, RekordboxLibrary, TrackEntry


def _track(cues: tuple[CuePoint, ...] = ()) -> TrackEntry:
    return TrackEntry(
        track_id="t1",
        title="Track One",
        artist="",
        album="",
        bpm=128.0,
        key="",
        duration_s=240.0,
        cues=cues,
        filepath="/Music/Track One.mp3",
    )


def _index(*, dj_cues: tuple[AnlzDjCue, ...] = ()) -> AnlzIndex:
    phrase = AnlzPhrase(
        index=0,
        mood=1,
        kind=1,
        raw_label="Intro 1",
        cue_label="intro",
        start_beat=1,
        end_beat=65,
        start_s=0.0,
        end_s=30.0,
        confidence=0.84,
        flags={},
    )
    meta = AnlzTrackMeta(
        ext_path="/tmp/ANLZ0000.EXT",  # type: ignore[arg-type]
        dat_path="/tmp/ANLZ0000.DAT",  # type: ignore[arg-type]
        ppth_path="/Music/Track One.mp3",
        basename_key="track one.mp3",
        beatgrid=AnlzBeatGrid(times_s=(0.0,), bpms=(128.0,), beat_in_bar=(1,)),
        phrases=(phrase,),
        dj_cues=dj_cues,
    )
    return AnlzIndex(by_basename={"track one.mp3": (meta,)})


def _index_for_basename(basename: str, *, phrase_start_s: float) -> AnlzIndex:
    phrase = AnlzPhrase(
        index=0,
        mood=1,
        kind=1,
        raw_label="Intro 1",
        cue_label="intro",
        start_beat=1,
        end_beat=65,
        start_s=phrase_start_s,
        end_s=phrase_start_s + 30.0,
        confidence=0.84,
        flags={},
    )
    meta = AnlzTrackMeta(
        ext_path="/tmp/ANLZ0001.EXT",  # type: ignore[arg-type]
        dat_path="/tmp/ANLZ0001.DAT",  # type: ignore[arg-type]
        ppth_path=f"/Users/test/Music/{basename}",
        basename_key=basename,
        beatgrid=AnlzBeatGrid(times_s=(0.0,), bpms=(124.0,), beat_in_bar=(1,)),
        phrases=(phrase,),
    )
    return AnlzIndex(by_basename={basename: (meta,)})


def test_anlz_cue_agreement_scores_when_dj_reference_exists() -> None:
    cues = (CuePoint(name="INTRO", type="cue", start_s=0.5, end_s=None, number=0),)

    report = evaluate_anlz_cue_agreement({"t1": _track(cues)}, _index())

    assert report["status"] == "ok"
    assert report["dj_reference_tracks"] == 1
    assert report["cache_dj_reference_tracks"] == 1
    assert report["anlz_sidecar_dj_reference_tracks"] == 0
    assert report["cue_agreement_scored_tracks"] == 1
    assert report["cue_agreement_mean_score"] == 1.0
    assert report["cue_agreement_mean_abs_offset_s"] == 0.5
    assert report["reference_audit"]["cache_tracks_with_structural_dj_cues"] == 1
    assert report["reference_audit"]["cache_structural_dj_anchor_count"] == 1
    assert report["reference_audit"]["numeric_agreement_claimable"] is True
    assert report["reference_audit"]["missing_reference_reason"] is None


def test_anlz_cue_agreement_scores_sidecar_dj_cues_when_cache_has_none() -> None:
    report = evaluate_anlz_cue_agreement(
        {"t1": _track(())},
        _index(
            dj_cues=(
                AnlzDjCue(
                    source_tag="PCO2",
                    name="intro",
                    cue_type="hotcue",
                    number=1,
                    start_s=0.5,
                ),
            )
        ),
    )

    assert report["status"] == "ok"
    assert report["dj_reference_tracks"] == 1
    assert report["cache_dj_reference_tracks"] == 0
    assert report["anlz_sidecar_dj_reference_tracks"] == 1
    assert report["anlz_sidecar_dj_anchor_count"] == 1
    assert report["cue_agreement_mean_score"] == 1.0
    assert report["cue_agreement_mean_abs_offset_s"] == 0.5
    assert report["sample_rows"][0]["dj_reference_source"] == "anlz_pcob_pco2"
    assert report["reference_audit"]["anlz_sidecar_tracks_with_pcob_pco2_dj_cues"] == 1
    assert report["reference_audit"]["anlz_sidecar_pcob_pco2_dj_anchor_count"] == 1
    assert report["reference_audit"]["numeric_agreement_claimable"] is True


def test_anlz_cue_agreement_honest_null_without_dj_reference() -> None:
    report = evaluate_anlz_cue_agreement({"t1": _track(())}, _index())

    assert report["status"] == "honest_null_no_dj_reference_cues"
    assert report["pssi_first_fill_candidate_tracks"] == 1
    assert report["dj_reference_tracks"] == 0
    assert report["cache_dj_reference_tracks"] == 0
    assert report["anlz_sidecar_dj_reference_tracks"] == 0
    assert report["anlz_sidecar_dj_anchor_count"] == 0
    assert report["cue_agreement_mean_score"] is None
    assert report["reference_audit"] == {
        "cache_tracks_with_structural_dj_cues": 0,
        "cache_structural_dj_anchor_count": 0,
        "anlz_sidecar_tracks_with_pcob_pco2_dj_cues": 0,
        "anlz_sidecar_pcob_pco2_dj_anchor_count": 0,
        "numeric_agreement_claimable": False,
        "missing_reference_reason": (
            "cache has no structural DJ cues and matched ANLZ sidecars have no PCOB/PCO2 DJ cue entries"
        ),
    }
    assert report["notes"]["agreement_score_is_not_fabricated_without_dj_refs"] is True


def test_load_rekordbox_xml_library_uses_isolated_cache(monkeypatch, tmp_path) -> None:
    user_cache = tmp_path / "user" / "library.pkl"
    isolated_cache = tmp_path / "eval" / "library.pkl"
    monkeypatch.setattr(RekordboxLibrary, "CACHE_PATH", user_cache)

    tracks, source_path = load_rekordbox_xml_library(
        Path("tests/library/fixtures/synthetic_collection.xml"),
        cache_path=isolated_cache,
    )

    assert source_path == "tests/library/fixtures/synthetic_collection.xml"
    assert len(tracks) == 5
    assert isolated_cache.exists()
    assert not user_cache.exists()
    assert RekordboxLibrary.CACHE_PATH == user_cache


def test_xml_reference_can_score_against_matching_anlz(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(RekordboxLibrary, "CACHE_PATH", tmp_path / "user" / "library.pkl")
    tracks, _source_path = load_rekordbox_xml_library(
        Path("tests/library/fixtures/synthetic_collection.xml"),
        cache_path=tmp_path / "eval" / "library.pkl",
    )

    report = evaluate_anlz_cue_agreement(
        tracks,
        _index_for_basename("track-1.mp3", phrase_start_s=8.5),
    )

    assert report["status"] == "ok"
    assert report["anlz_matched_cached_tracks"] == 1
    assert report["cache_dj_reference_tracks"] == 1
    assert report["cue_agreement_scored_tracks"] == 1
    assert report["cue_agreement_mean_score"] == 0.333333
    assert report["cue_agreement_mean_abs_offset_s"] == 0.5
    assert report["reference_audit"]["numeric_agreement_claimable"] is True
