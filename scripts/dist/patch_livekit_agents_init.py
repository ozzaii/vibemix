# SPDX-License-Identifier: Apache-2.0
"""Idempotent patch for livekit-agents 1.x's circular-import-in-frozen-bundle bug.

Background: PyInstaller-frozen sidecars hit a circular ``ImportError`` on first
``from livekit.agents import Agent`` in many spawn contexts (closed stdin from
Tauri's ``app.shell().command()``, Finder/launchd-launched .app processes, CI
smoke jobs that pipe stdio, subprocess.Popen with stdin=PIPE, or whenever
the parent process forwards env vars like CARGO_* / OUT_DIR):

    ImportError: cannot import name 'cli' from partially initialized module
    'livekit.agents'
      File "livekit/agents/voice/agent_session.py", line 26, in <module>

Root cause: ``livekit/agents/__init__.py:23`` does

    from . import cli, inference, ipc, llm, metrics, stt, tokenize, tts, utils, vad, voice

PyInstaller's frozen importer does NOT bind submodules onto the parent package
in the comma-list order the way CPython's normal importer does. When the
chained load of ``voice`` (last in the list) reaches
``voice/agent_session.py:26`` (``from .. import cli, inference, llm, ...``),
``cli`` has been imported as a module but isn't bound on the parent package
yet → circular.

The fix: split the single ``from . import ...`` line into two statements with
``cli`` first. Python evaluates each statement independently, so ``cli`` is
fully bound on the parent before the rest of the chain runs.

This script runs before ``pyinstaller`` inside ``scripts/build_sidecar.py``
so the patch is always applied to the .venv before the bundle is frozen.
Idempotent — re-running is a no-op if the patch is already in place.

Verified post-fix: standalone ``</dev/null``, ``subprocess.Popen(stdin=PIPE)``,
and Tauri-equivalent env (OUT_DIR + CARGO_*) spawns all boot cleanly.
Regression-guarded by ``tests/dist/test_livekit_agents_init_patch.py``.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

_BUG_LINE = (
    "from . import cli, inference, ipc, llm, metrics, stt, tokenize, tts, utils, vad, voice"
)

_FIX_LINES = (
    "from . import cli  # explicit-first to fix the PyInstaller frozen-importer "
    "circular ImportError — see scripts/dist/patch_livekit_agents_init.py\n"
    "from . import inference, ipc, llm, metrics, stt, tokenize, tts, utils, vad, voice"
)


def _candidate_init_paths() -> list[Path]:
    """Return possible site-packages locations of livekit/agents/__init__.py.

    Supports the project's two known install layouts:
      - ``.venv/lib/python3.X/site-packages/livekit/agents/__init__.py``
        (the dev venv, used by ``uv run python -m vibemix`` + the bundle build)
      - ``sys.path`` resolved location (CI / alternate venvs)
    """
    out: list[Path] = []
    # Repo-local .venv (the dev + build venv).
    venv_dir = REPO_ROOT / ".venv" / "lib"
    if venv_dir.exists():
        for py_dir in sorted(venv_dir.glob("python3.*")):
            cand = py_dir / "site-packages" / "livekit" / "agents" / "__init__.py"
            if cand.exists():
                out.append(cand)
    # Fallback: import-resolved path (for CI agents / non-uv envs).
    try:
        import livekit.agents  # type: ignore[import-not-found]
    except Exception:  # pragma: no cover — bare env that doesn't have it
        return out
    spec_origin = getattr(livekit.agents, "__file__", None)
    if spec_origin:
        p = Path(spec_origin)
        if p.exists() and p not in out:
            out.append(p)
    return out


def patch_path(path: Path, *, dry_run: bool = False) -> bool:
    """Apply the split-import patch to ``path``. Returns True if a change was written.

    Also clears the file's ``__pycache__/__init__.cpython-*.pyc`` so PyInstaller
    re-compiles fresh on its next freeze (without this, a stale bytecode cache
    would silently win even though the source is patched — the actual rc1
    repro we hit on 2026-05-27).
    """
    text = path.read_text(encoding="utf-8")
    if _BUG_LINE not in text:
        # Already patched (or upstream changed shape) — still clear the pyc
        # cache because we can't tell whether the cache was generated before
        # the patch landed.
        if not dry_run:
            _purge_pycache(path)
        return False
    new_text = text.replace(_BUG_LINE, _FIX_LINES, 1)
    if dry_run:
        return True
    path.write_text(new_text, encoding="utf-8")
    _purge_pycache(path)
    return True


def _purge_pycache(init_path: Path) -> None:
    """Delete any cached .pyc for ``init_path`` so PyInstaller re-compiles fresh."""
    cache_dir = init_path.parent / "__pycache__"
    if not cache_dir.exists():
        return
    stem = init_path.stem  # "__init__"
    purged: list[str] = []
    for pyc in cache_dir.glob(f"{stem}.cpython-*.pyc"):
        try:
            pyc.unlink()
            purged.append(pyc.name)
        except OSError:
            continue
    if purged:
        print(
            f"[patch_livekit_agents_init] purged stale pyc cache: {cache_dir} "
            f"({len(purged)} file(s): {', '.join(sorted(purged))})"
        )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would change without writing.",
    )
    args = p.parse_args(argv)

    paths = _candidate_init_paths()
    if not paths:
        print("[patch_livekit_agents_init] no livekit/agents/__init__.py found", file=sys.stderr)
        return 1

    any_changed = False
    for path in paths:
        changed = patch_path(path, dry_run=args.dry_run)
        if changed:
            verb = "would-patch" if args.dry_run else "patched"
            print(f"[patch_livekit_agents_init] {verb}: {path}")
            any_changed = True
        else:
            print(f"[patch_livekit_agents_init] already-patched / no-op: {path}")
    if any_changed and not args.dry_run:
        print("[patch_livekit_agents_init] OK — frozen bundle will now boot under any spawn context")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
