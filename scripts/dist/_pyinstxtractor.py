# SPDX-License-Identifier: Apache-2.0
"""scripts/dist/_pyinstxtractor.py — minimal in-house PyInstaller CArchive
extractor used by ``scripts.dist.verify_binary`` to unpack frozen modules
so the AIza-key scan can reach embedded source/bytecode.

Why in-house instead of vendoring upstream
------------------------------------------
The well-known upstream extractor (``extremecoders-re/pyinstxtractor``)
is licensed under GPL v3, which is incompatible with vibemix's Apache-2.0
distribution (any GPL-v3 file vendored into the tree would force the
combined work to GPL-v3). Plan 18-01 originally pointed at that upstream
under the assumption it was Unlicense/public-domain — that turned out to
be wrong, so we ship a minimal compatible-licensed extractor that covers
just the surface ``verify_binary`` needs.

Format reference
----------------
PyInstaller's CArchive layout (``cookie`` + table of contents + zipped
entries) is documented in PyInstaller's own source tree under
``PyInstaller/archive/readers.py`` (Apache-2.0 + portions GPL-with-
runtime-exception; the **format description** is freely usable). This
extractor implements the read side of that format only — no PyInstaller
internals, no GPL-derived code.

Cookie shape (PyInstaller 4.x .. 6.x):

    struct COOKIE {
        char magic[8];      // "MEI\014\013\012\013\016"
        uint32 lengthnHi;   // total archive length (high 32 bits)
        uint32 lengthnLo;   // total archive length (low 32 bits)
        uint32 toc;         // TOC offset from archive start
        uint32 tocLen;      // TOC byte length
        uint32 pyver;       // py version * 100 (or *1000 from 3.10+)
        char pylibname[64]; // libpython filename
    };

The cookie is the LAST occurrence of the magic in the file. The TOC is a
sequence of variable-length entries:

    struct ENTRY {
        uint32 entrySize;     // size of this entry in bytes
        uint32 offset;        // offset of payload from archive start
        uint32 cmprsdSize;    // compressed payload size
        uint32 uncmprsdSize;  // uncompressed payload size
        uint8  cmprsdFlag;    // 0 = raw, 1 = zlib
        uint8  typeCode;      // 's','m','M','b','x','z','Z','o',...
        char   name[entrySize - 18];
    };

We only care about: "given an archive file, write each entry's *raw*
bytes to disk under the entry name". We don't need to reconstruct
.pyc files (the byte regex doesn't care about magic headers — it just
scans bytes), so we skip the type-specific reassembly that the upstream
extractor does.

Library use only: importing this module never calls ``sys.exit``. The
``__main__`` block at the bottom is a tiny debugging convenience.
"""

from __future__ import annotations

import logging
import struct
import zlib
from dataclasses import dataclass
from pathlib import Path

__all__ = ["PyInstArchive", "TocEntry", "PYINST_MAGIC"]

_LOG = logging.getLogger(__name__)

# 8-byte PyInstaller cookie magic. Stable from PyInstaller 2.0 through 6.x.
PYINST_MAGIC: bytes = b"MEI\014\013\012\013\016"

# Search backwards in 8 KiB chunks for the cookie. PyInstaller bundles
# place the cookie near the end of the file, so this is fast in practice.
_TAIL_CHUNK = 8192


@dataclass(frozen=True)
class TocEntry:
    """A single TOC entry inside a PyInstaller CArchive."""

    name: str
    offset: int
    cmprsd_size: int
    uncmprsd_size: int
    cmprsd_flag: int  # 0 = raw, 1 = zlib
    type_code: str


