# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from pathlib import Path

from vibemix.library.setup_discovery import discover_library_setup_candidates


def test_setup_discovery_finds_standard_rekordbox_xml(tmp_path: Path) -> None:
    xml = tmp_path / "Music" / "PioneerDJ" / "collection.xml"
    xml.parent.mkdir(parents=True)
    xml.write_text("<DJ_PLAYLISTS />", encoding="utf-8")

    candidates = discover_library_setup_candidates(home=tmp_path)

    assert candidates
    assert candidates[0].kind == "rekordbox_xml"
    assert candidates[0].path == str(xml)
    assert "library ingest" in candidates[0].command


def test_setup_discovery_finds_bounded_music_folder_candidate(tmp_path: Path) -> None:
    crate = tmp_path / "Music" / "PSYMIND"
    crate.mkdir(parents=True)
    for idx in range(3):
        (crate / f"track-{idx}.mp3").write_bytes(b"audio")
    (crate / "cover.jpg").write_bytes(b"image")

    candidates = discover_library_setup_candidates(home=tmp_path)

    folders = [candidate for candidate in candidates if candidate.kind == "music_folder"]
    assert folders
    assert folders[0].path == str(crate)
    assert folders[0].audio_files_seen == 3
    assert "library embed-folder" in folders[0].command


def test_setup_discovery_does_not_descend_hidden_folders(tmp_path: Path) -> None:
    hidden = tmp_path / "Music" / ".private"
    hidden.mkdir(parents=True)
    (hidden / "secret.mp3").write_bytes(b"audio")

    candidates = discover_library_setup_candidates(home=tmp_path)

    assert candidates == []
