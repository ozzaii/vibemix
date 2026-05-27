# SPDX-License-Identifier: Apache-2.0
"""Regression for the 2026-05-27 v0.1.0-rc1 ship-blocker (parts 2+3).

PyInstaller-frozen sidecars hit a circular ``ImportError`` on first
``from livekit.agents import Agent`` in environments where the bootloader's
import order races livekit-agents 1.x's intra-package graph:

    ImportError: cannot import name 'cli' from partially initialized module
    'livekit.agents'
      File "livekit/agents/voice/agent_session.py", line 26, in <module>

The fix has three parts:

1. ``vibemix-core.{macos,windows}.spec`` part-name blocklist must include
   ``livekit.agents.cli`` (i.e. must NOT bare-block the string ``"cli"``).
   Regression-guarded by ``test_spec_blocklist_keeps_livekit_cli.py``.
2. A runtime hook fires BEFORE user ``__main__.py`` and eagerly loads
   ``livekit.agents.cli`` and ``livekit.agents.voice.agent_session`` so the
   parent's ``__init__.py:23`` ``from . import cli, ..., voice`` chain
   completes in a controlled scope (this file's regression).
3. The spec's ``runtime_hooks=[...]`` list must reference the rthook
   (this file's regression).

If someone deletes the rthook file or empties the spec's runtime_hooks list,
this test fires.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
RTHOOK = REPO_ROOT / "rthooks" / "pyi_rth_livekit_agents.py"


def test_rthook_file_exists() -> None:
    assert RTHOOK.exists(), (
        f"missing PyInstaller runtime hook: {RTHOOK}. This hook eagerly "
        "imports livekit.agents.cli + voice.agent_session at bundle boot "
        "to break the closed-stdin circular ImportError (rc1 ship-blocker "
        "fix, 2026-05-27)."
    )


def test_rthook_eager_imports_cli_and_voice() -> None:
    body = RTHOOK.read_text(encoding="utf-8")
    assert "import livekit.agents.cli" in body, (
        "rthook missing `import livekit.agents.cli` eager-load."
    )
    assert "import livekit.agents.voice.agent_session" in body, (
        "rthook missing `import livekit.agents.voice.agent_session` eager-load. "
        "Without this, voice/__init__.py loads agent_session AFTER cli but "
        "before the parent __init__ binds cli — circular ImportError."
    )


@pytest.mark.parametrize(
    "spec_name",
    ["vibemix-core.macos.spec", "vibemix-core.windows.spec"],
)
def test_spec_references_rthook(spec_name: str) -> None:
    spec_path = REPO_ROOT / spec_name
    assert spec_path.exists(), f"missing spec: {spec_path}"
    spec_text = spec_path.read_text(encoding="utf-8")

    m = re.search(r"runtime_hooks\s*=\s*\[([^\]]*)\]", spec_text)
    assert m is not None, (
        f"{spec_name}: couldn't locate `runtime_hooks=[...]` slot in "
        "Analysis(...) — has the spec layout changed?"
    )
    body = m.group(1)
    assert "pyi_rth_livekit_agents" in body, (
        f"{spec_name}: runtime_hooks list does not reference "
        "rthooks/pyi_rth_livekit_agents.py. The frozen sidecar will boot-crash "
        "with the closed-stdin circular ImportError without this hook."
    )
