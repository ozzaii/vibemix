# SPDX-License-Identifier: Apache-2.0
"""Phase 42 Plan 01 / GATE-03 — corpus directory + LFS layout sanity tests.

Pins the engineering scaffolding for the 6-session real-corpus that Kaan
discharges via the KAAN-ACTION-LEGAL.md §GATE-03 runbook. NO real WAV bytes
are asserted to exist — that is the Kaan-discharge step. These tests pin
the SCAFFOLD so Plan 42-02 (threshold recalibration) and Plan 42-03/04
(`check_ear_test.sh` / `check_gate.sh`) can wire against a stable surface.
"""

from __future__ import annotations

import re
from pathlib import Path

# Repo root resolves from this test's location:
#   <repo>/tests/eval/test_corpus_lfs_layout.py → <repo>/
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_CORPUS_ROOT = _REPO_ROOT / "eval" / "corpus"
_SESSIONS_DIR = _CORPUS_ROOT / "sessions"
_MANIFEST_MD = _CORPUS_ROOT / "MANIFEST.md"
_LICENSES_MD = _CORPUS_ROOT / "LICENSES.md"
_GITATTRIBUTES = _REPO_ROOT / ".gitattributes"

# The six canonical session IDs from manifest.json (Phase 27-03).
SESSION_IDS = (
    "hard_tek_01",
    "hard_tek_02",
    "techno_01",
    "techno_02",
    "house_01",
    "house_02",
)


def test_corpus_sessions_dir_exists() -> None:
    """eval/corpus/sessions/.gitkeep must exist so the dir survives empty clones."""
    keepfile = _SESSIONS_DIR / ".gitkeep"
    assert keepfile.is_file(), (
        f"expected {keepfile} to track the LFS-only sessions directory"
    )


def test_manifest_md_lists_six_sessions() -> None:
    """MANIFEST.md must enumerate all 6 canonical session IDs."""
    assert _MANIFEST_MD.is_file(), f"missing {_MANIFEST_MD}"
    body = _MANIFEST_MD.read_text(encoding="utf-8")
    for sid in SESSION_IDS:
        assert sid in body, f"MANIFEST.md missing session id: {sid}"


def test_manifest_md_documents_two_genre_minimum() -> None:
    """MANIFEST.md must surface the ≥2 genres contract for check_ear_test.sh."""
    assert _MANIFEST_MD.is_file(), f"missing {_MANIFEST_MD}"
    body = _MANIFEST_MD.read_text(encoding="utf-8")
    # Accept any of the canonical phrasings used in the planning docs.
    patterns = (
        r"≥\s*2\s+genres",
        r">=\s*2\s+genres",
        r"2\s+genres\s+minimum",
    )
    matched = any(re.search(p, body, re.IGNORECASE) for p in patterns)
    assert matched, (
        "MANIFEST.md must document the '≥2 genres' / '2 genres minimum' "
        "ear-test contract surface"
    )


def test_gitattributes_no_lfs_rules() -> None:
    """git-lfs removed 2026-05-19 — `.gitattributes` carries no LFS routing.

    History demoted via `git lfs migrate export --everything`. Working-tree
    total (~23 MB) fits comfortably under GitHub's 100 MB per-file hard
    limit; the external git-lfs dependency is no longer required, which
    aligns with the one-click install thesis.
    """
    assert _GITATTRIBUTES.is_file(), f"missing {_GITATTRIBUTES}"
    body = _GITATTRIBUTES.read_text(encoding="utf-8")
    pattern = re.compile(r"^\s*[^#].*filter=lfs", re.MULTILINE)
    assert not pattern.search(body), (
        ".gitattributes carries an LFS routing rule; expected none after the "
        "2026-05-19 demotion."
    )


def test_licenses_md_has_six_session_slots() -> None:
    """LICENSES.md must carry one block per canonical session ID."""
    assert _LICENSES_MD.is_file(), f"missing {_LICENSES_MD}"
    body = _LICENSES_MD.read_text(encoding="utf-8")
    for sid in SESSION_IDS:
        assert sid in body, f"LICENSES.md missing session id: {sid}"


def test_licenses_md_documents_expanded_schema() -> None:
    """Plan 42-01 expanded LICENSES.md with Source URL / SHA256 / ffmpeg slots."""
    body = _LICENSES_MD.read_text(encoding="utf-8")
    for required in ("Source URL", "Attribution", "Retrieval date", "SHA256", "ffmpeg"):
        assert required in body, (
            f"LICENSES.md schema missing required field: {required}"
        )


def test_corpus_dir_has_no_committed_wav_bytes() -> None:
    """Plan 42-01 must commit zero .wav bytes — that's Kaan-discharge."""
    if not _SESSIONS_DIR.is_dir():
        return
    wavs = list(_SESSIONS_DIR.rglob("*.wav"))
    # An .wav under sessions/ is fine as long as it is an LFS pointer file
    # (which is < 256 bytes). Real binary content is Kaan-discharge.
    for wav in wavs:
        size = wav.stat().st_size
        assert size < 1024, (
            f"{wav} appears to carry real WAV bytes ({size} B); "
            "real corpus is Kaan-discharge per KAAN-ACTION-LEGAL.md §GATE-03"
        )
