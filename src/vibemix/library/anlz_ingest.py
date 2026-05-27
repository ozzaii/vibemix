# SPDX-License-Identifier: Apache-2.0
"""Import-light Rekordbox ANLZ structure ingest helpers.

This module turns Rekordbox's offline analysis sidecars into grounded musical
structure. It deliberately does not read the encrypted Rekordbox database, audio
files, CLAP models, or live deck state.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from vibemix.library.cue_types import CueAnchor, CueLabel
from vibemix.library.rekordbox import TrackEntry

__all__ = [
    "AnlzBeatGrid",
    "AnlzIndex",
    "AnlzPhrase",
    "AnlzTrackMeta",
    "BeatTime",
    "anchors_from_anlz",
    "beat_to_time",
    "build_anlz_index",
    "iter_anlz_ext_files",
    "map_pssi_kind",
    "match_track_to_anlz",
    "parse_anlz_bundle",
    "phrases_from_pssi_entries",
]

_DEFAULT_ANLZ_ROOTS = (
    Path.home() / "Library" / "Pioneer" / "rekordbox" / "share" / "PIONEER" / "USBANLZ",
    Path.home() / "Library" / "Pioneer" / "rekordbox" / "PIONEER" / "USBANLZ",
)
_MIN_ANLZ_ANCHOR_CONFIDENCE = 0.45
_MAX_ANLZ_CONFIDENCE = 0.92


@dataclass(frozen=True, slots=True)
class AnlzBeatGrid:
    times_s: tuple[float, ...]
    bpms: tuple[float, ...]
    beat_in_bar: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class BeatTime:
    time_s: float
    extrapolated: bool


@dataclass(frozen=True, slots=True)
class AnlzPhrase:
    index: int
    mood: int
    kind: int
    raw_label: str
    cue_label: CueLabel | None
    start_beat: int
    end_beat: int
    start_s: float
    end_s: float
    confidence: float
    flags: dict[str, int]


@dataclass(frozen=True, slots=True)
class AnlzTrackMeta:
    ext_path: Path
    dat_path: Path
    ppth_path: str
    basename_key: str
    beatgrid: AnlzBeatGrid
    phrases: tuple[AnlzPhrase, ...]


@dataclass(frozen=True, slots=True)
class AnlzIndex:
    by_basename: dict[str, tuple[AnlzTrackMeta, ...]]


def iter_anlz_ext_files(root: Path | None = None) -> Iterator[Path]:
    """Yield Rekordbox `.EXT` analysis files under `root`.

    Missing roots yield nothing. When `root` is omitted, scan both the current
    rekordbox `share/PIONEER/USBANLZ` tree and the older legacy
    `PIONEER/USBANLZ` tree. Paths are sorted for deterministic indexing.
    """
    roots = (Path(root),) if root is not None else _DEFAULT_ANLZ_ROOTS
    yielded: set[Path] = set()
    for base in roots:
        if not base.exists():
            continue
        for path in sorted(base.rglob("*.EXT")):
            resolved = path.resolve()
            if resolved in yielded:
                continue
            yielded.add(resolved)
            yield path


def parse_anlz_bundle(ext_path: Path) -> AnlzTrackMeta | None:
    """Parse one `.EXT` plus sibling `.DAT` ANLZ bundle.

    Returns `None` for ordinary missing/partial analysis. The `pyrekordbox.anlz`
    import is intentionally lazy so importing this module stays light.
    """
    ext = Path(ext_path)
    dat = ext.with_suffix(".DAT")
    if not ext.exists() or not dat.exists():
        return None

    try:
        from pyrekordbox.anlz import AnlzFile

        ext_anlz = AnlzFile.parse_file(ext)
        dat_anlz = AnlzFile.parse_file(dat)
    except Exception:
        return None

    ppth_tags = _get_tags(ext_anlz, "PPTH")
    pssi_tags = _get_tags(ext_anlz, "PSSI")
    pqtz_tags = _get_tags(dat_anlz, "PQTZ")
    if not ppth_tags or not pssi_tags or not pqtz_tags:
        return None

    ppth_path = str(_get_value(ppth_tags[0], "path", ""))
    if not ppth_path:
        return None

    beatgrid = _beatgrid_from_pqtz(pqtz_tags[0])
    if not beatgrid.times_s:
        return None

    pssi = pssi_tags[0]
    pssi_content = getattr(pssi, "content", pssi)
    entries = [_container_to_dict(entry) for entry in _get_value(pssi_content, "entries", ())]
    mood = int(_get_value(pssi_content, "mood", 0) or 0)
    end_beat = int(_get_value(pssi_content, "end_beat", len(beatgrid.times_s)) or 0)
    phrases = phrases_from_pssi_entries(
        mood=mood,
        end_beat=end_beat,
        entries=entries,
        beatgrid=beatgrid,
    )
    if not any(phrase.cue_label is not None for phrase in phrases):
        return None

    return AnlzTrackMeta(
        ext_path=ext,
        dat_path=dat,
        ppth_path=ppth_path,
        basename_key=_basename_key(ppth_path),
        beatgrid=beatgrid,
        phrases=phrases,
    )


def build_anlz_index(root: Path | None = None) -> AnlzIndex:
    """Build a collision-preserving basename index from available ANLZ files."""
    grouped: dict[str, list[AnlzTrackMeta]] = {}
    for ext_path in iter_anlz_ext_files(root):
        meta = parse_anlz_bundle(ext_path)
        if meta is None:
            continue
        grouped.setdefault(meta.basename_key, []).append(meta)
    return AnlzIndex(by_basename={key: tuple(values) for key, values in sorted(grouped.items())})


def match_track_to_anlz(track: TrackEntry, index: AnlzIndex) -> AnlzTrackMeta | None:
    """Resolve a track to ANLZ metadata by basename, then suffix if needed."""
    candidates = index.by_basename.get(_basename_key(track.filepath), ())
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        return None

    track_path = _normalize_path(track.filepath)
    suffix_matches = [
        candidate
        for candidate in candidates
        if track_path.endswith(_normalize_path(candidate.ppth_path))
        or _normalize_path(candidate.ppth_path).endswith(track_path)
    ]
    if len(suffix_matches) == 1:
        return suffix_matches[0]
    return None


def anchors_from_anlz(
    track: TrackEntry,
    meta: AnlzTrackMeta,
    *,
    max_cues: int = 4,
    min_confidence: float = _MIN_ANLZ_ANCHOR_CONFIDENCE,
    window_s: float = 80.0,
) -> list[CueAnchor]:
    """Convert mappable ANLZ phrases into `CueAnchor`s.

    DJ-authored cue priority is handled by `excerpt.py`; this function only
    maps ANLZ structure into the shared cue vocabulary.
    """
    duration_s = float(track.duration_s) if track.duration_s else 0.0
    anchors: list[CueAnchor] = []
    for phrase in meta.phrases:
        if phrase.cue_label is None or phrase.confidence < min_confidence:
            continue
        start = max(0.0, phrase.start_s)
        end = min(phrase.end_s, start + float(window_s))
        if duration_s > 0:
            end = min(end, duration_s)
        if end - start < 1.0:
            continue
        anchors.append(
            CueAnchor(
                label=phrase.cue_label,
                start_s=start,
                end_s=end,
                confidence=phrase.confidence,
                source="anlz",
            )
        )
        if len(anchors) >= max(0, int(max_cues)):
            break
    return anchors


def beat_to_time(
    beat: int, beatgrid: AnlzBeatGrid, *, fallback_bpm: float | None = None
) -> BeatTime | None:
    """Convert one-indexed ANLZ beat numbers into seconds."""
    if beat <= 0 or not beatgrid.times_s:
        return None
    idx = beat - 1
    if idx < len(beatgrid.times_s):
        return BeatTime(float(beatgrid.times_s[idx]), extrapolated=False)

    last_bpm = beatgrid.bpms[-1] if beatgrid.bpms else fallback_bpm
    if not last_bpm or last_bpm <= 0:
        return None
    last_idx = len(beatgrid.times_s) - 1
    last_time = float(beatgrid.times_s[-1])
    return BeatTime(last_time + (idx - last_idx) * 60.0 / float(last_bpm), extrapolated=True)


def phrases_from_pssi_entries(
    *,
    mood: int,
    end_beat: int,
    entries: list[dict[str, Any]],
    beatgrid: AnlzBeatGrid,
    fallback_bpm: float | None = None,
) -> tuple[AnlzPhrase, ...]:
    """Map raw PSSI phrase entries into normalized ANLZ phrases."""
    phrases: list[AnlzPhrase] = []
    starts = [int(entry.get("beat", 0) or 0) for entry in entries]
    for index, entry in enumerate(entries):
        start_beat = starts[index]
        next_start = starts[index + 1] if index + 1 < len(starts) else int(end_beat)
        if start_beat <= 0 or next_start <= start_beat:
            continue

        kind = int(entry.get("kind", 0) or 0)
        flags = {
            key: int(entry.get(key, 0) or 0) for key in ("k1", "k2", "k3", "fill", "beat_fill")
        }
        raw_label, cue_label, base_confidence = map_pssi_kind(mood, kind, flags)

        phrase_end = next_start
        fill_trimmed = False
        if flags["fill"] and start_beat < flags["beat_fill"] < phrase_end:
            phrase_end = flags["beat_fill"]
            fill_trimmed = True

        start_time = beat_to_time(start_beat, beatgrid, fallback_bpm=fallback_bpm)
        end_time = beat_to_time(phrase_end, beatgrid, fallback_bpm=fallback_bpm)
        if start_time is None or end_time is None or end_time.time_s <= start_time.time_s:
            continue

        confidence = base_confidence
        duration_beats = phrase_end - start_beat
        if duration_beats < 32:
            confidence -= 0.10
        if duration_beats > 384:
            confidence -= 0.08
        if start_time.extrapolated or end_time.extrapolated:
            confidence -= 0.08
        if fill_trimmed:
            confidence -= 0.05

        phrases.append(
            AnlzPhrase(
                index=index,
                mood=mood,
                kind=kind,
                raw_label=raw_label,
                cue_label=cue_label,
                start_beat=start_beat,
                end_beat=phrase_end,
                start_s=round(start_time.time_s, 6),
                end_s=round(end_time.time_s, 6),
                confidence=_clamp(confidence, 0.0, _MAX_ANLZ_CONFIDENCE),
                flags=flags,
            )
        )
    return tuple(phrases)


def map_pssi_kind(
    mood: int, kind: int, flags: dict[str, int] | None = None
) -> tuple[str, CueLabel | None, float]:
    """Map Rekordbox PSSI mood/kind to coarse cue labels."""
    f = flags or {}
    k1 = int(f.get("k1", 0) or 0)
    k2 = int(f.get("k2", 0) or 0)

    if mood == 1:
        if kind == 1:
            return ("Intro 1" if k1 == 1 else "Intro 2", "intro", 0.84)
        if kind == 2:
            if k2 == 1:
                raw = "Up 2"
            elif k1 == 1:
                raw = "Up 3"
            else:
                raw = "Up 1"
            return (raw, "build", 0.82)
        if kind == 3:
            return ("Down", "breakdown", 0.84)
        if kind == 5:
            return ("Chorus 2" if k1 == 1 else "Chorus 1", "drop", 0.80)
        if kind == 6:
            return ("Outro 1" if k1 == 1 else "Outro 2", "outro", 0.84)
        return ("unknown", None, 0.0)

    if mood == 2:
        if kind == 1:
            return ("Intro", "intro", 0.72)
        if 2 <= kind <= 7:
            return (f"Verse {kind - 1}", "build", 0.56)
        if kind == 8:
            return ("Bridge", "breakdown", 0.64)
        if kind == 9:
            return ("Chorus", "drop", 0.66)
        if kind == 10:
            return ("Outro", "outro", 0.72)
        return ("unknown", None, 0.0)

    if mood == 3:
        if kind == 1:
            return ("Intro", "intro", 0.60)
        if 2 <= kind <= 7:
            return (f"Verse {kind - 1}", "build", 0.42)
        if kind == 8:
            return ("Bridge", "breakdown", 0.50)
        if kind == 9:
            return ("Chorus", "drop", 0.52)
        if kind == 10:
            return ("Outro", "outro", 0.60)
    return ("unknown", None, 0.0)


def _get_tags(anlz_file: Any, key: str) -> list[Any]:
    try:
        return list(anlz_file.getall_tags(key))
    except Exception:
        return []


def _beatgrid_from_pqtz(tag: Any) -> AnlzBeatGrid:
    try:
        times = tuple(float(value) for value in tag.get_times())
        bpms = tuple(float(value) for value in tag.get_bpms())
        beats = tuple(int(value) for value in tag.get_beats())
    except Exception:
        return AnlzBeatGrid(times_s=(), bpms=(), beat_in_bar=())
    return AnlzBeatGrid(times_s=times, bpms=bpms, beat_in_bar=beats)


def _container_to_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    if hasattr(value, "items"):
        return {str(k): v for k, v in value.items()}
    out: dict[str, Any] = {}
    for key in ("beat", "kind", "k1", "k2", "k3", "fill", "beat_fill"):
        if hasattr(value, key):
            out[key] = getattr(value, key)
    return out


def _get_value(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    if hasattr(obj, key):
        return getattr(obj, key)
    try:
        return obj[key]
    except Exception:
        return default


def _basename_key(path: str) -> str:
    normalized = _normalize_path(path).rstrip("/")
    if not normalized:
        return ""
    return normalized.rsplit("/", 1)[-1].lower()


def _normalize_path(path: str) -> str:
    value = str(path).replace("\\", "/").lower()
    if value.startswith("file://localhost/"):
        value = value.removeprefix("file://localhost")
    return value.rstrip("/")


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, round(value, 6)))
