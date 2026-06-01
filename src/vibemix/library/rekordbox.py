# SPDX-License-Identifier: Apache-2.0
"""RekordboxLibrary — one-shot ``collection.xml`` loader for vibemix v2.0.

Lifecycle::

    lib = RekordboxLibrary()
    lib.load_xml("/path/to/collection.xml")  # fresh parse, writes pickle cache
    # ... later session, possibly different process ...
    lib2 = RekordboxLibrary()
    if not lib2.try_load_cache():
        lib2.load_xml("/path/to/collection.xml")  # cold-start fallback

The XML parser is ``pyrekordbox.RekordboxXml`` (Plan 25-01 spike-locked at
0.4.4 with ``--no-deps + manual transitives`` install recipe). The SQLCipher
``db6`` path lives in the same package namespace but is NEVER imported,
called, or otherwise activated — guarded by a try/except fallback to stdlib
``sqlite3`` in ``pyrekordbox/db6/database.py:28-34``. v2.0's grep gate
(``grep -r "Rekordbox6Database\\|pyrekordbox.db6" src/vibemix/``) must stay
empty so future contributors can't silently activate the SQLCipher binary.

Concurrency: single-threaded by intent. The library is loaded once at sidecar
start (after the wizard completes the optional ``Import collection.xml`` step
in Phase 25 Wave 3 UI) and stays read-only for the session. No locks needed.

Staleness nudge (LIBRARY-06): if the XML file's mtime is more than 30 days
behind ``time.time()`` at load, emit a single ``logger.info`` line urging
re-import. v2.0 ships log-only — the Settings → Library UI surface ships
in a later wave / v2.1.
"""

from __future__ import annotations

import logging
import os
import pickle
import time
import urllib.parse
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from vibemix.state.harmonics import to_camelot

__all__ = ["CuePoint", "RekordboxLibrary", "TempoNode", "TrackEntry"]


# Rekordbox export writes Rating as a byte from a fixed 6-value ladder; map it
# to a 0..5 star int. pyrekordbox 0.4.4 ALSO already int-coerces to 0..5 in
# some paths, so the table passes those through unchanged via the .get fallback.
_RATING_BYTE_TO_STARS: dict[int, int] = {0: 0, 51: 1, 102: 2, 153: 3, 204: 4, 255: 5}

# PositionMark.Type int -> label. pyrekordbox 0.4.4 already resolves this in its
# GETTERS, so mark.Type is usually a label string already; this table is the
# defensive fallback for a raw int (schema drift / older exports).
_CUE_TYPE_INT_TO_LABEL: dict[int, str] = {
    0: "cue",
    1: "fadein",
    2: "fadeout",
    3: "load",
    4: "loop",
}
_CUE_TYPE_LABELS: frozenset[str] = frozenset(_CUE_TYPE_INT_TO_LABEL.values())


logger = logging.getLogger("vibemix.library")


# Number of seconds in a 30-day window for the staleness nudge.
_STALE_AGE_SECONDS: int = 30 * 86400


def _is_user_library_cache_path(cache_path: Path) -> bool:
    """Return true for the production user cache location.

    Tests are allowed to cache fixture XML when they monkeypatch ``CACHE_PATH`` to
    an isolated tmp file. The real user cache is different: if it ever points at
    the repo fixture corpus, Viber/search will look "wired" while answering from
    fake tracks. Keep this path-shape based so tests can simulate a user cache
    without touching ``~/.cache``.
    """
    parts = cache_path.expanduser().parts
    return len(parts) >= 3 and parts[-3:-1] == (".cache", "vibemix") and parts[-1] in {
        "library.pkl",
        "library.pkl.v1bak",
    }


def _is_repo_test_fixture_source_path(source_path: str) -> bool:
    """Return true when a cache source points at this repo's test fixtures."""
    source = Path(source_path).expanduser()
    repo_root = Path(__file__).resolve().parents[3]
    try:
        relative = source.resolve(strict=False).relative_to(repo_root)
    except ValueError:
        if source.is_absolute():
            return False
        relative = source
    parts = relative.parts
    return "tests" in parts and "fixtures" in parts


