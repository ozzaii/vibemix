# SPDX-License-Identifier: Apache-2.0
"""Cue export — write AI-placed hot cues (``CueAnchor``s) back to a
Rekordbox-importable XML via a NON-DESTRUCTIVE round-trip.

Data flow::

    auto-cue engine (cue_detect) → list[CueAnchor]
        → cue_anchor_to_mark_kwargs (pure CueAnchor → add_mark kwargs)
        → export_cues (one TRACK + N POSITION_MARKs in a fresh
          pyrekordbox.rbxml.RekordboxXml tree) → out_path "rekordbox xml"
        → the DJ imports that tree into their collection (never mutated
          in place — the import is additive on Rekordbox's side).

This is the last mile of the auto-cue *moat*: structural anchors the engine
placed (intro / build / breakdown / drop / outro) become real, colored hot-cue
pads in the DJ's player. We do NOT hand-roll ElementTree; ``pyrekordbox.rbxml.
RekordboxXml`` owns URI-encoding, the PositionMark Type bidict and Entries
bookkeeping (same engine as :mod:`vibemix.library.export_rekordbox`). It is
lazy-imported so the module import surface stays lean and tests can inject a
fake builder (no pyrekordbox needed to exercise the mapping + grounding gate).

Point-vs-loop choice (documented): a structural anchor is exported as a POINT
hot cue (``Type="cue"``, ``End=None``). A ``CueAnchor`` carries an ``end_s``
that defines the ≤80s *mixable window* — that is embedding/blend metadata, not
a Rekordbox loop region — so collapsing it to a point hot cue is the honest
mapping (a DJ presses the pad to jump to the anchor; the window is not a loop
they want auto-engaged). The kwargs builder leaves the ``loop`` door open
(``End`` is threaded through) for a future caller that explicitly wants loops.

Functions RETURN dicts and never raise — a bad input degrades to an
``{"error": ...}`` message instead of wedging the caller's loop (the toolset
handler contract).
"""

from __future__ import annotations

import logging
from typing import Any

from vibemix.library.cue_provenance import provenance_stamped_cue_name

__all__ = [
    "cue_anchor_to_mark_kwargs",
    "export_cues",
]

logger = logging.getLogger("vibemix.library")

# Each structural label → an RGB hot-cue pad color. Mirrors the dance-floor
# intuition: intro=green (go/load), build=yellow (tension rising),
# breakdown=blue (the calm), drop=red (the floor moment), outro=purple (tail).
# pyrekordbox 0.4.4's ``add_mark`` does NOT take Red/Green/Blue kwargs; we set
# them on the returned PositionMark object's RGB attributes after the call.
_LABEL_COLORS: dict[str, tuple[int, int, int]] = {
    "intro": (40, 226, 20),  # green
    "build": (224, 100, 27),  # amber/yellow
    "breakdown": (16, 104, 233),  # blue
    "drop": (230, 40, 40),  # red
    "outro": (155, 64, 224),  # purple
}

# Pad label shown on the hot cue. Uppercase = reads at a glance on the deck.
_LABEL_TO_MARK_NAME: dict[str, str] = {
    "intro": "INTRO",
    "build": "BUILD",
    "breakdown": "BREAKDOWN",
    "drop": "DROP",
    "outro": "OUTRO",
}


def cue_anchor_to_mark_kwargs(cue: Any, num: int) -> dict[str, Any]:
    """Pure mapping: one ``CueAnchor`` + a pad slot ``num`` → ``add_mark`` kwargs.

    Returns the kwargs ``pyrekordbox``'s ``track.add_mark`` accepts
    (``Name, Type, Start, End, Num``). A structural anchor is a POINT hot cue
    (``Type="cue"``, ``End=None``) — see the module docstring for why the
    ≤80s mixable window is NOT exported as a loop region.

    ``num`` is the 0-based hot-cue pad slot. ``Name`` falls back to the raw
    label upper-cased when the label is unknown (forward-compatible, never
    raises). No grounding here — this is the pure transform; ``export_cues``
    owns validation.
    """
    label = getattr(cue, "label", None)
    bare_name = _LABEL_TO_MARK_NAME.get(label, str(label).upper() if label else "CUE")
    name = provenance_stamped_cue_name(bare_name, getattr(cue, "source", "dj")) or "CUE"
    start = float(getattr(cue, "start_s", 0.0) or 0.0)
    return {
        "Name": name,
        "Type": "cue",
        "Start": start,
        "End": None,
        "Num": int(num),
    }


