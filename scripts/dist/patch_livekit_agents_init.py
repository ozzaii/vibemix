# SPDX-License-Identifier: Apache-2.0
"""Idempotent patch for livekit-agents 1.x's circular-import-in-frozen-bundle bug.

Background: PyInstaller-frozen sidecars hit a circular ``ImportError`` on first
``from livekit.agents import Agent`` in many spawn contexts (closed stdin from
Tauri's ``app.shell().command()``, Finder/launchd-launched .app processes, CI
smoke jobs that pipe stdio, subprocess.Popen with stdin=PIPE, or whenever
the parent process forwards env vars like CARGO_* / OUT_DIR):

    ImportError: cannot import name 'cli' from partially initialized module
    'livekit.agents'
      File "livekit/agents/__init__.py", line 23, in <module>

Root cause: ``livekit/agents/__init__.py`` eagerly does ``from . import cli``.
Loading ``cli`` pulls in ``voice``/``worker`` (cli/cli.py:46-49), whose chain
re-enters the parent package for ``cli`` while ``__init__`` is still parked on
that eager line — so ``cli`` is mid-load (not yet bound on the parent) and the
frozen importer raises the circular ImportError. (The earlier "split the line so
cli is first" fix did NOT help: loading cli at all is the trigger, regardless of
position. Verified 2026-05-30 on the real onedir sidecar.)

The fix: vibemix uses ``Agent``/``AgentSession``/``RealtimeModel`` only and never
touches the worker ``cli`` — so stop importing it eagerly. Drop the eager
``from . import cli`` and resolve cli lazily through the module's existing
PEP-562 ``__getattr__``. By the time anything reads ``livekit.agents.cli`` the
parent ``__init__`` has fully run, so cli's ``voice``/``worker`` chain finds them
bound → no cycle. ``cli`` stays bundled (collected by the spec's
``collect_submodules``; guarded by test_spec_blocklist_keeps_livekit_cli.py). The
companion ``voice/agent_session.py`` patch (drop module-scope ``cli``, lazy-import
it in the one function that needs it) stays load-bearing: that import fires during
the eager ``voice`` load, before ``__init__`` completes.

This script runs before ``pyinstaller`` inside ``scripts/build_sidecar.py``
so the patch is always applied to the .venv before the bundle is frozen.
Idempotent — re-running is a no-op if the patch is already in place.

Verified post-fix: standalone ``</dev/null``, ``subprocess.Popen(stdin=PIPE)``,
and Tauri-equivalent env (OUT_DIR + CARGO_*) spawns all boot cleanly.
Regression-guarded by ``tests/dist/test_livekit_agents_init_patch.py``.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# --- The __init__.py fix: make ``cli`` LAZY (not eager-first). ----------------
#
# History: the first fix split ``from . import cli, inference, ...`` into two
# statements with ``cli`` first, on the theory that binding cli before the rest
# would break the cycle. It does NOT — loading ``cli`` itself pulls in
# ``voice``/``worker`` (cli/cli.py:46-49), whose chain re-enters the parent for
# ``cli`` while ``__init__`` is still parked on the eager ``from . import cli``
# line → ``ImportError: cannot import name 'cli' from partially initialized
# module 'livekit.agents'`` in the frozen bundle (verified 2026-05-30 on the
# real onedir sidecar). The "cli first" split fought the wrong layer.
#
# Root cause: vibemix uses ``Agent``/``AgentSession``/``RealtimeModel`` only — it
# NEVER touches the worker ``cli``. So the real fix is to stop importing ``cli``
# eagerly at all: drop the eager ``from . import cli`` and resolve it lazily via
# the module's existing PEP-562 ``__getattr__`` (which already lazy-loads
# ``mcp``). By the time anything accesses ``livekit.agents.cli``, the parent
# ``__init__`` has fully executed, so cli's ``from ..voice import ...`` /
# ``from ..worker import ...`` chain finds those submodules already bound — no
# cycle. ``cli`` stays in the frozen bundle regardless (collected by the spec's
# ``collect_submodules`` + guarded by tests/dist/test_spec_blocklist_keeps_livekit_cli.py).
#
# The companion ``voice/agent_session.py`` patch below is still load-bearing: its
# module-scope ``from .. import cli`` (pristine upstream) would fire DURING the
# eager ``voice`` load (still inside __init__), re-triggering the cycle before
# __init__ completes — so cli is dropped there and lazy-imported in the one
# function that needs it.

# Match the eager ``from . import cli`` in either known shape, anchored at column
# 0 (the injected lazy branch is indented, so these never re-match it).
_EAGER_CLI_COMMA_RE = re.compile(r"^(from \. import )cli, ", re.MULTILINE)
_EAGER_CLI_STANDALONE_RE = re.compile(
    r"^from \. import cli[ \t]*(?:#[^\n]*)?\n", re.MULTILINE
)
_GETATTR_RAISE_RE = re.compile(
    r'^([ \t]+)raise AttributeError\(f"module \{__name__!r\} has no attribute \{name!r\}"\)',
    re.MULTILINE,
)


def _lazy_cli_branch(indent: str) -> str:
    # Use ``importlib.import_module`` (NOT ``from . import cli``): a relative
    # ``from . import cli`` INSIDE ``__getattr__('cli')`` re-enters via
    # ``hasattr(parent, 'cli')`` → infinite ``__getattr__`` recursion. Importing
    # the submodule by full name bypasses the parent's ``__getattr__`` entirely.
    return (
        f'{indent}if name == "cli":\n'
        f"{indent}    import importlib  # lazy — breaks the PyInstaller "
        "frozen-importer circular ImportError "
        "(see scripts/dist/patch_livekit_agents_init.py)\n"
        "\n"
        f'{indent}    return importlib.import_module(__name__ + ".cli")\n'
        "\n"
    )


def _append_getattr(text: str) -> str:
    """Degenerate fallback: upstream shipped no ``__getattr__`` to extend."""
    if not text.endswith("\n"):
        text += "\n"
    return text + (
        "\n\ndef __getattr__(name):\n"
        + _lazy_cli_branch("    ")
        + '    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")\n'
    )


def transform_init_text(text: str) -> str:
    """Convert ``livekit/agents/__init__.py`` text to the lazy-cli form.

    Idempotent: re-applying produces no further change. Handles both the
    pristine upstream comma-list and the older "cli first split" shape.
    """
    # 1) Drop the eager cli import (comma-list shape, then standalone-line shape).
    text = _EAGER_CLI_COMMA_RE.sub(r"\1", text)
    text = _EAGER_CLI_STANDALONE_RE.sub("", text)
    # 2) Make cli lazily resolvable via __getattr__ (only once).
    if 'if name == "cli":' not in text:
        if "def __getattr__(" in text:
            new_text, n = _GETATTR_RAISE_RE.subn(
                lambda m: _lazy_cli_branch(m.group(1)) + m.group(0), text, count=1
            )
            text = new_text if n else _append_getattr(text)
        else:
            text = _append_getattr(text)
    return text

# Second-tier patch (added 2026-05-27 late session): voice/agent_session.py:26
# does ``from .. import cli, inference, llm, stt, tts, utils, vad`` at module
# scope. The split-import of ``__init__.py`` (above) was supposed to make this
# safe by binding ``cli`` first, but launchd-spawn testing showed the circular
# still triggers FLAKILY — cli's own deep dependency chain (rich/typer/etc)
# transitively re-enters the voice load before cli's binding completes, so the
# parent's partial-init state catches ``from .. import cli`` half-loaded. Fix:
# drop ``cli`` from the module-scope from-import, lazy-import it inside the
# single function that uses it (``_create_console`` does
# ``cli.AgentsConsole.get_instance()`` at line 678). Net effect: agent_session
# can be loaded without any ``cli`` lookup on the partial-init parent.
_AS_BUG_LINE = "from .. import cli, inference, llm, stt, tts, utils, vad"
_AS_FIX_LINE = (
    "from .. import inference, llm, stt, tts, utils, vad  "
    "# cli lazy-imported inside _create_console (rc1 cycle break 2026-05-27 — "
    "see scripts/dist/patch_livekit_agents_init.py)"
)
_AS_CALL_BUG = "c = cli.AgentsConsole.get_instance()"
_AS_CALL_FIX = (
    "from .. import cli as _cli  # lazy — breaks the frozen-importer cycle\n"
    "            c = _cli.AgentsConsole.get_instance()"
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


def _candidate_agent_session_paths() -> list[Path]:
    """Sister to ``_candidate_init_paths()`` for ``voice/agent_session.py``."""
    out: list[Path] = []
    for init_path in _candidate_init_paths():
        cand = init_path.parent / "voice" / "agent_session.py"
        if cand.exists():
            out.append(cand)
    return out


def patch_agent_session(path: Path, *, dry_run: bool = False) -> bool:
    """Apply the cli-lazy-import patch to ``voice/agent_session.py``."""
    text = path.read_text(encoding="utf-8")
    changed = False
    if _AS_BUG_LINE in text:
        text = text.replace(_AS_BUG_LINE, _AS_FIX_LINE, 1)
        changed = True
    if _AS_CALL_BUG in text and "from .. import cli as _cli" not in text:
        text = text.replace(_AS_CALL_BUG, _AS_CALL_FIX, 1)
        changed = True
    if changed and not dry_run:
        path.write_text(text, encoding="utf-8")
        _purge_pycache(path)
    elif not changed and not dry_run:
        _purge_pycache(path)
    return changed


def patch_path(path: Path, *, dry_run: bool = False) -> bool:
    """Apply the lazy-cli patch to ``path``. Returns True if a change was written.

    Also clears the file's ``__pycache__/__init__.cpython-*.pyc`` so PyInstaller
    re-compiles fresh on its next freeze (without this, a stale bytecode cache
    would silently win even though the source is patched — the actual rc1
    repro we hit on 2026-05-27).
    """
    text = path.read_text(encoding="utf-8")
    new_text = transform_init_text(text)
    if new_text == text:
        # Already patched (or upstream changed shape) — still clear the pyc
        # cache because we can't tell whether the cache was generated before
        # the patch landed.
        if not dry_run:
            _purge_pycache(path)
        return False
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
            print(f"[patch_livekit_agents_init] {verb} __init__: {path}")
            any_changed = True
        else:
            print(f"[patch_livekit_agents_init] already-patched / no-op __init__: {path}")
    # Also apply the agent_session cycle-break patch (second-tier — the
    # __init__ patch wasn't enough on its own under launchd-spawn).
    for as_path in _candidate_agent_session_paths():
        changed = patch_agent_session(as_path, dry_run=args.dry_run)
        if changed:
            verb = "would-patch" if args.dry_run else "patched"
            print(f"[patch_livekit_agents_init] {verb} agent_session: {as_path}")
            any_changed = True
        else:
            print(f"[patch_livekit_agents_init] already-patched / no-op agent_session: {as_path}")
    if any_changed and not args.dry_run:
        print("[patch_livekit_agents_init] OK — frozen bundle will now boot under any spawn context")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
