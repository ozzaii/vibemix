# SPDX-License-Identifier: Apache-2.0
"""Serato Markers2 cue tags - the portable cue carrier.

Serato and Mixxx understand hot cues from an audio file's Serato ``Markers2``
tags on track load, with no database write. That makes this a high-leverage cue
export for copies of the user's own files: the cue rides in the file, not in a
vendor database.

This module reimplements the Markers2 binary payload from the DOCUMENTED,
reverse-engineered format (github.com/Holzhaus/serato-tags) - it copies no code
from any GPL parser, keeping the Apache-2.0 tree clean. The container write uses
``mutagen`` (a GPL-2.0+ runtime dependency, lazy-imported, never vendored).

CUE entry layout (Serato Markers2):
    offset 0  : 1 byte   0x00 (unknown)
    offset 1  : 1 byte   hotcue index (0-based pad slot)
    offset 2  : 4 bytes  position ms - uint32 BIG-endian (sample-rate independent)
    offset 6  : 1 byte   0x00 (unknown)
    offset 7  : 3 bytes  RGB color
    offset 10 : 2 bytes  0x00 0x00 (unknown)
    offset 12 : N bytes  UTF-8 name, null-terminated
wrapped as:  b"CUE\\x00" + uint32_BE(len(body)) + body

The pure encoder/decoder is spec-byte-asserted + round-trip tested. Whether a
specific Mixxx/Serato/Rekordbox build renders the pad is a human eye-check -
green tests prove format conformance, not that product conclusion.
"""

from __future__ import annotations

import base64
import logging
from dataclasses import dataclass
from pathlib import Path

from vibemix.library.cue_provenance import provenance_stamped_cue_name

logger = logging.getLogger("vibemix.library")

_HEADER = b"\x01\x01"
# Spec: minimum total tag length is 470 bytes (null-padded after the base64).
_MIN_TAG_LEN = 470
_GEOB_DESC = "Serato Markers2"


@dataclass(frozen=True, slots=True)
class SeratoCue:
    """One Serato hot cue: pad ``index``, ``position_ms``, RGB ``color``, name."""

    index: int
    position_ms: int
    color: tuple[int, int, int]
    name: str = ""


def _cue_entry(cue: SeratoCue) -> bytes:
    """Encode one CUE marker entry (header name + length + body)."""
    r, g, b = cue.color
    body = (
        b"\x00"
        + bytes((cue.index & 0xFF,))
        + int(cue.position_ms).to_bytes(4, "big")
        + b"\x00"
        + bytes((r & 0xFF, g & 0xFF, b & 0xFF))
        + b"\x00\x00"
        + cue.name.encode("utf-8")
        + b"\x00"
    )
    return b"CUE\x00" + len(body).to_bytes(4, "big") + body


def _inner_blob(cues: list[SeratoCue]) -> bytes:
    """The decoded payload: header + CUE entries + single null terminator."""
    return _HEADER + b"".join(_cue_entry(c) for c in cues) + b"\x00"


def encode_markers2(cues: list[SeratoCue]) -> bytes:
    """Build the full Serato Markers2 GEOB object data for ``cues``."""
    b64 = base64.b64encode(_inner_blob(cues))
    # Spec: a linefeed every 72 base64 bytes.
    wrapped = b"\n".join(b64[i : i + 72] for i in range(0, len(b64), 72))
    data = _HEADER + wrapped
    if len(data) < _MIN_TAG_LEN:
        data += b"\x00" * (_MIN_TAG_LEN - len(data))
    return data


def _decode_inner(data: bytes) -> bytes:
    """Strip the outer header + null padding, de-wrap, and base64-decode."""
    body = data[2:].rstrip(b"\x00").replace(b"\n", b"")
    pad = (-len(body)) % 4
    if pad:
        body += b"=" * pad
    return base64.b64decode(body)


def decode_markers2(data: bytes) -> list[SeratoCue]:
    """Parse the CUE entries out of a Serato Markers2 payload (others ignored)."""
    inner = _decode_inner(data)
    cues: list[SeratoCue] = []
    pos = 2 if inner[:2] == _HEADER else 0
    n = len(inner)
    while pos < n:
        end = inner.find(b"\x00", pos)
        if end == -1:
            break
        name = inner[pos:end]
        if not name:  # empty name == terminator
            break
        if end + 5 > n:
            break
        length = int.from_bytes(inner[end + 1 : end + 5], "big")
        bstart = end + 5
        bend = bstart + length
        if bend > n:
            break
        if name == b"CUE" and length >= 12:
            cues.append(_parse_cue(inner[bstart:bend]))
        pos = bend
    return cues


def _parse_cue(body: bytes) -> SeratoCue:
    return SeratoCue(
        index=body[1],
        position_ms=int.from_bytes(body[2:6], "big"),
        color=(body[7], body[8], body[9]),
        name=body[12:].split(b"\x00", 1)[0].decode("utf-8", "replace"),
    )


# ---- cue_folder marks -> Serato cues (single-sourced colors) ------------------
_DEFAULT_COLOR = (0xCC, 0x00, 0x00)  # Serato's default cue red


