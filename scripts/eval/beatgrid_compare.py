# SPDX-License-Identifier: Apache-2.0
"""Offline BPM/beatgrid comparison for the beat-this candidate.

This is a dev-tooling bench, not product wiring. It compares the BPM a user
actually sees today (``estimate_bpm`` -> ``_stabilize_bpm`` -> optional
``validate_bpm``) against the Rust ``beat-this`` CLI on a truth-labeled real
DJ corpus. The output is a single JSON report and an exit code, mirroring
``scripts/eval/cue_detect.py``.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from statistics import median
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from vibemix.audio.buffers import AudioBuffer  # noqa: E402
from vibemix.audio.constants import INPUT_SR_TARGET  # noqa: E402
from vibemix.audio.features import estimate_bpm  # noqa: E402
from vibemix.library.audio_decode import load_audio_mono  # noqa: E402
from vibemix.state.genre.bpm_validator import validate_bpm  # noqa: E402
from vibemix.state.genre.profile import load_profile  # noqa: E402
from vibemix.state.refresh import _stabilize_bpm  # noqa: E402

DEFAULT_AUDIO_DIR = ROOT / "tests" / "bench" / "data"
DEFAULT_MANIFEST = DEFAULT_AUDIO_DIR / "bpm_truth_manifest.json"
DEFAULT_BEAT_THIS_BIN = "beat-this"

SCHEMA = "beatgrid_compare_v1"
OCTAVE_TOLERANCE = 0.02
RING_SAMPLES = 5
WINDOW_SECONDS = 6.0
HOP_SECONDS = 3.0
BEAT_THIS_TIMEOUT_S = 180.0

# The shipped product path must stay torch-free. These are the known lazy-only
# references that are allowed to exist today; this bench must not add another.
TORCH_FREE_CONTRACT = {
    "lazy_only_sites": [
        "src/vibemix/library/clap_engine.py:286 import torch",
        "src/vibemix/library/clap_engine.py:329 import torchaudio",
        "src/vibemix/agent/moss_tts/__init__.py:8 import torch",
    ],
    "do_not_add": ["torch", "torchaudio", "onnxruntime", "beat-this", "rten", "ort"],
}


class BeatThisError(RuntimeError):
    """The external beat-this CLI did not produce a parseable BPM."""


@dataclass(frozen=True)
class LiveBpmEstimate:
    raw_bpm: float
    post_guard_bpm: float
    guard_corrected: bool
    raw_ring: list[float]
    profile: str | None
    profile_found: bool
    duration_s: float | None = None


BeatThisRunner = Callable[[Path], Mapping[str, Any] | float | int]
LiveEstimator = Callable[[Mapping[str, Any], Path], LiveBpmEstimate]


def load_manifest(path: Path = DEFAULT_MANIFEST) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _as_float(value: object, *, field: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be numeric, got {value!r}") from exc
    if not np.isfinite(result):
        raise ValueError(f"{field} must be finite, got {value!r}")
    return result


def _load_tracks(manifest: Mapping[str, Any], *, manifest_path: Path) -> list[dict[str, Any]]:
    tracks = manifest.get("tracks")
    if not isinstance(tracks, list) or not tracks:
        raise ValueError(f"{manifest_path}: expected non-empty 'tracks' list")

    parsed: list[dict[str, Any]] = []
    for index, item in enumerate(tracks):
        if not isinstance(item, dict):
            raise ValueError(f"{manifest_path}: track {index} must be an object")
        filename = str(item.get("file") or "")
        if not filename:
            raise ValueError(f"{manifest_path}: track {index} missing file")
        truth_bpm = _as_float(item.get("truth_bpm"), field=f"tracks[{index}].truth_bpm")
        if truth_bpm <= 0.0:
            raise ValueError(f"{manifest_path}: track {index} truth_bpm must be > 0")
        row = dict(item)
        row["file"] = filename
        row["truth_bpm"] = truth_bpm
        parsed.append(row)
    return parsed


def octave_error(
    reported_bpm: float | int | None,
    truth_bpm: float | int,
    *,
    tolerance: float = OCTAVE_TOLERANCE,
) -> bool:
    """Return true for half/double/3:2/3:4 BPM aliases, excluding correct hits."""
    if reported_bpm is None:
        return False
    reported = float(reported_bpm)
    truth = float(truth_bpm)
    if reported <= 0.0 or truth <= 0.0:
        return False

    def close_to(target: float) -> bool:
        return abs(reported - target) / target <= tolerance

    if close_to(truth):
        return False
    aliases = (truth / 2.0, truth * 2.0, truth * 1.5, truth * 0.75)
    return any(close_to(alias) for alias in aliases if alias > 0.0)


def _abs_delta(value: float | None, truth: float) -> float | None:
    if value is None or value <= 0.0:
        return None
    return round(abs(float(value) - float(truth)), 6)


def _round_bpm(value: float | None) -> float | None:
    if value is None:
        return None
    return round(float(value), 3)


def _pcm_window_to_buffer(samples: np.ndarray, *, sr: int) -> AudioBuffer:
    buf = AudioBuffer(seconds=max(WINDOW_SECONDS, samples.size / float(sr), 0.25), sr=sr)
    pcm = np.clip(samples, -1.0, 1.0)
    buf.push(np.round(pcm * 32767.0).astype(np.int16))
    return buf


def estimate_live_post_guard_bpm(track: Mapping[str, Any], audio_path: Path) -> LiveBpmEstimate:
    """Reproduce the current live BPM counter path over representative windows."""
    samples = load_audio_mono(audio_path, target_sr=INPUT_SR_TARGET)
    duration_s = samples.size / float(INPUT_SR_TARGET)
    analysis_start_s = _as_float(track.get("analysis_start_s", 0.0), field="analysis_start_s")
    window_s = _as_float(track.get("window_seconds", WINDOW_SECONDS), field="window_seconds")
    hop_s = _as_float(track.get("hop_seconds", HOP_SECONDS), field="hop_seconds")
    window_samples = max(1, round(window_s * INPUT_SR_TARGET))
    max_start = max(0.0, duration_s - window_s)

    raw_ring: list[float] = []
    for i in range(RING_SAMPLES):
        start_s = min(max(0.0, analysis_start_s + (i * hop_s)), max_start)
        start = round(start_s * INPUT_SR_TARGET)
        end = min(samples.size, start + window_samples)
        segment = samples[start:end]
        if segment.size < INPUT_SR_TARGET * 2:
            raw_ring.append(0.0)
            continue
        buf = _pcm_window_to_buffer(segment, sr=INPUT_SR_TARGET)
        raw_ring.append(float(estimate_bpm(buf, seconds=window_s)))

    stabilized = float(_stabilize_bpm(raw_ring, previous=0.0, allow_far_switch=True))
    profile_name = track.get("genre_profile") or track.get("genre")
    profile = load_profile(str(profile_name)) if profile_name else None
    post_guard = stabilized
    corrected = False
    if profile is not None:
        post_guard, corrected = validate_bpm(stabilized, profile)

    return LiveBpmEstimate(
        raw_bpm=float(raw_ring[0]) if raw_ring else 0.0,
        post_guard_bpm=float(post_guard),
        guard_corrected=bool(corrected),
        raw_ring=[round(float(value), 3) for value in raw_ring],
        profile=str(profile_name) if profile_name else None,
        profile_found=profile is not None,
        duration_s=round(duration_s, 3),
    )


def parse_beat_this_bpm(payload: Mapping[str, Any] | float | int) -> float:
    if isinstance(payload, (int, float)):
        bpm = float(payload)
        if bpm > 0.0 and np.isfinite(bpm):
            return bpm
        raise BeatThisError(f"invalid beat-this bpm {payload!r}")

    def walk(value: Any) -> float | None:
        if isinstance(value, Mapping):
            for key in ("bpm", "tempo", "estimated_bpm", "beats_per_minute"):
                if key in value:
                    try:
                        bpm = float(value[key])
                    except (TypeError, ValueError):
                        bpm = 0.0
                    if bpm > 0.0 and np.isfinite(bpm):
                        return bpm
            for nested in value.values():
                found = walk(nested)
                if found is not None:
                    return found
        elif isinstance(value, list):
            for nested in value:
                found = walk(nested)
                if found is not None:
                    return found
        return None

    result = walk(payload)
    if result is None:
        raise BeatThisError("beat-this JSON did not contain bpm/tempo")
    return result


def _run_beat_this_cli(
    audio_path: Path,
    *,
    beat_this_bin: str = DEFAULT_BEAT_THIS_BIN,
    timeout_s: float = BEAT_THIS_TIMEOUT_S,
) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="vibemix-beat-this-") as tmp:
        out_path = Path(tmp) / f"{audio_path.stem}.json"
        argv = [beat_this_bin, str(audio_path), f"--json={out_path}"]
        try:
            proc = subprocess.run(
                argv,
                capture_output=True,
                text=True,
                timeout=timeout_s,
                check=False,
            )
        except FileNotFoundError as exc:
            raise BeatThisError(f"beat-this binary not found: {beat_this_bin}") from exc
        except subprocess.TimeoutExpired as exc:
            raise BeatThisError(f"beat-this timed out after {timeout_s:.1f}s") from exc

        if proc.returncode != 0:
            stderr = (proc.stderr or "").strip()
            raise BeatThisError(f"beat-this exited {proc.returncode}: {stderr[:240]}")
        if out_path.exists() and out_path.stat().st_size > 0:
            return json.loads(out_path.read_text(encoding="utf-8"))
        stdout = (proc.stdout or "").strip()
        if stdout:
            return json.loads(stdout)
    raise BeatThisError("beat-this produced neither --json file nor stdout JSON")


def _runner_for_cli(
    *,
    beat_this_bin: str,
    timeout_s: float,
) -> BeatThisRunner:
    def run(audio_path: Path) -> Mapping[str, Any]:
        return _run_beat_this_cli(
            audio_path,
            beat_this_bin=beat_this_bin,
            timeout_s=timeout_s,
        )

    return run


def _aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    live_deltas = [
        float(row["live_abs_delta"]) for row in rows if row.get("live_abs_delta") is not None
    ]
    beat_this_deltas = [
        float(row["beat_this_abs_delta"])
        for row in rows
        if row.get("beat_this_abs_delta") is not None
    ]
    live_errors = sum(1 for row in rows if row["live_octave_error"])
    beat_this_rows = [row for row in rows if row.get("beat_this_bpm") is not None]
    beat_this_errors = sum(1 for row in beat_this_rows if row["beat_this_octave_error"])
    new_failures = [
        row["file"]
        for row in beat_this_rows
        if row["beat_this_octave_error"] and not row["live_octave_error"]
    ]

    n_tracks = len(rows)
    beat_this_count = len(beat_this_rows)
    live_rate = live_errors / n_tracks if n_tracks else 0.0
    beat_this_rate = beat_this_errors / beat_this_count if beat_this_count else None
    live_median = round(float(median(live_deltas)), 6) if live_deltas else None
    beat_this_median = (
        round(float(median(beat_this_deltas)), 6) if beat_this_deltas else None
    )
    complete = beat_this_count == n_tracks
    ok = (
        complete
        and beat_this_rate is not None
        and live_median is not None
        and beat_this_median is not None
        and beat_this_rate <= live_rate / 2.0
        and beat_this_median <= 1.0
        and beat_this_median < live_median
        and not new_failures
    )
    return {
        "n_tracks": n_tracks,
        "beat_this_tracks": beat_this_count,
        "live_octave_errors": live_errors,
        "beat_this_octave_errors": beat_this_errors,
        "live_octave_error_rate": round(live_rate, 6),
        "beat_this_octave_error_rate": (
            round(float(beat_this_rate), 6) if beat_this_rate is not None else None
        ),
        "live_median_abs_delta": live_median,
        "beat_this_median_abs_delta": beat_this_median,
        "new_beat_this_octave_failures": new_failures,
        "ok": bool(ok),
    }


def evaluate_beatgrid(
    *,
    audio_dir: Path = DEFAULT_AUDIO_DIR,
    manifest_path: Path = DEFAULT_MANIFEST,
    beat_this_bin: str = DEFAULT_BEAT_THIS_BIN,
    beat_this_timeout_s: float = BEAT_THIS_TIMEOUT_S,
    beat_this_runner: BeatThisRunner | None = None,
    live_estimator: LiveEstimator = estimate_live_post_guard_bpm,
) -> dict[str, Any]:
    manifest = load_manifest(manifest_path)
    tracks = _load_tracks(manifest, manifest_path=manifest_path)
    runner = beat_this_runner or _runner_for_cli(
        beat_this_bin=beat_this_bin,
        timeout_s=beat_this_timeout_s,
    )

    rows: list[dict[str, Any]] = []
    for track in tracks:
        audio_path = audio_dir / str(track["file"])
        truth = float(track["truth_bpm"])
        live = live_estimator(track, audio_path)

        beat_this_payload: Mapping[str, Any] | float | int | None = None
        beat_this_bpm: float | None = None
        beat_this_error: str | None = None
        try:
            beat_this_payload = runner(audio_path)
            beat_this_bpm = parse_beat_this_bpm(beat_this_payload)
        except Exception as exc:
            beat_this_error = str(exc)[:240]

        live_delta = _abs_delta(live.post_guard_bpm, truth)
        beat_this_delta = _abs_delta(beat_this_bpm, truth)
        rows.append(
            {
                "file": str(track["file"]),
                "truth_bpm": _round_bpm(truth),
                "genre": track.get("genre"),
                "genre_profile": live.profile,
                "genre_profile_found": live.profile_found,
                "raw_estimate_bpm": _round_bpm(live.raw_bpm),
                "live_post_guard_bpm": _round_bpm(live.post_guard_bpm),
                "live_guard_corrected": live.guard_corrected,
                "live_raw_ring": live.raw_ring,
                "beat_this_bpm": _round_bpm(beat_this_bpm),
                "live_abs_delta": live_delta,
                "beat_this_abs_delta": beat_this_delta,
                "live_octave_error": octave_error(live.post_guard_bpm, truth),
                "beat_this_octave_error": octave_error(beat_this_bpm, truth),
                "beat_this_error": beat_this_error,
                "duration_s": live.duration_s,
            }
        )

    aggregates = _aggregate(rows)
    return {
        "schema": SCHEMA,
        "audio_dir": str(audio_dir),
        "manifest": str(manifest_path),
        "beat_this_bin": beat_this_bin,
        "accept_bar": {
            "beat_this_octave_rate_at_most_half_live": True,
            "beat_this_median_abs_delta_bpm_max": 1.0,
            "beat_this_median_abs_delta_lower_than_live": True,
            "no_new_octave_errors_where_live_is_correct": True,
        },
        "torch_free_contract": TORCH_FREE_CONTRACT,
        **aggregates,
        "rows": rows,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audio-dir", type=Path, default=DEFAULT_AUDIO_DIR)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--beat-this-bin", default=DEFAULT_BEAT_THIS_BIN)
    parser.add_argument("--beat-this-timeout-s", type=float, default=BEAT_THIS_TIMEOUT_S)
    args = parser.parse_args(argv)

    if not args.manifest.exists():
        print(
            f"beatgrid manifest not found: {args.manifest} "
            "(needs Kaan/Rekordbox truth BPMs)",
            file=sys.stderr,
        )
        return 2
    if shutil.which(args.beat_this_bin) is None:
        print(
            f"beat-this binary not found on PATH: {args.beat_this_bin} "
            "(install in the isolated bench env; do not add it to product deps)",
            file=sys.stderr,
        )
        return 2

    report = evaluate_beatgrid(
        audio_dir=args.audio_dir,
        manifest_path=args.manifest,
        beat_this_bin=args.beat_this_bin,
        beat_this_timeout_s=args.beat_this_timeout_s,
    )
    json.dump(report, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0 if report["ok"] else 1


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    raise SystemExit(main())
