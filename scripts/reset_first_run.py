# SPDX-License-Identifier: Apache-2.0
"""Wipe vibemix first-run state so the calibration wizard can be re-tested.

Usage:
    uv run python scripts/reset_first_run.py [--include-tcc]

Without flags: deletes the platform config.json so the next Tauri launch
runs the wizard from scratch.
    macOS:   ~/Library/Application Support/vibemix/config.json
    Windows: %APPDATA%\\vibemix\\config.json

With ``--include-tcc`` (macOS only): also runs ``tccutil reset`` for
ScreenCapture + Microphone keyed to bundle id ``world.bravoh.vibemix``.
Used by Kaan + the Phase 20 fresh-machine rehearsal to simulate a brand-new
install on his already-warmed dev rig.

Threat model alignment (T-11-W4-05): the bundle id is hard-coded to
``world.bravoh.vibemix`` so a typo can't wipe other apps' permissions.
``--include-tcc`` is opt-in flag (not default) to keep one-off config
wipes safe from accidental TCC nuke.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

BUNDLE_ID = "world.bravoh.vibemix"


def _resolve_config_path() -> Path | None:
    """Return the platform-specific config.json path, or None on unsupported OS."""
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "vibemix" / "config.json"
    if sys.platform == "win32":
        import os

        return Path(os.environ.get("APPDATA", "")) / "vibemix" / "config.json"
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="reset_first_run",
        description=(
            "Wipe vibemix first-run state (config.json) so the calibration "
            "wizard runs again on next launch. Optionally reset macOS TCC "
            "grants for Screen Recording + Microphone."
        ),
    )
    parser.add_argument(
        "--include-tcc",
        action="store_true",
        help=(
            "macOS only: also run `tccutil reset` for ScreenCapture + Microphone "
            "keyed to bundle id world.bravoh.vibemix. WARNING: this revokes "
            "vibemix's TCC grants — the user must re-grant on next wizard run."
        ),
    )
    args = parser.parse_args(argv)

    config = _resolve_config_path()
    if config is None:
        print(f"unsupported platform: {sys.platform}", file=sys.stderr)
        return 1

    if config.exists():
        config.unlink()
        print(f"deleted {config}")
    else:
        print(f"no config.json at {config} (already clean)")

    if args.include_tcc and sys.platform == "darwin":
        # tccutil is part of macOS — no Homebrew dependency. The reset
        # subcommand is non-destructive to OTHER apps' TCC grants because
        # it's scoped to the bundle id.
        for kind in ("ScreenCapture", "Microphone"):
            result = subprocess.run(
                ["tccutil", "reset", kind, BUNDLE_ID], check=False
            )
            status = "ok" if result.returncode == 0 else f"failed ({result.returncode})"
            print(f"tccutil reset {kind} {BUNDLE_ID} -> {status}")
    elif args.include_tcc:
        print(
            f"--include-tcc is macOS-only (platform={sys.platform}); ignored.",
            file=sys.stderr,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
