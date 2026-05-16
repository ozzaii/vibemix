# SPDX-License-Identifier: Apache-2.0
"""parent_watchdog — orphan-process self-shutdown.

Tauri's ``tauri-plugin-shell`` calls ``child.kill()`` on clean app exit,
which delivers SIGTERM to the sidecar and its ``add_signal_handler``
sets the stop event. But on Force Quit, Activity Monitor's "Force Quit",
``kill -9 <tauri-pid>``, or a Rust panic in the parent process the
sidecar is reparented to launchd (``ppid=1``) and sits forever, holding
port 8765 — every subsequent Tauri launch then hits the port-in-use
crash banner until the user nukes the orphan manually.

This watchdog polls ``os.getppid()`` once every 2 s. The moment it
flips to 1 — or to anything other than the original parent — we set the
stop event so the WizardLoop / SessionLoop / live runtime can tear
down cleanly through the existing shutdown path (websocket close,
audio streams close, recorder flush).

The poll interval (2 s) is a compromise: long enough that the check is
free, short enough that the orphan window before port 8765 is
released stays under the wizard's typical relaunch latency.
"""

from __future__ import annotations

import asyncio
import os
import sys

POLL_INTERVAL_S: float = 2.0


async def watch_parent(stop_event: asyncio.Event) -> None:
    """Set ``stop_event`` if the parent process dies.

    Records the initial ``getppid()`` at start; thereafter wakes every
    ``POLL_INTERVAL_S`` seconds and trips the stop on either:

      * ppid == 1 (launchd / init has adopted us — parent gone)
      * ppid != initial (parent replaced — also abnormal)

    Returns early when ``stop_event`` is set by another path (normal
    SIGTERM, ``ipc.wizard.done``, etc.) — no spurious double-signal.
    """
    initial_ppid = os.getppid()
    # ppid 1 at boot means we were launched detached from a shell (e.g.,
    # ``open vibemix.app`` outside a Tauri context). In that case the
    # watchdog has no parent to watch — return immediately rather than
    # racing a shutdown.
    if initial_ppid == 1:
        return
    while not stop_event.is_set():
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=POLL_INTERVAL_S)
            return  # stop_event tripped elsewhere — clean exit path
        except asyncio.TimeoutError:
            pass
        current_ppid = os.getppid()
        if current_ppid != initial_ppid:
            print(
                f"-> parent died (ppid {initial_ppid} -> {current_ppid}); "
                "stopping sidecar to release port 8765",
                file=sys.stderr,
            )
            stop_event.set()
            return


__all__ = ["POLL_INTERVAL_S", "watch_parent"]
