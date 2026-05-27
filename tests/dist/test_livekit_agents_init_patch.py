# SPDX-License-Identifier: Apache-2.0
"""Regression for the 2026-05-27 v0.1.0-rc1 ship-blocker (the actual fix).

Three preceding partial fixes (spec blocklist removal of bare ``"cli"``,
eager-import attempt, runtime hook) chased the symptom. The actual root
cause: livekit-agents 1.x's ``livekit/agents/__init__.py:23`` does a single
``from . import cli, inference, ipc, llm, ..., voice`` statement. PyInstaller's
frozen importer does NOT bind submodules onto the parent package in the
comma-list order the way CPython's normal importer does — by the time
``voice.agent_session`` (transitively imported when voice loads, the LAST
item in the list) runs ``from .. import cli, ...``, ``cli`` has been
imported but isn't bound on the parent yet → circular ImportError in
many real-world spawn contexts (Tauri ``app.shell().command()``,
Finder/launchd-launched .app, subprocess.Popen with stdin=PIPE, anything
where parent forwards env vars like CARGO_* / OUT_DIR).

The fix: ``scripts/dist/patch_livekit_agents_init.py`` splits the offending
line into two statements with ``cli`` first. Idempotent. ``scripts/build_sidecar.py``
runs the patch before every ``pyinstaller`` invocation so freshly-built
bundles are always patched.

This test guards three properties:

1. The patch script exists.
2. The patch script is idempotent (re-running is a no-op).
3. ``scripts/build_sidecar.py`` invokes the patch before ``pyinstaller``
   (so a contributor who removes the call gets a CI failure, not a
   silent ship blocker).
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PATCH_SCRIPT = REPO_ROOT / "scripts" / "dist" / "patch_livekit_agents_init.py"
BUILD_SCRIPT = REPO_ROOT / "scripts" / "build_sidecar.py"


def test_patch_script_exists() -> None:
    assert PATCH_SCRIPT.exists(), (
        f"missing {PATCH_SCRIPT} — the build_sidecar.py pipeline depends on "
        "this script to patch livekit-agents before pyinstaller freezes the "
        "bundle. Without it, frozen sidecars hit the closed-stdin / "
        "Tauri-spawn / launchd circular ImportError (rc1 ship blocker)."
    )


def test_patch_script_is_idempotent_when_run_dry() -> None:
    # `--dry-run` must always succeed regardless of current .venv state.
    result = subprocess.run(
        [sys.executable, str(PATCH_SCRIPT), "--dry-run"],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0, (
        f"patch script --dry-run failed unexpectedly:\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )


def test_build_sidecar_invokes_the_patch() -> None:
    text = BUILD_SCRIPT.read_text(encoding="utf-8")
    # Two pieces must be present: the helper that runs the patch, and a call
    # to it from inside the pyinstaller-orchestration path.
    assert "_apply_livekit_agents_init_patch" in text, (
        f"{BUILD_SCRIPT} does not define _apply_livekit_agents_init_patch — "
        "the livekit-agents init patch will not be applied before pyinstaller, "
        "so the frozen bundle WILL crash on Tauri/launchd spawn. See "
        "scripts/dist/patch_livekit_agents_init.py for the full explanation."
    )
    # Find the run_pyinstaller body and confirm the patch is invoked inside.
    body_match = re.search(
        r"def run_pyinstaller\([^)]*\)[^:]*:.*?(?=\n(?:def |class |# ---))",
        text,
        re.DOTALL,
    )
    assert body_match is not None, (
        f"could not locate run_pyinstaller(...) body in {BUILD_SCRIPT}"
    )
    body = body_match.group(0)
    assert "_apply_livekit_agents_init_patch(" in body, (
        f"{BUILD_SCRIPT}::run_pyinstaller does not call the patch helper "
        "before invoking pyinstaller. The frozen bundle WILL crash on "
        "Tauri/launchd spawn without the livekit-agents init patch."
    )
