# SPDX-License-Identifier: Apache-2.0
"""Write CueCandidates as Rekordbox PositionMarks into a fresh XML.

Non-destructive by construction: we emit a NEW collection.xml the DJ imports
into Rekordbox. We never touch the SQLCipher master.db (no stable/safe write
API — see GitHub discussion #113). If the chosen output path already exists,
we back it up first.

Confirmed pyrekordbox 0.4.4 API (Task 1 probe): ``add_track(location=...)``
(lowercase positional), ``add_mark(Name=, Type=, Start=, Num=)`` (capitalized),
``xml.save(path=...)``.
"""
from __future__ import annotations

import os
import shutil
import time
from collections import defaultdict
from pathlib import Path

from pyrekordbox import RekordboxXml

from spikes.vibe_mix_slice0.types import CueCandidate


def _rb_location(path: str) -> str:
    """Compensate for pyrekordbox's macOS path-encoding quirk.

    ``pyrekordbox.rbxml.encode_path`` emits ``"file://localhost/" + quote(path)``.
    On POSIX an absolute path begins with ``/``, so it yields a DOUBLE slash
    (``file://localhost//Users/...``) that does NOT match Rekordbox's own
    canonical ``file://localhost/Users/...`` form — and a mismatched Location
    means the import does not attach cues to the real file. Strip exactly one
    leading slash so the saved URI is canonical. (encode_path's docstring is
    Windows-centric, where paths look like ``C:/...`` and need no fix.)
    """
    if os.name == "posix" and path.startswith("/"):
        return path[1:]
    return path


def _backup_if_exists(out_path: Path) -> None:
    if out_path.exists():
        stamp = time.strftime("%Y%m%d-%H%M%S")
        shutil.copy2(out_path, out_path.with_name(f"{out_path.name}.bak-{stamp}"))


def write_cues(candidates: list[CueCandidate], out_path: str) -> int:
    """Emit a Rekordbox XML carrying ``candidates`` as PositionMarks.

    Returns the number of marks written. Backs up ``out_path`` first if it
    exists. One ``<TRACK>`` per distinct ``track_location``; each candidate
    becomes one ``add_mark`` on its track.
    """
    target = Path(out_path)
    _backup_if_exists(target)

    by_track: dict[str, list[CueCandidate]] = defaultdict(list)
    for c in candidates:
        by_track[c.track_location].append(c)

    xml = RekordboxXml()
    written = 0
    for location, cues in by_track.items():
        track = xml.add_track(location=_rb_location(location))
        for c in cues:
            track.add_mark(Name=c.name, Type=c.type, Start=c.start_s, Num=c.number)
            written += 1

    xml.save(path=str(target))
    return written
