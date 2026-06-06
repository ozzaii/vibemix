# SPDX-License-Identifier: Apache-2.0
"""Own-track source loader for Learn Save mode.

Save mode is allowed to own its decks, but it is not allowed to invent them.
This module turns real library entries into the exact audio slabs and
``BeatGrid`` objects that the owned-deck beatmatch judge already consumes.
When the user's library cannot supply two decoded, ANLZ-gridded tracks, the
caller gets an explicit fallback reason and can keep the bundled synth drill.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import unquote

import numpy as np

from vibemix.audio.grid import BeatGrid
from vibemix.library.audio_decode import load_audio_stereo
from vibemix.library.next_suggestion import next_suggestion
from vibemix.library.rekordbox import CuePoint, RekordboxLibrary, TempoNode, TrackEntry
from vibemix.library.store import LibraryStore
from vibemix.state import harmonics

SAVE_MODE_SAMPLE_RATE = 44_100
SAVE_MODE_LOOP_BEATS = 64
_MIN_LOOP_BEATS = 16


@dataclass(frozen=True, slots=True)
class PracticeDeckSource:
    """One decoded Learn-owned deck source."""

    track_id: str
    title: str
    artist: str
    bpm: float
    sample_rate: int
    samples: np.ndarray
    grid: BeatGrid
    cues: tuple[dict[str, float | str], ...]
    filepath: str
    source_start_s: float


@dataclass(frozen=True, slots=True)
class PracticeDeckSources:
    """A grounded two-deck source pair for Save-mode practice."""

    deck_a: PracticeDeckSource
    deck_b: PracticeDeckSource
    sample_rate: int
    seed_track_id: str
    suggested_track_id: str
    source: str = "library_save_mode"


@dataclass(frozen=True, slots=True)
class SaveModeLoadOutcome:
    """Result of attempting to build Save mode from the user's library."""

    sources: PracticeDeckSources | None
    fallback_reason: str | None = None

    @property
    def ok(self) -> bool:
        return self.sources is not None


@dataclass(frozen=True, slots=True)
class _BeatGridAdapter:
    times_s: tuple[float, ...]
    bpms: tuple[float, ...]
    beat_in_bar: tuple[int, ...]


DecodeStereo = Callable[[str | Path], tuple[np.ndarray, int]]
SuggestionFn = Callable[..., Any]


def load_save_mode_sources(
    library: RekordboxLibrary,
    store: LibraryStore,
    *,
    seed_track_id: str | None = None,
    target_sample_rate: int = SAVE_MODE_SAMPLE_RATE,
    loop_beats: int = SAVE_MODE_LOOP_BEATS,
    decoder: DecodeStereo = load_audio_stereo,
    suggestion_fn: SuggestionFn = next_suggestion,
) -> SaveModeLoadOutcome:
    """Build a real two-track Save-mode source pair, or explain the fallback.

    The library is filtered to decode-ready, ANLZ-gridded entries before
    calling ``next_suggestion``. That keeps the existing grounded suggestion
    engine in charge while preventing an unplayable top neighbour from forcing
    synth fallback when a usable neighbour sits behind it.
    """

    vector_map = _load_vector_map(store)
    if not vector_map:
        return SaveModeLoadOutcome(None, "library vector store is empty")

    playable_entries = tuple(
        entry
        for entry in library.tracks.values()
        if _entry_has_save_metadata(entry) and entry.track_id in vector_map
    )
    if len(playable_entries) < 2:
        return SaveModeLoadOutcome(None, "fewer than two ANLZ-gridded library tracks")

    seed = _select_seed_entry(playable_entries, seed_track_id=seed_track_id)
    if seed is None:
        return SaveModeLoadOutcome(None, "requested seed track is not Save-mode ready")

    filtered_library = RekordboxLibrary()
    filtered_library.tracks = {entry.track_id: entry for entry in playable_entries}

    seed_vector = vector_map.get(seed.track_id)
    if seed_vector is None:
        return SaveModeLoadOutcome(None, "seed track has no stored library vector")

    suggestion = suggestion_fn(
        store,
        filtered_library,
        seed_vector=seed_vector,
        seed_track_id=seed.track_id,
        played_ids=set(),
        seed_camelot=_camelot_for(seed),
        seed_bpm=_positive_bpm(seed.bpm),
        k=8,
    )
    if suggestion is None:
        return SaveModeLoadOutcome(None, "no compatible ANLZ-gridded neighbour")

    suggested_id = str(getattr(suggestion, "track_id", "") or "")
    suggested = filtered_library.lookup_by_id(suggested_id)
    if suggested is None or suggested.track_id == seed.track_id:
        return SaveModeLoadOutcome(None, "suggestion did not resolve to a second track")

    try:
        deck_a = build_practice_deck_source(
            seed,
            target_sample_rate=target_sample_rate,
            loop_beats=loop_beats,
            decoder=decoder,
        )
        deck_b = build_practice_deck_source(
            suggested,
            target_sample_rate=target_sample_rate,
            loop_beats=loop_beats,
            decoder=decoder,
        )
    except (OSError, ValueError, RuntimeError) as exc:
        return SaveModeLoadOutcome(None, f"failed to load own-track Save audio: {exc}")

    return SaveModeLoadOutcome(
        PracticeDeckSources(
            deck_a=deck_a,
            deck_b=deck_b,
            sample_rate=target_sample_rate,
            seed_track_id=seed.track_id,
            suggested_track_id=suggested.track_id,
        )
    )