def _quarantine_user_fixture_cache(cache_path: Path, source_path: str) -> Path | None:
    """Move a production cache that points at repo fixtures out of the hot path."""
    if not _is_user_library_cache_path(cache_path) or not _is_repo_test_fixture_source_path(
        source_path
    ):
        return None
    quarantine = cache_path.with_name(f"{cache_path.name}.fixturebak")
    if quarantine.exists():
        quarantine = cache_path.with_name(f"{cache_path.name}.fixturebak.{int(time.time())}")
    try:
        cache_path.replace(quarantine)
    except OSError as e:
        logger.warning(
            "library: failed to quarantine user cache pointing at repo test fixture "
            "%s: %s",
            source_path,
            e,
        )
        return None
    logger.warning(
        "library: quarantined user cache pointing at repo test fixture %s -> %s",
        source_path,
        quarantine,
    )
    return quarantine


@dataclass(frozen=True, slots=True)
class CuePoint:
    """A single Rekordbox cue / loop / fade / load marker.

    Field set is the union of ``pyrekordbox.rbxml.PositionMark`` attributes
    relevant to vibemix's grounding grammar, plus materialized source metadata
    from offline structure such as Rekordbox ANLZ.
    """

    name: str  # PositionMark.Name; "" when unlabeled
    type: str  # one of: "cue" | "loop" | "fadein" | "fadeout" | "load"
    start_s: float  # PositionMark.Start in seconds
    end_s: float | None  # PositionMark.End, loop end, or materialized section end
    number: int  # Num — 1..8 for hot cues, -1 for memory cues
    source: str = "dj"  # "dj" for XML cues, "anlz"/"auto" for materialized structure
    confidence: float | None = None


@dataclass(frozen=True, slots=True)
class TempoNode:
    """A single Rekordbox TEMPO beatgrid node (``Tempo.ATTRIBS``).

    One node = a constant-tempo grid; multiple nodes = a variable-tempo grid
    (live / unquantized tracks). ``inizio_s`` is the grid-anchor offset in
    seconds, ``battito`` the beat-in-bar phase (1..4 for 4/4) — together they
    give the first-downbeat phase for free. Absent TEMPO -> the owning
    ``TrackEntry.beatgrid`` is ``()`` (honest empty, never fabricated).
    """

    inizio_s: float  # Tempo.Inizio — grid-anchor offset in seconds
    bpm: float  # Tempo.Bpm — BPM at this anchor (variable grid detection)
    metro: str  # Tempo.Metro — meter, e.g. "4/4"; "" when absent
    battito: int  # Tempo.Battito — beat-in-bar phase (1..4 for 4/4)


@dataclass(frozen=True, slots=True)
class TrackEntry:
    """A Rekordbox track row joined with its position marks.

    Field set is INTENTIONALLY narrow: title / artist / album / bpm / key /
    duration / cues / filepath. Phase 26 prompt grounding consumes
    ``bpm``, ``key``, and ``cues`` directly; the other fields support
    Phase 25 Wave 3 UI (Settings → Library list view) but are kept here so
    a single source of truth for "what we know about this track" lives in
    one dataclass.

    All optional Rekordbox attributes coerce to typed empties on absence:
    missing ``AverageBpm`` becomes ``bpm = 0.0`` (NOT ``None``) so callers
    don't have to special-case the field.
    """

    track_id: str
    title: str
    artist: str
    album: str
    bpm: float
    key: str
    duration_s: float
    cues: tuple[CuePoint, ...]
    filepath: str
    # Plan 89-02 enrichment — additive, default-coerced (Invariant #3: missing
    # stays missing). The SCHEMA_VERSION bump invalidates stale v1 caches so
    # this widened shape never unpickles a short blob.
    genre: str = ""
    label: str = ""
    rating: int = 0  # 0..5 stars (Rekordbox byte ladder normalized)
    play_count: int = 0
    comments: str = ""
    camelot: str | None = None  # to_camelot(key) at parse; None on odd/empty key
    beatgrid: tuple[TempoNode, ...] = ()  # TEMPO nodes; () when absent


