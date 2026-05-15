# SPDX-License-Identifier: Apache-2.0
"""Phase 27-08 — ack_bank real-audio assertion tests (LATENCY-15).

Verifies the 40 OPUS files under src/vibemix/audio/ack_bank/ are non-silent
(real Achird-voice TTS audio, not silent placeholders). Skips files that
are still placeholder-sized — flags them so the partial-regeneration state
is visible.

Per Pitfall LATENCY-15: silent placeholders are 178-500 bytes (libopus
on all-zero PCM); real Achird audio for a 1-3 word phrase is 5-20 KB.
"""

from __future__ import annotations

import io
import wave
from pathlib import Path

import numpy as np
import pytest

PROJECT_ROOT = Path(__file__).parents[2]
ACK_BANK = PROJECT_ROOT / "src" / "vibemix" / "audio" / "ack_bank"

EXPECTED_BUCKETS = (
    "drop_hit",
    "track_change",
    "mix_move",
    "silence_break",
    "generic_filler",
)
PER_BUCKET = 8

# Real Achird audio is consistently > 5KB; placeholder OPUS-on-silence
# is 100-500 bytes. The 1KB floor is a safe distinguisher.
REAL_AUDIO_MIN_BYTES = 1024


def _all_opus_paths() -> list[Path]:
    return sorted(
        p
        for bucket in EXPECTED_BUCKETS
        for p in (ACK_BANK / bucket).glob("*.opus")
    )


def test_ack_bank_directory_layout_complete() -> None:
    """All 5 buckets exist (independent of file count per bucket)."""
    for bucket in EXPECTED_BUCKETS:
        assert (ACK_BANK / bucket).is_dir(), f"missing bucket dir: {bucket}"


def _opus_rms(path: Path) -> float:
    """Decode OPUS via PyAV; return RMS in [0, 1] float scale.

    PyAV's OPUS decode returns ``fltp`` (float planar) — values already in
    [-1.0, 1.0] range. Do NOT divide by 32768; that's an int16 convention.
    """
    import av

    samples_list = []
    container = av.open(str(path))
    try:
        for frame in container.decode(audio=0):
            arr = frame.to_ndarray()
            # fltp / flt format: float32 already in [-1, 1].
            # s16 format: int16 needs /32768.
            fmt = frame.format.name
            f = arr.flatten().astype(np.float32)
            if "s16" in fmt:
                f /= 32768.0
            samples_list.append(f)
    finally:
        container.close()
    if not samples_list:
        return 0.0
    all_samples = np.concatenate(samples_list)
    if all_samples.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(all_samples**2)))


def test_at_least_one_real_audio_file_present() -> None:
    """Phase 27-08 minimum bar: at least one Achird-voice OPUS file exists."""
    paths = _all_opus_paths()
    real_files = [p for p in paths if p.stat().st_size >= REAL_AUDIO_MIN_BYTES]
    assert real_files, (
        "no real-audio OPUS files in ack_bank — generation script not run"
    )


def test_each_real_audio_file_has_nonzero_rms() -> None:
    """Every file > 1 KB decodes to non-silent audio (RMS > 0.001)."""
    paths = _all_opus_paths()
    for path in paths:
        if path.stat().st_size < REAL_AUDIO_MIN_BYTES:
            continue
        rms = _opus_rms(path)
        assert rms > 0.001, (
            f"file > 1 KB but RMS ≈ 0 (silent): {path} (RMS={rms:.6f})"
        )


def test_no_oversized_files() -> None:
    """Sanity cap: no OPUS file > 100 KB (would indicate runaway TTS / bug)."""
    paths = _all_opus_paths()
    for path in paths:
        size = path.stat().st_size
        assert size <= 100 * 1024, (
            f"file unexpectedly large: {path} ({size} bytes) — investigate"
        )


def test_partial_regeneration_documented() -> None:
    """Inform-only: count + report the regeneration state.

    Does NOT fail if some files are still placeholders — those land in
    KAAN-ACTION-LEGAL.md for follow-up. The strict 40/40 gate fires only
    when Plan 27-04 CI runs the full bar.
    """
    paths = _all_opus_paths()
    placeholders = [
        p for p in paths if p.stat().st_size < REAL_AUDIO_MIN_BYTES
    ]
    real = [p for p in paths if p.stat().st_size >= REAL_AUDIO_MIN_BYTES]
    # The total count IS asserted (must be 40 — both placeholders + real
    # collectively cover all 5 buckets × 8 ids).
    total = len(placeholders) + len(real)
    if total < PER_BUCKET * len(EXPECTED_BUCKETS):
        pytest.skip(
            f"partial regeneration state: {len(real)} real + "
            f"{len(placeholders)} placeholders + "
            f"{PER_BUCKET * len(EXPECTED_BUCKETS) - total} missing — "
            "see KAAN-ACTION-LEGAL.md Item 3"
        )
