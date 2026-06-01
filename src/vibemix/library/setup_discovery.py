# SPDX-License-Identifier: Apache-2.0
"""Consent-preserving library setup discovery.

Fresh installs often have no ``library.pkl`` yet, so Viber cannot ground deck
identity or set-prep. This module provides a bounded, content-light discovery
pass: standard Rekordbox XML export locations plus shallow music-folder
candidates. It never reads Rekordbox's live database and never auto-ingests.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

from vibemix.library.sources.rekordbox import RekordboxSource

CandidateKind = Literal["rekordbox_xml", "music_folder"]
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

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


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


def discover_library_setup_candidates(
    *,
    home: Path | None = None,
    max_candidates: int = 5,
) -> list[LibrarySetupCandidate]:
    """Return likely library setup inputs, without mutating or indexing them."""
    base = Path.home() if home is None else Path(home)
    candidates: list[LibrarySetupCandidate] = []

    for xml in RekordboxSource().default_paths():
        path = Path(str(xml).replace(str(Path.home()), str(base), 1)) if home else xml
        try:
            if path.is_file():
                candidates.append(
                    LibrarySetupCandidate(
                        kind="rekordbox_xml",
                        path=str(path),
                        confidence="high",
                        reason="standard Rekordbox collection.xml export path exists",
                        command=f"uv run python -m vibemix library ingest {path}",
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
                    command=f"uv run python -m vibemix library embed-folder {path}",
                    audio_files_seen=audio_count,
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
