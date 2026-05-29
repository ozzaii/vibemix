# SPDX-License-Identifier: Apache-2.0
"""Phase 93 Plan 04 — EXEMPLAR-03 packaged exemplar bank.

The honest-null fallback ships self-authored audio under
``src/vibemix/learn/assets/band_exemplars/{sub,low,mid,high}/*.wav``. When
the DJ's library has < 3 tracks passing the band floor, ``ExemplarFinder``
falls back to the packaged bank with the verbatim copy:

    "Your library doesn't have a great example of this — listen to this one we packaged"

Three sub-tests pin the contract:

    1. Empty library → packaged-bank pick with the honest-null reason.
    2. Bank directory layout: 4 band subdirs + MANIFEST.json present.
    3. Every MANIFEST entry has a corresponding file, attribution line,
       stable hash, and decodable audio.

REQ-ID: EXEMPLAR-03 (packaged bank scaffold + attribution).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from vibemix.learn.exemplar import ExemplarFinder, _packaged_bank_dir
from vibemix.library.audio_decode import load_audio_stereo


def test_empty_library_falls_back_to_packaged_bank(tmp_path, monkeypatch):
    """When the side-car band_shares table is empty, the engine falls back
    to the packaged CC-BY bank with the honest-null reason."""
    # Point the side-car DB at a tmp empty file
    monkeypatch.setattr(
        "vibemix.learn.band_share_store.DB_PATH", tmp_path / "library-clap.db"
    )
    # Block library cache load
    monkeypatch.setattr(
        "vibemix.library.rekordbox.RekordboxLibrary.try_load_cache",
        lambda: None,
    )

    finder = ExemplarFinder()
    picks = finder.find("low", k=1)
    assert picks, "empty library must fall back to a packaged low-band exemplar"
    assert picks[0].track_id.startswith("_packaged:low:")
    assert "Your library doesn't have a great example" in picks[0].reason
    assert picks[0].file_path.endswith(".wav")


def test_packaged_bank_directory_layout():
    """The bank must have all 4 band subdirs and a MANIFEST.json."""
    bank = _packaged_bank_dir()
    assert bank.exists()
    for band in ("sub", "low", "mid", "high"):
        assert (bank / band).exists(), f"Missing band subdir: {band}"
    assert (bank / "MANIFEST.json").exists()


def test_manifest_attribution_present_in_notice():
    """Every track in MANIFEST.json must have an attribution line in NOTICE.md."""
    bank = _packaged_bank_dir()
    manifest = json.loads((bank / "MANIFEST.json").read_text())
    notice = Path(__file__).parent.parent.parent / "NOTICE.md"
    assert notice.exists()
    notice_text = notice.read_text()
    for _track_rel, meta in manifest.get("tracks", {}).items():
        # NOTICE.md must contain the track's title + artist + license.
        assert meta["title"] in notice_text, f"NOTICE.md missing: {meta['title']}"
        assert meta["artist"] in notice_text, f"NOTICE.md missing artist: {meta['artist']}"
        assert meta["license"] in notice_text, f"NOTICE.md missing license: {meta['license']}"


def test_manifest_entries_exist_hash_and_decode() -> None:
    """The packaged bank is not just a manifest: every listed file exists,
    matches its pinned hash, and decodes to stereo float32.
    """
    bank = _packaged_bank_dir()
    manifest = json.loads((bank / "MANIFEST.json").read_text())
    tracks = manifest.get("tracks", {})
    assert set(tracks) == {
        "sub/vibemix_internal_sub_pulse.wav",
        "low/vibemix_internal_low_bass_gate.wav",
        "mid/vibemix_internal_mid_chord_body.wav",
        "high/vibemix_internal_high_hat_air.wav",
    }
    for rel, meta in tracks.items():
        path = bank / rel
        assert path.exists(), f"manifest lists missing audio file: {rel}"
        assert hashlib.sha256(path.read_bytes()).hexdigest() == meta["sha256"]
        samples, sr = load_audio_stereo(path)
        assert sr == meta["sample_rate_hz"]
        assert samples.ndim == 2
        assert samples.shape[1] == 2
        assert samples.shape[0] > 0
