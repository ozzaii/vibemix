# SPDX-License-Identifier: Apache-2.0
"""Prepare the Tauri bundle inputs before ``cargo tauri build``.

Tauri's ``bundle.resources`` globs will happily package committed placeholder
sidecar directories. This script makes the direct local build path match the
release workflow: build the frontend, ensure the PyInstaller sidecar exists,
and fail before Tauri can emit a dead app.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from scripts.dist.check_sidecar_bundle_ready import (  # noqa: E402
    REPO_ROOT,
    build_command_for_triple,
    check_sidecar_bundle_ready,
    detect_host_triple,
)

_FORCE_SIDECAR_ENV = "VIBEMIX_FORCE_SIDECAR"
_REQUIRE_CHATTERBOX_REF_ENV = "VIBEMIX_REQUIRE_CHATTERBOX_REF"


def _run(cmd: list[str], *, cwd: Path = REPO_ROOT) -> None:
    print(f"[prepare-tauri] running: {' '.join(cmd)}", file=sys.stderr)
    subprocess.run(cmd, cwd=cwd, check=True)


def _env_flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _spec_for_triple(triple: str) -> str:
    if "windows" in triple:
        return "vibemix-core.windows.spec"
    if "apple-darwin" in triple:
        return "vibemix-core.macos.spec"
    raise RuntimeError(
        f"unsupported Tauri sidecar target {triple!r}; v1 packages macOS/Windows only"
    )


def prepare_tauri_build(
    *,
    triple: str | None = None,
    skip_frontend: bool = False,
    check_only: bool = False,
    force_sidecar: bool = False,
    require_chatterbox_ref: bool = False,
) -> None:
    target_triple = triple or detect_host_triple()
    force_sidecar = force_sidecar or _env_flag(_FORCE_SIDECAR_ENV)
    require_chatterbox_ref = require_chatterbox_ref or _env_flag(
        _REQUIRE_CHATTERBOX_REF_ENV
    )

    if not skip_frontend:
        _run(["npm", "--prefix", str(REPO_ROOT / "tauri" / "ui"), "run", "build"])

    status = check_sidecar_bundle_ready(
        root=REPO_ROOT,
        triple=target_triple,
        require_chatterbox_ref=require_chatterbox_ref,
    )
    if check_only:
        if not status.ok:
            raise RuntimeError(status.message)
        print(f"[prepare-tauri] OK: {status.message}", file=sys.stderr)
        return

    if force_sidecar or not status.ok:
        if not status.ok:
            print(f"[prepare-tauri] sidecar not ready: {status.message}", file=sys.stderr)
        spec = _spec_for_triple(target_triple)
        cmd = [sys.executable, str(REPO_ROOT / "scripts" / "build_sidecar.py"), "--spec", spec]
        target_arch = os.environ.get("VIBEMIX_TAURI_TARGET_ARCH", "").strip()
        if target_arch:
            cmd.extend(["--target-arch", target_arch])
        _run(cmd)

    status = check_sidecar_bundle_ready(
        root=REPO_ROOT,
        triple=target_triple,
        require_chatterbox_ref=require_chatterbox_ref,
    )
    if not status.ok:
        raise RuntimeError(
            f"sidecar still not package-ready after `{build_command_for_triple(target_triple)}`: "
            f"{status.message}"
        )
    print(f"[prepare-tauri] OK: {status.message}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build/check frontend and sidecar inputs before Tauri packaging.",
    )
    parser.add_argument("--triple", default=None, help="target triple; default detects host")
    parser.add_argument(
        "--skip-frontend",
        action="store_true",
        help="do not run the frontend production build",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="validate inputs without building missing sidecar artifacts",
    )
    parser.add_argument(
        "--force-sidecar",
        action="store_true",
        help="rebuild the sidecar even if the readiness check already passes",
    )
    parser.add_argument(
        "--require-chatterbox-ref",
        action="store_true",
        help="fail unless the sidecar bundles the production Chatterbox reference WAV",
    )
    args = parser.parse_args(argv)

    try:
        prepare_tauri_build(
            triple=args.triple,
            skip_frontend=args.skip_frontend,
            check_only=args.check_only,
            force_sidecar=args.force_sidecar,
            require_chatterbox_ref=args.require_chatterbox_ref,
        )
    except (RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"[prepare-tauri] FAIL: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
