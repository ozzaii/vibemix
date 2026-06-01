# SPDX-License-Identifier: Apache-2.0
"""Real-audio auto-cue evaluation gate.

This is the cue-detection sibling of ``scripts/eval/clap_retrieval.py``:
it runs the shipped deterministic cue detector on committed in-repo MP3
fixtures, then checks a small manifest of expected labels and coarse timing
windows. No LLM, no mocked detector, no network.

The goal is a no-regression floor, not a benchmark claim. It catches the bad
class we keep tripping over: a cue pipeline that passes synthetic tests while
fabricating drops or losing obvious structure on real audio.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from vibemix.library.cue_detect import detect_cues  # noqa: E402

DEFAULT_AUDIO_DIR = ROOT / "tests" / "bench" / "data"
DEFAULT_FIXTURE_DIR = ROOT / "tests" / "library" / "fixtures" / "cue_real_corpus"
DEFAULT_MANIFEST = DEFAULT_FIXTURE_DIR / "manifest.json"


def load_manifest(path: Path = DEFAULT_MANIFEST) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def evaluate_cue_detection(
    *,
    audio_dir: Path = DEFAULT_AUDIO_DIR,
    manifest_path: Path = DEFAULT_MANIFEST,
    max_cues: int = 8,
) -> dict[str, Any]:
    """Run the real detector over the manifest and return metric rows."""
    manifest = load_manifest(manifest_path)
    tracks = manifest.get("tracks")
    if not isinstance(tracks, list) or not tracks:
        raise ValueError(f"{manifest_path}: expected non-empty 'tracks' list")

    rows: list[dict[str, Any]] = []
    expected_total = 0
    matched_total = 0
    unexpected_total = 0
    timing_miss_total = 0

    for track in tracks:
        if not isinstance(track, dict):
            raise ValueError(f"{manifest_path}: track entries must be objects")
        filename = str(track.get("file") or "")
        expected = track.get("expected")
        if not filename or not isinstance(expected, list) or not expected:
            raise ValueError(f"{manifest_path}: each track needs file + expected[]")

        audio_path = audio_dir / filename
        cues = detect_cues(audio_path, max_cues=max_cues)
        by_label: dict[str, list[dict[str, Any]]] = {}
        for cue in cues:
            by_label.setdefault(str(cue.label), []).append(
                {
                    "label": cue.label,
                    "start_s": round(float(cue.start_s), 3),
                    "end_s": round(float(cue.end_s), 3),
                    "confidence": round(float(cue.confidence), 6),
                }
            )

        allowed_labels = {str(item.get("label")) for item in expected if isinstance(item, dict)}
        detected_labels = set(by_label)
        unexpected = sorted(detected_labels - allowed_labels)
        unexpected_total += len(unexpected)

        matched: list[str] = []
        missing: list[str] = []
        timing_misses: list[dict[str, Any]] = []
        for item in expected:
            if not isinstance(item, dict):
                raise ValueError(f"{manifest_path}: expected entries must be objects")
            label = str(item.get("label") or "")
            if not label:
                raise ValueError(f"{manifest_path}: expected entry missing label")
            expected_total += 1
            candidates = by_label.get(label, [])
            if not candidates:
                missing.append(label)
                continue
            start_min = item.get("start_min_s")
            start_max = item.get("start_max_s")
            if start_min is None and start_max is None:
                matched.append(label)
                matched_total += 1
                continue
            lo = float(start_min)
            hi = float(start_max)
            if any(lo <= float(candidate["start_s"]) <= hi for candidate in candidates):
                matched.append(label)
                matched_total += 1
            else:
                timing_miss_total += 1
                timing_misses.append(
                    {
                        "label": label,
                        "expected_start_s": [lo, hi],
                        "detected_start_s": [candidate["start_s"] for candidate in candidates],
                    }
                )

        row_ok = not missing and not unexpected and not timing_misses
        rows.append(
            {
                "file": filename,
                "ok": row_ok,
                "detected": [cue for cues_for_label in by_label.values() for cue in cues_for_label],
                "matched": matched,
                "missing": missing,
                "unexpected": unexpected,
                "timing_misses": timing_misses,
            }
        )

    label_recall = matched_total / expected_total if expected_total else 0.0
    ok = (
        label_recall >= float(manifest.get("min_label_recall", 1.0))
        and unexpected_total <= int(manifest.get("max_unexpected_labels", 0))
        and timing_miss_total <= int(manifest.get("max_timing_misses", 0))
    )
    return {
        "schema": "cue_detect_eval_v1",
        "audio_dir": str(audio_dir),
        "manifest": str(manifest_path),
        "n_tracks": len(rows),
        "expected": expected_total,
        "matched": matched_total,
        "label_recall": round(label_recall, 6),
        "unexpected_labels": unexpected_total,
        "timing_misses": timing_miss_total,
        "ok": ok,
        "rows": rows,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audio-dir", type=Path, default=DEFAULT_AUDIO_DIR)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--max-cues", type=int, default=8)
    args = parser.parse_args(argv)

    if shutil.which("ffmpeg") is None:
        print("ffmpeg is required for cue detection eval", file=sys.stderr)
        return 2

    report = evaluate_cue_detection(
        audio_dir=args.audio_dir,
        manifest_path=args.manifest,
        max_cues=args.max_cues,
    )
    json.dump(report, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0 if report["ok"] else 1


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    raise SystemExit(main())
