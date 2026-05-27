# SPDX-License-Identifier: Apache-2.0
"""Regression for the 2026-05-27 v0.1.0-rc1 ship-blocker (part 2).

PyInstaller-frozen sidecars spawned with closed stdin (the default for
Tauri's ``app.shell().command()`` spawn, Finder/launchd-launched .app
processes, and CI smoke jobs that pipe stdio) hit a circular ImportError
on first ``from livekit.agents import Agent``:

    ImportError: cannot import name 'cli' from partially initialized
    module 'livekit.agents'
      File "livekit/agents/voice/agent_session.py", line 26, in <module>

The bug is PyInstaller's hidden-import boot order interacting with
``livekit-agents`` 1.x's intra-package import graph. The fix is two-fold:

1. Un-block the ``livekit.agents.cli`` submodule from the spec's part-name
   blocklist (``tests/dist/test_spec_blocklist_keeps_livekit_cli.py``
   regression-guards that).
2. Eager-import ``livekit.agents`` at the top of ``src/vibemix/__main__.py``
   so the parent-package ``__init__.py`` completes in a controlled scope
   BEFORE any other transitive import (notably ``dj_cohost.py:49`` which
   does ``from livekit.agents import Agent``) races the bootloader.

This test guards #2: ``src/vibemix/__main__.py`` must contain the eager
``import livekit.agents`` line, ordered BEFORE the import of
``vibemix.agent.config`` (which transitively pulls in ``dj_cohost``).

If someone "cleans up" the noqa-marked import without re-verifying frozen
boot in a closed-stdin context, this test fires.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MAIN_PY = REPO_ROOT / "src" / "vibemix" / "__main__.py"


def test_main_eager_imports_livekit_agents_before_vibemix_agent() -> None:
    text = MAIN_PY.read_text(encoding="utf-8")

    # The eager import line — match either `import livekit.agents` or
    # `import livekit.agents as ...`, with or without trailing noqa.
    eager_re = re.compile(r"^import\s+livekit\.agents\b", re.MULTILINE)
    eager_match = eager_re.search(text)
    assert eager_match is not None, (
        "src/vibemix/__main__.py is missing the eager `import livekit.agents` "
        "line that fixes the PyInstaller closed-stdin circular ImportError "
        "(rc1 ship-blocker fix #2, 2026-05-27). Do not remove this import "
        "without re-verifying the frozen sidecar boots clean under all four "
        "modes (--help, --wizard, --session, no-args) with `</dev/null`."
    )

    # And it must come BEFORE the first `from vibemix.agent` import (which
    # transitively pulls livekit.agents through dj_cohost.py:49).
    vibemix_agent_re = re.compile(r"^from\s+vibemix\.agent\b", re.MULTILINE)
    vibemix_agent_match = vibemix_agent_re.search(text)
    if vibemix_agent_match is not None:
        assert eager_match.start() < vibemix_agent_match.start(), (
            "src/vibemix/__main__.py orders `from vibemix.agent...` BEFORE the "
            "eager `import livekit.agents`. The eager import must come FIRST "
            "or the PyInstaller boot order can still race (rc1 ship-blocker "
            "fix #2, 2026-05-27)."
        )
