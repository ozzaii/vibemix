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

import importlib.util
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PATCH_SCRIPT = REPO_ROOT / "scripts" / "dist" / "patch_livekit_agents_init.py"
BUILD_SCRIPT = REPO_ROOT / "scripts" / "build_sidecar.py"


def _load_patch_module():
    """Import patch_livekit_agents_init.py as a module for unit-level testing."""
    spec = importlib.util.spec_from_file_location("_patch_lk", PATCH_SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# Faithful miniature of livekit/agents/__init__.py's load-bearing shape.
# Two real-world input shapes the patch must converge to the lazy form:

# Shape A — pristine upstream (single comma-list, cli first by position).
_PRISTINE_INIT = '''\
import typing

from . import cli, inference, ipc, llm, metrics, stt, tokenize, tts, utils, vad, voice
from ._exceptions import Exc


def __getattr__(name: str) -> typing.Any:
    if name == "mcp":
        from .llm import mcp

        return mcp

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["cli", "voice"]
'''

# Shape B — the already-(wrongly)-patched "cli first split" form (current .venv).
_SPLIT_INIT = '''\
import typing

from . import cli  # explicit-first to fix the PyInstaller frozen-importer circular ImportError — see scripts/dist/patch_livekit_agents_init.py
from . import inference, ipc, llm, metrics, stt, tokenize, tts, utils, vad, voice
from ._exceptions import Exc


def __getattr__(name: str) -> typing.Any:
    if name == "mcp":
        from .llm import mcp

        return mcp

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["cli", "voice"]
'''

_EAGER_CLI_RE = re.compile(r"^from \. import cli\b", re.MULTILINE)


def test_transform_drops_eager_cli_from_pristine() -> None:
    mod = _load_patch_module()
    out = mod.transform_init_text(_PRISTINE_INIT)
    # No module-scope eager ``from . import cli`` survives.
    assert not _EAGER_CLI_RE.search(out), (
        "pristine transform still eagerly imports cli:\n" + out
    )
    # The other submodules are preserved.
    assert "from . import inference, ipc, llm, metrics, stt, tokenize, tts, utils, vad, voice" in out
    # cli is now lazily resolvable via __getattr__, using importlib (NOT a
    # relative ``from . import cli`` — that would recurse through __getattr__).
    assert 'if name == "cli":' in out
    assert "importlib.import_module" in out
    assert "from . import cli" not in out, (
        "lazy cli branch must not use ``from . import cli`` — it re-enters "
        "__getattr__ via hasattr() and infinite-loops:\n" + out
    )


def test_transform_drops_eager_cli_from_split() -> None:
    mod = _load_patch_module()
    out = mod.transform_init_text(_SPLIT_INIT)
    assert not _EAGER_CLI_RE.search(out), (
        "split transform still eagerly imports cli:\n" + out
    )
    # The standalone split line is gone but the second import line stays intact.
    assert "from . import inference, ipc, llm, metrics, stt, tokenize, tts, utils, vad, voice" in out
    assert 'if name == "cli":' in out


def test_transform_preserves_existing_getattr_branches() -> None:
    mod = _load_patch_module()
    out = mod.transform_init_text(_PRISTINE_INIT)
    # The pre-existing ``mcp`` lazy branch must survive untouched.
    assert 'if name == "mcp":' in out
    assert "from .llm import mcp" in out


def test_transform_is_idempotent() -> None:
    mod = _load_patch_module()
    once = mod.transform_init_text(_SPLIT_INIT)
    twice = mod.transform_init_text(once)
    assert once == twice, "transform_init_text is not idempotent"
    # And a second pass adds no duplicate cli branch.
    assert once.count('if name == "cli":') == 1


def test_transform_output_imports_without_cycle(tmp_path: Path) -> None:
    """The transformed module body imports (no eager cli) in a fresh interpreter."""
    mod = _load_patch_module()
    out = mod.transform_init_text(_PRISTINE_INIT)
    # Strip the real submodule imports (no livekit here) down to what we assert:
    # the eager cli line is gone and __getattr__ compiles + resolves cli lazily.
    body = out.replace(
        "from . import inference, ipc, llm, metrics, stt, tokenize, tts, utils, vad, voice\n",
        "",
    ).replace("from ._exceptions import Exc\n", "")
    # Stub the lazy ``importlib.import_module(...)`` so it resolves to a
    # sentinel with no real cli submodule present.
    body = re.sub(r"importlib\.import_module\([^\n]*\)", "'CLI_MODULE'", body)
    fixture = tmp_path / "patched_init.py"
    fixture.write_text(body, encoding="utf-8")
    spec = importlib.util.spec_from_file_location("patched_init_fixture", fixture)
    assert spec and spec.loader
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    # __getattr__ resolves cli lazily; eager import never ran.
    assert loaded.cli == "CLI_MODULE"


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
