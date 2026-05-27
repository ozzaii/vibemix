# SPDX-License-Identifier: Apache-2.0
"""PyInstaller runtime hook — pre-flight livekit.agents submodule chain.

Fires BEFORE the user's __main__.py runs, inside the frozen bootloader.
Eagerly loads livekit.agents.cli and livekit.agents.voice.agent_session so
the parent package's __init__.py:23 ``from . import cli, ..., voice`` chain
completes in a controlled order before any user code triggers the circular
``ImportError: cannot import name 'cli' from partially initialized module
'livekit.agents'`` (livekit-agents 1.x bug specific to frozen bundles
spawned with closed stdin — see commits 3d2900ce + 8dd2f098).

Wrapped in try/except so a missing optional dep never blocks boot.
"""

try:
    import livekit.agents.cli  # noqa: F401
    import livekit.agents.voice.agent_session  # noqa: F401
except Exception:
    # Don't block boot for non-livekit modes (the wizard / debrief paths
    # don't touch livekit at all; let main() surface the real ImportError
    # if the user actually needs live co-host).
    pass