def _name_colors() -> dict[str, tuple[int, int, int]]:
    """Mark-NAME -> RGB, reversed from the cue_export label maps (single source)."""
    from vibemix.library.cue_export import _LABEL_COLORS, _LABEL_TO_MARK_NAME

    colors = {}
    for label in _LABEL_TO_MARK_NAME:
        name = _LABEL_TO_MARK_NAME[label]
        colors[name] = _LABEL_COLORS[label]
        colors[f"VM {name}"] = _LABEL_COLORS[label]
    return colors


def marks_to_serato_cues(marks: list[dict]) -> list[SeratoCue]:
    """Map the cue_folder cue dicts (``{num, start_s, name}``) -> ``SeratoCue``s.

    Position is ``start_s x 1000`` ms (Serato cue positions are sample-rate
    independent, so no per-file SR is needed - unlike a direct mixxxdb write).
    Color comes from the same label palette the Rekordbox path uses.
    """
    colors = _name_colors()
    cues: list[SeratoCue] = []
    for mark in marks:
        name = provenance_stamped_cue_name(mark.get("name"), mark.get("source"))
        if name is None:
            continue
        cues.append(
            SeratoCue(
                index=int(mark.get("num", 0)),
                position_ms=round(float(mark.get("start_s", 0.0)) * 1000),
                color=colors.get(name, _DEFAULT_COLOR),
                name=name,
            )
        )
    return cues


def _merge_cues(
    existing: list[SeratoCue], new: list[SeratoCue]
) -> list[SeratoCue]:
    """Union by pad index - vibemix's cues win at their pads, every OTHER pad
    (a DJ's hand-set cue) is preserved. Never clobbers foreign cues."""
    by_index: dict[int, SeratoCue] = {c.index: c for c in existing}
    for c in new:
        by_index[c.index] = c
    return sorted(by_index.values(), key=lambda c: c.index)


# ---- container read/write (mutagen, ID3 GEOB) --------------------------------
_ID3_SUFFIXES = (".mp3", ".aif", ".aiff")


def _read_geob(path: Path) -> bytes | None:
    from mutagen.id3 import ID3, ID3NoHeaderError

    try:
        tags = ID3(path)
    except ID3NoHeaderError:
        return None
    for frame in tags.getall("GEOB"):
        if getattr(frame, "desc", "") == _GEOB_DESC:
            return bytes(frame.data)
    return None


def _write_geob(path: Path, data: bytes) -> None:
    from mutagen.id3 import GEOB, ID3, ID3NoHeaderError

    try:
        tags = ID3(path)
    except ID3NoHeaderError:
        tags = ID3()
    # Replace ONLY our Serato Markers2 GEOB; keep any other GEOB frames intact.
    keep = [f for f in tags.getall("GEOB") if getattr(f, "desc", "") != _GEOB_DESC]
    tags.delall("GEOB")
    for f in keep:
        tags.add(f)
    tags.add(
        GEOB(
            encoding=0,
            mime="application/octet-stream",
            desc=_GEOB_DESC,
            data=data,
        )
    )
    tags.save(path)


def read_serato_cues(path: Path | str) -> list[SeratoCue]:
    """Read existing Serato Markers2 cues from an audio file (``[]`` if none)."""
    data = _read_geob(Path(path))
    return decode_markers2(data) if data else []


def write_serato_cues(
    path: Path | str,
    cues: list[SeratoCue],
    *,
    merge: bool = True,
    allow_write: bool = False,
) -> dict:
    """Write ``cues`` into a file's Serato Markers2 tag (opt-in, merge-by-default).

    Writing MUTATES the user's audio file, so it is gated behind ``allow_write``
    (the CLI's ``--write-tags``). With ``merge=True`` (default) any cue the DJ
    set on a pad vibemix does not write is preserved - vibemix never clobbers a
    hand-set cue. Returns a status dict, never raises on the opt-in/format gate.
    """
    p = Path(path)
    if not allow_write:
        return {
            "written": False,
            "reason": "opt-in required: pass allow_write=True "
            "(the CLI --write-tags flag) - this writes into your audio file",
        }
    if p.suffix.lower() not in _ID3_SUFFIXES:
        return {
            "written": False,
            "reason": f"serato tag-write supports {list(_ID3_SUFFIXES)} in v1, "
            f"not {p.suffix!r} (FLAC/MP4 are a follow-up)",
        }
    try:
        final = _merge_cues(read_serato_cues(p), cues) if merge else list(cues)
        _write_geob(p, encode_markers2(sorted(final, key=lambda c: c.index)))
    except ModuleNotFoundError as exc:
        if exc.name and (exc.name == "mutagen" or exc.name.startswith("mutagen.")):
            return {
                "written": False,
                "reason": "serato tag-write needs the optional 'serato' extra "
                "(install with `uv sync --extra serato`)",
            }
        raise
    return {"written": True, "cue_count": len(final), "path": str(p)}


__all__ = [
    "SeratoCue",
    "decode_markers2",
    "encode_markers2",
    "marks_to_serato_cues",
    "read_serato_cues",
    "write_serato_cues",
]