class PyInstArchive:
    """Minimal reader for a PyInstaller CArchive.

    Usage::

        arc = PyInstArchive(Path("vibemix-core.exe"))
        if arc.open():
            try:
                arc.extract(Path("/tmp/extracted"))
            finally:
                arc.close()
    """

    def __init__(self, path: Path) -> None:
        self.path: Path = Path(path)
        self._fh = None  # type: ignore[var-annotated]
        self._archive_start: int = 0
        self._toc_offset: int = 0
        self._toc_len: int = 0
        self._py_version: int = 0
        self._entries: list[TocEntry] = []

    # ------------------------------------------------------------------ open

    def open(self) -> bool:
        """Locate the PyInstaller cookie and parse the TOC.

        Returns True if the file is a recognisable PyInstaller bundle,
        False otherwise. Never raises on a non-PyInstaller file.
        """
        try:
            self._fh = self.path.open("rb")
        except OSError as exc:
            _LOG.debug("cannot open %s: %s", self.path, exc)
            return False

        cookie_pos = self._find_cookie()
        if cookie_pos < 0:
            self.close()
            return False

        if not self._parse_cookie(cookie_pos):
            self.close()
            return False

        if not self._parse_toc():
            self.close()
            return False

        return True

    def close(self) -> None:
        if self._fh is not None:
            try:
                self._fh.close()
            except OSError:
                pass
            self._fh = None

    # -------------------------------------------------------------- cookie

    def _find_cookie(self) -> int:
        """Return the byte offset of the last cookie magic in the file,
        or -1 if absent. Scans backwards in overlapping chunks for speed.
        """
        assert self._fh is not None
        fh = self._fh
        fh.seek(0, 2)
        file_size = fh.tell()
        # Cookie is 24 + 64 = 88 bytes; magic is at offset 0.
        # The whole struct lives in roughly the last 88 bytes of the
        # archive (CArchive is appended to the bootloader). But other
        # PyInstaller layouts pad with extra bytes after the cookie, so
        # we sweep a generous tail window.
        sweep = min(file_size, 64 * 1024)
        pos = file_size - sweep
        if pos < 0:
            pos = 0
        fh.seek(pos)
        chunk = fh.read(sweep)
        idx = chunk.rfind(PYINST_MAGIC)
        if idx < 0:
            return -1
        return pos + idx

    def _parse_cookie(self, cookie_pos: int) -> bool:
        """Parse the 88-byte cookie at ``cookie_pos`` and record the
        archive boundary + TOC offset.
        """
        assert self._fh is not None
        fh = self._fh
        fh.seek(cookie_pos)
        raw = fh.read(88)
        if len(raw) < 24:
            return False
        # struct: 8s I I I I I 64s — big-endian
        # bytes 0-7   : magic
        # bytes 8-11  : lengthHi  (added in PyInstaller 5+; for older
        #               PyInstaller this slot holds the archive length
        #               and the high half is implicitly zero)
        # bytes 12-15 : lengthLo
        # bytes 16-19 : tocOffset
        # bytes 20-23 : tocLen
        # The "modern" cookie is 88 bytes (with pyver + pylibname); the
        # legacy cookie is 24 bytes. Both keep the first 24 bytes shaped
        # the same way: magic + length-hi + length-lo + toc + tocLen.
        magic, length_hi, length_lo, toc_off, toc_len = struct.unpack(
            ">8sIIII", raw[:24]
        )
        if magic != PYINST_MAGIC:
            return False

        # On PyInstaller 4.x the cookie has only 24+4+4 = 32 bytes; on
        # 5.x+ it grows to include pyver and pylibname. We tolerate
        # either by guarding the extra read.
        if len(raw) >= 32:
            try:
                pyver = struct.unpack(">I", raw[24:28])[0]
            except struct.error:
                pyver = 0
        else:
            pyver = 0

        archive_total = (length_hi << 32) | length_lo
        # archive_start = cookie_pos + 24 - archive_total ... but
        # historically the archive begins at the start of the bootloader
        # + (file_size - archive_total). Use file-size-relative form
        # which matches both layouts:
        assert self._fh is not None
        self._fh.seek(0, 2)
        file_size = self._fh.tell()
        self._archive_start = file_size - archive_total
        if self._archive_start < 0:
            # Defensive fallback: assume the archive starts at the
            # cookie's archive_total offset, not before file start.
            self._archive_start = 0
        self._toc_offset = self._archive_start + toc_off
        self._toc_len = toc_len
        self._py_version = pyver
        return True

    # ----------------------------------------------------------------- toc

    def _parse_toc(self) -> bool:
        """Read the TOC and populate ``self._entries``."""
        assert self._fh is not None
        fh = self._fh
        if self._toc_len <= 0:
            return False
        fh.seek(self._toc_offset)
        toc_bytes = fh.read(self._toc_len)
        if len(toc_bytes) < self._toc_len:
            return False

        entries: list[TocEntry] = []
        pos = 0
        while pos < self._toc_len:
            if pos + 18 > self._toc_len:
                break
            entry_size, off, cmprsd, uncmprsd, cmprsd_flag, type_code = struct.unpack(
                ">IIIIBB", toc_bytes[pos : pos + 18]
            )
            if entry_size <= 0 or entry_size > self._toc_len - pos:
                # Bad entry — stop, don't blow up.
                break
            name_bytes = toc_bytes[pos + 18 : pos + entry_size]
            # Names are NUL-padded; strip trailing zeros.
            name = name_bytes.split(b"\x00", 1)[0].decode("utf-8", errors="replace")
            try:
                type_char = chr(type_code)
            except ValueError:
                type_char = "?"
            entries.append(
                TocEntry(
                    name=name,
                    offset=self._archive_start + off,
                    cmprsd_size=cmprsd,
                    uncmprsd_size=uncmprsd,
                    cmprsd_flag=cmprsd_flag,
                    type_code=type_char,
                )
            )
            pos += entry_size

        self._entries = entries
        return True

    # ------------------------------------------------------------- extract

    @property
    def entries(self) -> list[TocEntry]:
        """Read-only view of parsed TOC entries (empty if not opened)."""
        return list(self._entries)

    def extract(self, out_dir: Path) -> None:
        """Write each entry's payload (uncompressed) into ``out_dir``.

        Names that contain ``..`` or absolute paths are sanitised — we
        strip leading slashes and drop any segment equal to ``..`` so a
        malicious archive can't escape ``out_dir`` (zip-slip class).
        """
        assert self._fh is not None, "open() must be called before extract()"
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        for entry in self._entries:
            safe_name = self._sanitize_name(entry.name)
            if not safe_name:
                continue
            payload = self._read_payload(entry)
            target = out_dir / safe_name
            target.parent.mkdir(parents=True, exist_ok=True)
            try:
                target.write_bytes(payload)
            except OSError as exc:
                _LOG.debug("cannot write %s: %s", target, exc)

    def _read_payload(self, entry: TocEntry) -> bytes:
        assert self._fh is not None
        fh = self._fh
        fh.seek(entry.offset)
        raw = fh.read(entry.cmprsd_size)
        if entry.cmprsd_flag:
            try:
                return zlib.decompress(raw)
            except zlib.error as exc:
                _LOG.debug("zlib decompress failed for %s: %s", entry.name, exc)
                # Return raw bytes anyway so the scanner still sees them.
                return raw
        return raw

    @staticmethod
    def _sanitize_name(name: str) -> str:
        """Strip absolute-path / zip-slip components from a TOC entry name."""
        if not name:
            return ""
        # Drop drive letters + leading separators.
        name = name.replace("\\", "/").lstrip("/")
        parts = [p for p in name.split("/") if p not in ("", ".", "..")]
        return "/".join(parts)


# --------------------------------------------------------------------- CLI

if __name__ == "__main__":
    # Tiny dev convenience — list entries; never used by tests or
    # verify_binary itself. Importing this module performs zero work.
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description="Debug helper: list TOC of a PyInstaller bundle.",
    )
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    arc = PyInstArchive(args.path)
    if not arc.open():
        print(f"not a PyInstaller bundle: {args.path}", file=sys.stderr)
        sys.exit(2)
    try:
        for ent in arc.entries:
            print(
                f"{ent.type_code} {ent.cmprsd_size:>10} {ent.uncmprsd_size:>10}  {ent.name}"
            )
    finally:
        arc.close()
