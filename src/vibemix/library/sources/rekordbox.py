# SPDX-License-Identifier: Apache-2.0
"""RekordboxSource — the Rekordbox ``collection.xml`` LibrarySource (Phase 89).

Maps a Rekordbox XML export onto the :class:`LibrarySource` contract:

    * ``default_paths()`` — the standard Rekordbox export locations per-OS.
    * ``detect()``        — first ``collection.xml`` that exists wins; the hit
                            is recorded on ``self.resolved_path``.
    * ``iter_tracks()``   — drives the EXISTING :class:`RekordboxLibrary`
                            (cache-warm first, then ``load_xml``) and yields
                            each parsed :class:`TrackEntry`.

XML-ONLY by design (CONTEXT D-01 / LIBRARY-07): this source NEVER opens the
SQLCipher ``master.db`` — no ``Rekordbox6Database`` / ``pyrekordbox.db6`` import
here. The dormancy grep gate guards that commitment.

Lazy-import contract: top level pulls only stdlib + the numpy-free
``RekordboxLibrary``/``TrackEntry``. No torch / laion_clap / genai.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from pathlib import Path

from vibemix.library.rekordbox import RekordboxLibrary, TrackEntry

logger = logging.getLogger(__name__)

# Standard Rekordbox `collection.xml` export locations. Rekordbox does NOT
# write this file automatically — the DJ exports it via
# File → Export Collection in xml format → it lands at a user-chosen path,
# but these are the conventional defaults the DJ-share docs steer people to.
# We probe them in order; the first existing file wins.
_MACOS_DEFAULTS = (
    "~/Library/Pioneer/rekordbox/collection.xml",
    "~/Music/PioneerDJ/collection.xml",
    "~/Music/rekordbox/collection.xml",
)
_WINDOWS_DEFAULTS = (
    r"~\Documents\rekordbox\collection.xml",
    r"~\AppData\Roaming\Pioneer\rekordbox\collection.xml",
)


class RekordboxSource:
    """Rekordbox ``collection.xml`` source (structural :class:`LibrarySource`)."""

    name = "rekordbox"

    def __init__(self, xml_path: str | None = None) -> None:
        #: Explicit path the DJ passed (e.g. via ``library ingest <path>``).
        #: When set it takes precedence over the standard-location probe.
        self._explicit_path = xml_path
        #: The collection.xml that ``detect()`` resolved (None until detected).
        self.resolved_path: str | None = None

    def default_paths(self) -> list[Path]:
        """The standard export locations probed by :meth:`detect`.

        Returns the explicit path first (when given), then every per-OS
        default, all expanded to absolute user paths. We list BOTH macOS and
        Windows defaults so the probe is OS-tolerant — a non-existent path on
        the wrong OS simply fails the ``.exists()`` check, never raises.
        """
        candidates: list[str] = []
        if self._explicit_path:
            candidates.append(self._explicit_path)
        candidates.extend(_MACOS_DEFAULTS)
        candidates.extend(_WINDOWS_DEFAULTS)
        out: list[Path] = []
        for c in candidates:
            # expanduser() raises RuntimeError for a "~user" form it can't
            # resolve — and a Windows default like ``~\Documents\...`` is a
            # SINGLE POSIX component starting with ``~`` that POSIX cannot
            # expand. A wrong-OS default must simply fail the later
            # ``.exists()`` check, never abort the whole probe. Fall back to
            # the un-expanded path on any expansion failure.
            try:
                out.append(Path(c).expanduser())
            except (RuntimeError, OSError):  # pragma: no cover - wrong-OS path
                out.append(Path(c))
        return out

    def detect(self) -> bool:
        """Return True iff a ``collection.xml`` exists at a candidate path.

        First hit wins and is recorded on ``self.resolved_path``. Read-only
        ``.is_file()`` stat — no database open, no execution.
        """
        for candidate in self.default_paths():
            try:
                if candidate.is_file():
                    self.resolved_path = str(candidate)
                    return True
            except OSError:  # pragma: no cover - permission/odd FS
                continue
        return False

    def iter_tracks(self) -> Iterable[TrackEntry]:
        """Yield each parsed :class:`TrackEntry` from the detected collection.

        Resolves the path (running :meth:`detect` if not already done), then
        cache-warms via ``RekordboxLibrary.try_load_cache`` before falling
        through to a full ``load_xml`` parse. Raises ``FileNotFoundError`` if
        nothing was detected — the CLI surfaces this as the actionable
        "no collection.xml found" message rather than yielding nothing
        silently.
        """
        if self.resolved_path is None and not self.detect():
            raise FileNotFoundError(
                "RekordboxSource: no collection.xml detected — pass an explicit "
                "path or export via Rekordbox File → Export Collection in xml format"
            )

        lib = RekordboxLibrary()
        # Cache-warm first (cheap), but only trust the cache if it points at the
        # SAME source we resolved — otherwise parse the resolved XML fresh.
        if not (lib.try_load_cache() and lib.xml_path == self.resolved_path):
            lib.load_xml(self.resolved_path)

        yield from lib.tracks.values()


__all__ = ["RekordboxSource"]
