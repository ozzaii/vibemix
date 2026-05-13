"""Generate NOTICE from pyproject.toml + package.json + Cargo.toml.

Stub for v1 — emits a warning that NOTICE is maintained manually right
now. A full implementation would walk each manifest, look up SPDX
licenses via PyPI / npm / crates.io APIs, and emit the structured list.

For v1 we rely on manual maintenance because the dep list is small and
the auto-fetch path adds a CI dep (network + flaky) without a clear win.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit 0 if NOTICE looks current, 1 if obviously stale.",
    )
    parser.add_argument(
        "--write",
        type=Path,
        help="(Future) Path to write regenerated NOTICE to. Not yet implemented.",
    )
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parents[2]
    notice = repo_root / "NOTICE"

    if not notice.exists():
        print("NOTICE file missing", file=sys.stderr)
        return 1

    content = notice.read_text(encoding="utf-8")

    required_markers = [
        "Apache License, Version 2.0",
        "google-genai",
        "livekit-agents",
        "@tauri-apps/api",
        "tauri-plugin-updater",
    ]
    missing = [m for m in required_markers if m not in content]

    if args.check:
        if missing:
            print(f"NOTICE missing markers: {missing}", file=sys.stderr)
            return 1
        print("NOTICE looks current.")
        return 0

    if args.write:
        print(
            "auto-regeneration not implemented in v1 — NOTICE is maintained manually",
            file=sys.stderr,
        )
        return 2

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
