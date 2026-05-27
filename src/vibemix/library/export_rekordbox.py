# SPDX-License-Identifier: Apache-2.0
"""Vibe Mix export — turn a sequenced set into a Rekordbox-importable XML.

``export_set`` is the last mile of the sequencer: an ordered list of set
items → a self-contained ``collection.xml`` (``DJ_PLAYLISTS → PRODUCT +
COLLECTION + PLAYLISTS``). It is the ONLY portable format that carries
order **and** cues **and** beatgrid in a single file (research §C); M3U
carries order alone and is the neutral fallback elsewhere.

We do NOT hand-roll ElementTree — ``pyrekordbox.rbxml.RekordboxXml`` (pinned
0.4.4, installed ``--no-deps``; the write path is pure-stdlib ``xml.etree`` +
``bidict`` with ZERO SQLCipher coupling) owns URI encoding, the Rating byte
bidict, the PositionMark Type bidict, Entries bookkeeping, and the
TrackID/Location dedup cache. We feed it clean, grounded data.

Grounding / honesty contract (mirrors the rest of the codebase):
* ``Tonality`` is written as the CLASSICAL key via ``harmonics.to_classical``
  — NEVER the internal Camelot code (a Camelot tag in the XML is a silent
  corruption). An unknown / unresolvable Camelot OMITS ``Tonality`` rather
  than fabricating one.
* A track with a missing / empty ``filepath`` is SKIPPED (recorded in the
  returned ``ExportResult.dropped`` list) — the export never crashes on it.
* Dedup by on-disk location BEFORE ``add_track`` (the library raises
  ``XmlDuplicateError`` on a duplicate Location/TrackID): the same file
  appearing twice in the set adds ONE collection track and references its
  ``TrackID`` once per slot in the playlist, preserving set order.

Set-item shape (a plain ``Mapping``, e.g. a dict — the sequencer's output
row): ``track_id`` (str, opt), ``filepath`` (str), ``title``/``artist``
(str, opt), ``bpm`` (float, opt), ``camelot`` (internal code, opt),
``duration_s`` (float, opt), ``genre``/``colour`` (str, opt), ``rating``
(int 0-5, opt), ``cues`` (list of ``{name,type,start_s,end_s,num}``, opt),
``beatgrid`` (``{inizio,bpm,metro,battito}``, opt).

v1 scope: order + Tonality(classical)/BPM/TotalTime/Name/Artist/Genre/
Colour/Rating + memory & hot cues + a single constant-tempo TEMPO node.
Hot-cue COLOR is a known pyrekordbox 0.4.4 gap (``PositionMark.ATTRIBS`` has
no RGB) — Rekordbox assigns cue colors on import; we do not attempt RGB.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from vibemix.state.harmonics import to_classical

__all__ = ["ExportResult", "export_set"]

logger = logging.getLogger("vibemix.library")

# The subset of pyrekordbox PositionMark types we emit. The library's
# POSMARK_TYPE_MAPPING covers exactly these; anything else would raise
# ValueError inside add_mark, so we normalize unknown types to "cue".
_VALID_MARK_TYPES = frozenset({"cue", "fadein", "fadeout", "load", "loop"})


@dataclass(slots=True)
class ExportResult:
    """Outcome of an ``export_set`` call.

    ``path`` is the written file. ``written`` is the count of unique tracks
    placed in the COLLECTION; ``referenced`` is the count of playlist slots
    (>= ``written`` when a file repeats). ``dropped`` records each skipped
    item with a human-readable reason (currently only missing filepath) so a
    UI can surface "2 tracks skipped (no file)" honestly.
    """

    path: Path
    written: int = 0
    referenced: int = 0
    dropped: list[dict[str, Any]] = field(default_factory=list)

    def __fspath__(self) -> str:  # so it behaves like a path where convenient
        return str(self.path)

    def __eq__(self, other: Any) -> bool:
        # Callers commonly assert ``export_set(...) == out_path``; compare on
        # the written path so the result is ergonomic at the call site while
        # still carrying the dropped-list telemetry.
        if isinstance(other, ExportResult):
            return self.path == other.path
        if isinstance(other, (str, Path)):
            return self.path == Path(other)
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self.path)


def export_set(
    set_tracks: Sequence[Mapping[str, Any]],
    name: str,
    out_path: str | Path,
    *,
    library: Any = None,
) -> ExportResult:
    """Write an ordered, sequenced set to a Rekordbox-importable XML file.

    Parameters
    ----------
    set_tracks
        Ordered set items (the sequencer's output). Each is a Mapping; see
        the module docstring for the field set. ORDER is the contract — the
        playlist references tracks in exactly this order.
    name
        The playlist name shown under the Rekordbox "rekordbox xml" node.
    out_path
        Destination ``collection.xml`` path. Parent dirs are created.
    library
        Optional ``RekordboxLibrary`` for future enrichment (unused in v1 —
        accepted so callers can pass it without a signature change). The set
        items already carry everything v1 writes.

    Returns
    -------
    ExportResult
        Compares equal to ``out_path`` for call-site ergonomics; also carries
        ``written`` / ``referenced`` counts and the ``dropped`` list.
    """
    # Import inside the function (matches rekordbox.py): keeps the module
    # import surface lean and lets tests that prep pyrekordbox lazily work.
    from pyrekordbox.rbxml import RekordboxXml

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    xml = RekordboxXml(name="vibemix", version="1.0.0", company="Bravoh")
    pl = xml.add_playlist(name, keytype="TrackID")

    result = ExportResult(path=out)

    # Dedup by normalized on-disk location: the same file in two slots adds
    # ONE collection track but references its TrackID in both slots. We key
    # the cache the same way pyrekordbox does internally (os.path.normpath).
    location_to_id: dict[str, Any] = {}

    for item in set_tracks:
        filepath = item.get("filepath")
        if not filepath or not str(filepath).strip():
            # Honest skip — record it, never crash.
            result.dropped.append(
                {
                    "track_id": item.get("track_id"),
                    "title": item.get("title", ""),
                    "reason": "missing filepath",
                }
            )
            continue

        norm = os.path.normpath(str(filepath))
        track_id = location_to_id.get(norm)
        if track_id is None:
            track = _add_track(xml, item, filepath)
            track_id = track["TrackID"]
            location_to_id[norm] = track_id
            result.written += 1

        pl.add_track(track_id)
        result.referenced += 1

    xml.save(str(out))
    return result


def _add_track(xml: Any, item: Mapping[str, Any], filepath: Any) -> Any:
    """Add ONE collection TRACK from a set item; attach cues + beatgrid.

    ``location`` is passed as a plain path — the pyrekordbox setter
    URI-encodes it (never pre-encode). Only attributes in ``Track.ATTRIBS``
    may be passed as kwargs; we build the kwargs dict by including a field
    ONLY when present, so an absent field never lands as an empty attribute.
    """
    kwargs: dict[str, Any] = {}

    title = item.get("title")
    if title:
        kwargs["Name"] = str(title)
    artist = item.get("artist")
    if artist:
        kwargs["Artist"] = str(artist)
    genre = item.get("genre")
    if genre:
        kwargs["Genre"] = str(genre)
    colour = item.get("colour")
    if colour:
        kwargs["Colour"] = str(colour)

    bpm = item.get("bpm")
    if bpm is not None:
        try:
            kwargs["AverageBpm"] = float(bpm)
        except (TypeError, ValueError):
            pass

    duration_s = item.get("duration_s")
    if duration_s is not None:
        try:
            kwargs["TotalTime"] = round(float(duration_s))
        except (TypeError, ValueError):
            pass

    # Tonality MUST be the classical key, never the Camelot code. An
    # unresolvable Camelot omits the attribute (honest unknown).
    tonality = to_classical(item.get("camelot"))
    if tonality is not None:
        kwargs["Tonality"] = tonality

    track = xml.add_track(location=filepath, **kwargs)

    # Rating: the kwargs path bypasses the byte-mapping setter (it would
    # store the raw int), so set it via __setitem__ which runs
    # RATING_MAPPING.inv (0-5 → 0/51/.../255). Only for a valid 0-5 int.
    rating = item.get("rating")
    if rating is not None:
        try:
            r = int(rating)
        except (TypeError, ValueError):
            r = None
        if r is not None and 0 <= r <= 5:
            track["Rating"] = r

    _add_beatgrid(track, item.get("beatgrid"))
    _add_cues(track, item.get("cues"))
    return track


def _add_beatgrid(track: Any, beatgrid: Mapping[str, Any] | None) -> None:
    """Attach a single constant-tempo TEMPO node from a beatgrid dict.

    A single TEMPO node = constant tempo across the track (v1 scope). Sane
    defaults fill in when only ``bpm`` is known: ``inizio=0.0``,
    ``metro="4/4"``, ``battito=1``. A beatgrid without a usable bpm is
    skipped (no fabricated grid).
    """
    if not beatgrid:
        return
    bpm = beatgrid.get("bpm")
    if bpm is None:
        return
    try:
        bpm_f = float(bpm)
    except (TypeError, ValueError):
        return

    inizio = beatgrid.get("inizio", 0.0)
    try:
        inizio_f = float(inizio)
    except (TypeError, ValueError):
        inizio_f = 0.0

    metro = str(beatgrid.get("metro") or "4/4")

    battito = beatgrid.get("battito", 1)
    try:
        battito_i = int(battito)
    except (TypeError, ValueError):
        battito_i = 1

    track.add_tempo(Inizio=inizio_f, Bpm=bpm_f, Metro=metro, Battito=battito_i)


def _add_cues(track: Any, cues: Sequence[Mapping[str, Any]] | None) -> None:
    """Attach memory + hot cues (and loops) as POSITION_MARK elements.

    ``num`` is -1 for a memory cue, 0-7 for hot cues A-H. A ``loop`` type
    requires an ``end_s``; any other type ignores it. An unrecognized type
    degrades to ``"cue"`` rather than raising (the library's add_mark would
    ValueError on an unknown type).
    """
    if not cues:
        return
    for cue in cues:
        cue_type = str(cue.get("type") or "cue").lower()
        if cue_type not in _VALID_MARK_TYPES:
            cue_type = "cue"

        start = cue.get("start_s", 0.0)
        try:
            start_f = float(start)
        except (TypeError, ValueError):
            start_f = 0.0

        num = cue.get("num", -1)
        try:
            num_i = int(num)
        except (TypeError, ValueError):
            num_i = -1

        end_f: float | None = None
        if cue_type == "loop":
            end = cue.get("end_s")
            if end is not None:
                try:
                    end_f = float(end)
                except (TypeError, ValueError):
                    end_f = None

        track.add_mark(
            Name=str(cue.get("name") or ""),
            Type=cue_type,
            Start=start_f,
            End=end_f,
            Num=num_i,
        )
