# SPDX-License-Identifier: Apache-2.0
"""Phase 42 Plan 01 / GATE-02 — one-time VCR cassette population helper.

The Phase 27 eval test suite (tests/eval/test_judge_pro_rubric.py,
test_judge_flash_rubric.py, test_cited_relevance.py, test_substance_metric.py)
depends on recorded VCR cassettes under ``tests/eval/cassettes/`` to let CI
replay Gemini API responses at $0 cost on every PR. Phase 27 shipped the
scaffolding; cassette population is a one-time Kaan-discharge step that needs
a real ``GEMINI_API_KEY`` and burns ~$1-2 of API budget across the suite.

This helper:

1. Discovers the VCR-decorated tests under ``tests/eval/`` (heuristic grep for
   ``vcr`` / ``cassette`` / ``cassette_library_dir`` references).
2. Prints a Kaan-discharge oneliner that, when run with ``--really`` and an
   exported ``GEMINI_API_KEY``, subprocess-invokes pytest with
   ``VCR_RECORD_MODE=new_episodes``.

The script itself NEVER produces cassette bytes in default mode; it is a typed
wrapper documenting the one-time discharge. See ``KAAN-ACTION-LEGAL.md §GATE-02``
for the full runbook.

Exit codes:
    0 — dry-run successful (default) or ``--really`` invocation completed.
    1 — ``--really`` requested but ``GEMINI_API_KEY`` missing, or pytest absent.

Usage::

    # Default (no spend) — print the VCR-decorated test inventory.
    uv run python scripts/eval/record_cassettes.py

    # Kaan-discharge oneliner (Gemini API spend ~$1-2):
    GEMINI_API_KEY=... uv run python scripts/eval/record_cassettes.py \\
        --really --record-mode new_episodes

See also: ``.github/workflows/eval.yml`` (nightly canary uses
``VCR_RECORD_MODE=none`` against the populated cassettes).
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

# Project root resolves from this script's location:
#   <repo>/scripts/eval/record_cassettes.py → <repo>/
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_TEST_DIR = _PROJECT_ROOT / "tests" / "eval"
DEFAULT_CASSETTE_DIR = _PROJECT_ROOT / "tests" / "eval" / "cassettes"

# Heuristic regex for VCR-decorated test files. Matches:
#   - Direct VCR decorators (``@vcr.use_cassette``)
#   - VCR config tokens (``cassette_library_dir``, ``VCR_RECORD_MODE``)
#   - VCR libraries (``vcrpy``, ``pytest-recording``)
#   - Standalone tokens (``cassette[s]``, ``vcr``) — catches Phase 27 module
#     docstrings that say "VCR cassettes (deferred to ...)".
_VCR_HINTS = re.compile(
    r"@vcr\.use_cassette|cassette_library_dir|VCR_RECORD_MODE|vcr_cassette|"
    r"vcrpy|pytest-recording|\bcassettes?\b|\bvcr\b",
    re.IGNORECASE,
)


def discover_vcr_tests(test_dir: Path) -> list[str]:
    """Glob ``test_*.py`` under ``test_dir`` and return those that mention VCR.

    Heuristic: matches files whose source body contains any of the VCR
    decorator / config tokens (``@vcr.use_cassette``, ``cassette_library_dir``,
    ``VCR_RECORD_MODE``, ``vcrpy``, ``pytest-recording``). The Phase 27 tests
    document VCR semantics in their module docstrings even when no decorator
    is on the test function yet — those docstring hits are intentional.

    Returns an alphabetically sorted list of relative paths from ``test_dir``.
    Returns ``[]`` if the directory does not exist or contains no test files.
    """
    if not test_dir.exists() or not test_dir.is_dir():
        return []
    hits: list[str] = []
    for path in sorted(test_dir.glob("test_*.py")):
        try:
            body = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if _VCR_HINTS.search(body):
            hits.append(path.name)
    return hits


def _print_inventory(
    test_dir: Path,
    cassette_dir: Path,
    record_mode: str,
    discovered: list[str],
) -> None:
    """Print a human-readable inventory of VCR-decorated tests + the runbook."""
    print(
        f"[record-cassettes] test_dir={test_dir} cassette_dir={cassette_dir}",
        file=sys.stderr,
    )
    print(
        f"[record-cassettes] record_mode={record_mode}",
        file=sys.stderr,
    )
    print(
        f"[record-cassettes] discovered {len(discovered)} VCR-decorated "
        f"test file(s):",
        file=sys.stderr,
    )
    for name in discovered:
        print(f"  {name}")
    print(
        "\n[record-cassettes] To populate cassettes (Kaan-discharge, ~$1-2):",
        file=sys.stderr,
    )
    print(
        "  GEMINI_API_KEY=... uv run python scripts/eval/record_cassettes.py "
        "--really --record-mode new_episodes",
        file=sys.stderr,
    )
    print(
        "[record-cassettes] See KAAN-ACTION-LEGAL.md §GATE-02 for the full runbook.",
        file=sys.stderr,
    )


def _invoke_pytest(
    test_dir: Path,
    cassette_dir: Path,
    record_mode: str,
) -> int:
    """Subprocess-invoke pytest with the requested VCR record mode.

    Sets ``VCR_RECORD_MODE`` in the env (consumed by pytest-recording / vcrpy).
    Does NOT chain into uv — relies on the caller to invoke this script under
    ``uv run`` so pytest resolves from the project venv.
    """
    if not os.environ.get("GEMINI_API_KEY", "").strip():
        print(
            "[record-cassettes] FATAL: GEMINI_API_KEY not set; refusing to "
            "invoke pytest in record mode. Export the key first.",
            file=sys.stderr,
        )
        return 1
    cassette_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["VCR_RECORD_MODE"] = record_mode
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        str(test_dir),
        "-q",
        "--no-header",
    ]
    print(
        f"[record-cassettes] exec: VCR_RECORD_MODE={record_mode} "
        f"{' '.join(cmd)}",
        file=sys.stderr,
    )
    try:
        result = subprocess.run(cmd, check=False, env=env)
    except FileNotFoundError as e:
        # pytest binary missing from venv.
        print(
            f"[record-cassettes] FATAL: pytest not found in venv: {e}",
            file=sys.stderr,
        )
        return 1
    return result.returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="record_cassettes",
        description=(
            "Phase 42 GATE-02 — one-time VCR cassette population helper. "
            "Default mode is dry-run (inventory only, $0 spend); pass --really "
            "to invoke pytest with the requested record mode (~$1-2 Gemini "
            "spend, requires GEMINI_API_KEY)."
        ),
    )
    parser.add_argument(
        "--test-dir",
        type=Path,
        default=DEFAULT_TEST_DIR,
        help="Path to the eval test directory (default: tests/eval).",
    )
    parser.add_argument(
        "--cassette-dir",
        type=Path,
        default=DEFAULT_CASSETTE_DIR,
        help=(
            "Path to the VCR cassette output directory "
            "(default: tests/eval/cassettes)."
        ),
    )
    parser.add_argument(
        "--record-mode",
        choices=("none", "new_episodes", "all"),
        default="none",
        help=(
            "VCR record mode. 'none' (default) refuses to record; "
            "'new_episodes' records only missing interactions; "
            "'all' re-records every interaction (DESTRUCTIVE)."
        ),
    )
    parser.add_argument(
        "--really",
        action="store_true",
        help=(
            "Subprocess-invoke pytest in the requested record mode. Requires "
            "GEMINI_API_KEY in the environment and --record-mode != 'none'."
        ),
    )
    args = parser.parse_args(argv)

    discovered = discover_vcr_tests(args.test_dir)

    if not args.really:
        # Default dry-run path.
        _print_inventory(
            args.test_dir, args.cassette_dir, args.record_mode, discovered
        )
        return 0

    # --really path. Require an actual record mode.
    if args.record_mode == "none":
        print(
            "[record-cassettes] FATAL: --really requested with "
            "--record-mode=none; pass --record-mode=new_episodes (recommended) "
            "or --record-mode=all (destructive).",
            file=sys.stderr,
        )
        return 1
    _print_inventory(
        args.test_dir, args.cassette_dir, args.record_mode, discovered
    )
    return _invoke_pytest(args.test_dir, args.cassette_dir, args.record_mode)


if __name__ == "__main__":
    sys.exit(main())
