# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

FIXTURE_DIR = Path(__file__).parent / "fixtures"


def load_json(name: str):
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def test_fixture_tracks_are_public_synthetic() -> None:
    tracks = load_json("tracks.json")
    assert len(tracks) == 8
    assert all(track["track_id"].startswith("fx-") for track in tracks)
    assert all(track["title"].startswith("Fixture") for track in tracks)
    assert all(track["artist"].startswith("Fixture") for track in tracks)
    assert all(track["location"].startswith("fixture://") for track in tracks)


def test_fixture_sections_cover_core_roles_and_edge_cases() -> None:
    sections = load_json("sections.json")
    roles = {section["role"] for section in sections}

    assert {"intro", "groove", "build", "breakdown", "drop", "outro"}.issubset(roles)
    assert "unknown" in roles
    assert any(section["source"] == "fallback" for section in sections)


def test_fixture_vectors_preserve_contract_shapes() -> None:
    sections = load_json("sections.json")
    vectors_8d = load_json("section_vectors_8d.json")
    vectors_512d = np.load(FIXTURE_DIR / "section_vectors_512d.npy")

    assert set(vectors_8d) == {f"vec8:{section['section_id']}" for section in sections}
    assert all(len(vector) == 8 for vector in vectors_8d.values())
    assert vectors_512d.shape == (len(sections), 512)
    assert vectors_512d.dtype == np.float32


def test_fixture_context_packets_reference_issued_candidates_only() -> None:
    pairs = load_json("transition_pairs.json")
    candidate_ids = {pair["candidate_id"] for pair in pairs}
    packets = load_json("context_packets.json")

    assert packets
    for packet in packets:
        assert packet["schema_version"] == "intel_context_v1"
        assert set(packet.get("candidate_ids", ())).issubset(candidate_ids)
        assert "raw_vector" not in json.dumps(packet)
        assert "/Users/" not in json.dumps(packet)


def test_fixture_manifest_declares_generated_files() -> None:
    manifest = load_json("MANIFEST.json")
    files = manifest["files"]

    assert manifest["fixture_version"] == "intel_fixture_v1"
    assert manifest["dataset_card_id"] == "dataset_intel_synthetic_v1"
    assert "section_vectors_512d.npy" in files
    assert all(value.startswith("sha256:") for value in files.values())
