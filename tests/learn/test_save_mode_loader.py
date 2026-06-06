# SPDX-License-Identifier: Apache-2.0
"""Save-mode own-track loader tests."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from vibemix.learn.save_mode_loader import (
    SAVE_MODE_SAMPLE_RATE,
    beatgrid_from_tempo_nodes,
    build_practice_deck_source,
    load_save_mode_sources,
)
from vibemix.library.rekordbox import CuePoint, RekordboxLibrary, TempoNode, TrackEntry


def _tempo_nodes(bpm: float) -> tuple[TempoNode, ...]:
    beat_s = 60.0 / bpm
    return tuple(
        TempoNode(
            inizio_s=idx * beat_s,
            bpm=bpm,
            metro="4/4",
            battito=(idx % 4) + 1,
        )
        for idx in range(12)
    )


def _track(
    track_id: str,
    *,
    bpm: float = 128.0,
    key: str = "8A",
    filepath: str | None = None,
    beatgrid: tuple[TempoNode, ...] | None = None,
    cues: tuple[CuePoint, ...] = (),
) -> TrackEntry:
    return TrackEntry(
        track_id=track_id,
        title=f"Title {track_id}",
        artist=f"Artist {track_id}",
        album="",
        bpm=bpm,
        key=key,
        duration_s=300.0,
        cues=cues,
        filepath=filepath if filepath is not None else f"/tmp/{track_id}.wav",
        camelot=key,
        beatgrid=_tempo_nodes(bpm) if beatgrid is None else beatgrid,
    )


class _FakeBackend:
    def __init__(self, ids: list[str]) -> None:
        self._ids = ids
        self._vectors = np.eye(len(ids), 8, dtype=np.float32)

    def load_all(self):
        return self._ids, self._vectors


class _FakeStore:
    def __init__(self, ranked: list[tuple[str, float]]) -> None:
        self._ranked = ranked
        self._backend = _FakeBackend([track_id for track_id, _sim in ranked])

    def search_centered(self, _qvec, k: int = 10):
        return self._ranked[:k]


def _library(*entries: TrackEntry) -> RekordboxLibrary:
    library = RekordboxLibrary()
    library.tracks = {entry.track_id: entry for entry in entries}
    return library


def _sine_decoder(path: str | Path) -> tuple[np.ndarray, int]:
    sr = SAVE_MODE_SAMPLE_RATE
    seconds = 40
    freq = 220.0 if "seed" in str(path) else 330.0
    t = np.arange(sr * seconds, dtype=np.float32) / float(sr)
    mono = 0.2 * np.sin(2.0 * np.pi * freq * t)
    return np.column_stack([mono, mono]).astype(np.float32), sr


def test_beatgrid_from_tempo_nodes_anchors_to_rekordbox_downbeat() -> None:
    grid = beatgrid_from_tempo_nodes(
        (
            TempoNode(inizio_s=0.0, bpm=120.0, metro="4/4", battito=3),
            TempoNode(inizio_s=0.5, bpm=120.0, metro="4/4", battito=4),
            TempoNode(inizio_s=1.0, bpm=120.0, metro="4/4", battito=1),
        ),
        sample_rate=48_000,
    )

    assert grid.anchor_frame == pytest.approx(48_000.0)
    assert grid.bpm == pytest.approx(120.0)


def test_build_practice_deck_source_decodes_bounded_real_track_slab() -> None:
    entry = _track(
        "seed",
        cues=(CuePoint(name="DROP", type="cue", start_s=8.0, end_s=None, number=1),),
    )

    source = build_practice_deck_source(entry, decoder=_sine_decoder)

    assert source.track_id == "seed"
    assert source.sample_rate == SAVE_MODE_SAMPLE_RATE
    assert source.samples.shape[1] == 2
    assert source.samples.dtype == np.float32
    assert source.grid.bpm == pytest.approx(128.0)
    assert source.cues[0]["label"] == "drop"


def test_load_save_mode_sources_uses_next_suggestion_over_ready_tracks() -> None:
    seed = _track("seed", filepath="/tmp/seed.wav")
    missing_grid = _track("missing-grid", beatgrid=())
    target = _track("target", bpm=128.0, key="8A", filepath="/tmp/target.wav")
    store = _FakeStore([("seed", 0.99), ("missing-grid", 0.96), ("target", 0.90)])

    outcome = load_save_mode_sources(
        _library(seed, missing_grid, target),
        store,
        decoder=_sine_decoder,
    )

    assert outcome.ok is True
    assert outcome.sources is not None
    assert outcome.sources.seed_track_id == "seed"
    assert outcome.sources.suggested_track_id == "target"
    assert outcome.sources.deck_a.samples.shape[0] > 0
    assert outcome.sources.deck_b.grid.bpm == pytest.approx(128.0)


def test_load_save_mode_sources_honest_null_without_two_anlz_tracks() -> None:
    seed = _track("seed")
    no_grid = _track("no-grid", beatgrid=())
    store = _FakeStore([("seed", 0.99), ("no-grid", 0.9)])

    outcome = load_save_mode_sources(_library(seed, no_grid), store, decoder=_sine_decoder)

    assert outcome.sources is None
    assert outcome.fallback_reason == "fewer than two ANLZ-gridded library tracks"


def test_load_save_mode_sources_honest_null_when_decoder_fails() -> None:
    seed = _track("seed")
    target = _track("target")
    store = _FakeStore([("seed", 0.99), ("target", 0.9)])

    def fail_decoder(_path: str | Path) -> tuple[np.ndarray, int]:
        raise ValueError("no audio frames")

    outcome = load_save_mode_sources(_library(seed, target), store, decoder=fail_decoder)

    assert outcome.sources is None
    assert outcome.fallback_reason is not None
    assert "no audio frames" in outcome.fallback_reason


def test_load_save_mode_sources_honest_null_without_vectors() -> None:
    seed = _track("seed")
    target = _track("target")
    store = _FakeStore([])

    outcome = load_save_mode_sources(_library(seed, target), store, decoder=_sine_decoder)

    assert outcome.sources is None
    assert outcome.fallback_reason == "library vector store is empty"
