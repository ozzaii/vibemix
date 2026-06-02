# SPDX-License-Identifier: Apache-2.0
"""Consent-preserving library setup discovery.

Fresh installs often have no ``library.pkl`` yet, so Viber cannot ground deck
identity or set-prep. This module provides a bounded, content-light discovery
pass: standard Rekordbox XML export locations, standard Traktor NML locations,
standard VirtualDJ/Engine DJ database locations, plus shallow music-folder
candidates. It never reads Rekordbox's live database and never auto-ingests.
"""

from __future__ import annotations

import shlex
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

from vibemix.library.sources.engine import EngineDJSource
from vibemix.library.sources.rekordbox import RekordboxSource
from vibemix.library.sources.traktor import TraktorSource
from vibemix.library.sources.virtualdj import VirtualDJSource

CandidateKind = Literal[
    "rekordbox_xml",
    "traktor_nml",
    "virtualdj_database",
    "engine_database",
    "music_folder",
]
SUPPORTED_AUDIO_SUFFIXES = (".mp3", ".m4a", ".wav", ".flac", ".aac")


@dataclass(frozen=True, slots=True)
class LibrarySetupCandidate:
    """A local source the user can explicitly import."""

    kind: CandidateKind
    path: str
    confidence: str
    reason: str
    command: str
    audio_files_seen: int = 0
    import_action: dict[str, object] | None = None

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        if self.import_action is None:
            data.pop("import_action", None)
        return data


def _ipc_import_action(path: Path) -> dict[str, object]:
    """Structured one-click app action for a user-approved library import."""
    return {
        "type": "ipc.library.import",
        "payload": {"path": str(path), "schema_version": "1"},
    }


def _quote_path(path: Path) -> str:
    return shlex.quote(str(path))


def _audio_count_bounded(root: Path, *, max_depth: int = 2, max_entries: int = 1200) -> int:
    """Count supported audio files under ``root`` without crawling the world."""
    if max_entries <= 0:
        return 0
    seen = 0
    count = 0
    stack: list[tuple[Path, int]] = [(root, 0)]
    while stack and seen < max_entries:
        current, depth = stack.pop()
        try:
            entries = list(current.iterdir())
        except OSError:
            continue
        for entry in entries:
            seen += 1
            if seen > max_entries:
                break
            name = entry.name
            if name.startswith("."):
                continue
            try:
                if entry.is_file() and entry.suffix.lower() in SUPPORTED_AUDIO_SUFFIXES:
                    count += 1
                elif depth < max_depth and entry.is_dir():
                    stack.append((entry, depth + 1))
            except OSError:
                continue
    return count


def _music_roots(home: Path) -> list[Path]:
    roots = [home / "Music", home / "DJ", home / "Downloads"]
    seen: set[Path] = set()
    out: list[Path] = []
    for root in roots:
        expanded = root.expanduser()
        if expanded in seen:
            continue
        seen.add(expanded)
        out.append(expanded)
    return out


def _path_at_home(candidate: Path, home: Path | None) -> Path:
    if home is None:
        return candidate
    return Path(str(candidate).replace(str(Path.home()), str(home), 1))


def discover_library_setup_candidates(
    *,
    home: Path | None = None,
    max_candidates: int = 5,
) -> list[LibrarySetupCandidate]:
    """Return likely library setup inputs, without mutating or indexing them."""
    base = Path.home() if home is None else Path(home)
    candidates: list[LibrarySetupCandidate] = []

    for xml in RekordboxSource().default_paths():
        path = _path_at_home(xml, base if home else None)
        try:
            if path.is_file():
                candidates.append(
                    LibrarySetupCandidate(
                        kind="rekordbox_xml",
                        path=str(path),
                        confidence="high",
                        reason="standard Rekordbox collection.xml export path exists",
                        command=f"uv run python -m vibemix library ingest {_quote_path(path)}",
                        import_action=_ipc_import_action(path),
                    )
                )
        except OSError:
            continue

    for nml in TraktorSource().default_paths():
        path = _path_at_home(nml, base if home else None)
        try:
            if path.is_file():
                candidates.append(
                    LibrarySetupCandidate(
                        kind="traktor_nml",
                        path=str(path),
                        confidence="high",
                        reason="standard Traktor collection.nml path exists",
                        command=(
                            "uv run python -m vibemix library ingest --source traktor "
                            f"{_quote_path(path)}"
                        ),
                        import_action=_ipc_import_action(path),
                    )
                )
        except OSError:
            continue

    for database in VirtualDJSource().default_paths():
        path = _path_at_home(database, base if home else None)
        try:
            if path.is_file():
                candidates.append(
                    LibrarySetupCandidate(
                        kind="virtualdj_database",
                        path=str(path),
                        confidence="high",
                        reason="standard VirtualDJ database.xml path exists",
                        command=(
                            "uv run python -m vibemix library ingest --source virtualdj "
                            f"{_quote_path(path)}"
                        ),
                        import_action=_ipc_import_action(path),
                    )
                )
        except OSError:
            continue

    for database in EngineDJSource().default_paths():
        path = _path_at_home(database, base if home else None)
        try:
            if path.is_file():
                candidates.append(
                    LibrarySetupCandidate(
                        kind="engine_database",
                        path=str(path),
                        confidence="high",
                        reason="standard Engine DJ Database2/m.db path exists",
                        command=(
                            "uv run python -m vibemix library ingest --source engine "
                            f"{_quote_path(path)}"
                        ),
                        import_action=_ipc_import_action(path),
                    )
                )
        except OSError:
            continue

    folder_candidates: list[LibrarySetupCandidate] = []
    for root in _music_roots(base):
        if not root.is_dir():
            continue
        paths = [root]
        try:
            paths.extend(
                sorted(
                    (child for child in root.iterdir() if child.is_dir() and not child.name.startswith(".")),
                    key=lambda item: item.name.lower(),
                )[:40]
            )
        except OSError:
            pass
        for path in paths:
            audio_count = _audio_count_bounded(path)
            if audio_count <= 0:
                continue
            confidence = "high" if audio_count >= 8 else "medium"
            folder_candidates.append(
                LibrarySetupCandidate(
                    kind="music_folder",
                    path=str(path),
                    confidence=confidence,
                    reason=f"bounded scan saw {audio_count} supported audio files",
                    command=f"uv run python -m vibemix library embed-folder {_quote_path(path)}",
                    audio_files_seen=audio_count,
                    import_action=_ipc_import_action(path),
                )
            )

    folder_candidates.sort(
        key=lambda item: (
            item.confidence != "high",
            -item.audio_files_seen,
            -len(Path(item.path).parts),
            item.path.lower(),
        )
    )
    candidates.extend(folder_candidates)
    return candidates[: max(0, int(max_candidates))]


def discover_library_setup_candidate_dicts(
    *,
    home: Path | None = None,
    max_candidates: int = 5,
) -> list[dict[str, object]]:
    """JSON-friendly wrapper for live-context and doctor surfaces."""
    return [
        candidate.to_dict()
        for candidate in discover_library_setup_candidates(
            home=home,
            max_candidates=max_candidates,
        )
    ]


__all__ = [
    "LibrarySetupCandidate",
    "discover_library_setup_candidate_dicts",
    "discover_library_setup_candidates",
]