def build_practice_deck_source(
    entry: TrackEntry,
    *,
    target_sample_rate: int = SAVE_MODE_SAMPLE_RATE,
    loop_beats: int = SAVE_MODE_LOOP_BEATS,
    decoder: DecodeStereo = load_audio_stereo,
) -> PracticeDeckSource:
    """Decode one library entry into a bounded practice slab and owned grid."""

    if not _entry_has_save_metadata(entry):
        raise ValueError(f"{entry.track_id} lacks filepath, BPM, or beatgrid")
    path = _audio_path_for(entry.filepath)
    samples, source_sample_rate = decoder(path)
    stereo = _as_stereo(samples)
    if source_sample_rate != target_sample_rate:
        stereo = _resample_linear(
            stereo,
            src_sr=int(source_sample_rate),
            dst_sr=int(target_sample_rate),
        )

    full_grid = beatgrid_from_tempo_nodes(entry.beatgrid, sample_rate=target_sample_rate)
    slab, start_frame = _slice_practice_slab(stereo, grid=full_grid, loop_beats=loop_beats)
    local_grid = BeatGrid(
        anchor_frame=full_grid.anchor_frame - float(start_frame),
        bpm=full_grid.bpm,
        sample_rate=target_sample_rate,
    )
    start_s = float(start_frame) / float(target_sample_rate)
    duration_s = float(slab.shape[0]) / float(target_sample_rate)
    return PracticeDeckSource(
        track_id=entry.track_id,
        title=entry.title,
        artist=entry.artist,
        bpm=full_grid.bpm,
        sample_rate=target_sample_rate,
        samples=slab,
        grid=local_grid,
        cues=_cue_payload(entry.cues, source_start_s=start_s, duration_s=duration_s),
        filepath=str(path),
        source_start_s=start_s,
    )


def beatgrid_from_tempo_nodes(
    beatgrid: Iterable[TempoNode],
    *,
    sample_rate: int,
) -> BeatGrid:
    """Build the owned-deck judge grid from Rekordbox TEMPO nodes."""

    nodes = tuple(beatgrid)
    adapter = _BeatGridAdapter(
        times_s=tuple(float(node.inizio_s) for node in nodes),
        bpms=tuple(float(node.bpm) for node in nodes),
        beat_in_bar=tuple(int(node.battito) for node in nodes),
    )
    return BeatGrid.from_anlz(adapter, sample_rate=sample_rate, prefer_downbeat=True)


def _entry_has_save_metadata(entry: TrackEntry) -> bool:
    return bool(entry.filepath) and bool(entry.beatgrid) and _positive_bpm(entry.bpm) is not None


def _select_seed_entry(
    entries: Iterable[TrackEntry],
    *,
    seed_track_id: str | None,
) -> TrackEntry | None:
    for entry in entries:
        if seed_track_id is None or entry.track_id == seed_track_id:
            return entry
    return None


def _load_vector_map(store: LibraryStore) -> dict[str, np.ndarray]:
    try:
        ids, vectors = store._backend.load_all()
    except Exception:
        return {}
    arr = np.asarray(vectors, dtype=np.float32)
    if arr.ndim != 2 or arr.shape[0] <= 0:
        return {}
    out: dict[str, np.ndarray] = {}
    for idx, track_id in enumerate(ids):
        if idx >= arr.shape[0]:
            break
        out[str(track_id)] = arr[idx].astype(np.float32, copy=True)
    return out


