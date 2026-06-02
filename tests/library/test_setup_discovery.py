# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import shlex
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
    assert candidates[0].import_action == {
        "type": "ipc.library.import",
        "payload": {"path": str(xml), "schema_version": "1"},
    }


def test_setup_discovery_finds_standard_traktor_nml(tmp_path: Path) -> None:
    nml = tmp_path / "Documents" / "Native Instruments" / "Traktor 4.0.0" / "collection.nml"
    nml.parent.mkdir(parents=True)
    nml.write_text("<NML />", encoding="utf-8")

    candidates = discover_library_setup_candidates(home=tmp_path)

    traktor = [candidate for candidate in candidates if candidate.kind == "traktor_nml"]
    assert traktor
    assert traktor[0].path == str(nml)
    assert "library ingest --source traktor" in traktor[0].command
    assert traktor[0].import_action == {
        "type": "ipc.library.import",
        "payload": {"path": str(nml), "schema_version": "1"},
    }


def test_setup_discovery_finds_standard_virtualdj_database(tmp_path: Path) -> None:
    database = tmp_path / "Documents" / "VirtualDJ" / "database.xml"
    database.parent.mkdir(parents=True)
    database.write_text("<VirtualDJ_Database />", encoding="utf-8")

    candidates = discover_library_setup_candidates(home=tmp_path)

    virtualdj = [
        candidate for candidate in candidates if candidate.kind == "virtualdj_database"
    ]
    assert virtualdj
    assert virtualdj[0].path == str(database)
    assert "library ingest --source virtualdj" in virtualdj[0].command
    assert virtualdj[0].import_action == {
        "type": "ipc.library.import",
        "payload": {"path": str(database), "schema_version": "1"},
    }


def test_setup_discovery_finds_standard_engine_database(tmp_path: Path) -> None:
    database = tmp_path / "Music" / "Engine Library" / "Database2" / "m.db"
    database.parent.mkdir(parents=True)
    database.write_bytes(b"SQLite fixture")

    candidates = discover_library_setup_candidates(home=tmp_path)

    engine = [candidate for candidate in candidates if candidate.kind == "engine_database"]
    assert engine
    assert engine[0].path == str(database)
    assert "library ingest --source engine" in engine[0].command
    assert engine[0].import_action == {
        "type": "ipc.library.import",
        "payload": {"path": str(database), "schema_version": "1"},
    }


def test_setup_discovery_finds_standard_serato_database(tmp_path: Path) -> None:
    database = tmp_path / "Music" / "_Serato_" / "database V2"
    database.parent.mkdir(parents=True)
    database.write_bytes(b"Serato fixture")

    candidates = discover_library_setup_candidates(home=tmp_path)

    serato = [candidate for candidate in candidates if candidate.kind == "serato_database"]
    assert serato
    assert serato[0].path == str(database)
    assert "library ingest --source serato" in serato[0].command
    assert serato[0].import_action == {
        "type": "ipc.library.import",
        "payload": {"path": str(database), "schema_version": "1"},
    }


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
    assert folders[0].import_action == {
        "type": "ipc.library.import",
        "payload": {"path": str(crate), "schema_version": "1"},
    }


def test_setup_discovery_quotes_shell_commands_but_keeps_ipc_path_raw(tmp_path: Path) -> None:
    crate = tmp_path / "Music" / "two words"
    crate.mkdir(parents=True)
    (crate / "track.mp3").write_bytes(b"audio")

    candidates = discover_library_setup_candidates(home=tmp_path)

    folders = [candidate for candidate in candidates if candidate.kind == "music_folder"]
    assert folders
    assert shlex.quote(str(crate)) in folders[0].command
    assert folders[0].import_action is not None
    assert folders[0].import_action["payload"] == {
        "path": str(crate),
        "schema_version": "1",
    }


def test_setup_discovery_does_not_descend_hidden_folders(tmp_path: Path) -> None:
    hidden = tmp_path / "Music" / ".private"
    hidden.mkdir(parents=True)
    (hidden / "secret.mp3").write_bytes(b"audio")

    candidates = discover_library_setup_candidates(home=tmp_path)

    assert candidates == []
