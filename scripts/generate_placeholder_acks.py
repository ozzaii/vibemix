# SPDX-License-Identifier: Apache-2.0
"""Generate 40 silent-OPUS placeholder ack samples for the AckBank.

Layout produced:
    src/vibemix/audio/ack_bank/<bucket>/<NN>.opus

Five buckets (drop_hit / track_change / mix_move / silence_break /
generic_filler) × 8 clips per bucket = 40 files. Each file is 100ms of
silence (4800 samples at 48kHz mono int16) encoded as OPUS in an OGG
container — the standard distribution form for short OPUS clips, readable
by ``av.open`` without extra ffmpeg flags.

KAAN-ACTION REQUIRED before v2.0 RC: replace the silent placeholders with
real Gemini Achird-voice TTS recordings (one ack per file, ~80-200ms each,
naturally compressed). The runtime path (loader + rotation + four-gate
``should_fire``) is fully testable on the silent payload — Kaan only swaps
file bytes when ready. See `.planning/NEXT-SESSION.md` "P19-04 followup"
and `tests/agent/test_ack_bank.py` for the invariants the replacement
recordings must continue to satisfy (8 per bucket; av-decodable OPUS;
~100ms duration ±10% — plan invariant on decoded length, not source).

Idempotent: invoking twice produces byte-identical files. The OPUS
encoder itself is deterministic on all-zero input; the OGG container's
per-page random ``bitstream_serial`` (4 bytes at offset 14-17 of every
page) is overwritten in a post-pass to a fixed value (0) and the page
CRC32 (4 bytes at offset 22-25, OGG-spec polynomial 0x04c11db7 over the
page with the CRC field zeroed) is recomputed. Without this rewrite,
re-running the generator produces files with different SHAs every time —
which would pollute the git diff and the PyInstaller bundle hash.

Usage:
    .venv/bin/python scripts/generate_placeholder_acks.py
"""

from __future__ import annotations

from pathlib import Path

import av
import numpy as np


# Bucket order locked to vibemix.agent.ack_bank.ACK_BUCKETS — the loader
# asserts each of these subdirs holds exactly PER_BUCKET .opus files.
BUCKETS: tuple[str, ...] = (
    "drop_hit",
    "track_change",
    "mix_move",
    "silence_break",
    "generic_filler",
)
PER_BUCKET: int = 8

# Resolve the in-tree bank dir from this script's location:
#   <repo>/scripts/generate_placeholder_acks.py
#   <repo>/src/vibemix/audio/ack_bank/
OUT_DIR: Path = Path(__file__).resolve().parent.parent / "src" / "vibemix" / "audio" / "ack_bank"

# 100ms of silence at 48kHz mono.
_SAMPLE_RATE = 48000
_SAMPLES = _SAMPLE_RATE // 10  # 4800

# OGG page header layout (Xiph framing spec):
#   0..3   "OggS" capture pattern
#   4      stream_structure_version (always 0)
#   5      header_type_flag
#   6..13  granule_position (signed 64 LE)
#   14..17 bitstream_serial_number (random per stream — non-deterministic)
#   18..21 page_sequence_number
#   22..25 CRC checksum (over the page with CRC field zeroed)
#   26     number_page_segments
#   27..   segment_table[number_page_segments], then body
#
# To make the encoded bytes deterministic across runs we patch every page's
# serial to 0 and recompute its CRC. CRC32 polynomial = 0x04C11DB7, init=0,
# no reflection, no final xor (specific to OGG; NOT zlib's CRC32).
_OGG_CRC_POLY = 0x04C11DB7


def _build_ogg_crc_table() -> list[int]:
    table: list[int] = []
    for byte in range(256):
        r = byte << 24
        for _ in range(8):
            if r & 0x80000000:
                r = ((r << 1) & 0xFFFFFFFF) ^ _OGG_CRC_POLY
            else:
                r = (r << 1) & 0xFFFFFFFF
        table.append(r & 0xFFFFFFFF)
    return table


_OGG_CRC_TABLE = _build_ogg_crc_table()


def _ogg_crc32(data: bytes) -> int:
    """OGG framing CRC32 — table-driven."""
    crc = 0
    for byte in data:
        crc = ((crc << 8) & 0xFFFFFFFF) ^ _OGG_CRC_TABLE[((crc >> 24) ^ byte) & 0xFF]
    return crc


def _patch_ogg_deterministic(data: bytes, serial: int = 0) -> bytes:
    """Rewrite every OGG page's serial to ``serial`` and recompute its CRC.

    Walks the byte stream page-by-page using the segment-table to advance.
    The output is a valid OGG bitstream (av.open round-trips it cleanly)
    that produces byte-identical output for byte-identical input.
    """
    out = bytearray(data)
    i = 0
    while i + 27 <= len(out) and out[i : i + 4] == b"OggS":
        page_segments = out[i + 26]
        seg_table_start = i + 27
        seg_table_end = seg_table_start + page_segments
        if seg_table_end > len(out):
            break
        body_len = sum(out[seg_table_start:seg_table_end])
        page_end = seg_table_end + body_len
        if page_end > len(out):
            break
        # 1. Overwrite serial number.
        out[i + 14 : i + 18] = serial.to_bytes(4, "little")
        # 2. Zero the CRC field, then compute over the entire page, then write back.
        out[i + 22 : i + 26] = b"\x00\x00\x00\x00"
        page_bytes = bytes(out[i:page_end])
        crc = _ogg_crc32(page_bytes)
        out[i + 22 : i + 26] = crc.to_bytes(4, "little")
        i = page_end
    return bytes(out)


def write_silent_opus(path: Path) -> None:
    """Write a 100ms silent-OPUS-in-OGG file at ``path``.

    Two-phase: (1) PyAV/libopus encode; (2) post-pass to make the OGG
    container deterministic (zero serial + recomputed CRCs). The
    libopus encoder is itself deterministic on all-zero input on a fixed
    (rate, layout, bitrate) configuration; only the OGG container's
    random per-stream serial number breaks byte-equality across runs.
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    samples = np.zeros(_SAMPLES, dtype=np.int16)

    container = av.open(str(path), "w", format="ogg")
    try:
        stream = container.add_stream("libopus", rate=_SAMPLE_RATE)
        stream.layout = "mono"

        # Reshape to (channels, samples) — av.AudioFrame.from_ndarray
        # convention for non-planar layouts.
        frame = av.AudioFrame.from_ndarray(samples.reshape(1, -1), format="s16", layout="mono")
        frame.rate = _SAMPLE_RATE
        frame.sample_rate = _SAMPLE_RATE

        for packet in stream.encode(frame):
            container.mux(packet)
        # Flush.
        for packet in stream.encode(None):
            container.mux(packet)
    finally:
        container.close()

    # Phase 2: deterministic OGG patch.
    raw = path.read_bytes()
    path.write_bytes(_patch_ogg_deterministic(raw, serial=0))


def main() -> None:
    written = 0
    for bucket in BUCKETS:
        bucket_dir = OUT_DIR / bucket
        bucket_dir.mkdir(parents=True, exist_ok=True)
        for i in range(1, PER_BUCKET + 1):
            write_silent_opus(bucket_dir / f"{i:02d}.opus")
            written += 1
    print(f"[ack-gen] wrote {written} placeholder OPUS files")


if __name__ == "__main__":
    main()
