# SPDX-License-Identifier: Apache-2.0
"""Regression for the 2026-05-27 v0.1.0-rc1 ship-blocker.

The PyInstaller spec's ``_runtime_submodule`` filter blocks submodules whose
dotted parts contain certain "tool / test / demo" names so the frozen sidecar
doesn't carry interactive REPL helpers, test suites, etc. The blocklist used
to contain a bare ``"cli"`` entry — which accidentally excluded
``livekit.agents.cli`` (a runtime requirement of ``livekit-agents`` 1.x:
``livekit/agents/voice/agent_session.py`` does ``from .. import cli``).

Excluding ``livekit.agents.cli`` from ``collect_submodules("livekit.agents")``
made the frozen bundle boot-crash on the first ``from livekit.agents import
Agent`` (in ``src/vibemix/agent/dj_cohost.py``) with:

    ImportError: cannot import name 'cli' from partially initialized module
    'livekit.agents' (most likely due to a circular import)

This regression test keeps the bug from coming back: the part-name blocklist
in both spec files must not contain a bare ``"cli"`` entry. If a specific
package's ``cli`` subtree ever needs to be excluded, do it by full module
name in the explicit blocks below the part-blocklist (see the spec source).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    "spec_name",
    ["vibemix-core.macos.spec", "vibemix-core.windows.spec"],
)
def test_runtime_submodule_blocklist_does_not_contain_cli_part(spec_name: str) -> None:
    spec_path = REPO_ROOT / spec_name
    assert spec_path.exists(), f"missing spec file: {spec_path}"
    spec_text = spec_path.read_text(encoding="utf-8")

    # Locate the first `blocked = { ... }` literal inside `_runtime_submodule`.
    # The set body is everything between the opening `{` and the matching `}`.
    m = re.search(r"blocked\s*=\s*\{([^}]*)\}", spec_text)
    assert m is not None, (
        f"{spec_name}: couldn't locate the `blocked = {{...}}` set inside "
        "_runtime_submodule — has the spec layout changed?"
    )
    blocked_body = m.group(1)

    assert '"cli"' not in blocked_body, (
        f"{spec_name}: the part-name blocklist contains a bare \"cli\" entry. "
        "That excludes livekit.agents.cli from `collect_submodules`, which "
        "boot-crashes the frozen sidecar with a circular ImportError on "
        "`from livekit.agents import Agent`. See the in-spec comment where "
        "the 2026-05-27 fix removed it. If you need to exclude a specific "
        "package's cli subtree, do it by full module name in the explicit "
        "blocks below the part-blocklist."
    )
    assert "'cli'" not in blocked_body, (
        f"{spec_name}: same as above, just with single quotes."
    )
