# SPDX-License-Identifier: Apache-2.0
"""Session-lifetime PCM cache for fixed authored Learn tutor lines.

The Wreck Room's verdict-window barks must land near-instantly; a fresh MLX
synth costs seconds. The fixed bark bank is warm-synthesized once per session
(triggered by the first wreck-marked utterance) and pinned here, so a bark at
a verdict edge becomes one synchronous playback push.

Why not the Chatterbox engine cache: that one is an env-gated live-path
experiment (``VIBEMIX_CHATTERBOX_PCM_CACHE``) and stores pre-resample chunks.
This cache is learn-lane only, stores OUTPUT_SR-ready bytes, and pins the
warm bank so repeated live grade lines can never evict a verdict bark. Keys
assume one TTS engine per process (the resample pipeline is identity-stable).
"""
from __future__ import annotations

import threading

_DEFAULT_MAX_UNPINNED_BYTES = 8 * 1024 * 1024


class BarkPcmCache:
    """Byte-capped text->PCM store; pinned warm entries are never evicted."""

    def __init__(self, max_unpinned_bytes: int = _DEFAULT_MAX_UNPINNED_BYTES) -> None:
        self._lock = threading.Lock()
        # Insertion order doubles as LRU order for the unpinned entries.
        self._entries: dict[str, tuple[bytes, bool]] = {}
        self._max_unpinned_bytes = max_unpinned_bytes

    @staticmethod
    def _key(text: str) -> str:
        # Mirror the engine's speech key: whitespace runs collapse to one space.
        return " ".join((text or "").split())

    def get(self, text: str) -> bytes | None:
        key = self._key(text)
        if not key:
            return None
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            if not entry[1]:
                # Touch refreshes the unpinned LRU position.
                self._entries.pop(key)
                self._entries[key] = entry
            return entry[0]

    def put(self, text: str, pcm: bytes, *, pinned: bool = False) -> None:
        key = self._key(text)
        if not key or not pcm:
            return
        with self._lock:
            existing = self._entries.pop(key, None)
            if existing is not None and existing[1]:
                pinned = True  # a warm pin survives an opportunistic re-store
            self._entries[key] = (pcm, pinned)
            self._evict_locked()

    def _evict_locked(self) -> None:
        unpinned = sum(len(pcm) for pcm, pinned in self._entries.values() if not pinned)
        while unpinned > self._max_unpinned_bytes:
            oldest = next(
                (k for k, (_pcm, pinned) in self._entries.items() if not pinned),
                None,
            )
            if oldest is None:
                return
            unpinned -= len(self._entries.pop(oldest)[0])


__all__ = ["BarkPcmCache"]
