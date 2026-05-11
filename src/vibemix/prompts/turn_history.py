# SPDX-License-Identifier: Apache-2.0
"""TurnHistory ring — per-session anti-repetition memory.

Capacity: ``max_pairs=12`` (CONTEXT §TurnHistory). Each "pair" is one user
turn + one model turn. The ring stores arbitrary push order — pushes don't
have to alternate; the dispatcher decides what to inject.

Format (rendered by ``as_text()``):

    <recent_turns>
    <user>...</user>
    <model>...</model>
    ...
    </recent_turns>

If the ring is empty, ``as_text()`` returns the empty string (NOT a bare
wrapper) so the dj_cohost prompt builder can append it conditionally.

In-memory only — no disk persistence in v1 (CONTEXT §Storage).
Thread-safe (the audio loop and the asyncio loop both touch it). Lock is
fine-grained — a single mutex on push/clear/snapshot.
"""

from __future__ import annotations

import threading
from collections import deque

DEFAULT_MAX_PAIRS = 12


class TurnHistory:
    """Per-session ring of recent (role, text) entries.

    A "pair" is conceptually one user turn + one model turn, but the ring
    doesn't enforce alternation — pushes can come in any order. Capacity is
    measured in pairs, so the underlying deque maxlen is ``max_pairs * 2``.
    """

    __slots__ = ("_entries", "_lock", "max_pairs")

    def __init__(self, max_pairs: int = DEFAULT_MAX_PAIRS) -> None:
        if max_pairs < 1:
            raise ValueError(f"max_pairs must be ≥ 1, got {max_pairs}")
        self.max_pairs = max_pairs
        # Each entry = ("user"|"model", text). Capacity = pairs x 2.
        self._entries: deque[tuple[str, str]] = deque(maxlen=max_pairs * 2)
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Push
    # ------------------------------------------------------------------

    def push_user(self, text: str) -> None:
        """Append a user turn to the ring (oldest evicted on overflow)."""
        with self._lock:
            self._entries.append(("user", text))

    def push_model(self, text: str) -> None:
        """Append a model turn to the ring (oldest evicted on overflow)."""
        with self._lock:
            self._entries.append(("model", text))

    def clear(self) -> None:
        """Empty the ring."""
        with self._lock:
            self._entries.clear()

    # ------------------------------------------------------------------
    # Render
    # ------------------------------------------------------------------

    def as_text(self) -> str:
        """Render the ring as a ``<recent_turns>`` block.

        Returns an empty string when the ring is empty so prompt builders
        can append it conditionally without producing a bare wrapper.
        """
        with self._lock:
            entries = list(self._entries)
        if not entries:
            return ""
        lines = ["<recent_turns>"]
        for role, text in entries:
            lines.append(f"<{role}>{text}</{role}>")
        lines.append("</recent_turns>")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Introspection (for tests + diagnostics)
    # ------------------------------------------------------------------

    def __len__(self) -> int:
        with self._lock:
            return len(self._entries)
