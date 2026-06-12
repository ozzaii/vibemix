# SPDX-License-Identifier: Apache-2.0
"""``library gig-check`` — read-only preflight verdict over a DJ library.

The 2026-06-11 research pack's one executable conclusion: DJs do not trust
their library under pressure, and the open lane is a preflight verdict — not
another organizer. This module audits a parsed Rekordbox collection and ends
in exactly one of three words: take_it / fix_first / do_not_take, with the
receipts that drove it.

Contract (the research's red lines, kept):
* READ-ONLY. This module never writes a library, a cache, or an audio file.
* Deterministic — pure scoring over parsed rows; no model calls, no network.
* Only the DJ's own prep counts as prep: cue debt scores ``source == "dj"``
  cues; anlz/auto-materialized suggestions never silence a debt signal.
* Honest absence: a missing duration disables the mix-out check rather than
  fabricating a warning.

"Library Doctor" stays an internal historical alias only — the public noun is
Gig Check (a competitor occupies "Music Library Doctor", and ``library
doctor`` here is already the environment self-check).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from vibemix.library.rekordbox import TrackEntry

SCHEMA = "vibemix.gig-check.v1"

# Issue codes — red blocks a track, yellow degrades it to warn.
RED_ISSUES = frozenset({"missing_file", "no_hot_cues"})
YELLOW_ISSUES = frozenset({"unlabeled_cues", "no_mix_out_anchor", "no_beatgrid"})

# A cue this far into the track (fraction of duration) anchors the exit.
MIX_OUT_FRACTION = 0.70
# Verdict ladder thresholds: blocked share that flips do_not_take, warn share
# that flips fix_first. Both deliberately conservative — the verdict's value
# is that a green answer is actually safe to trust at 1:40 a.m.
DO_NOT_TAKE_BLOCKED_RATIO = 0.30
FIX_FIRST_WARN_RATIO = 0.25

DEFAULT_BLOAT_THRESHOLD = 80
DEFAULT_TONIGHT_CAP = 40

_WS = re.compile(r"\s+")


@dataclass(frozen=True, slots=True)
class PlaylistRef:
    """A named playlist/crate and the track ids it references."""

    name: str
    track_ids: tuple[str, ...]


def _dedup_key(track: TrackEntry) -> tuple[str, str] | None:
    title = _WS.sub(" ", track.title.strip().lower())
    artist = _WS.sub(" ", track.artist.strip().lower())
    if not title:
        return None
    return (title, artist)


def _track_issues(track: TrackEntry) -> list[str]:
    # _resolve_local_path owns the file://localhost / pyrekordbox-stripped
    # leading-slash mess; None = no candidate resolves to a real file.
    from vibemix.library.ingest import _resolve_local_path

    issues: list[str] = []
    if _resolve_local_path(track.filepath) is None:
        issues.append("missing_file")

    # Only the DJ's own markers count as prep; materialized anlz/auto cues are
    # suggestions and must not silence the naked-track signal.
    prep_cues = [c for c in track.cues if c.source == "dj"]
    hot_cues = [c for c in prep_cues if c.number >= 1]
    if not hot_cues:
        issues.append("no_hot_cues")
    else:
        if all(not c.name.strip() for c in hot_cues):
            issues.append("unlabeled_cues")
        if track.duration_s > 0 and not any(
            c.start_s >= MIX_OUT_FRACTION * track.duration_s for c in prep_cues
        ):
            issues.append("no_mix_out_anchor")

    if not track.beatgrid:
        issues.append("no_beatgrid")
    return issues


def _status(issues: list[str]) -> str:
    if any(i in RED_ISSUES for i in issues):
        return "blocked"
    if issues:
        return "warn"
    return "ready"


def _track_ref(track: TrackEntry) -> dict[str, Any]:
    return {
        "track_id": track.track_id,
        "title": track.title,
        "artist": track.artist,
    }


def _prep_key(track: TrackEntry) -> tuple[int, int, int, int]:
    """How much DJ prep a copy carries — the duplicate-winner ranking."""
    dj_hot = sum(1 for c in track.cues if c.source == "dj" and c.number >= 1)
    return (dj_hot, 1 if track.beatgrid else 0, track.rating, track.play_count)


def _duplicate_group(group: list[TrackEntry]) -> dict[str, Any]:
    """One duplicate cluster with the keeper named, when one earns it.

    The winner must STRICTLY beat the runner-up on prep; equally naked (or
    equally prepped) copies get ``keep: None`` — an arbitrary pick would be
    a guess dressed as advice.
    """
    ranked = sorted(group, key=_prep_key, reverse=True)
    keep: str | None = None
    reason: str | None = None
    if _prep_key(ranked[0]) > _prep_key(ranked[1]):
        winner = ranked[0]
        dj_hot, has_grid, rating, plays = _prep_key(winner)
        bits = [f"{dj_hot} DJ hot cue(s)"]
        if has_grid:
            bits.append("a beatgrid")
        if rating:
            bits.append(f"rating {rating}")
        if plays:
            bits.append(f"{plays} plays")
        keep = winner.track_id
        reason = (
            f"this copy carries the prep ({', '.join(bits)}); "
            f"the other copies carry less"
        )
    return {
        "tracks": [_track_ref(t) for t in group],
        "keep": keep,
        "reason": reason,
    }


def audit_library(
    tracks: dict[str, TrackEntry],
    playlists: tuple[PlaylistRef, ...] | list[PlaylistRef] = (),
    *,
    bloat_threshold: int = DEFAULT_BLOAT_THRESHOLD,
    tonight_cap: int = DEFAULT_TONIGHT_CAP,
) -> dict[str, Any]:
    """Score every track and the library as a whole; return the verdict report.

    Pure and read-only: the only filesystem access is ``Path.exists`` on each
    track's audio path (the missing-file check itself).
    """
    cue_debt: list[dict[str, Any]] = []
    missing_files: list[dict[str, Any]] = []
    ready: list[TrackEntry] = []
    counts = {"ready": 0, "warn": 0, "blocked": 0}

    ordered = sorted(tracks.values(), key=lambda t: (t.title.lower(), t.track_id))
    for track in ordered:
        issues = _track_issues(track)
        status = _status(issues)
        counts[status] += 1
        if status == "ready":
            ready.append(track)
        if "missing_file" in issues:
            missing_files.append({**_track_ref(track), "filepath": track.filepath})
        if issues:
            cue_issues = [i for i in issues if i != "missing_file"]
            if cue_issues:
                cue_debt.append(
                    {**_track_ref(track), "issues": cue_issues, "status": status}
                )

    # Duplicates: normalized (title, artist) collisions, plus the g13/g14
    # winner call — "which duplicate has my cues?" beats a bare dupe list.
    groups: dict[tuple[str, str], list[TrackEntry]] = {}
    for track in ordered:
        key = _dedup_key(track)
        if key is not None:
            groups.setdefault(key, []).append(track)
    duplicates = [
        _duplicate_group(group) for group in groups.values() if len(group) > 1
    ]

    crate_bloat = [
        {
            "playlist": pl.name,
            "tracks": len(pl.track_ids),
            "threshold": bloat_threshold,
        }
        for pl in playlists
        if len(pl.track_ids) > bloat_threshold
    ]

    total = len(ordered)
    verdict, blockers = _verdict(total, counts, missing_files, cue_debt, crate_bloat)

    # Tonight crate: the safest high-trust subset, not "best songs".
    tonight = [
        {
            "track_id": t.track_id,
            "title": t.title,
            "artist": t.artist,
            "bpm": t.bpm,
            "key": t.key,
        }
        for t in sorted(ready, key=lambda t: (-t.rating, t.title.lower(), t.track_id))[
            :tonight_cap
        ]
    ]

    return {
        "schema": SCHEMA,
        "verdict": verdict,
        "totals": {"tracks": total, **counts},
        "blockers": blockers,
        "missing_files": missing_files,
        "cue_debt": cue_debt,
        "duplicates": duplicates,
        "crate_bloat": crate_bloat,
        "tonight": tonight,
        "params": {
            "bloat_threshold": bloat_threshold,
            "tonight_cap": tonight_cap,
            "playlists_seen": len(playlists),
        },
    }


def _verdict(
    total: int,
    counts: dict[str, int],
    missing_files: list[dict[str, Any]],
    cue_debt: list[dict[str, Any]],
    crate_bloat: list[dict[str, Any]],
) -> tuple[str, list[str]]:
    if total == 0:
        return "do_not_take", ["library is empty — nothing to trust"]

    blockers: list[str] = []
    if missing_files:
        blockers.append(f"{len(missing_files)} track(s) point at files that do not exist")
    naked = sum(1 for d in cue_debt if "no_hot_cues" in d["issues"])
    if naked:
        blockers.append(f"{naked} track(s) carry no DJ hot cues at all")
    if crate_bloat:
        names = ", ".join(b["playlist"] for b in crate_bloat[:3])
        blockers.append(f"{len(crate_bloat)} crate(s) too fat to use live ({names})")

    blocked_ratio = counts["blocked"] / total
    warn_ratio = counts["warn"] / total
    if blocked_ratio > DO_NOT_TAKE_BLOCKED_RATIO:
        return "do_not_take", blockers
    if counts["blocked"] > 0 or warn_ratio > FIX_FIRST_WARN_RATIO:
        return "fix_first", blockers
    return "take_it", blockers


# --- loader ------------------------------------------------------------------ #

SOURCE_KINDS = ("rekordbox", "serato", "traktor", "virtualdj", "engine")


def detect_source_kind(path: str | Path) -> str:
    """Sniff which DJ-software catalog a path points at, by shape.

    Raises ValueError (with the supported shapes) instead of guessing —
    a wrong parse would produce a confidently wrong verdict.
    """
    p = Path(path)
    if p.is_dir():
        if p.name == "_Serato_" or (p / "_Serato_").is_dir():
            return "serato"
        raise ValueError(
            f"cannot detect a DJ library in directory {p} — expected a "
            f"_Serato_ folder (or pass a catalog file: collection.xml, "
            f"collection.nml, database.xml, m.db)"
        )
    name = p.name.lower()
    if name == "database v2":
        return "serato"
    if p.suffix.lower() == ".nml":
        return "traktor"
    if name == "m.db":
        return "engine"
    if p.suffix.lower() == ".xml":
        # Sniff the root element from the head only — substring check, no
        # XML parse of untrusted input at detection time.
        with open(p, encoding="utf-8", errors="replace") as fh:
            head = fh.read(4096)
        if "<VirtualDJ_Database" in head:
            return "virtualdj"
        if "<DJ_PLAYLISTS" in head:
            return "rekordbox"
        raise ValueError(
            f"{p} is XML but neither a Rekordbox DJ_PLAYLISTS export nor a "
            f"VirtualDJ database"
        )
    raise ValueError(
        f"unrecognized library shape: {p} — supported: Rekordbox "
        f"collection.xml, Traktor collection.nml, VirtualDJ database.xml, "
        f"Engine m.db, a _Serato_ folder"
    )


def _serato_root(p: Path) -> Path | None:
    if p.is_file() and p.name.lower() == "database v2":
        return p.parent
    if p.is_dir() and p.name == "_Serato_":
        return p
    if p.is_dir() and (p / "_Serato_").is_dir():
        return p / "_Serato_"
    return None


def load_serato_crates(serato_root: Path) -> tuple[PlaylistRef, ...]:
    """Map ``_Serato_/Subcrates/*.crate`` onto PlaylistRef for crate bloat.

    Members are filepaths (Serato's native reference); the bloat layer only
    counts them, so no track-id join is needed.
    """
    from vibemix.library.sources.serato import iter_crates

    return tuple(
        PlaylistRef(name=name, track_ids=members)
        for name, members in iter_crates(serato_root)
    )


def _iter_source_tracks(kind: str, path: Path):
    """Build the matching LibrarySource pinned to ``path`` and yield tracks."""
    if kind == "serato":
        from vibemix.library.sources.serato import SeratoSource

        # Pin to the resolved _Serato_ dir — the natural CLI input is the
        # drive root CONTAINING it, which SeratoSource won't probe into.
        source = SeratoSource(library_path=str(_serato_root(path) or path))
    elif kind == "traktor":
        from vibemix.library.sources.traktor import TraktorSource

        source = TraktorSource(nml_path=str(path))
    elif kind == "virtualdj":
        from vibemix.library.sources.virtualdj import VirtualDJSource

        source = VirtualDJSource(database_path=str(path))
    elif kind == "engine":
        from vibemix.library.sources.engine import EngineDJSource

        source = EngineDJSource(database_path=str(path))
    else:  # pragma: no cover - guarded by SOURCE_KINDS check upstream
        raise ValueError(f"unknown source kind: {kind}")
    return source.iter_tracks()


def load_playlists(xml_path: str | Path) -> tuple[PlaylistRef, ...]:
    """Read playlist leaf nodes from a Rekordbox collection XML.

    ``RekordboxLibrary`` intentionally indexes tracks only; crate bloat needs
    the playlist layer, so it is walked here read-only via pyrekordbox (the
    parser the repo already trusts for this exact file — no stdlib ``xml``
    on user-supplied input).
    """
    from pyrekordbox.rbxml import RekordboxXml

    found: list[PlaylistRef] = []

    def _walk(node: Any) -> None:
        if node.is_playlist:
            track_ids = tuple(str(key) for key in node.get_tracks())
            found.append(PlaylistRef(name=str(node.name or ""), track_ids=track_ids))
            return
        for i in range(node.count):
            _walk(node.get_node(i))

    _walk(RekordboxXml(str(xml_path)).root_playlist_folder)
    return tuple(found)


def run_gig_check(
    xml_path: str | Path,
    *,
    source: str = "auto",
    bloat_threshold: int = DEFAULT_BLOAT_THRESHOLD,
    tonight_cap: int = DEFAULT_TONIGHT_CAP,
) -> dict[str, Any]:
    """Parse any supported DJ catalog and audit it.

    ``source`` is one of SOURCE_KINDS or "auto" (sniff by shape). Raises
    FileNotFoundError when the input itself is absent and ValueError when
    the shape cannot be recognized — a missing/unknown input is the
    caller's bug, not a verdict.
    """
    path = Path(xml_path)
    if not path.exists():
        raise FileNotFoundError(path)
    kind = detect_source_kind(path) if source == "auto" else source
    if kind not in SOURCE_KINDS:
        raise ValueError(
            f"unknown source '{kind}' — supported: {', '.join(SOURCE_KINDS)}"
        )

    playlists: tuple[PlaylistRef, ...] = ()
    if kind == "rekordbox":
        from vibemix.library.rekordbox import RekordboxLibrary

        library = RekordboxLibrary()
        library.load_xml(path)
        tracks = library.tracks
        playlists = load_playlists(path)
    else:
        tracks = {t.track_id: t for t in _iter_source_tracks(kind, path)}
        if kind == "serato":
            root = _serato_root(path)
            if root is not None:
                playlists = load_serato_crates(root)

    report = audit_library(
        tracks,
        playlists,
        bloat_threshold=bloat_threshold,
        tonight_cap=tonight_cap,
    )
    report["source"] = kind
    return report


# --- human report -------------------------------------------------------------- #

_VERDICT_LINES = {
    "take_it": "TAKE IT — this library is safe to walk in with",
    "fix_first": "FIX FIRST — playable, but tonight has known holes",
    "do_not_take": "DO NOT TAKE — this library will betray you in the booth",
}


def format_report(report: dict[str, Any]) -> str:
    """Render the verdict report as terminal text, doctor-style."""
    totals = report["totals"]
    lines = [
        f"vibemix Gig Check — {_VERDICT_LINES[report['verdict']]}",
        (
            f"tracks: {totals['tracks']} | ready {totals['ready']}"
            f" · warn {totals['warn']} · blocked {totals['blocked']}"
        ),
    ]
    for blocker in report["blockers"]:
        lines.append(f"  [!] {blocker}")
    if report["missing_files"]:
        lines.append("missing files:")
        for m in report["missing_files"]:
            lines.append(f"  [x] {m['title']} — {m['artist']}  ({m['filepath']})")
    if report["cue_debt"]:
        lines.append("cue debt:")
        for d in report["cue_debt"]:
            mark = "x" if d["status"] == "blocked" else "!"
            lines.append(
                f"  [{mark}] {d['title']} — {d['artist']}: {', '.join(d['issues'])}"
            )
    if report["duplicates"]:
        lines.append("duplicate suspects:")
        for group in report["duplicates"]:
            names = " / ".join(
                f"{t['title']} ({t['track_id']})" for t in group["tracks"]
            )
            lines.append(f"  [!] {names}")
            if group["keep"]:
                lines.append(f"      keep {group['keep']} — {group['reason']}")
    if report["crate_bloat"]:
        lines.append("crate bloat:")
        for b in report["crate_bloat"]:
            lines.append(
                f"  [!] {b['playlist']}: {b['tracks']} tracks"
                f" (live-usable threshold {b['threshold']})"
            )
    tonight = report["tonight"]
    if tonight:
        lines.append(f"tonight crate ({len(tonight)} ready tracks):")
        for t in tonight:
            key = f" {t['key']}" if t["key"] else ""
            lines.append(f"  [+] {t['title']} — {t['artist']}  {t['bpm']:g}{key}")
    return "\n".join(lines)
