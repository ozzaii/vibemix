# SPDX-License-Identifier: Apache-2.0
"""tests/dist/conftest.py — fixtures for verify_binary tests.

The fixtures construct synthetic ``.app`` directory trees + optionally
plant byte sequences that look like leaked API keys. Every planted
sequence is obviously-not-a-real-key (e.g. ``b"AIza" + b"A" * 35``) —
see ``tests/dist/fixtures/README.md`` for the policy.
"""

from __future__ import annotations

import struct
import zlib
from collections.abc import Callable, Iterable, Sequence
from pathlib import Path

import pytest

from scripts.dist import _pyinstxtractor


# ---------------------------------------------------------------------------
# Fake .app builder
# ---------------------------------------------------------------------------


_DEFAULT_PAYLOAD: bytes = b"clean payload\n" * 256  # ~3.5 KiB


@pytest.fixture
def make_fake_app(
    tmp_path: Path,
) -> Callable[..., Path]:
    """Factory fixture for building a fake macOS-style ``.app`` directory.

    Usage::

        app = make_fake_app(planted_bytes=b"AIza" + b"A" * 35)
        # → tmp_path/vibemix.app/Contents/MacOS/vibemix-core with the
        #   planted bytes spliced into the middle of the payload.
    """

    def _factory(
        name: str = "vibemix.app",
        planted_bytes: bytes | None = None,
        extra_files: Sequence[tuple[str, bytes]] = (),
        base_payload: bytes = _DEFAULT_PAYLOAD,
    ) -> Path:
        app = tmp_path / name
        macos = app / "Contents" / "MacOS"
        macos.mkdir(parents=True)
        if planted_bytes is None:
            payload = base_payload
        else:
            mid = len(base_payload) // 2
            payload = base_payload[:mid] + planted_bytes + base_payload[mid:]
        (macos / "vibemix-core").write_bytes(payload)
        for rel, data in extra_files:
            target = app / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        return app

    return _factory


# ---------------------------------------------------------------------------
# subprocess mock
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_subprocess(monkeypatch: pytest.MonkeyPatch) -> list[Sequence[str]]:
    """Record calls to ``subprocess.check_call`` made by verify_binary.

    Returns a mutable list of argv tuples — assert against it.
    """
    calls: list[Sequence[str]] = []

    def fake_check_call(cmd: Sequence[str], *args: object, **kwargs: object) -> int:
        calls.append(tuple(cmd))
        return 0

    # Patch the module's reference, which is what _inspect_msi captures
    # when ``runner=None``.
    import subprocess as _sp

    monkeypatch.setattr(_sp, "check_call", fake_check_call)
    return calls


# ---------------------------------------------------------------------------
# Synthetic PyInstaller archive
# ---------------------------------------------------------------------------


def _build_pyinstaller_archive_bytes(entries: Iterable[tuple[str, bytes]]) -> bytes:
    """Produce a tiny valid PyInstaller CArchive that the in-house
    extractor can read. Layout:

        [ payload 1 ][ payload 2 ]...[ TOC ][ cookie (88 bytes) ]

    Each payload is zlib-compressed (cmprsd_flag=1). The TOC is the
    concatenation of fixed-width 18-byte headers + NUL-terminated names.
    The cookie's archive_total is set to (file_size - 0) so
    archive_start resolves to 0.
    """
    payload_blob = bytearray()
    toc_blob = bytearray()
    entries_list = list(entries)

    # First pass: write payloads + collect (name, offset, csize, usize).
    records: list[tuple[str, int, int, int]] = []
    cursor = 0
    for name, raw in entries_list:
        compressed = zlib.compress(raw)
        records.append((name, cursor, len(compressed), len(raw)))
        payload_blob.extend(compressed)
        cursor += len(compressed)

    # Second pass: build TOC.
    for name, offset, csize, usize in records:
        name_bytes = name.encode("utf-8") + b"\x00"
        # Pad name to 4-byte align (matches real PyInstaller TOC).
        while len(name_bytes) % 4 != 0:
            name_bytes += b"\x00"
        entry_size = 18 + len(name_bytes)
        header = struct.pack(
            ">IIIIBB",
            entry_size,
            offset,
            csize,
            usize,
            1,  # cmprsd_flag
            ord("s"),  # type_code — generic 'source' entry
        )
        toc_blob.extend(header)
        toc_blob.extend(name_bytes)

    payload_section_size = len(payload_blob)
    toc_offset_within_archive = payload_section_size  # archive starts at 0
    toc_len = len(toc_blob)

    # PyInstaller 2.1+ cookie (88 bytes):
    #   magic[8] + lengthofPackage(u32) + tocOffset(u32)
    #   + tocLen(i32) + pyver(i32) + pylibname[64]
    archive_total = payload_section_size + toc_len + 88
    pyver = 312
    cookie = struct.pack(
        ">8sIIii64s",
        _pyinstxtractor.PYINST_MAGIC,
        archive_total,
        toc_offset_within_archive,
        toc_len,
        pyver,
        b"libpython3.12.dylib".ljust(64, b"\x00"),
    )

    return bytes(payload_blob + toc_blob + cookie)


@pytest.fixture
def fixture_pyinstaller_archive(tmp_path: Path) -> Callable[..., Path]:
    """Factory: build a synthetic PyInstaller archive at a tmp path.

    Usage::

        arc = fixture_pyinstaller_archive([("planted.pyc", b"AIza" + b"A" * 35)])
        # → tmp_path/synthetic.pyz
    """

    def _factory(
        entries: Iterable[tuple[str, bytes]] | None = None,
        name: str = "synthetic.pyz",
    ) -> Path:
        if entries is None:
            entries = [("hello.txt", b"clean content\n")]
        path = tmp_path / name
        path.write_bytes(_build_pyinstaller_archive_bytes(entries))
        return path

    return _factory
