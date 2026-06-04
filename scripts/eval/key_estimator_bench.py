# SPDX-License-Identifier: Apache-2.0
"""Bench vibemix's ingest-time key estimator on GiantSteps key annotations.

This is the accuracy gate before changing ``library/key_estimator.py``. It
scores the current ``estimate_key(path)`` output with MIREX key-task weights:
exact=1.0, fifth=0.5, relative=0.3, parallel=0.2, other/abstain=0.0.

The GiantSteps repo ships annotations and an audio downloader. If the audio is
missing, the bench reports ``status: no_audio`` and exits non-zero by default;
no bench number is invented from annotations alone.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from vibemix.library.key_estimator import KeyEstimate, estimate_key  # noqa: E402

SCHEMA = "key_estimator_bench_v1"
DEFAULT_DATASET_ROOT = (
    Path(os.environ.get("VIBEMIX_GIANTSTEPS_KEY_ROOT", ""))
    if os.environ.get("VIBEMIX_GIANTSTEPS_KEY_ROOT")
    else Path.home() / ".cache" / "vibemix" / "giantsteps-key" / "giantsteps-key-dataset"
)
AUDIO_EXTENSIONS = (".mp3", ".wav", ".flac", ".aif", ".aiff", ".m4a", ".ogg")
MIREX_WEIGHTS = {
    "exact": 1.0,
    "fifth": 0.5,
    "relative": 0.3,
    "parallel": 0.2,
    "other": 0.0,
    "abstained": 0.0,
}

_PC_BY_NAME = {
    "c": 0,
    "b#": 0,
    "c#": 1,
    "db": 1,
    "d": 2,
    "d#": 3,
    "eb": 3,
    "e": 4,
    "fb": 4,
    "e#": 5,
    "f": 5,
    "f#": 6,
    "gb": 6,
    "g": 7,
    "g#": 8,
    "ab": 8,
    "a": 9,
    "a#": 10,
    "bb": 10,
    "b": 11,
    "cb": 11,
}
_CANON_MAJOR = ("C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B")
_CANON_MINOR = tuple(f"{name}m" for name in _CANON_MAJOR)


@dataclass(frozen=True, slots=True)
class KeyLabel:
    pc: int
    mode: str

    @property
    def canonical(self) -> str:
        names = _CANON_MINOR if self.mode == "minor" else _CANON_MAJOR
        return names[self.pc % 12]


@dataclass(frozen=True, slots=True)
class Annotation:
    track_id: str
    key: KeyLabel


Estimator = Callable[[Path], KeyEstimate | None]


def _strip_giantsteps_prefix(text: str) -> str:
    parts = text.strip().split()
    if len(parts) >= 4 and parts[0].lower() == "key":
        return " ".join(parts[2:])
    return text.strip()


def parse_key_label(raw: str) -> KeyLabel:
    """Parse common GiantSteps/vibemix key names into pitch class + mode."""
    text = _strip_giantsteps_prefix(raw).replace("♯", "#").replace("♭", "b")
    text = text.replace(":", " ").strip()
    if not text:
        raise ValueError("empty key label")

    parts = text.split()
    if len(parts) >= 2 and parts[-1].lower() in {"major", "maj", "minor", "min"}:
        mode_token = parts[-1].lower()
        mode = "minor" if mode_token.startswith("min") else "major"
        tonic = "".join(parts[:-1])
    else:
        tonic = text
        lower = tonic.lower()
        if lower.endswith("min"):
            tonic = tonic[:-3]
            mode = "minor"
        elif lower.endswith("maj"):
            tonic = tonic[:-3]
            mode = "major"
        elif lower.endswith("m") and len(tonic) > 1:
            tonic = tonic[:-1]
            mode = "minor"
        else:
            mode = "major"

    tonic_key = tonic.strip().lower()
    if tonic_key not in _PC_BY_NAME:
        raise ValueError(f"unsupported key label {raw!r}")
    return KeyLabel(pc=_PC_BY_NAME[tonic_key], mode=mode)


def parse_estimate_label(estimate: KeyEstimate | None) -> KeyLabel | None:
    if estimate is None:
        return None
    return parse_key_label(estimate.musical)


def mirex_relation(reference: KeyLabel, predicted: KeyLabel | None) -> str:
    if predicted is None:
        return "abstained"
    ref_pc = reference.pc % 12
    pred_pc = predicted.pc % 12
    if predicted.mode == reference.mode and pred_pc == ref_pc:
        return "exact"
    if predicted.mode == reference.mode and (pred_pc - ref_pc) % 12 in {5, 7}:
        return "fifth"
    if predicted.mode != reference.mode:
        if reference.mode == "major" and predicted.mode == "minor" and pred_pc == (ref_pc - 3) % 12:
            return "relative"
        if reference.mode == "minor" and predicted.mode == "major" and pred_pc == (ref_pc + 3) % 12:
            return "relative"
        if pred_pc == ref_pc:
            return "parallel"
    return "other"


def mirex_score(reference: KeyLabel, predicted: KeyLabel | None) -> float:
    return MIREX_WEIGHTS[mirex_relation(reference, predicted)]


def _first_key_line(path: Path) -> str:
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            return stripped
    raise ValueError(f"{path}: no key annotation line")


def load_annotations(annotations_dir: Path, *, limit: int | None = None) -> list[Annotation]:
    paths = sorted(annotations_dir.glob("*.key"))
    if limit is not None:
        paths = paths[: max(0, int(limit))]
    annotations: list[Annotation] = []
    for path in paths:
        key = parse_key_label(_first_key_line(path))
        annotations.append(Annotation(track_id=path.stem, key=key))
    return annotations


def build_audio_index(audio_dir: Path) -> dict[str, Path]:
    if not audio_dir.exists():
        return {}
    files = (
        path
        for path in audio_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS
    )
    index: dict[str, Path] = {}
    for path in sorted(files):
        index.setdefault(path.stem, path)
    return index


def _round_float(value: float | None, digits: int = 6) -> float | None:
    if value is None:
        return None
    return round(float(value), digits)


def _mean(total: float, count: int) -> float | None:
    if count <= 0:
        return None
    return _round_float(total / count)


def evaluate_dataset(
    *,
    annotations_dir: Path,
    audio_dir: Path,
    limit: int | None = None,
    estimator: Estimator = estimate_key,
    include_tracks: bool = False,
) -> dict[str, Any]:
    annotations = load_annotations(annotations_dir, limit=limit)
    audio_index = build_audio_index(audio_dir)
    counts = {name: 0 for name in MIREX_WEIGHTS}
    missing_audio = 0
    attempted = 0
    emitted = 0
    score_sum = 0.0
    emitted_score_sum = 0.0
    track_rows: list[dict[str, Any]] = []

    for annotation in annotations:
        audio_path = audio_index.get(annotation.track_id)
        if audio_path is None:
            missing_audio += 1
            if include_tracks:
                track_rows.append(
                    {
                        "track_id": annotation.track_id,
                        "truth": annotation.key.canonical,
                        "status": "missing_audio",
                    }
                )
            continue

        attempted += 1
        estimate = estimator(audio_path)
        predicted = parse_estimate_label(estimate)
        relation = mirex_relation(annotation.key, predicted)
        score = MIREX_WEIGHTS[relation]
        counts[relation] += 1
        score_sum += score
        if predicted is not None:
            emitted += 1
            emitted_score_sum += score

        if include_tracks:
            track_rows.append(
                {
                    "track_id": annotation.track_id,
                    "truth": annotation.key.canonical,
                    "predicted": predicted.canonical if predicted else None,
                    "confidence": getattr(estimate, "confidence", None),
                    "relation": relation,
                    "score": score,
                }
            )

    status = "ok" if attempted else "no_audio"
    result: dict[str, Any] = {
        "schema": SCHEMA,
        "status": status,
        "dataset": "GiantSteps-604",
        "annotations_total": len(annotations),
        "audio_found": attempted,
        "audio_missing": missing_audio,
        "attempted": attempted,
        "emitted": emitted,
        "abstained": attempted - emitted,
        "coverage": _mean(float(attempted), len(annotations)),
        "emission_rate": _mean(float(emitted), attempted),
        "counts": counts,
        "mirex_weighted": _mean(score_sum, attempted),
        "mirex_weighted_emitted": _mean(emitted_score_sum, emitted),
        "exact_accuracy": _mean(float(counts["exact"]), attempted),
        "exact_accuracy_emitted": _mean(float(counts["exact"]), emitted),
        "weights": MIREX_WEIGHTS,
        "notes": {
            "parallel_credit": MIREX_WEIGHTS["parallel"],
            "missing_audio_not_scored": True,
            "source_path_redacted": True,
        },
    }
    if include_tracks:
        result["tracks"] = track_rows
    return result


def _default_annotations_dir(dataset_root: Path, annotation_set: str) -> Path:
    return dataset_root / "annotations" / annotation_set


def _render_human(result: dict[str, Any]) -> str:
    if result["status"] == "no_audio":
        return (
            "GiantSteps-604 key bench: no audio found. "
            f"annotations={result['annotations_total']} missing_audio={result['audio_missing']}"
        )
    return (
        "GiantSteps-604 key bench: "
        f"attempted={result['attempted']} emitted={result['emitted']} "
        f"weighted={result['mirex_weighted']} exact={result['exact_accuracy']} "
        f"counts={result['counts']}"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-root", type=Path, default=DEFAULT_DATASET_ROOT)
    parser.add_argument("--audio-dir", type=Path)
    parser.add_argument("--annotations-dir", type=Path)
    parser.add_argument("--annotation-set", choices=("giantsteps", "key"), default="giantsteps")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--json", action="store_true", help="print JSON instead of one-line text")
    parser.add_argument("--tracks", action="store_true", help="include per-track redacted rows")
    parser.add_argument("--output", type=Path, help="write the JSON report to this path")
    parser.add_argument(
        "--allow-empty",
        action="store_true",
        help="return 0 even when no audio was scored (for fixture/dry runs only)",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    dataset_root = Path(args.dataset_root).expanduser()
    audio_dir = Path(args.audio_dir).expanduser() if args.audio_dir else dataset_root / "audio"
    annotations_dir = (
        Path(args.annotations_dir).expanduser()
        if args.annotations_dir
        else _default_annotations_dir(dataset_root, args.annotation_set)
    )

    result = evaluate_dataset(
        annotations_dir=annotations_dir,
        audio_dir=audio_dir,
        limit=args.limit,
        include_tracks=bool(args.tracks),
    )
    payload = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
    print(payload if args.json else _render_human(result))
    if result["status"] == "no_audio" and not args.allow_empty:
        return 2
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
