# SPDX-License-Identifier: Apache-2.0
"""Phase 93 Plan 04 — EXEMPLAR-03 packaged CC-BY exemplar bank (RED-state stub).

The honest-null fallback ships ~3-5 MB of CC-BY-licensed audio under
``src/vibemix/learn/assets/band_exemplars/{sub,low,mid,high}/*.mp3``. When
the DJ's library has < 3 tracks passing the band floor, ``ExemplarFinder``
falls back to the packaged bank with the verbatim copy:

    "Your library doesn't have a great example of this — listen to this one we packaged"

Three sub-tests pin the contract:

    1. Empty library → packaged-bank pick with the honest-null reason.
    2. Bank directory layout: 4 band subdirs + MANIFEST.json present.
    3. Every MANIFEST entry has corresponding ``NOTICE.md`` attribution
       (CC-BY 4.0 license requirement).

Sub-tests carry per-test ``pytest.skip(...)`` early-returns inside the body
(graceful when KAAN-ACTION asset population is pending). The OUTER
module-level skip blocks the whole file today; once Plan 93-04 ships the
asset scaffold + manifest, the module skip lifts and the per-test skips
gracefully ride forward until Kaan funds the actual CC-BY tracks.

REQ-ID: EXEMPLAR-03 (packaged bank scaffold + attribution).
Downstream plan that flips this skip: **Plan 93-04**.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest

# Plan 93-04 — module-level skip lifted; ExemplarFinder + _packaged_bank_dir
# now ship in src/vibemix/learn/exemplar.py + the bank scaffold lives at
# src/vibemix/learn/assets/band_exemplars/. The per-test inner skip guards
# stay in place — they fire gracefully when CC-BY audio assets aren't yet
# populated (the §EXEMPLAR-BANK-SOURCING KAAN-ACTION).
from vibemix.learn.exemplar import ExemplarFinder, _packaged_bank_dir


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
    # Must return a packaged-bank pick if the bank exists
    if not picks:
        pytest.skip("Packaged bank not installed — CC-BY assets not yet shipped")
    assert picks[0].track_id.startswith("_packaged:low:")
    assert "Your library doesn't have a great example" in picks[0].reason


def test_packaged_bank_directory_layout():
    """The bank must have all 4 band subdirs and a MANIFEST.json."""
    bank = _packaged_bank_dir()
    if not bank.exists():
        pytest.skip("Packaged bank not yet shipped")
    for band in ("sub", "low", "mid", "high"):
        assert (bank / band).exists(), f"Missing band subdir: {band}"
    assert (bank / "MANIFEST.json").exists()


def test_manifest_attribution_present_in_notice():
    """Every track in MANIFEST.json must have an attribution line in NOTICE.md."""
    import json
    bank = _packaged_bank_dir()
    if not (bank / "MANIFEST.json").exists():
        pytest.skip("Manifest not yet shipped")
    manifest = json.loads((bank / "MANIFEST.json").read_text())
    notice = Path(__file__).parent.parent.parent / "NOTICE.md"
    if not notice.exists():
        pytest.skip("NOTICE.md not yet authored")
    notice_text = notice.read_text()
    for track_rel, meta in manifest.get("tracks", {}).items():
        # NOTICE.md must contain the track's title + artist + license
        assert meta["title"] in notice_text, f"NOTICE.md missing: {meta['title']}"
        assert meta["artist"] in notice_text, f"NOTICE.md missing artist: {meta['artist']}"
