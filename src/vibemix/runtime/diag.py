# SPDX-License-Identifier: Apache-2.0
"""diag_loop — verbatim port of cohost_v4.py:1859-1869.

1Hz terminal meter showing music/voice levels + audible/deck/phase using
``\\r`` carriage-return overwrite. Format string preserved byte-for-byte
from v4:1865-1868.
"""

from __future__ import annotations

import asyncio
import sys
from typing import Any

from vibemix.audio import Levels
from vibemix.state import MusicState


async def diag_loop(
    levels: Levels,
    state: MusicState,
    stop_event: asyncio.Event,
    *,
    tracer: Any | None = None,
) -> None:
    """1Hz terminal meter. Verbatim port of cohost_v4.py:1859-1869.

    ``tracer`` (optional) gets a debounced AUDIO-category line at 1Hz — only
    when ``audible`` flips. The continuous level meter stays console-only (too
    noisy for the trace file); the trace captures the *transitions* a forensic
    read cares about. Fail-soft — a tracer error never breaks the meter.
    """
    while not stop_event.is_set():
        await asyncio.sleep(1.0)
        snap = levels.snapshot()
        m_bar = "#" * int(min(snap["music"] * 50, 30))
        v_bar = "#" * int(min(snap["voice"] * 50, 30))
        sys.stdout.write(
            f"\r[live] music={snap['music']:.3f} {m_bar:<30} | voice={snap['voice']:.3f} {v_bar:<10} | "
            f"audible={int(state.audible)} deck={state.audible_deck} phase={state.phase[:8]:<8}"
        )
        sys.stdout.flush()
        if tracer is not None:
            try:
                # Debounced: note_change only writes a line on an audible flip.
                tracer.note_change(
                    "AUDIO",
                    "audible_transition",
                    "levels.audible",
                    bool(state.audible),
                    music=round(float(snap["music"]), 3),
                    voice=round(float(snap["voice"]), 3),
                    deck=state.audible_deck,
                )
            except Exception:
                pass
