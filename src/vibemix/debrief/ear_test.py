# SPDX-License-Identifier: Apache-2.0
"""Near-miss ear-test clip export.

The detector's timestamp is not the final gate. This helper writes a small WAV
slice from the recorded master so the user can actually hear the reported
gallop -> snap window before any UI polish depends on it.
"""

from __future__ import annotations

import wave
from pathlib import Path

from vibemix.debrief.near_miss_detector import NearMissResult

DEFAULT_NEAR_MISS_CLIP = "near_miss_ear_test.wav"


def write_near_miss_clip(
    session_dir: Path | str,
    near_miss: NearMissResult,
    *,
    output_path: Path | str | None = None,
    pad_s: float = 2.0,
) -> Path:
    """Write a bounded WAV clip around ``near_miss`` from ``input.wav``.

    The output preserves the recorded WAV's sample rate, channel count, and
    sample width. It copies bytes from disk instead of re-encoding so the
    by-ear gate hears the same master capture the detector analyzed.
    """

    session_path = Path(session_dir)
    source = session_path / "input.wav"
    if output_path is None:
        target = session_path / DEFAULT_NEAR_MISS_CLIP
    else:
        target = Path(output_path)
        if not target.is_absolute():
            target = session_path / target

    pad = max(0.0, float(pad_s))
    start_s = max(0.0, float(near_miss.window_start_s) - pad)
    end_s = max(start_s, float(near_miss.window_end_s) + pad)

    with wave.open(str(source), "rb") as src:
        channels = src.getnchannels()
        sample_width = src.getsampwidth()
        sample_rate = src.getframerate()
        total_frames = src.getnframes()
        start_frame = max(0, min(total_frames, int(start_s * sample_rate)))
        end_frame = max(start_frame, min(total_frames, int(end_s * sample_rate)))
        frame_count = max(0, end_frame - start_frame)
        src.setpos(start_frame)
        frames = src.readframes(frame_count)

    if not frames:
        raise ValueError("near-miss clip window contains no input.wav frames")

    target.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(target), "wb") as dst:
        dst.setnchannels(channels)
        dst.setsampwidth(sample_width)
        dst.setframerate(sample_rate)
        dst.writeframes(frames)
    return target


__all__ = ["DEFAULT_NEAR_MISS_CLIP", "write_near_miss_clip"]