@dataclass(slots=True)
class _CacheBlob:
    """Internal pickle payload — versioned so v2.x can bump cleanly."""

    version: int
    xml_path: str
    xml_mtime: float
    tracks: dict[str, TrackEntry] = field(default_factory=dict)


class RekordboxLibrary:
    """One-shot ``collection.xml`` loader + in-memory track index.

    Attributes
    ----------
    tracks : dict[str, TrackEntry]
        Keyed by ``TrackEntry.track_id`` (the Rekordbox TrackID string).
        Empty until ``load_xml()`` or ``try_load_cache()`` succeeds.
    xml_path : str
        Source path of the most recent successful load. ``""`` before load.
    """

    SCHEMA_VERSION: int = 3  # bumped in sweep: CuePoint source/confidence widened
    STALE_AGE_DAYS: int = 30

    # Class attribute (NOT a default arg) so tests can monkeypatch the
    # cache location to an isolated tmpdir without polluting ~/.cache.
    CACHE_PATH: Path = Path.home() / ".cache" / "vibemix" / "library.pkl"

    def __init__(self) -> None:
        self.tracks: dict[str, TrackEntry] = {}
        self.xml_path: str = ""

    # ------------------------------------------------------------------ #
    # Loaders                                                             #
    # ------------------------------------------------------------------ #

    def load_xml(self, path: str | Path) -> int:
        """Parse ``collection.xml`` via pyrekordbox; populate ``self.tracks``.

        Returns the number of tracks loaded. Side effects:

        * Overwrites ``self.tracks`` and ``self.xml_path`` with fresh state.
        * Writes a pickle cache to ``CACHE_PATH`` for warm-start.
        * Emits a single ``logger.info`` line if the XML mtime is more than
          30 days behind ``time.time()`` (LIBRARY-06 staleness nudge).

        Raises whatever ``pyrekordbox.RekordboxXml`` raises on malformed
        input — vibemix v2.0 lets the wizard UI surface the error; we do
        not eat the exception here.
        """
        # Import inside the method so test fakes that pre-load pyrekordbox
        # before monkeypatching are unaffected; also keeps the module-level
        # import surface lean for tools that scan src/.
        from pyrekordbox import RekordboxXml

        path_str = str(path)
        xml = RekordboxXml(path_str)

        # Reset state — load_xml is idempotent but does NOT merge.
        self.tracks = {}
        self.xml_path = path_str

        for track in xml.get_tracks():
            entry = _track_to_entry(track)
            self.tracks[entry.track_id] = entry

        # Pickle cache — write after a successful parse so a partial parse
        # never leaves a stale-but-poison-shaped blob on disk.
        try:
            mtime = os.path.getmtime(path_str)
        except OSError:
            mtime = 0.0
        self._write_cache(path_str, mtime)

        # 30-day staleness nudge (LIBRARY-06). Log-only in v2.0 — Settings
        # UI ships later (LIBRARY-05).
        if mtime > 0:
            age_seconds = time.time() - mtime
            if age_seconds > _STALE_AGE_SECONDS:
                age_days = int(age_seconds // 86400)
                logger.info(
                    "library: collection.xml is %d days old — re-import via "
                    "Settings → Library when ready",
                    age_days,
                )

        return len(self.tracks)

    def try_load_cache(self) -> bool:
        """Attempt to populate ``self.tracks`` from the pickle cache.

        Returns ``True`` on a cache hit (cache exists, version matches,
        and the recorded XML mtime is at least as new as the on-disk
        mtime — i.e., the cache is not behind the source). Returns
        ``False`` on any failure mode (missing file, version mismatch,
        unpicklable blob, OSError on the source mtime stat). Failures
        are silent — callers are expected to fall through to
        ``load_xml()`` on False.

        Side effect on hit: overwrites ``self.tracks`` + ``self.xml_path``.
        On miss: ``self`` is unchanged.
        """
        cache_paths = (
            self.CACHE_PATH,
            self.CACHE_PATH.with_suffix(self.CACHE_PATH.suffix + ".v1bak"),
        )
        for cache_path in cache_paths:
            hit = self._try_load_cache_path(cache_path)
            if hit is None:
                continue
            self.tracks, self.xml_path = hit
            return True
        return False

    def _try_load_cache_path(self, cache_path: Path) -> tuple[dict[str, TrackEntry], str] | None:
        """Load one cache candidate.

        The primary cache stays strict for Rekordbox XML files. Folder-ingest
        caches are last-known snapshots, so a changed folder mtime must not make
        the live pill lose its library on startup.
        """
        if not cache_path.exists():
            return None
        try:
            with open(cache_path, "rb") as fh:
                blob: _CacheBlob = pickle.load(fh)
        except (pickle.PickleError, OSError, EOFError, AttributeError, ModuleNotFoundError):
            return None
        if not isinstance(blob, _CacheBlob):
            return None
        if blob.version not in (1, 2, self.SCHEMA_VERSION):
            return None
        if _is_user_library_cache_path(cache_path) and _is_repo_test_fixture_source_path(
            blob.xml_path
        ):
            _quarantine_user_fixture_cache(cache_path, blob.xml_path)
            return None
        # Mtime check: if the XML file on disk is NEWER than the cache,
        # the cache is stale — fall through.
        try:
            current_mtime = os.path.getmtime(blob.xml_path)
        except OSError:
            # Source missing — cache is technically usable (last-known
            # state), but for v2.0 we treat a missing source as a cache
            # miss so the wizard's "re-import" flow stays the source of
            # truth. Phase 25 Wave 3 may relax this.
            return None
        if current_mtime > blob.xml_mtime + 1.0 and not os.path.isdir(blob.xml_path):
            # 1.0s slack — file-system mtime resolution can drift slightly
            # under network mounts and APFS clones.
            return None
        return _coerce_cache_tracks(blob.tracks), blob.xml_path

    # ------------------------------------------------------------------ #
    # Reads                                                               #
    # ------------------------------------------------------------------ #

    def lookup_by_id(self, track_id: str) -> TrackEntry | None:
        """Return the TrackEntry for ``track_id`` or ``None`` when unknown."""
        return self.tracks.get(track_id)

    def __len__(self) -> int:
        return len(self.tracks)

    # ------------------------------------------------------------------ #
    # Internal                                                            #
    # ------------------------------------------------------------------ #

    def _write_cache(self, xml_path: str, xml_mtime: float) -> None:
        """Persist ``self.tracks`` to the pickle cache atomically.

        Atomic via temp-file + rename so a crash mid-write never produces
        a half-written cache. Silently swallows OSError (e.g., HOME dir
        unwritable in a sandboxed test env); the cache is a performance
        affordance, not a correctness requirement.
        """
        cache_path = self.CACHE_PATH
        try:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError:
            return
        blob = _CacheBlob(
            version=self.SCHEMA_VERSION,
            xml_path=xml_path,
            xml_mtime=xml_mtime,
            tracks=dict(self.tracks),
        )
        tmp_path = cache_path.with_suffix(cache_path.suffix + ".tmp")
        try:
            with open(tmp_path, "wb") as fh:
                pickle.dump(blob, fh, protocol=pickle.HIGHEST_PROTOCOL)
            os.replace(tmp_path, cache_path)
        except OSError:
            try:
                tmp_path.unlink(missing_ok=True)
            except OSError:
                pass


# ---------------------------------------------------------------------- #
# Track → TrackEntry conversion                                           #
# ---------------------------------------------------------------------- #


def _coerce_cache_tracks(tracks: dict[str, Any]) -> dict[str, TrackEntry]:
    """Normalize cache TrackEntry rows across schema bumps.

    v1 folder-ingest caches predate the enriched TrackEntry fields. Pickle can
    load those rows into the current class with missing slots, so rebuild every
    row through the current constructor and fill new fields with honest empties.
    """
    out: dict[str, TrackEntry] = {}
    for key, entry in tracks.items():
        track_id = str(getattr(entry, "track_id", key) or key)
        out[track_id] = TrackEntry(
            track_id=track_id,
            title=str(getattr(entry, "title", "") or ""),
            artist=str(getattr(entry, "artist", "") or ""),
            album=str(getattr(entry, "album", "") or ""),
            bpm=_coerce_float(getattr(entry, "bpm", 0.0), default=0.0),
            key=str(getattr(entry, "key", "") or ""),
            duration_s=_coerce_float(getattr(entry, "duration_s", 0.0), default=0.0),
            cues=_coerce_cue_points(getattr(entry, "cues", ()) or ()),
            filepath=str(getattr(entry, "filepath", "") or ""),
            genre=str(getattr(entry, "genre", "") or ""),
            label=str(getattr(entry, "label", "") or ""),
            rating=_coerce_int(getattr(entry, "rating", 0), default=0),
            play_count=_coerce_int(getattr(entry, "play_count", 0), default=0),
            comments=str(getattr(entry, "comments", "") or ""),
            camelot=getattr(entry, "camelot", None),
            beatgrid=tuple(getattr(entry, "beatgrid", ()) or ()),
        )
    return out


def _coerce_cue_points(cues: Any) -> tuple[CuePoint, ...]:
    """Normalize cue rows across cache schema bumps."""
    out: list[CuePoint] = []
    for cue in cues or ():
        out.append(
            CuePoint(
                name=str(getattr(cue, "name", "") or ""),
                type=str(getattr(cue, "type", "cue") or "cue"),
                start_s=_coerce_float(getattr(cue, "start_s", 0.0), default=0.0),
                end_s=(
                    _coerce_float(getattr(cue, "end_s", None), default=0.0)
                    if getattr(cue, "end_s", None) is not None
                    else None
                ),
                number=_coerce_int(getattr(cue, "number", -1), default=-1),
                source=str(getattr(cue, "source", "dj") or "dj"),
                confidence=(
                    _coerce_float(getattr(cue, "confidence", None), default=0.0)
                    if getattr(cue, "confidence", None) is not None
                    else None
                ),
            )
        )
    return tuple(out)


def _track_to_entry(track: Any) -> TrackEntry:
    """Convert a ``pyrekordbox.rbxml.Track`` element to a frozen TrackEntry.

    ``track`` is typed Any because the public pyrekordbox import surface
    does not re-export the ``Track`` class — see
    ``tests/library/test_rekordbox.py:test_load_xml_round_trip`` for the
    coverage that proves the duck-typed access works against real
    pyrekordbox 0.4.4 elements.
    """
    track_id = str(_safe_get(track, "TrackID", default="") or "")
    title = str(_safe_get(track, "Name", default="") or "")
    artist = str(_safe_get(track, "Artist", default="") or "")
    album = str(_safe_get(track, "Album", default="") or "")
    bpm_val = _safe_get(track, "AverageBpm", default=0.0)
    bpm = float(bpm_val) if bpm_val is not None else 0.0
    key = str(_safe_get(track, "Tonality", default="") or "")
    duration_val = _safe_get(track, "TotalTime", default=0)
    duration_s = float(duration_val) if duration_val is not None else 0.0
    location_raw = str(_safe_get(track, "Location", default="") or "")
    filepath = urllib.parse.unquote(location_raw)

    cues = tuple(_mark_to_cue(mark) for mark in getattr(track, "marks", []) or [])

    # --- Plan 89-02 enrichment (all default-coerced; never raise) --- #
    genre = str(_safe_get(track, "Genre", default="") or "")
    label = str(_safe_get(track, "Label", default="") or "")
    comments = str(_safe_get(track, "Comments", default="") or "")
    rating = _rating_to_stars(_safe_get(track, "Rating", default=0))
    play_count = _coerce_int(_safe_get(track, "PlayCount", default=0), default=0)
    # Camelot at parse via the deterministic harmonics table; raw key untouched.
    # to_camelot is total + honest-None — a false-confident key never surfaces.
    camelot = to_camelot(key) if key else None
    beatgrid = _track_to_beatgrid(track)

    return TrackEntry(
        track_id=track_id,
        title=title,
        artist=artist,
        album=album,
        bpm=bpm,
        key=key,
        duration_s=duration_s,
        cues=cues,
        filepath=filepath,
        genre=genre,
        label=label,
        rating=rating,
        play_count=play_count,
        comments=comments,
        camelot=camelot,
        beatgrid=beatgrid,
    )


def _track_to_beatgrid(track: Any) -> tuple[TempoNode, ...]:
    """Read the TEMPO beatgrid defensively; ``()`` when absent (honest empty).

    pyrekordbox 0.4.4 exposes the TEMPO children via ``track.tempos`` (a list
    of ``Tempo`` elements). Access is duck-typed + guarded so an older/odd
    export with no accessor degrades to an empty grid rather than raising.
    """
    nodes = _safe_get(track, "tempos", default=None)
    if not nodes:
        return ()
    out: list[TempoNode] = []
    for node in nodes:
        inizio = _coerce_float(_safe_get(node, "Inizio", default=0.0), default=0.0)
        bpm = _coerce_float(_safe_get(node, "Bpm", default=0.0), default=0.0)
        metro = str(_safe_get(node, "Metro", default="") or "")
        battito = _coerce_int(_safe_get(node, "Battito", default=1), default=1)
        out.append(
            TempoNode(inizio_s=inizio, bpm=bpm, metro=metro, battito=battito)
        )
    return tuple(out)


def _rating_to_stars(raw: Any) -> int:
    """Normalize a Rekordbox Rating to a 0..5 star int (never raises).

    The XML byte ladder is {0,51,102,153,204,255} -> 0..5 stars; pyrekordbox
    0.4.4 may already int-coerce to 0..5. Map a known byte, pass through an
    already-0..5 value, and clamp anything odd to 0 (Invariant #3 / T-89-05).
    """
    val = _coerce_int(raw, default=0)
    if val in _RATING_BYTE_TO_STARS:
        return _RATING_BYTE_TO_STARS[val]
    if 0 <= val <= 5:
        return val
    return 0  # odd/garbage value — honest 0, never raise


def _coerce_int(raw: Any, *, default: int) -> int:
    """int(raw) with a total fallback — never raises (T-89-05)."""
    if raw is None:
        return default
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def _coerce_float(raw: Any, *, default: float) -> float:
    """float(raw) with a total fallback — never raises (T-89-05)."""
    if raw is None:
        return default
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


def _mark_to_cue(mark: Any) -> CuePoint:
    """Convert a ``pyrekordbox.rbxml.PositionMark`` element to CuePoint."""
    name = str(_safe_get(mark, "Name", default="") or "")
    mark_type = _resolve_cue_type(_safe_get(mark, "Type", default=0))
    start_val = _safe_get(mark, "Start", default=0.0)
    start_s = float(start_val) if start_val is not None else 0.0
    end_val = _safe_get(mark, "End", default=None)
    end_s = float(end_val) if end_val is not None else None
    num_val = _safe_get(mark, "Num", default=-1)
    try:
        number = int(num_val) if num_val is not None else -1
    except (TypeError, ValueError):
        number = -1
    return CuePoint(
        name=name,
        type=mark_type,
        start_s=start_s,
        end_s=end_s,
        number=number,
    )


def _resolve_cue_type(raw: Any) -> str:
    """Map a PositionMark.Type to its label vocabulary; "cue" on unknown.

    pyrekordbox 0.4.4 already resolves the int -> label string in its GETTERS,
    so ``raw`` is usually one of {"cue","fadein","fadeout","load","loop"} —
    passed through unchanged. The defensive path int-coerces a raw int Type
    (schema drift / older exports) and maps it; anything unknown / odd falls
    back to "cue" (T-89-05 — never raise on a garbage Type).
    """
    if isinstance(raw, str) and raw in _CUE_TYPE_LABELS:
        return raw  # already a known label (the pyrekordbox 0.4.4 common case)
    type_int = _coerce_int(raw, default=0)
    return _CUE_TYPE_INT_TO_LABEL.get(type_int, "cue")


def _safe_get(obj: Any, attr: str, default: Any = None) -> Any:
    """Read ``attr`` off ``obj``; return ``default`` on AttributeError / None.

    pyrekordbox AbstractElement raises ``XmlAttributeKeyError`` for unset
    optional attributes; catching the broader Exception keeps the loader
    resilient against schema drift between Rekordbox 5/6/7 exports.
    """
    try:
        val = getattr(obj, attr)
    except Exception:
        return default
    if val is None:
        return default
    return val
