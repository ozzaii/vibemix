# SPDX-License-Identifier: Apache-2.0
"""vibemix.library.sources — DJ-library catalog sources (Phase 89).

Each source maps a DJ-software-specific catalog (Rekordbox ``collection.xml``,
Traktor ``collection.nml``, VirtualDJ ``database.xml``; Serato / Engine later)
onto the shared
:class:`LibrarySource` Protocol so the OS-agnostic ingest orchestrator depends
on the contract, not a concrete source.

Import-safe: this package's top level pulls only the lazy-import-clean
``base`` module. Concrete sources (``rekordbox``, ``traktor``, ``virtualdj``) are imported on
demand by the ingest path / CLI, never eagerly here — keeps the import surface
lean and the heavy-dep-free contract intact for CI.
"""

from vibemix.library.sources.base import LibrarySource

__all__ = ["LibrarySource"]
