# SPDX-License-Identifier: Apache-2.0
"""Phase 42 Plan 01 / GATE-01 — idempotent resume wrapper for the ack-bank.

This is a thin Kaan-discharge helper that wraps the existing Phase 27 / LATENCY-15
batch script ``scripts/generate_ack_audio.py``. It is quota-aware: by itself it
NEVER calls Gemini and spends $0. Its job is to:

1. Inspect which of the 40 ack-bank OPUS entries are present on disk and which
   are missing (the residual ``ACK-BANK-REMAINING-20`` set from Phase 27-08).
2. Print a Kaan-discharge oneliner that, when run with ``--really`` and an
   exported ``GEMINI_API_KEY``, subprocess-invokes the underlying batch script.

The actual TTS spend (~$0.10 against the free-tier quota when it resets) is
documented in ``KAAN-ACTION-LEGAL.md §GATE-01``. The script under
``scripts/generate_ack_audio.py`` already has skip-existing idempotency baked in
(see its ``_DEFAULT_OUTPUT`` + ``_generate_one`` skip path); this resume wrapper
just makes the inventory legible and gates the subprocess invocation behind
``--really`` so accidental dry-runs cannot spend quota.

Exit codes:
    0 — dry-run successful (default) or ``--really`` invocation completed.
    1 — manifest file missing / malformed JSON / bucket not allowed.

Usage::

    # Default (no spend) — print the missing-OPUS inventory.
    uv run python scripts/eval/generate_ack_audio_resume.py

    # Same as above but explicit.
    uv run python scripts/eval/generate_ack_audio_resume.py --dry-run

    # Kaan-discharge oneliner (Gemini TTS spend ~$0.10):
    GEMINI_API_KEY=... uv run python scripts/eval/generate_ack_audio_resume.py --really

See also: ``scripts/generate_ack_audio.py``, ``KAAN-ACTION-LEGAL.md §GATE-01``.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

# Project root resolves from this script's location:
#   <repo>/scripts/eval/generate_ack_audio_resume.py → <repo>/
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_MANIFEST = _PROJECT_ROOT / "assets" / "ack_bank" / "manifest.json"
DEFAULT_OUTPUT = _PROJECT_ROOT / "src" / "vibemix" / "audio" / "ack_bank"

# Path to the underlying batch generator that actually spends Gemini quota.
# Kept as a string so this module imports without google-genai available.
_BATCH_SCRIPT = _PROJECT_ROOT / "scripts" / "generate_ack_audio.py"


def list_missing_entries(
    manifest_path: Path,
    output_dir: Path,
) -> list[dict[str, str]]:
    """Return the manifest entries whose ``<bucket>/<id>.opus`` does NOT exist.

    Loads the 40-entry manifest (5 buckets × 8 ids) and walks each entry's
    expected output path under ``output_dir``. Does NOT call Gemini; safe to
    invoke without ``GEMINI_API_KEY`` set.

    Raises:
        FileNotFoundError: if the manifest path does not exist.
        ValueError: if the manifest is not a JSON list.
    """
    if not manifest_path.exists():
        raise FileNotFoundError(f"manifest not found: {manifest_path}")
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(
            f"manifest must be a JSON list; got {type(data).__name__}"
        )
    missing: list[dict[str, str]] = []
    for entry in data:
        bucket = entry.get("bucket")
        entry_id = entry.get("id")
        if not bucket or not entry_id:
            # Malformed entry — surface as missing so it is visible.
            missing.append(entry)
            continue
        out_path = output_dir / bucket / f"{entry_id}.opus"
        if not out_path.exists():
            missing.append(entry)
    return missing


def _print_inventory(
    manifest_path: Path,
    output_dir: Path,
    missing: list[dict[str, str]],
) -> None:
    """Print a human-readable inventory of present vs missing OPUS files."""
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        total = len(data) if isinstance(data, list) else 0
    except Exception:
        total = 0
    present = total - len(missing)
    print(
        f"[ack-resume] manifest={manifest_path} output={output_dir}",
        file=sys.stderr,
    )
    print(
        f"[ack-resume] present: {present}/{total} OPUS files",
        file=sys.stderr,
    )
    print(
        f"[ack-resume] missing: {len(missing)}/{total} OPUS files",
        file=sys.stderr,
    )
    for entry in missing:
        bucket = entry.get("bucket", "?")
        entry_id = entry.get("id", "?")
        print(f"  missing  {bucket}/{entry_id}.opus")
    print(
        "\n[ack-resume] To populate the missing entries (Kaan-discharge, ~$0.10):",
        file=sys.stderr,
    )
    print(
        "  GEMINI_API_KEY=... uv run python "
        "scripts/eval/generate_ack_audio_resume.py --really",
        file=sys.stderr,
    )
    print(
        "[ack-resume] See KAAN-ACTION-LEGAL.md §GATE-01 for the full runbook.",
        file=sys.stderr,
    )


def _invoke_batch(manifest_path: Path, output_dir: Path) -> int:
    """Subprocess-invoke the underlying batch generator.

    The batch script has its own ``--force`` / ``--dry-run`` / ``--bucket``
    flags; we deliberately do NOT forward those — this wrapper is the
    skip-existing-only path (Phase 27 idempotency contract).
    """
    if not _BATCH_SCRIPT.exists():
        print(
            f"[ack-resume] FATAL: batch script not found: {_BATCH_SCRIPT}",
            file=sys.stderr,
        )
        return 1
    if not os.environ.get("GEMINI_API_KEY", "").strip():
        print(
            "[ack-resume] FATAL: GEMINI_API_KEY not set; refusing to invoke "
            "the batch generator. Export the key first.",
            file=sys.stderr,
        )
        return 1
    cmd = [
        sys.executable,
        str(_BATCH_SCRIPT),
        "--manifest",
        str(manifest_path),
        "--output",
        str(output_dir),
    ]
    print(f"[ack-resume] exec: {' '.join(cmd)}", file=sys.stderr)
    result = subprocess.run(cmd, check=False)
    return result.returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="generate_ack_audio_resume",
        description=(
            "Phase 42 GATE-01 — quota-aware resume wrapper over "
            "scripts/generate_ack_audio.py. Default mode is dry-run "
            "(inventory only, $0 spend); pass --really to invoke the batch "
            "script (~$0.10 Gemini TTS spend, requires GEMINI_API_KEY)."
        ),
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help=(
            "Path to the 40-entry manifest JSON "
            "(default: assets/ack_bank/manifest.json)."
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=(
            "Output root for <bucket>/<id>.opus "
            "(default: src/vibemix/audio/ack_bank/)."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Print the missing-OPUS inventory and exit; never invoke Gemini. "
            "This is the DEFAULT mode if --really is not given."
        ),
    )
    parser.add_argument(
        "--really",
        action="store_true",
        help=(
            "Subprocess-invoke scripts/generate_ack_audio.py (skip-existing "
            "idempotent path). Requires GEMINI_API_KEY in the environment. "
            "Spends ~$0.10 of Gemini TTS free-tier quota."
        ),
    )
    args = parser.parse_args(argv)

    try:
        missing = list_missing_entries(args.manifest, args.output)
    except FileNotFoundError as e:
        print(f"[ack-resume] FATAL: {e}", file=sys.stderr)
        return 1
    except (ValueError, json.JSONDecodeError) as e:
        print(f"[ack-resume] FATAL: malformed manifest: {e}", file=sys.stderr)
        return 1

    # If --really is set, run the batch script. Otherwise dry-run.
    if args.really:
        if args.dry_run:
            # Mutually exclusive guard — be conservative: dry-run wins.
            print(
                "[ack-resume] WARN: both --really and --dry-run given; "
                "running dry-run.",
                file=sys.stderr,
            )
            _print_inventory(args.manifest, args.output, missing)
            return 0
        _print_inventory(args.manifest, args.output, missing)
        if not missing:
            print(
                "[ack-resume] nothing to do — 0 missing entries; "
                "exiting without Gemini call.",
                file=sys.stderr,
            )
            return 0
        return _invoke_batch(args.manifest, args.output)

    _print_inventory(args.manifest, args.output, missing)
    return 0


if __name__ == "__main__":
    sys.exit(main())
