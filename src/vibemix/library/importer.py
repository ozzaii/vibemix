# SPDX-License-Identifier: Apache-2.0
"""Phase 28 Plan 06 — drag-drop XML importer + batch embed.

Drag-drop UX flow:
    1. User drops Rekordbox XML on the Settings → Library panel.
    2. Renderer dispatches ``ipc.library.import { path }``.
    3. Sidecar runs ``import_library_async(xml_path, ...)``:
       a. Load XML via Phase 25 RekordboxLibrary.load_xml (writes
          ~/.cache/vibemix/library.pkl).
       b. For each track, batch-embed via LibraryEmbedder. Cache hits
          are silent; misses do the API call.
       c. Emit ``ipc.library.import_progress`` after every track so the
          UI can update the progress bar.
       d. On cancel: stop at next batch boundary, emit final progress
          tick with ``cancelled=True``.
       e. After import: refresh EvidenceRegistry so [track:<id>]
          citations work mid-session (no restart needed).

Cooperative cancel via asyncio.Event.
Per-track try/except so one bad audio file doesn't blow the batch.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Callable

from vibemix.library.embed import LibraryEmbedder
from vibemix.library.rekordbox import RekordboxLibrary
from vibemix.library.store import LibraryStore

logger = logging.getLogger(__name__)


class LibraryImporter:
    """Batch-embed importer with progress + cancel.

    on_progress callback signature:
        ``on_progress(payload: dict) -> None``
    where payload matches the Plan 09 ``LibraryImportProgressPayload`` shape.
    """

    def __init__(
        self,
        embedder: LibraryEmbedder,
        store: LibraryStore,
        on_progress: Callable[[dict], None] | None = None,
        batch_size: int = 10,
    ) -> None:
        self._embedder = embedder
        self._store = store
        self._on_progress = on_progress or (lambda _payload: None)
        self._batch_size = max(1, batch_size)
        self.cancel_flag = asyncio.Event()

    def _emit(self, payload: dict) -> None:
        try:
            self._on_progress(payload)
        except Exception as e:
            logger.warning("import progress emit failed: %s", e)

    async def import_library(self, xml_path: Path) -> dict:
        """Import an XML file. Returns final state dict.

        Final dict shape:
            {total, done, cache_hits, cancelled, schema_version: "1"}
        """
        loop = asyncio.get_running_loop()
        lib = RekordboxLibrary()
        total = await loop.run_in_executor(
            None, lib.load_xml, str(xml_path)
        )

        done = 0
        cache_hits = 0
        batch_buffer: list = []

        for track in lib.tracks.values():
            if self.cancel_flag.is_set():
                self._emit(
                    {
                        "total": total,
                        "done": done,
                        "current_track_name": "",
                        "cache_hits": cache_hits,
                        "cancelled": True,
                        "schema_version": "1",
                    }
                )
                # Flush any pending batch before exit.
                if batch_buffer:
                    try:
                        await loop.run_in_executor(
                            None, self._store.add_batch, batch_buffer
                        )
                    except Exception as e:
                        logger.warning("partial batch flush failed: %s", e)
                return {
                    "total": total,
                    "done": done,
                    "cache_hits": cache_hits,
                    "cancelled": True,
                }

            # Pre-probe the cache so we count hits accurately.
            # Uses the embedder's public probe (REVIEW WR-02 fix).
            was_hit = self._embedder.has_cached_embedding(track)

            try:
                vec = await loop.run_in_executor(
                    None, self._embedder.embed_track, track
                )
            except Exception as e:
                logger.warning(
                    "embed failed for %s: %s — skipping", track.track_id, e
                )
                done += 1
                continue

            batch_buffer.append((track.track_id, vec))
            done += 1
            if was_hit:
                cache_hits += 1

            self._emit(
                {
                    "total": total,
                    "done": done,
                    "current_track_name": f"{track.title} — {track.artist}"[:200],
                    "cache_hits": cache_hits,
                    "cancelled": False,
                    "schema_version": "1",
                }
            )

            if len(batch_buffer) >= self._batch_size:
                try:
                    await loop.run_in_executor(
                        None, self._store.add_batch, batch_buffer
                    )
                except Exception as e:
                    logger.warning("batch persist failed: %s", e)
                batch_buffer = []

        if batch_buffer:
            try:
                await loop.run_in_executor(
                    None, self._store.add_batch, batch_buffer
                )
            except Exception as e:
                logger.warning("final batch persist failed: %s", e)

        return {
            "total": total,
            "done": done,
            "cache_hits": cache_hits,
            "cancelled": False,
        }


async def import_library_async(
    xml_path: Path,
    embedder: LibraryEmbedder,
    store: LibraryStore,
    on_progress: Callable[[dict], None] | None = None,
    evidence_registry: object | None = None,
) -> dict:
    """Top-level entrypoint dispatched from the IPC handler.

    After import completes, refreshes ``evidence_registry`` (if provided)
    so ``[track:<id>]`` citations work mid-session — no restart needed.
    """
    importer = LibraryImporter(embedder, store, on_progress=on_progress)
    result = await importer.import_library(Path(xml_path))

    if evidence_registry is not None and not result.get("cancelled"):
        try:
            lib = RekordboxLibrary()
            if lib.try_load_cache():
                n = evidence_registry.register_library(lib)
                logger.info(
                    "post-import EvidenceRegistry refreshed: %s tracks", n
                )
        except Exception as e:
            logger.warning("post-import registry refresh failed: %s", e)

    return result


__all__ = ["LibraryImporter", "import_library_async"]
