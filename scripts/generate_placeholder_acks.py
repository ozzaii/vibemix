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

Idempotent: invoking twice produces byte-identical files because the OPUS
encoder is deterministic on all-zero input. Recreates missing bucket
subdirectories on demand.

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


def write_silent_opus(path: Path) -> None:
    """Write a 100ms silent-OPUS-in-OGG file at ``path``.

    Idempotent: the OPUS encoder produces byte-identical output for an
    all-zero input on a fixed (rate, layout, bitrate) configuration.
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