def export_cues(
    track_path: str,
    cues: list[Any],
    out_path: str,
    *,
    title: str | None = None,
    artist: str | None = None,
    bpm: float | None = None,
    xml_builder: Any | None = None,
) -> dict[str, Any]:
    """Write AI-placed ``CueAnchor``s as colored hot cues into a fresh
    Rekordbox-importable XML at ``out_path`` (non-destructive round-trip).

    Parameters
    ----------
    track_path
        The on-disk audio file the cues belong to (becomes the TRACK
        ``Location``; pyrekordbox URI-encodes it — never pre-encode).
    cues
        ``CueAnchor``s from the auto-cue engine. Empty → an error dict.
        Sorted by ``start_s`` before writing so pad slots (Num 0,1,2,…)
        ascend with the timeline.
    out_path
        Destination "rekordbox xml" file. The DJ imports this; their existing
        collection is never mutated in place.
    title, artist, bpm
        Optional TRACK metadata (Name / Artist / AverageBpm). Omitted from the
        ``add_track`` call when None so an absent field never lands as an empty
        attribute.
    xml_builder
        Optional injected builder for tests. When ``None``, lazy-imports
        ``pyrekordbox.rbxml.RekordboxXml`` and instantiates it. The builder
        MUST expose ``add_track(location, **kw) -> track`` (location POSITIONAL,
        matching pyrekordbox) where ``track`` has ``add_mark(**kwargs) -> mark``
        and ``mark`` has settable ``.Red/.Green/.Blue``; the real builder is
        saved via ``save(path=out_path)``.

    Returns
    -------
    dict
        ``{"exported": True, "path", "cue_count", "track_path"}`` on success;
        ``{"error": ...}`` on empty cues or any failure. NEVER raises.
    """
    if not cues:
        return {"error": "no cues to export"}

    try:
        if xml_builder is None:
            # Lazy import (matches export_rekordbox): keeps the module import
            # surface lean and lets the fake-builder tests run without
            # pyrekordbox installed.
            from pyrekordbox.rbxml import RekordboxXml

            xml = RekordboxXml(name="vibemix", version="1.0.0", company="Bravoh")
        else:
            xml = xml_builder

        # Build TRACK metadata kwargs: include a field ONLY when present.
        # NOTE: pyrekordbox's ``add_track(location, **kwargs)`` takes the file
        # path POSITIONALLY (not as a ``Location=`` kwarg — that raises
        # TypeError). Only Name/Artist/AverageBpm travel as kwargs.
        track_kwargs: dict[str, Any] = {}
        if title:
            track_kwargs["Name"] = str(title)
        if artist:
            track_kwargs["Artist"] = str(artist)
        if bpm is not None:
            try:
                track_kwargs["AverageBpm"] = float(bpm)
            except (TypeError, ValueError):
                pass

        track = xml.add_track(track_path, **track_kwargs)

        # Pad slots ascend with the timeline: sort by start, then Num 0,1,2,…
        ordered = sorted(cues, key=lambda c: float(getattr(c, "start_s", 0.0) or 0.0))
        for num, cue in enumerate(ordered):
            kwargs = cue_anchor_to_mark_kwargs(cue, num)
            mark = track.add_mark(**kwargs)
            # Color the hot cue via the RETURNED PositionMark's RGB attrs
            # (add_mark does NOT take Red/Green/Blue kwargs in 0.4.4).
            color = _LABEL_COLORS.get(getattr(cue, "label", None))
            if color is not None and mark is not None:
                r, g, b = color
                mark.Red = r
                mark.Green = g
                mark.Blue = b

        # Real RekordboxXml.save takes path=...; the fake records the call.
        xml.save(path=out_path)
    except Exception as e:
        logger.warning("[cue_export] export_cues failed: %s", e)
        return {"error": f"export_cues failed: {type(e).__name__}"}

    return {
        "exported": True,
        "path": out_path,
        "cue_count": len(cues),
        "track_path": track_path,
    }
