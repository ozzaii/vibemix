# SPDX-License-Identifier: Apache-2.0
"""LibrarySource — the structural contract every DJ-library source implements.

Phase 89 (DJ-Library Ingest). A ``LibrarySource`` is the firewall between a
DJ-software-specific catalog (Rekordbox ``collection.xml``, Traktor
``collection.nml``, VirtualDJ ``database.xml`` today; Serato / Engine later)
and the OS-agnostic ingest orchestrator
(``vibemix.library.ingest.ingest_source``). Each source knows three things:

    * ``detect()``         — is this source present on THIS machine?
    * ``default_paths()``  — the standard export locations to probe.
    * ``iter_tracks()``    — yield the parsed catalog as ``TrackEntry`` rows.

The ingest orchestrator depends on this Protocol, never on a concrete source,
so a second source (Serato) drops in by satisfying the same shape — no edits to
``ingest.py`` required (open/closed). ``@runtime_checkable`` so a duck-typed
fake in a test passes ``isinstance(obj, LibrarySource)``.

Lazy-import contract (mirrors ``clap_engine`` / ``telegram_bridge``): this
module's top level pulls ONLY ``__future__`` + ``typing`` + ``pathlib``. The
``TrackEntry`` import below is a numpy-free dataclass (``rekordbox`` defers its
own heavy ``pyrekordbox`` import into ``load_xml``), so importing this module in
CI — where ``torch`` / ``laion_clap`` are absent — must never pull a heavy dep.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Protocol, runtime_checkable

from vibemix.library.rekordbox import TrackEntry


@runtime_checkable
class LibrarySource(Protocol):
    """Structural contract for a DJ-library catalog source.

    A concrete source (e.g. :class:`~vibemix.library.sources.rekordbox.RekordboxSource`)
    satisfies this by exposing ``name`` plus the three methods. Structural
    typing means a class never has to inherit from this Protocol — implementing
    the shape is enough, which keeps test fakes trivial.
    """

    #: Stable, lower-case source id (e.g. ``"rekordbox"``). Surfaced in reports.
    name: str

    def detect(self) -> bool:
        """Return True iff this source's catalog is present on this machine.

        A read-only filesystem probe — never opens a database, never executes.
        On a hit the concrete source records the resolved path on itself so a
        subsequent :meth:`iter_tracks` reuses it.
        """
        ...

    def default_paths(self) -> list[Path]:
        """The standard export locations this source probes in :meth:`detect`."""
        ...

    def iter_tracks(self) -> Iterable[TrackEntry]:
        """Yield each catalog entry as a :class:`TrackEntry`.

        Lazily parses the detected catalog. One yield per track; the ingest
        orchestrator drives the embed/store loop over this iterable.
        """
        ...


__all__ = ["LibrarySource"]
