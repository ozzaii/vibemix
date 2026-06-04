# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from scripts.eval.anlz_cue_agreement import evaluate_anlz_cue_agreement

from vibemix.library.anlz_ingest import AnlzBeatGrid, AnlzIndex, AnlzPhrase, AnlzTrackMeta
from vibemix.library.rekordbox import CuePoint, TrackEntry


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


def _index() -> AnlzIndex:
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
    )
    return AnlzIndex(by_basename={"track one.mp3": (meta,)})


def test_anlz_cue_agreement_scores_when_dj_reference_exists() -> None:
    cues = (CuePoint(name="INTRO", type="cue", start_s=0.5, end_s=None, number=0),)

    report = evaluate_anlz_cue_agreement({"t1": _track(cues)}, _index())

    assert report["status"] == "ok"
    assert report["dj_reference_tracks"] == 1
    assert report["cue_agreement_scored_tracks"] == 1
    assert report["cue_agreement_mean_score"] == 1.0
    assert report["cue_agreement_mean_abs_offset_s"] == 0.5


def test_anlz_cue_agreement_honest_null_without_dj_reference() -> None:
    report = evaluate_anlz_cue_agreement({"t1": _track(())}, _index())

    assert report["status"] == "honest_null_no_dj_reference_cues"
    assert report["pssi_first_fill_candidate_tracks"] == 1
    assert report["dj_reference_tracks"] == 0
    assert report["cue_agreement_mean_score"] is None
    assert report["notes"]["agreement_score_is_not_fabricated_without_dj_refs"] is True