def _positive_bpm(value: float | int | None) -> float | None:
    try:
        bpm = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(bpm) or bpm <= 0.0:
        return None
    return bpm


def _camelot_for(entry: TrackEntry) -> str | None:
    if entry.camelot:
        return entry.camelot
    return harmonics.to_camelot(entry.key) if entry.key else None


def _audio_path_for(filepath: str) -> Path:
    text = unquote(str(filepath).strip())
    if text.startswith("file://localhost"):
        text = text.removeprefix("file://localhost")
    elif text.startswith("file://"):
        text = text.removeprefix("file://")
    return Path(text).expanduser()


def _as_stereo(samples: np.ndarray) -> np.ndarray:
    arr = np.asarray(samples, dtype=np.float32)
    if arr.ndim == 1:
        arr = np.column_stack([arr, arr])
    elif arr.ndim != 2:
        raise ValueError("decoded audio must be a mono or stereo array")
    if arr.shape[0] <= 0:
        raise ValueError("decoded audio is empty")
    if arr.shape[1] == 1:
        arr = np.column_stack([arr[:, 0], arr[:, 0]])
    elif arr.shape[1] > 2:
        arr = arr[:, :2]
    if arr.shape[1] != 2:
        raise ValueError("decoded audio must have two channels")
    return arr.astype(np.float32, copy=False)


def _resample_linear(samples: np.ndarray, *, src_sr: int, dst_sr: int) -> np.ndarray:
    if src_sr == dst_sr:
        return samples.astype(np.float32, copy=False)
    if src_sr <= 0 or dst_sr <= 0:
        raise ValueError("sample rates must be positive")
    target_n = max(1, round(samples.shape[0] * float(dst_sr) / float(src_sr)))
    src_x = np.linspace(0.0, samples.shape[0] - 1, samples.shape[0], dtype=np.float64)
    dst_x = np.linspace(0.0, samples.shape[0] - 1, target_n, dtype=np.float64)
    left = np.interp(dst_x, src_x, samples[:, 0])
    right = np.interp(dst_x, src_x, samples[:, 1])
    return np.column_stack([left, right]).astype(np.float32)


def _slice_practice_slab(
    samples: np.ndarray,
    *,
    grid: BeatGrid,
    loop_beats: int,
) -> tuple[np.ndarray, int]:
    min_frames = max(1, round(grid.beat_len_frames * _MIN_LOOP_BEATS))
    target_frames = max(min_frames, round(grid.beat_len_frames * max(_MIN_LOOP_BEATS, loop_beats)))
    if samples.shape[0] < min_frames:
        raise ValueError("track is too short for a Save-mode practice window")
    max_start = max(0, samples.shape[0] - target_frames)
    start_frame = int(max(0, min(max_start, math.floor(grid.anchor_frame))))
    end_frame = min(samples.shape[0], start_frame + target_frames)
    slab = samples[start_frame:end_frame]
    if slab.shape[0] < min_frames:
        raise ValueError("track has no usable Save-mode practice window")
    return np.ascontiguousarray(slab.astype(np.float32, copy=False)), start_frame


def _cue_payload(
    cues: Iterable[CuePoint],
    *,
    source_start_s: float,
    duration_s: float,
) -> tuple[dict[str, float | str], ...]:
    out: list[dict[str, float | str]] = []
    for cue in cues:
        rel_start = float(cue.start_s) - source_start_s
        if rel_start < 0.0 or rel_start > duration_s:
            continue
        label = (cue.name or cue.type or "cue").strip().lower()
        item: dict[str, float | str] = {
            "label": label[:48],
            "start_s": round(rel_start, 3),
            "end_s": round(min(duration_s, rel_start + 4.0), 3),
            "source": cue.source,
        }
        if cue.end_s is not None:
            rel_end = max(rel_start, float(cue.end_s) - source_start_s)
            item["end_s"] = round(min(duration_s, rel_end), 3)
        out.append(item)
    if out:
        return tuple(out)
    return (
        {
            "label": "save window",
            "start_s": 0.0,
            "end_s": round(duration_s, 3),
            "source": "library",
        },
    )


__all__ = [
    "SAVE_MODE_LOOP_BEATS",
    "SAVE_MODE_SAMPLE_RATE",
    "PracticeDeckSource",
    "PracticeDeckSources",
    "SaveModeLoadOutcome",
    "beatgrid_from_tempo_nodes",
    "build_practice_deck_source",
    "load_save_mode_sources",
]
