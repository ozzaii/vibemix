# SPDX-License-Identifier: Apache-2.0
"""vibemix.memory — the session-memory storage spine (Phase 63, v6.0).

A pure storage layer over a per-install ``memory.db``: embedded session
"moments" + their raw text signatures, with the same Mac/Win parity
guarantees as ``vibemix.library`` (sqlite-vec primary, numpy fallback, ranking
through the shared ``cosine_topk`` chokepoint). It imports nothing from the
live reaction path and makes no generation-model call — the store's only model
call is the embedding call (via the reused ``LibraryEmbedder``).

Public surface:
    ``from vibemix.memory import MemoryStore, open_memory_store, Record``
"""

from vibemix.memory.store import MemoryStore, Record, open_memory_store

__all__ = [
    "MemoryStore",
    "Record",
    "open_memory_store",
]
