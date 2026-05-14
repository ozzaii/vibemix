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

__all__ = ["CuePoint", "RekordboxLibrary", "TrackEntry"]


logger = logging.getLogger("vibemix.library")


# Number of seconds in a 30-day window for the staleness nudge.
_STALE_AGE_SECONDS: int = 30 * 86400


@dataclass(frozen=True, slots=True)
class CuePoint:
    """A single Rekordbox cue / loop / fade / load marker.

    Field set is the union of ``pyrekordbox.rbxml.PositionMark`` attributes
    relevant to vibemix's grounding grammar. ``end_s`` is set ONLY when
    ``type == "loop"``; for any other type the source XML has no End
    attribute and we record ``None``.
    """

    name: str  # PositionMark.Name; "" when unlabeled
    type: str  # one of: "cue" | "loop" | "fadein" | "fadeout" | "load"
    start_s: float  # PositionMark.Start in seconds
    end_s: float | None  # PositionMark.End (loop only); None otherwise
    number: int  # Num — 1..8 for hot cues, -1 for memory cues


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

    SCHEMA_VERSION: int = 1
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
        cache_path = self.CACHE_PATH
        if not cache_path.exists():
            return False
        try:
            with open(cache_path, "rb") as fh:
                blob: _CacheBlob = pickle.load(fh)  # noqa: S301 — owned user data
        except (pickle.PickleError, OSError, EOFError, AttributeError):
            return False
        if not isinstance(blob, _CacheBlob):
            return False
        if blob.version != self.SCHEMA_VERSION:
            return False
        # Mtime check: if the XML file on disk is NEWER than the cache,
        # the cache is stale — fall through.
        try:
            current_mtime = os.path.getmtime(blob.xml_path)
        except OSError:
            # Source missing — cache is technically usable (last-known
            # state), but for v2.0 we treat a missing source as a cache
            # miss so the wizard's "re-import" flow stays the source of
            # truth. Phase 25 Wave 3 may relax this.
            return False
        if current_mtime > blob.xml_mtime + 1.0:
            # 1.0s slack — file-system mtime resolution can drift slightly
            # under network mounts and APFS clones.
            return False
        self.tracks = dict(blob.tracks)
        self.xml_path = blob.xml_path
        return True

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
    )


def _mark_to_cue(mark: Any) -> CuePoint:
    """Convert a ``pyrekordbox.rbxml.PositionMark`` element to CuePoint."""
    name = str(_safe_get(mark, "Name", default="") or "")
    mark_type = str(_safe_get(mark, "Type", default="cue") or "cue")
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
